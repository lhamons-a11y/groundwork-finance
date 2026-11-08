"""Item 117 (gw 2.0/DEMO_BANK.md; Rob 2026-11-07: "Accept all as recommended", "Build it"): a demo bank and a demo biller
on Groundwork's own website, so the public can see "Get my accounts" and a bill read from its biller work.

    D1  they live on the website, at https addresses the bank window already accepts: nothing in the app was loosened
    D2  every page says it isn't real, is never indexed, and the sample's bank is "Demo Credit Union"
    D3  any login works and nothing typed is kept: no demo route writes anything
    D4  the code page shows its code and the agent sees it as a code page; a wrong code is refused; "Remember this
        computer" skips it next time; each cookie holds nothing but "1"
    D5  each download is the Morgans' own lines (one source, sample_lines.py, copied byte for byte to the website), in
        CSV, OFX and QFX, read by Groundwork's own importer, dated up to today
    D6  the security-check page is one the agent stops at, and no other demo page looks like one
    D7  the biller's amount and due date are where a recording finds them, and Pay now is never recorded or pressed
    D8  the sample arrives linked (checking and the card at the bank, the electric bill at the biller, no steps), and
        "Start with my own" forgets only the logins saved while the sample was here
"""
import json
import os
import re
import subprocess
import sys
import tempfile

_SCRIPT = r'''
import json, os, sys
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), 'core'))
import keyring
from keyring.backend import KeyringBackend

class _Memory(KeyringBackend):
    priority = 1
    store = {}
    def get_password(self, service, username):
        return self.store.get((service, username))
    def set_password(self, service, username, password):
        self.store[(service, username)] = password
    def delete_password(self, service, username):
        if (service, username) not in self.store:
            raise keyring.errors.PasswordDeleteError('none')
        del self.store[(service, username)]

mem = _Memory(); keyring.set_keyring(mem)
from server import create_app, _GW_TOKEN
from core import bank_vault
app = create_app(); c = app.test_client(); H = {'X-GW-Token': _GW_TOKEN, 'Content-Type': 'application/json'}
out = {}
c.patch('/api/settings', headers=H, data=json.dumps({'terms_accepted': 'v-test', 'ai_enabled': 'false'}))
out['load'] = c.post('/api/sample/load', headers=H).get_json().get('ok')
accts = c.get('/api/accounts', headers=H).get_json()['data']
out['accounts'] = sorted([a['name'], a.get('institution') or '', bool(a.get('has_portal'))] for a in accts)
ids = {a['name']: a['id'] for a in accts}
out['portal'] = c.get(f"/api/accounts/{ids['Everyday Checking']}/portal", headers=H).get_json()['data']['url']
rows = c.get('/api/settings/bank-logins', headers=H).get_json()['data']['accounts']
out['agent_rows'] = sorted([r['name'], r.get('kind', ''), bool(r.get('has_steps'))] for r in rows)
bill_key = next(r['key'] for r in rows if r.get('kind') == 'bill')
check_key = f"account:{ids['Everyday Checking']}"
savings_key = f"account:{ids['High-Yield Savings']}"
# a vault entry the sample never saved - for one of its own ids, and one for a household's account elsewhere
bank_vault.save_login(savings_key, 'kept', 'kept-1')
bank_vault.save_login('account:999', 'kept', 'kept-2')
planted = c.patch('/api/settings', headers=H, data=json.dumps({'sample_vault_keys': json.dumps(['account:999'])}))
for k in (check_key, bill_key):
    r = c.post('/api/settings/bank-logins', headers=H, data=json.dumps({'key': k, 'username': 'morgan', 'password': 'demo', 'acknowledged': True}))
    out.setdefault('saved', []).append(r.get_json().get('ok'))
out['clear'] = c.post('/api/sample/clear', headers=H).get_json().get('ok')
out['vault_after'] = sorted(u for (_s, u) in mem.store)
out['names'] = [check_key, bill_key, savings_key]
print('@@' + json.dumps(out))
'''


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    core_src = (BASE / 'core' / 'sample_lines.py').read_bytes()
    check('s293 D5 the website carries the sample lines byte for byte (Website/sample_lines.py == core/sample_lines.py), '
          'and they import nothing of Groundwork\'s',
          (BASE / 'Website' / 'sample_lines.py').read_bytes() == core_src
          and not re.search(rb'^\s*(from|import)\s+(core|server|bank_)', core_src, re.M))

    import importlib
    os.environ.setdefault('GW_SITE_DATA', tempfile.mkdtemp(prefix='gw_site_'))
    sys.path.insert(0, str(BASE / 'Website'))
    site = importlib.import_module('website')
    src = (BASE / 'Website' / 'website.py').read_text(encoding='utf-8')
    demo_src = src.split('# ── Item 117: the demo bank', 1)[1].split("if __name__ == '__main__':", 1)[0]
    import bank_agent_window as baw
    import bank_window
    from bank_importer import detect_and_parse

    # D1
    check('s293 D1 the demo addresses are ones the bank window already accepts, and the window still refuses this computer',
          bank_window.portal_url_problem('https://groundworkfinance.app/demo-bank/') is None
          and bank_window.portal_url_problem('https://groundworkfinance.app/demo-bill/') is None
          and bank_window.portal_url_problem('https://localhost/demo-bank/') is not None
          and bank_window.portal_url_problem('http://groundworkfinance.app/demo-bank/') is not None)

    sc = site.app.test_client()
    signin = sc.get('/demo-bank/')
    bill_signin = sc.get('/demo-bill/')
    # D3: no demo route writes anything
    check('s293 D3 no demo route writes anything: no database, no file',
          not re.search(r'get_db\(|sqlite3|\bopen\(|\.write\(|_bump\(|session\[', demo_src))
    bad = sc.post('/demo-bank/sign-in', data={'username': '', 'password': ''})
    sc.post('/demo-bank/sign-in', data={'username': 'anyone', 'password': 'anything'})
    verify = sc.get('/demo-bank/verify')
    code = site._demo_code()
    vt = verify.get_data(as_text=True)
    wrong = sc.post('/demo-bank/verify', data={'code': '000000' if code != '000000' else '111111'})
    ok = sc.post('/demo-bank/verify', data={'code': f'{code[:3]} {code[3:]}', 'remember': '1'})
    cookies = ok.headers.getlist('Set-Cookie')
    pages = {p: sc.get(p) for p in ('/demo-bank/accounts', '/demo-bank/accounts/checking', '/demo-bank/accounts/visa/download',
                                    '/demo-bank/security-check')}
    sc.get('/demo-bank/sign-out')
    after_out = sc.get('/demo-bank/accounts')
    again = sc.post('/demo-bank/sign-in', data={'username': 'x', 'password': 'y'})
    check('s293 D3 any username and password are let in; an empty one is asked for again',
          bad.status_code == 400 and again.status_code == 302)
    check('s293 D4 the code page shows its own code and holds a box the agent knows as a code (one-time-code); a wrong code '
          'is refused', f'{code[:3]} {code[3:]}' in vt and 'autocomplete="one-time-code"' in vt and 'Remember this computer' in vt
          and wrong.status_code == 400 and ok.headers.get('Location', '').endswith('/demo-bank/accounts'))
    check(f's293 D4 the cookies hold nothing but "1", only on the demo\'s path; signing out signs out; a remembered computer '
          f'skips the code ({cookies})',
          len(cookies) == 2 and all(c.split(';')[0].split('=')[1] == '1' and 'Path=/demo-bank' in c and 'HttpOnly' in c for c in cookies)
          and after_out.status_code == 302 and again.headers.get('Location', '').endswith('/demo-bank/accounts'))

    # D2
    texts = {p: r.get_data(as_text=True) for p, r in pages.items()}
    texts.update({'/demo-bank/': signin.get_data(as_text=True), '/demo-bank/verify': vt, '/demo-bill/': bill_signin.get_data(as_text=True)})
    sc.post('/demo-bill/sign-in', data={'username': 'x', 'password': 'y'})
    bill = sc.get('/demo-bill/account')
    texts['/demo-bill/account'] = bill.get_data(as_text=True)
    unlabelled = [p for p, t in texts.items() if not re.search(r'Not a real (bank|power company)\.', t)
                  or 'noindex' not in t]
    robots = sc.get('/robots.txt').get_data(as_text=True)
    check(f's293 D2 every demo page says first that it is not real, and is never indexed ({unlabelled})',
          not unlabelled and all(r.status_code == 200 for r in pages.values())
          and 'Disallow: /demo-bank/' in robots and 'Disallow: /demo-bill/' in robots
          and signin.headers.get('X-Robots-Tag') == 'noindex, nofollow')

    # D6: the agent's own words for a robot check (DO_SCRIPT's botCheck), applied to every demo page
    bot_words = re.compile(r"unusual activity|verify (that )?you(’|')?re (a )?human|are you a robot", re.I)
    def looks_like_bot(t):
        return bool(re.search(r'id="[^"]*captcha', t, re.I) or bot_words.search(re.sub(r'<[^>]+>', ' ', t)))
    flagged = sorted(p for p, t in texts.items() if looks_like_bot(t))
    check(f's293 D6 the security-check page is one the agent stops at, and it is the only demo page that is ({flagged})',
          flagged == ['/demo-bank/security-check'] and 'are you a robot' in baw.DO_SCRIPT
          and '[id*="captcha" i]' in baw.DO_SCRIPT)

    # D5
    from datetime import date
    from core.sample_lines import everyday
    _, lines = everyday(date.today())
    sc.post('/demo-bank/sign-in', data={'username': 'x', 'password': 'y'})       # remembered: straight in
    got, wrong_files = {}, []
    for acct in ('checking', 'savings', 'visa'):
        want = sorted((ln['date'].isoformat(), ln['description'], ln['amount'], ln['kind']) for ln in lines if ln['acct'] == acct)
        for fmt in ('csv', 'ofx', 'qfx'):
            r = sc.get(f'/demo-bank/file?account={acct}&range=all&format={fmt}')
            name = re.search(r'filename="([^"]+)"', r.headers.get('Content-Disposition', '')).group(1)
            recs, _bank, _w = detect_and_parse(r.get_data(as_text=True), name)
            have = sorted((x['date'], x['description'], x['amount'], x['type']) for x in recs)
            got[f'{acct}.{fmt}'] = len(have)
            if have != want or not name.endswith('.' + fmt):
                wrong_files.append(f'{acct}.{fmt}')
    recent = sc.get('/demo-bank/file?account=checking&range=30&format=csv').get_data(as_text=True)
    check(f's293 D5 every download is the Morgans\' own lines, read back the same by Groundwork\'s importer in all three '
          f'formats ({got}; wrong: {wrong_files})', not wrong_files and sum(got.values()) == 3 * len(lines))
    check('s293 D5 a range is a range, up to today, and a download needs a sign-in',
          all(re.match(r'\d\d/\d\d/\d{4}', ln) for ln in recent.splitlines()[1:])
          and len(recent.splitlines()) - 1 < got['checking.csv']
          and site.app.test_client().get('/demo-bank/file?account=checking&range=30&format=csv').status_code == 302)

    # D7: what a recording of the bill page would hold, and what a run would read
    bt = texts['/demo-bill/account']
    amount = re.search(r'<span>Amount due</span><strong class="big">(\$[\d,]+\.\d\d)</strong>', bt)
    due = re.search(r'<span>Due date</span><strong>([A-Z][a-z]{2} \d{1,2}, \d{4})</strong>', bt)
    pay = baw.clean_step({'k': 'click', 'role': 'button', 'text': 'Pay now'})
    check(f's293 D7 the biller\'s amount due and due date sit beside their labels where a run reads them, and Pay now is '
          f'never recorded ({amount and amount.group(1)}, {due and due.group(1)}, {pay})',
          amount and due and pay is None and baw.clean_step({'k': 'read', 'what': 'amount', 'field': 'Amount due'})
          and 'Not a real power company.' in bt and 'nothing was paid' in bt)

    # D8, in its own process and folder (the sample needs an empty Groundwork, and a vault of its own)
    env = {**os.environ, 'GROUNDWORK_DATA_DIR': tempfile.mkdtemp(prefix='s293_')}
    p = subprocess.run([sys.executable, '-c', _SCRIPT], cwd=str(BASE), env=env, capture_output=True, text=True, timeout=300)
    line = next((l for l in p.stdout.splitlines() if l.startswith('@@')), None)
    if not line:
        check(f's293 D8 the sample household ran ({(p.stderr or "")[-600:]})', False)
        return
    o = json.loads(line[2:])
    acc = {a[0]: a for a in o['accounts']}
    check(f"s293 D2/D8 the sample's bank is Demo Credit Union; its checking account and card are linked to the demo bank "
          f"and nothing else is ({o['accounts']}, {o['portal']})",
          o['load'] and acc['Everyday Checking'][1:] == ['Demo Credit Union', True] and acc['High-Yield Savings'][1:] == ['Demo Credit Union', False]
          and acc['Cashback Visa'][2] is True and acc['Brokerage'][2] is False
          and o['portal'] == 'https://groundworkfinance.app/demo-bank/')
    check(f"s293 D8 the electric bill is linked to the demo biller, and no steps are recorded for any of them ({o['agent_rows']})",
          ['Electric', 'bill', False] in o['agent_rows'] and not any(r[2] for r in o['agent_rows']))
    ck, bk, sk = o['names']
    check(f"s293 D8 \"Start with my own\" forgets the logins saved while the sample was here, and nothing else in the vault - "
          f"not even one for the sample's own ids, nor one the settings route tried to plant ({o['vault_after']})",
          o['saved'] == [True, True] and o['clear'] is True
          and o['vault_after'] == sorted([f'Groundwork - {sk}', 'Groundwork - account:999'])
          and "body.pop('sample_vault_keys', None)" in ctx.server_src)
