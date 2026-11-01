"""Item 108 (gw 2.0/RECURRING_PER_ACCOUNT.md; Rob 2026-10-22: "R1-R10 as recommended, build it"): a recurring
charge is one payee from one account.

    R1  every recurring reading keys by payee and account      R2  all seven readings at once
    R3  a payee from two accounts is two lines, named with their accounts; from one account, as before
    R4  (a) a card switch is one charge that moved               R5  (a) budget lines and answers stay by payee
    R6  Lever 4 per account                                      R10 the null models and the section 1 cases
"""
import json
from datetime import date, timedelta


def _month(today, k, day):
    y, m = today.year, today.month + k
    while m < 1:
        y, m = y - 1, m + 12
    while m > 12:
        y, m = y + 1, m - 12
    return date(y, m, min(day, 28))


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import server
    from core import recurring_groups as rg
    from core import upcoming
    from core.database import Account, AppSetting, BudgetItem, Transaction, db_session

    # ── the grouping itself ──────────────────────────────────────────────────────────────────────────────────────
    t = date(2026, 10, 21)
    mk = lambda acct, k, day, amt, p='Netflix': (p, acct, _month(t, k, day), amt, None)
    names = {1: 'Checking', 2: 'Visa'}
    two = rg.groups([mk(1, -k, 3, 17.99) for k in range(6)] + [mk(2, -k, 22, 17.99) for k in range(6)], names)
    check(f"s255 R1/R3 a payee from two accounts is two lines, each named with its account ({[g['label'] for g in two]})",
          sorted(g['label'] for g in two) == ['Netflix (Checking)', 'Netflix (Visa)'] and all(g['payee'] == 'Netflix' for g in two)
          and all(len(g['rows']) == 6 for g in two))
    one = rg.groups([mk(2, -k, 22, 17.99) for k in range(6)], names)
    check('s255 R3 a payee from one account reads as before: its name alone, every charge',
          len(one) == 1 and one[0]['label'] == 'Netflix' and len(one[0]['rows']) == 6)
    sw = rg.groups([mk(1, -k, 3, 17.99) for k in range(3, 9)] + [mk(2, -k, 28, 17.99) for k in range(0, 4)], names)
    check(f"s255 R4 (a) a card switch is one charge that moved: on the account it is on now, with its history ({[(g['label'], g['account'], len(g['rows'])) for g in sw]})",
          len(sw) == 1 and sw[0]['label'] == 'Netflix' and sw[0]['account'] == 'Visa' and len(sw[0]['rows']) == 10)
    off = rg.groups([mk(1, -k, 3, 17.99) for k in range(3, 9)] + [mk(2, -k, 28, 19.07) for k in range(0, 4)], names)
    long = rg.groups([mk(1, -k, 3, 17.99) for k in range(0, 3)] + [mk(2, -k, 9, 17.99) for k in range(0, 7)], names)
    check('s255 R4 not a switch: a different amount (6%), or both still paying',
          len(off) == 2 and len(long) == 2)

    # ── the readings, on this database ───────────────────────────────────────────────────────────────────────────
    today = date.today()
    with db_session() as s:
        A = Account(name='s255 Checking', type='checking'); B = Account(name='s255 Visa', type='credit')
        s.add_all([A, B]); s.flush()
        a, b = A.id, B.id
        ids = []

        def add(acct, d, merchant, amount):
            tx = Transaction(date=d, description=merchant.upper(), merchant=merchant, amount=amount, type='debit',
                             account_id=acct)
            s.add(tx); s.flush(); ids.append(tx.id)
        for k in range(0, 6):                                         # StreamQ from both, every month
            add(a, _month(today, -k, 1), 'S255 StreamQ', 13.37)       # the 1st: this month's has always come
            add(b, _month(today, -k - 1, 22), 'S255 StreamQ', 13.37)
        for k in range(3, 8):                                         # the gym moved from checking to the Visa
            add(a, _month(today, -k, 5), 'S255 Gym', 41.0)
        for k in range(1, 4):
            add(b, _month(today, -k, 27), 'S255 Gym', 41.0)
        for k in range(1, 16):                                        # a price step on the Visa only
            add(b, _month(today, -k, 12), 'S255 Tunes', 11.99 if k <= 4 else 9.99)
            add(a, _month(today, -k, 16), 'S255 Tunes', 9.99)
        def last(mo, day, k):                                         # the k-th most recent such date, by today
            y = today.year - (0 if date(today.year, mo, day) <= today else 1) - k
            return date(y, mo, day)
        for k in range(3):                                            # a yearly bill per car, from each account
            add(a, last(3, 10, k), 'S255 Insure', 620.0)
            add(b, last(9, 14, k), 'S255 Insure', 640.0)
        s.commit()
    acct_ids = [a, b]
    try:
        with db_session() as s:
            det = [p for p in server.detect_recurring_patterns(s) if p['merchant'].startswith('S255')]
            trim = [r for r in server.trim_candidates(s, limit=200) if r['payee'].startswith('S255')]
            rc = [r for r in upcoming.recurring_charges(s, today, include_budgeted=True) if r['merchant'].startswith('S255')]
            nxt = _month(today, 1, 1)
            cal = [e for e in server._calendar_entries(s, nxt, _month(today, 1, 28)) if e['title'].startswith('S255')]
            pcs = [x for x in server._price_changes(s) if x['payee'].startswith('S255')]
            ren = [x for x in (server._first_import_findings(s).get('renewals') or []) if x['payee'].startswith('S255')]
        sq = sorted((p['label'], p['frequency']) for p in det if p['merchant'] == 'S255 StreamQ')
        check(f"s255 R1/R3 the Ledger's patterns: each account's StreamQ, named, with its own count ({sq})",
              [x[0] for x in sq] == ['S255 StreamQ (s255 Checking)', 'S255 StreamQ (s255 Visa)'] and all(n >= 5 for _, n in sq))
        sqt = sorted((r['name'], r['monthly']) for r in trim if r['payee'] == 'S255 StreamQ')
        check(f's255 R6 Lever 4: each account\'s charge at its own monthly cost, not the two run together ({sqt})',
              [m for _, m in sqt] == [13.37, 13.37])
        sqr = sorted((r['label'], r['day']) for r in rc if r['merchant'] == 'S255 StreamQ')
        check(f's255 R2 the Budget card and the Calendar\'s one rule: both accounts, each on its own day ({sqr})',
              sqr == [('S255 StreamQ (s255 Checking)', 1), ('S255 StreamQ (s255 Visa)', 22)]
              and sorted({e['title'] for e in cal if 'StreamQ' in e['title']}) == ['S255 StreamQ (s255 Checking)', 'S255 StreamQ (s255 Visa)'])
        gym = [(r['label'], r['account']) for r in rc if r['merchant'] == 'S255 Gym']
        check(f's255 R4 (a) the switch null model: the gym that moved stays on the Budget card and the Calendar, on the account it is on now ({gym})',
              gym == [('S255 Gym', 's255 Visa')] and any(e['title'] == 'S255 Gym' for e in cal))
        tunes = [(x['label'], x['before'], x['after']) for x in pcs if x['payee'] == 'S255 Tunes']
        check(f's255 R1 a price step on one account is found, named with its account ({tunes})',
              tunes == [('S255 Tunes (s255 Visa)', 9.99, 11.99)])
        ins = sorted((x['label'], x['months']) for x in ren if x['payee'] == 'S255 Insure')
        check(f's255 R1 a yearly bill from each of two accounts: both found ({ins})',
              [x[0] for x in ins] == ['S255 Insure (s255 Checking)', 'S255 Insure (s255 Visa)'])

        # R5: the answers stay the payee's
        r = c.post('/api/first-import/answer', headers=HJ, data=json.dumps({'kind': 'renewal', 'payee': 'S255 Insure', 'answer': 'yes'})).get_json()
        with db_session() as s:
            yb = [e for e in json.loads((s.query(AppSetting).filter_by(key='yearly_bills_json').first() or AppSetting(value='[]')).value or '[]')
                  if e.get('payee') == 'S255 Insure']
            again = [x for x in (server._first_import_findings(s).get('renewals') or []) if x['payee'] == 'S255 Insure']
        check(f"s255 R5 (a) a yes to a yearly bill is the payee's: kept for each account's renewal, so both months reach the calendar ({[e['months'] for e in yb]})",
              r.get('ok') and sorted(m for e in yb for m in e['months']) == [3, 9] and all(set(e.keys()) == {'payee', 'amount', 'months', 'day', 'rhythm', 'answer', 'at'} for e in yb)
              and all(x['answer'] == 'yes' for x in again))
        with db_session() as s:
            s.add(BudgetItem(type='expense', name='S255 StreamQ', amount=26.74, category='', is_active=True)); s.commit()
            gone = [p for p in server.detect_recurring_patterns(s) if p['merchant'] == 'S255 StreamQ']
            still = [r for r in upcoming.recurring_charges(s, today, include_budgeted=True) if r['merchant'] == 'S255 StreamQ']
        check('s255 R5 (a) a budget line naming the payee covers it from every account',
              gone == [] and len(still) == 2 and all(r['budgeted'] for r in still))
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.id.in_(ids)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(acct_ids)).delete(synchronize_session=False)
            s.query(BudgetItem).filter(BudgetItem.name == 'S255 StreamQ').delete(synchronize_session=False)
            row = s.query(AppSetting).filter_by(key='yearly_bills_json').first()
            if row and row.value:
                row.value = json.dumps([e for e in json.loads(row.value) if e.get('payee') != 'S255 Insure'])
            s.commit()

    # ── the pages show the label, and match by payee ─────────────────────────────────────────────────────────────
    app = ctx.app_src
    yearly = (ctx.BASE / 'static/js/teaching/yearly.js').read_text(encoding='utf-8')
    check('s255 R3 the Ledger\'s patterns and the Budget card show the label; Add and Dismiss stay the payee\'s (R5)',
          '${esc(p.label || p.merchant)}' in app and "acceptRecurringDetection('${escJs(p.merchant)" in app
          and 'merchant: r.label || r.merchant' in app)
    check('s255 R3 a price change and a yearly question name the account\'s line when they are answered',
          "{ payee: c.payee, label: c.label }" in app and 'label: x.label' in yearly
          and "x['payee'] == payee and x['label'] == label" in ctx.server_src)
