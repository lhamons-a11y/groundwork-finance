"""Proposition-level about-ness: information about a proposition, never inserted into it - and whether each
way of inserting it is caught.

`gw 2.0/PROPOSITION_ABOUTNESS.md` s7 (ruled 2026-09-14). Runs the build gate
(`tests/test_proposition_concerns_fixture.py`) and then breaks the slice six ways:

    the match establishes            a reading-sourced concerns claim manufactures a party's assertion
    the claim fills P's slot         asserting proposition_concerns(P, X) writes X into P's participant
    retraction reaches P             retracting the association removes P's read evidence
    a non-kind takes the slot        'contradiction' enters the registry with a proposition subject
    the one-source guard is removed  a concerns claim attaches to a proposition whose participant is established
    levels are enforced              a line-level claim naming an identity the artefact does not concern is refused

Same shape as s86-s94: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_proposition_concerns_fixture.py'
    spec = importlib.util.spec_from_file_location('test_proposition_concerns_fixture', path)
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
    P, E, R = db.Proposition.__table__, db.EvidentiaryRelationship.__table__, db.Reading.__table__

    def _prop(connection, pid):
        return connection.execute(P.select().where(P.c.id == pid)).first()

    def match_establishes():
        def manufacture(mapper, connection, target):
            if target.reading_id is None:
                return
            p = _prop(connection, target.proposition_id)
            if p is not None and p.kind == db.PROPOSITION_CONCERNS:
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                connection.execute(E.insert().values(proposition_id=p.id, utterance_id=u.id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', manufacture)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', manufacture)

    def claim_fills_slot():
        models = [getattr(db, n) for n in db._IMMUTABLE_REFERENCES]
        for m in models:
            event.remove(m, 'before_update', db._refuse_repoint)

        def fill(mapper, connection, target):
            if target.kind != db.PROPOSITION_CONCERNS:
                return
            vals = {}
            if target.object_obligation_id is not None:
                vals = {'object_state': db.PARTICIPANT_ESTABLISHED, 'object_obligation_id': target.object_obligation_id}
            elif target.object_payment_id is not None:
                vals = {'object_state': db.PARTICIPANT_ESTABLISHED, 'object_payment_id': target.object_payment_id}
            if vals:
                connection.execute(P.update().where(P.c.id == target.subject_proposition_id).values(**vals))
        event.listen(db.Proposition, 'after_insert', fill)

        def restore():
            event.remove(db.Proposition, 'after_insert', fill)
            for m in models:
                event.listen(m, 'before_update', db._refuse_repoint)
        return restore

    def retraction_reaches_p():
        def on_retraction(mapper, connection, target):
            if target.kind != db.UTTERANCE_RETRACTION or target.subject_utterance_id is None:
                return
            for e in connection.execute(E.select().where(E.c.utterance_id == target.subject_utterance_id)):
                c = _prop(connection, e.proposition_id)
                if c is not None and c.kind == db.PROPOSITION_CONCERNS and c.subject_proposition_id is not None:
                    connection.execute(E.delete().where(E.c.proposition_id == c.subject_proposition_id,
                                                        E.c.reading_id.isnot(None)))
        event.listen(db.Proposition, 'after_insert', on_retraction)
        return lambda: event.remove(db.Proposition, 'after_insert', on_retraction)

    def non_kind_takes_slot():
        db.RULED_KINDS['contradiction'] = {'subject': ('subject_proposition_id',), 'object': (),
                                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
        return lambda: db.RULED_KINDS.pop('contradiction', None)

    def one_source_guard_removed():
        orig = db._aboutness_violations

        def lenient(connection, target):
            return [v for v in orig(connection, target) if 'already has an established' not in v]
        db._aboutness_violations = lenient
        return lambda: setattr(db, '_aboutness_violations', orig)

    def levels_enforced():
        orig = db._aboutness_violations

        def strict(connection, target):
            out = orig(connection, target)
            if out or target.object_obligation_id is None:
                return out
            subj = _prop(connection, target.subject_proposition_id)
            # find the artefact the subject proposition was read from, and require the artefact to concern X
            rel = connection.execute(E.select().where(E.c.proposition_id == subj.id, E.c.reading_id.isnot(None))).first()
            if rel is None:
                return out
            rd = connection.execute(R.select().where(R.c.id == rel.reading_id)).first()
            ok = connection.execute(P.select().where(P.c.kind == db.ARTEFACT_CONCERNS,
                                                     P.c.subject_artefact_id == rd.artefact_id,
                                                     P.c.object_obligation_id == target.object_obligation_id)).first()
            return out if ok is not None else ['the artefact does not concern that identity']
        db._aboutness_violations = strict
        return lambda: setattr(db, '_aboutness_violations', orig)

    return [
        ('a heading match manufactures a party\'s assertion', match_establishes),
        ('asserting proposition_concerns writes the identity into P\'s participant', claim_fills_slot),
        ('retracting the association removes P\'s read evidence', retraction_reaches_p),
        ('a slice-5 non-kind takes the proposition-subject slot', non_kind_takes_slot),
        ('a concerns claim attaches to a proposition whose participant is established', one_source_guard_removed),
        ('consistency between levels is enforced as a guard', levels_enforced),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries proposition_concerns as the one ruled kind with a proposition subject, and its guard',
          hasattr(db, 'PROPOSITION_CONCERNS') and hasattr(db, '_aboutness_violations')
          and [k for k, r in db.RULED_KINDS.items() if 'subject_proposition_id' in r['subject']] == [db.PROPOSITION_CONCERNS]
          and db.RULED_KINDS[db.PROPOSITION_CONCERNS]['reading_establishes'] is False
          and db.RULED_KINDS[db.PROPOSITION_CONCERNS]['relational_knowing'] is True)

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the proposition-concerns fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the proposition-concerns fixture passes in full',
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
