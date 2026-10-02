#!/usr/bin/env python3
"""
GROUNDWORK 8 GB MACHINE TEST - the hard completion gate for the in-app engine (ENGINE_REPLACEMENT.md, item 31, R-d)
===============================================================================================================
Rob, 2026-10-02: "A real 8 GB machine is a completion criterion for the engine replacement; the 34 GB development
machine cannot substitute for that test." This script IS that test. Run it ON the 8 GB machine, against the
packaged Groundwork, with the machine in its ordinary state (antivirus, updates, a browser - whatever it normally
runs). It never touches the machine's own Groundwork data: it starts Groundwork with a throwaway data folder.

    python engine_8gb_test.py "C:\\path\\to\\Groundwork"        (the folder holding Groundwork.exe and models\\)

What it establishes, one line each (the ruling's six points):
  1. the model loads reliably          load time, and the engine's state - never a crash of the app
  2. Groundwork stays usable           ordinary requests timed WHILE the model loads and WHILE it generates
  3. AI completes its intended work    a real narration-shaped request finishes, and how long it took
  4. memory pressure is tolerable      free memory, swap in use and hard page faults - before, loaded, generating
  5. closing releases the model        the window closed normally; memory comes back; the process exits
  6. a second launch works normally    launch again, load again, answer again

It is a CONFIGURATION-SELECTION test (Rob, 2026-10-02: "make the 8 GB configuration work"). It runs:
  shipping        the engine as it ships (2048 context, batch 256, full-precision cache, OpenBLAS at one thread),
                  twice - the second run is point 6
  next_lever      the same with an 8-bit KV cache: about 0.4 GB less, but R8-DISQUALIFIED in the voice A/B (2
                  violations in 120). Measured here only so Rob can see what it would buy on this machine; it is not
                  shippable unless re-validated.
The target (Rob): Groundwork stays responsive, the AI request completes, and sustained memory pressure does not
turn ordinary use into disk-bound behaviour - not "zero paging".

It prints a report and writes it beside itself (engine_8gb_report.json). It passes or fails nothing on its own:
the figures go to Rob, who rules on them.
Needs: Python 3 with psutil (pip install psutil). Windows only (the packaged app is Windows).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

import psutil

PORT = 8765
BASE = f'http://127.0.0.1:{PORT}'
PROMPT_SYSTEM = ('You describe a household\'s finances plainly, from the figures given and nothing else. No advice, '
                 'no judgement, no figures that are not in the findings.')
PROMPT_USER = ('Findings: income this month $4,280.00; spending so far $2,115.40 across 19 days of 31; the largest '
               'category is Groceries at $612.33; a card balance of $3,904.12 recorded, not yet verified against a '
               'statement. Describe this month so far in about 120 words.')


def gb(n):
    return round(n / 1024 ** 3, 2)


def system_memory():
    vm, sw = psutil.virtual_memory(), psutil.swap_memory()
    return {'total_gb': gb(vm.total), 'available_gb': gb(vm.available), 'used_pct': vm.percent,
            'swap_used_gb': gb(sw.used), 'swap_total_gb': gb(sw.total)}


def hard_faults():
    """System-wide hard page faults per second over one second (pages read back from disk): the paging cliff."""
    try:
        out = subprocess.run(['typeperf', r'\Memory\Pages Input/sec', '-sc', '2'], capture_output=True, text=True,
                             timeout=15).stdout
        vals = [float(x) for x in re.findall(r'"[\d/: .]+","([\d.]+)"', out)]
        return round(vals[-1], 1) if vals else None
    except Exception:
        return None


def process_tree_memory(pid):
    """Private memory of Groundwork and its children (the WebView2 window runs as child processes)."""
    try:
        p = psutil.Process(pid)
        procs = [p] + p.children(recursive=True)
        main = p.memory_info()
        return {'groundwork_private_gb': gb(getattr(main, 'private', main.rss)),
                'with_window_gb': gb(sum(getattr(x.memory_info(), 'private', x.memory_info().rss)
                                         for x in procs if x.is_running()))}
    except psutil.Error:
        return None


def token():
    html = urllib.request.urlopen(BASE + '/', timeout=10).read().decode('utf-8', 'replace')
    m = re.search(r'window\.GW_SESSION_TOKEN="([0-9a-f]+)"', html)      # server.py injects it into the page
    return m.group(1) if m else None


def call(path, tok, body=None, timeout=300, method=None):
    req = urllib.request.Request(BASE + path, method=method or ('POST' if body is not None else 'GET'),
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header('X-GW-Token', tok)
    if body is not None:
        req.add_header('Content-Type', 'application/json')
    t = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode('utf-8'))
    return data.get('data', data), round(time.time() - t, 3)


def responsiveness(tok, seconds, label):
    """Ordinary requests, back to back, for `seconds`: the database and the page stay usable or they don't."""
    times, errors, end = [], 0, time.time() + seconds
    while time.time() < end:
        for path in ('/api/settings/bootstrap', '/api/settings', '/api/ai/status'):
            try:
                _, dt = call(path, tok, timeout=30)
                times.append(dt)
            except Exception:
                errors += 1
        time.sleep(0.2)
    times.sort()
    return {'during': label, 'requests': len(times), 'errors': errors,
            'median_s': times[len(times) // 2] if times else None,
            'p95_s': times[int(len(times) * 0.95)] if times else None, 'worst_s': times[-1] if times else None}


CONFIGS = [
    ('shipping', {}),
    ('shipping', {}),
    ('next_lever_q8_kv (R8-disqualified unless re-validated)', {'GROUNDWORK_TEST_ENGINE_KV': 'GGML_TYPE_Q8_0',
                                                                'GROUNDWORK_TEST_ENGINE_FLASH': '1'}),
]


def one_run(app_dir, data_dir, n, label='shipping', extra=None):
    run = {'run': n, 'configuration': label}
    exe = os.path.join(app_dir, 'Groundwork.exe')
    env = dict(os.environ, GROUNDWORK_DATA_DIR=data_dir, **(extra or {}))
    run['memory_before'] = system_memory()
    t0 = time.time()
    proc = subprocess.Popen([exe], env=env)
    tok = None
    for _ in range(120):                                     # the window and server, up to 60 s
        try:
            tok = token()
            if tok:
                break
        except Exception:
            pass
        time.sleep(0.5)
    run['window_up_s'] = round(time.time() - t0, 1)
    if not tok:
        run['error'] = 'Groundwork did not come up (no server answer in 60 s)'
        proc.kill()
        return run
    # AI on for this throwaway data folder, so the engine loads (as a user who turned it on would have it).
    call('/api/settings', tok, {'ai_enabled': 'true'}, method='PATCH')
    load_t = time.time()
    run['responsive_while_loading'] = responsiveness(tok, 8, 'model loading')
    state = None
    for _ in range(240):                                     # the load, up to 120 s
        state, _ = call('/api/ai/status', tok)
        if state.get('engine') in ('ready', 'unavailable'):
            break
        time.sleep(0.5)
    run['engine'] = {'state': state.get('engine'), 'reason': state.get('reason'), 'message': state.get('message'),
                     'reported_load_s': state.get('load_seconds'), 'observed_s': round(time.time() - load_t, 1)}
    run['memory_loaded'] = {**system_memory(), **(process_tree_memory(proc.pid) or {}), 'hard_faults_per_s': hard_faults()}
    if state.get('engine') == 'ready':
        import threading
        box = {}

        def ask():
            try:
                box['out'], box['s'] = call('/api/ai/chat', tok, {'system': PROMPT_SYSTEM, 'max_tokens': 300,
                                                                   'messages': [{'role': 'user', 'content': PROMPT_USER}]})
            except Exception as e:                           # recorded, never hidden
                box['err'] = repr(e)
        th = threading.Thread(target=ask)
        th.start()
        time.sleep(1)
        run['responsive_while_generating'] = responsiveness(tok, 6, 'AI generating')
        run['memory_generating'] = {**system_memory(), 'hard_faults_per_s': hard_faults()}
        th.join(600)
        out = box.get('out') or {}
        text = ' '.join(b.get('text', '') for b in (out.get('content') or []))
        run['ai'] = {'completed': bool(text), 'seconds': box.get('s'), 'stop_reason': out.get('stop_reason'),
                     'words': len(text.split()), 'error': box.get('err') or (out.get('message') if not text else None),
                     'sample': text[:200]}
    # Close the window the way a user does (a close message, not a kill), and watch the memory come back.
    subprocess.run(['taskkill', '/PID', str(proc.pid)], capture_output=True)
    released, exited = None, None
    for i in range(60):
        time.sleep(0.5)
        mem = process_tree_memory(proc.pid)
        if mem and released is None and mem['groundwork_private_gb'] < 1.0:
            released = round((i + 1) * 0.5, 1)
        if proc.poll() is not None:
            exited = round((i + 1) * 0.5, 1)
            break
    if proc.poll() is None:
        proc.kill()
    run['close'] = {'model_released_s': released, 'process_exited_s': exited}
    time.sleep(3)
    run['memory_after'] = system_memory()
    return run


def main():
    if sys.platform != 'win32' or (len(sys.argv) < 2 and not getattr(sys, 'frozen', False)):
        print(__doc__)
        return 2
    app_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(sys.executable), 'Groundwork')
    if not os.path.exists(os.path.join(app_dir, 'Groundwork.exe')):
        print('No Groundwork.exe in', app_dir)
        return 2
    try:
        urllib.request.urlopen(BASE + '/', timeout=2)
        print(f'Something is already answering on port {PORT}: close Groundwork first.')
        return 2
    except Exception:
        pass
    report = {'when': time.strftime('%Y-%m-%d %H:%M'), 'machine': {
        'cpu': os.environ.get('PROCESSOR_IDENTIFIER', ''), 'cores': psutil.cpu_count(logical=False),
        'threads': psutil.cpu_count(), **system_memory()},
        'running_processes': len(psutil.pids())}
    data_dir = tempfile.mkdtemp(prefix='gw_8gb_test_')
    report['runs'] = []
    for n, (label, extra) in enumerate(CONFIGS, 1):              # the second shipping run is point 6
        print(f'run {n}: {label} ...', flush=True)
        report['runs'].append(one_run(app_dir, data_dir, n, label, extra))
        time.sleep(5)
    here = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
    path = os.path.join(here, 'engine_8gb_report.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))
    print('\nreport written to', path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
