# Lifecycle attack — the second review pass

**A review artifact for the healthcare module**

> Status: **Review artifact. Does not modify the underlying design blueprint.**
> Written 2026-09-06 by Rob, following `ARCHITECTURE_REVIEW_P0.md`. Companion to it.
>
> The method: run every proposed entity through **create → edit → correction → import →
> duplicate → refund/reversal → plan change → year rollover → delete**, assuming every field
> will eventually be wrong, duplicated, edited, imported late, partially populated, or deleted.
>
> The question is not *can this field represent the happy path*. It is:
> **can Groundwork preserve its invariants after five years of ugly real-world history?**

---

## The unifying diagnosis

> **A piece of mutable state is pretending to be historical truth.**

Every finding below is that bug wearing different clothes. Circle any field named `status`,
`current_balance`, `protected`, `reimbursed`, `validated`, `eligible`, `current_plan`,
`reserve_target`, `confidence` and ask: **is this a fact, or a conclusion derived from facts?**
If derived, storing it creates a synchronisation risk and eventually a contradiction:

```text
health_protected = false     health_classification = medical
reimbursed = true            reimbursement_total = $0
tax_eligible = true          qualifying_amount = $0
```

---

## 1. `health.py` must not own the truth

The temptation is to let one module determine healthcare, protection, tax treatment, reserve
eligibility, reimbursement and privacy. That is too much authority in one place.

**Create.** A classification of "likely healthcare" cannot silently become a fact. It needs
`classification`, `classification_source`, `classification_version`, `classification_at` — or
six months later the app cannot answer *why did you consider this healthcare?*

**Edit.** `Amazon → Medical` creates a new fact. Overwriting `health = true` destroys the
history of how the classification happened. Original / current / history must be separable.

**Correction.** *"That's not medical, it was a television"* must reverse every consequence
derived from the old classification — protection, reserve, healthcare totals, tax, reports,
generated explanations. **Changing a classification must invalidate or recompute every derived
fact that depended on it**, which is a real dependency problem the moment anything is cached.

**Import.** Re-encountering the same transaction: create, update, or duplicate? And when the
imported row has *better* healthcare metadata than the existing one, which wins? A deterministic
merge strategy is required, not an implicit one.

**Duplicate.** A bank import and a manual entry for the same $142.17 Walgreens charge — if one
is protected and one is not, which classification survives? This is why classification belongs
to the **canonical expense**, not to the imported row.

**Refund.** Without a relationship to the original, `$500 medical` + `$500 refund` reads as
`+$500 healthcare / −$500 ordinary income`, which corrupts the teaching layer.

**Plan change / year rollover.** Neither may rewrite history. An expense *occurred under* Plan
A; the current plan being B is a separate fact. A 2026 transaction stays a 2026 transaction.

**Delete.** If the record is physically removed, what happens to the classification, the
allocations, the tax figure, the reserve, the historian event, the audit trail?

**Verdict.** `health.py` is a **deterministic policy evaluator over facts**, not the owner of
them — which is the existing doctrine (*the application owns truth, the model interprets it*)
applied one layer down.

## 2. Reimbursement is a relationship, not a status

```text
Expense $1,000 → Insurance $300 · HSA $400 · User $300
```

**Edit.** Expense corrected to $1,200 and the allocations still sum to $1,000. The unresolved
$200 is **not an error — it is a state the system must represent.**

**Correction.** Insurance restates $300 as $250. Changing the number without retaining what
happened leaves the historian unable to explain yesterday's answer.

**Import.** An EOB arriving after the bank transaction is the normal case, so reimbursement
cannot be assumed to exist at expense creation. Asynchronous reconciliation is the default path,
not the exception.

**Duplicate.** The same EOB imported twice needs idempotency, but EOB identity may not exist.
A composite key (payer, person, provider, service date, claim reference, amount, source) gets
close — and where no authoritative identifier exists the honest answer is **possible
duplicate**, never *duplicate*.

**Refund vs reimbursement.** Must stay distinct: reimbursement is a third party funding an
expense; refund/reversal reduces or unwinds the expense itself. Collapsing them mangles tax and
reserve.

**Year rollover.** A 2027 reimbursement for a 2026 expense is a 2027 event affecting a 2026
expense. `expense_date` and `reimbursement_date` must both exist and must not be collapsed.

**Delete.** Money allocated against a non-existent expense is a corruption. **Hard deletion is
prohibited once financial relationships exist** — void instead.

## 3. Person is an entity, not an attribute

`person_id` is identity; `display_name` is presentation. Renaming Rob to Robert must not touch
history.

Reassigning a $400 expense from one person to another changes deductible accumulation, OOP
accumulation, HSA eligibility, tax reporting and reserve. **That is a financially meaningful
correction, not a cosmetic edit**, and it needs provenance.

Imported data saying `patient = "ROB L."` must map explicitly. Name matching is not identity —
`John` and `John Jr.` are the counterexample. Person survives plan changes; **coverage
enrolment does not**, so they are separate concepts. Deleting a person with 500 historical
transactions means `inactive`, never destroying the identity.

**Built 2026-09-07** — `core/person.py`, `tests/test_person_identity_fixture.py`,
`smoke_sections/s80_person_identity.py`. 29 assertions, 14 of 14 mutations detected.

The invariant that turned out to hold the rest together is not in the list above; it comes from
`HEALTHCARE_MODULE_DESIGN.md` §1.7. **The tax report is the household total**, so a
reassignment moves the attribution and must leave the household figure untouched — which is
what stops a reassignment being a way to move money. Everything else here is per-person
supporting detail hanging off that.

Two rules the implementation had to sharpen:

- **Exact-and-unique is a lookup; anything else needs an alias.** `John` resolves because
  exactly one person has that name; `Sam` resolves to **nobody** when two people are called
  Sam, because guessing between them is the same error wearing a coin flip. Both cases were
  missing from the first draft of the fixture and were found by mutation testing.
- **`per-person totals + unassigned == household total`, exactly.** An expense whose patient
  nobody recorded belongs to nobody — never to the only other candidate — and is reported
  rather than dropped. Absence is not zero, in attribution as in amounts.

## 4. Plan-year state is temporal history, not a current-state field

`current_plan_year = 2026` cannot explain history.

**Edit vs correction are different operations.** Discovering the deductible was $2,500 rather
than $3,000 corrects a fact that was always wrong; switching plans changes what is true going
forward. The system must know which one happened, and a correction preserves old value, new
value, source and timestamp.

**Late-arriving plan data is first class.** A January expense must be re-evaluable against plan
data that arrives in March.

**The critical case:** Plan A Jan–Jun, Plan B Jul–Dec. Mutating `plan_id` on the person destroys
the first half of the year. Historical expenses retain Plan A.

**Rollover is not `year += 1`** — accumulators reset according to the applicable plan. And a
historical plan record is effectively immutable; deleting Plan A strips context from every
expense under it.

**Built 2026-09-07** — `core/plan_year.py`, `tests/test_plan_year_fixture.py`,
`smoke_sections/s85_plan_year.py`. 27 assertions, 13 of 13 mutations detected.

**One decision made most of this list true for free: accumulators are derived on every read.**
A stored `deductible_met` has to be reset at a year boundary, recomputed when a correction
lands, and migrated when a plan is added — three chances to forget. A query over the expenses
in a period cannot forget. So there is no `rollover()` at all, and adding a plan structurally
cannot disturb an earlier one; both are asserted rather than assumed.

The assertion that matters most when it is wrong: **a year with no plan on file reports the
spend and `UNKNOWN`** — never `False`, never zero. How much was spent is a fact; whether it met
a deductible is an interpretation against terms that have not arrived. Telling someone their
deductible is unmet because nobody has entered their plan invents a fact about their coverage.
`unattributed` is reported beside the periods for the same reason: absence is not zero, and it
is never quietly added to whichever plan is nearest.

*A note on the mutation testing, because it produced a false alarm worth remembering.* Breaking
`plans(as_of)` alone did not change any answer — `terms_at` respects `as_of` independently, and
a plan and its first terms are written in the same breath, so hiding one hides the other. That
is a mutation the model **survives**, which is a different thing from one it fails to catch.
The honest mutation breaks the whole as-of path, and that one is caught.

## 5. The reserve is three things, not one

```text
reserve target · reserve balance · contribution history
```

A target's **basis** must be identified (OOP maximum, custom, historical spending), because a
user raising $6,000 → $8,000 is a preference change while a corrected OOP maximum is a fact
change, and they must not look alike. A new plan changing the target must be distinguishable
from the user changing it. Deleting a target must not delete the money.

**The failure this prevents:** *"You have $4,000 healthcare reserve"* when the truth is
*"$4,000 of your general cash is counted toward a $6,000 target."* Those are different claims —
the same class of error the net-worth surface already refuses to make.

**Built 2026-09-07** — `core/reserve.py`, `tests/test_reserve_fixture.py`,
`smoke_sections/s90_reserve.py`. 25 assertions, 12 of 12 mutations detected. **This closes the
P0 list.**

`held` and `counted` are separate figures and no single number stands in for the pair, so the
sentence above cannot be produced from the model's own output. `segregated` is true only when
money was actually set aside — a household with $4,000 of ordinary savings and no dedicated
fund is not holding a healthcare reserve, however close the arithmetic looks.

**The target is derived, and keeps no copy.** Design §1.4 makes the plan's out-of-pocket
maximum the honest target precisely because it is *computable from the user's own plan
document* rather than invented. So a target with that basis stores no figure and resolves it on
every read — which means correcting the plan moves the target with nothing to reconcile, and no
correction is recorded against the reserve because none happened. That is this session's
`allocation`/`plan_year` lesson applied before it could bite: one owner per fact.

**Three kinds of change, and a fourth state for not knowing.** `preference`, `fact` and
`plan_change` are distinguishable, and a derived target replaced without the caller saying why
records `unspecified` rather than guessing between the last two — principle 3, applied to a
classification instead of an amount.

**Not decided here:** whether the reserve is built before, alongside or after the last balance.
That is design Open Question 6, it is open, and the module has no opinion on it.

**Not yet persisted.** The reserve has no tables, unlike `person`, `plan_year` and the
obligation model. It belongs with the other §6.3 step-2 leftovers — providers, HSA and FSA as
funds — and wants a round-trip through the shipped schema before it is called done.

## 6. Provider plans need versioned terms and event history

A schedule change is a new effective-dated term, not an overwrite. A balance change **because a
payment occurred** and a balance change **because the original bill was corrected** are
different events with different meanings. An imported bank payment cannot be attributed to one
of several plans by merchant name alone — that is reconciliation. An obligation with payments
against it is never hard-deleted.

## 7. Collections are a temporal chain, not an account with a status

Ownership changes create a new relationship interval; they never overwrite. A balance moving
because of a payment differs from a creditor correction. A credit report arriving after the
account exists must match deterministically or the user gets the same debt three times — and
two collection records may be the same debt, the same debt with a different collector,
different debts from one provider, or old and new reporting records. **Account numbers are not
sufficient for duplicate detection.** Collections do not reset annually and must be explicitly
protected from any rollover logic. Resolution never destroys ownership or validation history.

## 7b. Two rules this produced

*Both now live in `ARCHITECTURE_PRINCIPLES.md` with the other four, since neither is
healthcare-specific.*

**States must represent reality, not the needs of their current consumer.**

> Do not collapse distinct states merely because the current consumer produces the same result
> from them. Preserve the distinction at the factual layer; let consumers collapse it only when
> their own rules permit.

Which protects against the failure this review kept meeting: **the first consumer becomes an
accidental schema designer for every future consumer.** `unpaid` and `pending_claim` are the
worked case; `reimbursed = true` was the same error one level down.

**Any interpretation that can change the meaning of a user-visible conclusion must be
version-identifiable.**

Not only the necessity floor. Tax classifications, adherence calculations, consequence
interpretations, solution eligibility — and arguably narrator transformations, where they
materially alter interpretation. **The consumer does not get to decide that versioning is
unnecessary because today it cannot distinguish two versions.** That is the non-collapse rule
again, applied to rules rather than states.

## 8. The cross-cutting requirement

The blueprint needs an explicit distinction between four things it currently blurs:

| | |
|---|---|
| **Facts** | transaction occurred · person was Rob · plan was A · amount was $500 |
| **Events** | payment · refund · reimbursement received · classification changed · plan changed · balance corrected |
| **Relationships** | refund reverses transaction · reimbursement funds expense · payment satisfies obligation · expense belongs to person · expense occurred under plan |
| **Conclusions** | healthcare · protected · qualifies · remaining OOP exposure · reserve target · payoff date |

**That distinction matters more than any individual function.**

## 9. The test to add

> **Can Groundwork reconstruct why the current answer is what it is?**

For any financial conclusion — *"you have $4,200 of covered healthcare exposure remaining"* —
the chain from conclusion → calculation → input facts → source events → provenance must be
walkable, and the records that produced the number must be showable.

If it cannot, the number may still be arithmetically correct and **Groundwork has lost the
receipt** — which contradicts the strongest idea in the project: *the app earns the right to
teach by showing receipts.* This is not a new principle. It is the existing one turned inward
on the app's own derived state.

---

## Contested — three points, argued rather than accepted

*These were pushed back on during review and the pushback stands unless overturned.*

### C1. "Never store derived conclusions" is incomplete — RESOLVED

The remedy of recomputing rather than storing fixes staleness and introduces
**non-reproducibility when the rules change rather than the data.** Run the 2026 tax report in
2028: same transactions, nothing edited, different answer — because the §213 threshold moved,
or an HSA limit did, or bureau policy changed. Pure recompute silently rewrites history on
every rule update, which is the same defect arriving from the other direction.

*Resolution, after pushback in both directions.* "A conclusion is itself an event" was wrong
and conflated two things — the record of having computed something, and the computing being
noteworthy. A tax figure recomputed on page load is not a thing that happened; a tax report
generated on 31 December is. Making every conclusion an event turns the historian into a
general-purpose database wearing an event log's name.

**The resolved shape is a versioned calculation record**, associated with an event only when
one actually occurred:

```text
CalculationRun          CalculationResult
  calculation_type        calculation_run_id
  calculation_version     metric
  rule_set_version        value
  input_set               unit
  calculated_at
  result
```

And the requirement underneath it, which is stronger than either draft:

> **A historical conclusion must never depend on an unversioned interpretation of the present.**

**One open fork.** `input_set_hash` *detects* that inputs changed; it does not let you
reproduce the old answer, because a hash cannot be reconstructed into state. Either the run
**stores its inputs** (fat, self-contained, works on day one, blocks on nothing) or it
**reconstructs from history** (thin, and only possible once facts are append-only and
versioned — which means the run cannot be built before the fact model). Recommended: the fat
version first. A tax run carrying its own inputs is reproducible immediately and does not wait
on the substrate question.

### C2. `classification_confidence` should not exist

A stored confidence number is a fabricated heuristic waiting to be thresholded. Confidence *of
what*, calibrated against *what*? The moment it exists, something writes `if confidence > 0.8`
and an invented number drives a protection decision invisibly — the null-model problem that has
already cost this project twice, and rule 22's *never bake risk into a rate* in different
clothes.

**Use `classification_source` as a typed enum** — `user_stated`, `imported_eob`,
`merchant_match`, `mcc`, `inferred`. Same information, honestly held, and it makes policy
checkable: *never protect on `inferred` alone* is testable; *never protect below 0.8* is not.

*Sharpened during review, twice.* **Source alone does not solve uncertainty.** `merchant_match`
on CVS says nothing about whether this transaction was a prescription, a birthday card or
crisps. So the evidence has to resolve to a per-transaction state rather than a per-merchant
label — but that state must be named in **evidence terms, not policy terms**. A state called
`SUPPORTED_HEALTH_CLASSIFICATION` has already smuggled in a policy judgement (supported enough
for *what?*), which is the separation this section is trying to enforce. `user_asserted`,
`corroborated`, `single_weak_signal` describe what is known; policy maps them to outcomes.

**And one classification cannot serve both protection and tax, because their error asymmetries
are opposite.** Protection wants to over-include: a false positive costs one unavailable lever,
a trade `is_protected`'s docstring already accepts. Tax must under-include: a false positive
costs a wrong return, the one place in this module where being wrong has a legal consequence
for the user. The CVS transaction should be *ambiguous → not a lever* **and** *not in the
Schedule A total* — the same decision only by coincidence. Two policies over one classification,
never one threshold serving both.

### C3. `green_light()` is in the wrong severity band — ACCEPTED

It is marked P1. Every other item on that table is a defect in code that does not exist yet.
This one is a behavioural change to **shipped software with real users on an LTS line** — it
can alter what existing users are told about money they already have, and they never opted into
healthcare. **P0 on blast radius**, ahead of several unbuilt-code items.

*Accepted, with a sharper reason than blast radius.* The other items are **new functionality
that is currently wrong**, which is a development problem. This is **existing functionality
whose meaning changes underneath existing users**, which is a product-integrity problem. It
therefore needs a **contract test**, not a unit test:

```text
existing user + no healthcare information + same historical financial state
        → the same green_light result
```

unless an intentional change is documented and versioned. That is a product invariant rather
than a function's return value.

**Built 2026-09-07** — `tests/green_light_contract.py` plus `smoke_sections/s70_green_light_contract.py`.
The distinction above is what shaped it: a hand-picked expected value written today is chosen
to match today's implementation, so it can notice that the arithmetic moved but not that the
*meaning* did. A recorded corpus fails on any difference, for any reason, which is the only
shape that catches a change nobody anticipated — and a healthcare reserve reaching
`green_light()` is precisely an unanticipated change until it is designed.

The section also proves it can fail, because a frozen baseline that quietly stops comparing
reports a safety it is not providing: it shifts the freed figure by one cent, turns an honest
silence into a light, and requires the comparison to catch both.

---

## Added during review — two things both passes missed

### A1. The event log already exists, and is already load-bearing

`HistorianEntry` is not a sidecar. It is read in fourteen places, and in several of them it
**is** the truth: `_proactive_state` reads `proactive_shown` / `proactive_dismissed` rows as the
authoritative frequency ledger, Pillar 5 reads estimate variance from it, the engagement streak
reads `session_start`.

So the question is not *design a fact/event model*. It is **is the one already carrying weight
the right substrate, or must it be replaced?** That is a decision with a migration attached and
it is documented separately in `EVENT_SUBSTRATE_QUESTION.md`.

### A1b. C1 confirmed in shipped behaviour — and mitigated

> **`is_protected()` is an unversioned interpretation fused directly to policy, making
> historical policy conclusions unreproducible. Immediate mitigation: version-identify the
> existing rule without restructuring it.**

Running the layer inventory against real code found the pattern's fourth instance, six lines
long. `is_protected(category_name)` takes **evidence** (a category name — and nothing else: no
merchant, no MCC, no amount, no user statement), performs a **classification** that is never
named, returned or stored, and emits a **policy verdict** as its return value. Three layers, one
expression, with the middle one existing only inside an `any()`.

Nothing is persisted, so nothing was corrupted. What was lost is reproducibility: when health
terms were added on 2026-09-06, `is_protected('Prescriptions')` went from `False` to `True`, and
every prior judgement about such a category — trim proposals, headroom figures, budget-pressure
lessons — became impossible to reconstruct. **The three checks written that same morning all
passed, because they assert the vocabulary rather than the provenance.**

**Mitigated, deliberately small.** `NECESSITY_FLOOR_VERSION` now exists (at `'2'`; version `'1'`
was the pre-health list), and every verdict that reaches user-visible reasoning carries it — the
overspend entry that reports `protected`, and both solvers, since the floor decides which levers
may be offered and **an absent lever is a verdict too.**

`is_protected` is structurally unchanged. The patch says *this answer came from floor rule
version 2*; it does not claim Groundwork has recorded the reasoning that produced it. That
distinction is the whole point, and inflating six working lines into a classification
architecture would recreate the fusion elsewhere.

**And the test that would have caught it now exists**, as a separate invariant:

| Invariant | Asks |
|---|---|
| Rule **content** | does the vocabulary contain the expected terms? |
| Rule **provenance** | does every user-visible verdict identify the rule that produced it? |

Content passed throughout the failure. Both are now checked, and both are mutation-proven.

### A2. Healthcare would sit on provenance-free primitives

A healthcare expense with full provenance derives from a `Transaction` that has none.
`Transaction`, `DebtAccount`, `BudgetItem` and the sinking funds are all mutable-state entities
with real user data behind them.

**§9's reconstruction test therefore fails at the boundary regardless of how well the
healthcare side is built** — the chain is walkable until it reaches the ledger, and then it
stops. Either the primitives gain provenance too, or the reconstruction guarantee has to be
stated as ending at the ledger, honestly and in the product.

---

## Severity

| Area | Risk | Why |
|---|---|---|
| Healthcare classification | **P0** | Wrong classification exposes protected spending |
| Provenance / taint | **P0** | Derived sensitive information escapes protection |
| Reimbursement | **P0** | Late corrections and multiple funders break simple state |
| Person identity | **P0** | Historical reassignment corrupts calculations |
| Plan-year history | **P0** | Mutable current state rewrites history |
| Merge | **P0** | Canonical identity and provenance |
| Reversal / chargeback | **P0** | Unwinds already-accounted events |
| Tax calculations | **P0** | Must survive late information and corrections |
| `green_light()` | **P0** *(raised, C3)* | Only item that regresses shipped software |
| Collections | P1/P0 | Temporal ownership and validation underspecified |
| Provider plans | P1 | Terms and history need versioning |
| Reserve | P1 | Target confused with actual money |
| Legal tables | P1 | Stale rules silently produce wrong conclusions |
| Export / backup | P1 | Derived sensitivity escapes secondary surfaces |

---

## Next step — now written

Not another broad critique, and not the lifecycle table first. **`tests/test_lifecycle_fixture.py`
exists and fails**, written before any model, so the model has to come to the test rather than
the test being shaped to flatter a model. Ten mutations against one expense with three funders.

Three assertions in it were not in either review pass and came out of writing it:

- **Arrival order.** An EOB imported in March describes January, and a correction was recorded
  in February. If events apply in arrival order rather than effective order, the answer depends
  on import sequence — and imports are retroactive by nature, so this is routine rather than an
  edge case. The assertion is *same facts, any arrival order, same answer*, and it falsifies
  more designs than the other nine mutations together.
- **Unallocated is not user-paid.** After M3 there is $650 nobody has paid. It is not the
  taxpayer's money and must not be rolled into the qualifying total merely because it was not
  reimbursed. A model that confuses the two overstates a deduction on a filed return — and the
  confusion is easy, because both are "not reimbursed".
- **Deletion is at least three operations.** Correction ("this never happened"), void ("this
  stops applying"), destruction ("erase the record") cannot be one button.

The lifecycle table falls out of this as a by-product: every cell that would have been filled
in by imagination becomes an assertion that either passes or does not.
