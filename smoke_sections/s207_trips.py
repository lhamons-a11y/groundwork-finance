"""Item 61 (gw 2.0/TRIP_FUNDING_COACH.md T1-T9; Rob 2026-10-12: "I accept T1 - T9").

    T1  trips are records; the old saved trip is carried in once; "going" comes only from the person's tap
    T2  a trip is never a budget line: a trip fund for saving ahead, and the trip shown in its own months
    T3  the money split by source - checking, savings, a fund, one or more cards, saving ahead - adding up to the trip
    T4  the way back per source; T5 one debt plan: a card's share is projected until the real charge is linked, then
        dropped (counted once); debt first / rebuild first / split priced by the one engine
    T6  the coach line is facts; T7 after the trip, charges count only on a yes; T8 the futures see a going trip
"""
import json
import math
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app = ctx.app_src
    from core import trips as tr
    from core.consequence import Card, simulate_payoff
    from core.database import (Account, AppSetting, BudgetItem, Category, DebtAccount, HistorianEntry, SinkingFund,
                               Transaction, Trip, TripBooking, db_session)

    post = lambda p, b: c.post(p, headers=HJ, data=json.dumps(b))
    patch = lambda p, b: c.patch(p, headers=HJ, data=json.dumps(b))
    data = lambda r: (r.get_json() or {}).get('data')

    # the one engine: a month-by-month extra changes the answer only through that extra
    cards = [Card(balance=4000.0, rate=22.0, minimum=100.0, name='s207 A'), Card(balance=2000.0, rate=9.0, minimum=60.0, name='s207 B')]
    base = simulate_payoff(cards, 400.0, start_month='2026-11')['months']
    same = simulate_payoff(cards, 400.0, start_month='2026-11', extra_schedule=[])['months']
    faster = simulate_payoff(cards, 400.0, start_month='2026-11', extra_schedule=[300.0] * 4)['months']
    check(f's207 T5 the payoff engine takes a month-by-month extra and nothing else changes ({base}, {same}, {faster})',
          base == same and faster < base)

    # T5's orders, by hand: the surplus pays the trip's card amount first, or the cash first
    o = tr.orders(cards, 400.0, 'avalanche', '2026-11', 300.0, 900.0, 600.0, split_pct=50)
    check(f"s207 T5 debt first / rebuild first / split: the rebuild dates are the arithmetic, the debt dates the engine's ({o})",
          o['debt_first']['rebuild_months'] == 3 + 2 and o['rebuild_first']['rebuild_months'] == 2
          and o['split']['rebuild_months'] == math.ceil(600 / 150)
          and o['debt_first']['debt_months'] <= o['rebuild_first']['debt_months']
          and o['debt_first']['debt_months'] == simulate_payoff(cards, 400.0, start_month='2026-11', today_key='2026-11', extra_schedule=[300.0] * 3)['months']
          and tr.orders(cards, 400.0, 'avalanche', '2026-11', 0, 900.0, 600.0) == {})
    check('s207 T6 the coach line is facts on the goal, never a verdict',
          tr.coach_line('debt', 12, {'debt_months': 14, 'rebuild_months': 5}, '2026-11', 600)
          == 'Going moves your debt-free date from November 2027 to January 2028, and the money from checking and savings is back by April 2027.'
          and not any(w in (tr.coach_line('debt', 12, {'debt_months': 14, 'rebuild_months': 5}, '2026-11', 600) or '').lower()
                      for w in ('should', 'afford', 'mistake', 'warning', 'risky')))

    # a clean slate, the old saved trip in place
    soon = date.today() + timedelta(days=60)
    with db_session() as s:
        keep = {k: (lambda r: r.value if r else None)(s.query(AppSetting).filter_by(key=k).first())
                for k in ('trip_budget', tr.CARRIED_KEY)}
        s.query(Trip).delete()
        for k in keep:
            s.query(AppSetting).filter_by(key=k).delete()
        s.add(AppSetting(key='trip_budget', value=json.dumps({'dest': 's207 Old Plan', 'depart': soon.isoformat(),
                                                              'ret': (soon + timedelta(days=3)).isoformat(),
                                                              'transport': 300, 'hotel': 420, 'total': 790})))
        card = DebtAccount(name='s207 Visa', begin_balance=1000, current_balance=1000, interest_rate=21.9,
                           minimum_payment=40, is_active=True, debt_type='credit', credit_limit=5000)
        chk = Account(name='s207 Checking', type='checking', is_active=True)
        s.add_all([card, chk]); s.commit()
        ids = {'card': card.id, 'chk': chk.id}
        n_items = s.query(BudgetItem).count()

    t0 = data(c.get('/api/trips', headers=H))['trips']
    t1 = data(c.get('/api/trips', headers=H))['trips']
    old = [t for t in t0 if t['label'] == 's207 Old Plan']
    check('s207 T1 the old saved trip is carried in once, as planning, with its lines; the setting is kept',
          len(old) == 1 and old[0]['status'] == 'planning' and old[0]['total'] == 790
          and [x['label'] for x in old[0]['lines']] == ['Getting there', 'Lodging'] and len(t1) == len(t0))

    bad = post('/api/trips', {'dest': '', 'total': 100}).status_code
    going = data(post('/api/trips', {'dest': 's207 Denver', 'depart': soon.isoformat(), 'ret': (soon + timedelta(days=4)).isoformat(),
                                     'transport': 600, 'hotel': 840, 'dining': 300, 'buffer': 174, 'total': 1914}))
    check("s207 T1 \"I'm going\" saves the trip as going; a trip needs a destination and a total",
          bad == 400 and going['status'] == 'going' and going['total'] == 1914 and going['left_to_assign'] == 1914)
    tid = going['id']

    over = patch(f'/api/trips/{tid}', {'sources': [{'kind': 'checking', 'ref_id': ids['chk'], 'amount': 2000}]}).status_code
    notcard = patch(f'/api/trips/{tid}', {'sources': [{'kind': 'card', 'ref_id': 999999, 'amount': 100}]}).status_code
    r = data(patch(f'/api/trips/{tid}', {'sources': [
        {'kind': 'card', 'ref_id': ids['card'], 'amount': 900}, {'kind': 'checking', 'ref_id': ids['chk'], 'amount': 514},
        {'kind': 'save_ahead', 'amount': 500}]}))
    with db_session() as s:
        f = s.get(SinkingFund, r['fund_id']) if r['fund_id'] else None
        fund = (f.purpose, f.target_amount, f.deadline) if f else None
        n_items2 = s.query(BudgetItem).count()
    check(f"s207 T3 the split must add up and name the person's own sources; saving ahead makes the trip's own fund ({fund})",
          over == 400 and notcard == 400 and r['left_to_assign'] == 0 and r['assigned'] == 1914
          and fund == ('trip', 500, soon.isoformat()))
    check('s207 T2 a trip is never a budget line: nothing was added to the budget',
          n_items2 == n_items and "it isn't a budget line" in app)
    p = r['plan']
    card_left = next(x for x in p['left'] if x['kind'] == 'card')
    check(f"s207 T3/T4 each source says what it leaves, and each card gets its payoff rows ({card_left.get('available_after')})",
          card_left['available_after'] == 5000 - 1000 - 900 and [x['months'] for x in card_left['payoff']] == [3, 6, 12]
          and p['card_total'] == 900 and p['cash_total'] == 514 and p['rebuild']['checking']['monthly'] == round(514 / 6, 2))
    check('s207 T4 the rebuild runs over 3, 6 or 12 months only',
          patch(f'/api/trips/{tid}', {'rebuild_months': 5}).status_code == 400
          and data(patch(f'/api/trips/{tid}', {'rebuild_months': 3}))['plan']['rebuild']['checking']['months'] == 3)

    # T5: counted once - once the booking's real charge is linked, the projection drops
    with db_session() as s:
        b = TripBooking(trip_label='s207 Denver', airline='s207 Air', amount=900, booked_on=date.today(),
                        paid_with_kind='card', debt_account_id=ids['card'], charged_amount=900, status='booked')
        s.add(b); s.commit(); bid = b.id
    p2 = data(c.get('/api/trips', headers=H))['trips']
    p2 = next(t for t in p2 if t['id'] == tid)['plan']
    with db_session() as s:
        b = s.get(TripBooking, bid); b.matched_transaction_id = None; b.matched_debt_entry_id = None
        from core.database import DebtLedgerEntry
        e = DebtLedgerEntry(debt_account_id=ids['card'], entry_type='charge', amount=900, entry_date=date.today(),
                            merchant='s207 Air', description='') if hasattr(DebtLedgerEntry, 'entry_type') else None
        if e is not None:
            s.add(e); s.flush(); b.matched_debt_entry_id = e.id
        s.commit()
    p3 = next(t for t in data(c.get('/api/trips', headers=H))['trips'] if t['id'] == tid)['plan']
    check(f"s207 T5 a card's share is projected until its booking's charge is linked, then dropped - counted once ({p2['card_total']} -> {p3['card_total']})",
          p2['card_total'] == 900 and p3['card_total'] == 0
          and list(p3['shares'].values())[0]['linked'] == 900 and list(p2['shares'].values())[0]['projected'] == 900)
    bad_order = patch(f'/api/trips/{tid}', {'pay_order': 'whatever'}).status_code
    bad_split = patch(f'/api/trips/{tid}', {'pay_order': 'split', 'split_pct': 150}).status_code
    ok_order = data(patch(f'/api/trips/{tid}', {'pay_order': 'debt_first'}))
    check('s207 T5 the order is the person\'s: debt first, rebuild first, or a split they set; nothing else',
          bad_order == 400 and bad_split == 400 and ok_order['pay_order'] == 'debt_first')

    # T2: the trip in its months, derived
    inm = data(c.get(f'/api/trips/in-month?month={soon.strftime("%Y-%m")}', headers=H))['trips']
    out = data(c.get(f'/api/trips/in-month?month={(soon + timedelta(days=95)).strftime("%Y-%m")}', headers=H))['trips']
    check('s207 T2 the trip shows in the months it touches, and no other', any(t['id'] == tid for t in inm) and not any(t['id'] == tid for t in out))

    # T8: the futures see the going trip, as the person's own statement, in its month
    import server
    from core import futures as fu
    with db_session() as s:
        tp = [x for x in server._going_trip_possibilities(s) if x.get('from_trip') == tid]
    inforce = fu.possibilities_in_force(tp)
    check(f"s207 T8 a going trip is a known cost in its month in every future - its cash part, tagged as said ({tp})",
          len(tp) == 1 and tp[0]['month'] == soon.strftime('%Y-%m') and tp[0]['amount'] == 514 and tp[0]['kind'] == 'cost'
          and len(inforce) == 1 and "a trip you're going on" in app)

    # T7: after the trip - only on a yes, only charges offered
    past = date.today() - timedelta(days=10)
    with db_session() as s:
        trav = s.query(Category).filter_by(name='Travel').first()
        if not trav:
            trav = Category(name='Travel', type='expense'); s.add(trav); s.flush()
        done_trip = Trip(label='s207 Past Trip', depart=(past - timedelta(days=3)).isoformat(), ret=past.isoformat(),
                         total=800, status='going')
        x1 = Transaction(date=past - timedelta(days=1), amount=310.0, type='debit', category_id=trav.id, merchant='s207 Hotel', description='s207 Hotel')
        x2 = Transaction(date=past - timedelta(days=40), amount=99.0, type='debit', category_id=trav.id, merchant='s207 Old', description='s207 Old')
        s.add_all([done_trip, x1, x2]); s.commit()
        did, xid, oldid = done_trip.id, x1.id, x2.id
    offer = data(c.get(f'/api/trips/{did}/charges', headers=H))
    stray = post(f'/api/trips/{did}/charges', {'ids': [f't{oldid}']}).status_code
    with db_session() as s:
        still = s.get(Trip, did).status
    yes = data(post(f'/api/trips/{did}/charges', {'ids': [f't{xid}']}))
    with db_session() as s:
        he = [e for e in s.query(HistorianEntry).filter_by(event_category='trip_actual').all()
              if json.loads(e.context_json or '{}').get('trip_id') == did]
    check(f"s207 T7 after the trip, its Travel charges are offered; only those, only on a yes ({offer['total']})",
          offer['ready'] and [x['id'] for x in offer['charges']] == [f't{xid}'] and stray == 400 and still == 'going'
          and yes['status'] == 'done' and yes['actual_spent'] == 310 and len(he) == 1 and he[0].expected_value == 800)

    # T1/TM5: "going" only from the tap; the page never sets it on its own; no AI on the way
    trip_js = app.split('function tripImGoing() {')[1].split('// T2: on the Budget page')[0]
    check("s207 T1/T9 \"I'm going\" is a confirmed tap, nothing else commits a trip, and no model is called",
          'confirmAction(' in trip_js and "API.post('/api/trips', d)" in trip_js and 'callAI' not in trip_js
          and app.count("API.post('/api/trips',") == 1 and "status === 'planning'" in trip_js)
    check('s207 TM1: nothing in the trip code moves or pays money - no payment or transfer route is called',
          not any(w in trip_js for w in ('/pay', 'transfer', '/deposit')))

    with db_session() as s:
        s.query(Trip).filter(Trip.label.like('s207%')).delete(synchronize_session=False)
        for k, v in keep.items():
            s.query(AppSetting).filter_by(key=k).delete()
            if v is not None:
                s.add(AppSetting(key=k, value=v))
        s.commit()
