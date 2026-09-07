# Does the architecture survive the criticism?

**Eight criticisms, checked against shipped code rather than against the design's intentions**

> Written 2026-09-07 in response to Rob's review. The question he set is *not "is my critique
> right?" but "can we prove the architecture survives the criticism?"* — so each entry below
> cites the mechanism, the assertion that enforces it, and the commit, or admits there is none.
>
> **The caveat that qualifies every "survives" verdict**, stated once here rather than repeated:
> `core/classification.py`, `core/allocation.py`, `core/person.py`, `core/plan_year.py` and
> `core/reserve.py` are **pure modules with no callers**. The record shape ships; nothing reads
> it. So every guarantee below is proven at module and schema level and **unproven in
> integration** — which is a real limit, not a formality.

---

## Two corrections to the review first

**There is no "Money Conservation invariant."** The review credits one; a search of the
repository returns nothing by that name or concept. What exists is narrower and worth naming
accurately, because the gap between them is where a double-count would live:

- **`server.py:3438`** — a checking transaction already linked to a debt entry is refused:
  *"That checking transaction is already linked to a debt entry."* Real, in code, and it is what
  stops one payment satisfying two bills. **It applies to debt only**; the healthcare allocation
  module has no server wiring and therefore no equivalent guard in force.
- **`tests/test_lifecycle_fixture.py`** — *"unallocated money is not treated as paid by the
  user"*, and the qualifying figure is asserted to be a **sum of evidenced payments, never a
  subtraction**.

Those cover part of what a conservation invariant would, at module level. **A general one does
not exist and would have to be written.**

**"Healthcare is not a spending category" was not overreach in the direction assumed.** The
design already draws exactly the distinction the review retreats to — see criticism 3.

---

## 1. Provenance — **SURVIVES**

> *Every health-derived fact traceable to its source and status: OBSERVED, IMPORTED, DERIVED,
> USER_CONFIRMED, SUPERSEDED.*

| Question | Answer |
|---|---|
| What fact is stored? | An evidence item, and separately a determination over all evidence |
| Where did it come from? | `source` per item: `user_stated`, `imported_eob`, `merchant_match`, `mcc`, `inferred` (`core/classification.py:80-84`) |
| Can it change? | Yes — determinations are superseded, never overwritten; `supersedes_id` appears three times in `core/database.py` |
| What may consume it? | `CONSUMER_AXES` — lever eligibility reads counterparty, tax reads content, and only that |

The review's five statuses map onto what exists, with one difference worth noting: this design
splits *source* (per evidence item) from *state* (the summary over all of it), because one merchant
match and three agreeing signals are different epistemic situations that a single enum flattens.

**The specific demand — the consequence engine never receives "patient owes $412" without
knowing where it came from — holds by construction**: `qualifying()` returns `confirmed_user_paid`,
`unresolved`, and **no definitive total at all** while anything is unresolved, and `explain()`
names the records behind every figure. Asserted: *"every reported figure can name the records
that produced it."*

## 2. Corrections and reversals as append-only history — **SURVIVES**

> *$412 was once believed correct; $287 superseded it. Don't destroy the historical explanation.*

`ExpenseObligationVersion` is append-only with `supersedes_id`; nothing is edited in place. The
worked case is the review's own, one level up:

```text
obligation $1,000  →  corrected to $1,200  →  a determination on the unresolved $650
```

Asserted in `tests/test_lifecycle_fixture.py`: *"a classification is superseded, never
overwritten"*, *"the prior determination is still readable"*, *"and a determination can be
superseded when evidence arrives later"* — and the historical figure stays reproducible under
the rule version in force when it was drawn.

**Stronger than the review asks:** `57b6154` establishes that **correction, reversal and refund
are three different things** a single `−$1,000` collapses. A correction says the figure was
always wrong; a reversal says money moved and came back, obligation standing; a refund says the
obligation itself shrank. `unwound` is reported beside the funding rather than folded into it,
because *no HSA distribution* and *a distribution that was reversed* are different facts.

## 3. Billed / owed / paid / reimbursed / unreimbursed — **SURVIVES**

> *Healthcare spending is a financial classification; healthcare liability is a separate concept.*

This is `OBLIGATION_SEMANTICS_QUESTION.md`, and it was settled before the review by a
disagreement over a single number:

```text
gross obligation  $1,200      an obligation
insurer funded      $250      a funding event
user funded         $300      a funding event
unreconciled        $650      an observation about the record — not an explanation
```

`$1,200 − $250 = $950` assumes everything unreimbursed was paid; `$1,200 − $250 − $650 = $300`
assumes everything unreconciled went unpaid. **Both assign meaning to an unknown**, which is why
the model refuses to produce a definitive total while any part is unresolved.

The four determinations — `provider_adjustment`, `user_paid_cash`, `unpaid`, `pending_claim` —
are held distinct even where they produce the same tax figure today, and `unpaid` versus
`pending_claim` is asserted as a *distinct state, not one state*.

## 4. The reimbursement relationship — **SURVIVES the model, PARTIAL on the guard**

> *The same dollar cannot appear in two buckets without the relationship explaining why.*

The model answers all four questions — gross obligation, cash paid, reimbursed, net
out-of-pocket — from funding allocations by funder, with a version chain rather than a
`reimbursed` boolean, because **one expense can have three funders** and a boolean cannot
represent that.

**Where it is partial:** the double-count guard exists for debt (`server.py:3438`) and **not for
healthcare**, because healthcare has no server wiring. The invariant is described in the
obligation document as transferable; it has not been transferred. That is a real gap and it is
the one place criticism 4 lands.

## 5. Out-of-pocket maximum language — **PARTIAL: architecture yes, language absent**

> *Don't say "you won't spend more than $X". Say "your plan's recorded limit is $X" and "$Y has
> been applied toward it".*

The architecture already refuses the promise. `core/plan_year.py` reports `oop_applied`,
`oop_max` and `oop_met` **separately**, with the docstring stating that an out-of-pocket maximum
is *"a coverage-based target, not a promise that nothing further will be charged"* — and the
review's own status list already recorded that.

**But the review is right that this is a language question, and there is no language.** No
narrator copy, no user-facing string, nothing that would say either the safe sentence or the
dangerous one exists anywhere in the repository. The architecture makes the honest sentence
*possible*; it does not yet make the dishonest one *impossible*, because nothing is written.
**Criticism accepted, and it is unbuilt rather than wrong.**

## 6. Collections — **OPEN, and the underbuild instinct is a live decision**

> *Model the underlying obligation separately from the payment. Don't build a collections
> subsystem unless requirements demand it.*

Design §8 exists and §8.5 is titled *what this feature is, and what it must never become* — the
same instinct. But **collections is entirely unbuilt**, and two items remain on the P0 list:
ownership history, and validation state.

The review's *"original obligation → current holder/status → financial transactions"* is
compatible with the obligation model already built: the obligation is the entity, and a change
of holder is a state change on it rather than a new subsystem. **Nothing here contradicts the
design; nothing here has been built either.** This is the one criticism I would neither defend
nor concede — it is an open decision, and *underbuild rather than overengineer* is a reasonable
position to take into it.

## 7. Health as a domain producing verified financial facts — **ALREADY THE ARCHITECTURE**

> *Not an independent financial universe. Not a Healthcare Intelligence Engine.*

This is what was built, and design §6.1 states it: **most of healthcare is LTS, and the teaching
layer is a thin overlay.** The `core/` modules produce facts; the existing consequence engine,
solution engine and narrator consume them. §4 places the calculations accordingly.

Corroborating detail: `/api/debt/decision-impact` was **reclassified from teaching to engine**
during the seam work, precisely because a 1.x feature depends on it. The boundary is drawn where
the review would draw it.

## 8. Health must never silently increase what Groundwork claims to know — **SURVIVES, and is the strongest match**

> *"$215.17 — Riverbend Hospital Health" may produce "a healthcare-related payment occurred". It must not
> produce "you had a medical procedure."*

This is `CLASSIFICATION_QUESTION.md`'s position 2, reached independently and stated as two axes:

```text
axis 1   counterparty   what kind of party received this money
axis 2   content        what this money bought
```

**No accumulation of counterparty evidence establishes content**, at any strength. Asserted and
mutation-proven: *"no amount of counterparty evidence establishes content"* — the fixture piles
ten more merchant matches on a CVS charge and requires the content axis to stay `not_evaluated`.

And position 3 goes further than the criticism: **sensitivity attaches to the question, not the
verdict.** Asking whether a named person's transaction is health-related creates health-domain
information *whatever the answer*, so `contradicted` still carries a domain — and the unresolved
states are the **most** sensitive, because a manufactured suspicion is the one the user cannot
correct.

The no-silent-learning boundary applies with no exceptions: an unsurfaced suspicion **does not
persist**.

---

## Summary

| # | Criticism | Verdict |
|---|---|---|
| 1 | Provenance | **Survives** — evidence source + state, superseded chain, consumer table |
| 2 | Corrections / reversals | **Survives**, and distinguishes three things the critique treats as two |
| 3 | Billed / owed / paid / reimbursed | **Survives** — settled before the review, by the $650 |
| 4 | Reimbursement relationship | **Survives** in model; **guard not transferred** from debt |
| 5 | OOP language | **Partial** — architecture refuses the promise; no language exists at all |
| 6 | Collections | **Open** — unbuilt, and underbuild is a live position |
| 7 | Health as a fact-producing domain | **Already the architecture** |
| 8 | No silent inference about the person | **Survives**, mutation-proven, and goes further |

**Two criticisms land: 4's untransferred guard and 5's absent language.** Both are gaps in what
has been built rather than errors in what was designed — which is the distinction the review
asked to be able to make.

**And the caveat above outranks the table.** Nothing is wired. Every verdict here is a statement
about modules and schema, and integration is where guarantees usually go to die.
