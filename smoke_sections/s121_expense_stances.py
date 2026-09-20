"""The provider's and insurer's stances on X: built by item 9 pass 9D-ii exactly as ruled (s 9D-ii.7) - and whether each
way of letting the wrong party hold a position, reading content as a verdict, or pulling the plan into the kind is caught.

`gw 2.0/CATALOGUES.md` s 9D-ii (2026-09-19). Runs the build gate (`tests/test_expense_stances_fixture.py`) and then
breaks the substrate ten ways:

    the insurer's relay of the charge knowing     billed knowing for the insurer of X (origin as role)
    the provider's "plan paid" knowing            plan_paid knowing for the provider of X
    a denial read as a determination              7H's current determination from a denial
    a denial read as an adjudication amount       7H's plan_paid series fed by the denial
    the plan gate at the kind level               applied_to_deductible not_knowing for the other plan's insurer
    the type conferring knowing                   the foundation stand-in restored for the six kinds
    a reading establishing state                  a reading-sourced stance reads as established
    an undated stance knowing                     the relation ignores as_of
    the relation re-ruled                         a second resolver for the insurer's stances
    exempt read as zero                           7J counts an applied 'none' as 0 in the basis

Same shape as s117-s120: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_expense_stances_fixture.py'
    spec = importlib.util.spec_from_file_location('test_expense_stances_fixture', path)
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
    SIX = (db.BILLED, db.PATIENT_RESPONSIBILITY, db.PLAN_PAID, db.APPLIED_TO_DEDUCTIBLE, db.DENIAL, db.ADJUDICATION)

    def _swap_resolver(fn):
        real = db._role_at_as_of
        db._role_at_as_of = fn
        for n in db._ROLE_AT_AS_OF:
            db._KNOWING_RELATIONS[n] = fn

        def undo():
            db._role_at_as_of = real
            for n in db._ROLE_AT_AS_OF:
                db._KNOWING_RELATIONS[n] = real
        return undo

    def relay_knowing():
        real = db._role_at_as_of

        def either(session, prop, claimant, role_kind):
            out = real(session, prop, claimant, role_kind)
            if prop.kind == db.BILLED and out == db.STRENGTH_NOT_KNOWING:
                return real(session, prop, claimant, db.INSURER_OF)      # the insurer's relay of the charge counts
            return out
        return _swap_resolver(either)

    def provider_plan_paid():
        real = db._role_at_as_of

        def either(session, prop, claimant, role_kind):
            out = real(session, prop, claimant, role_kind)
            if prop.kind == db.PLAN_PAID and out == db.STRENGTH_NOT_KNOWING:
                return real(session, prop, claimant, db.PROVIDER_OF)
            return out
        return _swap_resolver(either)

    def denial_as_determination():
        real = db.reconciliation

        def with_denial(session, expense, d, catalogue, knowing):
            rep = real(session, expense, d, catalogue, knowing)
            if rep['determinations']['current'] is None:
                den = session.query(db.Proposition).filter_by(kind=db.DENIAL, subject_expense_id=expense.id).first()
                if den is not None:
                    rep['determinations']['current'] = {'claim': den.id, 'name': 'unpaid', 'asserter': None, 'as_of': den.as_of}
            return rep
        db.reconciliation = with_denial
        return lambda: setattr(db, 'reconciliation', real)

    def denial_as_amount():
        real = db.reconciliation

        def with_denial(session, expense, d, catalogue, knowing):
            rep = real(session, expense, d, catalogue, knowing)
            den = session.query(db.Proposition).filter_by(kind=db.DENIAL, subject_expense_id=expense.id).first()
            if den is not None:
                rep['stances']['plan_paid']['governing'] = {'claim': den.id, 'value': 0, 'asserter': None, 'as_of': den.as_of}
                rep['note'] = [n for n in rep['note'] if 'denial' not in n]
            return rep
        db.reconciliation = with_denial
        return lambda: setattr(db, 'reconciliation', real)

    def plan_gate_in_kind():
        real = db._role_at_as_of

        def per_plan(session, prop, claimant, role_kind):
            out = real(session, prop, claimant, role_kind)
            if prop.kind == db.APPLIED_TO_DEDUCTIBLE and out == db.STRENGTH_KNOWING:
                # the kind reaches P through the expense's plan relation and demands the claimant insure THAT plan
                rels = session.query(db.Proposition).filter_by(kind=db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=prop.subject_expense_id).all()
                party = session.get(db.Party, claimant)
                for r in rels:
                    ans = db.in_effect(session, party, db.INSURER_OF_PLAN, prop.as_of)['identities'].get(r.object_plan_id)
                    if ans is not None and ans['answer'] == db.EFFECT_IN:
                        return db.STRENGTH_KNOWING
                return db.STRENGTH_NOT_KNOWING if rels else out
            return out
        return _swap_resolver(per_plan)

    def type_confers_knowing():
        saved = {k: db.RULED_KINDS[k] for k in SIX}
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

    def reading_establishes_state():
        real = db._claim_states

        def states(session, claim, retracted):
            out = real(session, claim, retracted)
            if claim.kind in SIX:
                out = [(db.CLAIM_ESTABLISHED if st == db.CLAIM_CANDIDATE else st, a, g) for st, a, g in out]
            return out
        db._claim_states = states
        return lambda: setattr(db, '_claim_states', real)

    def undated_knowing():
        real = db._role_at_as_of

        def dated_or_not(session, prop, claimant, role_kind):
            if not prop.as_of and prop.kind in SIX:
                shadow = type('P', (), {'as_of': '2026-12-31', 'kind': prop.kind, **{c: getattr(prop, c) for c in db.Proposition.SUBJECT_SLOTS}})()
                return real(session, shadow, claimant, role_kind)
            return real(session, prop, claimant, role_kind)
        return _swap_resolver(dated_or_not)

    def relation_re_ruled():
        real = db._KNOWING_RELATIONS[db.KNOWING_INSURER_AT_AS_OF]
        db._KNOWING_RELATIONS[db.KNOWING_INSURER_AT_AS_OF] = lambda session, prop, claimant, role_kind: db.STRENGTH_KNOWING if claimant else db.STRENGTH_UNDETERMINED
        return lambda: db._KNOWING_RELATIONS.__setitem__(db.KNOWING_INSURER_AT_AS_OF, real)

    def exempt_as_zero():
        real = db.accumulator

        def zeroed(session, plan, d, catalogue, knowing, person=None):
            rep = real(session, plan, d, catalogue, knowing, person=person)
            for x, c in rep['derived']['exempt']:
                rep['derived']['basis'].append((x, 0, c))
            rep['derived']['exempt'] = []
            return rep
        db.accumulator = zeroed
        return lambda: setattr(db, 'accumulator', real)

    return [
        ('the insurer\'s relay of the charge knowing for billed', relay_knowing),
        ('the provider\'s "plan paid" knowing', provider_plan_paid),
        ('a denial read as a determination', denial_as_determination),
        ('a denial read as an adjudication amount', denial_as_amount),
        ('the plan gate at the kind level (P reached from X)', plan_gate_in_kind),
        ('the origin\'s type confers knowing (the foundation restored)', type_confers_knowing),
        ('a reading establishes state', reading_establishes_state),
        ('an undated stance is knowing (as_of ignored)', undated_knowing),
        ('the relation re-ruled (a second resolver for the insurer)', relation_re_ruled),
        ('exempt read as zero', exempt_as_zero),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    six = (db.BILLED, db.PATIENT_RESPONSIBILITY, db.PLAN_PAID, db.APPLIED_TO_DEDUCTIBLE, db.DENIAL, db.ADJUDICATION)
    check('core/database.py carries the six stances on X exactly as ruled - billed by the provider relation, five by the insurer relation, reading_establishes True, no object; two rows added to the role-at-date table on the ONE resolver; denial and adjudication two kinds; the guard passing; no verdict / plan-of-stance helper',
          all(db.RULED_KINDS[k]['subject'] == ('subject_expense_id',) and db.RULED_KINDS[k]['object'] == () and db.RULED_KINDS[k]['reading_establishes'] for k in six)
          and db.RULED_KINDS[db.BILLED]['knowing_relation'] == db.KNOWING_PROVIDER_AT_AS_OF
          and all(db.RULED_KINDS[k]['knowing_relation'] == db.KNOWING_INSURER_AT_AS_OF for k in six[1:])
          and db._ROLE_AT_AS_OF[db.KNOWING_PROVIDER_AT_AS_OF] == db.PROVIDER_OF and db._ROLE_AT_AS_OF[db.KNOWING_INSURER_AT_AS_OF] == db.INSURER_OF
          and len({db._KNOWING_RELATIONS[n] for n in db._ROLE_AT_AS_OF}) == 1 and len(db._KNOWING_RELATIONS) == 6
          and db.registry_violations() == []
          and not any(hasattr(db, n) for n in ('verdict', 'is_denied', 'adjudicate', 'interpret_content', 'plan_of_stance', 'relay_knowing')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the expense stances fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the expense stances fixture passes in full',
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
