"""app.js, and every teaching module after it, run top to bottom without a runtime error.

Found 2026-10-02 in the browser, not by the gate: an edit left a bare `async` on its own line in app.js. That is valid
syntax - `node --check` passed it - but at runtime `async` is an undefined name, so app.js stopped at that line and
everything after it (a `let` the Budget page reads, the onboarding labels a teaching module extends) never existed.
Nothing in the gate executed app.js, so nothing could see it.

This runs the shipped files in Node with browser objects that answer anything, in the page's own order (app.js, then
the teaching modules by file name). It proves only that the top level runs to the end - not that any feature works -
and that is exactly the failure that was invisible.
"""
import json
import shutil
import subprocess

RUNNER = r"""
const fs = require('fs'), vm = require('vm');
function stub() {
  const f = function () { return stub(); };
  return new Proxy(f, { get: (t, k) => k === Symbol.toPrimitive ? (() => '') : (k === 'then' ? undefined : stub()),
                        set: () => true, apply: () => stub(), construct: () => stub(), has: () => true });
}
const ctx = { console: { log() {}, warn() {}, error() {}, info() {} }, setTimeout() {}, setInterval() {}, clearTimeout() {},
              Promise, JSON, Math, Date, Object, Array, String, Number, Boolean, RegExp, Map, Set, Symbol, Error,
              parseFloat, parseInt, isNaN, isFinite, encodeURIComponent, decodeURIComponent, Intl };
['document', 'localStorage', 'sessionStorage', 'navigator', 'location', 'fetch', 'history', 'performance',
 'requestAnimationFrame', 'getComputedStyle', 'matchMedia', 'Chart', 'pywebview', 'alert', 'confirm', 'Event',
 'CustomEvent', 'MutationObserver', 'ResizeObserver', 'IntersectionObserver', 'Blob', 'URL', 'FileReader',
 'Option', 'Image', 'HTMLElement', 'Node', 'screen', 'crypto', 'AbortController', 'GW_SESSION_TOKEN']
  .forEach(k => { ctx[k] = stub(); });
ctx.window = ctx;                                   // scripts share one global, as in the page
['addEventListener', 'removeEventListener', 'dispatchEvent', 'open', 'close', 'scrollTo', 'scrollBy', 'print',
 'focus', 'blur', 'getSelection', 'postMessage', 'queueMicrotask', 'innerWidth', 'innerHeight', 'devicePixelRatio',
 'self', 'top', 'parent', 'clearInterval', 'cancelAnimationFrame', 'structuredClone', 'atob', 'btoa', 'TextEncoder',
 'TextDecoder', 'WebSocket', 'XMLHttpRequest', 'FormData', 'Headers', 'Request', 'Response', 'EventSource',
 'speechSynthesis', 'SpeechSynthesisUtterance', 'Audio', 'AudioContext', 'Notification', 'indexedDB', 'caches']
  .forEach(k => { if (!(k in ctx)) ctx[k] = stub(); });
vm.createContext(ctx);
const out = [];
for (const file of JSON.parse(process.argv[1])) {
  try { vm.runInContext(fs.readFileSync(file, 'utf8'), ctx, { filename: file }); out.push([file, 'ok']); }
  catch (e) { out.push([file, e.name + ': ' + e.message]); }
}
console.log(JSON.stringify(out));
"""


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    node = shutil.which('node')
    check('s64 node is available to run the page\'s scripts (skip the rest if not)', bool(node))
    if not node:
        return
    js = BASE / 'static' / 'js'
    teaching = js / 'teaching'
    # The page's own order (server.py's loader): app.js, then teaching/index.js (GWTeaching), then the modules by name.
    files = [str(js / 'app.js')]
    if (teaching / 'index.js').exists():
        files += [str(teaching / 'index.js')] + [str(p) for p in sorted(teaching.glob('*.js')) if p.name != 'index.js']

    def go(paths):
        r = subprocess.run([node, '-e', RUNNER, json.dumps(paths)], capture_output=True, text=True, encoding='utf-8',
                           timeout=60)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                                   # noqa: BLE001 - reported as a failure
            return [['runner', (r.stderr or 'no output')[:200]]]

    res = go(files)
    bad = [(f, e) for f, e in res if e != 'ok']
    check(f's64 app.js and {len(files) - 1} teaching module(s) run top to bottom without a runtime error',
          not bad and len(res) == len(files))
    for f, e in bad[:5]:
        print(f'        {f.split("static")[-1]}: {e}')

    broken = ctx.TMP / 's64_broken_app.js'
    src = (js / 'app.js').read_text(encoding='utf-8')
    broken.write_text(src.replace('\nfunction _rowMonth(', '\nasync // a bare async, as on 2026-10-02\nfunction _rowMonth(', 1)
                      if '\nfunction _rowMonth(' in src else src + '\nasync // a bare async\n', encoding='utf-8')
    res = go([str(broken)])
    check('s64 mutation caught: a bare `async` (valid syntax, a runtime ReferenceError) stops the run and is reported',
          res and res[0][1].startswith('ReferenceError') and 'async' in res[0][1])
