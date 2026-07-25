# Groundwork 1.0 Roadmap — Consolidated

**Status:** Active build plan — supersedes the phase sequencing in the three source blueprints below
**Date:** July 24, 2026
**Sources merged:**
- `GROUNDWORK_DEBT_RECONCILIATION_BLUEPRINT.md` — detailed spec, Phases A–G (still the reference for module-level detail)
- `GROUNDWORK_1_0_WITH_ADAPTIVE_LEARNING.md` — chosen scope: adaptive learning ships in 1.0.0, not deferred to 1.1
- `GROUNDWORK_1_0_FINAL_FOUNDATION_BLUEPRINT.md` — superseded on scope (it defers adaptive learning); its Phase I/J structure is kept
- `GROUNDWORK_LLM_BUILD_PLAN.md` — the pre-existing roadmap this work continues from; its Phases 1–6 are cross-referenced below, not repeated

**Decision locked this session:** the six adaptive-learning features ship **with** 1.0.0, each validated against the real database before release. No 1.1 deferral.

---

## 0. Reality Check — What's Actually Built vs. What the Blueprints Assume

The three blueprints were written as if some infrastructure already existed. It was verified against the live codebase before folding them together. Corrections:

| Blueprint assumption | Actual state |
|---|---|
| "Historian infrastructure (existing, completing for adaptive learning)" | **Not built.** Only an informal one-line "historian auto-write" comment on import (`server.py:4627`). No `historian_entries` table, no event-category enum, no query helpers. Phase H is a **build**, not a verification pass. |
| Debt reconciliation tables | **Not built.** `debt_ledger_entries`, `recurring_debt_payments`, `checking_transaction_links` don't exist. `DebtAccount` and `debt_balance_history` do exist (from LLM Build Plan Phase 4) — reconciliation writes there today, informally. |
| LLM Build Plan Phase 1 (Voice Gate / R8 number-provenance) | **Built.** `_voiceGateCheck` / `_GW_VOICE` live in `app.js`, mirrored in `voice_discipline_test.py`. This is the gate the debt-reconciliation narrative (Phase F below) will route through — no new gate work needed, just a new call site. |
| LLM Build Plan Phase 4 (Capital One PDF extraction) | **Built**, issuer-agnostic (`pdf_statement.py`). Two-destination routing (transactions + summary→reconciliation) exists. |
| LLM Build Plan Phase 2 (Provider UI / RAM detection) | **Likely built** — `local_model`/`ai_provider`/`/api/ai/status`/"Test Connection" all present in `app.js` (11 references). Not re-verified line-by-line; treat as done unless a bug surfaces. |
| LLM Build Plan Phase 5 (trips/EIA) | **Mostly built.** `gas_price.py` (5A) done. `utility_price.py` extends EIA to natural gas/electricity for the budget feature (confirmed built 2026-07-24). **Correction to an earlier version of this table:** trip clustering / "learn from a past trip" (5C) *is* built — `_learnFromPastTrip()` / `tripUpdateBudget()` in `static/js/app.js` (~lines 10044–10474), client-side date-range filter + LLM bucket-classification + engine-summed per-category rates. It was missed on first pass because the check only searched `server.py`; the feature lives in `app.js`. Distance lookup (5E) done differently than spec'd (`trip_distance.py` uses live geocode + haversine, not a bundled table — functionally equivalent, arguably better). **Real gap found instead:** there is no `Trip`/`TripPlan` database table — trips exist only as a single `trip_budget` JSON blob in `AppSetting` (`server.py:3080–3106`). No persisted history across multiple trips. This blocks Phase H2 Feature 3 below as literally spec'd (see new §1 item). Document intake (5D) still unconfirmed. |
| LLM Build Plan Phase 6 (packaging) | **Substantially built** — both `Groundwork_Setup.exe` and `Groundwork_Setup_Offline.exe` exist in `installer_output/`. Code-signing status unverified. |
| smoke_test.py "35+ pytest-style checks" | smoke_test.py is **not pytest** — it's a custom `check(name, condition)` harness against a throwaway temp DB. The blueprint's `test_foo()` naming is illustrative; write new checks in the existing `check(...)` style, not as pytest functions. |

**Net effect:** the debt reconciliation blueprint's Phase A–G estimate (14–18 days) is accurate — that work is genuinely greenfield. Phase H (historian) is bigger than the Final Foundation blueprint implies, because it's a real build. Phases 2/4/5A/6 from the LLM Build Plan are mostly done and don't need to be re-scheduled here.

---

## 1. Build Order

Debt reconciliation is the floor everything else stands on — the historian only becomes real once it has debt-payment events to log, and the adaptive features only become real once the historian has data to learn from. Build strictly in this order:

### Phase A–G: Debt Reconciliation (14–18 days)
**Full spec: `GROUNDWORK_DEBT_RECONCILIATION_BLUEPRINT.md`.** Reference that document for schema, module code, and phase gates. Summary:

| Phase | Deliverable | Est. |
|---|---|---|
| A | `debt_ledger_entries`, `recurring_debt_payments`, `checking_transaction_links` tables + query helpers + migration | 2–3d |
| B | Debt ledger UI — semantic verbs (Charged/Payment/Interest), + Charge / + Payment forms | 3–4d |
| C | Recurring draft scheduler, confirmation modal, payoff-plan pre-fill | 3–4d |
| D | Checking↔debt linking, 💳 indicator, bi-directional nav, unlink | 2–3d |
| E | Payoff plan integration — draft suggestions, variance logging, recalculation | 2–3d |
| F | Distance Traveled narrative expansion (on-track/under-plan/over-plan) — **routes through the existing `_voiceGateCheck`, no new gate needed** | 3–4d |
| G | Integration tests, smoke test additions (in `check()` style, not pytest), UX polish, canary prep | 2–3d |

**Gate:** all seven phase gates in the source blueprint pass before moving to Phase H.

### Phase H1: Historian Infrastructure (2.5–3.5 days)
**This is new construction, not verification** (see §0). Build from `GROUNDWORK_1_0_FINAL_FOUNDATION_BLUEPRINT.md` §Phase H spec:
- `historian_entries` table, all 11 event types, indexed on `(event_category, debt_account_id)` and `(debt_account_id, created_at)`
- Query helpers: `getPaymentVarianceForAccount`, `getPaymentComplianceConfidence`, `getLatePaymentPattern`, plus the four 1.1-scaffold functions (`getCategoryPatterns`, `getBudgetVarianceByCategory`, `getTripVarianceByRegion`, `getLLMMissLog`) — these four get used immediately in Phase H2 below, not deferred
- `logHistorianEvent()` atomic insert helper
- `historian/HISTORIAN_GUIDE.md` documentation
- **NEW — `trip_history` table (+0.5–1 day).** Added because `getTripVarianceByRegion` has nothing to query without it (see §0). Fields: `id`, `trip_label`, `region`, `start_date`, `end_date`, `estimated_total`, `actual_total` (nullable until known), `estimated_by_category` (JSON), `actual_by_category` (JSON, populated when a trip is run through `_learnFromPastTrip`), `learned_basis_json` (snapshot of `_tripLearnedBasis` if applied), `created_at`/`updated_at`. Two write hooks: (1) on trip budget save (`tripUpdateBudget` commit) → insert/update the estimate side; (2) on "Use these numbers" in `_applyTripLearnedBasis()` (`app.js:10186`) → backfill the actual side for that date range. Without this, `region`-grouped variance queries have at most one row and Feature 3 (below) can't produce a real forecast.

### Phase H2: Adaptive Learning Features (8–12 days)
**Full spec: `GROUNDWORK_1_0_WITH_ADAPTIVE_LEARNING.md`.** Six features, each following the same loop: query real data → build adaptive logic → test against the real DB → measure → integrate → smoke-test.

| Feature | Est. | Success criterion |
|---|---|---|
| 1. Category suggestions | 3d | >85% accuracy on 10 most-used merchants |
| 2. Budget variance learning | 2–3d | Adjusted budgets measurably closer to actual |
| 3. Trip spending forecast | 2–3d | Estimate variance < 8% (requires `trip_history` from Phase H1 — see above; will only have real signal once a few trips have been logged through it) |
| 4. Recurring transaction auto-detection | 1–2d | Finds 80% of actual recurring transactions |
| 5. Payoff confidence scoring | 2d | Confidence score matches actual payment reliability (spot-check) |
| 6. LLM gate improvement | 1–2d | Flag rate drops after hardening (pre/post gate-log comparison) |

Each feature ships with its `scripts/explore_*.py` exploratory script per the source blueprint. Trip clustering itself (§0) is confirmed built and needs no rework; Feature 3 depends instead on the new `trip_history` table (Phase H1) having a few logged trips before its variance query has anything real to say — sequence Feature 3 after H1 lands, not blocked on further trip-clustering work.

### Phase I: Subsystem Verification (2–3 days)
Per `GROUNDWORK_1_0_WITH_ADAPTIVE_LEARNING.md` (Final Foundation's version plus the six adaptive smoke checks). Expand `smoke_test.py` using its existing `check(name, condition)` pattern — do not introduce pytest. Cover: ledger, budget, payoff, net worth, PDF import, trips, flights (if in scope), LLM gate, encryption, EIA, historian, and all six adaptive features.

### Phase J: Release Readiness (1.5–2 days)

#### J.0: Personal Data & Secrets Audit (0.5–1 day) — NEW, hard gate before J.1
**Why this exists:** during git setup for this roadmap (2026-07-24), a first pass over the repo root turned up, in minutes, with no dedicated audit: a live EIA API key hardcoded in a config file, a real bank statement PDF, a diagnostic dump with real debt-account balances (TJ Max, Old Navy, Harbor Amazon, Cashback), and an import-rules file naming the developer's actual bank/credit union and employer. None of those are in the shipped app itself (confirmed: `EIA_API_KEY` is correctly pulled via `_get_config_value()` in `server.py`/`gas_price.py`, never hardcoded in source; `home_install_import_rules.json` isn't referenced anywhere in `server.py`, so it isn't loaded or bundled) — but the fact that four separate leaks turned up unprompted in one directory listing means a real pre-ship audit, not a spot-check, is warranted before anything goes out the door.

**Scope — two separate things, both required:**
1. **Source & repo audit:** grep every `.py`/`.js`/`.html`/`.json`/`.txt`/`.md` file that will be **committed and/or built** (not just what's `.gitignore`d) for: hardcoded API keys/tokens/passwords (pattern: long alphanumeric strings assigned to `key=`/`token=`/`api_key=`/`secret=`), real names, real bank/credit union/employer names, real account numbers, and dollar figures that look like actual balances rather than illustrative examples (blueprint docs using `$735`/`$5,000` as spec examples are fine — those never ship; anything in `server.py`, `app.js`, fixtures, or seed/demo data is not).
2. **Built-artifact audit:** after `build.bat` runs, inspect `dist/Groundwork/` — every file `groundwork.spec` bundles via `datas`/`hiddenimports` — to confirm nothing personal got swept in by accident (e.g. a stray root file referenced in a debug path, a leftover fixture with real data). Check the app's demo/seed data (README references first-run demo data) is synthetic, not derived from a real account export.

**Definition of Done:**
- [ ] Full grep sweep of source for hardcoded secrets — zero hits
- [ ] Full sweep of every `.txt`/`.json`/`.md` in the repo for real names/accounts/balances — zero hits in anything committed or built
- [ ] `dist/Groundwork/` contents (post-build) inspected file-by-file against `groundwork.spec`'s `datas` list — confirmed no personal file is bundled
- [ ] Demo/seed data confirmed synthetic
- [ ] `.gitignore` reflects every category of personal data found (update it, don't just delete the file, so it can't silently reappear)
- **Gate: nothing proceeds to J.1 until this is clean**

#### J.1–J.3: Version, Deploy, Go/No-Go (1–1.5 days)
Per either source blueprint (identical in both): version bump to 1.0.0, changelog, release notes, deploy.bat test on Windows (macOS/Ubuntu if available), go/no-go gate.

---

## 2. Timeline

| Week | Focus |
|---|---|
| 1 | Phase A (data layer) → B (ledger UI) → C (recurring drafts, start) |
| 2 | C (finish) → D (checking linking) → E (payoff integration) |
| 3 | F (narrative) → G (testing/polish) → H1 (historian build) |
| 4 | H2.1–H2.3 (category suggestions, budget variance, trip forecast) |
| 5 | H2.4–H2.6 (recurring detection, payoff confidence, gate improvement) → I (subsystem verification incl. adaptive smoke tests) |
| 6 (Mon–Tue) | J.0 (personal data & secrets audit, hard gate) → J.1–J.3 (version bump, deploy test, go/no-go) → **ship 1.0.0** |

**Total: ~28–35 days solo**, up from the Final Foundation blueprint's 19–25 days — the difference is Phase H2 (adaptive learning), H1 being real construction (schema, queries, docs, and the `trip_history` table) rather than a verification pass, and the new J.0 data-audit gate.

---

## 3. Master Checklist

- [ ] **A–G:** Debt reconciliation complete, all 7 phase gates passed (see source blueprint)
- [ ] **H1:** Historian schema + queries + docs built and tested
- [ ] **H2:** All six adaptive features built, each validated against real data, success criteria met
- [ ] **I:** Smoke tests expanded (existing `check()` style) covering all subsystems + adaptive features; integration regression scenarios pass; DB integrity verified
- [ ] **J.0:** Personal data & secrets audit clean (source + built artifact) — hard gate, see below
- [ ] **J.1–J.3:** Version 1.0.0 tagged, changelog/release notes written, deploy tested, go/no-go = GO

---

## 4. Key Decisions Locked

- Debt reconciliation is the last *structural* feature before 1.0; adaptive learning is the last *intelligence* layer, built directly on top of it — not a separate future release
- Historian is genuinely production-grade at 1.0.0 launch, not scaffolding — it has to be, since six features read from it on day one
- Distance Traveled narrative (debt compliance + all adaptive-derived copy) routes through the existing `_voiceGateCheck` — no parallel gate is built
- Net worth, encryption, EIA pricing (trip + utility) — unchanged, already correct
- Versioning: 1.0.0 → 1.0.x = bugfixes/refinements only, no new features in the 1.0 line (matches both source blueprints)
