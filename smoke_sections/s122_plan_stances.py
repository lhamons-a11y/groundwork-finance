"""The insurer's stances and terms on P: built by item 9 pass 9D-iii exactly as ruled (s 9D-iii.7) - and whether each way of
letting the household hold the insurer's term, deriving one coverage-ended claim from another, reading the role on the
wrong side, or collapsing the two applied shapes is caught.

`gw 2.0/CATALOGUES.md` s 9D-iii (2026-09-20). Runs the build gate (`tests/test_plan_stances_fixture.py`) and then breaks
the substrate ten ways:

    the household's term knowing             the relay treated as the holder (F4 / F6-iii reversed)
    the household's plan year knowing        the same for the window's term
    coverage_ended mints under_plan_ended    the insurer's termination derives the household's boundary (F3)
    eligibility derives membership           the insurer's stance mints under_plan (F5 reversed)
    the other plan's insurer knowing         Cigna knowing for a stance on Aetna's plan
    the role read on the wrong side          eligibility read on its subject (F2 dropped)
    the type conferring knowing              the foundation stand-in restored for the eight kinds
    a reading establishing state             a reading-sourced stance reads as established
    an undated term knowing                  the relation ignores as_of
    the two applied shapes collapsed         the individual figure read as the family figure (F1 reversed)

Same shape as s117-s121: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_plan_stances_fixture.py'
    spec = importlib.util.spec_from_file_location('test_plan_stances_fixture', path)
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
    EIGHT = (db.DEDUCTIBLE, db.INDIVIDUAL_DEDUCTIBLE, db.PLAN_YEAR, db.DEDUCTIBLE_APPLIED, db.INDIVIDUAL_DEDUCTIBLE_APPLIED,
             db.ELIGIBILITY, db.COVERAGE_ENDED, db.AUTHORIZATION)

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

    def _on_insert(fn):
        from sqlalchemy import event

        def hook(mapper, connection, target):
            fn(connection, target, db.Proposition.__table__)
        event.listen(db.Proposition, 'after_insert', hook)
        return lambda: event.remove(db.Proposition, 'after_insert', hook)

    def _insert(connection, P, kind, **slots):
        r = connection.execute(P.insert().values(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                                 as_of=slots.pop('as_of', '2026-01-01'), **slots))
        U = db.Utterance.__table__
        u = connection.execute(U.select().order_by(U.c.id)).fetchone()
        connection.execute(db.EvidentiaryRelationship.__table__.insert().values(proposition_id=r.inserted_primary_key[0], utterance_id=u.id))

    def household_term_knowing():
        real = db._role_at_as_of

        def relay(session, prop, claimant, role_kind, side='subject'):
            out = real(session, prop, claimant, role_kind, side=side)
            if prop.kind in (db.DEDUCTIBLE, db.INDIVIDUAL_DEDUCTIBLE) and out == db.STRENGTH_NOT_KNOWING:
                party = session.get(db.Party, claimant)
                if party is not None and db.party_foundation(party) == 'person':
                    return db.STRENGTH_KNOWING       # "our deductible is $3,000" taken as the holder's own
            return out
        return _swap_resolver(relay)

    def household_plan_year_knowing():
        real = db._role_at_as_of

        def relay(session, prop, claimant, role_kind, side='subject'):
            out = real(session, prop, claimant, role_kind, side=side)
            if prop.kind == db.PLAN_YEAR and out == db.STRENGTH_NOT_KNOWING:
                return db.STRENGTH_KNOWING
            return out
        return _swap_resolver(relay)

    def termination_mints_boundary():
        def mint(connection, target, P):
            if target.kind == db.COVERAGE_ENDED and target.subject_plan_id is not None:
                for m in connection.execute(P.select().where(P.c.kind == db.UNDER_PLAN, P.c.object_plan_id == target.subject_plan_id)).fetchall():
                    _insert(connection, P, db.UNDER_PLAN_ENDED, subject_party_id=m.subject_party_id, object_plan_id=target.subject_plan_id,
                            as_of=(target.content if target.content and target.content[:4].isdigit() else target.as_of))
        return _on_insert(mint)

    def eligibility_derives_membership():
        def mint(connection, target, P):
            if target.kind == db.ELIGIBILITY and target.subject_party_id is not None and target.object_plan_id is not None:
                if 'never' in (target.content or ''):
                    _insert(connection, P, db.UNDER_PLAN_ENDED, subject_party_id=target.subject_party_id, object_plan_id=target.object_plan_id, as_of=target.as_of)
                elif not connection.execute(P.select().where(P.c.kind == db.UNDER_PLAN, P.c.subject_party_id == target.subject_party_id,
                                                              P.c.object_plan_id == target.object_plan_id)).fetchone():
                    _insert(connection, P, db.UNDER_PLAN, subject_party_id=target.subject_party_id, object_plan_id=target.object_plan_id, as_of=target.as_of)
        return _on_insert(mint)

    def other_insurer_knowing():
        real = db._role_at_as_of

        def any_insurer(session, prop, claimant, role_kind, side='subject'):
            out = real(session, prop, claimant, role_kind, side=side)
            if prop.kind in EIGHT and out == db.STRENGTH_NOT_KNOWING:
                party = session.get(db.Party, claimant)
                if party is not None and session.query(db.Proposition).filter_by(kind=db.INSURER_OF_PLAN, subject_party_id=claimant).count():
                    return db.STRENGTH_KNOWING       # an insurer of some plan is knowing for any plan's stance
            return out
        return _swap_resolver(any_insurer)

    def wrong_side():
        saved = dict(db._ROLE_AT_AS_OF_SIDE)
        db._ROLE_AT_AS_OF_SIDE.clear()

        def undo():
            db._ROLE_AT_AS_OF_SIDE.clear()
            db._ROLE_AT_AS_OF_SIDE.update(saved)
        return undo

    def type_confers_knowing():
        saved = {k: db.RULED_KINDS[k] for k in EIGHT}
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
            if claim.kind in EIGHT:
                out = [(db.CLAIM_ESTABLISHED if st == db.CLAIM_CANDIDATE else st, a, g) for st, a, g in out]
            return out
        db._claim_states = states
        return lambda: setattr(db, '_claim_states', real)

    def undated_knowing():
        real = db._role_at_as_of

        def dated_or_not(session, prop, claimant, role_kind, side='subject'):
            if not prop.as_of and prop.kind in EIGHT:
                shadow = type('P', (), {'as_of': '2026-12-31', 'kind': prop.kind,
                                        **{c: getattr(prop, c) for c in db.Proposition.SUBJECT_SLOTS + db.Proposition.OBJECT_SLOTS}})()
                return real(session, shadow, claimant, role_kind, side=side)
            return real(session, prop, claimant, role_kind, side=side)
        return _swap_resolver(dated_or_not)

    def shapes_collapsed():
        real = db.accumulator

        def collapsed(session, plan, d, catalogue, knowing, person=None):
            rep = real(session, plan, d, catalogue, knowing, person=person)
            if person is None:
                # the individual figure read as the family figure: the latest individual stance governs the family
                fam = real(session, plan, d, catalogue, knowing, person=None)
                rows = session.query(db.Proposition).filter_by(kind=db.INDIVIDUAL_DEDUCTIBLE_APPLIED, subject_plan_id=plan.id).order_by(db.Proposition.id.desc()).all()
                if rows and rep['stated']['governing'] is not None:
                    rep['stated']['governing'] = dict(rep['stated']['governing'], claim=rows[0].id, value=db._money(rows[0].content))
            return rep
        db.accumulator = collapsed
        return lambda: setattr(db, 'accumulator', real)

    return [
        ('the household\'s term knowing (the relay as holder)', household_term_knowing),
        ('the household\'s plan year knowing', household_plan_year_knowing),
        ('coverage_ended mints under_plan_ended (F3)', termination_mints_boundary),
        ('eligibility derives membership (F5 reversed)', eligibility_derives_membership),
        ('the other plan\'s insurer knowing', other_insurer_knowing),
        ('the role read on the wrong side (F2 dropped)', wrong_side),
        ('the origin\'s type confers knowing (the foundation restored)', type_confers_knowing),
        ('a reading establishes state', reading_establishes_state),
        ('an undated term is knowing (as_of ignored)', undated_knowing),
        ('the two applied shapes collapsed (F1 reversed)', shapes_collapsed),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    eight = (db.DEDUCTIBLE, db.INDIVIDUAL_DEDUCTIBLE, db.PLAN_YEAR, db.DEDUCTIBLE_APPLIED, db.INDIVIDUAL_DEDUCTIBLE_APPLIED,
             db.ELIGIBILITY, db.COVERAGE_ENDED, db.AUTHORIZATION)
    check('core/database.py carries the insurer\'s stances and terms on P exactly as ruled - eight kinds, all by the plan insurer\'s relation, two applied kinds by shape, eligibility read on its object by the side table alone, a third row on the one resolver; the guard passing; no terms / eligibility / coverage helper',
          all(db.RULED_KINDS[k]['knowing_relation'] == db.KNOWING_PLAN_INSURER_AT_AS_OF and db.RULED_KINDS[k]['reading_establishes'] for k in eight)
          and db.RULED_KINDS[db.INDIVIDUAL_DEDUCTIBLE_APPLIED]['object'] == ('object_party_id',) and db.RULED_KINDS[db.DEDUCTIBLE_APPLIED]['object'] == ()
          and db._ROLE_AT_AS_OF[db.KNOWING_PLAN_INSURER_AT_AS_OF] == db.INSURER_OF_PLAN and db._ROLE_AT_AS_OF_SIDE == {db.ELIGIBILITY: 'object'}
          and len({db._KNOWING_RELATIONS[n] for n in db._ROLE_AT_AS_OF}) == 1 and db.registry_violations() == []
          and not any(hasattr(db, n) for n in ('terms_of', 'current_terms', 'is_eligible', 'coverage_status', 'plan_ended')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the plan stances fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the plan stances fixture passes in full',
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
