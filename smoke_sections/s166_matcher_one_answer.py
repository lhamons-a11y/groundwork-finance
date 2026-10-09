"""One purchase, one category, whichever way it arrives (gw 2.0/MATCHER_ONE_ANSWER.md, item 54; Rob 2026-10-09:
"approve M1-M7 as recommended").

    M1  the page's rules are the server's rules: same words, same leaf, same order
    M2  every rule names a leaf, never a parent; words naming more than one service name Other (no guess)
    M3  the words of both old copies are kept
    M4  a refund is a Transfer          M5  a tax payment or refund has no tax leaf to go to: Other
    M6  rows saved under an old answer are offered with their amounts, and move only on a yes
The descriptions below are written to look like bank lines; they are not taken from real statements.
"""
import json
import re
import shutil
import subprocess

EXPECT = {
    'AEP OHIO BILL PAY': 'Electric', 'OHIO EDISON 12': 'Electric', 'DOMINION ENERGY GAS': 'Gas', 'COLUMBIA GAS OF OHIO': 'Gas',
    'ENBRIDGE GAS 44': 'Gas', 'CITY WATER DEPT': 'Water / Sewer', 'RUMPKE TRASH PICKUP': 'Trash',
    'DUKE ENERGY 1234': 'Other', 'DOMINION ENERGY 123': 'Other', 'NATIONAL GRID 7': 'Other', 'PGE WEB PAY': 'Other',
    'CITY UTILITY BILL': 'Municipal Utilities',   # item 56 U4: a city's utility bill
    'GEICO AUTO': 'Auto Insurance', 'STATE FARM 1234': 'Auto Insurance', 'ANTHEM INSURANCE': 'Other',
    'UBER TRIP 123': 'Rideshare / Transit', 'LYFT RIDE': 'Rideshare / Transit', 'AMTRAK 44': 'Rideshare / Transit',
    'CITY PARKING 9': 'Parking / Tolls', 'OHIO TURNPIKE TOLL': 'Parking / Tolls', 'UBER EATS 1': 'Fast Food / Takeout',
    'JOES DINER': 'Restaurants', 'MAIN ST GRILL': 'Restaurants',
    'CVS/PHARMACY 123': 'Prescriptions', 'WALGREENS 99': 'Prescriptions', 'DENTAL CLINIC 3': 'Dental',
    'MILLBROOK VISION CENTER': 'Vision', 'MERCY HOSPITAL': 'Doctor / Co-pays',
    'CHATGPT SUBSCR': 'Software / Apps', 'APPLE.COM/BILL': 'Software / Apps', 'NYTIMES DIGITAL': 'Other Subscriptions',
    'CINEMARK 12': 'Activities / Events', 'OSU TUITION': 'Tuition / Courses', 'MAIN DRY CLEANER': 'Personal Care',
    'AMAZON REFUND': 'Transfer', 'MERCHANDISE RETURN': 'Transfer',
    'IRS PAYMENT': 'Other', 'IRS TREAS 310 TAX REF': 'Other', 'STATE TAX OH': 'Other',
    'ACME PAYROLL': 'Paycheck / Salary', 'DIRECT DEPOSIT ACME': 'Paycheck / Salary',
    'FINANCE CHARGE': 'Interest / Fees', 'RULER FOODS 12': 'Groceries', 'FLYING FUR PETS': 'Pet Food / Supplies',
}


def _fn(src, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', src, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, HJ, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.app_src
    import bank_importer as bi
    from core.database import CATEGORY_TREE, Category, Transaction, Account, db_session

    names = {r[0] for r in CATEGORY_TREE}
    parents = {r[4] for r in CATEGORY_TREE if r[4]}
    py = [(p, cat) for cat, p in bi._CATEGORY_PATTERNS]
    client = _fn(app, 'clientAutoCategory')
    js = re.findall(r"\n  if \(/(.*?)/\.test\(d\)\) return '([^']+)';", client)
    check(f's166 M1 the page carries the server\'s rules exactly - same words, same leaf, same order ({len(py)} rules)',
          js == py and len(py) > 30)
    cats = {cat for _, cat in py}
    check('s166 M2 every rule names a real category, and none names a parent',
          sorted(cats - names) == [] and sorted(cats & parents) == [])

    got = {d: bi.auto_category(d) for d in EXPECT}
    wrong = {d: (got[d], want) for d, want in EXPECT.items() if got[d] != want}
    check(f's166 M2-M5 the server files each line where the ruling says ({len(EXPECT)} lines){" - wrong: " + json.dumps(wrong) if wrong else ""}',
          wrong == {})
    with db_session() as s:
        pay = s.query(Category).filter(Category.name == 'Paycheck / Salary').first()
        pay_type = pay.type if pay else None
    check('s166 M2 a paycheck goes to Paycheck / Salary, which is an income category (income is found by type)', pay_type == 'income')

    node = shutil.which('node')
    if node and client:
        p = subprocess.run([node, '-e', client + 'const L = ' + json.dumps(list(EXPECT)) +
                            ';\nconsole.log(JSON.stringify(Object.fromEntries(L.map(d => [d, clientAutoCategory(d)]))));'],
                           capture_output=True, text=True, encoding='utf-8', timeout=60)
        page = json.loads(p.stdout.strip() or '{}') if p.returncode == 0 else {}
        diff = {d: (page.get(d), got[d]) for d in EXPECT if page.get(d) != got[d]}
        check(f's166 M1 the page files every line the same way as the server{" - differs: " + json.dumps(diff) if diff else ""}', diff == {})

    # M6: rows saved under the old answers
    made_t, made_a = [], []
    try:
        from datetime import date
        with db_session() as s:
            cid = {cc.name: cc.id for cc in s.query(Category).all()}
            a = Account(name='s166 Checking', type='checking', is_active=True)
            s.add(a); s.flush()
            spec = [('AEP OHIO BILL PAY S166', 'Utilities', 121.40), ('UBER TRIP S166', 'Gas / Fuel', 18.25),
                    ('JOES DINER S166', 'Groceries', 34.10), ('GEICO AUTO S166', 'Health Insurance', 96.00),
                    ('KROGER #234 S166', 'Groceries', 88.00), ('IRS PAYMENT S166', 'Interest / Fees', 400.00)]
            rows = [Transaction(date=date.today(), description=d, amount=amt, type='debit', account_id=a.id, category_id=cid[cat])
                    for d, cat, amt in spec]
            s.add_all(rows); s.commit()
            made_a.append(a.id); made_t += [r.id for r in rows]
        aep, uber, diner, geico, kroger, irs = made_t
        rv = c.get('/api/categories/label-review', headers=H).get_json()['data']
        offered = {}
        for gp in rv.get('regroup') or []:
            for x in gp['rows']:
                if 'S166' in x['description']:
                    offered[x['id']] = (gp['from'], gp['to'], x['amount'])
        check('s166 M6 the review offers each row saved under an old answer, from -> to, with its amount',
              offered == {aep: ('Utilities', 'Electric', 121.40), uber: ('Gas / Fuel', 'Rideshare / Transit', 18.25),
                          diner: ('Groceries', 'Restaurants', 34.10), geico: ('Health Insurance', 'Auto Insurance', 96.00)})
        check('s166 M6 a row the rules agree with (Kroger in Groceries) and a row with no leaf to go to (a tax payment) are not offered',
              kroger not in offered and irs not in offered)
        with db_session() as s:
            before = {i: s.get(Transaction, i).category_id for i in made_t}
        check('s166 M6 looking moves nothing', before[aep] == cid['Utilities'] and before[uber] == cid['Gas / Fuel'])
        mv = c.post('/api/categories/label-review/move', headers=HJ, data=json.dumps({'ids': [aep, uber, kroger, irs]})).get_json()['data']
        with db_session() as s:
            after = {i: s.get(Transaction, i).category_id for i in made_t}
        check('s166 M6 only the rows said yes to move, each to its offered leaf; rows the review did not offer cannot move',
              mv['moved'] == 2 and after[aep] == cid['Electric'] and after[uber] == cid['Rideshare / Transit']
              and after[diner] == cid['Groceries'] and after[geico] == cid['Health Insurance']
              and after[kroger] == cid['Groceries'] and after[irs] == cid['Interest / Fees'])
        if node:
            jsr = _fn(app, '_labelReviewFuelBlock') + _fn(app, 'labelReviewHTML') + r'''
const esc = s => String(s), fmt = n => '$' + Number(n).toFixed(2), fmtDate = s => s;
console.log(JSON.stringify(labelReviewHTML({fuel: null, fuel_groceries: null, fitness: null,
  regroup: [{from: 'Utilities', to: 'Electric', count: 1, total: 121.40, rows: [{id: 5, date: '2026-10-01', description: 'AEP OHIO', amount: 121.40}]}]})));'''
            p = subprocess.run([node, '-e', jsr], capture_output=True, text=True, encoding='utf-8', timeout=60)
            html = json.loads(p.stdout.strip() or '""')
            check('s166 M6 the page asks: 1 purchase in Utilities would now be filed under Electric, with its amount and a choice',
                  '1 purchase in <strong>Utilities</strong> would now be filed under <strong>Electric</strong> — $121.40 in all. Move it?' in html
                  and "labelReviewMove('rg0', true)" in html and 'Leave them' in html and 'nothing moves unless you say so' in html)
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.id.in_(made_t)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made_a)).delete(synchronize_session=False)
            s.commit()
