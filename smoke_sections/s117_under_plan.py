"""under_plan: the first ruled role kind, built by item 9 pass 9A exactly as pass F accepted it - and whether each way of
giving the endpoint a MEANING is caught.

`gw 2.0/CATALOGUES.md` s 9A (2026-09-19), `gw 2.0/RELATION_SEMANTICS.md` s F.8 / F.10. Runs the build gate
(`tests/test_under_plan_fixture.py`) and then breaks the substrate seven ways, each an attempt to let Plan's existence,
a document or another claim supply what only a party's assertion may:

    plan_members appears             a selector over the plan's parties
    current_plan_of appears          a selector over a party's plans - F20's refused resolver
    membership from the card         a reading establishes under_plan (reading_establishes flipped)
    membership from an expense       an expense in respect of a plan mints an under_plan claim for whoever incurred it
    an expense from membership       a party under a plan carries their expense onto it
    a period on the anchor           `members` appears on Plan
    is_eligible from the stance      the insurer's "never eligible" answers eligibility

Same shape as s100 / s106: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_under_plan_fixture.py'
    spec = importlib.util.spec_from_file_location('test_under_plan_fixture', path)
    fx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fx)
    return fx


def _run_fixture(fx, db):
    fx.PASS.clear()
    fx.FAIL.clear()
    err = None
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            fx.run(db)
        except Exception as e:                                # noqa: BLE001
            err = f'{type(e).__name__}: {e}'
    return len(fx.PASS), list(fx.FAIL), err


def _mutations(db):
    def plan_members():
        db.plan_members = lambda session, plan: []
        return lambda: delattr(db, 'plan_members')

    def current_plan_of():
        db.current_plan_of = lambda session, party, d: None
        return lambda: delattr(db, 'current_plan_of')

    def membership_from_card():
        rule = db.RULED_KINDS[db.UNDER_PLAN_BEGAN]
        db.RULED_KINDS[db.UNDER_PLAN_BEGAN] = dict(rule, reading_establishes=True)
        return lambda: db.RULED_KINDS.__setitem__(db.UNDER_PLAN_BEGAN, rule)

    def membership_from_expense():
        from sqlalchemy import event

        def mint_member(mapper, connection, target):
            P = db.Proposition.__table__
            pairs = []
            if target.kind == db.EXPENSE_IN_RESPECT_OF_PLAN and target.object_plan_id is not None:
                for inc in connection.execute(P.select().where(P.c.kind == 'incurred_by', P.c.object_expense_id == target.subject_expense_id)).fetchall():
                    pairs.append((inc.subject_party_id, target.object_plan_id))
            if target.kind == 'incurred_by' and target.object_expense_id is not None:
                for xp in connection.execute(P.select().where(P.c.kind == db.EXPENSE_IN_RESPECT_OF_PLAN, P.c.subject_expense_id == target.object_expense_id)).fetchall():
                    pairs.append((target.subject_party_id, xp.object_plan_id))
            for party_id, plan_id in pairs:
                if party_id is not None and plan_id is not None:
                    connection.execute(P.insert().values(kind=db.UNDER_PLAN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                                         subject_party_id=party_id, object_plan_id=plan_id, as_of='2026-01-01'))
        event.listen(db.Proposition, 'after_insert', mint_member)
        return lambda: event.remove(db.Proposition, 'after_insert', mint_member)

    def expense_from_membership():
        from sqlalchemy import event

        def attribute(mapper, connection, target):
            if target.kind == 'incurred_by' and target.object_expense_id is not None and target.subject_party_id is not None:
                P = db.Proposition.__table__
                under = connection.execute(P.select().where(P.c.kind == db.UNDER_PLAN, P.c.subject_party_id == target.subject_party_id)).fetchone()
                if under is not None:
                    connection.execute(P.insert().values(kind=db.EXPENSE_IN_RESPECT_OF_PLAN, subject_state=db.PARTICIPANT_ESTABLISHED,
                                                         object_state=db.PARTICIPANT_ESTABLISHED, subject_expense_id=target.object_expense_id,
                                                         object_plan_id=under.object_plan_id))
        event.listen(db.Proposition, 'after_insert', attribute)
        return lambda: event.remove(db.Proposition, 'after_insert', attribute)

    def period_on_anchor():
        from sqlalchemy import Column, String
        col = Column('members', String(64))
        db.Plan.__table__.append_column(col)
        return lambda: db.Plan.__table__._columns.remove(col)

    def is_eligible():
        db.is_eligible = lambda session, party, plan, d: False
        return lambda: delattr(db, 'is_eligible')

    return [
        ('plan_members appears (a selector over the plan\'s parties)', plan_members),
        ('current_plan_of appears (F20\'s refused resolver)', current_plan_of),
        ('membership from the card (a reading establishes the role)', membership_from_card),
        ('membership from an expense (F14 reversed)', membership_from_expense),
        ('an expense from membership (F13 / E24)', expense_from_membership),
        ('a period / members column on the anchor', period_on_anchor),
        ('is_eligible from the insurer\'s stance (F5)', is_eligible),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    # 9B since marked under_plan 'role': True (classification only, 9B-F1) and bound two more roles' boundaries; under_plan's own are still exactly two
    check('core/database.py carries under_plan and its two boundaries exactly as accepted - party -> plan, a reading never establishes, knowing undetermined, marked a role (9B) - and no selector / eligibility / period helper',
          db.RULED_KINDS[db.UNDER_PLAN] == {'subject': ('subject_party_id',), 'object': ('object_plan_id',), 'symmetric': False,
                                            'reading_establishes': False, 'relational_knowing': True, 'role': True}
          and {k for k, r in db.RULED_KINDS.items() if r.get('of') == db.UNDER_PLAN} == {db.UNDER_PLAN_BEGAN, db.UNDER_PLAN_ENDED}
          and db.registry_violations() == []
          and not any(hasattr(db, n) for n in ('plan_members', 'members_of', 'current_plan_of', 'primary_plan', 'is_eligible', 'is_active')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the under_plan fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the under_plan fixture passes in full',
          not failures and not err and passed > 0)
    if failures or err:
        for f in failures[:6]:
            print(f'        failing: {f}')
        if err:
            print(f'        raised: {err}')
        check('mutation detection is meaningful (baseline green)', False)
        return

    for name, make in _mutations(db):
        undo = make()
        try:
            _, mutated, mutated_err = _run_fixture(fx, db)
        finally:
            undo()
        check('caught: ' + name, bool(mutated) or bool(mutated_err))
        after, after_failures, after_err = _run_fixture(fx, db)
        check('restored after: ' + name,
              after == passed and not after_failures and not after_err)

    restored, restored_failures, restored_err = _run_fixture(fx, db)
    check('the module is left exactly as it was found',
          restored == passed and not restored_failures and not restored_err)
