"""Named people, and whom health care was for (gw 2.0/NAMED_PEOPLE.md, item 92 = item 45 H7 stage 5; N1-N8 ruled
2026-10-16, N8 decided 2026-10-17).

core/person.py's rules, kept over the `people` table and a tag on the ledger row:
    a person is a name the household chooses; the id is identity, so a rename moves no figure (N1)
    whom a payment was for is said payment by payment and never inferred - not from the card, the account or an
        imported name; a joint account has no author (N2)
    an answer is kept: a change is a dated correction and the earlier one stays (N4)
    a person with history is made inactive, never deleted (N1)
    names are labels, not access control (N3) - said where a person is added

N8: the tag (`care_for`) is a 1.x record of the household's answer, not an expense identity. When the bank side of the
2.0 records is ruled, each tag becomes the household's statement there (NAMED_PEOPLE.md, "N8 decided").
N7: names are kept off the model's context, the AI log and every export that can't be ticked; nothing here logs.
"""
from datetime import date

VISIBILITY = ('Anyone who opens Groundwork on this computer can see everything here, including each person\'s health '
              'spending. Names are labels, not locks.')


def _people(session, include_inactive=False):
    from core.database import Person
    q = session.query(Person)
    if not include_inactive:
        q = q.filter(Person.active.is_(True))
    return q.order_by(Person.display_name).all()


def listing(session):
    """The people, and the household-mode names not yet added - offered, never copied (N6)."""
    from core.database import AppSetting
    ppl = _people(session, include_inactive=True)
    have = {p.display_name.strip().lower() for p in ppl}
    offer = []
    for k in ('household_user1', 'household_user2'):
        row = session.query(AppSetting).filter_by(key=k).first()
        n = (row.value or '').strip() if row else ''
        if n and n.lower() not in have and n not in offer:
            offer.append(n)
    hm = session.query(AppSetting).filter_by(key='household_mode').first()
    return {'people': [{'id': p.id, 'name': p.display_name, 'active': bool(p.active), 'used': _used(session, p.id)}
                       for p in ppl],
            'offer': offer if (hm and hm.value == 'true') else [], 'visibility': VISIBILITY}


def add(session, name):
    from core.database import Person
    name = ' '.join(str(name or '').split())[:80]
    if not name:
        return None, 'a name, please'
    if any(p.display_name.lower() == name.lower() for p in _people(session, include_inactive=True)):
        return None, f'"{name}" is already here'
    p = Person(display_name=name, active=True)
    session.add(p)
    session.flush()             # the Party anchor is minted in the same unit of work (database.py)
    return p, None


def rename(session, person_id, name):
    from core.database import Person
    p = session.get(Person, int(person_id or 0))
    name = ' '.join(str(name or '').split())[:80]
    if not p or not name:
        return None, 'a person and a name, please'
    p.display_name = name
    return p, None


def _used(session, person_id):
    from core.database import (CareFor, HealthPlanReading, Party, PersonAssignment, PersonEnrolment, Proposition,
                               Utterance)
    if any(session.query(m).filter_by(person_id=person_id).first() is not None
           for m in (CareFor, HealthPlanReading, PersonAssignment, PersonEnrolment)):
        return True
    # The 2.0 records point at the person's party anchor; a person any of them names has history too.
    party = session.query(Party).filter_by(person_id=person_id).first()
    if party is None:
        return False
    return (session.query(Utterance).filter_by(origin_party_id=party.id).first() is not None
            or session.query(Proposition).filter((Proposition.subject_party_id == party.id)
                                                 | (Proposition.object_party_id == party.id)).first() is not None)


def remove(session, person_id):
    """N1: deleted only when nothing points at them; otherwise made inactive (their history stays theirs)."""
    from core.database import Person
    p = session.get(Person, int(person_id or 0))
    if not p:
        return None, 'That person was not found.'
    if _used(session, p.id):
        p.active = False
        return 'inactive', None
    if p.party is not None:
        session.delete(p.party)
    session.delete(p)
    return 'deleted', None


# ── Whom a payment was for (N2, N4) ─────────────────────────────────────────────────────────────────────────────

def current(session, transaction_id):
    """The person on a payment now: a Person id, None for "Household" (not said), or None when never answered."""
    from core.database import CareFor
    row = session.query(CareFor).filter_by(transaction_id=transaction_id).order_by(CareFor.id.desc()).first()
    return row.person_id if row else None


def currents(session):
    """{transaction_id: person_id or None} for every answered payment - the newest answer each."""
    from core.database import CareFor
    out = {}
    for r in session.query(CareFor).order_by(CareFor.id).all():
        out[r.transaction_id] = r.person_id
    return out


def history(session, transaction_id):
    from core.database import CareFor, Person
    names = {p.id: p.display_name for p in session.query(Person).all()}
    return [{'person': names.get(r.person_id, 'Household'), 'mode': r.mode,
             'on': r.created_at.date().isoformat() if r.created_at else None}
            for r in session.query(CareFor).filter_by(transaction_id=transaction_id).order_by(CareFor.id).all()]


def assign(session, transaction_id, person_id):
    """N4: the household's answer for one health payment. A change is a correction; the earlier one stays."""
    from core import health_boundary as hb
    from core.database import CareFor, Person, Transaction
    t = session.get(Transaction, int(transaction_id or 0))
    if not t or not hb.health_rows(session)(t):
        return None, 'only a health payment can say whom it was for'
    pid = None
    if person_id not in (None, '', 'household'):
        p = session.get(Person, int(person_id))
        if not p or not p.active:
            return None, 'That person was not found.'
        pid = p.id
    had = session.query(CareFor).filter_by(transaction_id=t.id).first() is not None
    if had and current(session, t.id) == pid:
        return None, None                  # nothing changed, nothing written
    row = CareFor(transaction_id=t.id, person_id=pid, mode='correction' if had else 'initial')
    session.add(row)
    session.flush()
    return row, None


def _payee(t):
    return ' '.join(str(t.merchant or t.description or '').split())


def same_payee_offer(session, transaction_id):
    """N4: after an answer, the other health payments to the same payee with no answer yet - offered, only on a yes."""
    from core import health_boundary as hb
    from core.database import CareFor, Transaction
    t = session.get(Transaction, int(transaction_id or 0))
    if not t:
        return None
    is_health = hb.health_rows(session)
    answered = {r.transaction_id for r in session.query(CareFor).all()}
    name = _payee(t)
    others = [x.id for x in session.query(Transaction).filter(Transaction.type == 'debit').all()
              if x.id != t.id and is_health(x) and _payee(x) == name and x.id not in answered]
    return {'payee': name, 'ids': others} if others else None


def assign_many(session, ids, person_id):
    done = 0
    for i in ids or []:
        row, problem = assign(session, i, person_id)
        if problem:
            return done, problem
        done += 1 if row else 0
    return done, None
