"""Artefact origin: an assertion about the artefact by a party, never a property of it - and whether the
ways of letting a document vouch for itself are caught.

`gw 2.0/ARTEFACT_ORIGIN.md` s8 (ruled 2026-09-13). Runs the build gate
(`tests/test_artefact_origin_fixture.py`) and then breaks the slice five ways:

    a reading establishes origin       the letterhead vouches for the document - the circle closes
    the reader is consulted            reading strength derives from who read it, not whose statement it is
    the anchor guard is removed        a party with no anchor, or two, is accepted
    position chooses among claims      the last-asserted party wins - [-1] returns as "current origin"
    the origin link is not scored      reading strength ignores how well the origin itself is established

Same shape as s86-s88: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_artefact_origin_fixture.py'
    spec = importlib.util.spec_from_file_location('test_artefact_origin_fixture', path)
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

    def reading_establishes():
        orig = db.artefact_origin

        def credulous(session, artefact):
            state, parties = orig(session, artefact)
            if state == db.ORIGIN_CANDIDATES and len(parties) == 1:
                return db.ORIGIN_ESTABLISHED, parties
            return state, parties
        return _swap(db, 'artefact_origin', credulous)

    def reader_consulted():
        orig = db.derived_strength

        def by_reader(session, relation, knowing):
            if relation.reading_id is None:
                return orig(session, relation, knowing)
            prop = relation.proposition or session.get(db.Proposition, relation.proposition_id)
            rd = relation.reading or session.get(db.Reading, relation.reading_id)
            if prop.kind not in knowing:
                return db.STRENGTH_UNDETERMINED
            reader = session.get(db.Party, rd.reader_party_id) if rd.reader_party_id else None
            origin_kind = db.party_foundation(reader) if reader else 'institution'
            return db.STRENGTH_KNOWING if origin_kind in knowing[prop.kind] else db.STRENGTH_NOT_KNOWING
        return _swap(db, 'derived_strength', by_reader)

    def anchor_guard_removed():
        event.remove(db.Party, 'before_insert', db._validate_party_anchor)
        event.remove(db.Party, 'before_update', db._validate_party_anchor)

        def restore():
            event.listen(db.Party, 'before_insert', db._validate_party_anchor)
            event.listen(db.Party, 'before_update', db._validate_party_anchor)
        return restore

    def position_chooses():
        orig = db.artefact_origin

        def latest_wins(session, artefact):
            state, parties = orig(session, artefact)
            if state == db.ORIGIN_MULTIPLE:
                last = (session.query(db.Proposition)
                        .filter_by(kind=db.ARTEFACT_ORIGIN, subject_artefact_id=artefact.id)
                        .order_by(db.Proposition.id.desc()).first())
                return db.ORIGIN_ESTABLISHED, [last.object_party_id]
            return state, parties
        return _swap(db, 'artefact_origin', latest_wins)

    def link_not_scored():
        orig = db.derived_strength

        def link_only(session, relation, knowing):
            if relation.reading_id is None:
                return orig(session, relation, knowing)
            prop = relation.proposition or session.get(db.Proposition, relation.proposition_id)
            rd = relation.reading or session.get(db.Reading, relation.reading_id)
            art = session.get(db.Artefact, rd.artefact_id)
            state, parties = db.artefact_origin(session, art)
            if state != db.ORIGIN_ESTABLISHED or prop.kind not in knowing:
                return db.STRENGTH_UNDETERMINED
            origin = session.get(db.Party, parties[0])
            return (db.STRENGTH_KNOWING if db.party_foundation(origin) in knowing[prop.kind]
                    else db.STRENGTH_NOT_KNOWING)
        return _swap(db, 'derived_strength', link_only)

    return [
        ('a reading of the artefact establishes its origin - the document vouches for itself', reading_establishes),
        ('the reader is consulted for a reading\'s strength', reader_consulted),
        ('a party may have no anchor, or two', anchor_guard_removed),
        ('the last-asserted party is chosen among multiple origin claims', position_chooses),
        ('the origin claim\'s own strength is ignored - the link is not weakest-link', link_not_scored),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries the origin kind, its derivation and the institution anchor',
          all(hasattr(db, n) for n in ('ARTEFACT_ORIGIN', 'artefact_origin', 'party_foundation',
                                       'parties_without_one_anchor', '_validate_party_anchor'))
          and 'minted_by_id' in {c.name for c in db.Party.__table__.columns})

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the artefact-origin fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the artefact-origin fixture passes in full',
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
