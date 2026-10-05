/*
 * The working picture - the Willingness Layer's home (blueprint Appendix F.3;
 * gw 2.0/WILLINGNESS_LAYER.md, ruled 2026-09-27).
 *
 * Teaching layer: absent from an LTS bundle by path. The view, its nav entry
 * and the Settings pointer are all created from here, so neither index.html nor
 * app.js knows this page exists.
 *
 * What it is: the assistant's record of its own conclusions about how the user
 * handles money, each with the receipts it rests on, and what the user has said
 * back. It is the assistant's home before the assistant has a voice - the
 * conversation pane is deliberately not part of this build (ruling 3).
 *
 * Three rules shape every line of it:
 *   - The empty state is the design centre (F.3). With no conclusions it says
 *     so and offers NO controls - there is nothing yet to dispute.
 *   - Nothing is editable that is not first a claim with a receipt. Each
 *     control sits beside something Groundwork concluded or something the user
 *     said; editing is disputing, never configuring.
 *   - Willingness is never a stick (F.4). A statement is shown as the user's
 *     word and never set against their behaviour as a failing.
 */
(function () {
  'use strict';

  var VIEW = 'picture';

  function _date(iso) {
    if (!iso) return '';
    var p = String(iso).slice(0, 10).split('-').map(Number);
    return new Date(p[0], p[1] - 1, p[2]).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function _month(m) {
    var p = String(m).split('-').map(Number);
    return new Date(p[0], p[1] - 1, 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  }

  // One control: a statement answering a claim or a proposal. Data attributes
  // rather than inline handlers, so a category name never has to survive being
  // quoted into JavaScript.
  function _control(category, stance, kind, answerText, label) {
    return '<button class="btn btn-sm btn-secondary" style="margin:4px 6px 0 0" data-gw-declare="' + esc(stance) + '"'
      + ' data-gw-category="' + esc(category) + '" data-gw-kind="' + esc(kind) + '"'
      + ' data-gw-answer="' + esc(answerText) + '">' + esc(label) + '</button>';
  }

  // The in-context channel (F.3): a decision screen offers a path that names a
  // category, and the user can answer it where they stand. Shared with paths.js
  // - the one direction the seam allows.
  function _declareInline(category, proposalText) {
    return ' <a href="#" style="font-size:11px;color:var(--slate-2);white-space:nowrap"'
      + ' data-gw-declare="protect" data-gw-category="' + esc(category) + '" data-gw-kind="proposal"'
      + ' data-gw-answer="' + esc(proposalText) + '">never ' + esc(category) + '</a>';
  }

  // A reading standing on the months since a break counts only those (F.8).
  function _sinceNote(r) {
    return r.boundary ? ' Only the months from ' + _month(r.boundary.month) + ' on are counted: the record changed level then.' : '';
  }

  // What each reading claims, said as a fact about the record - never as what
  // the user ought to do.
  function _claimText(r) {
    var c = '<strong>' + esc(r.category) + '</strong>';
    var x = r.receipt || {};
    if (r.reason === 'cut_held') {
      return c + ': you lowered its budget from ' + fmt(x.cut.old) + ' to ' + fmt(x.cut.new) + ' on '
        + _date(x.cut.date) + ', and it stayed within ' + fmt(x.cut.new) + ' in each of the ' + x.months.length
        + ' months since (the highest was ' + fmt(x.worst) + ').' + _sinceNote(r)
        + ' Groundwork reads it as flexible for you.';
    }
    if (r.reason === 'restored') {
      return c + ': you lowered its budget from ' + fmt(x.cut.old) + ' to ' + fmt(x.cut.new) + ' on '
        + _date(x.cut.date) + ', then set it back to ' + fmt(x.restore.new) + ' on ' + _date(x.restore.date)
        + '. Groundwork reads it as something you keep.';
    }
    if (r.reason === 'break') return _breakText(r);
    if (r.reason === 'probation') {
      return c + ': you lowered its budget from ' + fmt(x.cut.old) + ' to ' + fmt(x.cut.new) + ' on '
        + _date(x.cut.date) + '. In the same window your recorded income moved from ' + fmt(x.income.from)
        + ' (' + _month(x.income.from_month) + ') to ' + fmt(x.income.to) + ' (' + _month(x.income.month) + ').'
        + ' Groundwork does not classify a change that moved beside your income - whether this is something'
        + ' to protect is yours to say.';
    }
    return '';
  }

  // F.8: the shift, not the story (BREAK_DETECTOR.md ruling 7). What moved,
  // from what to what, and from which month - never why, never for how long,
  // never what to do about it. The reading it set aside stays visible under it:
  // a break changes what is admissible now, it erases nothing.
  function _breakText(r) {
    var b = r.receipt.break;
    var from = _month(b.month);
    var fact;
    if (b.scope === 'income') {
      fact = 'Your recorded income moved from about ' + fmt(b.before) + ' a month to about ' + fmt(b.after)
        + ', from ' + from + ' on.';
    } else if (b.scope === 'together') {
      fact = 'Spending in ' + esc(_joinNames(b.categories.map(function (n) { return { name: n }; })))
        + ' changed level together, from ' + from + ' on.';
    } else {
      fact = '<strong>' + esc(r.category) + '</strong> spending moved from about ' + fmt(b.before)
        + ' a month to about ' + fmt(b.after) + ', from ' + from + ' on.';
    }
    var aside = r.receipt.set_aside ? _claimText(r.receipt.set_aside) : '';
    return fact + ' What Groundwork read about <strong>' + esc(r.category) + '</strong> from before then is set'
      + ' aside until the months since show where it stands.'
      + (aside ? '<div style="font-size:11px;color:var(--slate-2);margin-top:3px">Set aside: ' + aside + '</div>' : '');
  }

  function _claimControls(r) {
    var plain = _plain(_claimText(r));
    if (r.stance === 'flexible') return _control(r.category, 'protect', 'claim', plain, 'Protect it');
    if (r.stance === 'sacred') return _control(r.category, 'flexible', 'claim', plain, 'It is flexible');
    return _control(r.category, 'protect', 'claim', plain, 'Protect it')
      + _control(r.category, 'flexible', 'claim', plain, 'It is flexible');
  }

  function _plain(html) {
    var d = document.createElement('div');
    d.innerHTML = html;
    return d.textContent || '';
  }

  function _statementText(d) {
    var what = d.stance === 'protect' ? 'protected' : 'flexible';
    var line = 'You marked <strong>' + esc(d.category) + '</strong> ' + what + ' on ' + _date(d.said_at) + '.';
    if (d.on_floor && d.stance === 'flexible') {
      line += ' It is on the necessity floor - housing, food, insurance and the like are never proposed as a'
        + ' cut, because cutting them breaks stability - so Groundwork still will not offer it.';
    }
    if (d.answer_text) {
      line += '<div style="font-size:11px;color:var(--slate-2);margin-top:3px">Answering: '
        + esc(d.answer_text) + '</div>';
    }
    return line;
  }

  function _statementControls(d) {
    var plain = _plain(_statementText(d));
    return (d.stance === 'protect'
      ? _control(d.category, 'flexible', 'claim', plain, 'Mark it flexible')
      : _control(d.category, 'protect', 'claim', plain, 'Protect it'))
      + _control(d.category, 'release', 'claim', plain, 'Release');
  }

  function _historyRow(d) {
    var what = d.stance === 'release' ? 'released what you had said about'
      : d.stance === 'protect' ? 'marked protected' : 'marked flexible';
    return '<div style="font-size:11px;color:var(--slate);padding:3px 0">' + _date(d.said_at) + ' - '
      + (d.stance === 'release' ? what + ' <strong>' + esc(d.category) + '</strong>'
        : '<strong>' + esc(d.category) + '</strong> ' + what) + '</div>';
  }

  function _pictureHTML(s) {
    var readings = (s.readings || []).filter(function (r) {
      return r.stance === 'flexible' || r.stance === 'sacred' || r.reason === 'probation' || r.reason === 'break';
    });
    var said = {};
    (s.current || []).forEach(function (d) { said[d.category.trim().toLowerCase()] = true; });
    // A category the user has spoken about shows their word; the reading it
    // answered stays visible under it, because the receipt did not stop being
    // true when they disagreed with the conclusion.
    var claims = readings.filter(function (r) { return !said[r.category.trim().toLowerCase()]; });
    var answered = readings.filter(function (r) { return said[r.category.trim().toLowerCase()]; });
    var history = s.declarations || [];

    var head = '<div class="section-header"><div class="section-title">Working picture</div>'
      + '<div class="section-sub">What Groundwork has concluded about how you handle money, and what you have told it.</div></div>';

    var how = '<div style="font-size:12px;color:var(--slate);line-height:1.7">'
      + 'Groundwork concludes only from your own record: a budget cut that holds for three months, a cut you'
      + ' later undo, an envelope kept through months when spending passed income. Each conclusion appears here'
      + ' with the edits and months behind it, and you can dispute any of them. It never learns from which'
      + ' pages you open or which suggestions you dismiss.</div>';

    if (!claims.length && !answered.length && !history.length) {
      return head + '<div class="card"><div class="card-label">Nothing concluded yet</div>'
        + '<div style="font-size:14px;color:var(--ink);margin:4px 0 10px">Groundwork has not drawn any conclusions about you yet.</div>'
        + how
        + '<div style="font-size:12px;color:var(--slate);line-height:1.7;margin-top:8px">Until it has, there is'
        + ' nothing here to set - on purpose. When a decision screen offers a path that names one of your'
        + ' categories, you can answer it there, and what you say will appear here.</div></div>';
    }

    var out = head;
    if (claims.length) {
      out += '<div class="card"><div class="card-label">What your record shows</div>'
        + claims.map(function (r) {
          return '<div style="padding:10px 0;border-bottom:1px solid var(--steel);font-size:12px;color:var(--slate);line-height:1.8">'
            + _claimText(r) + '<div>' + _claimControls(r) + '</div></div>';
        }).join('') + '</div>';
    }
    if ((s.current || []).length) {
      out += '<div class="card mt-5"><div class="card-label">What you have told Groundwork</div>'
        + '<div style="font-size:12px;color:var(--slate);margin-bottom:4px">Your word stands over anything'
        + ' Groundwork reads from your record, and it stays until you change it.</div>'
        + s.current.map(function (d) {
          var r = answered.filter(function (a) { return a.category.trim().toLowerCase() === d.category.trim().toLowerCase(); })[0];
          // The reading under the statement, unless the statement already
          // quotes it word for word (it answered this very claim, unchanged).
          var rec = r && _plain(_claimText(r)) !== d.answer_text ? _claimText(r) : '';
          return '<div style="padding:10px 0;border-bottom:1px solid var(--steel);font-size:12px;color:var(--slate);line-height:1.8">'
            + _statementText(d)
            + (rec ? '<div style="font-size:11px;color:var(--slate-2);margin-top:3px">Your record now: ' + rec + '</div>' : '')
            + '<div>' + _statementControls(d) + '</div></div>';
        }).join('') + '</div>';
    }
    if (history.length) {
      out += '<details class="card mt-5"><summary class="card-label" style="cursor:pointer">Everything you have said, in order</summary>'
        + history.slice().reverse().map(_historyRow).join('') + '</details>';
    }
    return out + '<div class="card mt-5">' + how + '</div>';
  }

  async function render() {
    var view = g('view-' + VIEW);
    if (!view) return;
    try {
      var s = await API.get('/api/willingness');
      view.innerHTML = _pictureHTML(s || {});
    } catch (e) {
      _gwErr('willingness render')(e);
      view.innerHTML = '<div class="section-header"><div class="section-title">Working picture</div></div>'
        + '<div class="card" style="font-size:12px;color:var(--slate)">The working picture could not be loaded.</div>';
    }
  }

  async function _declare(el) {
    var body = {
      category: el.getAttribute('data-gw-category'),
      stance: el.getAttribute('data-gw-declare'),
      answer: { kind: el.getAttribute('data-gw-kind'), text: el.getAttribute('data-gw-answer') }
    };
    try {
      await API.post('/api/willingness/declarations', body);
      var verb = body.stance === 'release' ? 'Released' : body.stance === 'protect' ? 'Protected' : 'Marked flexible';
      showToast(verb + ': ' + body.category, 'It shows in your working picture.');
    } catch (e) {
      _gwErr('willingness declare')(e);
      return;
    }
    var active = document.querySelector('.nav-item.active');
    var name = active && active.getAttribute('data-view');
    if (name) showView(name);
  }

  document.addEventListener('click', function (ev) {
    var el = ev.target && ev.target.closest && ev.target.closest('[data-gw-declare]');
    if (!el) return;
    ev.preventDefault();
    _declare(el);
  });

  // The home: a view of its own, a nav entry, and one line in Settings (F.3 -
  // "Settings gets a pointer, never the thing").
  function _mount() {
    var content = document.querySelector('.content');
    if (content && !g('view-' + VIEW)) {
      var v = document.createElement('div');
      v.id = 'view-' + VIEW;
      v.className = 'view';
      content.appendChild(v);
    }
    var overview = document.querySelector('.nav-item[data-view="dashboard"]');
    var section = overview && overview.closest('.nav-section');
    if (section && !document.querySelector('.nav-item[data-view="' + VIEW + '"]')) {
      var s = document.createElement('div');
      s.className = 'nav-section';
      s.innerHTML = '<div class="nav-section-label">Assistant</div>'
        + '<div class="nav-item" data-view="' + VIEW + '" onclick="showView(\'' + VIEW + '\')">'
        + '<span class="nav-item-icon">◇</span>Working picture</div>';
      section.parentNode.insertBefore(s, section.nextSibling);
    }
    var settingsHead = document.querySelector('#view-settings .section-header');
    if (settingsHead && !g('gwPicturePointer')) {
      var p = document.createElement('div');
      p.id = 'gwPicturePointer';
      p.style.cssText = 'font-size:12px;margin:-6px 0 14px';
      p.innerHTML = '<a href="#" onclick="showView(\'' + VIEW + '\');return false" style="color:var(--pine)">'
        + 'What Groundwork has concluded about how you handle money →</a>';
      settingsHead.parentNode.insertBefore(p, settingsHead.nextSibling);
    }
    if (typeof VIEW_LABELS === 'object') VIEW_LABELS[VIEW] = 'Working picture';
  }

  var original = window.showView;
  window.showView = function (name) {
    var out = original.apply(this, arguments);
    if (name === VIEW) { try { render(); } catch (e) { /* never break navigation */ } }
    return out;
  };

  _mount();
  window._gwDeclareInline = _declareInline;
  GWTeaching.register('willingness', { render: render, mount: _mount });
})();
