"""Solution engine — the honest levers that close a gap.

Pillar 3 of `gw 2.0/GW_2.0_TEACHING_PLATFORM_BLUEPRINT.md`, §6. Given a gap
("this costs you four months"), it searches only the sanctioned lever set for
paths that close it, and returns them with their costs so the user chooses —
E.4's *rank, don't decide*. When nothing closes the gap it returns the honest no
with the nearest true path (§6.4), never a bare "you can't".

**What is deliberately banned** (§6.3), and cannot appear here by construction
because no lever produces it: new income, a side hustle, a raise; any new credit
product, loan, balance transfer or BNPL; motivational filler with no math.

**What is built, and what waits.** §6.1 lists seven levers. Three are computable
from data that exists today and are implemented: timing, payoff-order, and the
generic monthly increase Pillar 2 solves for. The rest are left as named gaps
rather than half-built:

  * reallocation and specific-cost trimming need per-category spend and the
    recurring-item ledger, and both must respect the necessity floor below;
  * substitution needs to know what a cheaper equivalent *is*, which is domain
    knowledge the ledger does not hold;
  * save-first is deliberately absent from *this* gap — see the note where it
    would have gone. It is the anti-loan, and this gap is already a cash cost.

**Ranking.** E.3 orders six preferences, and only two of them are universal:
waiting/timing over cutting (rule 1), and smaller/reversible over large and
permanent (rule 3). The other three key off what the user has proven flexible or
tolerated — willingness, which F.6b keeps `unclassified` for most people most of
the time. So this ranks on the universal two and stops. Not knowing someone's
strategy costs humility in ranking, not the ability to help (F.6a).
"""

from core.consequence import decision_impact, offsetting_monthly_delta, simulate_payoff

# E.1 — the one objective layer. Protected because cutting these breaks
# stability, NOT because they are morally superior, and the blueprint flags this
# as the single place the platform asserts a default a human should sanity-check
# ("transport to work" is not universal).
NECESSITY_FLOOR = (
    'housing', 'rent', 'mortgage',
    'utilities', 'electric', 'gas / electric', 'water',
    'groceries', 'food',
    'insurance',
    'transport', 'transportation', 'fuel', 'gas / fuel',
    'childcare', 'kids',
)


def is_protected(category_name):
    """True when a category sits on the necessity floor and may never be proposed
    for cuts. Matching is loose on purpose: a near-miss that over-protects costs
    one unavailable lever, while a near-miss that under-protects proposes cutting
    someone's rent."""
    if not category_name:
        return False
    n = str(category_name).strip().lower()
    return any(p in n or n in p for p in NECESSITY_FLOOR)


def _path(kind, label, detail, closes, cost_months=None, requires_cut=False,
          reversible=True, frees_monthly=None, available_in_months=None):
    return {
        'kind': kind, 'label': label, 'detail': detail, 'closes': closes,
        'cost_months': cost_months, 'requires_cut': requires_cut,
        'reversible': reversible, 'frees_monthly': frees_monthly,
        'available_in_months': available_in_months,
    }


def solve_one_time_cost(cards, budget, one_time_cost, strategy='avalanche',
                        today_key=None, start_month=None):
    """Paths that absorb a one-time cost's effect on the payoff date.

    Returns {'gap_months', 'paths', 'honest_no'}. `paths` is ordered by E.3's
    universal rules and never empty when a path exists; `honest_no` is populated
    only when none does, and carries the nearest true path rather than a refusal.
    """
    kw = dict(strategy=strategy, today_key=today_key, start_month=start_month)
    impact = decision_impact(cards, budget, one_time_cost=one_time_cost, **kw)
    gap = impact.get('months_delta')

    if gap is None:
        # Unsimulatable — honest-null, not a guessed path.
        return {'gap_months': None, 'paths': [], 'honest_no': None,
                'reason': 'the payoff cannot be simulated from what is recorded'}
    if gap <= 0:
        return {'gap_months': gap, 'paths': [], 'honest_no': None,
                'reason': 'nothing to close'}

    paths = []

    # ── Lever 2: timing. A card clearing frees its minimum, and capacity that
    # arrives on its own disrupts nothing at all — E.3's first rule.
    base = impact['base']
    for name, info in sorted((base.get('cleared_at') or {}).items(),
                             key=lambda kv: kv[1]['month']):
        if info['month'] >= base['months']:
            continue                    # clears only at the very end: frees nothing usable
        after = decision_impact(cards, budget + info['frees_monthly'],
                                one_time_cost=one_time_cost, **kw)
        if after['months_delta'] is not None and after['months_delta'] < gap:
            verb = 'is forgiven' if info.get('forgiven') else 'clears'
            paths.append(_path(
                'timing',
                f"wait for {name}",
                f"{name} {verb} in month {info['month']}, freeing "
                f"${info['frees_monthly']:.0f}/mo",
                closes=(after['months_delta'] <= 0),
                cost_months=after['months_delta'],
                requires_cut=False,
                frees_monthly=info['frees_monthly'],
                available_in_months=info['month']))

    # ── Lever 3: payoff-order. Switching the method costs nothing and cuts
    # nothing; it is pure sequencing.
    other = 'snowball' if strategy == 'avalanche' else 'avalanche'
    alt = decision_impact(cards, budget, one_time_cost=one_time_cost,
                          **{**kw, 'strategy': other})
    if alt['months_delta'] is not None and alt['months_delta'] < gap:
        paths.append(_path(
            'payoff_order',
            f"pay in {other} order",
            f"{other} order absorbs {gap - alt['months_delta']} of the "
            f"{gap} month{'s' if gap != 1 else ''}",
            closes=(alt['months_delta'] <= 0),
            cost_months=alt['months_delta'],
            requires_cut=False))

    # ── Lever 6: save-first is NOT offered here, and the omission is deliberate.
    # It is the anti-loan — its value is against FINANCING a purchase. This gap
    # is already a cash cost, and the money saved would come from the same
    # surplus that would otherwise reach the debt, so saving first delays the
    # payoff by the same amount. Offering it as a path that "closes the gap"
    # would be flattery: the same money, spent later, presented as free.

    # ── The generic monthly lever (Pillar 2). A cut is implied but no category
    # is named — which envelope it comes from is the user's to choose, and
    # naming one needs willingness this engine does not have.
    lever = offsetting_monthly_delta(cards, budget, one_time_cost, **kw)
    if lever:
        paths.append(_path(
            'monthly',
            'put more toward debt',
            f"${lever:.0f}/mo more holds the date where it is",
            closes=True, cost_months=0, requires_cut=True, reversible=True))

    paths.sort(key=_rank_key)

    honest_no = None
    if not any(p['closes'] for p in paths):
        # §6.4: never a bare "you can't". The nearest true path is the smallest
        # change that would close it, even when nothing offered does.
        nearest = offsetting_monthly_delta(cards, budget, one_time_cost,
                                           cap=max(1.0, budget), **kw)
        honest_no = {
            'gap_months': gap,
            'nearest_monthly': nearest,
            'reachable': nearest is not None,
        }

    return {'gap_months': gap, 'paths': paths, 'honest_no': honest_no}


def _rank_key(p):
    """E.3's universal rules only, in order.

    1. Waiting/timing over cutting — a path that requires no cut ranks above one
       that does, always.
    3. Smaller and reversible over large and permanent.
    Then, among equals, the one that closes the gap and closes it soonest.

    Rules 2, 4 and 5 (flexible-by-proof, demonstrated tolerance, spread vs
    concentrate) are absent deliberately: each needs willingness, and F.6b keeps
    that `unclassified` for most people. Adding them here on a guess would be
    exactly the assumption E.2 forbids.
    """
    return (
        p['requires_cut'],                       # False first
        not p['reversible'],                     # reversible first
        not p['closes'],                         # closes the gap first
        p['available_in_months'] if p['available_in_months'] is not None else 0,
        p['cost_months'] if p['cost_months'] is not None else 0,
    )
