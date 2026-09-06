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

### C1. "Never store derived conclusions" is incomplete

The remedy of recomputing rather than storing fixes staleness and introduces
**non-reproducibility when the rules change rather than the data.** Run the 2026 tax report in
2028: same transactions, nothing edited, different answer — because the §213 threshold moved,
or an HSA limit did, or bureau policy changed. Pure recompute silently rewrites history on
every rule update, which is the same defect arriving from the other direction.

**A conclusion is therefore itself an event, carrying the rule-version and input-set that
produced it.** Not `qualifying_amount = 4238` as a cached field, but *"on this date, under
rule-set v2026.1, over these 47 records, the qualifying amount was $3,687."* That is the only
form that survives dated rule tables meeting late reimbursements.

### C2. `classification_confidence` should not exist

A stored confidence number is a fabricated heuristic waiting to be thresholded. Confidence *of
what*, calibrated against *what*? The moment it exists, something writes `if confidence > 0.8`
and an invented number drives a protection decision invisibly — the null-model problem that has
already cost this project twice, and rule 22's *never bake risk into a rate* in different
clothes.

**Use `classification_source` as a typed enum** — `user_stated`, `imported_eob`,
`merchant_match`, `mcc`, `inferred`. Same information, honestly held, and it makes policy
checkable: *never protect on `inferred` alone* is testable; *never protect below 0.8* is not.

### C3. `green_light()` is in the wrong severity band

It is marked P1. Every other item on that table is a defect in code that does not exist yet.
This one is a behavioural change to **shipped software with real users on an LTS line** — it
can alter what existing users are told about money they already have, and they never opted into
healthcare. **P0 on blast radius**, ahead of several unbuilt-code items.

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

## Next step

Not another broad critique. Take the proposed schema and functions one at a time and **try to
make each produce a contradictory state.** That is where the bugs live that a happy-path
architecture review will never surface.
