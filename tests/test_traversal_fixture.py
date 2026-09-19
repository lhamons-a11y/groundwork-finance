"""reach / in_effect - the executable trace of `gw 2.0/CONSUMER_DERIVATIONS.md` pass 7F (ruled 2026-09-18).

ONE HOP, EVERY ENDPOINT, NOTHING CHOSEN. `reach(session, thing, kind, as_object)` reads one ruled relation kind
and stops at its endpoints - all of them, with claim, asserter and state - choosing none; the reverse
direction a labelled query, no inverse kind; nothing of the endpoint carried onto the subject; no second hop;
no inference; meta-kinds, boundary kinds and unruled kinds refused BY NAME. `in_effect(session, party, role_kind,
d)` reads a role's holds / began / ended stances under TS (ruled s 7F.8): G(d) read forward, N(d) read back,
in_effect / not_in_effect / undetermined / contested, G and N in the report; TS-c symmetric.

What this slice can and cannot exercise
---------------------------------------
    Tr1  C17: reach O -> X, by whom; nothing of X on O                                             EXERCISED
    Tr2  C21: two expenses, both, no "the"                                                        EXERCISED
    Tr3  D'3: p -> obligation empty by name; X <- O1, O2 as a query; no p -> O anywhere            EXERCISED
    Tr4  D'18: the reverse direction labelled; no inverse kind                                     EXERCISED
    Tr5  a reading-sourced claim: candidate, listed                                                EXERCISED
    Tr6  a retracted claim: contested, listed, not erased                                          EXERCISED
    Tr7  a party referent: the correspondent's claim reached, the claim named as its own           EXERCISED
    Tr8  E24: nothing connects X to P -> nothing; the unbuilt kind refused by name                  EXERCISED
    Tr9  E2 / F20: two plans, both, no primary                                                     EXERCISED
    Tr10-Tr19 the dated question: R9, R8, R5, R7, R6, R1, R3, R11, R12, nothing                   EXERCISED
    Tr20 surfaced not stored; no period / status column                                            EXERCISED
    Tr21 unruled kind refused by name                                                              EXERCISED
    Tr22 a relation kind to in_effect refused                                                      EXERCISED
    Tr23 a meta-kind to reach refused                                                              EXERCISED
    Tr24 one hop, mechanically: no via / path / second hop                                         EXERCISED
    Tr25 null model: the direct query; the one-beginning corpus                                    EXERCISED
    Tr26 where the failure appears                                                                 EXERCISED
    Ts1-Ts14 TS: the stance table, G / N, contested exactly, TS-c, Rob's three tests               EXERCISED
    the wiring guard: AST (session receivers) + a full row-content snapshot                        EXERCISED
    E / F kinds (accepted, unbuilt), the role catalogue, 7G discharge                              NOT BUILT

Run:  python tests/test_traversal_fixture.py
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


DECIDER_NAMES = ('current_plan_of', 'plan_of_person', 'primary_plan', 'entitled_party_of', 'current_entitled_party',
                 'the_expense_of', 'underlying_expense', 'obligation_of_payment', 'obligation_paid_by', 'plan_covers',
                 'plan_members', 'period_of', 'Period', 'RolePeriod', 'traverse', 'compose', 'via', 'path_to',
                 'in_effect_cache', 'reach_cache', 'latest_stance', 'current_status', 'resolve_overlap')
FORBIDDEN_KEYS = ('via', 'path', 'through', 'hops', 'primary', 'current', 'preferred', 'chosen', 'winner', 'period',
                  'interval', 'from', 'to', 'count', 'rank', 'weight')


def _role(subject, obj):
    return {'subject': (subject,), 'object': (obj,), 'symmetric': False, 'reading_establishes': False, 'relational_knowing': True, 'role': True}


def _boundary(of, which, subject, obj):
    r = _role(subject, obj)
    r.update({'boundary': which, 'of': of})
    return r


# stand-in role kinds - registered for this fixture and removed; their names carry NO ruling
STAND_INS = {
}


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_tr_')
    eng = create_engine(f'sqlite:///{Path(d) / "t.db"}')

    @event.listens_for(eng, 'connect')
    def _fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def _walk(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _walk(v)


def _refused(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except ValueError as e:
        return str(e)
    return None


def run(db):
    shipped = {k: v for k, v in db.RULED_KINDS.items()}
    for k in STAND_INS:
        assert k not in db.RULED_KINDS, k
    db.RULED_KINDS.update(STAND_INS)
    try:
        _run(db)
    finally:
        for k in STAND_INS:
            db.RULED_KINDS.pop(k, None)
    # 9A (CATALOGUES.md) built under_plan and its boundaries - the shipped registry now carries exactly those two boundary
    # entries; 7F ruled no role, and the substitution of the ruled kind for the stand-in changed nothing else here.
    # 9B ruled the role catalogue: the shipped boundary entries are those of the three roles that transition.
    check('the stand-in kinds are removed; the registry is as shipped - 7F ruled no role; the boundary entries are those of under_plan (9A), entitled_party_of and servicer_of (9B)',
          db.RULED_KINDS == shipped and {r['of'] for r in shipped.values() if r.get('boundary')} == {db.UNDER_PLAN, db.ENTITLED_PARTY_OF, db.SERVICER_OF})
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


def _run(db):
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

    def mint(cls, text, origin=None):
        u = utter(text, origin=origin)
        x = cls(minted_by_id=u.id)
        s.add(x)
        s.commit()
        return x

    def held(h, origin_party):
        a = db.Artefact(held=True, content_hash=h, as_of='2026-03-31')
        s.add(a)
        s.commit()
        pr = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=a.id, object_party_id=origin_party.id)
        s.add(pr)
        s.commit()
        s.add(db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=utter('origin').id))
        s.commit()
        r = db.Reading(artefact_id=a.id, reader_process='parser/5', read_at=datetime(2026, 4, 2))
        s.add(r)
        s.commit()
        return a, r

    def evidence(pr, utterance=None, reading=None):
        e = db.EvidentiaryRelationship(proposition_id=pr.id, utterance_id=utterance.id if utterance else None,
                                       reading_id=reading.id if reading else None)
        s.add(e)
        s.commit()
        return e

    def claim(kind, utterance=None, reading=None, as_of=None, **slots):
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            as_of=as_of, **slots)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utterance, reading=reading)
        return pr

    def fact(kind, content, utterance, **slots):
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                            content=content, as_of='2026-02-14', **slots)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utterance)
        return pr

    def retract(u, text):
        r = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                           subject_utterance_id=u.id)
        s.add(r)
        s.commit()
        evidence(r, utterance=utter(text, '2026-04-20T09:00:00'))

    def stance(kind, party, as_of, utterance=None, reading=None, **obj):
        return claim(kind, utterance=utterance if (utterance or reading) else utter(f'{kind} {as_of}'), reading=reading,
                     as_of=as_of, subject_party_id=party.id, **obj)

    def ids(rep, state=None):
        return sorted(e['id'] for e in rep['endpoints'] if state is None or e['state'] == state)

    def ans(rep, ident):
        return rep['identities'][ident]['answer']

    def gov(rep, ident):
        return [(st['sort'], st['as_of']) for st in rep['identities'][ident]['governing']]

    def nxt(rep, ident):
        return [(st['sort'], st['as_of']) for st in rep['identities'][ident]['next']]

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

    mercy = mint(db.Party, 'Mercy Hospital.')
    aetna = mint(db.Party, 'Aetna.')
    chase = mint(db.Party, 'Chase.')
    e1 = mint(db.Party, 'E1, the original lender.')
    e2 = mint(db.Party, 'E2, who bought the debt.')
    X = mint(db.Expense, 'The ER visit, Feb 14.')
    X2 = mint(db.Expense, 'The radiology read.')
    O = mint(db.Obligation, 'The Mercy bill.')
    O1 = mint(db.Obligation, 'The radiologist bill.')
    M = mint(db.Obligation, 'The mortgage.')
    p = mint(db.Payment, 'The $300 payment.')
    P1 = mint(db.Plan, "Kim's employer plan.")
    P2 = mint(db.Plan, "Rob's marketplace plan.")

    print('\n1. Absences - no selector, no inverse, no period, no path, no status\n')
    check('no selector / inverse / period / path / cache helper exists on the module',
          not any(hasattr(db, n) for n in DECIDER_NAMES))
    check('the four dated answers and three claim states are named; none is a Boolean',
          (db.EFFECT_IN, db.EFFECT_NOT, db.EFFECT_UNDETERMINED, db.EFFECT_CONTESTED) == ('in_effect', 'not_in_effect', 'undetermined', 'contested')
          and (db.CLAIM_ESTABLISHED, db.CLAIM_CANDIDATE, db.CLAIM_CONTESTED) == ('established', 'candidate', 'contested'))

    print('\n2. Tr1 / Tr2 / Tr24 - the endpoint, by whom; several; one hop\n')
    c_ox = claim(db.OBLIGATION_IN_RESPECT_OF, utterance=utter('The Mercy bill is for the ER visit.'), subject_obligation_id=O.id, object_expense_id=X.id)
    fact('nature', 'necessary care', utter('The ER visit was necessary care.'), subject_expense_id=X.id)
    fact('date_of_service', '2026-02-14', utter('It was on Feb 14.'), subject_expense_id=X.id)
    r1 = db.reach(s, O, db.OBLIGATION_IN_RESPECT_OF)
    check('Tr1 (C17): reach(O, obligation_in_respect_of) -> [X, the claim, Rob, established]; direction subject; nothing of X\'s nature or date appears on the report',
          [(e['id'], e['type'], e['claim'], e['asserter'], e['state']) for e in r1['endpoints']] == [(X.id, 'expense', c_ox.id, household.id, db.CLAIM_ESTABLISHED)]
          and r1['direction'] == db.DIRECTION_SUBJECT
          and not any(isinstance(v, str) and ('necessary' in v or '2026-02-14' in v) for _, v in _walk(r1)))
    claim(db.OBLIGATION_IN_RESPECT_OF, utterance=utter('And the radiology read.', origin=kim_party), subject_obligation_id=O.id, object_expense_id=X2.id)
    claim(db.OBLIGATION_IN_RESPECT_OF, utterance=utter('This bill covers the radiology read.', origin=mercy), subject_obligation_id=O.id, object_expense_id=X2.id)
    r2 = db.reach(s, O, db.OBLIGATION_IN_RESPECT_OF)
    check('Tr2 (C21): two expenses, three claims (Rob\'s X; Kim\'s and Mercy\'s X2) -> all three listed with their asserters - the institution\'s beside the household\'s; no "the" expense, no rank',
          set(ids(r2)) == {X.id, X2.id} and len(r2['endpoints']) == 3
          and {e['asserter'] for e in r2['endpoints']} == {household.id, kim_party.id, mercy.id}
          and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r2)))
    claim(db.PAYMENT_IN_RESPECT_OF, utterance=utter('The $300 was for the ER visit.'), subject_payment_id=p.id, object_expense_id=X.id)
    check('Tr24 (one hop): reach(O, obligation_in_respect_of) reaches X and NOTHING about the payment in respect of X - no via / path / hops key, no payment id',
          ('payment', p.id) not in [(e['type'], e['id']) for e in r2['endpoints']] and not any(k in ('via', 'path', 'hops', 'through') for k, _ in _walk(r2))
          and not any(e['type'] == 'payment' for e in r2['endpoints']))

    print("\n3. Tr3 / Tr4 - D'3: nothing manufactured; the reverse direction a labelled query\n")
    claim(db.OBLIGATION_IN_RESPECT_OF, utterance=utter('The radiologist bill is for the ER visit.'), subject_obligation_id=O1.id, object_expense_id=X.id)
    r3 = db.reach(s, p, db.PAYMENT_IN_RESPECT_OF_OBLIGATION)
    r3x = db.reach(s, X, db.OBLIGATION_IN_RESPECT_OF, as_object=True)
    check("Tr3 (D'3): p in respect of X; O and O1 in respect of X -> reach(p, payment_in_respect_of_obligation) is EMPTY with note 'no claim'; reach(X, obligation_in_respect_of, as_object) -> [O, O1] labelled 'object'; no p -> O anywhere",
          r3['endpoints'] == [] and r3['note'] == 'no claim'
          and ids(r3x) == sorted([O.id, O1.id]) and r3x['direction'] == db.DIRECTION_OBJECT
          and s.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION).count() == 0)
    c_pm = claim(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, utterance=utter('The $300 went toward the Mercy bill.'), subject_payment_id=p.id, object_obligation_id=O.id)
    r4 = db.reach(s, O, db.PAYMENT_IN_RESPECT_OF_OBLIGATION, as_object=True)
    check("Tr4 (D'18): reach(O, payment_in_respect_of_obligation, as_object) -> [p] labelled as the reverse direction; the claim is the SAME claim, of the same kind; no inverse kind exists in the registry",
          ids(r4) == [p.id] and r4['direction'] == db.DIRECTION_OBJECT and r4['endpoints'][0]['claim'] == c_pm.id and r4['kind'] == db.PAYMENT_IN_RESPECT_OF_OBLIGATION
          and not any(k in db.RULED_KINDS for k in ('obligation_paid_by', 'obligation_receives', 'plan_covers', 'plan_members')))

    print('\n4. Tr5 / Tr6 / Tr7 - candidate; contested; the party referent\n')
    A, rA = held('h-statement', chase)
    claim(db.OBLIGATION_IN_RESPECT_OF, reading=rA, subject_obligation_id=M.id, object_expense_id=X2.id)      # a match, reading-sourced
    r5 = db.reach(s, M, db.OBLIGATION_IN_RESPECT_OF)
    check('Tr5: a reading-sourced relation claim -> the endpoint listed as CANDIDATE with asserter None; not established, not dropped',
          [(e['id'], e['state'], e['asserter']) for e in r5['endpoints']] == [(X2.id, db.CLAIM_CANDIDATE, None)])
    u_ox = s.get(db.EvidentiaryRelationship, r1['endpoints'][0]['ground']).utterance
    retract(u_ox, 'No - the Mercy bill was not for the ER visit.')
    r6 = db.reach(s, O, db.OBLIGATION_IN_RESPECT_OF)
    check('Tr6: Rob retracts O -> X -> the endpoint listed as CONTESTED, still naming Rob and the claim; not erased, not read as "not in respect of"',
          [(e['id'], e['state']) for e in r6['endpoints'] if e['id'] == X.id] == [(X.id, db.CLAIM_CONTESTED)] and ids(r6, db.CLAIM_ESTABLISHED) == [X2.id, X2.id])
    chase_b = mint(db.Party, 'JPMorgan Chase Bank, N.A. (as the letter spells it).')
    KX = mint(db.Obligation, 'The car loan (Tr7).')
    claim(db.ENTITLED_PARTY_OF, utterance=utter('Chase, as the letter spells it, is the entitled party on the car loan.'), as_of='2026-01-15', subject_party_id=chase_b.id, object_obligation_id=KX.id)
    before7 = db.reach(s, chase, db.ENTITLED_PARTY_OF)
    claim(db.PARTY_CORRESPONDS, utterance=utter('That is our Chase.'), subject_party_id=chase_b.id, object_party_id=chase.id)
    r7 = db.reach(s, chase, db.ENTITLED_PARTY_OF)
    check('Tr7 (X3): the claim names party row B; once B ~ Chase is established, reach(Chase, role) reaches KX through the referent {Chase, B}; before the correspondence it did not; no row merged',
          before7['endpoints'] == [] and ids(r7) == [KX.id] and sorted(r7['referent']) == sorted([chase.id, chase_b.id])
          and s.query(db.Party).filter_by(id=chase_b.id).count() == 1)

    print('\n5. Tr8 / Tr9 / Tr21 / Tr22 / Tr23 - nothing inferred; refusals by name\n')
    claim(db.INCURRED_BY, utterance=utter('The ER visit was Kim\'s.'), subject_party_id=kim_party.id, object_expense_id=X.id)   # 9B: the ruled role's shape
    msg8 = _refused(db.reach, s, X, 'expense_in_respect_of_plan')
    check('Tr8 (E24): Kim under P1, X is Kim\'s, nothing connects X to P1 -> the (unbuilt) kind is REFUSED BY NAME, never a silent empty list; no candidate manufactured',
          msg8 is not None and 'not ruled' in msg8 and 'expense_in_respect_of_plan' in msg8)
    claim(db.UNDER_PLAN, utterance=utter('Kim is on her employer plan.'), as_of='2026-01-15', subject_party_id=kim_party.id, object_plan_id=P1.id)
    claim(db.UNDER_PLAN, utterance=utter('Kim is on my marketplace plan too.'), as_of='2026-01-15', subject_party_id=kim_party.id, object_plan_id=P2.id)
    r9 = db.reach(s, kim_party, db.UNDER_PLAN)
    check('Tr9 (E2 / F20): Kim under P1 and P2 -> both endpoints; no primary / current key',
          ids(r9) == sorted([P1.id, P2.id]) and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r9)))
    m21 = _refused(db.reach, s, O, 'services')
    m21b = _refused(db.in_effect, s, chase, 'serves', '2026-05-12')
    check('Tr21: an unruled kind -> reach and in_effect both REFUSE BY NAME',
          m21 is not None and "'services'" in m21 and m21b is not None and "'serves'" in m21b)
    m22 = _refused(db.in_effect, s, household, db.OBLIGATION_IN_RESPECT_OF, '2026-05-12')
    m22b = _refused(db.in_effect, s, household, db.UNDER_PLAN_BEGAN, '2026-05-12')
    check('Tr22: a relation kind to in_effect -> refused ("not a role - no boundary kind is bound to it"); a boundary kind -> refused ("not a role")',
          m22 is not None and 'not a role' in m22 and m22b is not None and 'boundary kind' in m22b)
    m23 = [_refused(db.reach, s, A, db.ARTEFACT_CONCERNS), _refused(db.reach, s, c_ox, db.PROPOSITION_CORRESPONDS),
           _refused(db.reach, s, A, db.ARTEFACT_ORIGIN), _refused(db.reach, s, kim_party, db.PARTY_CORRESPONDS),
           _refused(db.reach, s, kim_party, db.UNDER_PLAN_BEGAN), _refused(db.reach, s, X, db.OBLIGATION_IN_RESPECT_OF)]
    check('Tr23: meta-kinds (concerns, correspondence, origin) and a boundary kind to reach -> refused by name; a thing that does not fill the slot -> refused',
          all(m is not None for m in m23) and 'own derivation' in m23[0] and 'boundary' in m23[4] and 'does not fill' in m23[5])

    print('\n6. Ts1-Ts3 (Rob\'s three tests) / Tr10 / Tr15 - the governing stance is part of the answer\n')
    stance(db.ENTITLED_PARTY_OF, e1, '2026-01-15', object_obligation_id=M.id)                                   # holds
    t1 = db.in_effect(s, e1, db.ENTITLED_PARTY_OF, '2026-05-12')
    check('Ts1 (R1, Tr15): holds 1/15, d = 5/12 -> IN EFFECT, governing = [holds 1/15] named in the report, next = []; the extrapolation is visible',
          ans(t1, M.id) == db.EFFECT_IN and gov(t1, M.id) == [('holds', '2026-01-15')] and nxt(t1, M.id) == [] and t1['in_effect'] == [M.id])
    u_end = utter('E1 stopped being the entitled party on 4/01.')
    st_end = stance(db.ENTITLED_PARTY_OF_ENDED, e1, '2026-04-01', utterance=u_end, object_obligation_id=M.id)
    t2 = db.in_effect(s, e1, db.ENTITLED_PARTY_OF, '2026-05-12')
    check('Ts2: + ended 4/01 -> NOT IN EFFECT, governing = [ended 4/01]; the holds 1/15 still listed among the stances',
          ans(t2, M.id) == db.EFFECT_NOT and gov(t2, M.id) == [('ended', '2026-04-01')]
          and ('holds', '2026-01-15') in [(st['sort'], st['as_of']) for st in t2['identities'][M.id]['stances']])
    retract(u_end, 'I was wrong about 4/01.')
    S2, rS2 = held('h-letter', e1)
    stance(db.ENTITLED_PARTY_OF_ENDED, e1, '2026-04-01', reading=rS2, object_obligation_id=M.id)              # a candidate ending
    t3 = db.in_effect(s, e1, db.ENTITLED_PARTY_OF, '2026-05-12')
    sts3 = t3['identities'][M.id]['stances']
    check('Ts3: the 4/01 ending retracted; a CANDIDATE ending 4/01 read from a letter -> IN EFFECT, governing = [holds 1/15]; the candidate and the contested ending are listed and govern nothing',
          ans(t3, M.id) == db.EFFECT_IN and gov(t3, M.id) == [('holds', '2026-01-15')]
          and {st['state'] for st in sts3 if st['sort'] == 'ended'} == {db.CLAIM_CANDIDATE, db.CLAIM_CONTESTED})
    stance(db.ENTITLED_PARTY_OF_BEGAN, e2, '2026-01-01', object_obligation_id=O1.id)
    t10 = db.in_effect(s, e2, db.ENTITLED_PARTY_OF, '2026-05-12')
    check('Tr10 (R9): began 1/1, asked 5/12 -> IN EFFECT, governing [began 1/1]',
          ans(t10, O1.id) == db.EFFECT_IN and gov(t10, O1.id) == [('began', '2026-01-01')])

    print('\n7. Ts4-Ts10 - the table; contested exactly; TS-c\n')
    K = mint(db.Obligation, 'A loan for Ts4/Ts5.')
    stance(db.ENTITLED_PARTY_OF, chase, '2026-01-01', object_obligation_id=K.id)
    stance(db.ENTITLED_PARTY_OF, chase, '2026-05-01', object_obligation_id=K.id)
    t4 = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-03-01')
    check('Ts4 (Rob): holds 1/1 · holds 5/1 · d 3/1 -> IN EFFECT, not contested - a holds reads nothing back; governing [holds 1/1], next [holds 5/1]',
          ans(t4, K.id) == db.EFFECT_IN and gov(t4, K.id) == [('holds', '2026-01-01')] and nxt(t4, K.id) == [('holds', '2026-05-01')])
    K5 = mint(db.Obligation, 'A loan for Ts5.')
    stance(db.ENTITLED_PARTY_OF, chase, '2026-01-01', object_obligation_id=K5.id)
    stance(db.ENTITLED_PARTY_OF_ENDED, chase, '2026-05-01', object_obligation_id=K5.id)
    t5 = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-03-01')
    t5b = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-05-01')
    check('Ts5 (Rob): holds 1/1 · ended 5/1 · d 3/1 -> IN EFFECT (the ending reads back in effect, agreeing); at 5/1 the ending is G -> NOT IN EFFECT',
          ans(t5, K5.id) == db.EFFECT_IN and nxt(t5, K5.id) == [('ended', '2026-05-01')] and ans(t5b, K5.id) == db.EFFECT_NOT)
    stance(db.UNDER_PLAN_BEGAN, kim_party, '2026-01-01', object_plan_id=P1.id)
    stance(db.UNDER_PLAN_ENDED, kim_party, '2026-06-30', utterance=utter('Coverage ended June 30.', origin=aetna), object_plan_id=P1.id)
    stance(db.UNDER_PLAN_ENDED, kim_party, '2026-12-31', utterance=utter('It runs through December.'), object_plan_id=P1.id)
    t6 = db.in_effect(s, kim_party, db.UNDER_PLAN, '2026-07-15')
    t6b = db.in_effect(s, kim_party, db.UNDER_PLAN, '2026-05-01')
    t6c = db.in_effect(s, kim_party, db.UNDER_PLAN, '2027-01-15')
    check('Ts6 (R5): began 1/1 · ended 6/30 (Aetna) · ended 12/31 (Rob) -> 7/15 CONTESTED with G [ended 6/30] and N [ended 12/31] both named; 5/1 IN EFFECT; 1/15/27 NOT IN EFFECT - nothing chosen by date or party',
          ans(t6, P1.id) == db.EFFECT_CONTESTED and gov(t6, P1.id) == [('ended', '2026-06-30')] and nxt(t6, P1.id) == [('ended', '2026-12-31')]
          and {st['asserter'] for st in t6['identities'][P1.id]['governing'] + t6['identities'][P1.id]['next']} == {aetna.id, household.id}
          and ans(t6b, P1.id) == db.EFFECT_IN and ans(t6c, P1.id) == db.EFFECT_NOT)
    K7 = mint(db.Obligation, 'A loan for Ts7.')
    stance(db.ENTITLED_PARTY_OF_BEGAN, chase, '2026-01-01', object_obligation_id=K7.id)
    stance(db.ENTITLED_PARTY_OF_BEGAN, chase, '2026-05-01', object_obligation_id=K7.id)
    t7 = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-03-01')
    check('Ts7: began 1/1 · began 5/1 (no ending between) · d 3/1 -> CONTESTED - the second beginning reads back not in effect against the first',
          ans(t7, K7.id) == db.EFFECT_CONTESTED)
    K8 = mint(db.Obligation, 'A loan for Ts8.')
    stance(db.ENTITLED_PARTY_OF_BEGAN, chase, '2026-01-01', object_obligation_id=K8.id)
    stance(db.ENTITLED_PARTY_OF_ENDED, chase, '2026-03-01', object_obligation_id=K8.id)
    stance(db.ENTITLED_PARTY_OF_BEGAN, chase, '2026-05-01', object_obligation_id=K8.id)
    check('Ts8 (R4): began 1/1 · ended 3/1 · began 5/1 -> 4/1 NOT IN EFFECT (the next beginning reads back not in effect, agreeing); 6/1 IN EFFECT; nothing written',
          ans(db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-04-01'), K8.id) == db.EFFECT_NOT
          and ans(db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-06-01'), K8.id) == db.EFFECT_IN)
    K9 = mint(db.Obligation, 'A loan for Ts9.')
    stance(db.ENTITLED_PARTY_OF_BEGAN, chase, '2026-05-01', object_obligation_id=K9.id)
    stance(db.ENTITLED_PARTY_OF_ENDED, chase, '2026-05-01', object_obligation_id=K9.id)
    t9 = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-05-01')
    check('Ts9: began 5/1 · ended 5/1 · d 5/1 -> CONTESTED within G (two forward readings)',
          ans(t9, K9.id) == db.EFFECT_CONTESTED and len(t9['identities'][K9.id]['governing']) == 2)
    check('Ts10 (TS-c): began 1/1 · ended 6/30 -> 6/30 NOT IN EFFECT, 6/29 IN EFFECT - the ending\'s date is the first date not in effect',
          ans(db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-05-01'), K5.id) == db.EFFECT_NOT
          and ans(db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-04-30'), K5.id) == db.EFFECT_IN)

    print('\n8. Ts11-Ts14 / Tr11 / Tr13 / Tr16-Tr19 - an ending alone; retraction; overlap; two parties; learned-at; nothing\n')
    K11 = mint(db.Obligation, 'A loan for Ts11.')
    stance(db.ENTITLED_PARTY_OF_ENDED, chase, '2026-06-30', object_obligation_id=K11.id)
    check('Ts11 (R12): ended 6/30 only -> 5/1 UNDETERMINED (the ending\'s backward reading supplies no answer where nothing governs - no period by the back door); 7/1 NOT IN EFFECT',
          ans(db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-05-01'), K11.id) == db.EFFECT_UNDETERMINED
          and nxt(db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-05-01'), K11.id) == [('ended', '2026-06-30')]
          and ans(db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-07-01'), K11.id) == db.EFFECT_NOT)
    K12 = mint(db.Obligation, 'A loan for Ts12.')
    u12 = utter('Chase became the entitled party 1/1.')
    stance(db.ENTITLED_PARTY_OF_BEGAN, chase, '2026-01-01', utterance=u12, object_obligation_id=K12.id)
    retract(u12, 'Chase never was.')
    t12 = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-05-12')
    check('Ts12 (R6): the beginning retracted -> UNDETERMINED, not "ended"; the retracted stance listed as contested; governing []',
          ans(t12, K12.id) == db.EFFECT_UNDETERMINED and gov(t12, K12.id) == []
          and [st['state'] for st in t12['identities'][K12.id]['stances']] == [db.CLAIM_CONTESTED])
    stance(db.UNDER_PLAN_BEGAN, kim_party, '2026-07-01', object_plan_id=P2.id)
    t13 = db.in_effect(s, kim_party, db.UNDER_PLAN, '2026-08-01')
    check('Ts13 (R7 / Tr13): Kim under P1 (began 1/1, contested ending) and P2 (began 7/1) -> in August P2 IN EFFECT and P1 CONTESTED, per identity; the in_effect list is a fact; nothing resolved, no primary',
          ans(t13, P2.id) == db.EFFECT_IN and ans(t13, P1.id) == db.EFFECT_CONTESTED and t13['in_effect'] == [P2.id]
          and not any(k in FORBIDDEN_KEYS for k, _ in _walk(t13)))
    K14 = mint(db.Obligation, 'A loan for Ts14.')
    stance(db.ENTITLED_PARTY_OF, chase, '2026-01-01', utterance=utter('Chase holds it.'), object_obligation_id=K14.id)
    stance(db.ENTITLED_PARTY_OF, chase, '2026-01-01', utterance=utter('Chase holds it.', origin=aetna), object_obligation_id=K14.id)
    t14 = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-03-01')
    check('Ts14: holds 1/1 (Rob) · holds 1/1 (Aetna) -> IN EFFECT, both governing stances named, neither ranked',
          ans(t14, K14.id) == db.EFFECT_IN and len(t14['identities'][K14.id]['governing']) == 2
          and {st['asserter'] for st in t14['identities'][K14.id]['governing']} == {household.id, aetna.id})
    stance(db.ENTITLED_PARTY_OF_ENDED, e1, '2026-05-01', object_obligation_id=O.id)
    stance(db.ENTITLED_PARTY_OF_BEGAN, e2, '2026-05-01', object_obligation_id=O.id)
    check('Tr11 (R8): E1 ended 5/1, E2 began 5/1 -> 5/12: E1 NOT IN EFFECT, E2 IN EFFECT; 4/12: E1 UNDETERMINED (an ending alone), E2 UNDETERMINED (no stance precedes) - never "not in effect" from absence',
          ans(db.in_effect(s, e1, db.ENTITLED_PARTY_OF, '2026-05-12'), O.id) == db.EFFECT_NOT
          and ans(db.in_effect(s, e2, db.ENTITLED_PARTY_OF, '2026-05-12'), O.id) == db.EFFECT_IN
          and ans(db.in_effect(s, e1, db.ENTITLED_PARTY_OF, '2026-04-12'), O.id) == db.EFFECT_UNDETERMINED
          and ans(db.in_effect(s, e2, db.ENTITLED_PARTY_OF, '2026-04-12'), O.id) == db.EFFECT_UNDETERMINED)
    K16 = mint(db.Obligation, 'A loan for Tr16.')
    stance(db.ENTITLED_PARTY_OF_BEGAN, chase, '2026-01-01', object_obligation_id=K16.id)
    late = stance(db.ENTITLED_PARTY_OF_ENDED, chase, '2026-06-30', utterance=utter('Ended June 30.', '2026-08-15T09:00:00'), object_obligation_id=K16.id)
    late.created_at = datetime(2026, 8, 15, 9)
    s.commit()
    check('Tr16 (R3): an ending as_of 6/30 recorded 8/15, asked "on 7/1" -> NOT IN EFFECT - effective-at governs; in_effect reads no created_at',
          ans(db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-07-01'), K16.id) == db.EFFECT_NOT
          and 'created_at' not in __import__('inspect').getsource(db.in_effect) and 'created_at' not in __import__('inspect').getsource(db._stance_answer))
    K17 = mint(db.Obligation, 'A loan for Tr17.')
    card, r_card = held('h-card', chase)
    stance(db.ENTITLED_PARTY_OF_BEGAN, chase, '2026-01-01', reading=r_card, object_obligation_id=K17.id)
    t17 = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-05-12')
    check('Tr17 (R11): the insurer\'s card read "member since 1/1" -> a CANDIDATE stance, listed, grounds nothing -> UNDETERMINED',
          ans(t17, K17.id) == db.EFFECT_UNDETERMINED and [st['state'] for st in t17['identities'][K17.id]['stances']] == [db.CLAIM_CANDIDATE])
    K19 = mint(db.Obligation, 'A loan for Tr19 - no stance at all.')
    t19 = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-05-12')
    check('Tr19: no stance at all for (Chase, role, K19) -> the identity is absent from the report, not "not in effect"; a party with no stances anywhere -> note "no stance"',
          K19.id not in t19['identities'] and db.in_effect(s, mercy, db.ENTITLED_PARTY_OF, '2026-05-12')['note'] == 'no stance')

    print('\n9. Tr20 / Tr25 / Tr26 - surfaced not stored; null models; where the failure appears\n')
    before = snapshot()
    reports = [db.reach(s, O, db.OBLIGATION_IN_RESPECT_OF), db.reach(s, X, db.OBLIGATION_IN_RESPECT_OF, as_object=True),
               db.reach(s, kim_party, db.UNDER_PLAN), db.in_effect(s, kim_party, db.UNDER_PLAN, '2026-08-01'),
               db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-03-01'), db.in_effect(s, e1, db.ENTITLED_PARTY_OF, '2026-05-12')]
    check('Tr20: six reads wrote nothing - every row identical; no period / interval / status / current column or table exists',
          snapshot() == before
          and not any(any(w in c.name for w in ('period', 'interval', 'in_effect', 'current', 'effective_from', 'effective_to'))
                      for cls in (db.Proposition, db.Party, db.Obligation, db.Payment, db.Expense, db.Plan, db.Artefact, db.Reading, db.Utterance, db.EvidentiaryRelationship)
                      for c in cls.__table__.columns))
    direct = sorted((c.object_expense_id, c.id) for c in s.query(db.Proposition).filter_by(kind=db.OBLIGATION_IN_RESPECT_OF, subject_obligation_id=O.id))
    check('Tr25 (null model, reach): the endpoints of reach(O, obligation_in_respect_of) are exactly the direct query of claims by kind and subject - a correctness oracle',
          sorted({(e['id'], e['claim']) for e in reports[0]['endpoints']}) == direct)
    K25 = mint(db.Obligation, 'A loan for Tr25.')
    stance(db.ENTITLED_PARTY_OF_BEGAN, mercy, '2026-03-01', object_obligation_id=K25.id)
    oracle = all(ans(db.in_effect(s, mercy, db.ENTITLED_PARTY_OF, d), K25.id) == (db.EFFECT_IN if d >= '2026-03-01' else db.EFFECT_UNDETERMINED)
                 for d in ('2026-01-01', '2026-02-28', '2026-03-01', '2026-03-02', '2026-12-31'))
    check('Tr25 (null model, in_effect): one began, no ended -> IN EFFECT for every d >= the beginning, UNDETERMINED before - exact',
          oracle)
    check('Tr26 (where the failure appears): "in effect" never said with an empty governing set; never said where the next stance reads back against it; no endpoint without a claim; no second hop',
          all(v['governing'] for rep in reports if 'identities' in rep for v in rep['identities'].values() if v['answer'] == db.EFFECT_IN)
          and all(e['claim'] is not None for rep in reports if 'endpoints' in rep for e in rep['endpoints'])
          and ans(t6, P1.id) == db.EFFECT_CONTESTED and ans(t11 := db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-05-01'), K11.id) == db.EFFECT_UNDETERMINED)

    print('\n10. The dependency direction and the wiring guard\n')
    check('reach and in_effect call referent() for the subject and nothing that composes, projects, scores or resolves - no aboutness / chain_strength / level_consistency / independence / parse_disputes',
          'referent' in (calls_in(db.reach) | calls_in(db._referent_members))
          and not ({'aboutness', 'chain_strength', 'level_consistency', 'independence', 'parse_disputes', 'derived_strength'} & (calls_in(db.reach) | calls_in(db.in_effect))))
    check('the 7F wiring guard is executable (AST): reach, in_effect and their helpers call no session write method and construct no mapped class',
          all(writes_in(f) == [] for f in (db.reach, db.in_effect, db._stance_answer, db._claim_states, db._retracted, db._referent_members)))


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
