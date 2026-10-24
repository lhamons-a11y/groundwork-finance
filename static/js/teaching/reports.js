/*
 * The Reports surface's teaching (§8).
 *
 * Teaching layer: absent from an LTS bundle by path. The wrap lives here so
 * app.js carries no branch for a feature an LTS build cannot run.
 */
(function () {
  'use strict';

  // §8's line for Reports: the causal teaching layer, made explicit,
  // lever-oriented and proof-cited. Rendered deterministically, above the
  // narrative and independent of it — the blueprint's stack puts the model BELOW
  // the teaching layer, so losing narration must not mean losing the lesson.
  // Every figure here is one another surface already shows; the report gathers
  // them rather than deriving its own.
  let _rcTeachingData = null;

  async function _rcRenderMonthlyTeaching() {
    const host = g('rcMonthlyTeaching');
    if (!host) return;
    try {
      _rcTeachingData = await API.get('/api/debt/teaching');
    } catch (e) {
      _gwErr('_rcRenderMonthlyTeaching')(e);
      return;
    }
    host.innerHTML = _rcTeachingHTML(_rcTeachingData);
  }

  // One sentence per finding, written here rather than by the model. The measured
  // reason is sharper than the principle: inference-smuggling ran 37–70% on every
  // model tested and rose with size, so a causal claim composed by a narrator is
  // the one thing the evidence says not to build (MODEL_PLACEMENT.md).
  function _rcTeachingSentence(f) {
    const mo = (n) => `${n} month${n !== 1 ? 's' : ''}`;
    if (f.kind === 'charge') {
      return `The ${esc(f.subject)} charge cost <strong>${mo(f.months)}</strong> on your debt-free date`
           + ` and <strong>${fmt(f.interest)}</strong> in interest — had that money gone to the debt instead.`;
    }
    if (f.kind === 'overspend') {
      // Item 46 C2: necessary care is described, never priced in months.
      return f.protected
        ? `<strong>${esc(f.subject)}</strong> is budgeted <strong>${fmt(f.monthly)}/mo</strong> below what it`
          + ` has cost every month on record.`
        : `<strong>${esc(f.subject)}</strong> ran at least <strong>${fmt(f.monthly)}/mo</strong> over budget`
          + ` every month on record, which costs <strong>${mo(f.months)}</strong> and`
          + ` <strong>${fmt(f.interest)}</strong> in interest.`;
    }
    if (f.kind === 'lever') {
      return `The single change that moves your date most: <strong>${esc(f.subject)}</strong> —`
           + ` <strong>${mo(f.months)}</strong> sooner and <strong>${fmt(f.interest)}</strong> less interest,`
           + ` if that money went to the debt.`;
    }
    if (f.kind === 'fund') {
      const at = f.pace_source === 'observed' ? 'at the pace actually being kept' : 'at the planned pace';
      return `<strong>${esc(f.subject)}</strong> lands <strong>${mo(f.months)}</strong> past its own deadline`
           + ` ${at}; <strong>${fmt(f.monthly)}/mo</strong> more would make it.`;
    }
    return '';
  }

  function _rcTeachingHTML(d) {
    const rows = (d && d.findings) || [];
    // Panel I-03: with no payoff date there is nothing to price against - say so, with the gap, rather than nothing
    if (!rows.length && d && d.reason === 'below_minimums') {
      return `<div class="card"><div class="card-label">What this month cost, and what changes it</div><div style="font-size:13px;color:var(--slate);line-height:1.6">`
        + `Your debt budget, ${fmt(d.budget)} a month, is ${fmt(d.gap)} below the ${fmt(d.minimums)} in minimums owed, so there is no payoff date to measure a change against. `
        + `Debt Payoff can set the budget to your minimums.</div></div>`;
    }
    if (!rows.length && d && d.reason === 'never_clears') {
      return `<div class="card"><div class="card-label">What this month cost, and what changes it</div><div style="font-size:13px;color:var(--slate);line-height:1.6">`
        + `At ${fmt(d.budget)} a month the debt doesn't clear within 30 years, so there is no payoff date to measure a change against.</div></div>`;
    }
    if (!rows.length) return '';

    // B.1: show your work. The proof is the figures the claim rests on, printed
    // beside it rather than promised — a claim whose numbers are not on the page
    // is asking to be taken on trust, which is the thing this app does not do.
    const proof = (f) => (f.proof || [])
      .filter(p => p.value !== null && p.value !== undefined && p.value !== '')
      .map(p => {
        // Formatted by the unit the server states, never guessed from the label.
        // Sniffing for the word "month" printed a month count as $13.00 and a
        // dollars-per-month figure as a bare 105.
        const v = (p.unit === 'money') ? fmt(p.value)
                : (p.unit === 'months') ? `${p.value} mo`
                : esc(String(p.value));
        return `${esc(p.label)}: ${v}`;
      })
      .join(' · ');

    return `<div class="card">
      <div class="card-label">What this month cost, and what changes it</div>
      <div style="font-size:12px;color:var(--slate);line-height:1.7;margin-bottom:10px">
        Computed from your ledger, not written by the AI. Each line shows the figures behind it.
      </div>
      ${rows.map(f => `
        <div style="padding:10px 0;border-bottom:1px solid var(--steel)">
          <div style="font-size:12px;color:var(--slate);line-height:1.8">${_rcTeachingSentence(f)}</div>
          <div style="font-size:10px;font-family:var(--font-mono);color:var(--slate-2);margin-top:4px">${proof(f)}</div>
        </div>`).join('')}
    </div>`;
  }

  var original = window._rcRenderMonthlyReport;
  window._rcRenderMonthlyReport = function () {
    var out = original.apply(this, arguments);
    try { _rcRenderMonthlyTeaching(); } catch (e) { /* never break the page under it */ }
    return out;
  };

  GWTeaching.register('reports', { render: _rcRenderMonthlyTeaching });
})();
