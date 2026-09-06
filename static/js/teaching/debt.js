/*
 * The Debt Payoff surface's teaching (§8's row, and Appendix G's checkpoints).
 *
 * Teaching layer: absent from an LTS bundle by path. app.js renders the advisor
 * tab and knows nothing about what this appends to it — the wrap is here, not a
 * hook there, because a hook would be dead weight in every LTS build.
 */
(function () {
  'use strict';

  // Appendix G, passively. G.3a is precise about where each state may appear:
  // "below the prior peak" is already visible in the ordinary debt surfaces and G
  // does not repeat it, so only the approaching and past checkpoints get a
  // sentence here — and even those reach the dashboard only through the Gauntlet,
  // never as a channel of their own.
  let _debtCycleData = null;

  async function _debtRenderCycle() {
    const container = g('debtAdvisorSection');
    if (!container) return;
    try {
      const r = await API.get('/api/debt/cycle');
      _debtCycleData = r.cycle || null;
    } catch (e) {
      _gwErr('_debtRenderCycle')(e);
      return;
    }
    g('debtCycle')?.remove();
    const html = _debtCycleHTML(_debtCycleData);
    if (html) container.insertAdjacentHTML('beforeend', html);
  }

  function _debtCycleHTML(c) {
    if (!c || !c.prior) return '';
    if (c.state !== 'approaching' && c.state !== 'past') return '';

    const peakWhen = c.prior.peak_month
      ? new Date(c.prior.peak_month + '-01T00:00:00')
          .toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
      : null;
    // The cost of the last cycle travels with the comparison, and only when it
    // was actually recorded — "$0 to get out last time" from a missing figure
    // would be a receipt for something that never happened.
    const cost = (c.prior.interest !== null && c.prior.interest !== undefined)
      ? ` That cycle cost <strong style="font-family:var(--font-mono)">${fmt(c.prior.interest)}</strong> in interest to get out of.`
      : '';

    const line = (c.state === 'past')
      ? `You are carrying <strong style="font-family:var(--font-mono)">${fmt(c.current)}</strong>,
         more than the <strong style="font-family:var(--font-mono)">${fmt(c.prior.peak)}</strong>
         you were carrying${peakWhen ? ` in ${peakWhen}` : ''}, before you cleared it.`
      : `You are within <strong style="font-family:var(--font-mono)">${fmt(c.distance)}</strong>
         of the <strong style="font-family:var(--font-mono)">${fmt(c.prior.peak)}</strong>
         you were carrying${peakWhen ? ` in ${peakWhen}` : ''}, before you cleared it.`;

    return `<div class="card mb-5" id="debtCycle" style="border-left:3px solid var(--gold)">
      <div class="card-label">You have been here before</div>
      <div style="font-size:12px;color:var(--slate);line-height:1.8">${line}${cost}</div>
    </div>`;
  }

  // The levers pointed at the plan itself rather than at a decision, from the
  // engine and from the user's own record. The slider above this asks "what would
  // $200 more do"; this answers "where would $200 come from, and which one moves
  // the date furthest" — which is the question the slider leaves the user to
  // answer alone.
  let _debtAccelData = null;

  async function _debtRenderAccelerations() {
    const container = g('debtAdvisorSection');
    if (!container) return;
    try {
      _debtAccelData = await API.get('/api/debt/accelerations');
    } catch (e) {
      _gwErr('_debtRenderAccelerations')(e);
      return;                                  // silence beats a guess
    }
    g('debtAccelerations')?.remove();
    const html = _debtAccelerationsHTML(_debtAccelData);
    if (html) container.insertAdjacentHTML('beforeend', html);
  }

  function _debtAccelerationsHTML(d) {
    if (!d || !d.base) return '';
    const rows = d.accelerations || [];
    const dn   = d.do_nothing;

    if (!rows.length) {
      // Lever 7. An empty list is an answer, and it is only worth printing with
      // the proof attached — without a number "you're on track" is flattery.
      if (!dn || !dn.optimal_order || !(dn.optimal_order.months_better > 0)) return '';
      const o = dn.optimal_order;
      return `<div class="card mb-5" id="debtAccelerations">
        <div class="card-label">What moves your date most</div>
        <div style="font-size:12px;color:var(--slate);line-height:1.7">
          Nothing in your record moves it further than the plan you already have.
          Your ${esc(o.strategy)} order clears you
          <strong style="color:var(--pine)">${o.months_better} month${o.months_better !== 1 ? 's' : ''}</strong>
          sooner than ${esc(o.alternative)} would.
        </div>
      </div>`;
    }

    const line = (a) => `
      <div style="display:flex;align-items:baseline;justify-content:space-between;gap:14px;padding:9px 0;border-bottom:1px solid var(--steel)">
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;color:var(--ink)">${esc(a.label.charAt(0).toUpperCase() + a.label.slice(1))}</div>
          <div style="font-size:11px;color:var(--slate-2);line-height:1.6">${esc(a.detail)}</div>
        </div>
        <div style="text-align:right;white-space:nowrap">
          <div style="font-family:var(--font-mono);font-size:13px;color:var(--pine)">${a.months_saved} mo sooner</div>
          <div style="font-family:var(--font-mono);font-size:11px;color:var(--slate-2)">${fmt(a.interest_saved)} less interest</div>
        </div>
      </div>`;

    return `<div class="card mb-5" id="debtAccelerations">
      <div class="card-label">What moves your date most</div>
      <div style="font-size:12px;color:var(--slate);line-height:1.7;margin-bottom:10px">
        From <strong>${_payoffDateLabel(d.base.months)}</strong>, on what your ledger already records.
        Each of these is one change on its own — not a plan to do all of them — and each
        assumes the money freed goes toward the debt.
      </div>
      ${rows.map(line).join('')}
    </div>`;
  }

  // The wraps. loadDebtAdvisor is app.js's own; it runs, then this runs.
  var originalLoadDebtAdvisor = window.loadDebtAdvisor;
  window.loadDebtAdvisor = function () {
    var out = originalLoadDebtAdvisor.apply(this, arguments);
    try { _debtRenderAccelerations(); _debtRenderCycle(); } catch (e) { /* never break the page */ }
    return out;
  };

  GWTeaching.register('debt', {
    accelerations: _debtRenderAccelerations,
    cycle: _debtRenderCycle
  });
})();
