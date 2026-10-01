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
  var F = { money: function (n) { return fmt(n); }, month: _month };

  async function _load() {
    try { return await API.get('/api/budget/utility-estimate/gas'); }
    catch (e) { _gwErr('gas estimate')(e); return null; }
  }

  // Shown only when the record has something for it: a Gas budget row or gas bills (no empty card for a home
  // without gas service).
  async function _budgetCard() {
    var cont = g('budgetContent');
    if (!cont) return;
    var old = g('gwGasEstimate');
    if (old) old.innerHTML = '<div class="card-label">Natural gas estimate</div><div style="font-size:12px;color:var(--slate-2)">Loading EIA\'s outlook…</div>';
    var d = await _load();
    var W = _words();
    if (!d || !W || (!d.bills && d.saved_amount === null)) { if (old) old.remove(); return; }
    var t = W.gas(d, F);
    var html = '<div class="card-label">Natural gas estimate</div>'
      + t.lines.map(function (l) { return '<div style="font-size:12px;color:var(--slate);line-height:1.7">' + esc(l) + '</div>'; }).join('')
      + '<div style="margin-top:8px;font-size:12px;color:var(--slate)">'
      + '<label><input type="checkbox" data-gw-gas-optin ' + (d.optin ? 'checked' : '') + '> Follow this estimate</label>'
      + ' · bills pay for <select data-gw-gas-lag style="font-size:12px">'
      + [0, 1, 2].map(function (k) {
          return '<option value="' + k + '"' + (d.lag === k ? ' selected' : '') + '>' + ['the same month', 'the month before', 'two months before'][k] + '</option>';
        }).join('') + '</select></div>'
      + '<div class="gw-src" style="font-size:10px;color:var(--slate-2);margin-top:8px">' + esc(t.source || '') + '</div>';
    var card = g('gwGasEstimate');
    if (!card) {
      card = document.createElement('div');
      card.id = 'gwGasEstimate';
      card.className = 'card mt-5';
      cont.appendChild(card);
    }
    card.innerHTML = html;
  }

  async function _save(on, lag) {
    try { await API.post('/api/budget/utility-estimate/optin', { kind: 'gas', on: on, lag: lag }); }
    catch (e) { _gwErr('gas estimate opt-in')(e); return; }
    _budgetCard();
  }

  document.addEventListener('change', function (ev) {
    var t = ev.target;
    if (!t || !t.matches) return;
    if (t.matches('[data-gw-gas-optin]') || t.matches('[data-gw-gas-lag]')) {
      var card = g('gwGasEstimate');
      var box = card && card.querySelector('[data-gw-gas-optin]');
      var sel = card && card.querySelector('[data-gw-gas-lag]');
      _save(!!(box && box.checked), sel ? parseInt(sel.value, 10) : 1);
    }
  });

  // U4: the monthly report carries the forecast line only when the user follows the estimate, and only the sentence
  // the estimate itself proves (utilitytext's `statement`) - never a claim about budget totals.
  async function _reportLine() {
    var anchor = g('rcMonthlyTeaching');
    if (!anchor) return;
    var d = await _load();
    var W = _words();
    var host = g('rcUtilityEstimate');
    if (!d || !d.optin || !W) { if (host) host.remove(); return; }
    var t = W.gas(d, F);
    if (!t || !t.statement) { if (host) host.remove(); return; }
    if (!host) {
      host = document.createElement('div');
      host.id = 'rcUtilityEstimate';
      host.style.cssText = 'font-size:12px;color:var(--slate);line-height:1.7;margin:8px 0';
      anchor.parentNode.insertBefore(host, anchor.nextSibling);
    }
    host.textContent = t.statement;
  }

  var budgetOriginal = window.renderBudget;
  window.renderBudget = function () {
    var out = budgetOriginal.apply(this, arguments);
    try { _budgetCard(); } catch (e) { /* never break the page under it */ }
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
