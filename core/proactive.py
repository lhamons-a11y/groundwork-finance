"""When the app may speak first — the nagging threshold, as a function.

Appendix A of `gw 2.0/GW_2.0_TEACHING_PLATFORM_BLUEPRINT.md`. Everything the
engines compute is available on the screen it belongs to; this module governs
the one further step of bringing an insight to someone who did not ask.

**Strictness is free (A.1).** The threshold is a promotion bar, not a filter. A
candidate that fails it is not discarded — it stays passive on its own surface,
where it already lives. That is why the gates below can be as hard as they are
without hiding anything: the only thing at stake is whether the app interrupts.

**Saying nothing is correct behaviour (A.3).** A week with no material event is
a silent week, not a gap to fill. Nothing here reaches for a reason to speak.

**What this module cannot check, it says so rather than pretending.** A.2's
fifth gate is timing — never mid-task, never a blocking modal — and a pure
function cannot see what the user is doing. The caller is responsible for only
asking at a natural boundary, and `verdict` records that the gate was delegated
rather than silently passing it. Verify what is verifiable, constrain the rest
by design, and never invent a checker to feel covered (§3 #10).
"""

# A.3's starting defaults. Named because they are meant to be tuned, and
# because a magic number in a branch is a decision nobody can find later.
PER_SESSION = 1
BRAKE_PER_WEEK = 2
GREEN_PER_WEEK = 2

# A.4: the user told us; we listen.
DISMISS_COOLDOWN_DAYS = 60
DISMISSALS_TO_PASSIVE = 2

# §12: gentle-proactive is paired with a user control to dial it down or off.
# A.4 sets out the division of labour — the dial is explicit control, the
# backoff is implicit learning — and they compose rather than override: someone
# who asked for fewer AND keeps dismissing gets fewer still. Neither cancels the
# other, because both are the same request made two ways.
DIAL_NORMAL = 'normal'
DIAL_FEWER = 'fewer'
DIAL_OFF = 'off'

# A.2 #1, relative to the user's own scale rather than to an absolute figure.
# Two weeks of a payoff date, or a twentieth of what they budget in a month.
MATERIAL_MONTHS = 0.5
MATERIAL_BUDGET_SHARE = 0.05


def budget_class(kind):
    """Which budget a prompt-kind spends from.

    A.3's generalised rule: **a new prompt-kind joins the budget its attention
    cost resembles; it does not mint its own.** A clarification is an
    unsolicited interruption asking the user to resolve something, which is mild
    pressure, so it costs what a brake costs. Good news is not pressure, which
    is why the green budget exists at all and why it is separate.
    """
    return 'green' if kind == 'green' else 'brake'


def is_material(candidate, monthly_budget):
    """A.2 #1. Kills most nagging on its own, and deliberately so."""
    if candidate.get('crosses_boundary'):
        return True
    if abs(float(candidate.get('months') or 0)) >= MATERIAL_MONTHS:
        return True
    budget = float(monthly_budget or 0)
    dollars = abs(float(candidate.get('dollars') or 0))
    return bool(budget) and dollars >= budget * MATERIAL_BUDGET_SHARE


def verdict(candidate, state):
    """Whether this insight may interrupt, and if not, which gate stopped it.

    Returns {'promote': bool, 'gate': str|None, 'budget': 'brake'|'green'}. The
    failing gate is named because "it stayed passive" is a thing a person may
    reasonably ask about, and because a gauntlet whose failures are anonymous
    cannot be tested.
    """
    kind = candidate.get('kind', 'brake')
    cls = budget_class(kind)
    key = candidate.get('key')
    out = {'promote': False, 'gate': None, 'budget': cls,
           # A.2 #5, delegated upward with its name on it.
           'timing_delegated': True}

    # The dial is checked before anything else, because it is the user saying
    # so. Nothing is lost by it: A.1 makes every one of these available on the
    # screen it belongs to, so turning this off silences the interruption and
    # not the insight.
    dial = state.get('dial') or DIAL_NORMAL
    if dial == DIAL_OFF:
        out['gate'] = 'dial'
        return out

    if not is_material(candidate, state.get('monthly_budget')):
        out['gate'] = 'materiality'
        return out

    # A.2 #2. A brake with no honest path is bad news with nowhere to go, and
    # this platform does not deliver that unprompted. Good news always passes.
    if cls == 'brake' and not candidate.get('has_path'):
        out['gate'] = 'actionability'
        return out

    # A.2 #3, and A.4's decay. A dismissal is an instruction, not a signal to
    # be modelled: two in a category drops it to passive for good.
    seen = (state.get('dismissed') or {}).get(key) or {}
    if seen.get('days_ago') is not None and seen['days_ago'] < DISMISS_COOLDOWN_DAYS:
        out['gate'] = 'novelty'
        return out
    category = candidate.get('category')
    if category and (state.get('category_dismissals') or {}).get(category, 0) >= DISMISSALS_TO_PASSIVE:
        out['gate'] = 'novelty'
        return out
    if (state.get('shown') or {}).get(key) is not None:
        out['gate'] = 'novelty'
        return out

    # A.2 #4. Session first: it is the tightest and the cheapest to check.
    if int(state.get('session_prompts') or 0) >= PER_SESSION:
        out['gate'] = 'budget'
        return out
    # A.4's backoff lowers the whole cadence a tier when dismissals are
    # sustained. It is the only sanctioned use of engagement data: respecting a
    # demonstrated preference, never predicting from it.
    tier = int(state.get('cadence_tier') or 0) + (1 if dial == DIAL_FEWER else 0)
    weekly = (GREEN_PER_WEEK if cls == 'green' else BRAKE_PER_WEEK) - tier
    used = int(state.get('green_last_7d' if cls == 'green' else 'brake_last_7d') or 0)
    if weekly <= 0 or used >= weekly:
        out['gate'] = 'budget'
        return out

    out['promote'] = True
    return out


def contend(candidates):
    """Which promoted candidate takes a scarce slot (A.3).

    Ranked by impact on the user's own goal — never by insight kind. A fixed
    "this sort of insight outranks that sort" is the system imposing a universal
    importance ranking, which is the E.1/E.2 error: what most needs saying to
    THIS user is not ours to pre-decide.

    The one ordering that is not by kind is by **dependency**: a contradiction
    sits upstream of anything ranked on the declaration it contradicts, so
    firing the dependent candidate first spends the slot on advice that may be
    ranked wrongly. That is checkable — does this candidate's ranking use the
    category under dispute? — which is what keeps it from being a hierarchy in
    disguise.

    Ties fall to perishability: a decision the user is about to make outranks a
    fact equally true next week, judged from what is already true and never from
    a predicted trajectory (F.8). Still even, the extra is held rather than
    fired alongside — one clear thing now, the other next cycle.
    """
    promoted = [c for c in (candidates or []) if c]
    if not promoted:
        return None

    disputed = {c.get('disputes') for c in promoted if c.get('disputes')}

    def impact(c):
        raw = c.get('goal_impact')
        if raw is None:
            raw = c.get('months')
        return None if raw is None else abs(float(raw))

    # A.3 names the case explicitly: some candidates are POSITION FACTS that do
    # not reduce to a date-impact — G's "approaching your prior peak" is its own
    # example, alongside a contradiction-check. Ranking those by impact would
    # score them zero and bury them permanently, which is not "the user's goal
    # decides" but "whatever we can express in months decides". When one is in
    # the running, perishability becomes the ruler for the whole set: surface
    # what loses the most by waiting. Judged from what is already true — a
    # checkpoint that will be behind them next month — never from a predicted
    # trajectory (F.8).
    position_fact = any(impact(c) is None for c in promoted)

    def rank(c):
        depends = c.get('depends_on') in disputed if disputed else False
        tier = 0 if c.get('disputes') else (2 if depends else 1)
        perish = 0 if c.get('perishable') else 1
        size = -(impact(c) or 0)
        return (tier, perish, size) if position_fact else (tier, size, perish)

    return sorted(promoted, key=rank)[0]
