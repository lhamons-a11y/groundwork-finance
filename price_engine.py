"""
Groundwork — Price Engine
=========================
Free, no-API-key stock/ETF price lookups via Yahoo Finance's public
(unofficial) chart endpoint. This is the module server.py's investments
blueprint was always written against (refresh_stale_prices, fetch_prices,
validate_ticker) but that never actually existed —
see GROUNDWORK_STATUS.md, confirmed missing July 3.
(get_portfolio_value was also part of the original contract, but its only
caller was the dead /api/analytics/net-worth route — both removed in the
July 8 dead-code sweep. Net Worth pulls live portfolio value client-side
via /api/investments/positions.)

CONFIRMED IN THE FIELD (July 6, beta): Yahoo's v7/finance/quote batch
endpoint — this module's original primary path — now requires a session
cookie + "crumb" auth token that a plain unauthenticated request doesn't
have, and has for a couple of years. Every call to it returns HTTP 401.
The v8/finance/chart endpoint does NOT require that auth as of 2026, and
was already built in as a fallback — so prices were still working, just
always via the slow path, with a warning logged on every single refresh.
Fixed by dropping the v7 call entirely and using v8/chart directly, one
ticker per request (it doesn't support batching multiple symbols in one
call, unlike v7). For a personal portfolio's handful of holdings this is
fast enough that batching isn't worth the complexity it would add.

Design constraints, stated up front:
  - Free, unauthenticated stock data endpoints are inherently unstable —
    undocumented, can change or rate-limit without notice. Everything here
    is "best effort": a failure never raises into the caller's request
    thread, it just means that ticker (or all tickers) stay unpriced until
    the next refresh, or until the user sets a price manually.
  - No API key, no config, no new pip dependency. Uses stdlib urllib only,
    matching the rest of this codebase (see server.py's _get_api_key).
  - Manual prices are sacred. If a user has set a price by hand
    (PriceCache.is_manual), auto-refresh skips that ticker entirely.
  - If Yahoo's endpoint ever goes away or adds auth too, replace
    YAHOO_CHART_URL and _quote_one below — the staleness tracking, DB
    writes, and error handling around it don't need to change.
"""

import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta

from core.database import PriceCache

logger = logging.getLogger('groundwork.price_engine')

# ── Config ────────────────────────────────────────────────────────────────
STALE_MINUTES   = 30   # prices older than this are refreshed opportunistically
REQUEST_TIMEOUT = 6    # seconds — never let a slow price call hang a request
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
              'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# v8 chart endpoint — confirmed as of 2026 to work without cookie/crumb
# auth, unlike v7/finance/quote (see module docstring). One ticker per
# request; used both for live quotes and single-ticker validation.
YAHOO_CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'


# ── Low-level HTTP ────────────────────────────────────────────────────────

def _http_get_json(url: str) -> dict:
    """GET a URL and parse JSON. Raises on failure — callers decide whether
    that's fatal (skip this ticker) or total (skip the whole batch)."""
    from core import egress                        # item 8: the one door out
    return egress.get_json(url, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT)


# ── Quote fetching ────────────────────────────────────────────────────────

def _quote_one(symbol: str):
    """
    Fetch a single ticker's quote via the v8 chart endpoint — confirmed
    working without auth as of 2026, unlike the old v7 batch endpoint.
    Returns {price, previous_close, day_change, day_change_pct,
             company_name, currency, market_state}, or None if the ticker
    can't be resolved or the request fails for any reason. Never raises.
    """
    try:
        url  = YAHOO_CHART_URL.format(symbol=urllib.parse.quote(symbol.upper()))
        data = _http_get_json(url)
    except Exception as e:
        logger.info('price_engine: quote failed for %s: %s', symbol, e)
        return None

    result = (data.get('chart', {}) or {}).get('result') or []
    if not result:
        return None
    meta  = result[0].get('meta', {})
    price = meta.get('regularMarketPrice')
    if price is None:
        return None
    prev_close = meta.get('previousClose') or meta.get('chartPreviousClose') or price
    return {
        'price':          float(price),
        'previous_close': float(prev_close),
        'day_change':     float(price - prev_close),
        'day_change_pct': round((price - prev_close) / prev_close * 100, 4) if prev_close else 0.0,
        'company_name':   meta.get('symbol', symbol.upper()),
        'currency':       meta.get('currency', 'USD'),
        'market_state':   meta.get('marketState', ''),
    }


# ── Public API — matches server.py's existing imports exactly ─────────────

def fetch_prices(tickers: list, session) -> dict:
    """
    Fetch and persist current prices for the given tickers into PriceCache.
    Never raises — logs and skips on error. Skips (never overwrites) any
    ticker the user has manually priced.

    Returns {ticker: {price, previous_close, day_change, day_change_pct,
                       company_name, currency, market_state}} for whatever
    succeeded — callers should treat a missing ticker as "couldn't price it
    this round", not an error.
    """
    tickers = [t.upper().strip() for t in tickers if t and t.strip()]
    if not tickers:
        return {}

    results = {}
    for t in tickers:
        row = _quote_one(t)
        if row:
            results[t] = row

    now = datetime.utcnow()
    for ticker, info in results.items():
        row = session.get(PriceCache, ticker)
        if row and row.is_manual:
            continue  # never silently overwrite a manually-set price
        if row:
            row.price          = info['price']
            row.previous_close = info['previous_close']
            row.day_change     = info['day_change']
            row.day_change_pct = info['day_change_pct']
            row.company_name   = info['company_name']
            row.currency       = info['currency']
            row.market_state   = info['market_state']
            row.last_updated   = now
            row.is_manual      = False
            row.source         = 'yahoo'
        else:
            session.add(PriceCache(
                ticker=ticker, price=info['price'],
                previous_close=info['previous_close'],
                day_change=info['day_change'], day_change_pct=info['day_change_pct'],
                company_name=info['company_name'], currency=info['currency'],
                market_state=info['market_state'], last_updated=now,
                is_manual=False, source='yahoo',
            ))
    session.commit()
    return results


def refresh_stale_prices(session, force: bool = False) -> dict:
    """
    Refresh any cached price older than STALE_MINUTES for every ticker
    currently held in an open lot, plus any held ticker with no cache row
    at all. Cheap no-op when nothing's stale — safe to call opportunistically
    on every positions load.

    force=True refreshes every held ticker regardless of age (the manual
    "Refresh prices" button).

    Returns {'refreshed': [...], 'skipped': [...], 'errors': int}.
    """
    from core.database import InvestmentLot

    held_tickers = {
        row[0].upper() for row in
        session.query(InvestmentLot.ticker).filter_by(is_closed=False).distinct().all()
    }
    if not held_tickers:
        return {'refreshed': [], 'skipped': [], 'errors': 0}

    cutoff = datetime.utcnow() - timedelta(minutes=STALE_MINUTES)
    cached = {
        row.ticker: row for row in
        session.query(PriceCache).filter(PriceCache.ticker.in_(held_tickers)).all()
    }

    to_refresh, skipped = [], []
    for ticker in held_tickers:
        row = cached.get(ticker)
        if row and row.is_manual:
            skipped.append(ticker)  # never auto-overwrite a manual price
            continue
        if force or not row or not row.last_updated or row.last_updated < cutoff:
            to_refresh.append(ticker)
        else:
            skipped.append(ticker)

    if not to_refresh:
        return {'refreshed': [], 'skipped': skipped, 'errors': 0}

    try:
        results = fetch_prices(to_refresh, session)
    except Exception as e:
        logger.warning('price_engine: refresh_stale_prices failed: %s', e)
        return {'refreshed': [], 'skipped': skipped, 'errors': len(to_refresh)}

    refreshed = list(results.keys())
    errors    = len(to_refresh) - len(refreshed)
    return {'refreshed': refreshed, 'skipped': skipped, 'errors': errors}


def validate_ticker(symbol: str) -> dict:
    """
    Check whether a ticker symbol resolves to a real security.
    Never raises — a lookup failure just means valid=False.
    Returns {'valid': bool, 'symbol': str, 'name': str|None,
              'price': float|None, 'currency': str}.
    """
    symbol = (symbol or '').strip().upper()
    if not symbol:
        return {'valid': False, 'symbol': symbol, 'error': 'empty symbol'}

    info = _quote_one(symbol)

    if not info:
        return {'valid': False, 'symbol': symbol}

    return {
        'valid':    True,
        'symbol':   symbol,
        'name':     info.get('company_name', symbol),
        'price':    info.get('price'),
        'currency': info.get('currency', 'USD'),
    }
