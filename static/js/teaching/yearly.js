/*
 * Yearly price steps on the Budget page (gw 2.0/YEARLY_PRICE_STEPS.md, item 106).
 *
 * Teaching layer: absent from an LTS bundle by path (Y11). On the Bills tab, under Price changes: each bill whose
 * price has stepped about a year apart, said with its years (Y9); the projection from three steps (Y2 as measured),
 * which the household may choose to follow in the month's totals (Y6); and the question when a new price lands in
 * the expected month (Y7). On the plan, a row with a projection says so beside its saved amount. Every figure comes
 * from /api/yearly-steps; the only writes are the household's answer and their follow choice, each with Undo.
 */
(function () {
  'use strict';

  var _items = [];

  function _el(id) { return document.getElementById(id); }

  function _month(m) {
    return new Date(+m.slice(0, 4), +m.slice(5, 7) - 1, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }

  function _pct(p) { return (p > 0 ? '+' : '-') + Math.abs(p * 100).toFixed(1) + '%'; }

  function _projWords(p) {
    return 'Projected from ' + _month(p.month) + ': ' + fmt(p.amount) + ' (' + _pct(p.pct) + ', the median of '
      + p.years.map(function (m) { return m.slice(0, 4); }).join(', ') + ')';
  }

  function _question(x, i) {
    var q = x.question;
    if (!q) return '';
    var box = '<div style="margin-top:8px;padding:8px 10px;border:0.5px solid var(--steel-2);border-radius:8px">'
      + '<div style="font-size:13px;color:var(--ink);margin-bottom:6px">' + esc(q.text) + '</div>';
    if (q.kind === 'price') {
      box += '<button class="btn btn-secondary btn-sm" data-gw-ys="yes" data-i="' + i + '">Yes, ' + fmt(q.amount) + '</button> '
        + '<span style="font-size:12px;color:var(--slate)">or it is $</span>'
        + '<input type="number" min="0" step="0.01" data-gw-ys-amount="' + i + '" style="width:90px" aria-label="The bill\'s amount"> '
        + '<button class="btn btn-secondary btn-sm" data-gw-ys="amount" data-i="' + i + '">Save</button> '
        + '<button class="btn btn-ghost btn-sm" data-gw-ys="not_sure" data-i="' + i + '">Not sure</button>';
      if (x.line) {
        box += '<div style="font-size:11px;color:var(--slate);margin-top:6px">Your answer sets your budget line '
          + esc(x.line.name) + ' (now ' + fmt(x.line.amount) + '), with Undo.</div>';
      }
    } else {
      box += '<span style="font-size:12px;color:var(--slate)">Yes, by</span> '
        + '<input type="number" step="0.1" data-gw-ys-pct="' + i + '" style="width:70px" aria-label="The rate change, in percent">'
        + '<span style="font-size:12px;color:var(--slate)">%</span> '
        + '<button class="btn btn-secondary btn-sm" data-gw-ys="rate" data-i="' + i + '">Save</button> '
        + '<button class="btn btn-secondary btn-sm" data-gw-ys="no_change" data-i="' + i + '">No</button> '
        + '<button class="btn btn-ghost btn-sm" data-gw-ys="not_sure" data-i="' + i + '">Not sure</button>'
        + '<div data-gw-ys-preview="' + i + '" style="font-size:11px;color:var(--slate);margin-top:6px">'
        + (x.line ? 'Your answer sets your budget line ' + esc(x.line.name) + ' (now ' + fmt(x.line.amount) + ') by that percent, with Undo.' : '')
        + '</div>';
    }
    return box + '</div>';
  }

  function _card() {
    var host = _el('budgetYearlySteps');
    if (!host) return;
    var asked = _items.filter(function (x) { return x.question; }).length;
    _budTabCount('bills', asked, 'yearly');
    if (!_items.length) { host.innerHTML = ''; return; }
    host.innerHTML = '<div class="card mt-5"><div class="card-label">Yearly price steps</div>'
      + '<div style="font-size:12px;color:var(--slate);margin-bottom:8px">Bills whose price has changed about a year apart, '
      + 'from your record and your answers. A figure for the next year is shown from three such steps; with two, Groundwork '
      + 'asks when the new price arrives. It shows what the charges say, not why a price changed.</div>'
      + _items.map(function (x, i) {
        var rows = '<div style="padding:8px 0;border-bottom:0.5px solid var(--steel-2)">'
          + '<div style="font-size:13px;color:var(--ink)">' + esc(x.sentence || ((x.label || x.payee) + ': no step on record yet.')) + '</div>';
        if (x.steps && x.steps.length) {
          rows += '<details style="font-size:11px;color:var(--slate);margin-top:4px"><summary style="cursor:pointer">The years</summary>'
            + x.steps.map(function (s) {
              return '<div style="font-family:var(--font-mono)">' + _month(s.month) + ' &nbsp; ' + _pct(s.pct)
                + (s.before != null ? ' &nbsp; ' + fmt(s.before) + ' to ' + fmt(s.after) : '')
                + (s.source === 'answer' ? ' &nbsp; (you told us)' : '') + '</div>';
            }).join('') + '</details>';
        }
        if (x.projection) {
          rows += '<div style="margin-top:6px;font-size:12px;color:var(--slate)">' + esc(_projWords(x.projection)) + '.';
          if (x.line && x.line.kind === 'budget') {
            rows += ' <label style="cursor:pointer"><input type="checkbox" data-gw-ys-follow="' + i + '"' + (x.followed ? ' checked' : '')
              + '> Use it for ' + esc(x.line.name) + ' in the totals from ' + esc(_month(x.projection.month))
              + ' (your saved ' + fmt(x.line.amount) + ' stays)</label>';
          }
          rows += '</div>';
        }
        return rows + _question(x, i) + '</div>';
      }).join('') + '</div>';
    host.querySelectorAll('[data-gw-ys]').forEach(function (b) {
      b.addEventListener('click', function () { _answer(+b.dataset.i, b.dataset.gwYs); });
    });
    host.querySelectorAll('[data-gw-ys-follow]').forEach(function (c) {
      c.addEventListener('change', function () { _follow(+c.dataset.gwYsFollow, c.checked); });
    });
    host.querySelectorAll('[data-gw-ys-pct]').forEach(function (inp) {
      inp.addEventListener('input', function () {
        var x = _items[+inp.dataset.gwYsPct], p = parseFloat(inp.value), out = host.querySelector('[data-gw-ys-preview="' + inp.dataset.gwYsPct + '"]');
        if (!x || !x.line || !out) return;
        out.textContent = isFinite(p) && p !== 0
          ? 'Your budget line ' + x.line.name + ' would go from ' + fmt(x.line.amount) + ' to ' + fmt(Math.round(x.line.amount * (1 + p / 100) * 100) / 100) + ', with Undo.'
          : 'Your answer sets your budget line ' + x.line.name + ' (now ' + fmt(x.line.amount) + ') by that percent, with Undo.';
      });
    });
  }

  // Y6: a plan row with a projection says so beside its saved amount. A followed one already carries the month's
  // figure in its month note (utility.js), so it isn't said twice.
  function _rowNotes() {
    document.querySelectorAll('[data-gw-yearly-note]').forEach(function (n) { n.remove(); });
    _items.forEach(function (x) {
      if (!x.projection || !x.line || x.line.kind !== 'budget' || x.followed) return;
      var idx = (S.expenses || []).findIndex(function (e) { return e.id === x.line.id; });
      var row = idx < 0 ? null : document.querySelector('#budgetExpenseRows .ledger-row[data-expense-idx="' + idx + '"]');
      if (!row) return;
      var note = document.createElement('div');
      note.setAttribute('data-gw-yearly-note', '');
      note.style.cssText = 'font-size:11px;color:var(--slate-2);margin:4px 0 0 46px;line-height:1.5';
      note.textContent = _projWords(x.projection) + ' · not in the totals (the Bills tab can add it) · you saved '
        + fmt(x.line.amount);
      row.appendChild(note);
    });
  }

  // After a follow choice or an answer: the month figures again (utility.js's refresh, which redraws the plan), so
  // the totals follow at once, then this card and its row notes.
  async function _after() {
    var u = (GWTeaching._modules.filter(function (m) { return m.name === 'utility'; })[0] || {}).mod;
    if (u && typeof u.month === 'function') await u.month();
    else window.renderBudget();
    await _load();
  }

  async function _load() {
    try { _items = ((await API.get('/api/yearly-steps')) || {}).items || []; }
    catch (e) { _gwErr('yearly steps')(e); _items = []; }
    _card();
    _rowNotes();
  }

  async function _answer(i, answer) {
    var x = _items[i];
    if (!x || !x.question) return;
    var body = { payee: x.payee, label: x.label, answer: answer };    // item 108: the account's line
    if (answer === 'amount') {
      var a = parseFloat((document.querySelector('[data-gw-ys-amount="' + i + '"]') || {}).value);
      if (!(a > 0)) { showToast('Type the bill\'s amount first', '', 'info'); return; }
      body.amount = a;
    }
    if (answer === 'rate') {
      var p = parseFloat((document.querySelector('[data-gw-ys-pct="' + i + '"]') || {}).value);
      if (!isFinite(p) || p === 0) { showToast('Type the rate change in percent first', '', 'info'); return; }
      body.pct = p;
    }
    try {
      var r = await API.post('/api/yearly-steps/answer', body);
      var ch = r.change;
      if (ch) _setLocalLineAmount(ch.kind, ch.id, ch.to);
      var title = ch ? ch.line + ': ' + fmt(ch.from) + ' to ' + fmt(ch.to) : 'Answer kept for ' + (x.label || x.payee);
      showToast(title, '', 'success', async function () {
        try {
          await API.post('/api/yearly-steps/undo', { payee: x.payee, month: r.recorded.month, change: ch });
          if (ch) _setLocalLineAmount(ch.kind, ch.id, ch.from);
          showToast('Answer undone', '', 'info');
        }
        catch (e) { showToast('Undo failed', e.message || '', 'error'); }
        _after();
      });
      _after();
    } catch (e) { showToast('Could not keep the answer', e.message || '', 'error'); }
  }

  async function _follow(i, on) {
    var x = _items[i];
    if (!x || !x.line) return;
    try {
      await API.post('/api/yearly-steps/follow', { item_id: x.line.id, on: on });
      showToast(on ? x.line.name + ' follows its yearly step in the totals' : x.line.name + ' uses your saved amount', '', 'success', async function () {
        try { await API.post('/api/yearly-steps/follow', { item_id: x.line.id, on: !on }); } catch (e) { showToast('Undo failed', e.message || '', 'error'); }
        _after();
      });
      _after();
    } catch (e) { showToast('Could not change that', e.message || '', 'error'); }
  }

  var priceOriginal = window.renderPriceChanges;
  if (typeof priceOriginal === 'function') {
    window.renderPriceChanges = function () {
      var out = priceOriginal.apply(this, arguments);
      try { _load(); } catch (e) { /* never break the page under it */ }
      return out;
    };
  }
  var budgetOriginal = window.renderBudget;
  window.renderBudget = function () {
    var out = budgetOriginal.apply(this, arguments);
    try { _rowNotes(); } catch (e) { /* never break the page under it */ }
    return out;
  };

  GWTeaching.register('yearly', { load: _load, rows: _rowNotes });
})();
