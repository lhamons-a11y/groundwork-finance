# Concurrent coverage — is "unresolved" the right word when both plans really govern?

> Status: **Case set, 2026-09-12. Evidence mode — the last writable fence. No decision, no
> primary/secondary semantics, no claim allocation, no change to `plan_at()`, no deductible
> projection, no representation.** Rob's one question:
>
> > **Does the represent-and-report rule for unresolved overlap still hold when two plans
> > genuinely govern the same period concurrently, rather than when Groundwork simply cannot
> > determine which plan governed?**
>
> **The ruled rule** (`PERIOD_CLOSE_OVERLAP_TEST.md` §5), for state B:
>
> ```text
> unknown which plan governed  →  overlapped range attributes to neither
>                                 deductible_met → UNKNOWN
>                                 both claimants named
> ```
>
> and the three states the ruling named, establishing B and fencing C:
>
> ```text
> A.  one plan governs
> B.  competing claims exist, governing plan UNKNOWN
> C.  multiple plans genuinely govern (primary + secondary)
> ```
>
> **The test:** for each case, what is true, what the ruled rule would *say*, and whether that
> sentence is true. If the B-sentence is false of C, concurrency is a distinct state and the
> rule must distinguish it. If it is true, the rule stands and C needs nothing.
>
> **As built** (`core/plan_year.py`): `plan_at(when)` returns the **first** plan whose period
> contains the date; `year_summary` sets `deductible_met = UNKNOWN` whenever **more than one
> period** touches the year — with the comment *"no plan covers it, or more than one does.
> Either way there is no single answer."*

---

## Case CC1 — A and B genuinely concurrent, both applicable

The user is covered by their own plan A and their spouse's plan B for all of 2026.
An August expense of $600: A processes it first and applies $400 to A's deductible; B
processes the remainder and applies $150 to B's deductible. Each insurer issues an EOB.

- **What is true:** both plans govern August. The expense counts **$400 toward A** and **$150
  toward B**. Neither figure is unknown; each is stated by the plan that applied it.
- **What the B-rule would say:** *"two plans claim August; Groundwork cannot establish which
  governed"* → attributes to **neither**, `met = UNKNOWN`.
- **Is that sentence true?** **No.** Groundwork *can* establish which governed: **both**, and
  it can establish exactly how, from the two EOBs. *Cannot establish* is false; *neither* is
  false. The only true part is *two plans*.
- **What `plan_at` does:** returns A. **Wrong, but differently from B.** In B there is no right
  answer and `[0]` invents one. In CC1 there is a right answer with two values and `[0]`
  returns half of it.

**Forces finding 1.** Concurrency is **not unresolved.** It is a **determinate,
multi-valued attribution** — each plan is the knowing party for what it applied, and each
plan's EOB establishes it. The B-rule's sentence is false of it. **C is a distinct state.**

## Case CC2 — A primary, B secondary

CC1 with the order stated: A pays first by coordination-of-benefits rules.

- **What is true:** as CC1, plus an ordering that determines the *amounts* ($400 then $150
  rather than some other split).
- **For the state question:** still C. The order is an attribute *of* concurrency — it shapes
  the split, not whether both apply. What the record must be able to hold is *both apply, in
  this order*; how the order produces the split is claim allocation and is **fenced**.

**Forces finding 2.** Priority is a property **inside** C, not a fourth state. Concurrency
without a known order is still concurrency (CC3).

## Case CC3 — both plans claim primary; Groundwork cannot establish priority

Two EOBs, each processed as if primary; the household does not know which coordination rule
applies.

- **What is true:** both plans govern (C). Which paid first — and therefore what each *should*
  have applied — is **unknown**.
- **Two different unknowns, and they must not be merged:**

  ```text
  B      unknown WHICH plan governs           attribution unresolved
  CC3    known BOTH govern; unknown ORDER     attribution determinate; priority unresolved
  ```

- **What the B-rule would say:** *cannot establish which governed* — **false**: it can, both.
  What it cannot establish is priority, which is a different fact.
- **What the record can say:** *"two plans covered August; both apply to this expense; which
  paid first is not established."* Every clause true. The represent-and-report *discipline*
  — name the claimants, manufacture nothing — applies to the **priority** sub-fact, exactly as
  it applies to attribution in B.

**Forces finding 3.** Concurrency and unresolvedness are **orthogonal.** A record can be in C
with an unresolved sub-fact; that is not B, and collapsing it into B loses the determinate
part (both apply) to report the unresolved part (order). *Unresolved* is a property of a
specific fact, not of the period.

## Case CC4 — periods overlap; only one plan applies to this obligation

Medical plan A and dental plan B, both active all year. An August **dental** expense.

- **What is true:** two plans are *active* in August. **One applies** to this expense — B.
  A's rule exists and this expense falls *outside* it (`APPLICABILITY_CASES.md`: *negative /
  not covered — the rule exists; this falls outside*, established).
- **What the B-rule would say:** *two plans claim August; cannot establish which governed* →
  neither, `UNKNOWN`. **False twice over**: only one claims *this expense*, and which one is
  established.
- **What went wrong:** the overlap rule was written about **periods**; applicability is
  **per expense**. Period overlap is *necessary* for an attribution question to arise and
  *not sufficient* — the applicability axis has to be consulted first, per expense, and where
  it resolves the question there is no overlap left to report.

**Forces finding 4.** **Period overlap ≠ applicability overlap.** The represent-and-report
rule fires only where two plans' rules both *include* the expense (or where inclusion cannot
be determined). Where the applicability axis excludes one plan, the state is **A** for that
expense, whatever the periods say.

## Case CC5 — A ends June 30, B begins July 1

The ordinary transition. T3/T4's world, with the close done correctly.

- **What is true:** state A throughout — one plan per date. No overlap of periods.
- **What `year_summary` does today:** two periods touch the year → `met = UNKNOWN`. T3
  documented this: *"two periods; met = UNKNOWN."*
- **Is that the B-rule?** No — no claims compete. It is a **third thing** the same `UNKNOWN`
  is carrying: *the year-level question has no single answer because the year had two plans
  in sequence, each with its own deductible.* True, and not overlap, and not concurrency.

**Forces finding 5 — a measured finding about shipped code.** The built year-level `UNKNOWN`
is currently doing **three jobs**: B (competing claims, unresolved), C (both govern,
determinate), and *sequential periods* (no single year-level figure). Its own comment says as
much — *"no plan covers it, or more than one does. Either way there is no single answer"* —
and *more than one does* is B, C and CC5 at once. Not a defect on the default path (it refuses
rather than manufactures), but the refusal reads three different situations as one word.

---

## What the cases force

1. **Concurrency is a distinct state, not unresolved** (CC1). Both plans govern; each is the
   knowing party for what it applied; attribution is determinate and multi-valued. The
   B-sentence is false of it.
2. **Priority is a property inside C** (CC2), not a fourth state; how it produces the split is
   claim allocation, fenced.
3. **Concurrency and unresolvedness are orthogonal** (CC3). C can carry an unresolved
   sub-fact (priority). The represent-and-report discipline applies to *that fact*, not to the
   period. Two unknowns — *which* vs *in what order* — must not be merged.
4. **Period overlap ≠ applicability overlap** (CC4). Overlap of periods is necessary, not
   sufficient; the applicability axis is consulted per expense first, and where it excludes a
   plan the state is A.
5. **The built `UNKNOWN` conflates three situations** (CC5): B, C, and sequential periods. A
   refusal, correctly, and an uninformative one.

---

## The fence's question, answered by the cases — not ruled

> *Does represent-and-report still hold when two plans genuinely govern concurrently?*

**The rule holds for what it was ruled for, and concurrency is not that.** Represent-and-report
governs **unresolved competing claims** — B, and the unresolved *priority* inside CC3. Genuine
concurrency (C) is **not a competing claim**: both plans apply, each says what it applied, and
the record's true sentence is *"both, $X to A and $Y to B"* — determinate, and false to call
*unknown*.

So the refinement to Cluster C, if ruled:

```text
A       one plan governs this expense                     (incl. CC4 after applicability; CC5 per date)
B       claims compete; which governs is UNRESOLVED        represent-and-report (ruled)
C       both govern; attribution is DETERMINATE, multi-    a distinct state — not B
        valued, each plan knowing for its own share
C+      both govern; PRIORITY unresolved                   C, with represent-and-report on the priority fact
```

And the sentences, so the distinction is visible where the household meets it:

```text
B    "Two plans claim August; Groundwork cannot establish which governed."
C    "Two plans covered August; this expense applied $400 to A and $150 to B."
C+   "Two plans covered August; both apply; which paid first is not established."
CC4  "Two plans were active in August; only the dental plan applies to this expense."
CC5  "Your PPO ended June 30; the HMO began July 1."
```

Five true sentences where the built code has one word.

---

## What the cases do not establish

1. **Primary/secondary semantics or claim allocation** (CC2, CC3). How priority produces the
   split is not touched. Fenced by Rob.
2. **What `plan_at()` should return for C.** The cases sharpen the hazard — for C the right
   answer is two-valued, and `[0]` returns half — without deciding the shape. Fenced.
3. **Deductible projection under C** — per-plan accumulators exist (`accumulators(rows, p)`
   runs per period already); whether they are right for C's split is not tested.
4. **How each plan's share is evidenced.** CC1 assumes two EOBs; each plan's EOB is that
   plan's P-ack for its share — the acknowledgment ruling's shape, one knowing party per plan.
   Noted, not designed.
5. **Representation** of C, of priority, or of the three-way `UNKNOWN` split.

---

## Decision remaining — Rob's

Whether to lift the fence as a refinement of Cluster C on these terms: C is a distinct,
determinate state; represent-and-report governs B and the unresolved priority fact inside C,
never C's attribution; period overlap is necessary and not sufficient — applicability first;
and the built year-level `UNKNOWN` is recorded as carrying three situations.

---

## Ruling — Rob, 2026-09-12. Concurrent-coverage fence lifted exactly as written. Evidence mode closed.

**B and C differ ontologically, not merely in confidence:**

```text
B   competing applicability claims → which governs? UNKNOWN → represent-and-report
C   both applicable → both govern → attribution is determinate and multi-valued
```

Calling C *unresolved* would destroy information Groundwork possesses.

**Frozen — the refinement to Cluster C:**

> **Period overlap does not determine applicability. Applicability is evaluated for the
> particular expense. Where two plans genuinely govern, concurrency is a determinate
> multi-valued state, not unresolvedness. Represent-and-report applies to an unresolved fact
> within that state, such as priority, but does not collapse the concurrent attribution
> itself.**

CC3 is the case that makes it precise: the state is **C + unresolved priority**, not
*UNKNOWN period*. The system can truthfully say both plans apply while saying which paid first
is not established. Separate propositions; they remain separate.

**`plan_at()` — a sharper live hazard, with no implementation decision made:**

```text
B   + [0]   invents a winner where none is established
C   + [0]   discards a legitimate second governing plan
CC4 + [0]   selects a plan on temporal overlap before determining expense applicability
```

> **A single-valued positional lookup is incapable of representing the semantic states the
> evidence cases now establish.** What `plan_at()` should become remains a consumer/build
> decision.

**CC5 preserved — the three-way conflation is not cosmetic:**

> **The built year-level `UNKNOWN` currently conflates unresolved competing governance,
> determinate concurrent governance, and sequential periods. This is a consumer hazard, not a
> reason to invent a universal replacement state here.**

One generic `UNKNOWN` obscures rather than protects uncertainty.

**Evidence mode is genuinely exhausted.** The cases that can settle semantics without choosing
representation, consumers or implementation have all been run: entitlement/payee/discharge ·
acknowledgment · capture/held artefact · asserted referent · proposition kind · source ties ·
concurrent coverage. Each removed ambiguity without turning a finding into a new type or an
implementation rule.

**The board stops generating cases.** The next move is an explicit mode change — hazard
remediation, or build/representation selection — and neither is to be quietly begun because
the hazards are now obvious.
