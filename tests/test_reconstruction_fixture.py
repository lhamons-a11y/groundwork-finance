"""reconstruction - the executable trace of `gw 2.0/CONSUMER_DERIVATIONS.md` pass 7I (ruled 2026-09-19, s 7I.8).

THE CHECK, NOT THE VOCABULARY. No disposition kind is ruled; the reconstruction tests s5's invariant over amounts 7G
already establishes: P = the direct predecessor side (O and the other direct predecessors of each direct successor),
N = the direct successors; before = sum of P's confirmed(at-minus); after = sum of N's confirmed(d) plus each
predecessor's confirmed(d) where its governing P-ack is dated >= at (eligibility by the P-ack, never by a confirmed
value); unaccounted = after - before, a number with its terms and no reading; negative kept; zero is arithmetic.

What this slice can and cannot exercise
---------------------------------------
    Di1  B1 / case 3: the arrears are a position - unaccounted 0; overdue never read                  EXERCISED
    Di2  case 3': the new statement says 3,525 -> +525, no category                                     EXERCISED
    Di3  B2: O3 replaces O1; O1 restated 0 -> 0                                                          EXERCISED
    Di4  B2 without the 0 restatement: O1 not restated -> undetermined naming O1; never erased          EXERCISED
    Di5  B3 refinance with Chase's letter: the payoff unresolved, inside the base; 0                    EXERCISED
    Di6  B3 without the letter: undetermined naming O1 and the payoff                                   EXERCISED
    Di7  case 8: the agency's 3,300 -> +300 without an anchoring                                        EXERCISED
    Di8  case 1: the $650 -> -900, not waived, not never-liable                                         EXERCISED
    Di9  B5 partial: O1 an after-context with its residual -> 0                                        EXERCISED
    Di10 B4 consolidation: the successor's other predecessors pulled in -> 0                            EXERCISED
    Di11 B6 split -> 0                                                                                   EXERCISED
    Di12 B11 chain: one hop                                                                              EXERCISED
    Di13 candidate / contested relations listed, not in the group                                       EXERCISED
    Di14 the relation's content is not read                                                             EXERCISED
    Di15 undetermined propagates from 7G                                                                EXERCISED
    Di16 as of d: a successor restated after d is not restated by d                                     EXERCISED
    Di17 surfaced not stored                                                                             EXERCISED
    Di18 the null model: fully restated -> 0; one statement moved by 100 -> exactly 100                  EXERCISED
    Di19 where the failure appears                                                                       EXERCISED
    Di20 one hop mechanically (Rob's diagram, anchored at O1 and at O2)                                 EXERCISED
    Di21 at-minus: events dated exactly `at` are after-side                                             EXERCISED
    Di22 the negative discriminator: -100 kept                                                          EXERCISED
    Di23 zero is not a disposition; the write-off shape -> -3,000 and nothing more                      EXERCISED
    the wiring guard: AST (session receivers) + a full row-content snapshot                              EXERCISED
    the disposition vocabulary (blocked), 7H reconciliation, 7J                                          NOT BUILT

Run:  python tests/test_reconstruction_fixture.py
"""
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL = [], []


def check(name, condition):
    (PASS if condition else FAIL).append(name)
    print(('  OK    ' if condition else '  FAIL  ') + name)


DECIDER_NAMES = ('disposition', 'disposition_of', 'dispositions_of', 'waived', 'written_off', 'write_off', 'capitalised', 'capitalized',
                 'apportion', 'close_obligation', 'reconstructed', 'reconstruction_cache', 'successors_of', 'transition_group',
                 'family_of', 'originated', 'relocated', 'terminated')
FORBIDDEN_KEYS = ('disposition', 'waived', 'written_off', 'forgiven', 'discharged', 'closed', 'capitalised', 'originated', 'relocated',
                  'terminated', 'appeared', 'left', 'sign', 'reading', 'category', 'cause', 'fee', 'adjustment', 'overdue', 'ahead',
                  'share', 'scope', 'status', 'anchoring')


def _role(subject, obj):
    return {'subject': (subject,), 'object': (obj,), 'symmetric': False, 'reading_establishes': False, 'relational_knowing': True, 'role': True}


def _boundary(of, which, subject, obj):
    r = _role(subject, obj)
    r.update({'boundary': which, 'of': of})
    return r


STAND_INS = {
}
CATALOGUE = {'acknowledgment': 'acknowledged', 'entitled_party': 'entitled_party_of', 'balance': 'balance',   # acknowledged / balance: ruled (9D-i)
             'payment_amount': 'amount', 'occurred_on': 'occurred_on', 'paid_by': 'paid_by', 'paid_to': 'paid_to'}


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_rc_')
    eng = create_engine(f'sqlite:///{Path(d) / "t.db"}')

    @event.listens_for(eng, 'connect')
    def _fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA synchronous=OFF')          # throwaway DB: no fsync per commit
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
    check('the stand-in role kind is removed; the registry is as shipped; no value or acknowledgment kind was registered',
          db.RULED_KINDS == shipped)   # every kind this fixture reads is ruled: roles 9B, stances 9D-i, values 9D-iv
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'},   # amount / occurred_on: ruled values since 9D-iv - knowing by the role-set, not by the map
               'amount': {'person', 'institution'}, 'occurred_on': {'person', 'institution'}}
    D = Decimal

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

    def claim(kind, utterance=None, reading=None, as_of=None, content=None, **slots):
        obj = db.PARTICIPANT_ESTABLISHED if any(k.startswith('object_') for k in slots) else db.PARTICIPANT_NONE
        pr = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=obj, as_of=as_of, content=content, **slots)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utterance, reading=reading)
        return pr

    def retract(u, text):
        r = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                           subject_utterance_id=u.id)
        s.add(r)
        s.commit()
        evidence(r, utterance=utter(text, '2026-12-20T09:00:00'))

    def entitled(party, O, began='2026-01-01'):
        claim(db.ENTITLED_PARTY_OF_BEGAN, utterance=utter(f'{began} entitled'), as_of=began, subject_party_id=party.id, object_obligation_id=O.id)

    def pay(O, amount, on, payer, payee, attach=True, amount_by=None):
        p = mint(db.Payment, f'Paid {amount} on {on}.')
        claim(db.AMOUNT, utterance=utter(amount, origin=amount_by), content=amount, subject_payment_id=p.id)
        claim(db.OCCURRED_ON, utterance=utter(on), as_of=on, subject_payment_id=p.id)
        if payer is not None:
            claim('paid_by', utterance=utter('paid by'), as_of=on, subject_party_id=payer.id, object_payment_id=p.id)
        if payee is not None:
            claim('paid_to', utterance=utter('paid to'), as_of=on, subject_party_id=payee.id, object_payment_id=p.id)
        if attach:
            claim(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, utterance=utter('toward it'), subject_payment_id=p.id, object_obligation_id=O.id)
        return p

    def ack(by, p, as_of, origin=None, reading=None):
        return claim(db.ACKNOWLEDGED, utterance=None if reading else utter(f'ack {as_of}', origin=origin or by), reading=reading,
                     as_of=as_of, subject_party_id=by.id, object_payment_id=p.id)

    def stated(O, by, amount, as_of, origin=None):
        return claim(db.BALANCE, utterance=utter(amount, origin=origin or by), as_of=as_of, content=amount, subject_obligation_id=O.id)


    def rec(O, at, d):
        return db.reconstruction(s, O, at, d, CATALOGUE, KNOWING)

    def un(r):
        return r['unaccounted']['value']

    def after_term(r, O):
        return next(t for t in r['after']['terms'] if t['obligation'] == O.id)

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

    def replaces(new, old, utterance=None, reading=None, content=None):
        return claim(db.OBLIGATION_REPLACES, utterance=utterance if (utterance or reading) else utter('replaces'), reading=reading,
                     content=content, subject_obligation_id=new.id, object_obligation_id=old.id)

    chase = mint(db.Party, 'Chase.')
    mercy = mint(db.Party, 'Mercy Hospital.')
    newbank = mint(db.Party, 'NewBank.')
    agency = mint(db.Party, 'The collection agency.')
    aetna = mint(db.Party, 'Aetna.')

    print('\n1. Absences - no disposition, category, family, apportionment or cache helper\n')
    check('no disposition / waived / written_off / capitalised / apportion / close / family / cache helper exists on the module',
          not any(hasattr(db, n) for n in DECIDER_NAMES))
    check('refusals: a non-Obligation; d before at',
          _refused(db.reconstruction, s, chase, '2026-02-01', '2026-02-28', CATALOGUE, KNOWING) is not None
          and 'precedes' in (_refused(db.reconstruction, s, mint(db.Obligation, 'x'), '2026-02-01', '2026-01-15', CATALOGUE, KNOWING) or ''))

    print('\n2. Di1 / Di2 / Di21 - the same obligation: the arrears are a position; events on `at`\n')
    O1 = mint(db.Obligation, 'The Mercy plan (case 3).')
    entitled(mercy, O1)
    stated(O1, mercy, '$3,000', '2026-01-01')
    claim('overdue', utterance=utter('$525 behind', origin=mercy), as_of='2026-01-31', content='$525', subject_obligation_id=O1.id)
    stated(O1, mercy, '$3,000', '2026-02-01')                                      # new terms; the statement at `at`
    r1 = rec(O1, '2026-02-01', '2026-02-28')
    check('Di1 (B1 / case 3): no successor -> P = N = {O1}; before = O1(1/31) = 3,000; after = O1(2/28) = 3,000 (restated 2/1); UNACCOUNTED 0 - the $525 overdue is a position, never read',
          r1['group']['predecessors'] == [O1.id] and r1['group']['successors'] == [] and r1['before']['value'] == D('3000')
          and r1['after']['value'] == D('3000') and un(r1) == D('0')
          and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r1)) and not any(v == '$525' for _, v in _walk(r1)))
    check('Di21 (at-minus): the 2/1 statement is AFTER-side (it restates O1: eligible, as_of >= at) and before reads the 1/1 position on 1/31',
          after_term(r1, O1)['eligible'] and after_term(r1, O1)['stated']['as_of'] == '2026-02-01'
          and r1['before']['terms'][0]['stated']['as_of'] == '2026-01-01')
    O2 = mint(db.Obligation, "The Mercy plan (case 3').")
    entitled(mercy, O2)
    stated(O2, mercy, '$3,000', '2026-01-01')
    stated(O2, mercy, '$3,525', '2026-02-01')
    r2 = rec(O2, '2026-02-01', '2026-02-28')
    check("Di2 (case 3'): the new statement says 3,525 -> UNACCOUNTED +525; no capitalised / fee / originated key anywhere; dispositions read: none",
          un(r2) == D('525') and r2['dispositions']['read'] == [] and 'no disposition kind is ruled' in r2['dispositions']['note']
          and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r2)))

    print('\n3. Di3 / Di4 / Di14 / Di23 - replacement; not restated is never erased; the relation\'s content; zero\n')
    O3a = mint(db.Obligation, 'The old plan.')
    O3b = mint(db.Obligation, 'The new plan.')
    entitled(mercy, O3a)
    entitled(mercy, O3b)
    stated(O3a, mercy, '$3,000', '2026-01-01')
    rel3 = replaces(O3b, O3a, content='$3,000 rolled over - all of it')
    stated(O3b, mercy, '$3,000', '2026-02-01')
    r4 = rec(O3a, '2026-02-01', '2026-02-28')
    check('Di4 (B2, not restated): O3b replaces O3a; O3a has no statement after 2/1 -> O3a NOT RESTATED (its 1/1 position carried forward, shown as such); UNACCOUNTED UNDETERMINED naming O3a - never erased to 0, never counted at 3,000 on the after side',
          r4['group']['successors'] == [O3b.id] and not after_term(r4, O3a)['eligible'] and after_term(r4, O3a)['reason'] == db.RECON_NOT_RESTATED
          and after_term(r4, O3a)['confirmed'] == D('3000') and r4['after']['value'] is None and un(r4) is None
          and f'obligation {O3a.id}' in r4['unaccounted']['reason'])
    stated(O3a, mercy, '$0', '2026-02-01')
    r3 = rec(O3a, '2026-02-01', '2026-02-28')
    check('Di3 (B2): O3a restated $0 at 2/1 -> before 3,000; after = O3b 3,000 + O3a 0; UNACCOUNTED 0',
          r3['before']['value'] == D('3000') and r3['after']['value'] == D('3000') and un(r3) == D('0')
          and [t['obligation'] for t in r3['after']['terms']] == [O3b.id, O3a.id])
    check('Di23 (zero is not a disposition): O3a\'s $0 is an arithmetic result of a P-ack; no discharged / closed / written_off / waived / disposition word or key in the report',
          after_term(r3, O3a)['confirmed'] == D('0') and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r3))
          and not any(isinstance(v, str) and any(w in v.lower() for w in ('written off', 'waived', 'forgiven', 'closed')) for _, v in _walk(r3)))
    check('Di14: the relation\'s content ("$3,000 rolled over - all of it") is not read - nothing in the report carries it; the relation is listed by claim, subject, object, state only',
          not any(isinstance(v, str) and 'rolled over' in v for _, v in _walk(r3))
          and r3['group']['relations'] == [(rel3.id, O3b.id, O3a.id, db.CLAIM_ESTABLISHED)])
    O23 = mint(db.Obligation, 'The write-off shape.')
    entitled(mercy, O23)
    stated(O23, mercy, '$3,000', '2026-01-01')
    stated(O23, mercy, '$0', '2026-03-01')
    r23 = rec(O23, '2026-03-01', '2026-03-31')
    check('Di23 (the write-off shape): before 3,000, after 0 -> UNACCOUNTED -3,000 and nothing more - no explanation invented',
          un(r23) == D('-3000') and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r23)))

    print('\n4. Di5 / Di6 - the refinance: the payoff is unresolved; the letter reconstructs it\n')
    O5a = mint(db.Obligation, 'The Chase mortgage.')
    O5b = mint(db.Obligation, 'The NewBank loan.')
    entitled(chase, O5a)
    entitled(newbank, O5b)
    stated(O5a, chase, '$178,412', '2026-02-01')
    payoff = pay(O5a, '$178,412', '2026-03-01', newbank, chase)                      # a third party pays E
    ack(chase, payoff, '2026-03-01')
    replaces(O5b, O5a)
    stated(O5b, newbank, '$178,412', '2026-03-01')
    r6 = rec(O5a, '2026-03-01', '2026-03-31')
    check('Di6 (B3 without the letter): the payoff is DISCHARGED with direction UNDETERMINED (payer NewBank is neither the household nor E); O5a not restated; UNACCOUNTED undetermined naming O5a; the payoff listed as unresolved - the record cannot say the Chase mortgage is gone',
          un(r6) is None and not after_term(r6, O5a)['eligible']
          and [(u['obligation'], u['payment'], u['station']) for u in r6['unresolved_payments']] == [(O5a.id, payoff.id, db.STATION_DISCHARGED)])
    stated(O5a, chase, '$0', '2026-03-01')                                          # Chase's paid-in-full letter
    r5 = rec(O5a, '2026-03-01', '2026-03-31')
    check('Di5 (B3 with the letter): O5a restated $0 at 3/1 (the payoff inside its base); before 178,412; after = O5b 178,412 + O5a 0; UNACCOUNTED 0 - reconstructed because the letter is recorded, not because the payoff\'s direction was inferred',
          un(r5) == D('0') and after_term(r5, O5a)['eligible'] and after_term(r5, O5a)['confirmed'] == D('0')
          and [(u['payment']) for u in r5['unresolved_payments']] == [payoff.id])

    print('\n5. Di7 / Di8 - the tripwire and the $650\n')
    O7 = mint(db.Obligation, 'The hospital bill sold to an agency.')
    entitled(mercy, O7)
    claim(db.ENTITLED_PARTY_OF_ENDED, utterance=utter('sold'), as_of='2026-05-01', subject_party_id=mercy.id, object_obligation_id=O7.id)
    entitled(agency, O7, began='2026-05-01')
    stated(O7, mercy, '$3,000', '2026-04-01')
    stated(O7, agency, '$3,300', '2026-05-15')
    r7 = rec(O7, '2026-05-01', '2026-05-31')
    check('Di7 (case 8): one O, E changes (no relation); before = Mercy\'s 3,000 (4/30); after = the agency\'s 3,300 (in effect as E at 5/15); UNACCOUNTED +300 - expressible without an anchoring; no fee key',
          r7['group']['successors'] == [] and r7['before']['value'] == D('3000') and r7['after']['value'] == D('3300') and un(r7) == D('300')
          and after_term(r7, O7)['stated']['asserter'] == agency.id and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r7)))
    X = mint(db.Expense, 'The ER visit.')
    O8 = mint(db.Obligation, 'The Mercy bill (case 1).')
    entitled(mercy, O8)
    stated(O8, mercy, '$1,200', '2026-01-01')
    p8 = pay(O8, '$300', '2026-01-15', household, mercy)
    ack(mercy, p8, '2026-01-20')
    p8a = pay(O8, '$250', '2026-02-01', aetna, mercy, attach=False)                  # the insurer's payment - in respect of X, not O (D'5)
    claim(db.PAYMENT_IN_RESPECT_OF, utterance=utter('Aetna paid on the visit'), subject_payment_id=p8a.id, object_expense_id=X.id)
    stated(O8, mercy, '$0', '2026-03-01')
    r8 = rec(O8, '2026-03-01', '2026-03-31')
    check('Di8 (case 1): before = 1,200 - 300 = 900; after 0 -> UNACCOUNTED -900 - the insurer\'s payment (not attached to O) and the $650 adjustment are nowhere in O\'s record; not waived, not never-liable',
          r8['before']['value'] == D('900') and un(r8) == D('-900') and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r8))
          and r8['unresolved_payments'] == [])

    print('\n6. Di9 / Di10 / Di11 / Di12 / Di20 / Di13 - the group: partial, consolidation, split, chain, one hop, candidates\n')
    Oc = mint(db.Obligation, 'The card.')
    Ol = mint(db.Obligation, 'The consolidation loan (partial).')
    entitled(chase, Oc)
    entitled(newbank, Ol)
    stated(Oc, chase, '$8,000', '2026-01-01')
    replaces(Ol, Oc)
    stated(Oc, chase, '$3,000', '2026-02-01')
    stated(Ol, newbank, '$5,000', '2026-02-01')
    r9 = rec(Oc, '2026-02-01', '2026-02-28')
    check('Di9 (B5 partial): Oc is an after-context with its residual - before 8,000; after = Ol 5,000 + Oc 3,000; UNACCOUNTED 0; Oc appears once per side with two different figures',
          un(r9) == D('0') and [(t['obligation'], t['side'], t['confirmed']) for t in r9['after']['terms']] == [(Ol.id, 'successor', D('5000')), (Oc.id, 'predecessor', D('3000'))]
          and r9['before']['terms'][0]['confirmed'] == D('8000'))
    Oa, Ob_, Oc2 = mint(db.Obligation, 'Card A.'), mint(db.Obligation, 'Card B.'), mint(db.Obligation, 'Card C.')
    Ok = mint(db.Obligation, 'The consolidation loan.')
    for o, amt in ((Oa, '$5,000'), (Ob_, '$3,000'), (Oc2, '$2,000')):
        entitled(chase, o)
        stated(o, chase, amt, '2026-01-01')
        replaces(Ok, o)
        stated(o, chase, '$0', '2026-02-01')
    entitled(newbank, Ok)
    stated(Ok, newbank, '$10,000', '2026-02-01')
    r10 = rec(Oa, '2026-02-01', '2026-02-28')
    check('Di10 (B4 consolidation): anchored at Card A, the group pulls in Ok\'s other predecessors B and C - P = {A, B, C}, N = {Ok}; before 10,000; after 10,000 + 0 + 0 + 0; UNACCOUNTED 0 (not A alone against Ok)',
          sorted(r10['group']['predecessors']) == sorted([Oa.id, Ob_.id, Oc2.id]) and r10['group']['successors'] == [Ok.id]
          and r10['before']['value'] == D('10000') and un(r10) == D('0'))
    Os = mint(db.Obligation, 'The hospital bill (split).')
    Of, Op = mint(db.Obligation, 'The facility plan.'), mint(db.Obligation, 'The physician plan.')
    entitled(mercy, Os)
    entitled(mercy, Of)
    entitled(mercy, Op)
    stated(Os, mercy, '$3,000', '2026-01-01')
    replaces(Of, Os)
    replaces(Op, Os)
    stated(Of, mercy, '$1,800', '2026-02-01')
    stated(Op, mercy, '$1,200', '2026-02-01')
    stated(Os, mercy, '$0', '2026-02-01')
    r11 = rec(Os, '2026-02-01', '2026-02-28')
    check('Di11 (B6 split): N = {Of, Op}; after 1,800 + 1,200 + 0; UNACCOUNTED 0; nothing apportioned',
          sorted(r11['group']['successors']) == sorted([Of.id, Op.id]) and un(r11) == D('0'))
    C1, C2, C3, C4 = (mint(db.Obligation, f'Chain O{i}.') for i in (1, 2, 3, 4))
    for o in (C1, C2, C3, C4):
        entitled(chase, o)
        stated(o, chase, '$1,000', '2026-01-01')
    replaces(C2, C1)
    replaces(C3, C2)
    replaces(C3, C4)
    for o in (C1, C2, C3, C4):
        stated(o, chase, '$0' if o is not C3 else '$2,000', '2026-02-01')
    r20a, r20b = rec(C1, '2026-02-01', '2026-02-28'), rec(C2, '2026-02-01', '2026-02-28')
    check('Di20 / Di12 (one hop, Rob\'s diagram O1->O2->O3, O4->O3): anchored at O1 -> N = {O2}, P = {O1}; O3 and O4 outside; anchored at O2 -> N = {O3}, P = {O2, O4}; O1 outside; no recursive family',
          r20a['group']['successors'] == [C2.id] and r20a['group']['predecessors'] == [C1.id]
          and r20b['group']['successors'] == [C3.id] and sorted(r20b['group']['predecessors']) == sorted([C2.id, C4.id])
          and C3.id not in r20a['group']['predecessors'] + r20a['group']['successors'] and C1.id not in r20b['group']['predecessors'])
    check('Di12 (B11): each transition balances on its own - O1 -> O2: before 1,000, after 0 + 0 -> -1,000 (O2 restated 0: the money went on to O3, another transition); O2, O4 -> O3: before 2,000, after 2,000 -> 0',
          un(r20a) == D('-1000') and un(r20b) == D('0'))
    Od, Oe = mint(db.Obligation, 'Candidate old.'), mint(db.Obligation, 'Candidate new.')
    entitled(chase, Od)
    entitled(chase, Oe)
    stated(Od, chase, '$500', '2026-01-01')
    stated(Od, chase, '$500', '2026-02-01')
    _, rS = held('h-newbank-statement', newbank)
    replaces(Oe, Od, reading=rS)                                                     # a matcher's candidate
    u_rel = utter('Oe replaced Od.')
    replaces(Oe, Od, utterance=u_rel)
    retract(u_rel, 'No it did not.')
    r13 = rec(Od, '2026-02-01', '2026-02-28')
    check('Di13: a reading-sourced relation and a retracted one -> listed as candidate / contested, NOT in the group; the B1 arm runs: P = N = {Od}; 0',
          r13['group']['successors'] == [] and len(r13['group']['candidates']) == 1 and len(r13['group']['contested']) == 1 and un(r13) == D('0'))

    print('\n7. Di15 / Di16 / Di17 / Di18 / Di22 / Di19 - undetermined; as of d; stored; the null model; negative; failure\n')
    Ou = mint(db.Obligation, 'No P-ack.')
    entitled(chase, Ou)
    r15 = rec(Ou, '2026-02-01', '2026-02-28')
    check('Di15: a predecessor with no P-ack -> before undetermined with 7G\'s reason; UNACCOUNTED undetermined naming Ou; never zero',
          r15['before']['value'] is None and un(r15) is None and f'obligation {Ou.id}' in r15['unaccounted']['reason'])
    Ox, Oy = mint(db.Obligation, 'Restated later, old.'), mint(db.Obligation, 'Restated later, new.')
    entitled(chase, Ox)
    entitled(chase, Oy)
    stated(Ox, chase, '$700', '2026-01-01')
    replaces(Oy, Ox)
    stated(Ox, chase, '$0', '2026-02-01')
    stated(Oy, chase, '$700', '2026-03-15')
    r16a, r16b = rec(Ox, '2026-02-01', '2026-02-28'), rec(Ox, '2026-02-01', '2026-03-31')
    check('Di16 (as of d): the successor\'s statement is dated 3/15 -> asked 2/28 it is not restated (no stated position by d), UNACCOUNTED undetermined naming it; asked 3/31 it balances to 0; created_at never read',
          un(r16a) is None and not after_term(r16a, Oy)['eligible'] and un(r16b) == D('0')
          and 'created_at' not in __import__('inspect').getsource(db.reconstruction))
    before = snapshot()
    rec(O5a, '2026-03-01', '2026-03-31')
    check('Di17: reading a report wrote nothing - every row identical; no disposition / category / reconstructed column on any 2.0 table',
          snapshot() == before
          and not any(any(w in c.name for w in ('disposition', 'category', 'reconstructed', 'waived', 'written_off'))
                      for cls in (db.Proposition, db.Party, db.Obligation, db.Payment, db.Expense, db.Plan, db.Artefact, db.Reading, db.Utterance, db.EvidentiaryRelationship)
                      for c in cls.__table__.columns))
    On, Om = mint(db.Obligation, 'Null old.'), mint(db.Obligation, 'Null new.')
    entitled(chase, On)
    entitled(chase, Om)
    stated(On, chase, '$1,000', '2026-01-01')
    pn = pay(On, '$100', '2026-01-10', household, chase)
    ack(chase, pn, '2026-01-12')
    replaces(Om, On)
    stated(On, chase, '$0', '2026-02-01')
    stated(Om, chase, '$900', '2026-02-01')
    r18 = rec(On, '2026-02-01', '2026-02-28')
    check('Di18 (null model): fully restated, fully discharged -> before 900 (1,000 - 100 discharged); after 900 + 0; UNACCOUNTED 0',
          r18['before']['value'] == D('900') and un(r18) == D('0'))
    stated(Om, chase, '$1,000', '2026-02-02')
    r18b = rec(On, '2026-02-01', '2026-02-28')
    check('Di18 (null model): one statement moved by 100 -> UNACCOUNTED exactly +100',
          un(r18b) == D('100'))
    Ov = mint(db.Obligation, 'Negative.')
    entitled(chase, Ov)
    stated(Ov, chase, '$1,000', '2026-01-01')
    stated(Ov, chase, '$900', '2026-02-01')
    r22 = rec(Ov, '2026-02-01', '2026-02-28')
    check('Di22 (the negative discriminator): before 1,000, after 900 -> UNACCOUNTED -100, kept as it comes - not normalised, not absolute, no status',
          un(r22) == D('-100') and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r22)))
    corpus = [r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r13, r15, r16a, r16b, r18, r18b, r20a, r20b, r22, r23]
    check('Di19 (where the failure appears): no after term counted unless eligible by a P-ack dated >= at; no unaccounted value where any term is undetermined; no group with a successor two hops away; no float, no forbidden key',
          all(t['eligible'] and t['stated'] is not None and t['stated']['as_of'] >= r['at'] for r in corpus for t in r['after']['terms'] if t['eligible'])
          and all(r['unaccounted']['value'] is None for r in corpus if r['before']['value'] is None or r['after']['value'] is None)
          and all(r['unaccounted']['value'] == r['after']['value'] - r['before']['value'] for r in corpus if r['unaccounted']['value'] is not None)
          and not any(isinstance(v, float) for r in corpus for _, v in _walk(r)) and not any(k in FORBIDDEN_KEYS for r in corpus for k, _ in _walk(r)))

    print('\n7b. 7G-F3 inherited (Dc11): the acceptance\'s date is not the discharge\'s date\n')
    Oc = mint(db.Obligation, 'A loan acknowledged by document, accepted later.')
    entitled(chase, Oc)
    stated(Oc, chase, '$2,000', '2026-01-01')
    pc = pay(Oc, '$500', '2026-01-10', household, chase)
    _, rC = held('h-chase-jan-statement', chase)
    a_c = ack(chase, pc, '2026-01-15', reading=rC)                                                     # the reading: candidate, knowing
    evidence(a_c, utterance=utter('That line is Chase acknowledging the January payment.', '2026-03-05T09:00:00'))   # accepted in March
    stated(Oc, chase, '$1,500', '2026-02-05')                                                           # the February statement: the after side's P-ack (Di19)
    r_c = rec(Oc, '2026-02-01', '2026-02-28')
    check('Dc11 (7G-F3 inherited): the reading of Chase\'s statement + Rob\'s acceptance (uttered in March) on one claim dated 1/15 -> 7I reads 7G at two dates: discharged at the ACKNOWLEDGMENT\'s date (1/15), so the January payment is confirmed on both sides of `at` = 2/1 - the acceptance\'s utterance date is never the discharge\'s date; unaccounted 0',
          after_term(r_c, Oc)['confirmed'] == D('1500') and r_c['before']['terms'][0]['confirmed'] == D('1500') and un(r_c) == D('0'))

    print('\n7c. 7J-F4-F1 inherited (Sb11): the after side reads a P-ack that came by statement\n')
    Od = mint(db.Obligation, 'A loan whose February statement was read and accepted.')
    entitled(chase, Od)
    stated(Od, chase, '$2,000', '2026-01-01')
    pd_ = pay(Od, '$500', '2026-01-10', household, chase)
    ack(chase, pd_, '2026-01-15')
    _, rD = held('h-chase-feb-statement-read', chase)
    b_d = claim(db.BALANCE, reading=rD, as_of='2026-02-05', content='$1,500', subject_obligation_id=Od.id)
    r_d0 = rec(Od, '2026-02-01', '2026-02-28')
    evidence(b_d, utterance=utter('That is the February statement balance.', '2026-03-20T09:00:00'))    # accepted in March
    r_d = rec(Od, '2026-02-01', '2026-02-28')
    check('Sb11 (7I inherits): the February statement read alone -> the after side has no restated position; read + accepted (in March) -> the after side reads S = 1,500 dated 2/5 - the statement\'s date, never the acceptance\'s; unaccounted 0',
          after_term(r_d0, Od)['eligible'] is False and after_term(r_d, Od)['eligible'] is True
          and after_term(r_d, Od)['stated']['as_of'] == '2026-02-05' and after_term(r_d, Od)['confirmed'] == D('1500') and un(r_d) == D('0'))

    print('\n8. The dependency direction and the wiring guard\n')
    check('reconstruction reads reach (obligation_replaces, both directions) and remaining (7G) and nothing else that resolves, scores or allocates',
          {'reach', 'remaining'} <= calls_in(db.reconstruction)
          and not ({'level_consistency', 'chain_strength', 'aboutness', 'independence', 'parse_disputes', 'in_effect', 'derived_strength'} & calls_in(db.reconstruction)))
    check('the 7I wiring guard is executable (AST): reconstruction and _day_before call no session write method and construct no mapped class',
          writes_in(db.reconstruction) == [] and writes_in(db._day_before) == [])


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
