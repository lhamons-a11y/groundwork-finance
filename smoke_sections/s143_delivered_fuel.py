"""Propane and heating oil, priced from deliveries (gw 2.0/FUEL_PRICING.md, item 34 F2-F4; Rob 2026-10-03).

    price     EIA's weekly RESIDENTIAL price (petroleum/pri/wfr, process PRS - never the wholesale PWR rows in the same
              series): the state's own series, else its PADD region, else the U.S. (coverage measured 2026-10-03)
    gallons   a delivery's dollars / that week's price; a delivery with no price within two weeks (outside EIA's
              October-March season) is not converted - it still starts the next interval
    F2        the weather fit (gallons = b * days + k * HDD) is used only if, from three priced intervals, it beats one
              steady daily rate by 25% held out, k > 0, and the weather is at least 30% of a year's use (s7's simulation)
              - otherwise there is no estimate, and the card says which test failed
    F3        out of season there is no current figure: last season's price is shown as last season's, never a zero
    F4        the estimate keeps the budget totals' contract (BUDGET_MONTH_AMOUNT.md): followed, never written
"""
import datetime as dt
import json
import shutil
import subprocess

MONTH_HDD = [1100, 900, 750, 450, 200, 40, 10, 15, 100, 400, 700, 1000]


def _hdds():
    return {f'{y}-{m:02d}': float(MONTH_HDD[m - 1]) for y in range(2022, 2028) for m in range(1, 13)}


def _season_mondays(first_year, last_day):
    out, d = [], dt.date(first_year, 10, 1)
    while d.weekday() != 0:
        d += dt.timedelta(days=1)
    while d <= last_day:
        if d.month in (10, 11, 12, 1, 2, 3):
            out.append(d.isoformat())
        d += dt.timedelta(days=7)
    return out


def _deliveries(base, k, weekly, start, end, every=30, wobble=0.03):
    """Fills every `every` days; dollars = the true gallons used since the last fill x that week's price (or a summer
    price no one publishes). A small, fixed wobble stands in for the dealer and the weather not matching EIA's."""
    from core import utility_estimate as ue
    hdds, out, d, i = _hdds(), [], start, 0
    prev = d
    out.append({'date': d.isoformat(), 'amount': 300.0})
    while True:
        d = d + dt.timedelta(days=every)
        if d > end:
            break
        gal, day = 0.0, prev + dt.timedelta(days=1)
        while day <= d:
            m = day.strftime('%Y-%m')
            gal += base + k * hdds[m] / ue._days_in(m)
            day += dt.timedelta(days=1)
        gal *= 1 + wobble * (1 if i % 2 else -1)
        price = ue._week_price(d.isoformat(), weekly) or 2.40          # off-season: a price EIA does not publish
        out.append({'date': d.isoformat(), 'amount': round(gal * price, 2)})
        prev, i = d, i + 1
    return out


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    from core import utility_estimate as ue

    r = lambda st: ue.region(st)                                   # noqa: E731
    check('s143 the area: Ohio has its own residential propane and heating oil series; West Virginia propane uses the '
          'Lower Atlantic; Arizona propane and Texas heating oil the U.S. (EIA publishes neither region)',
          ue.delivered_area(r('OH'), 'propane')['duoarea'] == 'SOH' and ue.delivered_area(r('OH'), 'heating_oil')['duoarea'] == 'SOH'
          and ue.delivered_area(r('WV'), 'propane')['duoarea'] == 'R1Z'
          and ue.delivered_area(r('AZ'), 'propane')['duoarea'] == 'NUS'
          and ue.delivered_area(r('TX'), 'heating_oil')['duoarea'] == 'NUS'
          and ue.delivered_area(r(''), 'propane')['kind'] == 'national')
    check('s143 the products: EPLLPA propane, EPD2F heating oil (No. 2 heating oil, not on-highway diesel)',
          ue.DELIVERED_PRODUCT == {'propane': 'EPLLPA', 'heating_oil': 'EPD2F'})
    src = ctx.server_src
    check('s143 only RESIDENTIAL prices are fetched: the wfr series filtered to process PRS (wholesale PWR excluded)',
          '/petroleum/pri/wfr/data/' in src and 'facets[process][]=PRS' in src)

    today = dt.date(2026, 11, 10)
    weekly = {w: 2.60 for w in _season_mondays(2023, today)}
    hdds = _hdds()
    heat = _deliveries(0.5, 0.15, weekly, dt.date(2023, 10, 5), dt.date(2026, 11, 5))
    iv, unpriced = ue.delivered_intervals(heat, weekly, hdds)
    first = iv[0]
    check('s143 an interval: the gallons delivered at a priced fill are its dollars / that week\'s price, used since '
          'the fill before',
          first['days'] == 30 and abs(first['gallons'] - [x for x in heat if x['date'] == first['to']][0]['amount'] / 2.60) < 0.01)
    check('s143 a summer delivery (no EIA price that week) is not turned into gallons, and is counted',
          unpriced > 0 and all(dt.date.fromisoformat(x['to']).month in (10, 11, 12, 1, 2, 3, 4) for x in iv))
    year_hdd = float(sum(MONTH_HDD))
    ch = ue.choose_delivered(iv, year_hdd)
    check('s143 F2 a heating household: the weather fit passes all three tests and recovers its use '
          '(0.5 gal/day + 0.15/HDD)',
          ch['method'] == 'weather' and abs(ch['base'] - 0.5) < 0.1 and abs(ch['k'] - 0.15) < 0.02
          and ch['held_out_error'] < 0.75 * ch['average_error'] and ch['weather_share'] >= 0.30)
    check('s143 F2 under three priced intervals: no estimate (too few), never a forced fit',
          ue.choose_delivered(iv[:2], year_hdd) == {'method': 'none', 'reason': 'too_few', 'n': 2})
    flat = _deliveries(0.45, 0.0, weekly, dt.date(2023, 10, 5), dt.date(2026, 11, 5), wobble=0.10)
    fc = ue.choose_delivered(ue.delivered_intervals(flat, weekly, hdds)[0], year_hdd)
    check('s143 F2 a weather-free household (water heater, cooking): the weather fit is declined', fc['method'] == 'none'
          and fc['reason'] in ('no_heating_slope', 'no_better_than_average', 'weather_share_too_small'))
    weak = _deliveries(1.2, 0.01, weekly, dt.date(2023, 10, 5), dt.date(2026, 11, 5), wobble=0.0)
    wc = ue.choose_delivered(ue.delivered_intervals(weak, weekly, hdds)[0], year_hdd)
    check('s143 F2 the 30% floor: deliveries that track the weather exactly, but where it is under 30% of a year\'s '
          'use, are declined as heating', wc['method'] == 'none' and wc['reason'] == 'weather_share_too_small'
          and wc['weather_share'] < 0.30)

    est = ue.estimate_delivered(ch, '2026-11', hdds['2026-11'], weekly, today)
    latest = max(weekly)
    check('s143 in season: this month\'s use from the fit x EIA\'s latest residential price, with the week it is from',
          est['method'] == 'weather' and est['week'] == latest and est['price'] == 2.60 and est['current'] is True
          and abs(est['amount'] - (ch['base'] * 30 + ch['k'] * 700) * 2.60) < 0.5)
    spring = {w: p for w, p in weekly.items() if w <= '2026-03-30'}
    off = ue.estimate_delivered(ch, '2026-10', hdds['2026-10'], spring, dt.date(2026, 10, 3))
    check('s143 F3 out of season: no estimate and no amount; the last price is reported as last season\'s (its week)',
          off['method'] == 'none' and off['reason'] == 'out_of_season' and 'amount' not in off
          and off['last_price']['week'] == max(spring) and off['last_price']['season'] == 'last' and off['current'] is False)
    # The calendar is not the rule, the price evidence is: EIA published a summer week a month in 2024 and in April-May
    # 2025 (measured live 2026-10-03). A price under two weeks old is current; one older is not.
    april = ue.estimate_delivered(ch, '2026-04', hdds['2026-04'], spring, dt.date(2026, 4, 2))
    late = ue.estimate_delivered(ch, '2026-04', hdds['2026-04'], spring, dt.date(2026, 4, 20))
    check('s143 F3 by evidence: March 30\'s price is current on April 2; on April 20 it is not, and it is this '
          'season\'s (not last season\'s)',
          april['method'] == 'weather' and late['method'] == 'none' and late['reason'] == 'out_of_season'
          and late['last_price']['season'] == 'this')

    # ── the server: the household's answer first, then the estimate; totals followed, never written ─────────
    import server
    from core import household
    from core.database import AppSetting, BudgetItem, Category, HistorianEntry, HouseholdFact, Transaction
    asked = []
    real_w, real_s, real_d = server._eia_weekly_heating, server._steo, server.delivered_estimate

    def fake_w(session, area, product, fetch=True):
        asked.append((area, product))
        return dict(weekly)

    def facts(**kv):
        with ctx.dbs() as s:
            for k in household.FACTS:
                s.query(HouseholdFact).filter_by(key=k).delete()
                s.query(AppSetting).filter_by(key=k).delete()
            household.set_household_fact(s, 'home_state', 'OH', 'settings')
            for k, v in kv.items():
                household.set_household_fact(s, k, v, 'settings')
            s.commit()

    with ctx.dbs() as s:
        cat = s.query(Category).filter(Category.name == 'Propane').first()
        if not cat:
            cat = Category(name='Propane', type='expense')
            s.add(cat)
            s.flush()
        for x in heat:
            s.add(Transaction(date=dt.date.fromisoformat(x['date']), description='S143 propane delivery',
                              amount=x['amount'], type='debit', category_id=cat.id))
        item = BudgetItem(name='Propane', category='Propane', amount=180.0, type='expense', is_active=True)
        s.add(item)
        s.commit()
        item_id = item.id
    try:
        server._eia_weekly_heating = fake_w
        server._steo = lambda session, series, fetch=True: dict(hdds)
        server.delivered_estimate = lambda session, fuel, fetch=True, today=None: real_d(session, fuel, fetch, today=dt.date(2026, 11, 10))
        facts(heating_fuel='propane', heating_payment='by_bill')
        with ctx.dbs() as s:
            d = server.delivered_estimate(s, 'propane', fetch=False)
            gas = server.utility_applies(s, 'gas')
        check('s143 a propane household: priced from Ohio\'s residential propane series, and the fit is used',
              asked[-1] == ('SOH', 'EPLLPA') and d['estimate']['method'] == 'weather' and d['choice']['method'] == 'weather'
              and d['unpriced'] > 0)
        check('s143 the natural gas card no longer says propane is "not priced yet": it points to propane\'s own estimate',
              gas['applies'] is False and 'own estimate' in gas['why'] and 'yet' not in gas['why'])
        with ctx.dbs() as s:
            amounts = sorted((b.id, b.amount) for b in s.query(BudgetItem).all())
            before = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
        o = ctx.c.post('/api/budget/utility-estimate/optin', headers=ctx.HJ,
                       data=json.dumps({'kind': 'propane', 'on': True, 'lag': 0}))
        rt = (ctx.c.get('/api/budget/utility-estimate/propane', headers=ctx.HJ).get_json() or {}).get('data') or {}
        with ctx.dbs() as s:
            m = server.budget_month_amounts(s)[item_id]
            amounts2 = sorted((b.id, b.amount) for b in s.query(BudgetItem).all())
            after = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
        check('s143 F4 followed: this month\'s Propane row uses the estimate, and the route says the totals use it',
              o.status_code == 200 and m['month_source'] == 'estimate' and m['month_from'] == 'the propane estimate'
              and abs(m['month_amount'] - rt['estimate']['amount']) < 0.01 and rt['budget_uses']['in_totals'] is True
              and m['month_for'] is None)
        check('s143 F4 following it writes no budget amount and logs no budget_adjusted event',
              amounts == amounts2 and before == after)
        server.delivered_estimate = lambda session, fuel, fetch=True, today=None: real_d(session, fuel, fetch, today=dt.date(2026, 10, 3))
        server._eia_weekly_heating = lambda session, area, product, fetch=True: dict(spring)
        with ctx.dbs() as s:
            m2 = server.budget_month_amounts(s)[item_id]
        check('s143 F3 followed but out of season: the saved amount is used, never a zero, and it says why',
              m2['month_source'] == 'saved' and m2['month_amount'] == 180.0 and 'heating season' in (m2['month_why'] or ''))
        facts(heating_fuel='natural_gas')
        with ctx.dbs() as s:
            na = server.utility_applies(s, 'propane')
        check('s143 natural gas heats the home: no propane estimate, and it says why',
              na['applies'] is False and 'natural gas heats your home' in na['why'])
        facts(heating_fuel='heating_oil', heating_payment='even_monthly')
        with ctx.dbs() as s:
            ev = server.utility_applies(s, 'heating_oil')
        check('s143 a budget-plan heating oil bill does not follow the weather: no estimate, and it says so',
              ev['applies'] is False and 'same amount every month' in ev['why'])
        facts()
        with ctx.dbs() as s:
            un = server.utility_applies(s, 'propane')
        check('s143 heating fuel unanswered: the deliveries are read as heating, said, and the question asked',
              un['applies'] is True and 'heating_fuel' in un['ask'] and 'Propane deliveries' in un['assumes'])
    finally:
        server._eia_weekly_heating, server._steo, server.delivered_estimate = real_w, real_s, real_d
        ctx.c.post('/api/budget/utility-estimate/optin', headers=ctx.HJ, data=json.dumps({'kind': 'propane', 'on': False, 'lag': 0}))
        facts()
        with ctx.dbs() as s:
            for k in household.FACTS:
                s.query(HouseholdFact).filter_by(key=k).delete()
                s.query(AppSetting).filter_by(key=k).delete()
            s.query(Transaction).filter(Transaction.description == 'S143 propane delivery').delete()
            s.query(BudgetItem).filter_by(id=item_id).delete()
            s.commit()

    import ast
    callers = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)
               and any(isinstance(x, ast.Call) and getattr(x.func, 'id', None) == '_eia_weekly_heating' for x in ast.walk(n))}
    check('s143 the residential prices are fetched only by the delivered-fuel estimate (behind the Budget page)',
          callers == {'delivered_estimate'})
    # Found in the browser (2026-10-03): the cards load at once, propane and heating oil both fetch the degree days on a
    # cold cache, the second insert of the key failed - and left that request's session failed (a 500).
    real_store = server._dashboard_store
    with ctx.dbs() as s:
        s.add(AppSetting(key='s143_race', value='{}'))
        s.commit()
    try:
        server._dashboard_store = lambda session, key, value: session.add(AppSetting(key='s143_race', value='{}'))
        with ctx.dbs() as s:
            server._cache_rows(s, 's143_race', {'2026-03-30': 2.7})
            usable = s.query(AppSetting).filter_by(key='s143_race').count() == 1
    finally:
        server._dashboard_store = real_store
        with ctx.dbs() as s:
            s.query(AppSetting).filter_by(key='s143_race').delete()
            s.commit()
    check('s143 a lost race to cache an EIA series leaves the request\'s session usable (rolled back, not failed)', usable)
    check('s143 every EIA fetch caches through that one race-safe write',
          src.count('            _cache_rows(session, key, rows)\n') == 3 and 'session.commit()\n            return rows' not in src)
    check('s143 heating_fuel\'s consumer says what it now settles (propane and heating oil, from deliveries)',
          any(b == 'utility_applies' and 'propane and heating oil' in w for _a, b, w in household.FACTS['heating_fuel']['consumers']))

    node = shutil.which('node')
    check('s143 node is available to run the words (skip the next if not)', bool(node))
    if not node:
        return
    path = str(BASE.joinpath('static/js/teaching/utilitytext.js')).replace('\\', '/')
    base = {'fuel': 'propane', 'region': {'state': 'OH', 'national': False, 'division_name': 'the East North Central'},
            'area': {'kind': 'state', 'label': 'OH'}, 'saved_amount': 180, 'optin': False, 'budget_uses': {'in_totals': False}}
    cases = {
        'in': {**base, 'choice': ch, 'unpriced': 0, 'estimate': est},
        'off': {**base, 'choice': ch, 'unpriced': 4, 'estimate': off},
        'few': {**base, 'choice': {'method': 'none', 'reason': 'too_few', 'n': 1}, 'unpriced': 2,
                'estimate': {'method': 'none', 'reason': 'too_few', 'current': True, 'last_price': {'week': latest, 'price': 2.6}}},
        'flat': {**base, 'fuel': 'heating_oil', 'choice': fc, 'unpriced': 0,
                 'estimate': {'method': 'none', 'reason': fc['reason'], 'current': True, 'last_price': {'week': latest, 'price': 4.7}}},
    }
    prog = f"""
const U = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), month: m => m, date: s => s}};
const C = {json.dumps(cases)};
const o = {{}};
for (const k in C) o[k] = U[C[k].fuel](C[k], F);
console.log(JSON.stringify(o));
"""
    rr = subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8', timeout=30)
    try:
        o = json.loads(rr.stdout.strip().splitlines()[-1])
    except Exception:                                   # noqa: BLE001 - reported below
        o = {}
        print('        node:', rr.stderr[:300])
    words = lambda k: ' '.join((o.get(k) or {}).get('lines', [])) + ' ' + ((o.get(k) or {}).get('statement') or '')  # noqa: E731
    check('s143 in season: the card shows the fit, the gallons at EIA\'s latest residential price, and the stated limit',
          'Your deliveries follow the weather' in words('in') and 'EIA\'s latest residential price, $2.60/gal' in words('in')
          and 'partial fill breaks that' in words('in'))
    check('s143 the report statement is EIA\'s residential propane price, credited to the Budget page\'s estimate',
          (o.get('in') or {}).get('statement', '').startswith('EIA\'s latest weekly residential propane price for your state is $2.60/gal'))
    check('s143 F3 out of season: last season\'s price, said as last season\'s, no estimate, no statement, no zero',
          'is last season\'s price, so there is no estimate for this month' in words('off')
          and (o.get('off') or {}).get('statement') is None and '$0.00' not in words('off')
          and '4 deliveries had no EIA residential price within two weeks' in words('off'))
    check('s143 too few: it says how many deliveries can be compared and that three are needed',
          '1 of your deliveries can be compared so far; 3 are needed' in words('few') and (o.get('few') or {}).get('statement') is None)
    check('s143 a declined fit says which test it failed, for heating oil, and never names propane',
          ('not enough evidence' in words('flat') or 'too little to estimate' in words('flat'))
          and 'propane' not in words('flat') and 'Heating Oil budget' in words('flat'))
    ut = BASE.joinpath('static/js/teaching/utility.js').read_text(encoding='utf-8')
    hh = BASE.joinpath('static/js/teaching/household.js').read_text(encoding='utf-8')
    check('s143 the Budget page has a card for each (paid on delivery: no billing-lag choice)',
          "{ kind: 'propane', title: 'Propane estimate', id: 'gwPropaneEstimate', noLag: true }" in ut
          and "{ kind: 'heating_oil', title: 'Heating oil estimate', id: 'gwOilEstimate', noLag: true }" in ut)
    check('s143 onboarding\'s summary no longer says propane or heating oil is not priced',
          'heats your home: your \'\n          + \'Budget page can estimate it from your deliveries' in hh)
