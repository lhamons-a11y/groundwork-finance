"""
Groundwork — Core Database Layer
Column names match server.py exactly.
"""
import itertools
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
# Relation semantics (RELATION_SEMANTICS.md), one relation at a time - pass A: payment_counteracts, the
# asserting party holds that the subject payment economically counteracts some or all of the object payment;
# directional, no inverse, no cardinality, no amount, no status, no netting, no transitivity; knowing undetermined.
# Role period (ROLE_PERIOD.md): a role has NO intrinsic period; began / ended are propositions in their own
# right - boundary kinds bound to their role kind in the registry, `as_of` the date asserted about; a
# boundary never rewrites, implies its opposite, resolves, establishes continuous effect or creates a role.
# Plan (PLAN_IDENTITY.md): an identity for a coverage arrangement the household individuates - its being
# covered under an insurer's product, not the product; the insurer's product name and plan / group /
# member identifiers are content and correspondence evidence; terms, period, members, premium are claims.
# Expense (EXPENSE_IDENTITY.md): an event identity for an incurrence the household individuates;
# the household's assertion mints it, other parties assert claims about it but do not mint it;
# nature / category / amounts are claims; a source's category never mints or establishes nature.
# Relational knowing (RELATIONAL_KNOWING.md): knowing = a derived classification of an evidentiary
# relationship - the kind-designated relation to the kind-designated participant; named relations
# only, no generic resolver; not_knowing = not the identified party; Kn7: minting != knowing.
# proposition_corresponds (PROPOSITION_CORRESPONDENCE.md): two observations/recordings of one claim;
# relational never transmissive; g1 - established same-type participants may not disagree.
# Ab7 (PROPOSITION_ABOUTNESS.md): proposition_concerns - a proposition as subject, narrowly; about-ness
# is information about a proposition, not inserted into it; the one-source guard.
# Payment (PAYMENT_IDENTITY.md): an event identity minted by a Person's assertion that it occurred;
# not a transaction, not discharge, not a confirmation state; payment slots; payment_corresponds;
# artefact_concerns gains the payment object slot. The minting guard now requires a Person origin
# for obligations too.
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


def _minting_violations(target, connection, noun):
    """The minting act for a household-minted identity: the utterance must exist (the referent
    check foreign keys would do if the pragma were on) and must ORIGINATE FROM A PERSON - both
    identity rulings say *an individuating assertion originating from a Person*. A bank line, a
    creditor's statement, a draft or any institution-origin utterance yields a candidate and
    never mints. Payment slice, 2026-09-14: the Person requirement is enforced here for
    obligations too - the ruling said it; the obligation build had only stated it."""
    utt = target.minted_by
    if utt is None:
        t = Utterance.__table__
        utt = connection.execute(t.select().where(t.c.id == target.minted_by_id)).first() \
            if target.minted_by_id is not None else None
    if utt is None:
        return [f'{noun} exists only under the utterance that minted it']
    pt = Party.__table__
    origin = connection.execute(pt.select().where(pt.c.id == utt.origin_party_id)).first()
    if origin is None or origin.person_id is None:
        return [f'{noun} is minted only by an assertion originating from a Person - '
                f'an institution-origin utterance yields a candidate, never an identity']
    return []


@event.listens_for(Obligation, 'before_insert')
def _validate_obligation(mapper, connection, target):
    problems = _minting_violations(target, connection, 'an obligation')
    if problems:
        raise ValueError('; '.join(problems))


def obligations_without_minting_utterance(session):
    """Audit: obligations whose minting utterance is missing. Empty is the invariant."""
    return [o for o in session.query(Obligation).all()
            if o.minted_by_id is None or session.get(Utterance, o.minted_by_id) is None]


class Payment(Base):
    """A payment is an event identity. Ruled `PAYMENT_IDENTITY.md` s8/s10 (2026-09-14).

    An individuating assertion originating from a Person mints that identity; the asserting
    utterance is the minting act, not the payment. Minting establishes the identity, not the
    truth of any property asserted about the event - the assertion may be false and p still
    exists, as the payment event individuated by that assertion.

    The anchor is structure plus a pointer to the minting utterance and nothing else: payer,
    payee, amount, date, method, purpose, clearance, attachment, acknowledgment, discharge and
    reversal are NOT identity properties. They are claims about the payment, made by the party
    knowing for that claim - the bank for movement, the entitled party for acknowledgment
    (which IS the discharge claim, by definition, and does not establish the payment's
    existence), the household for what it was toward and to whom it was meant. Payer and payee
    are dated relations; `minted_by` names the asserting act, never the payer (Pm9: "my mother
    paid Mercy for me" - Rob asserts, the mother is `paid_by`).

    `created_at` is when this row was written - identity creation time - and is never the
    occurred date: a payment entered in September for one asserted to have occurred in March
    keeps March as a claim's `as_of` (the same discipline as asserted_at vs recorded_at).

    A payment is not a transaction (it may have none - cash; a debit may be no payment - a
    transfer to one's own savings), not discharge (it exists before, without or despite
    acknowledgment), not a "confirmed payment" (cleared / attached / user-confirmed are claims
    about an existing payment). A bank line, ledger row, draft or entitled-party statement can
    produce a candidate but cannot mint it - `_validate_payment` refuses a minting utterance
    that does not originate from a Person.

    Relations stay typed: `payment_corresponds` (separately minted identities later established
    as one referent - derived, never merged); `paid_by` / `paid_to` (role claims); `toward(p, O)`
    (a household claim; it does not establish discharge, as payee does not establish
    entitlement); `artefact_concerns(A, p)` for the payment's own record. A LINE in a statement
    needs proposition-level about-ness (Ab7), a separate ruling. A candidate match does not
    establish correspondence: similarity generates a candidate; it does not establish identity.
    """
    __tablename__ = 'payments'
    id           = Column(Integer, primary_key=True)
    minted_by_id = Column(Integer, ForeignKey('utterances.id'), nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    minted_by = relationship('Utterance')


@event.listens_for(Payment, 'before_insert')
def _validate_payment(mapper, connection, target):
    problems = _minting_violations(target, connection, 'a payment')
    if problems:
        raise ValueError('; '.join(problems))


def payments_without_minting_utterance(session):
    """Audit: payments whose minting utterance is missing or does not originate from a Person.
    Empty is the invariant."""
    out = []
    for pm in session.query(Payment).all():
        utt = session.get(Utterance, pm.minted_by_id) if pm.minted_by_id is not None else None
        if utt is None or party_foundation(utt.origin) != 'person':
            out.append(pm)
    return out


class Expense(Base):
    """An expense is a Groundwork event identity for an incurrence that the household
    individuates - a visit, a purchase, or a service received. Ruled `EXPENSE_IDENTITY.md` s8
    (2026-09-14).

    The household's individuating assertion mints the identity; other parties - the provider
    ("the service occurred"), the insurer ("these amounts were allowed"), the bank ("this
    movement occurred") - may assert claims about the expense but do not thereby mint it:
    identity authority is not epistemic authority. The asserting utterance is the minting act,
    not the expense; minting establishes the identity, not the truth of any property.

    The anchor is structure plus a pointer to the minting utterance and nothing else. Date of
    service, provider, who incurred it, nature on either axis, care necessity, category and every
    monetary amount (billed, allowed, plan-paid, patient responsibility, household-paid) are
    CLAIMS about the expense - the D1 classification and the D3 value claim take this identity as
    their subject; P-subject stays with the artefact. A source's category for a movement or a
    line is content of the source's statement and at most a candidate for a classification claim:
    it never mints an expense and never establishes its nature; a classification a process
    proposes is a candidate until a party asserts it (decision 9 stands).

    An expense is not a movement (it may have none, or several), not a payment, not an obligation
    (each exists without the other - a fully covered visit; a loan - and the obligation arising
    from an expense is a separate identity related to it by a claim whose kind is NOT ruled), not
    the insurer's claim (the EOB is the insurer's statement about the expense; its claim number
    is correspondence evidence), not a classification, not a source record. Bills, EOBs, receipts
    and lines concern it (the concerns kinds); two expenses later said to be one incurrence
    correspond and are never merged; the household decides the granularity (one visit, or the
    hospital, the radiologist and the lab).

    The 1.x `HealthcareExpense(id, incurred_on, created_at)` was already identity-only; 2.0 adds
    the minting provenance and moves `incurred_on` to a claim. It is decomposable only where its
    asserting party is a fact - not in production. `created_at` is when this row was written,
    never the date of service.
    """
    __tablename__ = 'expenses'
    id           = Column(Integer, primary_key=True)
    minted_by_id = Column(Integer, ForeignKey('utterances.id'), nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    minted_by = relationship('Utterance')


@event.listens_for(Expense, 'before_insert')
def _validate_expense(mapper, connection, target):
    problems = _minting_violations(target, connection, 'an expense')
    if problems:
        raise ValueError('; '.join(problems))


def expenses_without_minting_utterance(session):
    """Audit: expenses whose minting utterance is missing or does not originate from a Person."""
    out = []
    for x in session.query(Expense).all():
        utt = session.get(Utterance, x.minted_by_id) if x.minted_by_id is not None else None
        if utt is None or party_foundation(utt.origin) != 'person':
            out.append(x)
    return out


class Plan(Base):
    """A plan is a Groundwork identity for a coverage arrangement that the household individuates
    - its being covered under an insurer's product, not the insurer's product - minted by a
    Person's individuating assertion. Ruled `PLAN_IDENTITY.md` s7 (2026-09-14).

    The insurer's assertion mints nothing: its product name and its plan, group and member
    identifiers are content and correspondence evidence; the card, the SBC and the portal are
    artefacts whose encounter mints only the artefact. Two households on one product have two
    plans. The minting act establishes only the identity - "we have a plan" with no terms, no
    document and no identifier is a plan (Pl15): the arrangement exists as an identity before
    Groundwork knows anything substantive about it, and unknown terms are ABSENT term claims,
    never a zero and never an inferred nonexistence.

    The anchor is structure plus the minting utterance and nothing else. The insurer, the
    product, the terms (deductible, copay, out-of-pocket maximum, coinsurance), the effective
    period, who is covered and when, the premium, and whether it covered any expense are CLAIMS.
    Coverage of a person under a plan is a dated relation with the plan as an endpoint (item 5,
    not ruled); the premium is an obligation and payments, tied to the plan only by a relation
    claim (item 6, not ruled); which plan covered an expense is a relation claim or a consumer
    derivation, never a field on the expense; an authorization is the insurer's dated stance
    about a prospective service - no expense exists yet; an accumulator is the insurer's dated
    stance or a consumer's derivation; responsibility is a proposition about the expense.

    "Coverage arrangement" is the referent of this row and acquires no ontology by implication:
    there is no ruled coverage relation, contract, enrollment, benefit object or legal agreement.
    Whether a renewal, a COBRA continuation or a changed deductible is the same plan or a new one
    is the household's individuation choice, corrected later by `plan_corresponds` if two
    assertions individuated one arrangement differently - never a licence for arbitrary
    duplicates, and never decided by `created_at`, product ID, plan year or changing terms. A
    terminated, disputed or superseded plan remains minted: identity is not truth or currency.

    The 1.x `HealthPlan` / `HealthPlanTermVersion` rows fuse the plan with household-asserted
    terms; they are untouched and not decomposed. `created_at` is when this row was written,
    never an effective date.
    """
    __tablename__ = 'plans'
    id           = Column(Integer, primary_key=True)
    minted_by_id = Column(Integer, ForeignKey('utterances.id'), nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    minted_by = relationship('Utterance')


@event.listens_for(Plan, 'before_insert')
def _validate_plan(mapper, connection, target):
    problems = _minting_violations(target, connection, 'a plan')
    if problems:
        raise ValueError('; '.join(problems))


def plans_without_minting_utterance(session):
    """Audit: plans whose minting utterance is missing or does not originate from a Person."""
    out = []
    for p in session.query(Plan).all():
        utt = session.get(Utterance, p.minted_by_id) if p.minted_by_id is not None else None
        if utt is None or party_foundation(utt.origin) != 'person':
            out.append(p)
    return out


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
    'Payment':     ('minted_by_id',),
    'Expense':     ('minted_by_id',),
    'Plan':        ('minted_by_id',),
    'Proposition': ('kind', 'subject_party_id', 'subject_utterance_id', 'subject_artefact_id',
                    'subject_obligation_id', 'subject_payment_id', 'subject_proposition_id',
                    'subject_expense_id', 'subject_plan_id',
                    'object_party_id', 'object_utterance_id', 'object_artefact_id',
                    'object_obligation_id', 'object_payment_id', 'object_proposition_id',
                    'object_expense_id', 'object_plan_id'),
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
    subject_payment_id   = Column(Integer, ForeignKey('payments.id'), nullable=True)     # payment slice
    subject_expense_id   = Column(Integer, ForeignKey('expenses.id'), nullable=True)     # expense slice
    subject_plan_id      = Column(Integer, ForeignKey('plans.id'), nullable=True)        # plan slice
    # Ab7 (PROPOSITION_ABOUTNESS.md): a PROPOSITION as subject - narrowly. The only ruled kind that
    # uses it is proposition_concerns; slice 5's finding is reopened on that evidence and narrowed,
    # not reversed (truth / contradiction / reaffirmation claims about a proposition stay non-kinds).
    subject_proposition_id = Column(Integer, ForeignKey('propositions.id'), nullable=True)
    # proposition_corresponds (PROPOSITION_CORRESPONDENCE.md): the object-side proposition slot, forced
    # because a correspondence has two participants of one type - used by that kind alone. The
    # proposition-participant taxonomy stays explicit and asymmetric: proposition_concerns -> subject;
    # proposition_corresponds -> object (and subject); the slice-5 non-kinds -> neither.
    object_proposition_id  = Column(Integer, ForeignKey('propositions.id'), nullable=True)

    object_state         = Column(String(32), nullable=False, default=PARTICIPANT_NONE)
    object_party_id      = Column(Integer, ForeignKey('parties.id'), nullable=True)
    object_utterance_id  = Column(Integer, ForeignKey('utterances.id'), nullable=True)
    object_artefact_id   = Column(Integer, ForeignKey('artefacts.id'), nullable=True)    # slice 2
    object_obligation_id = Column(Integer, ForeignKey('obligations.id'), nullable=True)  # obligation slice
    object_payment_id    = Column(Integer, ForeignKey('payments.id'), nullable=True)     # payment slice
    object_expense_id    = Column(Integer, ForeignKey('expenses.id'), nullable=True)     # expense slice
    object_plan_id       = Column(Integer, ForeignKey('plans.id'), nullable=True)        # plan slice

    content              = Column(Text, nullable=True)
    as_of                = Column(String(10), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)

    # The slot columns per participant side, so guards and future slices enumerate one list.
    SUBJECT_SLOTS = ('subject_party_id', 'subject_utterance_id', 'subject_artefact_id', 'subject_obligation_id',
                     'subject_payment_id', 'subject_proposition_id', 'subject_expense_id', 'subject_plan_id')
    OBJECT_SLOTS  = ('object_party_id', 'object_utterance_id', 'object_artefact_id', 'object_obligation_id',
                     'object_payment_id', 'object_proposition_id', 'object_expense_id', 'object_plan_id')

    __table_args__ = (
        Index('ix_prop_kind', 'kind'),
        Index('ix_prop_subject_party', 'subject_party_id'),
        Index('ix_prop_subject_utterance', 'subject_utterance_id'),
        Index('ix_prop_subject_artefact', 'subject_artefact_id'),
        Index('ix_prop_subject_obligation', 'subject_obligation_id'),
        Index('ix_prop_object_obligation', 'object_obligation_id'),
        Index('ix_prop_subject_payment', 'subject_payment_id'),
        Index('ix_prop_object_payment', 'object_payment_id'),
        Index('ix_prop_subject_proposition', 'subject_proposition_id'),
        Index('ix_prop_object_proposition', 'object_proposition_id'),
        Index('ix_prop_subject_expense', 'subject_expense_id'),
        Index('ix_prop_object_expense', 'object_expense_id'),
        Index('ix_prop_subject_plan', 'subject_plan_id'),
        Index('ix_prop_object_plan', 'object_plan_id'),
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
        # Two participants means two: a kind whose subject and object are the same single type
        # (the correspondences; payment_counteracts; obligation_replaces) is never reflexive - a
        # thing does not correspond to, counteract, or replace itself.
        if not out and len(rule['subject']) == 1 and len(rule['object']) == 1 and (
                rule['symmetric'] or rule['subject'][0].replace('subject_', '') == rule['object'][0].replace('object_', '')):
            sub = getattr(prop, rule['subject'][0])
            obj = getattr(prop, rule['object'][0])
            if sub == obj:
                out.append(f'{prop.kind}: a thing does not stand in this relation to itself')
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
    if not problems and target.kind == PROPOSITION_CONCERNS:
        problems = _aboutness_violations(connection, target)
    if not problems and target.kind == PROPOSITION_CORRESPONDS:
        problems = _proposition_correspondence_violations(connection, target)
    if not problems:
        problems = _boundary_violations(target)
    if problems:
        raise ValueError('proposition participant state violated: ' + '; '.join(problems))


# The identity slots a proposition can carry, by type - the columns g1 compares, same column on
# both rows. Participant STATE columns, kind, content, as_of and evidence are not in this list and
# g1 never reads them.
_IDENTITY_SLOT_COLUMNS = ('subject_party_id', 'subject_utterance_id', 'subject_artefact_id',
                          'subject_obligation_id', 'subject_payment_id', 'subject_proposition_id',
                          'subject_expense_id', 'subject_plan_id',
                          'object_party_id', 'object_utterance_id', 'object_artefact_id',
                          'object_obligation_id', 'object_payment_id', 'object_proposition_id',
                          'object_expense_id', 'object_plan_id')


def _proposition_correspondence_violations(connection, target):
    """g1 (PROPOSITION_CORRESPONDENCE.md s4/s7), narrowly: both propositions must exist, and a
    correspondence may not identify one referent when the two propositions' ALREADY-ESTABLISHED
    same-type structural participants explicitly disagree - one claim cannot have two established
    structural subjects. g1 inspects established participants only: never candidates,
    proposition_concerns, content, kind, evidence, reading position, authority or semantic
    similarity. It is not a "these don't seem equivalent" validator and must not become one."""
    t = Proposition.__table__
    rows = {}
    for pid in (target.subject_proposition_id, target.object_proposition_id):
        if pid is None:
            return ['proposition_corresponds: both propositions must be named']
        rows[pid] = connection.execute(t.select().where(t.c.id == pid)).first()
        if rows[pid] is None:
            return ['proposition_corresponds: both propositions must exist']
    a, b = rows[target.subject_proposition_id], rows[target.object_proposition_id]
    for col in _IDENTITY_SLOT_COLUMNS:
        va, vb = getattr(a, col), getattr(b, col)
        if va is not None and vb is not None and va != vb:
            return [f'proposition_corresponds: the two propositions have established {col} participants '
                    f'that disagree ({va} vs {vb}) - one claim cannot have two established structural subjects']
    return []


def _aboutness_violations(connection, target):
    """proposition_concerns(P, X) attaches only to a proposition P that exists and has NO
    established participant of X's identity type (PROPOSITION_ABOUTNESS.md, Pa10): P's
    participant slot is structural participation; the concerns claim is a claim about what P is
    about; once the structural participant is established, P's about-ness is already
    structurally established, and the claim may not provide a competing source for it. Two
    representations of one fact that can drift are what the one-source rule forbids. And a
    proposition never concerns itself."""
    t = Proposition.__table__
    subj = connection.execute(t.select().where(t.c.id == target.subject_proposition_id)).first() \
        if target.subject_proposition_id is not None else None
    if subj is None:
        return ['proposition_concerns: the subject proposition must exist']
    if target.id is not None and subj.id == target.id:
        return ['proposition_concerns: a proposition does not concern itself']
    for slot in RULED_KINDS[PROPOSITION_CONCERNS]['object']:
        if getattr(target, slot) is None:
            continue
        kind_suffix = slot[len('object_'):]                     # e.g. 'obligation_id'
        for side in ('subject_', 'object_'):
            if getattr(subj, side + kind_suffix) is not None:
                return [f'proposition_concerns: the subject proposition already has an established '
                        f'{kind_suffix[:-3]} participant - its about-ness is structurally established; '
                        f'to re-identify it, retract its utterance and assert anew (Case B)']
    return []


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
PAYMENT_CORRESPONDS = 'payment_corresponds'           # the fourth (Pm8 b): two minted payments, one referent
EXPENSE_CORRESPONDS = 'expense_corresponds'           # the sixth type (Ex7): two minted expenses, one incurrence
PLAN_CORRESPONDS = 'plan_corresponds'                 # the seventh (Pl4 / Pl13): two minted plans, one arrangement

# ── Item 6, pass A: the payment-to-payment relation ──────────────────────────
# gw 2.0/RELATION_SEMANTICS.md s A.6, ruled 2026-09-15. `payment_counteracts(p2, p1)` means EXACTLY:
# *the asserting party holds that the subject payment economically counteracts some or all of
# the object payment.* Both participants are established payments - the claim mints neither and
# merges neither. Directional: the counteracting payment is the subject; never symmetric; no
# inverse kind ("p1 was counteracted by p2" is this claim read backwards); no cardinality - one
# refund may counteract several payments and one payment may be counteracted by several. It is
# established only by a party's assertion - the household, or the issuer of the counteracting
# payment; a reading, a matcher or a bank's REFUND label yields at most a candidate. It carries NO
# amount ("some or all" is the scope of the assertion, not a field), requires NO payer/payee
# mirroring (a refund may land on a different card), and derives NOTHING: no net or remaining, no
# discharge, no `reversed`/`refunded` status on either payment, no transitivity along a chain
# (p3 counteracts p2 says nothing of p1), no amount validation, no period from RP2. Refund,
# chargeback, return, partial and goodwill are content or separate claims about the counteracting
# payment, never kinds. Where no second payment is individuated there is no relation - a failed,
# returned, unapplied or voided payment remains a dated claim about the one payment (REVERSAL C).
# Knowing: relational_knowing True with no designated relation -> undetermined; the designated
# participant would be the payer of the subject payment, a role not ruled. Not a source word.
PAYMENT_COUNTERACTS = 'payment_counteracts'

# ── Item 6, pass B: the obligation-to-obligation relation ────────────────────
# gw 2.0/RELATION_SEMANTICS.md s B.7, ruled 2026-09-15. Of Rob's five phenomena - changed terms,
# a transfer of servicing (assignment, sale, recourse), a new dated stance, an ending and a
# beginning, a refinancing - FOUR are not obligation-to-obligation at all: terms claims, dated role
# claims and stances on ONE obligation, and two independent facts about two obligations that
# establish nothing about each other. The fifth is one claim with two obligation operands, forced
# by K8 (a referential operand is a participant), not by M2 (closed). `obligation_replaces(O3, O1)`
# means EXACTLY: *the asserting party holds that the subject obligation was incurred in substitution
# for some or all of the object obligation.* It says WHY the subject exists in relation to the object,
# not what happened afterward to the object - "in substitution for" is not a temporal or lifecycle
# assertion. Both participants are established obligations - the claim mints neither and merges
# neither. Directional: the replacing obligation is the subject; never symmetric; no inverse kind;
# no cardinality - one loan may replace several cards (B4) and one bill may be split into several
# plans (B6). Established only by a party's assertion - the household, or the new lender; a reading,
# a matcher, a PAYOFF line or "your new account" yields at most a candidate. It carries NO amount
# ("some or all" is the scope of the assertion, not a field), NO transfer semantics (the
# economic-transfer invariant's disposition, 8.1-b, is a claim of its own shape, fenced to that
# invariant's consumer - obligation_replaces does not explain where money went), and derives
# NOTHING: no ending, discharge, settled, closed or replaced status on the object (B15: the payoff
# is $40 short and the creditor keeps billing - both facts stand), no beginning on the subject (it
# was minted, not begun), no remaining, no transitivity along a chain, no apportionment among
# several, no period from RP2 (an obligation is not a role), no inference of which Ob6 arm the
# household meant. Refinance, consolidation, rollover, balance transfer, restructure and payment
# plan are content or claims about the replacing obligation, never kinds; a modification is the
# first arm and no relation at all; the same obligation under a new account number is Ob7
# (obligation_corresponds), not this kind. Where no second obligation is individuated there is no
# relation - a paid-off, closed, written-off or transferred obligation remains one obligation under
# dated claims. Knowing: relational_knowing True with no designated relation -> undetermined; neither
# the obligor of the subject nor the entitled party of the object is semantically forced by the
# relation, and participation in an obligation is not an epistemic rule. Not a source word.
OBLIGATION_REPLACES = 'obligation_replaces'

# ── Item 6, pass G: THE IN-RESPECT-OF FAMILY - the contract stated once ───────
# gw 2.0/RELATION_SEMANTICS.md s G.9, ruled 2026-09-16. Six kinds have IDENTICAL relational semantics
# after subject and object types are treated as parameters; their only semantic specialisation is the
# established type of each participant slot:
#
#     obligation_in_respect_of              obligation -> expense     (C,  built)
#     payment_in_respect_of                 payment    -> expense     (D,  built)
#     payment_in_respect_of_obligation      payment    -> obligation  (D', built)
#     expense_in_respect_of_plan            expense    -> plan        (E,  accepted, unbuilt)
#     obligation_in_respect_of_plan         obligation -> plan        (E,  accepted, unbuilt)
#     payment_in_respect_of_plan            payment    -> plan        (E,  accepted, unbuilt)
#
# THE FLOOR, once: a member means EXACTLY *the asserting party holds that the subject is in respect
# of the object* - both participants established (the claim mints neither); direction fixed by
# participant type and carrying no meaning (no reverse claim, no inverse kind, navigation either way
# a query); no cardinality (and cardinality is not allocation); established only by a party's
# assertion with both endpoints established - a reading, matcher, label, figure or document
# concerning both yields at most a candidate; relational_knowing True with no designated relation
# -> undetermined; it derives NOTHING - no amount, status, discharge, coverage, direction of money,
# temporal precedence or property projection. Each member keeps its own NOT-list beside its constant
# (E15's "what the plan didn't cover" is not C6's reconciliation).
#
# The family is a shared FLOOR, not a shared PATH: members do not compose with each other or with
# any other kind (C9, D8, D15, D'15, E15, E18, E19, F13/F14 restated, deciding nothing about the
# open composition question D'.11); the family licenses no inverse and no coverage relation from
# its existence. Each pass reached the floor separately after rejecting a source word
# (arises_from, funds, toward, under); the parallel is a RESULT, and the family adds no semantics
# to any member.
#
# REPRESENTATION: six kinds, as the seven correspondence kinds carry one shape (_CORRESPONDENCE_OF).
# A single typed-slot `in_respect_of` kind is REFUSED on structure: the registry's slots are per
# side, so one kind would permit the cross product - nine pairs - of which six are ruled and three
# were refused by name (expense -> obligation is C's inverse; obligation -> obligation is B's
# territory; payment -> payment is A's); a pair guard would be new machinery reproducing six
# entries while inviting intra-kind transitivity. artefact_concerns is no precedent (fixed subject,
# every object type ruled: its cross product IS its ruled set). The common implementation
# abstraction is RULED_KINDS and its guards - built before any ruling, carrying none; no relation
# base, family resolver, cross-pair selector or inverse accessor exists or is permitted.
# smoke_sections/s106_relation_family.py pins these invariants as a regression; it does not
# define the family, and it asserts nothing about composition.

# ── Item 6, pass C: the obligation-to-expense relation ───────────────────────
# gw 2.0/RELATION_SEMANTICS.md s C.9, ruled 2026-09-15. Ex4's `arises_from` was interrogated and
# REJECTED as the kind: its ordinary relational reading carries causal, temporal or lifecycle-origin
# implications the household's assertion does not establish and the cases contradict (C7: the
# pre-service deposit mints O before X is incurred) or prohibit (RP2). `obligation_in_respect_of(O, X)`
# means EXACTLY: *the asserting party holds that the subject obligation is in respect of the object
# expense* - and nothing above that floor. It does NOT mean caused by, preceded by, generated by,
# billed for, allocated to, legally owed because of, the payment obligation for, the coverage
# responsibility for, equal in amount to, or exclusively in respect of; each of those is a further
# claim by a party, a consumer's reading, or another pass's relation. Both participants are
# established - the claim mints neither. Direction is fixed by PARTICIPANT TYPE, not meaning: there
# is no reverse claim to distinguish (unlike passes A and B, where two same-typed participants made
# which-is-which the meaning); a kind with the slots swapped would be a second relation needing its
# own ruling, never this one read backwards; a query in either direction is navigation, not a
# relation. No cardinality - one surgery may have the hospital's, the radiologist's, the lab's and
# the financing obligation in respect of it, one account balance may be in respect of two visits -
# with no share, allocation, sum, merge, single creditor or correspondence candidate following.
# Established only by a party's assertion with both endpoints already established (the household,
# the provider) - the assertion establishes neither endpoint nor any property of either; a reading,
# a matcher, a bill concerning both identities, a shared minting utterance or an insurer's
# patient-responsibility figure yields at most a candidate. NOT a reconciliation operator: O's
# amount is not X's amount, not X's patient responsibility, not a residual of X's figures. NOT a
# projection: O acquires no nature, necessity, date, provider or amount from X - a consumer may
# traverse the relation to enumerate every asserted endpoint with its asserter and any contest, but
# no accessor may select a privileged "underlying expense" (that is a resolver, refused). Derives
# nothing else: no temporal order, no beginning or ending of O, no occurrence of X, no discharge,
# payment or coverage, no creditor/provider mirroring, no transitivity across obligation_replaces.
# Bill / charge / responsibility / balance / financed are content or claims about O, never kinds.
# Knowing: relational_knowing True with no designated relation -> undetermined; neither the obligor
# of O, the incurrer of X nor E of O is forced by the relation. Not a source word.
OBLIGATION_IN_RESPECT_OF = 'obligation_in_respect_of'

# ── Item 6, pass D: the payment-to-expense relation ──────────────────────────
# gw 2.0/RELATION_SEMANTICS.md s D.9, ruled 2026-09-15 - from D's own pressure (Ex8's card purchase,
# where no obligation exists to chain through; the 1.x ExpenseFundingAllocation row, whose `attached`
# is this relation and whose amount / mode / station booleans are NOT inherited onto the edge).
# "Payment = money movement for expense" is three collapses, each refused: the movement is the bank's
# statement and not the payment (Pm11/Pm12); funding is a direction of money that reimbursement (D9),
# an insurer's payment (D18 - no household party on p at all) and a third party's payment (D19 -
# payer != incurrer) independently contradict; one-to-one is contradicted by a copay beside a bill
# payment (D3) and one swipe for two prescriptions (D4). `payment_in_respect_of(p, X)` means EXACTLY:
# *the asserting party holds that the subject payment was in respect of the object expense* - and
# nothing above that floor. "In respect of" identifies the asserted subject/object relationship; it
# does not describe the economic purpose, direction, funding mechanism or legal effect of the
# payment. The relation carries NO payer/payee semantics - payer and payee remain separately asserted
# claims about the payment a consumer may join, never the relation's meaning. Both participants are
# established - the claim mints neither. Direction is fixed by participant type, not meaning: no
# reverse claim, no inverse kind (expense_paid_by / expense_funded_by would be second relations);
# navigation either way is a query. No cardinality, and cardinality is not allocation: several
# payments in respect of one expense imply no duplicate, replacement, counteraction or "partial"; one
# payment in respect of several expenses implies no allocation, split, percentage, order of
# satisfaction or remainder; several assertions are never an implicit allocation. Established only by
# a party's assertion with both endpoints already established (the household, the payee, any party -
# no household party is required anywhere on p); a bank line, a merchant string, a category, a
# matcher, a receipt concerning both identities or an insurer's paid figure yields at most a
# candidate. Derives NOTHING: no amount, sum or reconciliation; no paid / reimbursed / covered status
# on X (absence of a relation is absence of evidence, never "unpaid"); no discharge on any
# obligation; no direction of money; no temporal order (D21, PERMANENT: a relation's direction and
# participant types do not establish temporal precedence between its endpoints); no payer/incurrer
# or payee/provider mirroring; no composition with toward, obligation_in_respect_of or
# payment_counteracts (either direction); no manufactured expense for an untied payment or the rest
# of a swipe; no determination (user_paid_cash etc. are item 7). Paid-for / funded / covered /
# reimbursed / copay / attached / allocated are content or claims about p, never kinds. For G: C and
# D exhibit the same relational semantic floor under substitution of subject participant type -
# evidence for inspection, not a family ruling. Knowing: relational_knowing True with no designated
# relation -> undetermined (payer? payee? incurrer? none forced). Not a source word.
PAYMENT_IN_RESPECT_OF = 'payment_in_respect_of'

# ── Item 6, pass D': the payment-to-obligation relation ─────────────────────
# gw 2.0/RELATION_SEMANTICS.md s D'.9, ruled 2026-09-15 as a semantic pressure test on shared-X
# convergence. `payment_in_respect_of_obligation(p, O)` means EXACTLY: *the asserting party holds that
# the subject payment was in respect of the object obligation* - and nothing above that floor.
#
#     NON-DERIVABILITY (the D' invariant, stated where the kind is defined):
#         payment_in_respect_of_obligation(p, O) is assertable from evidence identifying both p and O.
#         It is NOT derivable merely from
#             payment_in_respect_of(p, X)  +  obligation_in_respect_of(O, X)
#         nor from any composition whose only shared operand is X, nor from E's acknowledgment of p,
#         nor from a payment's creation order, amount, payee or clearing.
#     Shared reference to X cannot establish payment -> obligation: with several obligations in respect
#     of X a derivation cannot name its result (D'3); with the insurer's payment (Aetna -> Mercy $568
#     beside Rob's $412 obligation, both in respect of the same visit) its result is FALSE (D'5,
#     PERMANENT); with a reimbursement or a desk copay it is unwanted (D'6); and the mortgage has no
#     expense to converge on at all (D'1). Convergence is neither a party nor a reading: it has no
#     evidentiary authority. Rob's four things are four: common referent (two claims of kinds C and D)
#     · economic relationship (E's acknowledgment; item 7's remaining) · identity relationship (THIS
#     kind, asserted) · derived relationship (refused). No selector, resolver or accessor may choose an
#     obligation for a payment; the relation is boring - p -> O - and the evidence explains why it exists.
#
# `toward` - the payment fixtures' stand-in since Pm1 - is REJECTED as the kind: it asserts a direction
# of money (a creditor's escrow refund is in respect of the mortgage with the money the other way, D'11)
# and an intent-to-reduce that is content (S3 / S6 separate intent from effect). The household's
# assertion of this relation IS the "attached" station of the ruled acknowledgment sequence (H2); E's
# acknowledgment is a different claim by a different party - and when read as *E applied p to O* it
# carries O as a hidden operand (K8), a participant / content question recorded for the catalogue (D4)
# and not fixed here. Both participants established - the claim mints neither. Direction fixed by
# participant type, no inverse kind (obligation_paid_by would be a second relation), navigation either
# way a query. No cardinality, and cardinality is not allocation (one cheque for two plans, twelve
# autopays for one mortgage: no split, no sum, no remaining). Established only by a party's assertion
# with both endpoints already established (the household, the creditor, a servicer); a statement line
# "applied to loan 4471", a matcher, E's credit yields at most a candidate. Derives NOTHING: no
# discharge, application or credit (E's, by definition); no remaining (H2 / item 7); no direction of
# money; no temporal order (D'4 with D21 / C7, PERMANENT); no composition with obligation_replaces,
# payment_counteracts, obligation_in_respect_of or payment_in_respect_of; no status on p or O.
# Toward / against / on / applied / attached / paid down are content or another party's claim, never
# kinds. JURISDICTION: whether this kind and payment_in_respect_of are one kind with typed object slots
# is G's question - a distinct kind is the representation until G rules, and G may not retroactively
# supply the semantics D' refused to derive. Knowing: relational_knowing True with no designated
# relation -> undetermined. Not a source word.
PAYMENT_IN_RESPECT_OF_OBLIGATION = 'payment_in_respect_of_obligation'

# ── Ab7: proposition-level about-ness ────────────────────────────────────────
# gw 2.0/PROPOSITION_ABOUTNESS.md, ruled s7. `proposition_concerns(P, X)` means EXACTLY: *this
# proposition concerns this identity* - subject a PROPOSITION (the first and only ruled kind with a
# proposition subject), second participant an already-minted identity. It presupposes X. It is
# asserted by a party's utterance; a match observed by a reading (a heading, an account number, a
# position) produces a CANDIDATE for this claim - it is not itself the claim - and is evidence for
# nothing else; those candidates are what PARTICIPANT_CANDIDATES has always referred to.
#
#     About-ness is information about a proposition, not information inserted into the proposition.
#
# It never changes the subject, participants, authority, evidence or history of P; P's own identity
# participant stays unestablished; it attaches only where P has no established participant of X's
# type (_aboutness_violations). Independent of artefact_concerns: needed where an artefact concerns
# several identities or none, never required; consistency between the levels is a consumer's to
# report, never a guard's to refuse or a resolver's to settle. A re-reading's propositions carry no
# about-ness of their own (proposition_corresponds is pressed by that case and not ruled).
PROPOSITION_CONCERNS = 'proposition_concerns'

# The named designated knowing relations (RELATIONAL_KNOWING.md s9) - the names a ruled kind may
# carry as `knowing_relation`; their resolvers live beside derived_strength.
KNOWING_ORIGIN_OF_SUBJECT_UTTERANCE = 'origin_of_subject_utterance'
KNOWING_MINTER_OF_OBJECT_IDENTITY = 'origin_of_the_utterance_that_minted_the_object_identity'

# ── proposition_corresponds ───────────────────────────────────────────────────
# gw 2.0/PROPOSITION_CORRESPONDENCE.md, ruled s7. Two separately minted propositions are two
# OBSERVATIONS OR RECORDINGS OF ONE CLAIM - one statement an artefact makes, read more than once;
# one assertion a party made, entered more than once. Slice 4's shape, a fifth type: established
# only by a party's utterance; a position or content match observed by a reading MAY produce a
# candidate (the observation is not itself the claim; candidate generation is outside the
# substrate); the referent is derived; never merged, never re-pointed. Contents and kinds MAY
# differ - that difference is the parse dispute, made computable and never resolved. Not
# agreement (a comparison), not shared subject (structural), not the entry path's reuse of one
# row (identity), not replacement (retraction), and NOT about-ness carrying: the substrate copies
# nothing across corresponding propositions; what a consumer derives through the correspondence
# is the consumer's rule. Relational, never transmissive.
PROPOSITION_CORRESPONDS = 'proposition_corresponds'

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
    PAYMENT_CORRESPONDS:  {'subject': ('subject_payment_id',),    'object': ('object_payment_id',),
                           'symmetric': True,  'reading_establishes': False, 'relational_knowing': False},
    EXPENSE_CORRESPONDS:  {'subject': ('subject_expense_id',),    'object': ('object_expense_id',),
                           'symmetric': True,  'reading_establishes': False, 'relational_knowing': False},
    PLAN_CORRESPONDS:     {'subject': ('subject_plan_id',),       'object': ('object_plan_id',),
                           'symmetric': True,  'reading_establishes': False, 'relational_knowing': False},
    # item 6 pass A - the one ruled relation between two payments; NOT a correspondence (two events,
    # never one referent); relational_knowing True and NO knowing_relation: undetermined by design.
    PAYMENT_COUNTERACTS:  {'subject': ('subject_payment_id',),    'object': ('object_payment_id',),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True},
    # obligation_replaces (item 6 pass B): the replacing obligation is the subject, the replaced the
    # object; never symmetric; relational_knowing True and NO knowing_relation: undetermined by design.
    OBLIGATION_REPLACES:  {'subject': ('subject_obligation_id',), 'object': ('object_obligation_id',),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True},
    # obligation_in_respect_of (item 6 pass C): obligation subject, expense object - direction fixed by
    # type, carrying no meaning; relational_knowing True and NO knowing_relation: undetermined by design.
    OBLIGATION_IN_RESPECT_OF: {'subject': ('subject_obligation_id',), 'object': ('object_expense_id',),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True},
    # payment_in_respect_of (item 6 pass D): payment subject, expense object - direction fixed by type,
    # carrying no meaning; relational_knowing True and NO knowing_relation: undetermined by design.
    PAYMENT_IN_RESPECT_OF: {'subject': ('subject_payment_id',),    'object': ('object_expense_id',),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True},
    # payment_in_respect_of_obligation (item 6 pass D'): payment subject, obligation object; NOT derivable
    # from payment_in_respect_of + obligation_in_respect_of sharing an X (see the constant); relational_knowing
    # True and NO knowing_relation: undetermined by design.
    PAYMENT_IN_RESPECT_OF_OBLIGATION: {'subject': ('subject_payment_id',), 'object': ('object_obligation_id',),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True},
    # subject: a proposition - the only ruled use of that slot. object: the identities ruled so far.
    PROPOSITION_CONCERNS: {'subject': ('subject_proposition_id',),
                           'object': ('object_obligation_id', 'object_payment_id', 'object_expense_id', 'object_plan_id'),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True,
                           'knowing_relation': KNOWING_MINTER_OF_OBJECT_IDENTITY},
    # proposition_corresponds: relational_knowing True and NO knowing_relation - a correctly fenced
    # unknown (held is custody, not knowledge; assertion origin is not knowing). Stays undetermined.
    # the only ruled kind with a proposition OBJECT.
    PROPOSITION_CORRESPONDS: {'subject': ('subject_proposition_id',), 'object': ('object_proposition_id',),
                           'symmetric': True,  'reading_establishes': False, 'relational_knowing': True},
    # object: the identities ruled so far. Grows additively as each further identity is minted
    # (obligation; payment - PAYMENT_IDENTITY.md s4: an artefact that is the payment's own record;
    # expense - EXPENSE_IDENTITY.md s4: a bill, an EOB, a receipt; plan - PLAN_IDENTITY.md s3: the
    # card, the SBC, an EOB naming the group).
    ARTEFACT_CONCERNS:    {'subject': ('subject_artefact_id',),
                           'object': ('object_obligation_id', 'object_payment_id', 'object_expense_id', 'object_plan_id'),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True,
                           'knowing_relation': KNOWING_MINTER_OF_OBJECT_IDENTITY},
    # object: () - a REQUIRED absence, enforced (object_state must be `none`).
    UTTERANCE_RETRACTION: {'subject': ('subject_utterance_id',), 'object': (),
                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True,
                           'knowing_relation': KNOWING_ORIGIN_OF_SUBJECT_UTTERANCE},
}

# ── Item 5: the role period ───────────────────────────────────────────────────
# gw 2.0/ROLE_PERIOD.md, ruled s7 (RP2, 2026-09-14). A role - a dated relation between a party
# and an identity - has NO intrinsic period. Its temporal history is propositions in their own
# right, of three sorts: that it HOLDS AT d (the role kind itself, `as_of` = d - D7's shape), that
# it BEGAN AT d, that it ENDED AT d. A beginning and an ending are kinds of their own, bound to the
# role kind they temporally qualify by two registry entries:
#
#     'boundary': 'began' | 'ended'     which boundary this kind asserts
#     'of':       <role kind>           the ruled role kind it bounds
#
# The sort is part of what is claimed, so it lives in the kind - never in coordinates on a claim
# (no effective_from / effective_to: that makes a derived interval look like intrinsic structure
# and fuses two provenances - the household's January beginning and the insurer's June ending,
# learned in August - into one row) and never in content. `as_of` is the date the boundary is
# about; the utterance's time and the row's `created_at` are when it was learned, so a late-
# discovered transition is a new claim recorded now about a boundary then, the prior claims
# untouched (T4/T8; OBLIGATION_LIFECYCLE rule 2: effective-at never collapses into learned-at).
#
# The guard below establishes STRUCTURAL validity only - *this boundary kind is permitted to
# bound this role kind*: the bound kind is ruled, is itself a role (not a boundary), takes the
# same participants; a boundary kind is not symmetric, a reading never establishes it, and a
# boundary claim requires `as_of`. The registry may not become "anything can be a beginning of
# anything." Nothing here says a role actually began or ended, implies the opposite boundary,
# resolves a disputed boundary (two claims, derived), infers a period, establishes continuous
# effect, decides overlap (two relations holding at once is a state the record shows), answers
# "in effect on d" (a derivation, item 7), or creates a role - a beginning is not a holds-at
# claim. A withdrawn beginning is an `utterance_retraction`, never an ending.
#
# No role kind is ruled by this slice: the catalogue (serves, entitled party of, obligor on,
# provider of, insurer of, covered under) and each role's semantics - who may assert it, what it
# establishes, who is knowing for it - are separate rulings; an endpoint's existence (a party, an
# obligation, a plan) gives a role no meaning. The shipped registry therefore carries no boundary
# entries; the fixture exercises the discipline on stand-in kinds it registers and removes.
BOUNDARY_BEGAN = 'began'
BOUNDARY_ENDED = 'ended'
BOUNDARIES = (BOUNDARY_BEGAN, BOUNDARY_ENDED)


def registry_violations(registry=None, kinds=None):
    """Structural validity of the registry's boundary metadata, as a list of what is wrong
    (empty = fine). `kinds` narrows the check to those entries. Structure only - never whether
    any role began or ended."""
    reg = RULED_KINDS if registry is None else registry
    out = []
    for kind in (reg if kinds is None else kinds):
        rule = reg.get(kind)
        if rule is None:
            continue
        boundary, of = rule.get('boundary'), rule.get('of')
        if boundary is None and of is None:
            continue
        if boundary not in BOUNDARIES:
            out.append(f'{kind}: boundary must be one of {BOUNDARIES}, is {boundary!r}')
        if of is None:
            out.append(f'{kind}: a boundary kind must name the role kind it bounds')
            continue
        role = reg.get(of)
        if role is None:
            out.append(f'{kind}: bounds {of!r}, which is not a ruled kind')
        elif role.get('boundary') is not None or role.get('of') is not None:
            out.append(f'{kind}: bounds {of!r}, which is itself a boundary kind')
        elif (tuple(role['subject']), tuple(role['object'])) != (tuple(rule['subject']), tuple(rule['object'])):
            out.append(f'{kind}: must take exactly the participants of {of!r}')
        if rule.get('symmetric'):
            out.append(f'{kind}: a boundary kind is not symmetric')
        if rule.get('reading_establishes'):
            out.append(f'{kind}: a reading never establishes a boundary')
    return out


def boundary_kinds_of(role_kind, registry=None):
    """The boundary kinds bound to a role kind, by boundary: {'began': kind, 'ended': kind} -
    registry introspection, so a consumer finds boundaries structurally rather than by naming
    convention. Not a temporal derivation: it reads the registry, never the rows."""
    reg = RULED_KINDS if registry is None else registry
    return {rule['boundary']: kind for kind, rule in reg.items()
            if rule.get('of') == role_kind and rule.get('boundary') in BOUNDARIES}


def _boundary_violations(prop):
    rule = RULED_KINDS.get(getattr(prop, 'kind', None))
    if rule is None or (rule.get('boundary') is None and rule.get('of') is None):
        return []
    out = registry_violations(kinds=(prop.kind,))
    if not getattr(prop, 'as_of', None):
        out.append(f'{prop.kind}: a boundary claim requires as_of - the date the boundary is about')
    return out


_registry_problems = registry_violations()
if _registry_problems:
    raise RuntimeError('RULED_KINDS boundary metadata is structurally invalid: ' + '; '.join(_registry_problems))
del _registry_problems

REFERENT_SEPARATE = 'separate'                          # no established claim touches it
REFERENT_CANDIDATES = 'separate_with_candidates'        # reading-sourced claims only
REFERENT_CORRESPONDING = 'corresponding'                # at least one established claim; one component
REFERENT_CONTESTED = 'contested'                        # an establishing utterance is itself the subject of a claim

_CORRESPONDENCE_OF = {'Artefact':   (ARTEFACT_CORRESPONDS,   'subject_artefact_id',   'object_artefact_id'),
                      'Party':      (PARTY_CORRESPONDS,      'subject_party_id',      'object_party_id'),
                      'Obligation': (OBLIGATION_CORRESPONDS, 'subject_obligation_id', 'object_obligation_id'),
                      'Payment':    (PAYMENT_CORRESPONDS,    'subject_payment_id',    'object_payment_id'),
                      'Expense':    (EXPENSE_CORRESPONDS,    'subject_expense_id',    'object_expense_id'),
                      'Plan':       (PLAN_CORRESPONDS,       'subject_plan_id',       'object_plan_id'),
                      'Proposition': (PROPOSITION_CORRESPONDS, 'subject_proposition_id', 'object_proposition_id')}


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


# ── Item 7, pass 7A: the parse dispute - a CONSUMER derivation ────────────────
# gw 2.0/CONSUMER_DERIVATIONS.md s 7A.6, ruled 2026-09-16. The first consumer: a read-only derivation
# over the observations of ONE artefact that reports disagreement and never resolves it. It answers
# one question - do the readings of this artefact disagree, and about what? - and returns its answer
# with the claims it rests on and what it could not settle.
#
#   established correspondence  ->  established referent / component   (referent(); never re-derived)
#   candidate correspondence    ->  candidate grouping only
#   no correspondence           ->  no claim that the propositions are one referent
#
# It CHOOSES nothing - not the latest reading, the newest parser, the majority or the household's
# preference (the hazard audit's R4); it STORES nothing and is recomputed on every read; it COUNTS
# readings of one referent as ONE source, never as corroboration (Pc2 / Pc9 - three readings, two
# contents, one source); it compares readings of one artefact only - two artefacts are a source
# question for later passes (Pd6); a person's transcription is a reading, not testimony (Pd9); a
# retracted correspondence reads contested and the derivation stops (Pd10); an omission is not a
# dispute and absence is not zero (Pd5); a single reading is "one observation", never "agreed" (Pd13).
# It is STRUCTURAL - same referent + different content or kind - so its null model is a correctness
# oracle (identical re-parse -> 0, one changed figure -> 1), never a similarity threshold.
# It must not call anything whose purpose is to establish correspondence: candidates originate from
# the fenced matcher / reading machinery; this reports them. It is the reading-level answer the hazard
# audit (H4) required to exist distinctly from source-level; `resolution()` may not read past it.
# The narrator may voice the dispute's existence and its readings, never a chosen value.
PARSE_CONTENT_DISPUTE = 'content_dispute'
PARSE_KIND_DISPUTE = 'kind_dispute'
PARSE_AGREED_ONE_SOURCE = 'agreed_one_source'
PARSE_OMISSION = 'omission'
PARSE_SINGLE_READING = 'single_reading'
GROUP_ESTABLISHED = 'established'
GROUP_CANDIDATE = 'candidate'
GROUP_CONTESTED = 'contested'


def parse_disputes(session, artefact):
    """The parse-dispute derivation for one artefact: a plain dict, computed on read, storing nothing.

        {'artefact_id', 'observations': n readings, 'sources': 1,
         'readings': [(reading_id, reader, read_at)],
         'groups':   [{'state': established|candidate|contested,
                       'propositions': [(prop_id, kind, content, reading_id)],
                       'readings': [reading_id...], 'kinds': [...], 'contents': [...],
                       'classification': [content_dispute | kind_dispute | agreed_one_source]}],
         'omissions': [{'proposition': (prop_id, kind, content, reading_id),
                        'present_in': [reading_id], 'absent_in': [reading_id...]}],
         'classification': [single_reading] when the artefact has one observation}

    A group is the established component `referent()` returns (state established / contested) or,
    failing that, the propositions a reading-sourced `proposition_corresponds` candidate joins
    (state candidate) - nothing else groups propositions, and nothing here establishes anything.
    Members read from another artefact's readings are excluded from the group (a source question,
    not this one) and reported under 'beyond_artefact' so the exclusion is visible.
    """
    readings = (session.query(Reading).filter(Reading.artefact_id == artefact.id)
                .order_by(Reading.id).all())
    reading_ids = [r.id for r in readings]
    out = {'artefact_id': artefact.id, 'observations': len(readings), 'sources': 1,
           'readings': [(r.id, r.reader_process if r.reader_process else ('party', r.reader_party_id), r.read_at)
                        for r in readings],
           'groups': [], 'omissions': [], 'classification': []}
    if not readings:
        return out
    if len(readings) == 1:
        out['classification'].append(PARSE_SINGLE_READING)
    # every proposition observed by a reading of THIS artefact, with the reading that observed it
    observed = {}
    rows = (session.query(Proposition, EvidentiaryRelationship)
            .join(EvidentiaryRelationship, EvidentiaryRelationship.proposition_id == Proposition.id)
            .filter(EvidentiaryRelationship.reading_id.in_(reading_ids))
            .filter(Proposition.kind != PROPOSITION_CORRESPONDS).all())
    for prop, rel in rows:
        observed.setdefault(prop.id, (prop, set()))[1].add(rel.reading_id)
    if not observed:
        return out
    # reading-sourced correspondence candidates between observed propositions (the matcher's; reported, never made)
    cand_edges = {}
    for prop, rel in (session.query(Proposition, EvidentiaryRelationship)
                      .join(EvidentiaryRelationship, EvidentiaryRelationship.proposition_id == Proposition.id)
                      .filter(Proposition.kind == PROPOSITION_CORRESPONDS,
                              EvidentiaryRelationship.utterance_id.is_(None)).all()):
        a, b = prop.subject_proposition_id, prop.object_proposition_id
        cand_edges.setdefault(a, set()).add(b)
        cand_edges.setdefault(b, set()).add(a)
    seen = set()
    for pid in sorted(observed):
        if pid in seen:
            continue
        prop = observed[pid][0]
        state, component, _cands = referent(session, prop)
        if state in (REFERENT_CORRESPONDING, REFERENT_CONTESTED):
            members = set(component)
            gstate = GROUP_CONTESTED if state == REFERENT_CONTESTED else GROUP_ESTABLISHED
        else:
            # candidate grouping: the connected component under reading-sourced candidates only
            members, frontier = {pid}, [pid]
            while frontier:
                nxt = frontier.pop()
                for other in cand_edges.get(nxt, ()):
                    if other not in members:
                        members.add(other)
                        frontier.append(other)
            gstate = GROUP_CANDIDATE
        here = sorted(m for m in members if m in observed)
        beyond = sorted(m for m in members if m not in observed)
        if len(here) < 2:
            continue                                        # a lone proposition is an omission candidate, below
        seen |= set(here)
        props = []
        for m in here:
            pr, rids = observed[m]
            for rid in sorted(rids):
                props.append((pr.id, pr.kind, pr.content, rid))
        kinds = sorted({k for _, k, _, _ in props})
        contents = sorted({c if c is not None else '' for _, _, c, _ in props})
        rids = sorted({rid for _, _, _, rid in props})
        classification = []
        if len(kinds) > 1:
            classification.append(PARSE_KIND_DISPUTE)
        if len(contents) > 1:
            classification.append(PARSE_CONTENT_DISPUTE)
        if not classification:
            classification.append(PARSE_AGREED_ONE_SOURCE)
        group = {'state': gstate, 'propositions': props, 'readings': rids, 'kinds': kinds,
                 'contents': contents, 'classification': classification}
        if beyond:
            group['beyond_artefact'] = beyond
        out['groups'].append(group)
    if len(readings) >= 2:
        for pid in sorted(observed):
            if pid in seen:
                continue
            pr, rids = observed[pid]
            present = sorted(rids)
            absent = sorted(set(reading_ids) - rids)
            if absent:
                out['omissions'].append({'proposition': (pr.id, pr.kind, pr.content, present[0]),
                                         'present_in': present, 'absent_in': absent})
    return out


# ── Item 7, pass 7B: independence - a CONSUMER derivation ─────────────────────
# gw 2.0/CONSUMER_DERIVATIONS.md s 7B.7, ruled 2026-09-16. Independence is a three-valued derivation
# between ORIGINS, for ONE proposition, and nothing weaker or stronger (contract C4):
#
#     independent      two distinct established origins, each knowing for the proposition, each chain established
#     not independent  the grounds resolve to one origin - through one artefact, two artefacts of one origin, two
#                      channels of one source, a duplicated utterance, or a correspondence a party established
#     undetermined     a chain or an origin is a candidate, contested or unasserted - NEVER defaulted either way
#
# Origin is read from the assertion's PROVENANCE, never from who is speaking (C1 / C2): an utterance's
# origin party is an origin; a reading conveys the ARTEFACT'S origin (artefact_origin(), established
# only by a party's utterance) and never the reader's; a process is not an origin and contributes
# nothing (O9); a candidate is not a claim by anyone. Artefacts and parties established as
# corresponding are ONE (referent()); a candidate correspondence between two origins leaves their
# pair undetermined. Knowing is read per evidentiary relationship (derived_strength); an origin not
# knowing for the proposition is listed and takes part in no pair. Difference establishes nothing -
# not a different reading, parser, document, channel, party, timestamp or row. The verdict is a set
# of origins and their pairwise states: NEVER a count, rank, score or strength (7E's question) -
# three independent origins are three independent pairs and no number. Independence is never a
# property of a document, source or party: it is evaluated for the proposition at hand.
#
#     THE 7B WIRING GUARD (Rob, s 7B.7): the consumer may inspect the established provenance /
#     relationship chain to determine the result, but may not establish, upgrade, resolve or mutate
#     any provenance, correspondence, knowing relationship or independence relationship while doing
#     so. Independence remains a consumer ANSWER, not an ontology relation. Nothing is stored.
#
# The 1.x count `distinct = {e.source for e in supporting}` (core/classification.py, the matrix's row
# 7) is a count of CHANNEL TYPES, not independence; it is named as such and not repaired by counting
# differently. Reader independence for P-subject (RA5) stays fenced.
INDEPENDENT = 'independent'
NOT_INDEPENDENT = 'not_independent'
INDEPENDENCE_UNDETERMINED = 'undetermined'
CHAIN_ESTABLISHED = 'established'
CHAIN_CANDIDATE = 'candidate'
CHAIN_CONTESTED = 'contested'
CHAIN_UNESTABLISHED = 'unestablished'


def independence(session, proposition, knowing):
    """The independence derivation for one proposition: a plain dict, computed on read, storing nothing.

        {'proposition_id', 'component': [prop ids taken as one claim - the established referent],
         'origins': [{'origin': party_id | None, 'state': established|candidate|contested|unestablished,
                      'knowing': knowing|not_knowing|undetermined,
                      'grounds': [(relationship_id, 'utterance'|'reading', source_id, artefact_id|None)],
                      'multiplicity': n grounds  -> n > 1 means NOT INDEPENDENT among those grounds}],
         'pairs': [(origin_a, origin_b, independent|undetermined)]   between distinct KNOWING origins only,
         'readers': [reader_process...]   processes seen - never origins,
         'note': 'one origin - no second term' | 'no knowing origin' | None}

    `knowing` is the caller's kind -> foundations map, as for derived_strength. Origins are collapsed
    by established party correspondence and artefacts by established artefact correspondence
    (referent()); a candidate correspondence between two origins leaves their pair undetermined.
    An origin whose chain is not established, or which is not knowing, takes part in no pair.

    THREE FENCES ON THE SHAPE (s 7B.8):
      multiplicity   is the structural cardinality of grounds attached to ONE resolved origin. It has
                     no evidentiary, corroborative, comparative, confidence, ranking, threshold or
                     independence meaning; no consumer may read it as a measure of support.
      origin: None   is NOT an origin identity. It marks an unresolved origin-bearing ground; each
                     such ground is its own entry, never collapsed with another unresolved ground,
                     never eligible for pairing or correspondence collapse.
      readers        is explanatory trace only - the processes that observed - not an alternative
                     evidence population; readers never participate in independence (RA5 stays fenced).
    """
    props = [proposition]
    state, component, _ = referent(session, proposition)
    if state in (REFERENT_CORRESPONDING, REFERENT_CONTESTED):
        props = [session.get(Proposition, pid) for pid in component]
    out = {'proposition_id': proposition.id, 'component': sorted(p.id for p in props),
           'origins': [], 'pairs': [], 'readers': [], 'note': None}
    rels = (session.query(EvidentiaryRelationship)
            .filter(EvidentiaryRelationship.proposition_id.in_([p.id for p in props]))
            .order_by(EvidentiaryRelationship.id).all())
    if not rels:
        out['note'] = 'no knowing origin'
        return out

    party_key_cache = {}

    def party_key(pid):
        # collapse parties established as one referent; report candidates separately
        if pid not in party_key_cache:
            pstate, comp, cands = referent(session, session.get(Party, pid))
            party_key_cache[pid] = (min(comp), pstate, set(cands))
        return party_key_cache[pid]

    retracted = {u for (u,) in session.query(Proposition.subject_utterance_id)
                 .filter(Proposition.kind == UTTERANCE_RETRACTION, Proposition.subject_utterance_id.isnot(None)).all()}
    entries = {}
    for rel in rels:
        strength = derived_strength(session, rel, knowing)
        if rel.utterance_id is not None:
            utt = rel.utterance
            key, pstate, pcands = party_key(utt.origin_party_id)
            chain = CHAIN_CONTESTED if (utt.id in retracted or pstate == REFERENT_CONTESTED) else CHAIN_ESTABLISHED
            ground = (rel.id, 'utterance', utt.id, None)
            origin = key
        else:
            rd = rel.reading
            art = rd.artefact
            if rd.reader_process:
                out['readers'].append(rd.reader_process)
            astate, comp_a, _ = referent(session, art)
            # the artefact's origin, through its established component: one artefact, one origin
            ostates = {}
            a_ids = comp_a if astate in (REFERENT_CORRESPONDING, REFERENT_CONTESTED) else [art.id]
            for aid in a_ids:
                o_state, parties = artefact_origin(session, session.get(Artefact, aid))
                ostates.setdefault(o_state, set()).update(parties)
            ground = (rel.id, 'reading', rd.id, art.id)
            if ORIGIN_ESTABLISHED in ostates and len(ostates) == 1 and len(ostates[ORIGIN_ESTABLISHED]) == 1:
                pid = next(iter(ostates[ORIGIN_ESTABLISHED]))
                key, pstate, pcands = party_key(pid)
                # the chain includes the origin claim's own evidence: a retracted origin utterance contests it
                origin_utts = {u for (u,) in (session.query(EvidentiaryRelationship.utterance_id)
                                              .join(Proposition, Proposition.id == EvidentiaryRelationship.proposition_id)
                                              .filter(Proposition.kind == ARTEFACT_ORIGIN,
                                                      Proposition.subject_artefact_id.in_(sorted(a_ids)),
                                                      Proposition.object_party_id == pid,
                                                      EvidentiaryRelationship.utterance_id.isnot(None)).all())}
                contested_origin = bool(origin_utts) and origin_utts <= retracted
                chain = CHAIN_CONTESTED if (astate == REFERENT_CONTESTED or pstate == REFERENT_CONTESTED or contested_origin) else CHAIN_ESTABLISHED
                origin = key
            elif ORIGIN_MULTIPLE in ostates or len(ostates.get(ORIGIN_ESTABLISHED, ())) > 1:
                origin, chain, pcands = None, CHAIN_CONTESTED, set()
            elif ORIGIN_CANDIDATES in ostates:
                origin, chain, pcands = None, CHAIN_CANDIDATE, set()
            else:
                origin, chain, pcands = None, CHAIN_UNESTABLISHED, set()
        ekey = origin if origin is not None else ('none', rel.id)
        e = entries.setdefault(ekey, {'origin': origin, 'state': chain, 'knowing': strength, 'grounds': [], 'candidates': set()})
        e['grounds'].append(ground)
        e['candidates'] |= pcands
        # a contested chain on any ground makes the origin's state contested; knowing is the weakest seen
        if chain == CHAIN_CONTESTED:
            e['state'] = CHAIN_CONTESTED
        e['knowing'] = _weakest(e['knowing'], strength)
    origins = []
    for ekey, e in entries.items():
        origins.append({'origin': e['origin'], 'state': e['state'], 'knowing': e['knowing'],
                        'grounds': e['grounds'], 'multiplicity': len(e['grounds']),
                        'correspondence_candidates': sorted(e['candidates'])})
    origins.sort(key=lambda o: (o['origin'] is None, o['origin'] or 0, o['grounds'][0][0]))
    out['origins'] = origins
    knowing_origins = [o for o in origins if o['origin'] is not None and o['knowing'] == STRENGTH_KNOWING]
    if len(knowing_origins) == 0:
        out['note'] = 'no knowing origin'
    elif len(knowing_origins) == 1:
        out['note'] = 'one origin - no second term'
    for i, a in enumerate(knowing_origins):
        for b in knowing_origins[i + 1:]:
            if a['state'] != CHAIN_ESTABLISHED or b['state'] != CHAIN_ESTABLISHED:
                verdict = INDEPENDENCE_UNDETERMINED
            elif a['origin'] in b['correspondence_candidates'] or b['origin'] in a['correspondence_candidates']:
                verdict = INDEPENDENCE_UNDETERMINED
            else:
                verdict = INDEPENDENT
            out['pairs'].append((a['origin'], b['origin'], verdict))
    return out


# ── Item 7, pass 7C: about-ness - a CONSUMER derivation ───────────────────────
# gw 2.0/CONSUMER_DERIVATIONS.md s 7C.7, ruled 2026-09-16. A proposition is about an identity by exactly
# four things and nothing else:
#     structural   its own ESTABLISHED participant slot of one of the identity types about-ness ranges over
#                  (obligation, payment, expense, plan - the concerns kinds' object types; a party is not one)
#     asserted     an established proposition_concerns(P, X) - a party's utterance behind it
#     derived      (artefact)        P was read from A, and A's ESTABLISHED concern set for X's type contains
#                                    exactly one identity - the one concern supplies the derivation; the
#                                    absence of a second is evidence of nothing; candidate / contested /
#                                    unestablished concerns neither satisfy the condition nor get resolved
#                  (correspondence)  P is ESTABLISHED as corresponding to a proposition that is about X by
#                                    structure or assertion - two recordings of one claim are one claim;
#                                    transitively through established links only (referent()'s component;
#                                    a cycle is one component); a candidate link stops the chain there
# A candidate is never about-ness: a reading-sourced concerns claim, a candidate correspondence, a candidate
# artefact claim, or an artefact whose established set for the type has several identities yields
# CANDIDATES - reported beside any established result, never suppressed by it and never able to unsettle
# it (candidate evidence is not a resolver). A contested component or a retracted assertion yields
# UNDETERMINED and stops the consumer. Several established paths to one identity are ONE derivation with
# its paths listed - paths are not counted and never strengthen, rank or multiply the result. Provenance
# labels are not an ordering of authority: where established sources reach incompatible identities of one
# type the CONFLICT is reported as found, never resolved (7D's). About-ness does not come from content,
# heading, amount, position or order; not from the artefact's origin party's roles; not through a ruled
# relation from the identity reached to another (D'.11); not from two propositions converging on one
# identity; not to a re-reading from the position of the line it re-read; and a reading is a carrier of
# access to its artefact's established semantics, never an about-ness edge - a sibling proposition's
# asserted concerns transmits nothing. A derived about-ness is reported AS derived, is never written back
# as a concerns claim or as the proposition's participant, acquires no knowing, and is voiced by the
# narrator as a derivation, never as an assertion. Nothing is chosen, stored or manufactured.
ABOUT_STRUCTURAL = 'structural'
ABOUT_ASSERTED = 'asserted'
ABOUT_DERIVED = 'derived'
ABOUT_CANDIDATE = 'candidate'
ABOUT_UNDETERMINED = 'undetermined'
ABOUT_PATH_ARTEFACT = 'artefact'
ABOUT_PATH_CORRESPONDENCE = 'correspondence'
# the identity types about-ness ranges over: the concerns kinds' object slots, and the matching subject slots
ABOUT_IDENTITY_TYPES = {
    'obligation': ('subject_obligation_id', 'object_obligation_id'),
    'payment':    ('subject_payment_id',    'object_payment_id'),
    'expense':    ('subject_expense_id',    'object_expense_id'),
    'plan':       ('subject_plan_id',       'object_plan_id'),
}


def _about_direct(session, prop, retracted):
    """The proposition's own about-ness - structural slots and its proposition_concerns claims - as
    (structural, asserted, candidates, undetermined). Reads only; establishes nothing."""
    structural, asserted, candidates, undetermined = [], [], [], []
    for typ, (sub_col, obj_col) in ABOUT_IDENTITY_TYPES.items():
        if prop.subject_state == PARTICIPANT_ESTABLISHED and getattr(prop, sub_col) is not None:
            structural.append((typ, getattr(prop, sub_col)))
        if prop.object_state == PARTICIPANT_ESTABLISHED and getattr(prop, obj_col) is not None:
            structural.append((typ, getattr(prop, obj_col)))
    rows = (session.query(Proposition, EvidentiaryRelationship)
            .join(EvidentiaryRelationship, EvidentiaryRelationship.proposition_id == Proposition.id)
            .filter(Proposition.kind == PROPOSITION_CONCERNS, Proposition.subject_proposition_id == prop.id).all())
    for claim, rel in rows:
        for typ, (_, obj_col) in ABOUT_IDENTITY_TYPES.items():
            ident = getattr(claim, obj_col)
            if ident is None:
                continue
            if rel.utterance_id is not None:
                if rel.utterance_id in retracted:
                    undetermined.append((typ, ident, 'retracted assertion', claim.id))
                else:
                    asserted.append((typ, ident, claim.id, rel.utterance.origin_party_id))
            else:
                candidates.append((typ, ident, 'reading-sourced concerns', rel.reading_id))
    return structural, asserted, candidates, undetermined


def aboutness(session, proposition):
    """The about-ness derivation for one proposition: a plain dict, computed on read, storing nothing.

        {'proposition_id',
         'structural':  [(type, id)],
         'asserted':    [(type, id, claim_id, asserter_party_id)],
         'derived':     [{'type', 'id', 'paths': [{'path': artefact|correspondence, 'links': [...]}]}],
         'candidates':  [(type, id, source, ref_id)],
         'undetermined': [(type, id, reason, ref_id)],
         'conflicts':   [{'type', 'identities': {id: [sources...]}}],     as found, for 7D - never resolved
         'note': 'no about-ness established' | 'candidates only' | None}
    """
    retracted = {u for (u,) in session.query(Proposition.subject_utterance_id)
                 .filter(Proposition.kind == UTTERANCE_RETRACTION, Proposition.subject_utterance_id.isnot(None)).all()}
    structural, asserted, candidates, undetermined = _about_direct(session, proposition, retracted)
    derived = {}                                              # (type, id) -> [paths]

    def add_path(typ, ident, path, links):
        derived.setdefault((typ, ident), []).append({'path': path, 'links': links})

    # ── the artefact level: reading -> artefact -> established concern set for the type ──────────
    artefact_sets = {}                                        # type -> set of established identities (for conflicts)
    rels = (session.query(EvidentiaryRelationship)
            .filter(EvidentiaryRelationship.proposition_id == proposition.id,
                    EvidentiaryRelationship.reading_id.isnot(None)).order_by(EvidentiaryRelationship.id).all())
    seen_artefacts = set()
    for rel in rels:
        rd = rel.reading
        art = rd.artefact
        if art.id in seen_artefacts:
            continue
        seen_artefacts.add(art.id)
        claims = (session.query(Proposition, EvidentiaryRelationship)
                  .join(EvidentiaryRelationship, EvidentiaryRelationship.proposition_id == Proposition.id)
                  .filter(Proposition.kind == ARTEFACT_CONCERNS, Proposition.subject_artefact_id == art.id).all())
        for typ, (_, obj_col) in ABOUT_IDENTITY_TYPES.items():
            established, cand, contested = {}, set(), set()
            for claim, crel in claims:
                ident = getattr(claim, obj_col)
                if ident is None:
                    continue
                if crel.utterance_id is None:
                    cand.add(ident)
                elif crel.utterance_id in retracted:
                    contested.add(ident)
                else:
                    established.setdefault(ident, []).append((claim.id, crel.utterance.origin_party_id))
            if established:
                artefact_sets.setdefault(typ, set()).update(established)
            if len(established) == 1:
                ident, claim_refs = next(iter(established.items()))
                add_path(typ, ident, ABOUT_PATH_ARTEFACT,
                         [('reading', rd.id), ('artefact', art.id)] + [('artefact_concerns', c, a) for c, a in claim_refs])
            elif len(established) > 1:
                for ident in sorted(established):
                    candidates.append((typ, ident, 'artefact concerns several', art.id))
            for ident in sorted(cand - set(established)):
                candidates.append((typ, ident, 'candidate artefact concerns', art.id))
            for ident in sorted(contested - set(established)):
                undetermined.append((typ, ident, 'contested artefact concerns', art.id))

    # ── established correspondence: the component's members' structural and asserted about-ness ──
    state, component, cands = referent(session, proposition)
    if state == REFERENT_CONTESTED:
        for pid in component:
            if pid == proposition.id:
                continue
            q = session.get(Proposition, pid)
            q_struct, q_assert, _, _ = _about_direct(session, q, retracted)
            for typ, ident in q_struct + [(t, i) for t, i, _, _ in q_assert]:
                undetermined.append((typ, ident, 'contested correspondence', pid))
    elif state == REFERENT_CORRESPONDING:
        for pid in component:
            if pid == proposition.id:
                continue
            q = session.get(Proposition, pid)
            q_struct, q_assert, _, _ = _about_direct(session, q, retracted)
            for typ, ident in q_struct:
                add_path(typ, ident, ABOUT_PATH_CORRESPONDENCE, [('proposition_corresponds', proposition.id, pid), ('structural', pid)])
            for typ, ident, claim_id, asserter in q_assert:
                add_path(typ, ident, ABOUT_PATH_CORRESPONDENCE,
                         [('proposition_corresponds', proposition.id, pid), ('proposition_concerns', claim_id, asserter)])
    for pid in cands:                                         # candidate correspondents: candidates only
        q = session.get(Proposition, pid)
        q_struct, q_assert, _, _ = _about_direct(session, q, retracted)
        for typ, ident in q_struct + [(t, i) for t, i, _, _ in q_assert]:
            candidates.append((typ, ident, 'candidate correspondence', pid))

    # ── conflicts: established sources reaching incompatible identities of one type - reported, not resolved ──
    conflicts = []
    for typ in ABOUT_IDENTITY_TYPES:
        reached = {}
        for t, i in structural:
            if t == typ:
                reached.setdefault(i, []).append(ABOUT_STRUCTURAL)
        for t, i, _, _ in asserted:
            if t == typ:
                reached.setdefault(i, []).append(ABOUT_ASSERTED)
        for (t, i), paths in derived.items():
            if t == typ:
                reached.setdefault(i, []).extend(ABOUT_DERIVED + ':' + pth['path'] for pth in paths)
        art_set = artefact_sets.get(typ, set())
        if reached and art_set and not set(reached) <= art_set:
            for i in sorted(art_set - set(reached)):
                reached.setdefault(i, []).append('artefact level')
        if len(reached) > 1:
            conflicts.append({'type': typ, 'identities': {i: sorted(v) for i, v in sorted(reached.items())}})

    out = {'proposition_id': proposition.id,
           'structural': sorted(structural),
           'asserted': sorted(asserted),
           'derived': [{'type': t, 'id': i, 'paths': paths} for (t, i), paths in sorted(derived.items())],
           'candidates': sorted(candidates, key=lambda c: (c[0], c[1], c[2], c[3] or 0)),
           'undetermined': sorted(undetermined, key=lambda u: (u[0], u[1], u[2], u[3] or 0)),
           'conflicts': conflicts,
           'note': None}
    if not structural and not asserted and not derived:
        out['note'] = 'candidates only' if candidates else 'no about-ness established'
    return out


# ── Item 7, pass 7D: level consistency - a CONSUMER derivation, a REPORT not a verdict ─
# gw 2.0/CONSUMER_DERIVATIONS.md s 7D.7, ruled 2026-09-16. For one artefact and one identity type: the
# artefact's ESTABLISHED concern set (claims, asserters) and every line read from the artefact classified
# by whether its established about-ness - asserted, structural, or derived through ESTABLISHED
# correspondence, taken from aboutness() WITH ITS PROVENANCE and never as a claim; the artefact-derived
# path excluded because it IS the artefact level - lies within that set:
#     consistent      established line identity in the established artefact set
#     inconsistent    established line identity outside it - both sides named
#     no_line_basis   the line has no established about-ness independent of the artefact level
#                     (candidates are listed and never raise an inconsistency)
#     no_level_basis  the artefact has no established concern of the type - NOT consistent (s1.5)
#     unresolved      the artefact side is contested for the type and the line lies outside the
#                     established set - contested stops the consumer; nothing is manufactured
# Never a Boolean. Partitioned by type - an artefact concerning O1, E1 and p never makes an obligation
# line "in conflict" because of E1 or p. Two propositions established as one claim but asserted about
# different identities are a PROPOSITION DISAGREEMENT, its own class, not a level. It refuses no claim
# at write (Pa7), settles nothing by level, specificity, recency, count or party, ranks no asserter,
# writes no status and suggests no retraction; the count of disagreeing lines is descriptive metadata,
# never majority, weight, confidence or probability. Surfaced to the household, who may retract or
# re-assert; recomputed on every read. Which evidence wins belongs elsewhere, if ever ruled.
LEVEL_CONSISTENT = 'consistent'
LEVEL_INCONSISTENT = 'inconsistent'
LEVEL_NO_LINE_BASIS = 'no_line_basis'
LEVEL_NO_LEVEL_BASIS = 'no_level_basis'
LEVEL_UNRESOLVED = 'unresolved'
ARTEFACT_SIDE_ESTABLISHED = 'established'
ARTEFACT_SIDE_CANDIDATES = 'candidates_only'
ARTEFACT_SIDE_CONTESTED = 'contested'
ARTEFACT_SIDE_NONE = 'none'
_META_KINDS = (ARTEFACT_ORIGIN, ARTEFACT_CONCERNS, PROPOSITION_CONCERNS, PROPOSITION_CORRESPONDS, UTTERANCE_RETRACTION)


def level_consistency(session, artefact):
    """The level-consistency report for one artefact: a plain dict, computed on read, storing nothing.

        {'artefact_id',
         'types': {type: {'artefact_state': established|candidates_only|contested|none,
                          'established': {id: [(claim_id, asserter_party_id)]},
                          'candidates': [id], 'contested': [id],
                          'lines': [{'proposition': id, 'classification': ..., 'identities': [(id, source)],
                                     'candidates': [id], 'against': [id]}],
                          'inconsistencies': [line entries classified inconsistent],
                          'counts': {classification: n}}},
         'proposition_disagreements': [{'type', 'component': [ids], 'identities': {id: [(prop, source)]}}],
         'note': None | 'no lines'}
    """
    retracted = {u for (u,) in session.query(Proposition.subject_utterance_id)
                 .filter(Proposition.kind == UTTERANCE_RETRACTION, Proposition.subject_utterance_id.isnot(None)).all()}
    # ── the artefact side, per type ──────────────────────────────────────────
    types = {}
    claims = (session.query(Proposition, EvidentiaryRelationship)
              .join(EvidentiaryRelationship, EvidentiaryRelationship.proposition_id == Proposition.id)
              .filter(Proposition.kind == ARTEFACT_CONCERNS, Proposition.subject_artefact_id == artefact.id).all())
    for typ, (_, obj_col) in ABOUT_IDENTITY_TYPES.items():
        established, cand, contested = {}, set(), set()
        for claim, rel in claims:
            ident = getattr(claim, obj_col)
            if ident is None:
                continue
            if rel.utterance_id is None:
                cand.add(ident)
            elif rel.utterance_id in retracted:
                contested.add(ident)
            else:
                established.setdefault(ident, []).append((claim.id, rel.utterance.origin_party_id))
        contested -= set(established)
        cand -= set(established) | contested
        if established:
            state = ARTEFACT_SIDE_ESTABLISHED
        elif contested:
            state = ARTEFACT_SIDE_CONTESTED
        elif cand:
            state = ARTEFACT_SIDE_CANDIDATES
        else:
            state = ARTEFACT_SIDE_NONE
        types[typ] = {'artefact_state': state, 'established': established, 'candidates': sorted(cand),
                      'contested': sorted(contested), 'lines': [], 'inconsistencies': [], 'counts': {}}
    # ── the lines: every non-meta proposition read from this artefact ─────────
    reading_ids = [r.id for r in session.query(Reading).filter(Reading.artefact_id == artefact.id).all()]
    lines = []
    if reading_ids:
        seen = set()
        for prop, _rel in (session.query(Proposition, EvidentiaryRelationship)
                           .join(EvidentiaryRelationship, EvidentiaryRelationship.proposition_id == Proposition.id)
                           .filter(EvidentiaryRelationship.reading_id.in_(reading_ids),
                                   Proposition.kind.notin_(_META_KINDS)).order_by(Proposition.id).all()):
            if prop.id not in seen:
                seen.add(prop.id)
                lines.append(prop)
    out = {'artefact_id': artefact.id, 'types': types, 'proposition_disagreements': [], 'note': None if lines else 'no lines'}
    components_seen = set()
    for prop in lines:
        ab = aboutness(session, prop)
        for typ, t in types.items():
            idents = []                                       # established line identities, independent of the artefact level
            for tt, i in ab['structural']:
                if tt == typ:
                    idents.append((i, ABOUT_STRUCTURAL))
            for tt, i, claim_id, asserter in ab['asserted']:
                if tt == typ:
                    idents.append((i, ABOUT_ASSERTED))
            for d in ab['derived']:
                if d['type'] == typ and any(pth['path'] == ABOUT_PATH_CORRESPONDENCE for pth in d['paths']):
                    idents.append((d['id'], ABOUT_DERIVED + ':' + ABOUT_PATH_CORRESPONDENCE))
            line_cands = sorted({i for tt, i, _, _ in ab['candidates'] if tt == typ})
            # line-level undetermined entries (a retracted assertion, a contested correspondence) are reported;
            # they are not a basis and they classify nothing - the artefact-side contest is the type's own state
            line_undet = sorted({(i, reason) for tt, i, reason, _ in ab['undetermined']
                                 if tt == typ and reason != 'contested artefact concerns'})
            entry = {'proposition': prop.id, 'identities': sorted(set(idents)), 'candidates': line_cands,
                     'undetermined': line_undet, 'against': []}
            est = set(t['established'])
            if not idents:
                cls = LEVEL_NO_LINE_BASIS
            elif t['artefact_state'] == ARTEFACT_SIDE_ESTABLISHED:
                outside = sorted({i for i, _ in idents} - est)
                if not outside:
                    cls = LEVEL_CONSISTENT
                elif t['contested']:
                    cls = LEVEL_UNRESOLVED                    # the artefact side is contested for this type: nothing manufactured
                else:
                    cls = LEVEL_INCONSISTENT
                    entry['against'] = sorted(est)
            elif t['artefact_state'] == ARTEFACT_SIDE_CONTESTED:
                cls = LEVEL_UNRESOLVED
            else:
                cls = LEVEL_NO_LEVEL_BASIS
            entry['classification'] = cls
            t['lines'].append(entry)
            if cls == LEVEL_INCONSISTENT:
                t['inconsistencies'].append(entry)
            t['counts'][cls] = t['counts'].get(cls, 0) + 1
        # proposition-level disagreement: members of one ESTABLISHED component asserted about different identities
        state, component, _ = referent(session, prop)
        key = tuple(sorted(component))
        if state == REFERENT_CORRESPONDING and len(component) > 1 and key not in components_seen:
            components_seen.add(key)
            per_type = {}
            for pid in component:
                q = ab if pid == prop.id else aboutness(session, session.get(Proposition, pid))
                for tt, i in q['structural']:
                    per_type.setdefault(tt, {}).setdefault(i, []).append((pid, ABOUT_STRUCTURAL))
                for tt, i, _, _ in q['asserted']:
                    per_type.setdefault(tt, {}).setdefault(i, []).append((pid, ABOUT_ASSERTED))
            for tt, idents in per_type.items():
                if len(idents) > 1:
                    out['proposition_disagreements'].append({'type': tt, 'component': list(key), 'identities': idents})
    return out


STRENGTH_KNOWING = 'knowing'
STRENGTH_NOT_KNOWING = 'not_knowing'
STRENGTH_UNDETERMINED = 'undetermined'


def _weakest(*strengths):
    """Weakest link (contract C3): undetermined absorbs; not_knowing beats knowing."""
    if STRENGTH_UNDETERMINED in strengths:
        return STRENGTH_UNDETERMINED
    return STRENGTH_NOT_KNOWING if STRENGTH_NOT_KNOWING in strengths else STRENGTH_KNOWING


# ── Relational knowing (RELATIONAL_KNOWING.md, ruled s9) ─────────────────────
# Knowing is a derived classification of an evidentiary relationship, not an independent fact
# about the party. A party knows a proposition when it stands in the epistemic relation the
# proposition's KIND designates, to the participant the kind designates - and in no other way:
#
#     PROPOSITION KIND -> designated epistemic relation -> designated participant -> party
#
# never "party relates to P somehow -> party knows P". Each named relation below resolves ONE
# designated participant for ONE kind of proposition, from structure already in the record. There
# is deliberately no generic resolver: nothing here finds "a related party" and calls it knowing.
# A kind that carries no `knowing_relation` derives undetermined (relational_knowing True) or falls
# back to the caller's foundation stand-in (relational_knowing False) - the stand-in survives only
# for kinds whose relation is unruled, per the ruling's last sentence.
#
# Knowing establishes exactly one thing - the strength class of an evidentiary relationship:
#     relation ruled + designated participant established + party stands in it   -> knowing
#     relation ruled + designated participant established + party does not        -> not_knowing
#     relation not ruled                                                          -> undetermined
#     designated participant not established                                      -> undetermined
# not_knowing means "this party is not the party the ruled relation identifies" - never "shown
# not to know". Minting an identity does not make the minter knowing for the event's properties
# (Kn7); originating an utterance does not make the origin knowing for its content (Kn5);
# originating an artefact does not make the origin knowing for every kind read from it (Kn10);
# holding an artefact is custody, not knowledge; a process is never knowing.

def _designated_origin_of_subject_utterance(session, prop):
    """utterance_retraction: the party knowing for "U's assertion no longer stands" is U's own
    origin. Designated participant: the subject utterance; relation: its origin party."""
    if prop.subject_utterance_id is None:
        return None
    utt = session.get(Utterance, prop.subject_utterance_id)
    return utt.origin_party_id if utt is not None else None


def _designated_minter_of_object_identity(session, prop):
    """artefact_concerns / proposition_concerns: the party knowing for "this concerns identity X"
    is the origin of the utterance that minted X - the household member who declared the
    obligation or payment knows which documents and lines are about it. Designated participant:
    the object identity (obligation or payment); relation: its minting utterance's origin.
    This is NOT "minted_by -> knowing" in general: it applies to the about-ness kinds only, whose
    designated participant IS the minted identity. Kn7 stands: the minter is not thereby knowing
    for the event's amount, date, payee or occurrence."""
    if prop.object_obligation_id is not None:
        ident = session.get(Obligation, prop.object_obligation_id)
    elif prop.object_payment_id is not None:
        ident = session.get(Payment, prop.object_payment_id)
    elif prop.object_expense_id is not None:
        ident = session.get(Expense, prop.object_expense_id)
    elif prop.object_plan_id is not None:
        ident = session.get(Plan, prop.object_plan_id)
    else:
        return None
    if ident is None:
        return None
    utt = session.get(Utterance, ident.minted_by_id)
    return utt.origin_party_id if utt is not None else None


# name -> resolver. Adding a relation means adding a NAMED entry here and naming it on a ruled
# kind; nothing resolves a relation that is not in this table.
_KNOWING_RELATIONS = {
    KNOWING_ORIGIN_OF_SUBJECT_UTTERANCE: _designated_origin_of_subject_utterance,
    KNOWING_MINTER_OF_OBJECT_IDENTITY: _designated_minter_of_object_identity,
}


def _relational_strength(session, prop, claimant_party_id, relation_name):
    """The ruled classification, for a kind whose designated relation is named."""
    resolver = _KNOWING_RELATIONS.get(relation_name)
    if resolver is None:
        return STRENGTH_UNDETERMINED                       # relation not ruled
    designated = resolver(session, prop)
    if designated is None or claimant_party_id is None:
        return STRENGTH_UNDETERMINED                       # designated participant not established
    return STRENGTH_KNOWING if claimant_party_id == designated else STRENGTH_NOT_KNOWING


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
        # Relational knowing (RELATIONAL_KNOWING.md s9): the caller's foundation map is never
        # consulted for these kinds. A reading-sourced claim of a relational kind is a candidate
        # (reading_establishes is False for all of them) -> undetermined. An utterance-sourced
        # claim is classified by the kind's NAMED designated relation, if it has one; a relational
        # kind with no named relation stays undetermined - nothing is manufactured for a flag.
        if relation.reading_id is not None or relation.reading is not None:
            return STRENGTH_UNDETERMINED
        utt = relation.utterance if relation.utterance is not None else session.get(Utterance, relation.utterance_id)
        if utt is None:
            return STRENGTH_UNDETERMINED
        return _relational_strength(session, prop, utt.origin_party_id, rule.get('knowing_relation'))
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


# ── Item 7, pass 7E: multi-link strength - a CONSUMER derivation ─────────────
# gw 2.0/CONSUMER_DERIVATIONS.md s 7E.7, ruled 2026-09-17. A CLASS, not a quantity. For one
# proposition: the class of each of its evidentiary relationships as the substrate derives it
# (derived_strength - as given, never re-derived), and, for every about-ness aboutness() reports as
# ESTABLISHED, every chain by which it is reached - the value's evidence followed by the links of
# one 7C path - as a list of links, each a claim on record with its own ground, and the chain's
# class as the WEAKEST link on the substrate's lattice (_weakest: undetermined absorbs).
#
#     evidence (L0)  ->  proposition_concerns | artefact_concerns | proposition_corresponds ...  ->  weakest
#
# 7E's only new operation is composition: consume the class of each already-established link and
# take the weakest along ONE established chain. Ground aggregation belongs entirely to
# derived_strength: the substrate's class is per evidentiary relationship, its only resolution of
# parallel grounds lives inside L0 (the origin claims within a reading-sourced relationship) and is
# inherited whole; for a concerns or correspondence link a ground IS an evidentiary relationship, so a
# link with n established grounds yields n chains - 7E aggregates nowhere, ranks no party, and
# assigns no class to a link beside its ground's. A correspondence link is undetermined BY DESIGN
# (Kn4 - correspondence has no ruled epistemology; 7E manufactures none), so every chain through
# correspondence is undetermined whatever its other links say; a correspondence path is expanded
# into its hops, every simple route listed, none chosen; a structural terminus is trace, not a link.
# Not links: readers (channels), role claims (no role kind is ruled - Kn6's servicer chain has
# nothing to evaluate and nothing is built from context), the fenced capture-faithfulness link
# (neither added nor claimed evaluated), ruled domain relations (D'.11), candidates, contested, counts.
# A chain IS its sequence of grounds (L0, ground_1 .. ground_n): equal sequences are one chain, reported
# once, however many structural traversals reach it; different sequences are different chains, however
# alike - a link is a claim on record, and two claims are two. "Simple" = no proposition visited twice.
# Across chains to one identity: NOTHING - listed in structural order (evidence, claim, ground ids),
# never chosen, summed, counted or ordered by class; no per-identity class. Across identities:
# nothing - 7C's conflicts are carried as a structural condition and graded not at all. The value's
# own class is reported unchanged beside its chains (Ab7: the chain grades the derivation that the
# value is about the identity, never the value). Where about-ness is a candidate, contested or
# undetermined there is no chain and no class - `unchained` is a report condition, not a strength;
# where there is no evidence there is no chain and no class - neither absence is undetermined.
# Reads no independence (independence is not strength; multiplicity is not strength), no level
# report, chooses no reading, says nothing of truth (Kn12). Computed on read, stored nowhere.
CHAIN_LINK_EVIDENCE = 'evidence'
CHAIN_TRACE_STRUCTURAL = 'structural'


def _link_grounds(session, claim_id, retracted):
    """The established grounds of one claim on record: its utterance-sourced, unretracted evidentiary
    relationships, in id order. A reading-sourced relationship of a relational kind is a candidate,
    never a ground; a retracted assertion is not a basis."""
    rels = (session.query(EvidentiaryRelationship)
            .filter(EvidentiaryRelationship.proposition_id == claim_id, EvidentiaryRelationship.utterance_id.isnot(None))
            .order_by(EvidentiaryRelationship.id).all())
    return [r for r in rels if r.utterance_id not in retracted]


def _correspondence_routes(session, start, end, retracted):
    """Every SIMPLE route of established proposition_corresponds claims from `start` to `end`, each a
    list of (claim_id, from, to) hops; a claim is read both ways (symmetric). Simple = no proposition
    visited twice on the route, so a cycle in the component terminates rather than multiplying routes,
    and no claim can repeat. Two different claims between the same pair are two routes. None is chosen."""
    edges = {}
    for c in session.query(Proposition).filter(Proposition.kind == PROPOSITION_CORRESPONDS).order_by(Proposition.id).all():
        if _link_grounds(session, c.id, retracted):
            edges.setdefault(c.subject_proposition_id, []).append((c.id, c.object_proposition_id))
            edges.setdefault(c.object_proposition_id, []).append((c.id, c.subject_proposition_id))
    routes = []

    def walk(node, visited, path):
        if node == end:
            routes.append(list(path))
            return
        for cid, nxt in sorted(edges.get(node, [])):
            if nxt not in visited:
                walk(nxt, visited | {nxt}, path + [(cid, node, nxt)])
    walk(start, {start}, [])
    return routes


def chain_strength(session, proposition, knowing):
    """The multi-link strength derivation for one proposition: a plain dict, computed on read, storing nothing.

        {'proposition_id',
         'evidence':  [{'relationship', 'source': utterance|reading, 'source_id', 'artefact', 'origin',
                        'class': knowing|not_knowing|undetermined}]        - L0, derived_strength AS GIVEN
         'about':     [{'type', 'id', 'provenance': structural|asserted|derived, 'path': None|artefact|correspondence,
                        'chains': [{'evidence': relationship_id,
                                    'links': [{'kind', 'claim', 'ground', 'class'}],   the first link is L0
                                    'trace': [(kind, id)...],                          reading / artefact / structural terminus
                                    'class': the weakest link}]}]
         'unchained': [(type, id, candidate|undetermined, reason)]   - 7C's; no chain, NO class - a report condition
         'conflicts': 7C's, as found - a structural condition; no class is assigned to a conflict
         'note': 'no evidentiary relationship' | 'no about-ness established' | None}

    `knowing` is the caller's kind -> foundations map, as for derived_strength. No class per identity, no
    class per proposition, no count, no number, no order by class, no write.
    """
    retracted = {u for (u,) in session.query(Proposition.subject_utterance_id)
                 .filter(Proposition.kind == UTTERANCE_RETRACTION, Proposition.subject_utterance_id.isnot(None)).all()}
    rels = (session.query(EvidentiaryRelationship).filter(EvidentiaryRelationship.proposition_id == proposition.id)
            .order_by(EvidentiaryRelationship.id).all())
    evidence = []
    for r in rels:
        artefact_id, origin = None, None
        if r.reading_id is not None:
            rd = r.reading if r.reading is not None else session.get(Reading, r.reading_id)
            art = rd.artefact if rd.artefact is not None else session.get(Artefact, rd.artefact_id)
            artefact_id = art.id
            state, parties = artefact_origin(session, art)
            origin = parties[0] if state == ORIGIN_ESTABLISHED else None
        else:
            utt = r.utterance if r.utterance is not None else session.get(Utterance, r.utterance_id)
            origin = utt.origin_party_id if utt is not None else None
        evidence.append({'relationship': r.id, 'source': 'reading' if r.reading_id is not None else 'utterance',
                         'source_id': r.reading_id if r.reading_id is not None else r.utterance_id,
                         'artefact': artefact_id, 'origin': origin, 'class': derived_strength(session, r, knowing)})
    out = {'proposition_id': proposition.id, 'evidence': evidence, 'about': [], 'unchained': [], 'conflicts': [], 'note': None}
    if not evidence:
        out['note'] = 'no evidentiary relationship'
        return out
    ab = aboutness(session, proposition)
    out['unchained'] = ([(t, i, ABOUT_CANDIDATE, reason) for t, i, reason, _ in ab['candidates']]
                        + [(t, i, ABOUT_UNDETERMINED, reason) for t, i, reason, _ in ab['undetermined']])
    out['conflicts'] = ab['conflicts']

    def l0(e):
        return {'kind': CHAIN_LINK_EVIDENCE, 'claim': None, 'ground': e['relationship'], 'class': e['class']}

    def ground(kind, claim_id, rel):
        return {'kind': kind, 'claim': claim_id, 'ground': rel.id, 'class': derived_strength(session, rel, knowing)}

    def chain(links, trace=()):
        return {'evidence': links[0]['ground'], 'links': links, 'trace': list(trace), 'class': _weakest(*(l['class'] for l in links))}

    entries = {}                                              # (type, id, provenance, path) -> chains
    seen = set()                                              # chain identities already reported

    def add(typ, ident, provenance, path, chains):
        # A chain IS its sequence of grounds (L0, ground_1 .. ground_n). Two enumerations that reach the same
        # sequence - 7C lists one correspondence path per (claim, ground) of the correspondent's assertion, so
        # a two-ground terminal claim arrives twice - are ONE chain, reported once. Two different claims on
        # record between the same nodes are two grounds, hence two chains: nothing is merged that differs.
        bucket = entries.setdefault((typ, ident, provenance, path), [])
        for c in chains:
            identity = tuple(l['ground'] for l in c['links'])
            if identity not in seen:
                seen.add(identity)
                bucket.append(c)

    for typ, ident in ab['structural']:
        add(typ, ident, ABOUT_STRUCTURAL, None, [chain([l0(e)]) for e in evidence])
    for typ, ident, claim_id in sorted({(t, i, c) for t, i, c, _ in ab['asserted']}):
        add(typ, ident, ABOUT_ASSERTED, None,
            [chain([l0(e), ground(PROPOSITION_CONCERNS, claim_id, g)])
             for e in evidence for g in _link_grounds(session, claim_id, retracted)])
    for d in ab['derived']:
        typ, ident = d['type'], d['id']
        for pth in d['paths']:
            links = pth['links']
            if pth['path'] == ABOUT_PATH_ARTEFACT:
                reading_id = next(x[1] for x in links if x[0] == 'reading')
                artefact_id = next(x[1] for x in links if x[0] == 'artefact')
                claims = sorted({x[1] for x in links if x[0] == ARTEFACT_CONCERNS})
                add(typ, ident, ABOUT_DERIVED, ABOUT_PATH_ARTEFACT,
                    [chain([l0(e), ground(ARTEFACT_CONCERNS, c, g)], trace=[('reading', e['source_id']), ('artefact', artefact_id)])
                     for e in evidence if e['source'] == 'reading' and e['artefact'] == artefact_id
                     for c in claims for g in _link_grounds(session, c, retracted)])
            else:
                _, start, end = next(x for x in links if x[0] == PROPOSITION_CORRESPONDS)
                terminal = links[-1]
                chains = []
                for route in _correspondence_routes(session, start, end, retracted):
                    hop_grounds = [[(cid, g) for g in _link_grounds(session, cid, retracted)] for cid, _, _ in route]
                    if terminal[0] == PROPOSITION_CONCERNS:
                        ends = [[(PROPOSITION_CONCERNS, terminal[1], g)] for g in _link_grounds(session, terminal[1], retracted)]
                        trace = []
                    else:
                        ends = [[]]
                        trace = [(CHAIN_TRACE_STRUCTURAL, end)]
                    for e in evidence:
                        for combo in itertools.product(*hop_grounds):
                            for tail in ends:
                                chains.append(chain([l0(e)] + [ground(PROPOSITION_CORRESPONDS, cid, g) for cid, g in combo]
                                                    + [ground(k, c, g) for k, c, g in tail], trace=trace))
                add(typ, ident, ABOUT_DERIVED, ABOUT_PATH_CORRESPONDENCE, chains)
    out['about'] = [{'type': t, 'id': i, 'provenance': pv, 'path': pth, 'chains': ch}
                    for (t, i, pv, pth), ch in entries.items()]
    if not out['about']:
        out['note'] = 'no about-ness established'
    return out


# ── Item 7, pass 7F: traversal - two CONSUMER derivations, one hop, nothing chosen ─────
# gw 2.0/CONSUMER_DERIVATIONS.md s 7F.6-7F.8, ruled 2026-09-18. A traversal reads ONE ruled relation
# ONE hop and stops at its endpoints - all of them, with the claim, the asserter and the state of
# each - choosing none. It answers the reverse direction as a query so labelled and mints no
# inverse kind (D'18); carries nothing of the endpoint onto the subject (C17); composes no second
# hop (D'.11 open - no via / path / recursion) and infers no relation no claim asserts (E24 - not
# from a shared person, membership or date); refuses BY NAME a kind that is unruled, one of the
# record's own meta-kinds (origin, correspondence, concerns, retraction - each has its own
# derivation) or a boundary kind - an empty list would be indistinguishable from "none exist".
#
# For a role, the dated derivation (TS, ruled s 7F.8): a stance is about its as_of = t and asserts
#     holds  -> in effect at t;        immediately before t: nothing (R1)
#     began  -> in effect at t;        immediately before t: NOT in effect   (a transition)
#     ended  -> NOT in effect at t;    immediately before t: in effect       (a transition; TS-c: the
#                                                                             ending's date is the first
#                                                                             date not in effect)
# and nothing about any other date. The one extrapolation - a consumer rule, not substrate
# ontology - is "a stance stands until the next stance": G(d) = the established stances at the
# latest as_of <= d read forward; N(d) = those at the earliest as_of > d read back; undetermined
# when G is empty (absence is not zero - an ending alone supplies no answer before it); contested
# when G disagrees within itself (began + ended on one date) or when a stance in N reads back
# against G's answer (R5's two endings; two beginnings with no ending between); otherwise G's
# answer. A holds reads nothing back and never contests; only the nearest next stance is consulted.
# Candidate (reading-sourced) and contested (retracted) stances neither govern nor contest - they
# are listed. G and N are both IN THE REPORT, so every answer shows the stance it rests on and the
# stance that could contest it: an extrapolation is visible as one. No period is materialised, no
# overlap resolved (two identities in effect are two), no disputed boundary settled, no retraction
# read as an ending, no created_at consulted (as-the-record-stood is the audit's question).
# No role kind is ruled: in_effect runs today on stand-in kinds a fixture registers and removes,
# and changes shape for none of the kinds accepted and unbuilt (E, F). Computed on read; stored nowhere.
EFFECT_IN = 'in_effect'
EFFECT_NOT = 'not_in_effect'
EFFECT_UNDETERMINED = 'undetermined'
EFFECT_CONTESTED = 'contested'
STANCE_HOLDS = 'holds'
CLAIM_ESTABLISHED = 'established'
CLAIM_CANDIDATE = 'candidate'
CLAIM_CONTESTED = 'contested'
DIRECTION_SUBJECT = 'subject'
DIRECTION_OBJECT = 'object'
DIRECTION_SYMMETRIC = 'symmetric'

_TRAVERSAL_META = set(_META_KINDS) | {k for k, _, _ in _CORRESPONDENCE_OF.values()}


def _slot_type(col):
    """'subject_obligation_id' -> 'obligation'."""
    return col.split('_', 1)[1].rsplit('_', 1)[0]


def _claim_states(session, claim, retracted):
    """One (state, asserter, relationship_id) per evidentiary relationship of a claim."""
    out = []
    for rel in (session.query(EvidentiaryRelationship).filter(EvidentiaryRelationship.proposition_id == claim.id)
                .order_by(EvidentiaryRelationship.id).all()):
        if rel.utterance_id is None:
            out.append((CLAIM_CANDIDATE, None, rel.id))
        elif rel.utterance_id in retracted:
            out.append((CLAIM_CONTESTED, rel.utterance.origin_party_id, rel.id))
        else:
            out.append((CLAIM_ESTABLISHED, rel.utterance.origin_party_id, rel.id))
    return out


def _retracted(session):
    return {u for (u,) in session.query(Proposition.subject_utterance_id)
            .filter(Proposition.kind == UTTERANCE_RETRACTION, Proposition.subject_utterance_id.isnot(None)).all()}


def _referent_members(session, thing):
    """The established referent of `thing` (its own id when separate or when the component is contested)."""
    if type(thing).__name__ not in _CORRESPONDENCE_OF:
        return [thing.id], None
    state, component, _ = referent(session, thing)
    if state == REFERENT_CORRESPONDING:
        return sorted(component), None
    if state == REFERENT_CONTESTED:
        return [thing.id], 'subject referent contested - read alone'
    return [thing.id], None


def reach(session, thing, kind, as_object=False):
    """The endpoint traversal for one thing and one ruled relation kind: a plain dict, computed on read,
    storing nothing.

        {'kind', 'direction': subject|object|symmetric, 'subject': id, 'subject_type', 'referent': [ids],
         'endpoints': [{'id', 'type', 'claim', 'asserter', 'state': established|candidate|contested, 'ground'}],
         'note'}

    Every claim, every ground, nothing chosen. `as_object=True` answers the reverse direction as a
    query - the endpoints are the claims' SUBJECTS - labelled 'object'; no inverse kind exists.
    Refuses by name (ValueError): an unruled kind; a meta-kind (origin, any correspondence, concerns,
    retraction - each has its own derivation); a boundary kind; a thing whose type does not fill the
    kind's slot.
    """
    rule = RULED_KINDS.get(kind)
    if rule is None:
        raise ValueError(f'reach: kind not ruled - {kind!r}; a traversal reads semantics, not strings')
    if kind in _TRAVERSAL_META:
        raise ValueError(f'reach: {kind!r} is one of the record\'s own kinds and has its own derivation; not traversed')
    if rule.get('boundary'):
        raise ValueError(f'reach: {kind!r} is a boundary kind - a stance, not a relation; in_effect reads it')
    typ = type(thing).__name__.lower()
    symmetric = rule.get('symmetric', False)
    side, other = ('object', 'subject') if as_object else ('subject', 'object')
    if symmetric:
        cols = list(rule['subject']) + list(rule['object'])
        direction = DIRECTION_SYMMETRIC
    else:
        cols = list(rule[side])
        direction = DIRECTION_OBJECT if as_object else DIRECTION_SUBJECT
    if not any(_slot_type(c) == typ for c in cols):
        raise ValueError(f'reach: a {typ} does not fill the {side} slot of {kind!r}')
    members, note = _referent_members(session, thing)
    retracted = _retracted(session)
    endpoints = []
    for col in cols:
        if _slot_type(col) != typ:
            continue
        claims = (session.query(Proposition).filter(Proposition.kind == kind, getattr(Proposition, col).in_(members))
                  .order_by(Proposition.id).all())
        for claim in claims:
            if symmetric:
                other_cols = [c for c in list(rule['subject']) + list(rule['object']) if c != col]
            else:
                other_cols = list(rule[other])
            for ocol in other_cols:
                ident = getattr(claim, ocol)
                if ident is None:
                    continue
                for state, asserter, ground in _claim_states(session, claim, retracted):
                    endpoints.append({'id': ident, 'type': _slot_type(ocol), 'claim': claim.id,
                                      'asserter': asserter, 'state': state, 'ground': ground})
    if not endpoints and note is None:
        note = 'no claim'
    return {'kind': kind, 'direction': direction, 'subject': thing.id, 'subject_type': typ, 'referent': members,
            'endpoints': endpoints, 'note': note}


def _stance_answer(established, d):
    """TS: G(d) read forward, N(d) read back. Returns (answer, governing, next)."""
    before = [st for st in established if st['as_of'] <= d]
    after = [st for st in established if st['as_of'] > d]
    if not before:
        return EFFECT_UNDETERMINED, [], ([st for st in after if st['as_of'] == min(x['as_of'] for x in after)] if after else [])
    g_date = max(st['as_of'] for st in before)
    G = [st for st in before if st['as_of'] == g_date]
    N = [st for st in after if st['as_of'] == min(x['as_of'] for x in after)] if after else []
    fwd = {EFFECT_NOT if st['sort'] == BOUNDARY_ENDED else EFFECT_IN for st in G}
    if len(fwd) > 1:
        return EFFECT_CONTESTED, G, N
    answer = next(iter(fwd))
    for st in N:
        bwd = EFFECT_IN if st['sort'] == BOUNDARY_ENDED else EFFECT_NOT if st['sort'] == BOUNDARY_BEGAN else None
        if bwd is not None and bwd != answer:
            return EFFECT_CONTESTED, G, N
    return answer, G, N


def in_effect(session, party, role_kind, d):
    """The dated derivation for one party and one ruled role kind on date `d` (ISO string or date): a plain
    dict, computed on read, storing nothing.

        {'party', 'referent': [ids], 'kind', 'd',
         'identities': {id: {'answer': in_effect|not_in_effect|undetermined|contested,
                             'governing': [stance...], 'next': [stance...],
                             'stances': [{'sort': holds|began|ended, 'kind', 'as_of', 'claim', 'asserter', 'state', 'ground'}]}},
         'in_effect': [ids answered in_effect],    a fact - several is an overlap, reported, never resolved
         'note'}

    Refuses by name (ValueError): an unruled kind; a boundary kind (a stance, not a role); a kind no
    boundary kind is `of` (a relation, not a role); a party that is not a Party.
    """
    rule = RULED_KINDS.get(role_kind)
    if rule is None:
        raise ValueError(f'in_effect: kind not ruled - {role_kind!r}')
    if rule.get('boundary'):
        raise ValueError(f'in_effect: {role_kind!r} is a boundary kind, not a role; name the role it is of')
    bounds = {k: r for k, r in RULED_KINDS.items() if r.get('of') == role_kind and r.get('boundary') in (BOUNDARY_BEGAN, BOUNDARY_ENDED)}
    if not bounds:
        raise ValueError(f'in_effect: {role_kind!r} is not a role - no boundary kind is bound to it; a relation has no "in effect"')
    if type(party).__name__ != 'Party' or 'subject_party_id' not in rule['subject']:
        raise ValueError(f'in_effect: {role_kind!r} takes a party subject; got {type(party).__name__}')
    d = d.isoformat() if hasattr(d, 'isoformat') else str(d)
    members, note = _referent_members(session, party)
    retracted = _retracted(session)
    obj_cols = list(rule['object'])
    sorts = {role_kind: STANCE_HOLDS}
    sorts.update({k: r['boundary'] for k, r in bounds.items()})
    per_identity = {}
    for claim in (session.query(Proposition).filter(Proposition.kind.in_(sorted(sorts)), Proposition.subject_party_id.in_(members))
                  .order_by(Proposition.id).all()):
        ident = next((getattr(claim, c) for c in obj_cols if getattr(claim, c) is not None), None)
        if ident is None:
            continue
        for state, asserter, ground in _claim_states(session, claim, retracted):
            per_identity.setdefault(ident, []).append({'sort': sorts[claim.kind], 'kind': claim.kind, 'as_of': claim.as_of,
                                                       'claim': claim.id, 'asserter': asserter, 'state': state, 'ground': ground})
    identities = {}
    for ident, stances in sorted(per_identity.items()):
        established = [st for st in stances if st['state'] == CLAIM_ESTABLISHED and st['as_of']]
        answer, G, N = _stance_answer(established, d)
        identities[ident] = {'answer': answer, 'governing': G, 'next': N, 'stances': stances}
    return {'party': party.id, 'referent': members, 'kind': role_kind, 'd': d, 'identities': identities,
            'in_effect': [i for i, v in identities.items() if v['answer'] == EFFECT_IN],
            'note': note if note else ('no stance' if not identities else None)}


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
