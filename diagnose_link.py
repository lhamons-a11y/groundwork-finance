"""
Groundwork one-off diagnostic — why isn't a linked debt balance updating?
Run from C:\Groundwork:   python diagnose_link.py
Reads the real database read-only. Changes nothing.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'core'))

from core.database import db_session, DebtAccount, Account, Transaction
from sqlalchemy import func

with db_session() as s:
    print("=== DEBT CARDS and their links ===")
    for d in s.query(DebtAccount).filter_by(is_active=True).all():
        link = d.linked_account_id
        linked_acct = s.get(Account, link) if link else None
        print(f"  '{d.name}': current_balance={d.current_balance}  "
              f"begin={d.begin_balance}  linked_account_id={link}"
              f"  -> {'account:'+repr(linked_acct.name) if linked_acct else 'NOT LINKED / missing account'}")

    print("\n=== ACCOUNTS and their transaction counts ===")
    for a in s.query(Account).all():
        n = s.query(Transaction).filter_by(account_id=a.id).count()
        n_bal = s.query(Transaction).filter(
            Transaction.account_id == a.id,
            Transaction.running_balance != None,
            Transaction.running_balance != 0,
        ).count()
        print(f"  id={a.id}  '{a.name}'  active={a.is_active}  "
              f"txns={n}  (with running_balance={n_bal})")

    print("\n=== DUPLICATE-NAME CHECK (the prime suspect) ===")
    from collections import Counter
    names = Counter(a.name.strip().lower() for a in s.query(Account).all())
    dupes = {k: v for k, v in names.items() if v > 1}
    print("  duplicate account names:", dupes if dupes else "none")

    print("\n=== FOR EACH LINKED DEBT: does its linked account actually have the txns? ===")
    for d in s.query(DebtAccount).filter_by(is_active=True).all():
        if not d.linked_account_id:
            continue
        txns = s.query(Transaction).filter_by(account_id=d.linked_account_id).all()
        net = sum(t.amount if t.type == 'debit' else -t.amount for t in txns)
        print(f"  '{d.name}' linked->id={d.linked_account_id}: "
              f"{len(txns)} txns, net activity={round(net,2)}, "
              f"current_balance={d.current_balance}")
        if txns:
            print(f"      most recent: {txns[-1].date} {txns[-1].description[:30]} "
                  f"{txns[-1].type} ${txns[-1].amount} running_bal={txns[-1].running_balance}")
