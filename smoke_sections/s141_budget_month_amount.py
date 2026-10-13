"""Item 26's totals pass: a budget row's amount for this month (BUDGET_MONTH_AMOUNT.md M1-M7; Rob 2026-10-02).

    M1  two figures per row: the saved amount (the only thing any write sends) and this month's figure (never written)
    M2  one server function decides; the client reads it through one helper and never recomputes
    M3  this month's totals use it; history (variance, reallocation, willingness, merge, export, reports) does not
    M4  the row says which figure is in use; un-following returns it at once - nothing was written
    M5  no figure (needs, ruled out by the household's answers, a bill the estimate does not cover): the saved amount,
        and why
    M6  "this month's budget includes it" only when the same request's total really does
    M7  the helper is shared; only 2.0's server sends month_amount, so on 1.x it is the saved amount

The crossing test for no-silent-writing: every write path sends the saved amount, and that check is proved able to
fail.
"""
import ast
import json
import re
import shutil
import subprocess
from datetime import date


def run(ctx):
    check, BASE, c, H, HJ = ctx.check, ctx.BASE, ctx.c, ctx.H, ctx.HJ
    import server
    from core import budget_month as bm, household
    from core.database import BudgetItem, AppSetting, HistorianEntry, HouseholdFact

    this = date.today().strftime('%Y-%m')
    prev = bm.bill_month(this, 1)

    # ── M1/M2 pure ────────────────────────────────────────────────────────────
    est = {'lag': 1, 'estimate': {'month': this, 'amount': 150.0, 'method': 'fit'},
           'previous': {'month': prev, 'amount': 142.0, 'method': 'fit'}}
    check('s141 M2 the bill paid this month is last month\'s service at lag 1, this month\'s at lag 0',
          bm.bill_month('2026-01', 1) == '2025-12' and bm.bill_month(this, 0) == this
          and bm.pick_estimate(est, 'gas', this)[0]['amount'] == 142.0
          and bm.pick_estimate(dict(est, lag=0), 'gas', this)[0]['amount'] == 150.0)
    e2, why2 = bm.pick_estimate(dict(est, lag=2), 'gas', this)
    eN, whyN = bm.pick_estimate({'lag': 1, 'estimate': None, 'needs': 'more bills',
                                 'previous': {'month': prev, 'method': 'none', 'needs': 'about 8 bills'}}, 'gas', this)
    eA, whyA = bm.pick_estimate({'not_applicable': 'You told us propane heats your home.'}, 'gas', this)
    check('s141 M5 no figure - a bill the estimate does not cover, a needs, or ruled out - says why, with no figure',
          e2 is None and 'does not cover' in why2 and eN is None and '8 bills' in whyN
          and eA is None and 'propane' in whyA)
    check('s141 M1 the figure: a followed estimate with an amount, else the saved amount',
          bm.month_amount(120, True, {'amount': 142.0}) == (142.0, 'estimate')
          and bm.month_amount(120, False, {'amount': 142.0}) == (120.0, 'saved')
          and bm.month_amount(120, True, None) == (120.0, 'saved'))

    # ── The server, with a stand-in estimate ─────────────────────────────────
    with ctx.dbs() as s:
        for k in household.FACTS:
            s.query(HouseholdFact).filter_by(key=k).delete()
            s.query(AppSetting).filter_by(key=k).delete()
        s.query(BudgetItem).filter(BudgetItem.category.in_(['Natural Gas', 'Electric'])).delete(synchronize_session=False)
        gas = BudgetItem(name='Natural Gas', category='Natural Gas', amount=120.0, type='expense', is_active=True)
        el = BudgetItem(name='Electric', category='Electric', amount=95.0, type='expense', is_active=True)
        s.add_all([gas, el])
        s.commit()
        gas_id, el_id = gas.id, el.id
        events_before = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()

    real_gas, real_el = server.gas_estimate, server.electric_estimate
    server.gas_estimate = lambda session, fetch=True, today=None: dict(est, kind='gas')
    server.electric_estimate = lambda session, fetch=True, today=None: {'kind': 'electric', 'lag': 1, 'estimate': None,
                                                                        'needs': 'EIA\'s outlook'}

    def follow(kind, on, lag=1):
        return c.post('/api/budget/utility-estimate/optin', headers=HJ, data=json.dumps({'kind': kind, 'on': on, 'lag': lag}))

    def months():
        return {int(k): v for k, v in ((c.get('/api/budget/month-amounts', headers=H).get_json() or {}).get('data') or {}).items()}

    try:
        follow('gas', False)
        follow('electric', False)
        m = months()
        check('s141 M1 not followed: this month\'s figure is the saved amount',
              m[gas_id]['month_amount'] == 120.0 and m[gas_id]['month_source'] == 'saved' and not m[gas_id]['month_why'])
        follow('gas', True, 1)
        follow('electric', True, 1)
        m = months()
        check('s141 M1 followed: the gas row\'s figure for this month is the estimate for the bill paid this month',
              m[gas_id]['month_amount'] == 142.0 and m[gas_id]['month_source'] == 'estimate'
              and m[gas_id]['month_from'] == 'the natural gas estimate' and m[gas_id]['month_for'] == prev)
        check('s141 M5 a followed estimate with no figure: the saved amount, and why',
              m[el_id]['month_amount'] == 95.0 and m[el_id]['month_source'] == 'saved'
              and 'electricity estimate is followed, but' in (m[el_id]['month_why'] or ''))
        boot = (c.get('/api/settings/bootstrap', headers=H).get_json() or {}).get('data') or {}
        row = next((e for e in boot.get('expenses', []) if e['id'] == gas_id), {})
        check('s141 M2 bootstrap sends each row with both figures - the saved amount untouched beside this month\'s',
              row.get('amount') == 120.0 and row.get('month_amount') == 142.0 and row.get('month_source') == 'estimate')
        from core.database import DebtAccount
        with ctx.dbs() as s:                       # debt capacity answers only with an active debt to plan against
            debt = DebtAccount(name='S141 Card', begin_balance=1000.0, current_balance=1000.0, interest_rate=20.0,
                               minimum_payment=50.0, is_active=True)
            s.add(debt)
            s.commit()
            debt_id = debt.id
        try:
            cap = (c.get('/api/debt/capacity', headers=H).get_json() or {}).get('data') or {}
        finally:
            with ctx.dbs() as s:
                s.query(DebtAccount).filter_by(id=debt_id).delete()
                s.commit()
        with ctx.dbs() as s:
            want = sum(v['month_amount'] for v in server.budget_month_amounts(s).values())
        check('s141 M3 a this-month total on the server (debt capacity) uses this month\'s figures',
              'monthly_expenses' in cap and abs(cap['monthly_expenses'] - want) < 0.01 and want > 0)
        d = (c.get('/api/budget/utility-estimate/gas', headers=H).get_json() or {}).get('data') or {}
        check('s141 M6 the gas route says, from this same request, that this month\'s budget uses it',
              d.get('budget_uses', {}).get('in_totals') is True and d['budget_uses']['month_amount'] == 142.0)
        with ctx.dbs() as s:
            set_ = household.set_household_fact(s, 'heating_fuel', 'propane', 'settings')
            s.commit()
        m = months()
        check('s141 M5 an estimate the household\'s answers rule out: the saved amount, and the reason (propane)',
              set_ and m[gas_id]['month_amount'] == 120.0 and 'propane' in (m[gas_id]['month_why'] or ''))
        with ctx.dbs() as s:
            household.set_household_fact(s, 'heating_fuel', None, 'settings')
            s.commit()
        follow('gas', False)
        m = months()
        check('s141 M4 un-following returns the row to the saved amount at once', m[gas_id]['month_amount'] == 120.0)
        with ctx.dbs() as s:
            amounts = {b.id: b.amount for b in s.query(BudgetItem).filter(BudgetItem.id.in_([gas_id, el_id]))}
            events_after = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
        check('s141 M1 NOTHING WAS WRITTEN: after following, un-following and every read, the saved amounts are as '
              'the user set them, and no budget_adjusted event was logged',
              amounts == {gas_id: 120.0, el_id: 95.0} and events_after == events_before)
    finally:
        server.gas_estimate, server.electric_estimate = real_gas, real_el
        follow('gas', False)
        follow('electric', False)
        with ctx.dbs() as s:
            s.query(BudgetItem).filter(BudgetItem.id.in_([gas_id, el_id])).delete(synchronize_session=False)
            s.commit()

    # ── The crossing test: every write path sends the saved amount ────────────
    app = ctx.app_src

    def writes_saved(src):
        sync = src[src.index('async function _syncBudgetItemsToDb('):]
        sync = sync[:sync.index('\n}\n')]
        byb = src[src.index('_byb.sandboxExpenses = S.expenses.map'):][:200]
        payloads = re.findall(r'API\.(?:patch|post|put)\([^;]*', src)
        return ('amount: item.amount' in sync and '_rowMonth' not in sync and '_sandboxAmt: e.amount' in byb
                and not any('month_amount' in p or '_rowMonth' in p for p in payloads))
    check('s141 CROSSING no-silent-writing: every write path sends the saved amount; nothing sends this month\'s figure',
          writes_saved(app))
    leaked = app.replace("const payload = { type, name: item.name, amount: item.amount,",
                         "const payload = { type, name: item.name, amount: _rowMonth(item),", 1)
    check('s141 CROSSING mutation caught: the whole-list save sending this month\'s figure', not writes_saved(leaked))

    # ── M3: which readers changed, which did not ─────────────────────────────
    def fn(name):
        m = re.search(r'^(async )?function ' + re.escape(name) + r'\(', app, re.M)
        return app[m.start():app.find('\n}\n', m.start())] if m else ''
    month_readers = ('renderBudget', '_budgetCheckShortfall', '_budgetUpdateRealismSentence', '_budgetUpdateWhatsLeft',
                     '_runScheduler', 'tripUpdateBudget', 'calcLeanMode', '_debtMaybeSuggestCommitment', 'loadDebtAdvisor',
                     'renderRetirementReadiness', 'renderWithdrawalSustainability', '_bybCurrentWhatsLeft',
                     '_findTopOverCat', '_budgetConsequenceSentence', '_budgetRenderExpenseRow')
    history_readers = ('_calcBehavioralProfile', '_findHighLeverageCategory', '_rcUpdateBudgetVsActual',
                       'updateReportPreview', '_bybBuildSandbox', '_bybCommit', '_budgetSaveExpenseBloom')
    check('s141 M3 this month\'s totals read this month\'s figure (through _rowMonth)',
          all('_rowMonth(' in fn(n) for n in month_readers))
    check('s141 M3 history, reports of any month and every write keep the saved amount (no _rowMonth)',
          all(fn(n) and '_rowMonth(' not in fn(n) for n in history_readers))
    stree = ast.parse(ctx.server_src)
    calls = {n.name for n in ast.walk(stree) if isinstance(n, ast.FunctionDef)
             and any(isinstance(x, ast.Call) and getattr(x.func, 'id', None) == 'budget_month_amounts' for x in ast.walk(n))}
    check('s141 M3 on the server only this-month readers use it - not variance, reallocation, willingness, merge, export',
          # item 71: the income check compares this month's budgeted spending with the new income
          # item 76: the Sunday check-in compares this month's spending so far with this month's budgeted spending
          # item 66: possible futures start from this month's budgeted spending
          calls <= {'budget_month_amounts_route', 'budget_utility_estimate', 'debt_capacity', 'bootstrap', '_income_change_state', '_byb_impact',
                    'checkin_get', '_futures_inputs'}
          and 'debt_capacity' in calls and 'bootstrap' in calls)

    # ── M4 / M6 / M7 in Node ─────────────────────────────────────────────────
    node = shutil.which('node')
    check('s141 node is available to run the words (skip the next if not)', bool(node))
    if node:
        path = str(BASE.joinpath('static/js/teaching/utilitytext.js')).replace('\\', '/')
        helper = fn('_rowMonth')
        prog = f"""
const U = require({json.dumps(path)});
{helper}
}}
const F = {{money: n => '$' + Number(n).toFixed(2), month: m => m, date: s => s}};
const base = {{region: {{state: 'AZ', national: false, division_name: 'Mountain'}}, saved_amount: 160,
  estimate: {{method: 'gallons', gallons: 38.4, price: 4.25, amount: 163.2, week: '2026-09-28', months_used: ['a','b','c'],
             year_ago: {{week: '2025-09-29', price: 3.80, amount: 145.92, price_part: 17.28}}}},
  area: {{kind: 'padd', label: 'the West Coast (PADD 5)'}}}};
const out = {{
  inTotals: U.gasoline(Object.assign({{}}, base, {{optin: true, budget_uses: {{in_totals: true, month_amount: 163.2}}}}), F),
  noFig: U.gasoline(Object.assign({{}}, base, {{optin: true, budget_uses: {{in_totals: false, why: 'x needs y'}}}}), F),
  notFollowed: U.gasoline(Object.assign({{}}, base, {{optin: false, budget_uses: {{in_totals: false}}}}), F),
  lts: [_rowMonth({{amount: 120}}), _rowMonth({{amount: 120, month_amount: 142}}), _rowMonth({{amount: '95.5', month_amount: null}})],
}};
console.log(JSON.stringify(out));
"""
        r = subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8', timeout=30)
        try:
            o = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                              # noqa: BLE001 - reported below
            o = {}
            print('        node:', r.stderr[:400])
        it, nf, no = o.get('inTotals', {}), o.get('noFig', {}), o.get('notFollowed', {})
        check('s141 M4 followed and used: the card says this month\'s budget uses the estimate, in place of the saved amount',
              any("This month's budget uses this estimate, $163.20, in place of your saved Gasoline / Diesel budget of $160.00." == l
                  for l in it.get('lines', [])))
        check('s141 M6 the report says the budget includes it only when it does',
              "this month's budget includes the estimate built on it" in (it.get('statement') or '')
              and 'includes' not in (nf.get('statement') or '') and 'includes' not in (no.get('statement') or ''))
        check('s141 M5 followed without a figure: the saved amount, and why',
              any(l.startswith("You follow this estimate, but this month's budget uses your saved") and 'x needs y' in l
                  for l in nf.get('lines', [])))
        check('s141 M7 the shared helper: no month figure (1.x) means the saved amount; a month figure is used as sent',
              o.get('lts') == [120, 142, 95.5])
