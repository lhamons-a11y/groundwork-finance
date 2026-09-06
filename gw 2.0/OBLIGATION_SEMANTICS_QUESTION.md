# What is an expense? — the obligation question

**An open decision, upstream of everything else**

> Status: **Question, frozen pending a decision.** Written 2026-09-06, forced by a disagreement
> over a single number that turned out not to be about the number.
>
> **This is upstream of `EVENT_SUBSTRATE_QUESTION.md`.** What events should be recorded depends
> on what is being recorded. Answer this first.
>
> `tests/test_lifecycle_fixture.py` is **frozen** until this is settled. Its disputed assertion
> is deliberately left as it stands — see the last section.

---

## How it surfaced

A fixture assertion said the qualifying tax figure was `$300`. A worked example in review said
`$950`. Both were computed from the same shape of facts:

```
gross obligation   $1,200
insurer funded       $250
HSA funded             $0   (reversed)
user funded          $300
unreconciled         $650
```

`$1,200 − $250 = $950` assumes everything not reimbursed was paid by the user.
`$1,200 − $250 − $650 = $300` assumes everything unreconciled was not paid at all.

**Both are doing the same forbidden thing: assigning meaning to an unknown.** The $650 can be
an unpaid balance, a payment the user made that has not been recorded, an adjustment the
provider wrote off, or a claim still being adjudicated. Same number, four meanings, three
different tax answers.

The `$1,200` is an **obligation**. The `$250` / `$400` / `$300` are **funding events**. They
cannot be added and subtracted as if they were the same kind of fact, and `unreconciled` is the
arithmetic gap between two different kinds of thing — an observation about reconciliation, not
an explanation of what happened to the money.

## The two models

### Model A — obligation-first

```text
provider claims $1,200  →  obligation exists  →  payments reconcile against it
```

An unpaid balance can legitimately exist. Reconciliation gaps are normal and meaningful.

### Model B — payment-first

Nothing is an expense until money moves. The provider's $1,200 is a bill, not an accounting
object — so a gap between obligation and payment cannot arise, because the obligation was never
recorded.

**These are not implementation details.** They determine what the historian records, what the
consequence engine may assert, and what the tax engine is permitted to conclude.

## The design has already chosen A, without saying so

Four places in `HEALTHCARE_MODULE_DESIGN.md` are only expressible under Model A:

- **§7.1, the bill-shock alarm** — *"a bill trips the alarm when paying it in full would take
  liquid savings below the reserve floor, **or when it cannot be paid in full at all**."* An
  unpaid bill must exist as an object for that sentence to have a subject.
- **§7.6, the agreed payment plan** — an obligation with a term and a balance that is not yet
  money.
- **§7.7, the end date** — `balance ÷ payment` presupposes a balance owed.
- **§8, collections in its entirety** — a collections account *is* an unpaid obligation.

So the foundational accounting choice was made by the features built on top of it rather than
by the architecture. That is exactly how a decision of this size gets locked in without being
examined, and it is worth stating explicitly before more is built on it.

## The refinement: it need not be a global choice

Both shapes occur in a real household, and forcing one is expensive in both directions.

- **Pure Model B** cannot represent *"I owe the hospital $1,200"* at all — which deletes the
  bill-shock alarm, the payment-plan calculator and collections.
- **Pure Model A** makes every $12 copay imported from a bank feed synthesise a phantom
  obligation to fund, which is bookkeeping nobody asked for.

The distinction that resolves it is whether the obligation was **observed** or **inferred**:

```text
observed obligation   a bill the user entered or imported
                      → reconciliation gap is possible and meaningful

inferred obligation   implied by a payment with no known bill
                      → obligation ≡ payment, so unreconciled ≡ 0 by construction
```

**Which narrows the problem considerably.** A payment-first record can never carry an
unreconciled balance, so it can never reach the tax ambiguity above. The blocking condition
fires only on expenses that came from a bill — a much smaller and more tractable set than
"every healthcare transaction".

## The invariants this produces

> **An unresolved reconciliation balance must never be implicitly classified as paid, unpaid,
> reimbursed, deductible or non-deductible.**

> **No tax calculation may convert an unresolved amount into a tax classification without an
> explicit rule establishing that classification.**

And the state shape that makes them enforceable — the reason attaches to the *unresolved
amount*, because the money did not change, our knowledge of it did:

```text
obligation
    gross: 1200
funding
    insurer: 250
    user:    300
    hsa:       0
reconciliation
    resolved:   550
    unresolved: 650
    status:  unknown        → pending_claim → provider_adjustment → unpaid …
```

`status` moves as evidence arrives. The $650 never moved.

## What the tax engine receives, and what it may say

Not `qualifying = expense − unallocated`. It receives the states and the rules decide what can
be established:

```text
gross_obligation · confirmed_user_paid · confirmed_reimbursed ·
confirmed_nonqualifying · unresolved
```

And the output distinguishes proof from completeness:

```text
confirmed qualifying:  $300
unresolved:            $650
```

rather than `qualifying: $300`, which sounds like the engine has the whole answer. The first
says **this is what we can prove** — which is the same standard the rest of the product already
holds itself to.

**This is the same defect the dashboard once shipped**, where blank income months read as a
$7,053 shortfall that was in fact a surplus. Absence treated as a value. The established rule —
completeness is tested before anything is judged — applies here unchanged.

## Why the fixture is frozen

`tests/test_lifecycle_fixture.py` asserts `qualifying == 300.00`. That assertion is **known to
be wrong in the same way `$950` is wrong** — it states one of four guesses as fact.

It has deliberately not been changed to `$950`, and deliberately not been changed to "unknown".
Correcting it now would be choosing a number before the semantics are settled, and the fixture
would then encode the choice invisibly, which is how the next forty tax rules would inherit it.

**What unfreezes it:** answering the question in this document's title. Once *observed* and
*inferred* obligations are distinguished and the evidence that converts an obligation into a
confirmed classification is specified, the assertion becomes a pair — confirmed and unresolved
— and the fixture becomes a good test instead of a broken one.
