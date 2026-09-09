# Payment agreements — the semantics the schema will have to preserve

**Gap 8, decisions 1 and 2 — posed, not answered**

> Status: **DECISION RECORD. No schema is proposed and none should be written.** Written
> 2026-09-09 at Rob's direction, after the inspection in
> `gw 2.0/PAYMENT_AGREEMENT_INSPECTION.md`:
>
> > *"Don't design the tables from decisions 1–4 all at once… Don't decide the schema because it
> > is convenient. Decide the semantics the schema must preserve, then derive the schema."*
>
> 8.1 and 8.2 come first because they are the two most likely to force a later migration if
> guessed. 8.3 (cardinality) and 8.4 (domain scope) are deliberately not in this document.

---

## 0. Two things that are settled before either question

### The instrument-kind requirement

Rob, 2026-09-09, as a hard domain requirement rather than a preference:

> **Instrument kind is explicit source data, not a value inferred from schedule shape.**

The inventory's most dangerous sentence is that **a 0% provider plan and a deferred-interest
promo are byte-identical as a schedule.** A schedule can tell you `$500/month · 6 months ·
$3,000 expected`. It cannot tell you *why that schedule exists* or *what financial consequence
attaches to it* — and one of those two instruments charges retroactive interest on the original
principal if the balance is not zero on a date the schedule does not contain.

**This is #15's first shall-not at the schema level.** `agreement ≠ evidence`: structural
consistency must not manufacture semantic evidence. A schedule that parses cleanly, reconciles
against its ledger and matches its instalments has proved nothing whatsoever about which
instrument it is. Inferring the kind from the shape would be the pipeline agreeing with itself
and calling that a fact.

**Consequence for any schema derived from this document:** the kind is `NOT NULL`, has no
default, and is never computed.

### The zero-consumer condition, and its expiry

`core/payment_plan.py` is imported by its own fixture and `smoke_sections/s99_payment_state.py`,
and by nothing in `server.py`. That is an unusually valuable position — **the model can be made
right before compatibility constraints start dictating it** — and it is a wasting asset. It ends
the moment the healthcare module is wired.

**Recorded as a deliberate condition:** no consumer is added to `payment_plan.py` while 8.1 and
8.2 are open.

---

## 1. Decision 8.1 — restructure

**Not** *"does a restructure create a new version?"* That is a table question, and answering it
first lets the table decide the meaning. The semantic question, in Rob's wording:

> **After a restructure, is the pre-restructure expected schedule still historically
> authoritative for dates before the restructure?**

### The three answers, and what each forces

**A — Yes, and it keeps accruing conceptually.** `expected_by_now('2026-03')` returns today
exactly what it returned in March, forever. Adherence history is immutable, the restructure is a
boundary rather than an erasure, and a user who was $525 behind in March is still $525 behind in
March.

*Forces:* the old terms stay queryable **with their span** — the fold has to know when each
version stopped applying, which is a column the point-lookup precedents
(`HealthPlanTermVersion`) do not have. Whether that lives as one agreement with versions or two
linked agreements becomes nearly free once the span boundary is recorded.

**B — No, the restructure supersedes and prior expectations are void.** Only current terms are
authoritative; earlier adherence is not reportable, or is reportable only as *"under a prior
agreement"* with no figures.

*Forces:* the simplest current view and **no historical narration at all**. It also contradicts
the `as_of` reproducibility the entire healthcare module was built on, and would be the first
place in Groundwork where a past answer becomes unavailable rather than merely superseded. Worth
stating as a position because rejecting it should be a decision, not an omission.

**C — Yes, but closed.** The old schedule remains authoritative for its own span and **stops
accruing expectation** at the boundary. Its final position is frozen as a fact — *"$525 short at
close"* — and that fact is then separately either carried into the new agreement or not.

*Forces:* a closing state on the version, and an explicit answer to the arrears question below.

### The question hiding underneath, and the reason C exists

A restructure very often happens **because** the person fell behind, and the arrears are rolled
into the new principal. So:

> **Does being behind under the old schedule survive the boundary as a debt, as a fact, as
> both, or as neither?**

If the old schedule stays authoritative **and** the arrears are also inside the new principal,
then a naive sum double-counts them. This is §7.8's separation — progress is dollars over
dollars, adherence is the schedule — arriving at the entity boundary and needing to be honoured
there.

**The derived requirement, whichever of A/B/C is chosen:** *whether the old schedule remains
authoritative* and *whether arrears cross the boundary* are **two facts, and must be recorded
separately.** Collapsing them is exactly how the double-count enters, and it is the same shape
as every collapse this review has found — a single field standing in for two independent
questions.

### The two invariants this splits into

*(Rob, 2026-09-09 — to be stated before schema work, not after.)*

> **8.1-a · Historical schedule authority.** What expectations applied before the restructure
> remains reconstructable.
>
> **8.1-b · Economic transfer.** Any amount incorporated into the new principal has a
> **traceable disposition** from the old agreement.

**The second is the one that would otherwise be missed**, and the reason is worth stating
plainly: *the system can preserve history perfectly and still double-count the economics.*
8.1-a is satisfied by an immutable version chain — which every precedent in this repository
already provides, and which would make the gap look closed. It says nothing about whether the
$525 that was short in March is now *also* sitting inside the new principal.

The failure that 8.1-b prevents has two directions, and only one of them is the obvious one:

- **Double-count** — the arrears are inside the new balance *and* still owed under the old
  schedule, so the same dollars are counted twice.
- **Silent erasure** — the new balance quietly stands in for the old obligation, and the
  historical payment obligation disappears into a number nobody can decompose.

Both are prevented by the same requirement: **every dollar that crossed the boundary can be
traced to what it was before it crossed.** Not merely *that* arrears were carried — which
amount, from which schedule, resolved how.

---

## 2. Decision 8.2 — promotional-balance ownership

**Not** *"which table do the promo columns go in?"* The semantic question, in Rob's wording:

> **What historical fact needs to remain independently reconstructable?**

### The candidate answer

A promotional balance's distinguishing fact is not its schedule. It is a **conditional
counterfactual, available at every date before the cliff**:

> *If this stops here, what happens?*

Answering that at an arbitrary past date requires three things as they stood **at that date**:
the **original principal** (not the remaining balance — that is the whole trap), the **cliff
date**, and the **post-promotional APR**. A 0% provider plan has no such counterfactual; its
answer is *nothing happens*, and that is not the same answer arrived at differently, it is the
absence of the question.

### What that forces, if it is the right reading

**The three facts need their own version chain.** The original principal is correctable — we
recorded $3,000 and the statement says $2,958 — and a correction there **retroactively changes
every counterfactual ever computed**, which is precisely the situation `supersedes_id` exists
for. That is a versioning requirement independent of the schedule's own versioning, and the two
do not change together.

**Optional columns on a generic term row cannot express it.** Three nullable columns that must
never be null for one kind and always null for the other is a constraint the database cannot
state and the code will eventually violate — and per §0 above, the one outcome forbidden is a
promo that can be stored as a plan by omitting a field.

**And the cliff date is not a term at all — it is an alarm source.** §7.4's urgent tier is
defined as *an external deadline whose consequence compounds if it passes*, and the design says
few things in personal finance fit that sentence better. A field consulted by the alarm layer,
on its own clock, sitting in a nullable column of a schedule row is a misfiling with
consequences.

**Rob's formulation, which is the cleanest statement of why they cannot share a row:**

```text
schedule   →  What was expected by date X?
cliff      →  What financial consequence occurs if condition Y is still true when X arrives?
```

**Two different temporal mechanisms.** One integrates over elapsed time and produces an
expectation; the other is a conditional evaluated at an instant and produces a consequence. They
share a date column and nothing else. Treating the cliff as another schedule term would make the
model **deceptively uniform** — the most expensive kind of tidiness, because uniformity that
hides a semantic difference is indistinguishable from uniformity that reflects one.

### The test that decides the placement

> **Can an agreement change from promotional to non-promotional, or the reverse?**

If **no** — a CareCredit promo does not become a provider plan; it only ever *expires*, which is
the instrument doing what it always was — then kind is immutable per agreement and belongs to
the agreement, with the promotional facts owned by their own versioned entity beside it.

If **yes**, in some real refinancing case not yet considered, then kind is itself a versioned
term and the whole shape changes.

**I have not answered this**, because the answer is a claim about how these instruments behave
in the world rather than about the repository, and the evidence for it is Rob's rather than
mine. The reasoning above is what the two answers would force.

---

## 2a. The instrument-kind transition question — the one open item

*(Rob, 2026-09-09: settle this before any further schema decision. **And do not choose A merely
because it produces a cleaner schema.**)*

### The two worlds

**A — kind is immutable.** The agreement's identity *is* its instrument. A promo does not become
a provider plan; it **expires**, which is the instrument doing what it always was.

```text
agreement (kind = deferred_interest_promo)
    ├── term versions
    └── expiration            ← a terminal state, not a change of kind
```

**B — kind can change.** Then the transition needs explicit semantics, and **the transition
itself becomes historical evidence** — a dated, sourced, versioned fact about the agreement, not
a column edit.

```text
agreement
    ├── kind = promo                    [until …]
    └── kind = ordinary_provider_plan   [from …]
```

### The scenarios that would decide it

Each of these is a real-world claim Rob can rule in or out. They are listed because *the
question is not answerable in the abstract* — it is answerable by whether any of these happens.

| # | Scenario | Reading |
|---|---|---|
| 1 | **Promo reaches its cliff**; retroactive interest lands; the balance revolves at ~30% | Terminal state of the same instrument, **or** the agreement ending and a card balance beginning. The single most likely decisive case. |
| 2 | **The provider sells or assigns the debt** to a lender or agency | See below — this one is not neutral. |
| 3 | Provider plan **refinanced onto CareCredit** at the office | Almost certainly a *new* agreement paying off the old, not a transition |
| 4 | Several plans **consolidated** into one | 8.3's cardinality question, not this one |
| 5 | A provider plan that **charges interest** from the start | A third instrument, not a transition |

### Scenario 2 is the one that makes this hard, and it links 8.2 back to 8.1

§7.7's classification rule keys on **who carries the obligation**:

> An obligation is a **healthcare cost** when the provider carries it at no interest. It is a
> **credit card** when a lender carries it, whatever the marketing calls it.

**Who carries it can change without the user doing anything.** Medical debt is sold and assigned
routinely. So under §7.7's own rule, the instrument kind of an unchanged agreement can change by
an act of a third party the user never signed anything for.

That leaves exactly two consistent readings, and **both of them reach into 8.1**:

- **Kind is mutable** (world B), and a sale is a kind transition on a surviving agreement.
- **Kind is immutable** (world A), and a sale therefore *ends* the agreement and begins another
  — which is **8.1's restructure question**, arrived at from the opposite direction, with the
  same arrears-disposition problem attached.

**Finding: 8.1 and 8.2 are not independent.** They were listed as separate decisions in the
inspection and that was wrong. Whatever answers *does a restructure end the agreement or version
it* also constrains *can an agreement change instrument kind*, because a sale is simultaneously
a candidate for both. Deciding them in separate sittings risks two answers that cannot both
hold.

**What is not in doubt either way:** a sale is not a silent event. Whichever structure carries
it, it is dated, sourced, and reconstructable — the user must be able to see that the thing they
owe changed hands, and when.

---

## 3. What must be true before any table is written

1. **The instrument-kind transition question answered first** (§2a) — because scenario 2 shows
   it constrains 8.1 rather than sitting beside it.
2. **8.1 answered** as A, B or C — *and* invariants 8.1-a and 8.1-b both stated, since the first
   can be satisfied while the second is silently violated.
3. **8.2 answered**, with the promotional facts' reconstructability requirement settled either
   way.
4. **Instrument kind stays explicit** — `NOT NULL`, no default, never computed. Settled above.
5. **Zero consumers preserved** until the above are done.

8.3 (can one expense belong to two agreements) and 8.4 (healthcare-scoped or general) remain
open and are deliberately downstream: both are easier to answer once the temporal semantics
above are fixed, and neither is migration-sensitive in the same way.

> **The method, recorded because it was corrected into shape:** decide the semantics the schema
> must preserve, then derive the schema. Not the reverse, and not both at once — a table drafted
> alongside its meaning will quietly settle the meaning, because the table is the more concrete
> of the two and concreteness wins arguments it has not earned.
