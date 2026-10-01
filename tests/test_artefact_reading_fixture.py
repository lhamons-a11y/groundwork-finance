# -*- coding: utf-8 -*-
"""The artefact/reading fixture - slice 2's build gate, as Rob stated it.

`gw 2.0/ARTEFACT_READING_SLICE.md` s8 (ruled 2026-09-13):

    An artefact and a reading must be independently representable, and neither may acquire
    the semantics of the other through convenience. A reading identifies an observation of a
    held artefact; it does not establish the artefact's origin, create a party, or become an
    assertion. An artefact's hash, dates, and reader information remain distinct coordinates,
    and every source-dependent conclusion remains derived rather than stored.

And the one practical requirement: construct the two identical-looking statements and prove
they remain different evidence paths -

    reading("EOB says $412")  !=  utterance("EOB says $412")

because the event that produced the proposition is what is being protected.

What this slice can and cannot exercise, stated so greenness is not over-read:

    artefact minted on encounter; held vs asserted     EXERCISED
    one artefact, two readings (parse dispute)         EXERCISED - by structure, nothing chosen
    two artefacts, one hash                            EXERCISED
    three times are three columns                      EXERCISED
    reader xor; process = no party                     EXERCISED
    readings only of held artefacts                    EXERCISED
    same sentence, two evidence events                 EXERCISED
    reading-sourced strength                           EXERCISED - undetermined, never from the reader
    the artefact's ORIGIN                              slice 3 - tests/test_artefact_origin_fixture.py
    correspondence between the two hash-twins          slice 4 - tests/test_correspondence_fixture.py
    asserted -> held upgrade                           NOT BUILT - fenced (never auto-match)
    which readings agree / independence                NOT BUILT - derived later, by consumers

Run:  python tests/test_artefact_reading_fixture.py
"""
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL = [], []


def check(name, condition):
    (PASS if condition else FAIL).append(name)
    print(('  OK    ' if condition else '  FAIL  ') + name)


EVIDENTIARY_ON_STRUCTURE = ('strength', 'rank', 'confidence', 'supports', 'truth', 'resolved',
                            'retracted', 'established', 'origin', 'issuer', 'source')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_artefact_')
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
    party = rob.party

    print('\n1. Encounter -> one artefact, minted, held, with its own as_of distinct from encountered_at\n')
    eob = db.Artefact(held=True, content_hash='h-eob-1', as_of='2026-02-14')
    s.add(eob)
    s.commit()
    check('a held artefact is minted on encounter with its own date',
          eob.id is not None and eob.held is True and eob.as_of == '2026-02-14')
    check('encountered_at is a separate column and is not the document date',
          isinstance(eob.encountered_at, datetime) and eob.encountered_at.isoformat()[:10] != eob.as_of)
    check('held must be stated - it is not defaulted into existence',
          _refused(s, db.Artefact(content_hash='h-x'), (ValueError, IntegrityError)))
    check('as_of may be absent - an undated capture is a real artefact',
          not _refused(s, db.Artefact(held=True, content_hash='h-undated')))

    print('\n2. Read -> one reading under that artefact, its own read_at, its reader recorded\n')
    r1 = db.Reading(artefact_id=eob.id, reader_process='pdf-parser/4E',
                    read_at=datetime(2026, 3, 1, 9, 0))
    s.add(r1)
    s.commit()
    check('a reading belongs to exactly one artefact and records who observed',
          r1.artefact is eob and r1.reader_process == 'pdf-parser/4E' and r1.reader_party_id is None)
    check('read_at is the observation time - neither as_of nor encountered_at',
          r1.read_at.isoformat()[:10] != eob.as_of and r1.read_at != eob.encountered_at)
    p_412 = db.Proposition(kind='eob_amount', subject_state=db.PARTICIPANT_ESTABLISHED,
                           subject_artefact_id=eob.id, content='$412')
    s.add(p_412)
    s.commit()
    e_r1 = db.EvidentiaryRelationship(proposition_id=p_412.id, reading_id=r1.id)
    s.add(e_r1)
    s.commit()
    check('a reading evidences a proposition whose subject is the artefact',
          e_r1.reading is r1 and e_r1.utterance is None and p_412.subject_artefact_id == eob.id)

    print('\n3. Read again -> a second reading under the SAME artefact; readings disagree; nothing chosen\n')
    r2 = db.Reading(artefact_id=eob.id, reader_process='pdf-parser/5',
                    read_at=datetime(2026, 3, 2, 9, 0))
    s.add(r2)
    s.commit()
    p_4_12 = db.Proposition(kind='eob_amount', subject_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=eob.id, content='$4.12')
    s.add(p_4_12)
    s.commit()
    s.add(db.EvidentiaryRelationship(proposition_id=p_4_12.id, reading_id=r2.id))
    s.commit()
    check('one artefact, two observations - two reading rows under one artefact_id',
          s.query(db.Reading).filter_by(artefact_id=eob.id).count() == 2
          and s.query(db.Artefact).count() == 2)
    disputed = (s.query(db.Proposition)
                 .filter_by(kind='eob_amount', subject_artefact_id=eob.id).all())
    check('the parse dispute is computable by structure: same kind + subject, two contents, both remain',
          len(disputed) == 2 and {p.content for p in disputed} == {'$412', '$4.12'})
    check('no column on artefact, reading or relationship names a winner',
          all(not any(e in c.name for e in ('winner', 'current', 'chosen', 'resolved'))
              for m in (db.Artefact, db.Reading, db.EvidentiaryRelationship)
              for c in m.__table__.columns))

    print('\n4. Same bytes twice -> two artefacts\n')
    twin = db.Artefact(held=True, content_hash='h-eob-1', as_of='2026-02-14')
    s.add(twin)
    s.commit()
    check('two encounters with one hash are two artefacts until correspondence says otherwise',
          twin.id != eob.id and s.query(db.Artefact).filter_by(content_hash='h-eob-1').count() == 2)
    check('content_hash is indexed for candidates, not unique',
          not any(getattr(c, 'unique', False) for c in db.Artefact.__table__.columns
                  if c.name == 'content_hash')
          and not any(ix.unique for ix in db.Artefact.__table__.indexes))
    r_twin = db.Reading(artefact_id=twin.id, reader_process='pdf-parser/5', read_at=datetime(2026, 3, 3))
    s.add(r_twin)
    s.commit()
    p_twin = db.Proposition(kind='eob_amount', subject_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=twin.id, content='$412')
    s.add(p_twin)
    s.commit()
    s.add(db.EvidentiaryRelationship(proposition_id=p_twin.id, reading_id=r_twin.id))
    s.commit()
    check('a reading of the twin is under the twin - two artefacts read once each is not one read twice',
          s.query(db.Reading).filter_by(artefact_id=twin.id).count() == 1
          and s.query(db.Reading).filter_by(artefact_id=eob.id).count() == 2)

    print('\n5. Unreadable -> a reading with no propositions\n')
    r_blank = db.Reading(artefact_id=eob.id, reader_process='ocr/1', read_at=datetime(2026, 3, 4))
    s.add(r_blank)
    s.commit()
    check('a reading that yielded nothing is a reading - the observation happened, the value did not',
          s.query(db.EvidentiaryRelationship).filter_by(reading_id=r_blank.id).count() == 0
          and s.get(db.Reading, r_blank.id) is not None)

    print('\n6. Asserted artefact -> held = false, under an utterance, and it cannot be read\n')
    u_assert = db.Utterance(origin_party_id=party.id, asserted_at='2026-03-10T09:00:00',
                            content='There was a March statement; I no longer have it.')
    s.add(u_assert)
    s.commit()
    march = db.Artefact(held=False, asserted_by_id=u_assert.id, as_of='2026-03')
    s.add(march)
    s.commit()
    check('an asserted artefact exists under the utterance that asserted it',
          march.held is False and march.asserted_by is u_assert and march.content_hash is None)
    check('an asserted artefact without its asserting utterance is refused',
          _refused(s, db.Artefact(held=False)))
    check('a held artefact under an asserting utterance is refused - the encounter is its provenance',
          _refused(s, db.Artefact(held=True, asserted_by_id=u_assert.id)))
    check('a reading of an asserted artefact is refused - POSE + FIND, never RE-READ',
          _refused(s, db.Reading(artefact_id=march.id, reader_process='pdf-parser/5')))
    check('a reading of an artefact that does not exist is refused',
          _refused(s, db.Reading(artefact_id=999999, reader_process='pdf-parser/5'),
                   (ValueError, IntegrityError)))

    print('\n7. Testimony -> an utterance about an artefact is not a reading of it (the same sentence)\n')
    # The parser read the held EOB and produced $412 (section 2). Now a household member SAYS
    # "the EOB says $412" - about the same held artefact. Same words. Different event.
    u_says = db.Utterance(origin_party_id=party.id, asserted_at='2026-03-05T18:00:00',
                          content='The EOB says $412.')
    s.add(u_says)
    s.commit()
    p_said = db.Proposition(kind='eob_amount', subject_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=eob.id, content='$412')
    s.add(p_said)
    s.commit()
    e_said = db.EvidentiaryRelationship(proposition_id=p_said.id, utterance_id=u_says.id)
    s.add(e_said)
    s.commit()
    same_shape = (p_said.kind == p_412.kind and p_said.subject_artefact_id == p_412.subject_artefact_id
                  and p_said.content == p_412.content)
    check('the two propositions are the same kind, subject and content',
          same_shape and p_said.id != p_412.id)
    check('reading("EOB says $412") != utterance("EOB says $412"): the evidence paths differ by structure',
          e_r1.reading_id is not None and e_r1.utterance_id is None
          and e_said.utterance_id is not None and e_said.reading_id is None)
    check('the reading path leads to a held artefact and a reader; the utterance path to a party',
          e_r1.reading.artefact.held is True and e_r1.reading.reader_process
          and e_said.utterance.origin is party)
    check('and the record tells them apart without consulting the text',
          e_r1.reading is not None and e_said.reading is None and
          s.query(db.EvidentiaryRelationship).filter(db.EvidentiaryRelationship.reading_id.isnot(None)).count() == 3
          and s.query(db.EvidentiaryRelationship).filter(db.EvidentiaryRelationship.utterance_id.isnot(None)).count() == 1)
    # The same sentence about the UNHELD March statement can only be an utterance.
    p_march = db.Proposition(kind='eob_amount', subject_state=db.PARTICIPANT_ESTABLISHED,
                             subject_artefact_id=march.id, content='$412')
    s.add(p_march)
    s.commit()
    s.add(db.EvidentiaryRelationship(proposition_id=p_march.id, utterance_id=u_says.id))
    s.commit()
    check('about an unheld artefact the sentence has exactly one path: an utterance with the artefact as subject',
          s.query(db.EvidentiaryRelationship).join(db.Proposition)
           .filter(db.Proposition.subject_artefact_id == march.id).count() == 1
          and not db.readings_of_unheld_artefacts(s))

    print('\n8. Process reader -> no party, and no party is manufactured\n')
    parties_before = s.query(db.Party).count()
    check('a process reading has no party and none was minted for the parser',
          r1.reader_party_id is None and s.query(db.Party).count() == parties_before == 1)
    r_member = db.Reading(artefact_id=eob.id, reader_party_id=party.id, read_at=datetime(2026, 3, 6))
    s.add(r_member)
    s.commit()
    check('a household member may be the reader - the observer, recorded as such',
          r_member.reader_party is party and r_member.reader_process is None)
    check('a reading with two readers is refused',
          _refused(s, db.Reading(artefact_id=eob.id, reader_party_id=party.id, reader_process='x')))
    check('a reading with no reader is refused - NULL is not "unknown reader"',
          _refused(s, db.Reading(artefact_id=eob.id)))
    check('reading_violations reports the same discipline for a detached object',
          db.reading_violations(db.Reading(artefact_id=eob.id), True) != []
          and db.reading_violations(db.Reading(artefact_id=eob.id, reader_process='x'), False) != []
          and db.reading_violations(db.Reading(artefact_id=eob.id, reader_process='x'), True) == [])

    print('\n9. Strength -> undetermined for every reading-sourced relation in this slice\n')
    knowing = {'eob_amount': {'person', 'institution'}}
    p_member = db.Proposition(kind='eob_amount', subject_state=db.PARTICIPANT_ESTABLISHED,
                              subject_artefact_id=eob.id, content='$412')
    s.add(p_member)
    s.commit()
    e_member = db.EvidentiaryRelationship(proposition_id=p_member.id, reading_id=r_member.id)
    s.add(e_member)
    s.commit()
    check('a process reading yields undetermined even when the kind has a rule (no origin established)',
          db.derived_strength(s, e_r1, knowing) == db.STRENGTH_UNDETERMINED)
    check('a member reading yields undetermined - the reader is a channel, never an origin (C2)',
          db.derived_strength(s, e_member, knowing) == db.STRENGTH_UNDETERMINED)
    check('the same member ASSERTING the value is a different event with its own strength',
          db.derived_strength(s, e_said, knowing) == db.STRENGTH_KNOWING)
    check('the not-knowing case still derives from the utterance side only',
          db.derived_strength(s, e_said, {'eob_amount': {'institution'}}) == db.STRENGTH_NOT_KNOWING)

    print('\n10. Exactly one source; absences\n')
    check('a relationship naming both a reading and an utterance is refused',
          _refused(s, db.EvidentiaryRelationship(proposition_id=p_412.id, reading_id=r1.id,
                                                 utterance_id=u_says.id)))
    check('a relationship naming no source is refused',
          _refused(s, db.EvidentiaryRelationship(proposition_id=p_412.id)))
    check('every audit is empty: one source, one reader, held-only readings, consistent assertion',
          not db.evidence_without_one_source(s) and not db.readings_without_one_reader(s)
          and not db.readings_of_unheld_artefacts(s) and not db.artefacts_with_inconsistent_assertion(s))
    for model, name in ((db.Artefact, 'artefacts'), (db.Reading, 'readings')):
        cols = {c.name for c in model.__table__.columns}
        check(f'{name} carries no evidentiary summary column (no origin, issuer, source, strength...)',
              not any(any(e in c for e in EVIDENTIARY_ON_STRUCTURE) for c in cols))
    check('readings carry no content column - their propositions are their content',
          not any(c.name in ('content', 'text', 'extracted_json', 'value') for c in db.Reading.__table__.columns))
    check('the artefact has no origin column - origin is derived from propositions that slice 3 rules',
          not any('origin' in c.name or 'party' in c.name for c in db.Artefact.__table__.columns))

    print('\n11. Not exercised here, stated so it is not assumed\n')
    # Slice 3 retired the origin-kind absence in place: `artefact_origin` is ruled and exercised
    # by tests/test_artefact_origin_fixture.py. Here, no origin claim exists, so the state is
    # not established - and the reading strength above was undetermined for that reason.
    check('with no origin claim the artefact origin derives to not established (slice 3 exercises the rest)',
          db.artefact_origin(s, eob) == (db.ORIGIN_NOT_ESTABLISHED, []))
    # Slice 4 retired the correspondence absence in place: with no claim between them the hash
    # twins are separate referents - and stay so until a party says otherwise.
    check('the hash twins are separate referents until a party asserts correspondence (slice 4 exercises the rest)',
          db.referent(s, eob) == (db.REFERENT_SEPARATE, [eob.id], [])
          and db.referent(s, twin) == (db.REFERENT_SEPARATE, [twin.id], []))
    check('the shipped cache is not read as an artefact store - PdfExtractCache is untouched',
          {c.name for c in db.PdfExtractCache.__table__.columns}
          == {'source_hash', 'issuer', 'extracted_json', 'created_at'})


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
