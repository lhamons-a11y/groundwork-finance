"""
Groundwork — Core Database Layer
Column names match server.py exactly.
"""
import os
from datetime import datetime
from pathlib import Path
from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    Boolean, DateTime, Text, ForeignKey, Date, Index, UniqueConstraint
)
from sqlalchemy import event as _sa_event
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, relationship
from sqlalchemy.pool import NullPool


def _get_data_dir() -> Path:
    # Test isolation: smoke_test.py sets this to a temp dir so tests can
    # never touch the real database. Not used in normal operation.
    override = os.environ.get('GROUNDWORK_DATA_DIR')
    if override:
        d = Path(override)
        d.mkdir(parents=True, exist_ok=True)
        return d
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif hasattr(os, 'uname') and os.uname().sysname == 'Darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    d = base / 'Groundwork'
    d.mkdir(parents=True, exist_ok=True)
    return d


DATA_DIR = _get_data_dir()
DB_PATH  = DATA_DIR / 'groundwork.db'

Base   = declarative_base()
# NullPool: one fresh sqlite3 connection per checkout, closed at return.
# Flask+pywebview runs threaded=True; the previous StaticPool shared a single
# connection process-wide, so concurrent lazy-loads collided on the cursor and
# raised sqlite3.InterfaceError. NullPool is the right shape for local SQLite
# and eliminates the class entirely — connection opens are cheap for a file DB.
engine = create_engine(
    f'sqlite:///{DB_PATH}',
    connect_args={'check_same_thread': False, 'timeout': 15},
    poolclass=NullPool,
)
_SessionFactory = sessionmaker(bind=engine)
db_session      = scoped_session(_SessionFactory)


class Account(Base):
    __tablename__ = 'accounts'
    id              = Column(Integer, primary_key=True)
    name            = Column(String(120), nullable=False)
    type            = Column(String(40), default='checking')
    institution     = Column(String(120), default='')
    currency        = Column(String(3), default='USD')
    balance         = Column(Float, default=0.0)
    sort_order      = Column(Integer, default=0)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    minimum_balance = Column(Float, default=0.0)
    transactions    = relationship('Transaction', back_populates='account', lazy='dynamic')


class Category(Base):
    __tablename__ = 'categories'
    id         = Column(Integer, primary_key=True)
    name       = Column(String(80), nullable=False, unique=True)
    type       = Column(String(20), default='expense')
    color      = Column(String(10), default='#6B7280')
    icon       = Column(String(20), default='')
    parent_id  = Column(Integer, ForeignKey('categories.id'), nullable=True)
    sort_order = Column(Integer, default=0)
    is_system  = Column(Boolean, default=False)
    is_optional = Column(Boolean, default=False)   # optional categories off by default
    is_enabled  = Column(Boolean, default=True)    # user can disable optional categories
    created_at = Column(DateTime, default=datetime.utcnow)
    transactions = relationship('Transaction', back_populates='category', lazy='dynamic')


class Transaction(Base):
    __tablename__ = 'transactions'
    id          = Column(Integer, primary_key=True)
    date        = Column(Date, nullable=False)
    description = Column(String(255), default='')
    amount      = Column(Float, nullable=False)
    type        = Column(String(10), default='debit')
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    account_id  = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    ticker      = Column(String(20), default='')
    cleared     = Column(Boolean, default=True)
    memo        = Column(Text, default='')
    import_id   = Column(String(64), default='')
    created_at  = Column(DateTime, default=datetime.utcnow)
    merchant       = Column(String(120), default='')
    posted_date    = Column(Date, nullable=True)
    running_balance= Column(Float, nullable=True)
    mcc            = Column(String(4), default='')
    card_last4     = Column(String(4), default='')
    source         = Column(String(10), default='')
    check_number   = Column(String(20), default='')
    import_batch   = Column(String(36), nullable=True)    # item 93 B7: one import's lines, so a mistaken one can be set aside together
    account     = relationship('Account', back_populates='transactions')
    category    = relationship('Category', back_populates='transactions')
    # Match _PERFORMANCE_INDEXES in migrate.py — models cover fresh installs
    # (create_all); the migration covers existing databases.
    __table_args__ = (
        Index('ix_txn_account_import', 'account_id', 'import_id'),
        Index('ix_txn_account_date',   'account_id', 'date'),
        Index('ix_txn_category',       'category_id'),
    )


class BudgetItem(Base):
    __tablename__ = 'budget_items'
    id         = Column(Integer, primary_key=True)
    name       = Column(String(120), nullable=False)
    category   = Column(String(80), default='')
    amount     = Column(Float, default=0.0)
    type       = Column(String(10), default='expense')
    sort_order = Column(Integer, default=0)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DebtAccount(Base):
    __tablename__ = 'debt_accounts'
    id              = Column(Integer, primary_key=True)
    name            = Column(String(120), nullable=False)
    begin_balance   = Column(Float, default=0.0)
    current_balance = Column(Float, default=0.0)
    start_date      = Column(Date, nullable=True)
    interest_rate   = Column(Float, default=0.0)
    minimum_payment = Column(Float, default=0.0)
    due_day         = Column(Integer, nullable=True)
    is_active       = Column(Boolean, default=True)
    paid_off_at     = Column(DateTime, nullable=True)
    sort_order      = Column(Integer, default=0)
    created_at      = Column(DateTime, default=datetime.utcnow)
    linked_account_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    linked_account    = relationship('Account')
    credit_limit      = Column(Float, nullable=True)
    # V2: where the current APR / minimum came from - 'user' (typed),
    # 'statement' (read from a reconciled statement) or 'calculated' (the
    # implied-APR alert, the APR estimator). Null = not recorded: rows from
    # before this column existed, and figures that are unknown.
    interest_rate_source   = Column(String(12), nullable=True)
    minimum_payment_source = Column(String(12), nullable=True)
    debt_type         = Column(String(20), default='credit')
    end_date          = Column(Date, nullable=True)


class DebtBalanceHistory(Base):
    __tablename__ = 'debt_balance_history'
    id                    = Column(Integer, primary_key=True)
    debt_id               = Column(Integer, ForeignKey('debt_accounts.id'), nullable=False)
    month                 = Column(String(7), nullable=False)
    balance               = Column(Float, nullable=False)
    payment               = Column(Float, nullable=False)
    min_payment           = Column(Float, nullable=False)
    apr                   = Column(Float, nullable=True)
    # B6b / Phase 4 PDF reconciliation write these — were referenced by
    # server.py (save_debt_history, B6b auto-write) long before the columns
    # existed here, which crashed with a TypeError on every INSERT of a new
    # row (SQLAlchemy's declarative constructor rejects unknown kwargs).
    interest_charged      = Column(Float, nullable=True)
    statement_period_end  = Column(String(10), nullable=True)
    saved_at              = Column(DateTime, default=datetime.utcnow)


class DebtLedgerEntry(Base):
    """
    Manual-entry ledger line for a debt account — charge/payment/interest/fee —
    independent of CSV/OFX import. Debt Reconciliation Blueprint, Phase A.

    No linked_payoff_plan_id column: this codebase has no persisted payoff-plan
    table — payoff projections are computed on the fly client-side
    (_calcDebtIntelligence in app.js), not stored server-side. Phase E decides
    how a "suggested amount" gets computed for drafts; deliberately not
    pointing a FK at a table that doesn't exist.
    """
    __tablename__ = 'debt_ledger_entries'
    id               = Column(Integer, primary_key=True)
    debt_account_id  = Column(Integer, ForeignKey('debt_accounts.id'), nullable=False)
    entry_type       = Column(String(10), nullable=False)   # 'charge' | 'payment' | 'interest' | 'fee'
    amount           = Column(Float, nullable=False)
    entry_date       = Column(Date, nullable=False)
    description      = Column(String(255), default='')
    category         = Column(String(80), default='')
    merchant         = Column(String(120), default='')
    linked_checking_transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    # 'manual' | 'imported' | 'inferred' | 'draft' | 'skipped'
    # (draft = Phase C scheduler, becomes 'manual' on confirm or 'skipped' if
    # the user dismisses that occurrence — 'skipped' isn't a delete, so the
    # generator's idempotency check still sees an entry for that due date
    # and won't regenerate it)
    source_type      = Column(String(10), nullable=False, default='manual')
    # Phase C: which recurring pattern generated this entry, if any. Doubles
    # as the idempotency key for draft generation — (linked_recurring_payment_id,
    # entry_date) is checked before materializing a new draft, so re-running
    # the generator never creates duplicates for a due date already handled.
    linked_recurring_payment_id = Column(Integer, ForeignKey('recurring_debt_payments.id'), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    debt_account                = relationship('DebtAccount')
    linked_checking_transaction = relationship('Transaction')
    linked_recurring_payment    = relationship('RecurringDebtPayment')

    __table_args__ = (
        Index('ix_dle_account_date', 'debt_account_id', 'entry_date'),
        Index('ix_dle_source_type',  'source_type'),
        Index('ix_dle_entry_type',   'entry_type'),
        Index('ix_dle_recurring',    'linked_recurring_payment_id'),
    )


class RecurringDebtPayment(Base):
    """
    Saved payment pattern (e.g. "$735 on the 15th of the month") that
    generates draft ledger entries ahead of the due date. Schema lands in
    Phase A; the draft generator itself is Phase C.
    """
    __tablename__ = 'recurring_debt_payments'
    id                      = Column(Integer, primary_key=True)
    debt_account_id         = Column(Integer, ForeignKey('debt_accounts.id'), nullable=False)
    scheduled_date_of_month = Column(Integer, nullable=True)   # 1-31; null = "last day"
    amount                  = Column(Float, nullable=False)
    frequency               = Column(String(10), default='monthly')   # 'monthly' | 'biweekly' | 'weekly'
    is_active               = Column(Boolean, default=True)
    is_auto_confirm         = Column(Boolean, default=False)   # reserved — user opt-in, not wired yet
    created_at              = Column(DateTime, default=datetime.utcnow)
    last_confirmed_at       = Column(DateTime, nullable=True)
    last_executed_at        = Column(DateTime, nullable=True)
    created_from_transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)

    debt_account = relationship('DebtAccount')

    __table_args__ = (
        Index('ix_rdp_account_active',  'debt_account_id', 'is_active'),
        Index('ix_rdp_schedule_active', 'scheduled_date_of_month', 'is_active'),
    )


class SetAsideTransaction(Base):
    """A deleted transaction, kept whole (gw 2.0/BANK_SIDE_RECORDS.md B7, item 93; a 1.x data-loss fix under L1).
    Out of every total, restorable with its own id - so anything that pointed at it points at it again."""
    __tablename__ = 'set_aside_transactions'
    id           = Column(Integer, primary_key=True)
    original_id  = Column(Integer, nullable=False)
    account_id   = Column(Integer, nullable=True)
    row_json     = Column(Text, nullable=False)        # every column, as the ledger held it
    links_json   = Column(Text, default='[]')          # its debt links, to reconnect on restore
    reason       = Column(String(200), default='')
    batch        = Column(String(36), nullable=True)
    set_aside_at = Column(DateTime, default=datetime.utcnow)
    restored_at  = Column(DateTime, nullable=True)


class ImportHeldLine(Base):
    """A line an import held back because it only LOOKED like one already here (gw 2.0/BANK_SIDE_RECORDS.md B5,
    item 93): never dropped - brought in or kept as "the same" only on the person's yes, and the decision kept."""
    __tablename__ = 'import_held_lines'
    id            = Column(Integer, primary_key=True)
    account_id    = Column(Integer, nullable=True)
    record_json   = Column(Text, nullable=False)       # the line as the import read it
    matched_id    = Column(Integer, nullable=True)     # the ledger line it looked like
    batch         = Column(String(36), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    resolved      = Column(String(10), default='')     # '' | bring_in | same
    resolved_at   = Column(DateTime, nullable=True)
    brought_in_id = Column(Integer, nullable=True)


class CheckingTransactionLink(Base):
    """
    Explicit link between a checking-account payment (Transaction) and a debt
    ledger entry. The checking transaction stays the single source of truth
    for the payment; this table just records the association so nothing gets
    double-entered, and can be removed (unlinked) without deleting either side.
    """
    __tablename__ = 'checking_transaction_links'
    id                      = Column(Integer, primary_key=True)
    checking_transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=False)
    debt_ledger_entry_id    = Column(Integer, ForeignKey('debt_ledger_entries.id'), nullable=False)
    link_indicator          = Column(String(20), nullable=False)   # 'payment_to_card' | 'charge_from_card'
    created_at              = Column(DateTime, default=datetime.utcnow)
    user_confirmed_at       = Column(DateTime, nullable=True)

    checking_transaction = relationship('Transaction')
    debt_entry           = relationship('DebtLedgerEntry')

    __table_args__ = (
        Index('ix_ctl_checking_txn', 'checking_transaction_id'),
        Index('ix_ctl_debt_entry',   'debt_ledger_entry_id'),
        UniqueConstraint('checking_transaction_id', 'debt_ledger_entry_id', name='uq_checking_debt_link'),
    )


class HistorianEntry(Base):
    """
    GROUNDWORK_1_0_ROADMAP.md Phase H1. A structured, queryable event log —
    genuinely new construction, not a rename of anything: before this, the
    only thing called "historian" in this codebase was the informal
    debt_balance_history monthly-snapshot table (see DebtBalanceHistory).
    This is what Phase H2's adaptive features (and Phase F/E's compliance
    reporting, going forward) actually read from.

    event_category values (source noted for each — several are 1.1-scaffold,
    logged nowhere yet, but the column supports them so Phase H2 doesn't need
    another migration to start writing them):
      'payment_confirmed'                 — debt reconciliation (Phase C confirm)
      'payment_amount_variance'           — debt reconciliation (confirmed != suggested)
      'payment_timing_slippage'           — debt reconciliation (confirmed late vs. due date)
      'payment_skipped'                   — debt reconciliation (Phase C skip)
      'balance_correction'                — manual balance correction
      'apr_correction'                    — card terms update
      'charge_observation'                — manual charge entry (Phase B)
      'interest_discrepancy'              — interest calc correction
      'late_fee_trigger'                  — late payment event
      'categorization_suggestion_confirm' — category suggestion kept at ledger save
      'categorization_suggestion_reject'  — category suggestion changed before ledger save
      'budget_variance_observed'          — 1.1-scaffold: budget learning (suggest_budget_adjustment has
                                             no UI consumer yet — see get_budget_variance_by_category)
      'trip_expense_variance'             — 1.1-scaffold: trip learning (trip_history covers this instead — see below)
      'llm_gate_flag'                     — LLM gate miss-log (voice_miss_log.jsonl covers this instead — see below)
      'net_worth_milestone_variance'      — net worth (snapshot save, vs. a milestone's linear pace)
      'investment_allocation_drift'       — investments (price refresh, actual $ vs. target % of portfolio)
      'sinking_fund_contribution_variance'— sinking funds (deposit/auto-credit, actual $ vs. fund's own monthly_contribution)
      'college_fund_contribution_variance'— college funds (contribution, actual $ vs. fund's own monthlyContrib)
      'recurring_pattern_confirm'         — a detected recurring merchant added to the budget
      'recurring_pattern_reject'          — a detected recurring merchant dismissed
      'proactive_shown'                   — an insight promoted past the A.2 gauntlet and shown
                                             unprompted. Context carries its key and budget class;
                                             this IS the frequency cap's ledger (A.3).
      'proactive_dismissed'               — the user dismissed one. An instruction, not a signal to
                                             model: it sets a 60-day cooldown, and two in a category
                                             drops that category to passive for good (A.4).
      'byb_purchase_decision'             — Before You Buy: a commit/walkaway decision (immediate or
                                             a later-resolved 'track' item). expected/actual only set
                                             when a real cost comparison exists (a resolved 'track' item
                                             with actual_cost) — a same-day commit/walkaway is logged as
                                             a pure categorical event (context only), not a fabricated
                                             0%-variance data point.
      'gift_season_contribution_variance' — gift seasons (deposit, actual $ vs. a deadline-derived
                                             monthly pace — gift seasons have no monthly_contribution
                                             field like sinking funds do, so expected is computed
                                             server-side the same way the client's own "$X/mo" display
                                             already is: (target - saved) / months_left)
      'gift_occasion_variance'            — a gift occasion's actual spend vs. its budgeted amount,
                                             logged once the occasion date has passed
      'session_start'                     — app open. Logged server-side in bootstrap() — the one
                                             request guaranteed to fire on every launch — not from a
                                             client signal. Purely categorical (no expected/actual).
      'session_end'                       — app close. Client keepalive POST to /api/historian/engagement
                                             on pagehide; best-effort, so it can be missed on a hard
                                             kill. session_start is the reliable half of the pair.
      'budget_reviewed'                   — user opened the Budget page. Client signal on navigation
                                             (showView('budget')), not on the re-renders renderBudget()
                                             does elsewhere. Purely categorical.
      'budget_adjusted'                   — user intentionally changed a budget item's amount via
                                             update_budget_item. expected=old amount, actual=new amount,
                                             so variance is real. Distinct from budget_variance_observed
                                             (automatic actual-vs-plan drift, still unwritten) — this is
                                             the user's deliberate edit, carrying budget_item_id in context.
    No payoff_plan_id column: same reason as DebtLedgerEntry — there is no
    persisted payoff-plan table in this codebase. Net worth milestones are
    similarly not a DB table (they live in AppSetting's nw_goals_json, a
    JSON array of {id, name, amount, date, startAmount, startDate}) — so
    net_worth_milestone_variance entries carry milestone_id/milestone_name
    in context_json instead of a dedicated FK column, the same way
    debt_account_id/category_id are used for the event types that DO have
    a real table to point at. Investment target allocation is the same
    story — a {asset_class: pct} dict in AppSetting's inv_target_alloc, not
    a table — so investment_allocation_drift carries asset_class in
    context_json too. Sinking funds ARE a real table (SinkingFund) — those
    entries carry a real sinking_fund_id. College funds are JSON again
    (AppSetting's college_funds_json, same {id, ...} shape as net worth
    milestones since neither predates that pattern) — those carry
    college_fund_id. BYB items are a real table (BYBItem) too — those
    entries carry byb_item_id. Gift seasons and occasions are JSON too
    (AppSetting's gift_seasons_json / gift_people_json[].occasions[]) —
    those carry gift_season_id, and gift_person_id + occasion_id since an
    occasion only exists nested inside a person record, not at top level.
    """
    __tablename__   = 'historian_entries'
    id              = Column(Integer, primary_key=True)
    event_category  = Column(String(40), nullable=False)
    debt_account_id = Column(Integer, ForeignKey('debt_accounts.id'), nullable=True)
    category_id     = Column(Integer, ForeignKey('categories.id'), nullable=True)
    expected_value  = Column(Float, nullable=True)
    actual_value    = Column(Float, nullable=True)
    variance_pct    = Column(Float, nullable=True)
    variance_amount = Column(Float, nullable=True)
    context_json    = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    debt_account = relationship('DebtAccount')
    category     = relationship('Category')

    __table_args__ = (
        Index('ix_hist_category_debt',    'event_category', 'debt_account_id'),
        Index('ix_hist_debt_created',     'debt_account_id', 'created_at'),
        Index('ix_hist_category_created', 'event_category', 'created_at'),
    )


class TripHistory(Base):
    """
    GROUNDWORK_1_0_ROADMAP.md Phase H1 addition. Persisted trip records —
    this codebase previously had none; a trip only ever existed as a single
    'trip_budget' JSON blob in AppSetting (server.py), so getTripVarianceByRegion
    (Phase H2 Feature 3) would have had nothing to query across multiple trips.
    Two write hooks populate this (wired when Feature 3 is built, not here):
    trip budget save -> estimate side; "Use these numbers" in
    _applyTripLearnedBasis (app.js) -> actual side, for the date range that
    was run through _learnFromPastTrip.
    """
    __tablename__       = 'trip_history'
    id                  = Column(Integer, primary_key=True)
    trip_label          = Column(String(120), default='')
    region               = Column(String(80), nullable=True)
    start_date          = Column(Date, nullable=True)
    end_date            = Column(Date, nullable=True)
    estimated_total     = Column(Float, nullable=True)
    actual_total        = Column(Float, nullable=True)
    estimated_by_category = Column(Text, nullable=True)   # JSON
    actual_by_category    = Column(Text, nullable=True)   # JSON
    learned_basis_json   = Column(Text, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_trip_history_region', 'region'),
        Index('ix_trip_history_dates',  'start_date', 'end_date'),
    )


class PdfExtractCache(Base):
    """SHA-256-keyed cache of validated PDF statement extractions (Phase 4E) —
    re-uploading the same statement returns the already-validated numbers
    instead of re-billing/re-running the model."""
    __tablename__  = 'pdf_extract_cache'
    source_hash    = Column(String(64), primary_key=True)
    issuer         = Column(String(40), default='')
    extracted_json = Column(Text, nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)


class FlightPriceCache(Base):
    """
    No longer written (gw 2.0/FLIGHT_FARES.md, item 40): the keyed SerpApi search
    that filled it was removed — fares are now looked up in the user's own
    browser and typed in. The table stays so existing databases need no
    migration.
    """
    __tablename__  = 'flight_price_cache'
    cache_key      = Column(String(64), primary_key=True)
    origin         = Column(String(10), nullable=False)
    destination    = Column(String(10), nullable=False)
    outbound_date  = Column(String(10), nullable=False)
    return_date    = Column(String(10), nullable=True)
    travelers      = Column(Integer, default=1)
    price_total    = Column(Float, nullable=True)
    airline        = Column(String(120), nullable=True)
    raw_json       = Column(Text, nullable=True)
    fetched_at     = Column(DateTime, default=datetime.utcnow)


class BudgetPlan(Base):
    __tablename__ = 'budget_plans'
    id            = Column(Integer, primary_key=True)
    name          = Column(String(120), default='Main')
    goal_amount   = Column(Float, default=0.0)
    goal_months   = Column(Integer, default=12)
    start_month   = Column(String(7), default='')
    total_saved   = Column(Float, default=0.0)
    streak_count  = Column(Integer, default=0)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    months        = relationship('BudgetMonth', back_populates='plan', cascade='all, delete-orphan')


class BudgetMonth(Base):
    __tablename__ = 'budget_months'
    id            = Column(Integer, primary_key=True)
    plan_id       = Column(Integer, ForeignKey('budget_plans.id'), nullable=False)
    month_key     = Column(String(7), nullable=False)
    targets       = Column(Text, default='{}')
    actuals       = Column(Text, default='{}')
    is_complete   = Column(Boolean, default=False)
    is_over       = Column(Boolean, default=False)
    saved_amount  = Column(Float, default=0.0)
    coach_note    = Column(Text, default='')
    created_at    = Column(DateTime, default=datetime.utcnow)
    plan          = relationship('BudgetPlan', back_populates='months')


class Achievement(Base):
    __tablename__ = 'achievements'
    id             = Column(Integer, primary_key=True)
    achievement_id = Column(String(60), nullable=False, unique=True)
    section        = Column(String(40), default='general')
    earned_at      = Column(DateTime, default=datetime.utcnow)
    notified       = Column(Boolean, default=False)
    extra_data     = Column(Text, default='{}')


class AppSetting(Base):
    __tablename__ = 'app_settings'
    id         = Column(Integer, primary_key=True)
    key        = Column(String(120), nullable=False, unique=True)
    value      = Column(Text, default='')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HouseholdFact(Base):
    """What the household told Groundwork - the history of one canonical fact (gw 2.0/ONBOARDING_REVISIT.md, item 30).

    Append-only and authoritative: a changed answer is a NEW row, a withdrawal is a row with value NULL, and nothing
    is edited or deleted. The current value is mirrored in app_settings[key] by core.household.set_household_fact(),
    the one write path, in the same transaction. The household's, not a person's: there is no user column.

    key          a fact in core.household.FACTS ('home_state', 'pay_frequency', 'surplus_goal')
    value        the answer, or NULL for a withdrawal (the fact is unanswered again)
    answered_at  when it was said; NULL only for 'carried_over' rows (said before history existed - not invented)
    source       'onboarding' | 'settings' | 'inline_prompt' | 'carried_over'
    """
    __tablename__ = 'household_facts'
    id          = Column(Integer, primary_key=True)
    key         = Column(String(40), nullable=False, index=True)
    value       = Column(String(80), nullable=True)
    answered_at = Column(DateTime, nullable=True)
    source      = Column(String(20), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BYBItem(Base):
    """
    The wizard (_bybCommit in app.js) has always computed decision,
    dti_before/after, payoff_impact, and whats_left_before/after when the
    user finishes evaluating a purchase — but _syncBYBItemToDb only ever
    sent type/name/category/monthly/replacing to the server, and this model
    had no columns for the rest. Every saved item's decision was silently
    dropped, which made _renderBYBList's `!b.decision` fallback treat every
    item as 'walkaway' (dimmed, no comparison stats) regardless of what the
    user actually chose. Added these columns to match what the frontend
    already computes and expects back.

    decided_at/actual_cost support a second use the wizard never had: a
    'track' item (still being considered, not yet committed or walked
    away) can be resolved later via PATCH /api/byb/<id>/resolve once the
    user actually decides — actual_cost captures what it really ended up
    costing, for real estimate-vs-actual signal (Historian: see
    byb_purchase_decision in HistorianEntry's docstring) instead of just a
    same-day categorical choice.
    """
    __tablename__ = 'byb_items'
    id               = Column(Integer, primary_key=True)
    item_type        = Column(String(40), default='subscription')
    name             = Column(String(200), default='')
    category         = Column(String(80), default='Other')
    monthly_cost     = Column(Float, default=0.0)
    replacing_name   = Column(String(200), nullable=True)
    replacing_amount = Column(Float, nullable=True)
    replacing_id     = Column(Integer, nullable=True)
    days_impact      = Column(Float, default=0.0)
    decision         = Column(String(20), nullable=True)   # 'commit' | 'track' | 'walkaway'
    dti_before       = Column(Float, nullable=True)
    dti_after        = Column(Float, nullable=True)
    payoff_impact    = Column(Float, nullable=True)         # months shift; null = "not affordable" (never fabricated)
    whats_left_before = Column(Float, nullable=True)
    whats_left_after  = Column(Float, nullable=True)
    actual_cost      = Column(Float, nullable=True)         # filled when a 'track' item is later resolved
    decided_at       = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)


class NetWorthSnapshot(Base):
    __tablename__ = 'net_worth_snapshots'
    id            = Column(Integer, primary_key=True)
    snapshot_date = Column(String(10), nullable=False)
    net_worth     = Column(Float, default=0.0)
    assets        = Column(Float, default=0.0)
    liabilities   = Column(Float, default=0.0)
    notes         = Column(Text, default='')
    created_at    = Column(DateTime, default=datetime.utcnow)


class SinkingFund(Base):
    """
    Sinking fund — a named savings target with a deadline.
    Monthly contribution is calculated from target and deadline.
    Surfaced in the Budget page as its own section.
    Money sits in the user's checking/savings — Groundwork just tracks it.
    """
    __tablename__ = 'sinking_funds'
    id                   = Column(Integer, primary_key=True)
    name                 = Column(String(120), nullable=False)
    target_amount        = Column(Float, default=0.0)
    current_amount       = Column(Float, default=0.0)
    deadline             = Column(String(10), nullable=True)   # YYYY-MM-DD
    monthly_contribution = Column(Float, default=0.0)          # user override; else auto-calculated
    note                 = Column(Text, default='')
    is_active            = Column(Boolean, default=True)
    last_contributed_month = Column(String(7), default='')     # YYYY-MM — for auto-credit
    created_at           = Column(DateTime, default=datetime.utcnow)


class InvestmentTransaction(Base):
    __tablename__ = 'investment_transactions'
    id              = Column(Integer, primary_key=True)
    account_id      = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    date            = Column(Date, nullable=False)
    ticker          = Column(String(20), nullable=False)
    type            = Column(String(20), nullable=False)
    security_type   = Column(String(20), default='stock')
    shares          = Column(Float, default=0.0)
    price_per_share = Column(Float, default=0.0)
    total_amount    = Column(Float, default=0.0)
    fees            = Column(Float, default=0.0)
    note            = Column(Text, default='')
    meta            = Column(Text, nullable=True)
    import_source   = Column(String(20), default='manual')
    created_at      = Column(DateTime, default=datetime.utcnow)


class InvestmentLot(Base):
    __tablename__ = 'investment_lots'
    id                    = Column(Integer, primary_key=True)
    account_id            = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    source_transaction_id = Column(Integer, ForeignKey('investment_transactions.id'), nullable=True)
    ticker                = Column(String(20), nullable=False)
    security_type         = Column(String(20), default='stock')
    shares_original       = Column(Float, default=0.0)
    shares_remaining      = Column(Float, default=0.0)
    cost_basis_per_share  = Column(Float, default=0.0)
    purchase_date         = Column(Date, nullable=False)
    is_closed             = Column(Boolean, default=False)
    closed_date           = Column(Date, nullable=True)
    sell_price_per_share  = Column(Float, nullable=True)
    realized_gain         = Column(Float, nullable=True)
    realized_gain_pct     = Column(Float, nullable=True)
    holding_period_days   = Column(Integer, nullable=True)


class PriceCache(Base):
    __tablename__  = 'price_cache'
    ticker         = Column(String(20), primary_key=True)
    price          = Column(Float, default=0.0)
    previous_close = Column(Float, nullable=True)
    day_change     = Column(Float, nullable=True)
    day_change_pct = Column(Float, nullable=True)
    company_name   = Column(String(120), nullable=True)
    currency       = Column(String(3), default='USD')
    market_state   = Column(String(20), nullable=True)
    last_updated   = Column(DateTime, nullable=True)
    is_manual      = Column(Boolean, default=False)
    source         = Column(String(20), nullable=True)


# ── Category hierarchy — full list ────────────────────────────────────────────
# Format: (name, type, color, icon, parent_name, sort_order, is_system, is_optional)
# parent_name=None means top-level parent category
# is_optional=True means off by default — user enables in Settings

CATEGORY_TREE = [
    # ── Home ──────────────────────────────────────────────────────────────────
    ('Home',                    'expense','#a16207','home',        None,   0,  True, False),
    ('Rent / Mortgage',         'expense','#a16207','home',        'Home', 0,  True, False),
    ('Homeowner\'s Insurance',  'expense','#a16207','shield',      'Home', 1,  True, False),
    ('Renter\'s Insurance',     'expense','#a16207','shield',      'Home', 2,  True, False),
    ('HOA Fees',                'expense','#a16207','building',    'Home', 3,  True, False),
    ('Home Maintenance',        'expense','#a16207','wrench',      'Home', 4,  True, False),
    ('Home Improvement',        'expense','#a16207','hammer',      'Home', 5,  True, False),
    ('Property Taxes',          'expense','#a16207','receipt',     'Home', 6,  True, False),
    ('Household Supplies',      'expense','#a16207','shopping-bag','Home', 7,  True, False),
    ('Cleaning Services',       'expense','#a16207','sparkles',    'Home', 8,  True, False),
    ('Lawn / Landscaping',      'expense','#a16207','leaf',        'Home', 9,  True, False),
    ('Security System',         'expense','#a16207','lock',        'Home', 10, True, False),
    ('Furniture / Decor',       'expense','#a16207','sofa',        'Home', 11, True, False),

    # ── Utilities ─────────────────────────────────────────────────────────────
    ('Utilities',               'expense','#06b6d4','bolt',        None,   1,  True, False),
    ('Electric',                'expense','#06b6d4','bolt',        'Utilities', 0, True, False),
    ('Gas',                     'expense','#06b6d4','flame',       'Utilities', 1, True, False),
    ('Water / Sewer',           'expense','#06b6d4','droplet',     'Utilities', 2, True, False),
    ('Internet',                'expense','#06b6d4','wifi',        'Utilities', 3, True, False),
    ('Phone / Cell',            'expense','#06b6d4','phone',       'Utilities', 4, True, False),
    ('Trash',                   'expense','#06b6d4','trash',       'Utilities', 5, True, False),
    ('Cable / TV',              'expense','#06b6d4','tv',          'Utilities', 6, True, False),

    # ── Food ──────────────────────────────────────────────────────────────────
    ('Food',                    'expense','#f97316','utensils',    None,   2,  True, False),
    ('Groceries',               'expense','#f97316','shopping-cart','Food',0,  True, False),
    ('Restaurants',             'expense','#f97316','utensils',   'Food', 1,  True, False),
    ('Fast Food / Takeout',     'expense','#f97316','package',    'Food', 2,  True, False),
    ('Coffee Shops',            'expense','#f97316','coffee',     'Food', 3,  True, False),
    ('Work Lunches',            'expense','#f97316','briefcase',  'Food', 4,  True, False),

    # ── Transportation ────────────────────────────────────────────────────────
    ('Transportation',          'expense','#8b5cf6','car',         None,   3,  True, False),
    ('Gas / Fuel',              'expense','#8b5cf6','fuel',        'Transportation', 0, True, False),
    ('Auto Insurance',          'expense','#8b5cf6','shield',      'Transportation', 1, True, False),
    ('Car Maintenance',         'expense','#8b5cf6','wrench',      'Transportation', 2, True, False),
    ('Car Registration',        'expense','#8b5cf6','file-text',   'Transportation', 3, True, False),
    ('Parking / Tolls',         'expense','#8b5cf6','map-pin',     'Transportation', 4, True, False),
    ('Rideshare / Transit',     'expense','#8b5cf6','bus',         'Transportation', 5, True, False),

    # ── Healthcare ────────────────────────────────────────────────────────────
    ('Healthcare',              'expense','#ef4444','heart',       None,   4,  True, False),
    ('Doctor / Co-pays',        'expense','#ef4444','stethoscope', 'Healthcare', 0, True, False),
    ('Prescriptions',           'expense','#ef4444','pill',        'Healthcare', 1, True, False),
    ('Dental',                  'expense','#ef4444','smile',       'Healthcare', 2, True, False),
    ('Vision',                  'expense','#ef4444','eye',         'Healthcare', 3, True, False),
    ('Gym / Fitness',           'expense','#ef4444','activity',    'Healthcare', 4, True, False),

    # ── Insurance ─────────────────────────────────────────────────────────────
    ('Insurance',               'expense','#64748b','shield',      None,   5,  True, False),
    ('Health Insurance',        'expense','#64748b','shield',      'Insurance', 0, True, False),
    ('Life Insurance',          'expense','#64748b','shield',      'Insurance', 1, True, False),
    ('Disability Insurance',    'expense','#64748b','shield',      'Insurance', 2, True, False),
    ('Long-term Care',          'expense','#64748b','shield',      'Insurance', 3, True, False),

    # ── Pets ──────────────────────────────────────────────────────────────────
    ('Pets',                    'expense','#92400e','heart',       None,   6,  True, False),
    ('Vet / Medical',           'expense','#92400e','stethoscope', 'Pets', 0,  True, False),
    ('Pet Food / Supplies',     'expense','#92400e','package',     'Pets', 1,  True, False),
    ('Grooming',                'expense','#92400e','scissors',    'Pets', 2,  True, False),
    ('Boarding / Pet Sitting',  'expense','#92400e','home',        'Pets', 3,  True, False),

    # ── Personal ──────────────────────────────────────────────────────────────
    ('Personal',                'expense','#6b7280','user',        None,   7,  True, False),
    ('Clothing',                'expense','#6b7280','shirt',       'Personal', 0, True, False),
    ('Haircut / Salon',         'expense','#6b7280','scissors',    'Personal', 1, True, False),
    ('Personal Care',           'expense','#6b7280','smile',       'Personal', 2, True, False),
    ('Hobbies',                 'expense','#6b7280','star',        'Personal', 3, True, False),

    # ── Subscriptions ─────────────────────────────────────────────────────────
    ('Subscriptions',           'expense','#ec4899','repeat',      None,   8,  True, False),
    ('Streaming Video',         'expense','#ec4899','play',        'Subscriptions', 0, True, False),
    ('Streaming Music',         'expense','#ec4899','music',       'Subscriptions', 1, True, False),
    ('Software / Apps',         'expense','#ec4899','monitor',     'Subscriptions', 2, True, False),
    ('Annual Memberships',      'expense','#ec4899','credit-card', 'Subscriptions', 3, True, False),
    ('Other Subscriptions',     'expense','#ec4899','repeat',      'Subscriptions', 4, True, False),

    # ── Entertainment ─────────────────────────────────────────────────────────
    ('Entertainment',           'expense','#ec4899','film',        None,   9,  True, False),
    ('Activities / Events',     'expense','#ec4899','calendar',    'Entertainment', 0, True, False),
    ('Concerts / Sports',       'expense','#ec4899','music',       'Entertainment', 1, True, False),
    ('Vacation / Travel',       'expense','#ec4899','plane',       'Entertainment', 2, True, False),

    # ── Education ─────────────────────────────────────────────────────────────
    ('Education',               'expense','#0ea5e9','book',        None,   10, True, False),
    ('Tuition / Courses',       'expense','#0ea5e9','graduation',  'Education', 0, True, False),
    ('Books / Materials',       'expense','#0ea5e9','book',        'Education', 1, True, False),
    ('Professional Development','expense','#0ea5e9','briefcase',   'Education', 2, True, False),

    # ── Gifts & Donations ─────────────────────────────────────────────────────
    ('Gifts & Donations',       'expense','#d97706','gift',        None,   11, True, False),
    ('Gifts',                   'expense','#d97706','gift',        'Gifts & Donations', 0, True, False),
    ('Charitable Donations',    'expense','#d97706','heart',       'Gifts & Donations', 1, True, False),

    # ── Children / Family (optional) ─────────────────────────────────────────
    ('Children / Family',       'expense','#f59e0b','users',       None,   12, True, True),
    ('Childcare / Daycare',     'expense','#f59e0b','home',        'Children / Family', 0, True, True),
    ('School / Tuition',        'expense','#f59e0b','graduation',  'Children / Family', 1, True, True),
    ('School Supplies',         'expense','#f59e0b','book',        'Children / Family', 2, True, True),
    ('Kids Activities',         'expense','#f59e0b','star',        'Children / Family', 3, True, True),

    # ── Business / Work (optional) ────────────────────────────────────────────
    ('Business / Work',         'expense','#6366f1','briefcase',   None,   13, True, True),
    ('Work Expenses',           'expense','#6366f1','briefcase',   'Business / Work', 0, True, True),
    ('Business Supplies',       'expense','#6366f1','package',     'Business / Work', 1, True, True),

    # ── System categories (no children) ──────────────────────────────────────
    ('Transfer',                'transfer','#94a3b8','arrow-right',None,  14, True, False),
    ('Interest / Fees',         'expense','#dc2626','percent',     None,  15, True, False),
    ('Debt',                    'expense','#dc2626','credit-card', None,  16, True, False),
    ('Other',                   'expense','#6b7280','more-horizontal',None,17,True, False),

    # ── Income ────────────────────────────────────────────────────────────────
    ('Income',                  'income', '#22c55e','dollar-sign', None,  18, True, False),
    ('Paycheck / Salary',       'income', '#22c55e','dollar-sign', 'Income', 0, True, True),
    ('Side Income',             'income', '#22c55e','trending-up', 'Income', 1, True, True),
    ('Rental Income',           'income', '#22c55e','home',        'Income', 2, True, True),
]


def init_db():
    Base.metadata.create_all(engine)
    session = db_session()
    try:
        if session.query(Category).count() == 0:
            _seed_categories(session)
    except Exception:
        session.rollback()
    finally:
        session.close()


def _seed_categories(session):
    """Seed the full parent/child category tree on a fresh database."""
    # First pass — create all parent categories (parent_id=None)
    parent_map = {}  # name → id
    for (name, ctype, color, icon, parent_name, sort, is_sys, is_opt) in CATEGORY_TREE:
        if parent_name is not None:
            continue
        cat = Category(name=name, type=ctype, color=color, icon=icon,
                       parent_id=None, sort_order=sort,
                       is_system=is_sys, is_optional=is_opt,
                       is_enabled=not is_opt)
        session.add(cat)
    session.flush()

    # Build parent name → id map
    for cat in session.query(Category).all():
        parent_map[cat.name] = cat.id

    # Second pass — create child categories
    for (name, ctype, color, icon, parent_name, sort, is_sys, is_opt) in CATEGORY_TREE:
        if parent_name is None:
            continue
        parent_id = parent_map.get(parent_name)
        cat = Category(name=name, type=ctype, color=color, icon=icon,
                       parent_id=parent_id, sort_order=sort,
                       is_system=is_sys, is_optional=is_opt,
                       is_enabled=not is_opt)
        session.add(cat)
    session.commit()



# ── Item 93 B7: a set-aside transaction keeps its id ──────────────────────────────────────────────────────────────
# SQLite hands a new row max(id) + 1, so setting aside the newest transaction would let the next import take its id,
# and a restore would then find it taken. A new transaction's id is chosen above every id ever set aside.
@_sa_event.listens_for(Transaction, 'before_insert')
def _txn_id_above_set_aside(mapper, connection, target):
    if target.id is not None:
        return
    from sqlalchemy import text as _t
    try:
        hi = connection.execute(_t('SELECT MAX(original_id) FROM set_aside_transactions')).scalar() or 0
    except Exception:             # a database from before the table existed
        return
    if hi:
        cur = connection.execute(_t('SELECT MAX(id) FROM transactions')).scalar() or 0
        # Rows inserted in one batch are not in the table yet when the next asks, so the last id handed out on this
        # connection is remembered and counted too - or a batch would be given one id for every row.
        last = connection.info.get('_gw_last_txn_id', 0)
        if hi >= cur or last > cur:
            target.id = max(hi, cur, last) + 1
            connection.info['_gw_last_txn_id'] = target.id
