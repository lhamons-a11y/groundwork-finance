# -*- coding: utf-8 -*-
"""The artefact-origin fixture - slice 3's build gate over the eleven cases.

`gw 2.0/ARTEFACT_ORIGIN.md` s7 (ruled s8, 2026-09-13):

    One proposition kind establishes an artefact's origin: "this artefact is a statement by P"
    - subject the artefact, second participant the party whose knowledge the artefact's
    readings convey. Established only when asserted by a party's utterance; a reading of the
    artefact itself, or of any other artefact, yields a candidate and never establishes.
    Established means referentially asserted, not true, not held, not unique. Maker, capturer,
    transmitter and recipient are not origin. With an established origin a reading's strength
    is derivable: weakest link of the origin party's knowingness for the kind and the origin
    claim's own strength. The institution anchor is this slice's dependency, built with it.

The line the slice must hold: a document can say where it is from; only a party can say where
a document is from. And Rob's fence: `artefact_origin` means exactly what the proposition says
- not "Issuer", "Created by", "Source" or "Author".

What this slice can and cannot exercise, stated so greenness is not over-read:

    O1  minted institution + origin in one utterance          EXERCISED
    O2  self-description via a reading -> candidate only      EXERCISED
    O3  origin established, role false, origin uncontaminated EXERCISED (the role claim is not built; asserted absent)
    O4  capturer is not origin                                EXERCISED (the capture link itself is fenced)
    O5  a household document does not launder a relayed value EXERCISED
    O6  another document naming P -> candidate for P          EXERCISED
    O7  two letterheads, nothing asserted -> candidates        EXERCISED
    O8/O11  two utterance-sourced claims -> multiple, nothing chosen   EXERCISED - joint vs competing NOT derivable (resolver fenced)
    O9  process-originated artefact                           NOT REPRESENTABLE - asserted as such
    O10 origin without custody                                EXERCISED
    correspondence                                            slice 4 - tests/test_correspondence_fixture.py
    descriptors · chain · unminting                           NOT BUILT

Run:  python tests/test_artefact_origin_fixture.py
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
    d = tempfile.mkdtemp(prefix='gw_origin_')
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'},   # the one ruled entry
               'eob_amount': {'institution'},                     # an insurer's figure
               'was_health': {'person'}}                          # the user was there

    def utter(text, when='2026-03-10T09:00:00', origin=None):
        u = db.Utterance(origin_party_id=(origin or household).id, asserted_at=when, content=text)
        s.add(u)
        s.commit()
        return u

    def claim(kind, subject_art, obj_party=None, content=None):
        p = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED,
                           subject_artefact_id=subject_art.id, content=content,
                           object_state=db.PARTICIPANT_ESTABLISHED if obj_party else db.PARTICIPANT_NONE,
                           object_party_id=obj_party.id if obj_party else None)
        s.add(p)
        s.commit()
        return p

    def evidence(prop, utterance=None, reading=None):
        e = db.EvidentiaryRelationship(proposition_id=prop.id,
                                       utterance_id=utterance.id if utterance else None,
                                       reading_id=reading.id if reading else None)
        s.add(e)
        s.commit()
        return e

    def read(art, process='pdf-parser/5'):
        r = db.Reading(artefact_id=art.id, reader_process=process, read_at=datetime(2026, 3, 11))
        s.add(r)
        s.commit()
        return r

    print('\n1. The institution anchor - one anchor per party, foundation by join\n')
    u_mint = utter('This is from Aetna, my insurer.')
    aetna = db.Party(minted_by_id=u_mint.id)
    s.add(aetna)
    s.commit()
    check('an institution party exists under the utterance that minted it',
          aetna.minted_by is u_mint and aetna.person_id is None)
    check('its foundation is a join to the anchor, never a stored kind',
          db.party_foundation(aetna) == 'institution' and db.party_foundation(household) == 'person'
          and 'kind' not in {c.name for c in db.Party.__table__.columns})
    check('the minting utterance originates from a Person - the fixed point one step out',
          db.party_foundation(u_mint.origin) == 'person')
    check('a party with no anchor is refused', _refused(s, db.Party()))
    check('a party with both anchors is refused - the two foundations never collapse',
          _refused(s, db.Party(person_id=rob.id, minted_by_id=u_mint.id), (ValueError, IntegrityError)))
    check('the party row still carries no descriptor - name, plan number, address are the utterance\'s content',
          {c.name for c in db.Party.__table__.columns} == {'id', 'person_id', 'minted_by_id', 'created_at'})
    check('the household anchor is unchanged: every Person still has its party, and no party lacks an anchor',
          not db.people_without_party(s) and not db.parties_without_one_anchor(s))

    print('\n2. O1 - a mailed EOB; "this is from Aetna, my insurer" mints and asserts origin in one act\n')
    eob = db.Artefact(held=True, content_hash='h-eob', as_of='2026-02-14')
    s.add(eob)
    s.commit()
    check('before any claim the origin is not established',
          db.artefact_origin(s, eob) == (db.ORIGIN_NOT_ESTABLISHED, []))
    o1 = claim(db.ARTEFACT_ORIGIN, eob, aetna)
    evidence(o1, utterance=u_mint)
    check('one utterance, two propositions: the minting act also evidences the origin claim',
          aetna.minted_by_id == u_mint.id and s.query(db.EvidentiaryRelationship)
          .filter_by(utterance_id=u_mint.id).count() == 1 and o1.object_party_id == aetna.id)
    check('the origin is established - by a party\'s utterance',
          db.artefact_origin(s, eob) == (db.ORIGIN_ESTABLISHED, [aetna.id]))
    check('and it is derived, not stored - the artefact has no origin column',
          not any('origin' in c.name or 'party' in c.name for c in db.Artefact.__table__.columns))
    r_eob = read(eob)
    p_amt = claim('eob_amount', eob, content='$412')
    e_amt = evidence(p_amt, reading=r_eob)
    check('a reading of the EOB now derives to KNOWING for an insurer\'s figure - through the origin, one link',
          db.derived_strength(s, e_amt, KNOWING) == db.STRENGTH_KNOWING)
    check('but not for a kind the insurer is not knowing for',
          db.derived_strength(s, e_amt, {**KNOWING, 'eob_amount': {'person'}}) == db.STRENGTH_NOT_KNOWING)
    check('and stays undetermined when the origin kind itself has no rule - the link cannot be scored',
          db.derived_strength(s, e_amt, {'eob_amount': {'institution'}}) == db.STRENGTH_UNDETERMINED)

    print('\n3. O2 - the parser reads the letterhead: a document cannot establish its own origin\n')
    eob2 = db.Artefact(held=True, content_hash='h-eob-2', as_of='2026-04-01')
    s.add(eob2)
    s.commit()
    r_head = read(eob2)
    o2 = claim(db.ARTEFACT_ORIGIN, eob2, aetna, content='letterhead: Aetna')
    evidence(o2, reading=r_head)
    check('a reading-sourced origin claim is a candidate, never establishing',
          db.artefact_origin(s, eob2) == (db.ORIGIN_CANDIDATES, [aetna.id]))
    r2 = read(eob2)
    e2 = evidence(claim('eob_amount', eob2, content='$90'), reading=r2)
    check('so a reading of that artefact stays undetermined - the circle is not closed',
          db.derived_strength(s, e2, KNOWING) == db.STRENGTH_UNDETERMINED)
    evidence(o2, utterance=utter('Yes, that one is from Aetna too.'))
    check('until a party asserts it - then the same proposition is established',
          db.artefact_origin(s, eob2) == (db.ORIGIN_ESTABLISHED, [aetna.id])
          and db.derived_strength(s, e2, KNOWING) == db.STRENGTH_KNOWING)

    print('\n4. O3 - S3\'s letter: origin established, the servicer relation is another proposition\n')
    u_s3 = utter('S3 is my servicer; this letter is from them.')
    s3 = db.Party(minted_by_id=u_s3.id)
    s.add(s3)
    s.commit()
    letter = db.Artefact(held=True, content_hash='h-s3', as_of='2026-05-01')
    s.add(letter)
    s.commit()
    evidence(claim(db.ARTEFACT_ORIGIN, letter, s3), utterance=u_s3)
    check('the letter\'s origin is S3 - a real party sent it',
          db.artefact_origin(s, letter) == (db.ORIGIN_ESTABLISHED, [s3.id]))
    check('"S3 is my servicer" is NOT the origin proposition and nothing here represents it (a dated role, later)',
          s.query(db.Proposition).filter(db.Proposition.kind.like('%servic%')).count() == 0)
    check('established is not true: the origin claim carries no truth column and can be wrong',
          not any(c.name in ('true', 'truth', 'verified') for c in db.Proposition.__table__.columns))

    print('\n5. O4 - Rob\'s screenshot of Aetna\'s portal: the capturer is not the origin\n')
    shot = db.Artefact(held=True, content_hash='h-shot', as_of='2026-06-01')
    s.add(shot)
    s.commit()
    evidence(claim(db.ARTEFACT_ORIGIN, shot, aetna), utterance=utter('Screenshot of my Aetna portal.'))
    r_shot = db.Reading(artefact_id=shot.id, reader_party_id=household.id, read_at=datetime(2026, 6, 2))
    s.add(r_shot)
    s.commit()
    e_shot = evidence(claim('eob_amount', shot, content='$1,925'), reading=r_shot)
    check('the origin is Aetna - whose statement the capture is - not Rob who captured it',
          db.artefact_origin(s, shot) == (db.ORIGIN_ESTABLISHED, [aetna.id]))
    check('a member READING the capture derives through Aetna, not through the member (C2)',
          db.derived_strength(s, e_shot, KNOWING) == db.STRENGTH_KNOWING)
    check('the capture link (faithful capture) is not represented - one link only, the chain is fenced',
          s.query(db.Proposition).filter(db.Proposition.kind.like('%captur%')).count() == 0)

    print('\n6. O5 - Rob\'s own spreadsheet: a household document does not launder a relayed value\n')
    sheet = db.Artefact(held=True, content_hash='h-sheet', as_of='2026-07-01')
    s.add(sheet)
    s.commit()
    evidence(claim(db.ARTEFACT_ORIGIN, sheet, household), utterance=utter('My spreadsheet of medical bills.'))
    r_sheet = read(sheet, 'csv-import/1')
    e_relayed = evidence(claim('eob_amount', sheet, content='$412 (Aetna EOB)'), reading=r_sheet)
    e_first_hand = evidence(claim('was_health', sheet, content='yes'), reading=r_sheet)
    check('origin of the spreadsheet is Rob - his statement',
          db.artefact_origin(s, sheet) == (db.ORIGIN_ESTABLISHED, [household.id]))
    check('the relayed insurer figure derives to NOT KNOWING - Rob created the document, Rob is not the source',
          db.derived_strength(s, e_relayed, KNOWING) == db.STRENGTH_NOT_KNOWING)
    check('while "it was health" from the same sheet derives to KNOWING - C1 exactly, through a document',
          db.derived_strength(s, e_first_hand, KNOWING) == db.STRENGTH_KNOWING)

    print('\n7. O6 - Aetna\'s EOB names Mercy Hospital: content, a candidate for a DIFFERENT artefact\n')
    u_mercy = utter('Mercy Hospital, the one that billed me.')
    mercy = db.Party(minted_by_id=u_mercy.id)
    s.add(mercy)
    s.commit()
    bill = db.Artefact(held=True, content_hash='h-bill', as_of='2026-02-20')
    s.add(bill)
    s.commit()
    evidence(claim(db.ARTEFACT_ORIGIN, bill, mercy, content='named on the Aetna EOB, NPI 1234'), reading=r_eob)
    check('the EOB\'s origin is unchanged by what it names',
          db.artefact_origin(s, eob) == (db.ORIGIN_ESTABLISHED, [aetna.id]))
    check('the bill\'s origin is a candidate (Mercy), sourced from a reading of another artefact - not established',
          db.artefact_origin(s, bill) == (db.ORIGIN_CANDIDATES, [mercy.id]))

    print('\n8. O7 - two identical letterheads, nobody has asserted anything\n')
    l1 = db.Artefact(held=True, content_hash='h-same', as_of='2026-08-01')
    l2 = db.Artefact(held=True, content_hash='h-same', as_of='2026-08-01')
    s.add_all([l1, l2])
    s.commit()
    for art in (l1, l2):
        evidence(claim(db.ARTEFACT_ORIGIN, art, aetna, content='letterhead: Aetna'), reading=read(art))
    check('two artefacts, each with a candidate only, indefinitely',
          db.artefact_origin(s, l1) == (db.ORIGIN_CANDIDATES, [aetna.id])
          and db.artefact_origin(s, l2) == (db.ORIGIN_CANDIDATES, [aetna.id]) and l1.id != l2.id)

    print('\n9. O8 / O11 - two utterance-sourced claims naming distinct parties: multiple, nothing chosen\n')
    ltr = db.Artefact(held=True, content_hash='h-ltr', as_of='2026-09-01')
    s.add(ltr)
    s.commit()
    u_a = utter('From Aetna.', '2026-09-02T09:00:00')
    u_b = utter('No - that was from Mercy.', '2026-09-05T09:00:00')
    evidence(claim(db.ARTEFACT_ORIGIN, ltr, aetna), utterance=u_a)
    evidence(claim(db.ARTEFACT_ORIGIN, ltr, mercy), utterance=u_b)
    state, parties = db.artefact_origin(s, ltr)
    check('the state is MULTIPLE with both parties listed - not the later, not the first, not the most repeated',
          state == db.ORIGIN_MULTIPLE and sorted(parties) == sorted([aetna.id, mercy.id]))
    evidence(claim(db.ARTEFACT_ORIGIN, ltr, aetna), utterance=utter('From Aetna, I am sure.', '2026-09-06T09:00:00'))
    check('saying one of them twice does not choose it - count is history, not resolution',
          db.artefact_origin(s, ltr)[0] == db.ORIGIN_MULTIPLE)
    e_ltr = evidence(claim('eob_amount', ltr, content='$50'), reading=read(ltr))
    check('a reading of it derives to UNDETERMINED - nothing chosen among the parties',
          db.derived_strength(s, e_ltr, KNOWING) == db.STRENGTH_UNDETERMINED)
    check('both claims remain - the correction is about, not a removal',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_ORIGIN, subject_artefact_id=ltr.id).count() == 3)
    check('joint (O11) vs competing (O8) is NOT derivable here - no correction/contradiction kind exists (fenced)',
          s.query(db.Proposition).filter(db.Proposition.kind.in_(('correction', 'contradiction', 'retraction'))).count() == 0)

    print('\n10. O9 - Groundwork\'s own export: NOT representable, asserted as such\n')
    export = db.Artefact(held=True, content_hash='h-export', as_of='2026-12-31')
    s.add(export)
    s.commit()
    check('an utterance with no origin party is refused - a process cannot utter',
          _refused(s, db.Utterance(content='exported by Groundwork'), IntegrityError))
    check('so an origin of "no party" has no evidence path: the export\'s origin reads not established',
          db.artefact_origin(s, export) == (db.ORIGIN_NOT_ESTABLISHED, []))
    check('and no process-origin escape hatch was added to the artefact',
          not any(c.name in ('process', 'manufactured', 'generated_by', 'origin_process') for c in db.Artefact.__table__.columns))

    print('\n11. O10 - "my March Chase statement, which I don\'t have": origin without custody\n')
    u_chase = utter('My March statement from Chase - I do not have it any more.')
    chase = db.Party(minted_by_id=u_chase.id)
    s.add(chase)
    s.commit()
    march = db.Artefact(held=False, asserted_by_id=u_chase.id, as_of='2026-03')
    s.add(march)
    s.commit()
    evidence(claim(db.ARTEFACT_ORIGIN, march, chase), utterance=u_chase)
    check('an asserted artefact has an established origin - established is not held',
          march.held is False and db.artefact_origin(s, march) == (db.ORIGIN_ESTABLISHED, [chase.id]))
    check('and still cannot be read', _refused(s, db.Reading(artefact_id=march.id, reader_process='x')))

    print('\n12. The literal meaning, and absences\n')
    check('the kind is named exactly artefact_origin - not issuer, author, source or created_by',
          db.ARTEFACT_ORIGIN == 'artefact_origin'
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(
              ('issuer', 'author', 'source', 'created_by', 'issued_by'))).count() == 0)
    check('origin state is a derivation with four values and none of them is a column anywhere',
          {db.ORIGIN_ESTABLISHED, db.ORIGIN_NOT_ESTABLISHED, db.ORIGIN_CANDIDATES, db.ORIGIN_MULTIPLE}
          and not any('origin' in c.name for m in (db.Artefact, db.Reading, db.Party, db.EvidentiaryRelationship)
                      for c in m.__table__.columns))
    # Slice 4 retired the correspondence absence in place; the two hash twins of O7 stay
    # separate referents here because nobody has asserted otherwise.
    check('no descriptor column, no chain link exists (fences); the O7 letters are separate referents',
          not any(c.name in ('name', 'display_name', 'external_id', 'issuer') for c in db.Party.__table__.columns)
          and db.referent(s, l1) == (db.REFERENT_SEPARATE, [l1.id], []))
    check('every audit is empty',
          not db.parties_without_one_anchor(s) and not db.people_without_party(s)
          and not db.evidence_without_one_source(s) and not db.readings_of_unheld_artefacts(s))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
