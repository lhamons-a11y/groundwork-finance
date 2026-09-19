"""Role period: a role has no intrinsic period; began / ended are propositions of their own, bound to the role
kind in the registry; a boundary never rewrites, implies its opposite, resolves, or creates a role - and
whether each way of letting it is caught.

`gw 2.0/ROLE_PERIOD.md` s7 (ruled RP2, 2026-09-14). Runs the build gate
(`tests/test_role_period_fixture.py`) and then breaks the slice seven ways:

    anything bounds anything        the registry guard stops checking the binding
    the period becomes structure    the proposition grows an `effective_to` attribute
    as_of becomes optional          a boundary claim without a date is accepted
    an ending rewrites history      inserting an ending deletes the beginning it "closes"
    a beginning creates the role    inserting a beginning also inserts a holds-at claim
    a resolver slips in             an `in_effect_on` accessor appears
    retraction becomes ending       retracting a beginning's utterance inserts an ending

Same shape as s86-s99: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_role_period_fixture.py'
    spec = importlib.util.spec_from_file_location('test_role_period_fixture', path)
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
    from sqlalchemy import event
    P = db.Proposition.__table__

    def anything_bounds_anything():
        orig = db.registry_violations
        db.registry_violations = lambda registry=None, kinds=None: []
        return lambda: setattr(db, 'registry_violations', orig)

    def period_becomes_structure():
        db.Proposition.effective_to = None
        return lambda: delattr(db.Proposition, 'effective_to')

    def as_of_optional():
        orig = db._boundary_violations

        def no_date_needed(prop):
            return [v for v in orig(prop) if 'as_of' not in v]
        db._boundary_violations = no_date_needed
        return lambda: setattr(db, '_boundary_violations', orig)

    def ending_rewrites_history():
        def close(mapper, connection, target):
            rule = db.RULED_KINDS.get(target.kind)
            if rule and rule.get('boundary') == 'ended':
                began = db.boundary_kinds_of(rule['of']).get('began')
                if began:
                    connection.execute(P.delete().where(P.c.kind == began))
        event.listen(db.Proposition, 'after_insert', close)
        return lambda: event.remove(db.Proposition, 'after_insert', close)

    def beginning_creates_role():
        def holds(mapper, connection, target):
            rule = db.RULED_KINDS.get(target.kind)
            if rule and rule.get('boundary') == 'began':
                connection.execute(P.insert().values(
                    kind=rule['of'], subject_state=target.subject_state, object_state=target.object_state,
                    subject_party_id=target.subject_party_id, object_party_id=target.object_party_id,
                    object_plan_id=target.object_plan_id, object_obligation_id=target.object_obligation_id,
                    as_of=target.as_of))
        event.listen(db.Proposition, 'after_insert', holds)
        return lambda: event.remove(db.Proposition, 'after_insert', holds)

    def resolver_slips_in():
        db.in_effect_on = lambda session, kind, on: None
        return lambda: delattr(db, 'in_effect_on')

    def retraction_becomes_ending():
        def end_it(mapper, connection, target):
            if target.kind != db.UTTERANCE_RETRACTION:
                return
            began_rows = connection.execute(
                P.select().where(P.c.kind == 'serves_began')).fetchall()
            for b in began_rows:
                connection.execute(P.insert().values(
                    kind='serves_ended', subject_state=b.subject_state, object_state=b.object_state,
                    subject_party_id=b.subject_party_id, object_party_id=b.object_party_id, as_of=b.as_of))
        event.listen(db.Proposition, 'after_insert', end_it)
        return lambda: event.remove(db.Proposition, 'after_insert', end_it)

    return [
        ('the registry guard stops checking the binding - anything bounds anything', anything_bounds_anything),
        ('the period becomes proposition structure', period_becomes_structure),
        ('a boundary claim without as_of is accepted', as_of_optional),
        ('an ending deletes the beginning it closes', ending_rewrites_history),
        ('a beginning inserts a holds-at claim - a boundary creates a role', beginning_creates_role),
        ('an in_effect_on resolver slips in', resolver_slips_in),
        ('retracting a beginning\'s utterance inserts an ending', retraction_becomes_ending),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    # item 9 pass 9A (CATALOGUES.md) built under_plan's two boundary entries as pass F accepted them - the registry's first
    check("core/database.py carries the boundary vocabulary, the registry guard, and exactly under_plan's two boundary entries (9A) - no other",
          all(hasattr(db, n) for n in ('BOUNDARIES', 'registry_violations', 'boundary_kinds_of', '_boundary_violations'))
          and db.BOUNDARIES == ('began', 'ended') and db.registry_violations() == []
          and {k for k, r in db.RULED_KINDS.items() if r.get('boundary') or r.get('of')} == {db.UNDER_PLAN_BEGAN, db.UNDER_PLAN_ENDED})

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the role-period fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the role-period fixture passes in full',
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

    restored, restored_failures, restored_err = _run_fixture(fx, db)
    check('the module is left exactly as it was found',
          restored == passed and not restored_failures and not restored_err)
