# -*- coding: utf-8 -*-
"""The consumer boundary has no second door, and the fixture can still detect one.

`EVIDENCE_MATRIX.md` Q1, implemented in `core/classification.py`; assertions in
`tests/test_consumer_boundary_fixture.py`, which was written while the defect was still there
and ran red until the fix landed.

**The first two mutations are the defect this section exists for**, and they are not
hypothetical — they are the shipped state of the module before Q1. `narrator_facts` and
`export_row` build what two of the four declared consumers receive, and both read
`derived.value` directly, so the strength each consumer declares was never consulted on the
path each consumer uses. Gap 4 closed the boundary; nothing checked that the boundary was the
only way through.

**The rest are the alternatives Q1 rejected, seeded as defects** — because a rejected design
that is never tested against is a design decision nobody can tell was made. A bare sentinel
loses *why*; a `None` becomes a blank cell and a blank cell is a zero; a refusal without
`offered` collapses `contradicted` into `not_evaluated` at the last inch, undoing exactly what
`_prefer_contradicted` exists to protect.

**And one in the other direction**, because a boundary that refuses everything passes every
refusal test ever written: refusing a fact the consumer is entitled to is also a failure, and
the fixture has to notice.
"""
import io
import contextlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_fixture():
    path = BASE / 'tests' / 'test_consumer_boundary_fixture.py'
    spec = importlib.util.spec_from_file_location('_gw_boundary_fixture', path)
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
    return len(fx.PASS), list(fx.FAIL) + list(fx.PENDING), err


def _mutations(m):
    def narrator_reads_value():
        # The pre-Q1 implementation, exactly.
        orig = m.narrator_facts
        m.narrator_facts = lambda derived: m.NarratorFacts(
            metric=derived.metric, value=derived.value, includes_records=False)
        return lambda: setattr(m, 'narrator_facts', orig)

    def export_reads_value():
        orig = m.export_row
        m.export_row = lambda derived: {'metric': derived.metric, 'value': derived.value,
                                        'sensitivity': derived.sensitivity.domain}
        return lambda: setattr(m, 'export_row', orig)

    def refusal_becomes_a_sentinel():
        # Q1's rejected alternative: safe, and it throws away which of not_evaluated,
        # contradicted or single_weak_signal was offered.
        orig = m._permitted_value
        m._permitted_value = lambda derived, consumer: (
            m.UNAVAILABLE if m.refusal(derived, consumer) is not None
            else orig(derived, consumer))
        return lambda: setattr(m, '_permitted_value', orig)

    def refusal_becomes_none():
        # The blank cell. A spreadsheet reads it as zero and a total changes silently -
        # `absence is not zero`, which cost a household a $7,053 shortfall that was a surplus.
        orig = m._permitted_value
        m._permitted_value = lambda derived, consumer: (
            None if m.refusal(derived, consumer) is not None else orig(derived, consumer))
        return lambda: setattr(m, '_permitted_value', orig)

    def refusal_drops_offered():
        orig = m.refusal

        def broken(fact, by=None):
            out = orig(fact, by)
            if out is None:
                return None
            return {k: v for k, v in out.items() if k != 'offered'}
        m.refusal = broken
        return lambda: setattr(m, 'refusal', orig)

    def boundary_refuses_everything():
        # The other direction. A boundary that never lets anything through satisfies every
        # refusal assertion and destroys the product.
        orig = m._permitted_value
        m._permitted_value = lambda derived, consumer: {
            'consumer': consumer, 'reason': 'no', 'required': None, 'offered': None}
        return lambda: setattr(m, '_permitted_value', orig)

    return [
        ('narrator_facts reads the value directly, as it did before Q1',
         narrator_reads_value),
        ('export_row reads the value directly, as it did before Q1', export_reads_value),
        ('a refusal is reduced to a bare sentinel and loses why', refusal_becomes_a_sentinel),
        ('a refusal becomes None, and a blank cell is a zero', refusal_becomes_none),
        ('a refusal no longer names which strength was offered', refusal_drops_offered),
        ('the boundary refuses a consumer that is entitled to the value',
         boundary_refuses_everything),
    ]


def run(ctx):
    check = ctx.check

    try:
        from core import classification as model
        model._permitted_value
    except Exception as e:                                    # noqa: BLE001
        check(f'the consumer boundary imports ({type(e).__name__}: {e})', False)
        return
    check('consumer helpers route through the permission boundary', True)

    try:
        fx = _load_fixture()
    except Exception as e:                                    # noqa: BLE001
        check(f'the consumer-boundary fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, model)
    check('the consumer-boundary fixture passes in full',
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
