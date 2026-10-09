"""Groundwork's local AI engine: the model runs inside this process (ENGINE_REPLACEMENT.md, item 31).

Rob, 2026-10-02: Ollama is gone from both lines. llama-cpp-python and the exact tested quantized phi3.5 file are the
one engine. The model ships inside Groundwork, loads at launch only when AI is enabled (R-a), and is released when
Groundwork closes. CPU always; acceleration is a later, separate test (R-c). A machine that cannot run the model gets
AI unavailable, said honestly - never a fallback service, never a crash of the rest of the app.

    Groundwork -> local engine -> model          (no port, no second process, no network)

What this module guarantees:
  - nothing is loaded until start() is called, and start() is only called by the launcher (or a toggle in the running
    app) when the user's AI setting is on; tests never load the model unless they ask to
  - the processor is checked BEFORE llama_cpp is imported: the CPU build uses AVX2/FMA unconditionally, and an
    illegal-instruction fault inside this process would take the whole app down, not just AI
  - the model file's SHA-256 must match the file that was tested, or it is not loaded
  - one call at a time (a lock); Ollama used to queue calls for us
  - stop() releases the model; the launcher calls it when the window closes
"""
import gc
import hashlib
import logging
import os

# numpy (imported by llama_cpp) brings OpenBLAS, which reserves a buffer per processor thread: measured 620 MB on a
# 20-thread machine. Groundwork does no numpy maths - the model runs in llama.cpp's own kernels - so one thread
# changes nothing the model writes (verified: identical text) and frees that memory. Must be set before numpy loads;
# launch.py sets it first thing too. setdefault: a developer's own setting wins.
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import platform
import sys
import threading
import time
from pathlib import Path

MODEL_FILE = 'phi3.5-mini-instruct-q4.gguf'
# The exact artifact tested (MODEL_PLACEMENT.md: the runtime spike and the voice A/B ran on it). Pinned; the licence
# and provenance check on this file is a release gate (ruling 8).
MODEL_SHA256 = 'b5374915da534cb93df39f03bd4f2cd5a0c533df0d5e21957dc9556c260be9eb'
# Context window and cache: the configuration the voice was validated on, chosen by measurement (2026-10-02,
# llama-cpp-python 0.3.35, CPU, ENGINE_REPLACEMENT.md s7):
#   memory (process private, model loaded)   4096 f16 cache 4.53 GB | 2048 f16 3.63 GB | 4096 q8_0 + flash 3.61 GB
#   voice A/B, 20 seeds x 6 real cases        f16 cache: gate pass 38/120, R8 violations 0
#                                             q8_0 + flash: gate pass 30/120, R8 violations 2   <- disqualified
# R8 (a figure not in the findings) is the cardinal rule, so the 8-bit cache is out even though it saves ~0.9 GB.
# The largest measured prompt + answer is ~1,720 tokens (STREAMING.md s3), so 4096 keeps headroom; 2048 gives the
# same output for anything that fits, at 3.63 GB, and is the measured fallback the real 8 GB test may choose (R-d).
# The runtime library itself is ~0.64 GB once imported - never, with AI off.
#
# Tuned for the 8 GB floor (Rob, 2026-10-02: "make the 8 GB configuration work"), memory only - never the model's
# arithmetic. Process private memory with the model loaded, measured 2026-10-02:
#   4096 ctx, f16 cache                         4.53 GB   (the first build)
#   2048 ctx, f16 cache                         3.63 GB
#   2048 ctx, f16, OpenBLAS at one thread       3.02 GB
#   2048 ctx, f16, OpenBLAS 1, batch 256        2.90 GB
#   ... and the file READ, not memory-mapped    2.83 GB resident (mapped: 4.60 GB resident)   <- shipped
#     The CPU build copies the weights into its own faster layout; a memory-mapped file then stays resident as well
#     (~1.8 GB of clean file pages). Read in once instead, only the copy remains: the free memory Groundwork takes
#     with the model loaded fell from 4.55 GB to 2.77 GB, same speed, load 1.44 s.
#   (2048 ctx, q8_0 cache: 3.19 GB before the OpenBLAS fix - still R8-disqualified, 2 violations in 120)
# The shipped configuration writes WORD FOR WORD the same text as the validated 4096 one: 12 of 12 voice cases over
# two seeds identical, so the voice A/B (R8 0/120) carries over unchanged. 2048 holds the largest measured prompt
# plus answer (~1,720 tokens, STREAMING.md s3); a longer request is refused plainly ('too_long'), never cut silently.
N_CTX = 2048
N_BATCH = 256          # prompt-processing batch: smaller compute buffers; measured not to change the output
USE_MMAP = False       # read the file in rather than map it: no second resident copy (identical text, 12 of 12)
FLASH_ATTN = False
KV_CACHE_TYPE = 'GGML_TYPE_F16'

# The 8 GB test kit compares configurations on the real machine in one visit (ENGINE_REPLACEMENT.md s9). These are
# read ONLY from the test's own variables; nothing in Groundwork sets them, and the shipped values above apply
# otherwise.
_T = os.environ.get
N_CTX = int(_T('GROUNDWORK_TEST_ENGINE_CTX', N_CTX))
N_BATCH = int(_T('GROUNDWORK_TEST_ENGINE_BATCH', N_BATCH))
KV_CACHE_TYPE = _T('GROUNDWORK_TEST_ENGINE_KV', KV_CACHE_TYPE)
FLASH_ATTN = _T('GROUNDWORK_TEST_ENGINE_FLASH', '1' if FLASH_ATTN else '') == '1'
USE_MMAP = _T('GROUNDWORK_TEST_ENGINE_MMAP', '1' if USE_MMAP else '') == '1'
LOADING_WAIT_SECONDS = 60       # a call made while the model is still loading waits this long for it

MESSAGES = {
    'off':         'Local AI is not running. Turn on AI features in Settings to start it.',
    'loading':     'The local AI model is still loading. Try again in a moment.',
    'cpu':         ("This computer's processor doesn't have the instructions Groundwork's local AI needs (AVX2), so AI "
                    "features are unavailable here. Everything else in Groundwork works normally."),
    'missing':     ("Groundwork's local AI model file is missing from this installation. Reinstalling Groundwork "
                    "restores it. Everything else works normally."),
    'checksum':    ("Groundwork's local AI model file doesn't match the file Groundwork was tested with, so it was not "
                    "loaded. Reinstalling Groundwork restores it. Everything else works normally."),
    'runtime':     ("Groundwork's local AI runtime could not be started on this computer, so AI features are "
                    "unavailable. Everything else works normally."),
    'load_failed': ("The local AI model could not be loaded on this computer, so AI features are unavailable. "
                    "Everything else works normally."),
    'too_long':    'That request is longer than the local AI model can read at once.',
}

_lock = threading.RLock()          # guards _model and every call into it: one call at a time
_ready = threading.Event()         # set when a load attempt has finished, whatever its outcome
_model = None
_state = {'state': 'off', 'reason': '', 'detail': '', 'load_seconds': None, 'verify_seconds': None}
_generation = 0                    # bumped by stop(), so a load that finishes after a stop is discarded
_allow_load = False                # only the launcher (and opt-in tests) may load the real model


def allow_load(on=True):
    """The launcher calls this once; until then start() does nothing. Keeps the gate from loading 2.2 GB."""
    global _allow_load
    _allow_load = bool(on)


def _base_dirs():
    dirs = []
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).resolve().parent
        dirs += [exe_dir, exe_dir.parent]
        # A macOS .app keeps bundled data in Contents/Resources (the executable is in Contents/MacOS) - item 33 Q4.
        if (exe_dir.parent / 'Resources').is_dir():
            dirs.append(exe_dir.parent / 'Resources')
        if getattr(sys, '_MEIPASS', None):
            dirs.append(Path(sys._MEIPASS))
    dirs.append(Path(__file__).resolve().parent.parent)
    return dirs


def model_path():
    """Where the model file is: GROUNDWORK_MODEL_PATH (tests, dev), the install's models folder, or the dev copy."""
    env = os.environ.get('GROUNDWORK_MODEL_PATH')
    if env:
        return Path(env)
    for base in _base_dirs():
        p = base / 'models' / MODEL_FILE
        if p.exists():
            return p
    for base in _base_dirs():      # a source checkout: the file staged under vendor/, named by its own hash
        p = base / 'vendor' / 'phi3.5_model' / 'blobs' / f'sha256-{MODEL_SHA256}'
        if p.exists():
            return p
    return _base_dirs()[0] / 'models' / MODEL_FILE


def cpu_supported():
    """(True, '') when this processor can run the CPU build; checked without importing llama_cpp."""
    machine = platform.machine().lower()
    if machine in ('arm64', 'aarch64'):
        return True, ''
    try:
        if sys.platform == 'win32':
            import ctypes
            k = ctypes.windll.kernel32
            # PF_AVX_INSTRUCTIONS_AVAILABLE = 39, PF_AVX2_INSTRUCTIONS_AVAILABLE = 40 (Windows 10+). Every x86 CPU
            # with AVX2 also has the FMA3 and F16C the build uses.
            ok = bool(k.IsProcessorFeaturePresent(39)) and bool(k.IsProcessorFeaturePresent(40))
            return ok, '' if ok else 'no AVX2'
        if sys.platform.startswith('linux'):
            flags = Path('/proc/cpuinfo').read_text(errors='ignore')
            ok = ' avx2' in flags
            return ok, '' if ok else 'no AVX2'
        if sys.platform == 'darwin':
            import subprocess
            out = subprocess.run(['sysctl', '-n', 'machdep.cpu.leaf7_features'], capture_output=True, text=True,
                                 timeout=5).stdout.upper()
            ok = 'AVX2' in out
            return ok, '' if ok else 'no AVX2'
    except Exception as e:
        return False, f'could not read the processor features: {e}'
    return False, 'unknown processor'


def verify(path, expected=MODEL_SHA256):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest() == expected


def status():
    """The engine's state for the UI. Deliberately lock-free: a generation holds the lock for seconds."""
    out = dict(_state)
    out['message'] = MESSAGES.get(out['reason'] or out['state'], '') if out['state'] != 'ready' else ''
    out['model_file'] = MODEL_FILE
    return out


def _set(state, reason='', detail=''):
    _state.update(state=state, reason=reason, detail=detail)


def start():
    """Begin loading in the background if allowed and not already loaded or loading. Never blocks."""
    if not _allow_load:
        return False
    with _lock:
        if _state['state'] in ('loading', 'ready'):
            return True
        _ready.clear()
        _set('loading')
        gen = _generation
    threading.Thread(target=_load, args=(gen,), daemon=True, name='groundwork-engine-load').start()
    return True


def _load(gen):
    global _model
    try:
        ok, why = cpu_supported()
        if not ok:
            return _finish(gen, None, 'cpu', why)
        path = model_path()
        if not path.exists():
            return _finish(gen, None, 'missing', str(path))
        t0 = time.time()
        if not verify(path):
            return _finish(gen, None, 'checksum', str(path))
        _state['verify_seconds'] = round(time.time() - t0, 2)
        try:
            import llama_cpp
            from llama_cpp import Llama
            kv = getattr(llama_cpp, KV_CACHE_TYPE)
        except Exception as e:                  # the native library failed to import
            return _finish(gen, None, 'runtime', repr(e))
        t1 = time.time()
        try:
            model = Llama(model_path=str(path), n_ctx=N_CTX, n_batch=N_BATCH, n_ubatch=N_BATCH, use_mmap=USE_MMAP,
                          flash_attn=FLASH_ATTN, type_k=kv, type_v=kv, verbose=False)
        except Exception as e:
            return _finish(gen, None, 'load_failed', repr(e))
        _state['load_seconds'] = round(time.time() - t1, 2)
        _finish(gen, model)
    except Exception as e:
        logging.exception('engine load failed')
        _finish(gen, None, 'load_failed', repr(e))


def _finish(gen, model, reason='', detail=''):
    global _model
    with _lock:
        if gen != _generation:                  # stopped while loading: discard what was loaded
            _close(model)
            _ready.set()
            return
        _model = model
        if model is not None:
            _set('ready')
            logging.info('engine ready (verify %ss, load %ss)', _state['verify_seconds'], _state['load_seconds'])
        else:
            _set('unavailable', reason, detail)
            logging.warning('engine unavailable: %s %s', reason, detail)
        _ready.set()


def _close(model):
    if model is None:
        return
    try:
        close = getattr(model, 'close', None)
        if close:
            close()
    except Exception:
        logging.exception('engine close failed')


def stop():
    """Release the model (AI switched off, or Groundwork closing). Safe to call at any time."""
    global _model, _generation
    with _lock:
        _generation += 1
        model, _model = _model, None
        _set('off')
        _state.update(load_seconds=None, verify_seconds=None)
        _ready.set()
    _close(model)
    del model
    gc.collect()


def is_loaded():
    return _model is not None


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('text'))
    return str(content or '')


_cancel = threading.Event()


def cancel():
    """Item 10 S6: end the generation in progress (the user pressed Stop). The stream reports 'stopped'."""
    _cancel.set()


def chat_stream(system, messages, max_tokens=1000, temperature=0.3):
    """Item 10 S3 (NARRATION_STREAMING.md): one completion, as it is written.

    Yields ('text', piece) as the model writes, then exactly one closing event: ('done', finish) with the engine's own
    finish reason ('stop' or 'length' - item 12's R10 reads it), ('stopped', None) when cancel() ended it, or
    ('error', {'reason', 'message'}). The engine's lock is held for the whole generation - one at a time, as chat() -
    and released when the generator finishes or is closed (a dropped connection closes it).
    """
    if _state['state'] == 'loading':
        _ready.wait(LOADING_WAIT_SECONDS)
    with _lock:
        if _model is None:
            st = _state['state']
            reason = _state['reason'] if st == 'unavailable' else st
            yield ('error', {'reason': reason, 'message': MESSAGES.get(reason, MESSAGES['off'])})
            return
        _cancel.clear()
        msgs = ([{'role': 'system', 'content': system}] if system else []) + [
            {'role': m.get('role', 'user'), 'content': _text_of(m.get('content'))} for m in (messages or [])]
        try:
            pieces = _model.create_chat_completion(messages=msgs, max_tokens=int(max_tokens),
                                                   temperature=float(temperature), stream=True)
        except ValueError as e:
            if 'context' in str(e).lower() or 'exceed' in str(e).lower():
                yield ('error', {'reason': 'too_long', 'message': MESSAGES['too_long']})
                return
            raise
        finish = None
        for chunk in pieces:
            if _cancel.is_set():
                yield ('stopped', None)
                return
            choice = (chunk.get('choices') or [{}])[0]
            piece = (choice.get('delta') or {}).get('content') or ''
            if piece:
                yield ('text', piece)
            if choice.get('finish_reason'):
                finish = choice['finish_reason']
        yield ('done', finish)


def chat(system, messages, max_tokens=1000, temperature=0.3):
    """One completion. {'ok': True, 'text', 'finish', 'tokens'} or {'ok': False, 'reason', 'message'}."""
    if _state['state'] == 'loading':
        _ready.wait(LOADING_WAIT_SECONDS)
    with _lock:
        if _model is None:
            st = _state['state']
            reason = _state['reason'] if st == 'unavailable' else st
            return {'ok': False, 'reason': reason, 'message': MESSAGES.get(reason, MESSAGES['off'])}
        msgs = ([{'role': 'system', 'content': system}] if system else []) + [
            {'role': m.get('role', 'user'), 'content': _text_of(m.get('content'))} for m in (messages or [])]
        try:
            out = _model.create_chat_completion(messages=msgs, max_tokens=int(max_tokens),
                                                temperature=float(temperature))
        except ValueError as e:                 # the prompt does not fit the context window
            if 'context' in str(e).lower() or 'exceed' in str(e).lower():
                return {'ok': False, 'reason': 'too_long', 'message': MESSAGES['too_long']}
            raise
    choice = (out.get('choices') or [{}])[0]
    return {'ok': True, 'text': ((choice.get('message') or {}).get('content') or '').strip(),
            'finish': choice.get('finish_reason'), 'tokens': (out.get('usage') or {}).get('completion_tokens')}
