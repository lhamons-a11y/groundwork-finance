# Hazard audit — concrete implementation against frozen semantics

> Status: **Audit, opened 2026-09-12. Mode: HAZARD AUDIT — no new case doctrine, no map
> extension, no code changes until the audit identifies the smallest safe repair boundary.**
> Evidence mode closed at `e7103d1` with seven fences lifted. Several places are now known
> where shipped behaviour contradicts semantics that are *frozen*, not proposed. This document
> audits each against the concrete code and its consumers.
>
> **Rob's audit rule, applied per hazard:**
>
> ```text
> frozen rule → actual implementation → actual consumers → specific contradiction
>             → blast radius → minimum safe repair boundary → implementation decision
> ```
>
> **Discipline:** audit first, repair second. **Never repair a mechanism merely because one
> consumer is wrong until its other consumers have been classified.** The evidence work proved
> `resolution()` correct for one half of its domain; that is the pattern to expect elsewhere.
>
> **Order, Rob's — semantically-wrong first, missing-representation last:**
>
> 1. `plan_at()` / overlap
> 2. `record_payment()` / `remaining`
> 3. dated resolvers — `knowing[-1]`, `attested[-1]`
> 4. `resolution()`
> 5. the narrator authorisation boundary
>
> Representation design is **not** this mode. *What must the system mean* is largely settled;
> *how to encode it* is the mode after this one, once it is known which code paths must survive.

---

## H1 — `plan_at()` / overlap

### Frozen rule

From `PERIOD_CLOSE_OVERLAP_TEST.md` §5 and `CONCURRENT_COVERAGE_CASES.md` ruling:

- **B (competing claims, governance unknown):** the overlapped range attributes to *neither*;
  `deductible_met = UNKNOWN`; both claimants named; **never resolved by position.**
- **C (both govern):** attribution is **determinate and multi-valued** — each plan's share, each
  plan the knowing party for its own. Not unresolved. Priority may be unresolved *within* C.
- **CC4:** period overlap does not determine applicability; **applicability is evaluated per
  expense, first.** Where it excludes a plan the state is A.
- **CC5 / A:** sequential periods are one plan per date.
- The year-level `UNKNOWN` conflates B, C and sequential periods — a consumer hazard.
- **Not decided:** `plan_at()`'s return shape — a consumer/build decision.

### Actual implementation — `core/plan_year.py`

```python
def plan_at(when, as_of=None):                      # L191
    for p in plans(as_of):
        if (p.effective_from or '') <= (when or '') <= (p.effective_to or '9999-12-31'):
            return p                                # first match, insertion order
    return None

def plan_of(expense_key, expenses, as_of=None):     # L204 — thin wrapper: plan_at(row['date'])

def accumulators(expenses, plan, as_of=None):       # L234
    applied = sum(e['amount'] for e in expenses if _in_period(plan, e['date']))
    # the FULL amount of every expense whose date falls in the plan's period

def year_summary(expenses, year, as_of=None):       # L258
    periods = [accumulators(rows, p) for p in plans(as_of) if any expense in p's period]
    unattributed = sum(e['amount'] for e in rows if plan_at(e['date'], as_of) is None)
    met = periods[0]['deductible_met'] if len(periods) == 1 and unattributed == 0 else UNKNOWN
```

Three facts about the implementation that the rulings did not have in view:

1. **`accumulators` is multi-valued already, and wrongly so.** It sums the *full* amount of
   every expense in the plan's period, per plan, independently. Under C it therefore attributes
   the whole $600 to A **and** the whole $600 to B — a double count — where the truth is $400
   to A and $150 to B. Under B it does the same. `plan_at` invents a winner; `accumulators`
   invents *two* whole winners. The C ruling's *each plan's share* is not representable:
   an expense carries `amount` and `date` only, and the share is evidence (each plan's EOB)
   the module does not hold.
2. **`year_summary`'s `unattributed` is the only internal caller of `plan_at`**, and it uses it
   for exactly one thing: *is there **no** plan for this date?* — a question `[0]` answers
   correctly, because `None` is position-independent. The overlap resolution inside `plan_at`
   is never consulted by `year_summary`.
3. **The module answers a period question and is read as an applicability question.** An
   expense is `{amount, date}`; nothing in `plan_year` can know that a dental expense is
   outside a medical plan's rule. CC4's hazard is therefore **not in this module** — it is in
   any caller that asks `plan_of` before consulting the applicability axis (which lives with
   `core/allocation.py` / `core/classification.py`). The contract *"the plan in force on a
   date"* is accurate; the hazard is a caller treating *in force* as *governs this expense*.

### Actual consumers

| consumer | what it reads | classification |
|---|---|---|
| `core/plan_year.plan_of` | `plan_at` | internal wrapper; inherits `[0]` |
| `core/plan_year.year_summary` L281 | `plan_at(...) is None` | **safe** — asks only *no plan?*, position-independent |
| `core/allocation.state(e, plan=UNRESOLVED)` | takes `plan` from the caller — *"reports the plan it was told"* | **future consumer**; single `plan` parameter presumes A; not wired |
| `core/database.py` L627 | — | *"NOTHING READS THESE TABLES YET… plan_year… pure and have no callers"* |
| `server.py`, `static/js/app.js` | — | **no reference** |
| `tests/test_plan_year_fixture.py` L89, L112 | `plan_at(...) is a`, `plan_of('x1') is a` | pins **single-object identity** on the happy path (A only) |
| `smoke_sections/s85_plan_year.py` | mutates `year_summary`, `accumulators` | **does not mutate `plan_at`** |
| `tests/substrate_experiment.py` `PlanYearStore._READS` | `plan_at`, `plan_of` in the read set | test double mirroring the API |

**Shipped consumers on the default path: none.** The module is pure and uncalled in production.

### Specific contradiction

| state | frozen | `plan_at` | `accumulators` |
|---|---|---|---|
| A | one plan | correct | correct |
| B | neither; UNKNOWN; never by position | **first inserted wins** | **both plans count the full amount** |
| C | both, each its share | **first inserted only** | **both plans count the full amount** (share unrepresentable) |
| CC4 | applicability first | not this module's to know — **caller** hazard | same |
| CC5 | one plan per date | correct | correct |
| year-level | three truths | — | one `UNKNOWN` for all three |

And one thing the audit adds: **the `[0]` behaviour is unpinned in both directions.** No test
asserts it (the fixture's `is a` cases have one plan per date) and no mutation catches a
change to it (s85 mutates `year_summary` and `accumulators` only). It is a live semantic
hazard that the suite is silent about.

### Blast radius

- **Today, shipped:** zero. No production caller. The hazard is *reachable* only through the
  module's own API and the year-level `UNKNOWN`'s uninformativeness.
- **On first wiring:** every consumer that calls `plan_of` for an expense inherits B's invented
  winner and C's dropped plan; every consumer that calls `accumulators` under B or C inherits a
  double count. The named first consumer, `allocation.state`, takes one `plan` and so can only
  receive A's answer — **it cannot be wired under B or C without the return shape being
  decided.**
- **Downstream doctrine:** period close (ruled: represent-and-report, three provenances)
  requires the record to *hold* the overlap state during REPORT — which is precisely the
  state `plan_at` currently resolves away. **Period-close work is blocked behind this hazard**,
  as Rob said.
- **Tests:** two identity assertions in the fixture and `PlanYearStore._READS` in the
  substrate experiment change if the return shape changes. s85 is unaffected until a
  mutation for `plan_at` is added.

### Minimum safe repair boundary

The boundary is the module's API plus its fixture, and it is smaller than "fix overlap":

1. **`plan_at` must stop resolving B and C by position.** That is the frozen rule and it is
   independent of the return shape: the *minimum* change is that `plan_at` **refuses** when more
   than one plan's period contains the date — fail-closed, single-valued contract preserved
   for A and CC5, and no shape decided. Anything richer (a tuple, a set, an ambiguity object)
   is the fenced consumer decision and is **not** in the minimum boundary.
2. **`year_summary` needs no change for its own use of `plan_at`** — `is None` survives a
   refusal only if the refusal is not `None`; that is the one coupling to check in the repair.
3. **`accumulators` is out of the minimum boundary.** Its double count under B/C is real and
   cannot be repaired without the per-plan share, which is evidence the module cannot hold —
   a representation question, next mode. It should be **guarded, not fixed**: the same
   refusal condition (more than one plan contains an expense's date) marks the result as
   not computable, rather than returning a double-counted `applied`.
4. **The contract must say *period*, not *governs*.** `plan_at`'s docstring — *"the plan in
   force on a date"* — is right; the caller-side hazard (CC4) is prevented by documenting that
   applicability is the caller's question and is asked first. A documentation change, in the
   boundary because it is the only place CC4 can be prevented from inside this module.
5. **Add the missing guard:** a mutation in s85 that restores first-match under overlap must
   be caught. Today it would not be.
6. **Out of the boundary:** the year-level `UNKNOWN` split (three states — a consumer
   decision on what the summary returns), the per-plan share, `plan_at`'s eventual shape,
   `allocation.state`'s signature, period close itself.

### Implementation decision — Rob's

Whether the minimum boundary above is the repair: **refuse on overlap in `plan_at`, guard
`accumulators` on the same condition, document the period/applicability contract, add the
mutation** — or whether the return shape should be decided now so that `plan_at` can *report*
B and C instead of refusing them. The first keeps the shape fenced and unblocks nothing
downstream except correctness; the second unblocks period close and `allocation.state` at
the cost of making the consumer decision now, in build mode rather than this one.

**No code is changed by this section.**

### H1 ruling — Rob, 2026-09-12. Minimum repair boundary accepted. Return shape NOT decided.

> *Do not decide the return shape in Hazard Audit. That is exactly the kind of decision this
> mode is supposed to prevent us from smuggling in under the label of "repair."*

1. **`plan_at()` — refuse on genuine period overlap.** Single-valued contract kept: one
   applicable period → that plan; none → `None`; more than one contains the date →
   **refuse / fail closed.** Refusal is not a new semantic answer; it is the API saying the
   existing single-plan representation cannot faithfully represent what the evidence
   establishes. Preserves A and CC5; prevents B/C being silently collapsed.
2. **`accumulators` — guard, don't repair the accounting.** The full expense against both
   plans is demonstrably wrong under C, and `$400/$150` is not something this module is
   entitled to invent. *If an expense falls within multiple governing periods, `accumulators`
   must not produce a normal per-plan applied amount.* Guard; manufacture no share. The
   allocation question stays separate from the period question.
3. **`year_summary` — don't touch it because `plan_at()` changes.** Its use asks *is there any
   plan?*, not *which governs?*; `[0]` does not contaminate it. Verify the refusal
   sentinel/exception does not break that contract; do not redesign.
4. **CC4 — contract, not logic.** `plan_at()` answers period membership; it cannot evaluate
   medical-vs-dental applicability. *The caller must establish applicability before treating
   a plan as governing an expense.* Made explicit, or a correct primitive becomes a semantic
   trap.
5. **Add the s85 mutation.** Protects frozen behaviour against regression; expands no doctrine.

**Explicitly not decided now:** `plan_at()` return shape · B's representation · C's
representation · per-plan allocation/share · `allocation.state()` signature · year-level
`UNKNOWN` decomposition · period-close representation. Consumer/build-selection decisions.
**The argument "period close is blocked, so decide the shape now" is rejected** — that is how
a blocked consumer starts dictating an API before the other consumers are audited.

**Audit observation kept:** zero shipped blast radius means this is not an emergency repair;
the boundary can be made correct before the first consumer is wired.

> **H1 minimum repair accepted: fail closed on multi-period `plan_at()`; guard `accumulators`
> on the same condition; clarify the period-vs-applicability contract; add the overlap
> mutation. Do not decide representation or consumer shape in Hazard Audit.**

**H1 is not implemented yet.** H2–H5 are audited first, because a later hazard may expose a
shared mechanism whose repair boundary should be coordinated.

---

## H2 — `record_payment()` / `remaining`

### Frozen rule

From `SERVICING_ONLY_CASES.md` and `ACKNOWLEDGMENT_EVIDENCE_CASES.md`, both ruled:

> Discharge is an acknowledgment fact, not a payee fact. A payment may evidence discharge; it
> does not establish discharge without acknowledgment by the entitled party. Until
> acknowledgment exists, the payment is **attached but unacknowledged** and must not be treated
> as confirmed discharge.

The ruled sequence, with the one step that is fenced:

```text
payment attached → attached/unacknowledged → E acknowledges → discharge established
→ confirmed remaining changes                      ← what strength `remaining` requires: FENCED
```

And two adjacent rulings that bear on it: a projection over attached payments is **not
evidence** and its discrepancy from P-ack is **diagnostic** (U6/F2); a cleared bank payment is
**no evidence of acknowledgment** (K6).

### Actual implementation — `core/payment_plan.py`

```python
Entry(kind, amount, on, reason, reverses, recorded_at)         # L54  — no acknowledgment field
record_payment(plan, amount, on)  → appends Entry('payment')   # L82
ledger(plan, as_of)  → payment + reversal entries, filtered by `on` (effective)   # L121
payment_state(plan, as_of):                                    # L158
    paid      = Σ ledger                    # attached payments net of NAMED reversals
    remaining = gross + adjustments − paid  # moves the moment a payment is attached
    expected_by_now, ahead, overdue         # agreement-relative, computed FROM paid
incoherences(plan, state)  → checks the projection against ITS OWN ledger              # L186
```

What the implementation gets right, and should keep: **dual dating** (`on` = effective,
`recorded_at` = provenance; the projection filters by `on`, never by position — H3's hazard is
*not* here); **named reversals** (a reversal is a household-side fact that money came back —
K6's inverse, and correctly not an acknowledgment); **adjustments kept apart from payments**;
one projection, no partial accessors.

What it has no concept of: **acknowledgment.** There is no input by which E's statement can
reach the module, no state for *attached, unacknowledged*, and therefore no distinction between
*paid* as *what the household attached* and *paid* as *what E credited.* `remaining` is the
first, presented as the second.

### Actual consumers

| consumer | what it reads | classification |
|---|---|---|
| production (`server.py`, `app.js`, `core/*`) | — | **none.** By rule: gap 8's fence — *do not add a consumer to `core/payment_plan.py`* — still stands |
| `tests/test_payment_state_fixture.py` (24 assertions) | the full projection | pins **attached arithmetic** — correct as such; asserts nothing about confirmation |
| `smoke_sections/s99_payment_state.py` (9 mutations) | `payment_state` | catches drift between the five dimensions; no mutation concerns acknowledgment |
| `tests/substrate_experiment.py` | — | no payment_plan store |

**Shipped consumers on the default path: none.** Same as H1, and for a stronger reason: the
zero-consumer condition is a *rule*, not an accident.

### Specific contradiction

| ruled | implemented |
|---|---|
| a payment is *attached, unacknowledged* until E acknowledges | a payment is *paid* on attachment |
| confirmed remaining changes only on discharge | `remaining` changes on attachment |
| the projection vs P-ack discrepancy is diagnostic | no P-ack can enter; nothing to diagnose against |
| ahead / overdue are positions against the agreement **as E sees it** | computed from attached `paid` — S2's household believes itself on track while E has it overdue |

The contradiction is **structural, not arithmetic**: the arithmetic over attached payments is
right; what is wrong is that the projection's names — `paid`, `remaining`, `ahead` — assert the
*acknowledged* meaning while computing the *attached* one. The module answers a narrower
question than its vocabulary claims — **the same shape as H1's period-vs-governs**, one
module over.

### Blast radius

- **Today, shipped:** zero, and held at zero by rule.
- **On first wiring:** every consumer reads `remaining` as confirmed. Given S2/S3 (misdirected
  or unauthorised payee), a wired consumer would show the household a balance lower than what
  they owe, and `ahead` where E has them behind.
- **Adjacent, shipped, and outside H2's boundary — flagged for Rob:** the 1.x debt path
  carries the same semantic *and* half of the remedy. `DebtAccount.current_balance` is advanced
  from committed transactions (B3.5, `server.py` ~L8208–8257) — attachment advances remaining.
  `debt_pdf_reconcile` (~L3157) then reads the statement's printed balance, reports
  `balance_check {implied, stated, diff, matches}` — which is F2's diagnostic exactly — and
  **overwrites `current_balance` with the stated figure**, with the comment *"a verified figure,
  not an inference."* That is P-ack winning, monthly; the diagnostic is returned to the caller
  once and not persisted as an attached-unacknowledged state. And `RecurringDebtPayment.
  is_auto_confirm` (default `False`, reserved) is a *household* confirmation step — the
  household confirming a payment happened, which is not E acknowledging it. **Whether the frozen
  discharge rule governs 1.x debt accounts is a doctrine-scope question, not a repair**, and it
  is not decided here. Recorded so the two mechanisms are not repaired separately without that
  decision.

### Minimum safe repair boundary

**There is no code-level repair for H2 that does not introduce representation** — an
acknowledgment input is a new evidence kind, and the ruled sequence's middle state needs a
place to live. Both are the next mode. The minimum that stays inside this one:

1. **The contract.** `payment_state`'s docstring and the module header state that `paid`,
   `remaining`, `ahead` and `overdue` are projections **over attached payments**, that the
   module holds no acknowledgment, and that no figure it returns is confirmed discharge. The
   H1 shape: a correct primitive kept from becoming a semantic trap by saying what it answers.
2. **Naming, as the one code change that is not representation** — offered, not chosen:
   returning the key as `attached_remaining` (and `attached_paid`) rather than `remaining`
   makes a future consumer *unable* to read it as confirmed without noticing. This is Q1's
   lesson in the other direction — *annotating it `float` was the lie that made the bypass
   easy to write.* It costs the fixture's key names and s99's, nothing else, and decides no
   representation. Rob's call whether a rename is inside "minimum".
3. **A guard of the gap-6 kind:** the fixture asserts the *absence* of any accessor or key
   that claims confirmation — `confirmed`, `discharged`, `acknowledged` — so that adding one
   later is a deliberate act with a test to change, not a drift.
4. **Out of the boundary:** any acknowledgment input; the attached-unacknowledged state's
   representation; what strength `remaining` requires; the 1.x debt path (doctrine scope
   first); `ahead`/`overdue` against E's view (needs acknowledgment to exist).

### Coordination note — the shared shape with H1

H1 and H2 are not one mechanism, but they are one **kind** of hazard: a pure module whose
vocabulary claims a broader answer than it computes (*in force* read as *governs*; *attached*
read as *confirmed*), with zero shipped consumers and a fence holding consumers off. The
minimum repair in both is **contract + guard**, not logic. If H3–H5 show the same shape, the
repair pass can be one pass over contracts rather than five over mechanisms.

### Implementation decision — Rob's

Whether the minimum boundary is the contract and the absence-guard alone (1, 3), or includes
the rename (2); and — separately, and first — whether the frozen discharge rule's scope includes
the 1.x debt accounts, which decides whether `debt_pdf_reconcile`'s monthly overwrite is a
partial embodiment to keep or a second mechanism to bring under the same rule later.

**No code is changed by this section.**

### H2 ruling — Rob, 2026-09-12. Boundary accepted with one qualification: no rename yet.

1. **Contract and absence guard: yes.** The module says what it knows — *attached-payment
   projections, not discharge* — and that covers `paid`, `remaining`, `ahead` and `overdue`.
   The absence guard prevents `confirmed` / `discharged` / `acknowledged` being added as though
   they were merely another computed field.
2. **Rename to `attached_remaining`: deferred.** Once it crosses the module/fixture boundary
   it is not merely naming — it changes the vocabulary consumers build around, and whether the
   eventual projection exposes attached amount, acknowledged amount, confirmed remaining, both,
   or an explicit state object is undecided. *A misleading name is a hazard; an unresolved
   replacement name is not yet a reason to choose an API.* The contract prevents the semantic
   lie while preserving the consumer decision.
3. **1.x debt scope: explicitly fenced.** The debt path shows this is not hypothetical, and the
   2.0 discharge doctrine is **not** silently imported into 1.x. Recorded exactly as:

   > **Does the frozen discharge rule have 1.x scope, or is it a 2.0 obligation only?**

   Until answered: do not "fix" `debt_pdf_reconcile`, and do not use its overwrite as precedent
   for 2.0 semantics. Noted distinction: that path treats the statement balance as verified
   evidence of the creditor's position, where `record_payment()` has only attachment evidence —
   potentially useful architecture later; it does not establish that 1.x already satisfies the
   doctrine.

**Coordination ruling.** The H1/H2 comparison is convincing:

| hazard | actual computation | vocabulary overclaim | safe audit response |
|---|---|---|---|
| H1 | period membership | "plan" → governing plan | contract + fail-closed guard |
| H2 | attached payment arithmetic | attached → discharged | contract + absence guard |
| H2 rename | — | ambiguous API vocabulary | **defer** |

A pattern worth watching, **not yet architecture doctrine** — two examples; H3–H5 say whether
it recurs.

**H3 proceeds exactly as stated.** The question is not *is `[-1]` bad?* but: **what proposition
does each consumer need resolved, what temporal axis belongs to that proposition, and is `[-1]`
being used as evidence time or merely insertion order?** The same mechanism may have valid and
invalid consumers — another reason not to fix the resolver globally.

---

*H3 – H5 follow, each on the same rule.*
