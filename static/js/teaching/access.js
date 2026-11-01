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
 * Voice commands: off by default. Conversation mode (item 114 H14): one tap on the microphone in the Ask box (H15) or
 * Alt+V, and it stays on until a tap, "stop", a minute of quiet or leaving the window. Each thing said goes to this
 * computer's own Groundwork server and nowhere else (core/voice.py); the browser's own recognition, which can send
 * audio away, is switched off here. What was heard is said before it is acted on, with Undo.
 */
(function () {
  'use strict';

  var SIZES = { '100': 1, '115': 1.15, '130': 1.3 };
  var RATES = { slower: 0.8, normal: 1, faster: 1.25 };
  var RATE_ORDER = ['slower', 'normal', 'faster'];
  var prefs = { text_size: '100', read_aloud: 'off', read_rate: 'normal', voice_commands: 'off', voice_tour: '' };
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
    catch (e) { showToast('Could not save that setting', e.message || '', 'error'); }
  }

  // ── Reading ──────────────────────────────────────────────────────────────────────────────────────────────────
  // A browser lists its voices a moment after the first ask, so they are asked for now, not on the first read
  if (window.speechSynthesis) { try { window.speechSynthesis.getVoices(); } catch (e) { /* none */ } }

  function _voice() {
    var vs = (window.speechSynthesis && window.speechSynthesis.getVoices()) || [];
    var local = vs.filter(function (v) { return v.localService; });
    return local.filter(function (v) { return /^en/i.test(v.lang); })[0] || local[0] || null;
  }

  // Groundwork's own voice (core/speak.py; Rob 2026-10-31: "lets add a human sounding voice"): made by this computer's
  // Groundwork server and played here, a sentence or two at a time so the first is heard while the next is made. The
  // computer's own voices are the fallback - the server can't speak, or the window won't play sound yet.
  var own = { available: null, audio: null, gen: 0, playing: false };

  function _chunks(words) {
    var out = [], cur = '';
    // only a full stop, ! or ? followed by a space ends a sentence - "$1,199.00" and "24.99%" stay whole. The first
    // sentence goes alone, so the voice starts soon; each later piece is at most twice the one before (and 400 at
    // most), so it is made while the one before is still being said - no gap (measured 2026-10-31: 1.2 s without)
    String(words).split(/(?<=[.!?])\s+/).forEach(function (s) {
      while (s.length > 500) { var at = s.lastIndexOf(' ', 500); at = at > 0 ? at : 500; out.push(s.slice(0, at)); s = s.slice(at).trim(); }
      var room = out.length ? Math.min(400, Math.max(120, 2 * out[out.length - 1].length)) : 0;
      if (cur && (cur + ' ' + s).length > room) { out.push(cur); cur = s; } else cur = cur ? cur + ' ' + s : s;
    });
    if (cur) out.push(cur);
    return out;
  }

  async function _made(text) {
    var r = await _gwFetch('/api/voice/speak', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, speed: prefs.read_rate }) });
    if (!r.ok) throw new Error('voice ' + r.status);
    return URL.createObjectURL(await r.blob());
  }

  function _sayOwn(words, then) {
    var gen = ++own.gen, parts = _chunks(words), next = _made(parts[0]);
    own.playing = true;
    (async function () {
      for (var i = 0; i < parts.length; i++) {
        var url = null, played = true;
        try { url = await next; } catch (e) { played = false; }
        if (gen !== own.gen) { if (url) URL.revokeObjectURL(url); return; }
        if (played && i + 1 < parts.length) next = _made(parts[i + 1]);
        if (played) played = await new Promise(function (done) {
          var a = new window.Audio(url);
          own.audio = a;
          a.onended = function () { done(true); };
          a.onerror = function () { done(false); };
          a.play().catch(function () { done(false); });
        });
        if (url) URL.revokeObjectURL(url);
        if (gen !== own.gen) return;
        if (!played) {                    // the rest in the computer's own voice, and the next reading straight there
          own.playing = false; own.audio = null;
          if (i === 0) own.available = false;
          _saySystem(parts.slice(i).join(' '), then);
          return;
        }
      }
      own.playing = false; own.audio = null;
      if (then) then();
    })();
    return true;
  }

  function _saySystem(words, then) {
    if (!window.speechSynthesis) return false;
    var v = _voice();
    if (!v) { showToast('There is no voice on this computer to read with', "Groundwork's own voice isn't in this copy, and the computer has none installed.", 'info'); return false; }
    window.speechSynthesis.cancel();
    var u = new window.SpeechSynthesisUtterance(words);
    u.voice = v;
    u.rate = RATES[prefs.read_rate] || 1;
    if (then) u.onend = then;
    window.speechSynthesis.speak(u);
    return true;
  }

  function _hush() {
    own.gen++;
    if (own.audio) { try { own.audio.pause(); } catch (e) { /* gone */ } }
    own.audio = null; own.playing = false;
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }

  function stop() {
    _hush();
    _closeQuestion();
  }

  function say(words, then) {
    if (!words) return false;
    _hush();
    return own.available !== false ? _sayOwn(words, then) : _saySystem(words, then);
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
    if (ev.altKey && ev.code === 'KeyV' && prefs.voice_commands === 'on' && !ev.repeat) { ev.preventDefault(); talkToggle(); }
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

  // ── Conversation mode (item 114 H14, Rob 2026-10-30: "it should stay on so the user can talk with the software") ──
  // One tap turns the microphone on and it stays on. Groundwork finds where each thing said ends (a pause), and sends
  // that clip - to this computer's own server, nowhere else. It turns off on a tap, on "stop", after a minute with
  // nothing said, or when Groundwork's window is left. While Groundwork reads aloud it listens only for a few short
  // words (V2 below), so it never takes its own voice for the person's. Nothing is kept: each clip lives for its one
  // request.
  var SPEECH_RMS = 0.012;       // louder than this is someone talking
  var END_PAUSE_MS = 900;       // a pause this long ends what was said
  var MAX_SAID_MS = 14000;      // the server takes at most 15 seconds a clip
  var MIN_SAID_MS = 250;        // shorter is a cough or a click
  var QUIET_OFF_MS = 60000;     // a minute with nothing said turns it off
  var conv = null;              // { ctx, stream, node, rate, speech, chunks, pre, start, lastVoice, lastActivity, busy }
  var micKept = false;          // this page has recorded the microphone's yes

  function _speaking() { return own.playing || !!(window.speechSynthesis && (window.speechSynthesis.speaking || window.speechSynthesis.pending)); }

  async function micOn() {
    if (conv) return;
    var c = { chunks: [], pre: [], speech: false, busy: 0, lastActivity: Date.now() };
    conv = c;
    _micState('listening');
    try {
      c.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    } catch (e) {
      conv = null;
      _micState('idle');
      showToast('Groundwork could not use the microphone', e.message || 'No microphone was found or allowed.', 'error');
      return;
    }
    // The microphone opened, so the person said yes to it: kept, and the window answers it from now on (Rob 2026-10-31)
    if (!micKept) { micKept = true; API.post('/api/voice/microphone', {}).catch(function () { micKept = false; }); }
    if (conv !== c) { c.stream.getTracks().forEach(function (tr) { tr.stop(); }); return; }
    c.ctx = new window.AudioContext();
    c.rate = c.ctx.sampleRate;
    var src = c.ctx.createMediaStreamSource(c.stream);
    c.node = c.ctx.createScriptProcessor(4096, 1, 1);
    c.node.onaudioprocess = function (e) { _hear(c, e.inputBuffer.getChannelData(0)); };
    src.connect(c.node);
    c.node.connect(c.ctx.destination);
    _chime(true);
    _tourOnce();
  }

  function micOff(why) {
    var c = conv;
    if (!c) return;
    conv = null;
    try { c.node && c.node.disconnect(); } catch (e) { /* already */ }
    if (c.stream) c.stream.getTracks().forEach(function (tr) { tr.stop(); });
    if (c.ctx) c.ctx.close();
    _chime(false);
    _micState('idle');
    if (why) showToast('The microphone is off', why, 'info');
  }

  // V2 (item 116): while Groundwork speaks it still listens, for a few short words only - "stop", "next", "repeat",
  // "slower" - so the person can cut in. Its own voice is not taken for theirs: the browser cancels the echo, a clip
  // over speech must be louder and short, and anything but those words is let go unread.
  var BARGE_RMS = SPEECH_RMS * 2.5;
  var BARGE_MAX_MS = 2500;
  var BARGE = { 'stop': 'stop', 'stop it': 'stop', 'stop in': 'stop', 'quiet': 'stop', 'be quiet': 'stop', 'stop reading': 'stop', 'stop talking': 'stop',
                'that s enough': 'stop', "that's enough": 'stop', 'enough': 'stop', 'pause': 'stop', 'no': 'stop',
                'nope': 'stop', 'next': 'next', 'next one': 'next', 'next part': 'next', 'skip': 'next',
                'repeat': 'repeat', 'again': 'repeat', 'say that again': 'repeat', 'slower': 'slower',
                'slow down': 'slower', 'faster': 'faster', 'speed up': 'faster' };

  function _hear(c, data) {
    if (conv !== c) return;
    var now = Date.now();
    var over = _speaking();
    if (over) c.lastActivity = now;                 // a long reading is not a quiet minute
    var sum = 0;
    for (var i = 0; i < data.length; i++) sum += data[i] * data[i];
    var loud = Math.sqrt(sum / data.length) > (over ? BARGE_RMS : SPEECH_RMS);
    var copy = new window.Float32Array(data);
    if (loud) {
      if (!c.speech) { c.speech = true; c.over = over; c.start = now; c.chunks = c.pre.slice(); }
      c.lastVoice = now;
      c.lastActivity = now;
    }
    if (c.speech) {
      c.chunks.push(copy);
      if (now - c.lastVoice > END_PAUSE_MS || now - c.start > (c.over ? BARGE_MAX_MS : MAX_SAID_MS)) {
        var said = c.chunks;
        var long = c.lastVoice - c.start;
        c.speech = false;
        c.chunks = [];
        c.pre = [];
        if (long >= MIN_SAID_MS) _said(c, said, c.over);
      }
    } else {
      c.pre.push(copy);
      if (c.pre.length > 2) c.pre.shift();       // a moment before the first sound, so its start is not cut
      if (now - c.lastActivity > QUIET_OFF_MS) micOff('Nothing was said for a minute.');
    }
  }

  async function _said(c, chunks, over) {
    c.busy++;
    _micState('working');
    await _send(wav(chunks, c.rate || 48000), over);
    c.busy--;
    _micState(conv ? (conv.busy ? 'working' : 'listening') : 'idle');
  }

  function talkToggle() { if (conv) micOff(); else micOn(); }

  // Leaving Groundwork's window turns the microphone off
  if (window.addEventListener) window.addEventListener('blur', function () { if (conv) micOff('Groundwork’s window was left.'); });
  document.addEventListener('visibilitychange', function () { if (document.hidden && conv) micOff('Groundwork’s window was left.'); });

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

  async function _send(buf, over) {
    try {
      var r = await _gwFetch('/api/voice/transcribe' + (over ? '?short=1' : ''), { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: buf });
      var j = await r.json();
      if (!r.ok) throw new Error(j.error || 'The voice engine did not answer.');
      var text = ((j.data || j).text || '').trim();
      if (over) {                                   // heard while Groundwork spoke: one of the short words, or nothing
        var cut = BARGE[_norm(text).replace(/^(?:groundwork|ok|okay|hey|please)\s+/, '').replace(/\s+please$/, '')];
        var cmd = cut && COMMANDS.filter(function (x) { return x.words.indexOf(cut) >= 0; })[0];
        if (cmd) {                                  // the reading's own command - "stop" stops the reading, not the mic
          _hush();
          var undo = cmd.run();
          showToast('Heard: “' + text + '”', cmd.said, 'info', typeof undo === 'function' ? undo : null);
        }
        return;
      }
      if (text) route(text);                        // in a conversation, a cough is not worth a message
    } catch (e) { showToast('Voice commands could not run', e.message || '', 'error'); }
  }

  // V7 (item 116): the first time the microphone is turned on, a short spoken tour - once; Settings records that it was
  // given, nothing else
  var TOUR = "Hi, this is Groundwork. You can talk to me. Try open my budget, show me my Kroger transactions, or what's "
    + "coming up this week. While I'm talking, say stop to cut me off, or next, or repeat. Say what can I say to hear more. "
    + "Everything you say stays on this computer.";
  function _tourOnce() {
    if (prefs.voice_tour === 'done') return;
    prefs.voice_tour = 'done';
    _save('voice_tour', 'done');
    setTimeout(function () { say(TOUR); }, 300);
  }

  // V7 (item 116): a soft sound when listening starts and when it stops - two short tones, made here, nothing played
  // from anywhere else
  var tones = null;
  function _chime(up) {
    try {
      tones = tones || new window.AudioContext();
      var t = tones.currentTime;
      (up ? [523.25, 783.99] : [783.99, 523.25]).forEach(function (f, i) {
        var o = tones.createOscillator(), gn = tones.createGain();
        o.type = 'sine'; o.frequency.value = f;
        gn.gain.setValueAtTime(0.0001, t + i * 0.09);
        gn.gain.exponentialRampToValueAtTime(0.05, t + i * 0.09 + 0.02);
        gn.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.09 + 0.12);
        o.connect(gn); gn.connect(tones.destination);
        o.start(t + i * 0.09); o.stop(t + i * 0.09 + 0.13);
      });
    } catch (e) { /* no sound is no harm */ }
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

  var MIC_OFF = ['stop', 'stop listening', 'that s all', "that's all", 'mic off', 'microphone off', 'turn off the microphone', 'goodbye', 'thank you that s all'];
  var YES_NO = /^(yes|yeah|yep|sure|no|nope|no thanks|no thank you)$/;

  function route(text) {
    var t = _norm(text);
    var heard = 'Heard: “' + text + '”';               // a toast's text: showToast escapes it
    if (conv && MIC_OFF.indexOf(t) >= 0) {            // H14: "stop" ends the conversation (and any reading)
      stop();
      micOff();
      showToast(heard, 'The microphone is off', 'info');
      return;
    }
    if (YES_NO.test(t) && _el('askPanel') && !asking) {
      // A change on a card is made only by pressing its Yes (H7) - a word heard can be a word misheard
      if (window._assistProposal && /^(yes|yeah|yep|sure)$/.test(t)) { showToast(heard, 'To make the change, press Yes on the card.', 'info'); return; }
      if (window._assistProposal) { window.assistProposalNo(); showToast(heard, 'Nothing was changed', 'info'); return; }
      window._gwVoiceAsked = true;
      window.askGroundwork(text);                       // the assistant's own question ("Did you mean ...?") hears it
      return;
    }
    var cmd = COMMANDS.filter(function (c) { return c.words.indexOf(t) >= 0; })[0];
    if (cmd) {
      var undo = cmd.run();
      if (undo === false) { showToast(heard, 'There is nothing to do that with right now.', 'info'); return; }
      showToast(heard, cmd.said, 'info', typeof undo === 'function' ? undo : null);
      return;
    }
    // Anything else is a question or an instruction, for the Ask bar to handle as if it were typed
    showToast(heard, 'Asking Groundwork', 'info', function () { var p = _el('askPanel'); if (p) p.remove(); });
    var box = _el('gwAskBox');
    if (box) box.value = text;                        // what was heard, where a typed question would be
    window._gwVoiceAsked = true;
    window.askGroundwork(text);   // a global of app.js's (s30's stripper can't see its definition past a regex there)
  }

  // ── The microphone, in the Ask box (item 114 H15); alone in the top bar when AI is off and the box is gone ──────────
  var MIC_SVG = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    + 'stroke-linejoin="round" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/>'
    + '<line x1="12" y1="17" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>';

  function _micButton() {
    var b = _el('gwMicBtn'), wrap = _el('gwAskWrap');
    if (prefs.voice_commands !== 'on') {
      if (b) b.remove();
      if (wrap) wrap.classList.remove('has-mic', 'no-box');
      micOff();
      return;
    }
    if (!wrap) return;
    var box = _el('gwAskBox');
    wrap.classList.add('has-mic');
    wrap.classList.toggle('no-box', !box || box.offsetParent === null);
    if (b) return;
    b = document.createElement('button');
    b.id = 'gwMicBtn';
    b.type = 'button';
    b.addEventListener('click', function (e) { e.preventDefault(); talkToggle(); });
    wrap.appendChild(b);
    _micState(conv ? 'listening' : 'idle');
  }

  function _micState(s) {
    var b = _el('gwMicBtn');
    if (!b) return;
    var wrap = _el('gwAskWrap'), box = _el('gwAskBox');
    if (wrap) wrap.classList.toggle('no-box', !box || box.offsetParent === null);
    b.dataset.state = s;
    b.innerHTML = s === 'working' ? '<span class="gw-working-dots" aria-hidden="true"><i></i><i></i><i></i></span>' : MIC_SVG;
    b.setAttribute('aria-pressed', s === 'idle' ? 'false' : 'true');
    var tip = s === 'listening' ? 'Listening - tap to turn the microphone off (Alt+V)'
      : s === 'working' ? 'Hearing what you said'
      : 'Talk with Groundwork - tap to turn the microphone on (Alt+V). Try "open my budget", "show me my Kroger '
        + 'transactions", "what can I say?". What you say is recognised on this computer.';
    b.setAttribute('aria-label', tip);
    b.title = tip;
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
    var vs = null, mic = null;
    try { vs = await API.get('/api/voice'); } catch (e) { vs = { available: false, reason: 'The voice engine could not be checked.' }; }
    try { mic = (await API.get('/api/voice/microphone')).allowed_at; } catch (e) { mic = null; }
    var small = 'font-size:var(--fs-xs);color:var(--slate-2);margin:2px 0 10px';
    card.innerHTML = '<div class="card-label">Reading and voice</div>'
      + '<div class="field mb-4"><label>Text size</label><div>' + _radios('gwTextSize', prefs.text_size, [['100', 'Standard'], ['115', 'Larger'], ['130', 'Largest']]) + '</div>'
      + '<div style="' + small + '">Every page, at once.</div></div>'
      + '<div class="field mb-4"><label>Read aloud</label><div>' + _radios('gwReadAloud', prefs.read_aloud, [['off', 'Off'], ['key', 'When I press Alt+R'], ['hover', 'When I rest the pointer on something']]) + '</div>'
      + '<div>' + _radios('gwReadRate', prefs.read_rate, [['slower', 'Slower'], ['normal', 'Normal'], ['faster', 'Faster']]) + '</div>'
      + '<div style="' + small + '">Reads the part of the page you point at, in Groundwork\'s own words, then asks if you\'d like it explained further. '
      + 'Esc stops. ' + (vs && vs.speak && vs.speak.available
        ? "Read in Groundwork's own voice, made on this computer - what it reads is never sent anywhere or kept."
        : "Read with a voice installed on this computer" + (vs && vs.speak && vs.speak.reason ? ' (' + esc(vs.speak.reason) + ')' : '') + '.')
      + '</div></div>'
      + '<div class="field"><label>Voice commands</label><div>' + _radios('gwVoice', prefs.voice_commands, [['off', 'Off'], ['on', 'On (talk with Groundwork)']]) + '</div>'
      + '<div style="' + small + '">Tap the microphone in the Ask box (or Alt+V) and talk - a question, or "read this", "read the page", '
      + '"explain further", "repeat", "slower", "faster", "next", "go back", "yes", "no". It stays on until you tap it again, say "stop", '
      + 'say nothing for a minute, or leave Groundwork\'s window. While Groundwork is reading aloud you can cut in with "stop", '
      + '"next", "repeat", "slower" or "faster"; nothing else is taken while it speaks. Say "what can I say?" to hear more. An answer to a '
      + 'spoken question is read back in Groundwork\'s own words. A change is made only by pressing Yes on its card. What you say is '
      + 'recognised by Groundwork on this computer and is never sent anywhere or kept.'
      + (vs && !vs.available ? '<br><span style="color:var(--ember-text)">Not available in this copy: ' + esc(vs.reason || '') + '</span>' : '')
      + (mic ? '<br>You allowed the microphone on ' + esc(new Date(mic).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }))
        + ', so Groundwork doesn\'t ask again. It listens only while the microphone shows it is on. '
        + '<button class="btn btn-ghost btn-sm" id="gwMicForget" style="font-size:var(--fs-xs)">Ask me next time</button>' : '')
      + '</div></div>';
    var forget = _el('gwMicForget');
    if (forget) forget.addEventListener('click', async function () {
      try { await API.delete('/api/voice/microphone'); micKept = false; showToast('Groundwork will ask about the microphone next time', '', 'info'); }
      catch (e) { showToast('Could not change it', e.message || '', 'error'); }
      _card();
    });
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
    if (prefs.voice_commands === 'on' || prefs.read_aloud !== 'off') {                  // the server readies the models
      API.get('/api/voice').then(function (v) { own.available = !!(v && v.speak && v.speak.available); }).catch(function () {});
    }
    _micButton();
    _card();
    var box = _el('gwAskBox');
    if (box && window.MutationObserver) new window.MutationObserver(function () { _micState(conv ? 'listening' : 'idle'); })
      .observe(box, { attributes: true, attributeFilter: ['style', 'class', 'hidden'] });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();

  window.GWVoice = { say: function (w) { return say(w); }, on: function () { return !!conv; } };   // item 114 H14
  GWTeaching.register('access', { load: load, route: route, wav: wav, readSection: readSection, answer: answer, stop: stop, prefs: prefs,
                                   talk: talkToggle, listening: function () { return !!conv; } });
})();
