"""Would daylight improve the electric estimate? (item 26 follow-up, Rob 2026-10-21: "see the weather, sun light set
times ... figure out the user average usage for their home and then use that as the next month budget".)

A null model in the manner of scripts/w2_null_model.py, run before anything is built. Seeded synthetic homes; the
shipped fit (core/utility_estimate.py) against the same fit allowed one more term, dark waking hours, kept only on
the shipped terms' own rule (positive slope, leave-one-out error cut by EXTRA_TERM_MARGIN). Both are scored on the
NEXT twelve months, which neither saw.

Dark waking hours per month: sunset to 23:00 plus 06:30 to sunrise, from latitude, with daylight saving time.
Nothing here is shipped and nothing is read from a household's record.

Usage: python3 scripts/daylight_null_model.py [worlds_per_cell]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import utility_estimate as ue   # noqa: E402

DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# Approximate monthly normals (HDD, CDD) and latitude. Shapes, not exact NOAA figures: what matters is how closely
# darkness tracks heating and cooling, which the shapes carry.
CLIMATES = {
    'Ohio (40.7N)': (40.7, [1150, 960, 780, 450, 200, 30, 5, 10, 90, 400, 720, 1050],
                     [0, 0, 3, 15, 70, 200, 290, 250, 110, 15, 0, 0]),
    'Texas (29.8N)': (29.8, [370, 270, 160, 50, 5, 0, 0, 0, 0, 30, 160, 320],
                      [40, 40, 110, 220, 420, 560, 640, 650, 500, 280, 110, 50]),
    'Minnesota (45.0N)': (45.0, [1600, 1300, 1050, 560, 250, 60, 10, 20, 180, 550, 1000, 1450],
                          [0, 0, 0, 5, 40, 170, 270, 220, 70, 5, 0, 0]),
}
HEATING = {'gas heat': (0.03, 0.06), 'electric heat': (0.30, 0.60)}       # kWh per HDD (furnace fan vs heat pump)
LIGHTING = {'no lighting effect': 0.0, 'LED-typical lighting': 0.15, 'heavy lighting': 0.80}   # kW lit while dark


def dark_hours(lat, month):
    """Dark waking hours in a month: sunset to 23:00 plus 06:30 to sunrise, local clock time with DST."""
    n0 = sum(DAYS[:month - 1])
    total = 0.0
    for d in range(DAYS[month - 1]):
        n = n0 + d + 1
        decl = math.radians(23.44) * math.sin(2 * math.pi * (284 + n) / 365)
        x = -math.tan(math.radians(lat)) * math.tan(decl)
        half = math.degrees(math.acos(max(-1.0, min(1.0, x)))) / 15.0
        noon = 13.1 if 70 <= n <= 308 else 12.1        # solar noon on the clock, about mid-zone, DST in summer
        rise, sset = noon - half, noon + half
        total += max(0.0, 23.0 - sset) + max(0.0, rise - 6.5)
    return total


def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def world(rnd, lat, hdd_n, cdd_n, heat, light_kw, months):
    """`months` consecutive service months of one home: weather, price and bill."""
    base = rnd.uniform(400, 700)
    sh = rnd.uniform(*HEATING[heat])
    sc = rnd.uniform(0.8, 1.5)
    fixed = rnd.uniform(10, 15)
    lit = light_kw * rnd.uniform(0.7, 1.3)
    out = []
    for i in range(months):
        mo = i % 12 + 1
        hdd = max(0.0, hdd_n[mo - 1] * (1 + rnd.gauss(0, 0.15)) + rnd.gauss(0, 5))
        cdd = max(0.0, cdd_n[mo - 1] * (1 + rnd.gauss(0, 0.15)) + rnd.gauss(0, 5))
        dark = dark_hours(lat, mo)
        price = 0.15 * (1 + 0.03 * i / 12) * (1.05 if 6 <= mo <= 9 else 1.0) * (1 + rnd.gauss(0, 0.01))
        kwh = base + sh * hdd + sc * cdd + lit * dark
        bill = fixed + kwh * price * (1 + rnd.gauss(0, 0.03)) + rnd.gauss(0, 2)
        out.append({'month': f'{2024 + i // 12}-{mo:02d}', 'amount': bill, 'price': price,
                    'hdd': hdd, 'cdd': cdd, 'dark': dark})
    return out


def with_dark(points, shipped):
    """The shipped choice, or the shipped terms plus darkness when that earns its place by the shipped rule."""
    terms = shipped['terms'] + ['dark']
    m = ue.fit_terms(points, terms)
    if m is None or any(m['S_' + t] <= 0 for t in terms):
        return shipped
    e_new = ue._loo_error(points, terms)
    e_old = ue._loo_error(points, shipped['terms'])
    if e_new is None or e_old is None or e_new >= (1 - ue.EXTRA_TERM_MARGIN) * e_old:
        return shipped
    return m


def run(per_cell):
    rnd = random.Random(20261021)
    print('Correlation of dark waking hours with heating / cooling degree days (normals):')
    for name, (lat, h, c) in CLIMATES.items():
        dk = [dark_hours(lat, m) for m in range(1, 13)]
        print(f'  {name:18s} HDD {corr(dk, h):+.2f}   CDD {corr(dk, c):+.2f}   '
              f'dark hours/month {min(dk):.0f}-{max(dk):.0f}')
    print()
    print(f'{per_cell} homes per row; error is the mean absolute miss on the next 12 bills (neither fit saw them).')
    hdr = f'{"climate":18s} {"heat":13s} {"lighting":21s} {"hist":>4s} {"dark kept":>9s} ' \
          f'{"shipped $":>9s} {"+dark $":>8s} {"change":>7s} {"worse>5%":>8s} {"better>5%":>9s}'
    print(hdr)
    print('-' * len(hdr))
    summary = {}
    for name, (lat, h, c) in CLIMATES.items():
        for heat in HEATING:
            for light, kw in LIGHTING.items():
                for hist in (12, 24):
                    kept = n = worse = better = 0
                    e_ship = e_dark = 0.0
                    for _ in range(per_cell):
                        pts = world(rnd, lat, h, c, heat, kw, hist + 12)
                        past, future = pts[:hist], pts[hist:]
                        shipped = ue._positive_terms(past)
                        if shipped is None:
                            continue
                        chosen = with_dark(past, shipped)
                        a = sum(abs(ue.predict_terms(shipped, p['price'], p) - p['amount']) for p in future) / 12
                        b = sum(abs(ue.predict_terms(chosen, p['price'], p) - p['amount']) for p in future) / 12
                        n += 1
                        kept += chosen is not shipped
                        e_ship += a
                        e_dark += b
                        worse += b > 1.05 * a
                        better += b < 0.95 * a
                    if not n:
                        continue
                    chg = (e_dark - e_ship) / e_ship * 100
                    summary.setdefault(light, []).append((kept / n, chg, worse / n, better / n))
                    print(f'{name:18s} {heat:13s} {light:21s} {hist:4d} {kept / n:9.1%} {e_ship / n:9.2f} '
                          f'{e_dark / n:8.2f} {chg:+6.1f}% {worse / n:8.1%} {better / n:9.1%}')
    print()
    print('Across every climate, heating type and history length:')
    for light, rows in summary.items():
        k = sum(r[0] for r in rows) / len(rows)
        ch = sum(r[1] for r in rows) / len(rows)
        w = sum(r[2] for r in rows) / len(rows)
        b = sum(r[3] for r in rows) / len(rows)
        print(f'  {light:21s} darkness kept in {k:5.1%} of homes; next-year error {ch:+.1f}% on average; '
              f'{w:5.1%} of homes worse by 5%+, {b:5.1%} better by 5%+')


if __name__ == '__main__':
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 400)
