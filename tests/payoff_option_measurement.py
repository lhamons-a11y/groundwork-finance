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
import contextlib
import io as _io
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
    `lever`     - the payoff computation is untouched and the reserve becomes one more path
                  the user may choose, priced in months like every other path
    """
    orig = cons.simulate_payoff
    if mode == 'after':
        return orig, (lambda: None)
    if mode == 'lever':
        return _as_lever(orig)

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


def _as_lever(orig_sim):
    """The reserve as a path in the solution engine rather than a property of the engine.

    Nothing about `simulate_payoff` moves. What changes is that `solve_one_time_cost` returns
    one more path - holding money back toward the reserve, priced in months exactly the way
    every other path is priced. Whether that counts as "a calculation changed" is precisely
    what the diff below has to be able to answer, which is why it reports WHICH keys moved.
    """
    orig_solver = sol.solve_one_time_cost

    def patched(cards, budget, one_time_cost, **kw):
        out = orig_solver(cards, budget, one_time_cost, **kw)
        if not out.get('paths'):
            return out
        sim_kw = {k: v for k, v in kw.items()
                  if k in ('strategy', 'today_key', 'start_month')}
        base = orig_sim(cards, budget, **sim_kw)
        monthly = cons.extra_above_minimums(cards, budget) or 0.0
        hold = round(monthly / 2.0, 2)
        held = orig_sim(cards, max(0.0, budget - hold), **sim_kw)
        cost = (held['months'] - base['months']
                if base and held else None)
        out = dict(out)
        out['paths'] = list(out['paths']) + [sol._path(
            'reserve', 'hold %.0f a month toward the reserve' % hold,
            'the card stays clear if a bad month lands', closes=False,
            cost_months=cost, requires_cut=False)]
        return out

    sol.solve_one_time_cost = patched

    def undo():
        sol.solve_one_time_cost = orig_solver
    return orig_sim, undo


def coverage():
    """What the 55-state corpus actually varies, and what it does not.

    Reported so "0 of 55" cannot be read as "never changes anything". It means *none of 55
    states that were recorded for a different purpose* - the corpus exists to protect
    `green_light`, and it predates the reserve entirely.
    """
    cases = glc.cases()
    ncards, rates, surplus, drivers = [], [], [], []
    tied = 0
    flags = set()
    strategies = set()
    for _name, inp in cases:
        cards = inp['cards']
        ncards.append(len(cards))
        rs = [c['rate'] for c in cards]
        rates += rs
        if len(rs) != len(set(rs)):
            tied += 1
        total_min = sum(c['minimum'] for c in cards)
        surplus.append(inp['budget'] - total_min)
        drivers.append(len(inp['drivers']))
        strategies.add(inp.get('strategy', 'avalanche'))
        for c in cards:
            for k in ('is_lease', 'is_pslf', 'forgive_after_months'):
                if c.get(k):
                    flags.add(k)
            if c['balance'] == 0:
                flags.add('zero_balance')

    present = [
        ('cases', '%d' % len(cases)),
        ('cards per case', '%d-%d' % (min(ncards), max(ncards))),
        ('interest rates', '%.2f%%-%.2f%%' % (min(rates), max(rates))),
        ('surplus over minimums', '$%.2f to $%.2f' % (min(surplus), max(surplus))),
        ('cases with no surplus', '%d' % sum(1 for x in surplus if x <= 0)),
        ('drivers per case', '%d-%d' % (min(drivers), max(drivers))),
        ('strategies', ', '.join(sorted(strategies))),
        ('special cards', ', '.join(sorted(flags)) or 'none'),
    ]
    absent = [
        ('a reserve, in any state', 'the corpus predates it entirely - 0 of 55 cases'),
        ('zero / partial / full reserve', 'no reserve dimension exists to vary'),
        ('reserve reached or depleted mid-run', 'same'),
        ('one-time costs', '0 of 55 - green_light does not take one'),
        ('tied interest rates', '%d of 55 - so ordering TIES are untested' % tied),
        ('a balance clearing mid-month', 'not varied deliberately'),
    ]
    return present, absent


def _diff(before, after):
    """What moved, in enough detail to become a requirement.

    `altered` - an existing value is different
    `extended` - a list grew and everything that was there is still there, unchanged

    The distinction is the whole point of the fourth position: a path added beside the others
    is not the same event as every existing figure moving, and a diff that reported both as
    "changed" could not tell Rob which one happened.
    """
    if isinstance(before, dict) and isinstance(after, dict):
        altered, extended = [], []
        for key in sorted(set(before) | set(after)):
            b, a = before.get(key), after.get(key)
            if b == a:
                continue
            if (isinstance(b, list) and isinstance(a, list)
                    and len(a) > len(b) and a[:len(b)] == b):
                extended.append(key)
            else:
                altered.append(key)
        return altered, extended
    return ([] if before == after else ['value']), []


def measure(mode):
    orig, undo = _with_reserve_draw(mode)
    try:
        checked, mismatches = glc.compare()
    finally:
        undo()
    return checked, mismatches


# Every calculation that reaches the payoff engine, with a representative portfolio for each.
# Named individually rather than exercised through a smoke section, because the requirement is
# to identify the CALCULATIONS whose ordering or baseline change, and a section reports checks.
#
# `_prepare`, `_month_key`, `is_protected`, `_headroom`, `_trims`, `_overspend`, `fund_pace`
# and `decision_memory` are deliberately absent: none of them reaches the engine, so none can
# move. That absence is part of the inventory rather than an omission from it.
_CARDS = [dict(balance=8000, rate=22, minimum=200, name='Visa'),
          dict(balance=3000, rate=6, minimum=75, name='Store')]
_CATEGORIES = [{'name': 'Dining Out', 'budgeted': 400.0, 'max_observed': 310.0,
                'months_observed': 6, 'spent': 460.0}]
_RECURRING = [{'name': 'Streaming', 'monthly': 43.0, 'category': 'Entertainment'}]


def _cards():
    from core.consequence import Card
    return [Card(**c) for c in _CARDS]


def _calculations():
    """(module, name, callable) for everything that consumes the engine."""
    from core import consequence as c
    from core import solution as so
    return [
        ('consequence', 'simulate_payoff', lambda: c.simulate_payoff(_cards(), 775)),
        ('consequence', 'extra_above_minimums',
         lambda: c.extra_above_minimums(_cards(), 775)),
        ('consequence', 'decision_impact',
         lambda: c.decision_impact(_cards(), 775, monthly_delta=-50.0)),
        ('consequence', 'affordable_one_time',
         lambda: c.affordable_one_time(_cards(), 775, 2400)),
        ('consequence', 'affordable_monthly',
         lambda: c.affordable_monthly(_cards(), 775, 120)),
        ('consequence', 'offsetting_monthly_delta',
         lambda: c.offsetting_monthly_delta(_cards(), 775, 2400)),
        ('solution', 'solve_one_time_cost',
         lambda: so.solve_one_time_cost(_cards(), 775, 2400, categories=_CATEGORIES,
                                        recurring=_RECURRING)),
        ('solution', 'save_first_plan', lambda: so.save_first_plan(_cards(), 775, 2400)),
        ('solution', 'do_nothing_note',
         lambda: so.do_nothing_note(_cards(), 775, one_time_cost=2400)),
        ('solution', 'solve_monthly_cost',
         lambda: so.solve_monthly_cost(_cards(), 775, 120, categories=_CATEGORIES,
                                       recurring=_RECURRING)),
        ('solution', 'accelerations',
         lambda: so.accelerations(_cards(), 775, categories=_CATEGORIES,
                                  recurring=_RECURRING)),
        ('solution', 'budget_pressure',
         lambda: so.budget_pressure(_cards(), 775, categories=_CATEGORIES)),
        ('solution', 'past_charge_lesson',
         lambda: so.past_charge_lesson(_cards(), 775, 900)),
        ('solution', 'capacity_unlocked',
         lambda: so.capacity_unlocked(_cards(), 775, 3500, 2600)),
        ('solution', 'green_light',
         lambda: so.green_light(_cards(), 775, [{'monthly': 180.0, 'deliberate': True,
                                                 'label': 'cancelled storage',
                                                 'months_ago': 1}])),
    ]


def audit(mode):
    """Identify every calculation whose ordering or baseline changes under `mode`.

    This is the instrument the requirement asks for: once a position is chosen, run it and the
    list of what has to be re-examined is the output rather than a fresh reading of the engine.
    """
    baseline = {}
    for module, name, fn in _calculations():
        try:
            baseline[(module, name)] = fn()
        except Exception as e:                                # noqa: BLE001
            baseline[(module, name)] = 'RAISED %s' % type(e).__name__

    orig, undo = _with_reserve_draw(mode)
    try:
        altered, extended, same = [], [], []
        for module, name, fn in _calculations():
            label = '%s.%s' % (module, name)
            try:
                now = fn()
            except Exception as e:                            # noqa: BLE001
                now = 'RAISED %s' % type(e).__name__
            was = baseline[(module, name)]
            a_keys, e_keys = _diff(was, now)
            if a_keys:
                altered.append((label, a_keys))
            elif e_keys:
                extended.append((label, e_keys))
            else:
                same.append(label)
    finally:
        undo()
    return altered, extended, same


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
    # ── The audit the requirement asks for ──────────────────────────────────
    print()
    print('Corpus coverage - what "0 of 55" is and is not evidence of:')
    present, absent = coverage()
    for label, value in present:
        print('    varies    %-30s %s' % (label, value))
    for label, why in absent:
        print('    ABSENT    %-30s %s' % (label, why))
    print()
    print('  So a position measured at 0 of 55 changed NONE OF THESE STATES. The corpus was')
    print('  recorded to protect green_light against unintended change; it was not designed')
    print('  to discriminate between reserve positions, and it contains no reserve at all.')

    print()
    print('Calculations whose ordering or baseline changes, by position:')
    total = len(_calculations())
    for mode in ('after', 'lever', 'alongside', 'before'):
        altered, extended, _same = audit(mode)
        print()
        print('  %-10s %d altered, %d extended, of %d engine-consuming calculations'
              % (mode, len(altered), len(extended), total))
        for name, keys in altered:
            print('             ALTERED  %-34s %s' % (name, ','.join(keys)))
        for name, keys in extended:
            print('             EXTENDED %-34s %s' % (name, ','.join(keys)))
    print()
    print('  Two caveats, so 12 of 15 is not read as authoritative:')
    print('   1. `extra_above_minimums` shows as unchanged only because this perturbation')
    print('      models the draw INSIDE simulate_payoff. A real implementation redefines the')
    print('      pool itself, so it moves too - and being the pool definition, it moves first.')
    print('   2. `budget_pressure` and `capacity_unlocked` are unchanged FOR THIS PORTFOLIO,')
    print('      which is not the same as unable to change. Both consume the engine.')
    print('   3. the lever footprint is a FLOOR, not a ceiling: it is measured with the path')
    print('      offered by solve_one_time_cost alone. Every further surface that offers it')
    print('      adds one more EXTENDED calculation - and none of them become ALTERED.')
    print()
    print('  Not in the inventory, because none of them reaches the engine and so none can')
    print('  move: _prepare, _month_key, is_protected, _headroom, _trims, _overspend,')
    print('  fund_pace, decision_memory.')
    print()
    print('  Outside this process entirely, and changed by any position but `after`:')
    print('    _simulatePayoffStrategy in static/js/app.js  (the second implementation)')
    print('    tests/test_consequence_parity.py             (holds the two to the month)')
    print('    tests/green_light_contract.json              (re-record, versioned)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
