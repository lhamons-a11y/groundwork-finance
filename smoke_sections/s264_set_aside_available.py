"""Item 114 stage 1b (gw 2.0/AGENT_HANDS.md section 10; Rob 2026-10-30, R11/R12): a goal is money set aside inside an
account the person already has.

    H19   a goal names the account its money is kept in - one of the person's own checking, savings or cash accounts
    H20   each account: its balance, each goal set aside in it, and what is available; more set aside than it holds is
          said, and available is then $0.00
    H20b  the trip planner's checking and savings sources say what is available after, not the whole balance
    H20c  "Have you set money aside for this?" - the goal covers what it holds, the rest from available funds or credit;
          nothing moves
"""
import json


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ

    def data(r):
        d = r.get_json(silent=True) or {}
        return d.get('data', d)

    acct = data(c.post('/api/accounts', headers=HJ, data=json.dumps({'name': 's264 Rainy Day Savings', 'type': 'savings'})))
    aid = acct['id']
    c.post('/api/transactions', headers=HJ, data=json.dumps({'account_id': aid, 'date': '2026-09-01', 'description': 's264 deposit',
                                                             'merchant': 's264 deposit', 'amount': 1000, 'type': 'credit',
                                                             'category': 'Transfer', 'source': 'manual'}))
    card = data(c.post('/api/accounts', headers=HJ, data=json.dumps({'name': 's264 Store Card', 'type': 'credit_card'})))

    # H19
    bad = c.post('/api/sinking-funds', headers=HJ, data=json.dumps({'name': 's264 Wrong', 'monthly_contribution': 10,
                                                                     'account_id': card['id']}))
    fund = data(c.post('/api/sinking-funds', headers=HJ, data=json.dumps({'name': 's264 Beach trip', 'monthly_contribution': 50,
                                                                           'current_amount': 300, 'account_id': aid})))
    check('s264 H19 a goal names its account - a card cannot hold one; a savings account can',
          bad.status_code == 400 and fund.get('account_id') == aid)

    # H20
    def row():
        return next(x for x in data(c.get('/api/accounts/with-balances', headers=H)) if x['id'] == aid)
    r = row()
    check(f"s264 H20 the account: its balance, the goal set aside in it, and what is available ({r.get('balance')}, "
          f"{r.get('set_aside')}, {r.get('available')})",
          r['balance'] == 1000 and r['set_aside'] == 300 and r['available'] == 700 and r['short'] == 0
          and r['goals_set_aside'] == [{'name': 's264 Beach trip', 'amount': 300.0}])
    big = data(c.post('/api/sinking-funds', headers=HJ, data=json.dumps({'name': 's264 Too much', 'monthly_contribution': 10,
                                                                          'current_amount': 900, 'account_id': aid})))
    r = row()
    check('s264 H20 more set aside than the account holds is said: available $0.00 and how much short',
          r['set_aside'] == 1200 and r['available'] == 0 and r['short'] == 200)
    c.patch(f"/api/sinking-funds/{big['id']}", headers=HJ, data=json.dumps({'account_id': None}))
    check('s264 H19 a goal\'s account can be taken off again; the account then holds only the other goal',
          row()['set_aside'] == 300)

    # H20b: a trip paid from this account says what is available after
    trip = data(c.post('/api/trips', headers=HJ, data=json.dumps({'label': 's264 Beach', 'total': 250})))
    c.patch(f"/api/trips/{trip['id']}", headers=HJ, data=json.dumps({'sources': [{'kind': 'savings', 'ref_id': aid, 'amount': 250}]}))
    t = next(x for x in data(c.get('/api/trips', headers=H))['trips'] if x['id'] == trip['id'])
    left = (t.get('plan') or {}).get('left') or [{}]
    check(f"s264 H20b the trip planner: available after, not the whole balance ({left[0]})",
          left[0].get('set_aside') == 300 and left[0].get('available_after') == 450 and left[0].get('balance_after') == 750)

    # H20c: paid from the goal first; nothing moves
    plan = data(c.post('/api/sinking-funds/goal-plan', headers=HJ, data=json.dumps({'amount': 500, 'label': 'Beach vacation'})))
    first = (plan.get('goals') or [{}])[0]
    pp = data(c.post('/api/sinking-funds/goal-plan', headers=HJ, data=json.dumps({'amount': 500, 'fund_id': fund['id'], 'label': 'Beach'})))
    mine = next((a for a in pp.get('from_accounts') or [] if a['id'] == aid), {})
    after = next(x for x in data(c.get('/api/sinking-funds', headers=H)) if x['id'] == fund['id'])
    check('s264 H20c the goal that fits is offered first, never chosen; it covers what it holds, the rest from available '
          'funds (the paying goal\'s own money not counted twice) or credit; nothing moves',
          first.get('fits') and any(x['name'] == 's264 Beach trip' and x['fits'] for x in plan['goals'])
          and all(x['fits'] for x in plan['goals'][:[x['fits'] for x in plan['goals']].count(True)]) and pp['covers'] == 300 and pp['rest'] == 200
          and pp['goal_left'] == 0 and mine.get('available') == 1000 and mine.get('after') == 800
          and isinstance(pp.get('from_cards'), list) and after['current_amount'] == 300)

    # R20: the assistant's goal_plan reads the same answer; nothing set aside - every goal's money left out
    ng = data(c.get('/api/sinking-funds/goal-plan?amount=500&no_goal=1', headers=H))
    mine = next((a for a in ng.get('from_accounts') or [] if a['id'] == aid), {})
    check('s264 R20 nothing set aside: the whole amount against available funds - the goals\' money is not offered',
          ng.get('covers') == 0 and ng.get('rest') == 500 and ng.get('goal') is None and mine.get('available') == 700
          and mine.get('after') == 200)
    from core import agent_hands as ah
    check('s264 R20 the assistant has the goal plan as a lookup, and asks before it picks a goal',
          'goal_plan' in ah.FUNCS and 'goal_plan' in ah.LOOKUPS
          and "'clarify': 'Have you set money aside for this?'" in (ctx.BASE / 'core' / 'agent_hands.py').read_text(encoding='utf-8'))

    # The page
    js = ctx.app_src
    check('s264 the page: the goal form and each goal name the account; each account shows set aside and available; the '
          'trip planner and Before You Buy ask about goals first',
          'id="sfAccount"' in ctx.html_src and 'account_id: parseInt(g(\'sfAccount\')?.value) || null' in js
          and 'Which account is this money kept in?' in js and '${_setAsideLine(a)}' in js
          and '${_tripGoalAsk(t)}' in js and "_bybGoalAsk();" in js and 'Nothing moves. The goal is reduced when the purchase happens.' in js
          and 'available after (its balance less the' in js)
