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

STEP_KINDS = ('click', 'choose', 'sign_in', 'sign_in_user', 'read')   # read: item 68 B2, a bill's figure
_FIELDS = {'k', 'role', 'text', 'field', 'option', 'opt', 'pop', 'what', 'page', 'at'}
READ_WHAT = ('amount', 'due')        # item 68 B2: the two figures a bill's page is read for
# A13.2: a click that would agree to something is never a step; A13.3: a choice that changes a setting at the bank
# ("don't show this again") is never a step. Both are the person's own clicks, every time.
# Item 68 B8 (b) / B9, item 65 TM1: Groundwork never moves money. A control named like a payment's own button is never
# saved as a step and never pressed - in any run, a bank download included.
_PAYS = re.compile(r"^\s*(pay(\s+(now|bill|this bill|it))?|make\s+(a\s+)?payment|(submit|confirm|schedule|authori[sz]e|complete|send)\s+payment"
                   r"|send(\s+(money|now))?|transfer(\s+(funds|money|now))?|pay\s+(\$|•).*)\s*[.!]?\s*$", re.I)   # •: an amount already masked
_AGREES = re.compile(r"^\s*(i\s+)?(accept|agree)\b|\bi\s+(accept|agree)\b|\baccept\s+(and|&)\s+continue\b", re.I)
_SETTING = re.compile(r"\b(don.?t|do\s+not)\s+(show|ask|remind)\b|\bremember\s+my\s+(choice|answer)\b|\bnever\s+show\b", re.I)
# Every number on a page - an amount, a balance, an account's last digits - becomes this mark; the replay treats it
# as "any number here" (Rob's first real run recorded "$2,608.57 $2,396.32" in a link's name).
MASK = '••••'
# What is private: money ($2,608.57), comma-grouped or decimal figures, and runs of 4+ digits (account numbers).
# Small whole numbers stay, so "Last 30 days" never matches "Last 90 days" at replay.
_NUMBER = r'\$\s?\d[\d,]*(?:\.\d+)?|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+\.\d+\b|\d{4,}'
_MAX = 80


def clean_path(path):
    """Item 70 R2: a page's path as Groundwork keeps it - '/' first, no query or fragment, at most 200 characters,
    and any segment that could be an identifier (it holds a digit and is six characters or more, or holds four
    digits running) masked. '/auth/login' and '/v2/accounts' stay readable; '/accounts/6f9508b0-ab48' does not
    carry the account's id. None for anything else."""
    p = str(path or '').split('?', 1)[0].split('#', 1)[0].strip()
    if not p.startswith('/') or len(p) > 200:
        return None
    segs = [(MASK if (re.search(r'\d', s) and (len(s) >= 6 or re.search(r'\d{4}', s))) else s) for s in p.split('/')]
    return '/'.join(segs)


def clean_signin_at(url):
    """Item 70 R1: the sign-in page's address - https only, its path cleaned as clean_path. None otherwise."""
    from urllib.parse import urlsplit
    try:
        u = urlsplit(str(url or '').strip())
    except ValueError:
        return None
    path = clean_path(u.path or '/')
    if u.scheme != 'https' or not u.hostname or path is None:
        return None
    return f'https://{u.hostname.lower()}{path}'


def same_site(a, b):
    """Item 70 R1: two https addresses on the same site - their hosts' last two labels agree
    (online.superiorcu.com and www.superiorcu.com do; superiorcu.com.evil.example does not)."""
    from urllib.parse import urlsplit
    try:
        ha, hb = (urlsplit(x).hostname or '' for x in (a, b))
    except ValueError:
        return False
    return bool(ha) and bool(hb) and ha.split('.')[-2:] == hb.split('.')[-2:] and len(ha.split('.')) >= 2


def _clean_text(v):
    s = re.sub(r'\s+', ' ', str(v or '')).strip()[:_MAX]
    s = re.sub(_NUMBER, MASK, s)                  # amounts, balances and account digits never leave the page
    return re.sub('(?:' + MASK + r'\s*)+' + MASK, MASK, s)   # several numbers in a row read as one mark


def clean_step(raw):
    """A step as Groundwork keeps it, or None. Only the named fields, only the known kinds, digits masked."""
    if not isinstance(raw, dict) or raw.get('k') not in STEP_KINDS:
        return None
    if raw['k'] == 'read':
        # item 68 B2: WHERE a bill's figure is - the label beside it, digits masked - never the figure itself
        # every number in a label is masked too (a date, a short amount): it's the figure, or next month's changes it
        label = re.sub(r'\d+', '••••', _clean_text(raw.get('field') or ''))
        if raw.get('what') not in READ_WHAT or not label:
            return None
        return {'k': 'read', 'what': raw['what'], 'field': label}
    step = {'k': raw['k']}
    for f in ('role', 'text', 'field', 'option'):
        if f in raw and raw[f] not in (None, ''):
            step[f] = _clean_text(raw[f])
    page = clean_path(raw.get('page'))
    if page:
        step['page'] = page                         # item 70 R2: where it was taken, to say where a run stopped
    if raw['k'] in ('sign_in', 'sign_in_user'):
        at = clean_signin_at(raw.get('at'))
        if at:
            step['at'] = at                         # item 70 R1: where the sign-in really is
    if raw.get('opt') is True:
        step['opt'] = True                          # only if the bank asks (a code check, "trust this device")
    if raw.get('pop') is True:
        step['pop'] = True                          # A13.1: taken inside the bank's pop-up - pressed only there
        step['opt'] = True                          # ... and only if the bank shows it this time
    if step['k'] == 'click' and _AGREES.search(step.get('text') or ''):
        return None                                 # A13.2: never agrees to anything
    if step['k'] == 'click' and _PAYS.search((step.get('text') or '').replace('_', ' ')):
        return None                                 # item 68 B9 / TM1: never presses a payment's own button
    if step['k'] == 'choose' and _SETTING.search((step.get('option') or '') + ' ' + (step.get('field') or '')):
        return None                                 # A13.3: never ticks a setting at the bank
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
    tail = ' (only if your bank shows it)' if step.get('pop') else ' (only if your bank asks)' if step.get('opt') else ''
    if k == 'sign_in':
        where = f" at {step['at'].split('://', 1)[1]}" if step.get('at') else ''
        return f'Sign in (Groundwork fills your saved login){where}' + tail
    if k == 'sign_in_user':
        return 'Enter your username (Groundwork fills it)' + tail
    return _step_words_rest(step) + tail


def _step_words_rest(step):
    k = step.get('k')
    if k == 'read':
        return ('Read the amount due' if step.get('what') == 'amount' else 'Read the due date') + f" (beside \u201c{step.get('field', '')}\u201d)"
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
  // Item 68 B2: on a bill's site, two buttons mark where the amount due and the due date are. The next click on the
  // page after a button is the mark: its LABEL is noted, never the figure. The buttons live in their own shadow root.
  var armed = null;
  function markPanel(text) {
    var host = document.getElementById('__gwMarkHost');
    if (!host) {
      host = document.createElement('div');
      host.id = '__gwMarkHost';
      host.style.cssText = 'position:fixed;top:10px;right:10px;z-index:2147483647';
      (document.body || document.documentElement).appendChild(host);
      host.attachShadow({mode: 'open'}).innerHTML = '<div style="background:#1f3a2e;color:#fff;border-radius:8px;padding:10px 12px;'
        + 'font:12px/1.4 system-ui,sans-serif;box-shadow:0 4px 18px rgba(0,0,0,.25);max-width:260px">'
        + '<div id="m" style="margin-bottom:6px"></div>'
        + '<button id="a" style="font:inherit;margin:0 6px 4px 0;cursor:pointer">This is the amount due</button>'
        + '<button id="u" style="font:inherit;cursor:pointer">This is the due date</button></div>';
      host.shadowRoot.getElementById('a').onclick = function () { armed = 'amount'; markPanel('Now click the amount due on the page.'); };
      host.shadowRoot.getElementById('u').onclick = function () { armed = 'due'; markPanel('Now click the due date on the page.'); };
    }
    host.shadowRoot.getElementById('m').textContent = text;
  }
  window.__gwMark = markPanel;
  window.__gwBar = gwBar;
  function api() { return window.pywebview && window.pywebview.api && window.pywebview.api.step; }
  var noted = 0;
  var countKey = '__gwNoted:' + (window.__gwRecId || '');      // per recording, so an old count never carries over
  try { noted = parseInt(sessionStorage.getItem(countKey) || '0', 10) || 0; } catch (e) {}
  function say() {
    if (window.__gwPay) {
      gwBar('Recording the way to pay this bill \u2014 go to your bank\u2019s payment screen for it. Stop before you enter an amount; Groundwork never pays. '
        + (noted ? noted + ' step' + (noted === 1 ? '' : 's') + ' noted. ' : '') + 'Press Done in Groundwork when you are there.', 'rec');
      return;
    }
    gwBar('Recording for Groundwork \u2014 do your usual download. Groundwork notes your clicks and choices, never what you type. '
      + (noted ? noted + ' step' + (noted === 1 ? '' : 's') + ' noted. ' : '') + 'Press Done in Groundwork when the file has downloaded.', 'rec');
  }
  function note(step) {
    step.page = location.pathname;                                      // item 70 R2
    if (step.k === 'sign_in' || step.k === 'sign_in_user') step.at = location.origin + location.pathname;   // R1
    window.pywebview.api.step(step);
    noted += 1;
    try { sessionStorage.setItem(countKey, String(noted)); } catch (e) {}
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
  // A13.1: the bank's pop-up - a dialog box over the page
  function inPopup(el) {
    return !!(el && el.closest && el.closest('[role=dialog],[role=alertdialog],[aria-modal=true],dialog'));
  }
  // The text next to a marked figure (item 68 B2) - the label a later run finds it by. The figure itself is cut out.
  function labelFor(el) {
    var own = (el.innerText || el.textContent || '').trim(), x = el;
    for (var n = 0; n < 4 && x.parentElement; n++) {
      x = x.parentElement;
      var t = (x.innerText || '').split(own).join(' ').replace(/\s+/g, ' ').trim();
      if (t) return t.length <= 60 ? t : '';
    }
    return '';
  }
  if (window.__gwBill) markPanel('Go to your bill. Then press a button below and click that figure on the page.');
  document.addEventListener('click', function (e) {
    if (!e.isTrusted || !api()) return;
    if (e.target && e.target.id === '__gwMarkHost') return;          // the marking buttons are not a step
    if (window.__gwBill && armed) {
      e.preventDefault(); e.stopPropagation();
      var what = armed;
      armed = null;
      var lab = labelFor(e.target);
      if (lab) { note({k: 'read', what: what, field: lab}); markPanel((what === 'amount' ? 'Amount due' : 'Due date') + ' marked. Mark the other, or press Done in Groundwork.'); }
      else markPanel('Groundwork could not find a label beside that. Try clicking the figure itself.');
      return;
    }
    var el = e.target && e.target.closest ? e.target.closest('a,button,[role=button],[role=link],[role=tab],[role=menuitem],input[type=submit],input[type=button]') : null;
    if (!el) return;
    if (signInForm(el.closest ? el.closest('form') : null)) return;   // the submit listener records it
    // A page with no form (Rob's bank): a click on a control named like a sign-in, with a password box showing
    if (/(^|[\s_])(sign ?in|log ?in|login|log on)([\s_]|$)/i.test(nameOf(el).replace(/_/g, ' ') + ' ' + (el.innerText || ''))
        && Array.prototype.some.call(document.querySelectorAll('input[type=password]'), function (p) { var r = p.getBoundingClientRect(); return r.width > 0 && r.height > 0; })) {
      note({k: 'sign_in', opt: checkPage()});
      return;
    }
    note({k: 'click', role: (el.getAttribute('role') || el.tagName.toLowerCase()), text: nameOf(el), opt: checkPage(), pop: inPopup(el)});
  }, true);
  document.addEventListener('change', function (e) {
    if (!e.isTrusted || !api()) return;
    var el = e.target;
    if (el && el.tagName === 'SELECT' && el.selectedIndex >= 0) {
      note({k: 'choose', field: labelOf(el), option: nameOf(el.options[el.selectedIndex]), opt: checkPage(), pop: inPopup(el)});
    } else if (el && el.tagName === 'INPUT' && (el.type === 'radio' || el.type === 'checkbox') && el.checked) {
      note({k: 'choose', field: el.getAttribute('name') || '', option: labelOf(el), opt: checkPage(), pop: inPopup(el)});
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
    kind_line = sys.stdin.readline().strip()
    is_bill = kind_line == 'bill'                          # item 68 B2: the marking buttons
    is_pay = kind_line == 'pay'                            # item 68 B8 (b): the way to the bank's bill pay
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
    import secrets
    rec_id = secrets.token_hex(8)              # names this recording's step count on the page
    window = webview.create_window(title=bw.window_title(url) + ' - showing Groundwork how', url=url,
                                   width=1100, height=800, js_api=api)

    def on_loaded(*_):
        try:
            window.evaluate_js('window.__gwRecId = ' + json.dumps(rec_id) + ';'
                               + ('window.__gwBill = true;' if is_bill else '') + ('window.__gwPay = true;' if is_pay else '')
                               + RECORD_SCRIPT)
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


def start_recording(key, url, wait_seconds=20.0, device_dir='', from_step=None):
    """'opened' | 'already_open' | 'refused_url' | 'engine_unavailable'."""
    import subprocess
    import bank_window as bw
    if bw.portal_url_problem(url):
        return 'refused_url'
    # Recording again starts over: a window still open from before (behind, or never finished) is closed, and its
    # steps go with it (Rob: "the steps are not getting deleted when you record over them")
    with _lock:
        old = _recordings.pop(key, None)
    if old and old['proc'] is not None:
        bw._stop(old['proc'])
    flags = 0x08000000 if sys.platform == 'win32' else 0
    proc = subprocess.Popen(_command('record'), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, creationflags=flags)
    kind = 'bill' if str(key).startswith('bill:') else 'pay' if str(key).startswith('pay:') else ''
    proc.stdin.write(url + '\n' + (device_dir or '') + '\n' + kind + '\n')
    proc.stdin.flush()
    status = bw._read_status(proc, wait_seconds)
    if status != bw.STATUS_READY:
        bw._stop(proc)
        return 'refused_url' if status == bw.STATUS_REFUSED_URL else 'engine_unavailable'
    with _lock:
        _recordings[key] = {'proc': proc, 'steps': [], 'from': from_step}     # item 70 R3: kept steps before it
    threading.Thread(target=collect, args=(key, proc.stdout), daemon=True).start()
    return 'opened'


def steps(key):
    with _lock:
        rec = _recordings.get(key)
        return list(rec['steps']) if rec else []


def finish_recording(key, with_from=False):
    """Close the window and hand back the steps it saw (and, asked for, the step it re-recorded from - R3)."""
    import bank_window as bw
    with _lock:
        rec = _recordings.pop(key, None)
    if not rec:
        return ([], None) if with_from else []
    bw._stop(rec['proc'])
    return (list(rec['steps']), rec.get('from')) if with_from else list(rec['steps'])


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

FETCH_STATUSES = ('step', 'skipped', 'signed_in', 'waiting_code', 'stopped', 'downloaded', 'no_download', 'done', 'read',
                  'signed_out')
SIGN_OUT_AFTER = ('downloaded', 'done', 'no_download', 'page_changed', 'code_timeout')   # item 70 R5: never bot_check
SIGN_OUT_FOUND = ('pressed', 'none', 'already')
STOP_REASONS = ('page_changed', 'bot_check', 'no_login', 'code_timeout', 'cancelled', 'sign_in_failed', 'would_pay')
STEP_WAIT = 15.0          # seconds for a step's control to appear after a page load
SIGN_IN_SETTLE = 12.0     # seconds the old login page may still show after Sign In is pressed
CLOSE_PAUSE = 8.0         # seconds the finished window stays before closing: the file finishes writing, and the
                          # browser saves the bank page's own settings (it batches them ~5 s; a 3 s close lost a
                          # "don't show this again" tick - Rob, 2026-10-10)
_SIGN_IN_WORDS = re.compile(r'(^|[\s_])(sign ?in|log ?in|login|log on)([\s_]|$)', re.I)


def is_sign_in_step(step):
    """A recorded sign-in: either kind, or a click on a control named like one (a page with no form)."""
    return step.get('k') in ('sign_in', 'sign_in_user') or (
        step.get('k') == 'click' and bool(_SIGN_IN_WORDS.search((step.get('text') or '').replace('_', ' '))))
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
  // Press an element the way a mouse does. A native button, link, input or label takes a plain click; a styled element
  // (a web-app "button" that is a div) answers only the full press - pointer and mouse down and up, then the click.
  // Item 68 B9 / TM1: a payment's own button is never pressed - whatever the steps say
  function paysMoney(el) {
    return /^\s*(pay(\s+(now|bill|this bill|it))?|make\s+(a\s+)?payment|(submit|confirm|schedule|authori[sz]e|complete|send)\s+payment|send(\s+(money|now))?|transfer(\s+(funds|money|now))?|pay\s+\$.*)\s*[.!]?\s*$/i
      .test(nameOf(el).replace(/_/g, ' ')) || /^\s*(pay(\s+(now|bill|this bill|it))?|make\s+(a\s+)?payment|(submit|confirm|schedule|authori[sz]e|complete|send)\s+payment|send(\s+(money|now))?|transfer(\s+(funds|money|now))?)\s*[.!]?\s*$/i
      .test((el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim());
  }
  function press(el) {
    if (paysMoney(el)) return false;
    try { el.scrollIntoView({block: 'center', inline: 'nearest'}); } catch (e) {}
    if (/^(BUTTON|A|INPUT|LABEL|OPTION)$/.test(el.tagName)) { el.click(); return; }
    var r = el.getBoundingClientRect();
    var o = {bubbles: true, cancelable: true, composed: true, view: window, button: 0, buttons: 1,
             clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, pointerId: 1, pointerType: 'mouse', isPrimary: true};
    var up = Object.assign({}, o, {buttons: 0});
    el.dispatchEvent(new PointerEvent('pointerdown', o)); el.dispatchEvent(new MouseEvent('mousedown', o));
    el.dispatchEvent(new PointerEvent('pointerup', up)); el.dispatchEvent(new MouseEvent('mouseup', up));
    el.dispatchEvent(new MouseEvent('click', up));
  }
  // Press the sign-in control for a field: a visible one whose words or label read like a sign-in (whatever the bank
  // calls it; a label's underscores read as spaces), nearest the field; a sign-in / log-in name before Continue / Next;
  // else a visible submit button; else Enter in the field
  function submitFor(field) {
    var signIn = /(^|[\s_])(sign ?in|log ?in|login|log on)([\s_]|$)/i, onward = /^(continue|next|submit)\b/i;
    var all = Array.prototype.filter.call(document.querySelectorAll('button,input[type=submit],input[type=button],[role=button],[role=link],a'), visible);
    function words(el) {
      return [nameOf(el), (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim()]
        .map(function (s) { return s.replace(/_/g, ' '); });
    }
    var fr = field.getBoundingClientRect();
    function dist(el) { var r = el.getBoundingClientRect(); return Math.abs(r.top - fr.bottom) + Math.abs(r.left - fr.left); }
    function near(re) {
      return all.filter(function (el) { return words(el).some(function (w) { return re.test(w); }); })
        .sort(function (a, b) { return dist(a) - dist(b); })[0];
    }
    var btn = near(signIn) || near(onward) || all.filter(function (el) { return el.type === 'submit'; })[0];
    if (btn) { press(btn); return; }
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
  // The bank's pop-ups (A13): what is showing, and whether one asks the person to agree to something
  function popups() {
    return Array.prototype.filter.call(document.querySelectorAll('[role=dialog],[role=alertdialog],[aria-modal=true],dialog'), visible);
  }
  function asksAgreement() {
    return popups().some(function (d) {
      return /\b(terms|agreement|consent|i accept|i agree|accept (the|these|our))\b/i.test((d.innerText || '').slice(0, 4000));
    });
  }
  // Item 70 R5: the bank's own sign-out, by name. 'already' when the sign-in form is showing (signed out),
  // 'pressed' when one was pressed, 'none' when none is on the page.
  window.__gwSignOut = function () {
    if (Array.prototype.some.call(document.querySelectorAll('input[type=password]'), visible)) return 'already';
    var els = Array.prototype.filter.call(document.querySelectorAll('a,button,[role=button],[role=link],[role=menuitem]'), function (el) {
      return visible(el) && /(^|[\s_])(sign|log)\s?(out|off)([\s_]|$)/i.test(nameOf(el).replace(/_/g, ' '));
    });
    if (!els.length) return 'none';
    press(els[0]);
    return 'pressed';
  };
  window.__gwDo = function (step, login, probe) {
    if (botCheck()) return 'bot';
    if (asksAgreement()) return 'code';      // A13.2: never accepts - the person answers it, as with a code
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
    if (step.k === 'read') {
      // Item 68 B3: find the label, then the nearest amount or date beside it - read as the page shows it
      var lab = Array.prototype.filter.call(document.querySelectorAll('body *'), function (el) {
        return visible(el) && el.children.length <= 3 && same(step.field || '', (el.innerText || '').replace(/\s+/g, ' ').trim());
      })[0];
      if (!lab) return codeAsked() ? 'code' : 'missing';
      if (probe) return 'present';
      var re = step.what === 'amount' ? /\$\s?\d[\d,]*\.\d{2}/
        : /\b(\d{1,2}\/\d{1,2}\/\d{2,4}|\d{4}-\d{2}-\d{2}|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(,?\s+\d{4})?)\b/i;
      var x = lab, own = (lab.innerText || '');
      for (var n = 0; n < 5 && x; n++) {
        var m = (x.innerText || '').split(own).join(' ').match(re);
        if (m) return 'read:' + JSON.stringify({what: step.what, text: m[0]});
        x = x.parentElement;
      }
      return 'missing';
    }
    if (step.k === 'click') {
      var scope = step.pop ? popups() : [document];
      var els = [];
      scope.forEach(function (root) {
        Array.prototype.forEach.call(root.querySelectorAll('a,button,[role=button],[role=link],[role=tab],[role=menuitem],input[type=submit],input[type=button]'),
          function (el) { if (visible(el) && same(step.text || '', nameOf(el)) && els.indexOf(el) < 0) els.push(el); });
      });
      if (els.length === 1) { if (paysMoney(els[0])) return 'would_pay'; if (probe) return 'present'; press(els[0]); return 'ok'; }
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
      if (radios.length === 1) { if (probe) return 'present'; press(radios[0]); return 'ok'; }
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
        if k in ('i', 'why', 'file', 'what', 'val', 'page', 'found'):
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
    if not isinstance(d, dict) or d.get('s') not in FETCH_STATUSES or set(d) - {'s', 'i', 'why', 'file', 'what', 'val', 'page', 'found'}:
        return None
    if d.get('page') is not None and clean_path(d['page']) != d['page']:
        return None                       # item 70 R2: a path, already cleaned, and nothing else
    if d['s'] == 'signed_out' and d.get('found') not in SIGN_OUT_FOUND:
        return None
    if d['s'] == 'read' and (d.get('what') not in READ_WHAT or not isinstance(d.get('val'), str) or len(d['val']) > 40):
        return None                       # item 68: a bill's figure, as the page showed it, and nothing else
    if d.get('why') is not None and d['why'] not in STOP_REASONS:
        return None
    return d


class Driver:
    """Runs the saved steps against a window. `window` needs evaluate_js(js) -> result; `login` is (user, password)
    or None; `say` writes one line; `now`/`sleep` are injectable for the gate. Never says the password."""

    def __init__(self, window, steps, login, say, now=None, sleep=None, downloads=None, open_url=None, to_front=None,
                 open_signin=None):
        import time
        self.w, self.steps, self.login, self.say = window, steps, login, say
        # item 70 R1: the recorded sign-in address, opened once when the link leads nowhere (the window checks it)
        self.open_signin = open_signin
        self.sign_in_at = next((s['at'] for s in steps if s.get('at')), None)
        self.to_front = to_front          # item 67 G5: brings this window forward when the bank asks for a code
        self.open_url = open_url          # opens an https address in this window (a sign-in held in a frame)
        self.now, self.sleep = now or time.monotonic, sleep or time.sleep
        self.downloads = downloads        # callable -> set of file names, or None
        self.cancelled = False

    def _page(self):
        """Item 70 R2: the bank page's path right now, cleaned - to say where a run stopped. None if unreadable."""
        try:
            return clean_path(self.w.evaluate_js('location.pathname'))
        except Exception:
            return None

    def sign_out(self, wait=5.0):
        """Item 70 R5: press the bank's own Sign out, if the page has one, and give the bank a moment to finish.
        Says what happened in one line; never touches anything else."""
        try:
            found = self.w.evaluate_js(DO_SCRIPT + ';window.__gwSignOut ? window.__gwSignOut() : "none";')
        except Exception:
            found = 'none'
        found = found if found in SIGN_OUT_FOUND else 'none'
        if found == 'pressed':
            self.sleep(wait)
        self.say(fetch_line('signed_out', found=found))
        return found

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
        i, signed_in, signin_opened = 0, False, False
        while i < len(self.steps):
            step = self.steps[i]
            deadline, waiting_code, skip_to, sign_ins, framed = self.now() + STEP_WAIT, False, None, 0, False
            settle = 0.0
            while True:
                if self.cancelled:
                    self.say(fetch_line('stopped', i=i, why='cancelled'))
                    return 'cancelled'
                r = self._try(step)
                if isinstance(r, str) and r.startswith('read:'):
                    # Item 68 B3: a bill's figure, as the page shows it; Groundwork parses and shows it for a yes
                    try:
                        got = json.loads(r[5:])
                        self.say(fetch_line('read', i=i, what=got.get('what'), val=str(got.get('text') or '')[:40]))
                    except (ValueError, AttributeError):
                        pass
                    r = 'ok'
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
                    if sign_ins and self.now() < settle:
                        self.sleep(1.0)               # the old login page, still showing just after Sign In
                        continue
                    if sign_ins >= 2:
                        self.say(fetch_line('stopped', i=i, why='sign_in_failed'))
                        return 'sign_in_failed'
                    sign_ins += 1
                    if self._try({'k': r.split(':', 1)[1]}) == 'ok':
                        self.say(fetch_line('signed_in', i=i))
                        signed_in = True
                    settle = self.now() + SIGN_IN_SETTLE
                    deadline = self.now() + STEP_WAIT
                    self.sleep(1.0)
                    continue
                if r == 'ok':
                    self.say(fetch_line('step', i=i))
                    if is_sign_in_step(step):
                        signed_in = True
                    if step.get('pop'):
                        self._bar('Closed your bank\u2019s pop-up (\u201c' + (step.get('text') or step.get('option') or '') + '\u201d). Carrying on.')
                    break
                if signed_in and is_sign_in_step(step) and r in ('missing', 'present'):
                    # The recorded sign-in, already done this run (the login form has gone): it counts as done
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
                if r == 'would_pay':
                    self.say(fetch_line('stopped', i=i, why='would_pay'))     # TM1: never presses a payment's button
                    return 'would_pay'
                if r == 'no_login':
                    self.say(fetch_line('stopped', i=i, why='no_login'))
                    return 'no_login'
                if r == 'code' and not waiting_code:
                    waiting_code = True
                    if self.to_front:
                        try:
                            self.to_front()       # the code is typed in the bank's own page - never through Groundwork
                        except Exception:
                            pass
                    deadline = self.now() + CODE_WAIT
                    self.say(fetch_line('waiting_code', i=i))
                if (r == 'missing' and self.now() >= deadline and not waiting_code and not signed_in
                        and not signin_opened and self.sign_in_at and self.open_signin):
                    # Item 70 R1: the link led neither to a sign-in nor to this step - open the sign-in page the
                    # person used while recording, once (the window refuses anything not https on the link's site)
                    signin_opened = True
                    self.open_signin(self.sign_in_at)
                    deadline = self.now() + STEP_WAIT
                    self.sleep(1.0)
                    continue
                if r == 'ambiguous' or self.now() >= deadline:      # checked on every attempt, a code page included
                    why = 'code_timeout' if waiting_code else 'page_changed'
                    page = self._page() if why == 'page_changed' else None
                    self.say(fetch_line('stopped', i=i, why=why, **({'page': page} if page else {})))
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
    try:
        extra = json.loads(sys.stdin.readline() or '{}') or {}
    except ValueError:
        extra = {}
    # Item 68 B8 (b): 'pay:<bill>' goes to the bank's bill pay, signed in with the bank account's login, and stops
    login_key = str(extra.get('login_key') or '') if key.startswith('pay:') else key
    hold = str(extra.get('hold') or '')[:400] if key.startswith('pay:') else ''
    if key.startswith('pay:') and not login_key.startswith(('account:', 'card:')):
        login_key = ''
    if bw.portal_url_problem(url) or not steps_ or not key.startswith(('account:', 'card:', 'bill:', 'pay:')) or not login_key:
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
    def _front():
        try:
            window.restore()
        except Exception:
            pass
        try:
            window.on_top = True
            window.on_top = False
        except Exception:
            pass
    def _signin(u):
        # item 70 R1: only an https address on the same site as the account's own link
        if not bw.portal_url_problem(u) and same_site(u, url) and MASK not in u:
            window.load_url(u)
    driver = Driver(window, steps_, _read_login(login_key), lambda l: (sys.stdout.write(l + '\n'), sys.stdout.flush()),
                    downloads=None if key.startswith(('bill:', 'pay:')) else _downloads_lister(),   # read or taken there; no file
                    open_url=_go_to, to_front=_front, open_signin=_signin)

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
        try:
            outcome = driver.run()
        except Exception:
            outcome = 'stopped'
        if outcome in SIGN_OUT_AFTER and not driver.cancelled and not (hold and outcome == 'done'):
            driver.sign_out()             # item 70 R5: before closing; never after a bot check or at a payment
        if hold and outcome == 'done' and not driver.cancelled:
            # Item 68 B8 (b): at the bank's payment screen, the window stays for the person - they enter the amount
            # and press Pay. Groundwork has nothing more to do here and never presses it.
            driver._bar(hold, 'ask')
            return
        # Rob: the agent always closes the window when it is finished - whatever the outcome. A short pause first lets
        # the file finish writing and shows the outcome on the bar; Groundwork's page says what happened and why.
        if not driver.cancelled:
            driver._bar('Finished (' + str(outcome).replace('_', ' ') + '). Groundwork is closing this window.')
            driver.sleep(CLOSE_PAUSE)
        try:
            window.destroy()
        except Exception:
            import os
            os._exit(0)
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


def start_fetch(key, url, steps_, device_dir, wait_seconds=20.0, on_finish=None, extra=None):
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
    proc.stdin.write(url + '\n' + key + '\n' + json.dumps(steps_) + '\n' + (device_dir or '') + '\n'
                     + json.dumps(extra or {}) + '\n')
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
    if s == 'read':
        return ('Read the amount due: ' if ev.get('what') == 'amount' else 'Read the due date: ') + str(ev.get('val') or '')
    if s == 'waiting_code':
        return 'Your bank is asking you something (a code, or something to agree to). Answer it in the window; Groundwork carries on after that.'
    if s == 'signed_out':
        return {'pressed': 'Signed out of the bank.', 'already': 'Signed out.',
                'none': "Groundwork couldn't find Sign out; your bank will end the session on its own."}.get(ev.get('found'), '')
    if s == 'stopped' and ev.get('why') == 'page_changed' and i is not None and i < len(steps_):
        # item 70 R2: where the bank was, beside where the step was recorded
        want = steps_[i].get('page')
        got = ev.get('page')
        where = (f" The bank was on {got}, not {want}" + (' - it may have signed you out.' if 'login' in (got or '').lower()
                 or 'signin' in (got or '').lower() else '.')) if got and want and got != want else ''
        return f"Stopped at step {i + 1} ({step_words(steps_[i])}): the page didn't look as recorded.{where} Show Groundwork again from step {i + 1}, or download this one yourself."
    if s == 'stopped':
        return {'page_changed': "Stopped: the page didn't look as recorded" + (f" at step {i + 1}" if i is not None else '') + '. Record the steps again, or download this one yourself.',
                'bot_check': 'Stopped: your bank showed a check for automated access. Groundwork stops there and closed the window.',
                'no_login': 'Stopped: no saved login for this account.',
                'code_timeout': 'Stopped: no code was entered in 5 minutes.',
                'sign_in_failed': "Stopped: signing in didn't get past the login page twice. Check the saved login (Forget, then Save login again).",
                'would_pay': "Stopped: the next step looked like making a payment. Groundwork never pays - that is your click.",
                'cancelled': 'Stopped.'}.get(ev.get('why'), 'Stopped.')
    if s == 'downloaded':
        return f"Downloaded {ev.get('file', '')} to your Downloads folder. It's waiting for you in the import review."
    if s == 'no_download':
        return "The steps ran, but no file arrived in 2 minutes."
    return ''


# ── Item 67 - Get all my accounts (GET_ALL_ACCOUNTS.md G1-G8) ─────────────────
# One press visits each account with saved steps, ONE AT A TIME, in the order given; each window closes as its run
# ends. The user's Stop ends the batch, and so does a bank's bot check (carrying on would look like what banks flag);
# any other stop ends that account's run only. Started by the press alone - nothing here runs on a timer.
_batch = None


def start_batch(items, launch, poll=0.5):
    """items: [{'key', 'name'}] in order. launch(key, batch_id, on_end) -> 'opened' or a reason it didn't open; on_end
    is called once when that account's run ends. 'started' | 'already_running' | 'nothing'."""
    global _batch
    import secrets
    if not items:
        return 'nothing'
    with _lock:
        if _batch and not _batch['done']:
            return 'already_running'
        b = {'id': secrets.token_hex(6), 'stop': None, 'done': False, 'current': None,
             'items': [{'key': i['key'], 'name': i['name'], 'state': 'waiting', 'why': None, 'file': None} for i in items]}
        _batch = b
    threading.Thread(target=run_batch, args=(b, launch, poll), daemon=True).start()
    return 'started'


def run_batch(b, launch, poll=0.5):
    """The batch's body (its thread; called directly by tests)."""
    for it in b['items']:
        if b['stop']:
            it['state'] = 'skipped'
            continue
        ended, box = threading.Event(), {}

        def on_end(key, events, box=box, ended=ended):
            box['events'] = events
            ended.set()
        it['state'], b['current'] = 'running', it['key']
        try:
            r = launch(it['key'], b['id'], on_end)
        except Exception:
            r = 'engine_unavailable'
        if r != 'opened':
            it['state'], it['why'] = 'stopped', r
            continue
        while not ended.wait(poll):
            pass
        _await_closed(it['key'])          # item 70 R5: the window signs out and closes before the next one opens
        end = next((e for e in reversed(box.get('events') or []) if e.get('s') in TERMINAL), {})
        it['state'], it['why'], it['file'] = end.get('s') or 'stopped', end.get('why'), end.get('file')
        it['i'] = end.get('i')
        if it['state'] == 'stopped' and not it['why']:
            it['why'] = 'cancelled'
        if it['why'] == 'bot_check' and not b['stop']:
            b['stop'] = 'bot_check'
    b['current'] = None
    b['done'] = True


def _await_closed(key, timeout=30.0):
    """Wait (bounded) for a fetch window's process to end - signing out happens after its outcome is known."""
    import time
    with _lock:
        f = _fetches.get(key)
    proc = f and f.get('proc')
    if proc is None:
        return
    end = time.monotonic() + timeout
    while proc.poll() is None and time.monotonic() < end:
        time.sleep(0.2)


def stop_batch():
    """The user's Stop: the open window closes, and the accounts not yet visited are skipped."""
    with _lock:
        b = _batch
        if not b or b['done']:
            return False
        b['stop'] = b['stop'] or 'user'
        cur = b['current']
    if cur:
        stop_fetch(cur)
    return True


BATCH_STATES = ('waiting', 'running', 'downloaded', 'no_download', 'done', 'stopped', 'skipped')


def batch_words(it, live=None):
    """One account's line in the progress panel, in words (G4)."""
    s, why = it['state'], it.get('why')
    if s == 'waiting':
        return 'Waiting'
    if s == 'running':
        if live == 'waiting_code':
            return 'Your bank is asking you something - its window is in front. Type it there.'
        if live == 'signed_in':
            return 'Signed in'
        return 'Working on it'
    if s == 'downloaded':
        return f"Downloaded {it.get('file') or 'a file'}"
    if s == 'no_download':
        return 'The steps ran, but no file arrived'
    if s == 'done':
        return 'Read - confirm it on the Budget page' if str(it.get('key', '')).startswith('bill:') else 'Done'
    if s == 'skipped':
        return 'Skipped'
    return {'page_changed': "Stopped: the page didn't look as recorded",
            'bot_check': 'Stopped: your bank showed a check for automated access - the rest were not visited',
            'no_login': 'Stopped: no saved login',
            'no_steps': 'Stopped: no saved steps',
            'code_timeout': 'Stopped: no code was entered in 5 minutes',
            'sign_in_failed': "Stopped: signing in didn't get past the login page",
            'already_open': 'Stopped: a window for this account was already open',
            'would_pay': 'Stopped: the next step looked like making a payment - Groundwork never pays',
            'refused_url': "Stopped: the bank link isn't an https address",
            'engine_unavailable': "Stopped: the window couldn't open",
            'cancelled': 'Stopped'}.get(why, 'Stopped')


def batch_state():
    """The batch as the panel shows it: each account's state and words; the open account's live state included."""
    with _lock:
        b = _batch
        if not b:
            return None
        items = [dict(i) for i in b['items']]
        cur, stop, done, bid = b['current'], b['stop'], b['done'], b['id']
    for it in items:
        live = None
        if it['state'] == 'running' and it['key'] == cur:
            evs = fetch_events(cur)
            live = evs[-1]['s'] if evs else None
        it['live'] = live
        so = next((e.get('found') for e in reversed(fetch_events(it['key'])) if e.get('s') == 'signed_out'), None) \
            if it['state'] not in ('waiting', 'running') else None
        it['signed_out'] = so
        it['words'] = batch_words(it, live) + ({'pressed': ' \u00b7 signed out', 'already': ' \u00b7 signed out',
                                                'none': " \u00b7 couldn't find Sign out"}.get(so, ''))
    return {'id': bid, 'items': items, 'stop': stop, 'done': done}


def reset_batch_for_test():
    global _batch
    with _lock:
        _batch = None


# ── Item 68 - reading a bill's figures (BILLS_AND_PAYING.md B3) ─────────────────
_MONTHS = {m: n for n, m in enumerate(('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'), 1)}


def parse_amount(text):
    """'$1,142.37' -> 1142.37, or None. Only a dollar amount with cents, as a bill shows it."""
    m = re.search(r'\$\s?(\d[\d,]*\.\d{2})\b', str(text or ''))
    if not m:
        return None
    try:
        return round(float(m.group(1).replace(',', '')), 2)
    except ValueError:
        return None


def parse_due(text, today=None):
    """A due date as a bill shows it -> a date, or None. 10/24/2026, 2026-10-24, Oct 24, 2026, October 24 (the next
    Oct 24 on or after 60 days ago - a bill's due date is near). Anything else is None: named, never guessed."""
    from datetime import date, timedelta
    s = str(text or '').strip()
    today = today or date.today()
    try:
        m = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})', s)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', s)
        if m:
            y = int(m.group(3))
            return date(y + 2000 if y < 100 else y, int(m.group(1)), int(m.group(2)))
        m = re.fullmatch(r'([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})(?:,?\s+(\d{4}))?', s)
        if m and m.group(1).lower() in _MONTHS:
            mo, d = _MONTHS[m.group(1).lower()], int(m.group(2))
            if m.group(3):
                return date(int(m.group(3)), mo, d)
            for y in (today.year - 1, today.year, today.year + 1):
                cand = date(y, mo, d)
                if cand >= today - timedelta(days=60):
                    return cand
    except ValueError:
        return None
    return None

