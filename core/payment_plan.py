# -*- coding: utf-8 -*-
"""Payment state — one coherent projection of a ledger, not five numbers reported side by side.

Gap 6 of `gw 2.0/HEALTHCARE_GAP_TRIAGE.md`, and specified by
`tests/test_payment_state_fixture.py`, written before this file existed.

**The invariant, in Rob's wording:**

> Payment state is a coherent projection of the obligation's transaction history; no
> payment-state dimension may contradict the reconciled transaction ledger or another derived
> payment-state dimension.

**Enforced at the boundary rather than reconstructed by consumers**, which was the specific
thing to check. `payment_state()` computes `paid`, `remaining`, `expected_by_now`, `ahead` and
`overdue` **together, in one pass over the ledger**, and there is no accessor for any one of
them alone. So they cannot drift apart by being read separately, and a consumer cannot assemble
a fifth interpretation of "ahead" that disagrees with this one. `incoherences()` exists so the
projection can be checked against its own ledger rather than trusted.

**Three operations that a signed number would collapse:**

    payment      money toward the obligation
    reversal     a NAMED payment coming back, wholly or partly — never more than it was
    adjustment   the obligation itself changing, which is not a payment at all

A `−$700` entry against $850 paid across three payments, none larger than $500, is not
obviously any of them. It is refused as a reversal — because a reversal names what it reverses,
and no payment here is that size — and accepted as an adjustment only when the caller says
that is what it is. Arithmetic does not get to decide which.

**Ahead and overdue are two names for one distance, never a signed number.** Being behind is
`overdue`, not negative `ahead`, because a user reading *"you are −$525 ahead"* has been handed
arithmetic instead of a sentence.

**The schedule is supplied by the caller and is not an entity here.** Versioning an agreement —
`24 × $175` becoming `18 × $233.33` — is gap 8, it needs a domain object that does not exist,
and inventing one here would hide the gap rather than close it.

**What this module knows, and does not (HAZARD_AUDIT H2).** Every figure here is a projection
over payments the household *attached* to the obligation. The module holds no acknowledgment
from the entitled party and has no way to receive one, so nothing it returns is confirmed
discharge: `paid` is what was attached net of named reversals, `remaining` is what would be
left *if every attached payment is credited*, and `ahead` / `overdue` are positions against
the agreement as the household's own record sees it — not as the creditor does. A payment may
evidence discharge; discharge is established only by the entitled party's acknowledgment
(`gw 2.0/SERVICING_ONLY_CASES.md`, `ACKNOWLEDGMENT_EVIDENCE_CASES.md`, both ruled). Until
that evidence has somewhere to live, the honest reading of `remaining` is *attached
remaining*, and no key returned here may claim otherwise - the fixture asserts the absence.
"""

from dataclasses import dataclass, field
from datetime import datetime

# Returned instead of a value when an operation is refused. Not None, and not a silently
# absorbed no-op: the caller asked for something the model will not do, and must be able to
# tell that from the operation having succeeded.
REFUSED = object()


def _now():
    return datetime.utcnow().isoformat(timespec='seconds')


@dataclass
class Entry:
    """One movement in the ledger. `kind` is the meaning; the sign alone is not enough to
    recover it, which is the reason this field exists."""
    kind: str                       # 'payment' | 'reversal' | 'adjustment'
    amount: float
    on: str = None
    reason: str = None
    reverses: object = None         # the payment a reversal names
    recorded_at: str = None


@dataclass
class Plan:
    gross: float = 0.0
    instalment: float = 0.0
    count: int = 0
    first_due: str = None
    entries: list = field(default_factory=list)
    refusals: list = field(default_factory=list)


def new_plan(gross=0.0, instalment=0.0, count=0, first_due=None):
    return Plan(gross=float(gross), instalment=float(instalment), count=int(count),
                first_due=first_due)


# ── The three operations ────────────────────────────────────────────────────

def record_payment(plan, amount, on=None):
    e = Entry(kind='payment', amount=round(float(amount), 2), on=on, recorded_at=_now())
    plan.entries.append(e)
    return e


def reverse_payment(plan, payment, amount=None, on=None, reason=None):
    """Reverse a NAMED payment, wholly or partly.

    Refused when the amount exceeds what that payment was, because a reversal is of something
    that happened. A larger figure may still be legitimate — a rebilling, a clawback — but it
    is not this operation, and letting it through here would mean the ledger no longer records
    which payment stopped being true.
    """
    want = round(float(payment.amount if amount is None else amount), 2)
    already = sum(-e.amount for e in plan.entries
                  if e.kind == 'reversal' and e.reverses is payment)
    available = round(payment.amount - already, 2)
    if want > available:
        plan.refusals.append({'operation': 'reverse_payment', 'requested': want,
                              'available': available, 'on': on, 'at': _now()})
        return REFUSED
    e = Entry(kind='reversal', amount=-want, on=on, reverses=payment, reason=reason,
              recorded_at=_now())
    plan.entries.append(e)
    return e


def record_adjustment(plan, amount, reason=None, on=None):
    """The obligation changing. Not a payment, and deliberately not expressible as one:
    `paid` does not move, `remaining` does."""
    e = Entry(kind='adjustment', amount=round(float(amount), 2), on=on, reason=reason,
              recorded_at=_now())
    plan.entries.append(e)
    return e


# ── Reading the ledger ──────────────────────────────────────────────────────

def ledger(plan, as_of=None):
    """Payment-affecting entries. Adjustments are excluded because they are not payments —
    which is what lets `paid` be exactly the sum of this list."""
    rows = [e for e in plan.entries if e.kind in ('payment', 'reversal')]
    if as_of is not None:
        rows = [e for e in rows if not e.on or e.on <= as_of]
    return rows


def reversals(plan):
    return [e for e in plan.entries if e.kind == 'reversal']


def reversed_total(plan):
    return round(sum(-e.amount for e in reversals(plan)), 2)


def last_refusal(plan):
    return plan.refusals[-1] if plan.refusals else None


def _instalments_due(plan, as_of):
    """How many instalments the agreement says should have been paid by `as_of`.

    Counted in whole months from the first due date, capped at the agreement's length — an
    agreement cannot expect more than it contains.
    """
    if not plan.first_due or not as_of:
        return 0
    y0, m0 = int(plan.first_due[:4]), int(plan.first_due[5:7])
    y1, m1 = int(as_of[:4]), int(as_of[5:7])
    months = (y1 - y0) * 12 + (m1 - m0) + 1
    return max(0, min(plan.count, months))


# ── The projection ──────────────────────────────────────────────────────────

def payment_state(plan, as_of=None):
    """All five dimensions, computed together from the ledger in one pass.

    There is deliberately no `paid()` or `ahead()` accessor. Five numbers that must agree are
    one answer, and offering them separately is how a consumer ends up holding two versions of
    "ahead" that were computed at different moments from different subsets.

    **Attached-payment projections, not discharge.** `paid`, `remaining`, `ahead` and
    `overdue` are computed from payments the household attached to this obligation. None of
    them says the entitled party has credited anything: a payment sent to the wrong servicer,
    or to a party that no longer holds the obligation, is attached here and unacknowledged
    there, and this projection cannot tell the two apart. A consumer that presents
    `remaining` as what the household owes has read attachment as acknowledgment - the
    hazard the module header names. The key is kept as `remaining` for now; renaming it is
    a consumer-vocabulary decision deliberately not made here.
    """
    rows = ledger(plan, as_of)
    paid = round(sum(e.amount for e in rows), 2)
    adjustments = round(sum(e.amount for e in plan.entries
                            if e.kind == 'adjustment'
                            and (as_of is None or not e.on or e.on <= as_of)), 2)
    owed = round(plan.gross + adjustments, 2)
    due = _instalments_due(plan, as_of)
    expected = round(min(due * plan.instalment, owed), 2)
    distance = round(paid - expected, 2)
    return {
        'paid': paid,
        'remaining': round(owed - paid, 2),
        'expected_by_now': expected,
        # One distance, two names. Never a negative "ahead".
        'ahead': distance if distance > 0 else 0.00,
        'overdue': -distance if distance < 0 else 0.00,
        'adjustments': adjustments,
        'instalments_due': due,
    }


def incoherences(plan, as_of=None, state=None):
    """Check a projection against the ledger it claims to project.

    With no `state`, checks the one this module would produce — which is coherent by
    construction, and therefore cannot tell a working checker from one that always returns
    clean. That is why `state` exists: a consumer holding a figure from a cache, an API
    response or a migration can ask whether it still agrees with the ledger, and the checker
    becomes testable by being given something wrong to find.
    """
    st = payment_state(plan, as_of) if state is None else dict(state)
    rows = ledger(plan, as_of)
    out = []
    if st['paid'] != round(sum(e.amount for e in rows), 2):
        out.append('paid does not equal the ledger it is drawn from')
    if round(st['paid'] + st['remaining'], 2) != round(plan.gross + st['adjustments'], 2):
        out.append('paid and remaining do not account for what is owed')
    if st['ahead'] > 0 and st['overdue'] > 0:
        out.append('ahead and overdue are both non-zero, which is one distance twice')
    if st['ahead'] > 0 and st['ahead'] != round(st['paid'] - st['expected_by_now'], 2):
        out.append('ahead is not the distance between paid and expected')
    if st['overdue'] > 0 and st['overdue'] != round(st['expected_by_now'] - st['paid'], 2):
        out.append('overdue is not the distance between expected and paid')
    return out
