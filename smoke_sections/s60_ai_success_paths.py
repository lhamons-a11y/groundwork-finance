"""The AI paths that work, tested against an Ollama that answers.

s55 checks these three routes with the network blocked, which is honest as far
as it goes: it proves the failures are reported rather than hung. It says
nothing about the case where everything is fine, and that half was untestable
for the usual reason - the success path needed a 1.3GB installer and a model
download, so nobody ever ran it and the parsing underneath it was never
exercised by anything but hand-testing.

None of that needs the internet. What it needs is something at the other end
speaking Ollama's protocol, and the app already knows how to be pointed
somewhere else: _local_endpoint() reads the local_endpoint setting, which is
how a user puts Ollama on another machine. So this stands up an Ollama on
127.0.0.1 that answers /api/tags, /api/chat and /api/pull, points the setting
at it, and runs the real client code against it.

The fake also RECORDS what it was sent, which is the only way to check the
half of this that lives in the request rather than the response - the qwen3
reasoning switch is a field in an outgoing payload, and no response can tell
you whether it was set.

Still not covered, and it cannot be from here: _run_install_ollama's last step
shells out to the downloaded installer with /VERYSILENT. Everything before it -
the download, the progress accounting, the file on disk - is exercised.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# What the fake is currently pretending to be. Rewritten between checks.
STATE = {
    'tags': ['mistral:7b', 'llama3:8b', 'qwen2.5:7b-instruct'],
    'chat_reply': 'A plain answer.',
    'pull_lines': [],
    'seen_chat': None,          # the last /api/chat payload, as sent
    'payload': b'',             # what /download/payload.bin serves
}


class _FakeOllama(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *_args):
        pass                    # the suite's output is not a web server log

    def _send(self, body, status=200, ctype='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/tags':
            models = [{'name': n} for n in STATE['tags']]
            self._send(json.dumps({'models': models}).encode('utf-8'))
        elif self.path == '/download/payload.bin':
            self._send(STATE['payload'], ctype='application/octet-stream')
        else:
            self._send(b'{}', status=404)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        try:
            sent = json.loads(raw.decode('utf-8'))
        except ValueError:
            sent = {}

        if self.path == '/api/chat':
            STATE['seen_chat'] = sent
            self._send(json.dumps(
                {'message': {'content': STATE['chat_reply']}}).encode('utf-8'))
        elif self.path == '/api/pull':
            # Ollama streams newline-delimited JSON while it works. This is the
            # shape _run_model_pull parses, one event per line.
            body = b''.join(json.dumps(line).encode('utf-8') + b'\n'
                            for line in STATE['pull_lines'])
            self._send(body, ctype='application/x-ndjson')
        else:
            self._send(b'{}', status=404)


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from server import _download_with_progress, _install_state, _local_endpoint

    server = HTTPServer(('127.0.0.1', 0), _FakeOllama)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{port}'

    def data_of(resp):
        body = resp.get_json() or {}
        return body.get('data') or body

    def settings(**kw):
        return c.patch('/api/settings', headers=HJ, json=kw)

    try:
        settings(local_endpoint=base, ai_provider='local', ai_enabled='true',
                 local_model='')
        check('the endpoint is a setting, so the app can be pointed at another '
              'machine - or at this one', _local_endpoint() == base)

        # ── Which model gets picked ─────────────────────────────────────────
        # The preference order is what makes "the model we shipped got pulled
        # from the registry" a non-event, so it is worth pinning: qwen first,
        # then llama, and never simply whatever came back first.
        _status = data_of(c.get('/api/ai/status', headers=H))
        check('an installed model is auto-detected from the tags Ollama reports',
              _status.get('active_model') == 'qwen2.5:7b-instruct'
              and _status.get('reachable') is True)
        STATE['tags'] = ['mistral:7b', 'llama3:8b']
        check('and with no qwen installed it falls to the next preference, not '
              'to the first tag returned',
              data_of(c.get('/api/ai/status', headers=H)).get('active_model')
              == 'llama3:8b')
        STATE['tags'] = []
        # Reachable AND empty, both asserted: "no model" and "no such field"
        # are the same falsy value, and the first version of this check could
        # not tell them apart - it passed while the two above it failed on a
        # key that does not exist.
        _empty = data_of(c.get('/api/ai/status', headers=H))
        check('an Ollama with no models at all resolves to nothing, and says so '
              'rather than guessing',
              _empty.get('reachable') is True
              and _empty.get('installed_models') == []
              and _empty.get('active_model') == '')
        STATE['tags'] = ['phi3.5:latest']

        # ── A chat that works ───────────────────────────────────────────────
        STATE['chat_reply'] = 'Your debt-free date moves two months earlier.'
        _chat = c.post('/api/ai/chat', headers=HJ, json={
            'system': 'You are terse.',
            'messages': [{'role': 'user', 'content': 'What changed?'}],
            'max_tokens': 200})
        _body = _chat.get_json() or {}
        check('a chat against a reachable model returns the text it produced, '
              'in the shape the client expects',
              _chat.status_code == 200
              and _body.get('content', [{}])[0].get('text') == STATE['chat_reply']
              and _body.get('model') == 'phi3.5:latest')
        check('and the system prompt is sent as a leading message, which is how '
              'Ollama takes one',
              (STATE['seen_chat'] or {}).get('messages', [{}])[0]
              == {'role': 'system', 'content': 'You are terse.'})
        check('the model is asked for a whole answer, not a stream the caller '
              'would have to reassemble',
              (STATE['seen_chat'] or {}).get('stream') is False)

        # A small model that reasons out loud puts the reasoning in the reply.
        # Shipping that to the user would read as the app talking to itself.
        STATE['chat_reply'] = ('<think>The user asked about the date. I should '
                               'check the balance.</think>Two months earlier.')
        _thought = c.post('/api/ai/chat', headers=HJ, json={
            'messages': [{'role': 'user', 'content': 'What changed?'}]})
        check('a model that thinks out loud has its thinking stripped before '
              'the answer is shown',
              (_thought.get_json() or {}).get('content', [{}])[0].get('text')
              == 'Two months earlier.')

        # ── The qwen3 switch, which only the request can prove ──────────────
        # qwen3 reasons by default in Ollama, which on CPU either times out or
        # spends the whole token budget before writing an answer - and comes
        # back with empty content, which looks exactly like a broken model.
        # Both halves of the workaround are in what gets SENT.
        settings(local_model='qwen3:8b')
        STATE['chat_reply'] = 'Fine.'
        c.post('/api/ai/chat', headers=HJ,
               json={'messages': [{'role': 'user', 'content': 'Status?'}]})
        _sent = STATE['seen_chat'] or {}
        check('a qwen3 model is asked not to reason, through the documented '
              'switch', _sent.get('think') is False)
        check('and the prompt carries the no-think token as well, because the '
              'switch alone did not hold',
              (_sent.get('messages') or [{}])[-1].get('content', '')
              .endswith('/no_think'))
        settings(local_model='')

        # ── A pull that finishes ────────────────────────────────────────────
        STATE['pull_lines'] = [
            {'status': 'pulling manifest'},
            {'status': 'downloading', 'total': 1000, 'completed': 250},
            {'status': 'downloading', 'total': 1000, 'completed': 900},
            {'status': 'verifying sha256 digest'},
            {'status': 'success'},
        ]
        _started = c.post('/api/ai/pull-model', headers=HJ,
                          json={'model': 'phi3.5'})
        check('a pull starts in the background and names what it is pulling',
              _started.status_code == 200
              and data_of(_started).get('model') == 'phi3.5')
        _pull = {}
        for _ in range(60):                            # ~6s ceiling
            _pull = data_of(c.get('/api/ai/pull-status', headers=H))
            if _pull.get('done'):
                break
            time.sleep(0.1)
        check('and it finishes, reporting complete rather than stopping at the '
              'last percentage it saw',
              _pull.get('done') is True and _pull.get('percent') == 100
              and not _pull.get('error') and _pull.get('active') is False)

        # An error arrives mid-stream, in a line that otherwise looks like
        # progress. Losing it would leave a pull that reports success.
        STATE['pull_lines'] = [
            {'status': 'downloading', 'total': 1000, 'completed': 100},
            {'status': 'error', 'error': 'no space left on device'},
        ]
        c.post('/api/ai/pull-model', headers=HJ, json={'model': 'phi3.5'})
        _failed = {}
        for _ in range(60):
            _failed = data_of(c.get('/api/ai/pull-status', headers=H))
            if _failed.get('done'):
                break
            time.sleep(0.1)
        check('an error inside the stream is kept, not overwritten by the '
              'lines after it',
              'no space left' in (_failed.get('error') or '')
              and _failed.get('percent') != 100)

        # ── The download, which is every step of the install but the last ───
        STATE['payload'] = b'GW-FAKE-INSTALLER' * 4096      # ~68KB, many chunks
        _dest = ctx.TMP / 's60_downloaded.bin'
        _install_state['percent'] = 0
        _download_with_progress(f'{base}/download/payload.bin', _dest,
                                'Downloading Ollama…')
        check('the installer download writes the bytes it was served, all of them',
              _dest.exists() and _dest.read_bytes() == STATE['payload'])
        check('and it reports progress as it goes, ending at complete',
              _install_state['percent'] == 100
              and _install_state['stage'] == 'Downloading Ollama…')

        # ── The toggle still outranks all of it ─────────────────────────────
        # A reachable model must not make the off switch advisory.
        settings(ai_enabled='false')
        _off = data_of(c.post('/api/ai/chat', headers=HJ, json={
            'messages': [{'role': 'user', 'content': 'Anything?'}]}))
        check('with AI turned off, a working model is still not called',
              _off.get('ai_available') is False and _off.get('reason') == 'disabled')
    finally:
        server.shutdown()
        server.server_close()
        # The endpoint and the toggle are settings; leaving them pointed at a
        # port that no longer exists would break every check written after this.
        settings(local_endpoint='', local_model='', ai_enabled='true')
