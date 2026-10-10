"""Item 59: the trip budget uses real prices, or says it has none (gw 2.0/TRIP_REAL_PRICES.md P1-P8, RULED
2026-10-09; built on "build all items that have been ruled on").

    P1  no model prices any line, nothing is "live", and an old saved AI budget says what it was
    P2  GSA's per-diem rates for lodging and meals, by place and season; a place GSA doesn't list says so
    P3  Google Hotels for the trip, in Groundwork's window (the address built on the server)
    P4  activities are the person's own figure, or left out and said
    P5  every line says its source; the old $140 / $45 / $50 defaults are gone
"""
import io
import json
import re
import zipfile


def _tiny_xlsx(fy, rows):
    """A minimal GSA-shaped spreadsheet: a title row, a header, the standard rate, then the rows."""
    strings, idx = [], {}

    def s(v):
        if v not in idx:
            idx[v] = len(strings)
            strings.append(v)
        return idx[v]
    lines = [[('A', f'FY{fy} Per Diem Rates - Effective October 1, {fy - 1}')],
             [('A', 'STATE'), ('B', 'DESTINATION')],
             [('B', 'Standard CONUS rate applies to all counties not specifically listed.'), ('D', f'October 1, {fy - 1}'),
              ('E', f'September 30, {fy}'), ('F', 113), ('G', 68)]] + rows
    sheet = []
    for n, row in enumerate(lines, 1):
        cells = ''.join(f'<c r="{c}{n}" t="s"><v>{s(v)}</v></c>' if isinstance(v, str) else f'<c r="{c}{n}"><v>{v}</v></c>' for c, v in row)
        sheet.append(f'<row r="{n}">{cells}</row>')
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('xl/sharedStrings.xml', f'<sst xmlns="{ns}">' + ''.join(f'<si><t>{x}</t></si>' for x in strings) + '</sst>')
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{ns}"><sheetData>' + ''.join(sheet) + '</sheetData></worksheet>')
    return buf.getvalue()


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    from core import per_diem as pd
    from core.database import AppSetting, db_session
    app = ctx.app_src

    # ── P1 ──
    gen = app.split('async function generateTripBudget(')[1].split('\n}')[0]
    check('s186 P1 no model is asked for a price, nothing is labelled live, and no web-search tool is passed',
          'callAI(' not in gen and 'live prices' not in app and 'web_search' not in app and 'Always search for real current prices' not in app
          and '_renderTripBudgetResult' not in app)
    r = c.post('/api/trip/budget', headers=HJ, data=json.dumps({'dest': 's186', 'total': 900, 'aiResult': {'hotel': {'cost': 999}}}))
    with db_session() as s:
        saved = json.loads(s.query(AppSetting).filter_by(key='trip_budget').first().value)
        s.query(AppSetting).filter_by(key='trip_budget').first().value = json.dumps({'dest': 'old', 'aiResult': {'total': 1234}})
        s.commit()
    old = c.get('/api/trip/budget', headers=H).get_json()['data']
    check('s186 P1 a budget is never saved with the model\'s prices again; an old one says what it was',
          r.status_code == 200 and 'aiResult' not in saved and saved['total'] == 900
          and old['aiResult_label'] == 'estimated by the AI model in an earlier version, not a price')
    with db_session() as s:
        s.query(AppSetting).filter_by(key='trip_budget').delete(); s.commit()

    # ── P2 ──
    t = pd.table()
    check('s186 P2 the shipped GSA table: a fiscal year, its rows, the standard rate, and its source',
          t and t['fy'] >= 2027 and len(t['rows']) >= 600 and t['standard'] == {'lodging': 113, 'mie': 68} and t['source'] == pd.SOURCE)
    oct_, nov = pd.lookup('Denver, CO', '2026-10-20'), pd.lookup('Denver, CO', '2026-12-05')
    check('s186 P2 a place\'s rate follows its season (Denver: October, then November to March)',
          oct_['found'] and nov['found'] and oct_['lodging'] != nov['lodging'] and oct_['mie'] == nov['mie'] and nov['season'] == ['11-01', '03-31'])
    check('s186 P2 a DOT market name finds its first city ("Dallas/Fort Worth, TX" -> Dallas)', pd.lookup('Dallas/Fort Worth, TX', '2027-03-01')['dest'] == 'Dallas')
    amb = pd.lookup('Portland', '2026-11-01')
    check('s186 P2 a place GSA doesn\'t list says so; a name in two states asks which - never a guess',
          pd.lookup('Millbrook, OH', '2026-11-01') == {'found': False, 'reason': 'not_listed'}
          and amb['reason'] == 'ambiguous' and 'Portland, OR' in amb['places'] and pd.lookup('Paris', '2026-11-01')['found'] is False)
    check('s186 P2 GSA\'s file reads with the standard library (a GSA-shaped sheet becomes a table)',
          pd.build_from_xlsx(_tiny_xlsx(2028, [[('A', 'CO'), ('B', 'Denver / Aurora'), ('C', 'Denver'), ('D', 'October 1, 2027'),
                                                ('E', 'September 30, 2028'), ('F', 200), ('G', 90)]] * 300))['fy'] == 2028)

    # the yearly refresh: GSA's whole file, nothing about a trip
    asked, real_get, real_fy = [], pd._get, pd.current_fy
    pd._get = lambda url: (asked.append(url), b'')[1]
    try:
        none = pd.refresh(force=True)                 # this fiscal year already ships: no request at all
        quiet = list(asked)
        pd.current_fy = lambda today=None: 2028
        link = '/system/files/FY2028_PerDiemRates_Validated.xlsx'
        xl = _tiny_xlsx(2028, [[('A', 'CO'), ('B', 'Denver / Aurora'), ('C', 'Denver'), ('D', 'October 1, 2027'),
                                ('E', 'September 30, 2028'), ('F', 201), ('G', 91)]] * 300)
        pd._get = lambda url: (asked.append(url), (f'<a href="{link}">FY 28</a>'.encode() if url == pd.FILES_PAGE else xl))[1]
        res = pd.refresh(force=True)
        newest = pd.table()
    finally:
        pd._get, pd.current_fy = real_get, real_fy
        if pd.DOWNLOADED.exists():
            pd.DOWNLOADED.unlink()
    check('s186 P2 the refresh asks nothing while the year is current; when a new year is out it fetches only the GSA page and file',
          none == {'updated': False, 'reason': 'already_latest'} and quiet == []
          and res == {'updated': True, 'fy': 2028} and asked == [pd.FILES_PAGE, 'https://www.gsa.gov' + link]
          and newest and newest['fy'] == 2028 and pd.table()['fy'] == 2027)

    # ── P3 ──
    url = pd.google_hotels_url('Denver, CO', '2026-11-12', '2026-11-15', 2)
    check('s186 P3 the Google Hotels address carries the destination, the dates and the guests as search text',
          url == 'https://www.google.com/travel/search?q=hotels+in+Denver%2C+CO+from+November+12+2026+to+November+15+2026+for+2+adults'
          and pd.google_hotels_url('', '2026-11-12', '2026-11-15') is None)
    import bank_window
    opened, real_open = [], bank_window.open_bank_window
    bank_window.open_bank_window = lambda key, u, *a, **k: (opened.append((key, u)), 'opened')[1]
    try:
        hr = c.post('/api/trip/hotels-window', headers=HJ, data=json.dumps({'dest': 'Denver, CO', 'checkin': '2026-11-12',
                                                                          'checkout': '2026-11-15', 'guests': 2, 'url': 'https://evil.example/'}))
    finally:
        bank_window.open_bank_window = real_open
    check('s186 P3 the window opens Google Hotels from the address built on the server - a page cannot name another site',
          hr.status_code == 200 and opened == [(('hotels', 0), url)])

    # ── P4 / P5 ──
    upd = app.split('function tripUpdateBudget(')[1].split('\nfunction ')[0]
    check('s186 P5 the old made-up defaults are gone: no $140 a night, no $45 a day, no $50 of activities',
          '?? 140' not in upd and ': 45 * travelers' not in upd and 'activitiesPerPersonDay ?? 50' not in upd)
    check('s186 P4/P5 each line carries its source; activities are yours or not included; a missing rate says so',
          all(x in upd for x in ('hotelSource', 'diningSource', 'activitiesSource', "No published rate for this destination; enter yours.",
                                  'Not included - add what you plan to spend.', '(the federal travel rate, not a quote)')))
    fb = app.split('function _tripBudgetFallbackHTML(')[1].split('\n}')[0]
    check('s186 P5 the budget says the total counts only sourced lines, with no verdict ("fits", "consider saving")',
          'counts only lines with a source' in fb and 'fits within your budget' not in fb and 'Consider saving' not in fb
          and 'Turn on AI' not in fb)
