"""payment_counteracts - the executable trace of `gw 2.0/RELATION_SEMANTICS.md` pass A (ruled 2026-09-15).

`payment_counteracts(p2, p1)` means exactly: the asserting party holds that the subject payment
economically counteracts some or all of the object payment. Both participants are established
payments; directional, never symmetric, no inverse kind, no cardinality; established only by a
party's assertion; carries no amount; requires no payer/payee mirroring; derives nothing.

What this slice can and cannot exercise
---------------------------------------
    A1  chargeback: p2 counteracts p1, asserted by Rob; p1 untouched, no status           EXERCISED
    A2  the pharmacy asserts it; "refund" in content establishes nothing; knowing undetermined  EXERCISED
    A3  partial: the relation carries no amount; nothing computes a remainder              EXERCISED
    A4  chain: p3 counteracts p2; p3 counteracts p1 is NOT derived                         EXERCISED
    A5  one refund counteracts two payments                                                EXERCISED
    A6  two refunds counteract one payment                                                 EXERCISED
    A7  the refund lands on Kim's card: no payer/payee mirroring required                  EXERCISED
    A8  the bank's REFUND line: a reading-sourced candidate at most; mints nothing          EXERCISED
    A9  disputed attribution: two claims, contested, nothing chosen                         EXERCISED
    A10 retraction of the assertion: payments untouched; no opposite relation               EXERCISED
    A11 goodwill over-credit: the relation validates no amounts                             EXERCISED
    A12 the bounced ACH: one payment, a claim about it, NO relation                         EXERCISED
    A13 direction is asserted, never derived from dates; not symmetric; the reverse is another claim  EXERCISED
    A14 refund / chargeback / return / goodwill are not kinds                               EXERCISED (absence)
    both endpoints established payments; reflexive refused; cross-type refused              EXERCISED
    no reversed/refunded status, no netting, no inverse accessor, no relation base or resolver  EXERCISED (absence)
    knowing for the relation (payer-of-subject role), netting, discharge (item 7), passes B-G  NOT BUILT

Run:  python tests/test_payment_counteracts_fixture.py
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


STATUS_WORDS = ('reversed', 'refunded', 'counteracted', 'undone', 'voided', 'net_', 'remaining', 'payment_status', 'payment_state')
CONSUMER_NAMES = ('net_of', 'net_paid', 'remaining_after', 'counteracted_by', 'counteracts', 'is_reversed', 'is_refunded',
                  'effective_amount', 'payment_net', 'inverse_of', 'relations_of', 'Relation', 'RelationBase',
                  'resolve_relation', 'relation_resolver', 'related_payments')
SOURCE_KINDS = ('reverses', 'reversal_of', 'refunds', 'refund_of', 'returns', 'chargeback', 'chargeback_of',
                'partial_refund', 'goodwill', 'payment_relation', 'payment_undoes')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_pc_')
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
               'bank_returned_item': {'institution'}}   # returned: E's kind since 9D-i - the bank's returned-item line is the bank's own stance (9D-iv); paid_to: a ruled role since 9B - knowing by relation, not by the map

    def utter(text, when='2026-06-03T09:00:00', origin=None):
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

    def about(kind, p, content, utterance=None, reading=None, as_of=None):
        pr = prop(kind, object_state=db.PARTICIPANT_NONE, subject_payment_id=p.id, content=content, as_of=as_of)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def counteracts(subject, obj, utterance=None, reading=None, content=None):
        pr = prop(db.PAYMENT_COUNTERACTS, subject_payment_id=subject.id, object_payment_id=obj.id, content=content)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def rel(subject=None, obj=None):
        q = s.query(db.Proposition).filter_by(kind=db.PAYMENT_COUNTERACTS)
        if subject is not None:
            q = q.filter_by(subject_payment_id=subject.id)
        if obj is not None:
            q = q.filter_by(object_payment_id=obj.id)
        return q

    mercy, u_mercy = mint_party('Mercy Hospital.')
    pharmacy, u_pharm = mint_party('The pharmacy.')
    bank, u_bank = mint_party('Our bank.')

    print('\n1. The registry entry - exactly as authorised\n')
    check('payment_counteracts is ruled exactly as authorised: payment subject, payment object, not symmetric, reading never establishes, relational_knowing True, no knowing_relation',
          db.RULED_KINDS[db.PAYMENT_COUNTERACTS] == {'subject': ('subject_payment_id',), 'object': ('object_payment_id',),
                                                    'symmetric': False, 'reading_establishes': False, 'relational_knowing': True})
    check('no source-word or generic relation kind exists beside it',
          not any(k in db.RULED_KINDS for k in SOURCE_KINDS))

    print('\n2. A1 - chargeback: p2 counteracts p1; p1 untouched\n')
    p1, u_p1 = pay('I paid Mercy $300 on June 2.', '2026-06-03T09:00:00')
    about('amount', p1, '$300', utterance=u_p1)
    p2, u_p2 = pay("Mercy's $300 came back on June 9 - the chargeback.", '2026-06-10T09:00:00')
    about('amount', p2, '$300', utterance=u_p2)
    e_a1, r_a1 = counteracts(p2, p1, utterance=utter('That undid the June 2 charge.', '2026-06-10T09:05:00'))
    check('A1: the relation is a claim with two established payment participants - the counteracting payment the subject',
          r_a1.subject_payment_id == p2.id and r_a1.object_payment_id == p1.id
          and r_a1.subject_state == db.PARTICIPANT_ESTABLISHED and r_a1.object_state == db.PARTICIPANT_ESTABLISHED)
    check('A1: p1 acquires no status - the payment anchor carries nothing; no reversed/refunded accessor exists',
          {c.name for c in db.Payment.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and not any(hasattr(db.Payment, w) for w in STATUS_WORDS)
          and not any(hasattr(db, n) for n in CONSUMER_NAMES))
    check('A1: two payments remain two identities - the relation merges nothing and mints nothing',
          s.get(db.Payment, p1.id) is not None and s.get(db.Payment, p2.id) is not None
          and s.query(db.Payment).count() == 2)

    print('\n3. A2 - the pharmacy asserts a refund; the word establishes nothing; knowing undetermined\n')
    p3, u_p3 = pay('The pharmacy credited $84 for the cushion I returned.', '2026-05-20T09:00:00')
    p0, u_p0 = pay('I bought the cushion at the pharmacy on 5/12, $84.', '2026-05-12T09:00:00')
    u_pharm_says = utter('Refund issued for order 5512.', '2026-05-19T09:00:00', origin=pharmacy)
    e_a2, r_a2 = counteracts(p3, p0, utterance=u_pharm_says, content='refund for order 5512')
    check('A2: an institution may assert the relation - a claim with its own evidence; "refund" is content',
          e_a2.utterance.origin_party_id == pharmacy.id and 'refund' in r_a2.content)
    check('A2: knowing for the relation is undetermined - ruled True with no designated relation; the payer-of-subject role is not ruled',
          db.derived_strength(s, e_a2, KNOWING) == db.STRENGTH_UNDETERMINED
          and db.derived_strength(s, e_a1, KNOWING) == db.STRENGTH_UNDETERMINED)

    print('\n4. A3 / A11 - partial and over-credit: the relation carries no amount, validates none\n')
    p4, u_p4 = pay('$120 of the $300 came back on 6/9.', '2026-06-10T09:00:00')
    about('amount', p4, '$120', utterance=u_p4)
    e_a3, r_a3 = counteracts(p4, p1, utterance=utter('That was a partial refund of the Mercy charge.', '2026-06-10T09:06:00'), content='partial')
    check('A3: the same kind for a partial - p4\'s $120 is p4\'s own amount claim; the relation row carries no amount and nothing computes $180',
          r_a3.kind == db.PAYMENT_COUNTERACTS and 'amount' not in {c.name for c in db.Proposition.__table__.columns}
          and not any(hasattr(db, n) for n in ('net_of', 'remaining_after', 'effective_amount', 'payment_net')))
    p5, u_p5 = pay('Mercy sent a $350 goodwill credit against the $300.', '2026-07-01T09:00:00')
    about('amount', p5, '$350', utterance=u_p5)
    e_a11, _ = counteracts(p5, p1, utterance=utter('That credit was for the June 2 charge.', '2026-07-01T09:05:00'), content='goodwill')
    check('A11: an over-credit is accepted as a claim like any other - the relation validates no amounts',
          rel(p5, p1).count() == 1)

    print('\n5. A4 - the chain: p3 counteracts p2 derives nothing about p1\n')
    p6, u_p6 = pay('The $300 went back to Mercy on 7/15 - the merchant won the dispute.', '2026-07-16T09:00:00')
    counteracts(p6, p2, utterance=utter('That reversed the chargeback.', '2026-07-16T09:05:00'))
    check('A4: p6 counteracts p2 is one claim; p6 counteracts p1 does not exist and is not derived',
          rel(p6, p2).count() == 1 and rel(p6, p1).count() == 0)

    print('\n6. A5 / A6 - no cardinality\n')
    p7, u_p7 = pay('One $130 refund cheque for the two returns.', '2026-08-02T09:00:00')
    p8, _ = pay('The $46 brace on 7/20.', '2026-07-20T09:00:00')
    u_two = utter('The cheque covered the cushion and the brace.', '2026-08-02T09:05:00')
    counteracts(p7, p0, utterance=u_two)
    counteracts(p7, p8, utterance=u_two)
    check('A5: one payment counteracts two - two claims, one utterance; no uniqueness anywhere',
          rel(p7).count() == 2)
    check('A6: one payment counteracted by several - p1 by p2, p4, p5',
          rel(obj=p1).count() == 3)

    print('\n7. A7 - the refund lands on Kim\'s card: no payer/payee mirroring\n')
    # 9B ruled paid_to / paid_by as roles (party -> payment); this corpus had used the names for a content claim on the payment
    evidence(prop(db.PAID_TO, subject_party_id=kim_party.id, object_payment_id=p2.id, as_of='2026-06-11'),
             utterance=utter("The chargeback credit went to Kim's new card.", '2026-06-11T09:00:00'))
    evidence(prop(db.PAID_BY, subject_party_id=household.id, object_payment_id=p1.id, as_of='2026-06-03'), utterance=u_p1)
    check('A7: p2\'s payee is Kim and p1\'s payer is Rob - role claims on each payment (9B\'s kinds); the relation stands without requiring them to mirror',
          s.query(db.Proposition).filter_by(kind=db.PAID_TO, object_payment_id=p2.id, subject_party_id=kim_party.id).count() == 1
          and rel(p2, p1).count() == 1
          and not any(hasattr(db, n) for n in ('payer_matches_payee', 'mirrored', 'requires_mirroring')))

    print('\n8. A8 - the bank\'s REFUND line: a candidate at most; nothing minted\n')
    stmt = db.Artefact(held=True, content_hash='h-stmt', as_of='2026-06-30')
    s.add(stmt)
    s.commit()
    evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=stmt.id, object_party_id=bank.id), utterance=u_bank)
    rd = db.Reading(artefact_id=stmt.id, reader_process='feed-import/1', read_at=datetime(2026, 7, 1))
    s.add(rd)
    s.commit()
    n_pay = s.query(db.Payment).count()
    p_line = prop('movement', object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=bank.id, content='REFUND MERCY 300.00', as_of='2026-06-09')
    evidence(p_line, reading=rd)
    check('A8: the REFUND line is a proposition from a capture - it minted no payment and asserted no relation',
          s.query(db.Payment).count() == n_pay
          and s.query(db.EvidentiaryRelationship).join(db.Proposition).filter(db.Proposition.kind == db.PAYMENT_COUNTERACTS,
                                                                            db.EvidentiaryRelationship.reading_id.isnot(None)).count() == 0)
    c_line = prop(db.PAYMENT_COUNTERACTS, subject_payment_id=p2.id, object_payment_id=p1.id, content='matcher: same amount, opposite direction')
    e_cand = evidence(c_line, reading=rd)
    check('A8: the matcher\'s pairing is a reading-sourced candidate - no party behind it; it establishes nothing and is not knowing',
          e_cand.utterance_id is None and e_cand.reading_id == rd.id
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c_line.id).count() == 1
          and not db.RULED_KINDS[db.PAYMENT_COUNTERACTS]['reading_establishes']
          and db.derived_strength(s, e_cand, KNOWING) == db.STRENGTH_UNDETERMINED)

    print('\n9. A9 / A10 - disputed attribution; retraction\n')
    u_kim = db.Utterance(origin_party_id=kim_party.id, asserted_at='2026-05-21T09:00:00', content='No - the $84 credit was for the brace, not the cushion.')
    s.add(u_kim)
    s.commit()
    counteracts(p3, p8, utterance=u_kim)
    check('A9: Rob says p3 counteracts p0, Kim says p3 counteracts p8 - two claims stand; nothing chooses; no current attribution',
          rel(p3).count() == 2 and not any(hasattr(db, n) for n in ('current_attribution', 'attribution_of', 'resolve_counteracts')))
    n_rel = rel().count()
    r = prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_pharm_says.id)
    evidence(r, utterance=utter("The pharmacy's note was wrong - that credit wasn't for 5512.", '2026-05-22T09:00:00', origin=pharmacy))
    check('A10: retracting the utterance behind a relation claim leaves both payments and the relation row; no opposite relation appears',
          rel().count() == n_rel and s.get(db.Payment, p3.id) is not None and s.get(db.Payment, p0.id) is not None
          and rel(p0, p3).count() == 0)

    print('\n10. A12 / A13 - no second payment, no relation; direction is asserted\n')
    p9, u_p9 = pay('I paid Chase $1,412 on 3/3.', '2026-03-03T09:00:00')
    about('bank_returned_item', p9, 'RETURNED ITEM 3/5', utterance=utter('The bank says the 3/3 payment was returned on 3/5.', '2026-03-06T09:00:00', origin=bank), as_of='2026-03-05')
    check('A12: the bounced ACH is one payment with a dated claim about it - no second payment, no relation',
          rel(obj=p9).count() == 0 and rel(p9).count() == 0
          and s.query(db.Proposition).filter_by(kind='bank_returned_item', subject_payment_id=p9.id).count() == 1)
    check('A13: the relation is not symmetric - asserting p1 counteracts p2 is a different claim, and it is not derived from p2 counteracts p1',
          not db.RULED_KINDS[db.PAYMENT_COUNTERACTS]['symmetric'] and rel(p1, p2).count() == 0)
    check('A13: reflexive and cross-type are refused; both participants must be established payments',
          _refused(s, db.Proposition(kind=db.PAYMENT_COUNTERACTS, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_payment_id=p1.id, object_payment_id=p1.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_COUNTERACTS, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_payment_id=p1.id, object_party_id=mercy.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_COUNTERACTS, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                         subject_payment_id=p2.id)))
    check('the relation\'s references are immutable - re-pointing a participant is refused; correction is retraction + a new claim',
          (lambda: (r_a1.object_payment_id, setattr(r_a1, 'object_payment_id', p0.id), _refused(s, r_a1))[2])()
          and s.get(db.Proposition, r_a1.id).object_payment_id == p1.id)

    print('\n11. A14 / absences\n')
    check('A14: refund, chargeback, return, partial, goodwill are content or claims about the counteracting payment - none is a kind',
          not any(k in db.RULED_KINDS for k in SOURCE_KINDS)
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(SOURCE_KINDS)).count() == 0)
    check('no generic relation base, resolver, inverse accessor, status or netting helper was introduced',
          not any(hasattr(db, n) for n in CONSUMER_NAMES)
          and not any(w in c.name for w in STATUS_WORDS for c in db.Proposition.__table__.columns))
    check('no schema: the payment anchor and the proposition slots are as the payment and plan slices left them',
          {c.name for c in db.Payment.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and 'subject_payment_id' in db.Proposition.SUBJECT_SLOTS and 'object_payment_id' in db.Proposition.OBJECT_SLOTS
          and not any('relation' in t for t in db.Base.metadata.tables))
    check('every audit is empty',
          not db.payments_without_minting_utterance(s))

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
