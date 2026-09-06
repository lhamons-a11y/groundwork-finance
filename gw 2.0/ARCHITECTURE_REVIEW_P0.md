# Critical architecture review — P0 addendum

**A review artifact for the healthcare module**

> Status: **Review artifact. Does not modify the underlying design blueprint.**
> Written 2026-09-06 by Rob, reviewing `HEALTHCARE_MODULE_DESIGN.md` and
> `LEGAL_BOUNDARIES.md` as a production architecture review with authority to block.
>
> Kept separate from the design on purpose. The design says what the product should do; this
> says where the specification is not yet strong enough to make that mechanically true. Merging
> them would lose the distinction between a decision and a challenge to it.
>
> **The review's own conclusion:** the philosophy is considerably more mature than the
> implementation specification. The documents are good at *never do X* and less complete on
> *what exact data, state, provenance, transition, test and failure behaviour makes "never X"
> mechanically true.* Four gap classes recur throughout: **classification**, **temporal**,
> **provenance**, and **state-transition**.

---

## 1. P0-1 — Protected healthcare classification

### Finding

The current protection mechanism is insufficient if `is_protected()` operates by substring
matching against a category name. This tests vocabulary rather than the invariant.

Examples that can pass existing vocabulary-based tests while remaining incorrectly exposed to
solution logic:

* A CVS transaction categorised as `Other`
* A medical device purchased through Amazon
* A prescription transaction with an unrecognised merchant
* A healthcare expense whose category was manually changed
* A healthcare expense imported without a healthcare-specific category

The resulting failure is architectural: **a healthcare expense can enter the solution engine
simply because its category does not contain a recognised healthcare word.**

### Existing test weakness

Mutation-proven tests can remain green while the actual safety property is violated. Tests that
assert:

```text
pharmacy → protected
dental   → protected
medical  → protected
```

do not establish:

```text
healthcare expense → never eligible as a financial lever
```

> **Live instance.** The floor fix shipped 2026-09-06 (`core/solution.py`, commit `1864d86`) is
> exactly this shape: it protects the named vocabulary and its three checks assert the
> vocabulary. It is a strict improvement over the prior state — the named categories were
> wholly unprotected — and it is **necessary, not sufficient**. It should stay; it does not
> close P0-1.

### Required direction

Protection must be based on a health-domain signal, not category-name substring matching.
Potential signals:

* merchant / provider identification
* MCC or equivalent transaction metadata
* provider matching
* prior user classification
* imported healthcare / EOB data
* explicit healthcare designation
* other deterministic classification signals

### Important boundary

Fail-closed behaviour must **not** mean `unknown → protected` across the entire transaction
universe. That would make ordinary unknown transactions unavailable as levers and could
effectively disable §6.1 for users with no healthcare data at all.

Instead, **fail-closed applies within the health-adjacent zone**:

```text
No health signal
    → ordinary classification
    → existing lever eligibility

Health signal present, classification resolved
    → healthcare
    → protect

Health signal present, classification unresolved
    → do not expose as lever
```

### Additional requirement

The prevalence of unresolved health-adjacent transactions must be **measured against real
transaction data before release**. This is not a UX decision: it directly affects how often
§6.4's honest-no path fires, and therefore changes solution-engine behaviour.

---

## 2. P0-3 — Provenance / sensitivity propagation

### Finding

Derived information can remain health information even when the original transaction is no
longer visible.

```text
Medication transaction
        ↓
Healthcare classification
        ↓
Monthly spending calculation
        ↓
"Spending increased 20%"
```

The final statement contains no medical word and is still derived from health information.
A check such as `if health_context: refuse` is insufficient, because health context can
disappear during transformation.

### Required architectural property

Health sensitivity must attach to provenance and propagate through derived objects.

```text
Raw transaction
    ↓
Health classification
    ↓
Health-sensitive derived fact
    ↓
Allowed internal calculations
    ↓
Policy gate
    ↓
Narrator-safe fact set
```

The narrator must not receive unrestricted access to underlying records merely because the
requested sentence appears financially oriented.

### Privacy implication, and the tension with P0-1

**Classification itself can create sensitive information.** A classification of
`Amazon → medical device` creates health information that did not exist explicitly in the bank
record. Therefore improving classification to satisfy P0-1 manufactures additional derived
health data that P0-3 must then protect. The classifier is not a categorisation convenience;
**it is a privacy-sensitive subsystem.**

### Required decision

Derived healthcare classifications must carry the same sensitivity protections as
user-supplied healthcare information. **Proposed position: yes** — protection should not depend
on whether the user typed the designation.

---

## 3. Priority contradiction

### Finding

These conflict:

> *Groundwork does not choose the user's financial priorities.*

> *The card is cleared. Nothing outranks this.*

The second is a priority assertion.

### Resolution

Do not encode the ordering as a universal financial priority. Present costed alternatives:

```text
Path A — clear the card faster; the healthcare reserve grows more slowly
Path B — build the reserve faster; card payoff takes longer
```

### Revised principle

**Groundwork chooses which consequences to show and which categories are protected from being
treated as levers; the user chooses among permitted paths.**

---

## 4. Rule 10 — credit card as healthcare funding

The rule as written reads more broadly than intended, while §1.1 already permits pricing
multiple funding sources. The correct distinction:

```text
Credit-card cost           → calculable
Credit-card recommendation → prohibited
```

Groundwork may show the consequence of using the card when asked. It may not present the card
as a recommendation or a neutral alternative.

## 5. "One number" in the tax report

Clarification: *one number* meant **one tax line Groundwork holds the inputs for**, not one
displayed value. The report already contemplates gross expenses, exclusions, reasons,
threshold, and whether the amount clears it.

**Accepted improvement:** formalise uncertainty as structured data rather than prose.

## 6. Rule 14 — internal terminology

Partial acceptance. The prohibition is primarily user-facing, but internal names leak through
logs, error messages, debug output, serialised objects, API responses, LLM context and
developer tooling.

Therefore: local implementation variables may use technical terminology where necessary, but
**persistent schema names, routes, API surfaces, logs and user-visible diagnostics must not**
encode "medical debt".

## 7. Rule 8 — user-initiated counterfactuals

```text
App-generated counterfactual   → prohibited for healthcare reduction
User-initiated counterfactual  → allowed
```

"What if I don't do this?" is the user selecting the counterfactual. Groundwork may calculate
the consequence without recommending the decision. This follows the existing principle — the
user chooses the number, Groundwork calculates the consequence — so **the boundary is who
initiated it**, not whether the subject is healthcare.

---

## 8. Reimbursement — allocation model

A single enum cannot represent:

```text
$1,000 healthcare expense
  $300 insurance reimbursement
  $400 HSA reimbursement
  $300 user-paid
```

Model funding and reimbursement as transactions/allocations against the expense, supporting
multiple sources, partial reimbursement, reimbursement after the fact, corrections, reversals
and unresolved allocations. Particularly important for tax.

## 9. Lifecycle gap — merge

Two bank transactions later found to be one expense; or an EOB record and a bank payment found
to be one healthcare event. The system must distinguish *two legitimate expenses* from *two
records of one expense*.

Open questions on merge: which record is canonical; are both originals preserved; does
provenance survive; are allocations moved; are historian events generated; is it reversible;
does the audit trail remain intact; does tax history recalculate.

**Requirement:** a merge must be reversible, provenance-preserving and auditable.

## 10. Lifecycle gap — reversal / chargeback

A reversal is not a refund. A refund returns money after an expense; a reversal unwinds the
original payment — which matters when that payment is already associated with an HSA
distribution, an FSA reimbursement, an insurance reimbursement, or a tax calculation.

```text
Healthcare expense: $1,000
HSA distribution:   $1,000
        ↓
Payment reversed
```

Posting `-$1,000` does not resolve this. **Requirement:** model reversal as a distinct
lifecycle event that unwinds prior allocations without destroying provenance.

## 11. Tax reconciliation

A January expense cannot remain permanently classified by its January state when an $800
reimbursement arrives in March.

```text
Gross expense − reimbursements − excluded amounts = qualifying amount
```

Each component must trace to source records. **A tax figure must be reproducible from the
complete event history.**

## 12. Deferred-interest obligations

A payoff date cannot be generated without modelling promotional terms: original principal,
current balance, promotional period and expiry, standard APR, accrual behaviour, whether
interest is retroactive, and fees. **The engine must classify the interest model before
presenting any payoff projection.** A "0%" label alone is insufficient.

## 13. HSA / FSA rules

Statutory limits must not live permanently in application logic — the same legal-data rot
identified elsewhere. Tax-year rules carry `year`, `value`, `source`, `effective_date` and a
verification/review status; the engine consumes the rule rather than hardcoding the number.

## 14. Healthcare reserve

The OOP maximum is a useful **coverage-based** target and not a universal maximum healthcare
cash requirement. It does not account for premiums, excluded services, out-of-network exposure,
uncovered care, or costs outside the accumulator.

The product must not imply that funding it guarantees healthcare will never require credit.
**Revised terminology: coverage-based healthcare reserve target.**

## 15. Plan-year state

Coverage accumulators must be evaluated against the applicable plan year and historical plan
state. The Care Planner cannot treat remaining OOP as a timeless value.

## 16. Healthcare expense taxonomy

The proposed categories combine expense type, cost-sharing mechanism, coverage domain and
service type into one hierarchy, which cannot answer all the questions asked of it. Separate
the dimensions: healthcare domain, service type, coverage type, funding source, reimbursement
allocation, person, provider, plan, plan year.

## 17. Collections ownership

```text
original creditor → debt buyer → collection agency → subsequent collector
```

A single `agency_name` cannot model this. Maintain an auditable ownership/servicing history.

## 18. Collections validation state

`requested` / `received` is insufficient. The lifecycle may need not-requested, requested,
received, partial, disputed, validated, invalidated, resolved. The invariant that matters:
**receipt of validation material is not resolution of a dispute.**

## 19. First-delinquency provenance

The date must carry its source — user entry, imported document, credit report, creditor
correspondence — and must never be presented as independently verified when it is not.

## 20. Provider plan vs credit instrument

`provider = healthcare cost` / `lender = credit card` depends on who carries the obligation
rather than what the instrument is. Classify by instrument — ordinary healthcare expense,
provider installment plan, revolving credit, installment credit, deferred-interest credit —
while retaining `underlying_domain = healthcare`. **These dimensions must not be collapsed.**

## 21. Legal information freshness

External legal and policy facts carry jurisdiction, source, effective date, retrieval date and
review status, with an explicit stale/expired state. **Groundwork must never silently treat
stale legal information as current authoritative fact.**

## 22. Export sensitivity

"Health rows are excluded from exports" is not an architectural rule. Sensitivity must
propagate to every surface — PDF, CSV, backups, clipboard, browser download, integrations,
future sharing. **Export behaviour is determined by the sensitivity of the underlying and
derived data, not by the screen it was initiated from.**

## 23. Backup sensitivity

Backups inherit the sensitivity of the primary database. Unspecified and required before
healthcare data is considered complete: encryption at rest, key management, retention,
deletion, restore behaviour, stale backups, user-managed cloud folders, duplicate copies.

## 24. `green_light()` / LTS regression risk

Changing `green_light()` to account for a healthcare reserve can alter behaviour for users with
no healthcare data — material because 1.x is an LTS line. Required regression matrix: no
healthcare data; healthcare data with no reserve; partially funded; fully funded; changing OOP
target; plan-year rollover; expense added; expense removed; expense reclassified.

**Existing behaviour for unaffected users must remain stable unless an intentional versioned
change is documented.**

---

## 25. The master principle

> **Policy must operate on typed, provenance-aware facts rather than strings, labels, or
> presentation context.**

The system should distinguish raw fact, derived fact, user assertion, external fact, inferred
classification, health-sensitive fact, legal-sensitive fact, financial calculation,
recommendation and counterfactual — **without relying on the narrator, or a developer, to
remember which rules apply.**

```text
                 ┌───────────────┐
                 │  Raw Record   │
                 └───────┬───────┘
                         ↓
                 ┌───────────────┐
                 │Classification │
                 └───────┬───────┘
                         ↓
             ┌───────────┴───────────┐
             ↓                       ↓
        Provenance              Sensitivity
             ↓                       ↓
        Calculation ──────────→ Policy Gates
             ↓                       ↓
       Derived Fact             Allowed Fact
             └───────────┬───────────┘
                         ↓
                     Narrator
                         ↓
                      Output
```

Once that exists, the rules become enforceable invariants rather than a list developers and
models are expected to remember.

---

## 26. Implementation gate

### P0 — resolve before implementation

Health-domain classification model · health-adjacent fail-closed behaviour ·
sensitivity/provenance propagation · person identity model · reimbursement allocation model ·
merge lifecycle · reversal/chargeback lifecycle · healthcare obligation/instrument model ·
plan-year model · deferred-interest fields and calculations · tax calculation decomposition ·
legal fact provenance/freshness · export/backup sensitivity propagation · collections ownership
history · collections validation state · LTS regression behaviour of `green_light()`

### P1 — resolve before release

Medication identity normalisation · external price-query consent scope · FSA carryover and
grace-period representation · provider-plan versioning · healthcare reserve terminology ·
user-initiated healthcare counterfactual behaviour · internal terminology leakage rules

---

## Review status

**Accepted as architectural defects or necessary clarifications:** vocabulary-based healthcare
protection is insufficient · health-derived information requires sensitivity propagation · card
payoff ordering conflicts with the non-prescriptive philosophy · reimbursement requires
allocations · tax calculations require traceability · deferred-interest requires explicit
modelling · HSA/FSA limits require externalised rules · the OOP maximum is a coverage-based
target and not a guarantee · collections require ownership history · collections validation
requires more than a binary state · first-delinquency information requires provenance ·
provider/lender identity is insufficient to classify instruments · legal facts require
freshness and provenance · healthcare changes to `green_light()` require LTS regression testing
· merge and reversal/chargeback belong in the lifecycle analysis

**Contested / clarified:** Rule 10 — pricing credit-card healthcare financing is allowed,
recommending it is not · "one number" means one tax-line calculation, not one displayed value ·
Rule 14 — "medical debt" may exist in transient technical reasoning if unavoidable, but not in
persistent schema, API, logging or LLM terminology · Rule 8 — explicitly user-initiated
healthcare counterfactuals are permitted, app-generated healthcare-reduction counterfactuals
are not

**Unresolved.** The largest open issue is the interaction between healthcare classification,
privacy sensitivity, derived inference, and solution-engine protection. **This should be
settled before implementing either the classifier or the privacy gate**, because each one
changes what the other must do.

---

## Next step

**Do not modify the blueprint yet.** Continue the lifecycle attack against the proposed data
model and functions:

```text
create · import · classify · edit · reclassify · merge · split · refund ·
reimbursement · reversal · chargeback · duplicate detection · plan change ·
plan-year rollover · tax recalculation · export · backup · deletion · restore
```

The objective is to determine whether the proposed architecture preserves its stated invariants
through **every transition**, rather than merely satisfying them at the moment a record is
first created.
