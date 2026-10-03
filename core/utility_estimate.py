"""Utility bill estimates from weather, usage and EIA prices (gw 2.0/UTILITY_ESTIMATES.md, item 26, ruled 2026-10-01).

Pure arithmetic: no database, no network. The server gathers the user's bills and EIA's Short-Term Energy Outlook
series; this module fits, tests and estimates.

    U1  the degree-day method, per user: bill = F + (B + S x HDD) x price, fitted by least squares on the user's own
        bills, each matched to its SERVICE month. The fit is used only when it beats the simple baseline - last
        year's same month x the price change - on months it was NOT fitted to (the null-model rule). Otherwise the
        baseline is used and labelled; with no year-ago bill either, there is no estimate.
    U6  any change is split into the part from price and the part from usage, so a price rise is never read as
        using more.
    U9  every state and DC maps to its census division (STEO's forecasts and degree days) and its PADD region
        (weekly gasoline). No state means U.S. series, labelled national.

Electricity (adds cooling degree days) and gasoline (fill-up gallons) are later slices (U8).
"""

# U9: every state and DC. Census divisions as STEO codes them (all nine confirmed against EIA, 2026-10-01), and
# the PADD region EIA's weekly gasoline prices use.
_DIVISIONS = {
    'NEC': ('New England', 'CT ME MA NH RI VT'),
    'MAC': ('Middle Atlantic', 'NJ NY PA'),
    'ENC': ('East North Central', 'IL IN MI OH WI'),
    'WNC': ('West North Central', 'IA KS MN MO NE ND SD'),
    'SAC': ('South Atlantic', 'DE DC FL GA MD NC SC VA WV'),
    'ESC': ('East South Central', 'AL KY MS TN'),
    'WSC': ('West South Central', 'AR LA OK TX'),
    'MTN': ('Mountain', 'AZ CO ID MT NV NM UT WY'),
    'PAC': ('Pacific', 'AK CA HI OR WA'),
}
_PADDS = {
    '1A': 'CT ME MA NH RI VT', '1B': 'DE DC MD NJ NY PA', '1C': 'FL GA NC SC VA WV',
    '2': 'IL IN IA KS KY MI MN MO NE ND SD OH OK TN WI', '3': 'AL AR LA MS NM TX',
    '4': 'CO ID MT UT WY', '5': 'AK AZ CA HI NV OR WA',
}
STATE_DIVISION = {st: code for code, (_, sts) in _DIVISIONS.items() for st in sts.split()}
STATE_PADD = {st: padd for padd, sts in _PADDS.items() for st in sts.split()}
DIVISION_NAME = {code: name for code, (name, _) in _DIVISIONS.items()}

MIN_BILLS = 8              # U1: about 8-12 bills
HEATING_HDD = 200          # a month with this many heating degree days is a heating month
MIN_HEATING = 2            # the fit needs both kinds of month to tell base use from heating use
MIN_NON_HEATING = 2
AVERAGE_MARGIN = 0.25      # the fit must cut the error of a plain average by at least a quarter


def region(state):
    """U9: the user's region, or the national one - always saying which."""
    st = (state or '').strip().upper()[:2]
    div = STATE_DIVISION.get(st)
    if not div:
        return {'state': None, 'division': None, 'division_name': 'United States', 'national': True,
                'steo_suffix': 'US', 'padd': None}
    return {'state': st, 'division': div, 'division_name': DIVISION_NAME[div], 'national': False,
            'steo_suffix': '_' + div, 'padd': STATE_PADD.get(st)}


def steo_series(kind, reg):
    """STEO series ids for a region: residential natural gas ($/MCF) and electricity (cents/kWh) prices, heating and
    cooling degree days. (All confirmed against EIA, 2026-10-01, including the national cooling series ZWCDPUS.)"""
    s = reg['steo_suffix']
    if kind == 'ng_price':
        return 'NGRCUUS' if s == 'US' else 'NGRCU' + s
    if kind == 'elec_price':
        return 'ESRCUUS' if s == 'US' else 'ESRCU' + s
    if kind == 'hdd':
        return 'ZWHDPUS' if s == 'US' else 'ZWHD' + s
    if kind == 'cdd':
        return 'ZWCDPUS' if s == 'US' else 'ZWCD' + s
    raise ValueError(kind)


def service_month(paid_month, lag=1):
    """The month a bill paid in `paid_month` ('YYYY-MM') pays for - `lag` months earlier (Rob: billed a month behind)."""
    y, m = int(paid_month[:4]), int(paid_month[5:7]) - int(lag)
    while m <= 0:
        y, m = y - 1, m + 12
    return f'{y}-{m:02d}'


def _solve3(a, b):
    """Solve a 3x3 linear system by Gaussian elimination; None when singular."""
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            return None
        m[col], m[piv] = m[piv], m[col]
        for r in range(3):
            if r != col:
                f = m[r][col] / m[col][col]
                for c in range(col, 4):
                    m[r][c] -= f * m[col][c]
    return [m[i][3] / m[i][i] for i in range(3)]


def fit(points):
    """Least squares for bill = F + B*price + S*(price*hdd). `points`: [{amount, price, hdd}]. None if it can't fit."""
    xs = [(1.0, p['price'], p['price'] * p['hdd']) for p in points]
    ys = [p['amount'] for p in points]
    ata = [[sum(x[i] * x[j] for x in xs) for j in range(3)] for i in range(3)]
    aty = [sum(x[i] * y for x, y in zip(xs, ys)) for i in range(3)]
    sol = _solve3(ata, aty)
    if sol is None:
        return None
    return {'F': sol[0], 'B': sol[1], 'S': sol[2]}


def predict(model, price, hdd):
    return model['F'] + (model['B'] + model['S'] * hdd) * price


def baseline(bills, month, price_now, prices):
    """Last year's same month x the price change. None without a bill for that month a year ago, or its price."""
    y = int(month[:4]) - 1
    prev = f'{y}{month[4:]}'
    b = next((x for x in bills if x['month'] == prev), None)
    p0 = prices.get(prev)
    if not b or not p0 or price_now is None:
        return None
    return {'amount': b['amount'] * price_now / p0, 'from_month': prev, 'from_amount': b['amount'],
            'from_price': p0, 'price': price_now}


def choose(bills, prices, hdds):
    """U1: fit, test it on months it was not fitted to, and say which method is used and why.

    The null model (run before shipping, the project's rule) showed that "beats the baseline" alone is not enough: on
    bills with no relation to weather or price, a fit wins most of the time simply by predicting the average, because
    the baseline (last year's same month x the price change) is poor too. So the fit must earn its place three ways,
    each scored leave-one-out across every bill (fit on all the others, predict the one left out):
        it beats the baseline,
        it beats a plain average of the other bills by at least AVERAGE_MARGIN,
        and its heating slope is positive (more cold, more gas) - the physical claim the method makes.
    Otherwise the baseline is used and labelled; it is the honest arithmetic Rob ruled when the fit has not earned it.

    `bills`  [{month: service month 'YYYY-MM', amount}], oldest first
    `prices` {month: $/MCF}   `hdds` {month: heating degree days}   (EIA's figures for those months)
    """
    pts = [{'month': b['month'], 'amount': b['amount'], 'price': prices.get(b['month']), 'hdd': hdds.get(b['month'])}
           for b in bills]
    pts = [p for p in pts if p['price'] is not None and p['hdd'] is not None]
    heating = sum(1 for p in pts if p['hdd'] >= HEATING_HDD)
    if len(pts) < MIN_BILLS or heating < MIN_HEATING or len(pts) - heating < MIN_NON_HEATING:
        return {'method': 'baseline', 'reason': 'not_enough_bills', 'bills': len(pts), 'heating': heating}
    whole = fit(pts)
    if whole is None:
        return {'method': 'baseline', 'reason': 'no_fit', 'bills': len(pts)}
    fit_err = base_err = avg_err = 0.0
    scored = 0
    for i, p in enumerate(pts):
        others = pts[:i] + pts[i + 1:]
        bl = baseline(bills, p['month'], p['price'], prices)
        m = fit(others)
        if not bl or m is None:
            continue
        avg = sum(o['amount'] for o in others) / len(others)
        fit_err += abs(predict(m, p['price'], p['hdd']) - p['amount'])
        base_err += abs(bl['amount'] - p['amount'])
        avg_err += abs(avg - p['amount'])
        scored += 1
    if scored == 0:
        return {'method': 'baseline', 'reason': 'no_baseline_to_test', 'bills': len(pts)}
    out = {'bills': len(pts), 'scored': scored, 'fit_error': round(fit_err / scored, 2),
           'baseline_error': round(base_err / scored, 2), 'average_error': round(avg_err / scored, 2)}
    if whole['S'] <= 0:
        return {**out, 'method': 'baseline', 'reason': 'no_heating_slope'}
    if fit_err >= base_err:
        return {**out, 'method': 'baseline', 'reason': 'fit_did_not_beat_baseline'}
    if fit_err > (1 - AVERAGE_MARGIN) * avg_err:
        return {**out, 'method': 'baseline', 'reason': 'fit_no_better_than_average'}
    return {**out, 'method': 'fit', 'model': whole, 'reason': 'earned'}


def estimate(choice, bills, month, price, hdd, prices):
    """The estimate for `month` at EIA's `price` and `hdd`, with the figures it rests on.

    A month EIA's outlook has no price or degree days for is not estimated: a missing figure is not zero (zero
    degree days would claim no heating at all) - it says what it needs.
    """
    if price is None or (choice['method'] == 'fit' and hdd is None):
        return {'method': 'none', 'month': month, 'needs': "EIA's outlook figures for that month"}
    if choice['method'] == 'fit':
        m = choice['model']
        usage = m['B'] + m['S'] * hdd
        return {'method': 'fit', 'amount': round(predict(m, price, hdd), 2), 'usage_mcf': round(usage, 2),
                'fixed': round(m['F'], 2), 'price': price, 'hdd': hdd, 'month': month}
    bl = baseline(bills, month, price, prices)
    if bl:
        return {'method': 'baseline', 'amount': round(bl['amount'], 2), 'price': price, 'month': month,
                'from_month': bl['from_month'], 'from_amount': bl['from_amount'], 'from_price': bl['from_price']}
    return {'method': 'none', 'month': month,
            'needs': 'a gas bill from the same month last year, or about eight bills across heating and non-heating months'}


def split_vs_last_year(choice, est, bills, prices, hdds):
    """U6: how the estimate differs from the SAME month last year, split into price and usage.

    Month-to-month changes are mostly the season, so comparing October with September would call the weather
    "price". The honest comparison is the same month a year earlier:
      fit       usage = B + S x HDD for each year; price part = last year's usage x the price change;
                usage part = the usage change x this year's price (the two add to the change in usage x price)
      baseline  the method assumes last year's usage, so the whole difference is price - and it says so
    None when there is no bill for that month last year.
    """
    if not est or est.get('method') in (None, 'none'):
        return None
    month = est['month']
    prev = f'{int(month[:4]) - 1}{month[4:]}'
    last = next((b for b in bills if b['month'] == prev), None)
    p0, p1 = prices.get(prev), est.get('price')
    if not last or p0 is None or p1 is None:
        return None
    if est['method'] == 'fit':
        m = choice['model']
        u0 = m['B'] + m['S'] * hdds.get(prev, 0.0)
        u1 = est['usage_mcf']
        return {'vs_month': prev, 'last_year_bill': last['amount'], 'price': round(u0 * (p1 - p0), 2),
                'usage': round((u1 - u0) * p1, 2), 'assumes_same_usage': False}
    return {'vs_month': prev, 'last_year_bill': last['amount'], 'price': round(est['amount'] - last['amount'], 2),
            'usage': 0.0, 'assumes_same_usage': True}


# ── Electricity (U8's second slice) ────────────────────────────────────────────────────────────────────────────
#
#     bill = F + (B + Sh x HDD + Sc x CDD) x price          price in $/kWh, usage in kWh
#
# Not every home heats with electricity or cools with it. A weather term whose slope comes out negative is not a
# fact about that home - it is the fit reaching for noise - so it is dropped and the fit redone; at least one weather
# slope must remain, and be positive. The same three tests as gas decide whether the fit is used, leave-one-out.

COOLING_CDD = 100          # a month with this many cooling degree days is a cooling month
TERMS = ('hdd', 'cdd')


def _solve(a, b):
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            return None
        m[col], m[piv] = m[piv], m[col]
        for r in range(n):
            if r != col:
                f = m[r][col] / m[col][col]
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    return [m[i][n] / m[i][i] for i in range(n)]


def _feats(p, terms):
    return [1.0, p['price']] + [p['price'] * p[t] for t in terms]


def fit_terms(points, terms):
    """Least squares for bill = F + B*price + sum(S_t * price * weather_t). None if it can't fit."""
    xs = [_feats(p, terms) for p in points]
    ys = [p['amount'] for p in points]
    k = len(xs[0]) if xs else 0
    if len(xs) <= k:
        return None
    ata = [[sum(x[i] * x[j] for x in xs) for j in range(k)] for i in range(k)]
    aty = [sum(x[i] * y for x, y in zip(xs, ys)) for i in range(k)]
    sol = _solve(ata, aty)
    if sol is None:
        return None
    model = {'F': sol[0], 'B': sol[1], 'terms': list(terms)}
    for t, v in zip(terms, sol[2:]):
        model['S_' + t] = v
    return model


def usage_terms(model, w):
    return model['B'] + sum(model['S_' + t] * w[t] for t in model['terms'])


def predict_terms(model, price, w):
    return model['F'] + usage_terms(model, w) * price


EXTRA_TERM_MARGIN = 0.10    # a second weather term must cut the leave-one-out error by a tenth to be kept
USAGE_REL_SE = 0.10         # the usage figure is stated only when its standard error is under a tenth of it
                            # (measured: at 15%, a few near-flat-price homes got a kWh figure 30-60% off; at 10%, none)


def _usage_identified(points, model):
    """Can the bills tell usage from the fixed charge? (Capable is not admissible.)

    bill = F + usage x price. When the price barely moves - electricity's often doesn't, month to month - F and the
    usage term trade off against each other: the bill is predicted well while the kWh figure and the fixed charge are
    not. Measured before shipping: electric bills predicted within about 1.5%, but the implied January kWh anywhere
    from a third to 1.6 times the truth. So the usage figure is stated only when the base-usage coefficient's standard
    error, from the fit's own residuals, is under USAGE_REL_SE of it.
    """
    terms = model['terms']
    xs = [_feats(p, terms) for p in points]
    k = len(xs[0])
    n = len(xs)
    if n <= k:
        return False
    resid = [p['amount'] - predict_terms(model, p['price'], p) for p in points]
    sigma2 = sum(r * r for r in resid) / (n - k)
    ata = [[sum(x[i] * x[j] for x in xs) for j in range(k)] for i in range(k)]
    unit = [1.0 if j == 1 else 0.0 for j in range(k)]
    col = _solve(ata, unit)                 # the (B, B) entry of (X'X)^-1 is col[1]
    if col is None or col[1] <= 0 or model['B'] <= 0:
        return False
    return (sigma2 * col[1]) ** 0.5 < USAGE_REL_SE * model['B']


def _loo_error(points, terms):
    """Mean absolute leave-one-out error of a fit with these terms; None if any refit fails."""
    err = 0.0
    for i, p in enumerate(points):
        m = fit_terms(points[:i] + points[i + 1:], terms)
        if m is None:
            return None
        err += abs(predict_terms(m, p['price'], p) - p['amount'])
    return err / len(points)


def _positive_terms(points):
    """Choose the weather terms: each candidate (heating and cooling, cooling only, heating only) must have positive
    slopes, and is scored leave-one-out; the simpler candidate wins unless the extra term cuts the error by
    EXTRA_TERM_MARGIN.

    Measured before shipping: with both terms always kept when positive, about one home in ten that only cools got a
    January estimate 60% or more above its true base use - winter heating it does not have, because base use and
    heating are hard to tell apart in two years of bills. Choosing the terms by held-out error removes that.
    None if no candidate has a positive slope.
    """
    best = None
    for terms in (('cdd',), ('hdd',), ('hdd', 'cdd')):
        m = fit_terms(points, list(terms))
        if m is None or any(m['S_' + t] <= 0 for t in terms):
            continue
        e = _loo_error(points, list(terms))
        if e is None:
            continue
        if best is None:
            best = (e, m)
            continue
        if len(terms) > len(best[1]['terms']):
            if e < (1 - EXTRA_TERM_MARGIN) * best[0]:
                best = (e, m)
        elif e < best[0]:
            best = (e, m)
    return best[1] if best else None


def choose_electric(bills, prices, hdds, cdds):
    """U1 for electricity: the fit is used only when it earns it, as for gas - scored leave-one-out, it must beat the
    baseline, beat a plain average by AVERAGE_MARGIN, and keep at least one positive weather slope. It needs both a
    heating and a cooling season in the record (Rob: a full year spanning summer and winter)."""
    pts = [{'month': b['month'], 'amount': b['amount'], 'price': prices.get(b['month']),
            'hdd': hdds.get(b['month']), 'cdd': cdds.get(b['month'])} for b in bills]
    pts = [p for p in pts if p['price'] is not None and p['hdd'] is not None and p['cdd'] is not None]
    heating = sum(1 for p in pts if p['hdd'] >= HEATING_HDD)
    cooling = sum(1 for p in pts if p['cdd'] >= COOLING_CDD)
    if len(pts) < MIN_BILLS or heating < MIN_HEATING or cooling < MIN_HEATING:
        return {'method': 'baseline', 'reason': 'not_enough_bills', 'bills': len(pts), 'heating': heating, 'cooling': cooling}
    whole = _positive_terms(pts)
    if whole is None:
        return {'method': 'baseline', 'reason': 'no_weather_slope', 'bills': len(pts)}
    terms = whole['terms']
    fit_err = base_err = avg_err = 0.0
    scored = 0
    for i, p in enumerate(pts):
        others = pts[:i] + pts[i + 1:]
        bl = baseline(bills, p['month'], p['price'], prices)
        m = fit_terms(others, terms)
        if not bl or m is None:
            continue
        avg = sum(o['amount'] for o in others) / len(others)
        fit_err += abs(predict_terms(m, p['price'], p) - p['amount'])
        base_err += abs(bl['amount'] - p['amount'])
        avg_err += abs(avg - p['amount'])
        scored += 1
    if scored == 0:
        return {'method': 'baseline', 'reason': 'no_baseline_to_test', 'bills': len(pts)}
    out = {'bills': len(pts), 'scored': scored, 'terms': terms, 'fit_error': round(fit_err / scored, 2),
           'baseline_error': round(base_err / scored, 2), 'average_error': round(avg_err / scored, 2)}
    if fit_err >= base_err:
        return {**out, 'method': 'baseline', 'reason': 'fit_did_not_beat_baseline'}
    if fit_err > (1 - AVERAGE_MARGIN) * avg_err:
        return {**out, 'method': 'baseline', 'reason': 'fit_no_better_than_average'}
    return {**out, 'method': 'fit', 'model': whole, 'reason': 'earned', 'usage_identified': _usage_identified(pts, whole)}


def estimate_electric(choice, bills, month, price, hdd, cdd, prices):
    """The electricity estimate for `month`: price in $/kWh. A month without EIA's figures is not estimated."""
    if price is None or (choice['method'] == 'fit' and (hdd is None or cdd is None)):
        return {'method': 'none', 'month': month, 'needs': "EIA's outlook figures for that month"}
    if choice['method'] == 'fit':
        m = choice['model']
        w = {'hdd': hdd, 'cdd': cdd}
        out = {'method': 'fit', 'amount': round(predict_terms(m, price, w), 2), 'price': price, 'hdd': hdd, 'cdd': cdd,
               'month': month, 'terms': m['terms'], 'usage_identified': bool(choice.get('usage_identified'))}
        if out['usage_identified']:
            out.update(usage_kwh=round(usage_terms(m, w), 1), fixed=round(m['F'], 2))
        return out
    bl = baseline(bills, month, price, prices)
    if bl:
        return {'method': 'baseline', 'amount': round(bl['amount'], 2), 'price': price, 'month': month,
                'from_month': bl['from_month'], 'from_amount': bl['from_amount'], 'from_price': bl['from_price']}
    return {'method': 'none', 'month': month,
            'needs': 'an electric bill from the same month last year, or about eight bills across a summer and a winter'}


def split_electric(choice, est, bills, prices, hdds, cdds):
    """U6 for electricity, against the same month last year: price (last year's kWh x the price change) and usage."""
    if not est or est.get('method') in (None, 'none'):
        return None
    month = est['month']
    prev = f'{int(month[:4]) - 1}{month[4:]}'
    last = next((b for b in bills if b['month'] == prev), None)
    p0, p1 = prices.get(prev), est.get('price')
    if not last or p0 is None or p1 is None:
        return None
    if est['method'] == 'fit' and not est.get('usage_identified'):
        # The bills can't tell usage from price yet, so the change is stated whole - never split by a guess.
        return {'vs_month': prev, 'last_year_bill': last['amount'], 'change': round(est['amount'] - last['amount'], 2),
                'price': None, 'usage': None, 'unsplit': True, 'assumes_same_usage': False}
    if est['method'] == 'fit':
        m = choice['model']
        u0 = usage_terms(m, {'hdd': hdds.get(prev, 0.0), 'cdd': cdds.get(prev, 0.0)})
        u1 = est['usage_kwh']
        return {'vs_month': prev, 'last_year_bill': last['amount'], 'price': round(u0 * (p1 - p0), 2),
                'usage': round((u1 - u0) * p1, 2), 'assumes_same_usage': False}
    return {'vs_month': prev, 'last_year_bill': last['amount'], 'price': round(est['amount'] - last['amount'], 2),
            'usage': 0.0, 'assumes_same_usage': True}


# ── Gasoline (U8's third slice): no weather - gallons from the user's own fill-ups ───────────────────────────────
#
# Each fill-up (a debit in Gas / Fuel) divided by EIA's weekly retail price for that week, in the user's area, gives
# the gallons bought - at the area's AVERAGE price, which the card says, because what the user paid at the pump is
# not in the record. A month's gallons are summed; the typical month is the median of the last six complete months
# that have fill-ups (a month without one may be a month without driving, or a month paid in cash - it is absent,
# never zero). The estimate is typical gallons x EIA's latest weekly price. Intraday pump swings don't matter at a
# monthly budget; gallons are the variable (Rob, 2026-09-28). Finding the cheapest station is GasBuddy's job.

# EIA publishes a weekly series for these states; everywhere else uses its PADD region (all confirmed, 2026-10-01).
WEEKLY_GAS_STATES = {'CA', 'CO', 'FL', 'MA', 'MN', 'NY', 'OH', 'TX', 'WA'}
PADD_AREA = {'1A': 'R1X', '1B': 'R1Y', '1C': 'R1Z', '2': 'R20', '3': 'R30', '4': 'R40', '5': 'R50'}
PADD_NAME = {'1A': 'New England', '1B': 'Central Atlantic', '1C': 'Lower Atlantic', '2': 'the Midwest',
             '3': 'the Gulf Coast', '4': 'the Rocky Mountains', '5': 'the West Coast'}
MIN_FUEL_MONTHS = 3
TYPICAL_OF = 6
PRICE_MATCH_DAYS = 14       # a fill-up with no weekly price within two weeks is not converted (gallons unknown)


def gasoline_area(reg):
    """EIA's weekly area for the user: their own state when EIA publishes one, else their PADD, else the U.S."""
    st = reg.get('state')
    if st in WEEKLY_GAS_STATES:
        return {'duoarea': 'S' + st, 'label': st, 'kind': 'state'}
    padd = reg.get('padd')
    if padd in PADD_AREA:
        return {'duoarea': PADD_AREA[padd], 'label': PADD_NAME[padd] + ' (PADD ' + padd + ')', 'kind': 'padd'}
    return {'duoarea': 'NUS', 'label': 'the U.S.', 'kind': 'national'}


# Diesel (item 34 F1, FUEL_PRICING.md): EIA's weekly No. 2 on-highway diesel price is published for the U.S., each PADD
# region and California alone among states (measured 2026-10-03). Everyone else uses their PADD region.
WEEKLY_DIESEL_STATES = {'CA'}
EIA_PRODUCT = {'gasoline': 'EPMR', 'diesel': 'EPD2D'}


def diesel_area(reg):
    """EIA's weekly diesel area for the user: California's own series, else their PADD, else the U.S."""
    st = reg.get('state')
    if st in WEEKLY_DIESEL_STATES:
        return {'duoarea': 'S' + st, 'label': st, 'kind': 'state'}
    padd = reg.get('padd')
    if padd in PADD_AREA:
        return {'duoarea': PADD_AREA[padd], 'label': PADD_NAME[padd] + ' (PADD ' + padd + ')', 'kind': 'padd'}
    return {'duoarea': 'NUS', 'label': 'the U.S.', 'kind': 'national'}


def _week_price(day, weekly):
    """EIA's price for the week a fill-up fell in: the latest weekly period on or before it, within PRICE_MATCH_DAYS."""
    from datetime import date as _d
    best = None
    for period in weekly:
        if period <= day and (best is None or period > best):
            best = period
    if best is None:
        return None
    gap = (_d.fromisoformat(day) - _d.fromisoformat(best)).days
    return weekly[best] if gap <= PRICE_MATCH_DAYS else None


def fuel_months(fillups, weekly, current_month):
    """Gallons per complete month, from fill-ups at the week's average price. {month: {gallons, spent, fillups}}."""
    out = {}
    for f in fillups:
        m = f['date'][:7]
        if m >= current_month:
            continue
        price = _week_price(f['date'], weekly)
        if not price:
            continue
        row = out.setdefault(m, {'gallons': 0.0, 'spent': 0.0, 'fillups': 0})
        row['gallons'] += f['amount'] / price
        row['spent'] += f['amount']
        row['fillups'] += 1
    return {m: {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()} for m, r in sorted(out.items())}


def estimate_gasoline(months, weekly):
    """Typical monthly gallons x EIA's latest weekly price, with the figures; or what it needs."""
    if not weekly:
        return {'method': 'none', 'needs': "EIA's weekly gasoline prices"}
    latest = max(weekly)
    recent = list(months.items())[-TYPICAL_OF:]
    if len(recent) < MIN_FUEL_MONTHS:
        return {'method': 'none', 'months': len(recent),
                'needs': 'fill-ups in at least three months (Gas / Fuel purchases in your ledger)'}
    gal = sorted(r['gallons'] for _, r in recent)
    typical = gal[len(gal) // 2] if len(gal) % 2 else (gal[len(gal) // 2 - 1] + gal[len(gal) // 2]) / 2
    price = weekly[latest]
    year_ago = None
    from datetime import date as _d, timedelta as _td
    target = (_d.fromisoformat(latest) - _td(days=364)).isoformat()
    then = _week_price(target, weekly)
    if then:
        # U6: price only - the same typical gallons at last year's price; usage is held at the typical month.
        year_ago = {'week': target, 'price': then, 'amount': round(typical * then, 2),
                    'price_part': round(typical * (price - then), 2)}
    return {'method': 'gallons', 'amount': round(typical * price, 2), 'gallons': round(typical, 1), 'price': price,
            'week': latest, 'months_used': [m for m, _ in recent], 'year_ago': year_ago}


# ── Delivered fuels: propane and heating oil (item 34 F2-F4, FUEL_PRICING.md) ───────────────────────────────────────
# EIA's weekly RESIDENTIAL price (petroleum/pri/wfr, process PRS - not the wholesale PWR figures in the same series),
# collected weekly October to March (and, in 2024 and April-May 2025, one summer week a month - measured 2026-10-03, so
# the calendar is not the rule: the price evidence is). Residential coverage measured 2026-10-03 for the 2025-26 season.
PROPANE_STATES = set('AL AR CO CT DE FL GA IA ID IL IN KS KY MA MD ME MI MN MO MS MT NC ND NE NH NJ NY OH OK PA RI SD '
                     'TN TX UT VA VT WI'.split())
HEATING_OIL_STATES = set('CT DC DE IA IN KY MA MD ME MI MN NC NE NH NJ NY OH PA RI VA VT WI'.split())
DELIVERED_PRODUCT = {'propane': 'EPLLPA', 'heating_oil': 'EPD2F'}
_DELIVERED_PADDS = {'propane': {'1A', '1B', '1C', '2', '3', '4'}, 'heating_oil': {'1A', '1B', '1C', '2'}}

# The acceptance rule the F2 guard's simulation supports (FUEL_PRICING.md s7, delivered_fuel_sim.py): attempt from
# three priced intervals; accept the weather fit only if it beats one daily rate by 25% held-out, k > 0, and the
# weather explains at least 30% of a year's use. Otherwise: insufficient evidence - no estimate.
MIN_DELIVERED_INTERVALS = 3
DELIVERED_MARGIN = 0.25
WEATHER_SHARE_FLOOR = 0.30


def delivered_area(reg, fuel):
    """EIA's weekly residential area for a delivered fuel: the state's own series, else its PADD, else the U.S."""
    st = reg.get('state')
    if st in (PROPANE_STATES if fuel == 'propane' else HEATING_OIL_STATES):
        return {'duoarea': 'S' + st, 'label': st, 'kind': 'state'}
    padd = reg.get('padd')
    if padd in _DELIVERED_PADDS[fuel]:
        return {'duoarea': PADD_AREA[padd], 'label': PADD_NAME[padd] + ' (PADD ' + padd + ')', 'kind': 'padd'}
    return {'duoarea': 'NUS', 'label': 'the U.S.', 'kind': 'national'}


def _days_in(month):
    import calendar
    y, m = (int(x) for x in month.split('-'))
    return calendar.monthrange(y, m)[1]


def delivered_intervals(deliveries, weekly, hdds):
    """Intervals between consecutive deliveries, gallons from the LATER delivery's dollars at that week's EIA price.

    A delivery with no EIA price within two weeks (a summer fill) is not converted - it still marks the start of the
    next interval. An interval whose days fall in a month without degree days is not usable. Returns (intervals,
    unpriced count)."""
    import datetime as _dt
    out, unpriced = [], 0
    ds = sorted(deliveries, key=lambda x: x['date'])
    for a, b in zip(ds, ds[1:]):
        price = _week_price(b['date'], weekly)
        if price is None:
            unpriced += 1
            continue
        d0, d1 = _dt.date.fromisoformat(a['date']), _dt.date.fromisoformat(b['date'])
        days = (d1 - d0).days
        if days <= 0:
            continue
        hdd, ok = 0.0, True
        day = d0 + _dt.timedelta(days=1)
        while day <= d1:
            m = day.strftime('%Y-%m')
            if hdds.get(m) is None:
                ok = False
                break
            hdd += hdds[m] / _days_in(m)
            day += _dt.timedelta(days=1)
        if ok:
            out.append({'from': a['date'], 'to': b['date'], 'days': days, 'hdd': hdd,
                        'gallons': b['amount'] / price, 'price': price})
    return out, unpriced


def _fit_bk(iv):
    sdd = sum(x['days'] ** 2 for x in iv); shh = sum(x['hdd'] ** 2 for x in iv); sdh = sum(x['days'] * x['hdd'] for x in iv)
    sdg = sum(x['days'] * x['gallons'] for x in iv); shg = sum(x['hdd'] * x['gallons'] for x in iv)
    det = sdd * shh - sdh * sdh
    if abs(det) < 1e-9:
        return None
    return (sdg * shh - shg * sdh) / det, (sdd * shg - sdh * sdg) / det


def _rate(iv):
    return sum(x['gallons'] for x in iv) / max(1, sum(x['days'] for x in iv))


def _loo(iv, weather):
    errs = []
    for i, x in enumerate(iv):
        rest = iv[:i] + iv[i + 1:]
        if weather:
            f = _fit_bk(rest)
            if not f:
                return None
            pred = f[0] * x['days'] + f[1] * x['hdd']
        else:
            pred = _rate(rest) * x['days']
        errs.append(abs(pred - x['gallons']) / max(1.0, x['gallons']))
    return sum(errs) / len(errs)


def choose_delivered(intervals, year_hdd):
    """The F2 rule. {'method': 'weather', 'base', 'k', 'n', 'held_out_error', 'weather_share'} or
    {'method': 'none', 'reason', 'n', ...}: never a forced fit."""
    n = len(intervals)
    if n < MIN_DELIVERED_INTERVALS:
        return {'method': 'none', 'reason': 'too_few', 'n': n}
    f = _fit_bk(intervals)
    lw, ln = _loo(intervals, True), _loo(intervals, False)
    if not f or lw is None:
        return {'method': 'none', 'reason': 'no_fit', 'n': n}
    b, k = f
    heat = k * year_hdd
    total = heat + b * 365
    share = heat / total if total > 0 else 0.0
    if k <= 0:
        return {'method': 'none', 'reason': 'no_heating_slope', 'n': n}
    if not lw < ln * (1 - DELIVERED_MARGIN):
        return {'method': 'none', 'reason': 'no_better_than_average', 'n': n,
                'held_out_error': round(lw, 3), 'average_error': round(ln, 3)}
    if share < WEATHER_SHARE_FLOOR:
        return {'method': 'none', 'reason': 'weather_share_too_small', 'n': n, 'weather_share': round(share, 3)}
    return {'method': 'weather', 'base': round(b, 4), 'k': round(k, 5), 'n': n, 'held_out_error': round(lw, 3),
            'average_error': round(ln, 3), 'weather_share': round(share, 3)}


def estimate_delivered(choice, month, hdd_month, weekly, today):
    """This month's use at EIA's latest residential price - only while that price is current (F3: within two weeks).

    With no price from the last two weeks there is no estimate: the latest price is reported with its week, marked
    'last' when it is from before this heating season (which starts 1 October), never as this month's, never a zero."""
    import datetime as _dt
    latest = max(weekly) if weekly else None
    start = _dt.date(today.year if today.month >= 10 else today.year - 1, 10, 1)
    last = ({'week': latest, 'price': weekly[latest], 'season': 'last' if latest < start.isoformat() else 'this'}
            if latest else None)
    current = latest is not None and (today - _dt.date.fromisoformat(latest)).days <= PRICE_MATCH_DAYS
    if choice.get('method') != 'weather':
        return {'method': 'none', 'reason': choice.get('reason'), 'last_price': last, 'current': current}
    if not current:
        return {'method': 'none', 'reason': 'out_of_season', 'last_price': last, 'current': False}
    if hdd_month is None:
        return {'method': 'none', 'reason': 'no_degree_days', 'last_price': last, 'current': True}
    gallons = choice['base'] * _days_in(month) + choice['k'] * hdd_month
    return {'method': 'weather', 'month': month, 'gallons': round(gallons, 1), 'price': last['price'],
            'week': latest, 'amount': round(gallons * last['price'], 2), 'hdd': hdd_month, 'current': True}
