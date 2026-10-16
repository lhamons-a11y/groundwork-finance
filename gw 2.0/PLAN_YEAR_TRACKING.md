# Item 87 — Plan year and deductible tracking (item 45 H7 stage 2)

**OPENED 2026-10-15 (Rob: "besides the ubi key lets continue to build"; the next stage in H7's ruled order). RULED +
BUILD AUTHORISED 2026-10-15 (Rob: "I approve P1-P9 as recommended. Build item 87.").**

## Summary

A health plan has a deductible, an out-of-pocket maximum and a plan year, and the person has made some progress
against each. Groundwork can't show any of that today. The record layer for it exists (`core/plan_year.py`, five
tables in `core/database.py`), but nothing calls it and nothing on screen uses it. This item would connect it: you
enter your plan and its terms, and Groundwork shows the deductible, the out-of-pocket maximum, how much has been met
so far, what is left, and when it starts over.

The hard part is one question: where does "met so far" come from? `plan_year.py` adds up the expenses in the plan's
period. A bank row can't support that. Groundwork can see what was paid, but the insurer decides what counts toward
the deductible: copays usually don't, bills arrive months after the visit, and out-of-network care may not count at
all. So the recommendation (P1) is that progress is what the insurer reports, typed by you with its date, and never
worked out from your spending. Everything else follows the rulings already made: unknown stays unknown, the plan is
health data under H6, it works with AI off, master only, and no advice.

## 1. What is there today (measured on master `89d7ae6`)

- **`core/plan_year.py`** (334 lines, tests written first: `tests/test_plan_year_fixture.py`):
  - plans with periods, terms kept as versions, and *change* (going forward) told apart from *correction* (always
    true);
  - a mid-year plan switch kept as two plans;
  - accumulators derived, never stored, and `UNKNOWN` when terms are missing;
  - an `OVERLAP` refusal when two plans cover the same date.

  It keeps its state in memory (a `Registry`) and has no callers.
- **Tables** `health_plans`, `health_plan_term_versions`, `health_plan_operations`, `person_enrolments`,
  `healthcare_expenses` and friends exist in the schema, empty, and are written by nothing.
- **H6** already treats `health_plans.name` and the term versions' reason and source as health text to scrub.
- **Item 86** (HSA and FSA) is on the Accounts tab of Settings, with its own terms and "can't tell" rule.

## 2. Points for ruling

**P1. "Met so far" comes from the insurer, typed and dated, never from spending.** You type what your insurer's
website or latest statement says, for example "$1,450 of the deductible, $1,900 toward the out-of-pocket maximum,
as of Oct 1". Groundwork shows it as that: *"as of Oct 1, from your insurer, as you entered it"*. It never sums your
health spending into it, because a payment shows what you paid, not what the insurer applied (the H4 evidence rule,
ruled 2026-10-09). *Recommended.* The other choice, deriving it from the ledger, would be wrong in both directions,
silently.

**P2. The plan record uses `plan_year.py`'s rules, stored in the tables that already exist.** A plan has a name you
choose, a start and end date, and the coverage tier (self-only or family) with its deductible and out-of-pocket
maximum. Changing a term asks one question: *"did it change, or was it always this?"* A change applies going
forward and a correction applies back. Both keep the earlier figure. A mid-year switch is a new plan, and the first
plan's half-year is left as it was. Two plans covering the same date are refused, as the module already does. This
needs a small `readings` table for P3, so a `SCHEMA_VERSION` bump. *Recommended.*

**P3. Each reading is kept, with its date.** The newest reading is current, and older ones stay as history. The date
is always shown, never hidden. If the newest reading is older than the most recent health spending on record, the
card says so as a fact: *"Your last reading is from Aug 2; you've paid health bills since then."* It never guesses
how much those bills changed the figure. *Recommended.*

**P4. Unknown stays unknown.** With no plan, there is no card, only a line offering to add one. With a plan but no
deductible entered, the card says "deductible not entered", not $0. With no reading, it says "met so far: not entered
yet", and "what's left" is not shown. Nothing is ever shown as "met" by default (the triage repair `efbb271` already
fixed this once). *Recommended.*

**P5. Individual deductibles inside a family plan wait.** Many family plans have an amount per person as well as one
for the family. That needs named people, which is H7 stage 5, behind its own gate. This stage tracks the plan's own
figures, and the card says the per-person amounts aren't tracked yet. *Recommended.*

**P6. Where it shows: a "Health plan" card on the Accounts tab of Settings**, beside the HSA and FSA. It would be the
one place for health money. *Recommended*; the other choice is a card on the Budget page.

**P7. Teach the terms; give no advice.** Short help text explains what a deductible, coinsurance and an out-of-pocket
maximum are, and that the figures start over at the plan year's start. The reset date is stated as a fact: *"These
figures start over on Jan 1, 2027 (78 days)."* Groundwork never says "get care before it resets", never suggests
timing, and never calls a plan good or bad. *Recommended.*

**P8. Privacy under H6.** The plan's name, readings and terms are health data:
- the name is scrubbed (H6 already learns `health_plans` names);
- the plan section is left out of exports unless the health box is ticked;
- backups are sealed as now (item 81).

The dollar figures alone are money, like the HSA's. s208's sink registry gets the new routes. *Recommended.*

**P9. No Needs attention item in this stage.** A reset isn't money lost, unlike an FSA deadline. *Recommended*; you
may want one, say 30 days before the reset.

## 3. Left out of this stage, on purpose

- **The Care Planner and any timing lever** (design §1.1): that is advice-shaped and needs its own ruling.
- **Reading an EOB to fill in progress:** that is item 18's document line, stage 3, not authorised.
- **Per-person deductibles, enrolment and "whose expense" (stage 5, named people),** and the bill that lands
  (stage 6).
- **Premiums:** they are a bill in the Budget, as now.
- **Coinsurance and copay amounts:** stored only when a later stage needs them.
- **HSA eligibility:** whether the deductible meets the IRS high-deductible minimum is a determination close to tax
  advice, and is left out.
- **The 1.x line:** master only.

## 4. How it would be built and proven, once authorised

1. A small storage layer that keeps `plan_year.py`'s rules over the existing tables.
2. The readings table, with its migration and pin.
3. `core/health_plan.py`, holding the card's figures and sentences with their working.
4. The card, with its change-or-correction question.
5. The H6 export and scrub wiring.

A new smoke section would check the rendered sentences:
- no reading means "not entered", never $0 or "met";
- a correction moves the past, and a change does not;
- a mid-year switch keeps two separate plans;
- an overlap is refused;
- a stale reading is said to be stale;
- no advice words appear;
- the plan name is scrubbed and left out of exports.

It would be gated in its own worktree and accepted before push.

## Closing

This stage turns an unused, tested module into something you can see, and keeps it honest about what Groundwork can
know. The one decision that shapes everything else is P1. With it, every figure on the card is either something you
entered from your insurer, with its date, or a subtraction from it.


## Built 2026-10-15 (s227; SCHEMA 20261015-plan-year)

- **P1:** `health_plan_readings` holds what the insurer reports, typed and dated. The card says *"From your
  insurer, as you entered it. Groundwork doesn't work these out from your spending."* s227 puts a health payment on
  record and checks that nothing is summed from it.
- **P2:** `core/health_plan.py` keeps `plan_year.py`'s rules over the existing tables.
  - Every term edit must say whether it is a correction or a change; the route refuses one that says neither.
  - A correction keeps the earlier figure and the card names it (*"Corrected on Oct 15, 2026: it was deductible
    $3,000.00 before"*).
  - A change closes the plan the day before and starts a new one to the old end date. The earlier plan keeps its
    terms and readings, under "Other plans".
  - Two plans on one date are refused when saved.
  - The coverage tier is a versioned term (`health_plan_term_versions.tier`).
- **P3:** each figure's newest reading is current, and earlier ones are listed. A future date is refused. A
  reading older than the last health payment on record says so, and makes no guess.
- **P4:** "Deductible: not entered." / "Met so far: not entered yet." No "left" is shown without a reading.
- **P5:** a family plan says per-person amounts aren't tracked yet.
- **P6:** the Health plan card sits on the Accounts tab of Settings, below the accounts, the HSA and the FSA.
- **P7:** "What these terms mean" covers the deductible, coinsurance, copays and the out-of-pocket maximum, and says
  the insurer decides what counts. The reset is stated as a fact (*"These figures start over on Jan 1, 2027 (78
  days)."*). s227 checks a list of advice and timing words.
- **P8:** every save refreshes the H6 scrubber, so the plan's name is scrubbed at once. Plans leave the JSON and CSV
  exports only on the health tick.
- **P9:** no attention kind was added.
- Verified in the running app (dev database). Found and fixed there:
  - the "Corrected on" date was the UTC date (Oct 16 at 8:50 pm on Oct 15) and is now the local one;
  - the card first sat above "+ Add account" and now sits below it.
