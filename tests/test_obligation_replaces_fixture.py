"""obligation_replaces - the executable trace of `gw 2.0/RELATION_SEMANTICS.md` pass B (ruled 2026-09-15).

`obligation_replaces(O3, O1)` means exactly: the asserting party holds that the subject obligation
was incurred in substitution for some or all of the object obligation. Both participants are
established obligations; directional, never symmetric, no inverse kind, no cardinality; established
only by a party's assertion; carries no amount and no transfer semantics; derives nothing - and
"in substitution for" is not a temporal or lifecycle assertion.

Of the five phenomena, four are NOT this relation (B.2): changed terms, a transfer of servicing /
assignment / sale / recourse, a new dated stance, and an ending beside a beginning are claims on
ONE obligation. The fixture exercises those absences as carefully as the presences.

What this slice can and cannot exercise
---------------------------------------
    B1  modification: a terms claim on O1; no O3; no relation                            EXERCISED
    B2  the household says "new plan": O3 minted; O3 replaces O1; O1 has no status        EXERCISED
    B3  refinance: O3 minted · payoff payment (toward = stand-in) · creditor's letter · relation - four things, none derives another  EXERCISED
    B4  consolidation: one loan replaces three cards - three claims                       EXERCISED
    B5  partial: the relation carries no amount; O1 continues                             EXERCISED
    B6  split: two plans replace one bill                                                 EXERCISED
    B7  arrears: the $525 is a position under the old terms; no disposition on the relation  EXERCISED
    B8  sale / new account number: one O, a role claim; NO relation; a second minting is Ob7  EXERCISED
    B9  the PAYOFF line and the matcher: a reading-sourced candidate at most; mints nothing   EXERCISED
    B10 direction is asserted, never derived from minting order                           EXERCISED
    B11 chain: O5 replaces O3 derives nothing about O1                                    EXERCISED
    B12 disputed successor: two claims, contested, nothing chosen                          EXERCISED
    B13 retraction: obligations untouched; no opposite relation                            EXERCISED
    B14 paid off and closed, no successor: a dated claim about O1, NO relation             EXERCISED
    B15 payoff $40 short, creditor keeps billing: the relation and the balance both stand  EXERCISED
    B16 the new lender asserts it; knowing undetermined                                    EXERCISED
    B17 refinance / consolidation / rollover / balance transfer / restructure are not kinds  EXERCISED (absence)
    B18 bill -> plan: the household says which arm; nothing infers it                      EXERCISED
    both endpoints established obligations; reflexive refused; cross-type refused           EXERCISED
    no closed/replaced status, no discharge, no disposition field, no inverse, no transitivity, no family base  EXERCISED (absence)
    knowing for the relation (which role), 8.1-b disposition, discharge / remaining (item 7), passes C-G  NOT BUILT

Run:  python tests/test_obligation_replaces_fixture.py
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


STATUS_WORDS = ('replaced', 'closed', 'settled', 'discharged', 'ended', 'succeeded', 'superseded', 'active',
                'obligation_status', 'obligation_state', 'remaining', 'carried')
CONSUMER_NAMES = ('replaced_by', 'replaces', 'successor_of', 'predecessor_of', 'is_replaced', 'is_discharged',
                  'discharged_by', 'discharge_of', 'carried_into', 'transferred_from', 'disposition_of',
                  'remaining_on', 'inverse_of', 'relations_of', 'Relation', 'RelationBase', 'resolve_relation',
                  'relation_resolver', 'related_obligations', 'successor_chain', 'current_obligation',
                  'obligation_ended', 'obligation_began', 'infer_restructure_arm')
SOURCE_KINDS = ('refinances', 'refinance_of', 'consolidates', 'consolidation_of', 'restructures', 'restructure_of',
                'rolls_into', 'rollover_of', 'transfers_balance', 'balance_transfer', 'settles', 'settled_by',
                'supersedes', 'obligation_supersedes', 'obligation_succeeds', 'obligation_relation',
                'obligation_ended', 'obligation_began', 'obligation_settles', 'obligation_refinances',
                'obligation_consolidates', 'obligation_transfers')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_or_')
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}, 'terms': {'person', 'institution'},
               'balance': {'institution'}, 'entitled_party': {'person', 'institution'}, 'closed': {'person'}}

    def utter(text, when='2026-09-01T09:00:00', origin=None):
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

    def owe(text, when):
        u = utter(text, when)
        o = db.Obligation(minted_by_id=u.id)
        s.add(o)
        s.commit()
        return o, u

    def pay(text, when):
        u = utter(text, when)
        p = db.Payment(minted_by_id=u.id)
        s.add(p)
        s.commit()
        return p, u

    def prop(kind, object_state=db.PARTICIPANT_ESTABLISHED, **slots):
        p = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=object_state, **slots)
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

    def about(kind, o, content, utterance=None, reading=None, as_of=None):
        # a stand-in dated stance about one obligation: subject the obligation, no second participant
        pr = prop(kind, object_state=db.PARTICIPANT_NONE, subject_obligation_id=o.id, content=content, as_of=as_of)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def role(kind, party, o, as_of, utterance):
        # a stand-in dated role claim: subject the party, object the obligation, as_of the effective date
        pr = prop(kind, subject_party_id=party.id, object_obligation_id=o.id, as_of=as_of)
        return evidence(pr, utterance=utterance), pr

    def replaces(subject, obj, utterance=None, reading=None, content=None, as_of=None):
        pr = prop(db.OBLIGATION_REPLACES, subject_obligation_id=subject.id, object_obligation_id=obj.id,
                  content=content, as_of=as_of)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def rel(subject=None, obj=None):
        q = s.query(db.Proposition).filter_by(kind=db.OBLIGATION_REPLACES)
        if subject is not None:
            q = q.filter_by(subject_obligation_id=subject.id)
        if obj is not None:
            q = q.filter_by(object_obligation_id=obj.id)
        return q

    def stances(kind, o):
        return s.query(db.Proposition).filter_by(kind=kind, subject_obligation_id=o.id)

    chase, u_chase = mint_party('Chase, my mortgage lender.')
    newbank, u_newbank = mint_party('NewBank, the refinance lender.')
    mercy, u_mercy = mint_party('Mercy Hospital.')
    newco, u_newco = mint_party('NewCo Servicing.')

    print('\n1. The registry entry - exactly as authorised\n')
    check('obligation_replaces is ruled exactly as authorised: obligation subject, obligation object, not symmetric, reading never establishes, relational_knowing True, no knowing_relation',
          db.RULED_KINDS[db.OBLIGATION_REPLACES] == {'subject': ('subject_obligation_id',), 'object': ('object_obligation_id',),
                                                    'symmetric': False, 'reading_establishes': False, 'relational_knowing': True})
    check('no source-word, succession, boundary or generic obligation-relation kind exists beside it',
          not any(k in db.RULED_KINDS for k in SOURCE_KINDS))
    # Pass C added obligation_in_respect_of on the obligation subject slot (RELATION_SEMANTICS.md C.9) - an
    # obligation -> expense relation, not an obligation -> obligation one; recorded here truthfully.
    check('the only ruled kinds on the obligation-subject slot are obligation_corresponds, obligation_replaces and obligation_in_respect_of - the role and stance kinds used here stay stand-ins',
          set(k for k, r in db.RULED_KINDS.items() if 'subject_obligation_id' in r['subject']) == {db.OBLIGATION_CORRESPONDS, db.OBLIGATION_REPLACES, db.OBLIGATION_IN_RESPECT_OF}
          and not any(k in db.RULED_KINDS for k in ('terms', 'entitled_party', 'balance', 'closed', 'toward')))

    print('\n2. B1 - modification: same mortgage, new terms; no O3, no relation\n')
    o1, u_o1 = owe('I have a mortgage with Chase - account ending 4471, about $180k.', '2019-06-01T09:00:00')
    role('entitled_party', chase, o1, '2019-06-01', u_o1)
    n_obl = s.query(db.Obligation).count()
    about('terms', o1, '30-year re-amortisation, $1,290/month', utterance=utter('Chase modified the loan - same mortgage, new payment.', '2026-12-01T09:00:00'), as_of='2026-11-15')
    check('B1: a modification is a dated terms claim on O1 with as_of the effective date - one participant',
          stances('terms', o1).count() == 1 and stances('terms', o1).one().as_of == '2026-11-15')
    check('B1: no obligation was minted by the modification and no relation exists - the first Ob6 arm needs none',
          s.query(db.Obligation).count() == n_obl and rel().count() == 0)

    print('\n3. B2 - "they closed the old plan and started a new one": O3 minted; O3 replaces O1; O1 has no status\n')
    o_plan1, u_plan1 = owe('Mercy put the ER bill on a $175/month plan - $3,000.', '2026-01-10T09:00:00')
    role('entitled_party', mercy, o_plan1, '2026-01-10', u_plan1)
    n_obl = s.query(db.Obligation).count()
    o_plan2, u_plan2 = owe('Mercy closed that plan and started a new one at $250/month.', '2026-09-01T09:00:00')
    e_b2, r_b2 = replaces(o_plan2, o_plan1, utterance=utter('The new plan took the place of the old one.', '2026-09-01T09:05:00'))
    check('B2: the relation is a claim with two established obligation participants - the replacing obligation the subject',
          r_b2.subject_obligation_id == o_plan2.id and r_b2.object_obligation_id == o_plan1.id
          and r_b2.subject_state == db.PARTICIPANT_ESTABLISHED and r_b2.object_state == db.PARTICIPANT_ESTABLISHED)
    check('B2: O1 acquires no status - the obligation anchor carries nothing; no closed/replaced/discharged accessor exists',
          {c.name for c in db.Obligation.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and not any(hasattr(db.Obligation, w) for w in STATUS_WORDS)
          and not any(hasattr(db, n) for n in CONSUMER_NAMES))
    check('B2: two obligations remain two identities - the relation merges nothing and mints nothing',
          s.get(db.Obligation, o_plan1.id) is not None and s.get(db.Obligation, o_plan2.id) is not None
          and s.query(db.Obligation).count() == n_obl + 1)

    print('\n4. B3 - refinance: four separate things; none derives another\n')
    o3, u_o3 = owe('I refinanced with NewBank - new loan, 15 years.', '2027-01-05T09:00:00')
    role('entitled_party', newbank, o3, '2027-01-03', u_o3)
    n_rel = rel().count()
    p_payoff, u_payoff = pay('NewBank sent Chase the payoff - $178,412 on Jan 3.', '2027-01-05T09:01:00')
    prop('paid_by', object_state=db.PARTICIPANT_NONE, subject_payment_id=p_payoff.id, content='NewBank')
    evidence(prop('toward', subject_payment_id=p_payoff.id, object_obligation_id=o1.id), utterance=u_payoff)   # stand-in, unruled
    check('B3: the payoff is a payment (payer NewBank - Pm9) claimed toward O1 by a stand-in; it asserted no obligation relation',
          rel().count() == n_rel and 'toward' not in db.RULED_KINDS
          and s.query(db.Proposition).filter_by(kind='toward', subject_payment_id=p_payoff.id, object_obligation_id=o1.id).count() == 1)
    letter = db.Artefact(held=True, content_hash='h-paid-in-full', as_of='2027-01-10')
    s.add(letter)
    s.commit()
    evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=letter.id, object_party_id=chase.id), utterance=u_chase)
    rd_letter = db.Reading(artefact_id=letter.id, reader_process='pdf-extract/1', read_at=datetime(2027, 1, 12))
    s.add(rd_letter)
    s.commit()
    n_obl = s.query(db.Obligation).count()
    about('balance', o1, '$0.00 - PAID IN FULL', reading=rd_letter, as_of='2027-01-10')
    check("B3: Chase's paid-in-full letter is an artefact whose reading yields a balance claim about O1 - it mints nothing and relates nothing",
          s.query(db.Obligation).count() == n_obl and rel().count() == n_rel)
    e_b3, r_b3 = replaces(o3, o1, utterance=utter('The NewBank loan replaced the Chase mortgage.', '2027-01-05T09:10:00'))
    check('B3: the relation is the fourth thing - asserted by Rob, with O3 the subject and O1 the object; it is not toward, not acknowledgment, not correspondence',
          rel(o3, o1).count() == 1 and r_b3.kind == db.OBLIGATION_REPLACES
          and s.query(db.Proposition).filter_by(kind=db.OBLIGATION_CORRESPONDS).count() == 0)
    check('B3: the relation does not establish the discharge and the payment does not establish the relation - no helper joins them',
          not any(hasattr(db, n) for n in ('discharged_by', 'is_discharged', 'discharge_of', 'relation_from_payment', 'payoff_establishes')))

    print('\n5. B4 / B6 - no cardinality: one loan replaces three cards; one bill split into two plans\n')
    c1, _ = owe('The Visa - about $4,000.', '2025-03-01T09:00:00')
    c2, _ = owe('The store card - about $1,200.', '2025-03-01T09:01:00')
    c3, _ = owe('The Mastercard - about $2,800.', '2025-03-01T09:02:00')
    o4, u_o4 = owe('The consolidation loan from the credit union - $8,000.', '2026-04-01T09:00:00')
    u_consol = utter('The credit union loan paid off all three cards.', '2026-04-01T09:05:00')
    for c in (c1, c2, c3):
        replaces(o4, c, utterance=u_consol, content='consolidation')
    check('B4: one obligation replaces three - three claims, one utterance; no uniqueness anywhere',
          rel(o4).count() == 3)
    o_bill, u_bill = owe('The surgery bill from Mercy - $6,400.', '2026-05-01T09:00:00')
    o_fac, _ = owe("Mercy's facility plan - $200/month.", '2026-06-01T09:00:00')
    o_phys, _ = owe("The physicians' group plan - $150/month.", '2026-06-01T09:01:00')
    u_split = utter('They split the surgery bill into two plans.', '2026-06-01T09:05:00')
    replaces(o_fac, o_bill, utterance=u_split)
    replaces(o_phys, o_bill, utterance=u_split)
    check('B6: one obligation replaced by two - two claims; nothing apportions O1 between them',
          rel(obj=o_bill).count() == 2 and not any(hasattr(db, n) for n in ('apportion', 'apportionment_of', 'share_of')))

    print('\n6. B5 / B7 - partial and arrears: the relation carries no amount and no disposition\n')
    c4, u_c4 = owe('The Discover card - $8,000.', '2025-03-01T09:03:00')
    e_b5, r_b5 = replaces(o4, c4, utterance=utter('The credit union loan covered $5,000 of the Discover balance.', '2026-04-01T09:06:00'), content='$5,000 of it')
    check('B5: a partial substitution is the same kind - "$5,000 of it" is content; the relation row carries no amount and nothing computes the $3,000 that continues',
          r_b5.kind == db.OBLIGATION_REPLACES and 'amount' not in {c.name for c in db.Proposition.__table__.columns}
          and not any(hasattr(db, n) for n in ('remaining_on', 'remaining_after', 'carried_into', 'transferred_amount')))
    check('B5: O1 continues un-statused beside the relation - a later balance claim on it is accepted like any other',
          (about('balance', c4, '$3,012.40', utterance=utter('Discover says $3,012.40 as of May.', '2026-05-05T09:00:00', origin=household), as_of='2026-05-01'),
           stances('balance', c4).count() == 1)[1])
    about('overdue', o_plan1, '$525 behind the $175 schedule', utterance=utter('I was three payments behind on the old plan.', '2026-09-01T09:06:00'), as_of='2026-08-31')
    check('B7: the $525 is a schedule-relative position under the old terms - a dated claim on O1, reconstructable; the relation between the plans carries nothing about it',
          stances('overdue', o_plan1).count() == 1 and r_b2.content is None
          and not any(w in c.name for w in ('carried', 'rolled', 'disposition', 'transfer') for c in db.Proposition.__table__.columns)
          and not any(hasattr(db, n) for n in ('disposition_of', 'carried_into', 'rolled_into', 'transfer_of')))

    print('\n7. B8 - sale and a new account number: one obligation, a role claim; a second minting is Ob7, not this kind\n')
    n_rel = rel().count()
    u_sale = utter('Chase sold the mortgage to NewCo - new account number, effective March 14; their letter came in September.', '2026-09-09T09:00:00')
    role('entitled_party', newco, o1, '2026-03-14', u_sale)
    check('B8: the sale is a dated role claim on O1 (as_of the effective date, recorded when learned); no relation and no new obligation',
          s.query(db.Proposition).filter_by(kind='entitled_party', object_obligation_id=o1.id).count() == 2
          and rel().count() == n_rel)
    o_dup, u_dup = owe('The NewCo loan - account 88-2201.', '2026-09-20T09:00:00')
    evidence(prop(db.OBLIGATION_CORRESPONDS, subject_obligation_id=o_dup.id, object_obligation_id=o1.id),
             utterance=utter("That's the same mortgage - NewCo just renumbered it.", '2026-09-21T09:00:00'))
    check('B8: if the household mints "the NewCo loan" and then says it is the same mortgage, that is obligation_corresponds - not obligation_replaces; the household says which',
          s.query(db.Proposition).filter_by(kind=db.OBLIGATION_CORRESPONDS, subject_obligation_id=o_dup.id).count() == 1
          and rel(o_dup).count() == 0 and rel(obj=o_dup).count() == 0
          and db.referent(s, o_dup)[0] in ('corresponding', 'contested'))

    print("\n8. B9 - NewBank's statement and the PAYOFF line: a candidate at most; nothing minted\n")
    stmt = db.Artefact(held=True, content_hash='h-newbank-stmt', as_of='2027-02-01')
    s.add(stmt)
    s.commit()
    evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=stmt.id, object_party_id=newbank.id), utterance=u_newbank)
    rd = db.Reading(artefact_id=stmt.id, reader_process='pdf-extract/1', read_at=datetime(2027, 2, 3))
    s.add(rd)
    s.commit()
    n_obl = s.query(db.Obligation).count()
    p_line = prop('disbursement', object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=newbank.id,
                  content='PAYOFF - CHASE ****4471 178,412.00', as_of='2027-01-03')
    evidence(p_line, reading=rd)
    check('B9: the PAYOFF line is a proposition from a capture with candidates - it minted no obligation and asserted no relation',
          s.query(db.Obligation).count() == n_obl
          and s.query(db.EvidentiaryRelationship).join(db.Proposition).filter(db.Proposition.kind == db.OBLIGATION_REPLACES,
                                                                            db.EvidentiaryRelationship.reading_id.isnot(None)).count() == 0)
    c_line = prop(db.OBLIGATION_REPLACES, subject_obligation_id=o3.id, object_obligation_id=o1.id,
                  content='matcher: disbursement equals the Chase payoff')
    e_cand = evidence(c_line, reading=rd)
    check("B9: the matcher's pairing is a reading-sourced candidate - no party behind it; it establishes nothing and is not knowing",
          e_cand.utterance_id is None and e_cand.reading_id == rd.id
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c_line.id).count() == 1
          and not db.RULED_KINDS[db.OBLIGATION_REPLACES]['reading_establishes']
          and db.derived_strength(s, e_cand, KNOWING) == db.STRENGTH_UNDETERMINED)

    print('\n9. B10 / B11 - direction is asserted; the chain derives nothing\n')
    o_late, u_late = owe("The old HELOC I never entered - it was paid off by the 2020 refi.", '2027-03-01T09:00:00')
    o_refi2020, _ = owe('The 2020 refinance loan.', '2027-03-01T09:01:00')
    replaces(o_refi2020, o_late, utterance=utter('The 2020 loan replaced that HELOC.', '2027-03-01T09:05:00'), as_of='2020-08-01')
    check('B10: the replacing obligation is the subject even when it was minted before the replaced one - direction is asserted, never derived from minting order or dates',
          rel(o_refi2020, o_late).count() == 1 and o_late.id < o_refi2020.id
          and rel(o_late, o_refi2020).count() == 0)
    replaces(o3, o_refi2020, utterance=utter('And the NewBank loan replaced the 2020 loan.', '2027-03-01T09:06:00'))
    check('B11: O3 replaces the 2020 loan is one claim; O3 replaces the HELOC does not exist and is not derived',
          rel(o3, o_refi2020).count() == 1 and rel(o3, o_late).count() == 0)

    print('\n10. B12 / B13 - disputed successor; retraction\n')
    o_heloc, _ = owe('Our current HELOC with Chase.', '2024-02-01T09:00:00')
    u_kim = db.Utterance(origin_party_id=kim_party.id, asserted_at='2027-01-06T09:00:00', content='No - the NewBank loan replaced the HELOC, not the mortgage.')
    s.add(u_kim)
    s.commit()
    replaces(o3, o_heloc, utterance=u_kim)
    check('B12: Rob says O3 replaces the mortgage, Kim says O3 replaces the HELOC - two claims stand; nothing chooses; no current successor',
          rel(o3, o1).count() >= 1 and rel(o3, o_heloc).count() == 1
          and not any(hasattr(db, n) for n in ('current_successor', 'successor_of', 'resolve_replaces')))
    n_rel = rel().count()
    n_obl = s.query(db.Obligation).count()
    r = prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_consol.id)
    evidence(r, utterance=utter("I was wrong - the credit union loan didn't pay off the store card.", '2026-04-15T09:00:00'))
    check('B13: retracting the utterance behind relation claims leaves every obligation and every relation row; no opposite relation appears and nothing is "restored"',
          rel().count() == n_rel and s.query(db.Obligation).count() == n_obl
          and rel(c2, o4).count() == 0 and not any(hasattr(db, n) for n in ('restore', 'restored', 'reinstate')))

    print('\n11. B14 / B15 - no successor, no relation; a successor derives no ending\n')
    c5, u_c5 = owe('The Amex - about $900.', '2025-03-01T09:04:00')
    about('closed', c5, 'paid off and closed', utterance=utter('I paid off the Amex and closed it.', '2026-07-01T09:00:00'), as_of='2026-06-30')
    about('balance', c5, '$0.00', utterance=utter('Amex confirms a zero balance.', '2026-07-02T09:00:00', origin=household), as_of='2026-06-30')
    check('B14: paying off and closing is a dated claim about one obligation - no second obligation, no relation, no successor manufactured',
          stances('closed', c5).count() == 1 and rel(obj=c5).count() == 0 and rel(c5).count() == 0)
    about('balance', o1, '$40.18 - remaining balance after payoff', reading=rd_letter, as_of='2027-02-01')
    about('balance', o1, '$40.18 plus late fee', utterance=utter('Chase is still billing the old mortgage - the payoff was $40 short.', '2027-02-20T09:00:00'), as_of='2027-02-15')
    check('B15: O3 replaces O1 stands beside Chase\'s continued balance claims on O1 - both true as asserted; the relation derived no ending, discharge or status',
          rel(o3, o1).count() >= 1 and stances('balance', o1).count() == 3
          and not any(hasattr(db.Obligation, w) for w in STATUS_WORDS)
          and not any(hasattr(db, n) for n in ('is_discharged', 'discharged_by', 'obligation_ended', 'ended_on')))
    check('B15: "in substitution for" is not a lifecycle assertion - no boundary kind is bound to obligation_replaces and no obligation boundary kind exists',
          db.boundary_kinds_of(db.OBLIGATION_REPLACES) == {}
          and not any(rule.get('of') == db.OBLIGATION_REPLACES or rule.get('boundary') and 'obligation' in kind
                      for kind, rule in db.RULED_KINDS.items()))

    print('\n12. B16 - the new lender asserts it; knowing undetermined\n')
    u_nb_says = utter('Proceeds were disbursed to pay off the borrower\'s Chase loan ending 4471.', '2027-01-04T09:00:00', origin=newbank)
    e_b16, r_b16 = replaces(o3, o1, utterance=u_nb_says, content='per closing disclosure')
    check('B16: an institution may assert the relation as a party - a claim with its own evidence; "payoff" is content',
          e_b16.utterance.origin_party_id == newbank.id and 'closing' in r_b16.content)
    check('B16: knowing for the relation is undetermined for every asserter - ruled True with no designated relation; neither obligor-of-subject nor entitled-of-object is forced',
          db.derived_strength(s, e_b16, KNOWING) == db.STRENGTH_UNDETERMINED
          and db.derived_strength(s, e_b3, KNOWING) == db.STRENGTH_UNDETERMINED
          and db.derived_strength(s, e_b2, KNOWING) == db.STRENGTH_UNDETERMINED
          and 'knowing_relation' not in db.RULED_KINDS[db.OBLIGATION_REPLACES])

    print('\n13. B18 - a bill becomes a plan: the household says which arm; nothing infers it\n')
    o_bill2, u_bill2 = owe('The MRI bill from Mercy - $1,150.', '2026-08-01T09:00:00')
    role('entitled_party', mercy, o_bill2, '2026-08-01', u_bill2)
    n_obl = s.query(db.Obligation).count()
    n_rel = rel().count()
    about('terms', o_bill2, '$100/month payment plan', utterance=utter('Mercy put the MRI bill on a payment plan - same bill.', '2026-08-20T09:00:00'), as_of='2026-08-15')
    check('B18: "same bill, now on a plan" is the first arm - a terms claim; the same creditor and the word "plan" mint nothing and relate nothing',
          s.query(db.Obligation).count() == n_obl and rel().count() == n_rel
          and not any(hasattr(db, n) for n in ('infer_restructure_arm', 'restructure_arm', 'is_same_obligation')))
    check('B18: had the household said "a new plan", B2 is available - both arms are representable and the substrate records the choice, never infers it',
          rel(o_plan2, o_plan1).count() == 1 and stances('terms', o_bill2).count() == 1)

    print('\n14. Structure - both participants established obligations; reflexive and cross-type refused; references immutable\n')
    check('B10: the relation is not symmetric - asserting O1 replaces O3 is a different claim, and it is not derived from O3 replaces O1',
          not db.RULED_KINDS[db.OBLIGATION_REPLACES]['symmetric'] and rel(o1, o3).count() == 0)
    check('reflexive and cross-type are refused; both participants must be established obligations',
          _refused(s, db.Proposition(kind=db.OBLIGATION_REPLACES, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_obligation_id=o1.id, object_obligation_id=o1.id))
          and _refused(s, db.Proposition(kind=db.OBLIGATION_REPLACES, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_obligation_id=o3.id, object_payment_id=p_payoff.id))
          and _refused(s, db.Proposition(kind=db.OBLIGATION_REPLACES, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_party_id=newbank.id, object_obligation_id=o1.id))
          and _refused(s, db.Proposition(kind=db.OBLIGATION_REPLACES, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                         subject_obligation_id=o3.id)))
    check("the relation's references are immutable - re-pointing a participant is refused; correction is retraction + a new claim",
          (lambda: (r_b3.object_obligation_id, setattr(r_b3, 'object_obligation_id', o_heloc.id), _refused(s, r_b3))[2])()
          and s.get(db.Proposition, r_b3.id).object_obligation_id == o1.id)

    print('\n15. B17 / absences\n')
    check('B17: refinance, consolidation, rollover, balance transfer, restructure, payment plan are content or claims about the replacing obligation - none is a kind; modification is no relation',
          not any(k in db.RULED_KINDS for k in SOURCE_KINDS)
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(SOURCE_KINDS)).count() == 0)
    check('no generic relation base, resolver, inverse accessor, successor chain, status, discharge or disposition helper was introduced',
          not any(hasattr(db, n) for n in CONSUMER_NAMES)
          and not any(w in c.name for w in STATUS_WORDS for c in db.Proposition.__table__.columns))
    check('no schema: the obligation anchor and the proposition slots are as the obligation slice left them; no relation table exists',
          {c.name for c in db.Obligation.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and 'subject_obligation_id' in db.Proposition.SUBJECT_SLOTS and 'object_obligation_id' in db.Proposition.OBJECT_SLOTS
          and not any('relation' in t or 'succession' in t for t in db.Base.metadata.tables))
    check('every audit is empty',
          not db.obligations_without_minting_utterance(s) and not db.payments_without_minting_utterance(s)
          and not db.parties_without_one_anchor(s))

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
