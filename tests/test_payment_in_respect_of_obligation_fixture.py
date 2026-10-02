"""payment_in_respect_of_obligation - the executable trace of `gw 2.0/RELATION_SEMANTICS.md` pass D' (ruled 2026-09-15).

`payment_in_respect_of_obligation(p, O)` means exactly: the asserting party holds that the subject payment
was in respect of the object obligation - and nothing above that floor. THE D' INVARIANT: it is NOT
derivable from payment_in_respect_of(p, X) + obligation_in_respect_of(O, X), nor from any composition whose
only shared operand is X, nor from E's acknowledgment. Convergence is neither a party nor a reading.
`toward` is rejected as the kind. The household's assertion of this relation is H2's "attached" station.

Every convergence case proves NON-SELECTION, not only non-existence: zero relation row, zero selected
obligation, zero resolver choice - the substrate has no authority to choose an obligation for a payment.

What this slice can and cannot exercise
---------------------------------------
    D'1  Pm1: the mortgage - a payment in respect of an obligation with NO expense to converge on   EXERCISED
    D'2  convergence, one obligation: p->X + O->X derives nothing; no selection                    EXERCISED
    D'3  convergence, TWO obligations: neither p->O1 nor p->O2; nothing selects            EXERCISED - MANDATORY
    D'4  the deposit before the obligation; E's credit is evidence, not the relation     EXERCISED - PERMANENT
    D'5  THE AETNA COUNTEREXAMPLE: the derived relation would be FALSE                  EXERCISED - PERMANENT
    D'6  reimbursement and desk copay: convergence with an unwanted result                         EXERCISED
    D'7  Chase's statement line: a candidate; the acknowledgment stand-in derives nothing            EXERCISED
    D'8  S3 / D'9 S6 / D'10 E rejects: the relation stands; no discharge, no remaining               EXERCISED
    D'11 the escrow refund: money the other way, the same kind; toward would misdescribe it          EXERCISED
    D'12 one cheque two plans; twelve autopays one mortgage - cardinality is not allocation          EXERCISED
    D'13 retraction; D'14 dispute                                                                   EXERCISED
    D'15 composition with obligation_replaces and payment_counteracts refused                       EXERCISED
    D'16 toward / against / applied / attached / paid down are not kinds; toward never became one   EXERCISED (absence)
    D'17 the semantic floor                                                                         EXERCISED
    D'18 direction fixed by type; the slots swapped refused; no inverse kind; no accessor            EXERCISED
    the toward stand-in retired INTO this kind in every fixture; no unrelated use reclassified      s105 (static scan)
    acknowledgment's own shape (participant vs content), discharge / remaining (item 7), G           NOT BUILT

Run:  python tests/test_payment_in_respect_of_obligation_fixture.py
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


# Anything that would let the substrate CHOOSE an obligation for a payment - the dangerous implementation
# is not insert(relation) but candidate = find_obligation_for_payment(...) followed by a later derivation.
SELECTOR_NAMES = ('find_obligation_for_payment', 'selected_obligation', 'select_obligation', 'obligation_of_payment',
                  'obligations_of_payment', 'resolve_payment_obligation', 'obligation_for', 'obligation_for_payment',
                  'payment_obligation', 'match_obligation', 'infer_obligation', 'candidate_obligation',
                  'obligation_candidates_for', 'derive_toward', 'converge', 'convergence', 'shared_expense_join',
                  'obligation_via_expense', 'obligations_via_expense')
CONSUMER_NAMES = SELECTOR_NAMES + (
    'is_discharged', 'discharged_by', 'discharge_of', 'applied_to', 'apply_payment', 'credit_payment', 'remaining_on',
    'remaining_after', 'paid_down', 'balance_after', 'allocate', 'allocation_of', 'split_of', 'inverse_of',
    'relations_of', 'Relation', 'RelationBase', 'resolve_relation', 'relation_resolver', 'payment_precedes',
    'obligation_precedes', 'order_of', 'toward', 'payment_toward')
SOURCE_KINDS = ('toward', 'payment_toward', 'against', 'payment_against', 'applied', 'applied_to', 'payment_applied',
                'attached', 'payment_attached', 'paid_down', 'payment_on', 'payment_for_obligation',
                'payment_obligation_relation', 'payment_reduces', 'payment_credits')
INVERSE_KINDS = ('obligation_paid_by', 'obligation_receives', 'obligation_has_payment', 'obligation_in_respect_of_payment',
                 'obligation_payment', 'obligation_credited_by')
ACCESSOR_ATTRS = ('obligation', 'obligations', 'toward', 'applied_to', 'selected_obligation')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_piroo_')
    eng = create_engine(f'sqlite:///{Path(d) / "t.db"}')

    @event.listens_for(eng, 'connect')
    def _fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA synchronous=OFF')          # throwaway DB: no fsync per commit
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
               'acknowledged': {'institution'}, 'credited': {'institution'}, 'returned': {'institution'},
               'paid_by': {'person', 'institution'}, 'paid_to': {'person', 'institution'}, 'cleared': {'institution'},
               'entitled_party': {'person', 'institution'}}

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

    def pay(text, when):
        u = utter(text, when)
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

    def role_p(kind, party, p, utterance, as_of=None, content=None):
        # a stand-in claim with subject a party and object a payment: paid_by / paid_to / acknowledged / credited
        pr = prop(kind, subject_party_id=party.id, object_payment_id=p.id, as_of=as_of, content=content)
        return evidence(pr, utterance=utterance), pr

    def role_o(kind, party, o, as_of, utterance):
        pr = prop(kind, subject_party_id=party.id, object_obligation_id=o.id, as_of=as_of)
        return evidence(pr, utterance=utterance), pr

    def held(h, as_of, origin_party, origin_utt):
        a = db.Artefact(held=True, content_hash=h, as_of=as_of)
        s.add(a)
        s.commit()
        evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=a.id, object_party_id=origin_party.id), utterance=origin_utt)
        return a

    def read(a, process='pdf-parser/5'):
        r = db.Reading(artefact_id=a.id, reader_process=process, read_at=datetime(2026, 3, 12))
        s.add(r)
        s.commit()
        return r

    def p_x(p, x, utterance):
        return evidence(prop(db.PAYMENT_IN_RESPECT_OF, subject_payment_id=p.id, object_expense_id=x.id), utterance=utterance)

    def o_x(o, x, utterance):
        return evidence(prop(db.OBLIGATION_IN_RESPECT_OF, subject_obligation_id=o.id, object_expense_id=x.id), utterance=utterance)

    def p_o(p, o, utterance=None, reading=None, content=None, as_of=None):
        pr = prop(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_payment_id=p.id, object_obligation_id=o.id, content=content, as_of=as_of)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def rel(p=None, o=None):
        q = s.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION)
        if p is not None:
            q = q.filter_by(subject_payment_id=p.id)
        if o is not None:
            q = q.filter_by(object_obligation_id=o.id)
        return q

    def nothing_selected():
        # NON-SELECTION: zero selector / resolver / accessor anywhere - the substrate has no authority to choose
        return (not any(hasattr(db, n) for n in SELECTOR_NAMES)
                and not any(hasattr(db.Payment, a) for a in ACCESSOR_ATTRS)
                and not any(hasattr(db.Obligation, a) for a in ('payments', 'payment', 'paid_by_payment', 'selected_payment')))

    chase, u_chase = mint_party('Chase, my mortgage lender.')
    mercy, u_mercy = mint_party('Mercy Hospital.')
    radiology, u_rad = mint_party('The radiology group.')
    aetna, u_aetna = mint_party('Aetna, our insurer.')
    hsa, u_hsa = mint_party('The HSA administrator.')
    s3, u_s3 = mint_party('The servicer that wrote to us (S3).')

    print('\n1. The registry entry - exactly as authorised; toward never became a kind\n')
    check('payment_in_respect_of_obligation is ruled exactly as authorised: payment subject, obligation object, not symmetric, reading never establishes, relational_knowing True, no knowing_relation',
          db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF_OBLIGATION] == {'subject': ('subject_payment_id',), 'object': ('object_obligation_id',),
                                                                 'symmetric': False, 'reading_establishes': False, 'relational_knowing': True})
    check("D'16: toward is REJECTED as the kind and never became one; no source-word, inverse or generic payment-obligation kind exists",
          not any(k in db.RULED_KINDS for k in SOURCE_KINDS + INVERSE_KINDS))
    check('no kind with an obligation subject and a payment object exists - the slots swapped would be a second relation',
          not any('subject_obligation_id' in r['subject'] and 'object_payment_id' in r['object'] for r in db.RULED_KINDS.values()))
    check('JURISDICTION: payment_in_respect_of still takes an expense object only - the typed-object question is G\'s, not decided by this build',
          db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF]['object'] == ('object_expense_id',))
    check('NON-SELECTION baseline: no selector, resolver, convergence join or payment.obligation accessor exists',
          nothing_selected() and not any(hasattr(db, n) for n in CONSUMER_NAMES))

    print("\n2. D'1 - Pm1: the mortgage - a relation with no expense to converge on\n")
    o1, u_o1 = owe('I have a mortgage with Chase - account ending 4471.', '2019-06-01T09:00:00')
    role_o('entitled_party', chase, o1, '2019-06-01', u_o1)
    n_exp = s.query(db.Expense).count()
    p1, u_p1 = pay('I paid Chase $1,412 on March 3 for the mortgage.', '2026-03-03T09:00:00')
    about_p('amount', p1, '$1,412', utterance=u_p1)
    role_p('paid_to', chase, p1, u_p1)
    e_d1, r_d1 = p_o(p1, o1, utterance=u_p1)
    check("D'1: the relation is a claim with two established participants - the payment the subject, the obligation the object - asserted by Rob",
          r_d1.subject_payment_id == p1.id and r_d1.object_obligation_id == o1.id
          and r_d1.subject_state == db.PARTICIPANT_ESTABLISHED and r_d1.object_state == db.PARTICIPANT_ESTABLISHED)
    check("D'1: no expense exists and none was manufactured - the relation is needed exactly where convergence is impossible",
          s.query(db.Expense).count() == n_exp == 0 and s.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF).count() == 0)
    check("D'1: the household's assertion is H2's 'attached' station and nothing more - no discharge, no acknowledgment, no remaining moved",
          s.query(db.Proposition).filter_by(kind='acknowledged', object_payment_id=p1.id).count() == 0
          and not any(hasattr(db, n) for n in ('is_discharged', 'discharged_by', 'remaining_on', 'paid_down', 'applied_to')))

    print("\n3. D'2 - convergence with one obligation: p->X + O->X derives nothing and selects nothing\n")
    X, u_X = incur('We took Kim to the ER on Feb 14.', '2026-02-15T09:00:00')
    O, u_O = owe("That's the ER visit - I owe Mercy for it.", '2026-03-06T09:00:00')
    role_o('entitled_party', mercy, O, '2026-03-06', u_O)
    o_x(O, X, u_O)
    q2, u_q2 = pay('I paid Mercy $382 in April for the ER visit.', '2026-04-10T09:00:00')
    p_x(q2, X, u_q2)
    check("D'2: p->X and O->X both stand; p->O does NOT exist - the two arrows establish a shared referent, not a third arrow",
          s.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF, subject_payment_id=q2.id, object_expense_id=X.id).count() == 1
          and s.query(db.Proposition).filter_by(kind=db.OBLIGATION_IN_RESPECT_OF, subject_obligation_id=O.id, object_expense_id=X.id).count() == 1
          and rel(p=q2).count() == 0)
    check("D'2: NON-SELECTION - zero relation, zero selected obligation, zero resolver choice",
          rel(p=q2).count() == 0 and nothing_selected())
    e_d2, r_d2 = p_o(q2, O, utterance=utter('And yes - that $382 was toward the bill.', '2026-04-10T09:05:00'), content='toward the bill')
    check("D'2: the relation exists only because Rob asserted it - a third claim of a third kind; 'toward' is his content",
          rel(p=q2, o=O).count() == 1 and 'toward' in r_d2.content)

    print("\n4. D'3 (MANDATORY) - convergence with TWO obligations: nothing can even name its result\n")
    O2, u_O2 = owe("The radiology group's bill for the ER visit.", '2026-03-20T09:00:00')
    role_o('entitled_party', radiology, O2, '2026-03-20', u_O2)
    o_x(O2, X, u_O2)
    q4, u_q4 = pay('I paid $120 on 5/1 for the ER visit.', '2026-05-01T09:00:00')
    p_x(q4, X, u_q4)
    check("D'3: X has two obligations in respect of it (O, O2) and a payment in respect of it (q4) - p->O absent AND p->O2 absent",
          s.query(db.Proposition).filter_by(kind=db.OBLIGATION_IN_RESPECT_OF, object_expense_id=X.id).count() == 2
          and rel(p=q4, o=O).count() == 0 and rel(p=q4, o=O2).count() == 0 and rel(p=q4).count() == 0)
    check("D'3: NON-SELECTION - the substrate has no authority to choose one: no selector, no candidate list, no accessor; not 'didn't happen to choose wrong' but 'cannot choose'",
          nothing_selected() and not any(hasattr(db, n) for n in ('obligation_candidates_for', 'candidate_obligation', 'select_obligation')))

    print("\n5. D'4 (PERMANENT) - the deposit before the obligation; E's credit is evidence, not the relation\n")
    dep, u_dep = pay('I paid Mercy a $500 deposit on 4/2 for the surgery.', '2026-04-02T09:00:00')
    K, u_K = incur("Kim's knee surgery on May 12.", '2026-05-13T09:00:00')
    p_x(dep, K, u_K)
    OK, u_OK = owe("Mercy's balance for the knee surgery.", '2026-06-05T09:00:00')
    o_x(OK, K, u_OK)
    stmt = held('h-mercy-june', '2026-06-05', mercy, u_mercy)
    r_stmt = read(stmt)
    role_p('credited', mercy, dep, utter("Mercy's June statement shows the deposit credited.", '2026-06-06T09:00:00'), as_of='2026-06-05', content='deposit credited $500')
    # The scenario is a payment minted BEFORE the obligation. Two mints a moment apart can share one clock tick
    # (Windows ticks ~15 ms; with the fixture DBs' synchronous=OFF the mints got fast enough to, 2026-10-01), and a
    # strict '<' then failed on a race, not on the substrate. The order the scenario needs is made real here.
    if OK.created_at <= dep.created_at:
        from datetime import timedelta as _td
        OK.created_at = dep.created_at + _td(milliseconds=1)
        s.flush()
    check("D'4 (PERMANENT): the payment precedes the obligation; p->X, O->X and E's credit all stand; p->O is derived from none of them - not from order, not from convergence, not from the credit",
          dep.created_at < OK.created_at and rel(p=dep).count() == 0 and nothing_selected()
          and s.query(db.Proposition).filter_by(kind='credited', object_payment_id=dep.id).count() == 1)
    e_d4, r_d4 = p_o(dep, OK, utterance=utter('The deposit was toward the surgery balance.', '2026-06-06T09:05:00'), as_of='2026-04-02')
    check("D'4 (PERMANENT): asserted, the relation is accepted with the payment minted before the obligation - no order guard; a relation's direction and participant types establish no temporal precedence",
          rel(p=dep, o=OK).count() == 1 and r_d4.as_of == '2026-04-02'
          and not any(hasattr(db, n) for n in ('payment_precedes', 'obligation_precedes', 'order_of', 'precedes', 'validate_order')))

    print("\n6. D'5 (PERMANENT) - THE AETNA COUNTEREXAMPLE: the derived relation would be FALSE\n")
    ins, u_ins = pay('Aetna paid Mercy $568 for the ER visit.', '2026-03-12T09:00:00')
    role_p('paid_by', aetna, ins, u_ins)
    role_p('paid_to', mercy, ins, u_ins)
    p_x(ins, X, u_ins)
    about_p('amount', ins, '$568', utterance=u_ins)
    check("D'5 (PERMANENT): Aetna's payment is in respect of X; Rob's $412 obligation O is in respect of X; the inference 'Aetna's payment -> Rob's obligation' is FALSE and NO row exists - not under-evidenced, semantically unsound",
          s.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF, subject_payment_id=ins.id, object_expense_id=X.id).count() == 1
          and rel(p=ins).count() == 0 and rel(p=ins, o=O).count() == 0)
    check("D'5 (PERMANENT): NON-SELECTION holds here too, and O is untouched - Rob owes $412 regardless; no balance, remaining or status on O changed",
          nothing_selected()
          and s.query(db.Proposition).filter(db.Proposition.subject_obligation_id == O.id,
                                             db.Proposition.kind.in_(('balance', 'remaining', 'paid', 'reduced', 'credited'))).count() == 0)

    print("\n7. D'6 - reimbursement and the desk copay: convergence with an unwanted result\n")
    reimb, u_reimb = pay('The HSA reimbursed me $412 for the ER visit.', '2026-05-21T09:00:00')
    role_p('paid_by', hsa, reimb, u_reimb)
    p_x(reimb, X, u_reimb)
    copay, u_copay = pay('$30 copay at the desk, before any bill.', '2026-02-14T18:00:00')
    p_x(copay, X, u_copay)
    check("D'6: the reimbursement and the desk copay are each in respect of X; neither is in respect of O; convergence produced nothing and selected nothing",
          rel(p=reimb).count() == 0 and rel(p=copay).count() == 0 and nothing_selected())

    print("\n8. D'7 - Chase's statement line: a candidate; the acknowledgment stand-in derives nothing\n")
    chase_stmt = held('h-chase-mar', '2026-03-31', chase, u_chase)
    r_chase = read(chase_stmt)
    n_rel = rel().count()
    line = prop('applied', object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=chase.id,
                content='payment received 3/5, $1,412, applied to loan 4471', as_of='2026-03-05')
    evidence(line, reading=r_chase)
    check("D'7: the statement line is Chase's proposition with candidates - 'applied to loan 4471' asserted no relation and selected no obligation",
          rel().count() == n_rel and nothing_selected())
    c_line = prop(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_payment_id=p1.id, object_obligation_id=o1.id, content='matcher: loan 4471 on the statement')
    e_cand = evidence(c_line, reading=r_chase)
    check("D'7: the matcher's pairing is a reading-sourced candidate - no party behind it; it establishes nothing and is not knowing",
          e_cand.utterance_id is None and e_cand.reading_id == r_chase.id
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c_line.id).count() == 1
          and not db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF_OBLIGATION]['reading_establishes']
          and db.derived_strength(s, e_cand, KNOWING) == db.STRENGTH_UNDETERMINED)
    n_rel = rel().count()
    e_ack, p_ack = role_p('acknowledged', chase, p1, utter('Chase confirmed the March payment.', '2026-03-06T09:00:00'), as_of='2026-03-05', content='applied')
    check("D'7: E's acknowledgment (subject E, object p - the D4 stand-in) is a different claim; it derived no relation row - 'which obligation' is not its participant (the S D'.4 finding, recorded, unfixed)",
          p_ack.subject_party_id == chase.id and p_ack.object_payment_id == p1.id and p_ack.object_obligation_id is None
          and rel().count() == n_rel and nothing_selected())
    u_chase_says = utter('Payment applied to loan 4471.', '2026-03-05T09:00:00', origin=chase)
    e_d7, r_d7 = p_o(p1, o1, utterance=u_chase_says, content='applied to 4471')
    check("D'7: Chase (an institution) may assert the relation as a party - a claim with its own evidence; knowing undetermined for every asserter",
          e_d7.utterance.origin_party_id == chase.id
          and db.derived_strength(s, e_d7, KNOWING) == db.STRENGTH_UNDETERMINED
          and db.derived_strength(s, e_d1, KNOWING) == db.STRENGTH_UNDETERMINED
          and 'knowing_relation' not in db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF_OBLIGATION])

    print("\n9. D'8 / D'9 / D'10 - S3, S6, E rejects: the relation stands; no discharge, no remaining\n")
    p5, u_p5 = pay('I paid the servicer that wrote to us $1,412 in May - for the mortgage.', '2026-05-03T09:00:00')
    role_p('paid_to', s3, p5, u_p5)
    p_o(p5, o1, utterance=u_p5)
    check("D'8 (S3): a payment to the never-authorised servicer in respect of O1 - a real claim; no acknowledgment ever comes; no discharge; S3 acquires no entitlement",
          rel(p=p5, o=o1).count() == 1
          and s.query(db.Proposition).filter_by(kind='acknowledged', object_payment_id=p5.id).count() == 0
          and s.query(db.Proposition).filter_by(kind='entitled_party', subject_party_id=s3.id).count() == 0)
    p6, u_p6 = pay('I paid Chase directly in June; they never credited it.', '2026-06-03T09:00:00')
    about_p(db.CLEARED, p6, 'cleared 6/4', reading=r_chase, as_of='2026-06-04')
    p_o(p6, o1, utterance=u_p6)
    check("D'9 (S6): bank says cleared, E says nothing - the relation stands beside both; nothing chosen; remaining not moved",
          rel(p=p6, o=o1).count() == 1 and s.query(db.Proposition).filter_by(kind='acknowledged', object_payment_id=p6.id).count() == 0
          and not any(hasattr(db, n) for n in ('remaining_on', 'remaining_after', 'balance_after')))
    role_p('returned', chase, p6, utter('Chase returned the June payment as unapplied.', '2026-06-10T09:00:00'), as_of='2026-06-09')
    check("D'10: E rejects the payment - a dated claim on p beside the relation; the relation is not withdrawn; no status on p or O",
          rel(p=p6, o=o1).count() == 1 and s.query(db.Proposition).filter_by(kind='returned', object_payment_id=p6.id).count() == 1
          and not any(hasattr(db.Payment, w) for w in ('rejected', 'unapplied', 'status')))

    print("\n10. D'11 - the escrow refund: money the other way, the same kind\n")
    esc, u_esc = pay('Chase refunded a $210 escrow overage on 7/1 - on the mortgage.', '2026-07-02T09:00:00')
    role_p('paid_by', chase, esc, u_esc)
    role_p('paid_to', household, esc, u_esc)
    e_d11, r_d11 = p_o(esc, o1, utterance=u_esc, content='escrow refund')
    check("D'11: a payment from the creditor to the household in respect of the mortgage - the same kind; 'toward' would misdescribe it; the relation carries no direction of money",
          r_d11.kind == db.PAYMENT_IN_RESPECT_OF_OBLIGATION
          and s.query(db.Proposition).filter_by(kind='paid_by', object_payment_id=esc.id).one().subject_party_id == chase.id
          and not any(hasattr(db, n) for n in ('direction_of', 'money_direction', 'reduces', 'payment_reduces')))

    print("\n11. D'12 - cardinality is not allocation\n")
    OP1, _ = owe("Mercy's facility plan.", '2026-06-01T09:00:00')
    OP2, _ = owe("The physicians' plan.", '2026-06-01T09:01:00')
    cheque, u_chq = pay('One cheque to Mercy for both plans, $350.', '2026-07-01T09:00:00')
    p_o(cheque, OP1, utterance=u_chq)
    p_o(cheque, OP2, utterance=u_chq)
    check("D'12: one payment in respect of two obligations - two claims; no allocation, split, percentage or order of satisfaction",
          rel(p=cheque).count() == 2
          and not any(w in c.name for w in ('share', 'portion', 'percent', 'allocation', 'priority', 'amount') for c in db.Proposition.__table__.columns)
          and not any(hasattr(db, n) for n in ('allocate', 'allocation_of', 'split_of', 'apportion')))
    u_auto = utter('The twelve autopay mortgage payments this year.', '2026-12-31T09:00:00')
    for m in range(1, 13):
        pm, _ = pay(f'Autopay {m}/2026, $1,412.', f'2026-{m:02d}-03T09:00:00')
        p_o(pm, o1, utterance=u_auto)
    check("D'12: twelve payments in respect of one obligation - no sum, no 'paid down', no remaining (H2 / item 7)",
          rel(o=o1).count() >= 12 and not any(hasattr(db, n) for n in ('total_paid', 'sum_of_payments', 'paid_down', 'remaining_on', 'balance_after')))

    print("\n12. D'13 / D'14 - retraction; dispute\n")
    heloc, u_heloc = owe('Our HELOC with Chase.', '2024-02-01T09:00:00')
    n_rel, n_pay, n_obl = rel().count(), s.query(db.Payment).count(), s.query(db.Obligation).count()
    r = prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_p1.id)
    evidence(r, utterance=utter("That March payment wasn't toward the mortgage - it was the HELOC.", '2026-09-15T09:00:00'))
    p_o(p1, heloc, utterance=utter('It was toward the HELOC.', '2026-09-15T09:01:00'))
    check("D'13: retracting the utterance behind a relation claim leaves p, O1 and every row; a new claim to the HELOC is a new claim",
          rel().count() == n_rel + 1 and s.query(db.Payment).count() == n_pay and s.query(db.Obligation).count() == n_obl
          and rel(p=p1, o=o1).count() >= 1 and rel(p=p1, o=heloc).count() == 1)
    u_kim = db.Utterance(origin_party_id=kim_party.id, asserted_at='2026-09-15T09:02:00', content='No - the March payment was the mortgage, not the HELOC.')
    s.add(u_kim)
    s.commit()
    p_o(p1, o1, utterance=u_kim)
    check("D'14: Rob and Kim disagree which obligation - claims stand, contested; nothing chooses; no current attribution",
          rel(p=p1).count() >= 3 and not any(hasattr(db, n) for n in ('current_obligation', 'attribution_of', 'resolve_toward')))

    print("\n13. D'15 - composition with obligation_replaces and payment_counteracts refused\n")
    o3, u_o3 = owe('The NewBank refinance loan.', '2027-01-05T09:00:00')
    evidence(prop(db.OBLIGATION_REPLACES, subject_obligation_id=o3.id, object_obligation_id=o1.id), utterance=u_o3)
    check("D'15: O3 replaces O1 + p in respect of O1 does NOT derive p in respect of O3",
          rel(o=o3).count() == 0)
    ref, u_ref = pay('The bank reversed the June payment.', '2026-06-12T09:00:00')
    evidence(prop(db.PAYMENT_COUNTERACTS, subject_payment_id=ref.id, object_payment_id=p6.id), utterance=u_ref)
    check("D'15: ref counteracts p6 + p6 in respect of O1 does NOT derive ref in respect of O1 (nor the reverse)",
          rel(p=ref).count() == 0)
    n_rel = rel().count()
    o_x(o1, X, utter('(a wrong but assertable claim, for the test)', '2026-09-16T09:00:00'))
    check("D'15: even after O1 is asserted in respect of X, the payments in respect of X (q4, ins, reimb, copay) acquire no relation to O1 - the convergence join is never made",
          rel().count() == n_rel and all(rel(p=q, o=o1).count() == 0 for q in (q4, ins, reimb, copay)) and nothing_selected())

    print("\n14. D'17 / D'18 - the floor; direction fixed by type; refusals; immutability\n")
    pf, u_pf = pay('The $1,412 payment was in respect of the mortgage.', '2026-08-03T09:00:00')
    e_d17, r_d17 = p_o(pf, o1, utterance=u_pf)
    check("D'17: the sentence establishes exactly the relation - no applied / credited / discharged / instalment / on-time / cleared / entitled / remaining claim appeared from it",
          rel(p=pf, o=o1).count() == 1 and r_d17.content is None
          and s.query(db.Proposition).filter(db.Proposition.object_payment_id == pf.id).count() == 0
          and s.query(db.Proposition).filter(db.Proposition.subject_payment_id == pf.id, db.Proposition.kind != db.PAYMENT_IN_RESPECT_OF_OBLIGATION).count() == 0
          and not any(w in c.name for w in ('applied', 'credited', 'discharged', 'instalment', 'installment', 'on_time', 'remaining') for c in db.Proposition.__table__.columns))
    check("D'18: there is no reverse claim - the slots swapped are refused; candidates, a party subject, an expense object, a payment object are refused",
          _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_obligation_id=o1.id, object_payment_id=p1.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                         subject_payment_id=p1.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_party_id=chase.id, object_obligation_id=o1.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_payment_id=p1.id, object_expense_id=X.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_payment_id=p1.id, object_payment_id=p6.id)))
    check("the relation's references are immutable - re-pointing a participant is refused; correction is retraction + a new claim",
          (lambda: (r_d1.object_obligation_id, setattr(r_d1, 'object_obligation_id', heloc.id), _refused(s, r_d1))[2])()
          and s.get(db.Proposition, r_d1.id).object_obligation_id == o1.id)
    check("D'18: traversal enumerates - from p1 every asserted obligation with its asserter (O1 by Rob, O1 by Chase, O1 by Kim, HELOC by Rob, the candidate); from O1 the other way; no accessor selects",
          {(pr.object_obligation_id, e.utterance.origin_party_id if e.utterance_id else None)
           for pr in rel(p=p1) for e in s.query(db.EvidentiaryRelationship).filter_by(proposition_id=pr.id)}
          >= {(o1.id, household.id), (o1.id, chase.id), (o1.id, kim_party.id), (heloc.id, household.id), (o1.id, None)}
          and {pr.subject_payment_id for pr in rel(o=o1)} >= {p1.id, p5.id, p6.id, esc.id, pf.id}
          and nothing_selected())

    print('\n15. Absences; schema; audits\n')
    check("D'16: toward / against / applied / attached / paid down are content or another party's claim - none is a kind, none has a proposition row of that kind on a payment-obligation pair",
          not any(k in db.RULED_KINDS for k in SOURCE_KINDS)
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(SOURCE_KINDS), db.Proposition.object_obligation_id.isnot(None)).count() == 0)
    check('no generic relation base, resolver, selector, convergence join, inverse, discharge, remaining or allocation helper was introduced; no payment.obligation accessor',
          not any(hasattr(db, n) for n in CONSUMER_NAMES) and nothing_selected())
    check('no schema: anchors as their slices left them; both slots pre-existed; no relation table',
          {c.name for c in db.Payment.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and {c.name for c in db.Obligation.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and 'subject_payment_id' in db.Proposition.SUBJECT_SLOTS and 'object_obligation_id' in db.Proposition.OBJECT_SLOTS
          and not any('relation' in t for t in db.Base.metadata.tables))
    check('every audit is empty',
          not db.payments_without_minting_utterance(s) and not db.obligations_without_minting_utterance(s)
          and not db.expenses_without_minting_utterance(s) and not db.parties_without_one_anchor(s))

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
