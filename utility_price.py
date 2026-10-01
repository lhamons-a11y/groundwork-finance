"""
Groundwork — Utility Price Engine
====================================
Real residential utility price benchmarks (natural gas, electricity) for
the household budget — "your Gas/Electric line vs the state or national
average" — via the same EIA API already integrated for trip gas prices
(gas_price.py, Phase 5A). Extended so users see a benchmark for where
they actually live, not just a national figure.

Both series publish monthly with no seasonal gap (unlike propane/heating
oil, which EIA only collects during heating season — confirmed live: those
series' most recent point sits in March while gas/electricity carry
through April). Design matches gas_price.py exactly: stdlib urllib only, a
failure never raises into the caller, cached with a staleness window,
honest fallback when unreachable or no EIA key is configured.

State handling: EIA's petroleum/natural-gas facet convention is
"S" + the 2-letter USPS state code (SOH=Ohio, SNY=New York, STX=Texas —
confirmed across every state checked); electricity's retail-sales facet
takes the bare 2-letter code directly, plus "US" for the national total
(confirmed live). No state selected -> national ('NUS' / 'US').
"""
import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

from core.database import db_session, AppSetting

logger = logging.getLogger('groundwork.utility_price')

REQUEST_TIMEOUT = 6
STALE_HOURS = 24 * 7   # both series publish monthly — a week-old cache is still fresh

NATURAL_GAS_FALLBACK = 14.00   # $/MCF — rough national ballpark, used only if unreachable
ELECTRICITY_FALLBACK = 16.50   # cents/kWh — rough national ballpark, used only if unreachable

NG_URL = ('https://api.eia.gov/v2/natural-gas/pri/sum/data/'
          '?api_key={key}&frequency=monthly&data[0]=value'
          '&facets[process][]=PRS&facets[duoarea][]={area}'
          '&sort[0][column]=period&sort[0][direction]=desc&length=6')

ELEC_URL = ('https://api.eia.gov/v2/electricity/retail-sales/data/'
            '?api_key={key}&frequency=monthly&data[0]=price'
            '&facets[sectorid][]=RES&facets[stateid][]={state}'
            '&sort[0][column]=period&sort[0][direction]=desc&length=6')


# UTILITY_ESTIMATES.md U0 (item 26, ruled 2026-10-01): EIA publishes each state's months on its own schedule, and
# its newest row for a state can exist with no value yet (Ohio's June 2026 natural gas did). Asking for one row
# and treating an empty value as a failure sent the price to the hard-coded estimate, so the Budget page showed
# no EIA line at all. The last six rows are asked for, and the newest one that HAS a value is used, with its own
# period - for every state, not one.
def _latest_published(rows, field):
    for r in rows or []:
        v = r.get(field)
        if v is not None and str(v).strip() != '':
            return r
    return None


def _state_to_duoarea(state: str) -> str:
    return 'S' + state.strip().upper()[:2]


def _fetch_natural_gas(api_key: str, area: str):
    """One monthly residential natural-gas price point for `area`
    (a duoarea code, e.g. 'SOH' or 'NUS'), or None on any failure. Never
    raises."""
    try:
        url = NG_URL.format(key=urllib.parse.quote(api_key), area=urllib.parse.quote(area))
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            data = json.loads(r.read().decode('utf-8'))
        row = _latest_published(((data.get('response') or {}).get('data')) or [], 'value')
        if not row:
            return None
        return {'price': round(float(row['value']), 2), 'period': str(row.get('period') or ''),
                'area_name': row.get('area-name', '')}
    except Exception as e:
        logger.info('utility_price: natural gas fetch failed (%s): %s', area, e)
        return None


def _fetch_electricity(api_key: str, state_code: str):
    """One monthly residential electricity price point for `state_code`
    (a 2-letter USPS code or 'US'), or None on any failure. Never raises."""
    try:
        url = ELEC_URL.format(key=urllib.parse.quote(api_key), state=urllib.parse.quote(state_code))
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            data = json.loads(r.read().decode('utf-8'))
        row = _latest_published(((data.get('response') or {}).get('data')) or [], 'price')
        if not row:
            return None
        return {'price': round(float(row['price']), 2), 'period': str(row.get('period') or ''),
                'area_name': row.get('stateDescription', '')}
    except Exception as e:
        logger.info('utility_price: electricity fetch failed (%s): %s', state_code, e)
        return None


def _cache_key(kind: str, area: str) -> str:
    return f'utility_price_{kind}_{area}'


def _read_cache(key: str):
    try:
        with db_session() as session:
            row = session.query(AppSetting).filter_by(key=key).first()
            return json.loads(row.value) if row else None
    except Exception:
        return None


def _write_cache(key: str, price: float, period: str, area_name: str):
    try:
        payload = json.dumps({
            'price': price, 'period': period, 'area_name': area_name,
            'fetched_at': datetime.utcnow().isoformat(),
        })
        with db_session() as session:
            row = session.query(AppSetting).filter_by(key=key).first()
            if row:
                row.value = payload
            else:
                session.add(AppSetting(key=key, value=payload))
            session.commit()
    except Exception as e:
        logger.warning('utility_price: cache write failed (%s): %s', key, e)


def _is_fresh(cached: dict) -> bool:
    try:
        fetched_at = datetime.fromisoformat(cached['fetched_at'])
        return datetime.utcnow() - fetched_at < timedelta(hours=STALE_HOURS)
    except Exception:
        return False


def _get_price(kind: str, area: str, api_key: str, fetch_fn, fallback: float) -> dict:
    """Shared cache/fetch/fallback flow for both series — same three-tier
    honesty rule as gas_price.py: fresh cache > fresh fetch > stale cache >
    a labeled estimate. Never raises, never silently wrong about which
    tier it's returning."""
    key = _cache_key(kind, area)
    cached = _read_cache(key)
    if cached and _is_fresh(cached):
        return {'price': cached['price'], 'period': cached['period'], 'area_name': cached.get('area_name', ''),
                'live': True, 'source': 'EIA (cached)'}

    if api_key:
        fresh = fetch_fn(api_key, area)
        if fresh:
            _write_cache(key, fresh['price'], fresh['period'], fresh['area_name'])
            return {'price': fresh['price'], 'period': fresh['period'], 'area_name': fresh['area_name'],
                    'live': True, 'source': 'EIA'}

    if cached:
        return {'price': cached['price'], 'period': cached['period'], 'area_name': cached.get('area_name', ''),
                'live': False, 'source': 'EIA (stale cache)'}

    return {'price': fallback, 'period': '', 'area_name': '', 'live': False, 'source': 'estimate'}


def get_natural_gas_price(api_key: str, state: str = '') -> dict:
    """Residential natural gas price, $/MCF (thousand cubic feet — the unit
    on an actual gas bill). {price, period, area_name, live, source}."""
    area = _state_to_duoarea(state) if state else 'NUS'
    out = _get_price('ng', area, api_key, _fetch_natural_gas, NATURAL_GAS_FALLBACK)
    return _national_if_unpublished(out, area, 'NUS', 'ng', api_key, _fetch_natural_gas, NATURAL_GAS_FALLBACK)


def get_electricity_price(api_key: str, state: str = '') -> dict:
    """Residential electricity price, cents/kWh.
    {price, period, area_name, live, source}."""
    area = state.strip().upper()[:2] if state else 'US'
    out = _get_price('elec', area, api_key, _fetch_electricity, ELECTRICITY_FALLBACK)
    return _national_if_unpublished(out, area, 'US', 'elec', api_key, _fetch_electricity, ELECTRICITY_FALLBACK)


def _national_if_unpublished(out, area, national, kind, api_key, fetch_fn, fallback):
    """U0: a state EIA does not publish (no row with a value, no cache) is shown at the U.S. figure - and SAYS so.

    `area_name` becomes 'U.S.' (the Budget page prints it as the area), and `national_fallback` names the state that
    was asked for, so nothing presents the national figure as the state's.
    """
    if out.get('source') != 'estimate' or area == national:
        return out
    nat = _get_price(kind, national, api_key, fetch_fn, fallback)
    if nat.get('source') == 'estimate':
        return out
    return {**nat, 'area_name': 'U.S.', 'national_fallback': area}
