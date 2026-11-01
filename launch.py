"""
Groundwork — Cross-platform launcher
"""

import sys
import os
import re
# Before anything can import numpy: OpenBLAS reserves memory per processor thread (620 MB measured on 20 threads) and
# Groundwork does no numpy maths. See core/engine.py (the 8 GB floor, ENGINE_REPLACEMENT.md s9).
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import threading
import time
import logging
from pathlib import Path


def _get_base_dir():
    """
    Return the directory containing our app files.
    - When frozen by PyInstaller: sys._MEIPASS (the temp bundle dir)
    - When running from source: the directory containing launch.py
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.resolve()


# AppleScript literals need escaped backslashes and quotes. chr(92) is a
# backslash - written this way so the escaping is readable rather than a wall
# of doubled slashes.
_BS = chr(92)


def _applescript_str(s):
    """Quote a Python string as an AppleScript literal, newlines included.

    AppleScript has no backslash-n escape, so multi-line text has to be joined
    with `return` between one literal per line.
    """
    def lit(x):
        return '"' + x.replace(_BS, _BS + _BS).replace('"', _BS + '"') + '"'
    return ' & return & '.join(lit(line) for line in s.splitlines() or [''])


def _show_error_dialog(title, msg):
    """Show a native error box using nothing but the standard library.

    This runs when startup has already failed - sometimes *because* an import
    failed - so it must not depend on anything that could be the broken thing.
    tkinter was the previous answer, and it cost roughly 8MB of tcl/tk in every
    bundle to draw three dialogs. ctypes and osascript cost nothing and are
    always present on their platforms.

    stderr always gets the message. The dialog is a bonus for a user who
    double-clicked an icon and has no console to read.
    """
    print(msg, file=sys.stderr)
    try:
        if sys.platform == 'win32':
            import ctypes
            MB_OK, MB_ICONERROR, MB_SETFOREGROUND = 0x0, 0x10, 0x10000
            ctypes.windll.user32.MessageBoxW(
                None, str(msg), str(title), MB_OK | MB_ICONERROR | MB_SETFOREGROUND)
        elif sys.platform == 'darwin':
            import subprocess
            subprocess.run(
                ['osascript', '-e',
                 'display dialog %s with title %s buttons {"OK"} '
                 'default button "OK" with icon stop'
                 % (_applescript_str(msg), _applescript_str(title))],
                check=False, timeout=300)
        else:
            import shutil
            import subprocess
            for tool, args in (
                ('zenity', ['--error', '--title', title, '--text', msg]),
                ('kdialog', ['--error', msg, '--title', title]),
            ):
                if shutil.which(tool):
                    subprocess.run([tool] + args, check=False, timeout=300)
                    break
    except Exception:
        pass    # stderr already carries it; never fail inside the failure path


def _folder_dialog_type():
    """FOLDER_DIALOG is deprecated in pywebview 6, and FileDialog.FOLDER does
    not exist in the 4.4 minimum this project declares. Accept either."""
    import webview
    fd = getattr(webview, 'FileDialog', None)
    if fd is not None and hasattr(fd, 'FOLDER'):
        return fd.FOLDER
    return webview.FOLDER_DIALOG



def _check_dependencies():
    errors = []
    try:
        import webview  # noqa
    except ImportError:
        errors.append("pywebview is not installed.\n  Fix: pip install pywebview")

    if errors:
        msg = "Groundwork cannot start:\n\n" + "\n\n".join(errors)
        print(msg, file=sys.stderr)
        _show_error_dialog("Groundwork - Missing dependencies", msg)
        sys.exit(1)


def _use_bundled_certificates():
    """Point HTTPS at the certificate list shipped in the app (Mac check 2026-10-31, issue 6).

    A frozen Python cannot find the Mac's own list, so every check failed with CERTIFICATE_VERIFY_FAILED - the update
    check, airfare, geocoding, prices - from at least 20 October. Setting SSL_CERT_FILE before anything opens a
    connection makes every ssl.create_default_context(), and so every urlopen, load certifi's list. Verification
    stays on; nothing falls back to an unchecked connection.
    """
    if os.environ.get('SSL_CERT_FILE'):
        return
    try:
        import certifi
        os.environ['SSL_CERT_FILE'] = certifi.where()
    except ImportError:
        logging.warning('certifi is not in this build - HTTPS checks will fail')


def _wait_for_flask(host='127.0.0.1', port=8765, timeout=30):
    """
    Confirms Groundwork's own Flask server is actually answering — not just
    that something is listening on the port. A bare TCP connect (the old
    check) succeeds instantly against a stale/zombie process left over from
    a previous crash, or any other app that happens to hold this port; the
    real Flask thread then fails in the background with "address already in
    use" while the webview opens against dead code, with no error ever
    surfaced. Hitting /api/health confirms it's genuinely our server.
    """
    import urllib.request
    import urllib.error
    deadline = time.time() + timeout
    url = f'http://{host}:{port}/api/health'
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.2)
    return False


def _flash_taskbar(w):
    """Windows only: flash the main window's taskbar button until it is clicked, if it could not take the front."""
    try:
        import ctypes
        from ctypes import wintypes
        hwnd = int(w.native.Handle.ToInt64())

        class FLASHWINFO(ctypes.Structure):
            _fields_ = [('cbSize', wintypes.UINT), ('hwnd', wintypes.HWND), ('dwFlags', wintypes.DWORD),
                        ('uCount', wintypes.UINT), ('dwTimeout', wintypes.DWORD)]
        if ctypes.windll.user32.GetForegroundWindow() == hwnd:
            return
        FLASHW_ALL, FLASHW_TIMERNOFG = 0x3, 0xC
        info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, FLASHW_ALL | FLASHW_TIMERNOFG, 0, 0)
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
    except Exception as e:
        logging.info('flash_taskbar: %s', e)


class GroundworkAPI:
    def open_external(self, url: str):
        # Item 104: a crisis or help line's "Call" / "Text" button is tel: or sms: with digits only - the Mac hands it
        # to FaceTime or Messages (an iPhone nearby places it); nothing else but a web link opens
        if not url or not (url.startswith(('http://', 'https://')) or re.fullmatch(r'(?:tel|sms):\d{3,11}', url)):
            return
        try:
            if sys.platform == 'win32':
                os.startfile(url)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.run(['open', url], check=False)
            else:
                import subprocess
                subprocess.run(['xdg-open', url], check=False)
        except Exception as e:
            logging.warning('open_external failed: %s', e)

    def bring_to_front(self):
        """Item 19 choice 5 (BANK_BROWSER.md section 9; Rob 2026-10-19: "B, user may also need to download another
        file"): when an import offer appears, Groundwork's main window comes forward over the bank window. The bank
        window stays open for the next download (savings, a card...), and nothing is sent to it. Where the system
        will not let a window take the front (Windows can refuse), the taskbar button flashes instead."""
        try:
            import webview
            windows = getattr(webview, 'windows', None) or []
            if not windows:
                return False
            w = windows[0]
            try:
                w.restore()                             # un-minimise; harmless when it isn't
            except Exception:
                pass
            w.show()
            w.on_top = True                             # raise over the bank window...
            w.on_top = False                            # ...without staying on top of everything after
            if sys.platform == 'win32':
                _flash_taskbar(w)
            return True
        except Exception as e:
            logging.warning('bring_to_front failed: %s', e)
            return False

    def pick_folder(self):
        """Folder picker via pywebview, the window layer the app already has.

        Previously tkinter, which meant shipping tcl/tk in every bundle to draw
        one dialog. pywebview is already present - it draws the whole UI.
        """
        try:
            import webview
            windows = getattr(webview, 'windows', None) or []
            if not windows:
                logging.warning('pick_folder: no webview window available')
                return None
            result = windows[0].create_file_dialog(_folder_dialog_type())
            if not result:
                return None
            return result[0] if isinstance(result, (list, tuple)) else str(result)
        except Exception as e:
            logging.warning('pick_folder failed: %s', e)
            return None


# ── Downloads folder watcher (auto-import) ────────────────────────────────────
# Watches the Downloads folder for bank files (.qfx/.ofx/.qbo/.qif/.csv) and
# statements (.pdf) and posts them to Flask's /api/auto-import/queue; the
# frontend polls /pending and OFFERS each one - nothing is previewed, parsed,
# extracted or sent to a model until the user says yes (BANK_BROWSER.md F7):
#   noticed -> offered -> chosen -> staged (the existing review) -> committed.
# A PDF is noticed by name only: its bytes are not read here at all.
# "The Downloads folder" is bank_window.downloads_dir(), the folder the bank
# window's Save dialog starts in (F6) - not Path.home()/'Downloads', which is a
# different folder when the user has moved it or runs a localised desktop. We watch RENAME (moved) events, not create: browsers download to a
# temp name (.crdownload/.part) and rename on completion, so the moved event
# fires exactly once, when the file is whole. Files Groundwork itself writes
# to Downloads (groundwork_export_*) are skipped.

_IMPORT_EXTENSIONS = {'.qfx', '.ofx', '.qbo', '.qif', '.csv'}
_STATEMENT_EXTENSIONS = {'.pdf'}
_MAX_IMPORT_BYTES  = 5 * 1024 * 1024  # 5MB — bank files are far smaller
_MAX_STATEMENT_BYTES = 25 * 1024 * 1024


def _queue_import_file(path: Path, seen: dict):
    name = path.name
    if name.lower().startswith('groundwork'):
        return  # our own export/backup — not a bank download
    suffix = path.suffix.lower()
    if suffix not in _IMPORT_EXTENSIONS and suffix not in _STATEMENT_EXTENSIONS:
        return  # everything else is ignored, never offered
    try:
        stat = path.stat()
    except OSError:
        return
    if seen.get(name) == stat.st_mtime_ns:
        return  # already queued this exact file version
    if suffix in _STATEMENT_EXTENSIONS:
        if 0 < stat.st_size <= _MAX_STATEMENT_BYTES:
            _post_queue_item({'filename': name, 'path': str(path), 'kind': 'statement'})
            seen[name] = stat.st_mtime_ns
        return
    if stat.st_size > _MAX_IMPORT_BYTES or stat.st_size == 0:
        return
    try:
        raw = path.read_bytes()
    except OSError as e:
        logging.warning('auto-import: could not read %s: %s', name, e)
        return
    # Bank exports are often Windows-1252/Latin-1 (curly quotes, accented
    # merchant names), not UTF-8. Try the two most likely encodings before
    # falling back to lossy replacement — errors='replace' as the FIRST
    # attempt would silently substitute U+FFFD for perfectly valid cp1252
    # bytes instead of decoding them correctly.
    try:
        content = raw.decode('utf-8')
    except UnicodeDecodeError:
        try:
            content = raw.decode('cp1252')
        except UnicodeDecodeError:
            content = raw.decode('utf-8', errors='replace')
            logging.warning('auto-import: %s has an unrecognized encoding — some characters may be corrupted', name)

    import hashlib
    # The hash of the RAW bytes on disk (H1), not of the decoded text the page
    # rebuilds a File from - only the raw bytes identify what was downloaded.
    sha256 = hashlib.sha256(raw).hexdigest()
    if _post_queue_item({'filename': name, 'content': content, 'path': str(path), 'sha256': sha256}):
        seen[name] = stat.st_mtime_ns


def _post_queue_item(item):
    """POST one noticed file to the queue. True if it was accepted."""
    name = item.get('filename', '')
    try:
        import json as _json
        import urllib.request
        import server as _server  # same process — share the session token
        req = urllib.request.Request(
            'http://127.0.0.1:8765/api/auto-import/queue',
            data=_json.dumps(item).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'X-GW-Token':   _server._GW_TOKEN,
            },
            method='POST',
        )
        urllib.request.urlopen(req, timeout=5)
        logging.info('auto-import: queued %s', name)
        return True
    except Exception as e:
        logging.warning('auto-import: queue failed for %s: %s', name, e)
        return False


def _start_downloads_watcher():
    """Start the watchdog observer. Silently unavailable if watchdog missing."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        logging.info('auto-import: watchdog not installed — watcher disabled')
        return None

    from bank_window import downloads_dir
    downloads = downloads_dir()
    if not downloads.is_dir():
        logging.info('auto-import: no Downloads folder found — watcher disabled')
        return None
    # Read the folder once before watching it (Mac check 2026-10-31, issue 1). On macOS a build with a new signature
    # is asked again for Downloads, and the watch call waits for that answer holding Python's lock, so every thread in
    # the app stopped with it. os.listdir lets go of the lock while it waits, and a refusal is an answer, not a hang.
    try:
        os.listdir(downloads)
    except OSError as e:
        logging.info('auto-import: Downloads cannot be read (%s) — watcher disabled', e)
        return None

    seen = {}

    class _Handler(FileSystemEventHandler):
        def on_moved(self, event):
            # Browser finished a download: temp name → final name
            if not event.is_directory:
                _queue_import_file(Path(event.dest_path), seen)

    observer = Observer()
    observer.schedule(_Handler(), str(downloads), recursive=False)
    observer.daemon = True
    observer.start()
    logging.info('auto-import: watching %s', downloads)
    return observer


def _start_engine():
    """Load the local AI model if the user's AI setting is on (ENGINE_REPLACEMENT.md R-a).

    The engine runs inside this process (core/engine.py): no separate AI program, no second process, no port. Loading happens on
    the engine's own background thread after the CPU check and the model's SHA-256 check, so the window never waits
    for it. With AI off nothing is loaded at all - not even the runtime library.
    """
    try:
        import server
        server.engine_launch()
    except Exception:
        logging.exception('local AI engine did not start (AI will be unavailable; everything else works)')


def _stop_engine():
    """Release the model when Groundwork closes (R-a) - explicitly, not left to process teardown."""
    try:
        from core import engine
        engine.stop()
    except Exception:
        logging.exception('local AI engine did not stop cleanly')


def _tighten_data_files():
    """The database, its backups and the logs, readable by this user only (Mac check 2026-10-31, issue 12).

    main() sets the umask, so what Groundwork writes from now on is made that way; this catches what an earlier
    build left at 644. The data folder itself was already 700. Not encryption: FileVault is what protects the disk.
    """
    if os.name != 'posix':
        return
    try:
        from core.database import DATA_DIR
        for f in [*DATA_DIR.glob('*'), *DATA_DIR.glob('backups/*')]:
            if f.is_file() and f.stat().st_mode & 0o077:
                f.chmod(0o600)
    except OSError as e:
        logging.warning('could not tighten the data files: %s', e)


def _start_server(base_dir: Path):
    try:
        # ── Path setup ────────────────────────────────────────────────────────
        # Add base_dir to sys.path so server.py and core/ are importable
        base_str = str(base_dir)
        if base_str not in sys.path:
            sys.path.insert(0, base_str)

        # Also add core/ explicitly so 'from core.database import ...' works
        core_str = str(base_dir / 'core')
        if core_str not in sys.path:
            sys.path.insert(0, core_str)

        static_folder = str(base_dir / 'static')

        # ── Import and start Flask ────────────────────────────────────────────
        from server import create_app, serve
        flask_app = create_app(static_folder=static_folder)
        _tighten_data_files()
        logging.getLogger('werkzeug').setLevel(logging.WARNING)

        # One serving path for every entry point (server.serve). The packaged
        # app used to run Flask's development server, which is what made a
        # loopback request cost 250ms as often as 45ms.
        serve(flask_app, host='127.0.0.1', port=8765)

    except Exception as e:
        # Log the real error so we can diagnose it
        logging.exception('Flask failed to start: %s', e)
        # Write to a log file in the user's data dir so we can read it
        try:
            import traceback
            log_dir = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Groundwork'
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_dir / 'startup_error.log', 'w') as f:
                f.write(f"Flask startup error:\n{traceback.format_exc()}\n")
                f.write(f"\nsys.path: {sys.path}\n")
                f.write(f"base_dir: {base_dir}\n")
                f.write(f"base_dir exists: {base_dir.exists()}\n")
                f.write(f"static exists: {(base_dir / 'static').exists()}\n")
                f.write(f"server.py exists: {(base_dir / 'server.py').exists()}\n")
        except Exception:
            pass


MAIN_PAGE = 'http://127.0.0.1:8765/'


def microphone_answer(kind_is_microphone, uri, allowed_at):
    """Whether the window answers a permission request itself: only the microphone, only for Groundwork's own page,
    and only once the person's yes is on record (server.MICROPHONE_SETTING). Anything else is left to the window's own
    question. Kept apart from the window code so s272 can hold it without a window."""
    return bool(kind_is_microphone and str(uri or '').startswith(MAIN_PAGE) and allowed_at)


def _keep_microphone_answer(window):
    """Rob 2026-10-31: the microphone's yes is recorded and kept. The window opens private (pywebview's default), so
    WebView2 forgets its own answer when Groundwork closes; the yes the page recorded answers the next request instead.
    Windows (WebView2) only - elsewhere the window asks as it always has. Any failure leaves the question as it was."""
    if sys.platform != 'win32':
        return
    hooked = []

    def on_loaded(*_):
        if hooked:
            return
        try:
            from System import Func, Type
            from Microsoft.Web.WebView2.Core import CoreWebView2PermissionKind, CoreWebView2PermissionState
            form = window.native
            core = form.browser.webview.CoreWebView2

            def on_permission(_sender, args):
                try:
                    from server import microphone_allowed
                    if microphone_answer(args.PermissionKind == CoreWebView2PermissionKind.Microphone, args.Uri,
                                         microphone_allowed()):
                        args.State = CoreWebView2PermissionState.Allow
                except Exception:
                    logging.exception('microphone answer')       # the window's own question still shows

            def add():
                core.PermissionRequested += on_permission

            form.Invoke(Func[Type](add))
            hooked.append(True)
        except Exception:
            logging.exception('could not keep the microphone answer')

    window.events.loaded += on_loaded


def main():
    # The bank window (BANK_BROWSER.md F1) is this same executable started with
    # --bank-window. It is dispatched before ANYTHING else - no Flask, no
    # watcher, no AI engine, no database, no token - so a bank process can never
    # become a second Groundwork. It takes the URL on stdin and nothing else.
    if '--bank-window' in sys.argv[1:]:
        from bank_window import child_main
        sys.exit(child_main())
    # The bank agent's window (BANK_AGENT.md, item 57): the same kind of process, dispatched just as early, with its
    # mode on the command line and the account's link on stdin. Everything it may do to a page is in bank_agent_window.py.
    # The engine's fitting test (GPU_ENGINE.md G3, item 95): one device, in its own process, so a graphics driver
    # that crashes ends only that test. Dispatched as early as the bank windows: no Flask, no window, no database.
    if '--engine-probe' in sys.argv[1:]:
        from core.engine_fit import probe_main
        sys.exit(probe_main(sys.argv[sys.argv.index('--engine-probe') + 1:]))
    if '--bank-agent' in sys.argv[1:]:
        from bank_agent_window import child_main as agent_main
        args = sys.argv[sys.argv.index('--bank-agent') + 1:]
        sys.exit(agent_main(args[0] if args else ''))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    _check_dependencies()
    if os.name == 'posix':
        os.umask(0o077)             # issue 12: every file Groundwork writes is this user's alone
    _use_bundled_certificates()

    import webview

    base_dir = _get_base_dir()

    # Start Flask
    server_thread = threading.Thread(
        target=_start_server,
        args=(base_dir,),
        daemon=True,
        name='groundwork-flask',
    )
    server_thread.start()

    # Wait for Flask to be ready
    flask_ready = _wait_for_flask(timeout=30)

    if not flask_ready:
        # Read the error log if it was written
        error_detail = ''
        try:
            log_path = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Groundwork' / 'startup_error.log'
            if log_path.exists():
                error_detail = '\n\nError details:\n' + log_path.read_text()[:800]
        except Exception:
            pass

        _show_error_dialog(
            "Groundwork - Startup Error",
            "Groundwork's server did not start.\n\n"
            "A log file has been written to:\n"
            r"%LOCALAPPDATA%\Groundwork\startup_error.log"
            "\n\nPlease send that file to support@groundworkfinance.app"
            + error_detail)
        sys.exit(1)

    _start_engine()

    api    = GroundworkAPI()

    import server as _server
    window = webview.create_window(
        title='Groundwork',
        # The page key opens the page once and is traded for a cookie only this window holds (issue 2).
        url=f'http://127.0.0.1:8765/?k={_server._GW_PAGE_KEY}',
        js_api=api,
        width=1280,
        height=820,
        min_size=(900, 600),
    )

    _keep_microphone_answer(window)

    # Groundwork exiting closes every bank window it opened (F2).
    import atexit
    from bank_window import close_all_bank_windows
    atexit.register(close_all_bank_windows)

    # The Downloads auto-import watcher starts once the window is up, on its own thread: a macOS permission
    # question about Downloads must never stand between the user and the window (issue 1).
    def _watch_after_shown():
        window.events.shown.wait(30)
        _start_downloads_watcher()
    threading.Thread(target=_watch_after_shown, daemon=True, name='groundwork-downloads').start()

    webview.start(debug=False)
    _stop_engine()


if __name__ == '__main__':
    main()
