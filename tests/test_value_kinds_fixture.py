"""Values and the bank - the executable trace of `gw 2.0/CATALOGUES.md` pass 9D-iv (ruled s 9D-iv.7, 2026-09-20): `amount`
(on a payment), `occurred_on` (one kind, two permitted subjects - a payment, an expense), `cleared` and `bank_returned_item`
(the bank's stances on a payment), and `drawn_on` - the bank's role, ruled in 9B's form because K6 requires it (a cross-slice
dependency 9D-iv exposed). THE ROLE-SET RELATION: a value is a fact about the thing, not a position; knowing iff the claimant
holds ANY of a set of roles on the claim's subject, read on the roles' established holds stances, UNDATED - a payment ->
{paid_by, paid_to, drawn_on}, an expense -> {provider_of, incurred_by}. No consumer reads a value's strength (_one_value):
nothing here changes a consumer. Kn7 (permanent): the minter holds no role and is not knowing.

What this slice can and cannot exercise
---------------------------------------
    the registry: four value / stance kinds, occurred_on's two subjects, the drawn_on role, the role-set table, one resolver   EXERCISED
    drawn_on on 9B's three points: who may assert, what it establishes (only that), who is knowing                          EXERCISED
    Va1  Pm9 / Kn7: the mother (paid_by recorded) knowing for the date; Rob (the minter) not                                  EXERCISED
    Va2  Rob's own payment - paid_by Rob -> knowing                                                                          EXERCISED
    Va3  K6 / F2: the bank's line read - the bank (drawn_on) knowing for amount and date; never acknowledgment               EXERCISED
    Va4  O5: Rob's spreadsheet read -> not_knowing                                                                          EXERCISED
    Va5  the expense's date: the provider and the incurrer knowing; Rob not; _one_value disputed                            EXERCISED
    Va6  Pm12: a bank line about nothing paid mints nothing                                                                  EXERCISED
    Va7  two amounts by the payer -> both knowing; _one_value disputed; 7G: amount disputed                                  EXERCISED
    Va8  F1: an undated amount -> knowing by the role-set; undated is the value's normal state                               EXERCISED
    Va9  F3: occurred_on on an expense and on a payment - one kind, the set by subject type                                  EXERCISED
    Va10 F4 / Dg3: cleared by the bank -> knowing; 7G's station unmoved (K6)                                                 EXERCISED
    Va11 F6: the bank line with the bank as subject refused under the ruled names                                           EXERCISED
    Va12 the 2 x 2 on p: origin {the payer, a stranger} x kind {amount, occurred_on}                                         EXERCISED
    the composition fence: no role reached through the attachment; the entitled party is not in the set                     EXERCISED
    the determination (9D-v); candidate generation; the bank line's own kind                                                NOT BUILT

Run:  python tests/test_value_kinds_fixture.py
"""
import sys
import tempfile
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL = [], []


def check(name, condition):
    (PASS if condition else FAIL).append(name)
    print(('  OK    ' if condition else '  FAIL  ') + name)


CATALOGUE = {'acknowledgment': 'acknowledged', 'entitled_party': 'entitled_party_of', 'balance': 'balance',
             'payment_amount': 'amount', 'occurred_on': 'occurred_on', 'paid_by': 'paid_by', 'paid_to': 'paid_to'}
ABSENT = ('amount_of', 'date_of', 'value_of', 'bank_of', 'account_bank', 'is_cleared', 'cleared_on', 'minter_knowing', 'ROLE_SET_AT_AS_OF')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_vk_')
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
    kim = db.Person(display_name='Kim')
    s.add_all([rob, kim])
    s.commit()
    household, kim_party = rob.party, kim.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}}      # no entry for any 9D-iv kind: knowing is the registry's

    def utter(text, when='2026-03-03T09:00:00', origin=None):
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
        return evidence(pr, utterance=utterance, reading=reading), pr

    def held(h, origin_party):
        a = db.Artefact(held=True, content_hash=h, as_of='2026-03-31')
        s.add(a)
        s.commit()
        pr = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=a.id, object_party_id=origin_party.id)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utter('origin'))
        r = db.Reading(artefact_id=a.id, reader_process='parser/5', read_at=datetime(2026, 4, 2))
        s.add(r)
        s.commit()
        return a, r

    def st(rel):
        return db.derived_strength(s, rel, KNOWING)

    def role(kind, party, obj_slot, thing, as_of='2026-03-01', origin=None, reading=None):
        return claim(kind, utterance=None if reading else utter(f'{kind}', origin=origin), reading=reading, as_of=as_of,
                     subject_party_id=party.id, **{obj_slot: thing.id})

    def value(kind, slot, thing, content=None, as_of=None, origin=None, reading=None):
        return claim(kind, utterance=None if reading else utter(content or as_of or kind, origin=origin), reading=reading, as_of=as_of,
                     content=content, **{slot: thing.id})

    chase = mint(db.Party, 'Chase, the mortgage holder.')
    bank = mint(db.Party, 'Bank B, our checking account.')
    mercy = mint(db.Party, 'Mercy Hospital.')
    mother = mint(db.Party, "Rob's mother.")
    stranger = mint(db.Party, 'A party with no role on anything.')
    O = mint(db.Obligation, 'The mortgage.')
    role(db.ENTITLED_PARTY_OF_BEGAN, chase, 'object_obligation_id', O, as_of='2026-01-01')

    print('\n1. The registry - four kinds, two subjects on one, the bank\'s role, the role-set, one resolver\n')
    check('amount, cleared, bank_returned_item on a payment; occurred_on on a payment OR an expense (one kind, two permitted subjects - F3); no object; reading_establishes True; all by the role-set relation; none a role',
          db.RULED_KINDS[db.AMOUNT] == {'subject': ('subject_payment_id',), 'object': (), 'symmetric': False, 'reading_establishes': True, 'relational_knowing': True, 'knowing_relation': db.KNOWING_ROLE_HOLDER_ON_SUBJECT}
          and db.RULED_KINDS[db.OCCURRED_ON]['subject'] == ('subject_payment_id', 'subject_expense_id') and db.RULED_KINDS[db.OCCURRED_ON]['knowing_relation'] == db.KNOWING_ROLE_HOLDER_ON_SUBJECT
          and all(db.RULED_KINDS[k]['subject'] == ('subject_payment_id',) and db.RULED_KINDS[k]['knowing_relation'] == db.KNOWING_ROLE_HOLDER_ON_SUBJECT for k in (db.CLEARED, db.BANK_RETURNED_ITEM))
          and not any(db.RULED_KINDS[k].get('role') for k in (db.AMOUNT, db.OCCURRED_ON, db.CLEARED, db.BANK_RETURNED_ITEM))
          and db.registry_violations() == [])
    check('drawn_on is a ROLE in 9B\'s form - party subject, payment object, holds-only (no boundary), KNOWING_SUBJECT_PARTY, a reading never establishes it; the tenth role kind',
          db.RULED_KINDS[db.DRAWN_ON] == {'subject': ('subject_party_id',), 'object': ('object_payment_id',), 'symmetric': False, 'reading_establishes': False,
                                          'relational_knowing': True, 'role': True, 'knowing_relation': db.KNOWING_SUBJECT_PARTY}
          and not any(r.get('of') == db.DRAWN_ON for r in db.RULED_KINDS.values())
          and len([k for k, r in db.RULED_KINDS.items() if r.get('role')]) == 10)
    check('the role-set relation: one resolver, the eighth named relation; the set by the subject\'s type - a payment {paid_by, paid_to, drawn_on}, an expense {provider_of, incurred_by}; the minter and the entitled party in neither; no dated variant; no value accessor',
          db._KNOWING_RELATIONS[db.KNOWING_ROLE_HOLDER_ON_SUBJECT] is db._role_holder_on_subject and len(db._KNOWING_RELATIONS) == 8
          and db._ROLE_SET == {'payment': (db.PAID_BY, db.PAID_TO, db.DRAWN_ON), 'expense': (db.PROVIDER_OF, db.INCURRED_BY)}
          and db.KNOWING_ROLE_HOLDER_ON_SUBJECT not in db._ROLE_AT_AS_OF
          and not any(hasattr(db, n) for n in ABSENT))

    print('\n2. drawn_on on 9B\'s three points\n')
    p = mint(db.Payment, 'The March mortgage payment, $1,412.')
    role(db.PAID_BY, household, 'object_payment_id', p)
    role(db.PAID_TO, chase, 'object_payment_id', p)
    e_d, d_claim = role(db.DRAWN_ON, bank, 'object_payment_id', p)                                     # the household asserts it
    e_d2, _ = role(db.DRAWN_ON, bank, 'object_payment_id', p, origin=bank)                            # the bank asserts its own
    _, r_stmt = held('h-bank-statement', bank)
    e_d3, d3 = role(db.DRAWN_ON, bank, 'object_payment_id', p, reading=r_stmt)                        # the statement line read
    check('who may assert: the household (established, NOT knowing - the subject party is the bank) and the bank as a party (established, KNOWING for its own role - Kn12); the statement line read -> a CANDIDATE (a reading never establishes a role)',
          st(e_d) == db.STRENGTH_NOT_KNOWING and st(e_d2) == db.STRENGTH_KNOWING and st(e_d3) == db.STRENGTH_UNDETERMINED
          and [x['state'] for x in db.reach(s, bank, db.DRAWN_ON)['endpoints'] if x['claim'] == d3.id] == [db.CLAIM_CANDIDATE])
    snap = [(r.id, r.kind) for r in s.query(db.Proposition).order_by(db.Proposition.id).all()]
    db.reach(s, bank, db.DRAWN_ON)
    check('what it establishes: ONLY that the payment was drawn on the bank\'s account for the payer - no amount, no date, no clearance, no acknowledgment claim exists or is minted by it; nothing written by reading the role',
          d_claim.content is None and not any(r.kind in (db.AMOUNT, db.OCCURRED_ON, db.CLEARED, db.ACKNOWLEDGED) for r in s.query(db.Proposition).all())
          and [(r.id, r.kind) for r in s.query(db.Proposition).order_by(db.Proposition.id).all()] == snap)
    check('the registry refuses drawn_on with a payment subject, and a drawn_on boundary (holds-only, no bounds)',
          _refused(s, db.Proposition(kind=db.DRAWN_ON, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_payment_id=p.id, object_party_id=bank.id, as_of='2026-03-01'))
          and 'drawn_on_began' not in db.RULED_KINDS and 'drawn_on_ended' not in db.RULED_KINDS)

    print('\n3. Va2 / Va3 / Va4 / Va7 / Va8 / Va12 - the payment\'s amount and date: payer, payee, the bank; the minter and a stranger\n')
    claim(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, utterance=utter('toward the mortgage'), subject_payment_id=p.id, object_obligation_id=O.id)
    e_a, a1 = value(db.AMOUNT, 'subject_payment_id', p, content='$1,412', origin=household)
    e_o, o1 = value(db.OCCURRED_ON, 'subject_payment_id', p, as_of='2026-03-05', origin=household)
    check('Va2 / Va8: Rob states his own payment\'s amount (UNDATED - the value\'s normal state) and date; Rob holds paid_by -> KNOWING for both; the amount\'s missing as_of is not a defect',
          st(e_a) == db.STRENGTH_KNOWING and st(e_o) == db.STRENGTH_KNOWING and a1.as_of is None)
    e_a_bank, a_bank = value(db.AMOUNT, 'subject_payment_id', p, content='$1,412', reading=r_stmt)
    e_o_bank, _ = value(db.OCCURRED_ON, 'subject_payment_id', p, as_of='2026-03-05', reading=r_stmt)
    e_c_bank, c_bank = value(db.CLEARED, 'subject_payment_id', p, content='CHASE MTG 3/5 -1,412.00', as_of='2026-03-06', reading=r_stmt)
    rem = db.remaining(s, O, '2026-03-31', CATALOGUE, KNOWING)
    pm = next(x for x in rem['payments'] if x['payment'] == p.id)
    check('Va3 (K6 / F2): the bank\'s statement line read - amount, date and cleared: CANDIDATES in state, KNOWING in strength (the origin holds drawn_on on p - the bank CAN know the household\'s money left); 7G: the value is Rob\'s established one, the reading listed as a candidate; cleared NOT read - attached_unacknowledged',
          st(e_a_bank) == db.STRENGTH_KNOWING and st(e_o_bank) == db.STRENGTH_KNOWING and st(e_c_bank) == db.STRENGTH_KNOWING
          and [c['state'] for c in pm['amount']['claims'] if c['claim'] == a_bank.id] == [db.CLAIM_CANDIDATE]
          and [c['state'] for c in pm['amount']['claims'] if c['claim'] == a1.id] == [db.CLAIM_ESTABLISHED]
          and pm['amount']['value'] == D('1412') and pm['occurred_on']['value'] == '2026-03-05' and pm['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED)
    _, r_sheet = held('h-rob-spreadsheet', household)
    e_a_sheet, _ = value(db.AMOUNT, 'subject_payment_id', p, content='$1,412', reading=r_sheet)
    check('Va4 (O5): Rob\'s spreadsheet with the same figure, read -> the origin is the household, which holds paid_by -> KNOWING (Rob paid it) - and a stranger\'s document would not be; relaying does not launder, but the payer\'s own sheet is the payer\'s',
          st(e_a_sheet) == db.STRENGTH_KNOWING)
    _, r_str = held('h-stranger-doc', stranger)
    e_a_str, _ = value(db.AMOUNT, 'subject_payment_id', p, content='$1,412', reading=r_str)
    grid = {}
    for on, o in (('payer', household), ('stranger', stranger)):
        grid[(on, 'amount')] = st(value(db.AMOUNT, 'subject_payment_id', p, content='$1,412', origin=o)[0])
        grid[(on, 'occurred_on')] = st(value(db.OCCURRED_ON, 'subject_payment_id', p, as_of='2026-03-05', origin=o)[0])
    check('Va12 (the 2 x 2 on p): (payer, amount) knowing · (payer, date) knowing · (stranger, ·) NOT_KNOWING; a stranger\'s document read -> NOT_KNOWING; the type test called an institution knowing and a person not - the role-set asks who holds a role on p',
          grid == {('payer', 'amount'): db.STRENGTH_KNOWING, ('payer', 'occurred_on'): db.STRENGTH_KNOWING,
                   ('stranger', 'amount'): db.STRENGTH_NOT_KNOWING, ('stranger', 'occurred_on'): db.STRENGTH_NOT_KNOWING}
          and st(e_a_str) == db.STRENGTH_NOT_KNOWING)
    e_a2, _ = value(db.AMOUNT, 'subject_payment_id', p, content='$1,421', origin=household)
    rem7 = db.remaining(s, O, '2026-03-31', CATALOGUE, KNOWING)
    check('Va7: the payer states a second, different amount -> both KNOWING; _one_value: disputed -> 7G\'s amount undetermined with the reason; the relation grades who may know, the consumer never chooses',
          st(e_a2) == db.STRENGTH_KNOWING and next(x for x in rem7['payments'] if x['payment'] == p.id)['amount']['value'] is None
          and next(x for x in rem7['payments'] if x['payment'] == p.id)['amount']['reason'] == 'disputed')
    e_ent, _ = value(db.AMOUNT, 'subject_payment_id', p, content='$1,412', origin=chase)
    p_svc = mint(db.Payment, 'A payment to the servicer, attached to the mortgage.')
    role(db.PAID_BY, household, 'object_payment_id', p_svc)
    role(db.PAID_TO, mint(db.Party, 'BillCo, the servicer.'), 'object_payment_id', p_svc)
    claim(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, utterance=utter('toward the mortgage'), subject_payment_id=p_svc.id, object_obligation_id=O.id)
    e_fence, _ = value(db.AMOUNT, 'subject_payment_id', p_svc, content='$5', origin=chase)
    check('the composition fence and the set\'s edge: Chase is the PAYEE of p (paid_to) -> knowing for its amount by that role; on p_svc - paid to the servicer, ATTACHED to O where Chase is the entitled party - Chase is NOT_KNOWING: the entitled-party role is not in the set and is not reached through the attachment',
          st(e_ent) == db.STRENGTH_KNOWING and st(e_fence) == db.STRENGTH_NOT_KNOWING)

    print('\n4. Va1 (Pm9 / Kn7) - the mother paid; the minter is not knowing\n')
    u_mom = utter('My mother paid Mercy $300 for me on July 1.', '2026-07-02T09:00:00')
    p9 = db.Payment(minted_by_id=u_mom.id)
    s.add(p9)
    s.commit()
    pr_o = db.Proposition(kind=db.OCCURRED_ON, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE, subject_payment_id=p9.id, as_of='2026-07-01')
    s.add(pr_o)
    s.commit()
    e_rob_o = evidence(pr_o, utterance=u_mom)
    e_mom_o, _ = value(db.OCCURRED_ON, 'subject_payment_id', p9, as_of='2026-07-01', origin=mother)
    before = st(e_mom_o)
    role(db.PAID_BY, mother, 'object_payment_id', p9, as_of='2026-07-01', origin=mother)
    check('Va1 (Kn7, permanent): Rob minted the payment; his claim that it occurred is NOT knowing (the minter holds no role); the mother\'s own claim is NOT knowing until her paid_by is in the record, then KNOWING - the relation answers why she is first-hand (paid_by), it manufactures nothing from her utterance',
          st(e_rob_o) == db.STRENGTH_NOT_KNOWING and before == db.STRENGTH_NOT_KNOWING and st(e_mom_o) == db.STRENGTH_KNOWING and p9.minted_by_id == u_mom.id)

    print('\n5. Va5 / Va9 - the expense\'s date: the provider and the incurrer; one kind, two subjects\n')
    X = mint(db.Expense, 'The ER visit.')
    role(db.PROVIDER_OF, mercy, 'object_expense_id', X, as_of='2026-02-14')
    role(db.INCURRED_BY, kim_party, 'object_expense_id', X, as_of='2026-02-14')
    e_x_m, _ = value(db.OCCURRED_ON, 'subject_expense_id', X, as_of='2026-02-14', origin=mercy)
    e_x_k, _ = value(db.OCCURRED_ON, 'subject_expense_id', X, as_of='2026-02-14', origin=kim_party)
    e_x_r, _ = value(db.OCCURRED_ON, 'subject_expense_id', X, as_of='2026-02-15', origin=household)
    dates = db._claim_entries(s, db.OCCURRED_ON, db._retracted(s), subject_expense_id=X.id)
    when, why = db._one_value([dict(e, value=(e['as_of'] or e['content'])) for e in dates])
    check('Va5 / Va9: the expense\'s date - Mercy (provider_of) KNOWING, Kim (incurred_by) KNOWING, Rob NOT (no role on X); the same kind as a payment\'s date, the set by the subject\'s type; Rob\'s different date -> _one_value disputed, nothing chosen',
          st(e_x_m) == db.STRENGTH_KNOWING and st(e_x_k) == db.STRENGTH_KNOWING and st(e_x_r) == db.STRENGTH_NOT_KNOWING
          and when is None and why == 'disputed')
    check('Va9 (F3): occurred_on refuses a plan or an obligation subject; a payment and an expense are its two permitted subjects; one catalogue key serves both',
          _refused(s, db.Proposition(kind=db.OCCURRED_ON, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE, subject_obligation_id=O.id, as_of='2026-01-01'))
          and CATALOGUE['occurred_on'] == db.OCCURRED_ON)

    print('\n6. Va6 / Va10 / Va11 - the bank\'s stances; the line\n')
    e_c, c1 = value(db.CLEARED, 'subject_payment_id', p, content='cleared 3/6', as_of='2026-03-06', origin=bank)
    e_ret, _ = value(db.BANK_RETURNED_ITEM, 'subject_payment_id', p, content='RETURNED ITEM 3/8', as_of='2026-03-08', origin=bank)
    e_c_rob, _ = value(db.CLEARED, 'subject_payment_id', p, content='it cleared', as_of='2026-03-06', origin=household)
    rem10 = db.remaining(s, O, '2026-03-31', CATALOGUE, KNOWING)
    check('Va10 (F4 / Dg3): the bank states cleared and a returned item on p - KNOWING through drawn_on; Rob saying "it cleared" is knowing through paid_by (the payer), NOT through any bank line - the bank line is an evidence shape, never a role or a knowing source; 7G reads neither stance: the station is unmoved',
          st(e_c) == db.STRENGTH_KNOWING and st(e_ret) == db.STRENGTH_KNOWING and st(e_c_rob) == db.STRENGTH_KNOWING
          and next(x for x in rem10['payments'] if x['payment'] == p.id)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED)
    n_pay = s.query(db.Payment).count()
    check('Va6 (Pm12): a bank line about nothing paid mints no payment; a value on nothing has no subject and is refused',
          s.query(db.Payment).count() == n_pay
          and _refused(s, db.Proposition(kind=db.CLEARED, subject_state=db.PARTICIPANT_NONE, object_state=db.PARTICIPANT_NONE, content='TRANSFER TO SAVINGS', as_of='2026-08-15')))
    check('Va11 (F6): the bank LINE - the bank as subject, the thing a candidate - is REFUSED under cleared / amount; it keeps its shape under the bank_line stand-in (payment-identity and Ab7 renamed theirs)',
          _refused(s, db.Proposition(kind=db.CLEARED, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=bank.id, content='CHASE MTG 3/5 -1,412.00', as_of='2026-03-05'))
          and _refused(s, db.Proposition(kind=db.AMOUNT, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=bank.id, content='-1,412.00', as_of='2026-03-05'))
          and not _refused(s, db.Proposition(kind='bank_line', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=bank.id, content='CHASE MTG 3/5 -1,412.00', as_of='2026-03-05'))
          and 'bank_line' not in db.RULED_KINDS)

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
