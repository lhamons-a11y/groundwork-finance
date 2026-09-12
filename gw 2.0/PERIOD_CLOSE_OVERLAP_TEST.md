# Period close ↔ overlap — the test, run on the late-discovered mid-year change

> Status: **Doctrine test, 2026-09-12. No decision. No `close_period`, no change to
> `plan_at`, no overlap detection built.** Joint constraint 2 of three, opened on the one case
> Rob named and nothing else: **T4/T8 in `HISTORICAL_TRUTH_CASES.md`**, the late-discovered
> mid-year plan change.
>
> **Rob's two questions, kept separate:**
>
> ```text
> period close:   what historical transition must be representable?
> overlap:        what must the system say while competing effective periods remain?
> ```
>
> **And the instruction:** *test whether either answer actually forces the other. Don't assume
> the mutual arrow is vindicated merely because they're related.* The case pass
> (`DEPENDENCY_CASE_RESULTS.md`, cluster C) found the arrow one-way and conditional — 8
> constrains 7 only under represent-and-report. This test runs the four combinations against
> the case to see whether that survives, and to answer the two questions from the case rather
> than from the map.
>
> **The test, per cell (the doctrine test's shape):** what a later observer must hold to
> reproduce the current answer, the record as it stood, and a true sentence during and after
> the transition — versus what is merely context. And what the operation *records about
> itself*, since 7 is a provenance question by the case doc's own criterion.
>
> **Fence.** True concurrent coverage (primary/secondary insurance) is not this case and is not
> imported. Where a cell's answer would be different for it, the cell says so and stops.

---

## 0. The case, as recorded, and what the code does today

**T4.** A plan P is entered as Jan–Dec, deductible $3,000 (seq 1). Later (seq N) we learn:
**from July 1 the deductible is $1,000.** Expenses in March and August. The only way to express
*true going forward* is `add_plan(Jul–Dec, 1000)` — call it Q. Result: August's answer depends
on insertion order (`plan_at` returns the first plan whose period contains the date), so the
historical belief *P runs all year* wins for August because it was written down first.

**T8.** The right model is *P ended June 30*. `close_period` is named in `DELETION_MODES` and
in `delete_plan`'s docstring and does not exist; `correct_terms` cannot touch `effective_to`.
Mutating the dataclass directly gives the right current answer and rewrites the past:
`plan_at(Aug, as_of=before)` returns `None` — the record now says nothing covered August when
at that time P did.

**As built, overlap is already half-represented.** `year_summary` (`core/plan_year.py`
~L270–300) sets `deductible_met = UNKNOWN` whenever more than one period touches the year —
sequential *or* overlapping — and lists the periods beside it, with the comment *"more than
one does. Either way there is no single answer, and manufacturing one would be answering a
question nobody can ask coherently."* Only the per-date lookup, `plan_at`, resolves by
position. So the record refuses to manufacture at the year and manufactures at the date.

**The candidates, held open:**

```text
7-CLOSE   a distinct operation: "was true, and ceased at an earlier effective boundary" —
          its own provenance (effective boundary · learned seq · source), prior belief kept
7-CORR    correct_terms extended to effective_to — semantics as built: "the figure was always
          wrong", retroactive across the plan

8-REFUSE  add_plan is refused while the new period overlaps a plan on file
8-REPORT  add_plan is accepted; overlap is a recorded state; the overlapped range reports
          two claimants and UNKNOWN; the user resolves it later
```

---

## 1. The four cells

### 7-CLOSE · 8-REFUSE

Forced sequence: close P at June 30 (seq N), then add Q (seq N+1). Q cannot be entered first.

- *Current answer:* August → Q, $1,000. Correct.
- *Record as it stood:* `as_of < N` → P covers August. The close is an operation, so guarantee 1
  holds and guarantee 2 follows. **T8 repaired.**
- *Operation records:* `close(P, effective_to=June 30, learned=N, source=…)`. Kind: *ended*.
- *Sentence:* *"Your plan changed July 1. Until [date] we had the first plan running all year."*
  True.
- *Mandatory:* the close operation with both dates and a source; nothing else.
- *Context:* Q's own `add_plan` — a change, as already built.
- **Holds.** Cost: the user must assert P's end **before** the system will accept Q. In T4 the
  user knows both facts from one document, so nothing is asked that cannot be answered. Whether
  that stays true outside T4 is §3.

### 7-CLOSE · 8-REPORT

Sequence as the user meets it: add Q (seq N) — overlap now recorded; close P (seq N+1).

- *Current answer at N:* August → **two claimants, UNKNOWN.** `year_summary` already says this;
  `plan_at` would have to stop returning `[0]` and return the overlap instead.
- *Current answer at N+1:* August → Q.
- *Record as it stood:* `as_of < N` → P; `as_of = N` → P and Q both claim August; `as_of ≥ N+1`
  → Q. **All three reproducible**, and the middle one is a state the record has to be able to
  hold — that is what 8-REPORT costs.
- *Operation records:* the close at N+1 records *P ended June 30, effective; learned N+1* — but
  the **evidence** arrived at N (Q's document said July 1). So the close has a *learned* time
  after the evidence's *recorded* time, and it has to say **which competing claim it resolved
  and how** — *P ended* (Q governs August) rather than *Q was mis-entered* (P governs). That is
  the third provenance kind the case pass predicted: **resolution of an ambiguity**, neither
  *was always wrong* nor merely *ended*, because it names a state that existed and closes it.
- *Sentence during:* *"Two plans claim August; Groundwork cannot establish which governed."*
  *Sentence after:* *"Your plan changed July 1; between [N] and [N+1] both were on file."* Both
  true.
- *Mandatory:* the overlap state as a reproducible record state; the close with both dates, a
  source, **and the claim it resolved**.
- *Context:* the interval length, which is a fact about the household's data entry, not their
  coverage.
- **Holds**, with the larger provenance vocabulary. And it is the shape the record already has
  at the year level.

### 7-CORR · 8-REFUSE

Forced sequence: correct P's `effective_to` to June 30 (seq N), then add Q.

- *Current answer:* August → Q. Correct.
- *Record as it stood:* `as_of < N` → P Jan–Dec. Reproducible, because the correction is an
  operation. Guarantee 2 holds.
- *Operation records:* `correction(P, effective_to: Dec 31 → June 30)`. Kind, as built: **the
  figure was always wrong** — P was always Jan–Jun.
- *Sentence:* *"We had your plan's end date wrong; it was always June 30."*
- **Holds on arithmetic; the sentence is false on T4 as written.** T4 is a plan that *changed*
  July 1 — P was in force Jan–Jun and the annual entry was correct when made. A correction
  asserts the entry was erroneous. That is a statement about the household's record-keeping,
  and it is not what happened. `HISTORICAL_TRUTH_CASES.md` posed exactly this as 7's deciding
  criterion — *whether "period ended earlier" has different provenance and history semantics
  from `correct_terms`* — and on this case it does: **the current answers are identical and the
  provenance sentences contradict each other.**
- *Mandatory* under 7-CORR to say a true sentence: a way to mark this correction as *not an
  error* — which is 7-CLOSE wearing a correction's name.

### 7-CORR · 8-REPORT

Add Q (seq N), overlap recorded; correct P's end (seq N+1).

- As 7-CLOSE·8-REPORT for the state, plus 7-CORR's sentence: the overlap is resolved *as an
  error that never really existed* — P was always Jan–Jun, so the overlap was an artefact of a
  wrong entry. On T4 that is the false sentence again, now attached to the resolution as well.
- *Coherent* — it is what a genuine data-entry error looks like when discovered after Q is
  entered. *False on T4.*
- **Holds structurally; wrong provenance on this case.**

---

## 2. Result

| | 8-REFUSE | 8-REPORT |
|---|---|---|
| **7-CLOSE** | holds; user asserts the end before the system accepts the change | holds; needs the overlap state + a third provenance kind (*resolved which claim*) |
| **7-CORR** | arithmetic holds; provenance sentence false on T4 | same, and the false sentence attaches to the resolution too |

**Rob's two questions, answered from the case.**

> **Period close — the transition that must be representable:** *this was true, and ceased to
> be true at an effective boundary earlier than the record shows, learned later* — with the
> prior belief preserved, both dates, a source, and **distinguishable from "the entry was always
> wrong."** The case forces the *distinction*, not the number of verbs: a late-discovered
> mid-year change and a late-discovered entry error have identical arithmetic and opposite
> provenance sentences, and the record must be able to say which it holds.

> **Overlap — what the system must say while competing periods remain:** *two plans claim
> [range]; Groundwork cannot establish which governed* — the overlapped range attributes to
> neither, `deductible_met` is `UNKNOWN`, both claimants are named, and position never decides.
> `year_summary` already says this. `plan_at` does not.

**Does either answer force the other?**

- **7 → 8: no, confirmed.** Both shapes of 7 sit under both answers to 8. 7's own deciding
  criterion (provenance semantics of *ended* vs *always wrong*) never mentions overlap, and the
  test shows it decided by the *sentence*, not by whether Q was entered first.
- **8 → 7: yes, under one answer, confirmed.** 8-REPORT puts a state in the record that 7 must
  then *close as a resolution* — naming which claim won — and that is a provenance kind
  8-REFUSE never needs. The case pass's one-way, branch-conditional arrow survives the test
  unchanged.

**What the test adds beyond the arrow.** 7-CORR fails the case on its sentence. Not because
corrections are wrong — a late-discovered *entry error* is exactly a correction — but because
T4 is not one, and a model with only `correct_terms` semantics has to describe a change in the
world as a mistake by the household. That is the M-LED shape from the §7.7 test: right
description, false implication. **The case is evidence for 7-CLOSE as a distinct provenance,
and it is evidence only** — it does not say whether that is a second operation or a kind on
one.

---

## 3. What the test does not prove

1. **That 8-REFUSE is safe outside T4.** In T4 the user learns *Q from July 1* and *P ended
   June 30* from one document, so refusing Q until P is closed asks for nothing the user does
   not have. A user who knows Q exists and does **not** know whether P ended — the case doc's
   own *"two plans claim coverage for August, and Groundwork cannot establish which one
   governed"* — is asked by 8-REFUSE to assert a conclusion in order to record an observation.
   The surface principle (*ask for evidence, never for conclusions the user cannot know*) and
   C9's precedent point at 8-REPORT there. **That user is adjacent to T4 and not in it**; the
   evidence is noted, not admitted.
2. **Anything about true concurrent coverage.** Primary/secondary insurance is a *real* overlap
   with a *real* answer (both govern, in order). Neither 8 answer as framed here represents it;
   8-REFUSE forbids it and 8-REPORT calls it unresolved. Outside the fence, and the reason
   neither answer should be adopted as "overlap policy" without a case that has it.
3. **Whether 7-CLOSE is one operation or a kind.** The case forces the record to distinguish
   *ended* from *always wrong*; `HealthPlanOperation.kind` being "one value short" (the gap-8
   remark) is one way to hold that and the test does not choose it.
4. **That `plan_at` should return the overlap.** Something has to stop it returning `[0]`; what
   it returns instead — the set, a refusal, `UNKNOWN` — is a consumer question, not decided by
   the case.

---

## 4. Decision remaining — Rob's

7 and 8, as before, with the case's contribution narrower than an answer: **the transition 7
must represent is now stated, and it is not a correction; the sentence 8 must say during
overlap is now stated, and the year-level record already says it.** 8-REPORT costs one
provenance kind; 8-REFUSE costs asking, in the adjacent case, for a conclusion the user may
not hold. Neither cost is decided here.

---

## 5. Ruling — Rob, 2026-09-12. Constraint 2 closed, with one asymmetry.

**8 = represent-and-report.** Not because reporting is more convenient: because *the thing
being observed and the thing being resolved are different facts.* If Groundwork has evidence
that Q claims coverage from July 1 while it cannot establish whether P ended June 30, it has
learned something real. Refusing to record Q until the user can prove which plan governed would
turn **uncertainty about resolution into absence of evidence** — the discipline preserved
everywhere else: *Unknown is a valid state; uncertainty is not permission to manufacture an
answer.* So the record must be able to say:

```text
Q claims [July 1 → …]
P claims [… → …]
governing plan:   UNKNOWN
deductible_met:   UNKNOWN
```

No position-based winner. No invented coverage. No forced user conclusion.

**7 — frozen from the case's narrower result:**

> **A late-discovered effective change is not semantically equivalent to a correction of an
> always-wrong record.** Strong enough to be a provenance requirement. The information is not
> *old value · new value*; it is *what was believed · what actually became true · when the truth
> changed · when Groundwork learned it · why the record now knows.* Those let the observer
> distinguish *"our belief was correct until June 30; reality changed July 1"* from *"our
> June 30 record was wrong when we entered it"* — materially different historical statements.

**8 → 7, accepted as the case implies:** REPORT requires 7 to represent a close/resolution
whose semantics distinguish *this period ended* from *this record was always wrong*, and, where
applicable, **identify which competing claim was resolved.** Whether that is
`HealthPlanOperation.kind = CLOSED / RESOLVED`, a separate operation, or another representation
is implementation design; the doctrine requires only the semantic distinction.

**Recorded:**

```text
7        period close must be representable as a late-discovered real-world transition,
         distinct from correction
8        represent-and-report governs unresolved competing claims in this case; overlapping
         claims stay explicitly unresolved, never position-resolved
7 → 8    no dependency
8 → 7    conditional dependency — REPORT requires 7's provenance to distinguish resolution
         of competing claims from correction
```

**Explicitly NOT generalised — three materially different states, and this case establishes
only B:**

```text
A.  one plan governs
B.  competing claims exist, governing plan UNKNOWN          ← this case
C.  multiple plans genuinely govern (primary + secondary)   ← fenced, undecided
```

**`plan_at()` fenced.** The doctrine establishes that the record cannot silently resolve B by
list position. It does not dictate whether `plan_at()` returns a set, `UNKNOWN`, an explicit
ambiguity object, or refuses the query — a consumer question.

### Consequence noted, not a further decision

With 8 ruled, the conditional on 7 has fired. 7 now carries **three** distinguishable
provenances, from two different sources of requirement: *always wrong* (built), *ended* (T4's
sentence, unconditional), *resolved — which claim* (REPORT). And *governing plan* becomes a
fact **derived on read from the claims**, never stored — B is what derivation reports when it
finds two claimants — which is the module's existing pattern (accumulators, `resolution()`) and
the one-owner-per-fact rule arriving where it was needed.
