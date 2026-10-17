"""The health reserve (gw 2.0/HEALTH_RESERVE.md, item 88 = item 45 H7 stage 3; R1-R9 ruled 2026-10-16).

Money set aside so a medical bill can be paid without a card (R9). Built on core/reserve.py's rules over its tables:
    the target is the current plan's out-of-pocket maximum, read and never copied (R2), or the person's own figure;
        never an invented one ("three to six months" is not said)
    the reserve is a LEVEL of a balance - $500 then $700 is $700 - and never a movement (R3, Rob's frozen rule of
        2026-09-07). The allocation rows keep no account reference, as reserve.py's table was written; which account
        holds the reserve is recorded beside them, with its date (`reserve_account_json`)
    an HSA balance counts toward the target on its own line; FSA money does not, because it can expire (R4)

R1: when the reserve fills - after the last debt (how the engine works today), before it, or alongside it - is the
person's choice. Each option is run through the same engine (core/consequence.simulate_payoff, with an
`extra_schedule`, R5) and shown with its debt-free month, its interest and the month the reserve would be full. None
is labelled best. Minimum payments are never touched: the engine pays them first, and a schedule only takes from the
extra above them. Using the reserve is the person's act (R6). No advice, no "should" (R9).
"""
import json
import math
from datetime import date

from core.hsa_fsa import money

CHOICES = ('after', 'before', 'alongside')
PURPOSE = 'Money set aside so a medical bill can be paid without a card.'


def _setting(session, key, default):
    from core.database import AppSetting
    row = session.query(AppSetting).filter_by(key=key).first()
    try:
        return json.loads(row.value) if row and row.value else default
    except (TypeError, ValueError):
        return default


def _append(session, key, entry):
    """A dated history in one setting: the newest entry is current, the earlier ones are kept."""
    from core.database import AppSetting
    hist = _setting(session, key, [])
    hist.append(dict(entry, said=date.today().isoformat()))
    row = session.query(AppSetting).filter_by(key=key).first()
    if row:
        row.value = json.dumps(hist)
    else:
        session.add(AppSetting(key=key, value=json.dumps(hist)))
    return hist[-1]


def _seq(session):
    from sqlalchemy import func
    from core.database import ReserveAllocation, ReserveTarget
    return 1 + max(session.query(func.max(m.seq)).scalar() or 0 for m in (ReserveTarget, ReserveAllocation))


def month_label(offset, today=None):
    t = today or date.today()
    m = t.month - 1 + int(offset)
    return date(t.year + m // 12, m % 12 + 1, 1).strftime('%b %Y')


# ── Writes: each one supersedes, none moves money ──────────────────────────────────────────────────────────────

def set_target(session, body):
    """R2: {basis: 'oop_max' | 'custom' | '' (none), amount (custom only)}."""
    from core.database import ReserveTarget
    basis = str(body.get('basis') or '').strip()
    if basis not in ('oop_max', 'custom', ''):
        return None, 'basis must be oop_max, custom or blank'
    amount = None
    if basis == 'custom':
        try:
            amount = round(float(body.get('amount')), 2)
        except (TypeError, ValueError):
            return None, 'a target of your own needs an amount'
        if amount <= 0:
            return None, 'the target must be more than zero'
    row = ReserveTarget(basis=basis or None, amount=amount, kind='preference', source='typed', cleared=(basis == ''),
                        seq=_seq(session))
    session.add(row)
    session.flush()
    return row, None


def set_reserved(session, body):
    """R3: {amount, account_id}. A level, not a contribution; the account's balance is never changed."""
    from core.database import Account, ReserveAllocation
    try:
        amount = round(float(body.get('amount')), 2)
    except (TypeError, ValueError):
        return None, 'an amount, please'
    if amount < 0:
        return None, 'the amount must be zero or more'
    acct_id = body.get('account_id')
    if acct_id not in (None, ''):
        acct = session.get(Account, int(acct_id))
        if not acct:
            return None, 'That account was not found.'
        cur = (_setting(session, 'reserve_account_json', []) or [{}])[-1].get('account_id')
        if cur != acct.id:
            _append(session, 'reserve_account_json', {'account_id': acct.id})
    elif not _setting(session, 'reserve_account_json', []):
        return None, 'say which account holds the reserve'
    row = ReserveAllocation(amount=amount, as_of=date.today().isoformat(), reason=str(body.get('reason') or '')[:200] or None,
                            source='typed', seq=_seq(session))
    session.add(row)
    session.flush()
    return row, None


def set_choice(session, body):
    """R1: {choice: after | before | alongside, monthly (alongside)}. Kept with its date; changeable any time."""
    choice = str(body.get('choice') or '').strip()
    if choice not in CHOICES:
        return None, 'choose after, before or alongside'
    monthly = None
    if choice == 'alongside':
        try:
            monthly = round(float(body.get('monthly')), 2)
        except (TypeError, ValueError):
            return None, 'alongside needs a monthly amount'
        if monthly <= 0:
            return None, 'the monthly amount must be more than zero'
    return _append(session, 'reserve_order_json', {'choice': choice, 'monthly': monthly}), None


# ── Reads ───────────────────────────────────────────────────────────────────────────────────────────────────────

def _target(session):
    from core.database import ReserveTarget
    from core import health_plan
    row = session.query(ReserveTarget).order_by(ReserveTarget.seq.desc()).first()
    if row is not None and (row.cleared or not row.basis):
        return None, 'none', 'No target set. It can be your plan\'s out-of-pocket maximum or a figure of your own.'
    if row is not None and row.basis == 'custom':
        return row.amount, 'custom', f'{money(row.amount)}, a target you set.'
    # R2: with no target chosen, a current plan's maximum is the target; with neither, there is none.
    cur = health_plan.states(session).get('current')
    if not cur or cur.get('oop_max') is None:
        if row is None:
            return None, 'none', ('No target yet. Enter your health plan\'s out-of-pocket maximum (Settings, Accounts, '
                                  'Health plan), or set a figure of your own.')
        return None, 'oop_max', ('The target is your plan\'s out-of-pocket maximum, but no current plan has one '
                                 'entered (Settings, Accounts, Health plan).')
    return cur['oop_max'], 'oop_max', (f'{money(cur["oop_max"])}, the out-of-pocket maximum of {cur["name"]} - the most '
                                       'a covered year can cost. Read from the plan, so a corrected maximum moves it.')


def _hsa(session, anchor_fn):
    from core import hsa_fsa
    rows = [r for r in hsa_fsa.states(session, anchor_fn) if r['kind'] == 'hsa' and r['balance']['amount'] is not None]
    return round(sum(r['balance']['amount'] for r in rows), 2), [r['name'] for r in rows]


def _last_health_payment_from(session, account_id, since):
    """R6: the newest health payment from the reserve's account that arrived after the reserve was last set (by when
    it came into the record, so a same-day payment counts)."""
    from core import health_boundary as hb
    from core.database import Transaction
    is_health = hb.health_rows(session)
    q = session.query(Transaction).filter(Transaction.account_id == account_id, Transaction.type == 'debit')
    if since:
        q = q.filter(Transaction.created_at > since)
    rows = [t for t in q.order_by(Transaction.date.desc()).all() if is_health(t)]
    return rows[0] if rows else None


def state(session, anchor_fn, balance_fn):
    """The card's figures, each with its working. `balance_fn(session, account_id)` -> (balance or None, as_of)."""
    from core.database import Account, ReserveAllocation
    target, basis, target_line = _target(session)
    hsa, hsa_names = _hsa(session, anchor_fn)
    alloc = session.query(ReserveAllocation).order_by(ReserveAllocation.seq.desc()).first()
    reserved = alloc.amount if alloc else 0.0
    acct_id = (_setting(session, 'reserve_account_json', []) or [{}])[-1].get('account_id')
    acct = session.get(Account, acct_id) if acct_id else None
    lines, notes, offer = [f'Target: {target_line}'], [], None
    if hsa_names:
        lines.append(f'HSA: {money(hsa)} ({", ".join(hsa_names)}), counted toward it. It stays in the HSA.')
    if acct:
        bal, as_of = balance_fn(session, acct.id)
        lines.append(f'Reserved in {acct.name}: {money(reserved)}.')
        if bal is None:
            notes.append(f'The balance of {acct.name} isn\'t known, so what is available beside the reserve isn\'t either.')
        else:
            avail = round(bal - reserved, 2)
            when = f' as of {as_of}' if as_of else ''
            lines.append(f'Available in {acct.name}: {money(avail)} ({money(bal)} balance{when}, less the reserve).')
            if avail < 0:
                notes.append(f'The balance of {acct.name} is {money(bal)}, below the {money(reserved)} reserved. Groundwork '
                             'doesn\'t lower the reserve by itself.')
        t = _last_health_payment_from(session, acct.id, alloc.recorded_at if alloc else None)
        if t and reserved > 0:
            offer = {'amount': round(min(reserved, float(t.amount or 0)), 2), 'on': t.date.isoformat(),
                     'sentence': f'A health payment of {money(float(t.amount or 0))} on {t.date.strftime("%b %d, %Y")} came '
                                 f'from {acct.name}. Lower the reserve by {money(min(reserved, float(t.amount or 0)))}?'}
    else:
        lines.append('Reserved: nothing yet. Name the account that holds it and how much of its balance is the reserve.')
    covered = round(hsa + (reserved if acct else 0.0), 2)
    gap = None if target is None else round(max(0.0, target - covered), 2)
    if target is not None:
        lines.append(f'Covered: {money(covered)} of {money(target)}' + (', full.' if gap == 0 else f', {money(gap)} to go.'))
    return {'purpose': PURPOSE, 'target': target, 'basis': basis, 'hsa': hsa, 'reserved': reserved,
            'account_id': acct.id if acct else None, 'account': acct.name if acct else None, 'covered': covered,
            'gap': gap, 'lines': lines, 'notes': notes, 'offer': offer,
            'choice': (_setting(session, 'reserve_order_json', []) or [None])[-1],
            'history': {'account': _setting(session, 'reserve_account_json', []),
                        'choice': _setting(session, 'reserve_order_json', [])}}


def _gap_now(session, anchor_fn):
    target, _basis, _line = _target(session)
    if target is None:
        return None
    from core.database import ReserveAllocation
    hsa, _names = _hsa(session, anchor_fn)
    alloc = session.query(ReserveAllocation).order_by(ReserveAllocation.seq.desc()).first()
    has_acct = bool((_setting(session, 'reserve_account_json', []) or [{}])[-1].get('account_id'))
    reserved = alloc.amount if (alloc and has_acct) else 0.0
    return round(max(0.0, target - hsa - reserved), 2)


def request_plan(session, anchor_fn):
    """Item 90 D2: what the engine needs for this request - the choice and the gap still to fill - or None when
    nothing should change (no choice, "after", no target, a full reserve). Worked out fresh; nothing stored."""
    ch = (_setting(session, 'reserve_order_json', []) or [None])[-1] or {}
    if ch.get('choice') not in ('before', 'alongside'):
        return None
    gap = _gap_now(session, anchor_fn)
    if not gap:
        return None
    return {'choice': ch['choice'], 'monthly': ch.get('monthly'), 'gap': gap}


def applied(plan, cards, budget, today=None):
    """Item 90 D4: the line a reserve-aware date carries - how much, until when - for these cards and budget."""
    from core.consequence import extra_above_minimums, no_reserve, reserve_schedule, RESERVE_PLAN
    if not plan or not cards:
        return None
    extra = extra_above_minimums(cards, budget)
    if not extra:
        return None
    tok = RESERVE_PLAN.set(plan)
    try:
        sched = reserve_schedule(extra)
    finally:
        RESERVE_PLAN.reset(tok)
    if not sched:
        return None
    x, n = -sched[0], len(sched)
    return {'monthly': round(x, 2), 'months': n, 'until': month_label(n, today), 'choice': plan['choice'],
            'line': f'Includes your health reserve: {money(x)} a month until {month_label(n, today)}.',
            'input': f'Health reserve: {money(x)} a month for {n} month{"s" if n != 1 else ""} (your choice).'}


def input_line(cards, budget):
    """Item 90 D4: the input line a surface that lists its inputs adds while the reserve shapes its dates."""
    from core.consequence import RESERVE_PLAN
    plan = RESERVE_PLAN.get()
    if callable(plan):
        plan = plan()
    a = applied(plan, cards, budget)
    return {'label': a['input'], 'value': a['monthly'], 'kind': 'user_supplied'} if a else None


def options(cards, budget, strategy, gap, monthly=None, today=None):
    """Item 90 D5: asked of the engine without the household's choice, so the three stay comparable."""
    from core.consequence import no_reserve
    with no_reserve():
        return _options(cards, budget, strategy, gap, monthly, today)


def _options(cards, budget, strategy, gap, monthly=None, today=None):
    """R1 / R5: the three timings through the same engine. Minimums are always paid in full (the engine pays them
    first); a schedule takes only from the extra above them. Stated assumptions: 'before' sends the extra the
    budget has today (cards freed later add more, so its dates are on the late side); after the last debt the
    whole debt budget goes to the reserve."""
    from core.consequence import extra_above_minimums, simulate_payoff
    if not cards:
        return {'available': False, 'why': 'No debt on record, so there is nothing for the reserve to come before or after.'}
    if gap is None:
        return {'available': False, 'why': 'Set a target first; the comparison needs to know how much the reserve is for.'}
    extra = extra_above_minimums(cards, budget)
    base = simulate_payoff(cards, budget, strategy=strategy)
    if base is None or extra is None:
        return {'available': False, 'why': 'The debt budget doesn\'t cover the minimum payments, so no plan can be dated.'}

    def row(key, sim, full_month, note):
        return {'key': key, 'debt_free': month_label(sim['months'], today), 'debt_months': sim['months'],
                'interest': sim['total_interest'], 'reserve_full': (month_label(full_month, today) if full_month else 'already full'),
                'note': note}

    out = []
    full_after = None if gap == 0 else base['months'] + math.ceil(gap / float(budget))
    out.append(row('after', base, full_after, 'How the payoff plan works today: every extra dollar goes to debt until it '
                   'is paid, then the whole debt budget goes to the reserve.'))
    if gap == 0:
        for k in ('before', 'alongside'):
            out.append(row(k, base, None, 'The reserve is already full, so this changes nothing.'))
        return {'available': True, 'extra': extra, 'options': out}
    if extra <= 0:
        out.append({'key': 'before', 'unavailable': 'Nothing is left above the minimum payments to put toward it.'})
    else:
        n = math.ceil(gap / extra)
        sim = simulate_payoff(cards, budget, strategy=strategy, extra_schedule=[-extra] * n)
        out.append(row('before', sim, n, f'The {money(extra)} a month above the minimums goes to the reserve for {n} '
                       f'month{"s" if n != 1 else ""}, then to debt. Minimum payments never change.'))
    if not monthly:
        out.append({'key': 'alongside', 'unavailable': 'Enter a monthly amount to see this one.'})
    else:
        x = min(float(monthly), max(0.0, extra))
        if x <= 0:
            out.append({'key': 'alongside', 'unavailable': 'Nothing is left above the minimum payments to put toward it.'})
        else:
            n = math.ceil(gap / x)
            sim = simulate_payoff(cards, budget, strategy=strategy, extra_schedule=[-x] * n)
            capped = ' (capped at what is above the minimums)' if x < float(monthly) else ''
            out.append(row('alongside', sim, n, f'{money(x)} a month{capped} goes to the reserve for {n} '
                           f'month{"s" if n != 1 else ""}, the rest to debt. Minimum payments never change.'))
    return {'available': True, 'extra': extra, 'options': out}
