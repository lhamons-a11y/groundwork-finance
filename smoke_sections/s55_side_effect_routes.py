"""The sixteen routes the sweep in s50 had to skip, tested by doing and undoing.

s50 asks every mutating route to refuse a body it cannot use. Sixteen cannot be
asked that, because they require nothing: an empty body is a valid instruction
to act, and sweeping them there would have meant emptying the transactions
table and downloading a 1.3GB installer to prove they do not crash.

So they are tested here instead, on their own terms, and the isolation comes
from the feature under test. A backup is taken before anything runs and
restored in a finally at the end, which puts the database back exactly as this
section found it - including whatever the destructive checks did to it. That
also means /api/backup/create and /api/backup/restore are not merely asserted
about; the rest of the section depends on them working.

Ordering is deliberate. This is s55 so it runs after every other section, and
the check that empties the transactions table is last inside it.

Two things are deliberately NOT exercised in full, and neither is an oversight:

  /api/settings/export-to-file writes into the real Downloads folder rather
  than the temp data directory, so running it here would drop a file on the
  machine of whoever ran the suite. Only its validation path is checked.

  /api/ai/install-ollama and /api/ai/pull-model are checked with the network
  blocked, which is the interesting half anyway: the installer runs on a
  background thread, so the failure a user actually meets is not an error
  response but a progress state that either reports the failure or spins
  forever.
"""
import io
import socket
import time


def _blocked(*_args, **_kwargs):
    raise OSError('network is blocked for this check')


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core.database import NetWorthSnapshot, Transaction
    from server import _backups_dir, db_session

    def data_of(resp):
        body = resp.get_json() or {}
        return body.get('data') or body

    # The restore point. Everything below can be as destructive as the route
    # it is testing, because this comes back at the end.
    _made = c.post('/api/backup/create', headers=H)
    _restore_point = data_of(_made).get('filename')
    check('a backup can be created, and it names the file it wrote',
          _made.status_code == 200 and bool(_restore_point))
    _backup_file = _backups_dir() / (_restore_point or 'missing')
    check('and the file is on disk and is a real SQLite database, not an empty one',
          _backup_file.exists()
          and _backup_file.read_bytes()[:15] == b'SQLite format 3'
          and _backup_file.stat().st_size > 4096)
    check('the backup list reports the file that was just written',
          any(row.get('filename') == _restore_point
              for row in (data_of(c.get('/api/backup/list', headers=H)) or [])))

    try:
        # ── The settings blob: the app's own save/load path ─────────────────
        # Nothing else in the suite round-trips this, and it is how every
        # preference in the app persists.
        _saved = c.post('/api/save', headers=HJ,
                        json={'settings': {'s55_probe': 'kept'}})
        _loaded = c.get('/api/load', headers=H)
        check('settings saved through /api/save come back from /api/load',
              _saved.status_code == 200
              and (data_of(_loaded).get('settings') or {}).get('s55_probe') == 'kept')

        # ── Restore's guards ────────────────────────────────────────────────
        # This route overwrites the live database with a file named in the
        # request, so its refusals are the security boundary, not a nicety.
        check('restore refuses a request naming no file at all',
              c.post('/api/backup/restore', headers=HJ,
                     json={}).status_code == 400)
        check('restore refuses a path that climbs out of the backups folder',
              c.post('/api/backup/restore', headers=HJ,
                     json={'filename': '../../../etc/passwd'}).status_code == 403)
        check('restore refuses a backup that is not there',
              c.post('/api/backup/restore', headers=HJ,
                     json={'filename': 'no_such_backup.db'}).status_code == 404)

        # A file in the right folder with the right extension and the wrong
        # contents. Without the magic-byte check this would be copied over the
        # live database and the app would come back up on rubble.
        _junk = _backups_dir() / 'groundwork_backup_not_really.db'
        _junk.write_bytes(b'this is not a database, it is a text file')
        check('restore refuses a file in the backups folder that is not a database',
              c.post('/api/backup/restore', headers=HJ,
                     json={'filename': _junk.name}).status_code == 400)
        _junk.unlink()

        check('an upload with no file attached is refused',
              c.post('/api/backup/restore-upload', headers=H).status_code == 400)
        check('and an uploaded file that is not a database is refused too',
              c.post('/api/backup/restore-upload', headers=H,
                     data={'file': (io.BytesIO(b'still not a database'), 'evil.db')},
                     content_type='multipart/form-data').status_code == 400)

        # ── Where backups live ──────────────────────────────────────────────
        _custom = ctx.TMP / 's55_custom_backups'
        _set = c.post('/api/backup/location', headers=HJ,
                      json={'path': str(_custom)})
        check('the backup folder can be pointed somewhere else, and it is created',
              _set.status_code == 200 and data_of(_set).get('is_custom') is True
              and _custom.exists())
        _reset = c.post('/api/backup/location', headers=HJ, json={'path': ''})
        check('and an empty path puts it back to the default rather than clearing it',
              _reset.status_code == 200
              and data_of(_reset).get('is_default') is True)

        check('an export in a format the app does not write is refused',
              c.post('/api/settings/export-to-file', headers=HJ,
                     json={'format': 'xml'}).status_code == 400)

        # ── Offline, which for these three is the normal case ───────────────
        _real_connect, _real_create = socket.socket.connect, socket.create_connection
        try:
            socket.socket.connect = _blocked
            socket.create_connection = _blocked

            check('a model pull with no model named is refused before it reaches '
                  'the network', c.post('/api/ai/pull-model', headers=HJ,
                                        json={}).status_code == 400)
            check('refreshing prices with no connection reports a result rather '
                  'than failing',
                  c.post('/api/investments/prices/refresh',
                         headers=HJ, json={}).status_code == 200)

            # The installer answers immediately because the work is on a
            # thread, so "started" is true and tells the user nothing. What
            # matters is where the thread leaves the progress state: an install
            # that can never finish has to say so, or the UI reports a download
            # in progress until the app is closed.
            _kick = c.post('/api/ai/install-ollama', headers=HJ, json={})
            check('the installer starts on a thread and says so',
                  _kick.status_code == 200
                  and data_of(_kick).get('started') is True)
            _state = {}
            for _ in range(60):                       # ~6s ceiling
                _state = data_of(c.get('/api/ai/install-status', headers=H))
                if _state.get('done') or _state.get('error'):
                    break
                time.sleep(0.1)                       # the work is on a thread
            check('and an install that cannot reach the network ends reported, '
                  'not running forever',
                  bool(_state.get('error')) and _state.get('active') is False)
        finally:
            socket.socket.connect = _real_connect
            socket.create_connection = _real_create

        # ── The bulk operations, which report what they touched ─────────────
        _imported = c.post('/api/import/commit', headers=HJ, json={
            'account_name': 'S55 Import Probe',
            'records': [
                {'date': '2026-08-01', 'amount': 11.0,
                 'description': 'S55 One', 'type': 'debit'},
                {'date': '2026-08-02', 'amount': 22.0,
                 'description': 'S55 Two', 'type': 'debit'},
            ]})
        check('an import with records creates them and reports the count',
              _imported.status_code == 200
              and data_of(_imported).get('created') == 2)
        with db_session() as session:
            _has_imported = session.query(Transaction).filter(
                Transaction.description.like('S55 %')).count()
        check('and they are in the database, not just in the response',
              _has_imported == 2)

        # force, because an earlier section already took this month's snapshot
        # and the route is right to refuse a second one without it. That
        # refusal has its own checks; this is the overwrite path.
        _snap = c.post('/api/net-worth/snapshot', headers=HJ, json={'force': True})
        with db_session() as session:
            _snap_rows = session.query(NetWorthSnapshot).count()
        check('a net-worth snapshot needs no figures of its own and records one',
              _snap.status_code == 200 and _snap_rows >= 1
              and data_of(_snap).get('snapshot', {}).get('month_label'))

        for _url, _field in (('/api/categories/reclassify-income', 'message'),
                             ('/api/categories/smart-backfill', 'message'),
                             ('/api/sinking-funds/auto-credit', 'credited')):
            _resp = c.post(_url, headers=HJ, json={})
            check(f'{_url} runs and reports what it changed',
                  _resp.status_code == 200 and data_of(_resp).get(_field) is not None)

        # ── Last, because it empties the table ──────────────────────────────
        # The route makes its own safety backup before deleting, server-side,
        # so the client cannot skip it. That backup is the assertion: it has to
        # exist, and it has to be good enough to undo what just happened.
        with db_session() as session:
            _before = session.query(Transaction).count()
        _wiped = c.delete('/api/transactions', headers=H)
        _safety = data_of(_wiped).get('backup_filename')
        with db_session() as session:
            _after = session.query(Transaction).count()
        check('deleting every transaction reports the count and empties the table',
              _wiped.status_code == 200 and _before > 0 and _after == 0
              and data_of(_wiped).get('deleted') == _before)
        check('and it took a safety backup first, without being asked to',
              bool(_safety) and (_backups_dir() / _safety).exists())

        _undo = c.post('/api/backup/restore', headers=HJ,
                       json={'filename': _safety})
        with db_session() as session:
            _restored = session.query(Transaction).count()
        check('that safety backup actually brings the transactions back',
              _undo.status_code == 200 and _restored == _before)
        check('and the app is still serving after a restore swapped the file '
              'under it', c.get('/api/health', headers=H).status_code == 200)
    finally:
        # Back to exactly what this section walked in on, whatever happened
        # above - including the probe rows, the settings key and the snapshot.
        c.post('/api/backup/restore', headers=HJ, json={'filename': _restore_point})

    with db_session() as session:
        _left = session.query(Transaction).filter(
            Transaction.description.like('S55 %')).count()
    check('and the section leaves the database as it found it',
          _left == 0
          and (data_of(c.get('/api/load', headers=H)).get('settings') or {})
          .get('s55_probe') is None)
