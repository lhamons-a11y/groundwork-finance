/*
 * The summary tiles meet the attention standard (gw 2.0/SUMMARY_TILES_STANDARD.md, item 27, ruled
 * 2026-09-30: all six points).
 *
 * Teaching layer: absent from an LTS bundle by path. dashboard.js calls render() after renderDashboard,
 * handing over what it already measured (the import facts, the attention items, the unpaid payments), so
 * this module borrows only what the tiles' own figures need from app.js (s30: borrowing, not coupling).
 * app.js computes every figure; this re-says them as facts with their source and completeness, never a
 * verdict. The 1.x wording stays in app.js for 1.x.
 */
(function () {
  'use strict';

  function _date(iso) {
    var p = String(iso).split('-').map(Number);
    return new Date(p[0], p[1] - 1, p[2]).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }
  // Looked up when the tiles render, not at load: modules load in file-name order, and tiletext.js
  // comes after this file - a load-time lookup finds nothing and the tiles silently keep their old words.
  var T = null;
  function _tiletext() {
    if (!T) { var m = GWTeaching._modules.filter(function (x) { return x.name === 'tiletext'; })[0]; T = m && m.mod; }
    return T;
  }
  var F = {
    money: function (n) { return fmt(n); },
    date: function (iso) { return _date(iso); },
    monthYear: function (d) { return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }); }
  };

  function _source(id, text) {
    var el = g(id);
    if (!el) return;
    var old = el.querySelector(':scope > .gw-src');
    if (old) old.remove();
    var s = document.createElement('div');
    s.className = 'gw-src';
    s.style.cssText = 'font-size:10px;color:var(--slate-2);margin-top:8px';
    s.textContent = text;
    el.appendChild(s);
  }

  // Item 29: the Investments tile, only when investments are on record (INVESTMENTS_TILE.md).
  async function _investments() {
    var card = g('dashInvestmentsCard');
    if (!card) return;
    var d = null;
    try { d = await API.get('/api/dashboard/investments'); }
    catch (e) { _gwErr('dashboard investments')(e); }
    var t = d && _tiletext().investments(d, F);
    if (!t) { card.style.display = 'none'; card.innerHTML = ''; return; }
    card.innerHTML = '<div class="card-label">Investments</div>'
      + t.lines.map(function (l) {
        return '<div style="font-size:12px;color:var(--slate);line-height:1.7;padding:2px 0">' + esc(l) + '</div>';
      }).join('');
    card.style.display = '';
    _source('dashInvestmentsCard', t.source);
  }

  function render(imports, items, payments) {
    if (!_tiletext()) { _gwErr('dashboard tiles')(new Error('tiletext module not loaded')); return; }
    _investments();
    var behind = (imports && imports.behind_this_month) || [];
    var now = new Date();
    var monthName = now.toLocaleDateString(undefined, { month: 'long' });
    var behindNote = behind.length ? ' Not yet imported this month: ' + behind.map(function (b) { return b.account; }).join(', ') + '.' : '';

    // Greeting (T3): the greeting stays; the line under it is one upcoming fact from the record, or nothing.
    var sub = g('dashGreetingSub');
    if (sub) sub.textContent = T.greetingFact(items && items[0], F);

    // This month (T1, T2, T4).
    var txns = getTxnsForPeriod();
    var spent = txns.filter(_isSpend).reduce(function (s, t) { return s + t.amount; }, 0);
    var bills = txns.filter(function (t) { return _isSpend(t) && _isMonthlyBill(t); })
                    .reduce(function (s, t) { return s + t.amount; }, 0);
    var m = T.month({ spent: spent, bills: bills, daysGone: now.getDate(),
                      daysInMonth: new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate(),
                      budget: _effectiveIncome(), behind: behind, monthName: monthName }, F);
    var v = g('dashHealthVerdict'), hs = g('dashHealthSub'), card = g('dashHealthCard');
    if (v) { v.textContent = m.head; v.style.color = 'var(--ink)'; }
    if (hs) hs.textContent = m.body;
    if (card) card.style.borderColor = '';
    ['dashPaceFill', 'dashPaceMarker'].forEach(function (id) {
      var el = g(id);
      if (!el) return;
      if (id === 'dashPaceFill') el.style.background = 'var(--slate-2)'; else el.style.color = 'var(--slate)';
    });
    var fill = g('dashPaceBar');
    if (fill) fill.style.display = behind.length ? 'none' : '';
    var meta = g('dashHealthMeta');
    if (meta) {
      var daysLeft = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate() - now.getDate();
      var ratio = (typeof calcDTI === 'function') ? calcDTI() : null;
      meta.textContent = daysLeft + ' days left in ' + monthName + '. ' + T.dti(ratio);
    }
    _source('dashHealthCard', 'From your ledger this month and your budgeted income.' + behindNote);

    // Your plan (T5): the two dates, not a schedule verdict.
    var hero = g('dashHeroCard');
    if (hero) {
      Array.prototype.forEach.call(hero.querySelectorAll('span'), function (s) {
        if (/(ahead of|behind) schedule/.test(s.textContent) && !s.querySelector('span')) {
          s.textContent = T.plan(typeof _gwDateMovement === 'function' ? _gwDateMovement() : null, F);
          s.style.color = 'var(--slate)';
        }
      });
      _source('dashHeroCard', 'From your debt balances and payments in Debt Payoff.');
    }

    // What changed (T7): a movement is a movement - no good / not-good marks.
    var wc = g('dashWhatChanged');
    if (wc) {
      Array.prototype.forEach.call(wc.querySelectorAll('span'), function (s) {
        if (s.textContent === '✓' || s.textContent === '↑') { s.textContent = '•'; s.style.color = 'var(--slate-2)'; }
      });
      if (wc.innerHTML.trim()) _source('dashWhatChanged', 'From your ledger, this month against last, shown only where the record can support it.');
    }

    // Spending by category (T7): completeness and coverage.
    _source('dashDonutCard', 'From your ledger for ' + monthName + ' so far.' + behindNote);
    _source('dashFreedMinimumsCard', 'From cards marked paid off in Debt Payoff.');

    // Coming up (T8): the next occurrence of each due date, this month or next.
    var up = g('dashUpcomingCard'), upc = g('dashUpcomingContent');
    if (up && upc) {
      var rows = (payments || []).map(function (i) { return { label: i.title, amount: i.amount, days: i.days }; });
      (typeof _recurringItems !== 'undefined' && _recurringItems ? _recurringItems : []).forEach(function (r) {
        var day = parseInt(r.dayOfMonth, 10) || 1;
        var d = new Date(now.getFullYear(), now.getMonth(), day);
        var t = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        if (d < t) d = new Date(now.getFullYear(), now.getMonth() + 1, day);
        var days = Math.round((d - t) / 86400000);
        if (days >= 0 && days <= 7) rows.push({ label: r.name || r.description, amount: r.amount || 0, days: days });
      });
      rows.sort(function (a, b) { return a.days - b.days; });
      if (rows.length) {
        upc.innerHTML = rows.slice(0, 5).map(function (r) {
          return '<div style="display:flex;gap:10px;padding:5px 0;border-bottom:1px solid var(--steel);font-size:12px">'
            + '<span style="flex:1;color:var(--ink)">' + esc(r.label) + '</span>'
            + '<span style="font-family:var(--font-mono);color:var(--slate)">' + (r.amount > 0 ? fmt(r.amount) : '') + '</span>'
            + '<span style="font-family:var(--font-mono);color:var(--slate-2)">' + (r.days === 0 ? 'today' : r.days === 1 ? 'tomorrow' : 'in ' + r.days + 'd') + '</span></div>';
        }).join('');
        up.style.display = '';
        _source('dashUpcomingCard', 'From each card\'s due day and minimum, and your recurring items; the next date, this month or next.');
      } else {
        up.style.display = 'none';
      }
    }
  }


  GWTeaching.register('tiles', { render: render });
})();
