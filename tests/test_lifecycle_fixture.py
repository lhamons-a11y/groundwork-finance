# -*- coding: utf-8 -*-
"""The hostile lifecycle fixture — written BEFORE the model it tests.

`gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` concluded that another conceptual pass would
produce diminishing returns, and that the way forward is to make the smallest real piece
survive the worst plausible lifecycle. This is that piece: **one healthcare expense with
three funders**, put through ten mutations.

It is deliberately written first, against nothing. Nothing here imports a model, because no
model exists — running it prints the specification it is asserting and exits non-zero. When
`core/allocation.py` exists, this file is what decides whether it works.

The order matters. A check written after the thing it checks gets shaped to flatter it; this
project has caught itself doing that three times in one session. Written first, the model has
to come to the test.

**The pre-registered failure criterion** (`EVENT_SUBSTRATE_QUESTION.md`): if making
`HistorianEntry` carry this requires more than TWO structural relationships to live inside
`context_json`, or if any read path must parse JSON to enforce an invariant, the historian has
failed the experiment and a typed event store is warranted. Declared here, before the
experiment, so the answer cannot be argued on attachment.

Run:  python tests/test_lifecycle_fixture.py
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


# ── The fixture ──────────────────────────────────────────────────────────────
# One expense, three funders, ten mutations. Every figure below is stated as the
# state AFTER that mutation, so a model can be driven straight from this table.

EXPENSE = {
    'amount': 1000.00,
    'incurred_on': '2026-01-15',
    'person': 'rob',
    'plan': 'plan-a',
}

INITIAL_ALLOCATIONS = [
    {'funder': 'insurance', 'amount': 300.00},
    {'funder': 'hsa',       'amount': 400.00},
    {'funder': 'user',      'amount': 300.00},
]

MUTATIONS = [
    # (name, what happens, expected state after)
    ('M1 insurance correction 300 -> 250',
     {'kind': 'correct_allocation', 'funder': 'insurance', 'to': 250.00},
     {'insurance': 250.00, 'hsa': 400.00, 'user': 300.00, 'unallocated': 50.00,
      'expense': 1000.00}),

    ('M2 HSA distribution reversed',
     {'kind': 'reverse_allocation', 'funder': 'hsa'},
     {'insurance': 250.00, 'hsa': 0.00, 'user': 300.00, 'unallocated': 450.00,
      'expense': 1000.00}),

    ('M3 expense corrected 1000 -> 1200',
     {'kind': 'correct_expense', 'to': 1200.00},
     {'insurance': 250.00, 'hsa': 0.00, 'user': 300.00, 'unallocated': 650.00,
      'expense': 1200.00}),

    ('M4 duplicate EOB imported -> no new funding event',
     {'kind': 'import_eob', 'duplicate_of': 'insurance'},
     {'insurance': 250.00, 'hsa': 0.00, 'user': 300.00, 'unallocated': 650.00,
      'expense': 1200.00}),

    ('M5 plan changes 1 July -> January expense stays on plan A',
     {'kind': 'change_plan', 'to': 'plan-b', 'effective': '2026-07-01'},
     {'expense_plan': 'plan-a'}),

    ('M6 2027 begins -> the January 2026 expense stays in 2026 on plan A',
     {'kind': 'roll_year', 'to': 2027},
     {'expense_plan': 'plan-a', 'expense_year': 2026}),

    ('M7 tax rules change -> the 2026 figure stays reproducible under v2026.1',
     {'kind': 'change_rules', 'to': 'v2027.1'},
     {'reproduce_under': 'v2026.1'}),

    ('M8 the same facts in any arrival order produce the same answer',
     {'kind': 'replay', 'orders': 3},
     {'identical': True}),

    ('M9 two expenses found to be one -> merge preserves both provenances',
     {'kind': 'merge', 'with': 'duplicate-expense'},
     {'reversible': True, 'provenance_preserved': True}),

    ('M10 "delete the reimbursement" is ambiguous and must not be one operation',
     {'kind': 'delete_allocation', 'funder': 'insurance'},
     {'distinguishes': ['correction', 'void', 'destruction']}),
]


def describe():
    """Print the fixture as a specification, for when no model exists yet."""
    print('\nThe fixture, as a specification:\n')
    print('  expense  $%.2f on %s, person=%s, plan=%s'
          % (EXPENSE['amount'], EXPENSE['incurred_on'], EXPENSE['person'], EXPENSE['plan']))
    for a in INITIAL_ALLOCATIONS:
        print('    funded  %-10s $%.2f' % (a['funder'], a['amount']))
    print()
    for name, _op, expected in MUTATIONS:
        print('  %-58s %s' % (name, expected))


# ── The assertions the model has to satisfy ─────────────────────────────────

def run(model):
    """Drive `model` through the fixture. `model` is whatever core/allocation.py exposes."""
    exp = model.new_expense(**EXPENSE)
    for a in INITIAL_ALLOCATIONS:
        model.allocate(exp, **a)

    check('the initial allocations sum to the expense, with nothing unallocated',
          model.unallocated(exp) == 0.00)

    for name, op, expected in MUTATIONS[:4]:
        model.apply(exp, op)
        got = {k: model.state(exp).get(k) for k in expected}
        check(name, got == expected)
        if got != expected:
            print(f'        expected {expected}')
            print(f'        got      {got}')

    # ── The trap this fixture exists to catch ───────────────────────────────
    # After M3 there is $650 nobody has paid. It is NOT the taxpayer's money and
    # must not be silently rolled into the qualifying total just because it is
    # not reimbursed. "Unallocated" and "user-paid" are different facts, and a
    # tax figure that confuses them overstates a deduction on a filed return.
    check('unallocated money is not treated as paid by the user',
          model.state(exp)['unallocated'] != model.state(exp)['user'])

    # ┌─ FROZEN — DO NOT "FIX" ────────────────────────────────────────────┐
    # │ The assertion below is KNOWN TO BE WRONG, and is left standing on   │
    # │ purpose. $300 assumes the unreconciled $650 was never paid; $950    │
    # │ (gross − reimbursement) assumes the user paid it. Both assign a     │
    # │ meaning to an unknown, which is the thing the check above forbids.  │
    # │                                                                     │
    # │ It has not been corrected because correcting it means choosing a    │
    # │ number before the semantics are settled, and the fixture would then │
    # │ encode that choice invisibly for every tax rule written after it.   │
    # │                                                                     │
    # │ See gw 2.0/OBLIGATION_SEMANTICS_QUESTION.md. When observed and      │
    # │ inferred obligations are distinguished, this becomes a PAIR —       │
    # │ confirmed qualifying AND unresolved — and the fixture becomes a     │
    # │ good test instead of a broken one.                                  │
    # └─────────────────────────────────────────────────────────────────────┘
    check('and the qualifying total counts what was actually paid, not the gap',
          model.qualifying(exp, rules='v2026.1') == 300.00)

    # ── Temporal: history is not rewritten by the present ───────────────────
    for name, op, expected in MUTATIONS[4:7]:
        model.apply(exp, op)
        got = {k: model.state(exp).get(k) for k in expected if k != 'reproduce_under'}
        if 'reproduce_under' in expected:
            check(name, model.qualifying(exp, rules='v2026.1') == 300.00)
        else:
            check(name, got == {k: v for k, v in expected.items()})

    check('a new rule version may give a different answer without changing the old one',
          model.qualifying(exp, rules='v2027.1') is not None
          and model.qualifying(exp, rules='v2026.1') == 300.00)

    check('every reported figure can name the records that produced it',
          bool(model.explain(model.qualifying(exp, rules='v2026.1'))))

    # ── Arrival order: the assertion that falsifies most designs ────────────
    # An EOB imported in March describes January, and a correction was recorded
    # in February. If events apply in ARRIVAL order rather than EFFECTIVE order,
    # the answer depends on import sequence. Imports are retroactive by nature,
    # so this is not an edge case.
    replays = [model.replay(EXPENSE, INITIAL_ALLOCATIONS, MUTATIONS[:7], order=i)
               for i in range(3)]
    check('the same facts in any arrival order produce the same final state',
          all(r['state'] == replays[0]['state'] for r in replays))
    check('and reproduce the same historical figure',
          all(r['qualifying_v2026_1'] == replays[0]['qualifying_v2026_1'] for r in replays))

    # ── Identity and deletion ───────────────────────────────────────────────
    merged = model.merge(exp, model.new_expense(**EXPENSE))
    check('a merge is reversible', model.can_unmerge(merged))
    check('and both original provenances survive it',
          len(model.provenance(merged)) >= 2)

    check('"delete this reimbursement" is not one operation',
          set(model.deletion_modes()) >= {'correction', 'void'})
    check('a correction says the reimbursement never happened, and is recoverable',
          model.apply(exp, {'kind': 'correct_allocation', 'funder': 'insurance',
                            'to': 0.00}) and model.explain_change(exp) is not None)


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    try:
        from core import allocation as model          # noqa: F401
    except ImportError:
        print('\nNo model yet — core/allocation.py does not exist.')
        print('This file is the specification it has to satisfy.')
        describe()
        print('\nAlso required, and not expressible as a table:')
        print('  * every figure explains itself down to source records')
        print('  * a historical figure is reproducible under the rule version in force')
        print('    when it was first computed, after the rules have changed')
        print('  * arrival order does not affect the answer')
        print('  * unallocated money is never counted as money the user paid')
        print('\n0 passed, 0 failed, %d pending a model' % (len(MUTATIONS) + 8))
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
