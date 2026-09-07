# -*- coding: utf-8 -*-
"""The hostile reserve fixture — written BEFORE the model it tests.

`gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §5: the reserve is **three things, not one**.

    reserve target · reserve balance · contribution history

    a target's BASIS must be identified, because a user raising $6,000 -> $8,000 is a
    preference change and a corrected out-of-pocket maximum is a fact change, and they
    must not look alike. A new plan changing the target must be distinguishable from the
    user changing it. Deleting a target must not delete the money.

**The frozen rule (Rob, 2026-09-07), which the balance half of this fixture tests:**

    A reserve is an allocation of an existing financial state, recorded alongside the
    applicable balance. It does not modify the historical account balance and is not
    itself a transaction.

    $2,000 ending balance          and never    $2,000 balance
    |-- $500 reserved                            -> reserve $500
    `-- $1,500 available                         -> $1,500 balance

If the account held $2,000 the historian goes on reporting $2,000, however much was allocated.
An allocation is therefore a **level, not an accumulation** - $500 then $700 means $700 is
reserved, not $1,200 - and there is no operation here that moves money at all.

**The failure §5 names:** *"You have $4,000 healthcare reserve"* when the truth is *"$4,000 of
your general cash is counted toward a $6,000 target."* In this vocabulary that is a shortfall
measured against the **balance** instead of against what is **reserved**, and it is asserted
below.

**The target is derived, not stored.** Design §1.4: the plan's out-of-pocket maximum is *by
definition* the most a covered year can cost, which is why it is the honest target and "three
to six months of expenses" is not. So a target whose basis is the OOP maximum keeps **no copy
of the figure** — it resolves it from the plan every time. A stored copy is two sources of
truth for one fact, which this project has already paid for once today.

**What this module still has no opinion about.** Open Question 6 had two halves. The data
half is answered above and frozen. The other - whether freed money fills the reserve before,
alongside or after the last DEBT balance is cleared - would change `core/consequence.py` and
affect every user, and it remains open. Nothing here decides it.

Run:  python tests/test_reserve_fixture.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS, FAIL, PENDING = [], [], []


def check(name, condition):
    if condition is None:
        PENDING.append(name)
        print(f'  ....  {name}')
    elif condition:
        PASS.append(name)
        print(f'  OK    {name}')
    else:
        FAIL.append(name)
        print(f'  FAIL  {name}')


# ── The fixture ─────────────────────────────────────────────────────────────
PLAN_OOP_MAX = 6000.00          # what the plan document says today
CORRECTED_OOP_MAX = 5500.00     # what it turns out to have said all along
GENERAL_CASH = 4000.00          # the household's ordinary savings - not a healthcare pot


def describe():
    print('\nThe fixture, as a specification:\n')
    print('  plan out-of-pocket maximum   $%.2f  (later corrected to $%.2f)'
          % (PLAN_OOP_MAX, CORRECTED_OOP_MAX))
    print('  account balance              $%.2f  - reported unchanged, whatever is allocated'
          % GENERAL_CASH)
    print('\n  $2,000 ending balance  ->  $500 reserved  +  $1,500 available')
    print('  and never: $2,000 -> reserve $500 -> $1,500 balance')


# ── The assertions the model has to satisfy ─────────────────────────────────

def run(model):
    model.reset()

    # ── Three things, and the target is derived ─────────────────────────────
    model.set_target(basis='oop_max', source='plan_document')
    check('a target has a basis, so what kind of number it is can be asked',
          model.current_target().basis == 'oop_max')
    check('and a derived target stores no copy of the figure',
          model.current_target().amount is None)
    check('it resolves from the plan when asked',
          model.target_amount(oop_max=PLAN_OOP_MAX) == 6000.00)

    # The point of not storing it. Correcting the plan moves the target with no edit here,
    # because there was never a second copy to reconcile.
    check('correcting the plan moves the target, with nothing to reconcile',
          model.target_amount(oop_max=CORRECTED_OOP_MAX) == 5500.00)
    check('and no correction was recorded against the reserve, because none happened',
          len(model.target_history()) == 1)

    # A basis that needs a figure nobody supplied does not fall back to zero.
    check('a target nobody can resolve is UNKNOWN, not zero',
          model.target_amount() is model.UNKNOWN)

    # ── Nothing reserved is a state, not a gap ──────────────────────────────
    # The household has $4,000 in the account and has designated none of it.
    st = model.snapshot(balance=GENERAL_CASH, oop_max=PLAN_OOP_MAX)
    check('with no allocation, nothing is reserved',
          st['reserved'] == 0.00)
    check('and all of the balance is available',
          st['available'] == 4000.00 and st['balance'] == 4000.00)
    check('the shortfall is the whole target, because nothing has been set aside',
          st['shortfall'] == 6000.00 and st['target'] == 6000.00)

    # ── The allocation, which moves no money ────────────────────────────────
    model.allocate(500.00, as_of='2026-09-07', reason='first designation', source='user')
    snap = model.snapshot(balance=2000.00, as_of='2026-09-07', oop_max=PLAN_OOP_MAX)
    check('the balance is reported exactly as it was given',
          snap['balance'] == 2000.00)
    check('with part of it identified as reserved',
          snap['reserved'] == 500.00)
    check('and the rest available, derived rather than stored',
          snap['available'] == 1500.00)
    check('the reserve is not a transaction, so nothing here can move money',
          not hasattr(model, 'contribute') and not hasattr(model, 'withdraw'))

    # A level, not an accumulation. This is what the first version of the model got wrong:
    # a contribution ledger sums, an allocation supersedes.
    model.allocate(700.00, as_of='2026-10-01', source='user')
    check('a later allocation supersedes rather than adding to the last',
          model.reserved() == 700.00)
    check('and both survive, so a September balance reads against September allocation',
          len(model.allocations()) == 2
          and model.reserved(as_of='2026-09-07') == 500.00)
    check('the historical balance is untouched by any of it',
          model.snapshot(balance=2000.00)['balance'] == 2000.00
          and model.snapshot(balance=2000.00)['available'] == 1300.00)

    # Section 5 failure sentence, in arithmetic. Measured against the balance this reads
    # 4000; measured against what is actually reserved it reads 5300, which is the true one.
    check('the shortfall is measured against what is reserved, not against the balance',
          model.snapshot(balance=2000.00, oop_max=PLAN_OOP_MAX)['shortfall'] == 5300.00)

    # Earmarking money you do not have is the one state a user most needs to see.
    tight = model.snapshot(balance=400.00)
    check('an allocation larger than the balance is reported, never clamped',
          tight['available'] == -300.00 and tight['over_allocated'] is True)
    check('and a balance nobody supplied is UNKNOWN, not zero',
          model.snapshot()['available'] is model.UNKNOWN)

    # ── The three ways a target changes, which must not look alike ──────────
    model.set_target(basis='custom', amount=8000.00, reason='wants more headroom',
                     source='user')
    check('the user raising the target is a preference change',
          model.target_history()[-1].kind == 'preference')
    check('and a preference target does store its amount, because nothing derives it',
          model.target_amount() == 8000.00)

    model.set_target(basis='oop_max', source='plan_document_corrected',
                     reason='benefits summary shows $5,500', kind='fact')
    check('a corrected out-of-pocket maximum is a fact change',
          model.target_history()[-1].kind == 'fact')

    model.set_target(basis='oop_max', source='new_plan', kind='plan_change')
    check('and a new plan changing the target is neither of those',
          model.target_history()[-1].kind == 'plan_change')
    check('all three are distinguishable, which is the whole point',
          len({t.kind for t in model.target_history()}) == 4)
    check('and every target change carries where it came from',
          all(t.source for t in model.target_history()))

    # ── Deleting a target must not delete the money ─────────────────────────
    reserved_before = model.reserved()
    model.clear_target()
    check('the target is gone',
          model.current_target() is None)
    check('the allocation is not',
          model.reserved() == reserved_before == 700.00)
    check('and neither is the history of how it moved',
          len(model.allocations()) == 2)
    check('with no target, the shortfall is UNKNOWN rather than zero',
          model.snapshot(balance=2000.00,
                         oop_max=PLAN_OOP_MAX)['shortfall'] is model.UNKNOWN)
    check('and the balance still reports as itself',
          model.snapshot(balance=2000.00)['balance'] == 2000.00)


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    try:
        from core import reserve as model          # noqa: F401
    except ImportError:
        print('\nNo model yet — core/reserve.py does not exist.')
        print('This file is the specification it has to satisfy.')
        describe()
        print('\nAlso required, and not expressible as a table:')
        print('  * target, balance and contribution history are three things; the balance')
        print('    is DERIVED from the history, never stored')
        print('  * a target derived from the plan keeps NO copy of the figure, so')
        print('    correcting the plan moves it with nothing to reconcile')
        print('  * a reserve is an ALLOCATION of a balance, never a movement of one: the')
        print('    balance comes back exactly as given, available is derived, and no')
        print('    operation here could be mistaken for a transaction')
        print('  * an allocation is a LEVEL, not an accumulation - $500 then $700 is $700')
        print('  * the shortfall is measured against what is reserved, never the balance')
        print('  * a preference change, a fact change and a plan change must not look alike')
        print('  * deleting a target does not delete the allocation or its history')
        print('  * an unresolvable target and a missing target are UNKNOWN, never zero')
        print('\n  and one thing this module must NOT do: decide whether the reserve is')
        print('  built before, alongside or after the last balance. That is design Open')
        print('  Question 6, and it is open.')
        print('\n0 passed, 0 failed — every assertion above is pending a model')
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    return 1 if (FAIL or PENDING) else 0


if __name__ == '__main__':
    sys.exit(main())
