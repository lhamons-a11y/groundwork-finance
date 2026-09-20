"""under_plan - the executable trace of `gw 2.0/RELATION_SEMANTICS.md` pass F (s F.8, accepted s F.10), built by
`gw 2.0/CATALOGUES.md` pass 9A (2026-09-19) as a SUBSTITUTION PROOF: the accepted relation and its two boundary kinds,
the first ruled role kind, and nothing else - who may assert it, who is knowing, candidate generation and the rest of
the role catalogue belong to 9B and are asserted absent here.

What this slice can and cannot exercise
---------------------------------------
    F1   a holds-at stance: party under plan as of a date; no beginning, no ending, nothing covered      EXERCISED
    F2   a beginning by the household; the card's "member since" a reading -> a candidate               EXERCISED
    F3   an ending as_of 6/30 recorded 8/15; the began row untouched; nothing about coverage            EXERCISED
    F4   two endings by two parties -> a dispute, derived; nothing chosen                                 EXERCISED
    F5   the evidence boundary: Aetna's "never eligible" beside; the household's claim stands            EXERCISED
    F6   a retraction of the beginning is not an ending                                                  EXERCISED
    F7   two beginnings, no ending -> overlap represented, never resolved                                EXERCISED
    F8   the newborn: as_of the birth, recorded later; no precedence from creation order                  EXERCISED
    F9   COBRA: either arm representable; the substrate infers neither                                    EXERCISED
    F10  subscriber != under: four claims; no subscriber kind                                             EXERCISED
    F11  persons, not the household: one claim per named party                                            EXERCISED
    F12  a plan with no claims: no known members is not no members                                        EXERCISED
    F13  E24 from F's side: nothing about an expense follows from membership                              EXERCISED
    F14  the reverse: no membership derived from an expense in respect of a plan                          EXERCISED
    F15  the insurer may assert as a party; from a reading a candidate                                    EXERCISED
    F16  a party that is not a Person can be under a plan                                                 EXERCISED
    F17  direction by type; no inverse kind; no selector                                                  EXERCISED
    F18  vocabulary: active / terminated / enrolled / member are not kinds                                 EXERCISED
    F19  the floor: exactly that and nothing about coverage                                                EXERCISED
    F20  MANDATORY: two plans, two claims, nothing selected                                                EXERCISED
    the registry: three entries exactly as accepted; the boundary guard on a real role kind               EXERCISED
    who may assert, knowing, candidate generation, the rest of the role catalogue (9B), E (9C)            NOT BUILT

Run:  python tests/test_under_plan_fixture.py
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


ABSENT_KINDS = ('plan_covers_party', 'plan_members', 'member_of', 'covered_under', 'membership', 'enrolled_in', 'subscriber',
                'subscriber_of', 'eligible', 'premium_active', 'plan_covers_expense', 'plan_covers_obligation', 'plan_covers_payment')
ABSENT_HELPERS = ('plan_members', 'members_of', 'current_plan_of', 'plan_of_person', 'primary_plan', 'selected_plan', 'is_eligible',
                  'is_active', 'is_member', 'membership_of', 'covered_by', 'plans_of', 'under_plan_period')
PERIOD_WORDS = ('effective', 'period', 'valid_from', 'valid_to', 'from_date', 'to_date', 'members', 'plan_id', 'member_of')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_up_')
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


def run(db):
    s = _fresh()
    rob = db.Person(display_name='Rob')
    kim = db.Person(display_name='Kim')
    s.add_all([rob, kim])
    s.commit()
    household, kim_party = rob.party, kim.party

    def utter(text, when='2026-01-05T09:00:00', origin=None):
        u = db.Utterance(origin_party_id=(origin or household).id, asserted_at=when, content=text)
        s.add(u)
        s.commit()
        return u

    def mint(cls, text, origin=None):
        u = utter(text, origin=origin)
        x = cls(minted_by_id=u.id)
        s.add(x)
        s.commit()
        return x

    def held(h, origin_party):
        a = db.Artefact(held=True, content_hash=h, as_of='2026-01-01')
        s.add(a)
        s.commit()
        pr = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=a.id, object_party_id=origin_party.id)
        s.add(pr)
        s.commit()
        s.add(db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=utter('origin').id))
        s.commit()
        r = db.Reading(artefact_id=a.id, reader_process='parser/5', read_at=datetime(2026, 1, 5))
        s.add(r)
        s.commit()
        return a, r

    def evidence(pr, utterance=None, reading=None):
        e = db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=utterance.id if utterance else None,
                                       reading_id=reading.id if reading else None)
        s.add(e)
        s.commit()
        return e

    def claim(kind, utterance=None, reading=None, as_of=None, content=None, created=None, **slots):
        obj = db.PARTICIPANT_ESTABLISHED if any(k.startswith('object_') for k in slots) else db.PARTICIPANT_NONE
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=obj, as_of=as_of, content=content, **slots)
        if created is not None:
            pr.created_at = created
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utterance, reading=reading)
        return pr

    def under(party, plan, as_of, utterance=None, reading=None, kind=None, created=None):
        return claim(kind or db.UNDER_PLAN, utterance=utterance if (utterance or reading) else utter(f'under {as_of}'), reading=reading,
                     as_of=as_of, created=created, subject_party_id=party.id, object_plan_id=plan.id)

    def retract(u, text):
        r = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                           subject_utterance_id=u.id)
        s.add(r)
        s.commit()
        evidence(r, utterance=utter(text, '2026-04-20T09:00:00'))

    def claims(kind, **f):
        return s.query(db.Proposition).filter_by(kind=kind, **f)

    aetna = mint(db.Party, 'Aetna.')
    P = mint(db.Plan, "Kim's employer plan.")
    P2 = mint(db.Plan, "Rob's marketplace plan.")

    print('\n1. The registry - three entries exactly as accepted; the boundary metadata\'s first entries; nothing else\n')
    rule, began, ended = db.RULED_KINDS[db.UNDER_PLAN], db.RULED_KINDS[db.UNDER_PLAN_BEGAN], db.RULED_KINDS[db.UNDER_PLAN_ENDED]
    check('under_plan is ruled: party subject, plan object, not symmetric, a reading never establishes, relational knowing with NO named relation on under_plan itself (F: undetermined; the 9B roles name theirs); marked a role (9B-F1)',
          rule == {'subject': ('subject_party_id',), 'object': ('object_plan_id',), 'symmetric': False, 'reading_establishes': False, 'relational_knowing': True, 'role': True})
    check('under_plan_began / under_plan_ended are bound to under_plan by the boundary metadata - the same slots, boundary began / ended, of under_plan; the registry guard passes',
          began.get('boundary') == db.BOUNDARY_BEGAN and ended.get('boundary') == db.BOUNDARY_ENDED and began.get('of') == ended.get('of') == db.UNDER_PLAN
          and began['subject'] == ended['subject'] == rule['subject'] and began['object'] == ended['object'] == rule['object']
          and db.registry_violations() == [])
    check('under_plan\'s two boundary entries are bound to it and to nothing else; under_plan is marked a role (9B-F1, classification only)',
          {k for k, r in db.RULED_KINDS.items() if r.get('of') == db.UNDER_PLAN} == {db.UNDER_PLAN_BEGAN, db.UNDER_PLAN_ENDED}
          and db.RULED_KINDS[db.UNDER_PLAN].get('role') is True)
    check('no coverage / membership / subscriber / eligibility kind was minted beside it; no selector, inverse or period helper exists',
          not any(k in db.RULED_KINDS for k in ABSENT_KINDS) and not any(hasattr(db, n) for n in ABSENT_HELPERS))
    check('no period, members or plan_id column on any anchor',
          not any(any(w in c.name for w in PERIOD_WORDS) for cls in (db.Party, db.Plan, db.Expense, db.Obligation, db.Payment, db.Person) for c in cls.__table__.columns))

    print('\n2. F1 / F2 / F3 / F19 - the floor: a stance, a beginning, an ending; nothing derived\n')
    f1 = under(kim_party, P, '2026-01-05', utterance=utter('Kim is on the work plan.'))
    check('F1 (R1): "Kim is on the work plan" -> one under_plan claim with two established participants, as_of the stance date; no beginning implied, no ending, nothing covered',
          f1.subject_party_id == kim_party.id and f1.object_plan_id == P.id and f1.as_of == '2026-01-05'
          and claims(db.UNDER_PLAN_BEGAN).count() == 0 and claims(db.UNDER_PLAN_ENDED).count() == 0)
    f2 = under(kim_party, P, '2026-01-01', utterance=utter("Kim's been on it since January 1."), kind=db.UNDER_PLAN_BEGAN)
    card, r_card = held('h-card', aetna)
    f2c = under(kim_party, P, '2026-01-01', reading=r_card, kind=db.UNDER_PLAN_BEGAN)
    check('F2 (R2 / R11): the beginning asserted by Rob is established; the card\'s "Member since 01/01/2026" read is a CANDIDATE for the same claim (a reading never establishes a role)',
          s.query(db.EvidentiaryRelationship).filter_by(proposition_id=f2.id).one().utterance_id is not None
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=f2c.id).one().reading_id == r_card.id
          and db.RULED_KINDS[db.UNDER_PLAN_BEGAN]['reading_establishes'] is False)
    f3 = under(kim_party, P, '2026-06-30', utterance=utter('Coverage ended June 30.', '2026-08-15T09:00:00', origin=aetna), kind=db.UNDER_PLAN_ENDED,
               created=datetime(2026, 8, 15, 9))
    check('F3 (R3): an ending as_of 6/30 recorded 8/15 (effective-at != learned-at); the began row untouched; no row rewritten',
          f3.as_of == '2026-06-30' and f3.created_at == datetime(2026, 8, 15, 9) and s.get(db.Proposition, f2.id).as_of == '2026-01-01'
          and claims(db.UNDER_PLAN_BEGAN, subject_party_id=kim_party.id, object_plan_id=P.id).count() == 2)
    check('F19 (the floor): the claims establish exactly under_plan and nothing about coverage of any service, enrollment, the subscriber, the premium or terms - no such kind, slot or helper exists',
          not any(k in db.RULED_KINDS for k in ABSENT_KINDS) and not any(hasattr(db, n) for n in ABSENT_HELPERS))

    print('\n3. F4 / F5 / F6 / F7 / F20 - disputes derived; the evidence boundary; retraction; overlap; nothing selected\n')
    f4 = under(kim_party, P, '2026-12-31', utterance=utter('It ran through December.'), kind=db.UNDER_PLAN_ENDED)
    check('F4 (R5): Aetna\'s ending 6/30 and Rob\'s ending 12/31 - two claims, two parties, both stand; nothing chosen, no "current membership" accessor',
          claims(db.UNDER_PLAN_ENDED, subject_party_id=kim_party.id, object_plan_id=P.id).count() == 2 and not hasattr(db, 'current_membership'))
    never = claim('eligibility', utterance=utter('Kim was never eligible.', origin=aetna), as_of='2026-09-01', content='never eligible',
                  subject_party_id=kim_party.id, object_plan_id=P.id)
    check('F5 (the evidence boundary): Aetna\'s "never eligible" is its own stance beside Rob\'s under_plan claims; the under_plan claims still stand unchanged - contest derived, nothing erased, nothing overridden',
          s.get(db.Proposition, f1.id) is not None and s.get(db.Proposition, f2.id) is not None and never.kind != db.UNDER_PLAN
          and claims(db.UNDER_PLAN, subject_party_id=kim_party.id, object_plan_id=P.id).count() == 1)
    u6 = utter('Kim is on the dental plan.')
    D = mint(db.Plan, 'The dental plan.')
    f6 = under(kim_party, D, '2026-02-01', utterance=u6, kind=db.UNDER_PLAN_BEGAN)
    retract(u6, 'I was wrong - Kim was never on the dental plan.')
    check('F6 (R6): the retraction of the utterance behind the dental beginning is a retraction, NOT an under_plan_ended claim; the beginning\'s row and history survive',
          claims(db.UNDER_PLAN_ENDED, object_plan_id=D.id).count() == 0 and s.get(db.Proposition, f6.id) is not None
          and claims(db.UTTERANCE_RETRACTION, subject_utterance_id=u6.id).count() == 1)
    under(kim_party, P2, '2026-07-01', utterance=utter("Kim is on my marketplace plan from July."), kind=db.UNDER_PLAN_BEGAN)
    check('F7 (R7) / F20 (MANDATORY): Kim under P (began 1/1, contested ending) and under P2 (began 7/1) - two separately asserted claims; overlap REPRESENTED (both rows), never resolved; no primary / selector / exclusivity',
          claims(db.UNDER_PLAN_BEGAN, subject_party_id=kim_party.id).filter(db.Proposition.object_plan_id.in_([P.id, P2.id])).count() == 3
          and not any(hasattr(db, n) for n in ('current_plan_of', 'plan_of_person', 'primary_plan', 'selected_plan')))
    aug = db.in_effect(s, kim_party, db.UNDER_PLAN, '2026-08-01')
    check('F20 / F4: the 7F consumer, read over the ruled kind, reports P2 in effect and P CONTESTED in August (its two endings dispute the date) - the same answers the stand-in gave; nothing selected',
          aug['in_effect'] == [P2.id] and aug['identities'][P.id]['answer'] == db.EFFECT_CONTESTED)

    print('\n4. F8 / F9 / F10 / F11 / F12 / F15 / F16 - no precedence from creation; both COBRA arms; subscriber; persons; no claims; the insurer as a party; a non-Person party\n')
    baby = mint(db.Party, 'The baby, born 4/3.')
    f8 = under(baby, P, '2026-04-03', utterance=utter('The baby is on the plan from her birth.', '2026-05-02T09:00:00'), kind=db.UNDER_PLAN_BEGAN,
               created=datetime(2026, 5, 2, 9))
    check('F8 (the newborn): as_of 4/3, recorded 5/2 - no precedence from creation order; the party was minted after the date it came under P; nothing derives "eligible since birth"',
          f8.as_of == '2026-04-03' and f8.created_at > datetime(2026, 4, 3) and not hasattr(db, 'eligible_since'))
    Pc = mint(db.Plan, 'The COBRA continuation, as a new plan.')
    under(household, Pc, '2026-09-01', utterance=utter('COBRA from September, treated as a new plan.'), kind=db.UNDER_PLAN_BEGAN)
    under(household, P, '2026-08-31', utterance=utter('The employer plan ended August 31.'), kind=db.UNDER_PLAN_ENDED)
    check('F9 (COBRA): the new-plan arm is representable (began under Pc; ended under P) and the same-plan arm needs no claim; the substrate infers neither',
          claims(db.UNDER_PLAN_BEGAN, object_plan_id=Pc.id).count() == 1 and claims(db.UNDER_PLAN_ENDED, subject_party_id=household.id, object_plan_id=P.id).count() == 1
          and 'continuation' not in db.RULED_KINDS and 'cobra' not in db.RULED_KINDS)
    child1, child2 = mint(db.Party, 'Child one.'), mint(db.Party, 'Child two.')
    for who in (household, child1, child2):
        under(who, P, '2026-01-01', utterance=utter('on the plan'))
    check('F10 (subscriber != under): Rob, Kim and the children are under P - four under_plan claims; no subscriber kind, no derivation of the subscriber from the claims or the premium',
          claims(db.UNDER_PLAN, object_plan_id=P.id).count() == 4 and not any(k in db.RULED_KINDS for k in ('subscriber', 'subscriber_of', 'policyholder')))
    check('F11 (persons, not the household): every claim names a party - none names "the household"; no household-level membership',
          all(c.subject_party_id is not None for c in claims(db.UNDER_PLAN)) and not hasattr(db, 'household_under'))
    Empty = mint(db.Plan, 'A plan with no members entered (Pl15).')
    check('F12 (Pl15): a plan with no under_plan claims - no known members, which is not no members; no Rob by default; the 7F consumer reports no stance',
          claims(db.UNDER_PLAN, object_plan_id=Empty.id).count() == 0 and claims(db.UNDER_PLAN_BEGAN, object_plan_id=Empty.id).count() == 0
          and Empty.id not in db.in_effect(s, household, db.UNDER_PLAN, '2026-08-01')['identities'])
    f15 = under(kim_party, P2, '2026-07-01', utterance=utter('Kim enrolled effective July 1.', origin=aetna), kind=db.UNDER_PLAN_BEGAN)
    conf, r_conf = held('h-enrollment-confirmation', aetna)
    f15c = under(kim_party, P2, '2026-07-01', reading=r_conf, kind=db.UNDER_PLAN_BEGAN)
    check('F15 (the insurer asserts): Aetna as a party MAY assert under_plan_began (established, origin Aetna); the same from a reading of its confirmation is a candidate; knowing undetermined (no named relation); the insurer\'s assertion does not outrank the household\'s',
          s.query(db.EvidentiaryRelationship).filter_by(proposition_id=f15.id).one().utterance.origin_party_id == aetna.id
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=f15c.id).one().reading_id == r_conf.id
          and db.RULED_KINDS[db.UNDER_PLAN].get('knowing_relation') is None and not hasattr(db, 'insurer_outranks'))
    ex = mint(db.Party, "Rob's ex-spouse (by court order; not a Groundwork Person).")
    f16 = under(ex, P, '2026-01-01', utterance=utter('My ex stays on the plan by court order.'))
    check('F16 (the ex-spouse): a minted party that is not a Person is under P - the subject slot takes any established party; no Person manufactured',
          f16.subject_party_id == ex.id and s.get(db.Party, ex.id).person_id is None and s.query(db.Person).count() == 2)

    print('\n5. F13 / F14 / F17 / F18 - nothing to or from an expense; direction; no inverse; vocabulary\n')
    X = mint(db.Expense, "Kim's visit on 3/1.")
    claim('incurred_by', utterance=utter('incurred by Kim'), subject_party_id=kim_party.id, object_expense_id=X.id)
    check('F13 (E24 from F\'s side): Kim under P during T and X is Kim\'s, incurred on d in T -> NOTHING about X follows: no expense_in_respect_of_plan claim, no candidate, no kind or helper carrying plan attribution',
          s.query(db.Proposition).filter(db.Proposition.subject_expense_id == X.id, db.Proposition.object_plan_id.isnot(None)).count() == 0
          and not any(hasattr(db, n) for n in ('plan_for_expense', 'which_plan', 'plan_of_expense', 'coverage_of')))
    Y = mint(db.Expense, "A visit somebody said was on P2.")
    claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('that visit was on P2'), subject_expense_id=Y.id, object_plan_id=P2.id)
    stranger = mint(db.Party, 'Somebody nobody has said is under any plan.')
    claim('incurred_by', utterance=utter('incurred by the stranger'), subject_party_id=stranger.id, object_expense_id=Y.id)
    check('F14 (the reverse): an expense asserted in respect of P2, incurred by a party nobody said is under P2 -> NO membership derived; no under_plan claim for that party exists or is manufactured',
          claims(db.UNDER_PLAN, subject_party_id=stranger.id).count() == 0 and claims(db.UNDER_PLAN_BEGAN, subject_party_id=stranger.id).count() == 0
          and stranger.id not in [c.subject_party_id for c in claims(db.UNDER_PLAN)])
    check('F17 (direction; inverse; resolver): the subject is the party and the object the plan, by type; a plan-subject claim is refused by the registry; no inverse kind, no selector',
          _refused(s, db.Proposition(kind=db.UNDER_PLAN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_plan_id=P.id, object_party_id=kim_party.id))
          and not any(k in db.RULED_KINDS for k in ('plan_has_party', 'plan_members', 'plan_covers_party'))
          and not any(hasattr(db, n) for n in ('members_of', 'current_plan_of')))
    check('F18 (vocabulary): on the plan / under / enrolled / eligible / member / dependent / subscriber / active / terminated are not kinds - "terminated" becomes an ended claim only when a party asserts the ending',
          not any(k in db.RULED_KINDS for k in ('on_the_plan', 'enrolled', 'eligible', 'member', 'dependent', 'subscriber', 'active', 'terminated', 'inactive')))

    print('\n6. The boundary guard on a real role kind; the absences held for 9B\n')
    check('the boundary guard on the ruled kind: an under_plan_began without as_of is refused; a boundary claim of a non-role kind is refused; a beginning with mismatched participants is refused',
          _refused(s, db.Proposition(kind=db.UNDER_PLAN_BEGAN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_party_id=kim_party.id, object_plan_id=P.id))
          and _refused(s, db.Proposition(kind=db.UNDER_PLAN_BEGAN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_party_id=kim_party.id, object_obligation_id=1, as_of='2026-01-01')))
    # HISTORICAL ORACLE UNDER THE LATER STATE. 9B (2026-09-19) has since ruled the role catalogue: the seven 9B roles name
    # KNOWING_SUBJECT_PARTY. That is a statement about THOSE kinds. under_plan's knowing relation is unnamed because pass F
    # ruled it undetermined - a fact about under_plan that is still true of the final registry, NOT a claim that the registry
    # names no knowing relation. The check states both halves so it cannot be read the wrong way.
    check('under_plan names NO knowing relation (F: undetermined - a fact about under_plan, not about the registry) while the seven 9B roles name KNOWING_SUBJECT_PARTY; 9A itself established nothing about who may assert, candidates or matching',
          db.RULED_KINDS[db.UNDER_PLAN].get('knowing_relation') is None
          and all(db.RULED_KINDS[k].get('knowing_relation') == db.KNOWING_SUBJECT_PARTY
                  for k, r in db.RULED_KINDS.items() if r.get('role') and k != db.UNDER_PLAN)
          and not any(hasattr(db, n) for n in ('may_assert_under_plan', 'under_plan_candidates', 'match_membership')))

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
