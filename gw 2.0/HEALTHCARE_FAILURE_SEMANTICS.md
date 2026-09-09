# What the health model may say when it cannot be trusted

**Gap 15 — a design exercise, deliberately before any implementation**

> Status: **DESIGN ONLY. Nothing here is built, and nothing should be built from it until the
> open decisions at the end are made.** Written 2026-09-07 at Rob's direction: *"I'd want that
> answer written down before any implementation begins"* — because inventing an error-handling
> framework first is how the framework decides the semantics.
>
> The question, in his words:
>
> > **When Groundwork's health model cannot establish that its conclusion is trustworthy,
> > exactly what is it permitted to return, record, surface, and say?**
>
> Extended 2026-09-09 with the permission ladder and the design adversary (§5), at his
> direction: *"I would add one test to the #15 design before declaring it complete."*

---

## 1. Two different conditions, and only one of them is "failure"

The design spends its length on behaviour when data is good. What it does not distinguish — and
the distinction decides everything below — is:

| | |
|---|---|
| **Detected failure** | the model *knows* it could not establish something |
| **Plausible and wrong** | the model establishes something confidently, and it is false |

**The second is the dangerous one**, and it is not an error-handling problem at all. A parser
that returns nothing has failed safely. A parser that reads `$412` as `$4.12` has succeeded, and
every downstream guarantee about honest nulls is irrelevant to it.

Rob's sharper statement of the same boundary, and the one to keep:

> **A safe failure is not the same thing as protection against a plausible wrong input.**

So this document answers the first directly, and says plainly what protects against the second:
**not detection — provenance, strength and cheap correction.** Those already exist
(`gw 2.0/HEALTHCARE_GAP_TRIAGE.md` gaps 4 and 1). Nothing here adds a mechanism that catches a
confident mistake, because nothing can — and **a layer whose promise is effectively *we will
detect wrongness* should be resisted**, because that promise cannot be kept. What can be
guaranteed is narrower and real: **the system does not manufacture certainty beyond its
evidence.**

## 2. The four boundaries, and the rule at each

Rob's four verbs are four different permissions, and conflating them is how a cautious return
value becomes a confident sentence three layers later.

### Return — what the caller gets

> **The return type must be able to express *I could not establish this*, and a caller must be
> unable to mistake it for zero.**

Already the practice, in three places independently: `simulate_payoff` returns `None` rather
than a fabricated month count; `qualifying()` returns `UNRESOLVED` while any part is unresolved;
`plan_year` returns `UNKNOWN` for terms nobody supplied. **The generalisation is the sentinel,
not the null** — `None` is acceptable where the caller cannot arithmetic on it, and a distinct
sentinel is required where they could.

### Record — what persists

> **A failure may record that it occurred and what it was looking at. It may not record a
> conclusion it could not establish.**

This is the no-silent-learning boundary, which already applies here with no exceptions
(design §3 rule 5). The sharp case: a classifier that could not decide must not persist its
best guess, because an unsurfaced suspicion is exactly what that boundary forbids.

**What may be recorded:** the attempt, the source it examined, the rule version, and the
resulting *unresolved state* — `not_evaluated` is a fact about the record and is safe to keep.

### Surface — what the user can see

> **Passive, always. A failure never interrupts.**

It fails A.2's materiality gate on its own — a thing Groundwork could not work out is not two
weeks of debt-free date — and A.1's *strictness is free* means it lives where the user meets it
rather than being lost.

**And surfacing is what makes recording legitimate**, per the classification decision: a state
rendered on the row it belongs to is surfaced, and may persist from that moment.

### Say — what the narrator may put in words

> **Templated only, and it may name the gap without explaining it.**

*"I could not match this to a plan"* is a statement about the record. *"Your insurance may have
changed"* is a hypothesis about the user's life, and the model has no standing to offer one.
B.2a already forbids free-generated prose in the high-risk cases; a failure sentence is one.

**The asymmetry worth stating:** the narrator may always say *less* than the return value
supports, and never more.

### The permission ladder — a second axis, and the one with teeth

*(Rob, 2026-09-09.)*

The four boundaries above are **where** a claim passes. This is **what kind of claim it is**,
and the levels are ordered:

| Permission | Meaning |
|---|---|
| **Record** | preserve what was observed |
| **Calculate** | produce what the available evidence mathematically supports |
| **Conclude** | state an interpretation |
| **Recommend** | tell the user what action to take |

> **Each level must be harder to earn than the one below it.**

Nothing about a successful `Record` licenses a `Calculate`; nothing about a correct `Calculate`
licenses a `Conclude`. This is principle 1 of `ARCHITECTURE_PRINCIPLES.md` — facts,
interpretation, policy — restated as *permissions* rather than *layers*, and the restatement is
useful because a layered diagram can be honoured by a call graph while a single function quietly
climbs all four rungs.

**The architectural test this buys later**, and the reason to write the ladder down now: hand
the explanation layer a deliberately rich internal result and verify that its language **cannot
upgrade** without an explicit evidence transition —

```text
possible    →  certain
inferred    →  observed
estimated   →  actual
unresolved  →  resolved
```

That is testable, it is a mutation the narrator either survives or does not, and it is the
concrete form of *say less, never more*. It is not built. It is the first thing worth building
when #15 is unblocked.

## 3. The eight cases

Rob's list, answered across the four boundaries. **Five follow from existing doctrine. Three
are genuine policy choices and are marked as open.**

| Failure | Return | Record | Surface | Say |
|---|---|---|---|---|
| **Classification fails** | `not_evaluated` | the attempt and rule version, **not a guess** | Passive marker on the row | *"not categorised"* |
| **Plan resolution fails** | `UNKNOWN` terms; expense preserved | the expense, with no plan attached | the expense shows *no plan on file* | may name the gap, never invent coverage |
| **EOB parsing fails** | nothing financial | **the source document**, unparsed | *"received, not read"* | may say it arrived; may not say what it said |
| **Correction unreconcilable** | current conclusion → `UNRESOLVED` | both figures, superseded not overwritten | both, with the conflict named | may state the conflict, not resolve it |
| **Reserve inputs stale** | target → `UNKNOWN` | the staleness and its date | the target with its age | *"based on a plan last updated…"* |
| **Duplicate wrongly detected** | **OPEN** | — | — | — |
| **Source document deleted** | **OPEN** | — | — | — |
| **Import conflicts with manual** | **OPEN** | — | — | — |

### The five that follow

**Classification, plan resolution, EOB parsing** are all the same shape: *preserve the input,
withhold the conclusion*. The record keeps what arrived; nothing derived is invented from it.
This is `simulate_payoff`'s honest null generalised — and it is the only generalisation of it
this document makes, deliberately.

**An unreconcilable correction** turns the current conclusion `UNRESOLVED` rather than picking a
figure. Both survive, superseded rather than overwritten, which the obligation model already
does. The user is shown two numbers and told they disagree — which is the honest state, and the
one gap 1's retraction work made expressible.

**A stale reserve target** neither freezes silently nor disappears. It reports with its age,
because a target derived from a plan document last touched in 2024 is not wrong so much as
*unverified*, and those are different claims.

### The three that are open, and why

**Duplicate wrongly detected — this is a correction-*authority* problem, not a data problem.**
The lifecycle review already settled that where no authoritative identifier exists the honest
answer is **possible duplicate, never duplicate**. What it did not settle is what happens when a
*possible* duplicate was merged and is later found distinct. Merge is reversible in the model,
so reversibility is not the question. The question is Rob's:

> **Who is authorized to establish that the two records were actually distinct?**

That answer, and only that answer, decides whether new evidence reverses the merge automatically
or whether Groundwork surfaces the conflict and leaves it with the user. **Neither behaviour
should be encoded until the ownership question is explicit**, because whichever is written first
answers it silently.

**Source document deleted — separate *the fact remains* from *the evidence remains*.** Does
derived data survive? Two defensible answers. *Keep it* — the figures were true when computed
and a tax report may already cite them. *Drop it* — the user asked for the source to be gone and
derived health facts are the most sensitive thing here. **These conflict**, and the conflict is
between the historical-truth invariant and the privacy boundary.

The framing that makes it tractable without pre-deciding it: **those two lifecycles need not be
the same one.** A derived fact and the evidence that produced it can plausibly expire at
different times. But whether Groundwork may retain a derived financial fact after its source is
gone is a **policy decision**, and the provenance machinery must not be permitted to settle it
by construction. It must not be resolved by whichever invariant is more convenient to the code
being written that day.

**Import conflicts with manual entry — resist the obvious answer.** *The user wins* is probably
right and is not obviously right: an EOB from the insurer is a knowing party, and the user
typing a figure from memory is not. The classification model ranks these deliberately equal
(`user_stated` and `imported_eob` are both knowing sources), which means **the model has no
tie-break today** — and asserting *manual wins* would not be reading a hierarchy out of the
model, it would be **inventing one the model does not have.** That is precisely the failure this
review exists to prevent.

So the model keeps an **explicit tie state** until there is an answer to the prior question:
*what constitutes a legitimate authority escalation?*

## 4. What protects against *plausible and wrong*

Since no failure semantics reach it, the honest answer belongs here rather than being implied:

- **Provenance and strength.** A confidently wrong figure still carries where it came from, and
  the weakest-link rule stops it acquiring authority by being used. It does not make it right.
- **Correction being cheap and non-destructive.** Supersession rather than overwrite means being
  wrong is recoverable and explicable. That is the actual defence.
- **Refusing to be the only witness.** Every figure names the records that produced it, so a
  user who knows better can see what the system was reading.

**What does not protect against it:** any amount of internal consistency. A coherent projection
of a wrong ledger is coherent.

## 5. The design adversary

*(Rob, 2026-09-09: "Can every safety rule survive a wrong input that is internally consistent?")*

Not an implementation test. A test **of this document**, run before it is called complete. The
input:

```text
source says $412                      <- and the true figure is $4.12
classification is valid
provenance is complete
weakest-link calculation is correct
ledger reconciles
payment_state() is coherent
health model produces a result
narrator describes the result accurately
```

Every rule in §2 holds. Every guarantee in §4 is delivered. **And the answer is wrong at every
layer, consistently.**

**Groundwork cannot know that, and that is not a defect.** No rule stated here was ever a claim
about correctness; each is a claim about *not exceeding evidence*, and the adversary does not
violate any of them. Recognising this is what stops the next mechanism from being built out of
discomfort.

So the requirement the adversary produces is not a detector. It is an inversion:

> **What must Groundwork *not do* merely because all of those layers agree?**

Four answers, all of which the existing constraints already imply and none of which has been
stated as a rule:

1. **Agreement is not evidence.** Internal consistency may never raise an evidence strength.
   Five layers concurring about one source is one source, five times — the weakest-link rule
   is exactly the refusal to let corroboration be manufactured downstream of the input.
2. **Coherence may never license a permission-ladder climb.** *The ledger reconciles* is a
   `Calculate`-level fact. It does not earn a `Conclude`, and it emphatically does not earn a
   `Recommend`.
3. **A conclusion may never become harder to correct because it was consistent.** The figures
   that flow onward from `$412` must stay as cheaply supersedable as the day they were derived.
   The consistent case is the one that most tempts an optimisation that hardens it.
4. **The narrator may not describe the *process* as though it were evidence about the
   *answer*.** *"This checks out"* is a sentence about arithmetic that a reader will hear as a
   sentence about truth. That is the upgrade table in §2 wearing different clothes.

**This is a more defensible safety model than one that promises detection.** It does not claim
omniscience. It constrains what the system is permitted to infer from an apparently coherent
world — which is a promise that can actually be kept.

## 6. Not decided here

The three open cases above, and one prior question that outranks them: **whether a failure state
is allowed to reach the teaching layer at all**, or whether teaching simply has nothing to say
about a thing the model could not establish. The second is more consistent with *the app earns
the right to teach by showing receipts* — but it is a scope decision, not a derivation, and it
belongs with Rob.

**No implementation should begin until the three open cases have answers**, because each one is
a policy choice that an error-handling framework would otherwise make by accident. And per §5:
**do not build another safety mechanism merely because the design admits that plausible errors
exist.** The limit of what the software can know has been identified. The next step is the three
ownership and lifecycle decisions, not machinery that pretends uncertainty can be eliminated.
