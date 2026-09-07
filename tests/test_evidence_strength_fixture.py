# -*- coding: utf-8 -*-
"""The hostile evidence-strength fixture — written BEFORE the rule it tests.

Gap 4 of `gw 2.0/HEALTHCARE_GAP_TRIAGE.md`, stated by Rob as:

    A derived fact may not possess greater evidentiary strength than its weakest
    material source.

**And the distinction that decides the design** — also Rob's, and the reason this is not
merely a `min()`:

    Walkable provenance is not enforced provenance.

`core/classification.py` already carries `sources`, so the chain can be walked. That makes the
information *available*, which is not a safety property. The stronger guarantee is:

    This operation cannot produce its result without accounting for the evidentiary
    properties of its inputs.

So the assertions below come in two halves. The first computes strength and requires it to
degrade. The second requires **consumption to be impossible without declaring what strength it
needs** — because a rule a consumer can forget is not an invariant, it is a convention.

**The centrepiece is the last case.** Two facts both equal to $1,250, one `corroborated` and one
degraded through `corroborated → inferred → single_weak_signal`, must not be interchangeable
merely because their values match.

Run:  python tests/test_evidence_strength_fixture.py
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


CVS = {'amount': 300.00, 'merchant': 'CVS/PHARMACY #4821', 'mcc': '5912',
       'category': 'Other', 'category_set_by': 'importer', 'date': '2026-03-04'}
TARGET = {'amount': 950.00, 'merchant': 'TARGET T-1184', 'mcc': '5310',
          'category': 'Household', 'category_set_by': 'importer', 'date': '2026-03-09'}
WALGREENS = {'amount': 1250.00, 'merchant': 'WALGREENS #7781', 'mcc': '5912',
             'category': 'Prescriptions', 'category_set_by': 'user', 'date': '2026-03-11'}


def describe():
    print('\nThe fixture, as a specification:\n')
    print('  strength lattice, weakest first:')
    print('    not_evaluated / contradicted  <  single_weak_signal  <  corroborated')
    print('                                  <  imported_attested / user_asserted')
    print('\n  a derived fact takes the MINIMUM over its material sources')
    print('  and no consumer may take its value without declaring what it requires')


def run(model):
    corr = model.classify(**CVS)            # merchant + mcc agree -> corroborated
    weak = model.classify(**TARGET)         # one mixed-retail signal -> single_weak_signal
    told = model.classify(**WALGREENS)      # the user named it -> user_asserted

    check('the lattice orders the states, weakest first',
          model.strength_rank('single_weak_signal') < model.strength_rank('corroborated')
          < model.strength_rank('user_asserted'))
    check('and the two ways of having no support share a floor without merging',
          model.strength_rank('not_evaluated') == model.strength_rank('contradicted')
          and 'not_evaluated' != 'contradicted')

    # ── 1. corroborated -> corroborated ─────────────────────────────────────
    f1 = model.derive('spend', 300.00, sources=[corr])
    check('a fact from one corroborated source is corroborated',
          model.strength_of(f1) == 'corroborated')

    # ── 2. corroborated + single_weak_signal -> degraded ────────────────────
    f2 = model.derive('spend', 1250.00, sources=[corr, weak])
    check('adding a weaker source degrades the fact to the weaker one',
          model.strength_of(f2) == 'single_weak_signal')
    check('and it is not rescued by the stronger source being present',
          model.strength_of(f2) != model.strength_of(f1))

    # ── 3. an inferred-only source is weak ──────────────────────────────────
    inferred_only = model.record_evidence(model.classify(amount=80.0, merchant='AMZN',
                                                         mcc='5942', category='Shopping'),
                                          'counterparty', source='inferred', supports=True)
    check('a classification resting on one inferred signal is weak',
          model.strength_of(inferred_only) == 'single_weak_signal')

    # ── 4. manufactured survives, as it already did ─────────────────────────
    check('a fact derived from manufactured sources is still manufactured',
          model.sensitivity(model.derive('spend', 300.00, sources=[corr])).manufactured is True)
    check('and one the user told us is not',
          model.sensitivity(model.derive('spend', 1250.00,
                                         sources=[told])).manufactured is False)

    # ── 5. multi-hop degradation ────────────────────────────────────────────
    hop1 = model.derive('subtotal', 1250.00, sources=[told])          # user_asserted
    hop2 = model.derive('total', 1250.00, sources=[hop1, corr])       # -> corroborated
    hop3 = model.derive('report', 1250.00, sources=[hop2, weak])      # -> single_weak_signal
    check('strength degrades across hops rather than resetting',
          model.strength_of(hop1) == 'user_asserted'
          and model.strength_of(hop2) == 'corroborated'
          and model.strength_of(hop3) == 'single_weak_signal')
    check('and a later hop can never be stronger than an earlier one',
          model.strength_rank(model.strength_of(hop3))
          <= model.strength_rank(model.strength_of(hop2))
          <= model.strength_rank(model.strength_of(hop1)))

    # ── 6. a contradicted source anywhere in the chain ──────────────────────
    ruled_out = model.record_evidence(model.classify(**TARGET), 'counterparty',
                                      source='user_stated', supports=False)
    f6 = model.derive('spend', 950.00, sources=[corr, ruled_out])
    check('a contradicted source drags the whole fact to the floor',
          model.strength_rank(model.strength_of(f6))
          == model.strength_rank('contradicted'))
    check('and the fact says WHICH floor it is on, because the two are different reasons',
          model.strength_of(f6) == 'contradicted')

    # ── 7. invalidating a source: what actually happens, stated honestly ────
    # The first version of this check was named "invalidating the source invalidates what
    # was derived from it" and did not test that at all - it built a NEW fact from the
    # weakened source, which is a different claim. Meaning-named and value-asserting, the
    # exact defect identified one commit earlier, committed here by the same hand.
    #
    # What is true: classifications are immutable, so recording contradicting evidence
    # returns a NEW classification and the existing fact still references the old one. A
    # derived fact is therefore a statement about its sources AS THEY STOOD - which is the
    # historical-truth invariant, not a propagation failure. The caller re-derives to get a
    # current view.
    before = model.strength_of(f1)
    weakened = model.record_evidence(corr, 'counterparty', source='user_stated',
                                     supports=False)
    check('contradicting evidence produces a new source, leaving the old one intact',
          model.strength_of(weakened) == 'contradicted'
          and model.strength_of(corr) == 'corroborated')
    check('so a fact already derived still reports what was known when it was made',
          model.strength_of(f1) == before == 'corroborated')
    check('and re-deriving against the new evidence degrades, which is how a current '
          'view is obtained',
          model.strength_of(model.derive('spend', 300.00,
                                         sources=[weakened])) == 'contradicted')

    # ── 7b. a source that contributes nothing cannot weaken the fact ────────
    # Untested in the first version, which is why the mutation making every source material
    # went unnoticed. `min` over sources is only correct over MATERIAL ones.
    nothing = model.classify(amount=0.0, merchant='TARGET T-1', mcc='5310',
                             category='Household')
    check('a zero-amount source is immaterial, however weak its evidence',
          model.strength_of(nothing) == 'single_weak_signal'
          and model.strength_of(model.derive('spend', 300.00,
                                             sources=[corr, nothing])) == 'corroborated')

    # ── 8. THE CENTREPIECE: same value, different strength, not interchangeable ─
    strong = model.derive('owed', 1250.00, sources=[corr])
    degraded = model.derive('owed', 1250.00, sources=[hop3])
    check('two facts can carry the same number and different strength',
          strong.value == degraded.value == 1250.00
          and model.strength_of(strong) != model.strength_of(degraded))

    # And the enforcement half. A consumer must declare what it requires, and the weaker
    # fact must be refused where the stronger one is accepted - or the strength is decoration.
    check('a consumer that declares its requirement gets the strong fact',
          model.consume(strong, by='tax_qualifying') == 1250.00)
    check('and is REFUSED the degraded one, though the numbers are identical',
          model.consume(degraded, by='tax_qualifying') is model.UNAVAILABLE)
    check('the refusal says what was required and what was offered',
          bool(model.refusal(degraded, by='tax_qualifying')))

    # ── The enforcement property itself ─────────────────────────────────────
    # Walkable is not enforced. A consumer that never declared a requirement must not be
    # able to take a value at all - otherwise the rule is a convention someone can forget.
    check('an undeclared consumer cannot take a value, however strong the fact',
          model.consume(strong, by='some_new_surface_nobody_registered')
          is model.UNAVAILABLE)
    check('and every registered consumer states the strength it needs',
          all(model.required_strength(c) in model.STRENGTH
              for c in model.consumers()))


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    try:
        from core import classification as model      # noqa: F401
        model.strength_of
    except (ImportError, AttributeError):
        print('\nNo rule yet — core/classification.py has no evidence-strength layer.')
        print('This file is the specification it has to satisfy.')
        describe()
        print('\nAlso required, and not expressible as a table:')
        print('  * strength is DERIVED on every read from the sources, never stored, so')
        print('    invalidating a source invalidates everything derived from it')
        print('  * a later hop can never be stronger than an earlier one')
        print('  * a contradicted source anywhere drags the fact to the floor, and the')
        print('    fact still says WHICH floor - contradicted is not not_evaluated')
        print('  * two facts with identical values and different strengths are NOT')
        print('    interchangeable to a consumer')
        print('  * a source contributing nothing cannot weaken what it did not build')
        print('  * ENFORCEMENT, not availability: a consumer that has not declared the')
        print('    strength it requires cannot take a value at all')
        print('\n0 passed, 0 failed — every assertion above is pending a rule')
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    return 1 if (FAIL or PENDING) else 0


if __name__ == '__main__':
    sys.exit(main())
