# -*- coding: utf-8 -*-
"""What each answer to the payoff half of Open Question 6 would invalidate.

Measured, not argued, and reproducible — which is the only reason the figures in
`gw 2.0/RESERVE_PAYOFF_QUESTION.md` are quotable. Each candidate is applied as a perturbation
to the shipped engine and run against the recorded `green_light` contract (55 user-like states)
and the solution engine.

**This decides nothing.** It is an instrument for a decision that is Rob's, and the numbers it
produces are inputs to a risk judgement the engine cannot make: `simulate_payoff` measures
months, and the question is about exposure.

Nothing here is modified permanently — every perturbation is undone, and the contract baseline
is left as it was found.

Run:  python tests/payoff_option_measurement.py
"""
import io
import sys
import importlib.util
from pathlib import Path

ROOT = Path(r'C:\Groundwork')
sys.path.insert(0, str(ROOT))

from core import consequence as cons          # noqa: E402
from core import solution as sol              # noqa: E402

spec = importlib.util.spec_from_file_location('glc', ROOT / 'tests' / 'green_light_contract.py')
glc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glc)

TARGET = 6000.00          # a plan out-of-pocket maximum, the §1.4 derived target


def _with_reserve_draw(mode, target=TARGET):
    """Wrap simulate_payoff so the reserve competes for the extra above minimums.

    `before`    - the reserve takes the whole extra until the target is met
    `alongside` - the extra is split evenly between reserve and principal
    `after`     - unchanged; the reserve is funded from capacity that exists once the
                  balances are gone, which is not a change to this loop at all
    """
    orig = cons.simulate_payoff
    if mode == 'after':
        return orig, (lambda: None)

    def patched(cards, budget, strategy='avalanche', one_time_cost=0.0,
                today_key=None, start_month=None, one_time_extra=0.0):
        # Model the draw as a reduction of the budget available to debt, month by month,
        # until the target is met. Approximated here as a flat reduction, which is the
        # cheapest faithful stand-in for "some of the extra goes elsewhere".
        data = cons._prepare(cards)
        total_min = sum(c.minimum for c in data) if data else 0.0
        extra = max(0.0, float(budget) - total_min)
        if extra <= 0:
            return orig(cards, budget, strategy, one_time_cost, today_key, start_month,
                        one_time_extra)
        share = extra if mode == 'before' else extra / 2.0
        return orig(cards, float(budget) - share, strategy, one_time_cost, today_key,
                    start_month, one_time_extra)

    cons.simulate_payoff = patched
    sol.simulate_payoff = patched

    def undo():
        cons.simulate_payoff = orig
        sol.simulate_payoff = orig
    return orig, undo


def measure(mode):
    orig, undo = _with_reserve_draw(mode)
    try:
        checked, mismatches = glc.compare()
    finally:
        undo()
    return checked, mismatches


def main():
    print('What each answer would invalidate, measured against the shipped behaviour')
    print('=' * 74)
    baseline_checked, baseline_mismatch = glc.compare()
    print('baseline: %d recorded green_light states, %d changed\n'
          % (baseline_checked, len(baseline_mismatch)))
    if baseline_mismatch:
        print('baseline is not clean - stop')
        return 1

    for mode in ('after', 'alongside', 'before'):
        checked, mismatches = measure(mode)
        pct = (100.0 * len(mismatches) / checked) if checked else 0.0
        print('  %-10s %3d of %d recorded states change  (%.0f%%)'
              % (mode, len(mismatches), checked, pct))
        for msg in mismatches[:2]:
            print('             e.g. %s' % msg[:96])
    print()

    # The solution engine draws its levers from the same pool.
    from core.consequence import Card
    cards = [Card(balance=8000, rate=22, minimum=200, name='Visa'),
             Card(balance=3000, rate=6, minimum=75, name='Store')]
    print('extra above minimums on a $775 budget: $%.2f'
          % sol.extra_above_minimums(cards, 775))
    base = sol.solve_one_time_cost(cards, 775, 2400)
    print('a $2,400 one-time cost today: gap %d months, %d honest paths'
          % (base['gap_months'], len(base['paths'])))
    for mode in ('alongside', 'before'):
        orig, undo = _with_reserve_draw(mode)
        try:
            r = sol.solve_one_time_cost(cards, 775, 2400)
            print('  under %-10s gap %d months, %d paths'
                  % (mode, r['gap_months'], len(r['paths'])))
        finally:
            undo()
    return 0


if __name__ == '__main__':
    sys.exit(main())
