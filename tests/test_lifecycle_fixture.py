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

# The "no definitive total" sentinel belongs to the MODEL, not to this file: a local
# object() could never compare identical to anything a model returns, so the assertion
# below could only ever FAIL - a check unable to pass for the reason it names, which is
# the mirror image of the failure this project keeps finding. Fixed 2026-09-07 while
# building core/allocation.py; the assertion is unchanged, only expressible.

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

    ('M5 2027 begins -> the January 2026 expense stays in 2026',
     {'kind': 'roll_year', 'to': 2027},
     {'expense_year': 2026}),

    ('M6 tax rules change -> the 2026 figure stays reproducible under v2026.1',
     {'kind': 'change_rules', 'to': 'v2027.1'},
     {'reproduce_under': 'v2026.1'}),

    ('M7 the same facts in any arrival order produce the same answer',
     {'kind': 'replay', 'orders': 3},
     {'identical': True}),

    ('M8 two expenses found to be one -> merge preserves both provenances',
     {'kind': 'merge', 'with': 'duplicate-expense'},
     {'reversible': True, 'provenance_preserved': True}),

    ('M9 "delete the reimbursement" is ambiguous and must not be one operation',
     {'kind': 'delete_allocation', 'funder': 'insurance'},
     {'distinguishes': ['correction', 'void', 'destruction']}),
]


def describe():
    """Print the fixture as a specification, for when no model exists yet."""
    print('\nThe fixture, as a specification:\n')
    print('  expense  $%.2f on %s, person=%s'
          % (EXPENSE['amount'], EXPENSE['incurred_on'], EXPENSE['person']))
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

    # The figure is a PAIR, and neither half may be inferred from the other.
    # $300 is not "gross minus reimbursed minus unresolved" — that would be
    # assuming the $650 went unpaid, which is the same forbidden move as
    # assuming the user paid it ($950). It is the SUM of cleared, attached,
    # user-confirmed payments the user made. The $650 is unresolved because
    # nothing is attached to it, which is a fact about the record rather than a
    # claim about the world. See gw 2.0/OBLIGATION_SEMANTICS_QUESTION.md.
    figure = model.qualifying(exp, rules='v2026.1')
    check('the confirmed total is the sum of evidenced user payments, not a subtraction',
          figure.confirmed_user_paid == 300.00
          and figure.basis == 'sum_of_confirmed_user_payments')
    check('and the unresolved balance is reported beside it, never folded into it',
          figure.unresolved == 650.00)

    # The assertion that makes this a specification rather than a calculator.
    # $300 is what can be PROVEN, not what is true — the truth is $300 or $950
    # and nothing here knows which. So there is no definitive total while any
    # part of the obligation is unresolved, and the model must say so rather
    # than nominate one of the two candidates.
    check('there is NO definitive qualifying total while anything is unresolved',
          figure.total is model.UNRESOLVED)

    check('a payment is confirmed only when cleared, attached, and user-confirmed',
          model.confirms_on() == {'cleared', 'attached', 'user_confirmed'})
    check('cleared alone is not enough, because cleared defaults to true',
          not model.is_confirmed(model.payment(exp, cleared=True, attached=False)))

    # ── The positive half: resolving the $650 must change the answer ────────
    # Two branches from the same state. If the ambiguity was real, these must
    # diverge — and if a model returns the same total for both, it was guessing
    # all along and the guess simply happened to match one branch.
    # NOT "resolve" — nothing here is terminal. `unpaid` becomes `user_paid_cash`
    # when a receipt surfaces months later; a write-off reverses if the provider
    # re-bills. These are current DETERMINATIONS, superseded rather than
    # overwritten, each carrying provenance and a date.
    write_off = model.branch(exp)
    model.apply(write_off, {'kind': 'record_determination',
                            'status': 'provider_adjustment', 'amount': 650.00})
    f1 = model.qualifying(write_off, rules='v2026.1')
    check('resolved as a provider write-off: gross falls, the total becomes available',
          f1.gross == 550.00 and f1.unresolved == 0.00 and f1.total == 300.00)

    paid_cash = model.branch(exp)
    model.apply(paid_cash, {'kind': 'record_determination',
                            'status': 'user_paid_cash', 'amount': 650.00,
                            'evidence': 'receipt'})
    f2 = model.qualifying(paid_cash, rules='v2026.1')
    check('resolved as a cash payment by the user: the total becomes available, and differs',
          f2.unresolved == 0.00 and f2.total == 950.00)

    # And the receipt is REQUIRED, not decorative. Section 213 deducts what was paid and
    # substantiation is the taxpayer's burden, so an unevidenced cash payment settles the
    # reconciliation without becoming deductible. Mutation-testing found that dropping the
    # evidence requirement broke nothing, because nothing asked.
    unevidenced = model.branch(exp)
    model.apply(unevidenced, {'kind': 'record_determination',
                              'status': 'user_paid_cash', 'amount': 650.00})
    f3 = model.qualifying(unevidenced, rules='v2026.1')
    check('an unevidenced cash payment is not deductible, though it settles the balance',
          f3.unresolved == 0.00 and f3.confirmed_user_paid == 300.00)

    check('the two determinations diverge, which is what made the ambiguity real',
          f1.total != f2.total)

    # unpaid and pending_claim produce the same tax figure today and are NOT the
    # same state: one says nobody paid, the other says nobody yet knows who
    # bears it. Their futures differ, so collapsing them loses the difference
    # exactly when a later transition needs it.
    unpaid = model.branch(exp)
    model.apply(unpaid, {'kind': 'record_determination', 'status': 'unpaid',
                         'amount': 650.00})
    pending = model.branch(exp)
    model.apply(pending, {'kind': 'record_determination', 'status': 'pending_claim',
                          'amount': 650.00})
    check('unpaid and pending_claim are distinct states, not one state',
          model.state(unpaid)['status'] != model.state(pending)['status'])
    check('unpaid settles the evidence question and leaves the obligation open',
          model.qualifying(unpaid, rules='v2026.1').total == 300.00
          and model.state(unpaid)['outstanding'] == 650.00)
    check('pending_claim settles nothing, so there is still no total',
          model.qualifying(pending, rules='v2026.1').total is model.UNRESOLVED)
    check('and a determination can be superseded when evidence arrives later',
          model.apply(unpaid, {'kind': 'record_determination',
                               'status': 'user_paid_cash', 'amount': 650.00,
                               'evidence': 'receipt'})
          and model.qualifying(unpaid, rules='v2026.1').total == 950.00
          and len(model.determinations(unpaid)) == 2)

    # ── The plan boundary: this module does not know, and does not guess ────
    # Which plan covered a charge is a household fact, owned by core/plan_year.py and
    # derived from the period covering the date. Two modules deriving it from two places is
    # the fusion this architecture is written against, and it was caught when the schema had
    # to pick one. So allocation reports what it is told - and the two ways of not having a
    # plan are different answers.
    check('with nobody supplying a plan, the plan is UNRESOLVED rather than guessed',
          model.state(exp)['expense_plan'] is model.UNRESOLVED)
    check('a supplied plan is reported as given',
          model.state(exp, plan='plan-a')['expense_plan'] == 'plan-a')
    check('and "no plan covered this date" is a real answer, distinct from not knowing',
          model.state(exp, plan=None)['expense_plan'] is None)

    # ── Temporal: history is not rewritten by the present ───────────────────
    for name, op, expected in MUTATIONS[4:6]:
        model.apply(exp, op)
        got = {k: model.state(exp).get(k) for k in expected if k != 'reproduce_under'}
        if 'reproduce_under' in expected:
            check(name, model.qualifying(exp, rules='v2026.1').confirmed_user_paid == 300.00)
        else:
            check(name, got == {k: v for k, v in expected.items()})

    check('a new rule version may give a different answer without changing the old one',
          model.qualifying(exp, rules='v2027.1') is not None
          and model.qualifying(exp, rules='v2026.1').confirmed_user_paid == 300.00)

    # A figure must CARRY the rules it was computed under. Mutation-testing found that
    # without this the `rules` argument can be ignored in favour of whatever version is
    # current, and every check above still passes - because the rules do not change this
    # arithmetic today. The next rule set will, and by then the figures are historical.
    check('and the figure names the rule version it was computed under',
          model.qualifying(exp, rules='v2026.1').rules == 'v2026.1'
          and model.qualifying(exp, rules='v2027.1').rules == 'v2027.1')

    check('every reported figure can name the records that produced it',
          bool(model.explain(model.qualifying(exp, rules='v2026.1'))))

    # ── Arrival order: the assertion that falsifies most designs ────────────
    # An EOB imported in March describes January, and a correction was recorded
    # in February. If events apply in ARRIVAL order rather than EFFECTIVE order,
    # the answer depends on import sequence. Imports are retroactive by nature,
    # so this is not an edge case.
    replays = [model.replay(EXPENSE, INITIAL_ALLOCATIONS, MUTATIONS[:6], order=i)
               for i in range(3)]
    check('the same facts in any arrival order produce the same final state',
          all(r['state'] == replays[0]['state'] for r in replays))
    check('and reproduce the same historical figure',
          all(r['qualifying_v2026_1'] == replays[0]['qualifying_v2026_1'] for r in replays))

    # And the two checks above CANNOT FAIL for the reason they name, which was found by
    # mutation-testing this file on 2026-09-07: M1-M7 all touch different things, so they
    # commute, and a model folding events in arrival order passes them both. The headline
    # assertion of this fixture was decorative. This is the pair that makes it real - two
    # corrections to the SAME allocation, where the later EFFECTIVE one must win whichever
    # order they arrive in.
    ordered = [
        ('insurance corrected to 250', {'kind': 'correct_allocation',
                                        'funder': 'insurance', 'to': 250.00}, {}),
        ('insurance corrected again to 275', {'kind': 'correct_allocation',
                                              'funder': 'insurance', 'to': 275.00}, {}),
    ]
    both = [model.replay(EXPENSE, INITIAL_ALLOCATIONS, ordered, order=i) for i in range(2)]
    check('the later correction wins whichever order the two arrive in',
          all(r['state']['insurance'] == 275.00 for r in both))


    # ── Reversal and chargeback: unwinding what was already accounted for ───
    # P0 section 10. "A reversal is not a refund. A refund returns money after an expense; a
    # reversal unwinds the original payment" - and the case that makes it P0 is a $1,000
    # expense funded by a $1,000 HSA distribution, where the payment then reverses. Posting
    # -$1,000 does not resolve it: an HSA distribution that was unwound is not a qualified
    # distribution, and a model that only zeroes the allocation has destroyed the fact that
    # the distribution ever happened.
    rev = model.new_expense(amount=1000.00, incurred_on='2026-02-01', person='rob')
    model.allocate(rev, funder='hsa', amount=1000.00)
    check('fully funded by one distribution, nothing unallocated',
          model.state(rev)['unallocated'] == 0.00)

    model.apply(rev, {'kind': 'reverse_allocation', 'funder': 'hsa',
                      'occurred_on': '2026-09-05'})
    check('a reversal returns the money to unallocated',
          model.state(rev)['hsa'] == 0.00 and model.state(rev)['unallocated'] == 1000.00)
    check('and the distribution that was unwound is still on the record',
          model.state(rev)['unwound'] == 1000.00)

    # The distinction the whole section turns on. A correction says the figure was always
    # wrong - there was never a distribution. A reversal says there WAS one and it came back.
    # Same $0 today, and a tax consumer has to tell them apart.
    corr = model.new_expense(amount=1000.00, incurred_on='2026-02-01', person='rob')
    model.allocate(corr, funder='hsa', amount=1000.00)
    model.apply(corr, {'kind': 'correct_allocation', 'funder': 'hsa', 'to': 0.00})
    check('a correction to zero leaves the same amount funded as a reversal',
          model.state(corr)['hsa'] == model.state(rev)['hsa'] == 0.00)
    check('but nothing was unwound, because nothing ever happened',
          model.state(corr)['unwound'] == 0.00)
    check('so the two are distinct states, not one state reached two ways',
          model.state(corr)['unwound'] != model.state(rev)['unwound'])

    check('the reversal names what it unwound, and when',
          model.explain_change(rev)['mode'] == 'reversal'
          and model.explain_change(rev)['funder'] == 'hsa'
          and model.explain_change(rev)['from'] == 1000.00
          and model.explain_change(rev)['occurred_on'] == '2026-09-05')
    check('and the two dates are not collapsed - the expense is still a February one',
          model.state(rev)['expense_year'] == 2026
          and model.explain_change(rev)['occurred_on'] > '2026-02-01')

    # Not terminal, which is what makes it a chargeback rather than a deletion. A disputed
    # charge can come back, and the record has to survive the round trip.
    model.apply(rev, {'kind': 'reinstate_allocation', 'funder': 'hsa',
                      'occurred_on': '2026-10-01'})
    check('a reversal can itself be reversed, and the funding returns',
          model.state(rev)['hsa'] == 1000.00 and model.state(rev)['unwound'] == 0.00)
    check('and all three events survive, superseded rather than overwritten',
          len([c for c in model.changes(rev) if c['what'] == 'allocation']) == 2)

    # ── Refund is a third thing, and collapsing it mangles tax ──────────────
    # Reimbursement is a third party funding an expense. A refund reduces the expense itself.
    # A reversal unwinds a payment. All three move a number; none of them means the same.
    ref = model.new_expense(amount=1000.00, incurred_on='2026-03-01', person='rob')
    model.allocate(ref, funder='user', amount=1000.00)
    before_refund = model.qualifying(ref, rules='v2026.1')
    check('the expense is fully funded by the user before anything comes back',
          before_refund.confirmed_user_paid == 1000.00 and before_refund.gross == 1000.00)

    # A refund names who received it. Without that the obligation falls to $800 while the
    # user still shows $1,000 paid, and the deduction is overstated by exactly the refund -
    # money back in their pocket, still on their return.
    model.apply(ref, {'kind': 'refund', 'amount': 200.00, 'to': 'user',
                      'occurred_on': '2026-11-01'})
    after_refund = model.qualifying(ref, rules='v2026.1')
    check('a refund reduces the obligation, because the care cost less in the end',
          after_refund.gross == 800.00)
    check('and reduces what the person is out of pocket, which is what is deductible',
          after_refund.confirmed_user_paid == 800.00)
    check('and it is recorded as a refund, never as a correction',
          model.explain_change(ref)['mode'] == 'refund')

    # The same $200 as a reversal of the user's payment would mean something else entirely:
    # the obligation stands and $200 of it is no longer funded.
    rev2 = model.new_expense(amount=1000.00, incurred_on='2026-03-01', person='rob')
    model.allocate(rev2, funder='user', amount=1000.00)
    model.apply(rev2, {'kind': 'correct_allocation', 'funder': 'user', 'to': 800.00})
    model.apply(rev2, {'kind': 'reverse_allocation', 'funder': 'user',
                       'occurred_on': '2026-11-01'})
    check('reversing the user payment leaves the obligation standing and unfunded',
          model.qualifying(rev2, rules='v2026.1').gross == 1000.00
          and model.state(rev2)['unallocated'] == 1000.00)
    check('so a refund and a reversal of the same amount do not agree',
          after_refund.gross != model.qualifying(rev2, rules='v2026.1').gross)
    check('and money the user no longer has out of pocket is no longer deductible',
          model.qualifying(rev2, rules='v2026.1').confirmed_user_paid == 0.00)

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
        print('  * a payment counts only when cleared AND attached AND user-confirmed;')
        print('    cleared alone is insufficient, because cleared defaults to true')
        print('  * the qualifying figure has THREE parts - confirmed, unresolved, and a')
        print('    total that is UNAVAILABLE while anything is unresolved. The confirmed')
        print('    half is a SUM of evidenced payments, never a subtraction')
        print('  * resolving the unresolved amount must CHANGE the total, and resolving it')
        print('    two different ways must produce two different totals')
        print('  * progress is dollars paid over dollars owed, never a payment count')
        print('\n0 passed, 0 failed — every assertion above is pending a model')
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
