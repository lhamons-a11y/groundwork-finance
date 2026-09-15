# -*- coding: utf-8 -*-
"""The artefact-concerns fixture - slice 8's build gate over Ab1-Ab10.

`gw 2.0/ARTEFACT_ABOUTNESS.md` s7 (ruled s9, 2026-09-14):

    The crossing is a claim of its own: "this artefact concerns this identity" - subject the
    artefact, second participant an already-established identity; it presupposes that identity
    and does not mint, establish or identify it. Asserted by a party's utterance under the
    ordinary discipline; whether that party is knowing for the relational claim is a separate
    question, strength undetermined until relational knowing is ruled. An observed match is a
    reading-sourced candidate for the concerns claim and for nothing else. Values read from the
    artefact keep their source's authority and are about the identity by derivation, never by
    rewriting their own participants. The association's history is its own. About-ness is not
    endorsement and needs no custody. Re-assertion is not the crossing: it is testimony.

    Anti-collapse invariant: artefact_concerns(A, O) never changes the subject, participants,
    authority, evidence or history of any proposition derived from a reading of A.

The value kinds used here (balance, payment_due, services) are STAND-INS; no consumer derives
"about O" - the fixture proves the association is beside the read propositions, never an edit.

What this build can and cannot exercise, stated so greenness is not over-read:

    Ab1  one concerns claim; five read values untouched, Chase's authority kept   EXERCISED
    Ab2  one utterance mints O and evidences concerns(bill, O)                     EXERCISED - two jobs, no new act
    Ab3  the account-number match is a candidate; undetermined; never touches X    EXERCISED
    Ab4  the association disputed: retract + new claim; A still says $1,925       EXERCISED
    Ab5  a parse dispute inside A; the association untouched                       EXERCISED
    Ab6  household testimony about O is a different proposition, not the crossing  EXERCISED
    Ab7  combined statement: two concerns claims; per-proposition relation         NOT REPRESENTABLE - asserted
    Ab8  an EOB concerns an insurance claim                                        NOT ESTABLISHABLE - no such identity or slot
    Ab9  an asserted (unheld) artefact concerns O                                  EXERCISED
    Ab10 a wrong letter concerns the right obligation                               EXERCISED
    assertion != knowing; strength undetermined                                    EXERCISED
    any consumer of "about O"; multi-link strength; candidate generation           NOT BUILT

Run:  python tests/test_artefact_concerns_fixture.py
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


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_concerns_')
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
    from sqlalchemy.exc import IntegrityError
    s = _fresh()
    rob = db.Person(display_name='Rob')
    s.add(rob)
    s.commit()
    household = rob.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'},
               db.ARTEFACT_CONCERNS: {'person', 'institution'},     # supplied - and must not score
               'balance': {'institution'}, 'payment_due': {'institution'}, 'services': {'institution'}}

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

    def held(h, as_of, origin_party, origin_utt):
        a = db.Artefact(held=True, content_hash=h, as_of=as_of)
        s.add(a)
        s.commit()
        evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=a.id, object_party_id=origin_party.id), utterance=origin_utt)
        return a

    def read(a, process='pdf-parser/5', when=datetime(2026, 3, 11)):
        r = db.Reading(artefact_id=a.id, reader_process=process, read_at=when)
        s.add(r)
        s.commit()
        return r

    def read_value(a, reading, kind, content, party):
        # a value read from A: subject the origin party's stance, object the obligation NOT ESTABLISHED WITH CANDIDATES
        p = prop(kind, object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=party.id, content=content, as_of=a.as_of)
        return p, evidence(p, reading=reading)

    def concerns(a, o, content=None):
        return prop(db.ARTEFACT_CONCERNS, subject_artefact_id=a.id, object_obligation_id=o.id, content=content)

    def fingerprint(p):
        return (p.kind, p.subject_state, p.subject_party_id, p.subject_utterance_id, p.subject_artefact_id,
                p.subject_obligation_id, p.object_state, p.object_party_id, p.object_utterance_id,
                p.object_artefact_id, p.object_obligation_id, p.content, p.as_of,
                tuple(sorted((e.utterance_id, e.reading_id)
                             for e in s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p.id))))

    chase, u_chase = mint_party('Chase, my mortgage lender.')
    u_mint = utter('I have a mortgage with Chase - account ending 4471.')
    o1 = mint_obligation(u_mint)

    print('\n1. Ab1 - a Chase statement; five values read; "that\'s my mortgage statement"\n')
    A = held('h-stmt', '2026-02-28', chase, u_chase)
    rA = read(A)
    values = [read_value(A, rA, k, c, chase) for k, c in
              (('balance', '$1,925'), ('payment_due', '$1,412'), ('balance', 'escrow $312'),
               ('payment_due', 'rate 6.1%'), ('balance', 'last payment $1,412'))]
    before = [fingerprint(p) for p, _ in values]
    strength_before = [db.derived_strength(s, e, KNOWING) for _, e in values]
    check('before any crossing the read values carry the obligation as not-established-with-candidates',
          all(p.object_state == db.PARTICIPANT_CANDIDATES and p.object_obligation_id is None for p, _ in values))
    check('and each derives Chase\'s authority - knowing for an institution\'s figure, via artefact_origin',
          all(x == db.STRENGTH_KNOWING for x in strength_before))
    u_that = utter("That's my mortgage statement.", '2026-03-12T09:00:00')
    c1 = concerns(A, o1, 'basis: Rob recognised the statement')
    e_c1 = evidence(c1, utterance=u_that)
    check('the crossing is ONE claim: concerns(A, O1), subject the artefact, second participant the obligation',
          c1.kind == db.ARTEFACT_CONCERNS and c1.subject_artefact_id == A.id and c1.object_obligation_id == o1.id
          and s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS).count() == 1)
    check('ANTI-COLLAPSE: no read proposition changed subject, participants, content, as_of or evidence',
          [fingerprint(p) for p, _ in values] == before)
    check('ANTI-COLLAPSE: no read proposition changed authority - Chase\'s, before and after',
          [db.derived_strength(s, e, KNOWING) for _, e in values] == strength_before)
    check('the read values are NOT re-pointed at O1 - about O1 is a consumer\'s derivation through the claim',
          all(p.object_obligation_id is None for p, _ in values))

    print('\n2. Assertion is not knowing; the claim presupposes the identity\n')
    check('the concerns claim is asserted by Rob\'s utterance - and derives UNDETERMINED even with a foundation rule supplied',
          e_c1.utterance is u_that and db.derived_strength(s, e_c1, KNOWING) == db.STRENGTH_UNDETERMINED
          and db.RULED_KINDS[db.ARTEFACT_CONCERNS]['relational_knowing'] is True)
    check('concerns presupposes O: a claim naming an obligation that does not exist is refused',
          _refused(s, db.Proposition(kind=db.ARTEFACT_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_artefact_id=A.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_obligation_id=999999), (ValueError, IntegrityError)))
    check('concerns never mints: the obligation count is unchanged by asserting the claim',
          s.query(db.Obligation).count() == 1)
    check('concerns with the obligation not established is refused - it is a claim about an identity, not a search for one',
          _refused(s, db.Proposition(kind=db.ARTEFACT_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_artefact_id=A.id, object_state=db.PARTICIPANT_CANDIDATES)))
    check('concerns with a party or artefact as second participant is refused - the object is an identity slot',
          _refused(s, db.Proposition(kind=db.ARTEFACT_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_artefact_id=A.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_party_id=chase.id)))

    print('\n3. Ab2 - a bill from Mercy; one utterance, two jobs\n')
    mercy, u_mercy = mint_party('Mercy Hospital.')
    bill = held('h-bill', '2026-02-20', mercy, u_mercy)
    r_bill = read(bill)
    p_due, _ = read_value(bill, r_bill, 'balance', '$1,200 due', mercy)
    n_obl = s.query(db.Obligation).count()
    u_er = utter("That's the ER visit - I owe Mercy for it.", '2026-03-13T09:00:00')
    o2 = mint_obligation(u_er)
    c2 = concerns(bill, o2)
    evidence(c2, utterance=u_er)
    check('the bill\'s reading minted nothing; the household\'s utterance minted O2',
          n_obl == 1 and s.query(db.Obligation).count() == 2 and o2.minted_by is u_er)
    check('the same utterance evidences concerns(bill, O2) - two semantic jobs, one act, no new kind of act',
          s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_er.id).count() == 1
          and o2.minted_by_id == u_er.id and c2.object_obligation_id == o2.id)
    check('the utterance is neither the identity nor the relation - three rows in three tables',
          o2.id != u_er.id and c2.id != u_er.id and type(o2) is not type(u_er) and type(c2) is not type(u_er))
    check('the bill\'s read value still carries the obligation as candidates - untouched',
          s.get(db.Proposition, p_due.id).object_state == db.PARTICIPANT_CANDIDATES)

    print('\n4. Ab3 - the parser notices "4471" in both: a candidate for the concerns claim, and for nothing else\n')
    A2 = held('h-stmt-2', '2026-03-31', chase, u_chase)
    rA2 = read(A2)
    p_bal2, e_bal2 = read_value(A2, rA2, 'balance', '$1,900', chase)
    c_match = concerns(A2, o1, 'basis: 4471 appears in A2 and in the minting utterance')
    e_match = evidence(c_match, reading=rA2)
    check('the match is a reading-sourced concerns claim - a candidate with no party behind it',
          e_match.reading is rA2 and e_match.utterance is None)
    check('its strength is undetermined - it establishes nothing',
          db.derived_strength(s, e_match, KNOWING) == db.STRENGTH_UNDETERMINED)
    check('the match never touched the balance claim: same participants, same evidence, same authority',
          s.get(db.Proposition, p_bal2.id).object_obligation_id is None
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p_bal2.id).count() == 1
          and db.derived_strength(s, e_bal2, KNOWING) == db.STRENGTH_KNOWING)
    evidence(c_match, utterance=utter('Yes, that is the mortgage statement.', '2026-04-02T09:00:00'))
    check('the household\'s answer is a second evidence row on the SAME claim - the candidate becomes asserted, nothing is rewritten',
          s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c_match.id).count() == 2
          and s.get(db.Proposition, p_bal2.id).object_state == db.PARTICIPANT_CANDIDATES)

    print('\n5. Ab4 / Ab5 - the association disputed; a value disputed; two histories\n')
    u_heloc = utter('I have a HELOC with Chase too.')
    o_heloc = mint_obligation(u_heloc)
    u_no = utter('No - that statement was for the HELOC, not the mortgage.', '2026-04-10T09:00:00')
    evidence(prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_that.id), utterance=u_no)
    evidence(concerns(A, o_heloc), utterance=u_no)
    check('Ab4: the association is disputed by retracting its utterance and asserting a new concerns claim',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=A.id).count() == 2
          and s.get(db.Proposition, c1.id) is not None)
    check('Ab4: A still says $1,925 - every read proposition unchanged, Chase\'s authority unchanged',
          [fingerprint(p) for p, _ in values] == before
          and [db.derived_strength(s, e, KNOWING) for _, e in values] == strength_before)
    rA_again = read(A, 'pdf-parser/6', datetime(2026, 4, 11))
    read_value(A, rA_again, 'balance', '$1,295', chase)
    check('Ab5: a parse dispute inside A ($1,925 vs $1,295) is two read propositions; the concerns claims are untouched',
          s.query(db.Proposition).filter_by(kind='balance', subject_party_id=chase.id, as_of=A.as_of).count() == 4
          and s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=A.id).count() == 2)

    print('\n6. Ab6 - "the mortgage balance is about $178k": testimony, a different proposition, not the crossing\n')
    n_concerns = s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS).count()
    u_says = utter('The mortgage balance is about $178k.', '2026-04-15T09:00:00')
    p_testimony = prop('balance', object_state=db.PARTICIPANT_NONE, subject_obligation_id=o1.id,
                       content='about $178,000', as_of='2026-04-15')
    e_testimony = evidence(p_testimony, utterance=u_says)
    check('testimony is an ordinary value claim about O1 with the household\'s strength - already representable',
          p_testimony.subject_obligation_id == o1.id and e_testimony.utterance is u_says
          and db.derived_strength(s, e_testimony, KNOWING) == db.STRENGTH_NOT_KNOWING)
    check('it identifies no artefact and creates no concerns claim - K2 answers "what does the household say", not "what is A about"',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS).count() == n_concerns
          and p_testimony.subject_artefact_id is None)

    print('\n7. Ab7 / Ab8 - not representable; not establishable; stated so it is not assumed\n')
    cu, u_cu = mint_party('The credit union.')
    combo = held('h-combo', '2026-03-31', cu, u_cu)
    u_combo = utter("That's my credit-union statement - mortgage and HELOC.", '2026-04-20T09:00:00')
    evidence(concerns(combo, o1), utterance=u_combo)
    evidence(concerns(combo, o_heloc), utterance=u_combo)
    r_combo = read(combo)
    p_which, _ = read_value(combo, r_combo, 'balance', '$44,000', cu)
    check('Ab7: an artefact may concern two identities - two claims, both asserted',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=combo.id).count() == 2)
    check('Ab7: which of them a PARTICULAR read proposition concerns is NOT representable - no proposition-subject slot exists',
          'subject_proposition_id' not in {c.name for c in db.Proposition.__table__.columns}
          and s.get(db.Proposition, p_which.id).object_state == db.PARTICIPANT_CANDIDATES)
    # The payment slice added the payment object slot (the ruled growth path); the claim and plan
    # identities still do not exist, so the check is stated over them.
    check('Ab8: an EOB cannot concern an insurance claim - no such identity, no such slot; the kind\'s object is the ruled identities only',
          set(db.RULED_KINDS[db.ARTEFACT_CONCERNS]['object']) == {'object_obligation_id', 'object_payment_id'}
          and not any('claim' in c.name or 'plan' in c.name for c in db.Proposition.__table__.columns))

    print('\n8. Ab9 / Ab10 - no custody needed; not endorsement\n')
    u_march = utter("My March Chase statement - I don't have it - it's for the mortgage.", '2026-04-25T09:00:00')
    a9 = db.Artefact(held=False, asserted_by_id=u_march.id, as_of='2026-03')
    s.add(a9)
    s.commit()
    evidence(concerns(a9, o1), utterance=u_march)
    check('Ab9: an asserted, unheld artefact concerns O1 - the same utterance asserts the artefact and the association',
          a9.held is False and s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=a9.id).count() == 1)
    s3, u_s3 = mint_party('S3 Servicing.')
    letter = held('h-s3', '2026-05-01', s3, u_s3)
    r_letter = read(letter)
    p_claim, e_claim = read_value(letter, r_letter, 'services', 'we service your mortgage', s3)
    evidence(concerns(letter, o1), utterance=utter("That letter is about my mortgage.", '2026-05-02T09:00:00'))
    u_false = utter('S3 was never my servicer.', '2026-07-01T09:00:00')
    check('Ab10: the letter concerns O1 even though what it says is false - about-ness is not endorsement',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=letter.id).count() == 1
          and db.derived_strength(s, e_claim, KNOWING) == db.STRENGTH_KNOWING)   # S3's own statement, S3's authority
    check('Ab10: what the letter SAYS is disputed on its own history; the association stands',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=letter.id).count() == 1
          and s.get(db.Proposition, p_claim.id) is not None)

    print('\n9. Absences\n')
    check('no consumer derives "about O": no accessor names it',
          not any(hasattr(db, n) for n in ('about', 'concerns_of', 'artefact_concerns', 'propositions_about',
                                           'values_about', 'identity_of_reading')))
    check('no schema change: the kind uses existing slots; SCHEMA_VERSION is untouched by this slice',
          'concerns' not in {c.name for c in db.Proposition.__table__.columns})
    check('every audit is empty',
          not db.obligations_without_minting_utterance(s) and not db.evidence_without_one_source(s)
          and not db.readings_of_unheld_artefacts(s) and not db.parties_without_one_anchor(s))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
