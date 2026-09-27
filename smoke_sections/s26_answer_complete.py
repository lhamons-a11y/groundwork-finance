"""Item 12 (BUILD_QUEUE; STREAMING.md T7): a cut answer must not pass the gate.

Before this, every narrative surface handed the model a hard token cap and nothing
told the gate the answer had hit it - a report cut mid-sentence passed R1-R9 (all
its numbers present, nothing forbidden) and was shown as complete. The stop reason
exists at the provider and nowhere else, so the fix is a carry: the server maps
Ollama's done_reason onto the internal response format's stop_reason (the only
provider since the cloud path was removed - CLOUD_AI_REMOVAL.md), and callAI feeds
it to the gate as rule R10.

Measured where the failure can appear, not at the source text:
  1. the /api/ai/chat route itself, with a fake Ollama answering done_reason
     'length' / 'stop' / nothing - the server must say max_tokens / end_turn /
     unknown, and a missing field must never read as finished;
  2. the gate function itself, executed in Node from the shipped app.js, with
     truncated true / false - R10 must fail exactly when the flag says cut;
  3. the wiring: both gate call sites in callAI pass the flag, and attempt()
     derives it from stop_reason and nothing else.
"""
import io
import json
import re
import shutil
import subprocess


def run(ctx):
    check, BASE, c, HJ = ctx.check, ctx.BASE, ctx.c, ctx.HJ
    server_src = ctx.server_src
    app_src = ctx.app_src

    # ── 1. the route, against a fake Ollama ─────────────────────────────────
    import urllib.request
    import server as srv

    class _Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def _fake_urlopen_for(done_reason):
        def fake(req, timeout=None):
            url = req.full_url if hasattr(req, 'full_url') else str(req)
            if url.endswith('/api/tags'):
                return _Resp(json.dumps({'models': [{'name': 'phi3.5:latest'}]}).encode())
            body = {'message': {'role': 'assistant', 'content': 'Income was $4,280.00 this month'}, 'done': True}
            if done_reason is not None:
                body['done_reason'] = done_reason
            return _Resp(json.dumps(body).encode())
        return fake

    def ask(done_reason):
        real = urllib.request.urlopen
        urllib.request.urlopen = _fake_urlopen_for(done_reason)
        try:
            r = c.post('/api/ai/chat', headers=HJ, data=json.dumps({
                'messages': [{'role': 'user', 'content': 'Income: $4,280.00'}], 'max_tokens': 20}))
            return r.status_code, r.get_json()
        finally:
            urllib.request.urlopen = real

    # the route reads the provider from settings; make sure it is local for this test
    with srv.db_session() as s:
        row = srv._get_setting(s, 'ai_provider')
        prior = row.value if row else None
        if row: row.value = 'local'
        else: s.add(srv.AppSetting(key='ai_provider', value='local'))
        s.commit()
    try:
        st, cut = ask('length')
        check('/api/ai/chat (local) reports stop_reason max_tokens when Ollama says done_reason length',
              st == 200 and cut.get('stop_reason') == 'max_tokens' and cut.get('provider') == 'local')
        st, fin = ask('stop')
        check('/api/ai/chat (local) reports stop_reason end_turn when Ollama says done_reason stop',
              st == 200 and fin.get('stop_reason') == 'end_turn')
        st, unk = ask(None)
        check('a missing done_reason is reported as unknown - never as finished, never as cut',
              st == 200 and unk.get('stop_reason') == 'unknown')
        check('the carry changed nothing else in the response shape (content, model, provider intact)',
              cut.get('content') == [{'type': 'text', 'text': 'Income was $4,280.00 this month'}]
              and cut.get('model') == 'phi3.5:latest')
    finally:
        with srv.db_session() as s:
            row = srv._get_setting(s, 'ai_provider')
            if prior is None:
                if row: s.delete(row)
            elif row:
                row.value = prior
            s.commit()

    # ── 2. the gate itself, executed from the shipped source ────────────────
    node = shutil.which('node')
    check('node is available to execute the shipped gate (skip the next four if not)', bool(node))
    if node:
        def fn(name):
            i = app_src.find(f'function {name}(')
            j = app_src.find('\n}', i)
            return app_src[i:j + 2]
        i = app_src.find('const _VOICE_RULES_FALLBACK = {')
        j = app_src.find('\n};', i)
        prog = (
            'const _VOICE_RULES = null;\n' + app_src[i:j + 3] + '\n'
            + 'const _FIN_NUM_RE = ' + re.search(r'const _FIN_NUM_RE = (.+);', app_src).group(1) + ';\n'
            + fn('_financialNumbers') + '\n' + fn('_voiceGateCheck') + '\n'
            + 'const clean = "Income was $4,280.00 this month.";\n'
            + 'const findings = "Income: $4,280.00";\n'
            + 'const out = {\n'
            + '  cut:     _voiceGateCheck(clean, findings, true),\n'
            + '  whole:   _voiceGateCheck(clean, findings, false),\n'
            + '  omitted: _voiceGateCheck(clean, findings),\n'
            + '};\n'
            + 'process.stdout.write(JSON.stringify(out));\n'
        )
        try:
            res = subprocess.run([node, '-e', prog], capture_output=True, text=True, timeout=30)
            out = json.loads(res.stdout)
        except Exception as e:  # noqa: BLE001
            out = None
            print(f'        node run failed: {type(e).__name__}: {e} {getattr(res, "stderr", "")[:300]}')
        r10 = lambda k: ((out or {}).get(k, {}).get('results', {}) or {}).get('R10_answer_complete') or {}
        check('the shipped gate, run in Node, FAILS a clean answer flagged as cut (R10 is the only failed rule)',
              bool(out) and out['cut'].get('pass') is False and out['cut'].get('failedRules') == ['R10_answer_complete'])
        check('the same answer not flagged as cut passes every rule including R10',
              bool(out) and out['whole'].get('pass') is True and r10('whole').get('ok') is True)
        check('R10 defaults to passing when the flag is omitted (a caller that cannot know says nothing)',
              bool(out) and out['omitted'].get('pass') is True and r10('omitted').get('ok') is True)
        check('R10 names what happened so the corrective retry can cite it',
              'cut off' in (r10('cut').get('note') or ''))

    # ── 3. the wiring in callAI ──────────────────────────────────────────────
    k = app_src.find('async function callAI(')
    body = app_src[k:app_src.find('\n}', k)]
    check('attempt() derives truncated from stop_reason === max_tokens and nothing else',
          "const truncated = data.stop_reason === 'max_tokens';" in body
          and body.count('truncated') >= 4)
    check('both gate call sites in callAI pass the flag (first attempt and every retry)',
          body.count('_voiceGateCheck(result.text, findings, result.truncated)') == 2
          and '_voiceGateCheck(result.text, findings)' not in body)
    check('skipGate callers receive the flag too (JSON surfaces can act on it later)',
          'truncated:result.truncated' in body)
    # Retired with the cloud path (CLOUD_AI_REMOVAL.md): there is no second provider
    # passing a stop reason through unmapped - the local mapping above is the only source.
    check('the local mapping is the only source of stop_reason - no cloud path remains to pass one through',
          "result['provider'] = 'cloud'" not in server_src and '_ai_chat_cloud' not in server_src)
