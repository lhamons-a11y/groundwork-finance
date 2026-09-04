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

from dataclasses import dataclass

MAX_MONTHS = 360          # matches the JS loop cap
SETTLED = 0.01            # a balance at or under this is cleared, as in the JS


@dataclass
class Card:
    balance: float
    rate: float           # APR percent, e.g. 22.0
    minimum: float
    name: str = 'Card'
    is_lease: bool = False
    end_month: str = None  # 'YYYY-MM'; a lease past this is written off


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
        ))
    return [c for c in out if c.balance > 0]


def simulate_payoff(cards, budget, strategy='avalanche', one_time_cost=0.0,
                    today_key=None, start_month=None):
    """Months until every balance clears, or None if the budget cannot cover
    the minimums — the JS returns null there and so do we, rather than a
    fabricated large number.

    one_time_cost is money that will NOT reach the debt: it consumes the extra
    above minimums until absorbed. That models paying cash from the same
    surplus the extra came from, which is the optimistic reading — financing it
    costs more. The assumption is stated because being optimistic here is the
    direction that flatters a spending decision.
    """
    data = _prepare(cards)
    if today_key is not None:
        data = [c for c in data if not (c.is_lease and c.end_month and c.end_month < today_key)]
    if not data:
        return None

    total_min = sum(c.minimum for c in data)
    if budget < total_min:
        return None

    order = sorted(
        [c for c in data if not c.is_lease],
        key=(lambda c: c.balance) if strategy == 'snowball' else (lambda c: -c.rate))

    bals = [c.balance for c in data]
    remaining_cost = float(one_time_cost or 0)
    month, total_interest = 0, 0.0
    first_cleared_month, first_cleared_name = None, None

    while month < MAX_MONTHS and any(b > SETTLED for b in bals):
        month += 1
        sim_key = _month_key(start_month, month)
        extra = float(budget)

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

        if first_cleared_month is None:
            for i, c in enumerate(data):
                if bals[i] <= SETTLED:
                    first_cleared_month, first_cleared_name = month, c.name
                    break

    return {
        'months': month,
        'total_interest': round(total_interest),
        'first_cleared_month': first_cleared_month,
        'first_cleared_name': first_cleared_name,
    }


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
