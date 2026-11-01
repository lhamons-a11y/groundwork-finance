"""Item 111 (gw 2.0/TRANSFERS.md; Rob 2026-10-26: "build item 111" - X1-X10 as recommended): money moving between
the person's own accounts. One kind per row, in one place (core/money_kind.py), read everywhere.

    X1  one definition      X2  a move is a pair; one side only stays as filed     X3  confirmed once, (a) counted
    X4  paying a card is not spending      X5  a refund nets in its category       X6  cash said as cash (a)
    X7  Venmo / Zelle are spending unless they pair      X8  the category stays the person's
    X9  the Morgans filed like an import      X10 the null model: no moves, no change

Reopened 2026-11-01 (TRANSFERS.md section 9, Rob: "As recommended"):
    X11 "payment" counts on the arriving side only    X12 a refund nets against a purchase before it
    X13 (a) no purchase, not filed as spending: Other    X14 unruled - as built    X15 (a) Zelle filed Debt: as filed
    X16 $0 never pairs    X17 (b) the other candidate named    X18 the null model has bills    X19 readers read the kind
    X20 (a) Ask why pairs by the Ledger's rule
"""
import json
import random
import re
import subprocess
from datetime import date, timedelta
from types import SimpleNamespace as N

CHK, VISA, SAV = 1, 2, 3
CATS = {10: ('Groceries', 'expense', None), 11: ('Debt', 'expense', None), 12: ('Transfer', 'transfer', None),
        13: ('Paycheck / Salary', 'income', None), 14: ('ATM', 'expense', None), 15: ('Interest / Fees', 'expense', None),
        16: ('Shopping', 'expense', None), 17: ('Savings', 'expense', None), 18: ('Utilities', 'expense', None),
        19: ('Insurance', 'expense', None)}
ACCT = {CHK: 'checking', VISA: 'credit', SAV: 'savings'}


def _cats():
    return {i: N(id=i, name=n, type=t, parent_id=p) for i, (n, t, p) in CATS.items()}


def _row(i, d, amount, acct, desc, cat, kind='debit', merchant=''):
    return N(id=i, date=d, amount=amount, account_id=acct, type=kind, category_id=cat, description=desc, merchant=merchant)


def _fn(src, name):
    m = re.search(r'\n(?:async )?function ' + name + r'\(.*?\n\}\n', src, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check = ctx.check
    from core import money_kind as mk
    D = date(2026, 9, 1)
    cats = _cats()

    # ── X1 / X2 / X4-X7: each kind on planted rows ────────────────────────────────────────────────────────────────
    rows = [
        _row(1, D, 120.00, VISA, 'KROGER #12', 10, merchant='Kroger'),                      # a purchase on the card
        _row(2, D + timedelta(days=20), 600.00, CHK, 'CHASE VISA PAYMENT', 11),             # paying the card ...
        _row(3, D + timedelta(days=21), 600.00, VISA, 'PAYMENT THANK YOU', 11, 'credit'),   # ... and its arrival
        _row(4, D + timedelta(days=2), 300.00, CHK, 'TRANSFER TO SAVINGS', 12),             # a move ...
        _row(5, D + timedelta(days=2), 300.00, SAV, 'TRANSFER FROM CHECKING', 12, 'credit'),  # ... both sides
        _row(6, D + timedelta(days=5), 200.00, CHK, 'ONLINE TRANSFER TO 4411', 12),         # one side only
        _row(7, D + timedelta(days=6), 30.00, VISA, 'KROGER REFUND', 12, 'credit', 'Kroger'),  # refund filed Transfer
        _row(8, D + timedelta(days=7), 60.00, CHK, 'ATM WITHDRAWAL 0042', 12),              # cash
        _row(9, D + timedelta(days=8), 45.00, CHK, 'ZELLE TO SAM', 12),                     # paying a friend
        _row(10, D + timedelta(days=9), 2150.00, CHK, 'ACME PAYROLL', 13, 'credit'),        # pay
        _row(11, D + timedelta(days=10), 24.99, VISA, 'INTEREST CHARGE ON PURCHASES', 15),  # interest
        _row(12, D + timedelta(days=11), 389.00, CHK, 'RIVERSIDE AUTO LOAN PMT', 11),       # a loan, other side not here
    ]
    before = [(r.id, r.category_id) for r in rows]
    k = mk.classify(rows, cats, ACCT)
    got = {i: k[i]['kind'] for i in k}
    check(f's257 X1 each kind on planted rows ({got})',
          got == {1: 'spending', 2: 'debt_payment', 3: 'own_move', 4: 'own_move', 5: 'own_move', 6: 'own_move',
                  7: 'refund', 8: 'cash_out', 9: 'spending', 10: 'income', 11: 'interest_fees', 12: 'debt_payment'})
    check('s257 X2 a pair is found on both sides, and named', k[2]['pair'] == 3 and k[3]['pair'] == 2 and k[4]['pair'] == 5
          and k[2]['confirmed'] is False)
    spent, moved = mk.spending_of(rows, k)
    check(f's257 X4 the double count is gone: spending is the purchase less the refund, and the card payment is not in it '
          f'(spent {spent}, moved {moved})', spent == 135.00 and moved == round(600 + 300 + 200 + 60 + 24.99 + 389, 2))
    check('s257 X2 one side only: a Transfer with no arriving side stays as filed, unpaired; a loan payment is a debt payment',
          k[6]['kind'] == 'own_move' and k[6]['pair'] is None and k[12]['kind'] == 'debt_payment' and k[12]['pair'] is None)
    check('s257 X5 a refund nets against the purchase it reverses - the same payee\'s category, not Transfer',
          k[7]['category'] == 'Groceries')
    check('s257 X6 (a) cash is said as cash: neither spending nor a move', k[8]['kind'] == 'cash_out')
    check('s257 X7 a friend paid by Zelle is spending, even filed under Transfer', k[9]['kind'] == 'spending')
    check('s257 X8 the category is untouched: classify writes nothing', [(r.id, r.category_id) for r in rows] == before)
    lone = mk.classify([_row(1, D, 600.00, CHK, 'CHASE VISA PAYMENT', 11)], cats, ACCT, linked={1})
    check('s257 X2 a payment linked to a debt on record is a debt payment', lone[1]['kind'] == 'debt_payment')
    p7 = mk.classify([_row(1, D, 50.0, CHK, 'ZELLE TO MY PAYPAL', 12),
                      _row(2, D + timedelta(days=1), 50.0, 4, 'TRANSFER FROM BANK', 12, 'credit')], cats, ACCT)
    check('s257 X7 Zelle to the person\'s own account pairs: a move', p7[1]['kind'] == 'own_move' and p7[1]['pair'] == 2)

    # ── X3: confirmed once ────────────────────────────────────────────────────────────────────────────────────────
    said = mk.append([], rows[1], rows[2], 'yes')
    k2 = mk.classify(rows, cats, ACCT, said=said)
    said_no = mk.append([], rows[3], rows[4], 'no')
    k3 = mk.classify(rows, cats, ACCT, said=said_no)
    said_always = mk.append([], rows[1], rows[2], 'always')
    nxt = rows + [_row(20, D + timedelta(days=50), 600.00, CHK, 'CHASE VISA PAYMENT', 11),
                  _row(21, D + timedelta(days=51), 600.00, VISA, 'PAYMENT THANK YOU', 11, 'credit')]
    k4 = mk.classify(nxt, cats, ACCT, said=said_always)
    undone = mk.withdraw(said_always, 0)
    k5 = mk.classify(nxt, cats, ACCT, said=undone)
    check('s257 X3 a yes confirms the pair; until then it is counted as a move and marked not yet confirmed (a)',
          k[2]['kind'] == 'debt_payment' and k[2]['confirmed'] is False and k2[2]['confirmed'] is True)
    check('s257 X3 a no ends the pair: both rows count as filed', k3[4]['pair'] is None and k3[5]['pair'] is None
          and k3[4]['kind'] == 'own_move')
    check('s257 X3 "every time" stands for that pair of accounts and that payee, and Undo withdraws it (adds, removes nothing)',
          k4[20]['confirmed'] is True and k5[20]['confirmed'] is False and len(undone) == 2 and mk.standing(undone) == [])

    # ── X10: the null model - a household with no moves reads exactly as before ──────────────────────────────────
    rnd = random.Random(111)
    false_pairs = changed = 0
    for h in range(300):
        rs, n = [], 0
        for _ in range(rnd.randint(40, 90)):
            n += 1
            rs.append(_row(n, D + timedelta(days=rnd.randint(0, 89)), round(rnd.choice([rnd.uniform(5, 200), rnd.choice([25, 50, 100])]), 2),
                           rnd.choice([CHK, VISA]), 'STORE %d' % rnd.randint(1, 30), rnd.choice([10, 16])))
        for _ in range(rnd.randint(0, 6)):                                # store credits, filed where they were spent
            n += 1
            rs.append(_row(n, D + timedelta(days=rnd.randint(0, 89)), rnd.choice([25, 50, 100]), rnd.choice([CHK, VISA]),
                           'STORE %d' % rnd.randint(1, 30), rnd.choice([10, 16]), 'credit'))
        for w in range(0, 90, 14):
            n += 1
            rs.append(_row(n, D + timedelta(days=w), rnd.choice([100.0, 2150.0]), rnd.choice([CHK, SAV]), 'PAYROLL', 13, 'credit'))
        # X18: bills in the bank's payment words, each beside an unrelated deposit of the same amount (unfiled, or
        # filed Transfer) on another account within the three days - none is a move (X11)
        for _ in range(rnd.randint(1, 4)):
            day, amt = rnd.randint(0, 85), rnd.choice([100.0, 142.17, 89.5])
            n += 1
            rs.append(_row(n, D + timedelta(days=day), amt, CHK,
                           rnd.choice(['OHIO EDISON AUTOPAY', 'STATE FARM PAYMENT', 'AEP ELECTRIC EPAY']), rnd.choice([18, 19])))
            n += 1
            rs.append(_row(n, D + timedelta(days=day + rnd.randint(0, 3)), amt, SAV,
                           rnd.choice(['DEPOSIT', 'TRANSFER FROM CHECKING']), rnd.choice([None, 12]), 'credit'))
        kk = mk.classify(rs, cats, ACCT)
        false_pairs += sum(1 for v in kk.values() if v['pair'])
        # the store credits are refunds now (X5), so spending is the debits less the credits filed where they were spent
        old = round(sum(r.amount for r in rs if r.type == 'debit')
                    - sum(r.amount for r in rs if r.type == 'credit' and r.category_id in (10, 16)), 2)
        changed += mk.spending_of(rs, kk)[0] != old
    check(f's257 X10 X18 null model: 300 households with no moves, bills in payment words beside same-amount deposits - '
          f'no pair found, spending the debits less refunds ({false_pairs} pairs, {changed} changed)',
          false_pairs == 0 and changed == 0)

    # ── the reopening's cases (TRANSFERS.md 9.1), each its own check ──────────────────────────────────────────────
    def one(rs):
        return mk.classify(rs, cats, ACCT)

    k = one([_row(1, D, 100.0, CHK, 'OHIO EDISON AUTOPAY', 18), _row(2, D + timedelta(days=2), 100.0, SAV, 'DEPOSIT', None, 'credit')])
    check('s257 X11 a bill in the bank\'s payment words and an unrelated deposit are not a move - the bill stays spending',
          k[1]['kind'] == 'spending' and k[1]['pair'] is None and k[2]['pair'] is None)
    k = one([_row(1, D, 142.17, CHK, 'STATE FARM PAYMENT', 19),
             _row(2, D + timedelta(days=1), 142.17, SAV, 'TRANSFER FROM CHECKING', 12, 'credit')])
    check('s257 X11 a bill filed as spending never pairs with a deposit filed Transfer to a bank account',
          k[1]['kind'] == 'spending' and k[1]['pair'] is None)
    k = one([_row(1, D, 111.0, CHK, 'WITHDRAWAL ACH CAPITAL ONE', 16),
             _row(2, D + timedelta(days=1), 111.0, VISA, 'CAPITAL ONE MOBILE PYMT', None, 'credit')])
    check('s257 X11 filed as spending, a payment that reached a card and is called one there still pairs: a debt payment',
          k[1]['kind'] == 'debt_payment' and k[1]['pair'] == 2)
    k = one([_row(1, D, 25.0, CHK, 'KROGER #12', 10), _row(2, D + timedelta(days=1), 25.0, VISA, 'STORE CREDIT', None, 'credit')])
    check('s257 X11 reaching a card is not a sign by itself: a purchase and an unfiled card credit do not pair',
          k[1]['kind'] == 'spending' and k[1]['pair'] is None)
    k = one([_row(1, D, 0.0, CHK, 'TRANSFER TO SAVINGS', 12), _row(2, D, 0.0, SAV, 'TRANSFER', 12, 'credit')])
    check('s257 X16 a $0 row never pairs', k[1]['pair'] is None and k[2]['pair'] is None)
    rs = [_row(1, D, 50.0, VISA, 'KROGER #12', 10, merchant='Kroger'),
          _row(2, D + timedelta(days=3), 20.0, VISA, 'KROGER REFUND', 10, 'credit', 'Kroger'),
          _row(3, D + timedelta(days=20), 80.0, VISA, 'KROGER #12', 16, merchant='Kroger')]
    k = one(rs)
    check(f"s257 X12 a refund nets against the purchase before it, never a later one ({k[2]['category']})",
          k[2]['category'] == 'Groceries')
    k = one([_row(1, D, 20.0, VISA, 'KROGER REFUND', 10, 'credit', 'Kroger'),
             _row(2, D + timedelta(days=5), 80.0, VISA, 'KROGER #12', 16, merchant='Kroger')])
    check('s257 X12 with no purchase before it, a refund filed as spending nets where it was filed',
          k[1]['category'] == 'Groceries')
    k = one([_row(1, D, 30.0, VISA, 'TARGET REFUND', 12, 'credit', 'Target')])
    check('s257 X13 (a) a refund with no purchase, filed under Transfer, nets in Other', k[1]['kind'] == 'refund'
          and k[1]['category'] == 'Other')
    k = one([_row(1, D, 30.0, CHK, 'KROGER REFUND', 13, 'credit', 'Kroger')])
    check('s257 X14 unruled, as built: a refund filed under Income stays income', k[1]['kind'] == 'income')
    k = one([_row(1, D, 45.0, CHK, 'ZELLE TO SAM', 11)])
    check('s257 X15 (a) Zelle filed under Debt is a debt payment, as filed', k[1]['kind'] == 'debt_payment')
    rs = [_row(1, D, 300.0, CHK, 'TRANSFER TO SAVINGS', 12), _row(2, D + timedelta(days=1), 300.0, SAV, 'DEPOSIT', None, 'credit'),
          _row(3, D + timedelta(days=1), 300.0, VISA, 'PAYMENT THANK YOU', 11, 'credit')]
    k = one(rs)
    words = mk.sentence(rs[0], rs[1], {CHK: 'Checking', SAV: 'Savings', VISA: 'Visa'}, [rs[2]])
    check(f's257 X17 (b) the other row it could be is named in the question ({words})',
          k[1]['pair'] == 2 and k[1].get('others') == [3]
          and '$300.00 also reached Visa on Sep 2.' in words and words.endswith('Is this money moving between your accounts?'))
    k = one(rs[:2])
    check('s257 X17 one candidate: nothing else named', 'others' not in k[1])
    k = one([_row(1, D, 5000.0, CHK, 'TRANSFER TO SAVINGS', 12), _row(2, D, 5000.0, SAV, 'DEPOSIT', 13, 'credit')])
    fi = mk.filed_income_pairs([N(**vars(r)) for r in [_row(1, D, 5000.0, CHK, 'TRANSFER TO SAVINGS', 12),
                                                       _row(2, D, 5000.0, SAV, 'DEPOSIT', 13, 'credit')]],
                               mk.category_kinds(cats), ACCT)
    check('s257 X20 a deposit filed as income is never counted as a move; Ask why finds it by the same rule',
          k[2]['kind'] == 'income' and k[1]['pair'] is None and [(d.id, c.id) for d, c in fi] == [(1, 2)])
    pay = [_row(1, D, 2150.0, CHK, 'GROCERY OUTLET', 10), _row(2, D, 2150.0, SAV, 'ACME PAYROLL', 13, 'credit')]
    check('s257 X20 a purchase and a paycheck of the same amount are not asked about',
          mk.filed_income_pairs(pay, mk.category_kinds(cats), ACCT) == [])
    k = one([_row(1, D, 120.0, VISA, 'KROGER #12', 10), _row(2, D + timedelta(days=20), 120.0, CHK, 'CHASE VISA PAYMENT', 11),
             _row(3, D + timedelta(days=21), 120.0, VISA, 'PAYMENT THANK YOU', 11, 'credit'),
             _row(4, D + timedelta(days=22), 389.0, CHK, 'RIVERSIDE AUTO LOAN PMT', 11),
             _row(5, D + timedelta(days=23), 300.0, CHK, 'TRANSFER TO SAVINGS', 12),
             _row(6, D + timedelta(days=23), 300.0, SAV, 'TRANSFER FROM CHECKING', 12, 'credit'),
             _row(7, D + timedelta(days=24), 60.0, CHK, 'ATM WITHDRAWAL', 12)])
    out_ids = [i for i in range(1, 8) if mk.money_out(N(id=i, type='credit' if i in (3, 6) else 'debit'), k)]
    check(f's257 X19 money out: the purchase, the loan and the cash - not the card payment (its purchases counted) nor '
          f'the move ({out_ids})', out_ids == [1, 4, 7])

    # ── X1: no second definition anywhere ─────────────────────────────────────────────────────────────────────────
    root = ctx.BASE
    py = {p.name: p.read_text(encoding='utf-8') for p in [root / 'server.py'] + sorted((root / 'core').glob('*.py'))
          if p.name != 'money_kind.py'}
    app = ctx.app_src
    hits = [n for n, s in py.items() for pat in ('NOT_SPENDING_WORDS', '_LESSON_EXCLUDED_CATEGORIES', 'NOT_PRICES =',
                                                   'def _transfer_ids', 'PAYMENT_NAMES')
            if pat in s]
    lists = [n for n, s in py.items() for lit in re.findall(r'[\{\(\[][^\{\}\(\)\[\]]*[\}\)\]]', s)
             if "'transfer'" in lit.lower() and ("'savings'" in lit.lower() or "'debt'" in lit.lower())]
    js = [pat for pat in ("t.category !== 'Transfer'", "t.category!=='Transfer'", "t.category === 'Transfer'",
                          "t.category === 'Debt'", 'function _isTransferCat') if pat in app]
    named = [f'{n}:{m.group(0)}' for n, s in py.items()
             for m in re.finditer(r"(?<!func)\.lower\(\)\s*[!=]=\s*'transfer'", s)]
    check(f's257 X1 X20 no second definition: no word list, transfer test or Transfer check outside money_kind '
          f'({hits}, {lists}, {js}, {named})', not hits and not lists and not js and not named)
    # X19: the readers the reopening named each read the one kind
    srv = py['server.py']
    readers = ('_willingness_inputs', 'reallocation_candidates', '_futures_inputs', '_bills_ctx', '_price_changes',
               '_yearly_steps', '_first_import_findings', '_category_months')
    body = {f: (re.search(r'\ndef ' + f + r'\(.*?(?=\n(?:def |@|class )\S)', srv, re.S) or [''])[0] for f in readers}
    off = [f for f, b in body.items() if 'money_kind.' not in b or "== 'transfer'" in b or '_transfer_category_ids' in b]
    check(f's257 X19 each reader the reopening named reads the one kind, never a Transfer category ({off})', not off)

    check('s257 X1 the page reads the kind from the server and decides nothing itself',
          "function _kind(t)" in app and "return (t && t.kind) || 'unknown'" in app and '/api/transactions/kinds' in app)

    # ── the routes, on this database ──────────────────────────────────────────────────────────────────────────────
    c, H, HJ = ctx.c, ctx.H, ctx.HJ
    from core.database import Account, Category, Transaction, db_session
    today = date.today()
    with db_session() as s:
        cid = {x.name: x.id for x in s.query(Category).all()}
        a1 = Account(name='s257 Checking', type='checking'); a2 = Account(name='s257 Visa', type='credit')
        s.add_all([a1, a2]); s.flush()
        last = today.replace(day=1) - timedelta(days=3)
        made = [Transaction(date=today, description='S257 MARKET', merchant='S257 Market', amount=80.0, type='debit',
                            account_id=a2.id, category_id=cid.get('Groceries')),
                Transaction(date=last, description='S257 MARKET', merchant='S257 Market', amount=40.0, type='debit',
                            account_id=a2.id, category_id=cid.get('Groceries')),
                Transaction(date=last, description='WITHDRAWAL ACH S257 VISA', amount=571.0, type='debit',
                            account_id=a1.id, category_id=cid.get('Groceries')),
                Transaction(date=last, description='S257 VISA MOBILE PYMT', amount=571.0, type='credit',
                            account_id=a2.id, category_id=None),
                Transaction(date=today, description='S257 VISA PAYMENT', amount=257.0, type='debit', account_id=a1.id,
                            category_id=cid.get('Debt')),
                Transaction(date=today, description='PAYMENT THANK YOU', amount=257.0, type='credit', account_id=a2.id,
                            category_id=cid.get('Debt'))]
        s.add_all(made); s.flush()
        ids = [t.id for t in made]
        cats_before = [t.category_id for t in made]
        s.commit()
    pay_ids, ids = ids[1:4], ids[:1] + ids[4:]                 # X19's rows; the X1-X3 checks below read the rest
    cats_before = cats_before[:1] + cats_before[4:]
    try:
        from server import _category_months
        with db_session() as s:
            _held, seen = _category_months(s, 'Groceries')
            pk = mk.kinds(s)
            m0 = last.replace(day=1)
            raw = s.query(Transaction).filter(Transaction.category_id == cid.get('Groceries'), Transaction.type == 'debit',
                                              Transaction.date >= m0, Transaction.date < today.replace(day=1)).all()
            want = round(sum(t.amount for t in raw if pk[t.id]['kind'] == 'spending'), 2)
        lm = last.strftime('%Y-%m')
        check(f"s257 X19 a card payment filed under Groceries is not Groceries' spending ({seen.get(lm)} = {want}, "
              f"{pk[pay_ids[1]]['kind']})", pk[pay_ids[1]]['kind'] == 'debt_payment'
              and any(t.id == pay_ids[1] for t in raw) and seen.get(lm) == want)
        tx = c.get('/api/transactions?per_page=5000', headers=H).get_json()['data']
        mine = {t['id']: t for t in tx if t['id'] in ids}
        check('s257 X1 every row carries its kind to the page', all(mine[i].get('kind') for i in ids)
              and mine[ids[1]]['kind'] == 'debt_payment' and mine[ids[1]]['pair_id'] == ids[2]
              and mine[ids[1]]['pair_confirmed'] is False)
        kinds_route = c.get('/api/transactions/kinds', headers=H).get_json()['data']
        check('s257 X1 the kinds route answers for every row', all(str(i) in kinds_route for i in ids))
        ask = c.get('/api/own-moves', headers=H).get_json()['data']['attention']
        mine_ask = [x for x in ask if x['pair'] == f'{ids[1]}>{ids[2]}']
        check(f"s257 X3 Needs attention asks, in the fixed words ({mine_ask and mine_ask[0]['sentence']})",
              len(mine_ask) == 1 and mine_ask[0]['sentence'].startswith('$257.00 left s257 Checking on ')
              and mine_ask[0]['sentence'].endswith('Is this money moving between your accounts?'))
        bad = c.post('/api/own-moves/answer', headers=HJ, data=json.dumps({'pair': f'{ids[1]}>{ids[2]}', 'answer': 'maybe'}))
        c.patch('/api/settings', headers=HJ, data=json.dumps({mk.SETTING: '[{"answer": "always"}]'}))
        r = c.post('/api/own-moves/answer', headers=HJ, data=json.dumps({'pair': f'{ids[1]}>{ids[2]}', 'answer': 'always'}))
        after = c.get('/api/own-moves', headers=H).get_json()['data']
        check(f's257 X3 an answer is kept as the person\'s statement, asked once, listed for Settings; the settings route can\'t '
              f'write over it ({bad.status_code}, {r.status_code})',
              bad.status_code == 400 and r.status_code == 200
              and not [x for x in after['attention'] if x['pair'] == f'{ids[1]}>{ids[2]}']
              and any(x['from'] == 's257 Checking' and x['to'] == 's257 Visa' for x in after['standing']))
        with db_session() as s:
            check('s257 X8 nothing re-filed: the categories are as filed', [s.get(Transaction, i).category_id for i in ids] == cats_before)
        # every page's spending equal to one total: the server's, the check-in's and the page's own sum
        from core import checkin
        with db_session() as s:
            rows = s.query(Transaction).filter(Transaction.date >= today.replace(day=1), Transaction.date <= today).all()
            server_total = mk.spending_of(rows, mk.kinds(s))[0]
            checkin_total = checkin.facts(s, today=today)['month']['spent']
        src = ctx.app_src
        js = (_fn(src, '_kind') + _fn(src, '_spendAmt')
              + 'const rows = %s; const m0 = %s; const t1 = %s;\n' % (json.dumps(tx), json.dumps(today.replace(day=1).isoformat()), json.dumps(today.isoformat()))
              + 'console.log(rows.filter(t => t.date >= m0 && t.date <= t1).reduce((s, t) => s + _spendAmt(t), 0).toFixed(2));')
        jsf = ctx.TMP / 's257_total.js'                   # a file: the whole ledger is too long for a command line
        jsf.write_text(js, encoding='utf-8')
        out = subprocess.run(['node', str(jsf)], capture_output=True, text=True)
        page_total = float(out.stdout.strip() or 'nan')
        check(f's257 X1 every page\'s spending is one total: server {server_total}, check-in {checkin_total}, page {page_total}',
              round(server_total, 2) == round(checkin_total, 2) == round(page_total, 2))
    finally:
        with db_session() as s:
            for i in ids + pay_ids:
                t = s.get(Transaction, i)
                if t:
                    s.delete(t)
            s.commit()
        c.patch('/api/settings', headers=HJ, data=json.dumps({}))

    # ── X9: the Morgans, filed like an import ─────────────────────────────────────────────────────────────────────
    sh = (root / 'core' / 'sample_household.py').read_text(encoding='utf-8')
    check('s257 X9 the Morgans file card and loan payments under Debt, with the card\'s payment thank you and one refund',
          "debt_pay = cat('Debt'" in sh and "'PAYMENT THANK YOU'" in sh and "'PARCELMART REFUND'" in sh)
