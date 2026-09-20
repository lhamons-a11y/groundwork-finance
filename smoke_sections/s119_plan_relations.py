"""The three plan relations: E built by item 9 pass 9C exactly as accepted (s E.8 / s E.10, represented per s G.9) - and
whether each way of giving a plan relation a MEANING above its floor is caught.

`gw 2.0/CATALOGUES.md` s 9C (authorised s 9C.7, 2026-09-19). Runs the build gate (`tests/test_plan_relations_fixture.py`)
and then breaks the substrate ten ways, each an attempt to let membership, convergence, a document, the insurer's stance
or a structural shortcut supply what only a party's assertion may:

    which-plan from membership and date     X -> P minted from under_plan + incurred_by + occurred_on (E2 / E3 / E5)
    X -> P from a shared person             X -> P minted from under_plan + incurred_by alone (E24)
    O -> P through X                        X -> P + O -> X mints O -> P (E15)
    p -> P through O                        p -> O + O -> P mints p -> P (E18)
    an inverse appears                      plan_covers_expense registered (E10)
    withdrawn on denial                     the insurer's denial deletes X -> P (E8 reversed)
    a typed-slot merge                      in_respect_of_plan with three subject slots (PE8 / G.9)
    a which_plan resolver                   which_plan(session, expense) exposed (E2)
    a knowing relation designated           E's undetermined manufactured (knowing_relation set)
    a temporal guard                        p -> P refused when p precedes P (E22)

Same shape as s117 / s118: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_plan_relations_fixture.py'
    spec = importlib.util.spec_from_file_location('test_plan_relations_fixture', path)
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

    def _on_insert(fn):
        def hook(mapper, connection, target):
            fn(connection, target, db.Proposition.__table__)
        event.listen(db.Proposition, 'after_insert', hook)
        return lambda: event.remove(db.Proposition, 'after_insert', hook)

    def _insert(connection, P, kind, **slots):
        # a minted claim, evidenced (by the corpus's first utterance) so the consumers read it as any other established claim
        r = connection.execute(P.insert().values(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                                 as_of='2026-01-01', **slots))
        U = db.Utterance.__table__
        u = connection.execute(U.select().order_by(U.c.id)).fetchone()
        connection.execute(db.EvidentiaryRelationship.__table__.insert().values(proposition_id=r.inserted_primary_key[0], utterance_id=u.id))

    def _exists(connection, P, kind, **where):
        q = P.select().where(P.c.kind == kind)
        for k, v in where.items():
            q = q.where(getattr(P.c, k) == v)
        return connection.execute(q).fetchone() is not None

    def which_plan_from_membership():
        def mint(connection, target, P):
            # membership + incurred-by + a date on the expense -> the expense is put on the member's plan
            if target.kind == db.INCURRED_BY and target.object_expense_id is not None:
                for m in connection.execute(P.select().where(P.c.kind == db.UNDER_PLAN, P.c.subject_party_id == target.subject_party_id)).fetchall():
                    if not _exists(connection, P, db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=target.object_expense_id, object_plan_id=m.object_plan_id):
                        _insert(connection, P, db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=target.object_expense_id, object_plan_id=m.object_plan_id)
            if target.kind == 'occurred_on' and target.subject_expense_id is not None:
                for inc in connection.execute(P.select().where(P.c.kind == db.INCURRED_BY, P.c.object_expense_id == target.subject_expense_id)).fetchall():
                    for m in connection.execute(P.select().where(P.c.kind == db.UNDER_PLAN, P.c.subject_party_id == inc.subject_party_id)).fetchall():
                        if not _exists(connection, P, db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=target.subject_expense_id, object_plan_id=m.object_plan_id):
                            _insert(connection, P, db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=target.subject_expense_id, object_plan_id=m.object_plan_id)
        return _on_insert(mint)

    def x_to_p_from_shared_person():
        def mint(connection, target, P):
            if target.kind == db.UNDER_PLAN and target.subject_party_id is not None:
                for inc in connection.execute(P.select().where(P.c.kind == db.INCURRED_BY, P.c.subject_party_id == target.subject_party_id)).fetchall():
                    if not _exists(connection, P, db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=inc.object_expense_id, object_plan_id=target.object_plan_id):
                        _insert(connection, P, db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=inc.object_expense_id, object_plan_id=target.object_plan_id)
            if target.kind == db.INCURRED_BY and target.object_expense_id is not None:
                for m in connection.execute(P.select().where(P.c.kind == db.UNDER_PLAN, P.c.subject_party_id == target.subject_party_id)).fetchall():
                    if not _exists(connection, P, db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=target.object_expense_id, object_plan_id=m.object_plan_id):
                        _insert(connection, P, db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=target.object_expense_id, object_plan_id=m.object_plan_id)
        return _on_insert(mint)

    def o_to_p_through_x():
        def mint(connection, target, P):
            if target.kind == db.OBLIGATION_IN_RESPECT_OF and target.object_expense_id is not None:
                for xp in connection.execute(P.select().where(P.c.kind == db.EXPENSE_IN_RESPECT_OF_PLAN, P.c.subject_expense_id == target.object_expense_id)).fetchall():
                    _insert(connection, P, db.OBLIGATION_IN_RESPECT_OF_PLAN, subject_obligation_id=target.subject_obligation_id, object_plan_id=xp.object_plan_id)
        return _on_insert(mint)

    def p_to_p_through_o():
        def mint(connection, target, P):
            if target.kind == db.PAYMENT_IN_RESPECT_OF_OBLIGATION and target.object_obligation_id is not None:
                for op in connection.execute(P.select().where(P.c.kind == db.OBLIGATION_IN_RESPECT_OF_PLAN, P.c.subject_obligation_id == target.object_obligation_id)).fetchall():
                    _insert(connection, P, db.PAYMENT_IN_RESPECT_OF_PLAN, subject_payment_id=target.subject_payment_id, object_plan_id=op.object_plan_id)
        return _on_insert(mint)

    def inverse_appears():
        db.RULED_KINDS['plan_covers_expense'] = {'subject': ('subject_plan_id',), 'object': ('object_expense_id',), 'symmetric': False,
                                                'reading_establishes': False, 'relational_knowing': True}
        return lambda: db.RULED_KINDS.pop('plan_covers_expense', None)

    def withdrawn_on_denial():
        def mint(connection, target, P):
            if target.kind == 'adjudication' and target.subject_expense_id is not None and 'denied' in (target.content or ''):
                connection.execute(P.delete().where(P.c.kind == db.EXPENSE_IN_RESPECT_OF_PLAN, P.c.subject_expense_id == target.subject_expense_id))
        return _on_insert(mint)

    def typed_slot_merge():
        saved = {k: db.RULED_KINDS.pop(k) for k in (db.EXPENSE_IN_RESPECT_OF_PLAN, db.OBLIGATION_IN_RESPECT_OF_PLAN, db.PAYMENT_IN_RESPECT_OF_PLAN)}
        db.RULED_KINDS['in_respect_of_plan'] = {'subject': ('subject_expense_id', 'subject_obligation_id', 'subject_payment_id'), 'object': ('object_plan_id',),
                                                'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}

        def undo():
            db.RULED_KINDS.pop('in_respect_of_plan', None)
            db.RULED_KINDS.update(saved)
        return undo

    def which_plan_resolver():
        db.which_plan = lambda session, expense: None
        return lambda: delattr(db, 'which_plan')

    def knowing_designated():
        rule = db.RULED_KINDS[db.EXPENSE_IN_RESPECT_OF_PLAN]
        db.RULED_KINDS[db.EXPENSE_IN_RESPECT_OF_PLAN] = dict(rule, knowing_relation=db.KNOWING_ORIGIN_OF_SUBJECT_UTTERANCE)
        return lambda: db.RULED_KINDS.__setitem__(db.EXPENSE_IN_RESPECT_OF_PLAN, rule)

    def temporal_guard():
        from sqlalchemy import event as ev

        def guard(mapper, connection, target):
            if target.kind == db.PAYMENT_IN_RESPECT_OF_PLAN and target.subject_payment_id is not None and target.object_plan_id is not None:
                Pm, Pl, U = db.Payment.__table__, db.Plan.__table__, db.Utterance.__table__
                pay = connection.execute(Pm.select().where(Pm.c.id == target.subject_payment_id)).fetchone()
                plan = connection.execute(Pl.select().where(Pl.c.id == target.object_plan_id)).fetchone()
                up = connection.execute(U.select().where(U.c.id == pay.minted_by_id)).fetchone()
                ul = connection.execute(U.select().where(U.c.id == plan.minted_by_id)).fetchone()
                if target.as_of and 'January' in (ul.content or '') and target.as_of < '2027-01-01':
                    raise ValueError('a payment cannot be in respect of a plan that had not started')
        ev.listen(db.Proposition, 'before_insert', guard)
        return lambda: ev.remove(db.Proposition, 'before_insert', guard)

    return [
        ('which-plan from membership and date (E2 / E3 / E5)', which_plan_from_membership),
        ('X -> P from a shared person (E24)', x_to_p_from_shared_person),
        ('O -> P through X (E15)', o_to_p_through_x),
        ('p -> P through O (E18)', p_to_p_through_o),
        ('an inverse plan_covers_expense appears (E10)', inverse_appears),
        ('the relation withdrawn on the insurer\'s denial (E8 reversed)', withdrawn_on_denial),
        ('a typed-slot in_respect_of_plan merge (PE8 / G.9)', typed_slot_merge),
        ('a which_plan resolver appears (E2)', which_plan_resolver),
        ('a knowing relation designated (E: undetermined)', knowing_designated),
        ('a temporal guard on p -> P (E22)', temporal_guard),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    three = (db.EXPENSE_IN_RESPECT_OF_PLAN, db.OBLIGATION_IN_RESPECT_OF_PLAN, db.PAYMENT_IN_RESPECT_OF_PLAN)
    check('core/database.py carries the three plan relations exactly as accepted - one per pair, the plan the object, family flags, no knowing relation, no role, no boundary; six family members; the guard passing - and no inverse, resolver, composer or which-plan helper',
          all(db.RULED_KINDS[k] == {'subject': (sub,), 'object': ('object_plan_id',), 'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
              for k, sub in zip(three, ('subject_expense_id', 'subject_obligation_id', 'subject_payment_id')))
          and len([k for k in db.RULED_KINDS if 'in_respect_of' in k]) == 6 and db.registry_violations() == []
          and not any(k in db.RULED_KINDS for k in ('plan_covers_expense', 'plan_covers', 'covered_by', 'in_respect_of_plan', 'in_respect_of'))
          and not any(hasattr(db, n) for n in ('which_plan', 'plan_of_expense', 'coverage_of', 'plan_from_membership', 'resolve_in_respect_of', 'compose')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the plan relations fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the plan relations fixture passes in full',
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
        after, after_failures, after_err = _run_fixture(fx, db)
        check('restored after: ' + name,
              after == passed and not after_failures and not after_err)

    restored, restored_failures, restored_err = _run_fixture(fx, db)
    check('the module is left exactly as it was found',
          restored == passed and not restored_failures and not restored_err)
