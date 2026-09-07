# -*- coding: utf-8 -*-
"""The hostile person-identity fixture — written BEFORE the model it tests.

`gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §3 states the doctrine in five lines, and every
assertion below is one of them made mechanical:

    person_id is identity; display_name is presentation
    reassignment is a financially meaningful CORRECTION, not a cosmetic edit
    imported "patient = ROB L." must map EXPLICITLY - name matching is not identity
    person survives plan changes; coverage enrolment does not
    deleting a person with 500 historical transactions means INACTIVE, never destroyed

Plus the one from `HEALTHCARE_MODULE_DESIGN.md` §1.7 that constrains all of them: **the tax
report is the household total**, and the per-person split is supporting detail. So moving an
expense between household members changes who it is attributed to and must not change what the
household deducts. That invariant is what stops a reassignment quietly moving money.

Nothing here imports a model, because none exists — running this prints the specification it is
asserting and exits non-zero. When `core/person.py` exists, this file decides whether it works.

**The division of labour, stated so it is not mistaken for an omission.** This module owns
*which person*, never *how much*. Amounts are supplied by the caller, the same way
`core/solution.py` takes `months_observed` on trust: the caller holds the ledger.

Run:  python tests/test_person_identity_fixture.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS, FAIL, PENDING = [], [], []


def check(name, condition):
    if condition is None:
        PENDING.append(name)
        print(f'  ....  {name}')
    elif condition:
        PASS.append(name)
        print(f'  OK    {name}')
    else:
        FAIL.append(name)
        print(f'  FAIL  {name}')


# ── The fixture ─────────────────────────────────────────────────────────────
# Three expenses and two people. E3 is deliberately unassigned: an expense whose patient
# nobody has recorded is normal, and it must not be guessed at or dropped.

EXPENSES = {
    'e1': 400.00,
    'e2': 250.00,
    'e3': 150.00,     # nobody has said whose this is
}
HOUSEHOLD = 800.00


def describe():
    print('\nThe fixture, as a specification:\n')
    print('  people   rob, sam  - and a second "Sam" who is a different person')
    for k, v in EXPENSES.items():
        print('  %-4s $%7.2f%s' % (k, v, '   (unassigned)' if k == 'e3' else ''))
    print('  household total  $%.2f  - and no reassignment may change it' % HOUSEHOLD)


# ── The assertions the model has to satisfy ─────────────────────────────────

def run(model):
    # A precondition, not a concession: this fixture describes a fresh household, and a
    # registry that carried people over from a previous run would be describing a different
    # one. Identity is inherently stateful in a way a payoff calculation is not.
    model.reset()

    rob = model.add_person('Rob')
    sam = model.add_person('Sam')

    model.assign('e1', rob)
    model.assign('e2', sam)

    check('a person is identified by a row, not by the name shown',
          model.id_of(rob) != model.id_of(sam)
          and model.display_name(rob) == 'Rob')

    # Two people in one household can share a name. If the name were identity this would
    # silently merge two patients' medical spending.
    sam2 = model.add_person('Sam')
    check('two people may share a display name and stay distinct',
          model.id_of(sam) != model.id_of(sam2))

    # ── Renaming is presentation, and touches nothing ───────────────────────
    before = model.per_person_total(EXPENSES, rob)
    model.rename(rob, 'Robert')
    check('renaming changes the label',
          model.display_name(rob) == 'Robert')
    check('and changes no figure, because the name was never the identity',
          model.per_person_total(EXPENSES, rob) == before == 400.00)
    check('and is not recorded as a correction to anything financial',
          len(model.assignments('e1')) == 1)

    # ── Name matching is not identity ───────────────────────────────────────
    # John and John Jr. are the counterexample the review names. An importer that guesses
    # puts one person's prescriptions on another person's record.
    model.add_person('John')
    model.add_person('John Jr.')
    check('an imported patient name resolves to nobody until it is mapped',
          model.resolve_name('ROB L.') is None)
    check('and a near-match is not a match',
          model.resolve_name('John') is not None
          and model.resolve_name('John Jr.') != model.resolve_name('John'))
    # The case the fixture originally forgot to ask about, found by mutation testing on
    # 2026-09-07: two people called Sam. A model willing to answer this at all has decided
    # which of them gets the other's medical spending.
    check('an ambiguous name resolves to nobody, rather than to whoever is first',
          model.resolve_name('Sam') is None)
    check('and a name close to a real one is still not that person',
          model.resolve_name('Rob L.') is None
          and model.resolve_name('Robert L') is None)

    model.map_alias(rob, 'ROB L.', source='imported_eob')
    check('an explicit mapping resolves, and says where it came from',
          model.resolve_name('ROB L.') == model.id_of(rob)
          and model.alias_source(rob, 'ROB L.') == 'imported_eob')

    # ── Reassignment is a correction, and it is financially meaningful ──────
    at_first = model.now()
    check('before the correction, the split is rob 400 / sam 250',
          model.per_person_total(EXPENSES, rob) == 400.00
          and model.per_person_total(EXPENSES, sam) == 250.00)

    model.reassign('e1', sam, reason='EOB names Sam as the patient',
                   source='imported_eob')

    check('the correction moves the attribution',
          model.per_person_total(EXPENSES, rob) == 0.00
          and model.per_person_total(EXPENSES, sam) == 650.00)

    # The invariant that stops a reassignment being a way to move money. Section 213 lets a
    # taxpayer deduct what they paid for a spouse and dependents, so the household total is
    # the figure that reaches a return and it must be indifferent to who the patient was.
    check('and the household total is unchanged, because the money did not move',
          model.household_total(EXPENSES) == HOUSEHOLD)

    check('a reassignment is superseded, never overwritten',
          len(model.assignments('e1')) == 2)
    check('the prior assignment is still readable',
          model.assignments('e1')[0].person_id == model.id_of(rob))
    # bool() is not decoration. `check` routes a None condition to PENDING rather than
    # FAIL, so an `and` chain whose first term is None reports as "pending a model" instead
    # of failing - which is how the missing-provenance mutation went undetected.
    check('and it carries provenance, because this is not a cosmetic edit',
          bool(model.assignments('e1')[-1].reason)
          and bool(model.assignments('e1')[-1].source)
          and model.assignments('e1')[-1].recorded_at is not None)

    # The figure as it stood before the correction must still be reproducible, or a
    # historical tax report cannot be explained after a late correction arrives.
    check('the earlier split is still reproducible as of when it was true',
          model.per_person_total(EXPENSES, rob, as_of=at_first) == 400.00
          and model.per_person_total(EXPENSES, sam, as_of=at_first) == 250.00)

    # ── An unassigned expense is not guessed at, and not dropped ────────────
    check('an expense nobody has assigned belongs to nobody',
          model.person_of('e3') is None)
    check('it is not silently attributed to the only other person',
          model.per_person_total(EXPENSES, sam) == 650.00)
    check('but it still counts to the household, and is reported as unassigned',
          model.unassigned_total(EXPENSES) == 150.00)
    check('so the parts add up to the whole, with nothing invented and nothing lost',
          round(sum(model.per_person_total(EXPENSES, p) for p in model.people())
                + model.unassigned_total(EXPENSES), 2) == HOUSEHOLD)

    # ── Coverage enrolment is not the person ────────────────────────────────
    model.enrol(sam, plan='plan-a', effective_on='2026-01-01')
    sam_id = model.id_of(sam)
    model.enrol(sam, plan='plan-b', effective_on='2026-07-01')
    check('a person survives a plan change, because enrolment is a separate concept',
          model.id_of(sam) == sam_id and len(model.enrolments(sam)) == 2)
    check('and the enrolment in force is looked up by date, not overwritten',
          model.enrolment_at(sam, '2026-03-01') == 'plan-a'
          and model.enrolment_at(sam, '2026-09-01') == 'plan-b')
    check('and the reassignment did not follow the plan change',
          model.person_of('e1') == model.id_of(sam))

    # ── Deletion of a person with history ───────────────────────────────────
    # 500 historical transactions do not become anonymous because someone tidied a list.
    check('deleting a person who has history is refused',
          model.delete(rob) is False)
    check('and the honest operation is offered instead',
          'deactivate' in model.deletion_modes())
    model.deactivate(rob)
    check('an inactive person keeps their identity and their history',
          not model.is_active(rob) and model.display_name(rob) == 'Robert'
          and model.assignments('e1')[0].person_id == model.id_of(rob))
    check('and an inactive person is out of the active list without vanishing',
          rob not in model.people(active_only=True)
          and rob in model.people())
    check('a person with no history at all may be deleted',
          model.delete(model.add_person('Typo')) is True)


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    try:
        from core import person as model          # noqa: F401
    except ImportError:
        print('\nNo model yet — core/person.py does not exist.')
        print('This file is the specification it has to satisfy.')
        describe()
        print('\nAlso required, and not expressible as a table:')
        print('  * person_id is identity and display_name is presentation, so a rename')
        print('    changes no figure and is not a financial correction')
        print('  * two people may share a display name and remain distinct')
        print('  * an imported patient name resolves to NOBODY until mapped explicitly;')
        print('    John and John Jr. are why a near-match may never be a match')
        print('  * reassignment is a correction with provenance - reason, source, date -')
        print('    superseded rather than overwritten, and the earlier split stays')
        print('    reproducible as of when it was true')
        print('  * a reassignment must NOT change the household total, because the money')
        print('    did not move; only the attribution did')
        print('  * an unassigned expense belongs to nobody, is never attributed to the')
        print('    only other candidate, and still counts to the household')
        print('  * per-person totals plus unassigned equal the household total exactly')
        print('  * a person survives plan changes; enrolment is looked up by date')
        print('  * deleting a person with history is refused - inactive, never destroyed')
        print('\n0 passed, 0 failed — every assertion above is pending a model')
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
