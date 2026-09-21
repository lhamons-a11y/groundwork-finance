"""remaining - the executable trace of `gw 2.0/CONSUMER_DERIVATIONS.md` pass 7G (ruled 2026-09-18, s 7G.8).

REMAINING IS THREE FIGURES AND A DIAGNOSTIC, NEVER ONE NUMBER. Stations per attached payment (attached_candidate /
attached_contested / attached_unacknowledged / discharged - RG-a: an established acknowledgment dated <= d by a party
in effect as the entitled party at that date, at strength knowing); the governing P-ack position S(d) named with its
date b (TG-base); attached and confirmed = S(d) - sum(dir*amt) over payments with b < occurred_on <= d, confirmed
additionally requiring discharge established by d (two independent predicates); remaining = confirmed by name;
direction = household <-> the entitled party in effect; netting by established counteracts only; undetermined
propagates; negative as it comes; pending and statement_check only where every term exists.

What this slice can and cannot exercise
---------------------------------------
    Dg1  attached, unacknowledged: attached moves, confirmed does not                                  EXERCISED
    Dg2  E's own statement -> discharged; Dg2' the parser's reading -> a candidate                     EXERCISED
    Dg3  K6: clearance is not read                                                                     EXERCISED
    Dg4  K2: the servicer's acknowledgment - role undetermined, not discharged                          EXERCISED
    Dg5  S3: the never-authorised servicer - never discharged; attached undetermined (direction)        EXERCISED
    Dg6  K8: discharge beside a statement - the statement check                                        EXERCISED
    Dg7  F2: bill 4,000 / attached 350 / statement 3,700 -> statement_check 50; P-ack history          EXERCISED
    Dg8  F3: the household's figure is no base (TG-base)                                                EXERCISED
    Dg9  F4: two statements at one date -> no S, no figures, no diagnostic                              EXERCISED
    Dg10 A1: counteraction nets both payments; establishes no discharge                                 EXERCISED
    Dg11 D9: a reimbursement from a non-entitled party -> direction undetermined, named                 EXERCISED
    Dg12 D'11: E's refund -> money in, +amount                                                         EXERCISED
    Dg13 no payee / payee's role undetermined -> undetermined naming the payment                         EXERCISED
    Dg14 no P-ack -> no S -> both projections undetermined; stations still reported                    EXERCISED
    Dg16 disputed amount -> undetermined naming the payment; the candidate never counts                 EXERCISED
    Dg17 D'12: one cheque, two obligations - counted in full on each; the note names it                 EXERCISED
    Dg18 D'10: a return kind is not read; the note says so                                              EXERCISED
    Dg19 as of d: an acknowledgment dated after d does not yet count                                     EXERCISED
    Dg20 surfaced not stored: retract / re-assert; nothing written                                      EXERCISED
    Dg21 E's role contested at the acknowledgment's date -> not discharged                              EXERCISED
    Dg22 the discriminator: the household relays E's acknowledgment - not_knowing - RG-a: no             EXERCISED
    Dg23 one hop: p in respect of X only is not among O's payments                                       EXERCISED
    Dg24 the null model: all discharged -> confirmed = attached; one retracted -> exactly that amount    EXERCISED
    Dg25 where the failure appears                                                                       EXERCISED
    Dg26 a payment before b acknowledged after b: inside the base, not subtracted twice                  EXERCISED
    Dg27 negative as it comes                                                                            EXERCISED
    Dg28 the invariant, mechanically                                                                     EXERCISED
    the wiring guard: AST (session receivers) + a full row-content snapshot                              EXERCISED
    the acknowledgment / role / value catalogues (stand-ins here), 7I allocation, 7H, payment_plan.py    NOT BUILT

Run:  python tests/test_remaining_fixture.py
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


DECIDER_NAMES = ('paid', 'balance_of', 'is_discharged', 'discharged', 'allocate', 'net', 'net_payments', 'reconcile',
                 'resolve_figures', 'one_balance', 'best_balance', 'remaining_cache', 'confirm_payment', 'apply_payment',
                 'attached_remaining', 'attached_paid', 'floor_remaining')
FORBIDDEN_KEYS = ('balance', 'best', 'resolved', 'chosen', 'average', 'allocation', 'share', 'floor', 'credit', 'status',
                  'ahead', 'overdue', 'first_hand')


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
    d = tempfile.mkdtemp(prefix='gw_rm_')
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
    check('the stand-in role kind is removed; the registry is as shipped; no value or acknowledgment kind was registered',
          db.RULED_KINDS == shipped)   # every kind this fixture reads is ruled: roles 9B, stances 9D-i, values and the bank's stances 9D-iv
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

    def rem(O, d):
        return db.remaining(s, O, d, CATALOGUE, KNOWING)

    def pm(rep, p):
        return next(x for x in rep['payments'] if x['payment'] == p.id)

    def fig(rep, name):
        return rep['figures'][name]['value']

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

    chase = mint(db.Party, 'Chase.')
    mercy = mint(db.Party, 'Mercy Hospital.')
    servicer = mint(db.Party, 'The servicer S.')
    s3 = mint(db.Party, 'S3, never authorised.')
    hsa = mint(db.Party, 'The HSA administrator.')
    bank = mint(db.Party, 'The bank.')

    print('\n1. Absences - no paid / discharged / allocate / net / reconcile helper; no status column\n')
    check('no paid, discharged, allocate, net, reconcile, one-balance or cache helper exists on the module',
          not any(hasattr(db, n) for n in DECIDER_NAMES))
    check('the four stations are named; CATALOGUE_KINDS is the closed list of stand-in names',
          (db.STATION_ATTACHED_CANDIDATE, db.STATION_ATTACHED_CONTESTED, db.STATION_ATTACHED_UNACKNOWLEDGED, db.STATION_DISCHARGED)
          == ('attached_candidate', 'attached_contested', 'attached_unacknowledged', 'discharged')
          and set(db.CATALOGUE_KINDS) == set(CATALOGUE))
    m1 = _refused(db.remaining, s, mint(db.Obligation, 'x'), '2026-03-31', {k: v for k, v in CATALOGUE.items() if k != 'balance'}, KNOWING)
    m2 = _refused(db.remaining, s, mint(db.Obligation, 'y'), '2026-03-31', dict(CATALOGUE, entitled_party=db.OBLIGATION_IN_RESPECT_OF), KNOWING)
    check('refusals by name: a catalogue missing a kind; an entitled-party kind that is not a role (no boundary bound to it)',
          m1 is not None and 'balance' in m1 and m2 is not None and 'not a ruled role' in m2)

    print('\n2. Dg1 / Dg2 / Dg2\' / Dg3 - attached moves attached, only discharge moves confirmed; a reading is a candidate\n')
    O1 = mint(db.Obligation, 'The mortgage.')
    entitled(chase, O1)
    stated(O1, chase, '$4,000', '2026-03-01')
    p1 = pay(O1, '$1,412', '2026-03-05', household, chase)
    r1 = rem(O1, '2026-03-31')
    check('Dg1 (H2): attached, no acknowledgment -> station ATTACHED_UNACKNOWLEDGED; attached = 4,000 - 1,412 = 2,588 with p1 in its basis; CONFIRMED = 4,000 unmoved; remaining = confirmed; S named with b = 3/1',
          pm(r1, p1)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED and fig(r1, 'attached') == D('2588') and fig(r1, 'confirmed') == D('4000')
          and r1['figures']['remaining'] == {'value': D('4000'), 'is': 'confirmed'}
          and r1['stated']['governing']['as_of'] == '2026-03-01' and r1['stated']['governing']['asserter'] == chase.id
          and r1['figures']['attached']['basis'] == [(p1.id, -1, D('1412'))] and r1['figures']['confirmed']['basis'] == [])
    check('Dg1: pending = attached - confirmed = -1,412, naming p1 - the acknowledgment-state number, not a balance',
          r1['diagnostic']['pending'] == {'value': D('-1412'), 'reason': None, 'payments': [p1.id]})
    claim(db.CLEARED, utterance=utter('cleared 3/6', origin=bank), as_of='2026-03-06', subject_payment_id=p1.id)
    check('Dg3 (K6): the bank\'s clearance is not an acknowledgment and is not read - the station is unchanged',
          pm(rem(O1, '2026-03-31'), p1)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED)
    a1 = ack(chase, p1, '2026-03-10')
    r2 = rem(O1, '2026-03-31')
    check('Dg2 (K1): Chase\'s own acknowledgment (origin Chase, entitled in effect, strength knowing) -> DISCHARGED at 3/10; confirmed = 2,588; pending 0',
          pm(r2, p1)['station'] == db.STATION_DISCHARGED and pm(r2, p1)['discharge'] == {'as_of': '2026-03-10', 'claim': a1.id}
          and pm(r2, p1)['acknowledgments'][0]['entitled'] == db.EFFECT_IN and pm(r2, p1)['acknowledgments'][0]['strength'] == db.STRENGTH_KNOWING
          and fig(r2, 'confirmed') == D('2588') and r2['diagnostic']['pending']['value'] == D('0'))
    O2 = mint(db.Obligation, 'The HELOC.')
    entitled(chase, O2)
    stated(O2, chase, '$9,000', '2026-03-01')
    p2 = pay(O2, '$500', '2026-03-05', household, chase)
    _, rS = held('h-chase-statement', chase)
    ack(chase, p2, '2026-03-10', reading=rS)
    r2b = rem(O2, '2026-03-31')
    check('Dg2\': the parser\'s reading of Chase\'s held statement -> a CANDIDATE acknowledgment (listed, state candidate), NOT discharge - reading E\'s statement does not turn the parser into E',
          pm(r2b, p2)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED and [a['state'] for a in pm(r2b, p2)['acknowledgments']] == [db.CLAIM_CANDIDATE]
          and fig(r2b, 'confirmed') == D('9000'))

    print('\n3. Dg4 / Dg5 / Dg21 / Dg22 - the role test and the strength test; the RG discriminator\n')
    O4 = mint(db.Obligation, 'A loan serviced by S.')
    entitled(chase, O4)
    stated(O4, chase, '$2,000', '2026-03-01')
    p4 = pay(O4, '$200', '2026-03-05', household, chase)
    ack(servicer, p4, '2026-03-10')
    claim('serves', utterance=utter('S services it for Chase.'), as_of='2026-01-01', subject_party_id=servicer.id, object_party_id=chase.id)
    r4 = rem(O4, '2026-03-31')
    a4 = pm(r4, p4)['acknowledgments'][0]
    check('Dg4 (K2): the servicer\'s acknowledgment - established, strength knowing by foundation, but S\'s entitled-party role on O4 UNDETERMINED (no stance; the "serves" chain is not evaluable) -> listed, NOT discharge',
          a4['state'] == db.CLAIM_ESTABLISHED and a4['strength'] == db.STRENGTH_KNOWING and a4['entitled'] == db.EFFECT_UNDETERMINED
          and not a4['qualifies'] and pm(r4, p4)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED and fig(r4, 'confirmed') == D('2000'))
    O5 = mint(db.Obligation, 'The mortgage S3 claimed to service.')
    entitled(chase, O5)
    stated(O5, chase, '$3,000', '2026-03-01')
    p5 = pay(O5, '$1,412', '2026-03-05', household, s3)
    ack(s3, p5, '2026-03-10')
    r5 = rem(O5, '2026-03-31')
    check('Dg5 (S3): the never-authorised servicer - never discharged; and the payment\'s direction is UNDETERMINED (payee\'s role undetermined) so ATTACHED is undetermined naming p5; confirmed = 3,000',
          pm(r5, p5)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED and pm(r5, p5)['direction']['sign'] is None
          and fig(r5, 'attached') is None and (p5.id, 'direction payee\'s entitled-party role undetermined') in r5['figures']['attached']['undetermined']
          and fig(r5, 'confirmed') == D('3000'))
    O21 = mint(db.Obligation, 'A loan whose entitled party is contested.')
    entitled(chase, O21)
    claim(db.ENTITLED_PARTY_OF_ENDED, utterance=utter('ended 6/30', origin=mercy), as_of='2026-06-30', subject_party_id=chase.id, object_obligation_id=O21.id)
    claim(db.ENTITLED_PARTY_OF_ENDED, utterance=utter('ended 12/31'), as_of='2026-12-31', subject_party_id=chase.id, object_obligation_id=O21.id)
    stated(O21, chase, '$1,000', '2026-05-01')
    p21 = pay(O21, '$100', '2026-07-10', household, chase)
    ack(chase, p21, '2026-07-15')
    r21 = rem(O21, '2026-07-31')
    check('Dg21: Chase\'s role on O21 is CONTESTED at the acknowledgment\'s date (7F) -> listed as contested, not discharged - and not "not discharged" either; the payment\'s direction is undetermined at its date too',
          pm(r21, p21)['acknowledgments'][0]['entitled'] == db.EFFECT_CONTESTED and pm(r21, p21)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED
          and pm(r21, p21)['direction']['sign'] is None)
    O22 = mint(db.Obligation, 'The discriminator.')
    entitled(chase, O22)
    stated(O22, chase, '$5,000', '2026-03-01')
    p22 = pay(O22, '$1,000', '2026-03-05', household, chase)
    ack(chase, p22, '2026-03-10', origin=household)                      # Rob relays: "Chase told me they got it"
    r22 = rem(O22, '2026-03-31')
    a22 = pm(r22, p22)['acknowledgments'][0]
    check('Dg22 (K5 / S2 - the RG discriminator): the household relays Chase\'s acknowledgment - established, Chase in effect as E, strength NOT_KNOWING -> under RG-a NOT discharged; confirmed = 5,000; RG-b would have moved it',
          a22['state'] == db.CLAIM_ESTABLISHED and a22['entitled'] == db.EFFECT_IN and a22['strength'] == db.STRENGTH_NOT_KNOWING
          and not a22['qualifies'] and pm(r22, p22)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED and fig(r22, 'confirmed') == D('5000')
          and fig(r22, 'attached') == D('4000'))

    print('\n4. Dg7 / Dg6 / Dg8 / Dg9 / Dg14 - the figures: P-ack history, TG-base, conflict, no P-ack\n')
    O7 = mint(db.Obligation, 'The Mercy bill (F2).')
    entitled(mercy, O7)
    stated(O7, mercy, '$4,000', '2026-01-01')
    p7 = pay(O7, '$350', '2026-01-15', household, mercy)
    stated(O7, mercy, '$3,700', '2026-02-01')
    r7 = rem(O7, '2026-02-15')
    check('Dg7 (F2): bill 4,000 at 1/1, attached 350 on 1/15, statement 3,700 at 2/1 -> S = 3,700 (b = 2/1), previous 4,000; p7 INSIDE THE BASE (not subtracted again); attached = confirmed = 3,700; STATEMENT_CHECK = 3,700 - (4,000 - 350) = 50 with its terms',
          r7['stated']['governing']['value'] == D('3700') and r7['stated']['previous']['value'] == D('4000')
          and r7['figures']['attached']['inside_base'] == [p7.id] and fig(r7, 'attached') == D('3700') and fig(r7, 'confirmed') == D('3700')
          and r7['diagnostic']['statement_check']['value'] == D('50') and r7['diagnostic']['statement_check']['terms']['computed'] == D('3650'))
    check('Dg7: two P-ack figures at two dates are HISTORY - both listed as qualifying claims; neither is a conflict',
          [x['value'] for x in r7['stated']['claims'] if x['qualifies']] == [D('4000'), D('3700')] and r7['stated']['conflict'] == [])
    r7b = rem(O7, '2026-01-20')
    check('Dg7: asked 1/20 (before the statement) -> S = 4,000 (b = 1/1), attached = 3,650, confirmed = 4,000; no statement check (no previous S)',
          r7b['stated']['governing']['value'] == D('4000') and fig(r7b, 'attached') == D('3650') and fig(r7b, 'confirmed') == D('4000')
          and r7b['diagnostic']['statement_check']['value'] is None)
    O6 = mint(db.Obligation, 'K8.')
    entitled(chase, O6)
    stated(O6, chase, '$2,075', '2026-07-01')
    p6 = pay(O6, '$175', '2026-07-15', household, chase)
    ack(chase, p6, '2026-07-20')
    stated(O6, chase, '$1,950', '2026-08-01')
    r6 = rem(O6, '2026-08-31')
    check('Dg6 (K8): p6 discharged; the 8/1 statement says 1,950 where the computation from 7/1 says 1,900 -> STATEMENT_CHECK 50, reported with its terms; nothing resolved, no key names a winner',
          pm(r6, p6)['station'] == db.STATION_DISCHARGED and r6['diagnostic']['statement_check']['value'] == D('50')
          and not any(k in FORBIDDEN_KEYS for k, _ in _walk(r6)))
    O8 = mint(db.Obligation, 'F3.')
    entitled(chase, O8)
    stated(O8, household, '$3,500', '2026-03-01')                        # Rob: "I think I owe about $3,500"
    r8 = rem(O8, '2026-03-31')
    check('Dg8 (F3 / TG-base): the household\'s "$3,500" is a balance claim by a party not in effect as E -> listed, NOT qualifying, no S; figures undetermined "no stated position by the entitled party"',
          r8['stated']['governing'] is None and [x['qualifies'] for x in r8['stated']['claims']] == [False]
          and fig(r8, 'attached') is None and r8['figures']['attached']['reason'] == 'no stated position by the entitled party')
    O9 = mint(db.Obligation, 'F4.')
    entitled(chase, O9)
    stated(O9, chase, '$1,900', '2026-08-01')
    stated(O9, chase, '$1,875', '2026-08-01')
    pay(O9, '$50', '2026-08-05', household, chase)
    r9 = rem(O9, '2026-08-31')
    check('Dg9 (F4): two Chase statements at ONE date with different figures -> a CONFLICT (both listed), no S, no figures, no diagnostic - nothing chosen by channel, recording order or amount',
          r9['stated']['governing'] is None and len(r9['stated']['conflict']) == 2 and 'conflicting' in r9['stated']['reason']
          and fig(r9, 'attached') is None and r9['diagnostic']['pending']['value'] is None and r9['diagnostic']['statement_check']['value'] is None)
    O14 = mint(db.Obligation, 'No statement.')
    entitled(chase, O14)
    p14 = pay(O14, '$100', '2026-03-05', household, chase)
    ack(chase, p14, '2026-03-10')
    r14 = rem(O14, '2026-03-31')
    check('Dg14: no P-ack at all -> no S; both projections UNDETERMINED with the reason; the station report still runs (p14 discharged)',
          r14['stated']['governing'] is None and fig(r14, 'attached') is None and fig(r14, 'confirmed') is None
          and pm(r14, p14)['station'] == db.STATION_DISCHARGED)

    print('\n5. Dg10 / Dg11 / Dg12 / Dg13 / Dg16 - netting by assertion; direction relative to the entitled party; undetermined propagates\n')
    O10 = mint(db.Obligation, 'The Mercy plan (A1).')
    entitled(mercy, O10)
    stated(O10, mercy, '$1,000', '2026-05-01')
    q1 = pay(O10, '$300', '2026-06-02', household, mercy)
    q2 = pay(O10, '$300', '2026-06-09', mercy, household)
    ack(mercy, q1, '2026-06-03')
    claim(db.PAYMENT_COUNTERACTS, utterance=utter('The chargeback undid the June payment.'), subject_payment_id=q2.id, object_payment_id=q1.id)
    r10 = rem(O10, '2026-06-30')
    check('Dg10 (A1 / Rv7): p2 counteracts p1 (established) -> BOTH excluded from every figure (counteracted / counteraction), listed with the claim; attached = confirmed = 1,000; p1\'s discharge stands but contributes nothing',
          pm(r10, q1)['netted']['as'] == 'counteracted' and pm(r10, q2)['netted']['as'] == 'counteraction'
          and fig(r10, 'attached') == D('1000') and fig(r10, 'confirmed') == D('1000')
          and pm(r10, q1)['station'] == db.STATION_DISCHARGED and (q1.id, 'counteracted') in r10['figures']['confirmed']['excluded'])
    O11 = mint(db.Obligation, 'D9.')
    entitled(mercy, O11)
    stated(O11, mercy, '$1,000', '2026-05-01')
    q11 = pay(O11, '$412', '2026-06-01', hsa, household)               # the HSA reimbursement, attached by Rob
    r11 = rem(O11, '2026-06-30')
    check('Dg11 (D9): the HSA reimbursement to Rob, attached by Rob - payer is not the entitled party, payee is the household -> direction UNDETERMINED (neither household -> E nor E -> household); attached undetermined naming it; nothing offset',
          pm(r11, q11)['direction']['sign'] is None and fig(r11, 'attached') is None
          and any(pid == q11.id for pid, _ in r11['figures']['attached']['undetermined']))
    O12 = mint(db.Obligation, "D'11.")
    entitled(chase, O12)
    stated(O12, chase, '$1,000', '2026-05-01')
    q12 = pay(O12, '$210', '2026-06-01', chase, household)              # Chase's escrow refund, "on the mortgage"
    r12 = rem(O12, '2026-06-30')
    ack(chase, q12, '2026-06-05')
    r12b = rem(O12, '2026-06-30')
    check("Dg12 (D'11): Chase's refund to Rob - E in effect -> household: MONEY IN, +210; attached = 1,210; once Chase acknowledges it, confirmed = 1,210 too",
          pm(r12, q12)['direction']['sign'] == 1 and fig(r12, 'attached') == D('1210') and fig(r12, 'confirmed') == D('1000')
          and fig(r12b, 'confirmed') == D('1210'))
    O13 = mint(db.Obligation, 'No payee.')
    entitled(chase, O13)
    stated(O13, chase, '$1,000', '2026-05-01')
    q13 = pay(O13, '$100', '2026-06-01', household, None)
    r13 = rem(O13, '2026-06-30')
    check('Dg13: no paid_to claim -> direction undetermined ("payer or payee not established"); attached undetermined naming q13; never assumed money out; never zero',
          pm(r13, q13)['direction']['reason'] == 'payer or payee not established' and fig(r13, 'attached') is None
          and (q13.id, 'direction payer or payee not established') in r13['figures']['attached']['undetermined'])
    O16 = mint(db.Obligation, 'Disputed amount.')
    entitled(chase, O16)
    stated(O16, chase, '$1,000', '2026-05-01')
    q16 = pay(O16, '$300', '2026-06-01', household, chase)
    claim(db.AMOUNT, utterance=utter('$330', origin=kim_party), content='$330', subject_payment_id=q16.id)
    _, rBank = held('h-bank-line', bank)
    claim('amount', reading=rBank, content='$330', subject_payment_id=q16.id)
    r16 = rem(O16, '2026-06-30')
    check('Dg16: Rob says $300, Kim says $330, the bank line reads $330 (a candidate) -> amount DISPUTED; the candidate never counts; attached undetermined naming q16 - no majority, no bank preference',
          pm(r16, q16)['amount']['value'] is None and pm(r16, q16)['amount']['reason'] == 'disputed' and fig(r16, 'attached') is None
          and (q16.id, 'amount disputed') in r16['figures']['attached']['undetermined'])

    print("\n6. Dg17 / Dg18 / Dg19 / Dg23 / Dg26 / Dg27 - one cheque two obligations; a return kind; as of d; one hop; inside the base; negative\n")
    Oa = mint(db.Obligation, 'Plan A.')
    Ob = mint(db.Obligation, 'Plan B.')
    entitled(mercy, Oa)
    entitled(mercy, Ob)
    stated(Oa, mercy, '$500', '2026-05-01')
    stated(Ob, mercy, '$700', '2026-05-01')
    q17 = pay(Oa, '$200', '2026-06-01', household, mercy)
    claim(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, utterance=utter('and toward plan B'), subject_payment_id=q17.id, object_obligation_id=Ob.id)
    ra, rb = rem(Oa, '2026-06-30'), rem(Ob, '2026-06-30')
    check("Dg17 (D'12): one cheque attached to two obligations -> counted IN FULL on each (300 and 500); no allocation, no split; the note names the double count for 7I",
          fig(ra, 'attached') == D('300') and fig(rb, 'attached') == D('500')
          and any("D'12" in n for n in ra['note']) and not any(k in ('allocation', 'share', 'split') for k, _ in _walk(ra)))
    claim(db.RETURNED, utterance=utter('returned unapplied', origin=chase), as_of='2026-03-12', subject_party_id=chase.id, object_payment_id=p1.id)   # 9D-i: E's return, the acknowledgment's shape
    check("Dg18 (D'10): Chase's 'returned unapplied' claim on p1 is a kind 7G does not read -> p1 stays discharged; the note says the return kind is not read",
          pm(rem(O1, '2026-03-31'), p1)['station'] == db.STATION_DISCHARGED and any("D'10" in n for n in r1['note']))
    O19 = mint(db.Obligation, 'As of d.')
    entitled(chase, O19)
    stated(O19, chase, '$1,000', '2026-08-01')
    q19 = pay(O19, '$100', '2026-08-05', household, chase)
    ack(chase, q19, '2026-08-15')
    r19a, r19b = rem(O19, '2026-08-10'), rem(O19, '2026-08-20')
    check('Dg19 (as of d): the acknowledgment dated 8/15 does not yet count on 8/10 (attached 900, confirmed 1,000); on 8/20 it does (confirmed 900); created_at is never read',
          fig(r19a, 'attached') == D('900') and fig(r19a, 'confirmed') == D('1000') and pm(r19a, q19)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED
          and fig(r19b, 'confirmed') == D('900') and pm(r19b, q19)['station'] == db.STATION_DISCHARGED
          and 'created_at' not in __import__('inspect').getsource(db.remaining))
    X = mint(db.Expense, 'The ER visit.')
    O23 = mint(db.Obligation, 'The Mercy bill for the ER visit.')
    entitled(mercy, O23)
    stated(O23, mercy, '$800', '2026-05-01')
    claim(db.OBLIGATION_IN_RESPECT_OF, utterance=utter('the bill is for the visit'), subject_obligation_id=O23.id, object_expense_id=X.id)
    q23 = pay(O23, '$100', '2026-06-01', household, mercy, attach=False)
    claim(db.PAYMENT_IN_RESPECT_OF, utterance=utter('the $100 was for the visit'), subject_payment_id=q23.id, object_expense_id=X.id)
    r23 = rem(O23, '2026-06-30')
    check("Dg23 (D'3, one hop): p in respect of X and O in respect of X, no p -> O -> p is NOT among O's payments; attached = 800",
          r23['payments'] == [] and fig(r23, 'attached') == D('800'))
    O26 = mint(db.Obligation, 'Before the base.')
    entitled(chase, O26)
    q26 = pay(O26, '$100', '2026-02-20', household, chase)               # occurred before b
    stated(O26, chase, '$1,000', '2026-03-01')
    ack(chase, q26, '2026-03-10')                                        # acknowledged after b
    r26 = rem(O26, '2026-03-31')
    check('Dg26 (the correction, s 7G.8): a payment that OCCURRED before b and was ACKNOWLEDGED after b is inside the base - discharged, yet NOT subtracted from confirmed (1,000, not 900); ack.as_of never substitutes for occurred_on',
          pm(r26, q26)['station'] == db.STATION_DISCHARGED and r26['figures']['confirmed']['inside_base'] == [q26.id]
          and fig(r26, 'confirmed') == D('1000') and fig(r26, 'attached') == D('1000'))
    O27 = mint(db.Obligation, 'Negative.')
    entitled(chase, O27)
    stated(O27, chase, '$100', '2026-03-01')
    q27 = pay(O27, '$300', '2026-03-05', household, chase)
    ack(chase, q27, '2026-03-10')
    r27 = rem(O27, '2026-03-31')
    check('Dg27: E\'s acknowledgments since b exceed S -> confirmed = -200, reported as it comes; no floor, no credit status',
          fig(r27, 'confirmed') == D('-200') and not any(k in ('floor', 'credit', 'overpaid') for k, _ in _walk(r27)))

    print('\n7. Dg20 / Dg24 / Dg25 / Dg28 - surfaced not stored; the null model; where the failure appears; the invariant\n')
    u_att = s.query(db.EvidentiaryRelationship).join(db.Proposition, db.Proposition.id == db.EvidentiaryRelationship.proposition_id).filter(
        db.Proposition.kind == db.PAYMENT_IN_RESPECT_OF_OBLIGATION, db.Proposition.subject_payment_id == p1.id).one().utterance
    before = snapshot()
    rem(O1, '2026-03-31')
    wrote_nothing = snapshot() == before
    retract(u_att, 'That payment was not toward the mortgage.')
    r20 = rem(O1, '2026-03-31')
    claim(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, utterance=utter('yes it was'), subject_payment_id=p1.id, object_obligation_id=O1.id)
    r20b = rem(O1, '2026-03-31')
    check('Dg20: the attachment retracted -> ATTACHED_CONTESTED, p1 leaves every figure (attached = confirmed = 4,000); re-asserted -> discharged again; the read before the retraction wrote nothing',
          pm(r20, p1)['station'] == db.STATION_ATTACHED_CONTESTED and fig(r20, 'attached') == D('4000') and fig(r20, 'confirmed') == D('4000')
          and pm(r20b, p1)['station'] == db.STATION_DISCHARGED and fig(r20b, 'confirmed') == D('2588')
          and wrote_nothing)
    O24 = mint(db.Obligation, 'Null model.')
    entitled(chase, O24)
    stated(O24, chase, '$1,000', '2026-03-01')
    n1 = pay(O24, '$100', '2026-03-05', household, chase)
    n2 = pay(O24, '$200', '2026-03-06', household, chase)
    n3 = pay(O24, '$300', '2026-03-07', household, chase)
    an2 = ack(chase, n2, '2026-03-10')
    ack(chase, n1, '2026-03-10')
    ack(chase, n3, '2026-03-10')
    r24 = rem(O24, '2026-03-31')
    check('Dg24 (null model): every attachment acknowledged by E -> CONFIRMED = ATTACHED = 400; pending 0',
          fig(r24, 'confirmed') == fig(r24, 'attached') == D('400') and r24['diagnostic']['pending']['value'] == D('0'))
    u_n2 = s.query(db.EvidentiaryRelationship).filter_by(proposition_id=an2.id).one().utterance
    retract(u_n2, 'We did not receive the $200.')
    r24b = rem(O24, '2026-03-31')
    check('Dg24 (null model): one acknowledgment retracted -> confirmed rises by EXACTLY that payment\'s amount (600), attached unchanged (400), pending -200 naming n2',
          fig(r24b, 'confirmed') == D('600') and fig(r24b, 'attached') == D('400') and r24b['diagnostic']['pending'] == {'value': D('-200'), 'reason': None, 'payments': [n2.id]})
    corpus = [rem(O, '2026-12-31') for O in (O1, O2, O4, O5, O21, O22, O7, O6, O8, O9, O14, O10, O11, O12, O13, O16, Oa, Ob, O19, O23, O26, O27, O24)]
    check('Dg28 (the invariant, mechanically): over the corpus every payment in confirmed\'s basis is DISCHARGED and not netted; no attached-only, acknowledged-only or counteracted payment contributes; every basis entry has an established amount and direction',
          all(pm(rep, type('P', (), {'id': pid})())['station'] == db.STATION_DISCHARGED and pm(rep, type('P', (), {'id': pid})())['netted'] is None
              for rep in corpus for pid, _, _ in rep['figures']['confirmed']['basis'])
          and all(sign in (-1, 1) and amt is not None for rep in corpus for f in ('attached', 'confirmed') for _, sign, amt in rep['figures'][f]['basis']))
    check('Dg25 (where the failure appears): no figure has a value where S is absent or conflicted; no diagnostic has a value where a term is missing; no acknowledgment qualifies without state established + E in effect + knowing + as_of <= d',
          all(rep['figures'][f]['value'] is None for rep in corpus if rep['stated']['governing'] is None for f in ('attached', 'confirmed'))
          and all(rep['diagnostic']['pending']['value'] is None for rep in corpus if rep['figures']['attached']['value'] is None or rep['figures']['confirmed']['value'] is None)
          and all(rep['diagnostic']['statement_check']['value'] is None for rep in corpus if rep['stated']['previous'] is None)
          and all((a['state'] == db.CLAIM_ESTABLISHED and a['entitled'] == db.EFFECT_IN and a['strength'] == db.STRENGTH_KNOWING and a['as_of'] <= rep['d'])
                  for rep in corpus for p_ in rep['payments'] for a in p_['acknowledgments'] if a['qualifies']))

    print('\n7b. 7G-F3 (s 7G-F3.8) - the discharge test is applied to the CLAIM: state from any relationship, strength the claim\'s knowing origin\n')
    Of = mint(db.Obligation, 'A loan whose acknowledgments come by document.')
    entitled(chase, Of)
    stated(Of, chase, '$5,000', '2026-03-01')
    pf = pay(Of, '$500', '2026-03-05', household, chase)
    _, rF = held('h-chase-march-statement', chase)
    a_f = ack(chase, pf, '2026-03-10', reading=rF)                                                      # the reading: candidate, knowing
    before = pm(rem(Of, '2026-03-31'), pf)
    u_accept = utter("That line is Chase acknowledging the March payment.", '2026-04-01T09:00:00')
    evidence(a_f, utterance=u_accept)                                                                 # Rob's acceptance: established, not_knowing
    r_f = rem(Of, '2026-03-31')
    a_rep = next(a for a in pm(r_f, pf)['acknowledgments'] if a['claim'] == a_f.id)
    check('Dc3 (K1 with acceptance - Dg2 as s 7G.3 wrote it): the reading of Chase\'s statement alone -> a candidate, NOT discharged; Rob\'s acceptance added to the SAME claim -> the claim ESTABLISHED with a KNOWING origin -> DISCHARGED at the acknowledgment\'s date; one entry per claim, both origins listed, Rob\'s own not_knowing',
          before['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED
          and pm(r_f, pf)['station'] == db.STATION_DISCHARGED and pm(r_f, pf)['discharge'] == {'as_of': '2026-03-10', 'claim': a_f.id}
          and a_rep['state'] == db.CLAIM_ESTABLISHED and a_rep['strength'] == db.STRENGTH_KNOWING
          and sorted((o['state'], o['strength']) for o in a_rep['origins']) == sorted([(db.CLAIM_CANDIDATE, db.STRENGTH_KNOWING), (db.CLAIM_ESTABLISHED, db.STRENGTH_NOT_KNOWING)])
          and fig(r_f, 'confirmed') == D('4500'))
    pf4 = pay(Of, '$500', '2026-04-05', household, chase)
    _, rSheet = held('h-rob-sheet', household)
    a_f4 = ack(chase, pf4, '2026-04-10', reading=rSheet)
    evidence(a_f4, utterance=utter('My sheet says Chase got the April payment.', '2026-04-12T09:00:00'))
    r_f4 = rem(Of, '2026-04-30')
    check('Dc4 (no laundering): Rob\'s acceptance + a reading of ROB\'s spreadsheet -> established, but no knowing origin (both origins Rob) -> NOT discharged; a knowing origin is required, a second not-knowing one lifts nothing',
          pm(r_f4, pf4)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED
          and next(a for a in pm(r_f4, pf4)['acknowledgments'] if a['claim'] == a_f4.id)['strength'] == db.STRENGTH_NOT_KNOWING)
    pf5 = pay(Of, '$500', '2026-05-05', household, chase)
    a_f5 = ack(chase, pf5, '2026-05-10', reading=rF)
    evidence(a_f5, utterance=utter("Chase's statement shows the May payment received.", '2026-05-12T09:00:00', origin=s3))
    r_f5 = rem(Of, '2026-05-31')
    check('Dc5 (F1 - any establishing party): S3\'s utterance establishes the claim beside the reading of CHASE\'s statement -> DISCHARGED on Chase\'s statement (the knowing origin); S3\'s say-so adds nothing and subtracts nothing - the origins list shows which is which',
          pm(r_f5, pf5)['station'] == db.STATION_DISCHARGED
          and [o['strength'] for o in next(a for a in pm(r_f5, pf5)['acknowledgments'] if a['claim'] == a_f5.id)['origins'] if o['state'] == db.CLAIM_ESTABLISHED] == [db.STRENGTH_NOT_KNOWING])
    retract(u_accept, 'I was wrong about that line.')
    r_f6 = rem(Of, '2026-03-31')
    check('Dc6 (F3): Rob retracts his acceptance -> the claim is CONTESTED by the existing state rule (the reading still a candidate) -> NOT discharged; nothing new decided',
          pm(r_f6, pf)['station'] != db.STATION_DISCHARGED and pm(r_f6, pf)['discharge'] is None
          and next(a for a in pm(r_f6, pf)['acknowledgments'] if a['claim'] == a_f.id)['state'] == db.CLAIM_CONTESTED)
    pf7 = pay(Of, '$500', '2026-06-05', household, chase)
    _, rS = held('h-servicer-statement', servicer)
    a_f7 = ack(chase, pf7, '2026-06-10', reading=rS)
    evidence(a_f7, utterance=utter("The servicer's statement shows June received.", '2026-06-12T09:00:00'))
    r_f7 = rem(Of, '2026-06-30')
    check('Dc7 (K2): Rob\'s acceptance + a reading of THE SERVICER\'s statement -> the origin is S, not the holder E -> not_knowing -> NOT discharged; K2\'s channel stays the consumer\'s question, as 9D-i left it',
          pm(r_f7, pf7)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED
          and next(a for a in pm(r_f7, pf7)['acknowledgments'] if a['claim'] == a_f7.id)['strength'] == db.STRENGTH_NOT_KNOWING)
    pf8 = pay(Of, '$500', '2026-07-05', household, chase)
    _, rF2 = held('h-chase-july-statement', chase)
    a_f8 = ack(chase, pf8, '2026-07-10', reading=rF2)
    evidence(a_f8, reading=rF2)                                                                        # the same statement read twice
    evidence(a_f8, utterance=utter('Yes, that is the July payment.', '2026-07-12T09:00:00'))
    r_f8 = rem(Of, '2026-07-31')
    a8 = next(a for a in pm(r_f8, pf8)['acknowledgments'] if a['claim'] == a_f8.id)
    check('Dc8 (Ms15 - multiplicity is not strength): two readings of Chase\'s statement + Rob\'s acceptance -> discharged once; three origins listed, one knowing origin twice, no count and no lift',
          pm(r_f8, pf8)['station'] == db.STATION_DISCHARGED and len(a8['origins']) == 3
          and [o['strength'] for o in a8['origins']].count(db.STRENGTH_KNOWING) == 2 and a8['strength'] == db.STRENGTH_KNOWING)

    print('\n7c. 7J-F4-F1 (s 7J-F4-F1.8, ruled C for the balance) - the stated series at the CLAIM level: E\'s statement line, read and accepted, is E\'s position\n')
    Os = mint(db.Obligation, 'A loan whose balance arrives only by statement.')
    entitled(chase, Os)
    stated(Os, chase, '$2,588', '2026-03-31', origin=household)                                        # Sb2: Rob's relay, its own claim
    r_s2 = rem(Os, '2026-03-31')
    check('Sb2 (unchanged): Rob alone states the balance -> NO stated position, the existing reason; the relay listed not_knowing - the gate already excluded it; nothing newly manufactured',
          r_s2['stated']['governing'] is None and r_s2['stated']['reason'] == 'no stated position by the entitled party'
          and [c['strength'] for c in r_s2['stated']['claims']] == [db.STRENGTH_NOT_KNOWING])
    _, rS1 = held('h-chase-0331-statement', chase)
    b_s3 = claim(db.BALANCE, reading=rS1, as_of='2026-03-31', content='$2,588', subject_obligation_id=Os.id)   # the line read: candidate, knowing
    r_s4 = rem(Os, '2026-03-31')
    c_s4 = next(c for c in r_s4['stated']['claims'] if c['claim'] == b_s3.id)
    check('Sb4 (Ob9 holds): the statement line read alone -> a candidate with a knowing origin, never governing',
          r_s4['stated']['governing'] is None and c_s4['state'] == db.CLAIM_CANDIDATE and c_s4['strength'] == db.STRENGTH_KNOWING)
    u_s3 = utter('That is the balance on the March statement.', '2026-04-15T09:00:00')
    evidence(b_s3, utterance=u_s3)                                                                     # Rob's acceptance: established, not_knowing
    r_s3 = rem(Os, '2026-03-31')
    c_s3 = next(c for c in r_s3['stated']['claims'] if c['claim'] == b_s3.id)
    check('Sb3 (MANDATORY - the document path): Rob\'s acceptance on the SAME claim -> established with a knowing origin -> GOVERNS at 2,588 dated 3/31; asserter Chase (the knowing origin\'s party - F6), both origins listed with their own state and class; one entry for the claim',
          r_s3['stated']['governing'] == {'claim': b_s3.id, 'asserter': chase.id, 'as_of': '2026-03-31', 'value': D('2588')}
          and sorted((o['state'], o['strength']) for o in c_s3['origins']) == sorted([(db.CLAIM_CANDIDATE, db.STRENGTH_KNOWING), (db.CLAIM_ESTABLISHED, db.STRENGTH_NOT_KNOWING)])
          and c_s3['entitled'] == db.EFFECT_IN and [c['claim'] for c in r_s3['stated']['claims']].count(b_s3.id) == 1)
    check('Sb11 (Dc11\'s rule, per surface): the acceptance was uttered 4/15; the position is dated by the STATEMENT (3/31) and governs on 3/31 - never by the acceptance',
          r_s3['stated']['governing']['as_of'] == '2026-03-31' and r_s3['figures']['confirmed']['value'] == D('2588'))
    _, rS0 = held('h-chase-0228-statement', chase)
    b_s5 = claim(db.BALANCE, reading=rS0, as_of='2026-02-28', content='$2,788', subject_obligation_id=Os.id)
    evidence(b_s5, utterance=utter('And that is the February balance.', '2026-04-15T09:01:00'))
    p_s5 = pay(Os, '$200', '2026-03-10', household, chase)
    r_s5 = rem(Os, '2026-03-31')
    check('Sb5 (F2): the February statement read + accepted too, a $200 payment between -> S = 3/31 (2,588), S\' = 2/28 (2,788) both from documents; the statement_check RUNS across the payment: 2,588 - (2,788 - 200) = 0',
          r_s5['stated']['governing']['claim'] == b_s3.id and r_s5['stated']['previous']['claim'] == b_s5.id
          and r_s5['diagnostic']['statement_check']['value'] == D('0') and r_s5['diagnostic']['statement_check']['terms']['computed'] == D('2588'))
    u_s7 = utter('$2,500', origin=chase)
    b_s7 = claim(db.BALANCE, utterance=u_s7, as_of='2026-03-31', content='$2,500', subject_obligation_id=Os.id)   # Chase's own utterance, the same date, another figure
    r_s7 = rem(Os, '2026-03-31')
    check('Sb7 (K7): Chase\'s utterance 2,500 and Chase\'s statement read + accepted 2,588, both 3/31 -> two knowing positions at one date -> CONFLICT, none governs; the utterance is not preferred over the document',
          r_s7['stated']['governing'] is None and r_s7['stated']['reason'] == 'conflicting stated positions at 2026-03-31'
          and sorted(c['claim'] for c in r_s7['stated']['conflict']) == sorted([b_s3.id, b_s7.id]))
    retract(u_s7, 'Chase withdraws the 2,500.')                                                          # the conflict cleared
    retract(u_s3, 'I misread the statement.')
    r_s6 = rem(Os, '2026-03-31')
    c_s6 = next(c for c in r_s6['stated']['claims'] if c['claim'] == b_s3.id)
    check('Sb6 (7G-F3 F3\'s rule, per surface): Rob retracts his acceptance -> the claim CONTESTED (the reading still a candidate) -> out of the series; S falls back to the February statement',
          c_s6['state'] == db.CLAIM_CONTESTED and r_s6['stated']['governing']['claim'] == b_s5.id)
    _, rSv = held('h-servicer-0331-statement', servicer)
    b_s8 = claim(db.BALANCE, reading=rSv, as_of='2026-03-31', content='$2,588', subject_obligation_id=Os.id)
    evidence(b_s8, utterance=utter("The servicer's statement shows the same balance.", '2026-04-16T09:00:00'))
    r_s8 = rem(Os, '2026-03-31')
    c_s8 = next(c for c in r_s8['stated']['claims'] if c['claim'] == b_s8.id)
    check('Sb8 (K2 - out of scope, stated so the build cannot drift): the SERVICER\'s statement read + Rob\'s acceptance -> origin S is not the holder -> not_knowing -> NOT in E\'s series; K2\'s balance half untouched',
          c_s8['state'] == db.CLAIM_ESTABLISHED and c_s8['strength'] == db.STRENGTH_NOT_KNOWING and not c_s8['qualifies']
          and r_s8['stated']['governing']['claim'] == b_s5.id)
    _, rRb = held('h-rob-balance-sheet', household)
    b_s10 = claim(db.BALANCE, reading=rRb, as_of='2026-03-31', content='$2,588', subject_obligation_id=Os.id)
    evidence(b_s10, utterance=utter('My spreadsheet says the same.', '2026-04-16T09:01:00'))
    c_s10 = next(c for c in rem(Os, '2026-03-31')['stated']['claims'] if c['claim'] == b_s10.id)
    check('Sb10 (O5): Rob\'s spreadsheet read + Rob\'s acceptance -> both origins Rob -> established, NOT_KNOWING, not in the series; relaying does not launder',
          c_s10['state'] == db.CLAIM_ESTABLISHED and c_s10['strength'] == db.STRENGTH_NOT_KNOWING and not c_s10['qualifies'])
    Os9 = mint(db.Obligation, 'A loan Chase sold on 3/1.')
    entitled(chase, Os9)
    claim(db.ENTITLED_PARTY_OF_ENDED, utterance=utter('Chase sold it 3/1.', origin=chase), as_of='2026-03-01', subject_party_id=chase.id, object_obligation_id=Os9.id)
    _, rS9 = held('h-chase-post-sale-statement', chase)
    b_s9 = claim(db.BALANCE, reading=rS9, as_of='2026-03-31', content='$1,000', subject_obligation_id=Os9.id)
    evidence(b_s9, utterance=utter('That is the March figure.', '2026-04-16T09:02:00'))
    c_s9 = next(c for c in rem(Os9, '2026-03-31')['stated']['claims'] if c['claim'] == b_s9.id)
    check('Sb9 (role at date, preserved): Chase\'s statement dated 3/31, after Chase\'s entitled role ended 3/1, read + accepted -> the origin NOT in effect at the claim\'s date -> not_knowing -> not in the series; the claim level does not replace role-at-date',
          c_s9['state'] == db.CLAIM_ESTABLISHED and c_s9['strength'] == db.STRENGTH_NOT_KNOWING and c_s9['entitled'] == db.EFFECT_NOT and not c_s9['qualifies'])

    Os9b = mint(db.Obligation, 'A loan Chase acquired on 4/1.')
    entitled(chase, Os9b, began='2026-04-01')
    _, rS9b = held('h-chase-pre-acquisition-statement', chase)
    b_s9b = claim(db.BALANCE, reading=rS9b, as_of='2026-03-31', content='$1,000', subject_obligation_id=Os9b.id)
    evidence(b_s9b, utterance=utter('That is the March figure on the new loan.', '2026-04-16T09:03:00'))
    r_s9b = rem(Os9b, '2026-04-30')
    c_s9b = next(c for c in r_s9b['stated']['claims'] if c['claim'] == b_s9b.id)
    check('Sb9\' (role at date, the other direction): Chase\'s statement dated 3/31, before Chase\'s entitled role began 4/1, read + accepted; d = 4/30 when Chase IS in effect -> the role is read at the claim\'s date, not at d -> not_knowing, not in the series',
          c_s9b['strength'] == db.STRENGTH_NOT_KNOWING and not c_s9b['qualifies'] and r_s9b['stated']['governing'] is None)

    print('\n8. The dependency direction and the wiring guard\n')
    check('remaining reads 7F (reach, in_effect) and derived_strength and nothing that resolves, scores or allocates - no level_consistency / chain_strength / aboutness / independence; payment_plan untouched',
          {'reach', 'in_effect', 'derived_strength'} <= (calls_in(db.remaining) | calls_in(db._entitled_at))
          and not ({'level_consistency', 'chain_strength', 'aboutness', 'independence', 'parse_disputes', 'payment_state', 'record_payment'} & calls_in(db.remaining))
          and 'payment_plan' not in __import__('inspect').getsource(db.remaining))
    check('no number in any report is a float; no forbidden key (balance / best / resolved / average / allocation / floor / credit / status / ahead / overdue) anywhere',
          not any(isinstance(v, float) for rep in corpus for _, v in _walk(rep)) and not any(k in FORBIDDEN_KEYS for rep in corpus for k, _ in _walk(rep)))
    before = snapshot()
    for O in (O1, O7, O10, O24):
        rem(O, '2026-12-31')
    check('reading four reports wrote nothing - every row identical; no remaining / paid / discharged / status column exists on any 2.0 table',
          snapshot() == before
          and not any(any(w in c.name for w in ('remaining', 'paid', 'discharged', 'confirmed', 'status'))
                      for cls in (db.Proposition, db.Party, db.Obligation, db.Payment, db.Expense, db.Plan, db.Artefact, db.Reading, db.Utterance, db.EvidentiaryRelationship)
                      for c in cls.__table__.columns))
    check('the 7G wiring guard is executable (AST): remaining and its helpers call no session write method and construct no mapped class',
          all(writes_in(f) == [] for f in (db.remaining, db._entitled_at, db._one_value, db._money)))


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
