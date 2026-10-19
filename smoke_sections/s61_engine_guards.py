"""The in-app engine's guarantees (ENGINE_REPLACEMENT.md, item 31; Rob 2026-10-02), each one tested where it can fail.

    R-a  AI off means nothing is loaded - not the model, not the runtime library; AI on loads at launch
    CPU  the processor is checked before anything else, because the CPU build would fault the whole app without AVX2
    E4   the model file must match the tested file's SHA-256, or it is not loaded
    7    a machine that cannot run the model gets AI unavailable, said honestly - the rest of the app keeps working
    E8   the engine opens no port and makes no network call; Ollama is absent from the architecture
    R-b  an existing Ollama is never removed: the notice reads, says, and offers Windows' own page
    E6   the installers ship the model inside Groundwork and carry no Ollama

The real model is never loaded here; its memory, speed and voice are measured outside the gate.
"""
import ast
import hashlib
import json
import os
import re


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import server
    from core import engine

    def data_of(resp):
        body = resp.get_json() or {}
        return body.get('data') or body

    loads = []
    real_load = engine._load
    engine._load = lambda gen: loads.append(gen)          # record a load instead of doing one

    def settle():
        engine.stop()
        engine.allow_load(False)
        loads.clear()

    try:
        # ── R-a: AI off loads nothing; AI on loads at launch ────────────────────
        settle()
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'false'})
        server.engine_launch()
        check('R-a launch with AI off: no load is started and the engine stays off',
              loads == [] and engine.status()['state'] == 'off')
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'true'})
        check('R-a switching AI on in the running app starts the load (the launcher allowed it)',
              len(loads) == 1 and engine.status()['state'] == 'loading')
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'false'})
        check('R-a switching AI off stops it: the engine is off and holds no model',
              engine.status()['state'] == 'off' and not engine.is_loaded())
        settle()
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'true'})
        server.engine_launch()
        check('R-a launch with AI on starts exactly one background load', len(loads) == 1)
        settle()
        engine.start()
        check('without the launcher, start() loads nothing (the gate can never load 2.2 GB by accident)', loads == [])
    finally:
        engine._load = real_load
        settle()
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'true'})

    # ── The load's own order and refusals, run for real on files that are not the model ──
    src = ctx.BASE.joinpath('core/engine.py').read_text(encoding='utf-8')
    load_src = src[src.index('def _load('):src.index('def _finish(')]
    check('CPU the processor check comes before the file check, the hash and the runtime import',
          load_src.index('cpu_supported()') < load_src.index('path.exists()') < load_src.index('verify(path)')
          < load_src.index('import llama_cpp'))
    check('CPU nothing at module level imports the runtime: it is imported only inside _load',
          'import llama_cpp' not in src[:src.index('def _load(')] and src.count('import llama_cpp') == 1)

    def attempt(path, cpu=(True, ''), sha=None):
        settle()
        real_cpu, real_sha, real_verify = engine.cpu_supported, engine.MODEL_SHA256, engine.verify
        verified = []
        engine.cpu_supported = lambda: cpu
        if sha:
            engine.MODEL_SHA256 = sha
        engine.verify = lambda p, expected=None: verified.append(p) or real_verify(p, expected or engine.MODEL_SHA256)
        old_env = os.environ.get('GROUNDWORK_MODEL_PATH')
        os.environ['GROUNDWORK_MODEL_PATH'] = str(path)
        try:
            engine.allow_load()
            engine.start()
            engine._ready.wait(30)
            return engine.status(), verified
        finally:
            engine.cpu_supported, engine.MODEL_SHA256, engine.verify = real_cpu, real_sha, real_verify
            if old_env is None:
                os.environ.pop('GROUNDWORK_MODEL_PATH', None)
            else:
                os.environ['GROUNDWORK_MODEL_PATH'] = old_env
            engine.allow_load(False)

    junk = ctx.TMP / 's61_not_a_model.gguf'
    junk.write_bytes(b'GGUF' + b'\0' * 4096)
    st, verified = attempt(junk, cpu=(False, 'no AVX2'))
    check('7 a processor without AVX2: AI unavailable with the plain reason, and nothing else is even read',
          st['state'] == 'unavailable' and st['reason'] == 'cpu' and 'processor' in st['message'] and not verified)
    st, _ = attempt(ctx.TMP / 's61_missing.gguf')
    check('7 a missing model file: unavailable, saying reinstalling restores it',
          st['reason'] == 'missing' and 'Reinstalling' in st['message'])
    st, verified = attempt(junk)
    check('E4 a file that is not the tested model is refused by its SHA-256 and never handed to the runtime',
          st['reason'] == 'checksum' and verified == [junk])
    st, _ = attempt(junk, sha=hashlib.sha256(junk.read_bytes()).hexdigest())
    check('7 a runtime that cannot start (or a file it cannot load): unavailable, never a crash of the app',
          st['state'] == 'unavailable' and st['reason'] in ('runtime', 'load_failed'))
    check('7 and the app still answers while AI is unavailable',
          c.get('/api/settings/bootstrap', headers=H).status_code == 200)
    settle()
    check('E4 the pinned hash is the tested file (the runtime spike and voice A/B ran on sha256-b537...)',
          engine.MODEL_SHA256 == 'b5374915da534cb93df39f03bd4f2cd5a0c533df0d5e21957dc9556c260be9eb')

    # ── The 8 GB floor (Rob 2026-10-02: "make the 8 GB configuration work") - memory only, never the arithmetic ──
    import os as _os
    tests_set = any(k.startswith('GROUNDWORK_TEST_ENGINE_') for k in _os.environ)
    check('8GB the shipped configuration: 2048 context, batch 256, full-precision cache, no flash attention '
          '(identical text to the validated 4096 one; the 8-bit cache stays out - 2 R8 violations in 120)',
          tests_set or (engine.N_CTX == 2048 and engine.N_BATCH == 256 and engine.KV_CACHE_TYPE == 'GGML_TYPE_F16'
                        and engine.FLASH_ATTN is False))
    check('8GB the model file is read in, not memory-mapped: no second resident copy of the weights '
          '(4.60 GB resident mapped, 2.83 GB read - identical text)',
          tests_set or (engine.USE_MMAP is False and 'use_mmap=USE_MMAP' in src))
    launch_src = ctx.BASE.joinpath('launch.py').read_text(encoding='utf-8')
    check('8GB OpenBLAS is capped at one thread before anything can import numpy (620 MB measured on 20 threads)',
          _os.environ.get('OPENBLAS_NUM_THREADS') == '1'
          and launch_src.index("os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')") < launch_src.index('import threading')
          and src.index("os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')") < src.index('import llama_cpp'))
    shipped_all = '\n'.join(ctx.BASE.joinpath(n).read_text(encoding='utf-8')
                            for n in ('server.py', 'launch.py', 'static/js/app.js'))
    check('8GB the test-only engine switches are read by the engine alone; nothing in Groundwork sets them',
          'GROUNDWORK_TEST_ENGINE_' not in shipped_all)

    # ── E8: no port, no network, no Ollama ───────────────────────────────────
    tree = ast.parse(src)
    imported = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | {
        (n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    check('E8 the engine imports nothing that can open a socket or reach a network',
          not imported & {'socket', 'http', 'urllib', 'requests', 'httpx', 'aiohttp', 'flask', 'waitress'})

    shipped = {name: ctx.BASE.joinpath(name).read_text(encoding='utf-8')
               for name in ('server.py', 'launch.py', 'core/engine.py', 'static/js/app.js', 'static/index.html')}

    def ollama_left(texts):
        found = []
        for name, text in texts.items():
            for pat in (r'11434', r'/api/tags', r'/api/pull', r'/api/generate', r'ollama\s+serve',
                        r'install-ollama', r'pull-model', r'OLLAMA_\w*URL', r'keep_alive'):
                if re.search(pat, text):
                    found.append(f'{name}: {pat}')
        return found
    left = ollama_left(shipped)
    check('E8 nothing shipped talks to Ollama: no port, no API path, no install or pull', not left)
    for f in left[:6]:
        print(f'        {f}')
    check('E8 mutation caught: Ollama\'s port put back in server.py',
          bool(ollama_left(dict(shipped, **{'server.py': shipped['server.py'] + "\nURL = 'http://localhost:11434'\n"}))))
    stree = ast.parse(shipped['server.py'])
    mentions = {n.name for n in ast.walk(stree) if isinstance(n, ast.FunctionDef)
                and re.search('ollama', ast.get_source_segment(shipped['server.py'], n) or '', re.I)}
    check('E8 the only server code that names Ollama is the read-only notice',
          mentions <= {'_ollama_footprint', 'ai_ollama_notice', 'ai_ollama_notice_shown', 'ai_ollama_open_uninstall'})
    check('E8 launch.py starts no Ollama: it loads the in-app engine and releases it on close',
          not re.search('ollama', shipped['launch.py'], re.I)
          and '_start_engine()' in shipped['launch.py'] and '_stop_engine()' in shipped['launch.py']
          and shipped['launch.py'].index('webview.start(') < shipped['launch.py'].index('    _stop_engine()'))

    # ── R-b: the notice reads and says; it never removes ─────────────────────
    notice_src = '\n'.join(ast.get_source_segment(shipped['server.py'], n) for n in ast.walk(stree)
                           if isinstance(n, ast.FunctionDef) and n.name in mentions)
    check('R-b the notice code removes nothing: no delete, no uninstall command, no process launched',
          not re.search(r'\b(remove|unlink|rmtree|rmdir|subprocess|Popen|system)\b', notice_src))
    real_fp = server._ollama_footprint
    from core.database import AppSetting
    with ctx.dbs() as s:                       # start from "never shown": s50's sweep POSTs every route, this one too
        s.query(AppSetting).filter_by(key='ollama_notice').delete()
        s.commit()
    try:
        server._ollama_footprint = lambda: None
        check('R-b no Ollama on this computer: no notice', data_of(c.get('/api/ai/ollama-notice', headers=H)).get('show') is False)
        server._ollama_footprint = lambda: {'program_dir': r'C:\Users\x\AppData\Local\Programs\Ollama',
                                            'program_bytes': 1, 'models_dir': '', 'models_bytes': 0,
                                            'starts_at_login': True}
        d = data_of(c.get('/api/ai/ollama-notice', headers=H))
        check('R-b an Ollama is found: the notice shows where it is and that it starts at login',
              d.get('show') is True and d.get('program_dir', '').endswith('Ollama') and d.get('starts_at_login') is True)
        c.post('/api/ai/ollama-notice', headers=HJ, json={})
        check('R-b the notice shows once: after it is shown it does not come back',
              data_of(c.get('/api/ai/ollama-notice', headers=H)).get('show') is False)
    finally:
        server._ollama_footprint = real_fp
        with ctx.dbs() as s:

            s.query(AppSetting).filter_by(key='ollama_notice').delete()
            s.commit()
    app = ctx.app_src
    check("R-b the page's notice says Groundwork leaves Ollama alone and offers Windows' own page",
          'Groundwork leaves it alone' in app and "\"Open Windows' Installed apps\"" in app
          and app.index("API.post('/api/ai/ollama-notice', {})") < app.index("confirmAction('Groundwork no longer uses Ollama'"))

    # ── The machine check (R-d) ──────────────────────────────────────────────
    d = data_of(c.get('/api/ai/system-ram', headers=H))
    check('R-d the machine check answers: total memory, the 8 GB AI minimum, and the processor',
          d.get('available') is False or (d.get('ai_min_gb') == 8 and isinstance(d.get('meets_ai_minimum'), bool)
                                           and isinstance(d.get('cpu_ok'), bool)))
    check('R-d the onboarding offers the choice and never a model download',
          "_obApplyAIChoice(true)" in app and "_obApplyAIChoice(false)" in app and 'pull-model' not in app)

    # ── E6: what the installers ship ─────────────────────────────────────────
    for iss in ('groundwork.iss', 'groundwork_offline.iss', 'groundwork_store.iss'):
        text = ctx.BASE.joinpath(iss).read_text(encoding='utf-8')
        check(f'E6 {iss} ships the model inside Groundwork and no Ollama',
              f'sha256-{engine.MODEL_SHA256}"; DestDir: "{{app}}\\models"; DestName: "{engine.MODEL_FILE}"' in text
              and not re.search(r'OllamaSetup|\.ollama|ollama_runtime|NeedsOllama', text))
    spec = ctx.BASE.joinpath('groundwork.spec').read_text(encoding='utf-8')
    check("E6 the packaged build collects the runtime's native libraries", "collect_dynamic_libs('llama_cpp')" in spec)

    # Rob, 2026-10-02: warn, don't block, on a Windows that no longer gets security updates (financial data).
    for iss in ('groundwork.iss', 'groundwork_offline.iss', 'groundwork_store.iss', 'installer/Groundwork_Setup.iss'):
        text = ctx.BASE.joinpath(iss).read_text(encoding='utf-8')
        mv = re.search(r'^MinVersion=([\d.]+)', text, re.M)
        check(f'OS {iss} warns on Windows 10 and still installs there (no Windows 11 floor), interactive installs only',
              'WarnIfWindowsUnsupported();' in text and 'V.Build < 22000' in text and "that''s perfectly fine" in text
              and mv is not None and not mv.group(1).startswith('10.0.22') and 'WizardSilent()' in text)

    # ── Item 33 (ENGINE_OTHER_PLATFORMS.md, Rob 2026-10-03): macOS and Linux package the same engine and model ──
    import importlib
    import sys as _sys
    _sys.path.insert(0, str(ctx.BASE))
    se = importlib.import_module('spec_engine')
    check('33 one pin: spec_engine and fetch_model read the model\'s name and SHA-256 from core/engine.py',
          se.MODEL_FILE == engine.MODEL_FILE and se.MODEL_SHA256 == engine.MODEL_SHA256
          and 'core\' / \'engine.py' in ctx.BASE.joinpath('fetch_model.py').read_text(encoding='utf-8'))
    junk = ctx.TMP / 's61_wrong_model.gguf'
    junk.write_bytes(b'GGUF' + b'\1' * 1024)
    refused = {}
    old_env = os.environ.get('GW_MODEL_PATH')
    real_intel = se.intel_mac
    try:
        se.intel_mac = lambda: False
        for label, path in (('wrong', junk), ('missing', ctx.TMP / 's61_no_model.gguf')):
            os.environ['GW_MODEL_PATH'] = str(path)
            try:
                se.model_data(stage_dir=ctx.TMP / 's61_stage')
                refused[label] = None
            except se.BuildRefused as e:
                refused[label] = str(e)
        real_pin = se.MODEL_SHA256
        se.MODEL_SHA256 = hashlib.sha256(junk.read_bytes()).hexdigest()   # a file that IS the pinned one
        os.environ['GW_MODEL_PATH'] = str(junk)
        staged = se.model_data(stage_dir=ctx.TMP / 's61_stage')
        se.MODEL_SHA256 = real_pin
        se.intel_mac = lambda: True
        intel = (se.engine_parts(), se.model_data(stage_dir=ctx.TMP / 's61_stage'))
    finally:
        se.intel_mac = real_intel
        if old_env is None:
            os.environ.pop('GW_MODEL_PATH', None)
        else:
            os.environ['GW_MODEL_PATH'] = old_env
    check('33 the build REFUSES a model that is not the tested file, and a missing one (the check is mandatory)',
          refused.get('wrong') and 'not the tested model' in refused['wrong']
          and refused.get('missing') and 'missing' in refused['missing'])
    check('33 the tested file is staged under its shipped name, for models/',
          len(staged) == 1 and staged[0][1] == 'models' and staged[0][0].endswith(engine.MODEL_FILE))
    check('33 Q2 an Intel Mac builds Groundwork WITHOUT the engine or the model - no untested runtime is shipped',
          intel == (([], [], []), []))
    for spec in ('groundwork_macos.spec', 'groundwork_linux.spec'):
        text = ctx.BASE.joinpath(spec).read_text(encoding='utf-8')
        check(f'33 Q4 {spec} packages the engine and the verified model, and no longer excludes numpy',
              'spec_engine.engine_parts()' in text and 'spec_engine.model_data()' in text and '*_model_datas' in text
              and "        'numpy'," not in text)
    req = ctx.BASE.joinpath('requirements.txt').read_text(encoding='utf-8')
    check('33 Q2 requirements: the runtime is not installed on an Intel Mac (no tested wheel), so the install never fails',
          'llama-cpp-python==0.3.35; sys_platform != "darwin" or platform_machine == "arm64"' in req)
    check("33 Q4 the engine finds the model in a macOS app's Contents/Resources",
          "exe_dir.parent / 'Resources'" in src)
    for wf in ('macos-build.yml', 'linux-build.yml'):
        text = ctx.BASE.joinpath('.github', 'workflows', wf).read_text(encoding='utf-8')
        check(f'33 Q5 {wf} fetches and verifies the pinned model before packaging (any failure fails the build)',
              'fetch_model.py' in text and text.index('fetch_model.py') < text.index('pyinstaller groundwork_'))
    site = ctx.BASE.joinpath('Website', 'website.py').read_text(encoding='utf-8')
    check('33 Q7 the website says what is true: Mac local AI is built in on Metal from macOS 12; Linux local AI is coming',
          "Local AI: built in, on Apple's graphics (Metal)." in site and 'macOS 12 Monterey or later' in site
          and 'Tahoe' not in site and 'Local AI: coming to Linux.' in site)
