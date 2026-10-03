"""Item 34 F2 guard (gw 2.0/FUEL_PRICING.md s7 - the results are recorded there): does a weather fit on DELIVERED fuel (propane / heating oil) beat a no-weather
estimate, on constructed data where the true consumption is known? Measurement only - no product code.

Each household: true daily use = base + k * HDD (k = 0 for a weather-free household: water heater / cooking only).
Deliveries: a 500-gal tank filled to 80%, "will-call" when it falls to 25%, plus a pre-season top-up in late summer.
Groundwork sees only each delivery's date and dollars. It can turn dollars into gallons only when EIA publishes a price
that week (October-March), and EIA's price is the STATE AVERAGE - the household's dealer charges more or less.
An interval = consecutive deliveries; gallons delivered at the later one = what was used since the earlier one.

Models, chosen as item 26's gas fit is (leave-one-out error):
    weather   gallons = b * days + k * hdd      (needs k > 0)
    null      gallons = r * days                (one daily rate: no weather)
The weather model is ACCEPTED only if its leave-one-out error beats the null's by MARGIN and k > 0.
Judged on the true use of a held-out January, priced or not.
"""
import random
import statistics as st

MONTH_HDD = [1100, 900, 750, 450, 200, 40, 10, 15, 100, 400, 700, 1000]     # an Ohio-like year
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
SEASON = {10, 11, 12, 1, 2, 3}                                              # EIA collects October-March
TANK, FULL, LOW = 500.0, 400.0, 125.0


def daily_hdd(rng, years):
    out = []
    for _ in range(years):
        for m in range(12):
            month_scale = rng.uniform(0.85, 1.15)
            for _ in range(DAYS[m]):
                out.append((m + 1, max(0.0, MONTH_HDD[m] / DAYS[m] * month_scale * rng.uniform(0.5, 1.5))))
    return out


def household(rng, weather, years=6):
    kind = weather if isinstance(weather, str) else ('heat' if weather else 'none')
    base = rng.uniform(0.3, 1.2)                                   # gal/day, all year
    k = {'heat': rng.uniform(0.10, 0.20), 'weak': rng.uniform(0.02, 0.05), 'none': 0.0}[kind]   # gal per HDD
    markup = rng.uniform(0.85, 1.20)                              # dealer vs EIA state average
    tank = 500.0 if kind == 'heat' else 120.0                     # water-heater/cooking homes have small tanks
    full, low = 0.8 * tank, 0.25 * tank
    local = rng.uniform(0.85, 1.15)                               # this home's weather vs the division's
    days = daily_hdd(rng, years)
    level, used, deliveries = full, 0.0, []
    behaviour = 1.0
    for i, (month, hdd) in enumerate(days):
        if i % 30 == 0:
            behaviour = rng.uniform(0.8, 1.2)                     # occupancy, thermostat, time away
        use = (base + k * hdd * local) * behaviour * rng.uniform(0.7, 1.3)
        level -= use
        used += use
        day_in_year = i % 365
        prefill = day_in_year in (235,)                           # a late-August top-up
        if level <= low or (prefill and level < 0.7 * full):
            gallons = full - level
            deliveries.append({'day': i, 'month': month, 'gallons': gallons * rng.uniform(0.98, 1.02)})
            level = full
    return {'base': base, 'k': k, 'markup': markup, 'days': days, 'deliveries': deliveries}


def observed_intervals(h, rng):
    """What Groundwork can see: intervals ending in a PRICED delivery, gallons estimated as dollars / EIA price."""
    out = []
    d = h['deliveries']
    for a, b in zip(d, d[1:]):
        if b['month'] not in SEASON:
            continue                                               # no EIA price that week: not converted
        span = h['days'][a['day'] + 1:b['day'] + 1]
        # dollars = true gallons * (EIA * markup); Groundwork divides by EIA -> gallons * markup (plus weekly noise)
        est_gal = b['gallons'] * h['markup'] * rng.uniform(0.97, 1.03)
        # Groundwork knows only the DIVISION's monthly HDD (EIA STEO), spread evenly over each month's days
        hdd_model = sum(MONTH_HDD[x[0] - 1] / DAYS[x[0] - 1] for x in span)
        out.append({'days': len(span), 'hdd': hdd_model, 'gal': est_gal})
    return out


def fit_weather(iv):
    # least squares gal = b*days + k*hdd, no intercept
    sdd = sum(x['days'] ** 2 for x in iv); shh = sum(x['hdd'] ** 2 for x in iv); sdh = sum(x['days'] * x['hdd'] for x in iv)
    sdg = sum(x['days'] * x['gal'] for x in iv); shg = sum(x['hdd'] * x['gal'] for x in iv)
    det = sdd * shh - sdh * sdh
    if abs(det) < 1e-9:
        return None
    b = (sdg * shh - shg * sdh) / det
    k = (sdd * shg - sdh * sdg) / det
    return b, k


def fit_null(iv):
    return sum(x['gal'] for x in iv) / max(1, sum(x['days'] for x in iv))


def loo(iv, kind):
    errs = []
    for i in range(len(iv)):
        rest = iv[:i] + iv[i + 1:]
        x = iv[i]
        if kind == 'weather':
            f = fit_weather(rest)
            if not f:
                return None
            pred = f[0] * x['days'] + f[1] * x['hdd']
        else:
            pred = fit_null(rest) * x['days']
        errs.append(abs(pred - x['gal']) / max(1.0, x['gal']))
    return st.mean(errs)


def run(n_target, weather, trials, margin, rng):
    acc = 0; err_w = []; err_n = []; err_chosen = []; usable = 0
    for _ in range(trials):
        h = household(rng, weather)
        iv = observed_intervals(h, rng)
        if len(iv) < n_target:
            continue
        iv = iv[-n_target:]
        usable += 1
        jan_hdd, jan_days = MONTH_HDD[0], 31
        truth = (h['base'] * jan_days + h['k'] * jan_hdd)   # an average January's true use
        r = fit_null(iv) / h['markup']                              # (judging the gallon figure against the truth;
        pred_null = r * jan_days                                    #  the markup is constant, so it cancels in choice)
        f = fit_weather(iv)
        lw, ln = loo(iv, 'weather'), loo(iv, 'null')
        accepted = bool(f and f[1] > 0 and lw is not None and lw < ln * (1 - margin))
        if f:
            pred_w = (f[0] * jan_days + f[1] * jan_hdd) / h['markup']
            err_w.append(abs(pred_w - truth) / truth)
        err_n.append(abs(pred_null - truth) / truth)
        if accepted:
            acc += 1
            err_chosen.append(abs(pred_w - truth) / truth)
    med = lambda xs: round(st.median(xs) * 100, 1) if xs else None
    return {'usable': usable, 'accepted_pct': round(100 * acc / usable, 1) if usable else None,
            'err_weather_med': med(err_w), 'err_null_med': med(err_n), 'err_when_accepted_med': med(err_chosen)}


def main():
    rng = random.Random(20261003)
    print('margin = weather LOO error must beat the null by this share; judged on the true January use\n')
    for margin in (0.10, 0.25):
        print(f'== margin {int(margin * 100)}%')
        print(f'{"priced intervals":>17} | {"WEATHER households: accepted":>29} {"err if accepted":>16} {"null err":>9}'
              f' | {"WEATHER-FREE: falsely accepted":>31}')
        for n in (3, 4, 5, 6, 8):
            w = run(n, True, 3000, margin, rng)
            z = run(n, False, 3000, margin, rng)
            wk = run(n, 'weak', 3000, margin, rng)
            print(f'{n:>17} | {str(w["accepted_pct"]) + "%":>29} {str(w["err_when_accepted_med"]) + "%":>16} '
                  f'{str(w["err_null_med"]) + "%":>9} | {str(z["accepted_pct"]) + "%":>31}   (usable {w["usable"]}/{z["usable"]})'
                  f' | weak: accepted {wk["accepted_pct"]}%, err {wk["err_when_accepted_med"]}% vs null {wk["err_null_med"]}%')
        print()


if __name__ == '__main__':
    main()
