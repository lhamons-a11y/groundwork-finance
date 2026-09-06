/*
 * The Budget surface's teaching (§8).
 *
 * Teaching layer: absent from an LTS bundle by path. The wrap lives here so
 * app.js carries no branch for a feature an LTS build cannot run.
 */
(function () {
  'use strict';

  // A budget page edits amounts. This says what one of those amounts is costing,
  // in the currency the rest of the app prices decisions in — months on the
  // payoff date — and names the envelope the difference could come from.
  let _budgetPressureData = null;

  async function _budgetRenderPressure() {
    const cont = g('budgetContent');
    if (!cont) return;
    try {
      _budgetPressureData = await API.get('/api/budget/pressure');
    } catch (e) {
      _gwErr('_budgetRenderPressure')(e);
      return;                                    // silence beats a guess
    }
    g('budgetPressure')?.remove();
    const html = _budgetPressureHTML(_budgetPressureData);
    if (html) cont.insertAdjacentHTML('beforeend', html);
  }

  function _budgetPressureHTML(d) {
    const rows = (d && d.pressure) || [];
    if (!rows.length || !d.base) return '';

    const one = (o) => {
      // A category on the necessity floor that runs over every month is not a
      // spending problem. The budget is set below what the thing costs, and the
      // honest correction is to the number — E.1 decides which sentence this is,
      // not just which levers may be offered.
      const lead = o.protected
        ? `<strong>${esc(o.name)}</strong> has not come in under
           <strong>${fmt(o.budgeted)}</strong> in ${o.months_observed} months — the budget is set
           <strong style="font-family:var(--font-mono)">${fmt(o.monthly)}/mo</strong> below what it costs.`
        : `<strong>${esc(o.name)}</strong> has run at least
           <strong style="font-family:var(--font-mono)">${fmt(o.monthly)}/mo</strong> over its
           <strong>${fmt(o.budgeted)}</strong> budget in every one of the last ${o.months_observed} months.`;
      const cost = o.months_cost > 0
        ? `That difference costs <strong style="color:var(--ember)">${o.months_cost} month${o.months_cost !== 1 ? 's' : ''}</strong>
           on your debt-free date and <strong style="font-family:var(--font-mono)">${fmt(o.interest_cost)}</strong> in interest.`
        : `It costs <strong>${fmt(o.interest_cost)}</strong> in interest, and does not move your debt-free date.`;
      const fix = o.fix
        ? `Covering it would take <strong style="font-family:var(--font-mono)">${fmt(o.fix.monthly)}/mo</strong>
           from ${esc(_joinNames(o.fix.sources))} — budgeted there, and not spent.`
        : `No other envelope has room to cover it, on what the ledger records.`;
      return `<div style="padding:10px 0;border-bottom:1px solid var(--steel);font-size:12px;color:var(--slate);line-height:1.8">
        ${lead} ${cost} ${fix}
      </div>`;
    };

    return `<div class="card mt-5" id="budgetPressure">
      <div class="card-label">What these amounts cost</div>
      <div style="font-size:12px;color:var(--slate);line-height:1.7;margin-bottom:6px">
        Measured against <strong>${_payoffDateLabel(d.base.months)}</strong>, and counted only where
        the ledger says it held every month. Each line is measured on its own — two of them can
        name the same envelope, because neither is a plan to do both.
      </div>
      ${rows.map(one).join('')}
    </div>`;
  }

  var original = window.renderBudget;
  window.renderBudget = function () {
    var out = original.apply(this, arguments);
    try { _budgetRenderPressure(); } catch (e) { /* never break the page under it */ }
    return out;
  };

  GWTeaching.register('budget', { render: _budgetRenderPressure });
})();
