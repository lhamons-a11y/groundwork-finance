"""plans_in_effect / accumulator - the executable trace of `gw 2.0/CONSUMER_DERIVATIONS.md` pass 7J (ruled 2026-09-19,
s 7J.7) - the last consumer.

NO HOUSEHOLD-LEVEL ANSWER MANUFACTURED. plans_in_effect: 7F over the membership role, overlap a fact, the insurer's
eligibility stances a separate surface that neither overrides nor creates membership. accumulator: three axes kept
apart - the term (amount / none / unknown; none is not zero, unknown is not none), the insurer's stated accumulator
(Pl10, G), the derived sum constrained to the plan-year window, the insurer's own adjudication stances, expenses the
household asserted in respect of P (never from membership), each plan its own share; exempt listed, unadjudicated ->
undetermined naming it; dispute and remaining arithmetic consequences; NO met key; nothing stored.

What this slice can and cannot exercise
---------------------------------------
    Ju1  F20 / R7: two plans in effect -> both, an overlap fact, no primary                             EXERCISED
    Ju2  F5: the insurer's "never eligible" beside the household's membership, overriding nothing       EXERCISED
    Ju3  Pl12: the retroactive letter a candidate; membership changes only when the household asserts   EXERCISED
    Ju4  E24: an expense enters only by the asserted relation, never from membership                    EXERCISED
    Ju5  Pl10: stated 1,800 vs derived 1,650 -> dispute 150, a derived dispute                           EXERCISED
    Ju6  C1: no term -> unknown; remaining undetermined; never met                                       EXERCISED
    Ju7  C2: term none -> the rule does not exist; remaining not applicable - distinct from unknown      EXERCISED
    Ju8  C6: an exempt adjudication excluded and listed                                                  EXERCISED
    Ju9  an unadjudicated expense -> derived undetermined naming it; stated still reported               EXERCISED
    Ju10 the window: outside excluded and listed; no plan-year term -> undetermined                     EXERCISED
    Ju11 CC1: each plan its own share; nothing split or summed                                          EXERCISED
    Ju12 CC3: priority appears nowhere                                                                    EXERCISED
    Ju13 Pl2: family vs individual - separate terms, separate sums                                        EXERCISED
    Ju14 no Boolean: remaining -200 as it comes                                                          EXERCISED
    Ju15 the household's accumulator does not govern                                                     EXERCISED
    Ju16 as of d                                                                                          EXERCISED
    Ju17 surfaced not stored                                                                               EXERCISED
    Ju18 the null model                                                                                    EXERCISED
    Ju19 where the failure appears                                                                         EXERCISED
    the wiring guard: AST (session receivers) + a full row-content snapshot                               EXERCISED
    the term / adjudication / eligibility catalogues (9D), allocation, priority (E and F built: 9C, 9A)     NOT BUILT

Run:  python tests/test_accumulator_fixture.py
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


DECIDER_NAMES = ('plan_at', 'primary_plan', 'current_plan_of', 'is_eligible', 'is_covered', 'covered', 'deductible_met', 'met',
                 'accumulator_cache', 'plans_cache', 'resolve_overlap', 'household_accumulator', 'apportion_expense', 'eligibility_of',
                 'membership_from_stance', 'plan_for_expense')
FORBIDDEN_KEYS = ('met', 'is_met', 'covered', 'eligible', 'primary', 'winner', 'preferred', 'chosen', 'priority', 'status',
                  'household', 'merged', 'average', 'confidence', 'apportioned', 'share')


def _role(subject, obj):
    return {'subject': (subject,), 'object': (obj,), 'symmetric': False, 'reading_establishes': False, 'relational_knowing': True, 'role': True}


def _boundary(of, which, subject, obj):
    r = _role(subject, obj)
    r.update({'boundary': which, 'of': of})
    return r


STAND_INS = {}   # empty since item 9 pass 9C built E's expense_in_respect_of_plan: every relation and role this fixture reads is ruled
CATALOGUE = {'occurred_on': 'occurred_on', 'insurer_of': 'insurer_of', 'under_plan': 'under_plan', 'plan_insurer': 'insurer_of_plan',
             'eligibility': 'eligibility', 'deductible': 'deductible', 'individual_deductible': 'individual_deductible', 'plan_year': 'plan_year',
             'deductible_applied': 'deductible_applied', 'individual_deductible_applied': 'individual_deductible_applied', 'expense_in_respect_of_plan': 'expense_in_respect_of_plan',   # 9D-iii F1: two kinds by shape
             'applied_to_deductible': 'applied_to_deductible', 'incurred_by': 'incurred_by'}


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_rj_')
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
    check('the stand-in role and relation kinds are removed; the registry is as shipped; no term, adjudication or eligibility kind was registered',
          db.RULED_KINDS == shipped and True)   # every kind this fixture reads is ruled: roles 9B, E's relation 9C, stances and terms 9D-ii / 9D-iii, values 9D-iv)
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}, 
               }   # billed / PR / plan_paid / applied_to_deductible: 9D-ii; amount / occurred_on: 9D-iv; determination: 9D-v - every kind this fixture reads is ruled, no map entry
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



    def pie(person, d):
        return db.plans_in_effect(s, person, d, CATALOGUE, KNOWING)

    def acc(P, d, person=None):
        return db.accumulator(s, P, d, CATALOGUE, KNOWING, person=person)

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

    def role_on(kind, party, obj_slot, obj, began='2026-01-01', utterance=None, reading=None):
        # 9B: a beginning where the role has boundaries (under_plan); a holds stance where it is holds-only
        k = f'{kind}_began' if f'{kind}_began' in db.RULED_KINDS else kind
        return claim(k, utterance=utterance if (utterance or reading) else utter(f'{kind} {began}'), reading=reading,
                     as_of=began, subject_party_id=party.id, **{obj_slot: obj.id})

    def term(P, kind, content, as_of='2026-01-01', by=None):
        return claim(kind, utterance=utter(content, origin=by), as_of=as_of, content=content, subject_plan_id=P.id)

    def plan_year(P, start, end):
        return claim(db.PLAN_YEAR, utterance=utter('plan year'), as_of=start, content=end, subject_plan_id=P.id)

    def applied_stance(P, by, amount, as_of, person=None):
        # 9D-iii F1: the individual figure is its own kind (person, P), the family figure has no object
        return claim(db.INDIVIDUAL_DEDUCTIBLE_APPLIED if person is not None else db.DEDUCTIBLE_APPLIED, utterance=utter(amount, origin=by), as_of=as_of,
                     content=amount, subject_plan_id=P.id, **({'object_party_id': person.id} if person is not None else {}))

    def expense_under(P, name, on, insurer, incurred=None):
        X = mint(db.Expense, name)
        claim(db.OCCURRED_ON, utterance=utter(on), as_of=on, subject_expense_id=X.id)
        role_on(db.INSURER_OF, insurer, 'object_expense_id', X)
        claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('on the plan'), subject_expense_id=X.id, object_plan_id=P.id)
        if incurred is not None:
            claim(db.INCURRED_BY, utterance=utter('incurred by'), subject_party_id=incurred.id, object_expense_id=X.id)
        return X

    def adjudicate(X, by, content, as_of):
        return claim(db.APPLIED_TO_DEDUCTIBLE, utterance=utter(content, origin=by), as_of=as_of, content=content, subject_expense_id=X.id)

    def eligibility(person, P, by, content, as_of, reading=None):
        return claim(db.ELIGIBILITY, utterance=None if reading else utter(content, origin=by), reading=reading, as_of=as_of, content=content,
                     subject_party_id=person.id, object_plan_id=P.id)

    aetna = mint(db.Party, 'Aetna.')
    cigna = mint(db.Party, 'Cigna.')
    P1 = mint(db.Plan, "Kim's employer plan.")
    P2 = mint(db.Plan, "Rob's marketplace plan.")
    role_on(db.INSURER_OF_PLAN, aetna, 'object_plan_id', P1)
    role_on(db.INSURER_OF_PLAN, cigna, 'object_plan_id', P2)

    print('\n1. Absences - no plan_at / primary / eligible / covered / met / cache helper\n')
    check('no plan_at, primary, eligibility, coverage, met, household-accumulator, apportion or cache helper exists on the module',
          not any(hasattr(db, n) for n in DECIDER_NAMES))
    check('the three term states are named (amount / none / unknown) and the two adjudication conditions (exempt / unadjudicated)',
          (db.TERM_AMOUNT, db.TERM_NONE, db.TERM_UNKNOWN, db.ADJ_EXEMPT, db.ADJ_UNADJUDICATED) == ('amount', 'none', 'unknown', 'exempt', 'unadjudicated'))
    check('refusals: a catalogue missing a kind; a membership kind no boundary is bound to; a non-Party; a non-Plan',
          'eligibility' in (_refused(db.plans_in_effect, s, kim_party, '2026-08-01', {k: v for k, v in CATALOGUE.items() if k != 'eligibility'}, KNOWING) or '')
          and 'not a ruled role' in (_refused(db.plans_in_effect, s, kim_party, '2026-08-01', dict(CATALOGUE, under_plan='deductible'), KNOWING) or '')
          and _refused(db.plans_in_effect, s, P1, '2026-08-01', CATALOGUE, KNOWING) is not None
          and _refused(db.accumulator, s, kim_party, '2026-08-01', CATALOGUE, KNOWING) is not None)

    print('\n2. Ju1 / Ju2 / Ju3 - plans in effect: overlap a fact; the insurer\'s stances beside; the letter a candidate\n')
    role_on(db.UNDER_PLAN, kim_party, 'object_plan_id', P1, began='2026-01-01')
    role_on(db.UNDER_PLAN, kim_party, 'object_plan_id', P2, began='2026-07-01')
    r1 = pie(kim_party, '2026-08-01')
    check('Ju1 (F20 / R7): Kim under P1 (1/1) and P2 (7/1) -> August: BOTH in effect; overlap = [P1, P2] - a fact; no primary / winner key; G named on each',
          sorted(r1['in_effect']) == sorted([P1.id, P2.id]) and sorted(r1['overlap']) == sorted([P1.id, P2.id])
          and r1['plans'][P1.id]['governing'][0]['sort'] == 'began' and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r1)))
    eligibility(kim_party, P1, aetna, 'never eligible', '2026-02-01')
    r2 = pie(kim_party, '2026-08-01')
    check('Ju2 (F5): Aetna\'s "never eligible" (dated, by the plan\'s insurer in effect) is listed beside P1; membership STILL in effect; nothing derived, nothing overridden',
          r2['plans'][P1.id]['answer'] == db.EFFECT_IN and [(e['content'], e['plan_insurer'], e['state']) for e in r2['plans'][P1.id]['eligibility']] == [('never eligible', db.EFFECT_IN, db.CLAIM_ESTABLISHED)]
          and sorted(r2['in_effect']) == sorted([P1.id, P2.id]))
    _, rL = held('h-aetna-letter', aetna)
    eligibility(kim_party, P1, aetna, 'terminated retroactively to 6/30', '2026-06-30', reading=rL)
    claim(db.UNDER_PLAN_ENDED, reading=rL, as_of='2026-06-30', subject_party_id=kim_party.id, object_plan_id=P1.id)   # the letter, read: a candidate ending
    r3a = pie(kim_party, '2026-08-01')
    check('Ju3 (Pl12): Aetna\'s letter read -> the eligibility stance a CANDIDATE and the ending a candidate stance; membership UNCHANGED (in effect) - the letter does not silently terminate',
          r3a['plans'][P1.id]['answer'] == db.EFFECT_IN and any(e['state'] == db.CLAIM_CANDIDATE for e in r3a['plans'][P1.id]['eligibility'])
          and any(st['state'] == db.CLAIM_CANDIDATE and st['sort'] == 'ended' for st in r3a['plans'][P1.id]['stances']))
    claim(db.UNDER_PLAN_ENDED, utterance=utter('ended 6/30'), as_of='2026-06-30', subject_party_id=kim_party.id, object_plan_id=P1.id)   # Rob asserts the ending
    r3b = pie(kim_party, '2026-08-01')
    check('Ju3: once the household asserts the ending, P1 is NOT in effect in August (7F); only P2 remains; no overlap',
          r3b['plans'][P1.id]['answer'] == db.EFFECT_NOT and r3b['in_effect'] == [P2.id] and r3b['overlap'] == [])
    P3 = mint(db.Plan, 'A plan the insurer names, the household never asserted.')
    role_on(db.INSURER_OF_PLAN, aetna, 'object_plan_id', P3)
    eligibility(kim_party, P3, aetna, 'enrolled', '2026-03-01')
    r3c = pie(kim_party, '2026-08-01')
    check('Ju3: the insurer\'s "enrolled" on a plan the household never asserted -> listed APART under eligibility_only with no membership answer at all; not among the plans, not in effect - a stance creates no membership and no status',
          P3.id in r3c['eligibility_only'] and P3.id not in r3c['plans'] and P3.id not in r3c['in_effect']
          and [e['content'] for e in r3c['eligibility_only'][P3.id]] == ['enrolled'])

    print('\n3. Ju5 / Ju6 / Ju7 / Ju14 / Ju15 - the accumulator: three axes; the term\'s three states; no met\n')
    Q = mint(db.Plan, 'The accumulator plan.')
    role_on(db.INSURER_OF_PLAN, aetna, 'object_plan_id', Q)
    plan_year(Q, '2026-01-01', '2026-12-31')
    x1 = expense_under(Q, 'Visit 1', '2026-01-20', aetna, incurred=kim_party)
    x2 = expense_under(Q, 'Visit 2', '2026-02-10', aetna, incurred=kim_party)
    x3 = expense_under(Q, 'Visit 3', '2026-03-05', aetna, incurred=household)
    adjudicate(x1, aetna, '$800', '2026-02-01')
    adjudicate(x2, aetna, '$500', '2026-02-20')
    adjudicate(x3, aetna, '$350', '2026-03-15')
    r6 = acc(Q, '2026-03-31')
    check('Ju6 (C1): no deductible term -> term UNKNOWN ("we do not have the deductible"); derived 1,650 with its basis; REMAINING UNDETERMINED with the reason; never met; no met key',
          r6['term']['state'] == db.TERM_UNKNOWN and r6['derived']['value'] == D('1650') and r6['remaining']['value'] is None
          and 'no established deductible term' in r6['remaining']['reason'] and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r6)))
    term(Q, 'deductible', '$3,000')
    applied_stance(Q, aetna, '$1,800', '2026-03-01')
    r5 = acc(Q, '2026-03-31')
    check('Ju5 (Pl10): the insurer\'s portal says 1,800 applied (3/1); the adjudications sum to 1,650 -> STATED 1,800 (Aetna, named), DERIVED 1,650 (basis x1, x2, x3), DISPUTE 150 - a number with its terms; neither replaces the other',
          r5['stated']['governing']['value'] == D('1800') and r5['stated']['governing']['asserter'] == aetna.id and r5['derived']['value'] == D('1650')
          and sorted(x for x, _, _ in r5['derived']['basis']) == sorted([x1.id, x2.id, x3.id]) and r5['dispute']['value'] == D('150'))
    check('Ju5: term 3,000 -> remaining = term - derived = 1,350 - the one ruled remainder; no term - stated figure, no met',
          r5['term'] == dict(r5['term'], state=db.TERM_AMOUNT, value=D('3000')) and r5['remaining']['value'] == D('1350')
          and 'remaining_from_stated' not in r5 and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r5)))
    H = mint(db.Plan, 'The HMO with no deductible.')
    role_on(db.INSURER_OF_PLAN, cigna, 'object_plan_id', H)
    plan_year(H, '2026-01-01', '2026-12-31')
    term(H, 'deductible', 'none')
    r7 = acc(H, '2026-03-31')
    check('Ju7 (C2): the term says none -> term NONE ("the rule does not exist"); remaining NOT APPLICABLE - an answer, distinct from Ju6\'s refusal; derived 0 over no expenses is arithmetic, not met',
          r7['term']['state'] == db.TERM_NONE and 'not applicable' in r7['remaining']['reason'] and r7['remaining']['value'] is None
          and r7['derived']['value'] == D('0') and r7['remaining']['reason'] != r6['remaining']['reason'])
    x4 = expense_under(Q, 'Visit 4', '2026-04-02', aetna, incurred=kim_party)
    adjudicate(x4, aetna, '$1,550', '2026-04-10')
    r14 = acc(Q, '2026-04-30')
    check('Ju14 (no Boolean): applied 3,200 against a 3,000 term -> REMAINING -200, reported as it comes; no met key',
          r14['derived']['value'] == D('3200') and r14['remaining']['value'] == D('-200') and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r14)))
    applied_stance(Q, household, '$2,000', '2026-04-15')                                # Rob: "we've had $2,000 applied"
    r15 = acc(Q, '2026-04-30')
    check('Ju15: the household\'s accumulator claim is listed and does NOT govern (Rob not in effect as the plan\'s insurer); stated remains Aetna\'s 1,800',
          [c['qualifies'] for c in r15['stated']['claims'] if c['asserter'] == household.id] == [False] and r15['stated']['governing']['value'] == D('1800'))

    print('\n4. Ju8 / Ju9 / Ju10 / Ju4 - exempt; unadjudicated; the window; never from membership\n')
    x5 = expense_under(Q, 'Preventive visit', '2026-05-01', aetna, incurred=kim_party)
    adjudicate(x5, aetna, 'none', '2026-05-10')
    r8 = acc(Q, '2026-05-31')
    check('Ju8 (C6): the preventive visit adjudicated "none" -> EXEMPT - excluded, listed; derived still determined (3,200); not unknown, not silently zero',
          [x for x, _ in r8['derived']['exempt']] == [x5.id] and r8['derived']['value'] == D('3200'))
    x6 = expense_under(Q, 'Pending claim', '2026-05-15', aetna, incurred=kim_party)
    r9 = acc(Q, '2026-05-31')
    check('Ju9: an expense in respect of Q in the window with NO adjudication -> UNADJUDICATED, listed; derived UNDETERMINED naming it; stated still reported (1,800); dispute and remaining undetermined',
          r9['derived']['unadjudicated'] == [x6.id] and r9['derived']['value'] is None and f'expense {x6.id}' in r9['derived']['reason']
          and r9['stated']['governing']['value'] == D('1800') and r9['dispute']['value'] is None and r9['remaining']['value'] is None)
    adjudicate(x6, aetna, '$0', '2026-06-01')
    x7 = expense_under(Q, 'Last December', '2025-12-15', aetna, incurred=kim_party)
    adjudicate(x7, aetna, '$300', '2025-12-20')
    r10 = acc(Q, '2026-06-30')
    check('Ju10 (the window): the December expense is OUTSIDE the plan year - excluded, listed with its date; derived 3,200 (x6 adjudicated $0 counts as zero, an answer)',
          r10['derived']['outside_window'] == [(x7.id, '2025-12-15')] and r10['derived']['value'] == D('3200'))
    NW = mint(db.Plan, 'No plan-year term.')
    role_on(db.INSURER_OF_PLAN, aetna, 'object_plan_id', NW)
    term(NW, 'deductible', '$1,000')
    xw = expense_under(NW, 'Some visit', '2026-02-01', aetna)
    adjudicate(xw, aetna, '$100', '2026-02-10')
    r10b = acc(NW, '2026-03-31')
    check('Ju10: no plan-year term -> derived UNDETERMINED "no plan year term containing d" - no calendar assumption',
          r10b['window']['start'] is None and r10b['derived']['value'] is None and 'no plan year term' in r10b['derived']['reason'])
    x8 = mint(db.Expense, "Kim's visit nobody tied to Q.")
    claim(db.OCCURRED_ON, utterance=utter('2026-06-01'), as_of='2026-06-01', subject_expense_id=x8.id)
    role_on(db.INSURER_OF, aetna, 'object_expense_id', x8)
    claim(db.INCURRED_BY, utterance=utter('incurred by Kim'), subject_party_id=kim_party.id, object_expense_id=x8.id)
    adjudicate(x8, aetna, '$999', '2026-06-05')
    r4 = acc(Q, '2026-06-30')
    check('Ju4 (E24): Kim is under Q and x8 is Kim\'s, adjudicated by Aetna - but nothing asserts x8 in respect of Q -> x8 is NOT in Q\'s accumulator (derived still 3,200)',
          x8.id not in [x for x, _, _ in r4['derived']['basis']] and r4['derived']['value'] == D('3200'))

    print('\n5. Ju11 / Ju12 / Ju13 - concurrency: each plan its own share; priority nowhere; family vs individual\n')
    A, B = mint(db.Plan, 'Plan A (medical).'), mint(db.Plan, 'Plan B (secondary).')
    role_on(db.INSURER_OF_PLAN, aetna, 'object_plan_id', A)
    role_on(db.INSURER_OF_PLAN, cigna, 'object_plan_id', B)
    for P in (A, B):
        plan_year(P, '2026-01-01', '2026-12-31')
        term(P, 'deductible', '$1,000')
    xc = mint(db.Expense, 'The concurrent visit.')
    claim(db.OCCURRED_ON, utterance=utter('2026-08-05'), as_of='2026-08-05', subject_expense_id=xc.id)
    role_on(db.INSURER_OF, aetna, 'object_expense_id', xc)
    role_on(db.INSURER_OF, cigna, 'object_expense_id', xc)
    for P in (A, B):
        claim(db.EXPENSE_IN_RESPECT_OF_PLAN, utterance=utter('on both'), subject_expense_id=xc.id, object_plan_id=P.id)
    adjudicate(xc, aetna, '$400', '2026-08-20')
    adjudicate(xc, cigna, '$150', '2026-08-25')
    rA, rB = acc(A, '2026-08-31'), acc(B, '2026-08-31')
    check('Ju11 (CC1): each plan derives only from adjudication stances by ITS insurer - A: 400 (Aetna), B: 150 (Cigna); nothing split, nothing summed across plans; no apportioned / share key',
          rA['derived']['value'] == D('400') and rB['derived']['value'] == D('150')
          and not any(k in FORBIDDEN_KEYS for r in (rA, rB) for k, _ in _walk(r)))
    check('Ju12 (CC3): nothing about priority appears in either report',
          not any(k == 'priority' or (isinstance(v, str) and 'priority' in v.lower()) for r in (rA, rB) for k, v in _walk(r)))
    F = mint(db.Plan, 'The family plan (Pl2).')
    role_on(db.INSURER_OF_PLAN, aetna, 'object_plan_id', F)
    plan_year(F, '2026-01-01', '2026-12-31')
    term(F, 'deductible', '$6,000')
    term(F, 'individual_deductible', '$3,000')
    fk = expense_under(F, "Kim's", '2026-03-01', aetna, incurred=kim_party)
    fr = expense_under(F, "Rob's", '2026-03-02', aetna, incurred=household)
    adjudicate(fk, aetna, '$2,000', '2026-03-10')
    adjudicate(fr, aetna, '$1,500', '2026-03-11')
    applied_stance(F, aetna, '$3,500', '2026-03-15')
    applied_stance(F, aetna, '$2,000', '2026-03-15', person=kim_party)
    rF, rK = acc(F, '2026-03-31'), acc(F, '2026-03-31', person=kim_party)
    check('Ju13 (Pl2): family: term 6,000, derived 3,500, stated 3,500, remaining 2,500; Kim individual: term 3,000, derived 2,000 (Kim\'s expenses only), stated 2,000 (the (Kim, F) stance), remaining 1,000 - separate terms, separate sums, no household figure',
          rF['term']['value'] == D('6000') and rF['derived']['value'] == D('3500') and rF['stated']['governing']['value'] == D('3500') and rF['remaining']['value'] == D('2500')
          and rK['term']['value'] == D('3000') and rK['derived']['value'] == D('2000') and rK['stated']['governing']['value'] == D('2000') and rK['remaining']['value'] == D('1000')
          and rK['person'] == kim_party.id)

    print('\n6. Ju16 / Ju17 / Ju18 / Ju19 - as of d; surfaced not stored; the null model; where the failure appears\n')
    check('Ju16 (as of d): asked 1/31, Q\'s term (dated 1/1) counts but no adjudication does yet (x1 adjudicated 2/1) -> x1 unadjudicated -> derived undetermined; asked 2/28 x1 and x2 count; created_at never read',
          acc(Q, '2026-01-31')['derived']['value'] is None and x1.id in acc(Q, '2026-01-31')['derived']['unadjudicated']
          and acc(Q, '2026-02-28')['derived']['value'] == D('1300')
          and 'created_at' not in __import__('inspect').getsource(db.accumulator) and 'created_at' not in __import__('inspect').getsource(db.plans_in_effect))
    before = snapshot()
    acc(Q, '2026-06-30')
    pie(kim_party, '2026-08-01')
    check('Ju17: reading both reports wrote nothing; no accumulator / met / eligible / covered column on any 2.0 table',
          snapshot() == before
          and not any(any(w in c.name for w in ('accumulator', 'met', 'eligible', 'covered', 'deductible')) for cls in
                      (db.Proposition, db.Party, db.Obligation, db.Payment, db.Expense, db.Plan, db.Artefact, db.Reading, db.Utterance, db.EvidentiaryRelationship)
                      for c in cls.__table__.columns))
    N = mint(db.Plan, 'Null model.')
    role_on(db.INSURER_OF_PLAN, aetna, 'object_plan_id', N)
    plan_year(N, '2026-01-01', '2026-12-31')
    term(N, 'deductible', '$1,000')
    n1 = expense_under(N, 'n1', '2026-02-01', aetna)
    n2 = expense_under(N, 'n2', '2026-02-02', aetna)
    adjudicate(n1, aetna, '$300', '2026-02-10')
    a_n2 = adjudicate(n2, aetna, '$200', '2026-02-11')
    applied_stance(N, aetna, '$500', '2026-02-15')
    rN = acc(N, '2026-02-28')
    check('Ju18 (null model): every expense adjudicated, stated = derived -> DISPUTE 0; remaining 500',
          rN['dispute']['value'] == D('0') and rN['remaining']['value'] == D('500'))
    adjudicate(n2, aetna, '$300', '2026-02-20')                                        # a later adjudication supersedes under G
    rN2 = acc(N, '2026-02-28')
    check('Ju18 (null model): one adjudication changed by 100 (a later stance under G) -> dispute exactly -100, remaining exactly 400',
          rN2['dispute']['value'] == D('-100') and rN2['remaining']['value'] == D('400'))
    corpus = [r5, r6, r7, r8, r9, r10, r10b, r14, r15, r4, rA, rB, rF, rK, rN, rN2]
    check('Ju19 (none vs unknown, pinned): term none -> value None and remaining "not applicable"; term unknown -> value None and remaining "undetermined"; neither is zero, neither permits a remaining value, and the two reasons differ',
          r7['term']['state'] == db.TERM_NONE and r7['term']['value'] is None and r7['remaining']['value'] is None and r7['remaining']['reason'].startswith('not applicable')
          and r6['term']['state'] == db.TERM_UNKNOWN and r6['term']['value'] is None and r6['remaining']['value'] is None and r6['remaining']['reason'].startswith('undetermined')
          and all(r['term']['value'] is None and r['remaining']['value'] is None for r in corpus if r['term']['state'] in (db.TERM_NONE, db.TERM_UNKNOWN)))
    check('Ju19 (where the failure appears): no remaining value without a term amount; no derived value with an unadjudicated expense or without a window; no basis entry from an expense not asserted in respect of the plan; no float; no forbidden key',
          all(r['term']['state'] == db.TERM_AMOUNT for r in corpus if r['remaining']['value'] is not None)
          and all(not r['derived']['unadjudicated'] and r['window']['start'] is not None for r in corpus if r['derived']['value'] is not None)
          and all(r['remaining']['value'] == r['term']['value'] - r['derived']['value'] for r in corpus if r['remaining']['value'] is not None)
          and not any(isinstance(v, float) for r in corpus for _, v in _walk(r)) and not any(k in FORBIDDEN_KEYS for r in corpus for k, _ in _walk(r)))

    print('\n7. The dependency direction and the wiring guard\n')
    check('plans_in_effect reads in_effect (7F) and the eligibility claims; accumulator reads reach and the claims under the catalogue; neither calls another consumer',
          'in_effect' in calls_in(db.plans_in_effect) and 'reach' in calls_in(db.accumulator)
          and not ({'remaining', 'reconciliation', 'reconstruction', 'level_consistency', 'chain_strength', 'aboutness', 'independence'} & (calls_in(db.plans_in_effect) | calls_in(db.accumulator))))
    check('the 7J wiring guard is executable (AST): both functions and their helpers call no session write method and construct no mapped class',
          all(writes_in(f) == [] for f in (db.plans_in_effect, db.accumulator, db._claim_entries, db._require_role)))


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
