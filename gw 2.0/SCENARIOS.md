# Item 66 — Exploring possible futures: scenarios the user can correct

Opened 2026-10-09. Rob first: *"having the groundwork agent running in the background utilizing as little memory as
possible running simulations of the user finances … We don't offer one simulation we offer the three best
simulations that would help the user and the three worse scenarios … That's teaching and learning."*

Then, refining it: *"You're not proposing a better budgeting screen. You're proposing a different way for Groundwork
to help someone understand and direct their financial future."*

**SC1–SC7 RULED as a whole (Rob, 2026-10-09: "I accept item 66 as a whole and item 65").** **First built 2026-10-10 through item 71** (Rob: "71 build on 66"): SC1 (the debt-free date as the goal measure, the goal fixed within an analysis), SC2's baseline and goal-oriented paths for an income drop, SC3 (every figure tagged observed / projected / user-supplied), SC5 (computed on read, nothing derived stored) and SC6 (side by side, assumptions in words, no verdicts, chosen only on the person's tap). **Still to build:** SC2's adverse scenarios from the record (the costliest months repeating, a month without income, minimums only, a known bill landing), SC4's "Partly / Unlikely for me" correction with a stored user-supplied possibility, SC6's charts over time, and SC7's pre-budget.

## The model (Rob, 2026-10-09)

1. **Financial reality:** imports, transactions, balances, bills, income, obligations, observed patterns.
2. **Financial engines:** cash flow, likely trajectories, payoff schedules, constraints.
3. **Scenario space:** goal-oriented futures and adverse ones, each with its assumptions and consequences.
4. **User context and judgment:** *"That doesn't reflect my life." "This expense is coming." "My hours may be cut."*
5. **Recalculated picture:** the consequences recomputed with the user's corrections and chosen assumptions.

**The feedback loop is the point.** Groundwork presents a picture the user can correct; it doesn't calculate once and
announce an answer.

**The goal is the constant; the circumstances are the variables.** Within an analysis the goal (for example, a
$5,000 cushion) stays fixed while scenarios vary the circumstances. A goal changes only when the user changes it.

**The design rule above all others: never confuse what the records show, what might happen, and what the user says
is happening.**

## 1. What is true today (measured 2026-10-09, master)

- **One payoff engine.** `POST /api/debt/simulate` runs the server's engine on a portfolio the page holds. The page's
  `_simulatePayoff` asks it rather than computing its own (Pillar 1: *"the defect is two answers to the same
  question"*), and the route persists nothing.
- **The solution engine** (`core/solution.py`) already compares paths:
  - `solve_one_time_cost`, `solve_monthly_cost` and `save_first_plan` rank paths;
  - `do_nothing_note` states the cost of no change;
  - `accelerations` names levers.

  Each works from the record and the user's statements (the Willingness Layer).
- **Other engines to build on:** the budget forecast, the trip forecast, plan years, reserves and payment plans
  (`core/plan_year.py`, `reserve.py`, `payment_plan.py`), and item 49's card payoff rows.
- **The goal exists as a household fact:** `surplus_goal` (debt / savings / goal / invest / unsure), asked in onboarding.
- **What doesn't exist:**
  - a place for a user-supplied *possibility* ("a repair may cost $800") that is neither a transaction nor a budget
    line;
  - a scenario that varies circumstances against a fixed goal;
  - a surface that compares futures over time;
  - any background recalculation.

## 2. Points for ruling

**SC1. The goal contract.** For each supported goal, define what counts as a better outcome:
- **debt:** an earlier debt-free date, then less interest;
- **savings:** the cushion reached sooner;
- **a named goal:** reached by its date;
- **invest:** more set aside each month after obligations;
- **unsure:** no ranking. Show the futures side by side and ask.

Every comparison also reports whether essential obligations stay affordable, and any debt taken on along the way.
The goal is fixed within an analysis, and only the user changes it.
*Recommended.*

**SC2. Scenario definitions.**
- **Baseline:** current income and spending continue, from the record.
- **Adverse, each from the user's own record** (never generic fear):
  - the three costliest recent months repeat;
  - one month without income;
  - minimum payments only;
  - a known upcoming bill lands (from the calendar, W3).
- **Goal-oriented:** the solution engine's ranked paths toward the goal.
- **User-modified:** any of these with the user's corrections (SC4).

Each scenario names its assumptions in words. A scenario the record can't support isn't offered, and the gap is said.
*Recommended.*

**SC3. Three kinds of input, never confused.** Every figure in a scenario carries its kind:
- **Observed:** established by transactions and records.
- **Projected:** what follows if the named assumptions continue.
- **User-supplied:** a possibility the user stated ("a repair, about $800, in March").

A user-supplied possibility is stored as such, with its own history like the household facts. It never becomes a
transaction, a budget line or a balance. The ledger is never rewritten by a scenario.
*Recommended.*

**SC4. Correcting the picture, not filling a form.** Each scenario asks one focused question, only when the answer
would materially change the result: *"Does this reflect your situation? Yes, a reasonable scenario / Partly,
something's missing / Unlikely for me / Explore something else."*
- *Partly* opens one prompt for the missing piece (another income continues, a known repair, hours already being cut).
- Groundwork recalculates. It doesn't argue, and it doesn't silently change the plan.
- *Unlikely for me* hides that scenario for the user, as their stated choice, undoable.

*Recommended.*

**SC5. The calculation lifecycle.** Scenarios are plain engine math, not the AI model, so they're light. They
recalculate when their inputs change: an import, an edit, a corrected assumption, a changed goal.
- A result computed from older inputs is marked stale until it's recomputed, never shown as current.
- Results are not persisted as conclusions (Willingness ruling 2). An in-memory cache keyed by the exact inputs is
  allowed.
- Whether a separate background runner is needed is decided after SC1–SC4, by measurement.

*Recommended.*

**SC6. The comparison surface.** The futures sit side by side over time as charts: the goal's progress, cash on
hand, debt.
- Each scenario has its assumptions in words and the kinds of input it used (SC3).
- Each scenario carries the questions it answers: *What would put me behind? Which upcoming expense changes the outcome
  most? How much room do I actually have? Which correction would change this result?*
- The words pass the voice rules: no verdicts, no fear words.
- With AI on, the model may explain a scenario; it never invents one (AP6).
- Choosing a path sets the plan only when the user says so.

*Recommended.*

**SC7. A pre-budget as an output.** From the observed record, Groundwork can estimate committed money, recurring
patterns and upcoming obligations, and show what remains under the chosen assumptions. That's a calculated starting
point the user corrects, not an assertion that Groundwork knows their whole life, and not a form they must fill
first.
*Recommended, as a later slice once SC1–SC6 stand.*

## 3. Not decided here

- **Ranges and probabilities** (for example, a spread of outcomes). The first version uses named, deterministic
  scenarios.
- **Which existing engines each scenario reuses.** That's decided in the build, after the ruling.
- **Assistant** asking about scenarios by voice: later, through the same surface.

## 4. Built 2026-10-12 (Rob 2026-10-11: "build ... 66"): the rest of SC1-SC7 - ACCEPTED + CLOSED 2026-10-12 (Rob: "I accept")

A **Possible futures** card on the Budget page, below "Your pay", for every household, not only after an income
drop. `core/futures.py` does plain arithmetic over the record plus the one payoff engine (its new `path` argument
gives the total still owed each month; nothing else in it changed). Routes are under `/api/futures`. Tests: s204.

- **The baseline** comes from the record:
  - income is the middle of the last three complete months with income on record (at least two are needed, or no
    futures are offered and the card says why);
  - spending is this month's budget, with debt payments apart;
  - the debt payment and the cards are the payoff engine's own inputs;
  - cash is what checking and savings hold above the person's own floors, the same figure item 71 uses (it starts at
    $0, said, when no balance is known).
- **SC1.** Each future is measured on the goal: debt-free months for *debt*, cash in 12 months for *savings* and a
  *goal*, what's left over for *invest*, and nothing ranked for *unsure*. Each future also shows its lowest cash and
  anything borrowed. When cash would go below $0, the shortfall is borrowed and counted, never hidden.
- **SC2.** Every future the record can support is offered:
  - **"What is left goes to the debt"** (debt goal, money left after the budget);
  - **"Your costliest months come again"** (the three costliest of the last 12 complete months, above a middle
    month, over the next three; needs six complete months on record);
  - **"A month without income"**;
  - **"Minimum payments only"** (only when the payment is above the minimums);
  - **"Known costs ahead land"** (gift occasions budgeted in the next 90 days; W3's calendar isn't built, so these
    are the costs on record).

  Each one the record can't support is listed under *Not shown, and why*.
- **SC3.** Every figure is tagged *Recorded*, *Projected* or *You said*. What the person says is kept append-only in
  `future_possibilities`, withdrawals included: another income, a known cost in a month, or hours being cut. It
  counts in every future and is never a transaction, a budget line or a balance; s204 checks the counts.
- **SC4.** Each adverse future, and the baseline, asks *"Does this reflect your situation?"*:
  - **Partly** and **Explore something else** open the one prompt for what's missing;
  - **Unlikely for me** hides it, with *Show ... again*.

  Answers are kept append-only in `future_answers`.
- **SC5.** Computed on every read, nothing derived stored. A fingerprint of the inputs is checked when the window
  regains focus; if it moved, the card says the figures were worked out from older records and offers
  *Recalculate*. No background runner: the arithmetic is instant.
- **SC6.** Two charts over 12 months show *Cash on hand* and *What you owe, with anything borrowed*, one line per
  future, each of which can be unticked. Each future carries its assumptions in words and its figures with their
  kinds. The four questions are answered from the figures:
  - what would put me behind;
  - which upcoming expense changes the outcome most;
  - how much room I actually have;
  - which correction would change this result.

  No verdicts and no fear words (s204 scans for them). There is no AI call. *Choose this path* only notes the choice;
  only *"What is left goes to the debt"* can change a figure, through its own *Set my debt payment to $X* button,
  with the old figure kept for *Undo*. A chosen future that is no longer offered, because its change is now the plan,
  still shows the choice and its Undo.
- **SC7.** *A starting budget from your record* lists what the record commits each month, each row with its
  source and kind, then the recorded income and what remains:
  - committed: the minimum debt payments, and budget lines set by a contract (item 71 D11);
  - recurring: recurring charges in the ledger (the solution engine's own list);
  - set aside: what each savings fund takes a month.

  It is a starting point to correct, not a form.
