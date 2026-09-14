"""Utterance retraction: a higher-order claim can say an assertion no longer stands; it cannot rewrite,
resolve or replace it - and whether each way of letting it do so is caught.

`gw 2.0/CLAIM_ABOUT_CLAIM.md` s7 (ruled 2026-09-13). Runs the build gate
(`tests/test_utterance_retraction_fixture.py`) and then breaks the slice five ways:

    a verdict appears                 is_retracted(utterance) is added to the substrate
    the earlier claim is removed      inserting a retraction deletes the retracted utterance's evidence
    a second participant is smuggled  the registry lets a retraction name a replacement utterance
    meaning migrates into content     a retraction with empty content is refused as incomplete
    strength scored from foundation   relational_knowing is ignored and the claimant's foundation decides

Same shape as s86-s90: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_utterance_retraction_fixture.py'
    spec = importlib.util.spec_from_file_location('test_utterance_retraction_fixture', path)
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

    def verdict_appears():
        def is_retracted(session, utterance):
            return session.query(db.Proposition).filter_by(kind=db.UTTERANCE_RETRACTION,
                                                           subject_utterance_id=utterance.id).count() > 0
        db.is_retracted = is_retracted
        return lambda: delattr(db, 'is_retracted')

    def earlier_claim_removed():
        def purge(mapper, connection, target):
            if target.kind == db.UTTERANCE_RETRACTION and target.subject_utterance_id is not None:
                t = db.EvidentiaryRelationship.__table__
                connection.execute(t.delete().where(t.c.utterance_id == target.subject_utterance_id))
        event.listen(db.Proposition, 'after_insert', purge)
        return lambda: event.remove(db.Proposition, 'after_insert', purge)

    def second_participant_smuggled():
        saved = dict(db.RULED_KINDS[db.UTTERANCE_RETRACTION])
        db.RULED_KINDS[db.UTTERANCE_RETRACTION]['object'] = ('object_utterance_id',)

        def restore():
            db.RULED_KINDS[db.UTTERANCE_RETRACTION].clear()
            db.RULED_KINDS[db.UTTERANCE_RETRACTION].update(saved)
        return restore

    def meaning_in_content():
        orig = db.participant_violations

        def demanding(prop):
            out = orig(prop)
            if getattr(prop, 'kind', None) == db.UTTERANCE_RETRACTION and not getattr(prop, 'content', None):
                out.append('a retraction must say why')
            return out
        db.participant_violations = demanding
        return lambda: setattr(db, 'participant_violations', orig)

    def foundation_scores():
        saved = db.RULED_KINDS[db.UTTERANCE_RETRACTION]['relational_knowing']
        db.RULED_KINDS[db.UTTERANCE_RETRACTION]['relational_knowing'] = False

        def restore():
            db.RULED_KINDS[db.UTTERANCE_RETRACTION]['relational_knowing'] = saved
        return restore

    return [
        ('a verdict accessor appears on the substrate', verdict_appears),
        ('inserting a retraction removes the retracted utterance\'s evidence', earlier_claim_removed),
        ('a retraction may name a replacement as its second participant', second_participant_smuggled),
        ('meaning migrates into content - an empty retraction is refused', meaning_in_content),
        ('strength is scored from the claimant\'s foundation', foundation_scores),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries utterance_retraction as a ruled kind with a required absence',
          hasattr(db, 'UTTERANCE_RETRACTION') and db.UTTERANCE_RETRACTION in db.RULED_KINDS
          and db.RULED_KINDS[db.UTTERANCE_RETRACTION]['object'] == ()
          and db.RULED_KINDS[db.UTTERANCE_RETRACTION]['relational_knowing'] is True)

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the utterance-retraction fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the utterance-retraction fixture passes in full',
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
