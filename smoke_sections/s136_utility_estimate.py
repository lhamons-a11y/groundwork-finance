"""Utility bill estimates, the natural gas slice (`gw 2.0/UTILITY_ESTIMATES.md`, item 26, ruled 2026-10-01).

    U9   every state and DC maps to a census division and a PADD; no state is the national series, labelled
    U1   the degree-day fit is used only when it earns it, scored leave-one-out on the user's own bills: it must beat the
         baseline, beat a plain average by a quarter, and slope up with the cold. The null model (bills with no weather
         or price pattern) is re-run on every gate - and must almost never pick the fit
    U3a  the estimate is derived and never written: no BudgetItem amount changes, no budget_adjusted event (the
         Willingness Layer reads those as the user's own edits)
    U4   the forecast line is EIA's, credited, and says only what the estimate proves - never that totals include it
         (Rob, 2026-10-01: totals use the saved amount until a follow-up pass)
    U6   a change is split into price and usage against the same month LAST YEAR - never month to month, which would
         call the season "price"
    I1   the dashboard fetches nothing; the outlook is fetched only behind the Budget page's own route
    U17  no location lookup anywhere - the state is the user's Settings choice
"""
import ast
import json
import random
import re
import shutil
import subprocess


def _world(rng, kind, months, noise=0.08):
    prof = [1100, 950, 760, 420, 180, 40, 10, 15, 90, 380, 720, 1000]
    prices, hdds, bills = {}, {}, []
    for i, mo in enumerate(months):
        hdd = prof[i % 12] * rng.uniform(0.85, 1.15)
        price = 12 + 6 * (i % 12 in (5, 6, 7, 8)) + rng.uniform(-1, 1)
        prices[mo], hdds[mo] = price, hdd
        if kind == 'model':
            amt = 25 + (0.6 + 0.011 * hdd) * price * rng.uniform(1 - noise, 1 + noise)
        elif kind == 'flat':
            amt = 90 * rng.uniform(0.8, 1.2)
        else:
            amt = rng.uniform(40, 220)
        bills.append({'month': mo, 'amount': amt})
    return bills, prices, hdds


def _node(base):
    node = shutil.which('node')
    if not node:
        return None
    path = str(base.joinpath('static/js/teaching/utilitytext.js')).replace('\\', '/')
    prog = f"""
const U = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), month: m => m}};
const reg = {{state: 'OH', division_name: 'East North Central', national: false}};
const out = {{}};
out.fit = U.gas({{region: reg, saved_amount: 120, choice: {{method: 'fit', fit_error: 8.4}},
  estimate: {{method: 'fit', amount: 165.2, usage_mcf: 9.1, fixed: 24, price: 14.54, month: '2026-10'}},
  split: {{vs_month: '2025-10', last_year_bill: 150, price: 9.5, usage: 5.7, assumes_same_usage: false}},
  forecast: {{month: '2026-10', price: 14.54, prev_month: '2026-09', prev_price: 13.10}}}}, F);
out.base = U.gas({{region: {{national: true}}, saved_amount: null, choice: {{method: 'baseline', reason: 'not_enough_bills', bills: 4}},
  estimate: {{method: 'baseline', amount: 90.02, price: 14.54, month: '2026-10', from_month: '2025-10', from_amount: 96.03, from_price: 15.51}},
  split: {{vs_month: '2025-10', last_year_bill: 96.03, price: -6.01, usage: 0, assumes_same_usage: true}},
  forecast: {{month: '2026-10', price: 14.54, prev_month: '2026-09', prev_price: 14.54}}}}, F);
out.none = U.gas({{region: reg, estimate: null, needs: 'EIA outlook missing.'}}, F);
console.log(JSON.stringify(out));
"""
    r = subprocess.run([node, '-e', prog], capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', r.stderr[:400])
        return {}


def run(ctx):
    check = ctx.check
    from core import utility_estimate as ue

    # U9 - every state and DC.
    states = ('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC '
              'ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY').split()
    check('s136 U9 every state and DC has a census division and a PADD (51 of 51)',
          len(states) == 51 and all(ue.STATE_DIVISION.get(s) and ue.STATE_PADD.get(s) for s in states)
          and set(ue.STATE_DIVISION) == set(states) and set(ue.STATE_PADD) == set(states))
    check('s136 U9 STEO series by region: Ohio is East North Central; no state is the national series, labelled',
          ue.steo_series('hdd', ue.region('oh')) == 'ZWHD_ENC' and ue.steo_series('ng_price', ue.region('AZ')) == 'NGRCU_MTN'
          and ue.region('')['national'] and ue.steo_series('hdd', ue.region('')) == 'ZWHDPUS'
          and ue.region('PR')['national'] and ue.region('')['division_name'] == 'United States')
    check('s136 a bill paid in a month pays for the month before (and the lag is the user\'s setting)',
          ue.service_month('2026-01', 1) == '2025-12' and ue.service_month('2026-03', 0) == '2026-03'
          and ue.service_month('2026-02', 2) == '2025-12')

    # U1 - the null model, on every gate.
    months = [f'{y}-{m:02d}' for y in (2024, 2025) for m in range(1, 13)]
    rng = random.Random(20261001)
    picks = {k: [ue.choose(*_world(rng, k, months))['method'] for _ in range(200)] for k in ('model', 'noise', 'flat')}
    rates = {k: v.count('fit') / len(v) for k, v in picks.items()}
    check(f"s136 U1 null model: the fit is chosen for bills that follow weather x price ({rates['model']:.2f} >= 0.85) "
          f"and almost never for bills that don't (noise {rates['noise']:.2f}, flat {rates['flat']:.2f} <= 0.05)",
          rates['model'] >= 0.85 and rates['noise'] <= 0.05 and rates['flat'] <= 0.05)
    few = ue.choose([{'month': '2026-01', 'amount': 150}], {'2026-01': 12}, {'2026-01': 1000})
    check('s136 U1 too few bills: the baseline, saying so', few['method'] == 'baseline' and few['reason'] == 'not_enough_bills')
    bills, prices, hdds = _world(random.Random(3), 'model', months)
    ch = ue.choose(bills, prices, hdds)
    nxt = ue.estimate(ch, bills, '2025-10', prices['2025-10'], hdds['2025-10'], prices)
    check('s136 U1 a fitted estimate carries its usage, fixed part, price and degree days',
          ch['method'] == 'fit' and nxt['method'] == 'fit' and nxt['usage_mcf'] > 0 and 'fixed' in nxt and nxt['hdd'] == hdds['2025-10'])
    none = ue.estimate({'method': 'baseline'}, [], '2026-10', 14.5, 300, {})
    check('s136 no year-ago bill and no fit: no estimate - it says what it needs', none['method'] == 'none' and 'needs' in none)
    gap = ue.estimate(ch, bills, '2031-01', None, None, prices)
    gap2 = ue.estimate(ch, bills, '2031-01', 14.0, None, prices)
    check('s136 a month EIA has no figure for is not estimated - missing degree days are never read as zero',
          gap['method'] == 'none' and gap2['method'] == 'none' and "EIA's outlook figures" in gap2['needs'])

    # U6 - against the same month last year.
    sp = ue.split_vs_last_year(ch, nxt, bills, prices, hdds)
    m = ch['model']
    u0 = m['B'] + m['S'] * hdds['2024-10']
    u1 = nxt['usage_mcf']
    check('s136 U6 the fitted split is against the same month last year, and price + usage add to the change in usage x price',
          sp and sp['vs_month'] == '2024-10' and not sp['assumes_same_usage']
          and abs((sp['price'] + sp['usage']) - (u1 * prices['2025-10'] - u0 * prices['2024-10'])) < 0.05)
    bl = ue.estimate({'method': 'baseline'}, bills, '2025-10', prices['2025-10'], 0, prices)
    sb = ue.split_vs_last_year({'method': 'baseline'}, bl, bills, prices, hdds)
    check('s136 U6 the baseline says the whole difference is price, because it assumes last year\'s usage',
          sb and sb['assumes_same_usage'] and sb['usage'] == 0.0)

    # The server, with EIA and the bills stood in (no network).
    import server
    from core.database import BudgetItem, HistorianEntry
    real = (server._steo, server._gas_bills)
    try:
        from datetime import date
        this_m = date.today().strftime('%Y-%m')
        prev_m = server._month_add(this_m, -1)

        def fake_steo(session, series, fetch=True):
            # EIA's outlook covers the current months too (history and forecast in one series).
            if series.startswith('NGRCU'):
                return {**prices, prev_m: 13.10, this_m: 14.54}
            return {**hdds, prev_m: 90.0, this_m: 377.0}
        server._steo = fake_steo
        server._gas_bills = lambda session, lag: [{'month': b['month'], 'paid_month': b['month'], 'amount': b['amount']} for b in bills]
        with ctx.dbs() as s:
            item = s.query(BudgetItem).filter(BudgetItem.category == 'Gas').first()
            if not item:
                item = BudgetItem(name='Gas', category='Gas', amount=120.0, type='expense', is_active=True)
                s.add(item)
                s.commit()
            saved = item.amount
            adj_before = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
        r = ctx.c.post('/api/budget/utility-estimate/optin', headers=ctx.HJ, data=json.dumps({'kind': 'gas', 'on': True, 'lag': 1}))
        g = (ctx.c.get('/api/budget/utility-estimate/gas', headers=ctx.HJ).get_json() or {}).get('data') or {}
        with ctx.dbs() as s:
            after = s.query(BudgetItem).filter(BudgetItem.category == 'Gas').first().amount
            adj_after = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
    finally:
        server._steo, server._gas_bills = real
    check('s136 the route answers with the region, the method chosen and why, the estimate and its forecast',
          r.status_code == 200 and g.get('optin') is True and g.get('choice', {}).get('method') in ('fit', 'baseline')
          and g.get('estimate') and g.get('forecast', {}).get('month'))
    check('s136 U3a following the estimate writes no budget amount and logs no budget_adjusted event',
          after == saved and adj_after == adj_before)
    bad1 = ctx.c.post('/api/budget/utility-estimate/optin', headers=ctx.HJ, data=json.dumps({'kind': 'water', 'on': True}))
    bad2 = ctx.c.post('/api/budget/utility-estimate/optin', headers=ctx.HJ, data=json.dumps({'kind': 'gas', 'on': True, 'lag': 5}))
    check('s136 only the estimated utilities can be followed, and the lag is 0-2 months', bad1.status_code == 400 and bad2.status_code == 400)

    # I1 / U17 - structural.
    src = ctx.server_src
    tree = ast.parse(src)
    callers = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
               and any(isinstance(c, ast.Call) and getattr(c.func, 'id', None) == '_steo' for c in ast.walk(n))}
    check('s136 I1 the outlook is fetched only by the utility estimates (behind the Budget page\'s route)',
          callers == {'gas_estimate', 'electric_estimate'})
    dash = ''.join(ctx.BASE.joinpath('static/js/teaching', f).read_text(encoding='utf-8')
                   for f in ('dashboard.js', 'tiles.js', 'asktile.js', 'attention.js'))
    check('s136 I1 nothing on the dashboard calls the estimate', 'utility-estimate' not in dash)
    every = src + ''.join(p.read_text(encoding='utf-8') for p in ctx.BASE.joinpath('static/js/teaching').glob('*.js')) \
        + ctx.BASE.joinpath('core/utility_estimate.py').read_text(encoding='utf-8')
    check('s136 U17 no location lookup anywhere - no geolocation, no IP-location service',
          not re.search(r'geolocation|ipinfo|ip-api|ipapi|geoip|freegeoip|getCurrentPosition', every, re.I))

    o = _node(ctx.BASE)
    check('s136 node is available to run the words (skip the next if not)', o is not None)
    if o is not None:
        f = o['fit']['lines']
        check('s136 the fit says its usage, the forecast price and its fixed part, and how close it has been',
              any('about 9.1 MCF at EIA\'s forecast $14.54/MCF, plus about $24.00 a month fixed' in l for l in f)
              and any('within about $8.40 on average' in l for l in f))
        check('s136 U6 price and usage said separately, against the same month last year',
              any(l == 'Against 2025-10 ($150.00): +$9.50 from price and +$5.70 from usage.' for l in f))
        check('s136 U4 the forecast is EIA\'s, credited, and says only that the estimate uses it',
              o['fit']['statement'] == 'EIA forecasts residential natural gas in East North Central at $14.54/MCF for 2026-10, '
                                       'up from $13.10 in 2026-09; the gas estimate on your Budget page uses that forecast.')
        check('s136 the saved amount still sets the totals, and the card says so (Rob, 2026-10-01)',
              any('still sets the budget totals' in l for l in f) and not any('budget already includes' in l for l in f))
        b = o['base']['lines']
        check('s136 the baseline names last year\'s bill and both prices, and why no weather fit is used',
              any('2025-10\'s bill of $96.03, at EIA\'s forecast $14.54/MCF instead of $15.51' in l for l in b)
              and any('not yet enough bills for a weather fit (4 so far' in l for l in b)
              and any('all from price - this figure assumes the same usage as last year' in l for l in b))
        check('s136 U9 no state: U.S. averages, with one plain pointer to Settings', b[0].startswith('Using U.S. averages; set your home state in Settings'))
        check('s136 an unchanged forecast makes no up/down statement', o['base']['statement'] is None)
        check('s136 without EIA\'s outlook, the card says what it needs', o['none']['lines'][-1] == 'EIA outlook missing.')
