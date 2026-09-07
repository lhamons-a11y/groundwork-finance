# -*- coding: utf-8 -*-
"""The `green_light()` contract — a recorded baseline of shipped behaviour.

`gw 2.0/ARCHITECTURE_REVIEW_LIFECYCLE.md` §C3 raised this to P0 with a sharper reason than
blast radius: every other P0 item is **new functionality that is currently wrong**, which is
a development problem. This one is **existing functionality whose meaning changes underneath
existing users**, which is a product-integrity problem — and 1.x is an LTS line whose whole
promise is stability.

So the invariant is not a return value, it is a product contract:

    existing user + no healthcare information + same historical financial state
            -> the same green_light result

unless an intentional change is documented and versioned.

**Why this is not a unit test.** A unit test asserts a hand-picked expected value, and a
hand-picked value written today is chosen to match today's implementation — it cannot notice
that the meaning moved, only that the arithmetic did. This records what the shipped function
actually returns across a corpus of user-like states and fails when any of it changes, for
any reason, including a reason nobody thought to write a check for. A healthcare reserve
added to `green_light()` is exactly such a reason.

**Re-recording is deliberate by construction.** `record()` refuses to overwrite a baseline
while `CONTRACT_VERSION` still matches the stored one. Changing recorded behaviour therefore
costs a version bump and a written reason, which lands in a diff and in review. A baseline
that can be silently regenerated is a rubber stamp, not a contract.

Re-record (only with an intentional, documented change):

    python tests/green_light_contract.py --record
"""
import sys
import json
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.consequence import Card                    # noqa: E402
from core.solution import green_light                # noqa: E402

BASELINE = Path(__file__).resolve().parent / 'green_light_contract.json'

# Bump ONLY for an intentional, documented behaviour change. The reason ships with it.
CONTRACT_VERSION = '1'
CHANGE_REASON = ('initial recording of the behaviour shipped in 1.x, before any healthcare '
                 'reserve exists to change it')

# The random block is seeded so the corpus is identical on every machine and every run. A
# contract baseline that drifts with the RNG is a check that fails for a reason other than
# the one it names.
SEED = 20260907
RANDOM_CASES = 40


def _card(**kw):
    base = dict(balance=0.0, rate=0.0, minimum=0.0, name='Card')
    base.update(kw)
    return base


# ── The named cases ─────────────────────────────────────────────────────────
# Chosen so each one exercises a branch that Appendix D argues about, rather than to
# produce round numbers. The recorded result is whatever the shipped function says.
NAMED_CASES = [
    ('no drivers at all', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa')],
        'budget': 775, 'drivers': []}),

    ('capacity arrived, but nobody chose anything (D.4)', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa')],
        'budget': 775,
        'drivers': [{'monthly': 120.0, 'deliberate': False, 'label': 'minimums ran out'}]}),

    ('one deliberate driver', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa'),
                  _card(balance=3000, rate=6, minimum=75, name='Store')],
        'budget': 775,
        'drivers': [{'monthly': 180.0, 'deliberate': True, 'label': 'cancelled storage',
                     'months_ago': 1}]}),

    ('two drivers, one dominant - not diffuse (D.5)', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa')],
        'budget': 900,
        'drivers': [{'monthly': 200.0, 'deliberate': True, 'label': 'cleared car',
                     'months_ago': 2},
                    {'monthly': 40.0, 'deliberate': True, 'label': 'trimmed streaming',
                     'months_ago': 5}]}),

    ('many small drivers - diffuse, so none are named (D.5)', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa')],
        'budget': 900,
        'drivers': [{'monthly': 45.0, 'deliberate': True, 'label': 'a', 'months_ago': 1},
                    {'monthly': 42.0, 'deliberate': True, 'label': 'b', 'months_ago': 2},
                    {'monthly': 40.0, 'deliberate': True, 'label': 'c', 'months_ago': 3},
                    {'monthly': 38.0, 'deliberate': True, 'label': 'd', 'months_ago': 4}]}),

    ('deliberate and uncredited together', {
        'cards': [_card(balance=12000, rate=19, minimum=280, name='Visa')],
        'budget': 1000,
        'drivers': [{'monthly': 150.0, 'deliberate': True, 'label': 'cancelled gym',
                     'months_ago': 1},
                    {'monthly': 95.0, 'deliberate': False, 'label': 'loan matured'}]}),

    ('stale credit - past the freshness window', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa')],
        'budget': 775,
        'drivers': [{'monthly': 180.0, 'deliberate': True, 'label': 'old win',
                     'months_ago': 24}]}),

    ('no months_ago recorded at all', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa')],
        'budget': 775,
        'drivers': [{'monthly': 180.0, 'deliberate': True, 'label': 'undated win'}]}),

    ('snowball rather than avalanche', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa'),
                  _card(balance=900, rate=4, minimum=25, name='Small')],
        'budget': 775, 'strategy': 'snowball',
        'drivers': [{'monthly': 180.0, 'deliberate': True, 'label': 'cancelled storage',
                     'months_ago': 1}]}),

    ('budget barely covers the minimums', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa'),
                  _card(balance=3000, rate=6, minimum=75, name='Store')],
        'budget': 280,
        'drivers': [{'monthly': 30.0, 'deliberate': True, 'label': 'trimmed something',
                     'months_ago': 1}]}),

    ('freed exceeds the budget, so the counterfactual floors at zero', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa')],
        'budget': 400,
        'drivers': [{'monthly': 600.0, 'deliberate': True, 'label': 'huge',
                     'months_ago': 1}]}),

    ('a lease past its end month, with today_key set', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa'),
                  _card(balance=4000, rate=0, minimum=310, name='Lease',
                        is_lease=True, end_month='2026-01')],
        'budget': 900, 'today_key': '2026-06', 'start_month': '2026-06',
        'drivers': [{'monthly': 310.0, 'deliberate': True, 'label': 'lease ended',
                     'months_ago': 1}]}),

    ('a PSLF loan takes minimums only', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa'),
                  _card(balance=41000, rate=5, minimum=310, name='Student',
                        is_pslf=True, forgive_after_months=48)],
        'budget': 900,
        'drivers': [{'monthly': 120.0, 'deliberate': True, 'label': 'trimmed dining',
                     'months_ago': 2}]}),

    ('a zero balance among real ones', {
        'cards': [_card(balance=0, rate=24, minimum=0, name='Paid off'),
                  _card(balance=8000, rate=22, minimum=200, name='Visa')],
        'budget': 775,
        'drivers': [{'monthly': 180.0, 'deliberate': True, 'label': 'cleared it',
                     'months_ago': 1}]}),

    ('a driver of exactly zero is not a driver', {
        'cards': [_card(balance=8000, rate=22, minimum=200, name='Visa')],
        'budget': 775,
        'drivers': [{'monthly': 0.0, 'deliberate': True, 'label': 'nothing'}]}),
]


def _random_cases():
    """Seeded portfolios, so the corpus covers shapes nobody thought to hand-write.

    `tests/test_consequence_parity.py` already establishes the pattern: randomised
    portfolios under a fixed seed, which is reproducible and broader than hand-picking.
    """
    rng = random.Random(SEED)
    out = []
    for i in range(RANDOM_CASES):
        n = rng.randint(1, 4)
        cards = []
        for k in range(n):
            balance = round(rng.uniform(200, 22000), 2)
            cards.append(_card(
                balance=balance,
                rate=round(rng.uniform(0, 29.99), 2),
                minimum=round(max(25.0, balance * rng.uniform(0.01, 0.04)), 2),
                name='C%d' % k))
        total_min = sum(c['minimum'] for c in cards)
        budget = round(total_min * rng.uniform(0.9, 2.5), 2)
        drivers = []
        for k in range(rng.randint(0, 4)):
            drivers.append({
                'monthly': round(rng.uniform(0, 320), 2),
                'deliberate': rng.random() < 0.6,
                'label': 'd%d' % k,
                'months_ago': rng.choice([None, 0, 1, 3, 9, 18, 30]),
            })
        out.append(('random %02d' % i, {
            'cards': cards, 'budget': budget, 'drivers': drivers,
            'strategy': rng.choice(['avalanche', 'snowball'])}))
    return out


def cases():
    return NAMED_CASES + _random_cases()


def compute(inputs):
    """Run the shipped function against one recorded input set."""
    kw = {k: v for k, v in inputs.items() if k not in ('cards', 'budget', 'drivers')}
    cards = [Card(**c) for c in inputs['cards']]
    # green_light mutates nothing, but the drivers list is handed straight back inside the
    # result, so copy it: a recorded baseline must not be able to alias its own input.
    drivers = [dict(d) for d in inputs['drivers']]
    return green_light(cards, inputs['budget'], drivers, **kw)


def build():
    return {
        'version': CONTRACT_VERSION,
        'reason': CHANGE_REASON,
        'seed': SEED,
        'cases': [{'id': name, 'inputs': inputs, 'result': compute(inputs)}
                  for name, inputs in cases()],
    }


def load():
    return json.loads(BASELINE.read_text(encoding='utf-8'))


def record():
    """Write the baseline. Refuses to overwrite one recorded under this same version."""
    if BASELINE.exists():
        stored = load()
        if stored.get('version') == CONTRACT_VERSION:
            print('REFUSED: a baseline already exists at version %s.' % CONTRACT_VERSION)
            print()
            print('Re-recording would silently redefine what "unchanged" means, which is')
            print('the whole thing this contract exists to prevent. If the behaviour change')
            print('is intentional, bump CONTRACT_VERSION and write CHANGE_REASON, so the')
            print('change is documented and versioned rather than absorbed.')
            return 1
        print('re-recording %s -> %s' % (stored.get('version'), CONTRACT_VERSION))
        print('reason: %s' % CHANGE_REASON)

    data = build()
    BASELINE.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n',
                        encoding='utf-8')
    lit = sum(1 for c in data['cases'] if c['result'] is not None)
    print('recorded %d cases (%d light, %d dark) at version %s'
          % (len(data['cases']), lit, len(data['cases']) - lit, CONTRACT_VERSION))
    return 0


def compare():
    """Recompute every recorded case. Returns (checked, [mismatch descriptions])."""
    stored = load()
    mismatches = []
    if stored.get('version') != CONTRACT_VERSION:
        mismatches.append('baseline is version %s, code expects %s'
                          % (stored.get('version'), CONTRACT_VERSION))
    recorded = {c['id']: c for c in stored['cases']}
    current = dict(cases())

    for missing in sorted(set(recorded) - set(current)):
        mismatches.append('case dropped from the corpus: %s' % missing)
    for added in sorted(set(current) - set(recorded)):
        mismatches.append('case not in the baseline: %s' % added)

    for name in sorted(set(recorded) & set(current)):
        got = json.loads(json.dumps(compute(current[name])))
        if got != recorded[name]['result']:
            mismatches.append('%s: recorded %r, now %r'
                              % (name, recorded[name]['result'], got))
    return len(recorded), mismatches


def main():
    if '--record' in sys.argv:
        return record()
    if not BASELINE.exists():
        print('No baseline. Run with --record to create one.')
        return 1
    checked, mismatches = compare()
    for m in mismatches[:10]:
        print('  CHANGED  %s' % m)
    print('%d cases checked, %d changed' % (checked, len(mismatches)))
    return 1 if mismatches else 0


if __name__ == '__main__':
    sys.exit(main())
