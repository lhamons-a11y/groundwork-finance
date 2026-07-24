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

| Category | Written by | Status |
|---|---|---|
| `payment_confirmed` | `confirm_debt_draft` (within ±5% of the recurring pattern's amount) | **Live** |
| `payment_amount_variance` | `confirm_debt_draft` (outside ±5%) | **Live** |
| `payment_skipped` | `skip_debt_draft` | **Live** |
| `charge_observation` | `create_debt_ledger_entry` (charge entries only) | **Live** |
| `payment_timing_slippage` | — | Not written. Needs a due-date-vs-confirmed-date offset computation that doesn't exist yet. |
| `balance_correction` | — | Not written. Candidate: a direct edit to `DebtAccount.current_balance` via `update_debt`. |
| `apr_correction` | — | Not written. Candidate: `interest_rate` edits via `update_debt`. |
| `interest_discrepancy` | — | Not written. |
| `late_fee_trigger` | — | Not written. |
| `categorization_suggestion_confirm` / `_reject` | — | 1.1-scaffold. Phase H2 Feature 1 wires this. |
| `budget_variance_observed` | — | 1.1-scaffold. Phase H2 Feature 2 wires this. |
| `trip_expense_variance` | — | 1.1-scaffold. Phase H2 Feature 3 wires this (see `trip_history` below). |
| `llm_gate_flag` | — | **Doesn't need wiring** — `voice_miss_log.jsonl` (the `ai_voice_miss` route) already is this log. `get_llm_miss_log()` reads that file, not this table. Don't build a parallel writer. |

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

### 1.1-scaffold reads

`get_category_patterns`, `get_budget_variance_by_category`, `get_trip_variance_by_region`,
`get_llm_miss_log` — real, working query functions, but three of them (all but
`get_category_patterns`, which reads existing ledger data as a reasonable stand-in today) read
event categories nothing writes yet. They return honest empty/neutral shapes until Phase H2 builds
the feature that starts writing to them. **Do not fill in fake data to make these "work" —
returning an honest `None`/empty result is the correct behavior for an unwired query.**

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
