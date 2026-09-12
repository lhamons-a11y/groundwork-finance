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

## H3 — the dated resolvers: `knowing[-1]`, `attested[-1]`, and the three others

### Frozen rule

From `SOURCE_TIE_CASES.md` (ruled), `REPARSE_CLUSTER_B_TEST.md` (ruled), Q2:

> Recency is measured on the evidence's own temporal axis, never by record/import position.
> utterance → `recorded_at` · dated document / capture → its **as-of** · import order →
> provenance of arrival, never evidence time. For dated documents `[-1]` is semantically
> invalid as a resolver.

> Two readings of one held artefact that disagree about a value are a **parse dispute**; the
> value is `UNKNOWN` while unresolved — never `[-1]`.

> Same party, same as-of → no evidentiary recency axis → **unresolved**, resolved only by
> evidence (a later as-of, a supersession claim, E's confirmation).

**Rob's audit question, verbatim:** *what proposition does each consumer need resolved, what
temporal axis belongs to that proposition, and is `[-1]` being used as evidence time or
merely insertion order?*

### Actual implementation — every positional read in `core/classification.py`

| # | line | read | over | proposition it resolves |
|---|---|---|---|---|
| R1 | 319 | `determinations(c, axis)[-1]` | the axis's determination history | *the module's current conclusion* |
| R2 | 273 | `knowing[-1]` in `_state_from` | knowing evidence on an axis | *the current state* (health, per axis) |
| R3 | 362, 366, 367, 370 | `knowing[-1][1]`, `dissent[-1]`, `knowing[ri]`, `prior[-1]` in `resolution()` | the same knowing sequence | *how the current conclusion was reached* (Q2's projection) |
| R4 | 593 | `attested[-1]` in `qualifying_amount` | supporting evidence with an amount | *the tax-qualifying figure* |
| R5 | 791, 800 | `sorted(...)[-1]`, `sorted(...)[0]` in `strength_of` | states / sources **sorted by rank** | *the weakest material source* |

And the one fact underneath all of them: **`Evidence` has one time, `recorded_at`, stamped
`_now()` by `record_evidence` at append.** There is no field for a document's own date. So
for a held EOB, `recorded_at` *is* import time — the thing the frozen rule says is never
evidence time.

### Classification, per read

**R1 — valid.** Determinations are *module events*, produced only by `record_evidence`
(the single mutator — `determinations + (_determine(...),)`, L390; nothing else appends).
"Latest determination" *is* "last appended" by construction; the proposition's axis is the
module's own event order, and position is that order. Not a hazard.

**R5 — valid.** These index a list **sorted by rank** with `_prefer_contradicted` as the
tie-break; `[-1]` after sort is *max*, `[0]` is *min*. Not positional in the record's sense.
Not a hazard.

**R2 — valid for some inputs, invalid for others, and the invalid case has no field to fix
it with.** Classify by the evidence kind in the knowing sequence:

| knowing evidence | evidence time per the frozen rule | today | verdict |
|---|---|---|---|
| `USER_STATED` (an utterance) | `recorded_at` | `recorded_at` = append time ≈ when said | **valid** while utterances are recorded promptly |
| `IMPORTED_EOB` (a held document) | **its own as-of** | `recorded_at` = import time; **as-of not stored** | **invalid** whenever import order ≠ document order — T1's late-arriving EOB |

Position and evidence time coincide today *only* because `record_evidence` is the sole
mutator and every knowing party's stance is appended when learned. The tie fixture's own
header says so: *"they diverge the moment evidence is assembled any other way — a merge, a
re-import, or §10's late-arriving discovery."* **The repair is not "sort by `recorded_at`"** —
for a document that is import order under another name (T3). The correct axis for documents
is a field that does not exist. **Representation. Next mode.**

**R3 — inherits R2's axis problem, plus H4's kind problem.** `resolution()` walks the same
sequence, so wherever R2 is invalid R3 is too. Separately, the R-ASSERT ruling: the
source-history kinds are **correct for testimony conflicts** (utterance vs utterance, or
utterance vs document about the *bit*) and **wrong for held-referent parse disputes** (two
readings of one artefact reported as a source reversing). That is H4's audit — R3's positional
reads are noted here and its callers classified there.

**R4 — invalid, and repairable in this mode.** `attested[-1]` resolves a *value* dispute by
position. The proposition is *the tax-qualifying figure*; the frozen rule says a disputed
P-subject value is `UNKNOWN` until resolved by evidence. No time axis rescues it — two
readings of one EOB have the same as-of. **This is H1's shape**: the single-valued contract
can be kept and the ambiguous case *refused*, with no representation decided.

### Actual consumers

| read | internal consumers | external |
|---|---|---|
| R1 | `axis()`, `evidence()`, `resolution()`, `record_evidence` (prior) — everything | — |
| R2 | `_determine` → every determination | — |
| R3 | `_fact_resolution` → `narrator_facts`, `export_row`, `backup_row` | — |
| R4 | `qualifying_total` (→ tax) | — |
| R5 | `consume`, `refusal`, `_permitted_value` | — |

**Production:** none. `server.py` imports six `core/` modules and never `core.classification`
(`HEALTH_TRUST_BOUNDARY.md`'s systemic finding). Tests and smoke sections only: s65, s95, s96,
s98 and five fixtures. **Shipped blast radius: zero** — the third hazard in a row.

**What the suite pins:** `test_evidence_tie_fixture.py` §3 measures R2's position-vs-time
divergence directly and is **failing on purpose** (a discovery instrument, not in the gate);
`test_resolution_projection_fixture.py` pins R3 over 5,460 histories *in call order*; nothing
asserts R4's `[-1]` and s65 does not mutate it — **R4 is unpinned in both directions, like
H1's `[0]`.**

### Specific contradiction

| read | frozen | implemented | when it bites |
|---|---|---|---|
| R2 | latest by evidence time; document → as-of | latest by position; as-of unrepresentable | late-arriving document whose date precedes an utterance |
| R3 | same, plus kinds by referent kind | same, plus source-history kinds for everything | same, plus any re-parse |
| R4 | disputed value → `UNKNOWN` | last-appended amount → the tax figure | any re-parse with a different amount; **decides a tax figure by scan order** |
| R1, R5 | — | — | never |

### Blast radius

Zero shipped. On wiring: R4 reaches the tax total, which `qualifying_total` already presents
with an `UNAVAILABLE` sentinel for the *unevaluated* case — so a consumer of tax already
handles a non-figure. R2/R3 reach every state and every narrator/export/backup row.

### Minimum safe repair boundary

The five reads fall into **three boundaries**, and only one is a code change:

1. **R4 — refuse on disagreement.** When the supporting evidence carries more than one
   distinct amount, `qualifying_amount` returns a refusal rather than `attested[-1]` — the
   H1 shape: fail closed, single-valued contract kept, the resolution's representation fenced.
   `qualifying_total` must then treat a refused amount as making `definitive` `UNAVAILABLE`.
   **One coupling to rule on:** `qualifying_total` today distinguishes *unevaluated* from
   *reviewed, none qualifying*; a *reviewed, amount disputed* transaction is neither, and
   counting it under `unevaluated` would misdescribe it. The minimum is that `definitive`
   becomes `UNAVAILABLE`; whether a third count is added is a small representation question —
   Rob's. Plus the s65 mutation R4 lacks.
2. **R2 / R3 — contract + guard, no logic.** No in-mode repair exists: the correct axis for a
   document is a field the model does not have, and sorting by `recorded_at` would encode the
   wrong axis. The minimum: (a) the module states that `_state_from` and `resolution()` are
   valid **only while the knowing sequence is in evidence-time order**, which holds by
   construction through `record_evidence` for promptly-recorded utterances and is **not
   guaranteed for documents**; (b) a guard that `record_evidence` remains the sole mutator
   (an absence assertion — no other path appends a determination), so the latent stays latent
   *by construction* rather than by luck until the as-of field exists. **Out of the boundary:**
   the document as-of field; any reordering; the reading-level kind (H4).
3. **R1 / R5 — nothing.** Valid; recorded so they are not "fixed" alongside the others.

### Coordination note

- **R4 is H1's shape** (refuse on ambiguity, shape fenced) and **R2/R3 are H2's shape**
  (contract + guard because the repair is representation). The two-kind pattern from H1/H2
  recurs inside one module — which is the evidence Rob asked H3–H5 to supply about whether the
  pattern is real. Three of three so far.
- **R2 and R3 share one axis and must be repaired together, later**, when the as-of field
  exists — the same field the acknowledgment ruling requires for P-ack (*every acknowledgment
  is dated*). One representation decision serves both.
- **Rob's expectation confirmed:** the same mechanism — position over the knowing sequence —
  has valid consumers (utterances; the determination history; rank sorts) and invalid ones
  (documents; values). A global "fix the resolver" would break R1 and R5 and mis-repair R2.

### Implementation decision — Rob's

Whether R4's refusal is in the minimum (with `definitive` → `UNAVAILABLE`, and whether a
*disputed* count is added now or later); and whether the R2/R3 contract-plus-sole-mutator
guard is sufficient to hold the latent by construction until representation mode.

**No code is changed by this section.**

### H3 ruling — Rob, 2026-09-12. Classification accepted; no resolver rewrite.

*The strongest audit so far, because it shows why "find every `[-1]` and replace it" would have
been the wrong engineering move.*

- **R1 — leave alone.** Event order, not evidence time; the position is semantically
  meaningful because the module itself creates the events.
- **R5 — leave alone.** Sorted by rank; `[-1]` means maximum rank, not latest record. Not the
  same hazard class.
- **R4 — fail closed.** A real defect: `attested[-1]` cannot resolve a disputed tax figure
  because one reading was appended last. When the supporting amount is genuinely disputed,
  `qualifying_total` must not emit a figure. *Unevaluated*, *evaluated-none* and
  *evaluated-but-disputed* are semantically different; the third is not collapsed into the
  first because `UNAVAILABLE` happens to exist. **The existing `UNAVAILABLE` output is permitted
  as the fail-closed result without deciding whether the representation needs a third state.**
- **R2/R3 — contract and guard only.** No legitimate algorithmic repair exists because the
  required temporal coordinate does not. `sorted(knowing, key=recorded_at)[-1]` would look more
  principled while encoding the same bug. The conclusion:

  > **The evidence model is missing the temporal dimension required by dated-document
  > resolution.** That is representation, not resolver logic.

  The same missing axis is required by P-ack — an emerging shared requirement:

  ```text
  dated evidence → the evidence's own as-of → resolution by evidence time
  ```

  **Not yet "add `as_of` to `Evidence`."** Not every evidence kind has been audited, nor
  whether every kind can share that representation. Record the requirement; the
  representation decision happens later.
- **R3 — one extra fence.** `resolution()` is not inherently broken because it uses the knowing
  sequence. It is broken when the sequence's ordering is treated as evidence chronology, and —
  separately — it has the held-referent vs asserted-referent resolution-kind problem. **Not
  repaired as part of H3.** H4's caller classification decides which semantic contract each
  invocation needs.

**Coordination finding.** Three of three now guide the remediation pass without becoming an
architecture principle: H1 and H2 — computation narrower than vocabulary → contract + guard;
H3 — some positional reads legitimate, some not, and missing evidence-time representation
prevents the real repair. The engineering lesson: **audit the proposition before auditing the
mechanism.** The syntax `[-1]` tells us almost nothing by itself.

> **H3 accepted:** R1 no change · R5 no change · R4 fail closed on genuine disagreement, no
> state expansion · R2/R3 contract + construction guard, no resolver rewrite · missing document
> as-of: representation requirement, deferred · `resolution()` global repair: deferred to H4 ·
> production blast radius zero, kept at zero.

---

## H4 — `resolution()`: do its callers divide into the two known worlds?

### Frozen rule

Q2 (`RESOLVED_CONFLICT_CASES.md`, ruled and implemented): *resolution = kind · resolver ·
contradictions · post, derived on read from the chain, never stored; travels beside value and
strength; never becomes evidence.* Kinds partition on the resolver's prior stance: `none ·
superseded · reaffirmation · self_reversal`.

R-ASSERT ruling (`ASSERTED_REFERENT_CASES.md` §8):

> Asserted-referent disagreements are **testimony conflicts**, for which `resolution()`'s
> source-history kinds are already correct. Held-referent disagreements may be **reading/parse
> conflicts**, for which they are wrong (D3b: two readings of one artefact reported as
> `self_reversal by imported_eob`). Do not repair `resolution()` globally.

H3 ruling: R3's positional reads over the knowing sequence are valid only while that sequence
is in evidence-time order — a representation requirement, deferred.

**Rob's question:** *do the `resolution()` callers divide cleanly into asserted-referent
testimony history versus held-referent reading/parse history?*

### Actual implementation

```python
resolution(c, axis_name)                                            # L330
    knowing = [(e.source, e.supports) for e in evidence(c, axis_name) if e.source in KNOWING_SOURCES]
    # reads (source TYPE, bit) pairs, in position order; amount, recorded_at, referent: not consulted
```

Two properties of the input that decide H4 before any caller is read:

1. **The projection sees source *types*, not instances.** `IMPORTED_EOB` is the identity of
   every EOB ever imported. Two entries `(imported_eob, no)`, `(imported_eob, yes)` are
   byte-identical whether they are two documents (a source conflict — D4) or two readings of one
   (a parse dispute — D3b). **`resolution()` cannot know which world it is in, because the
   record cannot say.** This is the document-identity gap arriving at H4: the referent
   distinction the R-ASSERT ruling relies on has no field.
2. **It reads the bit only.** Value disagreements (V4) never register; `resolution()` reports
   `none` for `$412` vs `$4.12`. Correct behaviour for a projection over a record that holds no
   value proposition — not a hazard here, a consequence of Cluster B's fence.

### Actual callers — every invocation, classified

| caller | what it passes | what it does with the result | world |
|---|---|---|---|
| `_fact_resolution(derived)` L515 | `derived.sources[0]`, `CONTENT` — **only when exactly one source**; several sources → `None` (multi-source combination is Q2-unspecified and marked *pending*) | returns it to the three consumers below | whatever the single source's evidence is — **the caller cannot tell** |
| `narrator_facts` L528 | via `_fact_resolution` | carries it beside `value` in `NarratorFacts.resolution` | **presentation** — a projection to be shown, never acted on |
| `export_row` L535 | via `_fact_resolution` | `'resolution'` column | **presentation** |
| `backup_row` L547 | delegates to `export_row` | same | **presentation** |
| `test_resolution_projection_fixture.py` | every history of length 1–6 over `{U, E} × {yes, no}`, 5,460 of them | asserts `kind/resolver/contradictions/post` against an oracle | **assumes the testimony world for every entry, including `E`** — an `IMPORTED_EOB` event is treated as *the EOB source spoke*, never as *a reading of a held artefact* |
| `test_evidence_tie_fixture.py` L115–117 | `eob_then_user`, `user_then_eob`, `said_yes` | asserts the conflict remains visible (`contradictions`) | testimony world |
| `s98_resolution_projection.py` | mutations: narrator/export drop it; strength demoted by it; strength carried inside it | asserts the projection **travels beside** value and **never becomes evidence** | boundary properties, world-independent |
| production | — | — | **none** — `core.classification` unimported by `server.py` |

### The answer to Rob's question

**The callers do not divide. The inputs divide, and the record cannot say which is which.**

Every production-shaped caller is `_fact_resolution`, and every consumer of it is
*presentation* — the projection is carried beside a value so a reader can see how the
conclusion was reached. None of the three consumers *branches* on `kind`; s98 asserts that
none may (a resolution that demoted strength or was folded into it is a caught mutation).
So there is no caller that needs the testimony contract and another that needs the reading
contract. **There is one caller, and it needs the true history — which is the testimony
history when the knowing events are utterances or distinct documents, and the reading history
when they are readings of one held artefact.** The projection cannot deliver the second because
`Evidence` carries a source type and no referent.

This is the same finding as H3's, one level up: H3 found the *temporal* axis for documents has
no field; H4 finds the *identity* axis for documents has no field. Both are the document-
referent representation the Cluster B ruling named as jointly necessary with the proposition
space, and both are what `resolution()` would need to be correct for held artefacts.

**And the fixture pins the wrong world for `E`.** 5,460 histories treat every `IMPORTED_EOB`
event as a source stance. For genuinely distinct EOBs that is right; for a re-parse it is the
D3b misreport, asserted as correct. The fixture is not wrong about the *projection* — it is
faithful to a record that cannot distinguish — but it will have to be re-pointed when the
referent exists, and that should be known now.

### Specific contradiction

| situation | frozen | `resolution()` today |
|---|---|---|
| utterance vs utterance (D8) | testimony conflict; source kinds correct | correct |
| utterance vs held document, on the bit (T1) | testimony conflict on the bit; source kinds correct — *ordering* subject to H3 | correct in call order; wrong if document date ≠ import order |
| two distinct documents (D4) | source conflict; `self_reversal by imported_eob` **is** what happened | correct |
| two readings of one document (D3b) | parse dispute; needs a reading-level kind | **`self_reversal by imported_eob` — a source reversal that did not happen** |
| value disagreement (V4) | not this projection's | `none` — correct for what it reads |

Only one row is wrong, and it is wrong because the record cannot distinguish it from the row
above it.

### Blast radius

Zero shipped. On wiring: the narrator, export and backup would carry a resolution whose
`kind` is wrong for re-parsed records — a wrong causal story, faithfully projected, in the
narrator's input and the export file. Not a value error; a *provenance* error, which is the
kind Q2 was built to prevent.

### Minimum safe repair boundary

**No resolver change.** Confirmed from the other side: there is nothing to branch on. The
minimum:

1. **Contract.** `resolution()`'s docstring states its domain: *source-history kinds over
   knowing events; correct where each knowing event is a distinct source stance (utterances,
   distinct documents); not applicable to multiple readings of one artefact, which the record
   cannot yet distinguish.* And that its ordering assumes H3's construction guard.
2. **The fixture's assumption made explicit.** A one-line note in
   `test_resolution_projection_fixture.py` that its `E` events model distinct-source stances
   and will need re-pointing when a document referent exists. Not a code change; a
   provenance note on a test, so that the day the referent lands the 5,460 are not read as
   proof the projection is right for re-parses.
3. **Out of the boundary:** the reading-level resolution kind (needs the referent — Cluster B
   representation); the document as-of (H3, same field family); the multi-source
   combination (Q2-pending, deliberately); anything in the three consumers.

### Coordination note — four of four

H4 is H3's shape exactly: a mechanism that is correct for the inputs it can distinguish and
wrong for the ones it cannot, where the fix is **a field the record lacks**, not logic. Across
H1–H4 the pattern now reads:

```text
H1  vocabulary > computation          contract + fail-closed guard
H2  vocabulary > computation          contract + absence guard
H3  position ≠ evidence time          contract + construction guard; as-of field deferred
H4  type ≠ instance                   contract + fixture note;     referent field deferred
```

And H3 + H4 together name the representation decision that build mode will face first:
**dated, individuated evidence** — the as-of and the referent — which the Cluster B ruling,
the acknowledgment ruling, the tie ruling and the R-ASSERT ruling all require, and which no
resolver rewrite can substitute for.

### Implementation decision — Rob's

Whether the contract and the fixture note are the whole of H4's minimum; and whether the
"dated, individuated evidence" requirement is recorded now as the first item of the
representation mode's agenda, without deciding its shape.

**No code is changed by this section.**

### H4 ruling — Rob, 2026-09-12. Minimum accepted exactly as proposed.

1. **No resolver repair.** `resolution()` receives an observation model in which two readings
   of one artefact and two independent artefacts are indistinguishable. *No resolver can
   recover a distinction that isn't represented.* Changing it would be cosmetic at best,
   dangerous at worst.
2. **Contract: yes.** `resolution()` operates on source-history events where each knowing event
   is a distinct source stance — `self_reversal by imported_eob` legitimate for D4,
   illegitimate for D3b. The H3 ordering assumption belongs in the same contract.
3. **Fixture note: yes.** Prevents the large fixture becoming accidental doctrine: 5,460
   histories demonstrate behaviour under a particular provenance model; they do not establish
   it for a future model containing document identity and readings.

**The architectural conclusion — recorded as a requirement, not a design:**

```text
                 dated, individuated evidence
                    /                 \
              evidence time       referent identity
                   |                    |
                 H3 / R2              H4 / D3b
                   |                    |
             P-ack ties            parse disputes
                    \                  /
                     Cluster B / R-ASSERT
```

Acknowledgment evidence adds the same temporal requirement without proving its storage shape
must be identical. So the agenda item is a **capability requirement**, not *add two fields to
`Evidence`*:

> **Representation requirement: the evidence model must be capable of preserving an evidence
> item's own temporal coordinate and individuating referent where those properties are
> required to distinguish source chronology or artefact readings. Representation shape
> remains undecided.**

> **H4 status:** contract accept · fixture provenance note accept · resolver rewrite
> reject/defer · reading-level kind defer · document as-of defer · referent representation
> defer · consumers not modified · shipped blast radius zero · representation agenda item yes,
> requirement only. The four-pattern summary stays an audit observation, not doctrine.

**H5 is to be treated differently.** Unlike H1–H4 there is a live path — `callAI()` and the
voice gate. Its blast radius must distinguish, carefully:

```text
(1)  a live safety failure
(2)  a latent safety hazard with no currently demonstrated violating output
(3)  a representation / boundary weakness exploitable only when a future finding
     reaches the narrator
```

That distinction decides whether H5 gets contract + guard or an actual remediation boundary.

---

## H5 — the narrator authorisation boundary

### Frozen rule

`NARRATOR_VOICE_PERMISSION_TEST.md` §5, ruled:

> A claim may be voiced only when the claim is asserted by the findings record. A manufactured
> classification is not an asserted claim, and narrator inference from strings is never an
> authorisation to make one. **Findings text is an authorisation-bearing boundary, not a
> neutral transport layer.** Sensitivity may travel to policy-enforcing components (the
> boundary, the gate) but may not become model-visible content merely because it exists.
> Enforcement is upstream (boundary, visible refusal) or downstream (gate, check) — **the model
> is never an enforcement locus.** §9 unchanged.

Standing, adjacent, not reopened: `HEALTH_TRUST_BOUNDARY.md` — F3 (`voice_miss_log.jsonl`
stores rejected narration verbatim) is a replica outside the sensitivity layer; five of six
release-blocking conditions hold today against financial data.

### Actual implementation — two halves, one live and one not

**Live (1.x, shipped):** `static/js/app.js`

```text
surface assembles a prompt from S (the household's 1.x data)
   → callAI({system, messages, surface, skipGate?})                       L22351
       findings := the user-message text                                    (what the model knows AND may say)
       → POST /api/ai/chat  → server.py → local Ollama | Anthropic cloud   (provider-switched, L6607)
       → _voiceGateCheck(text, findings)                                    L22264
            R1–R5b, R7, R9: wordlists     R8: every figure in text ∈ findings
            reads TEXT ONLY; no sensitivity input; no claim-level rule
       → on rejection: _logVoiceMiss(surface, model, rules, text)  → voice_miss_log.jsonl (F3)
       → retry ×2 with the offending phrases cited; then ok:false → honest fallback
```

The system prompt (`static/voice_rules.json` → `GW_VOICE`) already **asks** for the frozen rule:
*"Computed facts you were given are stated plainly… Anything NOT computed gets explicit
uncertainty or is omitted entirely. Never present an inference as a finding."* The gate
**enforces** it for figures (R8) and for inference *verbs* (R3), and for nothing else.

**Not live (2.0, unwired):** `core/classification.py` — `narrator_facts()` builds
`NarratorFacts(metric, value, includes_records=False, resolution)` with **no sensitivity
field**; `_permitted_value` refuses on **strength only**; the boundary fixture's AST scan
catches `.value` reads outside `consume()` and **not `.sensitivity`**. No production caller.

### Actual consumers — every gated surface, and what it hands the model

| surface | gate | what enters the findings | free text? |
|---|---|---|---|
| `monthly_report` L10029 | yes | category names, totals, budget deltas; **a user-typed annotation** | the user's own words |
| `sunday_checkin` L11372 | yes | spent, income, *biggest category* name + amount | no |
| `projection` L22493 | yes | one category name, over/surplus, redirect target debt name, dates | no |
| `monthly_report_v2` L23384 | yes | spent, income, top **parent** categories, price benchmarks; **the annotation** | the user's own words |
| `trip_learn_classify` L10374 | **skip** | transaction ids · dates · **descriptions** · categories | yes — but the model returns bucket labels only, no prose; no number in its output |
| `trip_quote_extract` L10563 | **skip** | a pasted quote | JSON extraction |
| (L11105) | **skip** | live web prices | JSON |

**No gated surface passes a transaction description or memo to the model.** What reaches a
gated model's findings is: category names (user-set, or the importer's parent-category map),
computed totals, debt names, dates, price benchmarks, and the household's own annotation.

### Specific contradiction, classified by Rob's three kinds

**(1) Live safety failure — none found.** The frozen rule is *voiced claims must be asserted in
the findings*. On every gated surface today, every claim-bearing string in the findings is
**asserted by the household**: a category name the user set (content evidence — asserted; the
*Prescriptions* row of the voice test), a parent-category name derived from it, or the user's
own annotation. There is no classifier-manufactured claim on the live path (1.x has no
classifier of that kind), and no unasserted memo for the model to infer from (the
*wheelchair ramp lumber* row is unreachable). A narrator sentence *"Medical was your largest
category at $412"* is authorised — the category is asserted and the figure is in the findings.
**Under the frozen rule, the live path is clean.**

**(2) Latent hazard, no demonstrated violating output — one, and it is the important one.**
The live path is clean **by construction of its inputs, not by enforcement.** Nothing checks
that a gated surface passes only asserted content; the gate has no claim-level rule; the
system prompt asks. The day a surface passes `t.description` into a gated prompt — the
skip-gated trip classifier already does, harmlessly, because it returns labels — the narrator
can manufacture a claim from wording and R3's verb list is the only thing in its way. No such
surface exists; no violating output is on record; the harness does not exercise it. Latent,
reachable by an ordinary feature change, ungated.

Also (2), already on the register and not reopened: F3 stores rejected sentences verbatim,
and a rejected sentence about a *Medical* category is health-sensitive by limb 2. Gap 12's
finding; 1.x's data is financial; recorded there as release-blocking for 2.0.

**(3) Boundary weakness, exploitable only when a future finding reaches the narrator —
three, all in the unwired 2.0 module:**
- `NarratorFacts` carries no sensitivity → the 2.0 narrator would receive a manufactured
  health figure with no way to know (the two-CVS case). Ruled: sensitivity travels to the
  gate/boundary, never into the model's text; **which reader gets it is the representation
  decision**, and no field exists for either.
- `_permitted_value` refuses on strength only → a manufactured health fact reaches
  `narrator_facts` if corroborated. The ruled locus for a refusal-with-reason has no rule in
  it yet.
- the boundary fixture scans `.value` only → a future surface reading
  `DerivedFact.sensitivity` directly and serialising it into findings would be the
  representation-becomes-authorisation collapse, and the scan would not see it.

### Blast radius

| kind | radius |
|---|---|
| (1) | **zero** — no live violation |
| (2) | **every gated surface, on the next feature that passes free text**; today none does. Not a production repair; a construction that must be made a guarantee |
| (3) | zero shipped; the full 2.0 narrator on first wiring |

**H5 is the first hazard whose live-path radius is not zero by rule** — it is zero by the
accident of what four surfaces happen to pass — and the first where a *contract* cannot hold
the line, because the contract's subject is JavaScript surfaces added by feature work, not a
pure module with a fence on its consumers.

### Minimum safe repair boundary

Two different answers for the two halves, and Rob's question — contract + guard, or an actual
remediation boundary — comes out **split**:

**Live half — an actual guard, small, no policy decided.** The property to guarantee is *a
gated surface's findings contain only asserted content*. Two ways in this mode, neither a
claim-provenance rule:

1. **Declare it at `callAI`.** A gated call names what it passes — `findings_kinds:
   ['category', 'total', 'annotation', …]` — and `callAI` refuses a gated call that declares
   `description`/`memo`/free transaction text, or that declares nothing. The declaration is
   the guard; the list of asserted kinds is short and known. Fail-closed for new surfaces: an
   undeclared gated call does not run. **Decides no policy** — it enforces the input side of
   the ruled rule (*asserted in the findings*) rather than the output side (a claim check).
2. **Or a harness assertion** over the four prompt builders that no `t.description` / memo
   reaches a gated prompt — weaker (it pins today's surfaces, not tomorrow's) and cheaper.

The first is the actual remediation boundary Rob asked whether H5 needs: **yes, for the live
half, and it is an input declaration, not a claim resolver.** The gate's text-only design and
R8's number rule are untouched.

**Unwired half — contract + guard, as H1–H4.** `NarratorFacts`'s contract states it carries
no sensitivity and that the findings assembler must never serialise `Sensitivity` into model
text (the ruled collapse); the boundary fixture's scan extends to `.sensitivity` reads outside
the declared consumers — the wiring condition the voice test recorded. Representation of the
gate-side reader: deferred with H3/H4's requirement.

**Out of the boundary:** any claim-provenance rule in the gate (R8 vs a sibling — fenced);
11's policy beyond narration; F3 (gap 12's); the cloud provider path (a crossing, gap 12's);
`_permitted_value`'s sensitivity refusal (needs the rule and the field — build mode).

### Coordination note — four and a half of five

The unwired half is the pattern (contract + guard, representation deferred). The live half is
**not** — it is the first place the audit finds a property that holds by construction on a
surface that feature work can change, and the response is a **declaration-based input guard**,
which is a new kind of repair in this audit. Recorded as the exception that the pattern needed
in order to be a pattern and not a reflex.

### Implementation decision — Rob's

Whether the live half's guard is the declaration at `callAI` (fail-closed for undeclared gated
calls) or the harness assertion; whether it is in this mode's boundary at all given no
violating output exists; and whether the unwired half's contract + scan extension is
sufficient until representation mode.

**No code is changed by this section.**

### H5 ruling — Rob, 2026-09-12. The right place to break the pattern.

**Live half: the declaration-based guard, inside the remediation boundary.** Not because
today's four surfaces are unsafe — they are not — but because the current safety property is
**accidental and feature-addition fragile.** A harness assertion says *these four things are
safe today*; the declaration says *a gated narrator call must explicitly declare what evidence
classes it is authorised to receive.* Materially stronger. Frozen for remediation:

> **A gated `callAI` invocation must declare its findings kinds. An undeclared gated
> invocation, or one declaring prohibited free transaction text, fails closed.**

This does **not** establish a claim-provenance policy — it is an input-side boundary only.
`callAI()` must not start interpreting individual claims, resolving provenance, or deciding
whether a sentence is allowed; that belongs to the later gate design.

**Why declaration over harness:** it makes the caller state its contract at the crossing.

```text
without:   feature → prompt builder → callAI → model        (reviewer inspects the whole builder)
with:      feature → declared findings kinds → callAI → model
                                  ↓
                             fail closed                    (the crossing is auditable)
```

Appropriate for Groundwork because the model is downstream of a deterministic evidence
boundary, not a participant in deciding what evidence is permissible.

**Unwired half: accepted as proposed** — `NarratorFacts` contract; no sensitivity
serialisation into model-visible findings; boundary fixture extended to detect
`.sensitivity`; the sensitivity-aware reader deferred to the representation/gate decision.
**`_permitted_value` is not modified** — neither the representation nor the settled gate
rule exists.

**Wording correction, applied:** *dated / individuated evidence* is a **representation
requirement**; the *sensitivity reader* is a **boundary capability requirement**. Adjacent,
not one schema requirement — the audit has not established that the reader's storage shape
belongs to the same representation decision.

| part | ruling |
|---|---|
| today's four gated surfaces | safe |
| live future-feature hazard | **real latent hazard** |
| live remediation | **yes — declaration at `callAI`** |
| harness alternative | rejected as primary boundary |
| claim-level gate | deferred |
| R8 | untouched |
| `_permitted_value` sensitivity | deferred |
| `NarratorFacts` contract | accept |
| `.sensitivity` boundary scan | accept |
| model as enforcement locus | absolutely not |

> **The absence of a violating output does not prove the boundary is safe when the safety
> property exists only because today's callers happen to behave.** A legitimate remediation
> target even with zero shipped blast radius.

### H5 correction — found during remediation, 2026-09-12. The audit under-counted the live path.

**The audit's consumer table was wrong.** It enumerated `callAI` sites by the literal
`surface: '…'` and found four gated surfaces. The static declaration check written for the
remediation found two more `callAI` sites with template-literal surface names — the generic
report path `_rcAnalyzeWithAI` (`surface: reportId`) and its follow-up thread
(`surface: \`${reportId}_followup\``) — through which **sixteen** further report kinds reach the
gate: `savings_goals_advisor`, `trip_advisor`, `debt_advisor`, `investment_advisor`,
`gift_advisor`, `retirement_advisor`, `trophy_room_narrative`, `snapshot`,
`distance_traveled`, `income_savings`, `debt_payoff`, `annual_*`, `category_*`, and the
report-centre re-analysis path. The follow-up additionally passes the user's own typed
question (asserted — the annotation's shape).

**Fifteen of the sixteen are clean** on inspection of their prompt builders: goal, debt,
person, category and achievement *names* (household-asserted), computed figures, dates,
price benchmarks.

**One is not.** The category report (`category_<name>_<from>_<to>`, `app.js` ~L23588–23699)
builds its prompt with

```text
Top merchants: <name> ($amt), …      where name = t.merchant || t.description
```

— bank description strings, on a gated surface, today. `CVS PHARMACY #1234 ($180)` is
exactly the referent-2 input the voice ruling named: the record asserts no health claim for
those rows (1.x has no classifier), and the narrator can infer one from the string and voice
it; R3's verb list is the only thing in the way.

**Classification, corrected:** the live path is **(2) with an existing input path**, not (1)
"none" and not (2) "reachable only by a future feature". No violating output has been
observed; that is the accident — the path exists. The (1) claim *"no gated surface passes a
transaction description or memo"* is withdrawn.

**Remediation state.** The declaration is implemented: a vocabulary of asserted kinds, a
prohibited set (`description · memo · transaction_text · free_text · notes · merchant_text`),
`callAI` refusing an undeclared or prohibited gated call before the model, the four literal
surfaces declared, a registry for the generic path keyed by `reportId` (prefix-matched for
`category_*` / `annual_*`; an unknown id is undeclared and refuses), and the follow-up
declaring the report's kinds plus `user_question`. The static check in
`s25_voice_rules_sync.py` pins that every gated call declares and every kind is known.

**The category report is declared truthfully — `['category', 'total', 'date',
'merchant_text']` — and therefore refuses at runtime under Rob's rule as written.** Its AI
analysis falls through to the non-AI rendering; the merchants table the household sees is
unaffected (that is HTML, not findings). The static check reports the surface as refusing,
which is one honest red line in the gate.

**Not decided here — Rob's, and the JS half is uncommitted until he rules:**
- (a) **keep it refusing** — the surface stays dark until its builder is redesigned;
- (b) **trim the merchant line from the prompt's `dataLines`** — the AI analysis returns, without
  merchant names in its narration; the on-screen merchants table stays;
- (c) **admit `merchant` as an asserted kind** — rejected on the audit's own evidence unless Rob
  reads the bank's description string as household-asserted, which the voice test's
  *wheelchair ramp lumber* row says it is not.

**What this correction says about the audit method:** the static guard found in one run what
the manual enumeration missed. That is the argument for the declaration over the harness,
made by the declaration itself.

---

## Audit summary — H1 to H5

| hazard | shipped radius | kind | minimum boundary | status |
|---|---|---|---|---|
| H1 `plan_at`/overlap | 0 | vocabulary > computation | refuse on multi-period; guard `accumulators`; contract; mutation | **ruled** |
| H2 `record_payment`/`remaining` | 0 (by rule) | vocabulary > computation | contract; absence guard; rename deferred; 1.x scope fenced | **ruled** |
| H3 dated resolvers | 0 | position ≠ evidence time (R2/R3); value by position (R4) | R4 refuse; R2/R3 contract + construction guard; as-of deferred | **ruled** |
| H4 `resolution()` | 0 | type ≠ instance | contract; fixture note; referent deferred | **ruled** |
| H5 narrator boundary | (2) with a live input path (corrected) / (3) unwired | one gated surface passes bank description strings | live: input declaration guard — built, one surface refuses, Rob to rule; unwired: contract + scan — done | **ruled; correction pending** |

**Two requirements carried forward, adjacent and not merged (Rob):**
- **Representation requirement** (H3, H4, and four evidence-mode rulings): dated, individuated
  evidence — an evidence item's own temporal coordinate and individuating referent, where
  required to distinguish source chronology or artefact readings. Shape undecided.
- **Boundary capability requirement** (H5-unwired): a sensitivity/provenance reader at the
  narrator boundary on the gate side, never in the model's text. May or may not touch the
  representation; not assumed to.

**Coordination:** H1–H4 repair as one contract-and-guard pass over three modules with zero
shipped consumers, plus two fail-closed refusals (`plan_at`, `qualifying_amount`). H5's live
half is its own small change at one choke point.

---

## Audit phase — closed. Rob, 2026-09-12.

**H1–H5 audited and closed.** No code was changed under the audit. The only changes later made
are the contract / fixture / guard decisions explicitly authorised above, applied in
remediation.

**Next mode, explicit: REPRESENTATION & REMEDIATION DESIGN.** Not implementation. Take the
exposed requirements and determine the **smallest representation** that can carry:

1. evidence referent identity
2. the evidence's own temporal coordinate
3. P-ack / acknowledgment evidence
4. the reading-vs-source distinction
5. sensitivity / provenance at the narrator boundary
6. the unresolved states required by the consumers

while deliberately **not** deciding what remains fenced: `plan_at()`'s eventual return shape ·
payment projection semantics · supersession semantics · the full claim-level narration policy.

**Carried separately, not buried in representation work:** *does the frozen discharge rule
have 1.x scope, or is it a 2.0 obligation only?*
