# The expense as a 2.0 identity — what is it, and what makes something correspond to it?

> Status: **Queue item 4 (first referent of three), opened by Rob 2026-09-14 — a doctrine record,
> no code.** Reversal is closed at `8ee5f76`. Slice 6 left D1 (*transaction t is health on axis X*)
> and D3 (P-world, *patient responsibility for this claim*) blocked on referents with no 2.0
> identity; the transaction referent (Tx8) sent D1's subject here — *the classifier's subject
> moves from the row to the expense identity*. This record tests four readings of the expense's
> identity against the classification, obligation, transaction and reversal rulings, answers
> the correspondence half, evaluates the 1.x rows afterwards, and ends with a ruling candidate.
> Nothing here is authorised to build.

**Rob's question, verbatim:** *what is an expense as a 2.0 identity?*

**Rob's hard constraint, carried from reversal:** ***a source's category for a movement does not
establish the identity of the thing being categorised.*** And the standing warning from Tx8:
*the 1.x notion of a "transaction" cannot be allowed to silently become the 2.0 subject of an
expense classification.*

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **§7.7 classification** (frozen) | classification describes the obligation *by its financial terms and, where applicable, the nature of the underlying expense*; three facts — instrument kind · **care necessity** · terms — consumed by different behaviours; `Unknown` is a terminal state; never computed from a party |
| **The two-axis space** (`core/classification.py`) | *health on axis X* — two axes, read by different consumers (protection reads axis 1, tax reads axis 2 and only axis 2); the shipped `Evidence` is the fused structure the substrate replaces |
| **Slice 6** | D1's subject is *a transaction* — the world event, not the row; D3's subject is *the claim* — a world event; `HealthcareExpense` is *the household's record of an expense event, from which an obligation arises* — **a different referent from the obligation** |
| **Obligation slice §6** | `HealthcareExpense` = the expense / claim referent, *of which the patient-responsibility obligation is one consequence — not the obligation*; Ob2: a bill mints nothing; the household's "that's the ER visit — I owe Riverbend Hospital for it" mints the obligation |
| **Transaction referent** | "transaction" names no identity; a bank line is the bank's statement about a movement; the movement is unminted; **Tx8:** the health claim attaches to an expense identity the household mints when it individuates the purchase, and the line then concerns it |
| **Reversal** | a movement is a payment identity only when the household individuates it; source vocabulary decides nothing |
| **Decision 9 / sensitivity** | the manufactured flag: a classification a process produced; the narrator voices a claim only when it is *asserted in the findings record*; manufactured provenance cannot authorise |
| **"What is an expense?"** (`OBLIGATION_SEMANTICS_QUESTION.md`, 2026-09-06) | the $1,200 is an obligation; the $250 / $300 are funding events; *an observed obligation is meaningful the moment the bill is recorded*; four determinations (`provider_adjustment · user_paid_cash · unpaid · pending_claim`) are *current determinations superseded rather than overwritten* |
| **Cluster B** | P-subject (*the EOB states X*) and P-world (*X is true of the claim*) are two propositions per value |
| **Identity pattern** | minted by a Person's individuating assertion; anchor = pointer to the minting act and nothing else; minting act ≠ minted identity; identity ≠ truth; a 1.x row is not presumed to be the thing |
| **1.x `HealthcareExpense`** | *"Identity only. The amount is versioned, the person is assigned, and the plan is derived … nothing here is a mutable current-state field"* — `id · incurred_on · created_at`; *"there is deliberately no `plan_id`"* — the 1.x author already refused fused state on this row |

Two consequences before the readings. First, **the household does individuate expenses** —
"the ER visit", "the plumber", "Kim's prescription" — as it individuates payments and
obligations and does *not* individuate movements. Under the identity pattern that is the mark of
a mintable identity. Second, **several parties make statements about one expense**: the provider
(billed), the insurer (allowed, plan-paid, patient responsibility — the EOB), the bank (a
movement that paid for it), the household (it happened, it was health, it was necessary, who it
was for). The condition that forced the obligation and the payment.

---

## 2. Four readings of "the expense as an identity"

**X1 — an expense is a categorised movement.** The bank line with a category: `MERCY HOSPITAL
412.00 · Medical`. This is 1.x's `Transaction.category_id`. Dies on the transaction ruling
(the line is the bank's statement; the movement is unminted) and on Rob's constraint (a source's
category establishes nothing about the identity of what it categorises); it also cannot hold an
expense with no movement (fully covered, Ex5) or one with several (Ex7).

**X2 — an expense is an obligation.** The bill *is* the expense. Dies on the obligation slice
(§6: different referents) and on the cases both ways: an expense with no obligation (Ex5), an
obligation with no expense (Ex6, a loan).

**X3 — an expense is an event identity: the incurrence the household individuates** — a
visit, a purchase, a service received — minted by a Person's assertion, anchor a pointer to that
act and nothing else. Its nature (health, on which axis; care necessity; a category), its date
of service, its provider, who incurred it, and its amounts (billed · allowed · plan-paid ·
patient responsibility · what the household paid) are **claims** by their knowing parties. Bills,
EOBs and bank lines *concern* it. Obligations and payments *relate* to it by claims. The
insurer's claim record is the insurer's statement *about* it.

**X4 — an expense is the insurer's claim.** The EOB's claim number individuates it. Dies as T3
did for transactions: an institution-side identifier is correspondence evidence, never
Groundwork identity; and it cannot hold the plumber, the pharmacy, or any expense never
submitted. *(What "the claim" is, as item 4's second referent, is a separate record — §7 notes
the parallel.)*

X3 is tested.

---

## 3. The cases

| # | Case | Ruled in | Under X3 |
|---|---|---|---|
| **Ex1** | Rob: "We took Kim to the ER on Feb 14." | minting | one utterance mints expense **X**; the same act evidences claims about X: date of service (Feb 14, `as_of`), provider Riverbend Hospital (a role claim), incurred by Kim (a role claim), nature *health* (the D1 claim — subject X, at last). "Feb 14" and "Riverbend Hospital" are **content / participants**, never identity |
| **Ex2** | The card line `MERCY HOSPITAL 412.00`, bank category *Medical*. | Tx8, Rob's constraint | a proposition from a capture; concerns X once Rob says so (`proposition_concerns`); **the bank's category is the bank's stance — content — and at most a candidate for a classification claim about X. It establishes neither X nor X's nature.** Before Rob individuates X, the line's category is a stance about nothing minted |
| **Ex3** | Lakeview Health's EOB: billed $1,300 · allowed $853 · plan paid $568 · patient responsibility $412 · claim #A77. | Cluster B, slice 8 | an artefact (origin Lakeview Health); its readings yield P-subject claims with X as a *not-established-with-candidates* participant; `artefact_concerns(EOB, X)` asserted by Rob; **claim #A77 is content and correspondence evidence** — the insurer's identifier for its record of X, never X's identity |
| **Ex4** | Riverbend Hospital's bill for $412. Rob: "that's the ER visit — I owe Riverbend Hospital for it." | Ob2 | the bill concerns X; the same utterance mints the **obligation** O (Ob2, unchanged) — a *separate* identity; the relation between O and X (*O arises from X*) is a **claim** the §7.7 consumers need (care necessity is read off the underlying expense) — **its kind is not ruled here** (§5) |
| **Ex5** | A fully covered wellness visit: billed $250, plan paid $250, patient responsibility $0. | §7.7 | **X with no obligation** — the household individuates the visit (it matters for the plan's accumulators and the tax record) and nobody owes anything. X2 cannot represent it |
| **Ex6** | The mortgage. | obligation slice | **an obligation with no expense** — nothing was incurred as an event; X2 cannot represent that either |
| **Ex7** | One ER visit: bills from the hospital, the radiologist and the lab. | correspondence | the household individuates **one X** ("the ER visit") with three obligations arising from it — or three expenses if it individuates per service; either is legitimate; two minted expenses later said to be one visit are `expense_corresponds`. Individuation is the household's, as for obligations |
| **Ex8** | Kim's prescription at CVS: a card line, no bill, no EOB yet. | D1 | Rob mints X ("Kim's prescription"); the line concerns it; the health claim is Rob's; when the pharmacy claim's EOB arrives it concerns X too. **The two CVS rows of the sensitivity ruling** — the manufactured classification — are exactly this shape, with the classification asserted rather than manufactured |
| **Ex9** | The classifier (MCC 8011 → *health*) proposes a nature for the line. | decision 9, O9 | a **candidate** for a classification claim about X — a process cannot utter; the claim exists when a party asserts it (Rob confirms) and is otherwise the manufactured flag's territory, which stays where the sensitivity ruling put it: *not voiced unless asserted* |
| **Ex10** | The bank says *Medical*; Rob says *dental, not covered*. | two-axis space | two stances by two parties on the nature of X — the two-axis space has room for both to be true on different axes or one to be wrong; nothing chosen; the classification doctrine's `Unknown` remains the terminal where nothing is asserted |
| **Ex11** | "That charge wasn't the ER — it was Kim's follow-up on the 20th." | Case B | retract the *concerns* claim and assert a new one (or mint the follow-up as X′); X remains; the line's content is untouched |
| **Ex12** | The 1.x rows. | shipped-vs-target | `HealthcareExpense(id · incurred_on · created_at)` is **already an identity-only row** — the closest 1.x comes to a 2.0 anchor; it lacks the minting utterance and carries `incurred_on` as structure where 2.0 makes it a claim (as the payment's occurred date is). `Transaction.category_id` is a classification of an **unindividuated movement** — a stance about nothing minted; it cannot be re-homed onto an expense nobody asserted. Blocker unchanged: zero `Person` rows |

**X3 survives every case.** What the cases fix:

- **An expense is an event identity the household individuates** — the incurrence — minted by a
  Person's assertion; identity = the minting act and nothing else (Ex1). The 1.x author had
  reached "identity only" already (Ex12); 2.0 adds the provenance and moves `incurred_on` to a
  claim.
- **Nature is a claim, never structure** (Ex1, Ex9, Ex10): health-on-axis, care necessity, a
  category — asserted by a party, candidates from a process or a bank's label; the manufactured
  flag and the narrator's assertion rule stand. **A source's category establishes neither the
  identity nor the nature of what it categorises** (Ex2) — Rob's constraint, structural.
- **Expense ≠ movement** (Ex2, Ex5), **≠ obligation** (Ex4, Ex5, Ex6), **≠ the insurer's claim**
  (Ex3): the line concerns it; the obligation arises from it by a claim; the EOB is a statement
  about it with an identifier that is evidence.
- **Individuation is the household's** (Ex7): one visit or three services; correspondence repairs.
- **D1 and D3 acquire their subject.** D1 = a nature claim with subject X; D3's P-world becomes a
  value claim with subject X (the world event), while P-subject stays with the artefact.

---

## 4. What may refer to, relate to, or concern the expense

| Referent / participant | Relation | Status |
|---|---|---|
| another **expense** | `expense_corresponds` — slice 4's shape, a sixth type (Ex7) | ruled shape |
| a **party** | *incurred by* (the patient / consumer) · *provided by* — dated role claims | role claims, catalogue unruled |
| an **obligation** | *O arises from X* — the relation the §7.7 consumers read care necessity through (Ex4) | **a claim between two identities of different types; its kind is its own ruling** (§5) |
| a **payment** | a payment *toward* an obligation arising from X; or, with no obligation, a payment *for* X (Ex8's card purchase) | the second is a relation claim between payment and expense — **not ruled here**; note it alongside `toward` |
| a **plan** | which plan covered X — *derived from the coverage period covering the date of service*, the 1.x row says; in 2.0 a plan identity (item 4's third referent) and a claim or derivation | deferred to the plan record |
| an **artefact** — a bill, an EOB, a receipt | `artefact_concerns(A, X)` — the slice-8 kind, gaining an expense object slot as its ruled growth path | ruled kind, slot not yet added |
| a **line** in a statement or EOB | `proposition_concerns(P, X)` | ruled kind, slot not yet added |
| a **classification** | a nature claim *about* X — a domain proposition with subject X (D1) | the kinds are the catalogue; the shape is ruled |

> **Invariant (Rob's constraint, made structural):** a source's category is content of a
> proposition about a movement or a line; it is at most a candidate for a classification claim
> about an expense; it never mints an expense and never establishes its nature.

---

## 5. Not decided here — fences and findings

- **The obligation ↔ expense relation** (*O arises from X*) — forced by Ex4 and by §7.7's
  consumers; a claim between identities of two types (not correspondence, not about-ness); the
  first of a **relation family** the queue keeps meeting (payment ↔ payment at reversal;
  obligation ↔ obligation at Ob6; payment ↔ expense at Ex8). **Not named or ruled here;** the
  family treatment (item 6) now has four members pressing it.
- **The insurer's claim** — item 4's second referent. The parallel with the transaction ruling is
  strong (an EOB is the insurer's statement about the expense; the claim number is an
  institution-side identifier) and would dissolve "claim" as an identity the way "transaction"
  dissolved; **its own record decides**, not this one.
- **The plan** — item 4's third referent; the 1.x row derives coverage from the date of service.
- **The classification catalogue** — the two axes' kind names; care necessity; categories. Shapes
  ruled, values the domain's.
- **Relational knowing for nature claims** — the household member who *incurred* X (a role,
  unruled) and the insurer that adjudicated it; `undetermined` until the roles are ruled, as
  built.
- **The four determinations** (`provider_adjustment · user_paid_cash · unpaid · pending_claim`) —
  reconciliation stances about amounts of an expense/obligation; claims by their parties;
  consumers of the identities, item 7.
- **Legacy decomposition** — `HealthcareExpense` is yes-shaped and blocked on the asserting party
  (no Person rows); `Transaction.category_id` is a stance about nothing minted and stays 1.x.

---

## 6. Ruling candidate — for Rob

> **An expense is an event identity: the incurrence the household individuates — a visit, a
> purchase, a service received — minted by a Person's individuating assertion; the asserting
> utterance is the minting act, not the expense; minting establishes the identity, not the truth
> of any property asserted about it. The anchor is structure plus a pointer to the minting
> utterance and nothing else: date of service, provider, who incurred it, nature on either axis,
> care necessity, category, and every amount — billed, allowed, plan-paid, patient
> responsibility, household-paid — are claims about the expense, made by the party knowing for
> that claim, with the roles that make them knowable ruled later. A source's category for a
> movement or a line is content of the source's statement and at most a candidate for a
> classification claim about an expense; it never mints the expense and never establishes its
> nature — and a classification a process proposes is a candidate until a party asserts it. An
> expense is not a movement (it may have none, or several), not an obligation (each exists
> without the other; the obligation that arises from an expense is a separate identity related
> to it by a claim whose kind is not ruled here), and not the insurer's claim (the EOB is the
> insurer's statement about the expense and its claim number is correspondence evidence).
> Bills, EOBs, receipts and lines concern the expense by the concerns kinds; two separately
> minted expenses later said to be one incurrence correspond and are never merged. The 1.x
> `HealthcareExpense` row is already identity-only and is decomposable into this identity where
> its asserting party is a fact, which today it is not; a 1.x transaction category is a stance
> about nothing minted.**

**If ruled**, implementation follows the obligation / payment identity shape: an `expenses`
anchor; additive expense slots; `expense_corresponds`; the expense object slot on
`artefact_concerns` and `proposition_concerns`; a fixture over Ex1–Ex12 with the not-derived
consequences asserted (no nature on the anchor; a category never mints; D1 representable as a
claim with subject X; the obligation ↔ expense relation asserted *not built*); no data step.
**Outside it:** the relation family · the insurer's claim · the plan · the classification
catalogue · the determinations · any consumer.

*The line: a bank can say what it was billed as; an insurer can say what it allowed; only the
household can say what happened — and what happened is the expense.*
