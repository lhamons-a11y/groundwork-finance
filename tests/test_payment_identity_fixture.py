# -*- coding: utf-8 -*-
"""The payment-identity fixture - the build gate over Pm1-Pm14 and the s9 consistency checks.

`gw 2.0/PAYMENT_IDENTITY.md` s8 (ruled s10, 2026-09-14):

    A payment is an event identity. An individuating assertion originating from a Person mints
    that identity; the asserting utterance is the minting act, not the payment. Minting
    establishes the identity, not the truth of any property asserted about the event. The
    anchor is structure plus a pointer to the minting utterance and nothing else. Payer and
    payee are dated relations; toward(p, O) is a household claim; acknowledgment by the entitled
    party is the discharge claim and does not establish the payment's existence. A payment is
    not a transaction, not discharge, not a confirmed payment. A bank line, ledger row, draft or
    entitled-party statement can produce a candidate but cannot mint the payment. Relations to
    a payment remain typed; a candidate match does not establish correspondence; a statement
    line requires proposition-level about-ness; no relation merges or re-points identities.

The claim kinds used here (amount, occurred_on, paid_to, paid_by, toward, cleared, acknowledged,
reversed) are STAND-INS; only payment_corresponds is ruled. Nothing derives discharge, remaining
or confirmation.

What this build can and cannot exercise, stated so greenness is not over-read:

    Pm1  one act mints p; amount, date, payee, toward are claims          EXERCISED
    Pm2  a bank line mints nothing; a candidate names no referent          EXERCISED (the line->p tie: Ab7 slice)
    Pm3  D4 - E acknowledges p as of d - is representable                  EXERCISED (consequence NOT derived)
    Pm4  S6 - bank says yes, E says nothing; nothing chosen                EXERCISED
    Pm5  S3 - payee != entitled; toward != discharge                       EXERCISED
    Pm6  K8 - $1,412 sent vs $1,387 applied: two claims, nothing chosen    EXERCISED
    Pm7  reversal as a dated claim about p; event-vs-claim NOT decided     EXERCISED (shape only)
    Pm8  (a) two payments, one debit = about-ness; (b) mis-individuation = correspondence  EXERCISED
    Pm9  payer is a role; a non-household individual is a minted party    EXERCISED
    Pm10 autopay lines are candidates; identity rule unchanged             EXERCISED (policy fenced)
    Pm11 a payment with no transaction (cash)                              EXERCISED
    Pm12 a transaction with no payment (own-account transfer)              EXERCISED
    Pm13 retraction of the toward claim; of the minting utterance          EXERCISED (no unminting)
    Pm14 a draft cannot mint; an institution-origin utterance cannot mint  EXERCISED
    s9   minted_by != payer; pointer not unique; created_at != occurred; generic slots;
         no inferring accessors; correspondence read-only                  EXERCISED
    line-level ties · discharge->remaining · reversal event · catalogue    NOT BUILT

Run:  python tests/test_payment_identity_fixture.py
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


DESCRIPTORS = ('payer', 'payee', 'amount', 'date', 'occurred', 'method', 'purpose', 'toward', 'cleared',
               'attached', 'confirmed', 'acknowledged', 'discharged', 'reversed', 'status', 'obligation',
               'transaction', 'account', 'merchant')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_payment_')
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


def _update_refused(s, obj, attr, value, exc=ValueError):
    before = getattr(obj, attr)
    try:
        setattr(obj, attr, value)
        s.commit()
        s.rollback()
        return False
    except exc:
        s.rollback()
        return getattr(obj, attr) == before


def run(db):
    from sqlalchemy.exc import IntegrityError
    s = _fresh()
    rob = db.Person(display_name='Rob')
    s.add(rob)
    s.commit()
    household = rob.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}, db.PAYMENT_CORRESPONDS: {'person', 'institution'},
               'cleared': {'institution'}, 'acknowledged': {'institution'}, 'amount': {'person', 'institution'}}

    def utter(text, when='2026-03-10T09:00:00', origin=None):
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

    def mint_obligation(u):
        o = db.Obligation(minted_by_id=u.id)
        s.add(o)
        s.commit()
        return o

    def mint_payment(u):
        pm = db.Payment(minted_by_id=u.id)
        s.add(pm)
        s.commit()
        return pm

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

    def about(kind, pm, content, utterance=None, reading=None, as_of=None):
        # a stand-in stance about the payment: subject the payment, no second participant
        p = prop(kind, object_state=db.PARTICIPANT_NONE, subject_payment_id=pm.id, content=content, as_of=as_of)
        return evidence(p, utterance=utterance, reading=reading), p

    def role(kind, party, pm, utterance, as_of=None):
        # a stand-in role claim: subject the party, object the payment
        p = prop(kind, subject_party_id=party.id, object_payment_id=pm.id, as_of=as_of)
        return evidence(p, utterance=utterance), p

    def held(h, as_of, origin_party, origin_utt):
        a = db.Artefact(held=True, content_hash=h, as_of=as_of)
        s.add(a)
        s.commit()
        evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=a.id, object_party_id=origin_party.id), utterance=origin_utt)
        return a

    def read(a, process='feed-import/1', when=datetime(2026, 3, 11)):
        r = db.Reading(artefact_id=a.id, reader_process=process, read_at=when)
        s.add(r)
        s.commit()
        return r

    chase, u_chase = mint_party('Chase, my mortgage lender.')
    bank, u_bank = mint_party('My bank.')
    o1 = mint_obligation(utter('I have a mortgage with Chase.'))

    print('\n1. Pm1 - "I paid Chase $1,412 on March 3 for the mortgage": one act mints; the rest is claims\n')
    u_paid = utter('I paid Chase $1,412 on March 3 for the mortgage.', '2026-09-14T09:00:00')
    p1 = mint_payment(u_paid)
    check('the payment exists under the utterance that minted it, whose origin is a Person',
          p1.minted_by is u_paid and db.party_foundation(u_paid.origin) == 'person')
    check('the anchor is structure plus the pointer and nothing else',
          {c.name for c in db.Payment.__table__.columns} == {'id', 'minted_by_id', 'created_at'})
    check('no descriptor lives on the anchor or the model - payer, payee, amount, date, toward, cleared... are claims',
          not any(any(d in c.name for d in DESCRIPTORS) for c in db.Payment.__table__.columns)
          and not any(hasattr(db.Payment, d) for d in DESCRIPTORS))
    e_amt, p_amt = about('amount', p1, '$1,412', utterance=u_paid)
    e_occ, p_occ = about('occurred_on', p1, None, utterance=u_paid, as_of='2026-03-03')
    e_to, p_to = role('paid_to', chase, p1, u_paid)
    p_toward = prop('toward', subject_payment_id=p1.id, object_obligation_id=o1.id)
    e_toward = evidence(p_toward, utterance=u_paid)
    check('the same act evidences amount, occurred date, payee and toward - four claims about p, none on the anchor',
          s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_paid.id).count() == 4
          and p_amt.subject_payment_id == p1.id and p_toward.object_obligation_id == o1.id)
    check('"$1,412" and "March 3" are content / as_of, never identity',
          p_amt.content == '$1,412' and p_occ.as_of == '2026-03-03')

    print('\n2. The minting act is not the minted identity; identity is not truth (s9)\n')
    check('the payment is not the utterance - different tables, different rows',
          p1.id != u_paid.id and type(p1) is not type(u_paid) and s.get(db.Utterance, u_paid.id) is not None)
    u_two = utter('I made two payments to the plumber this week.')
    pa, pb = mint_payment(u_two), mint_payment(u_two)
    check('one act may mint two identities - minted_by is a pointer to the act, not a unique key',
          pa.id != pb.id and pa.minted_by_id == pb.minted_by_id
          and not any(c.unique for c in db.Payment.__table__.columns if c.name == 'minted_by_id'))
    check('the pointer is immutable - a payment is never re-anchored to another act',
          _update_refused(s, p1, 'minted_by_id', u_two.id))
    check('created_at is identity-creation time: it is not March 3 and nothing reads it as the occurred date',
          p1.created_at.isoformat()[:10] != '2026-03-03' and p_occ.as_of == '2026-03-03'
          and not any(hasattr(db, n) for n in ('occurred_at', 'payment_date', 'occurred_on')))
    check('minted_by names the asserting act, never the payer - no payer column, payer is a role claim',
          not any('payer' in c.name or 'party' in c.name for c in db.Payment.__table__.columns))

    print('\n3. Pm14 / Pm2 - a draft, an institution\'s statement, a bank line: candidates, never mints\n')
    u_from_chase = utter('We received your payment of $1,412.', '2026-03-05T09:00:00', origin=chase)
    check('an utterance originating from an institution cannot mint a payment',
          _refused(s, db.Payment(minted_by_id=u_from_chase.id)))
    check('a payment without a minting utterance, or under one that does not exist, is refused',
          _refused(s, db.Payment(), (ValueError, IntegrityError))
          and _refused(s, db.Payment(minted_by_id=999999), (ValueError, IntegrityError)))
    stmt = held('h-bank-mar', '2026-03-31', bank, u_bank)
    r_stmt = read(stmt)
    n_before = s.query(db.Payment).count()
    p_line = prop('cleared', object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=bank.id,
                  content='CHASE MTG 3/3 -1,412.00', as_of='2026-03-03')
    e_line = evidence(p_line, reading=r_stmt)
    check('Pm2: a bank line mints nothing; the read claim names no payment referent (candidates, empty)',
          s.query(db.Payment).count() == n_before and p_line.object_payment_id is None
          and p_line.object_state == db.PARTICIPANT_CANDIDATES)
    # Ab7 retired the absence in place: the line -> p tie is proposition_concerns (tests/
    # test_proposition_concerns_fixture.py). Here none is asserted; the bank line names nothing.
    check('Pm2: the line -> p tie is a separate claim (Ab7), none asserted here - the line names nothing',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS).count() == 0
          and p_line.object_payment_id is None)
    check('a process cannot utter, so a draft cannot mint (O9) - the Person requirement covers it',
          _refused(s, db.Utterance(content='draft: mortgage payment due 4/1'), IntegrityError))

    print('\n4. Pm3 / Pm4 / Pm5 - D4 representable; S6; S3 - the three facts held apart\n')
    e_ack, p_ack = role('acknowledged', chase, p1, u_from_chase, as_of='2026-03-05')
    check('D4: E acknowledges p as of d - subject E, object p, as_of - is representable',
          p_ack.subject_party_id == chase.id and p_ack.object_payment_id == p1.id and p_ack.as_of == '2026-03-05'
          and e_ack.utterance.origin_party_id == chase.id)
    check('and its consequence is not derived: no remaining, no discharge accessor, no confirmed state',
          not any(hasattr(db, n) for n in ('remaining', 'discharged', 'discharge', 'is_confirmed', 'confirmed',
                                           'is_paid', 'paid', 'payment_status', 'cleared')))
    u_direct = utter('I paid Chase $400 directly at the branch on June 2.', '2026-06-03T09:00:00')
    p4 = mint_payment(u_direct)
    about('cleared', p4, 'debited 6/2', reading=r_stmt, as_of='2026-06-02')
    check('Pm4 (S6): the bank\'s claim stands and E\'s acknowledgment is absent - representable, nothing chosen',
          s.query(db.Proposition).filter_by(kind='cleared', subject_payment_id=p4.id).count() == 1
          and s.query(db.Proposition).filter_by(kind='acknowledged', object_payment_id=p4.id).count() == 0
          and s.get(db.Payment, p4.id) is not None)
    s3, _ = mint_party('S3 Servicing.')
    u_s3pay = utter('I paid S3 $1,412 in April - they said they were the servicer.', '2026-04-05T09:00:00')
    p5 = mint_payment(u_s3pay)
    role('paid_to', s3, p5, u_s3pay)
    evidence(prop('toward', subject_payment_id=p5.id, object_obligation_id=o1.id), utterance=u_s3pay)
    check('Pm5 (S3): a real payment; payee S3; toward O1; no acknowledgment from E - a payment, no discharge',
          s.query(db.Proposition).filter_by(kind='paid_to', object_payment_id=p5.id).count() == 1
          and s.query(db.Proposition).filter_by(kind='acknowledged', object_payment_id=p5.id).count() == 0)
    check('payee does not establish entitlement: S3 is paid_to p5 and holds no entitled_party claim on O1',
          s.query(db.Proposition).filter_by(kind='entitled_party', subject_party_id=s3.id).count() == 0)
    check('toward does not establish discharge: p5 is toward O1 and nothing derives discharge from it',
          not any(hasattr(db, n) for n in ('discharge_of', 'discharged_by', 'apply_payment')))

    print('\n5. Pm6 / Pm7 - two claims about one payment; a reversal as a dated claim\n')
    about('amount', p1, '$1,387 applied (fee deducted)', utterance=u_from_chase, as_of='2026-03-05')
    check('Pm6 (K8): $1,412 (Rob) and $1,387 applied (Chase) are two claims about p1; nothing chosen',
          s.query(db.Proposition).filter_by(kind='amount', subject_payment_id=p1.id).count() == 2
          and not any(hasattr(db, n) for n in ('amount_of', 'current_amount')))
    u_rev = utter('The bank reversed the June 2 payment on June 9.', '2026-06-10T09:00:00')
    about('reversed', p4, 'reversed', utterance=u_rev, as_of='2026-06-09')
    # REVERSAL ruled C (a claim, never an identity); item 6 pass A ruled the two-payment relation as
    # payment_counteracts - so 'reverses' / 'reversal_of' stay non-kinds by ruling, not by omission.
    check('Pm7: a reversal is representable as a dated claim about p4 (ruled: a claim, never an identity); no source-word relation kind exists',
          s.query(db.Proposition).filter_by(kind='reversed', subject_payment_id=p4.id).count() == 1
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(('reverses', 'reversal_of'))).count() == 0)

    print('\n6. Pm8 - (a) two payments, one debit: about-ness; (b) mis-individuation: correspondence, never merged\n')
    u_a = utter('I paid the plumber $700 on the 10th.', '2026-05-10T09:00:00')
    u_b = utter('And $712 the same day.', '2026-05-10T09:05:00')
    pa2, pb2 = mint_payment(u_a), mint_payment(u_b)
    check('(a) two real payments are two identities; a single bank debit concerning both is Ab7\'s question, not correspondence',
          pa2.id != pb2.id and db.referent(s, pa2) == (db.REFERENT_SEPARATE, [pa2.id], []))
    c = prop(db.PAYMENT_CORRESPONDS, subject_payment_id=pb2.id, object_payment_id=pa2.id,
             content='basis: one $1,412 debit on the 10th')
    evidence(c, reading=r_stmt)
    check('(b) the bank\'s single debit is a CANDIDATE for correspondence - no party behind it',
          db.referent(s, pa2) == (db.REFERENT_CANDIDATES, [pa2.id], [pb2.id])
          and db.derived_strength(s, s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c.id).one(), KNOWING)
          == db.STRENGTH_UNDETERMINED)
    evidence(c, utterance=utter('Actually those were one payment - I misremembered.', '2026-05-12T09:00:00'))
    check('(b) Rob\'s answer establishes: pa and pb correspond; the referent contains both; two rows remain under their own acts',
          db.referent(s, pa2) == (db.REFERENT_CORRESPONDING, sorted([pa2.id, pb2.id]), [])
          and s.get(db.Payment, pa2.id).minted_by_id == u_a.id and s.get(db.Payment, pb2.id).minted_by_id == u_b.id)
    check('correspondence stays correspondence: referent() is read-only and no substitution accessor exists',
          not any(hasattr(db, n) for n in ('merge_payments', 'canonical_payment', 'resolve_referent', 'substitute')))

    print('\n7. Pm9 / Pm11 / Pm12 - the payer is a role; a payment with no transaction; a transaction with no payment\n')
    mercy, _ = mint_party('Mercy Hospital.')
    mother, _ = mint_party('My mother.')
    u_mom = utter('My mother paid Mercy $300 for me.', '2026-07-01T09:00:00')
    p9 = mint_payment(u_mom)
    role('paid_by', mother, p9, u_mom)
    role('paid_to', mercy, p9, u_mom)
    check('Pm9: Rob asserts, the mother pays - paid_by is a role claim; the anchor names only the asserting act',
          p9.minted_by_id == u_mom.id and u_mom.origin_party_id == household.id
          and s.query(db.Proposition).filter_by(kind='paid_by', subject_party_id=mother.id, object_payment_id=p9.id).count() == 1)
    check('Pm9: a non-household individual is a minted party (the label is a naming matter, noted)',
          db.party_foundation(mother) == 'institution' and mother.minted_by_id is not None)
    u_cash = utter('I paid the plumber $180 in cash.', '2026-08-01T09:00:00')
    p11 = mint_payment(u_cash)
    check('Pm11: a payment with no transaction - no bank line will ever correspond; it is a payment',
          s.get(db.Payment, p11.id) is not None
          and s.query(db.Proposition).filter_by(kind='cleared', subject_payment_id=p11.id).count() == 0)
    n_pay = s.query(db.Payment).count()
    p_xfer = prop('cleared', object_state=db.PARTICIPANT_NONE, subject_party_id=bank.id,
                  content='TRANSFER TO SAVINGS -2,000.00', as_of='2026-08-15')
    evidence(p_xfer, reading=r_stmt)
    check('Pm12: a transaction with no payment - a bank line about nothing paid toward anything mints nothing',
          s.query(db.Payment).count() == n_pay and p_xfer.object_state == db.PARTICIPANT_NONE)

    print('\n8. Pm10 / Pm13 - autopay lines are candidates; retraction does not unmint\n')
    lines = [prop('cleared', object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=bank.id,
                  content=f'CHASE MTG {m}/3 -1,412.00', as_of=f'2026-{m:02d}-03') for m in (4, 5, 6)]
    for ln in lines:
        evidence(ln, reading=r_stmt)
    check('Pm10: three autopay lines are three candidates naming no referent; no payment was minted for any',
          all(ln.object_payment_id is None for ln in lines) and s.query(db.Payment).count() == n_pay)
    evidence(prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_paid.id),
             utterance=utter("That March payment wasn't toward the mortgage - it was the HELOC.", '2026-09-15T09:00:00'))
    check('Pm13: retracting the minting utterance leaves p1, its claims and its evidence in place - never removal',
          s.get(db.Payment, p1.id) is not None and s.get(db.Payment, p1.id).minted_by_id == u_paid.id
          and s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_paid.id).count() == 4
          and not db.payments_without_minting_utterance(s))

    print('\n9. Generic slots; artefact_concerns grows; absences; audits\n')
    # Item 6 pass A ruled payment_counteracts on the payment slots (RELATION_SEMANTICS.md A.6); the
    # role-shaped claims used here (paid_by, paid_to, toward) remain stand-ins - unruled by design.
    # ...and item 6 pass D ruled payment_in_respect_of on the payment subject slot (RELATION_SEMANTICS.md D.9)
    # - a payment -> expense relation; toward (payment -> obligation, D') is still a stand-in.
    check('payment slots are generic proposition participation - only payment_corresponds, payment_counteracts and payment_in_respect_of are ruled on them; paid_by / toward stay stand-ins',
          set(k for k, r in db.RULED_KINDS.items() if 'subject_payment_id' in r['subject']) == {db.PAYMENT_CORRESPONDS, db.PAYMENT_COUNTERACTS, db.PAYMENT_IN_RESPECT_OF}
          and 'paid_by' not in db.RULED_KINDS and 'toward' not in db.RULED_KINDS)
    receipt = held('h-receipt', '2026-03-03', chase, u_chase)
    evidence(prop(db.ARTEFACT_CONCERNS, subject_artefact_id=receipt.id, object_payment_id=p1.id),
             utterance=utter("That's the receipt for my March payment.", '2026-03-04T09:00:00'))
    check('artefact_concerns gained the payment object slot: a receipt (the payment\'s own record) concerns p1',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, object_payment_id=p1.id).count() == 1
          and _refused(s, db.Proposition(kind=db.ARTEFACT_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_artefact_id=receipt.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                         object_party_id=chase.id)))
    check('payment_corresponds is reflexive-refused and cross-type-refused',
          _refused(s, db.Proposition(kind=db.PAYMENT_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_payment_id=p1.id, object_state=db.PARTICIPANT_ESTABLISHED, object_payment_id=p1.id))
          and _refused(s, db.Proposition(kind=db.PAYMENT_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_payment_id=p1.id, object_state=db.PARTICIPANT_ESTABLISHED, object_obligation_id=o1.id)))
    check('DebtLedgerEntry, CheckingTransactionLink and ExpenseFundingAllocation are untouched and unmapped',
          {c.name for c in db.DebtLedgerEntry.__table__.columns} >= {'id', 'entry_type', 'amount'}
          and not any(hasattr(db, n) for n in ('payment_for_ledger_entry', 'backfill_payments', 'decompose_allocation')))
    check('every audit is empty',
          not db.payments_without_minting_utterance(s) and not db.obligations_without_minting_utterance(s)
          and not db.evidence_without_one_source(s) and not db.parties_without_one_anchor(s))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
