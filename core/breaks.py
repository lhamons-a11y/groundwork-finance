"""The break-detector (blueprint Appendix F.8; `gw 2.0/BREAK_DETECTOR.md`, ruled 2026-09-28).

A break is a sustained change in the LEVEL of a monthly series, detected by its shape and never on a clock.
It is used as an evidence boundary (ruling 1): behaviour before a break cannot support a reading of
behaviour after it. **A break erases nothing.** Every edit and every month stays in the record, available
for receipts, for history and for anything that legitimately uses it. A break changes only which evidence
is admissible for a *current* behavioural reading (Rob, 2026-09-28).

The shape (ruling 2)
- A run of at least MIN_AFTER recorded months at the end of the series, every one of them past the prior
  level by EACH_MULTIPLE of that series' own spread and on the same side of it. A run that dips back is not
  a new level, and one odd month is never a break.
- The run's level, measured against the prior level, must be at least Z_MIN standard errors away, where
  the error comes from the series' own spread and both segments' lengths. So a longer run can show a
  smaller change. A two-month run is judged by its LESS extreme month, because the middle of two is their
  average, and one big month would carry it.
- The change must also be at least MIN_RELATIVE of the prior level. That makes it material, not merely
  detectable.
- The prior level and spread come from at least MIN_BEFORE recorded months: the median and the median
  absolute deviation. Both are robust, so one odd month in the past does not move the yardstick.
- Only months in the series count. The caller decides what a missing month is. For spending it is a gap,
  never a zero, and a gap neither creates nor confirms a break.

The thresholds were set by the null model (`null_model`, below), and s130 re-runs it on every gate. On
trend-free series with realistic noise and one-off spikes, false breaks stay at or under
MAX_FALSE_BREAK_RATE at every noise level. Known shifts are found at or above the rates in DETECTION_FLOOR.
If those numbers stop holding, the gate fails and the detector does not ship (ruling 2).

**What it cannot see, stated plainly.** In a noisy category (month-to-month variation of 35% or more) a
moderate shift is usually invisible, and so is a ±50% shift at 20% variation, more often than not. That
blind spot is the safe direction: an unseen break leaves every reading exactly as it was without this
detector.

It says what moved and when. It never says why, and never for how long (F.8, "the shift, not the story").
"""

import random
from statistics import median

MIN_BEFORE = 4          # months of prior level before a run can be judged against it
MIN_AFTER = 2           # two recorded months at a new level: the ruled minimum; one is a wobble
EACH_MULTIPLE = 2.0     # every month of the run past the prior level by this many robust spreads
Z_MIN = 3.5             # the run's level past the prior level by this many standard errors
MIN_RELATIVE = 0.30     # and by at least this share of it: material, not merely detectable
_MAD_SCALE = 1.4826     # MAD -> standard deviation, for a normal-ish series
_SPREAD_FLOOR = 0.05    # a perfectly flat past (spread 0) still gets a yardstick: 5% of its level

# The acceptance numbers the null model must meet (ruling 2); s130 asserts them on every gate.
MAX_FALSE_BREAK_RATE = 0.05
# (noise CV, shift multiple) -> the least share of sustained three-month shifts that must be found,
# located within a month.
DETECTION_FLOOR = {(0.10, 1.5): 0.80, (0.10, 0.5): 0.80, (0.10, 2.0): 0.90, (0.10, 0.3): 0.90,
                   (0.20, 2.0): 0.75, (0.20, 0.3): 0.75}


def detect_break(series):
    """The latest confirmed break in `series`, or None.

    `series` is [(month 'YYYY-MM', value)] in month order, containing only the months that count. Returns
    {'month': first month at the new level, 'direction': 'up'|'down', 'before': prior level,
     'after': new level, 'relative': signed change as a share of the prior level,
     'months_before': [...], 'months_after': [...]}.
    """
    pts = [(m, float(v)) for m, v in series if v is not None]
    n = len(pts)
    best = None
    for start in range(n - MIN_AFTER, MIN_BEFORE - 1, -1):
        before = [v for _, v in pts[:start]]
        after = [v for _, v in pts[start:]]
        level = median(before)
        found = False
        if level > 0:
            spread = max(_MAD_SCALE * median(abs(v - level) for v in before), _SPREAD_FLOOR * level)
            up = all(v > level + EACH_MULTIPLE * spread for v in after)
            down = all(v < level - EACH_MULTIPLE * spread for v in after)
            if up or down:
                run = sorted(after, reverse=down)[0] if len(after) == 2 else median(after)
                se = spread * (1.0 / len(after) + 1.0 / len(before)) ** 0.5
                found = (abs(run - level) / se >= Z_MIN and abs(run - level) >= MIN_RELATIVE * level)
                if found:
                    best = (start, level, after, 'up' if up else 'down')
        if not found and best:
            break                      # the run began where the last test passed
    if not best:
        return None
    start, level, after, direction = best
    new = median(after)
    return {'month': pts[start][0], 'direction': direction, 'before': round(level, 2), 'after': round(new, 2),
            'relative': round((new - level) / level, 3),
            'months_before': [m for m, _ in pts[:start]], 'months_after': [m for m, _ in pts[start:]]}


def null_model(trials=1500, shifted=600, months=11, seed=20260928):
    """The simulation that set the thresholds and checks them on every gate (the null-model rule; ruling 2).

    Series are monthly spending: a level, multiplicative noise at a coefficient of variation, and, as real
    records have, a one-off month about one time in seventeen at roughly double. Deterministic (seeded).

    Returns {'false': {cv: share of TREND-FREE series with a break found},
             'found': {(cv, shift): share of series with a sustained three-month shift found within a month}}.
    """
    rng = random.Random(seed)
    labels = [f'2025-{m:02d}' for m in range(1, 13)] + [f'2026-{m:02d}' for m in range(1, 13)]

    def series(cv, shift=None, k=3):
        level = rng.uniform(80, 900)
        out = []
        for i in range(months):
            v = level * max(0.05, rng.gauss(1.0, cv))
            if rng.random() < 0.06:
                v *= rng.uniform(1.8, 2.6)
            if shift and i >= months - k:
                v *= shift
            out.append((labels[i], v))
        return out

    false = {cv: sum(1 for _ in range(trials) if detect_break(series(cv))) / trials
             for cv in (0.10, 0.20, 0.35, 0.50)}
    at = labels.index(labels[months - 3])
    found = {}
    for cv, shift in DETECTION_FLOOR:
        hit = 0
        for _ in range(shifted):
            b = detect_break(series(cv, shift))
            if b and abs(labels.index(b['month']) - at) <= 1:
                hit += 1
        found[(cv, shift)] = hit / shifted
    return {'false': false, 'found': found}
