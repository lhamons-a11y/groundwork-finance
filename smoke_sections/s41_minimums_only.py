"""V11: "minimums only" has one meaning everywhere, and a savings line shows only when the math proves it.

The Debt Payoff report's card read "Saved vs minimums - $297.52 - your strategy is
working" on three test cards whose net was -$2,642: it summed each debt's gains
against today's calculated minimum, frozen for life, and dropped its losses; and
"working" is a verdict (G5). Measuring it found "minimums only" meant four things:
that; the Budget page's (V10: the engine at today's minimum total, rolled over -
a plan, not minimums); the Debt page's (each minimum as issuers calculate it,
falling with the balance, nothing rolled over); and onboarding's (the engine
again). Rob chose one true meaning: the Debt page's, now _minimumsOnly, used by
every figure. The function runs under node, checked against an independent
Python re-implementation (two processes, one answer).
"""
import json
import subprocess
from pathlib import Path


def _extract(src, name):
    s = src.index('function ' + name + '(')
    i = src.index('{', s)
    d = 0
    for p in range(i, len(src)):
        if src[p] == '{':
            d += 1
        elif src[p] == '}':
            d -= 1
            if d == 0:
                return src[s:p + 1]
    raise ValueError('unbalanced ' + name)


def _py_minimums_only(data):
    """An independent re-implementation of issuer-style minimums only."""
    bals, m, ti = [c['balance'] for c in data], 0, 0.0
    while m < 360 and any(b > 0.01 for b in bals):
        m += 1
        for i, c in enumerate(data):
            if bals[i] <= 0:
                continue
            ic = bals[i] * c['rate'] / 1200
            revolving = c.get('debtType', 'credit') == 'credit'
            pay = max(25, bals[i] * 0.01 + ic) if revolving else c['minimum']
            if not revolving and pay <= ic:
                return None
            bals[i] += ic
            ti += ic
            bals[i] = max(0, bals[i] - min(pay, bals[i]))
    return {'months': m, 'totalInterest': round(ti), 'capped': any(b > 0.01 for b in bals)}


def run(ctx):
    check = ctx.check
    app_js = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')

    three = [{'balance': 8000, 'rate': 24, 'minimum': 200, 'debtType': 'credit'},
             {'balance': 1500, 'rate': 12, 'minimum': 50, 'debtType': 'credit'},
             {'balance': 4000, 'rate': 18, 'minimum': 100, 'debtType': 'credit'}]
    loan = [{'balance': 20000, 'rate': 7, 'minimum': 400, 'debtType': 'loan'}]
    stuck = [{'balance': 5000, 'rate': 24, 'minimum': 90, 'debtType': 'loan'}]
    harness = _extract(app_js, '_minimumsOnly') + '\nconsole.log(JSON.stringify(' + json.dumps(
        [three, loan, stuck]) + '.map(_minimumsOnly)));'
    try:
        js = json.loads(subprocess.run(['node', '-e', harness], capture_output=True, text=True,
                                       encoding='utf-8', timeout=60).stdout)
    except Exception as e:                      # noqa: BLE001
        js = [None, None, 'failed']
        print(f'        node failed: {e}')

    py = [_py_minimums_only(d) for d in (three, loan, stuck)]
    check('V11: minimums only, run in the app and re-implemented independently, gives one answer',
          js == py)
    t = js[0] or {}
    check('on the three test cards: 281 months and $20,667 of interest - so the snowball plan ($4,195) is $16,472 less, not $297.52',
          t.get('months') == 281 and t.get('totalInterest') == 20667 and t.get('capped') is False
          and t.get('totalInterest') - 4195 == 16472)
    check('a loan keeps its real payment, and one that cannot amortize has no baseline (null) - nothing is claimed',
          (js[1] or {}).get('capped') is False and js[2] is None)

    check('the Debt page\'s own loop is now the shared function, not a second copy',
          'const minResult = (function(){' not in app_js and 'const minResult = _minimumsOnly(data);' in app_js)
    check('every minimums-only figure uses it: Debt page, Budget forecast, report total and rows, Budget editor, onboarding',
          app_js.count('_minimumsOnly(') >= 7)
    check('the report no longer sums each debt\'s gains and drops its losses',
          'cardData.reduce((s,d)=>s+d.intSaved,0)' not in app_js and 'totalIntSaved' not in app_js)
    check('its verdict is gone: no "your strategy is working", no "Saved vs minimums"',
          'your strategy is working' not in app_js and '>Saved vs minimums<' not in app_js)
    rep = _extract(app_js, '_rcRenderDebtPayoff')
    check('the report states the plan against minimums only as a fact, and only when both runs finish and the plan is ahead',
          "plan && minsOnly && !minsOnly.capped" in rep
          and '${planSaves>0?' in rep and 'Less interest than minimums only' in rep
          and 'against paying only each minimum as issuers calculate it' in rep)
    check('a saving is never worked from a run cut off at 30 years - the Debt page, the Budget page and the report all check',
          'minResult && !minResult.capped' in app_js and 'mins && !mins.capped' in app_js
          and "minDate = minNever ? 'not within 30 years'" in app_js)
    ob = _extract(app_js, 'obCalcDebt')
    check('onboarding\'s "At minimums" is the same meaning, not the engine rolled over',
          '_minimumsOnly(rows.map(' in ob and '_simAsk(' not in ob)
    check('the Budget page no longer asks the engine for a "minimums" budget rolled over',
          'function _minimumsBudget' not in app_js)

    # The server's side of the same words: the trophy proof. Its twin must agree
    # with the page's function across processes, and the proof must use it.
    from core.consequence import minimums_only
    srv = [minimums_only([{**d, 'debt_type': d['debtType']} for d in x]) for x in (three, loan, stuck)]
    srv = [None if r is None else {'months': r['months'], 'totalInterest': r['total_interest'],
                                   'capped': r['capped']} for r in srv]
    check('the server\'s minimums_only (trophy proof) gives the page\'s answer on the same debts',
          srv == js)
    server_src = (Path(__file__).resolve().parent.parent / 'server.py').read_text(encoding='utf-8')
    check('the $1,000 interest trophy is proven against minimums only, not the engine rolled over',
          'floor = minimums_only([' in server_src and 'floor = _sim(cards, minimum_total' not in server_src
          and "if plan and floor and not floor['capped']:" in server_src)
