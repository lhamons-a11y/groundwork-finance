"""
The bank agent's window (gw 2.0/BANK_AGENT.md, item 57; Rob 2026-10-09: A1 (b) "change the viewers rule", A2-A11).

The plain bank viewer (bank_window.py) is unchanged and still reads nothing from a page; s126 holds it. Everything the
agent may do to a bank page lives in THIS module, in the same kind of separate, private process: Groundwork's own
executable started with --bank-agent, given the account's HTTPS link on stdin and nothing else of Groundwork's.

Stage 2 - "show me once" (A5). While the user does their usual download, a page script reports each real click and
each choice from a list, described the way the page names it (a label, a role, a link's text). It never reads a
typed value - no text, password or date box - and never page content, balances or account numbers: a run of four
or more digits in a label is masked. Each step goes back to Groundwork as one line, "step <json>", checked again
there (parse_step_line). This module imports nothing of Groundwork's (s173).
"""
import json
import re
import sys
import threading

STEP_KINDS = ('click', 'choose', 'sign_in', 'sign_in_user')
_FIELDS = {'k', 'role', 'text', 'field', 'option', 'opt'}
# Every number on a page - an amount, a balance, an account's last digits - becomes this mark; the replay treats it
# as "any number here" (Rob's first real run recorded "$2,608.57 $2,396.32" in a link's name).
MASK = '••••'
# What is private: money ($2,608.57), comma-grouped or decimal figures, and runs of 4+ digits (account numbers).
# Small whole numbers stay, so "Last 30 days" never matches "Last 90 days" at replay.
_NUMBER = r'\$\s?\d[\d,]*(?:\.\d+)?|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+\.\d+\b|\d{4,}'
_MAX = 80


def _clean_text(v):
    s = re.sub(r'\s+', ' ', str(v or '')).strip()[:_MAX]
    s = re.sub(_NUMBER, MASK, s)                  # amounts, balances and account digits never leave the page
    return re.sub('(?:' + MASK + r'\s*)+' + MASK, MASK, s)   # several numbers in a row read as one mark


def clean_step(raw):
    """A step as Groundwork keeps it, or None. Only the named fields, only the known kinds, digits masked."""
    if not isinstance(raw, dict) or raw.get('k') not in STEP_KINDS:
        return None
    step = {'k': raw['k']}
    for f in ('role', 'text', 'field', 'option'):
        if f in raw and raw[f] not in (None, ''):
            step[f] = _clean_text(raw[f])
    if raw.get('opt') is True:
        step['opt'] = True                          # only if the bank asks (a code check, "trust this device")
    if step['k'] == 'click' and not step.get('text'):
        return None
    if step['k'] == 'choose' and not step.get('option'):
        return None
    return step


def step_line(step):
    return 'step ' + json.dumps(step, separators=(',', ':'))


def parse_step_line(line):
    """Groundwork's side: a 'step <json>' line, checked again, or None."""
    line = (line or '').strip()
    if not line.startswith('step '):
        return None
    try:
        raw = json.loads(line[5:])
    except ValueError:
        return None
    if not isinstance(raw, dict) or set(raw) - _FIELDS:
        return None
    return clean_step(raw)


def step_words(step):
    """A step in words, for the user (A5)."""
    k = step.get('k')
    tail = ' (only if your bank asks)' if step.get('opt') else ''
    if k == 'sign_in':
        return 'Sign in (Groundwork fills your saved login)' + tail
    if k == 'sign_in_user':
        return 'Enter your username (Groundwork fills it)' + tail
    return _step_words_rest(step) + tail


def _step_words_rest(step):
    k = step.get('k')
    if k == 'choose':
        return f"Choose “{step.get('option', '')}”" + (f" in “{step['field']}”" if step.get('field') else '')
    return f"Click “{step.get('text', '')}”"


# ── The window process ─────────────────────────────────────────────────────────
# Installed on each page load. Real clicks only (isTrusted). Reads the clicked control's NAME - never a typed value.
RECORD_SCRIPT = r'''(function () {
  if (window.__gwRecorder) return;
  window.__gwRecorder = true;
  function gwBar(text, tone) {
    var host = document.getElementById('__gwBarHost');
    if (!host) {
      host = document.createElement('div');
      host.id = '__gwBarHost';
      host.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:2147483647;pointer-events:none';
      (document.body || document.documentElement).appendChild(host);
      host.attachShadow({mode: 'open'}).innerHTML = '<style>@keyframes gwrec{0%,100%{opacity:1}50%{opacity:.15}}'
        + '#d{display:none;width:11px;height:11px;border-radius:50%;background:#e5322d;margin-right:9px;vertical-align:-1px;animation:gwrec 1s infinite}'
        + '@media (prefers-reduced-motion: reduce){#d{animation:none}}</style>'
        + '<div id="b" style="margin:0 auto 10px;max-width:760px;padding:10px 16px;border-radius:8px;font:13px/1.45 system-ui,sans-serif;color:#fff;background:#1f3a2e;box-shadow:0 4px 18px rgba(0,0,0,.25)"><span id="d"></span><span id="t"></span></div>';
    }
    var b = host.shadowRoot.getElementById('b');
    host.shadowRoot.getElementById('t').textContent = text;
    host.shadowRoot.getElementById('d').style.display = tone === 'rec' ? 'inline-block' : 'none';
    b.style.background = tone === 'ask' ? '#8a4b08' : '#1f3a2e';
  }
  window.__gwBar = gwBar;
  function api() { return window.pywebview && window.pywebview.api && window.pywebview.api.step; }
  var noted = 0;
  try { noted = parseInt(sessionStorage.getItem('__gwNoted') || '0', 10) || 0; } catch (e) {}
  function say() {
    gwBar('Recording for Groundwork \u2014 do your usual download. Groundwork notes your clicks and choices, never what you type. '
      + (noted ? noted + ' step' + (noted === 1 ? '' : 's') + ' noted. ' : '') + 'Press Done in Groundwork when the file has downloaded.', 'rec');
  }
  function note(step) {
    window.pywebview.api.step(step);
    noted += 1;
    try { sessionStorage.setItem('__gwNoted', String(noted)); } catch (e) {}
    say();
  }
  say();
  function nameOf(el) {
    var t = el.getAttribute('aria-label') || el.getAttribute('title') || '';
    if (!t && el.tagName === 'INPUT' && (el.type === 'submit' || el.type === 'button')) t = el.getAttribute('value') || '';
    if (!t) t = (el.innerText || el.textContent || '');
    return String(t).replace(/\s+/g, ' ').trim().slice(0, 80);
  }
  function labelOf(el) {
    var id = el.getAttribute('id');
    var l = id ? document.querySelector('label[for="' + id.replace(/"/g, '') + '"]') : null;
    if (!l && el.closest) l = el.closest('label');
    return l ? nameOf(l) : (el.getAttribute('aria-label') || el.getAttribute('name') || '');
  }
  function userBox(form) {
    return Array.prototype.some.call(form.querySelectorAll('input[type=text],input[type=email],input[type=tel],input:not([type])'), function (i) {
      return /user|login|e-?mail|member|account|id\b/i.test((i.name || '') + ' ' + (i.id || '') + ' ' + (i.getAttribute('autocomplete') || '') + ' ' + (i.getAttribute('aria-label') || ''));
    });
  }
  // A code check: a code box, or a page asking to trust or remember this device. Steps taken here are optional.
  function checkPage() {
    if (document.querySelector('input[autocomplete="one-time-code"]')) return true;
    var codeBox = Array.prototype.some.call(document.querySelectorAll('input'), function (i) {
      return /\b(code|otp|one.?time|verification|passcode)\b/i.test((i.name || '') + ' ' + (i.id || '') + ' ' + (i.getAttribute('aria-label') || '') + ' ' + (i.placeholder || ''));
    });
    if (codeBox) return true;
    return /trust (this )?(device|computer|browser)|remember (this )?(device|computer|browser)|verify (your )?identity|security code|one.?time (pass)?code/i.test((document.body && document.body.innerText || '').slice(0, 4000));
  }
  function signInForm(form) {
    if (!form) return null;
    if (form.querySelector('input[type=password]')) return 'sign_in';
    if (userBox(form) && !checkPage()) return 'sign_in_user';
    return null;
  }
  // Any submit - a click, or Enter - of a sign-in form is the sign-in step (Rob's first run: Enter was missed)
  document.addEventListener('submit', function (e) {
    if (!api()) return;
    var kind = signInForm(e.target);
    if (kind) note({k: kind, opt: checkPage()});
  }, true);
  document.addEventListener('click', function (e) {
    if (!e.isTrusted || !api()) return;
    var el = e.target && e.target.closest ? e.target.closest('a,button,[role=button],[role=link],[role=tab],[role=menuitem],input[type=submit],input[type=button]') : null;
    if (!el) return;
    if (signInForm(el.closest ? el.closest('form') : null)) return;   // the submit listener records it
    note({k: 'click', role: (el.getAttribute('role') || el.tagName.toLowerCase()), text: nameOf(el), opt: checkPage()});
  }, true);
  document.addEventListener('change', function (e) {
    if (!e.isTrusted || !api()) return;
    var el = e.target;
    if (el && el.tagName === 'SELECT' && el.selectedIndex >= 0) {
      note({k: 'choose', field: labelOf(el), option: nameOf(el.options[el.selectedIndex]), opt: checkPage()});
    } else if (el && el.tagName === 'INPUT' && (el.type === 'radio' || el.type === 'checkbox') && el.checked) {
      note({k: 'choose', field: el.getAttribute('name') || '', option: labelOf(el), opt: checkPage()});
    }
  }, true);
})();'''


def unique_path(folder, name):
    """Where a download lands: the Downloads folder, under the bank's own file name - with " (2)", " (3)" ... when that
    name is taken, so an earlier file is never overwritten."""
    import os
    base = os.path.basename(name or '') or 'download'
    stem, ext = os.path.splitext(base)
    path, n = os.path.join(folder, base), 2
    while os.path.exists(path):
        path, n = os.path.join(folder, f'{stem} ({n}){ext}'), n + 1
    return path


def save_downloads_to_downloads_folder(platform_key):
    """Rob's real run (2026-10-09): the bank's download opened Windows' Save As dialog, a system window the agent can't
    see or answer, so the fetch waited forever. In the agent's windows only, a download is saved straight into the
    Downloads folder - the folder the watcher reads and the import review offers to tidy away. pywebview 6 on Windows
    always shows the dialog (EdgeChrome.on_download_starting); this replaces that one handler in this process. The plain
    bank viewer (bank_window.py) is not touched and keeps its dialog."""
    if platform_key != 'win32':
        return False                                  # macOS / Linux: not yet measured (named in BANK_AGENT.md)
    import bank_window as bw
    try:
        from webview.platforms import edgechromium
    except Exception:
        return False

    def on_download_starting(self, sender, args):
        from webview import settings as webview_settings
        if not webview_settings.get('ALLOW_DOWNLOADS'):
            args.Cancel = True
            return
        args.ResultFilePath = unique_path(str(bw.downloads_dir()), args.ResultFilePath)
        try:
            args.Handled = True                       # no download flyout either
        except Exception:
            pass
    edgechromium.EdgeChrome.on_download_starting = on_download_starting
    return True


class RecordApi:
    """The one function the page may call while recording. Everything it is given is cleaned before it leaves."""
    def __init__(self, out=None):
        self._out = out or sys.stdout

    def step(self, raw):
        s = clean_step(raw)
        if s is not None:
            self._out.write(step_line(s) + '\n')
            self._out.flush()
        return None


def child_main(mode):
    """The agent's window process: URL in on stdin -> the bank, with the recorder -> steps out as lines."""
    import bank_window as bw
    if mode == 'fetch':
        return fetch_child_main()
    url = sys.stdin.readline().strip()
    # A7: the account's remembered-device folder when the user ticked it ('' = private), so "Trust this device"
    # given while recording carries into the fetch (Rob's real run: the trust was lost with the private window)
    device = sys.stdin.readline().strip()
    if bw.portal_url_problem(url) or mode != 'record':
        bw._say(bw.STATUS_REFUSED_URL)
        return 2
    platform_key = bw._platform_key()
    import webview
    from webview.guilib import initialize
    try:
        renderer = getattr(initialize(bw._PINNED_GUI.get(platform_key)), 'renderer', None)
    except Exception:
        renderer = None
    if renderer != bw._EXPECTED_RENDERER.get(platform_key):
        bw._say(bw.STATUS_REFUSED_ENGINE)
        return 3
    webview.settings['ALLOW_DOWNLOADS'] = True
    save_downloads_to_downloads_folder(platform_key)
    api = RecordApi()
    window = webview.create_window(title=bw.window_title(url) + ' - showing Groundwork how', url=url,
                                   width=1100, height=800, js_api=api)

    def on_loaded(*_):
        try:
            window.evaluate_js(RECORD_SCRIPT)
        except Exception:
            pass
    window.events.loaded += on_loaded

    def _close_when_parent_goes():
        try:
            sys.stdin.read()
        except Exception:
            pass
        try:
            window.destroy()
        except Exception:
            import os
            os._exit(0)
    threading.Thread(target=_close_when_parent_goes, daemon=True).start()
    bw._say(bw.STATUS_READY)
    if device:
        webview.start(gui=bw._PINNED_GUI.get(platform_key), private_mode=False, storage_path=device)
    else:
        webview.start(gui=bw._PINNED_GUI.get(platform_key), private_mode=True)
    return 0


# ── Groundwork's side ──────────────────────────────────────────────────────────
_lock = threading.Lock()
_recordings = {}        # key -> {'proc', 'steps'}


def _command(mode):
    from pathlib import Path
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--bank-agent', mode]
    return [sys.executable, str(Path(__file__).resolve().parent / 'launch.py'), '--bank-agent', mode]


def collect(key, lines):
    """Read a recording process's lines into its steps (the reader thread's body; called directly by tests)."""
    for line in lines:
        s = parse_step_line(line)
        if s is not None:
            with _lock:
                rec = _recordings.get(key)
                if rec is not None:
                    rec['steps'].append(s)


def start_recording(key, url, wait_seconds=20.0, device_dir=''):
    """'opened' | 'already_open' | 'refused_url' | 'engine_unavailable'."""
    import subprocess
    import bank_window as bw
    if bw.portal_url_problem(url):
        return 'refused_url'
    with _lock:
        rec = _recordings.get(key)
        if rec and rec['proc'] is not None and rec['proc'].poll() is None:
            return 'already_open'
    flags = 0x08000000 if sys.platform == 'win32' else 0
    proc = subprocess.Popen(_command('record'), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, creationflags=flags)
    proc.stdin.write(url + '\n' + (device_dir or '') + '\n')
    proc.stdin.flush()
    status = bw._read_status(proc, wait_seconds)
    if status != bw.STATUS_READY:
        bw._stop(proc)
        return 'refused_url' if status == bw.STATUS_REFUSED_URL else 'engine_unavailable'
    with _lock:
        _recordings[key] = {'proc': proc, 'steps': []}
    threading.Thread(target=collect, args=(key, proc.stdout), daemon=True).start()
    return 'opened'


def steps(key):
    with _lock:
        rec = _recordings.get(key)
        return list(rec['steps']) if rec else []


def finish_recording(key):
    """Close the window and hand back the steps it saw."""
    import bank_window as bw
    with _lock:
        rec = _recordings.pop(key, None)
    if not rec:
        return []
    bw._stop(rec['proc'])
    return list(rec['steps'])


def begin_for_test(key):
    """A recording with no window, for the gate."""
    with _lock:
        _recordings[key] = {'proc': None, 'steps': []}


# ── Stage 3 - the fetch (A2, A4, A6, A7) ───────────────────────────────────────
# Started by the user only. The driver tries each saved step in order:
#   sign_in  fill the login from the vault (read here, in this process, used for the two boxes only) and submit
#   click    the one control whose name matches the recorded one (masked digits match any run of 4+ digits)
#   choose   the recorded option in the recorded list
# It stops and hands the window to the user, saying why, when (A6): the bank asks for a code (it waits up to 5
# minutes for the user to type it); the next control isn't there or there are several ("the page changed"); a
# CAPTCHA or "unusual activity" page appears (automation stops for good); the download doesn't arrive in 2 minutes.
# Nothing is guessed and nothing is retried on its own. The password never leaves this process except into the
# page's own login boxes, and is never written to a line, a log or a file.

FETCH_STATUSES = ('step', 'skipped', 'signed_in', 'waiting_code', 'stopped', 'downloaded', 'no_download', 'done')
STOP_REASONS = ('page_changed', 'bot_check', 'no_login', 'code_timeout', 'cancelled', 'sign_in_failed')
STEP_WAIT = 15.0          # seconds for a step's control to appear after a page load
CODE_WAIT = 300.0         # the user types a code
DOWNLOAD_WAIT = 120.0

DO_SCRIPT = r'''(function () {
  if (window.__gwDo) return;
  function gwBar(text, tone) {
    var host = document.getElementById('__gwBarHost');
    if (!host) {
      host = document.createElement('div');
      host.id = '__gwBarHost';
      host.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:2147483647;pointer-events:none';
      (document.body || document.documentElement).appendChild(host);
      host.attachShadow({mode: 'open'}).innerHTML = '<style>@keyframes gwrec{0%,100%{opacity:1}50%{opacity:.15}}'
        + '#d{display:none;width:11px;height:11px;border-radius:50%;background:#e5322d;margin-right:9px;vertical-align:-1px;animation:gwrec 1s infinite}'
        + '@media (prefers-reduced-motion: reduce){#d{animation:none}}</style>'
        + '<div id="b" style="margin:0 auto 10px;max-width:760px;padding:10px 16px;border-radius:8px;font:13px/1.45 system-ui,sans-serif;color:#fff;background:#1f3a2e;box-shadow:0 4px 18px rgba(0,0,0,.25)"><span id="d"></span><span id="t"></span></div>';
    }
    var b = host.shadowRoot.getElementById('b');
    host.shadowRoot.getElementById('t').textContent = text;
    host.shadowRoot.getElementById('d').style.display = tone === 'rec' ? 'inline-block' : 'none';
    b.style.background = tone === 'ask' ? '#8a4b08' : '#1f3a2e';
  }
  window.__gwBar = gwBar;

  function nameOf(el) {
    var t = el.getAttribute('aria-label') || el.getAttribute('title') || '';
    if (!t && el.tagName === 'INPUT' && (el.type === 'submit' || el.type === 'button')) t = el.getAttribute('value') || '';
    if (!t) t = (el.innerText || el.textContent || '');
    return String(t).replace(/\s+/g, ' ').trim().slice(0, 80);
  }
  function same(recorded, actual) {
    var esc = recorded.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/••••/g, '(?:\\$?\\d[\\d,]*(?:\\.\\d+)?\\s*)+');
    return new RegExp('^' + esc + '$', 'i').test(actual);
  }
  function visible(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
  function setVal(el, v) {
    var proto = Object.getPrototypeOf(el), d = Object.getOwnPropertyDescriptor(proto, 'value');
    if (d && d.set) d.set.call(el, v); else el.value = v;
    el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true}));
  }
  // Press the sign-in control for a field: the visible one named like a sign-in (whatever the bank calls it), nearest
  // the field; else a visible submit button; else Enter in the field
  function submitFor(field) {
    var named = /^(sign ?in|log ?in|login|log on|continue|next|submit)\b/i;
    var all = Array.prototype.filter.call(document.querySelectorAll('button,input[type=submit],input[type=button],[role=button],a'), visible);
    var fr = field.getBoundingClientRect();
    function dist(el) { var r = el.getBoundingClientRect(); return Math.abs(r.top - fr.bottom) + Math.abs(r.left - fr.left); }
    var hits = all.filter(function (el) { return named.test(nameOf(el)); }).sort(function (a, b) { return dist(a) - dist(b); });
    var btn = hits[0] || all.filter(function (el) { return el.type === 'submit'; })[0];
    if (btn) { btn.click(); return; }
    var form = field.closest('form');
    if (form && form.requestSubmit) { form.requestSubmit(); return; }
    ['keydown', 'keypress', 'keyup'].forEach(function (k) {
      field.dispatchEvent(new KeyboardEvent(k, {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
    });
  }
  function botCheck() {
    if (document.querySelector('iframe[src*="captcha"],.g-recaptcha,.h-captcha,[id*="captcha" i]')) return true;
    return /unusual activity|verify (that )?you(\u2019|')?re (a )?human|are you a robot/i.test((document.body && document.body.innerText || '').slice(0, 4000));
  }
  function codeAsked() {
    if (document.querySelector('input[type=password]')) return false;
    var c = document.querySelector('input[autocomplete="one-time-code"]');
    if (c && visible(c)) return true;
    var box = Array.prototype.some.call(document.querySelectorAll('input'), function (i) {
      var n = (i.name || '') + ' ' + (i.id || '') + ' ' + (i.getAttribute('aria-label') || '') + ' ' + (i.placeholder || '');
      return visible(i) && /\b(code|otp|one.?time|verification|passcode)\b/i.test(n);
    });
    if (box) return true;
    return /trust (this )?(device|computer|browser)|remember (this )?(device|computer|browser)|verify (your )?identity/i
      .test((document.body && document.body.innerText || '').slice(0, 4000));
  }
  function loginForm() {
    var p = Array.prototype.filter.call(document.querySelectorAll('input[type=password]'), visible)[0];
    if (p) return 'sign_in';
    if (!/\b(sign ?in|log ?in|login)\b/i.test((document.body && document.body.innerText || '').slice(0, 4000))) return null;
    var u = Array.prototype.filter.call(document.querySelectorAll('input[type=text],input[type=email],input[type=tel],input:not([type])'), function (i) {
      return visible(i) && /user|login|e-?mail|member|account|id\b/i.test((i.name || '') + ' ' + (i.id || '') + ' ' + (i.getAttribute('autocomplete') || '') + ' ' + (i.getAttribute('aria-label') || ''));
    })[0];
    return u ? 'sign_in_user' : null;
  }
  // A sign-in held in an embedded frame (another address the agent can't see into): its https address, or null
  function loginFrame() {
    var f = Array.prototype.filter.call(document.querySelectorAll('iframe[src]'), function (fr) {
      return visible(fr) && /log ?in|sign ?in|auth/i.test((fr.getAttribute('title') || '') + ' ' + fr.getAttribute('src'));
    })[0];
    if (!f) return null;
    try { var u = new URL(f.getAttribute('src'), location.href); return u.protocol === 'https:' ? u.href : null; } catch (e) { return null; }
  }
  window.__gwDo = function (step, login, probe) {
    if (botCheck()) return 'bot';
    // A login form on the page while the step is something else: the driver signs in first (recorded or not)
    if (step.k !== 'sign_in' && step.k !== 'sign_in_user') { var lf = loginForm(); if (lf) return 'login:' + lf; }
    if (!probe) { var fr = loginFrame(); if (fr && !document.querySelector('input[type=password]')) return 'frame:' + fr; }
    if (step.k === 'sign_in_user') {
      var pw = Array.prototype.filter.call(document.querySelectorAll('input[type=password]'), visible)[0];
      if (pw) return probe ? 'present' : 'missing';
      var ub = Array.prototype.filter.call(document.querySelectorAll('input[type=text],input[type=email],input[type=tel],input:not([type])'), visible)[0];
      if (!ub) return codeAsked() ? 'code' : 'missing';
      if (probe) return 'present';
      if (!login) return 'no_login';
      setVal(ub, login[0]);
      submitFor(ub);
      return 'ok';
    }
    if (step.k === 'sign_in') {
      var p = Array.prototype.filter.call(document.querySelectorAll('input[type=password]'), visible)[0];
      if (!p) return codeAsked() ? 'code' : 'missing';
      if (probe) return 'present';
      if (!login) return 'no_login';
      var form = p.closest('form') || document;
      var users = Array.prototype.filter.call(form.querySelectorAll('input[type=text],input[type=email],input[type=tel],input:not([type])'), visible);
      if (users.length) setVal(users[0], login[0]);
      setVal(p, login[1]);
      submitFor(p);
      return 'ok';
    }
    if (step.k === 'click') {
      var els = Array.prototype.filter.call(document.querySelectorAll('a,button,[role=button],[role=link],[role=tab],[role=menuitem],input[type=submit],input[type=button]'),
        function (el) { return visible(el) && same(step.text || '', nameOf(el)); });
      if (els.length === 1) { if (probe) return 'present'; els[0].click(); return 'ok'; }
      if (els.length > 1) return 'ambiguous';
      return codeAsked() ? 'code' : 'missing';
    }
    if (step.k === 'choose') {
      var sels = Array.prototype.filter.call(document.querySelectorAll('select'), visible);
      for (var i = 0; i < sels.length; i++) {
        for (var j = 0; j < sels[i].options.length; j++) {
          if (same(step.option || '', nameOf(sels[i].options[j]))) {
            if (probe) return 'present';
            sels[i].selectedIndex = j;
            sels[i].dispatchEvent(new Event('change', {bubbles: true}));
            return 'ok';
          }
        }
      }
      var radios = Array.prototype.filter.call(document.querySelectorAll('input[type=radio],input[type=checkbox]'), function (r) {
        var l = r.closest('label') || (r.id && document.querySelector('label[for="' + r.id + '"]'));
        return visible(r) && l && same(step.option || '', nameOf(l));
      });
      if (radios.length === 1) { if (probe) return 'present'; radios[0].click(); return 'ok'; }
      return codeAsked() ? 'code' : 'missing';
    }
    return 'missing';
  };
})();'''


def fetch_line(status, **kw):
    if status not in FETCH_STATUSES:
        raise ValueError(status)
    d = {'s': status}
    for k, v in kw.items():
        if k in ('i', 'why', 'file'):
            d[k] = v
    return 'fetch ' + json.dumps(d, separators=(',', ':'))


def parse_fetch_line(line):
    line = (line or '').strip()
    if not line.startswith('fetch '):
        return None
    try:
        d = json.loads(line[6:])
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get('s') not in FETCH_STATUSES or set(d) - {'s', 'i', 'why', 'file'}:
        return None
    if d.get('why') is not None and d['why'] not in STOP_REASONS:
        return None
    return d


class Driver:
    """Runs the saved steps against a window. `window` needs evaluate_js(js) -> result; `login` is (user, password)
    or None; `say` writes one line; `now`/`sleep` are injectable for the gate. Never says the password."""

    def __init__(self, window, steps, login, say, now=None, sleep=None, downloads=None, open_url=None):
        import time
        self.w, self.steps, self.login, self.say = window, steps, login, say
        self.open_url = open_url          # opens an https address in this window (a sign-in held in a frame)
        self.now, self.sleep = now or time.monotonic, sleep or time.sleep
        self.downloads = downloads        # callable -> set of file names, or None
        self.cancelled = False

    def _bar(self, text, tone=''):
        """The bar on the bank page (visual only). A page without the script yet ignores it."""
        try:
            self.w.evaluate_js(DO_SCRIPT + ';window.__gwBar && window.__gwBar(' + json.dumps(text) + ', ' + json.dumps(tone) + ');')
        except Exception:
            pass

    def _try(self, step, probe=False):
        uses_login = step.get('k') in ('sign_in', 'sign_in_user') and self.login and not probe
        js = DO_SCRIPT + ';window.__gwDo ? window.__gwDo(' + json.dumps(step) + ', ' + \
             (json.dumps(list(self.login)) if uses_login else 'null') + ', ' + ('true' if probe else 'false') + ') : "missing";'
        try:
            return self.w.evaluate_js(js)
        except Exception:
            return 'missing'

    def run(self):
        before = self.downloads() if self.downloads else set()
        i = 0
        while i < len(self.steps):
            step = self.steps[i]
            deadline, waiting_code, skip_to, sign_ins, framed = self.now() + STEP_WAIT, False, None, 0, False
            while True:
                if self.cancelled:
                    self.say(fetch_line('stopped', i=i, why='cancelled'))
                    return 'cancelled'
                r = self._try(step)
                if isinstance(r, str) and r.startswith('frame:') and not framed:
                    # The sign-in lives in an embedded frame from another address; open that address as the page
                    # (https only, checked again here), then sign in there. Once per step.
                    framed = True
                    target = r.split(':', 1)[1]
                    if target.startswith('https://') and self.open_url:
                        self.open_url(target)
                        deadline = self.now() + STEP_WAIT
                    self.sleep(1.0)
                    continue
                if isinstance(r, str) and r.startswith('frame:'):
                    r = 'missing'
                if r == 'code':
                    self._bar('Your bank is asking you something. Type the code or answer it here - Groundwork carries on after.', 'ask')
                elif r in ('ok', 'missing', 'ambiguous'):
                    self._bar("Groundwork is fetching your download. Please don't click unless your bank asks for something.")
                if isinstance(r, str) and r.startswith('login:'):
                    # The bank's login form, whether or not a sign-in was recorded (a remembered device can record
                    # none): sign in from the vault, then try the same step again. Twice at most, then stop.
                    if self.login is None:
                        self.say(fetch_line('stopped', i=i, why='no_login'))
                        return 'no_login'
                    if sign_ins >= 2:
                        self.say(fetch_line('stopped', i=i, why='sign_in_failed'))
                        return 'sign_in_failed'
                    sign_ins += 1
                    if self._try({'k': r.split(':', 1)[1]}) == 'ok':
                        self.say(fetch_line('signed_in', i=i))
                    deadline = self.now() + STEP_WAIT
                    self.sleep(1.0)
                    continue
                if r == 'ok':
                    self.say(fetch_line('step', i=i))
                    break
                # An optional step (a code check, "trust this device") the bank didn't show this time: when the next
                # step that isn't optional is already on the page, skip ahead to it. Nothing is guessed beyond that.
                if r in ('missing', 'code') and step.get('opt'):
                    j = next((n for n in range(i + 1, len(self.steps)) if not self.steps[n].get('opt')), None)
                    if j is not None and self._try(self.steps[j], probe=True) == 'present':
                        for n in range(i, j):
                            self.say(fetch_line('skipped', i=n))
                        skip_to = j
                        break
                if r == 'bot':
                    self.say(fetch_line('stopped', i=i, why='bot_check'))
                    return 'bot_check'
                if r == 'no_login':
                    self.say(fetch_line('stopped', i=i, why='no_login'))
                    return 'no_login'
                if r == 'code' and not waiting_code:
                    waiting_code = True
                    deadline = self.now() + CODE_WAIT
                    self.say(fetch_line('waiting_code', i=i))
                if r == 'ambiguous' or self.now() >= deadline:      # checked on every attempt, a code page included
                    why = 'code_timeout' if waiting_code else 'page_changed'
                    self.say(fetch_line('stopped', i=i, why=why))
                    return why
                self.sleep(1.0)
            i = skip_to if skip_to is not None else i + 1
        if self.downloads is None:
            self.say(fetch_line('done'))
            return 'done'
        deadline = self.now() + DOWNLOAD_WAIT
        while self.now() < deadline:
            new = self.downloads() - before
            if new:
                self.say(fetch_line('downloaded', file=sorted(new)[0]))
                return 'downloaded'
            self.sleep(1.0)
        self.say(fetch_line('no_download'))
        return 'no_download'


VAULT_SERVICE = 'Groundwork'      # the same naming as core/bank_vault.py - s174 checks they agree


def _read_login(key):
    try:
        import keyring
        raw = keyring.get_password(VAULT_SERVICE, f'{VAULT_SERVICE} - {key}')
    except Exception:
        return None
    if not raw:
        return None
    d = json.loads(raw)
    return d.get('u', ''), d.get('p', '')


def _downloads_lister():
    import os
    import bank_window as bw
    folder = bw.downloads_dir()

    def ls():
        try:
            return {n for n in os.listdir(folder) if not n.endswith(('.crdownload', '.part', '.tmp'))}
        except OSError:
            return set()
    return ls


def fetch_child_main():
    """The fetch process. stdin: the link, the account key, the saved steps (JSON), the device folder ('' = private)."""
    import bank_window as bw
    url = sys.stdin.readline().strip()
    key = sys.stdin.readline().strip()
    try:
        steps_ = [s for s in (clean_step(x) for x in json.loads(sys.stdin.readline() or '[]')) if s]
    except ValueError:
        steps_ = []
    device = sys.stdin.readline().strip()
    if bw.portal_url_problem(url) or not steps_ or not (key.startswith('account:') or key.startswith('card:')):
        bw._say(bw.STATUS_REFUSED_URL)
        return 2
    platform_key = bw._platform_key()
    import webview
    from webview.guilib import initialize
    try:
        renderer = getattr(initialize(bw._PINNED_GUI.get(platform_key)), 'renderer', None)
    except Exception:
        renderer = None
    if renderer != bw._EXPECTED_RENDERER.get(platform_key):
        bw._say(bw.STATUS_REFUSED_ENGINE)
        return 3
    webview.settings['ALLOW_DOWNLOADS'] = True
    save_downloads_to_downloads_folder(platform_key)
    window = webview.create_window(title=bw.window_title(url) + ' - Groundwork is fetching your download', url=url,
                                   width=1100, height=800)
    def _go_to(u):
        if not bw.portal_url_problem(u):            # the same https check as the link itself
            window.load_url(u)
    driver = Driver(window, steps_, _read_login(key), lambda l: (sys.stdout.write(l + '\n'), sys.stdout.flush()),
                    downloads=_downloads_lister(), open_url=_go_to)

    def _close_when_parent_goes():
        try:
            sys.stdin.read()
        except Exception:
            pass
        driver.cancelled = True
        try:
            window.destroy()
        except Exception:
            import os
            os._exit(0)
    threading.Thread(target=_close_when_parent_goes, daemon=True).start()
    started = threading.Event()
    window.events.loaded += lambda *_: started.set()

    def _drive():
        started.wait(60)
        driver.run()
    threading.Thread(target=_drive, daemon=True).start()
    bw._say(bw.STATUS_READY)
    if device:
        webview.start(gui=bw._PINNED_GUI.get(platform_key), private_mode=False, storage_path=device)
    else:
        webview.start(gui=bw._PINNED_GUI.get(platform_key), private_mode=True)
    return 0


_fetches = {}       # key -> {'proc', 'events'}


TERMINAL = ('stopped', 'downloaded', 'no_download', 'done')


def collect_fetch(key, lines, on_finish=None):
    """Read a fetch process's lines; stamp each with when Groundwork received it. When the fetch ends - however it
    ends, the user closing the window included - hand the whole run to on_finish once (stage 4, A11)."""
    from datetime import datetime
    finished = False
    for line in lines:
        d = parse_fetch_line(line)
        if d is None:
            continue
        d['at'] = datetime.now().isoformat(timespec='seconds')
        with _lock:
            f = _fetches.get(key)
            if f is not None:
                f['events'].append(d)
        if d['s'] in TERMINAL and not finished:
            finished = True
            if on_finish:
                on_finish(key, fetch_events(key))
    if not finished:                       # the window closed (or the process ended) before an outcome
        with _lock:
            f = _fetches.get(key)
            if f is not None:
                f['events'].append({'s': 'stopped', 'why': 'cancelled', 'at': datetime.now().isoformat(timespec='seconds')})
        if on_finish:
            on_finish(key, fetch_events(key))


def start_fetch(key, url, steps_, device_dir, wait_seconds=20.0, on_finish=None):
    """'opened' | 'already_open' | 'refused_url' | 'engine_unavailable'. Started only from the user's click (A2)."""
    import subprocess
    import bank_window as bw
    if bw.portal_url_problem(url):
        return 'refused_url'
    with _lock:
        f = _fetches.get(key)
        if f and f['proc'] is not None and f['proc'].poll() is None:
            return 'already_open'
    flags = 0x08000000 if sys.platform == 'win32' else 0
    proc = subprocess.Popen(_command('fetch'), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, creationflags=flags)
    proc.stdin.write(url + '\n' + key + '\n' + json.dumps(steps_) + '\n' + (device_dir or '') + '\n')
    proc.stdin.flush()
    status = bw._read_status(proc, wait_seconds)
    if status != bw.STATUS_READY:
        bw._stop(proc)
        return 'refused_url' if status == bw.STATUS_REFUSED_URL else 'engine_unavailable'
    with _lock:
        _fetches[key] = {'proc': proc, 'events': []}
    threading.Thread(target=collect_fetch, args=(key, proc.stdout, on_finish), daemon=True).start()
    return 'opened'


def fetch_events(key):
    with _lock:
        f = _fetches.get(key)
        return list(f['events']) if f else []


def stop_fetch(key):
    import bank_window as bw
    with _lock:
        f = _fetches.pop(key, None)
    if f and f['proc'] is not None:
        bw._stop(f['proc'])
    return bool(f)


def begin_fetch_for_test(key):
    with _lock:
        _fetches[key] = {'proc': None, 'events': []}


def fetch_words(ev, steps_):
    s = ev.get('s')
    i = ev.get('i')
    if s == 'step' and i is not None and i < len(steps_):
        return 'Done: ' + step_words(steps_[i])
    if s == 'skipped' and i is not None and i < len(steps_):
        return 'Skipped (your bank didn\'t ask this time): ' + step_words(steps_[i])
    if s == 'signed_in':
        return 'Signed in with your saved login.'
    if s == 'waiting_code':
        return 'Your bank is asking for a code. Type it in the window; Groundwork carries on after that.'
    if s == 'stopped':
        return {'page_changed': "Stopped: the page didn't look as recorded. The window is yours - finish by hand, or record the steps again.",
                'bot_check': 'Stopped: your bank showed a check for automated access. Groundwork stops there; the window is yours.',
                'no_login': 'Stopped: no saved login for this account.',
                'code_timeout': 'Stopped: no code was entered in 5 minutes.',
                'sign_in_failed': "Stopped: signing in didn't get past the login page twice. Check the saved login (Forget, then Save login again).",
                'cancelled': 'Stopped.'}.get(ev.get('why'), 'Stopped.')
    if s == 'downloaded':
        return f"Downloaded {ev.get('file', '')} to your Downloads folder. It's waiting for you in the import review."
    if s == 'no_download':
        return "The steps ran, but no file arrived in 2 minutes. Check the window."
    return ''
