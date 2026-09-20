"""obligation_in_respect_of - the executable trace of `gw 2.0/RELATION_SEMANTICS.md` pass C (ruled 2026-09-15).

`obligation_in_respect_of(O, X)` means exactly: the asserting party holds that the subject obligation
is in respect of the object expense - and nothing above that floor. Both participants are established;
direction is fixed by participant type and carries no meaning; no inverse kind; no cardinality; party-
asserted only; carries no amount, share or reconciliation; projects nothing of X onto O; derives
nothing. `arises_from` was rejected as the kind: cause, order and lifecycle it does not carry.

What this slice can and cannot exercise
---------------------------------------
    C1  "that's the ER visit - I owe Mercy for it": three things from one act; none derives another  EXERCISED
    C2  a fully covered visit: X, no O, no relation; PR mints nothing                     EXERCISED
    C3  the mortgage: O, no X, no relation                                                EXERCISED
    C4  one surgery, four obligations (hospital, radiologist, lab, financing) - no merge, no candidate, no sum  EXERCISED
    C5  one balance, two visits - no allocation, no exclusivity                           EXERCISED
    C6  Aetna $412 / Mercy $450 / billed $1,300 - the relation reconciles nothing          EXERCISED
    C7  the pre-service deposit: O minted before X; no temporal order            EXERCISED - PERMANENT
    C8  the CareCredit balance for a Mercy surgery: no creditor/provider mirroring        EXERCISED
    C9  the consolidation loan replaces the CareCredit balance: no transitivity across kinds  EXERCISED
    C10 the EOB's patient responsibility line: candidate at most; mints no O               EXERCISED
    C11 the bill concerns X and concerns O: the relation is not derived                  EXERCISED
    C12 direction fixed by type: no reverse claim exists                                  EXERCISED
    C13 disputed expense: two claims, contested, nothing chosen                           EXERCISED
    C14 retraction: O, X, X' untouched                                                    EXERCISED
    C15 payment toward O (stand-in) and coverage: the relation says nothing               EXERCISED
    C16 bill / charge / responsibility / financed / arises_from are not kinds             EXERCISED (absence)
    C17 endpoint, not projection: O acquires nothing of X                                 EXERCISED
    C18 the semantic floor: the $450 sentence establishes only the relation               EXERCISED
    C19 provider standing: Mercy may assert; it establishes neither endpoint              EXERCISED
    C20 no inverse kind                                                                   EXERCISED (absence)
    C21 traversal enumerates every asserted endpoint with its asserter; no resolver        EXERCISED
    knowing for the relation (which role), the determinations / reconciliation (item 7), passes D-G  NOT BUILT

Run:  python tests/test_obligation_in_respect_of_fixture.py
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


PROJECTED_WORDS = ('nature', 'necessity', 'necessary', 'medical', 'health', 'incurred_on', 'date_of_service', 'provider',
                   'expense_amount', 'patient_responsibility', 'category', 'expense_id', 'underlying')
CONSUMER_NAMES = ('underlying_expense', 'expense_of_obligation', 'obligations_of_expense', 'expense_for', 'expenses_for_obligation',
                  'corresponding_amount', 'reconcile', 'reconciled_amount', 'residual_of', 'allocate', 'allocation_of',
                  'share_of', 'apportion', 'necessity_of', 'nature_of_obligation', 'is_medical', 'is_necessary_care',
                  'inverse_of', 'relations_of', 'Relation', 'RelationBase', 'resolve_relation', 'relation_resolver',
                  'expense_precedes', 'order_of', 'arises_from', 'derive_obligation')
SOURCE_KINDS = ('arises_from', 'obligation_arises_from', 'obligation_arises_from_expense', 'expense_obligation',
                'obligation_bills_for', 'obligation_charges_for', 'obligation_responsibility_for', 'obligation_finances',
                'obligation_for', 'obligation_owed_for', 'obligation_expense_relation', 'billed_for', 'charge_for',
                'financed', 'on_account_of')
INVERSE_KINDS = ('expense_has_obligation', 'expense_generates', 'expense_generates_obligation', 'expense_is_owed',
                 'expense_in_respect_of', 'expense_obligation', 'expense_gives_rise_to')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_oiro_')
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}, 'balance': {'institution'}, 'billed': {'institution'},
               'patient_responsibility': {'institution'}, 'nature': {'person'}, 'entitled_party': {'person', 'institution'},
               'provided_by': {'person', 'institution'}}

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

    def owe(text, when):
        u = utter(text, when)
        o = db.Obligation(minted_by_id=u.id)
        s.add(o)
        s.commit()
        return o, u

    def incur(text, when):
        u = utter(text, when)
        x = db.Expense(minted_by_id=u.id)
        s.add(x)
        s.commit()
        return x, u

    def pay(text, when):
        u = utter(text, when)
        p = db.Payment(minted_by_id=u.id)
        s.add(p)
        s.commit()
        return p, u

    def prop(kind, object_state=db.PARTICIPANT_ESTABLISHED, **slots):
        p = db.Proposition(kind=kind, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=object_state, **slots)
        s.add(p)
        s.commit()
        return p

    def evidence(p, utterance=None, reading=None):
        e = db.EvidentiaryRelationship(proposition_id=p.id,
                                       utterance_id=utterance.id if utterance else None,
                                       reading_id=reading.id if reading else None)
        s.add(e)
        s.commit()
        return e

    def about_o(kind, o, content, utterance=None, reading=None, as_of=None):
        pr = prop(kind, object_state=db.PARTICIPANT_NONE, subject_obligation_id=o.id, content=content, as_of=as_of)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def about_x(kind, x, content, utterance=None, reading=None, as_of=None):
        pr = prop(kind, object_state=db.PARTICIPANT_NONE, subject_expense_id=x.id, content=content, as_of=as_of)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def role_o(kind, party, o, as_of, utterance):
        pr = prop(kind, subject_party_id=party.id, object_obligation_id=o.id, as_of=as_of)
        return evidence(pr, utterance=utterance), pr

    def role_x(kind, party, x, utterance):
        pr = prop(kind, subject_party_id=party.id, object_expense_id=x.id)
        return evidence(pr, utterance=utterance), pr

    def held(h, as_of, origin_party, origin_utt):
        a = db.Artefact(held=True, content_hash=h, as_of=as_of)
        s.add(a)
        s.commit()
        evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=a.id, object_party_id=origin_party.id), utterance=origin_utt)
        return a

    def read(a, process='pdf-parser/5'):
        r = db.Reading(artefact_id=a.id, reader_process=process, read_at=datetime(2026, 3, 12))
        s.add(r)
        s.commit()
        return r

    def concerns(a, utterance, o=None, x=None):
        pr = prop(db.ARTEFACT_CONCERNS, subject_artefact_id=a.id,
                  object_obligation_id=o.id if o else None, object_expense_id=x.id if x else None)
        return evidence(pr, utterance=utterance), pr

    def in_respect_of(o, x, utterance=None, reading=None, content=None, as_of=None):
        pr = prop(db.OBLIGATION_IN_RESPECT_OF, subject_obligation_id=o.id, object_expense_id=x.id, content=content, as_of=as_of)
        return evidence(pr, utterance=utterance, reading=reading), pr

    def rel(o=None, x=None):
        q = s.query(db.Proposition).filter_by(kind=db.OBLIGATION_IN_RESPECT_OF)
        if o is not None:
            q = q.filter_by(subject_obligation_id=o.id)
        if x is not None:
            q = q.filter_by(object_expense_id=x.id)
        return q

    def asserters(o):
        # C21: test-only enumeration of proposition rows + their evidence - every asserted endpoint with
        # its asserter, a reading-backed relation as (X, None). Deliberately NOT a database/model accessor
        # or semantic resolver, and not a canonical traversal API: it selects nothing and hides nothing.
        out = set()
        for pr in rel(o):
            for e in s.query(db.EvidentiaryRelationship).filter_by(proposition_id=pr.id):
                out.add((pr.object_expense_id, e.utterance.origin_party_id if e.utterance_id else None))
        return out

    mercy, u_mercy = mint_party('Mercy Hospital.')
    aetna, u_aetna = mint_party('Aetna, our insurer.')
    synchrony, u_syn = mint_party('Synchrony - the CareCredit card.')
    radiology, u_rad = mint_party('The radiology group.')
    lab, u_lab = mint_party('The lab.')

    print('\n1. The registry entry - exactly as authorised\n')
    check('obligation_in_respect_of is ruled exactly as authorised: obligation subject, expense object, not symmetric, reading never establishes, relational_knowing True, no knowing_relation',
          db.RULED_KINDS[db.OBLIGATION_IN_RESPECT_OF] == {'subject': ('subject_obligation_id',), 'object': ('object_expense_id',),
                                                         'symmetric': False, 'reading_establishes': False, 'relational_knowing': True})
    check('C16 / C20: no source-word kind, no arises_from, no inverse kind, no generic obligation-expense relation exists beside it',
          not any(k in db.RULED_KINDS for k in SOURCE_KINDS + INVERSE_KINDS))
    check('no kind with an expense subject and an obligation object exists - the slots swapped would be a second relation, not this one read backwards',
          not any('subject_expense_id' in r['subject'] and 'object_obligation_id' in r['object'] for r in db.RULED_KINDS.values()))

    print('\n2. C1 - "that\'s the ER visit - I owe Mercy for it": three things from one act\n')
    X, u_X = incur('We took Kim to the ER on Feb 14.', '2026-02-15T09:00:00')
    about_x('date_of_service', X, '2026-02-14', utterance=u_X, as_of='2026-02-14')
    role_x('provided_by', mercy, X, u_X)
    bill = held('h-bill', '2026-03-05', mercy, u_mercy)
    u_owe = utter("That's the ER visit - I owe Mercy for it.", '2026-03-06T09:00:00')
    O = db.Obligation(minted_by_id=u_owe.id)
    s.add(O)
    s.commit()
    concerns(bill, u_owe, x=X)
    e_c1, r_c1 = in_respect_of(O, X, utterance=u_owe)
    about_o('balance', O, '$412', utterance=u_owe, as_of='2026-03-05')
    check('C1: the relation is a claim with two established participants of different types - the obligation the subject, the expense the object',
          r_c1.subject_obligation_id == O.id and r_c1.object_expense_id == X.id
          and r_c1.subject_state == db.PARTICIPANT_ESTABLISHED and r_c1.object_state == db.PARTICIPANT_ESTABLISHED)
    check('C1: one utterance evidences three distinct claims - the bill concerns X, the relation, O\'s balance - and mints O; none is derived from the others',
          s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_owe.id).count() == 3 and O.minted_by_id == u_owe.id)
    check('C1: neither anchor grew - the expense and obligation rows are structure plus the minting pointer',
          {c.name for c in db.Obligation.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and {c.name for c in db.Expense.__table__.columns} == {'id', 'minted_by_id', 'created_at'})

    print('\n3. C2 / C3 - an expense nobody owes for; a debt for nothing incurred\n')
    W, u_W = incur("Kim's wellness visit on 4/2 - fully covered.", '2026-04-03T09:00:00')
    n_obl = s.query(db.Obligation).count()
    about_x('patient_responsibility', W, '$0', utterance=utter('Aetna paid all of it.', '2026-04-20T09:00:00'), as_of='2026-04-20')
    check('C2: an expense with a patient-responsibility stance and no obligation - PR mints no O and relates none',
          s.query(db.Obligation).count() == n_obl and rel(x=W).count() == 0)
    M, u_M = owe('I have a mortgage with Chase.', '2019-06-01T09:00:00')
    n_exp = s.query(db.Expense).count()
    check('C3: an obligation with no expense - nothing manufactures an incurrence for a debt; no relation',
          s.query(db.Expense).count() == n_exp and rel(o=M).count() == 0)

    print('\n4. C4 - one surgery, four obligations: no merge, no candidate, no single creditor, no sum\n')
    S, u_S = incur("Kim's surgery at Mercy on May 3.", '2026-05-04T09:00:00')
    role_x('provided_by', mercy, S, u_S)
    o_h, u_oh = owe("Mercy's surgery bill.", '2026-05-20T09:00:00')
    o_r, u_or = owe("The radiology group's bill for the surgery.", '2026-05-22T09:00:00')
    o_l, u_ol = owe("The lab's bill.", '2026-05-25T09:00:00')
    o_cc, u_occ = owe('The CareCredit balance - I put part of the surgery on it.', '2026-05-10T09:00:00')
    role_o('entitled_party', mercy, o_h, '2026-05-20', u_oh)
    role_o('entitled_party', radiology, o_r, '2026-05-22', u_or)
    role_o('entitled_party', lab, o_l, '2026-05-25', u_ol)
    role_o('entitled_party', synchrony, o_cc, '2026-05-10', u_occ)
    u_four = utter('All four of those are for the surgery.', '2026-05-26T09:00:00')
    for o in (o_h, o_r, o_l, o_cc):
        in_respect_of(o, S, utterance=u_four)
    check('C4: four obligations in respect of one expense - four claims, one utterance; no uniqueness anywhere',
          rel(x=S).count() == 4)
    check('C4: the four remain four identities with four creditors - not merged, no correspondence claim or candidate derived from the shared expense, no single creditor inferred',
          s.query(db.Obligation).filter(db.Obligation.id.in_([o.id for o in (o_h, o_r, o_l, o_cc)])).count() == 4
          and s.query(db.Proposition).filter_by(kind=db.OBLIGATION_CORRESPONDS).count() == 0
          and len({s.query(db.Proposition).filter_by(kind='entitled_party', object_obligation_id=o.id).one().subject_party_id
                   for o in (o_h, o_r, o_l, o_cc)}) == 4)
    check('C4: nothing sums them to "what the surgery cost" and nothing allocates S among them',
          not any(hasattr(db, n) for n in ('total_cost_of', 'cost_of_expense', 'allocate', 'allocation_of', 'apportion', 'share_of')))

    print('\n5. C5 - one balance, two visits: no allocation, no exclusivity\n')
    F, u_F = incur("Kim's follow-up at Mercy on Feb 20.", '2026-02-21T09:00:00')
    u_two = utter('That Mercy balance is the ER visit and the follow-up.', '2026-03-20T09:00:00')
    e_c5, r_c5 = in_respect_of(O, F, utterance=u_two)
    check('C5: one obligation in respect of two expenses - two claims; being in respect of X says nothing against being in respect of F',
          rel(o=O).count() == 2 and rel(o=O, x=X).count() == 1 and rel(o=O, x=F).count() == 1)
    check('C5: no allocation, percentage, amount split or priority - the proposition carries no such column and no helper exists',
          not any(w in c.name for w in ('share', 'portion', 'percent', 'allocation', 'priority', 'amount') for c in db.Proposition.__table__.columns)
          and not any(hasattr(db, n) for n in ('allocate', 'allocation_of', 'share_of', 'apportion', 'split_of')))

    print('\n6. C6 - Aetna $412, Mercy $450, billed $1,300: the relation reconciles nothing\n')
    eob = held('h-eob', '2026-03-10', aetna, u_aetna)
    r_eob = read(eob)
    n_obl, n_rel = s.query(db.Obligation).count(), rel().count()
    about_x('patient_responsibility', X, '$412', reading=r_eob, as_of='2026-03-10')
    about_x('billed', X, '$1,300', reading=r_eob, as_of='2026-03-10')
    check("C6 / C2: a patient-responsibility figure above $0 on X mints no obligation and asserts no relation - the insurer's stance is a claim about the expense",
          s.query(db.Obligation).count() == n_obl and rel().count() == n_rel)
    stmt = held('h-stmt', '2026-04-01', mercy, u_mercy)
    r_stmt = read(stmt)
    about_o('balance', O, '$450', reading=r_stmt, as_of='2026-04-01')
    check('C6: three stances stand - PR $412 on X, billed $1,300 on X, balance $450 on O - beside the relation; nothing flags a mismatch',
          s.query(db.Proposition).filter_by(kind='patient_responsibility', subject_expense_id=X.id).count() == 1
          and s.query(db.Proposition).filter_by(kind='billed', subject_expense_id=X.id).count() == 1
          and s.query(db.Proposition).filter_by(kind='balance', subject_obligation_id=O.id).count() == 2
          and rel(o=O, x=X).count() == 1)
    check('C6: the three temptations are absent - no O-amount-equals-X-amount, no O-amount-equals-PR, no residual-of-X\'s-figures helper or column',
          not any(hasattr(db, n) for n in ('corresponding_amount', 'reconcile', 'reconciled_amount', 'residual_of', 'obligation_amount_from_expense',
                                           'expected_obligation_amount', 'amount_of'))
          and 'amount' not in {c.name for c in db.Proposition.__table__.columns})

    print('\n7. C7 (PERMANENT) / C7\' - no temporal order\n')
    D, u_D = owe('I owe Mercy a $500 deposit for the surgery next month.', '2026-04-02T09:00:00')
    K, u_K = incur("Kim's knee surgery on May 12.", '2026-05-13T09:00:00')
    e_c7, r_c7 = in_respect_of(D, K, utterance=utter('That deposit was for the knee surgery.', '2026-05-13T09:05:00'), as_of='2026-04-01')
    check('C7 (PERMANENT): the obligation was minted before the expense - the relation is accepted; created_at on either anchor is not consulted; no order guard exists',
          D.created_at <= K.created_at and rel(o=D, x=K).count() == 1
          and not any(hasattr(db, n) for n in ('expense_precedes', 'order_of', 'precedes', 'temporal_order', 'validate_order')))
    check("C7: as_of dates the stance, not the expense - X's date of service stays X's own claim",
          r_c7.as_of == '2026-04-01' and s.query(db.Proposition).filter_by(kind='date_of_service', subject_expense_id=K.id).count() == 0)
    L, u_L = owe('A radiology bill arrived fourteen months after the ER visit.', '2027-04-20T09:00:00')
    in_respect_of(L, X, utterance=u_L)
    check("C7': a bill fourteen months later - the same relation; no timing semantics, no 'late'",
          rel(o=L, x=X).count() == 1 and not any(hasattr(db, n) for n in ('late', 'is_late', 'days_after')))

    print('\n8. C8 / C9 - financing: no creditor/provider mirroring; no transitivity across obligation_replaces\n')
    check('C8: the CareCredit balance is in respect of the surgery while Synchrony is E of the balance and Mercy provided the surgery - no mirroring required',
          rel(o=o_cc, x=S).count() == 1
          and s.query(db.Proposition).filter_by(kind='entitled_party', object_obligation_id=o_cc.id).one().subject_party_id == synchrony.id
          and s.query(db.Proposition).filter_by(kind='provided_by', object_expense_id=S.id).one().subject_party_id == mercy.id
          and not any(hasattr(db, n) for n in ('creditor_matches_provider', 'requires_mirroring')))
    about_o('instrument_kind', o_cc, 'deferred-interest card', utterance=u_occ)
    check('C8: instrument kind is a claim on O; it does not change what O is in respect of',
          s.query(db.Proposition).filter_by(kind='instrument_kind', subject_obligation_id=o_cc.id).count() == 1 and rel(o=o_cc).count() == 1)
    o_cons, u_cons = owe('The consolidation loan.', '2026-08-01T09:00:00')
    evidence(prop(db.OBLIGATION_REPLACES, subject_obligation_id=o_cons.id, object_obligation_id=o_cc.id),
             utterance=utter('The consolidation loan paid off the CareCredit balance.', '2026-08-01T09:05:00'))
    check('C9: the consolidation loan replaces the CareCredit balance - one claim; "the loan is in respect of the surgery" is NOT derived across kinds',
          s.query(db.Proposition).filter_by(kind=db.OBLIGATION_REPLACES, subject_obligation_id=o_cons.id).count() == 1
          and rel(o=o_cons).count() == 0)

    print("\n9. C10 / C11 - the EOB's PR line and the bill concerning both: candidates at most; nothing derived\n")
    n_obl = s.query(db.Obligation).count()
    n_rel = rel().count()
    p_line = prop('eob_amount', object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=aetna.id, content='$412 | claim #A77', as_of='2026-03-10')   # 9D-ii F2(i): the EOB line figure, not the ruled stance
    evidence(p_line, reading=r_eob)
    concerns(eob, utter("Aetna's EOB for the ER visit.", '2026-03-11T09:00:00'), x=X)
    check('C10: the EOB\'s PR line is the insurer\'s stance with X as a candidates participant; the EOB concerns X; no obligation minted, no relation asserted',
          s.query(db.Obligation).count() == n_obl and rel().count() == n_rel)
    c_line = prop(db.OBLIGATION_IN_RESPECT_OF, subject_obligation_id=O.id, object_expense_id=X.id, content='matcher: account 4471 on the bill matches the visit')
    e_cand = evidence(c_line, reading=r_stmt)
    check("C10: the matcher's pairing is a reading-sourced candidate - no party behind it; it establishes nothing and is not knowing",
          e_cand.utterance_id is None and e_cand.reading_id == r_stmt.id
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c_line.id).count() == 1
          and not db.RULED_KINDS[db.OBLIGATION_IN_RESPECT_OF]['reading_establishes']
          and db.derived_strength(s, e_cand, KNOWING) == db.STRENGTH_UNDETERMINED)
    n_rel = rel().count()
    concerns(bill, utter("That's Mercy's bill for the debt.", '2026-03-07T09:00:00'), o=O)
    check('C11: the bill concerns X and concerns O - two about-ness claims; no relation row appeared from the document concerning both',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=bill.id).count() == 2 and rel().count() == n_rel)

    print('\n10. C12 / C13 / C14 - direction fixed by type; dispute; retraction\n')
    check('C12: there is no reverse claim - a proposition of this kind with the slots swapped is refused (an expense is not a permitted subject, an obligation not a permitted object)',
          _refused(s, db.Proposition(kind=db.OBLIGATION_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_expense_id=X.id, object_obligation_id=O.id)))
    u_kim = db.Utterance(origin_party_id=kim_party.id, asserted_at='2026-03-21T09:00:00', content="No - that balance is my follow-up, not the ER.")
    s.add(u_kim)
    s.commit()
    in_respect_of(O, F, utterance=u_kim)
    check('C13: Rob says O is in respect of X, Kim says F - claims stand, contested; nothing chooses; no current attribution',
          rel(o=O, x=X).count() >= 1 and rel(o=O, x=F).count() == 2
          and not any(hasattr(db, n) for n in ('current_expense', 'attribution_of', 'resolve_in_respect_of')))
    n_rel = rel().count()
    n_obl, n_exp = s.query(db.Obligation).count(), s.query(db.Expense).count()
    r = prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_two.id)
    evidence(r, utterance=utter("I was wrong - that balance wasn't the follow-up.", '2026-03-22T09:00:00'))
    check('C14: retracting the utterance behind a relation claim leaves O, X, F and every relation row; nothing appears in the other direction',
          rel().count() == n_rel and s.query(db.Obligation).count() == n_obl and s.query(db.Expense).count() == n_exp)

    print('\n11. C15 - payment toward O and coverage: the relation says nothing\n')
    p1, u_p1 = pay('I paid Mercy $412 on 3/20.', '2026-03-20T09:00:00')
    evidence(prop(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_payment_id=p1.id, object_obligation_id=O.id), utterance=u_p1)   # ruled in pass D' (was the toward stand-in)
    about_x('covered', X, 'plan paid $568', utterance=utter('Aetna covered the rest.', '2026-03-21T09:00:00', origin=household), as_of='2026-03-10')
    check('C15: a payment in respect of O (pass D\'s ruled kind; toward rejected) and a coverage stance on X sit beside the relation; nothing marks X paid, O discharged or O covered',
          'toward' not in db.RULED_KINDS and rel(o=O, x=X).count() >= 1
          and not any(hasattr(db, n) for n in ('is_paid', 'paid_for', 'expense_paid', 'is_discharged', 'discharged_by', 'is_covered', 'covered_by'))
          and s.query(db.Proposition).filter_by(kind='covered', subject_obligation_id=O.id).count() == 0)

    print('\n12. C17 / C18 - endpoint, not projection; the semantic floor\n')
    about_x('nature', X, 'necessary care', utterance=utter('The ER visit was necessary care.', '2026-03-23T09:00:00'))
    about_x('nature', X, 'health', utterance=utter('It was health, obviously.', '2026-03-23T09:01:00'))
    check('C17: a consumer may traverse the relation to reach X and read X\'s nature claims there',
          (X.id, household.id) in asserters(O)
          and s.query(db.Proposition).filter_by(kind='nature', subject_expense_id=X.id).count() == 2)
    check('C17: O acquires nothing of X - no nature, necessity, date, provider or amount claim on O appeared; no projection helper; no projected column on the obligation',
          s.query(db.Proposition).filter(db.Proposition.subject_obligation_id == O.id,
                                         db.Proposition.kind.in_(('nature', 'date_of_service', 'provided_by', 'patient_responsibility', 'billed'))).count() == 0
          and s.query(db.Proposition).filter_by(kind='provided_by', object_obligation_id=O.id).count() == 0
          and not any(hasattr(db, n) for n in ('necessity_of', 'nature_of_obligation', 'is_medical', 'is_necessary_care', 'project', 'projected'))
          and not any(any(w in c.name for w in PROJECTED_WORDS) for c in db.Obligation.__table__.columns)
          and not any(hasattr(db.Obligation, w) for w in PROJECTED_WORDS))
    B450, u_450 = owe('The $450 Mercy obligation.', '2026-04-02T09:00:00')
    e_c18, r_c18 = in_respect_of(B450, X, utterance=utter('The $450 Mercy obligation is in respect of the February 14 ER expense.', '2026-04-02T09:05:00'))
    check('C18: the sentence establishes exactly the relation - the row carries no reason, correctness, attribution, enforceability, "the payment obligation" or "final responsibility"; content is opaque',
          rel(o=B450, x=X).count() == 1 and r_c18.content is None
          and not any(w in c.name for w in ('reason', 'cause', 'correct', 'valid', 'enforceable', 'final', 'primary', 'attributable') for c in db.Proposition.__table__.columns)
          and not any(hasattr(db, n) for n in ('why', 'reason_for', 'is_correct', 'is_enforceable', 'final_responsibility', 'payment_obligation_for')))

    print('\n13. C19 / C16 - provider standing; knowing undetermined; vocabulary is content\n')
    u_mercy_says = utter('Statement: balance $450 - for services 02/14.', '2026-04-01T09:00:00', origin=mercy)
    n_obl_before_mercy_assertion = s.query(db.Obligation).count()
    n_exp_before_mercy_assertion = s.query(db.Expense).count()
    e_c19, r_c19 = in_respect_of(O, X, utterance=u_mercy_says, content='for services 02/14')
    check('C19: Mercy (an institution) may assert the relation - a claim with its own evidence; "for services" is content',
          e_c19.utterance.origin_party_id == mercy.id and 'services' in r_c19.content)
    check('C19: the assertion establishes neither endpoint nor any property - O and X were already established; Mercy\'s stance added no creditor role, no amount, no correctness',
          s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_mercy_says.id).count() == 1
          and s.query(db.Proposition).filter_by(kind='entitled_party', object_obligation_id=O.id).count() == 0
          and s.query(db.Obligation).count() == n_obl_before_mercy_assertion
          and s.query(db.Expense).count() == n_exp_before_mercy_assertion)
    check('C19: knowing for the relation is undetermined for every asserter - ruled True with no designated relation; no role of O or X is forced',
          db.derived_strength(s, e_c19, KNOWING) == db.STRENGTH_UNDETERMINED
          and db.derived_strength(s, e_c1, KNOWING) == db.STRENGTH_UNDETERMINED
          and db.derived_strength(s, e_c18, KNOWING) == db.STRENGTH_UNDETERMINED
          and 'knowing_relation' not in db.RULED_KINDS[db.OBLIGATION_IN_RESPECT_OF])
    check('C16: bill / charge / responsibility / balance / financed / arises_from are content or claims about O - none is a kind, none has a row',
          not any(k in db.RULED_KINDS for k in SOURCE_KINDS)
          and s.query(db.Proposition).filter(db.Proposition.kind.in_(SOURCE_KINDS)).count() == 0
          and s.query(db.Proposition).filter(db.Proposition.kind.like('%arise%')).count() == 0)

    print('\n14. C21 - traversal enumerates; no resolver\n')
    found = asserters(O)
    check('C21: from O a query reaches every asserted endpoint with its asserter - X by Rob, X by Mercy, F by Rob, F by Kim - and the reading-sourced candidate separately',
          (X.id, household.id) in found and (X.id, mercy.id) in found and (F.id, household.id) in found and (F.id, kim_party.id) in found
          and (X.id, None) in found)
    check('C21: from X the same query runs the other way - navigation, not an inverse relation',
          {pr.subject_obligation_id for pr in rel(x=X)} >= {O.id, L.id, B450.id})
    check('C21: no accessor selects a privileged endpoint - underlying_expense / expense_of_obligation / obligations_of_expense do not exist; no resolver, no relation base',
          not any(hasattr(db, n) for n in CONSUMER_NAMES))

    print('\n15. Structure - both participants established; cross-type refused; references immutable; absences; audits\n')
    check('both participants must be established identities of the right type - candidates, a party subject, a payment object, an obligation object are refused',
          _refused(s, db.Proposition(kind=db.OBLIGATION_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                     subject_obligation_id=O.id))
          and _refused(s, db.Proposition(kind=db.OBLIGATION_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_party_id=mercy.id, object_expense_id=X.id))
          and _refused(s, db.Proposition(kind=db.OBLIGATION_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_obligation_id=O.id, object_payment_id=p1.id))
          and _refused(s, db.Proposition(kind=db.OBLIGATION_IN_RESPECT_OF, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_obligation_id=O.id, object_obligation_id=M.id)))
    check("the relation's references are immutable - re-pointing a participant is refused; correction is retraction + a new claim",
          (lambda: (r_c1.object_expense_id, setattr(r_c1, 'object_expense_id', F.id), _refused(s, r_c1))[2])()
          and s.get(db.Proposition, r_c1.id).object_expense_id == X.id)
    check('no schema: anchors as their slices left them; both slots pre-existed; no relation table; no generic relation base, resolver, inverse, reconciliation or projection helper',
          'subject_obligation_id' in db.Proposition.SUBJECT_SLOTS and 'object_expense_id' in db.Proposition.OBJECT_SLOTS
          and not any('relation' in t for t in db.Base.metadata.tables)
          and not any(hasattr(db, n) for n in CONSUMER_NAMES))
    check('every audit is empty',
          not db.obligations_without_minting_utterance(s) and not db.expenses_without_minting_utterance(s)
          and not db.payments_without_minting_utterance(s) and not db.parties_without_one_anchor(s))

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
