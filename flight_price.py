"""
Groundwork — Flight Price Engine
==================================
Real live flight prices for trip-planning, via SerpApi's Google Flights
engine — chosen over the other candidates considered (GROUNDWORK_LLM_BUILD_PLAN.md
decision #7, previously deferred):
  - Amadeus for Developers: free tier returns TEST/sandbox data, not real
    live prices — conflicts with this app's never-fabricate principle unless
    upgraded to a paid production key.
  - Duffel: real live pricing, but built for actually booking flights
    (heavier setup/verification than a personal trip-budget estimate needs).
  - Kiwi.com (Tequila API): access increasingly restricted to formal
    partnerships; uncertain availability for a small personal integration.
  - SerpApi: real, live Google Flights consumer prices via a simple REST
    GET + API key. No airline business/partnership verification. Free tier
    (100 searches/month) returns genuinely live prices, not sandbox data.

Design constraints, matching gas_price.py/utility_price.py's established
pattern for this codebase's other keyed external data sources:
  - A failure never raises into the caller — returns {'live': False, ...}
    with an honest reason, never a guessed price standing in for a real one.
  - Cached (FlightPriceCache, core/database.py), keyed on
    origin+destination+dates+travelers — not a single global key like
    gas_price.py's national average, because every search here is
    route-specific. This is also a quota guard: SerpApi's free tier is
    100 searches/month, and the trip planner recomputes on every keystroke
    (tripUpdateBudget in app.js) — this module is deliberately NOT called
    from that automatic path. It's wired to an explicit "Search live flight
    prices" button instead (see server.py's /api/trip/flight-price route
    and app.js's searchLiveFlightPrice()).
  - API key via server.py's _get_flights_api_key() (same config.json/env
    lookup convention as every other external key this app uses) — no key
    is bundled or hardcoded here. Free key at https://serpapi.com/users/sign_up

Residual uncertainty, flagged rather than hidden: the field names below
(`best_flights`/`other_flights`/`price`/`flights[].airline`) follow SerpApi's
documented Google Flights engine response shape, but this was never
exercised against a real key during development (registering one wasn't
something to do on the user's behalf). If a field name turns out wrong,
_parse_response() returns None exactly like any other failure — the
caller gets an honest "couldn't get a live price" rather than a wrong one.
"""
import json
import hashlib
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

from core.database import db_session, FlightPriceCache

logger = logging.getLogger('groundwork.flight_price')

REQUEST_TIMEOUT = 10
STALE_HOURS = 6   # flight prices move faster than gas/utility — a shorter cache window
SERPAPI_URL = 'https://serpapi.com/search.json'


def _cache_key(origin: str, destination: str, outbound_date: str, return_date, travelers: int) -> str:
    raw = f'{origin.upper()}|{destination.upper()}|{outbound_date}|{return_date or ""}|{travelers}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _read_cache(key: str):
    try:
        with db_session() as session:
            row = session.get(FlightPriceCache, key)
            if not row or row.price_total is None or not row.fetched_at:
                return None
            if datetime.utcnow() - row.fetched_at >= timedelta(hours=STALE_HOURS):
                return None
            return {'price_total': row.price_total, 'airline': row.airline}
    except Exception as e:
        logger.warning('flight_price: cache read failed: %s', e)
        return None


def _write_cache(key: str, origin: str, destination: str, outbound_date: str,
                  return_date, travelers: int, price: float, airline, raw: dict):
    try:
        with db_session() as session:
            row = session.get(FlightPriceCache, key)
            if not row:
                row = FlightPriceCache(
                    cache_key=key, origin=origin.upper(), destination=destination.upper(),
                    outbound_date=outbound_date, return_date=return_date, travelers=travelers,
                )
                session.add(row)
            row.price_total = price
            row.airline = airline
            row.raw_json = json.dumps(raw)[:4000]
            row.fetched_at = datetime.utcnow()
            session.commit()
    except Exception as e:
        logger.warning('flight_price: cache write failed: %s', e)


def _parse_response(data: dict):
    """The cheapest of best_flights/other_flights, or None if the response
    doesn't have what's expected — never guesses a price from a partial
    shape."""
    if data.get('error'):
        return None, str(data['error'])[:200]
    candidates = (data.get('best_flights') or []) + (data.get('other_flights') or [])
    if not candidates:
        return None, 'no_results'
    priced = [f for f in candidates if isinstance(f.get('price'), (int, float))]
    if not priced:
        return None, 'no_price_in_response'
    cheapest = min(priced, key=lambda f: f['price'])
    airline = None
    segments = cheapest.get('flights') or []
    if segments:
        airline = segments[0].get('airline')
    return {'price': float(cheapest['price']), 'airline': airline, 'raw': cheapest}, None


def search_flights(origin: str, destination: str, outbound_date: str,
                    return_date: str = None, travelers: int = 1, api_key: str = '') -> dict:
    """
    The single entry point server.py's route calls. Returns:
      {'live': True, 'price_total': float, 'airline': str|None, 'cached': bool}
      {'live': False, 'reason': str}   — no key / unreachable / no results /
                                          unexpected response shape

    NEVER a guessed number standing in for a real one — 'live': False with a
    reason is the correct, honest output when a real price can't be gotten.
    """
    if not origin or not destination or not outbound_date:
        return {'live': False, 'reason': 'missing_required_field'}

    # Cache check comes before the api_key gate: serving an already-cached
    # price makes no new request, so it needs no key. Checking api_key first
    # would wrongly hide a valid cached result the moment a key goes missing
    # or expires — the exact bug this ordering avoids.
    key = _cache_key(origin, destination, outbound_date, return_date, travelers)
    cached = _read_cache(key)
    if cached:
        return {'live': True, 'price_total': cached['price_total'],
                'airline': cached['airline'], 'cached': True}

    if not api_key:
        return {'live': False, 'reason': 'no_api_key'}

    params = {
        'engine': 'google_flights',
        'departure_id': origin.upper(),
        'arrival_id': destination.upper(),
        'outbound_date': outbound_date,
        'currency': 'USD',
        'hl': 'en',
        'adults': str(max(1, travelers)),
        'type': '1' if return_date else '2',   # 1 = round trip, 2 = one way
        'api_key': api_key,
    }
    if return_date:
        params['return_date'] = return_date

    url = f'{SERPAPI_URL}?{urllib.parse.urlencode(params)}'
    try:
        req = urllib.request.Request(
            url, headers={'User-Agent': 'Groundwork-PersonalFinance/1.0 (trip planner flight search)'})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        logger.info('flight_price: SerpApi fetch failed: %s', e)
        return {'live': False, 'reason': 'unreachable'}

    result, reason = _parse_response(data)
    if not result:
        return {'live': False, 'reason': reason}

    _write_cache(key, origin, destination, outbound_date, return_date, travelers,
                 result['price'], result['airline'], result['raw'])
    return {'live': True, 'price_total': result['price'], 'airline': result['airline'], 'cached': False}
