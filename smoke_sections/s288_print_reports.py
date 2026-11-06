"""Every page prints as a report (gw 2.0/PRINT_REPORTS.md; Rob 2026-11-05).

    P1  the words for it reach the print, on the page in front or a page named; the Ledger asks detail or overview first
    P2  nothing else is taken for it: real questions, "save money", and every phrase in the voice corpus
    P3  the possible future budget: the budget rises, income and fixed payments do not, a term ends, a running cost rises,
        and a figure it cannot stand behind is refused
    P4  the report says it is a projection, not actual inflation, and cannot account for unknown expenses
    P5  the Ledger's report counts money the way the Ledger does
    P6  the map holds both ends of any drive, and asks no map service
    P7  the button with AI off, and the sheet the print rule leaves showing; nothing prints the blank app shell any more
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile


def run(ctx):
    check = ctx.check
    base = ctx.BASE
    app = (base / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    html = (base / 'static' / 'index.html').read_text(encoding='utf-8')
    pr = (base / 'static' / 'js' / 'print.js').read_text(encoding='utf-8')

    # ── P3: the arithmetic ──
    from core import budget_projection as bp
    p = bp.project(5000, 3000, 400, 200, 350, kind='fixed', term_months=36)
    rows = {r['year']: r for r in p['rows']}
    check('s288 P3 the years shown are today, 1, 2, 3 and 5', list(rows) == [0, 1, 2, 3, 5])
    check('s288 P3 the budget rises 3% a year, compounded', rows[0]['budget'] == 3000 and rows[1]['budget'] == 3090 and rows[2]['budget'] == 3182.7)
    check('s288 P3 income is held at today\'s', all(r['income'] == 5000 for r in p['rows']))
    check('s288 P3 debt minimums and set-asides are held', all(r['debt_minimums'] == 400 and r['set_asides'] == 200 for r in p['rows']))
    check('s288 P3 a fixed payment stays, and stops when its term ends', rows[2]['purchase'] == 350 and rows[3]['purchase'] == 0 and rows[5]['purchase'] == 0)
    check('s288 P3 what is left is income less all of it', rows[0]['left_with'] == 5000 - 3000 - 400 - 200 - 350 and rows[0]['left_without'] == 5000 - 3000 - 400 - 200)
    check('s288 P3 a 36-month term costs 36 payments over five years', p['five_year_cost'] == 350 * 36)
    sub = bp.project(5000, 3000, 0, 0, 100, kind='rises')
    check('s288 P3 a running cost rises with the rest', {r['year']: r for r in sub['rows']}[2]['purchase'] == 106.09)
    check('s288 P3 with no term it runs all five years', {r['year']: r for r in sub['rows']}[5]['purchase'] > 100)
    swap = bp.project(5000, 3000, 400, 0, 350, replaces_monthly=300)
    check('s288 P3 what it replaces comes off the debt minimums', swap['rows'][0]['debt_minimums'] == 100 and swap['rows'][0]['left_without'] == 1600)
    for label, args in (('text', ('x', 1, 1, 1, 1)), ('a blank', (None, 1, 1, 1, 1)), ('a negative', (-1, 1, 1, 1, 1)), ('infinity', (float('inf'), 1, 1, 1, 1))):
        try:
            bp.project(*args)
            refused = False
        except ValueError:
            refused = True
        check(f's288 P3 {label} is refused, not guessed at', refused)

    # ── P4: the words ──
    check('s288 P4 the report says it is a projection, not actual inflation', 'This is a projection, not actual inflation.' in pr)
    check('s288 P4 and that it cannot account for unknown expenses', 'cannot account for other expenses that are not known' in pr)
    check('s288 P4 the rate is named as an illustration, not as a figure anyone published', "Groundwork's illustration and not a published or predicted rate" in pr)

    # ── P7: the button, the sheet, and the old blank prints ──
    check('s288 P7 a Print button stands in the Ask box\'s place', re.search(r'id="gwAskBox".*?id="gwPrintBtn".*?</span>', html, re.S) is not None and 'onclick="gwPrintPage()"' in html)
    check('s288 P7 it shows only with AI off', "printBtn.style.display = enabled ? 'none' : ''" in app)
    check('s288 P7 the print rule leaves only the sheet showing', 'body.gw-printing > *:not(#gwPrintSheet){display:none!important}' in html and ':not(#gwPrintSheet){display:none!important}' in html)
    check('s288 P7 the sheet is outside the app, and print.js loads', '<div id="gwPrintSheet"></div>' in html and '/js/print.js' in html)
    check('s288 P7 the Report Center\'s buttons use it (they printed blank)', 'onclick="window.print()"' not in app and "await _rbRun('print');\n  await gwPrintPage();" in app.replace('\r\n', '\n'))
    check('s288 P7 Net Worth prints the Report Center\'s own report', '_rcNetWorthTimelineHTML(_nwHistory)' in pr and 'body.innerHTML = _rcNetWorthTimelineHTML(history)' in app)
    check('s288 P7 a confirmation number is never printed', 'confirmation' not in pr.replace("Your airline's confirmation is the one to travel by", ''))
    check('s288 P7 the guide says how', '"How do I print a page?"' in app)
    check('s288 P7 BYB counts the goals that are really set (it read a field that does not exist)', 'parseFloat(f.monthly)' not in app[app.index('function _bybSandboxCalc'):app.index('function _bybUpdateScoreboard')])
    check('s288 P7 a loan\'s icon is an icon, not the word "bank"', "isLoan ? 'bank'" not in app)

    c, hj = ctx.c, ctx.HJ
    r = c.post('/api/byb/projection', headers=hj, data=json.dumps({'income': 5000, 'budget': 3000, 'debt_minimums': 400, 'set_asides': 200, 'monthly': 350}))
    body = (r.get_json() or {}).get('data') or {}
    check(f's288 P3 the route gives the same rows ({r.status_code})', r.status_code == 200 and body.get('rows', [{}])[0].get('left_with') == 1050)
    bad = c.post('/api/byb/projection', headers=hj, data=json.dumps({'income': 'lots', 'budget': 3000, 'debt_minimums': 0, 'set_asides': 0, 'monthly': 1}))
    check(f's288 P3 the route refuses a figure it cannot use ({bad.status_code})', bad.status_code == 400)
    half = c.get('/api/trip/route-points?origin=&destination=Denver', headers=hj)
    check(f's288 P6 the map route needs both ends ({half.status_code})', half.status_code == 400)
    # The licence's printed credit names its address (ROAD_MAP.md); that is words on the paper, not a request.
    check('s288 P6 the map asks no map service', not re.search(r'tile\.|openstreetmap\.org|mapbox|maps\.google|https?://',
                                                               pr.replace('openstreetmap.org/copyright.', '')))

    # ── P1, P2, P5, P6: on the page's own code ──
    node = shutil.which('node')
    if not node:
        check('s288 node is available for the page test', False)
        return
    spec = importlib.util.spec_from_file_location('voice_natural_measure', base / 'scripts' / 'voice_natural_measure.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    corpus = json.loads((base / 'scripts' / 'voice_natural_asks.json').read_text(encoding='utf-8'))
    phrases = []
    def walk(v):
        if isinstance(v, str):
            phrases.append(v)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for key, x in v.items():
                walk(key)
                walk(x)
    walk(corpus)
    js = mod.STUBS + mod.HOUSE + mod.page_code(base) + '\n' + pr + r"""
const prints = [];
let asked = 0, view = 'budget';
gwPrintPage = m => { prints.push(m || null); };
_prAskLedger = () => { asked += 1; _gwPrintLedgerAsked = true; };
_prActiveView = () => view;
function say(q) {
  prints.length = 0; asked = 0;
  const panel = { innerHTML: '' };
  window._gwVoiceAsked = false;
  const hit = askIntent(q, panel, '', true);
  return { hit, prints: prints.slice(), asked };
}
const printWords = ['print this page', 'print', 'print this', 'print it', 'print the page', 'print this page please', 'please print this page',
  'can you print this page', 'could you print this', 'i want to print this page', 'i need to print this', "let's print this", 'go print this page',
  'print this out', 'print out this page', 'save this page as a pdf', 'save this as a pdf', 'print this report', 'print a copy of this'];
const notPrint = ['how do i print a page', 'the printer is out of ink', 'save money', 'save this', 'save', 'what does the fine print mean', 'print money',
  'why is my printer broken', 'is the print button on this page', 'i printed it yesterday'];
const out = {};
out.yes = printWords.filter(w => { const r = say(w); return !(r.hit && r.prints.length === 1); });
out.no = notPrint.filter(w => { prints.length = 0; asked = 0; gwPrintIntent(_askNorm(w), _askCanon(_askRepaired(_askNorm(w)))); return prints.length || asked; });
out.corpus = CORPUS.filter(w => { prints.length = 0; asked = 0; _gwPrintLedgerAsked = false; const s = _askNorm(w); if (!s) return false; const place = gwPrintIntent(s, _askCanon(_askRepaired(s))); return place || prints.length || asked; });
view = 'ledger';
out.ledgerAsks = say('print this page');
out.ledgerSaid = ['detail', 'the overview please'].map(w => { _gwPrintLedgerAsked = true; prints.length = 0; say; const s = _askNorm(w); gwPrintIntent(s, _askCanon(_askRepaired(s))); return prints.slice(); });
_gwPrintLedgerAsked = false;
out.ledgerDirect = [say('print this page in detail'), say('print the detail page')].map(r => r.asked);
_gwPrintLedgerAsked = false;
out.otherWordsAfterAsk = (() => { _gwPrintLedgerAsked = true; const s = _askNorm('open my budget'); const hit = gwPrintIntent(s, _askCanon(_askRepaired(s))); return { hit, still: _gwPrintLedgerAsked }; })();
view = 'budget';
const rows = [
  { type: 'debit', amount: 100, category: 'Groceries', merchant: 'Kroger', account: 'Checking' },
  { type: 'debit', amount: 50, category: 'Groceries', merchant: 'Kroger', account: 'Checking' },
  { type: 'debit', amount: 200, category: 'Rent', merchant: 'Landlord', account: 'Checking' },
  { type: 'credit', amount: 1000, category: 'Pay', merchant: 'Work', account: 'Checking' },
  { type: 'credit', amount: 300, category: 'Debt', merchant: 'Payment', account: 'Visa' },
];
out.sum = prLedgerSummary(rows, ['Visa'], true);
out.sumOne = prLedgerSummary(rows, ['Visa'], false);
const pairs = [[{ lat: 40.74, lon: -84.1 }, { lat: 36.16, lon: -86.78 }], [{ lat: 47.6, lon: -122.3 }, { lat: 25.76, lon: -80.19 }], [{ lat: 32.7, lon: -117.1 }, { lat: 45.5, lon: -69 }],
  [{ lat: 40.74, lon: -84.1 }, { lat: 40.75, lon: -84.2 }], [{ lat: 61.2, lon: -149.9 }, { lat: 47.6, lon: -122.3 }]];
out.frame = pairs.map(([a, b]) => { const f = prMapFrame(a, b, 680, 300); return [f.project(a.lon, a.lat), f.project(b.lon, b.lat)].every(([x, y]) => x > 20 && x < 660 && y > 20 && y < 280); });
out.mapText = prRouteMapSVG({ origin: pairs[0][0], destination: pairs[0][1] }, 'Millbrook, OH', 'Nashville <TN>', 435);
out.chart = prFutureChartSVG([{ year: 0, income: 100, budget: 50, debt_minimums: 0, set_asides: 0, purchase: 10 }, { year: 1, income: 100, budget: 51, debt_minimums: 0, set_asides: 0, purchase: 10 }]);
console.log(JSON.stringify(out));
""".replace('CORPUS', json.dumps(phrases))
    d = tempfile.mkdtemp(prefix='s288_')
    f = os.path.join(d, 'page.js')
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(js)
    r = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=60)
    shutil.rmtree(d, ignore_errors=True)
    o = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else {}
    check(f's288 the page test ran ({r.stderr[-400:] if r.returncode else ""})', bool(o))
    if not o:
        return
    check(f's288 P1 every way of saying it prints ({o["yes"]})', not o['yes'])
    check(f's288 P2 what is not asking for it does nothing ({o["no"]})', not o['no'])
    check(f's288 P2 no phrase in the voice corpus is taken for it, of {len(phrases)} ({o["corpus"][:6]})', not o['corpus'])
    check('s288 P1 on the Ledger, "print this page" asks first and prints nothing yet', o['ledgerAsks']['asked'] == 1 and not o['ledgerAsks']['prints'])
    check(f's288 P1 the answer said aloud prints that one ({o["ledgerSaid"]})', o['ledgerSaid'] == [['detail'], ['overview']])
    check(f's288 P1 naming it up front does not ask again ({o["ledgerDirect"]})', o['ledgerDirect'] == [0, 0])
    check('s288 P1 saying something else drops the question and is not taken for an answer', o['otherWordsAfterAsk'] == {'hit': False, 'still': False})
    s = o['sum']
    check('s288 P5 in and out count as the Ledger does: a payment arriving on a card is not income', s['in'] == 1000 and s['out'] == 350 and s['net'] == 650)
    check('s288 P5 looking at one account, that account\'s credit counts', o['sumOne']['in'] == 1300)
    check('s288 P5 categories are largest first, with their counts', s['cats'][0] == {'name': 'Rent', 'total': 200, 'count': 1} and s['cats'][1]['count'] == 2)
    check(f's288 P6 both ends are on the map, across any distance ({o["frame"]})', all(o['frame']))
    check('s288 P6 a place name cannot break the map', 'Nashville &lt;TN&gt;' in o['mapText'] and '<TN>' not in o['mapText'])
    check('s288 P6 the map says it is a road estimate', '~435 mi by road' in o['mapText'])
    check('s288 P4 the chart labels today and later years against income today', all(w in o['chart'] for w in ('Today', 'In 1 year', 'Income today')))
