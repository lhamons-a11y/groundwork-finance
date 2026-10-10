"""Item 71: when income drops (gw 2.0/INCOME_CHANGE_SCENARIOS.md I1-I8, RULED 2026-10-10; built on item 66's frame,
gw 2.0/SCENARIOS.md SC1/SC3/SC5/SC6 - Rob: "71 build on 66", "build all items that have been ruled on").

    I1  a step or a slide in recorded income, null-modelled (biweekly pay, commission, late deposits, noise): <= 5%
    I2  "do you expect this to last?" kept as said, append-only
    I3  five futures, assumptions in words, every figure's kind (SC3), one payoff engine
    I4  the person's answer leads; then the smallest change that keeps the goal
    I6  (a) "Make this my budget" only on the tap, each change a budget_adjusted event, Undo restores; "Not now"
    I8  never the floor, never a protected category; never a why; recomputed on read, nothing derived stored
"""
import json
import random
import re
from datetime import date, datetime, timedelta


def _months(n, end=None):
    end = end or date.today().replace(day=1) - timedelta(days=1)
    out, y, m = [], end.year, end.month
    for _ in range(n):
        out.append(f'{y}-{m:02d}')
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    from core import income_change as ic
    from core.consequence import Card

    # ── I1 ──
    ms = _months(10)
    step = {m: (4600.0 if i < 6 else 3900.0) for i, m in enumerate(ms)}
    d = ic.detect(step)
    check('s183 I1 a step down is found, said as a fact: from, to, and the month', d and d['to'] < d['from'] and d['month'] in ms)
    slide = dict(zip(ms, [4000, 4000, 4000, 4000, 4000, 4000, 3700, 3500, 3400, 3300]))
    check('s183 I1 a slide is found', ic.detect(slide) is not None)
    flat = {m: 4000.0 for m in ms}
    gappy = {m: v for i, (m, v) in enumerate(slide.items()) if i != 6}
    check('s183 I1 level income is not a drop; a missing month is unknown, never zero, and no slide is read across it',
          ic.detect(flat) is None and ic.detect({m: 4000.0 for m in ms[:4]}) is None
          and ic.detect(gappy) is None)
    rnd = random.Random(71)

    def biweekly():
        three = set(rnd.sample(range(12), 2))
        return {m: 2000.0 * (3 if i % 12 in three else 2) for i, m in enumerate(_months(12))}

    def commission():
        return {m: 3500 + (rnd.random() < .3) * rnd.uniform(500, 2500) for m in _months(12)}

    def late():
        v = [4000.0] * 12
        for i in range(11):
            if rnd.random() < .15:
                v[i] -= 2000
                v[i + 1] += 2000
        return dict(zip(_months(12), v))

    def noisy():
        return {m: max(1.0, rnd.gauss(4000, 800)) for m in _months(12)}
    rates = {n: sum(1 for _ in range(1000) if ic.detect(g())) / 1000
             for n, g in (('biweekly', biweekly), ('commission', commission), ('late deposit', late), ('noise 20%', noisy))}
    check(f"s183 I1 null model: false drops stay <= 5% - {', '.join(f'{k} {v:.1%}' for k, v in rates.items())}",
          all(v <= 0.05 for v in rates.values()))
    real = sum(1 for _ in range(300) if ic.detect(dict(zip(_months(12), [4000.0 * rnd.uniform(.98, 1.02)] * 8
                                                               + [3800, 3500, 3300, 3200])))) / 300
    check(f's183 I1 and a real slide is found ({real:.0%})', real >= 0.9)

    # ── I3 / I4 / I6 engine ──
    lines = [{'id': 1, 'name': 'Rent', 'category': 'Rent', 'amount': 1500.0},
             {'id': 2, 'name': 'Dining', 'category': 'Dining', 'amount': 400.0},
             {'id': 3, 'name': 'Fun', 'category': 'Fun', 'amount': 300.0},
             {'id': 4, 'name': 'Gym', 'category': 'Gym', 'amount': 60.0}]
    eff = {'fun': {'stance': 'flexible', 'source': 'declared'}, 'gym': {'stance': 'protected', 'source': 'declared'}}
    plan = ic.budget_follows(lines, 300.0, eff)
    names = [x['name'] for x in plan['changes']]
    check('s183 I3 the budget follows: flexible first, never the necessity floor, never a protected line, at most half of a line',
          names[0] == 'Fun' and 'Rent' not in names and 'Gym' not in names
          and all(x['new'] >= x['old'] / 2 - 0.005 for x in plan['changes']) and plan['closed'] == 300.0 and plan['left'] == 0)
    big = ic.budget_follows(lines, 5000.0, eff)
    check('s183 I3 what cannot be closed is said, never forced out of the floor', big['left'] > 0 and 'Rent' not in [x['name'] for x in big['changes']])
    cards = [Card(balance=5000.0, rate=0.2, minimum=150.0, name='Card')]
    chg = {'kind': 'step', 'from': 4600.0, 'to': 3900.0, 'month': '2026-07'}
    sc = ic.scenarios(chg, 4300.0, lines, eff, cards, 600.0, 2400.0, answer=None)
    by = {s['key']: s for s in sc['scenarios']}
    check('s183 I3 five futures, each with its assumptions in words and every figure tagged by kind (SC3)',
          set(by) == {'nothing_changes', 'budget_follows', 'goal_moves', 'bridge', 'income_returns'}
          and all(s['assumptions'] for s in sc['scenarios'])
          and all(f['kind'] in ic.KIND for s in sc['scenarios'] for f in s['figures']))
    check('s183 I3 "nothing changes" shows the gap borrowed and the debt date it costs, from the one payoff engine',
          sc['gap'] == 400.0 and by['nothing_changes']['borrowed_monthly'] == 400.0
          and (by['nothing_changes']['debt_months'] is None or by['nothing_changes']['debt_months'] > sc['base_debt_months']))
    check('s183 I3 the bridge: how many months the savings above the person\'s floors cover', by['bridge']['bridge_months'] == 6)
    check('s183 I4 the person\'s word leads: lasting -> the budget follows; temporary -> the bridge; nothing-changes and income-returns last',
          ic.order(sc['scenarios'], 'lasting')[0] == 'budget_follows' and ic.order(sc['scenarios'], 'temporary')[0] == 'bridge'
          and ic.order(sc['scenarios'], None)[-2:] == ['nothing_changes', 'income_returns'])

    # ── the route: answer, apply on the tap, undo, not now ──
    from core.database import BudgetItem, Category, HistorianEntry, Transaction, AppSetting, db_session
    made = {'t': [], 'b': [], 'cat': None}
    first_event = 10 ** 12
    try:
        with db_session() as s:
            cat = s.query(Category).filter(Category.name == 'Income').first()
            if not cat:
                cat = Category(name='Income', type='income'); s.add(cat); s.commit(); made['cat'] = cat.id
            for i, m in enumerate(_months(10)):
                t = Transaction(date=date(int(m[:4]), int(m[5:]), 15), description='PAYROLL s183', amount=(4600.0 if i < 6 else 3900.0),
                                type='credit', category_id=cat.id)
                s.add(t); s.flush(); made['t'].append(t.id)
            b1 = BudgetItem(name='s183 Dining', category='s183 Dining', amount=900.0, type='expense', is_active=True)
            b2 = BudgetItem(name='s183 Rent', category='Rent', amount=4000.0, type='expense', is_active=True)
            s.add_all([b1, b2]); s.commit(); made['b'] += [b1.id, b2.id]
            n_adj = s.query(HistorianEntry).filter(HistorianEntry.event_category == 'budget_adjusted').count()
            first_event = (s.query(HistorianEntry.id).order_by(HistorianEntry.id.desc()).first() or (0,))[0]
        st = c.get('/api/income-change', headers=H).get_json()['data']
        with db_session() as s:
            unchanged = s.get(BudgetItem, made['b'][0]).amount == 900.0
        check('s183 I1/SC5 the route finds the drop and computes the futures on read - nothing changes by reading',
              st['change'] is not None and st['scenarios'] and unchanged and st['gap'] > 0)
        a1 = c.post('/api/income-change/answer', headers=HJ, data=json.dumps({'answer': 'lasting'})).get_json()['data']
        c.post('/api/income-change/answer', headers=HJ, data=json.dumps({'answer': 'temporary'}))
        with db_session() as s:
            hist = json.loads(s.query(AppSetting).filter_by(key='income_change_answers').first().value)
        check('s183 I2 the answer is kept as said, append-only, and it leads the order',
              a1['answer'] == 'lasting' and a1['order'][0] == 'budget_follows' and [h['answer'] for h in hist][-2:] == ['lasting', 'temporary']
          and c.post('/api/income-change/answer', headers=HJ, data=json.dumps({'answer': 'maybe'})).status_code == 400)
        ap = c.post('/api/income-change/apply', headers=HJ, data='{}').get_json()['data']
        with db_session() as s:
            dining, rent = s.get(BudgetItem, made['b'][0]).amount, s.get(BudgetItem, made['b'][1]).amount
            adj = s.query(HistorianEntry).filter(HistorianEntry.event_category == 'budget_adjusted').count() - n_adj
        check('s183 I6 (a) the tap applies the plan: lines change as shown, each a budget_adjusted event like a manual edit; rent is never touched',
              ap['applied'] and dining < 900.0 and dining >= 450.0 and rent == 4000.0 and adj == len(ap['applied']['changes']) >= 1)
        c.post('/api/income-change/undo', headers=HJ, data='{}')
        with db_session() as s:
            back = s.get(BudgetItem, made['b'][0]).amount
            adj2 = s.query(HistorianEntry).filter(HistorianEntry.event_category == 'budget_adjusted').count() - n_adj
            gone = s.query(AppSetting).filter_by(key='income_change_applied').first() is None
        check('s183 I6 (a) Undo restores the amounts, and the record shows both changes (AP10)', back == 900.0 and adj2 == 2 * adj and gone)
        sn = c.post('/api/income-change/snooze', headers=HJ, data='{}').get_json()['data']
        check('s183 I6 (a) "Not now" hides it for the rest of the month - the person\'s choice', sn['snoozed'] is True)
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.id.in_(made['t'])).delete(synchronize_session=False)
            s.query(HistorianEntry).filter(HistorianEntry.event_category == 'budget_adjusted',
                                           HistorianEntry.id > first_event).delete(synchronize_session=False)
            s.query(BudgetItem).filter(BudgetItem.id.in_(made['b'])).delete(synchronize_session=False)
            s.query(AppSetting).filter(AppSetting.key.in_(['income_change_answers', 'income_change_applied', 'income_change_snooze'])).delete(synchronize_session=False)
            if made['cat']:
                s.query(Category).filter(Category.id == made['cat']).delete(synchronize_session=False)
            s.commit()

    # ── I8: the words ──
    app = ctx.app_src
    card = app.split('function incomeChangeHtml(')[1].split('async function renderIncomeChange(')[0]
    words = card + (BASE / 'static/js/teaching/proactive.js').read_text(encoding='utf-8').split("p.detail_kind === 'income_change'")[1][:600]
    check('s183 I8 never a why, never doom: no hours, job, struggling, warning or urgency words',
          not re.search(r'\b(hours|job|laid off|fired|struggl|warning|urgent|danger|crisis|act now|failing)\b', words, re.I)
          and 'What still holds' in card and 'none of them is a prediction' in card)
    check('s183 I6 (a) the budget changes only from the tap: one route writes amounts, and it recomputes the plan itself',
          "@income_bp.route('/apply', methods=['POST'])" in ctx.server_src
          and "plan = next((s.get('plan') for s in st.get('scenarios', []) if s['key'] == 'budget_follows'), None)" in ctx.server_src
          and 'onclick="incomeChangeApply()"' in card)
    eng = (BASE / 'core/income_change.py').read_text(encoding='utf-8')
    check('s183 SC5 / AP11 the engine is arithmetic: no database, no model, no network', not re.search(
        r'^\s*(from|import)\s+(server|core\.database|core\.engine|requests|urllib|sqlite3)', eng, re.M))
