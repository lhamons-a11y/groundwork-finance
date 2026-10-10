/*
 * Appendix A — the one place the app speaks first.
 *
 * Teaching layer. Loaded only in a GW 2.0 build; absent from an LTS bundle by
 * path, so LTS does not disable this, it does not contain it.
 *
 * THE DEPENDENCY RUNS ONE WAY. This file reads app.js's globals and wraps its
 * render, and app.js knows nothing about it. That is why the wrap is here
 * rather than a call being there: a hook in app.js would be a dead branch in
 * every LTS build, which is the seam collapsing into a runtime flag.
 *
 * Its own container, too. A slot sitting in index.html for a feature that does
 * not exist is the same dead weight in smaller form.
 */
(function () {
  'use strict';

  var prompt = null;
  var asked = false;

  function host() {
    var view = document.getElementById('view-dashboard');
    if (!view) return null;
    var el = document.getElementById('dashProactive');
    if (!el) {
      el = document.createElement('div');
      el.id = 'dashProactive';
      view.insertBefore(el, view.firstChild);
    }
    return el;
  }

  function html(p) {
    var mo = function (n) {
      return Math.abs(n) + ' month' + (Math.abs(n) !== 1 ? 's' : '');
    };
    var green = p.kind === 'green';
    var body = '';
    if (p.detail_kind === 'charge') {
      body = 'The <strong>' + fmt(p.dollars) + '</strong> at <strong>' + esc(p.subject)
           + '</strong> cost <strong>' + mo(p.months) + '</strong> on your debt-free date.'
           + ' There is a way to put them back — it is on the ledger page.';
    } else if (p.detail_kind === 'overspend') {
      body = '<strong>' + esc(p.subject) + '</strong> has run <strong>' + fmt(p.dollars)
           + '/mo</strong> over its budget every month on record, which costs <strong>'
           + mo(p.months) + '</strong> on your debt-free date. The budget page shows where'
           + ' that could come from.';
    } else if (p.detail_kind === 'cycle') {
      var c = p.cycle || {};
      var cost = (c.prior && c.prior.interest != null)
        ? ' That one cost <strong>' + fmt(c.prior.interest) + '</strong> in interest to get out of.'
        : '';
      body = (c.state === 'past')
        ? 'You are carrying more than the <strong>' + fmt((c.prior || {}).peak)
          + '</strong> you carried before you cleared this last time.' + cost
        : 'You are within <strong>' + fmt(c.distance) + '</strong> of the <strong>'
          + fmt((c.prior || {}).peak) + '</strong> you carried before you cleared this'
          + ' last time.' + cost;
    } else if (p.detail_kind === 'clarification') {
      // W-D: asked, never applied - a question about which they mean, never a reproach
      body = 'You marked <strong>' + esc(p.subject) + '</strong> ' + (p.stance === 'protect' ? 'protected' : 'flexible')
           + ' on ' + esc(p.said_at) + '. Since then you lowered its budget from <strong>' + fmt(p.cut_old)
           + '</strong> to <strong>' + fmt(p.cut_new) + '</strong>' + (p.stance === 'protect' ? ', and it has held.' : ', then put it back.')
           + ' Which do you mean? <a href="#" onclick="showView(\'picture\');return false">Answer it in your working picture</a>.';
    } else if (p.detail_kind === 'green') {
      body = 'You freed <strong>' + fmt(p.freed_monthly) + '/mo</strong> by clearing <strong>'
           + esc(p.subject) + '</strong> — worth <strong>' + mo(p.months)
           + '</strong> on your debt-free date.';
    } else {
      return '';
    }

    var accent = green ? 'var(--pine)' : 'var(--gold)';
    var tint = green ? 'var(--pine-bg)' : 'var(--gold-bg)';
    return '<div class="card mb-4" id="dashProactiveCard"'
      + ' style="border-left:3px solid ' + accent + ';background:' + tint + '">'
      + '<div style="display:flex;align-items:flex-start;gap:12px">'
      + '<div style="flex:1;font-size:12px;color:var(--slate);line-height:1.8">' + body + '</div>'
      + '<button onclick="GWTeaching.proactiveDismiss()" title="Dismiss"'
      + ' style="background:none;border:none;color:var(--slate-2);font-size:16px;'
      + 'line-height:1;cursor:pointer;padding:0 2px">×</button>'
      + '</div></div>';
  }

  function render() {
    var el = host();
    if (!el) return;
    // Asked once per load and the answer kept: the dashboard re-renders for all
    // sorts of reasons, and re-asking would return nothing the second time —
    // no longer novel, session budget spent — pulling the card out from under
    // whoever was reading it.
    if (asked) {
      el.innerHTML = prompt ? html(prompt) : '';
      return;
    }
    asked = true;
    API.get('/api/proactive/next').then(function (r) {
      prompt = r.prompt || null;
      // Silence is the right answer most weeks (A.3): an empty slot, not an
      // empty state explaining that there is nothing to say.
      el.innerHTML = prompt ? html(prompt) : '';
      if (prompt) {
        // The budget is spent when someone is shown something, not when the
        // server works out what it would say.
        API.post('/api/proactive/shown', {
          key: prompt.key, budget: prompt.budget, category: prompt.category || null
        }).catch(function () {});
      }
    }).catch(function () {});
  }

  // Item 39 (USAGE_SIGNALS.md, Rob 2026-10-09: U1-U4). A dismissal answers
  // that insight for 60 days, and the card says so (U1). From the second in a
  // category the card ASKS whether to stop bringing the category up (U2 (b));
  // a yes is the user's setting, listed in Settings with Undo. Nothing is
  // concluded from the clicks, and the pace is the dial's alone (U3).
  function dismissedHtml(r) {
    var days = (r && r.cooldown_days) || 60;
    var h = '<div style="font-size:12px;color:var(--slate)">Dismissed. Groundwork won\'t bring this up again for ' + days + ' days.</div>';
    if (r && r.ask_silence) {
      var c = esc(r.ask_silence);
      h += '<div style="font-size:12px;color:var(--ink);margin-top:8px">Stop bringing up ' + c + ' on its own? Insights about it stay on their pages.</div>'
        + '<div style="margin-top:6px"><button class="btn btn-secondary btn-sm" data-gw-silence="yes">Yes, stop</button> '
        + '<button class="btn btn-ghost btn-sm" data-gw-silence="no">No</button></div>';
    }
    return h;
  }

  function answerSilence(card, category, yes) {
    API.post('/api/proactive/silence', { category: category, silence: !!yes }).then(function () {
      card.innerHTML = '<div style="font-size:12px;color:var(--slate)">' + (yes
        ? 'Groundwork won\'t bring up ' + esc(category) + ' on its own. Undo it any time in Settings, under how often Groundwork speaks up.'
        : 'Noted - ' + esc(category) + ' can still come up.') + '</div>';
    }).catch(function () {});
  }

  function dismiss() {
    var card = document.getElementById('dashProactiveCard');
    if (!prompt) { if (card) card.remove(); return; }
    var dismissed = prompt;
    prompt = null;
    if (card) card.innerHTML = dismissedHtml({ cooldown_days: 60 });
    API.post('/api/proactive/dismiss', {
      key: dismissed.key, category: dismissed.category || null
    }).then(function (r) {
      r = (r && (r.data || r)) || {};
      if (!card) return;
      card.innerHTML = dismissedHtml(r);
      card.onclick = function (ev) {
        var b = ev.target.closest('[data-gw-silence]');
        if (b) answerSilence(card, r.ask_silence, b.dataset.gwSilence === 'yes');
      };
    }).catch(function () {});
  }

  // Item 39 U2 (b): Settings lists the categories the user said to stop bringing up, each with Undo - their
  // setting, nothing inferred. Under the dial (#proactiveSilenced); app.js knows nothing of it.
  function silencedHtml(cats) {
    if (!cats || !cats.length) return '';
    return '<div style="font-size:11px;color:var(--slate-2);margin-top:8px">You asked Groundwork not to bring these up on its own (they stay on their pages):</div>'
      + cats.map(function (c) {
          return '<div style="font-size:12px;color:var(--ink);margin-top:4px">' + esc(c)
            + ' <button class="btn btn-ghost btn-sm" data-gw-unsilence="' + esc(c) + '">Undo</button></div>';
        }).join('');
  }

  function renderSilenced() {
    var box = document.getElementById('proactiveSilenced');
    if (!box) return;
    API.get('/api/proactive/silenced').then(function (r) {
      r = (r && (r.data || r)) || {};
      box.innerHTML = silencedHtml(r.silenced || []);
      box.onclick = function (ev) {
        var b = ev.target.closest('[data-gw-unsilence]');
        if (!b) return;
        API.post('/api/proactive/unsilence', { category: b.dataset.gwUnsilence }).then(renderSilenced).catch(function () {});
      };
    }).catch(function () { box.innerHTML = ''; });
  }

  var originalRenderSettings = window.renderSettings;
  if (typeof originalRenderSettings === 'function') {
    window.renderSettings = function () {
      var out = originalRenderSettings.apply(this, arguments);
      try { renderSilenced(); } catch (e) { /* teaching never breaks the page under it */ }
      return out;
    };
  }

  // The wrap. app.js renders the dashboard and has no idea this happens after.
  var originalRenderDashboard = window.renderDashboard;
  window.renderDashboard = function () {
    var out = originalRenderDashboard.apply(this, arguments);
    try { render(); } catch (e) { /* teaching never breaks the page under it */ }
    return out;
  };

  GWTeaching.proactiveDismiss = dismiss;
  GWTeaching.register('proactive', { render: render, dismiss: dismiss, dismissedHtml: dismissedHtml,
                                     silencedHtml: silencedHtml });
})();
