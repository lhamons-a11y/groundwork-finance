# -*- coding: utf-8 -*-
"""The hostile classification fixture — written BEFORE the classifier.

`gw 2.0/CLASSIFICATION_QUESTION.md` takes three positions: the state vocabulary is
evidence-shaped, protection and tax read two different axes rather than two thresholds on
one, and sensitivity attaches to the question rather than to the verdict. This is what
decides whether they survive contact.

Nothing here imports a classifier, because none exists — running this prints the
specification it is asserting and exits non-zero. When `core/classification.py` exists, this
file is what decides whether it works.

Written first on purpose. A check written after the thing it checks gets shaped to flatter
it, which this project has caught itself doing three times in one session.

**The pre-registered failure criterion** (`gw 2.0/CLASSIFICATION_QUESTION.md`): the two-axis
model fails if a legitimate consumer needs a claim that is neither about the counterparty nor
about the content, or if any axis-1-only classification can establish a tax-qualifying amount.
Declared here, before the experiment, so the answer cannot be argued on attachment.

Run:  python tests/test_classification_fixture.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

NOT_EVALUATED = 'not_evaluated'
UNAVAILABLE = object()   # not zero, and deliberately not None

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


# ── The fixture ──────────────────────────────────────────────────────────────
# Five transactions chosen so that every one of them breaks a different tempting
# shortcut. Each is stated as the raw record only — what a bank feed actually
# carries — because the whole question is what may be concluded from that.

TRANSACTIONS = {
    # The one the reviews argue about. Certain about the counterparty, silent
    # about what was bought: prescription, birthday card or crisps.
    't1_cvs': {
        'amount': 47.32, 'merchant': 'CVS/PHARMACY #4821', 'mcc': '5912',
        'category': 'Other', 'category_set_by': 'importer', 'date': '2026-03-04',
    },
    # Nothing in the record says health. It was a blood-pressure cuff; no part of
    # the system knows that, and no part of it may pretend to.
    't2_amazon': {
        'amount': 89.00, 'merchant': 'AMZN Mktp US*2K4B', 'mcc': '5942',
        'category': 'Shopping', 'category_set_by': 'importer', 'date': '2026-03-06',
    },
    # One charge, two kinds of thing. Protection and tax must reach DIFFERENT
    # answers on this single row, which is the clearest test that they are not
    # one decision with two thresholds.
    't3_target_split': {
        'amount': 150.00, 'merchant': 'TARGET T-1184', 'mcc': '5310',
        'category': 'Household', 'category_set_by': 'importer', 'date': '2026-03-09',
    },
    # Identical category strings, different provenance. This pair is the reason
    # `is_protected(category_name)` cannot be the whole path.
    't4_user_named': {
        'amount': 62.00, 'merchant': 'WALGREENS #7781', 'mcc': '5912',
        'category': 'Prescriptions', 'category_set_by': 'user', 'date': '2026-03-11',
    },
    't5_importer_named': {
        'amount': 62.00, 'merchant': 'WALGREENS #7781', 'mcc': '5912',
        'category': 'Prescriptions', 'category_set_by': 'importer', 'date': '2026-03-12',
    },
}

# What the evidence supports, per axis. Axis 1 is about the counterparty, axis 2
# about the content, and the second is not reachable from the first at any
# strength.
EXPECTED_AXES = {
    't1_cvs':            {'counterparty': 'corroborated',     'content': 'not_evaluated'},
    't2_amazon':         {'counterparty': 'not_evaluated',    'content': 'not_evaluated'},
    't3_target_split':   {'counterparty': 'single_weak_signal', 'content': 'not_evaluated'},
    't4_user_named':     {'counterparty': 'corroborated',     'content': 'user_asserted'},
    't5_importer_named': {'counterparty': 'corroborated',     'content': 'not_evaluated'},
}

# Which consumer may read which axis. Getting this table wrong is the defect the
# whole document exists to prevent.
CONSUMERS = {
    'lever_eligibility': 'counterparty',
    'tax_qualifying':    'content',
}


def describe():
    """Print the fixture as a specification, for when no classifier exists yet."""
    print('\nThe fixture, as a specification:\n')
    for key, t in TRANSACTIONS.items():
        axes = EXPECTED_AXES[key]
        print('  %-18s $%7.2f  %-22s mcc %s  category %-14s (%s)'
              % (key, t['amount'], t['merchant'], t['mcc'], t['category'],
                 t['category_set_by']))
        print('  %-18s   counterparty=%-18s content=%s'
              % ('', axes['counterparty'], axes['content']))
    print('\n  consumers:')
    for consumer, axis in CONSUMERS.items():
        print('    %-20s reads %s, and only that' % (consumer, axis))


# ── The assertions the classifier has to satisfy ────────────────────────────

def run(model):
    """Drive `model` through the fixture. `model` is whatever core/classification.py exposes."""
    c = {k: model.classify(**t) for k, t in TRANSACTIONS.items()}

    # ── Position 1: the vocabulary is evidence-shaped ───────────────────────
    for key, expected in EXPECTED_AXES.items():
        got = {'counterparty': model.axis(c[key], 'counterparty').state,
               'content': model.axis(c[key], 'content').state}
        check('%s resolves to %s' % (key, expected), got == expected)
        if got != expected:
            print(f'        expected {expected}')
            print(f'        got      {got}')

    # A stored confidence number is a fabricated heuristic waiting to be
    # thresholded, and the moment it exists something writes `> 0.8` and an
    # invented number drives a protection decision invisibly.
    check('no classification carries a confidence number',
          not any(hasattr(model.axis(c['t1_cvs'], a), 'confidence')
                  for a in ('counterparty', 'content')))

    # Source is per-evidence; state is the summary over all of it. Two fields,
    # not one, and the sources stay individually inspectable.
    check('each piece of evidence names its own source',
          {e.source for e in model.evidence(c['t1_cvs'], 'counterparty')}
          == {'merchant_match', 'mcc'})

    # `not_evaluated` and `contradicted` produce the same result for every
    # consumer that exists today. That is the condition under which states get
    # collapsed and a later consumer arrives that must tell them apart.
    ruled_out = model.record_evidence(c['t2_amazon'], 'content',
                                      source='user_stated', supports=False)
    check('contradicted is a distinct state from not_evaluated',
          model.axis(ruled_out, 'content').state == 'contradicted'
          and model.axis(c['t2_amazon'], 'content').state == NOT_EVALUATED)

    # ── Position 2: two axes, and a wall between them ───────────────────────
    # The trap this fixture exists to catch. Ten CVS charges are ten pieces of
    # counterparty evidence and zero pieces of content evidence. If piling them
    # up ever moves axis 2, the wall is not real and the separation collapses
    # back into one classification with two thresholds.
    piled = c['t1_cvs']
    for _ in range(10):
        piled = model.record_evidence(piled, 'counterparty', source='merchant_match',
                                      supports=True)
    check('no amount of counterparty evidence establishes content',
          model.axis(piled, 'content').state == NOT_EVALUATED)

    check('lever eligibility reads the counterparty axis',
          model.reads('lever_eligibility') == ('counterparty',))
    check('the tax consumer reads the content axis, and only that',
          model.reads('tax_qualifying') == ('content',))

    # CVS is ambiguous -> not a lever AND not in the Schedule A total. The same
    # decision, and only by coincidence: one over-includes, the other
    # under-includes, and they happen to agree here.
    check('an axis-1-only transaction is not offered as a lever',
          not model.is_lever_candidate(c['t1_cvs']))
    check('and cannot appear in a qualifying tax total',
          model.qualifying_amount(c['t1_cvs']) == 0.00)

    # The coincidence breaking. One row, two answers: protection over-includes
    # to the whole charge, tax under-includes to the attested part.
    split = model.record_evidence(c['t3_target_split'], 'content',
                                  source='imported_eob', supports=True,
                                  amount=28.40)
    check('a partially attested charge is protected in full',
          not model.is_lever_candidate(split))
    check('and qualifies only for the attested portion',
          model.qualifying_amount(split) == 28.40)
    check('so protection and tax reach different answers on the same row',
          model.is_lever_candidate(split) is False
          and model.qualifying_amount(split) != TRANSACTIONS['t3_target_split']['amount'])

    # The category-provenance pair. Identical strings, different axis, different
    # tax treatment - and no inspection of the string can tell them apart.
    check('a user-set category is content evidence and may reach the tax total',
          model.qualifying_amount(c['t4_user_named']) == 62.00)
    check('an importer-set category with the same name may not',
          model.qualifying_amount(c['t5_importer_named']) == 0.00)
    check('both are still protected, because protection reads the other axis',
          not model.is_lever_candidate(c['t4_user_named'])
          and not model.is_lever_candidate(c['t5_importer_named']))

    # ── The boundary is entered by existence, not by strength ───────────────
    # Global fail-closed would make ordinary unknown transactions unavailable as
    # levers and effectively disable the solution engine for users with no
    # healthcare data at all. A user with no health signals is never inside.
    check('a transaction with no signal on either axis is outside the boundary',
          not model.inside_boundary(c['t2_amazon']))
    check('and remains an ordinary lever candidate',
          model.is_lever_candidate(c['t2_amazon']))
    check('one weak signal is enough to enter the boundary',
          model.inside_boundary(c['t3_target_split']))
    check('and entering it removes the transaction as a lever',
          not model.is_lever_candidate(c['t3_target_split']))

    # ── Position 3: sensitivity attaches to the question ────────────────────
    # A row saying "evaluated for health relevance, not supported" still
    # discloses that this transaction was health-suspicious enough to evaluate.
    # The sensitive act was asking about a named person; the answer does not
    # undo it.
    check('a contradicted health classification still carries health sensitivity',
          model.sensitivity(ruled_out).domain == 'health')
    check('an unevaluated transaction carries none',
          model.sensitivity(c['t2_amazon']).domain is None)

    # The inversion. A verdict-keyed model ranks the unresolved states lowest -
    # nothing was established, so nothing was created - and gets it backwards.
    # What the user told us they can see and correct; what we inferred they
    # cannot, because they do not know it exists.
    check('a manufactured classification is marked as manufactured',
          model.sensitivity(c['t1_cvs']).manufactured is True)
    check('and one the user asserted is not',
          model.sensitivity(c['t4_user_named']).manufactured is False)

    # ── Contradicted is sticky, and that is a policy difference ─────────────
    # Entering the boundary costs one lever; leaving it wrongly proposes cutting
    # someone's medication. So entry takes any supporting signal and exit takes
    # knowing-party evidence - and a state reached by knowing-party evidence
    # cannot be undone by a merchant rule, or the user answers "no, it was a
    # birthday card" and gets asked again next month.
    nagged = model.record_evidence(ruled_out, 'content', source='merchant_match',
                                   supports=True)
    check('weak evidence cannot re-enter a contradicted transaction',
          model.axis(nagged, 'content').state == 'contradicted'
          and not model.inside_boundary(nagged))
    reopened = model.record_evidence(ruled_out, 'content', source='imported_eob',
                                     supports=True)
    check('but knowing-party evidence can',
          model.inside_boundary(reopened))
    check('and a not_evaluated transaction enters on any signal',
          model.inside_boundary(model.record_evidence(
              c['t2_amazon'], 'counterparty', source='merchant_match', supports=True)))

    # ── The no-silent-learning collision, and what surfacing means ──────────
    # A stored single_weak_signal health suspicion the user has never seen is an
    # unsurfaced observation that persists. The Passive tier is what resolves it:
    # visible where the user meets it, no prompt, no budget draw. Persistence
    # follows the RENDER, not the answer.
    check('an unsurfaced suspicion is not persisted',
          not model.is_persisted(c['t1_cvs']))
    marker = model.surface(c['t1_cvs'])
    check('surfacing is Passive - it lives on the transaction row',
          marker.tier == 'passive' and marker.draws_budget is False)
    check('and persistence follows the render, not the answer',
          model.is_persisted(marker))
    check('it asks for a fact, never for a commitment',
          marker.asks_for == 'fact')

    # The marker is about the TRANSACTION. Inferring which household member is
    # ill is the most disclosive thing this module could do, and it would be
    # inferred rather than told - so no person is named, suggested or defaulted,
    # even where history would support a guess.
    check('the marker names no person, and offers no default',
          marker.person is None and marker.suggested_person is None)

    # Per transaction it fails the gauntlet at the first gate, and that is the
    # correct outcome rather than a problem: strictness is free, so a
    # sub-threshold insight stays Passive instead of interrupting.
    check('a single classification question fails materiality',
          not model.gauntlet(marker)['materiality'])
    check('so it is never promoted to proactive',
          not model.can_promote(marker))

    # The one proactive form that can clear the gauntlet honestly: aggregated,
    # seasonal, and material because it moves a deduction. It joins the budget
    # its attention cost resembles rather than minting its own.
    offer = model.review_offer(list(c.values()), season='filing')
    check('the aggregate review offer is material and actionable',
          model.gauntlet(offer)['materiality'] and model.gauntlet(offer)['actionability'])
    check('and draws the brake budget rather than a new one',
          offer.budget == 'brake')

    answered = model.answer(marker, content_is_health=True, source='user_stated')
    check('answering it establishes content evidence',
          model.axis(answered, 'content').state == 'user_asserted')

    # ── No disclosiveness gradient within the health domain ─────────────────
    # A therapist's office is more disclosive than a pharmacy. Serving that
    # would require Groundwork to rank how embarrassing a kind of care is, which
    # is the confidence float in different clothes and a judgement this
    # application must never make. One domain, one protection level.
    check('the counterparty axis has no sub-kinds',
          not hasattr(model.axis(c['t1_cvs'], 'counterparty'), 'kind'))
    check('and sensitivity carries no disclosiveness ranking',
          not hasattr(model.sensitivity(c['t1_cvs']), 'degree'))

    # ── Derived facts: health context survives transformation ───────────────
    # "Spending increased 20%" contains no medical word and is derived entirely
    # from health-classified transactions. A check of the form
    # `if health_context: refuse` is insufficient, because the context is gone
    # by the time the sentence exists.
    delta = model.category_delta('Other', month='2026-03', from_month='2026-02')
    check('a derived figure inherits the sensitivity of what produced it',
          model.sensitivity(delta).domain == 'health')
    check('the narrator receives a gated fact set, not the underlying records',
          model.narrator_facts(delta) is not None
          and not model.narrator_facts(delta).includes_records)
    check('export carries the derived sensitivity with it',
          model.export_row(delta)['sensitivity'] == 'health')
    check('and so does backup',
          model.backup_row(delta)['sensitivity'] == 'health')

    # ── Provenance, and the C1 defect arriving with sensitive data ──────────
    # Not `health = true`. Without this, a rule change silently makes every
    # prior judgement unreproducible - which is exactly what happened to
    # `is_protected('Prescriptions')` on 2026-09-06, except the thing made
    # unreproducible here is sensitive information about a person.
    det = model.determination(c['t1_cvs'], 'counterparty')
    check('every classification names its evidence, rule version and date',
          det.evidence and det.rule_version and det.determined_at)
    check('a classification is superseded, never overwritten',
          len(model.determinations(answered, 'content')) == 2)
    check('and the prior determination is still readable',
          model.determinations(answered, 'content')[0].state == NOT_EVALUATED)

    # Adding a merchant to the health list must not silently change what a past
    # classification meant.
    bumped = model.with_rules(version='3')
    check('a new rule version may classify differently',
          bumped.classify(**TRANSACTIONS['t2_amazon']) is not None)
    check('without changing what the old version concluded',
          model.axis(model.reproduce(det), 'counterparty').state == 'corroborated'
          and model.reproduce(det).rule_version == det.rule_version)

    # ── The tax total is a triple, and absence is not zero ──────────────────
    # The axis-1-only set is not absent from the return, it is UNEVALUATED, and
    # a total that silently omits it claims a completeness it does not have.
    total = model.qualifying_total(list(c.values()), rules='v2026.1')
    check('the qualifying total reports what was attested',
          total.attested == 62.00)
    check('and reports the unevaluated population beside it',
          total.unevaluated_count == 4)
    check('and offers no definitive total while anything is unevaluated',
          total.definitive is UNAVAILABLE)

    # "43 unevaluated" and "43 reviewed, none qualifying" are different claims
    # about completeness. Both qualify $0.00; only one of them was looked at.
    # This is the second consumer that must tell contradicted from
    # not_evaluated, and it arrives immediately rather than hypothetically.
    reviewed = model.qualifying_total(
        [ruled_out if k == 't2_amazon' else v for k, v in c.items()], rules='v2026.1')
    check('a contradicted transaction counts as evaluated, not as unevaluated',
          reviewed.unevaluated_count == 3 and reviewed.evaluated_count >= 1)
    check('and still qualifies nothing',
          reviewed.attested == 62.00)


def main():
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    try:
        from core import classification as model      # noqa: F401
    except ImportError:
        print('\nNo classifier yet — core/classification.py does not exist.')
        print('This file is the specification it has to satisfy.')
        describe()
        print('\nAlso required, and not expressible as a table:')
        print('  * no confidence number exists anywhere in the model')
        print('  * counterparty evidence never establishes content, at any strength')
        print('  * the tax consumer reads content and ONLY content; protection reads')
        print('    counterparty, and their agreeing on a given row is a coincidence')
        print('  * two identical category strings classify differently when one was')
        print('    set by the user and one by the importer')
        print('  * the boundary is entered by a signal EXISTING, not by its strength,')
        print('    so a user with no health data is never inside it and the solution')
        print('    engine behaves exactly as it does today')
        print('  * sensitivity is keyed on (subject, claim domain) at the moment the')
        print('    question is asked - not on the verdict, so `contradicted` is still')
        print('    health-domain information about a person')
        print('  * a manufactured classification is marked as such, and the unresolved')
        print('    states are the MOST sensitive, not the least')
        print('  * an unsurfaced suspicion does not persist. Surfacing is PASSIVE -')
        print('    it lives on the transaction row, draws no budget, asks for a FACT,')
        print('    and persistence follows the RENDER rather than the answer')
        print('  * per transaction the ask fails materiality and is never promoted;')
        print('    the only proactive form is the aggregated seasonal review offer,')
        print('    which draws the brake budget rather than minting its own')
        print('  * the marker is about the transaction and names no person, even')
        print('    where history would support a guess')
        print('  * contradicted is sticky: weak evidence cannot re-enter it, and it')
        print('    counts as EVALUATED in the total while not_evaluated does not')
        print('  * the health domain has no sub-kinds and no disclosiveness ranking')
        print('  * derived figures inherit sensitivity through narrator, export, backup')
        print('  * every classification carries evidence, rule version and date, and is')
        print('    superseded rather than overwritten')
        print('  * the qualifying total is attested + unevaluated + no definitive figure')
        print('\n0 passed, 0 failed — every assertion above is pending a classifier')
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
