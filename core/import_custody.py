"""Nothing an import brings in is lost (gw 2.0/BANK_SIDE_RECORDS.md, item 93 stage 1: B5 and B7; ruled 2026-10-17, and a
1.x data-loss fix under item 32 L1).

B5  Similarity proposes; it never decides. A line that only LOOKS like one already here (same account, date, type and
    amount, a similar description) is held back and shown, never dropped: brought in on a yes, or kept as "the same"
    on a yes. The bank's own id (FITID) matching is the bank saying it is the same line, and that is still skipped -
    and two different bank ids are the bank saying they are two lines, so those are never treated as duplicates.
B7  Deleting hides; it never destroys. A deleted transaction is set aside whole - every column and its debt link -
    out of every total and restorable with the same id, so anything that pointed at it points at it again. A
    mistaken import can be set aside as a batch.

Nothing here logs a transaction's text.
"""
import json
from datetime import date, datetime

_DATE_COLS = ('date', 'posted_date')


def _row(txn):
    """Every column of a transaction, as plain JSON values."""
    out = {}
    for col in txn.__table__.columns:
        v = getattr(txn, col.name)
        if isinstance(v, datetime):
            v = v.isoformat()
        elif isinstance(v, date):
            v = v.isoformat()
        out[col.name] = v
    return out


def _unrow(model, data):
    kw = {}
    cols = {c.name: c for c in model.__table__.columns}
    for k, v in data.items():
        if k not in cols:
            continue                  # a column the row had on an older schema and this one does not
        if v is not None and k in _DATE_COLS:
            v = date.fromisoformat(v)
        elif v is not None and k in ('created_at', 'user_confirmed_at'):
            v = datetime.fromisoformat(v)
        kw[k] = v
    return model(**kw)


# ── B7: set aside, restore ─────────────────────────────────────────────────────────────────────────────────────

def set_aside(session, txn, reason='', batch=None):
    """Move a transaction out of the ledger, whole. Its debt link is recorded so a restore reconnects it."""
    from core.database import CheckingTransactionLink, DebtLedgerEntry, SetAsideTransaction
    links = []
    for ln in session.query(CheckingTransactionLink).filter_by(checking_transaction_id=txn.id).all():
        links.append(_row(ln))                # the whole link row, so a restore rebuilds it exactly
        entry = session.get(DebtLedgerEntry, ln.debt_ledger_entry_id)
        if entry and entry.linked_checking_transaction_id == txn.id:
            entry.linked_checking_transaction_id = None
        session.delete(ln)
    row = SetAsideTransaction(original_id=txn.id, account_id=txn.account_id, row_json=json.dumps(_row(txn)),
                              links_json=json.dumps(links), reason=(reason or '')[:200], batch=batch)
    session.add(row)
    session.delete(txn)
    session.flush()
    return row


def restore(session, set_aside_id):
    from core.database import CheckingTransactionLink, DebtLedgerEntry, SetAsideTransaction, Transaction
    sa = session.get(SetAsideTransaction, int(set_aside_id or 0))
    if not sa or sa.restored_at is not None:
        return None, 'That line was not found among the set-aside lines.'
    if session.get(Transaction, sa.original_id) is not None:
        return None, 'A transaction with that id is already in the ledger.'
    txn = _unrow(Transaction, json.loads(sa.row_json))
    session.add(txn)
    session.flush()
    for ln in json.loads(sa.links_json or '[]'):
        entry = session.get(DebtLedgerEntry, ln['debt_ledger_entry_id'])
        if entry is not None and entry.linked_checking_transaction_id in (None, txn.id):
            entry.linked_checking_transaction_id = txn.id
            link = _unrow(CheckingTransactionLink, dict(ln, id=None, checking_transaction_id=txn.id))
            session.add(link)
    sa.restored_at = datetime.utcnow()
    from core import bank_versions
    bank_versions.undone_by_restore(session, sa.id)     # item 93 B9: a restored pending line counts again
    session.flush()
    return txn, None


def set_aside_list(session, limit=200):
    from core.database import Account, SetAsideTransaction
    names = {a.id: a.name for a in session.query(Account).all()}
    out = []
    for sa in session.query(SetAsideTransaction).filter(SetAsideTransaction.restored_at.is_(None)) \
            .order_by(SetAsideTransaction.id.desc()).limit(limit).all():
        r = json.loads(sa.row_json)
        out.append({'id': sa.id, 'original_id': sa.original_id, 'date': r.get('date'), 'description': r.get('description'),
                    'amount': r.get('amount'), 'type': r.get('type'), 'account': names.get(sa.account_id, ''),
                    'reason': sa.reason or '', 'batch': sa.batch,
                    'set_aside_at': sa.set_aside_at.isoformat(timespec='seconds') if sa.set_aside_at else None})
    return out


def batches(session, limit=20):
    """Recent imports that carry a batch, newest first - so a mistaken one can be set aside in one step."""
    from sqlalchemy import func
    from core.database import Account, Transaction
    names = {a.id: a.name for a in session.query(Account).all()}
    rows = session.query(Transaction.import_batch, Transaction.account_id, func.count(Transaction.id),
                         func.min(Transaction.created_at)) \
        .filter(Transaction.import_batch.isnot(None), Transaction.import_batch != '') \
        .group_by(Transaction.import_batch, Transaction.account_id) \
        .order_by(func.min(Transaction.created_at).desc()).limit(limit).all()
    return [{'batch': b, 'account': names.get(a, ''), 'lines': n,
             'imported_at': t.isoformat(timespec='seconds') if t else None} for b, a, n, t in rows]


def set_aside_batch(session, batch):
    from core.database import Transaction
    rows = session.query(Transaction).filter(Transaction.import_batch == batch).all()
    for t in rows:
        set_aside(session, t, reason='a mistaken import, set aside as a batch', batch=batch)
    return len(rows)


# ── B5: lines held back ─────────────────────────────────────────────────────────────────────────────────────────

def is_bank_duplicate(existing, fitid):
    """The bank's own id says it is the same line."""
    return bool(fitid) and (existing.import_id or '') == fitid


def bank_says_different(existing, fitid):
    """Two different bank ids are the bank saying these are two lines - never a duplicate, however alike."""
    return bool(fitid) and bool(existing.import_id) and existing.import_id != fitid


def hold(session, account_id, rec, matched, batch):
    from core.database import ImportHeldLine
    row = ImportHeldLine(account_id=account_id, record_json=json.dumps(rec), matched_id=matched.id if matched else None,
                         batch=batch)
    session.add(row)
    session.flush()
    return row


def _held_view(session, h, names):
    from core.database import Transaction
    r = json.loads(h.record_json)
    m = session.get(Transaction, h.matched_id) if h.matched_id else None
    return {'id': h.id, 'batch': h.batch, 'account': names.get(h.account_id, ''), 'date': r.get('date'), 'description': r.get('description'),
            'amount': abs(float(r.get('amount') or 0)), 'type': r.get('type', 'debit'),
            'looks_like': ({'id': m.id, 'date': m.date.isoformat() if m.date else None, 'description': m.description,
                            'amount': m.amount} if m else None),
            'held_at': h.created_at.isoformat(timespec='seconds') if h.created_at else None}


def held_list(session):
    from core.database import Account, ImportHeldLine
    names = {a.id: a.name for a in session.query(Account).all()}
    return [_held_view(session, h, names) for h in session.query(ImportHeldLine)
            .filter(ImportHeldLine.resolved == '').order_by(ImportHeldLine.id).all()]


def held_views(session, rows):
    from core.database import Account
    names = {a.id: a.name for a in session.query(Account).all()}
    return [_held_view(session, h, names) for h in rows]


def resolve(session, held_id, answer, insert_fn):
    """answer 'bring_in': imported as its own line through the importer's own insert; 'same': kept, resolved as the
    same line. Either way the held line stays on record with what was decided."""
    from core.database import ImportHeldLine
    h = session.get(ImportHeldLine, int(held_id or 0))
    if not h or h.resolved:
        return None, 'That held line was not found.'
    if answer == 'bring_in':
        txn = insert_fn(session, h.account_id, json.loads(h.record_json), h.batch)
        if txn is None:
            return None, 'That line could not be brought in.'
        h.brought_in_id = txn.id
    elif answer != 'same':
        return None, 'answer bring_in or same'
    h.resolved = answer
    h.resolved_at = datetime.utcnow()
    session.flush()
    return h, None


def resolve_batch(session, batch, answer, insert_fn):
    """One decision for every line one import held back - the person's yes on the listed set (a re-import of a whole
    file can hold hundreds). Each line keeps its own record of the decision."""
    from core.database import ImportHeldLine
    rows = session.query(ImportHeldLine).filter(ImportHeldLine.batch == batch, ImportHeldLine.resolved == '').all()
    done = 0
    for h in rows:
        r, problem = resolve(session, h.id, answer, insert_fn)
        if problem:
            return done, problem
        done += 1
    return done, None
