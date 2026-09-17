"""aboutness - the executable trace of `gw 2.0/CONSUMER_DERIVATIONS.md` pass 7C (ruled 2026-09-16).

A proposition is about an identity by exactly four things and nothing else: structural (its own established
participant of an identity type), asserted (an established proposition_concerns), derived through the artefact
level (the artefact's ESTABLISHED concern set for the type is exactly one), derived through ESTABLISHED
correspondence (two recordings of one claim are one claim; a candidate link stops the chain). Candidates never
reach; contested stops; several paths to one identity are one derivation; provenance labels are not an
ordering - conflicts are reported, never resolved; nothing is written, ranked or known.

What this slice can and cannot exercise
---------------------------------------
    Ac1  asserted concerns on a line: about O2 - asserted; participant untouched                     EXERCISED
    Ac2  testimony with an established participant: structural; no concerns claim may attach          EXERCISED
    Ac3  single-identity artefact, no line claim: derived (artefact) with links                        EXERCISED
    Ac4  two-identity artefact, no line claim: candidates {O1, O2}; nothing chosen                     EXERCISED
    Ac5  no artefact claim, line-level assertion: asserted; the artefact level not needed             EXERCISED
    Ac6  established correspondence carries: derived (correspondence); no row copied                   EXERCISED
    Ac7  candidate correspondence: candidate only                                                      EXERCISED
    Ac8  correspondence retracted: contested -> undetermined; stops                                    EXERCISED
    Ac9  reading-sourced concerns candidates: listed, never about-ness, never promoted by count        EXERCISED
    Ac10 convergence: P about X and Q about X -> nothing about P ~ Q                                   EXERCISED
    Ac11 the Ab7 invariant: the participant stays candidates                                           EXERCISED
    Ac12 composition: P about O, O in respect of X -> P is not about X                                 EXERCISED
    Ac13 the origin party's roles transmit nothing                                                     EXERCISED
    Ac14 level conflict: asserted O3 beside artefact {O1, O2}: conflict reported, not resolved         EXERCISED
    Ac15 retraction: about O1; the retracted O2 assertion is undetermined; P byte-identical            EXERCISED
    Ac16 re-reading without correspondence: no about-ness                                              EXERCISED
    Ac17 the derivation has no knowing and no asserter                                                 EXERCISED
    Ac18 transitivity through established links: every link listed                                    EXERCISED
    Ac19 no path at all: 'no about-ness established' vs 'candidates only'                              EXERCISED
    Ac20 the null model: exactly the assertions; nothing from content                                  EXERCISED
    Ac21 "exactly one" scoped to the requested type                                                    EXERCISED
    Ac22 "nothing contradicts" defined: a candidate artefact concern neither blocks nor unsettles      EXERCISED
    Ac23 the mixed chain: a candidate link stops the chain                                             EXERCISED
    Ac24 the cycle: one component, one derivation                                                      EXERCISED
    Ac25 two established paths to one identity: one derived entry, two paths, no count                EXERCISED
    Ac26 established and candidate coexisting: both reported; neither wins nor unsettles               EXERCISED
    Ac27 a party subject is not structural about-ness                                                  EXERCISED
    Ac28 a sibling proposition's asserted concerns transmits nothing through the reading               EXERCISED
    the wiring guard: AST (no session write / no constructor) + a full row-content snapshot            EXERCISED
    level-consistency characterisation (7D), strength (7E), traversal of ruled relations (7F)          NOT BUILT

Run:  python tests/test_aboutness_fixture.py
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


CARRIER_NAMES = ('carry_aboutness', 'copy_concerns', 'propagate_concerns', 'set_participant', 'resolve_aboutness',
                 'about_of', 'is_about', 'aboutness_of', 'rank_aboutness', 'preferred_aboutness', 'aboutness_strength',
                 'aboutness_cache', 'match_heading', 'match_content', 'infer_about', 'about_via_relation',
                 'about_via_origin', 'resolve_levels', 'establish_concerns')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_about_')
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

    def owe(text):
        o = db.Obligation(minted_by_id=utter(text).id)
        s.add(o)
        s.commit()
        return o

    def incur(text):
        x = db.Expense(minted_by_id=utter(text).id)
        s.add(x)
        s.commit()
        return x

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

    def read(a, process='parser/5', when=datetime(2026, 4, 2)):
        r = db.Reading(artefact_id=a.id, reader_process=process, read_at=when)
        s.add(r)
        s.commit()
        return r

    def line(reading, kind, content, party):
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                            subject_party_id=party.id, content=content, as_of='2026-03-31')
        s.add(pr)
        s.commit()
        s.add(db.EvidentiaryRelationship(proposition_id=pr.id, reading_id=reading.id))
        s.commit()
        return pr

    def evidence(pr, utterance=None, reading=None):
        e = db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=utterance.id if utterance else None,
                                       reading_id=reading.id if reading else None)
        s.add(e)
        s.commit()
        return e

    def a_concerns(a, utterance=None, reading=None, **slot):
        pr = db.Proposition(kind=db.ARTEFACT_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=a.id, **slot)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utterance, reading=reading)
        return pr

    def p_concerns(p, utterance=None, reading=None, **slot):
        pr = db.Proposition(kind=db.PROPOSITION_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_proposition_id=p.id, **slot)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utterance, reading=reading)
        return pr

    def corr(a, b, utterance=None, reading=None):
        pr = db.Proposition(kind=db.PROPOSITION_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_proposition_id=a.id, object_proposition_id=b.id)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utterance, reading=reading)
        return pr

    def retract(u, text):
        r = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                           subject_utterance_id=u.id)
        s.add(r)
        s.commit()
        evidence(r, utterance=utter(text, '2026-04-20T09:00:00'))

    def derived_ids(res, typ='obligation'):
        return {d['id']: d for d in res['derived'] if d['type'] == typ}

    def cand_ids(res, typ='obligation'):
        return {c[1] for c in res['candidates'] if c[0] == typ}

    def snapshot():
        out = {}
        for name, table in sorted(db.Base.metadata.tables.items()):
            out[name] = sorted(tuple(str(v) for v in row) for row in s.execute(table.select()))
        return out

    def writes_in(func):
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

    cu, u_cu = mint_party('The credit union.')
    chase, u_chase = mint_party('Chase.')
    aetna, u_aetna = mint_party('Aetna.')
    o1 = owe('My mortgage with the credit union.')
    o2 = owe('My HELOC with the credit union.')
    o3 = owe('The car loan.')
    X = incur('The ER visit.')

    print('\n1. Absences - no carrier, no ranker, no matcher, no cache, no establishing helper\n')
    check('no carrier / participant-setter / ranker / matcher / cache / establishing helper exists on the module',
          not any(hasattr(db, n) for n in CARRIER_NAMES))
    check('about-ness ranges over the four identity types and a party is not one of them',
          set(db.ABOUT_IDENTITY_TYPES) == {'obligation', 'payment', 'expense', 'plan'})

    print('\n2. Ac1 / Ac11 / Ac5 - asserted on a line; the participant untouched; no artefact claim needed\n')
    A = held('h-combo', '2026-03-31', cu, u_cu)
    a_concerns(A, utterance=utter('That is my credit-union statement - mortgage and HELOC.'), object_obligation_id=o1.id)
    a_concerns(A, utterance=utter('(both)'), object_obligation_id=o2.id)
    r1 = read(A)
    P3 = line(r1, 'balance', '$44,000', cu)
    c3 = p_concerns(P3, utterance=utter('Line 3 is the HELOC.'), object_obligation_id=o2.id)
    ab = db.aboutness(s, P3)
    check('Ac1: an established line-level assertion - about O2, ASSERTED, with the claim and Rob as asserter; the artefact-level pair {O1, O2} is not a choice',
          [(t, i) for t, i, _, _ in ab['asserted']] == [('obligation', o2.id)] and ab['asserted'][0][2] == c3.id and ab['asserted'][0][3] == household.id
          and not derived_ids(ab))
    check('Ac11: the Ab7 invariant - P3\'s participant stays candidates; the derivation never reports the assertion as structural',
          P3.object_state == db.PARTICIPANT_CANDIDATES and ab['structural'] == [] and P3.object_obligation_id is None)
    B = held('h-bank', '2026-03-31', chase, u_chase)                # no artefact-level concerns claim at all
    rB = read(B)
    P7 = line(rB, 'movement', 'CHASE MTG -1,412.00', chase)
    p1 = db.Payment(minted_by_id=utter("That's my March payment.").id)
    s.add(p1)
    s.commit()
    p_concerns(P7, utterance=utter('Line 7 is that payment.'), object_payment_id=p1.id)
    ab7 = db.aboutness(s, P7)
    check('Ac5: with no artefact-level claim at all, the line-level assertion is enough - about p, ASSERTED; nothing manufactured at the artefact level',
          [(t, i) for t, i, _, _ in ab7['asserted']] == [('payment', p1.id)] and ab7['derived'] == [] and ab7['candidates'] == [])

    print('\n3. Ac2 / Ac27 - structural about-ness; a party subject is not structural\n')
    T = db.Proposition(kind='balance', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                       subject_obligation_id=o2.id, content='about $44k')
    s.add(T)
    s.commit()
    evidence(T, utterance=utter('The HELOC balance is about $44k.'))
    abT = db.aboutness(s, T)
    check('Ac2: testimony with an established obligation participant - STRUCTURAL about O2; nothing asserted, derived or candidate',
          abT['structural'] == [('obligation', o2.id)] and abT['asserted'] == [] and abT['derived'] == [] and abT['candidates'] == [])
    check('Ac2 / Pa10: a proposition_concerns claim may not attach where the participant of that type is established',
          _refused(s, db.Proposition(kind=db.PROPOSITION_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_proposition_id=T.id, object_obligation_id=o1.id)))
    check('Ac27: a P-subject line (subject the party Aetna) has NO structural about-ness - a party is not an identity about-ness ranges over',
          db.aboutness(s, P3)['structural'] == [] and P3.subject_party_id == cu.id)

    print('\n4. Ac3 / Ac4 / Ac21 / Ac22 / Ac28 - the artefact level: exactly one, of the requested type, established\n')
    S1 = held('h-single', '2026-03-31', cu, u_cu)
    a_concerns(S1, utterance=utter('My mortgage statement.'), object_obligation_id=o1.id)
    rS = read(S1)
    Q2 = line(rS, 'payment_due', '$1,412', cu)
    ab3 = db.aboutness(s, Q2)
    d3 = derived_ids(ab3)
    check('Ac3: a single-obligation artefact and no line claim - about O1, DERIVED (artefact), with the reading, the artefact and the concerns claim as links; nothing asserted',
          set(d3) == {o1.id} and d3[o1.id]['paths'][0]['path'] == db.ABOUT_PATH_ARTEFACT
          and [l[0] for l in d3[o1.id]['paths'][0]['links']] == ['reading', 'artefact', 'artefact_concerns'] and ab3['asserted'] == [])
    check('Ac3: the derivation wrote no proposition_concerns row and set no participant',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=Q2.id).count() == 0
          and Q2.object_state == db.PARTICIPANT_CANDIDATES)
    P4 = line(r1, 'escrow', '$310', cu)                            # from the two-obligation statement, no line claim
    ab4 = db.aboutness(s, P4)
    check('Ac4: a two-obligation artefact and no line claim - CANDIDATES {O1, O2}; nothing derived; nothing chosen; note "candidates only"',
          cand_ids(ab4) == {o1.id, o2.id} and not derived_ids(ab4) and ab4['note'] == 'candidates only'
          and {c[2] for c in ab4['candidates']} == {'artefact concerns several'})
    E1 = incur('The dental cleaning.')
    S2 = held('h-multi-type', '2026-04-30', cu, u_cu)
    a_concerns(S2, utterance=utter('That statement is the mortgage.'), object_obligation_id=o1.id)
    a_concerns(S2, utterance=utter('...and it lists the cleaning.'), object_expense_id=E1.id)
    a_concerns(S2, utterance=utter('...and that payment.'), object_payment_id=p1.id)
    r2m = read(S2)
    Q5 = line(r2m, 'balance', '$43,900', cu)
    ab21 = db.aboutness(s, Q5)
    check('Ac21: "exactly one" is scoped to the requested type - O1 for obligations, E1 for expenses, p for payments, each derived; identities of other types are neither multiplicity nor conflict',
          set(derived_ids(ab21, 'obligation')) == {o1.id} and set(derived_ids(ab21, 'expense')) == {E1.id}
          and set(derived_ids(ab21, 'payment')) == {p1.id} and ab21['conflicts'] == [] and ab21['candidates'] == [])
    S3 = held('h-nothing-contradicts', '2026-05-31', cu, u_cu)
    a_concerns(S3, utterance=utter('That one is the mortgage.'), object_obligation_id=o1.id)
    r3 = read(S3)
    a_concerns(S3, reading=r3, object_obligation_id=o2.id)          # the parser's heading match: a CANDIDATE artefact claim
    Q6 = line(r3, 'balance', '$43,800', cu)
    ab22 = db.aboutness(s, Q6)
    check('Ac22: "nothing contradicts" defined - one established concern (O1) beside a CANDIDATE concern (O2): derived O1; O2 listed as a candidate; not undetermined, not conflict; the candidate is not resolved',
          set(derived_ids(ab22)) == {o1.id} and cand_ids(ab22) == {o2.id} and ab22['undetermined'] == [] and ab22['conflicts'] == []
          and {c[2] for c in ab22['candidates']} == {'candidate artefact concerns'})
    Q2b = line(rS, 'escrow', '$300', cu)                            # a sibling line on the single-obligation statement
    p_concerns(Q2b, utterance=utter('Line 2 of that one concerns the mortgage.'), object_obligation_id=o1.id)
    Q2c = line(rS, 'rate', '6.1%', cu)
    ab28 = db.aboutness(s, Q2c)
    check("Ac28: a sibling proposition's asserted concerns transmits nothing through the reading - Q2c is derived through the ARTEFACT (S1 concerns O1 only), never through Q2b; the reading is a carrier of access, not an edge",
          set(derived_ids(ab28)) == {o1.id} and all(l[0] != 'proposition_concerns' for l in derived_ids(ab28)[o1.id]['paths'][0]['links'])
          and ab28['asserted'] == [])

    print('\n5. Ac6 / Ac7 / Ac8 / Ac16 / Ac18 / Ac23 / Ac24 / Ac25 - correspondence: established carries, candidate stops, contested halts\n')
    r1b = read(A, process='parser/6', when=datetime(2026, 5, 1))
    P3b = line(r1b, 'balance', '$4,400', cu)
    ab16 = db.aboutness(s, P3b)
    check('Ac16: a re-reading with no correspondence claim - NO about-ness; nothing inherited from position; the artefact level offers only candidates {O1, O2}',
          ab16['asserted'] == [] and not derived_ids(ab16) and cand_ids(ab16) == {o1.id, o2.id})
    cc = corr(P3b, P3, reading=r1b)                                  # the parser's position match - a candidate
    ab7c = db.aboutness(s, P3b)
    check('Ac7: a CANDIDATE correspondence to P3 (which is asserted about O2) - O2 reaches P3b as a candidate only, source "candidate correspondence"; nothing derived',
          (('obligation', o2.id, 'candidate correspondence', P3.id) in ab7c['candidates']) and not derived_ids(ab7c))
    u_same = utter('Same line, both readings.', '2026-05-02T09:00:00')
    corr(P3, P3b, utterance=u_same)
    ab6 = db.aboutness(s, P3b)
    d6 = derived_ids(ab6)
    check('Ac6: the correspondence ESTABLISHED - P3b is about O2, DERIVED (correspondence), with the correspondence claim and the concerns claim on P3 as links; no row copied; P3b\'s participant untouched',
          set(d6) == {o2.id} and d6[o2.id]['paths'][0]['path'] == db.ABOUT_PATH_CORRESPONDENCE
          and [l[0] for l in d6[o2.id]['paths'][0]['links']] == ['proposition_corresponds', 'proposition_concerns']
          and s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=P3b.id).count() == 0
          and P3b.object_state == db.PARTICIPANT_CANDIDATES and ab6['asserted'] == [])
    r1c = read(A, process='parser/7', when=datetime(2026, 6, 1))
    P3c = line(r1c, 'balance', '$44,000', cu)
    corr(P3b, P3c, utterance=utter('And the June parse is the same line.', '2026-06-02T09:00:00'))
    ab18 = db.aboutness(s, P3c)
    check('Ac18: transitivity through established links - P3c reaches O2 through the component; the correspondence and the concerns claim are listed as links',
          set(derived_ids(ab18)) == {o2.id} and derived_ids(ab18)[o2.id]['paths'][0]['path'] == db.ABOUT_PATH_CORRESPONDENCE)
    corr(P3c, P3, utterance=utter('(closing the loop - all three are one line)', '2026-06-03T09:00:00'))
    ab24 = db.aboutness(s, P3c)
    check('Ac24: the cycle P3 ~ P3b ~ P3c ~ P3 - one component, ONE derived O2, one path; no infinite traversal, no duplicate, no "three recordings = three about-nesses"',
          set(derived_ids(ab24)) == {o2.id} and len(derived_ids(ab24)[o2.id]['paths']) == 1 and ab24['conflicts'] == [])
    # Ac23 - the mixed chain: P ~ Q established, Q ~ R candidate, R concerns X
    M = held('h-mixed', '2026-06-30', cu, u_cu)
    rM = read(M)
    Pm, Qm, Rm = line(rM, 'balance', '$1', cu), line(rM, 'balance', '$2', cu), line(rM, 'balance', '$3', cu)
    corr(Pm, Qm, utterance=utter('P and Q are one line.', '2026-07-01T09:00:00'))
    corr(Qm, Rm, reading=rM)                                         # candidate
    p_concerns(Rm, utterance=utter('R is the car loan.', '2026-07-01T09:01:00'), object_obligation_id=o3.id)
    ab23 = db.aboutness(s, Pm)
    check('Ac23: the mixed chain - X reaches P as a CANDIDATE (through the candidate link Q ~ R), never derived; the chain stops at Q',
          not derived_ids(ab23) and ('obligation', o3.id, 'candidate correspondence', Rm.id) in ab23['candidates'])
    # Ac25 - two established paths to one identity
    N1 = held('h-n1', '2026-07-31', cu, u_cu)
    N2 = held('h-n2', '2026-07-31', cu, u_cu)
    a_concerns(N1, utterance=utter('N1 is the car loan statement.'), object_obligation_id=o3.id)
    a_concerns(N2, utterance=utter('N2 is the car loan statement too.'), object_obligation_id=o3.id)
    rN1, rN2 = read(N1), read(N2)
    Pn, Qn = line(rN1, 'balance', '$9,900', cu), line(rN2, 'balance', '$9,900', cu)
    corr(Pn, Qn, utterance=utter('Same line on both copies.', '2026-08-01T09:00:00'))
    p_concerns(Qn, utterance=utter('Q is the car loan line.', '2026-08-01T09:01:00'), object_obligation_id=o3.id)
    ab25 = db.aboutness(s, Pn)
    d25 = derived_ids(ab25)
    check('Ac25: two established paths to one identity (artefact; correspondence) - ONE derived entry with TWO paths listed; no multiplicity, no rank, no count key',
          set(d25) == {o3.id} and {pth['path'] for pth in d25[o3.id]['paths']} == {db.ABOUT_PATH_ARTEFACT, db.ABOUT_PATH_CORRESPONDENCE}
          and not any(k in d25[o3.id] for k in ('count', 'support', 'strength', 'rank', 'weight')))
    retract(u_same, 'No - those were two different lines after all.')
    ab8 = db.aboutness(s, P3b)
    check('Ac8: the correspondence retracted - the component reads contested; O2 is UNDETERMINED for P3b (reason contested correspondence); nothing derived; the consumer stops',
          not derived_ids(ab8) and any(u[0] == 'obligation' and u[1] == o2.id and u[2] == 'contested correspondence' for u in ab8['undetermined']))

    print('\n6. Ac9 / Ac10 / Ac12 / Ac13 / Ac14 / Ac15 / Ac26 - candidates, convergence, composition, roles, conflict, retraction, coexistence\n')
    H = held('h-headings', '2026-03-31', cu, u_cu)
    rH = read(H)
    lines = [line(rH, 'line', f'row {i}', cu) for i in range(5)]
    for ln in lines:
        p_concerns(ln, reading=rH, object_obligation_id=o1.id)     # the parser's heading match, five times
    ab9 = db.aboutness(s, lines[0])
    check('Ac9: five reading-sourced concerns candidates naming O1 - CANDIDATES, listed with their reading; not about-ness; five candidates are one process, not promotion by count',
          cand_ids(ab9) == {o1.id} and not derived_ids(ab9) and ab9['asserted'] == [] and ab9['note'] == 'candidates only')
    Pa, Qa = line(rH, 'line', 'a', cu), line(rH, 'line', 'b', cu)
    p_concerns(Pa, utterance=utter('a is the mortgage.'), object_obligation_id=o1.id)
    p_concerns(Qa, utterance=utter('b is the mortgage.'), object_obligation_id=o1.id)
    check('Ac10: P about O1 and Q about O1 - nothing about P ~ Q: referent() still separate; the derivation manufactures no correspondence',
          db.referent(s, Pa)[0] == db.REFERENT_SEPARATE and db.referent(s, Qa)[0] == db.REFERENT_SEPARATE)
    rel = db.Proposition(kind=db.OBLIGATION_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                         subject_obligation_id=o2.id, object_expense_id=X.id)
    s.add(rel)
    s.commit()
    evidence(rel, utterance=utter('The HELOC paid for the ER visit.'))
    ab12 = db.aboutness(s, P3)
    check('Ac12: P3 concerns O2 and O2 is in respect of X - P3 is NOT about X by derivation; about-ness stops at the endpoint it reaches (D\'.11)',
          not derived_ids(ab12, 'expense') and cand_ids(ab12, 'expense') == set() and not any(t == 'expense' for t, _, _, _ in ab12['asserted']))
    ent = db.Proposition(kind='entitled_party', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                         subject_party_id=cu.id, object_obligation_id=o3.id, as_of='2026-01-01')
    s.add(ent)
    s.commit()
    evidence(ent, utterance=utter('The credit union holds the car loan too.'))
    ab13 = db.aboutness(s, Q2)
    check("Ac13: the artefact's origin party (the credit union) is E of O3 as well - Q2's about-ness is still only O1 (derived via S1); the origin party's roles transmit nothing",
          set(derived_ids(ab13)) == {o1.id} and o3.id not in cand_ids(ab13))
    P3x = line(r1, 'balance', '$12,000', cu)                          # from the two-obligation statement A
    p_concerns(P3x, utterance=utter('That line is the car loan.'), object_obligation_id=o3.id)
    ab14 = db.aboutness(s, P3x)
    check('Ac14: asserted O3 beside an artefact level {O1, O2} - about O3 ASSERTED; the artefact candidates listed; the CONFLICT reported with its sources and NOT resolved',
          [(t, i) for t, i, _, _ in ab14['asserted']] == [('obligation', o3.id)] and cand_ids(ab14) == {o1.id, o2.id}
          and len(ab14['conflicts']) == 1 and set(ab14['conflicts'][0]['identities']) == {o1.id, o2.id, o3.id}
          and ab14['conflicts'][0]['identities'][o3.id] == [db.ABOUT_ASSERTED])
    u_line3 = s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c3.id).one().utterance
    retract(u_line3, 'No - line 3 was the mortgage, not the HELOC.')
    p_concerns(P3, utterance=utter('Line 3 is the mortgage.', '2026-04-21T09:00:00'), object_obligation_id=o1.id)
    ab15 = db.aboutness(s, P3)
    check('Ac15: the O2 assertion retracted and O1 asserted - about O1 ASSERTED; the retracted O2 is UNDETERMINED (retracted assertion), not a second about-ness; P3 byte-identical',
          [(t, i) for t, i, _, _ in ab15['asserted']] == [('obligation', o1.id)]
          and any(u[0] == 'obligation' and u[1] == o2.id and u[2] == 'retracted assertion' for u in ab15['undetermined'])
          and P3.content == '$44,000' and P3.object_state == db.PARTICIPANT_CANDIDATES)
    # Ac26 - established and candidate coexisting
    C1 = held('h-coexist', '2026-08-31', cu, u_cu)
    rC = read(C1)
    Pc, Qc = line(rC, 'balance', '$5', cu), line(rC, 'balance', '$6', cu)
    p_concerns(Pc, utterance=utter('P is the mortgage.', '2026-09-01T09:00:00'), object_obligation_id=o1.id)
    p_concerns(Qc, utterance=utter('Q is the HELOC.', '2026-09-01T09:01:00'), object_obligation_id=o2.id)
    corr(Pc, Qc, reading=rC)                                          # candidate
    ab26 = db.aboutness(s, Pc)
    check('Ac26: established X beside a candidate path to Y - asserted O1 AND candidate O2, side by side; O1 not made undetermined by the candidate; O2 not suppressed by the established result; no conflict (a candidate is not a claim)',
          [(t, i) for t, i, _, _ in ab26['asserted']] == [('obligation', o1.id)] and ('obligation', o2.id, 'candidate correspondence', Qc.id) in ab26['candidates']
          and ab26['undetermined'] == [] and ab26['conflicts'] == [])

    print('\n7. Ac17 / Ac19 / Ac20 - no knowing; where the failure appears; the null model\n')
    check('Ac17: a derived about-ness has no asserter and no strength - the derived entries carry paths and links only',
          all(set(d) == {'type', 'id', 'paths'} for d in ab6['derived'] + ab25['derived'] + ab3['derived'])
          and not any(hasattr(db, n) for n in ('aboutness_strength', 'aboutness_knowing')))
    Z = held('h-nothing', '2026-09-30', cu, u_cu)                    # no artefact concerns, no line claims
    rZ = read(Z)
    Pz = line(rZ, 'balance', '$0', cu)
    ab19 = db.aboutness(s, Pz)
    check("Ac19: no path at all - 'no about-ness established' (distinct from 'candidates only'); no default to the artefact's origin",
          ab19['note'] == 'no about-ness established' and ab19['structural'] == [] and ab19['asserted'] == []
          and ab19['derived'] == [] and ab19['candidates'] == [] and ab19['undetermined'] == [])
    NM = held('h-null', '2026-10-31', cu, u_cu)
    rNM = read(NM)
    nl = [line(rNM, 'balance', f'${i}', cu) for i in range(4)]
    for i, ln in enumerate(nl[:3]):
        p_concerns(ln, utterance=utter(f'null line {i}', '2026-11-01T09:00:00'), object_obligation_id=(o1, o2, o3)[i].id)
    nm = [db.aboutness(s, ln) for ln in nl]
    check('Ac20 (null model): an asserted-only corpus yields exactly the assertions, each ASSERTED; the un-asserted line yields nothing - no derivation from content, position or order',
          [[(t, i) for t, i, _, _ in r['asserted']] for r in nm[:3]] == [[('obligation', o1.id)], [('obligation', o2.id)], [('obligation', o3.id)]]
          and all(r['derived'] == [] for r in nm) and nm[3]['note'] == 'no about-ness established')

    print('\n8. The wiring guard - AST + a full row-content snapshot\n')
    before = snapshot()
    for pr in (P3, P3b, P3c, Q2, Q5, Q6, Pm, Pn, P3x, Pc, Pz, T):
        db.aboutness(s, pr)
    check('reading the derivation twelve times left every row of every table byte-for-byte identical',
          snapshot() == before)
    check('the 7C wiring guard is executable (AST): aboutness() and its helper call no session write method and construct no mapped class',
          writes_in(db.aboutness) == [] and writes_in(db._about_direct) == [])

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
