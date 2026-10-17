"""Item 93 (gw 2.0/GPU_ENGINE.md; Rob 2026-10-17: G0-G9 as recommended, G4' (a)): the engine fitted to this computer.

    G0  the software chooses: no route or control sets the device; AI on/off stays the user's
    G1  the graphics backend is loaded at run time, only if it loads; this build without one fits nothing
    G3  each device in its own process - one that crashes, hangs or says nothing is 'failed', and the app goes on;
        the shortest whole-answer time wins
    G4' a graphics device that wrote a figure not in its facts (R8) is never chosen, however fast
    G5  (a) fitting is a visible state, with its own message
    G6  fitted again only on a changed fingerprint, or after the chosen device failed at a launch (which runs on
        the processor); a launch that died inside the driver is caught by the next one
    G7  the result is a sentence: the device, its time on the test answer, the gain over the processor, the date;
        every device tried is accounted for
    G8  AI off fits nothing (nothing is loaded at all)
The probes themselves are run here for real only where no model is needed: the child-process entry and a child
that crashes. The measured run (CPU / Iris Xe / RTX A1000) is in GPU_ENGINE.md.
"""
import ast
import json
import subprocess
import sys


def run(ctx):
    check, c, H, BASE = ctx.check, ctx.c, ctx.H, ctx.BASE
    from core import engine
    from core import engine_fit as ef

    fit_file = ef.fit_path()
    fit_file.unlink(missing_ok=True)

    def probe(answer_s, r8=None, ok=True):
        p = {'ok': ok, 'answer_s': answer_s, 'first_word_s': answer_s / 4, 'layers': -1}
        if r8 is not None:
            p['r8'] = r8
        return p if ok else {'ok': False, 'error': 'it crashed'}

    # ── G3 + G4': the choice ────────────────────────────────────────────────────────────────────────────────────
    res = [{'device': 'cpu', 'name': "this computer's processor", 'kind': 'cpu', 'probe': probe(32.4)},
           {'device': 0, 'name': 'Intel(R) Iris(R) Xe Graphics', 'kind': 'builtin',
            'probe': probe(5.0, r8={'mixed_movement': ['50'], 'unverified_balance': []})},
           {'device': 1, 'name': 'NVIDIA RTX A1000 Laptop GPU', 'kind': 'card', 'probe': probe(9.1, r8={'a': []})},
           {'device': 2, 'name': 'Broken Card', 'kind': 'card', 'probe': probe(0, ok=False)}]
    best, res = ef.choose(res)
    check("s233 G4' a graphics chip that invented a figure is never chosen, even when it is the fastest",
          best['device'] == 1 and res[1]['verdict'] == 'r8')
    check('s233 G3 the shortest whole answer among the rest wins; a device that failed is marked failed',
          res[2]['verdict'] == 'chosen' and res[3]['verdict'] == 'failed' and res[0]['verdict'] == 'ran')
    best, _ = ef.choose([{'device': 'cpu', 'name': 'p', 'kind': 'cpu', 'probe': probe(30)},
                         {'device': 0, 'name': 'slow', 'kind': 'builtin', 'probe': probe(45, r8={})}])
    check('s233 G3 a graphics chip slower than the processor is not chosen', best['device'] == 'cpu')

    # ── G3: fit() over injected probes - a crash is one device's failure, never the fit's ────────────────────────
    calls = []

    def fake(args, timeout):
        calls.append(args)
        if args == ['list']:
            return {'ok': True, 'devices': [{'index': 0, 'description': 'Chip A', 'kind': 'builtin'},
                                            {'index': 1, 'description': 'Chip B', 'kind': 'card'}]}
        if args == ['cpu']:
            return probe(30.0)
        if args == ['gpu', '0']:
            return {'ok': False, 'error': 'the test process ended without an answer (exit 3221225477)'}
        return probe(10.0, r8={c: [] for c in ('a', 'b')})

    from datetime import date
    rec = ef.fit(run=fake, today=date(2026, 10, 17))
    check('s233 G3 every device is tried in its own probe: the listing, the processor, then each chip by index',
          calls == [['list'], ['cpu'], ['gpu', '0'], ['gpu', '1']])
    check('s233 G3 a chip whose test process crashed is failed; the fit still completes and chooses',
          rec['choice']['device'] == 1 and rec['choice']['name'] == 'Chip B'
          and [r['verdict'] for r in rec['results']] == ['ran', 'failed', 'chosen'])
    stopped = []
    rec_stop = ef.fit(run=lambda a, t: stopped.append(a) or fake(a, t), should_stop=lambda: True)
    check('s233 G8 AI switched off mid-fit: no device is tested after it, and the processor is the answer',
          stopped == [['list']] and rec_stop['choice']['device'] == 'cpu')

    # ── G3 across processes: the real child entry, and a child that crashes ─────────────────────────────────────
    out = subprocess.run([sys.executable, str(BASE / 'launch.py'), '--engine-probe', 'nonsense'],
                         capture_output=True, text=True, timeout=60)
    line = (out.stdout or '').strip().splitlines()[-1:] or ['']
    try:
        said = json.loads(line[0])
    except ValueError:
        said = {}
    check('s233 G3 launch.py --engine-probe is dispatched before Flask and answers with one JSON line',
          out.returncode == 0 and said.get('ok') is False and 'unknown probe' in said.get('error', ''))
    launch_src = (BASE / 'launch.py').read_text(encoding='utf-8')
    main_src = launch_src[launch_src.index('def main('):]
    check('s233 G3 the probe is dispatched as early as the bank windows: before logging, Flask and the engine',
          main_src.index("'--engine-probe'") < main_src.index('logging.basicConfig')
          < main_src.index('_start_server'))
    real_cmd = ef.probe_command
    try:
        ef.probe_command = lambda args: [sys.executable, '-c', 'import os; os._exit(3)']
        crashed = ef.run_probe(['gpu', '0'], 30)
        ef.probe_command = lambda args: [sys.executable, '-c', 'import time; time.sleep(30)']
        hung = ef.run_probe(['gpu', '0'], 2)
    finally:
        ef.probe_command = real_cmd
    check('s233 G3 a probe process that dies without a word is a failed device, with its exit code said',
          crashed['ok'] is False and 'exit 3' in crashed['error'])
    check('s233 G3 a probe that hangs is stopped at its time limit and failed', hung['ok'] is False
          and 'within 2 s' in hung['error'])

    # ── G6: when to fit again ───────────────────────────────────────────────────────────────────────────────────
    fp = {'fit_version': ef.FIT_VERSION, 'engine': '0.3.35', 'graphics_build': True, 'model': engine.MODEL_SHA256,
          'machine': 'AMD64', 'processor': 'x', 'graphics': ['Chip A|1.0', 'Chip B|2.0']}
    kept = dict(rec, fingerprint=fp)
    check('s233 G6 an unchanged computer is not fitted again', ef.needs_fit(kept, dict(fp)) is False)
    check('s233 G6 a new graphics driver, a new engine or a new model fits again',
          all(ef.needs_fit(kept, dict(fp, **ch)) for ch in ({'graphics': ['Chip A|1.0', 'Chip B|2.1']},
                                                             {'engine': '0.3.36'}, {'model': 'other'},
                                                             {'fit_version': ef.FIT_VERSION + 1})))
    check('s233 G6 no result yet, or a device that failed at a launch, fits again',
          ef.needs_fit(None, fp) and ef.needs_fit(dict(kept, refit=True), fp))

    # ── G6 in the engine: a launch that died in the driver; a chip that won't start ─────────────────────────────
    real = (ef.has_graphics_backend, ef.fingerprint, ef.fit, ef.load_backends)
    fitted = []
    try:
        ef.has_graphics_backend = lambda: True
        ef.fingerprint = lambda: fp
        ef.fit = lambda **kw: fitted.append(1) or dict(rec)
        ef.write_fit(dict(kept, pending_launch=True))
        choice, _ = engine._fitted_choice(engine._generation)
        after = ef.read_fit()
        check('s233 G6 the last launch died starting the graphics chip: this one runs on the processor, '
              'says so, and marks the next to fit again',
              choice['device'] == 'cpu' and after['refit'] is True and after['pending_launch'] is False
              and not fitted and 'could not start this time' in engine._state['device']['line'])
        choice, _ = engine._fitted_choice(engine._generation)
        check('s233 G6 ... and the next launch fits again, then uses the result', fitted == [1]
              and choice['device'] == 1 and ef.read_fit()['fingerprint'] == fp and not ef.read_fit().get('refit'))
        choice, _ = engine._fitted_choice(engine._generation)
        check('s233 G6 an unchanged computer after that is not fitted again', fitted == [1] and choice['device'] == 1)

        def no_chip(graphics):
            raise RuntimeError('the driver refused')
        ef.load_backends = no_chip
        r = ef.read_fit()
        got = engine._load_on_graphics('unused', None, r['choice'], r)
        after = ef.read_fit()
        check('s233 G6 a fitted chip that will not start: the processor is used now, and the next launch fits again',
              got is None and after['refit'] is True and after['pending_launch'] is False
              and engine._state['device']['running'] == 'cpu')
    finally:
        ef.has_graphics_backend, ef.fingerprint, ef.fit, ef.load_backends = real
        import os
        os.environ.pop('GGML_VK_VISIBLE_DEVICES', None)
        fit_file.unlink(missing_ok=True)
        engine._state['device'] = None

    # ── G1: this build with no graphics backend fits nothing ────────────────────────────────────────────────────
    if not ef.has_graphics_backend():
        choice, r = engine._fitted_choice(engine._generation)
        check('s233 G1 an engine build with no graphics backend runs on the processor and runs no fitting',
              choice['device'] == 'cpu' and r is None and not fit_file.exists())
        engine._state['device'] = None

    # ── G7: the sentence ────────────────────────────────────────────────────────────────────────────────────────
    measured = {'checked': '2026-10-17', 'choice': {'device': 1, 'name': 'NVIDIA RTX A1000 Laptop GPU', 'kind': 'card',
                                                    'layers': -1},
                'results': [{'device': 'cpu', 'name': "this computer's processor", 'verdict': 'ran',
                             'probe': {'ok': True, 'answer_s': 32.4}},
                            {'device': 0, 'name': 'Intel(R) Iris(R) Xe Graphics', 'verdict': 'r8',
                             'probe': {'ok': True, 'answer_s': 21.6, 'r8': {'mixed_movement': ['50']}}},
                            {'device': 1, 'name': 'NVIDIA RTX A1000 Laptop GPU', 'verdict': 'chosen',
                             'probe': {'ok': True, 'answer_s': 9.09}},
                            {'device': 2, 'name': 'Old Card', 'verdict': 'failed', 'probe': {'ok': False}},
                            {'device': 3, 'name': 'Slow Chip', 'verdict': 'ran', 'probe': {'ok': True, 'answer_s': 40}}]}
    d = ef.describe(measured)
    check('s233 G7 the line names the device, its time, how it was measured, the gain over the processor, the date',
          d['line'] == ("AI runs on NVIDIA RTX A1000 Laptop GPU - answers in about 9 s on Groundwork's test answer, "
                        "3.6x faster than this computer's processor (about 32 s) (checked 17 Oct 2026)."))
    check('s233 G7 every other device tried is accounted for: the invented figure, the failure, the slower time',
          d['tried'] == ["Intel(R) Iris(R) Xe Graphics was tried and wrote a figure that wasn't in the facts it was "
                         "given, so Groundwork doesn't use it.",
                         'Old Card was tried and could not run the model.',
                         'Slow Chip was tried: answers in about 40 s.'])
    part = ef.describe(dict(measured, choice=dict(measured['choice'], layers=16)))
    check('s233 G7 a card holding part of the model says how much', 'part of the model (16 of its layers)' in part['line'])
    check('s233 G7 the processor chosen says so, with its own time',
          ef.describe(dict(measured, choice={'device': 'cpu', 'name': 'p', 'kind': 'cpu', 'layers': 0}))['line']
          == "AI runs on this computer's processor - answers in about 32 s on Groundwork's test answer "
             "(checked 17 Oct 2026).")

    # ── G5 + G7 through the route ───────────────────────────────────────────────────────────────────────────────
    saved = dict(engine._state)
    try:
        engine._state.update(state='ready', reason='', device={'running': 1, **d})
        st = (c.get('/api/ai/status', headers=H).get_json() or {}).get('data') or {}
        check('s233 G7 Settings receives the line and the devices tried while the engine is ready',
              st.get('device_line') == d['line'] and st.get('device_tried') == d['tried'])
        engine._state.update(state='fitting')
        st = (c.get('/api/ai/status', headers=H).get_json() or {}).get('data') or {}
        check('s233 G5 fitting is its own visible state, with its message, and counts as on its way (not off)',
              st.get('engine') == 'fitting' and 'fitting the local AI to this computer' in st.get('message', '')
              and st.get('available') is True and st.get('device_line') == '')
        engine._ready.set()
        r = engine.chat('s', [{'role': 'user', 'content': 'q'}])
        check('s233 G5 an AI call during fitting is told why, not left hanging',
              r['ok'] is False and r['reason'] == 'fitting')
    finally:
        engine._state.clear()
        engine._state.update(saved)

    # ── G0: nothing lets anyone set the device ──────────────────────────────────────────────────────────────────
    server_src = (BASE / 'server.py').read_text(encoding='utf-8')
    app_src = (BASE / 'static/js/app.js').read_text(encoding='utf-8')
    tree = ast.parse(server_src)
    routes = [a.value for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, 'attr', '') == 'route'
              for a in n.args[:1] if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    check('s233 G0 no route sets, changes or re-runs the device choice',
          not [r for r in routes if any(w in r.lower() for w in ('device', 'fit', 'gpu', 'graphics'))
               and not r.startswith('/bank-agent/')])     # the bank agent's own browser-profile route, item 57
    check('s233 G0 only the engine writes the fit; the server and the page never touch it',
          'engine_fit' not in server_src and 'engine_fit' not in app_src and 'write_fit' not in server_src)
    check('s233 G7 the page shows the sentences as text, with no control beside them',
          '${esc(data.device_line)}' in app_src and 'device_choice' not in app_src and 'setDevice' not in app_src)

    # ── G1 / G2: the build ──────────────────────────────────────────────────────────────────────────────────────
    spec = (BASE / 'groundwork.spec').read_text(encoding='utf-8')
    bat = (BASE / 'build_engine_wheel.bat').read_text(encoding='utf-8')
    check('s233 G1 the Windows release build refuses an engine with no Vulkan backend',
          "glob('ggml-vulkan*.dll')" in spec and 'build_engine_wheel.bat' in spec)
    check('s233 G1/G2 the engine wheel: Vulkan only, backends at run time, no native tuning, the AVX2 floor',
          all(f in bat for f in ('-DGGML_VULKAN=ON', '-DGGML_BACKEND_DL=ON', '-DGGML_NATIVE=OFF', '-DGGML_AVX2=ON',
                                 'llama-cpp-python==0.3.35')) and '-DGGML_CUDA' not in bat)
    check("s233 G3 the probe's modules are bundled", "'core.engine_fit', 'voice_discipline_test'" in spec)
