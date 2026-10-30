# Historian — Developer Guide

**Status:** Phase H1 infrastructure, built 2026-07-24 (`GROUNDWORK_1_0_ROADMAP.md`)

## What this actually is

Before Phase H1, "historian" meant one thing in this codebase: `debt_balance_history`, a monthly
balance-snapshot table (see `DebtBalanceHistory` in `core/database.py`), auto-written on import.
That table still exists and still does that job — it isn't going anywhere.

`historian_entries` (`HistorianEntry` in `core/database.py`) is a different, new thing: a
structured, queryable **event log**. Where `debt_balance_history` answers "what was the balance in
March," `historian_entries` answers "what happened, and how did it compare to what was expected."
It's the substrate Phase H2's adaptive-learning features read from, and it's what Phase E/F's
payment-compliance reporting is quietly built on top of.

## Schema

```
historian_entries
  id
  event_category    -- see the list below
  debt_account_id    -- FK, nullable (not every event is debt-related)
  category_id        -- FK to categories.id, nullable (for category-learning events)
  expected_value      -- e.g. the recurring pattern's saved amount
  actual_value         -- e.g. what the user actually confirmed
  variance_pct          -- computed by log_historian_event() when both values are given
  variance_amount        -- ditto
  context_json             -- freeform JSON, whatever the event needs to remember
  created_at
```

Indexed on `(event_category, debt_account_id)`, `(debt_account_id, created_at)`, and
`(event_category, created_at)` — the three access patterns every query helper below actually uses.

No `payoff_plan_id` column. This codebase has no persisted payoff-plan table — payoff projections
are computed client-side on demand (`_calcDebtIntelligence` in `app.js`), not stored. If that ever
changes, this table would need a migration; don't invent a column pointing at nothing.

## Event categories

The canonical list lives in `HistorianEntry`'s docstring in `core/database.py` — keep this table
in sync with it (this is the artifact that drifts; the docstring has stayed current).

### Live — written today

Anchored by function name (the stable reference — line numbers drift on every edit, which is how
this table fell out of sync before).

**Domain events** — logged inline by the route where the thing actually happens:

| Category | Written by |
|---|---|
| `payment_confirmed` / `payment_amount_variance` | `confirm_debt_draft`, split on ±5% of the recurring pattern's amount |
| `payment_skipped` | `skip_debt_draft` |
| `charge_observation` | `create_debt_ledger_entry`, charge entries only |
| `recurring_pattern_confirm` / `_reject` | `budget_detect_recurring_feedback` — a detected merchant added to / dismissed from the budget |
| `categorization_suggestion_confirm` / `_reject` | `suggest_category_feedback` — suggestion kept / changed at ledger save |
| `net_worth_milestone_variance` | `_log_net_worth_milestone_variance` — snapshot save vs. a milestone's linear pace |
| `investment_allocation_drift` | price refresh, actual $ vs. target % of portfolio |
| `sinking_fund_contribution_variance` | a deposit vs. the fund's `monthly_contribution` (auto-credit retired 2026-10-30, item 114 F1) |
| `college_fund_contribution_variance` | `_log_college_fund_contribution_variance` vs. `monthlyContrib` |
| `gift_season_contribution_variance` | `_log_gift_season_contribution_variance` vs. a deadline-derived pace |
| `gift_occasion_variance` | `_log_gift_occasion_variance` — actual spend vs. budget, after the date passes |
| `byb_purchase_decision` | Before You Buy commit/walkaway (expected/actual only on a resolved `track` item) |
| `budget_adjusted` | `update_budget_item` — user changes a budget item's amount (expected=old, actual=new). Distinct from the unwritten automatic `budget_variance_observed` |

**Engagement / session events** — app lifecycle and page navigation:

| Category | Written by |
|---|---|
| `session_start` | `bootstrap` — server-side, the one request guaranteed to fire on every app open |
| `session_end` | client keepalive POST on `pagehide` (`boot` in `app.js`) → `log_engagement_event`. Best-effort; can be missed on a hard kill |
| `budget_reviewed` | client signal on `showView('budget')` in `app.js` → `log_engagement_event` |

The two client-signaled events (`session_end`, `budget_reviewed`) share one whitelisted route,
`POST /api/historian/engagement` (`log_engagement_event`), which rejects any category outside
`_CLIENT_ENGAGEMENT_EVENTS` — so the client can't inject arbitrary categories. `session_start` and
`budget_adjusted` are logged server-side instead, at the request that actually marks the event, so
they don't depend on a client call firing. Engagement events are purely categorical (no
expected/actual) except `budget_adjusted`, which carries a real old→new variance.

### Not written yet

| Category | Status |
|---|---|
| `payment_timing_slippage` | Not written. Needs a due-date-vs-confirmed-date offset computation that doesn't exist yet. |
| `balance_correction` | Not written. Candidate: a direct edit to `DebtAccount.current_balance` via `update_debt`. |
| `apr_correction` | Not written. Candidate: `interest_rate` edits via `update_debt`. |
| `interest_discrepancy` | Not written. |
| `late_fee_trigger` | Not written. |
| `budget_variance_observed` | 1.1-scaffold. `suggest_budget_adjustment` has no UI consumer yet — see `get_budget_variance_by_category`. |
| `trip_expense_variance` | 1.1-scaffold. `trip_history` covers this instead (see below). |
| `llm_gate_flag` | **Doesn't need wiring** — `voice_miss_log.jsonl` (the `ai_voice_miss` route) already is this log. `get_llm_miss_log()` reads that file, not this table. Don't build a parallel writer. |

## Query helpers (`server.py`)

- `log_historian_event(session, event_category, ...)` — the one writer. Computes
  `variance_pct`/`variance_amount` when both `expected_value` and `actual_value` are given; leaves
  them `None` otherwise. Does not commit — call inside an existing `with db_session() as session:`
  block and let the caller commit, same pattern as every other write helper in this file.
- `get_payment_variance_for_account(session, debt_account_id, months=12)` — on-time/under/over
  counts from the historian's point-in-time record. Distinct from Phase E's
  `get_payment_compliance` (which reads current ledger state per recurring pattern) — this reads
  what was true *at confirm time*, so it stays correct even if a ledger entry is edited later.
- `get_payment_compliance_confidence(session, debt_account_id)` — 0-100 score, on-time rate minus a
  penalty per late-fee event. Returns `confidence_pct: None` (not a fabricated number) when there's
  no history yet.
- `get_late_payment_pattern(session, debt_account_id)` — returns an honest empty result today;
  nothing writes `payment_timing_slippage` yet.

### Confidence reads for the non-debt variance events

All five mirror `get_payment_compliance_confidence`'s shape and honesty rule — a 0-100
`confidence_pct` (or `None`, never a fabricated number, when there's no history yet), penalising only
running *behind* pace, never being ahead. Each is exposed through a thin `ok(...)` route so `app.js`
can read it the same way the debt confidence UI does:

- `get_net_worth_milestone_confidence(session, milestone_id)` — reads `net_worth_milestone_variance`.
- `get_investment_allocation_confidence(session, asset_class)` — reads `investment_allocation_drift`.
- `get_sinking_fund_confidence(session, fund_id)` — reads `sinking_fund_contribution_variance`.
- `get_college_fund_confidence(session, fund_id)` — reads `college_fund_contribution_variance`.
- `get_gift_season_confidence(session, season_id)` — reads `gift_season_contribution_variance`.

Two live write categories have **no dedicated read helper yet**: `gift_occasion_variance` and
`byb_purchase_decision`. They're written and queryable, but nothing aggregates them into a
confidence score — add one following the pattern above when a feature needs it.

### Engagement read

- `get_engagement_streak(session)` — the first *engagement* reader (the confidence reads above all
  score variance events; this is a habit signal). Consecutive-day check-in streak from
  `session_start` (distinct calendar days, so multiple launches/refreshes in one day count once; the
  streak survives a day not-yet-opened until a full day lapses), plus this month's `budget_reviewed`
  count. Returns an honest zero shape when there's no history. Exposed at `GET /api/historian/streak`
  and consumed by `_renderCheckInStreak` in `app.js`, which self-gates the dashboard pill on
  `streak_days >= 2` — the same "show nothing until there's a real signal" rule the confidence cards
  use. This is the tracer-bullet consumer for the engagement events: `session_end` and
  `budget_adjusted` are collected but not yet read by anything.

### 1.1-scaffold reads

`get_category_patterns`, `get_budget_variance_by_category`, `get_trip_variance_by_region`,
`get_llm_miss_log` — real, working query functions. Two of them (`get_budget_variance_by_category`,
`get_trip_variance_by_region`) read event categories nothing writes yet and return honest
empty/neutral shapes until Phase H2 builds the feature that starts writing to them.
`get_category_patterns` reads the ledger/transaction history directly — a deliberate choice, not a
stopgap: `categorization_suggestion_confirm/reject` events *are* written now, but the ledger holds
the full categorization record while the confirm/reject log only captures the sparse shown-suggestion
cases. **Do not fill in fake data to make the unwired ones "work" — returning an honest `None`/empty
result is the correct behavior for an unwired query.**

## `trip_history` — the other Phase H1 table

Not `historian_entries` — trips are per-trip records, not point-in-time events, so they get their
own table (`TripHistory`). Before this, a trip only ever existed as a single `trip_budget` JSON
blob in `AppSetting` (`server.py`) — one current trip, no history across many. That blocked
`get_trip_variance_by_region` from having anything real to aggregate.

**The two write hooks this needs are not wired yet.** They belong with Phase H2 Feature 3 (trip
spending forecast), not H1, because that's when someone will actually be looking at the relevant
`app.js` trip code:
1. Trip budget save (`tripUpdateBudget` commit) → insert/update the estimate side.
2. "Use these numbers" in `_applyTripLearnedBasis` (`app.js:10186`) → backfill the actual side for
   that date range.

## How to add a new event type

1. Add it to the table in this doc and to `HistorianEntry`'s docstring in `core/database.py` (keep
   both in sync — that docstring is the canonical list).
2. Find the route where the thing actually happens, and call `log_historian_event(session, ...)`
   inside its existing `with db_session()` block, before `session.commit()`.
3. If the event needs a value nothing currently computes (e.g. `payment_timing_slippage` needs a
   due-date offset), build that computation first — don't log a value you don't actually have.
4. Add a smoke_test.py check that the event gets written with the right category and
   expected/actual values, following the pattern in the Phase H1 section of `smoke_test.py`.

## How to build an adaptive feature on top of this (Phase H2)

1. Confirm the event category you need is being written (check the table above — most aren't yet).
   If not, wire the writer first per the steps above.
2. Write (or extend) the query helper that reads it.
3. Build the feature against real data — this codebase's Phase H2 plan explicitly means testing
   against a real database, not synthetic fixtures, before shipping.
4. Add smoke_test.py coverage for the query helper, same as every other phase in this build.
