# The five-question reconstruction test — run against the payment model as it is

**The second ACTIONABLE NOW item from `LIFECYCLE_REVIEW_TRIAGE.md`, attacked as a diagnostic
rather than a mechanism.**

> Status: **Case set, 2026-09-11. No agreement entity, no version chain, no succession edge —
> those are M1/M2 and stay behind the carrier fence. The decision is Rob's.**
>
> The test, as the lifecycle triage set it: given an agreement change, five questions must be
> answerable **independently**, and none by consulting today's state —
>
> 1. What was expected under the old agreement?
> 2. What was actually owed?
> 3. What amount moved?
> 4. What is expected under the new agreement?
> 5. Why did the difference occur?
>
> Rob's sharpening, which makes it a diagnostic: for each question that cannot be answered,
> **name the loss** — evidence never represented · represented but projected away · an operation
> that never recorded a transition · an identity or referent not available · or a consumer
> asking for something the record never promised. And **"cannot reconstruct" is a permitted
> conclusion.** If the record legitimately never held it, inventing a reconstruction is worse
> than refusing.
>
> **Deductible decision not carried in.** This is the payment model, and the applicability axis
> is not consulted anywhere below.

---

## What the model can be asked

`core/payment_plan.py`: a `Plan` holds `gross · instalment · count · first_due` as **mutable
scalars** — no version — and a ledger of dated entries: `payment`, `reversal`, `adjustment`.
`payment_state(plan, as_of)` filters the ledger by each entry's `on`, so **owed at a date is
reconstructable**; `_instalments_due` reads the **current** scalars, so **expected at a date is
computed against whatever schedule the plan holds now.** That asymmetry is the whole test.

The history: $4,000 at 24 × $175 from January 2026; six payments January–June; restructured
1 July to 18 × $233.33 with a $50 fee capitalised. Baseline as of 30 June, before the
restructure is recorded:

```text
paid 1,050   expected 1,050   remaining 2,950   ahead 0   overdue 0
```

Then the restructure is recorded, and the questions are asked **as of 30 June** — what the
record can still say about a date that is now in the past.

---

## Path A — the caller mutates the plan to the new terms

The natural thing to do. `instalment = 233.33 · count = 18 · first_due = '2026-07-01'`, and
`record_adjustment(+50, 'restructure fee capitalised', on='2026-07-01')`.

| | as of | result | verdict |
|---|---|---|---|
| **Q1** expected under old, by June | 30 Jun | `expected = 0.00` · `ahead = 1,050` | **cannot reconstruct** |
| **Q2** actually owed at June | 30 Jun | `remaining = 2,950` | **holds** |
| **Q3** what moved | — | fee `+50, reason, on` on record; the $2,567 carry is implicit | **holds for the fee; the carry is unstated** |
| **Q4** expected under new, by Sept, no new payments | 30 Sep | `expected = 700` · `paid = 1,050` · **`ahead = 350`** | **false sentence** |
| **Q5** why | — | fee: recorded. Schedule change: nowhere | **cannot reconstruct** |

**Q1** — the June expectation was $1,050 before the restructure was recorded and is $0 after.
`_instalments_due` counts from `first_due`, which is now July, so June has no instalments due
and the user reads *$1,050 ahead* on a schedule that had not started. The old schedule is not
projected away; **it was overwritten.** Loss: **evidence never represented** — the scalars have
no history.

**Q4** — three months into the new agreement with **no payments made on it**, the state says
*$350 ahead*. The January–June payments are one undifferentiated sum in the ledger, and
`ahead = paid − expected` credits them against whichever schedule is current. Loss: **an
operation that never recorded a transition** — nothing in the ledger marks where the old
agreement's payments end and the new one's begin. This is `LIFECYCLE_REVIEW_TRIAGE.md`'s
*payment attachment across transitions* with a number on it: **money paid under one agreement
is reported as adherence to another.**

**Q5** — `Entry.reason` carries why the fee exists. Nothing carries why the schedule changed,
because the schedule change is not an entry. Loss: **never represented.**

## Path B — the caller makes a new plan and keeps the old one

`new_plan(gross=3000, instalment=233.33, count=18, first_due='2026-07-01')`, old plan retained.

| | as of | result | verdict |
|---|---|---|---|
| **Q1** expected under old, by June | 30 Jun | old plan: `expected = 1,050` | **holds** |
| **Q2** actually owed at June | 30 Jun | old plan: `remaining = 2,950` | **holds** |
| **Q3** what moved | — | new `gross` 3,000 vs old `remaining` 2,950 — **$50 derivable, recorded nowhere**; the carry is asserted by a number, not by a link | **cannot reconstruct** |
| **Q4** expected under new, by Sept | 30 Sep | new plan: `expected = 700` · `paid = 0` · `overdue = 700` | **holds** |
| **Q5** why | — | nowhere | **cannot reconstruct** |

**Q1 and Q4 hold only because the caller kept a reference.** The module does not know the two
plans are related; it holds two strangers. Loss for Q3: **an identity or referent not
available** — there is no succession edge, so *this continues that* is a fact in the caller's
head and nowhere in the record. The $50 is arithmetic between two unrelated numbers, and
arithmetic is not provenance.

---

## What the two paths show together

```text
                  Q1 old expected   Q2 owed   Q3 moved        Q4 new expected   Q5 why
Path A (mutate)   LOST              holds     fee only        FALSE (ahead 350) LOST
Path B (new)      holds*            holds     LOST            holds*            LOST
                                                              * only via a reference the module does not hold
```

**Each path preserves exactly what the other loses.** A keeps the ledger continuous and the
economic record dated — and destroys the schedule history, then misattributes six months of
payments to a schedule that had not begun. B keeps both schedules intact — and severs the
economic link, so the transfer becomes two unrelated numbers.

> **The five questions are jointly answerable only with both a schedule history and an
> economic-transfer record between the schedules. The model can hold one or the other, and
> the caller's choice of which to keep decides which false story is told.**

That is `e74d673`'s finding — *a perfect immutable version chain satisfies the first half of
the criterion and says nothing about the second* — reproduced at the code level, in both
directions. And it is the M1/M2 tension without deciding it: Path A is instrument-anchored and
Path B is agreement-anchored, and **the test does not prefer one, because each is wrong about
something the other gets right.** That is why the fence holds: the reconstruction test is
consistent with either anchoring and satisfiable by neither as the module stands.

---

## The losses, classified

| Question | Loss type | What specifically is gone |
|---|---|---|
| Q1 (A) | **never represented** | the schedule has no history; mutation is destruction |
| Q3 (B) | **identity / referent not available** | no succession link; the carry is a number, not a fact |
| Q4 (A) | **operation never recorded a transition** | the ledger has no boundary between agreements |
| Q5 (both) | **never represented** | a schedule change is not an entry and carries no reason |
| Q2 (both) | — | **holds**: adjustments are dated, and `as_of` filters them |

Two of Rob's five loss types do **not** appear, and their absence is information: nothing here
is *represented but projected away* — `payment_state` projects the ledger faithfully — and
nothing is *a consumer asking for what the record never promised*, because gap 8's two
invariants (historical schedule authority, economic transfer) promise Q1 and Q3 explicitly.
The losses are all upstream of the projection, which is the honest place for them to be.

**And "cannot reconstruct" is the right conclusion for Q1 under A and Q3 under B**, not a
failure of the test. The record never held it. A reconstruction that produced $1,050 for
June under Path A by *inferring* an old schedule from the payment pattern would be
manufacturing the very history the model failed to keep — `[-1]` for schedules.

---

## One entry for the register, held below the line

**Path A's Q4 — *$350 ahead* with no payments on the new agreement — is a false sentence of the
quarantine's kind:** plausible, coherent, every layer agreeing. It is **not reachable**:
`core/payment_plan.py` has zero consumers, deliberately, and stays that way while gap 8 is
open. So it sits with the trigger-dependent entries, with one addition to the promotion rule —
**the first consumer wired to `payment_plan` must not be able to produce it.** That is a
condition on the wiring, recorded now so it is not discovered by a user.

---

## What has not been done

No schedule version. No succession edge. No transition entry in the ledger. No inference of an
old schedule from a payment pattern. Nothing in `payment_plan.py` changed, and its zero-consumer
condition holds.

**What is Rob's:** nothing new — this test lands on the three doctrine questions already open,
and specifically on §7.7's *carries*, because which of Path A or Path B is the *right* shape is
M1/M2, and M1/M2 waits on the carrier. What the test adds is a concrete requirement either
answer must meet: **five reconstructable answers, and the fence-consistent proof that the
current model gives at most three.**
