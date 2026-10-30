"""H2: after a successful import, the user's Downloads copy may go to the Recycle Bin - at the user's word.

`gw 2.0/SOURCE_DOCUMENT_CUSTODY.md` s4 H2, authorised as its own build by Rob's ruling (s8, 2026-09-25). A
Downloads-tidiness act on the user's own file: it retains nothing and ends no Groundwork custody (Groundwork never
had the file). "Always remove" is a Downloads policy, never a retention policy.

    the route's guards   inside Downloads only; a bank file or statement only; a well-formed hash only; ONLY a
                         file that was imported (an H1 import_committed event from the watcher for exactly these
                         bytes); a file changed since import (a newer download, same name) is left alone; gone is
                         reported, not an error
    Recycle Bin only     removal goes through recycle_bin.send_to_recycle_bin; when that is unavailable the file is
                         left exactly where it was - recycle_bin.py contains no permanent-delete call at all
    recorded             a 'download_removed' Historian event, one-off or standing, touched by its writer alone
    the page             the offer comes only after a successful commit; "Always" is per kind and written only by its
                         button and its Settings checkbox - never inferred; nothing is retained

The Recycle Bin itself is replaced here by a stand-in that moves the file into a temp "bin", so the gate never
touches the real one. The real Windows Recycle Bin was measured when this was built (the build note).

Mutations, each of which must fail a case: the import check skipped; the hash check skipped; a permanent-delete
fallback when the Recycle Bin is unavailable; the event read by a prompt-building function; "Always" inferred from
repeated removals.
"""
import ast
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path


def _setup(tmp, tag):
    downloads = tmp / f'downloads_{tag}'
    downloads.mkdir(exist_ok=True)
    binned = tmp / f'bin_{tag}'
    binned.mkdir(exist_ok=True)
    return downloads, binned


def _commit(c, HJ, name, sha, origin='watcher', tag=''):
    return c.post('/api/import/commit', headers=HJ, data=json.dumps({
        'records': [{'date': '2026-09-10', 'description': f'S128 {tag} {name}', 'amount': 3.0, 'type': 'debit'}],
        'account_name': f's128 {tag}',
        'source_file': {'name': name, 'sha256': sha, 'origin': origin}}))


def _remove(c, HJ, path, sha, standing=False):
    r = c.post('/api/auto-import/remove-download', headers=HJ,
               data=json.dumps({'path': str(path), 'sha256': sha, 'standing': standing}))
    return r.status_code, (r.get_json() or {}).get('data') or {}


_RUN = [0]


def _cases(c, HJ, dbs, tmp):
    import bank_window
    import recycle_bin
    _RUN[0] += 1
    tag = f'r{_RUN[0]}'
    downloads, binned = _setup(tmp, tag)
    out = {}
    from core.database import Artefact
    with dbs() as s:
        arts_before = s.query(Artefact).count()   # other sections mint artefacts; H2 must add none
    real_dd, real_recycle = bank_window.downloads_dir, recycle_bin.send_to_recycle_bin

    def to_temp_bin(path):
        p = Path(path)
        if not p.is_file():
            return False, 'gone'
        shutil.move(str(p), str(binned / p.name))
        return True, ''

    try:
        bank_window.downloads_dir = lambda: downloads
        recycle_bin.send_to_recycle_bin = to_temp_bin

        f = downloads / f'chase_{tag}.qfx'
        f.write_bytes(b'OFXHEADER:100 ' + tag.encode())
        sha = hashlib.sha256(f.read_bytes()).hexdigest()

        code, d = _remove(c, HJ, f, sha)
        out['a file that was never imported is refused'] = code == 409 and f.exists()
        _commit(c, HJ, f.name, sha, origin='manual', tag=tag)
        code, d = _remove(c, HJ, f, sha)
        out['a hand-picked import does not authorise removing a Downloads file'] = code == 409 and f.exists()
        _commit(c, HJ, f.name, sha, tag=tag)
        code, d = _remove(c, HJ, f, sha, standing=True)
        out['an imported, unchanged file goes to the Recycle Bin'] = (
            code == 200 and d.get('removed') is True and not f.exists() and (binned / f.name).exists())

        code, d = _remove(c, HJ, f, sha)
        out['a file already gone is reported, not an error'] = code == 200 and d.get('reason') == 'gone'

        g2 = downloads / f'visa_{tag}.csv'
        g2.write_bytes(b'Date,Description,Amount\n' + tag.encode())
        sha2 = hashlib.sha256(g2.read_bytes()).hexdigest()
        _commit(c, HJ, g2.name, sha2, tag=tag)
        g2.write_bytes(b'Date,Description,Amount\nNEWER DOWNLOAD ' + tag.encode())
        code, d = _remove(c, HJ, g2, sha2)
        out['a file changed since import (a newer download, same name) is left alone'] = (
            d.get('reason') == 'changed' and g2.exists())

        outside = tmp / f'outside_{tag}.csv'
        outside.write_bytes(b'x')
        code, d = _remove(c, HJ, outside, hashlib.sha256(b'x').hexdigest())
        out['a file outside Downloads is refused'] = code == 403 and outside.exists()

        exe = downloads / f'setup_{tag}.exe'
        exe.write_bytes(b'MZ')
        code, d = _remove(c, HJ, exe, hashlib.sha256(b'MZ').hexdigest())
        out['only bank files and statements can be removed'] = code == 400 and exe.exists()

        h = downloads / f'stmt_{tag}.pdf'
        h.write_bytes(b'%PDF-1.4 ' + tag.encode())
        sha3 = hashlib.sha256(h.read_bytes()).hexdigest()
        _commit(c, HJ, h.name, sha3, tag=tag)
        recycle_bin.send_to_recycle_bin = lambda p: (False, 'recycle_unavailable')
        code, d = _remove(c, HJ, h, sha3)
        out['the Recycle Bin unavailable -> the file is left exactly where it was'] = (
            d.get('reason') == 'recycle_unavailable' and h.exists())

        from core.database import HistorianEntry, Artefact
        with dbs() as s:
            evs = [json.loads(e.context_json) for e in s.query(HistorianEntry).filter_by(event_category='download_removed')]
            arts = s.query(Artefact).count()
        mine = [e for e in evs if e.get('file_name') == f.name]
        out['the removal is recorded once, with its standing choice, and nothing is retained'] = (
            len(mine) == 1 and mine[0].get('standing') is True and mine[0].get('content_sha256') == sha
            and set(mine[0]) == {'file_name', 'content_sha256', 'standing'} and arts == arts_before)
    finally:
        bank_window.downloads_dir, recycle_bin.send_to_recycle_bin = real_dd, real_recycle
    return out


def _fn_touchers(src, needle):
    tree = ast.parse(src)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inner = [n for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not node]
            if not inner and needle in (ast.get_source_segment(src, node) or ''):
                found.add(node.name)
    return found


def _no_permanent_delete(recycle_src):
    code = '\n'.join(l for l in recycle_src.splitlines() if not l.lstrip().startswith('#'))
    body = code.split('"""', 2)[2] if code.count('"""') >= 2 else code
    return not re.search(r'\b(os\.remove|os\.unlink|\.unlink\(|shutil\.rmtree|os\.rmdir)', body)


def _always_writers(app_src):
    """Every place app.js writes a downloads_cleanup_ setting (via _CLEANUP_KEYS)."""
    return re.findall(r'_setDownloadsCleanup\(([^)]*)\)', app_src)


def run(ctx):
    check, c, HJ, dbs = ctx.check, ctx.c, ctx.HJ, ctx.dbs
    import server
    tmp = Path(tempfile.mkdtemp(prefix='s128_'))
    results = _cases(c, HJ, dbs, tmp)
    for name, ok in results.items():
        check(f's128 {name}', ok)
    baseline = all(results.values())

    recycle_src = ctx.BASE.joinpath('recycle_bin.py').read_text(encoding='utf-8')
    check('s128 recycle_bin.py has no permanent-delete call - there is no fallback to deletion',
          _no_permanent_delete(recycle_src))
    check("s128 'download_removed' is touched in server.py by its writer alone - it reaches no prompt",
          _fn_touchers(ctx.server_src, "'download_removed'") == {'_log_download_removed'})

    app = ctx.app_src
    writers = _always_writers(app)
    # app.js writes it in exactly two places (the helper, and the Always button); the page writes it only from
    # the two Settings checkboxes. Anything else writing it is inference.
    check('s128 "Always" is written only by its button and its Settings checkboxes - never inferred',
          sorted(w.strip() for w in writers) == ['kind, on', 'kind, true']
          and "_setDownloadsCleanup('transactions', this.checked)" in ctx.html_src
          and "_setDownloadsCleanup('statements', this.checked)" in ctx.html_src)
    check('s128 "Always" is per kind - bank files and statements are separate settings',
          "transactions: 'downloads_cleanup_transactions'" in app and "statements: 'downloads_cleanup_statements'" in app)
    check('s128 the offer comes only after a successful commit',
          app.index('const data = await API.post(\'/api/import/commit\'') < app.index('if (downloadsFile) _afterImportDownloadsChoice(downloadsFile);'))
    check('s128 the prompt names the file and says the transactions stay',
          'from your Downloads? Your transactions stay in Groundwork.' in app)

    # Mutations - route guards
    src = ctx.server_src

    def mutated_cases(pattern, replacement):
        mutated = src.replace(pattern, replacement, 1)
        if mutated == src:
            return None
        ns = {}
        fn_src = mutated[mutated.index('@auto_import_bp.route(\'/remove-download\''):mutated.index('def _log_download_removed')]
        fn_src = fn_src.split('\n', 1)[1]                       # drop the decorator
        exec(compile(fn_src, 'mutated', 'exec'), server.__dict__, ns)
        app_ = c.application
        endpoint = 'auto_import.auto_import_remove_download'
        real_view = app_.view_functions[endpoint]
        try:
            app_.view_functions[endpoint] = ns['auto_import_remove_download']
            return not all(_cases(c, HJ, dbs, tmp).values())
        finally:
            app_.view_functions[endpoint] = real_view

    m1 = mutated_cases("        if not any(json.loads(e.context_json or '{}').get('origin') == 'watcher' for e in imported):\n            return err('That file has not been imported', 409)\n", "")
    check('s128 mutation caught: the import check skipped', baseline and m1 is True)
    m2 = mutated_cases("        if hashlib.sha256(target.read_bytes()).hexdigest() != sha:\n            return ok({'removed': False, 'reason': 'changed'})\n", "")
    check('s128 mutation caught: the hash check skipped', baseline and m2 is True)

    fallback = recycle_src.replace("    return False, 'recycle_unavailable'\n",
                                   "    os.remove(path)\n    return True, ''\n", 1)
    check('s128 mutation caught: a permanent-delete fallback when the Recycle Bin is unavailable',
          fallback != recycle_src and not _no_permanent_delete(fallback))
    reader = src + "\n\ndef _assistant_context(session):\n    return session.query(1).filter_by(event_category='download_removed')\n"
    check('s128 mutation caught: the event read by a prompt-building function',
          _fn_touchers(reader, "'download_removed'") != {'_log_download_removed'})
    inferred = app.replace("else if (a === 'remove') { await _removeDownload(file, false); }",
                           "else if (a === 'remove') { _removeCount = (_removeCount||0)+1; if (_removeCount >= 3) _setDownloadsCleanup(kind, true); await _removeDownload(file, false); }", 1)
    check('s128 mutation caught: "Always" inferred from repeated removals',
          inferred != app and sorted(w.strip() for w in _always_writers(inferred)) != ['kind, on', 'kind, true'])

    check('s128 the route is left as found',
          c.application.view_functions['auto_import.auto_import_remove_download'] is server.auto_import_remove_download
          and all(_cases(c, HJ, dbs, tmp).values()))

    # Item 33 Q6 (ENGINE_OTHER_PLATFORMS.md section 7): the watcher's library is a requirement, so a build from
    # requirements.txt on a clean machine has it; each spec bundles its own platform's backend
    req = ctx.BASE.joinpath('requirements.txt').read_text(encoding='utf-8')
    backends = {'groundwork.spec': 'watchdog.observers.read_directory_changes',
                'groundwork_linux.spec': 'watchdog.observers.inotify', 'groundwork_macos.spec': 'watchdog.observers.fsevents'}
    check('s128 the Downloads watcher is a requirement, and all three builds carry its backend',
          re.search(r'^watchdog>=', req, re.M) is not None
          and all(f"'{b}'," in ctx.BASE.joinpath(s).read_text(encoding='utf-8') for s, b in backends.items()))
