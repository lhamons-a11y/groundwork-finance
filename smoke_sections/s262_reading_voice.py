"""Item 112 P6 and item 113: text size, read aloud and voice commands (PANEL_REVIEW.md; Rob 2026-10-24).

    P6   one type scale; a Text size setting for the whole app; read aloud in Groundwork's own words with local voices,
         then "Would you like this explained further?"
    113  push-to-talk voice commands recognised on this computer - "Sending the data to someone though is kinda of a
         deal breaker for me" - so: nothing that can reach a network in the voice engine, the browser's own
         recognition switched off, the clip posted to this server only, off by default, what was heard said first
         with Undo.
"""
import ast
import io
import json
import shutil
import socket
import subprocess
import wave


def _wav(seconds=1.0, rate=16000, channels=1, value=1000):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(int(value).to_bytes(2, 'little', signed=True) * int(seconds * rate) * channels)
    return buf.getvalue()


class _Seg:
    def __init__(self, text):
        self.text = text


class _FakeModel:
    def __init__(self, text):
        self.text, self.got = text, None

    def transcribe(self, samples, **params):
        self.got, self.params = samples, params          # item 116 V1: the route hands the person's words as the hint
        return [_Seg(self.text)]


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    from core import voice
    from core.database import AppSetting, db_session

    # ── Nothing in the voice engine can reach a network ─────────────────────────────────────────────────────────
    src = (ctx.BASE / 'core' / 'voice.py').read_text(encoding='utf-8')
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split('.')[0])
    net = mods & {'socket', 'http', 'urllib', 'requests', 'ssl', 'ftplib', 'smtplib', 'websocket', 'websockets',
                  'httpx', 'aiohttp'}
    check(f"s262 113 the voice engine imports nothing that can reach a network, and loads its model from a file path "
          f"(imports: {sorted(mods)})",
          not net and 'Model(str(model_path())' in src and 'initial_prompt=HINT' in src
          and __import__('logging').getLogger('pywhispercpp').level >= __import__('logging').WARNING)

    real_connect, tried = socket.socket.connect, []

    def _no_network(self, *a, **k):
        tried.append(a)
        raise OSError('s262: no network')
    socket.socket.connect = _no_network
    try:
        fake = _FakeModel(' Read the page.')
        heard = voice.transcribe(_wav(1.0), model=fake)
        noise = voice.transcribe(_wav(1.0), model=_FakeModel(' [BLANK_AUDIO]'))
        short = voice.transcribe(_wav(0.1), model=_FakeModel('x'))
    finally:
        socket.socket.connect = real_connect
    refused = []
    for bad in (_wav(1.0, rate=44100), _wav(1.0, channels=2), _wav(voice.MAX_SECONDS + 1), b'', b'not a wav'):
        try:
            voice.transcribe(bad, model=_FakeModel('x'))
        except voice.VoiceError:
            refused.append(True)
    check(f"s262 113 a 16 kHz mono clip becomes its words with no network touched; silence markers and a clip too "
          f"short are no words; any other clip is refused ({heard!r}, {noise!r}, {short!r}, {len(refused)}/5 refused)",
          heard == 'Read the page.' and noise == '' and short == '' and not tried and len(refused) == 5
          and abs(float(fake.got[0]) - 1000 / 32768) < 1e-6)

    # ── The routes: off by default, refused when off, and the clip is not kept ───────────────────────────────────
    with db_session() as s:
        for k in ('voice_commands', 'text_size', 'read_aloud', 'read_rate'):
            row = s.query(AppSetting).filter_by(key=k).first()
            if row:
                s.delete(row)
        s.commit()
    st = (c.get('/api/voice', headers=H).get_json() or {}).get('data') or {}
    off = c.post('/api/voice/transcribe', headers={**H, 'Content-Type': 'audio/wav'}, data=_wav(1.0))
    real_status, real_model, real_preload, preloads = voice.status, voice._model, voice.preload, []
    voice.preload = lambda: preloads.append(1)       # switching on readies the model; the real one is not loaded here
    c.patch('/api/settings', headers={**H, 'Content-Type': 'application/json'}, data=json.dumps({'voice_commands': 'on'}))
    try:
        voice.status = lambda: {'available': False, 'reason': 'no model'}
        missing = c.post('/api/voice/transcribe', headers={**H, 'Content-Type': 'audio/wav'}, data=_wav(1.0))
        voice.status = lambda: {'available': True, 'reason': ''}
        voice._model = _FakeModel('explain further')
        got = c.post('/api/voice/transcribe', headers={**H, 'Content-Type': 'audio/wav'}, data=_wav(1.0))
        bad = c.post('/api/voice/transcribe', headers={**H, 'Content-Type': 'audio/wav'}, data=_wav(1.0, rate=8000))
    finally:
        voice.status, voice._model, voice.preload = real_status, real_model, real_preload
    with db_session() as s:
        kept = [r.key for r in s.query(AppSetting).all() if 'explain further' in str(r.value)]
    c.patch('/api/settings', headers={**H, 'Content-Type': 'application/json'}, data=json.dumps({'voice_commands': 'off'}))
    check(f"s262 113 voice is off until chosen and refused while off; unavailable says why; on, the words come back "
          f"and nothing is kept ({st.get('on')}, {off.status_code}, {missing.status_code}, {got.status_code}, "
          f"{bad.status_code})",
          st.get('on') is False and 'available' in st and off.status_code == 409 and missing.status_code == 503
          and got.status_code == 200 and (got.get_json().get('data') or {}).get('text') == 'explain further'
          and bad.status_code == 400 and not kept and voice._model is None and preloads)

    # ── The page ────────────────────────────────────────────────────────────────────────────────────────────────
    acc_path = ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js'
    acc = acc_path.read_text(encoding='utf-8')
    check("s262 113 the page posts the clip to this computer's server only, switches the browser's own recognition "
          "off, and nothing in app.js uses it",
          "_gwFetch('/api/voice/transcribe'" in acc and 'http:' not in acc and 'https:' not in acc
          and "['SpeechRecognition', 'webkitSpeechRecognition']" in acc and 'SpeechRecognition' not in ctx.app_src)
    check("s262 P6 every font size is a step of the type scale on :root, and the Text size setting sets the root size",
          '--fs-base:0.8125rem' in ctx.html_src and not __import__('re').search(r'font-size:\s*\d+px', ctx.app_src)
          and "document.documentElement.style.fontSize" in acc and "'130': 1.3" in acc)
    mac = (ctx.BASE / 'groundwork_macos.spec').read_text(encoding='utf-8')
    check("s262 113 the Mac app says why it asks for the microphone; the builds carry the voice engine and its "
          "measured model",
          'NSMicrophoneUsageDescription' in mac and 'spec_engine.voice_model_data()' in mac
          and 'spec_engine.voice_parts()' in (ctx.BASE / 'groundwork.spec').read_text(encoding='utf-8')
          and 'pywhispercpp==' in (ctx.BASE / 'requirements.txt').read_text(encoding='utf-8'))

    node = shutil.which('node')
    if not node:
        check('s262 node is available for the page test', False)
        return
    prog = r"""
globalThis.window = globalThis;
const made = {}, toasts = [], spoken = [], asked = [], shown = [], patched = [], fetched = [];
const el = (id) => ({ id, style: {}, dataset: {}, children: [], setAttribute() {}, addEventListener() {},
  querySelector() { return { onclick: null }; }, querySelectorAll() { return []; }, remove() { delete made[this.id]; } });
globalThis.document = { readyState: 'complete', documentElement: { style: {} }, body: { appendChild: (e) => { made[e.id] = e; } },
  activeElement: null, getElementById: (id) => made[id] || null, querySelector: () => null, querySelectorAll: () => [],
  addEventListener() {}, createElement: () => el('') };
globalThis.localStorage = { getItem: () => null, setItem() {} };
globalThis.MutationObserver = function () { this.observe = () => {}; };
globalThis.SpeechSynthesisUtterance = function (t) { this.text = t; };
globalThis.speechSynthesis = { cancel() {}, speak(u) { spoken.push(u); },
  getVoices: () => [{ name: 'cloud', lang: 'en-US', localService: false }, { name: 'local', lang: 'en-US', localService: true }] };
globalThis.API = { get: async () => ({}), patch: async (p, b) => { patched.push(b); } };
globalThis.showToast = (t, s, k, undo) => toasts.push([t, s, !!undo, undo]);
globalThis.esc = (s) => String(s);
globalThis.askGroundwork = (q) => asked.push(q);
globalThis.showView = (v) => shown.push(v);
globalThis._gwFetch = async (p) => { fetched.push(p); return { ok: true, json: async () => ({ data: { text: '' } }) }; };
globalThis._explainWhere = () => ({ name: 'debt', tab: 'setup', tabName: 'Setup', view: null });
globalThis._explainFigures = () => [];
globalThis.FIGS = { 'debt.total_owed': { label: 'Total still owed', means: "the sum of every active debt's current balance" } };
globalThis.PAGE_EXPLAIN = { debt: { what: 'Your cards and loans.' } };
globalThis.VIEW_LABELS = { debt: 'Debt Payoff' };
const mods = {};
globalThis.GWTeaching = { register: (n, m) => { mods[n] = m; } };
""" + acc + r"""
(async () => {
  await new Promise(r => setTimeout(r, 10));
  const a = mods.access, out = {};
  out.defaults = Object.assign({}, a.prefs);
  out.recognition = [typeof window.SpeechRecognition, typeof window.webkitSpeechRecognition];
  const fig = { dataset: { fig: 'debt.total_owed' }, offsetParent: {}, innerText: '$12,000.00', matches: () => true };
  const card = { matches: () => false, querySelectorAll: () => [fig], querySelector: () => ({ innerText: 'Your debts' }),
                 closest: () => null };
  a.readSection(card);
  // Groundwork's own voice is asked first (core/speak.py); this stub server has none, so the computer's voice reads
  await new Promise(r => setTimeout(r, 20));
  out.read = spoken[0] && [spoken[0].text, spoken[0].voice.name];
  spoken[0].onend();
  out.question = !!made.gwReadAsk && spoken[spoken.length - 1].text;
  a.route('Yes.');
  out.further = spoken[spoken.length - 1].text;
  out.yesToast = toasts[toasts.length - 1].slice(0, 3);
  out.questionClosed = !made.gwReadAsk;
  a.route('Slower!');
  out.slower = [patched[patched.length - 1], spoken[spoken.length - 1].rate];
  toasts[toasts.length - 1][3]();
  out.undone = patched[patched.length - 1];
  a.route('go back');
  out.nothing = toasts[toasts.length - 1].slice(0, 2);
  a.route('How much do I owe on the Visa?');
  out.asked = asked.slice();
  const buf = a.wav([new Float32Array(48000).fill(0.5)], 48000), d = new DataView(buf);
  out.wav = [buf.byteLength, String.fromCharCode(d.getUint8(0), d.getUint8(1), d.getUint8(2), d.getUint8(3)),
             d.getUint32(24, true), d.getUint16(22, true), d.getInt16(44, true)];
  out.fetched = fetched;
  console.log(JSON.stringify(out));
})().catch(e => { console.log(JSON.stringify({ error: String(e && e.stack || e) })); });
"""
    # A file, not `node -e`: the program carries all of access.js, past Windows' 32,767-character command line
    import os, tempfile
    f = os.path.join(tempfile.mkdtemp(prefix='s262_'), 'read.js')
    open(f, 'w', encoding='utf-8').write(prog)
    r = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=30)
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        o = {'error': (r.stdout + r.stderr)[-400:]}
    check(f"s262 P6/113 everything is off by default at the standard size, and the browser's recognition is gone "
          f"({o.get('defaults')}, {o.get('recognition')}, {o.get('error')})",
          o.get('defaults') == {'text_size': '100', 'read_aloud': 'off', 'read_rate': 'normal', 'voice_commands': 'off', 'voice_tour': '', 'voice_wake': 'off'}
          and o.get('recognition') == ['undefined', 'undefined'])
    check(f"s262 P6 a section is read in Groundwork's words with a voice on this computer, then 'Would you like this "
          f"explained further?'; yes reads what the figure means ({o.get('read')}; {o.get('question')}; "
          f"{o.get('further')})",
          o.get('read') == ['Your debts. Total still owed: $12,000.00.', 'local']
          and o.get('question') == 'Would you like this explained further?'
          and o.get('further') == "Total still owed is the sum of every active debt's current balance."
          and o.get('questionClosed') is True)
    check(f"s262 113 what was heard is said before it acts, with Undo; slower is saved and undone; a command with "
          f"nothing to act on says so; anything else goes to Ask ({o.get('yesToast')}; {o.get('slower')}; "
          f"{o.get('undone')}; {o.get('nothing')}; {o.get('asked')})",
          o.get('yesToast') == ['Heard: “Yes.”', 'Explaining further', True]
          and o.get('slower') == [{'read_rate': 'slower'}, 0.8] and o.get('undone') == {'read_rate': 'normal'}
          and o.get('nothing') == ['Heard: “go back”', 'There is nothing to do that with right now.']
          and o.get('asked') == ['How much do I owe on the Visa?'])
    check(f"s262 113 the clip is a 16 kHz mono 16-bit WAV, and the page fetched nothing on its own - only Groundwork's "
          f"voice, from this computer's server, once, before the computer's voice took over ({o.get('wav')}, "
          f"{o.get('fetched')})",
          o.get('wav') == [44 + 32000, 'RIFF', 16000, 1, 16383] and o.get('fetched') == ['/api/voice/speak'])
