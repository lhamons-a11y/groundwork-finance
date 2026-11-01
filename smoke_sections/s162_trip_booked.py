"""\"I booked it\" (gw 2.0/TRIP_BOOKED.md, item 50; Rob 2026-10-08: "approve B1-B8 as recommended").

    B1  the confirmation number is the user's own typing: nothing reads a page for it, and it never reaches a log
    B2  a booking is a planned record: no transaction, no ledger entry, no balance moves when it is saved
    B3  the real charge is proposed only within $1.00, 7 days, on the chosen card or account, naming the airline -
        and linked only on the user's yes; a row is never matched twice (counted once)
    B4  paid with: credit cards and checking accounts
    B6  cancelled is kept, never deleted; a refund is matched like a charge
    B7  the trip's flight line shows booked, then charged (both when they differ)
    B8  the trip_bookings table is versioned (s51/s67 hold the recipe)
"""
import json
import re
import shutil
import subprocess
from datetime import date, timedelta


def _fn(src, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', src, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, HJ, BASE, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE, ctx.app_src
    from core.database import (DebtAccount, Account, Transaction, DebtLedgerEntry, TripBooking, db_session)
    from core.trip_booking import names_airline, trip_cost
    import migrate

    # The bump that added the table, or a later one (a later bump keeps the table: s67 upgrades its saved schema)
    check('s162 B8 the trip_bookings table is versioned', migrate.SCHEMA_VERSION >= '20261008-trip-bookings'
          and (BASE / 'tests/schema/20261008-trip-bookings.sql').exists())
    check('s162 B3 the airline is named as whole words ("DELTA AIR 0062" names Delta; "DELTAPLEX" does not)',
          names_airline('DELTA AIR 0062345', 'Delta') and names_airline('Southwest Airlines', 'southwest')
          and not names_airline('DELTAPLEX', 'Delta') and names_airline('AMERICAN AIRLINES', 'American Airlines'))

    made = {'debt': [], 'acct': [], 'tx': [], 'le': [], 'bk': []}
    try:
        d0 = date.today()
        with db_session() as s:
            acct = Account(name='s162 Checking', type='checking', is_active=True)
            card_acct = Account(name='s162 Visa account', type='credit', is_active=True)
            s.add_all([acct, card_acct]); s.flush()
            visa = DebtAccount(name='s162 Visa', current_balance=1000.0, interest_rate=22.0, minimum_payment=40.0,
                               credit_limit=5000.0, debt_type='credit', is_active=True, linked_account_id=card_acct.id)
            s.add(visa); s.commit()
            made['acct'] += [acct.id, card_acct.id]; made['debt'].append(visa.id)
            ids = {'acct': acct.id, 'card_acct': card_acct.id, 'visa': visa.id}

        ba = c.get('/api/trip/booking-accounts', headers=H).get_json()['data']
        check('s162 B4 paid with lists the credit card and the checking account (airlines take debit cards)',
              any(x['id'] == ids['visa'] for x in ba['cards']) and any(x['id'] == ids['acct'] for x in ba['accounts'])
              and not any(x['id'] == ids['card_acct'] for x in ba['accounts']))

        with db_session() as s:
            counts = (s.query(Transaction).count(), s.query(DebtLedgerEntry).count(),
                      s.get(DebtAccount, ids['visa']).current_balance)
        r = c.post('/api/trip/bookings', headers=HJ, data=json.dumps({
            'trip_label': 's162 Denver · 2026-11-01', 'airline': 'Delta', 'amount': 612.48,
            'booked_on': d0.isoformat(), 'paid_with_kind': 'card', 'debt_account_id': ids['visa'],
            'confirmation': 'S162ZQ'})).get_json()['data']
        made['bk'].append(r['id'])
        with db_session() as s:
            after = (s.query(Transaction).count(), s.query(DebtLedgerEntry).count(),
                     s.get(DebtAccount, ids['visa']).current_balance)
        check('s162 B2 saving a booking writes no transaction, no ledger entry, and moves no balance',
              r['status'] == 'booked' and after == counts)

        # The real charge arrives, plus three that must not be proposed.
        with db_session() as s:
            les = [DebtLedgerEntry(debt_account_id=ids['visa'], entry_type='charge', amount=612.48, entry_date=d0 + timedelta(days=2),
                                   merchant='DELTA AIR 0062345', description='', source_type='import'),
                   DebtLedgerEntry(debt_account_id=ids['visa'], entry_type='charge', amount=640.00, entry_date=d0 + timedelta(days=2),
                                   merchant='DELTA AIR 0062399', description='', source_type='import'),
                   DebtLedgerEntry(debt_account_id=ids['visa'], entry_type='charge', amount=612.48, entry_date=d0 + timedelta(days=12),
                                   merchant='DELTA AIR 0062311', description='', source_type='import'),
                   DebtLedgerEntry(debt_account_id=ids['visa'], entry_type='charge', amount=612.48, entry_date=d0 + timedelta(days=1),
                                   merchant='UNITED 016', description='', source_type='import')]
            s.add_all(les); s.commit()
            made['le'] += [e.id for e in les]
        cand = c.get(f"/api/trip/bookings/{r['id']}/candidates", headers=H).get_json()['data']['candidates']
        check('s162 B3 only the charge within $1.00 and 7 days, naming Delta, on that card is proposed',
              [x['id'] for x in cand] == [made['le'][0]])
        bad = c.post(f"/api/trip/bookings/{r['id']}/match", headers=HJ, data=json.dumps({'kind': 'ledger', 'id': made['le'][1]}))
        check('s162 B3 a row outside the rule cannot be matched without "by hand"', bad.status_code == 400)
        m = c.post(f"/api/trip/bookings/{r['id']}/match", headers=HJ,
                   data=json.dumps({'kind': 'ledger', 'id': made['le'][0]})).get_json()['data']
        check('s162 B3 the user\'s yes links it: the booking shows charged, at the charged amount',
              m['status'] == 'charged' and m['charged_amount'] == 612.48 and m['matched'])
        with db_session() as s:
            again = (s.query(Transaction).count(), s.query(DebtLedgerEntry).count() - 4)
        check('s162 B3 counted once: matching adds nothing - the imported charge is the only record of the money',
              again == counts[:2])

        # A second booking cannot take the same row.
        r2 = c.post('/api/trip/bookings', headers=HJ, data=json.dumps({
            'trip_label': 's162 Denver · 2026-11-01', 'airline': 'Delta', 'amount': 612.48, 'booked_on': d0.isoformat(),
            'paid_with_kind': 'card', 'debt_account_id': ids['visa']})).get_json()['data']
        made['bk'].append(r2['id'])
        cand2 = c.get(f"/api/trip/bookings/{r2['id']}/candidates", headers=H).get_json()['data']['candidates']
        check('s162 B3 a row already matched to one booking is never proposed for another', made['le'][0] not in [x['id'] for x in cand2])

        # Debit: a checking account, matched through its imported transaction; by hand outside the rule.
        r3 = c.post('/api/trip/bookings', headers=HJ, data=json.dumps({
            'trip_label': 's162 Austin · 2026-12-01', 'airline': 'Southwest', 'amount': 189.00, 'booked_on': d0.isoformat(),
            'paid_with_kind': 'account', 'account_id': ids['acct']})).get_json()['data']
        made['bk'].append(r3['id'])
        with db_session() as s:
            tx = Transaction(date=d0 + timedelta(days=1), description='SOUTHWES 5262 DALLAS', merchant='', amount=201.50,
                             type='debit', account_id=ids['acct'])
            s.add(tx); s.commit(); made['tx'].append(tx.id)
        cand3 = c.get(f"/api/trip/bookings/{r3['id']}/candidates", headers=H).get_json()['data']['candidates']
        hand = c.post(f"/api/trip/bookings/{r3['id']}/match", headers=HJ,
                      data=json.dumps({'kind': 'transaction', 'id': made['tx'][0], 'by_hand': True})).get_json()['data']
        check('s162 B3 a debit charge outside the rule is not proposed, and the user can link it by hand',
              cand3 == [] and hand['status'] == 'charged' and hand['charged_amount'] == 201.50)
        check('s162 B7 a charge that differs from the booking shows both',
              hand['trip_cost'] == {'amount': 201.50, 'label': 'charged', 'differs': True, 'booked': 189.00})

        # Cancel with a refund expected; it is kept, and the refund is matched like a charge.
        c.put(f"/api/trip/bookings/{r2['id']}", headers=HJ, data=json.dumps({'status': 'cancelled', 'refund_expected': True}))
        with db_session() as s:
            rf = DebtLedgerEntry(debt_account_id=ids['visa'], entry_type='payment', amount=612.48,
                                 entry_date=d0 + timedelta(days=3), merchant='DELTA AIR REFUND', description='', source_type='import')
            s.add(rf); s.commit(); made['le'].append(rf.id)
        lst = c.get('/api/trip/bookings?trip=' + 's162 Denver · 2026-11-01', headers=H).get_json()['data']['bookings']
        check('s162 B6 a cancelled booking is kept and shown cancelled, with no cost on the trip',
              any(b['id'] == r2['id'] and b['status'] == 'cancelled' and b['trip_cost'] is None for b in lst))
        rc = c.get(f"/api/trip/bookings/{r2['id']}/candidates", headers=H).get_json()['data']
        check('s162 B6 the refund is proposed like a charge, as money back', rc['for'] == 'refund' and [x['id'] for x in rc['candidates']] == [rf.id])

        # B1: the confirmation never reaches a log, an export or the narrator.
        srv = (BASE / 'server.py').read_text(encoding='utf-8')
        logged = [l for l in srv.splitlines() if re.search(r'log(ger|ging)?\.\w+\(', l) and 'confirmation' in l]
        check('s162 B1 nothing logs a confirmation number', logged == [])
        lt = c.get('/api/logs/tail', headers=H)
        check('s162 B1 the application log holds no confirmation number after a booking is made',
              lt.status_code != 200 or 'S162ZQ' not in json.dumps(lt.get_json()))
        check('s162 B1 the narrator\'s input and the exports carry no booking',
              'trip_bookings' not in app and 'TripBooking' not in srv.split('def export', 1)[-1][:20000])

        # B7 rendered: the page's own line.
        node = shutil.which('node')
        check('s162 node is available (skip the render check if not)', bool(node))
        if node:
            src = _fn(app, 'tripBookingLine')
            run_js = r'''const esc = s => String(s); const escJs = esc; const fmt = n => '$' + Number(n).toFixed(2);
const fmtDate = s => s;''' + src + r'''
const b = {airline: 'Delta', amount: 612.48, booked_on: '2026-10-08', status: 'booked', charged_amount: null, refund_expected: false};
console.log(JSON.stringify([tripBookingLine(b, 'Visa'), tripBookingLine({...b, status: 'charged', charged_amount: 618}, 'Visa'),
  tripBookingLine({...b, status: 'cancelled', refund_expected: true}, null)]));'''
            p = subprocess.run([node, '-e', run_js], capture_output=True, text=True, encoding='utf-8', timeout=60)
            lines = json.loads(p.stdout.strip() or '[]')
            check('s162 B7 the page says booked - waiting for the charge, then charged (with the booked amount when it differs)',
                  lines == ['Booked: Delta, $612.48 on Visa, 2026-10-08 — waiting for the charge.',
                            'Charged: Delta, $618.00 on Visa (booked $612.48), booked 2026-10-08.',
                            'Cancelled: Delta, $612.48, booked 2026-10-08 — refund expected.'])
        check('s162 B7 the trip\'s flight line uses the booking: booked, then charged',
              "tc.label === 'charged'" in app and '— waiting for the charge`' in app
              and trip_cost({'status': 'booked', 'amount': 10.0}) == {'amount': 10.0, 'label': 'booked', 'differs': False, 'booked': 10.0})
    finally:
        with db_session() as s:
            s.query(TripBooking).filter(TripBooking.id.in_(made['bk'])).delete(synchronize_session=False)
            s.query(DebtLedgerEntry).filter(DebtLedgerEntry.id.in_(made['le'])).delete(synchronize_session=False)
            s.query(Transaction).filter(Transaction.id.in_(made['tx'])).delete(synchronize_session=False)
            s.query(DebtAccount).filter(DebtAccount.id.in_(made['debt'])).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made['acct'])).delete(synchronize_session=False)
            s.commit()
