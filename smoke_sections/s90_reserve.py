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

    def held_and_counted_collapse():
        # The one sentence the review exists to prevent: general cash reported as a reserve.
        orig = m.status

        def broken(oop_max=None, general_cash=0.0, historical=None):
            out = orig(oop_max, general_cash, historical)
            out['held'] = round(out['held'] + out['counted'], 2)
            return out
        m.status = broken
        return lambda: setattr(m, 'status', orig)

    def counted_reads_as_segregated():
        orig = m.status

        def broken(oop_max=None, general_cash=0.0, historical=None):
            out = orig(oop_max, general_cash, historical)
            out['segregated'] = (out['held'] + out['counted']) > 0
            return out
        m.status = broken
        return lambda: setattr(m, 'status', orig)

    def shortfall_ignores_general_cash():
        orig = m.status

        def broken(oop_max=None, general_cash=0.0, historical=None):
            out = orig(oop_max, general_cash, historical)
            if out['shortfall'] is not m.UNKNOWN and out['target'] is not m.UNKNOWN:
                out['shortfall'] = round(max(0.0, out['target'] - out['held']), 2)
            return out
        m.status = broken
        return lambda: setattr(m, 'status', orig)

    def missing_target_means_funded():
        orig = m.status

        def broken(oop_max=None, general_cash=0.0, historical=None):
            out = orig(oop_max, general_cash, historical)
            if out['shortfall'] is m.UNKNOWN:
                out['shortfall'] = 0.00
            return out
        m.status = broken
        return lambda: setattr(m, 'status', orig)

    def withdrawal_netted_away():
        orig = m.withdraw

        def broken(amount, on=None, note=None):
            reg = m._r()
            remaining = float(amount)
            for c in list(reg.contributions):
                if remaining <= 0:
                    break
                take = min(c.amount, remaining)
                c.amount = round(c.amount - take, 2)
                remaining = round(remaining - take, 2)
            return None
        m.withdraw = broken
        return lambda: setattr(m, 'withdraw', orig)

    def balance_ignores_withdrawals():
        orig = m.held
        m.held = lambda: round(sum(c.amount for c in m._r().contributions
                                   if c.amount > 0), 2)
        return lambda: setattr(m, 'held', orig)

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

    def clearing_deletes_the_money():
        orig = m.clear_target

        def broken():
            m._r().contributions = []
            return orig()
        m.clear_target = broken
        return lambda: setattr(m, 'clear_target', orig)

    return [
        ('a derived target keeps a copy of the figure', target_keeps_a_copy),
        ('a target nobody can resolve becomes zero', unknown_target_is_zero),
        ('general cash is reported as money held', held_and_counted_collapse),
        ('general cash counts as segregated', counted_reads_as_segregated),
        ('the shortfall ignores the cash that counts toward it',
         shortfall_ignores_general_cash),
        ('no target at all reads as fully funded', missing_target_means_funded),
        ('a withdrawal is netted away instead of recorded', withdrawal_netted_away),
        ('the balance ignores withdrawals', balance_ignores_withdrawals),
        ('every target change is recorded as a preference', every_change_is_a_preference),
        ('only the latest target survives', targets_overwritten),
        ('a target change records no source', source_not_recorded),
        ('clearing the target deletes the money', clearing_deletes_the_money),
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
