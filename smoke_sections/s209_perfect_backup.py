"""Item 81, the perfect backup (gw 2.0/PERFECT_BACKUP.md B1-B9; Rob 2026-10-12: "I approve b1-b10"; B10 the optional
security key, built after these with Rob's key).

    B1  every backup is sealed; a damaged or altered one is refused and the live data is untouched
    B2  three keys: this computer's vault, the backup password, the 24-word recovery key - any one opens it; a
        "fresh Groundwork" (another computer, no vault key) opens it only with the password or the words
    B3  set up once: a password of 10+, 24 words shown once, confirmed; the words are never stored
    B4  restoring here needs nothing; elsewhere the password or words; a wrong one is refused
    B5  a versioned format; "Check this backup" opens it without restoring
    B6  a new password or new recovery key never strands an older backup
    B7  old plain backups re-saved sealed on a tap; deleting is the person's tap
    B8  this computer can set a new password and words; no other can
    B9  no key in the settings, the log, or anywhere it could leave
"""
import base64
import hashlib
import io
import json
from pathlib import Path


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import server
    from core import backup_crypto as bc
    from core.database import AppSetting, DATA_DIR, Transaction, db_session
    from datetime import date

    post = lambda p, b: c.post(p, headers=HJ, data=json.dumps(b))
    data = lambda r: (r.get_json() or {}).get('data')
    msg = lambda r: (r.get_json() or {}).get('error') or ''

    check('s209 B3 the recovery word list is 256 distinct words, fixed forever (every written key depends on its order)',
          len(bc.WORDLIST) == 256 and len(set(bc.WORDLIST)) == 256
          and hashlib.sha256(' '.join(bc.WORDLIST).encode()).hexdigest() == 'cd8a89c695f7a95ac280e42bad7aea2b77f05d606eececfe965037f866bd5295')

    old_vault = bc.VAULT
    vault = bc.VAULT = bc.MemoryVault()
    try:
        with db_session() as s:
            s.query(AppSetting).filter_by(key=bc.SETTING).delete(); s.commit()
        before = c.post('/api/backup/create', headers=HJ, data='{}')
        short = post('/api/backup/protect/setup', {'password': 'short'})
        setup = post('/api/backup/protect/setup', {'password': 'first password 01'})
        words = data(setup)['words']
        early = c.post('/api/backup/create', headers=HJ, data='{}')
        conf = c.post('/api/backup/protect/confirm', headers=HJ, data='{}')
        again = post('/api/backup/protect/setup', {'password': 'another password'})
        with db_session() as s:
            stored = s.query(AppSetting).filter_by(key=bc.SETTING).first().value
        check('s209 B1/B3 no unprotected backup: one is refused until a password (10+) is set and the words confirmed; setting up twice is refused',
              before.status_code == 409 and short.status_code == 400 and setup.status_code == 200 and len(words) == 24
              and early.status_code == 409 and conf.status_code == 200 and again.status_code == 400)
        key = vault.get()
        check('s209 B3/B9 the words and the key are never stored: the setting holds only wrapped copies',
              key is not None and ' '.join(words) not in stored and base64.b64encode(key).decode() not in stored
              and key.hex() not in stored and '"pw"' in stored and '"rec"' in stored)

        made = data(c.post('/api/backup/create', headers=HJ, data='{}'))
        path = server._backups_dir() / made['filename']
        blob = path.read_bytes()
        check("s209 B1/B5 a backup is sealed: a versioned GWBK1 file, not readable as a database",
              made['encrypted'] and made['filename'].endswith('.gwbk') and blob[:6] == b'GWBK1\n'
              and b'SQLite format 3' not in blob and bc.read_header(blob)[0]['v'] == 1)

        here = data(post('/api/backup/check', {'filename': made['filename']}))
        bc.VAULT = bc.MemoryVault()                 # another computer: Groundwork, but no key in its vault
        elsewhere = post('/api/backup/check', {'filename': made['filename']})
        wrong = post('/api/backup/check', {'filename': made['filename'], 'password': 'not the password'})
        by_pw = data(post('/api/backup/check', {'filename': made['filename'], 'password': 'first password 01'}))
        by_words = data(post('/api/backup/check', {'filename': made['filename'], 'words': words}))
        bad_words = post('/api/backup/check', {'filename': made['filename'], 'words': list(reversed(words))})
        bc.VAULT = vault
        check(f"s209 B2/B4 three keys: this computer opens it with nothing typed; another computer needs the password or the words; a wrong one is refused ({here['opened_with']}, {by_pw['opened_with']}, {by_words['opened_with']})",
              here['opened_with'] == 'this computer' and elsewhere.status_code == 403 and 'another computer' in msg(elsewhere)
              and wrong.status_code == 403 and by_pw['opened_with'] == 'password' and by_words['opened_with'] == 'recovery key'
              and bad_words.status_code == 403)

        # B1: tampering is caught, and nothing is restored
        tampered = server._backups_dir() / 's209_tampered.gwbk'
        tb = bytearray(blob); tb[-10] ^= 0x01
        tampered.write_bytes(bytes(tb))
        with db_session() as s:
            s.add(Transaction(date=date.today(), amount=1.23, type='debit', description='S209 KEEP ME', merchant='S209 KEEP ME')); s.commit()
        chk = post('/api/backup/check', {'filename': tampered.name})
        res = post('/api/backup/restore', {'filename': tampered.name})
        with db_session() as s:
            kept = s.query(Transaction).filter_by(description='S209 KEEP ME').count()
        check('s209 B1 a damaged or altered backup says so and is never restored; the live data is untouched',
              chk.status_code == 422 and 'changed or damaged' in msg(chk) and res.status_code == 400 and kept == 1)
        tampered.unlink()

        # B4: restoring a sealed backup brings the data back (the row added after it goes)
        rst = post('/api/backup/restore', {'filename': made['filename']})
        with db_session() as s:
            gone = s.query(Transaction).filter_by(description='S209 KEEP ME').count()
        check('s209 B4 restoring here needs nothing typed, and brings back exactly what was backed up',
              rst.status_code == 200 and gone == 0 and c.get('/api/health', headers=H).status_code == 200)

        # an uploaded sealed backup from "another computer"
        bc.VAULT = bc.MemoryVault()
        up1 = c.post('/api/backup/restore-upload', headers=H, data={'file': (io.BytesIO(blob), 'from_old_pc.gwbk')},
                     content_type='multipart/form-data')
        up2 = c.post('/api/backup/restore-upload', headers=H, data={'file': (io.BytesIO(blob), 'from_old_pc.gwbk'),
                     'password': 'first password 01'}, content_type='multipart/form-data')
        bc.VAULT = vault
        check('s209 B4 a backup file brought from another computer opens there only with its password (or words), and is kept sealed',
              up1.status_code == 403 and up2.status_code == 200 and data(up2)['filename'].endswith('.gwbk'))

        # B6: changing the password, and replacing the words, strands nothing
        import time
        chg = post('/api/backup/protect/password', {'new_password': 'second password 02'})
        time.sleep(1.1)
        made2 = data(c.post('/api/backup/create', headers=HJ, data='{}'))
        rec = data(post('/api/backup/protect/recovery', {}))
        c.post('/api/backup/protect/confirm', headers=HJ, data='{}')
        time.sleep(1.1)
        made3 = data(c.post('/api/backup/create', headers=HJ, data='{}'))
        bc.VAULT = bc.MemoryVault()
        o_old = post('/api/backup/check', {'filename': made['filename'], 'password': 'first password 01'}).status_code
        o_new = post('/api/backup/check', {'filename': made2['filename'], 'password': 'second password 02'}).status_code
        o_oldw = post('/api/backup/check', {'filename': made2['filename'], 'words': words}).status_code
        o_neww = post('/api/backup/check', {'filename': made3['filename'], 'words': rec['words']}).status_code
        o_stale = post('/api/backup/check', {'filename': made3['filename'], 'words': words}).status_code
        bc.VAULT = vault
        check('s209 B6 a new password or new words never strand an older backup: each opens with what it was made with',
              chg.status_code == 200 and o_old == 200 and o_new == 200 and o_oldw == 200 and o_neww == 200 and o_stale == 403)

        # B8: only this computer can set a new password and words
        bc.VAULT = bc.MemoryVault()
        not_here = post('/api/backup/protect/reset', {'new_password': 'third password 03'})
        bc.VAULT = vault
        reset = post('/api/backup/protect/reset', {'new_password': 'third password 03'})
        check('s209 B8 forgot the password and lost the words: this computer can set new ones; no other computer can',
              not_here.status_code == 403 and reset.status_code == 200 and len(data(reset)['words']) == 24)
        c.post('/api/backup/protect/confirm', headers=HJ, data='{}')

        # B7: old plain backups
        plain = server._backups_dir() / 'groundwork_backup_20200101_000000.db'
        from core.database import DB_PATH
        plain.write_bytes(Path(DB_PATH).read_bytes())
        listed = {b['filename']: b['encrypted'] for b in data(c.get('/api/backup/list', headers=H))}
        resave = data(post('/api/backup/encrypt-old', {'filename': plain.name}))
        still = plain.exists()
        dele = post('/api/backup/delete', {'filename': plain.name})
        check('s209 B7 an old plain backup is marked, re-saved sealed on a tap, and kept until the person deletes it',
              listed.get(plain.name) is False and listed.get(made['filename']) is True
              and resave['filename'].endswith('.gwbk') and still and dele.status_code == 200 and not plain.exists())
        (server._backups_dir() / resave['filename']).unlink()

        # B9: no key in the log, and nothing here can send one
        logtxt = (Path(DATA_DIR) / 'groundwork.log').read_text(encoding='utf-8', errors='replace') if (Path(DATA_DIR) / 'groundwork.log').exists() else ''
        src = (ctx.BASE / 'core' / 'backup_crypto.py').read_text(encoding='utf-8')
        check('s209 B9 no key reaches the log, and the backup code has no way to send anything',
              base64.b64encode(vault.get()).decode() not in logtxt and ' '.join(rec['words']) not in logtxt
              and not any(w in src for w in ('requests', 'urllib', 'http', 'socket')))
        app = ctx.app_src
        check('s209 B3 the page sets protection up once: the words shown once, printable, three typed back to confirm',
              'Protect your backups' in app and 'Groundwork will not show it again and does not keep it' in app
              and 'backupPrintWords' in app and 'Check that you saved it' in app and "slice(0, 3)" in app
              and 'id="backupProtect"' in ctx.html_src and 'accept=".db,.gwbk"' in ctx.html_src)
        # Rob 2026-10-12: Print came out blank - the app-wide print rule hides every window that is not a report, and
        # the words were inside the Backups window. They print from their own sheet at the top of the page now.
        html = ctx.html_src
        body_level = html.rsplit('<div id="bkPrintSheet"></div>', 1)
        check('s209 B3 the recovery key prints: from its own sheet outside every window, which the print rules let through',
              len(body_level) == 2 and '</body>' in body_level[1] and body_level[1].index('</body>') < 200
              and 'body.bk-printing > *:not(#bkPrintSheet){display:none!important}' in html
              and ':not(#gwFeedbackModal):not(#bkPrintSheet){display:none!important}' in html
              and "const sheet = g('bkPrintSheet');" in app and "sheet.innerHTML = ''" in app)
        # Rob 2026-10-12: Settings' backup card and the top bar's Backups window had drifted apart. One window holds
        # everything; Settings shows the same protection state, and its Create opens that window when setup is needed.
        settings = html.split('id="settingsPanel-data"')[1].split('Danger Zone')[0]
        modal = html.split('id="backupModal"')[1].split('</div>\n</div>')[0]
        sbs = app.split('async function renderSettingsBackupStatus() {')[1].split('\n}\n')[0]
        cb = app.split('async function createBackup(password) {')[1].split('\n}\n')[0]
        check('s209 Settings and the Backups window agree: the same protection state, the same location in both, and Create opens the window when protection is needed',
              'id="settingsBackupStatus"' in settings and "/api/backup/protect" in sbs and 'st.confirmed' in sbs
              and 'bk-loc-path' in settings and 'bk-loc-path' in modal and 'id="backupLocationPath"' not in html
              and 'openBackupModal();' in cb and 'renderSettingsBackupStatus();' in app.split('async function loadBackupList() {')[1][:200])
        for f in server._backups_dir().glob('*.gwbk'):
            if f.name in (made['filename'], made2['filename'], made3['filename']) or f.name.startswith('restored_'):
                f.unlink()
    finally:
        bc.VAULT = old_vault
        with db_session() as s:
            s.query(AppSetting).filter_by(key=bc.SETTING).delete(); s.commit()
