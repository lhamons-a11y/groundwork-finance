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

  // R1 (item 28): the tile list and its titles come from the server's catalogue (/prefs) - one source, no copy
  // kept here to drift from it.
  function _title(id) { return (_prefs && _prefs.titles && _prefs.titles[id]) || id; }
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
    catch (e) { _gwErr('dashboard prefs')(e); _prefs = _prefs || { tiles: [], titles: {}, layout: { order: [], pinned: [], hidden: [], added: [] }, dismissed: [], requests: [] }; }
    return _prefs;
  }

  // ── Your summary: the user's arrangement ───────────────────────────────────
  function _sequence(p) {
    var tiles = p.tiles || [];
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
      if (!el) {
        // A tile the user added from the catalogue (item 28): its container, filled by its own module.
        el = document.createElement('div');
        el.id = id;
        el.className = 'card';
        el.style.display = 'none';
      }
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
          + '<span style="flex:1;color:' + (isHidden ? 'var(--slate-2)' : 'var(--ink)') + '">' + esc(_title(id))
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
    } else if (i.kind === 'date_ends') {
      var what = { trial_ends: 'free trial ends', return_by: 'last day to return', cancel_by: 'last day to cancel' }[i.what] || 'date';
      var when = i.days === 0 ? ' (today)' : i.days === 1 ? ' (tomorrow)' : ' (in ' + i.days + ' days)';
      fact = '<strong>' + esc(i.title) + '</strong>: ' + what + ' ' + _date(i.due) + when
        + (i.price_after ? ', then ' + fmt(i.price_after) + (i.every ? ' a ' + esc(i.every) : '') : '') + '.';
      source = 'From the receipt you added in Before You Buy. Groundwork doesn\'t cancel or return anything; you do.';
      action = '<button class="btn btn-sm btn-secondary" data-gw-receipt-done="' + esc(String(i.rowId)) + '">Handled</button>';
    } else if (i.kind === 'fsa_deadline') {
      var left = i.days === 0 ? ' Today is the last day.' : i.days === 1 ? ' One day left.' : ' ' + i.days + ' days left.';
      fact = '<strong>' + esc(i.title) + '</strong>: ' + esc(i.sentence) + left;
      source = 'From this FSA\'s balance and the plan terms you entered. Groundwork doesn\'t spend or claim anything; you decide.';
      action = '<button class="btn btn-sm btn-secondary" onclick="showView(\'settings\');_settingsShowTab(\'accounts\')">Open Accounts</button>';
    } else if (i.kind === 'bill_due') {
      var by = i.days < 0 ? ' It was due ' + _date(i.due) + '.' : ' Due ' + _date(i.due) + (i.days === 0 ? ' (today).' : i.days === 1 ? ' (tomorrow).' : ' (in ' + i.days + ' days).');
      fact = '<strong>' + esc(i.title) + '</strong>: ' + esc(i.sentence) + by;
      source = 'From the bill you typed in, your savings on record and your reserve. Groundwork never contacts anyone or pays anything.';
      action = '<button class="btn btn-sm btn-secondary" onclick="showView(\'settings\');_settingsShowTab(\'accounts\')">Open Medical bills</button>';
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

  // Item 79 U5 (UI_AUDIT.md, ruled 2026-10-13): the same message six times made the one different item easy to miss.
  // Two or more stale imports are one row that opens to the list; conclusions blocked by the same missing input are
  // one row naming each. Nothing is dropped: every item keeps its date, source and its own Dismiss.
  function _rowHTML(fact, source, action, dismissFps) {
    return '<div style="padding:10px 0;border-bottom:1px solid var(--steel);font-size:12px;color:var(--slate);line-height:1.7">'
      + fact + '<div style="font-size:11px;color:var(--slate-2)">' + source + '</div>'
      + '<div style="margin-top:4px">' + action
      + ' <button class="btn btn-sm btn-secondary" data-gw-dismiss-all="' + esc(JSON.stringify(dismissFps)) + '">Dismiss</button></div></div>';
  }

  function _groupedHTML(items) {
    var stale = items.filter(function (i) { return i.kind === 'import_stale'; });
    var blocked = items.filter(function (i) { return i.kind === 'blocked_conclusion'; });
    var sameMissing = blocked.length > 1;      // every blocked conclusion is answered by the one Verify step
    var out = [], staleDone = false, blockedDone = false;
    items.forEach(function (i) {
      if (i.kind === 'import_stale' && stale.length > 1) {
        if (staleDone) return;
        staleDone = true;
        var least = Math.min.apply(null, stale.map(function (s) { return s.days; }));
        out.push(_rowHTML('<strong>' + stale.length + ' accounts</strong> haven\'t been imported for ' + least + '+ days.'
            + '<details style="margin-top:2px"><summary style="cursor:pointer;font-size:11px">Which ones</summary>'
            + stale.map(function (s) {
              return '<div>' + esc(s.title) + ': last imported ' + _date(s.last_import) + ', ' + s.days + ' days ago'
                + ' <button class="btn btn-ghost btn-sm" style="font-size:11px" data-gw-dismiss="' + esc(A.fingerprint(s)) + '">Dismiss</button></div>';
            }).join('') + '</details>',
          'From when each account\'s transactions were last imported. An account kept by hand is never listed.',
          '<button class="btn btn-sm btn-secondary" onclick="showView(\'ledger\')">Import</button>',
          stale.map(function (s) { return A.fingerprint(s); })));
        return;
      }
      if (blocked.indexOf(i) !== -1 && sameMissing) {
        if (blockedDone) return;
        blockedDone = true;
        var names = blocked.map(function (b) { return '<strong>' + esc(b.title) + '</strong>'; });
        out.push(_rowHTML(names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1] + ' can\'t be assessed yet. Missing: '
            + blocked.map(function (b) { return esc(b.missing.join('; ')) + ' (' + esc(b.title) + ')'; }).join('; ') + '.',
          'From what your Financial Record holds so far. One step answers all of them.',
          '<button class="btn btn-sm btn-secondary" onclick="_recordStatusAction()">Verify account balances →</button>',
          blocked.map(function (b) { return A.fingerprint(b); })));
        return;
      }
      out.push(_itemHTML(i));
    });
    return out.join('');
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
    var kept = [];
    try { kept = ((await API.get('/api/byb/receipt-dates')) || {}).dates || []; } catch (e) { _gwErr('dashboard receipt dates')(e); }
    var fsa = [];                                            // item 86 F5: only when an HSA or FSA account exists
    if ((S.accounts || []).some(function (a) { return a.type === 'fsa'; })) {
      try { fsa = ((await API.get('/api/accounts/hsa-fsa')) || {}).attention || []; } catch (e) { _gwErr('dashboard fsa')(e); }
    }
    var bills = [];                                          // item 94 L6: only what the bills you typed in establish
    try { bills = ((await API.get('/api/medical-bills')) || {}).attention || []; } catch (e) { _gwErr('dashboard bills')(e); }
    var items = A.build({
      payments: payments,
      imports: A.importsStale(stale),
      blocked: A.blockedConclusions(conf, hasRecord),
      dates: A.datesEnding(kept, new Date()),
      fsa: A.fsaDeadlines(fsa),
      bills: A.billsDue(bills)
    }, (_prefs && _prefs.dismissed) || []);
    var head = '<div class="card-label" style="margin-bottom:4px">Needs attention</div>';
    try { _tiles(imports, items, payments); } catch (e) { _gwErr('dashboard tiles')(e); }
    if (!items.length) {
      host.innerHTML = '<div class="card mb-5">' + head + '<div style="font-size:12px;color:var(--slate)">Nothing needs'
        + ' attention.' + (conf.overall === 'ready' ? ' Financial Record: up to date.' : '') + '</div></div>';
      return;
    }
    host.innerHTML = '<div class="card mb-5">' + head + _groupedHTML(items) + '</div>';
  }

  async function _dismiss(fps) {          // one fingerprint, or a group's list (item 79 U5)
    try {
      var r = null;
      for (var fp of [].concat(fps)) r = await API.post('/api/dashboard/dismiss', { fingerprint: fp });
      if (_prefs && r) _prefs.dismissed = r.dismissed || [];
    } catch (e) { _gwErr('dashboard dismiss')(e); return; }
    _renderAttention();
  }

  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.closest) return;
    var d = t.closest('[data-gw-dismiss]');
    if (d) { ev.preventDefault(); _dismiss(d.getAttribute('data-gw-dismiss')); return; }
    var da = t.closest('[data-gw-dismiss-all]');
    if (da) { ev.preventDefault(); try { _dismiss(JSON.parse(da.getAttribute('data-gw-dismiss-all'))); } catch (e) { _gwErr('dashboard dismiss all')(e); } return; }
    var rd = t.closest('[data-gw-receipt-done]');            // item 73 Y2: the person handled a trial or return date
    if (rd) {
      ev.preventDefault();
      API.post('/api/byb/receipt-dates/' + encodeURIComponent(rd.getAttribute('data-gw-receipt-done')) + '/done', {})
        .then(_renderAttention).catch(_gwErr('dashboard receipt done'));
      return;
    }
    var a = t.closest('[data-gw-arrange]');
    if (a) { ev.preventDefault(); _arrange(a.getAttribute('data-gw-arrange'), a.getAttribute('data-gw-tile')); return; }
    if (t.id === 'gwArrangeToggle') { ev.preventDefault(); _arranging = !_arranging; _applyLayout(); }
  });

  async function render() {
    _style();
    _mount();
    if (!_prefs) await _loadPrefs();
    _applyLayout();
    var ask = GWTeaching._modules.filter(function (x) { return x.name === 'asktile'; })[0];   // loads after this file
    if (ask) { try { ask.mod.render(_prefs); } catch (e) { _gwErr('dashboard ask')(e); } }
    await _renderAttention();
  }

  // After the user adds a tile (item 28), the prefs are read again: the server is the one source (R1).
  async function reload() { _prefs = null; await render(); }

  var original = window.renderDashboard;
  window.renderDashboard = function () {
    var out = original.apply(this, arguments);
    try { render(); } catch (e) { /* never break the page under it */ }
    return out;
  };

  _style();
  GWTeaching.register('dashboard', { render: render, reload: reload });
})();
