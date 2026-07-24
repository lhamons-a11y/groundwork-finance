"""
Groundwork — Gas Price Engine
==============================
Real U.S. national average gas price for trip-planning fuel estimates, via
the EIA (U.S. Energy Information Administration) open data API — the source
locked in during planning (Blueprint decision: "gas price = EIA").

Design constraints, matching price_engine.py's established pattern for this
codebase's other free/keyed external data source:
  - Zero user-data egress: this fetch takes no input from the user's data at
    all — it's a fixed query for the national weekly average. Nothing about
    the user's trip, location, or finances is ever sent anywhere.
  - A failure never raises into the caller's request thread — falls back to
    the last cached price (even if stale — a week-old real number beats a
    hardcoded guess), or FALLBACK_PRICE if there's never been a successful
    fetch (e.g. no EIA key configured yet).
  - EIA key via server.py's _get_eia_api_key() (same config.json/env lookup
    as the Anthropic key) — no key is bundled or hardcoded here.

Residual uncertainty, flagged rather than hidden: the exact response field
names below (`response.data[].value` / `.period`) follow EIA's documented
v2 API response envelope, but this was never exercised against a real key
during development (registering one wasn't something to do on the user's
behalf — see the code that calls this module). The endpoint URL and query
parameters ARE confirmed live (a keyless request correctly returns EIA's
own "API_KEY_MISSING" error, proving the route/facets parse). If the field
names turn out wrong once a real key is in place, _fetch_from_eia() returns
None exactly like any other failure — the app stays on the honest fallback
rather than breaking, and this is the one function to fix.
"""
import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

from core.database import db_session, AppSetting

logger = logging.getLogger('groundwork.gas_price')

REQUEST_TIMEOUT = 6      # seconds — never let a slow call hang a request
STALE_HOURS     = 24     # EIA publishes weekly; no need to refetch more than daily
FALLBACK_PRICE  = 3.40   # used only when no key is configured or every fetch has failed
CACHE_KEY       = 'gas_price_cache'   # AppSetting key: JSON {price, period, fetched_at}

# Weekly U.S. average retail price, regular gasoline, all formulations.
# product=EPMR (regular motor gasoline), duoarea=NUS (U.S. national average).
EIA_URL = (
    'https://api.eia.gov/v2/petroleum/pri/gnd/data/'
    '?api_key={key}&frequency=weekly&data[0]=value'
    '&facets[product][]=EPMR&facets[duoarea][]=NUS'
    '&sort[0][column]=period&sort[0][direction]=desc&length=1'
)


def _fetch_from_eia(api_key: str):
    """One weekly national-average regular-gasoline price point, or None on
    any failure (bad key, network issue, unexpected response shape). Never
    raises — the caller treats None exactly like "nothing new right now"."""
    try:
        url = EIA_URL.format(key=urllib.parse.quote(api_key))
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            data = json.loads(r.read().decode('utf-8'))
        rows = ((data.get('response') or {}).get('data')) or []
        if not rows:
            return None
        price = rows[0].get('value')
        period = rows[0].get('period')
        if price is None:
            return None
        return {'price': round(float(price), 3), 'period': str(period or '')}
    except Exception as e:
        logger.info('gas_price: EIA fetch failed: %s', e)
        return None


def _read_cache():
    try:
        with db_session() as session:
            row = session.query(AppSetting).filter_by(key=CACHE_KEY).first()
            return json.loads(row.value) if row else None
    except Exception:
        return None


def _write_cache(price: float, period: str):
    try:
        payload = json.dumps({
            'price': price, 'period': period,
            'fetched_at': datetime.utcnow().isoformat(),
        })
        with db_session() as session:
            row = session.query(AppSetting).filter_by(key=CACHE_KEY).first()
            if row:
                row.value = payload
            else:
                session.add(AppSetting(key=CACHE_KEY, value=payload))
            session.commit()
    except Exception as e:
        logger.warning('gas_price: cache write failed: %s', e)


def get_national_gas_price(api_key: str) -> dict:
    """
    The single entry point server.py's route calls. Returns
    {price, period, live, source}:
      live=True  — a fresh (<STALE_HOURS old) EIA price, cached or just fetched
      live=False — no key configured, or every fetch attempt has failed;
                   price is the last known cached value, or FALLBACK_PRICE
    """
    cached = _read_cache()
    if cached:
        try:
            fetched_at = datetime.fromisoformat(cached['fetched_at'])
            fresh = datetime.utcnow() - fetched_at < timedelta(hours=STALE_HOURS)
        except Exception:
            fresh = False
        if fresh:
            return {'price': cached['price'], 'period': cached['period'],
                    'live': True, 'source': 'EIA (cached)'}

    if api_key:
        fresh_data = _fetch_from_eia(api_key)
        if fresh_data:
            _write_cache(fresh_data['price'], fresh_data['period'])
            return {'price': fresh_data['price'], 'period': fresh_data['period'],
                    'live': True, 'source': 'EIA'}

    if cached:
        return {'price': cached['price'], 'period': cached['period'],
                'live': False, 'source': 'EIA (stale cache)'}

    return {'price': FALLBACK_PRICE, 'period': '', 'live': False, 'source': 'estimate'}
