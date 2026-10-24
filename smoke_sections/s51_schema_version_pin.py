"""A migration change must come with a SCHEMA_VERSION bump - or every upgraded database crashes.

migrate.run_migration_if_needed skips EVERY step while the database's stored schema_version equals
migrate.SCHEMA_VERSION. So a new column, index, seed or step that ships without a bump is never applied to an
existing database, while the models already query it - and the app crashes on its first read. It happened twice
in a week: the bank window's portal_url columns on master (caught while building), then V2's interest_rate_source
and minimum_payment_source on lts/1.x, where every 1.1 user's database stores '20260725-byb' and
/api/settings/bootstrap returned 500 after the upgrade (measured, 2026-09-26). The gate could not see either,
because every smoke run starts from a fresh database, which the migration builds from scratch.

This section closes the blind spot by pinning. migrate.py carries SCHEMA_SPEC_SHA256 beside SCHEMA_VERSION: a
fingerprint of migrate.py's code (its AST - comments, docstrings and formatting do not count; the pin lines
themselves are excluded). Since item 24 (2026-10-03) it also carries SCHEMA_MODELS_SHA256, a fingerprint of the models'
tables and columns, because migrate.py's fingerprint cannot see core/database.py - a new model table needs a bump
too (P1). s67 upgrades real old-schema fixtures, the only check that sees an unlisted column (P2). Change anything the migration does and the fingerprint moves, and this section fails
until BOTH lines are updated: a new SCHEMA_VERSION, and the new fingerprint, which the failure prints.

It guards against forgetting, not against someone who updates the fingerprint and not the version - the failure
message says which two lines to change, and in which order, so the easy fix is the right one.

Then the case that shows what the pin protects: a database stored at the previous version really does gain a
column the current migration adds (the mechanism the bump relies on).
"""
import ast
import hashlib

_PIN_NAMES = ('SCHEMA_VERSION', 'SCHEMA_SPEC_SHA256', 'SCHEMA_MODELS_SHA256')


def schema_models_sha256(metadata):
    """SHA-256 of the models' schema: every table, and each column's name, type, nullability and key (item 24, P1).

    migrate.py's fingerprint cannot see core/database.py, and a new model TABLE is created only inside the migration
    that a matching SCHEMA_VERSION skips. So the models get their own pin: change a table or a column and this moves.
    """
    import json as _json
    parts = []
    for name in sorted(metadata.tables):
        cols = sorted((c.name, str(c.type), bool(c.nullable), bool(c.primary_key)) for c in metadata.tables[name].columns)
        parts.append([name, cols])
    return hashlib.sha256(_json.dumps(parts).encode('utf-8')).hexdigest()


def schema_spec_sha256(source):
    """SHA-256 of migrate.py's AST, without its docstrings and without the two pin assignments."""
    tree = ast.parse(source)
    tree.body = [n for n in tree.body
                 if not (isinstance(n, ast.Assign)
                         and any(getattr(t, 'id', None) in _PIN_NAMES for t in n.targets))]
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if (isinstance(body, list) and body and isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], 'value', None), ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:] or [ast.Pass()]
    return hashlib.sha256(_stable_dump(tree).encode('utf-8')).hexdigest()


def _stable_dump(node):
    """The AST as text that reads the same on every Python (panel I-08): ast.dump's own text moved between 3.12 and 3.13,
    which began leaving out empty and None fields, so the pin failed on 3.13 with nothing changed. Here every node is
    its class and its set fields, by name, always - and a field a newer Python adds, unset (None, [], or a 0/False flag
    such as 3.15's Import.is_lazy), leaves no trace. A literal's value is always kept: 0 and None are different code."""
    import json as _json

    def walk(n):
        if isinstance(n, ast.AST):
            out = [type(n).__name__]
            for f in n._fields:
                v = getattr(n, f, None)
                if v is None or v == []:
                    continue
                if isinstance(v, (bool, int)) and not v and not (isinstance(n, ast.Constant) and f == 'value'):
                    continue                        # an unset flag (3.15's Import.is_lazy = 0); a literal 0 still counts
                out.append([f, walk(v)])
            return out
        if isinstance(n, list):
            return [walk(x) for x in n]
        return repr(n)
    return _json.dumps(walk(node))


def run(ctx):
    check = ctx.check
    import migrate
    src = ctx.BASE.joinpath('migrate.py').read_text(encoding='utf-8')
    actual = schema_spec_sha256(src)
    pinned = getattr(migrate, 'SCHEMA_SPEC_SHA256', None)
    ok = actual == pinned
    check('s51 migrate.py matches the fingerprint pinned beside SCHEMA_VERSION (a migration change came with a bump)', ok)
    if not ok:
        print('        migrate.py changed since SCHEMA_VERSION was last bumped. Existing databases will SKIP the change.')
        print(f'        1. set SCHEMA_VERSION to a new value (currently {migrate.SCHEMA_VERSION!r})')
        print(f'        2. set SCHEMA_SPEC_SHA256 = {actual!r}')

    # The fingerprint ignores what cannot change a migration, and sees what can.
    comment_only = src.replace('\ndef _add_missing_columns', '\n# a comment that changes nothing\ndef _add_missing_columns', 1)
    check('s51 a comment-only edit does not move the fingerprint',
          comment_only != src and schema_spec_sha256(comment_only) == actual)
    bumped = src.replace(f'SCHEMA_VERSION = {migrate.SCHEMA_VERSION!r}', "SCHEMA_VERSION = 'a-new-version'", 1)
    check('s51 bumping SCHEMA_VERSION alone does not move the fingerprint (the pin is the code, not the name)',
          bumped != src and schema_spec_sha256(bumped) == actual)

    # Mutations: the two ways the bug happened must both be caught.
    new_column = src.replace('_NEW_DEBT_COLUMNS = [', "_NEW_DEBT_COLUMNS = [\n    ('s51_probe_column', 'VARCHAR(4)'),", 1)
    check('s51 mutation caught: a column added without a bump',
          new_column != src and schema_spec_sha256(new_column) != pinned)
    new_step = src.replace('def run_migration_if_needed():', 'def run_migration_if_needed():\n    _s51_new_seed_step = True', 1)
    check('s51 mutation caught: a migration step added without a bump',
          new_step != src and schema_spec_sha256(new_step) != pinned)

    # ── P1 (item 24): the models are pinned too ──────────────────────────────
    from core import database as _d
    models_actual = schema_models_sha256(_d.Base.metadata)
    models_pinned = getattr(migrate, 'SCHEMA_MODELS_SHA256', None)
    check('s51 the models match the fingerprint pinned beside SCHEMA_VERSION (a model change came with a bump)',
          models_actual == models_pinned)
    if models_actual != models_pinned:
        print('        core/database.py changed since SCHEMA_VERSION was last bumped. A new table never reaches an existing')
        print('        database without a bump, and a new column needs listing in a _NEW_*_COLUMNS list as well.')
        print(f'        1. set SCHEMA_VERSION to a new value (currently {migrate.SCHEMA_VERSION!r})')
        print('        2. list any new column on an existing table in its _NEW_*_COLUMNS list (create_all never alters one)')
        print(f'        3. set SCHEMA_MODELS_SHA256 = {models_actual!r} (and SCHEMA_SPEC_SHA256 as printed above)')
        print('        4. python schema_fixture.py   (saves the new version\'s schema; the gate upgrades it from then on)')
    import copy as _copy
    from sqlalchemy import Column as _Col, Integer as _Int, MetaData as _Meta, String as _Str, Table as _Tab
    meta2 = _Meta()
    for t in _d.Base.metadata.tables.values():
        t.to_metadata(meta2)
    _Tab('s51_probe_table', meta2, _Col('id', _Int, primary_key=True))
    check('s51 mutation caught: a model table added without a bump', schema_models_sha256(meta2) != models_pinned)
    meta3 = _Meta()
    for t in _d.Base.metadata.tables.values():
        t.to_metadata(meta3)
    meta3.tables['accounts'].append_column(_Col('s51_probe_column', _Str(4)))
    check('s51 mutation caught: a model column added without a bump', schema_models_sha256(meta3) != models_pinned)

    # What the bump buys: a database stored at an older version gains a listed column on start.
    from sqlalchemy import text
    from core.database import engine
    col = migrate._NEW_DEBT_COLUMNS[-1][0]

    def cols():
        with engine.connect() as conn:
            return {r[1] for r in conn.execute(text('PRAGMA table_info(debt_accounts)'))}

    with engine.begin() as conn:
        if col in cols():
            conn.execute(text(f'ALTER TABLE debt_accounts DROP COLUMN {col}'))
        conn.execute(text("UPDATE app_settings SET value = 's51-an-older-version' WHERE key = 'schema_version'"))
    dropped = col not in cols()
    migrate.run_migration_if_needed()
    check(f's51 a database at an older SCHEMA_VERSION gains a listed column on start ({col})',
          dropped and col in cols())
