"""The visit report and the year in review (gw 2.0/VISIT_REPORT_YEAR_REVIEW.md, item 91 = item 45 H7 stage 4; Q3,
V1-V4 and Y1-Y7 ruled 2026-10-16).

Both are templated: every sentence below is fixed text with the person's figures in it. No AI, no clinical sentence,
no causal sentence, nothing about what to ask about care (V3, design §1.5). A payment establishes the payment, never
a price (V2, the H4 rule). Neither leaves the computer except by the person's own print or save (Q3). Neither is tax
advice: the year in review is a documented total, and the preparer decides (design §1.6).
"""
import json
from datetime import date

from core.hsa_fsa import money, day

NOT_A_PRICE = ('A record of payments, not a price list: what was paid before isn\'t what the next visit will cost, '
               'and it isn\'t a bill.')
NOT_IN_VISIT = ('Not in this report: who the care was for (named people come in a later stage), medications and what '
                'they cost (not yet ruled), and bills not yet paid (not yet tracked).')
NOT_ADVICE = 'Not tax advice. A documented total from your own record; your tax preparer decides what to claim.'
CANT_SEE = ('If any of these was reimbursed by insurance or a plan in a way that didn\'t come back into a health '
            'category, it doesn\'t count, and Groundwork can\'t tell.')
NO_MILEAGE = 'Mileage for medical travel isn\'t included: no trip is marked as medical yet.'
ITEMISE = ('Itemising only helps when itemised deductions are more than the standard deduction. Your preparer '
           'decides.')
FLOOR = 0.075


def _name(t):
    return ' '.join(str(t.merchant or t.description or '').split())


def providers(session):
    """V1: the health payees on the record, by their exact names - for the person to pick from, never matched loosely."""
    from core import health_boundary as hb
    from core.database import Transaction
    is_health = hb.health_rows(session)
    found = {}
    for t in session.query(Transaction).filter(Transaction.type == 'debit').all():
        if not is_health(t):
            continue
        n = _name(t)
        if not n:
            continue
        f = found.setdefault(n, {'name': n, 'payments': 0, 'last': None})
        f['payments'] += 1
        d = t.date.isoformat() if t.date else None
        if d and (f['last'] is None or d > f['last']):
            f['last'] = d
    return sorted(found.values(), key=lambda x: (x['last'] or ''), reverse=True)


def visit_report(session, names, anchor_fn, balance_fn, today=None):
    """V1-V4: what the person has paid the picked provider, the plan year's figures, the HSA / FSA and the reserve.
    `names` are exact payee names; nothing is stored (V4)."""
    from core import health_boundary as hb, health_plan, health_reserve, hsa_fsa
    from core.database import Account, Transaction
    today = today or date.today()
    known = {p['name'] for p in providers(session)}
    picked = [n for n in (names or []) if n in known]
    if not picked:
        return None, 'pick a provider from the names on your record'
    is_health = hb.health_rows(session)
    accts = {a.id: a.name for a in session.query(Account).all()}
    rows = sorted((t for t in session.query(Transaction).filter(Transaction.type == 'debit').all()
                   if is_health(t) and _name(t) in picked and t.date), key=lambda t: t.date)
    pays = [{'date': t.date.isoformat(), 'amount': round(float(t.amount or 0), 2), 'account': accts.get(t.account_id, ''),
             'line': f'{day(t.date.isoformat())}: {money(float(t.amount or 0))}'
                     + (f' from {accts[t.account_id]}' if t.account_id in accts else '') + '.'} for t in rows]
    total = round(sum(p['amount'] for p in pays), 2)
    summary = (f'{len(pays)} payment{"s" if len(pays) != 1 else ""} to {", ".join(picked)}, {money(total)} in all, '
               f'from {day(pays[0]["date"])} to {day(pays[-1]["date"])}.') if pays else 'No payments on record.'
    plan = health_plan.states(session, today).get('current')
    plan_lines = (plan['lines'] + plan['notes']) if plan else ['No health plan is entered for today.']
    accounts = [f'{r["name"]}: {r["balance"]["working"]}' for r in hsa_fsa.states(session, anchor_fn, today)]
    res = health_reserve.state(session, anchor_fn, balance_fn)
    reserve = res['lines'] if (res.get('target') is not None or res.get('reserved')) else []
    return {'provider': picked, 'as_of': today.isoformat(), 'summary': summary, 'payments': pays, 'total': total,
            'plan': plan_lines, 'accounts': accounts, 'reserve': reserve,
            'not_a_price': NOT_A_PRICE, 'not_included': NOT_IN_VISIT}, None


# ── The year in review: the Schedule A section of the year-end packet (Y1-Y7) ───────────────────────────────────

def agi(session, year):
    """Y4: the person's AGI for a year, as they typed it - the newest of its history, or None."""
    from core.database import AppSetting
    row = session.query(AppSetting).filter_by(key='agi_by_year_json').first()
    try:
        hist = (json.loads(row.value) if row and row.value else {}).get(str(year)) or []
    except (TypeError, ValueError):
        hist = []
    return hist[-1]['value'] if hist else None


def set_agi(session, year, value):
    from core.database import AppSetting
    try:
        year = int(year)
        value = None if value in (None, '') else round(float(value), 2)
    except (TypeError, ValueError):
        return 'a year and an amount, please'
    if value is not None and value < 0:
        return 'the amount must be zero or more'
    row = session.query(AppSetting).filter_by(key='agi_by_year_json').first()
    try:
        allv = json.loads(row.value) if row and row.value else {}
    except (TypeError, ValueError):
        allv = {}
    allv.setdefault(str(year), []).append({'value': value, 'said': date.today().isoformat()})
    if row:
        row.value = json.dumps(allv)
    else:
        session.add(AppSetting(key='agi_by_year_json', value=json.dumps(allv)))
    return None


def _is_premium(name):
    return 'insurance' in (name or '').lower()


def schedule_a(session, year, complete=True, today=None):
    """Y2-Y7: payments in health categories from ordinary accounts, less refunds back into them; HSA / FSA payments
    and premiums set aside with their reason; the floor only with the person's AGI; 8889 detail; what can't be seen."""
    from core import health_boundary as hb, hsa_fsa
    from core.database import Account, Category, Transaction
    today = today or date.today()
    hids = hb.health_category_ids(session)
    aids = hb.health_account_ids(session)
    cats = {c.id: c.name for c in session.query(Category).all()}
    accts = {a.id: a for a in session.query(Account).all()}
    y0, y1 = date(year, 1, 1), date(year, 12, 31)
    rows = session.query(Transaction).filter(Transaction.date >= y0, Transaction.date <= y1).order_by(Transaction.date).all()
    item = lambda t: {'date': t.date.isoformat(), 'name': _name(t), 'category': cats.get(t.category_id, ''),
                      'account': accts[t.account_id].name if t.account_id in accts else '', 'amount': round(float(t.amount or 0), 2)}
    counted, refunds, from_hsa, premiums = [], [], [], []
    for t in rows:
        in_health_acct = t.account_id in aids
        if t.type == 'debit' and in_health_acct:
            from_hsa.append(item(t))
        elif t.category_id in hids and not in_health_acct:
            if _is_premium(cats.get(t.category_id)):
                if t.type == 'debit':
                    premiums.append(item(t))
            elif t.type == 'debit':
                counted.append(item(t))
            elif t.type == 'credit':
                refunds.append(item(t))
    s = lambda xs: round(sum(x['amount'] for x in xs), 2)
    total = round(s(counted) - s(refunds), 2)
    a = agi(session, year)
    if a is None:
        floor_line = (f'Whether this clears the 7.5% floor can\'t be known without your adjusted gross income (AGI) '
                      f'for {year}.')
        floor = None
    else:
        floor = round(a * FLOOR, 2)
        floor_line = (f'On these numbers, the counted total is {money(total - floor)} above the 7.5% floor '
                      f'({money(floor)}, 7.5% of the {money(a)} AGI you entered).' if total > floor else
                      f'On these numbers, the counted total doesn\'t reach the 7.5% floor ({money(floor)}, 7.5% of the '
                      f'{money(a)} AGI you entered).')
    hsa_accts = [x for x in accts.values() if x.type == 'hsa']
    contrib, dist, seen = [], 0.0, False
    for x in hsa_accts:
        txns = session.query(Transaction).filter_by(account_id=x.id).all()
        c = hsa_fsa.contributions(txns, year, today)
        contrib.append(f'{x.name}: {c["working"]}')
        yr = [t for t in txns if t.date and t.date.year == year]
        seen = seen or bool(yr)
        dist += sum(float(t.amount or 0) for t in yr if t.type == 'debit')
    # Absence is not zero: with nothing imported into any HSA for the year, what went out of it isn't known.
    dist = round(dist, 2) if seen else None
    lines = [f'Counted: {money(s(counted))} in {len(counted)} payment{"s" if len(counted) != 1 else ""} in health '
             f'categories from your ordinary accounts'
             + (f', less {money(s(refunds))} refunded: {money(total)}.' if refunds else '.')]
    if not complete:
        lines.append('Months or accounts are missing from the record (listed above), so this total may be low.')
    lines += [floor_line, ITEMISE, CANT_SEE, NO_MILEAGE]
    return {'year': year, 'total': total, 'counted': counted, 'refunds': refunds, 'agi': a, 'floor': floor,
            'set_aside': [{'reason': 'Paid from an HSA or FSA: already tax-advantaged, so not counted.', 'rows': from_hsa,
                           'total': s(from_hsa)},
                          {'reason': 'Health insurance premiums: they count only if paid with after-tax money, which '
                                     'Groundwork can\'t see. Listed for your preparer.', 'rows': premiums, 'total': s(premiums)}],
            'hsa_8889': ({'contributions': contrib, 'distributions': dist,
                          'note': 'Your HSA custodian\'s forms (5498-SA, 1099-SA) are the authoritative figures.'}
                         if hsa_accts else None),
            'lines': lines, 'statement': NOT_ADVICE, 'complete': complete}
