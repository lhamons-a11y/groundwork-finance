"""Fill-ups recognised by the station's name (gw 2.0/FUEL_NAMES.md, item 53; Rob 2026-10-09: "approve G1-G8 as
recommended").

    G1  BP#8823 and EXXONMOBIL are fuel
    G2  the missing brands, whole words; a name that is also a word or another business counts only with a store
        number or a station word (Holiday Inn, Pilot Pen, Gulf Coast Bank and a race entry stay out)
    G3  warehouse-club and grocery fuel is Gas / Fuel; an ordinary Costco or Kroger trip stays Groceries
    G4  a card code still wins over the name (a food code at Casey's is food)
    G5  tested both ways. The lines below are WRITTEN TO LOOK LIKE bank descriptions - they are not taken from real
        statements
    G6  the server and the page use the same pattern text
    G7  fuel saved under Groceries is offered in the review, and moves only on a yes
"""
import json
import re
import shutil
import subprocess

FUEL = ['BP#8823456 MILLBROOK OH', 'BP#1234', 'BP 8823 MILLBROOK', 'EXXONMOBIL 4521', 'EXXON MOBIL 12', 'EXXON 0045', 'MOBIL 0123',
        'SHELL OIL 5744', 'SPEEDWAY 0412', 'MARATHON PETRO123', 'CIRCLE K 0034', 'SUNOCO 0021', 'CHEVRON 0098',
        'PHILLIPS 66 #12', 'CONOCO 123', 'CITGO 4567', 'VALERO 1234', 'KROGER FUEL #234', 'MEIJER EXPRESS 123',
        'COSTCO GAS #123', 'SAMS CLUB FUEL', "SAM'S FUEL 4545", 'WAWA 812', 'SHEETZ 123', 'QT 123 OUT', 'QUIKTRIP #456',
        'RACETRAC 778', 'CASEYS GEN STORE 2345', "CASEY'S #123", 'KWIK TRIP 456', 'PILOT 00123', 'LOVES #456',
        "LOVE'S TRAVEL 233", 'MURPHY USA 7123', 'MURPHY EXPRESS 8811', 'HOLIDAY STATIONS 123', 'SINCLAIR 1234',
        'GULF OIL 92', 'ARCO #1234', "BUC-EE'S #22", 'THORNTONS #45', 'TA TRAVEL CENTER', 'GETGO 1234', 'GIANT EAGLE GETGO',
        '7-ELEVEN 3345 FUEL', 'SPEEDY Q 12', 'CUMBERLAND FARMS 12', 'FLYING J 0712']
NOT_FUEL = ['T-MOBILE AUTOPAY', 'SHELLYS SALON', 'BPI SPORTS', 'MARATHON REGISTRATION', 'PILOT PEN STORE', 'GULF COAST BANK',
            'ARCOS DORADOS', 'HOLIDAY INN EXPRESS', 'LOVESAC', 'GIANT EAGLE 1234', 'KROGER #234', 'COSTCO WHSE #123',
            'SAMS CLUB #44', "CASEY'S PIZZA DELIVERY", 'MURPHY BED CO', 'DOMINION ENERGY GAS', 'COLUMBIA GAS OF OHIO',
            'SINCLAIR COMMUNITY COLLEGE', 'QTIPS BEAUTY']


def _fn(src, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', src, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, HJ, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.app_src
    import bank_importer as bi
    from core.database import Category, Transaction, Account, db_session

    got = {d: bi.auto_category(d) for d in FUEL}
    missed = [d for d, cat in got.items() if cat != 'Gas / Fuel']
    check(f's165 G1/G2/G3 every station line is Gas / Fuel ({len(FUEL)} lines){" - missed: " + ", ".join(missed) if missed else ""}',
          missed == [])
    caught = [d for d in NOT_FUEL if bi.auto_category(d) == 'Gas / Fuel']
    check(f's165 G2/G3 no non-fuel line is fuel ({len(NOT_FUEL)} lines){" - caught: " + ", ".join(caught) if caught else ""}',
          caught == [])
    check('s165 G3 an ordinary warehouse-club or grocery trip stays Groceries',
          [bi.auto_category(d) for d in ('COSTCO WHSE #123', 'KROGER #234', 'SAMS CLUB #44')] == ['Groceries'] * 3)
    check('s165 G4 a card code still wins over the name (a food code at Casey\'s is food; a fuel code anywhere is fuel)',
          bi.auto_category("CASEY'S #123", '5814') == 'Fast Food / Takeout' and bi.auto_category('ANY STORE', '5541') == 'Gas / Fuel')

    # G6: the same text on both sides
    py = next(p for cat, p in bi._CATEGORY_PATTERNS if cat == 'Gas / Fuel')
    client = _fn(app, 'clientAutoCategory')
    m = re.search(r"\n  if \(/(.*?)/\.test\(d\)\) return 'Gas / Fuel';", client)
    check('s165 G6 the page\'s fuel pattern is the same text as the server\'s', bool(m) and m.group(1) == py)

    node = shutil.which('node')
    if node and client:
        js = client + 'const L = ' + json.dumps({'fuel': FUEL, 'not': NOT_FUEL}) + ''';
console.log(JSON.stringify({fuel: L.fuel.filter(d => clientAutoCategory(d) !== 'Gas / Fuel'),
                            not: L.not.filter(d => clientAutoCategory(d) === 'Gas / Fuel')}));'''
        p = subprocess.run([node, '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=60)
        out = json.loads(p.stdout.strip() or '{}') if p.returncode == 0 else {}
        check('s165 G5/G6 the page reads the same lines the same way', out == {'fuel': [], 'not': []})

    # G7: fuel saved under Groceries is offered, and moves only on a yes
    made_t, made_a = [], []
    try:
        from datetime import date
        with db_session() as s:
            groc = s.query(Category).filter(Category.name == 'Groceries').first().id
            fuel = s.query(Category).filter(Category.name == 'Gas / Fuel').first().id
            a = Account(name='s165 Checking', type='checking', is_active=True)
            s.add(a); s.flush()
            rows = [Transaction(date=date.today(), description='COSTCO GAS #123 S165', amount=52.40, type='debit', account_id=a.id, category_id=groc),
                    Transaction(date=date.today(), description='COSTCO WHSE #123 S165', amount=210.00, type='debit', account_id=a.id, category_id=groc)]
            s.add_all(rows); s.commit()
            made_a.append(a.id); made_t += [r.id for r in rows]
        gas_row, shop_row = made_t
        rv = c.get('/api/categories/label-review', headers=H).get_json()['data']
        offered = [x['id'] for x in (rv.get('fuel_groceries') or {}).get('rows', []) if 'S165' in x['description']]
        check('s165 G7 the review offers the Costco Gas row saved under Groceries, not the Costco shopping trip',
              offered == [gas_row] and (rv.get('fuel_groceries') or {}).get('from') == 'Groceries')
        mv = c.post('/api/categories/label-review/move', headers=HJ, data=json.dumps({'ids': [gas_row, shop_row]})).get_json()['data']
        with db_session() as s:
            after = (s.get(Transaction, gas_row).category_id, s.get(Transaction, shop_row).category_id)
        check('s165 G7 on a yes the fill-up moves to Gas / Fuel; the shopping trip cannot be moved by the review',
              mv['moved'] == 1 and after == (fuel, groc))
        if node:
            js = _fn(app, '_labelReviewFuelBlock') + _fn(app, 'labelReviewHTML') + r'''
const esc = s => String(s), fmt = n => '$' + Number(n).toFixed(2), fmtDate = s => s;
console.log(JSON.stringify(labelReviewHTML({fuel: null, fitness: null,
  fuel_groceries: {count: 1, total: 52.40, rows: [{id: 7, date: '2026-10-01', description: 'COSTCO GAS #123', amount: 52.40}]}})));'''
            p = subprocess.run([node, '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=60)
            html = json.loads(p.stdout.strip() or '""')
            check('s165 G7 the page asks about the Groceries row by name, with its amount, Move all and Leave them',
                  '1 purchase in <strong>Groceries</strong> looks like a fill-up — $52.40 in all' in html
                  and "labelReviewMove('fuel_groceries', true)" in html and 'Leave them' in html)
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.id.in_(made_t)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made_a)).delete(synchronize_session=False)
            s.commit()
