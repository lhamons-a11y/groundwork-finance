"""Artefact and reading: the thing encountered vs the act of observing it - and whether letting a reading
become an alternate utterance is caught.

`gw 2.0/ARTEFACT_READING_SLICE.md` s8 (ruled 2026-09-13). Runs the build gate
(`tests/test_artefact_reading_fixture.py`) and then breaks the slice five ways, each one of the
collapses the record found:

    held-only guard removed          a reading of an asserted artefact is accepted - RE-READ of a
                                     document Groundwork never held
    reader xor guard removed         a reading with no reader, or two, is accepted - NULL becomes
                                     "unknown reader" again
    reader read as origin            derived_strength takes reader_party as the origin - a member
                                     transcribing Aetna's EOB becomes knowing for its figures
    one-source guard removed         a relationship may name both a reading and an utterance, or neither
    held/asserted guard removed      a held artefact under an utterance, or an asserted one under none

Same shape as s86 / s87: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_artefact_reading_fixture.py'
    spec = importlib.util.spec_from_file_location('test_artefact_reading_fixture', path)
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

    def _remove_listener(model, fn):
        event.remove(model, 'before_insert', fn)
        event.remove(model, 'before_update', fn)

        def restore():
            event.listen(model, 'before_insert', fn)
            event.listen(model, 'before_update', fn)
        return restore

    def held_only_removed():
        orig = db.reading_violations

        def lenient(reading, artefact_held):
            return [v for v in orig(reading, artefact_held) if 'held' not in v]
        return _swap(db, 'reading_violations', lenient)

    def reader_xor_removed():
        orig = db.reading_violations

        def lenient(reading, artefact_held):
            return [v for v in orig(reading, artefact_held) if 'reader' not in v]
        return _swap(db, 'reading_violations', lenient)

    def reader_as_origin():
        orig = db.derived_strength

        def collapsed(session, relation, knowing):
            if relation.reading_id is None:
                return orig(session, relation, knowing)
            prop = relation.proposition or session.get(db.Proposition, relation.proposition_id)
            rd = relation.reading or session.get(db.Reading, relation.reading_id)
            if prop.kind not in knowing:
                return db.STRENGTH_UNDETERMINED
            origin_kind = 'person' if rd.reader_party_id is not None else 'institution'
            return db.STRENGTH_KNOWING if origin_kind in knowing[prop.kind] else db.STRENGTH_NOT_KNOWING
        return _swap(db, 'derived_strength', collapsed)

    def one_source_removed():
        return _remove_listener(db.EvidentiaryRelationship, db._validate_source)

    def held_asserted_removed():
        return _remove_listener(db.Artefact, db._validate_artefact)

    return [
        ('a reading of an asserted artefact is accepted (RE-READ of an unheld document)', held_only_removed),
        ('a reading with no reader, or two, is accepted', reader_xor_removed),
        ('the reader is taken as the origin - a reading becomes an alternate utterance', reader_as_origin),
        ('a relationship may name two sources or none', one_source_removed),
        ('held and asserted lose their guard', held_asserted_removed),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries artefacts and readings beside the substrate',
          all(hasattr(db, n) for n in ('Artefact', 'Reading', 'reading_violations', 'artefact_violations',
                                       'source_violations', 'readings_of_unheld_artefacts')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the artefact/reading fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the artefact/reading fixture passes in full',
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
