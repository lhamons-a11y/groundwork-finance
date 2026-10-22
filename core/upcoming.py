"""The one calendar of what's coming (gw 2.0/AGENT_W_ITEMS.md W3, item 65; ruled 2026-10-12).

Every upcoming date Groundwork knows, from the record, each with its certainty (W3-a):
    confirmed - a date the person entered or a biller stated: a debt's due day, the person's own recurring bills,
                a bill read and confirmed, a gift occasion, a trip they are going on, a fund's date
    expected  - worked out from the record: pay from each employer's schedule, a recurring charge's usual day
    possible  - a yearly bill the person said yes to (W1), in its usual month
Nothing is inferred from purchases (TM5). The calendar page, the dashboard's Upcoming card and the Sunday check-in all
read from here, so they cannot disagree (W3-b). Nothing pushes or reminds (W3-c, TM6).
"""
from datetime import date, timedelta
from statistics import median

CONFIRMED, EXPECTED, POSSIBLE = 'confirmed', 'expected', 'possible'


def _month_day(year, month, day):
    last = ((date(year + (month == 12), month % 12 + 1, 1)) - timedelta(days=1)).day
    return date(year, month, min(int(day), last))


def monthly_dates(day, start, end):
    """Every date in [start, end] on day-of-month `day` (clamped to the month's last day)."""
    out = []
    try:
        day = int(day)
    except (TypeError, ValueError):
        return out
    if not 1 <= day <= 31:
        return out
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        d = _month_day(y, m, day)
        if start <= d <= end:
            out.append(d)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def entries(session, start, end, pay=None, recurring=None, people=None, include_detected=True):
    """Every upcoming entry in [start, end], sorted by date. Each: {date, kind, title, amount, certainty, source, ...}.
    `pay` the judged payers (server _pay_state()['payers']); `recurring` the person's own recurring bills
    ({name, amount, dayOfMonth}); `people` {payer: person}."""
    from core.database import AppSetting, BillReading, BudgetItem, DebtAccount, SinkingFund
    out = []
    # confirmed: each debt's due day, as entered
    for d in session.query(DebtAccount).filter_by(is_active=True).all():
        if not d.due_day or (d.current_balance or 0) <= 0:
            continue
        for when in monthly_dates(d.due_day, start, end):
            out.append({'date': when, 'kind': 'debt', 'title': d.name, 'amount': round(d.minimum_payment or 0, 2) or None,
                        'certainty': CONFIRMED, 'source': 'its minimum and due day', 'debt_id': d.id, 'view': 'debt'})
    # confirmed: the person's own recurring bills
    for r in recurring or []:
        if not isinstance(r, dict):
            continue
        for when in monthly_dates(r.get('dayOfMonth') or 1, start, end):
            out.append({'date': when, 'kind': 'recurring', 'title': r.get('name') or r.get('description') or 'A recurring bill',
                        'amount': round(float(r.get('amount') or 0), 2) or None, 'certainty': CONFIRMED,
                        'source': 'your recurring bills', 'view': 'budget'})
    # confirmed: bills read from their own page and confirmed (item 68)
    for b in session.query(BillReading).filter(BillReading.due_date >= start, BillReading.due_date <= end).all():
        item = session.get(BudgetItem, b.budget_item_id)
        out.append({'date': b.due_date, 'kind': 'bill', 'title': item.name if item else 'A bill',
                    'amount': round(b.amount, 2) if b.amount is not None else None, 'certainty': CONFIRMED,
                    'source': "read from the bill's own page", 'view': 'budget'})
    # confirmed: gift occasions (item 74), every one with a date
    try:
        from core import gifts as gf
        from core.database import GiftOccasion, GiftPerson
        ppl = {p.id: p for p in session.query(GiftPerson).all()}
        for o in session.query(GiftOccasion).all():
            nxt = gf.next_occurrence(o.type, o.date, start)
            while nxt and nxt <= end:
                out.append({'date': nxt, 'kind': 'gift', 'title': gf.occasion_label(o, ppl.get(o.person_id)),
                            'amount': round(float(o.budget), 2) if (o.budget or 0) > 0 else None, 'certainty': CONFIRMED,
                            'source': 'your gift list', 'view': 'gifts'})
                if o.type not in gf.ANNUAL and len(o.date or '') == 10:
                    break
                nxt = gf.next_occurrence(o.type, o.date, nxt + timedelta(days=1))
    except Exception:
        pass
    # confirmed: trips the person is going on (item 61)
    try:
        from core.database import Trip
        for t in session.query(Trip).filter_by(status='going').all():
            try:
                dep = date.fromisoformat(t.depart)
            except (TypeError, ValueError):
                continue
            if start <= dep <= end:
                out.append({'date': dep, 'kind': 'trip', 'title': f'Trip to {t.label}', 'amount': round(t.total or 0, 2) or None,
                            'certainty': CONFIRMED, 'source': "a trip you're going on", 'end': t.ret, 'view': 'trip'})
    except Exception:
        pass
    # confirmed: savings funds' dates
    for f in session.query(SinkingFund).filter_by(is_active=True).all():
        try:
            when = date.fromisoformat(f.deadline) if f.deadline else None
        except ValueError:
            when = None
        if when and start <= when <= end:
            out.append({'date': when, 'kind': 'fund', 'title': f.name, 'amount': round(f.target_amount or 0, 2) or None,
                        'certainty': CONFIRMED, 'source': "the fund's date", 'view': 'budget'})
    # expected: pay, from each employer's own schedule - never a payer that is overdue (item 76 S7/S8)
    for p in pay or []:
        if p.get('state') in ('missing', 'unknown', 'not_on_record_yet') or not p.get('every') or not p.get('last'):
            continue
        n = date.fromisoformat(p['last'])
        while n < start:
            n += timedelta(days=p['every'])
        while n <= end:
            out.append({'date': n, 'kind': 'pay', 'title': p['payer'], 'person': (people or {}).get(p['payer']),
                        'amount': None, 'certainty': EXPECTED, 'source': f"every {p['every']} days, from its last check",
                        'payer': p['payer'], 'view': 'budget'})
            n += timedelta(days=p['every'])
    # expected: recurring charges found in the ledger (not already budgeted), on their usual day
    if include_detected:
        out.extend(_detected(session, start, end))
    # possible: yearly bills the person said yes to (W1), in their usual month
    row = session.query(AppSetting).filter_by(key='yearly_bills_json').first()
    if row and row.value:
        import json
        try:
            yearly = json.loads(row.value)
        except ValueError:
            yearly = []
        for y in yearly if isinstance(yearly, list) else []:
            if not isinstance(y, dict) or y.get('answer') != 'yes':
                continue
            for when in _yearly_dates(y, start, end):
                out.append({'date': when, 'kind': 'yearly', 'title': y.get('payee') or 'A yearly bill',
                            'amount': y.get('amount'), 'certainty': POSSIBLE,
                            'source': 'a yearly bill you confirmed, in its usual month', 'view': 'budget'})
    out.sort(key=lambda e: (e['date'], e['kind'], e['title']))
    for e in out:
        e['date'] = e['date'].isoformat()
    return out


def _yearly_dates(y, start, end):
    out = []
    for mo in y.get('months') or []:
        for yr in (start.year, start.year + 1):
            try:
                d = _month_day(yr, int(mo), int(y.get('day') or 15))
            except (TypeError, ValueError):
                continue
            if start <= d <= end:
                out.append(d)
    return out


def recurring_charges(session, start, include_budgeted=False):
    """The one rule for "a recurring charge" (item 79 U6, ruled 2026-10-13: the Budget page and the Calendar never
    disagree about what recurs), one payee from one account (item 108): 3+ charges in the 6 months before `start`,
    each within 5% of their average, in 3+ different months, about a month apart.
    [{merchant, label, account, amount, day, months, budgeted}], biggest first."""
    from core.database import Account, BudgetItem, Category, Transaction
    from core.price_change import NOT_PRICES       # interest, fees, debt, transfers, savings: not a recurring bill
    from core import recurring_groups as rg
    cutoff = start - timedelta(days=183)
    rows = session.query(Transaction.merchant, Transaction.account_id, Transaction.date, Transaction.amount,
                         Category.name).outerjoin(Category, Category.id == Transaction.category_id).filter(
        Transaction.type == 'debit', Transaction.date >= cutoff, Transaction.date < start, Transaction.merchant != '').all()
    # a debt's payment is on the calendar already, from its own due day; interest follows a balance
    rows = [r for r in rows if r[0] and r[2] and (r[4] or '').strip().lower() not in NOT_PRICES]
    names = {a.id: a.name for a in session.query(Account).all()}
    budgeted = {(b.name or '').strip().lower() for b in session.query(BudgetItem).filter_by(is_active=True).all()}
    out = []
    # item 108 R1/R3/R4: one payee from one account; `merchant` stays the payee (R5), `label` names the account when
    # the payee recurs from more than one
    for grp in rg.groups(rows, names):
        m, xs = grp['payee'], [(abs(float(a or 0)), d) for d, a, _ in grp['rows']]
        is_budgeted = m.strip().lower() in budgeted
        if len(xs) < 3 or (is_budgeted and not include_budgeted):
            continue
        amts = [a for a, _ in xs]
        avg = sum(amts) / len(amts)
        if avg <= 0 or any(abs(a - avg) / avg > 0.05 for a in amts):
            continue
        ds = sorted(d for _, d in xs)
        gaps = [(b - a).days for a, b in zip(ds, ds[1:])]
        months = len({(d.year, d.month) for d in ds})
        if months < 3 or not 25 <= median(gaps) <= 35:
            continue                                    # monthly means about a month apart: a weekly coffee is not a bill
        out.append({'merchant': m, 'label': grp['label'], 'account': grp['account'], 'amount': round(avg, 2),
                    'day': int(median(d.day for _, d in xs)), 'months': months, 'budgeted': is_budgeted})
    return sorted(out, key=lambda r: -r['amount'])


def _detected(session, start, end):
    """Recurring charges the ledger shows and no budget line names (`recurring_charges`, the one rule), on their usual
    day of the month - expected, and said to be worked out."""
    out = []
    for r in recurring_charges(session, start):
        for when in monthly_dates(r['day'], start, end):
            out.append({'date': when, 'kind': 'charge', 'title': r['label'], 'amount': r['amount'], 'certainty': EXPECTED,
                        'source': f"about the {_ordinal(r['day'])}, from the last 6 months", 'view': 'ledger'})
    return out


def _ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
