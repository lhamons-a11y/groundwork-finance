# -*- mode: python ; coding: utf-8 -*-
# Groundwork — PyInstaller spec file for Linux
# Run from the repo root with: pyinstaller groundwork_linux.spec --clean --noconfirm
#
# Mirrors groundwork.spec (Windows) but drops the Windows-only .NET/pythonnet
# hidden imports (clr, System.*, webview's winforms/mshtml/edgechromium
# backends) since pywebview selects its GTK/WebKit2 backend on Linux instead,
# and produces a plain COLLECT tree (no BUNDLE/.app — that's macOS-only).
# gi/PyGObject/WebKit2 are system packages (apt: python3-gi, gir1.2-webkit2-4.1),
# not pip-installable, so the venv building this must have been created with
# --system-site-packages.

from pathlib import Path

block_cipher = None
root = Path.cwd()

try:
    import webview
    webview_path = Path(webview.__file__).parent
except ImportError:
    webview_path = None

a = Analysis(
    ['launch.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[
        ('static', 'static'),
        ('core', 'core'),
        ('bank_importer.py', '.'),
        *( [(str(webview_path / 'js'), 'webview/js')] if webview_path and (webview_path / 'js').exists() else [] ),
    ],
    hiddenimports=[
        'watchdog',
        'watchdog.events',
        'watchdog.observers',
        'watchdog.observers.api',
        'watchdog.observers.inotify',
        'watchdog.observers.inotify_buffer',
        'watchdog.observers.inotify_c',
        'watchdog.observers.polling',
        'watchdog.utils',
        'watchdog.utils.dirsnapshot',
        'price_engine',
        'gas_price',
        'utility_price',
        'trip_distance',
        'pdf_statement',
        'flight_price',
        # Flask
        'flask',
        'flask.json',
        'flask.json.provider',
        'flask.templating',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.middleware',
        'werkzeug.middleware.proxy_fix',
        'werkzeug.debug',
        'jinja2',
        'jinja2.ext',
        'click',
        'itsdangerous',
        # SQLAlchemy
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.sqlite.pysqlite',
        'sqlalchemy.orm',
        'sqlalchemy.pool',
        'sqlalchemy.event',
        'sqlalchemy.ext.declarative',
        'sqlalchemy.sql.default_comparator',
        # pywebview — GTK/WebKit2 backend on Linux
        'webview',
        'webview.platforms',
        'webview.platforms.gtk',
        'webview.guilib',
        'webview.js',
        'gi',
        'gi.repository',
        'gi.repository.Gtk',
        'gi.repository.GLib',
        'gi.repository.GObject',
        'gi.repository.WebKit2',
        'gi.repository.Gdk',
        # tkinter (native file dialogs)
        # stdlib
        'secrets',
        'threading',
        'logging',
        'logging.handlers',
        'json',
        'pathlib',
        'datetime',
        're',
        'csv',
        'difflib',
        'importlib',
        'importlib.util',
        'importlib.metadata',
        'email',
        'email.mime',
        'email.mime.text',
        'xml',
        'xml.etree',
        'xml.etree.ElementTree',
    ],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        # pdfplumber's render backend. It and PIL are imported in exactly one
        # place - pdfplumber/display.py - and Groundwork only ever calls
        # page.extract_text() (pdf_statement.py: 'layout -> text ONLY').
        # PIL was already excluded here and PDF extraction kept working, which
        # is the precedent: same import, same file, same verdict. Verified with
        # both blocked - a real 4-page statement still extracts 14,064 chars.
        # NOTE: cryptography is NOT excludable. pdfminer.six requires it
        # outright for encrypted PDFs, and bank statements often are.
        'pypdfium2',
        'pypdfium2_raw',
        # tkinter and its ~8MB of tcl/tk. Nothing imports it any more: the two
        # startup error dialogs use ctypes/osascript/zenity (stdlib only, and
        # they must be - they fire when an import has already failed), and the
        # backup folder picker uses pywebview, which already draws the whole
        # UI. pywebview itself imports tkinter nowhere, so this is safe on
        # every platform, not just Windows.
        'tkinter',
        '_tkinter',
        'PyQt5',
        'PyQt6',
        'wx',
    ],
    cipher=block_cipher,
    noarchive=False,
)

# ── Product line: which build is this? ────────────────────────────────────
# GW_PRODUCT=lts strips the 2.0 teaching layer out of the bundle. The split is
# teaching-layer vs no-teaching-layer, so the boundary is a path segment rather
# than a feature flag: nothing under static/js/teaching/ ships in an LTS build,
# and server.py emits no loader tag for a file that is not there. An LTS build
# therefore does not disable the teaching layer, it does not contain it.
#
# Filtering the TOC after Analysis, rather than pruning the datas list before
# it, means the rule holds however those files were collected.
GW_PRODUCT = os.environ.get('GW_PRODUCT', 'teaching').strip().lower()
GW_TEACHING_PREFIX = 'static/js/teaching/'
if GW_PRODUCT == 'lts':
    _before = len(a.datas)
    a.datas = [t for t in a.datas
               if not '/'.join(t[0].split(os.sep)).startswith(GW_TEACHING_PREFIX)]
    print('[spec] GW_PRODUCT=lts - stripped %d teaching-layer file(s)'
          % (_before - len(a.datas)))
else:
    print('[spec] GW_PRODUCT=%s - teaching layer included' % GW_PRODUCT)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Groundwork',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Groundwork',
)
