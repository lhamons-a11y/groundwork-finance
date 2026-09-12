"""The Person -> Party anchor: the creation path and the guard, and whether breaking either is caught.

`gw 2.0/PERSON_PARTY_ANCHOR.md` (ruled 2026-09-12). The database can express at-most-one
(`UNIQUE`); at-least-one is the creation path plus a guard. This section runs the guard
(`tests/test_party_anchor_fixture.py`) and then breaks the creation path two ways to show the
guard sees each:

    the listener is removed       a Person is added and no Party appears - the forbidden state
    the backfill over-mints       it creates anchors for people who already have one

Same shape as s85: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_party_anchor_fixture.py'
    spec = importlib.util.spec_from_file_location('test_party_anchor_fixture', path)
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

    def listener_removed():
        # The construction guarantee, gone: Person rows are written and no anchor is minted.
        event.remove(db.Person, 'after_insert', db._mint_party_anchor)
        return lambda: event.listen(db.Person, 'after_insert', db._mint_party_anchor)

    def backfill_over_mints():
        # A backfill that mints for everyone, not only for the missing - the second run is
        # no longer a no-op, and UNIQUE turns the over-mint into an error.
        orig = db.backfill_party_anchors

        def broken(session):
            people = session.query(db.Person).all()
            for p in people:
                session.add(db.Party(person_id=p.id))
            session.flush()
            return len(people)
        db.backfill_party_anchors = broken
        return lambda: setattr(db, 'backfill_party_anchors', orig)

    return [
        ('the creation path no longer mints the anchor', listener_removed),
        ('the backfill mints for people who already have an anchor', backfill_over_mints),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries the Party anchor',
          hasattr(db, 'Party') and hasattr(db, 'people_without_party'))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the party-anchor fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the party-anchor fixture passes in full',
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
