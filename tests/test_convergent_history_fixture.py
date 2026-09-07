# -*- coding: utf-8 -*-
"""The hostile convergent-history fixture — two histories, one present balance.

Gap 1 of `gw 2.0/HEALTHCARE_GAP_TRIAGE.md`, stated by Rob:

    When two different event histories produce the same apparent financial state, does
    Groundwork know whether they are actually equivalent?

```text
History A                          History B
obligation created  $400           obligation created  $400
→ corrected to      $275           → voided
                                   → replacement created  $275
```

Both end with $275 owed. **That is the only thing about them that is the same.**

**This is not the arrival-order question.** The lifecycle fixture already asserts that the same
facts in any order produce the same state. This asks something different and harder: whether
*different* facts producing the same number are distinguishable afterwards.

**Written before the mechanism, and it exposed one immediately:** history B is not currently
representable. There is no way to void an obligation — `deletion_modes()` covers allocations,
not the expense itself — so the model today can express a correction and cannot express a
retraction. That is a decision the implementation is making silently, which is exactly what this
fixture exists to surface.

**What must be identical, and what must differ**, derived from settled doctrine rather than
invented here:

| | | why |
|---|---|---|
| current balance | **identical** | both owe $275; if they differed one is arithmetically wrong |
| obligation identity | **differs** | A is one obligation restated; B is two, one retracted |
| provenance | **differs** | *we had the amount wrong* is not *that bill was not real* |
| what a payment attaches to | **differs** | and this is where the money goes wrong |
| derived facts | **cite different sources** | a voided obligation must not contribute |

Run:  python tests/test_convergent_history_fixture.py
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


BILL = {'amount': 400.00, 'incurred_on': '2026-02-01', 'person': 'rob'}


def describe():
    print('\nThe fixture, as a specification:\n')
    print('  History A   created $400  ->  corrected to $275')
    print('  History B   created $400  ->  voided  ->  replacement $275')
    print('\n  identical:  the current balance, and nothing else')
    print('  differs:    obligation identity, provenance, what a payment attaches to,')
    print('              and which sources a derived figure may cite')


def run(model):
    # ── History A: one obligation, restated ─────────────────────────────────
    a = model.new_expense(**BILL)
    model.apply(a, {'kind': 'correct_expense', 'to': 275.00})

    # ── History B: one obligation retracted, another created ────────────────
    b_old = model.new_expense(**BILL)
    model.apply(b_old, {'kind': 'void_obligation',
                        'reason': 'billed in error, provider reissued',
                        'occurred_on': '2026-03-01'})
    b_new = model.new_expense(amount=275.00, incurred_on='2026-02-01', person='rob')
    model.link_replacement(b_old, b_new)

    # ── The one thing that is the same ──────────────────────────────────────
    check('both histories end owing the same amount',
          model.state(a)['expense'] == model.state(b_new)['expense'] == 275.00)

    # ── And everything that is not ──────────────────────────────────────────
    check('a voided obligation owes nothing, rather than still owing $400',
          model.state(b_old)['expense'] == 0.00 and model.is_void(b_old))
    check('the corrected obligation was never voided',
          not model.is_void(a))

    check('A is one obligation restated; B is two, and the identities differ',
          len(model.obligation_versions(a)) == 2
          and len(model.obligation_versions(b_new)) == 1)

    check('the provenance says which happened, in the terms the user would recognise',
          model.history_kind(a) == 'corrected'
          and model.history_kind(b_new) == 'replacement')
    check('and the retraction carries its reason and its date',
          bool(model.void_record(b_old)['reason'])
          and model.void_record(b_old)['occurred_on'] == '2026-03-01')

    check('the replacement knows what it replaced, and the void knows it was replaced',
          model.replaced_by(b_old) is b_new and model.replaces(b_new) is b_old)

    # ── Where the money actually goes wrong ─────────────────────────────────
    # A payment made against the bill that was retracted is not a payment against the one
    # that replaced it. If those collapse, $275 gets satisfied by money that was attached to
    # a bill nobody owes - which looks like a paid obligation and is not one.
    model.allocate(b_old, funder='user', amount=275.00)
    check('a payment attached to the retracted bill does not fund its replacement',
          model.state(b_new)['unallocated'] == 275.00)
    check('and it is still visible on the bill it was actually attached to',
          model.state(b_old)['user'] == 275.00)
    check('so the retracted bill shows money against an obligation of zero, which is a '
          'state a user can be shown and asked about',
          model.state(b_old)['unallocated'] == -275.00)

    # The same payment against history A behaves normally, which is the contrast.
    model.allocate(a, funder='user', amount=275.00)
    check('the corrected obligation is funded by the same payment, because it is the '
          'same obligation',
          model.state(a)['unallocated'] == 0.00)

    # ── Derived facts may not cite what was retracted ───────────────────────
    check('a figure over the household cites the replacement, never the void',
          model.household_obligations([a, b_old, b_new]) == [a, b_new])

    # ── The question this fixture exists to force ───────────────────────────
    # Not "do they agree" - they do, on the number. The question is whether the system can
    # still tell them apart afterwards, and answer why they are the same size.
    check('the two histories are NOT reported as equivalent merely because they agree',
          not model.histories_equivalent(a, b_new))
    check('and the difference is nameable rather than merely present',
          model.history_difference(a, b_new) is not None)


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    try:
        from core import allocation as model          # noqa: F401
        model.void_obligation_supported
    except (ImportError, AttributeError):
        print('\nNo mechanism yet — core/allocation.py cannot express a retraction.')
        print('This file is the specification it has to satisfy.')
        describe()
        print('\nAlso required, and not expressible as a table:')
        print('  * a voided obligation owes nothing and is NOT deleted - the review already')
        print('    settled that hard deletion is prohibited once financial relationships')
        print('    exist, so a retraction is a state, not a removal')
        print('  * a payment attached to a retracted bill does not fund its replacement,')
        print('    and remains visible where it was actually attached')
        print('  * that leaves money against a zero obligation, which is a real state and')
        print('    must be showable rather than netted away')
        print('  * a derived figure may cite the replacement and never the void')
        print('  * the two histories must not be reportable as equivalent, and the')
        print('    difference must be nameable rather than merely present')
        print('\n0 passed, 0 failed — every assertion above is pending a mechanism')
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    return 1 if (FAIL or PENDING) else 0


if __name__ == '__main__':
    sys.exit(main())
