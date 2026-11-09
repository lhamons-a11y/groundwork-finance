// Enter real data through Groundwork's own forms, reload, and check it is still there (and visible on its page).
//   node scenarios.mjs <app url> <out dir>
// On the sample household (reset first). Each scenario: steps in the page, then a check after a full reload.
import { launch, newPage, sleep } from '../site_video/cdp.mjs';
import { writeFileSync, mkdirSync } from 'node:fs';
const [APP, OUT] = process.argv.slice(2);
mkdirSync(OUT, { recursive: true });

const HELP = `
window.vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; };
window.wait = (ms) => new Promise(r => setTimeout(r, ms));
window.press = (text, root = document) => { const e = [...root.querySelectorAll('button, [onclick], a, summary, [role=tab]')]
  .filter(x => vis(x) && (x.innerText || x.value || '').trim().includes(text)).sort((a, b) => (a.innerText || '').length - (b.innerText || '').length)[0];
  if (!e) throw new Error('nothing to press: ' + text); e.click(); return true; };
window.typeIn = (el, v) => { if (typeof el === 'string') el = document.getElementById(el) || document.querySelector(el);
  if (!el) throw new Error('no field'); el.focus(); el.value = v; el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true})); el.dispatchEvent(new Event('blur', {bubbles: true})); return el; };
window.fields = (root) => [...(root || document).querySelectorAll('input, select, textarea')].filter(vis)
  .map(e => (e.id || '') + '[' + (e.placeholder || e.getAttribute('aria-label') || e.name || e.type) + ']=' + (e.value || '').slice(0, 20));
window.api = (u) => fetch(u, {headers: {'X-GW-Token': window.GW_SESSION_TOKEN || ''}}).then(r => r.json()).then(j => j.data ?? j);
window.has = (obj, text) => JSON.stringify(obj).includes(text);
`;

const SCENARIOS = [
  { name: 'Ledger: add a transaction by hand',
    steps: `showView('ledger'); await wait(1500); openAddModal(); await wait(500);
      typeIn('txnDate', new Date().toISOString().slice(0, 10)); typeIn('txnType', 'debit'); typeIn('txnDesc', 'Scenario Coffee Cart');
      typeIn('txnAmount', '4.75'); typeIn('txnCategory', 'Coffee Shops'); typeIn('txnAccount', 'Everyday Checking');
      await saveTransaction(); await wait(1500); return document.getElementById('addTxnModal').classList.contains('hidden') ? 'saved' : 'modal still open: ' + fields(document.getElementById('addTxnModal')).join(' ');`,
    check: `const t = await api('/api/transactions?limit=2000'); const list = Array.isArray(t) ? t : (t.transactions || t.items || []);
      const row = list.find(x => x.description === 'Scenario Coffee Cart');
      showView('ledger'); await wait(2000);
      return {stored: !!row, amount: row && row.amount, category: row && row.category, onPage: document.getElementById('view-ledger').innerText.includes('Scenario Coffee Cart')};` },

  { name: 'Ledger: change that transaction category, then delete it',
    steps: `const t = await api('/api/transactions?limit=2000'); const list = Array.isArray(t) ? t : (t.transactions || t.items || []);
      const row = list.find(x => x.description === 'Scenario Coffee Cart'); if (!row) return 'not there to edit';
      const r = await fetch('/api/transactions/' + row.id, {method: 'PUT', headers: {'Content-Type': 'application/json', 'X-GW-Token': GW_SESSION_TOKEN}, body: JSON.stringify({category: 'Restaurants'})});
      const after = await r.text(); const d = await fetch('/api/transactions/' + row.id, {method: 'DELETE', headers: {'X-GW-Token': GW_SESSION_TOKEN}});
      return 'edit ' + r.status + ' ' + after.slice(0, 80) + ' / delete ' + d.status;`,
    check: `const t = await api('/api/transactions?limit=2000'); const list = Array.isArray(t) ? t : (t.transactions || t.items || []);
      return {goneAfterDelete: !list.some(x => x.description === 'Scenario Coffee Cart')};` },

  { name: 'Settings: add an account',
    steps: `showView('settings'); await wait(1500); try { press('Accounts'); } catch (e) {} await wait(800); showAddAccountForm(); await wait(400);
      typeIn('acctFormName', 'Scenario Rainy Day'); typeIn('acctFormType', 'savings'); typeIn('acctFormInstitution', 'Demo Credit Union');
      await saveAccountForm(); await wait(1200); return 'saved';`,
    check: `const a = await api('/api/accounts'); const list = Array.isArray(a) ? a : a.accounts || [];
      const x = list.find(x => x.name === 'Scenario Rainy Day'); return {stored: !!x, type: x && x.type};` },

  { name: 'Debt Payoff: add a card and fill it in',
    steps: `showView('debt'); await wait(2000); const before = (await api('/api/debt')).length; press('+ Add card or loan'); await wait(800);
      const card = [...document.querySelectorAll('#view-debt .card-row, #view-debt [data-card-id], #view-debt .debt-card')].filter(vis).pop();
      const inputs = [...document.querySelectorAll('#view-debt input')].filter(e => vis(e) && !e.value && e.type !== 'checkbox' && e.type !== 'range');
      const shown = inputs.map(e => (e.placeholder || e.getAttribute('aria-label') || e.id)).join(', ');
      const pick = (re) => inputs.find(e => re.test((e.placeholder || '') + ' ' + (e.getAttribute('aria-label') || '') + ' ' + e.id + ' ' + (e.closest('label, .field, div')?.innerText || '')));
      const set = [['name|card', 'Scenario Store Card'], ['balance', '1800'], ['apr|rate', '26.99'], ['min', '55'], ['due', '9']];
      const done = []; for (const [re, v] of set) { const e = pick(new RegExp(re, 'i')); if (e) { typeIn(e, v); done.push(re); } }
      await wait(2500); return {before, fieldsSeen: shown.slice(0, 300), filled: done};`,
    check: `const d = await api('/api/debt'); const x = d.find(c => (c.name || '') === 'Scenario Store Card');
      return {stored: !!x, balance: x && (x.current_balance ?? x.balance), rate: x && x.interest_rate, minimum: x && x.minimum_payment};` },

  { name: 'Budget: add an expense line',
    steps: `showView('budget'); await wait(2000); _budgetAddExpenseBloom(); await wait(600);
      const bloom = document.querySelector('#budgetExpenseRows .bloom, #budgetExpenseRows [class*=bloom]') || document.getElementById('budgetExpenseRows').lastElementChild;
      const ins = [...bloom.querySelectorAll('input')].filter(vis);
      const name = ins.find(e => !/number/.test(e.type)) , amt = ins.find(e => e.type === 'number' || /amount|\\$/i.test(e.placeholder || ''));
      if (name) typeIn(name, 'Scenario Piano Lessons'); if (amt) typeIn(amt, '85');
      const b = [...bloom.querySelectorAll('button')].filter(vis).find(x => /save|add|done|✓/i.test(x.innerText)); const label = b && b.innerText.trim();
      if (b) b.click(); await wait(1500); return {fields: fields(bloom).join(' '), pressed: label};`,
    check: `const items = await api('/api/budget/items'); const list = Array.isArray(items) ? items : items.items || [];
      const x = list.find(i => i.name === 'Scenario Piano Lessons'); return {stored: !!x, amount: x && x.amount};` },

  { name: 'Investments: add a holding',
    steps: `showView('investments'); await wait(2000); openAddHoldingModal(); await wait(700);
      const m = [...document.querySelectorAll('.modal-overlay')].find(x => !x.classList.contains('hidden'));
      return {modal: m && m.id, fields: fields(m).join(' ')};`,
    check: `return 'see steps';` },

  { name: 'Settings: home state and debt method survive a reload',
    steps: `showView('settings'); await wait(1500); const s = document.getElementById('settingsHomeState'); if (!s) return 'no home state field';
      typeIn(s, 'Ohio'); typeIn('settingsDebtMethod', 'snowball'); saveSettings(); await wait(1200); return 'saved';`,
    check: `const s = await api('/api/settings'); return {home: s.home_state, method: s.debt_method, budgetKept: s.monthly_budget};` },

  { name: 'Before You Buy: open the wizard',
    steps: `showView('byb'); await wait(1500); openBYBWizard(); await wait(800);
      const m = [...document.querySelectorAll('.modal-overlay')].find(x => !x.classList.contains('hidden')) || document.getElementById('view-byb');
      return {fields: fields(m).join(' ').slice(0, 400)};`,
    check: `return 'see steps';` },

  { name: 'Trip Planner: what a new trip asks for',
    steps: `showView('trip'); await wait(1800); return {fields: fields(document.getElementById('view-trip')).join(' ').slice(0, 500),
      buttons: [...document.querySelectorAll('#view-trip button')].filter(vis).map(b => b.innerText.trim()).slice(0, 15)};`,
    check: `return 'see steps';` },
];

import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
// A scenario list file (scenarios_data.mjs, scenarios_byb.mjs) as the third argument; the built-in list otherwise
const LIST = process.argv[4] ? (await import(pathToFileURL(resolve(process.argv[4])).href)).default : SCENARIOS;
const chrome = await launch({ port: 9343, width: 1600, height: 1000 });
const out = [];
try {
  const page = await newPage(chrome);
  const fresh = async () => { await page.goto(APP + '/', 2500); await page.eval(HELP); };
  await fresh();
  if (await page.eval(`document.body.innerText.includes('Before you begin')`)) {
    await page.eval(`(() => { const c = [...document.querySelectorAll('input[type=checkbox]')].find(e => e.offsetParent); c && c.click(); })()`); await sleep(300);
    await page.eval(`[...document.querySelectorAll('button')].find(b => b.offsetParent && b.textContent.includes('Agree')).click()`); await sleep(1500);
  }
  const raw = (m, u) => page.eval(`fetch(${JSON.stringify(u)}, {method: '${m}', headers: {'Content-Type': 'application/json', 'X-GW-Token': GW_SESSION_TOKEN}, body: '{}'}).then(r => r.status)`);
  await raw('POST', '/api/sample/clear'); await fresh(); await raw('POST', '/api/sample/load'); await fresh();
  for (const sc of LIST) {
    const errMark = page.errors.length;
    let steps, check;
    try { await fresh(); steps = await page.eval(`(async () => { ${sc.steps} })()`); } catch (e) { steps = 'ERROR ' + e.message.slice(0, 300); }
    try { await fresh(); check = await page.eval(`(async () => { ${sc.check} })()`); } catch (e) { check = 'ERROR ' + e.message.slice(0, 300); }
    writeFileSync(`${OUT}\\${out.length}.png`, await page.shot());
    const rec = { name: sc.name, steps, check, errors: page.errors.slice(errMark) };
    out.push(rec);
    console.log(JSON.stringify(rec));
  }
} finally { await chrome.close(); }
writeFileSync(`${OUT}\\scenarios.json`, JSON.stringify(out, null, 1));
