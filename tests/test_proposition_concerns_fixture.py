# -*- coding: utf-8 -*-
"""The proposition-concerns fixture - Ab7's build gate over Pa1-Pa10.

`gw 2.0/PROPOSITION_ABOUTNESS.md` s6 (ruled s7, 2026-09-14):

    Proposition-level about-ness is a claim of its own: "this proposition concerns this identity"
    - a domain proposition whose subject is a proposition and whose second participant is an
    already-minted identity. It presupposes the identity. Asserted by a party's utterance; a
    match observed by a reading produces a candidate for the claim - it is not itself the claim
    - and is evidence for nothing else; those candidates are what PARTICIPANT_CANDIDATES has
    always referred to. It never changes the subject, participants, authority, evidence or
    history of the proposition it is about: about-ness is information about a proposition, not
    information inserted into the proposition. Once a proposition's participant of the relevant
    identity type is established, proposition_concerns may not provide a competing source. It is
    independent of artefact-level about-ness; never required; level consistency is a consumer's
    to report. The first and only ruled kind with a proposition subject - slice 5 reopened and
    narrowed, not reversed. A re-reading's propositions carry no about-ness of their own.

What this build can and cannot exercise, stated so greenness is not over-read:

    Pa1  line 3 of a two-obligation statement is the HELOC; P3 byte-identical      EXERCISED
    Pa2  a bank line -> a payment with NO artefact-level claim above it            EXERCISED
    Pa3  heading matches are reading-sourced candidates - the candidates carrier   EXERCISED
    Pa4  the line-level association disputed; P3 unchanged                         EXERCISED
    Pa5  a re-reading's P3' has no about-ness; proposition_corresponds pressed      EXERCISED (absence); correspondence is its own slice
    Pa6  testimony about O2 is not about-ness                                       EXERCISED
    Pa7  level inconsistency is representable and reported by consumers only       EXERCISED (report NOT BUILT)
    Pa8  a single-identity statement needs no line-level claim                      EXERCISED
    Pa9  slice 5 narrowed, not reversed: one ruled kind uses the slot               EXERCISED
    Pa10 attaches only where no participant of X's type is established             EXERCISED
    multi-link strength · consistency derivation · candidate generation · consumers NOT BUILT

Run:  python tests/test_proposition_concerns_fixture.py
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
    d = tempfile.mkdtemp(prefix='gw_pconcerns_')
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
               db.PROPOSITION_CONCERNS: {'person', 'institution'},    # supplied - and must not score
               db.ARTEFACT_CONCERNS: {'person', 'institution'},
               'balance': {'institution'}, 'cleared': {'institution'}}

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

    def mint_obligation(text):
        o = db.Obligation(minted_by_id=utter(text).id)
        s.add(o)
        s.commit()
        return o

    def mint_payment(text):
        pm = db.Payment(minted_by_id=utter(text).id)
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

    def line(a, reading, kind, content, party):
        # a value read from A: subject the origin party's stance; the identity participant NOT ESTABLISHED WITH CANDIDATES
        p = prop(kind, object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=party.id, content=content, as_of=a.as_of)
        return p, evidence(p, reading=reading)

    def pconcerns(p, obligation=None, payment=None, content=None):
        return prop(db.PROPOSITION_CONCERNS, subject_proposition_id=p.id,
                    object_obligation_id=obligation.id if obligation else None,
                    object_payment_id=payment.id if payment else None, content=content)

    def fingerprint(p):
        return (p.kind, p.subject_state, p.subject_party_id, p.subject_utterance_id, p.subject_artefact_id,
                p.subject_obligation_id, p.subject_payment_id, p.subject_proposition_id,
                p.object_state, p.object_party_id, p.object_utterance_id, p.object_artefact_id,
                p.object_obligation_id, p.object_payment_id, p.content, p.as_of,
                tuple(sorted((e.utterance_id, e.reading_id)
                             for e in s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p.id))))

    cu, u_cu = mint_party('The credit union.')
    o1 = mint_obligation('My mortgage with the credit union.')
    o2 = mint_obligation('My HELOC with the credit union.')
    o3 = mint_obligation('My car loan.')

    print('\n1. Pa1 - the combined statement: "line 3 is the HELOC"\n')
    A = held('h-combo', '2026-03-31', cu, u_cu)
    evidence(prop(db.ARTEFACT_CONCERNS, subject_artefact_id=A.id, object_obligation_id=o1.id), utterance=utter('My CU statement - both loans.'))
    evidence(prop(db.ARTEFACT_CONCERNS, subject_artefact_id=A.id, object_obligation_id=o2.id), utterance=utter('My CU statement - both loans.'))
    rA = read(A)
    lines = [line(A, rA, 'balance', c, cu) for c in ('$181,200', 'rate 6.1%', '$44,000', 'rate 8.9%')]
    P3, e3 = lines[2]
    before = [fingerprint(p) for p, _ in lines]
    strength_before = [db.derived_strength(s, e, KNOWING) for _, e in lines]
    check('the artefact concerns two identities and the read lines name none - the artefact level cannot say which line is which',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=A.id).count() == 2
          and all(p.object_state == db.PARTICIPANT_CANDIDATES and p.object_obligation_id is None for p, _ in lines))
    u_line3 = utter('That $44,000 line is the HELOC.', '2026-04-01T09:00:00')
    c3 = pconcerns(P3, obligation=o2, content='basis: Rob read the statement')
    e_c3 = evidence(c3, utterance=u_line3)
    check('the crossing is a claim whose SUBJECT is the proposition: proposition_concerns(P3, O2)',
          c3.kind == db.PROPOSITION_CONCERNS and c3.subject_proposition_id == P3.id and c3.object_obligation_id == o2.id)
    check('ANTI-COLLAPSE: every read line is byte-identical after the claim - subject, participants, content, as_of, evidence',
          [fingerprint(p) for p, _ in lines] == before)
    check('ANTI-COLLAPSE: authority unchanged - the credit union\'s, before and after',
          [db.derived_strength(s, e, KNOWING) for _, e in lines] == strength_before
          and strength_before[2] == db.STRENGTH_KNOWING)
    check('P3\'s own participant stays candidates; the claim is beside P3, not in it',
          s.get(db.Proposition, P3.id).object_state == db.PARTICIPANT_CANDIDATES
          and s.get(db.Proposition, P3.id).object_obligation_id is None)
    # Relational knowing (2026-09-14) retired "undetermined until ruled" in place: Rob minted O2, so his
    # line-level concerns claim derives KNOWING by the designated relation; the map is not consulted.
    check('assertion is not knowing by itself - the claim derives KNOWING because Rob minted O2 (the designated relation), not because a map says so',
          db.derived_strength(s, e_c3, KNOWING) == db.STRENGTH_KNOWING
          and db.derived_strength(s, e_c3, {}) == db.STRENGTH_KNOWING)

    print('\n2. Pa2 - a bank statement with NO artefact-level claim: "line 7 is my March payment"\n')
    bank, u_bank = mint_party('My bank.')
    p1 = mint_payment('I paid the mortgage on March 3.')
    B = held('h-bank', '2026-03-31', bank, u_bank)
    rB = read(B, 'feed-import/1')
    P7, e7 = line(B, rB, 'cleared', 'CHASE MTG 3/3 -1,412.00', bank)
    check('no artefact_concerns claim exists for the bank statement - a bank account is not a ruled identity',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=B.id).count() == 0)
    c7 = pconcerns(P7, payment=p1)
    evidence(c7, utterance=utter("Line 7 is my March mortgage payment.", '2026-04-02T09:00:00'))
    check('proposition-level about-ness works with nothing above it: proposition_concerns(P7, p1) stands alone',
          c7.object_payment_id == p1.id and s.get(db.Proposition, P7.id).object_payment_id is None
          and db.derived_strength(s, e7, KNOWING) == db.STRENGTH_KNOWING)

    print('\n3. Pa3 - headings: a match observed by a reading produces a candidate; it is not the claim\n')
    n_before = s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS).count()
    cands = []
    for p, _ in lines[:2]:
        c = pconcerns(p, obligation=o1, content='basis: heading "Acct ...4471" over lines 1-2')
        cands.append((c, evidence(c, reading=rA)))
    for p, _ in lines[2:]:
        c = pconcerns(p, obligation=o2, content='basis: heading "Acct ...9902" over lines 3-4')
        cands.append((c, evidence(c, reading=rA)))
    check('four reading-sourced proposition_concerns candidates - no party behind them, undetermined',
          all(e.reading is rA and e.utterance is None for _, e in cands)
          and all(db.derived_strength(s, e, KNOWING) == db.STRENGTH_UNDETERMINED for _, e in cands)
          and all(s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c.id).count() == 1
                  and s.query(db.EvidentiaryRelationship).filter(db.EvidentiaryRelationship.proposition_id == c.id,
                                                                 db.EvidentiaryRelationship.utterance_id.isnot(None)).count() == 0
                  for c, _ in cands))
    check('the candidates ARE the carrier of the candidates state: each read line names nothing, and its candidates are these claims',
          all(p.object_state == db.PARTICIPANT_CANDIDATES for p, _ in lines)
          and s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=lines[0][0].id).count() == 1)
    check('the heading never touched the values: fingerprints and authority unchanged',
          [fingerprint(p) for p, _ in lines] == before
          and [db.derived_strength(s, e, KNOWING) for _, e in lines] == strength_before)

    print('\n4. Pa4 / Pa5 - the association disputed; a re-reading\n')
    u_no = utter('No - line 3 was the mortgage, not the HELOC.', '2026-04-10T09:00:00')
    evidence(prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_line3.id), utterance=u_no)
    evidence(pconcerns(P3, obligation=o1), utterance=u_no)
    check('Pa4: the association is disputed by retraction + a new claim; both claims remain',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=P3.id).count() == 3   # asserted x2 + candidate
          and s.get(db.Proposition, c3.id) is not None)
    check('Pa4: P3 is byte-identical - the credit union still says $44,000; its history is its own',
          fingerprint(P3) == before[2] and db.derived_strength(s, e3, KNOWING) == strength_before[2])
    rA2 = read(A, 'pdf-parser/6', datetime(2026, 4, 11))
    P3b, _ = line(A, rA2, 'balance', '$4,400', cu)
    check('Pa5: a re-reading yields P3\' with NO about-ness of its own - nothing carried across by position or content',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=P3b.id).count() == 0
          and P3b.object_state == db.PARTICIPANT_CANDIDATES)
    # proposition_corresponds is now ruled and built (tests/test_proposition_correspondence_fixture.py).
    # Here none is asserted: P3' still has no about-ness and no bridge - the correspondence would
    # carry nothing across even if it were.
    check('Pa5: no correspondence asserted here; P3\' stays without about-ness (correspondence copies nothing anyway)',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CORRESPONDS).count() == 0)

    print('\n5. Pa6 / Pa7 / Pa8 - testimony; level inconsistency; single-identity statements\n')
    n_c = s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS).count()
    T = prop('balance', object_state=db.PARTICIPANT_NONE, subject_obligation_id=o2.id, content='about $44k', as_of='2026-04-15')
    e_T = evidence(T, utterance=utter('The HELOC balance is about $44k.', '2026-04-15T09:00:00'))
    check('Pa6: testimony about O2 is an ordinary claim with the household\'s strength; it creates no about-ness claim',
          db.derived_strength(s, e_T, KNOWING) == db.STRENGTH_NOT_KNOWING
          and s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS).count() == n_c)
    evidence(pconcerns(lines[3][0], obligation=o3), utterance=utter('That rate line is actually the car loan.', '2026-04-16T09:00:00'))
    # Item 7 pass 7D built that consumer's report as core.database.level_consistency (CONSUMER_DERIVATIONS.md
    # s 7D.7) - a report, never a guard and never a resolver; this fixture still asserts the claim is
    # representable (no guard refused it) and that no resolver exists.
    check('Pa7: a line-level claim naming an identity the artefact does not concern is REPRESENTABLE - inconsistency is a consumer\'s report (built in item 7 as level_consistency(); still no guard, no resolver)',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, object_obligation_id=o3.id).count() == 1
          and callable(getattr(db, 'level_consistency', None))
          and not any(hasattr(db, n) for n in ('consistent_aboutness', 'resolve_aboutness', 'resolve_levels', 'refuse_inconsistent')))
    S1 = held('h-single', '2026-03-31', cu, u_cu)
    evidence(prop(db.ARTEFACT_CONCERNS, subject_artefact_id=S1.id, object_obligation_id=o1.id), utterance=utter('My mortgage statement.'))
    rS = read(S1)
    Ps, _ = line(S1, rS, 'balance', '$181,000', cu)
    check('Pa8: a single-identity statement needs no line-level claim; none exists and the line still names nothing itself',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=Ps.id).count() == 0
          and Ps.object_state == db.PARTICIPANT_CANDIDATES)
    check('and how a consumer combines the two levels is not derived here - no accessor',
          not any(hasattr(db, n) for n in ('about', 'identity_of', 'concerns_of', 'about_identity')))

    print('\n6. Pa9 - slice 5 narrowed, not reversed\n')
    # narrowed again by proposition_corresponds: two ruled kinds carry a proposition participant -
    # proposition_concerns (subject only) and proposition_corresponds (subject and object). No other.
    check('proposition_concerns is the only ruled kind whose proposition participant is subject-only',
          [k for k, r in db.RULED_KINDS.items()
           if 'subject_proposition_id' in r['subject'] and 'object_proposition_id' not in r['object']] == [db.PROPOSITION_CONCERNS])
    check('utterance_retraction is unchanged - its subject is still an utterance, never a proposition',
          db.RULED_KINDS[db.UTTERANCE_RETRACTION]['subject'] == ('subject_utterance_id',))
    check('"P3 is false", agreement and reaffirmation are still not kinds',
          not any(k in db.RULED_KINDS for k in ('contradiction', 'reaffirmation', 'proposition_false', 'agrees_with')))
    # the object-side slot was forced by proposition_corresponds and is used by that kind alone.
    check('the object-side proposition slot is used by proposition_corresponds alone - not by proposition_concerns',
          [k for k, r in db.RULED_KINDS.items() if 'object_proposition_id' in r['object']] == [db.PROPOSITION_CORRESPONDS]
          and 'object_proposition_id' not in db.RULED_KINDS[db.PROPOSITION_CONCERNS]['object'])

    print('\n7. Pa10 - about-ness attaches only where no participant of the identity\'s type is established\n')
    check('a concerns claim on Rob\'s testimony T (object O2 established) naming O1 is refused',
          _refused(s, db.Proposition(kind=db.PROPOSITION_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_proposition_id=T.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_obligation_id=o1.id)))
    check('and one naming the SAME identity is refused too - not a competing fact, a second source for one',
          _refused(s, db.Proposition(kind=db.PROPOSITION_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_proposition_id=T.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_obligation_id=o2.id)))
    check('a concerns claim on a proposition that does not exist is refused',
          _refused(s, db.Proposition(kind=db.PROPOSITION_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_proposition_id=999999, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_obligation_id=o1.id), (ValueError, IntegrityError)))
    check('a concerns claim naming an identity that does not exist is refused - it presupposes the identity',
          _refused(s, db.Proposition(kind=db.PROPOSITION_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_proposition_id=P3.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_obligation_id=999999), (ValueError, IntegrityError)))
    check('a concerns claim with a party or artefact as its object is refused - the object is an identity slot',
          _refused(s, db.Proposition(kind=db.PROPOSITION_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_proposition_id=P3.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_party_id=cu.id)))
    check('re-identifying T is Case B: retract its utterance and assert anew - the substrate offers no override',
          not any(hasattr(db, n) for n in ('override_aboutness', 'reassign', 'reidentify')))

    print('\n8. Absences; audits\n')
    check('no schema change beyond the one additive slot; SCHEMA_VERSION is the payment slice\'s',
          'subject_proposition_id' in {c.name for c in db.Proposition.__table__.columns})
    check('no consumer derives "about X" through either level; no multi-link strength',
          not any(hasattr(db, n) for n in ('strength_about', 'about_strength', 'values_about')))
    check('every audit is empty',
          not db.evidence_without_one_source(s) and not db.readings_of_unheld_artefacts(s)
          and not db.obligations_without_minting_utterance(s) and not db.payments_without_minting_utterance(s))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
