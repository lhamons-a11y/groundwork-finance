"""obligation_in_respect_of: the one ruled relation between an obligation and an expense - a party's assertion
that the subject obligation is in respect of the object expense, and nothing above that floor; direction
fixed by type, no inverse, no cardinality, no amount, no reconciliation, no projection of expense facts onto
the obligation, no temporal order - and whether each way of letting it is caught.

`gw 2.0/RELATION_SEMANTICS.md` pass C (ruled 2026-09-15). Runs the build gate
(`tests/test_obligation_in_respect_of_fixture.py`) and then breaks the slice nine ways:

    the label establishes           the matcher's pairing acquires a party's assertion
    expense facts project onto O    the Obligation model grows a `nature` attribute
    a resolver appears              `underlying_expense(obligation)` is exposed
    the relation reconciles         `corresponding_amount(obligation)` is exposed
    the phrase supplies order       a guard refuses the relation when the expense was minted after the obligation (C7)
    the inverse is manufactured     the registry gains an expense -> obligation kind
    PR mints the obligation         a patient-responsibility claim above $0 inserts an Obligation
    about-ness derives it           a bill concerning both O and X inserts the relation
    the kind turns symmetric        the registry entry flips symmetric True

Same shape as s86-s102: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_obligation_in_respect_of_fixture.py'
    spec = importlib.util.spec_from_file_location('test_obligation_in_respect_of_fixture', path)
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
    O, X = db.Obligation.__table__, db.Expense.__table__

    def label_establishes():
        def manufacture(mapper, connection, target):
            if target.reading_id is None:
                return
            p = connection.execute(P.select().where(P.c.id == target.proposition_id)).first()
            if p is not None and p.kind == db.OBLIGATION_IN_RESPECT_OF:
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                connection.execute(E.insert().values(proposition_id=p.id, utterance_id=u.id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', manufacture)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', manufacture)

    def facts_project():
        db.Obligation.nature = None
        return lambda: delattr(db.Obligation, 'nature')

    def resolver_appears():
        db.underlying_expense = lambda session, obligation: None
        return lambda: delattr(db, 'underlying_expense')

    def relation_reconciles():
        db.corresponding_amount = lambda session, obligation: None
        return lambda: delattr(db, 'corresponding_amount')

    def phrase_supplies_order():
        def refuse_out_of_order(mapper, connection, target):
            if target.kind != db.OBLIGATION_IN_RESPECT_OF or not target.subject_obligation_id or not target.object_expense_id:
                return
            o = connection.execute(O.select().where(O.c.id == target.subject_obligation_id)).first()
            x = connection.execute(X.select().where(X.c.id == target.object_expense_id)).first()
            if o is not None and x is not None and x.created_at > o.created_at:
                raise ValueError('an expense must precede the obligation in respect of it')
        event.listen(db.Proposition, 'before_insert', refuse_out_of_order)
        return lambda: event.remove(db.Proposition, 'before_insert', refuse_out_of_order)

    def inverse_manufactured():
        db.RULED_KINDS['expense_has_obligation'] = {'subject': ('subject_expense_id',), 'object': ('object_obligation_id',),
                                                   'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
        return lambda: db.RULED_KINDS.pop('expense_has_obligation', None)

    def pr_mints():
        def mint(mapper, connection, target):
            if target.kind == 'patient_responsibility' and target.subject_expense_id and (target.content or '') not in ('', '$0'):
                x = connection.execute(X.select().where(X.c.id == target.subject_expense_id)).first()
                connection.execute(O.insert().values(minted_by_id=x.minted_by_id))
        event.listen(db.Proposition, 'after_insert', mint)
        return lambda: event.remove(db.Proposition, 'after_insert', mint)

    def aboutness_derives():
        def derive(mapper, connection, target):
            if target.kind != db.ARTEFACT_CONCERNS or not target.subject_artefact_id:
                return
            rows = connection.execute(P.select().where(P.c.kind == db.ARTEFACT_CONCERNS,
                                                       P.c.subject_artefact_id == target.subject_artefact_id)).fetchall()
            os_ = {r.object_obligation_id for r in rows if r.object_obligation_id} | ({target.object_obligation_id} if target.object_obligation_id else set())
            xs = {r.object_expense_id for r in rows if r.object_expense_id} | ({target.object_expense_id} if target.object_expense_id else set())
            for o in os_:
                for x in xs:
                    connection.execute(P.insert().values(
                        kind=db.OBLIGATION_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                        subject_obligation_id=o, object_expense_id=x))
        event.listen(db.Proposition, 'after_insert', derive)
        return lambda: event.remove(db.Proposition, 'after_insert', derive)

    def kind_turns_symmetric():
        rule = db.RULED_KINDS[db.OBLIGATION_IN_RESPECT_OF]
        db.RULED_KINDS[db.OBLIGATION_IN_RESPECT_OF] = dict(rule, symmetric=True)
        return lambda: db.RULED_KINDS.__setitem__(db.OBLIGATION_IN_RESPECT_OF, rule)

    return [
        ("the matcher's pairing acquires a party's assertion", label_establishes),
        ('expense facts project onto the obligation', facts_project),
        ('a resolver selects the underlying expense', resolver_appears),
        ('the relation reconciles amounts', relation_reconciles),
        ('the phrase supplies temporal order (C7)', phrase_supplies_order),
        ('the inverse kind is manufactured', inverse_manufactured),
        ('patient responsibility mints the obligation', pr_mints),
        ('about-ness derives the relation', aboutness_derives),
        ('the kind turns symmetric', kind_turns_symmetric),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries obligation_in_respect_of exactly as authorised and nothing at family level',
          hasattr(db, 'OBLIGATION_IN_RESPECT_OF')
          and db.RULED_KINDS[db.OBLIGATION_IN_RESPECT_OF] == {'subject': ('subject_obligation_id',), 'object': ('object_expense_id',),
                                                               'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
          and not any(hasattr(db, n) for n in ('Relation', 'RelationBase', 'relation_resolver', 'underlying_expense',
                                               'corresponding_amount', 'arises_from', 'obligations_of_expense')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the obligation-in-respect-of fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the obligation-in-respect-of fixture passes in full',
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
