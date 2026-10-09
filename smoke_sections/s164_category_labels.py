"""Imported purchases land in the right category (gw 2.0/CATEGORY_LABELS.md, item 52; Rob 2026-10-09: "approve L1-L7
as recommended").

    L1  fuel is Gas / Fuel (Transportation), never Gas (the natural-gas utility); gyms are Gym / Fitness
    L3  every name an importer can return is a real category in the tree - the drift can't come back silently
    L4  re-categorising never creates a category: a name the user's categories don't hold leaves the row as it is
    L2  (master) every Apple Card name is a real category; Apple's Gas is Gas / Fuel
    L5  (master) rows already saved under the old names are offered with their amounts, and move only on a yes
"""
import json
import re
import shutil
import subprocess


def _fn(src, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', src, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, HJ, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.app_src
    import bank_importer as bi
    from core.database import CATEGORY_TREE, Category, Transaction, Account, BudgetItem, db_session
    tree = {r[0] for r in CATEGORY_TREE}

    # L1
    got = {d: bi.auto_category(d) for d in ('SHELL OIL 57444', 'CLARK GAS 12', 'MEIJER FUEL 0042', 'PLANET FITNESS 33')}
    check('s164 L1 fill-ups are Gas / Fuel and gyms are Gym / Fitness',
          got == {'SHELL OIL 57444': 'Gas / Fuel', 'CLARK GAS 12': 'Gas / Fuel', 'MEIJER FUEL 0042': 'Gas / Fuel',
                  'PLANET FITNESS 33': 'Gym / Fitness'})
    check('s164 L1 the fuel-station and fitness card codes follow',
          [bi.auto_category('X', m) for m in ('5541', '5542', '5172', '7997')] == ['Gas / Fuel'] * 3 + ['Gym / Fitness'])
    check('s164 L1 natural-gas bills never go to fuel (item 54: a gas company is the Gas leaf; item 55: code 4900 names no guess)',
          bi.auto_category('DOMINION ENERGY GAS') != 'Gas / Fuel' and bi.auto_category('COLUMBIA GAS OF OHIO') != 'Gas / Fuel'
          and bi.auto_category('X', '4900') == 'Other')
    tree_gas = [r for r in CATEGORY_TREE if r[0] in ('Gas', 'Gas / Fuel')]
    check('s164 L1 the tree is unchanged: Gas is the utility leaf, Gas / Fuel the Transportation leaf',
          sorted((r[0], r[4]) for r in tree_gas) == [('Gas', 'Utilities'), ('Gas / Fuel', 'Transportation')])

    # L3 - every name the importers can return
    pats = {p[0] for p in bi._CATEGORY_PATTERNS}
    mcc = set(bi.MCC_CATEGORY_MAP.values())
    check('s164 L3 every importer pattern names a real category', sorted(pats - tree) == [])
    check('s164 L3 every card-code target names a real category', sorted(mcc - tree) == [])
    client = _fn(app, 'clientAutoCategory')
    client_names = set(re.findall(r"return '([^']+)'", client))
    check('s164 L3 every name the page\'s own matcher returns is a real category',
          client_names and sorted(client_names - tree) == [])
    m = re.search(r"\n(?:const|let|var) (\w*MCC\w*)\s*=\s*\{(.*?)\n\};", app, re.S)
    client_mcc = set(re.findall(r":\s*'([^']+)'", m.group(2))) if m else set()
    check('s164 L3 every card-code target in the page is a real category', client_mcc and sorted(client_mcc - tree) == [])
    apple = _fn(app, '_mapAppleCardCategory')
    # L7: the Apple Card map is fixed on master only (2.0 carries the utility estimates; 1.x does not)
    if (ctx.BASE / 'core/utility_estimate.py').exists():
        apple_names = set(re.findall(r"return '([^']+)'", apple)) | set(re.findall(r"\|\| '([^']+)'", apple))
        check('s164 L2/L3 every name the Apple Card import returns is a real category, and fuel is Gas / Fuel',
              apple_names and sorted(apple_names - tree) == [] and "case 'gas':               return 'Gas / Fuel'" in apple)

    # L4 - the smart backfill never mints a category. The route reloads bank_importer, so the case is built in the
    # data: the user's categories don't hold the name the matcher returns (Gym / Fitness renamed for the check).
    made_t, made_a, renamed = [], [], None
    try:
        from datetime import date
        with db_session() as s:
            other_id = s.query(Category).filter(Category.name.ilike('other')).first().id
            gym = s.query(Category).filter(Category.name == 'Gym / Fitness').first()
            if gym:
                gym.name = 'S164 Gym (renamed)'
                renamed = gym.id
            a = Account(name='s164 Checking', type='checking', is_active=True)
            s.add(a); s.flush()
            t = Transaction(date=date.today(), description='PLANET FITNESS S164', amount=9.0, type='debit',
                            account_id=a.id, category_id=other_id)
            s.add(t); s.commit()
            made_t.append(t.id); made_a.append(a.id)
            before = s.query(Category).count()
        r = c.post('/api/categories/smart-backfill', headers=HJ, data=json.dumps({'dry_run': False}))
        with db_session() as s:
            after = s.query(Category).count()
            row_cat = s.get(Transaction, made_t[0]).category_id
            ghosts = s.query(Category).filter(Category.name.in_(('Fitness', 'Gym / Fitness'))).count()
        check("s164 L4 re-categorising leaves a row whose name the user's categories don't hold as it is, and creates nothing",
              r.status_code == 200 and after == before and ghosts == 0 and row_cat == other_id)
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.id.in_(made_t)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made_a)).delete(synchronize_session=False)
            s.query(Category).filter(Category.name.in_(('Fitness',)), Category.is_system == False).delete(synchronize_session=False)  # noqa: E712
            s.query(Category).filter(Category.name == 'Gym / Fitness', Category.id != renamed).delete(synchronize_session=False)
            if renamed:
                s.get(Category, renamed).name = 'Gym / Fitness'
            s.commit()

    # The category merge (both lines; Rob 2026-10-09: "fix the merge button on 1.x too"). It looked budget lines up
    # by a category_id they don't have and raised on every merge since 1.0, so no merge ever saved.
    mt, ma, mc, mb = [], [], [], []
    try:
        from datetime import date
        with db_session() as s:
            target_id = s.query(Category).filter(Category.name == 'Gym / Fitness').first().id
            a = Account(name='s164 merge Checking', type='checking', is_active=True)
            ghost = Category(name='S164 Ghost', is_system=False)
            s.add_all([a, ghost]); s.flush()
            tx = Transaction(date=date.today(), description='S164 GHOST ROW', amount=5.0, type='debit', account_id=a.id, category_id=ghost.id)
            bl = BudgetItem(name='S164 ghost line', category='s164 ghost', amount=5.0)
            s.add_all([tx, bl]); s.commit()
            mt.append(tx.id); ma.append(a.id); mc.append(ghost.id); mb.append(bl.id)
        r = c.post(f'/api/categories/{mc[0]}/merge', headers=HJ, data=json.dumps({'target_id': target_id}))
        with db_session() as s:
            gone = s.get(Category, mc[0]) is None
            row_ok = s.get(Transaction, mt[0]).category_id == target_id
            line = s.get(BudgetItem, mb[0]).category
        check('s164 the category merge saves: rows and budget lines (matched by name, any case) move, and the merged category is removed',
              r.status_code == 200 and gone and row_ok and line == 'Gym / Fitness'
              and (r.get_json() or {}).get('data', {}).get('budget_items_moved') == 1)
        if gone:
            mc.clear()
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.id.in_(mt)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(ma)).delete(synchronize_session=False)
            s.query(Category).filter(Category.id.in_(mc)).delete(synchronize_session=False)
            s.query(BudgetItem).filter(BudgetItem.id.in_(mb)).delete(synchronize_session=False)
            s.commit()

    # L5 (master): rows already saved are offered, with their amounts, and move only on a yes
    if not (ctx.BASE / 'core/utility_estimate.py').exists():
        return
    made_t, made_a, made_c, made_b = [], [], [], []
    try:
        from datetime import date
        with db_session() as s:
            cats = s.query(Category).all()
            pid = {c.id: c.name for c in cats}
            gas_id = next(c.id for c in cats if c.name == 'Gas' and pid.get(c.parent_id) == 'Utilities')
            fuel_id = next(c.id for c in cats if c.name == 'Gas / Fuel')
            gym_id = next(c.id for c in cats if c.name == 'Gym / Fitness')
            a = Account(name='s164 L5 Checking', type='checking', is_active=True)
            stray = Category(name='Fitness', is_system=False)
            s.add_all([a, stray]); s.flush()
            rows = [Transaction(date=date.today(), description='SHELL OIL S164', amount=41.37, type='debit', account_id=a.id, category_id=gas_id),
                    Transaction(date=date.today(), description='MEIJER FUEL S164', amount=38.10, type='debit', account_id=a.id, category_id=gas_id),
                    Transaction(date=date.today(), description='DOMINION ENERGY GAS S164', amount=88.00, type='debit', account_id=a.id, category_id=gas_id),
                    Transaction(date=date.today(), description='PLANET FITNESS S164', amount=24.99, type='debit', account_id=a.id, category_id=stray.id)]
            bline = BudgetItem(name='S164 gym line', category='Fitness', amount=25.0)
            s.add_all(rows + [bline]); s.commit()
            made_b.append(bline.id)
            made_a.append(a.id); made_c.append(stray.id); made_t += [r.id for r in rows]
            shell, meijer, bill, gymrow = made_t
        rv = c.get('/api/categories/label-review', headers=H).get_json()['data']
        fu = rv.get('fuel') or {}
        ours = [x for x in fu.get('rows', []) if 'S164' in x['description']]
        check('s164 L5 the review offers the fill-ups saved under the gas utility, each with its amount - not the gas bill',
              sorted(x['id'] for x in ours) == sorted([shell, meijer]) and all(x['amount'] in (41.37, 38.10) for x in ours))
        with db_session() as s:
            unmoved = [s.get(Transaction, i).category_id for i in (shell, meijer)]
        check('s164 L5 looking moves nothing', unmoved == [gas_id, gas_id])
        mv = c.post('/api/categories/label-review/move', headers=HJ, data=json.dumps({'ids': [shell, bill, gymrow]})).get_json()['data']
        with db_session() as s:
            after = {i: s.get(Transaction, i).category_id for i in (shell, meijer, bill, gymrow)}
        check('s164 L5 only the rows said yes to move, and only rows the review offers can move (the bill stays)',
              mv['moved'] == 1 and after == {shell: fuel_id, meijer: gas_id, bill: gas_id, gymrow: made_c[0]})
        fit = rv.get('fitness') or {}
        check('s164 L5 the stray Fitness category is offered for a merge into Gym / Fitness',
              fit.get('id') == made_c[0] and fit.get('to_id') == gym_id and fit.get('count') == 1)
        m = c.post(f"/api/categories/{made_c[0]}/merge", headers=HJ, data=json.dumps({'target_id': gym_id}))
        with db_session() as s:
            gone = s.get(Category, made_c[0]) is None
            moved_gym = s.get(Transaction, gymrow).category_id == gym_id
            bcat = s.get(BudgetItem, made_b[0]).category
        check('s164 L5 the merge, on a yes, moves its rows and budget lines to Gym / Fitness and removes the stray (it raised on every merge before)',
              m.status_code == 200 and gone and moved_gym and bcat == 'Gym / Fitness')
        if gone:
            made_c.clear()
        node = shutil.which('node')
        if node:
            js = _fn(app, '_labelReviewFuelBlock') + _fn(app, 'labelReviewHTML') + r'''
const esc = s => String(s), fmt = n => '$' + Number(n).toFixed(2), fmtDate = s => s;
console.log(JSON.stringify([labelReviewHTML({fuel: {count: 2, total: 79.47, rows: [{id: 1, date: '2026-10-01', description: 'SHELL OIL', amount: 41.37}, {id: 2, date: '2026-10-02', description: 'MEIJER FUEL', amount: 38.10}]}, fitness: null}),
  labelReviewHTML({fuel: null, fitness: null})]));'''
            p = subprocess.run([node, '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=60)
            out = json.loads(p.stdout.strip() or '["",""]')
            check('s164 L5 the page asks, with the total and each amount, and offers Move all, a choice, and Leave them',
                  '2 purchases in <strong>Gas</strong> (your natural-gas utility) look like fill-ups' in out[0]
                  and '$79.47 in all' in out[0] and '$41.37' in out[0] and 'Move all' in out[0]
                  and 'Move the ones checked' in out[0] and 'Leave them' in out[0] and out[1] == '')
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.id.in_(made_t)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made_a)).delete(synchronize_session=False)
            s.query(Category).filter(Category.id.in_(made_c)).delete(synchronize_session=False)
            s.query(BudgetItem).filter(BudgetItem.id.in_(made_b)).delete(synchronize_session=False)
            s.commit()
