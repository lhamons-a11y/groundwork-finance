"""Item 19 choice 5 (BANK_BROWSER.md section 9; Rob 2026-10-19: "B, user may also need to download another file"):
when a download's import offer appears, Groundwork's main window comes forward over the bank window, the bank window
stays open for the next download, and nothing is sent to it. The OS's own behaviour (Windows may refuse the front and
flash the taskbar instead) is measured in the packaged app; these checks hold the logic and the wiring."""
import sys
import types


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    calls = []

    class FakeWindow:
        def restore(self): calls.append('restore')
        def show(self): calls.append('show')
        def __setattr__(self, k, v): calls.append(f'{k}={v}')

    real = sys.modules.get('webview')
    sys.modules['webview'] = types.SimpleNamespace(windows=[FakeWindow()])
    try:
        import importlib
        launch = importlib.import_module('launch')
        ok = launch.GroundworkAPI().bring_to_front()
        sys.modules['webview'] = types.SimpleNamespace(windows=[])
        none = launch.GroundworkAPI().bring_to_front()
    finally:
        if real is not None:
            sys.modules['webview'] = real
        else:
            sys.modules.pop('webview', None)
    check('s241 the main window is restored, shown and raised over the bank window - then not left on top of everything',
          ok is True and calls[:4] == ['restore', 'show', 'on_top=True', 'on_top=False'])
    check('s241 with no app window (a browser), there is nothing to raise and nothing fails', none is False)

    app = ctx.app_src
    offer = app[app.index('function _offerAutoImport('):app.index('function _offerAutoImport(') + 4000]
    check('s241 the offer calls for the main window to come forward as it appears',
          'window.pywebview?.api?.bring_to_front?.()' in offer
          and offer.index('document.body.appendChild(el);') < offer.index('bring_to_front'))
    src = (BASE / 'launch.py').read_text(encoding='utf-8')
    body = src[src.index('    def bring_to_front(self):'):src.index('    def pick_folder(self):')]
    bank = (BASE / 'bank_window.py').read_text(encoding='utf-8')
    check('s241 the bank window stays open and is sent nothing: bringing forward touches only the main window',
          'windows[0]' in body and 'destroy' not in body and 'bring_to_front' not in bank
          and 'FlashWindowEx' in src)
