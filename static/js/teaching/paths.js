/*
 * Pillar 3's phrasing: the paths that close the gap, said for a person.
 *
 * Teaching layer. Loaded only in a GW 2.0 build; absent from an LTS bundle by
 * path, so LTS does not disable this, it does not contain it.
 *
 * Its own module because two surfaces say the same thing - the trip planner
 * and Before You Buy both offer paths with their costs - and one of them
 * having to import the other would make one surface depend on the other's
 * lifetime for no reason. Composed from the engine's STRUCTURED fields rather
 * than its `detail` string, so month counts render as dates here and the
 * register stays in one place (B.2a).
 */
(function () {
  'use strict';

  // The two impact cells. Date and money are separate facts because they move
  // independently: a payoff date set by loan forgiveness does not shift when you
  // spend, but the interest on everything else still does. Showing only "days
  // later" would render that trip free.
  // Pillar 3: the paths that close the gap, phrased for a person. Composed from
  // the engine's STRUCTURED fields rather than its `detail` string, so month
  // counts render as dates here and the register stays in one place (B.2a).
  //
  // Two at most. E.4 says show the top paths with their costs and let the user
  // choose; it does not say show all of them, and this page is already busy.
  // The Willingness Layer's two contributions to a path (WILLINGNESS_LAYER.md
  // W-B / W-C). Where a candidate is flexible by the user's record or their own
  // word, the path says which; and every category a path names can be answered
  // where it stands - "never Dining" - which is F.3's in-context channel. Both
  // come from willingness.js; without it (it is a sibling module, not a
  // dependency) the phrase is exactly what it was.
  function _flexibleNote(items) {
    const flex = (items || []).filter(i => i.willingness && i.willingness.stance === 'flexible');
    if (!flex.length) return '';
    const said  = flex.filter(i => i.willingness.source === 'declared').map(i => i.name);
    const shown = flex.filter(i => i.willingness.source !== 'declared').map(i => i.name);
    const parts = [];
    if (shown.length) parts.push(`your record shows ${esc(_joinNames(shown.map(n => ({ name: n }))))} has moved before`);
    if (said.length)  parts.push(`you marked ${esc(_joinNames(said.map(n => ({ name: n }))))} flexible`);
    return ` (${parts.join('; ')})`;
  }

  function _answerable(categories, proposal) {
    if (typeof window._gwDeclareInline !== 'function') return '';
    const seen = {};
    return categories.filter(c => c && !seen[c.toLowerCase()] && (seen[c.toLowerCase()] = true))
      .map(c => window._gwDeclareInline(c, proposal)).join('');
  }

  function _tripPathPhrases(paths, gap, unit = '') {
    // Take the top two by rank — but never drop the only path that actually
    // closes the gap. Ranking puts no-cut paths first (E.3 rule 1), and a closing
    // path usually requires a cut, so a naive slice can show two partial options
    // and silently hide the one that works.
    //
    // One of each kind, when both exist. The levers split in two: substitution
    // changes the decision on this page, everything else changes the finances
    // around it. Ranked strictly, substitution loses every time — it requires
    // giving something up, and E.3 rule 1 puts that below waiting — so the price
    // of the very thing the user is looking at would never once be shown. Two
    // answers to different questions beat two answers to the same one.
    const all  = paths || [];
    const sub  = all.find(p => p.kind === 'substitution');
    const rest = all.filter(p => p.kind !== 'substitution');
    let picked = sub ? [rest[0], sub].filter(Boolean) : rest.slice(0, 2);
    if (picked.length && !picked.some(p => p.closes)) {
      const closer = all.find(p => p.closes);
      if (closer) picked = picked.slice(0, 1).concat([closer]);
    }
    return picked.map(p => {
      const absorbed = (p.cost_months != null && gap != null) ? gap - p.cost_months : null;
      const part = (absorbed && absorbed > 0)
        ? `absorbs ${absorbed} of the ${gap}`
        : 'absorbs part of it';

      if (p.kind === 'timing') {
        const who   = p.label.replace(/^wait for /, '');
        const when  = p.available_in_months != null ? _monthsFromNowLabel(p.available_in_months) : null;
        const freed = p.frees_monthly ? `, freeing ${fmt(p.frees_monthly)}/mo` : '';
        const lead  = when ? `${esc(who)} clears in ${when}${freed}` : `${esc(who)} clears${freed}`;
        return p.closes ? `${lead}, which holds the date` : `${lead} — that ${part}`;
      }
      if (p.kind === 'payoff_order') {
        return p.closes
          ? `paying in ${esc(p.label.replace(/^pay in /, ''))} holds the date`
          : `paying in ${esc(p.label.replace(/^pay in /, ''))} ${part}`;
      }
      if (p.kind === 'reallocation') {
        // The receipt travels with the offer. "Shift $205/mo from Shopping" on
        // its own is a suggestion about someone's life; with the months behind
        // it, it is a statement about their record that they can check.
        const items = p.items || [];
        const seen  = items.map(i => i.months_observed).filter(m => m > 0);
        const proof = seen.length ? ` — budgeted, not spent, in ${Math.min(...seen)} recorded months —` : '';
        const lead  = `shifting ${fmt(p.frees_monthly)}/mo from ${esc(_joinNames(items))}${_flexibleNote(items)}${proof}`;
        const said  = `shifting ${fmt(p.frees_monthly)}/mo from ${_joinNames(items)}`;
        return (p.closes ? `${lead} holds the date` : `${lead} ${part}`)
          + _answerable(items.map(i => i.name), said);
      }
      if (p.kind === 'trim') {
        const items = p.items || [];
        const cost  = items.length > 1
          ? `${fmt(p.frees_monthly)}/mo between them`
          : `${fmt(p.frees_monthly)}/mo`;
        const lead  = `cutting ${esc(_joinNames(items))} (${cost})${_flexibleNote(items.map(i => ({ ...i, name: i.category })))}`;
        return (p.closes ? `${lead} holds the date` : `${lead} ${part}`)
          + items.map(i => _answerable([i.category], `cutting ${i.name}, in ${i.category}`)).join('');
      }
      if (p.kind === 'substitution') {
        // The price of the same decision, against what it costs in time. The
        // engine has no idea what a cheaper version of anything IS; it says only
        // what a smaller number would do to the date, which is the user's own
        // arithmetic and claims nothing about what is out there to buy.
        //
        // The engine prices two rungs — half the delay, and none of it — and this
        // renders the first. "Costs 2 months instead of 4" already carries the
        // relationship between price and time, which is the teaching; the second
        // rung is about one month of surplus whatever the decision costs, so
        // beside a $40,000 ask it reads as mockery rather than as an option. It
        // stays in the payload for a surface that prices a purchase directly.
        const rungs = p.items || [];
        const head  = rungs[0];
        if (!head) return esc(p.detail);
        // `unit` is '/mo' when the decision is a commitment rather than a
        // purchase. Same lever, same arithmetic, and the difference between
        // "$302.00" and "$302.00/mo" is the difference between a true sentence
        // and one off by the length of a car loan.
        return head.months_delta
          ? `a ${fmt(head.price)}${unit} version costs ${head.months_delta} month`
            + `${head.months_delta !== 1 ? 's' : ''} instead of ${gap}`
          : `a ${fmt(head.price)}${unit} version does not move the date`;
      }
      if (p.kind === 'monthly') {
        return esc(p.detail);
      }
      return esc(p.detail);
    });
  }

  // "A", "A and B", "A, B and C" — the engine names one to three things per
  // path, and a person reads the result.

  // Shared across the teaching layer, not with app.js: this is the one
  // direction the seam allows, and nothing in app.js may reach for it.
  window._tripPathPhrases = _tripPathPhrases;
  GWTeaching.register('paths', { phrases: _tripPathPhrases });
})();
