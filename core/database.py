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
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, relationship
from sqlalchemy import event
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
    # One foreign key per referable entity, following the convention `debt_account_id` and
    # `category_id` already set. Sprawl is the price of enforceability, and this project has
    # consistently paid it: a polymorphic (entity_type, entity_id) pair avoids the nullable
    # columns and gives up referential integrity, which is precisely the defect already
    # visible in the `entry_id` values written into `context_json` with nothing to enforce
    # them. See `gw 2.0/EVENT_SUBSTRATE_QUESTION.md`.
    healthcare_expense_id = Column(Integer, ForeignKey('healthcare_expenses.id'),
                                   nullable=True)

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
    SHA-256-keyed cache of live flight price searches (origin+destination+
    dates+travelers), via SerpApi's Google Flights engine (flight_price.py).
    SerpApi's free tier is 100 searches/month — this is what keeps a page
    reload or a duplicate click from spending it on a search already run.
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


# ── Healthcare: the record shape ──────────────────────────────────────────────
# Step 2 of `gw 2.0/HEALTHCARE_MODULE_DESIGN.md` §6.3, and §6.2 is the argument for landing
# it before the arithmetic that reads it: recording decisions are urgent, code decisions are
# not. A tax report cannot reconstruct which of 2027's pharmacy charges were HSA-paid if
# nothing recorded it at the time.
#
# The shape was not designed here. It was validated by `tests/substrate_experiment.py`
# against the criterion pre-registered in `gw 2.0/EVENT_SUBSTRATE_QUESTION.md`: every
# structural relationship in a foreign key or a link table, none in `context_json`, and the
# whole lifecycle fixture passing with that column never written.
#
# NOTHING READS THESE TABLES YET. The matching modules in `core/` — allocation, person,
# plan_year, classification — are pure and have no callers. Wiring them is the next step.

class Person(Base):
    """A named person in the household. `id` is identity; `display_name` is presentation, so
    renaming touches no figure. Names are labels, not access control — anyone who opens
    Groundwork sees every person's data (design §1.7)."""
    __tablename__ = 'people'
    id           = Column(Integer, primary_key=True)
    display_name = Column(String(80), nullable=False)
    active       = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    # The reference-layer anchor, minted with the row (see `Party`). Structural, not evidence.
    party = relationship('Party', back_populates='person', uselist=False)


class PersonAlias(Base):
    """The explicit mapping an import must make. `patient = "ROB L."` is a string a billing
    system chose; it becomes identity only when a person says so. John and John Jr. are why a
    near-match may never be a match."""
    __tablename__ = 'person_aliases'
    id         = Column(Integer, primary_key=True)
    person_id  = Column(Integer, ForeignKey('people.id'), nullable=False)
    alias      = Column(String(120), nullable=False)
    source     = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index('ix_person_alias', 'alias'),)


class Party(Base):
    """The one usable party reference — the stable target relationships point to.

    Ruled 2026-09-12 (`gw 2.0/PARTY_REFERENCE_SHAPE.md`, `PERSON_PARTY_ANCHOR.md`). A party
    is either a household member or an institution, and the two have different epistemic
    foundations: a household member's identity is the household's own declaration (`Person`);
    an institution's identity is minted by Groundwork and every "this is the same institution"
    is an asserted correspondence with a strength. One reference, two foundations - and which
    foundation a party has is a join to its anchor, never a kind that consumers switch on.

    **This row is structural, not evidence.** Its existence, its foreign key and its anchor
    relationship carry no source, no strength, no reason and no supersession, and none of them
    may be read as correspondence evidence. A party reference establishes only *this relation
    points to party X*; that X is the same as some entity described elsewhere still requires
    a correspondence claim, which lives in its own relation (not in this slice).

    **The household anchor.** `person_id` is 1:1 with `people`: UNIQUE gives *at most one*
    party per person; *at least one* - every `Person` has its anchor - is a cross-table
    existence constraint SQLite cannot express, so the creation path owns it (the
    `after_insert` listener below mints the anchor in the same unit of work as the `Person`,
    never afterwards, never on demand) and a guard asserts it (`tests/test_party_anchor_
    fixture.py`; the migration's audit query). A person without a party is the forbidden
    state.

    **The institution anchor** (slice 3, `ARTEFACT_ORIGIN.md` s5, ruled). `minted_by_id` points
    to the utterance that minted the institution - the household's individuating assertion
    ("this is from Aetna, my insurer"), whose origin is a Person: the fixed point one step out.
    It is a REFERENCE to a claim, not a claim: the party row still carries no source, strength
    or descriptor. An institution's name, plan number and address are the minting utterance's
    CONTENT and become correspondence evidence later - there is no name column here, and there
    will not be one. **Exactly one anchor per party** - `person_id` xor `minted_by_id` - is a
    guard (`_validate_party_anchor`, `parties_without_one_anchor`), since a CHECK cannot be
    added to a SQLite table after creation. A party with neither is the forbidden state; a
    party with both is the collapse of the two foundations. No `kind` column: foundation is
    which anchor is set, by join.

    **The pure registry (`core/person.py`) has no reference layer**; its `Person` is its own
    anchor. The persisted layer is where the anchor is a row.
    """
    __tablename__ = 'parties'
    id           = Column(Integer, primary_key=True)
    person_id    = Column(Integer, ForeignKey('people.id'), unique=True, nullable=True)
    # use_alter breaks the parties <-> utterances cycle for create_all's ordering; SQLite
    # renders the constraint inline regardless (verified), and existing databases receive the
    # column through migrate.py's _add_missing_columns.
    minted_by_id = Column(Integer, ForeignKey('utterances.id', use_alter=True, name='fk_party_minted_by'),
                          nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    person    = relationship('Person', back_populates='party')
    minted_by = relationship('Utterance', foreign_keys=[minted_by_id], post_update=True)

    ANCHOR_SLOTS = ('person_id', 'minted_by_id')


def party_anchor_violations(party):
    n = sum(getattr(party, c) is not None for c in Party.ANCHOR_SLOTS)
    return [] if n == 1 else [f'exactly one anchor must be set, {n} are']


@event.listens_for(Party, 'before_insert')
@event.listens_for(Party, 'before_update')
def _validate_party_anchor(mapper, connection, target):
    problems = party_anchor_violations(target)
    if problems:
        raise ValueError('party anchor violated: ' + '; '.join(problems))


def parties_without_one_anchor(session):
    """Audit: parties with no anchor or two. Empty is the invariant."""
    return [p for p in session.query(Party).all() if party_anchor_violations(p)]


def party_foundation(party):
    """'person' | 'institution' - which anchor is set. A join, never a stored kind."""
    return 'person' if party.person_id is not None else 'institution'


# Same unit of work, every ORM creation path, by construction. A raw SQL insert into `people`
# bypasses this - which is why the guard and the backfill exist beside it.
@event.listens_for(Person, 'after_insert')
def _mint_party_anchor(mapper, connection, target):
    connection.execute(Party.__table__.insert().values(person_id=target.id))


# ── The evidence substrate (slice 1) ─────────────────────────────────────────
# gw 2.0/SMALLEST_SCHEMA.md (ruled s12) and SHIPPED_VS_TARGET.md (ruled s6), 2026-09-13.
#
#     Person -> Utterance -> Proposition <- evidentiary relationship
#
#     Artefact -> Reading ------------------^   (slice 2: ARTEFACT_READING_SLICE.md)
#
# Five tables. Utterances and readings ARE the evidence - what a party said, what Groundwork
# saw of a held artefact; propositions are what they evidence; the relationship connects them.
# Slice 8 (ARTEFACT_ABOUTNESS.md): artefact_concerns - the crossing from "A says X" to "X is about O"
# is a claim of its own, presupposing O; it never rewrites what A said or how it is known.
# Obligation (OBLIGATION_IDENTITY.md): a continuant minted by the household's assertion - anchor =
# pointer to the minting utterance and nothing else; obligation slots; obligation_corresponds.
# Slice 5 (CLAIM_ABOUT_CLAIM.md): utterance_retraction - the one higher-order kind; about the
# utterance, never a verdict on it; strength undetermined until relational knowing is ruled.
# Slice 4 (CORRESPONDENCE.md): artefact_corresponds / party_corresponds, the RULED_KINDS slot
# registry, the same-foundation guard, `referent()` - and reference slots immutable after
# insert, because a merge is a re-point and a re-point rewrites history.
# Slice 3 (ARTEFACT_ORIGIN.md): the institution anchor on `parties` (`minted_by` -> the
# household's minting utterance) and the first ruled proposition kind, `artefact_origin`, with
# origin STATE derived from those propositions and reading strength derived over one link. Nothing here is a repair of, or a mapping onto, `core.classification.Evidence` or
# `PdfExtractCache` - the former fuses four of these objects (SHIPPED_VS_TARGET s1), the latter
# is the shipped artefact+reading 1:1 by hash; both are left exactly as they are.

# Explicit participant states for a proposition's subject and second participant. States,
# not NULL semantics: a NULL reference FOLLOWS from a state, never the reverse (the party-
# shape ruling, relocated to the proposition's subject by the proposition ruling).
PARTICIPANT_ESTABLISHED = 'established'
PARTICIPANT_NOT_ESTABLISHED = 'not_established'       # asserted; referent not yet settled
PARTICIPANT_CANDIDATES = 'not_established_with_candidates'   # candidates live in correspondence, not here
PARTICIPANT_NONE = 'none'                             # the world, a process, or a kind with no such participant
PARTICIPANT_STATES = (PARTICIPANT_ESTABLISHED, PARTICIPANT_NOT_ESTABLISHED,
                      PARTICIPANT_CANDIDATES, PARTICIPANT_NONE)


class Utterance(Base):
    """An assertion event. Its identity is the occurrence of the act.

    Ruled (`UTTERANCE_PRIMITIVE.md`, `UTTERANCE_IDENTITY.md`): an utterance exists by virtue of
    the originating party making the assertion - its truth, resolvability and comprehensibility
    are later findings ABOUT it, never conditions of it. Two acts are two utterances even with
    identical content; one act is one utterance even if encountered twice (a duplicate encounter
    is a correspondence question, never a second row minted by the importer).

    Intrinsic: who (`origin_party_id`), what (`content`, opaque), when asserted (`asserted_at` -
    the EVIDENCE TIME, nullable because "sometime in March" is a real coordinate that can be
    uncertain). About the utterance, kept separate: `recorded_at` - when Groundwork encountered
    it. For an in-app assertion the two may coincide; that is an implementation circumstance,
    not a rule, and the two columns exist so nothing can ever read one as the other.

    Not here, by ruling: strength (derived from origin x proposition kind - see
    `derived_strength`); any truth / resolution / retraction state (later propositions whose
    subject is this utterance); a surface or channel (about the encounter, not the act).
    An utterance with NO propositions is legitimate: content held, not yet interpreted.
    """
    __tablename__ = 'utterances'
    id              = Column(Integer, primary_key=True)
    origin_party_id = Column(Integer, ForeignKey('parties.id'), nullable=False)
    asserted_at     = Column(String(19), nullable=True)      # evidence time; ISO; may be absent
    recorded_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    content         = Column(Text, nullable=True)

    origin = relationship('Party', foreign_keys=[origin_party_id])


class Artefact(Base):
    """A thing encountered - a document, a capture, a statement the household says exists.
    Identity is MINTED on encounter (`id`); held vs asserted is a property, not a second kind.
    Ruled `IDENTITY_MECHANISM_COMPARISON.md`, `SMALLEST_SCHEMA.md` s2, `ARTEFACT_READING_SLICE.md`.

    `held` must be stated (no default): held means Groundwork retains the artefact such that its
    contents can later be re-read (the capture ruling, C4); asserted means the household said it
    exists and Groundwork never held it (R-ASSERT) - it then exists UNDER the asserting
    utterance (`asserted_by_id`), the same under-a-claim shape an institution will have. Held
    artefacts carry no `asserted_by`: the encounter is their provenance. Enforced by
    `_validate_artefact`, since SQLite cannot express it.

    `content_hash` is CORRESPONDENCE EVIDENCE, never identity: nullable, indexed, NOT unique.
    Two encounters with identical bytes are two artefacts until a correspondence claim says
    otherwise (`hash == X -> artefact_id = X` is forbidden by construction).

    Three times are three columns: `as_of` (the artefact's OWN date - a statement date, a
    capture's stated as-of; nullable because it may be absent or unknown), `encountered_at`
    (when Groundwork first held or was told of it - the minting event), and each reading's
    `read_at`. None may be read as another: `encountered_at` is never evidence of when the
    document existed; `read_at` is never the document's date (the tie ruling; H3).

    Not here, by ruling: ORIGIN. The artefact's origin party is derived from origin-of-artefact
    propositions (slice 3), never a column - a stored origin would be a summary of evidence that
    can drift from the claims that determine it. No issuer string, no description-as-origin.
    """
    __tablename__ = 'artefacts'
    id             = Column(Integer, primary_key=True)
    held           = Column(Boolean, nullable=False)
    content_hash   = Column(String(64), nullable=True)
    as_of          = Column(String(10), nullable=True)
    encountered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    asserted_by_id = Column(Integer, ForeignKey('utterances.id'), nullable=True)

    asserted_by = relationship('Utterance')
    readings    = relationship('Reading', back_populates='artefact')

    __table_args__ = (
        Index('ix_artefact_hash', 'content_hash'),     # for finding CANDIDATES - not unique
    )


def artefact_violations(artefact):
    """held <-> no asserting utterance; asserted <-> exactly the asserting utterance."""
    out = []
    if artefact.held is None:
        out.append('held must be stated')
    elif artefact.held and artefact.asserted_by_id is not None:
        out.append('a held artefact carries no asserting utterance - the encounter is its provenance')
    elif not artefact.held and artefact.asserted_by_id is None:
        out.append('an asserted artefact exists only under the utterance that asserted it')
    return out


@event.listens_for(Artefact, 'before_insert')
@event.listens_for(Artefact, 'before_update')
def _validate_artefact(mapper, connection, target):
    problems = artefact_violations(target)
    if problems:
        raise ValueError('artefact violated: ' + '; '.join(problems))


class Reading(Base):
    """An observation event of one HELD artefact - what Groundwork saw, as distinct from what a
    party said (`Utterance`). Ruled `SMALLEST_SCHEMA.md` s3, `ARTEFACT_READING_SLICE.md` s8.

    The artefact owns its readings, one per act of observation: the same artefact read twice
    is two rows under one `artefact_id` (one artefact, two observations), and that is how a
    parse dispute is distinguished from a source conflict - by structure, never by timestamp,
    text or row order.

    The READER is who performed the observation, not who asserted anything: `reader_party_id`
    (a household member transcribing) xor `reader_process` (a parser, name/version). A reading
    by a process has NO PARTY - a positive state, never a party minted for the parser, never
    NULL-ambiguity (exactly one reader slot is set; a guard). The reader is never an origin:
    a member reading Aetna's EOB does not become the origin of Aetna's figures (contract C1/C2),
    so `derived_strength` never consults the reader.

    `read_at` is this observation's own time - neither the artefact's `as_of` nor its
    `encountered_at`. No content column: a reading's content is the propositions it evidences;
    zero is legitimate (V6 - the reading happened and the field was unreadable).

    A reading exists only of a held artefact. An asserted artefact gives POSE + FIND, never
    RE-READ: the household's "the EOB says $412" about a document Groundwork does not hold is an
    UTTERANCE whose proposition has the artefact as subject - the same words, a different
    evidence event - and the record tells them apart without reading the text.
    """
    __tablename__ = 'readings'
    id              = Column(Integer, primary_key=True)
    artefact_id     = Column(Integer, ForeignKey('artefacts.id'), nullable=False)
    read_at         = Column(DateTime, default=datetime.utcnow, nullable=False)
    reader_party_id = Column(Integer, ForeignKey('parties.id'), nullable=True)
    reader_process  = Column(String(80), nullable=True)

    artefact     = relationship('Artefact', back_populates='readings')
    reader_party = relationship('Party')

    READER_SLOTS = ('reader_party_id', 'reader_process')

    __table_args__ = (
        Index('ix_reading_artefact', 'artefact_id'),
    )


def reading_violations(reading, artefact_held):
    """exactly one reader; the artefact is held. `artefact_held` is the artefact's `held`
    value, or None when the artefact does not exist (a violation in itself)."""
    out = []
    set_slots = [c for c in Reading.READER_SLOTS if getattr(reading, c) is not None]
    if len(set_slots) != 1:
        out.append(f'exactly one reader slot must be set, {len(set_slots)} are: {set_slots}')
    if artefact_held is None:
        out.append('the artefact does not exist')
    elif not artefact_held:
        out.append('a reading exists only of a held artefact - an asserted artefact cannot be observed')
    return out


@event.listens_for(Reading, 'before_insert')
@event.listens_for(Reading, 'before_update')
def _validate_reading(mapper, connection, target):
    held = None
    if target.artefact is not None:
        held = target.artefact.held
    elif target.artefact_id is not None:
        row = connection.execute(
            Artefact.__table__.select().where(Artefact.__table__.c.id == target.artefact_id)
        ).first()
        held = row.held if row is not None else None
    problems = reading_violations(target, held)
    if problems:
        raise ValueError('reading violated: ' + '; '.join(problems))


class Obligation(Base):
    """A continuant minted by the household's individuating assertion that it owes.
    Ruled `OBLIGATION_IDENTITY.md` s9 (2026-09-14).

    The anchor is structure plus a pointer to the minting utterance - and nothing else. No
    creditor, amount, kind, obligor, servicer, status, terms or account number lives here:
    every one of those is a CLAIM about the obligation (instrument kind, balance and terms as
    dated stances; entitled party, servicer, funder, risk-bearer and obligor as dated role
    relations over parties - s10's three layers are three kinds, not one field). That is why the
    obligation survives assignment, sale, write-off, recourse and restructure without a
    continuity algorithm: none of them touches the anchor (S4/S5: creditor and account number
    change, the obligation persists, so they cannot be its identity). It exists without a known
    creditor (Ob9). It is never minted by a bill, a statement, a payment or an inference - those
    yield candidates; a bill can describe a debt; only the household can say it owes one.

    The minting ACT is not the minted IDENTITY (Rob's emphasis). The obligation is not the
    utterance: the utterance mints it and supplies its anchor; the obligation thereafter exists
    as the continuant later propositions refer to. One utterance may mint several ("I have two
    loans with Chase"); retracting the minting utterance does not unmint (Ob12 - unminting is
    fenced, as for institutions).

    `DebtAccount` is a household assertion with descriptors fused onto one row - yes-shaped -
    and is decomposable into this identity only where its asserting party is a fact, which in
    production (zero Person rows) it is not. No synthetic migration: the ontology is settled
    before the migration data is.
    """
    __tablename__ = 'obligations'
    id           = Column(Integer, primary_key=True)
    minted_by_id = Column(Integer, ForeignKey('utterances.id'), nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    minted_by = relationship('Utterance')


@event.listens_for(Obligation, 'before_insert')
def _validate_obligation(mapper, connection, target):
    # NOT NULL covers the column; this covers the referent when foreign keys are not enforced
    # (production runs without the pragma): the minting utterance must exist.
    if target.minted_by is None:
        t = Utterance.__table__
        row = connection.execute(t.select().where(t.c.id == target.minted_by_id)).first() \
            if target.minted_by_id is not None else None
        if row is None:
            raise ValueError('an obligation exists only under the utterance that minted it')


def obligations_without_minting_utterance(session):
    """Audit: obligations whose minting utterance is missing. Empty is the invariant."""
    return [o for o in session.query(Obligation).all()
            if o.minted_by_id is None or session.get(Utterance, o.minted_by_id) is None]


# "Never merges rows, never rewrites a reference" (CORRESPONDENCE.md s4/s8), mechanically:
# the referential slots that make an event what it is - which artefact a reading observed,
# which party uttered, which things a claim is about - are immutable once the row exists.
# Re-pointing any of them is how a merge would be implemented, and a merge rewrites history.
# Unification happens only on read (`referent`, `artefact_origin`), never in the rows.
_IMMUTABLE_REFERENCES = {
    'Reading':     ('artefact_id',),
    'Utterance':   ('origin_party_id',),
    'Artefact':    ('asserted_by_id',),
    'Obligation':  ('minted_by_id',),
    'Proposition': ('kind', 'subject_party_id', 'subject_utterance_id', 'subject_artefact_id',
                    'subject_obligation_id',
                    'object_party_id', 'object_utterance_id', 'object_artefact_id',
                    'object_obligation_id'),
    'EvidentiaryRelationship': ('proposition_id', 'utterance_id', 'reading_id'),
}


def _refuse_repoint(mapper, connection, target):
    from sqlalchemy import inspect as _inspect
    state = _inspect(target)
    for col in _IMMUTABLE_REFERENCES[type(target).__name__]:
        hist = state.attrs[col].history
        if hist.has_changes() and hist.deleted and hist.deleted[0] is not None:
            raise ValueError(f'{type(target).__name__}.{col} is a reference and is never re-pointed '
                             f'({hist.deleted[0]!r} -> {hist.added[0]!r}); sameness is asserted by a '
                             f'correspondence claim and read by derivation, never written into rows')


def artefacts_with_inconsistent_assertion(session):
    """Audit: held artefacts under an utterance, or asserted artefacts under none. Empty is
    the invariant."""
    return [a for a in session.query(Artefact).all() if artefact_violations(a)]


def readings_without_one_reader(session):
    """Audit: readings with no reader or two. Empty is the invariant."""
    return [r for r in session.query(Reading).all()
            if sum(getattr(r, c) is not None for c in Reading.READER_SLOTS) != 1]


def readings_of_unheld_artefacts(session):
    """Audit: readings whose artefact is asserted, not held. Empty is the invariant - the
    mechanical form of never-RE-READ."""
    return [r for r in session.query(Reading).join(Artefact).filter(Artefact.held.is_(False)).all()]


class Proposition(Base):
    """A claim-shape: kind, subject, content - and, where the kind requires one, a second
    referential participant. Ruled `PROPOSITION.md` s7; representation ruled
    `SMALLEST_SCHEMA.md` s12.

    `kind` is primary: the knowing relation (who can be knowing for this) is defined over it,
    and nothing about a proposition can be computed before its kind is known. The kind
    CATALOGUE is not settled; the substrate carries whatever the ruled propositions require.

    Subject and second participant are explicit per-type referential slots, each governed by
    its own state column. `subject_state = established` means exactly one subject slot is set;
    any other state means every subject slot is NULL - and the same for the object side.
    "Not established with candidates" is a state; the candidates themselves are correspondence
    claims elsewhere, never a placeholder reference here. "None" is positive: the world, a
    process, or a kind that has no such participant. Enforced by `_validate_participants` on
    insert and update, and asserted by the fixture, because SQLite cannot express it.

    `content` is opaque and stays opaque - it is what is claimed, not a second schema. `as_of`
    is the date a dated kind is about (a stance as of d, an entitlement at d); it individuates
    the proposition, so it is a column rather than buried in content.

    NOT unique on (kind, subject, content), by ruling: proposition sameness beyond that
    minimum is a correspondence claim, and semantic sameness is not event identity. Nothing
    evidentiary lives on this row: what supports it is in `evidence`; its truth, resolution and
    strength are derived on read.

    Referent slots present: party, utterance (slice 1), artefact (slice 2), obligation
    (OBLIGATION_IDENTITY.md) - each additive. Further ruled referent types (a payment, a
    transaction, a plan, a claim) arrive only when their identity is ruled - a 1.x row is never
    presumed to be the thing (DOMAIN_PROPOSITION.md s4). Adding a slot never changes the state
    discipline.
    """
    __tablename__ = 'propositions'
    id                   = Column(Integer, primary_key=True)
    kind                 = Column(String(48), nullable=False)

    subject_state        = Column(String(32), nullable=False, default=PARTICIPANT_NONE)
    subject_party_id     = Column(Integer, ForeignKey('parties.id'), nullable=True)
    subject_utterance_id = Column(Integer, ForeignKey('utterances.id'), nullable=True)
    subject_artefact_id  = Column(Integer, ForeignKey('artefacts.id'), nullable=True)   # slice 2
    subject_obligation_id = Column(Integer, ForeignKey('obligations.id'), nullable=True) # obligation slice

    object_state         = Column(String(32), nullable=False, default=PARTICIPANT_NONE)
    object_party_id      = Column(Integer, ForeignKey('parties.id'), nullable=True)
    object_utterance_id  = Column(Integer, ForeignKey('utterances.id'), nullable=True)
    object_artefact_id   = Column(Integer, ForeignKey('artefacts.id'), nullable=True)    # slice 2
    object_obligation_id = Column(Integer, ForeignKey('obligations.id'), nullable=True)  # obligation slice

    content              = Column(Text, nullable=True)
    as_of                = Column(String(10), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)

    # The slot columns per participant side, so guards and future slices enumerate one list.
    SUBJECT_SLOTS = ('subject_party_id', 'subject_utterance_id', 'subject_artefact_id', 'subject_obligation_id')
    OBJECT_SLOTS  = ('object_party_id', 'object_utterance_id', 'object_artefact_id', 'object_obligation_id')

    __table_args__ = (
        Index('ix_prop_kind', 'kind'),
        Index('ix_prop_subject_party', 'subject_party_id'),
        Index('ix_prop_subject_utterance', 'subject_utterance_id'),
        Index('ix_prop_subject_artefact', 'subject_artefact_id'),
        Index('ix_prop_subject_obligation', 'subject_obligation_id'),
        Index('ix_prop_object_obligation', 'object_obligation_id'),
    )


def participant_violations(prop):
    """The state discipline, as a list of what is wrong with one proposition (empty = fine).

    established        -> exactly one slot on that side is set
    any other state    -> every slot on that side is NULL
    unknown state      -> a violation in itself

    And, for a RULED kind (`RULED_KINDS`, slice 4): both participants established, each in one
    of the slots that kind permits; a correspondence kind is never reflexive. Unruled kinds are
    not constrained beyond the state discipline - the catalogue stays open.
    """
    out = []
    for side, slots in (('subject', Proposition.SUBJECT_SLOTS),
                        ('object', Proposition.OBJECT_SLOTS)):
        state = getattr(prop, f'{side}_state')
        set_slots = [c for c in slots if getattr(prop, c) is not None]
        if state not in PARTICIPANT_STATES:
            out.append(f'{side}_state {state!r} is not a participant state')
        elif state == PARTICIPANT_ESTABLISHED and len(set_slots) != 1:
            out.append(f'{side}_state is established but {len(set_slots)} slot(s) are set: {set_slots}')
        elif state != PARTICIPANT_ESTABLISHED and set_slots:
            out.append(f'{side}_state is {state!r} but slot(s) are set: {set_slots}')
    rule = RULED_KINDS.get(getattr(prop, 'kind', None))
    if rule is not None and not out:
        for side in ('subject', 'object'):
            permitted = rule[side]
            state = getattr(prop, f'{side}_state')
            if not permitted:
                # A required ABSENCE: the kind has no such participant (utterance_retraction has
                # no second term - a replacement is a separate proposition, never an operand).
                if state != PARTICIPANT_NONE:
                    out.append(f'{prop.kind}: has no {side}; {side}_state must be none, is {state!r}')
                continue
            if state != PARTICIPANT_ESTABLISHED:
                out.append(f'{prop.kind}: {side} must be established, is {state!r}')
                continue
            set_slot = next(c for c in getattr(Proposition, f'{side.upper()}_SLOTS')
                            if getattr(prop, c) is not None)
            if set_slot not in permitted:
                out.append(f'{prop.kind}: {side} may be {permitted}, is {set_slot}')
        if rule['symmetric'] and not out:
            sub = getattr(prop, rule['subject'][0])
            obj = getattr(prop, rule['object'][0])
            if sub == obj:
                out.append(f'{prop.kind}: a thing does not correspond to itself')
    return out


@event.listens_for(Proposition, 'before_insert')
@event.listens_for(Proposition, 'before_update')
def _validate_participants(mapper, connection, target):
    # The column default (`none`) is applied at INSERT, after this hook runs - so an unset
    # state is applied here first. Nothing said about a participant means there is none.
    for side in ('subject', 'object'):
        if getattr(target, f'{side}_state') is None:
            setattr(target, f'{side}_state', PARTICIPANT_NONE)
    problems = participant_violations(target)
    if not problems and target.kind == PARTY_CORRESPONDS:
        problems = _foundation_violations(connection, target.subject_party_id, target.object_party_id)
    if problems:
        raise ValueError('proposition participant state violated: ' + '; '.join(problems))


def _foundation_violations(connection, a_id, b_id):
    """Correspondence never crosses foundations (the party-reference ruling): both parties
    must exist and both must have the same anchor kind. Person and institution may RELATE -
    a kind of its own, later - never be collapsed."""
    t = Party.__table__
    rows = {r.id: r for r in connection.execute(t.select().where(t.c.id.in_([a_id, b_id])))}
    if a_id not in rows or b_id not in rows:
        return ['party_corresponds: both parties must exist']
    fa = 'person' if rows[a_id].person_id is not None else 'institution'
    fb = 'person' if rows[b_id].person_id is not None else 'institution'
    if fa != fb:
        return [f'party_corresponds never crosses foundations ({fa} vs {fb})']
    return []


class EvidentiaryRelationship(Base):
    """*This proposition is evidenced by this utterance* (and, from slice 2, *or by this
    reading*). The table is named `evidence` because that is the eventual name; its semantic
    role is the RELATIONSHIP. Utterances and readings ARE the evidence - this row records which
    of them evidences which proposition, and must never be read as "the only thing that is
    evidence" (`SMALLEST_SCHEMA.md` s6, Rob's fence).

    One source per row: `utterance_id` xor `reading_id` (slice 2, additive). Exactly-one-source
    is a guard (`_validate_source`, `evidence_without_one_source`) because SQLite cannot add a
    CHECK to an existing table - which is why `utterance_id` was nullable from slice 1. At this
    row the two sources are symmetric: each evidences the proposition. Upstream they are not -
    an utterance is what a party said, a reading is what Groundwork saw of a held artefact - and
    `derived_strength` is where that asymmetry is enforced.

    No `supports` flag: a negative claim is a proposition with negative content evidenced here.
    No strength column: strength is `derived_strength(...)`, computed on read from the source's
    origin and the proposition's kind, so a stored value can never drift from the knowing
    relation that determines it.
    """
    __tablename__ = 'evidence'
    id             = Column(Integer, primary_key=True)
    proposition_id = Column(Integer, ForeignKey('propositions.id'), nullable=False)
    utterance_id   = Column(Integer, ForeignKey('utterances.id'), nullable=True)
    reading_id     = Column(Integer, ForeignKey('readings.id'), nullable=True)      # slice 2
    created_at     = Column(DateTime, default=datetime.utcnow)

    proposition = relationship('Proposition')
    utterance   = relationship('Utterance')
    reading     = relationship('Reading')

    SOURCE_SLOTS = ('utterance_id', 'reading_id')

    __table_args__ = (
        Index('ix_evidence_proposition', 'proposition_id'),
        Index('ix_evidence_utterance', 'utterance_id'),
        Index('ix_evidence_reading', 'reading_id'),
    )


def source_violations(relation):
    n = sum(getattr(relation, c) is not None for c in EvidentiaryRelationship.SOURCE_SLOTS)
    return [] if n == 1 else [f'exactly one source must be named, {n} are']


@event.listens_for(EvidentiaryRelationship, 'before_insert')
@event.listens_for(EvidentiaryRelationship, 'before_update')
def _validate_source(mapper, connection, target):
    problems = source_violations(target)
    if problems:
        raise ValueError('evidentiary relationship violated: ' + '; '.join(problems))


def evidence_without_one_source(session):
    """The relationship's forbidden state: a row naming no source, or more than one. Empty is
    the invariant; the audit half of the guard the constraint cannot be."""
    return [r for r in session.query(EvidentiaryRelationship).all() if source_violations(r)]


# ── Slice 3: the artefact-origin proposition kind and its derivation ─────────
# gw 2.0/ARTEFACT_ORIGIN.md, ruled s8. The first ruled entry in the proposition-kind catalogue.
#
# `artefact_origin` means EXACTLY: *this artefact is a statement by P* - subject the artefact,
# second participant the party whose knowledge the artefact's readings convey (contract C1).
# It does not mean who authored the file, who captured it, who transmitted it, who received
# it, or who is named in it (O4: captured by Rob, knowledge originating with Aetna). Rob's
# fence: no consumer or UI renames this "Issuer", "Created by", "Source" or "Author".
ARTEFACT_ORIGIN = 'artefact_origin'

# Origin STATE - read off the origin propositions, never a column on the artefact.
ORIGIN_ESTABLISHED = 'established'                        # one party, asserted by a party's utterance
ORIGIN_NOT_ESTABLISHED = 'not_established'                # no origin claim at all
ORIGIN_CANDIDATES = 'not_established_with_candidates'     # reading-sourced claims only (self-description, other documents)
ORIGIN_MULTIPLE = 'multiple'                              # utterance-sourced claims naming distinct parties


def artefact_origin(session, artefact):
    """The artefact's origin, derived: `(state, parties)`.

    Only a party's UTTERANCE establishes an origin. A reading of the artefact itself (the
    letterhead, O2) or of another artefact (Aetna's EOB naming Mercy, O6) yields a CANDIDATE
    and never establishes: a reading's strength would derive from the origin it established.
    *A document can say where it is from; only a party can say where a document is from.*

    Established means referentially asserted - not true (S3, forgery), not held (an asserted
    artefact has an origin, O10), not unique. Several utterance-sourced claims naming DISTINCT
    parties read as `multiple` with every party listed: whether that is a joint statement
    (O11) or competing claims (O8) needs a claim of correction or contradiction and a resolver
    over it - fenced - so this derivation reports the multiplicity and chooses nothing. Never
    by position, never by count, never by recency of recording.
    """
    props = (session.query(Proposition)
             .filter(Proposition.kind == ARTEFACT_ORIGIN,
                     Proposition.subject_artefact_id == artefact.id,
                     Proposition.object_state == PARTICIPANT_ESTABLISHED,
                     Proposition.object_party_id.isnot(None))
             .all())
    asserted, candidate = {}, {}
    for prop in props:
        for rel in session.query(EvidentiaryRelationship).filter_by(proposition_id=prop.id).all():
            if rel.utterance_id is not None:
                asserted.setdefault(prop.object_party_id, []).append(rel)
            elif rel.reading_id is not None:
                candidate.setdefault(prop.object_party_id, []).append(rel)
    if len(asserted) == 1:
        return ORIGIN_ESTABLISHED, list(asserted)
    if len(asserted) > 1:
        return ORIGIN_MULTIPLE, sorted(asserted)
    if candidate:
        return ORIGIN_CANDIDATES, sorted(candidate)
    return ORIGIN_NOT_ESTABLISHED, []


def _origin_claims(session, artefact, party_id):
    """The utterance-sourced relations asserting `artefact_origin(artefact, party_id)`."""
    return (session.query(EvidentiaryRelationship)
            .join(Proposition, EvidentiaryRelationship.proposition_id == Proposition.id)
            .filter(Proposition.kind == ARTEFACT_ORIGIN,
                    Proposition.subject_artefact_id == artefact.id,
                    Proposition.object_party_id == party_id,
                    EvidentiaryRelationship.utterance_id.isnot(None))
            .all())


# ── Slice 4: correspondence ──────────────────────────────────────────────────
# gw 2.0/CORRESPONDENCE.md, ruled s8. Two kinds: *X and Y are one referent*, for two separately
# minted identities of one type. Established ONLY by a party's utterance; every observed match
# (hash, import id, issuer string, description, date + origin) is a candidate with no party
# behind it, however strong its basis. The basis is the claim's CONTENT - shown to a person,
# never consulted by a derivation. Never merges rows, never rewrites a reference, never
# crosses foundations or types, never reflexive. Sameness is read, never stored.
#
# Vocabulary (Rob): *17 and 42 CORRESPOND; their derived referent CONTAINS both.* Never "17 and
# 42 are the same" - two identities, two histories, two arrival events remain.
#
# Not origin, not mention, not role: same origin is not same artefact (X2); a name in a
# document is content (X9); relatedness is another kind (X4).
ARTEFACT_CORRESPONDS = 'artefact_corresponds'
PARTY_CORRESPONDS = 'party_corresponds'
OBLIGATION_CORRESPONDS = 'obligation_corresponds'     # the third type (Ob7): two minted obligations, one referent

# ── Slice 8: about-ness ──────────────────────────────────────────────────────
# gw 2.0/ARTEFACT_ABOUTNESS.md, ruled s9. `artefact_concerns(A, X)` means EXACTLY: *this artefact
# concerns this identity* - subject the artefact, second participant an ALREADY-ESTABLISHED
# identity (the obligation now; each further identity as it is ruled). It PRESUPPOSES the
# identity: it does not mint, establish, identify or create it. It is asserted by a party's
# utterance under the ordinary discipline; whether that party is KNOWING for the relational
# claim is a separate, fenced question (relational_knowing -> undetermined). An observed match
# (account number, name, date) is a reading-sourced candidate for this claim and for nothing
# else - it never touches the evidence of anything the artefact says.
#
# The anti-collapse invariant: artefact_concerns(A, O) never changes the subject, participants,
# authority, evidence or history of any proposition derived from a reading of A. Values read
# from A keep their source's authority (via artefact_origin) and are about O only by a
# consumer's derivation through this claim - never by rewriting their own participants (which
# the immutability guard refuses anyway). About-ness is not endorsement (a wrong letter can
# concern the right debt) and needs no custody (an asserted artefact can concern an identity).
#
# Not the crossing: re-assertion - the household saying a value itself is testimony, a
# different proposition ("what does the household say about O?"), already representable.
# Not built: which of several identities a PARTICULAR read proposition concerns (a combined
# statement) - forced, reopening slice 5's finding, not designed here.
ARTEFACT_CONCERNS = 'artefact_concerns'

# The kind -> participant-slot registry, for RULED kinds only (the catalogue stays open; an
# unruled kind is constrained by the state discipline alone). Slice 3 fixed artefact_origin's
# shape by convention; convention is not enforcement - this tightens it retroactively, stated.
# `reading_establishes`: whether a reading-sourced claim of this kind can be more than a
# candidate. For all three it cannot - a document cannot vouch for its own origin, and bytes
# equal to bytes is an observation, not a party's assertion.
# ── Slice 5: the one higher-order kind ────────────────────────────────────────
# gw 2.0/CLAIM_ABOUT_CLAIM.md, ruled s7. `utterance_retraction` means EXACTLY: *the assertion
# made by utterance U no longer stands.* It is ABOUT the utterance - the act - not about the
# truth of the proposition the utterance contained. Subject: the utterance. Second
# participant: NONE, required - a replacement or contrary value is a separate domain
# proposition, which the same utterance may evidence (O8: one act, two propositions:
# utterance_retraction(U1) + artefact_origin(EOB, Mercy)). Content: the claimant's stance -
# text the derivations never read; the kind carries the whole meaning, and a retraction with
# empty content is complete.
#
# Correction is an interpretation of retraction + a new claim in one act, not a kind.
# Contradiction and reaffirmation are DERIVED relationships (Q2's resolver vocabulary), never
# stored kinds. Nothing here is a verdict: no column, accessor or function says "U1 is
# retracted"; U1, its evidence and everything under it remain; `multiple` and `contested` are
# untouched. The invariant, Rob's:
#
#     A higher-order claim can say that an utterance's assertion no longer stands.
#     It cannot itself rewrite, resolve, or replace that utterance.
#
# Strength: UNDETERMINED, always, in this slice. The knowing party for a retraction is the
# subject utterance's own origin - a relation between claimant and subject, which the
# foundation-keyed `knowing` map cannot express (P-ack's "entitled party of THIS obligation"
# is relational too). The relational form is a separate ruling, forced by the first consumer.
UTTERANCE_RETRACTION = 'utterance_retraction'

RULED_KINDS = {
    ARTEFACT_ORIGIN:      {'subject': ('subject_artefact_id',), 'object': ('object_party_id',),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': False},
    ARTEFACT_CORRESPONDS: {'subject': ('subject_artefact_id',), 'object': ('object_artefact_id',),
                           'symmetric': True,  'reading_establishes': False, 'relational_knowing': False},
    PARTY_CORRESPONDS:    {'subject': ('subject_party_id',),    'object': ('object_party_id',),
                           'symmetric': True,  'reading_establishes': False, 'relational_knowing': False},
    OBLIGATION_CORRESPONDS: {'subject': ('subject_obligation_id',), 'object': ('object_obligation_id',),
                           'symmetric': True,  'reading_establishes': False, 'relational_knowing': False},
    # object: the identities ruled so far. Grows additively as each further identity is minted.
    ARTEFACT_CONCERNS:    {'subject': ('subject_artefact_id',), 'object': ('object_obligation_id',),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True},
    # object: () - a REQUIRED absence, enforced (object_state must be `none`).
    UTTERANCE_RETRACTION: {'subject': ('subject_utterance_id',), 'object': (),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True},
}

REFERENT_SEPARATE = 'separate'                          # no established claim touches it
REFERENT_CANDIDATES = 'separate_with_candidates'        # reading-sourced claims only
REFERENT_CORRESPONDING = 'corresponding'                # at least one established claim; one component
REFERENT_CONTESTED = 'contested'                        # an establishing utterance is itself the subject of a claim

_CORRESPONDENCE_OF = {'Artefact':   (ARTEFACT_CORRESPONDS,   'subject_artefact_id',   'object_artefact_id'),
                      'Party':      (PARTY_CORRESPONDS,      'subject_party_id',      'object_party_id'),
                      'Obligation': (OBLIGATION_CORRESPONDS, 'subject_obligation_id', 'object_obligation_id')}


def referent(session, thing):
    """The derived referent of an artefact or a party: `(state, contains, candidates)`.

    `contains` is the connected component under ESTABLISHED correspondence claims - claims
    evidenced by a party's utterance - always including `thing` itself; a claim is read both
    ways (symmetric in meaning, stored once). `candidates` are the things reachable from the
    component only through reading-sourced claims (the importer's hash match, a description
    match): a reason to ask, never a member. Nothing here is stored; nothing here merges.

    `contested`: some establishing utterance in the component is itself the SUBJECT of a
    proposition - something has been said about the claim (Case B: "no, 42 was the corrected
    one"). WHAT was said is not derived: the correction/contradiction kinds and the resolver
    over them are fenced. So the state is reported fail-closed, the component is still
    returned in full, and nothing is chosen - never by position, recency of recording or count.
    """
    kind, sub_col, obj_col = _CORRESPONDENCE_OF[type(thing).__name__]
    claims = (session.query(Proposition, EvidentiaryRelationship)
              .join(EvidentiaryRelationship, EvidentiaryRelationship.proposition_id == Proposition.id)
              .filter(Proposition.kind == kind).all())
    established, candidate, establishing_utts = {}, {}, {}
    for prop, rel in claims:
        a, b = getattr(prop, sub_col), getattr(prop, obj_col)
        bucket = established if rel.utterance_id is not None else candidate
        bucket.setdefault(a, set()).add(b)
        bucket.setdefault(b, set()).add(a)
        if rel.utterance_id is not None:
            establishing_utts.setdefault(frozenset((a, b)), set()).add(rel.utterance_id)
    component, frontier = {thing.id}, [thing.id]
    while frontier:
        nxt = frontier.pop()
        for other in established.get(nxt, ()):
            if other not in component:
                component.add(other)
                frontier.append(other)
    cands = set()
    for member in component:
        cands |= candidate.get(member, set())
    cands -= component
    if len(component) == 1:
        return (REFERENT_CANDIDATES if cands else REFERENT_SEPARATE), [thing.id], sorted(cands)
    utts = set()
    for pair, ids in establishing_utts.items():
        if pair <= component:
            utts |= ids
    spoken_about = (session.query(Proposition)
                    .filter(Proposition.subject_utterance_id.in_(sorted(utts))).count() if utts else 0)
    state = REFERENT_CONTESTED if spoken_about else REFERENT_CORRESPONDING
    return state, sorted(component), sorted(cands)


STRENGTH_KNOWING = 'knowing'
STRENGTH_NOT_KNOWING = 'not_knowing'
STRENGTH_UNDETERMINED = 'undetermined'


def _weakest(*strengths):
    """Weakest link (contract C3): undetermined absorbs; not_knowing beats knowing."""
    if STRENGTH_UNDETERMINED in strengths:
        return STRENGTH_UNDETERMINED
    return STRENGTH_NOT_KNOWING if STRENGTH_NOT_KNOWING in strengths else STRENGTH_KNOWING


def _utterance_strength(session, utt, kind, knowing):
    if utt is None or kind not in knowing:
        return STRENGTH_UNDETERMINED
    party = utt.origin if utt.origin is not None else session.get(Party, utt.origin_party_id)
    if party is None:
        return STRENGTH_UNDETERMINED
    return STRENGTH_KNOWING if party_foundation(party) in knowing[kind] else STRENGTH_NOT_KNOWING


def derived_strength(session, relation, knowing):
    """Strength, computed on read and never stored.

    `knowing` is the knowing relation for proposition kinds - `{kind: {origin_kind, ...}}` -
    supplied by the caller because the kind catalogue is not settled (the health kinds' relation
    lives in `core.classification.KNOWING_SOURCES` today; P-ack's is "the entitled party only";
    P-world's is nobody). `origin_kind` is 'person' for a household-anchored party and
    'institution' for a minted one - which foundation, by a join to the anchor, never a kind
    column (the party-shape ruling). The one ruled entry (`ARTEFACT_ORIGIN.md` s4): for
    `artefact_origin` the recipient household and the origin party itself are knowing
    (`{'person', 'institution'}`); a third party's document and a parser are candidates only.

    Returns knowing / not_knowing / undetermined. Undetermined when the kind has no entry in
    the relation supplied: the absence of a rule is not a rule.

    UTTERANCE-sourced: the utterance's origin party's foundation x the proposition kind.

    READING-sourced (slice 3): the reading conveys the ARTEFACT'S origin's knowledge (C1) -
    never the reader's (C2; a member transcribing Aetna's EOB is not knowing for its figures,
    a parser is no party). So: the artefact's origin is derived (`artefact_origin`); if it is
    not a single established party the result is undetermined - nothing chosen among
    candidates or multiple claims; otherwise the strength is the WEAKEST LINK (C3) of
        knowing(kind, origin party's foundation)         - is P knowing for this kind?
        the strength of the origin claim itself           - how well is P established as origin?
    the second being the strongest of the agreeing claims naming P (parallel evidence for one
    referent is not a choice among referents). One link only: the capture-faithfulness and
    agency chains are fenced. O5's danger test holds by construction - Rob's spreadsheet has
    origin Rob, and Rob is not knowing for an insurer's figure, so relaying does not launder.
    """
    prop = relation.proposition
    if prop is None:
        prop = session.get(Proposition, relation.proposition_id)
    if prop is None:
        return STRENGTH_UNDETERMINED
    rule = RULED_KINDS.get(prop.kind)
    if rule is not None and rule.get('relational_knowing'):
        # The knowing party is defined relative to the SUBJECT (utterance_retraction: the
        # subject utterance's own origin), not by foundation. Not expressible in `knowing`;
        # not expanded here (CLAIM_ABOUT_CLAIM.md s3, s7). Undetermined until ruled.
        return STRENGTH_UNDETERMINED
    if relation.reading_id is not None or relation.reading is not None:
        if rule is not None and not rule['reading_establishes']:
            # A candidate, by ruling: the knowledge "these bytes equal those bytes" or "the
            # letterhead says Aetna" is nobody's - routing it through the artefact's origin
            # would score it by accident (CORRESPONDENCE.md s3).
            return STRENGTH_UNDETERMINED
        rd = relation.reading if relation.reading is not None else session.get(Reading, relation.reading_id)
        art = rd.artefact if rd.artefact is not None else session.get(Artefact, rd.artefact_id)
        state, parties = artefact_origin(session, art)
        if state != ORIGIN_ESTABLISHED or prop.kind not in knowing:
            return STRENGTH_UNDETERMINED
        origin = session.get(Party, parties[0])
        link = STRENGTH_KNOWING if party_foundation(origin) in knowing[prop.kind] else STRENGTH_NOT_KNOWING
        claim_strengths = [_utterance_strength(session, c.utterance, ARTEFACT_ORIGIN, knowing)
                           for c in _origin_claims(session, art, origin.id)]
        best = (STRENGTH_KNOWING if STRENGTH_KNOWING in claim_strengths
                else STRENGTH_NOT_KNOWING if STRENGTH_NOT_KNOWING in claim_strengths
                else STRENGTH_UNDETERMINED)
        return _weakest(link, best)
    utt = relation.utterance
    if utt is None:
        utt = session.get(Utterance, relation.utterance_id)
    return _utterance_strength(session, utt, prop.kind, knowing)


for _name in _IMMUTABLE_REFERENCES:
    event.listen(globals()[_name], 'before_update', _refuse_repoint)
del _name


class PersonAssignment(Base):
    """Which person an expense belongs to, as a version rather than a field.

    Deliberately NOT a `person_id` column on `healthcare_expenses`: that would be a mutable
    current-state field, and reassignment is a financially meaningful correction — it moves
    deductible and out-of-pocket accumulation, HSA eligibility and tax reporting. So it
    supersedes rather than overwrites, and carries reason, source and date.
    """
    __tablename__ = 'person_assignments'
    id          = Column(Integer, primary_key=True)
    expense_id  = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    person_id   = Column(Integer, ForeignKey('people.id'), nullable=False)
    mode        = Column(String(16), nullable=False)      # 'initial' | 'correction'
    seq         = Column(Integer, nullable=False)
    reason      = Column(String(200), nullable=True)
    source      = Column(String(40), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index('ix_person_assign_expense', 'expense_id'),)


class HealthPlan(Base):
    """A coverage period. Identity and dates only — terms are versioned separately, so this
    row never changes and a plan switch cannot rewrite the half-year before it."""
    __tablename__ = 'health_plans'
    id             = Column(Integer, primary_key=True)
    name           = Column(String(80), nullable=False)
    effective_from = Column(String(10), nullable=False)
    effective_to   = Column(String(10), nullable=True)
    seq            = Column(Integer, nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)


class HealthPlanTermVersion(Base):
    """Deductible and out-of-pocket maximum as of a point in the record.

    `previous_*` is what separates a correction from a first statement: discovering the
    deductible was $2,000 rather than $3,000 says the figure was always wrong, and the user is
    owed the old value when a number they were shown moves underneath them.
    """
    __tablename__ = 'health_plan_term_versions'
    id                  = Column(Integer, primary_key=True)
    plan_id             = Column(Integer, ForeignKey('health_plans.id'), nullable=False)
    deductible          = Column(Float, nullable=True)
    oop_max             = Column(Float, nullable=True)
    previous_deductible = Column(Float, nullable=True)
    previous_oop_max    = Column(Float, nullable=True)
    reason              = Column(String(200), nullable=True)
    source              = Column(String(40), nullable=True)
    seq                 = Column(Integer, nullable=False)
    recorded_at         = Column(DateTime, default=datetime.utcnow)


class HealthPlanOperation(Base):
    """`change` = what is true going forward. `correction` = what was always true. Collapsing
    these is how a plan switch silently rewrites February."""
    __tablename__ = 'health_plan_operations'
    id          = Column(Integer, primary_key=True)
    plan_id     = Column(Integer, ForeignKey('health_plans.id'), nullable=False)
    kind        = Column(String(16), nullable=False)      # 'change' | 'correction'
    seq         = Column(Integer, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class PersonEnrolment(Base):
    """A person survives a plan change; enrolment does not. Mutating a plan id on the person
    would destroy the first half of a year in which they switched, so enrolment is its own
    dated timeline."""
    __tablename__ = 'person_enrolments'
    id           = Column(Integer, primary_key=True)
    person_id    = Column(Integer, ForeignKey('people.id'), nullable=False)
    plan_id      = Column(Integer, ForeignKey('health_plans.id'), nullable=False)
    effective_on = Column(String(10), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)


class HealthcareExpense(Base):
    """Identity only. The amount is versioned, the person is assigned, and the plan is derived
    from the coverage period covering `incurred_on` — so nothing here is a mutable
    current-state field, and no figure can be rewritten by editing this row.

    There is deliberately no `plan_id`. `HealthPlan` periods are the single source of truth
    for which plan covered a date, and two sources for one fact is the fusion this whole
    architecture is written against.
    """
    __tablename__ = 'healthcare_expenses'
    id          = Column(Integer, primary_key=True)
    incurred_on = Column(String(10), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


class ExpenseObligationVersion(Base):
    """What the provider claims, and what it claimed before. Append-only, because a mutable
    amount cannot answer what the figure was in March."""
    __tablename__ = 'expense_obligation_versions'
    id            = Column(Integer, primary_key=True)
    expense_id    = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    amount        = Column(Float, nullable=False)
    effective_seq = Column(Float, nullable=False)
    recorded_seq  = Column(Integer, nullable=False)
    supersedes_id = Column(Integer, ForeignKey('expense_obligation_versions.id'))
    recorded_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index('ix_eov_expense', 'expense_id'),)


class ExpenseFundingAllocation(Base):
    """Money that moved, by funder, as a version chain rather than a mutable row.

    One expense can have three funders — insurer, HSA and the user — which a `reimbursed`
    boolean cannot represent. A correction writes a new row pointing at the one it supersedes,
    so "superseded, never overwritten" is true in the database and not only in the model.
    `cleared` + `attached` + `user_confirmed` is what confirms a payment; cleared alone is not
    enough, because it defaults to true.
    """
    __tablename__ = 'expense_funding_allocations'
    id             = Column(Integer, primary_key=True)
    expense_id     = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    funder         = Column(String(40), nullable=False)
    amount         = Column(Float, nullable=False)
    mode           = Column(String(24), nullable=False)   # allocated|corrected|reversed|reinstated|eob_import
    source         = Column(String(24), default='manual')
    cleared        = Column(Boolean, default=True)
    attached       = Column(Boolean, default=True)
    user_confirmed = Column(Boolean, default=True)
    duplicate_of   = Column(String(40), nullable=True)
    # When the money actually moved, which is not when the expense was incurred and not when
    # we heard about it. A 2027 reversal of a 2026 payment is a 2027 event affecting a 2026
    # expense, and collapsing those dates loses the year each belongs to.
    occurred_on    = Column(String(10), nullable=True)
    effective_seq  = Column(Float, nullable=False)
    recorded_seq   = Column(Integer, nullable=False)
    supersedes_id  = Column(Integer, ForeignKey('expense_funding_allocations.id'))
    recorded_at    = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index('ix_efa_expense', 'expense_id'),)


class ExpenseDetermination(Base):
    """What was concluded about an unresolved amount: a provider adjustment, paid in cash,
    unpaid, or a claim still pending. Not four flavours of one thing — `unpaid` and
    `pending_claim` give the same tax figure today and have different futures — and none of
    them terminal, so they are superseded rather than overwritten."""
    __tablename__ = 'expense_determinations'
    id            = Column(Integer, primary_key=True)
    expense_id    = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    status        = Column(String(32), nullable=False)
    amount        = Column(Float, nullable=False)
    evidence      = Column(String(80), nullable=True)
    rule_version  = Column(String(24), nullable=True)
    effective_seq = Column(Float, nullable=False)
    recorded_seq  = Column(Integer, nullable=False)
    supersedes_id = Column(Integer, ForeignKey('expense_determinations.id'))
    recorded_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index('ix_edet_expense', 'expense_id'),)


class ExpenseRefund(Base):
    """Money returned on an obligation that was correct.

    Its own table rather than another obligation version, because a refund is an event on the
    obligation and not a restatement of it — and because it names a recipient, which an
    obligation version has no business carrying. Three things reduce a number here and they
    must not be collapsed: a correction says the figure was always wrong, a refund says the
    care cost less in the end, and a reversal says a payment came back while the obligation
    stands.

    `to_funder` is what keeps a deduction honest. Without it the obligation falls and the
    payer still shows the full amount paid, overstating the deduction by exactly the refund.
    """
    __tablename__ = 'expense_refunds'
    id            = Column(Integer, primary_key=True)
    expense_id    = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    amount        = Column(Float, nullable=False)
    to_funder     = Column(String(40), nullable=True)
    occurred_on   = Column(String(10), nullable=True)
    effective_seq = Column(Float, nullable=False)
    recorded_seq  = Column(Integer, nullable=False)
    recorded_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index('ix_eref_expense', 'expense_id'),)


class ReserveTarget(Base):
    """How much reserve is wanted, and what kind of number that is.

    `basis` is what makes a change interpretable: without it, $6,000 becoming $8,000 is just a
    bigger number. `amount` is NULL for any derived basis — a target resolved from the plan's
    out-of-pocket maximum keeps no copy of the figure, so correcting the plan moves the target
    with nothing to reconcile. A stored copy would be two sources of truth for one fact.

    `kind` separates a preference change from a corrected fact from a new plan. They produce
    the same new number and mean different things, and `unspecified` exists because guessing
    between them would be manufacturing a classification from an unresolved state.

    `cleared` marks a target that was withdrawn. Deleting a target says nothing about the
    money, which lives in `reserve_contributions` and is untouched by it.
    """
    __tablename__ = 'reserve_targets'
    id          = Column(Integer, primary_key=True)
    basis       = Column(String(20), nullable=True)     # oop_max | custom | historical
    amount      = Column(Float, nullable=True)          # only where nothing derives it
    kind        = Column(String(20), nullable=False)    # initial|preference|fact|plan_change|unspecified
    source      = Column(String(40), nullable=True)
    reason      = Column(String(200), nullable=True)
    cleared     = Column(Boolean, default=False)
    seq         = Column(Integer, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class ReserveAllocation(Base):
    """How much of a balance is designated reserved, as of a date.

    **The frozen rule:** a reserve is an allocation of an existing financial state, recorded
    alongside the applicable balance. It does not modify the historical account balance and is
    not itself a transaction. So there is no account reference and no direction of movement
    here — nothing in this table can be read as money going anywhere.

    An allocation is a **level, not an accumulation**: each row supersedes the one before it,
    and $500 followed by $700 means $700 is reserved. `as_of` is what lets a balance from
    September be read against the allocation that was in force in September rather than
    today's, which is the same bitemporal property the rest of the model has.
    """
    __tablename__ = 'reserve_allocations'
    id          = Column(Integer, primary_key=True)
    amount      = Column(Float, nullable=False)
    as_of       = Column(String(10), nullable=True)
    reason      = Column(String(200), nullable=True)
    source      = Column(String(40), nullable=True)
    seq         = Column(Integer, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class TaxRuleVersion(Base):
    """Which tax rule set was in force, as a household-level timeline.

    Not a column on an expense: the rules are not a property of a charge. This exists because
    a historical conclusion must never depend on an unversioned interpretation of the present
    — the C1 defect the necessity floor demonstrated, where a rule changed and every prior
    judgement quietly became unreproducible.
    """
    __tablename__ = 'tax_rule_versions'
    id            = Column(Integer, primary_key=True)
    version       = Column(String(24), nullable=False)
    effective_seq = Column(Float, nullable=False)
    recorded_seq  = Column(Integer, nullable=False)
    recorded_at   = Column(DateTime, default=datetime.utcnow)


class ExpenseMergeLink(Base):
    """Two records found to be one. A single foreign key cannot hold two sources, which is
    what a link table is for — and both provenances have to survive the merge."""
    __tablename__ = 'expense_merge_links'
    id             = Column(Integer, primary_key=True)
    merged_into_id = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    merged_from_id = Column(Integer, ForeignKey('healthcare_expenses.id'), nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)


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


def people_without_party(session):
    """The forbidden state, as a query: every `Person` with no `Party` anchor. Empty is the
    invariant; non-empty is what the guard reports and the backfill repairs."""
    return (session.query(Person)
            .outerjoin(Party, Party.person_id == Person.id)
            .filter(Party.id.is_(None))
            .all())


def backfill_party_anchors(session):
    """Mint the missing anchors. Idempotent by construction - it only ever creates what
    `people_without_party` reports - and today finds nothing in production, where no route
    has ever created a `Person`. Exists so a database that predates the construction (a test
    database; a future upgrade path) becomes conformant, and as the audit the constraint
    cannot be."""
    missing = people_without_party(session)
    for p in missing:
        session.add(Party(person_id=p.id))
    session.flush()
    return len(missing)


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
