"""1.1.x security fixes (2026-10-31, Windows run; item 32 L1: security fixes ship on 1.x). The same fixes as 2.0:

    X1  a toast repeats names from the record - an imported category name carrying <img onerror=...> ran as code. A
        toast now escapes its title and line; callers pass text.
    X2  esc() left ' alone, and handlers quoted record text with it inside on*="fn('...')": the attribute is decoded
        before the script runs. escJs() quotes for the script first, then the attribute; esc() escapes ' too.
    X3  every response carries the security headers: the page may connect only to this server, load nothing but its
        own files (the fonts ship with the app since 2026-11-01), and cannot be framed.
    X4  /api/auto-import/delete-file is gone: nothing called it, and it deleted any file in Downloads outright.
    X5  1.1 had no host check: a DNS-rebinding page (its name made to resolve to 127.0.0.1) could read the token from
        index.html and use every route. The Host must name 127.0.0.1 or localhost on this port, and an /api/* request
        with an Origin must come from this server (2.0's BANK_BROWSER.md F12).
"""
import json
import os
import re
import shutil
import subprocess
import tempfile


def _handler_quotes(src):
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

    toast = app[app.index('function showToast('):app.index('function showToast(') + 1500]
    check('s234 X1 a toast writes its title and line as text, never markup',
          '${esc(title)}' in toast and '${esc(sub)}' in toast)
    pre = [n for n, s in sources.items() if re.search(r'showToast\([^;]*?\besc\(', s)]
    check(f's234 X1 no caller escapes a toast first ({pre})', not pre)
    raw = [f'{n}:{ln}' for n, s in sources.items() for ln, e in _handler_quotes(s) if e.startswith('esc(')]
    old = [n for n, s in sources.items() if re.search(r"esc\([^)]*\)\.replace\(/'/g", s)]
    check(f's234 X2 a quoted value in a handler goes through escJs, never esc alone ({raw[:5]}, {old})',
          not raw and not old and sum(1 for s in sources.values() for _, e in _handler_quotes(s) if e.startswith('escJs(')) >= 10)
    esc_fn = app[app.index("function esc(s='')"):app.index('function escJs(')]
    check('s234 X2 esc() escapes the single quote too', r".replace(/\x27/g,'&#39;')" in esc_fn)

    node = shutil.which('node')
    if node:
        fns = app[app.index("function esc(s='')"):app.index("function escJs(s='')")]
        fns += app[app.index("function escJs(s='')"):app.index('}', app.index("function escJs(s='')")) + 1] + '\n'
        hostile = ["O'Brien", "x');document.title='pwned';('", 'back\\slash\\', "a\\');alert(1);//", 'line\nbreak',
                   '<img src=x onerror="alert(1)">', '&#39;);alert(2);//', '"quoted"']
        script = fns + """
const decode = a => a.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
let ran = false;
const out = """ + json.dumps(hostile) + """.map(x => {
  const attr = `f('${escJs(x)}')`;
  if (attr.includes('"')) return [x, 'a raw " would end the attribute'];
  let got = null;
  try { new Function('f', 'document', 'alert', decode(attr))(v => { got = v; }, {set title(_) { ran = true; }}, () => { ran = true; }); }
  catch (e) { return [x, 'threw ' + e.message]; }
  return [x, got === x ? 'ok' : 'got ' + JSON.stringify(got)];
});
console.log(JSON.stringify({out, ran}));
"""
        f = os.path.join(tempfile.mkdtemp(prefix='s234_'), 'esc.js')
        open(f, 'w', encoding='utf-8').write(script)
        res = json.loads(subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=30).stdout or '{}')
        bad = [x for x in res.get('out', []) if x[1] != 'ok']
        check(f's234 X2 escJs: every hostile name reaches the handler exactly as written, and none runs ({bad})',
              res.get('out') and not bad and res.get('ran') is False)

    for path in ('/', '/api/health', '/api/accounts'):
        r = c.get(path, headers=H)
        csp = r.headers.get('Content-Security-Policy', '')
        parts = dict((p.split(' ', 1) + [''])[:2] for p in (x.strip() for x in csp.split(';')) if p)
        outside = set(re.findall(r'https?://[^\s;]+', csp))
        check(f's234 X3 {path}: connect only to this server, no frames, nosniff; no outside host at all - the '
              f'fonts ship with the app ({sorted(outside)})',
              parts.get('connect-src') == "'self'" and parts.get('default-src') == "'self'"
              and parts.get('object-src') == "'none'" and parts.get('frame-ancestors') == "'none'"
              and not outside and '*' not in csp
              and r.headers.get('X-Content-Type-Options') == 'nosniff' and r.headers.get('X-Frame-Options') == 'DENY')

    gone = c.post('/api/auto-import/delete-file', headers=ctx.HJ, data=json.dumps({'path': 'anything.csv'}))
    import server
    check('s234 X4 /api/auto-import/delete-file is gone', gone.status_code in (404, 405)
          and not hasattr(server, 'auto_import_delete_file'))

    def req(path, host, origin=None, token=True):
        env = {'HTTP_HOST': host}
        if origin:
            env['HTTP_ORIGIN'] = origin
        r = c.get(path, headers=H if token else {}, environ_overrides=env)
        return r.status_code
    check('s234 X5 a page under another name is refused - the page itself, health, and every route; so is a foreign '
          'Origin; this server by its own names is let through',
          req('/', 'evil.example', token=False) == 403 and req('/api/health', 'evil.example', token=False) == 403
          and req('/api/accounts', 'evil.example') == 403
          and req('/api/accounts', 'localhost', origin='http://evil.example') == 403
          and req('/', 'localhost', token=False) == 200 and req('/api/accounts', 'localhost') == 200
          and req('/api/accounts', '127.0.0.1', origin='http://127.0.0.1') == 200)
    real = server._request_host_refusal
    server._request_host_refusal = lambda environ, path: None
    try:
        broken = req('/', 'evil.example', token=False)
    finally:
        server._request_host_refusal = real
    check('s234 X5 proof: with the check removed, the other name gets the page (so the refusal above is the check)',
          broken == 200)
