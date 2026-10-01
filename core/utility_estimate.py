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
    """STEO series ids for a region: residential natural gas price ($/MCF) and heating degree days."""
    s = reg['steo_suffix']
    if kind == 'ng_price':
        return 'NGRCUUS' if s == 'US' else 'NGRCU' + s
    if kind == 'hdd':
        return 'ZWHDPUS' if s == 'US' else 'ZWHD' + s
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
