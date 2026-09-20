"""The obligation stances - the executable trace of `gw 2.0/CATALOGUES.md` pass 9D-i (ruled s 9D.7 / s 9D-i.8, 2026-09-19):
`acknowledged`, `balance`, `returned` - P-ack, the entitled party's stated position about a payment or a balance as of a
date; THE MIXED HOLDER SHAPE (the acknowledgment and the return carry their holder as a participant, the balance's holder
is the asserter in role at as_of); the role-at-date relation ruled once here (KNOWING_ENTITLED_PARTY_AT_AS_OF); the
reading path (reading_establishes True = strength through the artefact's established origin, never state, never
discharge); O absent from the acknowledgment; the servicer channel a consumer's read. Ob12's 2 x 2 is the distinction
the relation exists to make.

What this slice can and cannot exercise
---------------------------------------
    the registry: three kinds, two holder forms, one new relation, the flag's meaning                        EXERCISED
    Ob1  K1 / Dg2: E's own acknowledgment -> knowing; 7G discharged                                              EXERCISED
    Ob2  K1 held / Dg2': the parser's reading of E's statement -> candidate in state, KNOWING in strength         EXERCISED
    Ob3  K1 accepted: the reading + Rob's utterance on one claim -> built 7G does not discharge (9D-i-F3)          EXERCISED (recorded)
    Ob4  K2 / Dg4: the servicer's acknowledgment naming E as holder -> not_knowing; not discharged                EXERCISED
    Ob5  K3 / Dg5: S3's own -> knowing for its own, never entitled                                                EXERCISED
    Ob6  K5 / Dg22: Rob relays -> not_knowing                                                                     EXERCISED
    Ob7  Dg21: E's role contested at as_of -> balance undetermined; the ack's holder test is 7G's                  EXERCISED
    Ob8  K2 balance: the servicer's balance -> not_knowing; not in E's series                                     EXERCISED
    Ob9  K1 balance held / Ms1: E's held statement line -> candidate, knowing                                     EXERCISED
    Ob11 K7: two positions by date - G per series (7G's)                                                          EXERCISED
    Ob12 the 2 x 2: party x origin - the type test cannot tell (E, S) from (E, E); the relation can                EXERCISED
    Ob13 F7: undated -> undetermined; never governing                                                              EXERCISED
    Ob14 Dg18: returned - E's shape; not read by 7G; not a non-acknowledgment                                      EXERCISED
    Ob15 F2: the party-subject line refused under the ruled name                                                   EXERCISED
    the composition fence: the ack derives no O; the servicer's roles confer nothing on the ack                    EXERCISED
    Ob10 the portal observed (no artefact); the servicer's balance read by a consumer with O; 7G's F3 question   NOT BUILT

Run:  python tests/test_obligation_stances_fixture.py
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
ABSENT = ('discharge', 'is_discharged', 'acknowledged_by', 'position_of', 'holder_of', 'servicer_knowing', 'entitled_party_of_payment',
          'obligation_of_acknowledgment', 'ack_obligation', 'compose_knowing', 'KNOWING_ROLE_AT_DATE', 'role_at_date_relation')


def _fresh():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    d = tempfile.mkdtemp(prefix='gw_os_')
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
    # the foundation map carries NO entry for the three ruled kinds: their knowing is the registry's
    KNOWING = {db.ARTEFACT_ORIGIN: {'person', 'institution'}}   # amount / occurred_on: ruled values since 9D-iv

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

    def held(h, origin_party, origin_by=None):
        a = db.Artefact(held=True, content_hash=h, as_of='2026-03-31')
        s.add(a)
        s.commit()
        pr = db.Proposition(kind=db.ARTEFACT_ORIGIN, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                            subject_artefact_id=a.id, object_party_id=origin_party.id)
        s.add(pr)
        s.commit()
        evidence(pr, utterance=utter('origin', origin=origin_by))
        r = db.Reading(artefact_id=a.id, reader_process='parser/5', read_at=datetime(2026, 4, 2))
        s.add(r)
        s.commit()
        return a, r

    def st(rel):
        return db.derived_strength(s, rel, KNOWING)

    def ack(holder, p, as_of, origin=None, reading=None):
        return claim(db.ACKNOWLEDGED, utterance=None if reading else utter(f'ack {as_of}', origin=origin or holder), reading=reading,
                     as_of=as_of, subject_party_id=holder.id, object_payment_id=p.id)

    def balance(O, amount, as_of, origin=None, reading=None):
        return claim(db.BALANCE, utterance=None if reading else utter(amount, origin=origin), reading=reading, as_of=as_of, content=amount,
                     subject_obligation_id=O.id)

    def entitled(party, O, began='2026-01-01'):
        claim(db.ENTITLED_PARTY_OF_BEGAN, utterance=utter(f'{began} entitled'), as_of=began, subject_party_id=party.id, object_obligation_id=O.id)

    def pay(O, amount, on):
        p = mint(db.Payment, f'Paid {amount} on {on}.')
        claim('amount', utterance=utter(amount), content=amount, subject_payment_id=p.id)
        claim('occurred_on', utterance=utter(on), as_of=on, subject_payment_id=p.id)
        claim(db.PAID_BY, utterance=utter('paid by'), as_of=on, subject_party_id=household.id, object_payment_id=p.id)
        claim(db.PAID_TO, utterance=utter('paid to'), as_of=on, subject_party_id=chase.id, object_payment_id=p.id)
        claim(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, utterance=utter('toward it'), subject_payment_id=p.id, object_obligation_id=O.id)
        return p

    def rem(O, d):
        return db.remaining(s, O, d, CATALOGUE, KNOWING)

    def pm(rep, p):
        return next(x for x in rep['payments'] if x['payment'] == p.id)

    def snapshot():
        return [(r.id, r.kind, r.subject_party_id, r.subject_obligation_id, r.object_payment_id, r.as_of, r.content)
                for r in s.query(db.Proposition).order_by(db.Proposition.id).all()]

    chase = mint(db.Party, 'Chase.')
    billco = mint(db.Party, 'BillCo, the servicer.')
    s3 = mint(db.Party, 'S3, never authorised.')
    O = mint(db.Obligation, 'The mortgage.')
    entitled(chase, O)
    claim(db.SERVICER_OF, utterance=utter('BillCo services it.'), as_of='2026-01-01', subject_party_id=billco.id, object_obligation_id=O.id)
    balance(O, '$4,000', '2026-03-01', origin=chase)

    print('\n1. The registry - three kinds, two holder forms, one relation ruled once, the flag\'s meaning\n')
    check('acknowledged and returned: the holder an explicit participant (party subject, payment object), KNOWING_SUBJECT_PARTY, reading_establishes True; balance: the obligation the subject, no object, KNOWING_ENTITLED_PARTY_AT_AS_OF, reading_establishes True; none a role, none bounded',
          db.RULED_KINDS[db.ACKNOWLEDGED] == db.RULED_KINDS[db.RETURNED] == {'subject': ('subject_party_id',), 'object': ('object_payment_id',), 'symmetric': False,
                                                                             'reading_establishes': True, 'relational_knowing': True, 'knowing_relation': db.KNOWING_SUBJECT_PARTY}
          and db.RULED_KINDS[db.BALANCE] == {'subject': ('subject_obligation_id',), 'object': (), 'symmetric': False, 'reading_establishes': True,
                                             'relational_knowing': True, 'knowing_relation': db.KNOWING_ENTITLED_PARTY_AT_AS_OF}
          and not any(db.RULED_KINDS[k].get('role') or db.RULED_KINDS[k].get('boundary') for k in (db.ACKNOWLEDGED, db.BALANCE, db.RETURNED))
          and db.registry_violations() == [])
    # 9D-ii applied the relation to the provider and the insurer: two more rows in the table, the same resolver
    check('the role-at-date relation is named per role, its role taken from a table keyed by the name (entitled_party_of here; provider_of / insurer_of since 9D-ii), one resolver; no dated key exists on any entry; no generic resolver, no holder helper, no discharge helper',
          db.KNOWING_ENTITLED_PARTY_AT_AS_OF in db._KNOWING_RELATIONS and db._ROLE_AT_AS_OF[db.KNOWING_ENTITLED_PARTY_AT_AS_OF] == db.ENTITLED_PARTY_OF
          and len({db._KNOWING_RELATIONS[n] for n in db._ROLE_AT_AS_OF}) == 1
          and not any('dated' in r or 'as_of_required' in r for r in db.RULED_KINDS.values())
          and not any(hasattr(db, n) for n in ABSENT))
    check('O is absent from the acknowledgment: no obligation slot on the kind; an acknowledgment carrying an obligation is refused by the registry; the balance refuses a party subject and any object',
          'object_obligation_id' not in db.RULED_KINDS[db.ACKNOWLEDGED]['object'] and 'subject_obligation_id' not in db.RULED_KINDS[db.ACKNOWLEDGED]['subject']
          and _refused(s, db.Proposition(kind=db.ACKNOWLEDGED, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_party_id=chase.id, object_obligation_id=O.id, as_of='2026-03-10'))
          and _refused(s, db.Proposition(kind=db.BALANCE, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_NONE,
                                         subject_party_id=chase.id, content='$1', as_of='2026-03-10'))
          and _refused(s, db.Proposition(kind=db.BALANCE, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                         subject_obligation_id=O.id, object_payment_id=1, content='$1', as_of='2026-03-10')))

    print('\n2. Ob1 / Ob2 / Ob3 - E\'s own statement; E\'s held statement; the accepted reading (F3, recorded)\n')
    p1 = pay(O, '$1,412', '2026-03-05')
    e1, a1 = ack(chase, p1, '2026-03-10')
    r1 = rem(O, '2026-03-31')
    check('Ob1 (K1 / Dg2): Chase\'s own acknowledgment (holder Chase, origin Chase) -> KNOWING; 7G: in effect and knowing -> DISCHARGED; nothing about the foundation map read (no entry exists for the kind)',
          st(e1) == db.STRENGTH_KNOWING and pm(r1, p1)['station'] == db.STATION_DISCHARGED and pm(r1, p1)['acknowledgments'][0]['strength'] == db.STRENGTH_KNOWING
          and db.ACKNOWLEDGED not in KNOWING)
    p2 = pay(O, '$1,412', '2026-04-05')
    _, rS = held('h-chase-statement', chase)
    e2, a2 = ack(chase, p2, '2026-04-10', reading=rS)
    r2 = rem(O, '2026-04-30')
    check('Ob2 (K1 held / Dg2\'): the parser\'s reading of Chase\'s held statement -> state CANDIDATE, strength KNOWING (the reading conveys the origin\'s knowledge: origin Chase = holder Chase, weakest-linked); 7G: listed as a candidate, NOT discharged - reading -> origin -> relation -> strength, never reading -> discharge',
          st(e2) == db.STRENGTH_KNOWING and [a['state'] for a in pm(r2, p2)['acknowledgments']] == [db.CLAIM_CANDIDATE]
          and pm(r2, p2)['acknowledgments'][0]['strength'] == db.STRENGTH_KNOWING and pm(r2, p2)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED)
    e3 = evidence(a2, utterance=utter("That's Chase acknowledging the April payment."))
    r3 = rem(O, '2026-04-30')
    acks3 = pm(r3, p2)['acknowledgments']
    check('Ob3 (K1 accepted - 9D-i-F3, RECORDED not solved): Rob\'s acceptance added to the same claim -> two relationships, (candidate, knowing) and (established, not_knowing); built 7G qualifies per relationship, so NOT discharged - the 7G question stays 7G\'s; this fixture asserts what 7G does today',
          st(e3) == db.STRENGTH_NOT_KNOWING
          and sorted((a['state'], a['strength']) for a in acks3) == sorted([(db.CLAIM_CANDIDATE, db.STRENGTH_KNOWING), (db.CLAIM_ESTABLISHED, db.STRENGTH_NOT_KNOWING)])
          and pm(r3, p2)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED)

    print('\n3. Ob4 / Ob5 / Ob6 / Ob12 - who asserted vs whose position: the 2 x 2 the relation exists to make\n')
    p4 = pay(O, '$1,412', '2026-05-05')
    e4, a4 = ack(chase, p4, '2026-05-10', origin=billco)
    r4 = rem(O, '2026-05-31')
    check('Ob4 (K2 / Dg4): BillCo (the servicer, by Rob\'s servicer_of claim) asserts an acknowledgment NAMING CHASE as holder -> origin BillCo != holder Chase -> NOT_KNOWING at the kind level; 7G: holder in effect, strength not knowing -> listed, NOT discharged - the servicer channel is a consumer\'s to read with O in hand, and the kind composes nothing through BillCo\'s roles',
          st(e4) == db.STRENGTH_NOT_KNOWING and pm(r4, p4)['acknowledgments'][0]['entitled'] == db.EFFECT_IN
          and pm(r4, p4)['acknowledgments'][0]['strength'] == db.STRENGTH_NOT_KNOWING and pm(r4, p4)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED)
    e5, a5 = ack(s3, p4, '2026-05-11')
    check('Ob5 (K3 / Dg5): S3 asserts its own acknowledgment (holder S3, origin S3) -> KNOWING for its own position (Kn12); 7G: S3 not entitled -> never discharged',
          st(e5) == db.STRENGTH_KNOWING and next(a for a in pm(rem(O, '2026-05-31'), p4)['acknowledgments'] if a['claim'] == a5.id)['entitled'] != db.EFFECT_IN
          and pm(rem(O, '2026-05-31'), p4)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED)
    e6, a6 = ack(chase, p4, '2026-05-12', origin=household)
    check('Ob6 (K5 / Dg22): Rob relays "Chase told me they got it" (holder Chase, origin Rob) -> NOT_KNOWING; listed, not discharged',
          st(e6) == db.STRENGTH_NOT_KNOWING and pm(rem(O, '2026-05-31'), p4)['station'] == db.STATION_ATTACHED_UNACKNOWLEDGED)
    p12 = pay(O, '$1,412', '2026-06-05')
    grid = {(hn, on): st(ack(h, p12, '2026-06-10', origin=o)[0])
            for hn, h in (('E', chase), ('S', billco)) for on, o in (('E', chase), ('S', billco))}
    check('Ob12 (the 2 x 2 - party x origin): (E, E) knowing; (E, S) NOT_KNOWING; (S, S) knowing (S\'s own position); (S, E) NOT_KNOWING (E asserting S\'s position is testimony) - the foundation type test called all four knowing; the relation tells who asserted from whose position',
          grid == {('E', 'E'): db.STRENGTH_KNOWING, ('E', 'S'): db.STRENGTH_NOT_KNOWING, ('S', 'S'): db.STRENGTH_KNOWING, ('S', 'E'): db.STRENGTH_NOT_KNOWING})
    check('the composition fence: an acknowledgment by the servicer naming E gains nothing from the servicer\'s servicer_of claim, from p\'s attachment to O, or from E\'s entitled role - the kind reads only holder and asserter; no O is reached',
          st(e4) == db.STRENGTH_NOT_KNOWING and a4.subject_obligation_id is None and a4.object_obligation_id is None
          and s.query(db.Proposition).filter_by(kind=db.SERVICER_OF, subject_party_id=billco.id, object_obligation_id=O.id).count() == 1)

    print('\n4. Ob7 / Ob8 / Ob9 / Ob11 / Ob13 - the balance: the role-at-date relation on every path\n')
    eb1, b1 = balance(O, '$2,588', '2026-03-31', origin=chase)
    check('Ob1 (balance): Chase states the balance as of 3/31; Chase entitled in effect on 3/31 -> KNOWING by the role-at-date relation; 7G: governing stated position',
          st(eb1) == db.STRENGTH_KNOWING and rem(O, '2026-03-31')['stated']['governing']['claim'] == b1.id)
    eb8, b8 = balance(O, '$2,500', '2026-04-01', origin=billco)
    check('Ob8 (K2 balance): BillCo states a balance; BillCo holds servicer_of, not entitled_party_of -> NOT_KNOWING at the kind level (the servicer is not a clause); 7G: not in E\'s series (K2\'s balance half is a consumer question, recorded)',
          st(eb8) == db.STRENGTH_NOT_KNOWING and rem(O, '2026-04-30')['stated']['governing']['claim'] != b8.id)
    _, rS9 = held('h-chase-statement-2', chase)
    eb9, b9 = balance(O, '$2,588', '2026-03-31', reading=rS9)
    check('Ob9 (K1 balance held / Ms1): a reading of Chase\'s held statement line -> state candidate, strength KNOWING (origin Chase in role at 3/31, weakest-linked with the origin claim); never governing',
          st(eb9) == db.STRENGTH_KNOWING and all(e['claim'] != b9.id for e in [rem(O, '2026-03-31')['stated']['governing']]))
    _, rRob = held('h-rob-spreadsheet', household)
    eb9b, _ = balance(O, '$2,588', '2026-03-31', reading=rRob)
    check('Ob9\' (O5): a reading of Rob\'s spreadsheet carrying the same figure -> the origin is the household, not in role -> NOT_KNOWING; relaying does not launder',
          st(eb9b) == db.STRENGTH_NOT_KNOWING)
    eb11, b11 = balance(O, '$2,000', '2026-04-30', origin=chase)
    check('Ob11 (K7): Chase 3/31 $2,588 and Chase 4/30 $2,000 - two knowing positions; G by date is 7G\'s (TS): 4/30 governs on 4/30, 3/31 on 3/31',
          st(eb11) == db.STRENGTH_KNOWING and rem(O, '2026-04-30')['stated']['governing']['claim'] == b11.id and rem(O, '2026-03-31')['stated']['governing']['claim'] == b1.id)
    O7 = mint(db.Obligation, 'A loan whose entitled party is disputed.')
    entitled(chase, O7)
    claim(db.ENTITLED_PARTY_OF_ENDED, utterance=utter('Chase sold it 3/1.'), as_of='2026-03-01', subject_party_id=chase.id, object_obligation_id=O7.id)
    claim(db.ENTITLED_PARTY_OF_BEGAN, utterance=utter('No - Chase still holds it from 3/1.', origin=chase), as_of='2026-03-01', subject_party_id=chase.id, object_obligation_id=O7.id)
    eb7, _ = balance(O7, '$9,000', '2026-03-15', origin=chase)
    ans7 = db.in_effect(s, chase, db.ENTITLED_PARTY_OF, '2026-03-15')['identities'][O7.id]['answer']
    check('Ob7 (Dg21): Chase\'s entitled-party role on O7 is CONTESTED at the balance\'s date -> the relation answers UNDETERMINED (neither manufactured); 7G reports the role answer and lets nothing govern',
          ans7 == db.EFFECT_CONTESTED and st(eb7) == db.STRENGTH_UNDETERMINED)
    eb13, _ = balance(O, '$1', None, origin=chase)
    e13a, a13 = ack(chase, p12, None)
    check('Ob13 (F7 - no dated key): an undated balance and an undated acknowledgment -> the balance\'s relation answers UNDETERMINED (no date to place the role against); 7G disqualifies both from governing and from discharge',
          st(eb13) == db.STRENGTH_UNDETERMINED and rem(O, '2026-06-30')['stated']['governing']['claim'] != eb13.proposition_id
          and next(a for a in pm(rem(O, '2026-06-30'), p12)['acknowledgments'] if a['claim'] == a13.id)['qualifies'] is False)
    stranger = mint(db.Party, 'A party with no stance on O at all.')
    ebx, _ = balance(O, '$5', '2026-03-31', origin=stranger)
    check('a party with no role stance on O at all -> NOT_KNOWING (no stance is not in role), not undetermined',
          st(ebx) == db.STRENGTH_NOT_KNOWING)

    print('\n5. Ob14 / Ob15 - returned; the party-subject line\n')
    snap = snapshot()
    before = pm(rem(O, '2026-03-31'), p1)['station']
    e14, a14 = claim(db.RETURNED, utterance=utter('We returned the March payment unapplied.', origin=chase), as_of='2026-03-12',
                     subject_party_id=chase.id, object_payment_id=p1.id)
    after = pm(rem(O, '2026-03-31'), p1)['station']
    check('Ob14 (Dg18): Chase returns p1 unapplied - the acknowledgment\'s shape (holder Chase, the payment), KNOWING for Chase\'s own; 7G reads no such kind - the station is unchanged (still discharged by the 3/10 acknowledgment); a return is not a non-acknowledgment, and nothing was written',
          st(e14) == db.STRENGTH_KNOWING and before == after == db.STATION_DISCHARGED
          and snapshot()[:len(snap)] == snap)
    e14r, _ = claim(db.RETURNED, reading=rS, as_of='2026-03-12', subject_party_id=chase.id, object_payment_id=p1.id)
    check('Ob14\': a reading of Chase\'s statement stating the return -> candidate in state, knowing in strength - the same machinery, no discharge semantics',
          st(e14r) == db.STRENGTH_KNOWING and pm(rem(O, '2026-03-31'), p1)['station'] == db.STATION_DISCHARGED)
    check('Ob15 (F2): a statement-line figure whose subject is the PARTY and whose thing is a candidate is REFUSED under the ruled name balance - the ruled kind has the obligation as subject; such a line keeps its shape under its own stand-in name (7E, 7A, 7C, 7D, Ab7 renamed theirs)',
          _refused(s, db.Proposition(kind=db.BALANCE, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                     subject_party_id=chase.id, content='$1,925', as_of='2026-03-31'))
          and not _refused(s, db.Proposition(kind='statement_figure', subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_CANDIDATES,
                                             subject_party_id=chase.id, content='$1,925', as_of='2026-03-31'))
          and 'statement_figure' not in db.RULED_KINDS)

    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    for f in FAIL:
        print('  FAILED: ' + f)
    return not FAIL


if __name__ == '__main__':
    from core import database as db
    sys.exit(0 if run(db) else 1)
