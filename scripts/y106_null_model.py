"""Item 106 null model (gw 2.0/YEARLY_PRICE_STEPS.md section 4), run before the rule shipped, as W2's was.

Seeded synthetic charge histories through core/yearly_steps.py. The bar (section 4):
  - no more than 2% false yearly projections on any series without a yearly pattern;
  - yearly steps of 2% or more found at least 95% of the time with 2+ steps in the history (said, and asked about),
    and projected at least 95% of the time with 3+.
Measured on the way (section 7): two unrelated price changes land a year apart on 4-7% of series, so a projection
needs MIN_PROJECT (3) steps; two are said as a fact and asked about.
Also printed, not barred: steps of 1-2%, and how far the projection lands from the true next price.

The last line is PASS or FAIL, for s252 to read. Usage: python3 scripts/y106_null_model.py [series_per_row]
"""
import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import yearly_steps as ys   # noqa: E402

START = date(2021, 1, 1)


def _monthly(rnd, months, price_at, odd=0.03, cents_noise=0.003):
    """A monthly charge on a fixed day, with odd charges (prorated or a fee) and tax-rounding noise."""
    day = rnd.randint(1, 28)
    out = []
    for i in range(months):
        y, m = START.year + i // 12, i % 12 + 1
        d = date(y, m, day) + timedelta(days=rnd.randint(-2, 2))
        p = price_at(i)
        if rnd.random() < odd:
            a = p * rnd.uniform(0.3, 1.6)
        else:
            a = p * (1 + rnd.uniform(-cents_noise, cents_noise))
        out.append((d, round(a, 2)))
    return out


def _yearly_steps_fn(rnd, base, month_of_year, rate, sd, jitter):
    """Price at month i, stepping each year, each step within a month of the year before's, by about `rate`."""
    steps, mo = {}, month_of_year
    for y in range(1, 8):                     # from the second year: the old price has its charges first
        if rnd.random() < jitter:             # a month early or late - against the year before (Y2's "within one month")
            mo += rnd.choice((-1, 1))
        steps[y * 12 + mo] = max(0.0, rnd.gauss(rate, sd))

    def at(i):
        p = base
        for k in sorted(steps):
            if k <= i and k > 0:
                p *= 1 + steps[k]
        return round(p, 2)
    return at, steps


def _found(info, answers=None):
    if not info:
        return None
    return ys.pattern(ys.apply_answers(info['steps'], answers or []))


def _projects(pat):
    """Would this pattern be projected ahead of the month (Y6)? The same tests as ys.projection, without the clock."""
    return bool(pat and pat['pattern'] and pat['agree'] and len(pat['steps']) >= ys.MIN_PROJECT)


def run(n):
    rnd = random.Random(1062026)
    rows, ok = [], True

    # 1. steady charges, never a step
    fp = 0
    for _ in range(n):
        base = rnd.choice([9.99, 15.49, 54.99, 79.0, 120.0, 189.5])
        info = ys.read(_monthly(rnd, rnd.randint(30, 60), lambda i: base))
        pat = _found(info)
        fp += bool(pat and pat['pattern'])
    rows.append(('steady, no step: a pattern said', fp / n, '<= 2%', fp / n <= 0.02))

    # 2. steps at random times (about one every 30 months), never yearly by design
    fp = said = 0
    for _ in range(n):
        base = rnd.choice([15.49, 54.99, 79.0, 120.0])
        months = rnd.randint(30, 60)
        cuts = sorted(i for i in range(3, months) if rnd.random() < 1 / 30)
        sizes = {c: rnd.uniform(0.03, 0.10) for c in cuts}

        def at(i, base=base, sizes=sizes):
            p = base
            for c, s in sizes.items():
                if c <= i:
                    p *= 1 + s
            return round(p, 2)
        pat = _found(ys.read(_monthly(rnd, months, at)))
        fp += _projects(pat)
        said += bool(pat and pat['pattern'])
    rows.append(('steps at random times: projected', fp / n, '<= 2%', fp / n <= 0.02))
    rows.append(('  ... two a year apart by chance, said', said / n, '(shown: a fact, then asked)', True))

    # 3. true yearly steps, monthly charges: found, by step size and how many steps the history holds
    for label, lo, hi, nsteps, barred in (('yearly 2-8%, 2 steps seen: said', 0.02, 0.08, 2, True),
                                          ('yearly 2-8%, 3 steps seen: projected', 0.02, 0.08, 3, True),
                                          ('yearly 1-2%, 2 steps seen', 0.01, 0.02, 2, False)):
        hit = agree = 0
        err = []
        for _ in range(n):
            base = rnd.choice([54.99, 79.0, 120.0, 189.5])
            moy = rnd.randint(1, 12)
            rate = rnd.uniform(lo, hi)
            at, steps = _yearly_steps_fn(rnd, base, moy, rate, rate * 0.15, 0.3)
            seen = sorted(k for k in steps if k > 0)[:nsteps]
            months = seen[-1] + rnd.randint(3, 10)
            info = ys.read(_monthly(rnd, months, at))
            pat = _found(info)
            if pat and pat['pattern'] and len(pat['steps']) >= 2 and (nsteps < 3 or _projects(pat)):
                hit += 1
                if pat['agree']:
                    agree += 1
                    nxt = sorted(k for k in steps if k > seen[-1])[0]
                    truth = at(nxt)
                    err.append(abs(info['level'] * (1 + pat['pct']) - truth) / truth)
        bar = '>= 95%' if barred else '(shown)'
        rows.append((label, hit / n, bar, (hit / n >= 0.95) if barred else True))
        if err:
            err.sort()
            rows.append((f'  projected within 1% of the true next price', sum(e <= 0.01 for e in err) / len(err),
                         f'(agree {agree / n:.0%}; median miss {err[len(err) // 2]:.2%})', True))

    # 4. a charge paid once a year
    hit = 0
    for _ in range(n):
        base = rnd.uniform(600, 1800)
        rate = rnd.uniform(0.02, 0.08)
        years = rnd.randint(3, 5)
        xs = []
        p = base
        for y in range(years):
            d = date(START.year + y, 6, 10) + timedelta(days=rnd.randint(-12, 12))
            xs.append((d, round(p, 2)))
            p *= 1 + max(0.0, rnd.gauss(rate, rate * 0.15))
        pat = _found(ys.read(xs))
        hit += bool(pat and pat['pattern'])
    rows.append(('paid once a year, 2-8%, 3-5 charges', hit / n, '>= 95%', hit / n >= 0.95))

    # 5. a usage bill never steps from the ledger (Y5)
    seasonal = [140, 180, 120, 90, 70, 85, 130, 150, 110, 80, 75, 160]
    fired = 0
    for _ in range(n):
        xs = _monthly(rnd, 48, lambda i: seasonal[i % 12] * (1 + 0.03 * (i // 12)), odd=0, cents_noise=0.15)
        fired += ys.read(xs, 'Water / Sewer') is not None
    rows.append(('usage bill read from the ledger', fired / n, '= 0%', fired == 0))

    print(f'{n} series per row')
    for label, rate, bar, passed in rows:
        print(f'  {label:45s} {rate:7.1%}  {bar:30s} {"ok" if passed else "MISS"}')
        ok = ok and passed
    print('PASS' if ok else 'FAIL')
    return ok


if __name__ == '__main__':
    sys.exit(0 if run(int(sys.argv[1]) if len(sys.argv) > 1 else 2000) else 1)
