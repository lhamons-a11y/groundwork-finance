// Before You Buy at three monthly costs, with and without a saved debt plan; a trip's cost; the "$200 more" figure.
const BYB = (amt) => `showView('byb'); await wait(1500); openBYBWizard(); await wait(600);
  _bybSelectType('purchase', [...document.querySelectorAll('[onclick*=_bybSelectType]')].find(e => /purchase/.test(e.getAttribute('onclick')))); await wait(400);
  typeIn('bybItemName', 'Scenario ${amt}'); typeIn('bybMonthlyAmount', '${amt}'); await wait(400);
  _bybGoStep(3); await wait(3500); _bybBuildComparison(); await wait(500);
  const box = document.getElementById('bybComparisonContent');
  const grid = box.querySelector('div[style*="grid-template-columns"]');
  const cells = grid ? [...grid.children].map(c => c.innerText.split('\\n').filter(Boolean).join(': ')) : [];
  const msg = (document.getElementById('bybChangeFromOriginal') || box).innerText.split('\\n').filter(Boolean).join(' | ');
  const wall = [...box.querySelectorAll('div')].map(d => d.innerText).find(t => /stays payable|would fit|No version|can't carry any|no room in them/.test(t)) || '';
  return {cells, msg: msg.slice(0, 600), wall: wall.slice(0, 300), plan: _getMonthlyBudget(), saved: S.monthlyBudgetSaved};`;

const ENGINE = (body) => `const r = await fetch('/api/debt/decision-impact', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-GW-Token': GW_SESSION_TOKEN}, body: JSON.stringify(${body})}).then(r => r.json());
  const d = r.data || r; return {baseMonths: d.base && d.base.months, afterMonths: d.after && d.after.months, monthsDelta: d.months_delta, interestDelta: d.interest_delta, honestNo: !!d.honest_no};`;

export default [
  { name: 'BYB $100/mo, plan $900 saved', steps: BYB(100), check: `return '-';` },
  { name: 'BYB $1,200/mo, plan $900 saved', steps: BYB(1200), check: `return '-';` },
  { name: 'BYB $9,000/mo, plan $900 saved', steps: BYB(9000), check: `return '-';` },
  { name: 'Engine: $200 more a month, plan $900', steps: ENGINE('{monthly_delta: 200}'), check: `return '-';` },
  { name: 'Engine: a $591 trip, plan $900', steps: ENGINE('{one_time_cost: 591}'), check: `return '-';` },
  { name: 'No saved plan', steps: `const r = await fetch('/api/settings', {method: 'PATCH', headers: {'Content-Type': 'application/json', 'X-GW-Token': GW_SESSION_TOKEN}, body: JSON.stringify({monthly_budget: ''})}); return r.status;`,
    check: `showView('debt'); await wait(3000); return {field: document.getElementById('monthlyBudget').value, saved: S.monthlyBudgetSaved, plan: _getMonthlyBudget()};` },
  { name: 'BYB $100/mo, no saved plan', steps: BYB(100), check: `return '-';` },
  { name: 'Engine: $200 more, no saved plan', steps: ENGINE('{monthly_delta: 200}'), check: `return '-';` },
  { name: 'Engine: a $591 trip, no saved plan', steps: ENGINE('{one_time_cost: 591}'), check: `return '-';` },
];
