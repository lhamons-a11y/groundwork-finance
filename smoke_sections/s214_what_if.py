"""Item 65 W5 (gw 2.0/AGENT_W_ITEMS.md; Rob 2026-10-12: "approve as recommended"): cause and effect you can move.

    W5-a  one engine: the what-if runs through the futures' own run() and the one payoff engine - no second calculation
    W5-b  nothing is saved while figures move; "Make this my plan" says exactly what it changes first, and has Undo
    W5-c  the Debt page's and the mortgage's sliders stay, and open the panel with their figure in it
"""
import json


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app, html = ctx.app_src, ctx.html_src
    import server
    from core import futures as fu
    from core.consequence import Card
    from core.database import AppSetting, BudgetItem, db_session

    cards = [Card(balance=6000.0, rate=20.0, minimum=150.0, name='s214 Visa'),
             Card(balance=2000.0, rate=10.0, minimum=50.0, name='s214 Loan')]
    base = {'income': 5000.0, 'income_months': 3, 'spend': 3500.0, 'debt_lines': 600.0, 'debt_pay': 600.0,
            'minimums': 200.0, 'owed': 8000.0, 'cards': cards, 'strategy': 'avalanche', 'cash': 1000.0, 'goal': 'debt',
            'start_month': '2026-11', 'spend_record': [], 'known_costs': []}
    st = fu.build(base)
    by = {s['key']: s for s in st['scenarios']}

    same = fu.what_if(base, [], {})
    check('s214 W5-a nothing moved is as things are, figure for figure, and names no change',
          same['what_if']['cash'] == by['baseline']['cash'] and same['what_if']['debt_months'] == by['baseline']['debt_months']
          and same['as_things_are']['cash'] == by['baseline']['cash'] and same['changed'] == [])
    more = fu.what_if(base, [], {'debt_pay': 1500})
    check(f"s214 W5-a one engine: moving the debt payment to what is left gives exactly the futures card's own \"what is left goes to the debt\" ({more['what_if']['debt_months']} months)",
          more['what_if']['debt_months'] == by['surplus_to_goal']['debt_months'] and more['what_if']['cash'] == by['surplus_to_goal']['cash']
          and more['changed'] == [{'key': 'debt_pay', 'label': 'Debt payment a month', 'from': 600.0, 'to': 1500.0}]
          and more['what_if']['measure']['value'] < more['as_things_are']['measure']['value'] and more['note'] == 'A what-if, not a prediction.')
    sv = fu.what_if({**base, 'goal': 'savings'}, [], {'save': 300})
    check(f"s214 W5 set aside: it leaves the cash but stays the person's - the year's total counts it back ({sv['what_if']['set_aside']})",
          sv['what_if']['set_aside'] == 3600.0 and sv['what_if']['cash'][-1] == sv['as_things_are']['cash'][-1] - 3600.0
          and sv['what_if']['measure']['value'] == sv['as_things_are']['measure']['value'])
    several = fu.what_if(base, [], {'income': 4500, 'spend': 3300, 'one_time': {'amount': 1200, 'month': '2027-02'}})
    w, a = several['what_if'], several['as_things_are']
    check(f"s214 W5 several figures at once, each named: income, spending and a one-time cost in its month ({[x['key'] for x in several['changed']]})",
          [x['key'] for x in several['changed']] == ['income', 'spend', 'one_time'] and several['changed'][2]['month'] == '2027-02'
          and w['cash'][2] - a['cash'][2] == 3 * (-500 + 200) and w['cash'][3] - a['cash'][3] == 4 * (-300) - 1200)
    low = fu.what_if(base, [], {'debt_pay': 150})
    check('s214 W5 a debt payment below the minimums says so: no payoff date is worked out',
          low['below_minimums'] and low['what_if']['debt_months'] is None and not fu.what_if(base, [], {'debt_pay': 200})['below_minimums'])

    # W5-b through the routes, on this record
    orig = server._futures_inputs
    server._futures_inputs = lambda session, today=None: dict(base, cards=list(cards))
    try:
        with db_session() as s:
            s.query(AppSetting).filter(AppSetting.key.in_(['monthly_budget', 'what_if_applied', 'future_possibilities'])).delete(synchronize_session=False)
            s.add(AppSetting(key='monthly_budget', value='600'))
            sl = BudgetItem(name='s214 Savings', category='Savings', amount=100.0, type='expense', is_active=True)
            s.add(sl); s.commit(); sid = sl.id
        data = lambda r: (r.get_json() or {}).get('data') or {}
        post = lambda p, b: c.post(p, headers=HJ, data=json.dumps(b))
        ch = {'debt_pay': 900, 'save': 50, 'income': 5200, 'one_time': {'amount': 400, 'month': '2027-01'}}
        moved = post('/api/futures/what-if', {'changes': ch})
        with db_session() as s:
            untouched = (s.query(AppSetting).filter_by(key='monthly_budget').first().value, s.get(BudgetItem, sid).amount)
        preview = data(post('/api/futures/what-if/plan', {'changes': ch}))
        check(f"s214 W5-b moving figures saves nothing; the plan says first exactly what it changes, and what it doesn't ({[x['what'] for x in preview.get('changes', [])]})",
              moved.status_code == 200 and untouched == ('600', 100.0)
              and [(x['key'], x['before'], x['after']) for x in preview['changes']] == [('debt_pay', '600', 900.0), ('save', 100.0, 150.0), ('one_time', None, 400.0)]
              and any('Income isn' in n for n in preview['not_changed']))
        done = post('/api/futures/what-if/plan', {'changes': ch, 'apply': True})
        with db_session() as s:
            applied = (s.query(AppSetting).filter_by(key='monthly_budget').first().value, s.get(BudgetItem, sid).amount,
                       [p for p in json.loads(s.query(AppSetting).filter_by(key='future_possibilities').first().value) if not p.get('withdrawn')])
        undo = post('/api/futures/what-if/undo', {})
        with db_session() as s:
            back = (s.query(AppSetting).filter_by(key='monthly_budget').first().value, s.get(BudgetItem, sid).amount)
            live = fu.possibilities_in_force(json.loads(s.query(AppSetting).filter_by(key='future_possibilities').first().value))
        check(f"s214 W5-b \"Make this my plan\" changes exactly those, and Undo puts every one back ({applied[:2]} -> {back})",
              done.status_code == 200 and applied[0] == '900.0' and applied[1] == 150.0 and len(applied[2]) == 1
              and undo.status_code == 200 and back == ('600', 100.0) and live == [])
    finally:
        server._futures_inputs = orig
        with db_session() as s:
            s.query(AppSetting).filter(AppSetting.key.in_(['monthly_budget', 'what_if_applied', 'future_possibilities'])).delete(synchronize_session=False)
            s.query(BudgetItem).filter_by(name='s214 Savings').delete()
            s.commit()

    panel = app.split('function whatIfHtml() {')[1].split('\n}\n')[0]
    check('s214 W5 the panel sits on the futures card: income, spending, debt payment, set aside, a one-time cost and its month; labelled a what-if, not a prediction',
          '${whatIfHtml()}' in app.split('function futuresHtml(st) {')[1].split('\n}\n')[0]
          and all(f"row('{k}'" in panel for k in ('income', 'spend', 'debt_pay', 'save')) and "whatIfOne('month'" in panel
          and 'A what-if, not a prediction.' in panel and "API.post('/api/futures/what-if', { changes: _wi })" in app)
    check('s214 W5-c the Debt page slider and the mortgage slider stay, and each opens the panel with its figure in it',
          'id="whatIfSlider"' in html and 'openWhatIf({ add_debt: _debtWhatIfExtra || 0 })' in html
          and 'id="mortgageExtraSlider"' in app and 'openWhatIf({ add_debt: _mortgageWhatIfExtra })' in app)
