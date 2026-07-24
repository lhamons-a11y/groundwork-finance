"""Groundwork — Migration. Safe to call every boot."""
import logging
from core.database import init_db, engine, CATEGORY_TREE
from sqlalchemy import text

logger = logging.getLogger('groundwork.migrate')

# ── Schema version gate ──────────────────────────────────────────────────────
# Bump this string whenever ANY step in run_migration_if_needed changes
# (new column, new index, new table, new seed/rename step). When the stored
# version matches, the entire migration body is skipped — no per-table PRAGMAs,
# no index churn — making every post-first-boot launch effectively instant.
# The version is written ONLY after a fully successful run, so a failed
# migration retries on next boot instead of being silently skipped forever.
SCHEMA_VERSION = '20260724-drB'


def _stored_schema_version():
    """Read the recorded schema version via the ORM. Any failure (fresh DB,
    missing table, locked file) returns None → the full migration runs,
    which is the safe direction."""
    try:
        from core.database import db_session, AppSetting
        with db_session() as session:
            row = session.query(AppSetting).filter_by(key='schema_version').first()
            return row.value if row else None
    except Exception:
        return None

_NEW_TRANSACTION_COLUMNS = [
    ('merchant',        "VARCHAR(120) DEFAULT ''"),
    ('posted_date',     "DATE"),
    ('running_balance', "FLOAT"),
    ('mcc',             "VARCHAR(4) DEFAULT ''"),
    ('card_last4',      "VARCHAR(4) DEFAULT ''"),
    ('source',          "VARCHAR(10) DEFAULT ''"),
    ('import_id',       "VARCHAR(64)  DEFAULT ''"),
    ('check_number',    "VARCHAR(20)  DEFAULT ''"),
]

_NEW_DEBT_COLUMNS = [
    ('linked_account_id', "INTEGER REFERENCES accounts(id)"),
    ('credit_limit',      "FLOAT"),
    # d21: persistence for the paid-in-full flag. Null = not paid; the date
    # doubles as the "paid · March 2026" label. Model line required in
    # core/database.py: paid_off_at = Column(Date, nullable=True)
    ('paid_off_at',       "DATE"),
    # create_debt()/update_debt() in server.py pass debt_type and end_date
    # to the DebtAccount constructor/setattr long before these existed as
    # real columns — same TypeError-on-INSERT failure mode as the other
    # columns in this list. Model lines required in core/database.py:
    # debt_type = Column(String(20), default='credit'); end_date = Column(Date, nullable=True)
    ('debt_type',         "VARCHAR(20) DEFAULT 'credit'"),
    ('end_date',          "DATE"),
]

_NEW_ACCOUNT_COLUMNS = [
    ('minimum_balance', "FLOAT DEFAULT 0"),
]

_NEW_CATEGORY_COLUMNS = [
    ('is_optional', "BOOLEAN DEFAULT 0"),
    ('is_enabled',  "BOOLEAN DEFAULT 1"),
    ('icon',        "VARCHAR(20) DEFAULT ''"),
]

# Phase 4: these were referenced by server.py (save_debt_history, B6b
# auto-write) long before they existed as real columns — SQLAlchemy's
# declarative constructor raises TypeError on unknown kwargs, so every
# INSERT of a new debt_balance_history row was crashing. Existing DBs get
# them added here; core/database.py's model is now the matching source of
# truth for fresh DBs.
_NEW_DEBT_HISTORY_COLUMNS = [
    ('interest_charged',     "FLOAT"),
    ('statement_period_end', "VARCHAR(10)"),
]


def _add_missing_columns(table: str, columns: list):
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text(f'PRAGMA table_info({table})'))}
        for name, ddl_type in columns:
            if name in existing:
                continue
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl_type}'))
            conn.commit()
            print(f'Migration: added {table}.{name}')


# ── One-time migration flags ─────────────────────────────────────────────────
# Some migrations rewrite user data based on an assumption (e.g. renaming an
# old flat "Food" budget line to "Groceries"). Those must run exactly once, or
# they risk clobbering a value the user has since deliberately set. We record a
# flag in app_settings after each such migration runs, and skip it thereafter.
# _add_missing_columns / _ensure_indexes are naturally idempotent and don't
# need a flag — this is only for data-rewriting steps.

def _migration_done(session, flag: str) -> bool:
    from core.database import AppSetting
    return session.query(AppSetting).filter_by(key=flag).first() is not None


def _mark_migration_done(session, flag: str):
    from core.database import AppSetting
    if not _migration_done(session, flag):
        session.add(AppSetting(key=flag, value='1'))


def _seed_child_categories(session):
    """
    Add child categories to an existing database.
    Safe to run multiple times — checks each name before inserting.
    Resolves parent IDs dynamically from existing categories.
    """
    from core.database import Category

    existing = {c.name: c for c in session.query(Category).all()}

    added = 0
    for (name, ctype, color, icon, parent_name, sort, is_sys, is_opt) in CATEGORY_TREE:
        if name in existing:
            # Backfill icon / optional flags on categories that predate them.
            cat = existing[name]
            if not cat.icon and icon:
                cat.icon = icon
            if cat.is_optional != is_opt:
                cat.is_optional = is_opt
            if cat.is_enabled is None:
                cat.is_enabled = not is_opt
            continue

        parent_id = None
        if parent_name:
            parent = existing.get(parent_name)
            if not parent:
                continue  # parent not yet in DB — skip for now
            parent_id = parent.id

        cat = Category(
            name=name, type=ctype, color=color, icon=icon,
            parent_id=parent_id, sort_order=sort,
            is_system=is_sys, is_optional=is_opt,
            is_enabled=not is_opt,
        )
        session.add(cat)
        existing[name] = cat
        added += 1

    if added:
        session.flush()
        print(f'Migration: seeded {added} new categories')


def _migrate_old_category_names(session):
    """
    One-time rewrite of legacy flat budget-item category names to their
    modern child-category equivalents. Runs ONCE, guarded by a flag in
    app_settings — after that the user may have deliberately set any of these
    names, so we must never rewrite them again.

    Only touches BudgetItem.category (a free-text string column). Transactions
    reference categories by FK (category_id), which never held these flat
    names, so there is nothing to migrate there.
    """
    from core.database import BudgetItem

    FLAG = 'migrated_flat_category_names_v1'
    if _migration_done(session, FLAG):
        return

    # Old parent-level names → the modern child name a legacy budget line most
    # likely meant. Deliberately conservative; only unambiguous-enough cases.
    RENAME_MAP = {
        'Housing':        'Rent / Mortgage',
        'Streaming':      'Streaming Video',
        'Interest':       'Interest / Fees',
    }

    updated = 0
    for item in session.query(BudgetItem).all():
        if item.category in RENAME_MAP:
            item.category = RENAME_MAP[item.category]
            updated += 1

    _mark_migration_done(session, FLAG)
    if updated:
        print(f'Migration: updated {updated} budget item category names (one-time)')


_PERFORMANCE_INDEXES = [
    ('ix_txn_account_import', 'transactions(account_id, import_id)'),
    ('ix_txn_account_date',   'transactions(account_id, date)'),
    ('ix_txn_category',       'transactions(category_id)'),
]


def _ensure_indexes():
    with engine.connect() as conn:
        for name, spec in _PERFORMANCE_INDEXES:
            conn.execute(text(f'CREATE INDEX IF NOT EXISTS {name} ON {spec}'))
        conn.commit()


def run_migration_if_needed():
    # Schema version gate — skip everything when this DB is already current.
    if _stored_schema_version() == SCHEMA_VERSION:
        logger.info('Schema already at %s — migration skipped', SCHEMA_VERSION)
        return

    init_db()
    _add_missing_columns('transactions',         _NEW_TRANSACTION_COLUMNS)
    _add_missing_columns('debt_accounts',        _NEW_DEBT_COLUMNS)
    _add_missing_columns('accounts',             _NEW_ACCOUNT_COLUMNS)
    _add_missing_columns('categories',           _NEW_CATEGORY_COLUMNS)
    _add_missing_columns('debt_balance_history', _NEW_DEBT_HISTORY_COLUMNS)
    _ensure_indexes()

    # Audit note (d20 deferred → d21): debt_balance_history used to be defined
    # twice — as a model in core/database.py AND as a raw CREATE here. Two
    # schema sources that could silently drift. The model is now the single
    # source of truth (init_db/create_all above creates it on fresh DBs;
    # existing DBs already have it). The raw CREATE was removed; the check
    # below makes a regression loud instead of silent.
    with engine.connect() as conn:
        _dbh = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='debt_balance_history'"
        )).fetchone()
        if not _dbh:
            logger.error('debt_balance_history missing after init_db — '
                         'core/database.py model absent? Balance history will not record.')
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS sinking_funds (
                id                     INTEGER PRIMARY KEY,
                name                   VARCHAR(120) NOT NULL,
                target_amount          FLOAT DEFAULT 0,
                current_amount         FLOAT DEFAULT 0,
                deadline               VARCHAR(10),
                monthly_contribution   FLOAT DEFAULT 0,
                note                   TEXT DEFAULT '',
                is_active              BOOLEAN DEFAULT 1,
                last_contributed_month VARCHAR(7) DEFAULT '',
                created_at             DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        conn.commit()

    from core.database import db_session as _sess
    _seed_ok = False
    with _sess() as session:
        try:
            _seed_child_categories(session)
            _migrate_old_category_names(session)
            for name, ctype, color in [
                ('Interest / Fees', 'expense', '#dc2626'),
                ('Other', 'expense', '#6b7280'),
                ('Transfer', 'transfer', '#94a3b8'),
            ]:
                from core.database import Category
                if not session.query(Category).filter_by(name=name).first():
                    session.add(Category(name=name, type=ctype, color=color,
                                        is_system=True, sort_order=99))
            session.commit()
            _seed_ok = True
        except Exception as e:
            # pywebview has no console — print() here is invisible in the
            # bundled app. Log to the file the smoke test verifies so a broken
            # migration is loud, not silent.
            logger.error('Migration failed during category seed/rename: %s', e, exc_info=True)
            session.rollback()

    # Record the version ONLY after a fully clean run. A seed failure above
    # leaves the version unrecorded so the whole migration retries next boot.
    if _seed_ok:
        try:
            from core.database import AppSetting
            with _sess() as session:
                row = session.query(AppSetting).filter_by(key='schema_version').first()
                if row:
                    row.value = SCHEMA_VERSION
                else:
                    session.add(AppSetting(key='schema_version', value=SCHEMA_VERSION))
                session.commit()
            logger.info('Schema migrated to %s', SCHEMA_VERSION)
        except Exception as e:
            logger.error('Could not record schema_version: %s', e, exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_migration_if_needed()
    print('Migration complete.')
