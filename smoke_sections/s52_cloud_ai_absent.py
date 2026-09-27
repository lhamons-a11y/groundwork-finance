"""Cloud AI is gone: no path sends a user's data to an off-device AI model - by absence, not by a switch.

`gw 2.0/CLOUD_AI_REMOVAL.md`, ruled by Rob 2026-09-27: remove cloud AI outright on both lines, with both crossing
tests. The invariant is stronger than "the option is unavailable": Groundwork has NO path that sends user data to an
off-device model. A hidden toggle with the code still shipped would keep the asterisk; this section fails if any of
it comes back.

    the source scan     the shipped modules and pages contain no hosted-model endpoint, no Anthropic headers, no
                        key route, no key field, no cloud attribution, no hosted model name. The only place the key's
                        NAME may appear is migrate.py's crossover step, which deletes it
    the runtime test    every connection attempt is recorded and refused. With 'cloud' planted as the provider, a
                        key in the environment, and a non-loopback address planted as the local endpoint, every AI
                        route answers - and none of them ever tries to reach a host that is not this computer
    "local" is local    the endpoint override accepts only loopback addresses on save, and a planted remote value is
                        ignored at the moment of use (SAFETY_PROVISIONS_INVENTORY S6)
    the crossover       on upgrade: ai_provider goes; ONLY ANTHROPIC_API_KEY leaves Groundwork's config.json (the EIA
                        and SerpApi keys stay); an unreadable config.json is left alone; the one-time notice is
                        recorded only for a user it affected; it runs once

Mutations, each of which must fail a case: the Anthropic endpoint put back in server.py; a second provider added under
another name; "local" widened to any host; the crossover deleting the whole config.json; the crossover leaving the key.
"""
import json
import os
import re
import socket
from pathlib import Path

_SHIPPED = ['server.py', 'launch.py', 'migrate.py', 'bank_importer.py', 'pdf_statement.py', 'price_engine.py',
            'gas_price.py', 'utility_price.py', 'trip_distance.py', 'flight_price.py', 'quicken_import.py',
            'static/js/app.js', 'static/index.html']

# Hosted-model endpoints and the cloud-only machinery. Any of these in a shipped file is a path off the device.
_FORBIDDEN = [
    r'api\.anthropic\.com', r'x-api-key', r'anthropic-version', r"/api-key'", r'sk-ant',
    r'Powered by Claude', r'Cloud \(Anthropic\)', r'claude-(haiku|sonnet|opus)',
    r'api\.openai\.com', r'generativelanguage\.googleapis\.com', r'api\.mistral\.ai', r'api\.cohere\.',
    r'api\.groq\.com', r'openrouter\.ai', r'api\.together\.', r'bedrock-runtime', r'aiplatform\.googleapis',
    r"_ai_chat_cloud", r"ai_provider'\) == 'cloud'",
]


def _scan(texts):
    hits = []
    for name, text in texts.items():
        for pat in _FORBIDDEN:
            if re.search(pat, text):
                hits.append(f'{name}: {pat}')
        if name != 'migrate.py' and 'ANTHROPIC_API_KEY' in text:
            hits.append(f'{name}: ANTHROPIC_API_KEY')
    return hits


class _Refused(OSError):
    pass


def _runtime(c, H, HJ, server):
    """Every connection attempt recorded and refused; returns (attempted hosts, route statuses)."""
    from core.database import db_session, AppSetting
    attempts, statuses = [], {}
    real_connect, real_create = socket.socket.connect, socket.create_connection

    def rec_connect(self, address, *a, **k):
        attempts.append(address[0] if isinstance(address, tuple) else str(address))
        raise _Refused('s52: every connection refused')

    def rec_create(address, *a, **k):
        attempts.append(address[0] if isinstance(address, tuple) else str(address))
        raise _Refused('s52: every connection refused')

    with db_session() as s:
        for key, value in (('ai_provider', 'cloud'), ('local_endpoint', 'http://ai.example.com:11434'),
                           ('ai_enabled', 'true')):
            row = s.query(AppSetting).filter_by(key=key).first()
            if row:
                row.value = value
            else:
                s.add(AppSetting(key=key, value=value))
        s.commit()
    old_env = os.environ.get('ANTHROPIC_API_KEY')
    os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-s52-planted'
    try:
        socket.socket.connect, socket.create_connection = rec_connect, rec_create
        body = json.dumps({'messages': [{'role': 'user', 'content': 's52: my balance is $1,234'}],
                           'max_tokens': 20})
        statuses['/api/ai/chat'] = c.post('/api/ai/chat', headers=HJ, data=body).status_code
        statuses['/api/ai/status'] = c.get('/api/ai/status', headers=H).status_code
        try:
            # It only ever runs inside a request (PDF extraction), so it is called inside one here.
            with c.application.test_request_context('/api/debt/pdf-extract', method='POST'):
                server._ai_complete_text('s52 system', 's52 user')
            statuses['_ai_complete_text'] = 'returned'
        except Exception as e:                           # noqa: BLE001 - recorded, not hidden
            statuses['_ai_complete_text'] = f'raised {type(e).__name__}'
    finally:
        socket.socket.connect, socket.create_connection = real_connect, real_create
        if old_env is None:
            os.environ.pop('ANTHROPIC_API_KEY', None)
        else:
            os.environ['ANTHROPIC_API_KEY'] = old_env
        with db_session() as s:
            for key in ('ai_provider', 'local_endpoint'):
                row = s.query(AppSetting).filter_by(key=key).first()
                if row:
                    s.delete(row)
            s.commit()
    return attempts, statuses


def _off_device(attempts):
    import ipaddress
    bad = []
    for host in attempts:
        h = str(host).lower().strip('[]')
        if h == 'localhost':
            continue
        try:
            if ipaddress.ip_address(h).is_loopback:
                continue
        except ValueError:
            pass
        bad.append(host)
    return bad


def _crossover(dbs, data_dir, case):
    """Run the crossover on a staged state; return what it left. case: 'cloud' | 'plain' | 'badjson'."""
    import migrate
    from core.database import AppSetting
    cfg = Path(data_dir) / 'config.json'
    had = cfg.read_bytes() if cfg.exists() else None
    try:
        if case == 'badjson':
            cfg.write_text('{ not json', encoding='utf-8')
        else:
            keys = {'EIA_API_KEY': 'eia-s52', 'FLIGHTS_API_KEY': 'serp-s52'}
            if case == 'cloud':
                keys['ANTHROPIC_API_KEY'] = 'sk-ant-s52-stored'
            cfg.write_text(json.dumps(keys, indent=2), encoding='utf-8')
        with dbs() as s:
            for key in ('migration_cloud_ai_removed_20260927', 'cloud_ai_removed_notice', 'ai_provider'):
                row = s.query(AppSetting).filter_by(key=key).first()
                if row:
                    s.delete(row)
            if case == 'cloud':
                s.add(AppSetting(key='ai_provider', value='cloud'))
            s.commit()
        with dbs() as s:
            migrate._remove_cloud_ai(s)
            s.commit()
        with dbs() as s:
            migrate._remove_cloud_ai(s)          # the second run must change nothing
            s.commit()
            provider = s.query(AppSetting).filter_by(key='ai_provider').first()
            notice = s.query(AppSetting).filter_by(key='cloud_ai_removed_notice').first()
            out = {'provider_row': provider is not None,
                   'notice': json.loads(notice.value) if notice else None,
                   'config_text': cfg.read_text(encoding='utf-8') if cfg.exists() else None}
        return out
    finally:
        if had is None:
            cfg.unlink(missing_ok=True)
        else:
            cfg.write_bytes(had)
        with dbs() as s:
            for key in ('cloud_ai_removed_notice', 'ai_provider'):
                row = s.query(AppSetting).filter_by(key=key).first()
                if row:
                    s.delete(row)
            s.commit()


def _crossover_checks(dbs, data_dir):
    out = {}
    r = _crossover(dbs, data_dir, 'cloud')
    cfg = json.loads(r['config_text'] or '{}')
    out['a cloud user: ai_provider removed'] = not r['provider_row']
    out['a cloud user: ONLY ANTHROPIC_API_KEY leaves config.json - the EIA and SerpApi keys stay'] = (
        'ANTHROPIC_API_KEY' not in cfg and cfg.get('EIA_API_KEY') == 'eia-s52' and cfg.get('FLIGHTS_API_KEY') == 'serp-s52')
    out['a cloud user: the one-time notice records what was done (and a second run changes nothing)'] = (
        r['notice'] == {'was_cloud': True, 'key_removed': True})
    r = _crossover(dbs, data_dir, 'plain')
    out['a user who never had cloud gets no notice, and their config.json is untouched'] = (
        r['notice'] is None and json.loads(r['config_text'] or '{}') == {'EIA_API_KEY': 'eia-s52', 'FLIGHTS_API_KEY': 'serp-s52'})
    r = _crossover(dbs, data_dir, 'badjson')
    out['a config.json Groundwork cannot parse is left exactly as it was'] = r['config_text'] == '{ not json'
    return out


def run(ctx):
    check, c, H, HJ, dbs = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.dbs
    import server
    from core.database import DATA_DIR

    texts = {n: ctx.BASE.joinpath(n).read_text(encoding='utf-8', errors='replace')
             for n in _SHIPPED if ctx.BASE.joinpath(n).exists()}
    for n in (ctx.BASE / 'core').glob('*.py'):
        texts[f'core/{n.name}'] = n.read_text(encoding='utf-8', errors='replace')
    hits = _scan(texts)
    check(f's52 the source scan: no hosted-model endpoint, key route, key field or cloud attribution in the '
          f'{len(texts)} shipped files', len(texts) >= 15 and not hits)
    for h in hits[:10]:
        print(f'        {h}')
    check("s52 the key's name appears only in migrate.py's crossover step, which deletes it",
          'ANTHROPIC_API_KEY' in texts.get('migrate.py', '') and '_remove_cloud_ai' in texts.get('migrate.py', ''))

    attempts, statuses = _runtime(c, H, HJ, server)
    check('s52 runtime, cloud planted + a key in the environment + a remote endpoint planted: every AI route answers',
          all((v == 'returned') if isinstance(v, str) else v < 500 for v in statuses.values()))
    off = _off_device(attempts)
    check('s52 runtime: no AI route ever tried to reach a host that is not this computer', not off)
    print(f'        route answers: {statuses}')
    for h in off[:5]:
        print(f'        tried to reach {h}')
    check('s52 runtime: the AI routes did try the local model (the test was not vacuous)', bool(attempts))

    check('s52 "local" is local: a non-loopback endpoint is refused on save',
          c.patch('/api/settings', headers=HJ, data=json.dumps({'local_endpoint': 'http://10.0.0.5:11434'})).status_code == 400)
    ok_local = c.patch('/api/settings', headers=HJ, data=json.dumps({'local_endpoint': 'http://127.0.0.1:11434'})).status_code == 200
    c.patch('/api/settings', headers=HJ, data=json.dumps({'local_endpoint': ''}))
    check('s52 "local" is local: a loopback endpoint is accepted', ok_local)
    check('s52 the provider cannot be set - there is none', (
        c.patch('/api/settings', headers=HJ, data=json.dumps({'ai_provider': 'cloud'})).status_code == 200
        and c.get('/api/settings', headers=H).get_json()['data'].get('ai_provider') is None))
    check('s52 the key route is gone', c.post('/api/settings/api-key', headers=HJ,
                                                data=json.dumps({'key': 'sk-ant-x'})).status_code in (404, 405))
    check('s52 ai/status names local as the only provider',
          c.get('/api/ai/status', headers=H).get_json()['data'].get('provider') == 'local')

    for name, ok in _crossover_checks(dbs, DATA_DIR).items():
        check(f's52 crossover: {name}', ok)
    app = ctx.app_src
    check('s52 the page shows the crossover notice once, only when the upgrade recorded one',
          "_cloudAiRemovedNotice(data.settings['cloud_ai_removed_notice'])" in app
          and "cloud_ai_removed_notice: 'shown'" in app and "if (!raw || raw === 'shown') return;" in app
          # recorded on display, so no way of dismissing it can bring it back
          and app.index("{ cloud_ai_removed_notice: 'shown' }") < app.index("confirmAction('Cloud AI has been removed'"))
    check('s52 a PDF without a local model gets the honest message, pointing to CSV / QFX',
          "Reading a PDF statement needs a local AI model" in ctx.server_src)

    # Mutations
    back = dict(texts, **{'server.py': texts['server.py'] + "\nURL = 'https://api.anthropic.com/v1/messages'\n"})
    check('s52 mutation caught: the Anthropic endpoint put back in server.py', bool(_scan(back)))
    other = dict(texts, **{'static/js/app.js': texts['static/js/app.js'] + "\n// fetch('https://api.openai.com/v1/chat')\n"})
    check('s52 mutation caught: a second provider added under another name', bool(_scan(other)))

    real_loop = server._is_loopback_endpoint
    try:
        server._is_loopback_endpoint = lambda url: True
        m_attempts, _ = _runtime(c, H, HJ, server)
    finally:
        server._is_loopback_endpoint = real_loop
    check('s52 mutation caught: "local" widened to any host', bool(_off_device(m_attempts)))

    import migrate
    real_step = migrate._remove_cloud_ai

    def deletes_whole_file(session):
        cfg = Path(DATA_DIR) / 'config.json'
        if cfg.exists():
            cfg.unlink()
        return real_step(session)

    def keeps_key(session):
        cfg = Path(DATA_DIR) / 'config.json'
        before = cfg.read_text(encoding='utf-8') if cfg.exists() else None
        real_step(session)
        if before is not None:
            cfg.write_text(before, encoding='utf-8')

    for label, fn in (('the crossover deleting the whole config.json', deletes_whole_file),
                      ('the crossover leaving the key', keeps_key)):
        try:
            migrate._remove_cloud_ai = fn
            caught = not all(_crossover_checks(dbs, DATA_DIR).values())
        finally:
            migrate._remove_cloud_ai = real_step
        check(f's52 mutation caught: {label}', caught)
