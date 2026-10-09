"""Municipal utilities, and what the bill covers (gw 2.0/MUNICIPAL_UTILITIES.md, item 56; Rob 2026-10-09: "approve
U1-U8 as recommended").

    U1  the Municipal Utilities leaf, under Utilities - and it reaches an EXISTING database (the bump runs the seed)
    U2  municipal_covers: a set of answers, kept as one sorted list with its history; asked inline only once a
        Municipal Utilities charge exists and it is unanswered
    U3  Settings shows each service on the bill, or as its own company and the category it is filed under
    U4  "city / village / town of ... utilities" and "municipal utilities" are Municipal Utilities, on both sides;
        a parking ticket or court fee is not
    U5  a bundle covering electricity or natural gas: that estimate says it can't separate it
    U6  bills already saved are offered in the review, and move only on a yes
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

UPGRADE = r"""
import json, os, sqlite3, sys
sys.path.insert(0, os.getcwd())
fixture, bump = sys.argv[1], sys.argv[2] == 'bump'
sql = open(fixture, encoding='utf-8').read()
version = sql.splitlines()[0].split(': ', 1)[1].strip()
from core import database as d
con = sqlite3.connect(str(d.DB_PATH)); con.executescript(sql)
con.execute("INSERT INTO app_settings (key, value) VALUES ('schema_version', ?)", (version,))
con.commit(); con.close()
s = d.db_session()                      # the user's categories as they were: the whole tree except the new leaf
ids = {}
for row in d.CATEGORY_TREE:
    name, ctype, color, icon, parent, sort, is_sys, is_opt = row
    if parent is None:
        c = d.Category(name=name, type=ctype, color=color, icon=icon, sort_order=sort, is_system=is_sys, is_optional=is_opt, is_enabled=True)
        s.add(c); s.flush(); ids[name] = c.id
for row in d.CATEGORY_TREE:
    name, ctype, color, icon, parent, sort, is_sys, is_opt = row
    if parent is not None and name != 'Municipal Utilities':
        s.add(d.Category(name=name, type=ctype, color=color, icon=icon, parent_id=ids[parent], sort_order=sort,
                         is_system=is_sys, is_optional=is_opt, is_enabled=True))
s.commit(); s.close()
import migrate
if not bump:
    migrate.SCHEMA_VERSION = version      # the mutation: the leaf added with no bump
migrate.run_migration_if_needed()
s = d.db_session()
m = s.query(d.Category).filter(d.Category.name == 'Municipal Utilities').first()
p = s.get(d.Category, m.parent_id).name if m and m.parent_id else None
print(json.dumps({'has': bool(m), 'parent': p}))
"""


def _fn(src, name):
    m = re.search(r'\n  function ' + name + r'\(.*?\n  \}\n', src, re.S) or re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', src, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, HJ, BASE, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE, ctx.app_src
    import bank_importer as bi
    import migrate
    from core import household
    from core.database import CATEGORY_TREE, Category, Transaction, Account, AppSetting, HouseholdFact, db_session

    row = [r for r in CATEGORY_TREE if r[0] == 'Municipal Utilities']
    check('s168 U1 Municipal Utilities is a leaf under Utilities', len(row) == 1 and row[0][4] == 'Utilities')
    check('s168 U1 the version is bumped and its schema saved', migrate.SCHEMA_VERSION == '20261009-municipal-utilities'
          and (BASE / 'tests/schema/20261009-municipal-utilities.sql').exists())

    def upgrade(mode):
        env = dict(os.environ, GROUNDWORK_DATA_DIR=tempfile.mkdtemp(prefix='gw_s168_'))
        r = subprocess.run([sys.executable, '-c', UPGRADE, str(BASE / 'tests/schema/20261008-trip-bookings.sql'), mode],
                           cwd=str(BASE), env=env, capture_output=True, text=True, encoding='utf-8', timeout=180)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                                   # noqa: BLE001
            return {'error': (r.stderr or 'no output')[-300:]}
    up = upgrade('bump')
    check(f's168 U1 an existing database (2026-10-08 schema, the old tree) gains the leaf under Utilities on upgrade {up}',
          up == {'has': True, 'parent': 'Utilities'})
    check('s168 U1 mutation caught: without the bump the existing database never gets it', upgrade('nobump') == {'has': False, 'parent': None})

    # U2: the set, its one stored form, its history
    with db_session() as s:
        before = s.query(HouseholdFact).filter_by(key='municipal_covers').count()
        household.set_household_fact(s, 'municipal_covers', 'water, trash,sewer,water', 'settings')
        v1 = household.current(s, 'municipal_covers')
        same = household.set_household_fact(s, 'municipal_covers', 'sewer,trash,water', 'settings')
        household.set_household_fact(s, 'municipal_covers', 'electricity,sewer,trash,water', 'settings')
        hist = [h['value'] for h in household.history(s, 'municipal_covers')][before:]
        bad = []
        for v in ('none,water', 'water,wifi'):
            try:
                household.set_household_fact(s, 'municipal_covers', v, 'settings'); bad.append(v)
            except household.FactError:
                pass
        s.rollback()
    check('s168 U2 the set is kept as one sorted list; the same set again records nothing; a changed set is a new row',
          v1 == 'sewer,trash,water' and same is False and hist == ['sewer,trash,water', 'electricity,sewer,trash,water'])
    check('s168 U2 "none" cannot be combined with a service, and an unknown service is refused', bad == [])

    # U4: the matcher, both sides
    lines = {'CITY OF MILLBROOK UTILITIES': 'Municipal Utilities', 'VILLAGE OF ELM GROVE UTILITIES': 'Municipal Utilities',
             'MILLBROOK CITY UTILITY BILL': 'Municipal Utilities', 'MUNICIPAL UTILITIES 12': 'Municipal Utilities',
             'CITY OF MILLBROOK PARKING': 'Parking / Tolls', 'CITY OF MILLBROOK MUNICIPAL COURT': 'Other',
             'DOWNTOWN UTILITIES CO': 'Other'}
    got = {d: bi.auto_category(d) for d in lines}
    check(f's168 U4 a municipal utility bill is Municipal Utilities; a parking ticket, a court fee and a company named Downtown are not {got}',
          got == lines and bi.auto_category('CITY OF MILLBROOK UTILITIES', '4900') == 'Municipal Utilities')
    node = shutil.which('node')
    client = _fn(app, 'clientAutoCategory')
    if node and client:
        p = subprocess.run([node, '-e', client + 'console.log(JSON.stringify(' + json.dumps(list(lines)) + '.map(clientAutoCategory)))'],
                           capture_output=True, text=True, encoding='utf-8', timeout=60)
        check('s168 U4 the page files them the same way', json.loads(p.stdout.strip() or '[]') == list(lines.values()))

    # U2 inline + U5 + U6, through the real routes
    made_t, made_a = [], []
    try:
        from datetime import date
        with db_session() as s:
            s.query(AppSetting).filter_by(key='municipal_covers').delete()
            s.commit()
            cid = {cc.name: cc.id for cc in s.query(Category).all()}
            a = Account(name='s168 Checking', type='checking', is_active=True)
            s.add(a); s.flush(); made_a.append(a.id)
            ask0 = __import__('server').utility_applies(s, 'electric').get('ask', [])
            t1 = Transaction(date=date.today(), description='CITY OF MILLBROOK UTILITIES S168', amount=83.0, type='debit',
                             account_id=a.id, category_id=cid['Municipal Utilities'])
            t2 = Transaction(date=date.today(), description='CITY OF MILLBROOK UTILITIES S168B', amount=81.0, type='debit',
                             account_id=a.id, category_id=cid['Other'])
            t3 = Transaction(date=date.today(), description='CITY OF MILLBROOK PARKING S168', amount=5.0, type='debit',
                             account_id=a.id, category_id=cid['Other'])
            s.add_all([t1, t2, t3]); s.commit(); made_t += [t1.id, t2.id, t3.id]
            ask1 = __import__('server').utility_applies(s, 'electric').get('ask', [])
        check('s168 U2 the question is asked inline only once a Municipal Utilities charge exists, and only while unanswered',
              'municipal_covers' not in ask0 and 'municipal_covers' in ask1)
        r = c.post('/api/settings/household', headers=HJ, data=json.dumps({'key': 'municipal_covers', 'value': 'electricity,trash,water', 'source': 'inline_prompt'}))
        with db_session() as s:
            el = __import__('server').utility_applies(s, 'electric')
            gs = __import__('server').utility_applies(s, 'gas')
        check('s168 U5 electricity on the municipal bill: the electricity estimate says it can\'t separate it; gas is untouched',
              r.status_code == 200 and el['applies'] is False and "on your municipal utility bill with other services" in el['why']
              and "can't separate it from the total" in el['why'] and 'municipal' not in (gs.get('why') or '')
              and 'municipal_covers' not in el.get('ask', []))
        rv = c.get('/api/categories/label-review', headers=H).get_json()['data']
        offered = {x['id']: (gp['from'], gp['to']) for gp in rv.get('regroup') or [] for x in gp['rows'] if 'S168' in x['description']}
        check('s168 U6 the bill saved in Other is offered for Municipal Utilities; the parking charge in Other is not',
              offered == {made_t[1]: ('Other', 'Municipal Utilities')})
        mv = c.post('/api/categories/label-review/move', headers=HJ, data=json.dumps({'ids': [made_t[1], made_t[2]]})).get_json()['data']
        with db_session() as s:
            after = [s.get(Transaction, i).category_id for i in made_t]
        check('s168 U6 on a yes it moves; the parking charge cannot be moved by the review',
              mv['moved'] == 1 and after == [cid['Municipal Utilities'], cid['Municipal Utilities'], cid['Other']])
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.id.in_(made_t)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made_a)).delete(synchronize_session=False)
            s.query(AppSetting).filter_by(key='municipal_covers').delete()
            s.commit()

    # U3: the Settings lines, rendered
    hh = (BASE / 'static/js/teaching/household.js').read_text(encoding='utf-8')
    if node:
        js = ('const esc = s => String(s);\n' + hh[hh.index('  var Q = {'):hh.index('  // The state is asked')]
              + _fn(hh, '_municipalServices')
              + "console.log(JSON.stringify([_municipalServices('sewer,trash,water'), _municipalServices('none'), _municipalServices('')]));")
        p = subprocess.run([node, '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=60)
        out = json.loads(p.stdout.strip() or '["","",""]')
        check('s168 U3 each service: on the municipal bill, or its own company and the category its charge is filed under',
              'Water: on your municipal utility bill' in out[0] and 'Trash: on your municipal utility bill' in out[0]
              and "Electricity: not on your municipal bill. If you pay for it, its own company's charge is filed under Electric." in out[0]
              and "Natural gas: not on your municipal bill. If you pay for it, its own company's charge is filed under Gas." in out[0]
              and out[1] == '' and out[2] == '')
