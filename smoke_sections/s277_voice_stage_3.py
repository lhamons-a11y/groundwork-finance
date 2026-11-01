"""Item 116 stage 3 (gw 2.0/VOICE_ASSISTANT.md V3, approved 2026-10-31): hands-free start. Run on the page's own code
in Node, with a stand-in microphone and window:

    V3  off by default; on, the microphone opens by itself while Groundwork's window is in front - the red microphone
        showing - and acts only on what begins with "Groundwork", and on a follow-up within a few seconds of one;
        everything else is let go with no toast; leaving the window turns it off without a word, coming back turns it
        on again; a tap while it waits for its name means "talk now"
"""
import json
import os
import shutil
import subprocess
import tempfile


def run(ctx):
    check = ctx.check
    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    check('s277 V3 off by default, and only offered with voice commands on',
          "voice_wake: 'off' }" in acc and "prefs.voice_commands === 'on' && prefs.voice_wake === 'on'" in acc
          and "(prefs.voice_commands === 'on'" in acc and 'Start by saying "Groundwork"' in acc)
    node = shutil.which('node')
    if not node:
        return
    prog = r"""
globalThis.window = globalThis;
const made = {}, toasts = [], asked = [], sent = [], winOn = {}, docOn = {};
let now = 1000, focused = true;
Date.now = () => now;
const el = (id) => ({ id, style: {}, dataset: {}, classList: { add() {}, remove() {}, toggle() {} }, setAttribute() {},
  addEventListener(k, f) { this['on' + k] = f; }, appendChild(e) { made[e.id] = e; }, remove() { delete made[this.id]; },
  querySelector() { return { onclick: null }; }, querySelectorAll() { return []; } });
made.gwAskWrap = el('gwAskWrap'); made.gwAskBox = el('gwAskBox'); made.gwAskBox.offsetParent = {};
globalThis.document = { readyState: 'complete', documentElement: { style: {} }, body: { appendChild: (e) => { made[e.id] = e; } },
  activeElement: null, hidden: false, hasFocus: () => focused, getElementById: (id) => made[id] || null,
  querySelector: () => null, querySelectorAll: () => [], addEventListener(k, f) { docOn[k] = f; }, createElement: () => el('') };
globalThis.addEventListener = (k, f) => { winOn[k] = f; };
globalThis.localStorage = { getItem: () => null, setItem() {} };
globalThis.MutationObserver = function () { this.observe = () => {}; };
globalThis.SpeechSynthesisUtterance = function (t) { this.text = t; };
globalThis.speechSynthesis = { speaking: false, pending: false, cancel() {}, speak() {}, getVoices: () => [] };
globalThis.API = { get: async (p) => p === '/api/settings' ? { voice_commands: 'on', voice_tour: 'done', voice_wake: 'on' } : {},
  patch: async () => {}, post: async () => ({}) };
globalThis.showToast = (t, s) => toasts.push([t, s]);
globalThis.esc = (s) => String(s);
globalThis.askGroundwork = (q) => asked.push(q);
let reply = '';
globalThis._gwFetch = async (p) => { sent.push(p); return { ok: true, json: async () => ({ data: { text: reply } }) }; };
let node = null, opened = 0, stopped = 0;
Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: { getUserMedia: async () => { opened++; return { getTracks: () => [{ stop() { stopped++; } }] }; } } } });
globalThis.AudioContext = function () { this.sampleRate = 16000;
  this.createMediaStreamSource = () => ({ connect() {} }); this.createScriptProcessor = () => (node = { connect() {}, disconnect() {} });
  this.destination = {}; this.close = () => {}; };
const mods = {};
globalThis.GWTeaching = { register: (n, m) => { mods[n] = m; } };
""" + acc + r"""
const frame = (v) => ({ inputBuffer: { getChannelData: () => new Float32Array(4096).fill(v) } });
const say = async (text) => { reply = text; for (let t = 0; t < 900; t += 256) { now += 256; node.onaudioprocess(frame(0.2)); }
  for (let t = 0; t < 1200; t += 256) { now += 256; node.onaudioprocess(frame(0)); } await new Promise(r => setTimeout(r, 10)); };
const wait = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  await wait(800);                                     // load() arms it 600 ms after start
  const a = mods.access, out = {};
  out.armed = [a.listening(), opened, toasts.length];
  await say('how much is the rent this month');       // the room talking: not for Groundwork
  out.chatter = [asked.slice(), toasts.length];
  await say('Groundwork, open my budget');
  out.named = asked.slice();
  now += 3000; await say('and my debts');            // a follow-up within a few seconds
  out.follow = asked.slice();
  now += 20000; await say('open settings');          // long after: not for Groundwork
  out.late = asked.slice();
  await say('Groundwork.');                           // its name alone, then the command
  now += 2000; await say('show me my kroger transactions');
  out.nameThen = asked.slice();
  for (let t = 0; t < 70000; t += 256) { now += 256; node.onaudioprocess(frame(0)); }
  out.quietStays = a.listening();                     // a quiet minute does not turn listening-for-its-name off
  focused = false; winOn.blur && winOn.blur();
  out.blurred = [a.listening(), toasts.filter(t => /microphone is off/i.test(t[0])).length, stopped];
  focused = true; winOn.focus && winOn.focus(); await wait(300);
  out.back = [a.listening(), opened];
  console.log(JSON.stringify(out));
})().catch(e => console.log(JSON.stringify({ error: String(e && e.stack || e) })));
"""
    f = os.path.join(tempfile.mkdtemp(prefix='s277_'), 'wake.js')
    open(f, 'w', encoding='utf-8').write(prog)
    r = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        o = {'error': (r.stdout + r.stderr)[-600:]}
    check(f"s277 V3 on and in front, the microphone opens by itself, quietly ({o.get('armed')}, {o.get('error')})",
          o.get('armed') == [True, 1, 0])
    check(f"s277 V3 what isn't said to Groundwork is let go - not acted on, no toast ({o.get('chatter')})",
          o.get('chatter') == [[], 0])
    check(f"s277 V3 \"Groundwork, open my budget\" acts on \"open my budget\"; a follow-up within a few seconds counts; "
          f"long after, it is let go; its name alone waits for the command ({o.get('named')}, {o.get('follow')}, "
          f"{o.get('late')}, {o.get('nameThen')})",
          o.get('named') == ['open my budget'] and o.get('follow') == ['open my budget', 'and my debts']
          and o.get('late') == ['open my budget', 'and my debts']
          and o.get('nameThen') == ['open my budget', 'and my debts', 'show me my kroger transactions'])
    check(f"s277 V3 a quiet minute leaves it listening for its name; leaving the window turns it off without a toast, "
          f"coming back turns it on ({o.get('quietStays')}, {o.get('blurred')}, {o.get('back')})",
          o.get('quietStays') is True and o.get('blurred', [None, None, 0])[:2] == [False, 0]
          and o.get('back') == [True, 2])
