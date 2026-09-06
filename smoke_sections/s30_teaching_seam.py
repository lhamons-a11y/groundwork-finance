"""The teaching-layer seam (GW 2.0).

The 2.0 teaching layer lives entirely under static/js/teaching/. It is excluded
from a GW LTS build by path, not by runtime flag, so an LTS build does not
contain it. Three things have to hold for that to be true rather than
aspirational, and all three are checked here.

This ran on master only while lts/1.x was a separate code line, because the
directory it guards did not exist there. It does now: master merged into
lts/1.x and the two are the same tree, so which product a build is comes from
GW_PRODUCT and nothing else. That makes this section MORE load-bearing rather
than less. The teaching layer now sits in the release line's own checkout, and
the only thing keeping it out of an LTS build is the path strip these checks
verify.
"""
import re
import shutil as _shutil
from pathlib import Path

_DEF_FN = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(')
# Parameters are locals too. Without this, a callback parameter that is CALLED
# rather than passed on reads as a missing app.js global - which is exactly
# what this reported the first time a module named one `then`.
_PARAMS_FN = re.compile(r'function\s*[A-Za-z_$][\w$]*\s*\(([^)]*)\)')
_PARAMS_ANON = re.compile(r'function\s*\(([^)]*)\)')
_PARAMS_ARROW = re.compile(r'\(([^)]*)\)\s*=>')


def _params(src):
    """Every parameter name bound anywhere in the source."""
    names = set()
    for pattern in (_PARAMS_FN, _PARAMS_ANON, _PARAMS_ARROW):
        for group in pattern.findall(src):
            for part in group.split(','):
                bare = part.strip().split('=')[0].strip()
                if re.fullmatch(r'[A-Za-z_$][\w$]*', bare or ''):
                    names.add(bare)
    return names
_DEF_VAR = re.compile(r'(?:let|const|var)\s+([A-Za-z_$][\w$]*)\s*=')
_DEF_WIN = re.compile(r'window\.([A-Za-z_$][\w$]*)\s*=')
_CALL = re.compile(r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(')

_JS_KEYWORDS = {
    'if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'typeof',
    'new', 'else', 'do', 'try', 'throw', 'delete', 'void', 'in', 'of', 'var',
    'let', 'const', 'await', 'yield', 'instanceof', 'async',
}
_JS_GLOBALS = {
    'JSON', 'Math', 'Object', 'Array', 'Number', 'String', 'Date', 'Promise',
    'Set', 'Map', 'parseFloat', 'parseInt', 'isNaN', 'isFinite', 'setTimeout',
    'clearTimeout', 'setInterval', 'clearInterval', 'document', 'window',
    'console', 'decodeURIComponent', 'encodeURIComponent', 'Error', 'fetch',
    'alert', 'confirm', 'requestAnimationFrame',
    'GWTeaching',   # the seam's own namespace, defined by teaching/index.js
    'API',          # app.js's fetch wrapper, reached as a bare global
}


def _code_only(src):
    """The executable characters of a JS source; comments and string TEXT gone.

    Regexes fail this in both directions and both mattered. Prose inside a
    comment - "an LTS build (2.0)" - reads as a call to build(), which is how
    the first version of this check reported four dependencies that did not
    exist. And a template literal carries real calls inside its ${...}, so
    dropping templates whole hides the very dependencies being looked for -
    which is how the second version reported four modules borrowing less than
    they do. Interpolations are kept, recursively; everything quoted is not.
    """
    ESC = '\\'
    out = []
    i, n = 0, len(src)
    while i < n:
        two = src[i:i + 2]
        if two == '//':
            j = src.find('\n', i)
            i = n if j < 0 else j
            continue
        if two == '/*':
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        ch = src[i]
        if ch in ('"', "'"):
            i += 1
            while i < n and src[i] != ch:
                i += 2 if src[i] == ESC else 1
            i += 1
            continue
        if ch == '`':
            i += 1
            while i < n:
                if src[i] == ESC:
                    i += 2
                    continue
                if src[i] == '`':
                    i += 1
                    break
                if src[i:i + 2] == '${':
                    depth, i = 1, i + 2
                    start = i
                    while i < n and depth:
                        if src[i] == '{':
                            depth += 1
                        elif src[i] == '}':
                            depth -= 1
                        i += 1
                    out.append(' ' + _code_only(src[start:i - 1]) + ' ')
                    continue
                i += 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def run(ctx):
    check, BASE, c, H = ctx.check, ctx.BASE, ctx.c, ctx.H
    app_src, _TMP = ctx.app_src, ctx.TMP
    import shutil as _shutil
    from server import GW_VERSION as _srv_version

    # (1) The dependency runs ONE WAY: teaching code may read app.js, app.js may
    # never reference teaching code. This is the whole seam. The moment app.js
    # carries an `if (window.GWTeaching)` branch, the LTS build ships a dead
    # path for a feature it cannot run - on the machines with the least room -
    # and the directory is just a runtime flag in a costume.
    _app_teaching_refs = [ln.strip() for ln in app_src.splitlines()
                          if 'GWTeaching' in ln or 'js/teaching' in ln]
    check('app.js contains no reference to the teaching layer (one-way dependency)',
          not _app_teaching_refs)
    if _app_teaching_refs:
        for ln in _app_teaching_refs[:5]:
            print(f'        {ln[:100]}')

    # (1b) The same rule, in the form that actually bit. The grep above asks
    # whether app.js NAMES the teaching layer, which it never did — the 2.0
    # features were written straight into app.js instead, so the seam was
    # bypassed rather than violated and every check stayed green while an LTS
    # build carried the whole teaching layer.
    #
    # A feature is in the teaching layer if it consumes a teaching ROUTE. That
    # is checkable, and it is the honest generalisation of the one-way rule:
    # app.js may not reference teaching code, and it may not call it either.
    TEACHING_ROUTES = (
        '/api/debt/accelerations', '/api/debt/capacity', '/api/debt/teaching',
        '/api/debt/green-light', '/api/debt/cycle', '/api/budget/pressure',
        '/api/transactions/lesson', '/api/sinking-funds/pace',
        '/api/proactive/', '/api/trophies', '/api/byb/memory',
    )
    #
    # Six surfaces are out (see static/js/teaching/). The rest are pinned rather
    # than waved through: their teaching content is interleaved INSIDE app.js
    # template strings — a receipt inside a trophy card, a clause inside the
    # trip's sentence — so moving them needs DOM post-processing and, for the
    # trip, a decision about composing that sentence in two pieces. Pinned
    # exactly, so removing one is a passing change and adding a new one is a
    # failing one. The list only shrinks.
    #
    # /api/debt/decision-impact is NOT on this list and is not a teaching
    # route. It is Pillar 1's engine, and Before You Buy - a 1.x feature - gets
    # its own before-and-after payoff from it since that calculation was
    # unified onto the engine. Calling it teaching would strip an LTS build of
    # a comparison it has always shipped. What is teaching is the prose built
    # on top of the answer, and that has moved.
    STILL_IN_APP_JS = set()
    _app_teaching_calls = sorted({r for r in TEACHING_ROUTES if r in app_src})
    check('app.js consumes no teaching route beyond the pinned, interleaved ones',
          set(_app_teaching_calls) == STILL_IN_APP_JS)
    if set(_app_teaching_calls) != STILL_IN_APP_JS:
        added = set(_app_teaching_calls) - STILL_IN_APP_JS
        gone = STILL_IN_APP_JS - set(_app_teaching_calls)
        if added:
            print('        NEW drift into app.js: ' + ', '.join(sorted(added)))
        if gone:
            print('        moved out (shrink the pin): ' + ', '.join(sorted(gone)))

    _teaching_dir = BASE / 'static' / 'js' / 'teaching'
    _modules = sorted(f.name for f in _teaching_dir.glob('*.js'))
    check('the teaching layer has modules of its own, not just an entry point',
          len(_modules) > 1)
    check('and the loader emits every one of them, so adding a module is adding a file',
          all(f'/js/teaching/{name}' in _html_probe for name in _modules)
          if (_html_probe := c.get('/', headers=H).get_data(as_text=True)) else False)

    _teach_entry = BASE / 'static' / 'js' / 'teaching' / 'index.js'
    _teach_src = _teach_entry.read_text(encoding='utf-8') if _teach_entry.exists() else ''
    check('the teaching entry point exists and defines the GWTeaching namespace',
          bool(_teach_src) and 'window.GWTeaching' in _teach_src
          and 'register:' in _teach_src)

    # (2) Present in the build -> server emits the loader tag, after app.js.
    r = c.get('/', headers=H)
    _html = r.get_data(as_text=True)
    check('index.html is served with the teaching loader tag when the file is present',
          r.status_code == 200
          and f'/js/teaching/index.js?v={_srv_version}' in _html)
    check('the teaching loader is emitted after app.js (teaching reads app, not the reverse)',
          _html.find('/js/app.js') < _html.find('/js/teaching/index.js'))

    # (3) Absent from the build -> no tag at all. This is the LTS path, and it
    # is the half that would otherwise never be exercised until someone shipped
    # an LTS installer and found a 404 in the console. A second app on a static
    # folder with no teaching/ directory reproduces an LTS bundle exactly.
    _lts_static = Path(_TMP) / 'lts_static'
    (_lts_static / 'js').mkdir(parents=True, exist_ok=True)
    _shutil.copy(BASE / 'static' / 'index.html', _lts_static / 'index.html')
    _shutil.copy(BASE / 'static' / 'js' / 'app.js', _lts_static / 'js' / 'app.js')
    from server import create_app as _create_app
    _lts_app = _create_app(static_folder=str(_lts_static))
    _lts_html = _lts_app.test_client().get('/').get_data(as_text=True)
    check('a build without static/js/teaching/ serves NO teaching loader tag (the LTS path)',
          'js/teaching' not in _lts_html)
    check('that same LTS-shaped build still serves app.js normally',
          '/js/app.js' in _lts_html)

    # (4) All three specs strip the same path, and it is the same path server.py
    # looks for. Three platforms drifting apart here would ship a mac LTS build
    # that still carried the teaching layer, silently.
    _prefixes = {}
    for _spec in ('groundwork.spec', 'groundwork_linux.spec', 'groundwork_macos.spec'):
        _m = re.search(r"GW_TEACHING_PREFIX\s*=\s*'([^']+)'",
                       (BASE / _spec).read_text(encoding='utf-8'))
        _prefixes[_spec] = _m.group(1) if _m else None
    check('all three PyInstaller specs strip the same teaching-layer path',
          len(set(_prefixes.values())) == 1
          and next(iter(_prefixes.values())) == 'static/js/teaching/')
    if len(set(_prefixes.values())) != 1:
        for k, v in _prefixes.items():
            print(f'        {k}: {v}')

    # (5) The other end of the one-way dependency. Checks (1) and (1b) enforce
    # that app.js does not reach into teaching; nothing yet checks that what
    # teaching reaches for is still there. A helper renamed in app.js breaks
    # every module that borrowed it, at page load, with a ReferenceError - and
    # only in a 2.0 build, since the LTS line does not carry these files and
    # would never fail. Silent in the suite, silent in LTS, loud only in front
    # of a 2.0 user.
    _app_code = _code_only(app_src)
    _app_defs = (set(_DEF_FN.findall(_app_code)) | set(_DEF_VAR.findall(_app_code))
                 | set(_DEF_WIN.findall(_app_code)))
    # What the teaching layer defines for itself. Pillar 3's phrasing is said by
    # two surfaces - the trip planner and Before You Buy - so it lives in its
    # own module and both call it. That is teaching depending on teaching, which
    # is inside the seam; the rule this section enforces is about app.js.
    _teaching_src = ''
    for _mod in sorted(_teaching_dir.glob('*.js')):
        _teaching_src += _code_only(_mod.read_text(encoding='utf-8')) + chr(10)
    _teaching_defs = (set(_DEF_FN.findall(_teaching_src))
                      | set(_DEF_WIN.findall(_teaching_src)))
    _available = _app_defs | _teaching_defs

    _per_module, _dangling = {}, {}
    for _mod in sorted(_teaching_dir.glob('*.js')):
        if _mod.name == 'index.js':
            continue          # the namespace itself, and it borrows nothing
        _src = _code_only(_mod.read_text(encoding='utf-8'))
        _local = (set(_DEF_FN.findall(_src)) | set(_DEF_VAR.findall(_src))
                  | _params(_src))
        _ext = set(_CALL.findall(_src)) - _local - _JS_KEYWORDS - _JS_GLOBALS
        _per_module[_mod.name] = sorted(_ext & _app_defs)
        if _ext - _available:
            _dangling[_mod.name] = sorted(_ext - _available)
    _borrowed = {name for names in _per_module.values() for name in names}
    check('every app.js global the teaching modules call is still defined in app.js',
          not _dangling)
    for _name, _missing in _dangling.items():
        print(f'        {_name} calls, and app.js no longer defines: '
              + ', '.join(_missing))
    # Worth printing on the way past: this set is the seam's real surface area,
    # and it is small on purpose. A module reaching for a dozen app.js internals
    # is coupling, not borrowing.
    # Per module, not in total. The total only grows as surfaces move out, and
    # capping it would eventually be a reason not to move the next one. What
    # would actually be wrong is one module reaching deep into app.js, so that
    # is what this measures.
    _deepest = max((len(v) for v in _per_module.values()), default=0)
    check('and no single module reaches deep into app.js (borrowing, not coupling)',
          _deepest <= 8)
    print('        teaching borrows from app.js: ' + (', '.join(sorted(_borrowed)) or 'nothing'))
