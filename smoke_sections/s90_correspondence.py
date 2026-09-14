"""Correspondence: a match is a reason to ask; only an answer is a claim - and whether the ways of
turning an observation into an identity are caught.

`gw 2.0/CORRESPONDENCE.md` s8 (ruled 2026-09-13). Runs the build gate
(`tests/test_correspondence_fixture.py`) and then breaks the slice six ways, Rob's list:

    a hash match establishes             a reading-sourced claim is read as a member, not a candidate
    a party assertion does not establish the derivation ignores utterance-sourced claims
    merge / re-point accepted            the reference-immutability guard is removed
    cross-foundation accepted            party_corresponds(Person, institution) passes
    cross-type accepted                  the RULED_KINDS registry is emptied - slots go back to convention
    position resolves a contested one    the latest utterance decides and the contest disappears

Same shape as s86-s89: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_correspondence_fixture.py'
    spec = importlib.util.spec_from_file_location('test_correspondence_fixture', path)
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


def _swap(db, name, replacement):
    orig = getattr(db, name)
    setattr(db, name, replacement)
    return lambda: setattr(db, name, orig)


def _mutations(db):
    from sqlalchemy import event

    def hash_establishes():
        orig = db.referent

        def credulous(session, thing):
            state, contains, cands = orig(session, thing)
            if state == db.REFERENT_CANDIDATES:
                return db.REFERENT_CORRESPONDING, sorted(set(contains) | set(cands)), []
            return state, contains, cands
        return _swap(db, 'referent', credulous)

    def assertion_ignored():
        orig = db.referent

        def deaf(session, thing):
            state, contains, cands = orig(session, thing)
            if state in (db.REFERENT_CORRESPONDING, db.REFERENT_CONTESTED):
                return db.REFERENT_SEPARATE, [thing.id], cands
            return state, contains, cands
        return _swap(db, 'referent', deaf)

    def repoint_allowed():
        models = [getattr(db, n) for n in db._IMMUTABLE_REFERENCES]
        for m in models:
            event.remove(m, 'before_update', db._refuse_repoint)

        def restore():
            for m in models:
                event.listen(m, 'before_update', db._refuse_repoint)
        return restore

    def foundations_cross():
        return _swap(db, '_foundation_violations', lambda connection, a, b: [])

    def registry_emptied():
        saved = dict(db.RULED_KINDS)
        db.RULED_KINDS.clear()

        def restore():
            db.RULED_KINDS.update(saved)
        return restore

    def position_resolves():
        orig = db.referent

        def latest_wins(session, thing):
            state, contains, cands = orig(session, thing)
            if state == db.REFERENT_CONTESTED:
                # "the most recent utterance settles it" - the [-1] the rulings forbid
                return db.REFERENT_CORRESPONDING, contains, cands
            return state, contains, cands
        return _swap(db, 'referent', latest_wins)

    return [
        ('a hash match establishes a correspondence', hash_establishes),
        ('a party\'s assertion does not establish one', assertion_ignored),
        ('a reading, claim, utterance or relationship may be re-pointed (a merge)', repoint_allowed),
        ('party_corresponds crosses foundations', foundations_cross),
        ('the ruled kinds lose their slot contracts - cross-type and reflexive claims pass', registry_emptied),
        ('position resolves a contested referent', position_resolves),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries the two correspondence kinds, the registry, the guards and referent()',
          all(hasattr(db, n) for n in ('ARTEFACT_CORRESPONDS', 'PARTY_CORRESPONDS', 'RULED_KINDS', 'referent',
                                       '_foundation_violations', '_refuse_repoint', '_IMMUTABLE_REFERENCES')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the correspondence fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the correspondence fixture passes in full',
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
