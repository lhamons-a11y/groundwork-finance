# -*- mode: python ; coding: utf-8 -*-
# Groundwork — PyInstaller spec file
# Run from C:\Groundwork\ with: pyinstaller groundwork.spec --clean --noconfirm

import sys
from pathlib import Path

block_cipher = None

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
        'System.Windows.Forms',
        'System.Threading',
        'System.Threading.Thread',
        # tkinter
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        '_tkinter',
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
        'pkg_resources',
        'pkg_resources.extern',
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
