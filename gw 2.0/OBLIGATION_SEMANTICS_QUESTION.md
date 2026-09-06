# What is an expense? — the obligation question

**An open decision, upstream of everything else**

> Status: **Answered 2026-09-06.** Written the same day, forced by a disagreement over a single
> number that turned out not to be about the number. The answer is in "What confirms a payment"
> below; the fixture is unfrozen.
>
> **This is upstream of `EVENT_SUBSTRATE_QUESTION.md`.** What events should be recorded depends
> on what is being recorded. Answer this first.
>
> `tests/test_lifecycle_fixture.py` was frozen until this was settled. It is now unfrozen, and
> its disputed assertion has been rewritten on the basis below — same number, different claim.

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

---

## What confirms a payment — the answer

**The same way debt already does it: the ledger attaches to the obligation.** Three signals,
all of which exist today:

| Signal | Where it lives | What it establishes |
|---|---|---|
| `Transaction.cleared` | `transactions` | money actually moved |
| `CheckingTransactionLink` | its own table | this money went to *this* obligation |
| `link.user_confirmed_at` | the same row | the attachment is asserted, not guessed |

**A confirmed payment is a cleared transaction, attached to the obligation, confirmed by the
user.** Nothing else counts, and nothing weaker is inferred.

**This defines a payment, not an obligation, and the difference is load-bearing.** An observed
obligation is meaningful the moment the bill is recorded — nothing has been paid yet, and that
is precisely the state §7.1's alarm fires on (*"when it cannot be paid in full at all"*). If an
obligation only became meaningful once a payment confirmed it, the bill-shock alarm would have
no subject, the payment-plan calculator no balance, and every collections account would be
meaningless by definition.

| | |
|---|---|
| **Obligation** | exists when a bill is observed. Meaningful immediately. |
| **Payment** | confirmed when cleared **and** attached **and** user-confirmed. |
| **Reconciliation** | the relationship between them — and the piece still open. |

### Determinations, not resolutions

Four meanings can be recorded against an unresolved amount, and they are **not** four flavours
of the same thing:

| Determination | What it establishes | Tax consequence |
|---|---|---|
| `provider_adjustment` | the obligation was reduced | recalculate against a smaller gross |
| `user_paid_cash` | the amount was paid by the user | becomes user-paid |
| `unpaid` | nobody paid it | no additional user-paid amount |
| `pending_claim` | the funder is not yet decided | remains unresolved |

**`unpaid` and `pending_claim` must not be collapsed** merely because they produce the same tax
figure today. One says *nobody paid this*; the other says *nobody yet knows who bears it*. Their
futures differ, and merging them loses the difference at exactly the moment a later transition
needs it. That is the same error as a `reimbursed = true` flag, one level up: **states merged
because one consumer cannot currently distinguish them, then a second consumer arrives that
must.**

**And none of them is terminal**, which is why "resolution" was the wrong word — including in
the first version of the fixture. `unpaid` becomes `user_paid_cash` when a receipt surfaces six
months later; a write-off reverses if the provider re-bills. These are **current determinations,
superseded rather than overwritten**, each carrying provenance and a date — the same bitemporal
property the rest of the model already has.

`unpaid` carries one further subtlety: it settles the **evidentiary** question (*was this paid?*
— no) while leaving the **obligation** entirely open. `provider_adjustment` and `user_paid_cash`
close a portion of the obligation; `unpaid` closes none of it. Two different questions, and the
state has to answer both.

### Reconciliation is the bridge, and it is what to solve next

The four decisions now connect: obligation semantics says *what the obligation is*, progress and
adherence say *how movement against it is evaluated*, the substrate says *where these facts live*,
and reconciliation says *whether the obligation has been accounted for sufficiently to support a
downstream claim.*

That last one is the missing span, and it is the right next target rather than the tax formula.
**Once reconciliation has a rigorous semantic model, tax becomes a consumer of established facts
instead of another place where Groundwork has to guess** — which is the whole direction of this
work.

```text
obligation → funding evidence → reconciliation state → determination
           → established facts → tax interpretation
```

With a hard boundary between the last two:

> **Reconciliation establishes reality. Tax rules interpret established reality.**

No tax-specific logic belongs inside a determination. Its job is to record what happened; the
tax layer consumes that and decides what follows. **And neither layer may turn an unknown into a
convenient number.**

#### The same separation, for the third time

This is structurally identical to `MODEL_PLACEMENT.md`'s *the application owns truth, the model
interprets it*, and to `ARCHITECTURE_REVIEW_LIFECYCLE.md` §1's *`health.py` is a policy evaluator
over facts, not the owner of them*. Three layers, the same split, arrived at independently each
time.

That is unlikely to be coincidence. It looks like the project's central architectural instinct —
**keep the thing that establishes truth separate from the thing that interprets it** — and
naming it means the next layer can apply it deliberately rather than rediscovering it a fourth
time.

Which resolves the $650 without assuming anything about it. It is not *assumed unpaid* — it is
**not evidenced as paid**, which is a fact about the record rather than a guess about the world.
And that is also the correct tax posture: §213 deducts what was paid, substantiation is the
taxpayer's burden, and an unevidenced payment is not deductible because nothing evidences it.

**The reuse is the point.** A healthcare obligation takes the same shape as a debt ledger entry,
so the link rules transfer wholesale — including the existing invariant that a transaction
already linked cannot be re-linked, which is what stops one payment satisfying two bills.

### Three precisions

- **`cleared` defaults to `True`,** so the flag alone cannot distinguish *the bank settled this*
  from *the user typed it and the default applied*. Harmless for debt; not harmless for a figure
  substantiating a deduction. The evidence chain needs **source** (imported vs manual) alongside
  `cleared`. Both can be legitimate — a cash payment with a receipt is deductible — but they are
  different provenance.
- **"Settled obligations disappear from the attach picker" must be derived, never stored.** As a
  flag, a later correction reopens a balance on an obligation that has vanished from the list,
  and the payment that settles it has nothing to attach to. Derived from the reconciliation
  state, it comes back on its own. The safeguard itself is good: it also stops a payment being
  attached to a bill that is already settled.
- **Progress is measured in dollars, not payments.** A schedule of 24 × $175 that receives one
  extra $175 does not become 4-of-24; it becomes $350 closer to done, and the provider cares
  about the total rather than the cadence. So the bar is **paid ÷ owed**, with any payment count
  as a label beside it and never as the bar itself.

  Two consequences worth stating. **Early is free, late is not** — a provider does not mind being
  paid ahead, but a plan that falls behind can be voided or referred, so the schedule survives as
  a separate downward-only check: *is the balance where the agreement says it should be?* And
  **a corrected obligation moves the denominator**, so the bar can go backwards. That is correct
  — it is derived, and the truth changed — but it must say why, or it reads as a bug.

## The fixture, unfrozen

It asserted `qualifying == 300.00` as a bare figure, which stated one of four guesses as fact
and was wrong in the same way `$950` was wrong.

**The number survives; the claim does not** — and then the claim got stronger again.

`$300` is what can be **proven**, not what is true. The truth is $300 or $950 and nothing in the
model knows which, so the fixture now asserts **three** things: confirmed user-paid is $300, the
unresolved balance is $650, and **there is no definitive qualifying total at all** while any
part of the obligation is unresolved. A model that nominates one of the two candidates has
guessed, even when it guesses the number this fixture used to assert.

And the positive half, which is what makes it a specification rather than a calculator. Two
branches resolve the same $650 differently — a provider write-off drops gross to $550 and makes
the total available at $300; a cash payment with a receipt makes it available at $950 — and the
fixture asserts **the two must diverge.** If a model returns the same total for both, the
ambiguity was never being represented and the earlier agreement was a coincidence.
