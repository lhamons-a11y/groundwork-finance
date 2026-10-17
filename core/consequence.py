"""Consequence engine — what a financial decision does to the payoff date.

Pillar 1 of `gw 2.0/GW_2.0_TEACHING_PLATFORM_BLUEPRINT.md`. Lives in Python
because `gw 2.0/CALCULATION_PLACEMENT.md` puts claim-backing derivations here:
this number is used to tell the user something is true, a second consumer (the
assistant) is coming, and neither it nor the teaching layer can call into
`app.js`.

It is a faithful port of `_simulatePayoffStrategy` (app.js) plus **one dimension
that function never had**: a one-time cost. That gap is the whole reason this
exists. The trip planner needed to price a one-time expense, `_simulatePayoff`
accepted only a monthly delta, so the caller substituted
`(total / income) * 30` — measured on 2026-09-03 as understating the real figure
by 4.4x to 17.4x, worst for the tightest budgets, because it divided by income
when the driver is surplus over minimums.

`tests/test_consequence_parity.py` runs this against the JS under node on
randomised portfolios; they must agree to the month.
"""

import contextlib
import contextvars
import math
from dataclasses import dataclass

# ── Item 90: the health reserve's schedule (gw 2.0/RESERVE_AWARE_DATES.md, ruled 2026-10-16) ─────────────────────
# The household's plan - {'choice': 'before' | 'alongside', 'monthly', 'gap'} or None - is set once per request by the
# server (core/health_reserve.request_plan). Outside a request (tests, scripts) it is None and nothing changes.
RESERVE_PLAN = contextvars.ContextVar('reserve_plan', default=None)
_NO_RESERVE = contextvars.ContextVar('no_reserve', default=False)


@contextlib.contextmanager
def no_reserve():
    """Item 88's own comparison asks the engine without the household's choice, so "after" stays its comparison
    point (D5). The only sanctioned opt-out; s230 lists its callers."""
    tok = _NO_RESERVE.set(True)
    try:
        yield
    finally:
        _NO_RESERVE.reset(tok)


def reserve_schedule(extra):
    """The months of money going to the reserve, from THIS calculation's own extra above the minimums (D2):
    before = all of it, alongside = the person's amount capped at it, for as many months as the gap needs."""
    if _NO_RESERVE.get():
        return None
    plan = RESERVE_PLAN.get()
    if callable(plan):
        plan = plan()
    if not plan or not plan.get('gap') or extra <= 0:
        return None
    x = extra if plan['choice'] == 'before' else min(float(plan.get('monthly') or 0), extra)
    if x <= 0:
        return None
    return [-x] * math.ceil(plan['gap'] / x)

MAX_MONTHS = 360          # matches the JS loop cap
SETTLED = 0.01            # a balance at or under this is cleared, as in the JS


@dataclass
class Card:
    balance: float
    rate: float           # APR percent, e.g. 22.0
    minimum: float
    name: str = 'Card'
    is_lease: bool = False
    end_month: str = None   # 'YYYY-MM'; a lease past this is written off
    is_pslf: bool = False   # headed for forgiveness: minimums only, never extra
    # Months from now until the balance is forgiven, for a loan on an
    # income-driven forgiveness plan. None means WE DO NOT KNOW — not "never".
    # PSLF forgives after 120 qualifying payments, IBR/PAYE/SAVE after 240, so
    # this is (program total - paymentsMade). The caller computes it because the
    # caller holds the record; the engine refuses to guess.
    forgive_after_months: int = None


def _prepare(cards):
    """Mirror the JS mapping: clamp, drop expired leases, drop zero balances."""
    out = []
    for c in cards:
        out.append(Card(
            balance=max(0.0, float(c.balance or 0)),
            rate=max(0.0, float(c.rate or 0)),
            minimum=max(1.0, float(c.minimum or 25)),
            name=c.name or 'Card',
            is_lease=bool(c.is_lease),
            end_month=c.end_month,
            is_pslf=bool(getattr(c, 'is_pslf', False)),
            forgive_after_months=getattr(c, 'forgive_after_months', None),
        ))
    return [c for c in out if c.balance > 0]


def simulate_payoff(cards, budget, strategy='avalanche', one_time_cost=0.0,
                    today_key=None, start_month=None, one_time_extra=0.0, path=None, extra_schedule=None):
    """Months until every balance clears, or None if the budget cannot cover
    the minimums — the JS returns null there and so do we, rather than a
    fabricated large number.

    one_time_cost is money that will NOT reach the debt: it consumes the extra
    above minimums until absorbed. That models paying cash from the same
    surplus the extra came from, which is the optimistic reading — financing it
    costs more. The assumption is stated because being optimistic here is the
    direction that flatters a spending decision.

    one_time_extra is the mirror, and it exists for a question in the past
    tense: money that DID go somewhere else, priced by what it would have done
    here. It lands once, in the first month, on top of that month's budget. For
    a charge already on a card this slightly understates the cost, because the
    interest that has accrued since the charge is not unwound — understating is
    the right direction for a number attached to something already done.

    path, when a list is passed, receives the total still owed at the end of
    each month (SCENARIOS.md SC6's charts). It changes nothing else.

    extra_schedule, when a list is passed, adds its month's amount to that
    month's budget (month 1 is the first entry); months past its end add
    nothing. It is how a trip's payback order is priced (TRIP_FUNDING_COACH.md
    T5) without a second engine.
    """
    data = _prepare(cards)
    if today_key is not None:
        data = [c for c in data if not (c.is_lease and c.end_month and c.end_month < today_key)]
    if not data:
        return None

    total_min = sum(c.minimum for c in data)
    if budget < total_min:
        return None
    # Item 90 (RESERVE_AWARE_DATES.md D1-D3): the household's health reserve choice, when there is one, reaches every
    # payoff date here, in the one engine - both sides of every what-if alike. Minimums are untouched: the schedule
    # only takes from the money above them. No choice, "after", no target or a full reserve: nothing changes.
    sched = reserve_schedule(float(budget) - total_min)
    if sched:
        base = list(extra_schedule or [])
        extra_schedule = [(base[i] if i < len(base) else 0.0) + (sched[i] if i < len(sched) else 0.0)
                          for i in range(max(len(base), len(sched)))]

    # Extra payment skips leases (fixed end date, cannot be paid early) and PSLF
    # loans (headed for forgiveness — extra principal there is money burned).
    # Both still receive their minimums above. This mirrors _simulatePayoff.
    order = sorted(
        [c for c in data if not c.is_lease and not c.is_pslf],
        key=(lambda c: c.balance) if strategy == 'snowball' else (lambda c: -c.rate))

    bals = [c.balance for c in data]
    # forgive_after_months <= 0 means the qualifying payments are already made:
    # the balance is gone now, not after one more payment.
    for i, c in enumerate(data):
        if c.forgive_after_months is not None and c.forgive_after_months <= 0:
            bals[i] = 0.0
    remaining_cost = float(one_time_cost or 0)
    month, total_interest = 0, 0.0
    first_cleared_month, first_cleared_name = None, None
    # When each balance reaches zero. The timing lever (§6.1 #2) is built on
    # this: a card clearing frees its minimum, which is capacity arriving with
    # no cut required — the least-disruptive path there is (E.3 rule 1).
    cleared_at = {}

    while month < MAX_MONTHS and any(b > SETTLED for b in bals):
        month += 1
        sim_key = _month_key(start_month, month)
        extra = float(budget) + (float(one_time_extra or 0) if month == 1 else 0.0)
        if extra_schedule and month <= len(extra_schedule):
            extra += float(extra_schedule[month - 1] or 0)

        for i, c in enumerate(data):
            if bals[i] <= 0:
                continue
            if c.is_lease and c.end_month and sim_key and sim_key > c.end_month:
                bals[i] = 0.0
                continue
            interest = bals[i] * (c.rate / 100.0 / 12.0)
            bals[i] += interest
            total_interest += interest
            pay = min(c.minimum, bals[i])
            bals[i] = max(0.0, bals[i] - pay)
            extra -= pay

        # Forgiveness ends the loan outright — it does not amortise to zero.
        # Under an income-driven plan the balance often GROWS the whole time and
        # is then written off. Applied AFTER this month's minimum, because the
        # final qualifying payment is made in that month and forgiveness follows
        # it; zeroing first would skip a payment and land the date a month early.
        for i, c in enumerate(data):
            if c.forgive_after_months is not None and month >= c.forgive_after_months:
                bals[i] = 0.0

        # The one-time cost takes from the extra, never from the minimums:
        # skipping a minimum is a missed payment, which is a different event.
        if remaining_cost > 0 and extra > 0:
            taken = min(remaining_cost, extra)
            extra -= taken
            remaining_cost -= taken

        for c in order:
            if extra <= SETTLED:
                break
            i = data.index(c)
            if bals[i] <= 0:
                continue
            applied = min(extra, bals[i])
            bals[i] = max(0.0, bals[i] - applied)
            extra -= applied

        for i, c in enumerate(data):
            if bals[i] <= SETTLED and c.name not in cleared_at:
                cleared_at[c.name] = {'month': month, 'frees_monthly': c.minimum,
                                      'forgiven': c.forgive_after_months is not None
                                      and month >= c.forgive_after_months}
                if first_cleared_month is None:
                    first_cleared_month, first_cleared_name = month, c.name
        if path is not None:
            path.append(round(sum(bals), 2))

    undated = [c.name for c in data if c.is_pslf and c.forgive_after_months is None]
    return {
        'months': month,
        'total_interest': round(total_interest),
        'first_cleared_month': first_cleared_month,
        'first_cleared_name': first_cleared_name,
        'cleared_at': cleared_at,
        # A loan on a forgiveness plan whose payment count we do not have cannot
        # be dated. Modelling it as amortising to zero is what produced an
        # 18-year figure for someone ten months from forgiveness, so callers are
        # told rather than left to assume 'months' covers everything.
        'undated_forgiveness': undated,
        'covers_all_debt': not undated,
        # Any modelled forgiveness assumes qualifying employment stays certified
        # (`certifiedUntil` in the PSLF record). That is the user's own
        # assumption in being on the plan, but it is not a certainty and the
        # figure should not be presented as one.
        'conditional_on_certification': any(
            c.forgive_after_months is not None for c in data),
    }


def extra_above_minimums(cards, budget):
    """What is left of the debt budget once every minimum is paid.

    This is the money that actually reduces principal, and it is the pool
    `one_time_cost` is drawn from — so it is also the pool a save-first plan
    saves out of. Saying which pool a plan draws on matters: the trip planner's
    own "surplus" is what remains AFTER the debt payment, a different pool
    entirely, and a page that prices a decision against one while timing it
    against the other is telling the user two things about the same money.

    None when the budget cannot cover the minimums — the same honest-null
    `simulate_payoff` returns there, for the same reason.
    """
    data = _prepare(cards)
    if not data:
        return None
    total_min = sum(c.minimum for c in data)
    if float(budget) < total_min:
        return None
    return round(float(budget) - total_min, 2)


def _month_key(start_month, offset):
    if not start_month:
        return None
    y, m = int(start_month[:4]), int(start_month[5:7])
    m += offset - 1
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f'{y:04d}-{m:02d}'


def decision_impact(cards, budget, monthly_delta=0.0, one_time_cost=0.0,
                    strategy='avalanche', today_key=None, start_month=None):
    """The blueprint's Pillar 1 signature. Returns the base and the decided
    case side by side, plus the delta — never a delta alone, so a caller can
    always show its work (Appendix B).

    Returns None for either side that cannot be simulated, rather than a
    number: honest-null, no history no claim.
    """
    base = simulate_payoff(cards, budget, strategy,
                           today_key=today_key, start_month=start_month)
    after = simulate_payoff(cards, budget + float(monthly_delta or 0), strategy,
                            one_time_cost=one_time_cost,
                            today_key=today_key, start_month=start_month)
    if base is None or after is None:
        return {'base': base, 'after': after, 'months_delta': None,
                'interest_delta': None}
    return {
        'base': base,
        'after': after,
        'months_delta': after['months'] - base['months'],
        'interest_delta': after['total_interest'] - base['total_interest'],
    }


def affordable_one_time(cards, budget, one_time_cost, strategy='avalanche',
                        today_key=None, start_month=None, max_delay_months=0):
    """The largest one-time cost whose delay stays within `max_delay_months`.

    §6.1's substitution lever, taken as far as it can honestly go. The engine
    does not know what a cheaper version of a thing IS — that is domain
    knowledge the ledger does not hold, and the blueprint's own example (a
    $220/mo car instead of $350/mo) comes from BYB, where the USER names what is
    being replaced. What can be computed without inventing anything is the
    price, and the price is a curve rather than a number: at `max_delay_months`
    of 0 this is what fits before the date moves at all, and at larger targets
    it is what a smaller version of the same decision would have to cost to give
    a month back.

    Both ends of that curve are needed, because either alone misleads. Against a
    $775/mo budget, the amount that moves nothing is about $116 — roughly one
    month of surplus, which is the granularity of the model rather than a
    meaningful alternative — so "keep it under $116" would be the answer to a
    $900 decision and to a $40,000 one alike. Priced against a delay the user is
    actually facing, the same arithmetic says something they can use.

    Rounded DOWN, the mirror of why the monthly lever rounds up — rounded up,
    the figure would name a price that does not actually hold to the target.
    Returns None when the payoff cannot be simulated, and 0.0 when nothing fits.
    """
    target = max(0, int(max_delay_months or 0))

    def delta_at(x):
        d = decision_impact(cards, budget, one_time_cost=x, strategy=strategy,
                            today_key=today_key, start_month=start_month)
        return d['months_delta']

    if delta_at(0) is None:
        return None                              # unsimulatable, not affordable
    ceiling = float(one_time_cost or 0)
    if ceiling <= 0:
        return 0.0
    top = delta_at(ceiling)
    if top is not None and top <= target:
        return round(ceiling, 2)                 # all of it already fits

    # Monotonic in x — spending more never brings the payoff date forward — so
    # bisect, holding the invariant that lo fits and hi does not.
    lo, hi = 0.0, ceiling
    for _ in range(40):
        mid = (lo + hi) / 2.0
        d = delta_at(mid)
        if d is not None and d <= target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1.0:
            break
    return float(int(lo))


def affordable_monthly(cards, budget, monthly_cost, strategy='avalanche',
                       today_key=None, start_month=None, max_delay_months=0):
    """The largest recurring cost whose delay stays within `max_delay_months`.

    §6.1's substitution lever for a cost that repeats, and the blueprint's own
    example of it: "a $220/mo car instead of $350/mo keeps your date where it
    is." The $220 is not a car anyone found — it is the price at which the date
    stops moving, computed from this portfolio. What is on the lot at that price
    is the user's to discover, and this says nothing about it.

    A recurring cost is not a one-time one spread out: it drains every month for
    as long as the debt lasts, so it can push the budget below the minimums
    outright. That case comes back from the simulator as None, and None is
    treated here as "does not fit" rather than as an error — it is the honest
    top of the range, and the reason `max_delay_months` may be set high to find
    the largest payment that is payable at all.

    Rounded DOWN, as `affordable_one_time` is, and for the same reason.
    """
    target = max(0, int(max_delay_months or 0))

    def delta_at(x):
        d = decision_impact(cards, budget, monthly_delta=-float(x),
                            strategy=strategy, today_key=today_key,
                            start_month=start_month)
        return d['months_delta']

    if delta_at(0) is None:
        return None                              # unsimulatable before it starts
    ceiling = float(monthly_cost or 0)
    if ceiling <= 0:
        return 0.0
    top = delta_at(ceiling)
    if top is not None and top <= target:
        return round(ceiling, 2)                 # the whole payment already fits

    lo, hi = 0.0, ceiling                        # lo fits, hi does not
    for _ in range(40):
        mid = (lo + hi) / 2.0
        d = delta_at(mid)
        if d is not None and d <= target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1.0:
            break
    return float(int(lo))


def offsetting_monthly_delta(cards, budget, one_time_cost, strategy='avalanche',
                             today_key=None, start_month=None, cap=None):
    """The smallest sustained monthly increase that cancels a one-time cost's
    effect on the payoff date — Pillar 2's lever, as a number.

    This is the "swing" from F.8 pointed at a decision the user is considering:
    not a judgement about whether to spend, but the one change that undoes it.
    Returns None when no amount within `cap` cancels it, rather than a figure so
    large it is really a refusal wearing a number.

    `cap` defaults to the whole current debt budget. Beyond that the "lever"
    would have someone redirect more each month than they currently put toward
    debt at all — not a lever anyone pulls, and a refusal wearing a number. The
    honest answer past the cap is None, which is what routes §6.4's honest no.

    That bound governs what may be OFFERED, not what may be stated. C.4 requires
    every honest-no to carry the nearest lever — "the smallest change that makes
    it possible is [X]" — and a figure the user did not ask to act on is a fact,
    not a recommendation. `solve_one_time_cost` therefore passes a deliberately
    wide `cap` when it is answering that question rather than proposing a path.
    """
    def delta_at(x):
        d = decision_impact(cards, budget, monthly_delta=x, one_time_cost=one_time_cost,
                            strategy=strategy, today_key=today_key, start_month=start_month)
        return d['months_delta']

    baseline = delta_at(0)
    if baseline is None or baseline <= 0:
        return 0.0 if baseline == 0 else None   # nothing to offset, or unsimulatable

    ceiling = float(cap if cap is not None else max(1.0, float(budget)))
    if delta_at(ceiling) is None or delta_at(ceiling) > 0:
        return None                              # not reachable within the cap

    # Monotonic in x — more money each month never delays the payoff — so bisect.
    lo, hi = 0.0, ceiling
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if mid <= 0:
            break
        if delta_at(mid) <= 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 0.5:
            break
    return round(hi, 2)


def minimums_only(debts):
    """Paying only the minimums - the one meaning Groundwork gives the words (V11).

    The Python twin of app.js's _minimumsOnly, line for line: each revolving
    minimum recalculated every month the way issuers do (max($25, 1% of balance +
    interest)), so it falls with the balance, and nothing freed by a paid-off debt
    is rolled into another - rolling it over is a plan, not "minimums only". This
    is deliberately NOT simulate_payoff at a budget equal to today's minimums:
    that pays fixed minimums and rolls them over, which is how the trophy proof
    once meant something different from every page.

    `debts` is a list of dicts: balance, rate (APR percent), minimum (the payment
    a fixed-payment debt keeps), debt_type. Returns None when a fixed payment
    cannot amortize - no honest baseline, claim nothing - and otherwise months,
    total_interest and `capped`: True when 360 months end with a balance left, so
    the interest is short of the truth and no saving may be claimed from it.
    """
    bals = [float(d.get('balance') or 0) for d in debts]
    m, ti = 0, 0.0
    while m < 360 and any(b > 0.01 for b in bals):
        m += 1
        for i, d in enumerate(debts):
            if bals[i] <= 0:
                continue
            ic = bals[i] * (float(d.get('rate') or 0) / 100 / 12)
            revolving = (d.get('debt_type') or 'credit') == 'credit'
            pay = max(25, bals[i] * 0.01 + ic) if revolving else float(d.get('minimum') or 0)
            if not revolving and pay <= ic:
                return None
            bals[i] += ic
            ti += ic
            bals[i] = max(0.0, bals[i] - min(pay, bals[i]))
    return {'months': m, 'total_interest': round(ti), 'capped': any(b > 0.01 for b in bals)}
