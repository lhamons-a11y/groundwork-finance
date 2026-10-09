"""Has the average fare gone up or down? (gw 2.0/FARE_CHANGE.md, item 51; Rob 2026-10-08: "approve F1-F8 as recommended").

    F1  compared with the same quarter a year earlier - never the quarter before (season moves the average ~10%)
    F2  the dollar and percent difference with both figures; more / less / the same by the sign alone; no verdict words
    F3  like for like: the airport pair only when both quarters list it, else the city pair for both; a route the
        earlier quarter does not list is said so, never estimated
    F4  each quarter's own dollars, named as not adjusted for inflation
    F5  the year-earlier quarter ships in the table and is downloaded beside a newer one; if that fails, nothing is said
    F6  one-way, per leg - not multiplied into the trip
    F7  both quarters' passengers a day are shown
"""
import copy
import json
import re
import shutil
import subprocess


def _fn(app, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', app, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, app = ctx.check, ctx.app_src
    from core import airfare as af

    shipped = af._read(af.SHIPPED)
    check('s163 F5 the shipped table carries the same quarter a year earlier, a real quarter of rows',
          af._compare_valid(shipped) and shipped['compare']['year'] == shipped['year'] - 1
          and shipped['compare']['quarter'] == shipped['quarter'])

    ids = {v: k for k, v in shipped['markets'].items()}
    chi, den = ids['Chicago, IL'], ids['Denver, CO']
    r = af.lookup(chi, den)
    ch = r.get('change') or {}
    now_f, then_f = r['fare_one_way'], af._city_pair(shipped['compare']['city_pairs'], chi, den)[0]
    check('s163 F1/F2 a real route: the year-earlier average, the difference and its sign follow from the two figures',
          ch.get('available') and ch['basis'] == 'city' and ch['fare_now'] == now_f and ch['fare_then'] == then_f
          and ch['difference'] == abs(round(now_f - then_f, 2))
          and ch['direction'] == ('more' if now_f > then_f else 'less' if now_f < then_f else 'same')
          and ch['percent'] == round(abs(round(now_f - then_f, 2)) / then_f * 100, 1))

    # A fixture table: every case, independent of DOT's numbers.
    city = [['1', '2', 200.0, 50.0]] + [['1', str(100 + i), 100.0, 11.0] for i in range(af.MIN_CITY_ROWS)]
    t = {'year': 2026, 'quarter': 1, 'markets': {'1': 'A', '2': 'B', '3': 'C'},
         'city_pairs': city + [['1', '3', 150.0, 20.0]], 'airport_pairs': [['AAA', 'BBB', '1', '2', 210.0, 30.0]],
         'compare': {'year': 2025, 'quarter': 1, 'city_pairs': [['2', '1', 180.0, 40.0]] + city[1:],
                     'airport_pairs': [['BBB', 'AAA', '2', '1', 190.0, 25.0]]}}
    a = af.change(t, '1', '2', 'AAA', 'BBB')
    check('s163 F3 both quarters list the airport pair: compared airport to airport (DOT\'s rows have no direction)',
          a == {'available': True, 'year': 2025, 'quarter': 1, 'basis': 'airport', 'fare_now': 210.0, 'fare_then': 190.0,
                'passengers_now': 30.0, 'passengers_then': 25.0, 'difference': 20.0, 'percent': 10.5, 'direction': 'more'})
    t2 = copy.deepcopy(t); t2['compare']['airport_pairs'] = []
    b = af.change(t2, '1', '2', 'AAA', 'BBB')
    check('s163 F3 the earlier quarter lacks the airport pair: both fall back to the city pair',
          b['basis'] == 'city' and (b['fare_now'], b['fare_then'], b['direction']) == (200.0, 180.0, 'more'))
    check('s163 F3 a route the earlier quarter does not list is said so, never estimated',
          af.change(t, '1', '3') == {'available': False, 'reason': 'no_earlier_route', 'year': 2025, 'quarter': 1})
    t3 = copy.deepcopy(t); t3['compare']['city_pairs'][0][2] = 220.0
    t4 = copy.deepcopy(t); t4['compare']['city_pairs'][0][2] = 200.0
    check('s163 F2 less and the same are decided by the sign alone (no band calls a small change "about the same")',
          af.change(t3, '1', '2')['direction'] == 'less' and af.change(t4, '1', '2')['direction'] == 'same'
          and af.change(t4, '1', '2')['difference'] == 0.0)
    t5 = copy.deepcopy(t); t5['compare']['city_pairs'][0][2] = 199.99
    check('s163 F2 a $0.01 difference is stated as $0.01',
          af.change(t5, '1', '2')['difference'] == 0.01 and af.change(t5, '1', '2')['direction'] == 'more')
    tq = copy.deepcopy(t); tq['compare'].update(year=2025, quarter=4)
    tn = copy.deepcopy(t); del tn['compare']
    check('s163 F1 a quarter-before table is never compared; with no year-earlier table nothing is said (F5)',
          af.change(tq, '1', '2') == {'available': False, 'reason': 'no_compare_table'}
          and af.change(tn, '1', '2') == {'available': False, 'reason': 'no_compare_table'})

    # F5: the year-earlier download fails - the newer quarter is still used, and nothing is said about change.
    real_get = af._get
    nq = (shipped['year'] + (shipped['quarter'] == 4), shipped['quarter'] % 4 + 1)

    def fake(url, params):
        if '$where' not in params:
            return [{'year': str(nq[0]), 'quarter': str(nq[1])}]
        if f'year={nq[0] - 1} ' in params['$where']:
            raise OSError('offline')
        if url == af.CITY_TABLE:
            return [{'citymarketid_1': chi, 'citymarketid_2': str(90000 + i), 'city1': 'Chicago, IL', 'city2': f'Town {i}, ZZ',
                     'fare': '99', 'passengers': '11'} for i in range(1200)] + \
                   [{'citymarketid_1': chi, 'citymarketid_2': den, 'city1': 'Chicago, IL', 'city2': 'Denver, CO',
                     'fare': '123.45', 'passengers': '2000'}]
        return []
    try:
        for f in (af.DOWNLOADED, af._checked_path()):
            f.unlink(missing_ok=True)
        af._get = fake
        res = af.refresh(force=True)
        lk = af.lookup(chi, den)
        check('s163 F5 the year-earlier download fails: the newer quarter is used, and no change is stated',
              res.get('updated') and lk['fare_one_way'] == 123.45
              and lk['change'] == {'available': False, 'reason': 'no_compare_table'})
    finally:
        af._get = real_get
        for f in (af.DOWNLOADED, af._checked_path()):
            f.unlink(missing_ok=True)
    check('s163 F5 the gate leaves the shipped table in use', af.table()['quarter'] == shipped['quarter']
          and af._compare_valid(af.table()))

    # The page's own line, rendered.
    check('s163 the DOT note carries the change line', '${airfareChangeLine(d) ?' in _fn(app, '_airfareNoteHtml'))
    node = shutil.which('node')
    check('s163 node is available', bool(node))
    if node:
        js = _fn(app, 'fmt') + _fn(app, 'airfareChangeLine') + r'''
const d = {year: 2026, quarter: 1};
const base = {available: true, year: 2025, quarter: 1, basis: 'city', fare_now: 287.40, fare_then: 273.20,
              passengers_now: 1234.4, passengers_then: 1100, difference: 14.20, percent: 5.2, direction: 'more'};
console.log(JSON.stringify([
  airfareChangeLine({...d, change: base}),
  airfareChangeLine({...d, change: {...base, basis: 'airport', fare_now: 250, difference: 23.2, percent: 8.5, direction: 'less'}}),
  airfareChangeLine({...d, change: {...base, fare_now: 273.20, difference: 0, percent: 0, direction: 'same'}}),
  airfareChangeLine({...d, change: {available: false, reason: 'no_earlier_route', year: 2025, quarter: 1}}),
  airfareChangeLine({...d, change: {available: false, reason: 'no_compare_table'}}),
  airfareChangeLine({...d})]));'''
        p = subprocess.run([node, '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=60)
        out = json.loads(p.stdout.strip() or '[]') if p.returncode == 0 else []
        check('s163 F2/F4/F7 more: both figures, both quarters, inflation named, both quarters\' passengers',
              out[:1] == ["Compared with a year earlier, between these two cities, all their airports: the $287.40 average "
                          "one-way fare in 2026 Q1 is $14.20 (5.2%) more than in 2025 Q1, the same quarter a year earlier "
                          "($273.20). Both are in each quarter's own dollars, not adjusted for inflation; about 1,234 "
                          "passengers a day in 2026 Q1, 1,100 in 2025 Q1."])
        check('s163 F2/F3 less (airport to airport) and the same read by sign; a missing earlier route is said so; '
              'no comparison table says nothing',
              len(out) == 6 and 'between these two airports: the $250.00 average one-way fare in 2026 Q1 is $23.20 (8.5%) less than' in out[1]
              and 'is the same as in 2025 Q1, the same quarter a year earlier ($273.20)' in out[2]
              and out[3] == "DOT has no average for this route in 2025 Q1, so there's nothing to compare it with."
              and out[4] == '' and out[5] == '')
        words = re.compile(r'\b(high|higher|low|lower|cheap|cheaper|expensive|sharp|sharply|only|just|good|bad|deal|book now|should|surge|spike)\b', re.I)
        check('s163 F2/F6 no verdict words, no advice, and nothing multiplied into the trip (no travelers, legs or total)',
              out and not any(words.search(x) for x in out) and not any(re.search(r'traveler|×|round trip|total', x) for x in out))
