"""core/consequence.py must agree with the shipped JS, to the month.

Pillar 1 replaces math that is currently live in app.js. A port that disagrees
with what users see today would not be a unification, it would be a second
answer. So this compares the Python against the REAL _simulatePayoffStrategy,
extracted from app.js at runtime by tests/js_payoff_harness.js — if app.js
changes, this notices.

Leases are deliberately excluded: their handling keys off the current month, and
a test whose fixtures meet a rolling calendar is exactly the failure this
codebase has already had twice.

Run: python tests/test_consequence_parity.py
"""
import json
import random
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / 'core'))
from core.consequence import (Card, simulate_payoff, decision_impact,  # noqa: E402
                              offsetting_monthly_delta)

PASS, FAIL = [], []


def check(name, ok):
    (PASS if ok else FAIL).append(name)
    print(f'  {"OK  " if ok else "FAIL"}  {name}')


def pslf_scenarios(n, seed=20260904):
    """Portfolios that include PSLF-flagged loans, compared against the
    PSLF-aware simulator. A loan headed for forgiveness receives its minimum but
    never extra — paying down principal there is money burned — and only
    _simulatePayoff knows that, so this set targets it specifically."""
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        cards = [{'id': f'c{i}',
                  'balance': round(rnd.uniform(500, 30000), 2),
                  'rate': round(rnd.uniform(0, 29.99), 2),
                  'minimum': round(rnd.uniform(25, 700), 2),
                  'name': f'C{i}',
                  'pslf': rnd.random() < 0.35}
                 for i in range(rnd.randint(1, 4))]
        total_min = sum(c['minimum'] for c in cards)
        out.append({'cards': cards, 'budget': round(total_min * rnd.uniform(1.0, 3.0), 2),
                    'strategy': rnd.choice(['avalanche', 'snowball']),
                    'target': 'stateful'})
    return out


def random_scenarios(n, seed=20260903):
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        cards = [{'balance': round(rnd.uniform(200, 30000), 2),
                  'rate': round(rnd.uniform(0, 29.99), 2),
                  'minimum': round(rnd.uniform(15, 700), 2),
                  'name': f'C{i}'}
                 for i in range(rnd.randint(1, 5))]
        total_min = sum(c['minimum'] for c in cards)
        budget = round(total_min * rnd.uniform(0.8, 3.0), 2)
        out.append({'cards': cards, 'budget': budget,
                    'strategy': rnd.choice(['avalanche', 'snowball'])})
    return out


def main():
    print('Consequence engine — parity with the shipped JS\n')
    scenarios = random_scenarios(300)

    proc = subprocess.run([r'node', str(BASE / 'tests' / 'js_payoff_harness.js')],
                          input=json.dumps(scenarios), capture_output=True,
                          text=True, cwd=str(BASE))
    if proc.returncode != 0:
        check(f'js harness ran ({proc.stderr.strip()[:80]})', False)
        return finish()
    js = json.loads(proc.stdout)
    check('js harness extracted and ran _simulatePayoffStrategy', True)

    # The one departure from the frozen JS, on purpose: a debt still owing after MAX_MONTHS never clears, and the
    # engine says so with None (no payoff date) where the old JS reported the 360-month cap as if it were a date.
    def never_clears(p, j):
        return p is None and j is not None and j['months'] >= 360

    mismatches, none_mismatch, interest_off = [], 0, []
    for s, j in zip(scenarios, js):
        cards = [Card(balance=c['balance'], rate=c['rate'],
                      minimum=c['minimum'], name=c['name']) for c in s['cards']]
        p = simulate_payoff(cards, s['budget'], s['strategy'])
        if never_clears(p, j):
            continue
        if (p is None) != (j is None):
            none_mismatch += 1
            continue
        if p is None:
            continue
        if p['months'] != j['months']:
            mismatches.append((s, p['months'], j['months']))
        if abs(p['total_interest'] - j['totalInterest']) > 1:
            interest_off.append((p['total_interest'], j['totalInterest']))

    check(f'all {len(scenarios)} scenarios agree on unaffordable-budget (None)',
          none_mismatch == 0)
    check(f'all {len(scenarios)} scenarios agree on months to payoff',
          not mismatches)
    for s, pm, jm in mismatches[:3]:
        print(f'        python={pm} js={jm} budget={s["budget"]} cards={s["cards"]}')
    check('total interest agrees within $1', not interest_off)
    for pi, ji in interest_off[:3]:
        print(f'        python={pi} js={ji}')

    # PSLF, which only the stateful simulator models.
    pslf = pslf_scenarios(150)
    proc2 = subprocess.run([r'node', str(BASE / 'tests' / 'js_payoff_harness.js')],
                           input=json.dumps(pslf), capture_output=True,
                           text=True, cwd=str(BASE))
    if proc2.returncode != 0:
        check('js harness ran the PSLF set', False)
    else:
        js2 = json.loads(proc2.stdout)
        bad = 0
        with_pslf = sum(1 for s in pslf if any(c['pslf'] for c in s['cards']))
        for s, j in zip(pslf, js2):
            cards = [Card(balance=c['balance'], rate=c['rate'], minimum=c['minimum'],
                          name=c['name'], is_pslf=c['pslf']) for c in s['cards']]
            p = simulate_payoff(cards, s['budget'], s['strategy'])
            if never_clears(p, j):
                continue
            pm = p['months'] if p else None
            jm = j['months'] if j else None
            if pm != jm:
                bad += 1
                if bad <= 3:
                    print(f'        python={pm} js={jm} pslf={[c["pslf"] for c in s["cards"]]}')
        check(f'all {len(pslf)} PSLF portfolios ({with_pslf} with flagged loans) '
              f'agree with _simulatePayoff', bad == 0)

    # The new dimension, which has no JS counterpart to compare against.
    cards = [Card(balance=8000, rate=22, minimum=200),
             Card(balance=3000, rate=6, minimum=75)]
    base = simulate_payoff(cards, 775)
    with_cost = simulate_payoff(cards, 775, one_time_cost=2400)
    check('a one-time cost delays payoff', with_cost['months'] > base['months'])
    check('a zero one-time cost changes nothing',
          simulate_payoff(cards, 775, one_time_cost=0)['months'] == base['months'])

    d = decision_impact(cards, 775, one_time_cost=2400)
    check('decision_impact reports base and after, not just a delta',
          d['base']['months'] == base['months'] and d['after']['months'] == with_cost['months'])
    check('decision_impact months_delta is after minus base',
          d['months_delta'] == with_cost['months'] - base['months'])

    # The bug this engine exists to retire.
    real_days = round(d['months_delta'] * 30.44)
    heuristic = round((2400 / 5000) * 30)
    check(f'the old heuristic ({heuristic}d) understated this case ({real_days}d) by >4x',
          real_days > heuristic * 4)

    # ── Forgiveness ────────────────────────────────────────────────────────
    # A loan on an income-driven plan is written off after a payment count; it
    # does not amortise to zero, and modelling it that way told someone ten
    # months from forgiveness that they had eighteen years to go.
    def pslf_cards(made):
        fa = None if made is None else 120 - made
        return [Card(balance=8000, rate=22, minimum=200, name='Visa'),
                Card(balance=20000, rate=6, minimum=150, name='Grad loan',
                     is_pslf=True, forgive_after_months=fa)]

    visa_only = simulate_payoff([Card(balance=8000, rate=22, minimum=200)], 800)['months']
    seq = [(m, simulate_payoff(pslf_cards(m), 800)['months']) for m in (0, 30, 60, 90, 110, 119, 120)]

    check('the debt-free month falls as qualifying payments accumulate',
          all(seq[i][1] >= seq[i + 1][1] for i in range(len(seq) - 1)))
    check('forgiveness lands on the payment count, not one month either side',
          dict(seq)[0] == 120 and dict(seq)[30] == 90 and dict(seq)[60] == 60)
    # A loan awaiting forgiveness still takes its minimum every month until it
    # goes, which is money not reaching the other balances. So the rest of the
    # debt clears LATER than it would alone — the forgiven loan is free at the
    # end, not free along the way.
    check('a loan awaiting forgiveness slows the rest by taking its minimum',
          dict(seq)[110] > visa_only)
    check('once forgiveness is imminent, the other debt sets the date',
          dict(seq)[119] == visa_only and dict(seq)[110] > 120 - 110)
    check('a loan already past its payment count is gone immediately',
          dict(seq)[120] == visa_only)
    check('a forgiven loan is not paid off early — it takes minimums to the end',
          simulate_payoff(pslf_cards(0), 800)['months']
          > simulate_payoff([Card(balance=8000, rate=22, minimum=200),
                             Card(balance=20000, rate=6, minimum=150)], 800)['months'])

    unknown = simulate_payoff(pslf_cards(None), 800)
    check('an undated forgiveness loan is reported, not silently amortised',
          unknown['undated_forgiveness'] == ['Grad loan'] and not unknown['covers_all_debt'])
    check('a fully dated portfolio reports that it covers all debt',
          simulate_payoff(pslf_cards(60), 800)['covers_all_debt'])
    check('modelled forgiveness is flagged as conditional on certification',
          simulate_payoff(pslf_cards(60), 800)['conditional_on_certification']
          and not simulate_payoff([Card(balance=8000, rate=22, minimum=200)], 800)['conditional_on_certification'])
    check('a longer programme (IBR, 240 payments) forgives later than PSLF',
          simulate_payoff([Card(balance=20000, rate=6, minimum=150, is_pslf=True,
                                forgive_after_months=240 - 60)], 200)['months']
          > simulate_payoff([Card(balance=20000, rate=6, minimum=150, is_pslf=True,
                                  forgive_after_months=120 - 60)], 200)['months'])

    # ── Pillar 2's lever ───────────────────────────────────────────────────
    lev_cards = [Card(balance=8000, rate=22, minimum=200),
                 Card(balance=3000, rate=6, minimum=75)]
    for cost in (900, 2400, 5000):
        lev = offsetting_monthly_delta(lev_cards, 775, cost)
        applied = decision_impact(lev_cards, 775, monthly_delta=lev, one_time_cost=cost)
        check(f'the solved lever actually cancels a ${cost} cost',
              lev is not None and applied['months_delta'] <= 0)
        just_under = decision_impact(lev_cards, 775, monthly_delta=max(0.0, lev - 2.0),
                                     one_time_cost=cost)
        check(f'the ${cost} lever is near-minimal, not merely sufficient',
              just_under['months_delta'] >= applied['months_delta'])

    check('a bigger cost needs a bigger lever',
          offsetting_monthly_delta(lev_cards, 775, 5000)
          > offsetting_monthly_delta(lev_cards, 775, 900))
    check('nothing to offset means no lever is needed, not an unknown one',
          offsetting_monthly_delta(lev_cards, 775, 0) == 0.0)

    # A forgiveness-bound date does not move, so there is nothing to cancel —
    # the lever is zero rather than a figure implying the spend can be undone.
    fb = [Card(balance=8000, rate=22, minimum=200),
          Card(balance=20000, rate=6, minimum=150, is_pslf=True, forgive_after_months=60)]
    check('a forgiveness-bound date needs no lever',
          offsetting_monthly_delta(fb, 800, 2400) == 0.0)

    # Beyond the cap the honest answer is nothing, not a figure larger than the
    # cost itself dressed up as advice.
    check('an uncancellable cost returns None rather than an absurd figure',
          offsetting_monthly_delta(lev_cards, 775, 2400, cap=5) is None)

    # Honest-null rather than a fabricated number.
    check('an unaffordable budget returns None, not a large number',
          simulate_payoff(cards, 100) is None)
    check('decision_impact carries None through instead of inventing a delta',
          decision_impact(cards, 100)['months_delta'] is None)
    return finish()


def finish():
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    if FAIL:
        print('\nFAILURES:')
        for f in FAIL:
            print(f'  - {f}')
        return 1
    print('parity holds.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
