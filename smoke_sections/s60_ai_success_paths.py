"""The AI paths that work, tested against the in-app engine with a stand-in model.

The engine (core/engine.py, ENGINE_REPLACEMENT.md) owns the model; the server reaches it through one seam,
_ai_chat_local. This section puts a stand-in where the loaded model would be - an object with the same
create_chat_completion() the real llama_cpp.Llama has, which RECORDS what it was sent - and runs the real routes
against it. So it checks both halves: what the user's request becomes on the way in (system first, content blocks
flattened, the budget and temperature passed through), and what the response becomes on the way out.

It never loads the real 2.2 GB model: that is measured outside the gate (the voice A/B and the memory figures in
ENGINE_REPLACEMENT.md), and the gate has to stay fast and runnable on any machine.
"""
import json
import threading
import time


class _StandIn:
    """Answers like llama_cpp.Llama.create_chat_completion; records calls and how many ran at once."""

    def __init__(self, reply='A plain answer.', delay=0.0, raise_exc=None):
        self.reply, self.delay, self.raise_exc = reply, delay, raise_exc
        self.seen = []
        self.active = 0
        self.max_active = 0
        self.closed = False
        self._mx = threading.Lock()

    def create_chat_completion(self, messages, max_tokens, temperature, **_kw):
        with self._mx:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            self.seen.append({'messages': messages, 'max_tokens': max_tokens, 'temperature': temperature})
            if self.raise_exc:
                raise self.raise_exc
            time.sleep(self.delay)
            return {'choices': [{'message': {'content': '  ' + self.reply + '  '}, 'finish_reason': 'stop'}],
                    'usage': {'completion_tokens': 3}}
        finally:
            with self._mx:
                self.active -= 1

    def close(self):
        self.closed = True


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import server
    from core import engine

    def data_of(resp):
        body = resp.get_json() or {}
        return body.get('data') or body

    def install(model):
        engine.stop()
        with engine._lock:
            engine._model = model
            engine._set('ready')

    def chat(**body):
        return c.post('/api/ai/chat', headers=HJ, data=json.dumps(body))

    try:
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'true'})
        m = _StandIn()
        install(m)

        r = chat(system='Be plain.', messages=[{'role': 'user', 'content': [{'type': 'text', 'text': 'Hi'},
                                                                          {'type': 'text', 'text': 'there'}]}],
                 max_tokens=77, temperature=0.1)
        body = r.get_json() or {}
        check('a chat reaches the engine and comes back in the shape callAI() reads',
              r.status_code == 200 and body.get('content') == [{'type': 'text', 'text': 'A plain answer.'}]
              and body.get('provider') == 'local' and body.get('model') == engine.MODEL_FILE
              and body.get('finish') == 'stop' and body.get('stop_reason') == 'end_turn')
        sent = m.seen[-1]
        check('the system prompt goes first and content blocks are flattened to text',
              sent['messages'] == [{'role': 'system', 'content': 'Be plain.'}, {'role': 'user', 'content': 'Hi\nthere'}])
        check('the token budget and temperature pass through unchanged',
              sent['max_tokens'] == 77 and sent['temperature'] == 0.1)

        with c.application.test_request_context('/api/debt/pdf-extract', method='POST'):
            text = server._ai_complete_text('sys', 'user text', max_tokens=50)
        check('the server-side path (_ai_complete_text) gets the text too', text == 'A plain answer.')

        # ── Not running, said honestly ───────────────────────────────────────
        calls_before = len(m.seen)
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'false'})
        r = data_of(chat(messages=[{'role': 'user', 'content': 'x'}]))
        check('with AI off the route says so, and the engine is never asked',
              r.get('ai_available') is False and r.get('reason') == 'disabled' and len(m.seen) == calls_before)
        check('switching AI off released the model (it was closed, and nothing is loaded)',
              m.closed and not engine.is_loaded() and engine.status()['state'] == 'off')
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'true'})
        check('switching AI back on in the gate loads nothing: only the launcher may load the real model',
              engine.status()['state'] == 'off' and not engine.is_loaded())
        r = data_of(chat(messages=[{'role': 'user', 'content': 'x'}]))
        check('AI on but the engine not running: an honest message, never a 500 or an empty answer',
              r.get('ai_available') is False and r.get('reason') == 'engine_off' and 'Settings' in r.get('message', ''))

        with engine._lock:
            engine._set('unavailable', 'cpu', 'no AVX2')
        r = data_of(chat(messages=[{'role': 'user', 'content': 'x'}]))
        st = data_of(c.get('/api/ai/status', headers=H))
        check("an unavailable engine says why, in the user's words, on the chat and on the status",
              r.get('reason') == 'engine_cpu' and 'processor' in r.get('message', '')
              and st.get('engine') == 'unavailable' and 'processor' in st.get('message', ''))

        install(_StandIn(raise_exc=ValueError('Requested tokens (5000) exceed context window of 4096')))
        r = data_of(chat(messages=[{'role': 'user', 'content': 'x' * 10}]))
        check('a request too long for the model is refused plainly, not crashed on',
              r.get('ai_available') is False and r.get('reason') == 'engine_too_long')

        # ── One call at a time ────────────────────────────────────────────────
        slow = _StandIn(delay=0.25)
        install(slow)
        outs = []
        threads = [threading.Thread(target=lambda: outs.append(engine.chat(None, [{'role': 'user', 'content': 'q'}])))
                   for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        check('three calls at once run one at a time, and all three answer',
              slow.max_active == 1 and len(outs) == 3 and all(o['ok'] for o in outs))
        st = data_of(c.get('/api/ai/status', headers=H))
        check('status reports ready while a model is loaded', st.get('engine') == 'ready' and st.get('ready') is True)
    finally:
        engine.stop()
        engine.allow_load(False)
        c.patch('/api/settings', headers=HJ, json={'ai_enabled': 'true'})
