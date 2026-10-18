"""Item 93 stage 1 (gw 2.0/BANK_SIDE_RECORDS.md B5 and B7; Rob 2026-10-17: B1-B12 approved, B5 and B7 1.x data-loss fixes,
"Yes build"). The same section on 1.x and master.

    B5  a line that only LOOKS like one already here is held back and shown, never dropped; the bank's own id still
        says "the same line"; two different bank ids say "two lines"; bring in or "the same" only on a yes, kept on record
    B5  the page's duplicate bot finds and shows - it never removes anything by itself after an import
    B7  deleting sets the line aside whole, out of every total; a restore brings back the same id and its debt link;
        no new line can take a set-aside id; a mistaken import is set aside as a batch, each line restorable
"""
import json
from datetime import date


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    from core.database import (Account, CheckingTransactionLink, DebtAccount, DebtLedgerEntry, ImportHeldLine,
                               SetAsideTransaction, Transaction, db_session)

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    app = ctx.app_src
    with db_session() as s:
        a = Account(name='S233 Checking', type='checking', is_active=True); s.add(a); s.commit()
        aid = a.id
    rec = lambda d, desc, amt, fitid='': {'date': d, 'description': desc, 'amount': amt, 'type': 'debit',
                                          'category': 'Other', 'fitid': fitid, 'source': 'csv'}
    made_debt = []
    try:
        # ── B5: the commit ────────────────────────────────────────────────────
        r1 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-03-03', 'S233 CLARK GAS STATION 4471 MILLBROOK OH', 42.10),
            rec('2026-03-04', 'S233 BISTRO', 18.00, fitid='FIT-1')]}))
        check('s234 B7 every imported line carries its import batch',
              r1['created'] == 2 and r1['batch'])
        with db_session() as s:
            # by the section's own rows: an earlier section's deleted account can leave rows under a reused id
            b1 = {t.import_batch for t in s.query(Transaction).filter(Transaction.account_id == aid,
                                                                      Transaction.description.like('S233%')).all()}
        check('s234 B7 the batch is on the rows', b1 == {r1['batch']})
        r2 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-03-03', 'Withdrawal S233 CLARK GAS STATION 4471 MILLBROOK OH', 42.10),   # CSV prefix: looks alike
            rec('2026-03-04', 'S233 BISTRO', 18.00, fitid='FIT-1'),                  # the bank's own id: same line
            rec('2026-03-04', 'S233 BISTRO', 18.00, fitid='FIT-2')]}))               # two bank ids: two lines
        check('s234 B5 the bank\'s own id still says "the same line" (skipped); two different bank ids import as two',
              r2['duplicates'] == 1 and r2['created'] == 1)
        check('s234 B5 a look-alike is held back and shown with what it looks like - never dropped',
              len(r2.get('held') or []) == 1 and r2['held'][0]['looks_like']['description'] == 'S233 CLARK GAS STATION 4471 MILLBROOK OH')
        hid = r2['held'][0]['id']
        listed = data(c.get('/api/import/held', headers=H))['held']
        check('s234 B5 held lines stay listed until the person decides', any(h['id'] == hid for h in listed))
        bad = post(f'/api/import/held/{hid}', {'answer': 'maybe'})
        r3 = data(post(f'/api/import/held/{hid}', {'answer': 'bring_in'}))
        with db_session() as s:
            brought = s.get(Transaction, r3['brought_in_id'])
            kept = s.get(ImportHeldLine, hid)
        check('s234 B5 "bring it in" imports it as its own line, and the held record keeps the decision',
              bad.status_code == 400 and brought is not None and brought.amount == 42.10 and kept.resolved == 'bring_in'
              and not any(h['id'] == hid for h in r3['held']))
        r4 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-03-03', 'Deposit S233 CLARK GAS STATION 4471 MILLBROOK OH', 42.10)]}))
        hid2 = r4['held'][0]['id']
        post(f'/api/import/held/{hid2}', {'answer': 'same'})
        with db_session() as s:
            n_clark = s.query(Transaction).filter(Transaction.account_id == aid, Transaction.amount == 42.10,
                                                  Transaction.description.like('%S233 CLARK%')).count()
            same = s.get(ImportHeldLine, hid2)
        check('s234 B5 "it\'s the same" adds nothing, and the line stays on record as decided', n_clark == 2 and same.resolved == 'same')

        r6 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-03-03', 'Withdrawal S233 CLARK GAS STATION 4471 MILLBROOK OH', 42.10),
            rec('2026-03-04', 'Purchase S233 BISTRO AND GRILL MILLBROOK OHIO', 18.00)]}))
        nb_held = len(r6.get('held') or [])
        rb = data(post('/api/import/held/batch', {'batch': r6['batch'], 'answer': 'same'}))
        check("s234 B5 one decision covers a whole import's held lines (a file imported twice), each kept on record",
              nb_held >= 1 and rb['resolved'] == nb_held and not any(h['batch'] == r6['batch'] for h in rb['held']))

        # ── B5: the page's bot ────────────────────────────────────────────────
        bot = app.split('async function _runDedupBot(')[1].split('\n}\n')[0]
        silent_part = bot.split('if (silent) {')[1].split('return;')[0] if 'if (silent) {' in bot else ''
        check('s234 B5 after an import the duplicate bot only says what it found - it removes nothing by itself',
              silent_part and 'API.delete' not in silent_part and 'Nothing was removed' in silent_part
              and bot.index('if (silent) {') < bot.index('S.transactions = S.transactions.filter'))

        # ── B7: delete sets aside; restore ────────────────────────────────────
        with db_session() as s:
            t = s.query(Transaction).filter_by(account_id=aid, import_id='FIT-2').first()
            d = DebtAccount(name='S233 Card'); s.add(d); s.flush(); made_debt.append(d.id)
            e = DebtLedgerEntry(debt_account_id=d.id, entry_type='payment', amount=18.0, entry_date=date(2026, 3, 4),
                                linked_checking_transaction_id=t.id)
            s.add(e); s.flush()
            s.add(CheckingTransactionLink(checking_transaction_id=t.id, debt_ledger_entry_id=e.id, link_indicator='payment_to_card')); s.commit()
            tid, eid = t.id, e.id
        dr = c.delete(f'/api/transactions/{tid}', headers=H).get_json()['data']
        with db_session() as s:
            gone = s.get(Transaction, tid) is None
            sa = s.get(SetAsideTransaction, dr['set_aside'])
            unlinked = s.get(DebtLedgerEntry, eid).linked_checking_transaction_id is None
        check('s234 B7 deleting sets the line aside whole - out of the ledger, kept with its debt link',
              gone and sa is not None and sa.original_id == tid and 'S233 BISTRO' in sa.row_json and 'debt_ledger_entry_id' in sa.links_json
              and unlinked)
        lst = data(c.get('/api/transactions/set-aside', headers=H))
        check('s234 B7 set-aside lines are listed to restore', any(x['id'] == sa.id for x in lst['set_aside']))
        # the id guard: the newest line set aside, a new line must not take its id
        with db_session() as s:
            top = s.query(Transaction).order_by(Transaction.id.desc()).first()
            top_id = top.id
        c.delete(f'/api/transactions/{top_id}', headers=H)
        with db_session() as s:
            fresh = Transaction(date=date(2026, 3, 9), description='S233 NEW', amount=1.0, type='debit', account_id=aid)
            s.add(fresh); s.commit(); fresh_id = fresh.id
            top_sa = s.query(SetAsideTransaction).filter_by(original_id=top_id).first()
        check('s234 B7 no new line can take a set-aside id', fresh_id > top_id)
        rr = post(f'/api/transactions/set-aside/{sa.id}/restore', {})
        post(f'/api/transactions/set-aside/{top_sa.id}/restore', {})
        with db_session() as s:
            back = s.get(Transaction, tid)
            relinked = s.get(DebtLedgerEntry, eid).linked_checking_transaction_id == tid \
                and [x.link_indicator for x in s.query(CheckingTransactionLink).filter_by(checking_transaction_id=tid).all()] == ['payment_to_card']
        check('s234 B7 a restore brings back the same id, every column, and its debt link',
              rr.status_code == 200 and back is not None and back.import_id == 'FIT-2' and back.amount == 18.0 and relinked)
        again = post(f'/api/transactions/set-aside/{sa.id}/restore', {})
        check('s234 B7 a line restores once', again.status_code == 400)

        # ── B7: a mistaken import, as a batch ─────────────────────────────────
        r5 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-04-01', 'S233 OOPS ONE', 5.0), rec('2026-04-02', 'S233 OOPS TWO', 6.0)]}))
        batches = data(c.get('/api/transactions/set-aside', headers=H))['batches']
        nb = data(post(f"/api/transactions/import-batches/{r5['batch']}/set-aside", {}))
        with db_session() as s:
            left = s.query(Transaction).filter(Transaction.import_batch == r5['batch']).count()
            kept_n = s.query(SetAsideTransaction).filter_by(batch=r5['batch'], restored_at=None).count()
        check('s234 B7 a mistaken import is listed and set aside as a batch, each line kept to restore',
              any(b['batch'] == r5['batch'] and b['lines'] == 2 for b in batches) and nb['set_aside'] == 2 and left == 0 and kept_n == 2)
        srv = ctx.server_src
        dt = srv.split('def delete_transaction(')[1].split('\n@')[0]
        check('s234 B7 the Ledger\'s delete route destroys nothing (no session.delete of the row there)',
              'session.delete(' not in dt and 'set_aside' in dt)
    finally:
        with db_session() as s:
            ids = [t.id for t in s.query(Transaction).filter(Transaction.account_id == aid, Transaction.description.like('%S233%')).all()]
            s.query(CheckingTransactionLink).filter(CheckingTransactionLink.checking_transaction_id.in_(ids)).delete(synchronize_session=False)
            s.query(DebtLedgerEntry).filter(DebtLedgerEntry.debt_account_id.in_(made_debt)).delete(synchronize_session=False)
            s.query(DebtAccount).filter(DebtAccount.id.in_(made_debt)).delete(synchronize_session=False)
            s.query(Transaction).filter(Transaction.id.in_(ids)).delete(synchronize_session=False)
            s.query(SetAsideTransaction).filter_by(account_id=aid).delete()
            s.query(ImportHeldLine).filter_by(account_id=aid).delete()
            s.query(Account).filter_by(id=aid).delete()
            s.commit()
