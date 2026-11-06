"""The road map: exact driving miles from a map on this computer (gw 2.0/ROAD_MAP.md; Rob 2026-11-05: "Yes, build it").

An optional download, made of OpenStreetMap's main US roads, read by Valhalla in this process. Nothing about a trip leaves
the computer to route it. Without the map, or when a trip cannot be routed on it, trip_distance.py keeps its straight-line
estimate and says which one the figure is.

    download    only on the person's press; a file is checked against the fingerprint the manifest names, then against a
                real route, before it replaces anything
    update      once installed, and while "Keep the map current" is on: the planner asks at most once every 30 days
    memory      the router is opened for one route and closed, so it holds nothing between trips (measured: 243 MB while
                routing, back to 52 MB after)
"""
import gc
import gzip
import hashlib
import importlib.util
import json
import logging
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('groundwork.road_map')

DOWNLOAD_BASE = 'https://groundworkfinance.app/static/download/road-map/'
MANIFEST_URL = DOWNLOAD_BASE + 'us-roads.json'
USER_AGENT = 'Groundwork'
MAP_FILE = 'us-roads.tar'
STATE_FILE = 'installed.json'
PART_FILE = 'us-roads.tar.gz.part'
NEW_FILE = 'us-roads.new.tar'
MAX_DOWNLOAD = 2 * 1024 ** 3
CHECK_EVERY_DAYS = 30
AUTO_KEY = 'road_map_auto'
CHECKED_KEY = 'road_map_checked'
MAX_SHAPE_POINTS = 240
CREDIT = 'Map data from OpenStreetMap, under the Open Database License'
CREDIT_URL = 'https://www.openstreetmap.org/copyright'
# A route the whole country's map must be able to answer, within these miles, before it is used
CHECK_ROUTE = {'from': (39.96, -83.00), 'to': (39.10, -84.51), 'min': 95, 'max': 125}   # Columbus to Cincinnati, OH

_route_lock = threading.Lock()          # one route at a time, and never while the file is being replaced
_job_lock = threading.Lock()
_job = {'state': 'idle', 'done': 0, 'total': 0, 'error': '', 'version': ''}
_cancel = threading.Event()


def _dir():
    from core.database import DATA_DIR
    return Path(DATA_DIR) / 'road_map'


def engine_available():
    """False where no tested engine exists (an Intel Mac): the app runs, and the estimate stays."""
    return importlib.util.find_spec('valhalla') is not None


def installed():
    """What is installed, or None. The file and its record must both be there."""
    try:
        d = _dir()
        if not (d / MAP_FILE).is_file():
            return None
        info = json.loads((d / STATE_FILE).read_text(encoding='utf-8'))
        return info if isinstance(info, dict) else None
    except (OSError, ValueError):
        return None


def _hav(a, b):
    from math import asin, cos, radians, sin, sqrt
    la1, lo1, la2, lo2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 3958.8 * asin(sqrt(h))


def decode_shape(encoded):
    """Valhalla's route line (six-decimal polyline) as [[lat, lon], ...]."""
    out, i, lat, lon = [], 0, 0, 0
    while i < len(encoded):
        for k in (0, 1):
            shift = result = 0
            while True:
                b = ord(encoded[i]) - 63
                i += 1
                result |= (b & 31) << shift
                shift += 5
                if b < 32:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if k == 0:
                lat += delta
            else:
                lon += delta
        out.append([round(lat / 1e6, 4), round(lon / 1e6, 4)])
    return out


def _thin(points, limit=MAX_SHAPE_POINTS):
    if len(points) <= limit:
        return points
    step = (len(points) - 1) / (limit - 1)
    return [points[round(i * step)] for i in range(limit)]


def _route_on(path, a, b):
    """(miles, shape) on this map file. Raises if it cannot be routed. The router does not outlive the call."""
    from valhalla import Actor
    from valhalla.config import get_config
    actor = Actor(get_config(tile_extract=str(path), tile_dir=''))
    try:
        r = actor.route({'locations': [{'lat': a[0], 'lon': a[1]}, {'lat': b[0], 'lon': b[1]}], 'costing': 'auto',
                         'units': 'miles', 'directions_type': 'none'})
        r = json.loads(r) if isinstance(r, str) else r
        return float(r['trip']['summary']['length']), decode_shape(r['trip']['legs'][0]['shape'])
    finally:
        del actor
        gc.collect()


def route(origin, destination):
    """{miles, shape, data_date} for two {lat, lon} places, or None: no map, no engine, or no route between them.
    Never raises into the caller. A route shorter than the straight line is not a route, so it is not believed."""
    info = installed()
    if not info or not engine_available():
        return None
    a, b = (origin['lat'], origin['lon']), (destination['lat'], destination['lon'])
    try:
        with _route_lock:
            miles, shape = _route_on(_dir() / MAP_FILE, a, b)
    except Exception as e:                                     # outside the map, or no road near: the estimate stands
        logger.info('road_map: no route: %s', e)
        return None
    if miles <= 0 or miles < _hav(a, b) * 0.95:
        logger.warning('road_map: a route of %.1f miles is shorter than the straight line', miles)
        return None
    return {'miles': miles, 'shape': _thin(shape), 'data_date': info.get('data_date', '')}


# ── The manifest ────────────────────────────────────────────────────────────

def clean_manifest(raw):
    """The manifest's fields, or None. The file can only come from Groundwork's own download folder."""
    if not isinstance(raw, dict):
        return None
    try:
        out = {'version': str(raw['version'])[:20], 'data_date': str(raw.get('data_date', ''))[:10],
               'url': str(raw['url']), 'sha256': str(raw['sha256']).lower(), 'bytes': int(raw['bytes']),
               'tar_bytes': int(raw.get('tar_bytes') or 0)}
    except (KeyError, TypeError, ValueError):
        return None
    good = (out['version'] and out['url'].startswith(DOWNLOAD_BASE) and '..' not in out['url']
            and len(out['sha256']) == 64 and all(c in '0123456789abcdef' for c in out['sha256'])
            and 0 < out['bytes'] <= MAX_DOWNLOAD)
    return out if good else None


def fetch_manifest():
    from core import egress
    try:
        return clean_manifest(egress.get_json(MANIFEST_URL, headers={'User-Agent': USER_AGENT}, timeout=8, limit=65536))
    except Exception as e:
        logger.info('road_map: manifest unavailable: %s', e)
        return None


# ── Download, check, replace ───────────────────────────────────────────────

def job():
    with _job_lock:
        return dict(_job)


def _set(**kw):
    with _job_lock:
        _job.update(kw)


def _hash_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h


def _fetch(m, part):
    """The file to part, carrying on from what is already there when the server allows it. False if cancelled."""
    from core import egress
    have = part.stat().st_size if part.exists() else 0
    if have >= m['bytes']:
        part.unlink()
        have = 0
    headers = {'User-Agent': USER_AGENT}
    if have:
        headers['Range'] = f'bytes={have}-'
    with egress.open_stream(m['url'], headers=headers, timeout=30) as r:
        if have and getattr(r, 'status', 200) != 206:   # the server started over, so must we
            have = 0
        mode = 'ab' if have else 'wb'
        with open(part, mode) as f:
            done = have
            _set(done=done)
            while True:
                if _cancel.is_set():
                    return False
                chunk = r.read(1024 * 1024)
                if not chunk:
                    break
                done += len(chunk)
                if done > m['bytes']:
                    raise ValueError('larger than the manifest says')
                f.write(chunk)
                _set(done=done)
    return True


def _install(m):
    d = _dir()
    d.mkdir(parents=True, exist_ok=True)
    part, new = d / PART_FILE, d / NEW_FILE
    if not _fetch(m, part):
        return 'cancelled'
    _set(state='checking')
    if part.stat().st_size != m['bytes'] or _hash_file(part).hexdigest() != m['sha256']:
        part.unlink(missing_ok=True)
        raise ValueError('the download did not match its fingerprint')
    _set(state='unpacking')
    with gzip.open(part, 'rb') as src, open(new, 'wb') as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
    _set(state='checking')
    c = CHECK_ROUTE
    miles, _ = _route_on(new, c['from'], c['to'])
    if not c['min'] <= miles <= c['max']:
        raise ValueError(f'the map gave {miles:.0f} miles on its test route')
    with _route_lock:                                   # no route is reading the old file while it is replaced
        (d / NEW_FILE).replace(d / MAP_FILE)
        (d / STATE_FILE).write_text(json.dumps({'version': m['version'], 'data_date': m['data_date'], 'sha256': m['sha256'],
                                                'bytes': m['bytes'], 'installed_at': datetime.now().isoformat(timespec='seconds')}),
                                    encoding='utf-8')
    part.unlink(missing_ok=True)
    return 'done'


def _worker(m):
    try:
        result = _install(m)
        _set(state='idle' if result == 'cancelled' else 'done', error='')
    except Exception as e:                              # the old map, if any, is untouched
        logger.warning('road_map: download failed: %s', e)
        (_dir() / NEW_FILE).unlink(missing_ok=True)
        _set(state='error', error=str(e)[:160])


def start(m):
    """Begin the download of a clean manifest. False if one is already running."""
    with _job_lock:
        if _job['state'] in ('downloading', 'checking', 'unpacking'):
            return False
        _job.update(state='downloading', done=0, total=m['bytes'], error='', version=m['version'])
    _cancel.clear()
    threading.Thread(target=_worker, args=(m,), daemon=True, name='road-map').start()
    return True


def enough_room(m):
    """Room for the download and the unpacked map side by side."""
    d = _dir()
    d.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(d).free > m['bytes'] + (m['tar_bytes'] or m['bytes'] * 3) + 100 * 1024 ** 2


def cancel():
    _cancel.set()


def remove():
    """Takes the map off this computer. The estimate takes over at once."""
    with _route_lock:
        shutil.rmtree(_dir(), ignore_errors=True)
    _set(state='idle', done=0, total=0, error='')


# ── Keeping it current ──────────────────────────────────────────────────────

def _setting(session, key, default=None):
    from core.database import AppSetting
    row = session.query(AppSetting).filter_by(key=key).first()
    return row.value if row else default


def _put(session, key, value):
    from core.database import AppSetting
    row = session.query(AppSetting).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        session.add(AppSetting(key=key, value=value))


def auto_on():
    from core.database import db_session
    with db_session() as s:
        return _setting(s, AUTO_KEY, '1') == '1'


def set_auto(on):
    from core.database import db_session
    with db_session() as s:
        _put(s, AUTO_KEY, '1' if on else '0')
        s.commit()


def is_newer(m, info):
    return bool(m and info and str(m['version']) > str(info.get('version', '')))


def check_due(now=None):
    """Only with a map installed and "Keep the map current" on, and at most every 30 days. Without a map, nothing is asked."""
    if not installed() or not auto_on():
        return False
    from core.database import db_session
    now = now or time.time()
    with db_session() as s:
        try:
            last = float(_setting(s, CHECKED_KEY, '0') or 0)
        except ValueError:
            last = 0
        if now - last < CHECK_EVERY_DAYS * 86400:
            return False
        _put(s, CHECKED_KEY, str(now))
        s.commit()
    return True


def update_in_background():
    """What the planner calls on opening: asks once a month, and fetches a newer map if there is one."""
    if not check_due():
        return

    def go():
        m = fetch_manifest()
        if is_newer(m, installed()) and enough_room(m):
            start(m)
    threading.Thread(target=go, daemon=True, name='road-map-check').start()


def status():
    info = installed()
    j = job()
    return {'engine': engine_available(), 'installed': bool(info), 'version': (info or {}).get('version', ''),
            'data_date': (info or {}).get('data_date', ''), 'bytes': (info or {}).get('bytes', 0), 'auto': auto_on(),
            'job': j, 'credit': CREDIT, 'credit_url': CREDIT_URL}
