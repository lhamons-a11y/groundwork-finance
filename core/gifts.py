"""Gift Budget (GIFT_BUDGET.md, item 74): people, occasions, the year's set-aside, gift funds, ledger charges.

A gift is a yearly cost paid in a few months. Everything here works from the record's own dates and amounts:
nothing watches the person, nothing decides who a purchase was for (TM5), and every figure carries its working.
"""
import json
import math
from datetime import date, timedelta

# The yearly kinds come round every year; the rest happen once, on their date.
TYPE_LABELS = {
    'birthday': 'birthday', 'anniversary': 'anniversary', 'christmas': 'Christmas',
    'mothers_day': "Mother's Day", 'fathers_day': "Father's Day", 'hanukkah': 'Hanukkah', 'easter': 'Easter',
    'graduation': 'graduation', 'wedding': 'wedding', 'other': 'occasion',
}
ANNUAL = {'birthday', 'anniversary', 'christmas', 'mothers_day', 'fathers_day', 'hanukkah', 'easter'}
RELATIONSHIPS = ('family', 'friend', 'coworker', 'other')

SET_ASIDE_NAME = 'Gifts (set aside)'
GIFT_PURPOSE = 'gift'
IMPORTED_KEY = 'gift_tables_imported'
CHARGE_CATEGORIES_KEY = 'gift_charge_category_ids'   # G4: a category the person names, besides Gifts
CHARGE_DAYS_BEFORE = 42                               # G4: "the weeks before an occasion"
CHARGE_DAYS_AFTER = 3
CHARGE_LOOKBACK = 45                                  # an occasion this recently past still offers its charges
UPCOMING_DAYS = 30                                    # G5


def cents_up(x):
    return math.ceil(round(x * 100, 6)) / 100


def _parse(date_str):
    """(year or None, month, day) from 'YYYY-MM-DD' or 'MM-DD'; None when it can't be read."""
    s = (date_str or '').strip()
    try:
        if len(s) == 10:
            return int(s[:4]), int(s[5:7]), int(s[8:10])
        if len(s) == 5:
            return None, int(s[:2]), int(s[3:5])
    except ValueError:
        return None
    return None


def _on(year, month, day):
    try:
        return date(year, month, day)
    except ValueError:                      # 29 Feb in a common year
        return date(year, month, 28)


def next_occurrence(occ_type, date_str, today):
    """The occasion's next date on or after today, or None (a one-time occasion that has passed, no date)."""
    p = _parse(date_str)
    if not p:
        return None
    y, m, d = p
    if occ_type in ANNUAL or y is None:
        nxt = _on(today.year, m, d)
        return nxt if nxt >= today else _on(today.year + 1, m, d)
    one = _on(y, m, d)
    return one if one >= today else None


def last_occurrence(occ_type, date_str, today):
    """The occasion's most recent date on or before today, or None."""
    p = _parse(date_str)
    if not p:
        return None
    y, m, d = p
    if occ_type in ANNUAL or y is None:
        this = _on(today.year, m, d)
        return this if this <= today else _on(today.year - 1, m, d)
    one = _on(y, m, d)
    return one if one <= today else None


def _short(iso):
    d = date.fromisoformat(iso)
    return f'{d.strftime("%b")} {d.day}'


def months_until(today, when):
    """Monthly set-asides before a date: one per month boundary, at least one."""
    return max(1, (when.year - today.year) * 12 + (when.month - today.month))


def occasion_label(occ, person=None):
    kind = TYPE_LABELS.get(occ.type, 'occasion')
    if occ.shared or person is None:
        return occ.name or kind[:1].upper() + kind[1:]
    if occ.type == 'other' and occ.name:
        return f"{person.name}'s {occ.name}"
    return f"{person.name}'s {kind}"


# ── G8: carrying the old settings into the tables, once ─────────────────────

def ensure_imported(session):
    """Carry gift_people_json (or the older gift_recipients_json) into the tables, once.

    The settings are left as they were, as the record of what was carried over. Each person and occasion gets a
    new whole-number id (G7: the old fractional ids are why some occasions could not be changed); the old id is
    kept as legacy_id so the Historian's earlier entries can still be joined. Returns how many occasions came over.
    """
    from core.database import AppSetting, GiftPerson, GiftOccasion
    if session.query(AppSetting).filter_by(key=IMPORTED_KEY).first():
        return 0
    moved = 0
    if not session.query(GiftPerson).first():
        rows = {r.key: r.value for r in session.query(AppSetting).filter(
            AppSetting.key.in_(['gift_people_json', 'gift_recipients_json'])).all()}
        try:
            people = json.loads(rows.get('gift_people_json') or '[]')
        except (json.JSONDecodeError, TypeError):
            people = []
        if not people:
            try:
                old = json.loads(rows.get('gift_recipients_json') or '[]')
            except (json.JSONDecodeError, TypeError):
                old = []
            people = [{'id': r.get('id'), 'name': r.get('name'), 'relationship': 'family',
                       'occasions': [{'id': None, 'type': 'birthday', 'date': r['birthday'], 'budget': 0}]
                       if r.get('birthday') else []} for r in old if isinstance(r, dict)]
        for p in people:
            if not isinstance(p, dict) or not (p.get('name') or '').strip():
                continue
            rel = p.get('relationship') if p.get('relationship') in RELATIONSHIPS else 'other'
            gp = GiftPerson(name=p['name'].strip()[:120], relationship=rel,
                            legacy_id=None if p.get('id') is None else str(p.get('id')))
            session.add(gp)
            session.flush()
            for o in p.get('occasions') or []:
                if not isinstance(o, dict):
                    continue
                spent = o.get('actual_spent')
                session.add(GiftOccasion(
                    person_id=gp.id, type=o.get('type') if o.get('type') in TYPE_LABELS else 'other',
                    date=(o.get('date') or '')[:10], budget=max(0.0, float(o.get('budget') or 0)),
                    note=o.get('note') or '', actual_spent=None if spent is None else float(spent),
                    spent_at=o.get('spent_at'), legacy_id=None if o.get('id') is None else str(o.get('id'))))
                moved += 1
    session.add(AppSetting(key=IMPORTED_KEY, value='1'))
    session.flush()
    return moved


# ── G6: a shared occasion's split ───────────────────────────────────────────

def split_shared(total, shares):
    """shares: [(person_id, fixed_amount or None)]. Fixed amounts first; the rest split evenly among the others.

    Returns {'per_person': {person_id: amount}, 'fixed': x, 'split': y, 'left_to_assign': z}. left_to_assign is
    what nobody takes yet (no one without a fixed amount), negative when the fixed amounts are over the total.
    """
    total = round(float(total or 0), 2)
    fixed = {pid: round(float(a), 2) for pid, a in shares if a is not None}
    rest_people = [pid for pid, a in shares if a is None]
    fixed_sum = round(sum(fixed.values()), 2)
    rest = round(total - fixed_sum, 2)
    per = dict(fixed)
    split = 0.0
    if rest_people and rest > 0:
        each = math.floor(rest / len(rest_people) * 100) / 100
        for pid in rest_people:
            per[pid] = each
        per[rest_people[-1]] = round(rest - each * (len(rest_people) - 1), 2)
        split = rest
    else:
        for pid in rest_people:
            per[pid] = 0.0
    left = 0.0 if (rest_people and rest > 0) else rest
    return {'per_person': per, 'fixed': fixed_sum, 'split': round(split, 2), 'left_to_assign': round(left, 2)}


# ── G1: the year's gift plan ────────────────────────────────────────────────

def gift_funds(session):
    from core.database import SinkingFund
    return session.query(SinkingFund).filter_by(is_active=True, purpose=GIFT_PURPOSE).order_by(SinkingFund.id).all()


def year_plan(session, today):
    """Every budgeted occasion in the next 12 months, the year's total, and two monthly amounts with their working.

    steady: the total ÷ 12, the yearly cost spread over the year (a $100 birthday is $100 a year).
    to_cover: what each month takes so every occasion is covered by its own date, counting what the gift funds
    hold now. It is higher than steady only in a first year, when a date comes before the months to save for it.
    Both are offered; the person picks. Neither is a verdict.
    """
    from core.database import GiftPerson, GiftOccasion
    people = {p.id: p for p in session.query(GiftPerson).all()}
    rows = []
    for o in session.query(GiftOccasion).all():
        if not (o.budget or 0) > 0:
            continue
        nxt = next_occurrence(o.type, o.date, today)
        if not nxt or nxt >= _on(today.year + 1, today.month, today.day):
            continue
        rows.append({'id': o.id, 'label': occasion_label(o, people.get(o.person_id)), 'date': nxt.isoformat(),
                     'budget': round(float(o.budget), 2)})
    rows.sort(key=lambda r: r['date'])
    total = round(sum(r['budget'] for r in rows), 2)
    held = round(sum(float(f.current_amount or 0) for f in gift_funds(session)), 2)
    steady = cents_up(total / 12) if total else 0.0
    to_cover, tightest, cum = 0.0, None, 0.0
    for r in rows:
        cum += r['budget']
        months = months_until(today, date.fromisoformat(r['date']))
        need = max(0.0, cum - held) / months
        if need > to_cover:
            to_cover, tightest = need, dict(r, months=months, to_save=round(max(0.0, cum - held), 2))
    to_cover = cents_up(to_cover)
    working = []
    if rows:
        working.append(f'{len(rows)} budgeted occasion{"s" if len(rows) != 1 else ""} in the next 12 months come to '
                       f'${total:,.2f}.')
        working.append(f'${total:,.2f} ÷ 12 = ${steady:,.2f} a month, the year\'s cost spread over the year.')
        if to_cover > steady and tightest:
            working.append(
                f'To have each one covered by its own date, counting the ${held:,.2f} the gift funds hold now: '
                f'${to_cover:,.2f} a month. The tightest is {tightest["label"]} on {_short(tightest["date"])}: '
                f'${tightest["to_save"]:,.2f} to set aside in {tightest["months"]} '
                f'month{"s" if tightest["months"] != 1 else ""}.')
    line = set_aside_line(session)
    return {'occasions': rows, 'total': total, 'held': held, 'steady': steady,
            'to_cover': to_cover if to_cover > steady else None, 'working': working,
            'line': None if line is None else {'id': line.id, 'amount': round(float(line.amount or 0), 2)}}


def set_aside_line(session):
    from core.database import BudgetItem
    return session.query(BudgetItem).filter_by(name=SET_ASIDE_NAME, is_active=True).first()


def apply_set_aside(session, monthly, today):
    """G1, on a tap: one budget line at one of the plan's own amounts. Any other amount is refused (fail closed)."""
    from core.database import BudgetItem, GiftOccasion
    plan = year_plan(session, today)
    offered = [a for a in (plan['steady'], plan['to_cover']) if a]
    try:
        monthly = round(float(monthly), 2)
    except (TypeError, ValueError):
        return None, 'Pick one of the amounts shown.'
    if not any(abs(monthly - a) < 0.005 for a in offered):
        return None, 'Pick one of the amounts shown.'
    line = set_aside_line(session)
    if line is None:
        line = BudgetItem(name=SET_ASIDE_NAME, category='Gifts', amount=monthly, type='expense')
        session.add(line)
    else:
        line.amount = monthly
    session.flush()
    return line, None


# ── G4: ledger charges before an occasion, offered ───────────────────────────

def charge_category_ids(session):
    """Gifts and its children, and any category the person named for gift charges."""
    from core.database import AppSetting, Category
    ids = set()
    gifts = session.query(Category).filter_by(name='Gifts').first()
    if gifts:
        ids.add(gifts.id)
        ids.update(c.id for c in session.query(Category).filter_by(parent_id=gifts.id).all())
    row = session.query(AppSetting).filter_by(key=CHARGE_CATEGORIES_KEY).first()
    try:
        ids.update(int(x) for x in json.loads(row.value or '[]')) if row else None
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return ids


def _used_txn_ids(session, except_occasion=None):
    from core.database import GiftOccasion
    used = set()
    for o in session.query(GiftOccasion).filter(GiftOccasion.spent_txn_ids != '').all():
        if except_occasion is not None and o.id == except_occasion:
            continue
        used.update(int(x) for x in (o.spent_txn_ids or '').split(',') if x.strip().isdigit())
    return used


def offer_date(occ, today):
    """The occasion date the charges are gathered for: one just past, else one coming up within 30 days."""
    last = last_occurrence(occ.type, occ.date, today)
    if last and (today - last).days <= CHARGE_LOOKBACK:
        return last
    nxt = next_occurrence(occ.type, occ.date, today)
    if nxt and (nxt - today).days <= UPCOMING_DAYS:
        return nxt
    return None


def charges_for(session, occ, today):
    """Charges filed under the gift categories in the weeks before the occasion, not already given to another.

    Only listed. They become the occasion's spend only on the person's yes, and the person picks which.
    """
    from core.database import Transaction
    when = offer_date(occ, today)
    if when is None:
        return {'date': None, 'charges': [], 'total': 0.0}
    cats = charge_category_ids(session)
    if not cats:
        return {'date': when.isoformat(), 'charges': [], 'total': 0.0}
    start = when - timedelta(days=CHARGE_DAYS_BEFORE)
    end = min(today, when + timedelta(days=CHARGE_DAYS_AFTER))
    used = _used_txn_ids(session, except_occasion=occ.id)
    out = []
    for t in session.query(Transaction).filter(Transaction.category_id.in_(cats), Transaction.date >= start,
                                               Transaction.date <= end, Transaction.type == 'debit'
                                               ).order_by(Transaction.date).all():
        if t.id in used:
            continue
        out.append({'id': t.id, 'date': t.date.isoformat(), 'description': t.merchant or t.description or '',
                    'amount': round(abs(float(t.amount)), 2)})
    return {'date': when.isoformat(), 'charges': out, 'total': round(sum(c['amount'] for c in out), 2)}


def use_charges(session, occ, txn_ids, today):
    """On the person's yes: the picked charges become what the occasion cost. Every id must be one offered."""
    offered = {c['id']: c for c in charges_for(session, occ, today)['charges']}
    try:
        picked = sorted({int(x) for x in txn_ids})
    except (TypeError, ValueError):
        return None, 'Pick charges from the list.'
    if not picked or any(i not in offered for i in picked):
        return None, 'Pick charges from the list.'
    spent = round(sum(offered[i]['amount'] for i in picked), 2)
    occ.actual_spent = spent
    occ.spent_at = today.isoformat()
    occ.spent_txn_ids = ','.join(str(i) for i in picked)
    return spent, None


# ── G3: "Mark spent" keeps the record ───────────────────────────────────────

def last_spend(session, fund_id):
    from core.database import FundSpend
    s = session.query(FundSpend).filter_by(fund_id=fund_id).order_by(FundSpend.spent_on.desc(),
                                                                     FundSpend.id.desc()).first()
    if not s:
        return None
    return {'target': round(float(s.target or 0), 2), 'spent': round(float(s.spent), 2),
            'spent_on': s.spent_on.isoformat(),
            'text': f'Last time: target ${float(s.target or 0):,.2f}, spent ${float(s.spent):,.2f} '
                    f'({s.spent_on.strftime("%b %Y")})'}


def mark_fund_spent(session, fund, spent, today):
    from core.database import FundSpend
    row = FundSpend(fund_id=fund.id, target=float(fund.target_amount or 0), spent=round(float(spent), 2),
                    spent_on=today)
    session.add(row)
    fund.current_amount = 0
    fund.last_contributed_month = ''
    session.flush()
    return row


# ── G2: the old seasonal funds become gift funds, on a tap ──────────────────

def seasons_to_move(session):
    from core.database import AppSetting
    row = session.query(AppSetting).filter_by(key='gift_seasons_json').first()
    try:
        seasons = json.loads(row.value) if row and row.value else []
    except (json.JSONDecodeError, TypeError):
        seasons = []
    return [s for s in seasons if isinstance(s, dict) and not s.get('moved_to_fund_id')]


def move_seasons(session):
    """Each seasonal fund becomes a gift fund with its name, target, date and what it held. The setting keeps
    every season, each marked with the fund it became, so nothing is lost and none moves twice."""
    from core.database import AppSetting, SinkingFund
    row = session.query(AppSetting).filter_by(key='gift_seasons_json').first()
    try:
        seasons = json.loads(row.value) if row and row.value else []
    except (json.JSONDecodeError, TypeError):
        return []
    moved = []
    for s in seasons:
        if not isinstance(s, dict) or s.get('moved_to_fund_id'):
            continue
        f = SinkingFund(name=(s.get('name') or 'Gift fund')[:120], target_amount=float(s.get('target') or 0),
                        current_amount=float(s.get('saved') or 0), deadline=(s.get('deadline') or None),
                        monthly_contribution=0.0, note="Moved from the Gift page's seasonal funds",
                        purpose=GIFT_PURPOSE)
        session.add(f)
        session.flush()
        s['moved_to_fund_id'] = f.id
        moved.append({'season_id': s.get('id'), 'fund_id': f.id, 'name': f.name})
    if moved:
        row.value = json.dumps(seasons)
    return moved


# ── G5: occasions in what Groundwork already shows ahead ────────────────────

def upcoming(session, today, days=UPCOMING_DAYS):
    """Budgeted occasions within `days`, each as one sentence of facts from the record's own dates."""
    from core.database import GiftPerson, GiftOccasion
    people = {p.id: p for p in session.query(GiftPerson).all()}
    funds = gift_funds(session)
    held = round(sum(float(f.current_amount or 0) for f in funds), 2)
    out = []
    for o in session.query(GiftOccasion).all():
        if not (o.budget or 0) > 0:
            continue
        nxt = next_occurrence(o.type, o.date, today)
        if not nxt or (nxt - today).days > days:
            continue
        label = occasion_label(o, people.get(o.person_id))
        text = f'{label}, {nxt.strftime("%b")} {nxt.day}: ${float(o.budget):,.2f} budgeted'
        if funds:
            text += f'; the gift fund{"s hold" if len(funds) > 1 else " holds"} ${held:,.2f}'
        out.append({'id': o.id, 'label': label, 'date': nxt.isoformat(), 'days': (nxt - today).days,
                    'budget': round(float(o.budget), 2), 'text': text + '.'})
    out.sort(key=lambda r: r['date'])
    return out
