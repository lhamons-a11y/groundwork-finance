# -*- coding: utf-8 -*-
"""Person identity holds, and the fixture can still detect it not holding.

`core/person.py` implements `gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §3; the assertions live
in `tests/test_person_identity_fixture.py`, written before the model.

Two claims kept apart, as in s65 and s75: the fixture passing says the model satisfies the
specification, every mutation being caught says the specification is enforced.

The mutations are chosen to be the plausible implementations rather than absurd ones. Matching
an imported patient name by prefix, keeping one enrolment row and updating it, letting a
reassignment fall through to the household total — each is what a reasonable person writes
first, and each puts one household member's medical spending somewhere it does not belong.
"""
import io
import contextlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_fixture():
    path = BASE / 'tests' / 'test_person_identity_fixture.py'
    spec = importlib.util.spec_from_file_location('_gw_person_fixture', path)
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
    def name_is_identity():
        orig = m.resolve_name

        def broken(name):
            hit = orig(name)
            if hit is not None:
                return hit
            for p in m.people():
                if p.display_name.lower().startswith(name.lower()[:4]):
                    return p.id
            return None
        m.resolve_name = broken
        return lambda: setattr(m, 'resolve_name', orig)

    def ambiguous_name_resolves():
        orig = m.resolve_name

        def broken(name):
            for p in m.people():
                if p.display_name == name:
                    return p.id
            return orig(name)
        m.resolve_name = broken
        return lambda: setattr(m, 'resolve_name', orig)

    def rename_is_a_correction():
        orig = m.rename

        def broken(person, new_name):
            for a in m.assignments_all():
                if a.person_id == person.id:
                    m.reassign(a.expense_key, person, reason='renamed', source='ui')
                    break
            return orig(person, new_name)
        m.rename = broken
        return lambda: setattr(m, 'rename', orig)

    def reassign_overwrites():
        orig = m.reassign

        def broken(key, person, reason=None, source=None):
            rows = m.assignments(key)
            out = orig(key, person, reason, source)
            reg = m._r()
            for a in rows:
                if a in reg.assignments:
                    reg.assignments.remove(a)
            return out
        m.reassign = broken
        return lambda: setattr(m, 'reassign', orig)

    def household_follows_attribution():
        orig = m.household_total
        m.household_total = lambda expenses: round(
            sum(a for k, a in (expenses or {}).items() if m.person_of(k) is not None), 2)
        return lambda: setattr(m, 'household_total', orig)

    def as_of_ignored():
        orig = m.person_of
        m.person_of = lambda key, as_of=None: orig(key)
        return lambda: setattr(m, 'person_of', orig)

    def unassigned_goes_to_the_only_candidate():
        orig = m.person_of

        def broken(key, as_of=None):
            hit = orig(key, as_of)
            if hit is None:
                active = [p for p in m.people(active_only=True)]
                if len(active) >= 1:
                    return active[-1].id
            return hit
        m.person_of = broken
        return lambda: setattr(m, 'person_of', orig)

    def unassigned_dropped():
        orig = m.unassigned_total
        m.unassigned_total = lambda expenses, as_of=None: 0.00
        return lambda: setattr(m, 'unassigned_total', orig)

    def delete_ignores_history():
        orig = m.delete

        def broken(person):
            reg = m._r()
            reg.people = [p for p in reg.people if p.id != person.id]
            return True
        m.delete = broken
        return lambda: setattr(m, 'delete', orig)

    def deactivate_destroys():
        orig = m.deactivate

        def broken(person):
            reg = m._r()
            reg.people = [p for p in reg.people if p.id != person.id]
            reg.assignments = [a for a in reg.assignments if a.person_id != person.id]
            return person
        m.deactivate = broken
        return lambda: setattr(m, 'deactivate', orig)

    def enrolment_overwritten():
        orig = m.enrol

        def broken(person, plan=None, effective_on=None):
            reg = m._r()
            reg.enrolments = [e for e in reg.enrolments if e.person_id != person.id]
            return orig(person, plan, effective_on)
        m.enrol = broken
        return lambda: setattr(m, 'enrol', orig)

    def enrolment_is_current_not_dated():
        orig = m.enrolment_at

        def broken(person, when):
            rows = m.enrolments(person)
            return rows[-1].plan if rows else None
        m.enrolment_at = broken
        return lambda: setattr(m, 'enrolment_at', orig)

    def provenance_dropped():
        orig = m.reassign
        m.reassign = lambda key, person, reason=None, source=None: orig(key, person)
        return lambda: setattr(m, 'reassign', orig)

    def person_of_takes_the_first():
        orig = m.person_of

        def broken(key, as_of=None):
            rows = m.assignments(key)
            if as_of is not None:
                rows = [a for a in rows if a.seq <= as_of]
            return rows[0].person_id if rows else None
        m.person_of = broken
        return lambda: setattr(m, 'person_of', orig)

    return [
        ('an imported name is matched by prefix rather than mapped', name_is_identity),
        ('an ambiguous name resolves to the first person who has it',
         ambiguous_name_resolves),
        ('a rename is recorded as a financial correction', rename_is_a_correction),
        ('a reassignment overwrites the prior assignment', reassign_overwrites),
        ('the household total follows attribution instead of the money',
         household_follows_attribution),
        ('the as-of argument is ignored, so history is rewritten', as_of_ignored),
        ('an unassigned expense goes to the only other candidate',
         unassigned_goes_to_the_only_candidate),
        ('an unassigned expense is dropped rather than reported', unassigned_dropped),
        ('deleting a person with history is allowed', delete_ignores_history),
        ('deactivating destroys the identity and its history', deactivate_destroys),
        ('a new enrolment replaces the old one', enrolment_overwritten),
        ('the enrolment in force is the latest, not the one dated',
         enrolment_is_current_not_dated),
        ('a reassignment records no reason or source', provenance_dropped),
        ('the current person is the first assignment rather than the latest',
         person_of_takes_the_first),
    ]


def run(ctx):
    check = ctx.check

    try:
        from core import person as model
    except Exception as e:                                    # noqa: BLE001
        check(f'core/person.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/person.py imports', True)

    # The mutations need to reach the registry and the whole assignment list; exposing them
    # here rather than reaching into private state from the section.
    if not hasattr(model, 'assignments_all'):
        model.assignments_all = lambda: list(model._r().assignments)

    try:
        fx = _load_fixture()
    except Exception as e:                                    # noqa: BLE001
        check(f'the person fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, model)
    check('the person-identity fixture passes in full',
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
