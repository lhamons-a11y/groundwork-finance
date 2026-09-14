"""Obligation identity: a continuant minted by the household's assertion, anchor = the minting utterance
and nothing else - and whether each way of letting something else define it is caught.

`gw 2.0/OBLIGATION_IDENTITY.md` s9 (ruled 2026-09-14). Runs the build gate
(`tests/test_obligation_identity_fixture.py`) and then breaks the slice five ways:

    a bill mints                 encountering an artefact creates an obligation
    a descriptor appears         the anchor grows a creditor attribute
    a role rewrites the anchor   an entitled-party claim re-anchors the obligation to its own utterance
    retraction unmints           retracting the minting utterance deletes the obligation
    correspondence merges        establishing obligation_corresponds deletes the second row

"A missed payment records a transition" from the record's list is not constructible here: no payment
concept exists in the substrate, which is the point - asserted by the fixture rather than mutated.

Same shape as s86-s91: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_obligation_identity_fixture.py'
    spec = importlib.util.spec_from_file_location('test_obligation_identity_fixture', path)
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

    def bill_mints():
        def mint_from_bill(mapper, connection, target):
            if target.held and target.asserted_by_id is None:
                # "a bill arrived, so there must be a debt" - minted under whatever utterance exists
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                if u is not None:
                    connection.execute(db.Obligation.__table__.insert().values(minted_by_id=u.id))
        event.listen(db.Artefact, 'after_insert', mint_from_bill)
        return lambda: event.remove(db.Artefact, 'after_insert', mint_from_bill)

    def descriptor_appears():
        db.Obligation.creditor = None
        return lambda: delattr(db.Obligation, 'creditor')

    def role_rewrites_anchor():
        # the guard must go first, or the re-anchor is refused before it can be caught by the fixture
        models = [getattr(db, n) for n in db._IMMUTABLE_REFERENCES]
        for m in models:
            event.remove(m, 'before_update', db._refuse_repoint)

        def on_rel(mapper, connection, target):
            if target.utterance_id is None:
                return
            p = connection.execute(db.Proposition.__table__.select()
                                   .where(db.Proposition.__table__.c.id == target.proposition_id)).first()
            if p is not None and p.kind == 'entitled_party' and p.object_obligation_id is not None:
                t = db.Obligation.__table__
                connection.execute(t.update().where(t.c.id == p.object_obligation_id)
                                   .values(minted_by_id=target.utterance_id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', on_rel)

        def restore():
            event.remove(db.EvidentiaryRelationship, 'after_insert', on_rel)
            for m in models:
                event.listen(m, 'before_update', db._refuse_repoint)
        return restore

    def retraction_unmints():
        def unmint(mapper, connection, target):
            if target.kind == db.UTTERANCE_RETRACTION and target.subject_utterance_id is not None:
                t = db.Obligation.__table__
                connection.execute(t.delete().where(t.c.minted_by_id == target.subject_utterance_id))
        event.listen(db.Proposition, 'after_insert', unmint)
        return lambda: event.remove(db.Proposition, 'after_insert', unmint)

    def correspondence_merges():
        def merge(mapper, connection, target):
            if target.utterance_id is None:
                return
            p = connection.execute(db.Proposition.__table__.select()
                                   .where(db.Proposition.__table__.c.id == target.proposition_id)).first()
            if p is not None and p.kind == db.OBLIGATION_CORRESPONDS:
                t = db.Obligation.__table__
                connection.execute(t.delete().where(t.c.id == p.subject_obligation_id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', merge)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', merge)

    return [
        ('encountering a bill mints an obligation', bill_mints),
        ('a creditor descriptor appears on the anchor', descriptor_appears),
        ('an entitled-party claim re-anchors the obligation to its own utterance', role_rewrites_anchor),
        ('retracting the minting utterance unmints', retraction_unmints),
        ('establishing a correspondence merges the two obligations', correspondence_merges),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries the obligation anchor, its slots and obligation_corresponds',
          all(hasattr(db, n) for n in ('Obligation', 'OBLIGATION_CORRESPONDS', 'obligations_without_minting_utterance'))
          and 'subject_obligation_id' in db.Proposition.SUBJECT_SLOTS
          and 'Obligation' in db._CORRESPONDENCE_OF
          and {c.name for c in db.Obligation.__table__.columns} == {'id', 'minted_by_id', 'created_at'})

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the obligation-identity fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the obligation-identity fixture passes in full',
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
