# What a payment agreement would have to be

**Gap 8 — inspection before design, and design before schema**

> Status: **INSPECTION. Nothing is proposed for building.** Written 2026-09-09 at Rob's
> direction, after #15 closed as design: *"we now know why it can't be closed with another
> fixture: the missing payment-plan/versioning entity is genuinely schema-level. That's a good
> point to stop doing safety-theory work and inspect what the smallest correct domain
> representation would actually be."*
>
> This document establishes **facts about the repository** and names the **forks that are
> decisions**. Per the semantic-audit method, only question 1 is a design decision; two through
> six are findings, and establishing them is what makes the decision tractable.

---

## 0. Why a fixture cannot close this one

Gaps 4, 1 and 6 all closed the same way: the data already existed, the invariant did not, so the
work was to state it and mutation-test it. **Gap 8 has no data.** There is no payment-agreement
row anywhere in `core/database.py`, versioned or otherwise, and `core/payment_plan.py`'s `Plan`
takes `instalment`, `count` and `first_due` as **caller-supplied scalars** precisely so that
inventing the entity did not happen by accident inside gap 6.

So a fixture here would be a fixture against nothing. That is the difference, and it is why this
is schema-level work rather than another hostile-fixture pass.

**One fact that makes the timing favourable: the blast radius today is zero.** `payment_plan.py`
is imported by exactly two files — its own fixture and `smoke_sections/s99_payment_state.py`.
`server.py` does not reference it. Nothing in the running application consumes payment state,
which will not be true once the healthcare module is wired, and *that* is the argument for
settling the entity now rather than after it acquires callers.

## 1. What already exists, and what each thing actually is

| | What it is | Why it is not the answer |
|---|---|---|
| `payment_plan.Plan` | three scalars on a dataclass | no identity, no history, terms cannot change |
| `RecurringDebtPayment` | a **mutable saved pattern** — *"$735 on the 15th"* | `is_active` + editable amount; changing terms **destroys the prior terms** |
| `DebtAccount` | balance, APR, minimum, `debt_type` | an account, not an agreement; no schedule and no term |
| `HealthPlanTermVersion` + `HealthPlanOperation` | append-only terms + `kind = change \| correction` | **the right shape**, on the wrong subject |
| `ExpenseObligationVersion` | append-only claim amounts with `supersedes_id` | ditto |
| `ExpenseFundingAllocation` | version chain with `occurred_on`, `effective_seq`, `recorded_seq` | ditto |

**Finding 1 — the versioning mechanics are already solved, three times.** Append-only rows, a
`supersedes_id`, an effective ordering separate from a recorded ordering. None of that is open
work, and none of it should be re-derived. Copying it is cheap and correct.

**Finding 2 — `RecurringDebtPayment` is the trap.** It is the nearest existing table, it is
about payments on a schedule, and reaching for it would be the mistake. Toggling `is_active` and
writing a new amount is exactly the mutation that versioning exists to prevent, and it hangs off
`debt_accounts`, which drags in finding 6 uninvited.

## 2. The thing that is genuinely new

A `HealthPlanTermVersion` answers a **point** question: *what was the deductible in March?* Look
up the version in force, return the value.

A payment schedule answers a **span** question: *what was expected by March?* That is not a
lookup. It is a fold across every term version that was in force over the elapsed period.

Concretely, `core/payment_plan.py:142` today:

```python
def _instalments_due(plan, as_of):
    months = (y1 - y0) * 12 + (m1 - m0) + 1
    return max(0, min(plan.count, months))          # one cap, one instalment size
```

Under versioning this cannot survive. `expected_by_now` becomes a piecewise sum — each term
version contributing `its instalment × the dates elapsed under it`, each capped by **its own**
count, with the caps composing rather than one global `min()`. That is the honest answer to
audit question 6 (*exactly which outputs change*): **`expected_by_now`, and therefore `ahead`
and `overdue`, all three.** `paid` and `remaining` do not move, because they are ledger facts
and owe nothing to the schedule.

**Finding 3 — this is the real reason #8 is not a schema chore.** The entity is easy. The
projection over the entity is where the meaning lives.

## 3. The change-kind decides whether the past is re-judged

`24 × $175` becoming `18 × $233.33` is **at least three different events** wearing one shape:

| Event | What happens to the three payments already made | Past adherence |
|---|---|---|
| **Renegotiation** | they stand; new terms cover what remains | judged against $175 — unchanged |
| **Correction of the record** | the terms were *always* $233.33; we recorded them wrong | **re-judged** — the user may become retroactively behind |
| **Restructure after default** | the old agreement ended; a new one began | the old schedule's expectations *stop*; whether arrears carry forward is a further question |

Arithmetic cannot recover which of the three occurred, and each produces a different
`expected_by_now` for a date in the past. **This is gap 6's lesson at the entity level** — there,
a signed number could not distinguish payment from reversal from adjustment, so `kind` had to be
a field. Here a pair of numbers cannot distinguish renegotiation from correction from
restructure.

**Finding 4 — the precedent is already in the schema and is one value short.**
`HealthPlanOperation.kind` is `'change' | 'correction'`, with the docstring *"Collapsing these
is how a plan switch silently rewrites February."* A payment agreement needs the same field with
**at least a third value**, because a restructure is not a change of terms on a living agreement
— it is the end of one and the start of another, and modelling it as a version would keep an
agreement alive that both parties agreed was broken.

## 4. Three instruments, not one entity with a flag

§7.7 of the module design already draws this line, and it is the sharpest constraint on the
entity:

> An obligation is a **healthcare cost** when the provider carries it at no interest. It is a
> **credit card** when a lender carries it, whatever the marketing calls it, and however
> medical the purchase was.

And it names three, not two: a card, a provider plan at 0% with a term, and a **promotional
balance with a cliff date and a retroactive principal**.

**Finding 5 — a 0% provider plan and a deferred-interest promo are byte-identical as a
schedule.** Both are a start date, an instalment and a count. One is genuinely free; the other
charges interest from the purchase date, retroactively on the **original** amount, if the
balance is not zero on the cliff date — so paying 90% and missing by a month costs nearly what
paying nothing would have. The design already calls a serene *"paid off March 2028"* on one of
these **the most dangerous number this application has ever displayed**.

Therefore: whatever the entity is, **the instrument kind cannot be inferable from the schedule
and cannot be optional.** If a promo can be stored as a plan by omitting a field, it eventually
will be.

## 5. Two questions about scope that are cardinality decisions

**Finding 6 — what does one agreement cover?** Providers routinely consolidate several bills
into one plan. `healthcare_expenses.payment_agreement_id` (many expenses → one agreement)
represents that fine. What that shape **cannot** represent is one expense split across two
agreements.

Is that real? Probably rare. But the `reimbursed = true` scar is precisely this shape one level
down — a cardinality assumed because the consumer of the day did not need the other one, and
principle 2 exists because of it. Worth deciding rather than defaulting.

**Finding 7 — adherence and progress must stay two questions.** §7.8 is explicit: progress is
**dollars paid over dollars owed**, never a count of payments; adherence is the schedule; and
they diverge the moment anyone pays early. A versioned schedule changes adherence and must touch
nothing that feeds the progress bar. That is a constraint on where the entity may be read from,
not only on its columns.

**Finding 8 — and this entity is load-bearing for the cleanest attribution in the product.**
§7.8 again: everywhere else Groundwork struggles to separate deliberate action from the expected
floor, which is why `green_light` refuses to credit a balance that merely ran out on its
minimums. **A payment plan supplies that floor contractually.** Money above an agreed schedule is
provably deliberate rather than inferred to be.

Which is the strongest argument against a mutable agreement: if the schedule can be edited in
place, the baseline that made *ahead* attributable **disappears retroactively**, and every past
statement of *"you are $175 ahead"* becomes unexplainable.

## 6. The smallest shape the findings actually require

Stated as what the findings force, not as a proposal to build:

```text
payment_agreements
    identity, counterparty, opened_on, status
    instrument_kind            REQUIRED, not inferable          (finding 5)

payment_agreement_term_versions
    instalment, count, first_due
    kind  = change | correction | restructure                   (finding 4)
    supersedes_id, effective ordering, recorded ordering        (finding 1)
    reason, source

<link from expense to agreement>                                (finding 6)
```

Two notes on *smallest*:

- **The health plan needs both a term table and an operation table; this may not.** There, one
  operation can move several terms at once. An agreement's terms change atomically, so `kind`
  can sit on the version row and the second table is avoidable. That is a real simplification
  and it should be checked rather than assumed.
- **Where the promotional-balance fields live — cliff date, original principal, post-promo APR —
  is finding 5's fork and is not settled here.** On the term version, or a separate entity
  entirely. Putting them on the shared row makes them optional by construction, which is the one
  outcome finding 5 forbids.

## 7. What is a decision, and therefore not mine

1. **Does a restructure end the agreement or version it?** — finding 4. The answer decides
   whether arrears survive the boundary, and there is no derivation from existing doctrine.
2. **Where do promotional balances live?** — finding 5. The constraint is fixed (never
   optional); the placement is a choice.
3. **Can one expense belong to two agreements?** — finding 6. A cardinality, and the kind of
   thing that gets decided by accident by the first migration.
4. **Is the agreement healthcare-scoped or general?** The findings are all healthcare-sourced,
   but nothing in them is healthcare-specific — a consolidated provider plan and a consolidated
   utility arrears plan are the same object. Scoping it narrowly is defensible; scoping it
   narrowly *by accident*, because it was written in a healthcare session, is not.

**No schema should be written until 1 and 2 have answers**, because both are load-bearing on the
table layout and neither can be added later without a migration that rewrites history — which is
the thing this entity exists to make impossible.
