"""Utility bill estimates, the gasoline slice (`gw 2.0/UTILITY_ESTIMATES.md` U2, item 26; Rob 2026-10-01: "Build this").

    area      EIA's weekly regular-gasoline price for the user's own state where EIA publishes one (nine states),
              else their PADD region, else the U.S. - all confirmed against EIA, 2026-10-01
    gallons   each fill-up (Gas / Fuel) / that week's average price; a fill-up with no weekly price within two weeks is
              not converted; a month without fill-ups is absent, never zero; the current month is left out
    estimate  the median of the last six months with fill-ups x EIA's latest weekly price; under three months it says
              what it needs
    U6        a year earlier, the same gallons at last year's price - the difference is all price, and said so
    the rest  nothing written to the budget; fetched only behind the Budget route; the words carry no verdict
"""
import ast
import json
import shutil
import subprocess


def run(ctx):
    check = ctx.check
    from core import utility_estimate as ue

    oh, az, nj, none = (ue.gasoline_area(ue.region(s)) for s in ('OH', 'AZ', 'NJ', ''))
    check('s138 the area: Ohio\'s own weekly series; Arizona the West Coast PADD; New Jersey Central Atlantic; no state the U.S.',
          oh == {'duoarea': 'SOH', 'label': 'OH', 'kind': 'state'} and az['duoarea'] == 'R50' and 'PADD 5' in az['label']
          and nj['duoarea'] == 'R1Y' and none['duoarea'] == 'NUS' and none['kind'] == 'national')
    check('s138 every PADD region has its EIA area code', set(ue.PADD_AREA) == {'1A', '1B', '1C', '2', '3', '4', '5'})

    weekly = {'2026-06-01': 4.00, '2026-06-08': 4.10, '2026-07-06': 4.20, '2026-08-03': 4.30, '2026-09-28': 4.25,
              '2025-09-29': 3.80}
    check('s138 a fill-up takes the price of the week it fell in, and none if no week is within two weeks',
          ue._week_price('2026-06-10', weekly) == 4.10 and ue._week_price('2026-06-30', weekly) is None)
    fills = [{'date': '2026-06-03', 'amount': 40.0}, {'date': '2026-06-25', 'amount': 41.0},
             {'date': '2026-07-08', 'amount': 42.0}, {'date': '2026-08-05', 'amount': 43.0},
             {'date': '2026-09-30', 'amount': 44.0}, {'date': '2026-10-01', 'amount': 45.0}]
    months = ue.fuel_months(fills, weekly, '2026-10')
    check('s138 gallons per complete month at the week\'s price; an unmatched fill-up is not guessed; the current month left out',
          months['2026-06']['gallons'] == 10.0 and months['2026-06']['fillups'] == 1
          and abs(months['2026-07']['gallons'] - 10.0) < 0.01 and '2026-10' not in months
          and months['2026-09']['gallons'] == round(44 / 4.25, 2))
    few = ue.estimate_gasoline({'2026-06': {'gallons': 10, 'spent': 40, 'fillups': 1}}, weekly)
    check('s138 under three months with fill-ups: no estimate - it says what it needs',
          few['method'] == 'none' and 'at least three months' in few['needs'])
    est = ue.estimate_gasoline(months, weekly)
    typ = sorted(r['gallons'] for r in months.values())[len(months) // 2] if len(months) % 2 else None
    check('s138 the estimate: the median month\'s gallons x EIA\'s latest weekly price, with the week it is from',
          est['method'] == 'gallons' and est['week'] == '2026-09-28' and est['price'] == 4.25
          and abs(est['amount'] - est['gallons'] * 4.25) < 0.25)   # gallons shown rounded to 0.1
    check('s138 U6 a year earlier: the same gallons at last year\'s price - the difference is all price',
          est['year_ago'] and est['year_ago']['price'] == 3.80
          and abs(est['year_ago']['price_part'] - round(est['gallons'] * (4.25 - 3.80), 2)) < 0.2)
    check('s138 with no weekly prices: no estimate', ue.estimate_gasoline(months, {})['method'] == 'none')

    import server
    from core.database import BudgetItem, HistorianEntry
    real = server._eia_weekly_gas
    try:
        server._eia_weekly_gas = lambda session, area, fetch=True, product='EPMR': dict(weekly)
        with ctx.dbs() as s:
            before = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
            amounts = sorted((b.id, b.amount) for b in s.query(BudgetItem).all())
        r = ctx.c.post('/api/budget/utility-estimate/optin', headers=ctx.HJ, data=json.dumps({'kind': 'gasoline', 'on': True, 'lag': 0}))
        d = (ctx.c.get('/api/budget/utility-estimate/gasoline', headers=ctx.HJ).get_json() or {}).get('data') or {}
        with ctx.dbs() as s:
            after = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
            amounts2 = sorted((b.id, b.amount) for b in s.query(BudgetItem).all())
    finally:
        server._eia_weekly_gas = real
    check('s138 the route answers with the area, the user\'s choice and an estimate (or what it needs)',
          r.status_code == 200 and d.get('optin') is True and d.get('area', {}).get('duoarea') and d.get('estimate'))
    check('s138 following the gasoline estimate writes no budget amount and logs no budget_adjusted event',
          before == after and amounts == amounts2)
    tree = ast.parse(ctx.server_src)
    callers = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
               and any(isinstance(c, ast.Call) and getattr(c.func, 'id', None) == '_eia_weekly_gas' for c in ast.walk(n))}
    check('s138 the weekly prices are fetched only by the gasoline estimate (behind the Budget page\'s route)',
          callers == {'gasoline_estimate'})

    node = shutil.which('node')
    check('s138 node is available to run the words (skip the next if not)', bool(node))
    if node:
        path = str(ctx.BASE.joinpath('static/js/teaching/utilitytext.js')).replace('\\', '/')
        prog = f"""
const U = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), month: m => m, date: s => s}};
const base = {{region: {{state: 'AZ', national: false}}, area: {{kind: 'padd', label: 'the West Coast (PADD 5)'}}, saved_amount: 160}};
const out = {{}};
out.ok = U.gasoline(Object.assign({{}}, base, {{estimate: {{method: 'gallons', gallons: 38.4, price: 4.25, amount: 163.2, week: '2026-09-28',
  months_used: ['2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09'],
  year_ago: {{week: '2025-09-29', price: 3.80, amount: 145.92, price_part: 17.28}}}}}}), F);
out.none = U.gasoline(Object.assign({{}}, base, {{estimate: {{method: 'none', needs: 'fill-ups in at least three months'}}}}), F);
console.log(JSON.stringify(out));
"""
        o = json.loads(subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8',
                                      timeout=30).stdout.strip().splitlines()[-1])
        L = o['ok']['lines']
        check('s138 the area said plainly, including why a PADD is used',
              L[0] == 'Using EIA\'s weekly regular-gasoline price for the West Coast (PADD 5) (EIA publishes no weekly series for AZ).')
        check('s138 the gallons and how they were found (at each week\'s average price - the pump price isn\'t in the record)',
              any('about 38.4 gallons in a typical month' in l and "what you paid at the pump isn't in your record" in l for l in L)
              and any('At EIA\'s latest weekly price, $4.25/gal (week of 2026-09-28), that is about $163.20 a month.' == l for l in L))
        check('s138 U6 a year earlier, all from price; the statement is EIA\'s weekly price, credited, not a forecast',
              any('+$17.28, all from price' in l for l in L)
              and o['ok']['statement'] == "EIA's latest weekly regular-gasoline price for the West Coast (PADD 5) is $4.25/gal "
                                          "(week of 2026-09-28), up from $3.80 a year earlier; the gasoline estimate on your Budget page uses it.")
        check('s138 the saved amount still sets the totals; without enough fill-ups, it says what it needs',
              any('Your saved Gas / Fuel budget of $160.00 sets the budget totals. Follow this estimate' in l for l in L)
              and o['none']['lines'][-1] == 'A gasoline estimate needs fill-ups in at least three months.')
