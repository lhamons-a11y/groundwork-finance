"""Item 84 (gw 2.0/FUEL_NAMES_2.md; Rob 2026-10-13: "open as item 84, when pass accept, build").

    F1  fill-ups are "Gasoline / Diesel" (was Gas / Fuel)
    F2  the natural-gas utility is "Natural Gas" (was Gas, under Utilities); a stray top-level "Gas" is left alone
    F3  public charging has its own "EV Charging" under Transportation: card code 5552 and the charging networks
    F4  an existing database is updated once, in place: the categories and every stored copy of their names
    F5  rows older rules filed elsewhere are offered to EV Charging, shown first, moved only on a yes
"""
import json
import sqlite3
import tempfile
from pathlib import Path


def run(ctx):
    check = ctx.check
    import bank_importer as bi
    import migrate
    app = ctx.app_src

    ans = {d: bi.auto_category(d, m) for d, m in [('NAYAX EV VEHICL HUNT VALLEY', ''), ('ANY MERCHANT', '5552'),
                                                    ('CHARGEPOINT INC', ''), ('ELECTRIFY AMERICA 123', ''),
                                                    ('CLARK GAS #12', ''), ('COLUMBIA GAS OF OHIO', '')]}
    check(f"s224 F1-F3 the importer files charging, fill-ups and the gas bill each where it belongs ({ans})",
          ans['NAYAX EV VEHICL HUNT VALLEY'] == 'EV Charging' and ans['ANY MERCHANT'] == 'EV Charging'
          and ans['CHARGEPOINT INC'] == 'EV Charging' and ans['ELECTRIFY AMERICA 123'] == 'EV Charging'
          and ans['CLARK GAS #12'] == 'Gasoline / Diesel' and ans['COLUMBIA GAS OF OHIO'] == 'Natural Gas')
    check("s224 F3 the page's own matcher and card-code map agree with the importer",
          "'5552': 'EV Charging'" in app and "return 'EV Charging';" in app and "return 'Natural Gas';" in app
          and "'Gas / Fuel'" not in app)
    from core.database import CATEGORY_TREE
    names = {(t[0], t[4]) for t in CATEGORY_TREE}
    check('s224 F1-F3 a new database gets Gasoline / Diesel and EV Charging under Transportation, Natural Gas under Utilities',
          ('Gasoline / Diesel', 'Transportation') in names and ('EV Charging', 'Transportation') in names
          and ('Natural Gas', 'Utilities') in names and not any(t[0] in ('Gas', 'Gas / Fuel') for t in CATEGORY_TREE))

    # F4 on an old database: build one with the old names and stored copies, run the update twice
    tmp = Path(tempfile.mkdtemp()) / 'old.db'
    con = sqlite3.connect(tmp)
    con.executescript("""
        CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT, type TEXT, color TEXT, icon TEXT, parent_id INTEGER,
            sort_order INTEGER, is_system BOOLEAN, created_at TEXT, is_optional BOOLEAN, is_enabled BOOLEAN);
        CREATE TABLE transactions (id INTEGER PRIMARY KEY, category_id INTEGER);
        CREATE TABLE budget_items (id INTEGER PRIMARY KEY, name TEXT, category TEXT);
        CREATE TABLE willingness_declarations (id INTEGER PRIMARY KEY, category TEXT);
        CREATE TABLE app_settings (id INTEGER PRIMARY KEY, key TEXT, value TEXT);
        INSERT INTO categories (id, name, parent_id, is_system) VALUES (1, 'Transportation', NULL, 1), (2, 'Utilities', NULL, 1),
            (3, 'Gas / Fuel', 1, 1), (4, 'Gas', 2, 1), (5, 'Gas', NULL, 0);
        INSERT INTO transactions VALUES (1, 3), (2, 4), (3, 5);
        INSERT INTO budget_items VALUES (1, 'Gas / Fuel', 'Gas / Fuel'), (2, 'Heat', 'Gas');
        INSERT INTO willingness_declarations VALUES (1, 'Gas / Fuel');
        INSERT INTO app_settings (key, value) VALUES ('import_rules_json', '[{"value": "clark", "category": "Gas / Fuel"}]');
    """)
    con.commit()
    con.close()
    from sqlalchemy import create_engine
    real = migrate.engine
    migrate.engine = create_engine(f'sqlite:///{tmp}')
    try:
        migrate._fuel_names_v84()
        migrate._fuel_names_v84()          # idempotent
    finally:
        migrate.engine.dispose()
        migrate.engine = real
    con = sqlite3.connect(tmp)
    cats = dict(con.execute('SELECT id, name FROM categories').fetchall())
    ev = con.execute("SELECT parent_id FROM categories WHERE name = 'EV Charging'").fetchall()
    bl = dict(con.execute('SELECT id, category FROM budget_items').fetchall())
    wd = con.execute('SELECT category FROM willingness_declarations').fetchone()[0]
    rules = json.loads(con.execute("SELECT value FROM app_settings WHERE key = 'import_rules_json'").fetchone()[0])
    con.close()
    check(f"s224 F4 an old database is updated once, in place: the names, their rows and every stored copy; a stray top-level Gas is left ({cats})",
          cats[3] == 'Gasoline / Diesel' and cats[4] == 'Natural Gas' and cats[5] == 'Gas' and ev == [(1,)]
          and bl == {1: 'Gasoline / Diesel', 2: 'Natural Gas'} and wd == 'Gasoline / Diesel'
          and rules[0]['category'] == 'Gasoline / Diesel')
    check('s224 F4 the schema version moved with the update, so existing databases run it',
          migrate.SCHEMA_VERSION >= '20261013-fuel-names' and '_fuel_names_v84()' in ctx.BASE.joinpath('migrate.py').read_text(encoding='utf-8'))

    src = ctx.server_src.split('def _regroup_review(session):')[1].split('\n@')[0]
    check("s224 F5 charging rows are offered to EV Charging from wherever older rules left them - in the review that moves nothing without a yes",
          "by_name.get('EV Charging')" in src and "== 'EV Charging'" in src and 'groups.setdefault' in src)
