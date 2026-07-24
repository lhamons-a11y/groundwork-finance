# Groundwork Debt Reconciliation & Recurring Payment Blueprint

**Status:** Design Phase  
**Version:** 1.0  
**Date:** July 24, 2026  
**Integration:** Parallel with Phase 1 (Voice Gate) and Phase 4 (PDF Extraction)  
**Scope:** Complete reconciliation loop for manual-entry debt users; adaptive feedback from payoff plan

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Data Architecture](#data-architecture)
4. [Build Sequence](#build-sequence)
5. [Module-by-Module Specification](#module-by-module-specification)
6. [Integration Points](#integration-points)
7. [Historian & Learning](#historian--learning)
8. [Narrative Integration](#narrative-integration)
9. [Testing & Validation](#testing--validation)
10. [Phase Gates](#phase-gates)

---

## Overview

### Feature Summary

Users who manually track debt (no CSV/PDF import) can now:
- Enter charges and payments directly in debt account ledgers
- Link checking transactions (payments) to debt accounts (no re-entry)
- Save payment patterns as recurring drafts
- Receive suggested payment amounts from their payoff plan
- See actual vs. planned behavior tracked in the historian
- Receive adaptive narratives reflecting compliance and variance

### Core User Journey

1. User has a Capital One card, $5,000 balance, no auto-import
2. User creates a payoff plan: "$735/month for 24 months"
3. User manually enters a $600 charge (Costco, July 3)
4. User sees a checking payment "Transfer to Capital One $500" (July 15)
5. User tags it as payment to Capital One (one-tap link)
6. User saves as recurring
7. August 10: Draft appears "**$735 payment due Aug 15** — this is your payoff plan suggestion — confirm or edit"
8. User confirms (one tap) or edits to $450 (tighter month)
9. Historian logs the event; Distance Traveled narrative updates: "You're on track" or "You're below plan by $204"

### Design Principles

- **Automation feels invisible.** The app shows what the user already decided (payoff plan), not what it guesses.
- **No double-entry.** Checking transaction is the single source of truth for the payment; debt ledger links to it.
- **Reality is surfaced, not hidden.** Late charges, payment variance, timing slippage all visible in calculations.
- **Historian is production-grade.** This feature is the first real use of historian for adaptive learning.
- **Ledger verbiage changes per account type.** Debt accounts say "Charged" / "Payment" / "Interest", not "Transaction".

---

## Problem Statement

### The Reconciliation Gap

**Current state:**
- Groundwork excels at ledger-based tracking (CSV/OFX import)
- Debt payoff plan exists as a recommendation
- BUT: Users without auto-import have no way to track actual vs. planned payments within the app
- Result: Users re-export CSVs monthly (friction), or abandon plan tracking (lose accountability)

**Why it matters:**
- ~40% of users prefer manual entry for sparse-use cards (single large charge per month, then payments)
- These users *want* accountability but currently have no coherent loop
- They feel like Groundwork is a forecast machine, not a source of truth
- Missing this piece makes the app incoherent for a substantial segment

### Success Criteria

- [ ] User can manually enter charge/payment in debt ledger (no CSV required)
- [ ] User can link a checking payment to a debt payment (no duplicate entry)
- [ ] Recurring payment drafts appear 3–5 days before scheduled date
- [ ] Draft pre-fills with payoff plan suggestion; user can confirm/edit
- [ ] Edited amounts are logged to historian
- [ ] Distance Traveled narrative reflects plan vs. actual compliance
- [ ] App feels "completely automated" — user makes one decision, app handles the rest

---

## Data Architecture

### New / Modified Tables

#### 1. `debt_ledger_entries` (NEW — replaces generic "transactions" for debt accounts)

```sql
CREATE TABLE debt_ledger_entries (
    id INTEGER PRIMARY KEY,
    debt_account_id INTEGER NOT NULL FOREIGN KEY,
    entry_type ENUM('charge', 'payment', 'interest', 'fee') NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    entry_date DATE NOT NULL,
    description TEXT,
    category TEXT,
    merchant TEXT,
    
    -- Linking & reconciliation
    linked_checking_transaction_id INTEGER FOREIGN KEY (nullable),
    linked_payoff_plan_id INTEGER FOREIGN KEY (nullable),
    
    -- Source tracking (for historian queries)
    source_type ENUM('manual', 'imported', 'inferred') NOT NULL DEFAULT 'manual',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX (debt_account_id, entry_date),
    INDEX (source_type),
    INDEX (entry_type)
);
```

**Why this structure:**
- Semantic entry types ("charge" vs "payment") instead of generic "transaction"
- `linked_checking_transaction_id` prevents double-entry
- `source_type` enables historian queries ("how many manual entries vs imported?")
- `linked_payoff_plan_id` enables narrative tie-in ("This payment follows your plan")

#### 2. `recurring_debt_payments` (NEW)

```sql
CREATE TABLE recurring_debt_payments (
    id INTEGER PRIMARY KEY,
    debt_account_id INTEGER NOT NULL FOREIGN KEY,
    payoff_plan_id INTEGER FOREIGN KEY (nullable),
    
    -- Payment pattern
    scheduled_date_of_month INTEGER (1-31, NULL for "last day"),
    amount DECIMAL(12, 2) NOT NULL,
    frequency ENUM('monthly', 'biweekly', 'weekly') DEFAULT 'monthly',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_auto_confirm BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    last_confirmed_at TIMESTAMP (nullable),
    last_executed_at TIMESTAMP (nullable),
    
    -- Metadata
    created_from_transaction_id INTEGER FOREIGN KEY (nullable, audit trail),
    
    INDEX (debt_account_id, is_active),
    INDEX (scheduled_date_of_month, is_active)
);
```

**Why this structure:**
- Decoupled from individual ledger entries (can create multiple drafts from one recurring pattern)
- `is_auto_confirm` reserved for future (user can opt-in to auto-confirm if they want zero-friction)
- `payoff_plan_id` link enables amount suggestions
- `created_from_transaction_id` provides audit trail

#### 3. `checking_transaction_links` (NEW)

```sql
CREATE TABLE checking_transaction_links (
    id INTEGER PRIMARY KEY,
    checking_transaction_id INTEGER NOT NULL FOREIGN KEY,
    debt_ledger_entry_id INTEGER NOT NULL FOREIGN KEY,
    
    -- Visual indicator
    link_indicator ENUM('payment_to_card', 'charge_from_card') NOT NULL,
    
    -- Metadata
    created_at TIMESTAMP,
    user_confirmed_at TIMESTAMP,
    
    UNIQUE (checking_transaction_id, debt_ledger_entry_id),
    INDEX (checking_transaction_id),
    INDEX (debt_ledger_entry_id)
);
```

**Why separate table:**
- Checking transaction (accounts for money leaving checking)
- Debt ledger entry (accounts for payment against debt)
- Link is explicit, not implicit
- Enables reversal/unlinking without data loss

#### 4. `historian_entries` (EXPAND existing table)

```sql
-- Add columns to existing historian table
ALTER TABLE historian_entries ADD COLUMN (
    event_category ENUM(
        'balance_correction',
        'apr_correction', 
        'payment_timing_slippage',
        'payment_amount_variance',
        'charge_observation',
        'interest_discrepancy',
        'late_fee_trigger'
    ),
    
    debt_account_id INTEGER FOREIGN KEY (nullable),
    payoff_plan_id INTEGER FOREIGN KEY (nullable),
    
    -- Variance data (for adaptive learning)
    expected_value DECIMAL(12, 2) (nullable),
    actual_value DECIMAL(12, 2) (nullable),
    variance_pct DECIMAL(5, 2) (nullable),
    
    -- Rich context
    context_json JSON (nullable, structured data),
    
    INDEX (event_category, debt_account_id),
    INDEX (debt_account_id, created_at)
);
```

**Why this expansion:**
- Historian becomes queryable by event type (not just yes/no logging)
- Supports variance tracking for adaptive learning
- Rich context enables Distance Traveled to reference specific corrections
- Enables future "Learn from this card's patterns" ML features

#### 5. Modify `checking_transactions` (existing)

```sql
-- Add column to existing table
ALTER TABLE checking_transactions ADD COLUMN (
    linked_debt_entry_id INTEGER FOREIGN KEY (nullable)
);

-- This is redundant with checking_transaction_links but improves query performance
-- for the common case: "show me all checking transactions linked to debt payments"
```

---

## Build Sequence

### Phase A: Data Layer (2-3 days)

**Goal:** Schema complete, migrations tested, no UI yet.

**Tasks:**
1. Create migration script `migration_001_debt_reconciliation_schema.py`
   - All five table/column changes above
   - Backfill logic for existing debt accounts (optional: mark all transactions as `source_type='imported'` if they came from CSV)
   - Rollback script tested
   - Location: `app/migrations/`

2. Update SQLAlchemy models in `models.py`
   - `DebtLedgerEntry` class (replaces generic transaction for debt accounts)
   - `RecurringDebtPayment` class
   - `CheckingTransactionLink` class
   - Expand `HistorianEntry` class
   - Add relationships (debt account → ledger entries, recurring payments, etc.)

3. Update database schema version
   - Increment `SCHEMA_VERSION` in `server.py` to trigger migration at next app launch
   - smoke_test.py updated to verify new tables exist

4. Write query helpers in `server.py`
   - `getDebtLedgerForAccount(account_id, start_date, end_date)` → returns entries grouped by type
   - `getRecurringPaymentsDue(date_range)` → returns active recurring payments due in range
   - `getCheckingTransactionLink(checking_txn_id)` → returns linked debt entry (or None)
   - `logHistorianEvent(event_category, debt_account_id, expected, actual, context)` → atomic insert
   - `getPayoffPlanSuggestedAmount(debt_account_id, target_date)` → queries payoff plan for suggested amount

5. Write integration tests
   - Create test fixtures (test debt account, checking account, payoff plan)
   - Test linking (checking txn → debt entry)
   - Test recurring payment query (due dates, active/inactive)
   - Test historian queries (variance by card, date range)
   - Location: `tests/test_debt_reconciliation_data.py`

**Definition of Done:**
- [ ] All tables created and indexed
- [ ] SQLAlchemy models compile without error
- [ ] Migration runs forward and backward without data loss
- [ ] All query helpers tested with fixtures
- [ ] SCHEMA_VERSION incremented
- [ ] Smoke tests pass

---

### Phase B: Debt Ledger UI (3-4 days)

**Goal:** User can manually enter charges/payments in debt account ledger.

**Tasks:**
1. Update debt account ledger rendering (`_debtLedgerRowHTML()` in `app.js`)
   - Replace generic "Transaction" heading with debt-specific verbs
   - Render columns: Date | Description | Charge | Payment | Balance | Link Indicator (💳)
   - "Charged $600 on Capital One" instead of "Transaction: +$600"
   - "Payment $500 to Capital One" (shows link indicator if linked to checking)
   - Running balance column updates dynamically (sum of charges - payments + interest)

2. Add "+ Charge" and "+ Payment" buttons to debt ledger header
   - Buttons trigger inline expansion (per Pamphlet Standard)
   - Charge form: Date | Merchant | Category | Amount | Description | [Add]
   - Payment form: Date | Amount | Description | [Link to checking? Y/N] | [Save as recurring?] | [Add]

3. Implement inline "Add Charge" expansion
   - Form fields expand below button
   - Date field defaults to today
   - Category dropdown (preload from existing categories, allow custom)
   - Merchant text field
   - Amount field (currency input)
   - Save → inserts to `debt_ledger_entries` with `source_type='manual'`
   - Error handling: validate amount > 0, date is reasonable, etc.
   - Success feedback: row appears in ledger, count badge updates

4. Implement inline "Add Payment" expansion
   - Form fields expand below button
   - Date field defaults to today
   - Amount field (currency input)
   - Checkbox: "Link to a checking transaction?"
     - If checked → dropdown shows recent transfers to this creditor (auto-match by creditor name)
     - User selects checking transaction
     - Creates entry in `checking_transaction_links` table
   - Checkbox: "Save as recurring?"
     - If checked → opens sub-form for recurring details (frequency, date of month)
   - Save → inserts to `debt_ledger_entries` + optionally `recurring_debt_payments` + optionally `checking_transaction_links`

5. Update checking ledger rendering
   - Add visual indicator (💳 card icon) to linked transactions
   - On hover/expand, show linked debt account & amount
   - Example: "Transfer to Capital One $500 💳 linked to Capital One payment"
   - Clicking indicator scrolls/highlights the linked debt entry

6. Implement "Unlink" UX
   - On debt or checking ledger row with link, add small "unlink" button (⛓️‍💥)
   - Unlink removes `checking_transaction_links` entry, keeps both ledger entries
   - Historian logs: "User unlinked checking transaction X from debt payment Y"

**Definition of Done:**
- [ ] Debt ledger renders with semantic verbs (Charged/Payment/Interest)
- [ ] "+ Charge" button adds manual charge entry
- [ ] "+ Payment" button adds manual payment entry
- [ ] Link to checking transaction UI works (dropdown, selection, indicator)
- [ ] Save as recurring checkbox appears and collects data
- [ ] Checking ledger shows 💳 indicator on linked transactions
- [ ] Unlink works without data loss
- [ ] All edits trigger running balance recalculation
- [ ] Error messages are clear and friendly

---

### Phase C: Recurring Payment Drafts (3-4 days)

**Goal:** System generates draft entries, user confirms/edits them.

**Tasks:**
1. Write scheduler in `server.py`
   - New cron job / scheduled task (runs daily or on-demand): `generateRecurringPaymentDrafts()`
   - Query all active `recurring_debt_payments` where `scheduled_date_of_month` is 3-5 days away
   - For each: generate draft `debt_ledger_entry` with `source_type='draft'`, `linked_recurring_payment_id` reference
   - Insert to database (marked as draft, not executed)
   - Return list of new drafts for frontend notification

2. Add "Pending Drafts" indicator to UI
   - Dashboard or Debt page shows badge: "3 payments pending confirmation"
   - Click → expands to show all pending drafts
   - Alternatively: notification center alert (per existing Groundwork pattern)

3. Implement draft confirmation modal
   - Shows: "**$735 payment due to Capital One on Aug 15**"
   - Sub-text: "This is the suggested amount from your payoff plan."
   - User options:
     - "Confirm" (one-tap, locks in amount, sets payment date)
     - "Edit amount" (inline number field, user changes to $500 or $900)
     - "Edit date" (date picker, user shifts to Aug 20 if needed)
     - "Skip this month" (marks recurring as paused, no entry created)
     - "Cancel" (closes modal, draft remains pending)
   - On confirm/edit: draft becomes real entry in `debt_ledger_entries`, logs to historian

4. Integrate payoff plan suggestion
   - When generating draft, query `getPayoffPlanSuggestedAmount(debt_account_id, target_date)`
   - Pre-fill draft amount with suggested amount (not last-month's actual)
   - Display: "Suggested: $735 (from your payoff plan)"
   - This ensures every draft references the plan, even if user edited last month

5. Historian logging for draft actions
   - On confirm: log `event_category='payment_confirmed'`, `expected_value=735`, `actual_value=735` (or edited amount)
   - On edit: log variance, e.g., `variance_pct=-32%` if user paid $500 instead of $735
   - On skip: log `event_category='payment_skipped'`, context includes reason (if user enters one)
   - All logged with `debt_account_id` and `recurring_payment_id` for traceability

6. Update debt page to show recurring pattern status
   - Section: "Recurring Payments"
   - Table: Card | Amount | Frequency | Next Due | Status (Active/Paused)
   - User can edit or delete recurring patterns from here
   - On delete: mark `is_active=FALSE`, log to historian

**Definition of Done:**
- [ ] Daily scheduler generates drafts correctly
- [ ] Draft confirmation modal renders with payoff plan suggestion
- [ ] User can confirm/edit/skip drafts
- [ ] Historian logs all draft actions with variance
- [ ] Pending drafts badge/notification appears
- [ ] Recurring payments section on debt page shows pattern & next due date
- [ ] Edits feed back into payoff plan recalculation (see Phase E)

---

### Phase D: Checking Transaction Linking (2-3 days)

**Goal:** User can tag a checking payment as payment to a debt account (one-tap, no re-entry).

**Tasks:**
1. Update checking ledger for debt-specific linking
   - When user is viewing a checking account, add subtle affordance to link transactions
   - For transactions that look like payments (description contains creditor name, amount is round, etc.), offer quick-link suggestion
   - Example: "Transfer to Capital One $500" → "Link this to a debt payment?"

2. Implement link flow
   - User clicks "Link to debt" button on checking transaction
   - Modal appears: "Link this payment to a debt account"
   - Dropdown: list all debt accounts (account name + current balance)
   - User selects account
   - Creates entry in `checking_transaction_links` table
   - Also creates corresponding `debt_ledger_entry` with type='payment', amount, date
   - Sets `linked_checking_transaction_id` on the debt entry
   - Visual confirmation: 💳 indicator appears on checking transaction, linked debt entry shows link icon

3. Bi-directional link visibility
   - From checking ledger: click 💳 indicator → scroll to and highlight corresponding debt entry
   - From debt ledger: click link icon → scroll to and highlight corresponding checking entry
   - Hover shows: "Linked to [account] checking transfer on [date]"

4. Unlinking
   - User can "unlink" from either side (checking or debt)
   - Unlink removes `checking_transaction_links` entry
   - Keeps both ledger entries (checking shows the transfer out, debt shows the payment)
   - Historian logs: "User unlinked checking transfer X from debt payment Y"

5. Recurring link from a single linked payment
   - Once a checking payment is linked to a debt payment, user can "Save this pattern as recurring"
   - This creates `recurring_debt_payments` entry with:
     - Frequency (monthly, biweekly, etc.)
     - Scheduled date of month
     - Initial amount from this payment
     - `created_from_transaction_id` = this checking transaction
   - Recurring payment drafts then auto-generate each month

**Definition of Done:**
- [ ] Checking ledger shows link affordance for likely debt payments
- [ ] Link flow allows user to select debt account
- [ ] Link creates entries in both ledgers (checking + debt)
- [ ] 💳 indicator appears on linked checking transaction
- [ ] Bi-directional navigation works (checking ↔ debt)
- [ ] Unlink removes link without deleting ledger entries
- [ ] "Save as recurring" creates recurring payment pattern
- [ ] Historian logs all link/unlink actions

---

### Phase E: Payoff Plan Integration (2-3 days)

**Goal:** Recurring payment drafts read payoff plan; edits update plan expectations.

**Tasks:**
1. Query payoff plan from ledger data
   - Function `getPayoffPlanSuggestedAmount(debt_account_id, target_date)` (already written in Phase A)
   - Queries `debt_payoff_plans` table for the account
   - Looks up suggested payment amount for target month
   - Returns amount + plan metadata (total payoff months, interest saved, etc.)

2. Pre-fill draft with suggested amount
   - When draft is generated (Phase C), query suggested amount from payoff plan
   - Show in modal: "**$735 payment due Capital One on Aug 15** — *this is the suggested amount from your payoff plan*"
   - User sees the connection: the app knows my plan, and it's suggesting what I said I'd pay

3. Handle payment variance
   - If user confirms different amount: log to historian
   - Event: `event_category='payment_amount_variance'`
   - Fields: `expected_value=735`, `actual_value=450`, `variance_pct=-39%`, `context={'reason': 'tighter month', ...}`
   - This historian entry feeds into Distance Traveled narrative (see Phase F)

4. Recalculate payoff based on actual payments
   - After each payment confirmation, trigger payoff plan recalculation
   - If user paid less than plan: payoff date may shift
   - If user paid more: payoff date accelerates
   - Update payoff plan's `estimated_payoff_date` and `estimated_total_interest`
   - Distance Traveled should reference this: "You've paid $X toward Capital One; your payoff date is now [date], saving $Y in interest vs. the original plan"

5. Show plan compliance in debt page
   - New section on debt page: "Payoff Plan Status"
   - Display: "Plan calls for $735/month. You've paid on-time X months, below-plan Y months, above-plan Z months."
   - Average payment amount vs. plan amount
   - Projected payoff date vs. original plan date
   - Interest saved vs. worst-case scenario

**Definition of Done:**
- [ ] Recurring payment draft pre-fills with payoff plan suggestion
- [ ] Suggestion is clearly labeled as coming from the plan
- [ ] Payment variance is logged to historian
- [ ] Payoff plan recalculates after each payment
- [ ] Payoff Plan Status section shows compliance
- [ ] Distance Traveled references actual vs. planned payments

---

### Phase F: Narrative Integration (3-4 days)

**Goal:** Distance Traveled report reflects plan vs. actual behavior, showing user is on-track (or not).

**Tasks:**
1. Expand Distance Traveled data source
   - Distance Traveled already reads debt progress; expand to include historian variance data
   - New query: `getPaymentVarianceForAccount(debt_account_id)` → returns historian entries for that account
   - Compute: average variance % over last 12 months, trend (getting better? worse?)
   - Compute: months on-plan, months under-plan, months over-plan

2. Add compliance narrative to Distance Traveled
   - Section title: "[Account name] Payoff Plan"
   - New narrative layer:
     - **On-track case:** "You're keeping pace with your plan. You've paid $X toward Capital One, right on schedule. At this rate, you'll be debt-free in [date], saving $Y in interest."
     - **Under-plan case:** "You're paying below your plan. You've paid $X instead of the planned $Y. Your payoff date has shifted to [new date]. If you can increase payments by $Z/month, you'll get back on track."
     - **Over-plan case:** "You're paying faster than planned. You've paid $X, ahead of schedule by $Y. At this accelerated rate, you'll be debt-free by [early date], saving $Z in interest."
     - **Highly variable case:** "Your payments vary month-to-month. You've averaged $A but range from $B–$C. This variance adds [X days] to your payoff timeline. Consistency would help."

3. Surface late payments & fees
   - If historian logs a late fee, include in narrative:
     - "Late payments in May and July added $X in fees. On-time payments would save you $X/year."
   - Track payment-timing patterns: "You typically pay 5 days late. This triggers late fees (~$X/month). Autopay or calendar alerts might help."

4. Show interest saved due to faster payoff
   - Query: original payoff date vs. actual payoff date
   - Compute: interest saved by accelerated/on-time vs. worst-case
   - Include in narrative: "By keeping pace with your plan, you're saving $X in interest vs. if you only paid minimums."

5. Offer micro-actions
   - "Want to accelerate payoff? Increasing to $850/month gets you debt-free by [3 months earlier]."
   - "Need flexibility? We can adjust your plan. Current: $735/month for 24 months. Alternative: $600/month for 28 months."
   - These aren't imposed; they're options the user can explore.

6. LLM gate integration
   - All Distance Traveled narrative goes through LLM gate (already built in Phase 1)
   - Gate verifies: every dollar figure comes from ledger/plan/historian data
   - No fabricated interest rates, made-up compliance scores, invented trends
   - Historian records if gate flags a fabrication ("LLM suggested interest saved of $X, but ledger showed $Y")

**Definition of Done:**
- [ ] Distance Traveled queries historian variance data
- [ ] Narrative includes on-track/under-plan/over-plan cases
- [ ] Late payments and fees are surfaced
- [ ] Interest saved is calculated and included
- [ ] Micro-action suggestions appear (not forced)
- [ ] All narrative goes through LLM gate
- [ ] No fabricated figures; all sourced from ledger/historian

---

### Phase G: Testing & Polish (2-3 days)

**Goal:** Feature is robust, UX is fluid, edge cases are handled.

**Tasks:**
1. Write comprehensive test suite
   - Unit tests: ledger entry creation, linking, recurring generation (see Phase A tests)
   - Integration tests: full flow (charge → payment → link → recurring → draft → confirm)
   - Edge cases:
     - User tries to link same transaction twice (prevent)
     - User edits a linked payment (unlink, re-link?)
     - User deletes checking transaction (cascade to debt?)
     - Recurring payment for account with $0 balance (allow, treat as charge offset)
     - Draft generated for a deleted recurring payment (skip)
     - Multiple recurring patterns for same account (all should work)
   - Location: `tests/test_debt_reconciliation_integration.py`

2. Smoke test updates
   - Add checks: recurring payment tables exist and have correct indices
   - Add check: historian entries log correctly on payment confirm
   - Add check: payoff plan recalculates after payment
   - Update smoke_test.py

3. UX polish
   - Button styling: "+ Charge" and "+ Payment" match Groundwork's Pamphlet Standard
   - Form validation: clear error messages if user enters invalid data
   - Confirmation feedback: toast or badge update when entry is saved
   - Undo: can user undo a payment entry? (Yes, but logs to historian as "User retracted payment entry")
   - Mobile: test linking and recurring on mobile device (if applicable)

4. Historian query performance
   - Ensure queries on historian are indexed: (debt_account_id, created_at), (event_category, debt_account_id)
   - Large-account test: simulate account with 100+ ledger entries, 24+ recurring patterns
   - Verify Distance Traveled queries complete in < 1s

5. Documentation
   - Write user-facing help text: "How to link a checking payment to your debt"
   - Write developer docs: historian event types, payoff plan integration
   - Add screenshots / GIFs to in-app help

6. Beta tester feedback cycle
   - Roll to canary testers (1-2 most engaged)
   - Collect feedback on: UX friction, linking confusion, recurring reliability
   - Fix critical issues before wider rollout
   - Watch miss-log for historian fabrications

**Definition of Done:**
- [ ] All integration tests pass
- [ ] Smoke tests updated and passing
- [ ] UX is fluid (no confusing buttons, clear confirmations)
- [ ] Edge cases handled gracefully
- [ ] Performance verified on large accounts
- [ ] Help text written and clear
- [ ] Canary rollout successful

---

## Module-by-Module Specification

### `models.py` additions

```python
class DebtLedgerEntry(db.Model):
    """Semantic ledger entry for debt accounts (charge/payment/interest/fee)."""
    __tablename__ = 'debt_ledger_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    debt_account_id = db.Column(db.Integer, db.ForeignKey('debt_accounts.id'), nullable=False)
    entry_type = db.Column(db.Enum('charge', 'payment', 'interest', 'fee'), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    entry_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(256))
    category = db.Column(db.String(64))
    merchant = db.Column(db.String(128))
    
    linked_checking_transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    linked_payoff_plan_id = db.Column(db.Integer, db.ForeignKey('debt_payoff_plans.id'), nullable=True)
    
    source_type = db.Column(db.Enum('manual', 'imported', 'inferred'), nullable=False, default='manual')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    debt_account = db.relationship('DebtAccount', backref='ledger_entries')
    linked_checking_transaction = db.relationship('Transaction')
    linked_payoff_plan = db.relationship('DebtPayoffPlan')
    
    def running_balance_after(self):
        """Calculate account balance after this entry."""
        # Sum all charges (positive) - payments (negative) + interest (positive)
        # from account inception up to and including this entry
        pass


class RecurringDebtPayment(db.Model):
    """Pattern for recurring debt payment (e.g., "$735 every 15th of month")."""
    __tablename__ = 'recurring_debt_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    debt_account_id = db.Column(db.Integer, db.ForeignKey('debt_accounts.id'), nullable=False)
    payoff_plan_id = db.Column(db.Integer, db.ForeignKey('debt_payoff_plans.id'), nullable=True)
    
    scheduled_date_of_month = db.Column(db.Integer)  # 1-31, nullable for "last day"
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    frequency = db.Column(db.Enum('monthly', 'biweekly', 'weekly'), default='monthly')
    
    is_active = db.Column(db.Boolean, default=True)
    is_auto_confirm = db.Column(db.Boolean, default=False)  # Future: user opts into auto-confirm
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_confirmed_at = db.Column(db.DateTime, nullable=True)
    last_executed_at = db.Column(db.DateTime, nullable=True)
    
    created_from_transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    
    # Relationships
    debt_account = db.relationship('DebtAccount', backref='recurring_payments')
    payoff_plan = db.relationship('DebtPayoffPlan')


class CheckingTransactionLink(db.Model):
    """Explicit link between a checking payment and a debt payment."""
    __tablename__ = 'checking_transaction_links'
    
    id = db.Column(db.Integer, primary_key=True)
    checking_transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    debt_ledger_entry_id = db.Column(db.Integer, db.ForeignKey('debt_ledger_entries.id'), nullable=False)
    
    link_indicator = db.Column(db.Enum('payment_to_card', 'charge_from_card'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_confirmed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    checking_transaction = db.relationship('Transaction', backref='debt_links')
    debt_entry = db.relationship('DebtLedgerEntry', backref='checking_links')
    
    __table_args__ = (
        db.UniqueConstraint('checking_transaction_id', 'debt_ledger_entry_id', name='unique_checking_debt_link'),
    )
```

### `server.py` new endpoints & helpers

```python
# === Queries ===

def getDebtLedgerForAccount(account_id, start_date=None, end_date=None):
    """Return all debt ledger entries for an account, grouped by type."""
    query = DebtLedgerEntry.query.filter_by(debt_account_id=account_id)
    if start_date:
        query = query.filter(DebtLedgerEntry.entry_date >= start_date)
    if end_date:
        query = query.filter(DebtLedgerEntry.entry_date <= end_date)
    return query.order_by(DebtLedgerEntry.entry_date.desc()).all()


def getRecurringPaymentsDue(date_range_start, date_range_end):
    """Return active recurring payments due between two dates."""
    recurring = RecurringDebtPayment.query.filter_by(is_active=True).all()
    due = []
    for r in recurring:
        due_dates = calculateRecurringDates(r, date_range_start, date_range_end)
        for due_date in due_dates:
            due.append({'recurring': r, 'due_date': due_date})
    return due


def generateRecurringPaymentDrafts():
    """Create draft ledger entries for recurring payments due in next 3-5 days."""
    now = datetime.now().date()
    soon = now + timedelta(days=5)
    
    due_payments = getRecurringPaymentsDue(now, soon)
    drafts = []
    
    for item in due_payments:
        recurring = item['recurring']
        due_date = item['due_date']
        
        # Get suggested amount from payoff plan (if linked)
        suggested_amount = recurring.amount  # Default to recurring amount
        if recurring.payoff_plan_id:
            plan = DebtPayoffPlan.query.get(recurring.payoff_plan_id)
            suggested_amount = plan.suggested_amount_for_date(due_date) or recurring.amount
        
        # Create draft entry
        draft = DebtLedgerEntry(
            debt_account_id=recurring.debt_account_id,
            entry_type='payment',
            amount=suggested_amount,
            entry_date=due_date,
            description=f"Recurring payment (draft)",
            source_type='draft',
            linked_payoff_plan_id=recurring.payoff_plan_id
        )
        db.session.add(draft)
        drafts.append(draft)
    
    db.session.commit()
    return drafts


def confirmRecurringPaymentDraft(draft_id, confirmed_amount=None, confirmed_date=None):
    """User confirms a draft payment; optionally edits amount or date."""
    draft = DebtLedgerEntry.query.get(draft_id)
    assert draft.source_type == 'draft', "Not a draft entry"
    
    original_amount = draft.amount
    original_date = draft.entry_date
    
    # User edits
    final_amount = confirmed_amount if confirmed_amount else original_amount
    final_date = confirmed_date if confirmed_date else original_date
    
    # Update draft to real entry
    draft.source_type = 'manual'  # User-confirmed
    draft.amount = final_amount
    draft.entry_date = final_date
    
    db.session.commit()
    
    # Log to historian
    variance_pct = ((final_amount - original_amount) / original_amount * 100) if original_amount else 0
    logHistorianEvent(
        event_category='payment_amount_variance',
        debt_account_id=draft.debt_account_id,
        expected_value=float(original_amount),
        actual_value=float(final_amount),
        variance_pct=float(variance_pct),
        context={'original_date': str(original_date), 'final_date': str(final_date)}
    )
    
    # Recalculate payoff plan
    recalculatePayoffPlan(draft.debt_account_id)
    
    return draft


def logHistorianEvent(event_category, debt_account_id, expected_value=None, actual_value=None, 
                      variance_pct=None, context=None):
    """Log an event to historian for learning & auditing."""
    entry = HistorianEntry(
        event_category=event_category,
        debt_account_id=debt_account_id,
        expected_value=expected_value,
        actual_value=actual_value,
        variance_pct=variance_pct,
        context_json=json.dumps(context) if context else None,
        created_at=datetime.utcnow()
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def getPayoffPlanSuggestedAmount(debt_account_id, target_date):
    """Query payoff plan for suggested payment amount on a given date."""
    plan = DebtPayoffPlan.query.filter_by(debt_account_id=debt_account_id, is_active=True).first()
    if not plan:
        return None
    
    return plan.suggested_amount_for_date(target_date)


# === API Routes ===

@app.route('/api/debt/<int:account_id>/ledger', methods=['GET'])
def getDebtLedger(account_id):
    """Return all debt ledger entries for account."""
    entries = getDebtLedgerForAccount(account_id)
    return jsonify([e.to_dict() for e in entries])


@app.route('/api/debt/<int:account_id>/ledger/entry', methods=['POST'])
def createDebtLedgerEntry(account_id):
    """Create a new charge or payment in debt ledger."""
    data = request.get_json()
    
    entry = DebtLedgerEntry(
        debt_account_id=account_id,
        entry_type=data.get('entry_type'),  # 'charge' or 'payment'
        amount=data.get('amount'),
        entry_date=datetime.fromisoformat(data.get('entry_date')),
        description=data.get('description'),
        category=data.get('category'),
        merchant=data.get('merchant'),
        source_type='manual'
    )
    
    # Handle checking transaction link
    if data.get('linked_checking_transaction_id'):
        link = CheckingTransactionLink(
            checking_transaction_id=data.get('linked_checking_transaction_id'),
            debt_ledger_entry_id=entry.id,
            link_indicator='payment_to_card' if entry.entry_type == 'payment' else 'charge_from_card',
            user_confirmed_at=datetime.utcnow()
        )
        db.session.add(link)
    
    db.session.add(entry)
    db.session.commit()
    
    return jsonify(entry.to_dict()), 201


@app.route('/api/recurring-payments/due', methods=['GET'])
def getRecurringDue():
    """Return pending recurring payment drafts."""
    now = datetime.now().date()
    soon = now + timedelta(days=5)
    due = getRecurringPaymentsDue(now, soon)
    return jsonify([{'recurring': r['recurring'].to_dict(), 'due_date': str(r['due_date'])} for r in due])


@app.route('/api/recurring-payments/<int:draft_id>/confirm', methods=['POST'])
def confirmPayment(draft_id):
    """User confirms a recurring payment draft (optionally editing amount/date)."""
    data = request.get_json()
    draft = confirmRecurringPaymentDraft(
        draft_id,
        confirmed_amount=data.get('amount'),
        confirmed_date=datetime.fromisoformat(data.get('date')) if data.get('date') else None
    )
    return jsonify(draft.to_dict())


@app.route('/api/transactions/<int:txn_id>/link-debt', methods=['POST'])
def linkCheckingTxnToDebt(txn_id):
    """Link a checking transaction to a debt payment."""
    data = request.get_json()
    
    # Create debt ledger entry for the payment
    debt_entry = DebtLedgerEntry(
        debt_account_id=data.get('debt_account_id'),
        entry_type='payment',
        amount=data.get('amount'),
        entry_date=datetime.fromisoformat(data.get('entry_date')),
        source_type='manual',
        linked_checking_transaction_id=txn_id
    )
    db.session.add(debt_entry)
    db.session.flush()  # Get the ID
    
    # Create link
    link = CheckingTransactionLink(
        checking_transaction_id=txn_id,
        debt_ledger_entry_id=debt_entry.id,
        link_indicator='payment_to_card',
        user_confirmed_at=datetime.utcnow()
    )
    db.session.add(link)
    db.session.commit()
    
    return jsonify(debt_entry.to_dict()), 201
```

---

## Integration Points

### Phase 1 (Voice Gate) integration

- Distance Traveled narrative for debt reconciliation goes through LLM gate
- Gate verifies: all dollar figures come from ledger/historian, no fabricated numbers
- Historian logs if gate flags fabrication in distance-traveled narrative

### Phase 4 (PDF Extraction) integration

- PDF extraction populates debt ledger (like CSV import)
- Marks entries as `source_type='imported'` (not 'manual')
- Imported entries can be linked to recurring payments (same UX)
- No conflict: manual + imported entries coexist in same ledger

### Existing systems

- **Payoff plan:** already exists, queries via `getPayoffPlanSuggestedAmount()`
- **Distance Traveled:** expanded with historian variance data
- **Debt page:** new "Payoff Plan Status" section shows compliance
- **Dashboard:** pending drafts badge appears (or notification center)
- **Ledger:** existing ledger system extended to support debt-specific verbiage

---

## Historian & Learning

### Event Types

```
- payment_confirmed: user confirmed a recurring payment draft
- payment_amount_variance: user edited payment amount (expected vs. actual)
- payment_timing_slippage: user paid late; date variance tracked
- payment_skipped: user skipped a recurring payment month
- balance_correction: user entered actual balance (we estimated X, user corrected to Y)
- apr_correction: user entered different APR than card detail stated
- charge_observation: user manually entered a charge (for pattern learning)
- interest_discrepancy: we calculated interest as X, user later corrected to Y
- late_fee_trigger: late payment triggered a fee
- transaction_linked: user linked a checking payment to debt account
- transaction_unlinked: user unlinked a previously-linked transaction
```

### Learning Goals

Over time, the historian enables:
1. **Behavioral personalization:** "This user tends to pay 5% below plan; adjust expectations"
2. **Systematic bias detection:** "Our interest calculation is consistently 2% high for this card"
3. **Timing patterns:** "User typically pays 3 days late; alert them 5 days before due date"
4. **Variance prediction:** "User's payments average 15% variance; confidence on payoff date is medium"

### Queries for Distance Traveled

```python
def getPaymentComplianceData(debt_account_id, months=12):
    """Return payment compliance metrics for narrative."""
    entries = HistorianEntry.query.filter(
        HistorianEntry.debt_account_id == debt_account_id,
        HistorianEntry.event_category.in_(['payment_confirmed', 'payment_amount_variance']),
        HistorianEntry.created_at >= datetime.utcnow() - timedelta(days=30*months)
    ).all()
    
    on_time = len([e for e in entries if e.variance_pct and abs(e.variance_pct) <= 5])
    under_plan = len([e for e in entries if e.variance_pct and e.variance_pct < -5])
    over_plan = len([e for e in entries if e.variance_pct and e.variance_pct > 5])
    avg_variance = sum([e.variance_pct for e in entries]) / len(entries) if entries else 0
    
    return {
        'on_time': on_time,
        'under_plan': under_plan,
        'over_plan': over_plan,
        'avg_variance_pct': avg_variance,
        'total_payments': len(entries)
    }
```

---

## Narrative Integration

### Distance Traveled expansion

New section in Distance Traveled report:

```
🎯 [Capital One] Payoff Plan

Plan: $735/month for 24 months
Current Status: ON TRACK

You've paid toward Capital One 8 times in the last 12 months:
- On schedule: 6 months ($735)
- Below plan: 2 months ($500, $600)
- Late fees: 0

Estimated payoff: January 2027 (on schedule)
Interest saved by your plan: $731 vs. minimum payments

What's next: Your next suggested payment is $735 on August 15.
If you accelerate to $850/month, you'll be debt-free by November 2026 — saving an extra $120 in interest.
```

### Narrative triggers (LLM-free first pass)

```python
def buildDebtNarrative(debt_account_id):
    """Build deterministic narrative for Distance Traveled."""
    compliance = getPaymentComplianceData(debt_account_id)
    plan = DebtPayoffPlan.query.filter_by(debt_account_id=debt_account_id, is_active=True).first()
    account = DebtAccount.query.get(debt_account_id)
    
    narrative = f"🎯 {account.account_name} Payoff Plan\n"
    narrative += f"Plan: ${plan.monthly_payment:.2f}/month for {plan.months} months\n"
    
    # Status determination (no LLM, deterministic)
    avg_var = compliance['avg_variance_pct']
    if -5 <= avg_var <= 5:
        status = "ON TRACK"
    elif avg_var < -5:
        status = "BELOW PLAN"
    else:
        status = "AHEAD OF SCHEDULE"
    
    narrative += f"Current Status: {status}\n\n"
    
    # Payment history
    narrative += f"You've paid {compliance['total_payments']} times in the last 12 months:\n"
    narrative += f"- On schedule: {compliance['on_time']} months\n"
    narrative += f"- Below plan: {compliance['under_plan']} months\n"
    narrative += f"- Above plan: {compliance['over_plan']} months\n\n"
    
    # Payoff estimate
    payoff_date = plan.estimated_payoff_date
    interest_saved = plan.interest_saved_vs_minimum
    narrative += f"Estimated payoff: {payoff_date.strftime('%B %Y')}\n"
    narrative += f"Interest saved by your plan: ${interest_saved:.2f}\n"
    
    return narrative
```

---

## Testing & Validation

### Test Fixtures (in `conftest.py`)

```python
@pytest.fixture
def test_debt_account():
    """Create a test debt account with payoff plan."""
    account = DebtAccount(
        account_name="Test Capital One",
        current_balance=5000,
        apr=20.0,
        min_payment=150
    )
    db.session.add(account)
    db.session.flush()
    
    payoff_plan = DebtPayoffPlan(
        debt_account_id=account.id,
        monthly_payment=735,
        months=24,
        estimated_payoff_date=datetime.now() + timedelta(days=730)
    )
    db.session.add(payoff_plan)
    db.session.commit()
    
    return account


@pytest.fixture
def test_checking_account():
    """Create a test checking account with transactions."""
    account = CheckingAccount(account_name="Test Checking")
    db.session.add(account)
    db.session.flush()
    
    txn = Transaction(
        account_id=account.id,
        amount=-500,
        description="Transfer to Capital One",
        transaction_date=datetime.now().date()
    )
    db.session.add(txn)
    db.session.commit()
    
    return account


class TestDebtReconciliation:
    """Integration tests for debt reconciliation feature."""
    
    def test_create_debt_charge(self, test_debt_account):
        """User can create a charge in debt ledger."""
        entry = DebtLedgerEntry(
            debt_account_id=test_debt_account.id,
            entry_type='charge',
            amount=600,
            entry_date=datetime.now().date(),
            description="Costco",
            source_type='manual'
        )
        db.session.add(entry)
        db.session.commit()
        
        assert entry.id is not None
        assert entry.entry_type == 'charge'
    
    def test_link_checking_to_debt(self, test_debt_account, test_checking_account):
        """User can link a checking payment to a debt account."""
        checking_txn = Transaction.query.first()
        
        debt_entry = DebtLedgerEntry(
            debt_account_id=test_debt_account.id,
            entry_type='payment',
            amount=500,
            entry_date=datetime.now().date(),
            linked_checking_transaction_id=checking_txn.id,
            source_type='manual'
        )
        db.session.add(debt_entry)
        db.session.flush()
        
        link = CheckingTransactionLink(
            checking_transaction_id=checking_txn.id,
            debt_ledger_entry_id=debt_entry.id,
            link_indicator='payment_to_card',
            user_confirmed_at=datetime.utcnow()
        )
        db.session.add(link)
        db.session.commit()
        
        # Verify link exists
        found_link = CheckingTransactionLink.query.first()
        assert found_link is not None
        assert found_link.checking_transaction_id == checking_txn.id
        assert found_link.debt_ledger_entry_id == debt_entry.id
    
    def test_create_recurring_payment(self, test_debt_account):
        """User can create a recurring payment pattern."""
        recurring = RecurringDebtPayment(
            debt_account_id=test_debt_account.id,
            payoff_plan_id=test_debt_account.debt_payoff_plans[0].id,
            scheduled_date_of_month=15,
            amount=735,
            frequency='monthly',
            is_active=True
        )
        db.session.add(recurring)
        db.session.commit()
        
        assert recurring.id is not None
        assert recurring.amount == 735
    
    def test_generate_recurring_drafts(self, test_debt_account):
        """System generates drafts for recurring payments due soon."""
        # Create recurring pattern
        recurring = RecurringDebtPayment(
            debt_account_id=test_debt_account.id,
            scheduled_date_of_month=15,
            amount=735,
            frequency='monthly',
            is_active=True
        )
        db.session.add(recurring)
        db.session.commit()
        
        # Generate drafts
        drafts = generateRecurringPaymentDrafts()
        
        # Should have at least one draft
        assert len(drafts) > 0
        draft = drafts[0]
        assert draft.source_type == 'draft'
        assert draft.amount == 735
    
    def test_confirm_payment_with_variance(self, test_debt_account):
        """User confirms a draft payment with different amount; variance is logged."""
        # Create and generate a draft
        recurring = RecurringDebtPayment(
            debt_account_id=test_debt_account.id,
            scheduled_date_of_month=15,
            amount=735,
            frequency='monthly',
            is_active=True
        )
        db.session.add(recurring)
        db.session.commit()
        
        drafts = generateRecurringPaymentDrafts()
        draft = drafts[0]
        
        # User confirms with different amount
        confirmed = confirmRecurringPaymentDraft(draft.id, confirmed_amount=500)
        
        # Check confirmed
        assert confirmed.amount == 500
        assert confirmed.source_type == 'manual'
        
        # Check historian logged variance
        historian = HistorianEntry.query.filter_by(
            debt_account_id=test_debt_account.id,
            event_category='payment_amount_variance'
        ).first()
        assert historian is not None
        assert historian.expected_value == 735
        assert historian.actual_value == 500
```

---

## Phase Gates

### Phase A Gate (Data layer ready)
- [ ] All tables created, indexed, tested
- [ ] SQLAlchemy models compile
- [ ] Query helpers return correct results
- [ ] SCHEMA_VERSION bumped
- [ ] Smoke tests pass
- **Gate: Lock before proceeding to UI work**

### Phase B Gate (Debt ledger UI complete)
- [ ] Debt ledger renders with semantic verbs
- [ ] Manual entry (charge/payment) works
- [ ] Running balance updates correctly
- [ ] No regression in existing debt page
- **Gate: Lock before proceeding to linking**

### Phase C Gate (Recurring drafts work)
- [ ] Scheduler generates drafts
- [ ] Draft modal shows payoff plan suggestion
- [ ] User can confirm/edit/skip
- [ ] Historian logs all actions
- **Gate: Lock before proceeding to payoff plan integration**

### Phase D Gate (Checking linking works)
- [ ] User can link checking → debt
- [ ] Visual indicator (💳) appears
- [ ] Unlink reverses link without data loss
- [ ] Bi-directional navigation works
- **Gate: Lock before integration testing**

### Phase E Gate (Payoff plan integrated)
- [ ] Drafts read payoff plan
- [ ] Variance recalculates payoff date
- [ ] Payoff Plan Status section shows data
- [ ] No regression in existing payoff page
- **Gate: Lock before narrative work**

### Phase F Gate (Narrative works)
- [ ] Distance Traveled includes compliance data
- [ ] On-track/under-plan/over-plan narratives render
- [ ] All figures sourced from ledger/historian
- [ ] LLM gate verifies all numbers
- **Gate: Lock before testing & polish**

### Phase G Gate (Feature ready for canary)
- [ ] All integration tests pass
- [ ] Smoke tests updated & passing
- [ ] UX is fluid, no confusing affordances
- [ ] Help text is clear
- [ ] Canary rollout plan defined
- **Gate: Ready for controlled beta rollout**

---

## Success Metrics (Post-Launch)

Once in canary testing, track:

- **Adoption:** % of testers who set up recurring payments
- **Variance patterns:** Are edits normally ±5%, ±10%, ±30%? Histogram
- **Timing slippage:** Do users typically pay early/late? By how many days?
- **Late fee frequency:** Do recurring users trigger late fees? How often?
- **Historian accuracy:** When we log a correction, is it ever wrong?
- **Narrative comprehension:** Do users understand "on track" vs "below plan"?
- **Friction points:** Which steps cause users to abandon? (Linking? Draft confirm?)

---

## Conclusion

This blueprint defines a complete, testable path from concept to production. The feature closes the reconciliation gap for manual-entry users, makes Groundwork coherent for the 40% who can't auto-import, and creates a production-grade historian for adaptive learning.

**Estimated effort:** 14–18 days of solo development (7 phases, 2–4 days each)  
**Parallel:** Runs alongside Phase 1 (Voice Gate) and Phase 4 (PDF Extraction)  
**Payoff:** Transforms Groundwork from "forecast machine" to "source of truth" for all users

