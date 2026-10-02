"""Utility bill estimates, the electricity slice (`gw 2.0/UTILITY_ESTIMATES.md`, item 26; Rob 2026-10-01: "build
electricity").

    bill = F + (B + Sh x HDD + Sc x CDD) x price      price in $/kWh (EIA publishes cents/kWh), usage in kWh
    - a weather term with a slope that is not positive is dropped and the fit redone (not every home heats or cools
      with electricity); at least one positive weather slope must remain
    - used only when it earns it, leave-one-out, as for gas: beats the baseline, beats a plain average by a quarter
    - the null model re-run on every gate: noise and flat bills almost never pick the fit
    - the same no-write rule (no budget amount, no budget_adjusted event) and the same EIA-credited forecast line
"""
import json
import random
import shutil
import subprocess
from datetime import date


def _world(rng, kind, months, noise=0.08):
    hprof = [1100, 950, 760, 420, 180, 40, 10, 15, 90, 380, 720, 1000]
    cprof = [0, 0, 5, 20, 90, 260, 380, 340, 160, 30, 0, 0]
    prices, hdds, cdds, bills = {}, {}, {}, []
    for i, mo in enumerate(months):
        h = hprof[i % 12] * rng.uniform(.85, 1.15)
        c = cprof[i % 12] * rng.uniform(.85, 1.15)
        pr = 0.15 + 0.02 * (i % 12 in (5, 6, 7, 8)) + rng.uniform(-.005, .005)
        prices[mo], hdds[mo], cdds[mo] = pr, h, c
        if kind == 'both':
            amt = 12 + (550 + 0.25 * h + 1.4 * c) * pr * rng.uniform(1 - noise, 1 + noise)
        elif kind == 'cool':
            amt = 12 + (550 + 1.4 * c) * pr * rng.uniform(1 - noise, 1 + noise)
        elif kind == 'flat':
            amt = 95 * rng.uniform(.8, 1.2)
        else:
            amt = rng.uniform(40, 220)
        bills.append({'month': mo, 'amount': amt})
    return bills, prices, hdds, cdds


def run(ctx):
    check = ctx.check
    from core import utility_estimate as ue

    check('s137 STEO electricity and cooling series by region, and nationally',
          ue.steo_series('elec_price', ue.region('AZ')) == 'ESRCU_MTN' and ue.steo_series('cdd', ue.region('OH')) == 'ZWCD_ENC'
          and ue.steo_series('elec_price', ue.region('')) == 'ESRCUUS' and ue.steo_series('cdd', ue.region('')) == 'ZWCDPUS')

    months = [f'{y}-{m:02d}' for y in (2024, 2025) for m in range(1, 13)]
    rng = random.Random(20261002)
    res = {k: [ue.choose_electric(*_world(rng, k, months)) for _ in range(150)] for k in ('both', 'cool', 'noise', 'flat')}
    rate = {k: sum(1 for r in v if r['method'] == 'fit') / len(v) for k, v in res.items()}
    check(f"s137 null model: the fit is chosen for bills that follow the weather (both {rate['both']:.2f}, cooling only "
          f"{rate['cool']:.2f} >= 0.8) and almost never for bills that don't (noise {rate['noise']:.2f}, flat {rate['flat']:.2f} <= 0.05)",
          rate['both'] >= 0.8 and rate['cool'] >= 0.8 and rate['noise'] <= 0.05 and rate['flat'] <= 0.05)
    cool_terms = [tuple(r['terms']) for r in res['cool'] if r['method'] == 'fit']
    both_terms = [tuple(r['terms']) for r in res['both'] if r['method'] == 'fit']
    check('s137 the weather terms are chosen by held-out error: a home that only cools gets cooling only, one that '
          'heats and cools gets both (at least 9 in 10 each)',
          cool_terms and both_terms and sum(1 for t in cool_terms if t == ('cdd',)) / len(cool_terms) >= 0.9
          and sum(1 for t in both_terms if t == ('hdd', 'cdd')) / len(both_terms) >= 0.9)
    # Capable is not admissible: the bill can be well predicted while the kWh figure is not. Measured before shipping.
    hp = [1100, 950, 760, 420, 180, 40, 10, 15, 90, 380, 720, 1000]
    cp = [0, 0, 5, 20, 90, 260, 380, 340, 160, 30, 0, 0]

    def spread_world(r_, spread):
        P, H, C, B = {}, {}, {}, []
        for i, mo in enumerate(months):
            h, c = hp[i % 12] * r_.uniform(.85, 1.15), cp[i % 12] * r_.uniform(.85, 1.15)
            pr = 0.16 * r_.uniform(1 - spread, 1 + spread)
            P[mo], H[mo], C[mo] = pr, h, c
            B.append({'month': mo, 'amount': 12 + (550 + 1.4 * c) * pr * r_.uniform(.95, 1.05)})
        return B, P, H, C

    def run_spread(spread, n=120):
        r_ = random.Random(3)
        bills_ok, stated = [], []
        for _ in range(n):
            B, P, H, C = spread_world(r_, spread)
            r = ue.choose_electric(B, P, H, C)
            if r['method'] != 'fit':
                continue
            bills_ok.append(ue.predict_terms(r['model'], 0.16, {'hdd': 1100, 'cdd': 0}) / (12 + 550 * 0.16))
            if r['usage_identified']:
                stated.append(ue.usage_terms(r['model'], {'hdd': 1100, 'cdd': 0}) / 550)
        return sorted(bills_ok), stated

    flat_b, flat_s = run_spread(0.05)
    vary_b, vary_s = run_spread(0.15)
    check(f's137 capable is not admissible: with near-flat prices the bill is predicted within 5% (p10-p90) but no kWh '
          f'figure is stated ({len(flat_s)} stated); with prices that move, kWh is stated ({len(vary_s)} of {len(vary_b)}) '
          f'and every stated figure is within 25-35% of the truth',
          flat_b and flat_b[int(len(flat_b) * .1)] > 0.95 and flat_b[int(len(flat_b) * .9)] < 1.05 and not flat_s
          and len(vary_s) >= len(vary_b) // 3 and all(0.75 < x < 1.35 for x in vary_s))
    few = ue.choose_electric([{'month': '2026-01', 'amount': 150}], {'2026-01': .15}, {'2026-01': 900}, {'2026-01': 0})
    check('s137 too few bills, or no summer in the record: the baseline, saying so', few['reason'] == 'not_enough_bills')
    # A world whose prices move (so the bills can separate usage from price) for the fitted estimate and its split,
    # and the near-flat world for the unsplit path.
    r5 = random.Random(5)
    hp0 = [1100, 950, 760, 420, 180, 40, 10, 15, 90, 380, 720, 1000]
    cp0 = [0, 0, 5, 20, 90, 260, 380, 340, 160, 30, 0, 0]
    bills, prices, hdds, cdds = [], {}, {}, {}
    for i, mo in enumerate(months):
        h, c = hp0[i % 12] * r5.uniform(.85, 1.15), cp0[i % 12] * r5.uniform(.85, 1.15)
        pr = 0.16 * r5.uniform(0.7, 1.3)
        prices[mo], hdds[mo], cdds[mo] = pr, h, c
        bills.append({'month': mo, 'amount': 12 + (550 + 0.25 * h + 1.4 * c) * pr * r5.uniform(.95, 1.05)})
    ch = ue.choose_electric(bills, prices, hdds, cdds)
    est = ue.estimate_electric(ch, bills, '2025-07', prices['2025-07'], hdds['2025-07'], cdds['2025-07'], prices)
    sp = ue.split_electric(ch, est, bills, prices, hdds, cdds)
    ok_fit = ch['method'] == 'fit' and est.get('usage_identified') and est.get('usage_kwh', 0) > 0 and est['terms']
    if ok_fit:
        u0 = ue.usage_terms(ch['model'], {'hdd': hdds['2024-07'], 'cdd': cdds['2024-07']})
        ok_fit = sp and sp['vs_month'] == '2024-07' and abs(sp['price'] + sp['usage'] - (
            est['usage_kwh'] * prices['2025-07'] - u0 * prices['2024-07'])) < 0.1
    check('s137 a fitted estimate whose usage the bills support carries kWh and the fixed part; its split adds up against last year',
          ok_fit)
    fb, fp, fh, fc = _world(random.Random(5), 'both', months)
    fch = ue.choose_electric(fb, fp, fh, fc)
    fest = ue.estimate_electric(fch, fb, '2025-07', fp['2025-07'], fh['2025-07'], fc['2025-07'], fp)
    fsp = ue.split_electric(fch, fest, fb, fp, fh, fc)
    check('s137 when the bills can\'t separate usage from price: no kWh or fixed figure, and the change against last year stated whole',
          fch['method'] == 'fit' and not fest.get('usage_identified') and 'usage_kwh' not in fest and 'fixed' not in fest
          and fsp and fsp.get('unsplit') and fsp['price'] is None)
    gap = ue.estimate_electric(ch, bills, '2031-01', 0.15, None, 0, prices)
    check('s137 a month EIA has no figure for is not estimated (missing weather is not zero)', gap['method'] == 'none')

    # The server, EIA and the bills stood in: EIA's cents become dollars, and nothing is written.
    import server
    from core.database import BudgetItem, HistorianEntry
    this_m = date.today().strftime('%Y-%m')
    prev_m = server._month_add(this_m, -1)
    real = (server._steo, server._utility_bills)
    try:
        def fake(session, series, fetch=True):
            if series.startswith('ESRCU'):
                return {**{m: v * 100 for m, v in prices.items()}, prev_m: 19.34, this_m: 19.82}
            if series.startswith('ZWCD'):
                return {**cdds, prev_m: 120.0, this_m: 30.0}
            return {**hdds, prev_m: 90.0, this_m: 377.0}
        server._steo = fake
        server._utility_bills = lambda session, category, lag: [dict(b, paid_month=b['month']) for b in bills]
        with ctx.dbs() as s:
            if not s.query(BudgetItem).filter(BudgetItem.category == 'Electric').first():
                s.add(BudgetItem(name='Electric', category='Electric', amount=110.0, type='expense', is_active=True))
                s.commit()
            saved = s.query(BudgetItem).filter(BudgetItem.category == 'Electric').first().amount
            before = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
        r = ctx.c.post('/api/budget/utility-estimate/optin', headers=ctx.HJ, data=json.dumps({'kind': 'electric', 'on': True, 'lag': 1}))
        d = (ctx.c.get('/api/budget/utility-estimate/electric', headers=ctx.HJ).get_json() or {}).get('data') or {}
        bad = ctx.c.get('/api/budget/utility-estimate/water', headers=ctx.HJ)
        with ctx.dbs() as s:
            after = s.query(BudgetItem).filter(BudgetItem.category == 'Electric').first().amount
            after_n = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
    finally:
        server._steo, server._utility_bills = real
    e = d.get('estimate') or {}
    check('s137 the route: EIA\'s cents become dollars per kWh for the arithmetic, and the forecast stays in cents',
          r.status_code == 200 and d.get('optin') is True and abs((e.get('price') or 0) - 0.1982) < 1e-9
          and d.get('forecast', {}).get('price') == 19.82 and d.get('forecast', {}).get('prev_price') == 19.34)
    check('s137 U3a following the electricity estimate writes no budget amount and logs no budget_adjusted event',
          after == saved and after_n == before)
    check('s137 only the estimated utilities have a route', bad.status_code == 404)

    node = shutil.which('node')
    check('s137 node is available to run the words (skip the next if not)', bool(node))
    if node:
        path = str(ctx.BASE.joinpath('static/js/teaching/utilitytext.js')).replace('\\', '/')
        prog = f"""
const U = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), month: m => m}};
const reg = {{state: 'AZ', division_name: 'Mountain', national: false}};
const out = U.electric({{region: reg, saved_amount: 110, choice: {{method: 'fit', fit_error: 6.2}},
  estimate: {{method: 'fit', amount: 142.5, usage_kwh: 812.4, fixed: 12, price: 0.1982, month: '2026-10', terms: ['cdd'], usage_identified: true}},
  split: {{vs_month: '2025-10', last_year_bill: 131, price: 3.1, usage: 8.4, assumes_same_usage: false}},
  forecast: {{month: '2026-10', price: 19.82, prev_month: '2026-09', prev_price: 19.34}}}}, F);
console.log(JSON.stringify(out));
"""
        o = json.loads(subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8',
                                      timeout=30).stdout.strip().splitlines()[-1])
        L = o['lines']
        check('s137 kWh at EIA\'s forecast in cents per kWh, the fixed part, and which weather it follows',
              any('about 812 kWh at EIA\'s forecast 19.82¢/kWh, plus about $12.00 a month fixed' in l for l in L)
              and any('cooling (your bills don\'t rise with the cold)' in l for l in L))
        check('s137 the forecast is EIA\'s, credited, and says only that the estimate uses it',
              o['statement'] == 'EIA forecasts residential electricity in Mountain at 19.82¢/kWh for 2026-10, up from 19.34¢ '
                                'in 2026-09; the electricity estimate on your Budget page uses that forecast.')
        check('s137 not followed: the saved Electric amount sets the totals, and the card says so (M4)',
              any('Your saved Electric budget of $110.00 sets the budget totals. Follow this estimate' in l for l in L))
        prog2 = prog.replace("usage_identified: true", "usage_identified: false").replace(
            "split: {vs_month: '2025-10', last_year_bill: 131, price: 3.1, usage: 8.4, assumes_same_usage: false}",
            "split: {vs_month: '2025-10', last_year_bill: 131, change: 11.5, price: null, usage: null, unsplit: true}")
        o2 = json.loads(subprocess.run([node, '-e', prog2], capture_output=True, text=True, encoding='utf-8',
                                       timeout=30).stdout.strip().splitlines()[-1])
        L2 = o2['lines']
        check('s137 when the bills can\'t separate usage from the fixed charge: no kWh figure, and the change is stated whole',
              any('no kWh figure is given' in l for l in L2) and not any('kWh at EIA' in l for l in L2)
              and any("+$11.50 in all; your bills can't yet tell how much of that is price and how much is usage" in l for l in L2))
