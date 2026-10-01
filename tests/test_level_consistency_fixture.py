"""level_consistency - the executable trace of `gw 2.0/CONSUMER_DERIVATIONS.md` pass 7D (ruled 2026-09-16).

A REPORT, not a verdict. For one artefact and one identity type: the artefact's ESTABLISHED concern set and
every line read from it classified by whether its established about-ness (asserted, structural, or derived
through established correspondence - taken from aboutness() with provenance, the artefact-derived path
excluded as the artefact level itself) lies within that set: consistent · inconsistent · no_line_basis ·
no_level_basis · unresolved. Never a Boolean. Type-isolated. Candidates never raise an inconsistency;
contested stops; counts are descriptive; nothing decided, nothing written.

What this slice can and cannot exercise
---------------------------------------
    Ld1  {O1, O2} vs asserted O3: inconsistent, both sides named; nothing refused                    EXERCISED
    Ld2  {O1} vs asserted O2: inconsistent; nothing resolved by specificity or by the document       EXERCISED
    Ld3  {O1, O2} vs lines O1 and O2: consistent; two members are not a conflict                     EXERCISED
    Ld4  no artefact claim: no_level_basis - never "consistent"                                       EXERCISED
    Ld5  candidate artefact concern only: no_level_basis; the candidate listed; nothing inconsistent  EXERCISED
    Ld6  the artefact claim retracted: artefact side contested; outside lines unresolved              EXERCISED
    Ld7  correspondence-derived O2 vs {O1}: inconsistent with the derivation's source                 EXERCISED
    Ld8  P ~ P' asserted O1 / O2: a proposition disagreement, its own class, not a level              EXERCISED
    Ld9  an expense line under an obligation set: nothing cross-type                                  EXERCISED
    Ld10 structural O2 under {O1}: inconsistent                                                       EXERCISED
    Ld11 artefact claim by Rob, line by Kim: both named, neither ranked                               EXERCISED
    Ld12 three lines outside: three inconsistencies; a count as a fact; no verdict                    EXERCISED
    Ld13 recency decides nothing                                                                      EXERCISED
    Ld14 no about-ness / candidates only: no_line_basis; candidates never raise an inconsistency      EXERCISED
    Ld15 surfaced not stored: retract -> the next read is consistent; nothing written by 7D           EXERCISED
    Ld16 nothing on either level: no_level_basis + no_line_basis, never "consistent"                  EXERCISED
    Ld17 the null model: within-set corpus -> zero; one outlier -> exactly one                        EXERCISED
    Rob's six: the three-state distinction · contested STOP · candidates never · type isolation ·
               no Boolean · counts descriptive                                                        EXERCISED
    the wiring guard: AST (session receivers) + a full row-content snapshot                            EXERCISED
    which evidence wins (a later pass, if ever ruled), strength (7E), traversal (7F)                   NOT BUILT

Run:  python tests/test_level_consistency_fixture.py
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


DECIDER_NAMES = ('resolve_levels', 'prefer_level', 'prefer_artefact', 'prefer_line', 'winning_level', 'majority_level',
                 'level_confidence', 'level_weight', 'recommend_retraction', 'suggest_retraction', 'consistency_cache',
                 'is_consistent', 'consistent', 'mark_inconsistent', 'refuse_inconsistent', 'level_probability')
STATES = ('consistent', 'inconsistent', 'no_line_basis', 'no_level_basis', 'unresolved')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_lc_')
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

    def line(reading, kind, content, party, object_state=db.PARTICIPANT_CANDIDATES):
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=object_state,
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
        return evidence(pr, utterance=utterance, reading=reading), pr

    def p_concerns(p, utterance=None, reading=None, **slot):
        pr = db.Proposition(kind=db.PROPOSITION_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_proposition_id=p.id, **slot)
        s.add(pr)
        s.commit()
        return evidence(pr, utterance=utterance, reading=reading), pr

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

    def cls_of(rep, prop, typ='obligation'):
        return next(l['classification'] for l in rep['types'][typ]['lines'] if l['proposition'] == prop.id)

    def entry_of(rep, prop, typ='obligation'):
        return next(l for l in rep['types'][typ]['lines'] if l['proposition'] == prop.id)

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
    o1 = owe('My mortgage.')
    o2 = owe('My HELOC.')
    o3 = owe('The car loan.')
    e1 = incur('The dental cleaning.')

    print('\n1. Absences - no decider, no status, no cache, no Boolean\n')
    check('no level-preferring, majority, weight, suggestion, cache, refusal or Boolean helper exists on the module',
          not any(hasattr(db, n) for n in DECIDER_NAMES))
    check('the five report states are named and none is a Boolean',
          (db.LEVEL_CONSISTENT, db.LEVEL_INCONSISTENT, db.LEVEL_NO_LINE_BASIS, db.LEVEL_NO_LEVEL_BASIS, db.LEVEL_UNRESOLVED) == STATES)

    print("\n2. Rob's three-state distinction - {O1}/O1 consistent · {O1}/O2 inconsistent · {}/O1 no level basis\n")
    S1 = held('h-single', '2026-03-31', cu, u_cu)
    a_concerns(S1, utterance=utter('That is my mortgage statement.'), object_obligation_id=o1.id)
    rS = read(S1)
    L1 = line(rS, 'statement_figure', '$44,000', cu)
    L2 = line(rS, 'payment_due', '$1,412', cu)
    p_concerns(L1, utterance=utter('Line 1 is the mortgage.'), object_obligation_id=o1.id)
    p_concerns(L2, utterance=utter('Line 2 is the HELOC.'), object_obligation_id=o2.id)
    rep = db.level_consistency(s, S1)
    check('{O1} / line asserted O1 -> CONSISTENT',
          cls_of(rep, L1) == db.LEVEL_CONSISTENT and rep['types']['obligation']['artefact_state'] == db.ARTEFACT_SIDE_ESTABLISHED)
    check('Ld2: {O1} / line asserted O2 -> INCONSISTENT with both sides named - the line\'s O2 (asserted) against the artefact set [O1]; nothing resolved by specificity or by the document',
          cls_of(rep, L2) == db.LEVEL_INCONSISTENT and entry_of(rep, L2)['against'] == [o1.id]
          and entry_of(rep, L2)['identities'] == [(o2.id, db.ABOUT_ASSERTED)] and len(rep['types']['obligation']['inconsistencies']) == 1)
    B = held('h-bank', '2026-03-31', chase, u_chase)                # no artefact-level claim
    rB = read(B)
    L7 = line(rB, db.MOVEMENT, 'CHASE MTG -1,412.00', chase, object_state=db.PARTICIPANT_NONE)   # the ruled kind (BANK_LINE_KIND.md): no object; the tie Ab7's
    p_concerns(L7, utterance=utter('Line 7 is the mortgage.'), object_obligation_id=o1.id)
    repB = db.level_consistency(s, B)
    check('Ld4: {} / line asserted O1 -> NO_LEVEL_BASIS - never "consistent"; the artefact state is none',
          cls_of(repB, L7) == db.LEVEL_NO_LEVEL_BASIS and repB['types']['obligation']['artefact_state'] == db.ARTEFACT_SIDE_NONE
          and repB['types']['obligation']['inconsistencies'] == [])

    print('\n3. Ld1 / Ld3 / Ld11 - two-member sets; both parties named, neither ranked\n')
    A = held('h-combo', '2026-03-31', cu, u_cu)
    a_concerns(A, utterance=utter('That is my credit-union statement - mortgage and HELOC.'), object_obligation_id=o1.id)
    a_concerns(A, utterance=utter('(both)'), object_obligation_id=o2.id)
    rA = read(A)
    M1, M2, M3 = line(rA, 'statement_figure', '$44,000', cu), line(rA, 'statement_figure', '$9,100', cu), line(rA, 'statement_figure', '$12,000', cu)
    p_concerns(M1, utterance=utter('Line 1 is the mortgage.'), object_obligation_id=o1.id)
    p_concerns(M2, utterance=utter('Line 2 is the HELOC.'), object_obligation_id=o2.id)
    p_concerns(M3, utterance=utter('Line 3 is the car loan.', origin=kim_party), object_obligation_id=o3.id)
    repA = db.level_consistency(s, A)
    check('Ld3: {O1, O2} / lines O1 and O2 -> both CONSISTENT; a two-member set is not a conflict',
          cls_of(repA, M1) == db.LEVEL_CONSISTENT and cls_of(repA, M2) == db.LEVEL_CONSISTENT)
    check('Ld1 (Pa7): {O1, O2} / line asserted O3 -> INCONSISTENT; the O3 claim was not refused and is still in aboutness()',
          cls_of(repA, M3) == db.LEVEL_INCONSISTENT and entry_of(repA, M3)['against'] == sorted([o1.id, o2.id])
          and [(t, i) for t, i, _, _ in db.aboutness(s, M3)['asserted']] == [('obligation', o3.id)])
    check('Ld11: the artefact claims are Rob\'s and the line claim is Kim\'s - both named in the report; no rank key anywhere',
          {a for claims in repA['types']['obligation']['established'].values() for _, a in claims} == {household.id}
          and db.aboutness(s, M3)['asserted'][0][3] == kim_party.id
          and not any(k in repA['types']['obligation'] for k in ('rank', 'winner', 'preferred', 'weight', 'majority')))

    print('\n4. Ld5 / Ld6 - candidates never; contested STOP semantics exactly\n')
    C = held('h-candidates', '2026-04-30', cu, u_cu)
    rC = read(C)
    a_concerns(C, reading=rC, object_obligation_id=o1.id)             # the parser's heading match - a candidate
    K1 = line(rC, 'statement_figure', '$5', cu)
    p_concerns(K1, utterance=utter('That line is the HELOC.'), object_obligation_id=o2.id)
    repC = db.level_consistency(s, C)
    check('Ld5: a candidate artefact concern only -> artefact state candidates_only; the asserted-O2 line is NO_LEVEL_BASIS, not inconsistent; the candidate is listed',
          repC['types']['obligation']['artefact_state'] == db.ARTEFACT_SIDE_CANDIDATES and cls_of(repC, K1) == db.LEVEL_NO_LEVEL_BASIS
          and repC['types']['obligation']['candidates'] == [o1.id] and repC['types']['obligation']['inconsistencies'] == [])
    D = held('h-contested', '2026-05-31', cu, u_cu)
    a_concerns(D, utterance=utter('D is the mortgage statement.'), object_obligation_id=o1.id)
    u_d2 = utter('...and it covers the HELOC.')
    a_concerns(D, utterance=u_d2, object_obligation_id=o2.id)
    rD = read(D)
    P1, Q2, R3 = line(rD, 'statement_figure', '$1', cu), line(rD, 'statement_figure', '$2', cu), line(rD, 'statement_figure', '$3', cu)
    p_concerns(P1, utterance=utter('P is the mortgage.'), object_obligation_id=o1.id)
    p_concerns(Q2, utterance=utter('Q is the HELOC.'), object_obligation_id=o2.id)
    p_concerns(R3, utterance=utter('R is the car loan.'), object_obligation_id=o3.id)
    retract(u_d2, 'No - D does not cover the HELOC after all.')
    repD = db.level_consistency(s, D)
    tD = repD['types']['obligation']
    check("Ld6 / Rob's STOP: O1 established, O2 contested - the report preserves both (established {O1}, contested [O2]); the artefact state is still 'established' because a basis exists",
          set(tD['established']) == {o1.id} and tD['contested'] == [o2.id] and tD['artefact_state'] == db.ARTEFACT_SIDE_ESTABLISHED)
    check('Ld6: P -> O1 is CONSISTENT (its basis is established regardless); Q -> O2 is UNRESOLVED - no level disagreement is manufactured from the contested state',
          cls_of(repD, P1) == db.LEVEL_CONSISTENT and cls_of(repD, Q2) == db.LEVEL_UNRESOLVED)
    check('Ld6: R -> O3 (outside the established set while the artefact side is contested for the type) is UNRESOLVED, not inconsistent - contested stops the consumer; no inconsistency listed for D',
          cls_of(repD, R3) == db.LEVEL_UNRESOLVED and tD['inconsistencies'] == [])

    print('\n5. Ld7 / Ld8 / Ld10 - correspondence-derived counts; a proposition disagreement is its own class; structural counts\n')
    rS2 = read(S1, process='parser/6', when=datetime(2026, 5, 1))
    L2b = line(rS2, 'payment_due', '$1,412', cu)                      # a re-reading of line 2
    corr(L2, L2b, utterance=utter('Same line, both readings.', '2026-05-02T09:00:00'))
    rep7 = db.level_consistency(s, S1)
    check('Ld7: L2b has O2 only by derivation through the established correspondence to L2 - INCONSISTENT with source derived:correspondence, against [O1]',
          cls_of(rep7, L2b) == db.LEVEL_INCONSISTENT and entry_of(rep7, L2b)['identities'] == [(o2.id, db.ABOUT_DERIVED + ':' + db.ABOUT_PATH_CORRESPONDENCE)]
          and entry_of(rep7, L2b)['against'] == [o1.id])
    X1, X2 = line(rA, 'statement_figure', '$7', cu), line(rA, 'statement_figure', '$8', cu)
    p_concerns(X1, utterance=utter('X1 is the mortgage.'), object_obligation_id=o1.id)
    p_concerns(X2, utterance=utter('X2 is the HELOC.'), object_obligation_id=o2.id)
    corr(X1, X2, utterance=utter('X1 and X2 are one line.'))
    rep8 = db.level_consistency(s, A)
    dis = [d for d in rep8['proposition_disagreements'] if set(d['component']) == {X1.id, X2.id}]
    check('Ld8: P ~ P\' established, asserted O1 / O2, under an artefact set {O1, O2} - a PROPOSITION DISAGREEMENT (its own class, both members and both identities) and NO level inconsistency for either line',
          len(dis) == 1 and set(dis[0]['identities']) == {o1.id, o2.id} and dis[0]['type'] == 'obligation'
          and cls_of(rep8, X1) == db.LEVEL_CONSISTENT and cls_of(rep8, X2) == db.LEVEL_CONSISTENT)
    T = db.Proposition(kind='balance', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                       subject_obligation_id=o2.id, content='$9,100 (re-asserted)')
    s.add(T)
    s.commit()
    evidence(T, reading=rS)                                            # read from S1 with the participant established ((ii))
    rep10 = db.level_consistency(s, S1)
    check('Ld10: a line with STRUCTURAL O2 read from the single-obligation statement -> INCONSISTENT with source structural; structural is not preferred for being "in the row"',
          cls_of(rep10, T) == db.LEVEL_INCONSISTENT and entry_of(rep10, T)['identities'] == [(o2.id, db.ABOUT_STRUCTURAL)])

    print('\n6. Ld9 / type isolation - an artefact concerning O1, E1 and p; nothing cross-type\n')
    p1 = db.Payment(minted_by_id=utter('That payment.').id)
    s.add(p1)
    s.commit()
    Tm = held('h-multi', '2026-06-30', cu, u_cu)
    a_concerns(Tm, utterance=utter('Tm is the mortgage statement.'), object_obligation_id=o1.id)
    a_concerns(Tm, utterance=utter('...it lists the cleaning.'), object_expense_id=e1.id)
    a_concerns(Tm, utterance=utter('...and that payment.'), object_payment_id=p1.id)
    rTm = read(Tm)
    Y1 = line(rTm, 'statement_figure', '$43,900', cu)
    p_concerns(Y1, utterance=utter('Y1 is the mortgage.'), object_obligation_id=o1.id)
    Y2 = line(rTm, 'charge', '$150', cu)
    p_concerns(Y2, utterance=utter('Y2 is the cleaning.'), object_expense_id=e1.id)
    repT = db.level_consistency(s, Tm)
    check('Ld9 / type isolation: the report is partitioned by type - obligations {O1}, expenses {E1}, payments {p}; Y1 CONSISTENT for obligations and NO_LINE_BASIS for expenses; Y2 the mirror; no inconsistency anywhere',
          set(repT['types']['obligation']['established']) == {o1.id} and set(repT['types']['expense']['established']) == {e1.id}
          and set(repT['types']['payment']['established']) == {p1.id}
          and cls_of(repT, Y1, 'obligation') == db.LEVEL_CONSISTENT and cls_of(repT, Y1, 'expense') == db.LEVEL_NO_LINE_BASIS
          and cls_of(repT, Y2, 'expense') == db.LEVEL_CONSISTENT and cls_of(repT, Y2, 'obligation') == db.LEVEL_NO_LINE_BASIS
          and all(repT['types'][t]['inconsistencies'] == [] for t in repT['types']))

    print('\n7. Ld12 / Ld13 / Ld14 - counts are descriptive; recency nothing; candidates never\n')
    Z = held('h-three', '2026-07-31', cu, u_cu)
    a_concerns(Z, utterance=utter('Z is the mortgage statement.'), object_obligation_id=o1.id)
    rZ = read(Z)
    zl = [line(rZ, 'statement_figure', f'${i}', cu) for i in range(5)]
    p_concerns(zl[0], utterance=utter('z0 is the mortgage.', '2026-08-01T09:00:00'), object_obligation_id=o1.id)
    for i in (1, 2, 3):
        p_concerns(zl[i], utterance=utter(f'z{i} is the HELOC.', f'2026-08-0{i + 1}T09:00:00'), object_obligation_id=o2.id)
    p_concerns(zl[4], reading=rZ, object_obligation_id=o2.id)          # a candidate on the fifth line
    repZ = db.level_consistency(s, Z)
    tZ = repZ['types']['obligation']
    check('Ld12: three lines outside {O1} -> three inconsistencies listed; counts {consistent: 1, inconsistent: 3, no_line_basis: 1} as a FACT; the artefact set unchanged; no majority / weight / confidence / probability / recommendation key',
          len(tZ['inconsistencies']) == 3 and tZ['counts'] == {db.LEVEL_CONSISTENT: 1, db.LEVEL_INCONSISTENT: 3, db.LEVEL_NO_LINE_BASIS: 1}
          and set(tZ['established']) == {o1.id}
          and not any(k in tZ for k in ('majority', 'weight', 'confidence', 'probability', 'recommended', 'recommend_retraction', 'verdict'))
          and not any(k in repZ for k in ('majority', 'verdict', 'recommendation')))
    check('Ld13: the O2 line claims are newer than the artefact claim - nothing changes; the artefact set is not overwritten by recency',
          set(tZ['established']) == {o1.id} and cls_of(repZ, zl[1]) == db.LEVEL_INCONSISTENT)
    check('Ld14: the fifth line has only a candidate (heading match) -> NO_LINE_BASIS with the candidate listed; a candidate never raises an inconsistency',
          cls_of(repZ, zl[4]) == db.LEVEL_NO_LINE_BASIS and entry_of(repZ, zl[4])['candidates'] == [o2.id])

    print('\n8. Ld15 / Ld16 / Ld17 - surfaced not stored; nothing on either level; the null model\n')
    u_z1 = s.query(db.EvidentiaryRelationship).join(db.Proposition, db.Proposition.id == db.EvidentiaryRelationship.proposition_id).filter(
        db.Proposition.kind == db.PROPOSITION_CONCERNS, db.Proposition.subject_proposition_id == zl[1].id).one().utterance
    before_retract = snapshot()
    db.level_consistency(s, Z)
    check('Ld15: reading the report wrote nothing - every row identical before and after',
          snapshot() == before_retract)
    retract(u_z1, 'z1 was the mortgage after all.')
    p_concerns(zl[1], utterance=utter('z1 is the mortgage.', '2026-08-10T09:00:00'), object_obligation_id=o1.id)
    repZ2 = db.level_consistency(s, Z)
    check('Ld15: the household retracts one line claim and re-asserts - the next read shows it CONSISTENT and the count 2 inconsistent; 7D stored nothing and suggested nothing',
          cls_of(repZ2, zl[1]) == db.LEVEL_CONSISTENT and repZ2['types']['obligation']['counts'][db.LEVEL_INCONSISTENT] == 2
          and not any(hasattr(db, n) for n in ('recommend_retraction', 'suggest_retraction')))
    E = held('h-empty', '2026-08-31', cu, u_cu)                       # no artefact claim, no line claims
    rE = read(E)
    E1 = line(rE, 'statement_figure', '$0', cu)
    repE = db.level_consistency(s, E)
    check('Ld16: nothing on either level - artefact state none and the line NO_LINE_BASIS; never "consistent"; no inconsistency',
          repE['types']['obligation']['artefact_state'] == db.ARTEFACT_SIDE_NONE and cls_of(repE, E1) == db.LEVEL_NO_LINE_BASIS
          and all(l['classification'] != db.LEVEL_CONSISTENT for t in repE['types'].values() for l in t['lines']))
    N = held('h-null', '2026-09-30', cu, u_cu)
    a_concerns(N, utterance=utter('N is the mortgage statement.'), object_obligation_id=o1.id)
    rN = read(N)
    nl = [line(rN, 'statement_figure', f'${i}', cu) for i in range(4)]
    for ln in nl:
        p_concerns(ln, utterance=utter('within the set', '2026-10-01T09:00:00'), object_obligation_id=o1.id)
    repN = db.level_consistency(s, N)
    check('Ld17 (null model): a within-set corpus -> ZERO inconsistencies; counts {consistent: 4}',
          repN['types']['obligation']['inconsistencies'] == [] and repN['types']['obligation']['counts'] == {db.LEVEL_CONSISTENT: 4})
    outlier = line(rN, 'statement_figure', '$99', cu)
    p_concerns(outlier, utterance=utter('the outlier', '2026-10-02T09:00:00'), object_obligation_id=o3.id)
    repN2 = db.level_consistency(s, N)
    check('Ld17 (null model): one line asserted outside -> exactly ONE inconsistency, on that line; a correctness oracle, no threshold',
          len(repN2['types']['obligation']['inconsistencies']) == 1 and repN2['types']['obligation']['inconsistencies'][0]['proposition'] == outlier.id)

    print('\n9. The dependency direction and the wiring guard\n')
    check('7D reads 7C\'s established about-ness with its provenance - every line identity carries its source label (structural / asserted / derived:correspondence) and never the artefact path',
          all(src in (db.ABOUT_STRUCTURAL, db.ABOUT_ASSERTED, db.ABOUT_DERIVED + ':' + db.ABOUT_PATH_CORRESPONDENCE)
              for rep_ in (rep7, rep8, rep10, repZ2) for t in rep_['types'].values() for l in t['lines'] for _, src in l['identities']))
    before = snapshot()
    for a in (S1, A, B, C, D, Tm, Z, E, N):
        db.level_consistency(s, a)
    check('reading the report nine times left every row of every table byte-for-byte identical',
          snapshot() == before)
    check('the 7D wiring guard is executable (AST): level_consistency() calls no session write method and constructs no mapped class',
          writes_in(db.level_consistency) == [])

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
