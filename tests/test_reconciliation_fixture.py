"""reconciliation - the executable trace of `gw 2.0/CONSUMER_DERIVATIONS.md` pass 7H (ruled 2026-09-19, s 7H.8).

RECONCILIATION EQUATES NOTHING AND DETERMINES NOTHING. The sides as dated positions of parties in effect in the roles
(stand-ins); membership by an established obligation_in_respect_of ground; funding by an established
payment_in_respect_of ground THEN direction relative to the provider; the comparison a number only one-to-one; the
unresolved amount = the gross charge less every established funding event dated <= d, acknowledgment-independent;
determinations as dated claims with content one of four names, current by G per party's series and conflict across
parties; nothing inferred, nothing classified, nothing written.

What this slice can and cannot exercise
---------------------------------------
    Rc1  C6: billed 1,300 / PR 412 / balance 450 -> difference 38; nothing equated                        EXERCISED
    Rc2  the $650: charge 1,200 - 250 - 300 -> unresolved 650, classified by nothing                        EXERCISED
    Rc3  D12: user_paid_cash claimed -> current; the number does not move                                  EXERCISED
    Rc4  superseded within one party's series, never overwritten                                           EXERCISED
    Rc5  unpaid is not pending_claim - mechanical                                                           EXERCISED
    Rc6  C7: a denial kind is not read                                                                     EXERCISED
    Rc7  C5: the obligation in respect of several expenses -> no comparison                                EXERCISED
    Rc8  D'3: several obligations -> no comparison, no sum                                                 EXERCISED
    Rc9  no obligation -> no comparison; the sides still reported                                          EXERCISED
    Rc10 two PR at one date -> conflict, no governing PR                                                   EXERCISED
    Rc11 PR history -> the later governs, named                                                            EXERCISED
    Rc12 the household's PR figure does not govern                                                         EXERCISED
    Rc13 direction on X: any payer to the provider funds; the provider paying is money back               EXERCISED
    Rc14 a candidate relation is not a context; a payment to the provider without membership absent       EXERCISED
    Rc15 a retracted determination exposes the prior; cross-party disagreement -> conflict                 EXERCISED
    Rc16 as of d                                                                                            EXERCISED
    Rc17 surfaced not stored                                                                                EXERCISED
    Rc18 the null model: funding = charge -> 0; one event removed -> its amount; positions equal -> 0      EXERCISED
    Rc19 zero is not a determination; no current without a claim                                          EXERCISED
    Rc20 no classification word anywhere                                                                   EXERCISED
    Rc21 where the failure appears                                                                          EXERCISED
    the wiring guard: AST (session receivers) + a full row-content snapshot                                EXERCISED
    the role / value / determination catalogues (stand-ins here), a denial kind, tax, 7J                    NOT BUILT

Run:  python tests/test_reconciliation_fixture.py
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


DECIDER_NAMES = ('matches', 'reconciled', 'reconcile', 'corresponding_amount', 'infer_determination', 'determine', 'mark_paid',
                 'deductible', 'qualifying', 'is_paid', 'settle', 'resolve_determination', 'current_determination',
                 'reconciliation_cache', 'apportion', 'allocate_pr')
FORBIDDEN_KEYS = ('matches', 'match', 'reconciled', 'error', 'discrepancy', 'corresponding', 'verdict', 'deductible', 'qualifying',
                  'reimbursed', 'taxable', 'paid', 'status', 'share', 'allocation', 'apportioned', 'denied', 'denial', 'confidence',
                  'winner', 'preferred', 'resolved')


def _role(subject, obj):
    return {'subject': (subject,), 'object': (obj,), 'symmetric': False, 'reading_establishes': False, 'relational_knowing': True, 'role': True}


def _boundary(of, which, subject, obj):
    r = _role(subject, obj)
    r.update({'boundary': which, 'of': of})
    return r


STAND_INS = {}                                             # 9B: every role this fixture used is now a ruled kind
CATALOGUE = {'acknowledgment': 'acknowledged', 'entitled_party': 'entitled_party_of', 'balance': 'balance',
             'payment_amount': 'amount', 'occurred_on': 'occurred_on', 'paid_by': 'paid_by', 'paid_to': 'paid_to',
             'billed': 'billed', 'patient_responsibility': 'patient_responsibility', 'plan_paid': 'plan_paid',
             'determination': 'determination', 'provider_of': 'provider_of', 'insurer_of': 'insurer_of'}


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_rh_')
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
    check('the stand-in role kinds are removed; the registry is as shipped; no value, determination or acknowledgment kind was registered',
          db.RULED_KINDS == shipped and not any(k in shipped for k in ('acknowledged', 'balance', 'amount', 'occurred_on', 'billed', 'patient_responsibility', 'plan_paid', 'determination')))   # paid_by / paid_to: ruled roles since 9B
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}, 'acknowledged': {'institution'}, 'balance': {'institution'},
               'amount': {'person', 'institution'}, 'occurred_on': {'person', 'institution'},
               'billed': {'institution'}, 'patient_responsibility': {'institution'}, 'plan_paid': {'institution'}, 'determination': {'person', 'institution'}}
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
        claim('amount', utterance=utter(amount, origin=amount_by), content=amount, subject_payment_id=p.id)
        claim('occurred_on', utterance=utter(on), as_of=on, subject_payment_id=p.id)
        if payer is not None:
            claim('paid_by', utterance=utter('paid by'), as_of=on, subject_party_id=payer.id, object_payment_id=p.id)
        if payee is not None:
            claim('paid_to', utterance=utter('paid to'), as_of=on, subject_party_id=payee.id, object_payment_id=p.id)
        if attach:
            claim(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, utterance=utter('toward it'), subject_payment_id=p.id, object_obligation_id=O.id)
        return p

    def ack(by, p, as_of, origin=None, reading=None):
        return claim('acknowledged', utterance=None if reading else utter(f'ack {as_of}', origin=origin or by), reading=reading,
                     as_of=as_of, subject_party_id=by.id, object_payment_id=p.id)

    def stated(O, by, amount, as_of, origin=None):
        return claim('balance', utterance=utter(amount, origin=origin or by), as_of=as_of, content=amount, subject_obligation_id=O.id)


    def rc(X, d):
        return db.reconciliation(s, X, d, CATALOGUE, KNOWING)

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

    def role(kind, party, X, began='2026-01-01'):
        # 9B: provider_of and insurer_of are holds-only roles - a holds stance at the date, not a beginning
        claim(kind, utterance=utter(f'{kind} {began}'), as_of=began, subject_party_id=party.id, object_expense_id=X.id)

    def xstance(kind, X, by, amount, as_of, origin=None):
        return claim(kind, utterance=utter(amount, origin=origin or by), as_of=as_of, content=amount, subject_expense_id=X.id)

    def in_respect(O, X, utterance=None, reading=None):
        return claim(db.OBLIGATION_IN_RESPECT_OF, utterance=utterance if (utterance or reading) else utter('in respect of'), reading=reading,
                     subject_obligation_id=O.id, object_expense_id=X.id)

    def fund(X, amount, on, payer, payee, member=True, attach_to=None):
        p = pay(attach_to, amount, on, payer, payee, attach=attach_to is not None)
        if member:
            claim(db.PAYMENT_IN_RESPECT_OF, utterance=utter('for the visit'), subject_payment_id=p.id, object_expense_id=X.id)
        return p

    def determine(X, by, name, as_of, utterance=None, reading=None):
        return claim('determination', utterance=utterance if (utterance or reading) else utter(name, origin=by), reading=reading,
                     as_of=as_of, content=name, subject_expense_id=X.id)

    def visit(name, provider, insurer, billed=None, pr=None, billed_on='2026-01-01', pr_on='2026-01-15'):
        X = mint(db.Expense, name)
        role(db.PROVIDER_OF, provider, X)
        role(db.INSURER_OF, insurer, X)
        if billed:
            xstance('billed', X, provider, billed, billed_on)
        if pr:
            xstance('patient_responsibility', X, insurer, pr, pr_on)
        return X

    def bill(X, provider, amount, as_of='2026-02-01'):
        O = mint(db.Obligation, f'The bill for {X.id}.')
        entitled(provider, O)
        stated(O, provider, amount, as_of)
        in_respect(O, X)
        return O

    mercy = mint(db.Party, 'Mercy Hospital.')
    aetna = mint(db.Party, 'Aetna.')
    radiology = mint(db.Party, 'The radiologist.')
    hsa = mint(db.Party, 'The HSA administrator.')

    print('\n1. Absences - no matches / reconcile / corresponding amount / determine / classify helper\n')
    check('no matches, reconciled, corresponding-amount, infer-determination, mark-paid, deductible, apportion or cache helper exists on the module',
          not any(hasattr(db, n) for n in DECIDER_NAMES))
    check('the four determination names are the closed vocabulary; the reconciliation catalogue names are the closed list',
          db.DETERMINATION_NAMES == ('provider_adjustment', 'user_paid_cash', 'unpaid', 'pending_claim') and set(db.RECONCILIATION_KINDS) <= set(CATALOGUE))
    check('refusals: a catalogue missing a kind; a provider role no boundary is bound to; a non-Expense',
          'billed' in (_refused(db.reconciliation, s, mint(db.Expense, 'x'), '2026-03-31', {k: v for k, v in CATALOGUE.items() if k != 'billed'}, KNOWING) or '')
          and 'not a ruled role' in (_refused(db.reconciliation, s, mint(db.Expense, 'y'), '2026-03-31', dict(CATALOGUE, provider_of='balance'), KNOWING) or '')
          and _refused(db.reconciliation, s, mercy, '2026-03-31', CATALOGUE, KNOWING) is not None)

    print('\n2. Rc1 / Rc9 / Rc12 - the sides side by side; the comparison as a number; the household figure does not govern\n')
    X1 = visit('The ER visit (C6).', mercy, aetna, billed='$1,300', pr='$412')
    r9 = rc(X1, '2026-03-31')
    check('Rc9: billed and PR reported (governing named, by party and date); no obligation -> comparison undetermined "no obligation in respect of the expense"; unresolved = 1,300 (no funding)',
          r9['stances']['billed']['governing']['value'] == D('1300') and r9['stances']['billed']['governing']['asserter'] == mercy.id
          and r9['stances']['patient_responsibility']['governing']['value'] == D('412') and r9['comparison']['difference'] is None
          and r9['comparison']['reason'] == 'no obligation in respect of the expense' and r9['unresolved']['value'] == D('1300'))
    O1 = bill(X1, mercy, '$450')
    r1 = rc(X1, '2026-03-31')
    check('Rc1 (C6): Mercy billed 1,300 (X), Aetna PR 412 (X), Mercy\'s statement 450 (O), O in respect of X -> DIFFERENCE 450 - 412 = 38 with both terms named; O\'s figures 7G\'s and unchanged; no matches / error / corresponding key',
          r1['comparison']['difference'] == D('38') and r1['comparison']['obligation'] == O1.id and r1['comparison']['stated']['value'] == D('450')
          and r1['obligations'][0]['stated']['value'] == D('450') and r1['obligations'][0]['confirmed'] == D('450')
          and db.remaining(s, O1, '2026-03-31', CATALOGUE, KNOWING)['stated']['governing']['value'] == D('450')
          and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r1)))
    xstance('patient_responsibility', X1, household, '$400', '2026-01-20')                  # Rob: "the EOB said $400"
    r12 = rc(X1, '2026-03-31')
    check('Rc12: Rob\'s PR figure (a party not in effect as insurer) is listed and does NOT govern; the difference stays 38',
          [c['qualifies'] for c in r12['stances']['patient_responsibility']['claims'] if c['asserter'] == household.id] == [False]
          and r12['comparison']['difference'] == D('38'))

    print('\n3. Rc2 / Rc13 / Rc14 - the unresolved amount; direction relative to the provider; membership first\n')
    X2 = visit('The visit (the $650).', mercy, aetna, billed='$1,200', pr='$650')
    p2a = fund(X2, '$250', '2026-02-01', aetna, mercy)                                       # the insurer's payment, in respect of X
    p2b = fund(X2, '$300', '2026-02-05', household, mercy)                                   # the household's
    r2 = rc(X2, '2026-03-31')
    check('Rc2 (the $650): charge 1,200 - insurer 250 - user 300 -> UNRESOLVED 650 with its terms; classified by nothing; the acknowledged view absent (no obligation) and the note says the two views are not merged',
          r2['unresolved']['value'] == D('650') and sorted(r2['unresolved']['terms']) == sorted([(p2a.id, -1, D('250')), (p2b.id, -1, D('300'))])
          and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r2)) and any('never merged' in n for n in r2['note']))
    p2c = fund(X2, '$50', '2026-02-10', mercy, household)                                    # a refund from the provider
    p2d = fund(X2, '$100', '2026-02-12', hsa, mercy)                                         # the HSA pays the provider
    r13 = rc(X2, '2026-03-31')
    check('Rc13 (direction on X): Aetna -> Mercy -250, Mercy -> Rob +50, the HSA -> Mercy -100 - any payer to the provider in effect funds; the provider paying is money back; unresolved 600',
          {pm['payment']: pm['direction']['sign'] for pm in r13['payments']} == {p2a.id: -1, p2b.id: -1, p2c.id: 1, p2d.id: -1}
          and r13['unresolved']['value'] == D('600'))
    stray = pay(None, '$75', '2026-02-15', household, mercy, attach=False)                   # a payment to the provider with NO membership ground
    _, rM = held('h-mercy-statement', mercy)
    p2e = fund(X2, '$20', '2026-02-16', household, mercy, member=False)
    claim(db.PAYMENT_IN_RESPECT_OF, reading=rM, subject_payment_id=p2e.id, object_expense_id=X2.id)   # a matcher's candidate
    r14 = rc(X2, '2026-03-31')
    check('Rc14: a payment to the provider without the membership ground is NOT in the report at all; a candidate (reading-sourced) membership is listed as a candidate payment and not counted; unresolved still 600',
          stray.id not in [pm['payment'] for pm in r14['payments']] and stray.id not in [p for _, p in r14['candidate_payments']]
          and [p for _, p in r14['candidate_payments']] == [p2e.id] and r14['unresolved']['value'] == D('600'))
    O2 = bill(X2, mercy, '$650')
    Oc = mint(db.Obligation, 'A candidate bill.')
    entitled(mercy, Oc)
    in_respect(Oc, X2, reading=rM)
    r14b = rc(X2, '2026-03-31')
    check('Rc14: a reading-sourced *O in respect of X* is a candidate obligation, not a context; the comparison runs one-to-one with O2 (650 - 650 = 0) and names the candidate in nothing that breaks it',
          [o for _, o in r14b['candidate_obligations']] == [Oc.id] and [o['obligation'] for o in r14b['obligations']] == [O2.id]
          and r14b['comparison']['difference'] == D('0'))

    print('\n4. Rc3 / Rc4 / Rc5 / Rc6 / Rc15 / Rc16 / Rc19 - determinations: claims, series, conflict; nothing inferred\n')
    check('Rc19 (zero is not a determination): X2 has unresolved 600 and no claim -> current None, reason "no determination claimed"; X1 likewise',
          r14b['determinations']['current'] is None and r14b['determinations']['reason'] == 'no determination claimed' and r1['determinations']['current'] is None)
    d3 = determine(X2, household, 'user_paid_cash', '2026-03-01')
    r3 = rc(X2, '2026-03-31')
    check('Rc3 (D12): Rob claims user_paid_cash on 3/1 -> CURRENT user_paid_cash by Rob (the claim named); the unresolved amount does not move (600); the asserter\'s roles reported, not enforced',
          r3['determinations']['current'] == {'name': 'user_paid_cash', 'asserters': [household.id], 'claims': [d3.id]} and r3['unresolved']['value'] == D('600')
          and r3['determinations']['claims'][0]['roles'] == {'provider_of': db.EFFECT_UNDETERMINED, 'insurer_of': db.EFFECT_UNDETERMINED, 'household_person': True})
    X4 = visit('Superseded.', mercy, aetna, billed='$500', pr='$100')
    d4a = determine(X4, household, 'pending_claim', '2026-03-01')
    d4b = determine(X4, household, 'provider_adjustment', '2026-05-01')
    r4 = rc(X4, '2026-05-31')
    check('Rc4: pending_claim (3/1) then provider_adjustment (5/1) by Rob -> current the 5/1 claim; the 3/1 claim STILL LISTED (superseded, never overwritten); asked 4/1 the 3/1 claim is current',
          r4['determinations']['current']['claims'] == [d4b.id] and [c['claim'] for c in r4['determinations']['claims']] == [d4a.id, d4b.id]
          and rc(X4, '2026-04-01')['determinations']['current']['claims'] == [d4a.id])
    Xu = visit('Unpaid.', mercy, aetna, billed='$500', pr='$100')
    Xp = visit('Pending.', mercy, aetna, billed='$500', pr='$100')
    determine(Xu, household, 'unpaid', '2026-03-01')
    determine(Xp, household, 'pending_claim', '2026-03-01')
    ru, rp = rc(Xu, '2026-03-31'), rc(Xp, '2026-03-31')

    def _shape(r):
        return (r['d'], r['candidate_obligations'], r['contested_obligations'], r['candidate_payments'], r['contested_payments'],
                r['comparison']['difference'], r['comparison']['reason'], r['unresolved']['value'], r['unresolved']['charge']['value'],
                r['unresolved']['terms'], r['unresolved']['reason'], r['determinations']['reason'], r['note'])
    check('Rc5 (mechanical): two otherwise-identical expenses, one `unpaid`, one `pending_claim` -> the reports differ EXACTLY in the determination\'s name; no shared state; no mapping between the names anywhere in the module',
          ru['determinations']['current']['name'] == 'unpaid' and rp['determinations']['current']['name'] == 'pending_claim'
          and _shape(ru) == _shape(rp) and ru['unresolved']['value'] == rp['unresolved']['value']
          and not any(hasattr(db, n) for n in ('unpaid_is_pending', 'pending_is_unpaid', 'collapse_determinations', 'DETERMINATION_MAP')))
    X6 = visit('Denied.', mercy, aetna, billed='$500', pr='$0')
    claim('denial', utterance=utter('not a covered service', origin=aetna), as_of='2026-02-01', content='not covered', subject_expense_id=X6.id)
    determine(X6, aetna, 'not_covered', '2026-02-01')
    r6 = rc(X6, '2026-03-31')
    check('Rc6 (C7): Aetna\'s denial (a kind of its own) is not read; a determination claim whose content is not one of the four is UNRECOGNISED and never current; the note says no denial kind is read',
          r6['determinations']['current'] is None and [c['name'] for c in r6['determinations']['claims']] == [db.DETERMINATION_UNRECOGNISED]
          and any('denial' in n for n in r6['note']) and not any(isinstance(v, str) and 'not covered' in v for _, v in _walk(r6)))
    X15 = visit('Retracted and disputed.', mercy, aetna, billed='$500', pr='$100')
    u15 = utter('user_paid_cash')
    d15a = determine(X15, household, 'pending_claim', '2026-02-01')
    d15b = determine(X15, household, 'user_paid_cash', '2026-03-01', utterance=u15)
    retract(u15, 'not paid yet')
    r15a = rc(X15, '2026-03-31')
    check('Rc15: the latest claim retracted -> it leaves Rob\'s series (listed as contested) and the prior pending_claim is current again - not read as unpaid',
          r15a['determinations']['current'] == {'name': 'pending_claim', 'asserters': [household.id], 'claims': [d15a.id]}
          and [c['state'] for c in r15a['determinations']['claims'] if c['claim'] == d15b.id] == [db.CLAIM_CONTESTED])
    d15c = determine(X15, mercy, 'provider_adjustment', '2026-03-15')
    r15b = rc(X15, '2026-03-31')
    check('Rc15: Mercy says provider_adjustment (3/15) beside Rob\'s pending_claim -> the parties\' currents DIFFER -> CONFLICT, nothing current, both listed; recency across parties resolves nothing',
          r15b['determinations']['current'] is None and sorted(c['claim'] for c in r15b['determinations']['conflict']) == sorted([d15a.id, d15c.id])
          and 'differ' in r15b['determinations']['reason'])
    d15d = determine(X15, household, 'provider_adjustment', '2026-03-20')
    r15c = rc(X15, '2026-03-31')
    check('Rc15: Rob then says provider_adjustment too -> the parties agree -> CURRENT provider_adjustment with BOTH asserters named',
          r15c['determinations']['current']['name'] == 'provider_adjustment' and sorted(r15c['determinations']['current']['asserters']) == sorted([household.id, mercy.id]))
    determine(X15, mercy, 'unpaid', '2026-03-15')
    r15d = rc(X15, '2026-03-31')
    check('Rc15: two claims by Mercy at one date with different names -> Mercy\'s series conflicted (no current_Mercy); Rob\'s current stands alone -> current provider_adjustment by Rob only',
          r15d['determinations']['series'][mercy.id]['current'] is None and len(r15d['determinations']['series'][mercy.id]['conflict']) == 2
          and r15d['determinations']['current'] == {'name': 'provider_adjustment', 'asserters': [household.id], 'claims': [d15d.id]})
    X16 = visit('As of d.', mercy, aetna, billed='$500', pr='$100')
    determine(X16, household, 'unpaid', '2026-04-15')
    check('Rc16 (as of d): a determination dated 4/15 is not current on 3/31 and is current on 4/30; created_at is never read',
          rc(X16, '2026-03-31')['determinations']['current'] is None and rc(X16, '2026-04-30')['determinations']['current']['name'] == 'unpaid'
          and 'created_at' not in __import__('inspect').getsource(db.reconciliation))

    print("\n5. Rc7 / Rc8 / Rc10 / Rc11 - no apportionment, no sum, no choice between statements; history\n")
    X7a = visit('The ER visit (C5).', mercy, aetna, billed='$900', pr='$300')
    X7b = visit('The follow-up (C5).', mercy, aetna, billed='$300', pr='$100')
    O7 = bill(X7a, mercy, '$400')
    in_respect(O7, X7b)
    r7 = rc(X7a, '2026-03-31')
    check('Rc7 (C5): one O in respect of X7a and X7b -> comparison undetermined "in respect of several expenses - no apportionment"; unresolved for X7a still 900',
          r7['comparison']['difference'] is None and 'several expenses' in r7['comparison']['reason'] and r7['obligations'][0]['other_expenses'] == [X7b.id]
          and r7['unresolved']['value'] == D('900'))
    X8 = visit("Two bills (D'3).", mercy, aetna, billed='$1,300', pr='$412')
    bill(X8, mercy, '$300')
    O8b = mint(db.Obligation, 'The radiologist bill.')
    entitled(radiology, O8b)
    stated(O8b, radiology, '$150', '2026-02-01')
    in_respect(O8b, X8)
    r8 = rc(X8, '2026-03-31')
    check("Rc8 (D'3): O1 (Mercy) and O2 (the radiologist) both in respect of X -> comparison undetermined 'several obligations - no sum'; both listed with 7G figures",
          r8['comparison']['difference'] is None and 'several obligations' in r8['comparison']['reason'] and len(r8['obligations']) == 2)
    X10 = visit('PR conflict.', mercy, aetna, billed='$500', pr='$412')
    xstance('patient_responsibility', X10, aetna, '$380', '2026-01-15')
    bill(X10, mercy, '$400')
    r10 = rc(X10, '2026-03-31')
    check('Rc10: two Aetna PR claims at one date (412, 380) -> CONFLICT, no governing PR, both listed; comparison undetermined; nothing chosen',
          r10['stances']['patient_responsibility']['governing'] is None and len(r10['stances']['patient_responsibility']['conflict']) == 2
          and r10['comparison']['difference'] is None)
    X11 = visit('PR history.', mercy, aetna, billed='$500', pr='$500')
    xstance('patient_responsibility', X11, aetna, '$412', '2026-03-01')                       # a corrected EOB
    O11 = bill(X11, mercy, '$412')
    r11 = rc(X11, '2026-03-31')
    check('Rc11: EOB 1/15 PR 500, corrected EOB 3/1 PR 412 -> HISTORY (both listed, both qualifying); the 3/1 one governs, named; difference 0; asked 2/1 the 500 governs (difference -88)',
          r11['stances']['patient_responsibility']['governing']['value'] == D('412') and r11['comparison']['difference'] == D('0')
          and [c['qualifies'] for c in r11['stances']['patient_responsibility']['claims']] == [True, True]
          and rc(X11, '2026-02-01')['comparison']['difference'] == D('-88'))

    print('\n6. Rc17 / Rc18 / Rc20 / Rc21 - surfaced not stored; the null model; no classification; where the failure appears\n')
    before = snapshot()
    rc(X2, '2026-03-31')
    check('Rc17: reading a report wrote nothing - every row identical; no determination / status / paid column on any 2.0 table',
          snapshot() == before
          and not any(any(w in c.name for w in ('determination', 'status', 'paid', 'reconciled', 'matches')) for cls in
                      (db.Proposition, db.Party, db.Obligation, db.Payment, db.Expense, db.Plan, db.Artefact, db.Reading, db.Utterance, db.EvidentiaryRelationship)
                      for c in cls.__table__.columns))
    X18 = visit('Null model.', mercy, aetna, billed='$1,000', pr='$1,000')
    n1 = fund(X18, '$600', '2026-02-01', aetna, mercy)
    n2 = fund(X18, '$400', '2026-02-02', household, mercy)
    O18 = bill(X18, mercy, '$1,000')
    r18 = rc(X18, '2026-03-31')
    check('Rc18 (null model): funding = charge -> UNRESOLVED 0; positions equal -> DIFFERENCE 0; and zero is arithmetic: current determination None',
          r18['unresolved']['value'] == D('0') and r18['comparison']['difference'] == D('0') and r18['determinations']['current'] is None)
    u_n2 = s.query(db.EvidentiaryRelationship).join(db.Proposition, db.Proposition.id == db.EvidentiaryRelationship.proposition_id).filter(
        db.Proposition.kind == db.PAYMENT_IN_RESPECT_OF, db.Proposition.subject_payment_id == n2.id).one().utterance
    retract(u_n2, 'that was not for this visit')
    r18b = rc(X18, '2026-03-31')
    check('Rc18 (null model): one funding event\'s membership retracted -> unresolved rises by EXACTLY its amount (400); the payment listed as contested; no determination inferred',
          r18b['unresolved']['value'] == D('400') and [p for _, p in r18b['contested_payments']] == [n2.id] and r18b['determinations']['current'] is None)
    corpus = [r1, r2, r3, r4, r6, r7, r8, r9, r10, r11, r12, r13, r14, r14b, r15a, r15b, r15c, r15d, r18, r18b, ru, rp]
    check('Rc20: no classification word or key - deductible / qualifying / reimbursed / taxable / paid / status / denied - anywhere in any report; no float',
          not any(k in FORBIDDEN_KEYS for r in corpus for k, _ in _walk(r))
          and not any(isinstance(v, str) and any(w in v.lower() for w in ('deductible', 'qualifying', 'reimbursed', 'taxable')) for r in corpus for _, v in _walk(r))
          and not any(isinstance(v, float) for r in corpus for _, v in _walk(r)))
    check('Rc21 (where the failure appears): every current determination rests on established recognised claims; no difference without one-to-one; every unresolved value = charge - the signed terms; no payment in the report without a membership ground',
          all(all(any(c['claim'] == cid and c['state'] == db.CLAIM_ESTABLISHED and c['recognised'] for c in r['determinations']['claims']) for cid in r['determinations']['current']['claims'])
              for r in corpus if r['determinations']['current'] is not None)
          and all(len(r['obligations']) == 1 and r['obligations'][0]['other_expenses'] == [] for r in corpus if r['comparison']['difference'] is not None)
          and all(r['unresolved']['value'] == r['unresolved']['charge']['value'] + sum(sg * a for _, sg, a in r['unresolved']['terms']) for r in corpus if r['unresolved']['value'] is not None)
          and all(any(st == db.CLAIM_ESTABLISHED for _, _, st, _ in pm['grounds']) for r in corpus for pm in r['payments']))

    print('\n7. The dependency direction and the wiring guard\n')
    check('reconciliation reads reach (both in-respect-of kinds), remaining (7G), derived_strength and the role answers, and nothing that resolves, scores or allocates',
          {'reach', 'remaining', 'derived_strength'} <= calls_in(db.reconciliation)
          and not ({'level_consistency', 'chain_strength', 'aboutness', 'independence', 'parse_disputes', 'reconstruction'} & calls_in(db.reconciliation)))
    check('the 7H wiring guard is executable (AST): reconciliation calls no session write method and constructs no mapped class',
          writes_in(db.reconciliation) == [])


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
