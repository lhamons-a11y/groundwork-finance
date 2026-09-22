"""chain_strength - the executable trace of `gw 2.0/CONSUMER_DERIVATIONS.md` pass 7E (ruled 2026-09-17).

A CLASS, not a quantity. For one proposition: the class of each evidentiary relationship as derived_strength
gives it (L0, never re-derived), and for every about-ness 7C reports as ESTABLISHED every chain by which it is
reached - L0 followed by the links of one 7C path, each link a claim on record with ONE ground - and the chain's
class as the weakest link on the substrate's lattice. Ground aggregation belongs entirely to derived_strength:
a link with n grounds yields n chains. Across chains nothing; across identities nothing; unchained and
conflicts are report conditions, not classes; absence is not undetermined; nothing written.

What this slice can and cannot exercise
---------------------------------------
    Ms1  Chase value + Rob's concerns claim: [knowing, knowing] -> knowing                            EXERCISED
    Ms2  the association weaker than the value: [knowing, not_knowing] -> not_knowing; L0 unchanged  EXERCISED
    Ms3  O5 relay: [not_knowing, knowing] -> not_knowing; a knowing link lifts nothing               EXERCISED
    Ms4  the household re-asserts (structural): [L0] -> not_knowing = derived_strength               EXERCISED
    Ms5  the oracle: every zero-extra-link chain equals derived_strength                             EXERCISED
    Ms6  correspondence: [knowing, undetermined, knowing] -> undetermined; established, ungraded     EXERCISED
    Ms7  candidate correspondence + two strong ends: NO chain, NO class                              EXERCISED
    Ms8  three weak chains: three, listed, no aggregate                                              EXERCISED
    Ms9  several knowing chains say no more than one                                                 EXERCISED
    Ms10 mixed chains: both listed, no per-identity class, structural order                          EXERCISED
    Ms11 a 7C conflict carried ungraded                                                              EXERCISED
    Ms12 a 7D inconsistency untouched; 7E reads no level report                                      EXERCISED
    Ms13 a parse dispute: identical L0 by construction                                               EXERCISED
    Ms14 three independent origins: three chains; independence not read                             EXERCISED
    Ms15 one origin two readings: two chains, same class; multiplicity is not strength               EXERCISED
    Ms16 Kn6: the servicer's statement - one link, undetermined; no mediation link manufactured      EXERCISED
    Ms17 O4: a capture - one link; no faithfulness link added or claimed                             EXERCISED
    Ms18 the lattice: undetermined absorbs, by _weakest                                              EXERCISED
    Ms19 monotone: no chain above any of its links, over every chain in the corpus                   EXERCISED
    Ms20 no evidence: no chain, not undetermined                                                     EXERCISED
    Ms21 a retracted concerns claim: unchained, no class                                             EXERCISED
    Ms22 knowing is not true                                                                         EXERCISED
    Ms23 one claim, two grounds: TWO chains (inherited from derived_strength; no aggregation)         EXERCISED
    Ms24 surfaced not stored                                                                         EXERCISED
    Ms25 the three places a class can be said falsely - measured                                     EXERCISED
    Ms26 the null model: all-knowing corpus; one flipped link changes exactly its chains             EXERCISED
    Ms27 chain identity: equal ground sequences are one chain; two claims are two; cycles terminate  EXERCISED
    Rob's fence: no recompute, no aggregation, no rank, no 7B, no 7C resolution, no 7D, no lattice   EXERCISED
    the wiring guard: AST (session receivers) + a full row-content snapshot                            EXERCISED
    a ruled role kind (Kn6's link evaluable), correspondence's epistemology, traversal (7F)           NOT BUILT

Run:  python tests/test_chain_strength_fixture.py
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


DECIDER_NAMES = ('chain_cache', 'strength_cache', 'strength_score', 'chain_score', 'rank_chains', 'best_chain', 'strongest_chain',
                 'aggregate_strength', 'identity_strength', 'per_identity_strength', 'corroboration', 'combine_strengths',
                 'strength_of', 'link_strength', 'resolve_by_strength', 'CHAIN_STRONG', 'CHAIN_WEAK', 'STRENGTH_STRONG')
NUMERIC_KEYS = ('score', 'weight', 'confidence', 'probability', 'count', 'n_chains', 'n_paths', 'corroboration', 'rank',
                'strength', 'best', 'strongest', 'weakest_chain', 'summary', 'overall')
ORDER = {'undetermined': 0, 'not_knowing': 1, 'knowing': 2}


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_cs_')
    eng = create_engine(f'sqlite:///{Path(d) / "t.db"}')

    @event.listens_for(eng, 'connect')
    def _fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def _walk(x):
    """Every (key, value) pair anywhere in a report."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _walk(v)


def run(db):
    s = _fresh()
    rob = db.Person(display_name='Rob')
    kim = db.Person(display_name='Kim')
    s.add_all([rob, kim])
    s.commit()
    household, kim_party = rob.party, kim.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}, 'statement_figure': {'institution'}, 'balance': {'institution'}, 'eob_amount': {'institution'},
               'date_of_service': {'person', 'institution'}}   # movement: the ruled kind (BANK_LINE_KIND.md) - knowing by the relation, not by the map
    # 'acknowledgment' deliberately absent: its relation (the entitled party) is unruled -> undetermined

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

    def owe(text, origin=None):
        o = db.Obligation(minted_by_id=utter(text, origin=origin).id)
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

    def line(reading, kind, content, party, **slot):
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                            subject_party_id=party.id, content=content, as_of='2026-03-31', **slot)
        s.add(pr)
        s.commit()
        s.add(db.EvidentiaryRelationship(proposition_id=pr.id, reading_id=reading.id))
        s.commit()
        return pr

    def said(kind, content, utterance, **slot):
        obj = db.PARTICIPANT_ESTABLISHED if any(k.startswith('object_') for k in slot) else db.PARTICIPANT_NONE
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=obj,
                            content=content, as_of='2026-03-31', **slot)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utterance)
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

    def cs(p):
        return db.chain_strength(s, p, KNOWING)

    def entries(rep, ident, typ='obligation', **match):
        return [a for a in rep['about'] if a['type'] == typ and a['id'] == ident and all(a[k] == v for k, v in match.items())]

    def chains(rep, ident, typ='obligation', **match):
        return [c for a in entries(rep, ident, typ, **match) for c in a['chains']]

    def classes(chs):
        return [c['class'] for c in chs]

    def links(c):
        return [(l['kind'], l['class']) for l in c['links']]

    def all_chains(rep):
        return [c for a in rep['about'] for c in a['chains']]

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

    def calls_in(func):
        import ast, inspect, textwrap
        tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                names.add(fn.id if isinstance(fn, ast.Name) else getattr(fn, 'attr', None))
        return names

    chase, u_chase = mint_party('Chase.')
    aetna, u_aetna = mint_party('Aetna.')
    mercy, u_mercy = mint_party('Mercy Hospital.')
    servicer, u_serv = mint_party('The servicer S.')
    o1 = owe('My mortgage.')
    o2 = owe('My HELOC.')
    o3 = owe("Kim's car loan.", origin=kim_party)
    x1 = incur('The Feb 14 visit.')

    print('\n1. Absences - no score, no cache, no rank, no per-identity class, no second lattice\n')
    check('no scoring, caching, ranking, aggregating, corroboration or link-strength helper exists on the module',
          not any(hasattr(db, n) for n in DECIDER_NAMES))
    check('the three classes are the substrate\'s own (STRENGTH_*) and 7E declares no class of its own',
          (db.STRENGTH_KNOWING, db.STRENGTH_NOT_KNOWING, db.STRENGTH_UNDETERMINED) == ('knowing', 'not_knowing', 'undetermined')
          and not any(n.startswith('CHAIN_') and n not in ('CHAIN_LINK_EVIDENCE', 'CHAIN_TRACE_STRUCTURAL', 'CHAIN_ESTABLISHED',
                                                            'CHAIN_CANDIDATE', 'CHAIN_CONTESTED', 'CHAIN_UNESTABLISHED') for n in dir(db)))

    print('\n2. Ms1 / Ms2 / Ms3 / Ms4 / Ms5 - the chain grades the derivation, never the value; the oracle\n')
    A = held('h-chase', '2026-03-31', chase, u_chase)
    a_concerns(A, utterance=utter("That's my mortgage statement."), object_obligation_id=o1.id)
    rA = read(A)
    L1 = line(rA, 'statement_figure', '$1,925', chase)
    rep1 = cs(L1)
    ch1 = chains(rep1, o1.id, provenance=db.ABOUT_DERIVED, path=db.ABOUT_PATH_ARTEFACT)
    check('Ms1: Chase value (L0 knowing) + Rob\'s concerns claim (knowing, the minter of O1) -> ONE chain [evidence knowing, artefact_concerns knowing] -> KNOWING; slice 8 s5\'s combination',
          rep1['evidence'][0]['class'] == db.STRENGTH_KNOWING and len(ch1) == 1
          and links(ch1[0]) == [(db.CHAIN_LINK_EVIDENCE, db.STRENGTH_KNOWING), (db.ARTEFACT_CONCERNS, db.STRENGTH_KNOWING)]
          and ch1[0]['class'] == db.STRENGTH_KNOWING and ch1[0]['trace'] == [('reading', rA.id), ('artefact', A.id)])
    A2 = held('h-chase-2', '2026-04-30', chase, u_chase)
    a_concerns(A2, utterance=utter("That's the mortgage.", origin=kim_party), object_obligation_id=o1.id)
    L2 = line(read(A2), 'statement_figure', '$1,900', chase)
    rep2 = cs(L2)
    ch2 = chains(rep2, o1.id, provenance=db.ABOUT_DERIVED, path=db.ABOUT_PATH_ARTEFACT)
    check('Ms2: the association is Kim\'s (not the minter): chain [knowing, not_knowing] -> NOT_KNOWING - and L0 is reported UNCHANGED as knowing; the value keeps Chase\'s authority (Ab7)',
          rep2['evidence'][0]['class'] == db.STRENGTH_KNOWING and classes(ch2) == [db.STRENGTH_NOT_KNOWING]
          and links(ch2[0]) == [(db.CHAIN_LINK_EVIDENCE, db.STRENGTH_KNOWING), (db.ARTEFACT_CONCERNS, db.STRENGTH_NOT_KNOWING)]
          and rep2['evidence'][0]['class'] == db.derived_strength(s, s.get(db.EvidentiaryRelationship, rep2['evidence'][0]['relationship']), KNOWING))
    SP = held('h-spreadsheet', '2026-03-31', household, utter('My spreadsheet.'))
    L3 = line(read(SP), 'eob_amount', '$412 (Aetna EOB)', aetna)
    p_concerns(L3, utterance=utter('That row is the Feb 14 visit.'), object_expense_id=x1.id)
    rep3 = cs(L3)
    ch3 = chains(rep3, x1.id, 'expense', provenance=db.ABOUT_ASSERTED)
    check('Ms3 (O5): the spreadsheet relays Aetna\'s figure (L0 not_knowing - Rob is not the insurer) + Rob\'s concerns claim (knowing) -> NOT_KNOWING; a knowing link lifts nothing; relaying does not launder',
          rep3['evidence'][0]['class'] == db.STRENGTH_NOT_KNOWING and classes(ch3) == [db.STRENGTH_NOT_KNOWING]
          and links(ch3[0]) == [(db.CHAIN_LINK_EVIDENCE, db.STRENGTH_NOT_KNOWING), (db.PROPOSITION_CONCERNS, db.STRENGTH_KNOWING)])
    K2 = said('balance', '$1,925', utter('The mortgage balance is $1,925.'), subject_obligation_id=o1.id)
    rep4 = cs(K2)
    ch4 = chains(rep4, o1.id, provenance=db.ABOUT_STRUCTURAL)
    check('Ms4 (Ab1 K2): the household re-asserts the balance with O1 as subject (structural): chain [L0] -> NOT_KNOWING - the crossing downgrades E\'s statement into testimony; one link, no second invented',
          classes(ch4) == [db.STRENGTH_NOT_KNOWING] and len(ch4[0]['links']) == 1 and ch4[0]['trace'] == [])
    oracle = []
    for p in (K2, L1, L2, L3):
        rep = cs(p)
        for e in rep['evidence']:
            rel = s.get(db.EvidentiaryRelationship, e['relationship'])
            oracle.append(e['class'] == db.derived_strength(s, rel, KNOWING))
        for c in chains(rep, o1.id, provenance=db.ABOUT_STRUCTURAL):
            oracle.append(c['class'] == db.derived_strength(s, s.get(db.EvidentiaryRelationship, c['evidence']), KNOWING))
    check('Ms5 (the oracle): every L0 class IS derived_strength on that relationship, and every zero-extra-link chain equals it exactly - 7E re-derives nothing',
          oracle and all(oracle))

    print('\n3. Ms6 / Ms7 / Ms18 - correspondence: established about-ness, undetermined strength; a candidate is no chain; the lattice\n')
    B = held('h-chase-B', '2026-05-31', chase, u_chase)                # no artefact-level claim
    rB = read(B)
    P3 = line(rB, 'statement_figure', '$9,100', chase)
    p_concerns(P3, utterance=utter('P3 is the HELOC.'), object_obligation_id=o2.id)
    P3b = line(rB, 'statement_figure', '$9,100', chase)
    u_corr = utter('P3 and P3b are one line.')
    corr(P3, P3b, utterance=u_corr)
    rep6 = cs(P3b)
    ch6 = chains(rep6, o2.id, provenance=db.ABOUT_DERIVED, path=db.ABOUT_PATH_CORRESPONDENCE)
    check('Ms6 (Pc3): P3b about O2 through established correspondence: chain [evidence knowing, proposition_corresponds UNDETERMINED (by design, Kn4), proposition_concerns knowing] -> UNDETERMINED; established about-ness, undetermined strength; nothing manufactured for the correspondence link',
          [(t, i) for t, i in [(a['type'], a['id']) for a in db.aboutness(s, P3b)['derived']]] == [('obligation', o2.id)]
          and classes(ch6) == [db.STRENGTH_UNDETERMINED]
          and links(ch6[0]) == [(db.CHAIN_LINK_EVIDENCE, db.STRENGTH_KNOWING), (db.PROPOSITION_CORRESPONDS, db.STRENGTH_UNDETERMINED),
                                (db.PROPOSITION_CONCERNS, db.STRENGTH_KNOWING)])
    P7 = line(rB, 'statement_figure', '$500', chase)
    p_concerns(P7, utterance=utter('P7 is the mortgage.'), object_obligation_id=o1.id)
    P7b = line(rB, 'statement_figure', '$500', chase)
    corr(P7, P7b, reading=rB)                                          # a position match: a candidate
    rep7 = cs(P7b)
    check('Ms7 (Rob\'s boundary): a CANDIDATE correspondence between two strong ends -> NO chain and NO class for "P7b about O1" - unchained with 7C\'s reason; L0 alone is not reported as the strength of an about-ness that is not established',
          entries(rep7, o1.id) == [] and rep7['unchained'] == [('obligation', o1.id, db.ABOUT_CANDIDATE, 'candidate correspondence')]
          and rep7['evidence'][0]['class'] == db.STRENGTH_KNOWING and rep7['note'] == 'no about-ness established'
          and not any(v in ORDER for k, v in _walk(rep7['unchained'])))
    P18 = line(rB, 'statement_figure', '$7', chase)
    p_concerns(P18, utterance=utter('P18 is the HELOC.', origin=kim_party), object_obligation_id=o2.id)
    P18b = line(rB, 'statement_figure', '$7', chase)
    corr(P18, P18b, utterance=utter('P18 and P18b are one line.'))
    ch18 = chains(cs(P18b), o2.id, provenance=db.ABOUT_DERIVED, path=db.ABOUT_PATH_CORRESPONDENCE)
    check('Ms18 (the lattice): links knowing / undetermined / not_knowing -> UNDETERMINED - undetermined absorbs, by the substrate\'s _weakest; 7E reorders nothing',
          links(ch18[0]) == [(db.CHAIN_LINK_EVIDENCE, db.STRENGTH_KNOWING), (db.PROPOSITION_CORRESPONDS, db.STRENGTH_UNDETERMINED),
                             (db.PROPOSITION_CONCERNS, db.STRENGTH_NOT_KNOWING)]
          and ch18[0]['class'] == db.STRENGTH_UNDETERMINED == db._weakest(*(l['class'] for l in ch18[0]['links'])))

    print('\n4. Ms8 / Ms9 / Ms10 / Ms23 - across chains nothing; within a link, one chain per ground\n')
    C = held('h-three-weak', '2026-06-30', chase, u_chase)
    a_concerns(C, utterance=utter('C is the car loan.'), object_obligation_id=o3.id)      # Rob is not O3's minter -> not_knowing
    rC = read(C)
    W = line(rC, 'statement_figure', '$14,000', chase)
    p_concerns(W, utterance=utter('W is the car loan.'), object_obligation_id=o3.id)          # not_knowing
    Wb = line(rC, 'statement_figure', '$14,000', chase)
    p_concerns(Wb, utterance=utter('Wb is the car loan.'), object_obligation_id=o3.id)
    corr(W, Wb, utterance=utter('W and Wb are one line.'))
    rep8 = cs(W)
    ch8 = chains(rep8, o3.id)
    check('Ms8 (Rob\'s boundary): W about O3 by three established paths (asserted, artefact, correspondence), each chain weak -> THREE chains listed [not_knowing, not_knowing, undetermined]; no aggregate, no count key, no per-identity class',
          sorted(classes(ch8)) == [db.STRENGTH_NOT_KNOWING, db.STRENGTH_NOT_KNOWING, db.STRENGTH_UNDETERMINED]
          and {(a['provenance'], a['path']) for a in entries(rep8, o3.id)} == {(db.ABOUT_ASSERTED, None), (db.ABOUT_DERIVED, db.ABOUT_PATH_ARTEFACT), (db.ABOUT_DERIVED, db.ABOUT_PATH_CORRESPONDENCE)}
          and not any(k in NUMERIC_KEYS for k, _ in _walk(rep8)) and not any('class' in a for a in rep8['about']))
    N9 = held('h-strong', '2026-07-31', chase, u_chase)
    a_concerns(N9, utterance=utter('N9 is the mortgage.'), object_obligation_id=o1.id)
    rN9a, rN9b = read(N9, 'parser/5'), read(N9, 'parser/6', datetime(2026, 8, 1))
    S9 = line(rN9a, 'statement_figure', '$1,800', chase)
    evidence(S9, reading=rN9b)
    p_concerns(S9, utterance=utter('S9 is the mortgage.'), object_obligation_id=o1.id)
    rep9 = cs(S9)
    ch9 = chains(rep9, o1.id)
    check('Ms9: four knowing chains (two readings x {artefact claim, concerns claim}) - each KNOWING and nothing more than one knowing chain says; no "stronger", no count',
          len(ch9) == 4 and set(classes(ch9)) == {db.STRENGTH_KNOWING} and not any(k in NUMERIC_KEYS for k, _ in _walk(rep9))
          and set(classes(chains(rep1, o1.id))) == {db.STRENGTH_KNOWING})
    B10 = held('h-mixed', '2026-08-31', chase, u_chase)
    a_concerns(B10, utterance=utter('B10 is the HELOC.'), object_obligation_id=o2.id)
    rB10 = read(B10)
    M = line(rB10, 'statement_figure', '$9,000', chase)
    Mb = line(rB10, 'statement_figure', '$9,000', chase)
    p_concerns(Mb, utterance=utter('Mb is the HELOC.'), object_obligation_id=o2.id)
    corr(M, Mb, utterance=utter('M and Mb are one line.'))
    rep10 = cs(M)
    e10 = entries(rep10, o2.id)
    check('Ms10 (mixed): M about O2 via the artefact (knowing) and via correspondence (undetermined) - BOTH listed as their own entries in structural order (artefact path first, as 7C lists it), no summary class, no order by class',
          [(a['path'], classes(a['chains'])) for a in e10] == [(db.ABOUT_PATH_ARTEFACT, [db.STRENGTH_KNOWING]), (db.ABOUT_PATH_CORRESPONDENCE, [db.STRENGTH_UNDETERMINED])]
          and not any('class' in a for a in e10))
    T = held('h-two-grounds', '2026-09-30', chase, u_chase)
    Tl = line(read(T), 'statement_figure', '$3', chase)
    _, tclaim = p_concerns(Tl, utterance=utter('Tl is the mortgage.'), object_obligation_id=o1.id)
    evidence(tclaim, utterance=utter('Yes, the mortgage.', origin=kim_party))
    rep23 = cs(Tl)
    ch23 = chains(rep23, o1.id, provenance=db.ABOUT_ASSERTED)
    check('Ms23 (inherited, not redesigned): ONE concerns claim with two grounds - Rob\'s (knowing) and Kim\'s (not_knowing) -> TWO chains, one per ground, each with that ground\'s derived_strength; no link-level "strongest", no party ranked',
          len(ch23) == 2 and classes(ch23) == [db.STRENGTH_KNOWING, db.STRENGTH_NOT_KNOWING]
          and {c['links'][1]['claim'] for c in ch23} == {tclaim.id} and len({c['links'][1]['ground'] for c in ch23}) == 2
          and all(c['links'][1]['class'] == db.derived_strength(s, s.get(db.EvidentiaryRelationship, c['links'][1]['ground']), KNOWING) for c in ch23))

    print('\n5. Ms11 / Ms12 / Ms13 / Ms14 / Ms15 - strength solves nothing 7A-7D left open\n')
    D = held('h-conflict', '2026-10-31', chase, u_chase)
    a_concerns(D, utterance=utter('D is the mortgage.'), object_obligation_id=o1.id)
    rD = read(D)
    Q = line(rD, 'statement_figure', '$1,700', chase)
    p_concerns(Q, utterance=utter('Q is the HELOC.', origin=kim_party), object_obligation_id=o2.id)
    rep11 = cs(Q)
    ab11 = db.aboutness(s, Q)
    check('Ms11 (7C conflict): Q derived O1 through the artefact (knowing) and asserted O2 by Kim (not_knowing) - both entries reported; 7C\'s conflict carried AS FOUND with no class on it; the knowing chain settles nothing',
          classes(chains(rep11, o1.id)) == [db.STRENGTH_KNOWING] and classes(chains(rep11, o2.id)) == [db.STRENGTH_NOT_KNOWING]
          and rep11['conflicts'] == ab11['conflicts'] and len(rep11['conflicts']) == 1
          and not any(k == 'class' for k, _ in _walk(rep11['conflicts'])))
    lc = db.level_consistency(s, D)
    check('Ms12 (7D): the line is INCONSISTENT with its artefact level and stays so; chain_strength calls neither level_consistency nor independence',
          next(l['classification'] for l in lc['types']['obligation']['lines'] if l['proposition'] == Q.id) == db.LEVEL_INCONSISTENT
          and not ({'level_consistency', 'independence', 'parse_disputes'} & calls_in(db.chain_strength)))
    F = held('h-dispute', '2026-11-30', chase, u_chase)
    rF1, rF2 = read(F, 'parser/5'), read(F, 'parser/6', datetime(2026, 12, 1))
    Y1 = line(rF1, 'statement_figure', '$100', chase)
    Y2 = line(rF2, 'statement_figure', '$1OO', chase)
    corr(Y1, Y2, utterance=utter('Y1 and Y2 are one line.'))
    check('Ms13 (7A): two readings of one artefact disagree on the figure - IDENTICAL L0 by construction (one artefact, one origin, one kind); strength cannot choose a reading',
          cs(Y1)['evidence'][0]['class'] == cs(Y2)['evidence'][0]['class'] == db.STRENGTH_KNOWING
          and len(db.parse_disputes(s, F)['groups']) == 1)
    dos = said('date_of_service', '2026-02-14', utter('Feb 14.'), subject_expense_id=x1.id)
    evidence(dos, utterance=utter('Date of service Feb 14.', origin=mercy))
    evidence(dos, utterance=utter('DOS 02/14.', origin=aetna))
    rep14 = cs(dos)
    ch14 = chains(rep14, x1.id, 'expense', provenance=db.ABOUT_STRUCTURAL)
    check('Ms14 (In14): three independent knowing origins -> THREE chains, each knowing, one per relationship; no corroboration, no "independent" key; 7B not read',
          len(ch14) == 3 and set(classes(ch14)) == {db.STRENGTH_KNOWING}
          and not any(k in ('independent', 'pairs', 'origins', 'corroboration') for k, _ in _walk(rep14))
          and len(db.independence(s, dos, KNOWING)['pairs']) == 3)
    check('Ms15 (In13): one origin, two readings (S9) -> two chains per link, the SAME class; multiplicity is not strength',
          len({c['evidence'] for c in ch9}) == 2 and len(set(classes(ch9))) == 1)

    print('\n6. Ms16 / Ms17 / Ms22 - no link manufactured; knowing is not true\n')
    said('services', 'S services the mortgage.', utter('S is the servicer of my mortgage.'), subject_party_id=servicer.id, object_obligation_id=o1.id)
    ack = said('acknowledgment', 'E acknowledged the March payment.', utter('Chase received March.', origin=servicer), subject_obligation_id=o1.id)
    rep16 = cs(ack)
    ch16 = chains(rep16, o1.id, provenance=db.ABOUT_STRUCTURAL)
    check('Ms16 (Kn6): the servicer states E\'s acknowledgment; no role kind is ruled -> ONE link, UNDETERMINED (the kind\'s relation is unruled); the unruled "services" claim in the record is NOT read as a mediation link; nothing constructed from context',
          classes(ch16) == [db.STRENGTH_UNDETERMINED] and len(ch16[0]['links']) == 1
          and not any(v == 'services' for _, v in _walk(rep16)))
    CAP = held('h-capture', '2026-04-15', aetna, utter('That screenshot is from the Aetna portal.'))
    V = line(read(CAP, 'capture/1'), 'eob_amount', '$412', aetna)
    rep17 = cs(V)
    ch17 = chains(rep17, o1.id) + chains(rep17, x1.id, 'expense')
    check('Ms17 (O4): a captured portal - L0 KNOWING (Aetna is origin and knowing for the kind; the origin claim graded inside slice 3); no faithfulness link added or claimed - the evidence lists one relationship and no chain carries a "capture" link',
          rep17['evidence'][0]['class'] == db.STRENGTH_KNOWING and ch17 == []
          and not any(isinstance(v, str) and ('capture' in v or 'faithful' in v) for _, v in _walk(rep17)))
    said('balance', '$1,000', utter('The balance is $1,000.', origin=chase), subject_obligation_id=o1.id)   # E contradicts L1
    check('Ms22 (Kn12): Chase\'s own later contrary statement changes nothing on L1\'s chain - knowing is first-hand, never correct; truth is the fenced resolver\'s',
          classes(chains(cs(L1), o1.id)) == [db.STRENGTH_KNOWING])

    print('\n7. Ms19 / Ms20 / Ms21 / Ms25 - monotone; absence is not a class; where the failure appears\n')
    corpus = [cs(p) for p in (L1, L2, L3, K2, P3b, P7b, P18b, W, S9, M, Tl, Q, Y1, dos, ack, V)]
    check('Ms19 (monotone): over every chain in the corpus, the chain\'s class is never above any of its links\' - adding a link never raises a class',
          all(ORDER[c['class']] <= min(ORDER[l['class']] for l in c['links']) for rep in corpus for c in all_chains(rep))
          and sum(len(all_chains(rep)) for rep in corpus) >= 20)
    bare = db.Proposition(kind='balance', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                          subject_obligation_id=o1.id, content='$0', as_of='2026-03-31')
    s.add(bare)
    s.commit()
    rep20 = cs(bare)
    check('Ms20: a proposition with NO evidentiary relationship -> evidence [], about [] (its structural participant grades nothing), note "no evidentiary relationship"; "undetermined" appears nowhere - absence is not a class',
          rep20['evidence'] == [] and rep20['about'] == [] and rep20['note'] == 'no evidentiary relationship'
          and not any(v == db.STRENGTH_UNDETERMINED for _, v in _walk(rep20)))
    u_p3 = s.query(db.EvidentiaryRelationship).join(db.Proposition, db.Proposition.id == db.EvidentiaryRelationship.proposition_id).filter(
        db.Proposition.kind == db.PROPOSITION_CONCERNS, db.Proposition.subject_proposition_id == P3.id).one().utterance
    retract(u_p3, 'P3 was not the HELOC.')
    rep21 = cs(P3)
    check('Ms21: Rob retracts his concerns claim on P3 -> UNCHAINED (undetermined about-ness, "retracted assertion") with no class; not "weak"',
          entries(rep21, o2.id) == [] and ('obligation', o2.id, db.ABOUT_UNDETERMINED, 'retracted assertion') in rep21['unchained']
          and not any(v in ORDER for _, v in _walk(rep21['unchained'])))
    check('Ms25 (where the failure appears): no class above a weakest link (Ms19), no class of an about-ness not established (Ms7, Ms21), no class of evidence that does not exist (Ms20) - measured, all three',
          all(ORDER[c['class']] <= min(ORDER[l['class']] for l in c['links']) for rep in corpus for c in all_chains(rep))
          and entries(rep7, o1.id) == [] and entries(rep21, o2.id) == [] and rep20['about'] == [])

    print('\n8. Ms24 / Ms26 - surfaced not stored; the null model; the strength-blind consumer\n')
    before = snapshot()
    for rep in [cs(p) for p in (L1, L2, P3b, W, S9, Tl, Q, dos, ack, bare)]:
        pass
    check('Ms24: reading ten reports wrote nothing - every row identical; no strength / chain / lineage column or table exists',
          snapshot() == before
          and not any(any(w in c.name for w in ('strength', 'chain', 'lineage', 'class')) for t in db.Base.metadata.tables.values() for c in t.columns)
          and not any(w in n for n in db.Base.metadata.tables for w in ('strength', 'chain', 'lineage')))
    NM = held('h-null', '2026-12-31', chase, u_chase)
    a_concerns(NM, utterance=utter('NM is the mortgage.'), object_obligation_id=o1.id)
    rNM = read(NM)
    nl = [line(rNM, 'statement_figure', f'${i}', chase) for i in range(3)]
    _, flip_claim = p_concerns(nl[0], utterance=utter('n0 is the mortgage.'), object_obligation_id=o1.id)
    p_concerns(nl[1], utterance=utter('n1 is the mortgage.'), object_obligation_id=o1.id)
    reps_before = [cs(p) for p in nl]
    check('Ms26 (null model): an all-knowing corpus -> every chain KNOWING (five chains over three lines)',
          sum(len(all_chains(r)) for r in reps_before) == 5 and all(c['class'] == db.STRENGTH_KNOWING for r in reps_before for c in all_chains(r)))
    u_n0 = s.get(db.EvidentiaryRelationship, chains(reps_before[0], o1.id, provenance=db.ABOUT_ASSERTED)[0]['links'][1]['ground']).utterance
    retract(u_n0, 'not me')
    evidence(flip_claim, utterance=utter('n0 is the mortgage.', origin=kim_party))
    reps_after = [cs(p) for p in nl]
    changed = [(c['evidence'], c['class']) for c in chains(reps_after[0], o1.id, provenance=db.ABOUT_ASSERTED)]
    unchanged = all(
        [(c['evidence'], c['class']) for c in chains(reps_after[i], o1.id, provenance=db.ABOUT_DERIVED, path=db.ABOUT_PATH_ARTEFACT)]
        == [(c['evidence'], c['class']) for c in chains(reps_before[i], o1.id, provenance=db.ABOUT_DERIVED, path=db.ABOUT_PATH_ARTEFACT)]
        for i in range(3)) and classes(chains(reps_after[1], o1.id, provenance=db.ABOUT_ASSERTED)) == [db.STRENGTH_KNOWING]
    check('Ms26 (null model): flip exactly one link (Rob\'s ground on n0\'s claim retracted, Kim\'s in its place) -> exactly the chain through that link changes (now not_knowing); every other chain identical',
          [cls for _, cls in changed] == [db.STRENGTH_NOT_KNOWING] and unchanged)
    check('the strength-blind consumer (every link taken as knowing) would say KNOWING on Ms2, Ms3 and Ms6 - the fixture differs from it on all three',
          classes(ch2) == [db.STRENGTH_NOT_KNOWING] and classes(ch3) == [db.STRENGTH_NOT_KNOWING] and classes(ch6) == [db.STRENGTH_UNDETERMINED])

    print("\n8b. Ms27 - what a chain IS: its sequence of grounds; equal sequences one chain; simple routes\n")
    I = held('h-identity', '2027-01-31', chase, u_chase)
    rI = read(I)
    J, Jb = line(rI, 'statement_figure', '$5', chase), line(rI, 'statement_figure', '$5', chase)
    _, jclaim = p_concerns(Jb, utterance=utter('Jb is the mortgage.'), object_obligation_id=o1.id)
    evidence(jclaim, utterance=utter('Yes, the mortgage.', origin=kim_party))
    corr(J, Jb, utterance=utter('J and Jb are one line.'))
    rep27 = cs(J)
    ch27 = chains(rep27, o1.id, provenance=db.ABOUT_DERIVED, path=db.ABOUT_PATH_CORRESPONDENCE)
    ids27 = [tuple(l['ground'] for l in c['links']) for c in ch27]
    check('Ms27: a correspondence to a claim with two grounds - 7C lists the path twice (once per ground); 7E reports exactly TWO chains, one per ground sequence, never four; a chain is its sequence of grounds',
          len(db.aboutness(s, J)['derived'][0]['paths']) == 2 and len(ch27) == 2 and len(set(ids27)) == 2
          and set(classes(ch27)) == {db.STRENGTH_UNDETERMINED} and [c['links'][-1]['class'] for c in ch27] == [db.STRENGTH_KNOWING, db.STRENGTH_NOT_KNOWING])
    corr(J, Jb, utterance=utter('Same line, said again.', origin=kim_party))          # a second claim between the same pair
    ch27b = chains(cs(J), o1.id, provenance=db.ABOUT_DERIVED, path=db.ABOUT_PATH_CORRESPONDENCE)
    check('Ms27: a SECOND correspondence claim between the same pair is a different claim on record -> two routes, FOUR chains, all distinct ground sequences; nothing merged that differs, nothing counted',
          len(ch27b) == 4 and len({tuple(l['ground'] for l in c['links']) for c in ch27b}) == 4
          and not any(k in NUMERIC_KEYS for k, _ in _walk(cs(J))))
    Jc = line(rI, 'statement_figure', '$5', chase)
    corr(Jb, Jc, utterance=utter('Jb and Jc are one line.'))
    corr(Jc, J, utterance=utter('Jc and J are one line.'))                            # a cycle J ~ Jb ~ Jc ~ J
    rep27c = cs(J)
    ch27c = chains(rep27c, o1.id, provenance=db.ABOUT_DERIVED, path=db.ABOUT_PATH_CORRESPONDENCE)
    check('Ms27 (simple): a cycle J~Jb~Jc~J terminates - routes J->Jb (two claims) and J->Jc->Jb, no proposition visited twice, no route repeated; every chain a distinct ground sequence; every chain through correspondence undetermined',
          len(ch27c) == 6 and len({tuple(l['ground'] for l in c['links']) for c in ch27c}) == 6
          and all(len({h[2] for h in r} | {r[0][1]}) == len(r) + 1 for r in db._correspondence_routes(s, J.id, Jb.id, set()))
          and len(db._correspondence_routes(s, J.id, Jb.id, set())) == 3
          and set(classes(ch27c)) == {db.STRENGTH_UNDETERMINED})
    corpus.append(rep27c)
    check('no report in the corpus lists one ground sequence twice - chain identity is enforced, not assumed',
          all(len(all_chains(rep)) == len({tuple(l['ground'] for l in c['links']) for c in all_chains(rep)}) for rep in corpus))

    print("\n9. Rob's fence, the dependency direction and the wiring guard\n")
    check('7E consumes derived_strength and _weakest, and calls no aggregator of its own - every link class in the corpus equals derived_strength on its ground',
          all(l['ground'] is not None and l['class'] == db.derived_strength(s, s.get(db.EvidentiaryRelationship, l['ground']), KNOWING)
              for rep in corpus for c in all_chains(rep) for l in c['links'])
          and {'derived_strength', '_weakest', 'aboutness'} <= calls_in(db.chain_strength)
          and not ({'max', 'min', 'sum', 'sorted_by_class', 'mean'} & calls_in(db.chain_strength)))
    check('no number anywhere in any report except identifiers: no score / weight / confidence / probability / count / rank / strength / best key',
          not any(k in NUMERIC_KEYS for rep in corpus for k, _ in _walk(rep))
          and not any(isinstance(v, float) for rep in corpus for _, v in _walk(rep)))
    check('the 7E wiring guard is executable (AST): chain_strength() and its helpers call no session write method and construct no mapped class',
          writes_in(db.chain_strength) == [] and writes_in(db._link_grounds) == [] and writes_in(db._correspondence_routes) == [])

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
