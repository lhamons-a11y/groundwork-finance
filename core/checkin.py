"""
Groundwork - the Sunday check-in's facts (gw 2.0/SUNDAY_CHECKIN.md, item 76, S1-S12)
=================================================================================
Every figure the check-in says is worked out here, from the record; the written part (when AI is on) is handed these
and teaches with them (S11) - it never adds a number.

  - S3  spending is spending: transfers between the person's own accounts (a transfer-type category, or under one)
        are left out and named. Card payments filed under a spending category (e.g. "Debt") stay spending, because
        the budget budgets them - so the week and the budget are compared like for like.
  - S4  the week behind (Sunday to Saturday) against the week before, and the month so far against the month's
        budgeted spending.
  - S5  one mechanism the week shows: the debts' interest, as a week and as a month at these balances.
  - S6  bills due in the week ahead: debt minimums by due day, recurring bills, and bill readings with a due date.
  - S7  pay expected in the week ahead, from each employer's own schedule (item 71 D3), named by whose pay it is.
  - S8  an employer whose deposit is overdue is not mentioned - no "expected", no "missing" - until deposits resume.
"""
from datetime import date, timedelta


def week_bounds(today):
    """The week behind: the last full Sunday-to-Saturday before `today`."""
    sat = today - timedelta(days=(today.weekday() + 2) % 7 or 7)
    return sat - timedelta(days=6), sat


def _transfer_ids(session):
    from core.database import Category
    cats = session.query(Category).all()
    top = {c.id for c in cats if (c.type or '') == 'transfer' or (c.name or '').strip().lower() == 'transfer'}
    return top | {c.id for c in cats if c.parent_id in top}


def _spend(session, start, end, transfers):
    from core.database import Transaction
    rows = session.query(Transaction).filter(Transaction.type == 'debit', Transaction.date >= start, Transaction.date <= end).all()
    spent = sum(t.amount or 0 for t in rows if t.category_id not in transfers)
    moved = sum(t.amount or 0 for t in rows if t.category_id in transfers)
    return round(spent, 2), round(moved, 2)


def facts(session, today=None, budget_month=None, pay=None, payer_people=None, recurring=None):
    """The check-in's facts. `budget_month` the month's budgeted spending (server budget_month_amounts total);
    `pay` the judged payers (server _pay_state()['payers']); `payer_people` {payer: person}; `recurring` the
    recurring bills list ({name, amount, dayOfMonth})."""
    from core.database import BillReading, BudgetItem, DebtAccount
    today = today or date.today()
    w0, w1 = week_bounds(today)
    p0, p1 = w0 - timedelta(days=7), w0 - timedelta(days=1)
    tr = _transfer_ids(session)
    week, moved = _spend(session, w0, w1, tr)
    prev, _ = _spend(session, p0, p1, tr)
    m0 = today.replace(day=1)
    month_spent, _ = _spend(session, m0, today, tr)
    nxt = (m0.replace(year=m0.year + 1, month=1) if m0.month == 12 else m0.replace(month=m0.month + 1))
    days_in, day_n = (nxt - m0).days, today.day
    out = {'week': {'from': w0.isoformat(), 'to': w1.isoformat(), 'spent': week, 'moved': moved,
                    'last_week': prev, 'change': round(week - prev, 2)},
           'month': {'spent': month_spent, 'budget': round(budget_month, 2) if budget_month else None,
                     'left': round(budget_month - month_spent, 2) if budget_month else None,
                     'days_left': days_in - day_n, 'day': day_n, 'days': days_in}}
    # S5: interest at today's balances
    debts = [d for d in session.query(DebtAccount).filter_by(is_active=True).all() if (d.current_balance or 0) > 0]
    daily = sum((d.current_balance or 0) * (d.interest_rate or 0) / 100 / 365 for d in debts)
    out['interest'] = {'week': round(daily * 7, 2), 'month': round(daily * 365 / 12, 2), 'debts': len(debts)}
    # S6 / S7 / S8: the week ahead (today through the next six days), from the one calendar (W3-b, core/upcoming.py),
    # so the check-in, the Upcoming card and the Calendar page cannot disagree
    from core import upcoming
    a0, a1 = today, today + timedelta(days=6)
    week_ahead = upcoming.entries(session, a0, a1, pay=pay, recurring=recurring, people=payer_people, include_detected=False)
    bills = [{'name': e['title'], 'amount': e['amount'], 'date': e['date'], 'source': e['source']}
             for e in week_ahead if e['kind'] in ('debt', 'recurring', 'bill') and (e['kind'] != 'debt' or e['amount'])]
    seen, uniq = set(), []
    for b in sorted(bills, key=lambda x: x['date']):
        k = (b['name'].lower(), b['date'])
        if k not in seen:
            seen.add(k)
            uniq.append(b)
    out['bills'] = uniq
    people = payer_people or {}
    out['pay'] = [{'payer': e['payer'], 'person': e.get('person'), 'date': e['date']} for e in week_ahead if e['kind'] == 'pay']
    out['ask_whose'] = sorted({p['payer'] for p in (pay or []) if p.get('state') not in ('missing', 'unknown')
                               and p['payer'] not in people})
    return out
