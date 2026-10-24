/*
 * Ask for a tile (gw 2.0/ASK_FOR_A_TILE.md, item 28, ruled 2026-10-01 with build requirements R1-R7).
 *
 * Teaching layer: absent from an LTS bundle by path. dashboard.js calls render(prefs) after it lays out the tiles.
 *
 * The request only MATCHES (K2): the server compares its words with a closed catalogue and names one entry or none.
 * Nothing is added until the user confirms. An entry the record can't back says what it needs (K3). No match is an
 * honest no, and the words are kept in a list the user can see and delete - as their words, read by nothing else,
 * sent nowhere (K4). Numbers on an added tile come from the engines, never from a model (proof, not persuasion).
 * The model matcher (K7, last) is not part of this first build.
 */
(function () {
  'use strict';

  var _prefs = null;

  // Snapshot dates come two ways: a day ('2026-08-31', saved by the user) or a month ('2026-10', the app's own
  // monthly snapshot). A month is shown as a month - never invented into a day (found in the page run).
  function _date(iso) {
    var s = String(iso || '');
    var p = s.slice(0, 10).split('-').map(Number);
    if (/^\d{4}-\d{2}$/.test(s)) {
      return new Date(p[0], p[1] - 1, 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
    }
    return new Date(p[0], p[1] - 1, p[2]).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function _tiletext() {
    var m = GWTeaching._modules.filter(function (x) { return x.name === 'tiletext'; })[0];
    return m && m.mod;
  }

  function _box() {
    var box = g('gwAsk');
    if (box) return box;
    var head = g('gwSummaryHead');
    if (!head) return null;
    box = document.createElement('div');
    box.id = 'gwAsk';
    box.style.cssText = 'margin:0 0 12px';
    head.parentNode.insertBefore(box, head.nextSibling);
    return box;
  }

  // R4 / R5: the user's own words are escaped, capped by the server, and marked - so the BANNED lexicon, which
  // checks Groundwork's wording, never reads them as Groundwork's.
  function _requestsHTML(reqs) {
    if (!reqs || !reqs.length) return '';
    return '<div style="font-size:var(--fs-xs);color:var(--slate-2);margin-top:8px">Your requests Groundwork can\'t show yet:</div>'
      + reqs.slice().reverse().map(function (r) {
        return '<div style="display:flex;gap:8px;align-items:center;font-size:var(--fs-sm);padding:3px 0">'
          + '<span data-gw-user-words style="flex:1;color:var(--slate)">“' + esc(r.text) + '”</span>'
          + '<span style="font-size:var(--fs-xs);color:var(--slate-2)">' + _date(r.at) + '</span>'
          + '<button class="btn btn-sm btn-secondary" data-gw-ask-delete data-at="' + esc(r.at) + '" data-text="' + esc(r.text) + '">Delete</button></div>';
      }).join('');
  }

  function _draw(result) {
    var box = _box();
    if (!box) return;
    box.innerHTML = '<div style="display:flex;gap:8px">'
      + '<input id="gwAskInput" class="input" maxlength="200" placeholder="Ask for a tile - e.g. net worth over time"'
      + ' style="flex:1;font-size:var(--fs-sm)">'
      + '<button class="btn btn-sm btn-secondary" data-gw-ask>Ask</button></div>'
      + '<div id="gwAskResult" style="font-size:var(--fs-sm);color:var(--slate);margin-top:6px">' + (result || '') + '</div>'
      + _requestsHTML(_prefs && _prefs.requests);
  }

  async function _ask() {
    var input = g('gwAskInput');
    var text = input ? input.value.trim() : '';
    if (!text) return;
    // R7: the page never waits blind - the model matcher may take a few seconds, so say so while it does.
    var res = g('gwAskResult');
    if (res) res.textContent = 'Looking\u2026';
    var r;
    try { r = await API.post('/api/dashboard/ask', { text: text }); }
    catch (e) { _gwErr('ask for a tile')(e); return; }
    var out;
    if (r.match && r.match.shown) {
      out = '‘' + esc(r.match.title) + '’ is already on your dashboard.';
    } else if (r.match && !r.backed) {
      out = esc(r.needs);
    } else if (r.match) {
      out = 'Add ‘' + esc(r.match.title) + '’ to your summary? '
        + '<button class="btn btn-sm btn-secondary" data-gw-ask-add="' + esc(r.match.id) + '">Add</button> '
        + '<button class="btn btn-sm btn-secondary" data-gw-ask-no>No</button>';
    } else {
      if (_prefs) _prefs.requests = r.requests || _prefs.requests;
      out = 'Groundwork can\'t show that yet. Your request is kept below, in your words.';
    }
    _draw(out);
  }

  async function _add(id) {
    try { await API.post('/api/dashboard/add', { id: id }); }
    catch (e) { _gwErr('ask for a tile: add')(e); _draw('That tile could not be added.'); return; }
    var dash = GWTeaching._modules.filter(function (x) { return x.name === 'dashboard'; })[0];
    if (dash) await dash.mod.reload();
  }

  async function _delete(at, text) {
    try {
      var r = await API.post('/api/dashboard/requests/delete', { at: at, text: text });
      if (_prefs) _prefs.requests = r.requests || [];
    } catch (e) { _gwErr('ask for a tile: delete')(e); return; }
    _draw('');
  }

  // The catalogue entries beyond the seven: where each reads from, and which words say it. R3: when a chosen
  // tile's evidence is gone, it says what it needs in place.
  var TILES = {
    gwNetWorthTrendCard: { url: '/api/dashboard/tile/net-worth', words: 'netWorth' },
    gwFundsCard: { url: '/api/dashboard/tile/funds', words: 'funds' },
    gwRecurringCard: { url: '/api/dashboard/tile/recurring', words: 'recurring' },
    gwEnergyCard: { url: '/api/dashboard/tile/energy', words: 'energy' },
    gwPictureCard: { url: '/api/dashboard/tile/picture', words: 'picture' }
  };
  var F = { money: function (n) { return fmt(n); }, date: _date, month: _date };

  async function _fillTile(id) {
    var card = g(id);
    var T = _tiletext();
    if (!card || !T) return;
    var spec = TILES[id] || (id.indexOf('cat:') === 0
      ? { url: '/api/dashboard/tile/category?name=' + encodeURIComponent(id.slice(4)), words: 'category' } : null);
    if (!spec) return;
    var d = null;
    try { d = await API.get(spec.url); }
    catch (e) { _gwErr('dashboard tile ' + id)(e); return; }
    var t = T[spec.words](d, F);
    if (!t) return;
    var title = (_prefs && _prefs.titles && _prefs.titles[id]) || id;
    card.innerHTML = '<div class="card-label">' + esc(title) + '</div>'
      + t.lines.map(function (l) { return '<div style="font-size:var(--fs-sm);color:var(--slate);line-height:1.7">' + esc(l) + '</div>'; }).join('')
      + (id === 'gwPictureCard' && d && d.backed ? '<div style="margin-top:6px"><button class="btn btn-sm btn-secondary" onclick="showView(\'picture\')">Open the working picture</button></div>' : '')
      + (t.source ? '<div class="gw-src" style="font-size:var(--fs-xs);color:var(--slate-2);margin-top:8px">' + esc(t.source) + '</div>' : '');
    card.style.display = '';
  }

  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.closest) return;
    if (t.closest('[data-gw-ask]')) { ev.preventDefault(); _ask(); return; }
    var a = t.closest('[data-gw-ask-add]');
    if (a) { ev.preventDefault(); _add(a.getAttribute('data-gw-ask-add')); return; }
    if (t.closest('[data-gw-ask-no]')) { ev.preventDefault(); _draw(''); return; }
    var d = t.closest('[data-gw-ask-delete]');
    if (d) { ev.preventDefault(); _delete(d.getAttribute('data-at'), d.getAttribute('data-text')); }
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter' && ev.target && ev.target.id === 'gwAskInput') { ev.preventDefault(); _ask(); }
  });

  function render(prefs) {
    _prefs = prefs;
    if (!g('gwAskInput')) _draw('');
    ((prefs && prefs.layout && prefs.layout.added) || []).forEach(function (id) { _fillTile(id); });
  }

  GWTeaching.register('asktile', { render: render });
})();
