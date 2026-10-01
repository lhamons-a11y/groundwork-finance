# -*- coding: utf-8 -*-
"""The evidence-substrate fixture - slice 1's build gate, as Rob stated it.

`gw 2.0/SHIPPED_VS_TARGET.md` s6 (ruled 2026-09-13) and `SMALLEST_SCHEMA.md` s12.

    Person -> makes utterance -> has proposition (kind . subject . content)
                              -> has evidence time
                              -> has derived strength
    same act            -> one utterance
    same proposition    -> may be asserted by multiple utterances
    false proposition   -> remains representable
    unresolved subject  -> remains representable

And the substrate's own absences, asserted so they cannot drift back in: no strength column,
no supports flag, no uniqueness on kind + subject + content, NULL never the source of a state.

What this slice can and cannot exercise, stated so greenness is not over-read:

    subject / object state discipline        EXERCISED
    strength derived, never stored           EXERCISED (the knowing map is caller-supplied;
                                             the catalogue is not ruled)
    asserted-at distinct from recorded-at    EXERCISED
    a claim about an utterance (Case B)      EXERCISED - subject_utterance_id
    reading as a source                      slice 2 - tests/test_artefact_reading_fixture.py
    artefact subjects                        slice 2 - tests/test_artefact_reading_fixture.py
    institution origins                      slice 3 - tests/test_artefact_origin_fixture.py
    correspondence / candidates              NOT EXERCISABLE - slice 4; the state exists,
                                             the candidate claims do not

Run:  python tests/test_evidence_substrate_fixture.py
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


EVIDENTIARY_ON_STRUCTURE = ('strength', 'rank', 'confidence', 'supports', 'truth', 'resolved',
                            'retracted', 'established')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_substrate_')
    eng = create_engine(f'sqlite:///{Path(d) / "t.db"}')

    @event.listens_for(eng, 'connect')
    def _fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA synchronous=OFF')          # throwaway DB: no fsync per commit
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def run(db):
    from sqlalchemy.exc import IntegrityError
    s = _fresh()
    rob = db.Person(display_name='Rob')
    s.add(rob)
    s.commit()
    party = rob.party

    print('\n1. Person -> utterance -> proposition, with evidence time and derived strength\n')
    u1 = db.Utterance(origin_party_id=party.id, asserted_at='2026-03-10T09:00:00',
                      content='My servicer is Acme.')
    s.add(u1)
    s.commit()
    check('an utterance has an origin party, evidence time, and opaque content',
          u1.origin is party and u1.asserted_at == '2026-03-10T09:00:00'
          and u1.content == 'My servicer is Acme.')
    check('recorded_at is a separate column and is when Groundwork encountered it, not when it was asserted',
          isinstance(u1.recorded_at, datetime) and u1.recorded_at.year >= 2026
          and u1.recorded_at.isoformat()[:10] != u1.asserted_at[:10])
    p1 = db.Proposition(kind='servicing', subject_state=db.PARTICIPANT_ESTABLISHED,
                        subject_party_id=party.id, content='is served by Acme')
    s.add(p1)
    s.commit()
    e1 = db.EvidentiaryRelationship(proposition_id=p1.id, utterance_id=u1.id)
    s.add(e1)
    s.commit()
    check('a proposition has kind, subject and content',
          p1.kind == 'servicing' and p1.subject_party_id == party.id and p1.content)
    check('the evidentiary relationship names the proposition and its source',
          e1.proposition is p1 and e1.utterance is u1)
    knowing = {'servicing': {'person'}, 'p_ack': {'institution'}}
    check('strength is derived on read from origin x proposition kind',
          db.derived_strength(s, e1, knowing) == db.STRENGTH_KNOWING)
    p_ack = db.Proposition(kind='p_ack', subject_state=db.PARTICIPANT_NONE, content='balance $1,925')
    s.add(p_ack)
    s.commit()
    e_ack = db.EvidentiaryRelationship(proposition_id=p_ack.id, utterance_id=u1.id)
    s.add(e_ack)
    s.commit()
    check('the same origin is NOT knowing for a kind it is not knowing for (K5)',
          db.derived_strength(s, e_ack, knowing) == db.STRENGTH_NOT_KNOWING)
    check('a kind with no rule yields undetermined, not a guess',
          db.derived_strength(s, e_ack, {}) == db.STRENGTH_UNDETERMINED)

    print('\n2. Same act -> one utterance; same proposition -> many utterances\n')
    before = s.query(db.Utterance).count()
    e1b = db.EvidentiaryRelationship(proposition_id=p_ack.id, utterance_id=u1.id)
    s.add(e1b)
    s.commit()
    check('one act evidencing several propositions is still one utterance row',
          s.query(db.Utterance).count() == before)
    u2 = db.Utterance(origin_party_id=party.id, asserted_at='2026-03-14T09:00:00',
                      content='My servicer is Acme.')
    s.add(u2)
    s.commit()
    s.add(db.EvidentiaryRelationship(proposition_id=p1.id, utterance_id=u2.id))
    s.commit()
    check('a second act with identical content is a second utterance (said twice)',
          s.query(db.Utterance).count() == before + 1)
    check('and it evidences the SAME proposition - one proposition, two utterances',
          s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p1.id).count() == 2)

    print('\n3. A false proposition remains representable; a claim about an utterance (Case B)\n')
    # Slice 5 (2026-09-13) retired the placeholder label 'correction' in place: the ruled kind is
    # utterance_retraction - "the assertion made by utterance U no longer stands" - with no
    # second participant. Case B has been this proposition since slice 1; now it has its name.
    correction = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED,
                                subject_utterance_id=u1.id, object_state=db.PARTICIPANT_NONE,
                                content='the March assertion was wrong')
    s.add(correction)
    s.commit()
    u3 = db.Utterance(origin_party_id=party.id, asserted_at='2026-09-01T10:00:00',
                      content='I was wrong in March.')
    s.add(u3)
    s.commit()
    s.add(db.EvidentiaryRelationship(proposition_id=correction.id, utterance_id=u3.id))
    s.commit()
    check('a proposition may take an utterance as its subject',
          correction.subject_utterance_id == u1.id)
    check('the corrected utterance still exists with its evidence - retraction is about, not removal',
          s.get(db.Utterance, u1.id) is not None
          and s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u1.id).count() == 3)

    print('\n4. An unresolved subject remains representable\n')
    unresolved = db.Proposition(kind='servicing', subject_state=db.PARTICIPANT_CANDIDATES,
                                content='serves me')
    s.add(unresolved)
    s.commit()
    check('not-established-with-candidates is a state with every slot NULL',
          unresolved.subject_state == db.PARTICIPANT_CANDIDATES
          and unresolved.subject_party_id is None and unresolved.subject_utterance_id is None)
    check('no participant slot is required by default - the world / a kind without a second participant',
          p_ack.subject_state == db.PARTICIPANT_NONE and p_ack.object_state == db.PARTICIPANT_NONE)

    print('\n5. The state discipline: NULL follows from the state, never the reverse\n')

    def refused(**kw):
        try:
            s.add(db.Proposition(**kw))
            s.commit()
            s.rollback()
            return False
        except ValueError:
            s.rollback()
            return True
    check('established with no slot is refused',
          refused(kind='x', subject_state=db.PARTICIPANT_ESTABLISHED))
    check('established with two slots is refused',
          refused(kind='x', subject_state=db.PARTICIPANT_ESTABLISHED,
                  subject_party_id=party.id, subject_utterance_id=u1.id))
    check('a slot set under a non-established state is refused',
          refused(kind='x', subject_state=db.PARTICIPANT_NOT_ESTABLISHED, subject_party_id=party.id))
    check('an unknown state is refused', refused(kind='x', subject_state='bogus'))
    check('the same discipline governs the second participant',
          refused(kind='x', object_state=db.PARTICIPANT_ESTABLISHED)
          and refused(kind='x', object_state=db.PARTICIPANT_NONE, object_party_id=party.id))
    two_term = db.Proposition(kind='serves', subject_state=db.PARTICIPANT_ESTABLISHED,
                              subject_party_id=party.id, object_state=db.PARTICIPANT_NOT_ESTABLISHED)
    s.add(two_term)
    s.commit()
    check('a two-participant kind may hold its second participant as not established',
          two_term.object_state == db.PARTICIPANT_NOT_ESTABLISHED and two_term.object_party_id is None)
    check('participant_violations reports the same discipline for a detached object',
          db.participant_violations(db.Proposition(kind='x', subject_state=db.PARTICIPANT_ESTABLISHED)) != [])

    print('\n6. Absences - what the substrate must not carry\n')
    for model, name in ((db.Utterance, 'utterances'), (db.Proposition, 'propositions'),
                        (db.EvidentiaryRelationship, 'evidence')):
        cols = {c.name for c in model.__table__.columns}
        check(f'{name} carries no evidentiary summary column',
              not any(any(e in c for e in EVIDENTIARY_ON_STRUCTURE) for c in cols))
    check('the relationship has no supports flag - a negative is a proposition with negative content',
          'supports' not in {c.name for c in db.EvidentiaryRelationship.__table__.columns})
    dup = db.Proposition(kind='servicing', subject_state=db.PARTICIPANT_ESTABLISHED,
                         subject_party_id=party.id, content='is served by Acme')
    s.add(dup)
    s.commit()
    check('kind + subject + content is NOT a uniqueness constraint - sameness is a claim, not a key',
          s.query(db.Proposition).filter_by(kind='servicing', subject_party_id=party.id,
                                            content='is served by Acme').count() == 2)
    try:
        s.add(db.Utterance(content='no origin'))
        s.commit()
        orphan = False
    except IntegrityError:
        s.rollback()
        orphan = True
    check('an utterance without an origin party is refused by the database', orphan)
    check('the evidentiary relationship names exactly one source (audit empty)',
          not db.evidence_without_one_source(s))

    print('\n7. Not exercised here, stated so it is not assumed\n')
    # Slice 2 (2026-09-13) retired two absence checks in place: the reading source and the
    # artefact subject slot now exist and are exercised by tests/test_artefact_reading_fixture.py.
    check('the reading source arrived additively - utterance-sourced rows are untouched by it',
          'reading_id' in {c.name for c in db.EvidentiaryRelationship.__table__.columns}
          and all(r.reading_id is None for r in s.query(db.EvidentiaryRelationship).all()))
    check('the artefact subject slot arrived additively - the state discipline did not change',
          'subject_artefact_id' in db.Proposition.SUBJECT_SLOTS
          and db.participant_violations(db.Proposition(kind='x', subject_state=db.PARTICIPANT_NONE,
                                                   object_state=db.PARTICIPANT_NONE)) == [])
    # Slice 3 retired the institution absence in place; tests/test_artefact_origin_fixture.py
    # exercises institution origins.
    check('the institution anchor arrived additively - the household anchor is untouched by it',
          'minted_by_id' in {c.name for c in db.Party.__table__.columns}
          and all(p.minted_by_id is None for p in s.query(db.Party).all()))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
