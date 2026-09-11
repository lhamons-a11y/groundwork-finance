# -*- coding: utf-8 -*-
"""The resolution projection reads the chain faithfully, and the fixture can tell when it stops.

`core/classification.py`'s `resolution()`; assertions in
`tests/test_resolution_projection_fixture.py`, written before the projection existed. Every
mutation below is checked against **all 5,460 histories** of length 1-6, not the seven table
rows - the enumeration runs in half a second, and a nine-case probe is what let the resolver
bug through in the first place.

**The first mutation is that bug, exactly.** Resolver taken as the LAST knowing event rather
than the first event after the last disagreement. It agrees with the correct definition on 58%
of histories, which is why a hand-picked fixture passed it and an enumeration did not.

**The second is the off-by-one Rob's table contained.** `post` including the resolver itself.
The resolver is the event that establishes the current conclusion; `post` is strictly after it.

**Three are the ways a projection quietly becomes a second evidence evaluator** - the thing Q2
forbids: demoting strength for a resolved conflict, carrying a strength of its own, or
returning something derived from the value rather than the chain.

**One pending assertion is expected and tracked by name.** Multi-source resolution semantics
are unspecified in Q2, deliberately. The section fails if that assertion ever silently passes
- someone specified it without saying so - and fails if any *other* assertion pends.
"""
import io
import contextlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

EXPECTED_PENDING = {'a fact over several sources: resolution semantics are UNSPECIFIED here'}


def _load_fixture():
    path = BASE / 'tests' / 'test_resolution_projection_fixture.py'
    spec = importlib.util.spec_from_file_location('_gw_resolution_fixture', path)
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
            fx.run(model, exhaustive=True)
    except Exception as e:                                    # noqa: BLE001
        err = '%s: %s' % (type(e).__name__, e)
    unexpected_pending = [p for p in fx.PENDING if p not in EXPECTED_PENDING]
    missing_pending = [p for p in EXPECTED_PENDING if p not in fx.PENDING]
    return (len(fx.PASS), list(fx.FAIL) + unexpected_pending + missing_pending, err)


def _mutations(m):
    def _knowing(c, axis):
        return [(e.source, e.supports) for e in m.evidence(c, axis)
                if e.source in m.KNOWING_SOURCES]

    def resolver_is_last_event():
        # The 42% bug. Agrees with the truth on every short, simple history.
        orig = m.resolution

        def broken(c, axis):
            k = _knowing(c, axis)
            if not k:
                return orig(c, axis)
            cur = k[-1][1]
            dis = [i for i, (_, s) in enumerate(k) if s != cur]
            if not dis:
                return orig(c, axis)
            resolver = k[-1][0]
            before = k[:dis[-1]]
            contradictors = {s for s, sup in k if sup != cur}
            if any(s == resolver and sup == cur for s, sup in before):
                kind = m.REAFFIRMATION
            elif resolver in contradictors:
                kind = m.SELF_REVERSAL
            else:
                kind = m.SUPERSEDED
            return {'kind': kind, 'resolver': resolver, 'contradictions': len(dis),
                    'post': ()}
        m.resolution = broken
        return lambda: setattr(m, 'resolution', orig)

    def post_includes_resolver():
        orig = m.resolution

        def broken(c, axis):
            out = dict(orig(c, axis))
            if out['resolver'] is not None:
                out['post'] = (out['resolver'],) + tuple(out['post'])
            return out
        m.resolution = broken
        return lambda: setattr(m, 'resolution', orig)

    def kind_by_ever_not_last():
        # Reaffirmation if the resolver EVER stood for current, rather than by its most
        # recent prior stance. Misclassifies every flip-flop.
        orig = m.resolution

        def broken(c, axis):
            out = dict(orig(c, axis))
            if out['kind'] == m.SELF_REVERSAL:
                k = _knowing(c, axis)
                cur = k[-1][1]
                if any(s == out['resolver'] and sup == cur for s, sup in k[:-1]):
                    out['kind'] = m.REAFFIRMATION
            return out
        m.resolution = broken
        return lambda: setattr(m, 'resolution', orig)

    def contradictions_undercounted():
        orig = m.resolution

        def broken(c, axis):
            out = dict(orig(c, axis))
            if out['contradictions'] > 1:
                out['contradictions'] = 1
            return out
        m.resolution = broken
        return lambda: setattr(m, 'resolution', orig)

    def post_always_empty():
        # The user's concession after being overridden by a document disappears.
        orig = m.resolution
        m.resolution = lambda c, axis: {**orig(c, axis), 'post': ()}
        return lambda: setattr(m, 'resolution', orig)

    def resolution_from_value():
        # A "projection" that never looks at the chain. Constant across H1 and H2.
        orig = m.resolution
        m.resolution = lambda c, axis: {'kind': m.RESOLUTION_NONE, 'resolver': None,
                                        'contradictions': 0, 'post': ()}
        return lambda: setattr(m, 'resolution', orig)

    def narrator_drops_resolution():
        orig = m.narrator_facts
        m.narrator_facts = lambda derived: m.replace(orig(derived), resolution=None)
        return lambda: setattr(m, 'narrator_facts', orig)

    def export_drops_resolution():
        orig = m.export_row

        def broken(derived):
            out = dict(orig(derived))
            out.pop('resolution', None)
            return out
        m.export_row = broken
        return lambda: setattr(m, 'export_row', orig)

    def resolution_demotes_strength():
        # Turning history into a confidence score: a resolved conflict costs a rank.
        orig = m.strength_of

        def broken(fact):
            st = orig(fact)
            src = getattr(fact, 'sources', ())
            if len(src) == 1 and m.resolution(src[0], m.CONTENT)['kind'] != m.RESOLUTION_NONE:
                order = m.STRENGTH
                i = order.index(st)
                return order[max(i - 1, 0)]
            return st
        m.strength_of = broken
        return lambda: setattr(m, 'strength_of', orig)

    def resolution_carries_strength():
        orig = m.resolution
        m.resolution = lambda c, axis: {**orig(c, axis), 'strength': m.strength_of(c)}
        return lambda: setattr(m, 'resolution', orig)

    return [
        ('resolver is the last event, not the one that made the conclusion current',
         resolver_is_last_event),
        ('post includes the resolver itself (the off-by-one)', post_includes_resolver),
        ('reaffirmation decided by "ever stood for", not most recent stance',
         kind_by_ever_not_last),
        ('contradiction count capped at one', contradictions_undercounted),
        ('post is always empty - the concession vanishes', post_always_empty),
        ('resolution is constant, derived from nothing in the chain', resolution_from_value),
        ('narrator_facts drops the resolution', narrator_drops_resolution),
        ('export_row drops the resolution', export_drops_resolution),
        ('a resolved conflict demotes strength - history became confidence',
         resolution_demotes_strength),
        ('the resolution carries a strength of its own', resolution_carries_strength),
    ]


def run(ctx):
    check = ctx.check

    try:
        from core import classification as model
        model.resolution
    except Exception as e:                                    # noqa: BLE001
        check(f'the resolution projection imports ({type(e).__name__}: {e})', False)
        return
    check('core/classification.py carries a read-time resolution projection', True)

    try:
        fx = _load_fixture()
    except Exception as e:                                    # noqa: BLE001
        check(f'the resolution-projection fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, model)
    check('the fixture passes in full, exhaustively, with exactly the one expected pending',
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
