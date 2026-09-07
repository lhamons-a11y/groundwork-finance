# -*- coding: utf-8 -*-
"""The hostile plan-year fixture — written BEFORE the model it tests.

`gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §4, made mechanical:

    current_plan_year = 2026 cannot explain history
    EDIT and CORRECTION are different operations, and the system must know which happened
    late-arriving plan data is first class - a January expense re-evaluable against March data
    the critical case: Plan A Jan-Jun, Plan B Jul-Dec; mutating plan_id destroys half the year
    rollover is not year += 1 - accumulators reset according to the APPLICABLE plan
    a historical plan record is effectively immutable

**The hardest assertion here is the one about not knowing.** An expense incurred under a plan
whose terms have not arrived has a known *amount* and an unknown *status*: how much was spent
is a fact, whether it met a deductible is an interpretation, and nothing may turn the second
into `False` because the first is available. That is principle 1 and principle 3 arriving
together, in the place where a wrong answer tells someone their care is covered.

**Accumulators are derived, never stored.** Which is also why rollover is not an operation:
if the 2027 figure is a query over expenses in 2027, nothing has to reset, and nothing can
forget to.

Nothing here imports a model, because none exists — running this prints the specification it
is asserting and exits non-zero.

Run:  python tests/test_plan_year_fixture.py
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
# The critical case from §4, with a fourth expense in a year whose plan nobody has
# entered yet — because that is the normal state of January.

EXPENSES = {
    'x1': {'date': '2026-02-10', 'amount': 1200.00},
    'x2': {'date': '2026-05-05', 'amount':  900.00},   # Plan A period: 2100 applied
    'x3': {'date': '2026-08-01', 'amount': 1600.00},   # Plan B period: 1600 applied
    'x4': {'date': '2027-01-15', 'amount':  500.00},   # no plan on file yet
}

PLAN_A = dict(name='Plan A', deductible=3000.00, oop_max=6000.00,
              effective_from='2026-01-01', effective_to='2026-06-30')
PLAN_B = dict(name='Plan B', deductible=1500.00, oop_max=4000.00,
              effective_from='2026-07-01', effective_to='2026-12-31')
PLAN_C = dict(name='Plan C', deductible=1000.00, oop_max=3000.00,
              effective_from='2027-01-01', effective_to='2027-12-31')


def describe():
    print('\nThe fixture, as a specification:\n')
    for label, p in (('Plan A', PLAN_A), ('Plan B', PLAN_B), ('Plan C (arrives late)', PLAN_C)):
        print('  %-22s deductible $%7.2f  oop max $%7.2f  %s .. %s'
              % (label, p['deductible'], p['oop_max'], p['effective_from'],
                 p['effective_to']))
    print()
    for k, e in EXPENSES.items():
        print('  %-4s %s  $%7.2f' % (k, e['date'], e['amount']))
    print('\n  Plan A period: $2100 applied against $3000 - not met')
    print('  Plan B period: $1600 applied against $1500 - MET')
    print('  2027 before Plan C arrives: $500 applied, met is UNKNOWN - never False')


# ── The assertions the model has to satisfy ─────────────────────────────────

def run(model):
    model.reset()

    a = model.add_plan(**PLAN_A)

    check('a plan in force is found by date',
          model.plan_at('2026-03-01') is a and model.plan_at('2026-08-01') is None)

    acc_a_before = model.accumulators(EXPENSES, a)
    check('the Plan A period accumulates only what fell inside it',
          acc_a_before['applied'] == 2100.00)
    check('and the deductible is not met, on the terms as they stand',
          acc_a_before['deductible'] == 3000.00
          and acc_a_before['deductible_met'] is False)
    check('out-of-pocket is reported separately from the deductible',
          acc_a_before['oop_applied'] == 2100.00 and acc_a_before['oop_max'] == 6000.00
          and acc_a_before['oop_met'] is False)

    # ── Switching plans changes what is true going forward, and nothing else ─
    # The critical case. Mutating a plan_id here would destroy the first half of the year.
    b = model.add_plan(**PLAN_B)
    check('adding the second plan does not touch the first half of the year',
          model.accumulators(EXPENSES, a)['applied'] == 2100.00
          and model.accumulators(EXPENSES, a) == acc_a_before)
    check('a December expense does not count toward the plan that ended in June',
          model.accumulators(EXPENSES, b)['applied'] == 1600.00)
    check('and the second plan reaches its own, smaller deductible',
          model.accumulators(EXPENSES, b)['deductible_met'] is True)
    check('historical expenses retain the plan they were incurred under',
          model.plan_of('x1', EXPENSES) is a and model.plan_of('x3', EXPENSES) is b)

    # ── Correction is a different operation from a change ───────────────────
    at_first = model.now()
    model.correct_terms(a, deductible=2000.00,
                        reason='benefits summary shows $2,000',
                        source='imported_plan_document')

    check('a correction to a historical fact changes the historical conclusion',
          model.accumulators(EXPENSES, a)['deductible_met'] is True)
    check('because it says the figure was always wrong, not that it changed today',
          model.terms_at(a)['deductible'] == 2000.00)
    check('the prior terms survive, oldest first',
          len(model.term_history(a)) == 2
          and model.term_history(a)[0].terms['deductible'] == 3000.00)
    check('and the correction carries old value, new value, source and timestamp',
          model.term_history(a)[-1].previous['deductible'] == 3000.00
          and model.term_history(a)[-1].terms['deductible'] == 2000.00
          and bool(model.term_history(a)[-1].source)
          and model.term_history(a)[-1].recorded_at is not None)
    check('the earlier conclusion is still reproducible as of when it was true',
          model.accumulators(EXPENSES, a, as_of=at_first)['deductible_met'] is False)

    # The two operations must not look alike. Discovering the deductible was $2,000 corrects
    # a fact that was always wrong; switching to Plan B changed what is true going forward.
    kinds = {op.kind for op in model.operations()}
    check('a terms correction and a plan change are distinguishable operations',
          'correction' in kinds and 'change' in kinds)
    check('and adding a plan is never recorded as a correction to the old one',
          all(op.kind == 'change' for op in model.operations(plan=b)))

    # ── The year nobody has entered a plan for ──────────────────────────────
    # How much was spent is a fact. Whether it met a deductible is an interpretation, and
    # there is nothing to interpret it against.
    y2027 = model.year_summary(EXPENSES, 2027)
    check('spending in a year with no plan on file is still reported',
          y2027['applied'] == 500.00)
    check('but whether anything was met is UNKNOWN, not False',
          y2027['deductible_met'] is model.UNKNOWN)
    check('and the plan is named as missing rather than assumed',
          y2027['periods'] == [] and y2027['unattributed'] == 500.00)

    # ── Rollover is not an operation ────────────────────────────────────────
    y2026 = model.year_summary(EXPENSES, 2026)
    check('a year with two plans is summarised as two periods, not one',
          len(y2026['periods']) == 2)
    check('and the year total is the sum of its periods, with nothing unattributed',
          y2026['applied'] == 3700.00 and y2026['unattributed'] == 0.00)
    check('nothing had to be reset for 2027 to start from nothing',
          not hasattr(model, 'rollover'))
    check('and asking about 2027 did not disturb 2026',
          model.year_summary(EXPENSES, 2026) == y2026)

    # ── Late-arriving plan data is first class ──────────────────────────────
    before_c = model.now()
    model.add_plan(**PLAN_C)
    y2027_after = model.year_summary(EXPENSES, 2027)
    check('a January expense is re-evaluated against plan data that arrives in March',
          y2027_after['deductible_met'] is False
          and y2027_after['applied'] == 500.00)
    check('and the answer before that data arrived is still reproducible',
          model.year_summary(EXPENSES, 2027,
                             as_of=before_c)['deductible_met'] is model.UNKNOWN)

    # ── A historical plan record is effectively immutable ───────────────────
    check('deleting a plan with expenses under it is refused',
          model.delete_plan(a, EXPENSES) is False)
    check('and the honest operation is offered instead',
          'close_period' in model.deletion_modes())
    check('a plan nothing was incurred under may be removed',
          model.delete_plan(model.add_plan(name='Typo', deductible=0, oop_max=0,
                                           effective_from='2030-01-01',
                                           effective_to='2030-12-31'), EXPENSES) is True)


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    try:
        from core import plan_year as model         # noqa: F401
    except ImportError:
        print('\nNo model yet — core/plan_year.py does not exist.')
        print('This file is the specification it has to satisfy.')
        describe()
        print('\nAlso required, and not expressible as a table:')
        print('  * accumulators are DERIVED, never stored, which is why rollover is not an')
        print('    operation: nothing resets, so nothing can forget to')
        print('  * adding a plan must not touch any earlier period')
        print('  * a terms CORRECTION says the figure was always wrong and changes the')
        print('    historical conclusion; a plan CHANGE says what is true going forward.')
        print('    They must be distinguishable, and a correction carries old value, new')
        print('    value, source and timestamp')
        print('  * every conclusion stays reproducible as of when it was true')
        print('  * a year with no plan on file reports the spend and UNKNOWN - never False,')
        print('    never zero - and names the gap rather than assuming a deductible')
        print('  * late plan data re-evaluates the expenses already incurred under it')
        print('  * a historical plan record is effectively immutable: deleting one that has')
        print('    expenses under it is refused')
        print('\n0 passed, 0 failed — every assertion above is pending a model')
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    return 1 if (FAIL or PENDING) else 0


if __name__ == '__main__':
    sys.exit(main())
