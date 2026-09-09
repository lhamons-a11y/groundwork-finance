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
| **E** | Obligation transferred **while arrears exist** | carrier version; arrears carried, **fee delta disposed of** (§7) | successor **must re-express** the arrears |

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

> **Partly corrected in §7.** The claim below that a sale requires no disposition under M1 is
> wrong — §8.1 of the module design already records that the agency's figure diverges from the
> original. M1's advantage here is a delta rather than a restatement, which is smaller than
> what this finding originally claimed.

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
2. ~~Confirm finding 2~~ — **done, §9.** Well-supported: the CFPB's taxonomy puts the creditor
   at a lender for every deferred-interest medical product in its scope. C stays out of the
   deciding set.
3. **New, and ahead of 1:** §9 found that **recourse financing breaks §7.7's single-carrier
   assumption** — the provider transfers the receivable, retains contingent liability, and takes
   the account back on default. Whether the carrier rule classifies on servicing or on risk is a
   **doctrine question and Rob's**, and M1/M2 cannot be settled while it is open, because it
   changes what counts as a transition at all.
4. Then 8.1 and 8.2 as consequences.

**Not open, and not waiting on any of the above:** the economic-transfer invariant — stated
generally in §5, and applying to sales as well as restructures per §7's correction — the
explicitness of instrument kind (`NOT NULL`, no default, never computed), and the zero-consumer
condition on `core/payment_plan.py`.

> **No schema fields are proposed in this document, deliberately.** Per `e74d673`'s method note:
> decide the semantics the schema must preserve, then derive the schema.

---

## 5. The economic-transfer invariant, stated generally

*(Rob, 2026-09-09. The earlier phrasing made this look like a property of one model.)*

> **Whenever economic terms change, every amount whose economic treatment changes must have an
> explicit, reconstructable disposition.**

M1 and M2 then determine only **where that disposition is represented** — on a version, or on a
succession edge. That is materially cleaner than saying *"M2 needs transfer accounting"*, which
framed an invariant as a cost of one branch and would have let the other branch appear to
avoid it.

## 6. The trade, and the principle that decides it

**M1 — surviving obligation**

- *For:* less structural churn; no succession edges; simple historical identity.
- *Risk:* **a material change in counterparty and legal posture looks like a small attribute
  mutation.**

**M2 — succession**

- *For:* an explicit boundary; the narrator can say *"this obligation was transferred from X to
  Y on date Z"*; old and new contexts stay independently reconstructable.
- *Cost:* everything crossing needs explicit economic disposition, and **arrears and balances
  become much easier to double-count if succession is implemented lazily.**

**Not decided by which schema is simpler.** Rob's principle:

> **Does the distinction between old and new obligation materially change what Groundwork is
> entitled to explain to the user?**

## 7. What the existing doctrine already says about that

§8 of `HEALTHCARE_MODULE_DESIGN.md` turns out to answer the *entitlement* half directly, and it
was written long before this question was asked:

> *"A hospital bill and a collections account are not the same object, and §7 assumed a hospital
> throughout… Everything in §7 has to be re-derived here, and one thing in it becomes actively
> dangerous."*

Four commitments already made, each bearing on the principle:

1. **They are not the same object** — stated, not implied.
2. **§7's derivations do not carry over.** They must be re-derived, and one becomes dangerous.
3. **Both figures are kept.** §8.1 records the *original creditor* and *original amount*
   alongside the agency's, because *"the gap between them is sometimes the whole story."*
4. **What may be said changes.** §8.2a attaches a premise to every collections figure — *"this
   is what you would pay if you agree that you owe this… Groundwork has no way to know whether
   you do"* — which a hospital-bill figure does not carry. That is, literally, a change in what
   the app is entitled to explain.

Plus a fact set that exists only after transfer: agency name, date of first delinquency, whether
debt validation was requested and received.

**What this establishes, and what it does not.** It establishes that the distinction **is**
material by Rob's criterion — the entitlement changes, in writing, already. It does **not** by
itself select M2, because M1 can carry a versioned carrier fact plus a dated collections fact
set and obtain the same entitlement change from the version rather than from a succession. The
doctrine forces the **distinction**; it does not force the **succession**.

Worth stating that carefully rather than letting it flatter M2 — principle 7's tell is a
measurement that suits an argument one already found appealing.

### And a correction to finding 3

Finding 3 said that under M1 a transfer means *"no economic transfer occurs and no disposition
is required."* **§8.1 contradicts that.** The agency's figure diverges from the original once
fees are added — the design says so explicitly and treats the gap as significant. So a sale
*does* change economic terms, and the invariant in §5 applies to it under **both** models.

M1's advantage in scenario E is therefore narrower than stated: not *no disposition*, but *a
delta rather than a restatement*. Still a real difference, and a smaller one than claimed.

## 8. The carrier claim stays separate

Finding 2 rests on an **external-domain assertion** — that a deferred-interest promotional
balance is lender-carried from origination. The repository cannot establish it, and it is not
established here.

**And the sharper form of the caution:** one concrete product example must not quietly become
the universal healthcare instrument rule. CareCredit behind Synchrony is *one* arrangement.
Whether every promotional medical balance is lender-carried — or whether some providers carry
deferred-interest terms themselves — is exactly the kind of generalisation-from-one-instance
that principle 5's inventory questions exist to catch.

**Until verified, finding 2 is a hypothesis**, and scenario C stays out of the deciding set on
that basis rather than on a settled fact.

---

## 9. The carrier claim, verified — and what the verification turned up instead

*(2026-09-09, external sources listed at the end. Run as its own step, per Rob: verify the
external-domain fact rather than letting a plausible assumption become a domain invariant.)*

### The narrow claim: CONFIRMED, and on better evidence than one product

CareCredit's creditor is **Synchrony Bank**; the promotional structure is deferred interest at
~32.99% charged retroactively from the purchase date. That was the one instance, and on its own
it would not have been enough.

**The CFPB's own taxonomy is what makes it more than an instance.** Its May 2023 report divides
medical payment products into **medical credit cards** and **medical installment loans**, and
states that *financial institutions and fintech companies are the creditors, not healthcare
providers* — the firms market through providers and service the credit and loans themselves.
Deferred interest appears in **both** categories, across ~$20bn of purchases and ~$1bn of
deferred interest charged over 2018–2020.

And the report **explicitly does not cover** provider-administered or in-house plans; it treats
them as a different thing. Which is the answer to the generalisation worry: within the scope of
products that carry deferred interest, the creditor is a lender, from origination.

**What remains unestablished:** that no provider anywhere runs an in-house deferred-interest
plan. No counterexample was found — in-house plans are described as low- or no-interest, and one
charging interest triggers Reg Z disclosure — but *absence of a counterexample in four searches
is not proof of absence.* Finding 2 is now **well-supported rather than proven**, which is
enough to keep scenario C out of the deciding set.

### The finding that matters more: recourse financing breaks the binary

§7.7's rule assumes **one carrier**: the provider carries it, or a lender does. A third
arrangement is common and fits neither.

In **recourse patient financing**, the provider transfers the receivable to a financing vendor
for cash up front, and **retains contingent liability**. On default, *the debt is returned to
the healthcare provider* — the provider may be required to repurchase the account, refund part
of the advance, or absorb a reserve charge. Non-recourse is the opposite: a delinquent account
stays with the vendor permanently.

And the sting: **recourse is frequently what makes 0% APR possible.** The benign
provider-plan-at-0% that §7.7 treats as the safe case is, in a substantial share of real
arrangements, a recourse arrangement with a vendor in the middle.

### Four consequences, all bearing on the governing question

1. **"Who carries it" is not one fact.** Recourse splits *servicing and funding* from *risk*.
   §7.7's rule classifies on a single carrier, and here there are two parties with different
   claims to being it. **This is a doctrine question, not a modelling one**, and it is Rob's.
2. **Transitions can be round trips.** provider → vendor → **back to provider**. Under M2 that
   is three agreements for what the user experiences as one bill; under M1, three carrier
   versions on one obligation. This is scenario E occurring twice, in opposite directions.
3. **The return is triggered by the user's own non-payment.** So a lifecycle transition can be
   *caused by* the adherence state the payment model computes. Neither M1 nor M2 anticipated a
   feedback path from payment state back into obligation identity.
4. **The user may not be told, and Groundwork may not be able to observe it.** Neither source
   would establish whether patients are formally notified of a recourse return. That does not
   weaken *a sale is never silent* — it **relocates** it. Groundwork cannot promise to detect a
   transition; it can only promise that once known, it is dated, sourced and reconstructable.

**And a concrete requirement follows from 4**, derived rather than chosen: a carrier change will
routinely be discovered **late**, from a statement or a collection letter, with an effective date
in the past. So the record needs `effective_on` in the past with `recorded_at` now — the
effective/recorded separation the repository already uses in `ExpenseFundingAllocation` becomes
**mandatory here rather than merely good practice**, under either model.

### Sources

- [CFPB — report on medical credit cards and financing plans (May 2023)](https://www.consumerfinance.gov/about-us/newsroom/cfpb-report-highlights-costly-credit-cards-and-loans-pushed-on-patients/)
- [CarePayment — recourse vs. nonrecourse financing](https://www.carepayment.com/recourse-vs-nonrecourse-financing/)
- [Help Financial — recourse vs. non-recourse patient financing](https://www.helpfinancial.com/blog/recourse-vs-non-recourse-patient-financing-understanding-the-trade-offs)
- [HFD — what is a 0% APR patient financing program](https://gohfd.com/what-is-a-0-apr-patient-financing-program-a-clear-guide-for-providers/)
- [CareCredit — FAQs](https://www.carecredit.com/faqs/)

*(The CFPB's source PDF would not convert — the newsroom summary of the same report was used.
Noted so the citation can be re-checked against the primary document.)*
