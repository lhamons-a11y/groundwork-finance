# -*- coding: utf-8 -*-
"""The obligation-identity fixture - the build gate over Ob1-Ob12.

`gw 2.0/OBLIGATION_IDENTITY.md` s8 (ruled s9, 2026-09-14):

    An obligation is a continuant minted by the household's individuating assertion. The anchor
    is structure plus a pointer to the minting utterance and nothing else. Every property -
    creditor, amount, kind, obligor, servicer, terms, account number, entitlement, balance -
    is a claim about it. It survives assignment, sale, write-off, recourse and restructure
    because none touches the anchor; it exists without a known creditor; it is never minted by
    a bill, a statement, a payment or an inference. The minting act is not the minted identity.

    A bill can describe a debt; only the household can say it owes one.

Domain kinds used here (entitled_party, services, obligated_on, instrument_kind, balance) are
STAND-INS - the obligation catalogue is not ruled; only obligation_corresponds is. Nothing here
derives disposition, entitlement, discharge or remaining.

What this build can and cannot exercise, stated so greenness is not over-read:

    Ob1  mint from "I have a mortgage with Chase"; descriptors are content   EXERCISED
    Ob2  a bill mints nothing; its claims carry candidates                    EXERCISED
    Ob3  assignment/sale: new dated claim, old remains, anchor untouched      EXERCISED (as_of vs recorded_at)
    Ob4  write-off leaves the anchor                                          EXERCISED (the residue stays unnamed)
    Ob5  recourse loop: three dated claims; payments never consulted          EXERCISED (no payment concept exists)
    Ob6  restructure: same O + terms claim, or a new O                        EXERCISED (the relation: tests/test_obligation_replaces_fixture.py)
    Ob7  two minted obligations correspond; never merged                      EXERCISED
    Ob8  joint obligor = two dated relations, not a column                    EXERCISED
    Ob9  identity without a creditor                                          EXERCISED
    Ob10 S3's false servicer claim retracted; O untouched                     EXERCISED
    Ob11 amount is never identity; competing balances, nothing chosen         EXERCISED
    Ob12 retracting the minting utterance does not unmint                     EXERCISED
    minting act != minted identity; one act may mint two                      EXERCISED
    D4 P-ack payment                                                          payment slice - tests/test_payment_identity_fixture.py
    artefact -> obligation about-ness                                        slice 8 - tests/test_artefact_concerns_fixture.py
    role period -> tests/test_role_period_fixture.py · restructure relation -> obligation_replaces
    DebtAccount decomposition                                                 NOT BUILT - fenced

Run:  python tests/test_obligation_identity_fixture.py
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


DESCRIPTORS = ('creditor', 'amount', 'balance', 'kind', 'instrument', 'obligor', 'servicer', 'status',
               'terms', 'account', 'name', 'entitled', 'carrier', 'paid', 'remaining')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_oblig_')
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
    kim = db.Person(display_name='Kim')
    s.add_all([rob, kim])
    s.commit()
    household, kim_party = rob.party, kim.party

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

    def prop(kind, object_state=db.PARTICIPANT_ESTABLISHED, **slots):
        p = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED,
                           object_state=object_state, **slots)
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

    def role(kind, party, obligation, as_of, utterance):
        # a stand-in dated role claim: subject the party, object the obligation, as_of the effective date
        p = prop(kind, subject_party_id=party.id, object_obligation_id=obligation.id, as_of=as_of)
        return evidence(p, utterance=utterance), p

    def about(kind, obligation, content, utterance, as_of=None):
        # a stand-in stance about the obligation: subject the obligation, no second participant
        p = prop(kind, object_state=db.PARTICIPANT_NONE, subject_obligation_id=obligation.id,
                 content=content, as_of=as_of)
        return evidence(p, utterance=utterance), p

    print('\n1. Ob1 - "I have a mortgage with Chase, ending 4471, about $180k": one act mints; the rest is claims\n')
    chase, u_chase = mint_party('Chase, my mortgage lender.')
    u_mint = utter('I have a mortgage with Chase - account ending 4471, about $180k.')
    o1 = mint_obligation(u_mint)
    check('the obligation exists under the utterance that minted it',
          o1.minted_by is u_mint and db.party_foundation(u_mint.origin) == 'person')
    check('the anchor is structure plus the pointer and nothing else',
          {c.name for c in db.Obligation.__table__.columns} == {'id', 'minted_by_id', 'created_at'})
    check('no descriptor lives on the anchor - creditor, amount, kind, account number are claims or content',
          not any(any(d in c.name for d in DESCRIPTORS) for c in db.Obligation.__table__.columns)
          and not any(hasattr(db.Obligation, d) for d in DESCRIPTORS))
    e_kind, p_kind = about('instrument_kind', o1, 'mortgage', u_mint)
    e_e, p_e = role('entitled_party', chase, o1, '2019-06-01', u_mint)
    e_bal, p_bal = about('balance', o1, '$180,000 (approx.)', u_mint, as_of='2026-03-10')
    check('the same act evidences claims ABOUT the obligation: instrument kind, entitled party, a balance testimony',
          s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_mint.id).count() == 3
          and p_kind.subject_obligation_id == o1.id and p_e.object_obligation_id == o1.id)
    check('"4471" and "$180k" are content - never identity, never a column',
          '4471' in u_mint.content and p_bal.content.startswith('$180') and
          not any('account' in c.name for c in db.Obligation.__table__.columns))
    check('an obligation without a minting utterance is refused',
          _refused(s, db.Obligation(), (ValueError, IntegrityError)))
    check('an obligation under an utterance that does not exist is refused',
          _refused(s, db.Obligation(minted_by_id=999999), (ValueError, IntegrityError)))

    print('\n2. The minting act is not the minted identity\n')
    check('the obligation is not the utterance: different tables, different ids, the utterance has its own life',
          o1.id != u_mint.id and 'obligations' != 'utterances'
          and s.get(db.Utterance, u_mint.id).content.startswith('I have a mortgage'))
    u_two = utter('I have two loans with Chase.')
    oa, ob = mint_obligation(u_two), mint_obligation(u_two)
    check('one act may mint two identities - minted_by is a pointer, not a unique key',
          oa.id != ob.id and oa.minted_by_id == ob.minted_by_id == u_two.id
          and not any(c.unique for c in db.Obligation.__table__.columns if c.name == 'minted_by_id'))
    check('the pointer is immutable - an obligation is never re-anchored to another act',
          _update_refused(s, o1, 'minted_by_id', u_two.id))

    print('\n3. Ob2 - a bill from Mercy: mints nothing; its claims carry candidates\n')
    mercy, u_mercy = mint_party('Mercy Hospital.')
    before = s.query(db.Obligation).count()
    bill = db.Artefact(held=True, content_hash='h-bill', as_of='2026-02-20')
    s.add(bill)
    s.commit()
    evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=bill.id, object_party_id=mercy.id), utterance=u_mercy)
    r_bill = db.Reading(artefact_id=bill.id, reader_process='pdf-parser/5', read_at=datetime(2026, 3, 1))
    s.add(r_bill)
    s.commit()
    p_read = prop('balance', object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=mercy.id,
                  content='$1,200 due', as_of='2026-02-20')
    evidence(p_read, reading=r_bill)
    check('encountering a bill mints no obligation',
          s.query(db.Obligation).count() == before)
    check('a claim read from the bill carries the obligation as NOT ESTABLISHED WITH CANDIDATES - the reader cannot say which',
          p_read.object_state == db.PARTICIPANT_CANDIDATES and p_read.object_obligation_id is None)
    u_er = utter("That's the ER visit - I owe Mercy for it.")
    o2 = mint_obligation(u_er)
    # Slice 8 retired "not built here" in place: the tie is artefact_concerns (tests/
    # test_artefact_concerns_fixture.py). Here none is asserted, and minting O2 asserted none.
    check('the household\'s assertion mints O2 and, by itself, ties no artefact to it (the tie is a separate claim, slice 8)',
          o2.minted_by is u_er and s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS).count() == 0)

    print('\n4. Ob3 - Chase assigns the mortgage to NewCo: a new dated claim; the old remains; the anchor is untouched\n')
    newco, _ = mint_party('NewCo Servicing LLC.')
    u_learned = utter('A letter says NewCo took over my mortgage back in March.', '2026-09-09T09:00:00')
    e_new, p_new = role('entitled_party', newco, o1, '2026-03-14', u_learned)
    check('the transition is a claim with as_of = effective date and the utterance\'s recorded_at = learned date - two coordinates',
          p_new.as_of == '2026-03-14' and u_learned.recorded_at.isoformat()[:10] != '2026-03-14'
          and u_learned.asserted_at.startswith('2026-09-09'))
    check('the earlier entitled-party claim remains - history, not removal',
          s.get(db.Proposition, p_e.id) is not None and s.get(db.Proposition, p_e.id).subject_party_id == chase.id)
    check('the obligation is the same row under the same minting utterance',
          s.get(db.Obligation, o1.id).minted_by_id == u_mint.id)
    check('which party is entitled NOW is not derived here - no accessor, no column',
          not any(hasattr(db, n) for n in ('entitled_party', 'current_creditor', 'carrier_of', 'who_is_entitled')))

    print('\n5. Ob4 / Ob5 - write-off and the recourse loop leave the anchor; payments are never consulted\n')
    about('creditor_stance', o1, 'written off', utter('Chase says it was written off.', '2026-10-01T09:00:00',),
          as_of='2026-09-30')
    check('Ob4: a write-off is a stance about the obligation at a date; the anchor is unchanged',
          s.get(db.Obligation, o1.id).minted_by_id == u_mint.id)
    prov, _ = mint_party('The provider.')
    fin, _ = mint_party('The financing party.')
    u_loop = utter('The financing company had it for a while, then the provider took it back.', '2026-11-01T09:00:00')
    role('entitled_party', prov, o2, '2026-03-01', u_loop)
    role('entitled_party', fin, o2, '2026-05-01', u_loop)
    role('entitled_party', prov, o2, '2026-10-01', u_loop)
    check('Ob5: provider -> financing party -> provider is three dated claims on ONE obligation',
          s.query(db.Proposition).filter_by(kind='entitled_party', object_obligation_id=o2.id).count() == 3
          and s.query(db.Obligation).filter_by(id=o2.id).count() == 1)
    # The payment slice (2026-09-14) retired the absence in place: a payment referent now exists,
    # and still nothing consults payment state for a transition - no accessor, no derivation.
    check('payment state is never consulted for a transition - no accessor or derivation exists (the payment referent now does)',
          'payments' in db.Base.metadata.tables
          and not any(hasattr(db, n) for n in ('transition_from_payments', 'entitled_after_payment',
                                               'carrier_from_payment_state', 'payment_state')))

    print('\n6. Ob6 - restructure: the household says which; both shapes are representable\n')
    u_terms = utter('Chase re-amortised the same loan over 30 years.', '2026-12-01T09:00:00')
    about('terms', o1, '30-year re-amortisation', u_terms, as_of='2026-11-15')
    check('same obligation, new terms: a dated terms claim on O1',
          s.query(db.Proposition).filter_by(kind='terms', subject_obligation_id=o1.id).count() == 1)
    u_refi = utter('I refinanced - the new loan paid off the old one.', '2027-01-05T09:00:00')
    o3 = mint_obligation(u_refi)
    check('a new obligation that settled the old: O3 minted by the household\'s assertion; O1 remains',
          o3.id != o1.id and s.get(db.Obligation, o1.id) is not None)
    # Item 6 pass B ruled the second arm's relation as obligation_replaces (RELATION_SEMANTICS.md B.7) -
    # so 'settles' / 'supersedes' stay non-kinds by ruling, not by omission; this fixture still asserts
    # nothing about the relation and mints O3 without one (the household need not assert it).
    # ...and pass C ruled obligation_in_respect_of on the same subject slot (RELATION_SEMANTICS.md C.9).
    check('the relation between O3 and O1 is ruled elsewhere (obligation_replaces) and not asserted here; no source-word kind exists; the obligation-subject kinds are exactly correspondence, replaces and in-respect-of',
          s.query(db.Proposition).filter(db.Proposition.kind.in_(('settles', 'replaces', 'obligation_supersedes',
                                                                 db.OBLIGATION_REPLACES))).count() == 0
          and set(k for k in db.RULED_KINDS if k.startswith('obligation_')) == {db.OBLIGATION_CORRESPONDS, db.OBLIGATION_REPLACES, db.OBLIGATION_IN_RESPECT_OF})

    print('\n7. Ob7 - "my Chase mortgage" (March) and "the 4471 loan" (June): two minted; corresponding; never merged\n')
    u_june = utter('The 4471 loan - about $178k now.', '2026-06-10T09:00:00')
    o_june = mint_obligation(u_june)
    check('two obligations, separately minted, separate referents',
          o_june.id != o1.id and db.referent(s, o1) == (db.REFERENT_SEPARATE, [o1.id], []))
    c = prop(db.OBLIGATION_CORRESPONDS, subject_obligation_id=o_june.id, object_obligation_id=o1.id,
             content='basis: account number 4471 in both assertions')
    evidence(c, reading=r_bill)      # a process noticing the match - a candidate, no party behind it
    check('an observed match (the account number) is a candidate only',
          db.referent(s, o1) == (db.REFERENT_CANDIDATES, [o1.id], [o_june.id]))
    evidence(c, utterance=utter('Yes - same loan.', '2026-06-11T09:00:00'))
    check('the household\'s answer establishes: O1 and O_june correspond; the referent contains both',
          db.referent(s, o1) == (db.REFERENT_CORRESPONDING, sorted([o1.id, o_june.id]), []))
    check('never merged: two rows, each under its own minting utterance; the claims about each stay where they were',
          s.get(db.Obligation, o_june.id).minted_by_id == u_june.id and s.get(db.Obligation, o1.id).minted_by_id == u_mint.id
          and s.query(db.Proposition).filter_by(kind='entitled_party', object_obligation_id=o1.id).count() == 2)
    check('obligation_corresponds is reflexive-refused and cross-type-refused like the others',
          _refused(s, db.Proposition(kind=db.OBLIGATION_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_obligation_id=o1.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_obligation_id=o1.id))
          and _refused(s, db.Proposition(kind=db.OBLIGATION_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_obligation_id=o1.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                         object_artefact_id=bill.id)))

    print('\n8. Ob8 / Ob9 - a joint obligor is two dated relations; identity without a creditor\n')
    u_joint = utter('Kim and I are both on the car loan.')
    o_car = mint_obligation(u_joint)
    role('obligated_on', household, o_car, '2025-01-01', u_joint)
    role('obligated_on', kim_party, o_car, '2025-01-01', u_joint)
    check('Ob8: whose obligation it is = two claims, not an obligor column',
          s.query(db.Proposition).filter_by(kind='obligated_on', object_obligation_id=o_car.id).count() == 2
          and not any('obligor' in c.name or 'person' in c.name or 'party' in c.name
                      for c in db.Obligation.__table__.columns))
    u_amb = utter('I owe someone for the ambulance - the letter did not say who.')
    o_amb = mint_obligation(u_amb)
    check('Ob9: an obligation with no entitled-party claim at all is a legitimate identity',
          s.get(db.Obligation, o_amb.id) is not None
          and s.query(db.Proposition).filter_by(kind='entitled_party', object_obligation_id=o_amb.id).count() == 0)

    print('\n9. Ob10 / Ob11 / Ob12 - a false relation retracted; competing balances; retracting the mint\n')
    s3, _ = mint_party('S3 Servicing.')
    u_s3 = utter('S3 services my mortgage.', '2026-04-01T09:00:00')
    role('services', s3, o1, '2026-04-01', u_s3)
    u_never = utter('S3 was never my servicer.', '2026-07-01T09:00:00')
    evidence(prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_s3.id),
             utterance=u_never)
    check('Ob10: the false servicer claim is retracted; O1, S3 the party, and the claim itself all remain',
          s.get(db.Obligation, o1.id) is not None and s.get(db.Party, s3.id) is not None
          and s.query(db.Proposition).filter_by(kind='services', object_obligation_id=o1.id).count() == 1)
    about('balance', o1, '$1,925', utter('The statement says $1,925.', '2026-08-01T09:00:00'), as_of='2026-07-31')
    about('balance', o1, '$1,900', utter('The portal showed $1,900.', '2026-08-01T10:00:00'), as_of='2026-07-31')
    check('Ob11: competing balances at one as_of are two claims; nothing chosen; amount is never identity',
          s.query(db.Proposition).filter_by(kind='balance', subject_obligation_id=o1.id, as_of='2026-07-31').count() == 2
          and not any(hasattr(db, n) for n in ('current_balance', 'balance_of', 'remaining_of')))
    u_never_had = utter("I never had that ambulance debt - I was confusing it with my brother's.", '2026-09-01T09:00:00')
    evidence(prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_amb.id),
             utterance=u_never_had)
    check('Ob12: retracting the minting utterance does not unmint - the obligation remains under it',
          s.get(db.Obligation, o_amb.id) is not None and s.get(db.Obligation, o_amb.id).minted_by_id == u_amb.id
          and not db.obligations_without_minting_utterance(s))

    print('\n10. What the identity satisfies, and what it does not\n')
    check('D5-shaped and D7-shaped claims are representable with the obligation as a structural participant',
          p_bal.subject_obligation_id == o1.id and p_new.object_obligation_id == o1.id)
    # Retired in place by the payment slice: D4 is now representable (tests/test_payment_identity_
    # fixture.py); what this fixture pins is that the OBLIGATION anchor gained nothing for it.
    check('D4 became representable through the payment slice, and the obligation anchor is unchanged by it',
          'subject_payment_id' in db.Proposition.SUBJECT_SLOTS
          and {c.name for c in db.Obligation.__table__.columns} == {'id', 'minted_by_id', 'created_at'})
    check('nothing derives disposition, entitlement, discharge or remaining from these claims',
          not any(hasattr(db, n) for n in ('disposition', 'discharge', 'remaining', 'entitlement_of', 'obligation_state')))
    check('DebtAccount is untouched and nothing maps it - the asserting party is not a fact in production',
          {c.name for c in db.DebtAccount.__table__.columns} >= {'id', 'name'}
          and not any(hasattr(db, n) for n in ('decompose_debt_account', 'backfill_obligations',
                                               'obligation_for_debt_account', 'synthesize_person')))
    check('every audit is empty',
          not db.obligations_without_minting_utterance(s) and not db.parties_without_one_anchor(s)
          and not db.evidence_without_one_source(s) and not db.people_without_party(s))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
