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
