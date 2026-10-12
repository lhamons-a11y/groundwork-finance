"""A trip you commit to becomes part of the plan (TRIP_FUNDING_COACH.md, item 61, T1-T9).

Nothing here moves money or books anything (TM1); nothing decides a trip is happening (TM5): "I'm going" is the
person's tap. Every figure comes from the record and the one payoff engine, with its assumptions in words; no verdict.
"""
import json
import math
from datetime import date, timedelta

from core.consequence import Card, simulate_payoff

STATUSES = ('planning', 'going', 'done', 'cancelled')
SOURCE_KINDS = {
    'checking': 'Checking',
    'savings': 'Savings',
    'fund': 'A savings fund',
    'card': 'A credit card',
    'save_ahead': 'Saved ahead, in a trip fund',
}
REBUILD_MONTHS = (3, 6, 12)
ORDERS = ('debt_first', 'rebuild_first', 'split')
TRIP_PURPOSE = 'trip'
CARRIED_KEY = 'trips_carried_from_setting'
AFTER_DAYS = 3        # T7: charges up to this many days after the return date belong to the trip


def _d(s):
    try:
        return date.fromisoformat((s or '')[:10])
    except ValueError:
        return None


def months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month)


def sources(trip):
    try:
        out = json.loads(trip.sources_json or '[]')
    except (TypeError, ValueError):
        out = []
    return [s for s in out if isinstance(s, dict) and s.get('kind') in SOURCE_KINDS and float(s.get('amount') or 0) > 0]


def lines(trip):
    try:
        out = json.loads(trip.lines_json or '[]')
    except (TypeError, ValueError):
        out = []
    return [x for x in out if isinstance(x, dict)]


def assigned(trip):
    """T3: what the sources add up to, and what is left to assign (negative when over)."""
    total = round(sum(float(s['amount']) for s in sources(trip)), 2)
    return total, round(float(trip.total or 0) - total, 2)


def lines_from_budget(b):
    """The planner's own lines, from its saved trip budget object."""
    out = []
    for key, label, src in (('transport', 'Getting there', 'transportNote'), ('hotel', 'Lodging', 'hotelSource'),
                            ('dining', 'Food', 'diningSource'), ('activities', 'Activities', 'activitiesSource'),
                            ('other', 'Other', 'otherSource'), ('buffer', 'Buffer', None)):
        amt = b.get(key)
        try:
            amt = round(float(amt), 2)
        except (TypeError, ValueError):
            continue
        if amt > 0:
            out.append({'label': label, 'amount': amt, 'source': str(b.get(src) or '')[:160] if src else ''})
    return out


def carry_setting(session):
    """T1: the old single saved trip (the trip_budget setting) becomes the first trip, once, as 'planning'. The
    setting stays as it was."""
    from core.database import AppSetting, Trip
    if session.query(AppSetting).filter_by(key=CARRIED_KEY).first():
        return None
    made = None
    row = session.query(AppSetting).filter_by(key='trip_budget').first()
    try:
        b = json.loads(row.value) if row and row.value else None
    except (TypeError, ValueError):
        b = None
    if isinstance(b, dict) and b.get('dest') and float(b.get('total') or 0) > 0 and not session.query(Trip).first():
        made = Trip(label=str(b['dest'])[:160], depart=(b.get('depart') or '')[:10] or None,
                    ret=(b.get('ret') or '')[:10] or None, total=round(float(b['total']), 2),
                    lines_json=json.dumps(lines_from_budget(b)), status='planning')
        session.add(made)
    session.add(AppSetting(key=CARRIED_KEY, value='1'))
    session.flush()
    return made


# ── T2: the trip in its months, derived - never a budget line ───────────────

def in_month(trip, month_key):
    """True when the trip's dates touch the month 'YYYY-MM'."""
    a, b = _d(trip.depart), _d(trip.ret) or _d(trip.depart)
    if not a:
        return False
    first = date(int(month_key[:4]), int(month_key[5:7]), 1)
    last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return a <= last and b >= first


# ── T3/T4/T5/T6: the plan ───────────────────────────────────────────────────

def card_shares(trip, matched_by_card=None):
    """Each card's share of the trip, less what is already in the record through a linked booking (T5: counted once -
    projected until the real charge is linked, then the record carries it)."""
    matched_by_card = matched_by_card or {}
    out = {}
    for s in sources(trip):
        if s['kind'] == 'card' and s.get('ref_id'):
            cid = int(s['ref_id'])
            out[cid] = out.get(cid, 0.0) + float(s['amount'])
    return {cid: {'share': round(a, 2), 'linked': round(min(a, matched_by_card.get(cid, 0.0)), 2),
                  'projected': round(max(0.0, a - matched_by_card.get(cid, 0.0)), 2)} for cid, a in out.items()}


def cash_parts(trip):
    """What comes out of checking, savings and funds - what the rebuild brings back (T4). Saved-ahead money is set aside
    before the trip, so it has nothing to rebuild."""
    out = {'checking': 0.0, 'savings': 0.0, 'fund': 0.0}
    for s in sources(trip):
        if s['kind'] in out:
            out[s['kind']] += float(s['amount'])
    return {k: round(v, 2) for k, v in out.items()}


def _with_shares(cards, ids_by_name, shares):
    """The engine's cards with each card's projected trip share added to its balance."""
    out = []
    for c in cards:
        cid = ids_by_name.get(c.name)
        add = shares.get(cid, {}).get('projected', 0.0) if cid is not None else 0.0
        out.append(Card(balance=c.balance + add, rate=c.rate, minimum=c.minimum, name=c.name, is_lease=c.is_lease,
                        end_month=c.end_month, is_pslf=c.is_pslf, forgive_after_months=c.forgive_after_months))
    return out


def _months(cards, budget, strategy, start, schedule=None):
    if not cards:
        return 0
    r = simulate_payoff(cards, budget, strategy=strategy, today_key=start, start_month=start, extra_schedule=schedule)
    return r['months'] if r else None


def orders(cards_plus, budget, strategy, start, surplus, card_total, cash_total, split_pct=None):
    """T5: the debt-free month count and the rebuild month count under each order of paying the trip back from the
    monthly surplus. The surplus goes toward the debt until the trip's card amount has been paid in extra, then to
    rebuilding cash, or the other way round, or split. Each is the one engine, with a month-by-month extra."""
    out = {}
    if surplus <= 0:
        return out
    a = math.ceil(card_total / surplus) if card_total > 0 else 0
    r = math.ceil(cash_total / surplus) if cash_total > 0 else 0
    out['debt_first'] = {'debt_months': _months(cards_plus, budget, strategy, start, [surplus] * a),
                         'rebuild_months': a + r}
    out['rebuild_first'] = {'debt_months': _months(cards_plus, budget, strategy, start, [0.0] * r + [surplus] * a),
                            'rebuild_months': r}
    if split_pct is not None and 0 < split_pct < 100:
        to_debt = surplus * split_pct / 100
        to_cash = surplus - to_debt
        a2 = math.ceil(card_total / to_debt) if card_total > 0 else 0
        r2 = math.ceil(cash_total / to_cash) if cash_total > 0 else 0
        out['split'] = {'debt_months': _months(cards_plus, budget, strategy, start, [to_debt] * a2),
                        'rebuild_months': r2, 'pct': split_pct}
    return out


def month_label(start_key, n):
    if n is None:
        return None
    y, m = int(start_key[:4]), int(start_key[5:7]) + int(n)
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, 1).strftime('%B %Y')


def coach_line(goal, base_months, chosen, start_key, cash_total):
    """T6: one sentence of facts from the person's own numbers, measured on their goal. No verdict."""
    if not chosen:
        return None
    parts = []
    if goal in ('debt', 'unsure', None, '') and base_months is not None and chosen.get('debt_months') is not None:
        a, b = month_label(start_key, base_months), month_label(start_key, chosen['debt_months'])
        parts.append(f'going moves your debt-free date from {a} to {b}' if a != b
                     else f'your debt-free date stays {a}')
    if cash_total > 0 and goal in ('savings', 'goal', 'unsure', 'invest', 'debt', None, '') and chosen.get('rebuild_months'):
        parts.append(f'the money from checking and savings is back by {month_label(start_key, chosen["rebuild_months"])}')
    if not parts:
        return None
    s = ', and '.join(parts)
    return s[0].upper() + s[1:] + '.'


# ── T7: after the trip ──────────────────────────────────────────────────────

def travel_category_ids(session):
    from core.database import Category
    ids = set()
    for name in ('Travel', 'Vacation', 'Travel & Vacation'):
        c = session.query(Category).filter_by(name=name).first()
        if c:
            ids.add(c.id)
            ids.update(x.id for x in session.query(Category).filter_by(parent_id=c.id).all())
    return ids


def after_charges(session, trip, today):
    """Charges filed under Travel from the departure to a few days after the return, and the trip's linked bookings -
    listed for the person to pick from. Only on their yes do they become what the trip cost."""
    from core.database import Transaction, TripBooking
    a, b = _d(trip.depart), _d(trip.ret) or _d(trip.depart)
    if not a or not b or today < b:
        return {'ready': False, 'charges': [], 'total': 0.0}
    out, seen = [], set()
    for bk in session.query(TripBooking).filter(TripBooking.trip_label == trip.label).all():
        if bk.matched_transaction_id:
            seen.add(bk.matched_transaction_id)
        out.append({'id': f'b{bk.id}', 'date': bk.booked_on.isoformat(), 'description': f'Booking: {bk.airline}',
                    'amount': round(float(bk.charged_amount or bk.amount or 0), 2)})
    cats = travel_category_ids(session)
    if cats:
        for t in session.query(Transaction).filter(Transaction.category_id.in_(cats), Transaction.type == 'debit',
                                                   Transaction.date >= a,
                                                   Transaction.date <= b + timedelta(days=AFTER_DAYS)).all():
            if t.id in seen:
                continue
            out.append({'id': f't{t.id}', 'date': t.date.isoformat(), 'description': t.merchant or t.description or '',
                        'amount': round(abs(float(t.amount)), 2)})
    out.sort(key=lambda x: x['date'])
    return {'ready': True, 'charges': out, 'total': round(sum(x['amount'] for x in out), 2)}
