# -*- coding: utf-8 -*-
"""`green_light()` still means what it meant — a product contract, not a return value.

`gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §C3 raised this to P0 ahead of several unbuilt-code
items, with a sharper reason than blast radius. Every other P0 item is new functionality that
is currently wrong, which is a development problem. This is **existing functionality whose
meaning would change underneath existing users**, which is a product-integrity problem, on a
line whose whole promise is stability.

    existing user + no healthcare information + same historical financial state
            -> the same green_light result

The corpus and the recorded answers live in `tests/green_light_contract.py` and
`tests/green_light_contract.json`. This section recomputes them and fails on any difference,
including a difference nobody thought to write a check for — which is the point, since the
change this is waiting for (a healthcare reserve reaching `green_light`) has not been designed
yet.

**And it proves it can fail.** A frozen baseline that silently stops comparing is worse than
no baseline, because it reports safety it is not providing. So the section perturbs the
function in memory and requires the comparison to notice, then asserts the perturbation was
undone.
"""
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_contract():
    path = BASE / 'tests' / 'green_light_contract.py'
    spec = importlib.util.spec_from_file_location('_gw_green_light_contract', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(ctx):
    check = ctx.check

    try:
        gl = _load_contract()
    except Exception as e:                                    # noqa: BLE001
        check(f'the green_light contract loads ({type(e).__name__}: {e})', False)
        return

    if not gl.BASELINE.exists():
        check('a recorded green_light baseline exists '
              '(run: python tests/green_light_contract.py --record)', False)
        return

    stored = gl.load()
    check('the baseline is versioned and carries its reason',
          bool(stored.get('version')) and bool(stored.get('reason')))
    check('the baseline version matches the code that reads it',
          stored.get('version') == gl.CONTRACT_VERSION)

    # A corpus that drifted to all-None, or all-light, would pass a comparison while
    # testing almost nothing. Both branches have to be represented.
    lit = sum(1 for c in stored['cases'] if c['result'] is not None)
    dark = len(stored['cases']) - lit
    check('the corpus exercises both branches - a light and an honest silence',
          lit > 0 and dark > 0)
    check('the corpus has not shrunk below what was recorded',
          len(stored['cases']) == len(gl.cases()))

    checked, mismatches = gl.compare()
    check('every recorded green_light result is unchanged', not mismatches)
    if mismatches:
        for msg in mismatches[:6]:
            print(f'        CHANGED  {msg}')
        print('        If this change is intentional, bump CONTRACT_VERSION and write')
        print('        CHANGE_REASON in tests/green_light_contract.py, then re-record.')
        print('        If it is not, it is an LTS regression and the change is the bug.')
        return

    # ── The comparison has to be able to fail ───────────────────────────────
    # Three checks in one session once passed while unable to fail for the reason they
    # named, and a frozen baseline is especially prone to it: nothing about a green
    # comparison distinguishes "behaviour is stable" from "the comparison stopped
    # looking". So break the function and require the contract to notice.
    original = gl.green_light

    def shifted(cards, budget, drivers, **kw):
        out = original(cards, budget, drivers, **kw)
        if out is None:
            return None
        return dict(out, freed_monthly=round(out['freed_monthly'] + 0.01, 2))

    gl.green_light = shifted
    try:
        _, perturbed = gl.compare()
    finally:
        gl.green_light = original
    check('a one-cent change in the freed figure is detected', bool(perturbed))

    # A silence turning into a light is the change that would matter most to a user, and
    # it is the shape a healthcare reserve could produce. It must not be absorbed either.
    def never_dark(cards, budget, drivers, **kw):
        out = original(cards, budget, drivers, **kw)
        if out is None:
            return {'freed_monthly': 0.0, 'drivers': [], 'diffuse': False,
                    'driver_count': 0, 'fresh': False, 'months_sooner': 0,
                    'uncredited_monthly': 0.0}
        return out

    gl.green_light = never_dark
    try:
        _, lit_up = gl.compare()
    finally:
        gl.green_light = original
    check('an honest silence turning into a light is detected', bool(lit_up))

    _, after = gl.compare()
    check('the function is left exactly as it was found', not after)
