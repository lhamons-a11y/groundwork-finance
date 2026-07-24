# Groundwork 1.0 Final Foundation Blueprint

**Status:** Complete Build Specification  
**Version:** 1.0  
**Date:** July 24, 2026  
**Purpose:** Final foundational feature set before 1.0 open beta release  
**Scope:** Debt reconciliation feature (primary) + Historian infrastructure completion + Subsystem verification (secondary)

---

## Executive Summary

This is the **final build specification** for Groundwork 1.0. After this work is complete, the product is feature-locked. All future development (1.1+) is either bugfixes or new adaptive features based on real user behavior.

**What ships with 1.0:**
- Complete ledger + budget + payoff planning + net worth tracking (existing)
- PDF/CSV/auto-import (existing)
- LLM gate (existing, harness → shipping)
- **Debt reconciliation feature** (new, this build)
- **Historian infrastructure** (existing, but completing for adaptive learning)
- All eight local reports (existing)
- Trip planning + Flights API (existing)
- EIA energy/fuel tracking (existing)

**What this blueprint covers:**
1. **Debt Reconciliation Feature** (Phases A–G, 14–18 days)
2. **Historian Completion & Readiness** (Phase H, 2–3 days)
3. **Subsystem Verification** (Phase I, 2–3 days)
4. **1.0 Release Readiness** (Phase J, 1 day)

---

## Table of Contents

1. [Build Overview](#build-overview)
2. [Phase A–G: Debt Reconciliation (14–18 days)](#phases-ag-debt-reconciliation)
3. [Phase H: Historian Completion (2–3 days)](#phase-h-historian-completion)
4. [Phase I: Subsystem Verification (2–3 days)](#phase-i-subsystem-verification)
5. [Phase J: Release Readiness (1 day)](#phase-j-release-readiness)
6. [Master Checklist](#master-checklist)
7. [Timeline & Sequence](#timeline--sequence)

---

## Build Overview

### Total Effort Estimate
- **Phase A–G (Debt Reconciliation):** 14–18 days
- **Phase H (Historian):** 2–3 days
- **Phase I (Subsystem Verification):** 2–3 days
- **Phase J (Release Readiness):** 1 day
- **Total:** 19–25 days solo development

### Decision Gate
**After Phase J, 1.0 is release-ready.** Ship to open beta. No more features until 1.1.

---

## Phases A–G: Debt Reconciliation

**See GROUNDWORK_DEBT_RECONCILIATION_BLUEPRINT.md for complete detail.** This section is reference only.

### Phase A: Data Layer (2–3 days)
✅ **Status:** Blueprint complete, ready to build  
**Deliverable:** Five new tables (debt_ledger_entries, recurring_debt_payments, checking_transaction_links, historian expansion)  
**Gate:** All tables created, indexed, tested; SCHEMA_VERSION bumped

### Phase B: Debt Ledger UI (3–4 days)
✅ **Status:** Blueprint complete  
**Deliverable:** Debt ledger rendering with semantic verbs (Charged/Payment/Interest), "+ Charge" and "+ Payment" buttons  
**Gate:** Ledger renders, manual entry works, running balance updates

### Phase C: Recurring Drafts (3–4 days)
✅ **Status:** Blueprint complete  
**Deliverable:** Draft generation scheduler, confirmation modal, payoff plan integration  
**Gate:** Drafts generate 3–5 days before due date, user can confirm/edit/skip

### Phase D: Checking Linking (2–3 days)
✅ **Status:** Blueprint complete  
**Deliverable:** Link affordance, 💳 indicator, bi-directional navigation  
**Gate:** User can link checking payment to debt entry, unlink works without data loss

### Phase E: Payoff Integration (2–3 days)
✅ **Status:** Blueprint complete  
**Deliverable:** Drafts pre-fill with suggested amount from payoff plan, variance logged  
**Gate:** Draft shows plan suggestion, variance feeds historian, payoff recalculates

### Phase F: Narrative Integration (3–4 days)
✅ **Status:** Blueprint complete  
**Deliverable:** Distance Traveled includes compliance, on-track/under-plan/over-plan narratives  
**Gate:** All figures sourced from ledger, LLM gate verifies, no fabrication

### Phase G: Testing & Polish (2–3 days)
✅ **Status:** Blueprint complete  
**Deliverable:** Integration tests, smoke tests, UX polish, canary rollout prep  
**Gate:** All tests pass, UX fluid, ready for beta testing

---

## Phase H: Historian Completion

**Goal:** Historian infrastructure is production-grade and ready for 1.0 release and future adaptive features.

### H.1: Historian Schema Verification (1 day)

**Task:** Verify historian table is built with full adaptive learning support.

**Checklist:**
- [ ] `historian_entries` table has columns:
  - `id`, `created_at`, `updated_at` (basic)
  - `event_category` ENUM with all 11 types (see list below)
  - `debt_account_id`, `payoff_plan_id`, `category_id` (foreign keys for selective queries)
  - `expected_value`, `actual_value`, `variance_pct`, `variance_amount` (for adaptive math)
  - `context_json` (rich structured data)
  - Indices: `(event_category, debt_account_id)`, `(debt_account_id, created_at)`, `(event_category, created_at)`

**Event Category Enum (11 types):**
```
'payment_confirmed'              — Debt reconciliation
'payment_amount_variance'         — Debt reconciliation
'payment_timing_slippage'         — Debt reconciliation
'payment_skipped'                 — Debt reconciliation
'balance_correction'              — Manual correction
'apr_correction'                  — Card terms update
'charge_observation'              — Manual charge entry
'interest_discrepancy'            — Interest calc correction
'late_fee_trigger'                — Late payment event
'categorization_suggestion_confirm'  — Future adaptive: category learning
'categorization_suggestion_reject'   — Future adaptive: category learning
'budget_variance_observed'        — Future adaptive: budget learning
'trip_expense_variance'           — Future adaptive: trip learning
'llm_gate_flag'                   — LLM gate miss-log
```

**Definition of Done:**
- [ ] All 11 event types are defined in schema
- [ ] Foreign key indices optimized for queries on debt_account_id, created_at
- [ ] Sample historian records exist (from debt reconciliation builds)
- [ ] Tests verify historian queries return correct data

### H.2: Historian Query Helpers (1 day)

**Task:** Write all historian query functions needed for 1.0 and future 1.1 adaptive features.

**Functions to implement in `server.py`:**

```python
# Debt reconciliation queries (1.0)
def getPaymentVarianceForAccount(debt_account_id, months=12):
    """Return payment compliance metrics for Distance Traveled narrative."""
    # Returns: on_time count, under_plan count, over_plan count, avg_variance_pct

def getPaymentComplianceConfidence(debt_account_id):
    """Return confidence score (0-100) for payoff plan based on payment history."""
    # Returns: confidence_pct, reasoning (on_time? variable? late_fees?)

def getLatePaymentPattern(debt_account_id):
    """Return late payment frequency and days-late average."""
    # Returns: late_fee_count, avg_days_late, months_affected

# Future adaptive queries (scaffold for 1.1)
def getCategoryPatterns(user_id, merchant_name):
    """Return how user has categorized this merchant in the past."""
    # Returns: most common category, frequency, edge cases

def getBudgetVarianceByCategory(account_id, category_id, months=12):
    """Return budget vs actual for a category over time."""
    # Returns: avg_variance, variance_pct, months_over, months_under

def getTripVarianceByRegion(user_id, region):
    """Return trip spending variance for a region."""
    # Returns: avg_estimated, avg_actual, variance_pct, region-specific adjustment

def getLLMMissLog(user_id, time_range=30):
    """Return all gate flags for this user in date range."""
    # Returns: gate_flag_count_by_type, most_recent_flags

# Helper for all adaptive features
def logHistorianEvent(event_category, debt_account_id=None, category_id=None,
                      expected_value=None, actual_value=None, context=None):
    """Atomic historian insert with all event types supported."""
    # Validates event_category, calculates variance, commits to DB
```

**Definition of Done:**
- [ ] All query functions implemented and tested
- [ ] Queries return correct data for sample historian records
- [ ] Performance verified (queries <500ms even on large accounts)
- [ ] Queries used by Distance Traveled narrative (debt reconciliation)

### H.3: Historian Documentation (0.5 days)

**Task:** Document historian for future developers (especially for 1.1 adaptive features).

**Write in codebase:**
- [ ] `historian/HISTORIAN_GUIDE.md` — How historian works, event types, best practices
- [ ] Comments in `server.py` for each query helper explaining use case and result structure
- [ ] Data model diagram: event types → query → app behavior → historian log

**Definition of Done:**
- [ ] Developer reading guide can understand how to add a new event type
- [ ] Developer reading guide can understand how to write an adaptive feature using historian

---

## Phase I: Subsystem Verification

**Goal:** Verify that all existing subsystems (ledger, budget, payoff, net worth, PDF import, trips, flights, LLM gate, encryption) are still working after debt reconciliation integration.

### I.1: Smoke Test Expansion (1 day)

**Current smoke_test.py has 23 checks.** Expand to 35+ checks covering all subsystems.

**New checks to add:**

```python
# Ledger subsystem
test_ledger_running_balance_correct()
test_ledger_duplicate_detection_fitid()
test_ledger_split_transaction_works()
test_ledger_cross_month_search()

# Budget subsystem
test_budget_allocation_vs_spending()
test_budget_category_overage_detection()
test_budget_monthly_reset()

# Debt payoff subsystem
test_payoff_scheduler_creates_entries()
test_payoff_estimate_calculation()
test_payoff_interest_calculation()

# Net worth subsystem
test_net_worth_calculation(assets, accounts, debts)
test_net_worth_monthly_tracking()

# PDF import
test_pdf_extraction_creates_transactions()
test_pdf_balance_verification_gate()
test_pdf_csv_cross_validation()

# Trips
test_trip_clustering_from_ledger()
test_trip_budget_estimate()

# Flights API
test_flights_api_fetch_and_cache()
test_flights_pricing_display()

# LLM gate
test_llm_gate_r8_number_provenance()
test_llm_gate_inference_detection()
test_llm_gate_fallback_to_structured()

# Encryption
test_export_encryption_argon2()
test_export_decryption_correct_passphrase()
test_export_fails_wrong_passphrase()

# EIA energy tracking
test_eia_api_fetch()
test_eia_price_comparison_to_budget()

# Historian (new)
test_historian_event_insertion()
test_historian_query_by_debt_account()
test_historian_variance_calculation()
```

**Definition of Done:**
- [ ] 35+ smoke tests defined and implemented
- [ ] All tests pass on current codebase
- [ ] Debt reconciliation feature doesn't break any existing tests
- [ ] smoke_test.py runs in < 2 minutes

### I.2: Integration Regression Test (1 day)

**Task:** Run full user journey on beta version to catch integration bugs.

**Test Scenarios:**

1. **Complete Ledger → Debt Flow:**
   - Import CSV file with transactions
   - Manually enter a debt charge
   - Link a checking payment to debt
   - Save as recurring
   - Confirm draft
   - Check Distance Traveled narrative

2. **Payoff Plan → Debt Reconciliation Flow:**
   - Create payoff plan
   - Check next recurring draft
   - Confirm draft with different amount
   - Verify payoff date shifted in Distance Traveled
   - Check historian logged variance

3. **PDF → Debt Reconciliation Flow:**
   - Import PDF statement
   - Verify extracted balance
   - Verify transactions in ledger
   - Create recurring payment
   - Confirm monthly draft
   - Verify narrative reflects imports + manual entry

4. **Net Worth Across All Accounts:**
   - Add checking account with balance
   - Add savings account
   - Add credit card debt
   - Add investment account
   - Verify net worth = assets - debt
   - Update one account, verify net worth recalculates

5. **LLM Gate on Full Narrative:**
   - Run Distance Traveled
   - Gate checks all figures are sourced
   - Gate flags any suspicious inference
   - Narrative still readable even with caveats

**Definition of Done:**
- [ ] All 5 scenarios run without errors
- [ ] No data corruption
- [ ] No silent failures (all errors caught and logged)
- [ ] Performance acceptable (full flow completes in < 10 seconds)

### I.3: Database Integrity Check (0.5 days)

**Task:** Verify database schema is clean and ready for production.

**Checklist:**
- [ ] Run migration forward and backward (tests if rollback works)
- [ ] Verify SCHEMA_VERSION matches app version
- [ ] Verify all foreign keys are correct and indexed
- [ ] Verify no orphaned records (debts without accounts, etc.)
- [ ] Verify data types are consistent
- [ ] Backup/restore cycle works (test encryption restore)

**Definition of Done:**
- [ ] Migration scripts are solid
- [ ] Database can be backed up and restored without data loss
- [ ] Rollback works if needed

---

## Phase J: Release Readiness

**Goal:** Final polish and go/no-go decision for 1.0 open beta release.

### J.1: Version Bump & Changelog (0.25 days)

**Task:** Finalize version and document all changes for release.

**Actions:**
- [ ] Bump version to 1.0.0 (three-place: major.minor.patch)
- [ ] Update `/changelog` page in app with full 1.0 feature list
- [ ] Write release notes for Product Hunt / HackerNews / Reddit
- [ ] Update README.md with 1.0 feature list
- [ ] Update website (groundworkfinance.app) with 1.0 announcement

**Release Notes Template:**
```
Groundwork 1.0 is released.

FEATURES:
- Complete ledger: CSV/OFX/PDF import, manual entry, reconciliation
- Budget tracking with category allocation and alerts
- Debt payoff planning with adaptive narratives
- Net worth tracking: assets + accounts - debt = real wealth
- Debt reconciliation: manual entry, recurring payments, plan-aligned drafts
- Trip planning with historical learning
- Flights API integration
- Auto-import watcher (Downloads folder)
- Export encryption (Argon2/PBKDF2 + AES-GCM)
- EIA energy/fuel cost tracking with trending
- Distance Traveled narrative with LLM + validation gate
- Eight local reports (no cloud, no ads, no data sharing)

WHAT'S DIFFERENT:
- Local LLM (phi3.5 default, Ollama) — nothing leaves your machine
- Validation gate: every number sourced from your data, never fabricated
- Honest narratives: we show you plan vs actual, exogenous factors, net worth progress
- Historian: system learns from your behavior to improve recommendations

REQUIREMENTS:
- Windows 11, macOS (Apple Silicon), or Ubuntu 24.04 LTS
- 8GB RAM minimum (16GB recommended for local LLM)
- Ollama (auto-installs via setup wizard)

This is 1.0. All features are built and tested. We're shipping a finished product.
```

**Definition of Done:**
- [ ] Version bumped to 1.0.0
- [ ] Changelog complete and accurate
- [ ] Release notes written
- [ ] Website updated
- [ ] No uncommitted changes in git

### J.2: Deploy Package & Test (0.5 days)

**Task:** Create release package and test deployment one more time.

**Actions:**
- [ ] Run deploy.bat (verify release builds cleanly)
- [ ] Test on Windows 11 (primary platform)
- [ ] Test on macOS Apple Silicon (if available)
- [ ] Test on Ubuntu 24.04 LTS (if available)
- [ ] Verify Ollama auto-install works
- [ ] Verify app launches and loads demo data
- [ ] Verify all settings accessible
- [ ] Verify export/import works

**Definition of Done:**
- [ ] Deploy.bat produces clean release build
- [ ] App runs on all three platforms
- [ ] No crashes on startup
- [ ] Smoke tests pass

### J.3: Release Decision Gate (0.25 days)

**Task:** Final go/no-go decision before releasing to open beta.

**Checklist:**
- [ ] Phase A–G complete and tested (debt reconciliation)
- [ ] Phase H complete (historian ready)
- [ ] Phase I passing (subsystems verified)
- [ ] Phase J packaging done
- [ ] No critical bugs in current test run
- [ ] Performance acceptable (app responsive, queries < 1s)
- [ ] All smoke tests passing

**Go Decision Criteria:**
- [ ] All boxes checked above
- [ ] You're confident in the product quality
- [ ] Ready to support beta testers with issues

**No-Go Criteria:**
- [ ] Any critical bug discovered
- [ ] Any data corruption risk
- [ ] Any component completely broken
- **If no-go, identify bug, fix, return to Phase G smoke tests, then re-run J.3**

**Definition of Done:**
- Go/no-go decision made
- If go: proceed to open beta announcement

---

## Master Checklist

### Phase A–G (Debt Reconciliation) — 14–18 days
- [ ] **Phase A:** Data layer complete, SCHEMA_VERSION bumped, tests passing
- [ ] **Phase B:** Debt ledger UI complete, semantic verbs rendering
- [ ] **Phase C:** Recurring drafts generating 3–5 days before due date
- [ ] **Phase D:** Checking linking working, 💳 indicator visible
- [ ] **Phase E:** Payoff plan integration complete, variance logged
- [ ] **Phase F:** Distance Traveled narrative includes compliance
- [ ] **Phase G:** All integration tests passing, UX polished

### Phase H (Historian) — 2–3 days
- [ ] Historian schema complete with 11 event types
- [ ] Query helpers implemented and tested
- [ ] Performance verified (queries < 500ms)
- [ ] Documentation written

### Phase I (Subsystem Verification) — 2–3 days
- [ ] Smoke test expanded to 35+ checks, all passing
- [ ] Integration regression tests (5 scenarios) all passing
- [ ] Database integrity verified, migration works
- [ ] No data corruption, no silent failures

### Phase J (Release Readiness) — 1 day
- [ ] Version bumped to 1.0.0
- [ ] Changelog and release notes complete
- [ ] Deploy.bat tested on all platforms
- [ ] Smoke tests passing one final time
- [ ] Go/no-go decision made

---

## Timeline & Sequence

### Recommended Build Order

**Week 1 (Mon–Fri):**
- **Mon:** Phase A (data layer)
- **Tue–Wed:** Phase B (debt ledger UI)
- **Thu:** Phase C (recurring drafts)
- **Fri:** Phase C (continued) + Phase D (checking linking)

**Week 2 (Mon–Fri):**
- **Mon:** Phase D (continued) + Phase E (payoff integration)
- **Tue:** Phase E (continued) + Phase F (narrative)
- **Wed–Thu:** Phase F (continued)
- **Fri:** Phase G (testing & polish)

**Week 3 (Mon–Wed):**
- **Mon:** Phase G (continued) + Phase H.1 (historian schema verify)
- **Tue:** Phase H.2 (historian queries) + Phase H.3 (documentation)
- **Wed:** Phase I.1–I.3 (subsystem verification)

**Week 3 (Thu–Fri):**
- **Thu:** Phase J.1–J.2 (version bump, deploy test)
- **Fri:** Phase J.3 (release decision), then ship

### Parallel Work (If Needed)
- **Smoke test expansion (Phase I.1)** can happen alongside **Phase E–F** to catch integration issues early
- **Documentation (Phase H.3)** can happen while **Phase G testing** runs

### Go-Live Date
**Friday, end of Week 3** — Release to open beta (assuming all gates pass).

---

## Success Criteria for 1.0 Release

### Product Criteria
- [ ] Debt reconciliation feature complete and tested
- [ ] Historian infrastructure production-ready
- [ ] All subsystems passing smoke tests
- [ ] No critical bugs
- [ ] App performs well (< 1s query times, responsive UI)

### Process Criteria
- [ ] Three-place version control observed (1.0.0 tagging)
- [ ] Deploy.bat rollback tested and working
- [ ] Smoke test suite complete and passing
- [ ] Git history clean and documented

### Business Criteria
- [ ] Clear go/no-go decision made
- [ ] Release notes written and accurate
- [ ] Website updated
- [ ] Ready for open beta announcement

---

## Post-1.0: Adaptive Learning Roadmap (Not Part of This Build)

After 1.0 ships and real users start using it, 1.1 will add historian-driven adaptive features:

**1.1 Priority Features (in order):**
1. Category suggestion (user learns taxonomy)
2. Budget variance prediction (system learns spending patterns)
3. Trip spending forecast (system learns by region)
4. Payoff plan confidence (system learns payment reliability)
5. LLM gate improvements (system learns from miss-log)

These are **not** part of 1.0. They wait for real user data to inform design.

---

## Appendix: Key Decisions Locked for 1.0

**These decisions are final and not revisited:**
- Debt reconciliation is the last feature build
- LLM gate uses phi3.5 local default, Ollama primary, Anthropic fallback
- Historian is production-grade but only debt reconciliation actively uses it in 1.0
- Net worth = assets + accounts - debt (deterministic, no estimates)
- Distance Traveled narrative goes through LLM gate (validation locked)
- EIA API provides exogenous context (no user data egress)
- Export encryption uses Argon2/PBKDF2 + AES-GCM
- Three-place version control observed (1.0.0, 1.0.1, 1.1.0, etc.)

---

## Sign-Off

**This blueprint is the final specification for Groundwork 1.0.** After this work is complete, the product is feature-locked for open beta release.

**No new features after this. Bugfixes and polish only.**

