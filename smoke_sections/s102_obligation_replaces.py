"""obligation_replaces: the one ruled relation between two obligations - a party's assertion that the subject
was incurred in substitution for some or all of the object; directional, no inverse, no cardinality, no
amount, no transfer semantics, no status, no discharge, no transitivity - and whether each way of letting
it is caught.

`gw 2.0/RELATION_SEMANTICS.md` pass B (ruled 2026-09-15). Runs the build gate
(`tests/test_obligation_replaces_fixture.py`) and then breaks the slice eight ways:

    the label establishes           a PAYOFF line manufactures a party's replaces assertion
    the relation becomes a status   the Obligation model grows a `replaced` attribute
    the inverse is manufactured     asserting O3 replaces O1 also inserts O1 replaces O3
    transitivity slips in           O5 replaces O3 inserts O5 replaces O1
    discharge is derived            `discharged_by(obligation)` is exposed
    the money is explained          `carried_into(obligation)` - a disposition helper - is exposed
    the Ob6 arm is inferred         a terms claim on an obligation mints a successor and relates it
    the kind turns symmetric        the registry entry flips symmetric True

Same shape as s86-s101: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_obligation_replaces_fixture.py'
    spec = importlib.util.spec_from_file_location('test_obligation_replaces_fixture', path)
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
    P, E, O = db.Proposition.__table__, db.EvidentiaryRelationship.__table__, db.Obligation.__table__

    def label_establishes():
        def manufacture(mapper, connection, target):
            if target.reading_id is None:
                return
            p = connection.execute(P.select().where(P.c.id == target.proposition_id)).first()
            if p is not None and p.kind == db.OBLIGATION_REPLACES:
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                connection.execute(E.insert().values(proposition_id=p.id, utterance_id=u.id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', manufacture)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', manufacture)

    def relation_becomes_status():
        db.Obligation.replaced = None
        return lambda: delattr(db.Obligation, 'replaced')

    def inverse_manufactured():
        def invert(mapper, connection, target):
            if target.kind == db.OBLIGATION_REPLACES and target.subject_obligation_id and target.object_obligation_id:
                connection.execute(P.insert().values(
                    kind=db.OBLIGATION_REPLACES, subject_state=target.subject_state, object_state=target.object_state,
                    subject_obligation_id=target.object_obligation_id, object_obligation_id=target.subject_obligation_id))
        event.listen(db.Proposition, 'after_insert', invert)
        return lambda: event.remove(db.Proposition, 'after_insert', invert)

    def transitivity_slips_in():
        def chain(mapper, connection, target):
            if target.kind != db.OBLIGATION_REPLACES or not target.object_obligation_id:
                return
            for prior in connection.execute(P.select().where(P.c.kind == db.OBLIGATION_REPLACES,
                                                              P.c.subject_obligation_id == target.object_obligation_id)).fetchall():
                connection.execute(P.insert().values(
                    kind=db.OBLIGATION_REPLACES, subject_state=target.subject_state, object_state=target.object_state,
                    subject_obligation_id=target.subject_obligation_id, object_obligation_id=prior.object_obligation_id))
        event.listen(db.Proposition, 'after_insert', chain)
        return lambda: event.remove(db.Proposition, 'after_insert', chain)

    def discharge_derived():
        db.discharged_by = lambda session, obligation: None
        return lambda: delattr(db, 'discharged_by')

    def money_explained():
        db.carried_into = lambda session, obligation: []
        return lambda: delattr(db, 'carried_into')

    def arm_inferred():
        def successor(mapper, connection, target):
            # "new terms => a new obligation that replaced the old" - the substrate choosing the Ob6 arm
            if target.kind != 'terms' or not target.subject_obligation_id:
                return
            old = connection.execute(O.select().where(O.c.id == target.subject_obligation_id)).first()
            new_id = connection.execute(O.insert().values(minted_by_id=old.minted_by_id)).inserted_primary_key[0]
            connection.execute(P.insert().values(
                kind=db.OBLIGATION_REPLACES, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                subject_obligation_id=new_id, object_obligation_id=old.id))
        event.listen(db.Proposition, 'after_insert', successor)
        return lambda: event.remove(db.Proposition, 'after_insert', successor)

    def kind_turns_symmetric():
        rule = db.RULED_KINDS[db.OBLIGATION_REPLACES]
        db.RULED_KINDS[db.OBLIGATION_REPLACES] = dict(rule, symmetric=True)
        return lambda: db.RULED_KINDS.__setitem__(db.OBLIGATION_REPLACES, rule)

    return [
        ('a PAYOFF line manufactures a party\'s replaces assertion', label_establishes),
        ('the relation becomes an obligation status', relation_becomes_status),
        ('the inverse relation is manufactured', inverse_manufactured),
        ('transitivity slips in along the chain', transitivity_slips_in),
        ('discharge is derived from the relation', discharge_derived),
        ('a disposition helper explains where the money went', money_explained),
        ('the Ob6 arm is inferred - a terms claim mints a successor', arm_inferred),
        ('the kind turns symmetric', kind_turns_symmetric),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries obligation_replaces exactly as authorised and nothing at family level',
          hasattr(db, 'OBLIGATION_REPLACES')
          and db.RULED_KINDS[db.OBLIGATION_REPLACES] == {'subject': ('subject_obligation_id',), 'object': ('object_obligation_id',),
                                                          'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
          and not any(hasattr(db, n) for n in ('Relation', 'RelationBase', 'relation_resolver', 'discharged_by', 'carried_into',
                                               'replaced_by', 'successor_of')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the obligation-replaces fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the obligation-replaces fixture passes in full',
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
