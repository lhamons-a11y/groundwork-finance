/*
 * Item 107 D8 (gw 2.0/SAME_CHARGE_TWO_ACCOUNTS.md, ruled 2026-10-21): Settings lists what the person said about a
 * payee paid from two accounts, each with Undo. Undo adds a withdrawal on the server; nothing is removed. Their
 * statements only - nothing inferred, and nothing else reads them (D9). Under the Speaking up card, beside
 * #proactiveSilenced; app.js knows nothing of it.
 */
(function () {
  'use strict';

  var WORDS = { both_meant: 'Both are meant', should_stop: 'One of these should stop', not_same: "These aren't the same" };

  function saidHtml(said) {
    if (!said || !said.length) return '';
    return '<div style="font-size:11px;color:var(--slate-2);margin-top:8px">What you said about charges paid from two accounts:</div>'
      + said.map(function (s) {
          return '<div style="font-size:12px;color:var(--ink);margin-top:4px">' + esc(s.payee) + ', $'
            + Number(s.amount).toFixed(2) + ': ' + esc(WORDS[s.answer] || s.answer)
            + ' <span style="font-size:11px;color:var(--slate-2)">(' + esc(String(s.at).slice(0, 10)) + ')</span>'
            + ' <button class="btn btn-ghost btn-sm" data-gw-two-undo="' + esc(String(s.n)) + '">Undo</button></div>';
        }).join('');
  }

  function render() {
    var anchor = document.getElementById('proactiveSilenced');
    if (!anchor) return;
    var box = document.getElementById('twoAccountsSaid');
    if (!box) {
      box = document.createElement('div');
      box.id = 'twoAccountsSaid';
      anchor.parentNode.insertBefore(box, anchor.nextSibling);
    }
    API.get('/api/two-accounts').then(function (r) {
      r = (r && (r.data || r)) || {};
      box.innerHTML = saidHtml(r.said || []);
      box.onclick = function (ev) {
        var b = ev.target.closest('[data-gw-two-undo]');
        if (!b) return;
        API.post('/api/two-accounts/undo', { n: parseInt(b.getAttribute('data-gw-two-undo'), 10) }).then(render).catch(function () {});
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

  GWTeaching.register('twoaccounts', { render: render, saidHtml: saidHtml });
})();
