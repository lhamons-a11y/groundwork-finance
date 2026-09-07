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


def _plan(name, effective_from, seq):
    """Find or create the household plan period. A plan is not a property of a charge, so
    two expenses under Plan A share one row rather than each carrying a copy."""
    s = _s()
    hit = s.query(HealthPlan).filter_by(name=name).first()
    if hit is not None:
        return hit
    row = HealthPlan(name=name, effective_from=effective_from or '',
                     effective_to='9999-12-31', seq=seq)
    s.add(row)
    s.flush()
    return row


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
            if p.get('plan'):
                _plan(p['plan'], p.get('incurred_on'), ev.recorded_seq)
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
            s.add(ExpenseFundingAllocation(funder=p['funder'], amount=0.0,
                                           mode='reversed', **common))
        elif ev.kind == 'allocation_deleted':
            s.add(ExpenseFundingAllocation(funder=p['funder'], amount=0.0,
                                           mode=p.get('mode', 'correction'), **common))
        elif ev.kind == 'eob_imported':
            s.add(ExpenseFundingAllocation(
                funder=p.get('funder') or '', amount=float(p.get('amount') or 0.0),
                mode='eob_import', source='imported',
                duplicate_of=p.get('duplicate_of'), **common))
        elif ev.kind == 'plan_changed':
            _plan(p['to'], p.get('effective'), ev.recorded_seq)
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
            events.append(alloc.Event('allocation_reversed', {'funder': r.funder},
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

    # Plan periods are household-level, so they are read for every expense rather than by
    # expense id. That is the whole point of landing them that way: ONE source of truth for
    # which plan covered a date, instead of a copy hanging off every charge that can drift
    # from it. The expense's plan is then derived - the period covering `incurred_on`.
    for r in s.query(HealthPlan).order_by(HealthPlan.seq).all():
        events.append(alloc.Event('plan_changed',
                                  {'to': r.name, 'effective': r.effective_from},
                                  float(r.seq), r.seq))

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

    def state(self, ref):
        return alloc.state(_load(ref))

    def unallocated(self, ref):
        return alloc.unallocated(_load(ref))

    def qualifying(self, ref, rules=None):
        return alloc.qualifying(_load(ref), rules=rules)

    def determinations(self, ref):
        return alloc.determinations(_load(ref))

    def explain(self, figure):
        return alloc.explain(figure)

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


def _load_fixture():
    spec = importlib.util.spec_from_file_location(
        'fixture', ROOT / 'tests' / 'test_lifecycle_fixture.py')
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
                  ExpenseFundingAllocation, ExpenseObligationVersion, HealthcareExpense,
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
