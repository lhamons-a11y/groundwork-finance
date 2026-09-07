# -*- coding: utf-8 -*-
"""The healthcare reserve — three things, and the claim that must not be made.

Implements `gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §5, and is specified by
`tests/test_reserve_fixture.py`, written before this file existed.

    reserve target · reserve balance · contribution history

**The failure this exists to prevent**, in the review's own words: *"You have $4,000 healthcare
reserve"* when the truth is *"$4,000 of your general cash is counted toward a $6,000 target."*
Those are different claims, and the second is the true one for most households. So `held` and
`counted` are separate figures here and no single number stands in for the pair — the same
refusal the net-worth surface already makes.

**The target is derived, not stored.** Design §1.4: the plan's out-of-pocket maximum is *by
definition* the most a covered year can cost, which is what makes it an honest target where
"three to six months of expenses" is a number somebody invented. A target whose basis is that
maximum therefore keeps **no copy of the figure** — it resolves from the plan every time.
Storing a copy would be two sources of truth for one fact, which this project paid for once
already when `allocation` and `plan_year` each derived an expense's plan.

**Three ways a target changes, and they must not look alike:**

    preference    the user wants more headroom - $6,000 to $8,000
    fact          the out-of-pocket maximum was always $5,500; we had it wrong
    plan_change   a different plan, so a different maximum

Same new number, three different meanings, and a consumer that cannot tell them apart will
eventually tell someone their plan changed when they simply changed their mind.

**What this module has no opinion about.** Whether the reserve is built before, alongside or
after the last balance is design Open Question 6, and it is open. Nothing here decides it.
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
class Contribution:
    """Money in or out of the dedicated fund. Negative for a withdrawal, which stays in the
    history rather than being netted away — the balance is derived, so nothing is lost by
    keeping both sides."""
    amount: float
    on: str = None
    note: str = None
    seq: int = 0
    recorded_at: str = None


@dataclass
class Registry:
    targets: list = field(default_factory=list)
    contributions: list = field(default_factory=list)
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
    """Removes the target. Deliberately does not touch the money or the history — a target is
    a statement about how much is wanted, and deleting it says nothing about what is there."""
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


# ── The balance, derived from the history ───────────────────────────────────

def contribute(amount, on=None, note=None):
    r = _r()
    r._seq += 1
    c = Contribution(amount=round(float(amount), 2), on=on, note=note, seq=r._seq,
                     recorded_at=_now())
    r.contributions.append(c)
    return c


def withdraw(amount, on=None, note=None):
    return contribute(-round(float(amount), 2), on=on, note=note)


def contributions():
    return list(_r().contributions)


def held():
    """What is actually set aside. Derived on every read, so nothing has to remember to
    recompute it when a contribution is corrected."""
    return round(sum(c.amount for c in _r().contributions), 2)


# ── The claim ───────────────────────────────────────────────────────────────

def status(oop_max=None, general_cash=0.0, historical=None):
    """The honest statement, which needs more than one number to make.

    `held` is money set aside for this. `counted` is ordinary cash that happens to be large
    enough to count toward the target. Reporting only the second as though it were the first
    is the failure §5 names, and there is deliberately no field here that means "the reserve
    balance" without saying which kind it is.
    """
    target = target_amount(oop_max=oop_max, historical=historical)
    have = held()
    counted = round(float(general_cash or 0.0), 2)
    t = current_target()
    return {
        'basis': t.basis if t else None,
        'target': target,
        'held': have,
        'counted': counted,
        # True only when money was actually set aside. A household with $4,000 of general
        # savings and no dedicated fund is not holding a healthcare reserve, however close
        # the arithmetic looks.
        'segregated': have > 0,
        'shortfall': (UNKNOWN if target is UNKNOWN
                      else round(max(0.0, target - have - counted), 2)),
    }
