"""The teaching-layer seam (GW 2.0).

The 2.0 teaching layer lives entirely under static/js/teaching/. It is excluded
from a GW LTS build by path, not by runtime flag, so an LTS build does not
contain it. Three things have to hold for that to be true rather than
aspirational, and all three are checked here.

This section is master-only on purpose. On lts/1.x the directory it guards does
not exist, so there is nothing to exclude and nothing to check - which is the
kind of thing the old shared append anchor in smoke_test.py could not express.
"""
import re
import shutil as _shutil
from pathlib import Path


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
