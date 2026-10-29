"""Item 106 (gw 2.0/YEARLY_PRICE_STEPS.md, ruled 2026-10-21): a bill whose price steps at the same time each year.

Arithmetic over the charges and answers it is handed - no database, no clock, nothing stored. The server gathers the
record and the household's answers; the only things ever kept are those answers and the tap that updates a line.

  Y1  every step in a payee's history, by year - not only the latest, as W2 (core/price_change.py) finds
  Y2  a pattern: 2+ steps in different years, within NEAR months of each other, the same direction, none between;
      the figure is the median; projected from MIN_PROJECT (3, measured - ruled 2), "each year" only from 3;
      steps that disagree are not projected
  Y3  inside the search for a pattern, a steady charge steps at FLOOR (1%) and 50 cents - W2's 3% misses most
      yearly increases
  Y4  a charge paid once a year is compared charge to charge
  Y5  a usage bill (its amount follows use as well as price) never steps from the ledger: its yearly change is only
      ever the household's word, prompted by the same month a year earlier
  Y8  the household's answer for a year wins over the ledger's reading of that year
"""
from datetime import date

from core.price_change import (CENTS, MIN_AFTER, MIN_BEFORE, not_a_price, STEADY, SWING_TIMES, USAGE_CATEGORIES,
                               _median, rhythm)

FLOOR = 0.01          # Y3: a step inside a yearly pattern is at least 1% (and CENTS) ...
TOL = 0.005           # ... so a charge belongs to a level when within half a percent of it (or half of CENTS)
NEAR = 1              # Y2: within one month - of a year on between steps (as NEAR_DAYS), and for the window shown
NEAR_DAYS = 40        # Y2: steps 365 days apart, give or take a month (by date: a bill charged on the 30th that
                      # slips to the 1st is still a year on, which counting calendar months would miss)
DISAGREE = 2.0        # Y2: the largest step more than twice the smallest is a range, not a figure to project
MIN_PROJECT = 3       # Y2 as measured: a projection is shown ahead of the month only from 3 steps. Ruled "from 2";
                      # the null model found two unrelated price changes land a year apart by chance on 4.3-7.0% of
                      # series (bar: 2%), and three on 0.2-0.45%. Two steps are said as a fact, and the question (Y7)
                      # is still asked when the new price lands - the household's yes is the third step.
YEARLY_GAP = 330      # Y4: charges this many days apart, or more, are a charge paid once a year


def _ym(d):
    return d.year * 12 + d.month - 1


def _month_str(ym):
    return f'{ym // 12:04d}-{ym % 12 + 1:02d}'


LEVEL_TOL = STEADY / 2   # with a possible new level open, a charge joins whichever level it is nearer, within this


def _off(x, m):
    """How far x is from level m, as a share of m; a difference under half of CENTS counts as none (tax rounding)."""
    return 0.0 if abs(x - m) <= CENTS / 2 else abs(x - m) / m


def _levels(xs):
    """The charges split into price levels. A new level is MIN_AFTER charges together away from the old one.

    Measured in the null model: a charge must be within TOL to stay at today's level, or a 1% step would vanish into
    it; but once a new level is open, a charge goes to whichever level it is nearer (within LEVEL_TOL), or a few cents
    of noise kept restarting the new level and dated the step months late. A charge far from both (a prorated bill, a
    one-off fee) opens a level of its own that nothing joins; the two newest open levels are kept, so an odd charge
    on either side of a step can't hide the new price's first charge.
    Returns (levels, pending): pending is the newest charges at what may be a new price, not yet MIN_AFTER of them."""
    levels, cur, opened = [], [], []            # opened: up to two candidate levels, newest last
    for d, a in xs:
        if not cur:
            cur = [(d, a)]
            continue
        dc = _off(a, _median([x for _, x in cur]))
        if not opened and dc <= TOL:
            cur.append((d, a))
            continue
        near = [(dp, g) for g in opened for dp in [_off(a, _median([x for _, x in g]))] if dp <= LEVEL_TOL and dp < dc]
        if near:
            g = min(near, key=lambda t: t[0])[1]
            g.append((d, a))
            if len(g) >= MIN_AFTER:
                levels.append(cur)
                cur, opened = g, []
        elif opened and dc <= LEVEL_TOL:
            cur.append((d, a))                  # back at today's price: what was open was odd
            opened = []
        else:
            opened = (opened + [[(d, a)]])[-2:]
    if cur:
        levels.append(cur)
    return levels, (opened[-1] if opened else [])


def read(charges, category=''):
    """Y1/Y3/Y4: one payee's history read for every price step.

    Returns None for a usage bill or a charge that is not a price (Y5; W2's NOT_PRICES), else
    {kind: 'monthly' | 'yearly', level, level_since, pending, steps: [{month, before, after, pct, source}]}.
    `level` is today's price; `pending` is a first charge at what may be a new price, (date, amount) or None."""
    cat = (category or '').strip().lower()
    if not_a_price(cat) or cat in USAGE_CATEGORIES:
        return None
    xs = sorted((d, round(abs(float(a)), 2)) for d, a in charges if d and a)
    if len(xs) < 2:
        return None
    gaps = [(b[0] - a[0]).days for a, b in zip(xs, xs[1:])]
    if _median(gaps) >= YEARLY_GAP:                                    # Y4: paid once a year
        steps = []
        for (d0, a0), (d1, a1) in zip(xs, xs[1:]):
            if (d1 - d0).days >= YEARLY_GAP and abs(a1 - a0) >= CENTS and abs(a1 - a0) / a0 >= FLOOR:
                steps.append({'month': _month_str(_ym(d1)), 'date': d1.isoformat(), 'before': a0, 'after': a1,
                              'pct': (a1 - a0) / a0, 'source': 'ledger'})
        return {'kind': 'yearly', 'level': xs[-1][1], 'level_since': xs[-1][0], 'pending': None, 'steps': steps}
    levels, pend = _levels(xs)
    steps = []
    for prev, nxt in zip(levels, levels[1:]):
        bv, av = [a for _, a in prev], [a for _, a in nxt]
        if len(bv) < MIN_BEFORE or len(av) < MIN_AFTER:
            continue
        b, a = _median(bv), _median(av)
        swing = _median([abs(x - b) / b for x in bv])
        if swing > STEADY or not rhythm([d for d, _ in prev]):
            continue                                                   # not a steady recurring price before it
        if abs(a - b) < CENTS or abs(a - b) / b < max(FLOOR, SWING_TIMES * swing):
            continue
        steps.append({'month': _month_str(_ym(nxt[0][0])), 'date': nxt[0][0].isoformat(),
                      'before': round(b, 2), 'after': round(a, 2),
                      'pct': (a - b) / b, 'source': 'ledger'})
    cur = levels[-1]
    if not rhythm([d for d, _ in cur]) and len(levels) == 1:
        return None                                                    # never a recurring charge at all
    return {'kind': 'monthly', 'level': round(_median([a for _, a in cur]), 2), 'level_since': cur[0][0],
            'pending': pend[0] if pend else None, 'steps': steps}


def apply_answers(steps, answers):
    """Y8: the household's answer for a year wins over the ledger's reading of it.

    answers: [{month: 'YYYY-MM', answer: 'yes' | 'amount' | 'rate' | 'no_change' | 'not_sure', before, amount, pct}].
    'yes' / 'amount' give the new price (pct from `before`); 'rate' gives a percent (a usage bill, Y5); 'no_change'
    says that year had no step; 'not_sure' changes nothing."""
    out = [dict(s) for s in steps]
    for a in answers or []:
        kind = a.get('answer')
        if kind == 'not_sure' or not a.get('month'):
            continue
        ym = int(a['month'][:4]) * 12 + int(a['month'][5:7]) - 1
        out = [s for s in out if abs((int(s['month'][:4]) * 12 + int(s['month'][5:7]) - 1) - ym) > NEAR]
        mid = a.get('date') or a['month'] + '-15'
        if kind in ('yes', 'amount') and a.get('before') and a.get('amount') is not None:
            b, n = float(a['before']), float(a['amount'])
            out.append({'month': a['month'], 'date': mid, 'before': round(b, 2), 'after': round(n, 2), 'pct': (n - b) / b,
                        'source': 'answer'})
        elif kind == 'rate' and a.get('pct') is not None:
            out.append({'month': a['month'], 'date': mid, 'before': None, 'after': None, 'pct': float(a['pct']),
                        'source': 'answer'})
        elif kind == 'no_change':
            out.append({'month': a['month'], 'date': mid, 'before': None, 'after': None, 'pct': 0.0, 'source': 'answer'})
    return sorted(out, key=lambda s: s['date'])


def _ym_s(m):
    return int(m[:4]) * 12 + int(m[5:7]) - 1


def pattern(steps):
    """Y2: the newest run of yearly steps - each about a year after the one before (within NEAR months), the same
    direction, no other step between. None without a step; {'pattern': False} with one."""
    if not steps:
        return None
    ss = sorted(steps, key=lambda s: s['date'])
    chain = [ss[-1]]
    if chain[0]['pct'] != 0:
        for s in reversed(ss[:-1]):
            gap = (date.fromisoformat(chain[-1]['date']) - date.fromisoformat(s['date'])).days
            if abs(gap - 365) > NEAR_DAYS or s['pct'] == 0 or (s['pct'] > 0) != (chain[0]['pct'] > 0):
                break
            chain.append(s)
    chain.reverse()
    if len(chain) < 2:
        return {'pattern': False, 'steps': chain}
    pcts = [s['pct'] for s in chain]
    lo, hi = min(abs(p) for p in pcts), max(abs(p) for p in pcts)
    return {'pattern': True, 'steps': chain, 'pct': _median(pcts), 'low': min(pcts), 'high': max(pcts),
            'agree': hi <= DISAGREE * lo, 'each_year': len(chain) >= 3,
            'month_of_year': int(chain[-1]['month'][5:7])}


def next_expected(pat):
    """The month the next step would fall in, a year after the last one, as 'YYYY-MM'; None without a pattern."""
    if not pat or not pat.get('pattern'):
        return None
    return _month_str(_ym_s(pat['steps'][-1]['month']) + 12)


def projection(pat, level, today):
    """Y6: the figure shown beside the saved amount, from the month before the expected step to NEAR months after it.
    None outside that window, without a pattern, or when the steps disagree (Y2)."""
    nxt = next_expected(pat)
    if not nxt or not pat['agree'] or not level or len(pat['steps']) < MIN_PROJECT:
        return None
    t, e = _ym(today), _ym_s(nxt)
    if t < e - 1 or t > e + NEAR:
        return None
    return {'month': nxt, 'amount': round(level * (1 + pat['pct']), 2), 'from': round(level, 2), 'pct': pat['pct'],
            'years': [s['month'] for s in pat['steps']]}


def question(info, pat, today, answered):
    """Y7: 'Is your bill now $X?' - asked once, when a charge in the expected month lands at a new price.

    Two ways it lands: a first charge at a new price in the expected window (a monthly charge, before W2 would call it
    a step), or the newest step itself falling in the last NEAR months (a charge paid once a year is its own step).
    `answered`: the months already answered, any answer. None when there is nothing to ask."""
    if not info or not pat or not pat.get('pattern'):
        return None
    t = _ym(today)
    near_answered = lambda m: any(abs(_ym_s(m) - _ym_s(a)) <= NEAR for a in answered or [])
    nxt = next_expected(pat)
    p = info.get('pending')
    if nxt and p and abs(_ym(p[0]) - _ym_s(nxt)) <= NEAR and abs(p[1] - info['level']) >= CENTS \
            and not near_answered(nxt):
        return {'month': nxt, 'amount': p[1], 'before': info['level'], 'charge_date': p[0].isoformat()}
    last = pat['steps'][-1]
    if last['source'] == 'ledger' and 0 <= t - _ym_s(last['month']) <= NEAR and not near_answered(last['month']):
        return {'month': last['month'], 'amount': last['after'], 'before': last['before'], 'charge_date': None}
    return None


def same_month(charges, today):
    """Y5(a): a usage bill's newest month against the same month a year earlier, by the month paid. None when either
    month has no bill."""
    by = {}
    for d, a in charges:
        if d and a and d <= today:
            by[_ym(d)] = by.get(_ym(d), 0.0) + abs(float(a))
    if not by:
        return None
    last = max(by)
    if last - 12 not in by or not by[last - 12]:
        return None
    this, prev = round(by[last], 2), round(by[last - 12], 2)
    return {'month': _month_str(last), 'this': this, 'last_year': prev, 'pct': (this - prev) / prev}


def _pct(p):
    return f'{abs(p) * 100:.1f}%'


def _month_name(m):
    return date(int(m[:4]), int(m[5:7]), 1).strftime('%B')


def sentence(payee, pat):
    """Y9: facts with their years, never a verdict or a promise."""
    if not pat:
        return ''
    if not pat['pattern']:
        s = pat['steps'][0]
        if s['pct'] == 0:
            return f"{payee}: no change in {_month_name(s['month'])} {s['month'][:4]}, as you told us."
        way = 'up' if s['pct'] > 0 else 'down'
        return f"{payee}: went {way} {_pct(s['pct'])} in {_month_name(s['month'])} {s['month'][:4]}."
    way = 'up' if pat['pct'] > 0 else 'down'
    mon = _month_name(pat['steps'][-1]['month'])
    years = ', '.join(f"{s['month'][:4]}: {'+' if s['pct'] > 0 else '-'}{_pct(s['pct'])}" for s in pat['steps'])
    when = f'each {mon}' if pat['each_year'] else f'the last two {mon}s' if len(pat['steps']) == 2 else f'each {mon}'
    if not pat['agree']:
        return (f"{payee}: has gone {way} {when}, between {_pct(pat['low'])} and {_pct(pat['high'])} ({years}). "
                f"The steps differ too much to project one figure.")
    return f"{payee}: has gone {way} about {_pct(pat['pct'])} {when} ({years})."
