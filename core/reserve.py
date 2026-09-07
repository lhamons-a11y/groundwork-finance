# -*- coding: utf-8 -*-
"""The healthcare reserve — an allocation of a balance, not a movement of one.

Implements `gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §5 and design Open Question 6, and is
specified by `tests/test_reserve_fixture.py`.

**The frozen rule (Rob, 2026-09-07):**

> A reserve is an allocation of an existing financial state, recorded alongside the applicable
> balance. It does not modify the historical account balance and is not itself a transaction.

So the shape is:

    $2,000 ending balance
    ├── $500 reserved
    └── $1,500 available

and never:

    $2,000 balance → reserve $500 → $1,500 balance

The second makes the reserve look like a balance movement, and it is not one. **If the account
held $2,000, the historian goes on reporting $2,000** however much of it was allocated —
which is what keeps reconciliation and historical reporting honest. `available` is derived on
demand and stored nowhere.

**A consequence worth stating, because it is what the first version of this module got wrong.**
An allocation is a **level, not an accumulation**. Reserving $500 and later $700 means $700 is
reserved, not $1,200. A contribution ledger sums; an allocation supersedes. This module has no
`contribute`, no `withdraw` and no balance-moving operation of any kind, and that absence is
the rule made mechanical.

**The three things §5 asks for** survive the change intact: the *target* (how much should be
reserved), the *allocation* (how much is), and the *history* of how the allocation moved.

**The target is derived, not stored.** Design §1.4: the plan's out-of-pocket maximum is *by
definition* the most a covered year can cost, which is what makes it an honest target where
"three to six months of expenses" is a number somebody invented. A target whose basis is that
maximum keeps **no copy of the figure** and resolves it on every read — one owner per fact.

**What this module still has no opinion about.** Whether freed money fills the reserve before,
alongside or after the last debt balance is cleared is the *payoff-allocation* half of Open
Question 6 — the half that would change `core/consequence.py` and affect every user. It remains
open, and nothing here decides it.
"""

from dataclasses import dataclass, field
from datetime import datetime

# Not zero. A target nobody can resolve, and a target that does not exist, are both unknown
# quantities — and a shortfall computed against a zero target would read as "fully funded".
UNKNOWN = object()

# What a target's number is. The basis is what makes a change interpretable: without it,
# $6,000 becoming $8,000 is just a bigger number.
BASES = ('oop_max', 'custom', 'historical')

# How a target came to change. `unspecified` is deliberate: when a derived target is replaced
# and the caller does not say why, that is genuinely unknown, and inventing `fact` or
# `plan_change` would be manufacturing a classification from an unresolved state.
KINDS = ('initial', 'preference', 'fact', 'plan_change', 'unspecified')


def _now():
    return datetime.utcnow().isoformat(timespec='seconds')


@dataclass
class Target:
    """A target as of a point in the record. Superseded, never overwritten.

    `amount` is None for any derived basis — that absence is the design, not an omission.
    """
    basis: str
    amount: float = None
    kind: str = 'initial'
    source: str = None
    reason: str = None
    seq: int = 0
    recorded_at: str = None


@dataclass
class Allocation:
    """How much of the balance is designated reserved, as of a date.

    A level rather than a movement: each allocation supersedes the one before it. `as_of` is
    the date the allocation applies from, which is how a historical balance can be read back
    with the allocation that was in force at the time rather than today's.
    """
    amount: float
    as_of: str = None
    reason: str = None
    source: str = None
    seq: int = 0
    recorded_at: str = None


@dataclass
class Registry:
    targets: list = field(default_factory=list)
    allocations: list = field(default_factory=list)
    cleared: bool = False
    _seq: int = 0


_REGISTRY = Registry()


def reset():
    global _REGISTRY
    _REGISTRY = Registry()
    return _REGISTRY


def _r():
    return _REGISTRY


# ── The target ──────────────────────────────────────────────────────────────

def set_target(basis=None, amount=None, source=None, reason=None, kind=None):
    """Record a target. `amount` is stored only where nothing derives it.

    A derived basis that arrives with an amount is a copy waiting to drift, so the amount is
    dropped rather than kept.
    """
    r = _r()
    r._seq += 1
    if kind is None:
        if not r.targets:
            kind = 'initial'
        elif basis == 'custom':
            # The user picked a number. Nothing derived it, so wanting it is the whole reason.
            kind = 'preference'
        else:
            kind = 'unspecified'
    stored = float(amount) if (basis == 'custom' and amount is not None) else None
    t = Target(basis=basis, amount=stored, kind=kind, source=source, reason=reason,
               seq=r._seq, recorded_at=_now())
    r.targets.append(t)
    r.cleared = False
    return t


def target_history():
    return list(_r().targets)


def current_target():
    r = _r()
    if r.cleared or not r.targets:
        return None
    return r.targets[-1]


def clear_target():
    """Removes the target. Deliberately does not touch the allocation or its history — a
    target says how much is wanted, and withdrawing it says nothing about what is reserved."""
    _r().cleared = True
    return None


def target_amount(oop_max=None, historical=None):
    """Resolve the current target's figure from whoever holds it.

    The caller supplies the plan's maximum rather than this module reading it, which is the
    same division of labour `core/solution.py` uses when it takes `months_observed` on trust:
    one owner per fact.
    """
    t = current_target()
    if t is None:
        return UNKNOWN
    if t.basis == 'custom':
        return t.amount if t.amount is not None else UNKNOWN
    if t.basis == 'oop_max':
        return float(oop_max) if oop_max is not None else UNKNOWN
    if t.basis == 'historical':
        return float(historical) if historical is not None else UNKNOWN
    return UNKNOWN


# ── The allocation, which moves no money ────────────────────────────────────

def allocate(amount, as_of=None, reason=None, source=None):
    """Designate part of the balance as reserved, from `as_of` onward.

    Records what is reserved. It does not move money, does not touch an account, and is not a
    transaction — there is deliberately no operation here that could be mistaken for one.
    """
    r = _r()
    r._seq += 1
    a = Allocation(amount=round(float(amount), 2), as_of=as_of, reason=reason, source=source,
                   seq=r._seq, recorded_at=_now())
    r.allocations.append(a)
    return a


def allocations():
    """Every allocation, oldest first. Superseded, never overwritten — so a balance from
    March can be read back against the allocation that was in force in March."""
    return list(_r().allocations)


def reserved(as_of=None):
    """The allocation in force, now or as of a date. Zero when none was ever made, which is a
    real answer rather than an absent one: nothing reserved is a state, not a gap."""
    rows = _r().allocations
    if as_of is not None:
        rows = [a for a in rows if not a.as_of or a.as_of <= as_of]
    return rows[-1].amount if rows else 0.00


def available(balance, as_of=None):
    """What is left after the allocation. Derived here and stored nowhere.

    Returns UNKNOWN when the balance is not supplied, because a balance nobody gave us is not
    a balance of zero — and an `available` of zero would read as "spend nothing", which is a
    claim about someone's money made from no information.
    """
    if balance is None:
        return UNKNOWN
    return round(float(balance) - reserved(as_of=as_of), 2)


def snapshot(balance=None, as_of=None, oop_max=None, historical=None):
    """The balance, the allocation against it, and what that leaves — reported together.

    `balance` comes back exactly as it was given. That is the rule made checkable: the reserve
    is metadata alongside a balance, so nothing here can return a modified one.
    """
    have = reserved(as_of=as_of)
    target = target_amount(oop_max=oop_max, historical=historical)
    left = available(balance, as_of=as_of)
    return {
        'date': as_of,
        'balance': balance,
        'reserved': have,
        'available': left,
        # An allocation larger than the balance is reported, never clamped. Clamping would
        # hide the one state a user most needs to see — that they have earmarked money they
        # do not have.
        'over_allocated': (left is not UNKNOWN and left < 0),
        'basis': (current_target().basis if current_target() else None),
        'target': target,
        # Measured against what is RESERVED, not against the balance. A household with $2,000
        # in the account and nothing reserved is not a third of the way to a $6,000 target;
        # that is §5's failure sentence in arithmetic form.
        'shortfall': (UNKNOWN if target is UNKNOWN
                      else round(max(0.0, target - have), 2)),
    }
