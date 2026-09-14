# -*- coding: utf-8 -*-
"""The correspondence fixture - slice 4's build gate over the twelve cases.

`gw 2.0/CORRESPONDENCE.md` s7 (ruled s8, 2026-09-13):

    A correspondence claim is a proposition asserting that two separately minted identities
    of one type are one referent - artefact_corresponds and party_corresponds - with both
    participants established, distinct, of that type, and, for parties, of one foundation.
    Established only by a party's utterance; every observed match is a candidate with no
    party behind it, however strong its basis, and the basis is content, never consulted by
    a derivation. Never merges rows, never rewrites a reference, never crosses foundations
    or types, never reflexive. Sameness is read, never stored: the referent is the connected
    component under established claims, reported as contested when the claims conflict and
    never resolved by position. Origin, mention and role are not correspondence.

Vocabulary (Rob): 17 and 42 CORRESPOND; their derived referent CONTAINS both. Never "are the
same". X2 and X9 are permanent regression cases.

What this slice can and cannot exercise, stated so greenness is not over-read:

    X1  hash twins: candidate, then established; rows untouched   EXERCISED
    X2  same origin != same artefact                             EXERCISED - PERMANENT
    X3  two minted Aetnas correspond; no merge                   EXERCISED
    X4  cross-foundation refused                                 EXERCISED
    X5  asserted -> held only by "that's it"; nothing upgraded   EXERCISED
    X6  user's report vs the EOB: discovered, never assumed      EXERCISED (same shape as X5)
    X7  replayed sync = identity, not correspondence             NOT EXERCISABLE - the importer's contract; asserted absent
    X8  "$412" vs "412.00" = a comparison, not a correspondence  NOT BUILT - proposition_corresponds unforced
    X9  a mention is content, not origin, not correspondence     EXERCISED - PERMANENT
    X10 transitivity derived as the component, weakest-link      EXERCISED (component); strength over the path NOT derived (no consumer)
    X11 contested: reported, nothing chosen                      EXERCISED - what the contest SAYS is not derived (resolver fenced)
    X12 reflexive / cross-type refused                           EXERCISED
    retroactive tightening of artefact_origin                    EXERCISED
    never rewrites a reference (the merge/re-point guard)        EXERCISED

Run:  python tests/test_correspondence_fixture.py
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
    d = tempfile.mkdtemp(prefix='gw_corr_')
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'},
               db.ARTEFACT_CORRESPONDS: {'person', 'institution'},
               db.PARTY_CORRESPONDS: {'person', 'institution'},
               'eob_amount': {'institution'}}

    def utter(text, when='2026-03-10T09:00:00'):
        u = db.Utterance(origin_party_id=household.id, asserted_at=when, content=text)
        s.add(u)
        s.commit()
        return u

    def mint(text):
        u = utter(text)
        p = db.Party(minted_by_id=u.id)
        s.add(p)
        s.commit()
        return p, u

    def artefact(h, as_of, held=True, asserted_by=None):
        a = db.Artefact(held=held, content_hash=h, as_of=as_of,
                        asserted_by_id=asserted_by.id if asserted_by else None)
        s.add(a)
        s.commit()
        return a

    def read(art, process='pdf-parser/5'):
        r = db.Reading(artefact_id=art.id, reader_process=process, read_at=datetime(2026, 3, 11))
        s.add(r)
        s.commit()
        return r

    def prop(kind, object_state=db.PARTICIPANT_ESTABLISHED, **slots):
        p = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED,
                           object_state=object_state, **slots)
        s.add(p)
        s.commit()
        return p

    def corr_a(a, b, content=None):
        return prop(db.ARTEFACT_CORRESPONDS, subject_artefact_id=a.id, object_artefact_id=b.id, content=content)

    def corr_p(a, b, content=None):
        return prop(db.PARTY_CORRESPONDS, subject_party_id=a.id, object_party_id=b.id, content=content)

    def origin(art, party):
        return prop(db.ARTEFACT_ORIGIN, subject_artefact_id=art.id, object_party_id=party.id)

    def evidence(p, utterance=None, reading=None):
        e = db.EvidentiaryRelationship(proposition_id=p.id,
                                       utterance_id=utterance.id if utterance else None,
                                       reading_id=reading.id if reading else None)
        s.add(e)
        s.commit()
        return e

    aetna, u_aetna = mint('This is from Aetna, my insurer.')

    print('\n1. X1 - one EOB uploaded twice: a hash match is a reason to ask; only an answer is a claim\n')
    a17 = artefact('h-eob', '2026-02-14')
    a42 = artefact('h-eob', '2026-02-14')
    evidence(origin(a17, aetna), utterance=u_aetna)
    evidence(origin(a42, aetna), utterance=u_aetna)
    r17, r42 = read(a17), read(a42)
    check('before any claim each artefact is its own referent',
          db.referent(s, a17) == (db.REFERENT_SEPARATE, [a17.id], [])
          and db.referent(s, a42) == (db.REFERENT_SEPARATE, [a42.id], []))
    c_hash = corr_a(a42, a17, content='basis: identical content_hash h-eob')
    e_hash = evidence(c_hash, reading=r42)
    check('the importer\'s hash match is a CANDIDATE - separate, with a candidate - not a member',
          db.referent(s, a42) == (db.REFERENT_CANDIDATES, [a42.id], [a17.id])
          and db.referent(s, a17) == (db.REFERENT_CANDIDATES, [a17.id], [a42.id]))
    check('and its strength is undetermined even though 42\'s origin is established - bytes equal bytes is nobody\'s knowledge',
          db.derived_strength(s, e_hash, KNOWING) == db.STRENGTH_UNDETERMINED
          and db.artefact_origin(s, a42)[0] == db.ORIGIN_ESTABLISHED)
    u_yes = utter('Yes, I uploaded that statement twice.')
    e_yes = evidence(c_hash, utterance=u_yes)
    check('Rob\'s answer establishes: 17 and 42 correspond; the derived referent contains both',
          db.referent(s, a17) == (db.REFERENT_CORRESPONDING, sorted([a17.id, a42.id]), [])
          and db.referent(s, a42)[1] == sorted([a17.id, a42.id]))
    check('the claim is read both ways though stored once',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CORRESPONDS).count() == 1)
    check('the answer\'s strength derives from the household\'s foundation - knowing for correspondence',
          db.derived_strength(s, e_yes, KNOWING) == db.STRENGTH_KNOWING)
    check('rows untouched: two artefacts, each reading still under its own artefact, both hashes present',
          s.query(db.Artefact).filter_by(content_hash='h-eob').count() == 2
          and s.get(db.Reading, r17.id).artefact_id == a17.id and s.get(db.Reading, r42.id).artefact_id == a42.id)
    check('the basis is content, shown to a person - no column on the claim is read by the derivation',
          c_hash.content.startswith('basis:') and 'basis' not in {c.name for c in db.Proposition.__table__.columns})

    print('\n2. X2 - PERMANENT: two Aetna letters; same origin is not same artefact\n')
    l_a = artefact('h-letter-a', '2026-08-01')
    l_b = artefact('h-letter-b', '2026-08-01')
    evidence(origin(l_a, aetna), utterance=utter('Both of these are from Aetna.'))
    evidence(origin(l_b, aetna), utterance=utter('Both of these are from Aetna.'))
    check('X2: origin(A) = origin(B)',
          db.artefact_origin(s, l_a) == (db.ORIGIN_ESTABLISHED, [aetna.id])
          and db.artefact_origin(s, l_b) == (db.ORIGIN_ESTABLISHED, [aetna.id]))
    check('X2: A != B - no correspondence exists or is implied; each is its own referent',
          l_a.id != l_b.id and db.referent(s, l_a) == (db.REFERENT_SEPARATE, [l_a.id], [])
          and db.referent(s, l_b) == (db.REFERENT_SEPARATE, [l_b.id], []))
    check('X2: an origin claim is never read as a correspondence claim - different kinds, different derivations',
          db.RULED_KINDS[db.ARTEFACT_ORIGIN]['object'] == ('object_party_id',)
          and db.RULED_KINDS[db.ARTEFACT_CORRESPONDS]['object'] == ('object_artefact_id',))

    print('\n3. X3 - two minted Aetnas correspond; neither row is merged, re-pointed or deleted\n')
    aetna2, u_aetna2 = mint('Aetna Health Inc.')
    june = artefact('h-june', '2026-06-01')
    evidence(origin(june, aetna2), utterance=u_aetna2)
    check('before the claim the two parties are separate referents',
          db.referent(s, aetna) == (db.REFERENT_SEPARATE, [aetna.id], []))
    evidence(corr_p(aetna2, aetna, content='same company'), utterance=utter('Those are the same company.'))
    check('the parties correspond; the referent contains both',
          db.referent(s, aetna) == (db.REFERENT_CORRESPONDING, sorted([aetna.id, aetna2.id]), []))
    check('no merge: two party rows remain, each under its own minting utterance',
          s.query(db.Party).filter(db.Party.minted_by_id.isnot(None)).count() == 2
          and aetna.minted_by_id == u_aetna.id and aetna2.minted_by_id == u_aetna2.id)
    check('no re-point: the June EOB\'s origin still names the party it was asserted with',
          db.artefact_origin(s, june) == (db.ORIGIN_ESTABLISHED, [aetna2.id]))

    print('\n4. X4 - never crosses foundations\n')
    rob_llc, _ = mint("Rob's sole proprietorship.")
    check('party_corresponds(Rob, Rob LLC) is refused',
          _refused(s, db.Proposition(kind=db.PARTY_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_party_id=household.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_party_id=rob_llc.id)))
    check('and the refusal names the foundations, not the rows',
          'never crosses foundations' in ' '.join(db._foundation_violations(s.connection(), household.id, rob_llc.id)))
    check('a party that does not exist cannot be corresponded to',
          _refused(s, db.Proposition(kind=db.PARTY_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_party_id=aetna.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_party_id=999999), (ValueError, IntegrityError)))

    print('\n5. X5 / X6 - "my March Chase statement" and the PDF uploaded in May: found, then asserted; nothing upgraded\n')
    chase, u_chase = mint('My March statement from Chase - I do not have it any more.')
    a9 = artefact(None, '2026-03', held=False, asserted_by=u_chase)
    evidence(origin(a9, chase), utterance=u_chase)
    said = prop('eob_amount', object_state=db.PARTICIPANT_NONE,   # eob_amount is unruled; no second participant
                subject_artefact_id=a9.id, content='$1,925')
    evidence(said, utterance=u_chase)
    a30 = artefact('h-chase-pdf', '2026-03-31')
    evidence(origin(a30, chase), utterance=utter('Uploading my Chase March statement.'))
    r30 = read(a30)
    found = corr_a(a30, a9, content='basis: origin Chase, as_of March')
    evidence(found, reading=r30)
    check('a description match (origin + date) is a candidate only',
          db.referent(s, a9) == (db.REFERENT_CANDIDATES, [a9.id], [a30.id]))
    evidence(found, utterance=utter("That's it - that's the March statement."))
    check('"that\'s it" establishes: 9 and 30 correspond',
          db.referent(s, a9) == (db.REFERENT_CORRESPONDING, sorted([a9.id, a30.id]), []))
    check('nothing upgraded: 9 is still asserted and unreadable, 30 is still held',
          s.get(db.Artefact, a9.id).held is False and s.get(db.Artefact, a30.id).held is True
          and _refused(s, db.Reading(artefact_id=a9.id, reader_process='x')))
    check('the testimony about 9 keeps its subject - reading it as about 30\'s referent is a consumer\'s derivation, not a rewrite',
          s.get(db.Proposition, said.id).subject_artefact_id == a9.id)

    print('\n6. X9 - PERMANENT: a mention is content - not origin, not correspondence\n')
    mercy, _ = mint('Mercy Hospital, the one that billed me.')
    p_mention = prop('names_provider', subject_artefact_id=a17.id, object_party_id=mercy.id,
                     content='Mercy Hospital, NPI 1234')      # an UNRULED kind: content about the EOB
    evidence(p_mention, reading=r17)
    check('X9: the EOB\'s origin is unchanged by what it names',
          db.artefact_origin(s, a17) == (db.ORIGIN_ESTABLISHED, [aetna.id]))
    check('X9: no correspondence arises from a mention - the EOB\'s referent is exactly {17, 42}',
          db.referent(s, a17)[1] == sorted([a17.id, a42.id]))
    check('X9: a mention cannot be written as a correspondence - artefact <-> party is cross-type, refused',
          _refused(s, db.Proposition(kind=db.ARTEFACT_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_artefact_id=a17.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_party_id=mercy.id)))

    print('\n7. X10 - transitivity is derived, never stored\n')
    a55 = artefact('h-eob-3', '2026-02-14')
    evidence(corr_a(a42, a55), utterance=utter('And this third upload is the same one again.'))
    check('17 ~ 42 and 42 ~ 55 -> the referent of 17 contains 55; no row records the component',
          db.referent(s, a17)[1] == sorted([a17.id, a42.id, a55.id])
          and s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CORRESPONDS,
                                                subject_artefact_id=a17.id, object_artefact_id=a55.id).count() == 0
          and s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CORRESPONDS,
                                                subject_artefact_id=a55.id, object_artefact_id=a17.id).count() == 0)
    check('the two components are disjoint: Aetna letters are not pulled in by sharing an origin',
          l_a.id not in db.referent(s, a17)[1])

    print('\n8. X11 - contested: reported, nothing chosen, never by position\n')
    b1 = artefact('h-b1', '2026-09-01')
    b2 = artefact('h-b2', '2026-09-01')
    u_same = utter('b1 and b2 are the same statement.', '2026-09-02T09:00:00')
    evidence(corr_a(b1, b2), utterance=u_same)
    check('established: corresponding', db.referent(s, b1)[0] == db.REFERENT_CORRESPONDING)
    u_no = utter('No - b2 was the corrected one, not the same.', '2026-09-05T09:00:00')
    # Slice 5 retired the placeholder label 'correction' onto the ruled kind utterance_retraction.
    about = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED,
                           subject_utterance_id=u_same.id, object_state=db.PARTICIPANT_NONE,
                           content='the earlier assertion was wrong')
    s.add(about)
    s.commit()
    evidence(about, utterance=u_no)
    state, contains, cands = db.referent(s, b1)
    check('a claim about the establishing utterance makes the referent CONTESTED - the component is still returned in full',
          state == db.REFERENT_CONTESTED and contains == sorted([b1.id, b2.id]))
    check('what the contest MEANS for the referent is not derived - the retraction is represented, the resolver is fenced',
          db.RULED_KINDS[db.UTTERANCE_RETRACTION]['relational_knowing'] is True
          and not any(hasattr(db, n) for n in ('resolve_referent', 'governing_claim', 'is_retracted')))
    check('the later utterance does not win and the earlier does not win - both claims remain',
          s.get(db.Proposition, about.id) is not None
          and s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CORRESPONDS, subject_artefact_id=b1.id).count() == 1)

    print('\n9. X12 - never reflexive, never cross-type; ruled kinds have their slots enforced\n')
    check('corresponds(17, 17) is refused',
          _refused(s, db.Proposition(kind=db.ARTEFACT_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_artefact_id=a17.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_artefact_id=a17.id)))
    check('corresponds(party, artefact) is refused',
          _refused(s, db.Proposition(kind=db.PARTY_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_party_id=aetna.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_artefact_id=a17.id)))
    check('a correspondence with a participant not established is refused - both terms must be minted identities',
          _refused(s, db.Proposition(kind=db.ARTEFACT_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_artefact_id=a17.id, object_state=db.PARTICIPANT_CANDIDATES)))
    check('RETROACTIVE: artefact_origin with a party as subject is now refused, not silently ignored',
          _refused(s, db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_party_id=aetna.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_party_id=household.id)))
    check('RETROACTIVE: artefact_origin with an artefact as object is refused',
          _refused(s, db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_artefact_id=a17.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_artefact_id=a42.id)))
    check('an UNRULED kind is not constrained beyond the state discipline - the catalogue stays open',
          not _refused(s, db.Proposition(kind='some_future_kind', subject_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_party_id=aetna.id, object_state=db.PARTICIPANT_NONE)))
    check('participant_violations reports the kind contract for a detached object',
          any('may be' in v for v in db.participant_violations(
              db.Proposition(kind=db.ARTEFACT_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                             subject_party_id=aetna.id, object_state=db.PARTICIPANT_ESTABLISHED,
                             object_artefact_id=a17.id))))

    print('\n10. Never merges rows, never rewrites a reference\n')
    check('re-pointing a reading to another artefact is refused - the observation stays what it was',
          _update_refused(s, s.get(db.Reading, r42.id), 'artefact_id', a17.id))
    check('re-pointing a proposition\'s subject is refused - a claim is about what it was about',
          _update_refused(s, s.get(db.Proposition, said.id), 'subject_artefact_id', a30.id))
    check('re-pointing an utterance\'s origin is refused',
          _update_refused(s, s.get(db.Utterance, u_yes.id), 'origin_party_id', aetna.id))
    check('re-pointing an evidentiary relationship\'s source is refused',
          _update_refused(s, s.get(db.EvidentiaryRelationship, e_yes.id), 'utterance_id', u_no.id))
    check('there is no merge function, canonical-id column or duplicate_of pointer anywhere in the substrate',
          not any(n in dir(db) for n in ('merge_artefacts', 'merge_parties', 'canonical_id', 'dedupe'))
          and not any(c.name in ('canonical_id', 'duplicate_of', 'merged_into', 'referent_id')
                      for m in (db.Artefact, db.Party, db.Reading, db.Proposition) for c in m.__table__.columns))

    print('\n11. Not built, stated so it is not assumed\n')
    check('no utterance_corresponds or proposition_corresponds kind exists (unforced)',
          not any(k.startswith(('utterance_corr', 'proposition_corr')) for k in db.RULED_KINDS))
    check('no schema change: the tables are exactly slice 3\'s',
          {c.name for c in db.Party.__table__.columns} == {'id', 'person_id', 'minted_by_id', 'created_at'}
          and 'referent' not in db.Base.metadata.tables)
    check('every audit is empty',
          not db.parties_without_one_anchor(s) and not db.evidence_without_one_source(s)
          and not db.readings_of_unheld_artefacts(s) and not db.artefacts_with_inconsistent_assertion(s))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
