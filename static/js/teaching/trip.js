/*
 * What a trip costs the payoff date, and what would hold it.
 *
 * Teaching layer. Loaded only in a GW 2.0 build; absent from an LTS bundle by
 * path, so LTS does not disable this, it does not contain it. An LTS trip
 * planner still plans the trip and still shows what it costs and what the
 * surplus is - what it does not do is price it in months.
 *
 * THE DEPENDENCY RUNS ONE WAY. This file reads app.js's globals and wraps its
 * renders, and app.js knows nothing about it. app.js writes a plain summary
 * into #tripPayoffImpact and its own honest save-first line; both are
 * overwritten here when the engine has an answer for the trip on screen, and
 * both stand on their own when it does not.
 */
(function () {
  'use strict';

  let _tripImpactData  = null;  // Pillar 1 decision_impact for the CURRENT trip total
  let _tripImpactKey   = '';    // the rounded total the above is valid for
  let _tripImpactTimer = null;

  // Pillar 1: what the trip actually costs the payoff date, from the server's
  // consequence engine (core/consequence.py). Debounced exactly like the distance
  // fetch, because the total changes on every keystroke.
  //
  // This replaced Math.round((total / income) * 30), which was never a simulation
  // at all — it ignored balances, APRs, minimums and payoff order, and understated
  // the truth by 4.4x to 17.4x, worst for the tightest budgets. Never blocks the
  // render: the cells read "—" until this resolves, which is the honest state
  // rather than a guess.
  function _maybeLoadTripImpact(total) {
    const rounded = Math.round(total || 0);
    const key = String(rounded);
    if (key === _tripImpactKey) return;
    if (!(rounded > 0)) { _tripImpactData = null; _tripImpactKey = key; return; }
    clearTimeout(_tripImpactTimer);
    _tripImpactTimer = setTimeout(async () => {
      try {
        _tripImpactData = await API.post('/api/debt/decision-impact', { one_time_cost: rounded });
        _tripImpactKey  = key;
      } catch (e) {
        _gwErr('_maybeLoadTripImpact')(e);
        _tripImpactData = null;
      }
      tripUpdateBudget();
    }, 600);
  }

  function _tripImpactCells(d) {
    if (!d || !d.base) return '';                 // no debt, or not loaded yet
    const undated = (d.undated_forgiveness || []).length > 0;
    const months  = d.months_delta;
    const interest = d.interest_delta;

    let dateVal, dateSub, dateStyle = '';
    if (undated || months === null || months === undefined) {
      dateVal = '—';
      dateSub = undated
        ? `needs the payment count for ${esc(d.undated_forgiveness[0])}`
        : 'not calculated';
    } else if (months === 0) {
      // Deliberately NOT green. This is the absence of one cost, not good news.
      dateVal = 'no change';
      dateSub = d.base.conditional_on_certification
        ? 'forgiveness sets the date' : 'same payoff month';
    } else {
      dateVal = `+${months} month${months !== 1 ? 's' : ''}`;
      dateSub = 'later than planned';
      dateStyle = ' style="color:var(--gold)"';
    }

    const hasInterest = typeof interest === 'number' && interest > 0;
    return `
        <div class="trip-cell">
          <div class="trip-cell-label">Debt-free impact</div>
          <div class="trip-cell-value"${dateStyle}>${dateVal}</div>
          <div class="trip-cell-sub">${dateSub}</div>
        </div>
        <div class="trip-cell">
          <div class="trip-cell-label">Added interest</div>
          <div class="trip-cell-value"${hasInterest ? ' style="color:var(--gold)"' : ''}>${hasInterest ? '+' + fmt(interest) : '—'}</div>
          <div class="trip-cell-sub">${hasInterest ? 'over the payoff' : 'not calculated'}</div>
        </div>`;
  }

  // Phase 5A: fetch the real national-average gas price once per view visit,
  // then re-run the budget calc so the estimate uses it instead of the old
  // hardcoded $3.40. Never blocks the initial render — tripUpdateBudget()
  // falls back to the same $3.40 until this resolves (or forever, if no EIA
  // key is configured — see gas_price.py's honest degrade path).

  function renderSentence() {
    var el = document.getElementById('tripPayoffImpact');
    if (!el || !_tripBudgetData) return;
    var total = _tripBudgetData.total;
    var surplus = _tripBudgetData.surplus;
    var impact = el;
    {
      // Pillar 2's teaching sentence: cause -> effect -> a lever the user controls.
      // The lever is a number the consequence engine solved for (the smallest
      // sustained monthly increase that cancels the delay). It deliberately does
      // NOT name a category — "trim dining $40/mo" needs the Solution Engine to
      // know dining is flexible for this person, and inventing that is the
      // fabrication R8 exists to stop. "More toward debt" is still a lever they
      // control; which envelope it comes from is theirs to choose.
      //
      // Rounded UP to the nearest $5: rounding down would state a figure that
      // does not actually hold the date.
      const d = _tripImpactData;
      const lever = (d && typeof d.offsetting_monthly === 'number' && d.offsetting_monthly > 0)
        ? Math.ceil(d.offsetting_monthly / 5) * 5 : null;
      if (d && d.base && (d.undated_forgiveness || []).length === 0
          && typeof d.months_delta === 'number' && d.months_delta > 0) {
        const base = _monthsFromNowLabel(d.base.months);
        impact.innerHTML = `This trip moves your debt-free date from <strong>${base}</strong> `
          + `to <strong>${_monthsFromNowLabel(d.after.months)}</strong> — ${d.months_delta} month`
          + `${d.months_delta !== 1 ? 's' : ''} later.`;
        // Pillar 3: the paths, with their costs, so the choice is the user's (E.4).
        // The generic monthly lever is already one of them, so it is not repeated.
        const phrases = _tripPathPhrases(d.paths, d.months_delta);
        if (phrases.length) {
          const joined = phrases.join('; ');
          impact.innerHTML += ` ${joined.charAt(0).toUpperCase()}${joined.slice(1)}.`;
        } else if (lever) {
          impact.innerHTML += ` Putting <strong>${fmt(lever)}/mo</strong> more toward debt keeps it at ${base}.`;
        }
        // §6.4: never a bare "you can't" — when nothing holds the date, say so
        // bounded to today's numbers rather than as a permanent verdict (App. C).
        if (d.honest_no) {
          // C.4: an honest no is never just a no. It carries the nearest lever —
          // the smallest change that would hold the date — and, when the record
          // can name money, what that money comes to, so the user can see the
          // size of the difference rather than guess at it.
          //
          // The figure is stated, not urged. It is necessarily larger than what
          // this user directs at debt today (anything smaller would have closed
          // the gap as a path, and this branch would not have run), so offering
          // it would be pushing; saying what the arithmetic requires is not.
          // Rounded UP for the same reason the lever is: rounded down, it does
          // not actually hold the date.
          const hn = d.honest_no;
          impact.innerHTML += ` On today's numbers nothing holds the date entirely.`;
          if (hn.nearest_monthly > 0) {
            const need = Math.ceil(hn.nearest_monthly / 5) * 5;
            impact.innerHTML += ` The smallest change that would is `
              + `<strong>${fmt(need)}/mo</strong> more toward debt`
              + (hn.named_total > 0
                  ? `, against the <strong>${fmt(hn.named_total)}/mo</strong> your record can name.`
                  : `.`);
          }
          // Lever 7 (§6.1), and only here. Patience is the answer of last resort:
          // beside a path that already holds the date it is noise, but beside an
          // honest no it is the one thing still true. It is not a path — counted
          // as one it would hold every date ever asked about and leave the honest
          // no with nothing to say.
          const dnFar = d.do_nothing;
          if (dnFar && dnFar.free_from_months > 0) {
            impact.innerHTML += ` Waiting is the other answer: you are debt-free in `
              + `<strong>${_monthsFromNowLabel(dnFar.free_from_months)}</strong>, and after `
              + `that this costs no months at all.`;
          }
        }
      } else if (d && d.base && d.months_delta === 0 && d.interest_delta > 0) {
        impact.innerHTML = d.base.conditional_on_certification
          ? `Your payoff date is set by loan forgiveness, so this trip does not move it — it adds `
            + `<strong>${fmt(d.interest_delta)}</strong> in interest on your other balances.`
          : `This trip does not move your payoff date. It adds <strong>${fmt(d.interest_delta)}</strong> in interest.`;
        // Lever 7 (§6.1): do-nothing, quantified. Nothing here needs fixing, and
        // the proof is the one check a user is most likely to wonder about. The
        // engine stays quiet when the other order would actually be better —
        // that case is a path, and saying both would be the software arguing
        // with itself.
        const dn = d.do_nothing;
        if (dn && dn.optimal_order && dn.optimal_order.months_better > 0) {
          const o = dn.optimal_order;
          impact.innerHTML += ` Nothing needs to change: your ${esc(o.strategy)} order clears you `
            + `<strong>${o.months_better} month${o.months_better !== 1 ? 's' : ''}</strong> sooner `
            + `than ${esc(o.alternative)} would.`;
        }
      } else {
        impact.innerHTML = `Estimated trip cost: <strong>${fmt(total)}</strong>. Your monthly surplus is <strong>${fmt(surplus)}</strong>.`;
      }
    }
  }

  function renderCells() {
    var cells = document.getElementById('tripBudgetCells');
    if (!cells) return;
    var old = cells.querySelector('[data-gw-impact]');
    if (old) old.remove();
    var html = _tripImpactCells(_tripImpactData);
    if (!html) return;
    var slot = document.createElement('div');
    slot.setAttribute('data-gw-impact', '1');
    slot.style.display = 'contents';
    slot.innerHTML = html;
    cells.appendChild(slot);
  }

  function renderAll() {
    if (_tripBudgetData) _maybeLoadTripImpact(_tripBudgetData.total);
    renderCells();
    renderSentence();
  }

  var originalBudget = window.tripUpdateBudget;
  window.tripUpdateBudget = function () {
    var out = originalBudget.apply(this, arguments);
    try { renderAll(); } catch (e) { /* teaching never breaks the page under it */ }
    return out;
  };

  // Lever 6: saving out of the money now going to debt, priced by the engine.
  // app.js divides the trip by the page's surplus, which is the honest answer
  // when nothing prices it against debt and the wrong pool when something does.
  var originalFunding = window._renderFundingDetail;
  window._renderFundingDetail = function () {
    var out = originalFunding.apply(this, arguments);
    try {
      var detail = document.getElementById('tripFundDetail');
      if (detail && _tripFunding === 'save' && _tripBudgetData) {
            // Lever 6 (§6.1), from the engine rather than from a division. The line
            // this replaces divided the trip by the page's "surplus" — the money left
            // AFTER the debt payment — while the sentence directly above it prices the
            // same trip against the money going INTO that payment. Two pools, two
            // answers, one page, and the cheerful one was the one with no cost in it.
            const plan = _tripImpactData && _tripImpactData.save_first;
            if (plan && plan.months_to_save) {
              const m = plan.months_to_save;
              let line = `Save <strong>${fmt(plan.monthly)}/month</strong> for ${m} month${m!==1?'s':''} `
                + `out of the money now going to debt — ready by <strong>${_monthsFromNowLabel(m)}</strong>.`;
              if (plan.months_delta > 0) {
                // The part the old line left out, and the reason this lever is not
                // offered as a way to close the gap: saving does not dodge the cost.
                line += ` Saving first does not shorten the ${plan.months_delta}-month delay — `
                  + `the same money leaves your debt either way — but it is paid for before you go, `
                  + `not out of the months after.`;
              }
              detail.innerHTML = line;
            }
      }
    } catch (e) { /* teaching never breaks the page under it */ }
    return out;
  };

  GWTeaching.register('trip', { render: renderAll });
})();
