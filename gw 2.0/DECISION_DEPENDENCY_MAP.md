# Decision dependency map — the ten decisions, and what the cases say about how they touch

> Status: **Map, 2026-09-12. No decision is made here.** Every arrow cites the case document
> that established it; an arrow with no citation is not on the map. The board this is drawn from
> is the one recorded at `b2ba294`: one live defect repaired, five below the line, three
> modelling gaps, one operation gap, one projection gap, one boundary, and ten decisions — all
> Rob's. His reading of that board is the frame: *Groundwork's remaining problems are about what
> information it chooses to preserve and what it is permitted to say, not failures of arithmetic
> or basic evidence handling.*

**What this map is for.** The ten were reached one case at a time, in different documents, and
some of them will not hold still while another is answered. The map records *which* ones, and
in what way — so that they can be taken to the cases as clusters rather than answered in the
order they happened to be found. **It is not an implementation order**, and the arrow vocabulary
below exists to keep it from becoming one by accident.

---

## 0. Arrow vocabulary — gates and constraints are different claims

Rob's requirement for the map: distinguish a gate from a constraint, or the map will start
implying that one decision has authority over another when the cases establish nothing of the
kind.

| Arrow | Claim | What it says about B's answer | Evidence required |
|---|---|---|---|
| **A gates B** | B cannot be *posed* — has no content — until A is answered | nothing | a case where B is contentless without A |
| **A constrains B** | A's answer narrows B's admissible answers | some answers to B become inadmissible | a case where a specific answer to A rules out a specific answer to B |
| **A ↔ B** | both directions constrain | as above, both ways | one such case in each direction |
| **A = *x* forecloses B-branch** | one *particular* answer to A removes one branch of B | that branch | a case showing the branch is unreachable under A = *x* |
| **A ──X──► B** | tempting, and no case supports it | nothing | recorded so it is not assumed |
| **A ──?── B** | *interaction* — they touch, and no case has established a dependency of any kind | nothing | none yet; the row exists so the relationship is not upgraded silently |

A gate is an ordering claim only. It says B waits; it says nothing about what B should be. A
constraint is the opposite: both questions can be posed today, neither must go first, but they
cannot be answered independently. **Most of what the cases established is constraint, not
gate**, which is the finding — the ten are entangled, and they are not a hierarchy.

Foreclosure is the one that matters most and was not in the first draft. It is the asymmetric
case: a representation decision cannot *grant* a downstream permission by answering yes, but it
can *remove* a downstream branch by answering no, because information that is not carried cannot
be re-derived later (`HEALTH_TRUST_BOUNDARY.md` §9: sensitivity "has to have been attached
upstream rather than re-derived"). This codebase's recurring defect is *information that does
not travel* (`RESOLVED_CONFLICT_CASES.md`), and a foreclosure arrow is that defect drawn as a
dependency before it happens.

---

## 1. The ten (and the eleventh)

| # | Decision | Recorded in |
|---|---|---|
| 1 | **§7.7 *carries*** — four dimensions (funded · serviced · bears risk · entitled to collect); `carrier` is a deletion candidate, not a term to define | `OBLIGATION_LIFECYCLE_QUESTION.md` |
| 2 | **Disposition scope** — does a disposition describe the obligation, or the creditor's books? Bad-debt write-off is the boundary test | `DISPOSITION_VOCABULARY_CASES.md` |
| 3 | **F3 fork** — narration carries sensitivity from the point a figure becomes a sentence, or the miss-log cannot exist in 2.0 | `HEALTH_TRUST_BOUNDARY.md` §9 |
| 4 | **Document referent** — bytes held vs identity asserted; artefact ≠ file | `DOCUMENT_IDENTITY_CASES.md` |
| 5 | **Proposition space** — does it open beyond the boundary question at all | `VALUE_DISAGREEMENT_CASES.md` |
| 6 | **Verdict strength** — separate from support-for-a-proposition | `VALUE_DISAGREEMENT_CASES.md` |
| 7 | **Period-close shape** — a new operation, or a narrower correction | `HISTORICAL_TRUTH_CASES.md` |
| 8 | **Overlap policy** — refuse, or represent-and-report | `HISTORICAL_TRUTH_CASES.md` |
| 9 | **`NarratorFacts` carries `Sensitivity`?** — representation | `SENSITIVITY_TRACE_CASES.md` |
| 10 | **Export carries `manufactured`?** — representation, *if export needs the distinction* | `SENSITIVITY_TRACE_CASES.md` |
| 11 | **May a manufactured suspicion ever be voiced?** — permission ≠ representation | `SENSITIVITY_TRACE_CASES.md` |

---

## 2. The arrows, each with its evidence

### 5 gates 6 — and explicitly does not constrain it

Verdict strength has no content unless the proposition space opens: while the only proposition
is the boundary question (*is this inside the health zone?*), the lattice ranks support for that
one proposition and there is no separate verdict to be strong about. `VALUE_DISAGREEMENT_CASES.md`
poses 6 conditionally — *"whether the proposition space opens at all, **and if so** whether the
lattice's meaning of strength changes with it."* That is a gate.

The same document then forbids the constraint reading: *"Those are two decisions and **the
second must not ride on the first**."* So: 5 decides whether 6 is asked; 5 does not decide what
6's answer is. Rob's example is the gate in one picture — three sources say *yes* to *P: insurer
covered service X*, and the strength of that verdict is undefined until P is a thing the record
can hold.

**6 ──X──► 5.** Nothing about how strength should work tells you whether the space should open.

### 4 ↔ 5 — mutual constraint, no gate

Each answers a different question and they meet at evidence:

```text
proposition space    what claim exists?
document referent    what thing, if any, is evidence about — or attached to — that claim?
```

- **5 constrains 4.** `$412` re-parsed as `$4.12` registers *no disagreement* today, because both
  readings say *health* and there is no value proposition to disagree about
  (`VALUE_DISAGREEMENT_CASES.md`). Opening the space is what creates the dispute — and a dispute
  between two readings of one artefact is exactly what a referent has to be able to hold.
- **4 constrains 5.** Once that dispute exists, *"which reading is right is a parse dispute
  (document identity) and not something position or recency should answer"* — so what 5 can
  truthfully resolve depends on what 4 lets the record distinguish. `DOCUMENT_IDENTITY_CASES.md`:
  with `IMPORTED_EOB` as the identity of every EOB ever imported, one EOB twice ≡ two EOBs, and
  `resolution()` reports a re-parse as *self_reversal by imported_eob* — a wrong causal story
  faithfully projected.

Neither gates the other: both are posable today, and both case sets were written without the
other being answered. **Do not collapse them into one model because they meet at evidence** —
the DI boundaries (*document identity ≠ obligation identity*; *source instance ≠ source
independence*) are there to keep them apart.

**5 ──X──► 4 as a gate. 4 ──X──► 5 as a gate.**

### 1 ↔ 2 — mutual constraint, and neither is to be finalized alone

The bad-debt write-off is the case where they meet. Writing an amount off the books does not
establish that the obligation was extinguished — so *what disposition means* (2) depends on
which party's fact it describes, and *which party* is §7.7's question (1): the entity whose books
changed and the entity entitled to collect can be different entities. `DISPOSITION_VOCABULARY_CASES.md`
records finding 5 as *depending squarely* on obligation-vs-books, and case 8 — transfer to an
agency — as **not expressible**: that is the write-off meeting the fourth *carries* dimension
(legal entitlement) and finding no representation.

- **1 constrains 2:** a *carries* answer with entitlement separate from servicing makes
  "the creditor's books" ambiguous — *which* creditor — and narrows what disposition scope can mean.
- **2 constrains 1:** answering "obligation" (as opposed to books) is a claim that the household
  has a single counterparty whose obligation it is — which is a claim about *carries*, and the
  recourse case (`OBLIGATION_LIFECYCLE_QUESTION.md` §9: the provider takes the account back on
  default) says that counterparty can change without the household doing anything.

Rob's fence, kept: not to be decided by which produces the cleaner API. The write-off is the
adversarial case that should decide it, and it constrains both.

### 1 gates the recourse case → M1/M2 → schema

Recorded as a rule, not an arrow, at the top of `LIFECYCLE_REVIEW_TRIAGE.md` and §9 of
`OBLIGATION_LIFECYCLE_QUESTION.md`:

```text
funding/servicing/risk → doctrine → "carrier" definition → lifecycle semantics → M1/M2 → schema
Nothing downstream may be used to settle an upstream semantic question.
```

This is the one genuine multi-step gate on the board. M1/M2 is *stopped*, not pending: a choice
now would rest on a definition of *carrier* the recourse case shows does not exist. Neither
M1/M2 nor the schema is among the ten; they are consequences.

### 1 ──X──► 5 — not established

§7.7 potentially determines what a financial fact is *about* across the four dimensions, and a
proposition about *who bears this obligation* would live in the proposition space. But the cases
have not shown that *carries* **defines** propositions — it may equally be a property attached
to a proposition the space already holds. `DOCUMENT_IDENTITY_CASES.md` keeps *obligation
identity* unresolved by default and outside both document identity and the proposition work,
which is where the two would have met if they were one.

This X is load-bearing. Without it §7.7 — already the highest-leverage decision on the board —
becomes the master abstraction by default, and the map would have decided that, not a case.

### 7 ↔ 8 — mutual constraint, no gate

*(Corrected from a one-way `7 → 8`. The argument for the arrow runs both ways.)*

- **7 constrains 8.** If the record cannot say *this plan was true until June 30, although we
  learned that later*, then overlap is the only state a late discovery can leave — so a
  period-close that does not exist forces overlap to be *representable* whether or not it is
  *permitted*. `HISTORICAL_TRUTH_CASES.md` T8: `close_period` is named in `DELETION_MODES` and
  does not exist; mutating `effective_to` directly rewrites the past.
- **8 constrains 7.** If overlap is admitted as *truthful evidence of unresolved history* —
  two plans claim August and Groundwork cannot establish which governed — then period-close's
  job is to resolve a represented state, not to prevent one. If overlap is refused, close must
  be able to prevent it at the point of entry. Different operation.

Neither gates the other. 7 is decided by whether *ended earlier* has **different provenance and
history semantics** from `correct_terms` — "not by whether the API reads better with three
verbs" — and that question does not mention overlap. 8 is decidable on C9's precedent (*ask
rather than manufacture the answer*, `APPLICABILITY_CASES.md`) without knowing 7's shape.
The two are one cluster because they constrain each other, not because one waits.

**7 ──X──► 8 as a forced answer.** Rob's original caveat, kept: 7 does not determine 8.

**From outside the ten, settled, and it constrains 7:** `OBLIGATION_LIFECYCLE_QUESTION.md`
rule 2 — *a discovered transition preserves both when the change became effective and when
Groundwork learned of it* — is already doctrine, and *was true, stopped being true earlier than
recorded* is the same operation in a different module. Whatever period-close is, it may not
collapse effective-at into learned-at. This is the reason cluster C is not isolated from the
rest of the board.

### 3 ↔ 9 — F3 constrains 9; 9 = no forecloses F3's first branch

*(Corrected from a one-way `3 → 9`. The reverse direction is a foreclosure, and it is the
sharper of the two.)*

- **3 constrains 9.** If F3 is answered *keep the miss-log*, narration must carry sensitivity
  from the point a figure becomes a sentence — and the figure becomes a sentence *from*
  `NarratorFacts`. So that branch of 3 requires 9 = yes. If F3 is answered *no miss-log in 2.0*,
  9 is unconstrained by F3.
- **9 = no forecloses F3's first branch.** `NarratorFacts` has `includes_records = False` — the
  narrator does not secretly hold the evidence and cannot reconstruct what its contract excludes
  (`SENSITIVITY_TRACE_CASES.md`). `HEALTH_TRUST_BOUNDARY.md` §9: sensitivity has to be attached
  upstream, not re-derived. So with 9 = no, there is no sensitivity at the point the sentence is
  built, and F3's *carry it* branch is not a choice any more. The F3 fork would have been
  answered by a representation decision that was not asked to answer it.

F3 does not itself say whether `NarratorFacts` should gain the field. Rob's separation holds:
F3 decides what must *survive* for its chosen behaviour; 9 decides the representation at the
boundary. What the foreclosure adds is that 9 is not free to be decided *after* 3 as if 3 could
then be decided on its merits.

### 9 ↔ 11 — a constraint on where enforcement lives, and an X on the policy in both directions

`SENSITIVITY_TRACE_CASES.md`: *"#3 does not follow from #1. Carrying the distinction does not
mean the narrator is permitted to say it."* That X stands. The map records the two things that
*do* connect them:

- **11 is posable and answerable with 9 unanswered.** *Never* is a complete answer to 11 and
  needs no field. And it is *enforceable* with 9 = no: Q1's `_permitted_value` refuses before
  `narrator_facts` is built (`s96_consumer_boundary.py`), so a refusal on sensitivity could sit
  where the refusal on strength already sits — at the consumer boundary, upstream of the narrator.
  **9 does not gate 11.**
- **What 9 constrains is the enforcement locus.** If 11's answer is anything finer than
  never/always — *voiced as uncertain, never as fact*, say, which is a B.2a register question —
  the narrator has to be able to tell `manufactured` from `asserted` from `absent` in its input,
  and that is 9 = yes. Conversely, if enforcement is placed in the narrator, 9 = no leaves it
  unable to enforce anything. **11's enforcement point constrains 9; 9 constrains where 11 can be
  enforced.**

```text
9  ──X──►  11   (policy)     carrying the distinction grants nothing
11 ──X──►  9    (policy)     "never" needs no field; it needs a boundary
9  ◄────►  11   (locus)      where the refusal lives decides whether the field must exist
```

The warning survives intact: **a representation decision must never smuggle in a permission
decision.** The locus arrow is not a loophole in it — the locus is an engineering question that
becomes answerable once the policy is stated, and the policy is Rob's.

### 10 — independent until a consumer says otherwise

The gap-11 case proves the distinction exists upstream and is lost at both helpers,
`narrator_facts()` and `export_row()`, in the same module. It does not prove export has a
requirement to carry it: `SENSITIVITY_TRACE_CASES.md` lists 10 as a representation decision
*"if export actually needs that distinction."* No export consumer has stated a need.

- **9 ──?──► 10** — possible interaction, not a dependency. The two helpers will likely share a
  mechanism, and a shared mechanism is not a dependency between decisions; treating it as one
  is the schema-settles-doctrine trap `LIFECYCLE_REVIEW_TRIAGE.md` recorded as a rule.
- **10 ──X──► 9.** Export carrying it says nothing about the narrator.
- **Who counts as export's consumer:** `backup` is not in `CONSUMER_STRENGTH` and borrows
  export's (found, left, recorded at Q1). Whatever consumer requirement eventually decides 10
  decides it for backup too, unless backup is given its own row first.

**Do not let "`NarratorFacts` lost it" become "export must carry it."** The two losses are the
same class in the same module and are still two decisions.

### 3 ──X──► 11 — not established

F3 is about what the miss-log may persist; 11 is about what the narrator may say. A miss-log
that carries sensitivity can hold a sentence the narrator was refused permission to say — that is
what a miss-log is for. Neither answers the other.

---

## 3. The map

```text
   CLUSTER B — identity                        CLUSTER A — meaning
   what can be claimed, and about what          whose fact is it

   4. document referent ◄────────► 5. proposition space  ◄──X──  1. §7.7 carries ◄────────► 2. disposition scope
                                        │                              │
                                        │ gates (not constrains)       │ gates
                                        ▼                              ▼
                                   6. verdict strength           recourse case → M1/M2 → schema   (stopped)


   CLUSTER C — time                            CLUSTER D — teaching boundary
   what was true when, and when we knew         what survives into a projection, and what may be said

   7. period-close shape ◄────────► 8. overlap policy    3. F3 fork ──── constrains ────► 9. NarratorFacts.Sensitivity
            ▲                                                 ▲                                  │
            │ constrains (settled, off-board)                 └──── 9 = NO forecloses ───────────┘
   discovered-transition rule 2                                     branch "carry it"
   (effective-at ≠ learned-at)                                                                   │
                                                              3 ──── X ────► 11                  │ locus only (X on policy)
                                                                                                 ▼
   INDEPENDENT                                                                11. voice a manufactured suspicion?
   10. export.manufactured  ──?──  9    (interaction, no dependency)
```

Read `◄────►` as *constrains both ways, neither gates*; `▼ gates` as *B has no content until
A*; `X` as *tempting and unsupported*; `──?──` as *interaction, no dependency established*.
Cluster D is deliberately **not** drawn with the symmetric arrow: 3 → 9 is an ordinary
constraint, and the return arrow is a foreclosure that exists only under one answer.

**What the map says.** Four clusters, one independent decision, and exactly one multi-step
gate (§7.7 → M1/M2 → schema, already recorded as a rule). Everything else is constraint. The
ten are entangled rather than ordered, which is why they could not be closed one at a time and
why *decision dependency, not another gap hunt* was the right call.

---

## 4. The negative results — arrows this map refuses to draw

```text
§7.7 carries          ──X──►  proposition space         (may be a property on a proposition, not its definition)
proposition space     ──X──►  verdict strength's answer (gates the question; "must not ride on the first")
proposition space     ──X──►  document referent, as a gate
document referent     ──X──►  proposition space, as a gate
period-close shape    ──X──►  overlap policy, as a forced answer
F3                    ──X──►  voice permission
NarratorFacts.Sens.   ──X──►  voice permission (policy)
voice permission      ──X──►  NarratorFacts.Sens. (policy) — "never" needs a boundary, not a field
export.manufactured   ──X──►  narrator representation
NarratorFacts.Sens.   ──X──►  export.manufactured (mechanism sharing is not dependency)
```

These are the map's most useful content. Each is an arrow a reasonable person would draw from
the shape of the code, and each would turn the map into an architecture proposal wearing a
dependency map's clothes.

---

## 5. What this map does not do

The mistake it exists to prevent, in one line (Rob's):

```text
dependency  ≠  implementation order  ≠  authority  ≠  semantic containment
```

Applied to the board: `5 gates 6` means strength cannot be settled until the proposition exists
— not that proposition space *owns* verdict strength. `4 ↔ 5` means referent and proposition
interact — not that they need one combined abstraction. `9` may constrain what F3 can do — it
does not decide what the narrator is permitted to say. `7 ↔ 8` means temporal semantics meet —
choosing 7 does not choose 8. And `10` stays independent because no case has established its
consumer requirement: one downstream representation losing `Sensitivity` does not establish that
every other downstream representation must preserve some other attribute.


- **It does not order the decisions.** The clusters are kinds, not tiers. "Permission last"
  was in the first draft and is withdrawn as a rule: permission should *operate* on a truthful
  representation, but the foreclosure arrow shows that deciding representation first can
  quietly answer permission — so the policy may need to be *stated* early precisely so that the
  representation cannot settle it by starvation. Whether it is stated early is Rob's; the map
  only records that nothing forces it late.
- **It does not say which answer is right.** No case in any cited document is resolved here.
- **It does not add decisions.** Three settled things from outside the ten appear because they
  constrain items on the board (rule 2 → 7; Q1's boundary → 9/11's locus; the M1/M2 stop rule),
  and one open question from outside is noted below because it touches 6 and 4 — it is not
  promoted onto the board by being noted.

**Adjacent, noted, not placed:** gap 15's **tie state** (`USER_STATED` and `IMPORTED_EOB`
deliberately equal at rank 3; `knowing[-1]` breaks the tie by position — `EVIDENCE_MATRIX.md`)
is a verdict-strength question and a referent question at once, and the pending multi-source
resolution test (`test_resolution_projection_fixture.py`, 1 pending by name) waits on 4. And
`EVIDENCE_MATRIX.md`'s *supersession is positional where the record is temporal* becomes live
the moment 7 introduces an effective-time distinct from recorded-time — a wiring condition on
Q2's resolver, not a decision.

**Next, per the sequence:** take the clusters to the cases — A to the write-off and recourse,
B to the re-parse, C to the late-discovered plan change, D to the two-CVS-rows case — and
find out where a cluster's answers are jointly constrained. Not to implement anything.
