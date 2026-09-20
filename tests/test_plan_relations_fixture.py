"""The three plan relations - the executable trace of `gw 2.0/RELATION_SEMANTICS.md` pass E (accepted s E.10, 2026-09-15),
built by `gw 2.0/CATALOGUES.md` pass 9C (authorised s 9C.7, 2026-09-19): `expense_in_respect_of_plan`,
`obligation_in_respect_of_plan`, `payment_in_respect_of_plan` - each meaning exactly that the asserting party holds the
subject is in respect of the object plan, nothing about coverage; one fixture over E1-E24 as s E.8 specified, plus 9C's
cases c1-c5 - the consumer paths on the ruled kinds, evidence that the swap changed the identity of the relation and
nothing else.

What this slice can and cannot exercise
---------------------------------------
    the registry: three kinds, one per pair, family flags, no knowing relation / role / boundary (G.9)        EXERCISED
    E1  the floor - X in respect of P, two established participants                                            EXERCISED
    E2  two plans one date - two claims, nothing names a result, no priority                       MANDATORY   EXERCISED
    E3  the insurer's retroactive ending is a stance about P; the relation stands                              EXERCISED
    E4  coordination - two plans, two claims, no netting                                                        EXERCISED
    E5  cash at CVS - no relation; no "uninsured" from absence                                                  EXERCISED
    E6  the EOB concerns X and P - nothing derived from a document concerning both                             EXERCISED
    E7  the authorization tied by proposition_concerns; X -> P Rob's to assert                                  EXERCISED
    E8  denied, unpaid, cash-paid - the minimal-floor invariant                                    MANDATORY   EXERCISED
    E9  dispute; retraction; nothing chooses                                                                    EXERCISED
    E10 direction by type; a plan-subject claim refused; no inverse; no resolver                                EXERCISED
    E11 the floor stated                                                                                        EXERCISED
    E12 / E13 / E14 the premium O -> P; the employer's share not summed; O' the same kind (money direction)    EXERCISED
    E15 "what the plan didn't cover" - X -> P + O -> X does not yield O -> P                                    EXERCISED
    E16 COBRA - a plan is not an obligation; obligation_replaces does not apply                                  EXERCISED
    E17 the deduction with no obligation - p -> P, nothing manufactured                                          EXERCISED
    E18 p -> O + O -> P does not yield p -> P                                                                    EXERCISED
    E19 Aetna's payment to Mercy - p' -> P by Rob; no household party required                                  EXERCISED
    E20 reimbursement - no discharge                                                                            EXERCISED
    E21 the bank line - a candidate at most                                                                     EXERCISED
    E22 timing - no temporal precedence                                                           PERMANENT    EXERCISED
    E23 the vocabulary - none a kind                                                                            EXERCISED
    E24 shared person != plan attribution - no relation and no candidate                          MANDATORY   EXERCISED
    c1  E24 through 7F reach on the ruled kind - empty, not refused (9C-F1)                                     EXERCISED
    c2  E8 through 7J - unadjudicated, not excluded, not zero (9C-F2)                                           EXERCISED
    c3  E2 / E4 through 7J - each plan from its own insurer's stance; no priority, split or sum                  EXERCISED
    c4  E5 through 7J - not in P's set; no "uninsured" anywhere in the report                                    EXERCISED
    c5  F14 from 9A - no membership derived from the ruled kind                                                  EXERCISED
    who is knowing for a plan relation; candidate generation; the stance / value kinds (9D)                     NOT BUILT

Run:  python tests/test_plan_relations_fixture.py
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


ABSENT_KINDS = ('plan_covers_expense', 'plan_covers_obligation', 'plan_covers_payment', 'plan_covers', 'covered_by', 'covered_under',
                'expense_plan', 'adjudicated_under', 'premium_for', 'obligation_for_plan', 'plan_obligation', 'pays_for', 'in_respect_of_plan',
                'in_respect_of', 'plan_relation', 'expense_claimed_under', 'payment_premium_for', 'payment_benefit_under', 'benefit_under',
                'under', 'on', 'through', 'premium', 'benefit', 'claim', 'in_network')
ABSENT_HELPERS = ('plan_of_expense', 'plan_covering', 'which_plan', 'coverage_of', 'plan_for_expense', 'plans_of', 'primary_plan',
                  'derive_plan', 'infer_plan', 'plan_from_membership', 'uninsured', 'is_uninsured', 'is_covered', 'covered',
                  'resolve_in_respect_of', 'compose', 'inverse_of')
# the 7J catalogue as the accumulator fixture names it - the value / stance kinds are 9D's, read here by name only
CATALOGUE = {'occurred_on': 'occurred_on', 'insurer_of': 'insurer_of', 'under_plan': 'under_plan', 'plan_insurer': 'insurer_of_plan',
             'eligibility': 'eligibility', 'deductible': 'deductible', 'individual_deductible': 'individual_deductible', 'plan_year': 'plan_year',
             'deductible_applied': 'deductible_applied', 'individual_deductible_applied': 'individual_deductible_applied', 'expense_in_respect_of_plan': 'expense_in_respect_of_plan',
             'applied_to_deductible': 'applied_to_deductible', 'incurred_by': 'incurred_by'}


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_pr_')
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


def _walk(o, path=()):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, path + (k,))
            yield (path + (k,), k)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from _walk(v, path)
    else:
        yield (path, o)


def run(db):
    s = _fresh()
    rob = db.Person(display_name='Rob')
    kim = db.Person(display_name='Kim')
    s.add_all([rob, kim])
    s.commit()
    household, kim_party = rob.party, kim.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}}

    def utter(text, when='2026-04-02T09:00:00', origin=None):
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
        return evidence(pr, utterance=utterance if (utterance or reading) else utter(f'{kind}'), reading=reading), pr

    def st(rel):
        return db.derived_strength(s, rel, KNOWING)

    def held(h, origin_party):
        a = db.Artefact(held=True, content_hash=h, as_of='2026-04-01')
        s.add(a)
        s.commit()
        pr = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=a.id, object_party_id=origin_party.id)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utter('origin'))
        r = db.Reading(artefact_id=a.id, reader_process='parser/5', read_at=datetime(2026, 4, 2))
        s.add(r)
        s.commit()
        return a, r

    def retract(u, text):
        r = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                           subject_utterance_id=u.id)
        s.add(r)
        s.commit()
        evidence(r, utterance=utter(text, '2026-05-20T09:00:00'))

    def rel(kind, **f):
        return s.query(db.Proposition).filter_by(kind=kind, **f)

    def plan_claims(P):
        return s.query(db.Proposition).filter_by(object_plan_id=P.id).filter(db.Proposition.kind.in_([db.EXPENSE_IN_RESPECT_OF_PLAN, db.OBLIGATION_IN_RESPECT_OF_PLAN, db.PAYMENT_IN_RESPECT_OF_PLAN]))

    def snapshot():
        return [(r.id, r.kind, r.subject_expense_id, r.subject_obligation_id, r.subject_payment_id, r.object_plan_id, r.as_of, r.content)
                for r in s.query(db.Proposition).order_by(db.Proposition.id).all()]

    aetna = mint(db.Party, 'Aetna.')
    cigna = mint(db.Party, 'Cigna.')
    mercy = mint(db.Party, 'Mercy Hospital.')
    employer = mint(db.Party, "Kim's employer.")
    P = mint(db.Plan, "Kim's Aetna medical plan.")
    P_dental = mint(db.Plan, "Kim's Aetna dental plan.")
    P2 = mint(db.Plan, "Rob's marketplace plan.")
    X = mint(db.Expense, 'The ER visit, 3/1.')

    print('\n1. The registry - three kinds, one per pair, E\'s flags, nothing else (E, G.9)\n')
    three = (db.EXPENSE_IN_RESPECT_OF_PLAN, db.OBLIGATION_IN_RESPECT_OF_PLAN, db.PAYMENT_IN_RESPECT_OF_PLAN)
    check('three plan relation kinds are ruled - expense / obligation / payment subject, the plan the object - each symmetric False, a reading never establishes, relational knowing with NO named relation; not roles (no role key), no boundary',
          all(db.RULED_KINDS[k] == {'subject': (sub,), 'object': ('object_plan_id',), 'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
              for k, sub in zip(three, ('subject_expense_id', 'subject_obligation_id', 'subject_payment_id')))
          and db.registry_violations() == [])
    check('the in-respect-of family has six members, one per ruled pair (G.9); no typed-slot merge, no bare in_respect_of, no seventh pair; no inverse / coverage / premium kind; no resolver, composer or which-plan helper',
          len([k for k in db.RULED_KINDS if 'in_respect_of' in k]) == 6
          and not any(k in db.RULED_KINDS for k in ABSENT_KINDS) and not any(hasattr(db, n) for n in ABSENT_HELPERS))
    check('E10: direction is fixed by type - a plan-subject claim of each kind is refused by the registry; each kind refuses the other two\'s subject types; no plan_id on any anchor',
          all(_refused(s, db.Proposition(kind=k, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_plan_id=P.id, **{o: 1})) for k, o in zip(three, ('object_expense_id', 'object_obligation_id', 'object_payment_id')))
          and _refused(s, db.Proposition(kind=db.EXPENSE_IN_RESPECT_OF_PLAN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_obligation_id=1, object_plan_id=P.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF_PLAN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_expense_id=X.id, object_plan_id=P.id))
          and not any('plan' in c.name for cls in (db.Expense, db.Obligation, db.Payment) for c in cls.__table__.columns))

    print('\n2. E1 / E11 / E2 / E4 / E9 - the floor; two plans, nothing chosen; dispute\n')
    e1, pr1 = claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter("The ER visit was on Kim's Aetna plan."), as_of='2026-03-01', subject_expense_id=X.id, object_plan_id=P.id)
    check('E1 / E11: X in respect of P - two established participants, asserted by Rob; established; knowing undetermined (E: no designated relation); X and P unchanged; nothing about covered / member / terms / paid on either',
          pr1.subject_state == db.PARTICIPANT_ESTABLISHED and pr1.object_state == db.PARTICIPANT_ESTABLISHED and st(e1) == db.STRENGTH_UNDETERMINED
          and s.get(db.Expense, X.id) is not None and s.get(db.Plan, P.id) is not None
          and not any(c.name in ('covered', 'member', 'plan_paid', 'terms', 'status') for c in db.Expense.__table__.columns))
    Xd = mint(db.Expense, 'The dental cleaning, 4/2.')
    claim(db.INCURRED_BY, utterance=utter('Kim.'), subject_party_id=kim_party.id, object_expense_id=Xd.id)
    claim(db.OCCURRED_ON, utterance=utter('4/2'), as_of='2026-04-02', subject_expense_id=Xd.id)
    claim(db.UNDER_PLAN, utterance=utter('Kim is on both Aetna plans.'), as_of='2026-01-01', subject_party_id=kim_party.id, object_plan_id=P.id)
    claim(db.UNDER_PLAN, utterance=utter('Kim is on both Aetna plans.'), as_of='2026-01-01', subject_party_id=kim_party.id, object_plan_id=P_dental.id)
    before2 = plan_claims(P).count() + plan_claims(P_dental).count()
    check('E2 (MANDATORY): medical and dental, both Aetna, a cleaning on 4/2 with Kim under both - the membership-and-date derivation CANNOT NAME ITS RESULT and produces nothing: no claim of the kind exists for Xd until a party asserts one',
          rel(db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=Xd.id).count() == 0 and before2 == 1)
    claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('The cleaning was on the dental plan.'), subject_expense_id=Xd.id, object_plan_id=P_dental.id)
    check('E2: Rob asserts Xd in respect of P_dental - one claim, no rule chose it, no priority key anywhere; P (medical) has no claim for Xd',
          rel(db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=Xd.id).one().object_plan_id == P_dental.id
          and rel(db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=Xd.id, object_plan_id=P.id).count() == 0)
    Xc = mint(db.Expense, 'One visit, two plans (coordination).')
    claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('It went to Aetna and to Cigna.'), subject_expense_id=Xc.id, object_plan_id=P.id)
    claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('It went to Aetna and to Cigna.'), subject_expense_id=Xc.id, object_plan_id=P2.id)
    r4 = db.reach(s, Xc, db.EXPENSE_IN_RESPECT_OF_PLAN)
    check('E4: one visit in respect of two plans - two claims, both reached, no cardinality, no priority / primary / secondary key; the insurers\' adjudications are theirs (item 7)',
          sorted(e['id'] for e in r4['endpoints']) == sorted([P.id, P2.id])
          and not any(k in ('primary', 'secondary', 'priority', 'rank', 'order') for _, k in _walk(r4) if isinstance(k, str)))
    u9 = utter("No - the ER visit was on Rob's marketplace plan.", origin=kim_party)
    claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=u9, subject_expense_id=X.id, object_plan_id=P2.id)
    two9 = db.reach(s, X, db.EXPENSE_IN_RESPECT_OF_PLAN)
    retract(u9, 'I was thinking of a different visit.')
    after9 = db.reach(s, X, db.EXPENSE_IN_RESPECT_OF_PLAN)
    check('E9: Rob says P, Kim says P2 - two claims stand side by side, nothing chooses; Kim retracts -> her claim is contested by its own retraction, Rob\'s stands; X, P, P2 untouched',
          sorted(e['id'] for e in two9['endpoints']) == sorted([P.id, P2.id])
          and {e['id']: e['state'] for e in after9['endpoints']} == {P.id: db.CLAIM_ESTABLISHED, P2.id: db.CLAIM_CONTESTED})

    print('\n3. E3 / E8 / E5 - the floor is weaker than coverage; the lower boundary\n')
    claim(db.COVERAGE_ENDED, utterance=utter('Coverage ended 6/30, retroactively.', '2026-08-15T09:00:00', origin=aetna), as_of='2026-08-15', content='2026-06-30', subject_plan_id=P.id)
    claim(db.ADJUDICATION, utterance=utter('Reversed.', '2026-08-15T09:00:00', origin=aetna), as_of='2026-08-15', content='reversed', subject_expense_id=X.id)
    check('E3 (Pl12): Aetna\'s retroactive ending is a stance about P and the reversal a stance about X; X in respect of P STANDS - the relation is not withdrawn by the insurer\'s later stance; "covered" was never in it',
          rel(db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=X.id, object_plan_id=P.id).count() == 1 and st(e1) == db.STRENGTH_UNDETERMINED
          and db.reach(s, X, db.EXPENSE_IN_RESPECT_OF_PLAN)['endpoints'][0]['state'] == db.CLAIM_ESTABLISHED)
    X8 = mint(db.Expense, 'The MRI Aetna denied.')
    e8, pr8 = claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('We submitted the MRI under the plan.'), subject_expense_id=X8.id, object_plan_id=P.id)
    claim(db.ADJUDICATION, utterance=utter('Not covered.', origin=aetna), as_of='2026-04-10', content='denied - not covered', subject_expense_id=X8.id)
    claim(db.PLAN_PAID, utterance=utter('$0', origin=aetna), as_of='2026-04-10', content='0', subject_expense_id=X8.id)
    p8 = mint(db.Payment, 'Paid Mercy in cash for the MRI.')
    claim(db.PAYMENT_IN_RESPECT_OF, utterance=utter('That cash was for the MRI.'), subject_payment_id=p8.id, object_expense_id=X8.id)
    snap8 = snapshot()
    r8 = db.reach(s, X8, db.EXPENSE_IN_RESPECT_OF_PLAN)
    check('E8 (MANDATORY - the minimal-floor invariant): denied, plan paid $0, cash-paid -> X8 in respect of P REMAINS TRUE and established; the relation is an association with the arrangement, not "covered by"; nothing on X8 or P changed; reading the relation wrote nothing',
          [(e['id'], e['claim'], e['state'], e['asserter']) for e in r8['endpoints']] == [(P.id, pr8.id, db.CLAIM_ESTABLISHED, household.id)]
          and st(e8) == db.STRENGTH_UNDETERMINED and snapshot() == snap8)
    X5 = mint(db.Expense, "Kim's prescription, cash at CVS, never submitted.")
    claim(db.INCURRED_BY, utterance=utter('Kim.'), subject_party_id=kim_party.id, object_expense_id=X5.id)
    r5 = db.reach(s, X5, db.EXPENSE_IN_RESPECT_OF_PLAN)
    check('E5 (Ex8 - the lower boundary): never submitted -> NO relation; the absence derives no "uninsured" / "not covered" / "out of network" - no such kind, key or helper; contrast E8',
          r5['endpoints'] == [] and rel(db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=X5.id).count() == 0
          and not any(k in db.RULED_KINDS for k in ('uninsured', 'not_covered', 'out_of_network')) and not hasattr(db, 'uninsured'))

    print('\n4. E6 / E7 / E21 - documents, authorizations and bank lines: candidates at most, never the claim\n')
    eob, r_eob = held('h-eob', aetna)
    claim(db.ARTEFACT_CONCERNS, utterance=utter('That EOB is about the ER visit.'), subject_artefact_id=eob.id, object_expense_id=X.id)
    claim(db.ARTEFACT_CONCERNS, utterance=utter('And about the plan.'), subject_artefact_id=eob.id, object_plan_id=P.id)
    X6 = mint(db.Expense, 'A second visit the EOB also lists.')
    claim(db.ARTEFACT_CONCERNS, utterance=utter('The EOB lists this one too.'), subject_artefact_id=eob.id, object_expense_id=X6.id)
    check('E6: the EOB concerns X6 and concerns P - two about-ness claims; the relation X6 -> P is NOT derived from a document concerning both; the group number is a correspondence candidate at most',
          rel(db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=X6.id).count() == 0)
    e6r, pr6r = claim(db.EXPENSE_IN_RESPECT_OF_PLAN, reading=r_eob, subject_expense_id=X6.id, object_plan_id=P.id)
    check('E6 / E21: a reading-sourced claim of the kind (the EOB\'s line; a bank label) is a CANDIDATE - strength undetermined, state candidate, never the claim (reading_establishes False on all three)',
          st(e6r) == db.STRENGTH_UNDETERMINED
          and [e['state'] for e in db.reach(s, X6, db.EXPENSE_IN_RESPECT_OF_PLAN)['endpoints']] == [db.CLAIM_CANDIDATE]
          and all(not db.RULED_KINDS[k]['reading_establishes'] for k in three))
    _, auth = claim(db.AUTHORIZATION, utterance=utter('Prior auth for an MRI, 2/10.', '2026-02-10T09:00:00', origin=aetna), as_of='2026-02-10', content='MRI', subject_plan_id=P.id)
    X7 = mint(db.Expense, 'The MRI, 3/1.')
    claim(db.PROPOSITION_CONCERNS, utterance=utter('That authorization was for this MRI.'), subject_proposition_id=auth.id, object_expense_id=X7.id)
    check('E7 (Pl11): the authorization is a stance about P with the MRI as content; a party ties it to X7 by proposition_concerns; X7 -> P is Rob\'s to assert and is NOT derived from the authorization',
          rel(db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=X7.id).count() == 0
          and rel(db.PROPOSITION_CONCERNS, subject_proposition_id=auth.id).count() == 1)

    print('\n5. E12 / E13 / E14 / E15 / E16 - the obligation relation: the premium; money direction; through X; COBRA\n')
    O = mint(db.Obligation, 'We owe $412 a month - the premium.')
    e12, pr12 = claim(db.OBLIGATION_IN_RESPECT_OF_PLAN, utterance=utter('The $412 is the premium for the plan.'), content='premium', subject_obligation_id=O.id, object_plan_id=P.id)
    check('E12 (Pl7): O in respect of P - the premium is a claim on O (content) not a status; P acquires no cost; established, knowing undetermined',
          pr12.content == 'premium' and st(e12) == db.STRENGTH_UNDETERMINED
          and not any(c.name in ('cost', 'premium', 'premium_amount') for c in db.Plan.__table__.columns)
          and not any(c.name in ('premium', 'is_premium') for c in db.Obligation.__table__.columns))
    claim('contribution', utterance=utter('The employer pays 70% of the premium.'), content='70%', subject_party_id=employer.id)
    check('E13 (Pl8): the employer\'s contribution is a claim about the employer party; O is the household\'s share; nothing sums, no total kind or helper',
          rel('contribution', subject_party_id=employer.id).count() == 1 and rel(db.OBLIGATION_IN_RESPECT_OF_PLAN, object_plan_id=P.id).count() == 1
          and not any(hasattr(db, n) for n in ('premium_total', 'total_premium', 'plan_cost')))
    Oprime = mint(db.Obligation, 'Aetna owes us $340 - out of network.')
    claim(db.ENTITLED_PARTY_OF, utterance=utter('We are owed it.'), as_of='2026-04-01', subject_party_id=household.id, object_obligation_id=Oprime.id)
    e14, pr14 = claim(db.OBLIGATION_IN_RESPECT_OF_PLAN, utterance=utter('Under the plan, Aetna owes us $340.'), subject_obligation_id=Oprime.id, object_plan_id=P.id)
    check('E14: O\' (the insurer owes the household) in respect of P is the SAME KIND as E12\'s premium - money direction is not relational meaning; who owes whom is O\'s role claims; O -> P never yields "P covers O" (no such kind); PL3 stays rejected',
          pr14.kind == pr12.kind == db.OBLIGATION_IN_RESPECT_OF_PLAN and st(e14) == db.STRENGTH_UNDETERMINED
          and rel(db.ENTITLED_PARTY_OF, object_obligation_id=Oprime.id).one().subject_party_id == household.id
          and not any(k in db.RULED_KINDS for k in ('plan_covers_obligation', 'plan_owes', 'plan_charges')))
    O15 = mint(db.Obligation, "Mercy's bill - $412 patient responsibility.")
    claim(db.OBLIGATION_IN_RESPECT_OF, utterance=utter("That's Mercy's bill for the ER visit."), subject_obligation_id=O15.id, object_expense_id=X.id)
    check('E15 ("what the plan didn\'t cover"): X -> P (E1) + O15 -> X (C) -> O15 -> P is NOT derived - convergence through X refused; "didn\'t cover" is content or the insurer\'s PR stance; O15 -> P assertable by Rob, derives nothing',
          rel(db.OBLIGATION_IN_RESPECT_OF_PLAN, subject_obligation_id=O15.id).count() == 0
          and db.reach(s, O15, db.OBLIGATION_IN_RESPECT_OF_PLAN)['endpoints'] == [])
    O_cobra = mint(db.Obligation, 'The whole premium now - COBRA.')
    claim(db.OBLIGATION_IN_RESPECT_OF_PLAN, utterance=utter('COBRA - same plan, we pay all of it.'), content='COBRA', subject_obligation_id=O_cobra.id, object_plan_id=P.id)
    check('E16 (Pl13): O_cobra in respect of P (the household\'s arrangement, same P); a plan is not an obligation - obligation_replaces takes obligations only, a plan in its slots is refused; no composition with it',
          rel(db.OBLIGATION_IN_RESPECT_OF_PLAN, subject_obligation_id=O_cobra.id).count() == 1
          and 'subject_plan_id' not in db.RULED_KINDS[db.OBLIGATION_REPLACES]['subject'] and 'object_plan_id' not in db.RULED_KINDS[db.OBLIGATION_REPLACES]['object']
          and rel(db.OBLIGATION_REPLACES, subject_obligation_id=O_cobra.id).count() == 0)

    print('\n6. E17 / E18 / E19 / E20 / E22 - the payment relation: no obligation needed; through O; the insurer\'s payment; no discharge; timing\n')
    p17 = mint(db.Payment, '$412 out of every paycheque.')
    claim(db.PAID_BY, utterance=utter('It comes out of my pay.'), as_of='2026-01-31', subject_party_id=household.id, object_payment_id=p17.id)
    n_obl = s.query(db.Obligation).count()
    e17, pr17 = claim(db.PAYMENT_IN_RESPECT_OF_PLAN, utterance=utter('That deduction is the plan.'), content='deduction', subject_payment_id=p17.id, object_plan_id=P.id)
    check('E17: p17 in respect of P with NO obligation anywhere - the household never individuated "we owe the premium"; no obligation manufactured; no chain needed or available',
          st(e17) == db.STRENGTH_UNDETERMINED and s.query(db.Obligation).count() == n_obl
          and rel(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_payment_id=p17.id).count() == 0)
    p18 = mint(db.Payment, 'The March premium payment.')
    claim(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, utterance=utter('That paid the premium.'), subject_payment_id=p18.id, object_obligation_id=O.id)
    check('E18: p18 -> O (D\') + O -> P (E12) -> p18 -> P is NOT derived - composition through O refused; Rob may assert it',
          rel(db.PAYMENT_IN_RESPECT_OF_PLAN, subject_payment_id=p18.id).count() == 0
          and db.reach(s, p18, db.PAYMENT_IN_RESPECT_OF_PLAN)['endpoints'] == [])
    p19 = mint(db.Payment, 'Aetna paid Mercy $568.')
    claim(db.PAID_BY, utterance=utter('Aetna paid it.'), as_of='2026-04-20', subject_party_id=aetna.id, object_payment_id=p19.id)
    claim(db.PAID_TO, utterance=utter('To Mercy.'), as_of='2026-04-20', subject_party_id=mercy.id, object_payment_id=p19.id)
    claim(db.PAYMENT_IN_RESPECT_OF, utterance=utter('For the ER visit.'), subject_payment_id=p19.id, object_expense_id=X.id)
    claim(db.PLAN_PAID, utterance=utter('Plan paid $568.', origin=aetna), as_of='2026-04-20', content='568', subject_expense_id=X.id)
    check('E19 (D18): p19 -> P is NOT derived from the EOB\'s plan-paid stance nor from X -> P + p19 -> X; and when Rob asserts it, no household party is required on p19 (payer Aetna, payee Mercy)',
          rel(db.PAYMENT_IN_RESPECT_OF_PLAN, subject_payment_id=p19.id).count() == 0
          and (claim(db.PAYMENT_IN_RESPECT_OF_PLAN, utterance=utter('Under the plan.'), subject_payment_id=p19.id, object_plan_id=P.id) is not None)
          and rel(db.PAYMENT_IN_RESPECT_OF_PLAN, subject_payment_id=p19.id).count() == 1
          and rel(db.PAID_BY, object_payment_id=p19.id, subject_party_id=household.id).count() == 0)
    p20 = mint(db.Payment, 'Aetna reimbursed us $340.')
    claim(db.PAID_BY, utterance=utter('Aetna.'), as_of='2026-05-01', subject_party_id=aetna.id, object_payment_id=p20.id)
    claim(db.PAID_TO, utterance=utter('To us.'), as_of='2026-05-01', subject_party_id=household.id, object_payment_id=p20.id)
    claim(db.PAYMENT_IN_RESPECT_OF_PLAN, utterance=utter('The reimbursement under the plan.'), content='reimbursement', subject_payment_id=p20.id, object_plan_id=P.id)
    claim(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, utterance=utter('It settled what Aetna owed us.'), subject_payment_id=p20.id, object_obligation_id=Oprime.id)
    check('E20: the reimbursement in respect of P and in respect of O\' (D\') - no direction of money in either, no discharge of O\' (that is an acknowledgment, 9D\'s kind), no status on O\' or p20',
          rel(db.PAYMENT_IN_RESPECT_OF_PLAN, subject_payment_id=p20.id).count() == 1
          and not any(c.name in ('discharged', 'status', 'paid', 'settled') for cls in (db.Obligation, db.Payment) for c in cls.__table__.columns)
          and not any(hasattr(db, n) for n in ('is_discharged', 'discharge', 'settle')))
    P_jan = mint(db.Plan, 'The plan starting January 1, 2027.')
    p22 = mint(db.Payment, 'The first premium, paid in December 2026.')
    claim(db.OCCURRED_ON, utterance=utter('12/15/2026'), as_of='2026-12-15', subject_payment_id=p22.id)
    e22, _ = claim(db.PAYMENT_IN_RESPECT_OF_PLAN, utterance=utter('December\'s payment was for the January plan.'), as_of='2026-12-15', subject_payment_id=p22.id, object_plan_id=P_jan.id)
    P_late = mint(db.Plan, 'A January arrangement, minted in March.')
    X_late = mint(db.Expense, 'A January visit.')
    e22b, _ = claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('That January visit was on the plan we set up in March.', '2027-03-05T09:00:00'), as_of='2027-01-10', subject_expense_id=X_late.id, object_plan_id=P_late.id)
    check('E22 (PERMANENT): the December premium for the January plan, and a January visit on a plan minted in March - both accepted, as_of permitted; the relation\'s direction and participant types establish NO temporal precedence; no order guard',
          st(e22) == db.STRENGTH_UNDETERMINED and st(e22b) == db.STRENGTH_UNDETERMINED
          and not any(hasattr(db, n) for n in ('temporal_order', 'precedes', 'order_guard', 'must_precede')))

    print('\n7. E23 / E24 / E10 - vocabulary; shared person != plan attribution; no inverse, no resolver\n')
    check('E23: under / on / covered by / through / premium / benefit / claim / in network are content, claims on the subject or the insurer\'s stances - none is a kind; "covered by" refused as a name',
          not any(k in db.RULED_KINDS for k in ('under', 'on', 'covered_by', 'through', 'premium', 'benefit', 'claim', 'in_network', 'covered'))
          and all(db.RULED_KINDS[k]['object'] == ('object_plan_id',) for k in three))
    X24 = mint(db.Expense, "Kim's visit nobody has connected to any plan.")
    claim(db.INCURRED_BY, utterance=utter('It was Kim\'s visit.'), subject_party_id=kim_party.id, object_expense_id=X24.id)
    claim(db.OCCURRED_ON, utterance=utter('3/20'), as_of='2026-03-20', subject_expense_id=X24.id)
    snap24 = snapshot()
    r24 = db.reach(s, X24, db.EXPENSE_IN_RESPECT_OF_PLAN)
    r24p = db.reach(s, P, db.EXPENSE_IN_RESPECT_OF_PLAN, as_object=True)
    check('E24 (MANDATORY): Kim under P (9A\'s ruled kind, in effect on 3/20) + X24 incurred by Kim (9B\'s) + no evidence connecting X24 to P -> NO relation and NO candidate: no proposition of the kind for X24 in any state; convergence through Kim refused; reading wrote nothing',
          r24['endpoints'] == [] and X24.id not in [e['id'] for e in r24p['endpoints']]
          and rel(db.EXPENSE_IN_RESPECT_OF_PLAN, subject_expense_id=X24.id).count() == 0
          and db.in_effect(s, kim_party, db.UNDER_PLAN, '2026-03-20')['identities'][P.id]['answer'] == db.EFFECT_IN
          and snapshot() == snap24)
    check('E10: no inverse kind (plan_covers_* refused as the magnet\'s name); navigation from the plan is a query - reach(P, kind, as_object=True) lists what parties asserted, in every state; no resolver chooses "the" plan for X (E4\'s two both listed)',
          not any(k in db.RULED_KINDS for k in ('plan_covers_expense', 'plan_covers', 'plan_in_respect_of_expense'))
          and r24p['direction'] == db.DIRECTION_OBJECT and X.id in [e['id'] for e in r24p['endpoints']] and Xc.id in [e['id'] for e in r24p['endpoints']]
          and not any(hasattr(db, n) for n in ('the_plan_of', 'which_plan', 'plan_of_expense', 'primary_plan')))

    print('\n8. c1-c5 - the consumer paths on the ruled kinds (9C.4): the swap changed the identity of the relation and nothing else\n')
    check('c1 (Tr8 / 9C-F1): E24 through 7F on the RULED kind - reach answers empty, is not refused; an unruled name is still refused by name; reach unchanged',
          r24['kind'] == db.EXPENSE_IN_RESPECT_OF_PLAN and r24['endpoints'] == [] and r24['direction'] == db.DIRECTION_SUBJECT)
    try:
        db.reach(s, X24, 'expense_in_respect_of_plan_standin')
        unruled = False
    except ValueError as e:
        unruled = 'not ruled' in str(e)
    check('c1: the stand-in\'s name is not ruled and reach refuses it by name, as it refused E\'s name before 9C', unruled)
    # 7J needs the plan's insurer role, a plan year, a deductible term and an occurred_on on each expense
    claim(db.INSURER_OF_PLAN, utterance=utter('Aetna insures P.'), as_of='2026-01-01', subject_party_id=aetna.id, object_plan_id=P.id)
    claim(db.PLAN_YEAR, utterance=utter('2026'), as_of='2026-01-01', content='2026-12-31', subject_plan_id=P.id)
    claim(db.DEDUCTIBLE, utterance=utter('$1,000', origin=aetna), as_of='2026-01-01', content='$1,000', subject_plan_id=P.id)
    for x, on in ((X, '2026-03-01'), (X8, '2026-03-15'), (Xc, '2026-03-10'), (X6, '2026-03-12'), (X_late, '2027-01-10')):
        claim(db.OCCURRED_ON, utterance=utter(on), as_of=on, subject_expense_id=x.id)
    claim(db.APPLIED_TO_DEDUCTIBLE, utterance=utter('$300 applied', origin=aetna), as_of='2026-03-20', content='$300', subject_expense_id=X.id)
    snap_c = snapshot()
    a = db.accumulator(s, P, '2026-04-30', CATALOGUE, KNOWING)
    # 7J's ruling (absence is not zero): an asserted expense with no adjudication by the plan's insurer leaves the derived
    # VALUE undetermined and names the expense - it is never dropped from the set and never counted as zero.
    check('c2 (E8 through 7J / 9C-F2): X8 - denied, $0, cash-paid, in respect of P - is LISTED as unadjudicated and NAMED in the reason; the derived value is undetermined (not a partial sum, not zero); X8 is not excluded (the relation stands) and not counted (no stance); X (Aetna applied $300) is in the basis; the relation selects, the insurer\'s stance carries the amount; reading wrote nothing',
          X8.id in a['derived']['unadjudicated'] and a['derived']['value'] is None and f'expense {X8.id}' in (a['derived']['reason'] or '')
          and (X.id, D('300')) in [(b[0], b[1]) for b in a['derived']['basis']]
          and snapshot() == snap_c)
    claim(db.INSURER_OF_PLAN, utterance=utter('Cigna insures P2.'), as_of='2026-01-01', subject_party_id=cigna.id, object_plan_id=P2.id)
    claim(db.PLAN_YEAR, utterance=utter('2026'), as_of='2026-01-01', content='2026-12-31', subject_plan_id=P2.id)
    claim(db.DEDUCTIBLE, utterance=utter('$500', origin=cigna), as_of='2026-01-01', content='$500', subject_plan_id=P2.id)
    claim(db.APPLIED_TO_DEDUCTIBLE, utterance=utter('$400 applied', origin=aetna), as_of='2026-03-25', content='$400', subject_expense_id=Xc.id)
    claim(db.APPLIED_TO_DEDUCTIBLE, utterance=utter('$150 applied', origin=cigna), as_of='2026-03-26', content='$150', subject_expense_id=Xc.id)
    aP, aP2 = db.accumulator(s, P, '2026-04-30', CATALOGUE, KNOWING), db.accumulator(s, P2, '2026-04-30', CATALOGUE, KNOWING)
    check('c3 (E2 / E4 / Ju11 through 7J): Xc in respect of P and P2 - P\'s basis carries Aetna\'s stances only (X 300, Xc 400; Cigna\'s 150 on Xc is not P\'s), P2 derives 150 from Cigna\'s only; no priority, no split, no sum across plans',
          [(b[0], b[1]) for b in aP['derived']['basis']] == [(X.id, D('300')), (Xc.id, D('400'))] and aP2['derived']['value'] == D('150')
          and [(b[0], b[1]) for b in aP2['derived']['basis']] == [(Xc.id, D('150'))]
          and not any(k in ('primary', 'secondary', 'split', 'share', 'apportioned', 'total_across_plans') for _, k in _walk(aP) if isinstance(k, str)))
    check('c4 (E5 through 7J): the cash prescription is not in P\'s set and nowhere in the report; no "uninsured" / "not covered" key or value anywhere',
          X5.id not in [b[0] for b in a['derived']['basis']] and X5.id not in a['derived']['unadjudicated']
          and not any(isinstance(v, str) and ('uninsured' in v.lower() or 'not covered' in v.lower()) for _, v in _walk(a))
          and not any(k in ('uninsured', 'not_covered', 'covered') for _, k in _walk(a) if isinstance(k, str)))
    stranger = mint(db.Party, 'Somebody nobody has said is under any plan.')
    Y = mint(db.Expense, 'A visit somebody said was on P2.')
    claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('That visit was on P2.'), subject_expense_id=Y.id, object_plan_id=P2.id)
    claim(db.INCURRED_BY, utterance=utter('Incurred by the stranger.'), subject_party_id=stranger.id, object_expense_id=Y.id)
    check('c5 (F14 from 9A, on the ruled kind): Y in respect of P2, incurred by a party nobody said is under P2 -> NO membership derived - no under_plan claim for the stranger exists or is manufactured',
          rel(db.UNDER_PLAN, subject_party_id=stranger.id).count() == 0 and rel(db.UNDER_PLAN_BEGAN, subject_party_id=stranger.id).count() == 0
          and db.in_effect(s, stranger, db.UNDER_PLAN, '2026-04-30')['identities'] == {})

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
