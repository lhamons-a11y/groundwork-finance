#!/usr/bin/env python3
"""Save the exact schema a database has at a SCHEMA_VERSION, as a fixture the gate upgrades (gw 2.0/SCHEMA_PIN_MODELS.md,
item 24, P2/P3).

    python schema_fixture.py                    the current code's schema, saved as tests/schema/<SCHEMA_VERSION>.sql
    python schema_fixture.py --tree PATH        another checkout's (e.g. a worktree of the v1.1.0 tag)

When to run it: at every SCHEMA_VERSION bump, AFTER the bump - the fixture records the shape databases at the new
version will have, so the next model change is upgraded from it. Old fixtures are kept: each is a shape some user's
database is in. s51 fails if the current SCHEMA_VERSION has no fixture.

It builds a fresh database in a throwaway folder with that tree's own migration, in its own process (never the user's
data, never this process's imports), and writes the CREATE statements from sqlite_master.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DUMP = r"""
import os, sys, sqlite3
sys.path.insert(0, os.getcwd())
import migrate
from core import database as d
migrate.run_migration_if_needed()
con = sqlite3.connect(str(d.DB_PATH))
rows = con.execute("SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
                   "ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name").fetchall()
ver = con.execute("SELECT value FROM app_settings WHERE key='schema_version'").fetchone()[0]
con.close()
print('-- schema_version: ' + ver)
for t, n, s in rows:
    print(s.strip() + ';')
"""


def main():
    tree = HERE
    if '--tree' in sys.argv:
        tree = Path(sys.argv[sys.argv.index('--tree') + 1]).resolve()
    env = dict(os.environ, GROUNDWORK_DATA_DIR=tempfile.mkdtemp(prefix='gw_schema_fixture_'))
    r = subprocess.run([sys.executable, '-c', DUMP], cwd=str(tree), env=env, capture_output=True, text=True,
                       encoding='utf-8')
    lines = [l for l in r.stdout.splitlines() if l.startswith('-- schema_version: ') or l.strip()]
    start = next((i for i, l in enumerate(lines) if l.startswith('-- schema_version: ')), None)
    if start is None:
        print(r.stderr[-1500:] or 'no schema produced')
        return 1
    body = '\n'.join(lines[start:]) + '\n'
    version = lines[start].split(': ', 1)[1].strip()
    out = HERE / 'tests' / 'schema' / f'{version}.sql'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding='utf-8')
    print(f'wrote {out.relative_to(HERE)} ({body.count(chr(10) + "CREATE TABLE") + body.startswith("CREATE TABLE")} '
          f'tables, from {tree})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
