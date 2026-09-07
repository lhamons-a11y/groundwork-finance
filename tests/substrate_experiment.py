# -*- coding: utf-8 -*-
"""The substrate experiment — can `HistorianEntry` carry the lifecycle fixture?

`gw 2.0/EVENT_SUBSTRATE_QUESTION.md` pre-registered a failure criterion before any of this
was built, so the answer could not be argued on attachment:

> **The historian fails the experiment if carrying the fixture requires more than two
> structural relationships to live inside `context_json`, or if any read path must parse JSON
> to enforce an invariant.**

`core/allocation.py` satisfies the fixture in memory, which says nothing about this: the model
never touched storage. This is the part that touches storage.

**How the criterion is measured rather than inspected.** Two ways, both mechanical:

1. `RELATIONSHIPS` below is a manifest — every structural relationship the fixture needs, and
   where it lives. Anything homed in `context_json` is counted against the criterion.
2. **A phase with the JSON column permanently NULL.** Not wiping JSON after the fact — wiping
   leaves the next run free to write fresh JSON and quietly depend on it, which is how this
   experiment first reported a pass it had not earned. Instead the whole fixture runs a second
   time with `context_json` never written at all. If any invariant needed it, the fixture
   fails.

3. **And the experiment proves it can fail.** Two deliberate breakages — the event→expense
   relationship moved out of its foreign key and into JSON, and an allocation amount moved out
   of its column into JSON — must both be caught. A criterion that cannot fail is not a
   criterion.

**It now tests the SHIPPED schema.** The candidate tables were landed in `core/database.py`
on 2026-09-07 and this file imports them rather than redefining them, so it can no longer drift
from the thing it claims to test — and a change to the shipped shape that breaks the criterion
fails here rather than being noticed later.

Run:  python tests/substrate_experiment.py
"""
import io as _io
import os
import sys
import json
import contextlib
import shutil
import tempfile
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Isolation MUST happen before core.database is imported, exactly as smoke_test.py does it.
_TMP = tempfile.mkdtemp(prefix='gw_substrate_')
os.environ['GROUNDWORK_DATA_DIR'] = _TMP

from sqlalchemy import (Column, Integer, String, Float, Text, DateTime,   # noqa: E402
                        ForeignKey, Index)
from datetime import datetime                                            # noqa: E402

from core import database as db                                          # noqa: E402
from core import allocation as alloc                                     # noqa: E402
from core import person as personmod                                     # noqa: E402
from core import plan_year as planmod                                    # noqa: E402

PASS, FAIL = [], []

# Phase switches. Phase 2 runs with the JSON column permanently NULL, which is a far stronger
# claim than wiping it after the fact: wiping leaves the next run free to write fresh JSON and
# quietly depend on it. Phase 3 deliberately moves things INTO json to prove the experiment
# can fail - a criterion that cannot fail is not a criterion.
WRITE_JSON = True
JSON_RELATIONSHIP = False      # event -> expense lives in JSON instead of a foreign key
JSON_AMOUNTS = False           # the allocation amount lives in JSON instead of its column


def check(name, condition):
    (PASS if condition else FAIL).append(name)
    print(f'  {"OK  " if condition else "FAIL"}  {name}')


# ── The manifest: every structural relationship, and where it lives ─────────
# "Structural" means a relationship financial integrity depends on. A value that merely
# explains (a plan year label, a note) is not one, and JSON is the right home for those.
RELATIONSHIPS = [
    ('event -> expense',              'fk',         'historian.healthcare_expense_id'),
    ('obligation version -> expense', 'fk',         'expense_obligation_versions.expense_id'),
    ('funding allocation -> expense', 'fk',         'expense_funding_allocations.expense_id'),
    ('allocation version -> prior',   'fk',         'expense_funding_allocations.supersedes_id'),
    ('determination -> expense',      'fk',         'expense_determinations.expense_id'),
    ('determination -> prior',        'fk',         'expense_determinations.supersedes_id'),
    ('expense -> the plan covering it', 'derived',  'health_plans period covering incurred_on'),
    # Derived, and therefore nothing to persist per expense - which is the point. Note that
    # this leaves `health_plans` and its term versions exercised by NOTHING here: the fixture
    # no longer issues plan changes, because allocation no longer owns them, and
    # `core/plan_year.py` has no persistence layer yet. That is a real gap, named rather than
    # papered over.
    ('expense -> its person',         'link_table', 'person_assignments'),
    ('merged expense -> its sources', 'link_table', 'expense_merge_links'),
]

# `tax_rule_versions` is household-scoped rather than per-expense: the rules in force are not
# a property of a charge. And a year roll is deliberately absent - it carries no fact and no
# relationship, so it is an event in the historian and nothing else. That is the correct use
# of `context_json`, which may carry explanatory context and may not carry integrity.


# ── The shipped schema ──────────────────────────────────────────────────────
# Structure in tables with real foreign keys; events in the historian. The split the codebase
# already makes in `create_debt_ledger_entry`, seven lines apart, pointed at a new object.
#
# These are the models in `core/database.py`. Importing rather than mirroring them is the
# point: the experiment tests what ships.

HealthcareExpense = db.HealthcareExpense
ExpenseObligationVersion = db.ExpenseObligationVersion
ExpenseFundingAllocation = db.ExpenseFundingAllocation
ExpenseDetermination = db.ExpenseDetermination
ExpenseMergeLink = db.ExpenseMergeLink
ExpenseRefund = db.ExpenseRefund
TaxRuleVersion = db.TaxRuleVersion
HealthPlan = db.HealthPlan
HealthPlanTermVersion = db.HealthPlanTermVersion
HealthPlanOperation = db.HealthPlanOperation
Person = db.Person
PersonAlias = db.PersonAlias
PersonAssignment = db.PersonAssignment
PersonEnrolment = db.PersonEnrolment
Historian = db.HistorianEntry


# ── Persisting and rehydrating ──────────────────────────────────────────────

class Ref:
    """What the fixture passes around. Nothing but a database id — deliberately, so no state
    can survive in memory and flatter the round trip."""
    __slots__ = ('id',)

    def __init__(self, id):
        self.id = id


def _s():
    return db.db_session


def _person_id(name):
    """Find or create the named person. Identity is the row; the name is only how we found
    it, which is why an import has to map explicitly rather than match."""
    if not name:
        return None
    s = _s()
    hit = s.query(Person).filter_by(display_name=name).all()
    if len(hit) == 1:
        return hit[0].id
    p = Person(display_name=name)
    s.add(p)
    s.flush()
    return p.id


def _save(e, ref=None):
    """Append every event not yet persisted. Append-only, as a real event store would be."""
    s = _s()
    fresh = ref is None
    if ref is None:
        row = HealthcareExpense(incurred_on=e.incurred_on or '')
        s.add(row)
        s.flush()
        ref = Ref(row.id)
        pid = _person_id(e.person)
        if pid is not None:
            s.add(PersonAssignment(expense_id=row.id, person_id=pid, mode='initial', seq=1))
    # The append point is an identity set, not a count.
    #
    # Counting rows assumed every persisted event reads back as exactly one event, and that
    # stopped being true the moment plan periods became household-level: a plan change writes
    # one shared row and reads back for every expense, so the counts drift and the cursor
    # re-persists from the wrong place. Identifying what is already there survives that,
    # which a count cannot.
    already = {(v.kind, v.recorded_seq) for v in _load(ref).events} if not fresh else set()

    for ev in e.events:
        if (ev.kind, ev.recorded_seq) in already:
            continue
        p = ev.payload
        common = dict(expense_id=ref.id, effective_seq=ev.effective_seq,
                      recorded_seq=ev.recorded_seq)
        if ev.kind == 'expense_created':
            s.add(ExpenseObligationVersion(amount=float(p.get('amount') or 0.0), **common))
        elif ev.kind == 'expense_corrected':
            s.add(ExpenseObligationVersion(amount=float(p['to']), **common))
        elif ev.kind == 'allocated':
            s.add(ExpenseFundingAllocation(
                funder=p['funder'],
                amount=(0.0 if JSON_AMOUNTS else float(p['amount'])), mode='allocated',
                source=p.get('source', 'manual'), cleared=int(bool(p.get('cleared', True))),
                attached=int(bool(p.get('attached', True))),
                user_confirmed=int(bool(p.get('user_confirmed', True))), **common))
        elif ev.kind == 'allocation_corrected':
            s.add(ExpenseFundingAllocation(funder=p['funder'], amount=float(p['to']),
                                           mode='corrected', **common))
        elif ev.kind == 'allocation_reversed':
            s.add(ExpenseFundingAllocation(funder=p['funder'], amount=0.0, mode='reversed',
                                           occurred_on=p.get('occurred_on'), **common))
        elif ev.kind == 'allocation_reinstated':
            s.add(ExpenseFundingAllocation(funder=p['funder'], amount=0.0,
                                           mode='reinstated',
                                           occurred_on=p.get('occurred_on'), **common))
        elif ev.kind == 'obligation_refunded':
            # A refund gets its own table rather than another obligation version: it is an
            # event ON the obligation, not a restatement of it, and it names a recipient.
            s.add(ExpenseRefund(amount=float(p.get('amount') or 0.0),
                                to_funder=p.get('to'),
                                occurred_on=p.get('occurred_on'), **common))
        elif ev.kind == 'allocation_deleted':
            s.add(ExpenseFundingAllocation(funder=p['funder'], amount=0.0,
                                           mode=p.get('mode', 'correction'), **common))
        elif ev.kind == 'eob_imported':
            s.add(ExpenseFundingAllocation(
                funder=p.get('funder') or '', amount=float(p.get('amount') or 0.0),
                mode='eob_import', source='imported',
                duplicate_of=p.get('duplicate_of'), **common))
        elif ev.kind == 'rules_changed':
            s.add(TaxRuleVersion(version=p['to'], effective_seq=ev.effective_seq,
                                 recorded_seq=ev.recorded_seq))
        elif ev.kind == 'year_rolled':
            # Deliberately not recorded anywhere. A year roll carries no fact and no
            # relationship - the expense stays in the year it was incurred, on the plan in
            # force then - so there is nothing about it that integrity depends on. Skipping
            # the historian row too keeps the read path's event set exactly the write path's.
            continue
        elif ev.kind == 'determination_recorded':
            s.add(ExpenseDetermination(
                status=p['status'], amount=float(p.get('amount') or 0.0),
                evidence=p.get('evidence'), **common))
        else:
            raise AssertionError('no typed home for event kind %r' % ev.kind)

        # The event, in the historian, pointing at the expense through a real foreign key.
        # context_json carries explanation only; nothing below reads it back.
        s.add(Historian(
            event_category='healthcare_%s' % ev.kind,
            healthcare_expense_id=(None if JSON_RELATIONSHIP else ref.id),
            context_json=(json.dumps({'kind': ev.kind, 'payload': p,
                                      'expense_id': ref.id, 'seq': ev.recorded_seq})
                          if WRITE_JSON else None)))

    s.commit()
    return ref


def _load(ref):
    """Rebuild the expense from TYPED COLUMNS ONLY. No `context_json` is read here, which is
    what the wipe test proves rather than asserts."""
    s = _s()
    row = s.get(HealthcareExpense, ref.id)
    assign = (s.query(PersonAssignment).filter_by(expense_id=ref.id)
              .order_by(PersonAssignment.seq).all())
    who = (s.get(Person, assign[-1].person_id).display_name if assign else None)
    e = alloc.Expense(incurred_on=row.incurred_on, person=who)
    events = []

    for r in s.query(ExpenseObligationVersion).filter_by(expense_id=ref.id).all():
        kind = 'expense_created' if r.recorded_seq == 1 else 'expense_corrected'
        payload = ({'amount': r.amount, 'incurred_on': row.incurred_on}
                   if kind == 'expense_created' else {'to': r.amount})
        events.append(alloc.Event(kind, payload, r.effective_seq, r.recorded_seq))

    for r in s.query(ExpenseFundingAllocation).filter_by(expense_id=ref.id).all():
        if r.mode == 'allocated':
            amount = (_amount_from_json(ref.id, r.recorded_seq) if JSON_AMOUNTS
                      else r.amount)
            events.append(alloc.Event('allocated', {
                'funder': r.funder, 'amount': amount, 'source': r.source,
                'cleared': bool(r.cleared), 'attached': bool(r.attached),
                'user_confirmed': bool(r.user_confirmed)}, r.effective_seq, r.recorded_seq))
        elif r.mode == 'corrected':
            events.append(alloc.Event('allocation_corrected', {'funder': r.funder,
                                                               'to': r.amount},
                                      r.effective_seq, r.recorded_seq))
        elif r.mode == 'reversed':
            events.append(alloc.Event('allocation_reversed',
                                      {'funder': r.funder, 'occurred_on': r.occurred_on},
                                      r.effective_seq, r.recorded_seq))
        elif r.mode == 'reinstated':
            events.append(alloc.Event('allocation_reinstated',
                                      {'funder': r.funder, 'occurred_on': r.occurred_on},
                                      r.effective_seq, r.recorded_seq))
        elif r.mode == 'eob_import':
            events.append(alloc.Event('eob_imported', {'funder': r.funder or None,
                                                       'amount': r.amount,
                                                       'duplicate_of': r.duplicate_of},
                                      r.effective_seq, r.recorded_seq))
        else:
            events.append(alloc.Event('allocation_deleted', {'funder': r.funder,
                                                             'mode': r.mode},
                                      r.effective_seq, r.recorded_seq))

    for r in s.query(ExpenseRefund).filter_by(expense_id=ref.id).all():
        events.append(alloc.Event('obligation_refunded',
                                  {'amount': r.amount, 'to': r.to_funder,
                                   'occurred_on': r.occurred_on},
                                  r.effective_seq, r.recorded_seq))

    for r in s.query(TaxRuleVersion).all():
        events.append(alloc.Event('rules_changed', {'to': r.version},
                                  r.effective_seq, r.recorded_seq))
    for r in s.query(ExpenseDetermination).filter_by(expense_id=ref.id).all():
        events.append(alloc.Event('determination_recorded',
                                  {'status': r.status, 'amount': r.amount,
                                   'evidence': r.evidence},
                                  r.effective_seq, r.recorded_seq))

    e.events = events
    e._seq = max([v.recorded_seq for v in events] or [0])
    e._effective = max([v.effective_seq for v in events] or [0.0])

    links = s.query(ExpenseMergeLink).filter_by(merged_into_id=ref.id).all()
    e.merged_from = [_load(Ref(l.merged_from_id)) for l in links]

    own = (_rows_by_json(ref.id) if JSON_RELATIONSHIP
           else s.query(Historian).filter_by(healthcare_expense_id=ref.id).all())
    e.provenance = [{'kind': h.event_category, 'at': h.created_at} for h in own]
    for m in e.merged_from:
        e.provenance.extend(m.provenance)
    return e


def _amount_from_json(expense_id, recorded_seq):
    """A read path that must parse JSON to recover a value an invariant depends on. Exactly
    what the criterion forbids, present only so phase 3 can demonstrate it being caught."""
    for h in _s().query(Historian).all():
        if not h.context_json:
            continue
        d = json.loads(h.context_json)
        if d.get('expense_id') == expense_id and d.get('seq') == recorded_seq:
            return float(d['payload'].get('amount') or 0.0)
    return 0.0


def _rows_by_json(expense_id):
    """The same forbidden shape, for a relationship rather than a value."""
    out = []
    for h in _s().query(Historian).all():
        if h.context_json and json.loads(h.context_json).get('expense_id') == expense_id:
            out.append(h)
    return out


class Store:
    """The fixture's model, backed entirely by the database."""
    UNRESOLVED = alloc.UNRESOLVED

    def new_expense(self, **kw):
        return _save(alloc.new_expense(**kw), None)

    def allocate(self, ref, **kw):
        e = _load(ref)
        alloc.allocate(e, **kw)
        return _save(e, ref)

    def apply(self, ref, op, effective_seq=None):
        e = _load(ref)
        alloc.apply(e, op, effective_seq)
        return _save(e, ref)

    def branch(self, ref):
        e = _load(ref)
        return _save(alloc.branch(e), None)

    def state(self, ref, plan=alloc.UNRESOLVED):
        # The plan is resolved by whoever holds the household record, not reconstructed from
        # the expense - so it passes straight through.
        return alloc.state(_load(ref), plan)

    def unallocated(self, ref):
        return alloc.unallocated(_load(ref))

    def qualifying(self, ref, rules=None):
        return alloc.qualifying(_load(ref), rules=rules)

    def determinations(self, ref):
        return alloc.determinations(_load(ref))

    def explain(self, figure):
        return alloc.explain(figure)

    def changes(self, ref):
        return alloc.changes(_load(ref))

    def explain_change(self, ref):
        return alloc.explain_change(_load(ref))

    def confirms_on(self):
        return alloc.confirms_on()

    def payment(self, ref, **kw):
        return alloc.payment(None, **kw)

    def is_confirmed(self, p):
        return alloc.is_confirmed(p)

    def deletion_modes(self):
        return alloc.deletion_modes()

    def merge(self, a, b):
        s = _s()
        merged = _save(alloc.branch(_load(a)), None)
        s.add(ExpenseMergeLink(merged_into_id=merged.id, merged_from_id=a.id))
        s.add(ExpenseMergeLink(merged_into_id=merged.id, merged_from_id=b.id))
        s.commit()
        return merged

    def can_unmerge(self, ref):
        return len(_load(ref).merged_from) >= 2

    def provenance(self, ref):
        return _load(ref).provenance

    def replay(self, expense_kw, allocations, mutations, order=0):
        ref = self.new_expense(**expense_kw)
        for i, a in enumerate(allocations):
            self.allocate(ref, effective_seq=0.1 * (i + 1), **a)
        indexed = list(enumerate(mutations))
        n = len(indexed) or 1
        for i, (_name, op, _exp) in indexed[order % n:] + indexed[:order % n]:
            self.apply(ref, op, effective_seq=float(i + 1))
        return {'state': self.state(ref),
                'qualifying_v2026_1': alloc.explain(self.qualifying(ref, rules='v2026.1'))}


# ── Person, round-tripped ───────────────────────────────────────────────────
# Write-through, hydrate-on-read: every mutating call goes to the module and is then synced
# to the tables; every read rebuilds the registry FROM the tables first. So a field the
# schema cannot carry shows up as a wrong answer rather than as a silent absence.
#
# Hydration reuses the objects already in the registry by id and overwrites their fields
# from the row. Identity is preserved - the fixtures hold `rob` and compare with `is` - while
# every value still has to survive the round trip to be read back correctly.

def _keyed(rows, key):
    return {key(r): r for r in rows}


def _expense_row(expense_key):
    """Person assignments point at a real expense, so the fixture's string keys need rows."""
    s = _s()
    hit = s.query(HealthcareExpense).filter_by(incurred_on='key:%s' % expense_key).first()
    if hit is None:
        hit = HealthcareExpense(incurred_on='key:%s' % expense_key)
        s.add(hit)
        s.flush()
    return hit


def _sync_person():
    s = _s()
    reg = personmod._r()
    have = _keyed(s.query(Person).all(), lambda r: r.id)
    for p in reg.people:
        row = have.get(p.id)
        if row is None:
            s.add(Person(id=p.id, display_name=p.display_name, active=p.active))
        else:
            row.display_name, row.active = p.display_name, p.active

    have_alias = {(r.person_id, r.alias) for r in s.query(PersonAlias).all()}
    for a in reg.aliases:
        if (a.person_id, a.alias) not in have_alias:
            s.add(PersonAlias(person_id=a.person_id, alias=a.alias, source=a.source))

    have_assign = {(r.expense_id, r.seq) for r in s.query(PersonAssignment).all()}
    for a in reg.assignments:
        eid = _expense_row(a.expense_key).id
        if (eid, a.seq) not in have_assign:
            s.add(PersonAssignment(expense_id=eid, person_id=a.person_id, mode=a.mode,
                                   seq=a.seq, reason=a.reason, source=a.source))

    have_enrol = {(r.person_id, r.plan_id, r.effective_on)
                  for r in s.query(PersonEnrolment).all()}
    for e in reg.enrolments:
        plan = _plan_row(e.plan, e.effective_on)
        if (e.person_id, plan.id, e.effective_on) not in have_enrol:
            s.add(PersonEnrolment(person_id=e.person_id, plan_id=plan.id,
                                  effective_on=e.effective_on))
    s.commit()


def _plan_row(name, effective_on=None):
    """Enrolment points at a plan period, not a plan name. Find or create - a coverage
    period is a household fact, so two people on Plan A share one row."""
    s = _s()
    hit = s.query(HealthPlan).filter_by(name=name).first()
    if hit is None:
        hit = HealthPlan(name=name, effective_from=effective_on or '',
                         effective_to='9999-12-31', seq=0)
        s.add(hit)
        s.flush()
    return hit


def _hydrate_person():
    s = _s()
    reg = personmod._r()
    known = {p.id: p for p in reg.people}
    people = []
    for row in s.query(Person).order_by(Person.id).all():
        p = known.get(row.id)
        if p is None:
            p = personmod.Person(id=row.id, display_name=row.display_name,
                                 active=bool(row.active))
        else:
            p.display_name, p.active = row.display_name, bool(row.active)
        people.append(p)
    reg.people = people

    reg.aliases = [personmod.Alias(person_id=r.person_id, alias=r.alias, source=r.source)
                   for r in s.query(PersonAlias).all()]

    keys = {r.id: r.incurred_on for r in s.query(HealthcareExpense).all()}
    reg.assignments = [
        personmod.PersonAssignment(
            expense_key=(keys.get(r.expense_id) or '').replace('key:', ''),
            person_id=r.person_id, mode=r.mode, seq=r.seq, reason=r.reason,
            source=r.source, recorded_at=r.recorded_at)
        for r in s.query(PersonAssignment).order_by(PersonAssignment.seq).all()]

    plans = {r.id: r.name for r in s.query(HealthPlan).all()}
    reg.enrolments = [personmod.Enrolment(person_id=r.person_id,
                                          plan=plans.get(r.plan_id),
                                          effective_on=r.effective_on)
                      for r in s.query(PersonEnrolment).all()]


class PersonStore:
    """core/person.py, backed entirely by the shipped tables."""
    _READS = ('id_of', 'display_name', 'people', 'is_active', 'has_history', 'resolve_name',
              'alias_source', 'assignments', 'person_of', 'per_person_total',
              'household_total', 'unassigned_total', 'enrolments', 'enrolment_at',
              'deletion_modes', 'now')
    _WRITES = ('add_person', 'rename', 'deactivate', 'delete', 'map_alias', 'assign',
               'reassign', 'enrol')

    def reset(self):
        personmod.reset()
        _clear()

    def __getattr__(self, name):
        fn = getattr(personmod, name)
        if name in self._READS:
            def read(*a, **kw):
                _hydrate_person()
                return fn(*a, **kw)
            return read
        if name in self._WRITES:
            def write(*a, **kw):
                out = fn(*a, **kw)
                if name == 'delete' and out:
                    _sync_delete_person(a[0])
                else:
                    _sync_person()
                return out
            return write
        return fn


def _sync_delete_person(person):
    s = _s()
    s.query(PersonAlias).filter_by(person_id=person.id).delete()
    s.query(Person).filter_by(id=person.id).delete()
    s.commit()


# ── Plan years, round-tripped ───────────────────────────────────────────────

def _sync_plans():
    s = _s()
    reg = planmod._r()
    have = _keyed(s.query(HealthPlan).all(), lambda r: r.id)
    for p in reg.plans:
        if p.id not in have:
            s.add(HealthPlan(id=p.id, name=p.name, effective_from=p.effective_from,
                             effective_to=p.effective_to, seq=p.seq))

    have_terms = {(r.plan_id, r.seq) for r in s.query(HealthPlanTermVersion).all()}
    for t in reg.terms:
        if (t.plan_id, t.seq) not in have_terms:
            prev = t.previous or {}
            s.add(HealthPlanTermVersion(
                plan_id=t.plan_id, deductible=t.terms.get('deductible'),
                oop_max=t.terms.get('oop_max'),
                previous_deductible=prev.get('deductible'),
                previous_oop_max=prev.get('oop_max'),
                reason=t.reason, source=t.source, seq=t.seq))

    have_ops = {(r.plan_id, r.seq) for r in s.query(HealthPlanOperation).all()}
    for o in reg.ops:
        if (o.plan_id, o.seq) not in have_ops:
            s.add(HealthPlanOperation(plan_id=o.plan_id, kind=o.kind, seq=o.seq))
    s.commit()


def _hydrate_plans():
    s = _s()
    reg = planmod._r()
    known = {p.id: p for p in reg.plans}
    plans = []
    for row in s.query(HealthPlan).order_by(HealthPlan.id).all():
        p = known.get(row.id)
        if p is None:
            p = planmod.Plan(id=row.id, name=row.name, effective_from=row.effective_from,
                             effective_to=row.effective_to, seq=row.seq)
        else:
            p.name, p.effective_from = row.name, row.effective_from
            p.effective_to, p.seq = row.effective_to, row.seq
        plans.append(p)
    reg.plans = plans

    reg.terms = []
    for r in s.query(HealthPlanTermVersion).order_by(HealthPlanTermVersion.seq).all():
        prev = None
        if r.previous_deductible is not None or r.previous_oop_max is not None:
            prev = {'deductible': r.previous_deductible, 'oop_max': r.previous_oop_max}
        reg.terms.append(planmod.TermVersion(
            plan_id=r.plan_id,
            terms={'deductible': r.deductible, 'oop_max': r.oop_max},
            previous=prev, reason=r.reason, source=r.source, seq=r.seq,
            recorded_at=r.recorded_at))

    reg.ops = [planmod.Operation(kind=r.kind, plan_id=r.plan_id, seq=r.seq,
                                 recorded_at=r.recorded_at)
               for r in s.query(HealthPlanOperation).order_by(HealthPlanOperation.seq).all()]


class PlanYearStore:
    """core/plan_year.py, backed entirely by the shipped tables."""
    UNKNOWN = planmod.UNKNOWN
    _READS = ('plan_at', 'plan_of', 'plans', 'terms_at', 'term_history', 'operations',
              'accumulators', 'year_summary', 'deletion_modes', 'now')
    _WRITES = ('add_plan', 'correct_terms')

    def reset(self):
        planmod.reset()
        _clear()

    def delete_plan(self, plan, expenses=None):
        _hydrate_plans()
        out = planmod.delete_plan(plan, expenses)
        if out:
            s = _s()
            for model in (HealthPlanOperation, HealthPlanTermVersion):
                s.query(model).filter_by(plan_id=plan.id).delete()
            s.query(HealthPlan).filter_by(id=plan.id).delete()
            s.commit()
        return out

    def __getattr__(self, name):
        fn = getattr(planmod, name)
        if name in self._READS:
            def read(*a, **kw):
                _hydrate_plans()
                return fn(*a, **kw)
            return read
        if name in self._WRITES:
            def write(*a, **kw):
                out = fn(*a, **kw)
                _sync_plans()
                return out
            return write
        return fn


def _load_fixture(name='test_lifecycle_fixture'):
    spec = importlib.util.spec_from_file_location(
        'fixture_' + name, ROOT / 'tests' / ('%s.py' % name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _clear():
    """Empty the healthcare tables between phases.

    Not only for speed. Household-level rows - plan periods, people, rule versions - are
    shared by construction, so a phase inheriting them from the phase before is not testing
    what it says it is: it would be reading plans nobody in that run created.
    """
    s = _s()
    for model in (ExpenseMergeLink, PersonAssignment, ExpenseDetermination,
                  ExpenseRefund, ExpenseFundingAllocation, ExpenseObligationVersion,
                  HealthcareExpense,
                  HealthPlanOperation, HealthPlanTermVersion, HealthPlan,
                  PersonEnrolment, PersonAlias, Person, TaxRuleVersion):
        s.query(model).delete()
    s.query(Historian).filter(Historian.event_category.like('healthcare_%')).delete(
        synchronize_session=False)
    s.commit()


def _run(fx, model):
    """Run the fixture silently. Its own output is suppressed so the phases below read as
    phases - phase 3 deliberately breaks things, and its failures are the point rather than a
    problem."""
    _clear()
    fx.PASS[:] = []
    fx.FAIL[:] = []
    fx.PENDING[:] = []
    err = None
    try:
        with contextlib.redirect_stdout(_io.StringIO()):
            fx.run(model)
    except Exception as e:                                    # noqa: BLE001
        err = '%s: %s' % (type(e).__name__, e)
    return len(fx.PASS), list(fx.FAIL), err


def main():
    global WRITE_JSON, JSON_RELATIONSHIP, JSON_AMOUNTS

    print(__doc__.strip().splitlines()[0])
    print('=' * 74)
    db.Base.metadata.create_all(db.engine)

    # The shipped historian carries the one foreign key this needs, and it is a real key
    # rather than a value in a blob.
    cols = db.HistorianEntry.__table__.columns
    fk = cols['healthcare_expense_id']
    check('the shipped historian carries a real foreign key to a healthcare expense',
          bool(fk.foreign_keys) and fk.nullable)

    fx = _load_fixture()

    # ── Phase 1: every operation round-trips through the schema ─────────────
    passed, failures, err = _run(fx, Store())
    check('the fixture passes when every operation round-trips through the schema',
          not failures and not err and passed > 0)
    if err:
        print('        raised: %s' % err)
    for f in failures[:6]:
        print('        failing: %s' % f)

    # ── The criterion, part 1: the manifest ─────────────────────────────────
    in_json = [r for r in RELATIONSHIPS if r[1] == 'context_json']
    print()
    print('  Structural relationships, and where each lives:')
    for name, home, where in RELATIONSHIPS:
        print('    %-32s %-11s %s' % (name, home, where))
    check('no more than two structural relationships live in context_json (%d do)'
          % len(in_json), len(in_json) <= 2)

    # ── The criterion, part 2: run with the column permanently NULL ─────────
    WRITE_JSON = False
    try:
        passed2, failures2, err2 = _run(fx, Store())
    finally:
        WRITE_JSON = True
    # Counted after the phase, against a table the phase started empty. Nothing it wrote
    # carries JSON, which is the claim - and it is a stronger one than "we deleted the JSON
    # afterwards", because a wiped column leaves the next run free to write fresh JSON and
    # depend on it.
    wrote_json = _s().query(Historian).filter(
        Historian.event_category.like('healthcare_%'),
        Historian.context_json.isnot(None)).count()
    total_rows = _s().query(Historian).filter(
        Historian.event_category.like('healthcare_%')).count()

    check('the second phase wrote rows but none of them carry context_json (%d of %d)'
          % (wrote_json, total_rows), total_rows > 0 and wrote_json == 0)
    check('no read path needed context_json to enforce an invariant',
          not failures2 and not err2 and passed2 == passed)
    if err2:
        print('        raised: %s' % err2)
    for f in failures2[:6]:
        print('        failing: %s' % f)

    # ── The criterion has to be able to fail ────────────────────────────────
    # A green experiment that could not have gone red measures nothing. Both breakages are
    # exactly the shapes the criterion names.
    print()
    print('  Proving the criterion can fail:')

    WRITE_JSON = False
    JSON_RELATIONSHIP = True
    try:
        _, broken_rel, err_rel = _run(fx, Store())
    finally:
        JSON_RELATIONSHIP = False
        WRITE_JSON = True
    check('caught: the event -> expense relationship moved into context_json',
          bool(broken_rel) or bool(err_rel))

    WRITE_JSON = False
    JSON_AMOUNTS = True
    try:
        _, broken_amt, err_amt = _run(fx, Store())
    finally:
        JSON_AMOUNTS = False
        WRITE_JSON = True
    check('caught: an allocation amount moved into context_json',
          bool(broken_amt) or bool(err_amt))

    restored, restored_failures, _ = _run(fx, Store())
    check('the experiment is left exactly as it was found',
          restored == passed and not restored_failures)

    # ── The gap this leaves, now closed: person and plan-year round-trips ───
    # `health_plans`, its term versions and the person tables were persisted by nothing once
    # allocation stopped owning plans. Their own fixtures now drive them through the shipped
    # schema, which is the same question asked of the same tables: can the shape carry it,
    # and does any read need JSON?
    for label, fixture_name, store in (
            ('person identity', 'test_person_identity_fixture', PersonStore()),
            ('plan years', 'test_plan_year_fixture', PlanYearStore())):
        fx2 = _load_fixture(fixture_name)
        p2, f2, e2 = _run(fx2, store)
        check('%s round-trips through the shipped schema' % label,
              not f2 and not e2 and p2 > 0)
        if e2:
            print('        raised: %s' % e2)
        for f in f2[:6]:
            print('        failing: %s' % f)

        WRITE_JSON = False
        try:
            p3, f3, e3 = _run(fx2, store)
        finally:
            WRITE_JSON = True
        check('%s needs no context_json either' % label,
              not f3 and not e3 and p3 == p2)
        if e3:
            print('        raised: %s' % e3)

    # And these round-trips have to be able to fail too. A store that quietly answered from
    # the in-memory registry would pass every check above while persisting nothing, so each
    # one is broken at a single column and required to notice.
    print()
    print('  Proving the new round-trips can fail:')

    orig_sync = globals()['_sync_person']

    def person_loses_source():
        reg = personmod._r()
        for a in reg.assignments:
            a.source = None
        return orig_sync()

    globals()['_sync_person'] = person_loses_source
    try:
        fx_p = _load_fixture('test_person_identity_fixture')
        _, broke_p, err_p = _run(fx_p, PersonStore())
    finally:
        globals()['_sync_person'] = orig_sync
    check('caught: a reassignment persists without its source',
          bool(broke_p) or bool(err_p))

    orig_plan_sync = globals()['_sync_plans']

    def plans_lose_previous():
        s2 = _s()
        out = orig_plan_sync()
        for r in s2.query(HealthPlanTermVersion).all():
            r.previous_deductible = None
            r.previous_oop_max = None
        s2.commit()
        return out

    globals()['_sync_plans'] = plans_lose_previous
    try:
        fx_y = _load_fixture('test_plan_year_fixture')
        _, broke_y, err_y = _run(fx_y, PlanYearStore())
    finally:
        globals()['_sync_plans'] = orig_plan_sync
    check('caught: a terms correction persists without what it corrected',
          bool(broke_y) or bool(err_y))

    print()
    verdict = not FAIL
    print('%d passed, %d failed' % (len(PASS), len(FAIL)))
    print()
    if verdict:
        print('CRITERION MET, against the SHIPPED schema. The fixture round-trips with 0')
        print('structural relationships in context_json, and passes in full with the column')
        print('never written.')
    else:
        print('CRITERION NOT MET. A typed event store is warranted; see the failures above.')
    return 0 if verdict else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    finally:
        try:
            db.db_session.remove()
            db.engine.dispose()
            shutil.rmtree(_TMP, ignore_errors=True)
        except Exception:                                     # noqa: BLE001
            pass
