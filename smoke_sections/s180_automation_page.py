"""Item 69: the Automation page in the Assistant group (gw 2.0/AUTOMATION_PAGE.md P1-P8; RULED 2026-10-10, Rob:
"approve P1-P8 as recommended"; built on "build item 69").

    P1  the page in the sidebar's Assistant group; Settings' card moved there, one line left pointing to it
    P2  the page's top: Get my accounts, each account's last fetch, the reminder's days
    P3  every account and standalone card by name - no balance, no amount - and where each stands, in words
    P4  a row's settings slide down on a double-click, its ▸, or Enter; one row open at a time; Esc closes
    P5  bills the same way, with "Paid from" and the way to pay
    P6  the Budget card keeps the money and links to the setup
    P7  Settings -> Accounts unchanged; the website saved from either place is the same field
"""
import json
import re


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core.database import Account, DebtAccount, db_session
    html, app = ctx.html_src, ctx.app_src
    settings = html.split('id="view-settings"')[1].split('<div id="view-')[0]

    # ── P1 ──
    check('s180 P1 the Settings card is gone; one line in its place points to Coach -> Assistant',
          'Fetch my downloads' not in settings and 'settingsBankLogins' not in html and 'settingsBillSites' not in html
          and 'id="settingsAutomationPointer"' in settings and "showView('automation')" in settings
          and 'Coach → Assistant' in settings)
    nav = html.split('id="navAssistant"')[1].split('</div>\n      </div>')[0] if 'id="navAssistant"' in html else ''
    # renamed (Rob 2026-10-10: "combined they are a financial coach, Coach it is"): the group is Coach, the page Assistant
    check('s180 P1 the Assistant page is in the sidebar\'s Coach group, and the page exists',
          '>Coach<' in nav and 'data-view="automation"' in nav and '</span>Assistant' in nav and 'id="view-automation"' in html
          and "automation: 'Assistant'" in app and 'Automation page' not in app
          and "if (name === 'automation') renderBankLogins();" in app)
    will = (ctx.BASE / 'static/js/teaching/willingness.js').read_text(encoding='utf-8')
    check('s180 P1 the teaching layer joins that Assistant group rather than making a second one; app.js still never names it',
          "var assistant = g('navAssistant');" in will and 'assistant.appendChild(it);' in will
          and not re.search(r'willingness|view-picture|Working picture', app, re.I))
    check('s180 P1 Settings no longer draws the logins', 'function renderSettings() {\n  _settingsShowTab(_settingsActiveTab);' in app)

    # ── P2 ──
    top = app.split('function automationTopHtml(')[1].split('\nfunction ')[0]
    check('s180 P2 the top: Get my accounts, each account\'s last fetch, and the reminder\'s days',
          "onclick=\"startFetchAll()\"" in top and '_fetchAgo(a.days)' in top and 'setFetchRemindDays(this.value)' in top)

    # ── P3: every account and card, no amounts ──
    made_a, made_d = [], []
    try:
        with db_session() as s:
            a1 = Account(name='s180 Linked', type='checking', is_active=True, portal_url='https://bank.example.com')
            a2 = Account(name='s180 Unlinked', type='savings', is_active=True)
            d1 = DebtAccount(name='s180 Card', is_active=True, current_balance=812.0)
            s.add_all([a1, a2, d1]); s.commit()
            made_a += [a1.id, a2.id]; made_d.append(d1.id)
            k1, k2, k3 = f'account:{a1.id}', f'account:{a2.id}', f'card:{d1.id}'
        rows = c.get('/api/settings/bank-logins?all=1', headers=H).get_json()['data']['accounts']
        mine = {r['key']: r for r in rows if r['key'] in (k1, k2, k3)}
        check('s180 P3 every account and standalone card is listed, with a link or without, and says whether it has one',
              set(mine) == {k1, k2, k3} and mine[k1]['has_site'] is True and mine[k2]['has_site'] is False and mine[k3]['has_site'] is False)
        check('s180 P3 no balance, amount or address in what the page is given',
              not any(k in r for r in rows for k in ('balance', 'amount', 'current_balance', 'url', 'portal_url'))
              and 'bank.example.com' not in json.dumps(rows) and '812' not in json.dumps(rows))
        plain = c.get('/api/settings/bank-logins', headers=H).get_json()['data']['accounts']
        check('s180 P3 without ?all the list is as before (only those with a link) - Get my accounts reads that one',
              k1 in [r['key'] for r in plain] and k2 not in [r['key'] for r in plain])
    finally:
        with db_session() as s:
            s.query(Account).filter(Account.id.in_(made_a)).delete(synchronize_session=False)
            s.query(DebtAccount).filter(DebtAccount.id.in_(made_d)).delete(synchronize_session=False)
            s.commit()
    page_fns = ''.join(app.split(f'function {n}(')[1].split('\nfunction ')[0] for n in ('bankLoginsHtml', 'billSitesHtml', '_autoRow', '_autoStatus', 'automationTopHtml'))
    check('s180 P3 the page draws no money: no amount formatting, no balance, no planned amount',
          'fmt(' not in page_fns and '.balance' not in page_fns and '.planned' not in page_fns and '.amount' not in page_fns)
    check('s180 P3 each row says where it stands, in words', all(w in app for w in ("'needs a website'", "'login saved'", "'steps saved'", "'remembered computer'")))

    # ── P4: open a row ──
    row = app.split('function _autoRow(')[1].split('\nfunction ')[0]
    check('s180 P4 (amended) a click on the row, its arrow, and Enter all open it the same way',
          '<div class="gw-auto-head" onclick="toggleAutoRow(' in row and "event.stopPropagation();toggleAutoRow(" in row
          and "if (event.key === 'Enter' && event.target === this) toggleAutoRow(" in row and 'tabindex="0"' in row and 'aria-expanded' in row
          and 'ondblclick' not in row)
    check('s180 P4 (amended) it slides open smoothly - the height eases and the arrow turns - and a closed row cannot be tabbed into',
          '.gw-auto-details{display:grid;grid-template-rows:0fr' in html and '.gw-auto-details.open{grid-template-rows:1fr' in html
          and '.gw-auto-row.open .gw-auto-chev{transform:rotate(90deg)}' in html and "det.toggleAttribute('inert', !open)" in app)
    check('s180 tabs: Accounts and Bills, each its own panel; a bill opened from the Budget page lands on the Bills tab',
          'id="autoTab-accounts" role="tab"' in html and 'id="autoTab-bills" role="tab"' in html
          and 'id="autoPanel-accounts" role="tabpanel"' in html and 'id="autoPanel-bills" role="tabpanel"' in html
          and "_autoTab = /^(bill|pay):/.test(key) ? 'bills' : 'accounts';" in app and '_autoShowTab(_autoTab);' in app)
    tog = app.split('function toggleAutoRow(')[1].split('\nfunction ')[0]
    check('s180 P4 one row open at a time, and Esc closes it',
          "_autoOpen = _autoOpen === key ? null : key;" in tog and "row.dataset.autoKey === _autoOpen" in tog
          and "e.key === 'Escape' && _autoOpen" in app)
    check('s180 P4 the slide respects reduced motion',
          '@media (prefers-reduced-motion: reduce){.gw-auto-details,.gw-auto-chev,.gw-auto-head{transition:none}}' in html)
    check('s180 P4 the address is read into its field only when that row is open - never kept in page state',
          "if (!_autoOpen || !/^(account|card):\\d+$/.test(_autoOpen)) return;" in app and 'portal_url' not in app)

    # ── P5, P6, P7 ──
    bills = app.split('function billSitesHtml(')[1].split('\nasync function saveBillSite(')[0]
    check('s180 P5 a bill\'s row holds its website, login, show me once, read, paid from, and the way to pay',
          all(x in bills for x in ('saveBillSite(', "openBankLoginForm('bill:${b.id}', 'billLoginForm-${b.id}')", "startBankRecording('${key}')",
                                   "startBankFetch('${key}')", 'setBillFrom(', "startBankRecording('pay:${b.id}')")))
    card = app.split('function billCheckHtml(')[1].split('\nasync function setBillFrom(')[0]
    check('s180 P6 the Budget card keeps the money and links to the setup',
          "openAutomationRow('bill:${c.id}')" in card and 'setBillFrom(' not in card and "startBankRecording('pay:" not in card
          and 'Take me to pay this' in card and 'Can I pay this?' in card)
    check('s180 P7 the website saved from the Automation page goes through the same route Settings -> Accounts uses',
          "API.put(kind === 'account' ? `/api/accounts/${id}/portal` : `/api/debt/${id}/portal`, { url: v })" in app
          and "await API.put(`/api/accounts/${id}/portal`, { url: portal });" in app)
    for path in ('/api/settings/bank-logins', '/api/settings/bank-agent/bills', '/api/settings/bank-agent/last-fetched'):
        check(f's180 P8 the page\'s routes still answer: {path}', c.get(path, headers=H).status_code == 200)
