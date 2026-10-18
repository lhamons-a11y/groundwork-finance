"""Fitting the local AI engine to this computer (item 95, gw 2.0/GPU_ENGINE.md; Rob 2026-10-17: G0-G9, G4' (a)).

The engine can run the model on the processor or on a graphics chip (Vulkan: NVIDIA, AMD, Intel). Which is fastest
depends on the computer, so Groundwork measures it here, once, and uses the result:

    G0  the software chooses; nothing in the app lets the user change it (AI on/off stays theirs)
    G1  the graphics backend is a separate library loaded at run time, only if it loads; the processor always works
    G3  each device is tried in its OWN short-lived process (a driver that crashes takes down only its test), and the
        device with the shortest whole-answer time wins
    G4' a graphics device's answers to the six voice cases are read for figures not in their facts (R8); G4'' (a) and
        item 97 U4: the processor reads the same six, and a chip is out only when it has MORE such answers than the
        processor had on the same test (a single read flagged any device ~5-18% of the time - a draw, not a signal)
    G5  (a) a visible step, the first time AI starts on a computer
    G6  fitted again only when the hardware, a driver, the engine or the model changes - or when the chosen device
        failed at a launch (that launch uses the processor)
    G7  the result is shown, as a sentence; G8 AI off fits nothing (only engine._load calls in here)

This module never imports llama_cpp at module level; the probes run in child processes started from launch.py
(--engine-probe), and the parent only reads their last line of JSON.
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

FIT_VERSION = 1                 # bump when what fitting measures changes; a changed version fits again (G6)
FIT_FILE = 'engine_fit.json'    # beside the database: a property of this computer, not of the household's record
PROBE_TIMEOUT = 900             # seconds for one device's whole test (a slow processor: load + one long answer)
LIST_TIMEOUT = 60
PARTIAL_LAYERS = (24, 16, 8)    # a card too small for the whole model takes part of it (G3)

# The timed answer: about 1,000 tokens of facts and one question, the size of a real narration's prompt.
TIMING_SYSTEM = 'You explain a household budget in plain words. Use only the facts given.'
TIMING_USER = (' '.join(f'On 2026-09-{d:02d} the checking account paid ${17 * d + 3}.{d:02d} to Store {d}.'
                        for d in range(1, 29))
               + ' Rent of $950 is due on the 1st, a $310 car payment on the 5th, and a $1,600 paycheck arrives on'
                 ' the 3rd. Checking has $1,240. Is the car payment covered? Explain why.')
TIMING_MAX_TOKENS = 300
R8_TEMPERATURE = 0.3            # the shipped narration temperature (G4' (a): one seed, the shipped temperature)
R8_SEED = 1
R8_MAX_TOKENS = 512             # as the voice A/B


# ── Where the result lives ────────────────────────────────────────────────────────────────────────────────────────
def fit_path():
    override = os.environ.get('GROUNDWORK_DATA_DIR')
    if override:
        return Path(override) / FIT_FILE
    from core.database import DATA_DIR
    return Path(DATA_DIR) / FIT_FILE


def read_fit():
    try:
        return json.loads(fit_path().read_text(encoding='utf-8'))
    except Exception:
        return None


def write_fit(rec):
    p = fit_path()
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(rec, indent=1), encoding='utf-8')
    os.replace(tmp, p)


# ── The engine library, in whichever process is asking ─────────────────────────────────────────────────────────
def lib_dir():
    import llama_cpp
    return Path(llama_cpp.__file__).resolve().parent / 'lib'


def has_graphics_backend():
    """True when this build of the engine carries the Vulkan backend (the item 95 build); the CPU wheel doesn't."""
    try:
        return any(f.name.startswith('ggml-vulkan') for f in lib_dir().iterdir())
    except Exception:
        return False


def _dll(name):
    import ctypes
    lib = lib_dir()
    for f in (lib / f'{name}.dll', lib / f'lib{name}.so', lib / f'lib{name}.dylib'):
        if f.exists():
            return ctypes.CDLL(str(f))
    return None


def load_backends(graphics):
    """G1: load the run-time backends - the processor's always, the graphics one only when asked and only if it loads.
    A build with backends linked in (the CPU wheel) already has its devices, and nothing is loaded. Returns the
    devices ggml now has: [{'index', 'name', 'description', 'kind', 'free', 'total'}]."""
    import ctypes
    g, gb = _dll('ggml'), _dll('ggml-base')
    if g is None or gb is None:
        return [{'index': 0, 'name': 'CPU', 'description': '', 'kind': 'cpu', 'free': 0, 'total': 0}]
    g.ggml_backend_dev_count.restype = ctypes.c_size_t
    g.ggml_backend_dev_get.restype = ctypes.c_void_p
    g.ggml_backend_dev_get.argtypes = [ctypes.c_size_t]
    g.ggml_backend_load.restype = ctypes.c_void_p
    g.ggml_backend_load.argtypes = [ctypes.c_char_p]
    for fn in ('ggml_backend_dev_name', 'ggml_backend_dev_description'):
        getattr(gb, fn).restype = ctypes.c_char_p
        getattr(gb, fn).argtypes = [ctypes.c_void_p]
    gb.ggml_backend_dev_type.restype = ctypes.c_int
    gb.ggml_backend_dev_type.argtypes = [ctypes.c_void_p]
    gb.ggml_backend_dev_memory.restype = None
    gb.ggml_backend_dev_memory.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                                           ctypes.POINTER(ctypes.c_size_t)]

    def names():
        return [gb.ggml_backend_dev_name(g.ggml_backend_dev_get(i)).decode(errors='replace')
                for i in range(g.ggml_backend_dev_count())]

    lib = lib_dir()
    if not any(n.upper().startswith('CPU') for n in names()):
        for f in sorted(lib.glob('*ggml-cpu*')):
            if f.suffix in ('.dll', '.so', '.dylib') and g.ggml_backend_load(str(f).encode()):
                break
    if graphics and not any(n.lower().startswith('vulkan') for n in names()):
        for f in sorted(lib.glob('*ggml-vulkan*')):
            if f.suffix in ('.dll', '.so', '.dylib'):
                g.ggml_backend_load(str(f).encode())     # NULL when the driver isn't there: the processor stays (G1)
                break
    out, vk = [], 0
    for i in range(g.ggml_backend_dev_count()):
        d = g.ggml_backend_dev_get(i)
        name = gb.ggml_backend_dev_name(d).decode(errors='replace')
        free, total = ctypes.c_size_t(0), ctypes.c_size_t(0)
        gb.ggml_backend_dev_memory(d, ctypes.byref(free), ctypes.byref(total))
        t = gb.ggml_backend_dev_type(d)        # 0 processor, 1 graphics card, 2 built-in graphics, 3 accelerator
        kind = {0: 'cpu', 1: 'card', 2: 'builtin'}.get(t, 'other')
        rec = {'name': name, 'description': gb.ggml_backend_dev_description(d).decode(errors='replace'),
               'kind': kind, 'free': int(free.value), 'total': int(total.value)}
        if name.lower().startswith('vulkan'):
            rec['index'] = vk
            vk += 1
        out.append(rec)
    return out


# ── The child process: one device's test ────────────────────────────────────────────────────────────────────────
def probe_main(args):
    """launch.py --engine-probe list | cpu | gpu <vulkan index>. Prints exactly one JSON line last; exit 0."""
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    mode = args[0] if args else ''
    try:
        if mode == 'gpu':
            os.environ['GGML_VK_VISIBLE_DEVICES'] = str(int(args[1]))   # one chip at a time (G1 learned)
        if mode == 'list':
            devs = load_backends(graphics=True)
            print(json.dumps({'ok': True, 'devices': [d for d in devs if 'index' in d]}))
            return 0
        if mode not in ('cpu', 'gpu'):
            print(json.dumps({'ok': False, 'error': f'unknown probe {mode!r}'}))
            return 0
        print(json.dumps(_probe(mode)))
    except BaseException as e:                  # a Python-level failure; a native crash just ends the process
        print(json.dumps({'ok': False, 'error': repr(e)[:300]}))
    sys.stdout.flush()
    return 0


def _probe(mode):
    from core import engine
    import llama_cpp
    from llama_cpp import Llama
    devs = load_backends(graphics=(mode == 'gpu'))
    gpus = [d for d in devs if d['name'].lower().startswith('vulkan')]
    if mode == 'gpu' and not gpus:
        return {'ok': False, 'error': 'the graphics chip did not load'}
    path = engine.model_path()
    kv = getattr(llama_cpp, engine.KV_CACHE_TYPE)
    model, layers, errors = None, 0, []
    for n in ((-1,) + PARTIAL_LAYERS if mode == 'gpu' else (0,)):
        try:
            model = Llama(model_path=str(path), n_ctx=engine.N_CTX, n_batch=engine.N_BATCH, n_ubatch=engine.N_BATCH,
                          use_mmap=engine.USE_MMAP, flash_attn=engine.FLASH_ATTN, type_k=kv, type_v=kv,
                          verbose=False, n_gpu_layers=n)
            layers = n
            break
        except Exception as e:
            errors.append(repr(e)[:120])
    if model is None:
        return {'ok': False, 'error': 'the model did not load: ' + '; '.join(errors)}
    engine.install_stops(model)             # item 97 U2: what fitting measures is what ships
    if mode == 'gpu':
        # The driver compiles its shaders the first time a program uses the chip: measured on the packaged build,
        # first word 17.9 s on that first run, 0.83 s on every run after. Timed cold, a chip would be charged a cost
        # paid once per install (and could lose to the processor for it). So a short warm-up first, with a prompt
        # longer than one batch so the reading and the writing paths are both compiled; it is not timed.
        model.create_chat_completion(messages=[{'role': 'user', 'content': TIMING_USER[:1500]}],
                                     max_tokens=8, temperature=0.0, seed=R8_SEED, stop=engine.STOP)
    t = time.time()
    first = None
    for ch in model.create_chat_completion(messages=[{'role': 'system', 'content': TIMING_SYSTEM},
                                                     {'role': 'user', 'content': TIMING_USER}],
                                           max_tokens=TIMING_MAX_TOKENS, temperature=0.0, seed=R8_SEED, stream=True,
                                           stop=engine.STOP):
        if first is None and (ch['choices'][0].get('delta') or {}).get('content'):
            first = time.time() - t
    answer = time.time() - t
    out = {'ok': True, 'mode': mode, 'layers': layers, 'first_word_s': round(first or answer, 2),
           'answer_s': round(answer, 2), 'device': gpus[0]['description'] if gpus else 'processor'}
    out['r8'] = r8_on_voice_cases(model)     # U4: the processor too - it is what a chip is compared with
    return out


def r8_on_voice_cases(model):
    """G4' (a): the six voice cases, one seed, the shipped temperature; {case: [figures not in its facts]}."""
    import voice_discipline_test as v
    from core import engine
    found = {}
    for c in v.CASES:
        model.set_seed(R8_SEED)
        out = model.create_chat_completion(messages=[{'role': 'system', 'content': v.SYSTEM_PROMPT},
                                                     {'role': 'user', 'content': c.findings}],
                                           max_tokens=R8_MAX_TOKENS, temperature=R8_TEMPERATURE, seed=R8_SEED,
                                           stop=engine.STOP)
        text = out['choices'][0]['message']['content']
        ok, note = v.check(text, c).get('R8_number_provenance', (True, ''))
        found[c.name] = [] if ok else sorted(n for n in v._financial_numbers(text) if n not in
                                             v._financial_numbers(c.findings))
    return found


# ── The parent: run the probes, choose, keep the result ─────────────────────────────────────────────────────────
def probe_command(args):
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--engine-probe', *args]
    return [sys.executable, str(Path(__file__).resolve().parent.parent / 'launch.py'), '--engine-probe', *args]


def run_probe(args, timeout):
    """One child process; its last JSON line, or {'ok': False, 'error'} when it crashed, hung or said nothing."""
    flags = 0x08000000 if sys.platform == 'win32' else 0       # no console window
    try:
        p = subprocess.run(probe_command(args), capture_output=True, text=True, timeout=timeout,
                           creationflags=flags)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': f'no answer within {timeout} s'}
    except Exception as e:
        return {'ok': False, 'error': repr(e)[:200]}
    for line in reversed((p.stdout or '').strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {'ok': False, 'error': f'the test process ended without an answer (exit {p.returncode})'}


def _os_graphics():
    """The graphics chips and their driver versions, as Windows lists them - without loading any graphics code."""
    if sys.platform != 'win32':
        return []
    try:
        p = subprocess.run(['powershell', '-NoProfile', '-Command',
                            'Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion | '
                            'ConvertTo-Json -Compress'], capture_output=True, text=True, timeout=20,
                           creationflags=0x08000000)
        rows = json.loads(p.stdout or '[]')
        rows = rows if isinstance(rows, list) else [rows]
        return sorted(f"{r.get('Name')}|{r.get('DriverVersion')}" for r in rows if r)
    except Exception:
        return ['unknown']


def fingerprint():
    """What, if it changed, could change the answer (G6): the graphics chips and drivers, the engine, the model."""
    from core import engine
    import llama_cpp
    import platform
    return {'fit_version': FIT_VERSION, 'engine': getattr(llama_cpp, '__version__', ''),
            'graphics_build': has_graphics_backend(), 'model': engine.MODEL_SHA256,
            'machine': platform.machine(), 'processor': platform.processor(), 'graphics': _os_graphics()}


def needs_fit(rec, fp):
    """G6: fit when there's no result, it was made for different hardware / drivers / engine / model, or the chosen
    device failed at a launch (that launch already fell back to the processor)."""
    return not rec or rec.get('fingerprint') != fp or bool(rec.get('refit'))


def r8_count(probe):
    """How many of the six voice answers held a figure not in their facts."""
    return sum(1 for v in ((probe or {}).get('r8') or {}).values() if v)


def choose(results):
    """G3 + G4'' (a) / item 97 U4: the shortest whole-answer time among devices that ran; a graphics device only when
    it had no more R8 answers than the processor on the same six (none, if the processor's test didn't run).
    `results` = [{'device': 'cpu' | int, 'name', 'kind', 'probe': {...}}]. Returns (choice, results with 'verdict')."""
    best = None
    cpu = next((r.get('probe') for r in results if r['device'] == 'cpu'), None) or {}
    bar = r8_count(cpu) if cpu.get('ok') else 0
    for r in results:
        p = r.get('probe') or {}
        if not p.get('ok'):
            r['verdict'] = 'failed'
        elif r['device'] != 'cpu' and r8_count(p) > bar:
            r['verdict'] = 'r8'
        else:
            r['verdict'] = 'ran'
            if best is None or p['answer_s'] < best['probe']['answer_s']:
                best = r
    if best is not None:
        best['verdict'] = 'chosen'
    return best, results


def fit(run=run_probe, today=None, should_stop=lambda: False):
    """Try the processor and each graphics chip, choose, and return the record to keep (G3-G6). `should_stop` is
    asked before each test: AI switched off mid-fit tests nothing more (G8)."""
    results = [{'device': 'cpu', 'name': "this computer's processor", 'kind': 'cpu'}]
    listing = run(['list'], LIST_TIMEOUT)
    for d in (listing.get('devices') or []) if listing.get('ok') else []:
        results.append({'device': int(d['index']), 'name': d.get('description') or d.get('name'),
                        'kind': d.get('kind', 'other')})
    for r in results:
        if should_stop():
            r['probe'] = {'ok': False, 'error': 'stopped'}
            continue
        args = ['cpu'] if r['device'] == 'cpu' else ['gpu', str(r['device'])]
        r['probe'] = run(args, PROBE_TIMEOUT)
        logging.info('engine fit: %s -> %s', r['name'], {k: v for k, v in r['probe'].items() if k != 'r8'})
    best, results = choose(results)
    choice = ({'device': best['device'], 'name': best['name'], 'kind': best['kind'],
               'layers': best['probe'].get('layers', 0)} if best else
              {'device': 'cpu', 'name': "this computer's processor", 'kind': 'cpu', 'layers': 0})
    return {'checked': (today or date.today()).isoformat(), 'choice': choice, 'results': results}


# ── G7: what the user is told ───────────────────────────────────────────────────────────────────────────────────
def _when(iso):
    try:
        d = date.fromisoformat(iso)
        return f'{d.day} {d.strftime("%b")} {d.year}'
    except Exception:
        return iso or 'an earlier start'


def _secs(s):
    return f'about {round(s)} s' if s >= 2 else f'about {s:.1f} s'


def describe(rec, running=None):
    """The Settings sentences: {'line', 'tried': [...]} - every figure with how it was measured (transparency
    standard). `running` = the device actually in use this launch, when it differs from the fitted choice."""
    if not rec or not rec.get('choice'):
        return {'line': "AI runs on this computer's processor.", 'tried': []}
    ch, results = rec['choice'], rec.get('results') or []
    by = {str(r['device']): r for r in results}
    cpu = (by.get('cpu') or {}).get('probe') or {}
    mine = (by.get(str(ch['device'])) or {}).get('probe') or {}
    when = _when(rec.get('checked'))
    if running == 'cpu' and ch['device'] != 'cpu':
        line = (f"AI runs on this computer's processor for now: {ch['name']} could not start this time, so "
                f"Groundwork will fit the AI to this computer again next time it starts.")
    elif ch['device'] == 'cpu':
        line = "AI runs on this computer's processor"
        if mine.get('ok'):
            line += f" - answers in {_secs(mine['answer_s'])} on Groundwork's test answer"
        line += f' (checked {when}).'
    else:
        line = f"AI runs on {ch['name']}"
        if mine.get('ok'):
            line += f" - answers in {_secs(mine['answer_s'])} on Groundwork's test answer"
            if cpu.get('ok') and mine['answer_s'] > 0:
                x = cpu['answer_s'] / mine['answer_s']
                line += (f", {x:.1f}x faster than this computer's processor ({_secs(cpu['answer_s'])})")
            if ch.get('layers', -1) not in (-1, 0):
                line += f'; part of the model ({ch["layers"]} of its layers) is on the graphics chip, the rest on the processor'
        line += f' (checked {when}).'
    tried = []
    for r in results:
        if r.get('verdict') == 'chosen' or r['device'] == 'cpu':
            continue
        p = r.get('probe') or {}
        if r.get('verdict') == 'failed':
            tried.append(f"{r['name']} was tried and could not run the model.")
        elif r.get('verdict') == 'r8':
            tried.append(f"{r['name']} was tried and, on the same test answers, wrote more figures that weren't in the "
                         f"facts it was given than this computer's processor did, so Groundwork doesn't use it.")
        else:
            tried.append(f"{r['name']} was tried: answers in {_secs(p['answer_s'])}.")
    return {'line': line, 'tried': tried}
