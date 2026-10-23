"""
Groundwork - purchases an employer pays back (gw 2.0/ASK_WHY.md C5, item 72 stage 4)
====================================================================================
Told, never guessed (AP4, TM5): only after the person says they buy things for work and get paid back can a
purchase be marked, and only the person marks one.

  - A marked purchase moves under "Paid back by work", a category inside Transfer - the rule every spending and
    income figure already follows (app.js _isSpend/_isEarn, the server's 'transfer' type) - so it is not spending.
  - A repayment deposit is matched by the person, in part or in full. A deposit that the matches use up entirely
    moves under the same category, so it is not income. A deposit that carries other money too (a reimbursement
    added to a paycheck) stays where it is - one transaction can't be split - and the match records the paid-back
    part against the purchase; this is said where it happens.
  - "It won't be paid back" puts the purchase, and every deposit moved for it, back where they were.
Every step is recorded in the Historian (AP10). Nothing is moved without the person's tap.
"""
from datetime import datetime, timedelta

CATEGORY = 'Paid back by work'
MATCH_WINDOW_DAYS = 180
CENT = 0.005


def category(session):
    """The "Paid back by work" category, inside Transfer (both made if missing)."""
    from core.database import Category
    from sqlalchemy import func
    transfer = session.query(Category).filter(func.lower(Category.name) == 'transfer').first()
    if not transfer:
        transfer = Category(name='Transfer', type='transfer', is_system=True)
        session.add(transfer)
        session.flush()
    c = session.query(Category).filter(func.lower(Category.name) == CATEGORY.lower()).first()
    if not c:
        c = Category(name=CATEGORY, type='transfer', parent_id=transfer.id, is_system=True)
        session.add(c)
        session.flush()
    return c


def _used(session, credit_id):
    from core.database import ReimbursementMatch
    from sqlalchemy import func
    return float(session.query(func.coalesce(func.sum(ReimbursementMatch.amount), 0.0))
                 .filter(ReimbursementMatch.credit_transaction_id == credit_id).scalar() or 0)


def paid_back(session, item):
    from core.database import ReimbursementMatch
    return round(sum(m.amount for m in session.query(ReimbursementMatch).filter_by(item_id=item.id)), 2)


def _note(session, event, **ctx):
    import json
    from core.database import HistorianEntry
    session.add(HistorianEntry(event_category=event, context_json=json.dumps(ctx, default=str)))


def mark(session, transaction_id, employer=''):
    from core.database import ReimbursableItem, Transaction
    t = session.get(Transaction, transaction_id)
    if not t or t.type != 'debit' or (t.amount or 0) <= 0:
        return None, 'Only a purchase (money out) can be marked.'
    if session.query(ReimbursableItem).filter_by(transaction_id=t.id).filter(ReimbursableItem.status != 'written_off').first():
        return None, 'That purchase is already marked.'
    cat = category(session)
    item = ReimbursableItem(transaction_id=t.id, employer=(employer or '').strip()[:120], amount=round(float(t.amount), 2),
                            original_category_id=t.category_id, status='waiting')
    t.category_id = cat.id
    session.add(item)
    session.flush()
    _note(session, 'reimbursement_marked', item=item.id, transaction=t.id, amount=item.amount,
          original_category=item.original_category_id)
    return item, None


def candidates(session, item):
    """Deposits that could be this purchase's repayment: on or after the purchase, within six months, with money not
    already matched. Ones whose payer names the employer come first. Nothing is matched here - the person taps."""
    from core.database import Transaction
    t = session.get(Transaction, item.transaction_id)
    if not t:
        return []
    rows = session.query(Transaction).filter(
        Transaction.type == 'credit', Transaction.date >= t.date - timedelta(days=3),
        Transaction.date <= t.date + timedelta(days=MATCH_WINDOW_DAYS)).all()
    left_on_item = round(item.amount - paid_back(session, item), 2)
    out = []
    emp = (item.employer or '').lower()
    for c in rows:
        left = round(float(c.amount or 0) - _used(session, c.id), 2)
        if left <= CENT:
            continue
        name = (c.merchant or c.description or '')
        out.append({'id': c.id, 'date': c.date.isoformat(), 'amount': round(float(c.amount), 2), 'left': left,
                    'name': name[:80], 'would_apply': round(min(left, left_on_item), 2),
                    'carries_more': left - left_on_item > CENT, 'names_employer': bool(emp) and emp in name.lower()})
    out.sort(key=lambda x: (not x['names_employer'], abs(x['left'] - left_on_item), x['date']))
    return out[:8]


def match(session, item_id, credit_id):
    from core.database import ReimbursableItem, ReimbursementMatch, Transaction
    item = session.get(ReimbursableItem, item_id)
    c = session.get(Transaction, credit_id)
    if not item or item.status != 'waiting':
        return None, 'That purchase is not waiting to be paid back.'
    if not c or c.type != 'credit':
        return None, 'Only a deposit can be matched.'
    left_item = round(item.amount - paid_back(session, item), 2)
    left_credit = round(float(c.amount or 0) - _used(session, c.id), 2)
    amt = round(min(left_item, left_credit), 2)
    if amt <= CENT:
        return None, 'Nothing left to match.'
    m = ReimbursementMatch(item_id=item.id, credit_transaction_id=c.id, amount=amt, original_category_id=c.category_id)
    session.add(m)
    session.flush()
    moved = False
    if abs(float(c.amount or 0) - _used(session, c.id)) <= CENT:      # the deposit is used up: it was all repayment
        c.category_id = category(session).id
        moved = True
    if item.amount - paid_back(session, item) <= CENT:
        item.status, item.closed_at = 'paid', datetime.now()
    _note(session, 'reimbursement_matched', item=item.id, credit=c.id, amount=amt, deposit_moved=moved)
    return {'match': m.id, 'amount': amt, 'deposit_moved': moved, 'status': item.status}, None


def _restore_credit(session, m):
    from core.database import Transaction
    c = session.get(Transaction, m.credit_transaction_id)
    if c and c.category_id == category(session).id:
        c.category_id = m.original_category_id


def unmatch(session, match_id):
    from core.database import ReimbursableItem, ReimbursementMatch
    m = session.get(ReimbursementMatch, match_id)
    if not m:
        return None, 'Not a match Groundwork made.'
    item = session.get(ReimbursableItem, m.item_id)
    _restore_credit(session, m)
    session.delete(m)
    if item and item.status == 'paid':
        item.status, item.closed_at = 'waiting', None
    _note(session, 'reimbursement_unmatched', item=m.item_id, credit=m.credit_transaction_id, amount=m.amount)
    return {'ok': True}, None


def write_off(session, item_id):
    """It won't be paid back: the purchase, and any deposit moved for it, go back where they were."""
    from core.database import ReimbursableItem, ReimbursementMatch, Transaction
    item = session.get(ReimbursableItem, item_id)
    if not item or item.status == 'written_off':
        return None, 'Not a marked purchase.'
    t = session.get(Transaction, item.transaction_id)
    if t and t.category_id == category(session).id:
        t.category_id = item.original_category_id
    for m in session.query(ReimbursementMatch).filter_by(item_id=item.id).all():
        _restore_credit(session, m)
    item.status, item.closed_at = 'written_off', datetime.now()
    _note(session, 'reimbursement_written_off', item=item.id, transaction=item.transaction_id)
    return {'ok': True}, None


def unmark(session, item_id):
    """Not a work purchase after all (only before any repayment is matched): back to its category, record removed."""
    from core.database import ReimbursableItem, ReimbursementMatch, Transaction
    item = session.get(ReimbursableItem, item_id)
    if not item:
        return None, 'Not a marked purchase.'
    if session.query(ReimbursementMatch).filter_by(item_id=item.id).count():
        return None, 'A repayment is matched to it - undo that first, or say it won\'t be paid back.'
    t = session.get(Transaction, item.transaction_id)
    if t and t.category_id == category(session).id:
        t.category_id = item.original_category_id
    session.delete(item)
    _note(session, 'reimbursement_unmarked', transaction=item.transaction_id)
    return {'ok': True}, None


def state(session):
    from core.database import ReimbursableItem, ReimbursementMatch, Transaction
    items = []
    for it in session.query(ReimbursableItem).filter(ReimbursableItem.status != 'written_off') \
            .order_by(ReimbursableItem.marked_at.desc()).limit(50):
        t = session.get(Transaction, it.transaction_id)
        ms = [{'id': m.id, 'amount': m.amount, 'credit': m.credit_transaction_id,
               'date': (session.get(Transaction, m.credit_transaction_id).date.isoformat()
                        if session.get(Transaction, m.credit_transaction_id) else None)}
              for m in session.query(ReimbursementMatch).filter_by(item_id=it.id)]
        paid = round(sum(m['amount'] for m in ms), 2)
        items.append({'id': it.id, 'status': it.status, 'employer': it.employer, 'amount': it.amount,
                      'paid_back': paid, 'left': round(it.amount - paid, 2),
                      'date': t.date.isoformat() if t else None, 'name': (t.merchant or t.description or '')[:80] if t else '',
                      'matches': ms, 'candidates': candidates(session, it) if it.status == 'waiting' else []})
    return items
