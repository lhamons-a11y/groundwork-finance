# -*- coding: utf-8 -*-
"""The proposition-correspondence fixture - the build gate over Pc1-Pc10.

`gw 2.0/PROPOSITION_CORRESPONDENCE.md` s6 (ruled s7, 2026-09-14):

    A correspondence between propositions asserts that two separately minted propositions are
    two observations or recordings of one claim. Slice 4's shape, a fifth type: established only
    by a party's utterance; a match observed by a reading may produce a candidate - the
    observation is not itself the claim; the referent is derived; never merged, never re-pointed;
    contested when its establishing utterance is disputed. Contents and kinds may differ - that
    difference is the parse dispute, made computable and never resolved. Not agreement, not
    shared subject, not the entry path's reuse of one row, not replacement, and not about-ness
    carrying: the substrate copies nothing across corresponding propositions. It forces
    object_proposition_id, used by this kind alone; g1 refuses a correspondence whose already-
    established same-type structural participants explicitly disagree - inspecting established
    participants only. Strength undetermined.

What this build can and cannot exercise, stated so greenness is not over-read:

    Pc1  two readings, two contents, one claim: candidate then established; dispute computable   EXERCISED
    Pc2  two readings agree: corresponding - still one source (derivation NOT BUILT)             EXERCISED (structure)
    Pc3  P3 concerns O2; P3' corresponds; nothing copied to P3'                                  EXERCISED
    Pc4  X8 testimony vs P-subject: representable-but-wrong; g1 does not see it                  EXERCISED
    Pc5  "said twice" row reuse is identity; a mis-individuation is repaired, never merged        EXERCISED
    Pc6  kinds differ across readings: representable; no kind guard                              EXERCISED
    Pc7  correspondence between concerns claims                                                  NOT EXERCISED (unforced)
    Pc8  the establishing utterance retracted -> contested                                       EXERCISED
    Pc9  transitivity: the referent is the connected component                                   EXERCISED
    Pc10 the pipeline's monthly re-parse: candidates only; nothing carried                       EXERCISED
    g1   established same-type participants disagreeing -> refused; nothing else inspected       EXERCISED
    parse-dispute / independence / about-ness derivations · pipeline authorisation               NOT BUILT

Run:  python tests/test_proposition_correspondence_fixture.py
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
    d = tempfile.mkdtemp(prefix='gw_pcorr_')
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
    from sqlalchemy.exc import IntegrityError
    s = _fresh()
    rob = db.Person(display_name='Rob')
    s.add(rob)
    s.commit()
    household = rob.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'},
               db.PROPOSITION_CORRESPONDS: {'person', 'institution'},   # supplied - and must not score
               'statement_figure': {'institution'}, 'balance': {'institution'}, 'payment_due': {'institution'}}

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

    def read(a, process, when):
        r = db.Reading(artefact_id=a.id, reader_process=process, read_at=when)
        s.add(r)
        s.commit()
        return r

    def line(a, reading, kind, content, party):
        p = prop(kind, object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=party.id, content=content, as_of=a.as_of)
        return p, evidence(p, reading=reading)

    def corr(a, b, content=None):
        return prop(db.PROPOSITION_CORRESPONDS, subject_proposition_id=a.id, object_proposition_id=b.id, content=content)

    def fingerprint(p):
        return (p.kind, p.subject_state, p.subject_party_id, p.subject_artefact_id, p.subject_obligation_id,
                p.subject_proposition_id, p.object_state, p.object_obligation_id, p.object_payment_id,
                p.object_proposition_id, p.content, p.as_of,
                tuple(sorted((e.utterance_id, e.reading_id)
                             for e in s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p.id))))

    cu, u_cu = mint_party('The credit union.')
    o1 = mint_obligation('My mortgage with the credit union.')
    o2 = mint_obligation('My HELOC with the credit union.')
    A = held('h-combo', '2026-03-31', cu, u_cu)
    r1 = read(A, 'pdf-parser/5', datetime(2026, 3, 11))
    r2 = read(A, 'pdf-parser/6', datetime(2026, 4, 11))

    print('\n1. Pc1 - two readings of one line, two contents: a candidate, then established; the dispute stays\n')
    P3, e3 = line(A, r1, 'statement_figure', '$44,000', cu)
    P3b, e3b = line(A, r2, 'statement_figure', '$4,400', cu)
    fp_before = (fingerprint(P3), fingerprint(P3b))
    st_before = (db.derived_strength(s, e3, KNOWING), db.derived_strength(s, e3b, KNOWING))
    check('before any claim the two propositions are separate referents',
          db.referent(s, P3) == (db.REFERENT_SEPARATE, [P3.id], []) and P3.id != P3b.id)
    c = corr(P3b, P3, content='basis: same position on the page')
    e_cand = evidence(c, reading=r2)
    check('a position match observed by the second reading may produce a candidate - reading-sourced, no party, undetermined',
          db.referent(s, P3) == (db.REFERENT_CANDIDATES, [P3.id], [P3b.id])
          and e_cand.utterance is None and db.derived_strength(s, e_cand, KNOWING) == db.STRENGTH_UNDETERMINED)
    u_same = utter('Those are the same line - the second parse misread it.', '2026-04-12T09:00:00')
    e_est = evidence(c, utterance=u_same)
    check('a party\'s utterance establishes: P3 and P3\' correspond; the referent contains both',
          db.referent(s, P3) == (db.REFERENT_CORRESPONDING, sorted([P3.id, P3b.id]), []))
    check('the contents still differ - the parse dispute is now computable at line level, and nothing is chosen',
          P3.content == '$44,000' and P3b.content == '$4,400'
          and not any(hasattr(db, n) for n in ('resolve_dispute', 'winning_reading', 'current_value')))
    check('neither proposition changed: fingerprints and authority identical before and after',
          (fingerprint(P3), fingerprint(P3b)) == fp_before
          and (db.derived_strength(s, e3, KNOWING), db.derived_strength(s, e3b, KNOWING)) == st_before)
    check('the correspondence claim itself is undetermined even with a foundation rule supplied - relational knowing',
          db.derived_strength(s, e_est, KNOWING) == db.STRENGTH_UNDETERMINED)
    check('never merged: two rows, each under its own reading',
          s.get(db.Proposition, P3b.id) is not None
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=P3b.id, reading_id=r2.id).count() == 1)

    print('\n2. Pc2 / Pc9 - read twice, agreed; a third reading; the component\n')
    r3 = read(A, 'pdf-parser/7', datetime(2026, 5, 11))
    P3c, _ = line(A, r3, 'statement_figure', '$44,000', cu)
    evidence(corr(P3c, P3b), utterance=utter('Third parse, same line.', '2026-05-12T09:00:00'))
    check('Pc2: agreeing contents corresponding is representable - and nothing marks it "corroborated"',
          P3c.content == P3.content and not any(hasattr(db, n) for n in ('corroborated', 'independent_sources', 'source_count')))
    check('Pc9: the referent is the connected component {P3, P3\', P3"} - three readings of one claim, derived',
          db.referent(s, P3) == (db.REFERENT_CORRESPONDING, sorted([P3.id, P3b.id, P3c.id]), []))
    # Item 7 pass 7B built the one-source derivation as core.database.independence (CONSUMER_DERIVATIONS.md
    # s 7B.7) - a consumer over this structure, read-only, three-valued; this fixture still asserts that the
    # substrate itself holds no source count and that correspondence carries no independence.
    check('one source is a consumer\'s derivation over this structure (built in item 7 as independence()); the substrate holds no source count',
          callable(getattr(db, 'independence', None)) and not any(hasattr(db, n) for n in ('sources_of', 'n_sources', 'source_count'))
          and not any('independen' in c.name for c in db.Proposition.__table__.columns))

    print('\n3. Pc3 - about-ness is not carried\n')
    evidence(prop(db.PROPOSITION_CONCERNS, subject_proposition_id=P3.id, object_obligation_id=o2.id),
             utterance=utter('That line is the HELOC.', '2026-04-01T09:00:00'))
    check('P3 concerns O2; P3\' and P3" correspond to P3 - and NO concerns claim exists for either',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=P3.id).count() == 1
          and s.query(db.Proposition).filter(db.Proposition.kind == db.PROPOSITION_CONCERNS,
                                             db.Proposition.subject_proposition_id.in_([P3b.id, P3c.id])).count() == 0)
    check('P3\' still names nothing - its participant stays candidates; nothing copied, nothing derived here',
          s.get(db.Proposition, P3b.id).object_state == db.PARTICIPANT_CANDIDATES
          and s.get(db.Proposition, P3b.id).object_obligation_id is None
          and not any(hasattr(db, n) for n in ('about', 'about_via_correspondence', 'carried_aboutness')))

    print('\n4. Pc4 / Pc5 / Pc6 - a category error representable; identity not correspondence; kinds may differ\n')
    T = prop('balance', object_state=db.PARTICIPANT_NONE, subject_obligation_id=o2.id, content='$44,000', as_of='2026-04-15')
    evidence(T, utterance=utter('The HELOC balance is $44,000.', '2026-04-15T09:00:00'))
    check('Pc4: testimony T (subject O2) and the parser\'s P3 (subject the CU\'s stance) may be asserted corresponding - g1 does not see the category error',
          not _refused(s, db.Proposition(kind=db.PROPOSITION_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_proposition_id=T.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                         object_proposition_id=P3.id)))
    check('Pc4: and nothing treats it specially - agreement is a comparison, not a kind or an accessor',
          not any(hasattr(db, n) for n in ('agrees', 'agreement', 'agrees_with')))
    u_mar = utter('My servicer is Acme.', '2026-03-01T09:00:00')
    u_sep = utter('My servicer is Acme.', '2026-09-01T09:00:00')
    p_serv = prop('servicing', object_state=db.PARTICIPANT_NONE, subject_party_id=household.id, content='is served by Acme')
    evidence(p_serv, utterance=u_mar)
    evidence(p_serv, utterance=u_sep)
    check('Pc5: "said twice" is one proposition row evidenced twice - identity at the entry path, no correspondence',
          s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p_serv.id).count() == 2
          and s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CORRESPONDS, subject_proposition_id=p_serv.id).count() == 0)
    p_dup = prop('servicing', object_state=db.PARTICIPANT_NONE, subject_party_id=household.id, content='is served by Acme')
    evidence(p_dup, utterance=u_sep)
    evidence(corr(p_dup, p_serv), utterance=utter('That was the same statement entered twice.', '2026-09-02T09:00:00'))
    check('Pc5: a mis-individuation is repaired by correspondence - two rows remain, one referent',
          db.referent(s, p_serv)[1] == sorted([p_serv.id, p_dup.id]) and s.get(db.Proposition, p_dup.id) is not None)
    P3d, _ = line(A, read(A, 'pdf-parser/8', datetime(2026, 6, 11)), 'payment_due', '$44,000', cu)
    evidence(corr(P3d, P3), utterance=utter('Same line - that parser called it a payment due.', '2026-06-12T09:00:00'))
    check('Pc6: propositions of different KINDS may correspond - a dispute about kind, representable, no kind guard',
          P3d.kind != P3.kind and P3d.id in db.referent(s, P3)[1])
    check('Pc3 again, the other order: P3 already concerns O2 and P3d corresponds to it AFTERWARDS - still nothing copied to P3d',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=P3d.id).count() == 0
          and s.get(db.Proposition, P3d.id).object_obligation_id is None)

    print('\n5. g1 - established same-type participants disagreeing is refused; nothing else is inspected\n')
    T1 = prop('balance', object_state=db.PARTICIPANT_NONE, subject_obligation_id=o1.id, content='$181,000')
    T2 = prop('balance', object_state=db.PARTICIPANT_NONE, subject_obligation_id=o2.id, content='$181,000')
    check('g1: two propositions with established subject obligations O1 and O2 cannot be one claim - refused',
          _refused(s, db.Proposition(kind=db.PROPOSITION_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_proposition_id=T1.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_proposition_id=T2.id)))
    check('g1 inspects established participants only: differing content did not refuse Pc1, differing kind did not refuse Pc6',
          any(p.content != P3.content for p in (P3b,)) and P3d.kind != P3.kind
          and s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CORRESPONDS).count() >= 4)
    check('g1 ignores candidates: two read lines (participants in the candidates state) with different candidate claims still correspond',
          s.get(db.Proposition, P3.id).object_obligation_id is None and s.get(db.Proposition, P3b.id).object_obligation_id is None)
    check('g1 ignores proposition_concerns: P3 concerns O2, P3\' has no concerns claim, and they correspond',
          P3b.id in db.referent(s, P3)[1])
    check('a correspondence naming a proposition that does not exist, or the same proposition twice, is refused',
          _refused(s, db.Proposition(kind=db.PROPOSITION_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_proposition_id=P3.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_proposition_id=999999), (ValueError, IntegrityError))
          and _refused(s, db.Proposition(kind=db.PROPOSITION_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_proposition_id=P3.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                         object_proposition_id=P3.id)))
    check('cross-type is refused - a proposition does not correspond to an artefact or an obligation',
          _refused(s, db.Proposition(kind=db.PROPOSITION_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_proposition_id=P3.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_obligation_id=o1.id)))

    print('\n6. Pc8 / Pc10 - contested; the pipeline\'s re-parse\n')
    evidence(prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_same.id),
             utterance=utter('No - those were two different lines after all.', '2026-07-01T09:00:00'))
    check('Pc8: retracting the establishing utterance makes the referent contested; the component is still returned; nothing un-merged',
          db.referent(s, P3)[0] == db.REFERENT_CONTESTED and P3b.id in db.referent(s, P3)[1])
    B = held('h-bank', '2026-03-31', mint_party('My bank.')[0], u_cu)
    rb1 = read(B, 'feed-import/1', datetime(2026, 4, 1))
    rb2 = read(B, 'feed-import/1', datetime(2026, 5, 1))
    L1, _ = line(B, rb1, 'statement_figure', 'CHASE MTG -1,412.00', cu)
    L2, _ = line(B, rb2, 'statement_figure', 'CHASE MTG -1,412.00', cu)
    evidence(corr(L2, L1, content='basis: same position, same content, monthly re-parse'), reading=rb2)
    check('Pc10: a monthly re-parse may emit candidates; none is established; nothing carried',
          db.referent(s, L1) == (db.REFERENT_CANDIDATES, [L1.id], [L2.id])
          and s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=L2.id).count() == 0)

    print('\n7. The slot taxonomy; absences; audits\n')
    check('object_proposition_id is used by proposition_corresponds alone; subject_proposition_id by exactly the two proposition kinds',
          [k for k, r in db.RULED_KINDS.items() if 'object_proposition_id' in r['object']] == [db.PROPOSITION_CORRESPONDS]
          and sorted(k for k, r in db.RULED_KINDS.items() if 'subject_proposition_id' in r['subject'])
          == sorted([db.PROPOSITION_CONCERNS, db.PROPOSITION_CORRESPONDS]))
    check('the slice-5 non-kinds gained nothing; utterance_corresponds is still unforced',
          not any(k in db.RULED_KINDS for k in ('contradiction', 'reaffirmation', 'agrees_with', 'utterance_corresponds')))
    check('referent() derives and merges nothing; no substitution accessor exists',
          not any(hasattr(db, n) for n in ('merge_propositions', 'canonical_proposition', 'resolve_referent')))
    check('every audit is empty',
          not db.evidence_without_one_source(s) and not db.readings_of_unheld_artefacts(s)
          and not db.obligations_without_minting_utterance(s) and not db.parties_without_one_anchor(s))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
