"""Role period - the executable trace of `gw 2.0/ROLE_PERIOD.md` s7 (RP2, ruled 2026-09-14).

A role has no intrinsic period. Temporal boundaries are propositions in their own right: a ruled
beginning or ending kind, bound to the role kind it temporally qualifies, with `as_of` identifying
the date asserted about. Boundary claims preserve their own provenance and learned-at time. A
beginning or ending does not rewrite prior claims, imply the opposite boundary, resolve disputes,
establish continuous effect, or itself create a role.

NO ROLE KIND IS RULED BY THIS SLICE. The one stand-in left is `serves` / `serves_began` / `serves_ended`
(party <-> party), which the fixture registers and removes. The party <-> plan stand-in (`standin_covered_under`) was
retired into the RULED kind `under_plan` and its boundaries by item 9 pass 9A (CATALOGUES.md, 2026-09-19) - the first
ruled role kind; the party <-> obligation stand-in (`standin_role_of_obligation`) into the RULED kind `entitled_party_of`
and its boundaries by pass 9B (2026-09-19);
this fixture now exercises RP2's grammar on it as built. `standin_covered_under` was NOT "covered under" -
that relation's meaning is a separate ruling, and Plan's existence gives it none.

What this slice can and cannot exercise
---------------------------------------
    R1   holds-at alone: the role kind with as_of, no boundary                     EXERCISED
    R2   one utterance, two boundaries                                             EXERCISED
    R3   T4/T8: ended 6/30 learned 8/15; began row untouched; prior belief replays  EXERCISED
    R4   began / ended / began - three claims, one party                            EXERCISED
    R5   disputed ending = two claims; nothing chosen                               EXERCISED
    R6   retraction of a beginning is not an ending                                 EXERCISED
    R7   overlap: two beginnings, no ending - represented, not refused, not resolved EXERCISED
    R8   two roles' boundaries on one obligation; nothing on the anchor             EXERCISED
    R10  a party <-> plan stand-in gets endpoint + as_of and no meaning             EXERCISED
    R11  reading never establishes a boundary                                       EXERCISED
    R12  an ending with no beginning on file                                        EXERCISED
    the guard: structural validity only - bound kind ruled, a role, same slots;
         not symmetric; as_of required; "anything bounds anything" refused          EXERCISED
    a boundary creates no role; a boundary implies no opposite boundary             EXERCISED
    no period column, no in-effect accessor, no real role kind, no resolver         EXERCISED (absence)
    the role catalogue, knowing for roles, overlap policy, item 6                   NOT BUILT

Run:  python tests/test_role_period_fixture.py
"""
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL = [], []


def check(name, condition):
    (PASS if condition else FAIL).append(name)
    print(('  OK    ' if condition else '  FAIL  ') + name)


PERIOD_WORDS = ('effective', 'period', 'valid_from', 'valid_to', 'start', 'end_on', 'ends_on', 'from_date', 'to_date',
                'begins_on', 'began_on', 'ended_on', 'interval')
REAL_ROLE_NAMES = ('serves', 'servicer_of', 'entitled_party_of', 'entitled', 'obligor_on', 'obligor', 'provider_of',
                   'insurer_of', 'covered_under', 'member_of', 'enrolled_in', 'membership', 'payer_of', 'payee_of')
# Item 7 pass 7F (CONSUMER_DERIVATIONS.md s 7F.8, ruled 2026-09-18) built the consumer this fixture once said
# did not exist: `in_effect(session, party, role_kind, d)` answers "in effect on d" as a READ-ONLY derivation
# under TS (G read forward, N read back, four states, the governing stance named). It is not a resolver, a
# period, a status or an overlap policy - those absences still hold and are what CONSUMER_NAMES now lists.
CONSUMER_NAMES = ('in_effect_on', 'current_role', 'role_period', 'period_of', 'roles_in_effect',
                  'role_on', 'holds_on', 'effective_role', 'overlaps', 'resolve_boundaries', 'periods_of',
                  'resolve_overlap', 'current_status', 'latest_stance', 'in_effect_cache')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_role_')
    eng = create_engine(f'sqlite:///{Path(d) / "t.db"}')

    @event.listens_for(eng, 'connect')
    def _fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def _refused(s, obj, exc=ValueError):
    try:
        s.add(obj)
        s.commit()
        s.rollback()
        return False
    except exc:
        s.rollback()
        return True


def _role(subject, obj):
    return {'subject': (subject,), 'object': (obj,), 'symmetric': False, 'reading_establishes': False,
            'relational_knowing': True, 'role': True}   # 'role': True classifies the stand-in as a role (9B-F1); NO knowing_relation - the stand-in's knowing is not ruled


def _boundary(of, which, subject, obj):
    r = _role(subject, obj)
    r.update({'boundary': which, 'of': of})
    return r


STAND_INS = {
    'serves':                        _role('subject_party_id', 'object_party_id'),
    'serves_began':                  _boundary('serves', 'began', 'subject_party_id', 'object_party_id'),
    'serves_ended':                  _boundary('serves', 'ended', 'subject_party_id', 'object_party_id'),
}


def run(db):
    shipped = {k: v for k, v in db.RULED_KINDS.items()}
    # Item 9 pass 9A built under_plan and its boundaries as accepted in pass F: the shipped registry now rules exactly ONE
    # role kind and carries exactly its two boundary entries; the rest of the catalogue stays a separate ruling (9B).
    # Item 9 pass 9B ruled the role catalogue: the shipped registry now marks nine role kinds ('role': True - 9B-F1,
    # classification only) and carries boundary entries for the three that transition; `serves` (party <-> party,
    # Kn6's link as this fixture named it) is NOT one of them - 9B's servicer_of is party -> obligation - so it
    # stays a stand-in here, its name carrying no ruling.
    check('the shipped registry marks exactly the ruled role kinds and carries boundary entries only for under_plan, entitled_party_of and servicer_of; serves and the obligor role are not ruled',
          {k for k, r in shipped.items() if r.get('role')} == {'under_plan', 'entitled_party_of', 'servicer_of', 'provider_of', 'insurer_of', 'insurer_of_plan', 'incurred_by', 'paid_by', 'paid_to', 'drawn_on'}   # drawn_on: 9D-iv
          and {r['of'] for r in shipped.values() if r.get('of')} == {'under_plan', 'entitled_party_of', 'servicer_of'}
          and not any(n in shipped for n in ('serves', 'obligor_on', 'obligor', 'covered_under', 'member_of', 'enrolled_in', 'membership', 'payer_of', 'payee_of')))
    for k in STAND_INS:
        assert k not in db.RULED_KINDS, k
    db.RULED_KINDS.update(STAND_INS)
    try:
        _run(db)
    finally:
        for k in STAND_INS:
            db.RULED_KINDS.pop(k, None)
    check('the stand-in kinds are removed; the registry is as shipped',
          db.RULED_KINDS == shipped)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


def _run(db):
    s = _fresh()
    rob = db.Person(display_name='Rob')
    kim = db.Person(display_name='Kim')
    s.add_all([rob, kim])
    s.commit()
    household, kim_party = rob.party, kim.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}}

    def utter(text, when='2026-01-05T09:00:00', origin=None):
        u = db.Utterance(origin_party_id=(origin or household).id, asserted_at=when, content=text)
        s.add(u)
        s.commit()
        return u

    def mint_party(text):
        u = utter(text)
        p = db.Party(minted_by_id=u.id)
        s.add(p)
        s.commit()
        return p, u

    def prop(kind, as_of=None, created=None, **slots):
        p = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                           as_of=as_of, **slots)
        if created is not None:
            p.created_at = created
        s.add(p)
        s.commit()
        return p

    def evidence(p, utterance=None, reading=None):
        e = db.EvidentiaryRelationship(proposition_id=p.id,
                                       utterance_id=utterance.id if utterance else None,
                                       reading_id=reading.id if reading else None)
        s.add(e)
        s.commit()
        return e

    def claims(kind, **slots):
        return s.query(db.Proposition).filter_by(kind=kind, **slots)

    chase, u_chase = mint_party('Chase, the servicer.')
    aetna, u_aetna = mint_party('Aetna.')
    e1, _ = mint_party('The original lender.')
    e2, _ = mint_party('The debt buyer.')
    mortgage = db.Obligation(minted_by_id=utter('Our mortgage.').id)
    s.add(mortgage)
    s.commit()

    print('\n1. The registry guard - structural validity only\n')
    check('the boundary kinds are found through the registry, by boundary, not by naming convention',
          db.boundary_kinds_of('serves') == {'began': 'serves_began', 'ended': 'serves_ended'}
          and db.boundary_kinds_of('serves_began') == {} and db.registry_violations() == [])
    bad = {
        'bounds a kind that is not ruled': dict(STAND_INS['serves_began'], of='no_such_kind'),
        'bounds another boundary kind':     dict(STAND_INS['serves_began'], of='serves_ended'),
        'takes different participants than its role': dict(STAND_INS['serves_began'], object=('object_obligation_id',)),
        'is symmetric':                      dict(STAND_INS['serves_began'], symmetric=True),
        'lets a reading establish it':       dict(STAND_INS['serves_began'], reading_establishes=True),
        'names a boundary that is neither began nor ended': dict(STAND_INS['serves_began'], boundary='paused'),
        'names no role at all':              {k: v for k, v in STAND_INS['serves_began'].items() if k != 'of'},
    }
    caught = {}
    for name, rule in bad.items():
        db.RULED_KINDS['bad_boundary'] = rule
        try:
            caught[name] = bool(db.registry_violations(kinds=('bad_boundary',))) and _refused(
                s, db.Proposition(kind='bad_boundary', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                  subject_party_id=chase.id, as_of='2026-03-01',
                                  **({'object_obligation_id': mortgage.id} if 'different participants' in name else {'object_party_id': household.id})))
        finally:
            db.RULED_KINDS.pop('bad_boundary', None)
    check('"anything can be a beginning of anything" is refused - each malformed binding is a registry violation AND refused at insert: '
          + ', '.join(n for n, ok in caught.items() if not ok) if not all(caught.values()) else
          '"anything can be a beginning of anything" is refused - each malformed binding is a registry violation AND refused at insert',
          all(caught.values()))
    check('a boundary claim requires as_of - the date the boundary is about',
          _refused(s, db.Proposition(kind='serves_began', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_party_id=chase.id, object_party_id=household.id)))
    check('a boundary kind takes exactly its role\'s participants - the slot discipline applies to it unchanged',
          _refused(s, db.Proposition(kind='serves_began', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_party_id=chase.id, object_obligation_id=mortgage.id, as_of='2026-03-01')))

    print('\n2. R1 / R2 - holds-at alone; one utterance, two boundaries\n')
    u_holds = utter('Chase services our mortgage.', '2026-01-05T09:00:00')
    p_holds = prop('serves', as_of='2026-01-05', subject_party_id=chase.id, object_party_id=household.id)
    evidence(p_holds, utterance=u_holds)
    check('R1: a role stance with no boundary - the role kind, as_of the date it is about, no beginning and no ending anywhere',
          p_holds.as_of == '2026-01-05' and claims('serves_began').count() == 0 and claims('serves_ended').count() == 0)
    check('R1: knowing for a role claim is not ruled - the stand-in derives undetermined, never knowing',
          db.derived_strength(s, s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p_holds.id).one(), KNOWING)
          == db.STRENGTH_UNDETERMINED)
    u_span = utter('Chase serviced it from March to June, before that it was the lender.', '2026-07-02T09:00:00')
    p_b = prop('serves_began', as_of='2026-03-01', subject_party_id=chase.id, object_party_id=household.id)
    p_e = prop('serves_ended', as_of='2026-06-30', subject_party_id=chase.id, object_party_id=household.id)
    evidence(p_b, utterance=u_span)
    evidence(p_e, utterance=u_span)
    check('R2: one utterance evidences two boundary claims; the period is what they bound - nowhere written',
          s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_span.id).count() == 2
          and p_b.as_of == '2026-03-01' and p_e.as_of == '2026-06-30'
          and not any(any(w in c.name for w in PERIOD_WORDS) for c in db.Proposition.__table__.columns)
          and not any(hasattr(db.Proposition, w) for w in PERIOD_WORDS + ('effective_from', 'effective_to')))
    check('R2: the two boundaries created no holds-at claim - a boundary does not itself create a role',
          claims('serves', subject_party_id=chase.id).count() == 1)

    print('\n3. R3 - T4/T8: the late-discovered ending; the beginning untouched; the prior belief replays\n')
    P = db.Plan(minted_by_id=utter('We have a plan through work.', '2026-01-03T09:00:00').id)
    s.add(P)
    s.commit()
    u_began = utter('Kim has been on it since January 1.', '2026-01-05T09:00:00')
    p_kb = prop(db.UNDER_PLAN_BEGAN, as_of='2026-01-01', created=datetime(2026, 1, 5, 9), subject_party_id=kim_party.id, object_plan_id=P.id)
    evidence(p_kb, utterance=u_began)
    u_letter = utter('Coverage terminated effective June 30.', '2026-08-15T09:00:00', origin=aetna)
    p_ke = prop(db.UNDER_PLAN_ENDED, as_of='2026-06-30', created=datetime(2026, 8, 15, 9), subject_party_id=kim_party.id, object_plan_id=P.id)
    evidence(p_ke, utterance=u_letter)
    check('R3: the beginning created no holds-at claim for the stand-in - the role exists as claims only when a party makes them',
          claims(db.UNDER_PLAN).count() == 0)
    check('R3: the ending is its own claim - as_of 6/30 (effective), created 8/15 (learned), the insurer\'s provenance - not a coordinate on the beginning',
          p_ke.as_of == '2026-06-30' and p_ke.created_at == datetime(2026, 8, 15, 9)
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p_ke.id).one().utterance.origin_party_id == aetna.id
          and p_kb.as_of == '2026-01-01')
    record_on_jul_1 = s.query(db.Proposition).filter(db.Proposition.kind.like('under_plan%'),
                                                     db.Proposition.created_at <= datetime(2026, 7, 1)).all()
    check('R3: what the record held on 7/1 replays - a beginning and no ending; the prior belief survives because nothing was rewritten',
          [p.kind for p in record_on_jul_1] == [db.UNDER_PLAN_BEGAN]
          and s.get(db.Proposition, p_kb.id).as_of == '2026-01-01')
    check('R3: the ending did not touch the beginning row, and cannot - references and kind are immutable; as_of is a claim\'s own',
          (lambda: (p_kb.as_of, setattr(p_kb, 'kind', db.UNDER_PLAN_ENDED), _refused(s, p_kb))[2])()
          and s.get(db.Proposition, p_kb.id).kind == db.UNDER_PLAN_BEGAN)

    print('\n4. R4 / R5 / R6 - three transitions; a disputed ending; retraction is not ending\n')
    u_again = utter('Chase took it back over in September.', '2026-09-10T09:00:00')
    p_b2 = prop('serves_began', as_of='2026-09-01', subject_party_id=chase.id, object_party_id=household.id)
    evidence(p_b2, utterance=u_again)
    check('R4: began / ended / began - three claims at three dates; Chase is one party; no "current servicer" is written',
          claims('serves_began', subject_party_id=chase.id).count() == 2 and claims('serves_ended', subject_party_id=chase.id).count() == 1
          and s.get(db.Party, chase.id) is not None and not any(hasattr(db, n) for n in CONSUMER_NAMES))
    p_ke2 = prop(db.UNDER_PLAN_ENDED, as_of='2026-12-31', subject_party_id=kim_party.id, object_plan_id=P.id)
    evidence(p_ke2, utterance=utter('No - we paid through December; it ended 12/31.', '2026-08-16T09:00:00'))
    check('R5: two claims about the ending - 6/30 by the insurer, 12/31 by the household - both stand; nothing chosen, nothing deleted',
          claims(db.UNDER_PLAN_ENDED, subject_party_id=kim_party.id, object_plan_id=P.id).count() == 2
          and s.get(db.Proposition, p_ke.id) is not None and s.get(db.Proposition, p_ke2.id) is not None)
    n_ended = claims('serves_ended').count()
    r = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                       subject_utterance_id=u_again.id)
    s.add(r)
    s.commit()
    evidence(r, utterance=utter('I was wrong - Chase never took it back.', '2026-09-20T09:00:00'))
    check('R6: retracting the utterance behind a beginning is a retraction - no ending was created, the beginning row and its history remain',
          claims('serves_ended').count() == n_ended and s.get(db.Proposition, p_b2.id) is not None
          and s.query(db.Proposition).filter_by(kind=db.UTTERANCE_RETRACTION, subject_utterance_id=u_again.id).count() == 1)

    print('\n5. R7 / R12 - overlap represented, not resolved; an ending with no beginning\n')
    P2 = db.Plan(minted_by_id=utter('And the marketplace plan from July.', '2026-07-03T09:00:00').id)
    s.add(P2)
    s.commit()
    p_kb2 = prop(db.UNDER_PLAN_BEGAN, as_of='2026-07-01', subject_party_id=kim_party.id, object_plan_id=P2.id)
    evidence(p_kb2, utterance=utter('Kim went on the marketplace plan July 1.', '2026-07-03T09:05:00'))
    check('R7: two beginnings for Kim under two plans - both rows accepted; the record shows the state and neither refuses nor resolves it',
          claims(db.UNDER_PLAN_BEGAN, subject_party_id=kim_party.id).count() == 2
          and not any(hasattr(db, n) for n in ('overlap_policy', 'resolve_overlap', 'refuse_overlap')))
    p_orphan = prop('serves_ended', as_of='2025-12-31', subject_party_id=e1.id, object_party_id=household.id)
    evidence(p_orphan, utterance=utter('The lender stopped servicing at the end of last year.', '2026-01-06T09:00:00'))
    check('R12: an ending with no beginning on file is a claim like any other - accepted; the gap is a derivation\'s problem',
          claims('serves_began', subject_party_id=e1.id).count() == 0 and s.get(db.Proposition, p_orphan.id) is not None)

    print('\n6. R8 / R10 / R11 - two roles on one obligation; the party <-> plan stand-in; reading never establishes\n')
    u_sold = utter('The mortgage was sold May 1.', '2026-05-03T09:00:00')
    evidence(prop(db.ENTITLED_PARTY_OF_ENDED, as_of='2026-05-01', subject_party_id=e1.id, object_obligation_id=mortgage.id), utterance=u_sold)
    evidence(prop(db.ENTITLED_PARTY_OF_BEGAN, as_of='2026-05-01', subject_party_id=e2.id, object_obligation_id=mortgage.id), utterance=u_sold)
    check('R8: E1 ended and E2 began on one date, two claims on O; nothing on the obligation anchor; O continues',
          claims(db.ENTITLED_PARTY_OF_ENDED, object_obligation_id=mortgage.id).count() == 1
          and claims(db.ENTITLED_PARTY_OF_BEGAN, object_obligation_id=mortgage.id).count() == 1
          and {c.name for c in db.Obligation.__table__.columns} == {'id', 'minted_by_id', 'created_at'})
    check('R10: the party <-> plan stand-in has its endpoint and its as_of machinery - and no meaning: it is a stand-in, not a ruled "covered under"',
          p_kb.object_plan_id == P.id and 'covered_under' not in db.RULED_KINDS and 'member_of' not in db.RULED_KINDS
          and db.derived_strength(s, s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p_kb.id).one(), KNOWING) == db.STRENGTH_UNDETERMINED)
    card = db.Artefact(held=True, content_hash='h-card', as_of='2026-01-10')
    s.add(card)
    s.commit()
    evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=card.id, object_party_id=aetna.id), utterance=u_aetna)
    rd = db.Reading(artefact_id=card.id, reader_process='ocr/2', read_at=datetime(2026, 1, 20))
    s.add(rd)
    s.commit()
    p_since = prop(db.UNDER_PLAN_BEGAN, as_of='2026-01-01', subject_party_id=kim_party.id, object_plan_id=P.id)
    e_since = evidence(p_since, reading=rd)
    check('R11: "Member since 01/01/2026" read from the card is a candidate at most - reading_establishes is False for every boundary kind',
          not db.RULED_KINDS[db.UNDER_PLAN_BEGAN]['reading_establishes']
          and e_since.reading_id == rd.id and e_since.utterance_id is None
          and db.derived_strength(s, e_since, KNOWING) == db.STRENGTH_UNDETERMINED)

    print('\n7. What a boundary does not do; absences\n')
    n_holds = claims('serves', subject_party_id=chase.id).count()
    n_began = claims('serves_began', subject_party_id=chase.id).count()
    evidence(prop('serves_ended', as_of='2026-11-30', subject_party_id=chase.id, object_party_id=household.id),
             utterance=utter('Chase is off it as of the end of November.', '2026-12-02T09:00:00'))
    check('a boundary creates no role and implies no opposite boundary - an ending inserted no holds-at and no beginning',
          claims('serves', subject_party_id=chase.id).count() == n_holds
          and claims('serves_began', subject_party_id=chase.id).count() == n_began)
    check('no period is stored anywhere - no effective / period / interval column on any 2.0 table, no roles table',
          not any(any(w in c.name for w in PERIOD_WORDS)
                  for t in ('propositions', 'parties', 'obligations', 'payments', 'expenses', 'plans', 'utterances', 'artefacts', 'readings')
                  for c in db.Base.metadata.tables[t].columns)
          and not any(n in db.Base.metadata.tables for n in ('roles', 'role_periods', 'memberships', 'enrollments')))
    check('no resolver, period or overlap policy - "in effect on d" is answered by item 7\'s read-only in_effect() (7F), which is not one of those',
          callable(getattr(db, 'in_effect', None)) and not any(hasattr(db, n) for n in CONSUMER_NAMES))
    check('the guard is structural and only structural - no function says a role began, ended, or holds',
          not any(hasattr(db, n) for n in ('role_began', 'role_ended', 'role_holds', 'began_on', 'ended_on', 'boundaries_of_role')))
    check('the boundary vocabulary is exactly began / ended',
          db.BOUNDARIES == ('began', 'ended') and db.BOUNDARY_BEGAN == 'began' and db.BOUNDARY_ENDED == 'ended')
    check('the 1.x PersonEnrolment / PersonAssignment / HealthPlan periods are untouched and not decomposed',
          'person_enrolments' in db.Base.metadata.tables and 'effective_on' in {c.name for c in db.PersonEnrolment.__table__.columns}
          and not any(hasattr(db, n) for n in ('decompose_enrolments', 'backfill_roles', 'roles_for_enrolment')))


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
