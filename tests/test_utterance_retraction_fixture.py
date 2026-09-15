# -*- coding: utf-8 -*-
"""The utterance-retraction fixture - slice 5's build gate over the forced cases.

`gw 2.0/CLAIM_ABOUT_CLAIM.md` s7 (ruled 2026-09-13):

    One higher-order proposition kind is forced: utterance_retraction - a proposition whose
    subject is an utterance and whose content asserts that the assertion made by that
    utterance no longer stands. No second participant; any replacement or contrary domain
    proposition is a separate proposition, potentially evidenced by the same utterance.
    correction decomposes into retraction plus a new domain proposition; contradiction and
    reaffirmation are derived relationships, not stored kinds. No proposition takes another
    proposition as subject. Strength remains undetermined until the relational knowing form
    is separately ruled. Resolver interpretation is fenced.

    A higher-order claim can say that an utterance's assertion no longer stands.
    It cannot itself rewrite, resolve, or replace that utterance.

What this slice can and cannot exercise, stated so greenness is not over-read:

    B    "I was wrong in March"                              EXERCISED - U1 and its evidence remain
    O8   "no - it was from Mercy": retraction + new origin   EXERCISED - one act, two propositions; origin still `multiple`
    X11  "no - b2 was the corrected one"                    EXERCISED - referent still `contested`
    RA   withdrawing testimony about an unheld statement     EXERCISED - the asserted artefact stays
    S3   "S3 was never my servicer"                         EXERCISED - S3 the party keeps its provenance
    H10  retracting the utterance that minted an institution EXERCISED - the institution stays; unminting NOT derived
    the required absence of a second participant            EXERCISED
    content carries no meaning; empty content is complete   EXERCISED
    strength undetermined, any source, any claimant         EXERCISED
    contradiction / reaffirmation                           NOT KINDS - asserted absent; derived by a resolver, NOT BUILT
    a proposition as subject                                Ab7 - one ruled kind only (tests/test_proposition_concerns_fixture.py)
    the resolver; narrowing multiple/contested; reach       NOT BUILT - fenced

Run:  python tests/test_utterance_retraction_fixture.py
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


VERDICT_VOCABULARY = ('retracted', 'contradicted', 'reaffirmed', 'superseded', 'governing', 'current',
                      'resolved', 'withdrawn', 'replaced', 'stands')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_retract_')
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
    s.add(rob)
    s.commit()
    household = rob.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'},
               db.UTTERANCE_RETRACTION: {'person', 'institution'},   # even if a caller supplies one...
               'servicing': {'person'}, 'eob_amount': {'institution'}}

    def utter(text, when='2026-03-10T09:00:00', origin=None):
        u = db.Utterance(origin_party_id=(origin or household).id, asserted_at=when, content=text)
        s.add(u)
        s.commit()
        return u

    def mint(text):
        u = utter(text)
        p = db.Party(minted_by_id=u.id)
        s.add(p)
        s.commit()
        return p, u

    def prop(kind, object_state=db.PARTICIPANT_ESTABLISHED, **slots):
        p = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED,
                           object_state=object_state, **slots)
        s.add(p)
        s.commit()
        return p

    def retract(u, content=None):
        return prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE,
                    subject_utterance_id=u.id, content=content)

    def evidence(p, utterance=None, reading=None):
        e = db.EvidentiaryRelationship(proposition_id=p.id,
                                       utterance_id=utterance.id if utterance else None,
                                       reading_id=reading.id if reading else None)
        s.add(e)
        s.commit()
        return e

    def snapshot():
        return (s.query(db.Utterance).count(), s.query(db.Proposition).count(),
                s.query(db.EvidentiaryRelationship).count(), s.query(db.Artefact).count(),
                s.query(db.Party).count())

    print('\n1. Case B - "I was wrong in March": a claim about the act; the act remains\n')
    u1 = utter('My servicer is Acme.')
    p_serv = prop('servicing', object_state=db.PARTICIPANT_NONE, subject_party_id=household.id,
                  content='is served by Acme')
    e_serv = evidence(p_serv, utterance=u1)
    before = snapshot()
    u3 = utter('I was wrong in March.', '2026-09-01T10:00:00')
    r_b = retract(u1, 'the March assertion was wrong')
    e_b = evidence(r_b, utterance=u3)
    check('the retraction is an ordinary proposition: kind utterance_retraction, subject U1, evidenced by U3',
          r_b.kind == db.UTTERANCE_RETRACTION and r_b.subject_utterance_id == u1.id
          and e_b.utterance is u3 and r_b.object_state == db.PARTICIPANT_NONE)
    check('U1 remains, with its proposition and its evidence - nothing removed, nothing rewritten',
          s.get(db.Utterance, u1.id) is not None and s.get(db.Proposition, p_serv.id).subject_party_id == household.id
          and s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u1.id).count() == 1)
    check('the retraction added exactly one utterance, one proposition and one relationship',
          snapshot() == (before[0] + 1, before[1] + 1, before[2] + 1, before[3], before[4]))
    check('the domain claim\'s own strength is unchanged by the retraction - no verdict has been applied to it',
          db.derived_strength(s, e_serv, KNOWING) == db.STRENGTH_KNOWING)

    print('\n2. The required absence: a retraction has no second participant\n')
    check('a retraction naming a second utterance is refused - a replacement is never an operand',
          _refused(s, db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_utterance_id=u1.id, object_state=db.PARTICIPANT_ESTABLISHED,
                                     object_utterance_id=u3.id)))
    check('a retraction with object_state not_established is refused - there is no such participant to be unsure of',
          _refused(s, db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_utterance_id=u1.id, object_state=db.PARTICIPANT_NOT_ESTABLISHED)))
    check('a retraction whose subject is not an utterance is refused',
          _refused(s, db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_party_id=household.id, object_state=db.PARTICIPANT_NONE)))
    check('a retraction with no subject is refused - it is about an act, not the world',
          _refused(s, db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_NONE,
                                     object_state=db.PARTICIPANT_NONE)))
    check('participant_violations names the required absence for a detached object',
          any('has no object' in v for v in db.participant_violations(
              db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED,
                             subject_utterance_id=u1.id, object_state=db.PARTICIPANT_ESTABLISHED,
                             object_party_id=household.id))))

    print('\n3. Content carries no meaning - the kind does\n')
    u_bare = utter('Forget what I said about the dentist.', '2026-09-02T10:00:00')
    u_dent = utter('The dentist bill was $300.', '2026-08-01T10:00:00')
    r_empty = retract(u_dent)
    evidence(r_empty, utterance=u_bare)
    check('a retraction with empty content is a complete retraction',
          r_empty.content is None and s.get(db.Proposition, r_empty.id) is not None)
    check('no derivation reads the content: the same rows, with or without text, derive identically',
          db.derived_strength(s, s.query(db.EvidentiaryRelationship).filter_by(proposition_id=r_empty.id).one(), KNOWING)
          == db.derived_strength(s, e_b, KNOWING))
    check('no column on any substrate table carries verdict vocabulary',
          not any(any(v in c.name for v in VERDICT_VOCABULARY)
                  for m in (db.Utterance, db.Proposition, db.EvidentiaryRelationship, db.Artefact, db.Party, db.Reading)
                  for c in m.__table__.columns))
    check('no accessor or function in the substrate yields a verdict on an utterance',
          not any(hasattr(db, n) for n in ('is_retracted', 'retracted', 'governing_claim', 'current_assertion',
                                           'resolve', 'resolve_utterance', 'effective_claim', 'supersedes')))

    print('\n4. O8 - "I was wrong, it was from Mercy": one act, two propositions; the origin stays multiple\n')
    aetna, u_aetna = mint('This is from Aetna, my insurer.')
    mercy, _ = mint('Mercy Hospital.')
    eob = db.Artefact(held=True, content_hash='h-eob', as_of='2026-02-14')
    s.add(eob)
    s.commit()
    o_aetna = prop(db.ARTEFACT_ORIGIN, subject_artefact_id=eob.id, object_party_id=aetna.id)
    evidence(o_aetna, utterance=u_aetna)
    check('before the correction the origin is established: Aetna',
          db.artefact_origin(s, eob) == (db.ORIGIN_ESTABLISHED, [aetna.id]))
    u_fix = utter('I was wrong. It was from Mercy.', '2026-09-05T09:00:00')
    r_fix = retract(u_aetna, 'wrong insurer')
    evidence(r_fix, utterance=u_fix)
    o_mercy = prop(db.ARTEFACT_ORIGIN, subject_artefact_id=eob.id, object_party_id=mercy.id)
    evidence(o_mercy, utterance=u_fix)
    check('U2 evidences two propositions: utterance_retraction(U1) and artefact_origin(EOB, Mercy)',
          s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_fix.id).count() == 2
          and {s.get(db.Proposition, e.proposition_id).kind
               for e in s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_fix.id)}
          == {db.UTTERANCE_RETRACTION, db.ARTEFACT_ORIGIN})
    check('there is no "correction" kind - correction is an interpretation of those two in one act',
          'correction' not in db.RULED_KINDS
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(('correction', 'corrects'))).count() == 0)
    check('the origin derivation is UNCHANGED by the retraction: multiple, both parties - nothing resolved',
          db.artefact_origin(s, eob) == (db.ORIGIN_MULTIPLE, sorted([aetna.id, mercy.id])))
    check('the Aetna origin claim, its evidence and U1 all remain',
          s.get(db.Proposition, o_aetna.id) is not None and s.get(db.Utterance, u_aetna.id) is not None
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=o_aetna.id).count() == 1)
    r_eob = db.Reading(artefact_id=eob.id, reader_process='pdf-parser/5', read_at=datetime(2026, 3, 11))
    s.add(r_eob)
    s.commit()
    e_amt = evidence(prop('eob_amount', object_state=db.PARTICIPANT_NONE, subject_artefact_id=eob.id, content='$412'),
                     reading=r_eob)
    check('a reading of the EOB derives undetermined - the origin is multiple, and the retraction did not pick Mercy',
          db.derived_strength(s, e_amt, KNOWING) == db.STRENGTH_UNDETERMINED)

    print('\n5. X11 - the referent stays contested; nothing chosen\n')
    b1 = db.Artefact(held=True, content_hash='h-b1', as_of='2026-09-01')
    b2 = db.Artefact(held=True, content_hash='h-b2', as_of='2026-09-01')
    s.add_all([b1, b2])
    s.commit()
    u_same = utter('b1 and b2 are the same statement.', '2026-09-02T09:00:00')
    evidence(prop(db.ARTEFACT_CORRESPONDS, subject_artefact_id=b1.id, object_artefact_id=b2.id), utterance=u_same)
    u_no = utter('No - b2 was the corrected one.', '2026-09-05T09:00:00')
    evidence(retract(u_same, 'not the same after all'), utterance=u_no)
    check('the referent reads contested with the component in full - the retraction did not dissolve it',
          db.referent(s, b1) == (db.REFERENT_CONTESTED, sorted([b1.id, b2.id]), []))

    print('\n6. RA-retract, S3-later, H10 - what a retraction reaches is a consumer\'s question; nothing under it moves\n')
    chase, u_chase = mint('My March statement from Chase - I do not have it.')
    a9 = db.Artefact(held=False, asserted_by_id=u_chase.id, as_of='2026-03')
    s.add(a9)
    s.commit()
    evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=a9.id, object_party_id=chase.id), utterance=u_chase)
    evidence(retract(u_chase, 'I was thinking of a different bank'), utterance=utter('Actually that was not Chase.'))
    check('RA: the asserted artefact remains under its (now retracted) asserting utterance - never removal',
          s.get(db.Artefact, a9.id) is not None and s.get(db.Artefact, a9.id).asserted_by_id == u_chase.id
          and db.artefact_origin(s, a9) == (db.ORIGIN_ESTABLISHED, [chase.id]))
    s3, u_s3 = mint('S3 is my servicer; this letter is from them.')
    letter = db.Artefact(held=True, content_hash='h-s3', as_of='2026-05-01')
    s.add(letter)
    s.commit()
    evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=letter.id, object_party_id=s3.id), utterance=u_s3)
    evidence(retract(u_s3, 'S3 was never my servicer'), utterance=utter('S3 was never my servicer.'))
    check('S3: the party keeps its provenance and the letter its origin - a real party sent it; the ROLE was the error',
          s.get(db.Party, s3.id).minted_by_id == u_s3.id
          and db.artefact_origin(s, letter) == (db.ORIGIN_ESTABLISHED, [s3.id]))
    aetna2, u_aetna2 = mint('Aetna Health Inc.')
    evidence(retract(u_aetna2, 'not a separate company'), utterance=utter("Aetna Health Inc isn't separate."))
    check('H10: retracting the minting utterance does not unmint - the institution remains, anchored; unminting is fenced',
          s.get(db.Party, aetna2.id) is not None and s.get(db.Party, aetna2.id).minted_by_id == u_aetna2.id
          and not db.parties_without_one_anchor(s))

    print('\n7. Strength - undetermined from any source and any claimant; the relation is relational\n')
    check('self-retraction derives undetermined even when a caller supplies a foundation rule for the kind',
          db.derived_strength(s, e_b, KNOWING) == db.STRENGTH_UNDETERMINED)
    other, _ = mint('Some other institution.')
    u_other = utter('Their March claim was wrong.', origin=other)
    e_other = evidence(retract(u1, 'disputed by a third party'), utterance=u_other)
    check('a third party\'s retraction of another\'s utterance is representable, and equally undetermined',
          e_other.utterance.origin_party_id == other.id and db.derived_strength(s, e_other, KNOWING) == db.STRENGTH_UNDETERMINED)
    check('the registry says why: relational_knowing, not a foundation rule',
          db.RULED_KINDS[db.UTTERANCE_RETRACTION]['relational_knowing'] is True)
    check('the knowing map is still foundation-keyed - no relational form was added',
          all(isinstance(v, set) for v in KNOWING.values()) and 'knows_about' not in dir(db))

    print('\n8. Not kinds, not built, stated so it is not assumed\n')
    u_false = utter('That is false.', '2026-09-06T09:00:00')
    p_neg = prop('eob_amount', object_state=db.PARTICIPANT_NONE, subject_artefact_id=eob.id, content='not $412')
    evidence(p_neg, utterance=u_false)
    check('"that is false" is a domain proposition with negative content - not contradiction(U)',
          p_neg.kind == 'eob_amount' and p_neg.subject_artefact_id == eob.id
          and 'contradiction' not in db.RULED_KINDS
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(('contradiction', 'contradicts'))).count() == 0)
    u_again = utter('My servicer is Acme.', '2026-09-07T09:00:00')
    evidence(p_serv, utterance=u_again)
    check('"I still stand by that" is a later utterance of the SAME proposition - not reaffirmation(U)',
          s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p_serv.id).count() == 2
          and 'reaffirmation' not in db.RULED_KINDS
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(('reaffirmation', 'reaffirms'))).count() == 0)
    # Ab7 (2026-09-14) reopened slice 5's finding on evidence and NARROWED it: a proposition-subject
    # slot now exists, and exactly one ruled kind uses it (proposition_concerns). What slice 5 ruled
    # still holds - truth, contradiction and reaffirmation claims about a proposition are not kinds.
    # proposition_corresponds (2026-09-14) is the second - and last - ruled kind with a proposition
    # participant (subject and object, symmetric). The slice-5 non-kinds still gained nothing.
    check('proposition participants are used by exactly two ruled kinds, and none of the slice-5 non-kinds became one',
          sorted(k for k, r in db.RULED_KINDS.items() if 'subject_proposition_id' in r['subject'])
          == sorted([db.PROPOSITION_CONCERNS, db.PROPOSITION_CORRESPONDS])
          and not any(k in db.RULED_KINDS for k in ('contradiction', 'reaffirmation', 'proposition_false',
                                                    'proposition_true', 'agrees_with')))
    # The obligation slice (2026-09-14) retired the exact column set in place: referent slots
    # arrive additively as identities are ruled; what this slice pins is that no slot for a
    # PROPOSITION subject exists (checked above) and that the retraction kind's own shape is
    # unchanged.
    check('no slot was added for this slice: the retraction kind uses only subject_utterance_id',
          db.RULED_KINDS[db.UTTERANCE_RETRACTION] == {'subject': ('subject_utterance_id',), 'object': (),
                                                     'symmetric': False, 'reading_establishes': False,
                                                     'relational_knowing': True})
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
