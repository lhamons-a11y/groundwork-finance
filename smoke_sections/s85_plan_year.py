# -*- coding: utf-8 -*-
"""Plan-year state holds, and the fixture can still detect it not holding.

`core/plan_year.py` implements `gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §4; the assertions
live in `tests/test_plan_year_fixture.py`, written before the model.

Two claims kept apart, as in s65, s75 and s80: the fixture passing says the model satisfies the
specification, every mutation being caught says the specification is enforced.

The mutations are the plausible implementations. A stored accumulator, a `current_plan` field,
a correction written over the old terms, `deductible_met = False` when no plan is on file —
each is the shorter code, and each tells someone something untrue about their coverage.
"""
import io
import contextlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_fixture():
    path = BASE / 'tests' / 'test_plan_year_fixture.py'
    spec = importlib.util.spec_from_file_location('_gw_plan_year_fixture', path)
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
    def period_ignored():
        orig = m._in_period
        m._in_period = lambda plan, when: True
        return lambda: setattr(m, '_in_period', orig)

    def terms_as_of_ignored():
        orig = m.terms_at
        m.terms_at = lambda plan, as_of=None: orig(plan)
        return lambda: setattr(m, 'terms_at', orig)

    def as_of_ignored_everywhere():
        # Both as-of paths, because they are redundant by construction here: a plan and its
        # first terms are written in the same breath, so hiding one still hides the other and
        # the answer stays right. Breaking only `plans` is not the defect it looks like - it
        # is a mutation the model survives, which is a different thing from one it catches.
        orig_plans, orig_terms = m.plans, m.terms_at
        m.plans = lambda as_of=None: orig_plans()
        m.terms_at = lambda plan, as_of=None: orig_terms(plan)

        def undo():
            m.plans = orig_plans
            m.terms_at = orig_terms
        return undo

    def correction_overwrites():
        orig = m.correct_terms

        def broken(plan, reason=None, source=None, **new_terms):
            out = orig(plan, reason, source, **new_terms)
            reg = m._r()
            reg.terms = [t for t in reg.terms
                         if t.plan_id != plan.id or t is out]
            return out
        m.correct_terms = broken
        return lambda: setattr(m, 'correct_terms', orig)

    def correction_looks_like_a_change():
        orig = m.correct_terms

        def broken(plan, reason=None, source=None, **new_terms):
            out = orig(plan, reason, source, **new_terms)
            for op in m._r().ops:
                if op.kind == 'correction':
                    op.kind = 'change'
            return out
        m.correct_terms = broken
        return lambda: setattr(m, 'correct_terms', orig)

    def change_looks_like_a_correction():
        orig = m.add_plan

        def broken(**kw):
            p = orig(**kw)
            m._r().ops[-1].kind = 'correction'
            return p
        m.add_plan = broken
        return lambda: setattr(m, 'add_plan', orig)

    def previous_not_recorded():
        orig = m.correct_terms

        def broken(plan, reason=None, source=None, **new_terms):
            out = orig(plan, reason, source, **new_terms)
            out.previous = None
            return out
        m.correct_terms = broken
        return lambda: setattr(m, 'correct_terms', orig)

    def source_not_recorded():
        orig = m.correct_terms
        m.correct_terms = lambda plan, reason=None, source=None, **kw: orig(plan, reason,
                                                                           None, **kw)
        return lambda: setattr(m, 'correct_terms', orig)

    def unsupplied_terms_become_zero():
        # The shipped state before the quarantine repair: add_plan defaulted the deductible to
        # 0.0, so a plan entered before its terms were known read `met = True`. The most
        # mundane false sentence in the module, and the one the fixture could not see because
        # the UNKNOWN branch was unreachable through the API.
        orig = m.add_plan

        def broken(name=None, deductible=None, oop_max=None, effective_from=None,
                   effective_to=None):
            return orig(name=name,
                        deductible=0.0 if deductible is None else deductible,
                        oop_max=0.0 if oop_max is None else oop_max,
                        effective_from=effective_from, effective_to=effective_to)
        m.add_plan = broken
        return lambda: setattr(m, 'add_plan', orig)

    def unknown_becomes_false():
        orig = m.year_summary

        def broken(expenses, year, as_of=None):
            out = orig(expenses, year, as_of)
            if out['deductible_met'] is m.UNKNOWN:
                out['deductible_met'] = False
            return out
        m.year_summary = broken
        return lambda: setattr(m, 'year_summary', orig)

    def unattributed_absorbed():
        orig = m.year_summary

        def broken(expenses, year, as_of=None):
            out = orig(expenses, year, as_of)
            out['unattributed'] = 0.00
            return out
        m.year_summary = broken
        return lambda: setattr(m, 'year_summary', orig)

    def oop_follows_the_deductible():
        orig = m.accumulators

        def broken(expenses, plan, as_of=None):
            out = orig(expenses, plan, as_of)
            out['oop_max'] = out['deductible']
            out['oop_met'] = out['deductible_met']
            return out
        m.accumulators = broken
        return lambda: setattr(m, 'accumulators', orig)

    def delete_ignores_history():
        orig = m.delete_plan

        def broken(plan, expenses=None):
            reg = m._r()
            reg.plans = [p for p in reg.plans if p.id != plan.id]
            return True
        m.delete_plan = broken
        return lambda: setattr(m, 'delete_plan', orig)

    def rollover_exists():
        def rollover(to_year):
            return to_year
        m.rollover = rollover
        return lambda: delattr(m, 'rollover')

    def overlap_resolved_by_position():
        # The shipped behaviour before HAZARD_AUDIT H1: first inserted plan wins when two
        # periods contain the date. Position is not evidence; this must be caught.
        orig = m.plan_at

        def broken(when, as_of=None):
            for p in m.plans(as_of):
                if m._in_period(p, when):
                    return p
            return None
        m.plan_at = broken
        return lambda: setattr(m, 'plan_at', orig)

    def overlap_applied_to_both():
        # The other half of H1: `accumulators` summing the full amount against every plan
        # whose period contains the expense - a double count under concurrent coverage.
        orig = m.accumulators

        def broken(expenses, plan, as_of=None):
            terms = m.terms_at(plan, as_of)
            applied = round(sum(e['amount'] for e in (expenses or {}).values()
                                if m._in_period(plan, e.get('date'))), 2)
            d, o = terms.get('deductible'), terms.get('oop_max')
            return {'plan': plan.name, 'applied': applied, 'deductible': d,
                    'deductible_met': (m.UNKNOWN if d is None else applied >= d),
                    'oop_applied': applied, 'oop_max': o,
                    'oop_met': (m.UNKNOWN if o is None else applied >= o)}
        m.accumulators = broken
        return lambda: setattr(m, 'accumulators', orig)

    return [
        ('overlapping periods are resolved by insertion order', overlap_resolved_by_position),
        ('an expense in two periods is applied in full to both', overlap_applied_to_both),
        ('the plan period is ignored, so every expense counts everywhere', period_ignored),
        ('a terms correction rewrites history with no way back', terms_as_of_ignored),
        ('the record cannot be read as it stood - as-of is ignored throughout',
         as_of_ignored_everywhere),
        ('a correction overwrites the prior terms', correction_overwrites),
        ('a correction is recorded as a plan change', correction_looks_like_a_change),
        ('adding a plan is recorded as a correction to the old one',
         change_looks_like_a_correction),
        ('a correction records no previous value', previous_not_recorded),
        ('a correction records no source', source_not_recorded),
        ('not knowing the plan becomes "deductible not met"', unknown_becomes_false),
        ('not knowing the deductible becomes "deductible met" - a zero nobody entered',
         unsupplied_terms_become_zero),
        ('spending under no plan is absorbed rather than reported', unattributed_absorbed),
        ('out-of-pocket is derived from the deductible', oop_follows_the_deductible),
        ('deleting a plan with expenses under it is allowed', delete_ignores_history),
        ('a rollover operation exists, so something has to remember to reset',
         rollover_exists),
    ]


def run(ctx):
    check = ctx.check

    try:
        from core import plan_year as model
    except Exception as e:                                    # noqa: BLE001
        check(f'core/plan_year.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/plan_year.py imports', True)

    try:
        fx = _load_fixture()
    except Exception as e:                                    # noqa: BLE001
        check(f'the plan-year fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, model)
    check('the plan-year fixture passes in full',
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
