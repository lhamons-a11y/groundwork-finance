"""H1: every import is recorded in the Historian - a fact about the file, never the file.

`gw 2.0/SOURCE_DOCUMENT_CUSTODY.md` s4 H1, authorised as its own build by Rob's ruling (s8, 2026-09-25). Until now
nothing recorded that an import happened, or from what. The import is a historical event distinct from its source
being retained, so it is recorded whether or not the source is ever kept - and recording it keeps nothing.

    recorded     one 'import_committed' event per commit, in the commit's own transaction: file name, content hash
                 (correspondence, never identity), origin, account, counts, date range
    not an       an empty commit logs nothing; a commit of all duplicates still logs (an import happened)
    honest       a malformed hash is recorded as unknown, never kept as given; no file -> the fields are null, the
                 event still recorded
    not custody  no Artefact is minted, and the event carries a fixed set of keys - never the file's content (C3:
                 captured value != captured source)
    no model     'import_committed' is read by nothing in server.py but the commit that writes it, so a filename
                 that carries account digits reaches no prompt
    the hash     the watcher hashes the RAW bytes on disk, which the page cannot (it rebuilds a File from decoded
                 text); a statement's bytes stay unread by the watcher, as F7 ruled

Then the crossing mutations, each of which must fail at least one case: the file's content put into the event; an
Artefact minted by the commit; the event read by a prompt-building function.
"""
import hashlib
import json
import re
import tempfile
from pathlib import Path

_KEYS = {'file_name', 'content_sha256', 'origin', 'account_id', 'account_name', 'records', 'created',
         'duplicates', 'held', 'errors', 'first_date', 'last_date'}     # 'held': item 93 B5
_RUN = [0]


def _events(dbs):
    from core.database import HistorianEntry
    with dbs() as s:
        return [json.loads(e.context_json or '{}') for e in
                s.query(HistorianEntry).filter_by(event_category='import_committed').order_by(HistorianEntry.id)]


def _artefacts(dbs):
    from core.database import Artefact
    with dbs() as s:
        return s.query(Artefact).count()


def _cases(c, HJ, dbs):
    _RUN[0] += 1
    n = _RUN[0]
    out = {}
    acct = f's127 Checking {n}'
    body = lambda recs, src=None: json.dumps({'records': recs, 'account_name': acct,
                                              **({'source_file': src} if src is not None else {})})
    recs = [{'date': '2026-09-02', 'description': f'S127 COFFEE {n}', 'amount': 4.5, 'type': 'debit'},
            {'date': '2026-09-01', 'description': f'S127 PAYROLL {n}', 'amount': 900.0, 'type': 'credit'}]
    good = hashlib.sha256(b's127 bytes').hexdigest()

    before, arts = len(_events(dbs)), _artefacts(dbs)
    r = c.post('/api/import/commit', headers=HJ,
               data=body(recs, {'name': 'chase_sept.qfx', 'sha256': good, 'origin': 'watcher'}))
    ev = _events(dbs)
    e = ev[-1] if len(ev) == before + 1 else {}
    out['one import_committed event per commit'] = r.status_code == 200 and len(ev) == before + 1
    out['the event records the file, the account, the counts and the date range'] = (
        e.get('file_name') == 'chase_sept.qfx' and e.get('content_sha256') == good and e.get('origin') == 'watcher'
        and e.get('account_name') == acct and e.get('records') == 2 and e.get('created') == 2
        and e.get('duplicates') == 0 and e.get('first_date') == '2026-09-01' and e.get('last_date') == '2026-09-02')
    out['the event carries only its fixed keys - never content'] = set(e) == _KEYS
    out['no Artefact is minted - recording an import retains nothing'] = _artefacts(dbs) == arts

    before = len(_events(dbs))
    c.post('/api/import/commit', headers=HJ,
           data=body(recs, {'name': 'chase_sept.qfx', 'sha256': good, 'origin': 'watcher'}))
    ev = _events(dbs)
    # Item 93 B5: lines that only look alike (no bank id) are held for the person, never dropped - and counted.
    out['a commit of all look-alikes is still an import, and is recorded with what it held'] = (
        len(ev) == before + 1 and ev[-1].get('created') == 0 and ev[-1].get('held') == 2)

    before = len(_events(dbs))
    c.post('/api/import/commit', headers=HJ, data=body([], {'name': 'empty.csv'}))
    out['an empty commit is not an import, and records nothing'] = len(_events(dbs)) == before

    before = len(_events(dbs))
    c.post('/api/import/commit', headers=HJ,
           data=body([{'date': '2026-09-03', 'description': f'S127 BAD HASH {n}', 'amount': 1.0, 'type': 'debit'}],
                     {'name': 'x.csv', 'sha256': 'not-a-hash', 'origin': 'somewhere'}))
    ev = _events(dbs)
    out['a malformed hash or origin is recorded as unknown, never kept as given'] = (
        len(ev) == before + 1 and ev[-1].get('content_sha256') is None and ev[-1].get('origin') is None)

    before = len(_events(dbs))
    c.post('/api/import/commit', headers=HJ,
           data=body([{'date': '2026-09-04', 'description': f'S127 NO FILE {n}', 'amount': 2.0, 'type': 'debit'}]))
    ev = _events(dbs)
    out['no file reported -> the event is still recorded, its file fields null'] = (
        len(ev) == before + 1 and ev[-1].get('file_name') is None and ev[-1].get('content_sha256') is None)
    return out


def _readers(server_src):
    """Every function in server.py that mentions 'import_committed' (the writer is expected)."""
    import ast
    tree = ast.parse(server_src)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inner = [n for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not node]
            if not inner and "'import_committed'" in (ast.get_source_segment(server_src, node) or ''):
                found.add(node.name)
    return found


def run(ctx):
    check, c, HJ, dbs = ctx.check, ctx.c, ctx.HJ, ctx.dbs
    import server
    import launch

    results = _cases(c, HJ, dbs)
    for name, ok in results.items():
        check(f's127 {name}', ok)
    baseline = all(results.values())

    # Its writer, and H2's removal route, which reads it only to confirm a Downloads file really was imported
    # (provenance, never a prompt). Any other reader fails here - that is how H2's arrival was surfaced.
    readers = _readers(ctx.server_src)
    check("s127 'import_committed' is touched in server.py by its writer and H2's import check alone - it reaches no prompt",
          readers == {'_log_import_committed', 'auto_import_remove_download',
                      'bank_agent_history',    # item 57 A11: joins a fetch to its import by hash, for display only
                      '_account_balance_facts'})   # item 68 B6: when an account's transactions last came in (time + id only)

    # The watcher: the raw-bytes hash for a transaction file; a statement's bytes unread.
    tmp = Path(tempfile.mkdtemp(prefix='s127_'))
    csv = tmp / 'bank_s127.csv'
    raw = 'Date,Description,Amount\n09/01/2026,CAFÉ S127,-1.00\n'.encode('cp1252')
    csv.write_bytes(raw)
    pdf = tmp / 'statement_s127.pdf'
    pdf.write_bytes(b'%PDF-1.4 s127')
    posted = []
    real_post = launch._post_queue_item
    try:
        launch._post_queue_item = lambda item: posted.append(item) or True
        launch._queue_import_file(csv, {})
        launch._queue_import_file(pdf, {})
    finally:
        launch._post_queue_item = real_post
    by_kind = {p.get('kind', 'file'): p for p in posted}
    check('s127 the watcher sends the hash of the RAW bytes on disk (cp1252 here, not the decoded text)',
          by_kind.get('file', {}).get('sha256') == hashlib.sha256(raw).hexdigest()
          and hashlib.sha256(raw).hexdigest() != hashlib.sha256(raw.decode('cp1252').encode('utf-8')).hexdigest())
    check("s127 a statement's bytes stay unread by the watcher - no hash, no content (F7)",
          'sha256' not in by_kind.get('statement', {'sha256': 1}) and 'content' not in by_kind.get('statement', {}))
    r = c.post('/api/auto-import/queue', headers=HJ,
               data=json.dumps({'filename': 'q.csv', 'content': 'a,b\n', 'path': '', 'sha256': 'ZZ'}))
    item = c.get('/api/auto-import/pending', headers=ctx.H).get_json().get('data') or {}
    check('s127 the queue keeps only a well-formed hash', r.status_code == 200 and item.get('sha256') is None)
    check('s127 the page sends name, hash and origin with the commit, and a picked file is hashed from its own bytes',
          'const sourceFile = await _importSourceFile();' in ctx.app_src
          and 'source_file:  sourceFile,' in ctx.app_src and 'await _sha256Hex(_importFile)' in ctx.app_src)

    # Mutations
    real_log = server._log_import_committed

    def with_content(session, source, *a, **k):
        entry = real_log(session, source, *a, **k)
        from core.database import HistorianEntry
        last = session.query(HistorianEntry).filter_by(event_category='import_committed') \
                      .order_by(HistorianEntry.id.desc()).first()
        ctx_ = json.loads(last.context_json)
        ctx_['content'] = 'Date,Description,Amount\n...'
        last.context_json = json.dumps(ctx_)
        return entry

    def mints_artefact(session, *a, **k):
        from core.database import Artefact
        session.add(Artefact(held=True, content_hash=None))
        return real_log(session, *a, **k)

    caught = {}
    for label, fn in (('the file content put into the event', with_content),
                      ('an Artefact minted by the commit', mints_artefact)):
        try:
            server._log_import_committed = fn
            caught[label] = not all(_cases(c, HJ, dbs).values())
        finally:
            server._log_import_committed = real_log
    for label, ok in caught.items():
        check(f's127 mutation caught: {label}', baseline and ok)

    reader_src = ctx.server_src + "\n\ndef _narrator_context(session):\n    return session.query(1).filter_by(event_category='import_committed')\n"
    check('s127 mutation caught: the event read by a prompt-building function',
          _readers(reader_src) != {'_log_import_committed', 'auto_import_remove_download', 'bank_agent_history'})

    check('s127 the writer is left as found', server._log_import_committed is real_log and all(_cases(c, HJ, dbs).values()))
