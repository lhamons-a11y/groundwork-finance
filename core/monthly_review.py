"""
Groundwork - the month's review, written when the month is complete (gw 2.0/MONTHLY_REVIEW.md, item 75, M1-M10)
=============================================================================================================
  - M2  a month is complete when every account that had IMPORTED records in it also has an imported record dated
        after it - or the account is inactive, or the person said it is not needed for reviews. Records Groundwork
        writes itself (a recurring bill's auto-log) or the person types (source 'manual') never hold a month: the
        question is whether the bank's records have moved past it. Until then, which accounts it waits for, and the
        day each one's records end.
  - M4  a saved review keeps the fingerprint of the month's records it was written from; records that arrive or
        change later are counted and said, never written over. Writing again keeps the earlier one.
  - M1/M6  only the most recent complete month without a review is due after an import - one at a time; the
        earlier months are written from Reports when the person asks.

The words are written in the page (the same report the Reports page writes); this module keeps time and record.
"""
import hashlib
import json
from datetime import date, datetime, timedelta


def month_bounds(month):
    y, m = int(month[:4]), int(month[5:7])
    start = date(y, m, 1)
    end = (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)
    return start, end


def _setting(session, key, default=None):
    from core.database import AppSetting
    row = session.query(AppSetting).filter_by(key=key).first()
    if not row or not row.value:
        return default
    try:
        return json.loads(row.value)
    except (TypeError, ValueError):
        return row.value


def _put(session, key, value):
    from core.database import AppSetting
    row = session.query(AppSetting).filter_by(key=key).first()
    val = value if isinstance(value, str) else json.dumps(value)
    if row:
        row.value = val
    else:
        session.add(AppSetting(key=key, value=val))


def fingerprint(session, month):
    """What the month's records are now: how many, and a hash of each row's id, date, amount, type and category."""
    from core.database import Transaction
    start, end = month_bounds(month)
    rows = session.query(Transaction.id, Transaction.date, Transaction.amount, Transaction.type, Transaction.category_id) \
        .filter(Transaction.date >= start, Transaction.date <= end).order_by(Transaction.id).all()
    h = hashlib.sha256(json.dumps([[r[0], r[1].isoformat(), round(r[2] or 0, 2), r[3], r[4]] for r in rows]).encode())
    return {'records': len(rows), 'hash': h.hexdigest()[:24]}


def status(session, month, today=None):
    """M2: complete, in progress, or waiting - and for which accounts."""
    from core.database import Account, Transaction
    from sqlalchemy import func
    today = today or date.today()
    start, end = month_bounds(month)
    if end >= today:
        return {'month': month, 'state': 'in_progress', 'waiting': []}
    skip = set(_setting(session, 'review_skip_accounts', []) or [])
    imported = func.coalesce(Transaction.source, '') != 'manual'
    in_month = {a for (a,) in session.query(Transaction.account_id).filter(
        Transaction.date >= start, Transaction.date <= end, imported).distinct()}
    if not in_month:
        return {'month': month, 'state': 'empty' if not session.query(Transaction.id).filter(
            Transaction.date >= start, Transaction.date <= end).first() else 'complete', 'waiting': []}
    last = dict(session.query(Transaction.account_id, func.max(Transaction.date)).filter(imported)
                .group_by(Transaction.account_id).all())
    accts = {a.id: a for a in session.query(Account).all()}
    waiting = []
    for aid in in_month:
        a = accts.get(aid)
        if aid is None or aid in skip or (a and not a.is_active):
            continue
        if last.get(aid) and last[aid] > end:
            continue
        waiting.append({'account_id': aid, 'account': a.name if a else 'an account',
                        'records_end': last[aid].isoformat() if last.get(aid) else None})
    waiting.sort(key=lambda w: w['records_end'] or '')
    return {'month': month, 'state': 'waiting' if waiting else 'complete', 'waiting': waiting}


def saved(session, month):
    """The saved review and what it was written from. A review saved before item 75 has no record of that."""
    text = _setting(session, f'report_text_{month}')
    if not text:
        return None
    meta = _setting(session, f'review_meta_{month}') or {}
    out = {'month': month, 'text': text if isinstance(text, str) else json.dumps(text), 'meta': meta,
           'legacy': not meta}
    if meta.get('fingerprint'):
        now = fingerprint(session, month)
        out['changed_since'] = None if now['hash'] == meta['fingerprint']['hash'] else \
            {'records_then': meta['fingerprint']['records'], 'records_now': now['records']}
    return out


def due(session, today=None):
    """M1/M6: the one month whose review is due after an import - the most recent complete month without a review
    written under this item (a review saved before it, possibly from a month in progress, doesn't count)."""
    from core.database import Transaction
    from sqlalchemy import func
    today = today or date.today()
    if (_setting(session, 'auto_monthly_review', True) in (False, 'false', '0', 0)):
        return None
    first = session.query(func.min(Transaction.date)).scalar()
    if not first:
        return None
    m = date(today.year, today.month, 1) - timedelta(days=1)
    month = f'{m.year}-{m.month:02d}'
    if month < f'{first.year}-{first.month:02d}':
        return None
    s = saved(session, month)
    if s and not s['legacy']:
        return None
    st = status(session, month, today)
    return month if st['state'] == 'complete' else None


def save(session, month, text, kind, today=None):
    """Save a review as the month's (M4: the earlier one goes to its history). kind: 'written' | 'summary' |
    'summary_failed'. Completeness and the records are worked out here, never taken from the page."""
    if kind not in ('written', 'summary', 'summary_failed'):
        raise ValueError('kind')
    st = status(session, month, today)
    if st['state'] == 'in_progress':
        raise ValueError('in_progress')
    old = saved(session, month)
    if old:
        hist = _setting(session, f'review_history_{month}', []) or []
        hist.append({'text': old['text'], 'meta': old['meta'], 'replaced_at': datetime.now().isoformat(timespec='seconds')})
        _put(session, f'review_history_{month}', hist[-10:])
    meta = {'written_at': datetime.now().isoformat(timespec='seconds'), 'kind': kind,
            'fingerprint': fingerprint(session, month), 'complete': st['state'] == 'complete',
            'missing': [w['account'] for w in st['waiting']], 'seen': False}
    _put(session, f'report_text_{month}', text)
    _put(session, f'review_meta_{month}', meta)
    return {'month': month, 'meta': meta}
