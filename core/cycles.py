"""Has this shape happened before? — Appendix G, the long arc.

Everything else in this engine reads weeks to months. A debt cycle is months to
years: payoff, relief, gradual re-accumulation, a second crisis possibly worse
than the first. G.1 is careful about what the gap actually is — not that someone
might fail again, which is unknowable and not claimed here, but that they may
not realise they have already been through this shape once. They lived two
cycles as separate moments; the ledger can show they are the same story told
twice. A visibility gap, not a willpower gap.

§12 gated this on three things, pinned here:

**The cycle boundary (G.3).** A close is *overall revolving debt* at zero, in a
recorded month. Not "a major balance cleared" and not one debt type: the unit is
the whole revolving position, because that is the shape that recurs. Zero means
`SETTLED`, the same hundredth of a dollar the payoff engine has always treated
as cleared — borrowed rather than invented so the app has one definition of paid
off. Installment loans and leases are excluded: they amortise to zero by
design, and a car loan ending is not a cycle closing.

**The approaching checkpoint (G.3a).** `APPROACHING_SHARE` of the prior peak.
This is the one number here that is a judgement rather than a derivation, and it
is worth saying why the derivable alternative was rejected: proximity could be
expressed in the user's own recent re-accumulation ("within a quarter's worth of
the prior peak"), which self-scales and invents nothing — but it defines
nearness using the direction they are travelling, and G.3a is explicit that
distance is a fact while direction of travel is not claimed. A fixed share of
the peak says only where they are.

**Insufficient history (C.7).** A cycle must be *visible*, not inferred. If the
recorded history opens mid-cycle with no close in it, there is no prior peak —
and the answer is silence, never the largest number on file dressed up as one.
Bias to false-negatives throughout (G.3): missing a real cycle is the acceptable
cost; claiming one that isn't real is a fabricated story about someone's life.
"""

from core.consequence import SETTLED

# G.3a's proximity. Near enough that the remaining distance is small against the
# peak, far enough that the statement is not merely "you have passed it".
APPROACHING_SHARE = 0.90

# A cycle needs enough recorded months to be a cycle rather than a gap in the
# data — the same floor every other reader here uses.
MIN_CYCLE_MONTHS = 3

NONE = 'none'
BELOW = 'below'
APPROACHING = 'approaching'
PAST = 'past'


def detect_cycles(series):
    """Completed cycles in a monthly series of total revolving balances.

    `series` is [{'month': 'YYYY-MM', 'balance': float, 'interest': float|None}]
    in month order. A cycle is a stretch that ends at zero, and only a stretch
    that ENDS at zero: the run currently in progress is not a cycle, because it
    has not closed and its peak is not yet its peak.

    Returns [{'peak', 'peak_month', 'closed_month', 'interest'}]. Interest is
    None when the history does not carry it — a receipt that says "$0 to get out
    last time" when the figure was simply never recorded would be worse than
    saying nothing.
    """
    rows = [r for r in (series or []) if r.get('balance') is not None]
    cycles, run = [], []
    for row in rows:
        balance = float(row['balance'])
        if balance > SETTLED:
            run.append(row)
            continue
        # A zero month closes whatever run reached it.
        if len(run) >= MIN_CYCLE_MONTHS:
            peak_row = max(run, key=lambda r: float(r['balance']))
            charged = [float(r['interest']) for r in run
                       if r.get('interest') is not None]
            cycles.append({
                'peak': round(float(peak_row['balance']), 2),
                'peak_month': peak_row['month'],
                'closed_month': row['month'],
                'months': len(run),
                # Only when the whole run carries it. A partial sum understates
                # the cost of the last cycle, and understating a receipt makes
                # it a different receipt.
                'interest': (round(sum(charged), 2)
                             if len(charged) == len(run) else None),
            })
        run = []
    return cycles


def recurrence(series):
    """Where this run stands against the last completed cycle's peak.

    The four states of G.3a, and nothing between them. `none` covers both "no
    prior cycle" and "not enough history to see one" on purpose: from the user's
    side they are the same silence, and C.7 routes insufficient evidence through
    the honest-no rather than through a special empty state.

    Distance only. Nothing here says the balance is rising, or will.
    """
    rows = [r for r in (series or []) if r.get('balance') is not None]
    cycles = detect_cycles(rows)
    current = float(rows[-1]['balance']) if rows else 0.0

    if not cycles:
        return {'state': NONE, 'current': round(current, 2), 'prior': None,
                'reason': 'no completed cycle on record'}

    prior = cycles[-1]
    # Only the run since that close counts. A balance carried from before the
    # last close is not re-accumulation.
    since = []
    seen_close = False
    for row in rows:
        if row['month'] == prior['closed_month']:
            seen_close = True
            continue
        if seen_close:
            since.append(row)
    if len(since) < MIN_CYCLE_MONTHS:
        return {'state': NONE, 'current': round(current, 2), 'prior': prior,
                'reason': (f'only {len(since)} recorded month'
                           f'{"s" if len(since) != 1 else ""} since it closed')}

    peak = float(prior['peak'])
    if peak <= 0:
        return {'state': NONE, 'current': round(current, 2), 'prior': prior,
                'reason': 'the prior cycle has no peak to compare against'}

    share = current / peak
    if share > 1.0:
        state = PAST
    elif share >= APPROACHING_SHARE:
        state = APPROACHING
    else:
        state = BELOW
    return {
        'state': state,
        'current': round(current, 2),
        'prior': prior,
        'distance': round(peak - current, 2),
        'share': round(share, 3),
        'reason': None,
    }
