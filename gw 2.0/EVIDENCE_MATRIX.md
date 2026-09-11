# The evidence matrix

**Ten adversarial questions, run against `core/classification.py` rather than against a summary of it**

> Status: **Adversarial review, 2026-09-10. No implementation, and no doctrine decided.** The
> question is narrower than *what does Groundwork know*:
>
> > **For each fact: what evidence can legitimately establish it, how strong is that evidence, and
> > which downstream claims may use it?**
>
> **The three doctrine decisions stay out.** This review must not decide what `carrier` means, must
> not decide the disposition scope, and must not decide whether the miss-log exists. It establishes
> what evidence information is *available* and what a consumer may legitimately do with it — which
> is what those decisions will need afterwards, not a substitute for them.
>
> **The chain under attack**, with contradiction, staleness, weak evidence, correction and absence
> introduced deliberately at each link:
>
> ```text
> evidence → established fact → derived fact → claim permission → narration
> ```
>
> The failure being hunted is not *did the parser handle this*. It is:
>
> > **did the weakest evidence stay visible all the way to the point where Groundwork decides what
> > it is allowed to say?**

---

## The matrix

| # | Area | Verdict |
|---|---|---|
| 1 | source authority — equal ranks disagreeing | **GAP — an invented winner, decided by list position** |
| 2 | user-stated — what it establishes | **GAP — no separation of *said* from *so*** |
| 3 | imported/EOB — parsed vs true | **GAP — parsing establishes the fact** |
| 4 | contradiction — lowers permission, or picks a winner? | **HOLDS for classification · ABSENT for values** |
| 5 | age | **GAP — recorded everywhere, consulted nowhere** |
| 6 | correction — old claim reconstructable? | **HOLDS** |
| 7 | composite facts — weakest component inherited? | **HOLDS, and better than stored** |
| 8 | corroboration — five references to one source | **HOLDS at classification · latent downstream** |
| 9 | missing evidence — `UNKNOWN` vs `NOT_APPLICABLE` | **GAP — gap 3, now with a boundary consequence** |
| 10 | claim permission — stronger claim than evidence permits | **GAP — strength gates access, not assertion** |

---

### 1. Can two sources of equal rank disagree without forcing an invented winner?

**No. The winner is whichever appears last in the list.**

`_state_from` (`core/classification.py:250`) takes knowing-party evidence and resolves it as:

```python
knowing = [e for e in ev if e.source in KNOWING_SOURCES]
if knowing:
    latest = knowing[-1]
```

`KNOWING_SOURCES` is `{USER_STATED, IMPORTED_EOB}` (`:88`), and both carry rank 3 in `_RANK`
(`:629`) — deliberately equal, because gap 15 recorded that asserting *manual wins* would invent a
hierarchy the model does not have.

**So the deliberate tie at rank 3 is broken further down by list position.** A user saying *health*
and an EOB saying *not health* resolve to whichever was appended second. That is an invented winner
arrived at by accident rather than by decision — the outcome gap 15 explicitly refused, reached
through a different door.

Gap 15's own answer already exists and is unimplemented: **keep an explicit tie state.**

### 2. What exactly does a user statement establish, and what may it not become?

`USER_STATED` on the content axis produces `USER_ASSERTED` (`:250`), rank 3 — the top of the
lattice, tied with an attested import.

**What is missing is the distinction `USER_KNOWLEDGE_CASES.md` U5 named.** The model can record
*the user says this is a medical expense*. It has no way to record *the user says the letter says
the account was purchased* — a statement **about a document** rather than about the world. The
first is testimony the user is competent to give; the second is a report of evidence they hold and
Groundwork has not seen.

Both currently land as `USER_ASSERTED`, at the top of the lattice.

### 3. Does successful parsing establish the fact, or only that the document contained the value?

**It establishes the fact.** `IMPORTED_EOB` is a knowing source, so a parsed EOB yields
`IMPORTED_ATTESTED`, rank 3.

There is no state for *this document contained this value*, distinct from *this value is true*.
Which is the same shape as finding 2, from the machine side — and it is `HEALTHCARE_FAILURE_SEMANTICS.md`'s
first shall-not at the evidence layer: **successful processing is not evidence of correctness.** A
parser that reads `$412` as `$4.12` produces `IMPORTED_ATTESTED`, indistinguishable from one that
read it right.

### 4. Does conflicting evidence lower permission, or does the system select a best source?

**For classification it lowers permission, and does so correctly.**

`CONTRADICTED` sits at rank 0 (`:629`), tied with `NOT_EVALUATED` and kept distinct from it.
`strength_of` (`:666`) takes the **weakest material source** for a derived fact, and
`_prefer_contradicted` (`:697`) breaks the floor tie toward `contradicted` in both directions — so
a contradicted source in a chain is named rather than disappearing into *unevaluated*.

Every declared consumer requires rank ≥ 1 (`CONSUMER_STRENGTH`, `:641`). **A contradicted fact is
therefore refused by all four consumers that exist.** More evidence, less permission — working, and
enforced rather than described.

> **And here I have to correct myself.** `USER_KNOWLEDGE_CASES.md` U6 claims that four conflicting
> balance figures produce a `contradicted` strength and that the case set had simply failed to
> exercise built machinery. **That is wrong, and it was my claim rather than the review's.**
>
> `Evidence.supports` is a boolean about whether a piece of evidence supports **a health-domain
> claim on an axis**. `CONTRADICTED` means *a knowing party said this is not health*. It does not
> mean *two sources gave different amounts*.
>
> **There is no representation anywhere in this module for value-level disagreement.** $4,000 vs
> $3,500 vs $3,700 vs $3,176 is not expressible as contradiction; it is four facts with no stated
> relationship. U6 is a genuine gap, not an unexercised mechanism, and the correction makes it
> worse rather than better.

### 5. Can historical evidence establish a historical fact without establishing the current value?

**No, and the data to do it is already recorded.**

`Evidence` carries `recorded_at`, and `Determination` carries `determined_at` (`:250` and around
`:280`). Neither is consulted by `_state_from` or by `strength_of`. **Age is captured everywhere and
used nowhere**, so a corroborated EOB from 2019 and one from this morning are indistinguishable at
the consumer boundary.

**And a second-order finding falls out of #1.** `knowing[-1]` is described as *the latest*, but it
is the **last element of a list**, not the latest by `recorded_at`. Supersession is positional
where the record is temporal.

> **Refined after writing the fixture, because the first statement of this was too strong.**
> `record_evidence` stamps `recorded_at` itself and always appends in call order, so through the
> **only public mutator, position and time coincide** and the defect cannot be reached. It is
> **latent, not live** — reachable only by assembling an evidence tuple directly, which is what a
> merge, a re-import, or a backfill does.
>
> **It will not stay latent.** §10 of `OBLIGATION_LIFECYCLE_QUESTION.md` makes late-arriving
> evidence mandatory — `effective_on` in the past, `recorded_at` now — and that is precisely the
> shape in which the two orderings disagree.

This is `USER_KNOWLEDGE_CASES.md` U7 and gap 2's unstated invariant, landing on one attribute
access.

### 6. When new evidence replaces old, does the old claim remain reconstructable?

**Yes.** Classifications are immutable, `Determination` carries `rule_version` and `determined_at`,
and `classify` (`:284`) records a determination for **both** axes even at `not_evaluated`, because
*an absence has provenance too*.

`strength_of` recomputing on every read reinforces rather than threatens this: a derived fact is a
statement about its sources *as they stood*, and a caller wanting a current view re-derives. That
was already recorded as gap 2's historical-truth invariant showing up concretely.

### 7. Does a derived fact inherit the weakest evidentiary component?

**Yes, and by a better mechanism than storing it.** `strength_of` (`:666`) computes the weakest
material source **on every read**, with `_is_material` (`:707`) excluding sources that contributed
nothing — *a source contributing nothing cannot weaken what it did not build*.

The docstring states the reason, and it is the right one: *invalidating a source invalidates
everything derived from it without anything having to remember to recompute.*

### 8. Can five downstream references to one weak source look like five pieces of evidence?

**Not at the classification layer.** `_state_from` (`:250`) computes corroboration as
`distinct = {e.source for e in supporting}` and requires `len(distinct) >= 2`. Two signals from the
same source do not corroborate. Deduplication by source identity is exactly the right guard and it
is already there.

**Not through the lattice either.** Five derived facts all citing source A, folded into a sixth,
still resolve to A's strength under weakest-link. Amplification cannot occur through `strength_of`.

**Latent, and worth naming rather than fixing:** `DerivedFact.sources` is a plain tuple with no
deduplication (`derive`, `:715`). Nothing today counts it — but a future surface that renders *"5
sources"*, or a consumer that reads `len(fact.sources)` as corroboration, would manufacture exactly
the appearance the lattice refuses. The invariant lives in `strength_of`; the tuple is one
`len()` away from contradicting it.

### 9. Does absence become `UNKNOWN`, or can a consumer read it as `NOT_APPLICABLE`?

`NOT_EVALUATED` is the only representation of absence, and gap 3 already records `NOT_APPLICABLE`
and `NOT_COVERED` as the two genuinely unrepresented states.

**What this review adds is the consumer-boundary consequence.** §8 of `HEALTH_TRUST_BOUNDARY.md`
requires failing closed where classification cannot be established. If *not applicable* cannot be
distinguished from *not evaluated*, then everything genuinely inapplicable **fails closed
permanently** — and a rule that refuses a large class of things forever is one people route around.

Fail-closed and an unrepresentable *not applicable* are individually correct and jointly corrosive.

### 10. Can a consumer use a fact for a stronger claim than its evidence permits?

**Yes. Strength gates access to the number; it does not gate what is claimed with it.**

`consume` (`:745`) returns `UNAVAILABLE` or the value. Once a consumer clears its declared bar it
holds a float, and nothing constrains the sentence built from it. `narrator` requires `CORROBORATED`
— so a corroborated fact may be narrated, and the narration may say anything.

This is precisely the rung the **permission ladder** (Record → Calculate → Conclude → Recommend) was
designed for in `HEALTHCARE_FAILURE_SEMANTICS.md`, and it is designed and not built. The matrix's
last link is the unimplemented one.

---

## The particularly important gap, answered precisely

> *Does evidence strength belong to the fact, or only to the evidence graph behind the fact?*

**Neither, and the third answer is better than both.** Strength is a **function over the graph,
recomputed on every read** — `strength_of` (`:666`) — and `consume` calls it. So the concern that
*the permission boundary depends on every consumer remembering to walk `sources`* **does not hold**:
no consumer walks anything, and none can forget to.

**But the enforcement is one convention, not a structure.** `consume`'s docstring says it is *"the
only way to take a value out of a derived fact"* — and `DerivedFact` (`:392`) is a frozen dataclass
whose `value` is a public attribute. `fact.value` works. Nothing prevents it, and
`tests/test_evidence_strength_fixture.py:166` reads it directly (legitimately, to prove two facts
with equal values differ in strength — but it demonstrates the attribute is freely readable).

So the gap is real and it is **one step narrower than described**:

```text
NOT   every consumer must remember to walk the sources
BUT   every consumer must remember to call consume() instead of reading .value
```

**The precedent for closing it already exists and was not applied here.** Gap 6 asserted the
*absence* of a `paid()` accessor, so a future convenience method could not reintroduce the drift.
The analogous assertion — that no consumer reads `.value` — **does not exist in the fixture or in
s95**. That is the hard look this deserves, and it is a test rather than a mechanism.

---

## Findings

1. **The deliberate tie at rank 3 is broken by list position.** `knowing[-1]` invents the winner
   gap 15 refused to invent. The recorded answer — an explicit tie state — is unimplemented.
2. **Supersession is positional where the record is temporal.** `recorded_at` exists and is never
   used to order. §10's discovered-transition work depends on evidence arriving late, which is
   exactly when position and time diverge.
3. **Age is recorded everywhere and consulted nowhere.** A 2019 corroborated EOB and this morning's
   are indistinguishable at the boundary.
4. **Testimony about a document is indistinguishable from testimony about the world**, and both sit
   at the top of the lattice.
5. **Successful parsing establishes the fact**, with no state for *the document contained this
   value*. The failure-semantics shall-not — *successful processing is not evidence of correctness*
   — has no representation at the evidence layer.
6. **Value-level disagreement is unrepresentable.** `CONTRADICTED` is about a boolean claim on an
   axis, not about conflicting amounts. **This corrects a claim I made in `USER_KNOWLEDGE_CASES.md`
   U6**; the gap is larger than that document says.
7. **Fail-closed plus an unrepresentable `NOT_APPLICABLE` is corrosive**, because it refuses a whole
   class permanently — and permanent refusals get routed around.
8. **Strength gates access, not assertion.** The last link of the chain is the permission ladder,
   which is designed and not built.
9. **`consume()` is the only way in by convention, not by construction**, and unlike gap 6 the
   absence is not asserted.
10. **`DerivedFact.sources` is one `len()` away from manufacturing corroboration** the lattice
    exists to refuse. Latent, no instance today.

**Holding well and worth saying so:** weakest-link inheritance (7), materiality exclusion,
source-identity deduplication (8), contradiction as a permission-lowering state at the classification
layer (4), and correction reconstructability (6). The chain does keep the weakest evidence visible
from evidence to derived fact — it stops being visible at **claim permission**, which is finding 8.

---

## The case where more evidence makes the claim weaker

Requested explicitly, because it is the case most likely to expose *more inputs = more confidence*.
The module already produces it — and only in one of the two available shapes.

```text
WORKS      user says medical → USER_ASSERTED (rank 3)
           EOB then says not medical → CONTRADICTED (rank 0)
           the derived fact drops below every declared consumer
           more evidence, strictly less permission

FAILS      bill $4,000 · user $3,500 · statement $3,700 · payments imply $3,176
           four facts, no stated relationship, no strength consequence
           more evidence, unchanged permission
```

**The first shape is enforced. The second has no representation at all**, and it is the shape a real
household actually produces.

---

## Both tests are written, and both fail

*(2026-09-10. The two findings the review marked as tests rather than mechanisms.)*

**`tests/test_consumer_boundary_fixture.py` — 7 passed, 3 failed.** Three levels: the declared
refusals still fire (regression guard, all pass); no function in the module hands out a raw value;
no application file reads `.value` off a derived fact (passes today, exists to fail when the first
consumer arrives).

> **The middle level is not hypothetical, and it is worse than finding 9 described.** An AST scan
> for a read of `<param>.value` outside `consume` returns two offenders:
>
> ```text
> core/classification.py:430   narrator_facts()
> core/classification.py:435   export_row()
> ```
>
> **`narrator` and `export` are two of the four declared consumers in `CONSUMER_STRENGTH`** — and
> the module's own helpers for exactly those two consumers read the value directly. The strength
> each of them declares is never consulted on the path each of them uses. Verified behaviourally
> as well as structurally: `narrator_facts` emits the number for a `single_weak_signal` fact that
> `consume(fact, 'narrator')` refuses, and `export_row` emits it for a `contradicted` fact that
> `consume(fact, 'export')` refuses. `backup_row` delegates to `export_row` and inherits it.
>
> So finding 9 understated the case. `consume()` is not merely *the only way in by convention* —
> **the convention is already broken, inside the module, for half the consumer table.**

**`tests/test_evidence_tie_fixture.py` — 4 passed, 4 failed.** The controls hold: a user statement
establishes content, a non-knowing signal may not overturn a knowing one, and the same knowing
source may correct itself. Then:

```text
user says health, then EOB says not   ->  contradicted
EOB says not, then user says health   ->  user_asserted
```

Three assertions fail on that pair — order independence, *neither source wins by being recorded
second*, and the sharpest one: **in the second order the disagreement leaves no trace at all.**
`eob_then_user` is byte-identical to a user statement nothing ever contradicted. A conflict that
reads as though it never happened is worse than an unresolved one.

The fourth failure is the temporal half, asserted directly against `_state_from` because
`record_evidence` cannot produce the ordering: with `recorded_at` disagreeing with list position,
the *older* statement wins.

**Neither fixture is wired into `smoke_test.py`.** It discovers `smoke_sections/` only, so the
suite is unaffected — **824 passed, 0 failed**, verified after adding both. Wiring them in would
turn the gate red, correctly, and that is a decision rather than a consequence.

**No mechanism was written for either.** No tie state, no accessor guard, no change to
`narrator_facts` or `export_row` — what those should do when the evidence is refused is a design
question, and the standing rule is not to answer it in the same pass that found the defect.

---

## Three failure classes, and they must not be collapsed

*(Rob, 2026-09-10, on the fixture results. The classification is his and it is the useful output
of having written the tests.)*

| Failure | What breaks | Status |
|---|---|---|
| **consumer bypass** | a permission declaration does not govern actual consumption | **live defect** |
| **conflict disappearance** | the current fact's *summary* loses the disagreement; the record keeps it | **fixed** — `resolution()` carries it beside the value; gate-guarded by s98 |
| **effective vs recorded ordering** | the late-arrival case cannot presently be produced | **latent** |

**These are three mechanisms, not one evidence-handling gap.** The first is an
**authority-boundary bypass**, the second is **summary loss over an intact record** — first
labelled *provenance and history loss*, corrected by `RESOLVED_CONFLICT_CASES.md`, which found
the determination chain and evidence tuple preserve the conflict and only the current state and
strength collapse it — the third is **temporal semantics the current mutator cannot exercise**. Collapsing them would produce one
vague gap and, worse, one vague fix.

### The consumer bypass, restated as the requirement it implies

The module has **two parallel authority paths**, and the AST result is what makes it clean — the
bypass is not a hypothetical future consumer, it is inside the implementation of two consumers
that are named in `CONSUMER_STRENGTH`:

```text
narrator_facts()  ─┐
export_row()      ─┼──→  fact.value          no check
backup_row()      ─┘

consume()          ───→  strength check      the declared boundary
```

> **A declared consumer permission is not an architectural permission boundary unless every path
> by which that consumer obtains a fact is subject to the same permission check.**

The behavioural failures establish this is not stylistic: weak evidence reaches narration despite
narration's declared refusal, contradicted evidence reaches export despite export's, and backup
inherits export's bypass.

### Conflict disappearance, stated narrowly on purpose

The two histories produce byte-identical representations:

```text
A   user says health                                 no disagreement ever existed
B   EOB says not-health → user says health           a disagreement existed and vanished
```

Downstream code cannot tell A from B, which is the principle already applied elsewhere — *a
correction must not destroy the history required to explain how the current fact came to be.*

**The derived requirement is narrower than the obvious fix**, and the caution matters more than
the finding:

> **A resolution of conflicting evidence may change the current conclusion, but may not silently
> erase the existence of the conflict.**

*Therefore every conflict becomes `CONTRADICTED` forever* is **a possible design, not a derived
requirement**, and adopting it here would be settling by convenience the question gap 15 left
open. What survives a resolution — the prior contradictory evidence, a resolved-conflict marker,
provenance showing conflict and resolution, or some combination — is a separate decision, and it
is independent of the consumer-boundary fix.

### The temporal case stays latent, and says something useful as a latent

`record_evidence` sets `recorded_at = now` and appends in the same call, so call order and recorded
time **necessarily agree today**. The implementation therefore does not demonstrate a temporal
defect. What it demonstrates is:

> **The representation already carries both temporal concepts the future case needs; the current
> mutation path cannot create their divergence.**

§10 supplies the future case — `effective_on` in March, `recorded_at` in September — at which point
processing order stops being the same thing as effective chronology. **Retained as a latent matrix
requirement, not promoted to a current bug.**

---

## What must be answered before either fix

Two design questions stood between the fixtures and a fix. **One is now settled; the other is
genuinely open and is not to be inferred from the first.**

### Q1 — CLOSED: refusal propagation semantics

*(Rob, 2026-09-10.)*

> **The refusal is the consumer-facing value, in place of the refused value.** It must preserve
> `offered`, `reason`, `required` and `consumer`. **Presentation of those fields is a separate
> downstream decision.**

```text
fact
 ↓
consume(fact, consumer)
 ↓
 ┌───────────────┐
 │ permitted     │ → value
 │ refused       │ → refusal(fact, consumer)
 └───────────────┘
                         ↓
                  the consumer receives
                  the refusal itself
```

**And no consumer may bypass that boundary by reading `.value` directly.**

This closes the live defect **without inventing another state** — `refusal()` already returns
exactly that structure, and `consume()` already computes the decision. Nothing new is added to the
lattice.

**The three alternatives, and why each is refused:**

| | |
|---|---|
| **omission** | **prohibited** — absence alters downstream interpretation. A dropped row changes a total silently and a blank cell *is* a zero to a spreadsheet. This is `absence is not zero` exactly: blank income months once read as a $7,053 shortfall that was a surplus |
| **bare `UNAVAILABLE`** | technically safe, and it loses the distinction between *not evaluated*, *contradicted* and *insufficient evidence* that the lattice deliberately preserves — the gap-12 pattern a second time, where a distinction survives the typed layer and dies at rendering |
| **exception** | wrong failure mode for an export or narration boundary. An export that crashes on one contradicted row is worse than one that marks it |

**Why `offered` is the field that carries the weight.** Gap 4 built `_prefer_contradicted`
specifically so that *we looked and found against it* could never be reported as *we never looked*.
These are three different sentences to a person, and collapsing them at the boundary would undo
that at the last inch:

```text
not_evaluated        we have no evidence about this
contradicted         we have evidence against it
single_weak_signal   the evidence is real but too thin
```

**What each consumer then holds.** Export keeps the row present with a non-numeric refusal in the
value slot, so no total can absorb it and a downstream reader either handles it or breaks visibly.
The narrator receives something it structurally cannot render as a figure, and
`HEALTHCARE_FAILURE_SEMANTICS.md` already governs what happens next — *say* is templated and **may
name the gap without explaining it**, and the narrator may always say less than the return value
supports and never more.

**Still downstream and deliberately unanswered:** whether a refusal is visible to the user, and
with how much of its reason. Showing `offered` means telling someone *we have evidence against
this*, which is a teaching decision rather than a model one.

### Q2 — CLOSED and IMPLEMENTED; multi-source pending

**Not** *should contradictions be remembered* — that is settled: they may not silently disappear.
The open question is narrower:

> **After conflicting evidence is resolved, what historical representation survives, and what
> claims may subsequently use it?**

At least two materially different contracts satisfy the requirement:

```text
A   current fact = health
    history      = EOB contradicted user, later resolved

B   current fact = health
    provenance   = the supporting evidence for the present conclusion only
```

**A preserves the event of the disagreement. B preserves only the chain behind the current
conclusion.** Those are different capabilities, not different phrasings, and the evidence-tie
fixture has found the defect without telling us which contract is correct.

**No mechanism until it does.** In particular, *every conflict becomes `CONTRADICTED` forever* is
one possible reading of A and is not derived from anything.

> **Histories run 2026-09-11 — `gw 2.0/RESOLVED_CONFLICT_CASES.md`.** Six evidence histories
> against the shipped module, each answered against the five questions by locating where the
> answer lives. **Both contracts already exist, at different layers.** The determination chain and
> the current determination's evidence tuple preserve the conflict, its sequence and what resolved
> it — questions 1–4 are answerable today from the record with no new concept. What fails is
> question 5: `strength_of` reads the current state and nothing else, so H2 (EOB:not → user:health)
> and H1 (user:health, never opposed) are both rank 3 and both deliver the number.
>
> **This relabels the failure.** Not history loss — *summary loss over an intact record*, the same
> shape as sensitivity dying at rendering and the refusal never reaching the consumer before Q1.
> **This codebase's recurring defect is holding information that does not travel.**
>
> **Three findings forced.** Rank 3 is a ceiling that absorbs every history — an independent
> second source confirming after a conflict (H5) ranks identically to a bare unopposed statement
> (H1) and to recency alone (H2); **resolution kind is not a strength**, and encoding it as one
> needs headroom the lattice was never built to have. Reaffirmation (H4) is invisible, and gap 4's
> dedup-by-source-identity makes that probably correct. And an external contradiction (H3) and a
> self-correction (H6) are one state, `contradicted` — noticed, adjacent, not pursued.
>
> **Answered 2026-09-11 (Rob's): beside it.** *A resolved conflict travels beside the value and
> does not alter its strength.* The invariant: **resolution metadata describes how the current
> determination was reached; it does not constitute evidence for it** — so *was previously
> contradicted* can never become a strength. Vocabulary still to be scrutinised; presentation
> separate, as in Q1.
>
> **And the reaffirmation challenge was tested rather than blessed.** A probe over the chain
> distinguishes *none · superseded · reaffirmation · self_reversal* from data the module already
> keeps, with resolver and contradiction count beside them — so the earlier *reaffirmation is
> invisible* was wrong at the record layer. **What the probe proved unreachable is independent
> confirmation**: with two knowing source identities, a second agreement after a conflict is
> always a reversal by one of them, and the record cannot tell one EOB re-read from a different
> EOB because `IMPORTED_EOB` is a type, not a document. **That is finding 3's gap, not a Q2
> mechanism.** Derived on read, never stored — gap 4's rule, same reason.
>
> **Settled 2026-09-11 — `RESOLVED_CONFLICT_CASES.md` §"Q2 — settled".** *Resolution metadata is a
> read-time projection of the evidence chain — `kind`, `resolver`, `contradictions`, `post` — where
> the resolver is the event that made the current conclusion current. It travels beside the value
> and strength and never becomes evidence itself.* Checked against **every history to length 6,
> 5,460 of them**, under five properties, all holding — including that appending an agreeing event
> never rewrites the resolution. Rob's second adversarial case found that the earlier probe named
> the *last* event as resolver, which is wrong on **42%** of histories; nine hand-picked cases sat
> where the definitions coincide. `post` was added because without it the user's concession after
> being overridden by a document is invisible again. Two boundaries recorded: **source type ≠
> source instance**, and **agreement on a negative is not positive evidence** — a property of the
> determination, not a fifth kind. Contradiction count is history, not confidence.
>
> **Closed 2026-09-11 (Rob).** Contract: `resolution = kind · resolver · contradictions · post`,
> all four derived from the evidence chain at read time. Two negative boundaries that must not
> quietly become implementation assumptions: **source type ≠ source instance**, and **agreement on
> a negative ≠ positive evidence**. And the property the enumeration made load-bearing: **a
> resolution is a fixed historical event** — later agreement never rewrites why the current
> determination became current.
>
> **The projection-boundary fixture is written, before the projection —
> `tests/test_resolution_projection_fixture.py`.** Q1 proved a refused value cannot bypass the
> boundary; this has to prove the other half: *every consumer permitted to receive the value
> receives the resolution with it, and no consumer can manufacture a resolution from the value
> alone.* The dangerous case is the ordinary permitted rank-3 result — `value = 1250, rank 3` —
> from which a consumer cannot tell *never contradicted* from *contradicted → resolved* even
> though the model can. The oracle is embedded (the definition that survived 5,460 histories),
> `--exhaustive` re-runs that enumeration against the implementation, and today the fixture
> prints its specification, checks its own oracle against the table, and reports every
> projection assertion pending.
>
> **One row in the table as handed over was wrong, and it is the bug's shape.** `U:y → E:n → U:y`
> was given `post = U`. The final `U:y` **is** the resolver; nothing follows it; `post` is empty.
> `post` is non-empty only when something agrees *after* the resolving event. Encoded the other
> way, the resolver would sit in `post` and the off-by-one would be back. Corrected in the fixture.
>
> **Q2 IMPLEMENTED 2026-09-11 — `resolution(c, axis)` in `core/classification.py`.** A read-time
> projection of the chain and deliberately nothing more: it does not evaluate evidence, rank
> sources, or compute confidence. Constants `RESOLUTION_NONE · SUPERSEDED · REAFFIRMATION ·
> SELF_REVERSAL` beside the evidence states. `NarratorFacts` gains a `resolution` field;
> `export_row` a `resolution` key; both via `_fact_resolution`, which carries a single source's
> content-axis resolution and returns `None` for several sources — **multi-source stays
> unspecified, and the helper is explicitly not a fold.**
>
> **Verified in the sequence set out:** the ordinary fixture, 28 passed / 0 failed / 1 pending
> (the expected multi-source pending); `--exhaustive`, **all 5,460 histories match the oracle**;
> and mutation — `smoke_sections/s98_resolution_projection.py`, **10 of 10 caught**, every
> mutation checked against the full enumeration (it runs in half a second), the expected pending
> tracked **by name** so the section fails if multi-source is ever specified silently. The
> seeded defects: the 42% resolver bug, the off-by-one that puts the resolver in `post`,
> reaffirmation by *ever stood for* rather than most recent stance, an undercounted
> contradiction count, `post` always empty (the concession vanishes), a resolution constant
> across H1 and H2, each consumer dropping it, **a resolved conflict demoting strength**, and a
> resolution carrying a strength of its own — the last two being the two ways a projection
> quietly becomes a second evidence evaluator. **Gate 833 → 846.**
>
> **The tie fixture re-pointed, not deleted.** It was a discovery instrument and it found the
> defect. Two of its assertions demanded an order-independent *state*, which Q2 deliberately
> rejected — the state resolves by recency among equals and the history travels beside it. Those
> are retired in place with the reason, and the requirement they reached for — *the disagreement
> remains visible afterwards* — is asserted against `resolution()`, where the design put it. **8
> passed, 1 failed**: the remaining failure is the temporal one, latent, unchanged, and correct.
>
> **Q2, characterised (Rob, 2026-09-11):** *implemented projection, validated against the complete
> finite history space, with consumer propagation enforced and unresolved multi-source semantics
> explicitly left unspecified.* The number moving 833 → 846 is not the evidence; 10 of 10
> mutations caught over the exhaustive oracle is. Two things are **not** to be "fixed": the
> multi-source pending — making it pass by inventing semantics is the pressure that creates
> accidental doctrine — and the temporal failure in the tie fixture, which is projection
> correctness kept separate from temporal semantics nobody has settled.
>
> **The next subtle failure is not in `resolution()`.** It is in whether any downstream consumer
> can interpret the four fields in a way that **recreates an implicit confidence ranking** —
> `contradictions` read as a score, `superseded` treated as weaker than `reaffirmation`, `post`
> length taken as corroboration. Two forms are already refused by s98 (a resolved conflict
> demoting strength; the projection carrying a strength). The rest cannot be tested yet, for a
> structural reason: **`core/classification.py` has no consumer outside its own fixtures**, so
> the risk sits in the first narrator or export wiring, not in anything that exists. When that
> wiring arrives, the consumer-boundary fixture's level-3 scan is the place to extend — an
> application read of a resolution field inside a comparison or sort is the shape to refuse.
>
> **The question narrowed:** *should a resolved conflict affect what a consumer receives, and
> through what — the strength, or something carried beside it?* Four answers with costs. Demoting
> (ii) **penalises evidence** — a user who corrected a wrong EOB ends weaker than one who never
> imported it. Ranking the resolution (iii) is a lattice change. **Carrying the conflict beside the
> value (iv), strength untouched**, is the one consistent with the last three fixes of this shape,
> and it leaves *what exactly travels* — overridden · by recency or reaffirmation · by independent
> confirmation — as the decision, which is Rob's.

**And the gate stays green until then.** A red gate is useful once the desired behaviour is
defined; right now the fixtures are working correctly as discovery instruments, and a red gate
that nobody can act on is a gate people learn to ignore.

### Q1 IMPLEMENTED — `core/classification.py`, and the guard is permanent

**The change is two functions and one helper.** `narrator_facts` and `export_row` call
`_permitted_value(derived, consumer)`, which returns `refusal(...)` when it is not None and
`consume(...)` otherwise. `refusal()`, the lattice, Q2 and presentation semantics are untouched,
and no entry was added to `CONSUMER_STRENGTH`.

**Verified in the three ways the review asked for:**

| | |
|---|---|
| **behavioural** | a `single_weak_signal` fact returns the refusal to `narrator` — `{consumer, reason, required: corroborated, offered: single_weak_signal}` — and a `corroborated` fact still returns `1250.00`. A `contradicted` fact returns the refusal to `export`, in the value slot, with the row intact |
| **structural** | the AST scan finds no `<param>.value` read outside `consume()`. Fixture **17 passed, 0 failed** |
| **mutation** | the bypass reintroduced in both functions, together and separately — **3 of 3 caught**, file restored |

**The fixture was strengthened in the process, and it needed it.** Its original assertion was
`narrated.value != weak_fact.value`, which **anything** satisfies — including the `None` that Q1
rejects specifically because a blank cell is a zero. It now asserts that the value slot holds the
refusal, that all four fields are present, and that `offered` names *which* strength, so
`contradicted` stays distinguishable from `not_evaluated` at the boundary.

**And the mutation is now permanent rather than a thing that was run once** —
`smoke_sections/s96_consumer_boundary.py`, following s95's shape. Six mutations, all caught:

```text
narrator_facts reads the value directly, as it did before Q1
export_row reads the value directly, as it did before Q1
a refusal is reduced to a bare sentinel and loses why
a refusal becomes None, and a blank cell is a zero
a refusal no longer names which strength was offered
the boundary refuses a consumer that is entitled to the value
```

**The first two are the shipped pre-Q1 state, seeded as defects.** Three of the others are the
alternatives Q1 rejected — *a rejected design that is never tested against is a decision nobody
can tell was made.* **The last runs the other way** on purpose: a boundary that refuses everything
satisfies every refusal assertion ever written, so the fixture has to notice an entitled consumer
being denied.

The assertion the guard protects is not *refusal works*; it is **the consumer cannot obtain a
refused value through any other path** — gap 6's lesson at the mutation level, since a boundary
test that only ever sees the compliant implementation cannot tell a working boundary from a stub.

**Gate: 824 → 833 passed, 0 failed.** The consumer-boundary work is now inside it. The tie fixture
stays outside, because Q2 is open and its failures are still findings.

**One thing found and deliberately not fixed:** `backup` is **not** in `CONSUMER_STRENGTH`. It
borrows export's declared strength by delegating to `export_row`, so a consumer that never declared
what it requires is served anyway — a third, quieter instance of the same pattern. Giving backup its
own entry is a decision about what a backup may contain, and Q1 was not that decision. Recorded in
the code beside the delegation.

### The end-to-end test to add after the design lands

```text
weak evidence → derived fact → consumer refuses
        ↓  strengthen the evidence
same underlying fact → consumer now permits
```

The assertion that makes it worth writing: **permission changed because the evidence changed, not
because a consumer happened to call a different accessor.** That is the one test that runs the
whole chain — evidence → fact → permission → consumer — and it ties this defect directly back to
the weakest-link work in gap 4, which is where the boundary was supposed to have been closed.

---

## What has not been done

No implementation, no schema, no new state added to the lattice, no consumer added to
`CONSUMER_STRENGTH`. **No doctrine touched** — `carrier` is untouched, disposition scope is
untouched, and nothing here decides whether the miss-log exists in 2.0.

Two of the ten findings are **tests rather than mechanisms** (9, and the tie state in 1), and those
should be attempted before anything is designed, per the standing rule against reaching for a
mechanism the moment a review admits that failures are possible.
