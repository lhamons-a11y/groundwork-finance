"""Item 68 B6/B7 (gw 2.0/BILLS_AND_PAYING.md): "can I pay this?" against the person's buffer, and "paid?".

The engine only computes. Every answer carries its working and names what it can't see; nothing here decides, pays,
or writes. A buffer the person never set is never assumed (AP9), and an account whose last download is more than 24
hours old says so first (Rob, 2026-10-10).
"""
from datetime import timedelta

STALE_AFTER = timedelta(hours=24)
CANT_SEE = 'Not counted: pending charges, holds, and checks that are not in the download yet.'
NEAR_SHARE = 0.10                       # a payment within 10% of the bill is asked about, never assumed
BEFORE_DUE, AFTER_DUE = timedelta(days=25), timedelta(days=10)


def _money(x):
    return f'${x:,.2f}'


def pay_check(balance, balance_as_of, last_download, buffer, bill_amount, earlier, now):
    """balance: the account's figure (the bank's own running balance where it gave one) or None; balance_as_of: its
    date or None; last_download: when the account's transactions last came in (datetime) or None; buffer: the
    person's own floor or None; bill_amount: the confirmed bill's amount or None; earlier: [(name, amount)] of
    confirmed bills due before this one from the same account, not yet seen paid; now: datetime.

    {'state': 'fits' | 'below' | 'unknown', 'after', 'margin', 'stale', 'stale_hours', 'working': [str],
     'missing': [str], 'cant_see': str}"""
    out = {'state': 'unknown', 'after': None, 'margin': None, 'stale': False, 'stale_hours': None, 'working': [],
           'missing': [], 'cant_see': CANT_SEE}
    if last_download is not None:
        age = now - last_download
        out['stale'] = age > STALE_AFTER
        out['stale_hours'] = int(age.total_seconds() // 3600)
    if last_download is None or balance is None:
        out['missing'].append('a downloaded balance for this account')
    if buffer is None:
        out['missing'].append('the amount you want to always leave in this account')
    if bill_amount is None:
        out['missing'].append("the bill's amount")
    if out['missing']:
        return out
    earlier_total = round(sum(a for _, a in earlier), 2)
    after = round(balance - earlier_total - bill_amount, 2)
    margin = round(after - buffer, 2)
    out.update(after=after, margin=margin, state='fits' if margin >= 0 else 'below')
    as_of = f' as of {balance_as_of:%b} {balance_as_of.day}' if balance_as_of else ''
    out['working'] = ([f'Balance {_money(balance)}{as_of}']
                      + [f'minus {name} {_money(a)} (due earlier)' for name, a in earlier]
                      + [f'minus this bill {_money(bill_amount)}', f'= {_money(after)}',
                         f'your floor {_money(buffer)}: {_money(abs(margin))} {"above" if margin >= 0 else "below"}'])
    return out


def paid_match(bill_amount, due, name, txns, answer=None):
    """Look for the bill's payment among the paying account's transactions. txns: dicts with id, date, amount, type,
    description, running_balance. answer: the person's own word on a transaction ({'yes': id | None, 'no': [ids]}).

    {'state': 'paid' | 'near' | 'not_seen' | 'unknown', 'txn': {...} | None, 'lowest': (amount, date) | None}
    A match rests on a transaction and shows it; a near-match is asked about; nothing is assumed."""
    if bill_amount is None or due is None:
        return {'state': 'unknown', 'txn': None, 'lowest': None}
    answer = answer or {}
    rejected = set(answer.get('no') or [])
    debits = [t for t in txns if t.get('type') == 'debit' and due - BEFORE_DUE <= t['date'] <= due + AFTER_DUE
              and t['id'] not in rejected]
    chosen = next((t for t in txns if answer.get('yes') is not None and t['id'] == answer.get('yes')), None)
    state = 'paid' if chosen else None
    if not chosen:
        exact = sorted((t for t in debits if abs(t['amount'] - bill_amount) < 0.005), key=lambda t: abs((t['date'] - due).days))
        if exact:
            chosen, state = exact[0], 'paid'
    if not chosen:
        words = [w for w in str(name or '').lower().split() if len(w) >= 3]
        near = sorted((t for t in debits if abs(t['amount'] - bill_amount) <= bill_amount * NEAR_SHARE
                       or any(w in str(t.get('description') or '').lower() for w in words)),
                      key=lambda t: (abs(t['amount'] - bill_amount), abs((t['date'] - due).days)))
        if near:
            return {'state': 'near', 'txn': near[0], 'lowest': None}
        return {'state': 'not_seen', 'txn': None, 'lowest': None}
    after = [t for t in txns if t['date'] >= chosen['date'] and t.get('running_balance') not in (None, 0)]
    lowest = min(((t['running_balance'], t['date']) for t in after), default=None)
    return {'state': state, 'txn': chosen, 'lowest': lowest}
