"""Item 70: sturdier bank runs (gw 2.0/STURDIER_BANK_RUNS.md R1-R6; RULED 2026-10-10, Rob: "approve R1-R6 as
recommended"; built on "build item 70").

    R1  the sign-in page's own address is recorded (https, query dropped, identifiers masked) and opened ONCE when
        the link leads nowhere - only on the link's own site
    R2  each step keeps the path it was taken on; a stop says where the bank was; nothing navigates by it
    R3  show Groundwork again from step N: steps before N kept, the whole list reviewed
    R5  sign out before closing, after the allowed endings; never after a bot check, a payment guard, the person's
        Stop, or at a payment screen
"""
import json


class _Page:
    """A stand-in window: answers the agent's step calls from a list, its sign-out from `signout`, and its address."""
    def __init__(self, answers, path='/accounts/history', signout='pressed'):
        self.answers, self.sent, self.path, self.signout = list(answers), [], path, signout

    def evaluate_js(self, js):
        if js == 'location.pathname':
            return self.path
        if '__gwSignOut' in js and 'window.__gwDo ? window.__gwDo(' not in js:
            return self.signout
        if 'window.__gwDo ? window.__gwDo(' not in js:
            return None
        self.sent.append(js)
        return self.answers.pop(0) if self.answers else 'missing'


class _Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s



def _Driver(window, *a, **k):
    """The Driver on the bank's own site: the login guard has its own section (s287)."""
    import bank_agent_window as baw
    window.get_current_url = lambda: 'https://www.superiorcu.com/'
    return baw.Driver(window, *a, home='https://www.superiorcu.com/', **k)


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    import bank_agent_window as baw
    M = baw.MASK

    # ── R1 / R2: what is kept of an address ──
    check('s182 R2 a page path keeps its words and masks anything that could be an identifier; no query, no fragment',
          baw.clean_path('/auth/login') == '/auth/login' and baw.clean_path('/v2/accounts') == '/v2/accounts'
          and baw.clean_path('/accounts/6f9508b0-ab48/history?x=1#y') == f'/accounts/{M}/history'
          and baw.clean_path('/acct/12345') == f'/acct/{M}' and baw.clean_path('auth/login') is None
          and baw.clean_path('/' + 'a' * 250) is None)
    check('s182 R1 the sign-in address: https only, its query dropped, its path cleaned',
          baw.clean_signin_at('https://Online.SuperiorCU.com/auth/login?next=/x') == 'https://online.superiorcu.com/auth/login'
          and baw.clean_signin_at('http://online.superiorcu.com/auth/login') is None and baw.clean_signin_at('nonsense') is None)
    st = baw.clean_step({'k': 'sign_in', 'page': '/auth/login', 'at': 'https://online.superiorcu.com/auth/login?a=1'})
    ck = baw.clean_step({'k': 'click', 'text': 'Download', 'page': '/accounts/123456/history', 'at': 'https://evil.example/'})
    check('s182 R1/R2 a sign-in keeps its page and address; any other step keeps its page only',
          st == {'k': 'sign_in', 'page': '/auth/login', 'at': 'https://online.superiorcu.com/auth/login'}
          and ck == {'k': 'click', 'text': 'Download', 'page': f'/accounts/{M}/history'}
          and baw.step_words(st) == 'Sign in (Groundwork fills your saved login) at online.superiorcu.com/auth/login')
    check('s182 R1 same site means the same last two labels of the host - a lookalike is not',
          baw.same_site('https://online.superiorcu.com/x', 'https://www.superiorcu.com/')
          and not baw.same_site('https://superiorcu.com.evil.example/', 'https://www.superiorcu.com/')
          and not baw.same_site('https://bank.example.com/', 'https://www.superiorcu.com/'))
    rs = baw.RECORD_SCRIPT
    check('s182 R1/R2 the recorder notes where each step was taken, and a sign-in\'s address - in one place, for every step',
          "step.page = location.pathname;" in rs and "step.at = location.origin + location.pathname;" in rs
          and rs.count('window.pywebview.api.step(') == 1)
    src = (BASE / 'bank_agent_window.py').read_text(encoding='utf-8')
    child = src.split('def fetch_child_main')[1].split('\ndef ')[0]
    check('s182 R1 the window opens a recorded sign-in only when it is https, on the link\'s own site, and unmasked',
          "if not bw.portal_url_problem(u) and same_site(u, url) and MASK not in u:" in child and 'open_signin=_signin' in child)

    # ── R1 in a run: once, and only when the link leads nowhere ──
    steps = [{'k': 'sign_in', 'at': 'https://online.superiorcu.com/auth/login', 'page': '/auth/login'},
             {'k': 'click', 'text': 'Download', 'page': '/accounts/history'}]
    opened = []

    class _Late(_Page):
        def evaluate_js(self, js):
            if 'window.__gwDo ? window.__gwDo(' in js and not opened:
                self.sent.append(js)
                return 'missing'                 # the link led to a page with neither a sign-in nor the step
            return super().evaluate_js(js)
    page, clock, lines = _Late(['ok', 'ok']), _Clock(), []
    r = _Driver(page, steps, ('u', 'p'), lines.append, now=clock.now, sleep=clock.sleep, open_signin=opened.append).run()
    check('s182 R1 the link leads nowhere: the recorded sign-in page is opened once, and the run carries on',
          opened == ['https://online.superiorcu.com/auth/login'] and r == 'done')
    opened.clear()
    page, clock, lines = _Late([]), _Clock(), []

    class _Never(_Page):
        def evaluate_js(self, js):
            if 'window.__gwDo ? window.__gwDo(' in js:
                self.sent.append(js)
                return 'missing'
            return super().evaluate_js(js)
    page = _Never([])
    r = _Driver(page, steps, ('u', 'p'), lines.append, now=clock.now, sleep=clock.sleep, open_signin=opened.append).run()
    check('s182 R1 at most once: still nothing there, and the run stops as before', len(opened) == 1 and r == 'page_changed')
    page, clock, lines = _Never([]), _Clock(), []
    r = _Driver(page, [{'k': 'click', 'text': 'Download'}], ('u', 'p'), lines.append, now=clock.now, sleep=clock.sleep,
                   open_signin=opened.append).run()
    check('s182 R1 nothing recorded, nothing opened', len(opened) == 1 and r == 'page_changed')

    # ── R2: the stop says where the bank was ──
    page, clock, lines = _Never([], path='/auth/login'), _Clock(), []
    _Driver(page, [{'k': 'click', 'text': 'Download', 'page': '/accounts/history'}], ('u', 'p'), lines.append,
               now=clock.now, sleep=clock.sleep).run()
    end = baw.parse_fetch_line(lines[-1])
    words = baw.fetch_words(end, [{'k': 'click', 'text': 'Download', 'page': '/accounts/history'}])
    check('s182 R2 a stop names the step, where the bank was and where the step was recorded - and offers to show it again',
          end == {'s': 'stopped', 'i': 0, 'why': 'page_changed', 'page': '/auth/login'}
          and 'Stopped at step 1 (Click “Download”)' in words and 'The bank was on /auth/login, not /accounts/history' in words
          and 'it may have signed you out' in words and 'Show Groundwork again from step 1' in words)
    check('s182 R2 Groundwork checks the path again: an uncleaned one is refused',
          baw.parse_fetch_line('fetch {"s":"stopped","i":0,"why":"page_changed","page":"/acct/1234567"}') is None)
    check('s182 R2 no step navigates by its recorded page: the only address opened from a recipe is the sign-in (R1)',
          src.count('open_signin(') == 1 and "s['at']" in src and "s['page']" not in src)

    # ── R5: sign out ──
    page, clock, lines = _Page([], signout='pressed'), _Clock(), []
    d = _Driver(page, [], ('u', 'p'), lines.append, now=clock.now, sleep=clock.sleep)
    check('s182 R5 the bank\'s own Sign out is pressed, the bank is given a moment, and the line says so',
          d.sign_out() == 'pressed' and clock.t >= 5 and baw.parse_fetch_line(lines[-1]) == {'s': 'signed_out', 'found': 'pressed'}
          and baw.fetch_words({'s': 'signed_out', 'found': 'pressed'}, []) == 'Signed out of the bank.')
    page, clock, lines = _Page([], signout='none'), _Clock(), []
    _Driver(page, [], ('u', 'p'), lines.append, now=clock.now, sleep=clock.sleep).sign_out()
    check('s182 R5 no Sign out on the page: said plainly, nothing else touched',
          "couldn't find Sign out" in baw.fetch_words(baw.parse_fetch_line(lines[-1]), []) and clock.t == 0)
    ds = baw.DO_SCRIPT
    so = ds.split('window.__gwSignOut = function () {')[1].split('};')[0]
    check('s182 R5 the page finds Sign out / Log out / Log off by name, presses it the usual way, and knows when it is already signed out',
          "(sign|log)\\s?(out|off)" in so and 'press(els[0]);' in so and "return 'already';" in so)
    drive = child.split('def _drive():')[1]
    check('s182 R5 after the allowed endings only - never after a bot check, a payment guard or the person\'s Stop, and never at a payment screen',
          baw.SIGN_OUT_AFTER == ('downloaded', 'done', 'no_download', 'page_changed', 'code_timeout')
          and "if outcome in SIGN_OUT_AFTER and not driver.cancelled and not (hold and outcome == 'done'):" in drive
          and drive.index('driver.sign_out()') < drive.index('window.destroy()'))
    check('s182 R5 Get my accounts waits for each window to sign out and close before opening the next',
          "_await_closed(it['key'])" in src and "' \\u00b7 signed out'" in src)

    # ── R3: from step N ──
    from core.database import Account, AppSetting, db_session
    made = []
    try:
        with db_session() as s:
            a = Account(name='s182 Checking', type='checking', is_active=True, portal_url='https://bank.example.com')
            s.add(a); s.commit(); made.append(a.id); key = f'account:{a.id}'
            s.add(AppSetting(key=f'bank_recipe:{key}', value=json.dumps({'steps': [
                {'k': 'sign_in'}, {'k': 'click', 'text': 'Accounts'}, {'k': 'click', 'text': 'Old download'}]})))
            s.commit()
        baw.begin_for_test(key)
        with baw._lock:
            baw._recordings[key]['from'] = 2
        baw.collect(key, ['step {"k":"click","text":"New download"}\n'])
        fin = c.post('/api/settings/bank-agent/record/finish', headers=HJ, data=json.dumps({'key': key})).get_json()['data']
        check('s182 R3 re-recording from step 3 keeps steps 1-2 and replaces the rest; the review shows the whole list',
              [x.get('text', x['k']) for x in fin['steps']] == ['sign_in', 'Accounts', 'New download'] and fin['kept'] == 2)
        with db_session() as s:
            still = json.loads(s.query(AppSetting).filter_by(key=f'bank_recipe:{key}').first().value)['steps']
        check('s182 R3 nothing is saved until the person says yes (the old steps stand meanwhile)', len(still) == 3 and still[2]['text'] == 'Old download')
    finally:
        with db_session() as s:
            s.query(AppSetting).filter(AppSetting.key.in_([f'bank_recipe:account:{i}' for i in made])).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made)).delete(synchronize_session=False)
            s.commit()
    app = ctx.app_src
    check('s182 R3 the stop offers "Show Groundwork again from step N", in the account\'s box and in the Get my accounts panel',
          "startBankRecording('${escJs(key)}', ${end.i + 1})" in app and "startBankRecording('${escJs(it.key)}', ${it.i + 1})" in app
          and "fromStep ? { key, from_step: fromStep } : { key }" in app)
