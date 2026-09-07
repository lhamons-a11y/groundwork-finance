# -*- coding: utf-8 -*-
"""The hostile reserve fixture — written BEFORE the model it tests.

`gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §5: the reserve is **three things, not one**.

    reserve target · reserve balance · contribution history

    a target's BASIS must be identified, because a user raising $6,000 -> $8,000 is a
    preference change and a corrected out-of-pocket maximum is a fact change, and they
    must not look alike. A new plan changing the target must be distinguishable from the
    user changing it. Deleting a target must not delete the money.

**The failure it prevents, stated in the review:** *"You have $4,000 healthcare reserve"* when
the truth is *"$4,000 of your general cash is counted toward a $6,000 target."* Those are
different claims, and the second is the true one for most households — the same class of error
the net-worth surface already refuses to make.

**The target is derived, not stored.** Design §1.4: the plan's out-of-pocket maximum is *by
definition* the most a covered year can cost, which is why it is the honest target and "three
to six months of expenses" is not. So a target whose basis is the OOP maximum keeps **no copy
of the figure** — it resolves it from the plan every time. A stored copy is two sources of
truth for one fact, which this project has already paid for once today.

**What this module has no opinion about.** Whether the reserve is built before, alongside or
after the last balance is design Open Question 6, explicitly unanswered. Nothing here decides
it, and nothing here should be read as deciding it.

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
    print('  general cash                 $%.2f  - counted toward a target, NOT held' % GENERAL_CASH)
    print('  a dedicated fund starts at   $0.00')
    print('\n  the claim that must never be makeable: "you have a $%.2f healthcare reserve"'
          % GENERAL_CASH)


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

    # ── The claim the review exists to prevent ──────────────────────────────
    # No dedicated fund yet. The household has $4,000 in ordinary savings.
    st = model.status(oop_max=PLAN_OOP_MAX, general_cash=GENERAL_CASH)
    check('nothing is held, because no money was ever set aside',
          st['held'] == 0.00)
    check('but general cash is counted toward the target',
          st['counted'] == 4000.00 and st['target'] == 6000.00)
    check('held and counted are different numbers, and the claim needs both',
          st['held'] != st['counted'])
    check('the shortfall is against the target, not against what is held',
          st['shortfall'] == 2000.00)
    check('and the status says plainly that nothing is segregated',
          st['segregated'] is False)

    # ── Contribution history, and a balance derived from it ─────────────────
    model.contribute(1500.00, on='2026-03-01', note='first deposit')
    model.contribute(500.00, on='2026-04-01')
    check('the balance is the sum of what was contributed',
          model.held() == 2000.00)
    model.withdraw(300.00, on='2026-05-01', note='dental')
    check('a withdrawal reduces it',
          model.held() == 1700.00)
    check('and stays in the history rather than being netted away',
          len(model.contributions()) == 3
          and model.contributions()[-1].amount == -300.00)
    check('now something IS segregated, and the claim changes',
          model.status(oop_max=PLAN_OOP_MAX,
                       general_cash=GENERAL_CASH)['segregated'] is True)

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
    held_before = model.held()
    model.clear_target()
    check('the target is gone',
          model.current_target() is None)
    check('the money is not',
          model.held() == held_before == 1700.00)
    check('and neither is the history of how it got there',
          len(model.contributions()) == 3)
    check('with no target, the shortfall is UNKNOWN rather than zero',
          model.status(oop_max=PLAN_OOP_MAX,
                       general_cash=GENERAL_CASH)['shortfall'] is model.UNKNOWN)


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
        print('  * held and counted are different numbers - money set aside versus general')
        print('    cash counted toward a target - and the honest claim names both')
        print('  * a preference change, a fact change and a plan change must not look alike')
        print('  * deleting a target does not delete the money or the history')
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
