"""payment_counteracts: the one ruled relation between two payments - a party's assertion that the subject
economically counteracts some or all of the object; directional, no inverse, no cardinality, no amount, no
status, no netting, no transitivity - and whether each way of letting it is caught.

`gw 2.0/RELATION_SEMANTICS.md` pass A (ruled 2026-09-15). Runs the build gate
(`tests/test_payment_counteracts_fixture.py`) and then breaks the slice six ways:

    the label establishes           a REFUND line manufactures a party's counteracts assertion
    the relation becomes a status   the Payment model grows a `reversed` attribute
    the inverse is manufactured     asserting p2 counteracts p1 also inserts p1 counteracts p2
    transitivity slips in           p3 counteracts p2 inserts p3 counteracts p1
    a netting helper appears        `net_of(payment)` is exposed
    the kind turns symmetric        the registry entry flips symmetric True

Same shape as s86-s100: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_payment_counteracts_fixture.py'
    spec = importlib.util.spec_from_file_location('test_payment_counteracts_fixture', path)
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

    def label_establishes():
        def manufacture(mapper, connection, target):
            if target.reading_id is None:
                return
            p = connection.execute(P.select().where(P.c.id == target.proposition_id)).first()
            if p is not None and p.kind == db.PAYMENT_COUNTERACTS:
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                connection.execute(E.insert().values(proposition_id=p.id, utterance_id=u.id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', manufacture)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', manufacture)

    def relation_becomes_status():
        db.Payment.reversed = None
        return lambda: delattr(db.Payment, 'reversed')

    def inverse_manufactured():
        def invert(mapper, connection, target):
            if target.kind == db.PAYMENT_COUNTERACTS and target.subject_payment_id and target.object_payment_id:
                connection.execute(P.insert().values(
                    kind=db.PAYMENT_COUNTERACTS, subject_state=target.subject_state, object_state=target.object_state,
                    subject_payment_id=target.object_payment_id, object_payment_id=target.subject_payment_id))
        event.listen(db.Proposition, 'after_insert', invert)
        return lambda: event.remove(db.Proposition, 'after_insert', invert)

    def transitivity_slips_in():
        def chain(mapper, connection, target):
            if target.kind != db.PAYMENT_COUNTERACTS or not target.object_payment_id:
                return
            for prior in connection.execute(P.select().where(P.c.kind == db.PAYMENT_COUNTERACTS,
                                                              P.c.subject_payment_id == target.object_payment_id)).fetchall():
                connection.execute(P.insert().values(
                    kind=db.PAYMENT_COUNTERACTS, subject_state=target.subject_state, object_state=target.object_state,
                    subject_payment_id=target.subject_payment_id, object_payment_id=prior.object_payment_id))
        event.listen(db.Proposition, 'after_insert', chain)
        return lambda: event.remove(db.Proposition, 'after_insert', chain)

    def netting_helper():
        db.net_of = lambda session, payment: 0
        return lambda: delattr(db, 'net_of')

    def kind_turns_symmetric():
        rule = db.RULED_KINDS[db.PAYMENT_COUNTERACTS]
        db.RULED_KINDS[db.PAYMENT_COUNTERACTS] = dict(rule, symmetric=True)
        return lambda: db.RULED_KINDS.__setitem__(db.PAYMENT_COUNTERACTS, rule)

    return [
        ('a REFUND line manufactures a party\'s counteracts assertion', label_establishes),
        ('the relation becomes a payment status', relation_becomes_status),
        ('the inverse relation is manufactured', inverse_manufactured),
        ('transitivity slips in along the chain', transitivity_slips_in),
        ('a netting helper appears', netting_helper),
        ('the kind turns symmetric', kind_turns_symmetric),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries payment_counteracts exactly as authorised and nothing at family level',
          hasattr(db, 'PAYMENT_COUNTERACTS')
          and db.RULED_KINDS[db.PAYMENT_COUNTERACTS] == {'subject': ('subject_payment_id',), 'object': ('object_payment_id',),
                                                          'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
          and not any(hasattr(db, n) for n in ('Relation', 'RelationBase', 'relation_resolver', 'net_of', 'counteracted_by')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the payment-counteracts fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the payment-counteracts fixture passes in full',
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
