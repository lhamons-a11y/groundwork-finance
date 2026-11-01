#!/usr/bin/env python3
"""Item 115 stages 5 and 6 (gw 2.0/ASK_FOR_A_REPORT.md section 6): Rob's 25 report requests, read by the index.

    python scripts/report_requests_measure.py                    index alone (stage 5) - no model
    python scripts/report_requests_measure.py --model PATH       also the helpers (stage 6), phi3.5 on Metal
    python scripts/report_requests_measure.py --out DIR          write the results there as JSON

Runs tests/report_requests.json (and, with --model, tests/report_helper_cases.json) against the sample household,
built fresh in a throwaway folder. Nothing is written to the person's own Groundwork. Each request is scored on its
outcome, its sections and their settings, every period read by core/periods.py, its time, and whether any figure
reached the reading from the model (it never may: the helpers answer with a name from a list).
"""
import argparse
import json
import re
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUESTS = ROOT / 'tests' / 'report_requests.json'
HELPER_CASES = ROOT / 'tests' / 'report_helper_cases.json'
HELD_OUT = ROOT / 'tests' / 'report_requests_heldout.json'


def _same_settings(got, want, today):
    from core import periods
    for k, v in want.items():
        g = got.get(k)
        if k in ('period', 'period_b'):
            a, b = periods.read_period(str(g or ''), today), periods.read_period(str(v), today)
            if not a or not b or a['months'] != b['months'] or bool(a.get('window')) != bool(b.get('window')):
                return False
        elif isinstance(g, list) and len(g) == 1 and str(g[0]).lower() == str(v).lower():
            continue
        elif str(g or '').lower() != str(v).lower():
            return False
    extra = {k for k in got if k not in want and k not in ('period',)}
    return not extra


def score(r, want, today):
    """One request: outcome right; sections right (ids in order, settings the same); nothing wrong built."""
    ok_outcome = r['outcome'] == want['outcome']
    ws = want.get('sections') or []
    gs = r['sections'] if r['outcome'] not in ('clarify', 'does_not_know', 'none') else []
    if want['outcome'] in ('clarify', 'does_not_know'):
        ok_sections = not gs
    else:
        ok_sections = len(gs) == len(ws) and all(g['id'] == w['id'] and _same_settings(g['settings'], w['settings'], today)
                                                 for g, w in zip(gs, ws))
    wrong_built = bool(gs) and not ok_sections
    ok_style = r.get('style') == want.get('style')
    return {'outcome_ok': ok_outcome, 'sections_ok': ok_sections and ok_style, 'wrong_section_built': wrong_built,
            'style_ok': ok_style}


def child(out_path, model_path):
    sys.path.insert(0, str(ROOT))
    from datetime import date
    from server import create_app, _GW_TOKEN
    from core.database import db_session
    from core import agent_hands as ah, report_index as ri, report_sections as rs

    app = create_app()
    c = app.test_client()
    H = {'X-GW-Token': _GW_TOKEN, 'Content-Type': 'application/json'}
    c.patch('/api/settings', headers=H, data=json.dumps({'terms_accepted': 'v-test', 'ai_enabled': 'false'}))
    assert c.post('/api/sample/load', headers=H).get_json().get('ok')

    def get(path):
        d = c.get(path, headers=H).get_json(silent=True)
        return d.get('data', d) if isinstance(d, dict) and 'data' in d else d
    today = date.today()
    reader = ah.Reader(get, db_session, today)
    reqs = [dict(q, set='rob') for q in json.loads(REQUESTS.read_text())['requests']]
    reqs += [dict(q, set='held_out') for q in json.loads(HELD_OUT.read_text())['requests']]
    results = {'when': time.strftime('%Y-%m-%d %H:%M'), 'today': today.isoformat(), 'index': [], 'helpers': []}
    for q in reqs:
        t0 = time.perf_counter()
        r = ri.read(reader, q['ask'])
        ms = round((time.perf_counter() - t0) * 1000, 1)
        built = [rs.run(reader, s['id'], s['settings']) for s in r['sections']] if r['outcome'] not in (
            'clarify', 'does_not_know', 'none') else []
        results['index'].append({'id': q['id'], 'set': q['set'], 'style': r.get('style'), 'ask': q['ask'], 'want': q['expect']['outcome'], 'got': r['outcome'],
                                 'sections': r['sections'], 'question': r.get('question'), 'said': r['said'],
                                 'choices': [ch['label'] for ch in r.get('choices') or []], 'ms': ms,
                                 'step': r['step'], 'first_sentences': [b['sentences'][:1] for b in built],
                                 **score(r, q['expect'], today)})

    if model_path:
        from llama_cpp import Llama, LlamaGrammar, llama_supports_gpu_offload
        from core import engine
        llm = Llama(model_path=str(model_path), n_ctx=engine.N_CTX, n_batch=engine.N_BATCH, n_ubatch=engine.N_BATCH,
                    use_mmap=engine.USE_MMAP, flash_attn=engine.FLASH_ATTN, verbose=False,
                    n_gpu_layers=-1 if llama_supports_gpu_offload() else 0)
        engine.install_stops(llm)
        engine._model = llm
        engine._state['state'] = 'ready'
        cases = json.loads(HELPER_CASES.read_text())['cases']
        for q in cases:
            t0 = time.perf_counter()
            r = ri.read(reader, q['ask'], helper=engine.pick_label)
            s = round(time.perf_counter() - t0, 2)
            want = q['expect']
            got_names = [v for sec in r['sections'] for k, v in sec['settings'].items()
                         if k in ('category', 'payee', 'debt', 'exclude')]
            got_names = [x for v in got_names for x in (v if isinstance(v, list) else [v])]
            ok_out = r['outcome'] == want['outcome'] or (want['outcome'] == 'build' and r['outcome'] == 'build_and_say')
            right = (ok_out and all(n in got_names for n in want.get('names', []))
                     and (not want.get('any_of') or any(n in got_names for n in want['any_of']))
                     and (not want.get('sections') or [x['id'] for x in r['sections']] == want['sections']))
            ans = next((h['answer'] for h in reversed(r['helpers'])), None)
            likely = next((ch for ch in r.get('choices') or [] if ch.get('likely')), None)
            if want['outcome'] in ('clarify', 'none') or (want['outcome'] == 'build_and_say' and not want.get('names')):
                helper_right = ans in (None, ri.CANT_TELL)
            elif want.get('sections'):
                helper_right = bool(likely) and [x['id'] for x in likely['sections']] == want['sections']
            else:
                helper_right = ans in (want.get('names') or []) + (want.get('any_of') or [])
            alone = ri.read(reader, q['ask'])             # what the index does without the helper, for comparison
            results['helpers'].append({'id': q['id'], 'helper': q['helper'], 'ask': q['ask'], 'want': want,
                                       'got': r['outcome'], 'sections': r['sections'], 'said': r['said'],
                                       'asked': r['helpers'], 's': s, 'right': right, 'helper_right': helper_right, 'index_alone': alone['outcome'],
                                       'model_figures': [h for h in r['helpers'] if h['answer'] and re.search(r'\d', h['answer'])]})
        # H-d (P9): suggestions from a planted miss log - each one for Rob to say whether he would accept it
        planted = [{'said': 'What did the dog cost us this year?', 'picked': 'Pet Food / Supplies'},
                   {'said': 'How much on the wifi?', 'picked': None},
                   {'said': 'What do workouts cost us each month?', 'picked': 'Gym / Fitness'},
                   {'said': 'How much did the kids\' piano lessons cost?', 'picked': 'All spending'},
                   {'said': 'Show me date nights last month', 'picked': 'Restaurants'},
                   {'said': 'What are the tunes costing us?', 'picked': None}]
        t0 = time.perf_counter()
        results['h_d'] = {'planted': planted, 'suggestions': ri.suggest_terms(reader, planted, engine.pick_label),
                          's': round(time.perf_counter() - t0, 2)}
    Path(out_path).write_text(json.dumps(results, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model')
    ap.add_argument('--out', default=str(ROOT / 'tests' / 'report_requests_results'))
    ap.add_argument('--child', help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.child:
        child(a.child, a.model)
        return
    tmp = tempfile.mkdtemp(prefix='gw_report_measure_')
    res = os.path.join(tmp, 'results.json')
    env = {**os.environ, 'GROUNDWORK_DATA_DIR': tmp}
    subprocess.run([sys.executable, __file__, '--child', res] + (['--model', a.model] if a.model else []),
                   env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = json.loads(Path(res).read_text())
    idx = d['index']
    print(f"Index alone, {len(idx)} requests ({d['today']}):")
    for x in idx:
        mark = 'ok ' if x['outcome_ok'] and x['sections_ok'] else 'MISS'
        print(f"  {mark} {x['id']} want {x['want']:<14} got {x['got']:<14} {x['ms']:>6} ms  "
              f"{[s['id'] + ' ' + json.dumps(s['settings']) for s in x['sections']] if x['sections'] else (x['question'] or '')}")
        if mark == 'MISS':
            print(f"       {x['ask']}  said={x['said']} choices={x['choices']}")
    for name in ('rob', 'held_out'):
        xs = [x for x in idx if x['set'] == name]
        right = sum(1 for x in xs if x['outcome_ok'] and x['sections_ok'])
        print(f"  {name}: right {right} / {len(xs)}; wrong section built: {sum(1 for x in xs if x['wrong_section_built'])}; "
              f"slowest {max(x['ms'] for x in xs)} ms")
    if d['helpers']:
        print('Helpers (phi3.5):')
        for x in d['helpers']:
            print(f"  {'ok ' if x['helper_right'] else 'MISS'} {x['id']} {x['helper']} {x['s']:>5} s  {x['ask']}  -> {x['got']} "
                  f"{[s['id'] + ' ' + json.dumps(s['settings']) for s in x['sections']]} {x['asked']}")
        for h in ('H-a', 'H-b', 'H-c'):
            xs = [x for x in d['helpers'] if x['helper'] == h]
            print(f"  {h}: helper right {sum(1 for x in xs if x['helper_right'])} / {len(xs)}")
        print(f"  helper right: {sum(1 for x in d['helpers'] if x['helper_right'])} / {len(d['helpers'])}; "
              f"slowest {max(x['s'] for x in d['helpers'])} s")
    if d.get('h_d'):
        print(f"H-d from {len(d['h_d']['planted'])} planted misses ({d['h_d']['s']} s):")
        for x in d['h_d']['suggestions']:
            print(f"  \"{x['said']}\" means {x['means']} ({x['kind']})")
    os.makedirs(a.out, exist_ok=True)
    name = time.strftime('%Y%m%d-%H%M') + ('-m2-helpers' if a.model else '-index') + '.json'
    Path(a.out, name).write_text(json.dumps(d, indent=1, default=str))
    print('written', Path(a.out, name))


if __name__ == '__main__':
    main()
