# -*- coding: utf-8 -*-
"""The relational-knowing fixture - the mechanism gate over Kn1-Kn12.

`gw 2.0/RELATIONAL_KNOWING.md` s8 (ruled s9, 2026-09-14):

    A party knows a proposition when it stands, in the record, in the epistemic relation the
    proposition's kind designates, to the participant the kind designates. No other relation to
    any other participant confers knowing. Knowing is derived on read; never stored, never a
    foundation, never asserted directly. It establishes exactly one thing - the strength class
    of an evidentiary relationship: knowing (relation ruled, participant established, party in
    it); not knowing (relation ruled, participant established, party not in it - meaning only
    "not the party the relation identifies"); undetermined (relation unruled, or participant not
    established). Minting does not make the minter knowing for the event's properties (Kn7);
    originating an utterance does not make the origin knowing for its content (Kn5);
    originating an artefact does not make the origin knowing for every kind read from it
    (Kn10); a process is never knowing; holding is custody, not knowledge.

    Knowing is a derived classification of an evidentiary relationship, not an independent fact
    about the party.

Kn7 is a MANDATORY PERMANENT regression case.

What this build can and cannot exercise, stated so greenness is not over-read:

    Kn1  self-retraction knowing; a third party's not_knowing; map not consulted       EXERCISED
    Kn2  P-ack via the entitled party                                                  NOT DERIVABLE - role kind unruled (undetermined via stand-in)
    Kn3  a value read from the EOB: origin's authority (built); adjudicator             origin path EXERCISED; adjudicator NOT DERIVABLE (claim unminted)
    Kn4  concerns kinds by the minter of the identity: knowing; by another: not_knowing EXERCISED
    Kn5  K5 - the utterance origin is not knowing for the relayed value                 EXERCISED (via caller stand-in map)
    Kn6  the servicer relays E's acknowledgment (chain, weakest link)                  NOT BUILT - consumer derivation
    Kn7  minting != knowing: Rob mints his mother's payment; not knowing it occurred   EXERCISED - PERMANENT
    Kn8  one sheet, two kinds, one party knowing for one of them                        EXERCISED (via caller stand-in map)
    Kn9  a process is never knowing                                                     EXERCISED
    Kn10 an artefact's origin not knowing for a kind it did not adjudicate               EXERCISED (via caller stand-in map; the ruled relation is the point)
    Kn11 two knowing parties for one kind - no ranking                                  EXERCISED
    Kn12 knowing and wrong                                                              EXERCISED
    proposition_corresponds - no established relation                                   undetermined - EXERCISED
    the boundary table (knowing / not_knowing / undetermined)                            EXERCISED
    no generic resolver; named relations only                                            EXERCISED

Run:  python tests/test_relational_knowing_fixture.py
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


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_knowing_')
    eng = create_engine(f'sqlite:///{Path(d) / "t.db"}')

    @event.listens_for(eng, 'connect')
    def _fk_on(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA synchronous=OFF')          # throwaway DB: no fsync per commit
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def run(db):
    s = _fresh()
    rob = db.Person(display_name='Rob')
    kim = db.Person(display_name='Kim')
    s.add_all([rob, kim])
    s.commit()
    household, kim_party = rob.party, kim.party
    # An ADVERSARIAL map: for every relational kind it says "everyone is knowing" - and it must not
    # score. For unruled stand-in kinds it is the caller's foundation stand-in, as the ruling allows.
    KNOWING = {db.UTTERANCE_RETRACTION: {'person', 'institution'},
               db.ARTEFACT_CONCERNS: {'person', 'institution'},
               db.PROPOSITION_CONCERNS: {'person', 'institution'},
               db.PROPOSITION_CORRESPONDS: {'person', 'institution'},
               db.ARTEFACT_ORIGIN: {'person', 'institution'},
               'eob_amount': {'institution'}, 'was_health': {'person'}, 'occurred_on': set()}

    def utter(text, when='2026-03-10T09:00:00', origin=None):
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

    def held(h, origin_party, origin_utt):
        a = db.Artefact(held=True, content_hash=h, as_of='2026-02-14')
        s.add(a)
        s.commit()
        evidence(prop(db.ARTEFACT_ORIGIN, subject_artefact_id=a.id, object_party_id=origin_party.id), utterance=origin_utt)
        return a

    def read(a):
        r = db.Reading(artefact_id=a.id, reader_process='pdf-parser/5', read_at=datetime(2026, 3, 11))
        s.add(r)
        s.commit()
        return r

    st = lambda e, m=KNOWING: db.derived_strength(s, e, m)   # noqa: E731

    print('\n1. Kn1 - self-retraction: the designated relation is the subject utterance\'s origin\n')
    u1 = utter('My servicer is Acme.')
    r_self = prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u1.id)
    e_self = evidence(r_self, utterance=utter('I was wrong in March.', '2026-09-01T10:00:00'))
    check('Rob retracting his own utterance derives KNOWING - he is the origin of the subject utterance',
          st(e_self) == db.STRENGTH_KNOWING)
    check('the adversarial foundation map is never consulted for a relational kind: an empty map, or one saying nobody, gives the same answer',
          st(e_self, {}) == db.STRENGTH_KNOWING and st(e_self, {db.UTTERANCE_RETRACTION: set()}) == db.STRENGTH_KNOWING)
    other, _ = mint_party('Some institution.')
    e_other = evidence(prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u1.id),
                       utterance=utter('Their March claim was wrong.', origin=other))
    check('a third party retracting Rob\'s utterance derives NOT KNOWING - not the party the relation identifies',
          st(e_other) == db.STRENGTH_NOT_KNOWING)
    e_kim = evidence(prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u1.id),
                     utterance=utter('Rob was wrong about that.', origin=kim_party))
    check('another HOUSEHOLD member is equally not_knowing - the relation names a party, not a foundation',
          st(e_kim) == db.STRENGTH_NOT_KNOWING)
    check('not_knowing says nothing about what the third party knows - no accessor claims it',
          not any(hasattr(db, n) for n in ('knows', 'is_knowing', 'party_knows', 'knowledge_of')))

    print('\n2. Kn4 - the concerns kinds: knowing by the minter of the identity concerned\n')
    chase, u_chase = mint_party('Chase, my mortgage lender.')
    u_mint = utter('I have a mortgage with Chase.')
    o1 = db.Obligation(minted_by_id=u_mint.id)
    s.add(o1)
    s.commit()
    A = held('h-stmt', chase, u_chase)
    e_c_rob = evidence(prop(db.ARTEFACT_CONCERNS, subject_artefact_id=A.id, object_obligation_id=o1.id),
                       utterance=utter("That's my mortgage statement.", '2026-04-01T09:00:00'))
    e_c_kim = evidence(prop(db.ARTEFACT_CONCERNS, subject_artefact_id=A.id, object_obligation_id=o1.id),
                       utterance=utter("That's Rob's mortgage statement.", '2026-04-01T09:05:00', origin=kim_party))
    check('Rob (who minted O1) asserting "this statement concerns O1" derives KNOWING; Kim asserting it derives NOT KNOWING',
          st(e_c_rob) == db.STRENGTH_KNOWING and st(e_c_kim) == db.STRENGTH_NOT_KNOWING)
    rA = read(A)
    P = prop('eob_amount', object_state=db.PARTICIPANT_CANDIDATES, subject_party_id=chase.id, content='$1,925')
    evidence(P, reading=rA)
    e_pc = evidence(prop(db.PROPOSITION_CONCERNS, subject_proposition_id=P.id, object_obligation_id=o1.id),
                    utterance=utter('That line is the mortgage.', '2026-04-02T09:00:00'))
    check('the same relation for proposition_concerns: the minter of O1 derives KNOWING',
          st(e_pc) == db.STRENGTH_KNOWING)
    e_cand = evidence(prop(db.ARTEFACT_CONCERNS, subject_artefact_id=A.id, object_obligation_id=o1.id,
                           content='basis: 4471'), reading=rA)
    check('a reading-sourced concerns candidate is UNDETERMINED - a reading is never a knowing party',
          st(e_cand) == db.STRENGTH_UNDETERMINED)

    print('\n3. Kn7 - PERMANENT: minting is not knowing\n')
    mother, _ = mint_party('My mother.')
    mercy, _ = mint_party('Mercy Hospital.')
    u_mom = utter('My mother paid Mercy $300 for me on July 1.', '2026-07-02T09:00:00')
    p9 = db.Payment(minted_by_id=u_mom.id)
    s.add(p9)
    s.commit()
    e_occ = evidence(prop('occurred_on', object_state=db.PARTICIPANT_NONE, subject_payment_id=p9.id, as_of='2026-07-01'),
                     utterance=u_mom)
    check('Kn7: Rob minted the payment; his claim that it occurred is NOT knowing - by the ruled role-set relation now (9D-iv): the minter holds no role on the payment',
          st(e_occ) == db.STRENGTH_NOT_KNOWING and p9.minted_by_id == u_mom.id)
    check('Kn7: no named knowing relation maps a minter to knowledge of an event\'s properties - only the about-ness kinds designate the minter',
          set(k for k, r in db.RULED_KINDS.items() if r.get('knowing_relation') == db.KNOWING_MINTER_OF_OBJECT_IDENTITY)
          == {db.ARTEFACT_CONCERNS, db.PROPOSITION_CONCERNS}
          and 'minter' not in db.RULED_KINDS[db.OCCURRED_ON]['knowing_relation'] and 'minter' not in db.RULED_KINDS[db.AMOUNT]['knowing_relation'])   # 9D-iv: the values are ruled; their relation is the role-set, which names no minter
    # 9D-iv (F5, accepted as a change to this permanent case): the mother IS first-hand for the payment's date - by paid_by, when that
    # role is in the record. THIS corpus records no paid_by claim for her, and 9D-iv's F6 fence forbids adding a presupposed role
    # here - so the relation answers NOT_KNOWING for her claim as the record stands: nothing manufactured, nothing inferred from
    # the utterance. The 9D-iv fixture's Va1 shows her knowing where the role is asserted.
    check('Kn7: the mother\'s own claim that she paid on July 1 - with NO paid_by claim for her in this record - is NOT knowing by the role-set relation; the relation answers why she would be first-hand (paid_by) and manufactures nothing from her utterance',
          st(evidence(prop(db.OCCURRED_ON, object_state=db.PARTICIPANT_NONE, subject_payment_id=p9.id, as_of='2026-07-01'),
                      utterance=utter('I paid Mercy on July 1.', origin=mother)), {}) == db.STRENGTH_NOT_KNOWING)

    print('\n4. Kn5 / Kn8 / Kn10 - origin of an utterance or artefact is not knowing for what it relays\n')
    e_relay = evidence(prop('eob_amount', object_state=db.PARTICIPANT_NONE, subject_artefact_id=A.id, content='$412'),
                       utterance=utter('The EOB says $412.', '2026-03-05T18:00:00'))
    check('Kn5: Rob asserting the EOB\'s figure is NOT KNOWING - he originates the utterance, not the adjudication (stand-in: institution only)',
          st(e_relay) == db.STRENGTH_NOT_KNOWING)
    sheet = held('h-sheet', household, utter('My spreadsheet.'))
    r_sheet = read(sheet)
    e_health = evidence(prop('was_health', object_state=db.PARTICIPANT_NONE, subject_artefact_id=sheet.id, content='yes'), reading=r_sheet)
    e_fig = evidence(prop('eob_amount', object_state=db.PARTICIPANT_NONE, subject_artefact_id=sheet.id, content='$412'), reading=r_sheet)
    check('Kn8: one sheet, two kinds - Rob knowing for "it was health", not for the insurer\'s figure (C1 through a document)',
          st(e_health) == db.STRENGTH_KNOWING and st(e_fig) == db.STRENGTH_NOT_KNOWING)
    e_bank_health = evidence(prop('was_health', object_state=db.PARTICIPANT_NONE, subject_artefact_id=A.id, content='yes'), reading=rA)
    check('Kn10: Chase is the origin of the statement and NOT knowing for "was_health" - provenance is not epistemic standing',
          st(e_bank_health) == db.STRENGTH_NOT_KNOWING)

    print('\n5. Kn9 / Kn11 / Kn12 - a process never; two knowing parties, no ranking; knowing and wrong\n')
    check('Kn9: every reading-sourced relational claim is undetermined and no process is a party',
          st(e_cand) == db.STRENGTH_UNDETERMINED
          and s.query(db.Party).filter(db.Party.person_id.is_(None), db.Party.minted_by_id.is_(None)).count() == 0)
    u_r = utter('My servicer is Acme.', '2026-05-01T09:00:00')
    u_k = utter('Rob\'s servicer is Acme.', '2026-05-02T09:00:00', origin=kim_party)
    r1 = prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_r.id)
    r2 = prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u_k.id)
    e_r1 = evidence(r1, utterance=utter('I retract that.', origin=household))
    e_r2 = evidence(r2, utterance=utter('I retract that.', origin=kim_party))
    check('Kn11: two parties each knowing for their own retraction - and nothing ranks them',
          st(e_r1) == db.STRENGTH_KNOWING and st(e_r2) == db.STRENGTH_KNOWING
          and not any(hasattr(db, n) for n in ('rank_knowing', 'strongest', 'best_source')))
    check('Kn12: a knowing claim carries no truth - the strength value is the only output and no column stores it',
          not any(any(v in c.name for v in ('knowing', 'strength', 'truth')) for c in db.Proposition.__table__.columns)
          and not any(any(v in c.name for v in ('knowing', 'strength')) for c in db.EvidentiaryRelationship.__table__.columns))

    print('\n6. The boundary table; proposition_corresponds; no generic resolver\n')
    e_pcorr = evidence(prop(db.PROPOSITION_CORRESPONDS, subject_proposition_id=P.id,
                            object_proposition_id=prop('eob_amount', object_state=db.PARTICIPANT_CANDIDATES,
                                                       subject_party_id=chase.id, content='$1,952').id),
                       utterance=utter('Those two parses are one line.'))
    check('proposition_corresponds has no named relation and derives UNDETERMINED - a correctly fenced unknown, not custody-as-knowledge',
          db.RULED_KINDS[db.PROPOSITION_CORRESPONDS].get('knowing_relation') is None
          and st(e_pcorr) == db.STRENGTH_UNDETERMINED)
    r_none = prop(db.UTTERANCE_RETRACTION, object_state=db.PARTICIPANT_NONE, subject_utterance_id=u1.id)
    check('designated participant not established -> undetermined (a retraction whose subject utterance has no origin party cannot arise; the resolver returns None when the participant is missing)',
          db._designated_origin_of_subject_utterance(s, db.Proposition(kind=db.UTTERANCE_RETRACTION)) is None
          and db._relational_strength(s, db.Proposition(kind=db.UTTERANCE_RETRACTION), household.id,
                                      db.KNOWING_ORIGIN_OF_SUBJECT_UTTERANCE) == db.STRENGTH_UNDETERMINED)
    check('relation not ruled -> undetermined: an unknown relation name resolves to nothing',
          db._relational_strength(s, r_none, household.id, 'some_relation_nobody_ruled') == db.STRENGTH_UNDETERMINED
          and db._relational_strength(s, r_none, household.id, None) == db.STRENGTH_UNDETERMINED)
    # 9B named a third relation for the role kinds (KNOWING_SUBJECT_PARTY); 9D-i a fourth, the role-at-date relation
    # (KNOWING_ENTITLED_PARTY_AT_AS_OF) - three designated-participant resolvers and one that classifies the claimant by role at as_of.
    # 9D-ii applied the role-at-date relation to the provider and the insurer - two more names on the one resolver
    # 9D-iv added the role-set relation (one resolver) - the eighth and last name
    check('the relations are NAMED and finite - eight names (three designated-participant, four role-at-date on one resolver, one role-set), nothing generic',
          set(db._KNOWING_RELATIONS) == {db.KNOWING_ORIGIN_OF_SUBJECT_UTTERANCE, db.KNOWING_MINTER_OF_OBJECT_IDENTITY, db.KNOWING_SUBJECT_PARTY,
                                         db.KNOWING_ENTITLED_PARTY_AT_AS_OF, db.KNOWING_PROVIDER_AT_AS_OF, db.KNOWING_INSURER_AT_AS_OF, db.KNOWING_PLAN_INSURER_AT_AS_OF,
                                         db.KNOWING_ROLE_HOLDER_ON_SUBJECT}
          and not any(hasattr(db, n) for n in ('find_related_party', 'related_parties', 'reachable_parties', 'knowing_party_for')))
    check('every relational kind either names a relation from that table or none - never a bare traversal hint',
          all(r.get('knowing_relation') in (None, *db._KNOWING_RELATIONS) for r in db.RULED_KINDS.values()))
    check('no schema change and every audit empty',
          not any('know' in c.name for m in (db.Proposition, db.EvidentiaryRelationship, db.Party) for c in m.__table__.columns)
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
