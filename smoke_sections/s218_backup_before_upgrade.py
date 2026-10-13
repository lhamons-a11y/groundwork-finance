"""Item 82 R3 (gw 2.0/RELEASE_2_0.md; item 32 L3b, ruled 2026-10-04; built 2026-10-12, Rob: "yes").

Before a database whose recorded schema differs from this build's is migrated - 1.1 opened by 2.0, or any later
upgrade - a dated copy is written through the backup function, and never deleted:
    sealed when backup protection is set up (item 81 B1), plain only when it is not, as every safety copy is
    no copy when the schema is already current, or the database holds no records
    the copy's name and folder are kept, and the app says once where it is
"""
import json
from datetime import date


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import migrate
    import server
    from core import backup_crypto as bc
    from core.database import AppSetting, Transaction, db_session

    def stored(v):
        with db_session() as s:
            s.query(AppSetting).filter_by(key='schema_version').delete()
            if v is not None:
                s.add(AppSetting(key='schema_version', value=v))
            s.commit()

    folder = server._backups_dir()
    made = []
    with db_session() as s:
        s.add(Transaction(date=date(2026, 1, 2), amount=1.0, type='debit', merchant='S218 KEEP', description='S218 KEEP'))
        s.query(AppSetting).filter_by(key='pre_upgrade_backup').delete()
        s.commit()
    try:
        stored(migrate.SCHEMA_VERSION)
        none = server._backup_before_migration()
        before = set(p.name for p in folder.iterdir())
        stored('20260725-byb')                                   # v1.1.0's released schema
        rec = server._backup_before_migration()
        made += [rec.get('name')] if rec and rec.get('name') else []
        plain_file = folder / (rec or {}).get('name', 'none')
        check(f"s218 R3 an upgrade writes a dated copy first, kept in the backups folder; a current schema writes none ({(rec or {}).get('name')})",
              none is None and rec and rec.get('from') == '20260725-byb' and rec.get('to') == migrate.SCHEMA_VERSION
              and rec['name'].endswith('_before_upgrade.db') and plain_file.exists() and plain_file.name not in before
              and rec['sealed'] is False and rec['folder'] == str(folder))
        old = bc.test_protect(c, HJ)
        try:
            sealed = server._backup_before_migration()
            made += [sealed.get('name')] if sealed and sealed.get('name') else []
            blob = (folder / sealed['name']).read_bytes()
        finally:
            bc.test_unprotect(old)
        check('s218 R3 / item 81 B1 with backup protection set up, the copy is sealed like every other backup',
              sealed['name'].endswith('_before_upgrade.gwbk') and sealed['sealed'] is True and blob[:6] == b'GWBK1\n')
        g = (c.get('/api/backup/pre-upgrade', headers=H).get_json() or {}).get('data') or {}
        c.post('/api/backup/pre-upgrade', headers=HJ, data='{}')
        g2 = (c.get('/api/backup/pre-upgrade', headers=H).get_json() or {}).get('data') or {}
        check('s218 R3 the app is told once where the copy is: shown, then marked shown; the copy itself is untouched',
              g.get('name') == sealed['name'] and g.get('shown') is False and g2.get('shown') is True
              and (folder / sealed['name']).exists())
    finally:
        stored(migrate.SCHEMA_VERSION)
        for n in made:
            try:
                (folder / n).unlink()
            except OSError:
                pass
        with db_session() as s:
            s.query(Transaction).filter_by(merchant='S218 KEEP').delete()
            s.query(AppSetting).filter_by(key='pre_upgrade_backup').delete()
            s.commit()

    src = ctx.server_src
    boot = src.split('_backup_before_migration()\n    run_migration_if_needed()')
    helper = src.split('def _backup_before_migration():')[1].split('\ndef ')[0]
    app = ctx.app_src
    check('s218 R3 the copy is written before the migration at startup, never deletes, skips an empty database, and is said on the page',
          len(boot) == 2 and 'if not held:' in helper and '_write_backup(' in helper and 'unlink' not in helper
          and '_preUpgradeNotice();   // item 82 R3' in app and 'Groundwork never deletes it' in app)
