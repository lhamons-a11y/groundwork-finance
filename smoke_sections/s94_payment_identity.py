"""Payment identity: the payment event individuated by a Person's assertion that it occurred - and whether
each way of letting something else define it is caught.

`gw 2.0/PAYMENT_IDENTITY.md` s10 (ruled 2026-09-14). Runs the build gate
(`tests/test_payment_identity_fixture.py`) and then breaks the slice six ways:

    a bank line mints                 a read claim in the candidates state mints a payment
    E's statement mints               the Person requirement on the minting utterance is dropped
    a descriptor appears              the anchor grows a payee attribute
    acknowledgment moves something    a discharge accessor / confirmed state appears (item 7 pass 7G built the read-only
                                      remaining(); the mutation is now the accessor that would make discharge a status)
    cleared establishes acknowledged  a bank's cleared claim manufactures E's acknowledgment
    correspondence merges             establishing payment_corresponds deletes the second row

Same shape as s86-s93: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_payment_identity_fixture.py'
    spec = importlib.util.spec_from_file_location('test_payment_identity_fixture', path)
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
    P, E, PM = db.Proposition.__table__, db.EvidentiaryRelationship.__table__, db.Payment.__table__

    def bank_line_mints():
        def on_candidate(mapper, connection, target):
            if target.kind == db.MOVEMENT:   # the bank line's own kind (BANK_LINE_KIND.md): a movement line minting a payment
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                if u is not None:
                    connection.execute(PM.insert().values(minted_by_id=u.id))
        event.listen(db.Proposition, 'after_insert', on_candidate)
        return lambda: event.remove(db.Proposition, 'after_insert', on_candidate)

    def institution_mints():
        orig = db._minting_violations

        def existence_only(target, connection, noun):
            return [v for v in orig(target, connection, noun) if 'Person' not in v]
        db._minting_violations = existence_only
        return lambda: setattr(db, '_minting_violations', orig)

    def descriptor_appears():
        db.Payment.payee = None
        return lambda: delattr(db.Payment, 'payee')

    def acknowledgment_moves_something():
        # 7G's remaining() exists by ruling and is not the mutation; a discharge accessor is
        def is_discharged(session, payment):
            return True
        db.is_discharged = is_discharged
        return lambda: delattr(db, 'is_discharged')

    def cleared_establishes_acknowledged():
        def on_cleared(mapper, connection, target):
            if target.reading_id is None:
                return
            p = connection.execute(P.select().where(P.c.id == target.proposition_id)).first()
            if p is None or p.kind != 'cleared' or p.subject_payment_id is None:
                return
            # "the bank shows it cleared, so the creditor must have it" - E's claim manufactured
            party = connection.execute(db.Party.__table__.select().where(db.Party.__table__.c.person_id.is_(None)).limit(1)).first()
            res = connection.execute(P.insert().values(kind='acknowledged', subject_state=db.PARTICIPANT_ESTABLISHED,
                                                       subject_party_id=party.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                                       object_payment_id=p.subject_payment_id, as_of=p.as_of))
            connection.execute(E.insert().values(proposition_id=res.inserted_primary_key[0], reading_id=target.reading_id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', on_cleared)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', on_cleared)

    def correspondence_merges():
        def merge(mapper, connection, target):
            if target.utterance_id is None:
                return
            p = connection.execute(P.select().where(P.c.id == target.proposition_id)).first()
            if p is not None and p.kind == db.PAYMENT_CORRESPONDS:
                connection.execute(PM.delete().where(PM.c.id == p.subject_payment_id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', merge)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', merge)

    return [
        ('a bank line mints a payment', bank_line_mints),
        ('an institution-origin utterance mints a payment', institution_mints),
        ('a payee descriptor appears on the anchor', descriptor_appears),
        ('acknowledgment moves something - a discharge accessor appears', acknowledgment_moves_something),
        ('a cleared flag manufactures the creditor\'s acknowledgment', cleared_establishes_acknowledged),
        ('establishing a correspondence merges the two payments', correspondence_merges),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries the payment anchor, its slots, payment_corresponds and the Person minting guard',
          all(hasattr(db, n) for n in ('Payment', 'PAYMENT_CORRESPONDS', 'payments_without_minting_utterance',
                                       '_minting_violations'))
          and 'subject_payment_id' in db.Proposition.SUBJECT_SLOTS and 'Payment' in db._CORRESPONDENCE_OF
          and {c.name for c in db.Payment.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and 'object_payment_id' in db.RULED_KINDS[db.ARTEFACT_CONCERNS]['object'])

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the payment-identity fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the payment-identity fixture passes in full',
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
