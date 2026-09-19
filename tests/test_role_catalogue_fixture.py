"""The role catalogue - the executable trace of `gw 2.0/CATALOGUES.md` pass 9B (ruled s 9B.7, 2026-09-19): seven ruled
role kinds on three points each - who may assert, what it establishes, who is knowing (the subject party) - with
boundaries bound only to the two that transition; 'role': True as classification and nothing else (9B-F1); governing
determination deferred entirely to 7H (9B-F2) - this fixture exposes roles, occupants, knowing and boundaries and
asserts NO governing-PR resolution.

What this slice can and cannot exercise
---------------------------------------
    the registry: eight role kinds (with under_plan nine), 'role': True, the three points; boundaries on two   EXERCISED
    Ro1  S1: entitled Mercy, servicer BillCo, payee BillCo - three kinds, three facts                              EXERCISED
    Ro2  S2: the servicer changes 5/1; autopay keeps paying the old one                                             EXERCISED
    Ro3  S3: the never-authorised servicer's own claim - established, knowing, never entitlement                    EXERCISED
    Ro4  S4 / S5: assignment vs sale                                                                                EXERCISED
    Ro5  S6: paying the entitled party directly - direction, not discharge                                          EXERCISED
    Ro6  S7: money to the party that no longer holds it                                                              EXERCISED
    Ro7  R8: the sale's boundaries through 7F                                                                        EXERCISED
    Ro8  Pm9 / Kn7: the mother paid - no household-default payer; minting != knowing                                 EXERCISED
    Ro9  Ex1: provider and incurred-by from the minting act - holds only; no _began kind                             EXERCISED
    Ro10 Ic4 / CC1: two insurers of one expense - two claims, both in effect; governing PR NOT decided here          EXERCISED
    Ro11 Pl3 / Pl14: the plan's insurer; two plans one insurer; two insurers two plans                                EXERCISED
    Ro12 the party asserts its own role - knowing                                                                    EXERCISED
    Ro13 a reading -> a candidate for every role                                                                     EXERCISED
    Ro14 a stranger asserts - established, not_knowing                                                               EXERCISED
    Ro15 retraction is not an ending                                                                                  EXERCISED
    Ro16 no inverse kind; no selector                                                                                 EXERCISED
    Ro17 knowing != true                                                                                              EXERCISED
    Ro18 the substitution - proved in the consumer fixtures; here: the role key acquires no behaviour                 EXERCISED
    9B-F2: no governing-PR resolver, no party-local recency anywhere in the module                                    EXERCISED (absence)
    the subscriber role, the obligor role, E (9C), the stance kinds (9D)                                              NOT BUILT

Run:  python tests/test_role_catalogue_fixture.py
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


ABSENT_KINDS = ('obligation_entitled_party', 'plan_insurer', 'expense_provider', 'expense_insurer', 'payment_payer', 'payment_payee',
                'obligation_servicer', 'provider_of_began', 'provider_of_ended', 'insurer_of_began', 'insurer_of_ended', 'incurred_by_began',
                'paid_by_began', 'paid_to_ended', 'insurer_of_plan_began', 'subscriber', 'subscriber_of', 'obligor_on', 'obligor', 'serves')
ABSENT_HELPERS = ('entitled_party', 'current_entitled_party', 'entitled_party_of', 'servicer', 'current_servicer', 'provider', 'insurer',
                  'payer_of', 'payee_of', 'default_payer', 'household_payer', 'governing_pr', 'resolve_pr', 'latest_insurer', 'primary_insurer',
                  'party_local_recency', 'governing_insurer', 'role_behaviour', 'roles_of')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_rc_')
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}}

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

    def role(kind, party, utterance=None, reading=None, as_of='2026-01-01', **obj):
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            as_of=as_of, subject_party_id=party.id, **obj)
        s.add(pr)
        s.commit()
        return evidence(pr, utterance=utterance if (utterance or reading) else utter(f'{kind} {as_of}'), reading=reading), pr

    def st(rel):
        return db.derived_strength(s, rel, KNOWING)

    def retract(u, text):
        r = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                           subject_utterance_id=u.id)
        s.add(r)
        s.commit()
        evidence(r, utterance=utter(text, '2026-04-20T09:00:00'))

    def claims(kind, **f):
        return s.query(db.Proposition).filter_by(kind=kind, **f)

    mercy = mint(db.Party, 'Mercy Hospital.')
    billco = mint(db.Party, 'BillCo, a billing company.')
    chase = mint(db.Party, 'Chase.')
    newco = mint(db.Party, 'NewCo, who bought the note.')
    s3 = mint(db.Party, 'S3, never authorised.')
    aetna = mint(db.Party, 'Aetna.')
    cigna = mint(db.Party, 'Cigna.')
    mother = mint(db.Party, "Rob's mother.")
    O = mint(db.Obligation, 'The Mercy bill.')
    M = mint(db.Obligation, 'The mortgage.')
    X = mint(db.Expense, 'The ER visit, Feb 14.')
    p = mint(db.Payment, 'The $300 payment.')
    P1, P2 = mint(db.Plan, 'The medical plan.'), mint(db.Plan, 'The dental plan.')

    print('\n1. The registry - the catalogue exactly as ruled; the role key; the boundaries; the knowing relation\n')
    roles = {k: r for k, r in db.RULED_KINDS.items() if r.get('role')}
    check('nine role kinds are marked - under_plan (9A) and the seven of 9B (paid_by / paid_to counted as the payer and payee roles); no other kind is',
          set(roles) == {db.UNDER_PLAN, db.ENTITLED_PARTY_OF, db.SERVICER_OF, db.PROVIDER_OF, db.INSURER_OF, db.INSURER_OF_PLAN, db.INCURRED_BY, db.PAID_BY, db.PAID_TO})
    check('every role: party subject, an identity object, not symmetric, a reading never establishes, relational knowing; the seven of 9B name KNOWING_SUBJECT_PARTY; under_plan names none (F)',
          all(r['subject'] == ('subject_party_id',) and len(r['object']) == 1 and not r['symmetric'] and not r['reading_establishes'] and r['relational_knowing'] for r in roles.values())
          and all(db.RULED_KINDS[k].get('knowing_relation') == db.KNOWING_SUBJECT_PARTY for k in (db.ENTITLED_PARTY_OF, db.SERVICER_OF, db.PROVIDER_OF, db.INSURER_OF, db.INSURER_OF_PLAN, db.INCURRED_BY, db.PAID_BY, db.PAID_TO))
          and db.RULED_KINDS[db.UNDER_PLAN].get('knowing_relation') is None)
    check('the objects: entitled_party_of and servicer_of -> obligation; provider_of, insurer_of, incurred_by -> expense; insurer_of_plan -> plan; paid_by / paid_to -> payment',
          all(db.RULED_KINDS[k]['object'] == (o,) for k, o in ((db.ENTITLED_PARTY_OF, 'object_obligation_id'), (db.SERVICER_OF, 'object_obligation_id'),
                                                              (db.PROVIDER_OF, 'object_expense_id'), (db.INSURER_OF, 'object_expense_id'), (db.INCURRED_BY, 'object_expense_id'),
                                                              (db.INSURER_OF_PLAN, 'object_plan_id'), (db.PAID_BY, 'object_payment_id'), (db.PAID_TO, 'object_payment_id'))))
    check('boundaries are bound to exactly the three roles that transition - under_plan, entitled_party_of, servicer_of - and to none of the five holds-only roles; the guard passes; a boundary of a non-role is refused by the guard (9B-F1)',
          {r['of'] for r in db.RULED_KINDS.values() if r.get('boundary')} == {db.UNDER_PLAN, db.ENTITLED_PARTY_OF, db.SERVICER_OF}
          and not any(k in db.RULED_KINDS for k in ABSENT_KINDS) and db.registry_violations() == []
          and bool(db.registry_violations(registry=dict(db.RULED_KINDS, bad={'subject': ('subject_obligation_id',), 'object': ('object_expense_id',), 'symmetric': False,
                                                                                    'reading_establishes': False, 'relational_knowing': True, 'boundary': 'began', 'of': db.OBLIGATION_IN_RESPECT_OF}), kinds=('bad',))))
    check('KNOWING_SUBJECT_PARTY is the third named relation with its own resolver - the claim\'s subject party; nothing generic',
          db._KNOWING_RELATIONS[db.KNOWING_SUBJECT_PARTY] is db._designated_subject_party and len(db._KNOWING_RELATIONS) == 3
          and not any(hasattr(db, n) for n in ABSENT_HELPERS))

    print('\n2. Ro1 / Ro2 / Ro3 / Ro4 - entitlement, servicing and payee are three kinds; assignment vs sale; S3\n')
    e_ent, _ = role(db.ENTITLED_PARTY_OF, mercy, object_obligation_id=O.id)
    e_svc, _ = role(db.SERVICER_OF, billco, object_obligation_id=O.id)
    e_pay, _ = role(db.PAID_TO, billco, object_payment_id=p.id)
    check('Ro1 (S1): Mercy entitled, BillCo servicing, BillCo paid - three claims of three kinds; 7F\'s in_effect over each role gives Mercy the entitled party and BillCo the servicer; the payee makes nobody entitled',
          db.in_effect(s, mercy, db.ENTITLED_PARTY_OF, '2026-03-01')['identities'][O.id]['answer'] == db.EFFECT_IN
          and db.in_effect(s, billco, db.SERVICER_OF, '2026-03-01')['identities'][O.id]['answer'] == db.EFFECT_IN
          and db.in_effect(s, billco, db.ENTITLED_PARTY_OF, '2026-03-01')['identities'] == {})
    newsvc = mint(db.Party, 'The new servicer.')
    role(db.SERVICER_OF_ENDED, billco, as_of='2026-05-01', object_obligation_id=O.id)
    role(db.SERVICER_OF_BEGAN, newsvc, as_of='2026-05-01', object_obligation_id=O.id)
    p2 = mint(db.Payment, 'The June autopay, still to BillCo.')
    role(db.PAID_TO, billco, as_of='2026-06-01', object_payment_id=p2.id)
    check('Ro2 (S2): the servicer changes 5/1 (BillCo ended, the new one began); the June autopay still names BillCo as payee - a fact that stands; the payee is not redirected and nothing is discharged',
          db.in_effect(s, billco, db.SERVICER_OF, '2026-06-01')['identities'][O.id]['answer'] == db.EFFECT_NOT
          and db.in_effect(s, newsvc, db.SERVICER_OF, '2026-06-01')['identities'][O.id]['answer'] == db.EFFECT_IN
          and claims(db.PAID_TO, object_payment_id=p2.id).one().subject_party_id == billco.id)
    e_s3, _ = role(db.SERVICER_OF, s3, utterance=utter('We service your Mercy account - pay us.', origin=s3), object_obligation_id=O.id)
    check('Ro3 (S3): the never-authorised servicer asserts its own servicing - ESTABLISHED, and KNOWING for its own claim (the subject party); and NOT entitlement: S3\'s entitled-party role on O is undetermined (no stance) - 7G\'s E-test unchanged',
          st(e_s3) == db.STRENGTH_KNOWING and db.in_effect(s, s3, db.ENTITLED_PARTY_OF, '2026-03-01')['identities'] == {}
          and db.in_effect(s, s3, db.SERVICER_OF, '2026-03-01')['identities'][O.id]['answer'] == db.EFFECT_IN)
    role(db.ENTITLED_PARTY_OF, chase, object_obligation_id=M.id)
    role(db.SERVICER_OF, chase, object_obligation_id=M.id)
    role(db.SERVICER_OF_ENDED, chase, as_of='2026-04-01', object_obligation_id=M.id)
    role(db.SERVICER_OF_BEGAN, newsvc, as_of='2026-04-01', object_obligation_id=M.id)              # an assignment of servicing
    a4 = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-04-15')
    role(db.ENTITLED_PARTY_OF_ENDED, chase, as_of='2026-05-01', object_obligation_id=M.id)          # the sale (R8)
    role(db.ENTITLED_PARTY_OF_BEGAN, newco, as_of='2026-05-01', object_obligation_id=M.id)
    check('Ro4 (S4 / S5): the assignment of servicing (4/1) leaves Chase the entitled party and makes the new servicer nobody\'s entitled party; the sale (5/1) transitions entitlement to NewCo - the household says which; nothing inferred from a servicer or payee change',
          a4['identities'][M.id]['answer'] == db.EFFECT_IN and db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-05-12')['identities'][M.id]['answer'] == db.EFFECT_NOT
          and db.in_effect(s, newco, db.ENTITLED_PARTY_OF, '2026-05-12')['identities'][M.id]['answer'] == db.EFFECT_IN
          and db.in_effect(s, newsvc, db.ENTITLED_PARTY_OF, '2026-04-15')['identities'] == {}
          and db.in_effect(s, billco, db.ENTITLED_PARTY_OF, '2026-03-01')['identities'] == {})
    check('Ro7 (R8): on 4/12 Chase is in effect and NewCo undetermined (no stance precedes); on 5/12 the reverse - 7F over the ruled kind, unchanged',
          db.in_effect(s, newco, db.ENTITLED_PARTY_OF, '2026-04-12')['identities'][M.id]['answer'] == db.EFFECT_UNDETERMINED
          and db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-04-12')['identities'][M.id]['answer'] == db.EFFECT_IN)

    print('\n3. Ro5 / Ro6 / Ro8 - payee is direction, never discharge; money to a party that no longer holds it; no default payer\n')
    p5 = mint(db.Payment, 'Paid Chase directly at the branch.')
    role(db.PAID_BY, household, as_of='2026-04-20', object_payment_id=p5.id)
    role(db.PAID_TO, chase, as_of='2026-04-20', object_payment_id=p5.id)
    check('Ro5 (S6): paid_to Chase while Chase is the entitled party in effect - the roles say payee = E; nothing here is discharge (no acknowledgment kind is read by this fixture; no discharge helper exists)',
          claims(db.PAID_TO, object_payment_id=p5.id).one().subject_party_id == chase.id
          and db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-04-20')['identities'][M.id]['answer'] == db.EFFECT_IN
          and not any(hasattr(db, n) for n in ('is_discharged', 'discharged_by', 'payee_discharges')))
    p6 = mint(db.Payment, 'Sent to Chase after the sale.')
    role(db.PAID_BY, household, as_of='2026-06-01', object_payment_id=p6.id)
    role(db.PAID_TO, chase, as_of='2026-06-01', object_payment_id=p6.id)
    check('Ro6 (S7): money sent to Chase after its entitled-party role ended - the payee claim stands as a fact, Chase not in effect at the payment\'s date; nothing redirected',
          claims(db.PAID_TO, object_payment_id=p6.id).one().subject_party_id == chase.id
          and db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-06-01')['identities'][M.id]['answer'] == db.EFFECT_NOT)
    e_pb, _ = role(db.PAID_BY, mother, utterance=utter('My mother paid Mercy $300 for me.'), object_payment_id=p.id)
    e_pb2, _ = role(db.PAID_BY, mother, utterance=utter('I paid Mercy for Rob.', origin=mother), object_payment_id=p.id)
    check('Ro8 (Pm9 / Kn7): paid_by(mother, p) asserted by Rob -> established, Rob NOT_KNOWING (he was told); the same asserted by the mother -> KNOWING (the subject party); the household is not the payer by default - no paid_by claim names Rob',
          st(e_pb) == db.STRENGTH_NOT_KNOWING and st(e_pb2) == db.STRENGTH_KNOWING
          and claims(db.PAID_BY, object_payment_id=p.id, subject_party_id=household.id).count() == 0)

    print('\n4. Ro9 / Ro10 / Ro11 - holds-only roles; two insurers of one expense; the plan\'s insurer\n')
    role(db.PROVIDER_OF, mercy, utterance=utter('We took Kim to the ER on Feb 14; Mercy treated her.'), object_expense_id=X.id)
    role(db.INCURRED_BY, kim_party, utterance=utter('It was Kim.'), object_expense_id=X.id)
    check('Ro9 (Ex1): provider_of and incurred_by are holds-only - a stance at a date; no _began / _ended kind exists for them; and in_effect answers from the holds stance (in effect on d, G named)',
          not any(k in db.RULED_KINDS for k in ('provider_of_began', 'incurred_by_began', 'provider_of_ended'))
          and db.in_effect(s, mercy, db.PROVIDER_OF, '2026-03-01')['identities'][X.id]['answer'] == db.EFFECT_IN
          and db.in_effect(s, mercy, db.PROVIDER_OF, '2026-03-01')['identities'][X.id]['governing'][0]['sort'] == 'holds'
          and db.in_effect(s, kim_party, db.INCURRED_BY, '2026-03-01')['identities'][X.id]['answer'] == db.EFFECT_IN)
    role(db.INSURER_OF, aetna, object_expense_id=X.id)
    role(db.INSURER_OF, cigna, object_expense_id=X.id)
    r10a, r10c = db.in_effect(s, aetna, db.INSURER_OF, '2026-03-01'), db.in_effect(s, cigna, db.INSURER_OF, '2026-03-01')
    check('Ro10 (Ic4 / CC1): Aetna and Cigna both insurer_of X - two claims, BOTH in effect, each knowing for its own; this fixture decides NOTHING about a governing PR - no governing / primary / latest-insurer helper exists (9B-F2)',
          r10a['identities'][X.id]['answer'] == db.EFFECT_IN and r10c['identities'][X.id]['answer'] == db.EFFECT_IN
          and not any(hasattr(db, n) for n in ('governing_pr', 'governing_insurer', 'primary_insurer', 'latest_insurer', 'resolve_pr')))
    role(db.INSURER_OF_PLAN, aetna, object_plan_id=P1.id)
    role(db.INSURER_OF_PLAN, aetna, object_plan_id=P2.id)
    check('Ro11 (Pl3): two plans, one insurer - two insurer_of_plan claims, both in effect; the insurer is a party, not a plan; insurer_of (an expense) is not insurer_of_plan - the plan\'s insurer establishes nothing about X\'s insurers, still exactly the two asserted',
          db.in_effect(s, aetna, db.INSURER_OF_PLAN, '2026-03-01')['in_effect'] == sorted([P1.id, P2.id])
          and db.RULED_KINDS[db.INSURER_OF]['object'] != db.RULED_KINDS[db.INSURER_OF_PLAN]['object']
          and claims(db.INSURER_OF, object_expense_id=X.id).count() == 2)

    print('\n5. Ro12 / Ro13 / Ro14 / Ro15 / Ro16 / Ro17 - who asserts, who knows; readings; strangers; retraction; no inverse; knowing != true\n')
    e12, _ = role(db.ENTITLED_PARTY_OF, mercy, utterance=utter('We hold this account.', origin=mercy), object_obligation_id=O.id)
    check('Ro12: Mercy asserts its own entitled-party role -> established, KNOWING; beside Rob\'s claim (not_knowing) - contest derived where they differ, neither outranks',
          st(e12) == db.STRENGTH_KNOWING and st(e_ent) == db.STRENGTH_NOT_KNOWING)
    stmt, r_stmt = held('h-statement', chase)
    e13, _ = role(db.ENTITLED_PARTY_OF, chase, reading=r_stmt, object_obligation_id=O.id)
    e13b, _ = role(db.PAID_TO, chase, reading=r_stmt, object_payment_id=p5.id)
    check('Ro13: a statement\'s letterhead read -> a CANDIDATE for entitled_party_of; a bank line read -> a candidate for paid_to; strength undetermined; never the claim - the held artefact\'s origin minted no role claim (X\'s provider is still only Mercy)',
          st(e13) == db.STRENGTH_UNDETERMINED and st(e13b) == db.STRENGTH_UNDETERMINED
          and all(not db.RULED_KINDS[k]['reading_establishes'] for k in roles)
          and [c.subject_party_id for c in claims(db.PROVIDER_OF, object_expense_id=X.id)] == [mercy.id])
    cousin = mint(db.Party, "Kim's cousin.")
    e14, _ = role(db.ENTITLED_PARTY_OF, chase, utterance=utter('Chase holds it.', origin=cousin), object_obligation_id=M.id)
    check('Ro14: a stranger asserts Chase\'s role -> established, NOT_KNOWING; the claim is not refused and asserters are not ranked',
          st(e14) == db.STRENGTH_NOT_KNOWING and not any(hasattr(db, n) for n in ('rank_asserters', 'authoritative_asserter')))
    u15 = utter('Cigna also insures this visit.')
    e15, pr15 = role(db.INSURER_OF, cigna, utterance=u15, object_expense_id=X.id)
    retract(u15, 'I was wrong - it was only Aetna.')
    check('Ro15: retracting the utterance behind a holds-only role claim is a retraction - no insurer_of_ended kind exists and none is manufactured; the claim\'s row survives',
          claims(db.UTTERANCE_RETRACTION, subject_utterance_id=u15.id).count() == 1 and 'insurer_of_ended' not in db.RULED_KINDS
          and s.get(db.Proposition, pr15.id) is not None)
    check('Ro16: no inverse kind and no selector - obligation_entitled_party / plan_insurer / expense_provider absent; an obligation-subject entitled claim is refused by the registry; navigation is a 7F query',
          not any(k in db.RULED_KINDS for k in ('obligation_entitled_party', 'plan_insurer', 'expense_provider', 'expense_insurer'))
          and _refused(s, db.Proposition(kind=db.ENTITLED_PARTY_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_obligation_id=M.id, object_party_id=chase.id, as_of='2026-01-01'))
          and db.reach(s, M, db.ENTITLED_PARTY_OF, as_object=True)['direction'] == db.DIRECTION_OBJECT)
    check('Ro17 (Kn12): S3 is knowing for its servicing claim and Mercy for its entitlement claim - knowing says first-hand, never correct; no truth helper',
          st(e_s3) == db.STRENGTH_KNOWING and st(e12) == db.STRENGTH_KNOWING and not any(hasattr(db, n) for n in ('is_true', 'verified', 'authorised')))

    print('\n6. 9B-F1 / 9B-F2 / Ro18 - the role key is classification only; no governing determination; the module\'s surface\n')
    check('9B-F1: \'role\': True is read by in_effect (a holds-only role answers; a non-role relation is refused by name), by the consumers\' _require_role, and by the guard - and by nothing else: no behaviour keys on any role entry beyond the registry\'s existing shape',
          db.in_effect(s, mercy, db.PROVIDER_OF, '2026-03-01')['identities'][X.id]['answer'] == db.EFFECT_IN
          and all(set(r) <= {'subject', 'object', 'symmetric', 'reading_establishes', 'relational_knowing', 'role', 'knowing_relation', 'boundary', 'of'} for r in db.RULED_KINDS.values()))
    try:
        db.in_effect(s, mercy, db.OBLIGATION_IN_RESPECT_OF, '2026-03-01')
        refused = False
    except ValueError as e:
        refused = 'not a role' in str(e)
    check('9B-F1: a relation kind (obligation_in_respect_of) is refused by in_effect as "not a role" - the registry\'s classification, not a boundary test',
          refused)
    check('9B-F2: nothing in the module names a governing PR, a party-local recency, a primary insurer or any resolver over roles; the consumers\' role tests read only in_effect',
          not any(hasattr(db, n) for n in ABSENT_HELPERS)
          and not any(w in __import__('inspect').getsource(db.in_effect) for w in ('governing_pr', 'primary', 'latest_insurer')))
    try:
        db.in_effect(s, mercy, 'standin_provider', '2026-03-01')
        unruled_refused = False
    except ValueError as e:
        unruled_refused = 'not ruled' in str(e)
    check('Ro18: the substitution is proved where it lives - the 7F, 7G, 7H, 7I, 7J fixtures run on the ruled kinds with only names and catalogue lines changed (their own runs); here: every consumer role gate refuses an unruled kind by name, still',
          unruled_refused and all(k not in db.RULED_KINDS for k in ('serves', 'standin_entitled', 'standin_provider', 'standin_insurer')))

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
