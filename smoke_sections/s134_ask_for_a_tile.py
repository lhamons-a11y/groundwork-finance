"""Ask for a tile, first slice (`gw 2.0/ASK_FOR_A_TILE.md`, item 28, ruled 2026-10-01 with build requirements R1-R7).

    K1  a closed catalogue - the seven defaults and net worth over time; nothing else can become a tile
    K2  the request only matches, by its words; the user confirms with /add
    K3  an entry the record can't back says what it needs
    K4  no match is an honest no; the words are kept, visible, deletable, read by nothing else and sent nowhere
    R1  one source for the tile list - the server's catalogue; the page keeps no copy
    R2  a parameterised or unknown id is refused - the catalogue stays closed in practice
    R3  a chosen tile that loses its evidence says what it needs, in place
    R4  the BANNED lexicon covers Groundwork's words - the user's are marked as theirs
    R5  kept requests capped in length and count, and escaped on the page
    R6  additions merge into the latest stored layout - two quick ones cannot overwrite each other
    R7  the model matcher is NOT in this slice (K7) - no model call on this path
"""
import ast
import json
import re
import shutil
import subprocess


class _FakeQuery:
    def __init__(self, n):
        self.n = n

    def count(self):
        return self.n


class _FakeSession:
    def __init__(self, n):
        self.n = n

    def query(self, *_a):
        return _FakeQuery(self.n)


def _node(base):
    node = shutil.which('node')
    if not node:
        return None
    path = str(base.joinpath('static/js/teaching/tiletext.js')).replace('\\', '/')
    prog = f"""
const T = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), date: s => s}};
const out = {{}};
out.backed = T.netWorth({{backed: true, points: [{{date: '2026-01-31', net_worth: 10000}}, {{date: '2026-08-31', net_worth: 12500}}]}}, F);
out.down = T.netWorth({{backed: true, points: [{{date: '2026-01-31', net_worth: 10000}}, {{date: '2026-08-31', net_worth: 9000}}]}}, F).lines[1];
out.needs = T.netWorth({{backed: false, needs: 'Net worth over time needs at least two net worth snapshots; you have 1.'}}, F);
out.banned = T.banned(out.backed.lines.join(' ') + ' ' + out.backed.source + ' ' + out.down);
console.log(JSON.stringify(out));
"""
    r = subprocess.run([node, '-e', prog], capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', r.stderr[:400])
        return {}


def _readers(server_src, key):
    tree = ast.parse(server_src)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            inner = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef) and n is not node]
            if not inner and f"'{key}'" in (ast.get_source_segment(server_src, node) or ''):
                found.add(node.name)
    return found


def run(ctx):
    check, c, HJ = ctx.check, ctx.c, ctx.HJ
    base = ctx.BASE
    import server
    from core.database import NetWorthSnapshot

    def post(path, body):
        r = c.post(path, headers=HJ, data=json.dumps(body))
        return r.status_code, ((r.get_json() or {}).get('data') or (r.get_json() or {}))

    # K1 / R1 - one closed list, read by the page.
    cat_ids = [e['id'] for e in server.TILE_CATALOGUE]
    check('s134 K1 the catalogue is the seven defaults plus net worth over time - closed, written in code',
          cat_ids == list(server.DASHBOARD_TILES) + ['gwNetWorthTrendCard'])
    p = (c.get('/api/dashboard/prefs', headers=HJ).get_json() or {}).get('data') or {}
    check('s134 R1 /prefs gives the user\'s tiles and every title from the catalogue (the page\'s one source)',
          p.get('tiles', [])[:7] == list(server.DASHBOARD_TILES) and p.get('titles', {}).get('gwNetWorthTrendCard') == 'Net worth over time')
    dash = base.joinpath('static/js/teaching/dashboard.js').read_text(encoding='utf-8')
    check('s134 R1 dashboard.js keeps no copy of the tile list or titles',
          'NAMES' not in dash and 'What changed since last month' not in dash and '_prefs.titles' in dash)

    # K2 - matching, by words only.
    m = server.match_tile_request
    check('s134 Ak1 "show my net worth over time" matches Net worth over time', (m('show my net worth over time') or {}).get('id') == 'gwNetWorthTrendCard')
    check('s134 Ak7 "upcoming bills" matches the Coming up tile', (m('show my upcoming bills') or {}).get('id') == 'dashUpcomingCard')
    check('s134 Ak4 "my credit score" matches nothing', m('my credit score') is None)
    check('s134 a single shared everyday word is not a match ("dining by month")', m('dining by month') is None)

    # K3 / R3 - evidence, through a session whose snapshot count is known.
    ok1, needs1 = server._tile_evidence(_FakeSession(1), 'gwNetWorthTrendCard')
    ok3, needs3 = server._tile_evidence(_FakeSession(3), 'gwNetWorthTrendCard')
    check('s134 K3 / Ak2 with one snapshot the entry is not backed, and says what it needs',
          ok1 is False and needs1 == 'Net worth over time needs at least two net worth snapshots; you have 1.'
          and ok3 is True and needs3 is None)
    with ctx.dbs() as s:
        n = s.query(NetWorthSnapshot).count()
    code, d = post('/api/dashboard/add', {'id': 'gwNetWorthTrendCard'})
    if n < 2:
        check('s134 K3 /add refuses an entry the record does not back (409) with its needs', code == 409)
        with ctx.dbs() as s:
            for i in range(2 - n):
                s.add(NetWorthSnapshot(snapshot_date=f'2026-0{i + 1}-28', net_worth=1000.0 * (i + 1)))
            s.commit()
        code, d = post('/api/dashboard/add', {'id': 'gwNetWorthTrendCard'})
    check('s134 Ak1 confirming adds the tile to the user\'s own tiles', code == 200 and 'gwNetWorthTrendCard' in d.get('added', []))
    r = c.get('/api/dashboard/tile/net-worth', headers=HJ)
    t = (r.get_json() or {}).get('data') or {}
    check('s134 the net worth tile is computed from the snapshots on record', t.get('backed') is True and len(t.get('points', [])) >= 2)
    real = server._tile_evidence
    try:
        server._tile_evidence = lambda session, tid: (False, 'Net worth over time needs at least two net worth snapshots; you have 0.')
        t = (c.get('/api/dashboard/tile/net-worth', headers=HJ).get_json() or {}).get('data') or {}
    finally:
        server._tile_evidence = real
    p = (c.get('/api/dashboard/prefs', headers=HJ).get_json() or {}).get('data') or {}
    check('s134 R3 a chosen tile that loses its evidence stays the user\'s and says what it needs',
          t == {'backed': False, 'needs': 'Net worth over time needs at least two net worth snapshots; you have 0.'}
          and 'gwNetWorthTrendCard' in p.get('tiles', []))

    # R2 - closed in practice.
    code, _ = post('/api/dashboard/add', {'id': 'cat:Dining'})
    code2, _ = post('/api/dashboard/add', {'id': 'anything-at-all'})
    r = c.put('/api/dashboard/layout', headers=HJ, data=json.dumps({'order': ['cat:Dining'], 'pinned': [], 'hidden': []}))
    check('s134 R2 a parameterised or unknown id is refused by /add and by the layout', code == 400 and code2 == 400 and r.status_code == 400)

    # Ak7 + R6 - asking for a hidden default shows it; additions merge into the latest layout.
    c.put('/api/dashboard/layout', headers=HJ, data=json.dumps({'order': [], 'pinned': [], 'hidden': ['dashUpcomingCard']}))
    code_a, _ = post('/api/dashboard/add', {'id': 'dashUpcomingCard'})
    code_b, lay = post('/api/dashboard/add', {'id': 'gwNetWorthTrendCard'})
    check('s134 Ak7 / R6 the hidden tile is shown again, and the earlier addition survives the later one',
          code_a == 200 and code_b == 200 and 'dashUpcomingCard' not in lay.get('hidden', [])
          and 'gwNetWorthTrendCard' in lay.get('added', []))
    r = c.put('/api/dashboard/layout', headers=HJ, data=json.dumps({'order': ['gwNetWorthTrendCard'], 'pinned': ['gwNetWorthTrendCard'], 'hidden': []}))
    check('s134 K5 an added tile is arranged like the seven, and the layout cannot drop what was added',
          r.status_code == 200 and 'gwNetWorthTrendCard' in ((r.get_json() or {}).get('data') or {}).get('added', []))

    # K4 / R5 - no match is kept, capped, deletable.
    code, d = post('/api/dashboard/ask', {'text': 'my credit score'})
    kept = d.get('requests', [])
    check('s134 Ak4 no match: an honest no, and the words are kept with their date', code == 200 and d.get('match') is None
          and d.get('kept') is True and kept and kept[-1]['text'] == 'my credit score')
    code, d = post('/api/dashboard/ask', {'text': 'x' * 500 + ' credit'})
    check('s134 R5 a kept request is capped at 200 characters', len(d.get('requests', [{}])[-1].get('text', '')) == 200)
    for i in range(55):
        _, d = post('/api/dashboard/ask', {'text': f'no such tile {i}'})
    check('s134 R5 the kept list is capped at 50', len(d.get('requests', [])) == 50)
    last = d['requests'][-1]
    _, d = post('/api/dashboard/requests/delete', {'at': last['at'], 'text': last['text']})
    check('s134 Ak8 the user deletes their own request; nothing else changes', all(r['text'] != last['text'] for r in d.get('requests', [])))
    check('s134 K4 kept requests are read by nothing but the routes that keep, show and delete them',
          _readers(ctx.server_src, 'dashboard_tile_requests') == {'dashboard_ask', 'dashboard_delete_request', 'dashboard_prefs'})

    ask = base.joinpath('static/js/teaching/asktile.js').read_text(encoding='utf-8')
    check('s134 R4 / R5 the user\'s words are escaped and marked as theirs, so the lexicon never reads them as Groundwork\'s',
          '<span data-gw-user-words' in ask and 'esc(r.text)' in ask)
    check('s134 K4 the page sends the requests nowhere - only the dashboard\'s own endpoints are called',
          set(re.findall(r"API\.(?:get|put|post)\('([^']+)'", ask)) == {
              '/api/dashboard/ask', '/api/dashboard/add', '/api/dashboard/requests/delete', '/api/dashboard/tile/net-worth'})
    check('s134 R7 / K7 no model call in this first slice', '/api/ai' not in ask and '_ai_' not in ask)
    # Found in the page run: the app's own monthly net worth snapshot stores 'YYYY-MM', and a day-only formatter
    # showed it as "Invalid Date". Run the page's own formatter on both shapes.
    node = shutil.which('node')
    if node:
        fn = ask.split('function _date(iso) {', 1)[1].split(chr(10) + '  }' + chr(10), 1)[0]
        prog = ('function _date(iso) {' + fn + chr(10) + '}' + chr(10)
                + 'console.log(JSON.stringify([_date("2026-10"), _date("2026-08-31")]));')
        res = subprocess.run([node, '-e', prog], capture_output=True, text=True, timeout=30).stdout.strip()
        check('s134 a month-only snapshot date reads as a month, a day as a day - never "Invalid Date"',
              'Invalid' not in res and res.count('2026') == 2 and 'Oct' in res)

    o = _node(base)
    check('s134 node is available to run the tile\'s words (skip the next if not)', o is not None)
    if o is not None:
        check('s134 the net worth tile states latest, first and the change - a fall said with its sign',
              o['backed']['lines'] == ['Net worth: $12500.00 on 2026-08-31.',
                                       'First saved: $10000.00 on 2026-01-31 - a change of +$2500.00 across 2 snapshots.']
              and 'a change of -$1000.00' in o['down'])
        check('s134 R3 the needs line in place of figures', o['needs']['lines'] == ['Net worth over time needs at least two net worth snapshots; you have 1.'])
        check('s134 R4 Groundwork\'s words on the tile carry no verdict', o['banned'] == [])
