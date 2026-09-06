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

  function dismiss() {
    var card = document.getElementById('dashProactiveCard');
    if (card) card.remove();
    if (!prompt) return;
    // A dismissal is the user telling us something, and A.4 says we listen:
    // sixty days of quiet on this one, twice in a category drops the category
    // to passive for good.
    API.post('/api/proactive/dismiss', {
      key: prompt.key, category: prompt.category || null
    }).catch(function () {});
    prompt = null;
  }

  // The wrap. app.js renders the dashboard and has no idea this happens after.
  var originalRenderDashboard = window.renderDashboard;
  window.renderDashboard = function () {
    var out = originalRenderDashboard.apply(this, arguments);
    try { render(); } catch (e) { /* teaching never breaks the page under it */ }
    return out;
  };

  GWTeaching.proactiveDismiss = dismiss;
  GWTeaching.register('proactive', { render: render, dismiss: dismiss });
})();
