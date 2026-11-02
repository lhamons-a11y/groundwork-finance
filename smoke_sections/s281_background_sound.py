"""The microphone disregards background sound (Rob 2026-11-01: "microphone needs to disregard the background sounds").
Run on the page's own code in Node, with a stand-in microphone at the browser's real frame size (4096 at 48 kHz):

    B1  a steady sound - a fan, a TV left on - is learnt as the room's level within a few seconds, and from then on
        sends nothing, however long it goes on
    B2  someone talking over it is still heard, and sent
    B3  a door, a clap, a dropped dish - loud for a moment, not for as long as a word - is let go
    B4  what whisper makes of background sound is not taken for words: its marks ("[Music]", "(coughs)", "*sighs*",
        "♪") among words are dropped, and its stock lines on noise alone ("Thank you.") come back empty
"""
import json
import os
import shutil
import subprocess
import tempfile

from smoke_sections.s262_reading_voice import _FakeModel, _wav


def run(ctx):
    check = ctx.check
    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    node = shutil.which('node')
    if not node:
        check('s281 node is available for the page test', False)
        return
    prog = r"""
globalThis.window = globalThis;
const made = {}, sent = [];
let now = 1000;
Date.now = () => now;
const el = (id) => ({ id, style: {}, dataset: {}, classList: { add() {}, remove() {}, toggle() {} }, setAttribute() {},
  addEventListener(k, f) { this['on' + k] = f; }, appendChild(e) { made[e.id] = e; }, remove() { delete made[this.id]; },
  querySelector() { return { onclick: null }; }, querySelectorAll() { return []; } });
made.gwAskWrap = el('gwAskWrap'); made.gwAskBox = el('gwAskBox'); made.gwAskBox.offsetParent = {};
globalThis.document = { readyState: 'complete', documentElement: { style: {} }, body: { appendChild: (e) => { made[e.id] = e; } },
  activeElement: null, hidden: false, getElementById: (id) => made[id] || null, querySelector: () => null, querySelectorAll: () => [],
  addEventListener() {}, createElement: () => el('') };
globalThis.localStorage = { getItem: () => null, setItem() {} };
globalThis.MutationObserver = function () { this.observe = () => {}; };
globalThis.SpeechSynthesisUtterance = function (t) { this.text = t; };
globalThis.speechSynthesis = { speaking: false, pending: false, cancel() {}, speak() {},
  getVoices: () => [{ name: 'local', lang: 'en-US', localService: true }] };
globalThis.API = { get: async (p) => p === '/api/settings' ? { voice_commands: 'on', voice_tour: 'done' } : {}, patch: async () => {},
  post: async () => ({}) };
globalThis.showToast = () => {};
globalThis.esc = (s) => String(s);
globalThis.askGroundwork = () => {};
globalThis._gwFetch = async (p) => { sent.push(now); return { ok: true, json: async () => ({ data: { text: '' } }) }; };
let node = null;
Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: { getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }) } } });
globalThis.AudioContext = function () { this.sampleRate = 48000;
  this.createMediaStreamSource = () => ({ connect() {} }); this.createScriptProcessor = () => (node = { connect() {}, disconnect() {} });
  this.destination = {}; this.close = () => {}; };
const mods = {};
globalThis.GWTeaching = { register: (n, m) => { mods[n] = m; } };
""" + acc + r"""
const FRAME = 4096 / 48000 * 1000;
// a frame at this loudness (its RMS), a tone so nothing depends on it being a flat line
const frame = (rms) => ({ inputBuffer: { getChannelData: () => new Float32Array(4096).map((_, i) => rms * Math.SQRT2 * Math.sin(i / 7)) } });
// `level(t)` gives the loudness at each moment
const play = async (ms, level) => { for (let t = 0; t < ms; t += FRAME) { now += FRAME; node.onaudioprocess(frame(level(t))); } await new Promise(r => setTimeout(r, 5)); };
const fan = 0.05;                                            // a fan: four times what alone would count as talking
// talking: syllables about five a second, louder than the fan, with the fan between them
const talk = (t) => (Math.floor(t / 100) % 2 ? fan : 0.4);
(async () => {
  await new Promise(r => setTimeout(r, 10));
  const a = mods.access, out = {};
  made.gwMicBtn.onclick({ preventDefault() {} });
  await new Promise(r => setTimeout(r, 5));
  await play(4000, () => fan);                               // the room is learnt
  const learnt = sent.length;
  await play(30000, () => fan);                              // and half a minute more of it
  out.fanAfter = sent.length - learnt;
  out.learnt = learnt;
  await play(1800, talk); await play(1500, () => fan);       // someone talks over it
  out.talkOver = sent.length - learnt;
  await play(80, () => 0.6); await play(1500, () => fan);    // a door
  await play(80, () => 0.6); await play(80, () => fan); await play(80, () => 0.6); await play(1500, () => fan);  // a double knock
  out.knocks = sent.length - learnt - out.talkOver;
  out.on = a.listening();
  console.log(JSON.stringify(out));
})().catch(e => console.log(JSON.stringify({ error: String(e && e.stack || e) })));
"""
    f = os.path.join(tempfile.mkdtemp(prefix='s281_'), 'bg.js')
    open(f, 'w', encoding='utf-8').write(prog)
    r = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        o = {'error': (r.stdout + r.stderr)[-600:]}
    check(f"s281 B1 a steady background sound is learnt as the room's level and then sends nothing "
          f"(sent while learning {o.get('learnt')}, after {o.get('fanAfter')}; {o.get('error')})",
          o.get('learnt', 9) <= 1 and o.get('fanAfter') == 0 and o.get('on') is True)
    check(f"s281 B2 someone talking over the background sound is still heard ({o.get('talkOver')})", o.get('talkOver') == 1)
    check(f"s281 B3 a door or a double knock (a frame each), loud only for a moment, is let go ({o.get('knocks')})", o.get('knocks') == 0)

    from core import voice
    got = {t: voice.transcribe(_wav(1.0), model=_FakeModel(t)) for t in
           (' [Music] Open my budget.', ' (coughs) Show my bills ♪', ' *sighs*', ' Thank you.', ' you', ' Thank you for that.')}
    check(f"s281 B4 whisper's marks for background sound are dropped and its stock lines on noise come back empty ({ascii(got)})",
          got == {' [Music] Open my budget.': 'Open my budget.', ' (coughs) Show my bills ♪': 'Show my bills',
                  ' *sighs*': '', ' Thank you.': '', ' you': '', ' Thank you for that.': 'Thank you for that.'})
    check('s281 the room\'s level is the quietest tenth of the last few seconds, and talking must clear it',
          'var ABOVE_FLOOR = 2.5;' in acc and 'return s[Math.floor(s.length * 0.1)];' in acc
          and 'c.loudMs >= MIN_SAID_MS' in acc)
