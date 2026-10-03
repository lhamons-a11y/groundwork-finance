"""Upgrade real old schemas (gw 2.0/SCHEMA_PIN_MODELS.md, item 24, P2/P3; Rob 2026-10-03).

Every smoke run starts from a fresh database, which the migration builds from scratch - so the gate never saw what an
existing user's database is like. tests/schema/ keeps the exact CREATE statements a database had at a recorded
SCHEMA_VERSION (v1.1.0's released schema, and every version since that a bump moved from). This section builds each
one, stamps its version, runs TODAY's migration, and requires every model table and column to exist afterwards.

That is the only check that sees a column added to an existing model but not to its _NEW_*_COLUMNS list: create_all
never alters an existing table, so such a column never reaches an upgraded database - even with a bump. s51 pins the
version; this proves what the version promises.

Each upgrade runs in its own process with its own throwaway data folder: the gate's own database and imports never
take part (test the feature across processes).
"""
import json
import os
import subprocess
import sys
import tempfile

UPGRADE = r"""
import json, os, sqlite3, sys
sys.path.insert(0, os.getcwd())
fixture, mutation = sys.argv[1], sys.argv[2]
sql = open(fixture, encoding='utf-8').read()
version = sql.splitlines()[0].split(': ', 1)[1].strip()
from core import database as d
con = sqlite3.connect(str(d.DB_PATH))
con.executescript(sql)
con.execute("INSERT INTO app_settings (key, value) VALUES ('schema_version', ?)", (version,))
con.commit(); con.close()
import migrate
from sqlalchemy import Column, Integer, String, Table
if mutation == 'unlisted_column':          # a model column added AND bumped, but never listed: create_all won't add it
    d.Base.metadata.tables['app_settings'].append_column(Column('s67_probe_column', String(4)))
    migrate.SCHEMA_VERSION = 's67-a-bump'
elif mutation == 'unbumped_table':         # a model table added with no bump: the migration (and create_all) is skipped
    Table('s67_probe_table', d.Base.metadata, Column('id', Integer, primary_key=True))
migrate.run_migration_if_needed()
con = sqlite3.connect(str(d.DB_PATH))
have = {t: {r[1] for r in con.execute(f'PRAGMA table_info("{t}")')}
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
stored = con.execute("SELECT value FROM app_settings WHERE key='schema_version'").fetchone()[0]
con.close()
want = {t: {c.name for c in tbl.columns} for t, tbl in d.Base.metadata.tables.items()}
print(json.dumps({'from': version, 'stored_after': stored, 'expected': migrate.SCHEMA_VERSION,
                  'missing_tables': sorted(t for t in want if t not in have),
                  'missing_columns': {t: sorted(want[t] - have[t]) for t in want if t in have and want[t] - have[t]}}))
"""


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    import migrate
    folder = BASE / 'tests' / 'schema'
    fixtures = sorted(folder.glob('*.sql'))

    def upgrade(path, mutation='none'):
        env = dict(os.environ, GROUNDWORK_DATA_DIR=tempfile.mkdtemp(prefix='gw_s67_'))
        r = subprocess.run([sys.executable, '-c', UPGRADE, str(path), mutation], cwd=str(BASE), env=env,
                           capture_output=True, text=True, encoding='utf-8', timeout=180)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                                   # noqa: BLE001 - reported as a failure
            return {'error': (r.stderr or 'no output')[-400:]}

    names = [f.stem for f in fixtures]
    check('s67 a fixture exists for v1.1.0\'s released schema (20260725-byb) and for the current SCHEMA_VERSION',
          '20260725-byb' in names and migrate.SCHEMA_VERSION in names)
    if migrate.SCHEMA_VERSION not in names:
        print(f'        run: python schema_fixture.py   (saves {migrate.SCHEMA_VERSION}.sql)')

    for f in fixtures:
        res = upgrade(f)
        ok = (not res.get('error') and not res.get('missing_tables') and not res.get('missing_columns')
              and res.get('stored_after') == migrate.SCHEMA_VERSION)
        check(f's67 a database at {f.stem} upgrades to today\'s schema: every table and column, and the version recorded',
              ok)
        if not ok:
            print(f'        {f.name}: {json.dumps(res)[:400]}')

    current = folder / f'{migrate.SCHEMA_VERSION}.sql'
    if current.exists():
        res = upgrade(current, 'unlisted_column')
        check('s67 mutation caught: a model column added and bumped but not listed never reaches an upgraded database',
              's67_probe_column' in (res.get('missing_columns') or {}).get('app_settings', []))
        res = upgrade(current, 'unbumped_table')
        check('s67 mutation caught: a model table added without a bump never reaches a database at the current version',
              's67_probe_table' in (res.get('missing_tables') or []))
