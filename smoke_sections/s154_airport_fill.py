"""Picking a city fills its airport (gw 2.0/AIRPORT_FILL.md, item 43; Rob 2026-10-07: "when someone enters the city in
the trip planner and select fly the airport code should appear ... if their is two different airports for that city
then the user should be asked which airport ... the DOT flight average should appear near the google flight area").

    A1  each DOT city's airports ship in the table, busiest first, from BTS's airport list and passenger counts;
        an airfield with no passengers to speak of, or a military-only field, is not offered
    A2  one airport is filled in; several ask which, and the one picked is filled in; a code the user typed is kept
    A3  the DOT average sits beside the Google Flights button and says to compare it with Google's fares
    A4  a DOT refresh keeps the airports
"""
import json
import re
import shutil
import subprocess


def _fn(app, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', app, re.S)
    return m.group(0) if m else ''


LOOKUP = '''Code,Description
"ORD","Chicago, IL: Chicago O'Hare International"
"MDW","Chicago, IL: Chicago Midway International"
"PWK","Chicago/Wheeling, IL: Chicago Executive"
"DEN","Denver, CO: Denver International"
"APA","Denver, CO: Centennial"
"CSG","Columbus, GA: Columbus Airport"
"LSF","Columbus, GA: Lawson AAF"
"CHS","Charleston, SC: Charleston AFB/International"
"DAL","Dallas, TX: Dallas Love Field"
"DFW","Dallas/Fort Worth, TX: Dallas/Fort Worth International"
'''


def run(ctx):
    check, app, html = ctx.check, ctx.app_src, ctx.html_src
    from core import airfare as af

    # A1 - the rule, on a small table
    t = {'markets': {'1': 'Chicago, IL', '2': 'Denver, CO', '3': 'Columbus, GA', '4': 'Charleston, SC',
                     '5': 'Dallas/Fort Worth, TX'}, 'airport_pairs': []}
    pax = {'ORD': 30e6, 'MDW': 9e6, 'PWK': 40e3, 'DEN': 49e6, 'APA': 17e3, 'CSG': 60e3, 'LSF': 30e3, 'CHS': 3e6,
           'DAL': 8e6, 'DFW': 40e6}
    got = af.build_airports(t, LOOKUP, pax)
    check('s154 A1 a city\'s airports, busiest first, named as BTS names them',
          got.get('1') == [['ORD', "Chicago O'Hare International"], ['MDW', 'Chicago Midway International']])
    check('s154 A1 a business-jet field beside a big airport is not offered (Centennial beside DEN; Chicago Executive)',
          [c for c, _ in got.get('2', [])] == ['DEN'])
    check('s154 A1 a military-only field is not offered; a joint-use international airport is',
          [c for c, _ in got.get('3', [])] == ['CSG'] and [c for c, _ in got.get('4', [])] == ['CHS'])
    check('s154 A1 a DOT city named for two cities matches both ("Dallas/Fort Worth")',
          [c for c, _ in got.get('5', [])] == ['DFW', 'DAL'])
    shipped = af._read(af.SHIPPED)
    aps = shipped.get('airports') or {}
    ids = {v: k for k, v in shipped['markets'].items()}
    check('s154 A1 the shipped table carries airports for nearly every DOT city',
          len(aps) >= 0.95 * len(shipped['markets']))
    check('s154 A1 Chicago offers O\'Hare and Midway; Denver is DEN alone',
          [c for c, _ in aps.get(ids['Chicago, IL'], [])] == ['ORD', 'MDW']
          and [c for c, _ in aps.get(ids['Denver, CO'], [])] == ['DEN'])
    m = {x['name']: x for x in af.markets()['markets']}
    check('s154 A1 the city list sent to the page carries each city\'s airports',
          [c for c, _ in m['Chicago, IL']['airports']] == ['ORD', 'MDW'])

    # A4
    real_get = af._get
    try:
        nq = (shipped['year'] + (shipped['quarter'] == 4), shipped['quarter'] % 4 + 1)
        city = [{'citymarketid_1': '1', 'citymarketid_2': str(100 + i), 'city1': 'A, ZZ', 'city2': f'B{i}, ZZ',
                 'fare': '100', 'passengers': '11'} for i in range(1200)]
        af._get = lambda url, p: ([{'year': str(nq[0]), 'quarter': str(nq[1])}] if '$where' not in p
                                  else city if url == af.CITY_TABLE else [])
        for f in (af.DOWNLOADED, af._checked_path()):
            f.unlink(missing_ok=True)
        af.refresh(force=True)
        check('s154 A4 a refreshed DOT quarter keeps the shipped airports', (af._read(af.DOWNLOADED) or {}).get('airports') == aps)
    finally:
        af._get = real_get
        for f in (af.DOWNLOADED, af._checked_path()):
            f.unlink(missing_ok=True)

    # A3
    note_at = html.find('id="tripAirfareNote"')
    check('s154 A3 the DOT average sits right after the Google Flights row, not under the airports',
          html.find('onclick="openFlightSearch()"') < note_at < html.find('Opens Google Flights in a Groundwork window')
          and html.count('id="tripAirfareNote"') == 1)
    check('s154 A3 it says to compare it with the fares Google Flights shows',
          'compare it with the fares Google Flights shows for your dates' in app)
    check('s154 A2 each city box has its airport chooser, and both cities fill their airport',
          all(s in html for s in ('id="tripFromAirportChoice"', 'id="tripToAirportChoice"',
                                  "oninput=\"tripCityChanged('from')\"", "oninput=\"tripCityChanged('to')\"")))

    # A2 - run in Node
    node = shutil.which('node')
    check('s154 node is available to run the airport fill (skip the rest if not)', bool(node))
    if not node:
        return
    src = _fn(app, '_airfareMarketId') + _fn(app, 'tripCityChanged') + _fn(app, 'tripPickAirport')
    runner = r'''
const els = {}; const g = id => els[id] || (els[id] = {value: '', style: {}, innerHTML: '', dataset: {}});
const esc = s => String(s); let runs = 0; const tripUpdateBudget = () => { runs++; };
let _airfareMarkets = {byName: {'Chicago, IL': '1', 'Denver, CO': '2', 'Nowhere, ZZ': '9'},
  airports: {'1': [['ORD', "Chicago O'Hare International"], ['MDW', 'Chicago Midway International']], '2': [['DEN', 'Denver International']], '9': []}};
''' + src + r'''
const out = {};
g('tripToCity').value = 'Denver, CO'; tripCityChanged('to'); out.one = [g('tripDestAirport').value, g('tripToAirportChoice').style.display];
g('tripFromCity').value = 'Chicago, IL'; tripCityChanged('from');
out.asked = [g('tripAirport').value, g('tripFromAirportChoice').style.display, (g('tripFromAirportChoice').innerHTML.match(/tripPickAirport/g) || []).length,
             /Which airport\?/.test(g('tripFromAirportChoice').innerHTML)];
tripPickAirport('from', 'MDW'); out.picked = [g('tripAirport').value, g('tripFromAirportChoice').style.display];
g('tripToCity').value = 'Nowhere, ZZ'; tripCityChanged('to'); out.none = g('tripDestAirport').value;
g('tripDestAirport').value = 'XNA'; g('tripDestAirport').dataset.auto = '';
g('tripToCity').value = 'Denver, CO'; tripCityChanged('to'); out.typedKept = g('tripDestAirport').value;
console.log(JSON.stringify(out));'''
    p = subprocess.run([node, '-e', runner], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', p.stderr[-800:])
        out = {}
    check('s154 A2 a city with one airport fills it in, nothing asked', out.get('one') == ['DEN', 'none'])
    check('s154 A2 a city with two airports asks which, with a button for each, and fills nothing yet',
          out.get('asked') == ['', '', 2, True])
    check('s154 A2 the airport picked is filled in and the question goes away', out.get('picked') == ['MDW', 'none'])
    check('s154 A2 a city with no known airport leaves an auto-filled code empty for the user to type',
          out.get('none') == '')
    check('s154 A2 a code the user typed is never replaced by a city pick', out.get('typedKept') == 'XNA')
