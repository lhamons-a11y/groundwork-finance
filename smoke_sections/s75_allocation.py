# -*- coding: utf-8 -*-
"""The obligation model holds, and the fixture can still detect it not holding.

`core/allocation.py` implements `gw 2.0/OBLIGATION_SEMANTICS_QUESTION.md`; the assertions
live in `tests/test_lifecycle_fixture.py`, written before the model against nothing.

Two claims, kept apart for the same reason s65 keeps them apart: the fixture passing says the
model satisfies the specification, every mutation being caught says the specification is
enforced. Only the second survives contact with a change nobody anticipated.

**This section exists because the first mutation run failed.** Three of thirteen mutations
went undetected on 2026-09-07, and two were holes in the fixture rather than in the model —
including its own headline assertion, the arrival-order check, whose corpus of mutations all
commuted, so a model folding events in arrival order passed it. A check that cannot fail for
the reason it names is the defect this project keeps finding, and it was sitting inside the
file written specifically to avoid it.

**What is NOT tested here.** The model is pure and in-memory. `EVENT_SUBSTRATE_QUESTION.md`'s
pre-registered criterion is about persistence — whether `HistorianEntry` can carry this
without relationships living inside `context_json` — and nothing below touches storage. That
experiment is still unrun.
"""
import io
import contextlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_fixture():
    path = BASE / 'tests' / 'test_lifecycle_fixture.py'
    spec = importlib.util.spec_from_file_location('_gw_lifecycle_fixture', path)
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
    # PENDING counts as not-passing. `check` routes a None condition there rather than to
    # FAIL, so an assertion written as an `and` chain can quietly report "pending a model"
    # while the model is right there failing it. Folding pending into the failure signal is
    # the fix that does not depend on every future assertion remembering bool().
    return len(fx.PASS), list(fx.FAIL) + list(fx.PENDING), err


def _mutations(m):
    def arrival_order():
        orig = m._fold

        def broken(e):
            e2 = m.copy.deepcopy(e)
            for ev in e2.events:
                ev.effective_seq = float(ev.recorded_seq)
            return orig(e2)
        m._fold = broken
        return lambda: setattr(m, '_fold', orig)

    def subtraction():
        # The forbidden move, and it produces the RIGHT NUMBER today: gross minus reimbursed
        # minus unresolved is $300, which is what a sum of evidenced payments also gives.
        # Only the branches where the $650 resolves two different ways separate them.
        orig = m.qualifying

        def broken(e, rules=None):
            f = m._fold(e)
            gross = m._effective_obligation(f)
            others = sum(p.amount for p in f['funders'].values() if p.funder != 'user')
            settled = sum(d.amount for d in f['determinations'] if d.status in m.SETTLING)
            unresolved = round(max(0.0, gross - sum(p.amount for p in f['funders'].values())
                                   - settled), 2)
            confirmed = round(gross - others - unresolved, 2)
            return m.QualifyingFigure(gross, confirmed, unresolved,
                                      m.UNRESOLVED if unresolved > 0 else confirmed,
                                      'sum_of_confirmed_user_payments', rules,
                                      tuple(f['funders'].values()))
        m.qualifying = broken
        return lambda: setattr(m, 'qualifying', orig)

    def collapse_states():
        orig = m.state

        def broken(e):
            s = orig(e)
            if s.get('status') == 'pending_claim':
                s['status'] = 'unpaid'
            return s
        m.state = broken
        return lambda: setattr(m, 'state', orig)

    def overwrite_determinations():
        orig = m._fold

        def broken(e):
            f = orig(e)
            if f['determinations']:
                f['determinations'] = [f['determinations'][-1]]
            return f
        m._fold = broken
        return lambda: setattr(m, '_fold', orig)

    def plan_is_current():
        orig = m._plan_at
        m._plan_at = lambda folded, when: (folded['plan_timeline'][-1][1]
                                           if folded['plan_timeline'] else None)
        return lambda: setattr(m, '_plan_at', orig)

    def duplicate_funds_twice():
        orig = m._fold

        def broken(e):
            e2 = m.copy.deepcopy(e)
            for ev in e2.events:
                if ev.kind == 'eob_imported':
                    ev.kind = 'allocated'
                    ev.payload = {'funder': (ev.payload.get('duplicate_of') or 'x') + '_dup',
                                  'amount': 250.0}
            return orig(e2)
        m._fold = broken
        return lambda: setattr(m, '_fold', orig)

    def total_always_available():
        orig = m.qualifying

        def broken(e, rules=None):
            fig = orig(e, rules)
            return m.QualifyingFigure(fig.gross, fig.confirmed_user_paid, fig.unresolved,
                                      fig.confirmed_user_paid, fig.basis, fig.rules,
                                      fig.sources)
        m.qualifying = broken
        return lambda: setattr(m, 'qualifying', orig)

    def cleared_is_enough():
        orig = m.is_confirmed
        m.is_confirmed = lambda p: bool(p.cleared)
        return lambda: setattr(m, 'is_confirmed', orig)

    def year_rolls_forward():
        orig = m.state

        def broken(e):
            s = orig(e)
            s['expense_year'] = 2027
            return s
        m.state = broken
        return lambda: setattr(m, 'state', orig)

    def merge_loses_provenance():
        orig = m.merge

        def broken(a, b):
            out = orig(a, b)
            out.provenance = [{'kind': 'merged', 'at': m._now()}]
            return out
        m.merge = broken
        return lambda: setattr(m, 'merge', orig)

    def unpaid_closes_obligation():
        orig = m._effective_obligation

        def broken(folded):
            reduced = sum(d.amount for d in folded['determinations']
                          if d.status in (set(m.REDUCES_OBLIGATION) | {'unpaid'}))
            return round(folded['obligation'] - reduced, 2)
        m._effective_obligation = broken
        return lambda: setattr(m, '_effective_obligation', orig)

    def rules_argument_ignored():
        orig = m.qualifying
        m.qualifying = lambda e, rules=None: orig(e, m._fold(e)['rules'] or rules)
        return lambda: setattr(m, 'qualifying', orig)

    def evidence_not_required():
        orig = m.qualifying

        def broken(e, rules=None):
            f = m._fold(e)
            gross = m._effective_obligation(f)
            paid = [p for p in f['funders'].values() if p.funder == 'user' and p.confirmed]
            cash = [d for d in f['determinations'] if d.status in m.USER_FUNDING]
            confirmed = round(sum(p.amount for p in paid)
                              + sum(d.amount for d in cash), 2)
            settled = sum(d.amount for d in f['determinations'] if d.status in m.SETTLING)
            unresolved = round(max(0.0, gross - sum(p.amount for p in f['funders'].values())
                                   - settled), 2)
            return m.QualifyingFigure(gross, confirmed, unresolved,
                                      m.UNRESOLVED if unresolved > 0 else confirmed,
                                      'sum_of_confirmed_user_payments', rules,
                                      tuple(f['funders'].values()))
        m.qualifying = broken
        return lambda: setattr(m, 'qualifying', orig)

    return [
        ('events fold in arrival order rather than effective order', arrival_order),
        ('the confirmed figure is a subtraction, which gives the same $300 today',
         subtraction),
        ('unpaid and pending_claim collapse into one state', collapse_states),
        ('determinations are overwritten rather than superseded', overwrite_determinations),
        ('the plan is the current plan, not the plan in force when it was incurred',
         plan_is_current),
        ('a duplicate EOB creates a second funding event', duplicate_funds_twice),
        ('a definitive total is offered while something is unresolved',
         total_always_available),
        ('cleared alone confirms a payment', cleared_is_enough),
        ('a new plan year moves an expense into it', year_rolls_forward),
        ('a merge keeps only one provenance', merge_loses_provenance),
        ('unpaid closes the obligation the way a write-off does',
         unpaid_closes_obligation),
        ('the rules argument is ignored in favour of whatever is current',
         rules_argument_ignored),
        ('an unevidenced cash payment becomes deductible', evidence_not_required),
    ]


def run(ctx):
    check = ctx.check

    try:
        from core import allocation as model
    except Exception as e:                                    # noqa: BLE001
        check(f'core/allocation.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/allocation.py imports', True)

    try:
        fx = _load_fixture()
    except Exception as e:                                    # noqa: BLE001
        check(f'the lifecycle fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, model)
    check('the lifecycle fixture passes in full', not failures and not err and passed > 0)
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
