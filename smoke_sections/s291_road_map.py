"""The road map (gw 2.0/ROAD_MAP.md; Rob 2026-11-05: "Yes, build it"). Routes on a real map: tests/road_map_fixture/delaware.tar.

    M1  a real route, on the real engine; the router holds nothing afterward
    M2  without a map, or with a route it cannot make, the estimate stands, and the answer says which it is
    M3  a route shorter than the straight line is not believed
    M4  the manifest can only name Groundwork's own download folder
    M5  a download is believed only after its fingerprint and a real route; a bad one leaves the old map as it was
    M6  nothing goes out until the person presses, and a request that says nothing does nothing
    M7  once a month at most, only with a map installed and the box on; without a map, nothing is asked
    M8  the credit is where the licence asks; the page says which figure it is; a saved trip's figures don't move
"""
import gzip
import hashlib
import importlib.util
import json
import shutil
import time
from pathlib import Path


class _Stream:
    """Stands in for one response from the download folder."""
    def __init__(self, data, status=200):
        self.data, self.at, self.status = data, 0, status

    def read(self, n):
        out = self.data[self.at:self.at + n]
        self.at += n
        return out

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    import trip_distance as td
    from core import egress, road_map as rm
    from core.database import AppSetting, db_session

    post = lambda p, b: c.post(p, headers=HJ, data=json.dumps(b))
    data = lambda r: (r.get_json() or {}).get('data')
    fixture = BASE / 'tests' / 'road_map_fixture' / 'delaware.tar'
    wilmington, lewes = {'lat': 39.74, 'lon': -75.55}, {'lat': 38.77, 'lon': -75.14}
    rm.remove()

    check('s291 M1 the engine is installed where the gate runs: this section must not pass by skipping',
          importlib.util.find_spec('valhalla') is not None and fixture.is_file())

    # ── M2: no map ──
    with db_session() as s:
        for key, v in (('wilmington', wilmington), ('lewes', lewes), ('toronto', {'lat': 43.65, 'lon': -79.38})):
            s.query(AppSetting).filter_by(key=td.CACHE_PREFIX + key).delete()
            s.add(AppSetting(key=td.CACHE_PREFIX + key, value=json.dumps(v)))
        s.commit()
    none = td.get_drive_distance('Wilmington', 'Lewes')
    check(f'''s291 M2 no map: the straight line plus 25%, and it says so ({none})''',
          none['method'] == 'estimate' and none['live'] and none['miles'] == round(td._haversine_miles(39.74, -75.55, 38.77, -75.14) * 1.25))
    check('s291 M2 no map: route() answers None', rm.route(wilmington, lewes) is None)
    pts = td.get_route_points('Wilmington', 'Lewes')
    check('s291 M2 no map: the printed map gets the estimate and no route line', pts['method'] == 'estimate' and 'shape' not in pts)

    def place(path=fixture, version='20260101'):
        d = rm._dir()
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, d / rm.MAP_FILE)
        (d / rm.STATE_FILE).write_text(json.dumps({'version': version, 'data_date': '2026-01-01'}), encoding='utf-8')

    # ── M1: a real route ──
    place()
    t0 = time.time()
    r = rm.route(wilmington, lewes)
    check(f"s291 M1 a real route on the real engine, Wilmington to Lewes by road ({r and round(r['miles'], 1)} mi, {time.time() - t0:.2f}s)",
          r is not None and 80 < r['miles'] < 100 and r['data_date'] == '2026-01-01')
    check('s291 M1 the route line starts and ends at the two places, and is kept short',
          abs(r['shape'][0][0] - 39.74) < 0.1 and abs(r['shape'][-1][0] - 38.77) < 0.1 and 2 <= len(r['shape']) <= rm.MAX_SHAPE_POINTS)
    road = td.get_drive_distance('Wilmington', 'Lewes')
    check(f'''s291 M2 with the map: the road route, and it says so ({road})''',
          road['method'] == 'road' and road['live'] and road['miles'] == round(r['miles']) and 'on this computer' in road['source'])
    pts = td.get_route_points('Wilmington', 'Lewes')
    check('s291 M2 with the map: the printed map gets the road line and the same miles',
          pts['method'] == 'road' and pts['miles'] == road['miles'] and len(pts['shape']) > 1)
    far = td.get_drive_distance('Wilmington', 'Toronto')
    check(f'''s291 M2 a place off the map: no route, so the estimate stands and says so ({far['method']})''',
          far['method'] == 'estimate' and far['live'])

    # ── M3 ──
    real_route = rm._route_on
    rm._route_on = lambda *a: (10.0, [[39.74, -75.55], [38.77, -75.14]])
    check('s291 M3 a route shorter than the straight line is not believed', rm.route(wilmington, lewes) is None)
    rm._route_on = real_route

    # ── M4 ──
    good = {'version': '20260201', 'data_date': '2026-02-01', 'url': rm.DOWNLOAD_BASE + 'us-roads.tar.gz', 'sha256': 'a' * 64, 'bytes': 5}
    check('s291 M4 a good manifest is read', rm.clean_manifest(good)['version'] == '20260201')
    for bad in ({**good, 'url': 'https://example.com/us-roads.tar.gz'}, {**good, 'url': rm.DOWNLOAD_BASE + '../../x'},
                {**good, 'sha256': 'nope'}, {**good, 'bytes': 0}, {**good, 'bytes': rm.MAX_DOWNLOAD + 1}, {'version': '1'}, 'text', None):
        check(f's291 M4 refused: {str(bad)[:70]}', rm.clean_manifest(bad) is None)
    check('s291 M4 is_newer goes by the version', rm.is_newer(good, {'version': '20260101'}) and not rm.is_newer(good, {'version': '20260201'}))

    # ── M5: the whole install, the file coming through a stand-in for the door ──
    gz = gzip.compress(fixture.read_bytes(), 1)
    sha = hashlib.sha256(gz).hexdigest()
    m = {**good, 'sha256': sha, 'bytes': len(gz)}
    real_stream, real_check = egress.open_stream, rm.CHECK_ROUTE
    egress.open_stream = lambda url, headers=None, timeout=30: _Stream(gz)
    rm.CHECK_ROUTE = {'from': (39.74, -75.55), 'to': (38.77, -75.14), 'min': 80, 'max': 100}
    try:
        rm._worker({**m, 'sha256': 'b' * 64})
        check('s291 M5 a file that does not match its fingerprint is refused, and the old map stays',
              rm.job()['state'] == 'error' and 'fingerprint' in rm.job()['error'] and rm.installed()['version'] == '20260101'
              and not (rm._dir() / rm.PART_FILE).exists())
        rm.CHECK_ROUTE = {'from': (39.74, -75.55), 'to': (38.77, -75.14), 'min': 500, 'max': 600}
        rm._worker(m)
        check('s291 M5 a map that fails its test route is refused, and the old map stays',
              rm.job()['state'] == 'error' and 'test route' in rm.job()['error'] and rm.installed()['version'] == '20260101'
              and not (rm._dir() / rm.NEW_FILE).exists())
        rm.CHECK_ROUTE = {'from': (39.74, -75.55), 'to': (38.77, -75.14), 'min': 80, 'max': 100}
        rm._cancel.clear()
        rm._worker(m)
        check('s291 M5 a good file replaces the map, and leaves no download behind',
              rm.job()['state'] == 'done' and rm.installed()['version'] == '20260201' and rm.installed()['data_date'] == '2026-02-01'
              and not (rm._dir() / rm.PART_FILE).exists() and not (rm._dir() / rm.NEW_FILE).exists())
        check('s291 M5 and it routes', rm.route(wilmington, lewes) is not None)
        rm._cancel.set()
        rm._worker({**m, 'version': '20260301'})
        check('s291 M5 a cancelled download changes nothing, and can carry on later',
              rm.job()['state'] == 'idle' and rm.installed()['version'] == '20260201')
        rm._cancel.clear()
        half = len(gz) // 2
        part = rm._dir() / rm.PART_FILE
        part.write_bytes(gz[:half])
        seen = {}

        def resumed(url, headers=None, timeout=30):
            seen.update(headers or {})
            return _Stream(gz[half:], status=206)
        egress.open_stream = resumed
        rm._worker({**m, 'version': '20260401'})
        check(f"s291 M5 a download carries on where it stopped ({seen.get('Range')})",
              seen.get('Range') == f'bytes={half}-' and rm.installed()['version'] == '20260401')
        part.write_bytes(gz[:half])
        egress.open_stream = lambda url, headers=None, timeout=30: _Stream(gz, status=200)
        rm._worker({**m, 'version': '20260501'})
        check('s291 M5 and starts over when the server does not carry on', rm.installed()['version'] == '20260501')
    finally:
        egress.open_stream, rm.CHECK_ROUTE = real_stream, real_check

    # ── M6 ──
    calls = []
    real_fetch = rm.fetch_manifest
    rm.fetch_manifest = lambda: calls.append(1) or None
    try:
        got = data(c.get('/api/trip/road-map', headers=H))
        check('s291 M6 reading the status asks the internet nothing', not calls and got['installed'] and got['credit_url'].endswith('/copyright'))
        for p in ('manifest', 'download', 'cancel', 'remove', 'auto'):
            check(f'''s291 M6 POST road-map/{p} with nothing said does nothing''', post(f'/api/trip/road-map/{p}', {}).status_code == 400)
        check('s291 M6 and asked nothing', not calls and rm.installed() is not None)
        r2 = post('/api/trip/road-map/download', {'confirm': True})
        check('s291 M6 with no manifest to read, the download says so', r2.status_code == 400 and calls)
    finally:
        rm.fetch_manifest = real_fetch
    app = ctx.app_src
    check('s291 M6 the page asks first and shows the size before any download',
          "confirmAction(r.status.installed ? 'Download the newer map?'" in app and '${size} MB to download' in app
          and "roadMapDo('download')" in app.split('async function roadMapAsk()')[1].split('async function roadMapAuto')[0])
    src = (BASE / 'server.py').read_text(encoding='utf-8')
    check('s291 M6 the address comes from the manifest, never the page',
          "m = road_map.fetch_manifest()" in src.split('def road_map_download')[1].split('@trip_bp')[0]
          and 'request.json' in src.split('def road_map_download')[1].split('@trip_bp')[0]
          and "get('url')" not in src.split('def road_map_download')[1].split('@trip_bp')[0])

    # ── M7 ──
    with db_session() as s:
        s.query(AppSetting).filter_by(key=rm.CHECKED_KEY).delete()
        s.query(AppSetting).filter_by(key=rm.AUTO_KEY).delete()
        s.commit()
    check('s291 M7 the box is on by default, and the first look is due', rm.auto_on() and rm.check_due())
    check('s291 M7 then not again for 30 days', not rm.check_due() and not rm.check_due(time.time() + 29 * 86400))
    check('s291 M7 and again after them', rm.check_due(time.time() + 31 * 86400))
    with db_session() as s:
        s.query(AppSetting).filter_by(key=rm.CHECKED_KEY).delete()
        s.commit()
    check('s291 M7 the box turned off: nothing is asked',
          data(post('/api/trip/road-map/auto', {'auto': False}))['auto'] is False and not rm.check_due())
    post('/api/trip/road-map/auto', {'auto': True})
    check('s291 M7 only the planner opening looks, and only with the visit word',
          "'/api/trip/road-map?visit=1'" in app and "request.args.get('visit') == '1'" in src)

    data(post('/api/trip/road-map/remove', {'confirm': True}))
    check('s291 M7 Remove takes it off this computer, on Windows too, where an open map could not be deleted',
          not rm._dir().exists() and rm.installed() is None)
    check('s291 M7 without a map, nothing is asked', not rm.check_due())
    after = td.get_drive_distance('Wilmington', 'Lewes')
    check('s291 M2 with the map removed, the estimate is back at once', after['method'] == 'estimate')

    # ── M8 ──
    pr = (BASE / 'static' / 'js' / 'print.js').read_text(encoding='utf-8')
    check('s291 M8 the printed itinerary prints the credit and its address, for the estimate too',
          'Map data from OpenStreetMap, under the Open Database License: openstreetmap.org/copyright.' in pr)
    check('s291 M8 the Settings card and the planner carry the credit', app.count('${_ROAD_CREDIT}') >= 3)
    check('s291 M8 the planner says which figure it is',
          "onRoads ? '(road route)' : distLive ? '(estimated route)'" in app and "It doesn't take ferries." in app)
    site = (BASE / 'Website' / 'website.py').read_text(encoding='utf-8')
    notices = (BASE / 'THIRD_PARTY_NOTICES.md').read_text(encoding='utf-8')
    check('s291 M8 the Privacy page says what the download is and sends', '<strong>The road map</strong>' in site and 'Nothing about you' in site.split('<strong>The road map</strong>')[1][:300])
    check('s291 M8 the notices name the data and the engine', 'Open Database License' in notices and 'Valhalla' in notices)
    build = (BASE / 'scripts' / 'build_road_map.py').read_text(encoding='utf-8')
    check('s291 M8 the build keeps the licence notice and its method with the file',
          'ODbL' in build and "shutil.copy(__file__, out / 'build_road_map.py')" in build)
    check('s291 M8 a saved trip does not read the map: its figures stay until the person updates them',
          'road_map' not in (BASE / 'core' / 'trips.py').read_text(encoding='utf-8'))
    for spec in ('groundwork.spec', 'groundwork_linux.spec', 'groundwork_macos.spec'):
        text = (BASE / spec).read_text(encoding='utf-8')
        check(f'''s291 M8 {spec} ships the router''', 'spec_engine.road_parts()' in text and "'core.road_map'" in text and '*_road_binaries' in text)
