"""The health plan card: deductible, out-of-pocket maximum, progress and the plan year (gw 2.0/PLAN_YEAR_TRACKING.md,
item 87 = item 45 H7 stage 2; P1-P9 ruled 2026-10-15).

core/plan_year.py's rules, kept over the tables that already exist:
    a plan is identity and a period; its terms are versions, each keeping what it replaced
    a CORRECTION says the figure was always this (the old one is kept and named); a CHANGE is what is true from a date,
        so it closes the plan the day before and starts a new one - the earlier part of the year is never rewritten
    two plans covering one date are refused (plan_year.OVERLAP), here at the door rather than at read
    a term not entered is unknown - never 0, never "met"

P1: progress is what the insurer reports, typed by the person with its date. It is never summed from spending - a
payment shows what was paid, not what the insurer applied. P7: the terms are taught, and nothing here suggests what
to do or when.
"""
from datetime import date, timedelta, timezone

from core.hsa_fsa import money, day

TIERS = ('self', 'family', '')
HELP = ('A deductible is what you pay for covered care before the plan starts sharing the cost. After it, '
        'coinsurance is the share you still pay (for example 20%) and copays are set amounts per visit or '
        'prescription. The out-of-pocket maximum is the most you pay for covered, in-network care in a plan year; '
        'after it, the plan pays the rest of covered costs. Both figures start over when a new plan year begins. '
        'What counts toward them is decided by your insurer, so Groundwork shows the figures you enter from them.')


def _num(v, name):
    if v in (None, ''):
        return None, None
    try:
        v = round(float(v), 2)
    except (TypeError, ValueError):
        return None, f'{name} must be an amount or blank'
    if v < 0:
        return None, f'{name} must be zero or more'
    return v, None


def _date(v, name, required=False):
    v = str(v or '').strip()
    if not v:
        return None, (f'{name} is required' if required else None)
    try:
        date.fromisoformat(v)
    except ValueError:
        return None, f'{name} must be a date (YYYY-MM-DD)'
    return v, None


def _next_seq(session):
    from sqlalchemy import func
    from core.database import HealthPlan, HealthPlanOperation, HealthPlanTermVersion
    return 1 + max(session.query(func.max(m.seq)).scalar() or 0
                   for m in (HealthPlan, HealthPlanTermVersion, HealthPlanOperation))


def _overlaps(session, start, end, skip_id=None):
    from core.database import HealthPlan
    end = end or '9999-12-31'
    for p in session.query(HealthPlan).all():
        if p.id == skip_id:
            continue
        if p.effective_from <= end and start <= (p.effective_to or '9999-12-31'):
            return p
    return None


def _terms(body):
    out = {}
    for k in ('deductible', 'oop_max'):
        out[k], problem = _num(body.get(k), k)
        if problem:
            return None, problem
    tier = str(body.get('tier') or '').strip().lower()
    if tier not in TIERS:
        return None, 'tier must be self, family or blank'
    out['tier'] = tier
    return out, None


def add_plan(session, body):
    """A new plan: a change, what is true going forward."""
    from core.database import HealthPlan, HealthPlanOperation, HealthPlanTermVersion
    name = str(body.get('name') or '').strip()[:80]
    if not name:
        return None, 'a name for the plan is required'
    start, p1 = _date(body.get('effective_from'), 'the start date', required=True)
    end, p2 = _date(body.get('effective_to'), 'the end date')
    terms, p3 = _terms(body)
    problem = p1 or p2 or p3
    if problem:
        return None, problem
    if end and end < start:
        return None, 'the end date is before the start date'
    other = _overlaps(session, start, end)
    if other:
        return None, (f'"{other.name}" already covers part of those dates. Two plans can\'t cover the same date '
                      'here; end the earlier plan first.')
    seq = _next_seq(session)
    plan = HealthPlan(name=name, effective_from=start, effective_to=end, seq=seq)
    session.add(plan)
    session.flush()
    session.add(HealthPlanTermVersion(plan_id=plan.id, seq=seq, **terms))
    session.add(HealthPlanOperation(plan_id=plan.id, kind='change', seq=seq))
    session.flush()
    return plan, None


def current_terms(session, plan_id):
    from core.database import HealthPlanTermVersion
    return session.query(HealthPlanTermVersion).filter_by(plan_id=plan_id) \
        .order_by(HealthPlanTermVersion.seq.desc()).first()


def correct_terms(session, plan, body):
    """The figure was always this: a new version keeping the old one, and the past moves with it."""
    from core.database import HealthPlanOperation, HealthPlanTermVersion
    new, problem = _terms(body)
    if problem:
        return None, problem
    prior = current_terms(session, plan.id)
    seq = _next_seq(session)
    v = HealthPlanTermVersion(plan_id=plan.id, seq=seq, previous_deductible=prior.deductible if prior else None,
                              previous_oop_max=prior.oop_max if prior else None,
                              reason=str(body.get('reason') or 'corrected')[:200], source='typed', **new)
    session.add(v)
    session.add(HealthPlanOperation(plan_id=plan.id, kind='correction', seq=seq))
    session.flush()
    return v, None


def change_terms(session, plan, body):
    """From a date on: the plan closes the day before and a new one carries the new terms to the old end. The part
    of the year before the date keeps its terms and its readings (plan_year: a switch never rewrites February)."""
    from core.database import HealthPlanOperation
    when, problem = _date(body.get('from'), 'the date it changed', required=True)
    if problem:
        return None, problem
    if when <= plan.effective_from:
        return None, 'a change has to start after the plan began; if the figure was always different, it is a correction'
    if plan.effective_to and when > plan.effective_to:
        return None, 'that date is after this plan ends'
    terms, problem = _terms(body)
    if problem:
        return None, problem
    old_end = plan.effective_to
    plan.effective_to = (date.fromisoformat(when) - timedelta(days=1)).isoformat()      # plan_year: close_period
    session.add(HealthPlanOperation(plan_id=plan.id, kind='change', seq=_next_seq(session)))
    session.flush()
    return add_plan(session, dict(terms, name=plan.name, effective_from=when, effective_to=old_end))


def add_reading(session, plan, body, today=None):
    """P1/P3: what the insurer reports, as typed, with its date. Kept, never edited."""
    from core.database import HealthPlanReading
    today = today or date.today()
    as_of, problem = _date(body.get('as_of') or today.isoformat(), 'the as-of date')
    if problem:
        return None, problem
    if as_of > today.isoformat():
        return None, 'the as-of date is in the future'
    if as_of < plan.effective_from:
        return None, 'the as-of date is before this plan began'
    vals = {}
    for k in ('deductible_met', 'oop_met'):
        vals[k], problem = _num(body.get(k), k.replace('_', ' '))
        if problem:
            return None, problem
    pid = body.get('person_id')            # item 92 N5b: one person's figures in a family plan, or the plan's own
    if pid not in (None, ''):
        from core.database import Person
        p = session.get(Person, int(pid))
        if not p or not p.active:
            return None, 'That person was not found.'
        vals['person_id'] = p.id
    if vals['deductible_met'] is None and vals['oop_met'] is None:
        return None, 'enter at least one figure'
    r = HealthPlanReading(plan_id=plan.id, as_of=as_of, **vals)
    session.add(r)
    session.flush()
    return r, None


def _readings(session, plan_id):
    from core.database import HealthPlanReading
    return session.query(HealthPlanReading).filter_by(plan_id=plan_id) \
        .order_by(HealthPlanReading.as_of.desc(), HealthPlanReading.id.desc()).all()


def _line(label, total, met, as_of):
    """One figure with its working. Unknown stays unknown (P4)."""
    if total is None:
        return f'{label}: not entered.'
    if met is None:
        return f'{label}: {money(total)}. Met so far: not entered yet.'
    left = round(max(0.0, total - met), 2)
    if left == 0:
        return f'{label}: met - {money(met)} of {money(total)}, as of {day(as_of)}.'
    return f'{label}: {money(met)} of {money(total)} met, {money(left)} left, as of {day(as_of)}.'


def _last_health_payment(session):
    """The newest health payment on record (by category, or from an HSA / FSA) - for P3's stale-reading fact."""
    from core import health_boundary as hb
    from core.database import Transaction
    is_health = hb.health_rows(session)
    rows = session.query(Transaction).filter(Transaction.type == 'debit').order_by(Transaction.date.desc()).limit(2000).all()
    for t in rows:
        if is_health(t) and t.date:
            return t.date.isoformat()
    return None


def plan_state(session, plan, today=None):
    today = today or date.today()
    v = current_terms(session, plan.id)
    allreads = _readings(session, plan.id)
    reads = [r for r in allreads if r.person_id is None]           # the plan's own figures
    mine = [r for r in allreads if r.person_id is not None]        # item 92 N5b: per person, in a family plan
    # The newest reading of each figure: a later reading may give only one of the two.
    ded = next(((r.deductible_met, r.as_of) for r in reads if r.deductible_met is not None), (None, None))
    oop = next(((r.oop_met, r.as_of) for r in reads if r.oop_met is not None), (None, None))
    lines = [_line('Deductible', v.deductible if v else None, *ded),
             _line('Out-of-pocket maximum', v.oop_max if v else None, *oop)]
    if reads:
        lines.append('From your insurer, as you entered it. Groundwork doesn\'t work these out from your spending.')
    notes = []
    if v and (v.previous_deductible is not None or v.previous_oop_max is not None):
        was = [f'deductible {money(v.previous_deductible)}' if v.previous_deductible is not None and v.previous_deductible != v.deductible else '',
               f'out-of-pocket maximum {money(v.previous_oop_max)}' if v.previous_oop_max is not None and v.previous_oop_max != v.oop_max else '']
        was = [w for w in was if w]
        if was:
            on = v.recorded_at.replace(tzinfo=timezone.utc).astimezone().date()     # stored in UTC; said in local time
            notes.append(f'Corrected on {day(on.isoformat())}: it was {" and ".join(was)} before (you said the new figure was always right).')
    newest = max([d for d in (ded[1], oop[1]) if d] or [None]) if reads else None
    last_paid = _last_health_payment(session)
    if newest and last_paid and last_paid > newest:
        notes.append(f'Your last reading is from {day(newest)}; you\'ve paid health bills since then, on or before '
                     f'{day(last_paid)}. Groundwork doesn\'t guess how they changed these figures.')
    people = []
    if mine:
        from core.database import Person
        names = {p.id: p.display_name for p in session.query(Person).all()}
        for pid in sorted({r.person_id for r in mine}, key=lambda i: names.get(i, '').lower()):
            rs = [r for r in mine if r.person_id == pid]
            pd = next(((r.deductible_met, r.as_of) for r in rs if r.deductible_met is not None), (None, None))
            po = next(((r.oop_met, r.as_of) for r in rs if r.oop_met is not None), (None, None))
            bits = ([f'{money(pd[0])} toward the deductible as of {day(pd[1])}'] if pd[0] is not None else []) \
                + ([f'{money(po[0])} toward the out-of-pocket maximum as of {day(po[1])}'] if po[0] is not None else [])
            people.append({'person_id': pid, 'name': names.get(pid, ''), 'deductible_met': pd[0], 'oop_met': po[0],
                           'line': f'{names.get(pid, "")}: ' + ', '.join(bits) + ' (from your insurer).'})
    if v and v.tier == 'family' and not people:
        notes.append('Per-person amounts: none entered yet. Your insurer shows them member by member.')
    if plan.effective_to:
        reset = date.fromisoformat(plan.effective_to) + timedelta(days=1)
        days = (reset - today).days
        if days >= 0:
            notes.append(f'These figures start over on {day(reset.isoformat())} ({days} day{"s" if days != 1 else ""}).')
    else:
        notes.append('The plan year\'s end isn\'t entered, so when these figures start over isn\'t known.')
    return {'id': plan.id, 'name': plan.name, 'from': plan.effective_from, 'to': plan.effective_to,
            'tier': v.tier if v else '', 'deductible': v.deductible if v else None, 'oop_max': v.oop_max if v else None,
            'deductible_met': ded[0], 'oop_met': oop[0], 'lines': lines + [p['line'] for p in people], 'notes': notes,
            'people': people,
            'readings': [{'deductible_met': r.deductible_met, 'oop_met': r.oop_met, 'as_of': r.as_of} for r in reads],
            'current': plan.effective_from <= today.isoformat() <= (plan.effective_to or '9999-12-31')}


def states(session, today=None):
    from core.database import HealthPlan
    today = today or date.today()
    out = [plan_state(session, p, today) for p in
           session.query(HealthPlan).order_by(HealthPlan.effective_from.desc(), HealthPlan.id.desc()).all()]
    return {'plans': out, 'current': next((p for p in out if p['current']), None), 'help': HELP}


def export_rows(session):
    """P8: the plans for an export, only when the health box is ticked."""
    from core.database import HealthPlan
    return [dict(plan_state(session, p), lines=None, notes=None)
            for p in session.query(HealthPlan).order_by(HealthPlan.effective_from).all()]
