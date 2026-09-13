# -*- coding: utf-8 -*-
"""The Person -> Party anchor fixture - the invariant the database cannot express.

`gw 2.0/PARTY_REFERENCE_SHAPE.md` (ruled B) and `PERSON_PARTY_ANCHOR.md` (ruled), 2026-09-12.

    a household party is created WITH its Person, 1:1, in the same unit of work - never lazily
    UNIQUE(person_id) gives at-most-one; the creation path plus THIS guard give at-least-one
    the party row is structural, not evidence: no source, strength, reason or supersession
    the backfill is idempotent and today finds nothing in production

What this fixture can and cannot exercise, stated so nobody later reads its greenness as more
than it is. Of the three frozen invariants:

    a party reference is a referential mechanism, not evidence   EXERCISED - the row carries
                                                                  nothing evidentiary (asserted
                                                                  as an absence)
    correspondence never crosses foundations                     NOT EXERCISABLE - no
                                                                  correspondence relation and
                                                                  no institution exist in
                                                                  this slice
    party state is explicit; NULL follows from it                NOT EXERCISABLE - no
                                                                  party-bearing relation
                                                                  exists in this slice

The second and third are checked by the slices that introduce their subjects, not here.

Run:  python tests/test_party_anchor_fixture.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL = [], []


def check(name, condition):
    (PASS if condition else FAIL).append(name)
    print(('  OK    ' if condition else '  FAIL  ') + name)


# Nothing on a party row may carry evidentiary meaning. If one of these ever appears as a
# column, the row has stopped being structure and started being a claim.
EVIDENTIARY = ('source', 'strength', 'reason', 'supersedes', 'recorded_by', 'confidence',
               'asserted', 'evidence', 'rank')


def _fresh():
    """A throwaway database with the shipped models and FK enforcement ON, so that the
    checks below measure the schema and not SQLite's default leniency."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_party_')
    eng = create_engine(f'sqlite:///{Path(d) / "t.db"}')

    @event.listens_for(eng, 'connect')
    def _fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def run(db):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    s = _fresh()

    print('\n1. The anchor exists from the moment the Person does\n')
    p = db.Person(display_name='Rob')
    s.add(p)
    s.commit()
    anchors = s.query(db.Party).filter_by(person_id=p.id).all()
    check('adding a Person mints exactly one Party in the same unit of work',
          len(anchors) == 1)
    check('and the Person can reach it', p.party is not None and p.party.person_id == p.id)
    check('so the audit finds no person without a party', not db.people_without_party(s))

    print('\n2. At most one is the database\'s\n')
    try:
        s.add(db.Party(person_id=p.id))
        s.commit()
        dup = False
    except IntegrityError:
        s.rollback()
        dup = True
    check('a second anchor for the same person is refused by UNIQUE', dup)

    print('\n3. At least one is the creation path plus this guard\n')
    # A raw insert bypasses the ORM listener - the one way to make the forbidden state.
    s.execute(text("INSERT INTO people (display_name, active) VALUES ('Raw', 1)"))
    s.commit()
    orphans = db.people_without_party(s)
    check('a person written around the creation path is the forbidden state, and the audit sees it',
          len(orphans) == 1 and orphans[0].display_name == 'Raw')
    created = db.backfill_party_anchors(s)
    s.commit()
    check('the backfill mints exactly the missing anchor', created == 1)
    check('and leaves the audit empty', not db.people_without_party(s))
    check('and is idempotent - a second run creates nothing', db.backfill_party_anchors(s) == 0)

    print('\n4. The party row is structural, not evidence\n')
    cols = {c.name for c in db.Party.__table__.columns}
    check('a party row carries no evidentiary column',
          not any(any(e in c for e in EVIDENTIARY) for c in cols))
    # Slice 3 (2026-09-13) retired the exact column set in place: the institution anchor
    # `minted_by_id` arrived additively - a reference to the minting claim, not a claim.
    check('and nothing but its identity, its two anchors, and when it was made',
          cols == {'id', 'person_id', 'minted_by_id', 'created_at'})
    check('the anchor is a foreign key to the declaration, not a copy of it',
          bool(db.Party.__table__.columns['person_id'].foreign_keys))

    print('\n5. Not exercised here, stated so it is not assumed\n')
    check('no institution anchor exists in this slice (arrives with the institution slice)',
          'institution_id' not in cols)
    check('no correspondence relation exists in this slice',
          not any(t.name.startswith('party_correspond') for t in db.Base.metadata.sorted_tables))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
