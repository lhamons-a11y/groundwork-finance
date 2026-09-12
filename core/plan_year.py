# -*- coding: utf-8 -*-
"""Plan years — what was covered, under which terms, and when we learned them.

Implements `gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §4, and is specified by
`tests/test_plan_year_fixture.py`, written before this file existed.

    current_plan_year = 2026 cannot explain history
    EDIT and CORRECTION are different operations, and the system must know which happened
    late-arriving plan data is first class
    the critical case: Plan A Jan-Jun, Plan B Jul-Dec
    rollover is not year += 1
    a historical plan record is effectively immutable

**Accumulators are derived, never stored**, and that single choice is what makes most of the
list above true for free. A stored `deductible_met` has to be reset at a year boundary, has to
be recomputed when a correction lands, and has to be migrated when a plan is added — three
chances to forget. A query over the expenses in a period cannot forget, which is why there is
no `rollover()` here and why adding a plan cannot disturb an earlier one.

**The distinction the module exists to keep.** Discovering the deductible was $2,000 rather
than $3,000 says the figure was *always* wrong, and it changes what was true in February.
Switching from Plan A to Plan B says what is true *going forward*, and it must not touch
February at all. Both are recorded, and which one happened is answerable — `operations()`.

**And the one that matters most when it is wrong.** How much was spent is a fact; whether it
met a deductible is an interpretation of that fact against terms. When the terms have not
arrived, the interpretation is `UNKNOWN` — never `False`, never zero. Telling someone their
deductible is unmet because their plan has not been entered is inventing a fact about their
coverage, which is `ARCHITECTURE_PRINCIPLES.md` §3 in the place it costs most.
"""

from dataclasses import dataclass, field
from datetime import datetime

# Not False and not zero. A consumer that wants a boolean must decide what to do about not
# knowing, rather than being handed a plausible one.
UNKNOWN = object()

# What may honestly be done to a plan that has history. Destroying it strips context from
# every expense incurred under it.
DELETION_MODES = ('close_period', 'delete_if_unused')


def _now():
    return datetime.utcnow().isoformat(timespec='seconds')


@dataclass
class Plan:
    """Identity and period only. Terms live in versions, so this row never changes — which is
    what lets `plan_at()` return the same object before and after a correction."""
    id: int
    name: str
    effective_from: str
    effective_to: str
    seq: int


@dataclass
class TermVersion:
    """Terms as of a point in the record, with what they were before.

    `previous` is the difference between a correction and a first statement, and it is what a
    user is owed when a number they were shown changes underneath them.
    """
    plan_id: int
    terms: dict
    previous: dict = None
    reason: str = None
    source: str = None
    seq: int = 0
    recorded_at: str = None


@dataclass
class Operation:
    """`change` = what is true going forward. `correction` = what was always true.
    Collapsing these is how a plan switch silently rewrites February."""
    kind: str
    plan_id: int
    seq: int
    recorded_at: str = None


@dataclass
class Registry:
    plans: list = field(default_factory=list)
    terms: list = field(default_factory=list)
    ops: list = field(default_factory=list)
    _next_id: int = 1
    _seq: int = 0


_REGISTRY = Registry()


def reset():
    global _REGISTRY
    _REGISTRY = Registry()
    return _REGISTRY


def _r():
    return _REGISTRY


def now():
    """A marker for 'as of this point in the record'. A counter, not a clock."""
    return _r()._seq


# ── Plans and their terms ───────────────────────────────────────────────────

def _term(v):
    """A term the caller supplied, or None for one they did not.

    Not `float(v)`, and not a default of `0.0`. A plan added before its terms are known used to
    get a deductible of zero, and `applied >= 0.0` is true the moment anything is spent - so
    the module's own promise (`UNKNOWN`, never False, never zero) was unreachable through its
    own API, and a user who had not found their deductible yet was told it was met.
    `gw 2.0/APPLICABILITY_CASES.md` C1/C4/C5; quarantined in `HEALTHCARE_GAP_TRIAGE.md`.

    This is a narrow repair, not the applicability decision. A plan that genuinely has no
    deductible must be entered as `deductible=0.0` explicitly - and a plan whose caller omits
    the deductible reads UNKNOWN, which for an HMO is conservative rather than correct. That is
    an intentional consequence of today's representation, NOT evidence that "unknown
    deductible" and "no deductible" are one state. They are not, and that is the open axis.
    """
    return None if v is None else float(v)


def add_plan(name=None, deductible=None, oop_max=None, effective_from=None,
             effective_to=None):
    """A plan change: what is true going forward. Never a correction to what came before.

    Terms default to None - not supplied - and stay None until a caller supplies them.
    """
    r = _r()
    r._seq += 1
    p = Plan(id=r._next_id, name=name, effective_from=effective_from,
             effective_to=effective_to, seq=r._seq)
    r._next_id += 1
    r.plans.append(p)
    r.terms.append(TermVersion(plan_id=p.id,
                               terms={'deductible': _term(deductible),
                                      'oop_max': _term(oop_max)},
                               previous=None, seq=r._seq, recorded_at=_now()))
    r.ops.append(Operation(kind='change', plan_id=p.id, seq=r._seq, recorded_at=_now()))
    return p


def correct_terms(plan, reason=None, source=None, **new_terms):
    """A correction: the figure was always wrong, so the historical conclusion moves with it.

    This is the operation that *should* change what was true in February, and the reason it
    is safe to let it is that the prior version survives and every conclusion stays
    reproducible `as_of` the point it was drawn.
    """
    r = _r()
    r._seq += 1
    prior = terms_at(plan)
    merged = dict(prior)
    merged.update({k: _term(v) for k, v in new_terms.items()})
    r.terms.append(TermVersion(plan_id=plan.id, terms=merged, previous=dict(prior),
                               reason=reason, source=source, seq=r._seq,
                               recorded_at=_now()))
    r.ops.append(Operation(kind='correction', plan_id=plan.id, seq=r._seq,
                           recorded_at=_now()))
    return r.terms[-1]


def term_history(plan):
    return [t for t in _r().terms if t.plan_id == plan.id]


def terms_at(plan, as_of=None):
    rows = term_history(plan)
    if as_of is not None:
        rows = [t for t in rows if t.seq <= as_of]
    return dict(rows[-1].terms) if rows else {}


def operations(plan=None):
    return [o for o in _r().ops if plan is None or o.plan_id == plan.id]


def plans(as_of=None):
    return [p for p in _r().plans if as_of is None or p.seq <= as_of]


def plan_at(when, as_of=None):
    """The plan in force on a date, as the record stood at `as_of`.

    Two different times, and keeping them apart is what makes late-arriving plan data first
    class: a plan entered in March covers a January expense, and the answer given in February
    is still reproducible.
    """
    for p in plans(as_of):
        if (p.effective_from or '') <= (when or '') <= (p.effective_to or '9999-12-31'):
            return p
    return None


def plan_of(expense_key, expenses, as_of=None):
    row = (expenses or {}).get(expense_key) or {}
    return plan_at(row.get('date'), as_of)


def delete_plan(plan, expenses=None):
    """Refused for a plan anything was incurred under. Returns False rather than raising: the
    caller is expected to offer `close_period` instead."""
    covered = any((plan.effective_from or '') <= (e.get('date') or '')
                  <= (plan.effective_to or '9999-12-31')
                  for e in (expenses or {}).values())
    if covered:
        return False
    r = _r()
    r.plans = [p for p in r.plans if p.id != plan.id]
    r.terms = [t for t in r.terms if t.plan_id != plan.id]
    r.ops = [o for o in r.ops if o.plan_id != plan.id]
    return True


def deletion_modes():
    return set(DELETION_MODES)


# ── Accumulators, derived on every read ─────────────────────────────────────

def _in_period(plan, when):
    return (plan.effective_from or '') <= (when or '') <= (plan.effective_to or '9999-12-31')


def accumulators(expenses, plan, as_of=None):
    """What has been applied under one plan, and what that does or does not establish.

    `oop_applied` is reported beside the deductible rather than derived from it, because they
    answer different questions and a user reading one as the other is the failure the design
    already refuses elsewhere: an out-of-pocket maximum is a coverage-based target, not a
    promise that nothing further will be charged.
    """
    terms = terms_at(plan, as_of)
    applied = round(sum(e['amount'] for e in (expenses or {}).values()
                        if _in_period(plan, e.get('date'))), 2)
    deductible = terms.get('deductible')
    oop_max = terms.get('oop_max')
    return {
        'plan': plan.name,
        'applied': applied,
        'deductible': deductible,
        'deductible_met': (UNKNOWN if deductible is None else applied >= deductible),
        'oop_applied': applied,
        'oop_max': oop_max,
        'oop_met': (UNKNOWN if oop_max is None else applied >= oop_max),
    }


def year_summary(expenses, year, as_of=None):
    """A calendar year, broken into the plan periods that actually covered it.

    A year is not a plan. Two plans inside one year is the normal case, and reporting one
    number for it would be reporting an average of two different contracts. So the periods are
    the answer, and the top-level `deductible_met` is only available when exactly one plan
    covered the whole of the year's spending.

    Spending under no plan at all is `unattributed`: reported, never dropped, and never
    silently added to whichever plan happens to be nearest.
    """
    y = str(year)
    rows = {k: e for k, e in (expenses or {}).items()
            if (e.get('date') or '').startswith(y)}
    applied = round(sum(e['amount'] for e in rows.values()), 2)

    periods = []
    for p in plans(as_of):
        if not any(_in_period(p, e.get('date')) for e in rows.values()):
            continue
        periods.append(accumulators(rows, p, as_of))

    unattributed = round(sum(e['amount'] for e in rows.values()
                             if plan_at(e.get('date'), as_of) is None), 2)

    if len(periods) == 1 and unattributed == 0.0:
        met = periods[0]['deductible_met']
    else:
        # No plan covers it, or more than one does. Either way there is no single answer,
        # and manufacturing one would be answering a question nobody can ask coherently.
        met = UNKNOWN

    return {'year': int(year), 'applied': applied, 'deductible_met': met,
            'periods': periods, 'unattributed': unattributed}
