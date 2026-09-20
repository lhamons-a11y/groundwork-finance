"""parse_disputes - the executable trace of `gw 2.0/CONSUMER_DERIVATIONS.md` pass 7A (ruled 2026-09-16).

The first consumer: a read-only derivation over the observations of ONE artefact that reports
disagreement and never resolves it. It chooses nothing, stores nothing, counts readings of one referent
as one source, compares one artefact's readings only, treats a person's transcription as a reading, and
stops at a contested correspondence. Established correspondence -> referent()'s component; candidate
correspondence -> a candidate grouping; no correspondence -> no claim of one referent. It never calls
anything that establishes correspondence. Structural, so its null model is a correctness oracle.

What this slice can and cannot exercise
---------------------------------------
    Pd1  candidate correspondence + differing content: a CANDIDATE dispute, never upgraded          EXERCISED
    Pd2  established correspondence + differing content: an established dispute; nothing chosen       EXERCISED
    Pd3  two readings agree: agreed, ONE source, no corroboration                                      EXERCISED
    Pd4  the readings disagree about KIND: a kind dispute, distinct from content                       EXERCISED
    Pd5  a line one reading has and the other lacks: an OMISSION, not a dispute, not zero              EXERCISED
    Pd6  two readings of TWO artefacts: not a parse dispute; the other artefact's member excluded     EXERCISED
    Pd7  testimony vs a reading: not a dispute (different subjects; not this consumer's)               EXERCISED
    Pd8  three readings, two contents: one referent, one source; no majority                           EXERCISED
    Pd9  a person's transcription vs the parser: two readings; no promotion to testimony               EXERCISED
    Pd10 the correspondence retracted: contested; the derivation reports it and stops                  EXERCISED
    Pd11 a monthly re-parse: recomputed on read; nothing persisted; candidates reported as candidates  EXERCISED
    Pd12 the resolution() hazard: the reading-level answer exists; the 1.x projection names it and does not read past  EXERCISED
    Pd13 one reading: "one observation", never "agreed"                                                EXERCISED
    Pd14 the null model: identical re-parse -> 0; one changed figure -> 1; structural, no threshold    EXERCISED
    no disputed / current_value column, no threshold, no resolver, no persistence, no establishing call  EXERCISED (absence)
    independence (7B), about-ness via correspondence (7C), level consistency (7D), strength (7E)        NOT BUILT

Run:  python tests/test_parse_disputes_fixture.py
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


CHOOSER_NAMES = ('resolve_dispute', 'resolve_parse_dispute', 'latest_reading', 'newest_reading', 'majority', 'majority_content',
                 'pick_reading', 'choose_reading', 'current_value', 'current_content', 'preferred_reading', 'best_reading',
                 'similarity', 'similarity_threshold', 'PARSE_THRESHOLD', 'DISPUTE_THRESHOLD', 'fuzzy_match',
                 'establish_correspondence', 'make_correspondence', 'assert_correspondence', 'upgrade_candidate',
                 'cached_disputes', 'dispute_cache', '_DISPUTE_CACHE', 'parse_dispute_flag', 'mark_disputed',
                 'conflicts_between_artefacts', 'source_conflicts')
STATUS_COLS = ('disputed', 'dispute', 'resolved', 'current', 'chosen', 'preferred', 'agreed', 'winner')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_pd_')
    eng = create_engine(f'sqlite:///{Path(d) / "t.db"}')

    @event.listens_for(eng, 'connect')
    def _fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def run(db):
    s = _fresh()
    rob = db.Person(display_name='Rob')
    s.add(rob)
    s.commit()
    household = rob.party

    def utter(text, when='2026-04-02T09:00:00', origin=None):
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

    def held(h, as_of, origin_party, origin_utt):
        a = db.Artefact(held=True, content_hash=h, as_of=as_of)
        s.add(a)
        s.commit()
        pr = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=a.id, object_party_id=origin_party.id)
        s.add(pr)
        s.commit()
        s.add(db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=origin_utt.id))
        s.commit()
        return a

    def read(a, process=None, party=None, when=datetime(2026, 4, 2)):
        r = db.Reading(artefact_id=a.id, reader_process=process, reader_party_id=party.id if party else None, read_at=when)
        s.add(r)
        s.commit()
        return r

    def line(reading, kind, content, party):
        # a P-subject claim read from a line: subject the artefact's origin party, participants candidates
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                            subject_party_id=party.id, content=content, as_of='2026-03-31')
        s.add(pr)
        s.commit()
        s.add(db.EvidentiaryRelationship(proposition_id=pr.id, reading_id=reading.id))
        s.commit()
        return pr

    def corresponds(a, b, utterance=None, reading=None):
        pr = db.Proposition(kind=db.PROPOSITION_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_proposition_id=a.id, object_proposition_id=b.id)
        s.add(pr)
        s.commit()
        s.add(db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=utterance.id if utterance else None,
                                         reading_id=reading.id if reading else None))
        s.commit()
        return pr

    def groups_for(result, *prop_ids):
        want = set(prop_ids)
        return [g for g in result['groups'] if want <= {p[0] for p in g['propositions']}]

    chase, u_chase = mint_party('Chase, the mortgage lender.')

    print('\n1. Absences - the consumer chooses nothing, stores nothing, has no threshold, establishes nothing\n')
    check('no chooser, threshold, cache, resolver or establishing helper exists on the module',
          not any(hasattr(db, n) for n in CHOOSER_NAMES))
    check('no dispute / current / resolved status column or attribute exists on Proposition, Reading or Artefact',
          not any(any(w == c.name or w in c.name for w in STATUS_COLS) for m in (db.Proposition, db.Reading, db.Artefact) for c in m.__table__.columns)
          and not any(hasattr(m, w) for m in (db.Proposition, db.Reading, db.Artefact) for w in STATUS_COLS))
    check('the classifications are structural names, not thresholds',
          db.PARSE_CONTENT_DISPUTE == 'content_dispute' and db.PARSE_KIND_DISPUTE == 'kind_dispute'
          and db.PARSE_AGREED_ONE_SOURCE == 'agreed_one_source' and db.PARSE_OMISSION == 'omission'
          and db.PARSE_SINGLE_READING == 'single_reading' and not any(hasattr(db, n) for n in ('PARSE_THRESHOLD', 'SIMILARITY')))

    print('\n2. Pd13 / Pd1 / Pd2 - one reading; a candidate dispute; an established dispute\n')
    stmt = held('h-march', '2026-03-31', chase, u_chase)
    r1 = read(stmt, process='parser/4', when=datetime(2026, 4, 2))
    p3 = line(r1, 'statement_figure', '$44,000', chase)
    p_pay = line(r1, 'payment_due', '$1,412', chase)
    one = db.parse_disputes(s, stmt)
    check('Pd13: one reading - "single_reading", one observation, one source; no group, no omission, never "agreed"',
          one['observations'] == 1 and one['classification'] == [db.PARSE_SINGLE_READING] and one['groups'] == []
          and one['omissions'] == [] and one['sources'] == 1)
    r2 = read(stmt, process='parser/5', when=datetime(2026, 5, 1))
    p3b = line(r2, 'statement_figure', '$4,400', chase)
    p_payb = line(r2, 'payment_due', '$1,412', chase)
    c_cand = corresponds(p3b, p3, reading=r2)                   # the matcher's position match - a candidate
    c_cand2 = corresponds(p_payb, p_pay, reading=r2)
    n_props, n_corr = s.query(db.Proposition).count(), s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CORRESPONDS).count()
    two = db.parse_disputes(s, stmt)
    g = groups_for(two, p3.id, p3b.id)
    check('Pd1: a candidate correspondence with differing content is a CANDIDATE content dispute - both contents, both readings, state candidate',
          len(g) == 1 and g[0]['state'] == db.GROUP_CANDIDATE and g[0]['classification'] == [db.PARSE_CONTENT_DISPUTE]
          and g[0]['contents'] == ['$4,400', '$44,000'] and g[0]['readings'] == [r1.id, r2.id])
    check('Pd1: the candidate was not upgraded - referent() still reports the propositions separate-with-candidates; nothing was written',
          db.referent(s, p3)[0] == db.REFERENT_CANDIDATES and s.query(db.Proposition).count() == n_props
          and s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CORRESPONDS).count() == n_corr)
    check("Pd1: each proposition is reported with its reading's provenance - parser/4 on 4/2 and parser/5 on 5/1",
          two['readings'] == [(r1.id, 'parser/4', datetime(2026, 4, 2)), (r2.id, 'parser/5', datetime(2026, 5, 1))]
          and {(p[0], p[3]) for p in g[0]['propositions']} == {(p3.id, r1.id), (p3b.id, r2.id)})
    u_same = utter("Yes - that's the same balance line, both times.", '2026-05-02T09:00:00')
    corresponds(p3, p3b, utterance=u_same)
    est = db.parse_disputes(s, stmt)
    g = groups_for(est, p3.id, p3b.id)
    check('Pd2: an established correspondence with differing content is an ESTABLISHED content dispute; the referent is one line; NOTHING is chosen',
          len(g) == 1 and g[0]['state'] == db.GROUP_ESTABLISHED and g[0]['classification'] == [db.PARSE_CONTENT_DISPUTE]
          and len(g[0]['contents']) == 2 and 'chosen' not in g[0] and 'current' not in g[0] and 'value' not in g[0])
    check('Pd2: the later reading, the newer parser and the household are not preferred - the answer names both contents and no winner',
          set(g[0]['contents']) == {'$44,000', '$4,400'} and not any(k in g[0] for k in ('winner', 'preferred', 'latest', 'resolved')))

    print('\n3. Pd3 / Pd8 - agreement is one source; three readings do not vote\n')
    g = groups_for(est, p_pay.id, p_payb.id)
    check('Pd3: two readings agree on the payment line - agreed_one_source (candidate); sources stays 1; no corroboration anywhere',
          len(g) == 1 and g[0]['classification'] == [db.PARSE_AGREED_ONE_SOURCE] and g[0]['contents'] == ['$1,412']
          and est['sources'] == 1 and 'corroborated' not in g[0] and 'strength' not in g[0])
    r3 = read(stmt, process='parser/6', when=datetime(2026, 6, 1))
    p3c = line(r3, 'statement_figure', '$44,000', chase)
    corresponds(p3c, p3, utterance=utter('And the June re-parse is the same line again.', '2026-06-02T09:00:00'))
    three = db.parse_disputes(s, stmt)
    g = groups_for(three, p3.id, p3b.id, p3c.id)
    check('Pd8: three readings, two contents, ONE referent, ONE source - reported as such; the two $44,000s do not outvote the $4,400',
          len(g) == 1 and g[0]['state'] == db.GROUP_ESTABLISHED and len(g[0]['propositions']) == 3
          and g[0]['contents'] == ['$4,400', '$44,000'] and g[0]['readings'] == [r1.id, r2.id, r3.id]
          and three['sources'] == 1 and g[0]['classification'] == [db.PARSE_CONTENT_DISPUTE]
          and not any(k in g[0] for k in ('majority', 'votes', 'consensus')))

    print('\n4. Pd4 / Pd5 - a kind dispute; an omission is not a dispute and not zero\n')
    p_k1 = line(r1, 'statement_figure', '$2,100', chase)
    p_k2 = line(r2, 'payment_due', '$2,100', chase)
    corresponds(p_k1, p_k2, utterance=utter('Line 5 - same line, both readings.', '2026-05-03T09:00:00'))
    kd = db.parse_disputes(s, stmt)
    g = groups_for(kd, p_k1.id, p_k2.id)
    check('Pd4: the readings disagree about KIND (statement_figure vs payment_due) with the same content - a kind dispute, distinct from a content dispute',
          len(g) == 1 and g[0]['classification'] == [db.PARSE_KIND_DISPUTE] and g[0]['kinds'] == sorted(['statement_figure', 'payment_due'])
          and g[0]['contents'] == ['$2,100'])
    p_footer = line(r1, 'footer_note', 'Payments received after 3/28 are not reflected.', chase)
    om = db.parse_disputes(s, stmt)
    o = [x for x in om['omissions'] if x['proposition'][0] == p_footer.id]
    check('Pd5: a line reading 1 has and readings 2 and 3 lack is an OMISSION - present in r1, absent in r2 and r3; not a dispute, not zero, not retracted',
          len(o) == 1 and o[0]['present_in'] == [r1.id] and o[0]['absent_in'] == [r2.id, r3.id]
          and not groups_for(om, p_footer.id) and o[0]['proposition'][2] != '0' and 'retracted' not in o[0])

    print('\n5. Pd6 / Pd7 - two artefacts are not a parse dispute; testimony is not a reading\n')
    stmt_apr = held('h-april', '2026-04-30', chase, u_chase)
    r_apr = read(stmt_apr, process='parser/5', when=datetime(2026, 5, 3))
    p_apr = line(r_apr, 'statement_figure', '$43,100', chase)
    corresponds(p_apr, p3, utterance=utter('(a wrong but assertable claim: the April balance line IS the March one)', '2026-05-04T09:00:00'))
    six = db.parse_disputes(s, stmt)
    g = groups_for(six, p3.id, p3b.id)
    check("Pd6: a proposition read from ANOTHER artefact is excluded from the group and named under beyond_artefact - two artefacts are a source question, not a parse dispute",
          len(g) == 1 and p_apr.id not in {p[0] for p in g[0]['propositions']} and g[0].get('beyond_artefact') == [p_apr.id]
          and g[0]['contents'] == ['$4,400', '$44,000'])
    apr = db.parse_disputes(s, stmt_apr)
    check("Pd6: from the April statement's side the same - its one observation, the March members beyond it; no cross-artefact dispute manufactured",
          apr['classification'] == [db.PARSE_SINGLE_READING] and apr['groups'] == [])
    t = db.Proposition(kind='statement_figure', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,   # 9D-i F2: the party-subject figure, not the ruled balance
                       subject_party_id=chase.id, content='$44,000', as_of='2026-03-31')
    s.add(t)
    s.commit()
    s.add(db.EvidentiaryRelationship(proposition_id=t.id, utterance_id=utter('The March balance was $44,000 - I checked.', '2026-05-05T09:00:00').id))
    s.commit()
    seven = db.parse_disputes(s, stmt)
    check("Pd7: Rob's testimony is not observed by any reading of the artefact - it appears in no group and no omission; agreement with a reading is not this consumer's to compare",
          all(t.id not in {p[0] for p in g['propositions']} for g in seven['groups'])
          and all(o['proposition'][0] != t.id for o in seven['omissions']))

    print("\n6. Pd9 / Pd10 - a person's transcription is a reading; a retracted correspondence is contested and stops\n")
    r_rob = read(stmt, party=household, when=datetime(2026, 6, 5))
    p_rob = line(r_rob, 'statement_figure', '$44,000', chase)
    corresponds(p_rob, p3, utterance=utter("My own transcription of that line.", '2026-06-05T09:05:00'))
    nine = db.parse_disputes(s, stmt)
    g = groups_for(nine, p3.id, p_rob.id)
    check("Pd9: Rob's transcription is a reading by a party - in the group as a reading, provenance ('party', id); not promoted to testimony, not ranked above the parser",
          len(g) == 1 and any(rd[0] == r_rob.id and rd[1] == ('party', household.id) for rd in nine['readings'])
          and (p_rob.id, r_rob.id) in {(p[0], p[3]) for p in g[0]['propositions']}
          and not any(k in g[0] for k in ('rank', 'ranked', 'testimony', 'preferred')))
    retr = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                          subject_utterance_id=u_same.id)
    s.add(retr)
    s.commit()
    s.add(db.EvidentiaryRelationship(proposition_id=retr.id, utterance_id=utter('No - those were two different lines after all.', '2026-06-06T09:00:00').id))
    s.commit()
    ten = db.parse_disputes(s, stmt)
    g = groups_for(ten, p3.id, p3b.id)
    check('Pd10: the correspondence retracted - the group reads CONTESTED; both propositions still reported; the derivation does not infer two lines and does not drop the dispute',
          len(g) == 1 and g[0]['state'] == db.GROUP_CONTESTED and {p3.id, p3b.id} <= {p[0] for p in g[0]['propositions']}
          and db.referent(s, p3)[0] == db.REFERENT_CONTESTED)

    print('\n7. Pd11 / Pd14 - recomputed on read; the null model is a correctness oracle\n')
    before = db.parse_disputes(s, stmt)
    again = db.parse_disputes(s, stmt)
    check('Pd11: two reads give the same answer and nothing was written between them - no cache, no persisted list',
          before == again and not any(hasattr(db, n) for n in ('cached_disputes', 'dispute_cache', '_DISPUTE_CACHE'))
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(('parse_dispute', 'dispute'))).count() == 0)
    null_stmt = held('h-null', '2026-02-28', chase, u_chase)
    ra = read(null_stmt, process='parser/5', when=datetime(2026, 3, 2))
    rb = read(null_stmt, process='parser/5', when=datetime(2026, 3, 9))
    lines_a = [line(ra, k, c, chase) for k, c in (('statement_figure', '$9,910'), ('payment_due', '$300'), ('minimum', '$35'))]
    lines_b = [line(rb, k, c, chase) for k, c in (('statement_figure', '$9,910'), ('payment_due', '$300'), ('minimum', '$35'))]
    u_lines = utter('Same three lines, both parses.', '2026-03-10T09:00:00')
    for a, b in zip(lines_a, lines_b):
        corresponds(a, b, utterance=u_lines)
    zero = db.parse_disputes(s, null_stmt)
    check('Pd14 (null model): an identical re-parse yields ZERO disputes - three groups, all agreed_one_source, no omissions',
          len(zero['groups']) == 3 and all(g['classification'] == [db.PARSE_AGREED_ONE_SOURCE] for g in zero['groups'])
          and zero['omissions'] == [] and zero['sources'] == 1)
    rc = read(null_stmt, process='parser/6', when=datetime(2026, 3, 16))
    lines_c = [line(rc, k, c, chase) for k, c in (('statement_figure', '$9,190'), ('payment_due', '$300'), ('minimum', '$35'))]
    u_lines2 = utter('And the same three lines in the third parse.', '2026-03-17T09:00:00')
    for a, c in zip(lines_a, lines_c):
        corresponds(a, c, utterance=u_lines2)
    one_changed = db.parse_disputes(s, null_stmt)
    disputes = [g for g in one_changed['groups'] if db.PARSE_CONTENT_DISPUTE in g['classification']]
    check('Pd14 (null model): one changed figure yields exactly ONE dispute, on the balance line, with both contents - structural, no threshold consulted',
          len(disputes) == 1 and disputes[0]['kinds'] == ['statement_figure'] and disputes[0]['contents'] == ['$9,190', '$9,910']
          and len([g for g in one_changed['groups'] if g['classification'] == [db.PARSE_AGREED_ONE_SOURCE]]) == 2)
    check("Pd14: '$9,190' vs '$9,910' - a difference a similarity threshold would swallow - is a dispute because the contents differ, full stop",
          disputes[0]['contents'] != [disputes[0]['contents'][0]])

    print('\n8. Pd12 - the resolution() hazard: the reading-level answer exists; the 1.x projection names it and does not read past it\n')
    import core.classification as cl
    check("Pd12: resolution()'s contract names its domain (distinct source stances) and the reading-level derivation it may not read past - no logic change",
          'parse_disputes' in (cl.resolution.__doc__ or '') and 'HAZARD_AUDIT H4' in (cl.resolution.__doc__ or ''))
    check('Pd12: the derivation returns the dispute with provenance and no choice - readings -> correspondence state -> disagreement -> provenance -> no choice',
          all({'state', 'propositions', 'readings', 'kinds', 'contents', 'classification'} <= set(g) for g in ten['groups'])
          and not any(k in g for g in ten['groups'] for k in ('resolved', 'resolver', 'chosen', 'current')))

    print('\n9. The consumer establishes nothing; the record is untouched by reading it\n')
    n_props, n_ev, n_corr = (s.query(db.Proposition).count(), s.query(db.EvidentiaryRelationship).count(),
                             s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CORRESPONDS).count())
    for a in (stmt, stmt_apr, null_stmt):
        db.parse_disputes(s, a)
    check('reading the derivation three times over three artefacts wrote no proposition, no evidence and no correspondence',
          s.query(db.Proposition).count() == n_props and s.query(db.EvidentiaryRelationship).count() == n_ev
          and s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CORRESPONDS).count() == n_corr)
    check('the derivation calls nothing that establishes: its source contains no session.add, no Proposition(, no EvidentiaryRelationship(',
          (lambda src: 'session.add' not in src and 'Proposition(' not in src.replace('Proposition,', '') and 'EvidentiaryRelationship(' not in src
             and 'commit' not in src)(__import__('inspect').getsource(db.parse_disputes)))

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
