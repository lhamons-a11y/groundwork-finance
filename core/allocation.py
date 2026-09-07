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
    plan: str = None
    events: list = field(default_factory=list)
    provenance: list = field(default_factory=list)
    merged_from: list = field(default_factory=list)
    _seq: int = 0
    _effective: float = 0.0


# ── Recording ───────────────────────────────────────────────────────────────

def new_expense(amount=0.0, incurred_on=None, person=None, plan=None):
    e = Expense(amount=float(amount or 0.0), incurred_on=incurred_on, person=person,
                plan=plan)
    e.provenance.append({'kind': 'created', 'at': _now(), 'amount': e.amount,
                         'incurred_on': incurred_on, 'person': person, 'plan': plan})
    _record(e, 'expense_created', {'amount': e.amount, 'plan': plan,
                                   'incurred_on': incurred_on})
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
    'correct_expense': 'expense_corrected',
    'import_eob': 'eob_imported',
    'change_plan': 'plan_changed',
    'roll_year': 'year_rolled',
    'change_rules': 'rules_changed',
    'record_determination': 'determination_recorded',
    'delete_allocation': 'allocation_deleted',
}


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
    plan_timeline = []          # (effective_date, plan)
    funders = {}                # funder -> Payment
    determinations = []
    current_rules = None
    changes = []

    for ev in sorted(e.events, key=lambda v: (v.effective_seq, v.recorded_seq)):
        p = ev.payload
        if ev.kind == 'expense_created':
            obligation = float(p.get('amount') or 0.0)
            if p.get('plan'):
                plan_timeline.append((p.get('incurred_on') or '', p['plan']))
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
            if p['funder'] in funders:
                was = funders[p['funder']].amount
                funders[p['funder']].amount = 0.0
                changes.append({'what': 'allocation', 'funder': p['funder'],
                                'from': was, 'to': 0.0, 'mode': 'void'})
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
        elif ev.kind == 'plan_changed':
            plan_timeline.append((p.get('effective') or '', p['to']))
        elif ev.kind == 'rules_changed':
            current_rules = p.get('to')
        elif ev.kind == 'determination_recorded':
            determinations.append(DeterminationRecord(
                status=p['status'], amount=float(p.get('amount') or 0.0),
                evidence=p.get('evidence'), determined_at=ev.recorded_at,
                rule_version=current_rules))
        elif ev.kind == 'year_rolled':
            # A new plan year does not reach backwards. The expense stays in the year it
            # was incurred, on the plan in force then.
            pass

    return {'obligation': obligation, 'funders': funders, 'plan_timeline': plan_timeline,
            'determinations': determinations, 'rules': current_rules, 'changes': changes}


def _current_determination(folded):
    """The latest determination. Superseded, never overwritten — the earlier ones stay."""
    return folded['determinations'][-1] if folded['determinations'] else None


def _plan_at(folded, when):
    """The plan in force when the expense was incurred, not the plan in force now. A plan
    change on 1 July does not move a January expense."""
    eligible = [p for (eff, p) in folded['plan_timeline'] if not eff or eff <= (when or '')]
    return eligible[-1] if eligible else None


def _effective_obligation(folded):
    """What is owed after any determination that reduced the obligation. A provider
    write-off closes part of it; `unpaid` closes none of it."""
    reduced = sum(d.amount for d in folded['determinations']
                  if d.status in REDUCES_OBLIGATION)
    return round(folded['obligation'] - reduced, 2)


def _funded(folded):
    total = sum(p.amount for p in folded['funders'].values())
    total += sum(d.amount for d in folded['determinations'] if d.status in USER_FUNDING)
    return round(total, 2)


def state(e):
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
    out['expense_plan'] = _plan_at(f, e.incurred_on)
    out['expense_year'] = int((e.incurred_on or '0000')[:4])
    out['status'] = det.status if det else 'unknown'
    out['outstanding'] = round(gross - _funded(f), 2)
    return out


def unallocated(e):
    return state(e)['unallocated']


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


def explain_change(e):
    """What changed, from what, to what, and under which mode."""
    changes = _fold(e)['changes']
    return changes[-1] if changes else None


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
