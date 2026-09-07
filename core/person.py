# -*- coding: utf-8 -*-
"""Person identity — who an expense belongs to, and why that is not a name.

Implements `gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §3, and is specified by
`tests/test_person_identity_fixture.py`, which was written before this file existed.

    person_id is identity; display_name is presentation
    reassignment is a financially meaningful CORRECTION, not a cosmetic edit
    imported "patient = ROB L." must map EXPLICITLY - name matching is not identity
    person survives plan changes; coverage enrolment does not
    deleting a person with history means INACTIVE, never destroyed

**The invariant that holds the rest together** comes from `HEALTHCARE_MODULE_DESIGN.md` §1.7:
the tax report is the **household total**, and the per-person split is supporting detail. So
moving an expense between household members changes the attribution and must not change what
the household deducts. Without that, a reassignment is a way to move money.

**Names are labels, not access control** (§1.7 again). Nothing here restricts who may see
whose data; a shared ledger answers that for everyone at once, and the interface is where that
gets said plainly.

**This module owns *which person*, never *how much*.** Amounts are supplied by the caller, the
same division of labour `core/solution.py` uses when it takes `months_observed` on trust: the
caller holds the ledger.

**Why this one has state when the calculation modules do not.** Identity is inherently a
registry — `core/solution.py` and `core/consequence.py` can be pure because a payoff is a
function of its inputs, and a person is not. The module-level registry is the default one;
`Registry` is exposed for a caller that wants its own, and `reset()` exists so a test can start
from an empty household.
"""

from dataclasses import dataclass, field
from datetime import datetime

# The honest operations on a person who has history. Destroying an identity that 500
# transactions point at is not one of them.
DELETION_MODES = ('deactivate', 'delete_if_unused')


def _now():
    return datetime.utcnow().isoformat(timespec='seconds')


@dataclass
class Person:
    id: int
    display_name: str
    active: bool = True


@dataclass
class PersonAssignment:
    """Which person an expense belongs to, as a version rather than a field.

    A reassignment changes deductible accumulation, out-of-pocket accumulation, HSA
    eligibility, tax reporting and the reserve. That is a correction to a financial fact, so
    it carries a reason, a source and a date, and it supersedes rather than overwrites — or a
    historical figure cannot be explained once a late correction arrives.
    """
    expense_key: str
    person_id: int
    mode: str                     # 'initial' | 'correction'
    seq: int
    reason: str = None
    source: str = None
    recorded_at: str = None


@dataclass
class Enrolment:
    person_id: int
    plan: str
    effective_on: str


@dataclass
class Alias:
    person_id: int
    alias: str
    source: str


@dataclass
class Registry:
    people: list = field(default_factory=list)
    assignments: list = field(default_factory=list)
    aliases: list = field(default_factory=list)
    enrolments: list = field(default_factory=list)
    _next_id: int = 1
    _seq: int = 0


_REGISTRY = Registry()


def reset():
    """Start from an empty household. A test precondition, not an operation the product has."""
    global _REGISTRY
    _REGISTRY = Registry()
    return _REGISTRY


def _r():
    return _REGISTRY


# ── Identity ────────────────────────────────────────────────────────────────

def add_person(display_name):
    r = _r()
    p = Person(id=r._next_id, display_name=display_name)
    r._next_id += 1
    r.people.append(p)
    return p


def id_of(person):
    return person.id


def display_name(person):
    return person.display_name


def rename(person, new_name):
    """Presentation only. Nothing financial happened, so nothing financial is recorded —
    which is the point: a rename that showed up in the correction history would teach a user
    that fixing a typo is the same kind of act as moving an expense between patients."""
    person.display_name = new_name
    return person


def people(active_only=False):
    return [p for p in _r().people if p.active or not active_only]


def is_active(person):
    return bool(person.active)


def deactivate(person):
    person.active = False
    return person


def has_history(person):
    return any(a.person_id == person.id for a in _r().assignments) \
        or any(e.person_id == person.id for e in _r().enrolments)


def delete(person):
    """Refused for anyone with history. Returns False rather than raising, because the caller
    is expected to offer `deactivate` instead — the refusal is a product behaviour, not an
    error condition."""
    if has_history(person):
        return False
    r = _r()
    r.people = [p for p in r.people if p.id != person.id]
    r.aliases = [a for a in r.aliases if a.person_id != person.id]
    return True


def deletion_modes():
    return set(DELETION_MODES)


# ── Names, which are not identity ───────────────────────────────────────────

def map_alias(person, alias, source=None):
    """The explicit mapping an import must make. `patient = "ROB L."` is a string a billing
    system chose; it becomes identity only when a person says so."""
    _r().aliases.append(Alias(person_id=person.id, alias=alias, source=source))
    return person


def alias_source(person, alias):
    for a in _r().aliases:
        if a.person_id == person.id and a.alias == alias:
            return a.source
    return None


def resolve_name(name):
    """An explicit alias, or an exact and unique display name. Nothing else.

    Exact-and-unique is a lookup rather than a match, and the distinction is the whole rule:
    `John` and `John Jr.` are two people, and any scheme willing to call those a match will
    eventually put one person's prescriptions on the other's record. An ambiguous name — two
    people called Sam — resolves to nobody, because guessing between them is the same error
    wearing a coin flip.
    """
    r = _r()
    for a in r.aliases:
        if a.alias == name:
            return a.person_id
    exact = [p for p in r.people if p.display_name == name]
    return exact[0].id if len(exact) == 1 else None


# ── Assignment, and correcting it ───────────────────────────────────────────

def now():
    """A marker for 'as of this point', used to reproduce a figure as it stood. A counter
    rather than a clock, so the answer does not depend on how fast the test runs."""
    return _r()._seq


def _record(expense_key, person, mode, reason=None, source=None):
    r = _r()
    r._seq += 1
    a = PersonAssignment(expense_key=expense_key, person_id=person.id, mode=mode,
                         seq=r._seq, reason=reason, source=source, recorded_at=_now())
    r.assignments.append(a)
    return a


def assign(expense_key, person):
    return _record(expense_key, person, 'initial')


def reassign(expense_key, person, reason=None, source=None):
    """A correction to a financial fact. The prior assignment survives it."""
    return _record(expense_key, person, 'correction', reason=reason, source=source)


def assignments(expense_key):
    """Every assignment for one expense, oldest first. Superseded, never overwritten."""
    return [a for a in _r().assignments if a.expense_key == expense_key]


def person_of(expense_key, as_of=None):
    """Who this expense belonged to — now, or as of a point in the record.

    Returns None when nobody has said. That is not a gap to fill: an expense whose patient
    has not been recorded belongs to nobody, and attributing it to the only other candidate
    is manufacturing a fact about someone's medical care.
    """
    rows = assignments(expense_key)
    if as_of is not None:
        rows = [a for a in rows if a.seq <= as_of]
    return rows[-1].person_id if rows else None


# ── Totals: the household is the figure that reaches a return ───────────────

def per_person_total(expenses, person, as_of=None):
    pid = person.id if isinstance(person, Person) else person
    return round(sum(amount for key, amount in (expenses or {}).items()
                     if person_of(key, as_of) == pid), 2)


def household_total(expenses):
    """Everything, whoever the patient was.

    Section 213 lets a taxpayer deduct what they paid for a spouse and dependents, so this is
    the figure that reaches the return — and it is deliberately indifferent to attribution,
    which is what makes a reassignment unable to move money.
    """
    return round(sum((expenses or {}).values()), 2)


def unassigned_total(expenses, as_of=None):
    """Reported beside the per-person split rather than folded into it or dropped. The parts
    plus this equal the whole, with nothing invented and nothing lost."""
    return round(sum(amount for key, amount in (expenses or {}).items()
                     if person_of(key, as_of) is None), 2)


# ── Coverage enrolment, which is not the person ─────────────────────────────

def enrol(person, plan=None, effective_on=None):
    """A person survives a plan change. Mutating a `plan_id` on the person would destroy the
    first half of a year in which they changed plans, so enrolment is its own timeline."""
    e = Enrolment(person_id=person.id, plan=plan, effective_on=effective_on)
    _r().enrolments.append(e)
    return e


def enrolments(person):
    return [e for e in _r().enrolments if e.person_id == person.id]


def enrolment_at(person, when):
    eligible = [e for e in enrolments(person)
                if not e.effective_on or e.effective_on <= (when or '')]
    if not eligible:
        return None
    return sorted(eligible, key=lambda e: e.effective_on or '')[-1].plan
