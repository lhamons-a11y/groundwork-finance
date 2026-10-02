"""
Groundwork — Cross-platform launcher
"""

import sys
import os
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


class GroundworkAPI:
    def open_external(self, url: str):
        if not url or not url.startswith(('http://', 'https://')):
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
# Watches ~/Downloads for bank files (.qfx/.ofx/.qbo/.qif/.csv) and posts them
# to Flask's /api/auto-import/queue; the frontend polls /pending and offers to
# import. We watch RENAME (moved) events, not create: browsers download to a
# temp name (.crdownload/.part) and rename on completion, so the moved event
# fires exactly once, when the file is whole. Files Groundwork itself writes
# to Downloads (groundwork_export_*) are skipped.

_IMPORT_EXTENSIONS = {'.qfx', '.ofx', '.qbo', '.qif', '.csv'}
_MAX_IMPORT_BYTES  = 5 * 1024 * 1024  # 5MB — bank files are far smaller


def _queue_import_file(path: Path, seen: dict):
    name = path.name
    if name.lower().startswith('groundwork'):
        return  # our own export/backup — not a bank download
    if path.suffix.lower() not in _IMPORT_EXTENSIONS:
        return
    try:
        stat = path.stat()
    except OSError:
        return
    if seen.get(name) == stat.st_mtime_ns:
        return  # already queued this exact file version
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

    try:
        import json as _json
        import urllib.request
        import server as _server  # same process — share the session token
        req = urllib.request.Request(
            'http://127.0.0.1:8765/api/auto-import/queue',
            data=_json.dumps({
                'filename': name,
                'content':  content,
                'path':     str(path),
            }).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'X-GW-Token':   _server._GW_TOKEN,
            },
            method='POST',
        )
        urllib.request.urlopen(req, timeout=5)
        seen[name] = stat.st_mtime_ns
        logging.info('auto-import: queued %s', name)
    except Exception as e:
        logging.warning('auto-import: queue failed for %s: %s', name, e)


def _start_downloads_watcher():
    """Start the watchdog observer. Silently unavailable if watchdog missing."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        logging.info('auto-import: watchdog not installed — watcher disabled')
        return None

    downloads = Path.home() / 'Downloads'
    if not downloads.is_dir():
        logging.info('auto-import: no Downloads folder found — watcher disabled')
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


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    _check_dependencies()

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

    # Start the Downloads auto-import watcher — Flask is up, token exists
    _start_downloads_watcher()

    window = webview.create_window(
        title='Groundwork',
        url='http://127.0.0.1:8765/',
        js_api=api,
        width=1280,
        height=820,
        min_size=(900, 600),
    )

    webview.start(debug=False)
    _stop_engine()


if __name__ == '__main__':
    main()
