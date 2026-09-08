# -*- coding: utf-8 -*-
"""Payment state stays coherent, and the fixture can still detect it not being.

`core/payment_plan.py`; assertions in `tests/test_payment_state_fixture.py`, written before
the model.

**The boundary question, answered.** Rob's follow-up was whether the invariant is enforced at
the ledger boundary or merely reconstructed by each consumer — the "material exists, invariant
doesn't" shape of gap 4. It is at the boundary: `payment_state()` computes all five dimensions
**together in one pass**, and there is deliberately no `paid()` or `ahead()` accessor for a
consumer to call separately. The mutation that splits them apart is the first one below.

The other one that matters is silently absorbing an over-reversal. Arithmetic can always add a
negative number; the question is whether the ledger still records *which payment stopped being
true*, and a model that absorbs a $700 reversal of a $500 payment has lost that permanently.
"""
import io
import contextlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_fixture():
    path = BASE / 'tests' / 'test_payment_state_fixture.py'
    spec = importlib.util.spec_from_file_location('_gw_payment_fixture', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_fixture(fx, model):
    fx.PASS[:] = []
    fx.FAIL[:] = []
    fx.PENDING[:] = []
    err = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            fx.run(model)
    except Exception as e:                                    # noqa: BLE001
        err = '%s: %s' % (type(e).__name__, e)
    # PENDING counts as not-passing; see s65 for why.
    return len(fx.PASS), list(fx.FAIL) + list(fx.PENDING), err


def _mutations(m):
    def dimensions_drift_apart():
        # The gap-4 shape: each dimension computed independently, so they can disagree.
        # Here `ahead` is recomputed from a stale expectation while `paid` is current.
        orig = m.payment_state

        def broken(plan, as_of=None):
            st = orig(plan, as_of)
            st['ahead'] = round(st['paid'] - (st['expected_by_now'] - 50.0), 2)
            return st
        m.payment_state = broken
        return lambda: setattr(m, 'payment_state', orig)

    def over_reversal_absorbed():
        orig = m.reverse_payment

        def broken(plan, payment, amount=None, on=None, reason=None):
            want = round(float(payment.amount if amount is None else amount), 2)
            e = m.Entry(kind='reversal', amount=-want, on=on, reverses=payment,
                        recorded_at=m._now())
            plan.entries.append(e)
            return e
        m.reverse_payment = broken
        return lambda: setattr(m, 'reverse_payment', orig)

    def reversal_forgets_its_target():
        orig = m.reverse_payment

        def broken(plan, payment, amount=None, on=None, reason=None):
            out = orig(plan, payment, amount, on, reason)
            if out is not m.REFUSED:
                out.reverses = None
            return out
        m.reverse_payment = broken
        return lambda: setattr(m, 'reverse_payment', orig)

    def behind_is_negative_ahead():
        orig = m.payment_state

        def broken(plan, as_of=None):
            st = orig(plan, as_of)
            if st['overdue'] > 0:
                st['ahead'] = -st['overdue']
                st['overdue'] = 0.00
            return st
        m.payment_state = broken
        return lambda: setattr(m, 'payment_state', orig)

    def adjustment_moves_paid():
        # Collapsing the two meanings of a negative number: an adjustment treated as a
        # payment reversal, so what is owed and what was paid become the same lever.
        orig = m.ledger
        m.ledger = lambda plan, as_of=None: (
            orig(plan, as_of)
            + [e for e in plan.entries if e.kind == 'adjustment'
               and (as_of is None or not e.on or e.on <= as_of)])
        return lambda: setattr(m, 'ledger', orig)

    def refusal_absorbed_silently():
        orig = m.reverse_payment

        def broken(plan, payment, amount=None, on=None, reason=None):
            out = orig(plan, payment, amount, on, reason)
            return None if out is m.REFUSED else out
        m.reverse_payment = broken
        return lambda: setattr(m, 'reverse_payment', orig)

    def refusal_says_nothing():
        orig = m.last_refusal
        m.last_refusal = lambda plan: {}
        return lambda: setattr(m, 'last_refusal', orig)

    def expectation_exceeds_the_agreement():
        # An agreement cannot expect more than it contains; without the cap a long-running
        # plan reports an overdue that the contract never asked for.
        orig = m._instalments_due
        m._instalments_due = lambda plan, as_of: (orig(plan, as_of) + 4)
        return lambda: setattr(m, '_instalments_due', orig)

    def incoherence_check_always_clean():
        orig = m.incoherences
        m.incoherences = lambda plan, as_of=None: []
        return lambda: setattr(m, 'incoherences', orig)

    return [
        ('the five dimensions are computed separately and drift apart',
         dimensions_drift_apart),
        ('an over-reversal is absorbed instead of refused', over_reversal_absorbed),
        ('a reversal does not name the payment it reversed', reversal_forgets_its_target),
        ('falling behind is reported as negative ahead', behind_is_negative_ahead),
        ('an adjustment moves paid, collapsing it with a reversal', adjustment_moves_paid),
        ('a refusal is returned as None, indistinguishable from doing nothing',
         refusal_absorbed_silently),
        ('a refusal explains nothing', refusal_says_nothing),
        ('the schedule expects more instalments than the agreement contains',
         expectation_exceeds_the_agreement),
        ('the coherence check always reports clean', incoherence_check_always_clean),
    ]


def run(ctx):
    check = ctx.check

    try:
        from core import payment_plan as model
    except Exception as e:                                    # noqa: BLE001
        check(f'core/payment_plan.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/payment_plan.py imports', True)

    check('there is no single-dimension accessor for a consumer to drift with',
          not hasattr(model, 'paid') and not hasattr(model, 'ahead')
          and not hasattr(model, 'overdue'))

    try:
        fx = _load_fixture()
    except Exception as e:                                    # noqa: BLE001
        check(f'the payment-state fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, model)
    check('the payment-state fixture passes in full',
          not failures and not err and passed > 0)
    if failures or err:
        for f in failures[:6]:
            print(f'        failing: {f}')
        if err:
            print(f'        raised: {err}')
        check('mutation detection is meaningful (baseline green)', False)
        return

    for name, make in _mutations(model):
        undo = make()
        try:
            _, mutated, mutated_err = _run_fixture(fx, model)
        finally:
            undo()
        check('caught: ' + name, bool(mutated) or bool(mutated_err))

    restored, restored_failures, restored_err = _run_fixture(fx, model)
    check('the module is left exactly as it was found',
          restored == passed and not restored_failures and not restored_err)
