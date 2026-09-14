"""About-ness: the crossing from "A says X" to "X is about O" is a claim of its own - and whether each
way of collapsing it into the read propositions is caught.

`gw 2.0/ARTEFACT_ABOUTNESS.md` s9 (ruled 2026-09-14). Runs the build gate
(`tests/test_artefact_concerns_fixture.py`) and then breaks the slice five ways, the record's list:

    the match establishes            a reading-sourced concerns claim manufactures a party's assertion
    the read claim's participant     asserting concerns(A, O) fills O into A's read propositions
      is filled
    retracting the association       retracting the concerns utterance removes A's read evidence
      retracts the value
    re-assertion is the crossing     household testimony about O manufactures a concerns claim
    a value acquires O without       a read proposition with candidates is pointed at an obligation
      a concerns claim                 by the matcher

Same shape as s86-s92: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_artefact_concerns_fixture.py'
    spec = importlib.util.spec_from_file_location('test_artefact_concerns_fixture', path)
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
    P, E, R, O = db.Proposition.__table__, db.EvidentiaryRelationship.__table__, db.Reading.__table__, db.Obligation.__table__

    def _prop(connection, pid):
        return connection.execute(P.select().where(P.c.id == pid)).first()

    def _without_guard(make_listener):
        models = [getattr(db, n) for n in db._IMMUTABLE_REFERENCES]
        for m in models:
            event.remove(m, 'before_update', db._refuse_repoint)
        undo_listener = make_listener()

        def restore():
            undo_listener()
            for m in models:
                event.listen(m, 'before_update', db._refuse_repoint)
        return restore

    def match_establishes():
        def manufacture(mapper, connection, target):
            if target.reading_id is None:
                return
            p = _prop(connection, target.proposition_id)
            if p is not None and p.kind == db.ARTEFACT_CONCERNS:
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                connection.execute(E.insert().values(proposition_id=p.id, utterance_id=u.id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', manufacture)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', manufacture)

    def participant_filled():
        def fill():
            def on_concerns(mapper, connection, target):
                if target.kind != db.ARTEFACT_CONCERNS or target.object_obligation_id is None:
                    return
                readings = [r.id for r in connection.execute(R.select().where(R.c.artefact_id == target.subject_artefact_id))]
                if not readings:
                    return
                pids = [e.proposition_id for e in connection.execute(E.select().where(E.c.reading_id.in_(readings)))]
                connection.execute(P.update().where(P.c.id.in_(pids), P.c.object_state == db.PARTICIPANT_CANDIDATES)
                                   .values(object_state=db.PARTICIPANT_ESTABLISHED,
                                           object_obligation_id=target.object_obligation_id))
            event.listen(db.Proposition, 'after_insert', on_concerns)
            return lambda: event.remove(db.Proposition, 'after_insert', on_concerns)
        return _without_guard(fill)

    def retraction_retracts_value():
        def on_retraction(mapper, connection, target):
            if target.kind != db.UTTERANCE_RETRACTION or target.subject_utterance_id is None:
                return
            # the concerns claims that utterance evidenced -> their artefacts -> delete the read evidence
            cps = [e.proposition_id for e in connection.execute(E.select().where(E.c.utterance_id == target.subject_utterance_id))]
            for cp in cps:
                p = _prop(connection, cp)
                if p is None or p.kind != db.ARTEFACT_CONCERNS:
                    continue
                readings = [r.id for r in connection.execute(R.select().where(R.c.artefact_id == p.subject_artefact_id))]
                if readings:
                    connection.execute(E.delete().where(E.c.reading_id.in_(readings)))
        event.listen(db.Proposition, 'after_insert', on_retraction)
        return lambda: event.remove(db.Proposition, 'after_insert', on_retraction)

    def reassertion_is_crossing():
        def on_testimony(mapper, connection, target):
            if target.utterance_id is None:
                return
            p = _prop(connection, target.proposition_id)
            if p is None or p.kind == db.ARTEFACT_CONCERNS or p.subject_obligation_id is None:
                return
            a = connection.execute(db.Artefact.__table__.select().limit(1)).first()
            if a is None:
                return
            res = connection.execute(P.insert().values(kind=db.ARTEFACT_CONCERNS,
                                                       subject_state=db.PARTICIPANT_ESTABLISHED,
                                                       subject_artefact_id=a.id,
                                                       object_state=db.PARTICIPANT_ESTABLISHED,
                                                       object_obligation_id=p.subject_obligation_id))
            connection.execute(E.insert().values(proposition_id=res.inserted_primary_key[0],
                                                 utterance_id=target.utterance_id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', on_testimony)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', on_testimony)

    def value_acquires_o():
        def acquire():
            def on_candidates(mapper, connection, target):
                if target.object_state != db.PARTICIPANT_CANDIDATES:
                    return
                o = connection.execute(O.select().limit(1)).first()
                if o is not None:
                    connection.execute(P.update().where(P.c.id == target.id)
                                       .values(object_state=db.PARTICIPANT_ESTABLISHED, object_obligation_id=o.id))
            event.listen(db.Proposition, 'after_insert', on_candidates)
            return lambda: event.remove(db.Proposition, 'after_insert', on_candidates)
        return _without_guard(acquire)

    return [
        ('the account-number match manufactures a party\'s assertion', match_establishes),
        ('asserting concerns(A, O) fills O into A\'s read propositions', participant_filled),
        ('retracting the association removes A\'s read evidence', retraction_retracts_value),
        ('household testimony about O manufactures a concerns claim', reassertion_is_crossing),
        ('a read proposition acquires an obligation without any concerns claim', value_acquires_o),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries artefact_concerns as a ruled kind presupposing an established identity',
          hasattr(db, 'ARTEFACT_CONCERNS') and db.ARTEFACT_CONCERNS in db.RULED_KINDS
          and db.RULED_KINDS[db.ARTEFACT_CONCERNS]['subject'] == ('subject_artefact_id',)
          and db.RULED_KINDS[db.ARTEFACT_CONCERNS]['reading_establishes'] is False
          and db.RULED_KINDS[db.ARTEFACT_CONCERNS]['relational_knowing'] is True)

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the artefact-concerns fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the artefact-concerns fixture passes in full',
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
