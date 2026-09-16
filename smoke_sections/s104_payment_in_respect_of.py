"""payment_in_respect_of: the one ruled relation between a payment and an expense - a party's assertion that
the subject payment was in respect of the object expense, and nothing above that floor; direction fixed by
type, no inverse, no cardinality (and cardinality is not allocation), no amount, no payer/payee semantics,
no funding, no status on the expense, no temporal order, no composition with A / C / toward - and whether
each way of letting it is caught.

`gw 2.0/RELATION_SEMANTICS.md` pass D (ruled 2026-09-15). Runs the build gate
(`tests/test_payment_in_respect_of_fixture.py`) and then breaks the slice ten ways:

    the label establishes           the matcher's pairing acquires a party's assertion
    the expense gets a status       the Expense model grows a `paid` attribute
    the relation allocates          `allocation_of(payment)` is exposed
    the relation reconciles         `reconcile(expense)` is exposed
    the relation funds              `funder_of(expense)` reads the payer through the relation
    the phrase supplies order       a guard refuses the relation when the expense was minted after the payment (D21)
    the inverse is manufactured     the registry gains an expense -> payment kind
    the chain composes              payment_in_respect_of_obligation(p, O) + obligation_in_respect_of(O, X) inserts payment_in_respect_of(p, X)
    counteracts composes            payment_counteracts(p2, p1) + p1 in respect of X inserts p2 in respect of X
    the kind turns symmetric        the registry entry flips symmetric True

Same shape as s103: fixture passes, every mutation is caught, the baseline is re-established after every
undo, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_payment_in_respect_of_fixture.py'
    spec = importlib.util.spec_from_file_location('test_payment_in_respect_of_fixture', path)
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
    PAY, X = db.Payment.__table__, db.Expense.__table__

    def label_establishes():
        def manufacture(mapper, connection, target):
            if target.reading_id is None:
                return
            p = connection.execute(P.select().where(P.c.id == target.proposition_id)).first()
            if p is not None and p.kind == db.PAYMENT_IN_RESPECT_OF:
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                connection.execute(E.insert().values(proposition_id=p.id, utterance_id=u.id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', manufacture)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', manufacture)

    def expense_gets_status():
        db.Expense.paid = None
        return lambda: delattr(db.Expense, 'paid')

    def relation_allocates():
        db.allocation_of = lambda session, payment: {}
        return lambda: delattr(db, 'allocation_of')

    def relation_reconciles():
        db.reconcile = lambda session, expense: None
        return lambda: delattr(db, 'reconcile')

    def relation_funds():
        db.funder_of = lambda session, expense: None
        return lambda: delattr(db, 'funder_of')

    def phrase_supplies_order():
        def refuse_out_of_order(mapper, connection, target):
            if target.kind != db.PAYMENT_IN_RESPECT_OF or not target.subject_payment_id or not target.object_expense_id:
                return
            p = connection.execute(PAY.select().where(PAY.c.id == target.subject_payment_id)).first()
            x = connection.execute(X.select().where(X.c.id == target.object_expense_id)).first()
            if p is not None and x is not None and x.created_at > p.created_at:
                raise ValueError('an expense must precede a payment in respect of it')
        event.listen(db.Proposition, 'before_insert', refuse_out_of_order)
        return lambda: event.remove(db.Proposition, 'before_insert', refuse_out_of_order)

    def inverse_manufactured():
        db.RULED_KINDS['expense_paid_by'] = {'subject': ('subject_expense_id',), 'object': ('object_payment_id',),
                                            'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
        return lambda: db.RULED_KINDS.pop('expense_paid_by', None)

    def chain_composes():
        def compose(mapper, connection, target):
            if target.kind != db.PAYMENT_IN_RESPECT_OF_OBLIGATION or not target.subject_payment_id or not target.object_obligation_id:
                return
            for r in connection.execute(P.select().where(P.c.kind == db.OBLIGATION_IN_RESPECT_OF,
                                                          P.c.subject_obligation_id == target.object_obligation_id)).fetchall():
                connection.execute(P.insert().values(
                    kind=db.PAYMENT_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                    subject_payment_id=target.subject_payment_id, object_expense_id=r.object_expense_id))
        event.listen(db.Proposition, 'after_insert', compose)
        return lambda: event.remove(db.Proposition, 'after_insert', compose)

    def counteracts_composes():
        def compose(mapper, connection, target):
            if target.kind != db.PAYMENT_COUNTERACTS or not target.subject_payment_id or not target.object_payment_id:
                return
            for r in connection.execute(P.select().where(P.c.kind == db.PAYMENT_IN_RESPECT_OF,
                                                          P.c.subject_payment_id == target.object_payment_id)).fetchall():
                connection.execute(P.insert().values(
                    kind=db.PAYMENT_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                    subject_payment_id=target.subject_payment_id, object_expense_id=r.object_expense_id))
        event.listen(db.Proposition, 'after_insert', compose)
        return lambda: event.remove(db.Proposition, 'after_insert', compose)

    def kind_turns_symmetric():
        rule = db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF]
        db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF] = dict(rule, symmetric=True)
        return lambda: db.RULED_KINDS.__setitem__(db.PAYMENT_IN_RESPECT_OF, rule)

    return [
        ("the matcher's pairing acquires a party's assertion", label_establishes),
        ('the expense gets a paid status', expense_gets_status),
        ('the relation allocates', relation_allocates),
        ('the relation reconciles amounts', relation_reconciles),
        ('the relation names a funder', relation_funds),
        ('the phrase supplies temporal order (D21)', phrase_supplies_order),
        ('the inverse kind is manufactured', inverse_manufactured),
        ('the chain composes through the obligation', chain_composes),
        ('payment_counteracts composes into the relation', counteracts_composes),
        ('the kind turns symmetric', kind_turns_symmetric),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries payment_in_respect_of exactly as authorised and nothing at family level',
          hasattr(db, 'PAYMENT_IN_RESPECT_OF')
          and db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF] == {'subject': ('subject_payment_id',), 'object': ('object_expense_id',),
                                                            'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
          and 'toward' not in db.RULED_KINDS
          and not any(hasattr(db, n) for n in ('Relation', 'RelationBase', 'relation_resolver', 'allocation_of', 'reconcile',
                                               'funder_of', 'payments_for_expense', 'expense_paid_by')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the payment-in-respect-of fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the payment-in-respect-of fixture passes in full',
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
        # The baseline is re-established after EVERY undo, not only at the end - an incomplete undo
        # is attributed to the mutation that left it.
        after, after_failures, after_err = _run_fixture(fx, db)
        check('restored after: ' + name,
              after == passed and not after_failures and not after_err)

    restored, restored_failures, restored_err = _run_fixture(fx, db)
    check('the module is left exactly as it was found',
          restored == passed and not restored_failures and not restored_err)
