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
SCHEMA_VERSION = '20260924-bank-window'   # accounts.portal_url, debt_accounts.portal_url


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
    # BANK_BROWSER.md F3: an unlinked card's own bank website; NULL when linked.
    ('portal_url',        "VARCHAR(2048)"),
    ('end_date',          "DATE"),
]

_NEW_ACCOUNT_COLUMNS = [
    ('minimum_balance', "FLOAT DEFAULT 0"),
    # BANK_BROWSER.md F3: the bank website, nullable, no default.
    ('portal_url',      "VARCHAR(2048)"),
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

# Phase C: debt_ledger_entries already exists on any post-Phase-A install
# (created via create_all when the table itself was new) — this column is
# new on top of that existing table, so it needs the same ALTER TABLE path
# as everything else in this file. Model line required in core/database.py:
# linked_recurring_payment_id = Column(Integer, ForeignKey('recurring_debt_payments.id'), nullable=True)
_NEW_DEBT_LEDGER_COLUMNS = [
    ('linked_recurring_payment_id', "INTEGER REFERENCES recurring_debt_payments(id)"),
]

# The wizard (_bybCommit in app.js) has always computed these fields, but
# _syncBYBItemToDb never sent them and byb_items had no columns for them —
# every saved decision was silently dropped. See BYBItem's docstring in
# core/database.py.
_NEW_BYB_COLUMNS = [
    ('replacing_id',      "INTEGER"),
    ('decision',          "VARCHAR(20)"),
    ('dti_before',        "FLOAT"),
    ('dti_after',         "FLOAT"),
    ('payoff_impact',     "FLOAT"),
    ('whats_left_before', "FLOAT"),
    ('whats_left_after',  "FLOAT"),
    ('actual_cost',       "FLOAT"),
    ('decided_at',        "DATETIME"),
]


# The healthcare record shape lands as new TABLES, which `init_db()`/`create_all` creates on
# fresh and existing databases alike — no DDL needed here. The one exception is the foreign
# key added to an existing table, which create_all will not add to a table that already
# exists. Nullable and additive: no row is rewritten and nothing reads it yet.
_NEW_HISTORIAN_COLUMNS = [
    ('healthcare_expense_id', "INTEGER REFERENCES healthcare_expenses(id)"),
]

# Added with reversal/chargeback: when the money actually moved, distinct from when the
# expense was incurred and from when we heard about it.
# Slice 2 of the evidence substrate (gw 2.0/ARTEFACT_READING_SLICE.md). `artefacts` and
# `readings` are new tables (create_all). These are the additive columns on the two slice-1
# tables that create_all will not add: the reading source on the relationship, and the artefact
# slots on propositions. Nullable, no row rewritten, the state discipline unchanged - which is
# why slice 1 left `utterance_id` nullable and enforces exactly-one-source as a guard.
_NEW_EVIDENCE_COLUMNS = [
    ('reading_id', "INTEGER REFERENCES readings(id)"),
]
# Slice 3 (gw 2.0/ARTEFACT_ORIGIN.md): the institution anchor - a reference to the utterance
# that minted the institution. Additive and nullable; household parties keep person_id and
# never receive it. Exactly-one-anchor is a guard in core/database.py, not a CHECK.
_NEW_PARTY_COLUMNS = [
    ('minted_by_id', "INTEGER REFERENCES utterances(id)"),
]

_NEW_PROPOSITION_COLUMNS = [
    ('subject_artefact_id', "INTEGER REFERENCES artefacts(id)"),
    ('object_artefact_id',  "INTEGER REFERENCES artefacts(id)"),
    # Obligation identity (gw 2.0/OBLIGATION_IDENTITY.md): the obligation referent slots. The
    # `obligations` table itself is new (create_all). No data step: a DebtAccount is decomposable
    # into an obligation only where its asserting party is a fact, and in production (zero
    # Person rows) it is not - no synthetic migration, by ruling.
    ('subject_obligation_id', "INTEGER REFERENCES obligations(id)"),
    ('object_obligation_id',  "INTEGER REFERENCES obligations(id)"),
    # Payment identity (gw 2.0/PAYMENT_IDENTITY.md): the payment referent slots; `payments` is new
    # (create_all). No data step: DebtLedgerEntry / CheckingTransactionLink are household assertions
    # with the payment identity missing from the middle, decomposable only where the asserting
    # party is a fact - not in production. No synthetic migration, by ruling.
    ('subject_payment_id',    "INTEGER REFERENCES payments(id)"),
    ('object_payment_id',     "INTEGER REFERENCES payments(id)"),
    # Ab7 (gw 2.0/PROPOSITION_ABOUTNESS.md): a proposition as subject - used by exactly one ruled
    # kind, proposition_concerns. Subject side only; nothing forced an object-side slot. No data step.
    ('subject_proposition_id', "INTEGER REFERENCES propositions(id)"),
    # Expense identity (gw 2.0/EXPENSE_IDENTITY.md): the expense referent slots; `expenses` is new
    # (create_all). No data step: HealthcareExpense is already identity-only and decomposable only
    # where its asserting party is a fact - not in production; Transaction.category_id is a stance
    # about nothing minted and is not re-homed. No synthetic migration, by ruling.
    ('subject_expense_id',     "INTEGER REFERENCES expenses(id)"),
    ('object_expense_id',      "INTEGER REFERENCES expenses(id)"),
    # Plan identity (gw 2.0/PLAN_IDENTITY.md): the plan referent slots; `plans` is new (create_all).
    # No data step: HealthPlan / HealthPlanTermVersion fuse the plan with asserted terms and are
    # decomposable only where the asserting party is a fact - not in production. Additive only.
    ('subject_plan_id',        "INTEGER REFERENCES plans(id)"),
    ('object_plan_id',         "INTEGER REFERENCES plans(id)"),
    # proposition_corresponds (gw 2.0/PROPOSITION_CORRESPONDENCE.md): the object-side proposition
    # slot, forced because a correspondence has two participants of one type; used by that kind
    # alone. No data step.
    ('object_proposition_id',  "INTEGER REFERENCES propositions(id)"),
]

_NEW_FUNDING_ALLOCATION_COLUMNS = [
    ('occurred_on', "VARCHAR(10)"),
]


def _drop_reserve_contributions():
    """Remove the table the reserve briefly had before the allocation rule was frozen.

    `reserve_contributions` modelled the reserve as a fund you pay into, which the frozen rule
    replaced: a reserve is an allocation of a balance, not a movement of one. It shipped for a
    single commit, nothing in the application ever wrote to it, and `reserve_allocations`
    supersedes it.

    Dropped ONLY when empty. A table with rows in it is somebody's data, and this migration
    has no business deciding what those rows meant.
    """
    with engine.connect() as conn:
        exists = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='reserve_contributions'")).fetchone()
        if not exists:
            return
        rows = conn.execute(text('SELECT COUNT(*) FROM reserve_contributions')).scalar()
        if rows:
            print(f'Migration: reserve_contributions has {rows} rows - left in place')
            return
        conn.execute(text('DROP TABLE reserve_contributions'))
        conn.commit()
        print('Migration: dropped empty reserve_contributions '
              '(superseded by reserve_allocations)')


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


def _backfill_party_anchors(session):
    """Every `Person` gets its 1:1 `Party` anchor (gw 2.0/PERSON_PARTY_ANCHOR.md, ruled).

    Going forward the anchor is minted in the same unit of work as the `Person` by
    construction (`core.database._mint_party_anchor`). This step exists for databases that
    predate the construction: it creates the anchors `people_without_party` reports, and
    nothing else. Idempotent by construction, and additionally flagged so it does not re-scan
    on every start. In production today it finds nothing - no route has ever created a
    `Person` - and that emptiness is recorded rather than assumed: the count is logged.
    """
    from core.database import backfill_party_anchors
    flag = 'migration_party_anchors_20260912'
    if _migration_done(session, flag):
        return
    created = backfill_party_anchors(session)
    logger.info('Party anchors backfilled: %d person(s) lacked one', created)
    _mark_migration_done(session, flag)


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
    # Slice 2: indexes declared on the models for columns added to EXISTING tables, which
    # create_all does not create there. Neither is unique - content_hash is correlation
    # material, never identity, and lives on a new table where create_all handles it.
    ('ix_evidence_reading',      'evidence(reading_id)'),
    ('ix_prop_subject_artefact', 'propositions(subject_artefact_id)'),
    ('ix_prop_subject_obligation', 'propositions(subject_obligation_id)'),
    ('ix_prop_object_obligation',  'propositions(object_obligation_id)'),
    ('ix_prop_subject_payment',    'propositions(subject_payment_id)'),
    ('ix_prop_object_payment',     'propositions(object_payment_id)'),
    ('ix_prop_subject_proposition', 'propositions(subject_proposition_id)'),
    ('ix_prop_object_proposition',  'propositions(object_proposition_id)'),
    ('ix_prop_subject_expense',     'propositions(subject_expense_id)'),
    ('ix_prop_object_expense',      'propositions(object_expense_id)'),
    ('ix_prop_subject_plan',        'propositions(subject_plan_id)'),
    ('ix_prop_object_plan',         'propositions(object_plan_id)'),
    ('ix_txn_account_import', 'transactions(account_id, import_id)'),
    ('ix_txn_account_date',   'transactions(account_id, date)'),
    ('ix_txn_category',       'transactions(category_id)'),
    # Phase C: covers the idempotency check in generate_recurring_payment_drafts
    # (has a draft already been made for this recurring pattern + due date?).
    ('ix_dle_recurring',      'debt_ledger_entries(linked_recurring_payment_id)'),
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
    _add_missing_columns('debt_ledger_entries',  _NEW_DEBT_LEDGER_COLUMNS)
    _add_missing_columns('byb_items',            _NEW_BYB_COLUMNS)
    _add_missing_columns('historian_entries',    _NEW_HISTORIAN_COLUMNS)
    _add_missing_columns('expense_funding_allocations', _NEW_FUNDING_ALLOCATION_COLUMNS)
    _add_missing_columns('evidence',             _NEW_EVIDENCE_COLUMNS)
    _add_missing_columns('propositions',         _NEW_PROPOSITION_COLUMNS)
    _add_missing_columns('parties',              _NEW_PARTY_COLUMNS)
    _drop_reserve_contributions()
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
            _backfill_party_anchors(session)
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
