# -*- mode: python ; coding: utf-8 -*-
# Groundwork — PyInstaller spec file
# Run from C:\Groundwork\ with: pyinstaller groundwork.spec --clean --noconfirm

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
try:
    import webview
    webview_path = Path(webview.__file__).parent
except ImportError:
    webview_path = None

a = Analysis(
    ['launch.py'],
    pathex=['C:\\Groundwork'],
    binaries=[],
    datas=[
        ('static', 'static'),
        ('core', 'core'),
        ('bank_importer.py', '.'),
        *( [(str(webview_path / 'js'), 'webview/js')] if webview_path and (webview_path / 'js').exists() else [] ),
        *( [(str(webview_path / 'lib'), 'webview/lib')] if webview_path and (webview_path / 'lib').exists() else [] ),
    ],
    hiddenimports=[
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
        'gi',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

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
    upx_exclude=[],
    name='Groundwork',
)
