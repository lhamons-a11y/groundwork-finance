"""The bill that lands (gw 2.0/BILL_THAT_LANDS.md, item 94 = item 45 H7 stage 6; L1-L10 ruled 2026-10-19, Rob: "I accept
item 94 as written"). Master only.

    L1   a bill is a statement BY a provider (or an insurer's EOB), typed in by the household. It creates no obligation by
         arriving: the obligation is minted only by the household's "this bill is mine to pay" (item 93 B4)
    L2   "amount owed now" is worked out with its parts: the latest statement's figure, less the payments the household
         said were toward it after that date. Two statements that disagree are both shown with their dates; the newer
         is the current position, and the disagreement is named, never resolved. A payment the newest bill may or may
         not reflect is said in so many words
    L3   insurance moves a figure only through the insurer's or provider's own statement; a claim the household says is
         pending marks the bill "may change" and keeps it out of any "can be paid in full" judgement
    L4   an arrangement is the provider's terms as the household reports them; Groundwork never says one will be agreed
    L5   a bill paid by card is one payment toward the bill, and the card's balance is card debt - counted once. The link
         is the household's statement; a card charge that looks like the bill is only named, and both are counted
         until the household says
    L6   the alarm is about the reserve, never the bill's size: `bill_due` when paying in full would leave savings below
         the reserve or the stability floor, or when it can't be paid in full from what's on record
    L7   the federal non-profit hospital facts are stated only where the household said the provider is one
    L8   what the record sustains, never what to offer
    L9   the all-obligations date stands beside the card-free date (card balances only), and is not given when any
         included obligation can't be dated - the ones that can't are named
    L10  health data under H6 (scrubbed, kept from the model, the AI log and unticked exports); every sentence is
         templated here; nothing contacts anyone; collections are out

Nothing here logs, calls a model or reaches the network.
"""
import json
import re
from datetime import date, timedelta

from core.hsa_fsa import money

SOURCES = ('provider', 'insurer', 'collector')       # collector: item 101
DURATIONS = (6, 12, 24)                           # L8: three durations, each with its monthly amount
ATTENTION_DAYS = 30                               # L6: from a month before the due date
CANDIDATE_DAYS = 120                              # L5: how far back a look-alike charge is named

NONPROFIT_FACTS = (
    'A non-profit hospital must have a written financial assistance policy and make it available (IRC §501(r)).',
    'Patients have at least 240 days from the first bill after discharge to apply for financial assistance under it '
    '(26 CFR 1.501(r)-6).',
    'For at least 120 days from the first bill, the hospital may not take certain extraordinary collection actions '
    '(26 CFR 1.501(r)-6).',
)
NO_ASSISTANCE_SHOWN = "The bill doesn't show whether financial assistance was applied."
NEVER_DIRECTS = 'Groundwork states what the bills show. It never contacts anyone, and it never says what to do.'
# Item 101 C6 (Rob 2026-10-19): the one step Groundwork names, on every collection
LEGAL_NOTE = ("If you believe this debt isn't correct, or is no longer valid, consider getting legal advice before you "
              "pay or agree to anything.")

_NOISE = {'the', 'and', 'inc', 'llc', 'health', 'medical', 'center', 'hospital', 'clinic', 'group', 'services', 'care',
          'system', 'physicians', 'associates', 'of', 'for', 'at'}


def _day(iso):
    try:
        return date.fromisoformat(str(iso)[:10])
    except (TypeError, ValueError):
        return None


def _says(iso):
    d = _day(iso)
    return d.strftime('%b %d, %Y').replace(' 0', ' ') if d else str(iso or '')


def _hist(text):
    try:
        v = json.loads(text or '[]')
    except ValueError:
        v = []
    return v if isinstance(v, list) else []


def _iso_or_none(v):
    d = _day(v) if v else None
    return d.isoformat() if d else None


# ── L1: a statement, brought in by the household ─────────────────────────────────────────────────────────────────────

def add_statement(session, body):
    """{provider, account_number, source, statement_date, amount, due_date, service_from, service_to}. The
    household's utterance records that it typed this in; the statement is the provider's (or insurer's) word."""
    from core import household_statements as hs
    from core.database import MedicalBillAccount, MedicalBillStatement, MedicalProvider
    name = ' '.join(str(body.get('provider') or '').split())[:160]
    source = body.get('source') or 'provider'
    sd = _iso_or_none(body.get('statement_date'))
    try:
        amount = round(float(body.get('amount')), 2)
    except (TypeError, ValueError):
        amount = None
    if not name:
        return None, 'Name the provider (or the insurer) the statement is from.'
    if source not in SOURCES:
        return None, "A statement is the provider's bill or the insurer's explanation of benefits."
    if not sd:
        return None, "The statement's date is needed: it is what makes a newer statement newer."
    if amount is None or amount < 0:
        return None, 'The amount the statement gives is needed.'
    acct_no = ' '.join(str(body.get('account_number') or '').split())[:60]
    prov = next((p for p in session.query(MedicalProvider).all() if p.name.lower() == name.lower()), None)
    acct = None
    if prov is not None:
        acct = next((a for a in session.query(MedicalBillAccount).filter_by(provider_id=prov.id).all()
                     if (a.account_number or '').lower() == acct_no.lower()), None)
        if acct is None and body.get('account_id'):
            acct = session.get(MedicalBillAccount, int(body['account_id']))
    utt = hs.utter(session, {'statement': 'typed_bill', 'from': source, 'provider': name, 'account_number': acct_no,
                             'statement_date': sd, 'amount': f'{amount:.2f}'})
    if source == 'collector' and (acct is None or _collection_of(session, acct.id) is None):
        return None, ('Record that the bill went to collections first (on the bill), with this collector\'s name and '
                      'account number; its statements then come in here.')
    if prov is None:
        prov = MedicalProvider(name=name)
        session.add(prov)
        session.flush()
    if acct is None:
        acct = MedicalBillAccount(provider_id=prov.id, account_number=acct_no)
        session.add(acct)
        session.flush()
    st = MedicalBillStatement(account_id=acct.id, source=source, statement_date=sd, amount=amount,
                              due_date=_iso_or_none(body.get('due_date')), service_from=_iso_or_none(body.get('service_from')),
                              service_to=_iso_or_none(body.get('service_to')), typed_utterance_id=utt.id)
    session.add(st)
    session.flush()
    return acct, None


def say_mine(session, account_id):
    """"This bill is mine to pay": the obligation, minted by the household's utterance (L1, item 93 B4)."""
    from core import household_statements as hs
    from core.database import MedicalBillAccount, Obligation
    a = session.get(MedicalBillAccount, int(account_id or 0))
    if a is None:
        return None, 'That bill was not found.'
    if a.obligation_id:
        return a, None
    utt = hs.utter(session, {'statement': 'bill_mine_to_pay', 'medical_bill_account_id': a.id})
    ob = Obligation(minted_by_id=utt.id)
    session.add(ob)
    session.flush()
    a.obligation_id, a.mine_utterance_id = ob.id, utt.id
    session.flush()
    return a, None


def say_claim(session, account_id, pending):
    """L3: the household says the insurer's claim is (or is no longer) pending. Kept as history; newest is current."""
    from core import household_statements as hs
    from core.database import MedicalBillAccount
    a = session.get(MedicalBillAccount, int(account_id or 0))
    if a is None:
        return None, 'That bill was not found.'
    utt = hs.utter(session, {'statement': 'claim_pending' if pending else 'claim_settled', 'medical_bill_account_id': a.id})
    h = _hist(a.claim_json)
    h.append({'pending': bool(pending), 'said_on': date.today().isoformat(), 'utterance_id': utt.id})
    a.claim_json = json.dumps(h)
    session.flush()
    return a, None


def say_arrangement(session, account_id, body):
    """L4: the provider's terms as the household reports them - {monthly, first_date, payments}, or {none: true}."""
    from core import household_statements as hs
    from core.database import MedicalBillAccount
    a = session.get(MedicalBillAccount, int(account_id or 0))
    if a is None:
        return None, 'That bill was not found.'
    if body.get('none'):
        entry = {'none': True}
    else:
        try:
            monthly = round(float(body.get('monthly')), 2)
            count = int(body.get('payments'))
        except (TypeError, ValueError):
            return None, 'The monthly amount and the number of payments the provider agreed are needed.'
        first = _iso_or_none(body.get('first_date'))
        if monthly <= 0 or count <= 0 or not first:
            return None, 'The monthly amount, the first payment date and the number of payments are needed.'
        entry = {'monthly': monthly, 'first_date': first, 'payments': count}
    utt = hs.utter(session, {'statement': 'arrangement_as_agreed', 'medical_bill_account_id': a.id, **entry})
    h = _hist(a.arrangement_json)
    h.append({**entry, 'said_on': date.today().isoformat(), 'utterance_id': utt.id})
    a.arrangement_json = json.dumps(h)
    session.flush()
    return a, None


def say_nonprofit(session, provider_id, value):
    """L7: the household's word on whether the provider is a non-profit hospital (True / False / None = not sure)."""
    from core import household_statements as hs
    from core.database import MedicalProvider
    p = session.get(MedicalProvider, int(provider_id or 0))
    if p is None:
        return None, 'That provider was not found.'
    utt = hs.utter(session, {'statement': 'provider_kind', 'medical_provider_id': p.id, 'nonprofit_hospital': value})
    p.nonprofit_hospital, p.said_utterance_id = value, utt.id
    session.flush()
    return p, None


def link_payment(session, account_id, transaction_id):
    """L2/L5: "this payment was toward this bill" - a payment (item 93 B3) toward the bill's obligation. A card charge is
    linked the same way: it is then a payment toward the bill, and the card's balance is card debt, counted once."""
    from core import household_statements as hs
    from core.database import PAYMENT_IN_RESPECT_OF_OBLIGATION, MedicalBillAccount, MedicalProvider, Transaction
    a = session.get(MedicalBillAccount, int(account_id or 0))
    t = session.get(Transaction, int(transaction_id or 0))
    if a is None or t is None:
        return None, 'That bill or that line was not found.'
    if not a.obligation_id:
        return None, 'Say the bill is yours to pay first; a payment can only be toward an obligation you have.'
    if t.type != 'debit':
        return None, 'Only money out can be a payment toward a bill.'
    if t.id in {x['transaction_id'] for x in payments(session, a.obligation_id)}:
        return a, None
    prov = session.get(MedicalProvider, a.provider_id)
    utt = hs.utter(session, {'statement': 'toward_bill', 'medical_bill_account_id': a.id, 'transaction_id': t.id})
    rec, _ = hs._payment_for(session, t, utt, payee=prov.name if prov else None, via='bill')
    hs._prop(session, PAYMENT_IN_RESPECT_OF_OBLIGATION, utt, None, None, subject_payment_id=rec.payment_id,
             object_obligation_id=a.obligation_id)
    session.flush()
    return a, None


# ── Item 101 (COLLECTIONS.md C1-C6): a bill sent to collections ───────────────────────────────────────────────────────

def _collection_of(session, account_id):
    """The link that makes this account a collection, or None."""
    from core.database import MedicalCollection
    return session.query(MedicalCollection).filter_by(collection_account_id=account_id).first()


def _sent_of(session, account_id):
    """The link that sent this bill to collections, or None."""
    from core.database import MedicalCollection
    return session.query(MedicalCollection).filter_by(of_account_id=account_id).order_by(MedicalCollection.id.desc()).first()


def send_to_collections(session, account_id, body):
    """C2: "this bill went to collections with X" - {collector, account_number, sent_on, amount, statement_date}. The
    household's statement: the collector's account carries the bill's obligation (one debt that changed hands; minted
    now if the bill wasn't yet said to be theirs), and the collector's stated balance is its first statement."""
    from core import household_statements as hs
    from core.database import MedicalBillAccount, MedicalBillStatement, MedicalCollection, MedicalProvider, Obligation
    a = session.get(MedicalBillAccount, int(account_id or 0))
    if a is None:
        return None, 'That bill was not found.'
    if _collection_of(session, a.id) is not None:
        return None, 'This is already a collection.'
    name = ' '.join(str(body.get('collector') or '').split())[:160]
    sent = _iso_or_none(body.get('sent_on'))
    try:
        amount = round(float(body.get('amount')), 2)
    except (TypeError, ValueError):
        amount = None
    if not name or not sent or amount is None or amount < 0:
        return None, 'The collector\'s name, the date and the balance the collector states are needed.'
    acct_no = ' '.join(str(body.get('account_number') or '').split())[:60]
    utt = hs.utter(session, {'statement': 'went_to_collections', 'medical_bill_account_id': a.id, 'collector': name,
                             'account_number': acct_no, 'sent_on': sent, 'stated_balance': f'{amount:.2f}'})
    if not a.obligation_id:                                   # sending it on is the household saying it is theirs
        ob = Obligation(minted_by_id=utt.id)
        session.add(ob)
        session.flush()
        a.obligation_id, a.mine_utterance_id = ob.id, utt.id
    prov = next((p for p in session.query(MedicalProvider).all() if p.name.lower() == name.lower()), None)
    if prov is None:
        prov = MedicalProvider(name=name)
        session.add(prov)
        session.flush()
    col = MedicalBillAccount(provider_id=prov.id, account_number=acct_no, obligation_id=a.obligation_id,
                             mine_utterance_id=utt.id)
    session.add(col)
    session.flush()
    session.add(MedicalCollection(collection_account_id=col.id, of_account_id=a.id, sent_on=sent, said_utterance_id=utt.id))
    session.add(MedicalBillStatement(account_id=col.id, source='collector',
                                     statement_date=_iso_or_none(body.get('statement_date')) or sent, amount=amount,
                                     due_date=_iso_or_none(body.get('due_date')), typed_utterance_id=utt.id))
    session.flush()
    return col, None


def running_balance(sts, paid):
    """C4: the collector's statements and the payments after each, oldest first, with the balance after each line.
    A statement sets the balance as of its date (whatever fees it adds are in it, C5); a payment after it lowers it;
    a payment on or before the newest statement may already be in it, and is said so, never subtracted twice."""
    events = [(s.statement_date, 0, 'statement', s) for s in sts] + [(p['date'], 1, 'payment', p) for p in paid]
    rows, bal, last = [], None, ''
    for d_, _o, kind, x in sorted(events, key=lambda e: (e[0], e[1])):
        if kind == 'statement':
            bal, last = x.amount, x.statement_date
            rows.append({'date': d_, 'what': f'The collector states {money(x.amount)}', 'balance': round(bal, 2)})
        elif bal is not None and d_ > last:
            bal = max(0.0, bal - x['amount'])
            rows.append({'date': d_, 'what': f'You paid {money(x["amount"])}' + (' by card' if x['card'] else ''),
                         'balance': round(bal, 2)})
        else:
            rows.append({'date': d_, 'what': f'You paid {money(x["amount"])} - on or before the collector\'s statement '
                                             f'of {_says(last) if last else "its first statement"}, so it may already be in it',
                         'balance': round(bal, 2) if bal is not None else None})
    return rows


def payments(session, obligation_id):
    """The payments the household said were toward this obligation, each with its line: [{transaction_id, amount, date,
    account, card}] oldest first."""
    from core.database import (PAYMENT_IN_RESPECT_OF_OBLIGATION, Account, LedgerLineRecord, Proposition, Transaction)
    if not obligation_id:
        return []
    pay_ids = {p.subject_payment_id for p in session.query(Proposition).filter_by(
        kind=PAYMENT_IN_RESPECT_OF_OBLIGATION, object_obligation_id=obligation_id).all() if p.subject_payment_id}
    out = []
    for rec in session.query(LedgerLineRecord).filter(LedgerLineRecord.payment_id.in_(pay_ids)).all() if pay_ids else []:
        t = session.get(Transaction, rec.transaction_id)
        if t is None:
            continue
        acct = session.get(Account, t.account_id) if t.account_id else None
        out.append({'transaction_id': t.id, 'amount': round(float(t.amount or 0), 2),
                    'date': t.date.isoformat() if t.date else '', 'account': acct.name if acct else '',
                    'card': bool(acct and (acct.type or '') in ('credit', 'credit_card'))})
    return sorted(out, key=lambda x: (x['date'], x['transaction_id']))


# ── The bill as it stands (L2-L8) ────────────────────────────────────────────────────────────────────────────────────

def _words(text):
    return {w for w in re.findall(r'[a-z]{4,}', str(text or '').lower()) if w not in _NOISE}


def _candidates(session, name, linked, since, ceiling, limit=4):
    """L5: lines that may be a payment on this bill - a word of the provider's name in the line, an amount no more than
    the bill, after `since`. Named only; never linked, never netted."""
    from core.database import Account, Transaction
    words = _words(name)
    if not words:
        return []
    out = []
    for t in session.query(Transaction).filter(Transaction.type == 'debit', Transaction.date >= since) \
            .order_by(Transaction.date.desc()).limit(2000).all():
        if t.id in linked or float(t.amount or 0) > ceiling + 0.005:
            continue
        if words & _words(f'{t.merchant or ""} {t.description or ""}'):
            acct = session.get(Account, t.account_id) if t.account_id else None
            card = bool(acct and (acct.type or '') in ('credit', 'credit_card'))
            out.append({'transaction_id': t.id, 'amount': round(float(t.amount or 0), 2),
                        'date': t.date.isoformat() if t.date else '', 'card': card,
                        'sentence': f'A {money(t.amount)} {"card charge" if card else "payment"} to '
                                    f'{(t.merchant or t.description or "").strip()[:60]} on {_says(t.date)} may be this '
                                    f'bill; Groundwork counts both until you say.'})
        if len(out) >= limit:
            break
    return out


def _arrangement_end(arr):
    first = _day(arr.get('first_date'))
    if not first:
        return None
    m = first.month - 1 + int(arr['payments']) - 1
    return date(first.year + m // 12, m % 12 + 1, 1)


def _statement_line(s):
    what = {'provider': 'Bill', 'insurer': "Insurer's explanation of benefits", 'collector': "Collector's statement"}[s.source]
    due = ' due ' + _says(s.due_date) if s.due_date else ''
    mine = ' (your responsibility)' if s.source == 'insurer' else ''
    return f'{what} dated {_says(s.statement_date)}: {money(s.amount)}{due}{mine}.'


def view(session, a, ctx, today=None):
    """One bill account as the household sees it: its statements, the amount owed now with its working, and every note
    the record supports. `ctx`: {liquid, liquid_known, reserve, floor, capacity}."""
    from core.database import MedicalBillStatement, MedicalProvider
    today = today or date.today()
    prov = session.get(MedicalProvider, a.provider_id)
    sts = session.query(MedicalBillStatement).filter_by(account_id=a.id).order_by(
        MedicalBillStatement.statement_date, MedicalBillStatement.id).all()
    paid = payments(session, a.obligation_id)
    col_link, sent_link = _collection_of(session, a.id), _sent_of(session, a.id)
    if col_link is not None:                 # item 101: one debt that changed hands - from the hand-off on, the collector's
        paid = [p for p in paid if p['date'] >= (col_link.sent_on or '')]
    elif sent_link is not None:
        paid = [p for p in paid if p['date'] < (sent_link.sent_on or '9999')]
    claim = (_hist(a.claim_json) or [{}])[-1]
    arr = (_hist(a.arrangement_json) or [{}])[-1]
    arr = arr if arr.get('monthly') else None
    pending = bool(claim.get('pending'))
    lines, notes = [], []
    statements = [{'id': s.id, 'source': s.source, 'date': s.statement_date, 'amount': s.amount, 'due': s.due_date,
                   'service': [s.service_from, s.service_to], 'line': _statement_line(s)} for s in sts]
    out = {'id': a.id, 'provider': prov.name if prov else '', 'provider_id': a.provider_id,
           'account_number': a.account_number or '', 'mine': bool(a.obligation_id), 'statements': statements,
           'payments': paid, 'claim_pending': pending, 'arrangement': arr, 'nonprofit_hospital': prov.nonprofit_hospital
           if prov else None, 'owed': None, 'datable': False, 'lines': lines, 'notes': notes, 'candidates': [],
           'facts': [], 'capacity': None, 'attention': None, 'never_directs': NEVER_DIRECTS,
           'collection': None, 'sent_to': None}
    if sent_link is not None:                # C2: the amount now lives under the collection - counted once, there
        from core.database import MedicalBillAccount as _MBA
        ca = session.get(_MBA, sent_link.collection_account_id)
        cp = session.get(MedicalProvider, ca.provider_id) if ca else None
        out['sent_to'] = {'collection_id': sent_link.collection_account_id, 'collector': cp.name if cp else '',
                          'sent_on': sent_link.sent_on}
        out['owed'] = 0.0
        notes.append(f'Sent to collections with {cp.name if cp else "a collector"} on {_says(sent_link.sent_on)}. '
                     'Its balance is kept there, so it is counted once.')
        return out
    if col_link is not None:
        from core.database import MedicalBillAccount as _MBA
        oa = session.get(_MBA, col_link.of_account_id)
        op = session.get(MedicalProvider, oa.provider_id) if oa else None
        out['collection'] = {'of_provider': op.name if op else '', 'sent_on': col_link.sent_on,
                             'running': running_balance(sts, paid), 'legal_note': LEGAL_NOTE}
        out['nonprofit_hospital'] = None    # L7's facts are about the hospital, not the collector
    if not sts:
        return out
    cur = sts[-1]                                                            # the newest statement is the current position
    after = [p for p in paid if p['date'] > cur.statement_date]
    owed = round(max(0.0, cur.amount - sum(p['amount'] for p in after)), 2)
    out['owed'] = owed
    who = {'provider': 'The bill', 'insurer': 'The insurer', 'collector': "The collector's statement"}[cur.source]
    lines.append(f'{who} dated {_says(cur.statement_date)} gives {money(cur.amount)}.')
    for p in after:
        lines.append(f'Less {money(p["amount"])} you said you paid toward it on {_says(p["date"])}'
                     f'{" by card (" + p["account"] + ")" if p["card"] else ""}.')
    lines.append(f'Amount owed now: {money(owed)}' + (', as you\'ve recorded it.' if after else '.'))
    # L2: a payment between the previous statement and the newest - the bill may or may not reflect it
    prev = [s for s in sts[:-1] if s.source == cur.source]
    if prev:
        for p in paid:
            if prev[-1].statement_date < p['date'] <= cur.statement_date:
                notes.append(f'The bill doesn\'t show whether the {money(p["amount"])} paid on {_says(p["date"])} was applied.')
    # L2: two issuers that disagree - both shown, the newer current, the disagreement named
    by_src = {}
    for s in sts:
        by_src[s.source] = s
    disagree = len(by_src) == 2 and abs(by_src['provider'].amount - by_src['insurer'].amount) > 0.005
    if disagree:
        pv, ins = by_src['provider'], by_src['insurer']
        newer = pv if (pv.statement_date, pv.id) > (ins.statement_date, ins.id) else ins
        notes.append(f'The provider\'s bill ({_says(pv.statement_date)}) gives {money(pv.amount)}; the insurer\'s '
                     f'explanation of benefits ({_says(ins.statement_date)}) gives {money(ins.amount)} as your '
                     f'responsibility. The newer, from the {newer.source}, is used above; the difference isn\'t resolved.')
    if pending:                                                              # L3
        notes.append('May change: the insurer\'s claim is pending (as you said).')
    if arr:                                                                  # L4
        end = _arrangement_end(arr)
        lines.append(f'Payment arrangement, as you reported the provider\'s terms: {money(arr["monthly"])} a month, '
                     f'{arr["payments"]} payments from {_says(arr["first_date"])}'
                     f'{", the last in " + end.strftime("%B %Y") if end else ""}.')
    if not a.obligation_id:
        notes.append('Not yours to pay yet: a bill becomes something you owe only when you say so.')
    out['datable'] = bool(a.obligation_id and owed > 0 and arr and not pending and not disagree)
    out['undatable_reason'] = None if out['datable'] or not (a.obligation_id and owed > 0) else (
        'a claim is pending' if pending else 'its statements disagree' if disagree else 'no payment arrangement')
    # L5: look-alike lines, named only
    if a.obligation_id and owed > 0:
        since = (_day(cur.service_from) or _day(cur.statement_date)) - timedelta(days=CANDIDATE_DAYS // 4)
        out['candidates'] = _candidates(session, prov.name if prov else '', {p['transaction_id'] for p in paid},
                                        min(since, today - timedelta(days=CANDIDATE_DAYS)), cur.amount)
    if prov is not None and prov.nonprofit_hospital and col_link is None:     # L7 (the hospital, never the collector)
        out['facts'] = list(NONPROFIT_FACTS) + [NO_ASSISTANCE_SHOWN]
    if a.obligation_id and owed > 0:
        out['capacity'] = sustains(owed, ctx.get('capacity'))                # L8
        out['attention'] = attention(out, cur, ctx, today)                   # L6
    return out


def sustains(owed, cap):
    """L8: three durations with their monthly amounts, each marked by what the record sustains - never an offer.
    `cap`: {monthly, months, leanest} or {thin: True, months}."""
    if not cap:
        return None
    if cap.get('thin'):
        return {'thin': True, 'sentence': f'Your record is too thin to name a figure: {cap.get("months", 0)} complete '
                                          f'month{"" if cap.get("months") == 1 else "s"} on record.'}
    rows = []
    for n in DURATIONS:
        m = round(owed / n + 0.004, 2)
        ok = cap['monthly'] is not None and m <= cap['monthly'] + 0.005
        rows.append({'months': n, 'monthly': m, 'sustained': ok,
                     'line': f'{money(m)} a month for {n} months: {"your record sustains this" if ok else "more than your record sustains"}.'})
    fill = float(cap.get('reserve_monthly') or 0)
    working = (f'Your leanest month on record, {cap["leanest"]}, left {money(cap["left"])} after its spending'
               + (f', less {money(fill)} a month going to your reserve' if fill > 0 else '') + '.')
    head = working + (f' Your record sustains {money(cap["monthly"])} a month.' if cap['monthly'] > 0
                      else ' Your record sustains no monthly amount toward this bill.')
    return {'thin': False, 'sentence': head, 'rows': rows}


def attention(v, cur, ctx, today):
    """L6: `bill_due` when paying in full would leave savings below the reserve or the stability floor, or when it
    can't be paid in full from what's on record - never because of the bill's size. Not while a claim is pending."""
    due = _day(cur.due_date) or _day((v.get('arrangement') or {}).get('first_date'))
    if v['claim_pending'] or not due:
        return None
    days = (due - today).days
    if days > ATTENTION_DAYS:
        return None
    owed, liquid = v['owed'], float(ctx.get('liquid') or 0)
    reserve, floor = float(ctx.get('reserve') or 0), float(ctx.get('floor') or 0)
    left = round(liquid - owed, 2)
    if not ctx.get('liquid_known') or owed > liquid + 0.005:
        sentence = (f'This {money(owed)} bill can\'t be paid in full from what\'s on record'
                    + (f': savings on record are {money(liquid)}.' if ctx.get('liquid_known') else ': no savings balance is on record.'))
    elif reserve > 0 and left < reserve - 0.005:
        sentence = f'Paying this {money(owed)} bill in full would leave {money(left)} in savings, below your {money(reserve)} reserve.'
    elif floor > 0 and left < floor - 0.005:
        sentence = (f'Paying this {money(owed)} bill in full would leave {money(left)} in savings, below one month of your '
                    f'recorded expenses ({money(floor)}).')
    else:
        return None
    return {'kind': 'bill_due', 'subject': str(v['id']), 'title': v['provider'], 'due': due.isoformat(), 'days': days,
            'owed': owed, 'sentence': sentence, 'fact': f'{due.isoformat()}|{owed:.2f}'}


def obligations_date(views, card_free_months, today=None):
    """L9: the all-obligations date beside the card-free date (card balances only). No date when any included obligation
    can't be dated; the ones that can't are named. `card_free_months`: the engine's months, or None."""
    today = today or date.today()

    def label(months):
        m = today.month - 1 + months
        return date(today.year + m // 12, m % 12 + 1, 1).strftime('%B %Y')

    card = (f'Card balances only: {label(card_free_months)}.' if card_free_months is not None
            else 'Card balances only: not reached at the budget on record.')
    owing = [v for v in views if v['mine'] and (v['owed'] or 0) > 0]
    stuck = [v for v in owing if not v['datable']]
    if card_free_months is None:
        return {'card_free': card, 'all': None, 'sentence': 'The all-obligations date can\'t be calculated: the card-free '
                                                            'date isn\'t reached at the budget on record.', 'stuck': []}
    if stuck:
        n = len(stuck)
        return {'card_free': card, 'all': None, 'stuck': [{'id': v['id'], 'provider': v['provider'],
                                                            'why': v['undatable_reason']} for v in stuck],
                'sentence': f'The all-obligations date can\'t be calculated reliably: {n} obligation{"s have" if n > 1 else " has"} '
                            f'no schedule ({"; ".join(v["provider"] + ", " + v["undatable_reason"] for v in stuck)}).'}
    ends = [today.replace(day=1)]
    m = today.month - 1 + card_free_months
    ends.append(date(today.year + m // 12, m % 12 + 1, 1))
    for v in owing:
        e = _arrangement_end(v['arrangement'])
        if e:
            ends.append(e)
    last = max(ends)
    return {'card_free': card, 'all': last.strftime('%B %Y'), 'stuck': [],
            'sentence': f'All obligations on record: {last.strftime("%B %Y")}, the later of the card-free date and the last '
                        f'payment of each agreed arrangement.'}
