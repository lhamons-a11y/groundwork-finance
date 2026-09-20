"""The determination - the executable trace of `gw 2.0/CATALOGUES.md` pass 9D-v (ruled s 9D-v.7, 2026-09-20): one kind,
subject the expense, no object, no role, no knowing relation - KNOWING UNDETERMINED BY DESIGN (9D-F5: a party's reading of
the situation, not a first-hand position); reading_establishes False (a parser determines nothing - 7H); any party may
determine, 7H reports the asserter's roles as facts and constrains nothing; the four names are 7H's vocabulary, opaque to
the kind. The last stand-in of CATALOGUES.md s 1.

What this slice can and cannot exercise
---------------------------------------
    the registry: one entry, no relation, no role, no boundary; the relations still eight; no determiner role   EXERCISED
    De1  D12: Rob determines user_paid_cash -> established, undetermined; 7H: current for Rob's series           EXERCISED
    De2  Mercy determines provider_adjustment -> undetermined; 7H: current for Mercy's series                    EXERCISED
    De3  Rc15: two parties' currents differ -> 7H conflict, none current                                          EXERCISED
    De4  Rc6 / C7: 'denied' as content -> unrecognised, never current; the denial is denial's kind                EXERCISED
    De5  the EOB's 'pending' read -> a CANDIDATE, undetermined, never current (a parser determines nothing)       EXERCISED
    De6  Rc15: a retraction contests the latest; the prior is current again                                       EXERCISED
    De7  an undated determination: accepted by the registry, undetermined; 7H disqualifies (as_of required)      EXERCISED
    De8  the 2 x 2 collapses: every asserter x every name -> undetermined; roles reported, constraining nothing  EXERCISED
    De9  a party-subject or obligation-subject determination refused                                              EXERCISED
    De10 Rc19: unresolved = 0 with no determination -> current None; zero is not a determination                 EXERCISED
    De11 content opaque: 'paid in full' accepted by the kind, unrecognised by 7H                                  EXERCISED
    a role gate on determinations (a consumer's own ruling, if ever); the vocabulary's ownership (7H's)          NOT BUILT

Run:  python tests/test_determination_fixture.py
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
             'payment_amount': 'amount', 'occurred_on': 'occurred_on', 'paid_by': 'paid_by', 'paid_to': 'paid_to',
             'billed': 'billed', 'patient_responsibility': 'patient_responsibility', 'plan_paid': 'plan_paid',
             'determination': 'determination', 'provider_of': 'provider_of', 'insurer_of': 'insurer_of'}
ABSENT = ('determiner_of', 'may_determine', 'determine', 'determination_of', 'current_determination', 'resolve_determination',
          'KNOWING_DETERMINER', 'determination_names_enforced')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_de_')
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}}      # no entry for the determination: undetermined by design

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
        a = db.Artefact(held=True, content_hash=h, as_of='2026-03-10')
        s.add(a)
        s.commit()
        pr = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=a.id, object_party_id=origin_party.id)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utter('origin'))
        r = db.Reading(artefact_id=a.id, reader_process='parser/5', read_at=datetime(2026, 3, 11))
        s.add(r)
        s.commit()
        return a, r

    def st(rel):
        return db.derived_strength(s, rel, KNOWING)

    def determine(X, by, name, as_of, reading=None):
        return claim(db.DETERMINATION, utterance=None if reading else utter(name, origin=by), reading=reading, as_of=as_of, content=name, subject_expense_id=X.id)

    def retract(u, text):
        r = db.Proposition(kind=db.UTTERANCE_RETRACTION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u.id)
        s.add(r)
        s.commit()
        evidence(r, utterance=utter(text, '2026-04-20T09:00:00'))

    def rc(X, d):
        return db.reconciliation(s, X, d, CATALOGUE, KNOWING)

    mercy = mint(db.Party, 'Mercy Hospital.')
    aetna = mint(db.Party, 'Aetna.')
    X = mint(db.Expense, 'The ER visit.')
    claim(db.PROVIDER_OF, utterance=utter('Mercy treated her.'), as_of='2026-02-14', subject_party_id=mercy.id, object_expense_id=X.id)
    claim(db.INSURER_OF, utterance=utter('Aetna insures it.'), as_of='2026-02-14', subject_party_id=aetna.id, object_expense_id=X.id)
    claim(db.BILLED, utterance=utter('$600', origin=mercy), as_of='2026-03-01', content='$600', subject_expense_id=X.id)

    print('\n1. The registry - one entry; no relation, no role, no boundary; the last stand-in\n')
    check('determination is ruled: the expense the subject, no object, symmetric False, reading_establishes False (a parser determines nothing), relational knowing with NO named relation (undetermined by design), not a role, not bounded',
          db.RULED_KINDS[db.DETERMINATION] == {'subject': ('subject_expense_id',), 'object': (), 'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
          and db.registry_violations() == [])
    check('no relation was added for it (the named relations still eight), no determiner role exists, no helper decides or resolves a determination, the four names are not enforced by the registry (content opaque)',
          len(db._KNOWING_RELATIONS) == 8 and 'determiner_of' not in db.RULED_KINDS
          and not any(hasattr(db, n) for n in ABSENT)
          and not _refused(s, db.Proposition(kind=db.DETERMINATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE, subject_expense_id=X.id, content='anything at all', as_of='2026-01-01')))
    check('De9: a party-subject or an obligation-subject determination is refused - the subject is the expense',
          _refused(s, db.Proposition(kind=db.DETERMINATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE, subject_party_id=mercy.id, content='unpaid', as_of='2026-03-01'))
          and _refused(s, db.Proposition(kind=db.DETERMINATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE, subject_obligation_id=1, content='unpaid', as_of='2026-03-01')))
    check('every stand-in of CATALOGUES.md s 1 is now a ruled kind - the roles, E, the stances, the values, the determination; nothing a consumer reads is a stand-in',
          all(k in db.RULED_KINDS for k in ('under_plan', 'entitled_party_of', 'servicer_of', 'provider_of', 'insurer_of', 'insurer_of_plan', 'incurred_by', 'paid_by', 'paid_to', 'drawn_on',
                                              'expense_in_respect_of_plan', 'obligation_in_respect_of_plan', 'payment_in_respect_of_plan',
                                              'acknowledged', 'balance', 'returned', 'billed', 'patient_responsibility', 'plan_paid', 'applied_to_deductible', 'denial', 'adjudication',
                                              'deductible_applied', 'individual_deductible_applied', 'eligibility', 'coverage_ended', 'authorization', 'deductible', 'individual_deductible', 'plan_year',
                                              'amount', 'occurred_on', 'cleared', 'bank_returned_item', 'determination')))

    print('\n2. De1 / De2 / De3 / De8 - any party may determine; knowing undetermined for all; the series are 7H\'s\n')
    e1, d1 = determine(X, household, 'user_paid_cash', '2026-03-20')
    r1 = rc(X, '2026-03-31')
    check('De1 (D12): Rob determines user_paid_cash -> established, KNOWING UNDETERMINED (no relation); 7H: current for Rob\'s series; his roles reported as facts (a household person, not provider or insurer) and constraining nothing',
          st(e1) == db.STRENGTH_UNDETERMINED and r1['determinations']['current'] == {'name': 'user_paid_cash', 'asserters': [household.id], 'claims': [d1.id]}
          and r1['determinations']['claims'][0]['roles']['household_person'] is True)
    e2, d2 = determine(X, mercy, 'provider_adjustment', '2026-03-15')
    check('De2: Mercy determines provider_adjustment -> undetermined too (the provider is not first-hand for a determination - it is a reading of the situation); 7H: Mercy\'s roles reported (provider of X in effect)',
          st(e2) == db.STRENGTH_UNDETERMINED
          and next(c for c in rc(X, '2026-03-31')['determinations']['claims'] if c['claim'] == d2.id)['roles']['provider_of'] == db.EFFECT_IN)
    r3 = rc(X, '2026-03-31')
    check('De3 (Rc15): Rob\'s and Mercy\'s currents differ -> 7H: cross-party CONFLICT, nothing current, both listed; the kind ranks no party and no role',
          r3['determinations']['current'] is None and sorted(c['claim'] for c in r3['determinations']['conflict']) == sorted([d1.id, d2.id]))
    grid = {}
    X8 = mint(db.Expense, 'A visit for the grid.')
    claim(db.INSURER_OF, utterance=utter('Aetna insures it.'), as_of='2026-02-14', subject_party_id=aetna.id, object_expense_id=X8.id)
    for on, o in (('Rob', household), ('Mercy', mercy), ('Aetna', aetna)):
        for name in db.DETERMINATION_NAMES:
            grid[(on, name)] = st(determine(X8, o, name, '2026-03-01')[0])
    check('De8 (the 2 x 2 collapses): every asserter x every name -> UNDETERMINED; the type test had called institutions knowing and the household not - the determination has no holder to ask about',
          set(grid.values()) == {db.STRENGTH_UNDETERMINED} and len(grid) == 12)

    print('\n3. De4 / De5 / De6 / De7 / De10 / De11 - unrecognised; a reading; retraction; undated; zero; opaque content\n')
    X4 = mint(db.Expense, 'The denied visit.')
    claim(db.INSURER_OF, utterance=utter('Aetna insures it.'), as_of='2026-02-14', subject_party_id=aetna.id, object_expense_id=X4.id)
    e4, d4 = determine(X4, aetna, 'denied', '2026-03-01')
    r4 = rc(X4, '2026-03-31')
    check('De4 (Rc6 / C7): Aetna\'s "denied" as a determination\'s content -> the kind accepts it (opaque); 7H: UNRECOGNISED, never current; the denial belongs to the denial kind, not forced into unpaid or pending_claim',
          st(e4) == db.STRENGTH_UNDETERMINED and r4['determinations']['current'] is None
          and next(c for c in r4['determinations']['claims'] if c['claim'] == d4.id)['name'] == db.DETERMINATION_UNRECOGNISED)
    _, r_eob = held('h-eob', aetna)
    e5, d5 = determine(X4, aetna, 'pending_claim', '2026-03-05', reading=r_eob)
    r5 = rc(X4, '2026-03-31')
    check('De5: the EOB\'s "pending" read -> a CANDIDATE, undetermined (a parser determines nothing; reading_establishes False); 7H: never current',
          st(e5) == db.STRENGTH_UNDETERMINED and next(c for c in r5['determinations']['claims'] if c['claim'] == d5.id)['state'] == db.CLAIM_CANDIDATE
          and r5['determinations']['current'] is None)
    X6 = mint(db.Expense, 'A visit Rob determined twice.')
    u6a = utter('pending_claim', origin=household)
    e6a, d6a = claim(db.DETERMINATION, utterance=u6a, as_of='2026-03-01', content='pending_claim', subject_expense_id=X6.id)
    u6b = utter('user_paid_cash', origin=household)
    e6b, d6b = claim(db.DETERMINATION, utterance=u6b, as_of='2026-03-10', content='user_paid_cash', subject_expense_id=X6.id)
    before6 = rc(X6, '2026-03-31')['determinations']['current']
    retract(u6b, 'No - it is still pending.')
    after6 = rc(X6, '2026-03-31')['determinations']['current']
    check('De6 (Rc15): Rob\'s latest (user_paid_cash, 3/10) is current; he retracts it -> contested, it leaves his series; the prior (pending_claim, 3/1) is current again - superseded, never overwritten',
          before6 == {'name': 'user_paid_cash', 'asserters': [household.id], 'claims': [d6b.id]}
          and after6 == {'name': 'pending_claim', 'asserters': [household.id], 'claims': [d6a.id]})
    e7, d7 = determine(X6, household, 'unpaid', None)
    r7 = rc(X6, '2026-03-31')
    check('De7: an undated determination - accepted by the registry (no dated key), undetermined; 7H disqualifies it (as_of required) - the prior stays current',
          st(e7) == db.STRENGTH_UNDETERMINED and r7['determinations']['current'] == after6
          and next(c for c in r7['determinations']['claims'] if c['claim'] == d7.id)['as_of'] is None)
    X10 = mint(db.Expense, 'A visit fully funded, undetermined.')
    r10 = rc(X10, '2026-03-31')
    check('De10 (Rc19): no determination claimed -> current None with the reason; zero unresolved is not a determination and no claim is manufactured',
          r10['determinations']['current'] is None and r10['determinations']['reason'] == 'no determination claimed'
          and s.query(db.Proposition).filter_by(kind=db.DETERMINATION, subject_expense_id=X10.id).count() == 0)
    e11, d11 = determine(X10, household, 'paid in full', '2026-03-20')
    r11 = rc(X10, '2026-03-31')
    check('De11 (s 2.3): "paid in full" - not one of the four - the kind accepts it (content opaque); 7H: unrecognised, never current; the vocabulary is 7H\'s, not the catalogue\'s',
          d11.content == 'paid in full' and r11['determinations']['current'] is None
          and next(c for c in r11['determinations']['claims'] if c['claim'] == d11.id)['recognised'] is False)

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
