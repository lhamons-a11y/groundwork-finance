# -*- coding: utf-8 -*-
"""The classifier holds its invariants, and the fixture can still detect it losing them.

`core/classification.py` implements `gw 2.0/CLASSIFICATION_QUESTION.md`; the assertions
live in `tests/test_classification_fixture.py`, which was written before the module.

This section makes **two different claims**, and keeping them apart is the point:

    the fixture passes          the model satisfies the specification
    every mutation is caught    the specification is enforced, not merely asserted

The second is the one that keeps its value. A suite green at 685 while two surfaces were
visibly broken, three checks in one session that could not fail for the reason they named,
and a defect shipped at 09:00 inside a commit carrying three mutation-proven checks — the
recurring lesson is that passing checks say less than they appear to. So each invariant is
broken here on purpose, and the fixture has to notice.

The mutations run against an in-memory monkeypatch and are always undone, so this section
leaves the module exactly as it found it. That is asserted at the end rather than assumed.
"""
import io
import contextlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_fixture():
    path = BASE / 'tests' / 'test_classification_fixture.py'
    spec = importlib.util.spec_from_file_location('_gw_classification_fixture', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_fixture(fx, model):
    """Run every assertion silently. Returns (passed, failures, error)."""
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


# ── The mutations ───────────────────────────────────────────────────────────
# Each breaks exactly one invariant and returns an undo. A mutation that leaves the
# fixture green means the invariant it broke is not actually being enforced by any check,
# which is a hole in the specification rather than a passing model.

def _mutations(m):
    def wall():
        orig = m.qualifying_amount

        def broken(c):
            if m.axis(c, m.COUNTERPARTY).state in m.SUPPORTING_STATES:
                return round(getattr(c, 'classification', c).amount, 2)
            return orig(c)
        m.qualifying_amount = broken
        return lambda: setattr(m, 'qualifying_amount', orig)

    def boundary_by_strength():
        orig = m.inside_boundary
        m.inside_boundary = lambda c: any(
            m.axis(c, n).state in (m.CORROBORATED, m.USER_ASSERTED, m.IMPORTED_ATTESTED)
            for n in m.AXES)
        return lambda: setattr(m, 'inside_boundary', orig)

    def sticky():
        orig = m._state_from

        def broken(evidence):
            ev = list(evidence)
            if not ev:
                return m.NOT_EVALUATED
            latest = ev[-1]
            if latest.source in m.KNOWING_SOURCES:
                if not latest.supports:
                    return m.CONTRADICTED
                return (m.USER_ASSERTED if latest.source == m.USER_STATED
                        else m.IMPORTED_ATTESTED)
            supporting = [e for e in ev if e.supports]
            if len({e.source for e in supporting}) >= 2:
                return m.CORROBORATED
            return m.SINGLE_WEAK_SIGNAL if supporting else m.NOT_EVALUATED
        m._state_from = broken
        return lambda: setattr(m, '_state_from', orig)

    def category_provenance():
        orig = m._category_evidence

        def broken(category, category_set_by):
            if m._matches(category, m.HEALTH_CATEGORY_TERMS):
                return [m.Evidence(m.CONTENT, m.USER_STATED, True, recorded_at=m._now())]
            return []
        m._category_evidence = broken
        return lambda: setattr(m, '_category_evidence', orig)

    def sensitivity_on_verdict():
        orig = m.sensitivity

        def broken(c):
            src = getattr(c, 'classification', c)
            if hasattr(src, 'determinations'):
                states = {m.axis(src, n).state for n in m.AXES}
                if not (states & m.SUPPORTING_STATES):
                    return m.Sensitivity(domain=None, manufactured=False)
            return orig(c)
        m.sensitivity = broken
        return lambda: setattr(m, 'sensitivity', orig)

    def persist_before_surfacing():
        orig = m.is_persisted
        m.is_persisted = lambda x: True
        return lambda: setattr(m, 'is_persisted', orig)

    def promote_the_ask():
        orig = m.gauntlet
        m.gauntlet = lambda c, monthly_budget=None: dict(
            orig(c, monthly_budget), materiality=True, actionability=True)
        return lambda: setattr(m, 'gauntlet', orig)

    def overwrite():
        orig = m.record_evidence

        def broken(c, axis_name, source=None, supports=True, amount=None,
                   rule_version=m.CLASSIFIER_RULE_VERSION):
            out = orig(c, axis_name, source, supports, amount, rule_version)
            kept = tuple(d for d in out.determinations if d.axis != axis_name)
            return m.replace(out, determinations=kept + (m.determination(out, axis_name),))
        m.record_evidence = broken
        return lambda: setattr(m, 'record_evidence', orig)

    def collapse_completeness():
        orig = m.qualifying_total

        def broken(classifications, rules=None):
            rows = list(classifications)
            attested = round(sum(m.qualifying_amount(c) for c in rows), 2)
            une = [c for c in rows
                   if m.axis(c, m.CONTENT).state in (m.NOT_EVALUATED, m.CONTRADICTED)]
            return m.QualifyingTotal(attested, len(une), len(rows) - len(une),
                                     m.UNAVAILABLE if une else attested, rules)
        m.qualifying_total = broken
        return lambda: setattr(m, 'qualifying_total', orig)

    def manufacture_a_total():
        orig = m.qualifying_total
        m.qualifying_total = lambda cs, rules=None: m.replace(
            orig(cs, rules), definitive=orig(cs, rules).attested)
        return lambda: setattr(m, 'qualifying_total', orig)

    def guess_a_person():
        orig = m.surface
        m.surface = lambda c: m.replace(orig(c), suggested_person='rob')
        return lambda: setattr(m, 'surface', orig)

    def narrator_gets_records():
        orig = m.narrator_facts
        m.narrator_facts = lambda d: m.replace(orig(d), includes_records=True)
        return lambda: setattr(m, 'narrator_facts', orig)

    def last_reading_wins():
        # The shipped behaviour before HAZARD_AUDIT H3: `attested[-1]` - a disputed tax figure
        # decided by which reading was appended last. Position is not evidence.
        orig = m.qualifying_amount

        def broken(c):
            state = m.axis(c, m.CONTENT).state
            if state not in (m.USER_ASSERTED, m.IMPORTED_ATTESTED):
                return 0.00
            attested = [e.amount for e in m.evidence(c, m.CONTENT)
                        if e.supports and e.amount is not None]
            src = getattr(c, 'classification', c)
            return round(attested[-1] if attested else src.amount, 2)
        m.qualifying_amount = broken
        return lambda: setattr(m, 'qualifying_amount', orig)

    return [
        ('a disputed amount is decided by the last reading recorded', last_reading_wins),
        ('tax reads the counterparty axis - the wall between the axes is gone', wall),
        ('the boundary is entered by strength rather than existence',
         boundary_by_strength),
        ('a merchant rule can overturn a contradicted state', sticky),
        ('a category name is content evidence whoever set it', category_provenance),
        ('sensitivity is keyed on the verdict, so a ruled-out health question is free',
         sensitivity_on_verdict),
        ('a suspicion persists without ever being rendered', persist_before_surfacing),
        ('the per-transaction ask clears the gauntlet and can interrupt', promote_the_ask),
        ('a determination is overwritten rather than superseded', overwrite),
        ('contradicted is counted as unevaluated', collapse_completeness),
        ('a definitive total is manufactured while anything is unevaluated',
         manufacture_a_total),
        ('the marker guesses which household member the transaction belongs to',
         guess_a_person),
        ('the narrator receives the underlying records', narrator_gets_records),
    ]


def run(ctx):
    check = ctx.check

    try:
        from core import classification as model
    except Exception as e:                                    # noqa: BLE001
        check(f'core/classification.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/classification.py imports', True)

    try:
        fx = _load_fixture()
    except Exception as e:                                    # noqa: BLE001
        check(f'the classification fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, model)
    check('the classification fixture passes in full', not failures and not err
          and passed > 0)
    if failures or err:
        for f in failures[:6]:
            print(f'        failing: {f}')
        if err:
            print(f'        raised: {err}')
        # A broken model makes every mutation "detected" for the wrong reason, so the
        # mutation half is meaningless until the baseline is green again.
        check('mutation detection is meaningful (baseline green)', False)
        return

    # ── The half that keeps its value ───────────────────────────────────────
    for name, make in _mutations(model):
        undo = make()
        try:
            _, mutated_failures, mutated_err = _run_fixture(fx, model)
        finally:
            undo()
        # Raising also counts as detection - the fixture noticed, loudly.
        check('caught: ' + name, bool(mutated_failures) or bool(mutated_err))

    # The mutations monkeypatch a live module. If any undo failed, every check after
    # this section would be running against a broken classifier, so prove restoration
    # rather than trusting the try/finally.
    restored, restored_failures, restored_err = _run_fixture(fx, model)
    check('the module is left exactly as it was found',
          restored == passed and not restored_failures and not restored_err)
