"""The obligation stances: acknowledged, balance, returned - built by item 9 pass 9D-i exactly as ruled (s 9D.7 /
s 9D-i.8) - and whether each way of collapsing the reading / holder distinctions is caught.

`gw 2.0/CATALOGUES.md` s 9D-i (2026-09-19). Runs the build gate (`tests/test_obligation_stances_fixture.py`) and then
breaks the substrate ten ways, each an attempt to let the asserter stand in for the holder, a reading establish more
than strength, a type confer knowing, or the acknowledgment reach an obligation it does not carry:

    the servicer's acknowledgment discharges     KNOWING_SUBJECT_PARTY grants the servicer E's position (Ob4 reversed)
    the origin's type confers knowing            the foundation stand-in restored for the three kinds
    a reading establishes state                  a reading-sourced stance reads as established (Dg2' reversed)
    a reading discharges                         reading -> discharge: 7G's qualifies accepts a candidate
    the flag establishes state                   reading_establishes read as "established by a reading"
    a non-entitled balance is knowing            the role-at-date relation ignores the role
    the ack composes through the attachment      the kind reaches O via p's attachment and the servicer's role
    an undated stance is knowing                 the relation ignores as_of
    a second relation on the acknowledgment      the ack's holder read by the role-at-date relation (F1 uniformised)
    returned read as a non-acknowledgment        7G's station moved by a return

Same shape as s117-s119: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_obligation_stances_fixture.py'
    spec = importlib.util.spec_from_file_location('test_obligation_stances_fixture', path)
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
    def servicer_discharges():
        real = db._KNOWING_RELATIONS[db.KNOWING_SUBJECT_PARTY]

        def with_servicer(session, prop):
            # the servicer of any obligation the payment is attached to is treated as the holder
            if prop.kind in (db.ACKNOWLEDGED, db.RETURNED) and prop.object_payment_id is not None:
                att = session.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_payment_id=prop.object_payment_id).first()
                if att is not None:
                    sv = session.query(db.Proposition).filter_by(kind=db.SERVICER_OF, object_obligation_id=att.object_obligation_id).first()
                    if sv is not None:
                        rel = session.query(db.EvidentiaryRelationship).filter_by(proposition_id=prop.id).first()
                        u = session.get(db.Utterance, rel.utterance_id) if rel is not None and rel.utterance_id else None
                        if u is not None and u.origin_party_id == sv.subject_party_id:
                            return sv.subject_party_id
            return real(session, prop)
        db._KNOWING_RELATIONS[db.KNOWING_SUBJECT_PARTY] = with_servicer
        return lambda: db._KNOWING_RELATIONS.__setitem__(db.KNOWING_SUBJECT_PARTY, real)

    def type_confers_knowing():
        saved = {k: db.RULED_KINDS[k] for k in (db.ACKNOWLEDGED, db.BALANCE, db.RETURNED)}
        for k in saved:
            db.RULED_KINDS[k] = dict(saved[k], relational_knowing=False)
        # and the map the callers pass has no entry for them -> the foundation path; give it the old one
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
            if claim.kind in (db.ACKNOWLEDGED, db.BALANCE, db.RETURNED):
                out = [(db.CLAIM_ESTABLISHED if st == db.CLAIM_CANDIDATE else st, a, g) for st, a, g in out]
            return out
        db._claim_states = states
        return lambda: setattr(db, '_claim_states', real)

    def reading_discharges():
        real = db.remaining

        def lenient(session, obligation, d, catalogue, knowing):
            rep = real(session, obligation, d, catalogue, knowing)
            for pm in rep['payments']:
                if pm['discharge'] is None:
                    q = [a for a in pm['acknowledgments'] if a['state'] == db.CLAIM_CANDIDATE and a['strength'] == db.STRENGTH_KNOWING
                         and a['entitled'] == db.EFFECT_IN and a['as_of'] and a['as_of'] <= d]
                    if q:
                        pm['discharge'] = {'as_of': q[0]['as_of'], 'claim': q[0]['claim']}
                        pm['station'] = db.STATION_DISCHARGED
            return rep
        db.remaining = lenient
        return lambda: setattr(db, 'remaining', real)

    def flag_establishes_state():
        real = db._claim_states

        def states(session, claim, retracted):
            out = real(session, claim, retracted)
            if db.RULED_KINDS.get(claim.kind, {}).get('reading_establishes'):
                out = [(db.CLAIM_ESTABLISHED if st == db.CLAIM_CANDIDATE else st, a, g) for st, a, g in out]
            return out
        db._claim_states = states
        return lambda: setattr(db, '_claim_states', real)

    def role_ignored():
        real = db._role_at_as_of
        db._role_at_as_of = lambda session, prop, claimant, role_kind: db.STRENGTH_KNOWING if claimant is not None else db.STRENGTH_UNDETERMINED
        db._KNOWING_RELATIONS[db.KNOWING_ENTITLED_PARTY_AT_AS_OF] = db._role_at_as_of

        def undo():
            db._role_at_as_of = real
            db._KNOWING_RELATIONS[db.KNOWING_ENTITLED_PARTY_AT_AS_OF] = real
        return undo

    def ack_composes_through_attachment():
        real = db._KNOWING_RELATIONS[db.KNOWING_SUBJECT_PARTY]

        def composed(session, prop):
            if prop.kind == db.ACKNOWLEDGED and prop.object_payment_id is not None:
                att = session.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_payment_id=prop.object_payment_id).first()
                if att is not None:
                    rel = session.query(db.EvidentiaryRelationship).filter_by(proposition_id=prop.id).first()
                    u = session.get(db.Utterance, rel.utterance_id) if rel is not None and rel.utterance_id else None
                    if u is not None:
                        party = session.get(db.Party, u.origin_party_id)
                        for role in (db.ENTITLED_PARTY_OF, db.SERVICER_OF):
                            ans = db.in_effect(session, party, role, prop.as_of or '2026-12-31')['identities'].get(att.object_obligation_id)
                            if ans is not None and ans['answer'] == db.EFFECT_IN:
                                return u.origin_party_id
            return real(session, prop)
        db._KNOWING_RELATIONS[db.KNOWING_SUBJECT_PARTY] = composed
        return lambda: db._KNOWING_RELATIONS.__setitem__(db.KNOWING_SUBJECT_PARTY, real)

    def undated_knowing():
        real = db._role_at_as_of

        def dated_or_not(session, prop, claimant, role_kind):
            if not prop.as_of:
                return real(session, type('P', (), {'as_of': '2026-12-31', 'kind': prop.kind, **{c: getattr(prop, c) for c in db.Proposition.SUBJECT_SLOTS}})(),
                            claimant, role_kind)
            return real(session, prop, claimant, role_kind)
        db._role_at_as_of = dated_or_not
        db._KNOWING_RELATIONS[db.KNOWING_ENTITLED_PARTY_AT_AS_OF] = dated_or_not

        def undo():
            db._role_at_as_of = real
            db._KNOWING_RELATIONS[db.KNOWING_ENTITLED_PARTY_AT_AS_OF] = real
        return undo

    def ack_uniformised():
        rule = db.RULED_KINDS[db.ACKNOWLEDGED]
        db.RULED_KINDS[db.ACKNOWLEDGED] = dict(rule, knowing_relation=db.KNOWING_ENTITLED_PARTY_AT_AS_OF)
        return lambda: db.RULED_KINDS.__setitem__(db.ACKNOWLEDGED, rule)

    def returned_moves_station():
        real = db.remaining

        def with_returns(session, obligation, d, catalogue, knowing):
            rep = real(session, obligation, d, catalogue, knowing)
            for pm in rep['payments']:
                if session.query(db.Proposition).filter_by(kind=db.RETURNED, object_payment_id=pm['payment']).count():
                    pm['station'] = db.STATION_ATTACHED_UNACKNOWLEDGED
                    pm['discharge'] = None
            return rep
        db.remaining = with_returns
        return lambda: setattr(db, 'remaining', real)

    return [
        ('the servicer\'s acknowledgment discharges (Ob4 reversed)', servicer_discharges),
        ('the origin\'s type confers knowing (the foundation stand-in restored)', type_confers_knowing),
        ('a reading establishes state (Dg2\' reversed)', reading_establishes_state),
        ('a reading discharges (7G accepts a knowing candidate)', reading_discharges),
        ('the flag establishes state', flag_establishes_state),
        ('a non-entitled balance is knowing (the role ignored)', role_ignored),
        ('the acknowledgment composes through the attachment (O reached from p)', ack_composes_through_attachment),
        ('an undated stance is knowing (as_of ignored)', undated_knowing),
        ('a second relation on the acknowledgment (F1 uniformised)', ack_uniformised),
        ('returned read as a non-acknowledgment (the station moved)', returned_moves_station),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries the three obligation stances exactly as ruled - two holder forms, reading_establishes True on all three, the role-at-date relation named with its role in a table (the 9D-i row; later slices add theirs), no dated key - and no discharge / holder / servicer helper',
          db.RULED_KINDS[db.ACKNOWLEDGED]['knowing_relation'] == db.RULED_KINDS[db.RETURNED]['knowing_relation'] == db.KNOWING_SUBJECT_PARTY
          and db.RULED_KINDS[db.BALANCE]['knowing_relation'] == db.KNOWING_ENTITLED_PARTY_AT_AS_OF
          and all(db.RULED_KINDS[k]['reading_establishes'] for k in (db.ACKNOWLEDGED, db.BALANCE, db.RETURNED))
          and db._ROLE_AT_AS_OF[db.KNOWING_ENTITLED_PARTY_AT_AS_OF] == db.ENTITLED_PARTY_OF and db._KNOWING_RELATIONS[db.KNOWING_ENTITLED_PARTY_AT_AS_OF] is db._role_at_as_of   # 9D-ii added its rows; 9D-i's is unchanged
          and db.registry_violations() == []
          and not any(hasattr(db, n) for n in ('discharge', 'is_discharged', 'holder_of', 'position_of', 'servicer_knowing', 'compose_knowing')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the obligation stances fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the obligation stances fixture passes in full',
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
