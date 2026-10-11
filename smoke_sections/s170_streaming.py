"""Narration that appears as it is written, checked before it shows (gw 2.0/NARRATION_STREAMING.md, item 10; Rob
2026-10-09: "approve S1–S9 as recommended", "build item 10").

    S1  (a) a sentence reaches the screen only after the voice check passes it; the whole answer is checked again at
        the end (R10); a fabricating stream never shows its bad sentence
    S2  a failure withdraws what was shown and the answer is reworded out of sight
    S3  the engine streams, holding its lock, and reports its own finish reason
    S4  the route streams on the local server; AI off is unchanged
    S5  the monthly report and the report narratives stream
    S6  Stop ends the generation; a stopped answer is never treated as finished
"""
import json
import shutil
import subprocess


def _sse(resp):
    out = []
    for block in resp.get_data(as_text=True).split('\n\n'):
        block = block.strip()
        if block.startswith('data: '):
            out.append(json.loads(block[6:]))
    return out


def run(ctx):
    check, c, HJ, app = ctx.check, ctx.c, ctx.HJ, ctx.app_src
    from core import engine

    class _Streamer:
        def __init__(self, pieces, finish, cancel_after=None):
            self.pieces, self.finish, self.cancel_after = pieces, finish, cancel_after

        def create_chat_completion(self, messages, max_tokens, temperature, stream=False, **_kw):
            assert stream, 'the streaming route must ask the engine to stream'

            def gen():
                for i, p in enumerate(self.pieces):
                    if self.cancel_after is not None and i == self.cancel_after:
                        engine.cancel()
                    last = i == len(self.pieces) - 1
                    yield {'choices': [{'delta': {'content': p}, 'finish_reason': self.finish if last else None}]}
            return gen()

        def close(self):
            pass

    def ask(model, body_extra=None):
        engine.stop()
        with engine._lock:
            engine._model = model
            engine._set('ready')
        body = {'messages': [{'role': 'user', 'content': 'Income: $4,280.00'}], 'max_tokens': 50, 'stream': True}
        body.update(body_extra or {})
        return c.post('/api/ai/chat', headers=HJ, data=json.dumps(body))

    c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'true'})
    try:
        r = ask(_Streamer(['Income was ', '$4,280.00', ' this month.'], 'stop'))
        ev = _sse(r)
        check('s170 S3/S4 the route streams the model\'s pieces as events, then its finish reason',
              r.mimetype == 'text/event-stream' and [e['t'] for e in ev if 't' in e] == ['Income was ', '$4,280.00', ' this month.']
              # item 62: the end event also names its AI log entry
              and {k: v for k, v in ev[-1].items() if k != 'log_id'} == {'done': True, 'stop_reason': 'end_turn'}
              and 'log_id' in ev[-1])
        ev = _sse(ask(_Streamer(['Income was ', '$4,280'], 'length')))
        check('s170 S3 a stream cut at the length cap ends as max_tokens - never as finished (R10 reads it)',
              ev[-1].get('stop_reason') == 'max_tokens')
        ev = _sse(ask(_Streamer(['One. ', 'Two. ', 'Three. ', 'Four.'], 'stop', cancel_after=2)))
        check('s170 S6 Stop ends the generation: the stream says stopped, and the rest is never sent',
              ev[-1] == {'stopped': True} and ''.join(e.get('t', '') for e in ev) == 'One. Two. ')
        check('s170 S3 the engine\'s lock is free again after a stopped stream', engine._lock.acquire(timeout=2) and (engine._lock.release() or True))
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'false'})
        off = ask(_Streamer(['x'], 'stop'))
        check('s170 S4 AI off is unchanged: a JSON "AI is off" answer, no stream',
              off.mimetype == 'application/json' and (off.get_json().get('data') or {}).get('ai_available') is False)
    finally:
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'true'})
        engine.stop()

    # ── the page: callAI's streamed attempt, run from the shipped source ──
    node = shutil.which('node')
    check('s170 node is available', bool(node))
    if not node:
        return
    a = app.index('let _GW_VOICE = null;')
    b = app.index('// ─── Phase 8C')
    src = app[a:b]
    harness = r'''
const API = { _calls: [], post: async (url, body) => { API._calls.push(url);
    if (url === '/api/ai/chat') return { data: { content: [{ type: 'text', text: 'Income was $4,280.00 this month.' }], stop_reason: 'end_turn', provider: 'local' } };
    return {}; }, get: async () => ({}) };
const _gwErr = () => () => {};
const _GW_AUTH_HEADER = () => ({});
const esc = s => String(s);
let STREAM = [];
globalThis.fetch = async (url, opts) => {
  if (url === 'voice_rules.json') return new Response('', { status: 404 });
  const enc = new TextEncoder();
  const body = new ReadableStream({ start(ctrl) { for (const e of STREAM) ctrl.enqueue(enc.encode('data: ' + JSON.stringify(e) + '\n\n')); ctrl.close(); } });
  return new Response(body, { headers: { 'content-type': 'text/event-stream' } });
};
''' + src + r'''
async function run(events) {
  STREAM = events; API._calls = [];
  const shown = [], resets = [];
  const r = await callAI({ surface: 's170', findings_kinds: ['income', 'total'], max_tokens: 50,
    messages: [{ role: 'user', content: 'Income: $4,280.00. Spent: $3,100.00.' }],
    onSentence: s => shown.push(s), onReset: w => resets.push(w) });
  return { ok: r.ok, streamed: !!r.streamed, stopped: !!r.stopped, text: r.text, shown, resets, retried: API._calls.filter(u => u === '/api/ai/chat').length };
}
(async () => {
  const out = {};
  out.clean = await run([{ t: 'Income was $4,280.00 this month. ' }, { t: 'Spending was $3,100.00.' }, { done: true, stop_reason: 'end_turn' }]);
  out.fabricated = await run([{ t: 'Income was $4,280.00 this month. ' }, { t: 'You saved $9,999.00 extra. ' }, { t: 'More.' }, { done: true, stop_reason: 'end_turn' }]);
  out.cut = await run([{ t: 'Income was $4,280.00 this month. ' }, { t: 'Spending was' }, { done: true, stop_reason: 'max_tokens' }]);
  out.stopped = await run([{ t: 'Income was $4,280.00 this month. ' }, { t: 'Spending' }, { stopped: true }]);
  console.log(JSON.stringify(out));
})();
'''
    # the harness goes in a file: on Windows a command line stops at about 32,000 characters, and the page code it
    # carries has grown past that (item 62)
    import tempfile, os
    fd, hpath = tempfile.mkstemp(suffix='.js')
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        fh.write(harness)
    try:
        p = subprocess.run([node, hpath], capture_output=True, text=True, encoding='utf-8', timeout=120)
    finally:
        os.remove(hpath)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:                                          # noqa: BLE001
        out = {}
        print('        node said:', (p.stderr or p.stdout)[-600:])
    cl, fb, cut, st = out.get('clean', {}), out.get('fabricated', {}), out.get('cut', {}), out.get('stopped', {})
    check('s170 S1 a clean stream shows each sentence as it passes, and is the answer (no second call)',
          cl.get('ok') and cl.get('streamed') and cl.get('shown') == ['Income was $4,280.00 this month.', 'Spending was $3,100.00.']
          and cl.get('retried') == 0)
    check('s170 S1 a fabricating stream never shows its bad sentence ($9,999.00 is in no finding)',
          fb.get('shown') == ['Income was $4,280.00 this month.'] and not any('9,999' in s for s in fb.get('shown', [])))
    check('s170 S2 the failure withdraws what was shown and rewords out of sight (the retry is a normal, checked call)',
          fb.get('resets') == ['Rewording…'] and fb.get('retried') == 1 and fb.get('ok') is True
          and fb.get('text') == 'Income was $4,280.00 this month.' and not fb.get('streamed'))
    check('s170 S1 a stream cut at the length cap is never a finished answer: R10 at the end withdraws it',
          cut.get('resets') == ['Rewording…'] and cut.get('streamed') is False and 'Spending was' not in ' '.join(cut.get('shown', [])))
    check('s170 S6 a stopped answer keeps what was shown, marked stopped, and is never ok',
          st.get('stopped') is True and st.get('ok') is False and st.get('text') == 'Income was $4,280.00 this month.')

    # S5: the two surfaces use it, with Stop and the stopped panel
    check('s170 S5 the report narratives and the monthly report stream through callAI with Stop',
          app.count('onSentence: live.add, onReset: live.reset, signal: live.signal,') == 2
          and "_gwLiveNarration(target, reportId)" in app and "_gwLiveNarration(cont, 'monthly')" in app)
    check('s170 S6 a stopped report is never cached or saved as the month\'s report',
          "if (result.stopped) {        // S6: shown text stays, marked stopped; not saved as the month's report" in app
          and 'Stopped before it finished' in app)
