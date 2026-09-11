# Historical truth versus current truth — the invariant, and where it leaks

**Gap 2, attacked with a temporal matrix on one plan-year value, mutating insertion order and
observation timing.**

> Status: **Case set, 2026-09-11. No change to `plan_year`. The invariant is stated; the leak is
> named; the repair is Rob's.**
>
> `HEALTHCARE_GAP_TRIAGE.md` gap 2 recorded that every module takes `as_of` and reproduces the
> earlier answer — the mechanism is thorough — and that **the invariant is nowhere stated as
> such.** `USER_KNOWLEDGE_CASES.md` U7 gave it an instance: a March statement read in September.
>
> Rob's sharpening of the question, which is what the matrix tests:
>
> > **Can a historical observation change what the module reports as current, merely because it
> > is more recent, more complete, or otherwise wins the same resolution path?**
>
> And the specific separation to keep: **effective date** (when it was true) from **recorded
> date** (when we learned it). *We learned yesterday that the deductible was $1,000 effective
> January 1* is a historical fact discovered yesterday, not a January fact that became current
> yesterday.

---

## The invariant, stated

> **A historical conclusion is an immutable representation of the knowledge available at the
> point it was drawn. A current conclusion may be superseded by later evidence. Both are true
> at once, and a reader must always be able to tell which one they are holding.**

Which decomposes into what a module has to guarantee:

1. every change to the record is itself recorded, with when it took effect and when it was
   learned;
2. `as_of` reproduces exactly what the record said at that point — including its gaps;
3. the current answer is a function of the whole record and of effective dates, **never of the
   order things were written down.**

`plan_year` holds the first two for everything its API can express. The matrix found the one
fact its API cannot express, and there the third fails.

---

## The temporal model, as built

```text
effective time     Plan.effective_from / effective_to, and expense dates       (calendar)
recorded time      TermVersion.seq, Operation.seq, `as_of`                    (a counter, not a clock)
```

Two axes, kept apart, and `plan_at(when, as_of)` takes one of each — *the plan in force on a
date, as the record stood at a point.* That is the right shape. Terms carry **no** effective
date of their own: a `TermVersion` is true for the whole plan period, so a correction is
retroactive across it by design, and *change going forward* is expressed as a new plan.

---

## The matrix

### T1 — current fact only

One plan, Jan–Dec, deductible $3,000. March → $3,000. Baseline.

### T2 — historical → current correction, and `as_of` reproduces it

Correct to $2,000 at seq 2. `as_of = 1` → $3,000. Now → $2,000, for the whole period.
**Holds**, and the retroactivity is the documented meaning of *correction*: the figure was
always wrong.

### T3 — current → historical insertion: an earlier plan discovered late

Plan B (Jul–Dec) entered first; expenses in March and August. March is `unattributed: 400`.
Then Plan A (Jan–Jun) is entered. March attributes to A; two periods; `met = UNKNOWN`.

```text
as_of before A reproduces the old answer:   True
```

**Holds.** Late-arriving plan data is first class, and the record as it stood still says what it
said. This is the case the module was built for and it passes it.

### T5 — same fact, different seq

Correct $3,000 to $3,000. Terms unchanged; operations gain a `correction`. Date is part of the
record, not merely metadata, and it changes nothing it should not. **Holds.**

### T4 — the adversarial case: a mid-year change discovered late

A plan was entered as Jan–Dec, deductible $3,000. Later we learn: **from July 1 the deductible
is $1,000.** The only way to express *true going forward* is `add_plan(Jul–Dec, 1000)`.

```text
Jan–Dec entered first, then Jul–Dec:     August → $3,000    plan_at(Aug) = "entered as full year"
Jul–Dec entered first, then Jan–Dec:     August → $1,000    plan_at(Aug) = "from Jul, ded 1000"
```

**The current answer depends on insertion order.** `plan_at` returns the first plan in the
registry whose period contains the date, and the historical observation — *we thought it ran all
year* — was recorded first, so it wins for August. **A historical observation changes what is
reported as current, merely because it was written down earlier.** That is the leak, and it is
`[0]` where the other three were `[-1]`: position again, from the other end.

### T8 — why T4 has no correct move: the period cannot be corrected

The right model for T4 is *the first plan ended June 30* — shorten its period, then add the
July plan. The module names that operation:

```text
DELETION_MODES = ('close_period', 'delete_if_unused')
delete_plan():   "...the caller is expected to offer `close_period` instead."
hasattr(plan_year, 'close_period')  →  False
```

**`close_period` is named twice and does not exist.** `correct_terms` corrects deductible and
out-of-pocket; it cannot touch `effective_to`. So the period is the one fact about a plan with
**no correction path through the API.**

The only way is to mutate the dataclass directly. That produces the right current answer and
breaks the invariant:

```text
full3.effective_to = '2026-06-30'          then add the Jul plan
August → $1,000                            correct
operations recorded for the shortening:    none  (the 'change' is the Jul plan's own)
plan_at(Aug, as_of = before the shortening) → None
```

**The record as it stood before the shortening now says nothing covered August** — when at that
time, the full-year plan did. The unrecorded mutation rewrites the past. Guarantee 2 fails,
because guarantee 1 was bypassed, because the API offered no way to honour it.

### T6 — no `as_of` supplied

`terms_at(plan)` returns the last-recorded version. Terms have no effective date, so
*latest-recorded* is the only notion of *current* the module has for terms, and it is the right
one. For plans, *current* is `plan_at(when)` with no `as_of` — first match by insertion order,
which is T4.

### T7 — effective versus recorded

*Learned at seq 5 that the deductible was $1,000 effective January 1.* → `correct_terms` at seq 5.
`as_of = 4` → old value; `as_of = 5` → $1,000 across the plan. **Holds** — because the effective
scope of a term is the plan's whole period, and that is what a correction says. The case that
does not hold is *$1,000 effective January 1 **until June 30***, which is T4: the effective
scope is narrower than the plan, and the module cannot say so.

---

## The leak, named precisely

Not in `as_of`. `as_of` reproduces everything the record contains, and T2, T3, T5 and T7 show it
doing so. The leak is one layer up:

> **The period of a plan is the only fact the API cannot correct. A late-discovered mid-year
> change therefore has two moves, and each breaks one half of the invariant:** leave the periods
> overlapping and let insertion order pick the current plan (T4 — wrong current), or mutate the
> period directly and lose the record of what was believed before (T8 — wrong history).

And the missing operation is not *change* and not *correction* as the module defines them:

```text
change        what is true going forward             add_plan
correction    what was always true                   correct_terms
—             what was true, and stopped being true  earlier than we recorded    ← absent
```

Which is the gap-8 inspection's remark about `HealthPlanOperation.kind` being *one value short*,
arriving with the value named: **a period close is a correction to when something stopped being
true**, and it is representable by neither operation the module has.

---

## Requirements — and the one sentence each permits

| Requirement | Permits |
|---|---|
| a plan's period is correctable through the API, and the correction is an operation | *your PPO ended June 30; we had it running all year* |
| the current plan for a date is a function of effective dates, never of insertion order | *in August you were on the July plan* — regardless of which was entered first |
| `as_of` reproduces the record's view of periods, not only of terms | *in March we believed the PPO ran all year; that is what we told you then* |
| overlapping periods are a detectable state, not a silent tie broken by position | *two plans claim August; which one was it?* |

**And the invariant, once, so it is somewhere:** *a historical conclusion is an immutable
representation of the knowledge available then; a current conclusion may be superseded; every
change to the record is itself recorded; and the current answer never depends on the order the
record was written.*

---

## What has not been done

No `close_period`. No `correct_period`. No change to `plan_at`'s first-match. No overlap
detection. The direct mutation in T8 was performed in a scratch registry and nowhere else.

**What is Rob's:** whether a period close is a third operation kind or a correction with a
narrower target; and whether overlapping periods are an error the API refuses, or a state it
records and reports as ambiguous — the same choice `allocation.state()` made by asking the caller
rather than deriving.

**Next, per the sequence:** gap 14 — the general rule for naming external actions.
