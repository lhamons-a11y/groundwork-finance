/*
 * The dashboard: your summary, and what needs attention (gw 2.0/DASHBOARD_SUMMARY_ATTENTION.md, ruled
 * 2026-09-27, authorised 2026-09-30).
 *
 * Teaching layer: absent from an LTS bundle by path, so the 1.x dashboard is unchanged (ruling 6).
 * It wraps renderDashboard. app.js and index.html know nothing of it.
 *
 * Rob's rule, exactly: usage never creates, ranks, or implies an attention item; an attention item
 * requires evidence about the user's finances. So:
 *   - Needs attention holds three kinds of dated fact (attention.js), each with its source and a way
 *     to resolve it. It is not the app speaking first, so it sits outside Speaking up and its dial
 *     (ruling 2), and it shows whatever the dial says.
 *   - A dismissal is the user's act and lasts until the fact it names changes (ruling 3).
 *   - Your summary is arranged by the user alone: pin, hide, reorder (ruling 1). Nothing here counts
 *     a view, a click or a visit, and nothing reorders by use. The defaults are the record's: every
 *     tile starts in its place and hides itself when the record has nothing for it.
 *   - Current priority, a ranked verdict, is retired (ruling 5). The check-engine band is folded into
 *     Needs attention as its third kind.
 */
(function () {
  'use strict';

  var A = GWTeaching._modules.filter(function (m) { return m.name === 'attention'; })[0];
  A = A && A.mod;

  var NAMES = {
    dashWhatChanged: 'What changed since last month', dashHealthCard: 'This month',
    dashHeroCard: 'Your plan', dashFreedMinimumsCard: 'Freed minimums',
    dashDonutCard: 'Spending by category', dashUpcomingCard: 'Coming up',
    dashInvestmentsCard: 'Investments'                                   // item 29
  };
  var _prefs = null;          // {tiles, layout:{order,pinned,hidden}, dismissed}
  var _arranging = false;

  function _style() {
    if (g('gwDashStyle')) return;
    var s = document.createElement('style');
    s.id = 'gwDashStyle';
    s.textContent = '#dashCurrentPriority{display:none!important}'          // ruling 5: retired
      + '#dashRecordStatus{display:none!important}'                        // folded into Needs attention
      + '.gw-tile-hidden{display:none!important}'
      + '#gwSummary{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;align-items:start;margin-bottom:20px}'
      + '#gwSummary > *{margin:0!important}';
    document.head.appendChild(s);
  }

  function _mount() {
    var anchor = g('dashWhatChanged');
    if (!anchor || g('gwAttention')) return;
    var att = document.createElement('div');
    att.id = 'gwAttention';
    anchor.parentNode.insertBefore(att, anchor);
    var head = document.createElement('div');
    head.id = 'gwSummaryHead';
    head.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin:4px 0 10px';
    anchor.parentNode.insertBefore(head, anchor);
    var sum = document.createElement('div');
    sum.id = 'gwSummary';
    anchor.parentNode.insertBefore(sum, anchor);
    var panel = document.createElement('div');
    panel.id = 'gwArrange';
    anchor.parentNode.insertBefore(panel, sum);
    // Item 29: the seventh tile. It exists for the layout from the start and stays hidden until tiles.js
    // finds investments on record (item 22 D1: no investments, no investment tile).
    if (!g('dashInvestmentsCard')) {
      var inv = document.createElement('div');
      inv.id = 'dashInvestmentsCard';
      inv.className = 'card';
      inv.style.display = 'none';
      sum.appendChild(inv);
    }
  }

  async function _loadPrefs() {
    try { _prefs = await API.get('/api/dashboard/prefs'); }
    catch (e) { _gwErr('dashboard prefs')(e); _prefs = _prefs || { tiles: Object.keys(NAMES), layout: { order: [], pinned: [], hidden: [] }, dismissed: [] }; }
    return _prefs;
  }

  // ── Your summary: the user's arrangement ───────────────────────────────────
  function _sequence(p) {
    var tiles = p.tiles || Object.keys(NAMES);
    var order = (p.layout.order || []).filter(function (t) { return tiles.indexOf(t) >= 0; });
    tiles.forEach(function (t) { if (order.indexOf(t) < 0) order.push(t); });   // record default: the page's own order
    var pinned = order.filter(function (t) { return (p.layout.pinned || []).indexOf(t) >= 0; });
    return pinned.concat(order.filter(function (t) { return pinned.indexOf(t) < 0; }));
  }

  function _applyLayout() {
    var sum = g('gwSummary');
    if (!sum || !_prefs) return;
    var hidden = _prefs.layout.hidden || [];
    _sequence(_prefs).forEach(function (id) {
      var el = g(id);
      if (!el) return;
      sum.appendChild(el);
      el.classList.toggle('gw-tile-hidden', hidden.indexOf(id) >= 0);
    });
    var head = g('gwSummaryHead');
    if (head) {
      head.innerHTML = '<div class="card-label" style="margin:0">Your summary</div>'
        + '<a href="#" id="gwArrangeToggle" style="font-size:11px;color:var(--slate-2)">' + (_arranging ? 'Done' : 'Arrange') + '</a>';
    }
    _renderArrange();
  }

  function _renderArrange() {
    var panel = g('gwArrange');
    if (!panel) return;
    if (!_arranging) { panel.innerHTML = ''; return; }
    var seq = _sequence(_prefs), hidden = _prefs.layout.hidden || [], pinned = _prefs.layout.pinned || [];
    function btn(act, id, label) {
      return '<button class="btn btn-sm btn-secondary" style="margin-left:4px" data-gw-arrange="' + act + '" data-gw-tile="' + id + '">' + label + '</button>';
    }
    panel.innerHTML = '<div class="card mb-5" style="font-size:12px;color:var(--slate)">'
      + '<div style="margin-bottom:6px">Arrange your summary. It stays exactly as you set it: Groundwork does not'
      + ' move tiles by what you open.</div>'
      + seq.map(function (id, i) {
        var isHidden = hidden.indexOf(id) >= 0, isPinned = pinned.indexOf(id) >= 0;
        return '<div style="display:flex;align-items:center;padding:4px 0;border-bottom:1px solid var(--steel)">'
          + '<span style="flex:1;color:' + (isHidden ? 'var(--slate-2)' : 'var(--ink)') + '">' + esc(NAMES[id] || id)
          + (isPinned ? ' · pinned' : '') + (isHidden ? ' · hidden' : '') + '</span>'
          + (i > 0 ? btn('up', id, '↑') : '') + (i < seq.length - 1 ? btn('down', id, '↓') : '')
          + btn(isPinned ? 'unpin' : 'pin', id, isPinned ? 'Unpin' : 'Pin')
          + btn(isHidden ? 'show' : 'hide', id, isHidden ? 'Show' : 'Hide') + '</div>';
      }).join('') + '</div>';
  }

  async function _arrange(act, id) {
    var L = _prefs.layout, seq = _sequence(_prefs);
    var order = seq.slice(), i = order.indexOf(id);
    function without(list) { return (list || []).filter(function (t) { return t !== id; }); }
    if (act === 'up' && i > 0) { order.splice(i, 1); order.splice(i - 1, 0, id); }
    if (act === 'down' && i < order.length - 1) { order.splice(i, 1); order.splice(i + 1, 0, id); }
    var next = {
      order: order,
      pinned: act === 'pin' ? without(L.pinned).concat([id]) : act === 'unpin' ? without(L.pinned) : (L.pinned || []),
      hidden: act === 'hide' ? without(L.hidden).concat([id]) : act === 'show' ? without(L.hidden) : (L.hidden || [])
    };
    try {
      _prefs.layout = await API.put('/api/dashboard/layout', next);
    } catch (e) { _gwErr('dashboard layout')(e); return; }
    _applyLayout();
  }

  // ── Needs attention: three kinds of fact ───────────────────────────────────
  function _date(iso) {
    var p = String(iso).split('-').map(Number);
    return new Date(p[0], p[1] - 1, p[2]).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  function _itemHTML(i) {
    var fact, source, action;
    if (i.kind === 'payment_due') {
      fact = '<strong>' + esc(i.title) + '</strong>: ' + (i.amount ? fmt(i.amount) + ' ' : '') + 'due ' + _date(i.due)
        + (i.days === 0 ? ' (today)' : i.days === 1 ? ' (tomorrow)' : ' (in ' + i.days + ' days)')
        + ', not yet recorded as paid this month.';
      source = 'From this card\'s due day and minimum, and this month\'s payments in Debt Payoff.';
      action = '<button class="btn btn-sm btn-secondary" onclick="showView(\'debt\')">Open Debt Payoff</button>';
    } else if (i.kind === 'import_stale') {
      fact = '<strong>' + esc(i.title) + '</strong>: last imported ' + _date(i.last_import) + ', ' + i.days + ' days ago.';
      source = 'From when this account\'s transactions were last imported. An account kept by hand is never listed.';
      action = '<button class="btn btn-sm btn-secondary" onclick="showView(\'ledger\')">Import</button>';
    } else {
      fact = '<strong>' + esc(i.title) + '</strong> can\'t be assessed yet. Missing: ' + esc(i.missing.join('; ')) + '.';
      source = 'From what your Financial Record holds so far.';
      action = '<button class="btn btn-sm btn-secondary" onclick="_recordStatusAction()">Verify account balances →</button>';
    }
    return '<div style="padding:10px 0;border-bottom:1px solid var(--steel);font-size:12px;color:var(--slate);line-height:1.7">'
      + fact + '<div style="font-size:11px;color:var(--slate-2)">' + source + '</div>'
      + '<div style="margin-top:4px">' + action
      + ' <button class="btn btn-sm btn-secondary" data-gw-dismiss="' + esc(A.fingerprint(i)) + '">Dismiss</button></div></div>';
  }


  // Item 27's tile text lives in tiles.js (SUMMARY_TILES_STANDARD.md). Looked up when the tiles render,
  // not at load: modules load in file-name order and tiles.js comes after this file.
  function _tiles(imports, items, payments) {
    var m = GWTeaching._modules.filter(function (x) { return x.name === 'tiles'; })[0];
    if (!m) { _gwErr('dashboard tiles')(new Error('tiles module not loaded')); return; }
    m.mod.render(imports, items, payments);
  }

  async function _renderAttention() {
    var host = g('gwAttention');
    if (!host || !A) return;
    var hasRecord = (S.transactions || []).length > 0;
    if (!hasRecord && !(S.debtCards || []).length) { host.innerHTML = ''; _tiles(null, [], []); return; }
    var stale = [], imports = null;
    try { imports = await API.get('/api/dashboard/attention/imports'); stale = imports.stale || []; }
    catch (e) { _gwErr('dashboard imports')(e); }
    var conf = _computeClaimConfidence();
    var payments = A.paymentsDue(_activeDebtCards().map(function (c) {
      return { id: c.id, name: c.name, dueDay: c.dueDay, minimum: c.minimum };
    }), new Date(), function (c, month) {
      var m = parseFloat(c.minimum) || 0;
      return _debtPaidThisMonth({ id: c.id, name: c.name, minimum: m, total: m }, month).paid;
    });
    var items = A.build({
      payments: payments,
      imports: A.importsStale(stale),
      blocked: A.blockedConclusions(conf, hasRecord)
    }, (_prefs && _prefs.dismissed) || []);
    var head = '<div class="card-label" style="margin-bottom:4px">Needs attention</div>';
    try { _tiles(imports, items, payments); } catch (e) { _gwErr('dashboard tiles')(e); }
    if (!items.length) {
      host.innerHTML = '<div class="card mb-5">' + head + '<div style="font-size:12px;color:var(--slate)">Nothing needs'
        + ' attention.' + (conf.overall === 'ready' ? ' Financial Record: up to date.' : '') + '</div></div>';
      return;
    }
    host.innerHTML = '<div class="card mb-5">' + head + items.map(_itemHTML).join('') + '</div>';
  }

  async function _dismiss(fp) {
    try {
      var r = await API.post('/api/dashboard/dismiss', { fingerprint: fp });
      if (_prefs) _prefs.dismissed = r.dismissed || [];
    } catch (e) { _gwErr('dashboard dismiss')(e); return; }
    _renderAttention();
  }

  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.closest) return;
    var d = t.closest('[data-gw-dismiss]');
    if (d) { ev.preventDefault(); _dismiss(d.getAttribute('data-gw-dismiss')); return; }
    var a = t.closest('[data-gw-arrange]');
    if (a) { ev.preventDefault(); _arrange(a.getAttribute('data-gw-arrange'), a.getAttribute('data-gw-tile')); return; }
    if (t.id === 'gwArrangeToggle') { ev.preventDefault(); _arranging = !_arranging; _applyLayout(); }
  });

  async function render() {
    _style();
    _mount();
    if (!_prefs) await _loadPrefs();
    _applyLayout();
    await _renderAttention();
  }

  var original = window.renderDashboard;
  window.renderDashboard = function () {
    var out = original.apply(this, arguments);
    try { render(); } catch (e) { /* never break the page under it */ }
    return out;
  };

  _style();
  GWTeaching.register('dashboard', { render: render });
})();
