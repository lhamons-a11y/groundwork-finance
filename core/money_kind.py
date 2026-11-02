"""Item 111 (gw 2.0/TRANSFERS.md; Rob 2026-10-26: "build item 111" - X1-X10 as recommended, X3 (a), X6 (a)): money
moving between the person's own accounts. Every row gets ONE kind, worked out here and read everywhere (X1):

    spending       a purchase or bill
    income         money in from outside
    own_move       between the person's own accounts
    debt_payment   paying a card or loan
    interest_fees  the cost of debt
    refund         money back on a purchase
    cash_out       cash taken out
    unknown        can't be told

    X2  a move is a pair: money leaving one account and the same amount arriving in another within three days. The
        leaving side of a card or loan payment is `debt_payment` (X4), its arriving side (the card's *payment thank
        you*) `own_move`; any other pair is `own_move` on both sides. Only one side in Groundwork: a payment linked to
        a debt on record is `debt_payment`; anything else stays as filed.
    X3  each pair is the person's to confirm once; until then it is counted as a move and marked found, not yet
        confirmed (a). A yes can stand for that pair of accounts and that payee; a no ends the pair. Appended, never
        written over, each withdrawable (item 107's D8 pattern).
    X4  paying a card or loan is never spending; the purchases were. Interest and fees are the cost of debt.
    X5  a refund nets against the category of the purchase it reverses (the same payee's), else the one it was filed in
        when that is a spending category, else Other (X13 (a)). The purchase came before the refund (X12).
    X6  cash taken out is said as cash; what it was spent on isn't on record (a).
    X7  Venmo, Zelle, Cash App and PayPal are spending (or income) unless they pair with one of the person's accounts.
    X8  the kind sits beside the category and never overwrites it: nothing here writes a row.

Null model (X10 stage 2): a pair needs evidence beyond the amount - a side filed as a move or payment, or the bank's
own words for one - and its arriving side filed as a move or payment (or not filed), so a purchase and an unrelated
deposit, paycheck or store credit of the same amount never pair, and a household with no moves reads as before.

Reopened 2026-11-01 (TRANSFERS.md section 9, Rob: "As recommended"):
    X11 the bank's payment words count on the arriving side only (a card's *payment thank you*), never on the
        leaving side - a bill says "payment" too. A leaving side filed as spending pairs only when it reached a card
        or loan, and then still needs a sign on the arriving side.
    X16 a $0 row never pairs.
    X17 when another row could also have been the arriving side, the question names it.

Derived on every read. Only what the person said is stored.
"""
import re
from datetime import datetime

KINDS = ('spending', 'income', 'own_move', 'debt_payment', 'interest_fees', 'refund', 'cash_out', 'unknown')
NOT_SPENDING = frozenset(KINDS) - {'spending'}
PAIR_DAYS = 3
ARRIVING = (None, 'own_move', 'debt_payment', 'cash_out')     # how the arriving side of a move may be filed
SETTING = 'own_moves_said_json'
ANSWERS = ('yes', 'always', 'no')              # X3: this pair; this pair of accounts and payee from now on; not a move
DEBT_ACCOUNTS = {'credit', 'credit_card', 'loan', 'mortgage', 'line_of_credit', 'heloc', 'auto_loan', 'student_loan'}

# ── What a category's own name says (the one word list; X1 replaces the nine) ─────────────────────────────────────
DEBT_NAMES = {'debt', 'debt payment', 'debt payments', 'credit card payment', 'loan payment', 'payment'}
_WORDS = (('income', {'income', 'paycheck', 'salary'}),
          ('refund', {'refund', 'refunds'}),
          ('cash_out', {'atm', 'cash'}),
          ('interest_fees', {'interest', 'fees', 'fee'}),
          ('own_move', {'transfer', 'transfers', 'savings', 'investment', 'investments'}))

# ── What the bank's own words say ───────────────────────────────────────────────────────────────────────────────
REFUND_RX = re.compile(r'\brefund\b|\breversal\b|\bchargeback\b|\bcredit memo\b|\breturn.{0,10}(credit|merch)|\bmerchandise return\b', re.I)
ATM_RX = re.compile(r'\batm\b|\bcash withdrawal\b|\beft withdrawal\b', re.I)
PERSON_APP_RX = re.compile(r'\bvenmo\b|\bcash app\b|\bzelle\b|\bpaypal\b', re.I)
MOVE_RX = re.compile(r'\btransfer\b|\bxfer\b|\btrnsfr\b|\bsavings\b', re.I)
PAYMENT_RX = re.compile(r'\b(payment|pmt|pymt|autopay|auto pay|epay|e-payment)\b|\bthank you\b', re.I)
INTEREST_RX = re.compile(r'\binterest charge\b|\binterest charged\b|\bfinance charge\b|\bperiodic rate\b|\bpurchase interest\b|\bint chg\b|\bfinance chg\b|\blate fee\b|\bannual fee\b', re.I)


def filed_kind(name, ctype='', parent_name='', parent_type='', income=False):
    """The kind a category's filing implies, from its name, its type and its parent's. None for no category."""
    if not name:
        return None
    low, plow = (name or '').strip().lower(), (parent_name or '').strip().lower()
    if (ctype or '') == 'transfer' or (parent_type or '') == 'transfer' or 'transfer' in (low, plow):
        return 'own_move'
    if income or (ctype or '') == 'income' or (parent_type or '') == 'income':
        return 'income'
    if low in DEBT_NAMES or plow in DEBT_NAMES:
        return 'debt_payment'
    words = set(low.replace('/', ' ').replace('&', ' ').split())
    for kind, ws in _WORDS:
        if words & ws:
            return kind
    return 'spending'


def not_spending_category(name):
    """A category, by name alone, whose rows are never a price, a lever, an everyday charge or a lesson."""
    k = filed_kind(name)
    return bool(k) and k != 'spending'


def category_kinds(cats, income_ids=()):
    """{category id: filed kind}. `cats` {id: Category-like (name, type, parent_id)}."""
    out = {}
    for cid, c in cats.items():
        p = cats.get(c.parent_id) if c.parent_id else None
        out[cid] = filed_kind(c.name, c.type, p.name if p else '', p.type if p else '', cid in income_ids)
    return out


def category_ids(cats, kinds, income_ids=()):
    """The ids of the categories whose filing is one of `kinds` (e.g. {'own_move'} for the Transfer categories)."""
    return {cid for cid, k in category_kinds(cats, income_ids).items() if k in kinds}


# ── X2: pairs ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _text(t):
    return f'{t.description or ""} {t.merchant or ""}'


def payee_key(t):
    """The payee in letters only - a transfer's confirmation number changes every month, its payee doesn't."""
    return ''.join(ch for ch in (t.merchant or t.description or '').lower() if ch.isalpha())


def pair_key(out_row, in_row):
    return f'{out_row.id}>{in_row.id}'


def standing_key(out_row, in_row):
    return f'{out_row.account_id}>{in_row.account_id}|{payee_key(out_row)}'


def _evidence(d, c, ck, acct_type):
    # X11: a bill filed as spending and an unrelated deposit of the same amount are not a move - filed as spending,
    # the leaving side pairs only when it reached a card or loan
    if ck.get(d.category_id) == 'spending' and acct_type.get(c.account_id) not in DEBT_ACCOUNTS:
        return False
    if {ck.get(d.category_id), ck.get(c.category_id)} & {'own_move', 'debt_payment'}:
        return True
    if any(MOVE_RX.search(_text(t)) for t in (d, c)):
        return True
    return bool(PAYMENT_RX.search(_text(c)))                  # X11: "payment" on the arriving side only


def _amount(t):
    return round(abs(float(t.amount or 0)), 2)


def find_pairs(rows, ck, acct_type, said=(), others=None):
    """[(out_row, in_row)]: each debit paired with at most one credit of the same amount on another account within
    PAIR_DAYS, nearest date first. A pair the person said is not a move is skipped (X3). `others`, when given, gets
    {debit id: [the other credits that could have been its arriving side]} (X17)."""
    rejected = rejected_pairs(said)
    credits = {}
    for t in rows:
        # the arriving side is filed as a move or a payment, or not filed at all: money filed as income, as a refund
        # or under a spending category is something else that happens to match (the null model's store credit)
        if t.type == 'credit' and t.account_id and t.date and ck.get(t.category_id) in ARRIVING \
                and not REFUND_RX.search(_text(t)) and _amount(t) > 0:       # X16
            credits.setdefault(_amount(t), []).append(t)
    used, out = set(), []
    for d in sorted((t for t in rows if t.type == 'debit' and t.account_id and t.date), key=lambda t: (t.date, t.id)):
        if ck.get(d.category_id) == 'income' or REFUND_RX.search(_text(d)) or _amount(d) == 0:
            continue
        fits = [c for c in credits.get(_amount(d), [])
                if c.id not in used and c.account_id != d.account_id and abs((c.date - d.date).days) <= PAIR_DAYS
                and pair_key(d, c) not in rejected and _evidence(d, c, ck, acct_type)]
        if not fits:
            continue
        best = min(fits, key=lambda c: (abs((c.date - d.date).days), c.id))
        used.add(best.id)
        out.append((d, best))
        if others is not None and len(fits) > 1:
            others[d.id] = [c for c in fits if c is not best]
    return out


# ── X3: what the person said ──────────────────────────────────────────────────────────────────────────────────────
def _live(said):
    withdrawn = {s.get('withdraws') for s in said if s.get('answer') == 'withdrawn'}
    return [s for s in said if s.get('answer') in ANSWERS and s.get('n') not in withdrawn]


def rejected_pairs(said):
    return {s['key'] for s in _live(said) if s['answer'] == 'no'}


def answer_for(said, out_row, in_row):
    """'yes' / 'always' (confirmed), or None (found, not yet confirmed)."""
    pk, sk = pair_key(out_row, in_row), standing_key(out_row, in_row)
    for s in reversed(_live(said)):
        if s['answer'] in ('yes', 'no') and s.get('key') == pk:
            return s['answer']
        if s['answer'] == 'always' and s.get('standing') == sk:
            return 'always'
    return None


def append(said, out_row, in_row, answer, accounts=None, at=None):
    if answer not in ANSWERS:
        raise ValueError(answer)
    accounts = accounts or {}
    entry = {'n': len(said), 'key': pair_key(out_row, in_row), 'answer': answer,
             'from': accounts.get(out_row.account_id, ''), 'to': accounts.get(in_row.account_id, ''),
             'payee': (out_row.merchant or out_row.description or '').strip()[:80],
             'amount': round(abs(float(out_row.amount or 0)), 2), 'at': at or datetime.now().isoformat(timespec='seconds')}
    if answer == 'always':
        entry['standing'] = standing_key(out_row, in_row)
    return list(said) + [entry]


def withdraw(said, n, at=None):
    if not any(s.get('n') == n and s.get('answer') in ANSWERS for s in said):
        return None
    return list(said) + [{'n': len(said), 'answer': 'withdrawn', 'withdraws': n,
                          'at': at or datetime.now().isoformat(timespec='seconds')}]


def standing(said):
    """Settings: the standing statements that still hold, newest first."""
    return [s for s in reversed(_live(said)) if s['answer'] == 'always']


# ── X1: one kind per row ──────────────────────────────────────────────────────────────────────────────────────────
def _norm(s):
    return ''.join(ch for ch in (s or '').lower() if ch.isalnum())


def classify(rows, cats, acct_type, linked=(), said=(), income_ids=(), debt_names=()):
    """{row id: {'kind', 'category' (the category it counts in), 'pair' (the other row's id), 'confirmed'}}.
    `rows` Transaction-like; `cats` {id: Category-like}; `acct_type` {account id: type}; `linked` the ids attached to
    a debt on record (CheckingTransactionLink, a Debt Payoff entry); `debt_names` the debts' names - a payment from a
    bank account, in the bank's words for a payment, to a payee naming one is paying it (panel I-04)."""
    debt_names = [n for n in (_norm(x) for x in debt_names) if len(n) >= 4]
    ck = category_kinds(cats, income_ids)
    name = {cid: c.name for cid, c in cats.items()}
    linked = set(linked)
    out, others = {}, {}
    for d, c in find_pairs(rows, ck, acct_type, said, others):
        ans = answer_for(said, d, c)
        conf = ans in ('yes', 'always')
        out_kind = 'debt_payment' if acct_type.get(c.account_id) in DEBT_ACCOUNTS else 'own_move'
        out[d.id] = {'kind': out_kind, 'category': name.get(d.category_id), 'pair': c.id, 'confirmed': conf}
        out[c.id] = {'kind': 'own_move', 'category': name.get(c.category_id), 'pair': d.id, 'confirmed': conf}
        if d.id in others:
            out[d.id]['others'] = [x.id for x in others[d.id]]                   # X17
    # X5 / X12: the category a refund nets against - the same payee's latest purchase on or before the refund
    bought = {}
    for t in sorted(rows, key=lambda t: (t.date or datetime.min.date(), t.id)):
        if t.type == 'debit' and ck.get(t.category_id) == 'spending':
            bought.setdefault(payee_key(t), []).append((t.date or datetime.min.date(), name.get(t.category_id)))

    def bought_before(t):
        when = t.date or datetime.max.date()
        before = [cat for d, cat in bought.get(payee_key(t), []) if d <= when]
        return before[-1] if before else None
    for t in rows:
        if t.id in out:
            continue
        f, text = ck.get(t.category_id), _text(t)
        if t.type == 'debit':
            if t.id in linked or (debt_names and acct_type.get(t.account_id) not in DEBT_ACCOUNTS
                                  and PAYMENT_RX.search(text) and any(n in _norm(t.merchant or t.description) for n in debt_names)):
                k = 'debt_payment'
            elif f == 'cash_out' or ATM_RX.search(text):
                k = 'cash_out'
            elif f in ('debt_payment', 'interest_fees'):
                k = f
            elif INTEREST_RX.search(text) and f in (None, 'own_move'):
                k = 'interest_fees'
            elif PERSON_APP_RX.search(text):
                k = 'spending'                                       # X7: paying a friend is spending
            elif f == 'own_move':
                k = 'own_move'                                       # X2: one side only, as filed
            else:
                k = 'spending'
            out[t.id] = {'kind': k, 'category': name.get(t.category_id), 'pair': None, 'confirmed': None}
        elif t.type == 'credit':
            cat = name.get(t.category_id)
            if f == 'income':
                k = 'income'
            elif f == 'refund' or REFUND_RX.search(text):
                k = 'refund'
            elif PERSON_APP_RX.search(text):
                k = 'income'                                         # X7: money from a friend
            elif f in ('own_move', 'cash_out'):
                k = 'own_move'
            elif f == 'debt_payment':
                k = 'debt_payment'                                   # a card's payment thank you, the other side not here
            elif f in ('spending', 'interest_fees'):
                k = 'refund'                                         # money back, filed where it was spent
            else:
                k = 'unknown'
            if k == 'refund':                                        # X5
                cat = bought_before(t) or (cat if f == 'spending' else None) or 'Other'
            out[t.id] = {'kind': k, 'category': cat, 'pair': None, 'confirmed': None}
        else:
            out[t.id] = {'kind': 'unknown', 'category': name.get(t.category_id), 'pair': None, 'confirmed': None}
    return out


def _said(session):
    import json
    from core.database import AppSetting
    row = session.query(AppSetting).filter_by(key=SETTING).first()
    try:
        v = json.loads(row.value) if row and row.value else []
    except (TypeError, ValueError):
        v = []
    return v if isinstance(v, list) else []


def kinds(session, rows=None):
    """Every row's kind, from the record. `rows` defaults to every transaction (pairing needs both sides)."""
    from core.database import Account, Category, CheckingTransactionLink, DebtAccount, DebtLedgerEntry, Transaction
    from core.income_def import income_category_ids
    cats = {c.id: c for c in session.query(Category).all()}
    acct_type = {a.id: (a.type or '').lower() for a in session.query(Account).all()}
    linked = {r[0] for r in session.query(CheckingTransactionLink.checking_transaction_id).all()} | \
             {r[0] for r in session.query(DebtLedgerEntry.linked_checking_transaction_id).all() if r[0]}
    names = [d.name for d in session.query(DebtAccount).filter_by(is_active=True).all()]
    rows = session.query(Transaction).all() if rows is None else rows
    return classify(rows, cats, acct_type, linked, _said(session), income_category_ids(session), names)


def spending_of(rows, k):
    """(spent, moved): spending less refunds, and every other debit - one total for every reader."""
    spent = moved = 0.0
    for t in rows:
        kd = (k.get(t.id) or {}).get('kind')
        amt = abs(float(t.amount or 0))
        if kd == 'spending':
            spent += amt
        elif kd == 'refund':
            spent -= amt
        elif t.type == 'debit':
            moved += amt
    return round(spent, 2), round(moved, 2)


# ── X3: the question, asked once per pair ─────────────────────────────────────────────────────────────────────────
LABEL = 'Money between your accounts'
SOURCE = ('From your Ledger: the same amount left one of your accounts and reached another within three days. '
          'Until you answer, Groundwork counts it as a move, not as spending.')
ESTABLISHES = ('That the same amount left one of your accounts and reached another of your accounts within three days, '
               'with a sign it was a move: it was filed as a transfer or payment, the bank called it a transfer, or the '
               'arriving side was called a payment.')
CANNOT = ('Whether it really was one move - two unrelated amounts can match. A move to an account that is not in '
          'Groundwork has only one side here, and is counted as you filed it.')


def _day(d):
    return f'{d.strftime("%b")} {d.day}'


def sentence(out_row, in_row, accounts, others=()):
    amt = f'${abs(float(out_row.amount or 0)):,.2f}'
    also = ''.join(f' {amt} also reached {accounts.get(o.account_id, "another account")} on {_day(o.date)}.'
                   for o in others)                                              # X17: the other side it could be
    return (f'{amt} left {accounts.get(out_row.account_id, "one account")} on {_day(out_row.date)} and {amt} reached '
            f'{accounts.get(in_row.account_id, "another")} on {_day(in_row.date)}.{also} '
            'Is this money moving between your accounts?')


def asking(session):
    """X3: every found pair the person hasn't answered, newest first, as Needs attention's items."""
    from core.database import Account, Transaction
    k = kinds(session)
    said = _said(session)
    accounts = {a.id: a.name for a in session.query(Account).all()}
    ids = {i for i, v in k.items() if v['pair'] and not v['confirmed']}
    ids |= {o for i in ids for o in (k[i].get('others') or [])}
    rows = {t.id: t for t in session.query(Transaction).filter(Transaction.id.in_(ids)).all()} if ids else {}
    out = []
    for i in ids:
        t = rows.get(i)
        if t is None or t.type != 'debit' or k[i]['pair'] not in rows:
            continue
        c = rows[k[i]['pair']]
        if answer_for(said, t, c):
            continue
        out.append({'kind': 'own_move', 'subject': pair_key(t, c), 'pair': pair_key(t, c),
                    'title': (t.merchant or t.description or '').strip()[:60] or 'A move', 'date': t.date.isoformat(),
                    'amount': round(abs(float(t.amount or 0)), 2),
                    'sentence': sentence(t, c, accounts, [rows[o] for o in k[i].get('others') or [] if o in rows]),
                    'label': LABEL, 'source': SOURCE, 'fact': pair_key(t, c)})
    return sorted(out, key=lambda x: (x['date'], x['pair']), reverse=True)


def rows_of(session, pk):
    """The two rows of a pair key, while they still pair - else None."""
    from core.database import Transaction
    try:
        a, b = (int(x) for x in str(pk).split('>'))
    except ValueError:
        return None
    k = kinds(session)
    if (k.get(a) or {}).get('pair') != b:
        return None
    return session.get(Transaction, a), session.get(Transaction, b)


def money_out(t, k):
    """X19: a debit that left the household - spending, interest, cash, a payment to a debt whose purchases aren't on
    record. A move between the person's own accounts is not, and neither is a payment to a card that is in Groundwork:
    the card's purchases are already counted (the double count X4 ended)."""
    v = k.get(t.id) or {}
    if t.type != 'debit' or v.get('kind') == 'own_move':
        return False
    return not (v.get('kind') == 'debt_payment' and v.get('pair'))


def filed_income_pairs(rows, ck, acct_type, said=()):
    """X20: deposits filed as income that would pair as a move if they weren't - [(out_row, in_row)]. The Ledger
    never counts them as a move (a paycheck isn't one); Ask why's own-transfers check asks, by the same rule."""
    inc = {cid for cid, kd in ck.items() if kd == 'income'}
    as_unfiled = {cid: (None if cid in inc else kd) for cid, kd in ck.items()}
    return [(d, c) for d, c in find_pairs(rows, as_unfiled, acct_type, said) if c.category_id in inc]


def moved_by(rows, k):
    """Every debit that is not spending, by kind - so a sentence names each for what it is, never all as a move."""
    out = {}
    for t in rows:
        kd = (k.get(t.id) or {}).get('kind')
        if t.type == 'debit' and kd and kd != 'spending':
            out[kd] = round(out.get(kd, 0.0) + abs(float(t.amount or 0)), 2)
    return out
