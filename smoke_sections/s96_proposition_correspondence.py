"""Proposition correspondence: two observations or recordings of one claim - relational, never transmissive -
and whether each way of making it transmit, merge or judge is caught.

`gw 2.0/PROPOSITION_CORRESPONDENCE.md` s7 (ruled 2026-09-14). Runs the build gate
(`tests/test_proposition_correspondence_fixture.py`) and then breaks the slice six ways:

    the match establishes           a reading-sourced correspondence manufactures a party's assertion
    about-ness is carried           establishing a correspondence copies proposition_concerns to the other side
    correspondence merges           establishing a correspondence deletes the second proposition
    g1 is removed                   propositions with disagreeing established participants may correspond
    g1 over-reaches                 g1 starts inspecting content and kind - Pc1 and Pc6 get refused
    a non-kind takes the slot       'agrees_with' enters the registry with proposition participants

Same shape as s86-s95: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_proposition_correspondence_fixture.py'
    spec = importlib.util.spec_from_file_location('test_proposition_correspondence_fixture', path)
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
    P, E = db.Proposition.__table__, db.EvidentiaryRelationship.__table__

    def _prop(connection, pid):
        return connection.execute(P.select().where(P.c.id == pid)).first()

    def match_establishes():
        def manufacture(mapper, connection, target):
            if target.reading_id is None:
                return
            p = _prop(connection, target.proposition_id)
            if p is not None and p.kind == db.PROPOSITION_CORRESPONDS:
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                connection.execute(E.insert().values(proposition_id=p.id, utterance_id=u.id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', manufacture)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', manufacture)

    def aboutness_carried():
        def carry(mapper, connection, target):
            if target.utterance_id is None:
                return
            c = _prop(connection, target.proposition_id)
            if c is None or c.kind != db.PROPOSITION_CORRESPONDS:
                return
            a, b = c.subject_proposition_id, c.object_proposition_id
            for src, dst in ((a, b), (b, a)):
                for k in connection.execute(P.select().where(P.c.kind == db.PROPOSITION_CONCERNS,
                                                             P.c.subject_proposition_id == src)):
                    res = connection.execute(P.insert().values(kind=db.PROPOSITION_CONCERNS,
                                                               subject_state=db.PARTICIPANT_ESTABLISHED,
                                                               subject_proposition_id=dst,
                                                               object_state=db.PARTICIPANT_ESTABLISHED,
                                                               object_obligation_id=k.object_obligation_id,
                                                               object_payment_id=k.object_payment_id))
                    connection.execute(E.insert().values(proposition_id=res.inserted_primary_key[0],
                                                         utterance_id=target.utterance_id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', carry)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', carry)

    def correspondence_merges():
        def merge(mapper, connection, target):
            if target.utterance_id is None:
                return
            c = _prop(connection, target.proposition_id)
            if c is not None and c.kind == db.PROPOSITION_CORRESPONDS:
                connection.execute(E.delete().where(E.c.proposition_id == c.subject_proposition_id))
                connection.execute(P.delete().where(P.c.id == c.subject_proposition_id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', merge)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', merge)

    def g1_removed():
        orig = db._proposition_correspondence_violations

        def lenient(connection, target):
            return [v for v in orig(connection, target) if 'disagree' not in v]
        db._proposition_correspondence_violations = lenient
        return lambda: setattr(db, '_proposition_correspondence_violations', orig)

    def g1_overreaches():
        orig = db._proposition_correspondence_violations

        def judgemental(connection, target):
            out = orig(connection, target)
            if out:
                return out
            a = _prop(connection, target.subject_proposition_id)
            b = _prop(connection, target.object_proposition_id)
            if a.kind != b.kind or a.content != b.content:
                return ['these propositions do not seem equivalent']
            return out
        db._proposition_correspondence_violations = judgemental
        return lambda: setattr(db, '_proposition_correspondence_violations', orig)

    def non_kind_takes_slot():
        db.RULED_KINDS['agrees_with'] = {'subject': ('subject_proposition_id',), 'object': ('object_proposition_id',),
                                         'symmetric': True, 'reading_establishes': False, 'relational_knowing': True}
        return lambda: db.RULED_KINDS.pop('agrees_with', None)

    return [
        ('a position match manufactures a party\'s assertion', match_establishes),
        ('establishing a correspondence copies about-ness to the other proposition', aboutness_carried),
        ('establishing a correspondence merges the two propositions', correspondence_merges),
        ('g1 removed - disagreeing established participants may correspond', g1_removed),
        ('g1 over-reaches into content and kind', g1_overreaches),
        ('a slice-5 non-kind takes the proposition slots', non_kind_takes_slot),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries proposition_corresponds, its slot, referent() support and the g1 guard',
          hasattr(db, 'PROPOSITION_CORRESPONDS') and hasattr(db, '_proposition_correspondence_violations')
          and 'Proposition' in db._CORRESPONDENCE_OF
          and [k for k, r in db.RULED_KINDS.items() if 'object_proposition_id' in r['object']] == [db.PROPOSITION_CORRESPONDS]
          and db.RULED_KINDS[db.PROPOSITION_CORRESPONDS]['reading_establishes'] is False)

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the proposition-correspondence fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the proposition-correspondence fixture passes in full',
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
