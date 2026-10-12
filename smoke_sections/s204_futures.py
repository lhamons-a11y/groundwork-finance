"""Item 66 (gw 2.0/SCENARIOS.md SC1-SC7; Rob 2026-10-11: "build ... 66").

    SC1 the goal's own measure: debt -> the debt-free date; savings / a goal -> cash in a year; unsure -> no ranking
    SC2 adverse futures from the person's own record: the costliest months again, a month without income, minimum
        payments only, known costs ahead; a future the record can't support is not offered, and the gap is said
    SC3 every figure tagged recorded / projected / you said; a possibility never becomes a transaction or budget line
    SC4 "Does this reflect your situation?": partly -> one prompt; unlikely hides it, undoable
    SC5 computed on read; a fingerprint says when the figures on screen are stale
    SC6 side by side over time (cash, what is owed), assumptions in words, the questions answered; a path is chosen
        only on the person's word, and only "what is left goes to the debt" can change a figure, with Undo
    SC7 a starting budget from the record
"""
import json
from datetime import date


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app = ctx.app_src
    from core import futures as fu
    from core.consequence import Card, simulate_payoff
    from core.database import AppSetting, BudgetItem, Transaction, db_session

    cards = [Card(balance=6000.0, rate=20.0, minimum=150.0, name='s204 Visa'),
             Card(balance=2000.0, rate=10.0, minimum=50.0, name='s204 Loan')]
    base = {'income': 5000.0, 'income_months': 3, 'spend': 3500.0, 'debt_lines': 600.0, 'debt_pay': 600.0,
            'minimums': 200.0, 'owed': 8000.0, 'cards': cards, 'strategy': 'avalanche', 'cash': 1000.0, 'goal': 'debt',
            'start_month': '2026-11',
            'spend_record': [('2025-11', 4100.0), ('2025-12', 6200.0), ('2026-01', 3900.0), ('2026-02', 4000.0),
                             ('2026-03', 5200.0), ('2026-04', 4050.0), ('2026-05', 3950.0), ('2026-06', 5600.0)],
            'known_costs': [{'label': "Mom's birthday", 'month': '2026-12', 'amount': 300.0}]}

    # the one payoff engine gives the path without changing its answer
    p = []
    a = simulate_payoff(cards, 600.0, start_month='2026-11', path=p)
    b = simulate_payoff(cards, 600.0, start_month='2026-11')
    check('s204 SC6 the payoff engine reports what is owed each month, and its answer is unchanged',
          a['months'] == b['months'] and len(p) == a['months'] and p[-1] <= 0.01 and p[0] < 8000)

    st = fu.build(base)
    by = {s['key']: s for s in st['scenarios']}
    check(f"s204 SC2 every future the record supports is offered ({sorted(by)})",
          set(by) == {'baseline', 'surplus_to_goal', 'costly_months', 'no_income_month', 'minimums_only', 'known_cost'}
          and st['gaps'] == [])
    bl = by['baseline']
    check(f"s204 SC2 as things are: cash grows by what is left each month ($900) ({bl['cash'][:3]})",
          bl['cash'][:3] == [1900.0, 2800.0, 3700.0] and bl['borrowed'] == 0)
    check('s204 SC1 debt goal: measured on the debt-free date; spending more of the surplus on debt is sooner',
          bl['measure']['label'] == 'Debt-free in' and bl['measure']['value'] == a['months']
          and by['surplus_to_goal']['debt_months'] < bl['debt_months'] and by['surplus_to_goal']['new_debt_pay'] == 1500.0
          and by['surplus_to_goal']['cash'][0] == 1000.0 and by['surplus_to_goal']['behind'] < 0)
    mid = 4075.0   # the median of the eight recorded months
    over = (6200 - mid) + (5600 - mid) + (5200 - mid)
    check(f"s204 SC2 the costliest months again: Dec, Jun and Mar's excess over a middle month, over three months ({over})",
          # what cash could not cover is borrowed, so the two together are the excess
          abs((bl['cash'][2] - by['costly_months']['cash'][2]) + by['costly_months']['borrowed'] - over) < 0.01
          and 'happen again over the next three months' in ' '.join(by['costly_months']['assumptions']))
    nm = by['no_income_month']
    check(f"s204 SC2 a month without income: cash runs out and the rest is borrowed, counted ({nm['cash'][0]}, {nm['borrowed']})",
          nm['cash'][0] == 0.0 and nm['borrowed'] == 3100.0 and nm['owed'][0] > bl['owed'][0])
    mo = by['minimums_only']
    check('s204 SC2 minimum payments only: more cash, a later debt-free date', mo['cash'][0] == bl['cash'][0] + 400
          and mo['debt_months'] > bl['debt_months'] and mo['behind'] > 0)
    check('s204 SC2 known costs ahead land in their month, from cash', by['known_cost']['cash'][1] == bl['cash'][1] - 300)

    thin = dict(base, spend_record=base['spend_record'][:3], known_costs=[], debt_pay=200.0, income=None)
    check('s204 SC2 no income on record: no futures at all, and it says why',
          fu.build(thin)['offered'] is False and 'complete months of income' in fu.build(thin)['why'])
    thin['income'] = 5000.0
    st2 = fu.build(thin)
    keys2 = {s['key'] for s in st2['scenarios']}
    check(f"s204 SC2 what the record can't support isn't offered, and each gap is said ({st2['gaps']})",
          'costly_months' not in keys2 and 'known_cost' not in keys2 and 'minimums_only' not in keys2
          and len(st2['gaps']) == 3 and any('there are 3' in g for g in st2['gaps']))

    kinds = {f['kind'] for s in st['scenarios'] for f in s['figures']}
    check('s204 SC3 every figure carries its kind, and only the three kinds', kinds <= set(fu.KIND if hasattr(fu, 'KIND') else ('observed', 'projected', 'user_supplied'))
          and kinds >= {'observed', 'projected'} and all(s['assumptions'] for s in st['scenarios']))
    said = [{'id': 'x1', 'kind': 'cost', 'amount': 800, 'month': '2027-03', 'label': 'car repair'},
            {'id': 'x2', 'kind': 'income', 'amount': 400, 'label': 'side work'},
            {'id': 'x2', 'kind': 'income', 'amount': 400, 'label': 'side work', 'withdrawn': True}]
    st3 = fu.build(base, said)
    b3 = next(s for s in st3['scenarios'] if s['key'] == 'baseline')
    check('s204 SC3 a possibility the person states is counted in every future, tagged as theirs; a withdrawn one is not',
          [p['id'] for p in st3['possibilities']] == ['x1'] and b3['cash'][4] == bl['cash'][4] - 800
          and b3['cash'][3] == bl['cash'][3]
          and all(any(f['kind'] == 'user_supplied' for f in s['figures']) for s in st3['scenarios'])
          and any('car repair' in q['a'] for q in st3['questions']))
    st4 = fu.build(base, [], [{'key': 'no_income_month', 'answer': 'unlikely'}])
    st5 = fu.build(base, [], [{'key': 'no_income_month', 'answer': 'unlikely'}, {'key': 'no_income_month', 'answer': 'show'}])
    check('s204 SC4 "Unlikely for me" hides a future for the person, and they can show it again',
          'no_income_month' not in {s['key'] for s in st4['scenarios']} and st4['hidden'][0]['key'] == 'no_income_month'
          and 'no_income_month' in {s['key'] for s in st5['scenarios']} and st5['hidden'] == [])
    un = fu.build(dict(base, goal='unsure'))
    sav = fu.build(dict(base, goal='savings'))
    check('s204 SC1 unsure: nothing ranked; savings: measured on cash in a year',
          all(s['measure']['label'] is None and s['behind'] is None for s in un['scenarios'])
          and 'surplus_to_goal' not in {s['key'] for s in un['scenarios']}
          and next(s for s in sav['scenarios'] if s['key'] == 'baseline')['measure'] == {'label': 'Cash in 12 months', 'value': bl['cash'][-1], 'unit': 'dollars'})
    qs = {q['q']: q['a'] for q in st['questions']}
    check(f's204 SC6 the questions are answered from the figures ({list(qs)})',
          set(qs) == {'What would put me behind?', 'Which upcoming expense changes the outcome most?',
                      'How much room do I actually have?', 'Which correction would change this result?'}
          and '$900 a month is left' in qs['How much room do I actually have?']
          and "Mom's birthday" in qs['Which upcoming expense changes the outcome most?'])
    words = json.dumps(st).lower()
    check('s204 SC6 no verdicts or fear words in what the futures say', not any(w in words for w in (
        'danger', 'warning', 'risky', 'you should', 'bad idea', 'disaster', 'crisis', 'alarm', 'recommend')))
    check('s204 SC5 the fingerprint moves when an input or something said moves, and not otherwise',
          fu.fingerprint(base, [], []) == fu.fingerprint(dict(base), [], [])
          and fu.fingerprint(base, [], []) != fu.fingerprint(dict(base, cash=1001.0), [], [])
          and fu.fingerprint(base, [], []) != fu.fingerprint(base, said, []))
    pb = fu.pre_budget(5000.0, [{'label': 'a', 'amount': 200.0}, {'label': 'b', 'amount': 49.99}])
    check('s204 SC7 the starting budget: rows, their total, and what remains of the income', pb['total'] == 249.99 and pb['remains'] == 4750.01
          and fu.pre_budget(None, [])['remains'] is None)

    # ── the routes ──────────────────────────────────────────────────────────
    with db_session() as s:
        n_tx, n_bi = s.query(Transaction).count(), s.query(BudgetItem).count()
        keep = {k: (lambda r: r.value if r else None)(s.query(AppSetting).filter_by(key=k).first())
                for k in ('future_possibilities', 'future_answers', 'future_choice', 'monthly_budget')}
    r = c.get('/api/futures', headers=H)
    d = (r.get_json() or {}).get('data') or {}
    check('s204 the futures route answers, with its fingerprint and the starting budget',
          r.status_code == 200 and 'fingerprint' in d and 'pre_budget' in d and 'offered' in d)
    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    bad = [post('/api/futures/possibility', {'kind': 'lottery', 'amount': 5}).status_code,
           post('/api/futures/possibility', {'kind': 'cost', 'amount': 800}).status_code,
           post('/api/futures/possibility', {'kind': 'income', 'amount': 0}).status_code,
           post('/api/futures/answer', {'key': 'baseline', 'answer': 'maybe'}).status_code]
    ok1 = post('/api/futures/possibility', {'kind': 'cost', 'amount': 800, 'month': '2027-03', 'label': 's204 repair'})
    pid = (ok1.get_json() or {}).get('data', {}).get('id')
    fp1 = c.get('/api/futures/fingerprint', headers=H).get_json()['data']['fingerprint']
    wd = c.post(f'/api/futures/possibility/{pid}/withdraw', headers=HJ, data='{}')
    fp2 = c.get('/api/futures/fingerprint', headers=H).get_json()['data']['fingerprint']
    with db_session() as s:
        hist = json.loads(s.query(AppSetting).filter_by(key='future_possibilities').first().value)
        n_tx2, n_bi2 = s.query(Transaction).count(), s.query(BudgetItem).count()
    check('s204 SC3 a stated possibility is kept as said (with its withdrawal), never as a transaction or budget line',
          bad == [400, 400, 400, 400] and ok1.status_code == 200 and wd.status_code == 200 and fp1 != fp2
          and [h.get('withdrawn', False) for h in hist if h['id'] == pid] == [False, True] and (n_tx2, n_bi2) == (n_tx, n_bi))
    ch = post('/api/futures/choose', {'key': 'no_such_future'})
    ap = post('/api/futures/choose', {'key': 'baseline', 'apply': True})
    check('s204 SC6 a path is chosen only if it is shown, and only "what is left goes to the debt" can change a figure',
          ch.status_code == 404 and ap.status_code in (400, 404))
    check('s204 SC6/SC5 the page draws the charts, marks stale figures, asks the SC4 question, and never calls the model',
          "API.get('/api/futures/fingerprint')" in app and 'id="futStale"' in app and 'Does this reflect your situation?' in app
          and 'Unlikely for me' in app and "_futChart('Cash on hand'" in app
          and 'callAI' not in app.split('async function renderFutures()')[1].split('async function _incomeChangePost')[0]
          and 'id="budgetFutures"' in ctx.html_src
          # a chosen future that is no longer offered (its change is now the plan) still shows the choice and its Undo
          and "That future isn't shown now" in app)

    with db_session() as s:
        for k, v in keep.items():
            s.query(AppSetting).filter_by(key=k).delete()
            if v is not None:
                s.add(AppSetting(key=k, value=v))
        s.commit()
