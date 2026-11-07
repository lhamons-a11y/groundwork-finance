"""
The bank window - an untrusted webpage viewer, not a Groundwork integration surface.

`gw 2.0/BANK_BROWSER.md`, ruled 2026-09-23 (s7). Groundwork supplies only the user-entered
HTTPS URL, receives no page state, performs no interaction, retains no session, and receives
financial data only when the user independently downloads a file into the existing review path.

Three things live here, and this module imports nothing but the standard library at module
level so that the child process below cannot reach Groundwork even by accident:

  portal_url_problem()   F4 - the syntactic link check, run on save AND at launch
  downloads_dir()        F6 - the one Downloads folder, shared by the watcher and the copy
  child_main()           F1 - the bank process: URL on stdin -> a WebView -> the filesystem
  open_bank_window()     F1/F2 - the parent side: one child per account, tracked, terminated

The child is Groundwork's own executable started with --bank-window (launch.py dispatches it
before anything else starts). It is given the URL on stdin and nothing else. It never imports
server, core, the database, the session token or GroundworkAPI, never sets js_api, and never
calls evaluate_js / run_js / get_elements / get_cookies / load_html / load_url. s126 checks all
of that against this file's source, and fails if any of it changes.
"""

import os
import sys
import threading
from pathlib import Path


# ── F4: what a link may be ─────────────────────────────────────────────────────
# Syntactic only. Groundwork does not resolve the host and makes no claim about where it
# points or whom it belongs to (s7): the page can navigate anywhere once loaded, so a check on
# the first URL could never bound the window - F12, on the server, is what protects Groundwork.

_REFUSED_HOST_SUFFIXES = ('.localhost', '.local', '.internal', '.lan', '.home.arpa')


# launch.py sets this in the program that has a window: url -> the person's Yes. None: no window to ask in.
ASK_PERSON = None


def portal_url_problem(url):
    """Why this link may not be stored or opened, or None if it may.

    https only; no userinfo; no explicit port (:443 is tolerated and dropped by
    normalise_portal_url); a DNS name, never an IP literal, never a loopback or
    local-network name, never a single label.
    """
    from urllib.parse import urlsplit
    import ipaddress

    if not isinstance(url, str) or not url.strip():
        return 'The address is empty.'
    url = url.strip()
    if any(c.isspace() for c in url) or any(ord(c) < 32 for c in url):
        return 'The address contains spaces or control characters.'
    try:
        parts = urlsplit(url)
        port = parts.port          # raises ValueError on a malformed port
    except ValueError:
        return 'The address is not a valid web address.'
    if parts.scheme.lower() != 'https':
        return 'Only https:// addresses can be opened.'
    if parts.username is not None or parts.password is not None or '@' in parts.netloc:
        return 'The address may not contain a user name or password.'
    if port is not None and port != 443:
        return 'The address may not name a port.'
    host = (parts.hostname or '').rstrip('.').lower()
    if not host:
        return 'The address has no host name.'
    try:
        ipaddress.ip_address(host)
        return 'The address must be a name, not a numeric IP address.'
    except ValueError:
        pass
    if host == 'localhost' or host.endswith(_REFUSED_HOST_SUFFIXES):
        return 'The address points at this computer or the local network.'
    if '.' not in host:
        return 'The address must be a full web address, like https://www.yourbank.com.'
    return None


def normalise_portal_url(url):
    """The link as stored: trimmed, and an explicit :443 dropped. Nothing else is rewritten."""
    from urllib.parse import urlsplit, urlunsplit
    url = url.strip()
    parts = urlsplit(url)
    if parts.port == 443:
        host = parts.hostname or ''
        url = urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
    return url


def window_title(url):
    """The window's title, from its address alone - nothing else crosses into this process.
    The trip planner's Google Flights search (item 42) opens in this same separate window."""
    from urllib.parse import urlsplit
    parts = urlsplit(url)
    if (parts.hostname or '').lower() == 'www.google.com' and parts.path.startswith('/travel/flights'):
        return 'Google Flights'
    if (parts.hostname or '').lower() == 'www.google.com' and parts.path.startswith(('/travel/search', '/travel/hotels')):
        return 'Google Hotels'      # item 59 P3 (it read "Bank website - www.google.com" before)
    return f'Bank website - {portal_host(url)}'


def keep_new_windows_in_engine(platform_key):
    """Google Flights only (item 42; Rob 2026-10-08: "when I am clicking continue in google flights another window is
    opening and i am getting a 404 error"). Continue posts a form into a new window (/travel/clk/f, target=_blank).
    pywebview hands every new window to the system browser by its address alone, so the form is lost and Google
    answers 404. Left unhandled, WebView2 opens the page's own window in this same private process and the form
    arrives (measured 2026-10-08: unhandled, the POST and its fields reached the server; handed over, a bare GET).
    It changes where the page's own window opens, nothing more. Windows only: the other engines do not use this
    handler. A bank window is untouched."""
    if platform_key != 'win32':
        return False
    try:
        from webview.platforms import edgechromium
    except Exception:
        return False

    def on_new_window_request(self, sender, args):
        return          # unhandled: WebView2 opens the window the page asked for, with what the page sent

    edgechromium.EdgeChrome.on_new_window_request = on_new_window_request
    return True


def portal_host(url):
    from urllib.parse import urlsplit
    return (urlsplit(url).hostname or '').lower()


# ── F6: the one Downloads folder ───────────────────────────────────────────────
# pywebview's Save dialog starts in the platform's own Downloads folder - on Windows the
# known-folder registry value, on Linux the XDG user dir - which is NOT Path.home()/'Downloads'
# when the user has moved it or runs a localised desktop. The watcher and the copy both ask
# here, so "where the dialog saves" and "where Groundwork looks" are one concept, not two.

_WIN_DOWNLOADS_GUID = '{374DE290-123F-4565-9164-39C4925E467B}'


def downloads_dir():
    """The platform's Downloads folder, resolved the way the WebView's Save dialog resolves it."""
    home = Path.home()
    if sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders',
            ) as key:
                value = winreg.QueryValueEx(key, _WIN_DOWNLOADS_GUID)[0]
            if value:
                return Path(os.path.expandvars(value))
        except OSError:
            pass
        return home / 'Downloads'
    if sys.platform == 'darwin':
        return home / 'Downloads'          # NSDownloadsDirectory is always ~/Downloads
    return _xdg_download_dir(home)


def _xdg_download_dir(home):
    """XDG_DOWNLOAD_DIR from user-dirs.dirs, the file GLib's get_user_special_dir reads."""
    config = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    try:
        for line in (config / 'user-dirs.dirs').read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line.startswith('XDG_DOWNLOAD_DIR='):
                continue
            value = line.split('=', 1)[1].strip().strip('"')
            value = value.replace('$HOME', str(home))
            if value and value != str(home):
                return Path(value)
    except OSError:
        pass
    return home / 'Downloads'


# ── F1 / F13: the bank process ─────────────────────────────────────────────────
# One supported engine per OS, pinned by name; the renderer actually obtained is checked
# before any page loads. pywebview would otherwise fall back to MSHTML (IE11) on Windows
# when WebView2 is absent. Groundwork never ships, pins, downloads or updates an engine.

_PINNED_GUI = {'win32': 'edgechromium', 'darwin': 'cocoa', 'linux': 'gtk'}
_EXPECTED_RENDERER = {'win32': 'edgechromium', 'darwin': 'wkwebview', 'linux': 'gtkwebkit2'}

# The only lines the child ever writes to its stdout, and the only ones the parent reads.
# Fixed literals: nothing from the page, the URL or the file system can ever appear here.
STATUS_READY = 'ready'
STATUS_REFUSED_URL = 'refused-url'
STATUS_REFUSED_ENGINE = 'refused-engine'
_STATUSES = (STATUS_READY, STATUS_REFUSED_URL, STATUS_REFUSED_ENGINE)


def _platform_key():
    if sys.platform.startswith('linux'):
        return 'linux'
    return sys.platform


def _say(status):
    sys.stdout.write(status + '\n')
    sys.stdout.flush()


def child_main():
    """The bank process. URL in on stdin -> bank WebView -> user -> user-chosen download -> disk."""
    url = sys.stdin.readline().strip()
    if portal_url_problem(url):
        _say(STATUS_REFUSED_URL)
        return 2

    platform_key = _platform_key()
    import webview
    from webview.guilib import initialize
    try:
        lib = initialize(_PINNED_GUI.get(platform_key))
        renderer = getattr(lib, 'renderer', None)
    except Exception:
        renderer = None
    if renderer != _EXPECTED_RENDERER.get(platform_key):
        _say(STATUS_REFUSED_ENGINE)
        return 3

    # Downloads here and only here: the main process keeps ALLOW_DOWNLOADS False.
    webview.settings['ALLOW_DOWNLOADS'] = True
    flights = window_title(url) == 'Google Flights'
    if flights:
        keep_new_windows_in_engine(platform_key)
    hotels = window_title(url) == 'Google Hotels'

    if flights:
        # Item 44 (FLIGHT_FARE_READ.md): the one page read, Google Flights only. It all lives in flights_window.py,
        # so this file still reads nothing from any page.
        import flights_window
        window = flights_window.create_window(webview, url, window_title(url))
    elif hotels:
        # Item 59 P3: Google Hotels' one page read lives in hotels_window.py, as Google Flights' does in flights_window.
        import hotels_window
        window = hotels_window.create_window(webview, url, window_title(url))
    else:
        window = webview.create_window(
            title=window_title(url),
            url=url,
            width=1100,
            height=800,
        )

    def _close_when_parent_goes():
        # The parent holds our stdin open for as long as it wants this window. EOF means it
        # closed us or it is gone; either way the window goes too. This acts on the window,
        # never on the page.
        try:
            sys.stdin.read()
        except Exception:
            pass
        try:
            window.destroy()
        except Exception:
            os._exit(0)

    threading.Thread(target=_close_when_parent_goes, daemon=True).start()
    _say(STATUS_READY)
    webview.start(gui=_PINNED_GUI.get(platform_key), private_mode=True)
    return 0


# ── F1 / F2: the parent side ───────────────────────────────────────────────────

_children = {}          # (kind, id) -> Popen
_children_lock = threading.Lock()


def _child_command():
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--bank-window']
    launcher = Path(__file__).resolve().parent / 'launch.py'
    return [sys.executable, str(launcher), '--bank-window']


def _alive(proc):
    return proc is not None and proc.poll() is None


def process(key):
    """The running window process for `key`, or None."""
    with _children_lock:
        proc = _children.get(key)
    return proc if _alive(proc) else None


def is_open(key):
    with _children_lock:
        return _alive(_children.get(key))


def open_bank_window(key, url, wait_seconds=20.0):
    """Start the bank process for `key` with `url`. Returns one of:
    'opened', 'already_open', 'refused_url', 'engine_unavailable'."""
    import subprocess

    if portal_url_problem(url):
        return 'refused_url'
    with _children_lock:
        if _alive(_children.get(key)):
            return 'already_open'
        flags = 0x08000000 if sys.platform == 'win32' else 0     # CREATE_NO_WINDOW
        proc = subprocess.Popen(
            _child_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, creationflags=flags,
        )
        proc.stdin.write(url + '\n')
        proc.stdin.flush()
        _children[key] = proc
        if sys.platform == 'win32':
            # Windows keeps a background process from taking focus, so without
            # this the bank window opens BEHIND Groundwork and the user has to
            # go looking for it. The click that asked for it came to us, so we
            # pass the right to come forward on to the bank process.
            try:
                import ctypes
                ctypes.windll.user32.AllowSetForegroundWindow(proc.pid)
            except Exception:
                pass

    status = _read_status(proc, wait_seconds)
    if status == STATUS_READY:
        return 'opened'
    close_bank_window(key)
    return 'refused_url' if status == STATUS_REFUSED_URL else 'engine_unavailable'


def _read_status(proc, wait_seconds):
    box = []
    reader = threading.Thread(target=lambda: box.append(proc.stdout.readline().strip()), daemon=True)
    reader.start()
    reader.join(wait_seconds)
    line = box[0] if box else ''
    return line if line in _STATUSES else None


def close_bank_window(key):
    with _children_lock:
        proc = _children.pop(key, None)
    _stop(proc)


def close_all_bank_windows():
    with _children_lock:
        procs = list(_children.values())
        _children.clear()
    for proc in procs:
        _stop(proc)


def _stop(proc):
    if proc is None:
        return
    try:
        proc.stdin.close()         # the child's EOF watcher closes its window
    except Exception:
        pass
    try:
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass


def open_in_browser(url):
    """The escape hatch (F10): the same link, the same F4 check, the user's own browser."""
    import webbrowser
    if portal_url_problem(url):
        return 'refused_url'
    webbrowser.open(url)
    return 'opened'
