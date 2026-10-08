"""Google Flights in Groundwork's own window, filled in (gw 2.0/FLIGHTS_WINDOW.md, item 42; Rob 2026-10-07: "the google
flight link should open in the groundwork app web browser and it should have the airport that the user entered already
in the google flight search").

    W1  the search is Google's encoded form (tfs=), so it opens on the user's airports, dates, travelers and trip type -
        a plain ?q= search is ignored and opens Google's front page on the user's local airport (seen 2026-10-07)
    W2  the server builds the address from the form's fields; nothing else can be opened through this route
    W3  it opens in the bank window's separate private process, given only the address, titled from it;
        a new search replaces the one on screen; "Open in my browser" is the escape hatch
    W4  the button needs both airport codes and a departure date, and says so
"""
import base64
import json
import re
import shutil
import subprocess
import urllib.parse


def _fn(app, name):
    m = re.search(r'\n(async )?function ' + name + r'\(.*?\n\}\n', app, re.S)
    return m.group(0) if m else ''


def _decode(url):
    """The tfs message read back: legs [(date, from, to)], passengers, seat, trip."""
    tfs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['tfs'][0]
    buf = base64.b64decode(tfs)

    def fields(b):
        i, out = 0, []
        while i < len(b):
            key, i = _varint(b, i)
            num, wire = key >> 3, key & 7
            if wire == 0:
                v, i = _varint(b, i)
            else:
                n, i = _varint(b, i)
                v, i = b[i:i + n], i + n
            out.append((num, v))
        return out

    legs, pax, seat, trip = [], 0, None, None
    for num, v in fields(buf):
        if num == 3:
            f = dict(fields(v))
            legs.append((f[2].decode(), dict(fields(f[13]))[2].decode(), dict(fields(f[14]))[2].decode()))
        elif num == 8:
            pax += v == 1
        elif num == 9:
            seat = v
        elif num == 19:
            trip = v
    return legs, pax, seat, trip


def _varint(b, i):
    n = shift = 0
    while True:
        byte = b[i]
        i += 1
        n |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return n, i


def run(ctx):
    check, c, HJ, app, html = ctx.check, ctx.c, ctx.HJ, ctx.app_src, ctx.html_src
    from core import airfare
    import bank_window

    # W1
    rt = airfare.google_flights_url('ord', 'DEN', '2026-11-01', '2026-11-08', 2)
    ow = airfare.google_flights_url('ORD', 'DEN', '2026-11-01', None, 1)
    check('s153 W1 a round trip carries both legs, two adults, economy, round trip',
          rt.startswith('https://www.google.com/travel/flights/search?tfs=')
          and _decode(rt) == ([('2026-11-01', 'ORD', 'DEN'), ('2026-11-08', 'DEN', 'ORD')], 2, 1, 1))
    check('s153 W1 no return date is one leg, one way',
          _decode(ow) == ([('2026-11-01', 'ORD', 'DEN')], 1, 1, 2))
    check('s153 W1 the exact round-trip address Google was seen to open filled in (Chicago ORD - Denver DEN, 2 adults)',
          rt == 'https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjYtMTEtMDFqBRIDT1JEcgUSA0RFThoaEgoyMDI2LTExLTA4'
                'agUSA0RFTnIFEgNPUkRAAUABSAGYAQE%3D&hl=en&curr=USD')
    check('s153 W1 travelers are held to 1-9 adults', _decode(airfare.google_flights_url('ORD', 'DEN', '2026-11-01', None, 40))[1] == 9
          and _decode(airfare.google_flights_url('ORD', 'DEN', '2026-11-01', None, 'x'))[1] == 1)
    check('s153 W1 nothing is built from a bad code, the same airport twice or a malformed date',
          [airfare.google_flights_url(*a) for a in (('OR', 'DEN', '2026-11-01'), ('ORD', 'ORD', '2026-11-01'),
                                                     ('ORD', 'DEN', '11/01/2026'), ('ORD', 'DEN', '2026-11-01', 'soon'),
                                                     ('O/D', 'DEN', '2026-11-01'))] == [None] * 5)
    check('s153 W1 the plain-text ?q= search Google ignores is gone from the page code',
          'travel/flights?q=' not in app and 'flightSearchUrl' not in app)

    # W2 / W3 - the window machinery stood in for: no process is started by the gate
    calls = []
    real = (bank_window.open_bank_window, bank_window.close_bank_window, bank_window.open_in_browser)
    bank_window.open_bank_window = lambda key, url, **k: calls.append(('open', key, url)) or 'opened'
    bank_window.close_bank_window = lambda key: calls.append(('close', key))
    bank_window.open_in_browser = lambda url: calls.append(('browser', url)) or 'opened'
    try:
        body = {'origin': 'ord', 'dest': 'den', 'depart': '2026-11-01', 'return': '2026-11-08', 'travelers': 2}
        r = c.post('/api/trip/flights-window', headers=HJ, data=json.dumps(body))
        check('s153 W3 the search opens in Groundwork\'s window, replacing the one on screen, with the address built here',
              r.status_code == 200 and (r.get_json() or {}).get('data') == {'result': 'opened'}
              and calls == [('close', ('flights', 0)), ('open', ('flights', 0), rt)])
        calls.clear()
        r = c.post('/api/trip/flights-window', headers=HJ, data=json.dumps({**body, 'mode': 'browser'}))
        check('s153 W3 "Open in my browser" opens the same search in the user\'s browser',
              r.status_code == 200 and calls == [('browser', rt)])
        calls.clear()
        r = c.post('/api/trip/flights-window', headers=HJ,
                   data=json.dumps({**body, 'url': 'https://evil.example/', 'origin': 'ORD'}))
        check('s153 W2 a url sent by the page is ignored - only the form fields make the address',
              calls and calls[-1][2] == rt)
        calls.clear()
        r = c.post('/api/trip/flights-window', headers=HJ, data=json.dumps({**body, 'origin': ''}))
        check('s153 W2 without both airports nothing opens and the reason is given',
              r.status_code == 400 and calls == [] and 'airport codes' in ((r.get_json() or {}).get('error') or ''))
    finally:
        bank_window.open_bank_window, bank_window.close_bank_window, bank_window.open_in_browser = real
    check('s153 W3 the window is titled from its address alone: Google Flights, banks unchanged',
          bank_window.window_title(rt) == 'Google Flights'
          and bank_window.window_title('https://www.chase.com/login') == 'Bank website - www.chase.com'
          and bank_window.window_title('https://www.google.com.evil.example/travel/flights') .startswith('Bank website'))
    check('s153 W3 only the address goes to the window process (the bank window\'s one stdin write is unchanged)',
          re.findall(r'stdin\.write\(([^)]*)\)', (ctx.BASE / 'bank_window.py').read_text(encoding='utf-8')) == ["url + '\\n'"])

    # W4
    check('s153 W4 the note under the button says it opens in a Groundwork window, filled in, reading nothing',
          'Opens Google Flights in a Groundwork window with your airports, dates and travelers filled in' in html)
    node = shutil.which('node')
    check('s153 node is available to run the button (skip the rest if not)', bool(node))
    if not node:
        return
    src = _fn(app, '_tripAirportCode') + _fn(app, 'openFlightSearch')
    runner = r'''
const els = {}; const g = id => els[id] || (els[id] = {value: '', style: {}, innerHTML: ''});
const esc = s => String(s); const _gwErr = () => () => {};
const posts = []; const API = {post: async (u, b) => { posts.push([u, b]); return {result: 'opened'}; }};
''' + src + r'''
(async () => {
  g('tripAirport').value = 'ord'; g('tripDestAirport').value = 'DEN';
  await openFlightSearch(); const noDate = posts.length; const said = g('tripFlightSearchResult').innerHTML;
  g('tripDepart').value = '2026-11-01'; g('tripReturn').value = '2026-11-08'; g('tripTravelers').value = '3';
  g('tripRoundTrip').checked = true; await openFlightSearch();
  g('tripRoundTrip').checked = false; await openFlightSearch();
  console.log(JSON.stringify({noDate, said, posts}));
})();'''
    p = subprocess.run([node, '-e', runner], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', p.stderr[-800:])
        out = {}
    check('s153 W4 without a departure date nothing is asked for, and the reason is shown',
          out.get('noDate') == 0 and 'airport codes and your departure date' in out.get('said', ''))
    posts = out.get('posts') or []
    check('s153 W4 the button sends the form\'s trip, codes upper-cased; Round trip unticked sends no return date',
          posts == [['/api/trip/flights-window', {'origin': 'ORD', 'dest': 'DEN', 'depart': '2026-11-01',
                                                   'return': '2026-11-08', 'travelers': 3, 'mode': 'window'}],
                    ['/api/trip/flights-window', {'origin': 'ORD', 'dest': 'DEN', 'depart': '2026-11-01',
                                                   'return': '', 'travelers': 3, 'mode': 'window'}]])
