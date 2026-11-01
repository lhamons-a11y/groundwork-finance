"""The Mac build check of 2026-10-31 (gw 2.0/MAC_BUILD_CHECK_2026-10-31.md; Rob: "Fix all 14").

    1   the Downloads watcher reads the folder before watching it, and starts after the window, on its own thread
    2   the page - and with it the token - only for the window: a one-time key traded for an HttpOnly cookie
    3   account and debt names escaped in the dropdowns and the pop-up messages; a name that is HTML stays text
    4   a Content-Security-Policy that leaves injected script nowhere to send data, and no framing
    6   HTTPS from the built app finds certifi's certificate list
    7   nothing beside static/ is served but the named icons
    8   /api/health without the token says only that the server is up
    9   a build stamp beside the release stamp; 10 the icon; 14 build_macos.sh and the hardened-runtime entitlements
    11  a stream refused for length on its first chunk is the too-long answer, not a crash
    12  the data files made this user's alone
    13  at most ASSIST_JOBS_AT_ONCE assistant questions at once

Issue 5 (a Developer ID and notarization) needs a certificate this Mac does not have: build_macos.sh signs with one
when GW_SIGN_IDENTITY names it. That much is checked here; the signing itself is not.
"""
import os
import re
import stat
import tempfile
from pathlib import Path


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    import server
    import launch
    base = Path(server.__file__).parent
    key, cookie = server._GW_PAGE_KEY, server._PAGE_COOKIE
    tok = server._GW_TOKEN.encode()

    # ── 2. the page key ────────────────────────────────────────────────────────
    fresh = c.application.test_client                       # each its own cookie jar: the shared client keeps none
    bare = fresh().get('/')
    wrong = fresh().get('/?k=not-the-key')
    win = fresh()
    first = win.get(f'/?k={key}')
    sc = first.headers.get('Set-Cookie', '')
    check('s270 #2 / with no page cookie: refused, and no token in the answer',
          bare.status_code == 403 and tok not in bare.data and b'GW_SESSION_TOKEN' not in bare.data)
    check('s270 #2 a wrong page key is refused with no token', wrong.status_code == 403 and tok not in wrong.data)
    check('s270 #2 the right key: a redirect to /, a cookie that is HttpOnly and SameSite=Strict, no token in it',
          first.status_code == 303 and first.headers.get('Location', '').endswith('/') and tok not in first.data
          and f'{cookie}={key}' in sc and 'HttpOnly' in sc and 'SameSite=Strict' in sc)
    page = win.get('/')
    check('s270 #2 with the cookie it was given, the window gets the page and the token',
          page.status_code == 200 and tok in page.data)
    old = fresh()
    old.set_cookie(cookie, 'an-old-key')
    stale = old.get('/')
    check('s270 #2 a cookie from an earlier start is refused', stale.status_code == 403 and tok not in stale.data)
    server._PAGE_GATE = False
    try:
        broken = fresh().get('/').status_code == 200
    finally:
        server._PAGE_GATE = True
    check('s270 #2 proof: with the gate off the bare request gets the page (so the refusal above is the gate)', broken)
    src_launch = (base / 'launch.py').read_text(encoding='utf-8')
    check("s270 #2 the window opens on the page key, and dev_server.py alone turns the gate off",
          "?k={_server._GW_PAGE_KEY}" in src_launch
          and '_PAGE_GATE = False' in (base / 'dev_server.py').read_text(encoding='utf-8'))

    # ── 4. headers ─────────────────────────────────────────────────────────────
    for label, r in (('the page', page), ('an API answer', c.get('/api/settings/bootstrap', headers=H)),
                     ('a script file', c.get('/js/app.js'))):
        csp = r.headers.get('Content-Security-Policy', '')
        check(f's270 #4 {label} carries the CSP (connect only to itself, no framing), X-Frame-Options and nosniff',
              "connect-src 'self'" in csp and "frame-ancestors 'none'" in csp and "default-src 'self'" in csp
              and "img-src 'self' data: blob:" in csp and r.headers.get('X-Frame-Options') == 'DENY'
              and r.headers.get('X-Content-Type-Options') == 'nosniff')

    # ── 7. what is served ──────────────────────────────────────────────────────
    gone = {p: c.get(p).status_code for p in ('/core/database.py', '/server.py', '/LICENSE', '/bank_importer.py',
                                              '/models/phi3.5-mini-instruct-q4.gguf', '/launch.py', '/no-such-file')}
    check(f's270 #7 nothing beside static/ is served: {gone}', set(gone.values()) == {404})
    check('s270 #7 static files and the named icons still are',
          c.get('/js/app.js').status_code == 200 and c.get('/fonts/fonts.css').status_code == 200
          and all(c.get('/' + n).status_code == 200 for n in server._ASSET_FILES if (base / n).exists()))

    # ── 8. health ──────────────────────────────────────────────────────────────
    anon = c.get('/api/health').get_json()
    mine = c.get('/api/health', headers=H).get_json()
    check(f's270 #8 /api/health without the token is only {{ok: true}} (got {anon})', anon == {'ok': True})
    check('s270 #8 with the token: version, build and session for the heartbeat',
          mine.get('version') == server.GW_VERSION and mine.get('build') == server.GW_BUILD and mine.get('session_id'))

    # ── 3. names that are HTML ─────────────────────────────────────────────────
    js = (base / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    check('s270 #3 the three account dropdowns escape the names (Ledger, Select account, Investments)',
          "accts.map(a=>`<option value=\"${esc(a)}\"${a===cur?' selected':''}>${esc(a)}</option>`)" in js
          and "accounts.map(a => `<option value=\"${esc(a)}\">${esc(a)}</option>`)" in js
          and "accounts.map(a => `<option value=\"${esc(a.id)}\">${esc(a.name)}</option>`)" in js)
    check('s270 #3 and the typed-name lists and the pop-up messages',
          "_accountNames().map(a => `<option value=\"${esc(a)}\">`)" in js
          and "cats.map(c=>`<option value=\"${esc(c)}\">`)" in js and "accs.map(a=>`<option value=\"${esc(a)}\">`)" in js
          and '<div class="toast-title">${esc(title)}</div>' in js and '<div class="toast-sub">${esc(sub)}</div>' in js)
    unescaped = [m.group(0) for line in js.splitlines() if '<option' in line
                 for m in re.finditer(r'<option value="\$\{(a|c|a\.name|c\.name|x\.name)\}"[^>]*>\$\{\1\}', line)]
    check(f's270 #3 no <option> prints a bare account or category name as its value: {unescaped[:3]}', not unescaped)
    evil = '<img src=x onerror=alert(1)>'
    made = c.post('/api/accounts', headers=ctx.HJ, json={'name': evil, 'type': 'checking'})
    names = [a.get('name') for a in (c.get('/api/accounts', headers=H).get_json() or {}).get('data', [])] \
        if made.status_code in (200, 201) else []
    check('s270 #3 an account named with HTML is kept as written (the page escapes it; the record is not altered)',
          made.status_code not in (200, 201) or evil in names)
    if made.status_code in (200, 201):
        aid = (made.get_json() or {}).get('data', {}).get('id') or (made.get_json() or {}).get('id')
        if aid:
            c.delete(f'/api/accounts/{aid}', headers=H)

    # ── 1. the watcher ─────────────────────────────────────────────────────────
    sw = src_launch[src_launch.find('def _start_downloads_watcher'):src_launch.find('def _start_engine')]
    check('s270 #1 the watcher reads Downloads (os.listdir, which lets go of the lock) before it watches',
          0 < sw.find('os.listdir(downloads)') < sw.find('observer.schedule'))
    mn = src_launch[src_launch.find('def main'):]
    check('s270 #1 main starts the watcher after the window is made, on its own thread, waiting for it to show',
          0 < mn.find('webview.create_window') < mn.find('def _watch_after_shown')
          and 'window.events.shown.wait' in mn and "name='groundwork-downloads'" in mn
          and mn.find('_start_downloads_watcher()') > mn.find('webview.create_window'))
    import bank_window
    real_dd = bank_window.downloads_dir
    locked = Path(tempfile.mkdtemp())
    locked.chmod(0)
    try:
        bank_window.downloads_dir = lambda: locked
        # chmod(0) locks a folder on macOS and Linux only; on Windows (no geteuid) it cannot, so there is nothing to test
        refused = launch._start_downloads_watcher() is None if getattr(os, 'geteuid', lambda: 0)() != 0 else True
    finally:
        bank_window.downloads_dir = real_dd
        locked.chmod(0o700)
        locked.rmdir()
    check('s270 #1 a Downloads it may not read: no watcher, no hang', refused)

    # ── 6. certificates ────────────────────────────────────────────────────────
    saved = os.environ.pop('SSL_CERT_FILE', None)
    try:
        launch._use_bundled_certificates()
        got = os.environ.get('SSL_CERT_FILE', '')
    finally:
        os.environ.pop('SSL_CERT_FILE', None)
        if saved is not None:
            os.environ['SSL_CERT_FILE'] = saved
    import certifi
    check('s270 #6 the launcher points HTTPS at certifi\'s list', got == certifi.where() and Path(got).exists())
    spec = (base / 'groundwork_macos.spec').read_text(encoding='utf-8')
    check('s270 #6 the Mac build ships certifi and its list', "(certifi.where(), 'certifi')" in spec and "'certifi'," in spec)
    check('s270 #6 main sets it before anything opens a connection',
          0 < mn.find('_use_bundled_certificates()') < mn.find('_start_server'))

    # ── 9, 10, 14. the build ───────────────────────────────────────────────────
    check('s270 #9 the Mac build writes a build stamp to CFBundleVersion and build_info.json, and the log says it',
          "'CFBundleVersion': _build_id" in spec and 'build_info.json' in spec
          and "'Groundwork %s (build %s) starting', GW_VERSION, GW_BUILD" in ctx.server_src)
    check('s270 #10 the icon is in the repo', (base / 'assets' / 'groundwork.icns').stat().st_size > 10_000)
    sh = base / 'build_macos.sh'
    shs = sh.read_text(encoding='utf-8')
    check('s270 #14 build_macos.sh: executable; installs PyInstaller, finds the models, clears xattrs, signs and verifies',
          os.access(sh, os.X_OK) and 'pip install --quiet pyinstaller' in shs and 'GW_MODEL_PATH' in shs
          and 'GW_WHISPER_PATH' in shs and 'xattr -cr' in shs and 'codesign --verify --deep --strict' in shs)
    ent = (base / 'entitlements_macos.plist').read_text(encoding='utf-8')
    check('s270 #5 with a Developer ID: the hardened runtime, entitlements for executable memory and the microphone only',
          '--options runtime' in shs and 'notarytool' in shs and 'allow-unsigned-executable-memory' in ent
          and 'audio-input' in ent and 'disable-library-validation' not in ent and 'allow-jit' not in ent)
    check('s270 #1 Info.plist says why Downloads is asked for', 'NSDownloadsFolderUsageDescription' in spec)

    # ── 11. the stream refused on its first chunk ──────────────────────────────
    from core import engine

    class _TooLong:
        def create_chat_completion(self, **kw):
            def gen():
                raise ValueError('Requested tokens (2787) exceed context window of 2048')
                yield {}
            return gen()

    real_model, real_state = engine._model, dict(engine._state)
    engine._model, engine._state['state'] = _TooLong(), 'ready'
    try:
        events = list(engine.chat_stream('s', [{'role': 'user', 'content': 'x'}]))
        crashed = None
    except ValueError as e:
        events, crashed = [], e
    finally:
        engine._model = real_model
        engine._state.clear(); engine._state.update(real_state)
    check(f's270 #11 a stream refused for length on its first chunk is the too-long answer, not a crash ({crashed})',
          crashed is None and len(events) == 1 and events[0][0] == 'error' and events[0][1]['reason'] == 'too_long')

    # ── 12. file modes ─────────────────────────────────────────────────────────
    from core.database import DATA_DIR
    probe = DATA_DIR / 's270_probe.txt'
    probe.write_text('x'); probe.chmod(0o644)
    try:
        launch._tighten_data_files()
        mode = stat.S_IMODE(probe.stat().st_mode)
    finally:
        probe.unlink()
    # Windows keeps no owner/group/other modes (a file reads 0o666 whatever is set; access is the account's ACL)
    check(f's270 #12 a data file left at 644 is made 600 ({oct(mode)})', mode == 0o600 or os.name == 'nt')
    check('s270 #12 the app sets a 077 umask before it starts', 'os.umask(0o077)' in mn and mn.find('os.umask') < mn.find('_start_server'))

    # ── 13. the assistant ──────────────────────────────────────────────────────
    real_on = server._assistant_ai_on
    with server._ASSIST_LOCK:
        held = dict(server._ASSIST_JOBS)
        import time as _t
        for i in range(server.ASSIST_JOBS_AT_ONCE):
            server._ASSIST_JOBS[f's270-{i}'] = {'t': _t.time(), 'step': 'x', 'done': False, 'result': None}
    server._assistant_ai_on = lambda session: True
    try:
        r = c.post('/api/assistant/ask', headers=ctx.HJ, json={'question': 'what did I spend?'})
    finally:
        server._assistant_ai_on = real_on
        with server._ASSIST_LOCK:
            server._ASSIST_JOBS.clear(); server._ASSIST_JOBS.update(held)
    check(f's270 #13 with {server.ASSIST_JOBS_AT_ONCE} questions in progress, one more is refused, not threaded '
          f'({r.status_code})', r.status_code == 429)
