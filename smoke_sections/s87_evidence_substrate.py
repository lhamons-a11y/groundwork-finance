"""The evidence substrate: utterance, proposition, evidentiary relationship - and whether breaking its construction is caught.

`gw 2.0/SMALLEST_SCHEMA.md` s12 and `SHIPPED_VS_TARGET.md` s6 (ruled 2026-09-13). Runs the
build gate (`tests/test_evidence_substrate_fixture.py`) and then breaks the substrate two ways:

    the participant validator is removed     a proposition can say "established" with no referent -
                                             NULL becomes the source of the state again
    strength comes from a stored attribute   derived_strength stops reading the knowing relation and
                                             returns whatever is on the row - the drift the ruling forbids

Same shape as s85 / s86: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_evidence_substrate_fixture.py'
    spec = importlib.util.spec_from_file_location('test_evidence_substrate_fixture', path)
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

    def validator_removed():
        event.remove(db.Proposition, 'before_insert', db._validate_participants)
        event.remove(db.Proposition, 'before_update', db._validate_participants)

        def restore():
            event.listen(db.Proposition, 'before_insert', db._validate_participants)
            event.listen(db.Proposition, 'before_update', db._validate_participants)
        return restore

    def strength_stored():
        orig = db.derived_strength

        def broken(session, relation, knowing):
            # A "strength" that lives on the row - constant, and blind to the knowing relation.
            return getattr(relation, 'strength', db.STRENGTH_KNOWING)
        db.derived_strength = broken
        return lambda: setattr(db, 'derived_strength', orig)

    return [
        ('a proposition may claim an established participant with no referent', validator_removed),
        ('strength is read from the row instead of derived from the knowing relation', strength_stored),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries the evidence substrate',
          all(hasattr(db, n) for n in ('Utterance', 'Proposition', 'EvidentiaryRelationship',
                                       'derived_strength', 'participant_violations')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the evidence-substrate fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the evidence-substrate fixture passes in full',
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
