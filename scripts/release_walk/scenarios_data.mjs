export default [
  { name: 'Ledger: edit a transaction (category), then delete it',
    steps: `showView('ledger'); await wait(1500); openAddModal(); await wait(500);
      typeIn('txnDate', new Date().toISOString().slice(0, 10)); typeIn('txnType', 'debit'); typeIn('txnDesc', 'Scenario Coffee Cart');
      typeIn('txnAmount', '4.75'); typeIn('txnCategory', 'Coffee Shops'); typeIn('txnAccount', 'Everyday Checking'); await saveTransaction(); await wait(1500);
      const t = await api('/api/transactions?limit=2000'); const list = Array.isArray(t) ? t : (t.transactions || t.items || []);
      const row = list.find(x => x.description === 'Scenario Coffee Cart'); if (!row) return 'not saved';
      const r = await fetch('/api/transactions/' + row.id, {method: 'PATCH', headers: {'Content-Type': 'application/json', 'X-GW-Token': GW_SESSION_TOKEN}, body: JSON.stringify({category: 'Restaurants'})});
      return {id: row.id, edit: r.status + ' ' + (await r.text()).slice(0, 100)};`,
    check: `const t = await api('/api/transactions?limit=2000'); const list = Array.isArray(t) ? t : (t.transactions || t.items || []);
      const row = list.find(x => x.description === 'Scenario Coffee Cart');
      const d = row && await fetch('/api/transactions/' + row.id, {method: 'DELETE', headers: {'X-GW-Token': GW_SESSION_TOKEN}});
      const t2 = await api('/api/transactions?limit=2000'); const l2 = Array.isArray(t2) ? t2 : (t2.transactions || t2.items || []);
      return {categoryAfterEdit: row && row.category, deleted: d && d.status, gone: !l2.some(x => x.description === 'Scenario Coffee Cart')};` },

  { name: 'Debt Payoff: add a card with its minimum',
    steps: `showView('debt'); await wait(2000); press('+ Add card or loan'); await wait(800);
      const empty = () => [...document.querySelectorAll('#view-debt input')].filter(e => vis(e) && !e.value && e.type !== 'checkbox' && e.type !== 'range' && !/notes/i.test(e.placeholder || ''));
      typeIn(empty().find(e => /name/i.test(e.placeholder || '')), 'Scenario Store Card'); await wait(300);
      const nums = empty();
      const rate = nums.find(e => /dcRate/.test(e.id)), min = nums.find(e => /e\\.g\\. 60/.test(e.placeholder || '')), due = nums.find(e => /e\\.g\\. 15/.test(e.placeholder || ''));
      const bal = nums.find(e => e !== rate && e !== min && e !== due && !/bend/.test(e.id));
      if (bal) typeIn(bal, '1800'); if (rate) typeIn(rate, '26.99'); if (min) typeIn(min, '55'); if (due) typeIn(due, '9');
      await wait(2500); return {bal: !!bal, rate: !!rate, min: !!min, due: !!due};`,
    check: `const d = await api('/api/debt'); const x = d.find(c => (c.name || '') === 'Scenario Store Card');
      showView('debt'); await wait(2500);
      return {stored: !!x, balance: x && (x.current_balance ?? x.balance), rate: x && x.interest_rate, minimum: x && x.minimum_payment, due: x && x.due_day,
        onPage: document.getElementById('view-debt').innerText.includes('Scenario Store Card')};` },

  { name: 'Settings: home state by its name',
    steps: `showView('settings'); await wait(1500); const s = document.getElementById('settingsHomeState');
      const o = [...s.options].find(o => o.text === 'Ohio'); s.value = o.value; s.dispatchEvent(new Event('change', {bubbles: true}));
      saveSettings(); await wait(1200); return 'chose ' + o.value;`,
    check: `const h = await api('/api/settings/household'); showView('settings'); await wait(1500);
      return {fact: JSON.stringify(h.home_state || h).slice(0, 160), fieldAfterReload: document.getElementById('settingsHomeState').value};` },

  { name: 'Investments: add a holding',
    steps: `showView('investments'); await wait(2000); openAddHoldingModal(); await wait(700);
      typeIn('holdingTicker', 'VTI'); typeIn('holdingShares', '12'); typeIn('holdingCostBasis', '240'); typeIn('holdingDate', '2026-06-01');
      typeIn('holdingCurrentPrice', '275'); await saveHolding(); await wait(2000);
      const m = document.getElementById('addHoldingModal'); return m.classList.contains('hidden') ? 'saved' : 'still open: ' + m.innerText.slice(0, 200);`,
    check: `showView('investments'); await wait(2500);
      return {onPage: document.getElementById('view-investments').innerText.includes('VTI')};` },

  { name: 'Before You Buy: a purchase, all the way to the decision',
    steps: `showView('byb'); await wait(1500); openBYBWizard(); await wait(600);
      _bybSelectType('purchase', [...document.querySelectorAll('[onclick*=_bybSelectType]')].find(e => /purchase/.test(e.getAttribute('onclick')))); await wait(500);
      typeIn('bybItemName', 'Scenario Laptop'); const f = fields(document.getElementById('view-byb')).join(' ');
      const price = [...document.querySelectorAll('#view-byb input')].find(e => vis(e) && !e.value && e.type === 'number');
      if (price) typeIn(price, '1200');
      await wait(500); try { _bybGoStep(3); } catch (e) { return 'step3: ' + e.message; } await wait(2000);
      const btns = [...document.querySelectorAll('#view-byb button')].filter(vis).map(b => b.innerText.trim()).filter(Boolean);
      return {fields: f.slice(0, 300), price: price && (price.id || price.placeholder), result: document.getElementById('view-byb').innerText.replace(/\\n+/g, ' | ').slice(0, 600), buttons: btns.slice(0, 14)};`,
    check: `showView('byb'); await wait(1500); return {onPage: document.getElementById('view-byb').innerText.includes('Scenario Laptop')};` },

  { name: 'Trip Planner: drive, budget, keep the trip',
    steps: `showView('trip'); await wait(1800); setTripMode('drive'); await wait(300);
      typeIn('tripDestination', 'Columbus, OH'); typeIn('tripOrigin', 'Millbrook, OH'); typeIn('tripVehicle', 'Honda Civic'); typeIn('tripVehicleYear', '2019'); typeIn('tripMPG', '32');
      try { setTripFunding('save'); } catch (e) {}
      await generateTripBudget(); await wait(5000);
      const txt = document.getElementById('view-trip').innerText;
      const keep = [...document.querySelectorAll('#view-trip button')].find(b => vis(b) && /going on this trip/i.test(b.innerText));
      if (keep) { keep.click(); await wait(2500); }
      const i = txt.indexOf('Columbus');
      return {budget: txt.replace(/\\n+/g, ' | ').slice(Math.max(0, i - 50), i + 600), kept: !!keep};`,
    check: `showView('trip'); await wait(1500); try { press('Your trips'); } catch (e) {} await wait(1500);
      return {listed: document.getElementById('view-trip').innerText.includes('Columbus')};` },
];
