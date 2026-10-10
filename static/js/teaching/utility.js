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

  // Rob 2026-10-03: the user has full control of each card - follow it, do not follow it (an explicit answer; until
  // they give one, nothing is assumed), or hide it. Hiding is a VIEW choice only - in the off season they may see no
  // need to view it - so a hidden card keeps its follow choice, and the hidden line says what the budget uses.
  var _hidden = {};
  // A save re-renders the card more than once (the month refresh and the card itself), so 'Saved.' is shown for a
  // few seconds after the press rather than cleared by whichever render lands first.
  var _justSaved = {};
  function _saved(kind) { return _justSaved[kind] && Date.now() - _justSaved[kind] < 8000; }
  function _title(k, d) { return (k.kind === 'gasoline' && d && d.fuel === 'diesel') ? 'Diesel estimate' : k.title; }   // item 34 F1
  function _hideBtn(kind) {
    return '<button type="button" class="btn btn-ghost btn-sm" data-gw-util-hide data-kind="' + kind + '">Hide this card</button>';
  }
  function _hiddenLine() {
    var cont = g('budgetContent');
    if (!cont) return;
    var host = g('gwHiddenEstimates');
    var ks = KINDS.filter(function (k) { return _hidden[k.kind]; });
    if (!ks.length) { if (host) host.remove(); return; }
    if (!host) {
      host = document.createElement('div');
      host.id = 'gwHiddenEstimates';
      host.style.cssText = 'font-size:12px;color:var(--slate-2);margin-top:12px;line-height:1.9';
    }
    cont.appendChild(host);
    host.innerHTML = 'Hidden estimates: ' + ks.map(function (k) {
      var d = _hidden[k.kind], u = d.budget_uses || {};
      var note = d.follow !== 'follow' ? ''
        : u.in_totals ? ' \u2014 followed; this month\u2019s budget uses it, ' + fmt(u.month_amount)
        : ' \u2014 followed; this month\u2019s budget uses your saved amount';
      return esc(_title(k, d)) + esc(note) + ' <button type="button" class="btn btn-ghost btn-sm" data-gw-util-show data-kind="'
        + k.kind + '">Show</button>';
    }).join(' \u00b7 ');
  }

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
    if (!d || !W || (!d.bills && d.saved_amount === null)) { if (old) old.remove(); delete _hidden[k.kind]; _hiddenLine(); return; }
    if (d.hidden) { if (old) old.remove(); _hidden[k.kind] = d; _hiddenLine(); return; }
    delete _hidden[k.kind];
    _hiddenLine();
    var t = W[k.kind](d, F);
    var title = _title(k, d);
    var nm = 'gwUtilChoice_' + k.kind;
    var radio = function (v, label) {
      return '<label style="margin-right:12px"><input type="radio" name="' + nm + '" value="' + v + '" data-gw-util-choice data-kind="'
        + k.kind + '"' + (d.follow === v ? ' checked' : '') + '> ' + label + '</label>';
    };
    var html = '<div class="card-label">' + esc(title) + '</div>'
      + t.lines.map(function (l) { return '<div style="font-size:12px;color:var(--slate);line-height:1.7">' + esc(l) + '</div>'; }).join('')
      + '<div style="margin-top:8px;font-size:12px;color:var(--slate)">'
      + radio('follow', 'Follow this estimate') + radio('not_follow', 'Do not follow')
      + (k.noLag ? '' : ' \u00b7 bills pay for <select data-gw-util-lag data-kind="' + k.kind + '" style="font-size:12px">'
      + [0, 1, 2].map(function (n) {
          return '<option value="' + n + '"' + (d.lag === n ? ' selected' : '') + '>' + ['the same month', 'the month before', 'two months before'][n] + '</option>';
        }).join('') + '</select>')
      + ' <button type="button" class="btn btn-primary btn-sm" data-gw-util-submit data-kind="' + k.kind + '" disabled>Submit</button> '
      + _hideBtn(k.kind)
      + '<div data-gw-util-status style="font-size:11px;color:var(--slate-2);margin-top:4px">'
      + (_saved(k.kind) ? 'Saved.' : '') + '</div></div>'
      + '<div data-gw-ask></div>'
      + '<div class="gw-src" style="font-size:10px;color:var(--slate-2);margin-top:8px">' + esc(t.source || '') + '</div>';
    if (d.not_applicable) {                       // the household's answer settled it - nothing new to follow
      // Rob 2026-10-03: a household that moved (renters often do) may still follow this from before. That choice is
      // said, never changed for them, and the card offers the choice and Submit so they can stop following it.
      var stale = d.follow === 'follow';
      html = '<div class="card-label">' + esc(k.title) + '</div>'
        + '<div style="font-size:12px;color:var(--slate);line-height:1.7">' + esc(d.not_applicable) + '</div>'
        + (stale ? '<div style="font-size:12px;color:var(--slate);line-height:1.7">You still follow this estimate from before. '
            + 'It no longer applies, so your saved amount sets the budget; choose Do not follow and press Submit to stop following it.</div>'
            + '<div style="margin-top:8px;font-size:12px;color:var(--slate)">' + radio('follow', 'Follow this estimate')
            + radio('not_follow', 'Do not follow')
            + ' <button type="button" class="btn btn-primary btn-sm" data-gw-util-submit data-kind="' + k.kind + '" disabled>Submit</button>'
            + '<div data-gw-util-status style="font-size:11px;color:var(--slate-2);margin-top:4px"></div></div>'
          : _saved(k.kind) ? '<div style="font-size:12px;color:var(--slate);margin-top:6px">Saved: you no longer follow this estimate.</div>'
          : '')
        + '<div style="font-size:11px;color:var(--slate-2);margin-top:6px">Change this in Settings, under Your home.</div>'
        + '<div style="margin-top:6px">' + _hideBtn(k.kind) + '</div>';
    }
    var card = g(k.id);
    if (!card) {
      card = document.createElement('div');
      card.id = k.id;
      card.className = 'card mt-5';
      cont.appendChild(card);
    }
    card.innerHTML = html;
    card.dataset.gwSavedFollow = d.follow || '';
    card.dataset.gwSavedLag = d.lag === undefined || d.lag === null ? '' : String(d.lag);
    var host = card.querySelector('[data-gw-ask]');
    var H = GWTeaching._modules.filter(function (x) { return x.name === 'household'; })[0];
    if (host && H && d.ask && d.ask.length) H.mod.ask(host, d.ask, {}, function () { _budgetCard(); });
  }

  function _budgetCard() { KINDS.forEach(function (k) { _card(k); }); }

  // Only the field the user changed is sent: hiding keeps the follow choice and the lag, and the reverse.
  async function _save(kind, patch) {
    try { await API.post('/api/budget/utility-estimate/optin', Object.assign({ kind: kind }, patch)); }
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
      var text = (e.month_source === 'estimate' || e.month_source === 'bill') && e.month_from
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

  // The card's choices are a draft until Submit: picking a radio or a billing month saves nothing. Submit is enabled
  // only when the draft differs from what is saved, and the card says a choice is waiting.
  function _draft(card) {
    var r = card.querySelector('[data-gw-util-choice]:checked'), sel = card.querySelector('[data-gw-util-lag]');
    return { follow: r ? r.value : '', lag: sel ? sel.value : card.dataset.gwSavedLag };
  }
  document.addEventListener('change', function (ev) {
    var t = ev.target;
    if (!t || !t.matches || !(t.matches('[data-gw-util-choice]') || t.matches('[data-gw-util-lag]'))) return;
    var card = t.closest('.card');
    if (!card) return;
    var dr = _draft(card), changed = dr.follow !== card.dataset.gwSavedFollow || dr.lag !== card.dataset.gwSavedLag;
    var btn = card.querySelector('[data-gw-util-submit]'), st = card.querySelector('[data-gw-util-status]');
    if (btn) btn.disabled = !changed;
    if (st) st.textContent = changed ? 'Not saved yet \u2014 press Submit to keep this choice.' : '';
  });
  document.addEventListener('click', function (ev) {
    var t = ev.target && ev.target.closest && ev.target.closest('[data-gw-util-hide], [data-gw-util-show], [data-gw-util-submit]');
    if (!t) return;
    var kind = t.getAttribute('data-kind');
    if (t.hasAttribute('data-gw-util-submit')) {             // the user's decision: what they picked, sent together
      var card = t.closest('.card');
      if (!card || t.disabled) return;
      var dr = _draft(card), patch = {};
      if (dr.follow && dr.follow !== card.dataset.gwSavedFollow) patch.choice = dr.follow;
      if (dr.lag !== card.dataset.gwSavedLag && dr.lag !== '') patch.lag = parseInt(dr.lag, 10);
      if (!Object.keys(patch).length) return;
      t.disabled = true;
      _justSaved[kind] = Date.now();
      _save(kind, patch);
      return;
    }
    _save(kind, { hidden: t.hasAttribute('data-gw-util-hide') });   // hiding is a view choice: immediate
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
