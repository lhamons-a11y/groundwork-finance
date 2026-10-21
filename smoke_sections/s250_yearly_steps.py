"""Item 106 (gw 2.0/YEARLY_PRICE_STEPS.md; Rob 2026-10-21: Y1-Y11 "as recommended"): yearly price steps.

    Y1  every step in a payee's history, by year        Y2  a pattern a year apart; projected from 3 (measured)
    Y3  a 1% floor inside the search                    Y4  a charge paid once a year, charge to charge
    Y5  usage bills: only the household's word; item 26's kinds left to item 26
    Y6  the projection beside the saved amount, in the totals only when followed
    Y7  "Is your bill now $X?" - the answer the only write, with Undo     Y8  the answer wins for its year
    Y9  facts, never a verdict or a promise             Y10 the Bills tab, the plan rows, the check-in, the calendar
"""
import json
import subprocess
import sys
from datetime import date, datetime, timedelta


def _months_back(d, k):
    y, m = d.year, d.month - k
    while m < 1:
        y, m = y - 1, m + 12
    return date(y, m, min(d.day, 28))


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import checkin as ck
    from core import yearly_steps as ys
    from core.database import AppSetting, BudgetItem, Category, Transaction, db_session

    # ── the arithmetic ──────────────────────────────────────────────────────────────────────────────────────────
    d0 = date(2022, 3, 10)
    mon = lambda n, f: [(_months_back(date(2026, 3, 10), n - 1 - i), f(i)) for i in range(n)]
    three = ys.read(mon(46, lambda i: round(70.0 * 1.03 ** sum(i >= s for s in (10, 22, 34)), 2)))
    check(f"s250 Y1/Y3 every step is found, not only the latest - three 3% steps a year apart ({three and [s['month'] for s in three['steps']]})",
          three and len(three['steps']) == 3 and all(abs(s['pct'] - 0.03) < 0.002 for s in three['steps']))
    pat3 = ys.pattern(three['steps'])
    two = ys.pattern(three['steps'][-2:])
    check("s250 Y2 a pattern from steps a year apart: the median, 'each' only from three, 'the last two' with two",
          pat3['pattern'] and abs(pat3['pct'] - 0.03) < 0.002 and pat3['each_year'] and 'each ' in ys.sentence('X', pat3)
          and two['pattern'] and not two['each_year'] and 'the last two' in ys.sentence('X', two))
    exp = ys.next_expected(pat3)
    inside = date(int(exp[:4]), int(exp[5:7]), 5)
    p3 = ys.projection(pat3, three['level'], inside)
    check(f"s250 Y2 as measured: projected from three steps, never from two (MIN_PROJECT {ys.MIN_PROJECT}) - {p3}",
          ys.MIN_PROJECT == 3 and p3 and abs(p3['amount'] - round(three['level'] * (1 + pat3['pct']), 2)) < 0.01
          and ys.projection(two, three['level'], inside) is None
          and ys.projection(pat3, three['level'], inside + timedelta(days=120)) is None)
    odd = ys.pattern([{'month': '2024-03', 'date': '2024-03-10', 'pct': 0.02, 'source': 'ledger'},
                      {'month': '2025-03', 'date': '2025-03-10', 'pct': 0.09, 'source': 'ledger'},
                      {'month': '2026-03', 'date': '2026-03-10', 'pct': 0.03, 'source': 'ledger'}])
    check('s250 Y2 steps that differ too much are a range, said, and not projected',
          odd['pattern'] and not odd['agree'] and 'differ too much' in ys.sentence('X', odd)
          and ys.projection(odd, 100.0, date(2027, 3, 5)) is None)
    yearly = ys.read([(date(2022 + k, 6, 10), round(1140 * 1.045 ** k, 2)) for k in range(4)])
    check(f"s250 Y4 a charge paid once a year is compared charge to charge ({yearly and len(yearly['steps'])} steps)",
          yearly and yearly['kind'] == 'yearly' and len(yearly['steps']) == 3
          and ys.pattern(yearly['steps'])['each_year'])
    check('s250 Y5 a usage bill never steps from the ledger; neither does interest',
          ys.read(mon(36, lambda i: 120.0 + 30 * (i % 4)), 'Water / Sewer') is None
          and ys.read(mon(36, lambda i: 70.0), 'Interest / Fees') is None)
    won = ys.apply_answers(three['steps'], [{'month': three['steps'][-1]['month'], 'answer': 'amount',
                                             'before': three['steps'][-1]['before'], 'amount': 80.0}])
    check('s250 Y8 the household\'s answer replaces the ledger\'s reading of that year; "not sure" changes nothing',
          won[-1]['source'] == 'answer' and won[-1]['after'] == 80.0 and len(won) == 3
          and ys.apply_answers(three['steps'], [{'month': three['steps'][-1]['month'], 'answer': 'not_sure'}]) == three['steps'])
    words = ' '.join(ys.sentence('X', p) for p in (pat3, two, odd)).lower()
    check('s250 Y9 the words are facts with their years - no promise, verdict or advice',
          not any(w in words for w in ('will ', 'expect', 'should', 'raise', 'hike', 'because', 'likely', 'budget')))
    nm = subprocess.run([sys.executable, str(ctx.BASE / 'scripts' / 'y106_null_model.py'), '600'],
                        capture_output=True, text=True, timeout=600)
    last = (nm.stdout.strip().splitlines() or [''])[-1]
    check(f's250 the null model passes (false projections <= 2%; 2%+ yearly steps said and projected >= 95%): {last}',
          nm.returncode == 0 and last == 'PASS')

    # ── the record: three yearly 3% steps, and a first charge at a new price last week (Y7) ─────────────────────────
    today = date.today()
    w0, _w1 = ck.week_bounds(today)
    pdate = w0 + timedelta(days=2)
    base = 64.0
    price = lambda k: round(base * 1.03 ** sum(k <= s for s in (36, 24, 12)), 2)   # k months before the new charge
    with db_session() as s:
        cat = s.query(Category).filter_by(name='Internet').first()
        wcat = s.query(Category).filter_by(name='Water / Sewer').first()
        ecat = s.query(Category).filter_by(name='Electric').first()
        for k in range(47, 0, -1):
            s.add(Transaction(date=_months_back(pdate, k), amount=price(k), type='debit', merchant='S250 FIBERNET',
                              description='S250 FIBERNET', category_id=cat.id if cat else None))
        new_price = round(price(1) * 1.03, 2)
        s.add(Transaction(date=pdate, amount=new_price, type='debit', merchant='S250 FIBERNET',
                          description='S250 FIBERNET', category_id=cat.id if cat else None))
        last_bill = _months_back(today, 1)
        for d, a in ((_months_back(last_bill, 12), 80.0), (last_bill, 84.0)):
            s.add(Transaction(date=d, amount=a, type='debit', merchant='S250 CITY WATER', description='S250 CITY WATER',
                              category_id=wcat.id if wcat else None))
            s.add(Transaction(date=d, amount=a * 1.5, type='debit', merchant='S250 POWERCO', description='S250 POWERCO',
                              category_id=ecat.id if ecat else None))
        b = BudgetItem(name='S250 Fibernet', category='Internet', amount=price(1), type='expense', is_active=True)
        w = BudgetItem(name='S250 City Water', category='Water / Sewer', amount=80.0, type='expense', is_active=True)
        s.add(b); s.add(w); s.commit()
        bid, wid = b.id, w.id

    def items():
        return ((c.get('/api/yearly-steps', headers=H).get_json() or {}).get('data') or {}).get('items', [])

    def amount(i):
        with db_session() as s:
            return s.get(BudgetItem, i).amount
    got = items()
    mine = next((x for x in got if x['payee'] == 'S250 FIBERNET'), None)
    q = (mine or {}).get('question') or {}
    proj = (mine or {}).get('projection') or {}
    check(f"s250 Y6/Y7 the Bills list has the pattern, the projection and the question ({mine and mine['sentence']}; {q.get('text')})",
          mine and mine['pattern'] and len(mine['steps']) == 3 and mine['line'] and mine['line']['id'] == bid
          and abs(proj.get('amount', 0) - round(price(1) * (1 + 0.03), 2)) < 0.05
          and q.get('kind') == 'price' and q.get('amount') == new_price and f'${new_price:,.2f}' in q.get('text', ''))
    check('s250 Y5 a usage bill item 26 estimates (Electric) is left to item 26; a water bill is asked about its rate',
          not any(x['payee'] == 'S250 POWERCO' for x in got)
          and any(x['payee'] == 'S250 CITY WATER' and (x['question'] or {}).get('kind') == 'rate' for x in got))

    ckf = (c.get('/api/checkin', headers=H).get_json() or {}).get('data') or {}
    check('s250 Y10 the Sunday check-in names the question the week its new price landed',
          any(y['payee'] == 'S250 FIBERNET' and y.get('question') for y in ckf.get('yearly_steps', [])))

    def month_row():
        m = (c.get('/api/budget/month-amounts', headers=H).get_json() or {}).get('data') or {}
        return m.get(str(bid)) or {}
    before = month_row()
    fo = c.post('/api/yearly-steps/follow', headers=HJ, data=json.dumps({'item_id': bid, 'on': True}))
    followed = month_row()
    c.post('/api/yearly-steps/follow', headers=HJ, data=json.dumps({'item_id': bid, 'on': False}))
    after = month_row()
    check(f"s250 Y6 totals use the projection only while followed, and the saved amount never moves ({before.get('month_source')} -> {followed.get('month_source')} {followed.get('month_amount')} -> {after.get('month_source')})",
          fo.status_code == 200 and before.get('month_source') == 'saved' and followed.get('month_source') == 'yearly'
          and abs(followed.get('month_amount', 0) - proj.get('amount', -1)) < 0.01 and after.get('month_source') == 'saved'
          and amount(bid) == price(1))

    bad = c.post('/api/yearly-steps/answer', headers=HJ, data=json.dumps({'payee': 'S250 FIBERNET', 'answer': 'rate', 'pct': 3}))
    none = c.post('/api/yearly-steps/answer', headers=HJ, data=json.dumps({'payee': 'NOBODY S250', 'answer': 'yes'}))
    yes = c.post('/api/yearly-steps/answer', headers=HJ, data=json.dumps({'payee': 'S250 FIBERNET', 'answer': 'yes', 'amount': 1.0}))
    y = (yes.get_json() or {}).get('data') or {}
    after_yes = amount(bid)
    mine2 = next((x for x in items() if x['payee'] == 'S250 FIBERNET'), {})
    cal = ((c.get('/api/calendar', headers=H).get_json() or {}).get('data') or {}).get('entries', [])
    step = next((e for e in cal if e['kind'] == 'step' and 'S250 FIBERNET' in e['title']), None)
    check(f"s250 Y7 yes sets the line to the record's figure (never the page's), the answer is the newest step, and the calendar has next year ({after_yes}; {step and step['date']})",
          bad.status_code == 400 and none.status_code == 404 and yes.status_code == 200
          and after_yes == new_price and y.get('change', {}).get('from') == price(1)
          and not mine2.get('question') and mine2['steps'][-1]['source'] == 'answer'
          and step and step['certainty'] == 'expected'
          and datetime.strptime(step['date'], '%a, %d %b %Y %H:%M:%S GMT').strftime('%Y-%m') == f'{pdate.year + 1}-{pdate.month:02d}')
    un = c.post('/api/yearly-steps/undo', headers=HJ, data=json.dumps({'payee': 'S250 FIBERNET', 'month': y['recorded']['month'],
                                                                        'change': y.get('change')}))
    mine3 = next((x for x in items() if x['payee'] == 'S250 FIBERNET'), {})
    check('s250 Undo removes the answer and puts the line back; the question is open again',
          un.status_code == 200 and amount(bid) == price(1) and (mine3.get('question') or {}).get('amount') == new_price)

    rate = c.post('/api/yearly-steps/answer', headers=HJ, data=json.dumps({'payee': 'S250 CITY WATER', 'answer': 'rate', 'pct': 4}))
    r = (rate.get_json() or {}).get('data') or {}
    check(f"s250 Y5(c) a rate the household gives moves the water line by it, with Undo ({amount(wid)})",
          rate.status_code == 200 and amount(wid) == 83.2 and r.get('recorded', {}).get('pct') == 0.04)
    c.post('/api/yearly-steps/undo', headers=HJ, data=json.dumps({'payee': 'S250 CITY WATER', 'month': r['recorded']['month'],
                                                                   'change': r.get('change')}))

    app, html = ctx.app_src, ctx.html_src
    mod = (ctx.BASE / 'static' / 'js' / 'teaching' / 'yearly.js').read_text(encoding='utf-8')
    check('s250 Y10 the page: a Bills-tab card with the years, the projection and its follow choice, the question with '
          'Undo, a note on the plan row, the check-in line and a calendar icon',
          'id="budgetYearlySteps"' in html and "'/api/yearly-steps/answer'" in mod and "'/api/yearly-steps/undo'" in mod
          and "'/api/yearly-steps/follow'" in mod and 'The years' in mod and 'data-gw-yearly-note' in mod
          and "_budTabCount('bills', asked, 'yearly')" in mod and 'f.yearly_steps' in app and "step: '📈'" in app)
    # found building item 106: a line the server changed stayed at its old amount in the page's copy, and saving any
    # budget row sends every row's amount - so the next save quietly put the old price back (W2's tap had it too)
    tap = app.split('async function applyPriceChange(i) {')[1].split('\n}\n')[0]
    check("s250 a line the server changes is changed in the page's copy too (W2's tap and Undo, the yearly answer and its Undo), "
          'so the next save cannot put the old amount back',
          'function _setLocalLineAmount(kind, id, amount)' in app and tap.count('_setLocalLineAmount(') == 2
          and mod.count('_setLocalLineAmount(') == 2 and 'month: _refreshMonth' in
          (ctx.BASE / 'static' / 'js' / 'teaching' / 'utility.js').read_text(encoding='utf-8'))

    with db_session() as s:
        s.query(Transaction).filter(Transaction.merchant.in_(['S250 FIBERNET', 'S250 CITY WATER', 'S250 POWERCO'])).delete(
            synchronize_session=False)
        s.query(BudgetItem).filter(BudgetItem.id.in_([bid, wid])).delete(synchronize_session=False)
        for k in ('yearly_step_answers', 'yearly_step_follow'):
            row = s.query(AppSetting).filter_by(key=k).first()
            if row:
                s.delete(row)
        s.commit()
