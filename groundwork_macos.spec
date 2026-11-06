# -*- mode: python ; coding: utf-8 -*-
# Groundwork — PyInstaller spec file for macOS
# Run from the repo root with: pyinstaller groundwork_macos.spec --clean --noconfirm
#
# Mirrors groundwork.spec (Windows) but drops the Windows-only .NET/pythonnet
# hidden imports (clr, System.*, webview's winforms/mshtml/edgechromium
# backends) since pywebview selects its Cocoa backend on macOS instead, and
# produces a BUNDLE (.app) rather than a bare EXE/COLLECT tree.

import os
import sys
from pathlib import Path

block_cipher = None
root = Path.cwd()

# The local AI engine and its pinned, fingerprint-checked model (ENGINE_OTHER_PLATFORMS.md, item 33; spec_engine.py).
# The build fails without the runtime or with the wrong model - except on an Intel Mac, where no tested runtime exists
# and Groundwork ships with local AI unavailable (Q2).
import sys
from pathlib import Path
sys.path.insert(0, str(Path(SPECPATH)))
import spec_engine
_engine_binaries, _engine_datas, _engine_imports = spec_engine.engine_parts()
_model_datas = spec_engine.model_data()
_voice_binaries, _voice_datas, _voice_imports = spec_engine.voice_parts()     # item 113
_voice_model = spec_engine.voice_model_data()
_road_binaries, _road_datas, _road_imports = spec_engine.road_parts()     # the road map (core/road_map.py)
_speak_binaries, _speak_datas, _speak_imports = spec_engine.speak_parts()     # Groundwork's own voice (core/speak.py)
_speak_model = spec_engine.speak_model_data()
_voiceprint_model = spec_engine.voiceprint_model_data()     # item 116 V19

try:
    import webview
    webview_path = Path(webview.__file__).parent
except ImportError:
    webview_path = None

icon_path = root / 'assets' / 'groundwork.icns'      # committed; build_icns.py + iconutil remake it (issue 10)

# HTTPS needs a certificate list the frozen Python can find (Mac check 2026-10-31, issue 6): certifi's, pointed at by
# launch._use_bundled_certificates. Without it every update check and price lookup failed.
import certifi
_certifi_datas = [(certifi.where(), 'certifi')]

# Which build this is (issue 9). GW_VERSION is the release stamp the update feed compares, and it changes only with
# a release; this tells two builds of the same release apart - in Info.plist's CFBundleVersion and in the log.
import json, subprocess, datetime
try:
    _commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True,
                             cwd=str(root)).stdout.strip() or 'unknown'
    _dirty = bool(subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], capture_output=True,
                                 text=True, cwd=str(root)).stdout.strip())
except OSError:
    _commit, _dirty = 'unknown', False
_built = datetime.datetime.now().strftime('%Y%m%d.%H%M')
_build_id = f"{_built}-{_commit}{'+' if _dirty else ''}"
(root / 'build').mkdir(exist_ok=True)
(root / 'build' / 'build_info.json').write_text(json.dumps({'build': _build_id, 'commit': _commit, 'dirty': _dirty}))

a = Analysis(
    ['launch.py'],
    pathex=[str(root)],
    binaries=[*_engine_binaries, *_voice_binaries, *_speak_binaries, *_road_binaries],
    datas=[
        *_engine_datas,
        *_voice_datas, *_voice_model,
        *_speak_datas, *_speak_model, *_voiceprint_model,
        *_model_datas,             # -> models/ (macOS: Contents/Resources/models), where core/engine.py looks
        *_certifi_datas,
        (str(root / 'build' / 'build_info.json'), '.'),
        ('static', 'static'),
        ('core', 'core'),
        ('bank_importer.py', '.'),
        ('LICENSE', '.'), ('THIRD_PARTY_NOTICES.md', '.'), ('EULA.txt', '.'),   # GPL v3: the license ships with the app
        *( [(str(webview_path / 'js'), 'webview/js')] if webview_path and (webview_path / 'js').exists() else [] ),
    ],
    hiddenimports=[
        # keyring - item 57 (BANK_AGENT.md A4): bank logins live in the operating system's vault. Imported
        # inside core/bank_vault.py's functions, and its backend is chosen at runtime, so both are named here.
        'keyring', 'keyring.backends', 'keyring.backends.macOS',
        'certifi',
        *_engine_imports, *_voice_imports, 'core.voice', *_speak_imports, 'core.speak', *_road_imports, 'core.road_map',
        # waitress — the WSGI server every launch path now uses. Imported
        # inside server.serve() rather than at module scope, which is exactly
        # the import style PyInstaller's static analysis is least likely to
        # trace; without this the bundle falls back to the development server
        # and nobody finds out except by measuring.
        'waitress',
        'waitress.server',
        'watchdog',
        'watchdog.events',
        'watchdog.observers',
        'watchdog.observers.api',
        'watchdog.observers.fsevents',
        'watchdog.observers.kqueue',
        'watchdog.observers.polling',
        'watchdog.utils',
        'watchdog.utils.dirsnapshot',
        'price_engine',
        'gas_price',
        'utility_price',
        'trip_distance',
        'flights_window',
        'hotels_window',
        'pdf_statement',
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
        # pywebview — Cocoa backend on macOS
        'webview',
        'webview.platforms',
        'webview.platforms.cocoa',
        'webview.guilib',
        'webview.js',
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
        # numpy is NOT excluded: llama_cpp imports it (the local AI engine).
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
        # tkinter and its ~10MB of tcl/tk. Nothing imports it any more: the two
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
        'gi',
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
    # The engine's native libraries are never UPX-packed (they are loaded by ctypes).
    upx_exclude=['libllama.dylib', 'libggml.dylib', 'libggml-base.dylib', 'libggml-cpu.dylib', 'libggml-metal.dylib', 'libggml-blas.dylib', 'libmtmd.dylib', 'libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libmtmd.so'],
    name='Groundwork',
)

app = BUNDLE(
    coll,
    name='Groundwork.app',
    icon=str(icon_path) if icon_path.exists() else None,
    bundle_identifier='app.groundworkfinance.desktop',
    info_plist={
        'CFBundleName': 'Groundwork',
        'CFBundleDisplayName': 'Groundwork',
        'CFBundleShortVersionString': '1.1.1',
        'CFBundleVersion': _build_id,
        # Issue 1: what macOS shows when it asks about Downloads. The watcher only reads the folder after the window
        # is open, so the question never holds up starting.
        'NSDownloadsFolderUsageDescription': 'Groundwork watches Downloads for bank files you save, and offers to '
                                             'import them. Nothing is imported unless you say yes.',
        'NSHighResolutionCapable': True,
        # Item 113: push-to-talk voice commands. macOS asks the first time; the words are recognised on this Mac.
        'NSMicrophoneUsageDescription': 'Groundwork listens only while you hold Talk, for voice commands. What you say '
                                        'is recognised on this Mac and is never sent anywhere or kept.',
    },
)
