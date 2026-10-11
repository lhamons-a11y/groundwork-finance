"""
Groundwork - Before You Buy, from the record (gw 2.0/BYB_AGENT.md, item 73 stage 1: Y1 + Y6)
============================================================================================
Most purchases never pass through Before You Buy. Y1 brings two kinds to it from the ledger, after the fact:

  - a NEW repeating charge: the same merchant at a steady amount, three or more times, that started recently and is
    not already a budget line;
  - a charge that moved the payoff date by a month or more (the existing large-charge rule, server side).

Y6: what each one does to the person's savings goals, with the assumption said out loud.

Arithmetic over what it is handed - no database, no model. Nothing about why the purchase was made is inferred (TM5),
and an offer is made once per charge; the person's answer (or dismissal) ends it.
"""
import math
import statistics
from datetime import date, timedelta

NEW_DAYS = 100            # a repeating charge counts as new when its first charge on record is this recent
MIN_CHARGES = 3
STEADY = 0.05             # every charge within 5% of their average: the same subscription, not shopping
MONTHLY_GAP = (26, 35)
WEEKLY_GAP = (6, 8)


def _norm(s):
    return ' '.join(str(s or '').lower().split())


def new_recurring(rows, budgeted, today, window_start):
    """`rows` [(id, date, amount, merchant)] - debits since `window_start` (long enough that 'new' means new).
    `budgeted` - the active budget line names. -> [{key, kind, name, amount, monthly, every, since, ids}]"""
    by = {}
    for tid, d, amt, merchant in rows:
        if merchant and amt and amt > 0:
            by.setdefault(merchant, []).append((d, float(amt), tid))
    budget_names = {_norm(b) for b in budgeted}
    out = []
    for merchant, charges in by.items():
        charges.sort()
        if len(charges) < MIN_CHARGES or _norm(merchant) in budget_names:
            continue
        first = charges[0][0]
        if first < today - timedelta(days=NEW_DAYS) or first <= window_start:
            continue                                  # not new: it was there before the recent stretch
        amounts = [a for _, a, _ in charges]
        avg = sum(amounts) / len(amounts)
        if max(abs(a - avg) for a in amounts) > avg * STEADY:
            continue
        gaps = [(b[0] - a[0]).days for a, b in zip(charges, charges[1:])]
        g = statistics.median(gaps)
        if MONTHLY_GAP[0] <= g <= MONTHLY_GAP[1]:
            every, per_month = 'month', 1.0
        elif WEEKLY_GAP[0] <= g <= WEEKLY_GAP[1]:
            every, per_month = 'week', 52 / 12
        else:
            continue
        out.append({'key': f'recurring:{_norm(merchant)}', 'kind': 'new_recurring', 'name': merchant,
                    'amount': round(charges[-1][1], 2), 'monthly': round(avg * per_month, 2), 'every': every,
                    'since': first.isoformat(), 'count': len(charges), 'ids': [t for _, _, t in charges]})
    out.sort(key=lambda o: -o['monthly'])
    return out


def _add_months(d, n):
    y, m = d.year + (d.month - 1 + n) // 12, (d.month - 1 + n) % 12 + 1
    return date(y, m, 1)


def goal_dates(goals, today, monthly=0.0, one_time=0.0):
    """Y6: each goal's date at its own contribution, and with the purchase coming out of that contribution.
    `goals` [{id, name, target, saved, contribution}]. The assumption is part of the answer, not a footnote."""
    out = []
    for gl in goals:
        left = max(0.0, float(gl['target']) - float(gl['saved']))
        c = float(gl['contribution'] or 0)
        if left <= 0 or c <= 0:
            continue
        now = math.ceil(left / c)
        after_c = c - monthly
        if after_c <= 0:
            later = None
        else:
            later = math.ceil((left + one_time) / after_c)
        out.append({'id': gl['id'], 'name': gl['name'], 'contribution': round(c, 2),
                    'date_now': _add_months(today, now).isoformat()[:7],
                    'date_with': _add_months(today, later).isoformat()[:7] if later is not None else None,
                    'months_later': (later - now) if later is not None else None})
    return out


def assumption(monthly, one_time):
    if monthly:
        return (f'If the ${monthly:,.2f} a month came out of what goes to each goal (or to the debt for the payoff '
                f'date) - one way to see its size, not a prediction of where the money comes from.')
    return (f'If the ${one_time:,.2f} had come out of what goes to each goal (or to the debt for the payoff date) - '
            f'one way to see its size, not a statement of where the money came from.')
