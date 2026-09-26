"""A migration change must come with a SCHEMA_VERSION bump - or every upgraded database crashes.

migrate.run_migration_if_needed skips EVERY step while the database's stored schema_version equals
migrate.SCHEMA_VERSION. So a new column, index, seed or step that ships without a bump is never applied to an
existing database, while the models already query it - and the app crashes on its first read. It happened twice
in a week: the bank window's portal_url columns on master (caught while building), then V2's interest_rate_source
and minimum_payment_source on lts/1.x, where every 1.1 user's database stores '20260725-byb' and
/api/settings/bootstrap returned 500 after the upgrade (measured, 2026-09-26). The gate could not see either,
because every smoke run starts from a fresh database, which the migration builds from scratch.

This section closes the blind spot by pinning. migrate.py carries SCHEMA_SPEC_SHA256 beside SCHEMA_VERSION: a
fingerprint of migrate.py's code (its AST - comments, docstrings and formatting do not count; the two pin lines
themselves are excluded). Change anything the migration does and the fingerprint moves, and this section fails
until BOTH lines are updated: a new SCHEMA_VERSION, and the new fingerprint, which the failure prints.

It guards against forgetting, not against someone who updates the fingerprint and not the version - the failure
message says which two lines to change, and in which order, so the easy fix is the right one.

Then the case that shows what the pin protects: a database stored at the previous version really does gain a
column the current migration adds (the mechanism the bump relies on).
"""
import ast
import hashlib

_PIN_NAMES = ('SCHEMA_VERSION', 'SCHEMA_SPEC_SHA256')


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
    return hashlib.sha256(ast.dump(tree, include_attributes=False).encode('utf-8')).hexdigest()


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
