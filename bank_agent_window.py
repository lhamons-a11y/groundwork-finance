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

STEP_KINDS = ('click', 'choose', 'sign_in')
_FIELDS = {'k', 'role', 'text', 'field', 'option'}
_MAX = 80


def _clean_text(v):
    s = re.sub(r'\s+', ' ', str(v or '')).strip()[:_MAX]
    return re.sub(r'\d{4,}', '••••', s)          # account and card numbers never leave the page


def clean_step(raw):
    """A step as Groundwork keeps it, or None. Only the named fields, only the known kinds, digits masked."""
    if not isinstance(raw, dict) or raw.get('k') not in STEP_KINDS:
        return None
    step = {'k': raw['k']}
    for f in ('role', 'text', 'field', 'option'):
        if f in raw and raw[f] not in (None, ''):
            step[f] = _clean_text(raw[f])
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
    if k == 'sign_in':
        return 'Sign in (Groundwork fills your saved login)'
    if k == 'choose':
        return f"Choose “{step.get('option', '')}”" + (f" in “{step['field']}”" if step.get('field') else '')
    return f"Click “{step.get('text', '')}”"


# ── The window process ─────────────────────────────────────────────────────────
# Installed on each page load. Real clicks only (isTrusted). Reads the clicked control's NAME - never a typed value.
RECORD_SCRIPT = r'''(function () {
  if (window.__gwRecorder) return;
  window.__gwRecorder = true;
  function api() { return window.pywebview && window.pywebview.api && window.pywebview.api.step; }
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
  document.addEventListener('click', function (e) {
    if (!e.isTrusted || !api()) return;
    var el = e.target && e.target.closest ? e.target.closest('a,button,[role=button],[role=link],[role=tab],[role=menuitem],input[type=submit],input[type=button]') : null;
    if (!el) return;
    var form = el.closest ? el.closest('form') : null;
    if (form && form.querySelector('input[type=password]')) { window.pywebview.api.step({k: 'sign_in'}); return; }
    window.pywebview.api.step({k: 'click', role: (el.getAttribute('role') || el.tagName.toLowerCase()), text: nameOf(el)});
  }, true);
  document.addEventListener('change', function (e) {
    if (!e.isTrusted || !api()) return;
    var el = e.target;
    if (el && el.tagName === 'SELECT' && el.selectedIndex >= 0) {
      window.pywebview.api.step({k: 'choose', field: labelOf(el), option: nameOf(el.options[el.selectedIndex])});
    } else if (el && el.tagName === 'INPUT' && (el.type === 'radio' || el.type === 'checkbox') && el.checked) {
      window.pywebview.api.step({k: 'choose', field: el.getAttribute('name') || '', option: labelOf(el)});
    }
  }, true);
})();'''


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


def start_recording(key, url, wait_seconds=20.0):
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
    proc.stdin.write(url + '\n')
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

FETCH_STATUSES = ('step', 'waiting_code', 'stopped', 'downloaded', 'no_download', 'done')
STOP_REASONS = ('page_changed', 'bot_check', 'no_login', 'code_timeout', 'cancelled')
STEP_WAIT = 15.0          # seconds for a step's control to appear after a page load
CODE_WAIT = 300.0         # the user types a code
DOWNLOAD_WAIT = 120.0

DO_SCRIPT = r'''(function () {
  if (window.__gwDo) return;
  function nameOf(el) {
    var t = el.getAttribute('aria-label') || el.getAttribute('title') || '';
    if (!t && el.tagName === 'INPUT' && (el.type === 'submit' || el.type === 'button')) t = el.getAttribute('value') || '';
    if (!t) t = (el.innerText || el.textContent || '');
    return String(t).replace(/\s+/g, ' ').trim().slice(0, 80);
  }
  function same(recorded, actual) {
    var esc = recorded.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/••••/g, '\\d{4,}');
    return new RegExp('^' + esc + '$', 'i').test(actual);
  }
  function visible(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
  function setVal(el, v) {
    var proto = Object.getPrototypeOf(el), d = Object.getOwnPropertyDescriptor(proto, 'value');
    if (d && d.set) d.set.call(el, v); else el.value = v;
    el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true}));
  }
  function botCheck() {
    if (document.querySelector('iframe[src*="captcha"],.g-recaptcha,.h-captcha,[id*="captcha" i]')) return true;
    return /unusual activity|verify (that )?you(\u2019|')?re (a )?human|are you a robot/i.test((document.body && document.body.innerText || '').slice(0, 4000));
  }
  function codeAsked() {
    if (document.querySelector('input[type=password]')) return false;
    var c = document.querySelector('input[autocomplete="one-time-code"]');
    if (c && visible(c)) return true;
    return Array.prototype.some.call(document.querySelectorAll('input'), function (i) {
      var n = (i.name || '') + ' ' + (i.id || '') + ' ' + (i.getAttribute('aria-label') || '') + ' ' + (i.placeholder || '');
      return visible(i) && /\b(code|otp|one.?time|verification)\b/i.test(n);
    });
  }
  window.__gwDo = function (step, login) {
    if (botCheck()) return 'bot';
    if (step.k === 'sign_in') {
      var p = Array.prototype.filter.call(document.querySelectorAll('input[type=password]'), visible)[0];
      if (!p) return codeAsked() ? 'code' : 'missing';
      if (!login) return 'no_login';
      var form = p.closest('form') || document;
      var users = Array.prototype.filter.call(form.querySelectorAll('input[type=text],input[type=email],input[type=tel],input:not([type])'), visible);
      if (users.length) setVal(users[0], login[0]);
      setVal(p, login[1]);
      var btn = form.querySelector('button[type=submit],input[type=submit],button:not([type])');
      if (btn) btn.click(); else if (form.requestSubmit) form.requestSubmit();
      return 'ok';
    }
    if (step.k === 'click') {
      var els = Array.prototype.filter.call(document.querySelectorAll('a,button,[role=button],[role=link],[role=tab],[role=menuitem],input[type=submit],input[type=button]'),
        function (el) { return visible(el) && same(step.text || '', nameOf(el)); });
      if (els.length === 1) { els[0].click(); return 'ok'; }
      if (els.length > 1) return 'ambiguous';
      return codeAsked() ? 'code' : 'missing';
    }
    if (step.k === 'choose') {
      var sels = Array.prototype.filter.call(document.querySelectorAll('select'), visible);
      for (var i = 0; i < sels.length; i++) {
        for (var j = 0; j < sels[i].options.length; j++) {
          if (same(step.option || '', nameOf(sels[i].options[j]))) {
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
      if (radios.length === 1) { radios[0].click(); return 'ok'; }
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

    def __init__(self, window, steps, login, say, now=None, sleep=None, downloads=None):
        import time
        self.w, self.steps, self.login, self.say = window, steps, login, say
        self.now, self.sleep = now or time.monotonic, sleep or time.sleep
        self.downloads = downloads        # callable -> set of file names, or None
        self.cancelled = False

    def _try(self, step):
        js = DO_SCRIPT + ';window.__gwDo ? window.__gwDo(' + json.dumps(step) + ', ' + \
             (json.dumps(list(self.login)) if (step.get('k') == 'sign_in' and self.login) else 'null') + ') : "missing";'
        try:
            return self.w.evaluate_js(js)
        except Exception:
            return 'missing'

    def run(self):
        before = self.downloads() if self.downloads else set()
        for i, step in enumerate(self.steps):
            deadline, waiting_code = self.now() + STEP_WAIT, False
            while True:
                if self.cancelled:
                    self.say(fetch_line('stopped', i=i, why='cancelled'))
                    return 'cancelled'
                r = self._try(step)
                if r == 'ok':
                    self.say(fetch_line('step', i=i))
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
    window = webview.create_window(title=bw.window_title(url) + ' - Groundwork is fetching your download', url=url,
                                   width=1100, height=800)
    driver = Driver(window, steps_, _read_login(key), lambda l: (sys.stdout.write(l + '\n'), sys.stdout.flush()),
                    downloads=_downloads_lister())

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
    if s == 'waiting_code':
        return 'Your bank is asking for a code. Type it in the window; Groundwork carries on after that.'
    if s == 'stopped':
        return {'page_changed': "Stopped: the page didn't look as recorded. The window is yours - finish by hand, or record the steps again.",
                'bot_check': 'Stopped: your bank showed a check for automated access. Groundwork stops there; the window is yours.',
                'no_login': 'Stopped: no saved login for this account.',
                'code_timeout': 'Stopped: no code was entered in 5 minutes.',
                'cancelled': 'Stopped.'}.get(ev.get('why'), 'Stopped.')
    if s == 'downloaded':
        return f"Downloaded {ev.get('file', '')} to your Downloads folder. It's waiting for you in the import review."
    if s == 'no_download':
        return "The steps ran, but no file arrived in 2 minutes. Check the window."
    return ''
