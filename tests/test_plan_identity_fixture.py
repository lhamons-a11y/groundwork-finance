"""Plan identity - the executable trace of `gw 2.0/PLAN_IDENTITY.md` s7 (PL2, ruled 2026-09-14).

A plan is a Groundwork identity for a coverage arrangement that the household individuates - its
being covered under an insurer's product, not the insurer's product - minted by a Person's
individuating assertion. The minting act establishes only the identity; the insurer, the product,
the terms, the effective period, who is covered and when, the premium, and whether it covered any
expense are claims. The insurer's assertion mints nothing; its product name and plan / group /
member identifiers are content and correspondence evidence; the card, SBC and portal are artefacts.

What this slice can and cannot exercise
---------------------------------------
    Pl15 "we have a plan" - minted with NO claims; unknown = absent, not zero   EXERCISED (the decisive case)
    minting: Person-origin only; insurer / employer / bank cannot mint          EXERCISED
    Pl1  the card: an artefact; identifiers content; it concerns P              EXERCISED
    Pl2  the SBC: P-subject lines from the reading; P-world terms take P        EXERCISED
    Pl3  medical and dental both with Aetna: two plans by assertion             EXERCISED
    Pl4  renewal: same P with a new dated term, or a new P; plan year decides nothing  EXERCISED
    Pl4/Pl13 mis-individuation is plan_corresponds; both rows remain            EXERCISED
    Pl5/Pl12 termination, retroactive or not, is a dated claim; P remains       EXERCISED
    Pl7  the premium: an obligation; ties to P only by a party's asserted obligation_in_respect_of_plan (E, 9C)   EXERCISED
    Pl9  no plan_id on the expense; which-plan not built; the one ruled kind is asserted, never derived (E, 9C)   EXERCISED
    Pl11 authorization: the insurer's dated stance about P; no expense exists   EXERCISED
    Pl16 the group number is correspondence evidence, never establishment       EXERCISED
    membership (item 5), plan <-> expense / obligation / payment (item 6)        NOT BUILT (asserted absent)
    accumulators, coverage status, which-plan derivations (item 7)               NOT BUILT (asserted absent)
    the term / authorization catalogue, the resolver, legacy HealthPlan          NOT BUILT

Run:  python tests/test_plan_identity_fixture.py
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


# Everything the collapse would put on the row (PLAN_IDENTITY.md s2) - none of it may be there.
INTRINSIC = ('name', 'product', 'insurer', 'carrier', 'group', 'member', 'plan_id', 'term', 'deductible', 'copay',
             'coinsurance', 'oop', 'premium', 'effective', 'start', 'end', 'period', 'year', 'status', 'active',
             'coverage', 'covered', 'benefit', 'authoriz', 'accumulat', 'person', 'expense')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_plan_')
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
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}, 'sbc_line_figure': {'institution'}}   # deductible / authorization / coverage_ended: ruled stances since 9D-iii - knowing by the plan's insurer's role

    def utter(text, when='2026-01-05T09:00:00', origin=None):
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

    def mint_plan(u):
        p = db.Plan(minted_by_id=u.id)
        s.add(p)
        s.commit()
        return p

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

    def about(kind, plan, content, utterance=None, reading=None, as_of=None):
        p = prop(kind, object_state=db.PARTICIPANT_NONE, subject_plan_id=plan.id, content=content, as_of=as_of)
        return evidence(p, utterance=utterance, reading=reading), p

    def held(h, as_of, origin_party, origin_utt):
        a = db.Artefact(held=True, content_hash=h, as_of=as_of)
        s.add(a)
        s.commit()
        evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=a.id, object_party_id=origin_party.id), utterance=origin_utt)
        return a

    def read(a, process='pdf-parser/5'):
        r = db.Reading(artefact_id=a.id, reader_process=process, read_at=datetime(2026, 1, 20))
        s.add(r)
        s.commit()
        return r

    def line(a, reading, kind, content, party):
        p = prop(kind, object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=party.id, content=content, as_of=a.as_of)
        return p, evidence(p, reading=reading)

    aetna, u_aetna = mint_party('Aetna, our insurer.')
    employer, u_employer = mint_party("Kim's employer.")
    cigna, u_cigna = mint_party('Cigna.')

    print('\n1. Pl15 - "We have a plan": the decisive case; minted with nothing else known\n')
    u_have = utter('We have a health plan through Kim\'s work.')
    P = mint_plan(u_have)
    check('the plan exists under the utterance that minted it, whose origin is a Person',
          P.minted_by is u_have and db.party_foundation(u_have.origin) == 'person')
    check('the anchor is structure plus the pointer and nothing else',
          {c.name for c in db.Plan.__table__.columns} == {'id', 'minted_by_id', 'created_at'})
    check('nothing the collapse would put on the row is there - insurer, product, terms, period, members, premium, status, coverage',
          not any(any(i in c.name for i in INTRINSIC) for c in db.Plan.__table__.columns)
          and not any(hasattr(db.Plan, i) for i in INTRINSIC))
    check('Pl15: no claim of any kind touches P - unknown terms are ABSENT claims, not deductible = 0 and not "no plan"',
          s.query(db.Proposition).filter_by(subject_plan_id=P.id).count() == 0
          and s.query(db.Proposition).filter_by(object_plan_id=P.id).count() == 0
          and s.get(db.Plan, P.id) is not None)
    check('created_at is when the row was written, never an effective date',
          P.created_at.isoformat()[:10] != '2026-01-01')

    print('\n2. Identity authority: the insurer, the employer and the bank cannot mint; they may claim\n')
    u_from_aetna = utter('Enrolled: Aetna Choice POS II, Group 12345, eff. 1/1.', '2026-01-02T09:00:00', origin=aetna)
    check('the insurer\'s enrollment notice cannot mint a plan - the product is the insurer\'s; the plan is the household\'s',
          _refused(s, db.Plan(minted_by_id=u_from_aetna.id)))
    check('nor the employer\'s, nor an institution-origin utterance of any kind',
          _refused(s, db.Plan(minted_by_id=utter('Open enrollment complete.', origin=employer).id))
          and _refused(s, db.Plan(minted_by_id=utter('Premium debited.', origin=cigna).id)))
    check('a plan without a minting utterance, or under a nonexistent one, is refused',
          _refused(s, db.Plan(), (ValueError, IntegrityError)) and _refused(s, db.Plan(minted_by_id=999999), (ValueError, IntegrityError)))
    check('one act may mint two plans; the pointer is not unique',
          (lambda u: (mint_plan(u).id != mint_plan(u).id))(utter('Medical and dental, both through work.')))

    print('\n3. Pl1 / Pl2 / Pl16 - the card and the SBC: artefacts; identifiers content; terms are claims about P\n')
    card = held('h-card', '2026-01-10', aetna, u_aetna)
    r_card = read(card, 'ocr/2')
    n_plans = s.query(db.Plan).count()
    p_card, _ = line(card, r_card, 'identifiers', 'Aetna | Group 12345 | Member W2288 | Kim', aetna)
    check("Pl1: reading the card mints no plan - the insurer's product identifiers are content; encounter minted the artefact and nothing else",
          s.query(db.Plan).count() == n_plans)
    evidence(prop(db.ARTEFACT_CONCERNS, subject_artefact_id=card.id, object_plan_id=P.id), utterance=utter("That's our card for the work plan."))
    check('Pl1: the card is an artefact; the group and member numbers are content of a read line - never an identity or a slot',
          '12345' in p_card.content and p_card.subject_party_id == aetna.id
          and not any(('group' in c.name or 'member' in c.name) for c in db.Proposition.__table__.columns))
    check('Pl1: the card concerns P when Rob says so; the household is knowing for that (minter of the object identity)',
          s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, object_plan_id=P.id).count() == 1
          and db.derived_strength(s, s.query(db.EvidentiaryRelationship).join(db.Proposition)
                                  .filter(db.Proposition.kind == db.ARTEFACT_CONCERNS, db.Proposition.object_plan_id == P.id).one(),
                                  KNOWING) == db.STRENGTH_KNOWING)
    sbc = held('h-sbc', '2026-01-01', aetna, u_aetna)
    r_sbc = read(sbc)
    p_ded_line, e_ded_line = line(sbc, r_sbc, 'sbc_line_figure', '$3,000 individual / $6,000 family', aetna)   # 9D-iii F6(i): the SBC line figure (subject the insurer), not the ruled term
    check('Pl2: the SBC line is a P-subject claim - the insurer\'s statement, P a candidates participant, never established by the reading',
          p_ded_line.object_state == db.PARTICIPANT_CANDIDATES and p_ded_line.subject_plan_id is None
          and e_ded_line.reading_id == r_sbc.id)
    e_ded, p_ded = about(db.DEDUCTIBLE, P, '$3,000 individual / $6,000 family', utterance=utter('Our deductible is 3,000, 6,000 for the family.'), as_of='2026-01-01')
    check('Pl2: the P-world term takes P as its subject - the family deductible has a subject that is neither Kim nor Aetna',
          p_ded.subject_plan_id == P.id and p_ded.subject_party_id is None and p_ded.as_of == '2026-01-01')
    # 9D-iii F4 / F6(iii): the household's "our deductible is 3,000" RELAYS the insurer's term - the household is not the holder,
    # so the type test's `knowing` retires to NOT_KNOWING; the check's meaning (a claim, dated, a party behind it, not a field) stands
    check('the term is a claim, dated, with a party behind it - the household relaying the insurer\'s rule, established and NOT knowing; it is not on the anchor and there is no accessor for it',
          db.derived_strength(s, e_ded, KNOWING) == db.STRENGTH_NOT_KNOWING
          and not any(hasattr(db, n) for n in ('deductible_of', 'plan_terms', 'current_terms', 'terms_of')))
    eob = held('h-eob', '2026-03-10', aetna, u_aetna)
    r_eob = read(eob)
    p_eob_line, _ = line(eob, r_eob, 'eob_amount', '$412 | Group 12345 | claim #A77', aetna)   # 9D-ii F2(i): the EOB line figure, not the ruled stance
    c16 = prop(db.PROPOSITION_CORRESPONDS, subject_proposition_id=p_eob_line.id, object_proposition_id=p_card.id, content='basis: group 12345')
    evidence(c16, reading=r_eob)
    check('Pl16: the same group number on the EOB is reading-sourced evidence for a correspondence candidate - one evidence row, no party, nothing established',
          s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c16.id).count() == 1
          and s.query(db.EvidentiaryRelationship).filter_by(proposition_id=c16.id).one().utterance_id is None
          and s.query(db.Proposition).filter_by(kind=db.ARTEFACT_CONCERNS, subject_artefact_id=eob.id).count() == 0)

    print('\n4. Pl3 - medical and dental, both with Aetna: two plans by assertion, not by content\n')
    D = mint_plan(utter('And we have the dental plan, also Aetna.'))
    check('Pl3: two plans, one insurer, overlapping periods - individuated by two assertions; nothing on either row tells them apart',
          D.id != P.id and s.get(db.Plan, D.id) is not None
          and {c.name for c in db.Plan.__table__.columns} == {'id', 'minted_by_id', 'created_at'})
    about(db.DEDUCTIBLE, D, '$50', utterance=utter('Dental deductible is 50.'), as_of='2026-01-01')
    check('Pl3: each plan carries its own term claims; the terms describe, they do not individuate',
          s.query(db.Proposition).filter_by(kind=db.DEDUCTIBLE, subject_plan_id=P.id).count() == 1
          and s.query(db.Proposition).filter_by(kind=db.DEDUCTIBLE, subject_plan_id=D.id).count() == 1)

    print('\n5. Pl4 / Pl13 - renewal: the household decides; plan year decides nothing; mis-individuation is correspondence\n')
    about(db.DEDUCTIBLE, P, '$3,500 individual / $7,000 family', utterance=utter('Deductible went up to 3,500 this year.', '2027-01-08T09:00:00'), as_of='2027-01-01')
    # Item 7 pass 7J (CONSUMER_DERIVATIONS.md s 7J.7) built `plans_in_effect()` - a read-only fact report over the
    # membership role, choosing no plan; this check once named it as an absence. The absences that still hold are listed.
    check('Pl4: same P, a second dated term claim - two deductible claims about one plan, neither overwritten, no "current" chosen (item 7 plans_in_effect() exists as a read-only report and chooses none)',
          s.query(db.Proposition).filter_by(kind=db.DEDUCTIBLE, subject_plan_id=P.id).count() == 2
          and callable(getattr(db, 'plans_in_effect', None))
          and not any(hasattr(db, n) for n in ('current_deductible', 'plan_state', 'active_plan', 'current_plan', 'primary_plan', 'plan_at')))
    P_new = mint_plan(utter('New plan year - I\'ll treat it as a new plan.', '2027-01-08T09:05:00'))
    c = prop(db.PLAN_CORRESPONDS, subject_plan_id=P_new.id, object_plan_id=P.id, content='basis: same arrangement, renewed')
    evidence(c, utterance=utter('Actually that is the same plan, just renewed.', '2027-02-01T09:00:00'))
    check('Pl4/Pl13: the other choice, corrected later - plan_corresponds; both rows remain; one component on read',
          db.referent(s, P) == (db.REFERENT_CORRESPONDING, sorted([P.id, P_new.id]), [])
          and s.get(db.Plan, P_new.id) is not None)
    check('plan_corresponds is reflexive- and cross-type-refused',
          _refused(s, db.Proposition(kind=db.PLAN_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                     subject_plan_id=P.id, object_state=db.PARTICIPANT_ESTABLISHED, object_plan_id=P.id))
          and _refused(s, db.Proposition(kind=db.PLAN_CORRESPONDS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_plan_id=P.id, object_state=db.PARTICIPANT_ESTABLISHED, object_party_id=aetna.id)))
    check('a plan\'s minting pointer is never re-pointed - correspondence corrects, it never merges',
          (lambda: (P_new.minted_by_id, setattr(P_new, 'minted_by_id', u_have.id), _refused(s, P_new))[2])()
          and s.get(db.Plan, P_new.id).minted_by_id != u_have.id)

    print('\n6. Pl5 / Pl12 - termination is a dated claim; the identity remains\n')
    e_end, p_end = about(db.COVERAGE_ENDED, P, '2026-06-30', utterance=utter('Coverage terminated retroactive to 6/30.', '2026-08-15T09:00:00', origin=aetna), as_of='2026-08-15')
    check('Pl12: the insurer\'s retroactive termination is its dated stance about P (as of 8/15, content 6/30); P is still minted',
          p_end.as_of == '2026-08-15' and '06-30' in p_end.content and e_end.utterance.origin_party_id == aetna.id
          and s.get(db.Plan, P.id) is not None)
    about(db.COVERAGE_ENDED, P, 'disputed - we paid through December', utterance=utter('That is wrong, we paid every month.', '2026-08-16T09:00:00'))
    check('Pl12: the household\'s contrary stance is a second claim; nothing chosen, nothing deleted - identity is not truth or currency',
          s.query(db.Proposition).filter_by(kind=db.COVERAGE_ENDED, subject_plan_id=P.id).count() == 2
          and not any(hasattr(db, n) for n in ('is_active', 'coverage_status', 'plan_status')))
    Q = mint_plan(utter('Switched to Cigna for 2028.', '2027-11-20T09:00:00'))
    check('Pl5: the new plan is a new identity; the old one persists; nothing links them unless a party corresponds them',
          s.get(db.Plan, Q.id) is not None and s.get(db.Plan, P.id) is not None
          and s.query(db.Proposition).filter_by(kind=db.PLAN_CORRESPONDS, subject_plan_id=Q.id).count() == 0)

    print('\n7. Pl11 - authorization: the insurer\'s dated stance about P; no expense exists\n')
    # 9D-iii F6(ii): Pl11 always meant "Aetna, the plan's insurer, is knowing for its authorization"; under the ruled
    # role-at-date relation that is Aetna's insurer_of_plan role on P in the record - added, never inferred
    prov = db.Proposition(kind=db.INSURER_OF_PLAN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                          subject_party_id=aetna.id, object_plan_id=P.id, as_of='2026-01-01')
    s.add(prov)
    s.commit()
    evidence(prov, utterance=utter('Aetna is the insurer for our plan.', '2026-01-02T09:01:00'))
    n_x = s.query(db.Expense).count()
    e_auth, p_auth = about(db.AUTHORIZATION, P, 'MRI, lumbar - approved', utterance=utter('Prior auth approved for the MRI.', '2026-02-10T09:00:00', origin=aetna), as_of='2026-02-10')
    check('Pl11: the authorization is a claim about P by the insurer, dated; it minted no expense - nothing was incurred',
          p_auth.subject_plan_id == P.id and s.query(db.Expense).count() == n_x
          and db.derived_strength(s, e_auth, KNOWING) == db.STRENGTH_KNOWING)
    X = db.Expense(minted_by_id=utter('Kim had the MRI on 2/24.', '2026-02-25T09:00:00').id)
    s.add(X)
    s.commit()
    evidence(prop(db.PROPOSITION_CONCERNS, subject_proposition_id=p_auth.id, object_expense_id=X.id), utterance=utter('That auth was for this MRI.', '2026-02-25T09:05:00'))
    check('Pl11: once the household mints the expense, a party may tie the authorization to it - proposition_concerns, nothing on either anchor',
          s.query(db.Proposition).filter_by(kind=db.PROPOSITION_CONCERNS, subject_proposition_id=p_auth.id, object_expense_id=X.id).count() == 1
          and p_auth.object_expense_id is None)

    print('\n8. Pl7 / Pl9 - the premium and which-plan: identities and relations that are NOT tied here\n')
    prem = db.Obligation(minted_by_id=utter('We owe the $412 premium each month.').id)
    s.add(prem)
    s.commit()
    # Item 9 pass 9C built E's three plan relations (s E.8 pre-authorised these two retirements: the relations now exist;
    # plan_id, which_plan and plan_covers still do not). The absences that hold are what these checks now assert.
    check('Pl7: the premium is an obligation; the only kind that can tie it to P is E\'s obligation_in_respect_of_plan, by a party\'s assertion - none asserted here, so nothing ties it; no premium_for / pays_for kind, no slot',
          s.get(db.Obligation, prem.id) is not None
          and db.OBLIGATION_IN_RESPECT_OF_PLAN in db.RULED_KINDS
          and not any(k in db.RULED_KINDS for k in ('premium_for', 'obligation_for_plan', 'plan_obligation', 'pays_for'))
          and s.query(db.Proposition).filter_by(object_plan_id=P.id).filter(db.Proposition.subject_obligation_id.isnot(None)).count() == 0)
    check('Pl9: the expense carries no plan_id; the one plan <-> expense kind is E\'s expense_in_respect_of_plan (asserted, never derived; no inverse); no covered_by / plan_covers kind; no which-plan accessor',
          not any('plan' in c.name for c in db.Expense.__table__.columns)
          and db.EXPENSE_IN_RESPECT_OF_PLAN in db.RULED_KINDS and db.RULED_KINDS[db.EXPENSE_IN_RESPECT_OF_PLAN]['object'] == ('object_plan_id',)
          and not any(k in db.RULED_KINDS for k in ('covered_by', 'plan_covers', 'expense_plan', 'adjudicated_under', 'plan_covers_expense'))
          and not any(hasattr(db, n) for n in ('plan_of_expense', 'plan_covering', 'which_plan', 'coverage_of')))
    # Item 9 pass 9A built membership as pass F ruled it - `under_plan`, a party -> plan role claim, no slot on the anchor.
    check('membership is built as under_plan (9A) - a claim, never a slot on the anchor; no member_of / covered_under / enrolled_in kind; no member is manufactured here',
          db.UNDER_PLAN in db.RULED_KINDS and not any(k in db.RULED_KINDS for k in ('member_of', 'covered_under', 'membership', 'enrolled_in'))
          and 'members' not in {c.name for c in db.Plan.__table__.columns}
          and s.query(db.Proposition).filter_by(kind=db.UNDER_PLAN, object_plan_id=P.id).count() == 0)

    print('\n9. Absences; audits; the 1.x rows\n')
    check('no schema beyond the anchor and the additive slots; no accumulator, coverage, status or which-plan consumer',
          'plans' in db.Base.metadata.tables
          and {c.name for c in db.Plan.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and not any(hasattr(db, n) for n in ('accumulators', 'deductible_met', 'plan_for_date', 'coverage_on', 'plan_year_of')))
    check('the concerns kinds gained the plan object slot and nothing else; plan_corresponds is symmetric, reading never establishes, no relational knowing',
          'object_plan_id' in db.RULED_KINDS[db.ARTEFACT_CONCERNS]['object']
          and 'object_plan_id' in db.RULED_KINDS[db.PROPOSITION_CONCERNS]['object']
          and db.RULED_KINDS[db.PLAN_CORRESPONDS] == {'subject': ('subject_plan_id',), 'object': ('object_plan_id',),
                                                       'symmetric': True, 'reading_establishes': False, 'relational_knowing': False})
    check('the 1.x HealthPlan and term rows are untouched, unmapped and not decomposed',
          'health_plans' in db.Base.metadata.tables
          and not any(hasattr(db, n) for n in ('plan_for_health_plan', 'backfill_plans', 'decompose_health_plans')))
    check('every audit is empty',
          not db.plans_without_minting_utterance(s) and not db.expenses_without_minting_utterance(s)
          and not db.obligations_without_minting_utterance(s))
    check('the insurer\'s claim still has no identity, slot or kind - by ruling (4b)',
          not any(n in db.Base.metadata.tables for n in ('claims', 'insurance_claims'))
          and not any('claim' in c.name for c in db.Proposition.__table__.columns))

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
