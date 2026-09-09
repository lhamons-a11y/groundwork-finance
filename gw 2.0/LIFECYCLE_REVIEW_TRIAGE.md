# The lifecycle review, triaged

**Fifteen findings against the gap-8 doctrine work — dispositioned, not catalogued**

> Status: **Triage record, 2026-09-09.** A review of the lifecycle and carrier work
> (`OBLIGATION_LIFECYCLE_QUESTION.md`, `PAYMENT_AGREEMENT_DECISIONS.md`,
> `PAYMENT_AGREEMENT_INSPECTION.md`) arrived after `973ffb4`. This document records **what the
> repository already says about each finding**, in the form used by
> `HEALTHCARE_CRITIQUE_SURVIVAL.md` and `HEALTHCARE_GAP_TRIAGE.md`: checked against what exists,
> and marked with its disposition and the mechanism cited or its absence admitted.
>
> **It is a triage record, not a second design authority.** The findings are not restated as a
> numbered agenda of their own, because the value of writing this down is the *provenance of the
> dispositions* — why something was rejected, and against which existing decision. A document
> that read as the review's own list would invite a later session to treat it as a parallel
> source of requirements.
>
> **Verified while triaging, not assumed:** `core/payment_plan.py` still has zero consumers
> outside `tests/test_payment_state_fixture.py` and `smoke_sections/s99_payment_state.py`; the
> `effective_on` / `recorded_at` separation exists in `core/database.py`. Both are load-bearing
> below.

---

## 0. The fence, stated first because four dispositions depend on it

```text
Doctrine  →  lifecycle semantics  →  M1 / M2  →  schema  →  implementation

Nothing downstream may be used to settle an upstream semantic question.
```

This is `c21f0e9`'s dependency chain with the rule that governs it made explicit. Everything
below the first arrow is blocked on §7.7's meaning of *carries*, which is doctrine and Rob's.

The fence is not a scheduling statement — it is a prohibition on a particular kind of argument.
A table, a schema sketch, a fixture or a corpus drafted while the doctrine is open does not
merely arrive early; **it arrives with the answer already assumed in its columns**, and the later
decision then gets made against it rather than against the domain.

Two rules sit **outside** the chain and survive whatever definition eventually lands, per §10:
the effective/recorded dating requirement, and *payment state may evidence but never
independently establish a change in who bears the obligation*.

---

## ADDRESSED — recorded already; do not reopen

### The carrier question itself

The review's leading finding — that §7.7 is semantically undefined and M1/M2 cannot proceed — is
the current head of the chain, and `OBLIGATION_LIFECYCLE_QUESTION.md` §10 states it in a stronger
form than the review does:

> **Do not ask which dimension is the carrier.** Treat the word as a candidate for deletion
> rather than a term to define. If several dimensions independently matter, `carrier` was an
> abstraction error and there should not be one.

The repository also names **four** dimensions — funding, servicing, economic risk, legal
entitlement to collect — where the review offers a looser five. The difference matters:
**recourse is not a fifth dimension.** Recourse is the arrangement that makes economic risk
*separate* from the other three, which is the §9 finding and the reason the premise failed.

### Payment state versus agreement semantics

Answered in `PAYMENT_AGREEMENT_INSPECTION.md`, in the exact terms the review asks for:

| Dimension | Under agreement versioning |
|---|---|
| `paid` | unchanged — economic fact |
| `remaining` | unchanged — economic fact |
| `expected_by_now` | changes — agreement-relative |
| `ahead` | changes — agreement-relative |
| `overdue` | changes — agreement-relative |

That **is** the economic-fact / agreement-relative split. The review's *"you are $600 ahead —
according to which schedule?"* is the same observation, and the inspection reached it by way of
`expected_by_now` becoming a piecewise fold with per-version caps rather than `min(count,
months)`.

### Corrections versus real-world change

Already stated twice. The inspection records that renegotiation, correction and restructure
produce **three different `expected_by_now` values for the same past date, and arithmetic cannot
recover which occurred**. Gap 1's closure ships the provenance distinction it needs —
`corrected` / `replacement` / `retracted` — and §10 makes `effective_on` / `recorded_at`
mandatory rather than merely good practice.

**One refinement worth keeping:** the review notes that it is not only the *figure* that can
coincide between a real change and a correction, but the **entire final state**. That is a
sharper statement of why the change kind cannot be reconstructed afterwards and must be recorded
at the time.

### Schema-becomes-doctrine as a process risk

The defence exists and is stronger than the review's version of it. `PAYMENT_AGREEMENT_DECISIONS.md`
§0 records the zero-consumer condition as **a deliberate condition with a stated expiry** — a
wasting asset that ends the moment the healthcare module is wired — rather than as discipline
someone must remember to apply. §10's scope fence forbids schema, forbids adding a consumer to
`core/payment_plan.py`, and labels `c21f0e9` an architectural checkpoint rather than unfinished
implementation.

### What the user is entitled to learn from each distinction

This is §6's deciding principle already in use:

> **Does the distinction between old and new obligation materially change what Groundwork is
> entitled to explain to the user?**

And §7 goes one step further than the review does, which is the step that keeps M1 alive: the
existing collections doctrine (§8 of `HEALTHCARE_MODULE_DESIGN.md`) forces the **distinction**
without forcing the **succession**. A versioned carrier fact plus a dated collections fact set
obtains the same entitlement change. Treating the entitlement argument as decisive for M2 would
be principle 7's tell — a measurement that suits an argument one already found appealing.

---

## PARTIAL / RECORDED — the refinement is real; no new implementation follows

### Evidence strength applied to transitions

The general invariant is closed (gap 4: weakest-link strength over a lattice, enforced at the
`consume()` boundary), and §10 already forbids the review's specific example by name — inferring
a creditor change from payment destination, matching amount and timing is *principle 1 in its
sharpest form*, because it manufactures a fact about a third-party contract out of the user's own
ledger.

**What genuinely does not exist** is the mapping *which evidence types establish which transition
types*. It cannot be written yet: it is indexed by the transition taxonomy, which is itself partly
downstream of the doctrine. Recorded, not scheduled.

### Payment attachment across a transition

`HEALTHCARE_GAP_TRIAGE.md` gap 5 already marks attribution **representable but unnamed**, and gap
1's closure establishes the governing behaviour at the expense level: a payment attached to a
retracted obligation does **not** fund its replacement, and the resulting money-against-a-zero-
obligation is reported as negative unallocated rather than netted away.

The review's rule — resist attaching payments to whichever agreement is current, because that
rewrites history — is the same rule one level up. The precedent covers the behaviour; the
vocabulary is what is missing, which is gap 5's existing finding rather than a new one.

### Unknown versus not-applicable

`HEALTHCARE_GAP_TRIAGE.md` gap 3 already lists `NOT_APPLICABLE` as one of **two genuinely
unrepresented** states. The review adds one thing worth recording: the distinction is not confined
to EOB classification. *Post-promo APR unknown* versus *this instrument has no promo* is the same
collapse in the agreement domain, and the second is not a null at all — it is a structural
consequence of the instrument kind. Recorded against gap 3 rather than opened beside it.

### Agreement identity versus obligation identity

This is M1 versus M2 in different wording, and M1/M2 is stopped by the fence. The precedent is
already in the repository and should be the starting point when it resumes: gap 1 settled that an
identical balance is not an identical history, and that **what a payment attaches to is where the
money goes wrong**. The $4,000 → $3,000 → $1,914 chain is that same question asked about
agreements instead of expenses.

The review is right that economic-transfer invariants do not answer identity. Finding 4 says the
equivalent already: the invariant is produced by **neither** anchoring.

---

## NEW — recorded narrowly

Three findings are genuinely absent from the repository. Each is recorded with its blocked and
unblocked portions separated, so that a later session cannot read the heading as a licence to
build the whole thing.

### 1. Transition taxonomy — only the doctrine-independent portion may proceed

There is no enumeration of what constitutes a transition. *A known transition is never silent*
governs the recording of one; nothing defines the set.

```text
BLOCKED on the doctrine          UNBLOCKED
  creditor change                  economic-term change
  servicing change                 collection-status change
  funding change                   correction / succession of record
  risk-transfer change
```

The left column is indexed by the four dimensions whose status is exactly what is under decision.
The right column is scenario A and scenario D, which finding 1 showed **both candidate models
treat identically** — so work there cannot bias M1/M2. `HealthPlanOperation.kind` is the
precedent, and the inspection already notes it is one value short.

### 2. Cliff lifecycle — the extension/correction distinction needs explicit treatment

Finding 2 established that the cliff is not a lifecycle event: the carrier does not change, the
instrument does not change, and a conditional consequence fires. **Nobody then asked what happens
when the cliff itself moves.**

```text
promo expires 2027-03-01  →  issuer extends  →  expires 2027-09-01
```

Probably scenario A — a terms change on an unchanged instrument, which both models version
identically — but that must be established rather than assumed, because an extension is
**indistinguishable in final state** from a correction of a misrecorded expiry date. That is the
corrections finding above, arriving in the one place where the clock is not the payment
schedule's.

### 3. Transition candidate semantics — what a surfaced candidate may claim

The review's sharpest question: *can weak evidence create a transition candidate without creating
a transition fact?*

It is already half-constrained by a settled rule. **An unsurfaced observation may never persist.**
So the storage half of the question closes before it is asked: a candidate that is retained but
not shown is prohibited outright, whatever its evidence strength.

What remains open is therefore narrower and better posed:

> **What is a surfaced transition candidate permitted to claim?**

Bounded already by the permission ladder (Record → Calculate → Conclude → Recommend), by
`consume()`'s declared-strength requirement, and by §10's rule that payment state may evidence but
never establish. **No unsurfaced persistence, under any evidence strength.**

---

## ACTIONABLE NOW — the only two

Both are existing requirements rather than new findings, and both are unblocked because finding 4
established that the economic-transfer invariant is produced by neither anchoring. §4 lists it
under *not open, and not waiting on any of the above*.

### The disposition vocabulary, attacked beyond collections

> **Whenever economic terms change, every amount whose economic treatment changes must have an
> explicit, reconstructable disposition.** (§5)

The invariant survives conceptually. What is untested is whether the eventual disposition
vocabulary can explain the amounts that are not principal without inventing a special case for
each:

```text
accrued interest        capitalized interest      waived fees
collection fees         disputed amounts          uncleared payments
reversed payments       insurance adjustments     provider discounts
contractual write-offs  partial settlements
```

This is a semantics exercise, not a schema one, and it names no carrier.

### The five-question reconstruction test

Both 8.1 invariants — historical schedule authority and economic transfer — are model-independent,
so the test can be written now. Given an agreement change, five questions must be answerable
**independently**, and none of them by consulting today's state:

1. What was expected under the old agreement?
2. What was actually owed?
3. What amount moved?
4. What is expected under the new agreement?
5. Why did the difference occur?

The failure this catches is the one `e74d673` named: a perfect, immutable, `as_of`-reproducible
version chain satisfies the first half of the criterion completely and says nothing whatsoever
about the second.

---

## FENCED — rejected from current work because it crosses the dependency boundary

### The adversarial corpus, and why the review's version is evidence for the fence

The review proposes a semantic corpus for carrier and lifecycle cases before implementation —
correct in principle, and §10 already anticipates it as the thing that must arrive **after** the
doctrine rather than before it.

The proposed table is columned:

```text
Case | Funding | Servicing | Legal creditor | Risk | Schedule | Transition
```

**Those columns are the answer to the open question.** They assert that *carries* decomposes into
exactly that set, which is precisely what §10 refuses to presume — including the live possibility
that `carrier` should not exist at all. `df95101` was committed specifically for posing 8.1 and
8.2 as semantic questions **with no table drafted beside them**, and §10 requires the doctrine to
arrive *"before M1/M2 or a table exists to bias it."*

**This is the finding worth preserving from the whole review.** A careful engineering review that
warned in one section against letting the schema become the doctrine produced, in the next
section, a table that would have done exactly that. Not carelessness — the pull toward a structure
that lets work start is strong enough to survive being named explicitly one paragraph earlier.
That is direct evidence that the fence has to be a rule rather than an intention.

### M1/M2 advocacy in any form

Including by way of agreement-identity arguments, entitlement arguments, or schema-tidiness
arguments. §10's scope fence stands: no schema, no consumer added to `core/payment_plan.py`, no
M1/M2 advocacy until §7.7 has an answer that survives the recourse case.

---

## The failure mode, in the review's own words

Worth recording because it names the danger without prescribing a fix — which is the only form in
which it is safe to keep:

> **The biggest danger now isn't that the code is wrong. It's that the code becomes beautifully
> correct around an imprecise noun.**

That is a better statement of §10's finding than §10 manages, and it generalises past `carrier`:
the same session found *payment*, *agreement* and *transition* each hiding several independent
domain concepts. It is not an argument for more architecture. It is an argument for the fence.
