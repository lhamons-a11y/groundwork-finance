# The obligation lifecycle question

**Now governing. Gap 8.1 and 8.2 are consequences of it, not decisions beside it.**

> Status: **OPEN — the five scenarios are tested here against two candidate models; the choice
> is Rob's.** Written 2026-09-09, replacing the structure of `PAYMENT_AGREEMENT_DECISIONS.md`
> rather than refining it. His instruction:
>
> > *"I think your correction about 8.1 ↔ 8.2 is important enough that I would change the review
> > structure permanently rather than treat it as a refinement."*
>
> **The question that governs both:**
>
> > **What is the lifecycle of an obligation when the party carrying it, its instrument, or its
> > economic terms change?**
>
> And the criterion for judging any candidate answer:
>
> > **Can the model reconstruct both the user's obligation history and the economic disposition
> > of every dollar across the transition?**

---

## 0. Why the criterion has two halves

Because the two failure modes are independent, and each survives a model that only satisfies the
other half:

```text
DOUBLE COUNT                          SILENT ERASURE
old arrears                           old obligation disappears
  + new principal containing them        ↓
  + old obligation still counted       new balance exists
                                         ↓
                                       no trace of what happened to the old
```

**Neither is fixed by having excellent version history.** A perfect, immutable, `as_of`-
reproducible chain of terms satisfies the first half of the criterion completely and says
nothing whatsoever about the second. That is the finding from `e74d673` and it is the reason the
criterion is stated as a conjunction.

## 1. The two candidate anchorings

Rob's framing, and the two are genuinely both viable:

**M1 — instrument-anchored.** *Instrument kind describes the economic instrument carrying the
obligation at a point in time.* The obligation is the durable entity; carrier, instrument and
terms are versioned facts **about** it. A sale is a carrier transition on a surviving obligation.

**M2 — agreement-anchored.** *Instrument kind is part of the agreement's identity.* Changing
carrier or instrument **ends** the agreement and begins a successor, joined by a typed
succession edge. The obligation may span several agreements.

**M3 — the mixing case, named so it can be refused.** Kind stored on the agreement *and*
mutable. This is what a schema drafted without answering the question produces, and it is the
outcome Rob warned about: *"Either can work. The dangerous outcome is mixing them."* It fails
because a mutable identity field means the agreement's history contains states its own identity
denies ever existing.

## 2. The five scenarios against the criterion

| | Scenario | M1 — instrument-anchored | M2 — agreement-anchored |
|---|---|---|---|
| **A** | Provider-plan restructure (terms change, arrears rolled in) | terms version | terms version |
| **B** | Debt sold / assigned to a lender | carrier version; obligation survives | agreement ends; successor + edge |
| **C** | Promo reaches its cliff | **not a transition** (see below) | **not a transition** |
| **D** | Correction / replacement of mis-recorded terms | correction version | correction version |
| **E** | Obligation transferred **while arrears exist** | carrier version; arrears untouched | successor **must re-express** the arrears |

### Finding 1 — A and D do not discriminate, and C may not either

Both models treat a terms change as a version and a correction as a correction. §7.7's carrier
rule is not engaged by either. **Three of the five scenarios are silent on the choice.**

### Finding 2 — the cliff is probably not a lifecycle transition at all

This matters because it was the scenario most likely to be treated as decisive, and Rob was
right to warn against letting it decide.

Apply §7.7's own rule: *it is a credit card when a lender carries it, whatever the marketing
calls it.* A deferred-interest promotional balance is carried by a lender **from origination** —
Synchrony behind CareCredit, and its relatives. So at the cliff:

- the carrier does not change — the same lender carried it yesterday,
- the instrument does not change — the cliff is a term the instrument always had,
- what happens is that a **conditional consequence fires**, exactly as §2 of the decision record
  describes it: *what financial consequence occurs if condition Y is still true when X arrives.*

**So the cliff is an instrument reaching a terminal condition, not an obligation becoming a
different instrument** — Rob's distinction, and §7.7 already resolves which side it falls on. If
that reading holds, scenario C **cannot** decide the lifecycle, because under both models it is
not a lifecycle event.

*(This is a claim about how these products are carried, not about the repository. It is the
reading §7.7 forces, and it is worth confirming rather than assuming.)*

### Finding 3 — the discriminator is E, not C

**Scenario E is the only one where the two models produce materially different obligations.**

- **M1** changes one fact — who carries it. The arrears are a state of an obligation that never
  stopped existing, so **no economic transfer occurs and no disposition is required.** There is
  nothing to double-count because nothing was restated.
- **M2** restarts the container, so everything inside must be re-expressed across the succession
  edge. That **manufactures an economic-transfer problem** in a scenario that did not otherwise
  have one — and it is exactly the shape that produces double-counting when done carelessly.

That is an argument from the criterion rather than from schema tidiness, which is the only kind
that should count here.

**And the counter-argument, which is real.** M1 says the obligation survives a sale unchanged.
But a bill now held by a collection agency is not the same thing in the user's life: different
counterparty, different consequences, credit reporting, a different legal posture. A model that
treats it as one continuous obligation with an updated field **risks understating a change that
matters enormously to the person.** M2's heavier structure buys a boundary the narrator can
speak from.

So: M1 is better against the reconstruction criterion; M2 is better at not flattening a change
in the user's actual situation. **That is the trade, and it is a judgement rather than a
derivation.**

### Finding 4 — 8.1-b holds in every model, so it is not downstream of this choice

Arrears disposition arises from a **terms** change (scenario A), which both models treat
identically as a version. So:

> **The economic-transfer invariant is not produced by either anchoring.** It must be stated and
> enforced independently, whichever model wins.

This is the strongest structural result here. It means 8.1-b does **not** wait on §2a — it is
already settled as a requirement and only its mechanism is pending. And it confirms the instinct
to name it separately rather than fold it into "restructure semantics", because folding it in
would have made it look like a consequence of a decision it does not depend on.

## 3. What the choice actually determines

Once §2a is answered, these stop being open questions and become derivations:

| Was | Becomes |
|---|---|
| **8.1** restructure semantics | a consequence: whether a carrier/instrument change ends the agreement is *the same answer* |
| **8.2** promo ownership | a consequence: under M1 the promotional facts are a versioned instrument-property of the obligation; under M2 they belong to the agreement whose identity they partly are |
| the succession/transition record | required under both — only its shape differs |

**Invariant that survives every branch**, and the one thing already settled:

> **A sale is never silent.** Whether the storage model treats it as a new agreement or a
> version, the transition itself is dated, sourced and reconstructable. The user must be able to
> see that what they owe changed hands, and when.

## 4. What is open, and the order

1. **§2a — the governing question.** M1 or M2, decided on the trade in finding 3, and
   deliberately **not** on scenario C.
2. **Confirm finding 2** — that a deferred-interest promotional balance is lender-carried from
   origination, which is what removes C from the deciding set.
3. Then 8.1 and 8.2 as consequences.

**Not open, and not waiting on any of the above:** the economic-transfer invariant (finding 4),
the explicitness of instrument kind (`NOT NULL`, no default, never computed), and the
zero-consumer condition on `core/payment_plan.py`.

> **No schema fields are proposed in this document, deliberately.** Per `e74d673`'s method note:
> decide the semantics the schema must preserve, then derive the schema.
