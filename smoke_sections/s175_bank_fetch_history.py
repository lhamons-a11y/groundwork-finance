"""Item 57 stage 4: each fetch in the Historian, joined to its import by the file's hash (gw 2.0/BANK_AGENT.md A11, A8;
Rob 2026-10-09: "lets do stage 4").

    A11  one 'statement_fetched' event per fetch, however it ends (the user closing the window included): host, the
         steps in words, started / code asked / code entered / finished, the outcome and why, the file's name and
         SHA-256 - never its content; joined to the later 'import_committed' by that hash; a fetch whose file isn't
         imported says "not imported yet"
    A8   the file goes only to the Downloads folder and the existing review; nothing in the agent writes a transaction
         Read by the Settings history route alone - no prompt, no engine.
"""
import hashlib
import json
import tempfile
from pathlib import Path


def run(ctx):
    check, c, H, HJ, BASE, srv = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE, ctx.server_src
    import server
    import bank_agent_window as baw
    from core.database import HistorianEntry, Transaction, db_session

    key = 'account:917501'
    folder = Path(tempfile.mkdtemp(prefix='s175_'))
    body = b'Date,Description,Amount\n2026-10-01,COFFEE,-4.50\n'
    (folder / 'stmt-oct.csv').write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    made = []
    try:
        with db_session() as s:
            before_tx = s.query(Transaction).count()
        # a whole run, through the parent's reader, ending in a download
        got = []
        baw.begin_fetch_for_test(key)
        baw.collect_fetch(key, ['ready\n', 'fetch {"s":"step","i":0}\n', 'fetch {"s":"waiting_code","i":1}\n',
                                'fetch {"s":"step","i":1}\n', 'fetch {"s":"downloaded","file":"stmt-oct.csv"}\n'],
                          on_finish=lambda k, evs: got.append((k, evs)))
        check('s175 A11 the run is handed over once, when it ends, each event stamped with when it arrived',
              len(got) == 1 and got[0][0] == key and all('at' in e for e in got[0][1]) and got[0][1][-1]['s'] == 'downloaded')
        server._record_fetch(key, 'https://Bank.Example.com/login?x=1', ['Sign in (Groundwork fills your saved login)', 'Click “Download”'],
                             '2026-10-09T10:00:00', got[0][1], folder=folder)
        with db_session() as s:
            ev = s.query(HistorianEntry).filter(HistorianEntry.event_category == 'statement_fetched').order_by(HistorianEntry.id.desc()).first()
            made.append(ev.id)
            ctx_ = json.loads(ev.context_json)
            after_tx = s.query(Transaction).count()
        check('s175 A11 one statement_fetched event: host, steps in words, the times, the outcome, the file\'s name and hash',
              set(ctx_) == {'account_key', 'host', 'steps', 'started', 'code_asked', 'code_entered', 'finished', 'outcome', 'why',
                            'file_name', 'content_sha256'}
              and ctx_['host'] == 'bank.example.com' and ctx_['outcome'] == 'downloaded' and ctx_['file_name'] == 'stmt-oct.csv'
              and ctx_['content_sha256'] == sha and ctx_['code_asked'] and ctx_['code_entered'] and ctx_['started'] == '2026-10-09T10:00:00')
        check('s175 A11 never the file\'s content', 'COFFEE' not in ev.context_json and '4.50' not in ev.context_json)
        check('s175 A8 recording a fetch writes no transaction - the file waits for the existing review', after_tx == before_tx)

        h = c.get(f'/api/settings/bank-agent/history?key={key}', headers=H).get_json()['data']['fetches']
        check('s175 A11 before its import, the fetch says "not imported yet" (imported is empty)', h and h[0]['imported'] is None)
        with db_session() as s:
            server.log_historian_event(s, 'import_committed', context={'file_name': 'stmt-oct.csv', 'content_sha256': sha, 'origin': 'watcher',
                                                                       'account_id': None, 'account_name': 's175', 'records': 1, 'created': 1,
                                                                       'duplicates': 0, 'errors': 0, 'first_date': '2026-10-01', 'last_date': '2026-10-01'})
            s.commit()
            made.append(s.query(HistorianEntry).order_by(HistorianEntry.id.desc()).first().id)
        h = c.get(f'/api/settings/bank-agent/history?key={key}', headers=H).get_json()['data']['fetches']
        check('s175 A11 after the import, the fetch is joined to it by the file\'s hash - when, and how many transactions',
              h[0]['imported'] and h[0]['imported']['records'] == 1)

        # the user closed the window before an outcome
        got2 = []
        baw.begin_fetch_for_test(key + '9')
        baw.collect_fetch(key + '9', ['fetch {"s":"step","i":0}\n'], on_finish=lambda k, evs: got2.append(evs))
        check('s175 A11 a fetch the user ends by closing the window is still recorded, as cancelled',
              len(got2) == 1 and got2[0][-1]['s'] == 'stopped' and got2[0][-1]['why'] == 'cancelled')
        server._record_fetch(key, 'https://bank.example.com', [], '2026-10-09T11:00:00',
                             [{'s': 'downloaded', 'file': 'gone.csv', 'at': '2026-10-09T11:01:00'}], folder=folder)
        with db_session() as s:
            ev2 = s.query(HistorianEntry).filter(HistorianEntry.event_category == 'statement_fetched').order_by(HistorianEntry.id.desc()).first()
            made.append(ev2.id)
            c2 = json.loads(ev2.context_json)
        check('s175 A11 a file that is gone when hashed is recorded with no hash - unknown, never guessed', c2['content_sha256'] is None)
    finally:
        with db_session() as s:
            s.query(HistorianEntry).filter(HistorianEntry.id.in_(made)).delete(synchronize_session=False)
            s.commit()

    import re
    lines, owner, users = srv.splitlines(), None, set()
    for ln in lines:
        m = re.match(r'def (\w+)\(', ln)
        if m:
            owner = m.group(1)
        if "'statement_fetched'" in ln and not ln.lstrip().startswith(('"""', '#')) and 'Item 57 A11: one' not in ln:
            users.add(owner)
    check(f's175 A11 the fetch record is written by one function and read by the Settings history route alone - no prompt, no engine {sorted(users)}',
          users == {'_record_fetch', 'bank_agent_history'} and 'statement_fetched' not in ctx.app_src)
