/*
 * Item 111 X3 (gw 2.0/TRANSFERS.md, ruled 2026-10-26): Settings lists the standing statements the person made about
 * money moving between two of their accounts ("Yes, every time between these two"), each with Undo. Undo adds a
 * withdrawal on the server; nothing is removed. Their statements only - never assumed. Under the Speaking up card,
 * after item 107's list; app.js knows nothing of it.
 */
(function () {
  'use strict';

  function saidHtml(standing) {
    if (!standing || !standing.length) return '';
    return '<div style="font-size:var(--fs-xs);color:var(--slate-2);margin-top:8px">Money you said always moves between your own accounts:</div>'
      + standing.map(function (s) {
          return '<div style="font-size:var(--fs-sm);color:var(--ink);margin-top:4px">' + esc(s.payee) + ', from '
            + esc(s.from) + ' to ' + esc(s.to)
            + ' <span style="font-size:var(--fs-xs);color:var(--slate-2)">(' + esc(String(s.at).slice(0, 10)) + ')</span>'
            + ' <button class="btn btn-ghost btn-sm" data-gw-move-undo="' + esc(String(s.n)) + '">Undo</button></div>';
        }).join('');
  }

  function render() {
    var anchor = document.getElementById('twoAccountsSaid') || document.getElementById('proactiveSilenced');
    if (!anchor) return;
    var box = document.getElementById('ownMovesSaid');
    if (!box) {
      box = document.createElement('div');
      box.id = 'ownMovesSaid';
      anchor.parentNode.insertBefore(box, anchor.nextSibling);
    }
    API.get('/api/own-moves').then(function (r) {
      r = (r && (r.data || r)) || {};
      box.innerHTML = saidHtml(r.standing || []);
      box.onclick = function (ev) {
        var b = ev.target.closest('[data-gw-move-undo]');
        if (!b) return;
        API.post('/api/own-moves/undo', { n: parseInt(b.getAttribute('data-gw-move-undo'), 10) }).then(render).catch(function () {});
      };
    }).catch(function () { box.innerHTML = ''; });
  }

  var originalRenderSettings = window.renderSettings;
  if (typeof originalRenderSettings === 'function') {
    window.renderSettings = function () {
      var out = originalRenderSettings.apply(this, arguments);
      try { render(); } catch (e) { /* teaching never breaks the page under it */ }
      return out;
    };
  }

  GWTeaching.register('ownmoves', { render: render, saidHtml: saidHtml });
})();
