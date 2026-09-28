"""V10: the Budget page's payoff forecast is the plan.

The Budget page, its two-scenario line and the Debt Payoff report ran their own
payoff maths (_budgetAvalancheSequence): always avalanche, whatever plan the user
chose, and with a mortgage's whole payment - escrow too - taken as principal. On a
$180,000 mortgage and a card it said 130 months where the engine says 194. They
now show the Debt page's own engine run, and "minimums only" is the same engine
at a budget equal to the minimums. The Budget-page functions run for real under
node, extracted from app.js, over a stubbed engine; the engine itself is asked
through the route.
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


def run(ctx):
    check = ctx.check
    app_js = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')

    harness = '\n'.join([
        _extract(app_js, '_minimumsOnly'),
        _extract(app_js, '_budgetPlanForecast'),
        _extract(app_js, '_budgetTwoScenarioComparison'),
        """
const fmt = v => '$' + Number(v).toFixed(2);
function _payoffDateLabel(m) { return 'M' + m; }
function _getMonthlyBudget() { return 600; }
let method = 'snowball', cards = [], plan, mins, asked = [];
function _planName() { return method; }
function _simCards() { return cards; }
function _simulatePayoff(extra) { return plan; }
let data = [];
function getCardData() { return data; }
global.S = { debtCards: [] };
const card = { id: 1, balance: 5000, rate: 22, minimum: 150, non_principal: 0 };
const home = { id: 2, balance: 180000, rate: 6.5, minimum: 1200, non_principal: 450 };
const out = {};
cards = [card, home]; plan = { months: 30, totalInterest: 900 };
data = [{ balance: 5000, rate: 22, minimum: 150, debtType: 'credit' }];
out.minsOnly = _minimumsOnly(data);
out.snow = _budgetTwoScenarioComparison([1]);
method = 'avalanche';
out.aval = _budgetTwoScenarioComparison([1]);
plan = undefined; out.pending = _budgetTwoScenarioComparison([1]);
plan = null;      out.uncovered = _budgetTwoScenarioComparison([1]);
plan = { months: 30, totalInterest: 900 };
data = [{ balance: 400000, rate: 9, minimum: 3050, debtType: 'loan' }];   // a loan that runs past 30 years
out.capped = _budgetTwoScenarioComparison([1]);
data = [{ balance: 5000, rate: 24, minimum: 90, debtType: 'loan' }];      // cannot amortize: no honest baseline
out.never = _budgetTwoScenarioComparison([1]);
cards = []; out.none = _budgetPlanForecast();
console.log(JSON.stringify(out));
"""])
    try:
        proc = subprocess.run(['node', '-e', harness], capture_output=True, text=True, timeout=60)
        res = json.loads(proc.stdout.strip() or '{}')
        if proc.returncode:
            print('        node:', proc.stderr[-400:])
    except Exception as e:                      # noqa: BLE001
        res = {}
        print(f'        node harness failed: {e}')

    snow = res.get('snow') or ''
    check('V10: the Budget page\'s two-scenario line names the chosen plan (snowball) and shows its date',
          'Your snowball plan at $600.00/mo' in snow and '>M30<' in snow and 'Avalanche' not in snow)
    mo = (res.get('minsOnly') or {}).get('months')
    check('V11: the minimums-only line is the one shared meaning (_minimumsOnly: issuer-style falling minimum, nothing rolled over)',
          bool(mo) and f'>M{mo}<' in snow and (res.get('minsOnly') or {}).get('capped') is False)
    check('an avalanche plan is named as avalanche',
          'Your avalanche plan at' in (res.get('aval') or ''))
    check('while the engine is working, or the payments do not cover the minimums, it says nothing rather than a guess',
          res.get('pending') == '' and res.get('uncovered') == '')
    check('a minimums run that reaches the 30-year horizon says so, not a date',
          'not within 30 years' in (res.get('capped') or ''))
    check('a loan whose payment cannot amortize has no honest baseline, so nothing is claimed',
          res.get('never') == '')
    check('with no debts there is no plan and no minimums run',
          res.get('none') == {'plan': None, 'mins': None})

    # The engine, through the route, on the case the retired code got wrong.
    r = ctx.c.post('/api/debt/simulate', headers=ctx.HJ, data=json.dumps({
        'cards': [{'id': 1, 'name': 'Home', 'balance': 180000, 'rate': 6.5, 'minimum': 1200},
                  {'id': 2, 'name': 'Card', 'balance': 5000, 'rate': 22, 'minimum': 150}],
        'budget': 2000 - 450, 'extra': 0, 'strategy': 'snowball'}))
    months = (((r.get_json(silent=True) or {}).get('data') or {}).get('result') or {}).get('months')
    check('the engine the Budget page now shows leaves a mortgage\'s escrow out (194 months, not the retired 130)',
          months == 194)

    summ = _extract(app_js, '_budgetRenderDebtSummary')
    check('the Budget summary\'s forecast is the plan, named',
          'Payoff forecast (your ${_planName()} plan, ${fmt(_getMonthlyBudget())}/mo): ${_payoffDateLabel(plan.months)}' in summ
          and '_budgetPlanForecast()' in summ)
    rep = _extract(app_js, '_rcRenderDebtPayoff')
    check('the Debt Payoff report waits for the plan\'s run and dates the sequence from it',
          'const plan          = await _planAwait();' in rep
          and "plan?.months ? _payoffDateLabel(plan.months) : '—'" in rep
          and 'Payoff sequence — your ${_planName()} plan' in rep and 'avalanche order' not in rep)
    wait = _extract(app_js, '_planAwait')
    check('the report\'s run is the Debt page\'s: the same cards, budget and key',
          'const key = _simKey(cards, budget, 0, strategy);' in wait and '_simCards()' in wait
          and '_getMonthlyBudget()' in wait and '_planName()' in wait)
    check('the Budget page\'s own avalanche is gone',
          'function _budgetAvalancheSequence' not in app_js and '_budgetAvalancheSequence(' not in app_js)
