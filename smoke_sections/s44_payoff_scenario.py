"""V4: a debt's payoff month belongs to a plan, and wherever one is shown its scenario is named.

The collapsed debt row used to project each card on its own - its payment plus
"a share of extra" if it was the target - which ignored rollover: when one debt
clears, its payment moves to the next. So every debt but the first target
showed a later month than the plan the debt-free date comes from. Now the row
reads the plan's own per-debt month (the engine's cleared_at, from the same run
as the debt-free date), the Debt page says once which plan its dates belong to,
the dashboard names the plan, and projections of one debt at its own payment say
so.
"""
from pathlib import Path


def _solo_months(balance, apr, payment):
    r = apr / 1200
    months = 0
    while balance > 0.005 and months < 1200:
        balance = balance * (1 + r) - payment
        months += 1
    return months


def run(ctx):
    check, c, HJ = ctx.check, ctx.c, ctx.HJ

    cards = [
        {'id': 1, 'name': 'V4 Card A', 'balance': 3800, 'rate': 24.9, 'minimum': 117},
        {'id': 2, 'name': 'V4 Card B', 'balance': 1200, 'rate': 18.9, 'minimum': 31},
    ]
    r = c.post('/api/debt/simulate', headers=HJ,
               json={'cards': cards, 'budget': 500, 'extra': 0, 'strategy': 'avalanche'})
    res = ((r.get_json() or {}).get('data') or r.get_json() or {}).get('result') or {}
    cleared = res.get('clearedAt') or {}
    b_plan = (cleared.get('V4 Card B') or {}).get('month')
    b_solo = _solo_months(1200, 18.9, 31)
    check('V4: the plan reports the month each debt clears (the engine\'s cleared_at)',
          bool(r.status_code == 200 and b_plan is not None and (cleared.get('V4 Card A') or {}).get('month')))
    check('and under the plan the second debt clears well before it would on its own payment '
          '(rollover), which the old row date ignored',
          b_plan is not None and b_plan < b_solo - 12)
    check('and the last debt to clear is the household debt-free month',
          b_plan is not None and max(v['month'] for v in cleared.values()) == res.get('months'))

    app_js = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    check('the collapsed row reads the plan\'s month for the debt, not a solo projection',
          'const payoffMo = _planClearedMonth(c, plan);' in app_js
          and 'Approximate: project this card solo' not in app_js)
    check('and names the plan with the date',
          'title="Under ${_planScenario()}${assumed}"' in app_js)
    check('two debts sharing a name get no date rather than each other\'s',
          'if (same.length !== 1) return null;' in app_js)
    check('the Debt page says once which plan its dates belong to',
          'Payoff dates are from ${_planScenario()}. Change the plan and they change.' in app_js)
    check('the dashboard\'s debt-free date names the plan',
          '(${_planName()}, ${fmt(_getMonthlyBudget())}/mo)' in app_js)
    check('the Budget page\'s forecast names the plan it belongs to (V10: it is the plan)',
          'Payoff forecast (your ${_planName()} plan, ${fmt(_getMonthlyBudget())}/mo)' in app_js
          and 'Your ${_planName()} plan at ${fmt(_getMonthlyBudget())}/mo:' in app_js)
    check('projections of one debt at its own payment say so, in the report and the Budget editor',
          '${_payoffDateLabel(snaps.length)} at its own payment' in app_js
          and 'Payoff date at this payment alone' in app_js)
