"""launch.py ships no tkinter.

tkinter cost ~10MB of tcl/tk in every bundle to draw two error dialogs and one
folder picker. Those now use ctypes/osascript/zenity (stdlib only - they fire
when an import has already failed, so they must not depend on anything that
could be the broken thing) and pywebview's own dialog. The specs exclude
tkinter outright, so a re-added import would not fail here - it would fail in a
built installer on a user's machine.
"""
import re


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    # tkinter cost ~10MB of tcl/tk in every bundle to draw two error dialogs and
    # one folder picker. Those now use ctypes/osascript/zenity (stdlib only -
    # they fire when an import has already failed, so they must not depend on
    # anything that could be the broken thing) and pywebview's own dialog. The
    # specs exclude tkinter outright, so a re-added import would not fail here,
    # it would fail in a built installer on a user's machine.
    _launch_src = (BASE / 'launch.py').read_text(encoding='utf-8')
    _tk_imports = [ln.strip() for ln in _launch_src.splitlines()
                   if re.match(r'\s*(import|from)\s+tkinter', ln)]
    check('launch.py imports no tkinter (the specs exclude it from every bundle)',
          not _tk_imports)
    if _tk_imports:
        for ln in _tk_imports:
            print(f'        {ln}')

    check('the stdlib error dialog and the pywebview folder picker are both wired',
          '_show_error_dialog' in _launch_src
          and 'create_file_dialog' in _launch_src
          and 'MessageBoxW' in _launch_src)

    _specs_excluding_tk = [f for f in ('groundwork.spec', 'groundwork_linux.spec',
                                       'groundwork_macos.spec')
                           if "'tkinter'," in (BASE / f).read_text(encoding='utf-8')]
    check('all three specs exclude tkinter (one platform keeping it re-adds 10MB there)',
          len(_specs_excluding_tk) == 3)
