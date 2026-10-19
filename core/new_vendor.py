"""Item 98 (Rob 2026-10-19: "accept"): a vendor Groundwork has never seen, filed by the bank's own category label, is
asked about - once, one vendor at a time, never decided for the person.

    N1  only a row whose category came from the bank's own label (an import record's `bank_category`): Apple Card's
        category column, a QIF file's category. A row an import rule or the person's preview choice filed is theirs.
    N2  only a vendor never seen before: no earlier transaction, in any account, has this merchant (the Ledger's own
        merchant key - merchant, else description, trimmed and lower-cased). A vendor an import rule covers is known.
    N3  never on an account's first import: every vendor in a whole history is new, and hundreds of questions help
        nobody.
    N4  one question per vendor, however many of its rows came in; asked until answered, then never again.
    N5  Yes opens the transaction to change its category; No leaves it. Either way the Ledger then offers the usual
        "always categorize this merchant this way" rule - Groundwork itself never makes one.
"""
import json
from datetime import datetime

SETTING = 'new_vendor_bank_json'


def key(merchant, description=''):
    """The Ledger's merchant key (app.js: (t.merchant || t.description).toLowerCase().trim())."""
    return (merchant or description or '').strip().lower()


def account_had_rows(session, account_id):
    from core.database import Transaction
    return session.query(Transaction.id).filter(Transaction.account_id == account_id).first() is not None


def ruled(rules, k):
    """N2: an import rule already says where this vendor goes (the same contains/startsWith test the page applies)."""
    for r in rules or []:
        if not isinstance(r, dict):
            continue
        v = (r.get('value') or '').strip().lower()
        if v and ((r.get('type') == 'startsWith' and k.startswith(v)) or (r.get('type') != 'startsWith' and v in k)):
            return True
    return False


def seen_before(session, k, batch):
    """N2: any transaction outside this import with this merchant key."""
    from sqlalchemy import func, or_
    from core.database import Transaction
    return session.query(Transaction.id).filter(
        or_(Transaction.import_batch.is_(None), Transaction.import_batch != batch),
        or_(func.lower(func.trim(Transaction.merchant)) == k,
            func.lower(func.trim(Transaction.description)) == k),
    ).first() is not None


def queue(items, found, at=None):
    """N4: merge this import's new vendors {key: {merchant, label, category, ids}} into the waiting list."""
    at = at or datetime.now().isoformat(timespec='seconds')
    for k, f in found.items():
        e = next((x for x in items if x.get('key') == k), None)
        if e and e.get('answer'):
            continue                                    # asked and answered: never again
        if e:
            e['ids'] = sorted(set((e.get('ids') or []) + f['ids']))
        else:
            items.append({'key': k, 'merchant': f['merchant'], 'label': f['label'], 'category': f['category'],
                          'ids': sorted(set(f['ids'])), 'at': at})
    return items


def waiting(session, items):
    """The unanswered questions, oldest first, each with its first transaction as it is now (rows since deleted drop
    out; a vendor with none left is not asked about)."""
    from core.database import Category, Transaction
    out = []
    for e in items:
        if e.get('answer'):
            continue
        rows = session.query(Transaction).filter(Transaction.id.in_(e.get('ids') or [])).order_by(
            Transaction.date, Transaction.id).all()
        if not rows:
            continue
        t = rows[0]
        cat = session.get(Category, t.category_id) if t.category_id else None
        out.append({'key': e['key'], 'merchant': e['merchant'], 'label': e['label'],
                    'category': cat.name if cat else 'Other', 'count': len(rows),
                    'txn': {'id': t.id, 'date': t.date.isoformat() if t.date else '', 'amount': round(t.amount or 0, 2)}})
    return out


def load(session):
    from core.database import AppSetting
    row = session.query(AppSetting).filter_by(key=SETTING).first()
    try:
        v = json.loads(row.value) if row and row.value else []
    except (TypeError, ValueError):
        v = []
    return [x for x in v if isinstance(x, dict)]
