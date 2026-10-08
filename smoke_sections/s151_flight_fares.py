"""Flight fares without a key (gw 2.0/FLIGHT_FARES.md; Rob 2026-10-07: a user who can't get a price into the budget is
data loss, so 1.x gets it too).

The "Search live flight prices" button called SerpApi with a key the user was told to put in config.json; nobody has
one, so every click failed. Now the button opens Google Flights in the user's own browser (Groundwork sends nothing)
and the fare they pick is typed into tripFlightFare, which fills the same _tripQuoteData.flightTotal the trip budget
already reads.
    F1  no keyed flight search is left: no flight_price.py, no route, no key, no bundling of it
    F2  the link-out carries the route, dates and travelers, and needs both airport codes and a date
    F3  a typed fare becomes the trip's flight total; clearing it keeps a pasted lodging quote
"""
import json
import re
import shutil
import subprocess


def _fn(app, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', app, re.S)
    return m.group(0) if m else ''


RUNNER = r'''
const src = process.argv[1];
const els = {};
const g = id => els[id] || (els[id] = { value: '', style: {}, textContent: '' });
let opened = null; const openExternal = u => { opened = u; };
let _tripQuoteData = null; let budgetRuns = 0; const tripUpdateBudget = () => { budgetRuns++; };
eval(src);
const out = {};
out.round = flightSearchUrl('ORD', 'DEN', '2026-11-01', '2026-11-08', '2');
out.oneway = flightSearchUrl('ORD', 'DEN', '2026-11-01', '', '1');
g('tripAirport').value = 'ord'; g('tripDestAirport').value = 'DEN'; g('tripDepart').value = '';
openFlightSearch(); out.noDate = opened;
g('tripDepart').value = '2026-11-01'; g('tripReturn').value = '2026-11-08'; g('tripTravelers').value = '3';
openFlightSearch(); out.opened = opened;
g('tripAirport').value = 'OR'; opened = null; openFlightSearch(); out.badCode = opened;
_tripQuoteData = { label: 'your quote', hotelTotal: 900, hotelPerNight: null, flightTotal: null };
g('tripFlightFare').value = '612.40'; tripSetFlightFare(); out.typed = JSON.parse(JSON.stringify(_tripQuoteData));
g('tripFlightFare').value = ''; tripSetFlightFare(); out.cleared = JSON.parse(JSON.stringify(_tripQuoteData));
_tripQuoteData = null; g('tripFlightFare').value = '300'; tripSetFlightFare();
g('tripFlightFare').value = ''; tripSetFlightFare(); out.clearedOnly = _tripQuoteData;
g('tripFlightFare').value = '-5'; tripSetFlightFare(); out.negative = _tripQuoteData;
out.budgetRuns = budgetRuns;
console.log(JSON.stringify(out));
'''


def run(ctx):
    check, BASE, c, H, app, html = ctx.check, ctx.BASE, ctx.c, ctx.H, ctx.app_src, ctx.html_src

    # F1
    shipped = {p: (BASE / p).read_text(encoding='utf-8') for p in
               ('server.py', 'static/js/app.js', 'static/index.html',
                'groundwork.spec', 'groundwork_linux.spec', 'groundwork_macos.spec')}
    check('s151 F1 flight_price.py is gone', not (BASE / 'flight_price.py').exists())
    check('s151 F1 no shipped file names the keyed search (flight_price, FLIGHTS_API_KEY, serpapi, the old button)',
          [p for p, t in shipped.items()
           if re.search(r"flight_price['.]|FLIGHTS_API_KEY|serpapi|searchLiveFlightPrice", t, re.I)] == [])
    rules = [str(r) for r in c.application.url_map.iter_rules()]
    check('s151 F1 the /api/trip/flight-price route is gone (an unknown path falls to the page, so read the map)',
          '/api/trip/distance' in ' '.join(rules) and not [r for r in rules if 'flight-price' in r])

    # F2 / F3 in the page
    check('s151 F2 the trip form has the Google Flights button and the fare box wired to their functions',
          'onclick="openFlightSearch()"' in html and 'id="tripFlightFare"' in html
          and 'oninput="tripSetFlightFare()"' in html)
    check('s151 F3 a pasted quote fills the fare box and clearing the quote empties it',
          "g('tripFlightFare').value = clean.flightTotal" in app
          and re.search(r"function _clearTripQuote\(\) \{[^}]*tripFlightFare'\)\.value = ''", app) is not None)
    check('s151 F3 the budget still reads the flight total from _tripQuoteData.flightTotal',
          'transportCost = Math.round(_tripQuoteData.flightTotal)' in app)

    node = shutil.which('node')
    check('s151 node is available to run the fare functions (skip the rest if not)', bool(node))
    if not node:
        return
    src = '\n'.join(_fn(app, n) for n in ('_pbVarint', '_pbField', '_pbStr', 'flightSearchUrl', 'openFlightSearch',
                                          'tripSetFlightFare'))
    check('s151 the fare functions are found in app.js', src.count('\nfunction ') == 6)
    p = subprocess.run([node, '-e', RUNNER, src], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', p.stderr[-800:])
        out = {}
    q = 'https://www.google.com/travel/flights/search?tfs='
    # Item 42: the exact addresses Google was seen to open filled in, 2026-10-07 (Chicago ORD - Denver DEN).
    check('s151 F2 a round trip link is Google\'s encoded search: both legs, two adults (item 42)',
          out.get('round') == q + 'GhoSCjIwMjYtMTEtMDFqBRIDT1JEcgUSA0RFThoaEgoyMDI2LTExLTA4agUSA0RFTnIFEgNPUkRAAUABSAGYAQE%3D&hl=en&curr=USD')
    check('s151 F2 a trip with no return date is one leg, one way, one adult (item 42)',
          out.get('oneway') == q + 'GhoSCjIwMjYtMTEtMDFqBRIDT1JEcgUSA0RFTkABSAGYAQI%3D&hl=en&curr=USD')
    check('s151 F2 the plain-text ?q= search Google ignores is gone (item 42)', 'travel/flights?q=' not in app)
    check('s151 F2 nothing opens without a departure date or with a code that is not 3 letters',
          'noDate' in out and out['noDate'] is None and 'badCode' in out and out['badCode'] is None)
    check('s151 F2 the button opens the form\'s own trip, airport codes upper-cased',
          (out.get('opened') or '').startswith(q) and out.get('opened') != out.get('round'))
    check('s151 F3 a typed fare becomes the flight total and keeps a pasted lodging total',
          out.get('typed') == {'label': 'the fare you entered', 'hotelTotal': 900, 'hotelPerNight': None,
                               'flightTotal': 612.4})
    check('s151 F3 clearing the fare removes the flight total and keeps the lodging quote',
          out.get('cleared') == {'label': 'the fare you entered', 'hotelTotal': 900, 'hotelPerNight': None})
    check('s151 F3 clearing a fare that was the only quote leaves no quote at all',
          'clearedOnly' in out and out['clearedOnly'] is None)
    check('s151 F3 a negative fare is refused, not used',
          'negative' in out and out['negative'] is None and out.get('budgetRuns') == 4)
