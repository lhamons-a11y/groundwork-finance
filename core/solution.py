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
from data that exists today: timing, payoff-order, the generic monthly increase
Pillar 2 solves for, substitution as a price rather than as a product, save-
first as a plan rather than as a path (`save_first_plan`, below), and — when the
caller hands over per-category spend and the recurring ledger — reallocation and
specific-cost trimming. Those last two are the first levers here that name
something: a category, a merchant. What naming does and does not license is set
out at `_headroom` and `_trims`.

Not every lever is a path, and the distinction is load-bearing. **A path holds
the date for the decision as asked.** Three levers do not, and each is returned
on its own rather than appended to `paths`:

  * **save-first** changes when the money leaves, not whether it does
    (`save_first_plan`);
  * **substitution** changes the decision — it is in `paths` because a cheaper
    version is still this decision, but it is excluded from the honest-no test
    for the same reason;
  * **patience** changes when the decision happens (`do_nothing_note`).

The test each one fails is the same: counted as a path, it would make §6.4's
honest no vacuous. Waiting until every balance clears holds any date at all, so
"nothing holds your date" would become false for every gap, and the answer to a
$40,000 question would be "wait fifty-seven months" — a refusal wearing a
number, which is the exact thing the honest no exists to replace.

Both shapes of decision are solved. `solve_one_time_cost` prices a purchase;
`solve_monthly_cost` prices a commitment, where a new recurring cost displaces
an existing one and only the difference is felt — BYB's `replacing` mechanic
(`replacing_id` on `BYBItem`), where the user names what is replaced, because a
ledger cannot infer which of someone's commitments a new one takes the place of.

The two differ in more than units. A one-time cost is absorbed once, so what
holds the date has to be solved for; a recurring one drains for as long as the
debt lasts, so what holds the date is exactly the net cost. And a commitment can
put the budget under the minimums outright, which is not a longer delay but a
different answer — §6.4's honest no there reports the largest payment that is
payable, because "how much later" is the wrong question once the answer is "you
could not make the minimums".

**Ranking.** E.3 orders six preferences, and only two of them are universal:
waiting/timing over cutting (rule 1), and smaller/reversible over large and
permanent (rule 3). The other three key off what the user has proven flexible or
tolerated — willingness, which F.6b keeps `unclassified` for most people most of
the time. So this ranks on the universal two and stops. Not knowing someone's
strategy costs humility in ranking, not the ability to help (F.6a).
"""

import re

from core.consequence import (MAX_MONTHS, Card, affordable_monthly, affordable_one_time,
                              decision_impact, extra_above_minimums,
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
    # Health, named in full rather than left to a lucky substring. Before this,
    # 'Health Insurance' was protected only because it contains "insurance",
    # while Medications, Prescriptions, Pharmacy, Doctor, Therapy and Dental
    # were all fair game — so the engine could propose cutting someone's
    # medication by $85/month to hold a debt-free date. Arithmetically sound,
    # and the software suggesting a person ration medicine to pay a card faster.
    'health care', 'healthcare', 'medical', 'medication', 'prescription',
    'pharmacy', 'doctor', 'clinic', 'hospital', 'dental', 'dentist',
    'vision care', 'copay', 'co-pay',
    # Mental health explicitly, because it is the part most likely to be read as
    # optional: recurring, discretionary-looking, and easy to stop. It is the
    # reason this floor exists rather than an afterthought to it.
    'mental health', 'therapy', 'counseling', 'counselling', 'psychiatry',
    'psychologist',
    # Version 3 (item 47 = item 45 H2, Rob 2026-10-08). The names users type for
    # care that version 2 missed - each could be offered as money to cut:
    # medicine by any name, visits and procedures, eyes, ears and teeth, care
    # that lasts, and the emergency room by its initials.
    'medicine', 'meds', 'rx', 'insulin',
    'urgent care', 'physician', 'pediatrician', 'surgery', 'surgeon', 'ambulance',
    'ob gyn', 'obgyn', 'lab', 'lab work',
    'vision', 'eyeglasses', 'glasses', 'contacts', 'contact lenses', 'optometrist',
    'ophthalmologist', 'hearing', 'hearing aid',
    'orthodontist', 'orthodontics', 'braces',
    'long term care', 'home health', 'nursing home',
    'er', 'emergency room',
    # Utilities and food under the spellings whole-word matching (below) no
    # longer catches by accident, and "gas", which was only ever matched as part
    # of "gas / electric".
    'electricity', 'grocery', 'gasoline', 'gas',
    # item 84 (2026-10-13): the renamed fuel leaf and public charging - appended, so the version-2 terms keep their places
    'gasoline / diesel', 'ev charging',
)

# Names that are on the floor only when they are the WHOLE name. "Health" alone
# is someone's health spending; "Health Club" is a gym (s45). Version 2 got both
# right by accident - "health" sat inside "health care" - and version 3 keeps it
# on purpose.
NECESSITY_FLOOR_WHOLE_NAME = ('health',)


# The floor's rule version. Not cosmetic: `is_protected` is an interpretation
# fused directly to a policy verdict, and until 2026-09-06 it carried no version
# at all — so when health terms were added that day, every past judgement about a
# "Prescriptions" category silently changed meaning and became unreproducible.
# Nothing was corrupted, because nothing was ever stored; what was lost was the
# ability to say which rule produced an answer. This is the thin end of that fix:
# it identifies the rule without pretending the reasoning was ever recorded.
#
# Bump on any change to NECESSITY_FLOOR. Version '1' was the pre-2026-09-06 list,
# which had no health terms and is the reason this constant exists.
NECESSITY_FLOOR_VERSION = '3'
# Version '2' (2026-09-06) added the health terms. Version '3' (2026-10-08, item
# 47) added the names in its block and changed how a name is matched (below).

_WORD = re.compile(r'[a-z0-9]+')


def _floor_words(text):
    """A name as words: lower case, split on anything that is not a letter or a
    digit, a plural s dropped ("Prescriptions" and "prescription" are one word;
    "glasses" and "glasses" stay alike; "ss" is never cut)."""
    out = []
    for w in _WORD.findall(str(text).lower()):
        if len(w) > 3 and w.endswith('s') and not w.endswith('ss'):
            w = w[:-1]
        out.append(w)
    return tuple(out)


def _has_run(words, run):
    n = len(run)
    return n > 0 and any(words[i:i + n] == run for i in range(len(words) - n + 1))


_FLOOR_RUNS = tuple(_floor_words(p) for p in NECESSITY_FLOOR)
_WHOLE_NAMES = frozenset(_floor_words(p) for p in NECESSITY_FLOOR_WHOLE_NAME)


def is_protected(category_name):
    """True when a category sits on the necessity floor and may never be proposed
    for cuts. Matching stays loose on purpose - a near-miss that over-protects
    costs one unavailable lever, while a near-miss that under-protects proposes
    cutting someone's rent - but it is loose in WHOLE WORDS (version 3, item 47).
    A floor term counts when its words appear together in the name ("Doctor /
    Co-pays" has "doctor", "Urgent Care Visit" has "urgent care"). A term inside
    an unrelated word never counts (Rob 2026-10-08): "ER" was protected by
    "water", "groceries" and "therapy", "Hospitality" by "hospital", "Parenting"
    by "rent". Nor does a name inside a longer term: version 2 let "Gas" match
    "gas / electric", which in whole words would make "Home" match "nursing
    home" - so "gas" is a term, and "health" counts only as the whole name."""
    if not category_name:
        return False
    words = _floor_words(category_name)
    if not words:
        return False
    if words in _WHOLE_NAMES:
        return True
    return any(_has_run(words, run) for run in _FLOOR_RUNS)


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


# E.3 rule 2 (flexible-by-proof), within a lever's candidates. The Willingness
# Layer (core/willingness.py, WILLINGNESS_LAYER.md) hands each candidate the
# stance the user's record or their own word gives it; a category the user
# protected never arrives here at all. Flexible first, then what nobody has
# classified, then what the record says the user keeps - and within each, size,
# as before. With no willingness on a candidate this is exactly the old order.
_WILLINGNESS_ORDER = {'flexible': 0, 'unclassified': 1, 'sacred': 2}


def _willing_key(c):
    w = c.get('willingness') or {}
    return (_WILLINGNESS_ORDER.get(w.get('stance'), 1), -c['monthly'])


def _carry(c):
    """The willingness a candidate arrived with, kept on it so the path can cite it."""
    return {'willingness': c['willingness']} if c.get('willingness') else {}


def _flexible_named(categories):
    """Categories the user has shown or said are flexible, with how - the only ones a generic lever may name."""
    out = []
    for c in categories or []:
        w = (c or {}).get('willingness') or {}
        if w.get('stance') == 'flexible' and c.get('name') and not is_protected(c['name']):
            out.append({'name': c['name'], 'source': w.get('source')})
    return out


def _named_by_willingness(flex):
    """The clause the generic lever adds when it may name where the money comes from."""
    if not flex:
        return ''
    said = [f['name'] for f in flex if f['source'] == 'declared']
    shown = [f['name'] for f in flex if f['source'] != 'declared']
    parts = []
    if shown:
        parts.append(f"your record shows {_join(shown)} {'has' if len(shown) == 1 else 'have'} moved before")
    if said:
        parts.append(f"you marked {_join(said)} flexible")
    return '; ' + ' and '.join(parts)


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
                    'months_observed': int(c['months_observed']), **_carry(c)})
    out.sort(key=_willing_key)
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
                    'category': category, **_carry(r)})
    out.sort(key=_willing_key)
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


def _best_named(pool, target, evaluate, gap):
    """The set to offer from a pool of named sources, and what it does.

    Shared by both solvers. The smallest set that covers `target`, or — when no
    set does — the single largest candidate, whose partial effect is still true
    and still the user's to weigh (E.4). One path per lever, never a page of
    them. None when the pool cannot move the date at all, because a path that
    frees money and changes nothing is noise wearing arithmetic.

    `evaluate` belongs to the caller because "after" means different things: a
    one-time cost is absorbed once, a recurring one drains every month for as
    long as the debt lasts.
    """
    if not pool:
        return None
    chosen, freed = _smallest_cover(pool, target)
    if not chosen:
        chosen, freed = [pool[0]], pool[0]['monthly']
    after = evaluate(freed)
    if after['months_delta'] is None or after['months_delta'] >= gap:
        return None
    return chosen, freed, after


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
                        categories=None, recurring=None, demonstrated=None):
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
        # `monthly_delta`, not a raised budget — and the difference is not
        # cosmetic. A raised budget moves the baseline too, which is right for
        # timing (the card clears whether or not the trip happens) and wrong
        # here (this money only moves if the user moves it). Measured against a
        # shifted baseline, a shift the lever says holds the date comes back
        # saying it does not.
        return _best_named(
            pool, _named_target(pool),
            lambda freed: decision_impact(cards, budget, monthly_delta=freed,
                                          one_time_cost=one_time_cost, **kw),
            gap)

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

    # ── Lever 6: save-first is still NOT a path here, and the omission is
    # deliberate. It is the anti-loan — its value is against FINANCING — and
    # this gap is already a cash cost. The money saved comes out of the same
    # extra-above-minimums the cost would have consumed, on the same schedule,
    # so the payoff moves by the same amount either way; the engine's absorption
    # model makes the two cash flows identical rather than merely similar.
    # Offering it as a path that "closes the gap" would be flattery: the same
    # money, spent later, presented as free.
    #
    # What it honestly answers is a different question — what financing this
    # would cost instead — and that lives in `save_first_plan` below, which the
    # funding panel asks for by name rather than receiving here unasked.

    # ── The generic monthly lever (Pillar 2). A cut is implied, and a category
    # is named only where the user's record or their own word says it is
    # flexible (WILLINGNESS_LAYER.md W-C) - with which of the two it was. With
    # neither, which envelope it comes from stays the user's to choose.
    lever = offsetting_monthly_delta(cards, budget, one_time_cost, **kw)
    if lever:
        flex = _flexible_named(categories)
        paths.append(_path(
            'monthly',
            'put more toward debt',
            f"${lever:.0f}/mo more holds the date where it is{_named_by_willingness(flex)}",
            closes=True, cost_months=0, requires_cut=True, reversible=True,
            items=flex))

    paths.sort(key=_rank_key_for(demonstrated))

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

    # The floor filtered which levers could be offered at all, so the set of
    # paths - including a path that is missing - is a conclusion it produced.
    return {'gap_months': gap, 'paths': paths, 'honest_no': honest_no,
            'floor_version': NECESSITY_FLOOR_VERSION}


def _rank_key(p):
    """E.3's universal rules only, in order.

    1. Waiting/timing over cutting — a path that requires no cut ranks above one
       that does, always.
    3. Smaller and reversible over large and permanent.
    Then, among equals, the one that closes the gap and closes it soonest.

    Rule 2 (flexible-by-proof) is applied where it can be proven: among a named
    lever's candidates (`_willing_key`), from the Willingness Layer's observed
    readings and the user's own word. Rule 4 (demonstrated tolerance) applies
    only through `_rank_key_for` with an EARNED strategy label (F.6b, W-E) -
    unclassified for most people, which leaves this order exactly as it is.
    Rule 5 (spread vs concentrate) stays absent: no edit in the record shows it.
    """
    return (
        p['requires_cut'],                       # False first
        not p['reversible'],                     # reversible first
        not p['closes'],                         # closes the gap first
        p['available_in_months'] if p['available_in_months'] is not None else 0,
        p['cost_months'] if p['cost_months'] is not None else 0,
    )


def _rank_key_for(demonstrated=None):
    """E.3 rule 4: among paths that need a cut, the kind the user has DEMONSTRATED (an earned W-E label - trim or
    reallocation) comes first; everything else keeps `_rank_key`'s order. With no label this is `_rank_key`."""
    if not demonstrated:
        return _rank_key

    def key(p):
        k = _rank_key(p)
        return (k[0], p['kind'] != demonstrated) + k[1:]
    return key


def save_first_plan(cards, budget, price, strategy='avalanche',
                    today_key=None, start_month=None):
    """Lever 6, the anti-loan: what saving for it first is, and what financing
    it instead would cost — both in the user's own numbers.

    §6.1 states this lever as "save $X/mo for 4 months and buy it in cash — $0
    interest, vs. ~$Y in interest if financed", and the second half is the part
    that needs care. `$Y` is not a rate we picked: it is what the purchase does
    to this portfolio when it is CHARGED rather than saved for, simulated by the
    same engine, on a card the user actually holds.

    **Which card, and why the cheapest one.** Charging the purchase to the
    highest-rate card would produce the largest number and the most persuasive
    sentence, which is exactly the reason not to do it. The figure is priced on
    the lowest-rate card available — the most flattering financing the user
    could realistically find — and named, so the comparison understates our own
    case rather than overstating theirs. Leases and loans headed for forgiveness
    are excluded: a trip cannot be charged to either.

    **What saving does NOT do.** It does not shorten the delay. The money comes
    out of the extra above minimums either way, on the same schedule, so the
    payoff date moves by the same amount whether it is spent now or saved for
    first. That is returned as `months_delta` on the plan itself rather than
    left for a caller to imply otherwise. What saving changes is the interest,
    and that it stays off a card.

    **A finding §6.1 did not anticipate, measured 2026-09-05.** The lever is
    written there as "$0 interest, vs. ~$Y in interest if financed", which
    assumes financing always costs more. Against a real mixed-rate portfolio it
    frequently does not. Charging $2,400 to a 6% card while the extra keeps
    attacking a 22% balance costs $225 in interest; paying cash for it out of
    that same extra costs $663, because the money stops reducing a 22% balance.
    Financing is $438 cheaper and neither option moves the date more than the
    other. The arithmetic is not in doubt — it is ordinary rate arbitrage — and
    it turns on the engine's own stated assumption that a cash purchase is paid
    out of debt-reduction money, an assumption chosen because it does not
    flatter a spending decision and which happens to flatter financing.

    It changes nothing about what the platform may offer. §6.2 requires a
    solution to need no new debt, so financing is not a path here whatever the
    number says, and a surface that showed the comparison unasked would be
    offering one. The block is computed for a surface where the purchase is
    already financed and the user has raised it — BYB, whose `replacing_id`
    mechanic is the blueprint's own example — and the trip planner is handed
    the plan without it.

    Returns None when the payoff cannot be simulated at all, and a plan with
    `financed: None` when there is no card the purchase could honestly be
    priced against.
    """
    kw = dict(strategy=strategy, today_key=today_key, start_month=start_month)
    price = float(price or 0)
    if price <= 0:
        return None

    base = simulate_payoff(cards, budget, **kw)
    cash = decision_impact(cards, budget, one_time_cost=price, **kw)
    if base is None or cash['months_delta'] is None:
        return None                       # honest-null, not a guessed plan

    monthly = extra_above_minimums(cards, budget)
    if not monthly or monthly <= 0:
        # Nothing above the minimums to save out of. Saying "save $0/mo" would
        # be a plan in form and nonsense in substance.
        months_to_save = None
    else:
        months_to_save = int(-(-price // monthly))      # ceil, in whole months

    plan = {
        'price': round(price, 2),
        'monthly': monthly,
        'months_to_save': months_to_save,
        'months_delta': cash['months_delta'],
        'interest_paying_cash': cash['interest_delta'],
        'financed': None,
    }

    chargeable = [c for c in cards
                  if not getattr(c, 'is_lease', False)
                  and not getattr(c, 'is_pslf', False)
                  and float(getattr(c, 'balance', 0) or 0) > 0]
    if not chargeable:
        return plan

    target = min(chargeable, key=lambda c: float(getattr(c, 'rate', 0) or 0))
    charged = []
    for c in cards:
        charged.append(Card(
            balance=float(getattr(c, 'balance', 0) or 0) + (price if c is target else 0.0),
            rate=float(getattr(c, 'rate', 0) or 0),
            minimum=float(getattr(c, 'minimum', 0) or 0),
            name=getattr(c, 'name', 'Card') or 'Card',
            is_lease=bool(getattr(c, 'is_lease', False)),
            end_month=getattr(c, 'end_month', None),
            is_pslf=bool(getattr(c, 'is_pslf', False)),
            forgive_after_months=getattr(c, 'forgive_after_months', None),
        ))
    financed = simulate_payoff(charged, budget, **kw)
    if financed is None:
        return plan

    plan['financed'] = {
        'card': target.name,
        'apr': round(float(getattr(target, 'rate', 0) or 0), 2),
        'months_delta': financed['months'] - base['months'],
        'interest': financed['total_interest'] - base['total_interest'],
        # What financing ADDS over saving for it. The two are not alternatives
        # in name only: paying cash out of the extra costs interest too, because
        # that money stops reducing principal, and reporting the financed figure
        # alone against a notional zero would overstate the difference.
        'extra_interest': (financed['total_interest'] - base['total_interest']
                           - cash['interest_delta']),
        'extra_months': (financed['months'] - base['months']) - cash['months_delta'],
    }
    return plan


def do_nothing_note(cards, budget, one_time_cost=0.0, strategy='avalanche',
                    today_key=None, start_month=None, monthly_delta=0.0):
    """Lever 7, do-nothing quantified: what is true if nothing changes.

    §6.1 puts it as "you're on track; Z arrives on its own in 6 months if
    nothing changes", and it has two halves, both of which are computations
    rather than reassurance.

    **The decision already costs nothing.** A gap of zero or less means no lever
    is needed — but "no months" is not "no cost", so the interest it still adds
    is returned alongside, because a page that says only "this does not move
    your date" has told half the truth.

    **The current path is already the faster one.** The engine can check the one
    thing a user is most likely to wonder about — whether the other payoff order
    would do better — and prove the answer with a number. It is deliberately
    silent when the alternative IS better: lever 3 offers that as a path, and
    saying both would be the software arguing with itself. It is also silent
    with fewer than two payable balances, where the two orders are the same
    thing and "your order is optimal" would be noise dressed as insight.

    **And when the decision stops costing months at all.** Once the last balance
    clears there is no date left to delay, so `free_from_months` is exactly the
    base payoff length. It is a fact about months, not about affordability —
    money still has to exist — and it is NOT returned as a path: see the module
    docstring on why patience cannot be one without hollowing out the honest no.

    Returns None when the payoff cannot be simulated, honest-null as ever.
    """
    kw = dict(today_key=today_key, start_month=start_month)
    base = simulate_payoff(cards, budget, strategy, **kw)
    if base is None:
        return None

    impact = decision_impact(cards, budget, one_time_cost=one_time_cost,
                             monthly_delta=monthly_delta, strategy=strategy, **kw)
    gap = impact['months_delta']

    note = {
        'moves_nothing': gap is not None and gap <= 0,
        'interest_cost': impact['interest_delta'],
        'free_from_months': base['months'],
        'optimal_order': None,
    }

    payable = [c for c in cards
               if not getattr(c, 'is_lease', False)
               and not getattr(c, 'is_pslf', False)
               and float(getattr(c, 'balance', 0) or 0) > 0]
    if len(payable) < 2:
        return note

    other = 'snowball' if strategy == 'avalanche' else 'avalanche'
    alt = simulate_payoff(cards, budget, other, **kw)
    if alt is None:
        return note
    months_better = alt['months'] - base['months']
    if months_better < 0:
        return note                     # the other order wins; lever 3 says so
    note['optimal_order'] = {
        'strategy': strategy,
        'alternative': other,
        'months_better': months_better,
        'interest_better': alt['total_interest'] - base['total_interest'],
    }
    return note


def solve_monthly_cost(cards, budget, monthly_cost, replaces_monthly=0.0,
                       strategy='avalanche', today_key=None, start_month=None,
                       categories=None, recurring=None, demonstrated=None):
    """Paths that absorb a NEW RECURRING cost's effect on the payoff date.

    Substitution's other half. The one-time solver prices a purchase; this one
    prices a commitment, where a new monthly obligation displaces an existing
    one and only the difference is felt — BYB's `replacing_id` mechanic, in
    which the USER names what is being replaced, because which of someone's
    commitments a new one displaces is not something a ledger can infer.

    A recurring cost is not a one-time cost spread out, and two things follow.

    The money that holds the date is exactly the net cost — no bisection needed
    and nothing to "absorb", because the drain does not stop. Every named lever
    is therefore aimed at `net` rather than at a solved figure.

    And it can put the budget under the minimums outright, which is not a longer
    delay but a different answer. §6.4's honest no there is not about months at
    all: it reports the largest payment that is payable, because "how much
    later" is the wrong question once the answer is "you could not make the
    minimums". That case is real — BYB shipped a bug for a while where it read
    as the BEST possible outcome, months arriving as zero and rendering green.
    """
    kw = dict(strategy=strategy, today_key=today_key, start_month=start_month)
    gross = float(monthly_cost or 0)
    replaces = float(replaces_monthly or 0)
    net = gross - replaces

    if net <= 0:
        # The new commitment costs no more than the one it replaces. There is
        # nothing to solve, and manufacturing a lever here would invent a
        # problem the user does not have.
        return {'net_monthly': round(net, 2), 'gap_months': 0, 'paths': [],
                'honest_no': None,
                'reason': 'the replacement costs no more than what it replaces'}

    impact = decision_impact(cards, budget, monthly_delta=-net, **kw)
    gap = impact['months_delta']

    if gap is None:
        payable = affordable_monthly(cards, budget, gross,
                                     max_delay_months=MAX_MONTHS, **kw)
        # C.4: even a wall carries a way forward when one exists, and here only
        # one lever can move it — capacity that arrives on its own. Waiting for
        # a balance to clear frees its minimum permanently, which is exactly
        # what a repeating cost needs; nothing else raises the ceiling without
        # asking something of the user.
        waiting = None
        base = simulate_payoff(cards, budget, **kw)
        for name, info in sorted(((base or {}).get('cleared_at') or {}).items(),
                                 key=lambda kv: kv[1]['month']):
            if info['month'] >= (base or {}).get('months', 0):
                continue
            after_cap = affordable_monthly(cards, budget + info['frees_monthly'],
                                           gross, max_delay_months=MAX_MONTHS, **kw)
            if after_cap is None or (payable is not None and after_cap <= payable):
                continue                     # that wait buys nothing here
            waiting = {
                'name': name,
                'available_in_months': info['month'],
                'frees_monthly': info['frees_monthly'],
                'max_payable_monthly': round(after_cap + replaces, 2),
                'enough': after_cap >= net,
            }
            break
        return {
            'net_monthly': round(net, 2), 'gap_months': None, 'paths': [],
            'honest_no': {
                'unaffordable': True,
                # The wall, in the units the decision is made in: what this
                # thing may cost per month, replacement included, before the
                # minimums stop being coverable.
                'max_payable_monthly': (None if payable is None
                                        else round(payable + replaces, 2)),
                'replaces_monthly': round(replaces, 2),
                # And whether waiting moves it — including when it does not,
                # which is the answer BYB has always given here and the one a
                # dead end would swallow.
                'after_waiting': waiting,
            },
            'reason': 'this payment would leave the minimum payments uncovered',
        }
    if gap <= 0:
        return {'net_monthly': round(net, 2), 'gap_months': gap, 'paths': [],
                'honest_no': None, 'reason': 'nothing to close'}

    paths = []
    room, cuts = _headroom(categories), _trims(recurring)

    def _after(freed):
        # The named money offsets the drain from now on, so it nets against the
        # cost rather than being absorbed by it.
        return decision_impact(cards, budget, monthly_delta=freed - net, **kw)

    # ── Lever 1: reallocation, and ── Lever 4: trimming. Both aimed at `net`,
    # which is the whole of what holds the date when the cost repeats.
    for kind, pool in (('reallocation', room), ('trim', cuts)):
        effect = _best_named(pool, net, _after, gap)
        if not effect:
            continue
        chosen, freed, after = effect
        names = _join([c['name'] for c in chosen])
        if kind == 'reallocation':
            label = f"shift ${freed:.0f}/mo from {names}"
            detail = '; '.join(
                f"{c['name']} is budgeted at ${c['budgeted']:.0f}/mo and never went over "
                f"${c['worst']:.0f} in {c['months_observed']} months" for c in chosen)
        else:
            label = f"cut {names}"
            detail = (f"{chosen[0]['name']} costs ${chosen[0]['monthly']:.0f}/mo"
                      if len(chosen) == 1 else
                      f"{names} cost ${freed:.0f}/mo between them")
        paths.append(_path(
            kind, label, detail,
            closes=(after['months_delta'] <= 0),
            cost_months=after['months_delta'],
            requires_cut=(kind == 'trim'),
            frees_monthly=freed, items=chosen,
            alternatives=[c for c in pool if c not in chosen][:4]))

    # ── Lever 2: timing. A card clearing frees its minimum for good, which is
    # what a repeating cost needs — capacity that arrives and stays.
    base = impact['base']
    for name, info in sorted((base.get('cleared_at') or {}).items(),
                             key=lambda kv: kv[1]['month']):
        if info['month'] >= base['months']:
            continue
        after = decision_impact(cards, budget + info['frees_monthly'],
                                monthly_delta=-net, **kw)
        if after['months_delta'] is not None and after['months_delta'] < gap:
            verb = 'is forgiven' if info.get('forgiven') else 'clears'
            paths.append(_path(
                'timing', f"wait for {name}",
                f"{name} {verb} in month {info['month']}, freeing "
                f"${info['frees_monthly']:.0f}/mo",
                closes=(after['months_delta'] <= 0),
                cost_months=after['months_delta'],
                requires_cut=False,
                frees_monthly=info['frees_monthly'],
                available_in_months=info['month']))

    # ── Lever 3: payoff-order.
    other = 'snowball' if strategy == 'avalanche' else 'avalanche'
    alt = decision_impact(cards, budget, monthly_delta=-net,
                          **{**kw, 'strategy': other})
    if alt['months_delta'] is not None and alt['months_delta'] < gap:
        paths.append(_path(
            'payoff_order', f"pay in {other} order",
            f"{other} order absorbs {gap - alt['months_delta']} of the "
            f"{gap} month{'s' if gap != 1 else ''}",
            closes=(alt['months_delta'] <= 0),
            cost_months=alt['months_delta'], requires_cut=False))

    # ── Lever 5: substitution, priced GROSS — the number a person shops with.
    # The engine solves the net ceiling and hands back what the thing itself may
    # cost, replacement included: "$279/mo instead of $350" is §6.1's own
    # sentence, and it still claims nothing about what exists at that price.
    rungs = []
    for target in sorted({gap // 2, 0}, reverse=True):
        ceiling = affordable_monthly(cards, budget, net,
                                     max_delay_months=target, **kw)
        if ceiling is not None and ceiling < net:
            rungs.append({'months_delta': target,
                          'price': round(ceiling + replaces, 2),
                          'net_price': ceiling})
    if rungs:
        head = rungs[0]
        paths.append(_path(
            'substitution', f"a version at ${head['price']:,.0f}/mo",
            '; '.join(
                f"${r['price']:,.0f}/mo costs {r['months_delta']} month"
                f"{'s' if r['months_delta'] != 1 else ''} instead of {gap}"
                if r['months_delta'] else
                f"${r['price']:,.0f}/mo does not move the date at all"
                for r in rungs),
            closes=(head['months_delta'] == 0),
            cost_months=head['months_delta'],
            requires_cut=True, reversible=True,
            amount=head['price'], items=rungs))

    # ── The generic monthly lever. For a repeating cost it is not solved for,
    # it IS the net cost — and it is worth saying anyway when something is being
    # replaced, because the figure that matters is the difference rather than
    # the price on the sticker.
    flex = _flexible_named(categories)
    paths.append(_path(
        'monthly', 'put more toward debt',
        f"${net:.0f}/mo more holds the date where it is{_named_by_willingness(flex)}",
        closes=True, cost_months=0, requires_cut=True, reversible=True,
        items=flex))

    paths.sort(key=_rank_key_for(demonstrated))
    # No honest no here, and the omission is structural rather than an
    # oversight: a cost that leaves the minimums coverable is by definition
    # within the extra above them, so the money that holds the date always
    # exists in principle. When it does not, the branch above has already
    # returned the wall instead of a month count.
    return {'net_monthly': round(net, 2), 'gap_months': gap,
            'paths': paths, 'honest_no': None,
            'floor_version': NECESSITY_FLOOR_VERSION}


def accelerations(cards, budget, categories=None, recurring=None,
                  strategy='avalanche', today_key=None, start_month=None,
                  limit=5):
    """What moves the payoff date most, on the plan the user already has.

    §8's line for the Debt Payoff surface: "name the single lever that moves the
    date most; payoff-order optimization". Every solver above answers a question
    about a DECISION — a purchase, a commitment — and this one answers a
    question about the plan itself, which is the question that surface is for.

    Each entry is a single lever with the months and the interest it saves,
    never a combination. "Shift these three and cut those two" is a different
    kind of claim: it needs to know which of them this person would actually
    accept, and F.6b keeps that unclassified.

    **Ranked by impact, and only here.** Everywhere else the ordering is E.3's —
    least disruption first, no-cut before cut. This list is the answer to "what
    moves it most", and sorting that by anything other than how much it moves it
    would be answering a question nobody asked. `requires_cut` rides on every
    entry so the caller can still tell the two kinds apart, and reallocation
    from money the record shows was never spent is not a cut.

    **The assumption each entry rests on, stated in its own sentence:** the
    freed money goes to the debt. Nothing here can verify that it would, so the
    detail says "toward debt" rather than implying the saving happens by itself.
    """
    kw = dict(strategy=strategy, today_key=today_key, start_month=start_month)
    base = simulate_payoff(cards, budget, **kw)
    if base is None:
        return []                        # honest-null: no plan to accelerate

    out = []

    for source in _headroom(categories) + _trims(recurring):
        after = simulate_payoff(cards, budget + source['monthly'], **kw)
        if after is None or after['months'] >= base['months']:
            continue                     # frees money, moves nothing
        cut = (source['kind'] == 'trim')
        out.append({
            'kind': source['kind'],
            'label': (f"cut {source['name']}" if cut
                      else f"shift ${source['monthly']:.0f}/mo from {source['name']}"),
            'detail': (
                f"{source['name']} costs ${source['monthly']:.0f}/mo" if cut else
                f"{source['name']} is budgeted at ${source['budgeted']:.0f}/mo and never "
                f"went over ${source['worst']:.0f} in {source['months_observed']} months"),
            'monthly': source['monthly'],
            'months_saved': base['months'] - after['months'],
            'interest_saved': base['total_interest'] - after['total_interest'],
            'requires_cut': cut,
            'items': [source],
        })

    # Payoff order, which costs nothing at all — no money moves, only its
    # sequence. Offered only when it wins; when it does not, lever 7's
    # do_nothing_note proves the current order is already the faster one.
    other = 'snowball' if strategy == 'avalanche' else 'avalanche'
    alt = simulate_payoff(cards, budget, **{**kw, 'strategy': other})
    if alt is not None and (alt['months'] < base['months']
                            or alt['total_interest'] < base['total_interest']):
        out.append({
            'kind': 'payoff_order',
            'label': f"pay in {other} order",
            'detail': f"same money, different sequence — {other} clears the balances sooner",
            'monthly': 0.0,
            'months_saved': base['months'] - alt['months'],
            'interest_saved': base['total_interest'] - alt['total_interest'],
            'requires_cut': False,
            'items': [],
        })

    out.sort(key=lambda a: (-a['months_saved'], -a['interest_saved']))
    return out[:limit]


def _overspend(categories):
    """Categories the record shows running over their own budget, every month.

    The mirror of `_headroom`, and measured the same way: headroom is budgeted
    minus the WORST month, this is the BEST month minus budgeted. Both are the
    part of the record that held in every month the ledger can speak about.

    The average would be a larger number and a weaker claim. One holiday month
    in six is enough to make an average look chronic, and "you overspend this
    category" is a statement about someone's habits — the sort of thing that
    should be provable from their own record rather than inferred from a spike.
    A single month back inside the budget is enough to withdraw the claim, and
    that is the right sensitivity for a sentence of this kind.
    """
    out = []
    for c in categories or []:
        name = (c or {}).get('name')
        budgeted, best = c.get('budgeted'), c.get('min_observed')
        if not name or budgeted is None or best is None:
            continue
        if int(c.get('months_observed') or 0) < MIN_MONTHS_OBSERVED:
            continue
        over = float(best) - float(budgeted)
        if over < MIN_MATERIAL_MONTHLY:
            continue
        out.append({
            'kind': 'overspend',
            'name': name,
            'monthly': round(over, 2),
            'budgeted': float(budgeted),
            'floor': float(best),
            'months_observed': int(c['months_observed']),
            # E.1 again, and it changes what the honest lesson IS rather than
            # just what may be proposed. A category on the necessity floor that
            # runs over every month is not a spending problem to be corrected;
            # it is a budget set below what the thing actually costs, and the
            # honest correction is to the number, not to the groceries.
            'protected': is_protected(name),
            # Which rule said so. A verdict without its rule version cannot be
            # reproduced once the rule moves, and the rule has moved before.
            'protected_rule_version': NECESSITY_FLOOR_VERSION,
        })
    out.sort(key=lambda c: -c['monthly'])
    return out


def budget_pressure(cards, budget, categories=None, strategy='avalanche',
                    today_key=None, start_month=None, limit=3):
    """What each overspent category costs, and where the money could come from.

    §8's line for the Budget surface: "this category's overspend costs ~6 weeks;
    here's the reallocation that fixes it." Both halves are here — the cost, in
    the same currency the rest of this app prices decisions in (time on the
    payoff date), and the reallocation, drawn from envelopes the record shows
    were never emptied.

    **The assumption, which is the app's existing one.** Money that does not
    reach the debt costs time; that is how the trip planner has priced a
    purchase since Pillar 1, and pricing an overspend any other way would give
    the same dollar two different meanings on two screens. It does mean the
    figure is a counterfactual: it is what bringing the category back to its own
    budget would save, not a bill anyone is being handed.

    A category cannot fund itself: the reallocation for an overspend never draws
    on the category that is over. Returns [] when there is no debt to price
    against — without a date, an overspend has no cost this engine can name, and
    inventing one would be the fabrication R8 exists to stop.
    """
    kw = dict(strategy=strategy, today_key=today_key, start_month=start_month)
    base = simulate_payoff(cards, budget, **kw)
    if base is None:
        return []

    room = _headroom(categories)
    out = []
    for over in _overspend(categories)[:limit]:
        # Item 46 (CARE_NOT_PRICED.md C2; item 45 H1, §0.1): a category on the
        # necessity floor is described - its budget is set below what it costs -
        # and never priced on the debt-free date. Months and interest for
        # someone's medicine is an accusation, not information, and the only
        # counterfactual it implies is the care not happening.
        priced = not over['protected']
        after = simulate_payoff(cards, budget + over['monthly'], **kw) if priced else None
        if priced and after is None:
            continue
        sources = [r for r in room if r['name'] != over['name']]
        chosen, freed = _smallest_cover(sources, over['monthly'])
        out.append({
            'name': over['name'],
            'monthly': over['monthly'],
            'budgeted': over['budgeted'],
            'floor': over['floor'],
            'months_observed': over['months_observed'],
            'protected': over['protected'],
            'priced': priced,
            'months_cost': (base['months'] - after['months']) if priced else None,
            'interest_cost': (base['total_interest'] - after['total_interest']) if priced else None,
            # The fix, when the record can name one. `monthly` is what covering
            # this actually takes — the overspend — not the room the named
            # envelopes happen to have: reporting the capacity said "covering it
            # would take $190/mo" of a $120/mo gap, which asks for more than the
            # problem costs. `available` keeps the capacity, because a source
            # with barely enough and one with room to spare are not the same
            # offer.
            'fix': ({'sources': chosen,
                     'monthly': over['monthly'],
                     'available': freed} if chosen else None),
        })
    return out


def past_charge_lesson(cards, budget, amount, strategy='avalanche',
                       today_key=None, start_month=None):
    """What one charge cost, priced by what that money would have done here.

    §8's line for the Ledger: "a large charge → retrospective, past-tense lesson
    + §6 options". The lesson is a counterfactual and is written as one — had
    this money gone to the debt, the date would be N months earlier — never as
    a verdict on the charge. Why someone spent it is not knowable from a ledger
    row, and the platform's non-judgment rests on not pretending otherwise.

    "Large" is deliberately not a dollar threshold. The caller keeps the biggest
    recent charges and this prices them; what makes one worth a sentence is that
    it moved the date by a month or more, which is a fact about this portfolio
    rather than a number picked for all portfolios. A $900 charge is large
    against one plan and rounding against another.

    Returns None when the payoff cannot be simulated — with no date, a charge
    has no cost this engine can name.
    """
    kw = dict(strategy=strategy, today_key=today_key, start_month=start_month)
    amount = float(amount or 0)
    if amount <= 0:
        return None
    base = simulate_payoff(cards, budget, **kw)
    if base is None:
        return None
    had_it = simulate_payoff(cards, budget, one_time_extra=amount, **kw)
    if had_it is None:
        return None
    return {
        'amount': round(amount, 2),
        'months_cost': base['months'] - had_it['months'],
        'interest_cost': base['total_interest'] - had_it['total_interest'],
        'base_months': base['months'],
    }


def capacity_unlocked(cards, budget, liquid, monthly_expenses,
                      strategy='avalanche', today_key=None, start_month=None):
    """What a balance the user could now cover outright would actually enable.

    §8's line for Net Worth is "you crossed $X — here's what that enables", and
    the first half is the trap. A round number crossed is a milestone invented
    by whoever picked the number, and celebrating one is engagement dressed as
    teaching. The crossing that means something is not $10,000; it is liquid
    savings reaching a balance the user actually holds, which is a threshold
    their own portfolio defines.

    (Nor is a crossing DATE claimed. Net-worth snapshots record totals, not the
    liquid share, so when this first became true is not recoverable from what is
    recorded — and a date that cannot be recovered will not be guessed at.)

    **The reserve.** Clearing a balance with savings is only an option if
    something is left, and C.5 is explicit that a path breaking the user's
    stability is not offered however well the math works. The floor here is one
    month of their own recorded expenses: the smallest buffer expressible in
    their numbers rather than a rule about what is adequate, which is not this
    engine's to state. With no recorded expenses there is no way to express a
    buffer at all, and the answer is nothing rather than a guess.

    **What it does not do.** Paying a balance from savings does not raise net
    worth by a cent — the same money moves from one side of the sheet to the
    other. On a page whose whole subject is that number going up, saying so is
    the difference between teaching and cheerleading, so `changes_net_worth` is
    returned false and the surface is expected to say it out loud.
    """
    kw = dict(strategy=strategy, today_key=today_key, start_month=start_month)
    liquid = float(liquid or 0)
    monthly_expenses = float(monthly_expenses or 0)
    if liquid <= 0 or monthly_expenses <= 0:
        return []

    base = simulate_payoff(cards, budget, **kw)
    if base is None:
        return []

    spendable = liquid - monthly_expenses
    if spendable <= 0:
        return []

    out = []
    for card in cards:
        balance = float(getattr(card, 'balance', 0) or 0)
        if balance <= 0 or balance > spendable:
            continue
        # A lease cannot be settled early and a loan headed for forgiveness is
        # money burned — the engine already refuses to send extra to either, and
        # spending savings on them would be worse than sending extra.
        if getattr(card, 'is_lease', False) or getattr(card, 'is_pslf', False):
            continue

        rest = [c for c in cards if c is not card]
        after = simulate_payoff(rest, budget, **kw) if rest else None
        if rest and after is None:
            continue                      # cannot price it: say nothing
        months_after = after['months'] if after else 0
        interest_after = after['total_interest'] if after else 0
        left = liquid - balance
        out.append({
            'name': getattr(card, 'name', 'that balance'),
            'balance': round(balance, 2),
            'frees_monthly': round(float(getattr(card, 'minimum', 0) or 0), 2),
            'months_saved': base['months'] - months_after,
            'interest_saved': base['total_interest'] - interest_after,
            'clears_all_debt': not rest,
            'liquid_after': round(left, 2),
            # Shown, not tested against a standard. How many months of their own
            # recorded expenses would still be sitting there is a fact; whether
            # that is enough is the user's judgement and nobody else's.
            'months_of_expenses_after': round(left / monthly_expenses, 1),
            'changes_net_worth': False,
        })

    out.sort(key=lambda c: (-c['months_saved'], -c['interest_saved']))
    return out


def fund_pace(target, current, planned_monthly, deadline_months=None,
              observed_monthly=None, samples=0, categories=None, recurring=None,
              since_break=None):
    """Where a savings target lands at the pace it is actually being fed, and
    the lever that moves that date.

    §8's line for the sinking / college / gift funds: "causal pace narration —
    on-track/behind + the lever that changes the finish date". The pace badge
    those surfaces already carry says how reliably the plan is being met; it
    does not say when the thing arrives, or what would make it arrive sooner.

    **Which pace.** The observed one when the record can support it, the planned
    one otherwise, and `pace_source` says which — a finish date computed from a
    plan is a statement about the plan, and calling it a projection of behaviour
    would be borrowing certainty from data that does not exist. Below
    MIN_MONTHS_OBSERVED contributions there is no pace, only a plan.

    **No compounding.** A sinking fund is money set aside, not invested; adding
    a return would be inventing one. Months here are `remaining / monthly`,
    rounded up, because a part month does not finish the fund.

    **The lever** is the same named money every other surface draws on, and it
    is aimed at the shortfall rather than at the whole contribution: what closes
    the gap between the pace and the deadline is the difference, not the plan.

    **A break** (F.8; BREAK_DETECTOR.md ruling 6). When the contributions
    changed level, the caller passes only the months since as `observed_monthly`
    / `samples` and the break as `since_break`. Too few of them and there is no
    observed pace - never the average from before the change - and the result
    says so (`insufficient_since_break`), so the date it carries is plainly the
    plan's.
    """
    target = float(target or 0)
    current = float(current or 0)
    remaining = target - current
    planned = float(planned_monthly or 0)

    if target <= 0:
        return None
    if remaining <= 0:
        return {'funded': True, 'remaining': 0.0}

    enough = int(samples or 0) >= MIN_MONTHS_OBSERVED
    pace = float(observed_monthly or 0) if enough and observed_monthly else planned
    pace_source = 'observed' if (enough and observed_monthly) else 'plan'

    def finish_at(rate):
        if not rate or rate <= 0:
            return None
        return int(-(-remaining // rate))          # ceil, in whole months

    out = {
        'funded': False,
        'remaining': round(remaining, 2),
        'planned_monthly': round(planned, 2),
        'pace_monthly': round(pace, 2) if pace else 0.0,
        'pace_source': pace_source,
        'samples': int(samples or 0),
        'finish_months': finish_at(pace),
        'deadline_months': deadline_months,
        'on_track': None,
        'short_monthly': None,
        'lever': None,
        'since_break': ({k: since_break[k] for k in ('month', 'direction', 'before', 'after')}
                        if since_break else None),
        'insufficient_since_break': bool(since_break) and not enough,
    }
    if out['finish_months'] is None:
        # Nothing is being contributed and nothing is planned. There is no
        # finish date to name, and naming one anyway is the fabrication R8
        # exists to stop.
        return out

    if deadline_months is None:
        return out                                 # a date, but nothing to miss

    if deadline_months <= 0:
        out['on_track'] = False
        return out

    out['on_track'] = out['finish_months'] <= deadline_months
    if out['on_track']:
        return out

    required = remaining / float(deadline_months)
    short = required - pace
    out['short_monthly'] = round(short, 2)
    if short <= 0:
        return out

    chosen, freed = _smallest_cover(_headroom(categories) + _trims(recurring), short)
    if chosen:
        out['lever'] = {
            'sources': chosen,
            'monthly': round(short, 2),           # what the gap costs, not the room
            'available': freed,
            'finish_months': finish_at(pace + short),
        }
    return out


# A rate over two decisions is an anecdote wearing a percentage. Three is the
# same floor every other reader here uses, and for the same reason: below it
# there is a record of events but not of a practice.
MIN_DECISIONS = 3


def decision_memory(records):
    """What the user's own decision history says, and nothing beyond it.

    Pillar 5 (§7): read `byb_purchase_decision` and show walkaway discipline and
    estimate bias. It is a READER — the events are already written and nothing
    has ever read them back, which is the collect-and-ignore loop the blueprint
    names.

    Each record is {decision, variance_pct}. Two rules do the work.

    **Silence is not a decision.** An item with no decision recorded is not a
    walkaway; it is a purchase still being thought about, or one the user never
    came back to. Counting it as a walkaway would infer a choice from an absence,
    which is the one inference this platform refuses — and it is exactly what the
    list on that page has been doing.

    **A record, never a forecast.** "Walked away from 4 of 7" is a receipt. "You
    usually walk away" is a prediction about a person, which F.6b keeps
    unclassified and E.2 forbids outright. Rates are returned with the sample
    count attached so nothing has to be taken on faith, and no direction is
    extrapolated from them.

    Estimate bias is positive when things cost MORE than estimated, because
    that is the direction of the variance the historian already logs, and it is
    computed only over decisions that produced a real comparison — a same-day
    commit has no actual to compare against, and the writer is careful not to
    log a fabricated zero.
    """
    records = [r for r in (records or []) if r]
    decided = [r for r in records if r.get('decision') in ('commit', 'walkaway')]
    walkaways = [r for r in decided if r['decision'] == 'walkaway']
    priced = [r for r in decided if r.get('variance_pct') is not None]

    out = {
        'decisions': len(decided),
        'walkaways': len(walkaways),
        'commits': len(decided) - len(walkaways),
        'walkaway_rate_pct': None,
        'estimate': None,
    }
    if len(decided) >= MIN_DECISIONS:
        out['walkaway_rate_pct'] = round(len(walkaways) / len(decided) * 100)

    if len(priced) >= MIN_DECISIONS:
        bias = sum(float(r['variance_pct']) for r in priced) / len(priced)
        out['estimate'] = {
            'samples': len(priced),
            'bias_pct': round(bias, 1),
            # Named rather than left to a sign the reader has to interpret.
            'direction': 'under' if bias > 2 else 'over' if bias < -2 else 'even',
        }
    return out


# D.5: recency governs FRAMING, not truth. Inside this many months an action is
# spoken of as just done ("because you cleared the Visa"); outside it the same
# cause is stated as a position ("your plan now carries $180/mo it did not").
# The fact does not change at the boundary, only the tense.
FRESH_CREDIT_MONTHS = 3


def green_light(cards, budget, drivers, strategy='avalanche',
                today_key=None, start_month=None):
    """What deliberate action freed, and what that now covers (Pillar 4, App. D).

    §7 states it as "you freed $180/mo, this fits". Appendix D spends four
    sections on what may go in front of that number, and the filtering is the
    substance of this function rather than the arithmetic.

    **Only deliberate action, above the baseline (D.4).** A driver arrives with
    `deliberate` already decided by the caller, which is the only layer that can
    see whether a balance cleared because someone attacked it or because the
    minimums ran their course. Paying the minimum is the expected floor, not an
    achievement; capacity that arrived that way is reported as capacity and
    credited to nobody. "Real credit only, or none."

    **Never the market, never a raise (D.3, D.6).** No investment or income
    figure reaches this function, and that is by construction rather than by
    filtering: the caller passes cleared balances, extra payments and
    walkaways. A raise is a bigger opportunity to do the real thing, not the
    real thing; a paper gain is not an action at all.

    **Top one or two by magnitude, or say it was diffuse (D.5).** Naming the
    largest driver and implying it was the whole story is a cherry-pick. When no
    driver carries a third of the total, the honest answer is that it was a lot
    of small things.

    **What it enables** is the counterfactual: the same plan without that
    monthly capacity. It understates, because a cleared balance would also still
    carry its balance, and understating is the right direction for a number
    attached to praise.
    """
    kw = dict(strategy=strategy, today_key=today_key, start_month=start_month)
    drivers = [d for d in (drivers or []) if float(d.get('monthly') or 0) > 0]
    if not drivers:
        return None

    credited = [d for d in drivers if d.get('deliberate')]
    freed = round(sum(float(d['monthly']) for d in credited), 2)
    if freed <= 0:
        # Capacity arrived, but not from anything anyone chose to do. D.4 is
        # explicit that praising a floor erodes trust, so there is no light here
        # — the capacity itself still shows up wherever capacity is shown.
        return None

    ranked = sorted(credited, key=lambda d: -float(d['monthly']))
    top = ranked[:2]
    diffuse = float(top[0]['monthly']) < freed / 3.0

    now = simulate_payoff(cards, budget, **kw)
    without = simulate_payoff(cards, max(0.0, budget - freed), **kw)
    months_sooner = (without['months'] - now['months']
                     if now is not None and without is not None else None)
    months_ago = [int(d['months_ago']) for d in credited
                  if d.get('months_ago') is not None]
    return {
        'freed_monthly': freed,
        'drivers': ([] if diffuse else top),
        'diffuse': diffuse,
        'driver_count': len(credited),
        # D.5's framing switch, and only a framing switch.
        'fresh': bool(months_ago) and min(months_ago) <= FRESH_CREDIT_MONTHS,
        'months_sooner': months_sooner,
        # What it now covers, and this is the whole of it: the freed figure IS
        # the ceiling. A commitment up to that much puts the date back where it
        # stood before, by construction — the counterfactual above is exactly
        # that plan. An earlier draft reported how much more one-time cost now
        # "fits", which came back as $2.00: the price that moves no month is
        # about one month of surplus at any budget, so the difference between
        # two budgets is noise wearing a dollar sign.
        # Capacity that arrived without anyone deciding anything. Reported so a
        # caller can show the number honestly, never as credit.
        'uncredited_monthly': round(
            sum(float(d['monthly']) for d in drivers if not d.get('deliberate')), 2),
    }
