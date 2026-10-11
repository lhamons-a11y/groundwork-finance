/*
 * The Ledger surface's teaching (§8).
 *
 * Teaching layer: absent from an LTS bundle by path. app.js renders the page
 * and knows nothing about what this adds to it.
 */
(function () {
  'use strict';

  // §8's teaching form for the Ledger: a charge that already happened, in the
  // past tense, with the levers that would put the months back.
  //
  // Past tense is the whole discipline here. Why someone spent it is not
  // knowable from a ledger row, and the sentence has to be about the money
  // rather than about the person — "that money would have bought three months"
  // is a fact; anything with "should" in it is a verdict on a stranger.
  let _ledgerLessonData = null;

  async function _ledgerRenderLesson() {
    const host = g('ledgerLessonSlot') || g('view-ledger');
    if (!host) return;
    try {
      _ledgerLessonData = await API.get('/api/transactions/lesson');
    } catch (e) {
      _gwErr('_ledgerRenderLesson')(e);
      return;                                    // silence beats a guess
    }
    g('ledgerLesson')?.remove();
    const html = _ledgerLessonHTML(_ledgerLessonData);
    if (html) host.insertAdjacentHTML('afterbegin', html);
  }

  function _ledgerLessonHTML(d) {
    if (!d || !d.lesson || !d.charge) return '';
    const l = d.lesson, c = d.charge;
    if (!(l.months_cost >= 1)) return '';

    const when = c.date ? new Date(c.date + 'T00:00:00')
      .toLocaleDateString('en-US', { month: 'long', day: 'numeric' }) : null;

    // One lever, preferring one that needs no cut — the point of the sentence is
    // the arithmetic, not a list of things to do about something already done.
    //
    // Phrased here rather than through _tripPathPhrases, which says "holds the
    // date". Nothing is being held: the date already moved, and the only honest
    // offer is what would put it back.
    const paths = d.paths || [];
    const usable = paths.filter(p => p.items.length && p.months_recovered > 0);
    const pick   = usable.find(p => !p.requires_cut) || usable[0];
    let back = '';
    if (pick) {
      // What it puts back is the measured figure, not the months the charge
      // cost. Those two are close and are not the same computation, and a
      // sentence that rounds one into the other is asserting arithmetic it did
      // not do.
      const r = pick.months_recovered;
      const puts = (r >= l.months_cost)
        ? 'would put them back'
        : `would put ${r} of them back`;
      back = (pick.kind === 'trim')
        ? ` Cutting ${esc(_joinNames(pick.items))}`
          + ` (<strong style="font-family:var(--font-mono)">${fmt(pick.frees_monthly)}/mo</strong>) ${puts}.`
        : ` Shifting <strong style="font-family:var(--font-mono)">${fmt(pick.frees_monthly)}/mo</strong>`
          + ` from ${esc(_joinNames(pick.items))} — budgeted there, and not spent — ${puts}.`;
    }

    return `<div class="card mb-4" id="ledgerLesson">
      <div class="card-label">What that one cost</div>
      <div style="font-size:12px;color:var(--slate);line-height:1.8">
        The <strong style="font-family:var(--font-mono)">${fmt(c.amount)}</strong> at
        <strong>${esc(c.name)}</strong>${when ? ` on ${when}` : ''}: had that money gone to the debt,
        you would be debt-free <strong style="color:var(--pine-text)">${l.months_cost} month${l.months_cost !== 1 ? 's' : ''}</strong>
        sooner, with <strong style="font-family:var(--font-mono)">${fmt(l.interest_cost)}</strong> less interest.${back}
      </div>
    </div>`;
  }

  var original = window.renderLedger;
  window.renderLedger = function () {
    var out = original.apply(this, arguments);
    try { _ledgerRenderLesson(); } catch (e) { /* never break the page under it */ }
    return out;
  };

  GWTeaching.register('ledger', { render: _ledgerRenderLesson });
})();
