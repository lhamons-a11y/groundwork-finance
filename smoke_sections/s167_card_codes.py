"""The card codes name the same categories as the words (gw 2.0/CARD_CODES.md, item 55; Rob 2026-10-09: "approve
C1-C6 as recommended").

    C1  the page's code table is the server's: the same codes, the same categories
    C2  every code names a leaf, never a parent        C3  a code covering more than one thing, or with no leaf, names Other
    C4  a code naming a leaf wins; a code naming Other lets the words decide (on both sides)
    C5  rows saved under an old code answer are offered in item 54's review, moved only on a yes
"""
import json
import re
import shutil
import subprocess

LEAF = {'5552': 'Gas / Fuel', '4121': 'Rideshare / Transit', '7523': 'Parking / Tolls', '5912': 'Prescriptions',
        '8021': 'Dental', '8042': 'Vision', '8062': 'Doctor / Co-pays', '5818': 'Software / Apps',
        '5968': 'Other Subscriptions', '5651': 'Clothing', '7832': 'Activities / Events', '8211': 'School / Tuition',
        '8220': 'Tuition / Courses', '8351': 'Childcare / Daycare'}
NO_GUESS = ('4900', '4901', '5960', '6300', '6381', '4816', '8999', '5921', '9311')
# C4: (description, code) -> expected. The code wins when it names a leaf; when it names Other, the words decide.
CASES = [('AEP OHIO 123', '4900', 'Electric'), ('DOMINION ENERGY GAS', '4900', 'Gas'), ('CITY OF MILLBROOK', '4900', 'Other'),
         ('GEICO AUTO', '6300', 'Auto Insurance'), ('ANTHEM', '6300', 'Other'), ('KIDS CARE CENTER', '8351', 'Childcare / Daycare'),
         ('SHELL OIL 5744', '5541', 'Gas / Fuel'), ('UBER TRIP', '5541', 'Gas / Fuel'), ('ACME', '9311', 'Other')]


def _fn(src, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', src, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, HJ, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.app_src
    import bank_importer as bi
    from core.database import CATEGORY_TREE, Category, Transaction, Account, db_session

    names = {r[0] for r in CATEGORY_TREE}
    parents = {r[4] for r in CATEGORY_TREE if r[4]}
    sm = bi.MCC_CATEGORY_MAP
    m = re.search(r"\nconst CLIENT_MCC_CATEGORY_MAP = \{(.*?)\n\};", app, re.S)
    cm = dict(re.findall(r"'(\d+)': '([^']+)'", m.group(1))) if m else {}
    check(f's167 C1 the page\'s code table is the server\'s - the same {len(sm)} codes, the same categories', cm == sm and len(sm) > 100)
    vals = set(sm.values())
    check('s167 C2 every code names a real category, and none names a parent', sorted(vals - names) == [] and sorted(vals & parents) == [])
    check('s167 C2 the codes name the leaves the ruling gives', {k: sm[k] for k in LEAF} == LEAF)
    check('s167 C3 a code covering more than one thing, or with no leaf, names Other', all(sm[k] == 'Other' for k in NO_GUESS))
    got = [(d, k, bi.auto_category(d, k)) for d, k, _ in CASES]
    check('s167 C4 a code naming a leaf wins; a code naming Other lets the words decide (server)',
          [g[2] for g in got] == [w for _, _, w in CASES])

    node = shutil.which('node')
    if node and m:
        js = (app[app.index('\nconst CLIENT_MCC_CATEGORY_MAP = {'):app.index('\n};', app.index('\nconst CLIENT_MCC_CATEGORY_MAP = {')) + 4]
              + _fn(app, 'clientAutoCategory') + _fn(app, 'clientCategorize')
              + 'const L = ' + json.dumps([[d, k] for d, k, _ in CASES]) + ';\nconsole.log(JSON.stringify(L.map(([d, k]) => clientCategorize(d, k))));')
        p = subprocess.run([node, '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=60)
        page = json.loads(p.stdout.strip() or '[]') if p.returncode == 0 else []
        check('s167 C4 the page decides the same way', page == [w for _, _, w in CASES])

    # C5: a row saved under an old code answer is offered in the review
    made_t, made_a = [], []
    try:
        from datetime import date
        with db_session() as s:
            cid = {cc.name: cc.id for cc in s.query(Category).all()}
            a = Account(name='s167 Checking', type='checking', is_active=True)
            s.add(a); s.flush()
            rows = [Transaction(date=date.today(), description='LITTLE STARS S167', mcc='8351', amount=210.0, type='debit', account_id=a.id, category_id=cid['Tuition / Courses']),
                    Transaction(date=date.today(), description='OLD NAVY S167', mcc='5651', amount=44.0, type='debit', account_id=a.id, category_id=cid['Personal Care']),
                    Transaction(date=date.today(), description='CITY OF MILLBROOK S167', mcc='4900', amount=61.0, type='debit', account_id=a.id, category_id=cid['Utilities'])]
            s.add_all(rows); s.commit()
            made_a.append(a.id); made_t += [r.id for r in rows]
        care, navy, millbrook = made_t
        rv = c.get('/api/categories/label-review', headers=H).get_json()['data']
        offered = {x['id']: (gp['from'], gp['to']) for gp in rv.get('regroup') or [] for x in gp['rows'] if 'S167' in x['description']}
        check('s167 C5 child care filed as tuition and clothing filed as Personal Care are offered; a code-4900 row with no leaf is not',
              offered == {care: ('Tuition / Courses', 'Childcare / Daycare'), navy: ('Personal Care', 'Clothing')})
        mv = c.post('/api/categories/label-review/move', headers=HJ, data=json.dumps({'ids': [care, millbrook]})).get_json()['data']
        with db_session() as s:
            after = {i: s.get(Transaction, i).category_id for i in made_t}
        check('s167 C5 only the row said yes to moves', mv['moved'] == 1 and after == {care: cid['Childcare / Daycare'],
              navy: cid['Personal Care'], millbrook: cid['Utilities']})
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.id.in_(made_t)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made_a)).delete(synchronize_session=False)
            s.commit()
