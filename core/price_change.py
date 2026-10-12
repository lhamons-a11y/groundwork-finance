"""Item 65 W2 (gw 2.0/AGENT_W_ITEMS.md, ruled 2026-10-12): when a recurring charge's price steps to a new level.

Arithmetic over the charges it is handed - no database, no clock, nothing stored. The server gathers the record and
shows what this finds; the only thing ever kept is the person's tap that updates a budget line (with Undo).

  W2-a  a step, not noise: 2+ charges at the new level, every one of them nearer the new level than the old, and the
        change more than the payee's own normal swing (SWING_TIMES of it) and more than a floor. Null-modelled before
        it shipped (section "W2 null model" of AGENT_W_ITEMS.md), as item 71's paycheck rule was.
  W2-b  no reason invented: `kind` is only what the record itself shows - the charges moved from monthly to yearly
        (the gaps say so), or the line is a usage bill (its category says so). Otherwise it is only a price change.
"""
from datetime import date

FLOOR = 0.03          # a step is at least 3% ...
CENTS = 0.50          # ... and at least 50 cents (a rounding cent is not a new price) ...
SWING_TIMES = 3       # ... and at least three times the payee's own normal swing before it
STEADY = 0.03         # a price can only step from a steady charge: the old level's typical swing, and every new
                      # charge's distance from the new level, within 3%. A bill whose amount follows use (a seasonal
                      # utility) has no one price to step from - the null model fired on 18-30% of those without this
MIN_BEFORE = 3        # the old level is known from 3+ charges
MIN_AFTER = 2         # the new level from 2+ (W2-a: one odd charge isn't a new price)
REGULAR = ((6, 8, 'weekly'), (12, 17, 'every two weeks'), (25, 35, 'monthly'), (80, 100, 'quarterly'),
           (170, 195, 'twice a year'), (350, 380, 'yearly'))
# metered bills: the amount follows use as well as the price (a level-billing reset reads as a step)
USAGE_CATEGORIES = {'utilities', 'electric', 'electricity', 'natural gas', 'water / sewer', 'municipal utilities',
                    'propane', 'heating oil'}
# not prices: interest and fees follow a balance, a debt payment or a transfer or savings is the person's own choice
NOT_PRICES = {'interest', 'interest / fees', 'fees', 'debt', 'transfer', 'savings', 'refund', 'atm'}


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return 0.0
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def rhythm(dates):
    """The schedule the dates keep (weekly ... yearly), or None when they keep none."""
    if len(dates) < 2:
        return None
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    g = _median(gaps)
    for lo, hi, name in REGULAR:
        if lo <= g <= hi and sum(lo <= x <= hi for x in gaps) >= 0.6 * len(gaps):
            return name
    return None


def step(charges, category=''):
    """The latest price step in one payee's charges [(date, amount)], or None.

    Returns {before, after, last_before, first_after, after_count, kind, records} - the old and new levels (medians),
    the dates either side of the step, and every charge it was read from."""
    xs = sorted((d, round(abs(float(a)), 2)) for d, a in charges if d and a)
    if len(xs) < MIN_BEFORE + MIN_AFTER or (category or '').strip().lower() in NOT_PRICES:
        return None
    for k in range(len(xs) - MIN_AFTER, MIN_BEFORE - 1, -1):          # the most recent step first
        before, after = xs[:k][-12:], xs[k:]
        bv, av = [a for _, a in before], [a for _, a in after]
        b, a = _median(bv), _median(av)
        if b <= 0:
            continue
        swing = _median([abs(x - b) / b for x in bv])
        if swing > STEADY or any(abs(x - a) / a > STEADY for x in av):
            continue
        if sum(abs(x - b) / b <= STEADY for x in bv) < max(MIN_BEFORE, 0.75 * len(bv)):
            continue                                                    # the old level is most of the charges, not two odd ones
        change = abs(a - b) / b
        if change < max(FLOOR, SWING_TIMES * swing) or abs(a - b) < CENTS:
            continue
        if not all(abs(x - a) < abs(x - b) for x in av):              # every charge since sits at the new level
            continue
        if abs(bv[-1] - b) >= abs(bv[-1] - a):                          # and the one before it at the old level
            continue
        rb, ra = rhythm([d for d, _ in before]), rhythm([d for d, _ in after])
        if not rb:
            return None                                                  # not a recurring charge before the step
        kind = 'price'
        if ra and ra != rb:
            kind = 'frequency'                                            # e.g. monthly -> yearly, from the gaps
        elif (category or '').strip().lower() in USAGE_CATEGORIES:
            kind = 'usage'
        return {'before': round(b, 2), 'after': round(a, 2), 'last_before': before[-1][0], 'first_after': after[0][0],
                'after_count': len(after), 'kind': kind, 'rhythm_before': rb, 'rhythm_after': ra,
                'records': [{'date': d.isoformat() if isinstance(d, date) else d, 'amount': x} for d, x in xs[-(len(after) + 6):]]}
    return None


def sentence(payee, s):
    """The fact, in words, from the record only (W2-b). E.g. 'Netflix: $15.49 through July, $17.99 since August (2 charges).'"""
    m = lambda d: d.strftime('%B') if isinstance(d, date) else str(d)
    base = (f"{payee}: ${s['before']:,.2f} through {m(s['last_before'])}, ${s['after']:,.2f} since {m(s['first_after'])} "
            f"({s['after_count']} charge{'s' if s['after_count'] != 1 else ''}).")
    if s['kind'] == 'frequency':
        return base + f" The charges also moved from {s['rhythm_before']} to {s['rhythm_after']}."
    if s['kind'] == 'usage':
        return base + " This is a usage bill: its amount follows what is used as well as the price."
    return base
