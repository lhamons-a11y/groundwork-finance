/*
 * Section 8 on the savings goals: where each fund lands at the pace actually
 * being kept, and the lever that moves that date.
 *
 * Teaching layer. Loaded only in a GW 2.0 build; absent from an LTS bundle by
 * path, so LTS does not disable this, it does not contain it.
 *
 * THE DEPENDENCY RUNS ONE WAY. This file reads app.js's globals and wraps its
 * render, and app.js knows nothing about it. The sentence used to be a single
 * ${...} inside the row template, which is why it stayed behind when the other
 * six surfaces moved: there was no way to put it back from out here without
 * the row saying which fund it was. It says so now - data-fund-id, which is
 * ordinary markup that costs an LTS build one attribute and no behaviour.
 */
(function () {
  'use strict';

  // §8's causal pace narration for a fund: where it lands at the pace being
  // kept, and the lever that moves that date.
  //
  // The pace it reports is the OBSERVED one where the record can carry it and
  // the planned one otherwise, and the sentence says which. A finish date
  // computed from a plan is a statement about the plan; calling it a projection
  // of behaviour would borrow certainty from data that does not exist.
  function _sfPaceSentence(p) {
    if (!p || p.funded || !p.finish_months) return '';

    // F.8 (BREAK_DETECTOR.md ruling 6): when what goes in changed level, only
    // the months since count - and when there are too few of them, the date is
    // the plan's and the sentence says why, rather than borrowing the old pace.
    const brk = p.since_break;
    const since = brk ? _breakMonth(brk.month) : '';
    let at = (p.pace_source === 'observed')
      ? (brk ? `at the ${fmt(p.pace_monthly)}/mo you have put in since ${since}, when what goes in changed`
             : `at the ${fmt(p.pace_monthly)}/mo you have actually been putting in`)
      : `at the planned ${fmt(p.pace_monthly)}/mo`;
    if (brk && p.insufficient_since_break) {
      at = `what goes in changed in ${since}, from about ${fmt(brk.before)}/mo to about ${fmt(brk.after)}/mo, and`
         + ` there are too few months since then to set a pace from - so at the planned ${fmt(p.pace_monthly)}/mo`;
    }
    const lands = `lands <strong>${_monthsFromNowLabel(p.finish_months)}</strong>`;

    let verdict;
    if (p.on_track === true) {
      verdict = `— ahead of the deadline`;
    } else if (p.on_track === false) {
      verdict = `— <span style="color:var(--gold-text)">past the deadline</span>`;
    } else {
      verdict = '';                                // no deadline: a date, nothing missed
    }

    let lever = '';
    if (p.lever) {
      lever = ` <strong style="font-family:var(--font-mono)">${fmt(p.lever.monthly)}/mo</strong> more`
            + ` — from ${esc(_joinNames(p.lever.sources))} — would bring it to`
            + ` <strong>${_monthsFromNowLabel(p.lever.finish_months)}</strong>.`;
    } else if (p.on_track === false && p.short_monthly > 0) {
      // The gap is real and nothing in the record covers it. Saying so is the
      // honest no: what is missing, and that no envelope here can supply it.
      lever = ` It would take <strong style="font-family:var(--font-mono)">${fmt(p.short_monthly)}/mo</strong>`
            + ` more to make the deadline, and nothing in your record has that room.`;
    }

    return `<div style="font-size:11px;color:var(--slate);line-height:1.7;margin-top:4px">
      ${at.charAt(0).toUpperCase()}${at.slice(1)}, this ${lands} ${verdict}.${lever}
    </div>`;
  }

  function _breakMonth(m) {
    var p = String(m).split('-').map(Number);
    return new Date(p[0], p[1] - 1, 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  }

  function render() {
    var section = document.getElementById('budgetSinkingFundsCard');
    if (!section) return;
    var rows = section.querySelectorAll('[data-fund-id]');
    if (!rows.length) return;

    API.get('/api/sinking-funds/pace').then(function (paced) {
      var byId = {};
      (paced.funds || []).forEach(function (f) { byId[f.id] = f.pace; });
      Array.prototype.forEach.call(rows, function (row) {
        // Rendered again on every re-render, so the old sentence goes first -
        // otherwise a fund gains a paragraph every time the budget page moves.
        var old = row.querySelector('[data-gw-pace]');
        if (old) old.remove();
        var html = _sfPaceSentence(byId[row.getAttribute('data-fund-id')]);
        if (!html) return;
        var slot = document.createElement('div');
        slot.setAttribute('data-gw-pace', '1');
        slot.innerHTML = html;
        // The row's TEXT column - the flex:1 one holding the name, the bar and
        // the percentages - not whatever div happens to come last. Appended to
        // the wrong one, the sentence lands inside the icon-and-text flex row
        // and overlaps the figures beside it.
        (row.querySelector('[style*="flex:1"]') || row).appendChild(slot);
      });
    }).catch(_gwErr('teaching/funds:pace'));
  }

  // Item 112 P3: a fund notices what it paid for. A recent charge near what a fund holds, or its target, is asked
  // about once - "Is this what you were saving for?" - and a yes takes it out of the fund (the roof was paid and the
  // fund still said 18 months to go). The person's answer, with Undo.
  function purchases() {
    var section = document.getElementById('budgetSinkingFundsCard');
    if (!section) return;
    API.get('/api/sinking-funds/purchases').then(function (r) {
      var old = section.querySelector('[data-gw-fund-purchase]');
      if (old) old.remove();
      var qs = (r && r.questions) || [];
      if (!qs.length) return;
      var box = document.createElement('div');
      box.setAttribute('data-gw-fund-purchase', '');
      box.innerHTML = qs.map(function (q) {
        var when = q.date ? new Date(q.date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
        return '<div style="margin:0 0 10px;padding:10px 12px;border:0.5px solid var(--pine-border);border-radius:8px;background:var(--pine-bg);font-size:12px;color:var(--ink);line-height:1.6">'
          + 'The <strong style="font-family:var(--font-mono)">' + fmt(q.amount) + '</strong> at <strong>' + esc(q.payee) + '</strong>' + (when ? ' on ' + when : '')
          + ' is close to what <strong>' + esc(q.fund) + '</strong> holds (' + fmt(q.held) + '). Is this what you were saving for? '
          + '<button class="btn btn-secondary btn-sm" data-gw-fp="yes" data-fund="' + q.fund_id + '" data-txn="' + q.txn_id + '">Yes, take it from the fund</button> '
          + '<button class="btn btn-ghost btn-sm" data-gw-fp="no" data-fund="' + q.fund_id + '" data-txn="' + q.txn_id + '">No</button></div>';
      }).join('');
      section.insertBefore(box, section.firstChild);
      box.querySelectorAll('[data-gw-fp]').forEach(function (b) {
        b.addEventListener('click', function () { answer(+b.dataset.fund, +b.dataset.txn, b.dataset.gwFp); });
      });
    }).catch(_gwErr('teaching/funds:purchases'));
  }

  function answer(fundId, txnId, said) {
    API.post('/api/sinking-funds/purchases/answer', { fund_id: fundId, txn_id: txnId, answer: said }).then(function (r) {
      var title = said === 'yes'
        ? (r.done ? r.fund + ': done - ' + fmt(r.spent) + ' paid from it' : r.fund + ': ' + fmt(r.spent) + ' paid from it, ' + fmt(r.left) + ' left')
        : 'Kept: that was not from ' + r.fund;
      showToast(title, '', 'success', function () {
        API.post('/api/sinking-funds/purchases/undo', r.undo).then(function () { loadSinkingFunds(); });
      });
      loadSinkingFunds();
    }).catch(function (e) { showToast('Could not keep that', e.message || '', 'error'); });
  }

  // The wrap. app.js renders the section and has no idea this happens after.
  var original = window._budgetRenderSinkingFundsSection;
  window._budgetRenderSinkingFundsSection = function () {
    var out = original.apply(this, arguments);
    // The render is async: the rows do not exist until it settles.
    Promise.resolve(out).then(function () {
      try { render(); purchases(); } catch (e) { /* teaching never breaks the page under it */ }
    });
    return out;
  };

  GWTeaching.register('funds', { render: render });
})();
