"""V8: a card added by mistake can be deleted, and then it stops counting.

DELETE /api/debt/<id> hides a debt; its history still feeds revolving_series and
the trophies, which is right for a card that existed and closed. A duplicate
needs real deletion: DELETE /api/debt/<id>/permanent. This section builds two
debts in the fixture database - one real and archived, one a mistake - and
checks what goes, what stays, and that the sums stop counting only the mistake.
"""
from datetime import date


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    from core.database import (Account, CheckingTransactionLink, DebtAccount,
                               DebtBalanceHistory, DebtLedgerEntry,
                               HistorianEntry, RecurringDebtPayment, Transaction)
    from server import _backups_dir, db_session, revolving_series

    def body(resp):
        j = resp.get_json() or {}
        return j.get('data') or j

    with db_session() as s:
        acct = Account(name='V8 Duplicate Card Account', type='credit', is_active=True)
        s.add(acct); s.flush()
        txn = Transaction(date=date(2026, 8, 3), amount=-150.0, description='V8 card payment',
                          account_id=acct.id)
        s.add(txn); s.flush()
        dup = DebtAccount(name='V8 Duplicate Card', current_balance=4000, interest_rate=21.0,
                          minimum_payment=90, debt_type='credit', linked_account_id=acct.id)
        real = DebtAccount(name='V8 Real Closed Card', current_balance=0, interest_rate=19.0,
                           minimum_payment=25, debt_type='credit', is_active=False)
        s.add_all([dup, real]); s.flush()
        for d, bal in ((dup, 4000.0), (real, 2500.0)):
            s.add(DebtBalanceHistory(debt_id=d.id, month='2025-01', balance=bal,
                                     payment=100.0, min_payment=25.0, interest_charged=40.0))
        entry = DebtLedgerEntry(debt_account_id=dup.id, entry_type='payment', amount=150.0,
                                entry_date=date(2026, 8, 3), source_type='manual')
        s.add(entry); s.flush()
        s.add(CheckingTransactionLink(checking_transaction_id=txn.id,
                                      debt_ledger_entry_id=entry.id,
                                      link_indicator='payment_to_card'))
        s.add(RecurringDebtPayment(debt_account_id=dup.id, amount=150.0))
        s.add(HistorianEntry(event_category='debt_payment_variance', debt_account_id=dup.id))
        s.commit()
        dup_id, real_id, acct_id, txn_id = dup.id, real.id, acct.id, txn.id

    def jan_2025():
        with db_session() as s:
            row = next((r for r in revolving_series(s) if r['month'] == '2025-01'), None)
            return round(row['balance'], 2) if row else None

    before = jan_2025()
    check('V8: before the delete, the duplicate adds to the past revolving balance',
          before is not None and before >= 6500.0)

    missing = c.delete('/api/debt/987654321/permanent', headers=H)
    check('an id nothing owns is a 404 from the permanent delete, not a 500',
          missing.status_code == 404)

    resp = c.delete(f'/api/debt/{dup_id}/permanent', headers=H)
    data = body(resp)
    check('the permanent delete succeeds and names the backup it took first',
          resp.status_code == 200 and str(data.get('backup', '')).startswith('groundwork_backup_pre-delete-debt-'))
    backup = _backups_dir() / str(data.get('backup', 'missing'))
    check('and the backup is on disk and is a real SQLite database',
          backup.exists() and backup.read_bytes()[:15] == b'SQLite format 3')

    with db_session() as s:
        check('the debt row is gone', s.get(DebtAccount, dup_id) is None)
        check('its balance history is gone',
              s.query(DebtBalanceHistory).filter_by(debt_id=dup_id).count() == 0)
        check('its ledger entries and their checking links are gone',
              s.query(DebtLedgerEntry).filter_by(debt_account_id=dup_id).count() == 0
              and s.query(CheckingTransactionLink).filter_by(checking_transaction_id=txn_id).count() == 0)
        check('its recurring payments are gone',
              s.query(RecurringDebtPayment).filter_by(debt_account_id=dup_id).count() == 0)
        hist = s.query(HistorianEntry).filter_by(event_category='debt_payment_variance',
                                                 debt_account_id=None).count()
        check('historian entries are kept, unlinked rather than left pointing at a reusable id',
              hist >= 1 and s.query(HistorianEntry).filter_by(debt_account_id=dup_id).count() == 0)
        check('the companion account and its bank transaction are untouched',
              s.get(Account, acct_id) is not None and s.get(Transaction, txn_id) is not None)
        check('the real, archived card is untouched, history and all',
              s.get(DebtAccount, real_id) is not None
              and s.query(DebtBalanceHistory).filter_by(debt_id=real_id).count() == 1)

    after = jan_2025()
    check('V8: after the delete the duplicate stops counting, and the real card still does',
          before is not None and after is not None and abs((before - after) - 4000.0) < 0.01)

    soft = c.delete(f'/api/debt/{real_id}', headers=H)
    with db_session() as s:
        check('the ordinary remove still only hides a debt, keeping its history (V7 wording holds)',
              soft.status_code == 200 and s.get(DebtAccount, real_id) is not None
              and s.query(DebtBalanceHistory).filter_by(debt_id=real_id).count() == 1)
        s.query(DebtBalanceHistory).filter_by(debt_id=real_id).delete()
        s.query(DebtAccount).filter_by(id=real_id).delete()
        s.query(HistorianEntry).filter_by(event_category='debt_payment_variance',
                                          debt_account_id=None).delete()
        s.query(Transaction).filter_by(id=txn_id).delete()
        s.query(Account).filter_by(id=acct_id).delete()
        s.commit()
    try:
        backup.unlink()
    except OSError:
        pass
