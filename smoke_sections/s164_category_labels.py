"""Imported purchases land in the right category (gw 2.0/CATEGORY_LABELS.md, item 52; Rob 2026-10-09: "approve L1-L7
as recommended").

    L1  fuel is Gas / Fuel (Transportation), never Gas (the natural-gas utility); gyms are Gym / Fitness
    L3  every name an importer can return is a real category in the tree - the drift can't come back silently
    L4  re-categorising never creates a category: a name the user's categories don't hold leaves the row as it is
"""
import json
import re


def _fn(src, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', src, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, HJ, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.app_src
    import bank_importer as bi
    from core.database import CATEGORY_TREE, Category, Transaction, Account, db_session
    tree = {r[0] for r in CATEGORY_TREE}

    # L1
    got = {d: bi.auto_category(d) for d in ('SHELL OIL 57444', 'CLARK GAS 12', 'MEIJER FUEL 0042', 'PLANET FITNESS 33')}
    check('s164 L1 fill-ups are Gas / Fuel and gyms are Gym / Fitness',
          got == {'SHELL OIL 57444': 'Gas / Fuel', 'CLARK GAS 12': 'Gas / Fuel', 'MEIJER FUEL 0042': 'Gas / Fuel',
                  'PLANET FITNESS 33': 'Gym / Fitness'})
    check('s164 L1 the fuel-station and fitness card codes follow',
          [bi.auto_category('X', m) for m in ('5541', '5542', '5172', '7997')] == ['Gas / Fuel'] * 3 + ['Gym / Fitness'])
    check('s164 L1 natural-gas bills still go to Utilities, not to fuel',
          bi.auto_category('DOMINION ENERGY GAS') == 'Utilities' and bi.auto_category('X', '4900') == 'Utilities')
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
