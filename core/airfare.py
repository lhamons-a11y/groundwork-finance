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
    """Every city market DOT lists, for the From / To pickers: [{id, name}], by name."""
    t = table()
    if not t:
        return {'available': False}
    return {'available': True, 'year': t['year'], 'quarter': t['quarter'], 'source': SOURCE,
            'markets': sorted(({'id': k, 'name': v} for k, v in t['markets'].items()), key=lambda m: m['name'])}


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
        for ap1, ap2, m1, m2, fare, pax in t.get('airport_pairs') or []:
            if {(ap1, m1), (ap2, m2)} == {(fa, a), (fb, b)}:
                return {**out, 'found': True, 'basis': 'airport', 'from_airport': fa, 'to_airport': fb,
                        'fare_one_way': fare, 'passengers_per_day': pax}
    for m1, m2, fare, pax in t['city_pairs']:
        if {m1, m2} == {a, b}:
            return {**out, 'found': True, 'basis': 'city', 'fare_one_way': fare, 'passengers_per_day': pax}
    return {**out, 'found': False, 'reason': 'no_route'}


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
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f'{url}?{q}', headers={'User-Agent': 'Groundwork'})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
        return json.loads(r.read().decode('utf-8'))


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
    _write(SHIPPED, t)
    print(f'shipped table: DOT {y} Q{q}, {len(t["markets"])} markets, '
          f'{len(t["city_pairs"])} city pairs, {len(t["airport_pairs"])} airport pairs')
