"""DOT average airfare replaces the $220 guess (gw 2.0/DOT_AIRFARE.md, item 41; Rob 2026-10-07: "replace the $220 with
the DOT average", "go with A and ship the table", "grab the latest data and not dependent on the user to always update").

    D1  a DOT table ships with the app and reads cleanly
    D2  a route is looked up on the computer: by city, narrowed to the airport pair when DOT lists it; no row, no fare
    D3  a newer DOT quarter is downloaded without a new release; a bad or failed download keeps the current table;
        the download carries nothing about the user's trip
    D4  the trip budget's flight line is the DOT average x legs x travelers; no DOT figure leaves flights out and says so;
        the $220 guess is gone
"""
import json
import re
import shutil
import subprocess


def _fn(app, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', app, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, app = ctx.check, ctx.c, ctx.H, ctx.app_src
    from core import airfare as af

    # D1
    shipped = af._read(af.SHIPPED)
    check('s152 D1 the shipped DOT table reads cleanly (a quarter, 1,000+ city pairs, markets named)',
          shipped is not None and len(shipped['markets']) > 100 and shipped['airport_pairs'])
    check('s152 D1 core/ is bundled whole, so the table ships (groundwork.spec datas)',
          "('core', 'core')" in (ctx.BASE / 'groundwork.spec').read_text(encoding='utf-8'))
    for f in (af.DOWNLOADED, af._checked_path()):
        f.unlink(missing_ok=True)
    t = af.table()
    check('s152 D1 with nothing downloaded, the app uses the shipped table',
          t and (t['year'], t['quarter']) == (shipped['year'], shipped['quarter']))

    # D2
    ids = {v: k for k, v in t['markets'].items()}
    chi, den = ids.get('Chicago, IL'), ids.get('Denver, CO')
    row = next((p for p in t['city_pairs'] if {p[0], p[1]} == {chi, den}), None)
    there, back = af.lookup(chi, den), af.lookup(den, chi)
    check('s152 D2 Chicago-Denver is DOT\'s city-pair average, one way, with its quarter and source',
          row is not None and there.get('found') and there['basis'] == 'city' and there['fare_one_way'] == row[2]
          and there['year'] == t['year'] and there['source'] == af.SOURCE)
    check('s152 D2 DOT routes have no direction: Denver-Chicago is the same average',
          back.get('found') and back['fare_one_way'] == there['fare_one_way'] and back['from_name'] == 'Denver, CO')
    ap = next((p for p in t['airport_pairs'] if {p[2], p[3]} == {chi, den}), None)
    if ap:
        a_chi = ap[0] if ap[2] == chi else ap[1]
        a_den = ap[1] if ap[2] == chi else ap[0]
        by_ap = af.lookup(den, chi, a_den.lower(), a_chi)
        check('s152 D2 both airports given and listed: the airport-pair average is used',
              by_ap.get('basis') == 'airport' and by_ap['fare_one_way'] == ap[4] and by_ap['from_airport'] == a_den)
    check('s152 D2 an airport DOT does not list for that city falls back to the city average',
          af.lookup(chi, den, 'ZZZ', 'YYY').get('basis') == 'city')
    pairs = {frozenset(p[:2]) for p in t['city_pairs']}
    lone = next(((a, b) for a in t['markets'] for b in t['markets'] if a < b and frozenset((a, b)) not in pairs
                 and not any({p[2], p[3]} == {a, b} for p in t['airport_pairs'])), None)
    check('s152 D2 a route DOT does not list returns no fare (never a guess)',
          lone and af.lookup(*lone) == {**{k: af.lookup(*lone)[k] for k in ('year', 'quarter', 'source', 'from_name', 'to_name')},
                                        'found': False, 'reason': 'no_route'})
    check('s152 D2 an unknown market, or the same city at both ends, returns no fare',
          af.lookup('nope', den) == {'found': False, 'reason': 'unknown_market'}
          and af.lookup(den, den) == {'found': False, 'reason': 'same_market'})
    r = c.get(f'/api/trip/airfare?from={chi}&to={den}', headers=H)
    check('s152 D2 GET /api/trip/airfare answers from the table', (r.get_json() or {}).get('data') == there)
    m = (c.get('/api/trip/airfare-markets', headers=H).get_json() or {}).get('data') or {}
    check('s152 D2 GET /api/trip/airfare-markets lists every DOT city by name, with the quarter',
          m.get('available') and len(m['markets']) == len(t['markets']) and m['year'] == t['year']
          and {'id': chi, 'name': 'Chicago, IL'} in [{'id': x['id'], 'name': x['name']} for x in m['markets']])

    # D3 - DOT's API stood in for, so the gate never touches the network
    real_get, calls = af._get, []
    nq = (t['year'] + (t['quarter'] == 4), t['quarter'] % 4 + 1)

    def fake(newer=True, fare='123.45', city_rows=None, fail=False):
        def _g(url, params):
            calls.append((url, dict(params)))
            if fail:
                raise OSError('offline')
            if '$where' not in params:
                y, q = nq if newer else (t['year'], t['quarter'])
                return [{'year': str(y), 'quarter': str(q)}]
            if url == af.CITY_TABLE:
                n = city_rows if city_rows is not None else 1200
                return [{'citymarketid_1': chi, 'citymarketid_2': str(90000 + i), 'city1': 'Chicago, IL',
                         'city2': f'Town {i}, ZZ', 'fare': fare, 'passengers': '11'} for i in range(n - 1)] + \
                       [{'citymarketid_1': chi, 'citymarketid_2': den, 'city1': 'Chicago, IL', 'city2': 'Denver, CO',
                         'fare': fare, 'passengers': '2000'}]
            return [{'airport_1': 'ORD', 'airport_2': 'DEN', 'citymarketid_1': chi, 'citymarketid_2': den,
                     'city1': 'Chicago, IL', 'city2': 'Denver, CO', 'fare': fare, 'passengers': '1500'}]
        return _g

    try:
        af._get = fake(newer=False)
        res = af.refresh(force=True)
        check('s152 D3 DOT has nothing newer: nothing downloaded', res == {'updated': False, 'reason': 'already_latest'}
              and not af.DOWNLOADED.exists())
        af._get = fake(fail=True)
        res = af.refresh(force=True)
        check('s152 D3 DOT unreachable: the shipped table stays in use',
              res['reason'] == 'unreachable' and af.table()['year'] == shipped['year'])
        af._get = fake(fare='-5')
        check('s152 D3 a download with a bad fare is refused', af.refresh(force=True)['reason'] == 'bad_download'
              and not af.DOWNLOADED.exists())
        af._get = fake(city_rows=10)
        check('s152 D3 a download too small to be a real quarter is refused',
              af.refresh(force=True)['reason'] == 'bad_download' and not af.DOWNLOADED.exists())
        calls.clear()
        af._get = fake()
        res = af.refresh(force=True)
        check('s152 D3 a newer quarter is downloaded and used at once, without a new release',
              res == {'updated': True, 'year': nq[0], 'quarter': nq[1]} and af.table()['quarter'] == nq[1]
              and af.lookup(chi, den)['fare_one_way'] == 123.45)
        sent = json.dumps(calls)
        check('s152 D3 the download asks DOT only for a whole quarter - no city, airport or route of the user\'s',
              len(calls) == 3 and all(set(p) <= {'$select', '$order', '$limit', '$where'} for _, p in calls)
              and 'Chicago' not in sent and chi not in sent and 'ORD' not in sent.replace('airport_1', ''))
        calls.clear()
        res = (c.post('/api/trip/airfare-refresh', headers=H).get_json() or {}).get('data')
        check('s152 D3 the page\'s refresh looks at most once a week', res == {'updated': False, 'reason': 'checked_recently'}
              and calls == [])
    finally:
        af._get = real_get
        for f in (af.DOWNLOADED, af._checked_path()):
            f.unlink(missing_ok=True)
    check('s152 D3 the gate leaves the shipped table in use', af.table()['quarter'] == shipped['quarter'])

    # D4
    check('s152 D4 the $220 per person guess is gone from the trip budget',
          '220 * travelers' not in app and 'AI will refine`' not in app)
    check('s152 D4 no DOT figure leaves flights out of the total and says so',
          "transportCost = 0;\n      transportNote = 'Not in the total yet" in app)
    html = ctx.html_src
    check('s152 D4 the Fly form has From / To cities from DOT\'s list, optional airports and a Round trip box',
          all(s in html for s in ('id="tripFromCity" list="airfareMarketList"', 'id="tripToCity" list="airfareMarketList"',
                                  '<datalist id="airfareMarketList">', 'id="tripRoundTrip" checked', 'id="tripAirfareNote"')))
    node = shutil.which('node')
    check('s152 node is available to run the trip math (skip the rest if not)', bool(node))
    if not node:
        return
    src = _fn(app, 'airfareEstimate')
    runner = src + r'''
const f = {found: true, fare_one_way: 217.27};
console.log(JSON.stringify([airfareEstimate(f, true, '2'), airfareEstimate(f, false, 1), airfareEstimate(f, true, 0),
                            airfareEstimate({found: false}, true, 2), airfareEstimate(null, true, 2)]));'''
    p = subprocess.run([node, '-e', runner], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', p.stderr[-800:])
        out = [None] * 5
    check('s152 D4 round trip: outbound + return, each the DOT average, times the travelers ($217.27 x 2 x 2)',
          out[0] == {'fare': 217.27, 'legs': 2, 'travelers': 2, 'total': 869.08})
    check('s152 D4 one way: one leg', out[1] == {'fare': 217.27, 'legs': 1, 'travelers': 1, 'total': 217.27})
    check('s152 D4 no travelers entered counts one', out[2] and out[2]['travelers'] == 1)
    check('s152 D4 no DOT figure gives no estimate', out[3] is None and out[4] is None)
