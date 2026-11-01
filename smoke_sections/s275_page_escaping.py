"""Found 2026-10-31 (Windows run, memory + security pass): three ways into the page, and one way out of Downloads.

    X1  a toast repeats names from the record - an imported category name carrying <img onerror=...> ran as code
        when "Leave in Other" was pressed. showToast now escapes its title and line; callers pass text.
    X2  esc() left ' alone, and 54 on*="fn('${esc(x)}')" handlers quoted record text with it: the attribute is
        decoded before the script runs, so a payer or category name carrying '); ran there. escJs() quotes for the
        script first, then the attribute; esc() now escapes ' too.
    X3  the page may talk to this server only (Content-Security-Policy on every response), so a script that does get
        in cannot send the record anywhere - core/egress.py only ever saw the server's own requests.
    X4  /api/auto-import/delete-file is gone: nothing called it, and it deleted any file in Downloads outright.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile


def _handler_quotes(src):
    """Every '${...}' quoted inside an on*="..." attribute, as (line, expression)."""
    out = []
    for ln, line in enumerate(src.split('\n'), 1):
        for m in re.finditer(r'\bon[a-z]+="([^"]*)"', line):
            out += [(ln, e) for e in re.findall(r"'\$\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'", m.group(1))]
    return out


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    js_dir = ctx.BASE / 'static' / 'js'
    app = (js_dir / 'app.js').read_text(encoding='utf-8')
    sources = {'app.js': app}
    for mod in sorted((js_dir / 'teaching').glob('*.js')):
        sources[mod.name] = mod.read_text(encoding='utf-8')

    toast = app[app.index('function showToast('):app.index('var _toastUndo = {};')]
    check('s275 X1 a toast writes its title and line as text, never markup',
          '${esc(title)}' in toast and '${esc(sub)}' in toast
          and not re.search(r'<div class="toast-(title|sub)">\$\{(title|sub)\}', toast))
    pre = [f'{n}:{app.count(chr(10), 0, m.start()) + 1}' for n, s in sources.items()
           for m in re.finditer(r'showToast\([^;]*?\besc\(', s)]
    check(f's275 X1 no caller escapes a toast first - it would show &amp; ({pre})', not pre)

    raw_esc = [f'{n}:{ln}' for n, s in sources.items() for ln, e in _handler_quotes(s) if e.startswith('esc(')]
    old = [n for n, s in sources.items() if re.search(r"esc\([^)]*\)\.replace\(/'/g", s)]
    check(f's275 X2 a quoted value in a handler goes through escJs, never esc alone ({raw_esc[:5]}, {old})',
          not raw_esc and not old and len([1 for s in sources.values() for _, e in _handler_quotes(s)
                                           if e.startswith('escJs(')]) >= 50)
    esc_fn = app[app.index("function esc(s='')"):app.index('function escJs(')]
    check('s275 X2 esc() escapes the single quote too', r".replace(/\x27/g,'&#39;')" in esc_fn)

    node = shutil.which('node')
    if node:
        fns = app[app.index("function esc(s='')"):app.index('// ─── DB write helpers')]
        hostile = ["O'Brien", "x');document.title='pwned';('", 'back\\slash\\', "a\\');alert(1);//", 'line\nbreak',
                   'sep arator', '<img src=x onerror="alert(1)">', '&#39;);alert(2);//', '"quoted"', 'é ünï €']
        script = fns + """
const decode = a => a.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const hostile = """ + json.dumps(hostile) + """;
let ran = false;
const out = hostile.map(x => {
  const attr = `f('${escJs(x)}')`;                       // what onclick="..." holds once the page is parsed
  if (attr.includes('"')) return [x, 'a raw " would end the attribute'];
  let got = null;
  try { new Function('f', 'document', 'alert', decode(attr))(v => { got = v; }, {set title(_) { ran = true; }}, () => { ran = true; }); }
  catch (e) { return [x, 'threw ' + e.message]; }
  return [x, got === x ? 'ok' : 'got ' + JSON.stringify(got)];
});
console.log(JSON.stringify({out, ran}));
"""
        d = tempfile.mkdtemp(prefix='s275_')
        f = os.path.join(d, 'esc.js')
        open(f, 'w', encoding='utf-8').write(script)
        res = json.loads(subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8',
                                        timeout=30).stdout or '{}')
        bad = [x for x in res.get('out', []) if x[1] != 'ok']
        check(f's275 X2 escJs: every hostile name reaches the handler exactly as written, and none runs ({bad})',
              res.get('out') and not bad and res.get('ran') is False)

    for path in ('/', '/api/health', '/api/accounts'):
        r = c.get(path, headers=H)
        csp = r.headers.get('Content-Security-Policy', '')
        parts = dict((p.split(' ', 1) + [''])[:2] for p in (x.strip() for x in csp.split(';')) if p)
        check(f's275 X3 {path}: the page may connect only to this server, load nothing from elsewhere, and frame nothing',
              parts.get('connect-src') == "'self'" and parts.get('default-src') == "'self'"
              and parts.get('object-src') == "'none'" and parts.get('frame-ancestors') == "'none'"
              and 'http' not in csp and '*' not in csp and r.headers.get('X-Content-Type-Options') == 'nosniff')

    gone = c.post('/api/auto-import/delete-file', headers=ctx.HJ, data=json.dumps({'path': 'anything.csv'}))
    import server
    check('s275 X4 /api/auto-import/delete-file is gone, and nothing in the server unlinks a Downloads file',
          gone.status_code in (404, 405) and not hasattr(server, 'auto_import_delete_file'))
