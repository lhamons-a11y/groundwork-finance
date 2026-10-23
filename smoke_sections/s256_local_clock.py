"""Item 109 (gw 2.0/LOCAL_CLOCK.md; Rob 2026-10-22: "write it, push it build it. We have ran into this issue multiple
times now lets fully fix it throughout the program"): one clock - the computer's own local date and time.

    T1  every day and month from the local calendar; T2 every moment written in local time
    T3  what was stored in UTC converted once, each moment by its own offset; a new database is only marked
    T5  comparisons follow (the backup reminder by its local `at`)     T6 a stored YYYY-MM-DD is a local day
    T7  UTC can't quietly come back: no utcnow / utcfromtimestamp / timezone.utc in the server, the engines or the
        migration, and no toISOString() picking a day or month in the page
"""
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone

# A place that genuinely needs UTC is named here, by its code, with its reason (T7).
ALLOWED_UTC = {('migrate.py', 'return v.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)'):
               'T3 converts what was stored in UTC, so it has to say UTC'}


def run(ctx):
    check, base = ctx.check, ctx.BASE
    import migrate

    # ── T7: nothing left behind ──────────────────────────────────────────────────────────────────────────────────
    py = [base / 'server.py', base / 'migrate.py', base / 'launch.py'] + sorted((base / 'core').glob('*.py'))
    utc = []
    for f in py:
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            code = line.split('#', 1)[0]
            if re.search(r'\butcnow\b|\butcfromtimestamp\b|timezone\.utc', code) and (f.name, code.strip()) not in ALLOWED_UTC:
                utc.append(f'{f.name}:{i}')
    check(f's256 T7 no UTC clock in the server, the engines or the migration ({utc[:6]})', not utc)
    js = [base / 'static/js/app.js'] + sorted((base / 'static/js/teaching').glob('*.js'))
    iso = []
    for f in js:
        for i, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            code = line.split('//', 1)[0]
            if re.search(r'toISOString\(\)', code):
                iso.append(f'{f.name}:{i}')
    check(f's256 T7 no toISOString() in the page - a day or month is the local one, a moment is _localStamp() ({iso[:6]})',
          not iso)
    app = ctx.app_src
    check('s256 T1/T6 the page\'s clock: _localISODate (the local calendar), _localStamp (local, no zone), _localDay '
          '(a stored YYYY-MM-DD is a local day), and today() uses the first',
          'function _localISODate(d = new Date())' in app and 'd.getFullYear()' in app
          and 'function today() { return _localISODate(); }' in app and 'function _localStamp(' in app
          and 'function _localDay(s)' in app and '_localDay(card.endDate)' in app)
    from core import database
    defaults = [c.default.arg for t in database.Base.metadata.sorted_tables for c in t.columns
                if c.default is not None and callable(getattr(c.default, 'arg', None))]
    check('s256 T2 every stamped column\'s default is the local clock',
          defaults and all(getattr(d, '__name__', '') != 'utcnow' for d in defaults))

    # ── T3: the conversion ───────────────────────────────────────────────────────────────────────────────────────
    jan, jul = datetime(2026, 1, 15, 2, 30), datetime(2026, 7, 15, 2, 30)
    lj = jan.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
    lu = jul.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
    off = lambda a, b: round((b - a).total_seconds() / 3600, 2)
    check(f's256 T3 each moment moves by its own offset (January {off(jan, migrate._utc_to_local(jan))} h, '
          f'July {off(jul, migrate._utc_to_local(jul))} h on this computer)',
          migrate._utc_to_local(jan) == lj and migrate._utc_to_local(jul) == lu)
    st = migrate._clock_local_settings({'payee': [{'month': '2026-01', 'at': '2026-01-15T02:30:00'}],
                                        'saved': '2026-07-15T02:30:00.123456', 'note': '2026-01-15T02:30:00',
                                        'fetched_at': 'not a date'})
    check('s256 T3 settings: `at`, `saved` and `fetched_at` move, other text stays',
          st['payee'][0]['at'] == lj.isoformat(timespec='seconds') and st['saved'] == lu.replace(microsecond=123456).isoformat()
          and st['note'] == '2026-01-15T02:30:00' and st['fetched_at'] == 'not a date'
          and migrate._utc_iso_to_local('2026-01-15') == '2026-01-15')

    # on a database: one planted UTC row moves; a never-UTC column stays; it runs once; a new database is only marked
    from core.database import AppSetting, BillReading, Category, HistorianEntry, db_session
    from sqlalchemy import text
    with db_session() as s:
        s.query(AppSetting).filter_by(key=migrate._CLOCK_FLAG).delete()
        cat = Category(name='s256 clock', type='expense', created_at=jan)
        s.add(cat); s.flush()
        cid = cat.id
        br_cols = {c.name for c in BillReading.__table__.columns}
        s.commit()
    try:
        moved = migrate._clock_local_v109(True)
        again = migrate._clock_local_v109(True)
        with db_session() as s:
            got = s.get(Category, cid).created_at
            logged = s.query(HistorianEntry).filter_by(event_category='clock_local').count()
            s.query(AppSetting).filter_by(key=migrate._CLOCK_FLAG).delete(); s.commit()
        fresh = migrate._clock_local_v109(False)
        with db_session() as s:
            got2 = s.get(Category, cid).created_at
            marked = s.query(AppSetting).filter_by(key=migrate._CLOCK_FLAG).first() is not None
        check(f's256 T3 a stored UTC moment becomes the same instant in local time, once ({jan} -> {got}; moved {moved}, '
              f'then {again})', got == lj and again == 0 and logged >= 1)
        check('s256 T3 a new database is only marked: nothing in it was ever UTC', fresh == 0 and got2 == lj and marked)
        check('s256 T3 the two columns that were never UTC are left as they are',
              ('bill_readings', 'read_at') in migrate._CLOCK_NOT_UTC and ('debt_accounts', 'paid_off_at') in migrate._CLOCK_NOT_UTC
              and 'read_at' in br_cols)
    finally:
        with db_session() as s:
            s.query(Category).filter(Category.id == cid).delete()
            if not s.query(AppSetting).filter_by(key=migrate._CLOCK_FLAG).first():
                s.add(AppSetting(key=migrate._CLOCK_FLAG, value='1'))
            s.commit()
    src = (base / 'migrate.py').read_text(encoding='utf-8')
    check('s256 T3 it runs first in the migration, before anything else that run writes a local time',
          src.index('_clock_local_v109(had_version)') < src.index("_add_missing_columns('transactions'")
          and "SCHEMA_VERSION = '20261022-local-clock'" in src)

    # ── T5: the backup reminder compares local with local ────────────────────────────────────────────────────────
    srv = ctx.server_src
    rem = srv[srv.index('def _backup_reminder('):srv.index('def _backup_reminder(') + 1400]
    check('s256 T5 the backup reminder counts what was added after the backup by its local time; no UTC copy is written',
          'model.created_at > since' in rem and "'utc':" not in srv[srv.index('def _backup_stamp('):srv.index('def _backup_last(')])

    # ── T1 in Node: 11:30 pm Eastern on Oct 31 is still Oct 31, and October ──────────────────────────────────────
    if shutil.which('node'):
        body = app[app.index('function _localISODate('):app.index('function today()')]
        js_src = (body + "\nconst d = new Date(2026, 9, 31, 23, 30);"
                  "console.log(JSON.stringify([_localISODate(d), _localISODate(d).slice(0, 7), _localStamp(d)]));")
        r = subprocess.run(['node', '-e', js_src], capture_output=True, text=True, env={**os.environ, 'TZ': 'America/New_York'})
        out = json.loads(r.stdout or 'null')
        check(f's256 T1 in Node (TZ America/New_York): 11:30 pm on Oct 31 is Oct 31 and October ({out})',
              out == ['2026-10-31', '2026-10', '2026-10-31T23:30:00'])
