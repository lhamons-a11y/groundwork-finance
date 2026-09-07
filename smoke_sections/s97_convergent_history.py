# -*- coding: utf-8 -*-
"""Two histories reaching one balance stay distinguishable, and the fixture can prove it.

`core/allocation.py`'s retraction and replacement; assertions in
`tests/test_convergent_history_fixture.py`, written before the mechanism — and it exposed one
immediately, because history B was not representable at all: the model could express a
correction and could not express a retraction.

The mutation that matters most is **collapsing a retraction into a correction**. Both end owing
$275, so a model that treats them as the same thing looks right on every balance — and then a
payment attached to the retracted bill silently funds its replacement, which makes $275 appear
satisfied by money attached to an obligation nobody owes.

The second is **netting the retracted bill's payment away**. Money against a zero obligation is
an uncomfortable state, and hiding it is the tempting thing to do; it is also the state a user
most needs to be shown, because it is their money sitting against a bill that no longer exists.
"""
import io
import contextlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_fixture():
    path = BASE / 'tests' / 'test_convergent_history_fixture.py'
    spec = importlib.util.spec_from_file_location('_gw_convergent_fixture', path)
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
    def retraction_is_a_correction():
        # The collapse this whole fixture exists to prevent.
        orig = m.history_kind
        m.history_kind = lambda e: ('corrected' if orig(e) in ('retracted', 'replacement')
                                    else orig(e))
        return lambda: setattr(m, 'history_kind', orig)

    def equivalent_when_balances_agree():
        orig = m.histories_equivalent
        m.histories_equivalent = lambda a, b: m.state(a)['expense'] == m.state(b)['expense']
        return lambda: setattr(m, 'histories_equivalent', orig)

    def void_still_owes():
        orig = m._fold

        def broken(e):
            f = orig(e)
            f['voided'] = None
            return f
        m._fold = broken
        return lambda: setattr(m, '_fold', orig)

    def payment_follows_the_replacement():
        # A payment on the retracted bill funding its replacement: the balance looks right
        # and $275 has been satisfied by money attached to an obligation nobody owes.
        orig = m.state

        def broken(e, plan=m.UNRESOLVED):
            out = orig(e, plan)
            prior = m.replaces(e)
            if prior is not None:
                paid = sum(v for k, v in orig(prior).items() if k == 'user')
                out['unallocated'] = round(out['unallocated'] - paid, 2)
            return out
        m.state = broken
        return lambda: setattr(m, 'state', orig)

    def negative_is_netted_away():
        orig = m.state

        def broken(e, plan=m.UNRESOLVED):
            out = orig(e, plan)
            if out['unallocated'] < 0:
                out['unallocated'] = 0.00
            return out
        m.state = broken
        return lambda: setattr(m, 'state', orig)

    def void_counted_in_totals():
        orig = m.household_obligations
        m.household_obligations = lambda expenses: list(expenses)
        return lambda: setattr(m, 'household_obligations', orig)

    def replacement_link_one_way():
        orig = m.link_replacement

        def broken(old, new):
            out = orig(old, new)
            new.replaces_ref = None
            return out
        m.link_replacement = broken
        return lambda: setattr(m, 'link_replacement', orig)

    def void_forgets_why():
        orig = m._fold

        def broken(e):
            f = orig(e)
            if f['voided']:
                f['voided'] = dict(f['voided'], reason=None, occurred_on=None)
            return f
        m._fold = broken
        return lambda: setattr(m, '_fold', orig)

    def difference_unnameable():
        orig = m.history_difference
        m.history_difference = lambda a, b: None
        return lambda: setattr(m, 'history_difference', orig)

    return [
        ('a retraction is reported as a correction', retraction_is_a_correction),
        ('histories are equivalent when their balances agree',
         equivalent_when_balances_agree),
        ('a voided obligation still owes what it owed', void_still_owes),
        ('a payment on the retracted bill funds its replacement',
         payment_follows_the_replacement),
        ('money against a zero obligation is netted away', negative_is_netted_away),
        ('a retracted obligation is counted in household totals', void_counted_in_totals),
        ('the replacement does not know what it replaced', replacement_link_one_way),
        ('a retraction records no reason or date', void_forgets_why),
        ('the difference between two histories cannot be named', difference_unnameable),
    ]


def run(ctx):
    check = ctx.check

    try:
        from core import allocation as model
        model.void_obligation_supported
    except Exception as e:                                    # noqa: BLE001
        check(f'core/allocation.py can express a retraction ({type(e).__name__}: {e})', False)
        return
    check('core/allocation.py can express a retraction', True)

    try:
        fx = _load_fixture()
    except Exception as e:                                    # noqa: BLE001
        check(f'the convergent-history fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, model)
    check('the convergent-history fixture passes in full',
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
