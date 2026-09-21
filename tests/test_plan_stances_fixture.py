"""The insurer's stances and terms on P - the executable trace of `gw 2.0/CATALOGUES.md` pass 9D-iii (ruled s 9D-iii.7,
2026-09-20): `deductible`, `individual_deductible`, `plan_year` (the insurer's terms about P's rule), `deductible_applied`
and `individual_deductible_applied` (two kinds by shape, F1), `eligibility` (about (person, P) - the role read on the OBJECT
plan, F2: an application of the ruled relation, not a redefinition), `coverage_ended` (about P; three coverage-ended kinds,
F3), `authorization` (one kind, F5); the insurer holds the terms and the household relays (F4); 7J's any-party term read
stays 7J's.

What this slice can and cannot exercise
---------------------------------------
    the registry: eight kinds, the third table row, the SIDE table for the one object-read stance, one resolver          EXERCISED
    Ps1  Pl10: Aetna's family accumulator on P -> knowing; 7J's stated accumulator                                        EXERCISED
    Ps2  Pl10 individual: Aetna's figure on (Kim, P) -> its own kind, knowing; 7J's individual figure                     EXERCISED
    Ps3  F5: Aetna's "never eligible" about (Kim, P) -> knowing BY THE ROLE ON THE OBJECT PLAN                            EXERCISED
    Ps4  Rob's "Kim is eligible, they told me" -> not_knowing                                                              EXERCISED
    Ps5  Pl12: Aetna's coverage_ended on P -> knowing; P remains; no under_plan_ended manufactured                        EXERCISED
    Ps6  Pl12 disputed: Rob's coverage_ended -> not_knowing, established, beside                                          EXERCISED
    Ps7  Pl11: Aetna's authorization on P -> knowing; minted no expense                                                   EXERCISED
    Ps8  Pl2 / F4: Rob's "our deductible is $3,000" not_knowing; the SBC read candidate + knowing; Aetna knowing          EXERCISED
    Ps9  C2: "none" -> knowing, content opaque; 7J: the rule does not exist                                               EXERCISED
    Ps10 CC1 on P: Cigna's accumulator stance on Aetna's plan -> not_knowing                                              EXERCISED
    Ps11 the plan year by the household -> not_knowing; 7J's window still (F4, recorded)                                  EXERCISED
    Ps12 F7: an undated term -> undetermined; 7J disqualifies                                                              EXERCISED
    Ps13 the 2 x 2 on P: origin {Aetna, Rob} x kind {deductible_applied, eligibility}                                     EXERCISED
    Ps14 F6(i): the SBC line with the insurer as subject refused under the ruled name                                     EXERCISED
    F2's negative: eligibility read on the wrong side is not_knowing; the side is per kind, not per relation              EXERCISED
    7J's any-party term read (its own question); the determination (9D-v); values (9D-iv)                                NOT BUILT

Run:  python tests/test_plan_stances_fixture.py
"""
import sys
import tempfile
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL = [], []


def check(name, condition):
    (PASS if condition else FAIL).append(name)
    print(('  OK    ' if condition else '  FAIL  ') + name)


CATALOGUE = {'occurred_on': 'occurred_on', 'insurer_of': 'insurer_of', 'under_plan': 'under_plan', 'plan_insurer': 'insurer_of_plan',
             'eligibility': 'eligibility', 'deductible': 'deductible', 'individual_deductible': 'individual_deductible', 'plan_year': 'plan_year',
             'deductible_applied': 'deductible_applied', 'individual_deductible_applied': 'individual_deductible_applied',
             'expense_in_respect_of_plan': 'expense_in_respect_of_plan', 'applied_to_deductible': 'applied_to_deductible', 'incurred_by': 'incurred_by'}
ABSENT = ('terms_of', 'current_terms', 'deductible_of', 'plan_terms', 'is_eligible', 'eligible', 'coverage_status', 'plan_ended', 'terminate',
          'side_of', 'role_side', 'object_role')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_ps_')
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}}   # amount / occurred_on: ruled values since 9D-iv   # no entry for the eight ruled kinds

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

    def evidence(pr, utterance=None, reading=None):
        e = db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=utterance.id if utterance else None,
                                       reading_id=reading.id if reading else None)
        s.add(e)
        s.commit()
        return e

    def claim(kind, utterance=None, reading=None, as_of=None, content=None, **slots):
        obj = db.PARTICIPANT_ESTABLISHED if any(k.startswith('object_') for k in slots) else db.PARTICIPANT_NONE
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=obj, as_of=as_of, content=content, **slots)
        s.add(pr)
        s.commit()
        return evidence(pr, utterance=utterance, reading=reading), pr

    def held(h, origin_party):
        a = db.Artefact(held=True, content_hash=h, as_of='2026-01-01')
        s.add(a)
        s.commit()
        pr = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=a.id, object_party_id=origin_party.id)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utter('origin'))
        r = db.Reading(artefact_id=a.id, reader_process='parser/5', read_at=datetime(2026, 1, 6))
        s.add(r)
        s.commit()
        return a, r

    def st(rel):
        return db.derived_strength(s, rel, KNOWING)

    def on_plan(kind, P, content, as_of, origin=None, reading=None, person=None):
        return claim(kind, utterance=None if reading else utter(content, origin=origin), reading=reading, as_of=as_of, content=content,
                     subject_plan_id=P.id, **({'object_party_id': person.id} if person is not None else {}))

    def elig(person, P, content, as_of, origin=None, reading=None):
        return claim(db.ELIGIBILITY, utterance=None if reading else utter(content, origin=origin), reading=reading, as_of=as_of, content=content,
                     subject_party_id=person.id, object_plan_id=P.id)

    def acc(P, d, person=None):
        return db.accumulator(s, P, d, CATALOGUE, KNOWING, person=person)

    def pie(person, d):
        return db.plans_in_effect(s, person, d, CATALOGUE, KNOWING)

    aetna = mint(db.Party, 'Aetna.')
    cigna = mint(db.Party, 'Cigna.')
    P = mint(db.Plan, "Kim's Aetna plan.")
    claim(db.INSURER_OF_PLAN, utterance=utter('Aetna insures P.'), as_of='2026-01-01', subject_party_id=aetna.id, object_plan_id=P.id)
    claim(db.UNDER_PLAN, utterance=utter('Kim is on P.'), as_of='2026-01-01', subject_party_id=kim_party.id, object_plan_id=P.id)

    print('\n1. The registry - eight kinds, the third row, the SIDE for the one object-read stance, one resolver\n')
    on_P = (db.DEDUCTIBLE, db.INDIVIDUAL_DEDUCTIBLE, db.PLAN_YEAR, db.DEDUCTIBLE_APPLIED, db.COVERAGE_ENDED, db.AUTHORIZATION)
    check('six stances with the plan as subject and no object; individual_deductible_applied with the person as object (F1); eligibility with the person as subject and the plan as object (F5\'s shape); all KNOWING_PLAN_INSURER_AT_AS_OF, reading_establishes True; none a role',
          all(db.RULED_KINDS[k] == {'subject': ('subject_plan_id',), 'object': (), 'symmetric': False, 'reading_establishes': True, 'relational_knowing': True,
                                    'knowing_relation': db.KNOWING_PLAN_INSURER_AT_AS_OF} for k in on_P)
          and db.RULED_KINDS[db.INDIVIDUAL_DEDUCTIBLE_APPLIED] == {'subject': ('subject_plan_id',), 'object': ('object_party_id',), 'symmetric': False, 'reading_establishes': True,
                                                                   'relational_knowing': True, 'knowing_relation': db.KNOWING_PLAN_INSURER_AT_AS_OF}
          and db.RULED_KINDS[db.ELIGIBILITY] == {'subject': ('subject_party_id',), 'object': ('object_plan_id',), 'symmetric': False, 'reading_establishes': True,
                                                 'relational_knowing': True, 'knowing_relation': db.KNOWING_PLAN_INSURER_AT_AS_OF}
          and db.registry_violations() == [])
    check('the relation APPLIED: a third row (insurer_of_plan) on the ONE resolver; the SIDE table names eligibility alone as read on its object - keyed by the stance kind, not the relation; no terms / eligibility / coverage helper',
          db._ROLE_AT_AS_OF[db.KNOWING_PLAN_INSURER_AT_AS_OF] == db.INSURER_OF_PLAN and db._KNOWING_RELATIONS[db.KNOWING_PLAN_INSURER_AT_AS_OF] is db._role_at_as_of
          and len({db._KNOWING_RELATIONS[n] for n in db._ROLE_AT_AS_OF}) == 1
          and db._ROLE_AT_AS_OF_SIDE == {db.ELIGIBILITY: 'object'}
          and not any(hasattr(db, n) for n in ABSENT))
    check('the registry refuses: a deductible_applied with a person (that is the individual kind), an individual_deductible_applied without one, a plan-subject eligibility, a party-subject term',
          _refused(s, db.Proposition(kind=db.DEDUCTIBLE_APPLIED, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED, subject_plan_id=P.id, object_party_id=kim_party.id, content='$1', as_of='2026-03-01'))
          and _refused(s, db.Proposition(kind=db.INDIVIDUAL_DEDUCTIBLE_APPLIED, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE, subject_plan_id=P.id, content='$1', as_of='2026-03-01'))
          and _refused(s, db.Proposition(kind=db.ELIGIBILITY, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED, subject_plan_id=P.id, object_party_id=kim_party.id, content='x', as_of='2026-03-01'))
          and _refused(s, db.Proposition(kind=db.DEDUCTIBLE, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE, subject_party_id=aetna.id, content='$1', as_of='2026-03-01')))

    print('\n2. Ps8 / Ps9 / Ps11 / Ps12 - the terms: the insurer holds them; the household relays\n')
    e_rob, t_rob = on_plan(db.DEDUCTIBLE, P, '$3,000', '2026-01-01', origin=household)
    _, r_sbc = held('h-sbc', aetna)
    e_sbc, _ = on_plan(db.DEDUCTIBLE, P, '$3,000', '2026-01-01', reading=r_sbc)
    e_aet, t_aet = on_plan(db.DEDUCTIBLE, P, '$3,000', '2026-01-02', origin=aetna)
    check('Ps8 (Pl2 / F4): Rob\'s "our deductible is $3,000" -> NOT_KNOWING (a relay of the insurer\'s rule); the SBC read -> candidate in state, KNOWING in strength (origin Aetna, insurer of P); Aetna\'s own statement -> KNOWING',
          st(e_rob) == db.STRENGTH_NOT_KNOWING and st(e_sbc) == db.STRENGTH_KNOWING and st(e_aet) == db.STRENGTH_KNOWING)
    on_plan(db.PLAN_YEAR, P, '2026-12-31', '2026-01-01', origin=aetna)
    a8 = acc(P, '2026-03-31')
    # 7J-F4 (s 7J-F4.8) ruled the question this check had recorded: the governing term is the holder's - a claim with a knowing origin
    check('Ps8 (7J-F4 ruled): the governing term is the latest claim WITH A KNOWING ORIGIN - Aetna\'s own 1/2 statement; Rob\'s relay is listed, not_knowing, and does not govern',
          a8['term']['state'] == db.TERM_AMOUNT and a8['term']['value'] == D('3000') and a8['term']['claim'] == t_aet.id
          and [c['strength'] for c in a8['term']['claims'] if c['claim'] == t_rob.id] == [db.STRENGTH_NOT_KNOWING])
    H = mint(db.Plan, 'The HSA plan with no deductible.')
    claim(db.INSURER_OF_PLAN, utterance=utter('Aetna insures H.'), as_of='2026-01-01', subject_party_id=aetna.id, object_plan_id=H.id)
    on_plan(db.PLAN_YEAR, H, '2026-12-31', '2026-01-01', origin=aetna)
    e9, _ = on_plan(db.DEDUCTIBLE, H, 'none', '2026-01-01', origin=aetna)
    check('Ps9 (C2): Aetna states the deductible is "none" -> KNOWING; content opaque to the kind; 7J: the rule does not exist (TERM_NONE), not zero, not unknown',
          st(e9) == db.STRENGTH_KNOWING and acc(H, '2026-03-31')['term']['state'] == db.TERM_NONE)
    N = mint(db.Plan, 'A plan whose year the household stated.')
    claim(db.INSURER_OF_PLAN, utterance=utter('Cigna insures N.'), as_of='2026-01-01', subject_party_id=cigna.id, object_plan_id=N.id)
    e11, _ = on_plan(db.PLAN_YEAR, N, '2026-12-31', '2026-01-01', origin=household)
    on_plan(db.DEDUCTIBLE, N, '$500', '2026-01-01', origin=cigna)
    a11 = acc(N, '2026-03-31')
    check('Ps11 (7J-F4 ruled): the plan year stated by the household -> NOT_KNOWING; 7J\'s window does NOT take it - no window, the derived figure undetermined, the reason naming the household\'s statement as listed and not the insurer\'s',
          st(e11) == db.STRENGTH_NOT_KNOWING and a11['window']['start'] is None and 'household' in a11['window']['reason'] and a11['derived']['value'] is None)
    e12, t12 = on_plan(db.INDIVIDUAL_DEDUCTIBLE, P, '$1,500', None, origin=aetna)
    check('Ps12 (F7): an undated individual deductible term -> UNDETERMINED; 7J disqualifies it (no as_of)',
          st(e12) == db.STRENGTH_UNDETERMINED and acc(P, '2026-03-31', person=kim_party)['term']['claim'] != t12.id)

    print('\n3. Ps1 / Ps2 / Ps10 / Ps13 - the stated accumulator: two kinds by shape; the plan\'s insurer\n')
    e1, s1 = on_plan(db.DEDUCTIBLE_APPLIED, P, '$700', '2026-03-15', origin=aetna)
    a1 = acc(P, '2026-03-31')
    check('Ps1 (Pl10): Aetna\'s "applied $700 as of 3/15" on P -> KNOWING; 7J: the stated family accumulator, G named',
          st(e1) == db.STRENGTH_KNOWING and a1['stated']['governing']['claim'] == s1.id and a1['stated']['governing']['value'] == D('700'))
    e2, s2 = on_plan(db.INDIVIDUAL_DEDUCTIBLE_APPLIED, P, '$300', '2026-03-15', origin=aetna, person=kim_party)
    on_plan(db.INDIVIDUAL_DEDUCTIBLE, P, '$1,500', '2026-01-01', origin=aetna)
    a2 = acc(P, '2026-03-31', person=kim_party)
    check('Ps2 (Pl10 individual): Aetna\'s "Kim: $300 applied" on (Kim, P) -> ITS OWN KIND (F1), KNOWING; 7J reads the individual figure by that kind; the family figure is not it and it is not the family figure',
          st(e2) == db.STRENGTH_KNOWING and a2['stated']['governing']['claim'] == s2.id and a2['stated']['governing']['value'] == D('300')
          and a1['stated']['governing']['claim'] == s1.id and s2.kind != s1.kind)
    e10, s10 = on_plan(db.DEDUCTIBLE_APPLIED, P, '$900', '2026-03-20', origin=cigna)
    a10 = acc(P, '2026-03-31')
    check('Ps10 (CC1 on P): Cigna states an applied figure on Aetna\'s plan -> NOT_KNOWING (Cigna is not the insurer of P); 7J: not the stated accumulator (plan_insurer not in effect)',
          st(e10) == db.STRENGTH_NOT_KNOWING and a10['stated']['governing']['claim'] == s1.id
          and [c['qualifies'] for c in a10['stated']['claims'] if c['claim'] == s10.id] == [False])

    print('\n4. Ps3 / Ps4 / F2 - eligibility: the role read on the OBJECT plan\n')
    e3, _ = elig(kim_party, P, 'never eligible', '2026-02-01', origin=aetna)
    r3 = pie(kim_party, '2026-03-01')
    check('Ps3 (F5 / F2): Aetna\'s "Kim was never eligible" about (Kim, P) -> KNOWING - the role read on the OBJECT plan (Aetna insurer of P at 2/1), the subject the person; 7J lists it beside membership with plan_insurer in effect; membership unchanged (in effect)',
          st(e3) == db.STRENGTH_KNOWING and r3['plans'][P.id]['answer'] == db.EFFECT_IN
          and [(e['content'], e['plan_insurer']) for e in r3['plans'][P.id]['eligibility']] == [('never eligible', db.EFFECT_IN)])
    e4, _ = elig(kim_party, P, 'eligible - they told me', '2026-02-02', origin=household)
    check('Ps4: Rob\'s "Kim is eligible, they told me" about (Kim, P) -> NOT_KNOWING (Rob is not the plan\'s insurer); listed, plan_insurer not in effect',
          st(e4) == db.STRENGTH_NOT_KNOWING
          and all(e['plan_insurer'] != db.EFFECT_IN for e in pie(kim_party, '2026-03-01')['plans'][P.id]['eligibility'] if e['content'].startswith('eligible')))
    # F2's negative: the side is per KIND. Read eligibility on its subject and the person carries no plan-insurer role -> not_knowing.
    wrong_side = db._role_at_as_of(s, s.get(db.Proposition, e3.proposition_id), aetna.id, db.INSURER_OF_PLAN, side='subject')
    right_side = db._role_at_as_of(s, s.get(db.Proposition, e3.proposition_id), aetna.id, db.INSURER_OF_PLAN, side='object')
    check('F2 negative: the same eligibility claim read on its SUBJECT side answers NOT_KNOWING (a person bears no insurer_of_plan role) and on its OBJECT side KNOWING - the side is what 9D-iii adds, and it is the kind\'s, not the relation\'s',
          wrong_side == db.STRENGTH_NOT_KNOWING and right_side == db.STRENGTH_KNOWING)
    e3r, _ = elig(kim_party, P, 'never eligible', '2026-02-01', reading=r_sbc)
    check('Ps3\' (the reading path on the object-read stance): Aetna\'s letter read -> candidate in state, KNOWING in strength through the origin on the object plan',
          st(e3r) == db.STRENGTH_KNOWING and any(e['state'] == db.CLAIM_CANDIDATE for e in pie(kim_party, '2026-03-01')['plans'][P.id]['eligibility']))

    print('\n5. Ps5 / Ps6 / Ps7 / Ps13 / Ps14 - coverage ended is three kinds; the authorization; the 2 x 2 on P; the borrowed line\n')
    n_ended = s.query(db.Proposition).filter_by(kind=db.UNDER_PLAN_ENDED).count()
    e5, p5 = on_plan(db.COVERAGE_ENDED, P, '2026-06-30', '2026-08-15', origin=aetna)
    check('Ps5 (Pl12 / F3): Aetna\'s "coverage ended 6/30, retroactively" on P -> KNOWING; P remains minted; NO under_plan_ended manufactured for Kim and NO eligibility stance minted - three kinds, none derives another; 7J: Kim still in effect on 7/15 by the household\'s claim',
          st(e5) == db.STRENGTH_KNOWING and s.get(db.Plan, P.id) is not None
          and s.query(db.Proposition).filter_by(kind=db.UNDER_PLAN_ENDED).count() == n_ended
          and s.query(db.Proposition).filter_by(kind=db.ELIGIBILITY, subject_party_id=kim_party.id).count() == 3
          and pie(kim_party, '2026-07-15')['plans'][P.id]['answer'] == db.EFFECT_IN)
    e6, _ = on_plan(db.COVERAGE_ENDED, P, 'disputed - we paid through December', '2026-08-16', origin=household)
    check('Ps6 (Pl12 disputed): Rob\'s "that is wrong, we paid through December" as a coverage_ended claim on P -> established, NOT_KNOWING; two claims beside each other, nothing chooses',
          st(e6) == db.STRENGTH_NOT_KNOWING and s.query(db.Proposition).filter_by(kind=db.COVERAGE_ENDED, subject_plan_id=P.id).count() == 2)
    n_x = s.query(db.Expense).count()
    e7, _ = on_plan(db.AUTHORIZATION, P, 'MRI, lumbar - approved', '2026-02-10', origin=aetna)
    check('Ps7 (Pl11 / F5): Aetna\'s prior authorization on P, the service as content -> KNOWING; one kind; it minted no expense',
          st(e7) == db.STRENGTH_KNOWING and s.query(db.Expense).count() == n_x and 'authorized' not in db.RULED_KINDS)
    grid = {}
    for on, o in (('Aetna', aetna), ('Rob', household)):
        grid[(on, 'applied')] = st(on_plan(db.DEDUCTIBLE_APPLIED, P, '$1', '2026-03-25', origin=o)[0])
        grid[(on, 'eligibility')] = st(elig(kim_party, P, 'x', '2026-03-25', origin=o)[0])
    check('Ps13 (the 2 x 2 on P): (Aetna, applied) knowing · (Rob, applied) not · (Aetna, eligibility) knowing - by the role on the object · (Rob, eligibility) not; the type test called the two Aetna cells knowing and could not distinguish the shapes',
          grid == {('Aetna', 'applied'): db.STRENGTH_KNOWING, ('Rob', 'applied'): db.STRENGTH_NOT_KNOWING,
                   ('Aetna', 'eligibility'): db.STRENGTH_KNOWING, ('Rob', 'eligibility'): db.STRENGTH_NOT_KNOWING})
    check('Ps14 (F6-i): an SBC line figure whose subject is the INSURER and whose thing is a candidate is REFUSED under the ruled term; it keeps its shape under its stand-in (plan-identity renamed its line)',
          _refused(s, db.Proposition(kind=db.DEDUCTIBLE, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                     subject_party_id=aetna.id, content='$3,000 individual / $6,000 family', as_of='2026-01-01'))
          and not _refused(s, db.Proposition(kind='sbc_line_figure', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                             subject_party_id=aetna.id, content='$3,000 individual / $6,000 family', as_of='2026-01-01'))
          and 'sbc_line_figure' not in db.RULED_KINDS)

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
