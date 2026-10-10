"""Item 57 stage 3: the fetch (gw 2.0/BANK_AGENT.md A2/A4/A6/A7; Rob 2026-10-09: "lets do stage 3").

    A2  started by the user's click only: a route, no schedule, no background start, no retry on its own
    A4  the password is read from the vault inside the agent's process and goes only into the page's login boxes -
        never into a line Groundwork reads, a log or a file
    A6  it stops and says why: a code asked for (it waits for the user), the page changed, a bot check (stops for
        good), no download in 2 minutes; nothing guessed, nothing retried on its own
    A7  a remembered device only when the user opted in for that account; unticking forgets it
The driver runs against a stand-in window whose page answers are scripted - no real bank, no real browser.
"""
import json
import re


class _Page:
    """A stand-in window. `answers` is a list of results per evaluate_js call; it records what it was sent."""
    def __init__(self, answers):
        self.answers, self.sent, self.bars = list(answers), [], []

    def evaluate_js(self, js):
        if 'window.__gwDo ? window.__gwDo(' not in js:
            self.bars.append(js)
            return None                     # the bar on the page (visual only) - kept apart from the agent's actions
        self.sent.append(js)
        return self.answers.pop(0) if self.answers else 'missing'


class _Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def run(ctx):
    check, c, H, HJ, BASE, srv, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE, ctx.server_src, ctx.app_src
    import bank_agent_window as baw
    from core import bank_vault

    STEPS = [{'k': 'sign_in'}, {'k': 'click', 'text': 'Accounts'}, {'k': 'choose', 'field': 'Range', 'option': 'Last 30 days'},
             {'k': 'click', 'text': 'Download'}]
    LOGIN = ('s174user', 's174-Secret-pw')

    def drive(answers, downloads_seq=None, login=LOGIN, steps=STEPS):
        page, clock, lines = _Page(answers), _Clock(), []
        seq = list(downloads_seq) if downloads_seq is not None else None
        dl = (lambda: seq.pop(0) if len(seq) > 1 else seq[0]) if seq is not None else None
        d = baw.Driver(page, steps, login, lines.append, now=clock.now, sleep=clock.sleep, downloads=dl)
        return d.run(), lines, page, clock

    r, lines, page, _ = drive(['ok', 'ok', 'ok', 'ok'], downloads_seq=[set(), set(), {'stmt.csv'}])
    evs = [baw.parse_fetch_line(l) for l in lines]
    check('s174 A6 a clean run follows each saved step in order and reports the file that arrived',
          r == 'downloaded' and [e['s'] for e in evs] == ['step', 'step', 'step', 'step', 'downloaded'] and evs[-1]['file'] == 'stmt.csv')
    check('s174 A4 the password goes only into the sign-in step, and no line Groundwork reads carries it',
          LOGIN[1] in page.sent[0] and all(LOGIN[1] not in js for js in page.sent[1:]) and not any(LOGIN[1] in l for l in lines))

    r, lines, _, clock = drive(['ok', 'code', 'code', 'ok', 'ok', 'ok'], downloads_seq=[set(), {'a.csv'}])
    check('s174 A6 a code request: it says so once, waits for the user to type it, then carries on',
          r == 'downloaded' and [baw.parse_fetch_line(l)['s'] for l in lines].count('waiting_code') == 1)
    r, lines, _, clock = drive(['ok'] + ['code'] * 400)
    check('s174 A6 no code in 5 minutes: it stops and says so', r == 'code_timeout' and clock.t <= baw.CODE_WAIT + baw.STEP_WAIT + 5)
    r, lines, _, clock = drive(['ok'] + ['missing'] * 100)
    check('s174 A6 the next control never appears: it stops after the wait - "the page changed" - nothing guessed',
          r == 'page_changed' and baw.parse_fetch_line(lines[-1]) == {'s': 'stopped', 'i': 1, 'why': 'page_changed'} and clock.t <= baw.STEP_WAIT + 2)
    r, lines, _, _ = drive(['ok', 'ambiguous'])
    check('s174 A6 two controls match: it stops rather than pick one', r == 'page_changed')
    r, lines, page, _ = drive(['ok', 'bot', 'ok', 'ok'])
    check('s174 A6 a bot check: automation stops for good, nothing after it is tried', r == 'bot_check' and len(page.sent) == 2)
    r, lines, _, _ = drive(['no_login'], login=None)
    check('s174 A4 no saved login: it stops and says so', r == 'no_login')
    r, lines, _, clock = drive(['ok', 'ok', 'ok', 'ok'], downloads_seq=[set()])
    check('s174 A6 no file in 2 minutes: it says so', r == 'no_download' and clock.t >= baw.DOWNLOAD_WAIT)

    words = [baw.fetch_words({'s': 'stopped', 'why': w}, STEPS) for w in ('bot_check', 'page_changed')]
    check('s174 A6 the user is told why in words; the window has closed (Rob: the agent always closes it)',
          "Groundwork stops there and closed the window" in words[0] and "Record the steps again" in words[1]
          and 'window is yours' not in ' '.join(words))
    check('s174 A2 Groundwork checks each line again: an unknown status or reason is refused',
          baw.parse_fetch_line('fetch {"s":"stopped","why":"retrying"}') is None
          and baw.parse_fetch_line('fetch {"s":"step","i":1,"password":"x"}') is None)
    check('s174 A4 the agent reads the vault the same way Settings saves it',
          baw.VAULT_SERVICE == bank_vault.SERVICE and "f'{VAULT_SERVICE} - {key}'" in (BASE / 'bank_agent_window.py').read_text(encoding='utf-8')
          and "f'{SERVICE} - {key}'" in (BASE / 'core/bank_vault.py').read_text(encoding='utf-8'))

    src = (BASE / 'bank_agent_window.py').read_text(encoding='utf-8')
    check('s174 A2 nothing starts a fetch except the route the user\'s click calls - no timer, no schedule, no retry loop',
          # two starts, both behind a click's route: the fetch (item 57/67) and the way to bill pay (item 68 B8 (b))
          srv.count('start_fetch(') == 2 and "@settings_bp.route('/bank-agent/fetch', methods=['POST'])" in srv
          and "@settings_bp.route('/bank-agent/pay-open', methods=['POST'])" in srv
          # (the never-press-a-payment guard names "schedule payment" as a button it refuses; that is not a schedule)
          and not re.search(r'(schedule|Timer\(|setInterval\([^)]*startBankFetch)',
                            (src + srv.split('bank_agent_fetch():')[1][:1500]).replace('(submit|confirm|schedule|', '('))
          and app.count('startBankFetch(') == 2)
    check('s174 A4 the agent writes the password to no file and no log', not re.search(r'(logging|logger|(?<![A-Za-z])open\()', src.split('# ── Stage 3')[1]))

    # A7 + the route's guards
    from core.database import Account, AppSetting, db_session
    made = []
    try:
        with db_session() as s:
            a = Account(name='s174 Checking', type='checking', is_active=True, portal_url='https://bank.example.com')
            s.add(a); s.commit(); made.append(a.id)
            ka = f'account:{a.id}'
        r = c.post('/api/settings/bank-agent/fetch', headers=HJ, data=json.dumps({'key': ka}))
        check('s174 A2 a fetch needs a saved login and saved steps first', r.status_code == 400)
        c.post('/api/settings/bank-agent/device', headers=HJ, data=json.dumps({'key': ka, 'on': True}))
        on = next(x for x in c.get('/api/settings/bank-logins', headers=H).get_json()['data']['accounts'] if x['key'] == ka)['remembered']
        import server
        d = server._bank_device_dir(ka, create=True)
        (d / 'cookie').write_text('x')
        c.post('/api/settings/bank-agent/device', headers=HJ, data=json.dumps({'key': ka, 'on': False}))
        off = next(x for x in c.get('/api/settings/bank-logins', headers=H).get_json()['data']['accounts'] if x['key'] == ka)['remembered']
        check('s174 A7 a remembered device only when ticked for that account; unticking forgets it (the folder is deleted)',
              on is True and off is False and not d.exists())
        check('s174 A7 with no tick the fetch runs private, as the viewer does', "device = str(_bank_device_dir(key, create=True)) if device_on else ''" in srv
              and "private_mode=True" in src.split('def fetch_child_main')[1])
    finally:
        with db_session() as s:
            s.query(AppSetting).filter(AppSetting.key.in_([f'bank_device:account:{i}' for i in made])).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made)).delete(synchronize_session=False)
            s.commit()

    # Rob's first real run: the code check ("Trust Device", its Submit) only appears when the bank asks
    OPT = [{'k': 'sign_in'}, {'k': 'choose', 'option': 'Trust Device', 'opt': True}, {'k': 'click', 'text': 'Submit', 'opt': True},
           {'k': 'click', 'text': 'Accounts'}, {'k': 'click', 'text': 'Download'}]
    page, clock, lines = _Page(['ok', 'missing', 'present', 'ok', 'ok']), _Clock(), []
    r = baw.Driver(page, OPT, LOGIN, lines.append, now=clock.now, sleep=clock.sleep).run()
    evs = [baw.parse_fetch_line(l) for l in lines]
    check('s174 A6 an optional step the bank did not show is skipped when the next real step is on the page',
          r == 'done' and [(e['s'], e.get('i')) for e in evs] == [('step', 0), ('skipped', 1), ('skipped', 2), ('step', 3), ('step', 4), ('done', None)]
          and LOGIN[1] not in page.sent[2] and ', true)' in page.sent[2])
    page, clock, lines = _Page(['ok'] + ['missing'] * 100), _Clock(), []
    r = baw.Driver(page, OPT, LOGIN, lines.append, now=clock.now, sleep=clock.sleep).run()
    check('s174 A6 when neither the optional step nor the next real one is there, it still stops - nothing guessed', r == 'page_changed')
    page, clock, lines = _Page(['missing'] * 100), _Clock(), []
    r = baw.Driver(page, [{'k': 'click', 'text': 'Accounts'}], LOGIN, lines.append, now=clock.now, sleep=clock.sleep).run()
    check('s174 A6 a step that is not optional is never skipped', r == 'page_changed')
    rec_src = src.split('def child_main(mode)')[1].split("# ── Groundwork's side")[0]
    check('s174 A7 the recording window uses the same remembered-device folder when ticked, so "Trust this device" carries into the fetch; private otherwise',
          'storage_path=device' in rec_src and 'private_mode=True' in rec_src
          and "start_recording(key, url, device_dir=device)" in srv
          and "device = str(_bank_device_dir(key_for_device, create=True)) if device_on else ''" in srv.split('def bank_agent_record():')[1][:1400]
          and "dkey = _device_key(session, key)" in srv.split('def bank_agent_record():')[1][:1400])
    import tempfile, os
    d = tempfile.mkdtemp(prefix='s174_dl_')
    first = baw.unique_path(d, r'C:\\Users\\x\\Downloads\\transactions-1.csv')
    open(first, 'w').close()
    second = baw.unique_path(d, 'transactions-1.csv')
    check('s174 A8 a download lands in the Downloads folder under the bank\'s own name; a taken name gets " (2)", never an overwrite',
          os.path.basename(first) == 'transactions-1.csv' and os.path.dirname(first) == d
          and os.path.basename(second) == 'transactions-1 (2).csv')
    check('s174 A8 both agent windows save downloads without the Save As dialog the agent cannot see; the plain viewer keeps it',
          src.count('    save_downloads_to_downloads_folder(platform_key)\n') == 2
          and 'save_downloads_to_downloads_folder' not in (BASE / 'bank_window.py').read_text(encoding='utf-8'))
    if os.name == 'nt':
        from webview.platforms import edgechromium
        before = edgechromium.EdgeChrome.on_download_starting
        try:
            ok_patch = baw.save_downloads_to_downloads_folder('win32')

            class _Args:
                ResultFilePath = r'C:\\anything\\stmt.csv'
                Cancel = False
                Handled = False
            from webview import settings as ws
            old = ws.get('ALLOW_DOWNLOADS')
            ws['ALLOW_DOWNLOADS'] = True
            a = _Args()
            edgechromium.EdgeChrome.on_download_starting(None, None, a)
            ws['ALLOW_DOWNLOADS'] = old
            import bank_window as bw
            check('s174 A8 on Windows the handler saves to the Downloads folder with no dialog and no cancel',
                  ok_patch and a.Cancel is False and a.Handled is True
                  and os.path.dirname(a.ResultFilePath) == str(bw.downloads_dir()) and a.ResultFilePath.endswith('stmt.csv'))
        finally:
            edgechromium.EdgeChrome.on_download_starting = before
    # Rob's third real run: recorded while already signed in (no sign-in step); the fetch met the login page
    STEPS3 = [{'k': 'click', 'text': 'Checking'}, {'k': 'click', 'text': 'Download'}]
    page, clock, lines = _Page(['login:sign_in', 'ok', 'ok', 'ok']), _Clock(), []
    r = baw.Driver(page, STEPS3, LOGIN, lines.append, now=clock.now, sleep=clock.sleep).run()
    evs = [baw.parse_fetch_line(l)['s'] for l in lines]
    check('s174 A6 the login form appears with no sign-in recorded: it signs in from the vault, then carries on',
          r == 'done' and evs == ['signed_in', 'step', 'step', 'done'] and LOGIN[1] in page.sent[1] and LOGIN[1] not in page.sent[0])
    class _StuckLogin(_Page):
        def evaluate_js(self, js):                  # always the login page; a sign-in attempt "works"
            if 'window.__gwDo ? window.__gwDo(' not in js:
                return None
            self.sent.append(js)
            return 'ok' if '"k": "sign_in"' in js else 'login:sign_in'
    page, clock, lines = _StuckLogin([]), _Clock(), []
    r = baw.Driver(page, STEPS3, LOGIN, lines.append, now=clock.now, sleep=clock.sleep).run()
    check('s174 A6 still on the login page after two sign-ins: it stops and says so - no loop', r == 'sign_in_failed' and sum(LOGIN[1] in js for js in page.sent) == 2)
    page, clock, lines = _Page(['login:sign_in']), _Clock(), []
    r = baw.Driver(page, STEPS3, None, lines.append, now=clock.now, sleep=clock.sleep).run()
    check('s174 A4 a login form with no saved login: it stops and says so', r == 'no_login')
    check('s174 A6 a "trust this device" / "verify your identity" page waits for the user like a code',
          'trust (this )?(device|computer|browser)|remember (this )?(device|computer|browser)|verify (your )?identity' in baw.DO_SCRIPT.split('function codeAsked')[1].split('function loginForm')[0])
    page, clock, lines = _Page(['code', 'code', 'ok', 'ok']), _Clock(), []
    baw.Driver(page, [{'k': 'click', 'text': 'Download'}, {'k': 'click', 'text': 'CSV'}], LOGIN, lines.append, now=clock.now, sleep=clock.sleep).run()
    bars = page.bars
    check('s174 A6 the fetch window says what is happening on the page: fetching, and when the bank asks the user something',
          any('Your bank is asking you something' in b for b in bars) and any('Groundwork is fetching your download' in b for b in bars)
          and not any(LOGIN[1] in b for b in bars))

    # Rob's fourth real run: Superior CU's sign-in sits in an embedded frame from another address
    opened = []
    page, clock, lines = _Page(['frame:https://online.example.com/auth/signin', 'login:sign_in', 'ok', 'ok', 'ok']), _Clock(), []
    r = baw.Driver(page, STEPS3, LOGIN, lines.append, now=clock.now, sleep=clock.sleep, open_url=opened.append).run()
    check('s174 A6 a sign-in in an embedded frame: the window opens the frame\'s address as the page, signs in there, then carries on',
          r == 'done' and opened == ['https://online.example.com/auth/signin'])
    opened = []
    page, clock, lines = _Page(['frame:https://a.example.com/login'] * 3 + ['missing'] * 400), _Clock(), []
    r = baw.Driver(page, STEPS3, LOGIN, lines.append, now=clock.now, sleep=clock.sleep, open_url=opened.append).run()
    check('s174 A6 the frame is opened once per step at most - no loop', len(opened) == 1 and r == 'page_changed')
    check('s174 A6 only an https frame address is opened, and only by the window\'s own https check',
          "u.protocol === 'https:'" in baw.DO_SCRIPT and 'if not bw.portal_url_problem(u):' in (BASE / 'bank_agent_window.py').read_text(encoding='utf-8'))
    ds = baw.DO_SCRIPT
    check('s174 A6 signing in presses the control named like a sign-in (Sign in, Log in, Continue...), not the first button in the form (Rob\'s fifth run)',
          ds.count('submitFor(') == 3 and 'sign ?in|log ?in|login|log on' in ds and 'continue|next|submit' in ds
          and "querySelector('button[type=submit],input[type=submit],button:not([type])')" not in ds)
    check('s174 A6 every press is a full mouse press for a styled element (Superior CU\'s online banking ignores a bare .click() on its div "links") - clicks, choices and sign-in alike',
          ds.count('.click()') == 1 and 'el.click(); return; }' in ds and ds.count('press(') == 4
          and "new PointerEvent('pointerdown'" in ds and "new MouseEvent('click', up)" in ds)
    check('s174 A6 a sign-in / log-in name wins over Continue / Next, and a label like tethered_login_sign_in counts',
          'near(signIn) || near(onward)' in ds and "replace(/_/g, ' ')" in ds)
    # Rob's seventh run: a recorded 'Click "Sign In"' (no form on the page); the fetch signed in, then hunted for it
    STEPS7 = [{'k': 'click', 'text': 'Sign In'}, {'k': 'click', 'text': 'Checking'}]
    page, clock, lines = _Page(['login:sign_in', 'ok', 'login:sign_in', 'login:sign_in', 'missing', 'ok']), _Clock(), []
    r = baw.Driver(page, STEPS7, LOGIN, lines.append, now=clock.now, sleep=clock.sleep).run()
    evs = [baw.parse_fetch_line(l)['s'] for l in lines]
    check('s174 A6 a recorded "Sign In" click counts as done once signed in; the old login page showing for a moment is waited out, not signed into again',
          r == 'done' and evs == ['signed_in', 'step', 'step', 'done'] and sum(LOGIN[1] in js for js in page.sent) == 1)
    check('s174 A6 a sign-in step is known by kind or by name', baw.is_sign_in_step({'k': 'click', 'text': 'Log In'})
          and baw.is_sign_in_step({'k': 'sign_in'}) and not baw.is_sign_in_step({'k': 'click', 'text': 'Trouble Signing In?'})
          and not baw.is_sign_in_step({'k': 'click', 'text': 'Checking'}))
    check('s174 A6 each control is scrolled into view before it is pressed',
          baw.DO_SCRIPT.index('scrollIntoView') < baw.DO_SCRIPT.index("new PointerEvent('pointerdown'"))
    check('s173 A5 a click on a sign-in-named control with a password box showing is recorded as the sign-in (a page with no form)',
          "note({k: 'sign_in', opt: checkPage()});" in baw.RECORD_SCRIPT)
    fsrc = (BASE / 'bank_agent_window.py').read_text(encoding='utf-8')
    drive = fsrc.split('def _drive():')[1].split('threading.Thread(target=_drive')[0]
    check('s174 A6 the fetch window always closes itself when the fetch ends, whatever the outcome (Rob: "always close out the web browser window")',
          'outcome = driver.run()' in drive and 'window.destroy()' in drive and 'except Exception:' in drive
          and drive.index('outcome = driver.run()') < drive.index('window.destroy()') and 'if not driver.cancelled' in drive)
    # Amendment A13: the bank's pop-ups during a fetch
    ds = baw.DO_SCRIPT
    POP = [{'k': 'click', 'text': 'Close', 'opt': True, 'pop': True}, {'k': 'click', 'text': 'Download'}]
    page, clock, lines = _Page(['ok', 'ok']), _Clock(), []
    r = baw.Driver(page, POP, LOGIN, lines.append, now=clock.now, sleep=clock.sleep).run()
    check('s174 A13.1 the pop-up is there: the agent closes it, says so on the bar, and carries on',
          r == 'done' and any('Closed your bank' in b and 'pop-up' in b for b in page.bars))
    page, clock, lines = _Page(['missing', 'present', 'ok']), _Clock(), []
    r = baw.Driver(page, POP, LOGIN, lines.append, now=clock.now, sleep=clock.sleep).run()
    check('s174 A13.1 no pop-up this time: the step is skipped and the run carries on',
          r == 'done' and [baw.parse_fetch_line(l)['s'] for l in lines][:1] == ['skipped'])
    check('s174 A13.1 a pop-up step is pressed only inside a pop-up, never a same-named control on the page beneath',
          'var scope = step.pop ? popups() : [document];' in ds)
    check('s174 A13.2 a pop-up asking to agree to terms, an agreement or consent stops and waits for the person, as a code does',
          "if (asksAgreement()) return 'code';" in ds and ds.index('if (asksAgreement())') < ds.index("if (step.k === 'sign_in_user')")
          and 'terms|agreement|consent|i accept|i agree' in ds and 'something to agree to' in baw.fetch_words({'s': 'waiting_code'}, []))
    check('s174 A13.3 the agent never ticks a box in a pop-up on its own: it only presses recorded steps, which never include a setting',
          ds.count('.checked = true') == 0 and ds.count('setAttribute(\x27aria-checked') == 0)

