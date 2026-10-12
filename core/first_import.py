"""Item 65 W1 (gw 2.0/AGENT_W_ITEMS.md, ruled 2026-10-12): patterns a long history shows, asked about, never assumed.

Arithmetic over what it is handed - no database, no clock, nothing stored. The server gathers the record, shows each
finding with its records and asks "Is this a regular bill?" / "Does this happen every year?"; only the person's answer
is kept (W1-b), and only a yes changes anything (a yearly bill on the calendar, a known cost in the futures).

  W1-a  both rules were simulated against trend-free and realistic synthetic years first (scripts/w1_null_model.py)
  W1-c  under MIN_MONTHS complete months of history it says so, and finds nothing
"""
import math
from datetime import date
from statistics import mean, median, pstdev

MIN_MONTHS = 10
# yearly / twice-yearly: every gap between the payee's charges fits one rhythm, and the amounts agree
RHYTHMS = (('yearly', 355, 375, 12), ('twice a year', 176, 189, 6))
AMOUNT_TOL = 0.15
# a payee with everyday spending is not a bill: two coffees a year apart are a coincidence, not a renewal
EVERYDAY = {'groceries', 'food', 'restaurant', 'restaurants', 'fast food / takeout', 'fastfood', 'coffee shops',
            'gas', 'gas / fuel', 'shopping', 'clothing', 'personal', 'other', 'household supplies', 'entertainment',
            'hobbies', 'hobby', 'gifts', 'work lunches', 'parking / tolls', 'rideshare / transit', 'atm', 'transfer',
            'refund', 'interest', 'interest / fees', 'fees', 'debt', 'savings', 'income', 'beauty', 'personal care'}
GRACE = 20                  # days of slack before a missing renewal counts against the rhythm
SLACK = 6                   # days each of several gaps may wander, when their middle gap is in the window
# heavy months (W1 null model): one year cannot tell a heavy month from an ordinary bumpy one - the single-year rule
# flagged 5-26% of trend-free years and found a real +40% December only 20-55% of the time. A month that runs high
# EVERY year can be seen: the same month heavy in each of two or more full years.
HEAVY_SHARE = 0.20          # at least 20% above the year's median month, on average over the years ...
HEAVY_Z = 3.5               # ... and its average over the years 3.5 robust deviations above the twelve months' averages
HEAVY_YEARS = 2
EVERY_YEAR = 0.15          # and at least 10% above its year's middle month in every year, so one freak year can't carry it


def complete_months(dates):
    """The calendar months the record fully covers: from the first whole month after the first record through the
    last whole month before the last. A partial month is not a small month (absence is not zero)."""
    if not dates:
        return []
    lo, hi = min(dates), max(dates)
    y, m = (lo.year, lo.month + 1) if lo.day > 1 else (lo.year, lo.month)
    if m == 13:
        y, m = y + 1, 1
    out = []
    while True:
        nxt = date(y + (m == 12), m % 12 + 1, 1)
        if nxt > hi:
            break
        out.append(f'{y}-{m:02d}')
        y, m = nxt.year, nxt.month
    return out


def renewals(by_payee, categories=None, history=None):
    """Payees charged yearly or twice a year: [{payee, rhythm, amount, months, day, records}].
    `by_payee` {payee: [(date, amount)]} over the whole history; `history` its (first, last) dates. A rhythm the
    history contradicts is not one: when the record runs on past the next charge's date (plus GRACE days) and it never
    came, the charges were a coincidence (or the bill stopped - either way, nothing is coming). The start is not
    checked: a bill begins some time, and a new policy in a long record is still a yearly bill."""
    out = []
    for payee, xs in by_payee.items():
        if (categories or {}).get(payee, '').strip().lower() in EVERYDAY:
            continue
        xs = sorted((d, round(abs(float(a)), 2)) for d, a in xs if d and a)
        if not 2 <= len(xs) <= 4:
            continue
        gaps = [(b[0] - a[0]).days for a, b in zip(xs, xs[1:])]
        amts = [a for _, a in xs]
        mid = median(amts)
        if mid <= 0 or any(abs(a - mid) / mid > AMOUNT_TOL for a in amts):
            continue
        for name, lo, hi, every in RHYTHMS:
            # one gap must sit in the window; several may each wander SLACK days if their middle one sits in it
            fits = (lo <= gaps[0] <= hi) if len(gaps) == 1 else (
                lo <= median(gaps) <= hi and all(lo - SLACK <= g <= hi + SLACK for g in gaps))
            if fits:
                if history and (history[1] - xs[-1][0]).days > hi + GRACE:
                    continue
                months = sorted({((xs[-1][0].month - 1 + k * every) % 12) + 1 for k in range(12 // every)})
                out.append({'payee': payee, 'rhythm': name, 'amount': round(mid, 2), 'months': months,
                            'day': int(median(d.day for d, _ in xs)),
                            'records': [{'date': d.isoformat(), 'amount': a} for d, a in xs]})
                break
    return sorted(out, key=lambda f: -f['amount'])


def heavy_months(totals):
    """Months of the year that ran heavy in every full year on record: [{month (1-12), years: [{month, total, median,
    over}], over}]. `totals` {YYYY-MM: spending} over complete months only. The years are 12-month blocks counted back
    from the newest complete month, so each is whole; fewer than HEAVY_YEARS blocks and nothing can be seen."""
    keys = sorted(totals)
    blocks = [keys[len(keys) - 12 * (b + 1):len(keys) - 12 * b] for b in range(len(keys) // 12)]
    if len(blocks) < HEAVY_YEARS:
        return []
    # each month's distance from its own year's middle month, in logs; then each month of the year's average over
    # the years, judged against how much all twelve averages spread (pooled - a heavy month need not clear the bar
    # alone in a noisy year, but it must stand above its year's middle month in every one)
    per = {}
    for blk in blocks:
        mid = median(totals[k] for k in blk)
        if mid <= 0 or any(totals[k] <= 0 for k in blk):
            return []
        for k in blk:
            per.setdefault(int(k[5:7]), []).append({'month': k, 'total': round(totals[k], 2), 'median': round(mid, 2),
                                                    'over': round(totals[k] - mid, 2), 'log': math.log(totals[k] / mid)})
    avg = {m: sum(y['log'] for y in ys) / len(ys) for m, ys in per.items()}
    out = []
    for m, a in sorted(avg.items()):
        ys = per[m]
        # one month's spread, from every OTHER month on record (the month judged is never its own yardstick)
        rest = [y['log'] for k, zs in per.items() if k != m for y in zs]
        spread = pstdev(rest)
        if spread <= 0:
            continue
        if (math.exp(a) >= 1 + HEAVY_SHARE and (a - mean(rest)) * math.sqrt(len(ys)) / spread >= HEAVY_Z
                and all(y['over'] >= EVERY_YEAR * y['median'] for y in ys)):
            years = sorted(({k: v for k, v in y.items() if k != 'log'} for y in ys), key=lambda y: y['month'])
            out.append({'month': m, 'years': years, 'over': round(median(y['over'] for y in years), 2)})
    return out


def biggest_categories(month_cats, median_cats, n=3):
    """What stood above its own usual month, biggest first: [(category, that month, usual month)]. Facts only."""
    rows = [(c, round(v, 2), round(median_cats.get(c, 0.0), 2)) for c, v in month_cats.items()
            if v - median_cats.get(c, 0.0) > 0]
    return sorted(rows, key=lambda r: -(r[1] - r[2]))[:n]


def sentence(f):
    """W1: the finding in words, from its records only. 'Geico: $612.00 on Mar 3, 2025 and $598.00 on Sep 2, 2025.'"""
    parts = [f"${r['amount']:,.2f} on {_day(r['date'])}" for r in f['records']]
    joined = parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + ' and ' + parts[-1]
    gap = 'about a year apart' if f['rhythm'] == 'yearly' else 'about six months apart'
    return f"{f['payee']}: {joined}, {gap}."


def _day(iso):
    x = date.fromisoformat(iso)
    return f"{x.strftime('%b')} {x.day}, {x.year}"
