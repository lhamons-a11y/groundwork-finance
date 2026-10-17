# Item 90 — Payoff dates that follow the health reserve choice (item 88 follow-up)

**OPENED 2026-10-16 (Rob: "Do this task here: Make payoff dates reserve-aware (item 88 follow-up)"). RULED + BUILD
AUTHORISED 2026-10-16 (Rob: "I approve D1-D7 as recommended. Build item 90."). ACCEPTED + CLOSED 2026-10-16 (Rob: "I accept merge and push").**

## Summary

Item 88 lets you choose when the health reserve fills: after the last debt, before it, or alongside it. The Debt
Payoff card shows each option's dates. Every other payoff date in Groundwork still assumes "after", including the
date at the top of Debt Payoff, the dashboard's debt-free date, Before You Buy's "this moves your date", trips and
possible futures. The item 88 card says so in one line.

The fix is smaller than it looked. The page has no payoff math of its own: all 32 of its payoff calculations ask the
server engine through one route (`/api/debt/simulate`). The server's own teaching surfaces read the same engine
through `_consequence_inputs`. So one function, the reserve's month-by-month schedule, applied at those two doors,
makes every date follow your choice, and the page and server still give one answer. For anyone who hasn't chosen,
or chose "after", nothing changes.

## 1. What is there today (measured on branch `health-reserve-88`, `4506e53`)

- **The page:** `_simulatePayoff` and `_simulatePayoffStrategy` (`static/js/app.js`, 32 call sites) build the cards
  and budget and call `_simAsk`, which posts to `/api/debt/simulate`. That route runs
  `core/consequence.simulate_payoff`. The page computes no dates itself (Pillar 1: one engine).
- **The server:** `_consequence_inputs(session)` (16 callers in `server.py`) feeds `simulate_payoff` directly (9
  calls) and through the engines in `core/solution.py`, `futures.py`, `income_change.py`, `trips.py` and
  `trip_card.py`.
- **The engine** already takes `extra_schedule`, a per-month change to the money above the minimums. Minimums are
  always paid first.
- **Item 88** builds its three options with that schedule, so the comparison and the app would use the same
  mechanism.

## 2. Points for ruling

**D1. Every payoff date follows the choice.** That covers the page through `/api/debt/simulate` and the server
through `_consequence_inputs`. What-if comparisons (a purchase, a trip, an income change, a possible future) get the
schedule on both sides, so the difference they show stays like for like. *Recommended.* The other choice, the Debt
Payoff date only, would leave two answers to one question, which is what Pillar 1 forbids.

**D2. One function makes the schedule, worked out fresh on every read.** `reserve_schedule(session, cards, budget)`
in `core/health_reserve.py` returns nothing when:
- there is no choice, or the choice is "after";
- there is no target;
- the reserve is full.

Otherwise it returns the months of money going to the reserve:
- **Before:** the extra above the minimums for this call's own cards and budget.
- **Alongside:** your amount, capped at that extra.

As you raise the reserved level, the schedule shortens by itself. Nothing is stored. *Recommended.*

**D3. Nothing changes for anyone who hasn't chosen.** With no choice, "after", no target or a full reserve, every
date is identical to today's. The gate pins that by comparing the engine's answers with and without the hook.
*Recommended.*

**D4. A date that includes the reserve says so.**
- **The Debt Payoff headline:** one line under it, for example *"Includes your health reserve: $150 a month until
  Mar 2027."*
- **Surfaces that already list their inputs** (the transparency standard): one input line, *"Health reserve: $150 a
  month for 14 months (your choice)."*

No figure moves without its working showing why. *Recommended.*

**D5. Item 88's own card keeps its three options.** It asks the engine without the hook, so "after" stays the
comparison point and the three options stay comparable. Its one-line note becomes *"The dates elsewhere in
Groundwork follow your choice."* *Recommended.*

**D6. History is never rewritten.** Net-worth snapshots, milestones and anything already recorded stay as they were.
Only forward-looking dates change. Trophies are awarded on recorded events, and the build measures that none reads a
projected date. *Recommended.*

**D7. Master only, AI-off, no schema change.** The choice and the reserve are already stored by item 88.
*Recommended.*

## 3. Left out, on purpose

- **A dashboard Needs attention item** for the reserve or the date: none was ruled.
- **Freed minimums flowing into the reserve under "before"** as cards clear: still the item 88 R5 assumption (its
  dates are on the late side). It can be its own refinement.

## 4. How it would be built and proven, once authorised

1. `reserve_schedule` in `core/health_reserve.py`.
2. Applied in `/api/debt/simulate`, unless a request says `reserve: false`, as item 88's card will.
3. Applied in one helper that every `simulate_payoff` call reached from `_consequence_inputs` goes through, so a new
   caller can't miss it. A scan in the new smoke section lists every `simulate_payoff` call and fails on one that
   bypasses the helper.
4. The headline line and the input lines.

The smoke section checks:
- no choice gives identical dates (D3);
- "before" and "alongside" move the headline, Before You Buy, trips and possible futures by the same months as item
  88's card shows;
- the page's and server's answers agree;
- the schedule shortens as the reserve fills;
- the date says so (D4);
- snapshots are untouched (D6).

## Closing

All of the page's dates already go through one route, which is why this is small. It completes item 88's R1: once
you choose, Groundwork's dates follow your choice and show that they do. Until then, nothing moves.


## Built 2026-10-16 (s230; no schema change)

- **D1–D3, one door instead of two.** Measuring the code showed a simpler place than the two doors in section 4:
  the engine itself. `core/consequence.simulate_payoff` reads the household's reserve plan from a per-request
  context (`RESERVE_PLAN`). The server sets it at the start of each `/api/` request, lazily: the database is read
  only if the request computes a date, then reset.
  - Every payoff date gets the schedule, on both sides of every what-if: all 32 page calculations through
    `/api/debt/simulate`, and every server engine. A new caller can't bypass it.
  - Outside a request (tests, scripts) there is no plan, so nothing changes.
  - With no choice, "after", no target or a full reserve, the plan is None and every date is identical. s230
    compares against the bare engine.
- **D2:** `reserve_schedule(extra)` uses this calculation's own extra above the minimums: all of it for "before",
  the person's amount capped at it for "alongside", for as many months as the gap needs. The gap is worked out
  fresh (`health_reserve.request_plan`), so raising the reserve shortens the schedule by itself.
- **D4:**
  - The line under the Debt Payoff date: *"Includes your health reserve: $300.00 a month until Jun 2028."*
  - Possible futures and income changes list *"Health reserve: $X a month for N months (your choice)"* with their
    inputs.
  - The page's cached dates are cleared when the reserve, the choice or the plan changes, so the dates update.
- **D5:** item 88's card asks with `no_reserve()`, the only sanctioned opt-out (s230 lists its callers). Its note now
  reads *"The payoff dates elsewhere in Groundwork follow your choice."*
- **D6:** the hook writes nothing; trophies read no projected date.
- **Verified in the running app:** choosing "before" moved the Debt Payoff date from Oct 2028 to Oct 2029, the same
  date the card shows for "before", with the line under it. Choosing "after" restored Oct 2028 and removed the
  line.
