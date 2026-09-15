# -*- coding: utf-8 -*-
"""The expense-identity fixture - the build gate over Ex1-Ex12.

`gw 2.0/EXPENSE_IDENTITY.md` s8 (ruled 2026-09-14):

    An expense is a Groundwork event identity for an incurrence that the household individuates
    - a visit, purchase, or service received. Its minting act establishes only the identity. The
    expense anchor does not acquire date, provider, patient, nature, necessity, category, or
    monetary amounts as intrinsic properties. Those remain claims about the expense. The
    household's individuating assertion mints the identity; other parties may assert claims
    about that expense but do not thereby mint it.

    A source's category for a movement does not establish the identity of the thing being
    categorised - nor its nature.

The claim kinds used here (incurred_on, provided_by, incurred_by, nature_health, category,
patient_responsibility, billed) are STAND-INS; only expense_corresponds is ruled.

What this build can and cannot exercise, stated so greenness is not over-read:

    Ex1  one act mints X; date, provider, patient, nature are claims          EXERCISED
    Ex2  a bank line with a category concerns X only when asserted; the
         category mints nothing and establishes no nature                    EXERCISED - Rob's constraint, executable
    Ex3  the EOB concerns X; claim #A77 is content                            EXERCISED
    Ex4  the bill concerns X; the obligation is a separate identity; the
         O <-> X relation -> tests/test_obligation_in_respect_of_fixture.py   EXERCISED (not asserted here)
    Ex5  a fully covered visit: X with no obligation                          EXERCISED
    Ex6  a loan: an obligation with no expense                                EXERCISED
    Ex7  one visit, three bills; or three expenses; correspondence             EXERCISED
    Ex8  the prescription: X minted, the card line concerns it                EXERCISED
    Ex9  the classifier's proposal is a candidate; a party asserts            EXERCISED
    Ex10 two stances on nature; nothing chosen                                EXERCISED
    Ex11 re-identification is retraction + a new claim; X remains             EXERCISED
    Ex12 1.x rows: HealthcareExpense untouched; category_id not re-homed      EXERCISED (absence)
    D1 / D3 acquire their subject                                             EXERCISED
    identity authority != epistemic authority (provider/insurer/bank cannot mint) EXERCISED
    the insurer's claim (ruled: no identity), the relation family, consumers  NOT BUILT
    the plan                                                                  its own slice (PLAN_IDENTITY.md)

Run:  python tests/test_expense_identity_fixture.py
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


INTRINSIC = ('date', 'incurred', 'provider', 'patient', 'person', 'nature', 'health', 'necessity', 'category',
             'amount', 'billed', 'allowed', 'paid', 'responsibility', 'plan', 'claim', 'status', 'merchant')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_expense_')
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
    from sqlalchemy.exc import IntegrityError
    s = _fresh()
    rob = db.Person(display_name='Rob')
    kim = db.Person(display_name='Kim')
    s.add_all([rob, kim])
    s.commit()
    household, kim_party = rob.party, kim.party
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}, 'nature_health': {'person'},
               'patient_responsibility': {'institution'}, 'billed': {'institution'}}

    def utter(text, when='2026-02-15T09:00:00', origin=None):
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

    def mint_expense(u):
        x = db.Expense(minted_by_id=u.id)
        s.add(x)
        s.commit()
        return x

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

    def about(kind, x, content, utterance=None, reading=None, as_of=None):
        p = prop(kind, object_state=db.PARTICIPANT_NONE, subject_expense_id=x.id, content=content, as_of=as_of)
        return evidence(p, utterance=utterance, reading=reading), p

    def role(kind, party, x, utterance):
        p = prop(kind, subject_party_id=party.id, object_expense_id=x.id)
        return evidence(p, utterance=utterance), p

    def held(h, as_of, origin_party, origin_utt):
        a = db.Artefact(held=True, content_hash=h, as_of=as_of)
        s.add(a)
        s.commit()
        evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=a.id, object_party_id=origin_party.id), utterance=origin_utt)
        return a

    def read(a, process='pdf-parser/5'):
        r = db.Reading(artefact_id=a.id, reader_process=process, read_at=datetime(2026, 3, 1))
        s.add(r)
        s.commit()
        return r

    def line(a, reading, kind, content, party):
        p = prop(kind, object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=party.id, content=content, as_of=a.as_of)
        return p, evidence(p, reading=reading)

    mercy, u_mercy = mint_party('Mercy Hospital.')
    aetna, u_aetna = mint_party('Aetna, our insurer.')
    bank, u_bank = mint_party('Our bank.')

    print('\n1. Ex1 - "We took Kim to the ER on Feb 14": one act mints; the rest is claims\n')
    u_er = utter('We took Kim to the ER on Feb 14.')
    X = mint_expense(u_er)
    check('the expense exists under the utterance that minted it, whose origin is a Person',
          X.minted_by is u_er and db.party_foundation(u_er.origin) == 'person')
    check('the anchor is structure plus the pointer and nothing else',
          {c.name for c in db.Expense.__table__.columns} == {'id', 'minted_by_id', 'created_at'})
    check('no intrinsic property lives on the anchor or the model - date, provider, patient, nature, category, amounts are claims',
          not any(any(i in c.name for i in INTRINSIC) for c in db.Expense.__table__.columns)
          and not any(hasattr(db.Expense, i) for i in INTRINSIC))
    e_date, p_date = about('incurred_on', X, None, utterance=u_er, as_of='2026-02-14')
    e_prov, p_prov = role('provided_by', mercy, X, u_er)
    e_who, p_who = role('incurred_by', kim_party, X, u_er)
    e_nat, p_nat = about('nature_health', X, 'yes', utterance=u_er)
    check('the same act evidences date of service, provider, patient and nature - four claims about X, none on the anchor',
          s.query(db.EvidentiaryRelationship).filter_by(utterance_id=u_er.id).count() == 4
          and p_date.as_of == '2026-02-14' and p_prov.subject_party_id == mercy.id and p_who.subject_party_id == kim_party.id)
    check('D1 has its subject: the health classification is a claim with subject X - not a row, not a line',
          p_nat.kind == 'nature_health' and p_nat.subject_expense_id == X.id and p_nat.subject_artefact_id is None)
    check('created_at is when the row was written, never the date of service',
          X.created_at.isoformat()[:10] != '2026-02-14' and p_date.as_of == '2026-02-14')

    print('\n2. Identity authority is not epistemic authority: other parties claim, they do not mint\n')
    u_from_mercy = utter('Service rendered 2/14 to Kim.', '2026-02-20T09:00:00', origin=mercy)
    check('the provider\'s utterance cannot mint an expense',
          _refused(s, db.Expense(minted_by_id=u_from_mercy.id)))
    check('nor the insurer\'s, nor the bank\'s',
          _refused(s, db.Expense(minted_by_id=utter('Claim adjudicated.', origin=aetna).id))
          and _refused(s, db.Expense(minted_by_id=utter('Debit posted.', origin=bank).id)))
    e_mercy_says, _ = about('billed', X, '$1,300', utterance=u_from_mercy)
    check('but the provider may assert a claim ABOUT X (billed $1,300), with its own authority',
          e_mercy_says.utterance.origin_party_id == mercy.id and db.derived_strength(s, e_mercy_says, KNOWING) == db.STRENGTH_KNOWING)
    check('an expense without a minting utterance, or under a nonexistent one, is refused',
          _refused(s, db.Expense(), (ValueError, IntegrityError)) and _refused(s, db.Expense(minted_by_id=999999), (ValueError, IntegrityError)))
    check('one act may mint two expenses; the pointer is not unique',
          (lambda u: (mint_expense(u).id != mint_expense(u).id))(utter('Two visits that week.')))

    print('\n3. Ex2 - the card line with the bank\'s category: content, a candidate at most; it mints nothing\n')
    stmt = held('h-card', '2026-02-28', bank, u_bank)
    r_stmt = read(stmt, 'feed-import/1')
    n_before = s.query(db.Expense).count()
    p_line, e_line = line(stmt, r_stmt, 'movement', 'MERCY HOSPITAL 412.00 | bank category: Medical', bank)
    check('the categorised line mints no expense',
          s.query(db.Expense).count() == n_before)
    check('the bank\'s category is content of the bank\'s statement - no expense or nature claim was created from it',
          'Medical' in p_line.content and s.query(db.Proposition).filter_by(kind='nature_health', subject_expense_id=X.id).count() == 1)
    c_line = prop(db.PROPOSITION_CONCERNS, subject_proposition_id=p_line.id, object_expense_id=X.id)
    evidence(c_line, reading=r_stmt)      # the matcher's candidate (merchant string)
    check('a merchant match is a reading-sourced candidate for proposition_concerns(line, X) - no party behind it',
          s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c_line.id).count() == 1
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c_line.id).one().utterance_id is None)
    evidence(c_line, utterance=utter("That's the ER charge.", '2026-03-02T09:00:00'))
    check('Rob\'s answer ties the line to X; the line itself is unchanged and still names nothing',
          s.get(db.Proposition, p_line.id).object_state == db.PARTICIPANT_CANDIDATES
          and s.get(db.Proposition, p_line.id).object_expense_id is None)

    print('\n4. Ex3 / Ex4 - the EOB and the bill concern X; the obligation is separate; O <-> X is not built\n')
    eob = held('h-eob', '2026-03-10', aetna, u_aetna)
    r_eob = read(eob)
    p_pr, e_pr = line(eob, r_eob, 'patient_responsibility', '$412 | claim #A77', aetna)
    evidence(prop(db.ARTEFACT_CONCERNS, subject_artefact_id=eob.id, object_expense_id=X.id), utterance=utter("Aetna's EOB for the ER visit."))
    check('Ex3: the EOB concerns X; claim #A77 is content of a read line - never an identity or a slot',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, object_expense_id=X.id).count() == 1
          and 'A77' in p_pr.content and not any('claim' in c.name for c in db.Proposition.__table__.columns))
    p_world = prop('patient_responsibility', object_state=db.PARTICIPANT_NONE, subject_expense_id=X.id, content='$412', as_of='2026-03-10')
    evidence(p_world, utterance=utter('Aetna says I owe $412 for the ER.', '2026-03-11T09:00:00'))
    check('D3 has its subject: the P-world value claim takes X; the P-subject line keeps the artefact/party and its candidates',
          p_world.subject_expense_id == X.id and p_pr.subject_party_id == aetna.id and p_pr.object_state == db.PARTICIPANT_CANDIDATES)
    bill = held('h-bill', '2026-03-05', mercy, u_mercy)
    u_owe = utter("That's the ER visit - I owe Mercy for it.", '2026-03-06T09:00:00')
    O = db.Obligation(minted_by_id=u_owe.id)
    s.add(O)
    s.commit()
    evidence(prop(db.ARTEFACT_CONCERNS, subject_artefact_id=bill.id, object_expense_id=X.id), utterance=u_owe)
    check('Ex4: the bill concerns X; the same act mints the obligation O - a separate identity in a separate table',
          O.minted_by_id == u_owe.id and type(O) is not type(X) and O.__tablename__ != X.__tablename__)
    # Item 6 pass C ruled the O <-> X relation as obligation_in_respect_of (RELATION_SEMANTICS.md C.9) and
    # REJECTED arises_from as the kind - so 'arises_from' stays a non-kind by ruling, not by omission; this
    # fixture still asserts no relation here (the household need not assert one) and no accessor exists.
    check('Ex4: the O <-> X relation is ruled elsewhere (obligation_in_respect_of; arises_from rejected) and not asserted here - no arises kind, no claim, no accessor',
          not any(k in db.RULED_KINDS for k in ('arises_from', 'obligation_arises_from_expense', 'expense_obligation'))
          and db.OBLIGATION_IN_RESPECT_OF in db.RULED_KINDS
          and s.query(db.Proposition).filter(db.Proposition.kind.like('%arise%')).count() == 0
          and s.query(db.Proposition).filter_by(kind=db.OBLIGATION_IN_RESPECT_OF).count() == 0
          and not any(hasattr(db, n) for n in ('obligations_of_expense', 'expense_of_obligation', 'underlying_expense')))

    print('\n5. Ex5 / Ex6 / Ex7 - expense without obligation; obligation without expense; granularity is the household\'s\n')
    W = mint_expense(utter('Kim\'s wellness visit on 4/2 - fully covered.'))
    about('patient_responsibility', W, '$0', utterance=utter('Aetna paid all of it.'), as_of='2026-04-20')
    check('Ex5: an expense with no obligation - it exists, it is claimed about, nobody owes anything',
          s.get(db.Expense, W.id) is not None
          and s.query(db.Obligation).count() == 1)   # only the ER obligation
    loan = db.Obligation(minted_by_id=utter('I have a car loan.').id)
    s.add(loan)
    s.commit()
    check('Ex6: an obligation with no expense - nothing incurred as an event',
          s.get(db.Obligation, loan.id) is not None
          and s.query(db.Proposition).filter_by(object_obligation_id=loan.id).count() == 0)
    X_rad = mint_expense(utter('The radiologist\'s reading of Kim\'s scans.'))
    c = prop(db.EXPENSE_CORRESPONDS, subject_expense_id=X_rad.id, object_expense_id=X.id, content='basis: same visit')
    evidence(c, utterance=utter('That was part of the same ER visit.'))
    check('Ex7: two separately minted expenses later said to be one incurrence correspond; both rows remain',
          db.referent(s, X) == (db.REFERENT_CORRESPONDING, sorted([X.id, X_rad.id]), [])
          and s.get(db.Expense, X_rad.id) is not None)
    check('expense_corresponds is reflexive- and cross-type-refused',
          _refused(s, db.Proposition(kind=db.EXPENSE_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_expense_id=X.id, object_state=db.PARTICIPANT_ESTABLISHED, object_expense_id=X.id))
          and _refused(s, db.Proposition(kind=db.EXPENSE_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_expense_id=X.id, object_state=db.PARTICIPANT_ESTABLISHED, object_obligation_id=O.id)))

    print('\n6. Ex8 / Ex9 / Ex10 - the prescription; the classifier\'s proposal; two stances\n')
    Rx = mint_expense(utter("Kim's prescription at CVS on 3/3."))
    p_cvs, _ = line(stmt, r_stmt, 'movement', 'CVS PHARMACY 38.20 | MCC 5912', bank)
    evidence(prop(db.PROPOSITION_CONCERNS, subject_proposition_id=p_cvs.id, object_expense_id=Rx.id), utterance=utter("That's the prescription."))
    check('Ex8: the prescription is an expense Rob minted; the card line concerns it',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, object_expense_id=Rx.id).count() == 1)
    p_prop = prop('nature_health', object_state=db.PARTICIPANT_NONE, subject_expense_id=Rx.id, content='yes (MCC 5912)')
    e_prop = evidence(p_prop, reading=r_stmt)
    check("Ex9: the classifier's MCC proposal is a reading-sourced claim whose authority is the bank's (the artefact's origin), not the classifier's - the bank is not knowing for nature; a process cannot utter",
          db.derived_strength(s, e_prop, KNOWING) == db.STRENGTH_NOT_KNOWING
          and _refused(s, db.Utterance(content='classifier: health'), IntegrityError))
    e_conf = evidence(p_prop, utterance=utter('Yes, that was health.'))
    check('Ex9: a party\'s assertion is what makes it an asserted claim - the same proposition, a second evidence row',
          s.query(db.EvidentiaryRelationship).filter_by(proposition_id=p_prop.id).count() == 2
          and db.derived_strength(s, e_conf, KNOWING) == db.STRENGTH_KNOWING)
    about('category', X, 'Medical', reading=r_stmt)                      # the bank's label, as a candidate stance
    about('category', X, 'dental - not covered', utterance=utter('It was the dentist, not covered.'))
    check('Ex10: two stances on the nature of X - two claims, nothing chosen, no "current category" accessor',
          s.query(db.Proposition).filter_by(kind='category', subject_expense_id=X.id).count() == 2
          and not any(hasattr(db, n) for n in ('current_category', 'category_of', 'classification_of')))

    print('\n7. Ex11 / Ex12 - re-identification is retraction + a new claim; the 1.x rows\n')
    u_tie = s.query(db.Utterance).filter(db.Utterance.content == "That's the ER charge.").one()
    evidence(prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_tie.id),
             utterance=utter("That charge wasn't the ER - it was the follow-up on the 20th."))
    X2 = mint_expense(utter("Kim's follow-up on Feb 20."))
    evidence(prop(db.PROPOSITION_CONCERNS, subject_proposition_id=p_line.id, object_expense_id=X2.id),
             utterance=utter('The 412 charge was the follow-up.'))
    check('Ex11: the tie is retracted and re-asserted; X remains; the line is untouched',
          s.get(db.Expense, X.id) is not None and s.get(db.Proposition, p_line.id).object_expense_id is None
          and s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=p_line.id).count() == 2)
    check('Ex12: HealthcareExpense is untouched and unmapped; Transaction.category_id is not re-homed',
          {c.name for c in db.HealthcareExpense.__table__.columns} == {'id', 'incurred_on', 'created_at'}
          and 'category_id' in {c.name for c in db.Transaction.__table__.columns}
          and not any(hasattr(db, n) for n in ('expense_for_healthcare_expense', 'backfill_expenses', 'rehome_categories')))

    print('\n8. Absences; audits\n')
    check('no schema beyond the anchor and the additive slots; no expense status/state accessor',
          'expenses' in db.Base.metadata.tables
          and not any(hasattr(db, n) for n in ('expense_state', 'is_health', 'expense_total', 'net_cost')))
    # 4b ruled the insurer's claim has no identity and nothing can mint one; the plan is its own
    # identity (4c) with its own slots - the check is narrowed to what stays absent by ruling, and
    # to the one thing 4c forbids on this side: a plan reference on the expense anchor.
    check('the insurer\'s claim has no identity, slot or kind - by ruling, not by omission; the expense carries no plan_id',
          not any(n in db.Base.metadata.tables for n in ('claims', 'insurance_claims'))
          and not any('claim' in c.name for c in db.Proposition.__table__.columns)
          and not any('plan' in c.name for c in db.Expense.__table__.columns))
    check('every audit is empty',
          not db.expenses_without_minting_utterance(s) and not db.obligations_without_minting_utterance(s)
          and not db.evidence_without_one_source(s) and not db.parties_without_one_anchor(s))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    from core import database as db
    run(db)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
