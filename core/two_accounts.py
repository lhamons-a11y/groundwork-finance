"""Item 107 (gw 2.0/SAME_CHARGE_TWO_ACCOUNTS.md; Rob 2026-10-21: "D1-D12 as recommended, build it"): the same charge
paid from two of the person's accounts in the same month - said as what was seen, never as a mistake, never why.

    D1  the same payee: the Ledger key (merchant, else description) in letters and digits, equal, or one inside the
        other when both are 4+ characters (the `_price_line` test)
    D2  the two charges within 5% of each other
    D3  two different accounts; never a transfer, a card or loan payment, a deposit or refund, or a pending line - so
        checking paying the card never pairs with a charge on the card, even when a store card shares the store's name
    D4  the same calendar month; said from the second such month within the last three (one month is every card switch)
    D5  read per pair of accounts, never from both accounts' charges together
    §7  measured before build (the null model): a charge pairs only when it is that payee's one charge on that
        account that month, and the same amount again across the months - shopping at one store from two accounts
        otherwise met D1-D4 in 299 of 300 households. A row whose bank text says it is a payment never pairs (D3).
    D8  the person's answer is appended to `two_accounts_said_json`, never written over; the newest one counts, Undo
        adds a withdrawal (each statement has its place, `n`). "Both are meant" and "these aren't the same" end the pair; "one of these should stop" is said
        once more if both still pay it two months later, then never; Dismiss is "not now" for 60 days
    D9  an answer feeds nothing else: no total, budget line, recurring item or person changes

Derived on every read: nothing about a finding is stored, only what the person said.
"""
import re
from datetime import date, datetime, timedelta

SETTING = 'two_accounts_said_json'
MIN_KEY = 4               # D1: containment only between names of 4+ characters
SAME = 0.05               # D2: the house "same subscription" rule (core/byb_offer.STEADY)
MONTHS_SAID = 2           # D4 (b): the second such month ...
WINDOW = 3                # ... within the last three calendar months, this one included
NOT_NOW_DAYS = 60         # D8: Dismiss is the A.4 cooldown
AGAIN_MONTHS = 2          # D8 (a): "should stop", and both still pay it two months on
ANSWERS = ('both_meant', 'should_stop', 'not_same', 'not_now')
SAID_ANSWERS = ('both_meant', 'should_stop', 'not_same')      # what Settings lists; Dismiss isn't a statement
PAYMENT_NAMES = {'debt', 'credit card payment', 'loan payment', 'debt payment'}
# D3: a payment to a card or loan on record under no payment category still says what it is in the bank's own words
_PAYMENT_WORDS = re.compile(r'\b(payment|pmt|pymt|autopay|auto pay|epay|e-payment)\b', re.I)


def key(merchant, description=''):
    """D1: the Ledger's merchant key, letters and digits only."""
    return ''.join(ch for ch in (merchant or description or '').lower() if ch.isalnum())


def same_payee(a, b):
    if not a or not b:
        return False
    return a == b or (len(a) >= MIN_KEY and len(b) >= MIN_KEY and (a in b or b in a))


def payment_category_ids(cats):
    """D3: Transfer-typed categories and the ones under them (core/checkin._transfer_ids), and the debt / card / loan
    payment categories and the ones under them. `cats` {id: Category}."""
    top = {cid for cid, c in cats.items() if (c.type or '') == 'transfer'
           or (c.name or '').strip().lower() in ({'transfer'} | PAYMENT_NAMES)}
    return top | {cid for cid, c in cats.items() if c.parent_id in top}


def _month(d):
    return f'{d.year}-{d.month:02d}'


def _months_back(today, k):
    y, m = today.year, today.month - k
    while m < 1:
        y, m = y - 1, m + 12
    return f'{y}-{m:02d}'


def eligible(t, excluded_cats):
    """D3, one row: a charge, settled, not a transfer or a payment toward a debt."""
    if t.type != 'debit' or getattr(t, 'pending', False) or not t.account_id or not t.date:
        return False
    if (t.amount or 0) <= 0 or t.category_id in excluded_cats:
        return False
    if _PAYMENT_WORDS.search(t.description or '') or _PAYMENT_WORDS.search(t.merchant or ''):
        return False
    return bool(key(t.merchant, t.description))


def pairs(rows, accounts, excluded_cats, today, months=WINDOW):
    """Every pair of accounts paying the same payee at the same amount in the same month, over the last `months`
    calendar months (this one included). `rows` Transaction-like; `accounts` {id: name}.
    -> [{key, payee, accounts: [id, id], account_names, months: [{month, rows: [row, row]}], amount}] newest month
    last in each, ordered by payee. Each pair is read from its own two accounts' rows only (D5)."""
    first = _months_back(today, months - 1)
    by_month, count = {}, {}
    for t in rows:
        if t.date > today or _month(t.date) < first or not eligible(t, excluded_cats):
            continue
        by_month.setdefault(_month(t.date), []).append(t)
        ck = (_month(t.date), t.account_id, key(t.merchant, t.description))
        count[ck] = count.get(ck, 0) + 1
    # Null model (section 7): shopping at one store from two accounts met D1-D4 in 299 of 300 households. A charge
    # pairs only when it is that payee's one charge on that account that month - a subscription charges once.
    once = lambda t: count[(_month(t.date), t.account_id, key(t.merchant, t.description))] == 1
    by_month = {m: [t for t in ts if once(t)] for m, ts in by_month.items()}
    found = {}
    for m, ts in sorted(by_month.items()):
        ts = sorted(ts, key=lambda t: (float(t.amount), t.id))
        taken = set()
        for i, a in enumerate(ts):
            ka = key(a.merchant, a.description)
            for b in ts[i + 1:]:
                if float(b.amount) > float(a.amount) * (1 + SAME):
                    break                                            # sorted by amount: nothing further is within 5%
                if b.account_id == a.account_id or not same_payee(ka, key(b.merchant, b.description)):
                    continue
                kb = key(b.merchant, b.description)
                canon = min((ka, kb), key=lambda k: (len(k), k))
                ids = tuple(sorted((a.account_id, b.account_id)))
                pk = f'{canon}|{ids[0]}|{ids[1]}'
                if (pk, m) in taken:
                    continue                                         # one pair of rows per pair of accounts per month
                taken.add((pk, m))
                left, right = (a, b) if a.account_id == ids[0] else (b, a)
                p = found.setdefault(pk, {'key': pk, 'canon': canon, 'accounts': list(ids), 'months': []})
                p['months'].append({'month': m, 'rows': [left, right]})
    out = []
    for p in found.values():
        # ... and the same charge again: each month's pair within 5% of the latest month's (section 7)
        ref = float(p['months'][-1]['rows'][0].amount)
        p['months'] = [m for m in p['months'] if all(abs(float(r.amount) - ref) <= ref * SAME for r in m['rows'])]
        last = p['months'][-1]['rows']
        names = [r.merchant or r.description or '' for m in p['months'] for r in m['rows']]
        p['payee'] = min(names, key=lambda n: (len(n), n)).strip()   # the plainest spelling on record
        p['account_names'] = [accounts.get(a, '') for a in p['accounts']]
        p['amount'] = round(float(last[0].amount), 2)
        out.append(p)
    return sorted(out, key=lambda p: (p['payee'].lower(), p['key']))


# ── D8: what the person said ─────────────────────────────────────────────────────────────────────────────────────
def effective(said, pk):
    """The newest answer for a pair that has not been withdrawn, or None."""
    withdrawn = {s.get('withdraws') for s in said if s.get('answer') == 'withdrawn'}
    live = [s for s in said if s.get('key') == pk and s.get('answer') in ANSWERS and s.get('n') not in withdrawn]
    return live[-1] if live else None


def _again_month(at):
    d = datetime.fromisoformat(at).date()
    m = d.month + AGAIN_MONTHS
    return f'{d.year + (m - 1) // 12}-{(m - 1) % 12 + 1:02d}'


def state(p, said, today):
    """What a pair shows now: 'said' (2+ months, nothing answered), 'again' (once more, after "should stop"), or None.
    A single month is never said on the Dashboard (D4); Ask why lists it as one month."""
    s = effective(said, p['key'])
    months = [m['month'] for m in p['months']]
    if s is None:
        return 'said' if len(months) >= MONTHS_SAID else None
    if s.get('again'):
        return None                                                  # the once-more was answered: then never
    a = s['answer']
    if a in ('both_meant', 'not_same'):
        return None
    if a == 'not_now':
        until = datetime.fromisoformat(s['at']).date() + timedelta(days=NOT_NOW_DAYS)
        return 'said' if today >= until and len(months) >= MONTHS_SAID else None
    if a == 'should_stop':
        return 'again' if any(m >= _again_month(s['at']) for m in months) else None
    return None


def append(said, p, answer, at=None, again=False):
    """D8: a new statement, added after the others. Nothing is written over."""
    if answer not in ANSWERS:
        raise ValueError(answer)
    entry = {'n': len(said), 'key': p['key'], 'payee': p['payee'], 'accounts': p['accounts'], 'amount': p['amount'],
             'answer': answer, 'at': at or datetime.now().isoformat(timespec='seconds')}
    if again:
        entry['again'] = True
    return list(said) + [entry]


def withdraw(said, n, at=None):
    """Undo: a withdrawal of statement `n`, added after the others. It removes nothing."""
    if not any(s.get('n') == n and s.get('answer') in ANSWERS for s in said):
        return None
    return list(said) + [{'n': len(said), 'answer': 'withdrawn', 'withdraws': n,
                          'at': at or datetime.now().isoformat(timespec='seconds')}]


def listed(said):
    """Settings: each statement the person made that still stands, newest first."""
    withdrawn = {s.get('withdraws') for s in said if s.get('answer') == 'withdrawn'}
    return [s for s in reversed(said) if s.get('answer') in SAID_ANSWERS and s.get('n') not in withdrawn]


# ── D7: the words ────────────────────────────────────────────────────────────────────────────────────────────────
WORDS_ANSWER = {'both_meant': 'Both are meant', 'should_stop': 'One of these should stop',
                'not_same': "These aren't the same"}
SOURCE = ('From your Ledger: the same payee at the same amount, from two of your accounts, in the same month. '
          "Groundwork can't tell whether both are meant.")
LABEL = 'Paid from two accounts'
ESTABLISHES = ('That the same payee, at amounts within 5% of each other, was paid from two of your accounts in the '
               'same month. Transfers, card and loan payments, refunds and pending lines are left out.')
CANNOT = ('Whether both are meant - one may be for someone else. Two different services under one name, a price that '
          'changed between the two, and anything paid outside your Ledger are not seen.')


def _day(iso):
    d = date.fromisoformat(iso)
    return f'{d.strftime("%b")} {d.day}'


def _month_name(m):
    return date(int(m[:4]), int(m[5:]), 1).strftime('%B')


def _and(xs):
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]


def _row(t, accounts):
    return {'id': t.id, 'date': t.date.isoformat(), 'amount': round(float(t.amount), 2), 'account_id': t.account_id,
            'account': accounts.get(t.account_id, ''), 'merchant': t.merchant or '', 'description': (t.description or '')[:140]}


def sentence(p, kind='said', since=None):
    """D7's fixed words. No verdict, no cause."""
    last = p['months'][-1]
    a, b = last['rows']
    names = p['account_names']
    seen = f'${float(a.amount):,.2f} from {names[0]} on {_day(a.date.isoformat())} and ${float(b.amount):,.2f} from {names[1]} on {_day(b.date.isoformat())}'
    if kind == 'again':
        later = [m['month'] for m in p['months'] if since and m['month'] >= since]
        return (f'You said one of these should stop. Both paid it in {_and([_month_name(m) for m in later])} '
                f'({seen}).')
    earlier = [_month_name(m['month']) for m in p['months'][:-1]]
    tail = f' Both accounts paid it in {_and(earlier)} too.' if earlier else ' One month only.'
    return seen[0].upper() + seen[1:] + '.' + tail


def item(p, kind, said, accounts):
    s = effective(said, p['key'])
    since = _again_month(s['at']) if kind == 'again' and s else None
    return {'kind': 'two_accounts', 'subject': p['key'], 'title': p['payee'], 'pair': p['key'], 'state': kind,
            'accounts': p['accounts'], 'account_names': p['account_names'], 'amount': p['amount'],
            'months': [m['month'] for m in p['months']], 'sentence': sentence(p, kind, since),
            'label': LABEL, 'source': SOURCE, 'search': p['payee'],
            'rows': [_row(t, accounts) for m in p['months'] for t in m['rows']],
            'fact': p['key'] + '|' + kind}
