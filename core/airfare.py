"""
Groundwork — average airfare by route (gw 2.0/DOT_AIRFARE.md, item 41)
=====================================================================
The trip planner's default flight cost: the average one-way fare passengers
actually paid on a route, from the U.S. DOT Domestic Airline Fares Consumer
Report (a 10% sample of real tickets, DB1B; public domain). It replaces the
old made-up $220/person.

  - Two DOT tables, both published quarterly on data.transportation.gov with
    no key: Table 6 (yj5y-b2ir) by city market, every contiguous-state route
    averaging 10+ passengers a day; Table 1a (tfrh-tu9e) by airport pair,
    only where one end is a city with more than one airport.
  - DOT markets have no direction: Chicago-Denver and Denver-Chicago are one
    row. A round trip is the outbound leg plus the return leg, the same
    average twice.
  - A table ships with the app (core/data/dot_airfare.json), and refresh()
    downloads a newer quarter into the data folder when DOT publishes one.
    Both downloads are the whole table for a quarter - nothing about the
    user's trip is ever sent. Looking a route up never leaves the computer.
  - A route DOT does not list returns found: False. Never a guessed fare.
  - Each city's airports (item 43) ship in the same table: BTS's airport list
    ("City, ST: Airport name") matched to DOT's city names, kept when the
    airport carried passengers in BTS's T-100 counts, busiest first. Built at
    release (build_airports); a DOT refresh keeps them.
  - Item 51 (gw 2.0/FARE_CHANGE.md, Rob 2026-10-08: "approve F1-F8 as
    recommended"): the table also carries the same quarter a year earlier
    ('compare'), downloaded beside the newest one, so a route's average can be
    stated against it - like for like (season moves the average ~10% within a
    year), in each quarter's own dollars, by sign only, never estimated.
"""
import base64
import json
import logging
import os
import re
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from core.database import DATA_DIR

logger = logging.getLogger('groundwork.airfare')

SOURCE        = 'U.S. DOT Domestic Airline Fares Consumer Report'
CITY_TABLE    = 'https://data.transportation.gov/resource/yj5y-b2ir.json'
AIRPORT_TABLE = 'https://data.transportation.gov/resource/tfrh-tu9e.json'
SHIPPED       = Path(__file__).parent / 'data' / 'dot_airfare.json'
DOWNLOADED    = DATA_DIR / 'dot_airfare.json'
CHECK_EVERY   = timedelta(days=7)    # DOT publishes quarterly; a weekly look is plenty
REQUEST_TIMEOUT = 30
MIN_CITY_ROWS = 1000                 # a real quarter has ~6,000; fewer means a bad download

_lock = threading.Lock()
_cache = {'path': None, 'mtime': None, 'table': None}


# ── The table ───────────────────────────────────────────────────────────────

def _read(path):
    try:
        with open(path, encoding='utf-8') as f:
            t = json.load(f)
        return t if _valid(t) else None
    except (OSError, ValueError):
        return None


def _valid(t):
    return (isinstance(t, dict) and isinstance(t.get('year'), int) and t.get('quarter') in (1, 2, 3, 4)
            and isinstance(t.get('markets'), dict) and len(t.get('city_pairs') or []) >= MIN_CITY_ROWS)


def _newer(a, b):
    return (a['year'], a['quarter']) > (b['year'], b['quarter'])


def table():
    """The newest valid table: the downloaded one if it is newer than the shipped one."""
    best = None
    for path in (SHIPPED, DOWNLOADED):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if _cache['path'] == path and _cache['mtime'] == mtime:
            t = _cache['table']
        else:
            t = _read(path)
        if t and (best is None or _newer(t, best[1])):
            best = (path, t, mtime)
    if best:
        _cache.update(path=best[0], table=best[1], mtime=best[2])
        return best[1]
    return None


def markets():
    """Every city market DOT lists, for the From / To pickers: [{id, name, airports}], by name.
    airports is [[code, name], ...], busiest first; empty when none is known for the city."""
    t = table()
    if not t:
        return {'available': False}
    aps = t.get('airports') or {}
    return {'available': True, 'year': t['year'], 'quarter': t['quarter'], 'source': SOURCE,
            'markets': sorted(({'id': k, 'name': v, 'airports': aps.get(k, [])} for k, v in t['markets'].items()),
                              key=lambda m: m['name'])}


def lookup(from_market, to_market, from_airport='', to_airport=''):
    """The average one-way fare between two DOT city markets, narrowed to the airport pair
    when both airports are given and DOT lists that pair. found: False when DOT has no row."""
    t = table()
    if not t:
        return {'found': False, 'reason': 'no_table'}
    a, b = str(from_market or ''), str(to_market or '')
    if a not in t['markets'] or b not in t['markets']:
        return {'found': False, 'reason': 'unknown_market'}
    if a == b:
        return {'found': False, 'reason': 'same_market'}
    out = {'year': t['year'], 'quarter': t['quarter'], 'source': SOURCE,
           'from_name': t['markets'][a], 'to_name': t['markets'][b]}
    fa, fb = (from_airport or '').strip().upper(), (to_airport or '').strip().upper()
    if fa and fb:
        hit = _airport_pair(t.get('airport_pairs'), a, b, fa, fb)
        if hit:
            return {**out, 'found': True, 'basis': 'airport', 'from_airport': fa, 'to_airport': fb,
                    'fare_one_way': hit[0], 'passengers_per_day': hit[1], 'change': change(t, a, b, fa, fb)}
    hit = _city_pair(t['city_pairs'], a, b)
    if hit:
        return {**out, 'found': True, 'basis': 'city', 'fare_one_way': hit[0], 'passengers_per_day': hit[1],
                'change': change(t, a, b)}
    return {**out, 'found': False, 'reason': 'no_route'}


def _airport_pair(pairs, a, b, fa, fb):
    for ap1, ap2, m1, m2, fare, pax in pairs or []:
        if {(ap1, m1), (ap2, m2)} == {(fa, a), (fb, b)}:
            return fare, pax
    return None


def _city_pair(pairs, a, b):
    for m1, m2, fare, pax in pairs or []:
        if {m1, m2} == {a, b}:
            return fare, pax
    return None


# ── Has the average gone up or down? (item 51) ──────────────────────────────

def _compare_valid(t):
    """The comparison is the same quarter a year earlier (F1), and a real quarter's worth of rows, or nothing."""
    c = t.get('compare')
    return (isinstance(c, dict) and c.get('year') == t['year'] - 1 and c.get('quarter') == t['quarter']
            and len(c.get('city_pairs') or []) >= MIN_CITY_ROWS)


def change(t, a, b, fa='', fb=''):
    """The route's average against the same quarter a year earlier (F1). Like for like (F3): the airport pair when
    both quarters list it, otherwise the city pair for both; a route the earlier quarter does not list is said so,
    never estimated. The direction is the sign alone (F2); dollars are each quarter's own (F4); one-way, per leg (F6);
    both quarters' passengers a day are carried (F7). available: False with no comparison table (F5)."""
    if not _compare_valid(t):
        return {'available': False, 'reason': 'no_compare_table'}
    c = t['compare']
    when = {'year': c['year'], 'quarter': c['quarter']}
    now = then = None
    basis = 'airport'
    if fa and fb:
        now, then = _airport_pair(t.get('airport_pairs'), a, b, fa, fb), _airport_pair(c.get('airport_pairs'), a, b, fa, fb)
    if not (now and then):
        basis = 'city'
        now, then = _city_pair(t['city_pairs'], a, b), _city_pair(c['city_pairs'], a, b)
    if not now:
        return {'available': False, 'reason': 'no_route', **when}
    if not then:
        return {'available': False, 'reason': 'no_earlier_route', **when}
    diff = round(now[0] - then[0], 2)
    return {'available': True, **when, 'basis': basis, 'fare_now': now[0], 'fare_then': then[0],
            'passengers_now': now[1], 'passengers_then': then[1], 'difference': abs(diff),
            'percent': round(abs(diff) / then[0] * 100, 1),
            'direction': 'more' if diff > 0 else ('less' if diff < 0 else 'same')}


def attach_compare(t):
    """F5: download the same quarter a year earlier into t['compare']. True when it read cleanly; on any failure
    the table is left as it was, and the page says nothing about change."""
    try:
        p = build(t['year'] - 1, t['quarter'])
    except Exception as e:     # network, DOT's API
        logger.warning('airfare: year-earlier quarter not downloaded: %s', e)
        p = None
    if not p:
        t.pop('compare', None)
        return False
    t['compare'] = {'year': p['year'], 'quarter': p['quarter'],
                    'city_pairs': p['city_pairs'], 'airport_pairs': p['airport_pairs']}
    return True


# ── The Google Flights search, filled in (item 42) ──────────────────────────
# Google Flights ignores a plain-text ?q= search and opens its front page with
# the user's own local airport. A search opens filled in only when it is given
# as Google's encoded search (tfs=): a small protobuf of the legs, passengers,
# cabin and trip type, base64. Google does not document it; if it stops being
# read, Google shows its front page, which is where the old link already went.

GOOGLE_FLIGHTS = 'https://www.google.com/travel/flights/search'
_IATA = re.compile(r'^[A-Z]{3}$')
_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _varint(n):
    out = bytearray()
    while True:
        b, n = n & 0x7F, n >> 7
        out.append(b | 0x80 if n else b)
        if not n:
            return bytes(out)


def _field(num, value):
    """A protobuf field: bytes are length-delimited, ints are varints."""
    if isinstance(value, int):
        return _varint(num << 3) + _varint(value)
    return _varint(num << 3 | 2) + _varint(len(value)) + value


def google_flights_url(origin, dest, depart, ret=None, travelers=1):
    """The Google Flights search for these airports, dates and travelers, or None if any is not well formed."""
    origin, dest = (origin or '').strip().upper(), (dest or '').strip().upper()
    if not _IATA.match(origin) or not _IATA.match(dest) or origin == dest:
        return None
    if not _DATE.match(depart or '') or (ret and not _DATE.match(ret)):
        return None
    try:
        n = min(9, max(1, int(travelers)))
    except (TypeError, ValueError):
        n = 1

    def leg(date, a, b):
        return _field(3, _field(2, date.encode()) + _field(13, _field(2, a.encode())) + _field(14, _field(2, b.encode())))

    info = leg(depart, origin, dest) + (leg(ret, dest, origin) if ret else b'')
    info += b''.join(_field(8, 1) for _ in range(n))          # passengers: n adults
    info += _field(9, 1) + _field(19, 1 if ret else 2)        # economy; round trip or one way
    tfs = base64.b64encode(info).decode('ascii')
    return f'{GOOGLE_FLIGHTS}?{urllib.parse.urlencode({"tfs": tfs, "hl": "en", "curr": "USD"})}'


# ── Building a table from DOT's two datasets ────────────────────────────────

def _get(url, params):
    """One GET against DOT's open-data API. Separate so the gate can stand in for the network."""
    from core import egress                        # item 8: the one door out
    q = urllib.parse.urlencode(params)
    return egress.get_json(f'{url}?{q}', headers={'User-Agent': 'Groundwork'}, timeout=REQUEST_TIMEOUT)


def latest_quarter():
    rows = _get(CITY_TABLE, {'$select': 'year,quarter', '$order': 'year DESC, quarter DESC', '$limit': 1})
    return int(rows[0]['year']), int(rows[0]['quarter'])


def build(year, quarter):
    """The table for one quarter, as the app stores it, or None if DOT's rows do not read cleanly."""
    where = f'year={int(year)} AND quarter={int(quarter)}'
    city = _get(CITY_TABLE, {'$select': 'citymarketid_1,citymarketid_2,city1,city2,fare,passengers',
                             '$where': where, '$limit': 50000})
    airport = _get(AIRPORT_TABLE, {'$select': 'airport_1,airport_2,citymarketid_1,citymarketid_2,city1,city2,fare,passengers',
                                   '$where': where, '$limit': 50000})
    markets, city_pairs, airport_pairs = {}, [], []
    try:
        for r in city:
            fare = round(float(r['fare']), 2)
            if fare <= 0:
                return None
            markets[r['citymarketid_1']] = r['city1']
            markets[r['citymarketid_2']] = r['city2']
            city_pairs.append([r['citymarketid_1'], r['citymarketid_2'], fare, round(float(r['passengers']), 1)])
        for r in airport:
            fare = round(float(r['fare']), 2)
            if fare <= 0:
                return None
            markets.setdefault(r['citymarketid_1'], r['city1'])
            markets.setdefault(r['citymarketid_2'], r['city2'])
            airport_pairs.append([r['airport_1'].upper(), r['airport_2'].upper(), r['citymarketid_1'],
                                  r['citymarketid_2'], fare, round(float(r['passengers']), 1)])
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    t = {'source': SOURCE, 'year': int(year), 'quarter': int(quarter),
         'retrieved': datetime.now().strftime('%Y-%m-%d'),
         'markets': markets, 'city_pairs': city_pairs, 'airport_pairs': airport_pairs}
    return t if _valid(t) else None


# ── Each city's airports (item 43) ──────────────────────────────────────────
BTS_AIRPORTS = 'https://www.transtats.bts.gov/Download_Lookup.asp?Y11x72=Y_NVecbeg'   # L_AIRPORT: code -> "City, ST: Name"
BTS_T100 = 'https://data.bts.gov/resource/r495-tyji.json'                            # T-100 passengers by origin airport
MIN_PASSENGERS = 2000        # a year's domestic boardings; below this an airfield is not a choice to offer
MIN_SHARE = 0.03             # of the city's busiest airport: keeps a second airport, drops a business-jet field
_MILITARY = re.compile(r'\b(Army|Air Force|AFB|Naval|NAS|Air Reserve|Air National Guard|Joint Base|Marine Corps|AAF|AAB|ANGB|NAF)\b', re.I)
_CIVIL = re.compile(r'\b(International|Regional|Municipal)\b', re.I)     # a joint-use field still serves the public


def _military_only(desc):
    return bool(_MILITARY.search(desc)) and not _CIVIL.search(desc)


def _city_names(loc):
    """'Dallas/Fort Worth, TX (Metropolitan Area)' -> ({'dallas', 'fort worth', 'dallas/fort worth'}, 'TX')."""
    loc = re.sub(r'\s*\(Metropolitan Area\)', '', loc)
    city, st = loc.rsplit(', ', 1)
    return {c.strip().lower() for c in city.split('/')} | {city.strip().lower()}, st.strip()


def build_airports(t, lookup_csv, passengers):
    """{market id: [[code, name], ...]} for the table t, busiest airport first.
    lookup_csv is BTS's L_AIRPORT text; passengers is {code: a year's domestic boardings}."""
    import csv
    import io
    names = {}
    for row in csv.DictReader(io.StringIO(lookup_csv)):
        code, desc = (row.get('Code') or '').strip(), (row.get('Description') or '').strip()
        if re.fullmatch(r'[A-Z]{3}', code) and ':' in desc and ', ' in desc.split(':', 1)[0]:
            names[code] = desc
    markets = {mid: _city_names(m) for mid, m in t['markets'].items()}
    found = {}
    for code, desc in names.items():
        if passengers.get(code, 0) < MIN_PASSENGERS or _military_only(desc):
            continue
        cities, st = _city_names(desc.split(':', 1)[0])
        for mid, (mcities, mst) in markets.items():
            if st == mst and cities & mcities:
                found.setdefault(mid, set()).add(code)
    for a1, a2, m1, m2, *_ in t.get('airport_pairs') or []:     # DOT's own airport-to-city pairs
        for code, mid in ((a1, m1), (a2, m2)):
            if code in names and not _military_only(names[code]):
                found.setdefault(mid, set()).add(code)
    out = {}
    for mid, codes in found.items():
        top = max(passengers.get(c, 0) for c in codes)
        keep = sorted((c for c in codes if passengers.get(c, 0) >= max(MIN_PASSENGERS, MIN_SHARE * top)),
                      key=lambda c: -passengers.get(c, 0))
        if keep:
            out[mid] = [[c, names[c].split(':', 1)[1].strip()] for c in keep]
    return out


def _fetch_airports(t):
    from core import egress                        # item 8: the one door out
    lookup_csv = egress.get(BTS_AIRPORTS, headers={'User-Agent': 'Mozilla/5.0 (Groundwork release build)'},
                            timeout=REQUEST_TIMEOUT).decode('latin-1')
    since = f'{datetime.now().year - 1}-{datetime.now().month:02d}-01'
    rows = _get(BTS_T100, {'$select': 'origin_airport_code,sum(domestic_passengers) as pax',
                           '$where': f"reporting_month >= '{since}'", '$group': 'origin_airport_code', '$limit': 10000})
    passengers = {r['origin_airport_code']: float(r.get('pax') or 0) for r in rows}
    return build_airports(t, lookup_csv, passengers)


def _write(path, t):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(t, f, separators=(',', ':'))
    os.replace(tmp, path)


# ── Keeping it current without a new release ────────────────────────────────

def _checked_path():
    return DATA_DIR / 'dot_airfare_checked.txt'


def refresh(force=False):
    """Download DOT's newest quarter when it is newer than what the app has. At most one look a
    week unless forced. Never raises; the current table stays in use on any failure."""
    if not _lock.acquire(blocking=False):
        return {'updated': False, 'reason': 'already_running'}
    try:
        checked = _checked_path()
        if not force:
            try:
                last = datetime.fromisoformat(checked.read_text(encoding='utf-8').strip())
                if datetime.now() - last < CHECK_EVERY:
                    return {'updated': False, 'reason': 'checked_recently'}
            except (OSError, ValueError):
                pass
        current = table()
        try:
            year, quarter = latest_quarter()
            if current and (year, quarter) <= (current['year'], current['quarter']):
                result = {'updated': False, 'reason': 'already_latest'}
            else:
                t = build(year, quarter)
                if not t:
                    result = {'updated': False, 'reason': 'bad_download'}
                else:
                    t['airports'] = (current or {}).get('airports') or {}     # built at release, not refetched
                    attach_compare(t)                                          # item 51 F5; optional
                    _write(DOWNLOADED, t)
                    result = {'updated': True, 'year': year, 'quarter': quarter}
        except Exception as e:     # network, DOT's API, a full disk: keep what we have
            logger.warning('airfare: refresh failed: %s', e)
            result = {'updated': False, 'reason': 'unreachable'}
        try:
            checked.write_text(datetime.now().isoformat(), encoding='utf-8')
        except OSError:
            pass
        return result
    finally:
        _lock.release()


if __name__ == '__main__':
    # Release step: python -m core.airfare  (writes the newest quarter into the shipped table)
    y, q = latest_quarter()
    t = build(y, q)
    if not t:
        raise SystemExit(f'DOT {y} Q{q} did not read cleanly; shipped table left alone')
    t['airports'] = _fetch_airports(t)
    attach_compare(t)
    _write(SHIPPED, t)
    print(f'shipped table: DOT {y} Q{q}, {len(t["markets"])} markets, '
          f'{len(t["city_pairs"])} city pairs, {len(t["airport_pairs"])} airport pairs, '
          f'airports for {len(t["airports"])} cities; '
          + (f'compared with {t["compare"]["year"]} Q{t["compare"]["quarter"]}' if t.get('compare') else 'NO year-earlier quarter'))
