/*
 * Text size, read aloud and voice commands (gw 2.0/PANEL_REVIEW.md, item 112 P6 and item 113; Rob 2026-10-24).
 *
 * Text size: one setting for the whole app (100, 115 or 130%), applied to the root font size - every size on every
 * page is a step of the type scale on :root, so they move together.
 *
 * Read aloud: off by default. The section under the pointer (or the one with focus) is read on Alt+R, or after a
 * short rest with "When I rest the pointer" chosen. What is read is Groundwork's own words: a figure's name and value,
 * a card's heading and its figures - never the AI's. After a section, "Would you like this explained further?"; yes
 * reads what each figure means (FIGS), or what the page works out (PAGE_EXPLAIN). Only voices on this computer are
 * used (localService); Esc stops.
 *
 * Voice commands: off by default. Push to talk (Alt+V or the mic button: hold, or tap to start and tap to stop). The
 * clip goes to this computer's own Groundwork server and nowhere else (core/voice.py); the browser's own recognition,
 * which can send audio away, is switched off here. What was heard is said before it is acted on, with Undo.
 */
(function () {
  'use strict';

  var SIZES = { '100': 1, '115': 1.15, '130': 1.3 };
  var RATES = { slower: 0.8, normal: 1, faster: 1.25 };
  var RATE_ORDER = ['slower', 'normal', 'faster'];
  var prefs = { text_size: '100', read_aloud: 'off', read_rate: 'normal', voice_commands: 'off' };
  var last = null;          // { words, section } - what was read last, for "repeat" and "explain further"
  var asking = null;        // the open "explained further?" question: { section }
  var hoverTimer = null, pointerAt = null, lastView = null, viewStack = [];

  function _el(id) { return document.getElementById(id); }

  // ── The browser's own speech recognition is never used: it can send audio to a company's servers ──────────────
  ['SpeechRecognition', 'webkitSpeechRecognition'].forEach(function (k) {
    try { Object.defineProperty(window, k, { value: undefined, writable: false, configurable: false }); }
    catch (e) { /* already fixed in place */ }
  });

  // ── Text size ────────────────────────────────────────────────────────────────────────────────────────────────
  function applySize(v) {
    var f = SIZES[v] || 1;
    document.documentElement.style.fontSize = f === 1 ? '' : (16 * f) + 'px';
    try { localStorage.setItem('gw_text_size', String(v)); } catch (e) { /* a convenience only */ }
  }
  try { var cached = localStorage.getItem('gw_text_size'); if (cached) applySize(cached); } catch (e) { /* none */ }

  async function _save(key, value) {
    prefs[key] = value;
    var body = {};
    body[key] = value;
    try { await API.patch('/api/settings', body); }
    catch (e) { showToast('Could not save that setting', esc(e.message || ''), 'error'); }
  }

  // ── Reading ──────────────────────────────────────────────────────────────────────────────────────────────────
  // A browser lists its voices a moment after the first ask, so they are asked for now, not on the first read
  if (window.speechSynthesis) { try { window.speechSynthesis.getVoices(); } catch (e) { /* none */ } }

  function _voice() {
    var vs = (window.speechSynthesis && window.speechSynthesis.getVoices()) || [];
    var local = vs.filter(function (v) { return v.localService; });
    return local.filter(function (v) { return /^en/i.test(v.lang); })[0] || local[0] || null;
  }

  function stop() {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    _closeQuestion();
  }

  function say(words, then) {
    if (!window.speechSynthesis || !words) return false;
    var v = _voice();
    if (!v) { showToast('There is no voice on this computer to read with', 'Read aloud uses only voices installed on this computer.', 'info'); return false; }
    window.speechSynthesis.cancel();
    var u = new window.SpeechSynthesisUtterance(words);
    u.voice = v;
    u.rate = RATES[prefs.read_rate] || 1;
    if (then) u.onend = then;
    window.speechSynthesis.speak(u);
    return true;
  }

  function _clean(t) { return String(t || '').replace(/\s+/g, ' ').trim(); }

  // The section a pointer or focus is in: a figure, else its card, else the page
  function sectionAt(node) {
    if (!node || !node.closest) return null;
    if (node.closest('#askPanel')) return null;            // the AI's words are not read
    return node.closest('[data-fig]') || node.closest('.card') || null;
  }

  function _figs(section) {
    var list = section.matches && section.matches('[data-fig]') ? [section] : Array.prototype.slice.call(section.querySelectorAll('[data-fig]'));
    return list.map(function (el) {
      var f = FIGS[el.dataset.fig];
      var value = _clean(el.innerText);
      if (!f || !el.offsetParent || !/\d/.test(value) || value.length > 60) return null;
      return { label: (el.dataset.figOf ? el.dataset.figOf + ', ' : '') + f.label, value: value, means: f.means };
    }).filter(Boolean).slice(0, 12);
  }

  function wordsFor(section) {
    var figs = _figs(section);
    var head = section.querySelector && section.querySelector('.card-label');
    var lead = head ? _clean(head.innerText) + '. ' : '';
    if (figs.length) return lead + figs.map(function (f) { return f.label + ': ' + f.value + '.'; }).join(' ');
    return _clean(section.innerText).slice(0, 600);
  }

  function readSection(section) {
    if (!section) { showToast('Point at a part of the page first', '', 'info'); return false; }
    var words = wordsFor(section);
    last = { words: words, section: section };
    return say(words, function () { _ask(section); });
  }

  function readPage() {
    var w = _explainWhere(), page = PAGE_EXPLAIN[w.name];
    var what = page ? [page.what, page.tabs && page.tabs[w.tab]].filter(Boolean).join(' ') : '';
    var figs = _explainFigures(w.view).map(function (f) { return (f.of ? f.of + ', ' : '') + f.label + ': ' + f.value + '.'; });
    var words = _clean(((VIEW_LABELS[w.name] || '') + (w.tabName ? ', ' + w.tabName : '') + '. ' + what + ' ' + figs.join(' ')));
    last = { words: words, section: null };
    return say(words);
  }

  function explainFurther(section) {
    section = section || (last && last.section);
    var figs = section ? _figs(section) : [];
    var words;
    if (figs.length) {
      words = figs.map(function (f) { return f.label + ' is ' + f.means + '.'; }).join(' ');
    } else {
      var w = _explainWhere(), page = PAGE_EXPLAIN[w.name];
      words = page ? [page.what, page.tabs && page.tabs[w.tab]].filter(Boolean).join(' ') : 'Groundwork has no more to say about this part yet.';
    }
    last = { words: words, section: section };
    return say(words);
  }

  // "Would you like this explained further?" - said, and shown with Yes and No for anyone not using their voice
  function _ask(section) {
    asking = { section: section };
    _closeQuestion(true);
    var box = document.createElement('div');
    box.id = 'gwReadAsk';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-label', 'Would you like this explained further?');
    box.style.cssText = 'position:fixed;right:1.25rem;bottom:5rem;z-index:9000;background:var(--paper);border:1px solid var(--steel);'
      + 'border-radius:10px;padding:.75rem 1rem;box-shadow:0 4px 16px rgba(0,0,0,.12);font-size:var(--fs-base);color:var(--ink)';
    box.innerHTML = '<div style="margin-bottom:.5rem">Would you like this explained further?</div>'
      + '<button class="btn btn-secondary btn-sm" data-gw-read="yes">Yes</button> '
      + '<button class="btn btn-ghost btn-sm" data-gw-read="no">No</button>';
    box.querySelector('[data-gw-read="yes"]').onclick = function () { answer(true); };
    box.querySelector('[data-gw-read="no"]').onclick = function () { answer(false); };
    document.body.appendChild(box);
    say('Would you like this explained further?');
  }

  function _closeQuestion(keep) {
    var b = _el('gwReadAsk');
    if (b) b.remove();
    if (!keep) asking = null;
  }

  function answer(yes) {
    if (!asking) return false;
    var section = asking.section;
    _closeQuestion();
    if (yes) explainFurther(section);
    return true;
  }

  function setRate(r) { if (RATES[r]) _save('read_rate', r); }

  // ── Keys and the pointer ─────────────────────────────────────────────────────────────────────────────────────
  document.addEventListener('mousemove', function (ev) {
    pointerAt = ev.target;
    if (prefs.read_aloud !== 'hover') return;
    clearTimeout(hoverTimer);
    var s = sectionAt(ev.target);
    if (!s || (last && last.section === s)) return;
    hoverTimer = setTimeout(function () { readSection(s); }, 700);
  });

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') { stop(); return; }
    if (ev.altKey && (ev.code === 'KeyR') && prefs.read_aloud !== 'off') {
      ev.preventDefault();
      readSection(sectionAt(document.activeElement !== document.body ? document.activeElement : pointerAt));
    }
    if (ev.altKey && ev.code === 'KeyV' && prefs.voice_commands === 'on' && !ev.repeat) { ev.preventDefault(); talkDown(); }
  });
  document.addEventListener('keyup', function (ev) {
    if (ev.code === 'KeyV' && rec) talkUp();
  });

  // Where "go back" goes: the page before this one (watched on the pages themselves, not every change on them)
  var goingBack = false;
  var views = new window.MutationObserver(function () {
    var v = document.querySelector('.view.active');
    var name = v ? v.id.replace(/^view-/, '') : null;
    if (!name || name === lastView) return;
    if (lastView && !goingBack) viewStack = viewStack.concat([lastView]).slice(-20);
    goingBack = false;
    lastView = name;
  });
  function _watchViews() {
    var v = document.querySelector('.view.active');
    lastView = v ? v.id.replace(/^view-/, '') : null;
    document.querySelectorAll('.view').forEach(function (el) { views.observe(el, { attributes: true, attributeFilter: ['class'] }); });
  }

  // ── Push to talk: a short clip, to this computer's server only ───────────────────────────────────────────────
  var rec = null;           // { ctx, stream, node, chunks, rate, downAt, held, timer }

  async function talkDown() {
    if (rec) { if (!rec.held) talkUp(); return; }    // tapped to start: a second tap stops
    var r = { chunks: [], downAt: Date.now(), held: true };
    rec = r;
    _micState('listening');
    try {
      r.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    } catch (e) {
      rec = null;
      _micState('idle');
      showToast('Groundwork could not use the microphone', esc(e.message || 'No microphone was found or allowed.'), 'error');
      return;
    }
    if (rec !== r) { r.stream.getTracks().forEach(function (t) { t.stop(); }); return; }
    r.ctx = new window.AudioContext();
    r.rate = r.ctx.sampleRate;
    var src = r.ctx.createMediaStreamSource(r.stream);
    r.node = r.ctx.createScriptProcessor(4096, 1, 1);
    r.node.onaudioprocess = function (e) { r.chunks.push(new window.Float32Array(e.inputBuffer.getChannelData(0))); };
    src.connect(r.node);
    r.node.connect(r.ctx.destination);
    r.timer = setTimeout(function () { if (rec === r) _finish(r); }, 14000);
  }

  function talkUp() {
    var r = rec;
    if (!r) return;
    if (r.held && Date.now() - r.downAt < 350) { r.held = false; return; }   // a tap: keep listening until the next
    _finish(r);
  }

  function _finish(r) {
    rec = null;
    clearTimeout(r.timer);
    try { r.node && r.node.disconnect(); } catch (e) { /* already */ }
    if (r.stream) r.stream.getTracks().forEach(function (t) { t.stop(); });
    if (r.ctx) r.ctx.close();
    if (!r.chunks.length) { _micState('idle'); return; }
    _micState('working');
    _send(wav(r.chunks, r.rate || 48000));
  }

  // 16 kHz mono 16-bit WAV, the form whisper.cpp reads
  function wav(chunks, rate) {
    var n = chunks.reduce(function (a, c) { return a + c.length; }, 0);
    var all = new window.Float32Array(n), o = 0;
    chunks.forEach(function (c) { all.set(c, o); o += c.length; });
    var step = rate / 16000, out = new window.Int16Array(Math.floor(n / step));
    for (var i = 0; i < out.length; i++) {
      var a = Math.floor(i * step), b = Math.min(n, Math.floor((i + 1) * step)), s = 0;
      for (var j = a; j < b; j++) s += all[j];
      var v = Math.max(-1, Math.min(1, s / Math.max(1, b - a)));
      out[i] = v < 0 ? v * 32768 : v * 32767;
    }
    var buf = new window.ArrayBuffer(44 + out.length * 2), d = new window.DataView(buf);
    var put = function (p, t) { for (var k = 0; k < t.length; k++) d.setUint8(p + k, t.charCodeAt(k)); };
    put(0, 'RIFF'); d.setUint32(4, 36 + out.length * 2, true); put(8, 'WAVE'); put(12, 'fmt ');
    d.setUint32(16, 16, true); d.setUint16(20, 1, true); d.setUint16(22, 1, true); d.setUint32(24, 16000, true);
    d.setUint32(28, 32000, true); d.setUint16(32, 2, true); d.setUint16(34, 16, true); put(36, 'data');
    d.setUint32(40, out.length * 2, true);
    for (var m = 0; m < out.length; m++) d.setInt16(44 + m * 2, out[m], true);
    return buf;
  }

  async function _send(buf) {
    try {
      var r = await _gwFetch('/api/voice/transcribe', { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: buf });
      var j = await r.json();
      if (!r.ok) throw new Error(j.error || 'The voice engine did not answer.');
      var text = ((j.data || j).text || '').trim();
      if (!text) showToast('Groundwork did not hear any words', 'Hold Alt+V (or the mic button) and speak, then let go.', 'info');
      else route(text);
    } catch (e) { showToast('Voice commands could not run', esc(e.message || ''), 'error'); }
    _micState('idle');
  }

  // ── What was said, to what it does. Every action is said first and can be undone ─────────────────────────────
  function _norm(t) { return String(t).toLowerCase().replace(/[^a-z0-9\u0027 ]+/g, ' ').replace(/\s+/g, ' ').trim(); }

  var COMMANDS = [
    { words: ['yes', 'yeah', 'yes please', 'sure'], said: 'Explaining further', run: function () { return answer(true) ? stop : false; } },
    { words: ['no', 'nope', 'no thanks', 'no thank you'], said: 'Not explaining further', run: function () { return answer(false) ? function () {} : false; } },
    { words: ['stop', 'quiet', 'be quiet', 'stop reading'], said: 'Stopped reading', run: function () { stop(); return function () { if (last) say(last.words); }; } },
    { words: ['repeat', 'say that again', 'again'], said: 'Reading it again', run: function () { return last && say(last.words) ? stop : false; } },
    { words: ['slower', 'slow down', 'read slower'], said: 'Reading slower', run: function () { return _step(-1); } },
    { words: ['faster', 'speed up', 'read faster'], said: 'Reading faster', run: function () { return _step(1); } },
    { words: ['read this', 'read that', 'read it'], said: 'Reading this part', run: function () { return readSection(sectionAt(pointerAt)) ? stop : false; } },
    { words: ['read the page', 'read page', 'read this page', 'read the whole page'], said: 'Reading the page', run: function () { return readPage() ? stop : false; } },
    { words: ['next', 'next one', 'next part'], said: 'Reading the next part', run: function () { return _next() ? stop : false; } },
    { words: ['go back', 'previous page', 'last page'], said: 'Going back', run: function () { return _back(); } },
    { words: ['explain further', 'explain more', 'explain that', 'explain this further'], said: 'Explaining further', run: function () { return explainFurther() ? stop : false; } },
  ];

  function _step(d) {
    var was = prefs.read_rate, i = RATE_ORDER.indexOf(was) + d;
    if (i < 0 || i >= RATE_ORDER.length) return false;
    setRate(RATE_ORDER[i]);
    if (last) say(last.words);
    return function () { setRate(was); };
  }

  function _next() {
    var all = Array.prototype.filter.call(document.querySelectorAll('.view.active .card'), function (c) { return c.offsetParent; });
    var at = last && last.section ? all.indexOf(last.section.closest('.card') || last.section) : -1;
    var n = all[at + 1];
    if (!n) return false;
    n.scrollIntoView({ block: 'center', behavior: 'smooth' });
    return readSection(n);
  }

  function _back() {
    var to = viewStack.pop(), from = lastView;
    if (!to) return false;
    goingBack = true;                      // the move back is not a new step to go back over
    showView(to);
    return function () { showView(from); };
  }

  function route(text) {
    var t = _norm(text);
    var cmd = COMMANDS.filter(function (c) { return c.words.indexOf(t) >= 0; })[0];
    var heard = 'Heard: “' + esc(text) + '”';
    if (cmd) {
      var undo = cmd.run();
      if (undo === false) { showToast(heard, 'There is nothing to do that with right now.', 'info'); return; }
      showToast(heard, esc(cmd.said), 'info', typeof undo === 'function' ? undo : null);
      return;
    }
    // Anything else is a question or an instruction, for the Ask bar to handle as if it were typed
    showToast(heard, 'Asking Groundwork', 'info', function () { var p = _el('askPanel'); if (p) p.remove(); });
    window.askGroundwork(text);   // a global of app.js's (s30's stripper can't see its definition past a regex there)
  }

  // ── The mic button, shown only with voice commands on ────────────────────────────────────────────────────────
  function _micButton() {
    var b = _el('gwMicBtn');
    if (prefs.voice_commands !== 'on') { if (b) b.remove(); return; }
    if (b) return;
    var right = document.querySelector('.topbar-right');
    if (!right) return;
    b = document.createElement('button');
    b.id = 'gwMicBtn';
    b.className = 'btn btn-sm btn-secondary';
    b.type = 'button';
    b.setAttribute('aria-label', 'Voice command: hold to talk, or tap to start and tap to stop (Alt+V)');
    b.title = 'Hold to talk, or tap to start and tap to stop (Alt+V). What you say is recognised on this computer.';
    b.textContent = '🎙 Talk';
    b.addEventListener('pointerdown', function (e) { e.preventDefault(); talkDown(); });
    b.addEventListener('pointerup', function () { talkUp(); });
    right.insertBefore(b, _el('gwAskBox') || null);
  }

  function _micState(s) {
    var b = _el('gwMicBtn');
    if (!b) return;
    b.textContent = s === 'listening' ? '● Listening…' : s === 'working' ? 'Hearing…' : '🎙 Talk';
    b.style.color = s === 'listening' ? 'var(--ember-text)' : '';
    b.setAttribute('aria-pressed', s === 'listening' ? 'true' : 'false');
  }

  // ── The Settings card ────────────────────────────────────────────────────────────────────────────────────────
  function _radios(name, current, options) {
    return options.map(function (o) {
      return '<label style="display:inline-flex;align-items:center;gap:6px;margin:0 14px 6px 0;cursor:pointer;font-size:var(--fs-base);text-transform:none;letter-spacing:normal;font-weight:400;color:var(--ink)">'
        + '<input type="radio" style="width:auto;margin:0" name="' + name + '" value="' + o[0] + '"' + (String(current) === o[0] ? ' checked' : '') + '> ' + o[1] + '</label>';
    }).join('');
  }

  async function _card() {
    var panel = _el('settingsPanel-general');
    if (!panel) return;
    var card = _el('gwAccessCard');
    if (!card) {
      card = document.createElement('div');
      card.id = 'gwAccessCard';
      card.className = 'card mb-4';
      panel.insertBefore(card, panel.firstChild);
    }
    var vs = null;
    try { vs = await API.get('/api/voice'); } catch (e) { vs = { available: false, reason: 'The voice engine could not be checked.' }; }
    var small = 'font-size:var(--fs-xs);color:var(--slate-2);margin:2px 0 10px';
    card.innerHTML = '<div class="card-label">Reading and voice</div>'
      + '<div class="field mb-4"><label>Text size</label><div>' + _radios('gwTextSize', prefs.text_size, [['100', 'Standard'], ['115', 'Larger'], ['130', 'Largest']]) + '</div>'
      + '<div style="' + small + '">Every page, at once.</div></div>'
      + '<div class="field mb-4"><label>Read aloud</label><div>' + _radios('gwReadAloud', prefs.read_aloud, [['off', 'Off'], ['key', 'When I press Alt+R'], ['hover', 'When I rest the pointer on something']]) + '</div>'
      + '<div>' + _radios('gwReadRate', prefs.read_rate, [['slower', 'Slower'], ['normal', 'Normal'], ['faster', 'Faster']]) + '</div>'
      + '<div style="' + small + '">Reads the part of the page you point at, in Groundwork\'s own words, then asks if you\'d like it explained further. '
      + 'Esc stops. Only voices installed on this computer are used.</div></div>'
      + '<div class="field"><label>Voice commands</label><div>' + _radios('gwVoice', prefs.voice_commands, [['off', 'Off'], ['on', 'On (push to talk)']]) + '</div>'
      + '<div style="' + small + '">Hold Alt+V or the Talk button and speak - "read this", "read the page", "explain further", "repeat", '
      + '"slower", "faster", "next", "go back", "stop", "yes", "no", or a question. What you say is recognised by Groundwork on this '
      + 'computer and is never sent anywhere or kept. Groundwork says what it heard first, with Undo.'
      + (vs && !vs.available ? '<br><span style="color:var(--ember-text)">Not available in this copy: ' + esc(vs.reason || '') + '</span>' : '')
      + '</div></div>';
    card.querySelectorAll('input[name="gwTextSize"]').forEach(function (i) {
      i.addEventListener('change', function () { applySize(i.value); _save('text_size', i.value); });
    });
    card.querySelectorAll('input[name="gwReadAloud"]').forEach(function (i) {
      i.addEventListener('change', function () { _save('read_aloud', i.value); if (i.value === 'off') stop(); });
    });
    card.querySelectorAll('input[name="gwReadRate"]').forEach(function (i) {
      i.addEventListener('change', function () { _save('read_rate', i.value); });
    });
    card.querySelectorAll('input[name="gwVoice"]').forEach(function (i) {
      i.addEventListener('change', async function () { await _save('voice_commands', i.value); _micButton(); });
    });
  }

  async function load() {
    try {
      var s = (await API.get('/api/settings')) || {};
      Object.keys(prefs).forEach(function (k) { if (s[k] != null && s[k] !== '') prefs[k] = String(s[k]); });
    } catch (e) { /* defaults: everything off, standard size */ }
    applySize(prefs.text_size);
    if (lastView === null) _watchViews();
    _micButton();
    _card();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();

  GWTeaching.register('access', { load: load, route: route, wav: wav, readSection: readSection, answer: answer, stop: stop, prefs: prefs });
})();
