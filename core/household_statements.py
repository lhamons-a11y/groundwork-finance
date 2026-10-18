"""What the household says about its bank lines, recorded as the household's statements in the 2.0 records
(gw 2.0/BANK_SIDE_RECORDS.md, item 93 stages 3 and 4; B1-B12 ruled 2026-10-17, built on Rob's "go ahead stage 3 and 4",
2026-10-18, with two rulings made that day: who is answering is asked once and remembered, with a switch; answers given
before that are confirmed once by a person before they are absorbed). Master only.

The fixed point, unchanged: a payment, an expense, an obligation and an institution are minted only by an utterance that
ORIGINATES FROM A PERSON (core/database.py `_minting_violations`). Groundwork does not know who is at the keyboard, so
it asks once ("Who's answering?") and every statement made here is that person's utterance. Nothing is minted without
one - a route that would mint answers `need_speaker` and the page asks.

    B2   a bank is a party once, per account, by the household's word ("Is this account at Superior Credit Union?").
         Its roles: holding the account, and being the source of the statement. It establishes nothing else.
    B3   a line becomes a payment only by the household's statement: one line at a time, or a standing statement -
         scoped to an account, a payee as the person names it, and debits; dated, listed, withdrawable; suggested
         after three answers, made only on a yes. Withdrawing stops new lines and undoes nothing already recorded.
    B4   only the household's say-so creates an expense; a payment is never assumed to be one.
    B8   a reversal is linked only on the person's word: money moving back is another payment, and the link is the
         household's payment_counteracts claim. Nothing is netted off.
    B11  care-for answers, "attach as debt payment" links and work-reimbursement matches become the same statements in
         the 2.0 records once a person confirms them - each keeps its first date, nothing new is inferred.

The ledger line itself never becomes an identity (Pm2, Tx12): it is relayed as a `movement` proposition - the bank's
line, subject the bank's party once the household has named it - evidenced by the household's utterance, and tied to
the payment by `proposition_concerns`. 1.x rows are indexed (`LedgerLineRecord`, `AccountBank`), never presumed to be
the thing. Totals are unchanged by anything here.

Nothing here logs a transaction's text or a person's name.
"""
import json
import re
from datetime import datetime, timedelta

SPEAKER_KEY = 'speaker_person_id'
SUGGEST_AFTER = 3                 # B3: a standing statement may be suggested after three answers for one payee
REVERSAL_WINDOW_DAYS = 90

_NOISE = {'pending', 'purchase', 'pos', 'debit', 'credit', 'card', 'withdrawal', 'deposit', 'ach', 'payment', 'the',
          'and', 'recurring', 'authorized', 'visa', 'mastercard', 'checkcard', 'check', 'dbt', 'crd', 'pur', 'refund',
          'return', 'returned', 'reversal', 'transaction', 'online', 'web', 'www', 'com', 'inc', 'llc'}


# The 409 the page recognises: it asks who is answering, then tries again.
NEED_SPEAKER_TEXT = "Who is answering? Groundwork records each statement as a person's."


class NeedSpeaker(Exception):
    """No one has said who is answering on this computer: nothing can be minted until a person does."""


class NeedBank(Exception):
    """A line is relayed as the statement of the party that holds its account, and nobody has said which bank holds
    this one (B2). The page asks, then tries again."""

    def __init__(self, account_id, account, candidate):
        super().__init__(f'Which bank holds {account}?')
        self.account_id, self.account, self.candidate = account_id, account, candidate


def _words(text):
    return {w for w in re.findall(r'[a-z]{3,}', (text or '').lower()) if w not in _NOISE}


def _now_local():
    return datetime.now().isoformat(timespec='seconds')


# ── Who is answering (Rob 2026-10-18: asked once, remembered, with a switch) ─────────────────────────────────────────

def speaker(session):
    from core.database import AppSetting, Person
    row = session.query(AppSetting).filter_by(key=SPEAKER_KEY).first()
    try:
        p = session.get(Person, int(row.value)) if row and row.value else None
    except (TypeError, ValueError):
        p = None
    return p if p is not None and p.active else None


def set_speaker(session, person_id):
    from core.database import AppSetting, Person
    p = session.get(Person, int(person_id or 0))
    if p is None or not p.active:
        return None, 'That person was not found.'
    row = session.query(AppSetting).filter_by(key=SPEAKER_KEY).first()
    if row is None:
        session.add(AppSetting(key=SPEAKER_KEY, value=str(p.id)))
    else:
        row.value = str(p.id)
    session.flush()
    return p, None


def speaker_view(session):
    p = speaker(session)
    return {'person_id': p.id if p else None, 'name': p.display_name if p else None}


def utter(session, content):
    """The answering person's statement, now. Raises NeedSpeaker when no one has said who is answering."""
    from core.database import Utterance
    p = speaker(session)
    if p is None:
        raise NeedSpeaker()
    u = Utterance(origin_party_id=p.party.id, asserted_at=_now_local(), content=json.dumps(content, sort_keys=True))
    session.add(u)
    session.flush()
    return u


# ── The substrate, written the one way ───────────────────────────────────────────────────────────────────────────────

def _prop(session, kind, utt, content=None, as_of=None, **slots):
    from core.database import EvidentiaryRelationship, PARTICIPANT_ESTABLISHED, PARTICIPANT_NONE, Proposition
    given_state = slots.pop('subject_state', None)
    sub = {k: v for k, v in slots.items() if k.startswith('subject_')}
    obj = {k: v for k, v in slots.items() if k.startswith('object_')}
    sub_state = given_state or (PARTICIPANT_ESTABLISHED if sub else PARTICIPANT_NONE)
    p = Proposition(kind=kind, subject_state=sub_state, object_state=PARTICIPANT_ESTABLISHED if obj else PARTICIPANT_NONE,
                    content=content, as_of=as_of, **slots)
    session.add(p)
    session.flush()
    session.add(EvidentiaryRelationship(proposition_id=p.id, utterance_id=utt.id))
    session.flush()
    return p


def _mint_institution(session, utt):
    from core.database import Party
    party = Party(minted_by_id=utt.id)
    session.add(party)
    session.flush()
    return party


def institutions(session):
    """Institution parties by the name the household gave them (the minting utterance's content; a party has no name)."""
    from core.database import Party, Utterance
    out = {}
    for party in session.query(Party).filter(Party.minted_by_id.isnot(None)).all():
        u = session.get(Utterance, party.minted_by_id)
        try:
            c = json.loads(u.content) if u and u.content else {}
        except ValueError:
            c = {}
        for key in ('institution', 'payee', 'employer'):
            name = (c.get(key) or '').strip()
            if name and c.get(f'{key}_party_minted') == party.id:
                out.setdefault(name.lower(), (party.id, name))
    return out


def _institution(session, utt, name, key):
    """The party the person names: the one already minted under that name, or a new one minted by this utterance."""
    name = ' '.join(str(name or '').split())[:120]
    if not name:
        return None
    hit = institutions(session).get(name.lower())
    if hit:
        return hit[0]
    party = _mint_institution(session, utt)
    c = json.loads(utt.content or '{}')
    c.update({key: name, f'{key}_party_minted': party.id})
    utt.content = json.dumps(c, sort_keys=True)
    session.flush()
    return party.id


# ── B2: the bank, per account ────────────────────────────────────────────────────────────────────────────────────────

def bank_of(session, account_id):
    from core.database import AccountBank
    return session.query(AccountBank).filter_by(account_id=account_id).order_by(AccountBank.id.desc()).first()


def bank_questions(session):
    """Each active account and what the household has said about its bank. The account's institution text is offered
    as the candidate - never taken as the answer."""
    from core.database import Account
    out = []
    for a in session.query(Account).filter_by(is_active=True).order_by(Account.name).all():
        b = bank_of(session, a.id)
        out.append({'account_id': a.id, 'account': a.name, 'candidate': (a.institution or '').strip(),
                    'said': ({'name': b.name, 'not_a_bank': b.party_id is None,
                              'on': b.said_at.date().isoformat() if b.said_at else None} if b else None)})
    return {'accounts': out, 'known': sorted(v[1] for v in institutions(session).values())}


def say_bank(session, account_id, name, not_a_bank=False):
    from core.database import Account, AccountBank
    a = session.get(Account, int(account_id or 0))
    if a is None:
        return None, 'That account was not found.'
    name = ' '.join(str(name or '').split())[:120]
    if not not_a_bank and not name:
        return None, 'the bank\'s name, please'
    utt = utter(session, {'statement': 'account_held_at', 'account_id': a.id, 'account': a.name,
                          'institution': '' if not_a_bank else name, 'not_a_bank': bool(not_a_bank)})
    party_id = None if not_a_bank else _institution(session, utt, name, 'institution')
    row = AccountBank(account_id=a.id, party_id=party_id, utterance_id=utt.id, name='' if not_a_bank else name)
    session.add(row)
    session.flush()
    return row, None


# ── The ledger line, relayed; a payment by the household's statement (B3) ───────────────────────────────────────────

def record_of(session, transaction_id):
    from core.database import LedgerLineRecord
    return session.query(LedgerLineRecord).filter_by(transaction_id=transaction_id) \
        .order_by(LedgerLineRecord.id).first()


def _line_content(txn):
    return json.dumps({'date': txn.date.isoformat() if txn.date else None, 'description': txn.description or '',
                       'amount': round(float(txn.amount or 0), 2), 'type': txn.type or 'debit'}, sort_keys=True)


def _movement(session, txn, utt):
    """The line, as the household relays it: a `movement` - a party's statement that money moved on its account. Its
    subject must be established (the ruled kind requires it): the bank, once the household has named it (B2); for an
    account the household said is not a bank account, the household's own record - the person making the statement.
    An account nobody has answered for raises NeedBank, and the page asks first. It mints nothing (Pm2)."""
    from core.database import Account, MOVEMENT
    b = bank_of(session, txn.account_id)
    if b is None:
        a = session.get(Account, txn.account_id)
        raise NeedBank(txn.account_id, a.name if a else '', (a.institution or '').strip() if a else '')
    subject = b.party_id if b.party_id is not None else utt.origin_party_id
    return _prop(session, MOVEMENT, utt, _line_content(txn), txn.date.isoformat() if txn.date else None,
                 subject_party_id=subject)


def _payment_for(session, txn, utt, payee=None, via='line', standing_id=None, payee_party_id=None):
    """One payment for one line, minted by `utt`. A line already said to be a payment keeps the one it has."""
    from core.database import (AMOUNT, OCCURRED_ON, PAID_TO, PROPOSITION_CONCERNS, LedgerLineRecord, Payment)
    rec = record_of(session, txn.id)
    if rec is not None and rec.payment_id is not None:
        return rec, False
    p = Payment(minted_by_id=utt.id)
    session.add(p)
    session.flush()
    mv = rec.movement_id if rec is not None and rec.movement_id else _movement(session, txn, utt).id
    _prop(session, PROPOSITION_CONCERNS, utt, None, None, subject_proposition_id=mv, object_payment_id=p.id)
    _prop(session, AMOUNT, utt, f'{float(txn.amount or 0):.2f}', None, subject_payment_id=p.id)
    _prop(session, OCCURRED_ON, utt, None, txn.date.isoformat() if txn.date else None, subject_payment_id=p.id)
    if payee_party_id is None and payee:
        payee_party_id = _institution(session, utt, payee, 'payee')
    if payee_party_id is not None:
        _prop(session, PAID_TO, utt, None, None, subject_party_id=payee_party_id, object_payment_id=p.id)
    if rec is None:
        rec = LedgerLineRecord(transaction_id=txn.id, utterance_id=utt.id, via=via, standing_id=standing_id)
        session.add(rec)
    rec.movement_id, rec.payment_id = mv, p.id
    session.flush()
    return rec, True


def say_payment(session, transaction_id, payee):
    """"That was my payment to AEP": one line at a time (B3, the first way)."""
    from core.database import Transaction
    t = session.get(Transaction, int(transaction_id or 0))
    if t is None:
        return None, 'That line was not found.'
    if t.type != 'debit':
        return None, 'Only money out can be your payment.'
    if record_of(session, t.id) is not None and record_of(session, t.id).payment_id:
        return None, 'This line is already your payment.'
    payee = ' '.join(str(payee or '').split())[:120]
    utt = utter(session, {'statement': 'my_payment', 'transaction_id': t.id, 'line': json.loads(_line_content(t)),
                          'payee': payee})
    rec, _ = _payment_for(session, t, utt, payee=payee, via='line')
    return rec, None


def line_view(session, transaction_id):
    """What the household has said this line is, for the Ledger's edit panel."""
    from core.database import (PAID_TO, PAYMENT_COUNTERACTS, StandingStatement, Proposition, Transaction, Utterance)
    t = session.get(Transaction, transaction_id)
    rec = record_of(session, transaction_id)
    out = {'payment': None, 'suggest_standing': None, 'speaker': speaker_view(session)}
    if rec is not None and rec.payment_id:
        names = {v[0]: v[1] for v in institutions(session).values()}
        to = session.query(Proposition).filter_by(kind=PAID_TO, object_payment_id=rec.payment_id).first()
        u = session.get(Utterance, rec.utterance_id)
        st = session.get(StandingStatement, rec.standing_id) if rec.standing_id else None
        undone = session.query(Proposition).filter(Proposition.kind == PAYMENT_COUNTERACTS,
                                                   (Proposition.object_payment_id == rec.payment_id)
                                                   | (Proposition.subject_payment_id == rec.payment_id)).first()
        out['payment'] = {'payee': names.get(to.subject_party_id) if to else None, 'via': rec.via,
                          'said_on': (u.asserted_at or '')[:10] if u else None,
                          'by': _who(session, u),
                          'standing': ({'id': st.id, 'payee': st.payee} if st else None),
                          'counteract': bool(undone), 'expense': rec.expense_id is not None}
    if t is not None and out['payment'] and out['payment']['via'] == 'line':
        out['suggest_standing'] = standing_suggestion(session, t, out['payment']['payee'])
    return out


def _who(session, utt):
    from core.database import Person
    if utt is None or utt.origin is None or utt.origin.person_id is None:
        return None
    p = session.get(Person, utt.origin.person_id)
    return p.display_name if p else None


# ── B3: standing statements, the importer contract ───────────────────────────────────────────────────────────────────

def _covers(st_account, st_payee, txn):
    return (txn.account_id == st_account and txn.type == 'debit'
            and st_payee.lower() in (txn.description or '').lower())


def covered_lines(session, account_id, payee):
    from core.database import Transaction
    payee = (payee or '').strip()
    if not payee:
        return []
    rows = session.query(Transaction).filter(Transaction.account_id == account_id, Transaction.type == 'debit',
                                             Transaction.description.ilike(f'%{payee}%')).all()
    return [t for t in rows if not (record_of(session, t.id) and record_of(session, t.id).payment_id)]


def standing_suggestion(session, txn, payee):
    """After three of the person's own answers for one payee on one account, offer - never make - a standing statement."""
    from core.database import LedgerLineRecord, PAID_TO, Proposition, StandingStatement, Transaction
    if not payee:
        return None
    if any(st.withdrawn_at is None and st.payee.lower() == payee.lower()
           for st in session.query(StandingStatement).filter_by(account_id=txn.account_id).all()):
        return None
    names = {v[0]: v[1] for v in institutions(session).values()}
    n = 0
    for rec in session.query(LedgerLineRecord).filter_by(via='line').all():
        t = session.get(Transaction, rec.transaction_id)
        if t is None or t.account_id != txn.account_id or rec.payment_id is None:
            continue
        to = session.query(Proposition).filter_by(kind=PAID_TO, object_payment_id=rec.payment_id).first()
        if to and (names.get(to.subject_party_id) or '').lower() == payee.lower():
            n += 1
    if n < SUGGEST_AFTER:
        return None
    if payee.lower() not in (txn.description or '').lower():
        return None                 # a standing statement matches the payee in the line's text; this one isn't there
    return {'payee': payee, 'answers': n, 'account_id': txn.account_id,
            'covers': len(covered_lines(session, txn.account_id, payee))}


def standing_list(session):
    from core.database import Account, StandingStatement, LedgerLineRecord, Utterance
    names = {a.id: a.name for a in session.query(Account).all()}
    out = []
    for st in session.query(StandingStatement).order_by(StandingStatement.id.desc()).all():
        u = session.get(Utterance, st.utterance_id)
        out.append({'id': st.id, 'account_id': st.account_id, 'account': names.get(st.account_id, ''),
                    'payee': st.payee, 'said_on': (u.asserted_at or '')[:10] if u else None, 'by': _who(session, u),
                    'withdrawn_on': st.withdrawn_at.date().isoformat() if st.withdrawn_at else None,
                    'payments': session.query(LedgerLineRecord).filter_by(standing_id=st.id).count()})
    return out


def say_standing(session, account_id, payee):
    """"Treat every debit from this account to PAYEE as my payment." It covers the lines already here (the count is
    shown before the yes) and each new one as it arrives."""
    from core.database import Account, StandingStatement
    a = session.get(Account, int(account_id or 0))
    payee = ' '.join(str(payee or '').split())[:120]
    if a is None or len(payee) < 3:
        return None, 0, 'an account and a payee of at least three letters, please'
    if any(st.withdrawn_at is None and st.payee.lower() == payee.lower()
           for st in session.query(StandingStatement).filter_by(account_id=a.id).all()):
        return None, 0, 'You already said this for that payee.'
    if bank_of(session, a.id) is None:      # the lines it will cover are this bank's statements: named first (B2)
        raise NeedBank(a.id, a.name, (a.institution or '').strip())
    utt = utter(session, {'statement': 'standing_my_payment', 'account_id': a.id, 'account': a.name, 'payee': payee,
                          'direction': 'debit'})
    party_id = _institution(session, utt, payee, 'payee')
    st = StandingStatement(account_id=a.id, payee=payee, payee_party_id=party_id, utterance_id=utt.id)
    session.add(st)
    session.flush()
    n = 0
    for t in covered_lines(session, a.id, payee):
        _payment_for(session, t, utt, via='standing', standing_id=st.id, payee_party_id=party_id)
        n += 1
    return st, n, None


def withdraw_standing(session, standing_id):
    from core.database import StandingStatement
    st = session.get(StandingStatement, int(standing_id or 0))
    if st is None or st.withdrawn_at is not None:
        return None, 'That statement was not found.'
    utt = utter(session, {'statement': 'withdraw_standing', 'standing_id': st.id, 'payee': st.payee})
    st.withdrawn_at, st.withdrawn_utterance_id = datetime.utcnow(), utt.id
    session.flush()
    return st, None


def apply_standing(session, txns):
    """New lines from an import: each one a standing statement covers becomes a payment by that statement - the
    household's word, lent once, recorded as such. Never invented: no statement, no payment."""
    from core.database import StandingStatement, Utterance
    live = session.query(StandingStatement).filter(StandingStatement.withdrawn_at.is_(None)).all()
    n = 0
    for t in txns:
        st = next((s for s in live if _covers(s.account_id, s.payee, t)), None)
        if st is None:
            continue
        sp = session.begin_nested()           # all or nothing per line, so an import never fails on a statement
        try:
            _, made = _payment_for(session, t, session.get(Utterance, st.utterance_id), via='standing',
                                   standing_id=st.id, payee_party_id=st.payee_party_id)
        except NeedBank:                       # cannot happen while bank answers are only ever added; never invent one
            sp.rollback()
            continue
        sp.commit()
        n += int(made)
    return n


# ── B4: an expense, only by the household's say-so; the care-for answer as a statement ──────────────────────────────

def say_care(session, transaction_id, person_id, utt=None, first_said=None):
    """"That was Sam's visit": a payment, an expense minted by the answer, incurred_by the person, the payment
    toward the expense. A change of person is a new incurred_by claim; the earlier one stays (newest current)."""
    from core.database import (INCURRED_BY, OCCURRED_ON, PAYMENT_IN_RESPECT_OF, Expense, Person, Transaction)
    t = session.get(Transaction, int(transaction_id or 0))
    person = session.get(Person, int(person_id or 0)) if person_id else None
    if t is None or person is None:
        return None
    if utt is None:
        utt = utter(session, {'statement': 'care_for', 'transaction_id': t.id, 'line': json.loads(_line_content(t)),
                              'person_id': person.id, **({'first_said': first_said} if first_said else {})})
    rec, _ = _payment_for(session, t, utt, via='care')
    if rec.expense_id is None:
        x = Expense(minted_by_id=utt.id)
        session.add(x)
        session.flush()
        _prop(session, OCCURRED_ON, utt, None, t.date.isoformat() if t.date else None, subject_expense_id=x.id)
        _prop(session, PAYMENT_IN_RESPECT_OF, utt, None, None, subject_payment_id=rec.payment_id, object_expense_id=x.id)
        rec.expense_id = x.id
    _prop(session, INCURRED_BY, utt, None, None, subject_party_id=person.party.id, object_expense_id=rec.expense_id)
    session.flush()
    return rec


# ── B8: a reversal, linked only on the person's word ────────────────────────────────────────────────────────────────

def reversal_candidates(session, limit=40):
    """A money-in line that may undo an earlier charge on the same account: within 90 days after it, no more than it,
    sharing a merchant word. Offered, never decided; a no is not asked again."""
    from core.database import LedgerLineRecord, ReversalAnswer, Transaction
    answered = {(r.credit_id, r.debit_id) for r in session.query(ReversalAnswer).all()}
    linked = {r.credit_id for r in session.query(ReversalAnswer).filter_by(answer='yes').all()}
    out = []
    credits = session.query(Transaction).filter(Transaction.type == 'credit').order_by(Transaction.date.desc()).limit(400).all()
    for c in credits:
        if c.id in linked or _is_income(c):
            continue                        # pay is money in, never money back
        words = {w for w in _words(c.description) if len(w) >= 4}
        if not words:
            continue
        debits = session.query(Transaction).filter(
            Transaction.account_id == c.account_id, Transaction.type == 'debit',
            Transaction.date <= c.date, Transaction.date >= c.date - timedelta(days=REVERSAL_WINDOW_DAYS),
            Transaction.amount >= c.amount - 0.005).all()
        # the merchant, not a stray word: at least half of the money-in line's own words appear in the charge
        debits = [d for d in debits if (c.id, d.id) not in answered
                  and len(words & _words(d.description)) * 2 >= len(words)]
        if not debits:
            continue
        d = min(debits, key=lambda d: (abs(d.amount - c.amount), (c.date - d.date).days))
        out.append({'credit': _brief(c), 'debit': _brief(d)})
        if len(out) >= limit:
            break
    return out


def _is_income(t):
    from sqlalchemy.orm import object_session
    from core.database import Category
    cat, seen = t.category, set()
    while cat is not None and cat.id not in seen:
        if (cat.type or '') == 'income':
            return True
        seen.add(cat.id)
        cat = object_session(t).get(Category, cat.parent_id) if cat.parent_id else None
    return False


def _brief(t):
    return {'id': t.id, 'date': t.date.isoformat() if t.date else None, 'description': t.description,
            'amount': round(float(t.amount or 0), 2)}


def answer_reversal(session, credit_id, debit_id, yes):
    from core.database import PAYMENT_COUNTERACTS, ReversalAnswer, Transaction
    c, d = session.get(Transaction, int(credit_id or 0)), session.get(Transaction, int(debit_id or 0))
    if c is None or d is None or c.type != 'credit' or d.type != 'debit':
        return None, 'Those two lines were not found.'
    if not yes:
        row = ReversalAnswer(credit_id=c.id, debit_id=d.id, answer='no')
        session.add(row)
        session.flush()
        return row, None
    utt = utter(session, {'statement': 'counteracts', 'credit': json.loads(_line_content(c)), 'credit_id': c.id,
                          'debit': json.loads(_line_content(d)), 'debit_id': d.id})
    p1, _ = _payment_for(session, d, utt, via='reversal')
    p2, _ = _payment_for(session, c, utt, via='reversal')      # money moving back is another payment
    _prop(session, PAYMENT_COUNTERACTS, utt, None, None, subject_payment_id=p2.payment_id, object_payment_id=p1.payment_id)
    row = ReversalAnswer(credit_id=c.id, debit_id=d.id, answer='yes', utterance_id=utt.id)
    session.add(row)
    session.flush()
    return row, None


# ── B11: earlier answers, confirmed once by a person ────────────────────────────────────────────────────────────────

def earlier(session):
    """Answers given before Groundwork recorded who gave them, not yet confirmed. Only answers that said something:
    a "Household (not said)" care answer has nothing to absorb."""
    from core.database import (CareFor, CheckingTransactionLink, DebtAccount, DebtLedgerEntry, EarlierAnswer, Person,
                               ReimbursableItem, ReimbursementMatch, Transaction)
    done = {(e.source, e.source_id) for e in session.query(EarlierAnswer).all()}
    out = []
    latest = {}
    for cf in session.query(CareFor).order_by(CareFor.id).all():
        latest[cf.transaction_id] = cf
    for cf in latest.values():
        t = session.get(Transaction, cf.transaction_id)
        if cf.person_id is None or t is None or ('care', cf.id) in done:
            continue
        p = session.get(Person, cf.person_id)
        out.append({'source': 'care', 'source_id': cf.id, 'line': _brief(t), 'first_said': _day(cf.created_at),
                    'says': f"for {p.display_name if p else 'someone'}"})
    for ln in session.query(CheckingTransactionLink).filter_by(link_indicator='payment_to_card').all():
        t = session.get(Transaction, ln.checking_transaction_id)
        e = session.get(DebtLedgerEntry, ln.debt_ledger_entry_id)
        if t is None or e is None or ('debt', ln.id) in done:
            continue
        d = session.get(DebtAccount, e.debt_account_id)
        out.append({'source': 'debt', 'source_id': ln.id, 'line': _brief(t), 'first_said': _day(ln.user_confirmed_at),
                    'says': f"a payment toward {d.name if d else 'a debt'}"})
    for m in session.query(ReimbursementMatch).all():
        item = session.get(ReimbursableItem, m.item_id)
        c = session.get(Transaction, m.credit_transaction_id)
        t = session.get(Transaction, item.transaction_id) if item else None
        if c is None or t is None or ('reimburse', m.id) in done:
            continue
        out.append({'source': 'reimburse', 'source_id': m.id, 'line': _brief(c), 'first_said': _day(m.matched_at),
                    'says': f"paid back by work for {t.description} ({t.date.isoformat() if t.date else ''})"})
    return out


def _day(dt):
    return dt.date().isoformat() if dt else None


def _carry_one(session, e, utt, obligations):
    """One kept answer, as the same statement in the 2.0 records, under `utt`."""
    from core.database import (CareFor, CheckingTransactionLink, DebtLedgerEntry, PAID_BY, PAYMENT_COUNTERACTS,
                               PAYMENT_IN_RESPECT_OF_OBLIGATION, ReimbursableItem, ReimbursementMatch, Transaction)
    if e['source'] == 'care':
        cf = session.get(CareFor, e['source_id'])
        say_care(session, cf.transaction_id, cf.person_id, utt=utt)
    elif e['source'] == 'debt':
        ln = session.get(CheckingTransactionLink, e['source_id'])
        entry = session.get(DebtLedgerEntry, ln.debt_ledger_entry_id)
        rec, _ = _payment_for(session, session.get(Transaction, ln.checking_transaction_id), utt, via='debt')
        # The debt the payment went toward: an obligation, minted once per debt by the statement that first names it
        # ("my payment toward Chase Sapphire" says there is a debt called that).
        ob = obligations.get(entry.debt_account_id) or _obligation_for(session, entry.debt_account_id, utt)
        obligations[entry.debt_account_id] = ob
        _prop(session, PAYMENT_IN_RESPECT_OF_OBLIGATION, utt, None, None, subject_payment_id=rec.payment_id,
              object_obligation_id=ob)
    elif e['source'] == 'reimburse':
        m = session.get(ReimbursementMatch, e['source_id'])
        item = session.get(ReimbursableItem, m.item_id)
        p1, _ = _payment_for(session, session.get(Transaction, item.transaction_id), utt, via='reimburse')
        p2, _ = _payment_for(session, session.get(Transaction, m.credit_transaction_id), utt, via='reimburse')
        if item.employer:
            emp = _institution(session, utt, item.employer, 'employer')
            _prop(session, PAID_BY, utt, None, None, subject_party_id=emp, object_payment_id=p2.payment_id)
        _prop(session, PAYMENT_COUNTERACTS, utt, json.dumps({'amount_matched': round(m.amount, 2)}), None,
              subject_payment_id=p2.payment_id, object_payment_id=p1.payment_id)


def confirm_earlier(session, items):
    """"These were mine": one statement by the answering person today, naming each answer with the date it was first
    given. Each becomes the same statement in the 2.0 records; nothing else is inferred."""
    from core.database import EarlierAnswer
    open_ = {(e['source'], e['source_id']): e for e in earlier(session)}
    pick = [open_[(i.get('source'), int(i.get('source_id') or 0))] for i in (items or [])
            if (i.get('source'), int(i.get('source_id') or 0)) in open_]
    if not pick:
        return 0, 'Nothing to confirm.'
    utt = utter(session, {'statement': 'confirm_earlier_answers',
                          'answers': [{'source': e['source'], 'source_id': e['source_id'], 'first_said': e['first_said'],
                                       'says': e['says'], 'line': e['line']} for e in pick]})
    obligations = {}
    for e in pick:
        _carry_one(session, e, utt, obligations)
        session.add(EarlierAnswer(source=e['source'], source_id=e['source_id'], utterance_id=utt.id,
                                  first_said=e['first_said']))
    session.flush()
    return len(pick), None


def carry_new(session, source, source_id):
    """An answer given just now (a care-for answer, an "attach as debt payment", a reimbursement match): with someone
    answering, it is their statement at once. With no one answering - or no bank named for the line's account - it is
    kept as before and waits among the earlier answers to confirm, so it isn't credited to anyone. All or nothing: a
    savepoint, so a half-carried answer never stays. Returns True when carried."""
    from core.database import EarlierAnswer
    if speaker(session) is None:
        return False
    e = next((x for x in earlier(session) if x['source'] == source and x['source_id'] == source_id), None)
    if e is None:
        return False
    sp = session.begin_nested()
    try:
        utt = utter(session, {'statement': f'{source}_answer', 'source_id': source_id, 'says': e['says'], 'line': e['line']})
        _carry_one(session, e, utt, {})
        session.add(EarlierAnswer(source=source, source_id=source_id, utterance_id=utt.id, first_said=_now_local()[:10]))
        session.flush()
    except (NeedBank, NeedSpeaker):
        sp.rollback()
        return False
    sp.commit()
    return True


def _obligation_for(session, debt_account_id, utt):
    """The obligation for a 1.x debt: the one a confirmation already minted, or a new one minted by `utt`."""
    from core.database import DebtAccount, Obligation, Utterance
    for ob in session.query(Obligation).all():
        u = session.get(Utterance, ob.minted_by_id)
        try:
            c = json.loads(u.content) if u and u.content else {}
        except ValueError:
            c = {}
        if str(debt_account_id) in (c.get('obligations_minted') or {}) and (c['obligations_minted'][str(debt_account_id)] == ob.id):
            return ob.id
    ob = Obligation(minted_by_id=utt.id)
    session.add(ob)
    session.flush()
    d = session.get(DebtAccount, debt_account_id)
    c = json.loads(utt.content or '{}')
    c.setdefault('obligations_minted', {})[str(debt_account_id)] = ob.id
    c.setdefault('debts_named', {})[str(debt_account_id)] = d.name if d else ''
    utt.content = json.dumps(c, sort_keys=True)
    session.flush()
    return ob.id
