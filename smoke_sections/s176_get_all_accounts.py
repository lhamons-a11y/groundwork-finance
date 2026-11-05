"""Item 67: Get all my accounts, with one press (gw 2.0/GET_ALL_ACCOUNTS.md G1-G9; RULED 2026-10-09, Rob: "i accept
all points"; built on "Item 57 passed. Build 67").

    G1  one press visits each account with saved steps, ONE AT A TIME, in order; the user's Stop or a bank's bot check
        ends the batch; any other stop ends that account's run only
    G2  a header button, shown only when an account has saved steps; the same button on the dashboard line
    G3  the dashboard line reads the record only (statement_fetched); the user's number of days, 0 = off; no timer
    G4  one panel, a line per account in words, Stop, and it stays until Close
    G5  a code page brings that bank's window forward; the code is typed there, never through Groundwork
    G6  each file still goes through the review; it starts on the account it was fetched for, matched by its hash;
        "File 1 of 3"
    G8  each run records its own statement_fetched, plus the batch id
"""
import json
import re
import threading


def _only_clicks(app, html):
    """Every call of startFetchAll is its definition, an onclick, inside openLedgerBank (the Bank button's click), or
    askFetch - the person typing "get my accounts" in the Ask box (Rob 2026-10-19, item 102 A7), the same as pressing it."""
    ledger = app.split('async function openLedgerBank(')[1].split('\nfunction ')[0]
    typed = app.split('function askFetch(')[1].split('\nfunction ')[0]
    rest = app.replace(ledger, '').replace(typed, '')
    lines = [ln for ln in (rest + html).splitlines() if 'startFetchAll(' in ln]
    return all('async function startFetchAll(' in ln or 'onclick=' in ln for ln in lines)



def _Driver(window, *a, **k):
    """The Driver on the bank's own site: the login guard has its own section (s286)."""
    import bank_agent_window as baw
    window.get_current_url = lambda: 'https://www.superiorcu.com/'
    return baw.Driver(window, *a, home='https://www.superiorcu.com/', **k)


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    import bank_agent_window as baw
    import server
    from core.database import Account, AppSetting, HistorianEntry, db_session

    # ── G1: the batch, with a stand-in launch ──
    def batch(outcomes, stop_after=None):
        """outcomes: per key, the events its run ends with (or a string: the reason it didn't open)."""
        active, most, order = [0], [0], []
        b = {'id': 'b1', 'stop': None, 'done': False, 'current': None,
             'items': [{'key': k, 'name': k, 'state': 'waiting', 'why': None, 'file': None} for k in outcomes]}

        def launch(key, bid, on_end):
            order.append(key)
            o = outcomes[key]
            if isinstance(o, str):
                return o
            active[0] += 1
            most[0] = max(most[0], active[0])

            def finish():
                active[0] -= 1
                if stop_after == key:
                    b['stop'] = 'user'
                on_end(key, o)
            threading.Timer(0.01, finish).start()
            return 'opened'
        baw.run_batch(b, launch, poll=0.005)
        return b, order, most[0]

    dl = lambda f: [{'s': 'step', 'i': 0}, {'s': 'downloaded', 'file': f}]          # noqa: E731
    b, order, most = batch({'account:1': dl('a.csv'), 'account:2': [{'s': 'stopped', 'i': 1, 'why': 'page_changed'}],
                            'account:3': dl('c.csv')})
    check('s176 G1 one at a time, in order; a stop on one account moves on to the next',
          order == ['account:1', 'account:2', 'account:3'] and most == 1 and b['done']
          and [i['state'] for i in b['items']] == ['downloaded', 'stopped', 'downloaded']
          and b['items'][1]['why'] == 'page_changed' and b['items'][2]['file'] == 'c.csv')
    b, order, _ = batch({'account:1': [{'s': 'stopped', 'why': 'bot_check'}], 'account:2': dl('b.csv'), 'account:3': dl('c.csv')})
    check('s176 G1 a bank\'s bot check ends the batch at once: the rest are skipped, not visited',
          order == ['account:1'] and b['stop'] == 'bot_check' and [i['state'] for i in b['items']] == ['stopped', 'skipped', 'skipped'])
    b, order, _ = batch({'account:1': dl('a.csv'), 'account:2': dl('b.csv'), 'account:3': dl('c.csv')}, stop_after='account:1')
    check('s176 G1 the user\'s Stop ends the batch: what is left is skipped',
          order == ['account:1'] and [i['state'] for i in b['items']] == ['downloaded', 'skipped', 'skipped'])
    b, order, _ = batch({'account:1': 'no_login', 'account:2': dl('b.csv')})
    check('s176 G1 an account that can\'t start (no saved login) says why, and the batch moves on',
          [i['state'] for i in b['items']] == ['stopped', 'downloaded'] and b['items'][0]['why'] == 'no_login'
          and baw.batch_words(b['items'][0]) == 'Stopped: no saved login')
    b, _, _ = batch({'account:1': []})
    check('s176 G1 a run that ends with no outcome (the window closed) reads as stopped', b['items'][0]['state'] == 'stopped'
          and b['items'][0]['why'] == 'cancelled')
    baw.reset_batch_for_test()
    gate = threading.Event()
    held = lambda key, bid, on_end: (threading.Thread(target=lambda: (gate.wait(5), on_end(key, dl('x.csv'))), daemon=True).start(), 'opened')[1]   # noqa: E731
    first = baw.start_batch([{'key': 'account:1', 'name': 'One'}], held, poll=0.005)
    second = baw.start_batch([{'key': 'account:1', 'name': 'One'}], held, poll=0.005)
    gate.set()
    check('s176 G1 one batch at a time: a second press while one runs does not start another',
          first == 'started' and second == 'already_running' and baw.start_batch([], held) == 'nothing')
    for _ in range(200):
        st = baw.batch_state()
        if st and st['done']:
            break
        threading.Event().wait(0.01)
    check('s176 G4 the panel\'s state: a line per account, in words', st and st['done'] and st['items'][0]['words'] == 'Downloaded x.csv')
    check('s176 G4 the words for a code page say the bank\'s window is in front',
          'window is in front' in baw.batch_words({'state': 'running'}, 'waiting_code'))
    baw.reset_batch_for_test()

    # ── G5: a code page brings the window forward; the code itself never passes through Groundwork ──
    from smoke_sections import s174_bank_fetch as s174   # noqa: F401  (its stand-in page)
    fronts = []
    page, clock, lines = s174._Page(['code', 'code', 'ok']), s174._Clock(), []
    _Driver(page, [{'k': 'click', 'text': 'Download'}], ('u', 'p'), lines.append, now=clock.now, sleep=clock.sleep,
               to_front=lambda: fronts.append(1)).run()
    check('s176 G5 a code page brings the bank\'s window to the front, once', fronts == [1])
    srv = (BASE / 'server.py').read_text(encoding='utf-8')
    app = ctx.app_src
    check('s176 G5 no route takes a code, and the panel has no box to type one in',
          not re.search(r"route\('/bank-agent/[^']*code", srv) and '<input' not in app.split('function fetchAllPanelHtml(')[1].split('function _showFetchAllPanel(')[0])

    # ── G2/G3: the header button, the dashboard line, the reminder setting ──
    html = ctx.html_src
    check('s176 G2 the header button is hidden until the record shows an account with saved steps',
          'id="gwFetchAllBtn"' in html and re.search(r'id="gwFetchAllBtn"[^>]*style="display:none"', html)
          and "btn.style.display = (d && d.accounts.length) ? '' : 'none'" in app)
    check('s176 G3 nothing starts a batch on its own: startFetchAll is only ever a click',
          _only_clicks(app, html) and not re.search(r'(setInterval|setTimeout)\([^)]*(startFetchAll|openLedgerBank)', app)
          and 'onclick="openLedgerBank(event)"' in html and app.count('openLedgerBank(') == 1)
    # The real vault is never touched: an empty stand-in replaces it, so no account here has a login and no window
    # can open (an id in the gate's database can match a real login saved on this computer)
    import keyring
    from keyring.backend import KeyringBackend

    class _Empty(KeyringBackend):
        priority = 1

        def get_password(self, service, username):
            return None

        def set_password(self, service, username, password):
            raise keyring.errors.PasswordSetError('the gate saves no login')

        def delete_password(self, service, username):
            raise keyring.errors.PasswordDeleteError('none')
    real_kr = keyring.get_keyring()
    keyring.set_keyring(_Empty())
    launched = []
    real_start = baw.start_fetch
    baw.start_fetch = lambda *a, **k: (launched.append(a[0]), 'refused_url')[1]     # belt and braces: never a window
    made = []
    try:
        with db_session() as s:
            a = Account(name='s176 Checking', type='checking', is_active=True, portal_url='https://bank.example.com')
            s.add(a); s.commit(); made.append(a.id)
            key = f'account:{a.id}'
            s.add(AppSetting(key=f'bank_recipe:{key}', value=json.dumps({'steps': [{'k': 'click', 'text': 'Download'}]})))
            s.commit()
        d = c.get('/api/settings/bank-agent/last-fetched', headers=H).get_json()['data']
        mine = [r for r in d['accounts'] if r['key'] == key]
        check('s176 G3 an account with saved steps and no fetch yet: "not fetched yet", and the line shows (7 days by default)',
              mine and mine[0]['days'] is None and d['show'] and d['remind_days'] == 7)
        folder = ctx.TMP / 's176_dl'
        folder.mkdir(exist_ok=True)
        (folder / 'one.csv').write_text('Date,Amount\n2026-10-01,1.00\n', encoding='utf-8')
        server._record_fetch(key, 'https://bank.example.com/', ['Click “Download”'], '2026-10-09T10:00:00',
                             [{'s': 'downloaded', 'file': 'one.csv', 'at': '2026-10-09T10:01:00'}], folder=folder, batch='bat176')
        (folder / 'two.csv').write_text('Date,Amount\n2026-10-02,2.00\n', encoding='utf-8')
        server._record_fetch(key, 'https://bank.example.com/', ['Click “Download”'], '2026-10-09T10:02:00',
                             [{'s': 'downloaded', 'file': 'two.csv', 'at': '2026-10-09T10:03:00'}], folder=folder, batch='bat176')
        with db_session() as s:
            evs = s.query(HistorianEntry).filter(HistorianEntry.event_category == 'statement_fetched').order_by(HistorianEntry.id.desc()).limit(2).all()
            ctxs = [json.loads(e.context_json) for e in evs]
        check('s176 G8 each run records its own statement_fetched, with the batch id', all(x['batch'] == 'bat176' for x in ctxs))
        r = c.post('/api/settings/bank-agent/remind-days', headers=HJ, data=json.dumps({'days': 0})).get_json()['data']
        d0 = c.get('/api/settings/bank-agent/last-fetched', headers=H).get_json()['data']
        c.post('/api/settings/bank-agent/remind-days', headers=HJ, data=json.dumps({'days': 7}))
        d7 = c.get('/api/settings/bank-agent/last-fetched', headers=H).get_json()['data']
        mine = [x for x in d7['accounts'] if x['key'] == key]
        check('s176 G3 0 days turns the line off; the last download comes from the record',
              r['remind_days'] == 0 and d0['show'] is False and mine and mine[0]['last'] == '2026-10-09T10:03:00')
        check('s176 G3 the line states a fact, no verdict words', 'Last fetched from your bank:' in app
              and not re.search(r'(overdue|behind|you should|don\x27t forget)', app.split('function fetchAllLineHtml(')[1].split('async function setFetchRemindDays(')[0], re.I))

        # ── G6: the review starts on the account the file was fetched for, matched by its hash ──
        import hashlib
        sha = hashlib.sha256((folder / 'two.csv').read_bytes()).hexdigest()
        server._auto_import_queue.append({'filename': 'two.csv', 'content': 'x', 'path': str(folder / 'two.csv'), 'sha256': sha})
        item = c.get('/api/auto-import/pending', headers=H).get_json()['data']
        ff = item.get('fetched_for') or {}
        check('s176 G6 a fetched file is offered on its account, by its hash; "2 of 2" from its batch',
              ff.get('key') == key and ff.get('name') == 's176 Checking' and ff.get('pos') == 2 and ff.get('of') == 2)
        server._auto_import_queue.append({'filename': 'mine.csv', 'content': 'x', 'path': 'x', 'sha256': '0' * 64})
        item = c.get('/api/auto-import/pending', headers=H).get_json()['data']
        check('s176 G6 a file the user downloaded themselves carries no account - nothing is guessed', 'fetched_for' not in item)
        acc = app.split('async function _acceptAutoImport(')[1].split('\nfunction ')[0]
        check('s176 G6 the account is pre-chosen only when it is one of the review\'s own choices; the review still runs',
              '[...sel.options].some(o => o.value === ff.name)' in acc and acc.index('sel.value = ff.name') < acc.rindex('handleImportFile(')
              and 'showImportModal()' in acc)

        # ── G1: the press itself ──
        r = c.post('/api/settings/bank-agent/fetch-all', headers=HJ, data='{}')
        check('s176 G1 the press with accounts to visit starts one batch (no login here, so each stops and says so)',
              r.status_code == 200 and r.get_json()['data']['result'] in ('started', 'already_running'))
        for _ in range(300):
            st = c.get('/api/settings/bank-agent/fetch-all', headers=H).get_json()['data']
            if st and st['done']:
                break
            threading.Event().wait(0.01)
        mine = [i for i in st['items'] if i['key'] == key]
        baw.reset_batch_for_test()
        r1 = c.post('/api/settings/bank-agent/fetch-all', headers=HJ, data=json.dumps({'keys': ['account:999999']}))
        check('s176 Ledger: a press for one account visits that account only (no saved steps there: nothing to do)',
              r1.status_code == 400)
        pb = app.split('function _portalButtonsHTML(')[1].split('async function _openBankPortal(')[0]
        check('s176 Ledger: an account with saved steps gets "Get my transactions" from its Bank button (Rob); the browser button stays',
              "_fetchKeys.has(fkey)" in pb and "startFetchAll(['${fkey}'])" in pb and "_openBankPortal('${kind}', ${id}, 'browser')" in pb)
        lb = app.split('async function openLedgerBank(')[1].split('\nfunction ')[0]
        check('s176 Ledger: the Bank button fetches for an account with saved steps - filtered to it, or from its menu row',
              "if (_fetchKeys.has(fk(match))) startFetchAll([fk(match)]);" in lb and "startFetchAll(['${fk(x)}'])" in lb)
        check('s176 G1 an account with no saved login stops with that reason; nothing opened',
              mine and mine[0]['why'] == 'no_login' and key not in launched)
    finally:
        keyring.set_keyring(real_kr)
        baw.start_fetch = real_start
        baw.reset_batch_for_test()
        with db_session() as s:
            s.query(AppSetting).filter(AppSetting.key.in_([f'bank_recipe:account:{i}' for i in made] + ['bank_fetch_remind_days'])).delete(synchronize_session=False)
            s.query(HistorianEntry).filter(HistorianEntry.event_category == 'statement_fetched',
                                           HistorianEntry.context_json.contains('"batch": "bat176"')).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made)).delete(synchronize_session=False)
            s.commit()
