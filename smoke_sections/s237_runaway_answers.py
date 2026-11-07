"""Item 97 (gw 2.0/RUNAWAY_ANSWERS.md; Rob 2026-10-18: U1-U7 as recommended): answers that don't end.

    U1  every call into the model stops at a run of three newlines, and at the model's role tokens; a cut answer
        reports the engine's own 'stop', so item 12's R10 / K3 read it as finished
    U2  every create_chat_completion in shipped and measuring code passes STOP, and every model built gets the
        role-token stops (install_stops) - scanned, so a new caller can't skip them; the runtime spike is the one
        exemption, a frozen historical record
    U3  probed per kind of caller before the stop went in (RUNAWAY_ANSWERS.md, "Built"): no real answer uses a run of
        three newlines; where one appeared it began a runaway
    U4  fitting compares a chip with the processor on the same six voice answers (G4'' (a))
    U5  the engine's quoted baseline says it doesn't reproduce and names the reference
The A/B on the built engine (U6) is in RUNAWAY_ANSWERS.md; U7 (master only) is the branch this runs on.
"""
import ast


SKIP_DIRS = {'tests', 'smoke_sections', 'build', 'dist', 'installer_output', 'node_modules', 'vendor', '.claude', 'engine_wheel'}
EXEMPT = {'llm_runtime_spike.py': 'the historical record of how the runtime was chosen (item 31) - not what ships'}


def _py_files(base):
    for p in sorted(base.rglob('*.py')):
        rel = p.relative_to(base)
        if rel.parts[0] in SKIP_DIRS or any(part.startswith('.') for part in rel.parts):
            continue
        yield rel.as_posix(), p


def _is_stop(node):
    return (isinstance(node, ast.Name) and node.id == 'STOP') or (isinstance(node, ast.Attribute) and node.attr == 'STOP')


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    from core import engine
    from core import engine_fit as ef

    # ── U1: the stops ───────────────────────────────────────────────────────────────────────────────────────────
    check('s237 U1 the stop is a run of three newlines - paragraphs use one blank line, so it never cuts one',
          engine.STOP == ['\n\n\n'])
    check("s237 U1 the model's role tokens end an answer too (a runaway once began with <|user|>)",
          set(engine.ROLE_TOKENS) == {'<|end|>', '<|user|>', '<|system|>', '<|assistant|>'})

    class Inner:
        def token_get_text(self, i):
            return {1: '<s>', 2: '</s>'}.get(i, '')

    class Fake:
        metadata = {'tokenizer.chat_template': "{% for m in messages %}{{ m['content'] }}{% endfor %}"}
        _model = Inner()
        chat_handler = None
        ids = {'<|end|>': 32007, '<|user|>': 32010, '<|system|>': 32006, '<|assistant|>': 32001}

        def token_eos(self):
            return 2

        def token_bos(self):
            return 1

        def tokenize(self, b, add_bos=False, special=False):
            t = b.decode()
            return [self.ids[t]] if special and t in self.ids else [9, 9, 9]

    f = Fake()
    ids = engine.install_stops(f)
    check('s237 U1 install_stops looks the role tokens up by their text and hands them to the chat handler',
          ids == [2, 32007, 32010, 32006, 32001] and callable(f.chat_handler))

    # ── U1 through chat() and chat_stream(): STOP is passed, and a cut answer is 'stop' ─────────────────────────
    seen = []

    class Model:
        def create_chat_completion(self, **kw):
            seen.append(kw)
            if kw.get('stream'):
                return iter([{'choices': [{'delta': {'content': 'A clean answer.'}}]},
                             {'choices': [{'delta': {}, 'finish_reason': 'stop'}]}])
            return {'choices': [{'message': {'content': 'A clean answer.'}, 'finish_reason': 'stop'}],
                    'usage': {'completion_tokens': 4}}

    saved_model, saved_state = engine._model, dict(engine._state)
    try:
        engine._model = Model()
        engine._state.update(state='ready')
        r = engine.chat('s', [{'role': 'user', 'content': 'q'}], max_tokens=80)
        events = list(engine.chat_stream('s', [{'role': 'user', 'content': 'q'}], max_tokens=80))
    finally:
        engine._model = saved_model
        engine._state.clear()
        engine._state.update(saved_state)
    check('s237 U1 chat() and chat_stream() pass the stops on every call',
          len(seen) == 2 and all(k.get('stop') == engine.STOP for k in seen))
    check("s237 U1 an answer the stop ended reports 'stop', so R10 and K3 treat it as finished",
          r['finish'] == 'stop' and events[-1] == ('done', 'stop'))

    # ── U2: the scan ────────────────────────────────────────────────────────────────────────────────────────────
    calls, missing, builds, unstopped = 0, [], 0, []
    for rel, p in _py_files(BASE):
        if rel in EXEMPT:
            continue
        try:
            tree = ast.parse(p.read_text(encoding='utf-8', errors='replace'))
        except SyntaxError:
            continue
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module))]:
            body_calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
            names = {getattr(c.func, 'attr', getattr(c.func, 'id', '')) for c in body_calls}
            if not isinstance(fn, ast.Module) and 'Llama' in names:
                builds += 1
                if 'install_stops' not in names:
                    unstopped.append(f'{rel}:{fn.name}')
        for c in [n for n in ast.walk(tree) if isinstance(n, ast.Call)]:
            if getattr(c.func, 'attr', '') == 'create_chat_completion':
                calls += 1
                if not any(k.arg == 'stop' and _is_stop(k.value) for k in c.keywords):
                    missing.append(f'{rel}:{c.lineno}')
    check(f's237 U2 every call into the model passes STOP ({calls} calls found; missing: {missing})',
          calls >= 7 and not missing)
    check(f's237 U2 every function that builds a model gives it the role-token stops ({builds} found; '
          f'without: {unstopped})', builds >= 3 and not unstopped)
    check('s237 U2 the one exemption is the frozen runtime spike, and it says it is historical',
          'HISTORICAL CONTROL' in (BASE / 'llm_runtime_spike.py').read_text(encoding='utf-8'))

    # ── U4: fitting compares a chip with the processor ──────────────────────────────────────────────────────────
    def res(cpu_r8, chip_r8, cpu_ok=True):
        return [{'device': 'cpu', 'name': 'p', 'kind': 'cpu',
                 'probe': {'ok': cpu_ok, 'answer_s': 30.0, 'r8': cpu_r8} if cpu_ok else {'ok': False}},
                {'device': 0, 'name': 'chip', 'kind': 'card', 'probe': {'ok': True, 'answer_s': 9.0, 'r8': chip_r8}}]
    one, two = {'a': ['50'], 'b': []}, {'a': ['50'], 'b': ['7']}
    best, _ = ef.choose(res(one, one))
    check("s237 U4 a chip with no more invented-figure answers than the processor's is admissible",
          best['device'] == 0)
    best, r = ef.choose(res(one, two))
    check("s237 U4 a chip with more of them than the processor on the same six is not used",
          best['device'] == 'cpu' and r[1]['verdict'] == 'r8')
    best, _ = ef.choose(res({}, one, cpu_ok=False))
    check("s237 U4 with no processor reading to compare, a chip must have none", best is None or best['device'] != 0)
    src = (BASE / 'core/engine_fit.py').read_text(encoding='utf-8')
    probe_body = src[src.index('def _probe('):src.index('def r8_on_voice_cases(')]
    check('s237 U4 the processor reads the same six voice answers in its own probe',
          "out['r8'] = r8_on_voice_cases(model)" in probe_body and "if mode == 'gpu':\n        out['r8']" not in probe_body)

    # ── U5: the baseline ────────────────────────────────────────────────────────────────────────────────────────
    esrc = ' '.join((BASE / 'core/engine.py').read_text(encoding='utf-8').replace('\n# ', ' ').split())
    check('s237 U5 the quoted 0/120 is marked as not reproducing, with the re-measured figures and the reference',
          'the 0/120 above does not reproduce' in esrc and '39/120 with R8 4/120' in esrc
          and 'the processor measured beside it' in esrc)
