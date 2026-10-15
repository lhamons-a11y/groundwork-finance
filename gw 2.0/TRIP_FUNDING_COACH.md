# Item 61 — A trip you commit to becomes part of the plan

Recorded 2026-10-09 as a direction for a later version, not for ruling now. Rob: *"What I would like to think about in
later versions that When the user selects that they are going on this trip that should kick in a travel budget that
can be seen in budget maybe that breaks out how much the user plans on spending on the trip and if this is all coming
out of monies left in checking, savings, credit cards, spread over multiple credit cards, and then create a way a
plan to pay them off or how to help build back up that checking or savings account in the near future. The app
should help like a coach that goal is to get the person to financial independence."*

## The idea, in parts

1. **"I'm going on this trip."** A committed trip becomes a travel budget, visible on the Budget page for the months
   it touches: what's planned, line by line, sourced as in items 59 and 60.
2. **Where the money comes from.** The user splits the total across sources: checking, savings (and which fund), one
   or more credit cards. Each source shows what's left after the trip, from the record:
   - available credit per card (item 49 already does one card);
   - the checking cushion against upcoming bills;
   - the savings balance against its goal.
3. **The way back.** A plan, built from each source's own terms:
   - **cards paid off:** a payoff per card, or across cards by the user's chosen method, the same engine as the debt
     plan;
   - **checking rebuilt** to its usual cushion over N months;
   - **savings refilled** to where it was, or to its goal.

   Each plan is shown against the user's own surplus, as a fact, never as a verdict on the trip.
4. **The coach.** The trip is one step on the path the user set. The plan says what the trip costs in time toward
   financial independence, in the user's own numbers ("this moves your debt-free date from March to May"). The choice
   stays the user's.

## What already exists to build on

- **Item 49:** a trip on one credit card, with payoff rows and the user's savings rate.
- **Item 50:** bookings matched to real charges.
- **Items 41–44, 48:** sourced fares and exact totals.
- **The debt plan, sinking funds, savings goals, the Willingness Layer** (the user's statements) and the solution
  engine.
- **The teaching principle:** teach the question, never a verdict.

## Before it's opened for ruling

Items 59 (real prices) and 60 (itinerary import) come first, so a committed trip's figures are real. The open
questions for that later ruling:
- whether a committed trip creates budget lines or a sinking fund;
- how a split across sources is entered;
- how the payback plan sits beside the existing debt plan without two plans competing for the same surplus.


---

## Opened for ruling 2026-10-12 (Rob 2026-10-11: "build ... all of item 61") - T1-T9 RULED 2026-10-12 (Rob: "I was going to add that we allow multiple cards but T5 is brilliant.. I accept T1 - T9")

Items 59 and 60 are built and accepted, so the trip's figures are real. This section measures what exists, answers
the three open questions above with recommendations, and asks for rulings. **No code until ruled.**

### 1. What is true today (measured 2026-10-12, master)

- **One trip at a time.** The planner saves a single trip in one setting (`trip_budget`), overwritten by the next.
  There is no list of trips and no state that says *"I'm going"*. `trip_history` keeps an estimate per trip for
  learning actuals; it is not a plan.
- **One card.** Item 49's card plan (`/api/trip/card-plan`, `core/trip_card.py`) prices the trip on **one** chosen
  card. It shows whether it fits, payoffs over 3/6/12 months at that card's APR, paying it in full, and the whole debt
  plan at current payments. Nothing is saved.
- **Bookings.** Item 50's "I booked it" records a booking against a card or a checking account, then links the real
  charge on a yes. It is a planned record; the money is counted once, when the charge is imported.
- **The Budget page knows nothing of a trip.** No line, no fund, no month marked.
- **What can be reused:**
  - the one payoff engine (with item 66's month-by-month path);
  - sinking funds that fill themselves (item 74 G2);
  - the floors on checking and savings (item 68 B6, *"always leave"*);
  - item 66's futures (a known cost in a month already counts in every future);
  - the evidence library's card-payoff entries (item 58 E9).

### 2. Points for ruling

**T1. Trips become records, and "I'm going" is a state.**
- Trips get their own table (`trips`: destination, dates, the planned total and its lines, status
  *planning* / *going* / *done* / *cancelled*), with a SCHEMA_VERSION bump.
- The single `trip_budget` setting is carried over as the first trip, and kept.
- Only a tap on **"I'm going on this trip"** makes a trip *going*. Groundwork never decides a trip is happening from
  purchases (TM5).

*Recommended.* Every later point needs a trip that stays put while the person plans another.

**T2. How a committed trip shows on the budget (the first open question).**
- (a) **Budget lines.** This repeats item 74's *"Budget it"* bug: a line repeats every month, so a $1,800 trip reads
  as $18,792 a year.
- (b) **A trip fund, plus the trip shown in its months.** A gift-style sinking fund, *"Trip: Denver, June"*, takes
  what the person chooses to save ahead and fills itself monthly. The Budget page shows the trip in the months it
  touches as a derived block, *"Trip to Denver, Jun 12-16: $1,601 planned"*, with its lines. Nothing is written as a
  budget line.
- (c) Nothing on the Budget page; the trip page only.

*Recommended: (b).* It is the same fix item 74 made for a yearly cost: a one-time cost is set aside, not budgeted
every month.

**T3. Where the money comes from (the second open question).** On "I'm going", one row per source, entered once and
editable. The rows must add up to the trip's total, and the page shows what's left to assign.
- **Checking:** the amount, and what's left above the person's own floor once the bills due before the trip are
  paid (from item 68's bill checks; it says so when no floor is set).
- **Savings, or a fund:** which one, the amount, and where it leaves that fund against its goal.
- **One or more credit cards:** an amount on each, and each card's available credit after it. This needs a limit
  entered; otherwise it says the limit isn't entered.

Groundwork never moves any of this money (TM1). The split is the person's plan, kept as their statement.

*Recommended.*

**T4. The way back, from each source's own terms.**
- **Each card's share:** paid off by the one payoff engine, alongside the existing debt plan (T5), with each card's
  3/6/12-month figures as item 49 shows today, now per card.
- **Checking:** back to its usual level over 3, 6 or 12 months, as the person picks. It shows the monthly amount
  that takes.
- **Savings or a fund:** refilled to where it was, or to its goal by its date, with the monthly amount.

Every plan is shown against the person's own monthly surplus, as a fact, never as a verdict on the trip.

*Recommended.*

**T5. One plan, not two (the third open question).**
- **Card shares.** A card's share of a *going* trip is added to that card's balance in **the** debt plan as a
  *projected* charge, labelled. Once the real charge is imported and linked (item 50), the record carries it and the
  projection drops. It is counted once, never twice.
- **Rebuilding cash competes with the debt plan's extra for the same surplus.** So the page shows the split, and the
  person chooses the order:
  - debt first, then rebuild;
  - rebuild first;
  - or a split they set.

  With no choice made, nothing is assumed: the page shows both orders side by side, and the debt-free date and the
  rebuild date for each.

*Recommended.* A second payoff calculation for trips is the defect Pillar 1 exists to retire.

**T6. The coach line: the trip's cost in time.** One sentence of facts from the person's own numbers: *"Going moves
your debt-free date from March 2028 to May 2028, and checking is back to its usual level by September."*
- It is measured on the goal the person set (item 66 SC1): the debt-free date for *debt*, the cushion date for
  *savings*.
- With *unsure*, both are shown, unranked.
- No verdict and no fear words, and the choice stays the person's.

*Recommended.*

**T7. After the trip.**
- Once the end date passes, the trip offers its matched bookings, plus the charges filed under Travel during the
  trip's dates, as *"what it cost"*. They count only on a yes, the same rule as item 74 G4 (TM5).
- The plan and the actual then sit side by side: *"Planned $1,601, spent $1,831"*.
- The trip becomes *done*. Money left in its fund stays in the fund, and the person decides what happens to it.

*Recommended.*

**T8. Item 66's futures see a going trip.** A *going* trip appears in every possible future as a known cost in its
month, tagged *You said* (SC3). The futures' **"Known costs ahead"** includes it.

*Recommended.* The futures already count a possibility the person states; a committed trip is one.

**T9. Lines and tests.** Master only. Tests:
- a trip's cost is never a monthly line;
- the sources must add up to the total;
- a card share is counted once (projected, then linked, never both);
- the two orders give the dates the engine gives;
- "I'm going" is only ever a tap;
- after the trip, charges count only on a yes;
- AI off works throughout.

*Recommended.*

### 3. Not decided here

- **Financial independence as its own number** (for example, "years to independence"). Settled 2026-10-14
  (Rob): financial independence is defined as the purpose of the whole application (out of debt, budget wisely,
  invest and build net worth), not as a separate number (`BUILD_QUEUE.md` horizon note). T6 uses the goal contract
  that exists.
- **Sharing a trip's cost with other people** (who owes whom).
- **Booking or paying anything.** Never (TM1).

## Built 2026-10-12 (Rob: "I accept T1 - T9") - ACCEPTED + CLOSED 2026-10-12 (Rob: "I love the new tools that we are adding to 2.0 ... I accept Item 61")

- **T1.** A `trips` table, at SCHEMA `20261012-trips`. The old `trip_budget` setting is carried in once as a
  *planning* trip with its lines, and the setting is kept. **"I'm going on this trip"** under the trip budget is the
  only way a trip becomes *going*: a confirmed tap, `POST /api/trips`.
- **T2.**
  - *Save ahead, in a trip fund* creates the trip's own sinking fund (purpose `trip`, its date the departure). It
    fills itself monthly like every fund.
  - The Budget page shows **Trips this month**, derived, saying it isn't a budget line. s207 checks that no budget
    item is added.
- **T3.**
  - **Sources:** checking, savings, a savings fund, one or more credit cards, or saving ahead.
  - **Validation:** each must be the person's own, and they may not add up to more than the trip. The panel shows
    what's left to assign.
  - **What each source leaves:**
    - a card: its credit left, or *its limit isn't entered*;
    - checking or savings: what's above the person's *always leave* amount, or that none is set;
    - a fund: what is left in it.
- **T4.**
  - **Each card:** item 49's 3/6/12-month rows, now per card.
  - **Checking, savings and funds:** rebuilt over 3, 6 or 12 months, with the monthly amount.
- **T5.**
  - **Counted once.** A card's share joins the one debt plan as a projected charge. Once a booking for that trip on
    that card has its charge linked (item 50), the projection drops.
  - **One engine.** `simulate_payoff` gained `extra_schedule`, an extra per month. With it, *debt first*, *rebuild
    first* and a *split* the person sets are each priced by the one engine. Left unchosen, both are shown.
  - **The surplus** is item 66's: income minus the budget minus debt payments. With none, the panel says so.
- **T6.** The coach line, in facts: *"Your debt-free date stays October 2028, and the money from checking and savings
  is back by December 2026."*, or *"Going moves your debt-free date from ... to ..."*. It is measured on the person's
  goal, and both orders are shown when none is chosen.
- **T7.** After the return date, *"The trip's over: what did it cost?"* offers the trip's bookings and its Travel
  charges, up to 3 days after. Only ticked ones count. The trip becomes *done*, with a Historian `trip_actual`
  (expected the plan, actual the charges).
- **T8.** Each going trip is a known cost in its departure month in every possible future: its cash part, or the
  whole trip when no split is entered. It is tagged *You said*, marked *a trip you're going on*, and isn't taken back
  from there.
- **T9.** s207, 17 checks.

Never: booking, paying or moving money (TM1); a trip inferred from purchases (TM5); a budget line for a trip.
