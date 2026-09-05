"""Solution engine — the honest levers that close a gap.

Pillar 3 of `gw 2.0/GW_2.0_TEACHING_PLATFORM_BLUEPRINT.md`, §6. Given a gap
("this costs you four months"), it searches only the sanctioned lever set for
paths that close it, and returns them with their costs so the user chooses —
E.4's *rank, don't decide*. When nothing closes the gap it returns the honest no
with the nearest true path (§6.4), never a bare "you can't".

**What is deliberately banned** (§6.3), and cannot appear here by construction
because no lever produces it: new income, a side hustle, a raise; any new credit
product, loan, balance transfer or BNPL; motivational filler with no math.

**What is built, and what waits.** §6.1 lists seven levers. Six are computable
from data that exists today and are implemented: timing, payoff-order, the
generic monthly increase Pillar 2 solves for, substitution as a price rather
than as a product, and — when the caller hands over per-category spend and the
recurring ledger — reallocation and specific-cost trimming. Those last two are
the first levers here that name something: a category, a merchant. What naming
does and does not license is set out at `_headroom` and `_trims`.

Two things are still deliberately absent:

  * save-first, from *this* gap — see the note where it would have gone. It is
    the anti-loan, and this gap is already a cash cost.
  * substitution's OTHER half, where a new recurring cost replaces an existing
    one and only the difference is felt. That is BYB's `replacing` mechanic
    (`replacing_id` on `BYBItem`), where the user names what is replaced; it
    needs a monthly-gap solver and a surface that asks the question, and this
    one is neither.

**Ranking.** E.3 orders six preferences, and only two of them are universal:
waiting/timing over cutting (rule 1), and smaller/reversible over large and
permanent (rule 3). The other three key off what the user has proven flexible or
tolerated — willingness, which F.6b keeps `unclassified` for most people most of
the time. So this ranks on the universal two and stops. Not knowing someone's
strategy costs humility in ranking, not the ability to help (F.6a).
"""

from core.consequence import (affordable_one_time, decision_impact,
                              offsetting_monthly_delta, simulate_payoff)

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


# Both history-reading levers need a window long enough to be a record rather
# than an anecdote, and an amount large enough to be worth naming. Three months
# is the floor `detect_recurring_patterns` already uses to call something
# recurring at all, and a lever worth less than five dollars a month is noise
# wearing a name.
MIN_MONTHS_OBSERVED = 3
MIN_MATERIAL_MONTHLY = 5.0


# ── Naming, and what it does not license ────────────────────────────────
# Pillar 2's lever deliberately does not name a category, because "trim dining
# $40/mo" asserts that dining is flexible for this person, and F.6b keeps that
# unclassified. Levers 1 and 4 do name things, so the line has to be drawn
# somewhere finer than "never name".
#
# It is drawn between a receipt and a recommendation. What is offered here is
# arithmetic over the user's own record — this envelope was budgeted at $400 and
# never once needed more than $310 in the months on file; these two items cost
# $43/mo between them. Which of the named things the user is willing to give up
# is not asserted, not ranked and not inferred: candidates are ordered by size
# and count only, the alternatives ride along on the path so one can be swapped
# for another, and no path says a word about what would be missed least.


def _headroom(categories):
    """Lever 1's candidates: budgeted money the record shows was never needed.

    Each entry the caller supplies is {name, budgeted, max_observed,
    months_observed}. Headroom is budgeted minus the WORST observed month, not
    the average — what is left over in an average month is money that some real
    month spent, and offering it back would be offering the user their own
    grocery run. The worst month is the part of the envelope their own record
    never reached.

    `months_observed` must count the months this category was actually seen in
    a recorded month — not the months in the window. A category absent from a
    month spent nothing only if the ledger holds that month at all, and a
    category absent from the whole window is not thrift, it is an envelope paid
    somewhere the ledger cannot see. Both tests need the whole ledger, so they
    belong to the caller; this refuses to work with too few months and takes the
    count on trust.
    """
    out = []
    for c in categories or []:
        name = (c or {}).get('name')
        if not name or is_protected(name):
            continue
        budgeted, worst = c.get('budgeted'), c.get('max_observed')
        if budgeted is None or worst is None:
            continue
        if int(c.get('months_observed') or 0) < MIN_MONTHS_OBSERVED:
            continue
        room = float(budgeted) - float(worst)
        if room < MIN_MATERIAL_MONTHLY:
            continue
        out.append({'kind': 'reallocation', 'name': name, 'monthly': round(room, 2),
                    'budgeted': float(budgeted), 'worst': float(worst),
                    'months_observed': int(c['months_observed'])})
    out.sort(key=lambda c: -c['monthly'])
    return out


def _trims(recurring):
    """Lever 4's candidates: recurring items whose removal changes the verdict.

    Each entry is {name, monthly, category}. `monthly` is what the item costs
    per month, which is not what it charges: a weekly $16 item is a $69/mo line,
    and naming the charge would understate it fourfold. Turning one into the
    other needs the cadence, so the caller does it.

    An item whose category is unknown is treated as protected and dropped. The
    costs are asymmetric — over-protecting loses a candidate, under-protecting
    proposes cancelling someone's power bill.
    """
    out = []
    for r in recurring or []:
        name = (r or {}).get('name')
        category = r.get('category')
        if not name or not category or is_protected(category):
            continue
        monthly = r.get('monthly')
        if monthly is None or float(monthly) < MIN_MATERIAL_MONTHLY:
            continue
        out.append({'kind': 'trim', 'name': name, 'monthly': round(float(monthly), 2),
                    'category': category})
    out.sort(key=lambda c: -c['monthly'])
    return out


def _smallest_cover(candidates, needed, max_items=3, pool=8):
    """The fewest named items that cover `needed`, and among those the cheapest.

    Fewest first, because every named item is a separate thing to act on; then
    smallest total, because overshooting asks for more than the gap needs.
    Neither criterion says anything about which items this user would rather
    keep. Bounded at three items drawn from the eight largest: "cancel these six
    things" is not an offer anyone takes, and the combinatorics past that buy
    nothing.
    """
    from itertools import combinations
    if not candidates or not needed or needed <= 0:
        return None, None
    for k in range(1, min(max_items, len(candidates)) + 1):
        best = None
        for combo in combinations(candidates[:pool], k):
            total = sum(c['monthly'] for c in combo)
            if total >= needed and (best is None or total < best[0]):
                best = (total, combo)
        if best:
            return list(best[1]), round(best[0], 2)
    return None, None


def _join(names):
    """"A", "A and B", "A, B and C" — a person reads this sentence."""
    names = list(names)
    if len(names) <= 1:
        return names[0] if names else ''
    return '%s and %s' % (', '.join(names[:-1]), names[-1])


def _path(kind, label, detail, closes, cost_months=None, requires_cut=False,
          reversible=True, frees_monthly=None, available_in_months=None,
          items=None, alternatives=None, amount=None):
    return {
        'kind': kind, 'label': label, 'detail': detail, 'closes': closes,
        'cost_months': cost_months, 'requires_cut': requires_cut,
        'reversible': reversible, 'frees_monthly': frees_monthly,
        'available_in_months': available_in_months,
        # The named sources behind a path, and the ones it passed over. E.4
        # ranks rather than decides, and a user who would sooner keep one of
        # these can only swap it for another if the others are on the page.
        'items': items or [], 'alternatives': alternatives or [],
        # The one-off figure a path turns on, where that figure is not a monthly
        # one — substitution's price ceiling is the only one so far.
        'amount': amount,
    }


def solve_one_time_cost(cards, budget, one_time_cost, strategy='avalanche',
                        today_key=None, start_month=None,
                        categories=None, recurring=None):
    """Paths that absorb a one-time cost's effect on the payoff date.

    Returns {'gap_months', 'paths', 'honest_no'}. `paths` is ordered by E.3's
    universal rules and never empty when a path exists; `honest_no` is populated
    only when none does, and carries the nearest true path rather than a refusal.

    `categories` and `recurring` are the raw material for levers 1 and 4, in the
    shapes `_headroom` and `_trims` describe. Both are optional: given neither,
    the engine offers the three levers that need nothing but the debt itself,
    which is what it did before these existed. A caller that cannot measure
    spend honestly should pass nothing rather than pass a guess.
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

    # Pillar 2's lever, solved once: the smallest sustained monthly increase
    # that cancels the delay. It is a path in its own right further down, and it
    # is also the figure the named levers have to cover.
    lever = offsetting_monthly_delta(cards, budget, one_time_cost, **kw)
    room, cuts = _headroom(categories), _trims(recurring)

    def _named_target(pool):
        """What a named lever has to free to hold the date.

        Pillar 2's lever is capped at the current debt budget, on the grounds
        that asking for more each month than someone puts toward debt at all is
        a refusal wearing a number. Named money is not an abstraction: its
        ceiling is the sum of things that exist in the record. So when the
        capped lever comes back None, the bisection may run to that ceiling
        instead and still be talking about real dollars.
        """
        if lever is not None:
            return lever
        total = sum(c['monthly'] for c in pool)
        if total <= 0:
            return None
        return offsetting_monthly_delta(cards, budget, one_time_cost, cap=total, **kw)

    def _named_effect(pool):
        """The set to offer from a pool of named sources, and what it does.

        The smallest set that holds the date, or — when no set does — the single
        largest candidate, whose partial effect is still true and still the
        user's to weigh (E.4). One path per lever, never a page of them. Returns
        None when the pool cannot move the date at all, because a path that
        frees money and changes nothing is noise wearing arithmetic.
        """
        if not pool:
            return None
        chosen, freed = _smallest_cover(pool, _named_target(pool))
        if not chosen:
            chosen, freed = [pool[0]], pool[0]['monthly']
        # `monthly_delta`, not a raised budget — and the difference is not
        # cosmetic. A raised budget moves the baseline too, which is right for
        # timing (the card clears whether or not the trip happens) and wrong
        # here (this money only moves if the user moves it). Measured against a
        # shifted baseline, a shift the lever says holds the date comes back
        # saying it does not.
        after = decision_impact(cards, budget, monthly_delta=freed,
                                one_time_cost=one_time_cost, **kw)
        if after['months_delta'] is None or after['months_delta'] >= gap:
            return None
        return chosen, freed, after

    # ── Lever 1: reallocation. Money inside an envelope this user's own record
    # never reached. Nothing about their spending changes, so it ranks with the
    # paths that need no cut — but the sentence carries the receipt rather than
    # an assurance that it costs nothing, because a smaller envelope is still a
    # smaller envelope, and that judgement is theirs.
    effect = _named_effect(room)
    if effect:
        chosen, freed, after = effect
        paths.append(_path(
            'reallocation',
            f"shift ${freed:.0f}/mo from {_join([c['name'] for c in chosen])}",
            '; '.join(
                f"{c['name']} is budgeted at ${c['budgeted']:.0f}/mo and never went over "
                f"${c['worst']:.0f} in {c['months_observed']} months"
                for c in chosen),
            closes=(after['months_delta'] <= 0),
            cost_months=after['months_delta'],
            requires_cut=False,
            frees_monthly=freed,
            items=chosen,
            alternatives=[c for c in room if c not in chosen][:4]))

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

    # ── Lever 4: specific-cost trimming. Named items, at what they actually
    # cost per month, with the candidates this passed over riding along so a
    # user who would sooner keep one of them can trade it for another.
    effect = _named_effect(cuts)
    if effect:
        chosen, freed, after = effect
        detail = (f"{chosen[0]['name']} costs ${chosen[0]['monthly']:.0f}/mo"
                  if len(chosen) == 1 else
                  f"{_join([c['name'] for c in chosen])} cost ${freed:.0f}/mo between them")
        paths.append(_path(
            'trim',
            f"cut {_join([c['name'] for c in chosen])}",
            detail,
            closes=(after['months_delta'] <= 0),
            cost_months=after['months_delta'],
            requires_cut=True,
            frees_monthly=freed,
            items=chosen,
            alternatives=[c for c in cuts if c not in chosen][:4]))

    # ── Lever 5: substitution, as far as it goes without inventing anything.
    # The engine cannot know what a cheaper version of a thing IS, and it does
    # not pretend to: the claim here is about the money, not about the product.
    # "$1,500 of the $2,400 fits" is arithmetic over their own numbers, where
    # "a cheaper trip holds your date" would assert that a cheaper trip exists —
    # exactly the knowledge the ledger does not hold. The other half of the
    # lever, where a new cost replaces an old one, is BYB's and is noted above.
    # Two rungs, because either alone misleads. The price that moves the date
    # by nothing is about one month of surplus whatever the decision costs —
    # true, and useless as the only answer to a $40,000 question. The price that
    # gives back one month of a fifty-seven month delay is just as useless at
    # the other end. Halving the delay the user is actually facing is derived
    # from their own gap rather than from a threshold picked here, and the pair
    # shows the relationship (C.6's "what would have to be true") instead of
    # prescribing a purchase.
    rungs = []
    for target in sorted({gap // 2, 0}, reverse=True):
        price = affordable_one_time(cards, budget, one_time_cost,
                                    max_delay_months=target, **kw)
        if price and price < one_time_cost:
            rungs.append({'months_delta': target, 'price': price})
    if rungs:
        head = rungs[0]
        paths.append(_path(
            'substitution',
            f"a version at ${head['price']:,.0f}",
            '; '.join(
                f"${r['price']:,.0f} costs {r['months_delta']} month"
                f"{'s' if r['months_delta'] != 1 else ''} instead of {gap}"
                if r['months_delta'] else
                f"${r['price']:,.0f} does not move the date at all"
                for r in rungs),
            closes=(head['months_delta'] == 0),
            cost_months=head['months_delta'],
            # Something is given up, just not out of an existing envelope — so
            # it ranks with the cuts, below waiting and below money the record
            # shows was never spent.
            requires_cut=True,
            reversible=True,
            amount=head['price'],
            items=rungs))

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
    # Substitution is excluded from this test on purpose. Every other lever
    # holds the date for the decision the user actually asked about; that one
    # holds it by changing the decision. Letting it count would replace "nothing
    # holds your date" with "$260 of your $40,000 does" — an answer to a
    # question nobody asked, in place of the one §6.4 requires.
    if not any(p['closes'] and p['kind'] != 'substitution' for p in paths):
        # §6.4: never a bare "you can't". The nearest true path is the smallest
        # change that would close it, even when nothing offered does — C.4 makes
        # it a requirement, not a nicety.
        #
        # It is searched PAST the bound on the offered lever, and the distinction
        # is the whole point: that bound exists so the engine does not propose a
        # monthly increase larger than what someone already directs at debt. Here
        # nothing is being proposed. The user is being told the smallest change
        # that would hold the date, which is a fact about their arithmetic — and
        # a fact is not pushy the way a recommendation is. Suppressing it left
        # every honest no saying only what could not be done.
        #
        # The ceiling is arithmetic rather than a policy guess: past the point
        # where a single month clears every balance and the cost with it, more
        # money changes nothing, so a minimum that exists at all exists below it.
        # A None here therefore means no monthly amount holds the date, not that
        # the search gave up — which happens when the date is set by forgiveness
        # rather than by payments.
        ceiling = sum(float(getattr(c, 'balance', 0) or 0) for c in cards) \
            + float(one_time_cost) + 1.0
        nearest = offsetting_monthly_delta(cards, budget, one_time_cost,
                                           cap=ceiling, **kw)
        # And what the named sources come to between them. When nothing here
        # closes the gap, this is the honest shape of §6.4's "here's where that
        # could come from": the money that exists, named, with its total — and
        # no suggestion that the total is enough, since on this branch it
        # demonstrably is not.
        named = room + cuts                  # sources needing no cut first
        honest_no = {
            'gap_months': gap,
            'nearest_monthly': nearest,
            'reachable': nearest is not None,
            'named_sources': named[:6],
            'named_total': round(sum(c['monthly'] for c in named), 2) if named else None,
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
