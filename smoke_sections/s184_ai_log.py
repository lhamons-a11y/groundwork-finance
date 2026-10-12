"""Item 62: the AI log (gw 2.0/AI_LOG.md G1-G8, RULED 2026-10-09; built on Rob's "build all items that have been
ruled on").

    G1  every AI attempt lands one entry: the surface, when, the instructions and data as sent, what came back, the
        voice check's verdict, shortened or stopped, run on this computer
    G2  the panel keeps "The numbers behind this analysis"; "View what was sent to AI" becomes one line to the log
    G3  nothing but the log's own routes reads the table
    G4  90 days; Clear; Keep the log off writes nothing
    G5  out of backups and exports unless included
    G7  one table, written by the chat route only
    G8  AI off logs nothing
"""
import ast
import json
import sqlite3
from datetime import datetime, timedelta


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    import server
    from core import engine
    from core.database import AiLog, AppSetting, db_session

    real_chat = engine.chat
    engine.chat = lambda system, messages, max_tokens=1000, temperature=0.3: {'ok': True, 'text': 'Dining was $412.', 'finish': 'stop'}
    try:
        with db_session() as s:
            s.query(AiLog).delete(synchronize_session=False)
            s.query(AppSetting).filter(AppSetting.key.in_(['ai_log_keep', 'ai_enabled'])).delete(synchronize_session=False)
            s.commit()
        body = {'system': 'Write two sentences.', 'messages': [{'role': 'user', 'content': 'Dining: $412'}], 'surface': 'monthly_report',
                'log_call': 'call-s184', 'log_attempt': 1, 'max_tokens': 200}
        r = c.post('/api/ai/chat', headers=HJ, data=json.dumps(body)).get_json()
        with db_session() as s:
            row = s.query(AiLog).filter_by(call_id='call-s184').first()
            got = (row.surface, row.system, json.loads(row.messages), row.response, row.stop_reason, row.attempt) if row else None
        check('s184 G1 an attempt lands one entry: surface, instructions and data exactly as sent, what came back, how it ended',
              r.get('log_id') and got == ('monthly_report', 'Write two sentences.', [{'role': 'user', 'content': 'Dining: $412'}],
                                          'Dining was $412.', 'end_turn', 1))
        c.post('/api/ai/chat', headers=HJ, data=json.dumps({**body, 'log_attempt': 2}))
        c.post(f"/api/ai/log/{r['log_id']}/voice", headers=HJ, data=json.dumps({'pass': False, 'rules': ['R5_verdict_words']}))
        call = c.get('/api/ai/log/call/call-s184', headers=H).get_json()['data']['entries']
        check('s184 G1/G6 a request\'s attempts come back together, each with the voice check\'s verdict - a rewrite is visible, not hidden',
              [e['attempt'] for e in call] == [1, 2] and call[0]['voice'] == {'pass': False, 'rules': ['R5_verdict_words'], 'shortened': False}
              and call[0]['response'] == 'Dining was $412.')
        lst = c.get('/api/ai/log', headers=H).get_json()['data']
        check('s184 G1 the log lists newest first, with whether it is being kept and for how long',
              lst['entries'][0]['attempt'] == 2 and lst['keep'] is True and lst['days'] == 90 and 'system' not in lst['entries'][0])

        # G4: off, prune, clear
        c.post('/api/ai/log/keep', headers=HJ, data=json.dumps({'keep': False}))
        c.post('/api/ai/chat', headers=HJ, data=json.dumps({**body, 'log_call': 'call-off'}))
        with db_session() as s:
            off = s.query(AiLog).filter_by(call_id='call-off').count()
        c.post('/api/ai/log/keep', headers=HJ, data=json.dumps({'keep': True}))
        check('s184 G4 Keep the log off writes nothing', off == 0)
        with db_session() as s:
            s.add(AiLog(call_id='call-old', surface='x', created_at=datetime.utcnow() - timedelta(days=91))); s.commit()
        c.get('/api/ai/log', headers=H)
        with db_session() as s:
            old = s.query(AiLog).filter_by(call_id='call-old').count()
        check('s184 G4 entries older than 90 days are deleted', old == 0)

        # G5: backups (sealed since item 81 - opened here with the stand-in vault's key to count the rows)
        from core import backup_crypto as _bc
        _old_vault = _bc.test_protect(c, HJ)
        made = c.post('/api/backup/create', headers=HJ, data='{}').get_json()['data']
        import time
        time.sleep(1.1)                    # backups are named by the second
        kept = c.post('/api/backup/create', headers=HJ, data=json.dumps({'include_ai_log': True})).get_json()['data']
        bdir = server._backups_dir()

        def _rows(name):
            data, _ = _bc.decrypt((bdir / name).read_bytes(), vault_key=_bc.VAULT.get())
            tmp = bdir / f'.s184_{name}.db'
            tmp.write_bytes(data)
            con = sqlite3.connect(str(tmp))
            try:
                return con.execute('SELECT COUNT(*) FROM ai_log').fetchone()[0], data
            finally:
                con.close()
                tmp.unlink()
        n1, raw = _rows(made['filename'])
        n2, _ = _rows(kept['filename'])
        _bc.test_unprotect(_old_vault)
        check('s184 G5 a backup leaves the AI log out - rows gone and the file compacted - unless the person includes it',
              n1 == 0 and n2 >= 2 and b'Dining was $412.' not in raw)
        srv = ctx.server_src
        check('s184 G5 an export carries the AI log only when ticked', "if body.get('include_ai_log'):    # item 62 G5" in srv
              and 'include_ai_log: !!g(\'exportIncludeAiLog\')?.checked' in ctx.app_src)

        c.post('/api/ai/log/clear', headers=HJ, data='{}')
        with db_session() as s:
            left = s.query(AiLog).count()
        check('s184 G4 Clear the log deletes every entry', left == 0)

        # G8: AI off logs nothing
        with db_session() as s:
            server._set_setting(s, 'ai_enabled', 'false'); s.commit()
        off_r = c.post('/api/ai/chat', headers=HJ, data=json.dumps({**body, 'log_call': 'call-aioff'})).get_json()
        with db_session() as s:
            n = s.query(AiLog).filter_by(call_id='call-aioff').count()
            s.query(AppSetting).filter_by(key='ai_enabled').delete(); s.commit()
        check('s184 G8 with AI off nothing is sent and nothing is logged', n == 0 and (off_r.get('data') or {}).get('ai_available') is False)
    finally:
        engine.chat = real_chat
        with db_session() as s:
            s.query(AiLog).delete(synchronize_session=False)
            s.query(AppSetting).filter(AppSetting.key.in_(['ai_log_keep'])).delete(synchronize_session=False)
            s.commit()

    # G3 / G7: who touches the table
    tree = ast.parse(ctx.server_src)
    users = sorted({f.name for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)
                    and any(isinstance(n, ast.Name) and n.id == 'AiLog' for n in ast.walk(f))})
    check(f's184 G3/G7 only the chat route writes the log and only its own routes (and the ticked export) read it: {users}',
          users == ['_ai_log_write', 'ai_log_call', 'ai_log_clear', 'ai_log_entry', 'ai_log_list', 'ai_log_voice', 'export_to_file'])
    stream = ctx.server_src.split('def _ai_chat_stream(')[1].split('\ndef ')[0]
    check('s184 G1 a streamed answer is logged when it ends - finished, stopped (item 10) or failed - and hands back its entry',
          stream.count('_ai_log_write(') == 3 and "'log_id': log_id" in stream and 'stopped=True' in stream)

    # G2: the panel
    app = ctx.app_src
    disc = app.split('function _renderAIDisclosure(payload) {')[1].split('\n}')[0]
    check('s184 G2 the panel says one line - sent to AI on this computer, see it in the log - opening that request',
          'Sent to AI on this computer' in disc and 'openAiLog(' in disc and 'View what was sent to AI' not in disc
          and 'The numbers behind this analysis' in app)
    check('s184 G2 callAI gives every attempt of one request the same id, and reports each voice verdict to its entry',
          'payload.logCall = callId;' in app and 'log_call: callId, log_attempt: ++attemptNo' in app
          and app.count('_aiLogVoice(result.logId, gate);') == 2 and '_aiLogVoice(s.logId, s.gate, !!s.shortened)' in app)
    check('s184 the untrue "could search the web" line is gone from what a person can see (item 63\'s L2 in passing)',
          'This request could search the web for current prices' not in app)
