// Math audit, half 1: the raw records, and every figure the app shows, from a dev server with the sample household.
//   node math_collect.mjs <app url> <out.json>
// Half 2 (math_check.py) recomputes the figures from the raw records alone, sharing no code with Groundwork.
import { launch, newPage, sleep } from '../site_video/cdp.mjs';
import { openSample } from '../site_video/app.mjs';
import { writeFileSync } from 'node:fs';

const [APP, OUT] = process.argv.slice(2);
process.env.GW_VIDEO_APP = APP;
const chrome = await launch({ port: 9345 });
try {
  const page = await openSample(chrome);
  await page.goto(APP + '/', 3000);
  const data = await page.eval(`(async () => {
    const H = {'X-GW-Token': window.GW_SESSION_TOKEN || ''};
    const get = (u) => fetch(u, {headers: H}).then(r => r.json()).then(j => j.data ?? j).catch(e => ({error: String(e)}));
    const post = (u, b) => fetch(u, {method: 'POST', headers: {...H, 'Content-Type': 'application/json'}, body: JSON.stringify(b)}).then(r => r.json()).then(j => j.data ?? j);
    const wait = (ms) => new Promise(r => setTimeout(r, ms));
    const text = async (view, ms = 2500) => { showView(view); await wait(ms); return document.getElementById('view-' + view).innerText; };
    const raw = {
      transactions: await get('/api/transactions?per_page=100000'),
      accounts: await get('/api/accounts/with-balances'),
      debts: await get('/api/debt'),
      budget_items: await get('/api/budget/items'),
      settings: await get('/api/settings'),
      holdings: await get('/api/investments/positions'),
      investment_txns: await get('/api/investments/transactions'),
      today: _localISODate(),     // the app's own local date, not UTC
    };
    const shown = {};
    shown.dashboard = await text('dashboard', 3500);
    shown.budget = await text('budget', 3000);
    shown.debt = await text('debt', 3500);
    shown.networth = await text('networth', 3000);
    shown.investments = await text('investments', 3500);
    // the client's own figures behind those pages
    shown.client = {
      incomes: S.incomes, expenses: S.expenses.map(e => ({name: e.name, cat: e.cat, amount: e.amount, freq: e.freq || e.frequency})),
      monthlyBudget: _getMonthlyBudget(), saved: S.monthlyBudgetSaved, debtMethod: S.debtMethod,
      payoff0: _simulatePayoff(0), debtMonthPlan: _debtMonthPlan(),
      cards: S.debtCards.map(c => ({name: c.name, bal: _cardBal(c), rate: c.rate, min: c.minimum, type: c.debtType, end: c.endDate, paid: c.paidInFull})),
    };
    // the server engine's answers
    shown.engine = {
      base: await post('/api/debt/decision-impact', {monthly_delta: 0}),
      plus200: await post('/api/debt/decision-impact', {monthly_delta: 200}),
      trip591: await post('/api/debt/decision-impact', {one_time_cost: 591}),
      snowball: await post('/api/debt/simulate', {strategy: 'snowball'}).catch(e => String(e)),
    };
    return {raw, shown};
  })()`);
  writeFileSync(OUT, JSON.stringify(data, null, 1));
  console.log('collected', Object.keys(data.raw).map(k => k + ':' + (Array.isArray(data.raw[k]) ? data.raw[k].length : typeof data.raw[k])).join(' '));
} finally { await chrome.close(); }
