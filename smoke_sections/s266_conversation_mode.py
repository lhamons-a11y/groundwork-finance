"""Item 114 stage 3 (gw 2.0/AGENT_HANDS.md H14, H15; Rob 2026-10-30: "When a user selects the microphone to be turned on
it should stay on so the user can talk with the software ... the button on the microphone should be a microphone
button in the text box"). Run on the page's own code in Node, with a stand-in microphone:

    H14  one tap and it stays on; each thing said, ended by a pause, is sent on its own; "stop" turns it off; it does
         not listen while Groundwork is speaking; a minute of quiet turns it off
    H14  a spoken "yes" answers the assistant's question, but never makes a change - a card's Yes is pressed (H7)
    H15  the microphone is a button inside the Ask box
    P6   an answer to a spoken question is read back in Groundwork's own words only - never the model's
"""
import json
import shutil
import subprocess


def run(ctx):
    check = ctx.check
    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    node = shutil.which('node')
    if not node:
        check('s266 node is available for the page test', False)
        return
    prog = r"""
globalThis.window = globalThis;
const made = {}, toasts = [], spoken = [], asked = [], sent = [];
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
let speaking = false;
globalThis.SpeechSynthesisUtterance = function (t) { this.text = t; };
globalThis.speechSynthesis = { get speaking() { return speaking; }, pending: false, cancel() {}, speak(u) { spoken.push(u.text); },
  getVoices: () => [{ name: 'local', lang: 'en-US', localService: true }] };
globalThis.API = { get: async (p) => p === '/api/settings' ? { voice_commands: 'on', voice_tour: 'done' } : {}, patch: async () => {},
  post: async () => ({}) };
globalThis.showToast = (t, s) => toasts.push([t, s]);
globalThis.esc = (s) => String(s);
globalThis.askGroundwork = (q) => asked.push([q, !!window._gwVoiceAsked]);
let reply = 'how much did we spend on groceries';
globalThis._gwFetch = async (p, o) => { sent.push(p); return { ok: true, json: async () => ({ data: { text: reply } }) }; };
let node = null, stopped = 0;
Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: { getUserMedia: async () => ({ getTracks: () => [{ stop() { stopped++; } }] }) } } });   // Node has a navigator of its own
globalThis.AudioContext = function () { this.sampleRate = 16000;
  this.createMediaStreamSource = () => ({ connect() {} }); this.createScriptProcessor = () => (node = { connect() {}, disconnect() {} });
  this.destination = {}; this.close = () => {}; };
const mods = {};
globalThis.GWTeaching = { register: (n, m) => { mods[n] = m; } };
""" + acc + r"""
const frame = (v) => ({ inputBuffer: { getChannelData: () => new Float32Array(4096).fill(v) } });
const run = async (v, ms) => { for (let t = 0; t < ms; t += 256) { now += 256; node.onaudioprocess(frame(v)); } await new Promise(r => setTimeout(r, 5)); };
(async () => {
  await new Promise(r => setTimeout(r, 10));
  const a = mods.access, out = {};
  out.button = !!made.gwMicBtn && made.gwAskWrap && 'gwMicBtn' in made;
  made.gwMicBtn.onclick({ preventDefault() {} });
  await new Promise(r => setTimeout(r, 5));
  out.on = a.listening();
  await run(0.2, 1500); await run(0, 1200);                 // said something, then a pause
  out.firstSent = sent.length;
  await run(0.2, 1200); await run(0, 1200);                 // and again - still on
  out.secondSent = sent.length; out.stillOn = a.listening();
  out.asked = asked.slice();
  // its own voice is not taken for the person's: a clip over speech is heard, and let go - it is no short word (V2)
  speaking = true; await run(0.3, 2000); await run(0, 1200); speaking = false; await run(0, 1200);
  out.whileSpeaking = [sent.length, asked.length];
  // and "stop" said over it cuts it off (item 116 V2)
  const hushed = []; globalThis.speechSynthesis.cancel = () => hushed.push(1);
  speaking = true; reply = 'Stop.'; await run(0.3, 600); await run(0, 1200); speaking = false;
  out.bargeStop = [hushed.length > 0, asked.length, toasts[toasts.length - 1][1]];
  reply = 'how much did we spend on groceries';
  window._assistProposal = { ticket: 'x' }; made.askPanel = el('askPanel');
  reply = 'yes'; await run(0.2, 600); await run(0, 1200);
  out.yesOnCard = toasts[toasts.length - 1][1]; out.yesAsked = asked.length;
  delete window._assistProposal;
  reply = 'stop'; await run(0.2, 600); await run(0, 1200);
  out.offAfterStop = !a.listening(); out.tracksStopped = stopped;
  made.gwMicBtn.onclick({ preventDefault() {} }); await new Promise(r => setTimeout(r, 5));
  await run(0, 61000);
  out.quietOff = !a.listening();
  console.log(JSON.stringify(out));
})().catch(e => console.log(JSON.stringify({ error: String(e && e.stack || e) })));
"""
    # A file, not `node -e`: the program carries all of access.js, and Windows refuses a command line past 32,767
    # characters (it passed that on 2026-10-31)
    import os, tempfile
    f = os.path.join(tempfile.mkdtemp(prefix='s266_'), 'conv.js')
    open(f, 'w', encoding='utf-8').write(prog)
    r = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        o = {'error': (r.stdout + r.stderr)[-600:]}
    check(f"s266 H15 the microphone is a button inside the Ask box ({o.get('error')})", o.get('button') is True)
    check(f"s266 H14 one tap and it stays on: each thing said, ended by a pause, is sent on its own ({o.get('firstSent')}, "
          f"{o.get('secondSent')}, {o.get('stillOn')}, {o.get('asked')})",
          o.get('on') is True and o.get('firstSent') == 1 and o.get('secondSent') == 2 and o.get('stillOn') is True
          and o.get('asked') == [['how much did we spend on groceries', True]] * 2)
    check(f"s266 H14 / 116 V2 while Groundwork speaks, what it hears is let go unless it is a short word; 'stop' cuts it "
          f"off ({o.get('whileSpeaking')}, {o.get('bargeStop')})",
          o.get('whileSpeaking') == [3, 2] and o.get('bargeStop') == [True, 2, 'Stopped reading'])
    check(f"s266 H7 a spoken yes never makes a change - the card's Yes is pressed ({o.get('yesOnCard')})",
          o.get('yesOnCard') == 'To make the change, press Yes on the card.' and o.get('yesAsked') == 2)
    check(f"s266 H14 'stop' turns the microphone off, and the microphone is released ({o.get('tracksStopped')})",
          o.get('offAfterStop') is True and (o.get('tracksStopped') or 0) >= 1)
    check('s266 H14 a minute with nothing said turns it off', o.get('quietOff') is True)

    # P6: what is read back is Groundwork's own; the model's lead and close are never read
    srv, js = ctx.server_src, ctx.app_src
    check("s266 P6 an answer to a spoken question is read back without the model's words",
          "'say': [x for x in (out.get('shown') or []) if x not in (out.get('model_words') or [])]" in srv
          and "window.GWVoice.say(res.say.join(' '))" in js and "out['model_words'] = w['words']"
          in (ctx.BASE / 'core' / 'agent_hands.py').read_text(encoding='utf-8'))
    check('s266 H15 the Ask box holds the microphone', 'id="gwAskWrap"' in ctx.html_src and '#gwAskWrap.has-mic #gwMicBtn' in ctx.html_src)
