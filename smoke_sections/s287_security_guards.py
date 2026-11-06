"""Security audit 2026-11-05 (gw 2.0/SECURITY_AUDIT_2026_11.md; Rob: "Yes let's fix 1 and 3 first").

    Gap 1  a saved bank login is typed only on the bank's own site, by the window's own address and never the page's
           word for it; a login box anywhere else stops the run with nothing sent
    Gap 3  what leaves the Groundwork window: the system browser opens known sites, anything else on the person's Yes;
           the main window stays on Groundwork's own pages

Each guard is broken here on purpose and the break must be caught (the method of s125).
"""
import re

BANK = 'https://www.superiorcu.com/'
LOGIN = ('someone', 'the-saved-password')
SIGN_IN = {'k': 'sign_in'}
USERNAME = {'k': 'sign_in_user'}


class _Window:
    """The window as the Driver sees it. `says` is what the page would claim about itself, which must never matter."""
    def __init__(self, at, answers=(), says=None):
        self.at, self.answers, self.sent, self.says = at, list(answers), [], says

    def get_current_url(self):
        return self.at

    def evaluate_js(self, js):
        if js in ('location.href', 'location.hostname') and self.says:
            return self.says
        if 'window.__gwDo ? window.__gwDo(' not in js:
            return None
        self.sent.append(js)
        if self.answers:
            return self.answers.pop(0)
        # The agent's own rule: at a login box, no login means no_login
        return 'no_login' if ', null, ' in js else 'ok'


class _Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _mac_hold(ctx, lg, keep):
    """launch._hold_window_mac, run against stand-ins for PyObjC and pywebview so this holds on every platform. Measured
    on a real WKWebView window on 2026-11-06 (SECURITY_AUDIT_2026_11.md); these keep what was measured from drifting."""
    import logging
    import sys
    import types
    import launch

    check, HOME, EVIL, PORT, CANCEL = ctx.check, 'http://127.0.0.1:8765/?k=abc', 'https://evil.example/?d=secret', 8765, 0
    main, other = object(), object()

    class Instance:
        def __init__(self, win):
            self.pywebview_window = win

    class BrowserView:
        get_instance = staticmethod(lambda _attr, webview: Instance(webview))

        class BrowserDelegate:
            webView_decidePolicyForNavigationAction_decisionHandler_ = types.SimpleNamespace(
                callable=lambda _self, _webview, _action, handler: handler('pywebview answered'))

    added = []
    objc = types.ModuleType('objc')
    objc.registerMetaDataForSelector = lambda *a: None
    objc.selector = lambda fn, selector, signature: types.SimpleNamespace(fn=fn, selector=selector, signature=signature)
    objc.classAddMethods = lambda cls, methods: added.extend((cls, m) for m in methods)
    cocoa = types.ModuleType('webview.platforms.cocoa')
    cocoa.BrowserView = BrowserView

    def action(url, new_window=False):
        u = types.SimpleNamespace(absoluteString=lambda: url)
        return types.SimpleNamespace(request=lambda: types.SimpleNamespace(URL=lambda: u),
                                     targetFrame=lambda: None if new_window else object())

    def broken():
        raise ValueError('no address')

    names = ('objc', 'webview', 'webview.platforms', 'webview.platforms.cocoa')
    saved = {n: sys.modules.get(n) for n in names}
    sys.modules.update({'objc': objc, 'webview': types.ModuleType('webview'),
                        'webview.platforms': types.ModuleType('webview.platforms'), 'webview.platforms.cocoa': cocoa})
    try:
        launch._hold_window_mac(main, PORT)
    finally:
        for n, mod in saved.items():
            if mod is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = mod

    check('s287 gap 3 a Mac: the cancel goes on pywebview\'s own delegate, at the selector WebKit asks before sending',
          len(added) == 1 and added[0][0] is BrowserView.BrowserDelegate
          and added[0][1].selector == b'webView:decidePolicyForNavigationAction:decisionHandler:')
    if len(added) != 1:
        return
    answer = added[0][1].fn

    def ask(webview, act):
        got = []
        answer(None, webview, act, got.append)
        return got

    check('s287 gap 3 a Mac: Groundwork\'s own page goes on to pywebview', ask(main, action(HOME)) == ['pywebview answered'])
    check('s287 gap 3 a Mac: another address is cancelled, and only once', ask(main, action(EVIL)) == [CANCEL])
    check('s287 gap 3 a Mac: a new window goes on, to reach open_external',
          ask(main, action(EVIL, new_window=True)) == ['pywebview answered'])
    check('s287 gap 3 a Mac: this holds Groundwork\'s window and no other',
          ask(other, action(EVIL)) == ['pywebview answered'])

    seen = []

    class Hear(logging.Handler):
        def emit(self, record):
            seen.append(record.getMessage())
    hear, root = Hear(), logging.getLogger()
    root.addHandler(hear)
    try:
        cant_read = types.SimpleNamespace(request=broken, targetFrame=lambda: object())
        check('s287 gap 3 a Mac: a check that cannot read the address says no', ask(main, cant_read) == [CANCEL])
        ask(main, action(EVIL))
    finally:
        root.removeHandler(hear)
    check('s287 gap 3 a Mac: a stopped address is never logged: it may be the data',
          seen and not any('secret' in s or 'evil' in s for s in seen))

    # Break the guard: the check must notice
    real = lg.mac_window_may_go
    lg.mac_window_may_go = lambda *_a: True
    try:
        check('s287 gap 3 the mutation: a Mac guard that always says yes lets the address through',
              ask(main, action(EVIL)) == ['pywebview answered'])
    finally:
        lg.mac_window_may_go = real
    check('s287 gap 3 a Mac: the window keeps the way home as well, and the hold is put in place from _keep_window_home',
          "sys.platform == 'darwin'" in keep and '_hold_window_mac(window, port)' in keep and 'window.load_url(' in keep)


def _carries_password(window):
    return any(LOGIN[1] in js for js in window.sent)


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    import bank_agent_window as baw
    import link_guard as lg

    def drive(window, steps=(SIGN_IN,), home=BANK, login=LOGIN):
        clock, lines = _Clock(), []
        result = baw.Driver(window, list(steps), login, lines.append, now=clock.now, sleep=clock.sleep, home=home).run()
        return result, lines

    # ── Gap 1: where a login may go ──
    w = _Window('https://online.superiorcu.com/login')
    r, _ = drive(w)
    check('s287 gap 1 the bank\'s own site (another host on it): the saved login is filled', r == 'done' and _carries_password(w))

    for label, at in (('a stranger', 'https://evil.example/login'),
                      ('a lookalike ending in the bank\'s name', 'https://superiorcu.com.evil.example/login'),
                      ('a name containing the bank\'s', 'https://superiorcu-login.com/'),
                      ('the bank\'s site over plain http', 'http://www.superiorcu.com/login')):
        w = _Window(at)
        r, lines = drive(w)
        check(f's287 gap 1 {label}: the run stops as other_site and no password is sent',
              r == 'other_site' and not _carries_password(w) and baw.parse_fetch_line(lines[-1]).get('why') == 'other_site')

    w = _Window('https://evil.example/login', says='www.superiorcu.com')
    r, _ = drive(w)
    check('s287 gap 1 a page claiming to be the bank is not believed: the window\'s own address decides',
          r == 'other_site' and not _carries_password(w))

    class _Unreadable(_Window):
        def get_current_url(self):
            raise RuntimeError('no address')
    w = _Unreadable('')
    r, _ = drive(w)
    check('s287 gap 1 an address that cannot be read: no password', r == 'other_site' and not _carries_password(w))
    w = _Window(None)
    r, _ = drive(w)
    check('s287 gap 1 no address yet: no password', r == 'other_site' and not _carries_password(w))
    w = _Window('https://www.superiorcu.com/')
    r, _ = drive(w, home=None)
    check('s287 gap 1 no link given and nothing recorded: nowhere is allowed', r == 'other_site' and not _carries_password(w))

    w = _Window('https://login.cuvendor.example/')
    r, _ = drive(w, steps=[{'k': 'sign_in', 'at': 'https://login.cuvendor.example/auth'}])
    check('s287 gap 1 a sign-in the person recorded on another site stays allowed (banks that use a login vendor)',
          r == 'done' and _carries_password(w))

    # The login form that turns up during another step takes the same road
    w = _Window('https://evil.example/', answers=['login:sign_in'])
    r, _ = drive(w, steps=[{'k': 'click', 'text': 'Download'}])
    check('s287 gap 1 a login box met during another step, off the site: stopped, no password',
          r == 'other_site' and not _carries_password(w))
    w = _Window(BANK, answers=['login:sign_in', 'ok', 'ok'])
    r, _ = drive(w, steps=[{'k': 'click', 'text': 'Download'}])
    check('s287 gap 1 a login box met during another step, on the site: signed in and carried on',
          r == 'done' and _carries_password(w))

    # A page without a login box, off the site, is only a page on the way: no stop
    w = _Window('https://redirect.example/', answers=['missing', 'ok'])
    w.get_current_url = lambda: BANK if len(w.sent) else 'https://redirect.example/'
    r, _ = drive(w)
    check('s287 gap 1 a page on the way with no login box does not stop the run', r == 'done')

    # What is sent
    w = _Window(BANK)
    drive(w, steps=[USERNAME])
    check('s287 gap 1 the username step is given the username and never the password',
          LOGIN[0] in w.sent[0] and not _carries_password(w))
    w = _Window(BANK)
    drive(w)
    check('s287 gap 1 the login is sent only behind a check of the page\'s address in the same script, with operators a page cannot redefine',
          'location.protocol === "https:" && location.hostname === "www.superiorcu.com" ? (' in w.sent[0])
    w = _Window(BANK)
    baw.Driver(w, [SIGN_IN], LOGIN, lambda _l: None, now=_Clock().now, sleep=_Clock().sleep, home=BANK)._try(SIGN_IN, probe=True)
    check('s287 gap 1 a look at the page (a probe) carries no login', not _carries_password(w))

    src = (BASE / 'bank_agent_window.py').read_text(encoding='utf-8')
    child = src.split('def fetch_child_main')[1].split('\ndef ')[0]
    check('s287 gap 1 the real run gives the Driver the account\'s own link', 'home=url)' in child and 'Driver(window' in child)
    check('s287 gap 1 the stop has words on both surfaces', src.count("'other_site': ") == 2 and "wasn't on the bank's own site" in src)
    words = (BASE / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    check('s287 gap 1 the page does not wait for a sign-out after this stop', "'would_pay', 'other_site']" in words)

    # same_site
    same = baw.same_site
    check('s287 gap 1 same site: the bank\'s own hosts yes, shared endings no',
          same('https://online.superiorcu.com/', 'https://www.superiorcu.com/')
          and same('https://online.bank.co.uk/', 'https://www.bank.co.uk/')
          and not same('https://bank.co.uk/', 'https://evil.co.uk/')
          and not same('https://evil.github.io/', 'https://bank.github.io/')
          and not same('https://co.uk/', 'https://co.uk/')
          and not same('https://localhost/', 'https://localhost/')
          and not same('nonsense', BANK))

    # Break the guard: the check must notice
    real = baw.Driver._login_host
    baw.Driver._login_host = lambda self: 'evil.example'
    try:
        w = _Window('https://evil.example/login')
        r, _ = drive(w)
        check('s287 gap 1 the mutation: a guard that always says yes is what this section catches',
              _carries_password(w) and r == 'done')
    finally:
        baw.Driver._login_host = real

    # ── Gap 3: the system browser ──
    d = lg.decide
    check('s287 gap 3 known sites open without a question, with or without www, with a path or a query',
          all(d(u) == lg.OPEN for u in ('https://groundworkfinance.app/changelog', 'https://www.consumerfinance.gov/x',
                                        'https://988lifeline.org/', 'https://groundworkfinance.app/d?v=1')))
    check('s287 gap 3 a help line\'s Call and Text open: digits only', d('tel:988') == lg.OPEN and d('sms:741741') == lg.OPEN)
    check('s287 gap 3 anything else waits for the person',
          all(d(u) == lg.ASK for u in ('https://evil.example/?d=balance-1234', 'http://groundworkfinance.app/',
                                       'https://groundworkfinance.app.evil.example/', 'https://evilgroundworkfinance.app/',
                                       'https://groundworkfinance.app:8443/', 'https://www.superiorcu.com/')))
    check('s287 gap 3 what could be read two ways, or is no web address, is refused outright',
          all(d(u) == lg.REFUSE for u in ('', None, 42, 'file:///C:/x', 'javascript:alert(1)', 'data:text/html,x',
                                          'tel:988?body=x', 'sms:12', 'https://groundworkfinance.app@evil.example/',
                                          'https://user:pw@groundworkfinance.app/', 'https://groundworkfinance.app\\@evil.example/',
                                          'https://a b.example/', 'https://evil.example/\nx', 'https://x.example/' + 'a' * lg.MAX_ADDRESS,
                                          'https://x.example:notaport/')))
    title, message = lg.ask_words('https://evil.example/?d=1234')
    check('s287 gap 3 the question shows the whole address', 'https://evil.example/?d=1234' in message and title)

    linked = set(re.findall(r'https://([a-z0-9.-]+)', words + (BASE / 'static' / 'index.html').read_text(encoding='utf-8')))
    placeholders = {'www.yourbank.com', 'www.yourcompany.com', 'www.w3.org', 'yourbank.com'}
    strangers = sorted(h for h in linked - placeholders if lg.decide(f'https://{h}/') != lg.OPEN)
    check(f's287 gap 3 every site the page itself links to is a known one, so nobody is asked about Groundwork\'s own links: {strangers}',
          not strangers)

    # ── Gap 3: the window ──
    home = lg.stays_home
    check('s287 gap 3 the window may go to Groundwork\'s own pages, on its own port',
          all(home(u, 8765) for u in ('http://127.0.0.1:8765/', 'http://127.0.0.1:8765/?k=abc', 'http://localhost:8765/x',
                                      'about:blank', 'blob:http://127.0.0.1:8765/1234')))
    check('s287 gap 3 and nowhere else',
          not any(home(u, 8765) for u in ('https://evil.example/?d=1', 'http://127.0.0.1:9999/', 'https://127.0.0.1:8765/',
                                          'http://127.0.0.1.evil.example:8765/', 'http://x@127.0.0.1:8765/',
                                          'blob:https://evil.example/1', 'data:text/html,x', 'file:///C:/x', '', None,
                                          'http://127.0.0.1:8765\\@evil.example/')))

    launch = (BASE / 'launch.py').read_text(encoding='utf-8')
    api = launch.split('class GroundworkAPI')[1].split('def bring_to_front')[0]
    check('s287 gap 3 open_external decides before it opens anything, and a no is the default',
          api.index('link_guard.decide(url)') < api.index('os.startfile(url)')
          and 'verdict == link_guard.REFUSE or (verdict == link_guard.ASK and not _person_says_yes(url))' in api)
    check('s287 gap 3 a refused address is never logged: it may be the data',
          "logging.info('open_external: an address was not opened')" in api)
    keep = launch.split('def _keep_window_home')[1].split('\ndef ')[0]
    check('s287 gap 3 the main window is held, new windows go through open_external, and a check that fails says no',
          '_keep_window_home(window, api)' in launch and 'webbrowser.open = outside' in keep
          and 'NavigationStarting += on_navigating' in keep and keep.count('args.Cancel = True') == 2
          and "args=(url,)" in keep)
    _mac_hold(ctx, lg, keep)
    srv = (BASE / 'server.py').read_text(encoding='utf-8')
    check('s287 gap 3 the policy\'s comment no longer claims script has nowhere to send data',
          'leaves injected script nowhere to send data' not in srv)
