"""Item 74 (gw 2.0/GIFT_BUDGET.md G1-G9; Rob 2026-10-11: "build 74").

    G1  the year's gifts as one monthly set-aside: total ÷ 12 (a $100 birthday is $100 a year, never $1,200), a
        higher "covered by its date" amount only when a date comes first; one budget line, written on a tap, at
        one of the plan's own amounts
    G2  gift funds are sinking funds ('gift'), add their monthly amount once a month; old seasonal funds move on a tap
    G3  "Mark spent" keeps target and spent, in the Historian and on the fund ("Last time: ...")
    G4  gift charges before an occasion are offered; they become its spend only on a yes, only those offered
    G5  budgeted occasions 30 days out reach the dashboard's coming-up list, as a sentence of facts
    G6  a shared occasion: fixed amounts first, the rest split, what's left to assign shown
    G7  carried-over occasions (fractional ids) get whole ids and can be changed, logged and deleted
    G8  people and occasions in tables, carried from the settings once, the settings kept
"""
import json
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app = ctx.app_src
    from core import gifts as gf
    from core.database import (AppSetting, BudgetItem, Category, FundSpend, GiftOccasion, GiftPerson, GiftShare,
                               HistorianEntry, SinkingFund, Transaction, db_session)

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    patch = lambda path, body: c.patch(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    today = date.today()

    # A clean gift slate, with the settings this section changes put back at the end.
    with db_session() as s:
        saved = {k: (lambda r: r.value if r else None)(s.query(AppSetting).filter_by(key=k).first())
                 for k in ('gift_people_json', 'gift_seasons_json', gf.IMPORTED_KEY)}
        s.query(GiftShare).delete(); s.query(GiftOccasion).delete(); s.query(GiftPerson).delete()
        s.query(BudgetItem).filter_by(name=gf.SET_ASIDE_NAME).delete()
        for k in saved:
            s.query(AppSetting).filter_by(key=k).delete()
        # G7: the old list as it was, with a fractional occasion id, like Rob's birthday.
        s.add(AppSetting(key='gift_people_json', value=json.dumps([
            {'id': 1782615276010, 'name': 's202 Rob', 'relationship': 'family',
             'occasions': [{'id': 1782615276010.1562, 'type': 'birthday', 'date': '1980-03-02', 'budget': 0}]}])))
        s.commit()

    # ── G8 / G7: carried over once, whole ids, the setting kept ─────────────
    st = data(c.get('/api/gifts', headers=H))
    rob = next((p for p in st['people'] if p['name'] == 's202 Rob'), None)
    occ = rob and rob['occasions'][0]
    with db_session() as s:
        kept = s.query(AppSetting).filter_by(key='gift_people_json').first()
        row = s.get(GiftOccasion, occ['id']) if occ else None
        legacy = row.legacy_id if row else None
    check('s202 G8 the old gift list is carried into the tables, the setting kept as it was',
          rob is not None and occ is not None and '1782615276010.1562' in (kept.value if kept else ''))
    check('s202 G7 the carried-over occasion has a whole-number id; its old id is kept for the Historian',
          occ is not None and isinstance(occ['id'], int) and legacy == '1782615276010.1562')
    r1 = patch(f"/api/gifts/occasions/{occ['id']}", {'budget': 40})
    r2 = post(f"/api/gifts/occasions/{occ['id']}/spend", {'actual_spent': 35.5})
    st2 = data(c.get('/api/gifts', headers=H))
    again = next(p for p in st2['people'] if p['name'] == 's202 Rob')
    check('s202 G7 it can be budgeted and logged now',
          r1.status_code == 200 and r2.status_code == 200 and again['occasions'][0]['budget'] == 40
          and again['occasions'][0]['actual_spent'] == 35.5 and len(st2['people']) == len(st['people']))
    r3 = c.delete(f"/api/gifts/occasions/{occ['id']}", headers=H)
    check('s202 G7 ... and deleted; a second read does not carry it over again',
          r3.status_code == 200 and not next(p for p in data(c.get('/api/gifts', headers=H))['people']
                                                 if p['name'] == 's202 Rob')['occasions'])

    # ── G1: the year's plan ─────────────────────────────────────────────────
    far = today + timedelta(days=200)
    mom = data(post('/api/gifts/people', {'name': 's202 Mom', 'relationship': 'family'}))['id']
    oid = data(post('/api/gifts/occasions', {'person_id': mom, 'type': 'birthday',
                                            'date': f'1960-{far.month:02d}-{min(far.day, 28):02d}'}))['id']
    patch(f'/api/gifts/occasions/{oid}', {'budget': 100})
    plan = data(c.get('/api/gifts', headers=H))['plan']
    check(f"s202 G1 a $100 birthday is $100 a year: {plan['steady']} a month, 12 of them cover it to the cent",
          plan['total'] == 100 and plan['steady'] == 8.34 and 100 <= plan['steady'] * 12 < 100.12
          and '$100.00 ÷ 12 = $8.34' in plan['working'][1]
          # in a first year the date comes before 12 months of setting aside, so "covered by its date" is offered too
          and plan['to_cover'] == gf.cents_up(100 / gf.months_until(today, date.fromisoformat(plan['occasions'][0]['date']))))
    bad = post('/api/gifts/set-aside', {'monthly': 100})
    ok1 = post('/api/gifts/set-aside', {'monthly': plan['steady']})
    ok2 = post('/api/gifts/set-aside', {'monthly': plan['steady']})
    with db_session() as s:
        lines = s.query(BudgetItem).filter_by(name=gf.SET_ASIDE_NAME).all()
    check('s202 G1 the set-aside is ONE monthly line at the plan\'s amount; any other amount is refused',
          bad.status_code == 400 and ok1.status_code == 200 and ok2.status_code == 200 and len(lines) == 1
          and lines[0].amount == 8.34 and lines[0].category == 'Gifts')
    soon = today + timedelta(days=45)
    o2 = data(post('/api/gifts/occasions', {'person_id': mom, 'type': 'christmas',
                                           'date': f'2001-{soon.month:02d}-{min(soon.day, 28):02d}'}))['id']
    patch(f'/api/gifts/occasions/{o2}', {'budget': 300})
    plan2 = data(c.get('/api/gifts', headers=H))['plan']
    check(f"s202 G1 a date before its months to save offers a second amount, with its working ({plan2['to_cover']})",
          plan2['total'] == 400 and plan2['steady'] == 33.34 and plan2['to_cover'] and plan2['to_cover'] > plan2['steady']
          and 'covered by its own date' in plan2['working'][2] and plan2['line']['amount'] == 8.34)
    check('s202 G1 the page offers "Set aside for gifts" and no longer has "Budget it" (a yearly gift as a monthly line)',
          'Set aside for gifts' in app and "'budget-it'" not in app and '_giftBudgetIt' not in app)

    # ── G6: a shared occasion ───────────────────────────────────────────────
    check('s202 G6 the split: fixed first, the rest even (to the cent), nothing assigned shows as left',
          gf.split_shared(100, [(1, 40), (2, None), (3, None)]) == {'per_person': {1: 40.0, 2: 30.0, 3: 30.0}, 'fixed': 40.0, 'split': 60.0, 'left_to_assign': 0.0}
          and gf.split_shared(100, [(1, None), (2, None), (3, None)])['per_person'] == {1: 33.33, 2: 33.33, 3: 33.34}
          and gf.split_shared(100, [(1, 30)])['left_to_assign'] == 70.0
          and gf.split_shared(100, [(1, 80), (2, 50)])['left_to_assign'] == -30.0)
    dad = data(post('/api/gifts/people', {'name': 's202 Dad', 'relationship': 'family'}))['id']
    xmas = data(post('/api/gifts/occasions', {'shared': True, 'name': 's202 Family Christmas', 'type': 'christmas',
                                             'date': f'{today.year}-12-25', 'budget': 250}))['id']
    sh1 = data(post(f'/api/gifts/occasions/{xmas}/shares', {'person_id': mom}))['id']
    post(f'/api/gifts/occasions/{xmas}/shares', {'person_id': dad})
    dup = post(f'/api/gifts/occasions/{xmas}/shares', {'person_id': dad})
    patch(f'/api/gifts/shares/{sh1}', {'fixed_amount': 100})
    shared = next(o for o in data(c.get('/api/gifts', headers=H))['shared'] if o['id'] == xmas)
    check('s202 G6 a shared Christmas: Mom fixed at $100, Dad takes the other $150, nothing left to assign',
          dup.status_code == 400 and {s['name']: s['amount'] for s in shared['shares']} == {'s202 Mom': 100.0, 's202 Dad': 150.0}
          and shared['split']['left_to_assign'] == 0.0 and shared['label'] == 's202 Family Christmas')

    # ── G4: ledger charges, offered, never assumed ─────────────────────────
    past = today - timedelta(days=10)
    with db_session() as s:
        gifts = s.query(Category).filter_by(name='Gifts').first()
        if not gifts:
            gifts = Category(name='Gifts', type='expense'); s.add(gifts); s.flush()
        food = Category(name='s202 Groceries', type='expense'); s.add(food); s.flush()
        T = lambda d, amt, cat, m: Transaction(date=d, amount=amt, type='debit', category_id=cat.id, merchant=m, description=m)
        tx = [T(past - timedelta(days=20), 40.0, gifts, 's202 Target'), T(past - timedelta(days=3), 46.4, gifts, 's202 Etsy'),
              T(past - timedelta(days=60), 99.0, gifts, 's202 Too early'), T(past - timedelta(days=5), 70.0, food, 's202 Kroger')]
        s.add_all(tx); s.commit()
        tids = [t.id for t in tx]
    sis = data(post('/api/gifts/people', {'name': 's202 Sis', 'relationship': 'family'}))['id']
    bday = data(post('/api/gifts/occasions', {'person_id': sis, 'type': 'birthday',
                                             'date': f'1990-{past.month:02d}-{past.day:02d}'}))['id']
    patch(f'/api/gifts/occasions/{bday}', {'budget': 80})
    offer = data(c.get(f'/api/gifts/occasions/{bday}/charges', headers=H))
    with db_session() as s:
        before = s.get(GiftOccasion, bday).actual_spent
    check(f"s202 G4 the Gifts charges in the weeks before are listed, not used ({offer['total']})",
          [x['id'] for x in offer['charges']] == tids[:2] and offer['total'] == 86.4 and before is None
          and offer['date'] == past.isoformat())
    stray = post(f'/api/gifts/occasions/{bday}/charges', {'txn_ids': [tids[0], tids[3]]})
    none = post(f'/api/gifts/occasions/{bday}/charges', {'txn_ids': []})
    yes = post(f'/api/gifts/occasions/{bday}/charges', {'txn_ids': [tids[1]]})
    with db_session() as s:
        o = s.get(GiftOccasion, bday)
        got = (o.actual_spent, o.spent_txn_ids)
        he = [e for e in s.query(HistorianEntry).filter_by(event_category='gift_occasion_variance').all()
              if json.loads(e.context_json or '{}').get('gift_occasion_id') == bday]
    check('s202 G4 only charges it offered, only on a yes, only those picked: $46.40, in the Historian against $80',
          stray.status_code == 400 and none.status_code == 400 and yes.status_code == 200 and got == (46.4, str(tids[1]))
          and len(he) == 1 and he[0].expected_value == 80 and he[0].actual_value == 46.4
          and json.loads(he[0].context_json)['from_ledger'] is True)
    bro = data(post('/api/gifts/people', {'name': 's202 Bro', 'relationship': 'family'}))['id']
    bday2 = data(post('/api/gifts/occasions', {'person_id': bro, 'type': 'birthday',
                                              'date': f'1992-{past.month:02d}-{past.day:02d}'}))['id']
    offer2 = data(c.get(f'/api/gifts/occasions/{bday2}/charges', headers=H))
    check('s202 G4 a charge given to one occasion is not offered for another',
          [x['id'] for x in offer2['charges']] == [tids[0]])
    check("s202 G4 TM5: the page says Groundwork can't tell who a purchase was for, and asks the person to pick",
          "can't tell who a purchase was for" in app and 'class="gift-charge"' in app)

    # ── G5: occasions 30 days out reach the coming-up list ─────────────────
    up = data(c.get('/api/gifts/upcoming', headers=H))['occasions']
    check('s202 G5 a budgeted occasion 30 days out is not yet in the coming-up list; past ones are not either',
          all(o['days'] <= 30 for o in up) and not any(o['id'] in (oid, bday) for o in up))
    near = today + timedelta(days=12)
    o5 = data(post('/api/gifts/occasions', {'person_id': dad, 'type': 'birthday',
                                           'date': f'1958-{near.month:02d}-{near.day:02d}'}))['id']
    patch(f'/api/gifts/occasions/{o5}', {'budget': 60})
    up = data(c.get('/api/gifts/upcoming', headers=H))['occasions']
    hit = next((o for o in up if o['id'] == o5), None)
    check(f"s202 G5 ... and 12 days out it is, as a sentence of facts ({hit and hit['text']})",
          hit is not None and hit['days'] == 12 and hit['text'].startswith("s202 Dad's birthday, ")
          and '$60.00 budgeted' in hit['text'])
    check('s202 G5 the dashboard puts gift occasions beside bills', '_loadDashGiftUpcoming' in app
          and "API.get('/api/gifts/upcoming')" in app and '_dashGiftUpcoming' in app.split('function _renderDashUpcoming()')[1].split('\n}\n')[0])

    # ── G2: gift funds fill themselves; old seasonal funds move on a tap ─────
    dl = (today.replace(day=1) + timedelta(days=32 * 5)).replace(day=15)
    f = data(post('/api/gifts/funds', {'name': 's202 Christmas Fund', 'target_amount': 500, 'deadline': dl.isoformat()}))
    with db_session() as s:
        s.get(SinkingFund, f['id']).last_contributed_month = ''
        s.commit()
    c.post('/api/sinking-funds/auto-credit', headers=HJ, data='{}')
    c.post('/api/sinking-funds/auto-credit', headers=HJ, data='{}')
    with db_session() as s:
        fr = s.get(SinkingFund, f['id'])
        held = fr.current_amount
    listed = [x for x in data(c.get('/api/sinking-funds', headers=H)) if x['id'] == f['id']]
    check(f's202 G2 a gift fund adds its monthly amount itself, once a month ({held})',
          f['purpose'] == 'gift' and held > 0 and abs(held - f['monthly_needed']) < 0.01
          and listed and listed[0]['purpose'] == 'gift')
    with db_session() as s:
        s.query(AppSetting).filter_by(key='gift_seasons_json').delete()
        s.add(AppSetting(key='gift_seasons_json', value=json.dumps([
            {'id': 1700000000000, 'name': 's202 Old Season', 'target': 800, 'saved': 120, 'deadline': dl.isoformat()}])))
        s.commit()
    waiting = data(c.get('/api/gifts', headers=H))['seasons_to_move']
    mv = data(c.post('/api/gifts/seasons/move', headers=HJ, data='{}'))['moved']
    mv2 = data(c.post('/api/gifts/seasons/move', headers=HJ, data='{}'))['moved']
    st3 = data(c.get('/api/gifts', headers=H))
    moved = next((x for x in st3['funds'] if x['name'] == 's202 Old Season'), None)
    with db_session() as s:
        kept = json.loads(s.query(AppSetting).filter_by(key='gift_seasons_json').first().value)
    check('s202 G2 a seasonal fund moves on the tap with what it held, once; the setting keeps it, marked',
          len(waiting) == 1 and len(mv) == 1 and mv2 == [] and moved and moved['current_amount'] == 120
          and moved['target_amount'] == 800 and st3['seasons_to_move'] == []
          and kept[0]['moved_to_fund_id'] == moved['id'] and kept[0]['saved'] == 120)

    # ── G3: "Mark spent" keeps the record ───────────────────────────────────
    sp = post(f"/api/gifts/funds/{moved['id']}/spent", {'spent': 1140})
    after = data(sp)
    with db_session() as s:
        rows = s.query(FundSpend).filter_by(fund_id=moved['id']).all()
        he = [e for e in s.query(HistorianEntry).filter_by(event_category='gift_fund_spent').all()
              if json.loads(e.context_json or '{}').get('sinking_fund_id') == moved['id']]
    check(f"s202 G3 Mark spent keeps target and spent, sets the fund to $0, says it next time ({after and after['last_spend']})",
          sp.status_code == 200 and after['current_amount'] == 0 and len(rows) == 1 and rows[0].target == 800
          and rows[0].spent == 1140 and len(he) == 1 and he[0].expected_value == 800 and he[0].actual_value == 1140
          and after['last_spend']['text'] == f'Last time: target $800.00, spent $1,140.00 ({today.strftime("%b %Y")})')
    check('s202 G3 the page asks what was spent before marking it', "API.post(`/api/gifts/funds/${f.id}/spent`" in app
          and 'gsSpentAmt' in app)

    # ── dates, and AI off ───────────────────────────────────────────────────
    check('s202 dates: a yearly occasion rolls to next year; a one-time one that passed has no next date; 29 Feb',
          gf.next_occurrence('birthday', '1980-01-01', date(2026, 6, 1)) == date(2027, 1, 1)
          and gf.next_occurrence('wedding', '2026-05-01', date(2026, 6, 1)) is None
          and gf.next_occurrence('wedding', '2026-07-01', date(2026, 6, 1)) == date(2026, 7, 1)
          and gf.next_occurrence('birthday', '2000-02-29', date(2026, 3, 1)) == date(2027, 2, 28)
          and gf.next_occurrence('birthday', '12-25', date(2026, 6, 1)) == date(2026, 12, 25))
    plan_src = app.split('function _renderGiftPlan() {')[1].split('\n}\n')[0]
    check('s202 G9 AI off: the plan, the charges and the funds are figures from the server, no AI call on the way',
          'callAI' not in plan_src and '_rcAnalyzeWithAI' not in plan_src
          and 'callAI' not in app.split('async function _giftOfferCharges(oid) {')[1].split('\n}\n')[0])

    # put the gift settings back the way the rest of the gate expects them
    with db_session() as s:
        for k, v in saved.items():
            s.query(AppSetting).filter_by(key=k).delete()
            if v is not None:
                s.add(AppSetting(key=k, value=v))
        s.commit()
