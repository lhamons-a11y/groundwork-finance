/*
 * The Trophy Room's receipts: which trophies are proven, which are waiting on
 * evidence, and which were never trophies (core/trophies.py, Appendix B.3).
 *
 * Teaching layer. Loaded only in a GW 2.0 build; absent from an LTS bundle by
 * path, so LTS does not disable this, it does not contain it. An LTS Trophy
 * Room is the 1.x one: the same trophies, awarded the 1.x way, without the
 * receipt under each card and without the evidence-based awarding below.
 *
 * THE DEPENDENCY RUNS ONE WAY. This file reads app.js's globals and wraps its
 * render, and app.js knows nothing about it. The receipt used to be a single
 * ${...} inside the card template, which is why it stayed behind; the card
 * carries data-ach-id now, which is ordinary markup naming what it shows.
 */
(function () {
  'use strict';

  // The pinned standard, as the room sees it: which trophies are proven, which
  // are waiting on evidence, and which were never trophies (core/trophies.py).
  let _trophyVerdicts = {};

  async function _loadTrophyVerdicts() {
    try {
      const r = await API.get('/api/trophies');
      _trophyVerdicts = Object.fromEntries((r.trophies || []).map(t => [t.id, t]));
      _awardProvenTrophies();
    } catch (e) {
      _gwErr('_loadTrophyVerdicts')(e);
      _trophyVerdicts = {};
    }
  }

  // Award what the ledger proves, and never take anything back.
  //
  // Only ever additive. An unproven trophy is unproven, not false — 1.x awarded
  // these before any receipt existed — and an earned trophy is a receipt of a
  // real past, so nothing here revokes one. The server is the authority on
  // whether the proof exists, because the proof is in the ledger and the ledger
  // is the server's.
  function _awardProvenTrophies() {
    Object.values(_trophyVerdicts).forEach(v => {
      if (v.earned === true && v.class !== 'setup' && !S.achievements.has(v.id)) {
        awardAchievement(v.id);
      }
    });
  }

  // The receipt, or an honest note about why there isn't one. A trophy awarded
  // before any of this existed is not retroactively false — it is unproven, and
  // saying that is better than either dropping it or dressing it up.
  function _trophyReceipt(id) {
    const v = _trophyVerdicts[id];
    if (!v) return '';
    if (v.class === 'setup') {
      return `<div style="font-size:10px;color:var(--slate-2);margin-top:5px">Setup step — not an earned trophy.</div>`;
    }
    const proof = (v.proof || [])
      .filter(p => p.value !== null && p.value !== undefined && p.value !== '')
      .map(p => {
        const val = p.unit === 'money' ? fmt(p.value)
                  : p.unit === 'percent' ? `${p.value}%`
                  : esc(String(p.value));
        return `${esc(p.label)}: ${val}`;
      }).join(' · ');

    if (v.earned === true) {
      return `<div style="font-size:10px;font-family:var(--font-mono);color:var(--pine-text);margin-top:5px">
        ${proof || 'proved by your ledger'}
      </div>`;
    }
    if (v.earned === null) {
      return `<div style="font-size:10px;color:var(--slate-2);margin-top:5px">${esc(v.reason)}</div>`;
    }
    return '';
  }

  function render() {
    var cards = document.querySelectorAll('[data-ach-id]');
    if (!cards.length) return;
    API.get('/api/trophies').then(function (r) {
      _trophyVerdicts = Object.fromEntries((r.trophies || []).map(function (t) {
        return [t.id, t];
      }));
      // The awarding is evidence-based and only ever additive: the server is
      // the authority on whether the proof exists, because the proof is in the
      // ledger and the ledger is the server's.
      _awardProvenTrophies();
      Array.prototype.forEach.call(cards, function (card) {
        var old = card.querySelector('[data-gw-receipt]');
        if (old) old.remove();
        var html = _trophyReceipt(card.getAttribute('data-ach-id'));
        if (!html) return;
        var slot = document.createElement('div');
        slot.setAttribute('data-gw-receipt', '1');
        slot.innerHTML = html;
        // The card's TEXT column, not the flex row that holds the icon beside
        // it: appended to the row, a receipt becomes a third flex item and
        // renders off to the right of the trophy it belongs to.
        (card.querySelector('[style*="flex:1"]') || card).appendChild(slot);
      });
    }).catch(function (e) {
      _gwErr('teaching/trophies')(e);
      _trophyVerdicts = {};
    });
  }

  // The wrap. app.js renders the room and has no idea this happens after.
  var original = window._renderTrophyContent;
  window._renderTrophyContent = function () {
    var out = original.apply(this, arguments);
    try { render(); } catch (e) { /* teaching never breaks the page under it */ }
    return out;
  };

  GWTeaching.register('trophies', { render: render });
})();
