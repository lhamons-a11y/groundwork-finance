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

**What is deliberately NOT done here.** Nothing is added to `core/database.py`. The candidate
tables live in this file, and the historian mirror carries one extra column
(`healthcare_expense_id`) over the shipped table — asserted against the real schema below, so
this experiment cannot quietly drift from the table it claims to be testing. Shipping it is
one migration adding one nullable foreign key, plus the new tables.

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
    ('plan change -> expense',        'fk',         'expense_plan_changes.expense_id'),
    ('rules change -> expense',       'fk',         'expense_rule_changes.expense_id'),
    ('merged expense -> its sources', 'link_table', 'expense_merge_links'),
]


# ── The candidate schema ────────────────────────────────────────────────────
# Structure in tables with real foreign keys; events in the historian. The split the codebase
# already makes in `create_debt_ledger_entry`, seven lines apart, pointed at a new object.

class HealthcareExpense(db.Base):
    """Identity only. Everything that can change is versioned in its own table, because a
    mutable amount column cannot answer what the figure was in March."""
    __tablename__ = 'healthcare_expenses'
    id          = Column(Integer, primary_key=True)
    incurred_on = Column(String(10), nullable=False)
    person      = Column(String(80), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    # Bookkeeping for this experiment's append-only save path.
    persisted_events = Column(Integer, default=0)


class ExpenseObligationVersion(db.Base):
    """What the provider claims, and what it claimed before. Append-only."""
    __tablename__ = 'expense_obligation_versions'
    id            = Column(Integer, primary_key=True)
    expense_id    = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    amount        = Column(Float, nullable=False)
    effective_seq = Column(Float, nullable=False)
    recorded_seq  = Column(Integer, nullable=False)
    supersedes_id = Column(Integer, ForeignKey('expense_obligation_versions.id'))
    recorded_at   = Column(DateTime, default=datetime.utcnow)


class ExpenseFundingAllocation(db.Base):
    """Money that moved, by funder, as a version chain rather than a mutable row.

    A correction does not overwrite: it writes a new row pointing at the one it supersedes,
    which is what keeps 'superseded, never overwritten' true in the database and not only in
    the model.
    """
    __tablename__ = 'expense_funding_allocations'
    id             = Column(Integer, primary_key=True)
    expense_id     = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    funder         = Column(String(40), nullable=False)
    amount         = Column(Float, nullable=False)
    mode           = Column(String(24), nullable=False)   # allocated|corrected|reversed|deleted|eob_import
    source         = Column(String(24), default='manual')
    cleared        = Column(Integer, default=1)
    attached       = Column(Integer, default=1)
    user_confirmed = Column(Integer, default=1)
    duplicate_of   = Column(String(40), nullable=True)
    effective_seq  = Column(Float, nullable=False)
    recorded_seq   = Column(Integer, nullable=False)
    supersedes_id  = Column(Integer, ForeignKey('expense_funding_allocations.id'))
    recorded_at    = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index('ix_efa_expense', 'expense_id'),)


class ExpenseDetermination(db.Base):
    """What was concluded about an unresolved amount. Superseded, never overwritten."""
    __tablename__ = 'expense_determinations'
    id            = Column(Integer, primary_key=True)
    expense_id    = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    status        = Column(String(32), nullable=False)
    amount        = Column(Float, nullable=False)
    evidence      = Column(String(80), nullable=True)
    rule_version  = Column(String(24), nullable=True)
    effective_seq = Column(Float, nullable=False)
    recorded_seq  = Column(Integer, nullable=False)
    supersedes_id = Column(Integer, ForeignKey('expense_determinations.id'))
    recorded_at   = Column(DateTime, default=datetime.utcnow)


class ExpensePlanChange(db.Base):
    __tablename__ = 'expense_plan_changes'
    id            = Column(Integer, primary_key=True)
    expense_id    = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    plan          = Column(String(40), nullable=False)
    effective_on  = Column(String(10), nullable=True)
    effective_seq = Column(Float, nullable=False)
    recorded_seq  = Column(Integer, nullable=False)


class ExpenseRuleChange(db.Base):
    """A typed home for the rule version in force. Without it this would be the one thing
    living only in JSON, and a rule version is not explanatory context — it decides whether a
    historical figure can be reproduced."""
    __tablename__ = 'expense_rule_changes'
    id            = Column(Integer, primary_key=True)
    expense_id    = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    rules_version = Column(String(24), nullable=False)
    effective_seq = Column(Float, nullable=False)
    recorded_seq  = Column(Integer, nullable=False)


class ExpenseYearRoll(db.Base):
    __tablename__ = 'expense_year_rolls'
    id            = Column(Integer, primary_key=True)
    expense_id    = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    rolled_to     = Column(Integer, nullable=False)
    effective_seq = Column(Float, nullable=False)
    recorded_seq  = Column(Integer, nullable=False)


class ExpenseMergeLink(db.Base):
    """Two records found to be one. A single FK column cannot hold two sources, which is
    exactly what a link table is for."""
    __tablename__ = 'expense_merge_links'
    id             = Column(Integer, primary_key=True)
    merged_into_id = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    merged_from_id = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)


class HistorianEntryX(db.Base):
    """The shipped historian plus ONE nullable foreign key.

    Per-entity keys, following the convention `debt_account_id` and `category_id` already
    set. The column set is asserted against the real table below, so this cannot drift from
    what it claims to be testing.
    """
    __tablename__ = 'historian_entries_experimental'
    id              = Column(Integer, primary_key=True)
    event_category  = Column(String(40), nullable=False)
    debt_account_id = Column(Integer, nullable=True)
    category_id     = Column(Integer, nullable=True)
    expected_value  = Column(Float, nullable=True)
    actual_value    = Column(Float, nullable=True)
    variance_pct    = Column(Float, nullable=True)
    variance_amount = Column(Float, nullable=True)
    context_json    = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    # The one addition.
    healthcare_expense_id = Column(Integer, ForeignKey('healthcare_expenses.id'),
                                   nullable=True)


# ── Persisting and rehydrating ──────────────────────────────────────────────

class Ref:
    """What the fixture passes around. Nothing but a database id — deliberately, so no state
    can survive in memory and flatter the round trip."""
    __slots__ = ('id',)

    def __init__(self, id):
        self.id = id


def _s():
    return db.db_session


def _save(e, ref=None):
    """Append every event not yet persisted. Append-only, as a real event store would be."""
    s = _s()
    if ref is None:
        row = HealthcareExpense(incurred_on=e.incurred_on or '', person=e.person,
                                persisted_events=0)
        s.add(row)
        s.flush()
        ref = Ref(row.id)
    row = s.get(HealthcareExpense, ref.id)
    start = row.persisted_events or 0

    for ev in e.events[start:]:
        p = ev.payload
        common = dict(expense_id=ref.id, effective_seq=ev.effective_seq,
                      recorded_seq=ev.recorded_seq)
        if ev.kind == 'expense_created':
            s.add(ExpenseObligationVersion(amount=float(p.get('amount') or 0.0), **common))
            if p.get('plan'):
                s.add(ExpensePlanChange(plan=p['plan'], effective_on=p.get('incurred_on'),
                                        **common))
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
            s.add(ExpensePlanChange(plan=p['to'], effective_on=p.get('effective'), **common))
        elif ev.kind == 'rules_changed':
            s.add(ExpenseRuleChange(rules_version=p['to'], **common))
        elif ev.kind == 'year_rolled':
            s.add(ExpenseYearRoll(rolled_to=int(p['to']), **common))
        elif ev.kind == 'determination_recorded':
            s.add(ExpenseDetermination(
                status=p['status'], amount=float(p.get('amount') or 0.0),
                evidence=p.get('evidence'), **common))
        else:
            raise AssertionError('no typed home for event kind %r' % ev.kind)

        # The event, in the historian, pointing at the expense through a real foreign key.
        # context_json carries explanation only; nothing below reads it back.
        s.add(HistorianEntryX(
            event_category='healthcare_%s' % ev.kind,
            healthcare_expense_id=(None if JSON_RELATIONSHIP else ref.id),
            context_json=(json.dumps({'kind': ev.kind, 'payload': p,
                                      'expense_id': ref.id, 'seq': ev.recorded_seq})
                          if WRITE_JSON else None)))

    row.persisted_events = len(e.events)
    s.commit()
    return ref


def _load(ref):
    """Rebuild the expense from TYPED COLUMNS ONLY. No `context_json` is read here, which is
    what the wipe test proves rather than asserts."""
    s = _s()
    row = s.get(HealthcareExpense, ref.id)
    e = alloc.Expense(incurred_on=row.incurred_on, person=row.person)
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

    for r in s.query(ExpensePlanChange).filter_by(expense_id=ref.id).all():
        if r.recorded_seq == 1:
            events.append(alloc.Event('expense_created', {'amount': None, 'plan': r.plan,
                                                          'incurred_on': r.effective_on},
                                      r.effective_seq, r.recorded_seq + 0.5))
        else:
            events.append(alloc.Event('plan_changed', {'to': r.plan,
                                                       'effective': r.effective_on},
                                      r.effective_seq, r.recorded_seq))

    for r in s.query(ExpenseRuleChange).filter_by(expense_id=ref.id).all():
        events.append(alloc.Event('rules_changed', {'to': r.rules_version},
                                  r.effective_seq, r.recorded_seq))
    for r in s.query(ExpenseYearRoll).filter_by(expense_id=ref.id).all():
        events.append(alloc.Event('year_rolled', {'to': r.rolled_to},
                                  r.effective_seq, r.recorded_seq))
    for r in s.query(ExpenseDetermination).filter_by(expense_id=ref.id).all():
        events.append(alloc.Event('determination_recorded',
                                  {'status': r.status, 'amount': r.amount,
                                   'evidence': r.evidence},
                                  r.effective_seq, r.recorded_seq))

    # The created event carries both the amount and the plan; they were written to two
    # tables and are stitched back into one event here.
    created = [v for v in events if v.kind == 'expense_created']
    if len(created) == 2:
        amount = next((c.payload.get('amount') for c in created
                       if c.payload.get('amount') is not None), 0.0)
        plan = next((c.payload.get('plan') for c in created if c.payload.get('plan')), None)
        for c in created[1:]:
            events.remove(c)
        created[0].payload = {'amount': amount, 'plan': plan,
                              'incurred_on': row.incurred_on}
        e.plan = plan

    e.events = events
    e._seq = max([v.recorded_seq for v in events] or [0])
    e._effective = max([v.effective_seq for v in events] or [0.0])

    links = s.query(ExpenseMergeLink).filter_by(merged_into_id=ref.id).all()
    e.merged_from = [_load(Ref(l.merged_from_id)) for l in links]

    own = (_rows_by_json(ref.id) if JSON_RELATIONSHIP
           else s.query(HistorianEntryX).filter_by(healthcare_expense_id=ref.id).all())
    e.provenance = [{'kind': h.event_category, 'at': h.created_at} for h in own]
    for m in e.merged_from:
        e.provenance.extend(m.provenance)
    return e


def _amount_from_json(expense_id, recorded_seq):
    """A read path that must parse JSON to recover a value an invariant depends on. Exactly
    what the criterion forbids, present only so phase 3 can demonstrate it being caught."""
    for h in _s().query(HistorianEntryX).all():
        if not h.context_json:
            continue
        d = json.loads(h.context_json)
        if d.get('expense_id') == expense_id and d.get('seq') == recorded_seq:
            return float(d['payload'].get('amount') or 0.0)
    return 0.0


def _rows_by_json(expense_id):
    """The same forbidden shape, for a relationship rather than a value."""
    out = []
    for h in _s().query(HistorianEntryX).all():
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


def _run(fx, model):
    """Run the fixture silently. Its own output is suppressed so the phases below read as
    phases - phase 3 deliberately breaks things, and its failures are the point rather than a
    problem."""
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

    # The mirror must be the shipped table plus exactly one column, or this experiment is
    # testing something other than what it claims.
    real = {c.name for c in db.HistorianEntry.__table__.columns}
    mine = {c.name for c in HistorianEntryX.__table__.columns}
    check('the historian mirror is the shipped table plus one foreign key',
          mine - real == {'healthcare_expense_id'} and real - mine == set())

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
    before = _s().query(HistorianEntryX).filter(
        HistorianEntryX.context_json.isnot(None)).count()
    WRITE_JSON = False
    try:
        passed2, failures2, err2 = _run(fx, Store())
    finally:
        WRITE_JSON = True
    after = _s().query(HistorianEntryX).filter(
        HistorianEntryX.context_json.isnot(None)).count()

    check('the second phase wrote no context_json at all', after == before)
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
        print('CRITERION MET. The fixture round-trips through the schema with 0 structural')
        print('relationships in context_json, and passes in full with the column never')
        print('written. Shipping this is one migration: one nullable foreign key on')
        print('historian_entries, plus the structure tables.')
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
