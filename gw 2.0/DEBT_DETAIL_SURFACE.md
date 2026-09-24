# The debt as a navigable object — concept, violations, semantic tests, gates

> Status: **Concept + case set, 2026-09-24. No code. Not in the build queue — its number, if
> any, is Rob's. G4 and G5 RULED (Rob, 2026-09-24), §11; the §12 teaching principle AGREED (Rob, 2026-09-24);
> every other gate open, G7 included.** Concept
> layout: the *Debt Detail Concept Layout* canvas (claude.ai artifact, private). Written from Rob's concept note of the same day and his review of the first
> read against the code. The review's instruction: *not "here is the feature," but the concept,
> the discovered violations, the semantic tests, and the gates that must pass before
> implementation.* Cases first, then rulings, then implementation only after the meaning is
> stable.
>
> **The concept exposed existing violations.** Reading it against 1.x found five places where
> the shipped debt surfaces already break the rules the concept depends on (§4); a sixth, V6, was
> found investigating the fifth. V1 and V5 are fixed on 1.x; V2–V4 and V6 are open. A debt view built
> on today's code would carry every one of them into a new surface and give them a teaching voice.
> **Do not build the view yet** (Rob, 2026-09-24).

**Rob's question, as the concept frames it:** *can a debt be opened from wherever it is shown —
"Debt → specific debt → understand this debt" — so that the user can see what they owe, on what
terms, what has happened, what it costs, what Groundwork knows versus what they told it, what it
calculates, what changes if something changes, and what is unknown — without creating a new
layer of financial authority?*

---

## 1. The concept, condensed

**What it is.** A contextual view of one existing debt — credit card, store card, auto loan,
mortgage, or any loan Groundwork has enough information to model — opened from its name wherever
the debt is shown (first: the Debt page). Checking, savings and other non-debt accounts do not get
one.

**Why debt and not accounts.** Without debt, a spending decision is close to
`available − spending = remaining`, and the ledger answers it. Debt adds a second object: a
transaction can change an obligation whose meaning depends on its terms, history and balance. A
card purchase moves balance, available credit, utilization, interest, required payment and payoff
timing; a car loan or mortgage has different consequences because its structure is different. The
debt is the useful object for explanation.

**What it gathers** — never creates:

| Group | Contents (as applicable to the debt type) |
|---|---|
| Current state | balance · original balance · credit limit · utilization · APR / rate · required payment · remaining term · payoff information already calculated |
| History | payments · interest charged · fees · balance changes · APR / rate changes · relevant transactions · other documented changes |
| Calculated | utilization % · principal / interest split · projected payoff · interest under stated assumptions · effect of extra payments · effect of a proposed purchase · trajectory change |
| User-supplied | anything the user entered or corrected — its provenance kept distinct from a statement's |

**The teaching role.** The teaching model explains the debt from seven kinds of input, and only
these: observed information · user-supplied information · Groundwork calculations · documented
terms · known history · explicit assumptions · explicit unknowns. It is not a financial advisor for
the debt. *"Your balance is $3,800 and the limit you entered is $5,000, which is 76% utilization"*
is in scope, as is explaining what utilization means. *"You should get below 30%"* is not. An APR
change may be shown; its reason may not be supplied unless the evidence establishes it. Unknowns
stay unknown.

**The architectural principle** (the concept's own, and the one every gate below serves): **the
debt view is a lens over existing financial knowledge, not another financial system.** No second
balance, no independent payoff calculation, no second transaction history, no recommendation
engine. The financial engine stays authoritative; the view assembles, the teaching layer explains.

**Success:** the existing debt information becomes more understandable and nothing becomes more
authoritative.

---

## 2. Already ruled or recorded, and therefore constraining

| Record | What it fixes for this surface |
|---|---|
| `CALCULATION_PLACEMENT.md` | *Split by claim, not by math.* A number used to tell the user something is true belongs where it can be tested and logged (Python), not in a render function. Utilization-as-verdict and per-debt payoff dates are claims. |
| `VALUE_DISAGREEMENT_CASES.md` | A disagreement must be **representable** before it can be resolved by anything other than position or recency. Test 11 is this requirement arriving on the debt side. |
| `PROVENANCE_IDENTITY_CONTRACT.md` | Source lineage / artefact identity / reading identity. Rule 2 below is this contract applied to debt figures that today carry none of it. |
| `OBLIGATION_IDENTITY.md` (ruled, built) | The obligation is already a 2.0 identity. Whether "the debt" of this concept is that identity, a view of it, or a 1.x row is Gate 0's question — not assumed here. |
| `RESERVE_PAYOFF_QUESTION.md` (**open**) | The payoff half of Open Question 6 is unanswered. Any payoff figure this view shows inherits that openness. |
| No-silent-learning boundary | The view may not persist anything learned from what the user opens, lingers on, or ignores. |

---

## 3. Four architectural rules

The first read's four findings reduce to four rules (Rob, 2026-09-24):

**R1 — A metric is not a prescription.** Utilization can be calculated and taught. Groundwork must
not silently turn it into a target — by a sentence, a threshold, or a colour.

**R2 — A number needs provenance.** `22.9%` is not interchangeable with *the user entered 22.9%*
or *the statement reported 22.9%*. The view cannot teach from those as though they were one fact.

**R3 — A debt type has semantics.** A mortgage is not a credit card with a large balance. If the
engine supports only card-shaped payoff semantics, the view must not manufacture amortization
semantics the engine does not possess.

**R4 — A payoff result has dependencies.** *"This debt pays off on X"* is incomplete if X depends
on the household's other debts, the strategy, and the payoff budget. **The result belongs to a
scenario, not intrinsically to the debt.**

And a fifth, from the Before You Buy discussion, which is a rule about the lens itself:

**R5 — A lens that must change an engine's inputs is no longer a lens.** That can be right, but
only when it is deliberately authorised and named as an **engine capability**, never introduced as
UI behaviour.

**R6 — The cost of a financed purchase is a scenario, not a number.** Added with the G4 / G5
rulings; stated in full in §11.

---

## 4. Discovered violations — measured in 1.x, 2026-09-24

Each is shipped behaviour today, independent of whether the debt view is ever built.

### V1 — the utilization line prescribes (R1)

[`static/js/app.js:8991-8999`](../static/js/app.js) renders *"Combined credit utilization: X%
across N cards with limits. **Target: under 15%.**"* and colours the figure ember at ≥30%, gold at
≥15%, pine below. That is the concept's own counter-example, shipped: a target sentence plus two
thresholds encoded as judgement colours. It is also a claim-backing calculation living in a render
function, which `CALCULATION_PLACEMENT.md` already says it should not be.

> **FIXED on 1.x, 2026-09-24 (Rob: "fix V1 and V5 in 1.x"), `f7a93bb` + `e81d6db` on `lts/1.x`,
> merged into master.** This entry named one site and there were three: the combined line above,
> a per-card utilization bar coloured at the same 30% / 15% thresholds, and a per-card line
> reading *"— aim for under 30%"*, *"— aim for under 15%"* or *"— good"*. The first sweep searched
> for "utiliz" and the two siblings only say `utilPct`; `e81d6db` fixed them after the master
> merge's own check found them. All three now show the percentage alone, in one neutral colour.
> **What V1 does not close:** the calculation still lives client-side in render code — G1's
> second half (a named, tested contract per `CALCULATION_PLACEMENT.md`) stays open.

### V2 — the current APR loses its source (R2)

`debt_pdf_reconcile` ([`server.py` ~3275](../server.py)) writes the statement's APR over
`DebtAccount.interest_rate`. Before the reconcile, that column holds what the user typed; after
it, the statement's figure; afterwards, nothing records which. *"You entered 22.9%"* and *"the
statement says 24.9%"* collapse into one number, and the earlier one is gone — so the disagreement
test 11 needs cannot even be observed, let alone represented.

`DebtAccount.credit_limit` ([`core/database.py:146`](../core/database.py)) is one nullable float
with no source. The PDF path does not extract a limit, so today every stored limit is in fact
user-entered — but the record cannot say so, and the first time any path writes a statement limit
the same collapse happens.

`DebtBalanceHistory` has no source column. The only trace is `statement_period_end`, which the
statement path fills and the manual path does not — an inference from a side effect, not
provenance. `DebtLedgerEntry.source` (`manual` / `imported` / `inferred` / `draft` / `skipped`)
is the one debt record that already carries its origin.

### V3 — debt type is read only for leases (R3)

*Correction to the first read, which said "every debt is modelled as a credit card." More
precisely:* `core/consequence.py`'s `Card` carries balance, rate, minimum, and flags for leases and
income-driven forgiveness. Its month-by-month arithmetic (interest on balance, less a fixed
payment) is in fact correct amortization for a fixed-payment loan. The gap is semantic, not
arithmetic:

- the engine consults `debt_type` only to detect a lease ([`server.py:1796`](../server.py));
  `DebtAccount.end_date` exists but is not a term the engine reasons from;
- a **scheduled payment** and a **minimum payment** are the same field, though one is a contract
  term and the other a floor;
- a mortgage payment that includes **escrow** would be treated as entirely principal and
  interest, projecting payoff early — and the record has nowhere to say what the payment is made
  of;
- utilization, available credit, and "a purchase on this debt" are meaningless for an instalment
  loan, and nothing in the model marks them so.

So the engine can produce numbers for a mortgage; it cannot know which of its outputs mean
anything for one.

### V4 — per-debt payoff dates exist without their scenario (R4)

`simulate_payoff` is a household calculation: every debt, one strategy (avalanche default), one
budget. The client's avalanche sequence
([`app.js` ~8495](../static/js/app.js)) records a `payoffMonth` **per debt** as a by-product of
that household run. A single debt's month is a function of every other debt, the strategy, and
where extra money flows. Displayed on the debt alone it becomes a naked *"Payoff: March 2028"* —
and it would change when the user adds a different card, with nothing on the screen explaining why.

### V5 — Before You Buy commits a financed purchase as a debt with invented zeros (R2, R3, R5)

On `commit` of a vehicle or purchase decision, Before You Buy **creates a real `DebtAccount`**
([`app.js` ~20381](../static/js/app.js)) with `current_balance: 0`, `begin_balance: 0`,
`interest_rate: 0` and `minimum_payment` set to the monthly figure. The principal and rate are
unknown, and the record says they are zero. That is absence written as zero, into the
authoritative debt table, from a UI flow — a second, weaker debt model created outside the one the
concept says must stay authoritative. A debt view opened on that record would teach *"0% APR,
$0 balance"* from nothing.

> **FIXED on 1.x, 2026-09-24, `f7a93bb` on `lts/1.x`, merged into master.** Worse than recorded
> here: the credit-purchase path already asked for an APR and discarded it. 1.x cannot store
> "unknown" (the server turns a missing figure into 0), so Rob ruled **require them**: the vehicle
> loan path now asks for the amount financed, APR and an optional term; the credit-purchase path
> adds the amount financed; Commit stays disabled with a stated reason until both figures are
> entered, and a blocked commit writes nothing, history included. 0% is accepted when typed. A
> **lease** is unchanged — no balance and no APR by design; the rate is in the payment (Rob). Rows
> already written at $0 / 0% by earlier installs are not touched (§9 question 5 stays open).

*Also found, bearing on test 8 / 14:* `simulate_payoff`'s `one_time_cost` is documented as
**money that will not reach the debt** — cash from the same surplus the extra payment came from,
the stated optimistic reading. "$300 **on Card A**" is the opposite: it adds to one specific
balance. The engine has no input that means that today. Before You Buy's current card-purchase
consequence is therefore the cash reading, whatever the user intends to pay with.

### V6 — the Debt page collapses a blank into zero (R2) — OPEN

*Found 2026-09-24 while investigating question 5 (V5's legacy rows); recorded at Rob's direction.*

**The Debt page currently collapses blank APR, balance, and minimum-payment inputs into numeric
zero, and the database does not preserve whether zero was entered or produced by a blank input.
Because zero is a legitimate value for at least APR and balance, the stored value cannot
subsequently distinguish known zero from unknown.**

- **Where:** `_syncDebtToDb` sends `parseFloat(card.rate) || 0`, and the same for
  `begin_balance` and `minimum_payment`, on every create **and every edit**; `create_debt` in
  `server.py` independently turns a missing field into `0`. This is the main entry point for debts,
  not a legacy path — the zero is being written today.
- **Why it cannot be repaired after the fact:** 0% is a real rate (promotional financing) and $0
  a real balance (a debt paid off), so zero is sometimes a value and sometimes a placeholder, and
  nothing in the row records which. On load, `restoreFromBootstrap` hands the stored `0` back as a
  real 0%, so every calculation and display downstream treats it as known.
- **What already distinguishes:** `credit_limit` is nullable and blank is stored as null — in the
  one database measured, 17 of 17 rows null and none at 0. `DebtLedgerEntry.source` is the other
  debt record that carries its origin. V6 is the gap between those and the three core figures.
- **Relation to the rest:** the same failure as V2 (a number without its source) at the most-used
  entry point, and the representational half of G2. It is a data-semantics gap, not an urgent
  defect: nothing is miscalculated that the user did not leave blank.

**Status:** OPEN. No code and no migration authorised (Rob, 2026-09-24).

---

## 5. The semantic tests

Fifteen cases. Twelve are the concept's; 13–15 were added in Rob's review. *Current state* is
what the 1.x code does today where it was measured, and says **not measured** where it was not —
no case is marked passing by assumption.

| # | Case | Question | Rule | Current state |
|---|---|---|---|---|
| 1 | No debt | Does Groundwork avoid inventing a debt surface when the ledger is sufficient? | lens | not measured |
| 2 | Credit card | Can the view explain balance, limit, utilization, APR, payments and interest without turning into advice? | R1 | **fails today** — V1 |
| 3 | Auto loan | Does the concept hold when utilization and purchases are meaningless? | R3 | **cannot pass** — V3: nothing marks those outputs meaningless for an instalment loan |
| 4 | Mortgage | Does it stay useful when the debt is long-term and barely transaction-driven? | R3 | **cannot pass** — V3 (escrow, scheduled vs minimum) |
| 5 | Missing credit limit | Does it say utilization cannot be calculated rather than guess? | honest-null | the combined line skips cards without limits and says *"across N cards with limits"* — partial; per-debt behaviour not yet designed |
| 6 | User-entered limit | Does it distinguish *"you told us $5,000"* from *"the statement says $5,000"*? | R2 | **cannot pass** — V2: no source on `credit_limit` |
| 7 | APR changed | Can it report the change without inventing why? | R2 + unknowns | change is detectable month-to-month in `DebtBalanceHistory.apr`; **its source is not** (V2) |
| 8 | Before You Buy | Can a proposed purchase borrow the debt's facts and simulate consequences without a second debt model? | lens, R5 | **fails today** — V5; and no engine input means "charge to this card" |
| 9 | Multiple cards | Can it explain each card without deciding which to use? | R1 | not measured; collides with 15 |
| 10 | Closed debt | Does the debt stay understandable after it is paid off or closed? | history | `is_active` / `paid_off_at` exist; whether history survives and renders is **not measured** |
| 11 | Conflicting evidence | When the facts disagree, does the teaching layer present the disagreement rather than resolve it? | R2 | **cannot pass** — V2 destroys the earlier value; see §6 |
| 12 | Nothing interesting | Does the teaching model know when there is nothing worth explaining? | teaching | not measured; pass condition in §7 |
| 13 | **Dependency** | If a payoff date is shown for one debt, can the user see the strategy, budget and other-debt context that produced it? | R4 | **fails today** — V4 |
| 14 | **Simulation boundary** | Is a proposed transaction explained from existing debt information, or does it need a new engine capability? | R5 | answered by measurement: **it needs one** — "$300 on Card A" has no engine input |
| 15 | **Comparison** | If the same purchase can be simulated on Card A and Card B, is presenting both an implicit recommendation? | R1 | **unruled** — Rob: *"we don't say which is best"* does not make a side-by-side neutral; the presentation itself can make the choice |

---

## 6. Test 11 — the disagreement state, defined

Rob's review defines it. The teaching model neither falls silent nor picks a value:

> *Groundwork has two different APR values for this debt. You entered 22.9%, while the statement
> reports 24.9%. Groundwork has not resolved which value should be used as the current APR.*

What that sentence requires, and does not yet exist:

1. **Both values survive.** Today the reconcile overwrites (V2). Nothing downstream can be built
   until neither write path destroys the other's figure.
2. **Each carries its source** — user-entered, statement (which statement, which period), or
   calculated.
3. **"Current APR" is a resolution, not a column.** Which value the engine uses while the
   disagreement stands is a decision that must itself be visible — *"projections below use 24.9%,
   the statement's figure"* — never a silent choice by write order. `VALUE_DISAGREEMENT_CASES.md`
   already records the failure shape: resolved by position.
4. **Consequences of the uncertainty may be explained where they matter** — e.g. how far the
   payoff projection moves between the two rates — and that explanation is a calculation under
   both stated assumptions, not a verdict.
5. **The disagreement is the teaching.** It is the most useful thing on the screen in that state,
   and the teaching layer should say so plainly rather than emit a generic warning.

---

## 7. Test 12 — silence is a valid outcome

Rob: *nothing worth teaching is also a valid outcome* — the guard against a teaching model that
behaves like a chatbot looking for an excuse to speak.

**Pass condition (proposed, for ruling):** when, for this debt, since the last time it was
explained —

- no figure changed,
- every displayed figure is established (observed, or user-supplied and labelled so),
- no disagreement stands,
- no calculation's inputs changed,
- and no event in its history is new —

the view shows the debt's facts **and no teaching paragraph**. Not a placeholder, not *"nothing
new to report"*, not a generic explanation of what APR means. The absence of prose is the correct
output, and a test should assert it.

*Open inside this:* "since the last time it was explained" needs a reference point. Recording
that the user **opened** the view to establish it would be an observation persisted from
behaviour — the no-silent-learning boundary applies. The reference point may have to be
data-side (the last statement, the last change to the record) rather than view-side. Flagged, not
decided.

---

## 8. Gates before implementation

Ordered as Rob reordered them: **the meaning of the debt model is ruled first**, because what
provenance a figure needs and what a payoff depends on both follow from what the debt *is*.

| Gate | Must be true before | Closes |
|---|---|---|
| **G0 — What the debt is** | anything else | What does the debt view's object refer to: the 2.0 obligation identity (`OBLIGATION_IDENTITY.md`), a 1.x `DebtAccount` row, or a view over both? Which debt types exist as types, and for each, which fields and calculations are meaningful, which are meaningless, and which are unknown-until-supplied? | 3, 4, and the shape of 6 / 7 |
| **G1 — Metric, not prescription** | the view shows utilization | V1 removed: the percentage kept, the target sentence and judgement thresholds gone; the calculation moved behind a named, tested contract per `CALCULATION_PLACEMENT.md`. Independent of the view — it is a violation shipped today. | 2 |
| **G2 — Provenance on debt figures** | the view shows any figure | Every figure the view can display — limit, rate, payment, balance, each history row — records its source; no write path destroys another source's value; "current" becomes a visible resolution. | 6, 7, 11 |
| **G3 — Payoff is scenario-scoped** | the view shows any payoff figure | A per-debt payoff figure exists only as *"under [strategy] and [$X/month], this debt is projected to clear in [month]"*; changing inputs visibly changes the scenario, never the debt. Consistent with whatever `RESERVE_PAYOFF_QUESTION.md` rules. | 13 |
| **G4 — The engine capability — RULED, authorised (§11)** | Before You Buy uses the debt | "A proposed charge to this specific debt" is either authorised as a named engine capability, with its own contract and tests, or refused — in which case Before You Buy states the cash reading it actually computes. V5 resolved either way: a committed decision never writes unknown principal or rate as zero. | 8, 14 |
| **G5 — Comparison — RULED, permitted as information (§11)** | any surface shows two debts' outcomes for one decision | Whether side-by-side outcomes may be shown at all, and if so in what form, ruled before anything renders them. | 9, 15 |
| **G7 — Payment-method terms (§12) — OPEN** | Before You Buy uses rewards or promotional financing | Whether a proposed purchase may carry payment-method terms (rewards, 0% APR, deferred interest) into the engine, stored as sourced facts or as unknown — never as zero; its own gate, not an extension of G4, which was ruled narrowly. | 8, 14, 15 |
| **G6 — The teaching contract** | the teaching layer speaks | The seven inputs as the only permitted inputs; §6's disagreement sentence; §7's silence condition as an asserted test. | 11, 12 |

**Not a gate, but a dependency:** tests 1 and 10 were not measured and should be, against the
shipped Debt page, before G0 is written — they describe what the view must *not* do and what it
must *keep*, and both are cheaper to measure than to argue.

---

## 9. For Rob — questions this document does not answer

Listed, not defaulted. Any of them may be reframed.

1. **G0.** Is "the debt" here the ruled obligation identity, or a 1.x surface over `DebtAccount`
   that 2.0 later re-points? The concept's own language (*obligation*, *terms*, *documented
   changes*) reads like the former; the code it would ship on is the latter.
2. **G1's timing.** V1 is a shipped prescription on the 1.x line. Fix it as its own small 1.x
   change now, or hold it for this pass?
3. ~~**G4.**~~ *Answered, §11: authorised, narrowly.*
4. ~~**G5.**~~ *Answered, §11: yes, as information, never ranked.*
5. **V5.** The committed-purchase debt with invented zeros is live data in any install that has
   used it. Does correcting it forward suffice, or do existing zero rows need a marked "unknown"
   state? — **STILL OPEN.** *Investigated 2026-09-24, read-only, counts only, on the one database
   available (installs cannot be counted — Groundwork does not call home):*
   - **Before You Buy legacy zeros: no migration population found in that database** (0 committed
     vehicle / purchase decisions, 0 rows matching the fingerprint — same name as a committed item,
     0 / 0 / 0%, minimum equal to its monthly cost). The V5 fix prevents new occurrences. The
     fingerprint makes such rows identifiable in any install that has them.
   - **Not settled by that:** of 17 debts, 5 carry 0%; 4 are closed at $0; **1 is active, unpaid,
     not a lease, at 0%**, and the database cannot establish whether that is a legitimate rate or
     a blank collapsed to zero (V6). The question stays open pending that record's meaning.

---

## 10. Not decided here

No schema. No field. No provenance model for debt figures beyond the requirement that one exist.
No change to `consequence.py`, `app.js`, `server.py` or any Before You Buy flow. No view design,
no navigation design, no teaching copy beyond the two sentences quoted from Rob's review. V1–V5
are recorded, not repaired.

---

## 11. Rulings — Rob, 2026-09-24. G4 and G5, recorded narrowly.

Made against the concept layout, which added Before You Buy to every open debt's page with a
needed purchase ($869.99 dishwasher on the Capital One card; $640 brakes on the auto loan) and
a table comparing each way to pay it. Rob's reasoning for ruling now: *these aren't merely UI
preferences anymore; they are semantic decisions about what the surface is allowed to do. The
layout can evolve; the permissions are now clear.* Every other gate stays open.

### G4 — specific-debt purchase simulation: AUTHORISED

> **Before You Buy may model a proposed expense as being charged to a specific debt instrument,
> rather than treating the expense only as cash.**

- This is an **engine capability the current implementation does not have** (§4: `one_time_cost`
  is money that never reaches a debt). The ruling authorises the capability to be investigated
  and built. **It does not authorise the rest of the Before You Buy engine to be redesigned.**
- **For loans:** the proposed expense is **not** added to the loan balance. The loan's scheduled
  payment stays unchanged. The simulation compares the available payment sources for the
  expense. Stated because otherwise *"Before You Buy on a mortgage"* could be read as the repair
  becoming mortgage debt.
- V5 is untouched by this ruling: a committed decision still may not write an unknown principal
  or rate as zero (§8, G4's second half, still open).

### G5 — debt comparison: PERMITTED AS INFORMATION

> **Before You Buy may present the calculated consequences of the same expense under multiple
> available payment methods / debt instruments. The results are displayed without sorting,
> highlighting, ranking, recommending, or selecting a preferred payment method.**

- **Presentation rule:** the Debt page's existing order. Cash, where offered, follows the debts.
- **The principle:** *comparison is information; ranking is a decision.* Groundwork can show that
  one path produces about $2,240 and another about $2,675. It does not say which the user should
  choose.
- Test 15 is answered by this ruling; test 9 (explain each card without deciding which to use)
  now has its pass condition.

### R6 — the cost of a financed purchase is a scenario, not a number

Added to the rules at Rob's direction, because the layout's example exposed it: **when financing
is involved, "the cost of the purchase" is not one universal number.** Each figure belongs to a
named scenario with stated assumptions, and is shown as such — never as *the dishwasher costs
$2,675*.

For the $869.99 on the concept layout's figures (illustrative, from a scratch script, not the
engine):

| Scenario | Total cost, under stated assumptions |
|---|---|
| Capital One, minimum payments only | ≈ $2,675 |
| Harbor Freedom, minimum payments only | ≈ $2,240 |
| Capital One, current payoff plan | ≈ $1,120 ($869.99 + ≈ $287 added card interest) |
| Harbor Freedom, current payoff plan | ≈ $1,067 ($869.99 + ≈ $197) |
| Cash from the payoff surplus | $869.99 + ≈ $205 of added card interest from the cash-flow change |

*Figure note:* Rob's review gave ≈ $1,067 as "the current payoff-plan scenario"; that is the
**Harbor** row. The Capital One plan-scenario figure is ≈ $1,120. Recorded as corrected.

Two consequences, both from R4:

1. **The plan-scenario figure is a household figure.** Its added interest is measured across every
   card in the plan, because the purchase delays whatever the plan pays next. It is not interest
   charged on this purchase alone, and it is labelled as such.
2. **The scenario gap is itself worth showing.** On minimums, the choice of instrument moves the
   cost by about $500; under the payoff plan, by about $60. That difference is why the section
   sits near the top of the debt surface: it connects an ordinary spending decision to the debt
   mechanics the user is already looking at, and it matters most to the user paying minimums.

### Not ruled here

G0, G1, G2, G3, G6 remain open, as do §9 questions 1, 2 and 5. The minimum-payment rule the
layout estimates (1% of balance plus interest, $25 floor) is an **unknown** per card; how
Groundwork obtains or labels it is part of G2, not decided by G4. No code.

---

## 12. Teach the question, not just the answer — the payment-terms investigation

> Status: **The principle AGREED (Rob, 2026-09-24). Everything else in this section is an open
> design question. G7 opened, not ruled. No code.**

Opened from a Before You Buy extension: payment methods carry terms (cash back, points,
promotional financing) that change what a purchase does, and a store's "90 days same as cash"
is not the same thing as a 0% APR.

### The principle (agreed)

**When a term is unknown, the unknown is the teaching moment, not a dead end.** A first read
treated a missing term as *"cannot be calculated — enter it"*. Rob's correction: the teaching
model should teach what the term is, how it can go wrong, and **what the user should ask before
signing** — so that next time they ask it without Groundwork.

**The goal, in Rob's words: users not needing Groundwork to make good financial decisions.** The
success test for any teaching here: *would the user ask this question next time without the app?*
A lesson only reachable by opening Groundwork has recorded a decision, not taught one.

**The line it keeps (also agreed): the mechanism is taught conditionally, never asserted about
this offer.**

- *"**If** this is deferred interest, a missed deadline can mean interest on the full original
  $869.99 from the purchase date"* — teaching.
- *"This offer will charge you interest on $869.99"* — an assertion Groundwork cannot make until
  the user has confirmed the terms. Unknowns stay unknown.

And it stays teaching rather than advice: *"deferred interest works like this; here is what to
check"* is in scope; *"avoid deferred-interest offers"* is a verdict and is not. The user can
learn all of it, ask, and still take the deal.

### What the user learns to ask — the "90 days same as cash" example

1. **Is this "no interest if paid in full" (deferred interest), or a true 0% APR?** They sound
   alike and are not.
2. **If it is not paid in full in time, is interest charged back to the purchase date on the
   full original amount** — even if most of it has been paid?
3. **What APR applies after the promotion?** Store cards often run near 30%.
4. **What exactly is financed?** Sales tax, delivery and installation may or may not be included.
5. **When exactly does it end?** A statement date, not "90 days from today".
6. **Will the minimum payment clear it in time?** Usually not.

Groundwork's arithmetic serves the teaching: *"if this is deferred interest, clearing it in time
takes about $290 a month; your plan's extra is $313"* — and what the rest of the plan does while
that is diverted. That connection to the existing payoff plan is the most valuable single piece.

### Open design questions (not ruled)

- **Framing.** *"How could you pay for this?"*, never *"Which card should I use?"* — the second
  makes Groundwork the chooser before the page renders.
- **Terms as sourced facts.** A reward, a promotional APR, a deferred-interest period are stored
  as *user-entered* (with *"verify the offer terms"* shown back) or as **unknown** — never as `0`.
  V6 is the reason: a zero written for "don't know" cannot later be told apart from a real zero.
- **Proposed rule — a reward is never shown alone.** Cash back is the lever issuers use to move
  purchases onto high-APR cards, so a bare *"$40 cash back"* beside *"$15"* leans without ranking.
  Proposed: a reward always appears against the interest cost in the same scenario (on minimums,
  $40 back against ≈ $2,075 interest; under the plan, against ≈ $287). G5 permits comparison; this
  closes a way to make comparison lean while keeping G5's letter.
- **Two promotions, never collapsed.** A true 0% promotional APR and deferred interest have
  different consequences when the balance is not cleared.
- **Deferred interest needs more than a duration:** the post-promotion APR; whether the promotion
  sits on its own account or on a card with other balances (payment allocation across balances
  decides whether the promotional balance clears — a first version may model only a stand-alone
  promotion, and say so); billing cycles rather than months, so the required payment is "about".
- **Reward scope:** all purchases / this merchant / this category covers most; caps and rotating
  categories go to "Other" with the user's note shown back, rather than modelled.
- **Reward timing:** a reward is not subtracted from the balance at purchase; it applies as and
  when the user says it posts (statement credit, deposit, points).

### Cases, each with what the user should learn to ask

| Case | What Groundwork shows | What the user learns to ask |
|---|---|---|
| Reward, terms known | the reward against the interest cost, in each scenario | Does the reward outlast the interest if I carry this balance? |
| True 0% promotion | cost inside the promotion; the rate and balance after it | What rate applies after, and on what balance? |
| Deferred interest, cleared in time | the required monthly amount, against the plan's extra | What must I pay each month to clear it, and what does that take from my plan? |
| Deferred interest, missed | the conditional consequence, labelled *if* | Is interest charged from the purchase date on the full amount? |
| Term unknown | the mechanism taught conditionally; no number invented | Which kind of offer is this, and where is it written down? |
| Financed amount unclear | the price as entered; the question raised | Are tax, delivery and installation in the financed amount? |

### Not decided here

G7 is open. No field, no schema, no engine input, no copy beyond the examples above.
