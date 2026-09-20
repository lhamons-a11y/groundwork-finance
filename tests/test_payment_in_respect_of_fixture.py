"""payment_in_respect_of - the executable trace of `gw 2.0/RELATION_SEMANTICS.md` pass D (ruled 2026-09-15).

`payment_in_respect_of(p, X)` means exactly: the asserting party holds that the subject payment was in
respect of the object expense - and nothing above that floor. "In respect of" identifies the asserted
subject/object relationship; it does not describe the economic purpose, direction, funding mechanism or
legal effect of the payment. Both participants are established; direction is fixed by participant type;
no inverse kind; no cardinality, and cardinality is not allocation; party-asserted only; carries no
amount, no payer/payee semantics, no direction of money; derives nothing. "Payment = money movement for
expense" is three collapses (movement, funding, one-to-one), each refused.

What this slice can and cannot exercise
---------------------------------------
    D1  Ex8: the CVS charge was Kim's prescription - p, X, the relation; no obligation           EXERCISED
    D2  the bank line: mints neither, proves no purpose; the matcher's pairing is a candidate       EXERCISED
    D3  one expense, three payments - cardinality is not allocation                               EXERCISED
    D4  one payment, two expenses - no allocation, split, percentage or order of satisfaction     EXERCISED
    D5  a payment with no expense; D6 an expense with no payment - no relation, nothing manufactured  EXERCISED
    D7  disputed attribution: two claims, contested                                                EXERCISED
    D8  the chain (toward + obligation_in_respect_of): no composition either way; discharge untouched  EXERCISED
    D9  reimbursement: money to the household; the same kind                                      EXERCISED
    D10 amounts: copay $30 / PR $412 / billed $1,300 - the relation reconciles nothing             EXERCISED
    D11 the 1.x allocation row decomposed; no amount / mode / station on the edge                  EXERCISED (absence)
    D12 the determinations are not this kind and not derived                                       EXERCISED (absence)
    D13 direction fixed by type; the slots swapped refused; no inverse kind                        EXERCISED
    D14 retraction: p, X, X' untouched                                                             EXERCISED
    D15 composition with payment_counteracts refused both ways                                     EXERCISED
    D16 paid for / funded / covered / reimbursed / copay / attached are not kinds                  EXERCISED (absence)
    D17 the mixed basket: no manufactured expense for the shampoo, no remainder                    EXERCISED
    D18 the insurer's payment: no household party on p; the EOB's plan-paid is a stance on X       EXERCISED
    D19 the mother paid: no payer/incurrer mirroring                                               EXERCISED
    D20 the receipt concerns both; CVS may assert; establishes neither endpoint                    EXERCISED
    D21 the deposit before the surgery: no temporal precedence                          EXERCISED - PERMANENT
    D22 the semantic floor: "in respect of" != "made for"                                          EXERCISED
    knowing for the relation (which role), the determinations / reconciliation (item 7), D' toward, passes E-G  NOT BUILT

Run:  python tests/test_payment_in_respect_of_fixture.py
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


STATUS_WORDS = ('paid', 'reimbursed', 'covered', 'funded', 'settled', 'unpaid', 'remaining', 'allocated', 'expense_status')
CONSUMER_NAMES = ('payments_for_expense', 'expenses_for_payment', 'payment_for', 'expense_of_payment', 'payments_of_expense',
                  'allocate', 'allocation_of', 'split_of', 'share_of', 'apportion', 'remainder_of', 'unallocated',
                  'is_paid', 'paid_for', 'expense_paid', 'is_reimbursed', 'net_cost', 'net_cost_of', 'reconcile',
                  'reconciled_amount', 'corresponding_amount', 'funds', 'funded_by', 'funder_of', 'direction_of',
                  'inverse_of', 'relations_of', 'Relation', 'RelationBase', 'resolve_relation', 'relation_resolver',
                  'expense_precedes', 'payment_precedes', 'order_of', 'determination', 'determine', 'user_paid_cash',
                  'derive_expense', 'toward_from_expense')
SOURCE_KINDS = ('paid_for', 'payment_paid_for', 'payment_funds', 'payment_funded', 'payment_reimburses', 'payment_covers',
                'payment_copay', 'payment_attached', 'payment_allocated', 'payment_allocation', 'payment_expense_relation',
                'payment_for', 'payment_for_expense', 'funds', 'reimburses', 'covers', 'attached', 'allocated')
INVERSE_KINDS = ('expense_paid_by', 'expense_funded_by', 'expense_has_payment', 'expense_in_respect_of_payment',
                 'expense_reimbursed_by', 'expense_payment')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_piro_')
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}, 'amount': {'person', 'institution'},
               'patient_responsibility': {'institution'}, 'billed': {'institution'}, 'plan_paid': {'institution'},
               'paid_by': {'person', 'institution'}, 'paid_to': {'person', 'institution'}}   # cleared: ruled since 9D-iv

    def utter(text, when='2026-03-03T09:00:00', origin=None):
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

    def pay(text, when, origin=None):
        u = utter(text, when, origin=origin)
        p = db.Payment(minted_by_id=u.id)
        s.add(p)
        s.commit()
        return p, u

    def incur(text, when):
        u = utter(text, when)
        x = db.Expense(minted_by_id=u.id)
        s.add(x)
        s.commit()
        return x, u

    def owe(text, when):
        u = utter(text, when)
        o = db.Obligation(minted_by_id=u.id)
        s.add(o)
        s.commit()
        return o, u

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

    def about_p(kind, p, content, utterance=None, reading=None, as_of=None):
        pr = prop(kind, object_state=db.PARTICIPANT_NONE, subject_payment_id=p.id, content=content, as_of=as_of)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def about_x(kind, x, content, utterance=None, reading=None, as_of=None):
        pr = prop(kind, object_state=db.PARTICIPANT_NONE, subject_expense_id=x.id, content=content, as_of=as_of)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def role_p(kind, party, p, utterance):
        # a stand-in role claim on the payment: paid_by / paid_to - subject the party, object the payment
        pr = prop(kind, subject_party_id=party.id, object_payment_id=p.id)
        return evidence(pr, utterance=utterance), pr

    def role_x(kind, party, x, utterance):
        pr = prop(kind, subject_party_id=party.id, object_expense_id=x.id)
        return evidence(pr, utterance=utterance), pr

    def held(h, as_of, origin_party, origin_utt):
        a = db.Artefact(held=True, content_hash=h, as_of=as_of)
        s.add(a)
        s.commit()
        evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=a.id, object_party_id=origin_party.id), utterance=origin_utt)
        return a

    def read(a, process='feed-import/1'):
        r = db.Reading(artefact_id=a.id, reader_process=process, read_at=datetime(2026, 3, 5))
        s.add(r)
        s.commit()
        return r

    def concerns(a, utterance, p=None, x=None):
        pr = prop(db.ARTEFACT_CONCERNS, subject_artefact_id=a.id,
                  object_payment_id=p.id if p else None, object_expense_id=x.id if x else None)
        return evidence(pr, utterance=utterance), pr

    def in_respect_of(p, x, utterance=None, reading=None, content=None, as_of=None):
        pr = prop(db.PAYMENT_IN_RESPECT_OF, subject_payment_id=p.id, object_expense_id=x.id, content=content, as_of=as_of)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def rel(p=None, x=None):
        q = s.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF)
        if p is not None:
            q = q.filter_by(subject_payment_id=p.id)
        if x is not None:
            q = q.filter_by(object_expense_id=x.id)
        return q

    def stances(kind, subject_col, ident):
        return s.query(db.Proposition).filter_by(kind=kind, **{subject_col: ident.id})

    cvs, u_cvs = mint_party('CVS Pharmacy.')
    mercy, u_mercy = mint_party('Mercy Hospital.')
    aetna, u_aetna = mint_party('Aetna, our insurer.')
    hsa, u_hsa = mint_party('The HSA administrator.')
    bank, u_bank = mint_party('Our bank.')
    mother, u_mother = mint_party("Rob's mother.")

    print('\n1. The registry entry - exactly as authorised\n')
    check('payment_in_respect_of is ruled exactly as authorised: payment subject, expense object, not symmetric, reading never establishes, relational_knowing True, no knowing_relation',
          db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF] == {'subject': ('subject_payment_id',), 'object': ('object_expense_id',),
                                                      'symmetric': False, 'reading_establishes': False, 'relational_knowing': True})
    check('D16 / D13: no source-word kind (paid_for, funds, reimburses, covers, attached, allocated), no inverse kind, no generic payment-expense relation exists beside it',
          not any(k in db.RULED_KINDS for k in SOURCE_KINDS + INVERSE_KINDS))
    check('no kind with an expense subject and a payment object exists - the slots swapped would be a second relation, not this one read backwards',
          not any('subject_expense_id' in r['subject'] and 'object_payment_id' in r['object'] for r in db.RULED_KINDS.values()))
    check("D' is not bundled: toward stays a stand-in, unruled",
          'toward' not in db.RULED_KINDS and 'payment_toward' not in db.RULED_KINDS)   # D' ruled its own kind; toward rejected

    print("\n2. D1 - Ex8: the CVS charge was Kim's prescription; no obligation anywhere\n")
    X, u_X = incur("Kim's prescription at CVS on 3/2.", '2026-03-03T09:00:00')
    p1, u_p1 = pay('I paid CVS $24.99 on 3/2 - that was the prescription.', '2026-03-03T09:01:00')
    about_p('amount', p1, '$24.99', utterance=u_p1)
    role_p('paid_by', household, p1, u_p1)
    role_p('paid_to', cvs, p1, u_p1)
    n_obl = s.query(db.Obligation).count()
    e_d1, r_d1 = in_respect_of(p1, X, utterance=u_p1)
    check('D1: the relation is a claim with two established participants of different types - the payment the subject, the expense the object',
          r_d1.subject_payment_id == p1.id and r_d1.object_expense_id == X.id
          and r_d1.subject_state == db.PARTICIPANT_ESTABLISHED and r_d1.object_state == db.PARTICIPANT_ESTABLISHED)
    check('D1: no obligation was minted or implied - the card purchase has none and needs none; the relation stands without a chain',
          s.query(db.Obligation).count() == n_obl == 0)
    check('D1: neither anchor grew; X acquires no paid status; the amount is p1\'s own claim',
          {c.name for c in db.Payment.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and {c.name for c in db.Expense.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and not any(hasattr(db.Expense, w) for w in STATUS_WORDS)
          and stances('amount', 'subject_payment_id', p1).count() == 1)

    print('\n3. D2 - the bank line: mints neither, proves no purpose; the matcher\'s pairing is a candidate\n')
    feed = held('h-feed', '2026-03-31', bank, u_bank)
    r_feed = read(feed)
    n_pay, n_exp, n_rel = s.query(db.Payment).count(), s.query(db.Expense).count(), rel().count()
    line = prop('movement', object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=bank.id, content='CVS PHARMACY 24.99 | Medical', as_of='2026-03-02')
    evidence(line, reading=r_feed)
    check('D2: the feed line is the bank\'s proposition about a movement with candidates - it minted no payment, no expense, and asserted no relation; "Medical" proves no purpose',
          s.query(db.Payment).count() == n_pay and s.query(db.Expense).count() == n_exp and rel().count() == n_rel)
    evidence(prop(db.PROPOSITION_CONCERNS, subject_proposition_id=line.id, object_expense_id=X.id), utterance=utter("That's the prescription line.", '2026-03-06T09:00:00'))
    check('D2: the line concerning X (Tx8) is about-ness, not this relation',
          rel().count() == n_rel)
    c_line = prop(db.PAYMENT_IN_RESPECT_OF, subject_payment_id=p1.id, object_expense_id=X.id, content='matcher: merchant + amount + date')
    e_cand = evidence(c_line, reading=r_feed)
    check("D2: the matcher's pairing is a reading-sourced candidate - no party behind it; it establishes nothing and is not knowing",
          e_cand.utterance_id is None and e_cand.reading_id == r_feed.id
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c_line.id).count() == 1
          and not db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF]['reading_establishes']
          and db.derived_strength(s, e_cand, KNOWING) == db.STRENGTH_UNDETERMINED)

    print('\n4. D3 / D4 / D17 - cardinality is not allocation\n')
    ER, u_ER = incur('We took Kim to the ER on Feb 14.', '2026-02-15T09:00:00')
    q1, u_q1 = pay('$30 copay at the desk, cash.', '2026-02-15T09:01:00')
    q2, u_q2 = pay('I paid Mercy $382 on the bill in April.', '2026-04-10T09:00:00')
    q3, u_q3 = pay('And another $40 they said I still owed.', '2026-05-02T09:00:00')
    u_three = utter('All three were for the ER visit.', '2026-05-02T09:05:00')
    for q in (q1, q2, q3):
        in_respect_of(q, ER, utterance=u_three)
    check('D3: three payments in respect of one expense - three claims; no uniqueness anywhere',
          rel(x=ER).count() == 3)
    check('D3: cardinality is not allocation - no sum, no "fully paid", no duplicate / replacement / counteraction derived among the three',
          s.query(db.Proposition).filter(db.Proposition.kind.in_((db.PAYMENT_CORRESPONDS, db.PAYMENT_COUNTERACTS))).count() == 0
          and not any(hasattr(db, n) for n in ('total_paid', 'paid_so_far', 'sum_of_payments', 'is_paid', 'fully_paid'))
          and not any(hasattr(db.Expense, w) for w in STATUS_WORDS))
    X2, u_X2 = incur("Rob's prescription, same trip.", '2026-03-03T09:02:00')
    swipe, u_swipe = pay('One CVS swipe, $61.48, on 3/9 - both prescriptions.', '2026-03-10T09:00:00')
    about_p('amount', swipe, '$61.48', utterance=u_swipe)
    in_respect_of(swipe, X, utterance=u_swipe)
    in_respect_of(swipe, X2, utterance=u_swipe)
    check('D4: one payment in respect of two expenses - two claims; the relation says nothing about how the payment relates to each',
          rel(p=swipe).count() == 2)
    check('D4: no allocation, split, percentage, order of satisfaction or remainder - no such column on the proposition, no helper; several assertions are never an implicit allocation',
          not any(w in c.name for w in ('share', 'portion', 'percent', 'allocation', 'priority', 'amount', 'remainder', 'order') for c in db.Proposition.__table__.columns)
          and not any(hasattr(db, n) for n in ('allocate', 'allocation_of', 'split_of', 'share_of', 'apportion', 'remainder_of', 'unallocated', 'satisfaction_order')))
    n_exp = s.query(db.Expense).count()
    basket, u_basket = pay('CVS $61.48 on 3/16 - the prescription and some shampoo.', '2026-03-17T09:00:00')
    in_respect_of(basket, X, utterance=u_basket, content='the prescription part')
    check('D17: the mixed basket - the relation is asserted for the prescription only; no expense is manufactured for the shampoo and nothing computes an unallocated remainder',
          s.query(db.Expense).count() == n_exp and rel(p=basket).count() == 1
          and not any(hasattr(db, n) for n in ('unallocated', 'remainder_of', 'rest_of')))

    print('\n5. D5 / D6 - a payment with no expense; an expense with no payment\n')
    n_exp = s.query(db.Expense).count()
    plumber, u_pl = pay('I paid the plumber $200 in cash.', '2026-01-20T09:00:00')
    gift, u_gift = pay('I gave my brother $500.', '2026-01-25T09:00:00')
    check('D5: a payment with no expense - nothing manufactures an incurrence for it; no relation; "every payment is for something" is false in the ontology',
          s.query(db.Expense).count() == n_exp and rel(p=plumber).count() == 0 and rel(p=gift).count() == 0)
    W, u_W = incur("Kim's wellness visit on 4/2 - fully covered.", '2026-04-03T09:00:00')
    about_x('patient_responsibility', W, '$0', utterance=utter('Aetna paid all of it.', '2026-04-20T09:00:00'), as_of='2026-04-20')
    n_pay = s.query(db.Payment).count()
    check('D6: an expense with no payment - no relation, no payment manufactured, and nothing derives "unpaid" from an absent relation',
          rel(x=W).count() == 0 and s.query(db.Payment).count() == n_pay
          and not any(hasattr(db, n) for n in ('is_unpaid', 'unpaid_expenses', 'unpaid', 'determination', 'user_paid_cash')))

    print('\n6. D7 / D14 - disputed attribution; retraction\n')
    brace, u_brace = incur('The knee brace from CVS on 5/12.', '2026-05-12T09:00:00')
    p84, u_p84 = pay('The $84 at CVS on 5/12.', '2026-05-13T09:00:00')
    u_rob84 = utter('The $84 was for the cushion - I mean the prescription.', '2026-05-13T09:05:00')
    in_respect_of(p84, X, utterance=u_rob84)
    u_kim84 = db.Utterance(origin_party_id=kim_party.id, asserted_at='2026-05-13T09:10:00', content='No - the $84 was the brace.')
    s.add(u_kim84)
    s.commit()
    in_respect_of(p84, brace, utterance=u_kim84)
    check('D7: Rob says the $84 was for X, Kim says the brace - two claims stand, contested; nothing chooses; no current attribution',
          rel(p=p84).count() == 2 and not any(hasattr(db, n) for n in ('current_attribution', 'attribution_of', 'resolve_in_respect_of')))
    n_rel, n_pay, n_exp = rel().count(), s.query(db.Payment).count(), s.query(db.Expense).count()
    r = prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_rob84.id)
    evidence(r, utterance=utter("Kim's right - it was the brace.", '2026-05-14T09:00:00'))
    check('D14: retracting the utterance behind a relation claim leaves p, X, the brace and every relation row; nothing appears in the other direction',
          rel().count() == n_rel and s.query(db.Payment).count() == n_pay and s.query(db.Expense).count() == n_exp)

    print("\n7. D8 - the chain through an obligation: no composition either way; discharge untouched\n")
    O, u_O = owe("That's the ER visit - I owe Mercy for it.", '2026-03-06T09:00:00')
    evidence(prop(db.OBLIGATION_IN_RESPECT_OF, subject_obligation_id=O.id, object_expense_id=ER.id), utterance=u_O)
    pb, u_pb = pay('I paid Mercy $382 toward the bill.', '2026-04-10T09:01:00')
    evidence(prop(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_payment_id=pb.id, object_obligation_id=O.id), utterance=u_pb)   # ruled in pass D' (was the toward stand-in)
    check('D8: pb in respect of O + O in respect of ER does NOT derive pb in respect of ER',
          rel(p=pb, x=ER).count() == 0)
    n_toward = s.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION).count()
    in_respect_of(q2, ER, utterance=utter('The $382 was for the ER visit.', '2026-04-10T09:02:00'))
    check('D8: q2 in respect of ER + O in respect of ER does NOT derive q2 in respect of O; the household asserts it, or does not',
          s.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_payment_id=q2.id).count() == 0
          and s.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION).count() == n_toward)
    check('D8: discharge of O is untouched - no acknowledgment claim appeared, no discharge helper exists',
          s.query(db.Proposition).filter_by(kind='acknowledged', object_payment_id=pb.id).count() == 0
          and not any(hasattr(db, n) for n in ('is_discharged', 'discharged_by', 'discharge_of', 'remaining_on')))

    print('\n8. D9 / D18 / D19 - three independent reasons against "funds the expense"\n')
    reimb, u_reimb = pay('The HSA reimbursed me $412 on 5/20 - for the ER visit.', '2026-05-21T09:00:00')
    role_p('paid_by', hsa, reimb, u_reimb)
    role_p('paid_to', household, reimb, u_reimb)
    e_d9, r_d9 = in_respect_of(reimb, ER, utterance=u_reimb, content='reimbursement')
    check('D9: reimbursement - money flows TO the household; the same kind; "reimbursement" is content; the relation carries no direction of money',
          r_d9.kind == db.PAYMENT_IN_RESPECT_OF and 'reimbursement' in r_d9.content
          and s.query(db.Proposition).filter_by(kind='paid_to', object_payment_id=reimb.id).one().subject_party_id == household.id
          and not any(hasattr(db, n) for n in ('direction_of', 'money_direction', 'net_cost', 'net_cost_of', 'is_reimbursed'))
          and not any(hasattr(db.Expense, w) for w in STATUS_WORDS))
    eob = held('h-eob', '2026-03-10', aetna, u_aetna)
    r_eob = read(eob, 'pdf-parser/5')
    n_pay, n_rel = s.query(db.Payment).count(), rel().count()
    about_x('plan_paid', ER, '$568', reading=r_eob, as_of='2026-03-10')
    check("D18: the EOB's plan-paid $568 is the insurer's stance on X - it minted no payment and asserted no relation",
          s.query(db.Payment).count() == n_pay and rel().count() == n_rel)
    ins, u_ins = pay('Aetna paid Mercy $568 for the ER visit.', '2026-03-12T09:00:00')
    role_p('paid_by', aetna, ins, u_ins)
    role_p('paid_to', mercy, ins, u_ins)
    in_respect_of(ins, ER, utterance=u_ins)
    check('D18: a payment with NO household party as payer or payee stands in the relation - no household participant is required anywhere on p',
          rel(p=ins, x=ER).count() == 1
          and {s.query(db.Proposition).filter_by(kind=k, object_payment_id=ins.id).one().subject_party_id for k in ('paid_by', 'paid_to')} == {aetna.id, mercy.id})
    mom, u_mom = pay("My mother paid CVS $24.99 for Kim's prescription.", '2026-03-04T09:00:00')
    role_p('paid_by', mother, mom, u_mom)
    role_x('incurred_by', kim_party, X, u_X)
    in_respect_of(mom, X, utterance=u_mom)
    check('D19: the payer is a third party and the incurrer is Kim - no payer/incurrer mirroring is required; no helper checks it',
          rel(p=mom, x=X).count() == 1
          and s.query(db.Proposition).filter_by(kind='paid_by', object_payment_id=mom.id).one().subject_party_id == mother.id
          and s.query(db.Proposition).filter_by(kind='incurred_by', object_expense_id=X.id).one().subject_party_id == kim_party.id
          and not any(hasattr(db, n) for n in ('payer_is_incurrer', 'requires_mirroring', 'payer_matches_incurrer')))

    print('\n9. D10 / D11 / D12 - amounts, the 1.x row, the determinations: nothing on the edge\n')
    about_x('patient_responsibility', ER, '$412', reading=r_eob, as_of='2026-03-10')
    about_x('billed', ER, '$1,300', reading=r_eob, as_of='2026-03-10')
    about_p('amount', q1, '$30', utterance=u_q1)
    check('D10: copay $30 on q1, PR $412 and billed $1,300 on ER stand beside the relation; the relation carries no amount and reconciles nothing',
          stances('amount', 'subject_payment_id', q1).count() == 1 and stances('patient_responsibility', 'subject_expense_id', ER).count() == 1
          and 'amount' not in {c.name for c in db.Proposition.__table__.columns}
          and not any(hasattr(db, n) for n in ('reconcile', 'reconciled_amount', 'corresponding_amount', 'residual_of', 'remaining_on', 'amount_of')))
    check('D11: the 1.x allocation row is not inherited onto the edge - no funder / mode / cleared / attached / user_confirmed / duplicate_of column on the proposition, and the 1.x table is untouched',
          not any(w in c.name for w in ('funder', 'mode', 'cleared', 'attached', 'confirmed', 'duplicate', 'source') for c in db.Proposition.__table__.columns)
          and 'expense_funding_allocations' in db.Base.metadata.tables
          and not any(hasattr(db, n) for n in ('decompose_allocation', 'allocation_to_payment')))
    about_p(db.CLEARED, q2, 'cleared 4/11', reading=r_feed, as_of='2026-04-11')
    check('D11: what the row fused is now separate claims - cleared is the bank\'s claim on the payment, not a station on the relation',
          stances(db.CLEARED, 'subject_payment_id', q2).count() == 1)
    check('D12: the determinations are neither this kind nor derived from it - no user_paid_cash / unpaid / pending_claim kind or helper',
          not any(k in db.RULED_KINDS for k in ('user_paid_cash', 'unpaid', 'pending_claim', 'provider_adjustment'))
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(('user_paid_cash', 'unpaid', 'pending_claim', 'provider_adjustment'))).count() == 0
          and not any(hasattr(db, n) for n in ('determination', 'determine', 'user_paid_cash', 'determinations_of')))

    print('\n10. D15 - composition with payment_counteracts refused both ways\n')
    refund, u_ref = pay('CVS refunded the $24.99 on 3/20.', '2026-03-21T09:00:00')
    evidence(prop(db.PAYMENT_COUNTERACTS, subject_payment_id=refund.id, object_payment_id=p1.id), utterance=u_ref)
    check('D15: refund counteracts p1 + p1 in respect of X does NOT derive refund in respect of X',
          rel(p=refund).count() == 0)
    refund2, u_ref2 = pay('CVS refunded the $61.48 swipe on 3/22.', '2026-03-23T09:00:00')
    in_respect_of(refund2, X2, utterance=utter("That refund was for Rob's prescription.", '2026-03-23T09:05:00'))
    n_rel = rel().count()
    evidence(prop(db.PAYMENT_COUNTERACTS, subject_payment_id=refund2.id, object_payment_id=basket.id), utterance=u_ref2)
    check('D15: refund2 in respect of X2 + refund2 counteracts basket does NOT derive basket in respect of X2 - the counteracted payment inherits nothing either',
          rel(p=basket, x=X2).count() == 0 and rel().count() == n_rel
          and not any(hasattr(db.Expense, w) for w in ('refunded', 'reversed')) and not any(hasattr(db, n) for n in ('net_of', 'net_paid')))

    print('\n11. D13 / D20 - direction fixed by type; the receipt concerns both; CVS may assert\n')
    check('D13: there is no reverse claim - a proposition of this kind with the slots swapped is refused',
          _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_expense_id=X.id, object_payment_id=p1.id)))
    receipt = held('h-receipt', '2026-03-02', cvs, u_cvs)
    n_rel = rel().count()
    concerns(receipt, utter('The CVS receipt.', '2026-03-03T09:03:00'), p=p1)
    concerns(receipt, utter('The CVS receipt - for the prescription.', '2026-03-03T09:04:00'), x=X)
    check('D20: the receipt concerns p1 and concerns X - two about-ness claims; no relation row appeared from the document concerning both',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=receipt.id).count() == 2 and rel().count() == n_rel)
    n_pay, n_exp = s.query(db.Payment).count(), s.query(db.Expense).count()
    u_cvs_says = utter('Rx #4471 - $24.99 - paid 3/2.', '2026-03-02T18:00:00', origin=cvs)
    e_d20, r_d20 = in_respect_of(p1, X, utterance=u_cvs_says, content='Rx #4471')
    check('D20: CVS (an institution) may assert the relation - a claim with its own evidence; both endpoints were already established and the assertion minted neither and added no payee, amount or correctness',
          e_d20.utterance.origin_party_id == cvs.id and 'Rx' in r_d20.content
          and s.query(db.Payment).count() == n_pay and s.query(db.Expense).count() == n_exp
          and s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_cvs_says.id).count() == 1)
    check('knowing for the relation is undetermined for every asserter - ruled True with no designated relation; no role of p or X is forced',
          db.derived_strength(s, e_d20, KNOWING) == db.STRENGTH_UNDETERMINED
          and db.derived_strength(s, e_d1, KNOWING) == db.STRENGTH_UNDETERMINED
          and db.derived_strength(s, e_d9, KNOWING) == db.STRENGTH_UNDETERMINED
          and 'knowing_relation' not in db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF])

    print('\n12. D21 (PERMANENT) - no temporal precedence\n')
    dep, u_dep = pay('I paid Mercy a $500 deposit on 4/2 for the surgery next month.', '2026-04-02T09:00:00')
    K, u_K = incur("Kim's knee surgery on May 12.", '2026-05-13T09:00:00')
    e_d21, r_d21 = in_respect_of(dep, K, utterance=utter('The deposit was for the knee surgery.', '2026-05-13T09:05:00'), as_of='2026-04-02')
    check('D21 (PERMANENT): the payment was minted before the expense - the relation is accepted; created_at on either anchor is not consulted; no order guard exists',
          dep.created_at <= K.created_at and rel(p=dep, x=K).count() == 1
          and not any(hasattr(db, n) for n in ('expense_precedes', 'payment_precedes', 'order_of', 'precedes', 'temporal_order', 'validate_order')))
    late, u_late = pay('Paid the last of the 2026 ER bill in January 2027.', '2027-01-15T09:00:00')
    in_respect_of(late, ER, utterance=u_late)
    check('D21: a payment long after the expense - the same relation; no timing semantics',
          rel(p=late, x=ER).count() == 1 and not any(hasattr(db, n) for n in ('late', 'is_late', 'days_after')))

    print('\n13. D22 - the semantic floor: "in respect of" != "made for"\n')
    pf, u_pf = pay("I made this payment in respect of Kim's prescription - $24.99 on 6/1.", '2026-06-01T09:00:00')
    e_d22, r_d22 = in_respect_of(pf, X, utterance=u_pf)
    check('D22: the sentence establishes exactly the relation - no payer, payee, incurrer, funding, cause, discharge, amount-correspondence or only-payment claim appeared from it',
          rel(p=pf, x=X).count() == 1 and r_d22.content is None
          and s.query(db.Proposition).filter(db.Proposition.object_payment_id == pf.id).count() == 0
          and s.query(db.Proposition).filter(db.Proposition.subject_payment_id == pf.id, db.Proposition.kind != db.PAYMENT_IN_RESPECT_OF).count() == 0
          and not any(w in c.name for w in ('purpose', 'cause', 'funding', 'legal', 'effect', 'only', 'sole', 'primary') for c in db.Proposition.__table__.columns)
          and not any(hasattr(db, n) for n in ('purpose_of', 'funds', 'funded_by', 'funder_of', 'is_only_payment', 'legal_effect')))
    check('D22: X acquires nothing from the relation - no paid / reimbursed / covered / funded claim on X and no such attribute',
          s.query(db.Proposition).filter(db.Proposition.subject_expense_id == X.id, db.Proposition.kind.in_(STATUS_WORDS)).count() == 0
          and not any(hasattr(db.Expense, w) for w in STATUS_WORDS))

    print('\n14. Structure - both participants established; cross-type refused; references immutable; absences; audits\n')
    check('both participants must be established identities of the right type - candidates, a party subject, an obligation object, a payment object are refused',
          _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                     subject_payment_id=p1.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_party_id=cvs.id, object_expense_id=X.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_payment_id=p1.id, object_obligation_id=O.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_payment_id=p1.id, object_payment_id=refund.id)))
    check("the relation's references are immutable - re-pointing a participant is refused; correction is retraction + a new claim",
          (lambda: (r_d1.object_expense_id, setattr(r_d1, 'object_expense_id', X2.id), _refused(s, r_d1))[2])()
          and s.get(db.Proposition, r_d1.id).object_expense_id == X.id)
    check('traversal: from p1 a query enumerates every asserted expense with its asserter (X by Rob, X by CVS, the candidate separately); from X the same query runs the other way; no accessor selects',
          {(pr.object_expense_id, e.utterance.origin_party_id if e.utterance_id else None)
           for pr in rel(p=p1) for e in s.query(db.EvidentiaryRelationship).filter_by(proposition_id=pr.id)}
          >= {(X.id, household.id), (X.id, cvs.id), (X.id, None)}
          and {pr.subject_payment_id for pr in rel(x=X)} >= {p1.id, swipe.id, basket.id, mom.id, pf.id}
          and not any(hasattr(db, n) for n in CONSUMER_NAMES))
    check('no schema: anchors as their slices left them; both slots pre-existed; no relation table; no generic relation base, resolver, inverse, allocation, reconciliation or funding helper',
          'subject_payment_id' in db.Proposition.SUBJECT_SLOTS and 'object_expense_id' in db.Proposition.OBJECT_SLOTS
          and not any('relation' in t for t in db.Base.metadata.tables)
          and not any(hasattr(db, n) for n in CONSUMER_NAMES))
    check('every audit is empty',
          not db.payments_without_minting_utterance(s) and not db.expenses_without_minting_utterance(s)
          and not db.obligations_without_minting_utterance(s) and not db.parties_without_one_anchor(s))

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
