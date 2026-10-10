"""Item 68 stage 2: "can I pay this?" and "paid?" (gw 2.0/BILLS_AND_PAYING.md B6, B7; RULED 2026-10-10).

    B6  the person's floor per account, kept as they said it; the check shows its working, names what it can't see,
        and says first when the account's last download is more than 24 hours old (Rob); no floor, no answer - never
        assumed; no verdict words
    B7  a payment that matches the bill is shown with its transaction; a near-match is asked about; none is "not seen
        yet" with the download date; the lowest balance after it, when the download carries running balances
"""
import json
import re
from datetime import date, datetime, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import bill_check as bc
    import server
    from core.database import Account, AppSetting, BillReading, BudgetItem, HistorianEntry, Transaction, db_session

    now = datetime(2026, 10, 10, 12, 0)
    r = bc.pay_check(3850.0, date(2026, 10, 10), now - timedelta(hours=2), 2000.0, 142.37, [], now)
    check('s178 B6 it fits: the figure after the bill, the margin over the floor, and the working',
          r['state'] == 'fits' and r['after'] == 3707.63 and r['margin'] == 1707.63 and not r['stale']
          and r['working'][0] == 'Balance $3,850.00 as of Oct 10' and r['working'][-2] == '= $3,707.63'
          and r['working'][-1] == 'your floor $2,000.00: $1,707.63 above' and 'pending charges' in r['cant_see'])
    r = bc.pay_check(2100.0, None, now - timedelta(hours=2), 2000.0, 142.37, [('Water', 50.0)], now)
    check('s178 B6 it would go below: by how much, with an earlier bill from the same account counted',
          r['state'] == 'below' and r['after'] == 1907.63 and r['margin'] == -92.37
          and 'minus Water $50.00 (due earlier)' in r['working'] and r['working'][-1].endswith('below'))
    check('s178 B6 the 24-hour notice: over 24 hours is stale, 23 hours is not',
          bc.pay_check(3000, None, now - timedelta(hours=24, minutes=1), 2000, 10, [], now)['stale'] is True
          and bc.pay_check(3000, None, now - timedelta(hours=23), 2000, 10, [], now)['stale'] is False
          and bc.pay_check(3000, None, now - timedelta(hours=50), 2000, 10, [], now)['stale_hours'] == 50)
    r = bc.pay_check(3000.0, None, now, None, 142.37, [], now)
    check('s178 B6 no floor set: no answer, and it says what it needs - a floor is never assumed',
          r['state'] == 'unknown' and r['after'] is None and r['missing'] == ['the amount you want to always leave in this account'])
    r = bc.pay_check(None, None, None, 2000.0, 142.37, [], now)
    check('s178 B6 no download for the account: no answer, said so', r['state'] == 'unknown' and 'a downloaded balance for this account' in r['missing'])

    due = date(2026, 10, 24)
    tx = [{'id': 1, 'date': date(2026, 10, 1), 'amount': 900.0, 'type': 'debit', 'description': 'RENT', 'running_balance': 3000.0},
          {'id': 2, 'date': date(2026, 10, 22), 'amount': 142.37, 'type': 'debit', 'description': 'AEP OHIO PMT', 'running_balance': 2410.0},
          {'id': 3, 'date': date(2026, 10, 23), 'amount': 60.0, 'type': 'debit', 'description': 'GAS', 'running_balance': 2350.0}]
    p = bc.paid_match(142.37, due, 'Electric AEP', tx)
    check('s178 B7 the payment matches: shown with its transaction, and the lowest balance after it',
          p['state'] == 'paid' and p['txn']['id'] == 2 and p['lowest'] == (2350.0, date(2026, 10, 23)))
    near = [{'id': 4, 'date': date(2026, 10, 20), 'amount': 140.0, 'type': 'debit', 'description': 'ONLINE PMT', 'running_balance': None}]
    check('s178 B7 a near amount is asked about, never assumed', bc.paid_match(142.37, due, 'Electric', near)['state'] == 'near')
    named = [{'id': 5, 'date': date(2026, 10, 20), 'amount': 99.0, 'type': 'debit', 'description': 'AEP OHIO', 'running_balance': None}]
    check('s178 B7 a payment named like the bill but for another amount is asked about too',
          bc.paid_match(142.37, due, 'AEP Electric', named)['state'] == 'near')
    check('s178 B7 the person\'s "no" removes a near-match; their "yes" makes it the payment',
          bc.paid_match(142.37, due, 'Electric', near, {'yes': None, 'no': [4]})['state'] == 'not_seen'
          and bc.paid_match(142.37, due, 'Electric', near, {'yes': 4, 'no': []})['state'] == 'paid')
    check('s178 B7 nothing in the window: not seen yet; no amount or date: unknown',
          bc.paid_match(142.37, due, 'Electric', [tx[0]])['state'] == 'not_seen' and bc.paid_match(None, due, 'x', tx)['state'] == 'unknown')

    made = {'a': [], 'b': [], 'r': [], 't': [], 'h': []}
    try:
        today = date.today()
        with db_session() as s:
            a = Account(name='s178 Checking', type='checking', is_active=True)
            b = BudgetItem(name='s178 AEP', category='Electric', amount=120.0, type='expense', is_active=True)
            s.add_all([a, b]); s.commit()
            made['a'].append(a.id); made['b'].append(b.id)
            t1 = Transaction(date=today - timedelta(days=3), description='PAYROLL', amount=4000.0, type='credit', account_id=a.id, running_balance=3850.0)
            s.add(t1); s.commit(); made['t'].append(t1.id)
            server.log_historian_event(s, 'import_committed', context={'account_id': a.id, 'file_name': 'x.csv'})
            s.commit()
            ev = s.query(HistorianEntry).filter(HistorianEntry.event_category == 'import_committed').order_by(HistorianEntry.id.desc()).first()
            ev.created_at = datetime.utcnow() - timedelta(days=2)
            made['h'].append(ev.id)
            rd = BillReading(budget_item_id=b.id, amount=142.37, due_date=today + timedelta(days=10), read_at=datetime.now(), source_host='aep.example.com')
            s.add(rd); s.commit(); made['r'].append(rd.id)
            aid, bid = a.id, b.id
        c.post('/api/settings/bank-agent/bill-from', headers=HJ, data=json.dumps({'id': bid, 'account_id': aid}))
        k = c.get('/api/settings/bank-agent/bill-checks', headers=H).get_json()['data']
        mine = next(x for x in k['bills'] if x['id'] == bid)
        check('s178 B6 with no floor set, the route gives no answer and asks for one',
              mine['check']['state'] == 'unknown' and 'always leave' in ' '.join(mine['check']['missing']))
        c.post('/api/settings/bank-agent/buffer', headers=HJ, data=json.dumps({'account_id': aid, 'amount': 2000}))
        k = c.get('/api/settings/bank-agent/bill-checks', headers=H).get_json()['data']
        mine = next(x for x in k['bills'] if x['id'] == bid)
        check('s178 B6 the route: the bank\'s balance, the floor, the answer, and the 24-hour notice for a 2-day-old download',
              mine['check']['state'] == 'fits' and mine['check']['after'] == 3707.63 and mine['check']['stale'] is True
              and mine['last_download'].endswith('Z') and mine['paid']['state'] == 'not_seen'
              and next(x for x in k['accounts'] if x['id'] == aid)['buffer'] == 2000.0)
        with db_session() as s:
            buf = json.loads(s.query(AppSetting).filter_by(key=f'bank_buffer:account:{aid}').first().value)
        check('s178 B6 the floor is kept as the person said it, with when', buf['amount'] == 2000.0 and buf['said'])
        with db_session() as s:
            t2 = Transaction(date=today + timedelta(days=8), description='ONLINE PMT', amount=140.0, type='debit', account_id=aid)
            s.add(t2); s.commit(); made['t'].append(t2.id); t2id = t2.id
        k = c.get('/api/settings/bank-agent/bill-checks', headers=H).get_json()['data']
        mine = next(x for x in k['bills'] if x['id'] == bid)
        c.post('/api/settings/bank-agent/bill-paid', headers=HJ, data=json.dumps({'reading_id': made['r'][0], 'txn_id': t2id, 'yes': True}))
        k2 = c.get('/api/settings/bank-agent/bill-checks', headers=H).get_json()['data']
        mine2 = next(x for x in k2['bills'] if x['id'] == bid)
        check('s178 B7 the route asks about a near-match, and the person\'s yes makes it the payment',
              mine['paid']['state'] == 'near' and mine['paid']['txn']['id'] == t2id and mine2['paid']['state'] == 'paid')
    finally:
        with db_session() as s:
            s.query(AppSetting).filter(AppSetting.key.in_([f'bank_buffer:account:{i}' for i in made['a']] + [f'bill_from:{i}' for i in made['b']]
                                                          + [f'bill_paid:{i}' for i in made['r']])).delete(synchronize_session=False)
            s.query(BillReading).filter(BillReading.id.in_(made['r'])).delete(synchronize_session=False)
            s.query(Transaction).filter(Transaction.id.in_(made['t'])).delete(synchronize_session=False)
            s.query(HistorianEntry).filter(HistorianEntry.id.in_(made['h'])).delete(synchronize_session=False)
            s.query(BudgetItem).filter(BudgetItem.id.in_(made['b'])).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made['a'])).delete(synchronize_session=False)
            s.commit()

    app = ctx.app_src
    block = app.split('function billCheckHtml(')[1].split('async function setBillFrom(')[0]
    check('s178 B6 the words state facts: no verdicts ("safe", "afford", "should", "good", "bad", "don\x27t worry")',
          not re.search(r'\b(safe|afford|should|good|bad|worry|great)\b', block, re.I)
          and 'Transactions since then aren\x27t counted' in block and 'Can I pay this? It fits:' in block)
    check('s178 B6/B7 the page never moves money: no pay route is called from the bills card',
          'pay' not in ' '.join(re.findall(r"API\.post\('([^']+)'", block)).replace('bill-paid', ''))
