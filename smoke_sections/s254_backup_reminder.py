"""The backup reminder (Rob 2026-10-22, after Quicken's "you have not backed up since"):

    each backup the person makes records its date - so a backup on a drive that is unplugged still counts
    due when the last one is 7 days old (or 3 / 14 / 30, their choice) AND records were added since; never backed up,
    due once there are transactions; never for the sample household
    a Needs attention item: Back up now (Settings > Data & Backup) and Remind me later (three days)
    after an upgrade migrates the database, the migrated database is backed up too, and counts as the latest
"""
import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import server
    from core import sample_household as sh
    from core.database import AppSetting, Transaction, db_session

    keys = ('backup_last', 'backup_remind_days', 'backup_remind_snooze', sh.SAMPLE_FLAG)
    with db_session() as s:
        saved = {k: (r.value if (r := s.query(AppSetting).filter_by(key=k).first()) else None) for k in keys}
        for k in keys:
            s.query(AppSetting).filter_by(key=k).delete()
        s.add(Transaction(date=datetime.now().date(), amount=12.34, type='debit', merchant='S254 COFFEE',
                          description='S254 COFFEE'))
        s.commit()

    def put(k, v):
        with db_session() as s:
            server._set_setting(s, k, json.dumps(v))
            s.commit()

    def rem():
        return (c.get('/api/backup/reminder', headers=H).get_json() or {}).get('data') or {}

    put('backup_last', server._backup_stamp('groundwork_backup_s254.gwbk', time.time() - 8 * 86400))
    r = rem()
    a = (r.get('attention') or [{}])[0]
    check(f"s254 a backup 8 days old with records added since is due, saying when and how many ({a})",
          r.get('due') and r.get('every') == 7 and a.get('days') == 8 and a.get('transactions', 0) >= 1
          and a.get('last') == r['last']['at'][:10])

    put('backup_last', server._backup_stamp('groundwork_backup_s254.gwbk'))
    now_r = rem()
    with db_session() as s:
        later = server._backup_reminder(s, now=datetime.now() + timedelta(days=8))
    check(f"s254 nothing added since the last backup: no reminder, however old - and a record made before the backup "
          f"isn't counted as after it, in any time zone (added {now_r.get('added')}, 8 days on {later['added']})",
          now_r.get('added') == {'transactions': 0, 'other': 0} and not later['due'] and later['days_since'] == 8)

    put('backup_last', server._backup_stamp('groundwork_backup_s254.gwbk', time.time() - 8 * 86400))
    e14 = c.post('/api/backup/reminder/every', headers=HJ, data=json.dumps({'days': 14}))
    r14 = rem()
    bad = c.post('/api/backup/reminder/every', headers=HJ, data=json.dumps({'days': 9}))
    c.post('/api/backup/reminder/every', headers=HJ, data=json.dumps({'days': 7}))
    check('s254 the interval is the person\'s: 14 days makes an 8-day-old backup not due yet; only 3, 7, 14 or 30',
          e14.status_code == 200 and not r14.get('due') and r14.get('every') == 14 and bad.status_code == 400
          and r14.get('choices') == [3, 7, 14, 30])

    sn = c.post('/api/backup/reminder/snooze', headers=H)
    rs = rem()
    check(f"s254 Remind me later rests it for three days, then it can come back ({rs.get('snoozed_until')})",
          sn.status_code == 200 and not rs.get('due')
          and rs.get('snoozed_until') == (datetime.now().date() + timedelta(days=3)).isoformat())
    with db_session() as s:
        s.query(AppSetting).filter_by(key='backup_remind_snooze').delete()
        s.commit()

    put(sh.SAMPLE_FLAG, 'true')
    with db_session() as s:
        s.query(AppSetting).filter_by(key=sh.SAMPLE_FLAG).update({'value': 'true'})
        s.commit()
    rsm = rem()
    with db_session() as s:
        s.query(AppSetting).filter_by(key=sh.SAMPLE_FLAG).delete()
        s.commit()
    check('s254 never for the sample household', not rsm.get('due'))

    real_dir = server._backups_dir
    empty = Path(tempfile.mkdtemp(prefix='s254_'))
    try:
        server._backups_dir = lambda: empty
        with db_session() as s:
            s.query(AppSetting).filter_by(key='backup_last').delete()
            s.commit()
        never = rem()
        (empty / 'groundwork_backup_20261001_090000.gwbk').write_bytes(b'x')
        (empty / 'groundwork_backup_pre-delete-all_20261020_090000.gwbk').write_bytes(b'x')
        with db_session() as s:
            s.query(AppSetting).filter_by(key='backup_last').delete()
            s.commit()
        found = rem()
        rec = server._backup_after_migration({'name': 'groundwork_backup_x_before_upgrade.gwbk'}) or None
        with db_session() as s:
            after = json.loads(s.query(AppSetting).filter_by(key='backup_last').first().value)
            pre = json.loads((s.query(AppSetting).filter_by(key='pre_upgrade_backup').first() or AppSetting(value='{}')).value)
        made = sorted(f.name for f in empty.iterdir() if 'after_upgrade' in f.name)
    finally:
        server._backups_dir = real_dir
    check(f"s254 never backed up, with transactions: due, saying so ({(never.get('attention') or [{}])[0]})",
          never.get('due') and (never.get('attention') or [{}])[0].get('last') is None and rec is None)
    check(f"s254 backups made before dates were recorded count: the newest of the person's own files, never a safety "
          f"copy ({found.get('last', {}).get('file')})",
          (found.get('last') or {}).get('file') == 'groundwork_backup_20261001_090000.gwbk'
          and (found.get('last') or {}).get('from_file'))
    check(f"s254 after an upgrade migrates the database, the migrated one is backed up too and is the latest ({made})",
          len(made) == 1 and after.get('after_upgrade') and after.get('file') == made[0] and 'utc' in after
          and pre.get('after_name') == made[0])

    src = ctx.server_src
    att = (ctx.BASE / 'static' / 'js' / 'teaching' / 'attention.js').read_text(encoding='utf-8')
    dash = (ctx.BASE / 'static' / 'js' / 'teaching' / 'dashboard.js').read_text(encoding='utf-8')
    app = ctx.app_src
    check('s254 the wiring: each backup the person makes records its date; the upgrade copies it after migrating; '
          'Needs attention offers Back up now (Settings > Data & Backup) and Remind me later; Settings shows the last '
          'backup and the choice; the upgrade note names both copies',
          "_set_setting(session, 'backup_last', json.dumps(_backup_stamp(backup_name)))" in src
          and '_backup_after_migration(_pre)' in src and "'backup_due'" in att and 'backupDue: backupDue' in att
          and "_settingsShowTab(\\'data\\')\">Back up now</button>" in dash and 'data-gw-backup-later' in dash
          and "'/api/backup/reminder/snooze'" in dash and 'function _backupReminderLine(r)' in app
          and "'/api/backup/reminder/every'" in app and 'r.after_name' in app)

    with db_session() as s:
        s.query(Transaction).filter_by(merchant='S254 COFFEE').delete()
        for k in keys:
            s.query(AppSetting).filter_by(key=k).delete()
            if saved[k] is not None:
                s.add(AppSetting(key=k, value=saved[k]))
        s.commit()
