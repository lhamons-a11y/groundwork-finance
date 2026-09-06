/*
 * The Networth surface's teaching (§8).
 *
 * Teaching layer: absent from an LTS bundle by path. app.js renders the page
 * and knows nothing about what this adds to it.
 */
(function () {
  'use strict';

  // §8's teaching form for Net Worth: what the number now enables, which is a
  // balance the user could cover outright rather than a round number crossed.
  // A milestone at $10,000 is a milestone invented by whoever picked $10,000.
  let _nwCapacityData = null;

  async function _nwRenderCapacity() {
    const host = g('nwCapacitySlot') || g('view-networth');
    if (!host) return;
    try {
      _nwCapacityData = await API.get('/api/debt/capacity');
    } catch (e) {
      _gwErr('_nwRenderCapacity')(e);
      return;                                    // silence beats a guess
    }
    g('nwCapacity')?.remove();
    const html = _nwCapacityHTML(_nwCapacityData);
    if (html) host.insertAdjacentHTML('beforeend', html);
  }

  function _nwCapacityHTML(d) {
    const rows = (d && d.capacity) || [];
    if (!rows.length || !d.base) return '';
    const c = rows[0];                           // the one that moves the date most

    const outcome = c.clears_all_debt
      ? `would clear the last balance you carry — debt-free now instead of
         <strong>${_payoffDateLabel(d.base.months)}</strong>`
      : `would free <strong style="font-family:var(--font-mono)">${fmt(c.frees_monthly)}/mo</strong>
         and bring your debt-free date <strong style="color:var(--pine)">${c.months_saved} month${c.months_saved !== 1 ? 's' : ''}</strong>
         sooner, with <strong style="font-family:var(--font-mono)">${fmt(c.interest_saved)}</strong> less interest`;

    return `<div class="card mb-5" id="nwCapacity">
      <div class="card-label">What this number now covers</div>
      <div style="font-size:12px;color:var(--slate);line-height:1.8">
        Your savings and cash (<strong style="font-family:var(--font-mono)">${fmt(d.liquid)}</strong>)
        now cover what you owe on <strong>${esc(c.name)}</strong>
        (<strong style="font-family:var(--font-mono)">${fmt(c.balance)}</strong>). Clearing it ${outcome}.
        <span style="color:var(--slate-2)">
          It would not move your net worth today — the same money crosses from one side to the other —
          and <strong style="font-family:var(--font-mono)">${fmt(c.liquid_after)}</strong> would be left,
          about ${c.months_of_expenses_after} month${c.months_of_expenses_after !== 1 ? 's' : ''}
          of your recorded expenses.
        </span>
      </div>
    </div>`;
  }

  var original = window.renderNetWorth;
  window.renderNetWorth = function () {
    var out = original.apply(this, arguments);
    try { _nwRenderCapacity(); } catch (e) { /* never break the page under it */ }
    return out;
  };

  GWTeaching.register('networth', { render: _nwRenderCapacity });
})();
