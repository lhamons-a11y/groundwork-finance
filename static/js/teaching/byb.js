/*
 * Pillar 5 on Before You Buy: the record of what this person has actually
 * decided, read back to them.
 *
 * Teaching layer. Loaded only in a GW 2.0 build; absent from an LTS bundle by
 * path, so LTS does not disable this, it does not contain it.
 *
 * THE DEPENDENCY RUNS ONE WAY. This file reads app.js's globals and wraps its
 * renders, and app.js knows nothing about it.
 *
 * Two sentences, deliberately in different places, and the split survives the
 * move. Estimate bias belongs where a number is being typed, because it
 * corrects that number. The walkaway record belongs in the history, not in the
 * middle of a decision - the same fact reads as a receipt in one place and as
 * a nudge in the other, and this app does not nudge.
 */
(function () {
  'use strict';

  // Pillar 5 (§7): the memory. These decisions have been logged since Phase H1
  // and nothing has ever read them back.
  //
  // Two sentences, deliberately in different places. Estimate bias belongs where
  // a number is being typed, because it corrects that number. The walkaway record
  // belongs in the history, not in the middle of a decision — the same fact reads
  // as a receipt in one place and as a nudge in the other, and this app does not
  // nudge.
  let _bybMemoryData = null;

  async function _bybLoadMemory() {
    try {
      _bybMemoryData = await API.get('/api/byb/memory');
    } catch (e) {
      _gwErr('_bybLoadMemory')(e);
      _bybMemoryData = null;
    }
  }

  function _bybMemoryHTML() {
    const m = _bybMemoryData;
    if (!m || !m.decisions) return '';
    const parts = [];

    // A count is a receipt at any size; a RATE needs enough decisions to be one,
    // and the reader withholds it below three rather than dressing two up as a
    // pattern. Either way this is a record and never a prediction: what someone
    // did is theirs, what they will do is nobody's to state.
    parts.push(`You have decided <strong>${m.decisions}</strong> of these`
      + ` — <strong>${m.commits}</strong> committed, <strong>${m.walkaways}</strong> walked away`
      + (m.walkaway_rate_pct != null ? ` (${m.walkaway_rate_pct}%)` : '') + `.`);

    if (m.estimate && m.estimate.direction !== 'even') {
      const e = m.estimate;
      parts.push(` Across the ${e.samples} you priced afterwards, the real cost came in`
        + ` <strong>${Math.abs(e.bias_pct)}%</strong> ${e.direction === 'under' ? 'above' : 'below'}`
        + ` your estimate.`);
    }
    return `<div class="card mb-3" style="font-size:12px;color:var(--slate);line-height:1.8">
      ${parts.join('')}
    </div>`;
  }

  // The estimate-bias half, for the step where the estimate is typed.
  function _bybEstimateBiasNote() {
    const e = _bybMemoryData && _bybMemoryData.estimate;
    if (!e || e.direction === 'even') return '';
    const over = e.direction === 'under';
    return `<div style="font-size:11px;color:var(--slate-2);line-height:1.6;margin-top:6px">
      Your last ${e.samples} priced purchases came in
      <strong>${Math.abs(e.bias_pct)}%</strong> ${over ? 'above' : 'below'} what you estimated.
    </div>`;
  }

  // Fetched once. The guard is on the data, so a render that lands before the
  // fetch does not loop: it asks, and re-renders when the answer arrives.
  var asked = false;

  function ensure(andThen) {
    if (_bybMemoryData !== null) { andThen(); return; }
    if (asked) return;
    asked = true;
    _bybLoadMemory().then(andThen).catch(_gwErr('teaching/byb:memory'));
  }

  function renderList() {
    var cont = document.getElementById('bybContent');
    // Not on the empty state: app.js renders a "nothing evaluated yet" guide
    // there, and a record of decisions belongs above decisions, not above an
    // invitation to make a first one.
    if (!cont || !(S.bybItems && S.bybItems.length)) return;
    ensure(function () {
      var old = document.getElementById('gwBybMemory');
      if (old) old.remove();
      var html = _bybMemoryHTML();
      if (!html) return;
      var slot = document.createElement('div');
      slot.id = 'gwBybMemory';
      slot.innerHTML = html;
      cont.insertBefore(slot, cont.firstChild);
    });
  }

  function renderBias() {
    var prev = document.getElementById('bybStep1Preview');
    if (!prev) return;
    ensure(function () {
      var bias = document.getElementById('bybEstimateBias');
      if (!bias) {
        bias = document.createElement('div');
        bias.id = 'bybEstimateBias';
        prev.appendChild(bias);
      }
      bias.innerHTML = _bybEstimateBiasNote();
    });
  }

  // The wraps. app.js renders both surfaces and has no idea this happens after.
  var originalList = window._renderBYBList;
  window._renderBYBList = function () {
    var out = originalList.apply(this, arguments);
    try { renderList(); } catch (e) { /* teaching never breaks the page under it */ }
    return out;
  };

  var originalLive = window._bybLiveUpdate;
  window._bybLiveUpdate = function () {
    var out = originalLive.apply(this, arguments);
    try { renderBias(); } catch (e) { /* teaching never breaks the page under it */ }
    return out;
  };

  // What the engine says about a commitment, in at most two sentences: the price
  // this could cost and still leave the date alone (§6.1's "$220/mo instead of
  // $350"), and the best path that is not about the price — one lever of each
  // kind, the same rule the trip planner follows.
  // Pillar 4 (§7, Appendix D): "you freed $180/mo, this fits." It fires only
  // when the freed capacity actually covers what is being weighed, and only when
  // the freeing was something the user DID — a balance that ran out on its
  // minimums is the expected floor, and D.4 is explicit that praising a floor
  // erodes trust.
  let _bybGreenLight = null;

  async function _bybLoadGreenLight() {
    try {
      const r = await API.get('/api/debt/green-light');
      _bybGreenLight = r.green_light || null;
    } catch (e) {
      _gwErr('_bybLoadGreenLight')(e);
      _bybGreenLight = null;
    }
  }

  function _bybGreenLightHTML() {
    const gl = _bybGreenLight;
    const monthly = parseFloat(_byb.monthly) || 0;
    if (!gl || !monthly || monthly > gl.freed_monthly) return '';

    // D.5: name one or two drivers by size, or say plainly that it was diffuse.
    // Naming the largest and implying it was the whole story is a cherry-pick.
    const from = gl.diffuse
      ? 'a lot of small changes'
      : _joinNames(gl.drivers);
    // D.5 again: recency governs the tense, not the fact.
    const lead = gl.fresh
      ? `You freed <strong style="font-family:var(--font-mono)">${fmt(gl.freed_monthly)}/mo</strong> by clearing ${esc(from)}`
      : `Your plan now carries <strong style="font-family:var(--font-mono)">${fmt(gl.freed_monthly)}/mo</strong> it did not, from ${esc(from)}`;

    // The half that keeps this from being cheerleading: it fits, AND it spends
    // what was earned. A green light that only says yes is applause.
    const worth = gl.months_sooner
      ? `, capacity worth <strong>${gl.months_sooner} month${gl.months_sooner !== 1 ? 's' : ''}</strong> on your date`
      : '';
    return `<div style="font-size:12px;color:var(--pine-text);line-height:1.8;margin-bottom:10px">
      ${lead}${worth}. This <strong style="font-family:var(--font-mono)">${fmt(monthly)}/mo</strong>
      fits inside it, and uses <strong style="font-family:var(--font-mono)">${fmt(monthly)}</strong> of it.
    </div>`;
  }

  function _bybEngineNote() {
    const eng = _bybEngineData();
    const m = eng && eng.monthly;
    if (!m) return _bybGreenLightHTML();

    if (m.honest_no && m.honest_no.unaffordable) {
      // Not a longer delay — a wall. The number is what makes it payable at all.
      const cap = m.honest_no.max_payable_monthly;
      return `<div style="font-size:12px;color:var(--ember-text);line-height:1.7;margin-bottom:12px">`
        + (cap
            ? `At <strong>${fmt(cap)}/mo</strong> or less this stays payable. Above that your `
              + `minimum payments stop being covered, which is not a later date — it is no date at all.`
            : `No version of this leaves your minimum payments covered.`)
        + `</div>`;
    }
    if (!m.gap_months || m.gap_months <= 0) return '';

    // The trip line shows two phrases and lets a closing path displace the price
    // one, because it has a sentence to fit in. This screen has room, and the
    // price IS the decision here — so the closing path is ADDED rather than
    // swapped in, and the guard that says never hide a path that actually holds
    // the date still holds.
    const paths = m.paths || [];
    const sub   = paths.find(p => p.kind === 'substitution');
    const rest  = paths.filter(p => p.kind !== 'substitution');
    const picks = [];
    if (rest[0]) picks.push(rest[0]);
    if (sub) picks.push(sub);
    if (!picks.some(p => p.closes)) {
      const closer = paths.find(p => p.closes);
      if (closer && picks.indexOf(closer) === -1) picks.push(closer);
    }
    const phrases = picks
      .map(p => _tripPathPhrases([p], m.gap_months, '/mo')[0])
      .filter(Boolean);
    if (!phrases.length) return _bybGreenLightHTML();
    const joined = phrases.join('; ');
    return _bybGreenLightHTML()
      + `<div style="font-size:12px;color:var(--slate);line-height:1.7;margin-bottom:12px">`
      + `${joined.charAt(0).toUpperCase()}${joined.slice(1)}.</div>`;
  }

  function renderEngineNote() {
    var anchor = document.getElementById('bybChangeFromOriginal');
    if (!anchor) return;
    var old = document.getElementById('gwBybEngineNote');
    if (old) old.remove();
    var html = _bybEngineNote();
    if (!html) return;
    var slot = document.createElement('div');
    slot.id = 'gwBybEngineNote';
    slot.innerHTML = html;
    anchor.insertAdjacentElement('afterend', slot);
  }

  var originalComparison = window._bybBuildComparison;
  window._bybBuildComparison = function () {
    var out = originalComparison.apply(this, arguments);
    try { renderEngineNote(); } catch (e) { /* teaching never breaks the page */ }
    return out;
  };

  // Pillar 4's evidence is fetched once when the wizard opens.
  var originalOpen = window.openBYBWizard;
  window.openBYBWizard = function () {
    var out = originalOpen.apply(this, arguments);
    try { _bybLoadGreenLight().then(renderEngineNote).catch(function () {}); }
    catch (e) { /* teaching never breaks the page under it */ }
    return out;
  };

  GWTeaching.register('byb', { renderList: renderList, renderBias: renderBias,
                              renderEngineNote: renderEngineNote });
})();
