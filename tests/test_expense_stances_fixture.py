"""The provider's and insurer's stances on X - the executable trace of `gw 2.0/CATALOGUES.md` pass 9D-ii (ruled s 9D-ii.7,
2026-09-19): `billed` (the provider's), `patient_responsibility`, `plan_paid`, `applied_to_deductible`, `denial`,
`adjudication` (the insurer's) - the role-at-date relation APPLIED on X through two rows in the table, not re-ruled;
`denial` and `adjudication` two kinds by name with opaque content (C7); the one consumer gate not on X (7J selects
`applied_to_deductible` by the PLAN's insurer under CC1) the consumer's - the kind-level holder is insurer_of X; the EOB
relay: origin is not a role claim.

What this slice can and cannot exercise
---------------------------------------
    the registry: six kinds on X, two rows in the table, one resolver, content opaque, no family                EXERCISED
    Xs1  Rc9: Mercy's bill read -> billed candidate, knowing (origin Mercy in role)                                EXERCISED
    Xs2  F3 / K5: Rob's "the EOB said $400" -> not_knowing; reported, never governing                             EXERCISED
    Xs3  the EOB's own billed column -> NOT knowing for billed (the insurer relays the provider's charge)          EXERCISED
    Xs4  Rc10: two Aetna PR stances at one date -> both knowing; 7H conflict -> none                               EXERCISED
    Xs5  CC1 / Ju11: Aetna and Cigna each applied on one X -> BOTH knowing at kind level; 7J per plan              EXERCISED
    Xs6  C6: applied 'none' -> knowing, content opaque; 7J exempt, not zero                                        EXERCISED
    Xs7  C7 / Rc6: the denial - its own kind, knowing; not a determination; 7H does not read it                   EXERCISED
    Xs8  E3: 'reversed' - an adjudication, knowing; no consumer                                                     EXERCISED
    Xs9  the provider states plan_paid -> not_knowing                                                              EXERCISED
    Xs10 the 2 x 2 on X: origin {Mercy, Aetna} x kind {billed, PR}                                                  EXERCISED
    Xs11 the insurer's role contested at the stance's date -> undetermined                                         EXERCISED
    Xs12 F7: an undated stance -> undetermined; 7H disqualifies                                                    EXERCISED
    Xs13 F2(i): the EOB line with the insurer as subject refused under the ruled name                              EXERCISED
    Xs14 F2(ii): knowing needs the role in the record - by type it is nothing                                       EXERCISED
    the determination (9D-v); the insurer's stances on P (9D-iii); the plan gate's own semantics (7J's)           NOT BUILT

Run:  python tests/test_expense_stances_fixture.py
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


CATALOGUE = {'acknowledgment': 'acknowledged', 'entitled_party': 'entitled_party_of', 'balance': 'balance',
             'payment_amount': 'amount', 'occurred_on': 'occurred_on', 'paid_by': 'paid_by', 'paid_to': 'paid_to',
             'billed': 'billed', 'patient_responsibility': 'patient_responsibility', 'plan_paid': 'plan_paid',
             'determination': 'determination', 'provider_of': 'provider_of', 'insurer_of': 'insurer_of'}
ACC = {'occurred_on': 'occurred_on', 'insurer_of': 'insurer_of', 'under_plan': 'under_plan', 'plan_insurer': 'insurer_of_plan',
       'eligibility': 'eligibility', 'deductible': 'deductible', 'individual_deductible': 'individual_deductible', 'plan_year': 'plan_year',
       'deductible_applied': 'deductible_applied', 'individual_deductible_applied': 'individual_deductible_applied', 'expense_in_respect_of_plan': 'expense_in_respect_of_plan',
       'applied_to_deductible': 'applied_to_deductible', 'incurred_by': 'incurred_by'}
ABSENT = ('verdict', 'is_denied', 'denied', 'adjudicate', 'interpret_content', 'parse_verdict', 'plan_of_stance', 'stance_plan',
          'relay_knowing')   # (the plan insurer's relation name was pinned absent here until 9D-iii applied it - the exact-pin class, retired)


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_xs_')
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
    s.add(rob)
    s.commit()
    household = rob.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'},
               }   # no entry for any ruled kind: their knowing is the registry's; determination (9D-v) undetermined by design

    def utter(text, when='2026-03-03T09:00:00', origin=None):
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
        a = db.Artefact(held=True, content_hash=h, as_of='2026-03-10')
        s.add(a)
        s.commit()
        pr = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=a.id, object_party_id=origin_party.id)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utter('origin'))
        r = db.Reading(artefact_id=a.id, reader_process='parser/5', read_at=datetime(2026, 3, 11))
        s.add(r)
        s.commit()
        return a, r

    def st(rel):
        return db.derived_strength(s, rel, KNOWING)

    def stance(kind, X, amount, as_of, origin=None, reading=None):
        return claim(kind, utterance=None if reading else utter(amount, origin=origin), reading=reading, as_of=as_of, content=amount, subject_expense_id=X.id)

    def role(kind, party, X, as_of='2026-01-01'):
        return claim(kind, utterance=utter(f'{kind} {as_of}'), as_of=as_of, subject_party_id=party.id, object_expense_id=X.id)

    def rec(X, d):
        return db.reconciliation(s, X, d, CATALOGUE, KNOWING)

    mercy = mint(db.Party, 'Mercy Hospital.')
    aetna = mint(db.Party, 'Aetna.')
    cigna = mint(db.Party, 'Cigna.')
    X = mint(db.Expense, 'The ER visit, 2/14.')
    role(db.PROVIDER_OF, mercy, X)
    role(db.INSURER_OF, aetna, X)

    print('\n1. The registry - six kinds on X, two rows in the table, one resolver, content opaque\n')
    six = (db.BILLED, db.PATIENT_RESPONSIBILITY, db.PLAN_PAID, db.APPLIED_TO_DEDUCTIBLE, db.DENIAL, db.ADJUDICATION)
    check('six stance kinds with the expense as subject and no object, reading_establishes True, relational knowing; billed by KNOWING_PROVIDER_AT_AS_OF, the five by KNOWING_INSURER_AT_AS_OF; none a role, none bounded',
          all(db.RULED_KINDS[k] == {'subject': ('subject_expense_id',), 'object': (), 'symmetric': False, 'reading_establishes': True, 'relational_knowing': True,
                                    'knowing_relation': (db.KNOWING_PROVIDER_AT_AS_OF if k == db.BILLED else db.KNOWING_INSURER_AT_AS_OF)} for k in six)
          and db.registry_violations() == [])
    check('the relation APPLIED, not re-ruled: 9D-ii\'s two rows (provider_of, insurer_of) beside 9D-i\'s, every role-at-date name on the ONE resolver; no verdict / content interpreter, no plan-of-stance helper',
          db._ROLE_AT_AS_OF[db.KNOWING_PROVIDER_AT_AS_OF] == db.PROVIDER_OF and db._ROLE_AT_AS_OF[db.KNOWING_INSURER_AT_AS_OF] == db.INSURER_OF
          and db._ROLE_AT_AS_OF[db.KNOWING_ENTITLED_PARTY_AT_AS_OF] == db.ENTITLED_PARTY_OF
          and len({db._KNOWING_RELATIONS[n] for n in db._ROLE_AT_AS_OF}) == 1 and db._KNOWING_RELATIONS[db.KNOWING_INSURER_AT_AS_OF] is db._role_at_as_of
          and not any(hasattr(db, n) for n in ABSENT))
    check('denial and adjudication are TWO kinds by name (C7): each its own entry; neither carries a verdict key; the registry refuses a party-subject or an object on any of the six',
          db.DENIAL != db.ADJUDICATION and db.DENIAL in db.RULED_KINDS and db.ADJUDICATION in db.RULED_KINDS
          and not any('verdict' in r or 'content' in r for k, r in db.RULED_KINDS.items() if k in six)
          and _refused(s, db.Proposition(kind=db.DENIAL, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE, subject_party_id=aetna.id, content='x', as_of='2026-03-01'))
          and _refused(s, db.Proposition(kind=db.PATIENT_RESPONSIBILITY, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_expense_id=X.id, object_plan_id=1, content='$1', as_of='2026-03-01')))

    print('\n2. Xs1 / Xs2 / Xs3 / Xs9 / Xs10 - whose position: the provider\'s charge, the insurer\'s figures, the relay\n')
    e1, b1 = stance(db.BILLED, X, '$1,300', '2026-03-05', origin=mercy)
    _, r_bill = held('h-bill', mercy)
    e1r, _ = stance(db.BILLED, X, '$1,300', '2026-03-05', reading=r_bill)
    r9 = rec(X, '2026-03-31')
    check('Xs1 (Rc9): Mercy states billed $1,300 -> KNOWING (provider of X in effect at 3/5); Mercy\'s bill read -> candidate in state, KNOWING in strength; 7H: Mercy\'s utterance governs, the reading never does',
          st(e1) == db.STRENGTH_KNOWING and st(e1r) == db.STRENGTH_KNOWING
          and r9['stances']['billed']['governing']['claim'] == b1.id and [c['state'] for c in r9['stances']['billed']['claims'] if c['claim'] != b1.id] == [db.CLAIM_CANDIDATE])
    e2, p2 = stance(db.PATIENT_RESPONSIBILITY, X, '$400', '2026-03-08', origin=household)
    check('Xs2 (F3 / K5): Rob says "the EOB said $400" - a PR claim by the household -> NOT_KNOWING (Rob holds no role on X); 7H: reported as a fact, never governing',
          st(e2) == db.STRENGTH_NOT_KNOWING and [c['qualifies'] for c in rec(X, '2026-03-31')['stances']['patient_responsibility']['claims'] if c['claim'] == p2.id] == [False])
    _, r_eob = held('h-eob', aetna)
    e3pp, _ = stance(db.PLAN_PAID, X, '$568', '2026-03-10', reading=r_eob)
    e3pr, _ = stance(db.PATIENT_RESPONSIBILITY, X, '$412', '2026-03-10', reading=r_eob)
    e3b, _ = stance(db.BILLED, X, '$1,300', '2026-03-10', reading=r_eob)
    check('Xs3 (the EOB\'s billed column): the EOB read - plan_paid and PR KNOWING (origin Aetna, insurer of X); its billed column NOT_KNOWING - the insurer relays the provider\'s charge; origin is not a role claim; relaying does not launder',
          st(e3pp) == db.STRENGTH_KNOWING and st(e3pr) == db.STRENGTH_KNOWING and st(e3b) == db.STRENGTH_NOT_KNOWING)
    e9, p9 = stance(db.PLAN_PAID, X, '$568', '2026-03-12', origin=mercy)
    check('Xs9: Mercy states "plan paid $568" -> NOT_KNOWING (the provider is not the insurer of X); 7H: reported, not in the insurer\'s series',
          st(e9) == db.STRENGTH_NOT_KNOWING and [c['qualifies'] for c in rec(X, '2026-03-31')['stances']['plan_paid']['claims'] if c['claim'] == p9.id] == [False])
    grid = {(on, kn): st(stance(k, X, '$1', '2026-03-15', origin=o)[0])
            for on, o in (('Mercy', mercy), ('Aetna', aetna)) for kn, k in (('billed', db.BILLED), ('PR', db.PATIENT_RESPONSIBILITY))}
    check('Xs10 (the 2 x 2 on X): (Mercy, billed) knowing · (Aetna, billed) not · (Mercy, PR) not · (Aetna, PR) knowing - the type test called all four knowing; the role tells whose position each is',
          grid == {('Mercy', 'billed'): db.STRENGTH_KNOWING, ('Aetna', 'billed'): db.STRENGTH_NOT_KNOWING,
                   ('Mercy', 'PR'): db.STRENGTH_NOT_KNOWING, ('Aetna', 'PR'): db.STRENGTH_KNOWING})

    print('\n3. Xs4 / Xs5 / Xs6 - one date, two stances; two insurers, one X; exempt\n')
    X4 = mint(db.Expense, 'A visit with two EOBs on one day.')
    role(db.INSURER_OF, aetna, X4)
    role(db.PROVIDER_OF, mercy, X4)
    stance(db.BILLED, X4, '$900', '2026-01-10', origin=mercy)
    e4a, _ = stance(db.PATIENT_RESPONSIBILITY, X4, '$412', '2026-01-15', origin=aetna)
    e4b, _ = stance(db.PATIENT_RESPONSIBILITY, X4, '$380', '2026-01-15', origin=aetna)
    r4 = rec(X4, '2026-01-31')
    check('Xs4 (Rc10): two Aetna PR stances at one date - BOTH knowing at the kind level; 7H: conflict -> no governing PR, both listed (TS is the consumer\'s)',
          st(e4a) == st(e4b) == db.STRENGTH_KNOWING and r4['stances']['patient_responsibility']['governing'] is None and len(r4['stances']['patient_responsibility']['conflict']) == 2)
    P_A, P_B = mint(db.Plan, 'Plan A (Aetna).'), mint(db.Plan, 'Plan B (Cigna).')
    claim(db.INSURER_OF_PLAN, utterance=utter('Aetna insures A.'), as_of='2026-01-01', subject_party_id=aetna.id, object_plan_id=P_A.id)
    claim(db.INSURER_OF_PLAN, utterance=utter('Cigna insures B.'), as_of='2026-01-01', subject_party_id=cigna.id, object_plan_id=P_B.id)
    for P in (P_A, P_B):
        claim('plan_year', utterance=utter('2026'), as_of='2026-01-01', content='2026-12-31', subject_plan_id=P.id)
        claim('deductible', utterance=utter('$1,000'), as_of='2026-01-01', content='$1,000', subject_plan_id=P.id)
    Xc = mint(db.Expense, 'The concurrent visit.')
    claim('occurred_on', utterance=utter('2026-03-05'), as_of='2026-03-05', subject_expense_id=Xc.id)
    role(db.INSURER_OF, aetna, Xc)
    role(db.INSURER_OF, cigna, Xc)
    for P in (P_A, P_B):
        claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('on both'), subject_expense_id=Xc.id, object_plan_id=P.id)
    e5a, _ = stance(db.APPLIED_TO_DEDUCTIBLE, Xc, '$400', '2026-03-20', origin=aetna)
    e5c, _ = stance(db.APPLIED_TO_DEDUCTIBLE, Xc, '$150', '2026-03-25', origin=cigna)
    aA = db.accumulator(s, P_A, '2026-03-31', ACC, KNOWING)
    aB = db.accumulator(s, P_B, '2026-03-31', ACC, KNOWING)
    check('Xs5 (CC1 / Ju11): Aetna applied $400 and Cigna $150 on one X - BOTH KNOWING at the kind level (each holds insurer_of X); 7J: A derives from Aetna\'s stance only (400), B from Cigna\'s only (150) - the plan gate is the consumer\'s; the kind has no P',
          st(e5a) == db.STRENGTH_KNOWING and st(e5c) == db.STRENGTH_KNOWING and aA['derived']['value'] == D('400') and aB['derived']['value'] == D('150')
          and 'object_plan_id' not in db.RULED_KINDS[db.APPLIED_TO_DEDUCTIBLE]['object'])
    # Xs5': the sentence of the ruling made executable - the kind cannot acquire P because a consumer has P
    role(db.INSURER_OF, cigna, X6 := mint(db.Expense, 'The preventive visit.'))
    e5x, _ = stance(db.APPLIED_TO_DEDUCTIBLE, X6, '$75', '2026-02-12', origin=cigna)
    claim('occurred_on', utterance=utter('2026-02-01'), as_of='2026-02-01', subject_expense_id=X6.id)
    role(db.INSURER_OF, aetna, X6)
    claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('on A'), subject_expense_id=X6.id, object_plan_id=P_A.id)
    check('Xs5\' (the kind has no P): Cigna holds insurer_of X6 but insures no plan X6 is in respect of (X6 is on A, Aetna\'s) -> Cigna\'s applied stance is KNOWING at the kind level; 7J for A does not read it (Cigna is not A\'s insurer) - the plan selection is the consumer\'s, never the kind\'s',
          st(e5x) == db.STRENGTH_KNOWING)
    e6, _ = stance(db.APPLIED_TO_DEDUCTIBLE, X6, 'none', '2026-02-10', origin=aetna)
    a6 = db.accumulator(s, P_A, '2026-03-31', ACC, KNOWING)
    check('Xs6 (C6): Aetna applied "none" (exempt) -> KNOWING; content opaque to the kind; 7J reads exempt - listed, not zero, not unknown; the family figure still 400; Cigna\'s $75 (Xs5\') nowhere in A\'s basis',
          st(e6) == db.STRENGTH_KNOWING and X6.id in [x for x, _ in a6['derived']['exempt']] and a6['derived']['value'] == D('400')
          and all(v != D('75') for _, v, _ in a6['derived']['basis']))

    print('\n4. Xs7 / Xs8 - the denial and the adjudication: two kinds by name, no verdict field\n')
    X7 = mint(db.Expense, 'The visit Aetna denied.')
    role(db.INSURER_OF, aetna, X7)
    role(db.PROVIDER_OF, mercy, X7)
    stance(db.BILLED, X7, '$600', '2026-01-20', origin=mercy)
    e7, p7 = stance(db.DENIAL, X7, 'not a covered service', '2026-02-01', origin=aetna)
    r7 = rec(X7, '2026-02-28')
    check('Xs7 (C7 / Rc6): Aetna\'s "not a covered service" is a DENIAL - its own kind, KNOWING for Aetna; NOT a determination (none current; not unpaid, not pending_claim); 7H reads no denial and says so in its note; nothing parses the content',
          st(e7) == db.STRENGTH_KNOWING and r7['determinations']['current'] is None
          and any('denial' in n for n in r7['note']) and p7.kind == db.DENIAL and p7.content == 'not a covered service')
    e8, p8 = stance(db.ADJUDICATION, X7, 'reversed', '2026-03-01', origin=aetna)
    e8m, _ = stance(db.ADJUDICATION, X7, 'reversed', '2026-03-01', origin=mercy)
    check('Xs8 (E3): Aetna\'s "reversed" is an ADJUDICATION - the insurer\'s adjudicative stance with content opaque, KNOWING for Aetna and NOT_KNOWING for Mercy; no consumer reads it; it is not a denial by kind',
          st(e8) == db.STRENGTH_KNOWING and st(e8m) == db.STRENGTH_NOT_KNOWING and p8.kind != db.DENIAL)

    print('\n5. Xs11 / Xs12 / Xs13 / Xs14 - contested, undated, the borrowed line, knowing needs the role in the record\n')
    X11 = mint(db.Expense, 'A visit whose insurer is disputed.')
    role(db.INSURER_OF, aetna, X11)
    claim(db.INSURER_OF, utterance=utter('No - Cigna was the insurer for that one.', origin=cigna), as_of='2026-01-01', subject_party_id=cigna.id, object_expense_id=X11.id)
    claim(db.UTTERANCE_RETRACTION, utterance=utter('I retract the Aetna claim... no, I don\'t.'), subject_utterance_id=s.query(db.Utterance).filter_by(content=f'{db.INSURER_OF} 2026-01-01').order_by(db.Utterance.id.desc()).first().id)
    ans11 = db.in_effect(s, aetna, db.INSURER_OF, '2026-02-01')['identities'][X11.id]['answer']
    e11, _ = stance(db.PATIENT_RESPONSIBILITY, X11, '$100', '2026-02-01', origin=aetna)
    check('Xs11 (Dg21\'s analogue): Aetna\'s insurer_of holds claim on X11 is retracted (contested) at the stance\'s date - 7F answers UNDETERMINED (no established stance stands) -> the relation answers UNDETERMINED, neither knowing nor not_knowing manufactured; 7H reports the role answer and lets nothing govern',
          ans11 == db.EFFECT_UNDETERMINED and st(e11) == db.STRENGTH_UNDETERMINED
          and rec(X11, '2026-02-28')['stances']['patient_responsibility']['governing'] is None)
    e12, p12 = stance(db.PATIENT_RESPONSIBILITY, X, '$1', None, origin=aetna)
    check('Xs12 (F7): an undated PR stance by the insurer -> UNDETERMINED (no date to place the role against); 7H disqualifies it',
          st(e12) == db.STRENGTH_UNDETERMINED and [c['qualifies'] for c in rec(X, '2026-03-31')['stances']['patient_responsibility']['claims'] if c['claim'] == p12.id] == [False])
    check('Xs13 (F2-i): an EOB line figure whose subject is the INSURER and whose thing is a candidate is REFUSED under the ruled name; it keeps its shape under the eob_amount stand-in (7E\'s; expense-identity, plan-identity, C renamed theirs)',
          _refused(s, db.Proposition(kind=db.PATIENT_RESPONSIBILITY, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                     subject_party_id=aetna.id, content='$412 | claim #A77', as_of='2026-03-10'))
          and not _refused(s, db.Proposition(kind='eob_amount', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                             subject_party_id=aetna.id, content='$412 | claim #A77', as_of='2026-03-10'))
          and 'eob_amount' not in db.RULED_KINDS)
    X14 = mint(db.Expense, 'A visit with no role in the record.')
    humana = mint(db.Party, 'Humana - an institution, no role on X14.')
    e14, _ = stance(db.PATIENT_RESPONSIBILITY, X14, '$50', '2026-03-01', origin=humana)
    before = st(e14)
    role(db.INSURER_OF, humana, X14)
    check('Xs14 (F2-ii): Humana - an institution - states PR on X14 with NO insurer_of claim in the record -> NOT_KNOWING (a type is not a role); once the role claim is in the record -> KNOWING; the role is added to the record, never inferred from the stance, the origin or the type',
          before == db.STRENGTH_NOT_KNOWING and st(e14) == db.STRENGTH_KNOWING)

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
