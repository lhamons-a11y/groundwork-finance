"""independence - the executable trace of `gw 2.0/CONSUMER_DERIVATIONS.md` pass 7B (ruled 2026-09-16).

A three-valued derivation between ORIGINS, for ONE proposition: independent (two distinct established
origins, each knowing, each chain established) · not independent (the grounds resolve to one origin - shown
as one origin entry with multiplicity > 1) · undetermined (a chain or origin candidate, contested or
unasserted - never defaulted). Origin from the assertion's provenance, never from who is speaking; a
reading conveys the artefact's origin; a process is never an origin; correspondence collapses; a candidate
correspondence leaves a pair undetermined; not a score; never stored; establishes nothing.

What this slice can and cannot exercise
---------------------------------------
    In1  same artefact, two readings: one origin, multiplicity 2, no pair                        EXERCISED
    In2  same origin, duplicated evidence (one utterance twice; two utterances): one origin      EXERCISED
    In3  same origin through two artefacts (two EOBs from Aetna): one origin                     EXERCISED
    In4  two genuinely different knowing origins agreeing: INDEPENDENT - and nothing more        EXERCISED
    In5  two parties repeating one EOB (readings of it): one origin, two channels               EXERCISED
    In5' the same two parties each from their own knowledge: two origins, independent            EXERCISED
    In6  the classifier's proposal vs Rob: the process is no origin; the bank is not knowing     EXERCISED
    In7  correspondence: (a) artefacts established one -> one origin; (b) parties established
         one -> one origin; (c) candidate party correspondence -> the pair UNDETERMINED           EXERCISED
    In8  one origin, five downstream rows: one origin entry, multiplicity 5                      EXERCISED
    In9  an artefact whose origin is only a candidate: undetermined, not false                   EXERCISED
    In10 a retracted origin utterance / a retracted assertion: contested -> undetermined         EXERCISED
    In11 process-generated rows with no origin: listed as readers, never origins                 EXERCISED
    In12 per proposition: the same artefacts, different answers for PR and for necessity         EXERCISED
    In13 mediated chains through two servicers to one E                                          NOT EXERCISED - the
         acknowledgment kind and its knowing relation are stand-ins (D4 open); nothing is faked
    In14 three knowing origins: three pairs, no count, no score                                  EXERCISED
    In15 the 1.x distinct = {e.source} named as a count of channel types, not repaired          EXERCISED
    In16 RA5 reader independence for P-subject: fenced, not decided                              NOT DECIDED (asserted absent)
    In17 one claim: "one origin - no second term"                                                EXERCISED
    In18 the null model: one-document corpus -> zero independent pairs; distinct knowing parties -> exactly those pairs  EXERCISED
    In4' Rob asserts the EOB's origin: Rob is the assertion's provenance, Aetna the origin       EXERCISED
    In7d the candidate correspondence encountered in the OPPOSITE direction: the same result      EXERCISED
    In9' two unrelated unresolved grounds: two entries, never collapsed into one origin None      EXERCISED
    multiplicity is structural cardinality, never support; readers are trace only; None is no origin  EXERCISED
    absences: no score / count / rank / stored relation / default / establishing call             EXERCISED
    the wiring guard: AST-based (no session write / no constructor) + a full row-content snapshot  EXERCISED

Run:  python tests/test_independence_fixture.py
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


SCORE_NAMES = ('corroboration', 'corroborated', 'n_sources', 'source_count', 'independent_count', 'count_sources',
               'strength_from_independence', 'independence_score', 'confidence', 'majority', 'rank_origins',
               'preferred_origin', 'best_origin', 'independent_of', 'INDEPENDENT_OF', 'is_independent',
               'establish_independence', 'store_independence', 'independence_cache', 'default_independent',
               'assume_independent', 'assume_not_independent')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_ind_')
    eng = create_engine(f'sqlite:///{Path(d) / "t.db"}')

    @event.listens_for(eng, 'connect')
    def _fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA synchronous=OFF')          # throwaway DB: no fsync per commit
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def run(db):
    s = _fresh()
    rob = db.Person(display_name='Rob')
    kim = db.Person(display_name='Kim')
    s.add_all([rob, kim])
    s.commit()
    household, kim_party = rob.party, kim.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'},
               'patient_responsibility': {'institution'}, 'date_of_service': {'person', 'institution'},
               'copay_paid': {'person'}, 'nature': {'person'}, 'statement_figure': {'institution'}, 'balance': {'institution'}}

    def utter(text, when='2026-03-06T09:00:00', origin=None):
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

    def held(h, as_of, origin_party=None, origin_utt=None):
        a = db.Artefact(held=True, content_hash=h, as_of=as_of)
        s.add(a)
        s.commit()
        if origin_party is not None:
            pr = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                subject_artefact_id=a.id, object_party_id=origin_party.id)
            s.add(pr)
            s.commit()
            s.add(db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=origin_utt.id))
            s.commit()
        return a

    def read(a, process=None, party=None, when=datetime(2026, 3, 12)):
        r = db.Reading(artefact_id=a.id, reader_process=process, reader_party_id=party.id if party else None, read_at=when)
        s.add(r)
        s.commit()
        return r

    def world(kind, content, subject_expense=None, subject_party=None):
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                            subject_expense_id=subject_expense.id if subject_expense else None,
                            subject_party_id=subject_party.id if subject_party else None, content=content, as_of='2026-02-14')
        s.add(pr)
        s.commit()
        return pr

    def evidence(pr, utterance=None, reading=None):
        e = db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=utterance.id if utterance else None,
                                       reading_id=reading.id if reading else None)
        s.add(e)
        s.commit()
        return e

    def corresponds(kind, a_col, b_col, a, b, utterance=None, reading=None):
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            **{a_col: a.id, b_col: b.id})
        s.add(pr)
        s.commit()
        s.add(db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=utterance.id if utterance else None,
                                         reading_id=reading.id if reading else None))
        s.commit()
        return pr

    def origins_of(res):
        return {o['origin']: o for o in res['origins']}

    def snapshot():
        # every row of every table, by content - not cardinality: an in-place UPDATE must be visible
        out = {}
        for name, table in sorted(db.Base.metadata.tables.items()):
            out[name] = sorted(tuple(str(v) for v in row) for row in s.execute(table.select()))
        return out

    def writes_in(func):
        # AST, not substring: any call to a session write method, or any construction of a mapped class
        import ast, inspect, textwrap
        tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
        write_methods = {'add', 'add_all', 'commit', 'flush', 'merge', 'delete', 'execute', 'bulk_save_objects',
                         'bulk_insert_mappings', 'bulk_update_mappings', 'refresh', 'expunge'}
        constructors = {'Proposition', 'Party', 'Artefact', 'Reading', 'Utterance', 'EvidentiaryRelationship',
                        'Obligation', 'Payment', 'Expense', 'Plan', 'Person'}
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                # a write METHOD is one called on the session (or a session-like receiver), never a set's .add
                if (isinstance(fn, ast.Attribute) and fn.attr in write_methods
                        and isinstance(fn.value, ast.Name) and fn.value.id in ('session', 's', 'sess', 'db_session', 'conn', 'connection')):
                    found.append(fn.attr)
                if isinstance(fn, ast.Name) and fn.id in constructors:
                    found.append(fn.id)
                if isinstance(fn, ast.Attribute) and fn.attr in constructors:
                    found.append(fn.attr)
            if isinstance(node, ast.Name) and node.id in ('update', 'insert', 'delete') and isinstance(getattr(node, 'ctx', None), ast.Load):
                found.append(node.id)
        return found

    aetna, u_aetna = mint_party('Aetna, our insurer.')
    mercy, u_mercy = mint_party('Mercy Hospital.')
    bank, u_bank = mint_party('Our bank.')
    X = db.Expense(minted_by_id=utter('We took Kim to the ER on Feb 14.', '2026-02-15T09:00:00').id)
    s.add(X)
    s.commit()
    # 9D-ii F2(ii): these cases always meant "Aetna is knowing for an insurer's figure"; under the ruled role-at-date
    # relation that is a fact the record must hold - Aetna's insurer_of role on X - not a party type. Added, not inferred.
    def insurer_of(party, x, text):
        pr = db.Proposition(kind=db.INSURER_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_party_id=party.id, object_expense_id=x.id, as_of='2026-01-01')
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utter(text, '2026-02-15T09:01:00'))
    insurer_of(aetna, X, 'Aetna is the insurer for the ER visit.')

    print('\n1. Absences - not a score, not stored, not a relation, not a default\n')
    check('no score, count, rank, default, cache, stored-relation or establishing helper exists on the module',
          not any(hasattr(db, n) for n in SCORE_NAMES))
    check('independence is not a ruled kind and no independence column exists anywhere - a consumer answer, not an ontology relation',
          not any('independen' in k for k in db.RULED_KINDS)
          and not any('independen' in c.name for m in (db.Proposition, db.Artefact, db.Party, db.Reading, db.Utterance) for c in m.__table__.columns))
    check('the verdict vocabulary is three-valued and structural: independent / not_independent / undetermined',
          {db.INDEPENDENT, db.NOT_INDEPENDENT, db.INDEPENDENCE_UNDETERMINED} == {'independent', 'not_independent', 'undetermined'})

    print('\n2. In17 / In1 / In2 - one claim; two readings of one artefact; duplicated evidence\n')
    eob = held('h-eob', '2026-03-10', aetna, u_aetna)
    r1 = read(eob, process='parser/4')
    pr = world('patient_responsibility', '$412', subject_expense=X)
    evidence(pr, reading=r1)
    one = db.independence(s, pr, KNOWING)
    check("In17: one claim, one origin (Aetna, via the EOB's established origin) - 'one origin - no second term'; no pair; knowing",
          [o['origin'] for o in one['origins']] == [aetna.id] and one['pairs'] == [] and one['note'] == 'one origin - no second term'
          and one['origins'][0]['knowing'] == db.STRENGTH_KNOWING and one['origins'][0]['state'] == db.CHAIN_ESTABLISHED)
    r2 = read(eob, process='parser/5', when=datetime(2026, 4, 1))
    evidence(pr, reading=r2)
    two = db.independence(s, pr, KNOWING)
    check('In1: two readings of one artefact - ONE origin entry with multiplicity 2 (not independent); no pair; readers listed, never origins',
          len(two['origins']) == 1 and two['origins'][0]['multiplicity'] == 2 and two['pairs'] == []
          and sorted(two['readers']) == ['parser/4', 'parser/5'])
    dos = world('date_of_service', '2026-02-14', subject_expense=X)
    u_dos = utter('It was February 14.', '2026-02-15T09:01:00')
    evidence(dos, utterance=u_dos)
    evidence(dos, utterance=u_dos)                                          # the same utterance evidenced twice
    evidence(dos, utterance=utter('Feb 14 - I said so in September too.', '2026-09-01T09:00:00'))
    dup = db.independence(s, dos, KNOWING)
    check('In2: one utterance twice and a second utterance by the same party - ONE origin (Rob), multiplicity 3; recency and row count are nothing',
          len(dup['origins']) == 1 and dup['origins'][0]['origin'] == household.id and dup['origins'][0]['multiplicity'] == 3 and dup['pairs'] == [])

    print('\n3. In3 / In8 - one origin through two artefacts; one origin, five rows\n')
    eob2 = held('h-eob-reprocessed', '2026-03-24', aetna, u_aetna)
    r3 = read(eob2, process='parser/5', when=datetime(2026, 3, 25))
    evidence(pr, reading=r3)
    three = db.independence(s, pr, KNOWING)
    check('In3: two artefacts, both from Aetna - still ONE origin (multiplicity 3); distinct documents are not independence',
          len(three['origins']) == 1 and three['origins'][0]['origin'] == aetna.id and three['origins'][0]['multiplicity'] == 3
          and {g[3] for g in three['origins'][0]['grounds']} == {eob.id, eob2.id})
    r_kim = read(eob, party=kim_party, when=datetime(2026, 3, 13))                # Kim transcribes the EOB - a reading by a party
    evidence(pr, reading=r_kim)
    r_pipe = read(eob, process='pipeline/import', when=datetime(2026, 3, 14))
    evidence(pr, reading=r_pipe)
    five = db.independence(s, pr, KNOWING)
    check('In8: read twice, reprocessed, transcribed by Kim, imported by the pipeline - five rows, ONE origin (Aetna), multiplicity 5; no pair',
          len(five['origins']) == 1 and five['origins'][0]['multiplicity'] == 5 and five['pairs'] == [])
    check('FENCE: multiplicity is structural cardinality of grounds on one resolved origin and nothing else - no support / strength / corroboration / confidence key anywhere in the result, and no self-pair',
          not any(k in five for k in ('support', 'strength', 'corroboration', 'confidence', 'score', 'weight'))
          and not any(k in five['origins'][0] for k in ('support', 'strength', 'corroboration', 'confidence', 'score', 'weight'))
          and not any(a == b for a, b, _ in five['pairs']))
    check('FENCE: readers is explanatory trace only - three process readers and one origin is one source; readers never appear among origins',
          len([r for r in five['readers']]) >= 3 and len(five['origins']) == 1
          and not any(isinstance(o['origin'], str) for o in five['origins']))

    print("\n4. In4 / In5 / In5' - two origins agreeing; two parties repeating one source; the same two parties from their own knowledge\n")
    bill = held('h-bill', '2026-03-05', mercy, u_mercy)
    r_bill = read(bill, process='parser/5')
    evidence(dos, reading=r_bill)                                          # Mercy's bill: date of service 02/14
    four = db.independence(s, dos, KNOWING)
    check('In4: Rob (was there) and Mercy (served) agree on the date of service - two origins, both knowing, both chains established: INDEPENDENT - and that is the whole answer',
          {o['origin'] for o in four['origins']} == {household.id, mercy.id}
          and four['pairs'] == [(household.id, mercy.id, db.INDEPENDENT)] and four['note'] is None
          and not any(k in four for k in ('score', 'strength', 'corroboration', 'count')))
    check("In4': the EOB's origin was asserted by Rob's utterance ('this EOB came from Aetna') - Rob is the assertion's provenance, Aetna the artefact's origin; Rob appears as no origin for the EOB's figure",
          (lambda o: set(o) == {aetna.id} and household.id not in o)(origins_of(db.independence(s, pr, KNOWING)))
          and s.query(db.EvidentiaryRelationship).join(db.Proposition, db.Proposition.id == db.EvidentiaryRelationship.proposition_id)
               .filter(db.Proposition.kind == db.ARTEFACT_ORIGIN, db.Proposition.subject_artefact_id == eob.id).one().utterance.origin_party_id == household.id)
    r_rob_eob = read(eob, party=household, when=datetime(2026, 3, 15))
    evidence(pr, reading=r_rob_eob)                                        # Rob reads the EOB: $412
    five_b = db.independence(s, pr, KNOWING)
    check('In5: Rob and Kim each repeat the EOB (readings by two parties) - still ONE origin (Aetna); two channels are not two origins',
          len(five_b['origins']) == 1 and five_b['origins'][0]['origin'] == aetna.id
          and {g[1] for g in five_b['origins'][0]['grounds']} == {'reading'} and five_b['pairs'] == [])
    copay = world('copay_paid', '$30', subject_expense=X)
    evidence(copay, utterance=utter('The copay was $30 - I paid it.', '2026-02-15T09:02:00'))
    evidence(copay, utterance=utter('It was $30 - I was at the desk.', '2026-02-15T09:03:00', origin=kim_party))
    own = db.independence(s, copay, KNOWING)
    check("In5': the same two people, each from their own knowledge (no chain to a document) - TWO origins, INDEPENDENT: origin is read from the assertion's provenance, never guessed from who is speaking",
          {o['origin'] for o in own['origins']} == {household.id, kim_party.id}
          and own['pairs'] == [(household.id, kim_party.id, db.INDEPENDENT)])

    print('\n5. In6 / In11 / In12 - a process is no origin; the bank is not knowing; per proposition\n')
    stmt = held('h-stmt', '2026-02-28', bank, u_bank)
    r_stmt = read(stmt, process='classifier/mcc')
    nature = world('nature', 'health', subject_expense=X)
    evidence(nature, reading=r_stmt)                                       # the classifier's proposal, MCC 5912
    evidence(nature, utterance=utter('Yes, that was health.', '2026-03-01T09:00:00'))
    six = db.independence(s, nature, KNOWING)
    o6 = origins_of(six)
    check("In6 / In11: the process contributes no origin; the reading reaches the artefact's established origin, which is the bank - not knowing for nature; the process is listed as a reader, never an origin; Rob is the only knowing origin - 'one origin - no second term'",
          set(o6) == {bank.id, household.id} and o6[bank.id]['knowing'] == db.STRENGTH_NOT_KNOWING
          and o6[household.id]['knowing'] == db.STRENGTH_KNOWING and six['pairs'] == []
          and six['note'] == 'one origin - no second term' and 'classifier/mcc' in six['readers'])
    pr12 = world('patient_responsibility', '$412', subject_expense=X)
    evidence(pr12, reading=r1)
    evidence(pr12, utterance=utter('I owe $412 - the EOB said so.', '2026-03-11T09:00:00'))
    nec = world('nature', 'necessary care', subject_expense=X)
    evidence(nec, utterance=utter('The ER visit was necessary care.', '2026-03-11T09:01:00'))
    evidence(nec, reading=r_bill)
    twelve_pr = db.independence(s, pr12, KNOWING)
    twelve_nec = db.independence(s, nec, KNOWING)
    o_pr, o_nec = origins_of(twelve_pr), origins_of(twelve_nec)
    check("In12: for PR $412 - Aetna (via the EOB) is knowing, Rob's utterance is an origin NOT knowing for an insurer's figure: no pair, one knowing origin",
          o_pr[aetna.id]['knowing'] == db.STRENGTH_KNOWING and o_pr[household.id]['knowing'] == db.STRENGTH_NOT_KNOWING
          and twelve_pr['pairs'] == [] and twelve_pr['note'] == 'one origin - no second term')
    check("In12: for necessary care - Rob is knowing and Mercy's bill is NOT: the same parties, the opposite answer; independence is per proposition, never per document or party",
          o_nec[household.id]['knowing'] == db.STRENGTH_KNOWING and o_nec[mercy.id]['knowing'] == db.STRENGTH_NOT_KNOWING
          and twelve_nec['pairs'] == [])

    print('\n6. In7 - correspondence: artefacts one, parties one, a candidate leaves the pair undetermined\n')
    eob_dup = held('h-eob-again', '2026-03-10', aetna, u_aetna)            # the same EOB uploaded twice (X1)
    r_dup = read(eob_dup, process='parser/5', when=datetime(2026, 3, 30))
    pr7 = world('patient_responsibility', '$412', subject_expense=X)
    evidence(pr7, reading=r1)
    evidence(pr7, reading=r_dup)
    corresponds(db.ARTEFACT_CORRESPONDS, 'subject_artefact_id', 'object_artefact_id', eob, eob_dup,
                utterance=utter('That is the same EOB, uploaded twice.', '2026-03-31T09:00:00'))
    seven_a = db.independence(s, pr7, KNOWING)
    check('In7(a): two artefacts established as one - one artefact, ONE origin, multiplicity 2; no pair',
          len(seven_a['origins']) == 1 and seven_a['origins'][0]['origin'] == aetna.id and seven_a['origins'][0]['multiplicity'] == 2)
    aetna2, u_aetna2 = mint_party('Aetna Health Inc.')
    insurer_of(aetna2, X, 'Aetna Health Inc. is the insurer for the ER visit.')   # 9D-ii F2(ii): the second party's role, as the case presupposes
    letter = held('h-aetna-letter', '2026-04-02', aetna2, u_aetna2)
    r_letter = read(letter, process='parser/5', when=datetime(2026, 4, 3))
    pr7b = world('patient_responsibility', '$412', subject_expense=X)
    evidence(pr7b, reading=r1)
    evidence(pr7b, reading=r_letter)
    before_corr = db.independence(s, pr7b, KNOWING)
    check("In7(b) baseline: 'Aetna' and 'Aetna Health Inc.' as two parties - two knowing origins, INDEPENDENT (nothing yet says they are one)",
          before_corr['pairs'] == [(aetna.id, aetna2.id, db.INDEPENDENT)])
    corresponds(db.PARTY_CORRESPONDS, 'subject_party_id', 'object_party_id', aetna2, aetna, reading=r_letter)   # the letterhead match - a candidate
    cand = db.independence(s, pr7b, KNOWING)
    check('In7(c): a CANDIDATE party correspondence between the two origins - the pair is UNDETERMINED, not false and not true',
          cand['pairs'] == [(aetna.id, aetna2.id, db.INDEPENDENCE_UNDETERMINED)])
    # In7(d): the same candidate encountered in the OPPOSITE direction, on a fresh pair of parties
    cig1, u_c1 = mint_party('Cigna.')
    cig2, u_c2 = mint_party('Cigna Healthcare Inc.')
    insurer_of(cig1, X, 'Cigna is the insurer for the ER visit.')                   # 9D-ii F2(ii): the roles the case presupposes
    insurer_of(cig2, X, 'Cigna Healthcare Inc. is the insurer for the ER visit.')
    l1 = held('h-cigna-1', '2026-04-05', cig1, u_c1)
    l2 = held('h-cigna-2', '2026-04-06', cig2, u_c2)
    rl1, rl2 = read(l1, process='parser/5'), read(l2, process='parser/5')
    pr7d = world('patient_responsibility', '$88', subject_expense=X)
    evidence(pr7d, reading=rl1)
    evidence(pr7d, reading=rl2)
    corresponds(db.PARTY_CORRESPONDS, 'subject_party_id', 'object_party_id', cig1, cig2, reading=rl2)     # subject/object the other way round
    seven_d = db.independence(s, pr7d, KNOWING)
    check("In7(d): the candidate correspondence with subject and object the other way round gives exactly the same result - UNDETERMINED; the consumer does not depend on which side of the correspondence a party sits",
          seven_d['pairs'] == [(cig1.id, cig2.id, db.INDEPENDENCE_UNDETERMINED)])
    corresponds(db.PARTY_CORRESPONDS, 'subject_party_id', 'object_party_id', aetna2, aetna,
                utterance=utter('Aetna Health Inc. is Aetna - same insurer.', '2026-04-04T09:00:00'))
    est = db.independence(s, pr7b, KNOWING)
    check('In7(b): the parties established as one - ONE origin, multiplicity 2, no pair; nothing merged in the record',
          len(est['origins']) == 1 and est['origins'][0]['multiplicity'] == 2 and est['pairs'] == []
          and s.get(db.Party, aetna2.id) is not None and s.get(db.Party, aetna.id) is not None)

    print('\n7. In9 / In10 - unknown is undetermined, not false; contested is undetermined\n')
    newco_letter = held('h-newco', '2026-05-01')                              # no origin asserted by anyone
    r_newco = read(newco_letter, process='parser/5', when=datetime(2026, 5, 2))
    chase, u_chase = mint_party('Chase.')
    chase_stmt = held('h-chase', '2026-05-01', chase, u_chase)
    r_chase = read(chase_stmt, process='parser/5', when=datetime(2026, 5, 2))
    bal = world('statement_figure', '$1,900', subject_party=chase)
    evidence(bal, reading=r_chase)
    evidence(bal, reading=r_newco)
    nine = db.independence(s, bal, KNOWING)
    o9 = origins_of(nine)
    check("In9: the NewCo letter's origin is unasserted - its ground has no origin and chain 'unestablished'; Chase is the one knowing origin; no pair says independent and none says not",
          None in o9 and o9[None]['state'] == db.CHAIN_UNESTABLISHED and o9[chase.id]['knowing'] == db.STRENGTH_KNOWING
          and nine['pairs'] == [] and nine['note'] == 'one origin - no second term')
    other_letter = held('h-someone-else', '2026-05-01')                     # a second artefact with no origin asserted
    r_other = read(other_letter, process='parser/5', when=datetime(2026, 5, 2))
    evidence(bal, reading=r_other)
    nine_two = db.independence(s, bal, KNOWING)
    unresolved = [o for o in nine_two['origins'] if o['origin'] is None]
    check("In9': two unrelated unresolved grounds are TWO entries with origin None and multiplicity 1 each - None is not an origin identity and unresolved grounds are never collapsed into one",
          len(unresolved) == 2 and all(o['multiplicity'] == 1 for o in unresolved) and nine_two['pairs'] == []
          and {o['grounds'][0][3] for o in unresolved} == {newco_letter.id, other_letter.id})
    newco, u_newco = mint_party('NewCo Servicing.')
    self_desc = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                               subject_artefact_id=newco_letter.id, object_party_id=newco.id)
    s.add(self_desc)
    s.commit()
    evidence(self_desc, reading=r_newco)                                      # the letterhead says NewCo - a candidate origin
    nine_c = db.independence(s, bal, KNOWING)
    newco_entry = [o for o in nine_c['origins'] if o['origin'] is None and o['grounds'][0][3] == newco_letter.id]
    check("In9: with the letterhead's self-description the origin is a CANDIDATE - chain 'candidate', still no pair: undetermined, never defaulted (the other unresolved ground stays its own entry)",
          len(newco_entry) == 1 and newco_entry[0]['state'] == db.CHAIN_CANDIDATE and nine_c['pairs'] == []
          and len([o for o in nine_c['origins'] if o['origin'] is None]) == 2)
    u_from = utter('That letter came from NewCo.', '2026-05-03T09:00:00')
    evidence(self_desc, utterance=u_from)
    nine_e = db.independence(s, bal, KNOWING)
    check('In9 -> established: Rob asserts the origin - NewCo and Chase are two knowing origins, INDEPENDENT',
          nine_e['pairs'] == [(chase.id, newco.id, db.INDEPENDENT)])
    retr = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                          subject_utterance_id=u_from.id)
    s.add(retr)
    s.commit()
    evidence(retr, utterance=utter("I'm not sure that letter was NewCo's after all.", '2026-05-04T09:00:00'))
    ten = db.independence(s, bal, KNOWING)
    check("In10: the origin assertion retracted - the NewCo chain is CONTESTED and the pair with Chase is explicitly UNDETERMINED (not absent, not independent, not 'not independent')",
          origins_of(ten)[newco.id]['state'] == db.CHAIN_CONTESTED
          and ten['pairs'] == [(chase.id, newco.id, db.INDEPENDENCE_UNDETERMINED)])
    dos2 = world('date_of_service', '2026-02-14', subject_expense=X)
    u_r = utter('Feb 14.', '2026-02-16T09:00:00')
    evidence(dos2, utterance=u_r)
    evidence(dos2, reading=r_bill)
    retr2 = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                           subject_utterance_id=u_r.id)
    s.add(retr2)
    s.commit()
    evidence(retr2, utterance=utter('Actually I am not sure of the date.', '2026-02-17T09:00:00'))
    ten_b = db.independence(s, dos2, KNOWING)
    check("In10: Rob's own assertion retracted - his origin's chain is CONTESTED; the pair with Mercy is UNDETERMINED",
          origins_of(ten_b)[household.id]['state'] == db.CHAIN_CONTESTED
          and ten_b['pairs'] == [(household.id, mercy.id, db.INDEPENDENCE_UNDETERMINED)])

    print('\n8. In14 / In18 - three origins are three pairs and no number; the null model\n')
    dos3 = world('date_of_service', '2026-02-14', subject_expense=X)
    evidence(dos3, utterance=utter('February 14.', '2026-02-18T09:00:00'))
    evidence(dos3, reading=r_bill)
    evidence(dos3, reading=r1)
    fourteen = db.independence(s, dos3, KNOWING)
    check('In14: three knowing origins (Rob, Mercy, Aetna) - three INDEPENDENT pairs and no count, rank, score or strength',
          len(fourteen['origins']) == 3 and len(fourteen['pairs']) == 3 and all(v == db.INDEPENDENT for _, _, v in fourteen['pairs'])
          and not any(k in fourteen for k in ('score', 'strength', 'corroboration', 'count', 'rank', 'n')))
    # null model 1: a one-document corpus - every row a re-read, quote, transcription or import of the EOB
    null_pr = world('patient_responsibility', '$412', subject_expense=X)
    for r in (r1, r2, r3, r_kim, r_pipe, r_rob_eob, r_dup):
        evidence(null_pr, reading=r)
    n1 = db.independence(s, null_pr, KNOWING)
    check('In18 (null model 1): seven rows, all of one document - ZERO independent pairs, one origin, multiplicity 7',
          n1['pairs'] == [] and len(n1['origins']) == 1 and n1['origins'][0]['multiplicity'] == 7)
    # null model 2: distinct knowing parties, each with an established chain - exactly those pairs
    null_dos = world('date_of_service', '2026-02-14', subject_expense=X)
    evidence(null_dos, utterance=utter('Feb 14, I was there.', '2026-02-19T09:00:00'))
    evidence(null_dos, utterance=utter('Feb 14, so was I.', '2026-02-19T09:01:00', origin=kim_party))
    evidence(null_dos, reading=r_bill)
    n2 = db.independence(s, null_dos, KNOWING)
    check('In18 (null model 2): three distinct knowing origins with established chains - exactly the three pairs, all independent; a correctness oracle, no threshold',
          len(n2['pairs']) == 3 and all(v == db.INDEPENDENT for _, _, v in n2['pairs']))

    print('\n9. In15 / In16 - the 1.x count named; RA5 left fenced\n')
    import inspect
    import core.classification as cl
    src = inspect.getsource(cl._state_from) if hasattr(cl, '_state_from') else inspect.getsource(cl)
    # SOURCE-PRESERVATION GUARD, not a semantic test: the exact 1.x spelling is kept so the audit language is
    # not silently "fixed" into a smarter count; a formatting change here breaks the gate on purpose.
    check('In15 (source-preservation guard, not a semantic test): the 1.x distinct = {e.source} still exists and is named as a count of CHANNEL TYPES pointing at the 2.0 derivation - not repaired by counting differently',
          'distinct = {e.source for e in supporting}' in src and 'CHANNEL TYPES' in src and 'core.database.independence' in src)
    check('In16 (RA5): reader independence for P-subject is not decided - no reader-independence helper, and readers are listed, never origins',
          not any(hasattr(db, n) for n in ('reader_independence', 'readers_independent', 'reader_corroboration'))
          and all(o['origin'] is None or isinstance(o['origin'], int) for o in five['origins']))

    print('\n10. The consumer establishes nothing; the record is untouched by reading it\n')
    before = snapshot()
    for prop in (pr, dos, copay, nature, pr7b, bal, dos3, null_pr):
        db.independence(s, prop, KNOWING)
    check('the 7B wiring guard is executable (AST, not substring): independence() calls no session write method (add / commit / flush / merge / execute / delete / bulk_*) and constructs no mapped class; no update / insert / delete construct is referenced',
          writes_in(db.independence) == [])
    check('reading the derivation eight times left every row of every table byte-for-byte identical - not merely the counts',
          snapshot() == before)

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
