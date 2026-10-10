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

    # ── I1, as amended (section 4, D3-D10): each payer judged on its own checks ──
    today = date.today()

    def series(every, n, amount, end=None):
        end = end or today - timedelta(days=2)
        return [(end - timedelta(days=every * (n - 1 - k)), amount(k)) for k in range(n)]

    J = lambda checks, kind=None, ends=None: ic.judge_payer('p', checks, kind, today, ends or today)
    steady = series(14, 20, lambda k: 2400.0)
    cut = series(14, 20, lambda k: 2400.0 if k < 15 else 2100.0)
    d = J(cut)
    check(f's183 D4/D5 a cut in steady pay is found, measured against the checks before it, in dollars a month ({d.get("monthly_drop")})',
          d['state'] == 'drop' and d['per_check_before'] == 2400.0 and d['per_check_now'] == 2100.0
          and abs(d['monthly_drop'] - 300 * 26 / 12) < 0.01 and J(steady)['state'] == 'steady')
    long_cut = series(30, 10, lambda k: 4600.0 if k < 6 else 3900.0)
    check('s183 D4 a cut that has lasted months is still measured against the pay before it, not the new level',
          J(long_cut)['state'] == 'drop' and J(long_cut)['per_check_before'] == 4600.0)
    stopped = series(14, 12, lambda k: 2400.0, end=today - timedelta(days=40))
    check('s183 D7 a paycheck that has not come in, while the account kept recording, is asked about - never a drop',
          J(stopped, ends=today)['state'] == 'missing' and J(stopped, ends=today - timedelta(days=39))['state'] == 'not_on_record_yet')
    hourly = series(7, 30, lambda k: 950.0 + (700.0 if k % 5 in (1, 2) else 0))
    check('s183 D10 pay that varies widely is asked about once, and gets no alarm until answered; a single step or a double check is not "varies"',
          J(hourly)['state'] == 'ask' and J(hourly, 'hourly')['state'] == 'steady' and J(cut)['state'] == 'drop'
          and J(series(14, 20, lambda k: 4800.0 if k == 9 else 2400.0))['state'] == 'steady')
    heavy = series(7, 30, lambda k: 950.0 + (600.0 + 37 * (k % 7) if k % 6 != 0 else 0))
    check('s183 D8 / AP9 overtime nearly every week: no ordinary week can be told, so it says so - facts, no alarm',
          J(heavy, 'hourly')['state'] == 'cannot_tell')
    h = J(hourly, 'hourly')
    check(f's183 D8 hourly pay: the ordinary week and the overtime, as facts ({h.get("ordinary")}, {h.get("overtime")})',
          h['ordinary'] == 950.0 and h['overtime']['recent'] > 0)
    hours_cut = series(7, 30, lambda k: (950.0 if k < 18 else 830.0) + (700.0 if k % 5 in (1, 2) else 0))
    hc = J(hours_cut, 'hourly')
    check(f's183 D8 a cut in hours is found under the overtime ({hc.get("per_check_before")} -> {hc.get("per_check_now")})',
          hc['state'] == 'drop' and hc['per_check_before'] == 950.0 and hc['per_check_now'] < 950.0 * 0.92)
    split = [(today - timedelta(days=14 * (19 - k)), 1200.0) for k in range(20)] * 2
    sp = ic.detect_pay([{'date': dd, 'amount': a, 'payer': 'p', 'account_id': 1} for dd, a in split], {}, {1: today}, today)
    check('s183 D3 a paycheck split across two deposits on one day is one paycheck', sp['payers'][0]['state'] == 'steady'
          and sp['payers'][0]['typical'] == 2400.0)

    # the null models (D6): no real change, each payer shape 1,000 times - false drops <= 5%
    rnd = random.Random(71)

    def salary_noise():
        return series(14, 22, lambda k: 2400.0 * rnd.uniform(.985, 1.015)), None

    def salary_double():
        dbl = rnd.randrange(22)
        return series(14, 22, lambda k: 2400.0 * (2 if k == dbl else 1) * rnd.uniform(.99, 1.01)), None

    def monthly_noise():
        return series(30, 10, lambda k: 4000.0 * rnd.uniform(.98, 1.02)), None

    def late():
        s = series(14, 22, lambda k: 2400.0)
        i = rnd.randrange(1, 21)
        s[i] = (s[i][0] + timedelta(days=rnd.choice((2, 3))), s[i][1])
        return s, None

    def overtime_streaks(stay=.7, enter=.3):
        on, out = False, []
        for k in range(32):
            on = (rnd.random() < stay) if on else (rnd.random() < enter)
            out.append(950.0 * rnd.uniform(.99, 1.01) + (rnd.uniform(300, 1100) if on else 0))
        end = today - timedelta(days=2)
        return [(end - timedelta(days=7 * (31 - k)), a) for k, a in enumerate(out)], 'hourly'

    rates = {}
    for name, gen in (('salary noise', salary_noise), ('a double check', salary_double), ('monthly', monthly_noise),
                      ('late deposits', late), ('hourly overtime streaks', overtime_streaks),
                      ('hourly overtime most weeks', lambda: overtime_streaks(.8, .45))):
        hits = 0
        for _ in range(1000):
            s, kind = gen()
            hits += J(s, kind)['state'] == 'drop'
        rates[name] = hits / 1000
    check(f"s183 D6 null model: false drops stay <= 5% - {', '.join(f'{k} {v:.1%}' for k, v in rates.items())}",
          all(v <= 0.05 for v in rates.values()))

    def real_cut():
        return series(14, 22, lambda k: 2400.0 * rnd.uniform(.985, 1.015) * (1 if k < 18 else .88)), None

    def real_hours_cut():
        s, _ = overtime_streaks(.5, .15)        # overtime now and then; a cut under heavy overtime may read "can't tell"
        return [(dd, a - (124.0 if k >= 20 else 0)) for k, (dd, a) in enumerate(s)], 'hourly'
    found = {n: sum(J(*g())['state'] == 'drop' for _ in range(300)) / 300 for n, g in (('a 12% pay cut', real_cut),
                                                                                       ('a 13% cut in hours', real_hours_cut))}
    check(f"s183 D6 and real cuts are found: {', '.join(f'{k} {v:.0%}' for k, v in found.items())}",
          all(v >= 0.9 for v in found.values()))

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
