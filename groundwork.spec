# -*- mode: python ; coding: utf-8 -*-
# Groundwork — PyInstaller spec file
# Run from C:\Groundwork\ with: pyinstaller groundwork.spec --clean --noconfirm

import os
import sys
from pathlib import Path

block_cipher = None

# ── Windows version resource ──────────────────────────────────────────────
# Without this the built Groundwork.exe carries NO version metadata at all --
# right-click > Properties > Details is blank, which reads as untrustworthy on
# an unsigned binary and is a question Store certification asks. Generated from
# version.py rather than hard-coded here so that file remains what it claims to
# be: the single source of truth. The installers' AppVersion is set separately
# in the .iss files and must be bumped alongside it.
sys.path.insert(0, str(Path(SPECPATH)))
from version import VERSION, VERSION_TUPLE, APP_NAME, RELEASE_YEAR

_version_res = Path(SPECPATH) / 'build' / 'version_info.txt'
_version_res.parent.mkdir(parents=True, exist_ok=True)
_version_res.write_text(f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={VERSION_TUPLE!r},
    prodvers={VERSION_TUPLE!r},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)
  ),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{APP_NAME}'),
      StringStruct('FileDescription', '{APP_NAME} - Personal Finance'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', '{APP_NAME}'),
      StringStruct('LegalCopyright', '(c) {RELEASE_YEAR} {APP_NAME}'),
      StringStruct('OriginalFilename', '{APP_NAME}.exe'),
      StringStruct('ProductName', '{APP_NAME}'),
      StringStruct('ProductVersion', '{VERSION}'),
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
''', encoding='utf-8')

# Find pywebview package location
# The local AI engine (ENGINE_REPLACEMENT.md, item 31): llama-cpp-python, the CPU wheel, runs the model inside
# Groundwork. It is imported lazily (core/engine.py, after the processor check), so PyInstaller cannot see it on its
# own; it is collected here. A build without it would ship a Groundwork whose AI can never start, so it fails here.
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules, collect_data_files
try:
    import llama_cpp  # noqa: F401
except Exception as _e:
    raise SystemExit('groundwork.spec: llama-cpp-python is not installed in the build environment (%s). Install the '
                     'CPU wheel: pip install llama-cpp-python==0.3.35 --only-binary=:all: '
                     '--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu' % _e)
# Item 95 (GPU_ENGINE.md G1/G2): on Windows the shipped engine is the Vulkan build with run-time backends, made by
# build_engine_wheel.bat - the processor always works, a graphics chip when fitting chooses it. The CPU-index wheel has
# no graphics backend, so a Windows build made with it would quietly never use the graphics chip: refused here.
if sys.platform == 'win32':
    import pathlib as _pl
    if not any(_pl.Path(llama_cpp.__file__).parent.joinpath('lib').glob('ggml-vulkan*.dll')):
        raise SystemExit('groundwork.spec: this llama-cpp-python has no Vulkan backend. Build and install the item 95 '
                         'engine wheel first: build_engine_wheel.bat (GPU_ENGINE.md "G1 proven").')
_engine_binaries = collect_dynamic_libs('llama_cpp')
_engine_datas = collect_data_files('llama_cpp')
_engine_imports = collect_submodules('llama_cpp')
# Item 113: voice commands (core/voice.py) - optional; the installer places models/ggml-base.en.bin
import spec_engine
_voice_binaries, _voice_datas, _voice_imports = spec_engine.voice_parts()
# Groundwork's own voice (core/speak.py) - optional; the installer places models/kokoro-v1.0.int8.onnx and voices-v1.0.bin
_speak_binaries, _speak_datas, _speak_imports = spec_engine.speak_parts()

try:
    import webview
    webview_path = Path(webview.__file__).parent
except ImportError:
    webview_path = None

a = Analysis(
    ['launch.py'],
    pathex=['C:\\Groundwork'],
    binaries=[*_engine_binaries, *_voice_binaries, *_speak_binaries],
    datas=[
        *_engine_datas, *_voice_datas, *_speak_datas,
        ('static', 'static'),
        ('core', 'core'),
        ('bank_importer.py', '.'),
        ('LICENSE', '.'), ('THIRD_PARTY_NOTICES.md', '.'), ('EULA.txt', '.'),   # GPL v3: the license ships with the app
        *( [(str(webview_path / 'js'), 'webview/js')] if webview_path and (webview_path / 'js').exists() else [] ),
        *( [(str(webview_path / 'lib'), 'webview/lib')] if webview_path and (webview_path / 'lib').exists() else [] ),
    ],
    hiddenimports=[
        # keyring - item 57 (BANK_AGENT.md A4): bank logins live in the operating system's vault. Imported
        # inside core/bank_vault.py's functions, and its backend is chosen at runtime, so both are named here.
        'keyring', 'keyring.backends', 'keyring.backends.Windows',
        *_engine_imports, *_voice_imports, 'core.voice', *_speak_imports, 'core.speak',
        # Item 95 (GPU_ENGINE.md G3/G4'): the fitting test runs in a child process started as this executable with
        # --engine-probe, imported inside launch.main(); its R8 check reads the voice cases from voice_discipline_test.
        'core.engine_fit', 'voice_discipline_test',
        # waitress — the WSGI server every launch path now uses. Imported
        # inside server.serve() rather than at module scope, which is exactly
        # the import style PyInstaller's static analysis is least likely to
        # trace; without this the bundle falls back to the development server
        # and nobody finds out except by measuring.
        'waitress',
        'waitress.server',
        # watchdog — Downloads auto-import watcher (RESOLVED July 8; flagged
        # since June). launch.py degrades gracefully if watchdog is missing,
        # which means a build without it shows NO error — testers just never
        # get the "file detected" banner. Explicit hiddenimports make the
        # bundle independent of whether PyInstaller's static analysis happens
        # to trace launch.py's import style. winapi + read_directory_changes
        # are the Windows backend modules watchdog selects at runtime;
        # polling is its universal fallback.
        'watchdog',
        'watchdog.events',
        'watchdog.observers',
        'watchdog.observers.api',
        'watchdog.observers.winapi',
        'watchdog.observers.read_directory_changes',
        'watchdog.observers.polling',
        'watchdog.utils',
        'watchdog.utils.dirsnapshot',
        # price_engine — same silent-degradation class as watchdog:
        # server.py imports it inside try/except ImportError, so a bundle
        # without it doesn't crash — prices just silently go manual-only.
        # d19 proved it does get traced (tester price logs), but explicit
        # beats accidental.
        'price_engine',
        # gas_price / utility_price / trip_distance / pdf_statement — same
        # function-local `import x` style as price_engine above, imported
        # the same way from inside server.py route handlers. PyInstaller's
        # static analysis likely already traces these (as it does
        # price_engine), but explicit beats accidental here too — a bundle
        # missing one of these would silently degrade a feature (trip gas
        # price, utility benchmarks, distance lookup, PDF import) rather
        # than crash, with no obvious signal that something's wrong.
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
        # pywebview
        'webview',
        'webview.platforms',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'webview.platforms.mshtml',
        'webview.guilib',
        'webview.js',
        # .NET / pythonnet
        'clr',
        'clr_loader',
        'pythonnet',
        'System',
        # tkinter
        # stdlib — let PyInstaller include everything it finds automatically
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
        # Only exclude things we are 100% certain are not needed
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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    icon='groundwork.ico',
    version=str(_version_res),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    # The engine's native libraries are never UPX-packed: they are loaded by ctypes and a packed DLL is one more
    # thing that can fail on a clean machine.
    upx_exclude=['llama.dll', 'ggml.dll', 'ggml-base.dll', 'ggml-cpu.dll', 'mtmd.dll'],
    name='Groundwork',
)
