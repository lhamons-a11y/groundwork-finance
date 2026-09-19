"""The role catalogue: the seven ruled role kinds of item 9 pass 9B exactly as ruled (s 9B.7) - and whether each way of
giving a role a MEANING beyond its three points is caught.

`gw 2.0/CATALOGUES.md` s 9B (2026-09-19). Runs the build gate (`tests/test_role_catalogue_fixture.py`) and then breaks the
substrate ten ways, each an attempt to let one role stand in for another, a document or a default supply the occupant,
a boundary or a behaviour attach where the ruling bound none, or a governing determination arrive early:

    payee = entitled                 paid_to minted as entitled_party_of (S1 / S6 collapsed)
    servicer = entitled              a servicer's began claim minted as the entitled party's (S4 / S5 collapsed)
    a reading establishes a role     reading_establishes flipped on entitled_party_of (Ro13)
    a household-default payer        a payment without a payer gets the household as paid_by (Pm9)
    the provider from letterhead     a held artefact's origin becomes provider_of (Ro13 / Ex1)
    insurer of X from the plan       insurer_of_plan + under_plan mints insurer_of for the expense (Ic4 / F14)
    a holds-only role gets bounds    provider_of_began appears (RB-a)
    knowing = the household          KNOWING_SUBJECT_PARTY resolves to the asserter (Kn7 / Ro8)
    a non-role passes in_effect      the role classification dropped from in_effect (9B-F1)
    governing PR appears             a resolver over insurer_of claims (9B-F2) - the one thing 9B must not carry

Same shape as s100 / s117: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_role_catalogue_fixture.py'
    spec = importlib.util.spec_from_file_location('test_role_catalogue_fixture', path)
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

    def _mint_on_insert(fn):
        def hook(mapper, connection, target):
            fn(connection, target, db.Proposition.__table__)
        event.listen(db.Proposition, 'after_insert', hook)
        return lambda: event.remove(db.Proposition, 'after_insert', hook)

    def _insert(connection, P, kind, party_id, as_of='2026-01-01', **obj):
        # a minted claim, evidenced (by the corpus's first utterance) so the consumers read it as any other established claim
        r = connection.execute(P.insert().values(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                                 subject_party_id=party_id, as_of=as_of, **obj))
        U = db.Utterance.__table__
        u = connection.execute(U.select().order_by(U.c.id)).fetchone()
        connection.execute(db.EvidentiaryRelationship.__table__.insert().values(proposition_id=r.inserted_primary_key[0], utterance_id=u.id))

    def payee_is_entitled():
        def mint(connection, target, P):
            if target.kind == db.PAID_TO and target.subject_party_id is not None:
                for ob in connection.execute(P.select().where(P.c.kind == db.PAYMENT_IN_RESPECT_OF_OBLIGATION, P.c.subject_payment_id == target.object_payment_id)).fetchall():
                    _insert(connection, P, db.ENTITLED_PARTY_OF, target.subject_party_id, object_obligation_id=ob.object_obligation_id)
                # the payee of the first payment in the corpus is taken as the entitled party of every obligation the payee services
                for sv in connection.execute(P.select().where(P.c.kind == db.SERVICER_OF, P.c.subject_party_id == target.subject_party_id)).fetchall():
                    _insert(connection, P, db.ENTITLED_PARTY_OF, target.subject_party_id, object_obligation_id=sv.object_obligation_id)
        return _mint_on_insert(mint)

    def servicer_is_entitled():
        def mint(connection, target, P):
            if target.kind == db.SERVICER_OF_BEGAN and target.subject_party_id is not None:
                _insert(connection, P, db.ENTITLED_PARTY_OF_BEGAN, target.subject_party_id, as_of=target.as_of, object_obligation_id=target.object_obligation_id)
        return _mint_on_insert(mint)

    def reading_establishes_role():
        rule = db.RULED_KINDS[db.ENTITLED_PARTY_OF]
        db.RULED_KINDS[db.ENTITLED_PARTY_OF] = dict(rule, reading_establishes=True)
        return lambda: db.RULED_KINDS.__setitem__(db.ENTITLED_PARTY_OF, rule)

    def household_default_payer():
        def mint(connection, target, P):
            if target.kind == db.PAID_TO and target.object_payment_id is not None:
                payer = connection.execute(P.select().where(P.c.kind == db.PAID_BY, P.c.object_payment_id == target.object_payment_id)).fetchone()
                if payer is None:
                    ut = connection.execute(db.Payment.__table__.select().where(db.Payment.__table__.c.id == target.object_payment_id)).fetchone()
                    u = connection.execute(db.Utterance.__table__.select().where(db.Utterance.__table__.c.id == ut.minted_by_id)).fetchone()
                    _insert(connection, P, db.PAID_BY, u.origin_party_id, object_payment_id=target.object_payment_id)
        return _mint_on_insert(mint)

    def provider_from_letterhead():
        def mint(connection, target, P):
            if target.kind == db.ARTEFACT_ORIGIN and target.object_party_id is not None:
                for x in connection.execute(db.Expense.__table__.select()).fetchall():
                    _insert(connection, P, db.PROVIDER_OF, target.object_party_id, object_expense_id=x.id)
        return _mint_on_insert(mint)

    def insurer_of_x_from_plan():
        def mint(connection, target, P):
            if target.kind == db.INSURER_OF_PLAN and target.subject_party_id is not None:
                for m in connection.execute(P.select().where(P.c.kind == db.UNDER_PLAN, P.c.object_plan_id == target.object_plan_id)).fetchall():
                    for inc in connection.execute(P.select().where(P.c.kind == db.INCURRED_BY, P.c.subject_party_id == m.subject_party_id)).fetchall():
                        _insert(connection, P, db.INSURER_OF, target.subject_party_id, object_expense_id=inc.object_expense_id)
                # and with no membership recorded, the plan's insurer is taken as the insurer of every expense
                for x in connection.execute(db.Expense.__table__.select()).fetchall():
                    _insert(connection, P, db.INSURER_OF, target.subject_party_id, object_expense_id=x.id)
        return _mint_on_insert(mint)

    def holds_only_role_bounded():
        rule = db.RULED_KINDS[db.PROVIDER_OF]
        db.RULED_KINDS['provider_of_began'] = dict(rule, boundary='began', of=db.PROVIDER_OF)
        return lambda: db.RULED_KINDS.pop('provider_of_began')

    def knowing_is_the_household():
        real = db._KNOWING_RELATIONS[db.KNOWING_SUBJECT_PARTY]

        def asserter(session, prop):
            rel = session.query(db.EvidentiaryRelationship).filter_by(proposition_id=prop.id).first()
            u = session.get(db.Utterance, rel.utterance_id) if rel is not None and rel.utterance_id is not None else None
            return u.origin_party_id if u is not None else None
        db._KNOWING_RELATIONS[db.KNOWING_SUBJECT_PARTY] = asserter
        return lambda: db._KNOWING_RELATIONS.__setitem__(db.KNOWING_SUBJECT_PARTY, real)

    def non_role_passes_in_effect():
        rule = db.RULED_KINDS[db.OBLIGATION_IN_RESPECT_OF]
        db.RULED_KINDS[db.OBLIGATION_IN_RESPECT_OF] = dict(rule, role=True)
        return lambda: db.RULED_KINDS.__setitem__(db.OBLIGATION_IN_RESPECT_OF, rule)

    def governing_pr_appears():
        db.governing_insurer = lambda session, expense, d: None
        return lambda: delattr(db, 'governing_insurer')

    return [
        ('payee = entitled (paid_to mints entitled_party_of)', payee_is_entitled),
        ('servicer = entitled (a servicer began mints the entitled party\'s began)', servicer_is_entitled),
        ('a reading establishes a role (reading_establishes flipped)', reading_establishes_role),
        ('a household-default payer (Pm9)', household_default_payer),
        ('the provider from the letterhead (a held artefact\'s origin becomes provider_of)', provider_from_letterhead),
        ('insurer of the expense from the plan (Ic4 / F14)', insurer_of_x_from_plan),
        ('boundaries bound to a holds-only role (RB-a)', holds_only_role_bounded),
        ('the knowing relation resolves to the asserter (Kn7)', knowing_is_the_household),
        ('a non-role relation passes in_effect (9B-F1)', non_role_passes_in_effect),
        ('a governing-PR resolver appears (9B-F2)', governing_pr_appears),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    roles = {k for k, r in db.RULED_KINDS.items() if r.get('role')}
    check('core/database.py carries the role catalogue exactly as ruled - nine role kinds marked, the seven of 9B knowing by the subject party, boundaries bound to the three that transition only, the guard passing - and no selector, default or governing resolver',
          roles == {db.UNDER_PLAN, db.ENTITLED_PARTY_OF, db.SERVICER_OF, db.PROVIDER_OF, db.INSURER_OF, db.INSURER_OF_PLAN, db.INCURRED_BY, db.PAID_BY, db.PAID_TO}
          and all(db.RULED_KINDS[k].get('knowing_relation') == db.KNOWING_SUBJECT_PARTY for k in roles - {db.UNDER_PLAN})
          and {r['of'] for r in db.RULED_KINDS.values() if r.get('boundary')} == {db.UNDER_PLAN, db.ENTITLED_PARTY_OF, db.SERVICER_OF}
          and db.registry_violations() == []
          and not any(hasattr(db, n) for n in ('entitled_party', 'current_servicer', 'default_payer', 'household_payer', 'governing_pr', 'governing_insurer', 'primary_insurer', 'latest_insurer', 'roles_of')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the role catalogue fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the role catalogue fixture passes in full',
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
