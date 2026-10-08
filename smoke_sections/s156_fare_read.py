"""The Google Flights fare read (gw 2.0/FLIGHT_FARE_READ.md, item 44; Rob 2026-10-08: "I accept R0 (a) and R1-R8").

    R1  one figure: the price in the label of the Continue button the user clicks, on Google's booking page only
    R2  read on a real click; nothing is watched
    R3  one line back, "fare <amount>", a number over $0 and at most $100,000, checked on both sides
    R4  the trip planner asks before using it; nothing is written without the user's choice
    R5  anything that does not read exactly as expected gives no figure
    R6  the note says what is read, and that the airline's checkout may add taxes or fees (R0 (a))
    R7  the read lives only in flights_window.py and only the Google Flights branch loads it; a bank window gains nothing
"""
import io
import json
import re
import shutil
import subprocess


def _fn(app, name):
    m = re.search(r'\n(?:async )?function ' + name + r'\(.*?\n\}\n', app, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    app, html = ctx.app_src, ctx.html_src
    import flights_window as fw

    # R1 / R5 - the label
    good = 'Continue to book with United, Basic Economy for 690 US dollars'
    check('s156 R1 the price is read from a Continue label exactly as Google words it',
          fw.fare_from_label(good) == 690.0
          and fw.fare_from_label('Continue to book with Delta, Main for 1,234.50 US dollars') == 1234.5)
    check('s156 R5 any other wording, currency, zero, an over-limit price or not text gives no figure',
          [fw.fare_from_label(s) for s in (
              'Continue to book with United, Basic Economy for 690 euros',
              'Book with United for 690 US dollars',
              'Continue to book with United for 0 US dollars',
              'Continue to book with United for 250,000 US dollars',
              'Continue to book with United for 690 US dollars and more',
              None, 690)] == [None] * 7)

    # R3 - the line back
    check('s156 R3 the line back is "fare <amount>" and reads back the same',
          fw.fare_line(690) == 'fare 690.00' and fw.parse_fare_line('fare 690.00\n') == 690.0)
    check('s156 R3 Groundwork accepts nothing else on that line',
          [fw.parse_fare_line(s) for s in ('fare 690', 'fare 690.00 extra', 'fare abc', 'ready', 'fare 0.00',
                                           'fare 999999.99', 'fare -5.00', '')] == [None] * 8)

    # R1 / R2 - the page api checks the page before reading
    class _W:
        def __init__(self, url):
            self.url = url

        def get_current_url(self):
            return self.url

    out = io.StringIO()
    api = fw.FareApi(out=out)
    api._window = _W('https://www.google.com/travel/flights/booking?tfs=x')
    api.fare_label(good)
    api._window = _W('https://www.united.com/en/us/traveler/choose-travelers')
    api.fare_label(good)
    api._window = _W('https://www.google.com.evil.example/travel/flights/booking')
    api.fare_label(good)
    api._window = _W('http://www.google.com/travel/flights/booking')
    api.fare_label(good)
    check('s156 R1 the label is read only while the window is on Google\'s booking page (https, exact host)',
          out.getvalue() == 'fare 690.00\n')
    s = fw.PAGE_SCRIPT
    check('s156 R2 the page script acts only on a real click on a Continue button on the booking page',
          'e.isTrusted' in s and "location.hostname !== 'www.google.com'" in s and "'/travel/flights/booking'" in s
          and 'button[aria-label^="Continue to book with "]' in s and s.count('getAttribute(') == 1)

    # Groundwork's side: the watcher keeps only valid fares
    class _P:
        def __init__(self, lines):
            self.stdout = io.StringIO(''.join(lines))

    fw.clear()
    fw.watch(_P(['ready\n', 'fare 9999999.00\n', 'whatever the page said\n', 'fare 690.00\n', 'fare abc\n']))
    import time
    for _ in range(50):
        if fw.latest()['fare'] is not None:
            break
        time.sleep(0.02)
    check('s156 R3 Groundwork keeps the last valid fare line and ignores everything else', fw.latest()['fare'] == 690.0)
    r = c.get('/api/trip/flights-window/fare', headers=H).get_json()['data']
    check('s156 R4 GET /api/trip/flights-window/fare gives the fare to show the user', r['fare'] == 690.0 and r['at'])
    c.post('/api/trip/flights-window/fare/clear', headers=HJ, data='{}')
    check('s156 R4 using or declining it clears it', c.get('/api/trip/flights-window/fare', headers=H).get_json()['data']['fare'] is None)

    # R7 - where the read lives
    bw = (BASE / 'bank_window.py').read_text(encoding='utf-8')
    fsrc = (BASE / 'flights_window.py').read_text(encoding='utf-8')
    check('s156 R7 bank_window.py itself still has no page read (no js_api, evaluate_js or page script)',
          not re.search(r'js_api\s*=|evaluate_js|PAGE_SCRIPT', bw.split('"""', 2)[2]))
    branch = re.search(r'    if flights:\n(.*?)\n    else:\n', bw, re.S)
    check('s156 R7 only the Google Flights branch loads flights_window',
          bw.count('import flights_window') == 1 and branch is not None and 'import flights_window' in branch.group(1)
          and "flights = window_title(url) == 'Google Flights'" in bw)
    check('s156 R7 flights_window imports nothing of Groundwork\'s and nothing that talks to a network',
          not re.search(r'^\s*(from|import)\s+(server|core|urllib\.request|http|socket|requests|sqlite3|sqlalchemy)\b',
                        fsrc, re.M))
    check('s156 R3 the window process writes only fare lines to Groundwork',
          re.findall(r'self\._out\.write\((.*)\)$', fsrc, re.M) == ["fare_line(amount) + '\\n'"]
          and 'sys.stdout.write' not in fsrc)
    for spec in ('groundwork.spec', 'groundwork_linux.spec', 'groundwork_macos.spec'):
        check(f's156 R7 {spec} bundles flights_window', "'flights_window'" in (BASE / spec).read_text(encoding='utf-8'))

    # R7 mutations - each must be caught by the checks above
    caught_bank = bool(re.search(r'js_api\s*=|evaluate_js|PAGE_SCRIPT',
                                 bw.replace('            width=1100,\n', '            width=1100,\n            js_api=object(),\n', 1)
                                 .split('"""', 2)[2]))
    leaked = fsrc.replace("self._out.write(fare_line(amount) + '\\n')", "self._out.write(label + '\\n')", 1)
    caught_leak = re.findall(r'self\._out\.write\((.*)\)$', leaked, re.M) != ["fare_line(amount) + '\\n'"]
    clickless = s.replace('if (!e.isTrusted) return;', '')
    caught_click = 'e.isTrusted' not in clickless
    check('s156 R7 mutations caught: a read added to a bank window, the label sent back, a read without a real click',
          caught_bank and caught_leak and caught_click and leaked != fsrc and clickless != s)

    # R4 / R6 - the trip planner
    check('s156 R6 the note says what is read and that the airline may add taxes or fees',
          'Groundwork reads one thing from it: the price on the Continue button you click, which it asks you to confirm.' in html
          and "The airline's checkout may add taxes or fees" in html and 'Groundwork reads nothing from it' not in html)
    check('s156 R0 a used Google price is labelled as Google\'s in the budget, never as final',
          "(from Google Flights; the airline may add taxes or fees)" in app)
    node = shutil.which('node')
    check('s156 node is available to run the prompt (skip the rest if not)', bool(node))
    if not node:
        return
    src = ''.join(_fn(app, n) for n in ('googleFareMessage', '_offerGoogleFare', 'tripUseGoogleFare', 'tripDeclineGoogleFare'))
    runner = r'''
const els = {}; const g = id => els[id] || (els[id] = {value: '', style: {}, innerHTML: '', textContent: '', focus() { this.focused = true; }});
const esc = s => String(s); const fmt = n => '$' + Number(n).toFixed(2); const _gwErr = () => () => {};
const posts = []; const API = {post: (u) => { posts.push(u); return Promise.resolve({}); }};
let _tripQuoteData = {label: 'your quote', hotelTotal: 900}; let budget = 0; const tripUpdateBudget = () => { budget++; };
let _googleFareTrip = {travelers: 2, roundTrip: true};
''' + src + r'''
const out = {};
out.msg = googleFareMessage(690, {travelers: 2, roundTrip: true});
out.one = googleFareMessage(345, {travelers: 1, roundTrip: false});
_offerGoogleFare(690);
out.offered = [/Use \$690\.00/.test(els.tripFlightSearchResult.innerHTML), /Enter the airline's total/.test(els.tripFlightSearchResult.innerHTML), g('tripFlightFare').value, JSON.stringify(_tripQuoteData)];
tripUseGoogleFare(690);
out.used = [g('tripFlightFare').value, _tripQuoteData, budget, posts.slice()];
_tripQuoteData = null; g('tripFlightFare').value = ''; posts.length = 0;
tripDeclineGoogleFare();
out.declined = [g('tripFlightFare').value, _tripQuoteData, !!els.tripFlightFare.focused, posts.slice()];
console.log(JSON.stringify(out));'''
    p = subprocess.run([node, '-e', runner], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', p.stderr[-800:])
        o = {}
    check('s156 R0 the prompt names the price as Google\'s, for the whole trip, and says the airline may add taxes or fees',
          o.get('msg') == "Google Flights showed $690.00 for this trip (2 travelers, round trip). The airline's checkout may add taxes or fees."
          and o.get('one', '').startswith('Google Flights showed $345.00 for this trip (1 traveler, one way).'))
    check('s156 R4 the prompt offers Use and Enter the airline\'s total, and changes nothing until one is chosen',
          o.get('offered') == [True, True, '', json.dumps({'label': 'your quote', 'hotelTotal': 900}, separators=(',', ':'))])
    check('s156 R4 Use fills the fare box and the budget, labelled Google Flights, keeps a pasted lodging total, clears the fare',
          o.get('used') == ['690.00', {'label': 'Google Flights', 'hotelTotal': 900, 'flightTotal': 690}, 1,
                            ['/api/trip/flights-window/fare/clear']])
    check('s156 R4 Enter the airline\'s total writes nothing, puts the cursor in the fare box and clears the fare',
          o.get('declined') == ['', None, True, ['/api/trip/flights-window/fare/clear']])
