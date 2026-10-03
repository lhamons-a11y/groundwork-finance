/*
 * Utility bill estimates on the Budget page and in the monthly report (gw 2.0/UTILITY_ESTIMATES.md, item 26).
 *
 * Teaching layer: absent from an LTS bundle by path; the 1.x Budget page keeps its benchmark line (U7).
 * The natural gas slice: a card on the Budget page with the estimate and every figure behind it, the user's choice
 * to follow it (U3), and - when they have chosen it - the forecast line in the monthly report (U4).
 * Nothing here writes a budget amount; the estimate is derived on every read (U3(a)).
 */
(function () {
  'use strict';

  function _words() {
    var m = GWTeaching._modules.filter(function (x) { return x.name === 'utilitytext'; })[0];   // loads after this file
    return m && m.mod;
  }

  function _month(m) {
    var p = String(m).split('-').map(Number);
    return new Date(p[0], p[1] - 1, 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  }
  function _day(iso) {
    var p = String(iso).split('-').map(Number);
    return new Date(p[0], p[1] - 1, p[2]).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }
  var F = { money: function (n) { return fmt(n); }, month: _month, date: _day };

  var KINDS = [
    { kind: 'gas', title: 'Natural gas estimate', id: 'gwGasEstimate' },
    { kind: 'electric', title: 'Electricity estimate', id: 'gwElecEstimate' },
    { kind: 'gasoline', title: 'Gasoline estimate', id: 'gwFuelEstimate', noLag: true },  // fill-ups aren't billed later
    { kind: 'propane', title: 'Propane estimate', id: 'gwPropaneEstimate', noLag: true },  // item 34: paid on delivery
    { kind: 'heating_oil', title: 'Heating oil estimate', id: 'gwOilEstimate', noLag: true }
  ];

  async function _load(kind) {
    try { return await API.get('/api/budget/utility-estimate/' + kind); }
    catch (e) { _gwErr(kind + ' estimate')(e); return null; }
  }

  // Shown only when the record has something for it: that utility's budget row or bills (no empty card for a home
  // without the service).
  async function _card(k) {
    var cont = g('budgetContent');
    if (!cont) return;
    var old = g(k.id);
    if (old) old.innerHTML = '<div class="card-label">' + esc(k.title) + '</div><div style="font-size:12px;color:var(--slate-2)">Loading EIA\'s outlook\u2026</div>';
    var d = await _load(k.kind);
    var W = _words();
    if (!d || !W || (!d.bills && d.saved_amount === null)) { if (old) old.remove(); return; }
    var t = W[k.kind](d, F);
    var title = (k.kind === 'gasoline' && d.fuel === 'diesel') ? 'Diesel estimate' : k.title;   // item 34 F1
    var html = '<div class="card-label">' + esc(title) + '</div>'
      + t.lines.map(function (l) { return '<div style="font-size:12px;color:var(--slate);line-height:1.7">' + esc(l) + '</div>'; }).join('')
      + '<div style="margin-top:8px;font-size:12px;color:var(--slate)">'
      + '<label><input type="checkbox" data-gw-util-optin data-kind="' + k.kind + '" ' + (d.optin ? 'checked' : '') + '> Follow this estimate</label>'
      + (k.noLag ? '' : ' \u00b7 bills pay for <select data-gw-util-lag data-kind="' + k.kind + '" style="font-size:12px">'
      + [0, 1, 2].map(function (n) {
          return '<option value="' + n + '"' + (d.lag === n ? ' selected' : '') + '>' + ['the same month', 'the month before', 'two months before'][n] + '</option>';
        }).join('') + '</select>') + '</div>'
      + '<div data-gw-ask></div>'
      + '<div class="gw-src" style="font-size:10px;color:var(--slate-2);margin-top:8px">' + esc(t.source || '') + '</div>';
    if (d.not_applicable) {                       // nothing to follow: the household's answer settled it
      html = '<div class="card-label">' + esc(k.title) + '</div>'
        + '<div style="font-size:12px;color:var(--slate);line-height:1.7">' + esc(d.not_applicable) + '</div>'
        + '<div style="font-size:11px;color:var(--slate-2);margin-top:6px">Change this in Settings, under Your home.</div>';
    }
    var card = g(k.id);
    if (!card) {
      card = document.createElement('div');
      card.id = k.id;
      card.className = 'card mt-5';
      cont.appendChild(card);
    }
    card.innerHTML = html;
    var host = card.querySelector('[data-gw-ask]');
    var H = GWTeaching._modules.filter(function (x) { return x.name === 'household'; })[0];
    if (host && H && d.ask && d.ask.length) H.mod.ask(host, d.ask, {}, function () { _budgetCard(); });
  }

  function _budgetCard() { KINDS.forEach(function (k) { _card(k); }); }

  async function _save(kind, on, lag) {
    try { await API.post('/api/budget/utility-estimate/optin', { kind: kind, on: on, lag: lag }); }
    catch (e) { _gwErr(kind + ' estimate opt-in')(e); return; }
    await _refreshMonth();                    // the totals follow the choice at once (M4); nothing is written
    _card(KINDS.filter(function (k) { return k.kind === kind; })[0]);
  }

  // This month's figure per row, from the server (BUDGET_MONTH_AMOUNT.md M2). It only ever sets the month_* fields;
  // the saved amount (e.amount) - the only figure any write sends - is never touched here.
  async function _refreshMonth() {
    var m;
    try { m = await API.get('/api/budget/month-amounts'); } catch (e) { _gwErr('month amounts')(e); return; }
    m = (m && (m.data || m)) || {};
    (S.expenses || []).forEach(function (e) {
      var r = e.id != null ? m[String(e.id)] : null;
      if (!r) return;
      e.month_amount = r.month_amount; e.month_source = r.month_source; e.month_why = r.month_why; e.month_from = r.month_from;
      e.month_for = r.month_for;
    });
    budgetOriginal.apply(window, []);
    _rowNotes();
  }

  // M4/M5: a row that differs from what the user saved says so, with both figures; a followed estimate that has no
  // figure says why the saved amount is in use.
  function _rowNotes() {
    document.querySelectorAll('#budgetExpenseRows .ledger-row[data-expense-idx]').forEach(function (row) {
      var e = (S.expenses || [])[+row.dataset.expenseIdx];
      var old = row.querySelector('[data-gw-month-note]');
      if (old) old.remove();
      if (!e) return;
      var text = e.month_source === 'estimate' && e.month_from
        ? fmt(e.month_amount) + ' this month, from ' + e.month_from + ' \u00b7 you saved ' + fmt(parseFloat(e.amount) || 0)
        : e.month_why ? 'Using your saved ' + fmt(parseFloat(e.amount) || 0) + ': ' + e.month_why : '';
      if (!text) return;
      var note = document.createElement('div');
      note.setAttribute('data-gw-month-note', '');
      note.style.cssText = 'font-size:11px;color:var(--slate-2);margin:4px 0 0 46px;line-height:1.5';
      note.textContent = text;
      row.appendChild(note);
    });
  }

  document.addEventListener('change', function (ev) {
    var t = ev.target;
    if (!t || !t.matches || !(t.matches('[data-gw-util-optin]') || t.matches('[data-gw-util-lag]'))) return;
    var kind = t.getAttribute('data-kind');
    var k = KINDS.filter(function (x) { return x.kind === kind; })[0];
    var card = k && g(k.id);
    var box = card && card.querySelector('[data-gw-util-optin]');
    var sel = card && card.querySelector('[data-gw-util-lag]');
    _save(kind, !!(box && box.checked), sel ? parseInt(sel.value, 10) : 1);
  });

  // U4: the monthly report carries each followed utility's forecast line - only the sentence the estimate proves
  // (utilitytext's `statement`), never a claim about budget totals.
  async function _reportLine() {
    var anchor = g('rcMonthlyTeaching');
    if (!anchor) return;
    var W = _words();
    var host = g('rcUtilityEstimate');
    var lines = [];
    for (var i = 0; i < KINDS.length; i++) {
      var d = await _load(KINDS[i].kind);
      if (!d || !d.optin || !W) continue;
      var t = W[KINDS[i].kind](d, F);
      if (t && t.statement) lines.push(t.statement);
    }
    if (!lines.length) { if (host) host.remove(); return; }
    if (!host) {
      host = document.createElement('div');
      host.id = 'rcUtilityEstimate';
      host.style.cssText = 'font-size:12px;color:var(--slate);line-height:1.7;margin:8px 0';
      anchor.parentNode.insertBefore(host, anchor.nextSibling);
    }
    host.innerHTML = lines.map(function (l) { return '<div>' + esc(l) + '</div>'; }).join('');
  }

  var budgetOriginal = window.renderBudget;
  window.renderBudget = function () {
    var out = budgetOriginal.apply(this, arguments);
    try { _rowNotes(); _budgetCard(); } catch (e) { /* never break the page under it */ }
    return out;
  };
  var reportOriginal = window._rcRenderMonthlyReport;
  if (typeof reportOriginal === 'function') {
    window._rcRenderMonthlyReport = function () {
      var out = reportOriginal.apply(this, arguments);
      try { _reportLine(); } catch (e) { /* never break the page under it */ }
      return out;
    };
  }

  GWTeaching.register('utility', { budget: _budgetCard, report: _reportLine });
})();
