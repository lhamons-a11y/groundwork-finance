"""Diesel, priced (gw 2.0/FUEL_PRICING.md, item 34 F1; Rob 2026-10-03).

The gasoline method (s138), with EIA's weekly No. 2 diesel series when the household said its vehicle uses diesel:
California's own series in California, the PADD region everywhere else, the U.S. with no state - which is how EIA
publishes diesel (measured 2026-10-03; gasoline has nine states' series, diesel only California's). The estimate keeps
its id, so the opt-in and the budget totals (BUDGET_MONTH_AMOUNT.md) carry over; the words name the fuel priced.
"""
import json
import shutil
import subprocess


def run(ctx):
    check, BASE, c, H, HJ = ctx.check, ctx.BASE, ctx.c, ctx.H, ctx.HJ
    import server
    from core import utility_estimate as ue, household
    from core.database import AppSetting, HouseholdFact

    oh, ca, az, none = (ue.diesel_area(ue.region(s)) for s in ('OH', 'CA', 'AZ', ''))
    check('s142 the area: California\'s own diesel series; Ohio the Midwest PADD (no Ohio diesel series); Arizona the '
          'West Coast; no state the U.S.',
          ca == {'duoarea': 'SCA', 'label': 'CA', 'kind': 'state'} and oh['duoarea'] == 'R20' and 'PADD 2' in oh['label']
          and az['duoarea'] == 'R50' and none['duoarea'] == 'NUS')
    check('s142 gasoline keeps its own areas (Ohio has a gasoline series, not a diesel one)',
          ue.gasoline_area(ue.region('OH'))['duoarea'] == 'SOH' and ue.EIA_PRODUCT == {'gasoline': 'EPMR', 'diesel': 'EPD2D'})

    asked = []
    weekly = {'2026-06-01': 3.90, '2026-07-06': 4.00, '2026-08-03': 4.10, '2026-09-28': 4.05, '2025-09-29': 3.70}
    real = server._eia_weekly_gas

    def fake(session, area, fetch=True, product='EPMR'):
        asked.append((area, product))
        return dict(weekly)

    def setup(fuel):
        with ctx.dbs() as s:
            for k in household.FACTS:
                s.query(HouseholdFact).filter_by(key=k).delete()
                s.query(AppSetting).filter_by(key=k).delete()
            household.set_household_fact(s, 'home_state', 'OH', 'settings')
            if fuel:
                household.set_household_fact(s, 'vehicle_fuel', fuel, 'settings')
            s.commit()

    try:
        server._eia_weekly_gas = fake
        setup('diesel')
        with ctx.dbs() as s:
            d = server.gasoline_estimate(s, fetch=False)
            applies = server.utility_applies(s, 'gasoline')
        check('s142 a diesel household is priced from EIA\'s diesel series for its PADD (Ohio -> R20, EPD2D)',
              d['fuel'] == 'diesel' and d['area']['duoarea'] == 'R20' and asked[-1] == ('R20', 'EPD2D'))
        check('s142 diesel is no longer "not priced yet": the estimate applies, and asks nothing more',
              applies['applies'] is True and applies.get('ask') == [])
        setup('gasoline')
        with ctx.dbs() as s:
            g = server.gasoline_estimate(s, fetch=False)
        check('s142 a gasoline household is unchanged: Ohio\'s own gasoline series (SOH, EPMR)',
              g['fuel'] == 'gasoline' and asked[-1] == ('SOH', 'EPMR'))
        setup(None)
        with ctx.dbs() as s:
            u = server.gasoline_estimate(s, fetch=False)
        check('s142 vehicle fuel unanswered: priced as gasoline, as item 30 says it does (and asks)',
              u['fuel'] == 'gasoline' and asked[-1][1] == 'EPMR')
    finally:
        server._eia_weekly_gas = real
        setup(None)
        with ctx.dbs() as s:
            for k in household.FACTS:
                s.query(HouseholdFact).filter_by(key=k).delete()
                s.query(AppSetting).filter_by(key=k).delete()
            s.commit()

    tree = server.__dict__
    import ast
    callers = {n.name for n in ast.walk(ast.parse(ctx.server_src)) if isinstance(n, ast.FunctionDef)
               and any(isinstance(x, ast.Call) and getattr(x.func, 'id', None) == '_eia_weekly_gas' for x in ast.walk(n))}
    check('s142 the weekly fetch is still made only by the vehicle-fuel estimate (behind the Budget page)',
          callers == {'gasoline_estimate'})
    check('s142 the cache keeps gasoline and diesel apart (a diesel price is never read as gasoline\'s)',
          "f'eia_weekly_{product}_{area}'" in ctx.server_src)

    node = shutil.which('node')
    check('s142 node is available to run the words (skip the next if not)', bool(node))
    if node:
        path = str(BASE.joinpath('static/js/teaching/utilitytext.js')).replace('\\', '/')
        prog = f"""
const U = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), month: m => m, date: s => s}};
const d = {{fuel: 'diesel', region: {{state: 'OH', national: false}}, area: {{kind: 'padd', label: 'the Midwest (PADD 2)'}},
  saved_amount: 220, optin: false, budget_uses: {{in_totals: false}},
  estimate: {{method: 'gallons', gallons: 52.0, price: 4.05, amount: 210.6, week: '2026-09-28', months_used: ['a','b','c'],
             year_ago: {{week: '2025-09-29', price: 3.70, amount: 192.4, price_part: 18.2}}}}}};
console.log(JSON.stringify(U.gasoline(d, F)));
"""
        r = subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8', timeout=30)
        try:
            o = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                                   # noqa: BLE001 - reported below
            o = {}
            print('        node:', r.stderr[:300])
        L = o.get('lines', [])
        check('s142 the words name diesel: EIA\'s weekly diesel price for the Midwest, and why a PADD is used',
              L and L[0] == 'Using EIA\'s weekly diesel price for the Midwest (PADD 2) (EIA publishes no weekly series for OH).')
        check('s142 the statement is EIA\'s diesel price, credited, and never says "gasoline"',
              o.get('statement', '').startswith("EIA's latest weekly diesel price for the Midwest (PADD 2) is $4.05/gal")
              and 'gasoline' not in ' '.join(L) + (o.get('statement') or ''))
        ut = BASE.joinpath('static/js/teaching/utility.js').read_text(encoding='utf-8')
        check('s142 the card is titled "Diesel estimate" for a diesel household',
              "(k.kind === 'gasoline' && d.fuel === 'diesel') ? 'Diesel estimate' : k.title" in ut)
