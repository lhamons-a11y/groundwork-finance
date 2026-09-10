# Fifteen gaps, triaged against what exists

**Rob's second review, 2026-09-07 — checked rather than accepted or argued**

> Same discipline as `HEALTHCARE_CRITIQUE_SURVIVAL.md`: each gap is checked against shipped
> code, and marked **ADDRESSED**, **PARTIAL** or **NEW** with the mechanism cited or its absence
> admitted. The review's own framing is right — these are **gaps, not flaws**. Nothing below
> contradicts the design; several things below are missing from it.
>
> **The standing caveat:** all five `core/` modules are pure and have no callers. Every
> "addressed" is addressed *in isolation*.

---

## NEW — nothing in the repository does this

### 1. Two valid histories, one present state — **the sharpest new gap**

```text
EOB $400 → corrected to $275          versus          EOB $400 → deleted → EOB B $275
```

The lifecycle fixture asserts **arrival-order independence** — the same facts in any order
produce the same state — which is a different claim. It does **not** assert anything about two
*different* histories converging, and the model would represent them differently: one is an
obligation version chain, the other is a deletion plus a new obligation.

**Unanswered, and the review is right that it must be answered explicitly:** are those
semantically identical? If yes, normalization rules are needed. If no, the distinction has to
survive every read path. Today it survives by accident rather than by rule.

> **CLOSED — retraction and replacement in `core/allocation.py`.** 14 assertions
> (`tests/test_convergent_history_fixture.py`), 9 of 9 mutations
> (`smoke_sections/s97_convergent_history.py`). **No history-equivalence abstraction was
> built** — the fixture was written first, as the review asked, and it exposed the answer
> rather than requiring one to be invented.
>
> **What it exposed immediately: history B was not representable.** There was no way to void an
> obligation — `deletion_modes()` covers allocations, not the expense — so the model could
> express a correction and could not express a retraction. That was a decision being made
> silently, which is exactly what the fixture existed to surface.
>
> **The answer: they are not equivalent, and the balance is the only thing they share.**
>
> | | | |
> |---|---|---|
> | current balance | **identical** | both owe $275 |
> | obligation identity | **differs** | one restated, two with one retracted |
> | provenance | **differs** | `corrected` versus `replacement` versus `retracted` |
> | what a payment attaches to | **differs** | and this is where the money goes wrong |
> | derived facts | **cite different sources** | a retracted obligation is never totalled |
>
> **Where it actually matters** is not taxonomy. A payment attached to the retracted bill does
> **not** fund its replacement — collapsing them would make $275 look satisfied by money
> attached to an obligation nobody owes. That leaves money against a zero obligation, showing
> as **negative unallocated**, and the model reports it rather than netting it away: it is the
> user's money sitting against a bill that no longer exists, which is precisely the state they
> most need to be asked about.
>
> A retraction is **a state, not a removal** — the review had already settled that hard deletion
> is prohibited once financial relationships exist — so the record, its reason, its date and
> everything attached to it survive. And `histories_equivalent` is deliberately strict: agreeing
> on the number is not being the same history, and a caller wanting *do these owe the same*
> must ask that instead.

### 4. Inference amplification — **the material exists, the invariant does not**

> *A derived fact may not acquire greater certainty merely because it participates in additional
> derivations.*

What a `DerivedFact` carries today (`core/classification.py`): `domain`, `manufactured`, and
`sources` — the contributing classifications. So:

- **Better than the review assumes:** `manufactured` survives the hop. A figure derived from
  inferred classifications is still marked as manufactured, and `sources` keeps the chain
  walkable, so the information needed to enforce the invariant is present.
- **Exactly as bad as the review fears in one respect:** the derived fact does **not** carry the
  strength of its weakest link. A figure resting on one `single_weak_signal` is indistinguishable
  from one resting on `corroborated` evidence, except by walking `sources` — and nothing requires
  anyone to walk it. `DerivedFact.value` is a plain float.

**There is no rule anywhere that certainty cannot rise along a chain.** The invariant should be
written and asserted; the data to enforce it is already there, which makes this cheap to close
and dangerous to leave.

> **CLOSED — `core/classification.py`'s evidence-strength layer.** 22 assertions
> (`tests/test_evidence_strength_fixture.py`), 7 of 7 mutations
> (`smoke_sections/s95_evidence_strength.py`). The rule: *a derived fact may not possess
> greater evidentiary strength than its weakest material source*, over a lattice rather than a
> float, because a float invites a threshold and a threshold is an invented policy.
>
> **The half that makes it an invariant rather than infrastructure is the consumer boundary.**
> `consume()` is the only way to take a value; every consumer declares the strength it
> requires; **a consumer absent from the table is refused outright**. So adding a surface means
> stating what it needs, and forgetting to state it fails closed. Walkable provenance became
> enforced provenance, which was Rob's distinction and is the whole point.
>
> Two things the fixture forced that the design had not anticipated. At the floor,
> `contradicted` and `not_evaluated` tie on rank, and the tie must resolve to **contradicted** —
> *we looked and found against it* is the finding, and reporting *we never looked* discards the
> only thing established. And a **source contributing nothing cannot weaken what it did not
> build**, so the minimum is over *material* sources.
>
> **And a correction of my own, worth keeping:** the first version of case 7 was named
> *"invalidating the source invalidates what was derived from it"* and tested no such thing — it
> built a new fact from the weakened source. **Meaning-named and value-asserting, committed one
> commit after identifying that exact defect.** What is actually true is better: classifications
> are immutable, so a derived fact is a statement about its sources *as they stood*, and the
> caller re-derives for a current view. That is gap 2's historical-truth invariant showing up
> concretely rather than a propagation failure.

### 6. Compound partial payments — no single invariant

The $4,000 obligation with `175 · 175 · 500 · −50 · 300` is not tested. Reversal is
(`57b6154`), and progress-as-dollars is settled, but **the invariant that paid / remaining /
scheduled / ahead / overdue cannot contradict one another does not exist.** That is a fixture
waiting to be written, and it is the kind that finds things.

> **CLOSED — `core/payment_plan.py`.** 24 assertions
> (`tests/test_payment_state_fixture.py`), 9 of 9 mutations
> (`smoke_sections/s99_payment_state.py`). The whole state vector is asserted **at every step**,
> not only at the end, so an implementation cannot be wrong in the middle and right by the time
> anyone looks.
>
> **The boundary question, answered:** the invariant is enforced at the ledger, not
> reconstructed by consumers. `payment_state()` computes all five dimensions **together in one
> pass**, and there is deliberately **no `paid()` or `ahead()` accessor** — asserted, so a
> future convenience method cannot reintroduce the drift. This is *not* another
> material-exists-invariant-doesn't situation.
>
> **Three operations a signed number would collapse:** a *payment*; a *reversal*, which **names
> the payment it reverses and may not exceed it**; and an *adjustment*, which changes what is
> **owed** rather than what was **paid**. The adversarial −$700 against $850 paid across three
> payments is **refused as a reversal** — no payment is that size, so the ledger would lose
> which payment stopped being true — and accepted as an adjustment only when the caller says
> that is what it is. The same $700 gives `remaining` of $2,450 as an adjustment and $3,850 as
> a reversal: the four readings are not interchangeable, and arithmetic does not choose.
>
> **Ahead and overdue are one distance under two names**, never a signed number — *"you are
> −$525 ahead"* hands the user arithmetic instead of a sentence.
>
> **The mutation that found something:** *the coherence check always reports clean* went
> undetected, because the fixture only ever pointed it at a coherent plan — the projection is
> coherent by construction, so nothing could tell a working checker from a stub. `incoherences()`
> now accepts a `state` to verify, which is both what makes it testable and what makes it
> useful: a figure arriving from a cache, an API response or a migration can be asked whether
> it still agrees with the ledger.
>
> **Gap 8 is untouched and honestly so.** The schedule is a caller-supplied input; versioning an
> agreement needs a domain object that does not exist, and inventing one here would have hidden
> the gap rather than closed it.

### 8. Payment agreements need versioning

`24 × $175` becoming `18 × $233.33` is not representable. There is **no payment-plan entity at
all** — versioned or otherwise. The review's reasoning holds: recalculating against the current
agreement rewrites history, freezing it makes current adherence wrong, so the agreement itself
needs versions exactly as the obligation does.

> **INSPECTED, not designed — `gw 2.0/PAYMENT_AGREEMENT_INSPECTION.md`** (2026-09-09).
>
> **Why no fixture can close it:** gaps 4, 1 and 6 all had the data and lacked the invariant.
> Gap 8 has no data — no agreement row exists anywhere, and gap 6 deliberately took the schedule
> as caller-supplied scalars so the entity would not get invented by accident. Favourable
> timing, though: `core/payment_plan.py` has **zero consumers** outside its own fixture and s99,
> so the blast radius is zero today and will not be after wiring.
>
> **The mechanics are already solved three times** (`HealthPlanTermVersion`,
> `ExpenseObligationVersion`, `ExpenseFundingAllocation`) and should be copied, not re-derived.
> `RecurringDebtPayment` is the trap — a *mutable* pattern whose `is_active` toggle destroys
> prior terms.
>
> **What is actually new:** a plan term version answers a *point* question; a schedule answers a
> *span* one. `expected_by_now` becomes a piecewise fold with per-version caps rather than
> `min(count, months)` — so `expected_by_now`, `ahead` and `overdue` all change and `paid` and
> `remaining` do not.
>
> **And the change-kind decides whether the past is re-judged.** Renegotiation, correction and
> restructure produce three different `expected_by_now` values for the same past date, and
> arithmetic cannot recover which occurred — **gap 6's lesson at the entity level.**
> `HealthPlanOperation.kind` is the precedent and is one value short.
>
> **The hardest constraint** is §7.7's: a 0% provider plan and a deferred-interest promo are
> byte-identical as a schedule and catastrophically different in consequence, so instrument kind
> must be **required and not inferable**. Four decisions are Rob's — restructure semantics,
> where promo balances live, expense↔agreement cardinality, and whether the entity is
> healthcare-scoped or general. **No schema until the first two have answers.**
>
> **8.1 and 8.2 posed, not answered — `gw 2.0/PAYMENT_AGREEMENT_DECISIONS.md`** (2026-09-09). Both
> are stated as the semantic question underneath the table question, because *"does a restructure
> create a new version?"* lets the table decide the meaning and *"is the pre-restructure schedule
> still historically authoritative for dates before it?"* does not. Three positions on 8.1, and
> the arrears question underneath it recorded as a **separate fact that must not be collapsed into
> it**. 8.2 turns on whether an agreement can change instrument kind; if it cannot, the
> promotional facts need their own version chain rather than nullable columns on a schedule row.
> Two things settled: **instrument kind is explicit source data, never inferred from schedule
> shape** — #15's *agreement ≠ evidence* at the schema level — and the **zero-consumer state is
> preserved on purpose** while the decisions are open.
>
> **Status: design investigation active, no implementation.** Two invariants now stated for 8.1
> rather than one - **historical schedule authority** (pre-restructure expectations stay
> reconstructable) and **economic transfer** (any amount folded into the new principal has a
> traceable disposition from the old agreement). The second is the one that would have been
> missed: an immutable version chain satisfies the first completely and says nothing about whether
> the arrears are now also inside the new balance, so **history can be preserved perfectly while
> the economics double-count**.
>
> **And 8.1 and 8.2 turned out not to be independent**, which the inspection had wrong. §7.7 keys
> instrument kind on *who carries the obligation*, and medical debt is sold routinely - so an
> unchanged agreement can change kind by a third party's act. Either kind is mutable and a sale is
> a transition, or kind is immutable and a sale **ends the agreement**, which is 8.1's restructure
> question arrived at from the other side with the same arrears problem attached. The instrument-
> kind transition question is therefore settled **first**.
>
> **RESTRUCTURED, not refined — `gw 2.0/OBLIGATION_LIFECYCLE_QUESTION.md`** (2026-09-09). 8.1 and
> 8.2 are no longer separate decisions. One governing question replaces them: *what is the
> lifecycle of an obligation when the party carrying it, its instrument, or its economic terms
> change?* - judged by whether a candidate model can reconstruct **both** the user's obligation
> history **and** the economic disposition of every dollar across the transition. Two anchorings
> are viable (instrument-anchored, agreement-anchored); mixing them is the failure.
>
> Three findings from testing the five scenarios. **The cliff is probably not a lifecycle event at
> all** - §7.7's carrier rule makes a deferred-interest promo lender-carried from origination, so
> nothing changes hands at the cliff and a conditional consequence simply fires; it therefore
> cannot decide the lifecycle, which is what Rob warned against. **The real discriminator is a
> transfer with arrears outstanding**, where the agreement-anchored model manufactures an
> economic-transfer problem the instrument-anchored one does not have - against which stands the
> genuine counter that a bill held by a collection agency is not the same thing in a user's life.
> And **the economic-transfer invariant holds under every candidate model**, so it is already a
> requirement rather than a consequence, and does not wait on the governing decision.
>
> **Carrier claim verified 2026-09-09 - and the verification found something bigger.** The narrow
> claim holds on better evidence than one product: the CFPB's taxonomy puts the creditor at a
> financial firm rather than a provider for every deferred-interest medical product in its scope,
> and it excludes in-house plans entirely. But **recourse patient financing breaks §7.7's single-
> carrier assumption** - the provider transfers the receivable for cash up front, retains
> contingent liability, and **takes the account back on default**, which is frequently what makes
> 0% APR possible in the first place. So transitions can be round trips, the return leg is
> triggered by the user's own non-payment (a feedback path from payment state into obligation
> identity), and the user may not be told - which relocates *a sale is never silent* rather than
> weakening it. Whether the carrier rule classifies on **servicing** or on **risk** is doctrine
> and Rob's, and M1/M2 cannot be settled while it is open.
>
> **And that is a premise invalidated, not an edge case added** (§10). *Who carries an obligation*
> is **three layers** - funding, servicing, and economic risk - which coincide in the arrangements
> §7.7 was written against and separate under recourse. One `carrier` field cannot represent all
> three. So the governing question moves up again: **what does §7.7's "carries" mean** -
> servicing, funding, economic risk, legal creditor status, or a defined combination? Doctrine,
> and Rob's. M1/M2 stops until it has an answer, because a choice made now would rest on a
> definition of *carrier* the evidence has shown does not exist.
>
> Two rules fall out and apply under **either** model. **Payment state may become evidence about a
> change in who bears an obligation; it may never independently establish that change** - non-
> payment precipitates a recourse return, it does not constitute one, and inferring it would
> manufacture a fact about a third-party contract from the user's own ledger (now principle 1's
> sharpest instance). And **a discovered transition preserves both when the change became
> effective and when Groundwork learned of it** - collapse those and late-arriving evidence
> rewrites the user's history. *A sale is never silent* survives, qualified: Groundwork cannot
> promise to detect a transition it has no evidence of, only that a known one is dated, sourced
> and reconstructable.

> **Review triaged, not accepted — `gw 2.0/LIFECYCLE_REVIEW_TRIAGE.md`** (2026-09-09). Fifteen
> findings against the lifecycle and carrier work, dispositioned against what exists. Five were
> already recorded, four are refinements of existing partials, three are genuinely new and are
> recorded with their blocked and unblocked portions separated, and two are **fenced**. Only two
> items are actionable now — the disposition vocabulary and the five-question reconstruction
> test — both because finding 4 already established that the economic-transfer invariant is
> produced by neither anchoring. The review's proposed carrier corpus is fenced because its
> columns presume the four-dimension decomposition that §10 refuses to presume: **a review that
> warned against the schema becoming the doctrine drafted the table that would have done it**,
> which is why the dependency chain is recorded there as a rule rather than an intention.

### 15. Failure-mode behaviour — **CLOSED AS DESIGN** (2026-09-09)

> **Closed as design, not solved.** Rob's wording, and the distinction is the point: wrong
> inputs are not fixed, but *the question now has an explicit boundary* and the implementation
> work is **deferred on purpose** rather than forgotten.
>
> **Why the status has to say that.** Otherwise someone six months from now reads
> *wrong-but-coherent input* and concludes **"we need an AI confidence layer."** The design's
> answer to that person: **confidence must not be invented merely because the pipeline agrees
> with itself.**
>
> **The four shall-nots, in the form to attack in implementation review:**
>
> ```text
> agreement              ≠  evidence
> coherence              ≠  conclusion authority
> consistency            ≠  reduced correctability
> successful processing  ≠  evidence of correctness
> ```
>
> The three ownership questions stay open. **Implementation pressure must not answer them
> accidentally.**

Classification fails, plan resolution fails, EOB parsing fails, a duplicate is detected wrongly,
a correction cannot be reconciled, reserve inputs go stale, the user deletes the source document,
imported data conflicts with manual entry. **None of these has a stated answer.** The design
specifies behaviour when data is good.

The one partial exception is the honest-null discipline already in the engine — `simulate_payoff`
returns `None` rather than a fabricated figure when the budget cannot cover minimums — which is
the right shape, applied in one place and not generalised.

> **DESIGNED, not built — `gw 2.0/HEALTHCARE_FAILURE_SEMANTICS.md`.** Written as a design
> exercise at Rob's direction, because inventing an error-handling framework first is how the
> framework decides the semantics.
>
> **The distinction that decides it:** *detected failure* (the model knows it could not
> establish something) versus **plausible and wrong** (it establishes something confidently and
> falsely). Only the first is an error-handling problem. A parser returning nothing has failed
> safely; a parser reading `$412` as `$4.12` has *succeeded*, and every honest-null guarantee is
> irrelevant to it. The document says plainly what protects against the second — provenance,
> weakest-link strength, and cheap non-destructive correction — and that **nothing catches a
> confident mistake**, because nothing can.
>
> **Four boundaries, four permissions**, conflating which is how a cautious return value becomes
> a confident sentence three layers on: *return* must be able to express *I could not establish
> this*; *record* may keep the attempt but never the guess; *surface* is Passive, always; *say*
> is templated and may name the gap without explaining it. The narrator may always say **less**
> than the return value supports and never more.
>
> **Five of the eight cases follow from existing doctrine** — classification, plan resolution
> and EOB parsing are one shape (*preserve the input, withhold the conclusion*); an
> unreconcilable correction goes `UNRESOLVED` with both figures surviving; a stale target
> reports with its age rather than freezing or vanishing.
>
> **Three are genuinely open and are Rob's**, and his 2026-09-09 reading sharpened each into the
> prior question it actually is: a wrongly-detected duplicate later found distinct is a
> **correction-authority** problem — *who is authorized to establish that the two records were
> distinct?* — not a reversibility problem. Deletion of a source separates **the fact remains**
> from **the evidence remains**, which need not share a lifecycle; whether a derived financial
> fact may outlive its source is a policy decision the provenance machinery must not settle by
> construction. And import-versus-manual keeps an **explicit tie state**, because the model has
> no tie-break today (`user_stated` and `imported_eob` are deliberately equal knowing sources)
> and asserting *manual wins* would be inventing a hierarchy rather than reading one.
> **No implementation until those have answers.**
>
> **Added 2026-09-09, two things.** The **permission ladder** — Record → Calculate → Conclude →
> Recommend, each harder to earn than the one below — which is principle 1 restated as
> permissions rather than layers, because a call graph can honour a layered diagram while one
> function climbs all four rungs. It buys a concrete future test: hand the narrator a rich
> internal result and verify its language cannot upgrade *possible → certain*, *inferred →
> observed*, *estimated → actual*, *unresolved → resolved* without an explicit evidence
> transition.
>
> And the **design adversary** (§5), Rob's test of the document itself: *can every safety rule
> survive a wrong input that is internally consistent?* Every rule holds against a `$412` that
> should be `$4.12` and is wrong at every layer, consistently — **and that is not a defect**,
> because no rule here was ever a claim about correctness. The requirement it produces is an
> inversion: *what must Groundwork not do merely because all the layers agree?* Four answers —
> agreement is not evidence; coherence licenses no ladder climb; a consistent conclusion may not
> become harder to correct; the narrator may not describe the process as evidence about the
> answer. **Do not build another safety mechanism merely because the design admits that
> plausible errors exist.**

### 14. A general rule for naming external actions

§0.3 settles *cost, not counsel* for healthcare specifically. The review's generalisation — **a
user-verifiable external action may be named when it follows from an established fact; an
outcome or negotiation position may not** — does not exist as a reusable rule, and it should,
because the next module will face it.

---

## PARTIAL — mechanism exists, statement or coverage does not

### 2. Historical truth versus current truth

Every module built this session takes `as_of` and reproduces the earlier answer: plan-year terms,
person assignments, allocation rule versions. So the mechanism is thorough. **What is missing is
the invariant stated as such** — *a historical conclusion is an immutable representation of the
knowledge available then; a current conclusion may be superseded by later evidence.* Both true
at once, and nothing says so in one place.

### 3. Unknown is not one state

Four of the review's six already exist, and the split was deliberate:

| Review's | Exists as |
|---|---|
| PENDING | `pending_claim` — settles nothing, distinct from `unpaid` |
| NOT_PROVIDED | `not_evaluated` — never examined |
| UNRESOLVED | `UNRESOLVED` — the arithmetic gap, no definitive total |
| UNKNOWN | `UNKNOWN` — plan terms nobody supplied |
| NOT_COVERED | **absent** — would be a determination |
| NOT_APPLICABLE | **absent** |

`contradicted` also exists and is on none of the review's lists — *we looked and found against
it*, deliberately split from *we never looked*. **So the challenge is answered for four, and two
are genuinely unrepresented.**

### 5. Payment-to-obligation attribution

Representable but unnamed. A confirmed payment is `cleared + attached + user_confirmed`; an
attachment the system guessed would be attached-but-not-user-confirmed, which is exactly the
review's *inferred*. **The states exist; the vocabulary does not**, and a nameless distinction is
one nobody enforces.

### 7. Financial progress versus contractual adherence

Conceptually separated and argued (*early is free, late is not*; progress is dollars, payment
count is a label beside it). **Schema absent** — see gap 8. The review's point that the schema
must make the collapse impossible is right and unmet.

### 9. Reserve language in the UI

Already conceded in the first review round: the architecture refuses the promise, **no
user-facing language exists at all**. The review extends it correctly — solving the semantics in
the database and recreating the problem in the UI is a live risk precisely because the UI is
unwritten.

### 11. Joint-account relational leakage

The mechanism exists: sensitivity propagates through narrator, export and backup, and derived
facts inherit it. **What is untested is reconstruction** — whether a health situation can be
rebuilt from surfaces that carry no health marking. That is a different and harder property than
"health rows are hidden", and the review is right that it is architectural rather than cosmetic.

### 12. Export, logs, backups, diagnostics

Export and backup carry sensitivity and are asserted. **Logs, diagnostics, crash reports and
screenshots are not covered**, and the single invariant the review proposes — *no health-sensitive
fact crosses the local trust boundary unless the operation explicitly permits health data* — does
not exist. Its framing is better than what is there, because it puts the burden on every exporter
rather than on each new surface remembering.

> **INVARIANT RECORDED, ENFORCEMENT MEASURED — `gw 2.0/HEALTH_TRUST_BOUNDARY.md`** (2026-09-10).
> Rob's full statement is now doctrine: deny-by-default, no implicit inheritance, indirect paths
> count, fail closed, plus the blast-radius and release-blocking lists. **No enforcement model was
> designed** — §5 of the failure-semantics document forbids reaching for a mechanism at the moment
> a design admits violations are possible.
>
> What was done instead was measurement, and it moves this entry off PARTIAL for the wrong reason.
> **The sensitivity layer has no contact with any crossing that exists:** `server.py` imports six
> `core/` modules and **never `core.classification`**, where `Sensitivity` and `consume()` live.
> Roughly ten `urlopen` sites in `server.py` and eight further modules each open their own
> connection, so there is no place a crossing is recognisable as one. **Five of the six
> release-blocking conditions hold today**, against financial data, before healthcare exists.
>
> Three replicas sit outside the database and outside the sensitivity machinery: the application
> log, `voice_miss_log.jsonl` — which stores **the narrator's generated sentence verbatim**, up to
> 2000 characters — and the beta bug report. The bug report is the sharp one: the panel labelled
> *Report preview* does not show the report, because `_gwSendFeedbackEmail` appends server log
> lines after the preview is rendered, beside a line claiming no transaction details are included.
> **A present defect in shipped 1.0 code, separable from healthcare.**
>
> Two questions are Rob's before any mechanism: **is the local browser inside the boundary**
> (`/api/debug/log-tail` is a crossing under one reading and not the other), and **what makes a
> value health-sensitive** — origin, classification domain, or available inference. The second is
> unanswered for exactly the artefacts the findings are made of: a formatted sentence, a route
> path, an exception message.
>
> **BOTH ANSWERED 2026-09-10 (Rob's), §8 — semantic, not structural.** Sensitivity may never be
> read off a field name, storage location, source system, transport or representation. Three
> independent limbs — origin, classification domain, **available inference** — and
> **transformation does not declassify**: no pipeline may launder health information into an
> apparently ordinary representation by changing its format or location. Where classification
> cannot be established with confidence, the artefact **stays** health-sensitive; uncertainty may
> not resolve to safe. The browser question was **malformed rather than open**: location is not
> evidence of safety, and *where may this go* / *what does this reveal* / *is this operation
> authorized* are three separate axes.
>
> **The finding that came out of applying it (§9): the doctrine is already in the code, and its
> scope is the gap.** `DerivedFact` carries the sensitivity of what produced it, for the stated
> reason that *"'spending increased 20%' contains no medical word and is still health
> information"* — the doctrine's own argument, written before it. **Declassification happens at
> rendering**: the moment a figure becomes a sentence, a route path or an exception message it
> leaves the typed lattice and nothing carries the domain with it. F3 is that path in production
> today.
>
> All three artefacts are classified **health-sensitive**, two of them because the blocker's
> question cannot be answered rather than because the answer is bad. And F3 forces a structural
> consequence rather than a policy one: the narration reaches the server as a bare string, so
> *is this value health-sensitive* **cannot be evaluated at the boundary** — meaning **either
> narration carries its sensitivity from the point the figure becomes a sentence, or the miss-log
> cannot exist in 2.0.**


---

## ADDRESSED

### 10. The reserve as a hidden priority engine

This is the one the architecture is most explicitly built against. `core/reserve.py` **has no
opinion** on whether the reserve is filled before, alongside or after the last debt balance, and
says so. The Q6 instrument carries a written guard: **it enumerates consequences, it does not
rank options.** The review's distinction — *"filling this reserve would delay payoff by 4 months"*
is Groundwork; *"you should fill your reserve first"* is Groundwork deciding — is the line
already drawn, and `tests/payoff_option_measurement.py` exists to keep the decision with the
user rather than the tooling.

### 13. Commercial medication pricing

Agreed, and already the design's position: §2.1 argues the partnership *need not be pursued*, and
§6.3 files it as gated and optional. The user's own recorded price is inside Groundwork; a
pharmacy price index is a different product.

---

## The other end of the method — what the user can supply

**`gw 2.0/USER_KNOWLEDGE_CASES.md`** (2026-09-10). Every case set above asks what the *model* must
distinguish. This one asks what a *person* can actually supply, written against Rob's doubt that
the semantics were becoming too specific for a user who is unsure.

**The floor is not zero.** One bill and nothing else already supports bill shock and cash-flow
effect — the two things most likely to matter on the day someone opens a medical bill. Value
degrades along a ladder rather than falling off a cliff, and the fields that demand real knowledge
are the ones whose absence is safest to admit.

**The precision reduces the demand on the user rather than raising it.** Carrier being explicit is
what makes *I don't know who holds this* recordable instead of defaulting to *the provider*.
Not-knowing not being a disposition is what stops the model demanding one. Unconfirmed payments
have a home. **A model that collapses these is the model that makes the user decide before anything
can be recorded.**

**The risk is concentrated in one field** — instrument kind, which is both hard to supply and gates
a class of statements. In two of three sub-cases the ask is *look at the paperwork*, not *know*,
which is gap 14's ungeneralised rule doing the work.

> **One new finding, and it is a live one: adherence language must be gated on instrument kind
> being established, not merely on a schedule existing.** With a schedule and no kind, the system
> can compute adherence perfectly and say *"you're on track"* about a deferred-interest balance
> whose cliff the schedule does not contain — arithmetically true, materially false, and the worst
> combination a teaching system can produce. Nothing currently prevents the sentence.

And the sentence the surface decision turns on, recorded so it is made deliberately rather than
discovered in a form: **the distinctions the model must hold are not the questions the interface
may ask.**

---

## The closing criticism, which I think is correct

> *The biggest danger is not getting healthcare wrong. It is becoming the first place Groundwork
> violates its own philosophy.*

Worth recording because it identifies the mechanism, not just the risk: healthcare knows history,
insurance, deductible, cash flow, debt and reserve simultaneously, and that concentration is what
makes *"you should…"* feel earned. The architecture has to make it hard **even when the
recommendation would be financially sensible** — which is a strictly stronger requirement than
making it hard when the recommendation is wrong.

The existing defences are real: the honest-no, the levers-not-decisions rule, F.6b's refusal to
model motive, and the Q6 guard. **What the review adds is that none of them was designed against
a subsystem that knows this much at once**, and that is a fair thing to say.

---

## What I would do first

Ordered by *cheap to close and dangerous to leave*, which is not the review's ordering:

1. **Gap 4** — the data is already there; only the invariant is missing. Write it, assert it,
   mutation-test it.
2. **Gap 1** — a fixture question, answerable with the existing lifecycle harness.
3. **Gap 6** — a compound-payment fixture, the kind that has found things every time this session.
4. **Gap 2** — one invariant, stated once, covering machinery that already exists.

Gaps 8, 15, and the schema half of 7 are larger and depend on entities that do not exist yet.
