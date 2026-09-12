# -*- coding: utf-8 -*-
"""The hostile payment-state fixture — five dimensions that must not contradict each other.

Gap 6 of `gw 2.0/HEALTHCARE_GAP_TRIAGE.md`. The invariant, in Rob's wording:

    Payment state is a coherent projection of the obligation's transaction history; no
    payment-state dimension may contradict the reconciled transaction ledger or another
    derived payment-state dimension.

Stated that way rather than as *these numbers must agree*, because it leaves room for
complexity without baking today's arithmetic into the rule.

**The sequence, against a $4,000 obligation on a 24 × $175 agreement:**

```text
175  →  175  →  500  →  −50  →  300
```

The negative entry is what makes this worth writing. It forces the model to prove it
*understands reversal* rather than merely accumulating signed numbers: after it, `paid` falls,
`remaining` rises, the schedule position moves back, and `ahead` is recomputed — and nothing
downstream may still rest on the payment that was invalidated.

**The state vector is asserted at every step, never just at the end.** A test that checks only
the final $2,900 remaining permits an implementation that is wrong in the middle and right by
the time anyone looks.

**And the adversarial case Rob added:** a −$700 entry when $850 has been paid across three
payments, none larger than $500. That is not arithmetically impossible, and it is not obviously
a reversal — it could be an adjustment, an over-reversal, or invalid. The model must not let
arithmetic decide silently.

**The schedule is supplied by the caller.** Payment-plan *versioning* is gap 8, and it needs a
domain object that does not exist; inventing one here would hide that. See the note at the end.

Run:  python tests/test_payment_state_fixture.py
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


GROSS = 4000.00
SCHEDULE = {'instalment': 175.00, 'count': 24, 'first_due': '2026-01-01'}

# (label, month, paid-to-date, expected-by-then, ahead, overdue)
STEPS = [
    ('after the first instalment',  '2026-01-01',  175.00,  175.00,   0.00,   0.00),
    ('after the second',            '2026-02-01',  350.00,  350.00,   0.00,   0.00),
    ('after paying $500',           '2026-03-01',  850.00,  525.00, 325.00,   0.00),
    ('after $50 of it reverses',    '2026-04-01',  800.00,  700.00, 100.00,   0.00),
    ('after a further $300',        '2026-05-01', 1100.00,  875.00, 225.00,   0.00),
]


def describe():
    print('\nThe fixture, as a specification:\n')
    print('  obligation $%.2f on %d x $%.2f from %s\n'
          % (GROSS, SCHEDULE['count'], SCHEDULE['instalment'], SCHEDULE['first_due']))
    print('  %-28s %9s %9s %8s %8s %8s'
          % ('', 'paid', 'expected', 'ahead', 'overdue', 'remaining'))
    for label, _on, paid, expected, ahead, overdue in STEPS:
        print('  %-28s %9.2f %9.2f %8.2f %8.2f %8.2f'
              % (label, paid, expected, ahead, overdue, GROSS - paid))


def run(model):
    plan = model.new_plan(gross=GROSS, **SCHEDULE)

    p1 = model.record_payment(plan, 175.00, on='2026-01-01')
    model.record_payment(plan, 175.00, on='2026-02-01')
    p3 = model.record_payment(plan, 500.00, on='2026-03-01')

    # ── The whole vector at every step, not just the end ────────────────────
    for i, (label, on, paid, expected, ahead, overdue) in enumerate(STEPS):
        if i == 3:
            model.reverse_payment(plan, p3, amount=50.00, on='2026-04-01')
        if i == 4:
            model.record_payment(plan, 300.00, on='2026-05-01')
        st = model.payment_state(plan, as_of=on)
        got = (st['paid'], st['expected_by_now'], st['ahead'], st['overdue'],
               st['remaining'])
        want = (paid, expected, ahead, overdue, round(GROSS - paid, 2))
        check('%s: the whole vector' % label, got == want)
        if got != want:
            print('        want %s' % (want,))
            print('        got  %s' % (got,))

    # ── The dimensions are related, not independently reported ──────────────
    st = model.payment_state(plan, as_of='2026-05-01')
    check('paid and remaining account for the whole obligation',
          round(st['paid'] + st['remaining'], 2) == GROSS)
    check('ahead is what was paid beyond what was due by then',
          st['ahead'] == round(st['paid'] - st['expected_by_now'], 2))
    check('ahead and overdue cannot both be non-zero',
          not (st['ahead'] > 0 and st['overdue'] > 0))
    check('paid is the ledger, not a running total kept beside it',
          st['paid'] == round(sum(e.amount for e in model.ledger(plan)), 2))

    # And the coherence check the module exposes, so a consumer cannot reconstruct these
    # relationships slightly differently and drift.
    check('the module can verify its own projection against the ledger',
          model.incoherences(plan, as_of='2026-05-01') == [])

    # And the verifier has to be able to FIND something, or it is a stub that reports clean.
    # The projection is coherent by construction, so the only way to test the checker is to
    # hand it a state that is not - which is also the real use: a figure arriving from a
    # cache, an API response or a migration, asked whether it still agrees with the ledger.
    wrong = dict(model.payment_state(plan, as_of='2026-05-01'))
    wrong['ahead'] = 1250.00
    check('a state that disagrees with the ledger is reported, not waved through',
          model.incoherences(plan, as_of='2026-05-01', state=wrong) != [])
    drifted = dict(model.payment_state(plan, as_of='2026-05-01'))
    drifted['remaining'] = round(drifted['remaining'] - 100.00, 2)
    check('and so is one where paid and remaining no longer account for what is owed',
          model.incoherences(plan, as_of='2026-05-01', state=drifted) != [])

    # ── The reversal moved everything that depended on it ───────────────────
    before = model.payment_state(plan, as_of='2026-03-01')
    after = model.payment_state(plan, as_of='2026-04-01')
    check('the reversal reduced paid and raised remaining together',
          after['paid'] == before['paid'] - 50.00
          and after['remaining'] == before['remaining'] + 50.00)
    check('and the reversed amount is still on the record, not erased',
          model.reversed_total(plan) == 50.00)
    check('naming which payment it reversed, so nothing downstream rests on a ghost',
          model.reversals(plan)[0].reverses is p3)

    # ── Falling behind is representable, and is not negative "ahead" ────────
    late = model.new_plan(gross=GROSS, **SCHEDULE)
    model.record_payment(late, 175.00, on='2026-01-01')
    st_late = model.payment_state(late, as_of='2026-04-01')
    check('a plan that has fallen behind reports overdue, not negative ahead',
          st_late['overdue'] == 525.00 and st_late['ahead'] == 0.00)
    check('and being behind never makes remaining disagree with paid',
          round(st_late['paid'] + st_late['remaining'], 2) == GROSS)

    # ── The adversarial case: a reversal larger than any payment ────────────
    # $850 paid across 175 / 175 / 500. A −$700 entry is arithmetically possible and is not
    # obviously a reversal. Four readings, and the model must not pick one silently.
    adv = model.new_plan(gross=GROSS, **SCHEDULE)
    model.record_payment(adv, 175.00, on='2026-01-01')
    model.record_payment(adv, 175.00, on='2026-02-01')
    big = model.record_payment(adv, 500.00, on='2026-03-01')

    refused = model.reverse_payment(adv, big, amount=700.00, on='2026-04-01')
    check('reversing more than the payment it names is refused, not absorbed',
          refused is model.REFUSED)
    check('the refusal says what it could have reversed',
          model.last_refusal(adv)['available'] == 500.00
          and model.last_refusal(adv)['requested'] == 700.00)
    check('and the ledger is untouched by a refused operation',
          model.payment_state(adv, as_of='2026-04-01')['paid'] == 850.00)

    # The same $700 as an explicit adjustment IS allowed - because the caller has said what
    # it is, which is the whole difference.
    model.record_adjustment(adv, -700.00, reason='provider rebilled the account',
                            on='2026-04-01')
    st_adj = model.payment_state(adv, as_of='2026-04-01')
    check('an explicit adjustment is accepted where a silent reversal was not',
          st_adj['paid'] == 850.00 and st_adj['adjustments'] == -700.00)
    # The sign matters and the first draft of this assertion got it backwards: it computed
    # what remaining would be if the $700 had been a REVERSAL and labelled that the
    # adjustment's answer. Correcting it makes the point sharper, because the two readings
    # of the same number are now both stated and shown to differ.
    check('an adjustment changes what is owed, not what was paid',
          st_adj['paid'] == 850.00 and st_adj['remaining'] == 2450.00)
    check('whereas the same $700 as a reversal would have moved paid and left a different '
          'remaining entirely',
          round(GROSS - (850.00 - 700.00), 2) == 3850.00
          and st_adj['remaining'] != 3850.00)
    check('so the four readings of a negative number are not interchangeable',
          model.payment_state(plan, as_of='2026-05-01')['remaining'] != st_adj['remaining'])

    # ── Nothing here may claim discharge (HAZARD_AUDIT H2) ──────────────────
    # Every figure is a projection over ATTACHED payments; the module holds no
    # acknowledgment from the entitled party. So no key and no accessor may claim that a
    # payment was credited or an obligation discharged. Asserted as an absence, the way the
    # missing `paid()` accessor is: adding one later is a deliberate act with a test to
    # change, not a drift.
    CLAIMS = ('confirmed', 'discharged', 'acknowledged', 'credited')
    st_keys = set(model.payment_state(plan))
    check('no projection key claims confirmation, discharge or acknowledgment',
          not any(any(c in k.lower() for c in CLAIMS) for k in st_keys))
    check('and no module accessor does either',
          not any(any(c in name.lower() for c in CLAIMS) for name in dir(model)))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    try:
        from core import payment_plan as model       # noqa: F401
    except ImportError:
        print('\nNo model yet — core/payment_plan.py does not exist.')
        print('This file is the specification it has to satisfy.')
        describe()
        print('\nAlso required, and not expressible as a table:')
        print('  * the five dimensions are ONE projection computed together from the')
        print('    ledger, not five outputs a consumer reassembles - so they cannot')
        print('    drift apart by being read separately')
        print('  * a reversal NAMES the payment it reverses, and may not exceed it;')
        print('    exceeding is REFUSED rather than absorbed, and the refusal says what')
        print('    was available')
        print('  * an adjustment is a different operation with a different effect -')
        print('    it changes what is owed, not what was paid')
        print('  * falling behind reports overdue, never negative ahead')
        print('  * the reversed amount stays on the record and names its target')
        print('\n  NOT here, deliberately: payment-plan VERSIONING (gap 8). The schedule')
        print('  is a caller-supplied input; the domain object that would let an')
        print('  agreement change terms does not exist, and inventing one here would')
        print('  hide that gap rather than close it.')
        print('\n0 passed, 0 failed — every assertion above is pending a model')
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    return 1 if (FAIL or PENDING) else 0


if __name__ == '__main__':
    sys.exit(main())
