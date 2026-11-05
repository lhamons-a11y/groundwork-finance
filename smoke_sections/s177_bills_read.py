"""Item 68 stage 1: bills read from their own website (gw 2.0/BILLS_AND_PAYING.md B1-B5; RULED 2026-10-10, Rob:
"approve B1-B9 as recommended"; built on "build item 68").

    B1  a bill's own website (https only) and its login in the vault as bill:<id>
    B2  show me once marks WHERE the amount due and the due date are - the label beside each, digits masked, never
        the figure
    B3  a run reads both figures; Groundwork parses them, keeps them waiting, and uses nothing until the person says
        yes; a confirmed reading sits beside the budget line, and "use the bill's amount for this month" is derived
        when the month is read - the saved amount is never written
    B4  bills come after the banks in Get my accounts
    B5  never from email: nothing in Groundwork reads mail
"""
import json
import re
from datetime import date, timedelta



def _Driver(window, *a, **k):
    """The Driver on the bank's own site: the login guard has its own section (s286)."""
    import bank_agent_window as baw
    window.get_current_url = lambda: 'https://www.superiorcu.com/'
    return baw.Driver(window, *a, home='https://www.superiorcu.com/', **k)


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    import bank_agent_window as baw
    import server
    from core import bank_vault
    from core.database import Account, AppSetting, BillReading, BudgetItem, HistorianEntry, db_session
    from smoke_sections import s174_bank_fetch as s174

    # ── B2: what a marked figure leaves behind ──
    st = baw.clean_step({'k': 'read', 'what': 'amount', 'field': 'Amount Due by 10/24', 'text': '$142.37', 'value': '142.37'})
    check('s177 B2 a marked figure is kept as WHERE it is - the label beside it, digits masked - never the figure',
          st == {'k': 'read', 'what': 'amount', 'field': 'Amount Due by ••••/••••'} and '142' not in json.dumps(st)
          and baw.clean_step({'k': 'read', 'what': 'amount', 'field': 'Total due $142.37'}) == {'k': 'read', 'what': 'amount', 'field': 'Total due ••••'})
    check('s177 B2 an unknown figure or a mark with no label is refused',
          baw.clean_step({'k': 'read', 'what': 'balance', 'field': 'Balance'}) is None
          and baw.clean_step({'k': 'read', 'what': 'due', 'field': ''}) is None)
    check('s177 B2 the steps read as words',
          baw.step_words({'k': 'read', 'what': 'amount', 'field': 'Amount Due'}) == 'Read the amount due (beside “Amount Due”)'
          and baw.step_words({'k': 'read', 'what': 'due', 'field': 'Due Date'}) == 'Read the due date (beside “Due Date”)')
    rs = baw.RECORD_SCRIPT
    check('s177 B2 the marking buttons appear only on a bill\'s site, live in their own shadow root, and the mark notes the label alone',
          'if (window.__gwBill) markPanel(' in rs and "host.id = '__gwMarkHost'" in rs and "attachShadow" in rs
          and "note({k: 'read', what: what, field: lab});" in rs and "if (e.target && e.target.id === '__gwMarkHost') return;" in rs
          and rs.count('window.pywebview.api.step(') == 1)
    src = (BASE / 'bank_agent_window.py').read_text(encoding='utf-8')
    check('s177 B2 the record window is told it is a bill\'s, and only then shows the buttons',
          "kind = 'bill' if str(key).startswith('bill:') else" in src and "('window.__gwBill = true;' if is_bill else '')" in src)

    # ── B3: reading ──
    t = date(2026, 10, 10)
    check('s177 B3 an amount reads only as dollars and cents',
          baw.parse_amount('$142.37') == 142.37 and baw.parse_amount('$ 1,142.37') == 1142.37
          and baw.parse_amount('142') is None and baw.parse_amount('Pay now') is None)
    check('s177 B3 a due date reads in the forms bills use; anything else is None, never guessed',
          baw.parse_due('10/24/2026', t) == date(2026, 10, 24) and baw.parse_due('2026-10-24', t) == date(2026, 10, 24)
          and baw.parse_due('Oct 24, 2026', t) == date(2026, 10, 24) and baw.parse_due('October 24', t) == date(2026, 10, 24)
          and baw.parse_due('Jan 5', t) == date(2027, 1, 5) and baw.parse_due('Sep 30', t) == date(2026, 9, 30)
          and baw.parse_due('soon', t) is None and baw.parse_due('13/45/2026', t) is None)
    check('s177 B3 Groundwork checks each read line again: a figure as the page showed it, nothing else',
          baw.parse_fetch_line('fetch {"s":"read","i":2,"what":"amount","val":"$142.37"}') == {'s': 'read', 'i': 2, 'what': 'amount', 'val': '$142.37'}
          and baw.parse_fetch_line('fetch {"s":"read","what":"balance","val":"$1"}') is None
          and baw.parse_fetch_line('fetch {"s":"read","what":"amount","val":"' + 'x' * 41 + '"}') is None
          and baw.parse_fetch_line('fetch {"s":"read","what":"amount","val":"$1","password":"p"}') is None)
    page, clock, lines = s174._Page(['ok', 'read:{"what":"amount","text":"$142.37"}', 'read:{"what":"due","text":"Oct 24, 2026"}']), s174._Clock(), []
    r = _Driver(page, [{'k': 'click', 'text': 'View bill'}, {'k': 'read', 'what': 'amount', 'field': 'Amount Due'},
                          {'k': 'read', 'what': 'due', 'field': 'Due Date'}], ('u', 'p'), lines.append, now=clock.now, sleep=clock.sleep).run()
    reads = [baw.parse_fetch_line(l) for l in lines if '"read"' in l]
    check('s177 B3 a bill\'s run reads both figures and ends without waiting for a download',
          r == 'done' and [(x['what'], x['val']) for x in reads] == [('amount', '$142.37'), ('due', 'Oct 24, 2026')])
    ds = baw.DO_SCRIPT
    check('s177 B3 the page finds the figure beside its label: an amount with cents, or a date',
          "if (step.k === 'read') {" in ds and "return 'read:' + JSON.stringify({what: step.what, text: m[0]});" in ds)
    fsrc = src.split('def fetch_child_main')[1]
    check('s177 B3 a bill\'s fetch window expects no file', "downloads=None if key.startswith(('bill:', 'pay:')) else _downloads_lister()" in fsrc)

    # ── B1: the vault and the website ──
    check('s177 B1 the vault takes a bill\'s login under bill:<id>, and still refuses anything else',
          bank_vault._entry('bill:7')[1] == 'Groundwork - bill:7' and _raises(lambda: bank_vault._entry('bill:x'))
          and _raises(lambda: bank_vault._entry('payee:7')))
    made_b, made_a = [], []
    try:
        with db_session() as s:
            a = Account(name='s177 Checking', type='checking', is_active=True, portal_url='https://bank.example.com')
            b = BudgetItem(name='s177 Electric', category='Electric', amount=120.0, type='expense', is_active=True)
            s.add_all([a, b]); s.commit()
            made_a.append(a.id); made_b.append(b.id)
            bid, key = b.id, f'bill:{b.id}'
        bad = c.post('/api/settings/bank-agent/bill-site', headers=HJ, data=json.dumps({'id': bid, 'url': 'http://aep.example.com'}))
        good = c.post('/api/settings/bank-agent/bill-site', headers=HJ, data=json.dumps({'id': bid, 'url': 'https://aep.example.com/account'}))
        check('s177 B1 a bill\'s website must be https, as a bank\'s link must', bad.status_code == 400 and good.status_code == 200)
        with db_session() as s:
            rows = server._bank_agent_accounts(s)
        keys = [r['key'] for r in rows]
        check('s177 B4 bills come after the banks in the list Get my accounts visits',
              key in keys and f'account:{made_a[0]}' in keys and keys.index(f'account:{made_a[0]}') < keys.index(key)
              and next(r for r in rows if r['key'] == key)['kind'] == 'bill')

        # ── B3: waiting for a yes; no; yes; use for this month ──
        today = date.today()
        due = date(today.year, today.month, min(28, today.day))
        evs = [{'s': 'read', 'what': 'amount', 'val': '$142.37'}, {'s': 'read', 'what': 'due', 'val': due.strftime('%m/%d/%Y')}, {'s': 'done'}]
        server._bill_pending(key, 'https://aep.example.com/account', evs)
        mine = lambda: next(x for x in c.get('/api/settings/bank-agent/bills', headers=H).get_json()['data']['bills'] if x['id'] == bid)   # noqa: E731
        w = mine()
        with db_session() as s:
            before = s.query(BillReading).filter_by(budget_item_id=bid).count()
        check('s177 B3 what was read waits for a yes, with its source and time; nothing is kept as a reading yet',
              w['pending']['amount'] == 142.37 and w['pending']['due'] == due.isoformat() and w['pending']['host'] == 'aep.example.com'
              and w['pending']['read_at'] and before == 0 and w['confirmed'] is None)
        c.post('/api/settings/bank-agent/bill-read/confirm', headers=HJ, data=json.dumps({'id': bid, 'yes': False}))
        with db_session() as s:
            after_no = s.query(BillReading).filter_by(budget_item_id=bid).count()
        check('s177 B3 "Not right" discards it: nothing kept', after_no == 0 and mine()['pending'] is None)
        server._bill_pending(key, 'https://aep.example.com/account', evs)
        y = c.post('/api/settings/bank-agent/bill-read/confirm', headers=HJ, data=json.dumps({'id': bid, 'yes': True})).get_json()['data']
        with db_session() as s:
            ev = s.query(HistorianEntry).filter(HistorianEntry.event_category == 'bill_confirmed').order_by(HistorianEntry.id.desc()).first()
            evctx = json.loads(ev.context_json) if ev else {}
            month_before = server.budget_month_amounts(s)[bid]
            saved_amt = s.get(BudgetItem, bid).amount
        check('s177 B3 "Yes" keeps it as a reading, recorded in the Historian; the month still uses the saved amount',
              y['confirmed']['amount'] == 142.37 and evctx.get('budget_item_id') == bid and evctx.get('amount') == 142.37
              and month_before['month_source'] != 'bill' and month_before['month_amount'] == 120.0 and saved_amt == 120.0)
        c.post('/api/settings/bank-agent/bill-read/use', headers=HJ, data=json.dumps({'reading_id': y['confirmed']['id'], 'use': True}))
        with db_session() as s:
            month_use = server.budget_month_amounts(s)[bid]
            saved_after = s.get(BudgetItem, bid).amount
        check('s177 B3 "Use the bill\'s amount for this month": the month\'s figure is the bill\'s, it says where from, and the saved amount is untouched',
              month_use['month_source'] == 'bill' and month_use['month_amount'] == 142.37 and 'aep.example.com' in month_use['month_from']
              and saved_after == 120.0)
        server._bill_pending(key, 'https://aep.example.com/account', [{'s': 'read', 'what': 'amount', 'val': 'Pay now'}])
        check('s177 B3 a figure that won\'t read as an amount is named and left out, never guessed',
              mine()['pending']['amount'] is None and mine()['pending']['amount_text'] == 'Pay now')
        c.post('/api/settings/bank-agent/bill-site', headers=HJ, data=json.dumps({'id': bid, 'url': ''}))
        with db_session() as s:
            gone = [k for k in (f'bill_site:{bid}', f'bill_pending:{bid}') if s.query(AppSetting).filter_by(key=k).first()]
        check('s177 B1 removing a bill\'s website removes its saved steps and anything waiting', gone == [])
    finally:
        with db_session() as s:
            s.query(BillReading).filter(BillReading.budget_item_id.in_(made_b)).delete(synchronize_session=False)
            s.query(AppSetting).filter(AppSetting.key.in_([f'{p}{i}' for i in made_b for p in ('bill_site:', 'bill_pending:', 'bank_recipe:bill:')])).delete(synchronize_session=False)
            s.query(HistorianEntry).filter(HistorianEntry.event_category == 'bill_confirmed').delete(synchronize_session=False)
            s.query(BudgetItem).filter(BudgetItem.id.in_(made_b)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made_a)).delete(synchronize_session=False)
            s.commit()

    # ── B5: never from email ──
    code = '\n'.join(p.read_text(encoding='utf-8', errors='ignore') for p in [BASE / 'server.py', BASE / 'launch.py', BASE / 'bank_agent_window.py']
                     + list((BASE / 'core').glob('*.py')))
    check('s177 B5 nothing in Groundwork reads email: no mail library, no mailbox route',
          not re.search(r'^\s*(import|from)\s+(imaplib|poplib|exchangelib|email\.parser)\b', code, re.M)
          and not re.search(r"route\('/[^']*(mail|inbox)", code))
    app = ctx.app_src
    check('s177 B3 the Budget page shows what was read with its source and time, asks for a yes, and offers "use the bill\'s amount" only for this month',
          "Is that right?" in app and "confirmBillReading(${b.id}, true)" in app and "Use the bill's amount for this month (your saved amount stays as it is)" in app
          and 'id="budgetBillsCard"' in ctx.html_src and 'renderBudgetBills();   // item 68 B3' in app)
    # Rob, 2026-10-10: the login is saved on the bill's own line too
    check('s177 B1 each bill with a website has Save login on its own line (or says the login is saved), into the same vault',
          "openBankLoginForm('bill:${b.id}', 'billLoginForm-${b.id}')" in app and 'login saved in the vault' in app
          and "bank_vault.has_login(f'bill:{b.id}')" in (BASE / 'server.py').read_text(encoding='utf-8'))


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False
