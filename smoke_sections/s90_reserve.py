# -*- coding: utf-8 -*-
"""The reserve holds its distinctions, and the fixture can still detect it losing them.

`core/reserve.py` implements `gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §5; the assertions live
in `tests/test_reserve_fixture.py`, written before the model.

Two claims kept apart, as in s65, s75, s80 and s85.

The mutations are the shorter code in every case. Storing the target's figure instead of
resolving it, reporting one balance instead of two, treating every target change as the same
kind of change — each is what a reasonable person writes first, and each produces a sentence
about someone's money that is not true.
"""
import io
import contextlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_fixture():
    path = BASE / 'tests' / 'test_reserve_fixture.py'
    spec = importlib.util.spec_from_file_location('_gw_reserve_fixture', path)
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
    def target_keeps_a_copy():
        # The shortcut that creates a second source of truth: store the figure at the moment
        # the target is set. It agrees with the plan right up until the plan is corrected.
        orig = m.set_target
        seen = {}

        def broken(basis=None, amount=None, source=None, reason=None, kind=None):
            t = orig(basis, amount, source, reason, kind)
            if basis == 'oop_max':
                seen['copy'] = 6000.00
                t.amount = 6000.00
            return t
        orig_amount = m.target_amount

        def broken_amount(oop_max=None, historical=None):
            t = m.current_target()
            if t is not None and t.basis == 'oop_max' and t.amount is not None:
                return t.amount
            return orig_amount(oop_max=oop_max, historical=historical)
        m.set_target, m.target_amount = broken, broken_amount

        def undo():
            m.set_target, m.target_amount = orig, orig_amount
        return undo

    def unknown_target_is_zero():
        orig = m.target_amount

        def broken(oop_max=None, historical=None):
            out = orig(oop_max=oop_max, historical=historical)
            return 0.00 if out is m.UNKNOWN else out
        m.target_amount = broken
        return lambda: setattr(m, 'target_amount', orig)

    def balance_is_modified():
        # The rule broken head on: report the balance net of the allocation, so the
        # historian would go on to disagree with the account.
        orig = m.snapshot

        def broken(balance=None, as_of=None, oop_max=None, historical=None):
            out = orig(balance, as_of, oop_max, historical)
            if out['balance'] is not None:
                out['balance'] = out['available']
            return out
        m.snapshot = broken
        return lambda: setattr(m, 'snapshot', orig)

    def allocations_accumulate():
        # A contribution ledger instead of an allocation: $500 then $700 becomes $1,200.
        orig = m.reserved

        def broken(as_of=None):
            rows = m._r().allocations
            if as_of is not None:
                rows = [a for a in rows if not a.as_of or a.as_of <= as_of]
            return round(sum(a.amount for a in rows), 2)
        m.reserved = broken
        return lambda: setattr(m, 'reserved', orig)

    def available_is_clamped():
        orig = m.available

        def broken(balance, as_of=None):
            out = orig(balance, as_of)
            return out if out is m.UNKNOWN else max(0.0, out)
        m.available = broken
        return lambda: setattr(m, 'available', orig)

    def as_of_ignored():
        orig = m.reserved
        m.reserved = lambda as_of=None: orig()
        return lambda: setattr(m, 'reserved', orig)

    def shortfall_against_the_balance():
        # Section 5's failure sentence: a household with money in the account reads as
        # part-way to a target it has set nothing aside for.
        orig = m.snapshot

        def broken(balance=None, as_of=None, oop_max=None, historical=None):
            out = orig(balance, as_of, oop_max, historical)
            if out['shortfall'] is not m.UNKNOWN and out['balance'] is not None:
                out['shortfall'] = round(max(0.0, out['target'] - out['balance']), 2)
            return out
        m.snapshot = broken
        return lambda: setattr(m, 'snapshot', orig)

    def missing_balance_is_zero():
        orig = m.available
        m.available = lambda balance, as_of=None: (0.0 if balance is None
                                                   else orig(balance, as_of))
        return lambda: setattr(m, 'available', orig)

    def allocations_overwritten():
        orig = m.allocations
        m.allocations = lambda: orig()[-1:]
        return lambda: setattr(m, 'allocations', orig)

    def missing_target_means_funded():
        orig = m.snapshot

        def broken(balance=None, as_of=None, oop_max=None, historical=None):
            out = orig(balance, as_of, oop_max, historical)
            if out['shortfall'] is m.UNKNOWN:
                out['shortfall'] = 0.00
            return out
        m.snapshot = broken
        return lambda: setattr(m, 'snapshot', orig)

    def every_change_is_a_preference():
        orig = m.set_target

        def broken(basis=None, amount=None, source=None, reason=None, kind=None):
            t = orig(basis, amount, source, reason, kind)
            if t.kind != 'initial':
                t.kind = 'preference'
            return t
        m.set_target = broken
        return lambda: setattr(m, 'set_target', orig)

    def targets_overwritten():
        orig = m.target_history
        m.target_history = lambda: orig()[-1:]
        return lambda: setattr(m, 'target_history', orig)

    def source_not_recorded():
        orig = m.set_target
        m.set_target = lambda basis=None, amount=None, source=None, reason=None, kind=None: \
            orig(basis, amount, None, reason, kind)
        return lambda: setattr(m, 'set_target', orig)

    def clearing_deletes_the_allocation():
        orig = m.clear_target

        def broken():
            m._r().allocations = []
            return orig()
        m.clear_target = broken
        return lambda: setattr(m, 'clear_target', orig)

    return [
        ('a derived target keeps a copy of the figure', target_keeps_a_copy),
        ('a target nobody can resolve becomes zero', unknown_target_is_zero),
        ('the reported balance is net of the allocation', balance_is_modified),
        ('allocations accumulate instead of superseding', allocations_accumulate),
        ('an over-allocation is clamped to zero', available_is_clamped),
        ('the allocation in force is always the latest, whatever the date', as_of_ignored),
        ('the shortfall is measured against the balance', shortfall_against_the_balance),
        ('a balance nobody supplied is treated as zero', missing_balance_is_zero),
        ('only the latest allocation survives', allocations_overwritten),
        ('no target at all reads as fully funded', missing_target_means_funded),
        ('every target change is recorded as a preference', every_change_is_a_preference),
        ('only the latest target survives', targets_overwritten),
        ('a target change records no source', source_not_recorded),
        ('clearing the target deletes the allocation', clearing_deletes_the_allocation),
    ]


def run(ctx):
    check = ctx.check

    try:
        from core import reserve as model
    except Exception as e:                                    # noqa: BLE001
        check(f'core/reserve.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/reserve.py imports', True)

    try:
        fx = _load_fixture()
    except Exception as e:                                    # noqa: BLE001
        check(f'the reserve fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, model)
    check('the reserve fixture passes in full', not failures and not err and passed > 0)
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
