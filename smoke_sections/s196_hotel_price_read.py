"""Item 59 P3's optional half: the stay total the person clicks on Google Hotels, read in Groundwork's window and offered
before use (gw 2.0/TRIP_REAL_PRICES.md P3; built 2026-10-11, Rob: "build 58 and 59"). Item 44's shape, for hotels.

The fixture is a real click measured on Google Hotels 2026-10-11 (KAYAK's row for a Denver hotel, 3 nights).
"""
import io
import json
import re


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    app = ctx.app_src
    import hotels_window as hw
    import bank_window

    real = ['Visit site for KAYAK.com', ['$87', '$100', '$301'], True, '3 nights with taxes + fees']
    check('s196 the real click reads as the stay total and its nights', hw.total_from_row(*real) == (301.0, 3))
    bad = {
        'no stay-total heading': (real[0], real[1], False, real[3]),
        'two prices': (real[0], ['$87', '$301'], True, real[3]),
        'a total that does not agree with the nightly price': (real[0], ['$87', '$100', '$450'], True, real[3]),
        'another button': ('Book now', real[1], True, real[3]),
        'no nights': (real[0], real[1], True, ''),
        'a price that is not a price': (real[0], ['$87', 'about $100', '$301'], True, real[3]),
    }
    got = {k: hw.total_from_row(*v) for k, v in bad.items()}
    check(f's196 anything that does not read exactly so gives no figure ({got})', all(v is None for v in got.values()))
    check('s196 one line back, numbers only, checked again on Groundwork\'s side',
          hw.parse_hotel_line(hw.hotel_line(301.0, 3)) == (301.0, 3) and hw.parse_hotel_line('hotel 301.00 3 KAYAK') is None
          and hw.parse_hotel_line('hotel 999999.00 3') is None and hw.parse_hotel_line('fare 301.00') is None)

    # the window process: only on Google's travel pages
    out = io.StringIO()
    api = hw.HotelApi(out)

    class W:
        def __init__(self, u): self.u = u
        def get_current_url(self): return self.u
    api._window = W('https://www.google.com/travel/search?q=x')
    api.hotel_row(*real)
    api._window = W('https://www.kayak.com/hotels')
    api.hotel_row(*real)
    check('s196 the window writes the line only from Google\'s travel pages', out.getvalue() == 'hotel 301.00 3\n')

    src = (BASE / 'hotels_window.py').read_text(encoding='utf-8')
    bw = (BASE / 'bank_window.py').read_text(encoding='utf-8')
    check('s196 the page script acts only on a real click of a "Visit site for" button on Google\'s travel pages',
          'if (!e.isTrusted) return;' in hw.PAGE_SCRIPT and "location.hostname !== 'www.google.com'" in hw.PAGE_SCRIPT
          and '[aria-label^="Visit site for "]' in hw.PAGE_SCRIPT)
    check('s196 the read lives in hotels_window.py, loaded only for a Google Hotels window; bank_window.py still reads no page',
          bw.count('import hotels_window') == 1 and "hotels = window_title(url) == 'Google Hotels'" in bw
          and not re.search(r'js_api\s*=|evaluate_js|PAGE_SCRIPT', bw.split('"""', 2)[2])
          and not re.search(r'^\s*(from|import)\s+(server|core|urllib\.request|http|socket|requests|sqlite3|sqlalchemy)\b', src, re.M)
          and re.findall(r'self\._out\.write\((.*)\)$', src, re.M) == ["hotel_line(*got) + '\\n'"])
    check('s196 the hotels window is titled Google Hotels (it said "Bank website - www.google.com")',
          bank_window.window_title('https://www.google.com/travel/search?q=hotels+in+Denver') == 'Google Hotels'
          and bank_window.window_title('https://www.google.com/travel/flights?q=x') == 'Google Flights')
    for spec in ('groundwork.spec', 'groundwork_linux.spec', 'groundwork_macos.spec'):
        check(f's196 {spec} bundles hotels_window', "'hotels_window'" in (BASE / spec).read_text(encoding='utf-8'))

    # Groundwork's side: offered, used only on the tap, then forgotten
    hw.clear()
    hw._latest.update(total=301.0, nights=3, at='2026-10-11T10:00:00')
    got = c.get('/api/trip/hotels-window/price', headers=H).get_json()['data']
    c.post('/api/trip/hotels-window/price/clear', headers=HJ, data='{}')
    after = c.get('/api/trip/hotels-window/price', headers=H).get_json()['data']
    check('s196 the price is offered, and using or declining it clears it', got['total'] == 301.0 and got['nights'] == 3 and after['total'] is None)
    use = app.split('function tripUseGoogleHotel(total) {')[1].split('\n}\n')[0]
    check('s196 used only on the tap, named as Google\'s with taxes and fees, in the hotel line\'s source',
          "hotelLabel: 'Google Hotels'" in use and "Google Hotels' stay total with taxes and fees (you chose it)" in app
          and 'onclick="tripUseGoogleHotel(' in app and "The hotel\\'s own checkout may differ." in app)
