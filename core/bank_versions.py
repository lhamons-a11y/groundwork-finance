"""The bank's statement, and what the household says beside it (gw 2.0/BANK_SIDE_RECORDS.md, item 93 stage 2: B6 and
B9; ruled 2026-10-17, built on Rob's "go ahead on stage 2", 2026-10-18). Master only: under item 32 L1 only B5 and B7
were ruled data-loss fixes for 1.x.

B6  A correction sits beside the bank's statement, never over it. The ledger line holds the current value, so every
    total uses the correction; each value it replaced is kept, dated (`TransactionCorrection`, written by a flush
    listener in core/database.py so no path can skip it). The earliest kept version is called the bank's only when
    the line came in after corrections began to be kept - before that, an edit may have left no trace.
B9  A pending line and its posted line are both kept. The posted line is current for totals; the pending one is set
    aside whole (B7), with its own date and amount, and a changed amount is shown, never overwritten. The bank's own
    id (FITID) establishes the pair; anything else is a suggestion that waits for the person's yes (B5).

Nothing here logs a transaction's text.
"""
import re
from datetime import datetime, timedelta

FIELDS = ('date', 'description', 'amount', 'category', 'type')
PAIR_WINDOW_DAYS = 10          # a pending line posts within days, not weeks

# Words a bank adds around a merchant's name, which say nothing about which merchant it was.
_NOISE = {'pending', 'purchase', 'pos', 'debit', 'credit', 'card', 'withdrawal', 'deposit', 'ach', 'payment', 'the',
          'and', 'recurring', 'authorized', 'authorization', 'visa', 'mastercard', 'checkcard', 'check', 'dbt', 'crd',
          'pur', 'preauth', 'auth', 'temporary', 'hold', 'transaction', 'online', 'web', 'www', 'com', 'inc', 'llc'}


def _local_day(dt):
    """The day of a recorded time - recorded in the computer's own local time (item 109)."""
    if not dt:
        return None
    return dt.date().isoformat()


def _say_day(d):
    return f'{d:%b} {d.day}, {d.year}' if d else ''


def _since(session):
    from core.database import AppSetting
    row = session.query(AppSetting).filter_by(key='corrections_kept_since').first()
    try:
        return datetime.fromisoformat(row.value) if row and row.value else None
    except ValueError:
        return None


def _current(txn):
    return {'date': txn.date.isoformat() if txn.date else '', 'description': txn.description or '',
            'amount': f'{float(txn.amount or 0):.2f}', 'category': txn.category.name if txn.category else 'Other',
            'type': txn.type or 'debit'}


# ── B6 ────────────────────────────────────────────────────────────────────────────────────────────────────────────

def corrected_ids(session, ids):
    from core.database import TransactionCorrection
    if not ids:
        return set()
    return {r[0] for r in session.query(TransactionCorrection.transaction_id)
            .filter(TransactionCorrection.transaction_id.in_(list(ids))).distinct().all()}


def versions(session, txn):
    """The line as it is now, the earliest version kept, and every correction between, oldest first."""
    from core.database import TransactionCorrection
    rows = session.query(TransactionCorrection).filter_by(transaction_id=txn.id) \
        .order_by(TransactionCorrection.id).all()
    now = _current(txn)
    first = dict(now)
    for f in FIELDS:
        c = next((r for r in rows if r.field == f), None)
        if c is not None:
            first[f] = c.before
    since = _since(session)
    kept_from_start = bool(since and txn.created_at and txn.created_at >= since)
    if kept_from_start and (txn.source or 'manual') not in ('manual', ''):
        kind, label = 'bank', "What the bank's file said"
    elif kept_from_start:
        kind, label = 'entered', 'As it was first entered'
    else:
        kind = 'earliest_kept'
        label = ('The earliest version kept' + (f' (changes made before {_local_day(since)} were not kept)' if since else ''))
    return {'id': txn.id, 'current': now, 'first': first, 'first_kind': kind, 'first_label': label,
            'corrections': [{'field': r.field, 'before': r.before, 'after': r.after, 'on': _local_day(r.corrected_at)}
                            for r in rows],
            'pending': pending_of(session, txn.id)}


# ── B9 ────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _words(text):
    return {w for w in re.findall(r'[a-z]{3,}', (text or '').lower()) if w not in _NOISE}


def _pair_view(p):
    return {'id': p.id, 'pending_id': p.pending_id, 'posted_id': p.posted_id, 'how': p.how, 'state': p.state,
            'pending_date': p.pending_date.isoformat() if p.pending_date else None, 'pending_amount': p.pending_amount,
            'posted_date': p.posted_date.isoformat() if p.posted_date else None, 'posted_amount': p.posted_amount,
            'changed': (p.pending_amount is not None and p.posted_amount is not None
                        and abs(p.pending_amount - p.posted_amount) >= 0.005)}


def pending_of(session, posted_id):
    """The pending line a posted line followed, once paired."""
    from core.database import PendingPosted
    p = session.query(PendingPosted).filter_by(posted_id=posted_id, state='paired').first()
    return _pair_view(p) if p else None


def paired_ids(session, ids):
    from core.database import PendingPosted
    if not ids:
        return {}
    return {p.posted_id: _pair_view(p) for p in session.query(PendingPosted)
            .filter(PendingPosted.posted_id.in_(list(ids)), PendingPosted.state == 'paired').all()}


def _new_pair(session, pending, posted):
    from core.database import PendingPosted
    p = PendingPosted(pending_id=pending.id, posted_id=posted.id, account_id=posted.account_id,
                      pending_date=pending.date, pending_amount=pending.amount,
                      posted_date=posted.posted_date or posted.date, posted_amount=posted.amount)
    session.add(p)
    return p


def _pair(session, p, pending, how):
    """Both kept: the pending line is set aside whole, with its own date and amount; the posted one stays current."""
    from core import import_custody as ic
    sa = ic.set_aside(session, pending, reason=f'Pending. Posted {_say_day(p.posted_date)} '
                                               f'as ${p.posted_amount:,.2f}; the posted line counts.')
    p.set_aside_id, p.how, p.state, p.decided_at = sa.id, how, 'paired', datetime.now()
    session.flush()
    return p


def pair_by_bank_id(session, pending, posted):
    """The bank's own id says the posted line is the pending one, posted: established, nothing to ask."""
    p = _new_pair(session, pending, posted)
    session.flush()
    return _pair(session, p, pending, 'bank_id')


def suggest(session, posted, prefer=None):
    """A pending line this posted line may be: offered, never decided (B5). `prefer` is a look-alike the import
    already found. Returns the suggestion, or None."""
    from core.database import PendingPosted, Transaction
    if posted.pending:
        return None
    asked = {(p.pending_id) for p in session.query(PendingPosted).filter(PendingPosted.state.in_(('suggested', 'paired'))).all()}
    declined = {p.pending_id for p in session.query(PendingPosted).filter_by(posted_id=posted.id, state='declined').all()}
    if prefer is not None and prefer.pending and prefer.id not in asked | declined:
        best = prefer
    else:
        day = posted.posted_date or posted.date
        words = _words(posted.description)
        cands = session.query(Transaction).filter(
            Transaction.account_id == posted.account_id, Transaction.type == posted.type,
            Transaction.pending.is_(True), Transaction.id != posted.id,
            Transaction.date >= day - timedelta(days=PAIR_WINDOW_DAYS), Transaction.date <= day).all()
        cands = [c for c in cands if c.id not in asked | declined and words & _words(c.description)]
        if not cands:
            return None
        best = min(cands, key=lambda c: (abs(c.amount - posted.amount), abs((day - c.date).days)))
    p = _new_pair(session, best, posted)
    session.flush()
    return p


def suggestions(session):
    from core.database import Account, PendingPosted, Transaction
    names = {a.id: a.name for a in session.query(Account).all()}
    out = []
    for p in session.query(PendingPosted).filter_by(state='suggested').order_by(PendingPosted.id).all():
        pend, post = session.get(Transaction, p.pending_id), session.get(Transaction, p.posted_id)
        if pend is None or post is None:          # one of them was set aside since: nothing left to pair
            continue
        v = _pair_view(p)
        v.update(account=names.get(p.account_id, ''), pending_description=pend.description,
                 posted_description=post.description)
        out.append(v)
    return out


def answer(session, pair_id, yes):
    from core.database import PendingPosted, Transaction
    p = session.get(PendingPosted, int(pair_id or 0))
    if not p or p.state != 'suggested':
        return None, 'That pending line was not found.'
    pending = session.get(Transaction, p.pending_id)
    if not yes:
        p.state, p.decided_at = 'declined', datetime.now()
        session.flush()
        return p, None
    if pending is None or session.get(Transaction, p.posted_id) is None:
        return None, 'One of the two lines is no longer in the ledger.'
    return _pair(session, p, pending, 'your_yes'), None


def undone_by_restore(session, set_aside_id):
    """A restored pending line counts again, so the pair it was set aside for no longer holds."""
    from core.database import PendingPosted
    for p in session.query(PendingPosted).filter_by(set_aside_id=set_aside_id, state='paired').all():
        p.state, p.decided_at = 'undone', datetime.now()
