"""Item 111 (gw 2.0/TRANSFERS.md; Rob 2026-10-26: "build item 111" - X1-X10 as recommended): money moving between
the person's own accounts. One kind per row, in one place (core/money_kind.py), read everywhere.

    X1  one definition      X2  a move is a pair; one side only stays as filed     X3  confirmed once, (a) counted
    X4  paying a card is not spending      X5  a refund nets in its category       X6  cash said as cash (a)
    X7  Venmo / Zelle are spending unless they pair      X8  the category stays the person's
    X9  the Morgans filed like an import      X10 the null model: no moves, no change
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
        16: ('Shopping', 'expense', None), 17: ('Savings', 'expense', None)}
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
        kk = mk.classify(rs, cats, ACCT)
        false_pairs += sum(1 for v in kk.values() if v['pair'])
        old = round(sum(r.amount for r in rs if r.type == 'debit'), 2)
        changed += mk.spending_of([r for r in rs if r.type == 'debit'], kk)[0] != old
    check(f's257 X10 null model: 300 households with no moves - no pair found, spending unchanged ({false_pairs} pairs, {changed} changed)',
          false_pairs == 0 and changed == 0)

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
    check(f's257 X1 no second definition: no word list, transfer test or Transfer check outside money_kind ({hits}, {lists}, {js})',
          not hits and not lists and not js)
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
        made = [Transaction(date=today, description='S257 MARKET', merchant='S257 Market', amount=80.0, type='debit',
                            account_id=a2.id, category_id=cid.get('Groceries')),
                Transaction(date=today, description='S257 VISA PAYMENT', amount=257.0, type='debit', account_id=a1.id,
                            category_id=cid.get('Debt')),
                Transaction(date=today, description='PAYMENT THANK YOU', amount=257.0, type='credit', account_id=a2.id,
                            category_id=cid.get('Debt'))]
        s.add_all(made); s.flush()
        ids = [t.id for t in made]
        cats_before = [t.category_id for t in made]
        s.commit()
    try:
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
            for i in ids:
                t = s.get(Transaction, i)
                if t:
                    s.delete(t)
            s.commit()
        c.patch('/api/settings', headers=HJ, data=json.dumps({}))

    # ── X9: the Morgans, filed like an import ─────────────────────────────────────────────────────────────────────
    sh = (root / 'core' / 'sample_household.py').read_text(encoding='utf-8')
    check('s257 X9 the Morgans file card and loan payments under Debt, with the card\'s payment thank you and one refund',
          "debt_pay = cat('Debt'" in sh and "'PAYMENT THANK YOU'" in sh and "'PARCELMART REFUND'" in sh)
