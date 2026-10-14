"""Item 85 (gw 2.0/CARD_CODES_HOME.md; Rob 2026-10-13: "yes" - fix it the same way, rows offered with a yes).

    H1  home-store codes name home leaves, not Rent / Mortgage (every Lowe's purchase read as a housing payment)
    H2  general-merchandise codes name no leaf (item 55 C3) - the store's name decides; Amazon's 5942 too
    H3  general retailers are Shopping (a leaf now, under Personal); clothing stores stay Clothing
    H4  "Withdrawal" alone is not a transfer: Rob's bank starts every debit with it, and purchases left spending
    H5  rows the corrected rules file differently are offered in the review, moved only on a yes - never to Transfer
"""


def run(ctx):
    check = ctx.check
    import bank_importer as bi
    from core.database import CATEGORY_TREE
    app = ctx.app_src
    m = bi.MCC_CATEGORY_MAP
    check('s225 H1 home-store codes name home leaves',
          m['5200'] == 'Home Improvement' and m['5211'] == 'Home Improvement' and m['5251'] == 'Home Maintenance'
          and m['5712'] == 'Furniture / Decor' and m['5713'] == 'Home Improvement' and m['5722'] == 'Home Improvement'
          and 'Rent / Mortgage' not in m.values())
    check('s225 H2 general-merchandise codes, electronics and Amazon\'s 5942 name no leaf; gift shops are Gifts',
          all(m[c] == 'Other' for c in ('5310', '5311', '5331', '5399', '5999', '5969', '5932', '5732', '5942'))
          and m['5947'] == 'Gifts' and set(v for k, v in m.items() if v == 'Clothing') == {'Clothing'}
          and all(m[c] == 'Clothing' for c in ('5621', '5651', '5661', '5691')))
    a = lambda d, c='': bi.auto_category(d, c)
    W = 'Withdrawal CHECK CARD TRAN '
    check('s225 H3/H4 the name decides: general retailers Shopping, clothing stores Clothing, a bank\'s "Withdrawal" prefix no transfer',
          a(W + 'DOLLAR TREE MILLBROOK OH', '5331') == 'Shopping' and a(W + 'HARBOR FREIGHT', '5999') == 'Shopping'
          and a(W + 'TEMU.COM', '5311') == 'Shopping' and a(W + 'TJ MAXX', '5310') == 'Clothing'
          and a(W + 'KOHLS', '5651') == 'Clothing' and a(W + "LOWE'S #1234", '5200') == 'Home Improvement'
          and a('Withdrawal ACH AEP OHIO POWER R TYPE: BILL PAY') == 'Electric')
    check('s225 H4 a real move of money is still a transfer',
          a('ATM WITHDRAWAL 123 MAIN ST') == 'Transfer' and a('Withdrawal ATM EFT MILLBROOK') == 'Transfer'
          and a('Withdrawal Transfer to savings') == 'Transfer' and a('ZELLE TO SAM') == 'Transfer')
    check("s225 H3 Shopping is a leaf under Personal in a new database's tree, and the page's matcher agrees",
          ('Shopping', 'Personal') in {(t[0], t[4]) for t in CATEGORY_TREE} and "return 'Shopping';" in app
          and "'5331': 'Other'" in app and '\\bwithdrawal\\b|' not in app)
    src = ctx.server_src.split('def _regroup_review(session):')[1].split('\n@')[0]
    check('s225 H5 the review offers rows the corrected rules file differently - to a real leaf, never Other - and moves nothing itself',
          "Transaction.mcc.in_(list(fixed))" in src and "('Clothing', 'Rent / Mortgage')" in src
          and "to not in ('Other', src)" in src and 'session.commit' not in src)
