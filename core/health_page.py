"""The Health page's spending, as recorded (gw 2.0/HEALTH_PAGE.md, item 100 HP5/HP6; Rob 2026-10-19: "open it, make it
and I'll approve it").

Health money out by month (the last twelve complete months, and this month so far) and by person, as the household said
it payment by payment (item 92: never inferred; "not said" otherwise), with the year so far. "Health" is the one test
used everywhere (health_boundary.health_rows: the category, or an HSA / FSA account).

HP6, never a lever (item 89 C1): figures only - no budget to compare with, no "over", nothing about spending less on
care. Nothing here logs, calls a model or reaches the network.
"""
from datetime import date, timedelta

from core.hsa_fsa import money

NOT_SAID = 'Not said'
WHAT_IT_IS = ('Money out for health care, as recorded: health categories, and spending from an HSA or FSA. A record, '
              'not a budget: Groundwork never suggests spending less on care.')


def summary(session, today=None):
    from core.database import CareFor, Person, Transaction
    from core.health_boundary import health_rows
    today = today or date.today()
    start = (today.replace(day=1) - timedelta(days=365)).replace(day=1)
    is_health = health_rows(session)
    rows = [t for t in session.query(Transaction).filter(Transaction.type == 'debit', Transaction.date >= start).all()
            if is_health(t)]
    months = {}
    m = start
    while m <= today:
        months[m.strftime('%Y-%m')] = 0.0
        m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
    for t in rows:
        k = t.date.strftime('%Y-%m')
        if k in months:
            months[k] += float(t.amount or 0)
    # whom it was for: the newest answer per payment (item 92 N4), never inferred
    said = {}
    for c in session.query(CareFor).filter(CareFor.transaction_id.in_([t.id for t in rows])).order_by(CareFor.id).all() \
            if rows else []:
        said[c.transaction_id] = c.person_id
    names = {p.id: p.display_name for p in session.query(Person).all()}
    year = str(today.year)
    by_person = {}
    for t in rows:
        if t.date.strftime('%Y') != year:
            continue
        pid = said.get(t.id)
        who = names.get(pid) if pid else NOT_SAID
        by_person[who] = by_person.get(who, 0.0) + float(t.amount or 0)
    this_month = today.strftime('%Y-%m')
    ytd = round(sum(v for k, v in months.items() if k.startswith(year)), 2)
    month_rows = [{'month': k, 'label': date.fromisoformat(k + '-01').strftime('%b %Y'), 'amount': round(v, 2),
                   'so_far': k == this_month} for k, v in months.items()]
    people_rows = sorted(({'who': k, 'amount': round(v, 2)} for k, v in by_person.items()),
                         key=lambda r: (r['who'] == NOT_SAID, -r['amount']))
    return {'what': WHAT_IT_IS, 'months': month_rows, 'by_person': people_rows, 'year': year, 'year_total': ytd,
            'year_line': f'{year} so far: {money(ytd)} in health spending recorded.',
            'count': len(rows)}
