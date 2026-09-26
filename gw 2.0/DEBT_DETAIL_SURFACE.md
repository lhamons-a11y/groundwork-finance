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
> found investigating the fifth. V1, V2, V3, V5 and V6 are fixed on 1.x; V4 and V9 are open. A debt view built
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

> **FIXED on 1.x, 2026-09-25 (`1b7abb9` on `lts/1.x`, merged into master) — Rob chose all three
> layers.** Measured first: the reconcile screen does show the statement's APR before the import
> is confirmed, so the replacement was not silent at that moment; but (1) **a real defect** — after
> a reconcile the page updated the card's balance in memory and not its APR or minimum, and the
> Debt page save resends every field on every edit, so the next edit to that card wrote the old
> figures back over the statement's until a reload; (2) the toast never said what was replaced;
> (3) no source was recorded — four writers (typed, statement, the implied-APR alert, the
> estimator) shared one column. Now the page takes up the statement's figures; the toast says
> *"From this statement: APR 22.9% (you entered) → 24.9%; minimum $99.18 (you entered) →
> $117.00"*; and new nullable `interest_rate_source` / `minimum_payment_source` columns record
> `user` / `statement` / `calculated`, shown under the fields (*"from your Aug 28, 2026
> statement"*). The source moves only when the value changes, a client cannot claim `statement`,
> and existing rows show no source rather than a guessed one. Gate section `s47` (14 checks,
> the migration exercised against an old-shaped table, a mutation caught). **Still open:** the
> credit limit and each balance-history row carry no source (the history's `statement_period_end`
> remains the only trace), and a statement that *disagrees* with a typed APR still replaces it
> rather than presenting both (§6's disagreement state, G2).
>
> **Correction, 2026-09-26: V2 as first pushed was a release blocker.** `1b7abb9` added the two
> source columns to `migrate.py`'s column list but did not bump `SCHEMA_VERSION`, and
> `run_migration_if_needed` skips every step when a database already stores the current version —
> which every 1.1 install does. On an upgraded database the columns were never added and
> `/api/settings/bootstrap` returned 500 (*"no such column: debt_accounts.interest_rate_source"*).
> Fresh databases were unaffected, and no release tag contains V2. `s47` missed it because it
> called the column helper directly, past the version gate. Found and fixed by the bank-window
> session (`125b020` on `lts/1.x`, merged into master): `SCHEMA_VERSION` bumped on each line, a
> `SCHEMA_SPEC_SHA256` fingerprint pinned beside it, and gate section `s51_schema_version_pin`,
> which fails any change to `migrate.py` until the version is bumped and the pin updated;
> measured, a v1.1.0 database boots 500 before the fix and 200 after.

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

> **FIXED on 1.x, 2026-09-26 (`95a6907` on `lts/1.x`, merged into master) — Rob chose a Mortgage
> type with calculated principal & interest.** Measured first: 1.x had **no mortgage debt type**
> (a mortgage lived in Net Worth as a balance, in the budget as *Rent / Mortgage*, and in the
> extra-payment tool), so V3 applied only to a mortgage added as a *Loan*; and the extra-payment
> tool had already decided **not to ask for escrow** — it calculates principal & interest from
> balance, APR and months remaining (exact for a fixed-rate, fully amortizing loan). The fix
> follows it: *Mortgage* joins the types, with a balance, APR and maturity date its principal &
> interest is calculated, every payoff projection uses that, and **the payoff budget leaves out
> each mortgage's escrow share** (left in, the engine would hand it to other debts as "extra").
> Budgets and debt-to-income keep the whole payment. The row explains the split (*"about
> $1,073.21 is principal & interest ... the other $162.19 likely covers escrow, PMI or fees; it
> doesn't reduce what you owe"*); without a maturity date the whole payment is used and the page
> says so. Gate section `s46` (14 checks — a 25-year mortgage at its calculated P&I pays off at
> its maturity date where the whole payment projected it years early; a mutation caught).
> **Not changed:** the Budget page's live estimator (typed values, no stored card).

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

### V9 — Net Worth can count a mortgage twice — OPEN

*Found 2026-09-26 while fixing V3; recorded, not fixed.* Net Worth's liabilities are
`nw.mortgage + totalDebt`: the mortgage balance typed on the Net Worth page, plus every debt on
the Debt page. A mortgage entered in both places is counted twice. V3 makes that more likely,
since *Mortgage* is now a debt type. Which record should hold the mortgage — or how the two
should be reconciled — is a question for Rob, not a guess.

### V6 — the Debt page collapses a blank into zero (R2) — FIXED on 1.x

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

**Status:** FIXED on 1.x, 2026-09-25 (`457d6d2` on `lts/1.x`, merged into master) — Rob chose
*store and show unknown*. A blank APR, balance or minimum is stored as NULL; a typed 0 stays 0; a
caller that sends no figures keeps the old default of 0. The client sends blanks as null and the
startup load keeps a stored null blank, so a re-save cannot collapse it again. An unknown balance
plus a ledger entry stays unknown; a bank-reported balance fills one in. The monthly history
snapshot records an unknown APR as unknown. **Calculations are unchanged** — a missing APR is
still simulated as 0% and a missing minimum estimated — **but every projection that used one
says so**: the collapsed debt row (*"0% APR assumed"*, *"APR not entered"*), the Debt page
summary, the dashboard's debt-free date, and the AI payoff narration. The columns default to
0.0 and SQLAlchemy applies that default even to an explicit None at insert, so create sets
blanks back to NULL after the insert. Gate section `s49` (12 checks, a mutation caught).
**No migration:** zeros stored before the fix stay ambiguous, so §9 question 5 stays open.

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

**Clarified — Rob, 2026-09-24: Before You Buy appears only on revolving credit.** Credit cards,
store cards and **home equity lines of credit** carry it: a purchase can be charged or drawn on
them. A HELOC is different from a mortgage because it is a line of credit, using the home as
collateral. Before You Buy does **not** appear on the page of an instalment loan or a mortgage:
nothing can be charged to either. The loan clause above therefore describes how a loan figures in
a Before You Buy opened from elsewhere (its payment unchanged, the expense landing on a card, a
line or cash), not a section on the loan's own page. On the concept layout, Before You Buy sits
behind its own button on each revolving-credit page, closed until the user selects it, as the
ledger's Reconcile panel is.

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

**G5 language — Rob, 2026-09-24.** The boundary is semantic, not a list of forbidden adjectives:

| Statement | Kind | Status |
|---|---|---|
| *"This card has an APR of 18.9%."* | fact | permitted |
| *"This card's APR is 6 points lower than the other card's."* | factual comparison | permitted |
| *"This card has the lowest APR."* | factual superlative | **OPEN** — proposed prohibition |
| *"This card is the better choice."* | decision | **prohibited** |

**Prohibited — all remain prohibited, in any wording:**

- *"Card A is the better option."*
- *"Given your situation, Card A makes more sense."*
- *"I'd go with Card A."*
- *"The numbers strongly favor Card A."*
- *"Card A is the obvious choice."*
- *"You'd be better off using Card A."*
- *"If I were you, I'd use Card A."*
- *"Based on these factors, Card A appears preferable."*
- *"The financially optimal choice is Card A."*
- Showing a "recommended" or "preferred" path without explicitly saying so.
- Sorting, highlighting, scoring, or otherwise visually designating one option as the choice.
- **Indirect recommendation:** the model must not turn factual comparisons into a choice through
  implication — by selection, emphasis, ordering or framing — even when every sentence it says is
  individually true.

**Factual superlatives — OPEN.** Whether statements such as *"Harbor Freedom has the lowest APR
among these options"* are permissible remains OPEN. The current proposed rule is to prohibit
factual superlatives that single out one option, because the same information can be presented
independently for each option without directing the user's choice. (If every option already
shows its APR, *"lowest APR"* adds little information while directing attention to one option.)

*Applied on the concept layout:* the HELOC board's closing sentence (*"The line has the lowest rate
here, and paying only its minimum costs less than either card's…"*) used two superlatives and was
reworded to per-option facts.

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

### Case: a store's own offer — discount, financing, or both (recorded 2026-09-24)

Raised by Rob: some stores offer a discount on their card (e.g. 5% off), a promotional financing
period (e.g. "90 days same as cash"), or a choice between the two. The store's offer is one more
way to pay, so it is asked about like any other — the store is never known to Groundwork by name,
and its terms are user-entered facts or unknown (store terms change). **Recorded as a case, not a
surface: nothing is added to the Before You Buy board until the semantics below are settled.**

**Five distinctions, kept apart:**

1. **Store discount** — e.g. 5% off. A benefit, so never shown without its cost in the same
   scenario (the §12 pairing rule).
2. **Store financing** — deferred interest ("same as cash", "no interest if paid in full") or a
   true 0% APR; never collapsed, as above.
3. **Both available** — Groundwork **asks whether they can actually be combined** rather than
   assuming. At many stores it is one or the other, chosen at checkout.
4. **Credit application involved** — if the offer requires opening the store account, that is
   surfaced **as a fact**: taking it means applying for credit and opening a new account.
5. **Terms unknown** — teach the user what to ask rather than calculating from assumptions.

**What the user learns to ask:**

- Is it the discount *or* the financing, or can I have both?
- Does taking it mean opening a new store card?
- What is the card's rate if the balance is not paid in full?
- Does the discount apply to delivery, installation and tax?
- If it is financing: every question in the "90 days same as cash" list above.

**The "suggestion" is a set of conditional paths — consequence teaching, no path selected.**
On the concept figures (a $869.99 dishwasher; a store-card rate of 29.99% and an estimated
minimum rule, both standing in for user-entered terms):

- *If you take the 5% discount, the purchase is **$826.49**.*
- *If you then pay it in full by the first due date, the purchase costs **$826.49**.*
- *If you instead make only minimum payments, the modelled total is approximately **$1,821**
  under these terms* — about $994 of interest over about 6½ years.
- *If you take a 6-month deferred-interest period instead, about **$145.00** a month clears it
  in time; if the deadline is missed, interest back-dated to the purchase could be **up to about
  $150** under these terms.*

Groundwork states each path; it does not say which to take.

**Cash reserves — dependent on `RESERVE_PAYOFF_QUESTION.md`.** Until that question is ruled,
Groundwork **may identify available reserves and show the consequence of using them** (*"paying
this from savings leaves the emergency fund $826.49 lower"*), but **must not establish that
reserves are available for this purpose.** Teaching the question stays in scope either way: *if
you use the reserve, what is left for the next emergency?*

**The budget action belongs later, and only as an explicit confirmation.** The eventual behaviour
can be *"Add $826.49 to next month's budget?"* — showing what it adds and where, acting only on
the user's yes — never a silent change to the budget because a store offer was selected (the
no-silent-writing rule).

**Sequence (Rob, 2026-09-24):** this §12 documentation → resolve reserve semantics
(`RESERVE_PAYOFF_QUESTION.md`) → resolve store-offer semantics → design the Before You Buy surface
→ then consider whether and what G7 authorises. No board changes until then.

### Not decided here

G7 is open. No field, no schema, no engine input, no copy beyond the examples above.

---

## 13. Closing a card, and the closed-accounts history

> Status: **Design case, recorded 2026-09-24 at Rob's direction. Nothing ruled beyond what is
> marked as Rob's. No code, no surface change, no migration.**

Rob: instead of *removing* a debt or a card, the user **closes** it. Closing asks why. Closed
accounts stay browsable — with their credit limits, terms, history and the user's own reasons —
so that *"I had that card before; I don't remember why I closed it"* has an answer. And when the
card comes back as an offer, the teaching model helps the user see what the card is actually
offering, **in the words of the document the issuer sent** — *"not stating that they should or
shouldn't, but the actual truth of this card."*

### What 1.x does today (measured 2026-09-24)

- **"Remove this card?"** (`confirmRemoveCard`) and **"Archive"** on a paid-off card both call
  `removeCard`, which calls `DELETE /api/debt/<id>`. The server's `delete_debt` **does not
  delete**: it sets `is_active = False`. The record — balance history, rate, limit, ledger — is
  kept and simply hidden. So the closed-accounts history this section asks for already exists in
  every install's data; what is missing is the reason, the distinction between endings, and a way
  to look back.
- **V7 — the Remove dialog implied erasure. FIXED on 1.x, 2026-09-24 (`5eae28e` on `lts/1.x`,
  merged into master).** *Corrected from the first record,* which called *"This cannot be
  undone"* false: measured, 1.x has no way to bring a removed debt back (bootstrap loads only
  active debts and nothing sets one active again), so from the user's side it could not be
  undone. What misled was the implication that the card was gone: its balance history is kept
  and still counts wherever past debt is summed — `revolving_series` (the *"You have been here
  before"* comparison) and the trophies read every debt's history, active or not. The dialog now
  reads: *"It will leave your Debt page, and Groundwork has no way to bring it back. Its past
  balances are kept and still count in your debt history."*
- **V8 — a card added by mistake keeps counting after removal. FIXED on 1.x, 2026-09-25
  (`aaa05b3` on `lts/1.x`, merged into master).** Removed debts still feed those sums — right for
  a card that existed (the debt-cycle comparison needs archived cards' past peaks), wrong for a
  duplicate or a typo. 1.x cannot tell the two apart, so **the user says which** (Rob chose real
  deletion): the Remove dialog carries a checkbox, *"It was added by mistake. Delete it and its
  history instead, so it stops counting. A backup of your data is saved first."* Unticked,
  removal is unchanged. Ticked, `DELETE /api/debt/<id>/permanent` checks the debt exists, takes a
  full backup server-side (nothing is deleted if that fails), then deletes the debt, its balance
  history, ledger entries and their checking links, and recurring payments; historian entries are
  kept and unlinked (SQLite reuses the highest id); the companion account and its bank
  transactions are left alone. Gate section `s48` (13 checks, a mutation caught). This is the
  *added by mistake* ending below, built early for 1.x; *closed* versus *paid off* is still
  undistinguished there.

### Three different endings, never one button

| Ending | What it means | What happens to the record |
|---|---|---|
| **Closed** | the account itself ended — by the user or the issuer | kept; moves to Closed accounts with its history and the user's reasons |
| **Paid off** | the balance is $0 and the account is **still open** | stays an open account; its limit still counts toward available credit |
| **Added by mistake** | a duplicate or a typo — the account never existed as entered | real deletion is right, with a confirmation that says so truthfully |

*Correction to the concept layout:* its closed Discover board shows *"Paid off Mar 2025"* under
*Closed* — the conflation this table exists to prevent. Paid off and closed are separate facts
with separate dates.

### Closing asks why — optional, and never inferred

At the moment of closing — the only moment the answer can be recorded honestly — Groundwork asks,
for example:

- Why are you closing it? *(annual fee · rate too high · don't use it · too tempting to use ·
  switching to another card · the issuer closed it · other · prefer not to say)*
- Anything you'd want to remember about it? *(free text)*

Every answer is optional; **"prefer not to say" is a complete answer**. Answers are stored as
**what the user said, on that date** — provenance like any user-entered figure. Groundwork never
works a reason out for itself from behaviour (the no-silent-learning rule).

**The consequences of closing are taught as questions, not warnings.** Conditionally and with the
arithmetic, e.g. *"closing this removes a $5,000 limit; your remaining cards' utilization would
go from 22% to 34%"* — and what a closed account can mean for the age of the user's credit
history, taught as something to ask about rather than asserted. Groundwork never says *"don't
close it."*

### Closed accounts — a page in Settings (Rob)

- A **Closed accounts** page in **Settings**, reached by its own button there.
- Each closed account is listed with its name, type, when it closed, its last credit limit and
  rate, and — **if Groundwork has them** — the user's recorded reasons.
- **Each name is a link to that account's history page** — the same kind of page as the open debt
  detail (the concept layout's closed-debt board is the model): the limit, the rates and their
  changes, the balance history, what it cost in recorded interest, missing months shown as
  *unknown, not zero*, and the user's own words about why it closed.
- Whether the Debt page keeps a small link to it as well is **not decided here**.

### When the card comes back — the offer, in the issuer's words

The user can **upload the document the card company sent** — an offer, or the cardholder
agreement. Card offers must carry a standard rates-and-fees table, so there is a real source to
quote. The teaching model then tells the user **what the document actually says**:

- every statement **cites where it is in the document**; anything the document does not state is
  shown as **not stated** — never filled in from what cards usually do;
- **set beside the user's own record**, e.g. *"You closed this card in March 2025 and said:
  'annual fee.' This offer's rates-and-fees table lists an annual fee of $95."* — the truth of the
  card, with nobody choosing for the user;
- the teaching asks what a teacher would: *what makes you want this card again? what are you being
  promised, and where in the document is it?* — and separates the promise in the marketing from
  the term in the agreement.

It never says the user should or shouldn't take the card.

**Two constraints on that:**

1. **Grounded in the document or it does not happen.** Summarising a long legal document with a
   small local model is the real risk. The existing statement reader checks every figure against
   the source text before use (R8-style provenance); an offer reader needs the same — and
   `SAFETY_PROVISIONS_INVENTORY.md` S13 applies: a check that a figure is *present* is not a check
   of what it is *attached to*.
2. **A reopened card is usually a new account**, not the old one back. Linking an offer or a new
   account to the closed record is an identity question (the kind `OBLIGATION_IDENTITY.md`
   handles); the link is **the user's to confirm**, never made silently.

### Test 10, extended

| # | Case | Question |
|---|---|---|
| 10a | Paid off, still open | Does Groundwork keep a $0 card as an open account, not a closed one? |
| 10b | Closed with a reason | Is the reason shown later as the user's words, dated, and nothing more? |
| 10c | Closed, no reason given | Does the history show no reason, rather than an inferred one? |
| 10d | Added by mistake | Does deletion say truthfully what it does, distinct from closing? |
| 10e | Offer uploaded | Is every claim about the offer cited to the document, and every gap shown as *not stated*? |
| 10f | Offer vs. closing reason | Does Groundwork set the two side by side without recommending? |

### Not decided here

No schema for endings or reasons, no Settings page, no upload path, no reader for offer documents,
no change to `removeCard` or `delete_debt`, and no change to the concept layout's boards. V7 is
fixed on 1.x (wording only); V8 is fixed on 1.x (the *added by mistake* delete).
