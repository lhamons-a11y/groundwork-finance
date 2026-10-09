"""
Putting a trip on a card: what it would take, and what it would cost (gw 2.0/TRIP_ON_CREDIT.md, item 49; Rob
2026-10-08, R1-R7 approved as recommended).

    "We are not saying don't do this but if you do this then here is what you need to do to pay this off and how much
    it will cost over the time that it will take you to pay it off."

Every figure here backs a sentence the user reads, so it is computed here, named and tested (CALCULATION_PLACEMENT.md),
and each carries the assumption it rests on (item 39 U7):

  - the payoff rows (R2) price the trip ALONE at the card's recorded APR, paid in equal monthly payments - the
    standard amortisation. A real card applies payments by its own rules and charges interest on the whole balance;
    that is the stated assumption, not a hidden one.
  - "in full this statement" (R4) has no interest only if the card has a grace period, which the record does not hold.
  - "at your current payments" re-runs the whole payoff plan with the trip added to that card's balance.

Nothing here is a verdict. There is no row it prefers.
"""
import copy
from datetime import date

from core.consequence import simulate_payoff

PAYOFF_MONTHS = (3, 6, 12)


def _month_label(today, months_ahead):
    y, m = today.year, today.month + months_ahead
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, 1).strftime('%b %Y')


def available_credit(balance, limit):
    """Limit minus balance, or None when no limit is recorded - never a guessed limit."""
    if limit is None:
        return None
    return round(float(limit) - float(balance or 0), 2)


def payoff_rows(amount, apr, months=PAYOFF_MONTHS, today=None):
    """Equal monthly payments that clear `amount` in n months at `apr` percent a year, and the interest they cost."""
    today = today or date.today()
    amount = float(amount)
    r = float(apr or 0) / 100.0 / 12.0
    rows = []
    for n in months:
        payment = amount / n if r == 0 else amount * r / (1 - (1 + r) ** -n)
        payment = round(payment, 2)
        rows.append({
            'months': n,
            'payment': payment,
            'interest': round(max(0.0, payment * n - amount), 2),
            'paid_off': _month_label(today, n),
        })
    return rows


def at_current_payments(cards, budget, strategy, index, amount, today_key=None):
    """The whole plan with the trip added to card `index`: how much later the debt-free date comes, and the interest
    the trip adds, at what the plan pays now. None when the plan cannot be simulated."""
    kw = dict(today_key=today_key, start_month=today_key)
    base = simulate_payoff(cards, budget, strategy, **kw)
    if base is None:
        return None
    moved = copy.deepcopy(cards)
    moved[index].balance = float(moved[index].balance) + float(amount)
    after = simulate_payoff(moved, budget, strategy, **kw)
    if after is None:
        return {'payable': False}
    return {
        'payable': True,
        'months_before': base['months'],
        'months_after': after['months'],
        'months_added': after['months'] - base['months'],
        'interest_added': round(after['total_interest'] - base['total_interest'], 2),
    }


def plan(amount, card, cards, budget, strategy, index, today=None):
    """Everything sections A and B show, for one card."""
    today = today or date.today()
    amount = round(float(amount), 2)
    avail = available_credit(card['balance'], card.get('limit'))
    return {
        'amount': amount,
        'card': card,
        'fits': None if avail is None else avail >= amount,
        'available': avail,
        'short_by': None if avail is None or avail >= amount else round(amount - avail, 2),
        'statement': {'payment': amount, 'grace_period_known': False},
        'rows': payoff_rows(amount, card['apr'], today=today),
        'current': at_current_payments(cards, budget, strategy, index, amount, today.strftime('%Y-%m')),
        'assumptions': [
            f"The payoff rows price the trip alone at this card's recorded APR ({card['apr']:g}%), in equal monthly "
            "payments. Your card applies payments by its own rules and charges interest on its whole balance.",
            "No interest on a purchase paid in full by the statement due date is true only if your card has a grace "
            "period; Groundwork's record doesn't say whether it does.",
            "If the card has a 0% or promotional rate, the interest figures here are too high; they use the APR on "
            "record.",
        ],
    }
