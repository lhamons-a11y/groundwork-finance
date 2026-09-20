"""Values and the bank: built by item 9 pass 9D-iv exactly as ruled (s 9D-iv.7) - and whether each way of letting the
minter, a type, a date, the attachment or a stranger confer knowing for a value, or letting the bank's stance move a
consumer, is caught.

`gw 2.0/CATALOGUES.md` s 9D-iv (2026-09-20). Runs the build gate (`tests/test_value_kinds_fixture.py`) and then breaks
the substrate ten ways:

    the minter knowing                    the role-set includes the minter (Kn7 reversed)
    the type conferring knowing           the foundation stand-in restored for the value kinds
    the role-set read at a date           an undated amount undetermined (the value treated as a position)
    a stranger knowing                    the set ignored - any party knowing
    the bank without its role             drawn_on dropped from the payment set (F2 reversed)
    cleared moves 7G's station            a cleared stance read as acknowledgment (K6 reversed)
    a reading establishes state           a reading-sourced value reads as established
    the attachment composes               the entitled party of the attached obligation in the set
    the two subject types' sets swapped   a payment read with the expense's roles and vice versa
    a second resolver                     the role-set relation re-ruled (any claimant knowing)

Same shape as s117-s122: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_value_kinds_fixture.py'
    spec = importlib.util.spec_from_file_location('test_value_kinds_fixture', path)
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
    FOUR = (db.AMOUNT, db.OCCURRED_ON, db.CLEARED, db.BANK_RETURNED_ITEM)

    def _swap_resolver(fn):
        real = db._role_holder_on_subject
        db._role_holder_on_subject = fn
        db._KNOWING_RELATIONS[db.KNOWING_ROLE_HOLDER_ON_SUBJECT] = fn

        def undo():
            db._role_holder_on_subject = real
            db._KNOWING_RELATIONS[db.KNOWING_ROLE_HOLDER_ON_SUBJECT] = real
        return undo

    def minter_knowing():
        real = db._role_holder_on_subject

        def with_minter(session, prop, claimant):
            out = real(session, prop, claimant)
            if out == db.STRENGTH_NOT_KNOWING and prop.subject_payment_id is not None:
                pay = session.get(db.Payment, prop.subject_payment_id)
                u = session.get(db.Utterance, pay.minted_by_id) if pay is not None else None
                if u is not None and u.origin_party_id == claimant:
                    return db.STRENGTH_KNOWING
            return out
        return _swap_resolver(with_minter)

    def type_confers_knowing():
        saved = {k: db.RULED_KINDS[k] for k in FOUR}
        for k in saved:
            db.RULED_KINDS[k] = dict(saved[k], relational_knowing=False)
        real = db.derived_strength

        def with_map(session, relation, knowing):
            return real(session, relation, dict(knowing, **{k: {'institution'} for k in saved}))
        db.derived_strength = with_map

        def undo():
            db.RULED_KINDS.update(saved)
            db.derived_strength = real
        return undo

    def dated_role_set():
        real = db._role_holder_on_subject

        def dated(session, prop, claimant):
            if not prop.as_of:
                return db.STRENGTH_UNDETERMINED           # the value treated as a position needing a date
            return real(session, prop, claimant)
        return _swap_resolver(dated)

    def anyone_knowing():
        return _swap_resolver(lambda session, prop, claimant: db.STRENGTH_KNOWING if claimant is not None else db.STRENGTH_UNDETERMINED)

    def bank_without_role():
        saved = dict(db._ROLE_SET)
        db._ROLE_SET['payment'] = (db.PAID_BY, db.PAID_TO)

        def undo():
            db._ROLE_SET.clear()
            db._ROLE_SET.update(saved)
        return undo

    def cleared_moves_station():
        real = db.remaining

        def with_cleared(session, obligation, d, catalogue, knowing):
            rep = real(session, obligation, d, catalogue, knowing)
            for pm in rep['payments']:
                c = session.query(db.Proposition).filter_by(kind=db.CLEARED, subject_payment_id=pm['payment']).first()
                if c is not None and pm['discharge'] is None:
                    pm['discharge'] = {'as_of': c.as_of, 'claim': c.id}
                    pm['station'] = db.STATION_DISCHARGED
            return rep
        db.remaining = with_cleared
        return lambda: setattr(db, 'remaining', real)

    def reading_establishes_state():
        real = db._claim_states

        def states(session, claim, retracted):
            out = real(session, claim, retracted)
            if claim.kind in FOUR:
                out = [(db.CLAIM_ESTABLISHED if st == db.CLAIM_CANDIDATE else st, a, g) for st, a, g in out]
            return out
        db._claim_states = states
        return lambda: setattr(db, '_claim_states', real)

    def attachment_composes():
        real = db._role_holder_on_subject

        def through_attachment(session, prop, claimant):
            out = real(session, prop, claimant)
            if out == db.STRENGTH_NOT_KNOWING and prop.subject_payment_id is not None:
                party = session.get(db.Party, claimant)
                for att in session.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_payment_id=prop.subject_payment_id).all():
                    ans = db.in_effect(session, party, db.ENTITLED_PARTY_OF, prop.as_of or '2026-12-31')['identities'].get(att.object_obligation_id)
                    if ans is not None and ans['answer'] == db.EFFECT_IN:
                        return db.STRENGTH_KNOWING
            return out
        return _swap_resolver(through_attachment)

    def sets_swapped():
        saved = dict(db._ROLE_SET)
        db._ROLE_SET['payment'], db._ROLE_SET['expense'] = saved['expense'], saved['payment']

        def undo():
            db._ROLE_SET.clear()
            db._ROLE_SET.update(saved)
        return undo

    def second_resolver():
        real = db._KNOWING_RELATIONS[db.KNOWING_ROLE_HOLDER_ON_SUBJECT]
        db._KNOWING_RELATIONS[db.KNOWING_ROLE_HOLDER_ON_SUBJECT] = lambda session, prop, claimant: db.STRENGTH_KNOWING if claimant else db.STRENGTH_UNDETERMINED
        return lambda: db._KNOWING_RELATIONS.__setitem__(db.KNOWING_ROLE_HOLDER_ON_SUBJECT, real)

    return [
        ('the minter knowing (Kn7 reversed)', minter_knowing),
        ('the origin\'s type confers knowing (the foundation restored)', type_confers_knowing),
        ('the role-set read at a date (an undated amount undetermined)', dated_role_set),
        ('a stranger knowing (the set ignored)', anyone_knowing),
        ('the bank without its role (drawn_on dropped from the set)', bank_without_role),
        ('cleared moves 7G\'s station (K6 reversed)', cleared_moves_station),
        ('a reading establishes state', reading_establishes_state),
        ('the attachment composes (the entitled party in the set)', attachment_composes),
        ('the two subject types\' sets swapped', sets_swapped),
        ('a second resolver for the role-set relation', second_resolver),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    four = (db.AMOUNT, db.OCCURRED_ON, db.CLEARED, db.BANK_RETURNED_ITEM)
    check('core/database.py carries the value kinds and the bank\'s stances exactly as ruled - four kinds by the role-set relation, occurred_on with two permitted subjects, drawn_on a role in 9B\'s form; the set by subject type with the bank in the payment set; one resolver, undated; the guard passing; no value accessor or bank helper',
          all(db.RULED_KINDS[k]['knowing_relation'] == db.KNOWING_ROLE_HOLDER_ON_SUBJECT and db.RULED_KINDS[k]['reading_establishes'] for k in four)
          and db.RULED_KINDS[db.OCCURRED_ON]['subject'] == ('subject_payment_id', 'subject_expense_id')
          and db.RULED_KINDS[db.DRAWN_ON].get('role') is True and db.RULED_KINDS[db.DRAWN_ON]['knowing_relation'] == db.KNOWING_SUBJECT_PARTY
          and db._ROLE_SET == {'payment': (db.PAID_BY, db.PAID_TO, db.DRAWN_ON), 'expense': (db.PROVIDER_OF, db.INCURRED_BY)}
          and db._KNOWING_RELATIONS[db.KNOWING_ROLE_HOLDER_ON_SUBJECT] is db._role_holder_on_subject
          and db.registry_violations() == []
          and not any(hasattr(db, n) for n in ('amount_of', 'date_of', 'value_of', 'bank_of', 'is_cleared', 'minter_knowing')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the value kinds fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the value kinds fixture passes in full',
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
