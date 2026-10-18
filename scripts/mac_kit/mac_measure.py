#!/usr/bin/env python3
"""Item 96 / item 33 Q6: measure the in-app engine on this Mac, on the processor or on Metal. Measurement only.

    python mac_measure.py cpu   <out.jsonl>       the CPU build (venv-cpu), n_gpu_layers=0
    python mac_measure.py metal <out.jsonl>       the Metal build (venv-metal), every layer on the graphics

Loads the model with the shipped settings (core/engine.py: context, batch, f16 cache, no mmap, flash off) and the
shipped stops (engine.STOP, install_stops - item 97). Then it runs:
  1. one untimed warm-up answer (Metal compiles its shaders on first use, as Vulkan does - item 95);
  2. fitting's timing test (engine_fit.TIMING_*, temperature 0, seed 1): first word and whole answer;
  3. the voice A/B (GPU_ENGINE.md, G4''): 20 seeds x the 6 voice CASES at 512 tokens, temperature 0.3,
     set_seed(seed), scored by voice_discipline_test.check().
Every answer is written to the .jsonl; the last line is the summary. GROUNDWORK_MODEL_PATH must name the model file.
"""
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ['OPENBLAS_NUM_THREADS'] = '1'

mode, outp = sys.argv[1], Path(sys.argv[2]).resolve()
assert mode in ('cpu', 'metal'), mode
SEEDS = int(os.environ.get('KIT_SEEDS', '20'))


def peak_rss_gb():
    """This process's peak resident memory; macOS reports bytes. None where there's no resource module (Windows)."""
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2)
    except ImportError:
        return None


def free_gb():
    """Free + inactive memory as macOS counts it (vm_stat pages), in GB."""
    try:
        out = subprocess.run(['vm_stat'], capture_output=True, text=True).stdout
        page = int(out.split('page size of ')[1].split(' ')[0])
        vals = {l.split(':')[0].strip(): int(l.split(':')[1].strip().rstrip('.')) for l in out.splitlines()[1:] if ':' in l}
        return round((vals.get('Pages free', 0) + vals.get('Pages inactive', 0)) * page / 1e9, 2)
    except Exception:
        return None


from core import engine, engine_fit   # noqa: E402
import llama_cpp                       # noqa: E402
from llama_cpp import Llama            # noqa: E402
import voice_discipline_test as v      # noqa: E402

devices = engine_fit.load_backends(graphics=(mode == 'metal'))   # as the app does; a build with backends linked in
lib = Path(llama_cpp.__file__).resolve().parent / 'lib'
head = {
    'mode': mode, 'machine': platform.machine(), 'macos': platform.mac_ver()[0], 'python': platform.python_version(),
    'llama_cpp': llama_cpp.__version__, 'gpu_offload': bool(llama_cpp.llama_supports_gpu_offload()),
    'libs': sorted(f.name for f in lib.iterdir()) if lib.is_dir() else [],
    'devices': [d['name'] for d in devices], 'model': str(engine.model_path()), 'free_gb_before': free_gb(),
}
assert llama_cpp.__version__ == '0.3.35', head['llama_cpp']
if mode == 'metal' and not head['gpu_offload']:
    print(json.dumps({'ok': False, 'error': 'this build has no Metal: llama_supports_gpu_offload() is false', **head}))
    sys.exit(1)

kv = getattr(llama_cpp, engine.KV_CACHE_TYPE)
t = time.time()
model = Llama(model_path=str(engine.model_path()), n_ctx=engine.N_CTX, n_batch=engine.N_BATCH, n_ubatch=engine.N_BATCH,
              use_mmap=engine.USE_MMAP, flash_attn=engine.FLASH_ATTN, type_k=kv, type_v=kv, verbose=False,
              n_gpu_layers=-1 if mode == 'metal' else 0)
engine.install_stops(model)
head.update(load_s=round(time.time() - t, 1), free_gb_loaded=free_gb(),
            cfg=dict(n_ctx=engine.N_CTX, n_batch=engine.N_BATCH, kv=engine.KV_CACHE_TYPE, use_mmap=engine.USE_MMAP,
                     flash_attn=engine.FLASH_ATTN, stop=engine.STOP))

model.create_chat_completion(messages=[{'role': 'user', 'content': engine_fit.TIMING_USER[:1500]}],
                             max_tokens=8, temperature=0.0, seed=engine_fit.R8_SEED, stop=engine.STOP)  # warm-up
t, first = time.time(), None
for ch in model.create_chat_completion(messages=[{'role': 'system', 'content': engine_fit.TIMING_SYSTEM},
                                                 {'role': 'user', 'content': engine_fit.TIMING_USER}],
                                       max_tokens=engine_fit.TIMING_MAX_TOKENS, temperature=0.0,
                                       seed=engine_fit.R8_SEED, stream=True, stop=engine.STOP):
    if first is None and (ch['choices'][0].get('delta') or {}).get('content'):
        first = time.time() - t
head.update(first_word_s=round(first or 0, 2), answer_s=round(time.time() - t, 2))

f = open(outp, 'w', encoding='utf-8')
f.write(json.dumps(head) + '\n')
f.flush()
print(f"{mode}: loaded in {head['load_s']} s, first word {head['first_word_s']} s, whole test answer "
      f"{head['answer_s']} s; free memory {head['free_gb_before']} -> {head['free_gb_loaded']} GB", flush=True)

gate = r8 = capped = 0
t0 = time.time()
for seed in range(1, SEEDS + 1):
    for c in v.CASES:
        model.set_seed(seed)
        out = model.create_chat_completion(messages=[{'role': 'system', 'content': v.SYSTEM_PROMPT},
                                                     {'role': 'user', 'content': c.findings}],
                                           max_tokens=512, temperature=0.3, seed=seed, stop=engine.STOP)
        text = out['choices'][0]['message']['content'] or ''
        fin = out['choices'][0].get('finish_reason')
        p, n, hard, _ = v.score_output(text, c)
        invented = sorted(x for x in v._financial_numbers(text) if x not in v._financial_numbers(c.findings))
        ok = p == n and bool(text.strip())
        gate += ok
        r8 += bool(invented)
        capped += fin == 'length'
        f.write(json.dumps({'seed': seed, 'case': c.name, 'pass': ok, 'invented': invented, 'finish': fin,
                            'fails': sorted(k for k, (good, _) in hard.items() if not good), 'text': text}) + '\n')
        f.flush()
    print(f'  seed {seed}/{SEEDS}: gate {gate}, R8 {r8}, {time.time() - t0:.0f} s', flush=True)

summary = {'summary': True, 'mode': mode, 'n': SEEDS * len(v.CASES), 'gate': gate, 'r8': r8, 'to_the_cap': capped,
           'secs': round(time.time() - t0), 'peak_rss_gb': peak_rss_gb(),
           'first_word_s': head['first_word_s'], 'answer_s': head['answer_s'], 'load_s': head['load_s'],
           'free_gb_before': head['free_gb_before'], 'free_gb_loaded': head['free_gb_loaded']}
f.write(json.dumps(summary) + '\n')
f.close()
print('SUMMARY ' + json.dumps(summary), flush=True)
