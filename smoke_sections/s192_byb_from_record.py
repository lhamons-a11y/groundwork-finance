"""Item 73 stage 1 (gw 2.0/BYB_AGENT.md Y1 + Y6, RULED 2026-10-10; Rob: "build stage 1").

    Y1  a new repeating charge, or a charge that moved the payoff date, brought to Before You Buy from the record -
        once; the person's answer or dismissal ends it; nothing is read into why (TM5)
    Y6  each savings goal's date with and without, with the assumption in words
"""
import json
import re
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app = ctx.app_src
    from core import byb_offer as bo
    from core.database import AppSetting, BudgetItem, DebtAccount, SinkingFund, Transaction, db_session
    import server

    today = date.today()
    win = today - timedelta(days=365)
    rows = []
    n = 0

    def add(merchant, amounts_days):
        nonlocal n
        for amt, days_ago in amounts_days:
            n += 1
            rows.append((n, today - timedelta(days=days_ago), amt, merchant))
    add('Peacock', [(14.99, 70), (14.99, 40), (14.99, 10)])                    # new, monthly, steady
    add('Netflix', [(15.49, 70), (15.49, 40), (15.49, 10)])                    # steady, but a budget line already
    add('Spotify', [(11.99, d) for d in (250, 220, 190, 160, 130, 100, 70, 40, 10)])   # steady, but not new
    add('Walmart', [(52.10, 60), (140.33, 35), (23.75, 8)])                    # shopping, not a subscription
    add('Gym Class', [(20.0, 27), (20.0, 20), (20.0, 13), (20.0, 6)])           # new, weekly
    found = bo.new_recurring(rows, ['Netflix'], today, win)
    names = [o['name'] for o in found]
    check(f'Y1 a new steady repeating charge is found; one already budgeted, one that is not new, and shopping are not ({names})',
          sorted(names) == ['Gym Class', 'Peacock'])
    pk = next(o for o in found if o['name'] == 'Peacock')
    gym = next(o for o in found if o['name'] == 'Gym Class')
    check('Y1 the figures: the last charge, how often, since when, and a month\'s worth',
          pk['amount'] == 14.99 and pk['every'] == 'month' and pk['monthly'] == 14.99 and pk['since'] == (today - timedelta(days=70)).isoformat()
          and gym['every'] == 'week' and abs(gym['monthly'] - 20 * 52 / 12) < 0.01)

    goals = [{'id': 1, 'name': 'Denver trip', 'target': 1200, 'saved': 200, 'contribution': 100},
             {'id': 2, 'name': 'Tires', 'target': 600, 'saved': 500, 'contribution': 15},
             {'id': 3, 'name': 'Done', 'target': 100, 'saved': 100, 'contribution': 50}]
    gd = {x['name']: x for x in bo.goal_dates(goals, date(2026, 10, 10), monthly=20)}
    check(f'Y6 a goal\'s date now and with the purchase coming out of its contribution; one it would stop is said, not dated ({gd})',
          gd['Denver trip']['date_now'] == '2027-08' and gd['Denver trip']['date_with'] == '2027-11'
          and gd['Denver trip']['months_later'] == 3 and gd['Tires']['date_with'] is None and 'Done' not in gd)
    one = {x['name']: x for x in bo.goal_dates(goals, date(2026, 10, 10), one_time=300)}
    check('Y6 a one-time charge pushes a goal back by what it would have taken', one['Denver trip']['date_with'] == '2027-11')
    check('Y6 the assumption is said in words, as one way to see the size, not where the money comes from',
          'not a prediction' in bo.assumption(20, 0) and 'not a statement' in bo.assumption(0, 300))

    # the route, on the record
    with db_session() as s:
        for _, d, amt, m in rows:
            s.add(Transaction(date=d, amount=amt, type='debit', merchant=f's192 {m}', description=f's192 {m}'))
        s.add(BudgetItem(name='s192 Netflix', category='Streaming Video', amount=15.49, type='expense', is_active=True))
        s.add(SinkingFund(name='s192 Denver trip', target_amount=1200, current_amount=200, monthly_contribution=100, is_active=True))
        s.add(DebtAccount(name='s192 Card', current_balance=3000.0, interest_rate=21.0, minimum_payment=90.0, is_active=True))
        s.commit()
    real_lesson = server.large_charge_lesson
    server.large_charge_lesson = lambda *a, **k: {'lesson': {'months_cost': 2},
                                                   'charge': {'amount': 765.84, 'date': '2026-08-14', 'name': 's192 County Tax', 'category': 'Taxes'}}
    try:
        d1 = c.get('/api/byb/offers', headers=H).get_json()['data']
        mine = {o['name']: o for o in d1['offers'] if o['name'].startswith('s192')}
        pk = mine.get('s192 Peacock', {})
        im = pk.get('impact', {})
        g = next((x for x in im.get('goals', []) if x['name'] == 's192 Denver trip'), {})
        check(f'Y1 the route offers the new charges and the large one, each with what it does ({sorted(mine)})',
              {'s192 Peacock', 's192 Gym Class', 's192 County Tax'} <= set(mine) and 's192 Netflix' not in mine
              and im.get('left_with') is not None and abs(im['left_now'] - im['left_with'] - 14.99) < 0.01
              and g.get('months_later') is not None and im.get('assumption'))
        tax = mine.get('s192 County Tax', {})
        check('Y1 the large charge carries the months it cost, and has no "cancel" (it already happened)',
              tax.get('months_cost') == 2 and tax.get('kind') == 'large_charge')
        a1 = c.post('/api/byb/offers/answer', headers=HJ, data=json.dumps({'key': pk.get('key'), 'said': 'dismiss'}))
        a2 = c.post('/api/byb/offers/answer', headers=HJ, data=json.dumps({'key': tax.get('key'), 'said': 'meant'}))
        bad = c.post('/api/byb/offers/answer', headers=HJ, data=json.dumps({'key': tax.get('key'), 'said': 'later'}))
        d2 = c.get('/api/byb/offers', headers=H).get_json()['data']
        left = {o['name'] for o in d2['offers']}
        check('Y1 an answered or dismissed offer is not made again; "I meant to" is kept as said, a dismissal is not listed',
              a1.status_code == a2.status_code == 200 and bad.status_code == 400 and 's192 Peacock' not in left
              and 's192 County Tax' not in left and 's192 Gym Class' in left
              and any(x['key'] == tax.get('key') and x['said'] == 'meant' for x in d2['answered'])
              and not any(x['key'] == pk.get('key') for x in d2['answered']))
        with db_session() as s:
            unchanged = s.query(BudgetItem).filter_by(name='s192 Netflix').first().amount == 15.49
        check('Y1 an answer changes nothing else: no budget line, no decision record', unchanged)
    finally:
        server.large_charge_lesson = real_lesson

    js = app.split('async function renderBybFromRecord(')[1].split('\n}\n')[0]
    check('Y1 on the page: shown above the purchase list, no model, and no verdict or "why" words',
          'callAI(' not in js and 'id="bybFromRecord"' in ctx.html_src and 'renderBybFromRecord();' in app
          and not re.search(r'\b(impulse|splurge|waste|should|mistake|you need|careful)\b', js, re.I))
    srv = ctx.server_src.split('def byb_offers():')[1].split('\n@')[0]
    check('Y1 / TM4 the offers read the money only - never page views, sessions or app opens',
          not re.search(r'session_start|app_opens|page_view|budget_reviewed|engagement', srv))

    with db_session() as s:
        s.query(Transaction).filter(Transaction.merchant.like('s192 %')).delete(synchronize_session=False)
        s.query(BudgetItem).filter(BudgetItem.name.like('s192%')).delete(synchronize_session=False)
        s.query(SinkingFund).filter(SinkingFund.name.like('s192%')).delete(synchronize_session=False)
        s.query(DebtAccount).filter(DebtAccount.name.like('s192%')).delete(synchronize_session=False)
        s.query(AppSetting).filter_by(key='byb_offers_said').delete()
        s.commit()
