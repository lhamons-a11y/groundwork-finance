# -*- coding: utf-8 -*-
"""The weakest-link rule holds, and the fixture can still detect it not holding.

`core/classification.py`'s evidence-strength layer; assertions in
`tests/test_evidence_strength_fixture.py`, written before the rule.

The mutation that matters most is the first: **strength taken as the maximum rather than the
minimum over sources.** That is inference amplification in one line — three algorithms agreeing
turning *maybe healthcare → maybe claim → maybe responsibility* into a confident number — and it
is the shorter, more natural thing to write.

**One mutation is deliberately absent.** Freezing strength at derive time rather than computing
it on read is *unobservable here*, because classifications are immutable: recording contradicting
evidence returns a new object, so a fact's sources never change underneath it and the two
implementations agree always. That is a mutation the model **survives** for a structural reason,
which is a different thing from one it fails to catch — and asserting it would be asserting
nothing.

The second most important is `consume` failing **open**. A consumer that never declared what
strength it requires taking a value anyway is the difference between walkable provenance and
enforced provenance: the information would still be there, and nothing would be using it.
"""
import io
import contextlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_fixture():
    path = BASE / 'tests' / 'test_evidence_strength_fixture.py'
    spec = importlib.util.spec_from_file_location('_gw_strength_fixture', path)
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
    def amplification():
        # THE defect this rule exists to prevent: strongest source wins, so a chain of weak
        # inferences ends in a confident number because something upstream was solid.
        orig = m.strength_of

        def broken(fact):
            src = getattr(fact, 'sources', None)
            if src is None:
                return orig(fact)
            material = [x for x in src if m._is_material(x)]
            if not material:
                return m.NOT_EVALUATED
            return sorted(material, key=lambda x: m._RANK[orig(x)])[-1] and orig(
                sorted(material, key=lambda x: m._RANK[orig(x)])[-1])
        m.strength_of = broken
        return lambda: setattr(m, 'strength_of', orig)

    def floor_collapses():
        # `contradicted` reported as `not_evaluated`: the two share a rank, and merging them
        # throws away the only thing that was actually established.
        orig = m.strength_of
        m.strength_of = lambda fact: (m.NOT_EVALUATED if orig(fact) == m.CONTRADICTED
                                      else orig(fact))
        return lambda: setattr(m, 'strength_of', orig)

    def consume_ignores_strength():
        orig = m.consume
        m.consume = lambda fact, by=None: fact.value
        return lambda: setattr(m, 'consume', orig)

    def undeclared_consumer_allowed():
        # Fails OPEN. The rule becomes a convention that a new surface can skip by not
        # appearing in the table - which is exactly what "walkable, not enforced" means.
        orig = m.refusal

        def broken(fact, by=None):
            if m.required_strength(by) is None:
                return None
            return orig(fact, by)
        m.refusal = broken
        return lambda: setattr(m, 'refusal', orig)

    def immaterial_sources_count():
        orig = m._is_material
        m._is_material = lambda source: True
        return lambda: setattr(m, '_is_material', orig)

    def manufactured_lost():
        orig = m.derive

        def broken(metric, value, sources=()):
            out = orig(metric, value, sources)
            return m.replace(out, sensitivity=m.Sensitivity(
                domain=out.sensitivity.domain, manufactured=False))
        m.derive = broken
        return lambda: setattr(m, 'derive', orig)

    def refusal_says_nothing():
        orig = m.refusal
        m.refusal = lambda fact, by=None: ({} if orig(fact, by) is not None else None)
        return lambda: setattr(m, 'refusal', orig)

    return [
        ('strength is the strongest source, not the weakest', amplification),
        ('contradicted is reported as not_evaluated at the floor', floor_collapses),
        ('consume returns the value whatever the strength', consume_ignores_strength),
        ('an undeclared consumer is allowed through - the rule fails open',
         undeclared_consumer_allowed),
        ('sources contributing nothing still drag the strength down',
         immaterial_sources_count),
        ('manufactured is lost when a fact is derived', manufactured_lost),
        ('a refusal explains nothing', refusal_says_nothing),
    ]


def run(ctx):
    check = ctx.check

    try:
        from core import classification as model
        model.strength_of
    except Exception as e:                                    # noqa: BLE001
        check(f'the evidence-strength layer imports ({type(e).__name__}: {e})', False)
        return
    check('core/classification.py carries an evidence-strength layer', True)

    try:
        fx = _load_fixture()
    except Exception as e:                                    # noqa: BLE001
        check(f'the evidence-strength fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, model)
    check('the evidence-strength fixture passes in full',
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
