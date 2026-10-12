"""Item 65 W2-a: the price-step rule against synthetic charges before it ships (AGENT_W_ITEMS.md, "W2 null model").

Trend-free series must almost never fire; real steps on steady charges must almost always be found.
Run: python scripts/w2_null_model.py   (deterministic, seeded)
"""
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.price_change import step  # noqa: E402

N = 4000
START = date(2025, 10, 9)


def monthly(n, f):
    return [(START + timedelta(days=30 * i + random.randint(-2, 2)), f(i)) for i in range(n)]


def weekly(n, f):
    return [(START + timedelta(days=7 * i + random.randint(-1, 1)), f(i)) for i in range(n)]


def run(name, make, category='', want=False):
    hit = sum(1 for _ in range(N) if (step(make(), category) is not None))
    rate = hit / N
    print(f"  {'FOUND' if want else 'FALSE'} {rate:6.1%}  {name}")
    return rate


random.seed(65)
print('Trend-free (any hit is a false alarm):')
fa = []
fa.append(run('steady subscription, 12 months, exact price',
              lambda: monthly(12, lambda i: 15.49)))
fa.append(run('steady subscription with tax / exchange jitter (+-1%)',
              lambda: monthly(12, lambda i: round(15.49 * (1 + random.uniform(-.01, .01)), 2))))
fa.append(run('steady, with one odd charge (prorated / refund-adjusted) somewhere',
              lambda: (lambda k: monthly(12, lambda i: 15.49 * (random.choice((.5, 1.3, .7)) if i == k else 1)))(random.randrange(12))))
fa.append(run('steady, with TWO odd charges apart',
              lambda: (lambda ks: monthly(12, lambda i: 40.0 * (random.choice((.5, 1.4)) if i in ks else 1)))(random.sample(range(12), 2))))
fa.append(run('usage bill: seasonal +-25% and 10% noise', lambda: monthly(
    12, lambda i: round(120 * (1 + .25 * math.cos(2 * math.pi * (i + random.random()) / 12)) * random.gauss(1, .10), 2)), 'Utilities'))
fa.append(run('usage bill: seasonal +-40% and 15% noise', lambda: monthly(
    12, lambda i: round(90 * (1 + .40 * math.cos(2 * math.pi * i / 12)) * random.gauss(1, .15), 2)), 'Utilities'))
fa.append(run('variable spending, weekly (groceries, 35% lognormal)',
              lambda: weekly(40, lambda i: round(110 * math.exp(random.gauss(0, .35)), 2))))
fa.append(run('variable spending, monthly (25% lognormal)',
              lambda: monthly(12, lambda i: round(60 * math.exp(random.gauss(0, .25)), 2))))
fa.append(run('steady subscription, only 6 months of history',
              lambda: monthly(6, lambda i: round(9.99 * (1 + random.uniform(-.01, .01)), 2))))

print('\nReal steps (should be found):')
fd = []


def stepped(base, up, after, n=12, jitter=.01):
    k = n - after
    return monthly(n, lambda i: round(base * (1 + (up if i >= k else 0)) * (1 + random.uniform(-jitter, jitter)), 2))


for up in (.05, .08, .10, .16, .25, -.10):
    for after in (2, 3, 6):
        fd.append((up, after, run(f'step {up:+.0%}, {after} charges since', lambda: stepped(15.49, up, after), want=True)))
fd.append((.10, 3, run('step +10%, 3 since, after a prorated first charge and one odd month', lambda: (lambda xs: [(d, a * (.4 if i == 0 else 1.3 if i == 5 else 1)) for i, (d, a) in enumerate(xs)])(stepped(15.49, .10, 3)), want=True)))
print('\nTrend (a slow drift is not a step; reported, not judged):')
run('usage price drifting up 1% a month, 10% noise', lambda: monthly(
    12, lambda i: round(100 * 1.01 ** i * random.gauss(1, .1), 2)), 'Utilities')

worst = max(fa)
big = [r for up, a, r in fd if abs(up) >= .08]
print(f"\nWorst false-alarm rate: {worst:.1%}   lowest find rate for steps of 8%+: {min(big):.1%}")
ok = worst <= 0.02 and min(big) >= 0.95
print('PASS' if ok else 'FAIL', '(bar: false alarms <= 2% on every trend-free series; steps of 8% or more found >= 95%)')
sys.exit(0 if ok else 1)
