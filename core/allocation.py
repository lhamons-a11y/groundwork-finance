# -*- coding: utf-8 -*-
"""Healthcare obligations, funding and reconciliation — what can be proven, and what cannot.

Implements `gw 2.0/OBLIGATION_SEMANTICS_QUESTION.md`, and is specified by
`tests/test_lifecycle_fixture.py`, which was written before this file existed, against
nothing, deliberately.

**The three kinds of thing, kept apart.** An obligation is what a provider claims. A funding
event is money that moved. Reconciliation is the relationship between them — and the gap
between the two is an *observation about the record*, never an explanation of what happened
to the money:

    obligation  ->  funding evidence  ->  reconciliation state  ->  determination
                ->  established facts  ->  tax interpretation

with a hard boundary before that last arrow: **reconciliation establishes reality, tax rules
interpret established reality.** No tax logic lives inside a determination.

**The $650 that started it.** `$1,200 - $250 = $950` assumes everything unreimbursed was paid
by the user; `$1,200 - $250 - $650 = $300` assumes everything unreconciled went unpaid. Both
assign meaning to an unknown. So the qualifying figure is a *sum of evidenced payments*, never
a subtraction, and while any part is unresolved there is **no definitive total at all** —
`UNRESOLVED`, which is not zero and deliberately not `None`.

**Determinations, not resolutions.** Nothing here is terminal: `unpaid` becomes
`user_paid_cash` when a receipt surfaces six months later, and a write-off reverses if the
provider re-bills. Determinations are superseded rather than overwritten, each carrying
provenance and a date.

**This module does not know what plan covered an expense, and must not guess.** Coverage
periods are household facts owned by `core/plan_year.py`; an expense knows the date it was
incurred and nothing more. So `state()` reports the plan it was *told*, and `UNRESOLVED` when
nobody told it — which is a different answer from `None`, meaning no plan covered that date.
Two modules deriving one fact from two places is the fusion the architecture is written
against, and it was caught when the schema had to pick one.

**Reversal, refund and correction are three different things**, and a single `-$1,000`
collapses all of them:

    correction   the figure was always wrong - there was never a distribution
    reversal     there WAS a payment and it came back; the obligation still stands
    refund       the obligation itself shrank, and someone got money back

They can land on the same `$0` today and their futures differ, which is exactly the condition
under which states get merged and a later consumer arrives that must tell them apart. The
consumer here is a tax figure: an HSA distribution that was unwound is not a qualified
distribution, and a model that only zeroes the allocation has destroyed the fact that the
distribution ever happened. So a reversal records what it unwound, and `unwound` is reported
beside the funding rather than folded into it.

**A refund names who received it.** Otherwise the obligation falls and the payer still shows
the full amount paid, and the deduction is overstated by exactly the refund — money back in
their pocket and still on their return.

**Correction is not retraction, and the same present balance can be reached by either.**

    created $400 -> corrected to $275        one obligation, restated
    created $400 -> voided -> new $275       two obligations, one retracted

Both end owing $275, and that is the *only* thing they share. A correction says *we had the
amount wrong*; a retraction says *that bill was not real, this one is*. The distinction has to
survive, because a payment attached to the retracted bill is not a payment against its
replacement — and collapsing them makes $275 look satisfied by money attached to an obligation
nobody owes.

**A retraction is a state, not a removal.** Hard deletion is prohibited once financial
relationships exist, so `void_obligation` sets the obligation to nothing and keeps the record,
its reason, its date, and whatever was attached to it.

**Events fold in effective order, not arrival order.** An EOB imported in March describes
January, and a correction may have been recorded in February. Imports are retroactive by
nature, so arrival order is not an edge case — it is the normal case, and a model whose answer
depends on it is wrong for most real users.
"""

import copy
from dataclasses import dataclass, field
from datetime import datetime

# Not zero, not None, and not a number a caller can accidentally add to something. Absence is
# not zero; a consumer that wants a total must be made to say so.
UNRESOLVED = object()

# What confirms a payment — the same three signals debt already uses, and nothing weaker is
# inferred. `cleared` alone is insufficient because it defaults to True, which cannot
# distinguish "the bank settled this" from "the user typed it and the default applied".
CONFIRMS_ON = frozenset(('cleared', 'attached', 'user_confirmed'))

# Determinations that settle the EVIDENTIARY question — is every dollar accounted for? —
# which is a different question from whether the obligation is closed.
SETTLING = frozenset(('provider_adjustment', 'user_paid_cash', 'unpaid'))

# `pending_claim` is deliberately absent above: it says nobody yet knows who bears the cost,
# which settles nothing. It produces the same tax figure as `unpaid` today and is not the same
# state — one says nobody paid, the other says nobody yet knows — and their futures differ.
REDUCES_OBLIGATION = frozenset(('provider_adjustment',))
USER_FUNDING = frozenset(('user_paid_cash',))

DELETION_MODES = ('correction', 'void', 'destruction')


def _now():
    return datetime.utcnow().isoformat(timespec='seconds')


@dataclass
class Event:
    """One thing that happened, or one thing we learned. `effective_seq` is when it takes
    effect; `recorded_seq` is when we heard about it. Folding uses the first and breaks ties
    with the second, which is what makes arrival order irrelevant."""
    kind: str
    payload: dict = field(default_factory=dict)
    effective_seq: float = 0.0
    recorded_seq: int = 0
    recorded_at: str = None


@dataclass
class Payment:
    """A funding event by a named funder. Confirmed only when all three signals hold."""
    funder: str
    amount: float
    cleared: bool = True
    attached: bool = True
    user_confirmed: bool = True
    source: str = 'manual'      # imported vs manual: both legitimate, different provenance

    @property
    def confirmed(self):
        return bool(self.cleared and self.attached and self.user_confirmed)


@dataclass
class DeterminationRecord:
    status: str
    amount: float
    evidence: str = None
    determined_at: str = None
    rule_version: str = None


@dataclass
class Expense:
    amount: float = 0.0
    incurred_on: str = None
    person: str = None
    events: list = field(default_factory=list)
    provenance: list = field(default_factory=list)
    merged_from: list = field(default_factory=list)
    # A retraction points forward to what replaced it, and the replacement points back. Two
    # links rather than one, because either end may be the one in hand.
    replaced_by_ref: object = None
    replaces_ref: object = None
    _seq: int = 0
    _effective: float = 0.0


# ── Recording ───────────────────────────────────────────────────────────────

def new_expense(amount=0.0, incurred_on=None, person=None):
    """No `plan` argument, deliberately. Which plan covered this charge is a household fact
    derived from the period covering `incurred_on`, and storing a copy here would be a second
    source of truth that can drift from the first."""
    e = Expense(amount=float(amount or 0.0), incurred_on=incurred_on, person=person)
    e.provenance.append({'kind': 'created', 'at': _now(), 'amount': e.amount,
                         'incurred_on': incurred_on, 'person': person})
    _record(e, 'expense_created', {'amount': e.amount, 'incurred_on': incurred_on})
    return e


def _record(e, kind, payload, effective_seq=None):
    e._seq += 1
    if effective_seq is None:
        e._effective += 1.0
        effective_seq = e._effective
    else:
        e._effective = max(e._effective, float(effective_seq))
    e.events.append(Event(kind=kind, payload=dict(payload), effective_seq=float(effective_seq),
                          recorded_seq=e._seq, recorded_at=_now()))
    return e


def allocate(e, funder=None, amount=0.0, cleared=True, attached=True, user_confirmed=True,
             source='manual', effective_seq=None):
    return _record(e, 'allocated', {'funder': funder, 'amount': float(amount or 0.0),
                                    'cleared': cleared, 'attached': attached,
                                    'user_confirmed': user_confirmed, 'source': source},
                   effective_seq)


_OPS = {
    'correct_allocation': 'allocation_corrected',
    'reverse_allocation': 'allocation_reversed',
    'reinstate_allocation': 'allocation_reinstated',
    'refund': 'obligation_refunded',
    'correct_expense': 'expense_corrected',
    'import_eob': 'eob_imported',
    'roll_year': 'year_rolled',
    'change_rules': 'rules_changed',
    'record_determination': 'determination_recorded',
    'delete_allocation': 'allocation_deleted',
    'void_obligation': 'obligation_voided',
}

# Present so a caller can ask whether this build understands retraction, rather than
# discovering it from an exception.
void_obligation_supported = True


def apply(e, op, effective_seq=None):
    """Apply one operation. Returns the expense, so callers can chain or assert on it."""
    kind = _OPS.get((op or {}).get('kind'))
    if kind is None:
        raise ValueError('unknown operation: %r' % (op or {}).get('kind'))
    payload = {k: v for k, v in op.items() if k != 'kind'}
    _record(e, kind, payload, effective_seq)
    e.provenance.append({'kind': kind, 'at': _now(), **payload})
    return e


def branch(e):
    """An independent copy, for asking what a different determination would mean."""
    return copy.deepcopy(e)


# ── Folding: state is derived, never stored ─────────────────────────────────

def _fold(e):
    """Replay the events in EFFECTIVE order. Nothing about the answer may depend on the
    order the facts arrived in."""
    obligation = 0.0
    voided = None
    funders = {}                # funder -> Payment
    unwound = {}                # funder -> amount that moved and then came back
    refunds = []
    determinations = []
    current_rules = None
    changes = []

    for ev in sorted(e.events, key=lambda v: (v.effective_seq, v.recorded_seq)):
        p = ev.payload
        if ev.kind == 'expense_created':
            obligation = float(p.get('amount') or 0.0)
        elif ev.kind == 'allocated':
            funders[p['funder']] = Payment(
                funder=p['funder'], amount=float(p['amount']),
                cleared=p.get('cleared', True), attached=p.get('attached', True),
                user_confirmed=p.get('user_confirmed', True),
                source=p.get('source', 'manual'))
        elif ev.kind == 'allocation_corrected':
            if p['funder'] in funders:
                was = funders[p['funder']].amount
                funders[p['funder']].amount = float(p['to'])
                changes.append({'what': 'allocation', 'funder': p['funder'],
                                'from': was, 'to': float(p['to']), 'mode': 'correction'})
        elif ev.kind == 'allocation_reversed':
            # The money moved and came back. The amount stops counting as funding and starts
            # counting as unwound - it does not disappear, because "no HSA distribution" and
            # "an HSA distribution that was reversed" are different facts to a tax consumer.
            if p['funder'] in funders:
                was = funders[p['funder']].amount
                funders[p['funder']].amount = 0.0
                unwound[p['funder']] = unwound.get(p['funder'], 0.0) + was
                changes.append({'what': 'allocation', 'funder': p['funder'],
                                'from': was, 'to': 0.0, 'mode': 'reversal',
                                'occurred_on': p.get('occurred_on')})
        elif ev.kind == 'allocation_reinstated':
            # A disputed charge can come back. Nothing here is terminal.
            back = unwound.pop(p['funder'], 0.0)
            if p['funder'] in funders:
                funders[p['funder']].amount += back
            changes.append({'what': 'allocation', 'funder': p['funder'],
                            'from': 0.0, 'to': back, 'mode': 'reinstatement',
                            'occurred_on': p.get('occurred_on')})
        elif ev.kind == 'obligation_refunded':
            # The obligation itself shrank. Distinct from a correction, which says it was
            # always smaller, and from a reversal, which leaves it standing.
            amount = float(p.get('amount') or 0.0)
            refunds.append(amount)
            to = p.get('to')
            if to in funders:
                funders[to].amount = round(funders[to].amount - amount, 2)
            changes.append({'what': 'obligation', 'from': None, 'to': None,
                            'mode': 'refund', 'amount': amount, 'funder': to,
                            'occurred_on': p.get('occurred_on')})
        elif ev.kind == 'allocation_deleted':
            # "Delete the reimbursement" is ambiguous and must not be one operation: a
            # correction says it never happened and is recoverable, a void says it happened
            # and was undone, destruction removes the record. The caller says which.
            mode = p.get('mode', 'correction')
            if p['funder'] in funders and mode != 'destruction':
                funders[p['funder']].amount = 0.0
            changes.append({'what': 'allocation', 'funder': p['funder'], 'mode': mode})
        elif ev.kind == 'expense_corrected':
            was, obligation = obligation, float(p['to'])
            changes.append({'what': 'obligation', 'from': was, 'to': obligation,
                            'mode': 'correction'})
        elif ev.kind == 'eob_imported':
            # A duplicate EOB describes funding already recorded. It must not create a
            # second funding event, or one payment funds the same bill twice.
            dup = p.get('duplicate_of')
            if dup is None or dup not in funders:
                if p.get('funder'):
                    funders[p['funder']] = Payment(funder=p['funder'],
                                                   amount=float(p.get('amount') or 0.0),
                                                   source='imported')
        elif ev.kind == 'rules_changed':
            current_rules = p.get('to')
        elif ev.kind == 'determination_recorded':
            determinations.append(DeterminationRecord(
                status=p['status'], amount=float(p.get('amount') or 0.0),
                evidence=p.get('evidence'), determined_at=ev.recorded_at,
                rule_version=current_rules))
        elif ev.kind == 'obligation_voided':
            # The obligation goes to nothing and the record stays. Anything attached to it
            # stays attached, which is what makes the resulting negative unallocated a state
            # a user can be shown and asked about rather than an error to hide.
            voided = {'at': ev.recorded_at, 'reason': p.get('reason'),
                      'occurred_on': p.get('occurred_on')}
            obligation = 0.0
            changes.append({'what': 'obligation', 'from': None, 'to': 0.0,
                            'mode': 'void', 'reason': p.get('reason'),
                            'occurred_on': p.get('occurred_on')})
        elif ev.kind == 'year_rolled':
            # A new plan year does not reach backwards. The expense stays in the year it
            # was incurred, and the plan is looked up for that date rather than the present.
            pass

    return {'obligation': obligation, 'funders': funders, 'unwound': unwound,
            'refunds': refunds, 'determinations': determinations, 'rules': current_rules,
            'changes': changes, 'voided': voided}


def _current_determination(folded):
    """The latest determination. Superseded, never overwritten — the earlier ones stay."""
    return folded['determinations'][-1] if folded['determinations'] else None


def _effective_obligation(folded):
    """What is owed after anything that reduced the obligation itself.

    Two different reducers, deliberately summed here and recorded separately above: a provider
    write-off (a determination about an unresolved amount) and a refund (money returned on an
    obligation that was correct). A reversal is not one of them - it unwinds funding and
    leaves what is owed exactly where it was.
    """
    reduced = sum(d.amount for d in folded['determinations']
                  if d.status in REDUCES_OBLIGATION)
    return round(folded['obligation'] - reduced - sum(folded['refunds']), 2)


def _funded(folded):
    total = sum(p.amount for p in folded['funders'].values())
    total += sum(d.amount for d in folded['determinations'] if d.status in USER_FUNDING)
    return round(total, 2)


def state(e, plan=UNRESOLVED):
    """Current state, plus the plan the caller resolved for this expense.

    `plan` defaults to `UNRESOLVED` rather than `None` because the two are different answers:
    nobody has told us which plan covered this date, versus no plan covered it. Only a caller
    holding the household record can tell them apart, which is why this asks rather than
    derives — the same division of labour `core/solution.py` uses when it takes
    `months_observed` on trust.
    """
    f = _fold(e)
    gross = _effective_obligation(f)
    out = {name: round(p.amount, 2) for name, p in f['funders'].items()}
    det = _current_determination(f)
    # `unallocated` is the ARITHMETIC gap between an obligation and its funding — an
    # observation about the record. `unresolved` on the figure is the EVIDENTIARY question,
    # and they part company the moment a determination lands: `unpaid` resolves the evidence
    # and leaves the gap exactly where it was.
    out['unallocated'] = round(gross - _funded(f), 2)
    out['expense'] = gross
    out['expense_plan'] = plan
    out['expense_year'] = int((e.incurred_on or '0000')[:4])
    out['status'] = det.status if det else 'unknown'
    out['outstanding'] = round(gross - _funded(f), 2)
    # Reported beside the funding, never folded into it. `hsa: 0` and `hsa: 0, unwound: 1000`
    # are different records, and only the second says a distribution happened.
    out['unwound'] = round(sum(f['unwound'].values()), 2)
    out['refunded'] = round(sum(f['refunds']), 2)
    return out


def unallocated(e):
    return state(e)['unallocated']


# ── Retraction and replacement ──────────────────────────────────────────────

def is_void(e):
    return _fold(e)['voided'] is not None


def void_record(e):
    """Why the obligation was retracted and when. None when it was not."""
    return _fold(e)['voided']


def obligation_versions(e):
    """Every amount this obligation has been stated at. One entry means it was never
    restated — which is how a replacement differs from a correction."""
    f = _fold(e)
    return [c for c in f['changes'] if c['what'] == 'obligation'
            and c.get('mode') == 'correction'] + [{'what': 'obligation',
                                                   'mode': 'original'}]


def link_replacement(old, new):
    """Record that `new` stands in place of `old`. Both directions, because either end may
    be the one a caller is holding."""
    old.replaced_by_ref = new
    new.replaces_ref = old
    old.provenance.append({'kind': 'replaced_by', 'at': _now()})
    new.provenance.append({'kind': 'replaces', 'at': _now()})
    return new


def replaced_by(e):
    return e.replaced_by_ref


def replaces(e):
    return e.replaces_ref


def history_kind(e):
    """What shape this obligation's history has, in terms a user would recognise.

    `corrected`   the amount was restated on the same obligation
    `replacement` this obligation stands in place of one that was retracted
    `retracted`   this obligation was itself retracted
    `original`    neither happened
    """
    if is_void(e):
        return 'retracted'
    if e.replaces_ref is not None:
        return 'replacement'
    if any(c['what'] == 'obligation' and c.get('mode') == 'correction'
           for c in _fold(e)['changes']):
        return 'corrected'
    return 'original'


def household_obligations(expenses):
    """Which obligations a figure may cite. A retracted one is not among them — it is kept
    so the record stays explicable, not so it can be added up."""
    return [e for e in expenses if not is_void(e)]


def histories_equivalent(a, b):
    """Two obligations agreeing on the current balance are NOT thereby the same history.

    Deliberately strict: equivalence requires the same shape of history, not the same number
    at the end. A caller that wants "do these owe the same" should ask that instead.
    """
    return (history_kind(a) == history_kind(b)
            and len(obligation_versions(a)) == len(obligation_versions(b))
            and state(a)['expense'] == state(b)['expense'])


def history_difference(a, b):
    """What actually differs, named rather than merely detected."""
    if histories_equivalent(a, b):
        return None
    out = {}
    if history_kind(a) != history_kind(b):
        out['shape'] = (history_kind(a), history_kind(b))
    if len(obligation_versions(a)) != len(obligation_versions(b)):
        out['restatements'] = (len(obligation_versions(a)), len(obligation_versions(b)))
    if state(a)['expense'] != state(b)['expense']:
        out['balance'] = (state(a)['expense'], state(b)['expense'])
    return out


def determinations(e):
    return list(_fold(e)['determinations'])


# ── What confirms a payment ─────────────────────────────────────────────────

def confirms_on():
    return set(CONFIRMS_ON)


def payment(e, funder='user', amount=0.0, cleared=True, attached=True, user_confirmed=True):
    return Payment(funder=funder, amount=float(amount or 0.0), cleared=cleared,
                   attached=attached, user_confirmed=user_confirmed)


def is_confirmed(p):
    return bool(p.confirmed)


# ── The tax interpretation, which consumes established facts and nothing else ─

@dataclass
class QualifyingFigure:
    gross: float
    confirmed_user_paid: float
    unresolved: float
    total: object
    basis: str
    rules: str
    sources: tuple = ()


def qualifying(e, rules=None):
    """Three parts, and the third is usually unavailable.

    `confirmed_user_paid` is a SUM of evidenced user payments. It is never
    `gross - reimbursed - unresolved`, because that subtraction assumes the unresolved
    amount went unpaid — one of the two guesses this whole model exists to refuse.
    """
    f = _fold(e)
    gross = _effective_obligation(f)

    user_payments = [p for p in f['funders'].values()
                     if p.funder == 'user' and p.confirmed]
    cash = [d for d in f['determinations'] if d.status in USER_FUNDING and d.evidence]
    confirmed = round(sum(p.amount for p in user_payments) + sum(d.amount for d in cash), 2)

    # Evidentially unresolved: the part of the obligation that is neither funded nor covered
    # by a determination that settles what happened to it.
    settled = sum(d.amount for d in f['determinations'] if d.status in SETTLING)
    unresolved = round(max(0.0, gross - sum(p.amount for p in f['funders'].values())
                           - settled), 2)

    return QualifyingFigure(
        gross=gross,
        confirmed_user_paid=confirmed,
        unresolved=unresolved,
        # No definitive total while any part is unresolved. The truth is one of two numbers
        # and nothing in the model knows which, so naming either is a guess — even when the
        # guess would land on the right one.
        total=UNRESOLVED if unresolved > 0 else confirmed,
        basis='sum_of_confirmed_user_payments',
        rules=rules,
        sources=tuple(f['funders'].values()))


def explain(figure):
    """Every reported figure can name the records that produced it."""
    return {'basis': figure.basis, 'rules': figure.rules, 'gross': figure.gross,
            'confirmed_user_paid': figure.confirmed_user_paid,
            'unresolved': figure.unresolved,
            'sources': [{'funder': p.funder, 'amount': p.amount,
                         'confirmed': p.confirmed, 'source': p.source}
                        for p in figure.sources]}


def changes(e):
    """Every recorded change, oldest first. A reversal and the reinstatement that undid it
    both survive; neither overwrites the other."""
    return list(_fold(e)['changes'])


def explain_change(e):
    """What changed, from what, to what, under which mode, and when it happened.

    `occurred_on` is when the money moved, which is not when the expense was incurred and not
    when we heard about it. A 2027 reversal of a 2026 payment is a 2027 event affecting a 2026
    expense, and collapsing those dates loses the year that each belongs to.
    """
    rows = _fold(e)['changes']
    return rows[-1] if rows else None


# ── Arrival order, identity, deletion ───────────────────────────────────────

def replay(expense_kw, allocations, mutations, order=0):
    """Build the same expense from the same facts, arriving in a different sequence.

    Each mutation keeps its position in `mutations` as its EFFECTIVE sequence and is applied
    in a rotated ARRIVAL order. If the two are ever confused, this diverges.
    """
    e = new_expense(**expense_kw)
    for i, a in enumerate(allocations):
        allocate(e, effective_seq=0.1 * (i + 1), **a)

    indexed = list(enumerate(mutations))
    n = len(indexed) or 1
    rotated = indexed[order % n:] + indexed[:order % n]
    for i, (_name, op, _expected) in rotated:
        apply(e, op, effective_seq=float(i + 1))

    return {'state': state(e), 'qualifying_v2026_1': explain(qualifying(e, rules='v2026.1'))}


def merge(a, b):
    """Two records found to be one. Both provenances survive, and it is reversible."""
    merged = branch(a)
    merged.merged_from = [branch(a), branch(b)]
    merged.provenance = list(a.provenance) + list(b.provenance) + [
        {'kind': 'merged', 'at': _now()}]
    return merged


def can_unmerge(e):
    return len(e.merged_from) >= 2


def provenance(e):
    return list(e.provenance)


def deletion_modes():
    return set(DELETION_MODES)
