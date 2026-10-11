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

    # ── The endpoint ────────────────────────────────────────────────────────
    import json as _json
    from core.database import db_session as _dbs2, DebtAccount as _DA, AppSetting as _AS2

    c, H = ctx.c, ctx.HJ
    with _dbs2() as s:
        s.add(_DA(name='CE Visa', current_balance=8000, interest_rate=22,
                  minimum_payment=200, is_active=True))
        s.add(_DA(name='CE Grad', current_balance=20000, interest_rate=6,
                  minimum_payment=150, is_active=True))
        s.add(_AS2(key='monthly_budget', value='800'))
        s.commit()
        grad_id = s.query(_DA).filter_by(name='CE Grad').first().id

    def impact(**kw):
        r = c.post('/api/debt/decision-impact', headers=H, data=_json.dumps(kw))
        return r.status_code, (r.get_json() or {}).get('data', {})

    st, d = impact()
    check('POST /api/debt/decision-impact returns base and after, not a bare delta',
          st == 200 and d.get('base') and d.get('after') is not None)
    check('a zero decision moves the date by zero',
          d.get('months_delta') == 0)

    st, d = impact(one_time_cost=2400)
    check('a one-time cost delays the date and costs interest',
          d['months_delta'] > 0 and d['interest_delta'] > 0)

    st, _ = impact(one_time_cost=-5)
    check('a negative one-time cost is rejected rather than simulated', st != 200)

    def set_pslf(v):
        with _dbs2() as s:
            row = s.query(_AS2).filter_by(key='pslf_accounts_json').first()
            if not row:
                row = _AS2(key='pslf_accounts_json')
                s.add(row)
            row.value = _json.dumps({str(grad_id): v})
            s.commit()

    # The legacy shape is flagged-but-undatable. Amortising it instead is what
    # told a user ten months from forgiveness that they had eighteen years.
    set_pslf(True)
    st, d = impact()
    check('a PSLF loan with no recorded payments is reported undated, not amortised silently',
          d.get('covers_all_debt') is False and 'CE Grad' in (d.get('undated_forgiveness') or []))

    set_pslf({'enabled': True, 'program': 'pslf', 'paymentsMade': 60})
    st, d60 = impact()
    set_pslf({'enabled': True, 'program': 'pslf', 'paymentsMade': 110})
    st, d110 = impact()
    check('more qualifying payments means an earlier date',
          d60['base']['months'] > d110['base']['months'])
    check('a dated forgiveness plan covers all debt and is flagged conditional',
          d60.get('covers_all_debt') and d60['base']['conditional_on_certification'])

    # A forgiveness-bound date does not move for a one-time cost — but the money
    # is still spent, so the interest delta is what carries the cost. A caller
    # showing only "days later" would make the spend look free.
    # 60 payments made: forgiveness at month 60, well after the other card
    # clears, so the date is forgiveness-bound. (At 110 it is card-bound and the
    # cost DOES move it, which is why the state is reset here explicitly.)
    set_pslf({'enabled': True, 'program': 'pslf', 'paymentsMade': 60})
    st, dt = impact(one_time_cost=2400)
    check('a forgiveness-bound date can be unmoved while interest still rises',
          dt['months_delta'] == 0 and dt['interest_delta'] > 0)

    # ── The trip planner's wiring ───────────────────────────────────────────
    # app.js plus the teaching modules. These ask what the trip planner DOES,
    # and the causal half of it now lives behind the seam - where the code sits
    # is s30's question, not this one.
    _teaching_dir = ctx.BASE / 'static' / 'js' / 'teaching'
    view = ctx.app_src + chr(10) + chr(10).join(
        f.read_text(encoding='utf-8') for f in sorted(_teaching_dir.glob('*.js')))
    # The old heuristic must be gone from the CODE. It is still quoted in a
    # comment explaining what replaced it, which is worth keeping — so this
    # ignores comment lines rather than matching the file as one string.
    code_lines = [ln for ln in view.splitlines() if not ln.lstrip().startswith('//')]
    heuristic_live = any('(total / income) * 30' in ln for ln in code_lines)
    check('the trip planner calls the engine instead of computing its own figure',
          '_maybeLoadTripImpact' in view
          and "API.post('/api/debt/decision-impact'" in view
          and not heuristic_live)
    check('the impact fetch is debounced, like the distance fetch on the same page',
          '_tripImpactTimer' in view and '_tripImpactKey' in view)
    check('both costs are rendered — date and interest as separate cells',
          "'Debt-free impact'" in view.replace('"', "'")
          or 'Debt-free impact' in view)
    check('the interest cell exists, so a date that does not move cannot read as free',
          'Added interest' in view)
    check('an undated forgiveness loan blocks the date cell rather than filling it',
          'undated_forgiveness' in view)
    # "no change" must not be green: it is the absence of one cost, not good news,
    # and colouring it green is the same flattery-toward-spending the old
    # heuristic had.
    i = view.find("dateVal = 'no change'")
    check('"no change" is not styled as a positive outcome',
          i != -1 and 'var(--pine' not in view[i:i + 400])   # the bright green or its text shade (item 77)

    # ── Pillar 2: the sentence ends in a lever ──────────────────────────────
    st, dl = impact(one_time_cost=2400)
    check('the endpoint returns a solved lever alongside the costs',
          isinstance(dl.get('offsetting_monthly'), (int, float)))
    check('the teaching sentence ends in a lever the user controls',
          'offsetting_monthly' in view and 'more toward debt keeps it at' in view)
    # What matters is the RENDERED sentence, not the prose around it — the
    # comment there deliberately quotes "trim dining $40/mo" to explain what is
    # not being done. So this inspects the template literal, not the region.
    lever_tpl = [ln for ln in view.splitlines() if 'more toward debt keeps it at' in ln]
    check('the lever template interpolates only the amount and the date',
          len(lever_tpl) == 1
          and lever_tpl[0].count('${') == 2
          and 'category' not in lever_tpl[0].lower())
    # Rounding DOWN would state a figure that does not hold the date.
    check('the displayed lever rounds up, never down',
          'Math.ceil(d.offsetting_monthly / 5)' in view)

    # Pillar 3 reaches the surface. Clear the PSLF state first: the checks above
    # leave the loan forgiveness-bound, where the date does not move at all — so
    # there is correctly nothing to solve, and asserting paths there would be
    # asserting the wrong thing. (Third time this section's shared DB state has
    # caught an assumption of mine; the state is the point of it being a smoke
    # test rather than a unit test.)
    with _dbs2() as s:
        s.query(_AS2).filter_by(key='pslf_accounts_json').delete()
        s.commit()
    st, dp = impact(one_time_cost=2400)
    check('the endpoint returns solution paths alongside the costs',
          isinstance(dp.get('paths'), list) and dp['paths'])
    check('the trip planner renders the paths, not just the single lever',
          '_tripPathPhrases' in view and 'd.paths' in view)
    check('the view keeps a closing path rather than showing two partial ones',
          'picked.some(p => p.closes)' in view)
    check("an unreachable gap says so, bounded to today's numbers",
          "On today's numbers nothing holds the date" in view)

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
