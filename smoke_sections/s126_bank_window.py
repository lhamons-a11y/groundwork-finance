"""The bank window: an untrusted webpage viewer, not a Groundwork integration surface.

`gw 2.0/BANK_BROWSER.md`, ruled 2026-09-23 (s7), built after F12's acceptance. The invariant this section makes
executable: Groundwork supplies only the user-entered HTTPS URL, receives no page state, performs no interaction,
retains no session, and receives financial data only when the user independently downloads a file into the
existing review path.

    F4   the link rules - https only, no userinfo, no port, no IP literal, no local name, a full DNS name;
         checked on save AND at launch; :443 dropped, nothing else rewritten
    F3   one source of truth - a linked card stores no link and cannot be given one; unlinking empties it;
         linking a card whose link differs from the account's is refused until the user chooses
    F5   the link is launch configuration - with an address planted on an account and on a card, it appears in
         the answer of no GET route but the two /portal routes (network blocked, as s50), and portal_url is
         read in server.py only by the functions named here, and never by app.js
    F7   a statement is noticed by name, offered, and read only after yes - and only a path that was offered
    F2   one window per account; archiving or deleting closes it; Groundwork exiting closes all of them
    F6   the Downloads folder is the one the Save dialog uses - the Windows known folder, the XDG dir
    F1 / F13 / s5.1   the crossing test on bank_window.py's source, every ruled mutation caught

The bank process itself is not started here - it opens a window. F2 runs against a stand-in child that speaks the
same four-word protocol. The real process was measured on Windows when this was built (the build note, s9).
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

SENTINEL_A = 'https://sentinel-account-f5.example-bank.com/login'
SENTINEL_C = 'https://sentinel-card-f5.example-bank.com/'


# ── F4 ────────────────────────────────────────────────────────────────────────
F4_CASES = [
    ('', True),                              # empty clears the link
    ('https://www.superiorcu.com/', True),
    ('https://bank.com:443/login', True),
    ('http://bank.com/', False),
    ('https://user:pass@bank.com/', False),
    ('https://user@bank.com/', False),
    ('https://bank.com:8443/', False),
    ('https://127.0.0.1/', False),
    ('https://[::1]/', False),
    ('https://10.0.0.5/', False),
    ('https://localhost/', False),
    ('https://portal.localhost/', False),
    ('https://nas.local/', False),
    ('https://intranet/', False),
    ('javascript:alert(1)', False),
    ('file:///C:/Windows/', False),
    ('data:text/html,hi', False),
    ('https://bank.com/ path', False),
]


def _f4(c, H, aid):
    results = {}
    for url, ok in F4_CASES:
        r = c.put(f'/api/accounts/{aid}/portal', headers=H, json={'url': url})
        results[url] = (r.status_code == 200) == ok
    stored = c.get(f'/api/accounts/{aid}/portal', headers=H).get_json()['data']['url']
    return results, stored


# ── F3 ────────────────────────────────────────────────────────────────────────
_F3_RUNS = [0]


def _f3(c, H, dbs):
    out = {}
    _F3_RUNS[0] += 1
    n = _F3_RUNS[0]
    acct = c.post('/api/accounts', headers=H, json={'name': f's126 Checking {n}'}).get_json()['data']
    aid = acct['id']
    card = c.post('/api/debt', headers=H, json={'name': f's126 Visa {n}'}).get_json()['data']
    did = card['id']
    auto_aid = card['linked_account_id']
    out['a new card is linked to its companion account'] = bool(auto_aid)
    out['a linked card is refused a link of its own'] = \
        c.put(f'/api/debt/{did}/portal', headers=H, json={'url': 'https://card.example.com/'}).status_code == 409
    out['portal_url cannot be written through the debt PATCH'] = \
        c.patch(f'/api/debt/{did}', headers=H, json={'portal_url': 'https://card.example.com/'}).status_code == 400
    c.put(f'/api/accounts/{auto_aid}/portal', headers=H, json={'url': 'https://companion.example.com/'})
    got = c.get(f'/api/debt/{did}/portal', headers=H).get_json()['data']
    out['a linked card opens its account\'s link'] = got['owner'] == 'account' and got['url'] == 'https://companion.example.com/'
    c.patch(f'/api/debt/{did}', headers=H, json={'linked_account_id': None})
    got = c.get(f'/api/debt/{did}/portal', headers=H).get_json()['data']
    out['unlinking empties the card\'s link - nothing copied'] = got['owner'] == 'card' and got['url'] == ''
    c.put(f'/api/debt/{did}/portal', headers=H, json={'url': 'https://card.example.com/'})
    c.put(f'/api/accounts/{aid}/portal', headers=H, json={'url': 'https://account.example.com/'})
    r = c.patch(f'/api/debt/{did}', headers=H, json={'linked_account_id': aid})
    conflict = (r.get_json() or {}).get('portal_conflict') or {}
    out['linking two different links is refused until the user chooses'] = \
        r.status_code == 409 and conflict.get('card_host') == 'card.example.com' \
        and conflict.get('account_host') == 'account.example.com'
    r = c.patch(f'/api/debt/{did}', headers=H, json={'linked_account_id': aid, 'portal_keep': 'card'})
    got = c.get(f'/api/debt/{did}/portal', headers=H).get_json()['data']
    out['the user\'s choice governs, stored once on the account'] = \
        r.status_code == 200 and got['owner'] == 'account' and got['url'] == 'https://card.example.com/'
    c.patch(f'/api/debt/{did}', headers=H, json={'linked_account_id': None})
    out['relinking after an unlink resurrects nothing'] = \
        c.get(f'/api/debt/{did}/portal', headers=H).get_json()['data']['url'] == ''

    from core.database import DebtAccount
    with dbs() as s:
        both = s.query(DebtAccount).filter(DebtAccount.linked_account_id.isnot(None),
                                           DebtAccount.portal_url.isnot(None)).count()
    out['the database holds no linked card with a link of its own'] = both == 0
    return out


# ── F5 ────────────────────────────────────────────────────────────────────────
PORTAL_ROUTE = re.compile(r'^/api/(accounts|debt)/<int:[a-z_]+>/portal$')

# The functions in server.py allowed to touch portal_url, each for its reason.
PORTAL_READERS = {
    '_serialize_account',      # has_portal, a boolean
    'list_accounts',           # has_portal, a boolean
    '_debt_portal_url',        # resolves which link a card opens
    'get_account_portal', 'put_account_portal', 'open_account_portal',
    'put_debt_portal',         # get / open read it only through _debt_portal_url
    'update_debt',             # refuses portal_url in the PATCH body
    '_relink_card_portal',     # F3 across a link change
    '_bank_agent_accounts',    # item 57 (BANK_AGENT.md A1 (b)): whether a link exists, to list it; returns key + name, never the URL
    '_bank_agent_url',         # item 57: the link the agent's window opens - handed to that process on stdin, like the viewer's
}


def _portal_touchers(server_src):
    import ast
    tree = ast.parse(server_src)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            seg = ast.get_source_segment(server_src, node) or ''
            inner = {n.name for n in ast.walk(node)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not node}
            if re.search(r'(?<![A-Za-z0-9_])portal_url\b', seg) and not inner:
                found.add(node.name)
    return found


def _blocked(*_a, **_k):
    raise OSError('outbound network is blocked during the s126 sweep')


def _f5_sweep(c, H, app):
    urls = set()
    for rule in app.url_map.iter_rules():
        raw = str(rule.rule)
        if 'GET' not in (rule.methods or ()) or raw.startswith('/static') or '<path:' in raw:
            continue
        if PORTAL_ROUTE.match(raw):
            continue
        urls.add(re.sub(r'<[^>]+>', '1', raw))
    leaks = []
    real_connect, real_create = socket.socket.connect, socket.create_connection
    try:
        socket.socket.connect = _blocked
        socket.create_connection = _blocked
        for url in sorted(urls):
            try:
                body = c.get(url, headers=H).get_data(as_text=True)
            except Exception:                                   # noqa: BLE001
                continue
            if 'sentinel-account-f5' in body or 'sentinel-card-f5' in body:
                leaks.append(url)
    finally:
        socket.socket.connect, socket.create_connection = real_connect, real_create
    return len(urls), leaks


# ── F7 ────────────────────────────────────────────────────────────────────────
def _f7(c, H, server, tmp):
    import bank_window
    import launch
    out = {}
    fake = tmp / 's126_downloads'
    fake.mkdir(exist_ok=True)
    pdf = fake / 'statement_s126.pdf'
    pdf.write_bytes(b'%PDF-1.4 s126 statement bytes')
    other = fake / 'other_s126.pdf'
    other.write_bytes(b'%PDF-1.4 never offered')
    outside = tmp / 'outside_s126.pdf'
    outside.write_bytes(b'%PDF-1.4 outside')

    real_dd = bank_window.downloads_dir
    real_post = launch._post_queue_item
    posted = []
    try:
        bank_window.downloads_dir = lambda: fake
        # the watcher's decision, without the network: what would it post?
        launch._post_queue_item = lambda item: posted.append(item) or True
        launch._queue_import_file(pdf, {})
        csv = fake / 'bank_s126.csv'
        csv.write_text('Date,Description,Amount\n09/01/2026,S126,-1.00\n', encoding='utf-8')
        launch._queue_import_file(csv, {})
        for name in ('setup_s126.exe', 'bundle_s126.zip'):
            (fake / name).write_bytes(b'x')
            launch._queue_import_file(fake / name, {})
        kinds = [(p.get('kind'), 'content' in p) for p in posted]
        out['the watcher offers a statement by name only - its bytes unread'] = \
            ('statement', False) in kinds
        out['a structured file still carries its content to the offer'] = (None, True) in kinds
        out['anything else is ignored, never offered'] = len(posted) == 2

        r = c.post('/api/auto-import/queue', headers=H,
                   json={'filename': pdf.name, 'path': str(pdf), 'kind': 'statement'}).get_json()['data']
        item = c.get('/api/auto-import/pending', headers=H).get_json()['data']
        out['the offer carries no statement content'] = \
            r.get('queued') and item and item.get('kind') == 'statement' and 'content' not in item
        out['a statement outside the Downloads folder is not queued'] = not c.post(
            '/api/auto-import/queue', headers=H,
            json={'filename': outside.name, 'path': str(outside), 'kind': 'statement'}).get_json()['data']['queued']
        got = c.post('/api/auto-import/statement', headers=H, json={'path': str(pdf)})
        out['after yes, the offered statement\'s bytes are served'] = \
            got.status_code == 200 and got.data == pdf.read_bytes()
        out['a statement that was never offered is refused'] = c.post(
            '/api/auto-import/statement', headers=H, json={'path': str(other)}).status_code == 403
        out['a path outside the Downloads folder is refused'] = c.post(
            '/api/auto-import/statement', headers=H, json={'path': str(outside)}).status_code == 403
    finally:
        bank_window.downloads_dir = real_dd
        launch._post_queue_item = real_post
        server._offered_statements.clear()
    return out


# ── F2 ────────────────────────────────────────────────────────────────────────
_STAND_IN = r'''
import sys
url = sys.stdin.readline().strip()
say = sys.argv[1]
sys.stdout.write(say + "\n"); sys.stdout.flush()
if say == "ready":
    sys.stdin.read()
'''


def _f2(c, H, tmp):
    import bank_window
    out = {}
    script = tmp / 's126_stand_in.py'
    script.write_text(_STAND_IN, encoding='utf-8')
    real_cmd = bank_window._child_command
    try:
        bank_window._child_command = lambda: [sys.executable, str(script), 'ready']
        out['open -> opened'] = bank_window.open_bank_window(('account', 901), 'https://bank.example.com/') == 'opened'
        out['the same account again -> already_open, no second window'] = \
            bank_window.open_bank_window(('account', 901), 'https://bank.example.com/') == 'already_open'
        out['a different account -> its own window'] = \
            bank_window.open_bank_window(('account', 902), 'https://other.example.com/') == 'opened'
        bank_window.close_bank_window(('account', 901))
        out['closing one closes that one only'] = not bank_window.is_open(('account', 901)) \
            and bank_window.is_open(('account', 902))
        bank_window.close_all_bank_windows()
        out['Groundwork exiting closes every bank window'] = not bank_window.is_open(('account', 902))

        acct = c.post('/api/accounts', headers=H, json={'name': 's126 Archive me'}).get_json()['data']
        c.put(f"/api/accounts/{acct['id']}/portal", headers=H, json={'url': 'https://bank.example.com/'})
        r = c.post(f"/api/accounts/{acct['id']}/portal/open", headers=H, json={'mode': 'window'}).get_json()
        opened = r['data']['result'] == 'opened' and bank_window.is_open(('account', acct['id']))
        c.delete(f"/api/accounts/{acct['id']}", headers=H)
        out['archiving an account closes its bank window'] = opened and not bank_window.is_open(('account', acct['id']))

        bank_window._child_command = lambda: [sys.executable, str(script), 'refused-engine']
        out['an unusable engine is reported, never substituted'] = \
            bank_window.open_bank_window(('account', 903), 'https://bank.example.com/') == 'engine_unavailable' \
            and not bank_window.is_open(('account', 903))
        out['the parent refuses a bad link before any process starts'] = \
            bank_window.open_bank_window(('account', 904), 'http://bank.example.com/') == 'refused_url'
    finally:
        bank_window._child_command = real_cmd
        bank_window.close_all_bank_windows()
    return out


# ── F6 ────────────────────────────────────────────────────────────────────────
def _f6(tmp):
    import bank_window
    out = {}
    home = tmp / 's126_home'
    cfg = home / '.config'
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / 'user-dirs.dirs').write_text('XDG_DOWNLOAD_DIR="$HOME/Téléchargements"\n', encoding='utf-8')
    old = os.environ.get('XDG_CONFIG_HOME')
    os.environ['XDG_CONFIG_HOME'] = str(cfg)
    try:
        out['a localised XDG Downloads folder is the one watched'] = \
            bank_window._xdg_download_dir(home) == home / 'Téléchargements'
        (cfg / 'user-dirs.dirs').write_text('# nothing set\n', encoding='utf-8')
        out['no XDG setting -> ~/Downloads'] = bank_window._xdg_download_dir(home) == home / 'Downloads'
    finally:
        if old is None:
            os.environ.pop('XDG_CONFIG_HOME', None)
        else:
            os.environ['XDG_CONFIG_HOME'] = old
    if sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders') as k:
                reg = Path(os.path.expandvars(winreg.QueryValueEx(k, bank_window._WIN_DOWNLOADS_GUID)[0]))
        except OSError:
            reg = Path.home() / 'Downloads'
        out['on Windows, the watched folder is the known folder the WebView2 dialog opens'] = \
            bank_window.downloads_dir() == reg
    return out


# ── The upgrade path: an existing database must gain the columns ──────────────
# Found while building, not assumed: migrate.py skips every step while the stored
# schema_version equals SCHEMA_VERSION, so adding the columns without bumping it
# left every existing database without them - bootstrap crashed on the first
# query. A fresh gate database can never show that; this case recreates the
# failure where it appears: a database at the previous version, columns absent.

def _upgrade(prior_version):
    import migrate
    from sqlalchemy import text
    from core.database import engine

    def cols(table):
        with engine.connect() as conn:
            return {r[1] for r in conn.execute(text(f'PRAGMA table_info({table})'))}

    with engine.begin() as conn:
        for table in ('accounts', 'debt_accounts'):
            if 'portal_url' in cols(table):
                conn.execute(text(f'ALTER TABLE {table} DROP COLUMN portal_url'))
        conn.execute(text("UPDATE app_settings SET value = :v WHERE key = 'schema_version'"),
                     {'v': prior_version})
    dropped = 'portal_url' not in cols('accounts') and 'portal_url' not in cols('debt_accounts')
    migrate.run_migration_if_needed()
    restored = 'portal_url' in cols('accounts') and 'portal_url' in cols('debt_accounts')
    return dropped, restored


# ── F1 / F13 / s5.1: the crossing test ────────────────────────────────────────
_PAGE_CALLS = ('evaluate_js', 'run_js', 'get_elements', 'get_cookies', 'load_html', 'load_url',
               '.dom', 'expose(', 'state.')
_FORBIDDEN_IMPORTS = ('server', 'core', 'GroundworkAPI', '_GW_TOKEN', 'urllib.request', 'http.client',
                      'requests', 'socket', 'sqlite3', 'sqlalchemy')
_ENGINE_ESCAPES = ('mshtml', "'cef'", 'qtwebengine', 'qtwebkit', 'PyQt', 'PySide', 'cefpython',
                   'WEBVIEW2_RUNTIME_PATH', 'PYWEBVIEW_GUI', 'MicrosoftEdgeWebview2Setup', 'fwlink')


def _crossing_violations(src, launch_src='', server_src=''):
    """Every way the bank window's source crosses the ruled boundary. Empty when clean."""
    v = []
    code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))
    body = code.split('"""', 2)[2] if code.count('"""') >= 2 else code   # past the module docstring
    for call in _PAGE_CALLS:
        if call in body:
            v.append(f'page interaction: {call}')
    if re.search(r'js_api\s*=', body):
        v.append('js_api set on the bank window')
    for mod in _FORBIDDEN_IMPORTS:
        if re.search(rf'^\s*(from|import)\s+{re.escape(mod)}\b', body, re.M) or \
           re.search(rf'import\s+[^\n]*\b{re.escape(mod)}\b', body):
            v.append(f'imports {mod}')
    if '/api/' in body:
        v.append('reaches a Groundwork endpoint')
    for esc in _ENGINE_ESCAPES:
        if esc in body:
            v.append(f'an alternate engine reachable: {esc}')
    if re.search(r'private_mode\s*=\s*False', body) or 'storage_path' in body:
        v.append('a persistent session')
    if not re.search(r'webview\.start\(.*private_mode=True', body):
        v.append('private_mode not stated True at start')
    expected = re.search(r"_EXPECTED_RENDERER\s*=\s*\{([^}]*)\}", body)
    if not expected or set(re.findall(r":\s*'([^']+)'", expected.group(1))) != \
            {'edgechromium', 'wkwebview', 'gtkwebkit2'}:
        v.append('the accepted renderers are not exactly the three platform engines')
    writes = re.findall(r'stdin\.write\(([^)]*)\)', body)
    if writes != ["url + '\\n'"]:
        v.append(f'something other than the URL goes to the bank process: {writes}')
    says = re.findall(r'_say\(([^)]*)\)', body)
    if not says or any(s not in ('status', 'STATUS_READY', 'STATUS_REFUSED_URL', 'STATUS_REFUSED_ENGINE')
                       for s in says):
        v.append(f'the bank process reports something besides a fixed status: {says}')
    if 'webview.settings[\'ALLOW_DOWNLOADS\'] = True' not in body.split('def child_main', 1)[-1].split('\ndef ', 1)[0]:
        v.append('downloads not enabled in the bank process alone')
    if re.search(r"ALLOW_DOWNLOADS['\"]\]\s*=\s*True", launch_src + server_src):
        v.append('downloads enabled in the main process')
    child = body.split('def child_main', 1)[-1].split('\ndef ', 1)[0]   # to the next top-level def
    threads = re.findall(r'Thread\(target=([A-Za-z_]+)', child)
    if threads != ['_close_when_parent_goes']:
        v.append(f'something runs beside the page in the bank process: {threads}')
    watcher = child.split('def _close_when_parent_goes', 1)[-1].split('threading.Thread', 1)[0]
    if re.search(r'window\.(?!destroy\b)\w+', watcher):
        v.append('the parent-watcher acts on the window beyond closing it')
    return v


_MUTATIONS = [
    ('js_api set on the bank window',
     "        width=1100,\n", "        width=1100,\n        js_api=object(),\n"),
    ('evaluate_js to fill credentials',
     "    _say(STATUS_READY)\n", "    window.evaluate_js('document.forms[0].password.value=1')\n    _say(STATUS_READY)\n"),
    ('the page\'s cookies read',
     "    _say(STATUS_READY)\n", "    window.get_cookies()\n    _say(STATUS_READY)\n"),
    ('a DOM read',
     "    _say(STATUS_READY)\n", "    window.dom.get_elements('input')\n    _say(STATUS_READY)\n"),
    ('an automation action beside the page',
     "    threading.Thread(target=_close_when_parent_goes, daemon=True).start()\n",
     "    threading.Thread(target=_close_when_parent_goes, daemon=True).start()\n"
     "    threading.Thread(target=_click_download, daemon=True).start()\n"),
    ('the bank process imports the server',
     "import threading\n", "import threading\nimport server\n"),
    ('account data passed to the bank process',
     "        proc.stdin.write(url + '\\n')\n", "        proc.stdin.write(url + '\\n')\n        proc.stdin.write(account_name + '\\n')\n"),
    ('downloaded content handed to the page',
     "    _say(STATUS_READY)\n", "    window.state.statement = open(path).read()\n    _say(STATUS_READY)\n"),
    ('a download delivered by POST rather than the filesystem',
     "import threading\n", "import threading\nimport urllib.request  # POST the file to /api/auto-import/queue\n"),
    ('a persistent session',
     "private_mode=True)", "private_mode=False)"),
    ('MSHTML accepted as a renderer',
     "'win32': 'edgechromium', 'darwin': 'wkwebview'", "'win32': 'mshtml', 'darwin': 'wkwebview'"),
    ('an alternate engine made reachable',
     "    import webview\n", "    import webview\n    webview.settings['WEBVIEW2_RUNTIME_PATH'] = 'C:/bundled/webview2'\n"),
    ('the page reports back through the status channel',
     "    _say(STATUS_READY)\n", "    _say(window.get_current_url())\n"),
]


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    import server
    import bank_window

    # F4
    results, stored = _f4(c, H, c.post('/api/accounts', headers=H, json={'name': 's126 F4'}).get_json()['data']['id'])
    for url, ok in results.items():
        check(f's126 F4 {"accepted" if dict(F4_CASES)[url] else "refused"}: {url or "(empty - clears the link)"}', ok)
    check('s126 F4 an explicit :443 is dropped and nothing else rewritten (last accepted value stored)',
          stored == 'https://bank.com/login')
    check('s126 F4 the child re-checks the link at launch, whatever the parent did',
          'if portal_url_problem(url):' in ctx.BASE.joinpath('bank_window.py').read_text(encoding='utf-8')
          .split('def child_main', 1)[1][:400])

    # F3
    for name, ok in _f3(c, H, ctx.dbs).items():
        check(f's126 F3 {name}', ok)

    # F5
    acct = c.post('/api/accounts', headers=H, json={'name': 's126 Sentinel'}).get_json()['data']
    c.put(f"/api/accounts/{acct['id']}/portal", headers=H, json={'url': SENTINEL_A})
    card = c.post('/api/debt', headers=H, json={'name': 's126 Sentinel card'}).get_json()['data']
    c.patch(f"/api/debt/{card['id']}", headers=H, json={'linked_account_id': None})
    c.put(f"/api/debt/{card['id']}/portal", headers=H, json={'url': SENTINEL_C})
    check('s126 F5 the sentinels are stored (the sweep below is not vacuous)',
          c.get(f"/api/accounts/{acct['id']}/portal", headers=H).get_json()['data']['url'] == SENTINEL_A
          and c.get(f"/api/debt/{card['id']}/portal", headers=H).get_json()['data']['url'] == SENTINEL_C)
    from server import create_app
    app = create_app()
    swept, leaks = _f5_sweep(c, H, app)
    check(f's126 F5 the link appears in none of the {swept} other GET answers (network blocked)',
          swept >= 70 and not leaks)
    for url in leaks[:8]:
        print(f'        leaked by {url}')
    check('s126 F5 has_portal is a boolean in the serializers',
          any(a.get('id') == acct['id'] and a.get('has_portal') is True
              for a in c.get('/api/accounts/with-balances', headers=H).get_json()['data']))
    touchers = _portal_touchers(ctx.server_src)
    check('s126 F5 portal_url is touched in server.py only by the named functions',
          touchers == PORTAL_READERS)
    if touchers != PORTAL_READERS:
        print(f'        unexpected: {sorted(touchers - PORTAL_READERS)}  missing: {sorted(PORTAL_READERS - touchers)}')
    check('s126 F5 app.js never holds the address in state (no portal_url anywhere in it)',
          'portal_url' not in ctx.app_src)

    # F5 mutation: the serializer made to carry the address
    real_ser = server._serialize_account
    try:
        server._serialize_account = lambda a, session=None: dict(real_ser(a, session),
                                                                 portal_url=getattr(a, 'portal_url', None))
        _, leaked = _f5_sweep(c, H, app)
    finally:
        server._serialize_account = real_ser
    check('s126 F5 mutation caught: the address carried by the account serializer', bool(leaked))

    # F3 mutation: unlinking copies the account's link onto the card
    real_relink = server._relink_card_portal
    def copies(session, debt, new_id, keep=None):
        prev = session.get(server.Account, debt.linked_account_id) if debt.linked_account_id else None
        r = real_relink(session, debt, new_id, keep)
        if not new_id and prev is not None:
            debt.portal_url = prev.portal_url
        return r
    try:
        server._relink_card_portal = copies
        caught = not all(_f3(c, H, ctx.dbs).values())
    finally:
        server._relink_card_portal = real_relink
    check('s126 F3 mutation caught: unlinking copies the account\'s link', caught)

    # F4 mutation: http admitted
    real_problem = bank_window.portal_url_problem
    try:
        bank_window.portal_url_problem = lambda u: None if (u or '').startswith('http://') else real_problem(u)
        r, _ = _f4(c, H, c.post('/api/accounts', headers=H, json={'name': 's126 F4m'}).get_json()['data']['id'])
    finally:
        bank_window.portal_url_problem = real_problem
    check('s126 F4 mutation caught: http admitted', not all(r.values()))

    # F7
    tmp = Path(tempfile.mkdtemp(prefix='s126_'))
    f7 = _f7(c, H, server, tmp)
    for name, ok in f7.items():
        check(f's126 F7 {name}', ok)
    real_offered = server._offered_statements
    class _Everything(set):
        def __contains__(self, _item):
            return True
    try:
        server._offered_statements = _Everything()
        caught = not all(_f7(c, H, server, tmp).values())
    finally:
        server._offered_statements = real_offered
    check('s126 F7 mutation caught: any statement served whether offered or not', caught)

    # F2
    for name, ok in _f2(c, H, tmp).items():
        check(f's126 F2 {name}', ok)

    # F6
    for name, ok in _f6(tmp).items():
        check(f's126 F6 {name}', ok)
    launch_src = ctx.BASE.joinpath('launch.py').read_text(encoding='utf-8')
    check('s126 F6 the watcher asks the shared resolver, not Path.home()/Downloads',
          'downloads = downloads_dir()' in launch_src and "Path.home() / 'Downloads'" not in launch_src)
    check("s126 F6 the delete route and the statement route share the resolver",
          ctx.server_src.count('_in_downloads(') >= 4 and "P.home() / 'Downloads'" not in ctx.server_src)

    # The upgrade path, and its mutation: the version left unbumped
    import migrate
    dropped, restored = _upgrade('20260914-plan-identity')
    check('s126 upgrade: a database at the previous schema version gains both portal_url columns on start',
          dropped and restored)
    real_version = migrate.SCHEMA_VERSION
    try:
        migrate.SCHEMA_VERSION = '20260914-plan-identity'
        m_dropped, m_restored = _upgrade('20260914-plan-identity')
    finally:
        migrate.SCHEMA_VERSION = real_version
        _upgrade('20260914-plan-identity')      # leave the database as found
    check('s126 upgrade mutation caught: the columns added with SCHEMA_VERSION left unbumped',
          m_dropped and not m_restored)

    # F1 / F13 / s5.1 - the crossing test
    src = ctx.BASE.joinpath('bank_window.py').read_text(encoding='utf-8')
    baseline = _crossing_violations(src, launch_src, ctx.server_src)
    check('s126 crossing: bank_window.py is inside the boundary as built', not baseline)
    for item in baseline:
        print(f'        {item}')
    check('s126 crossing: --bank-window is dispatched before anything else starts',
          launch_src.index("if '--bank-window' in sys.argv[1:]") < launch_src.index('logging.basicConfig(', launch_src.index('def main():')))
    for label, old, new in _MUTATIONS:
        mutated = src.replace(old, new, 1)
        applied = mutated != src
        check(f's126 crossing mutation caught: {label}',
              applied and bool(_crossing_violations(mutated, launch_src, ctx.server_src)))
    main_dl = launch_src.replace("    import atexit\n", "    webview.settings['ALLOW_DOWNLOADS'] = True\n    import atexit\n", 1)
    check('s126 crossing mutation caught: downloads enabled in the main process',
          main_dl != launch_src and bool(_crossing_violations(src, main_dl, ctx.server_src)))
