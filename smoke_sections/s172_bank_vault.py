"""Item 57 stage 1: saved bank logins live in the operating system's vault (gw 2.0/BANK_AGENT.md A3/A4; Rob 2026-10-09:
"I agree with keeping the passwords in the security vaults in the operating system", "BUILD 57").

    A3  before the first login is saved the user reads why fetching only runs when they ask (two-step verification,
        the banks' rules) and where the password lives, and accepts it - the server refuses a save without that
    A4  the password goes to the vault and nowhere else: not the database, settings, logs or a response; Settings
        lists which accounts have a saved login and Forget deletes it; no vault, no feature (no file fallback)
The real vault is never touched: a stand-in backend replaces it for the section.
"""
import json
import re
import shutil
import subprocess

SECRET = 's172-Pa55word-zq'


def run(ctx):
    check, c, H, HJ, BASE, app, srv = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE, ctx.app_src, ctx.server_src
    import keyring
    from keyring.backend import KeyringBackend
    from keyring.backends import fail
    from core import bank_vault
    from core.database import Account, DebtAccount, AppSetting, db_session

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

    real = keyring.get_keyring()
    mem = _Memory()
    made_a, made_d = [], []
    try:
        keyring.set_keyring(mem)
        with db_session() as s:
            a = Account(name='s172 Checking', type='checking', is_active=True, portal_url='https://bank.example.com')
            b = Account(name='s172 No Link', type='checking', is_active=True)
            d = DebtAccount(name='s172 Card', current_balance=0, interest_rate=0, minimum_payment=0, debt_type='credit',
                            is_active=True, portal_url='https://card.example.com')
            s.add_all([a, b, d]); s.commit()
            made_a += [a.id, b.id]; made_d.append(d.id)
            ka, kb, kd = f'account:{a.id}', f'account:{b.id}', f'card:{d.id}'
        lst = c.get('/api/settings/bank-logins', headers=H).get_json()['data']
        keys = {r['key']: r for r in lst['accounts']}
        check('s172 A4 Settings lists the accounts and cards with a bank link, none with a login yet',
              lst['available'] is True and ka in keys and kd in keys and kb not in keys
              and not keys[ka]['has_login'])
        r = c.post('/api/settings/bank-logins', headers=HJ, data=json.dumps({'key': ka, 'username': 'u', 'password': SECRET}))
        check('s172 A3 a login is refused until the user has accepted how fetching works', r.status_code == 400 and not mem.store)
        r = c.post('/api/settings/bank-logins', headers=HJ, data=json.dumps({'key': kb, 'username': 'u', 'password': SECRET, 'acknowledged': True}))
        check('s172 A4 an account with no bank link cannot have a login', r.status_code == 400 and not mem.store)
        r = c.post('/api/settings/bank-logins', headers=HJ, data=json.dumps({'key': ka, 'username': 's172user', 'password': SECRET, 'acknowledged': True}))
        stored = mem.store.get(('Groundwork', f'Groundwork - {ka}'))
        check('s172 A4 accepted: the login is in the vault, under "Groundwork - account:<id>"',
              r.status_code == 200 and stored and json.loads(stored) == {'u': 's172user', 'p': SECRET})
        lst = c.get('/api/settings/bank-logins', headers=H)
        check('s172 A4 the page sees that a login is saved - and never the password',
              lst.get_json()['data']['accounts'] and SECRET not in lst.get_data(as_text=True) and SECRET not in r.get_data(as_text=True)
              and next(x for x in lst.get_json()['data']['accounts'] if x['key'] == ka)['has_login'] is True)
        with db_session() as s:
            in_settings = [x.key for x in s.query(AppSetting).all() if SECRET in (x.value or '')]
        dump = ''
        import sqlite3
        from core import database as dbm
        con = sqlite3.connect(str(dbm.DB_PATH))
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            for row in con.execute(f'SELECT * FROM "{t}"'):
                dump += ' '.join(str(v) for v in row) + '\n'
        con.close()
        logs = ''
        for f in ctx.TMP.rglob('*.log'):
            try:
                logs += f.read_text(encoding='utf-8', errors='replace')
            except OSError:
                pass
        check('s172 A4 the password is in no table of the database, no setting and no log', not in_settings and SECRET not in dump and SECRET not in logs)
        r = c.post('/api/settings/bank-logins/forget', headers=HJ, data=json.dumps({'key': ka}))
        check('s172 A4 Forget deletes the vault entry', r.get_json()['data']['forgotten'] is True and not mem.store
              and next(x for x in c.get('/api/settings/bank-logins', headers=H).get_json()['data']['accounts'] if x['key'] == ka)['has_login'] is False)

        keyring.set_keyring(fail.Keyring())
        lst = c.get('/api/settings/bank-logins', headers=H).get_json()['data']
        r = c.post('/api/settings/bank-logins', headers=HJ, data=json.dumps({'key': kd, 'username': 'u', 'password': SECRET, 'acknowledged': True}))
        check('s172 A4 no vault on the computer: the feature says so, and nothing is saved anywhere (no file fallback)',
              lst['available'] is False and r.status_code == 400 and not mem.store)
    finally:
        keyring.set_keyring(real)
        with db_session() as s:
            s.query(Account).filter(Account.id.in_(made_a)).delete(synchronize_session=False)
            s.query(DebtAccount).filter(DebtAccount.id.in_(made_d)).delete(synchronize_session=False)
            s.commit()

    # the code itself
    vault_src = (BASE / 'core/bank_vault.py').read_text(encoding='utf-8')
    check('s172 A4 the vault module reaches only keyring - no database, server or file write',
          not re.search(r'^\s*(from|import)\s+(server|core\.database|sqlite3)', vault_src, re.M) and 'open(' not in vault_src)
    check('s172 A4 no route reads a password back (read_login is for the fetch alone)', 'read_login' not in srv)
    check('s172 A4 the requirement and all three builds carry keyring',
          'keyring>=' in (BASE / 'requirements.txt').read_text(encoding='utf-8')
          and all("'keyring'," in (BASE / s).read_text(encoding='utf-8') for s in ('groundwork.spec', 'groundwork_linux.spec', 'groundwork_macos.spec')))

    node = shutil.which('node')
    if node:
        m = re.search(r'\nconst BANK_AGENT_TERMS = \[.*?\n\];\n', app, re.S)
        f = re.search(r'\nfunction bankLoginsHtml\(.*?\n\}\n', app, re.S)
        # item 69: the accounts list is drawn as rows - its two helpers come with it
        h = ''.join(x.group(0) for x in (re.search(r'\nfunction _autoStatus\(.*?\n\}\n', app, re.S),
                                         re.search(r'\nfunction _autoRow\(.*?\n\}\n', app, re.S)) if x)
        js = 'const esc = s => String(s);\nlet _autoOpen = null;\n' + (m.group(0) if m else '') + h + (f.group(0) if f else '') + \
             "console.log(JSON.stringify([bankLoginsHtml({available: true, vault: 'Windows Credential Manager', accounts: [{key: 'account:1', name: 'Checking', has_login: false}]}), bankLoginsHtml({available: false})]));"
        p = subprocess.run([node, '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=60)
        out = json.loads(p.stdout.strip() or '["",""]')
        check('s172 A3 the page says why it only runs when asked (two-step verification, the banks\' rules) and where the password lives',
              'only when you ask' in out[0] and 'two-step verification' in out[0] and 'Windows Credential Manager' in out[0]
              and 'Anyone who can sign in to your computer as you could use it' in out[0] and 'Save login' in out[0])
        check('s172 A4 with no vault the page says so and offers nothing to save', "can't keep a bank login" in out[1] and 'Save login' not in out[1])
    check('s172 A4 the password box is a password field, emptied after every save attempt',
          'type="password" id="bankLoginPass"' in app and "if (p) p.value = '';" in app)
