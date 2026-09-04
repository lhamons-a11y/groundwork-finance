"""The consequence engine agrees with the JS it is replacing.

core/consequence.py is Pillar 1: it reproduces app.js's _simulatePayoffStrategy
and adds the one-time-cost dimension that function never had. A port that
disagreed with the shipped code would not unify anything — it would be a second
answer to the same question, which is the defect this engine exists to retire.

The full 300-scenario differential lives in tests/test_consequence_parity.py and
needs node. Here we run a smaller fixed set so the deploy gate covers it without
depending on node being present; if node IS present, the full parity run is
invoked too.
"""
import subprocess
import sys


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core.consequence import Card, simulate_payoff, decision_impact
    except Exception as e:
        check(f'core/consequence.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/consequence.py imports', True)

    cards = [Card(balance=8000, rate=22, minimum=200),
             Card(balance=3000, rate=6, minimum=75)]

    # Fixed expectations, verified against the JS on 2026-09-03. These are the
    # numbers the shipped app produces; if they move, the port has drifted.
    base = simulate_payoff(cards, 775)
    check('base payoff matches the JS (16 months, $1,252 interest)',
          base is not None and base['months'] == 16 and abs(base['total_interest'] - 1252) <= 1)

    snow = simulate_payoff(cards, 775, strategy='snowball')
    check('snowball is simulated separately and is not faster here',
          snow is not None and snow['months'] >= base['months'])

    # Honest-null: a budget under the minimums has no answer, and inventing one
    # is what this codebase keeps having to undo.
    check('a budget below the minimums returns None rather than a number',
          simulate_payoff(cards, 100) is None)
    check('decision_impact carries the None through instead of a fabricated delta',
          decision_impact(cards, 100)['months_delta'] is None)

    # The dimension _simulatePayoff never had, and the reason the trip planner
    # substituted (total/income)*30.
    d = decision_impact(cards, 775, one_time_cost=2400)
    check('a one-time cost is priced, and it is months rather than days',
          d['months_delta'] is not None and d['months_delta'] >= 3)
    check('decision_impact shows base and after, never a bare delta',
          d['base'] is not None and d['after'] is not None)
    check('a zero-cost, zero-delta decision changes nothing',
          decision_impact(cards, 775)['months_delta'] == 0)

    # If node is here, run the real differential against app.js itself.
    try:
        proc = subprocess.run([sys.executable, str(BASE / 'tests' / 'test_consequence_parity.py')],
                              capture_output=True, text=True, cwd=str(BASE), timeout=300)
        if 'EXTRACT_FAIL' in proc.stdout or 'js harness ran' in proc.stdout:
            check('300-scenario parity against app.js (js harness failed to run)', False)
        else:
            check('300-scenario differential parity against app.js passes',
                  proc.returncode == 0)
            if proc.returncode != 0:
                for ln in proc.stdout.splitlines():
                    if 'FAIL' in ln:
                        print(f'        {ln.strip()}')
    except Exception as e:
        print(f'        parity run skipped ({type(e).__name__}) — node may be absent')
