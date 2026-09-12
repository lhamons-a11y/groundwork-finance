# §7.7 *carries* — the doctrine test, run on two cases

> Status: **Doctrine test, 2026-09-12. No decision. No enum, no schema, no M1/M2.**
> Rob opened the §7.7 question narrowly, and this document runs his test and nothing else:
>
> > **What is the object whose continuity *carries* is required to preserve?**
>
> Three candidate answers, held open, none chosen here:
>
> ```text
> M-OBL   obligation-centred      the underlying obligation and its identity/history carry
>                                 through disposition
> M-LED   creditor-ledger-centred what carries is the creditor/account-side state needed to
>                                 understand what happened on its books
> M-ABS   defined abstraction     carries operates over a deliberately defined combination of
>                                 obligation + creditor/account state
> ```
>
> **The test, Rob's, applied per model per case:**
>
> > *For each possible definition of disposition scope, what information becomes logically
> > mandatory for a later observer to understand what was disposed of — and what information
> > remains merely historical context?*
>
> **Evidence admitted: two cases.** The bad-debt write-off (`DISPOSITION_VOCABULARY_CASES.md`
> 4b, the blocker's boundary test) and recourse patient financing
> (`OBLIGATION_LIFECYCLE_QUESTION.md` §9–10). Nothing else from the board is pulled in; where a
> cell needs something the two cases do not supply, the cell says so rather than borrowing.
>
> **The rule under test, as §7.7 wrote it:** *an obligation is a healthcare cost when the
> provider carries it at no interest; a credit card when a lender carries it.* The downstream
> behaviour that rule controls is what §0.2 protects (care is not called a failure) and what
> §7.4 escalates (a cliff). So "the object whose continuity carries preserves" is the object
> those two behaviours read.
>
> **Fence.** Disposition scope is kept separate from any implementation question. A
> preservation requirement is not admitted because information *could be useful later* — only
> because a later observer *cannot understand what was disposed of without it*.

---

## 0. The two cases, as recorded

**W — the bad-debt write-off.** $50 of patient responsibility. The user did not pay. The
provider removes it from collectible balance **on its own books**. The account may still be
sold, pursued, or reported. One party. Nothing changes hands. The blocker's rule: the write-off
*must not by itself establish* that the obligation was extinguished, settled, waived, reversed or
otherwise disposed of.

**R — recourse patient financing.** The provider transfers the receivable to a financing vendor
for cash up front and **retains contingent liability**. The vendor funds and services; the
provider bears the loss on default. The user defaults; **the account returns to the provider**
(repurchase, refund of part of the advance, or a reserve charge). Round trip: provider → vendor →
provider. The return is *precipitated* by the user's non-payment but *constituted* by a contract
Groundwork cannot see. The user may not be told; Groundwork learns late — effective March,
recorded September — and *may not be able to observe it at all* (§9 consequence 4). Amounts
unchanged throughout; the case is about who holds, not how much.

**What "a later observer" means here.** Whoever reads the record after the fact — `as_of`, the
Historian, the narrator — and has to say a true sentence to the household about what happened.
The test's *mandatory* is what that sentence cannot be built without.

---

## 1. The six cells

Each cell: **mandatory** (the observer cannot understand what was disposed of without it) ·
**context** (true, recordable, not needed for that) · **the sentence** the observer can then say
· and whether the cell **holds**.

### M-OBL — obligation-centred

**W.** What happened to the obligation? *Nothing that the write-off establishes.* So under
M-OBL, **there is no disposition** — the write-off is a creditor-side fact about an obligation
that continues.

- *Mandatory:* the obligation's identity and the fact that it remains owed; **who is entitled to
  collect it** (still the provider), because the write-off's stated consequences — sold, pursued,
  reported — are all changes or exercises of *that*, and a later letter from an agency has to be
  attachable to *this* obligation rather than read as a new one.
- *Context:* the write-off event itself — its date, its source, that it happened. Useful for
  explaining a later sale or a credit-report entry; not needed to understand what was disposed
  of, because nothing was.
- *Sentence:* *"Your provider has stopped treating this as collectible on its own books. You may
  still owe it, and it may still be sold or reported."* True, and buildable from mandatory +
  context.
- **Holds.** And it holds *because* the model refuses the disposition: the blocker's rule is not
  a constraint bolted onto M-OBL, it is what M-OBL says.

**R.** What happened to the obligation? Its **entitled-to-collect party changed twice**; funding
and servicing changed with it on the outbound leg; economic risk never moved (the provider bore
it throughout — that is what *recourse* means). Amounts unchanged. Under M-OBL the disposition
subject is the obligation's continuity across those changes.

- *Mandatory:* obligation identity across all three states — so a payment to the vendor in month
  three and a letter from the provider in month nine are the same obligation; **the entitled
  party at each effective date**, with **both** the effective date and the learned date (the
  March/September separation, which §10 already made mandatory for exactly this case); and the
  **source** of each transition — a statement, a letter — because rule 1 forbids establishing
  the transition from payment behaviour.
- *Context:* who funded (the vendor's cash advance is between vendor and provider); who
  serviced (operationally important — whom to call — but the household owed the same amount to
  the same obligation throughout); who bore the risk (invisible to the household, and the *cause*
  of the return leg — cause is orthogonal to disposition by the candidate structure's own rule).
- *Sentence:* *"This was owed to your provider, then to [vendor] from March, and to your
  provider again from [date] — we learned of the return in September. The amount did not
  change."* True, and buildable.
- **Holds.** The recourse case's four consequences all land inside M-OBL without strain:
  "not one fact" becomes *one mandatory dimension and three context dimensions*; round trips are
  two entitlement transitions; the feedback path from payment state is rule 1; late discovery is
  the dual date.

**M-OBL survives both cases.** Its mandatory set is small and the same in both:

```text
obligation identity  ·  entitled-to-collect over (effective, learned) time  ·  source of each change
```

### M-LED — creditor-ledger-centred

**W.** The disposition is real and complete: $50 leaves collectible balance on the provider's
books — bad debt, allowance, whatever the entry is.

- *Mandatory:* whose books (the provider's); the account on those books; the entry's kind and
  date.
- *Context:* the household's obligation as such. M-LED does not describe it.
- *Sentence:* the observer can say exactly what was disposed of — *"the provider wrote $50 off"*
  — and **cannot say whether the household still owes it**, because the model holds no fact about
  that. The sentence M-LED licenses without a further fact is *"it is gone"*, which is the false
  one the boundary test exists to catch.
- **Holds as a description of the ledger; fails as a teaching.** To avoid the false sentence
  the observer needs a second fact — *this disposition is on the books, not on the obligation* —
  and the moment that fact is mandatory, the model is carrying obligation state beside ledger
  state. That is M-ABS, not M-LED.

**R.** The dispositions are on **two parties' books**: the vendor's (receivable acquired;
receivable repurchased out) and the provider's (receivable sold; contingent liability
recognised; receivable re-recognised on return). Five entries for what the household
experiences as one bill that changed hands and came back.

- *Mandatory:* whose books for every entry — so M-LED needs multi-party account identity from
  the outset; the receivable's identity across books, so that the vendor's account and the
  provider's account are known to be about one thing.
- *Context:* the household's obligation, again unrepresented.
- *Sentence:* none the observer can build, **because none of the mandatory information is
  observable from where Groundwork stands.** The household receives statements and letters —
  evidence *about the obligation*. It never sees the vendor's ledger, and §9 consequence 4 says
  it may not be told of the return at all. Under M-LED the only way to fill the mandatory slots
  is to infer book entries from household-side events — *payments stopped, therefore the vendor
  must have repurchased* — which is rule 1's forbidden inference, arriving as the model's
  **only** way to satisfy itself.
- **Fails.** Not on expressiveness — the ledger model expresses recourse perfectly — but on
  **evidentiary reachability**: it makes mandatory what no evidence available to Groundwork can
  supply. A doctrine whose mandatory information can only be manufactured is a doctrine that
  will be satisfied by manufacture.

**M-LED fails R outright and fails W's sentence.** The two failures are different kinds and
should not be merged: W is a *teaching* failure (true description, false implication); R is a
*reachability* failure (the subject of the disposition is on the far side of a boundary
Groundwork cannot see across).

### M-ABS — defined abstraction over both

**W.** Expressible cleanly: books component = terminating; obligation component = unchanged. The
divergence between them *is* the case's content.

- *Mandatory:* both components, and — this is what makes it an abstraction rather than two
  fields — the rule that **neither fills the other**: a books fact may not be read as an
  obligation fact (the blocker), and an obligation fact does not imply a books entry.
- *Context:* nothing left over; both slots are doing work.
- *Sentence:* *"The provider wrote this off; it is still owed."* Both halves true, each sourced.
- **Holds** — at the price of two independently-sourced slots per disposition. And note what
  the obligation slot holds when its evidence is missing: *unknown*, and the sentence becomes
  *"the provider wrote this off; whether you still owe it, Groundwork does not know."* That is
  honest. It also means the obligation slot's *presence* is mandatory while its *value* may be
  unknown.

**R.** Obligation component: entitled party changed twice, as M-OBL. Books components: the five
entries, as M-LED — **and unobservable, as M-LED.**

- If M-ABS makes **both** components mandatory, it fails R exactly as M-LED does: the books
  slots can only be filled by inference.
- If M-ABS makes the obligation component mandatory and the books component *optional-when-
  evidenced*, then in R the books slots sit at *unknown* forever and the model behaves as M-OBL;
  and in W the books slot holds the write-off as a sourced fact — which is precisely what M-OBL
  called *context*.
- **Holds only in the second form, and in that form it is M-OBL with a name for its context.**
  M-ABS is not a third survivor; it is either M-LED's failure or M-OBL's structure.

---

## 2. Result

| | W — write-off | R — recourse | Survives both? |
|---|---|---|---|
| **M-OBL** | holds; no disposition, and that is the rule | holds; two entitlement transitions, dual-dated, sourced | **yes** |
| **M-LED** | describes the ledger, licenses the false sentence | mandatory information unobservable; satisfiable only by inference | no — two different failures |
| **M-ABS** | holds, two sourced slots | fails if both slots mandatory; collapses to M-OBL if not | not as a distinct model |

**One model survives both cases, and the cases do not ask for a fourth formulation.** What they
ask for instead is a *name* — see §4.

**The object whose continuity *carries* is required to preserve**, as the two cases answer it:

> **The household's obligation, identified across changes in the party entitled to collect it.**
> Funding, servicing and risk are context — except where a change in one of them *is* a change
> in entitlement, which is the only reason any of them enters the mandatory set.

This is consistent with what the case pass found from the other direction (`DEPENDENCY_CASE_
RESULTS.md`, cluster A): *disposition = obligation* makes entitled-to-collect the mandatory
dimension. The doctrine test arrives there from the object rather than from the dimension.

---

## 3. What the test does not prove — stated so it is not assumed

1. **Entitlement versus the authorised payee.** In both cases the servicer *is* the entitled
   party or acts for it (vendor funds and services; provider does both before and after). The
   cases therefore cannot separate *who is entitled to collect* from *to whom a payment validly
   discharges the obligation*. A servicing-only arrangement — provider keeps the receivable, a
   billing company sends the statements — would separate them, and it is not one of the two
   cases. **So the mandatory dimension is established as *entitlement-or-payee*, not resolved
   between them.** Do not read this document as having chosen.
2. **That books events are never household-visible.** The reachability failure was proven on R,
   where §9 says the return may be unobservable. On W, a write-off *can* reach the household —
   a statement line, a credit-report entry, a cancellation-of-debt form. M-LED's W failure is the
   sentence, not reachability. The two failures were kept apart above for this reason.
3. **That §7.7's rule survives with its object changed.** The rule reads *provider carries at no
   interest → healthcare cost; lender carries → credit card*. Under M-OBL "carries" means
   *is entitled to collect*, and on R's outbound leg a vendor is entitled — so the rule would
   reclassify the same obligation as a credit card in March and a healthcare cost again on
   return, with no change in what the household owes or in the interest rate. Whether that is
   the behaviour §0.2 and §7.4 want, or whether the rule was reading a *different* dimension
   (risk? interest-bearing?) all along, is exactly the question Rob posed — *what downstream
   behaviour is the distinction supposed to control* — and the two cases do not answer it. They
   show only that entitlement is what disposition needs; they do not show it is what
   classification needs. **Those may be two objects.**
4. **Anything about M1/M2.** The test never needed to ask whether the returned obligation is the
   same object or a successor; under M-OBL both cases were answerable with *identity across
   changes*, which either anchoring can provide. The fence did not fire because nothing crossed
   it.

---

## 4. What M-OBL would demand, if chosen — consequences to check, not requirements adopted

Recorded so that choosing it is done with its costs in view. None of these is a decision.

- **From evidence:** the record must be able to say whether a piece of evidence is *about the
  obligation* or *about the creditor's books*. A write-off letter and a waiver letter are the
  same paper with opposite consequences, and only the entitled party's statement about
  entitlement can dispose under M-OBL. This is a demand on what evidence can express; it is
  named here and not opened.
- **From the record:** every entitlement transition carries effective-at and learned-at (already
  mandatory per §10) and a source (already rule 1). M-OBL adds no dating or sourcing requirement
  the recourse case had not already forced.
- **A name for what W leaves over.** Under M-OBL the write-off is "context", and the word is too
  weak for what it does: it changes the household's *exposure* — collection, sale, reporting —
  without changing their *obligation*. That is not a disposition and not nothing. The two cases
  do not force a fourth model; they force M-OBL to say what it calls a creditor-side event that
  alters exposure and not obligation. Unnamed here on purpose.

---

## 5. Decision remaining — Rob's

Whether the object is the obligation across entitlement (M-OBL), or whether §7.7's classification
behaviour is reading a different dimension than disposition needs (§3 item 3), in which case the
question splits into two objects before either is chosen. The test's contribution is narrower
than an answer: **it eliminated M-LED on evidentiary grounds rather than expressive ones, showed
M-ABS is not a third option, and located the one distinction the two cases cannot make.**
