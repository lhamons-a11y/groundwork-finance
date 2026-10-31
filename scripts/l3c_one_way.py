#!/usr/bin/env python3
"""Item 82 R3 / LTS_RETIREMENT.md L3c: the one-way test - a 1.1.1 database, upgraded by 2.0, opened again in 1.1.1, then
in 2.0 again. Each step runs in its own process against one throwaway data folder. Recorded either way.

    git worktree add /tmp/gw-v111 v1.1.1
    python scripts/l3c_one_way.py /tmp/gw-v111
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
STEP = r'''
import json, os, sys, sqlite3
tree, step = sys.argv[1], sys.argv[2]
sys.path.insert(0, tree); os.chdir(tree)
out = {'step': step}
try:
    from server import create_app, _GW_TOKEN
    app = create_app(); c = app.test_client(); H = {'X-GW-Token': _GW_TOKEN, 'Content-Type': 'application/json'}
    out['started'] = True
    def g(p):
        r = c.get(p, headers=H); d = r.get_json(silent=True)
        return r.status_code, (d.get('data', d) if isinstance(d, dict) else d)
    if step == 'make':
        c.patch('/api/settings', headers=H, data=json.dumps({'terms_accepted': '1.2', 'ai_enabled': 'false', 'onboarding_complete': 'true'}))
        a = c.post('/api/accounts', headers=H, data=json.dumps({'name': 'L3c Checking', 'type': 'checking'})).get_json()
        aid = (a.get('data') or a)['id']
        for i, d in enumerate(['2026-09-03', '2026-09-17', '2026-10-01']):
            c.post('/api/transactions', headers=H, data=json.dumps({'account_id': aid, 'date': d, 'description': f'L3C STORE {i}', 'merchant': 'L3c Store',
                   'amount': 40 + i, 'type': 'debit', 'category': 'Groceries', 'source': 'csv'}))
        c.post('/api/budget/items', headers=H, data=json.dumps({'type': 'expense', 'name': 'Groceries', 'amount': 500, 'category': 'Groceries'}))
    s, tx = g('/api/transactions?per_page=500'); out['transactions'] = [s, len(tx) if isinstance(tx, list) else tx]
    s, ac = g('/api/accounts'); out['accounts'] = [s, len(ac) if isinstance(ac, list) else ac]
    s, bi = g('/api/budget/items'); out['budget_items'] = [s, len(bi) if isinstance(bi, list) else bi]
    if step == 'reopen_in_111':
        a = g('/api/accounts')[1][0]['id']
        r = c.post('/api/transactions', headers=H, data=json.dumps({'account_id': a, 'date': '2026-10-20', 'description': 'L3C WRITE IN 1.1',
                   'merchant': 'L3c Write', 'amount': 9, 'type': 'debit', 'category': 'Groceries', 'source': 'manual'}))
        out['write_in_111'] = r.status_code
except Exception as e:
    import traceback; out['error'] = traceback.format_exc()[-900:]
db = os.path.join(os.environ['GROUNDWORK_DATA_DIR'], 'groundwork.db')
con = sqlite3.connect(db)
out['schema_version'] = (con.execute("select value from app_settings where key='schema_version'").fetchone() or [None])[0]
out['tables'] = con.execute("select count(*) from sqlite_master where type='table'").fetchone()[0]
out['sinking_cols'] = [r[1] for r in con.execute('pragma table_info(sinking_funds)')]
con.close()
out['backups'] = sorted(os.listdir(os.path.join(os.environ['GROUNDWORK_DATA_DIR'], 'backups'))) if os.path.isdir(os.path.join(os.environ['GROUNDWORK_DATA_DIR'], 'backups')) else []
print('RESULT ' + json.dumps(out))
'''


def main():
    v111 = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='gw_l3c_') as d:
        step = Path(d) / 'step.py'
        step.write_text(STEP)
        data = Path(d) / 'data'
        data.mkdir()
        env = {**os.environ, 'GROUNDWORK_DATA_DIR': str(data)}
        for tree, name in ((v111, 'make'), (HERE, 'migrate_to_20'), (v111, 'reopen_in_111'), (HERE, 'reopen_in_20')):
            r = subprocess.run([sys.executable, str(step), str(tree), name], capture_output=True, text=True, env=env)
            line = next((l for l in r.stdout.splitlines() if l.startswith('RESULT ')), None)
            print(line[7:] if line else json.dumps({'step': name, 'error': (r.stdout + r.stderr)[-600:]}))


if __name__ == '__main__':
    main()
