# -*- mode: python ; coding: utf-8 -*-
# Groundwork — PyInstaller spec file for macOS
# Run from the repo root with: pyinstaller groundwork_macos.spec --clean --noconfirm
#
# Mirrors groundwork.spec (Windows) but drops the Windows-only .NET/pythonnet
# hidden imports (clr, System.*, webview's winforms/mshtml/edgechromium
# backends) since pywebview selects its Cocoa backend on macOS instead, and
# produces a BUNDLE (.app) rather than a bare EXE/COLLECT tree.

import sys
from pathlib import Path

block_cipher = None
root = Path.cwd()

try:
    import webview
    webview_path = Path(webview.__file__).parent
except ImportError:
    webview_path = None

icon_path = root / 'assets' / 'groundwork.icns'

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
        'watchdog.observers.fsevents',
        'watchdog.observers.kqueue',
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
        # pywebview — Cocoa backend on macOS
        'webview',
        'webview.platforms',
        'webview.platforms.cocoa',
        'webview.guilib',
        'webview.js',
        # tkinter (native file dialogs)
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        '_tkinter',
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
        'PyQt5',
        'PyQt6',
        'wx',
        'gi',
    ],
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

app = BUNDLE(
    coll,
    name='Groundwork.app',
    icon=str(icon_path) if icon_path.exists() else None,
    bundle_identifier='app.groundworkfinance.desktop',
    info_plist={
        'CFBundleName': 'Groundwork',
        'CFBundleDisplayName': 'Groundwork',
        'CFBundleShortVersionString': '1.1.0',
        'NSHighResolutionCapable': True,
    },
)
