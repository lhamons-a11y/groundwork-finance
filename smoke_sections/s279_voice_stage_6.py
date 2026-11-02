"""Item 116 stage 6 + V18 (gw 2.0/VOICE_ASSISTANT.md section 4, Rob 2026-10-31: "I approve v13-v18"):

    V13  spoken figures in: "four hundred fifty dollars" is 450 dollars before anything reads it
    V14  dictation: "type ..." into the box the cursor is in; that box's own Save keeps it
    V16  "say Meijer like my-er": kept in Settings, shown, removable, applied before Groundwork speaks; never learned
         without being told
    V17  step by step: a job one spoken step at a time - next step, previous step, repeat, stop
    V18  the kept microphone answer on macOS and Linux, through each window's own hook - written without the hardware
"""
import json
import os
import shutil
import subprocess
import tempfile


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    node = shutil.which('node')
    if node:
        js = (acc[acc.index('  var NUM_SMALL = '):acc.index('  // V16 (item 116):')]
              + acc[acc.index('  var GUIDES = {'):acc.index('  function route(text) {')]
              + r"""
globalThis.window = globalThis; globalThis.Event = function (t) { this.type = t; };
const toasts = [], said = [], opened = [];
function showToast(t, s) { toasts.push([t, s]); }
function say(w) { said.push(w); return true; }
function _hush() {}
globalThis.showView = v => opened.push(v); globalThis.showImportModal = () => opened.push('import');
globalThis._debtShowTab = t => opened.push('tab:' + t); globalThis.addCard = () => opened.push('addCard');
globalThis.setTimeout = (f) => f();
""")
        js = js.replace("  document.addEventListener('focusin', function (e) {", "  0 && (function (e) {")
        js += r"""
const out = {};
out.figures = ['set groceries to four hundred fifty', 'set groceries to four hundred and fifty dollars',
  'add a forty dollar grocery purchase at Kroger', 'twelve hundred', 'one thousand two hundred fifty', 'a hundred dollars',
  'twenty five dollars and fifty cents', 'show me one', 'open a statement', 'Groundwork, open my budget.']
  .map(q => [q, _figures(q)]);
const box = { tagName: 'TEXTAREA', value: 'Paid at the', selectionStart: 11, selectionEnd: 11, offsetParent: {},
  dispatchEvent() { this.fired = true; }, focus() {}, setSelectionRange() {} };
globalThis.document = { body: { contains: () => true } };
_lastField = box; _dictate('farmers market');
out.dictate = [box.value, !!box.fired, toasts[toasts.length - 1][1]];
_lastField = null; _dictate('hello');
out.noBox = toasts[toasts.length - 1][0];
const r = q => { said.length = 0; opened.length = 0; const hit = _guideRoute(q, 'Heard'); return [hit, said[0] || null, opened.slice()]; };
out.start = r('walk me through how to import a statement');
out.next = r('next step');
out.again = r('repeat');
out.back = r('previous step');
out.other = r('how much do i owe');
out.end = r('stop');
out.after = r('next step');
out.card = r('help me add a credit card');
console.log(JSON.stringify(out));
"""
        f = os.path.join(tempfile.mkdtemp(prefix='s279_'), 'stage6.js')
        open(f, 'w', encoding='utf-8').write(js)
        r = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=30)
        try:
            o = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            o = {'error': (r.stdout + r.stderr)[-500:]}
        want = ['set groceries to 450', 'set groceries to 450 dollars', 'add a 40 dollar grocery purchase at Kroger', '1200',
                '1250', '100 dollars', '25.50 dollars', 'show me one', 'open a statement', 'Groundwork, open my budget.']
        got = [x[1] for x in o.get('figures', [])]
        check(f"s279 V13 spoken figures become figures - and words that are not amounts are left alone "
              f"({[(a, b) for a, b in zip(got, want) if a != b] or o.get('error')})", got == want)
        check(f"s279 V14 \"type ...\" goes into the box the cursor is in, as typing would, and nothing is saved by it; "
              f"with no box, it says to click one ({o.get('dictate')}, {o.get('noBox')})",
              o.get('dictate') == ['Paid at the farmers market', True, 'Nothing is saved until you save it there.']
              and o.get('noBox') == 'Click the box to type into first')
        check(f"s279 V17 a job step by step: it starts, goes on, repeats, goes back, lets other questions through, and "
              f"ends on stop ({o.get('start')}, {o.get('next')}, {o.get('back')}, {o.get('other')}, {o.get('end')}, "
              f"{o.get('after')})",
              o.get('start', [None, ''])[0] is True and o.get('start')[1].startswith('Step 1 of 5. Download')
              and o.get('next') == [True, 'Step 2 of 5. I am opening Import on the Ledger.', ['ledger', 'import']]
              and o.get('again', [None, ''])[1].startswith('Step 2 of 5.')
              and o.get('back', [None, ''])[1].startswith('Step 1 of 5.')
              and o.get('other') == [False, None, []] and o.get('end') == [True, 'OK, the steps are closed.', []]
              and o.get('after') == [False, None, []]
              and o.get('card', [None, '', []])[2] == ['debt', 'tab:setup', 'addCard'])

    from core import speak
    import numpy as np
    heard = []

    class _Fake:
        def create(self, words, voice, speed, lang):
            heard.append(words)
            return np.zeros(2400, dtype=np.float32), 24000
    real = speak._load, speak.status
    speak._load, speak.status = (lambda: _Fake()), (lambda: {'available': True, 'reason': ''})
    try:
        c.patch('/api/settings', headers=HJ, data=json.dumps({'speak_lexicon': json.dumps({'Meijer': 'my-er'})}))
        c.post('/api/voice/speak', headers=HJ, data=json.dumps({'text': 'Meijer: $40.00, at MEIJER #12.'}))
        c.patch('/api/settings', headers=HJ, data=json.dumps({'speak_lexicon': '{}'}))
        c.post('/api/voice/speak', headers=HJ, data=json.dumps({'text': 'Meijer: $40.00.'}))
    finally:
        speak._load, speak.status = real
    check(f"s279 V16 a name taught is said that way, whole words only, and forgotten when removed ({heard})",
          heard == ['my-er: 40 dollars, at my-er #12.', 'Myer: 40 dollars.'])   # removed: back to the built-in MY-er (2026-11-01)
    check('s279 V16 taught by voice, with Undo; shown in Settings with Remove; never learned without being told',
          "_save('speak_lexicon', JSON.stringify(lex))" in acc and 'data-gw-unsay' in acc
          and "say\\s+(.+?)\\s+(?:like|as)\\s+" in acc)

    src = (ctx.BASE / 'launch.py').read_text(encoding='utf-8')
    check('s279 V18 the kept microphone answer is wired for macOS (WKUIDelegate) and Linux (WebKitGTK), through the '
          'same microphone_answer rule, and says it is unproven without the hardware',
          'return _keep_microphone_answer_mac(window)' in src and 'return _keep_microphone_answer_gtk(window)' in src
          and b'webView:requestMediaCapturePermissionForOrigin:initiatedByFrame:type:decisionHandler:'.decode() in src
          and "view.connect('permission-request', on_permission)" in src
          and src.count('microphone_answer(') >= 4 and 'WRITTEN WITHOUT THE HARDWARE' in src)
