"""Item 68 stage 3: take the person to their bank's bill pay, and stop (gw 2.0/BILLS_AND_PAYING.md B8 (b), B9;
RULED 2026-10-10 - TM1 stands).

    B8 (b)  "Take me to pay this" follows the way the person recorded once, signed in with the bank account's login,
            and stops at the payment screen; the window stays with the bill's facts on its bar
    B9      no agent step ever presses a control named like Pay / Submit payment / Send / Transfer / Confirm payment -
            never saved as a step, refused by the page script, and a run that reaches one stops
"""
import json
import subprocess


PAYS = ['Pay', 'Pay now', 'PAY BILL', 'Pay this bill', 'Make a payment', 'Make Payment', 'Submit payment', 'Confirm payment',
        'Schedule payment', 'Authorize payment', 'Send', 'Send money', 'Transfer', 'Transfer funds', 'Pay $142.37']
NAV = ['Bill Pay', 'Payments', 'Pay bills menu', 'AEP Ohio', 'Submit', 'Continue', 'Payment history', 'Transfers',
       'Download', 'Spreadsheet (CSV)']



def _Driver(window, *a, **k):
    """The Driver on the bank's own site: the login guard has its own section (s287)."""
    import bank_agent_window as baw
    window.get_current_url = lambda: 'https://www.superiorcu.com/'
    return baw.Driver(window, *a, home='https://www.superiorcu.com/', **k)


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    import bank_agent_window as baw
    import server
    from core.database import Account, AppSetting, BillReading, BudgetItem, HistorianEntry, db_session
    from smoke_sections import s174_bank_fetch as s174
    from datetime import date, datetime, timedelta

    # ── B9: never a step ──
    dropped = [t for t in PAYS if baw.clean_step({'k': 'click', 'text': t}) is not None]
    kept = [t for t in NAV if baw.clean_step({'k': 'click', 'text': t}) is None]
    check(f's179 B9 a payment\'s own button is never saved as a step; navigation is (wrongly kept: {dropped}; wrongly dropped: {kept})',
          not dropped and not kept)

    # ── B9: never pressed - the page script's own guard, run in Node against the same names ──
    ds = baw.DO_SCRIPT
    fns = ds[ds.index('  function nameOf(el)'):ds.index('  function same(')] + ds[ds.index('  function paysMoney(el)'):ds.index('  function press(el)')]
    js = fns + """
var el = function (t) { return {innerText: t, textContent: t, tagName: 'BUTTON', type: 'button', getAttribute: function () { return null; }}; };
console.log(JSON.stringify({pays: %s.filter(function (t) { return !paysMoney(el(t)); }), nav: %s.filter(function (t) { return paysMoney(el(t)); })}));
""" % (json.dumps(PAYS), json.dumps(NAV))
    try:
        out = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30).stdout or '{}')
    except Exception as e:     # noqa: BLE001
        out = {'error': str(e)}
    check(f's179 B9 the page script refuses to press every payment button and presses navigation (missed: {out.get("pays")}; blocked: {out.get("nav")})',
          out.get('pays') == [] and out.get('nav') == [])
    check('s179 B9 the guard is the first thing press() does, and a click step on a payment button stops the run before pressing',
          "function press(el) {\n    if (paysMoney(el)) return false;" in ds
          and "if (paysMoney(els[0])) return 'would_pay'; if (probe) return 'present'; press(els[0]);" in ds)
    page, clock, lines = s174._Page(['ok', 'would_pay']), s174._Clock(), []
    r = _Driver(page, [{'k': 'click', 'text': 'Bill Pay'}, {'k': 'click', 'text': 'AEP Ohio'}], ('u', 'p'), lines.append,
                   now=clock.now, sleep=clock.sleep).run()
    check('s179 B9 a run that reaches a payment button stops and says why', r == 'would_pay'
          and baw.parse_fetch_line(lines[-1]) == {'s': 'stopped', 'i': 1, 'why': 'would_pay'}
          and 'Groundwork never pays' in baw.fetch_words({'s': 'stopped', 'why': 'would_pay'}, []))

    # ── B8 (b): the window for a pay run ──
    src = (BASE / 'bank_agent_window.py').read_text(encoding='utf-8')
    child = src.split('def fetch_child_main')[1].split('\ndef ')[0]
    check('s179 B8 a pay run signs in with the bank account\'s own login (account: or card: only), expects no file, and holds the window at the payment',
          "login_key = str(extra.get('login_key') or '') if key.startswith('pay:') else key" in child
          and "if key.startswith('pay:') and not login_key.startswith(('account:', 'card:')):" in child
          and "_read_login(login_key)" in child and "downloads=None if key.startswith(('bill:', 'pay:'))" in child
          and child.split('def _drive():')[1].index("driver._bar(hold, 'ask')") < child.split('def _drive():')[1].index('window.destroy()')
          and "if hold and outcome == 'done' and not driver.cancelled:" in child)
    check('s179 B8 the recording words for the way to pay: stop before an amount; Groundwork never pays',
          'Stop before you enter an amount; Groundwork never pays.' in baw.RECORD_SCRIPT and "'window.__gwPay = true;' if is_pay" in src)

    # ── B8 (b): the route ──
    import keyring
    from keyring.backend import KeyringBackend

    class _Mem(KeyringBackend):
        priority = 1
        store = {}

        def get_password(self, s, u):
            return self.store.get((s, u))

        def set_password(self, s, u, p):
            self.store[(s, u)] = p

        def delete_password(self, s, u):
            self.store.pop((s, u), None)
    real_kr, mem = keyring.get_keyring(), _Mem()
    keyring.set_keyring(mem)
    started, real_start = [], baw.start_fetch
    baw.start_fetch = lambda *a, **k: (started.append((a, k)), 'opened')[1]
    made = {'a': [], 'b': [], 'r': []}
    try:
        with db_session() as s:
            a = Account(name='s179 Checking', type='checking', is_active=True, portal_url='https://bank.example.com/login')
            b = BudgetItem(name='s179 AEP', category='Electric', amount=120.0, type='expense', is_active=True)
            s.add_all([a, b]); s.commit()
            made['a'].append(a.id); made['b'].append(b.id)
            rd = BillReading(budget_item_id=b.id, amount=142.37, due_date=date.today() + timedelta(days=9), read_at=datetime.now(),
                             source_host='aep.example.com')
            s.add(rd); s.commit(); made['r'].append(rd.id)
            aid, bid = a.id, b.id
        post = lambda: c.post('/api/settings/bank-agent/pay-open', headers=HJ, data=json.dumps({'id': bid}))   # noqa: E731
        r1 = post()
        c.post('/api/settings/bank-agent/bill-from', headers=HJ, data=json.dumps({'id': bid, 'account_id': aid}))
        r2 = post()
        sv = c.post('/api/settings/bank-agent/recipe', headers=HJ, data=json.dumps({'key': f'pay:{bid}', 'steps': [
            {'k': 'click', 'text': 'Bill Pay'}, {'k': 'click', 'text': 'AEP Ohio'}, {'k': 'click', 'text': 'Pay now'}]})).get_json()['data']
        r3 = post()
        from core import bank_vault
        bank_vault.save_login(f'account:{aid}', 'rob', 's179-secret-pass')
        r4 = post()
        check('s179 B8 the way to pay needs: the account it is paid from, the recorded way, and that bank\'s saved login - in that order',
              r1.status_code == 400 and r2.status_code == 400 and r3.status_code == 400 and r4.status_code == 200
              and 'paid from' in r1.get_json().get('error', r1.get_data(as_text=True)).lower())
        check('s179 B9 a recorded "Pay now" never reaches the saved way', [x['text'] for x in sv['steps']] == ['Bill Pay', 'AEP Ohio'])
        (args, kw) = started[-1] if started else ((), {})
        hold = (kw.get('extra') or {}).get('hold', '')
        check('s179 B8 the pay run: its own key, the bank\'s link, the bank account\'s login key, and the bill\'s facts on the bar - never the password',
              args[0] == f'pay:{bid}' and args[1] == 'https://bank.example.com/login'
              and kw['extra']['login_key'] == f'account:{aid}' and '$142.37' in hold and 'Enter the amount and press Pay yourself' in hold
              and 'Groundwork never pays' in hold and 's179-secret-pass' not in json.dumps(kw['extra']) and 'rob' not in json.dumps(kw['extra']))
        with db_session() as s:
            dev = server._device_key(s, f'pay:{bid}')
        check('s179 B8 the pay window uses the bank account\'s remembered device, so its "trust this device" carries over',
              dev == f'account:{aid}')
        k = c.get('/api/settings/bank-agent/bill-checks', headers=H).get_json()['data']
        check('s179 B8 the bills card knows the way to pay is recorded', next(x for x in k['bills'] if x['id'] == bid)['pay_steps'] is True)
    finally:
        baw.start_fetch = real_start
        keyring.set_keyring(real_kr)
        with db_session() as s:
            s.query(AppSetting).filter(AppSetting.key.in_([f'bill_from:{i}' for i in made['b']] + [f'bank_recipe:pay:{i}' for i in made['b']])).delete(synchronize_session=False)
            s.query(BillReading).filter(BillReading.id.in_(made['r'])).delete(synchronize_session=False)
            s.query(BudgetItem).filter(BudgetItem.id.in_(made['b'])).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made['a'])).delete(synchronize_session=False)
            s.commit()
    app = ctx.app_src
    check('s179 B8 the button says what happens: Groundwork opens the payment screen and stops; you enter the amount and press Pay',
          'Take me to pay this' in app and "Groundwork opens your bank's payment screen and stops there. You enter the amount and press Pay." in app)
