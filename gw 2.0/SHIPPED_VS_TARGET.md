# The shipped system against the target — what exists under other names, what is conflated, what cannot be represented

> Status: **Build mode, second question, 2026-09-12. Comparison only — no migration, no
> alteration, no compatibility machinery.** Rob's question:
>
> > **Against the shipped system, which of these six semantic objects already exist under
> > other names, which are conflated, and which required distinctions are currently impossible
> > to represent?**
>
> **The rule for this record:** the comparison must be able to find that **one old table
> represents parts of several new objects**, rather than forcing the ontology into old
> boundaries. So it is done in the target's direction — each shipped structure is decomposed
> into the target objects it holds — and never by asking "which new table does this old table
> become."
>
> **The target** (`SMALLEST_SCHEMA.md`, PARTIAL): parties (built) · artefacts · readings ·
> utterances · propositions (kind · subject + state · content · as-of; second participant
> open) · the evidentiary relationship; correspondence a proposition kind; origin, strength,
> resolution derived.
>
> **What "shipped" means here:** the pure `core/` modules with no production consumers
> (`classification`, `payment_plan`, `plan_year`, `allocation`, `person`), the 2.0 tables
> nothing reads, and the 1.x tables that do run. All are in the room; their consumer status
> is noted where it matters.

---

## 1. Decomposition — every shipped structure that holds a piece of the six

Each row: the shipped structure → which target objects it contains → what it fuses → what it
cannot say.

### `Evidence(axis, source, supports, amount, recorded_at)` — `core/classification.py`

| target object | held as |
|---|---|
| **proposition** | `axis` + `supports` = *this transaction is health on axis X*, content = a bit. Kind fixed to two values. Subject implicit (the enclosing `Classification`). |
| **evidentiary relationship** | each row *is* one relationship (this source evidences this proposition) |
| **utterance or reading** | `source` — a *type* standing in for the source: `USER_STATED` is an utterance with no origin party recorded; `IMPORTED_EOB` is a reading with no artefact and no reader; `MERCHANT_MATCH` / `MCC` / `INFERRED` are readings by a process (**no party** — the positive fourth state, held as an enum value) |
| **artefact** | **absent** — `IMPORTED_EOB` names the kind, never the instance (DI, H4) |
| **party** | **absent** — origin is the channel enum (K5, H3 R2) |
| **evidence time** | `recorded_at` = import clock; **asserted-at / document as-of absent** (H3) |

**Fuses:** four target objects in one dataclass — proposition, relationship, source-event,
and (by enum) origin. **Cannot say:** which artefact; which reading of it; who asserted; when
it was true; that two rows are one artefact read twice; any value proposition (`amount` is
scope, not content — V4).

**This is the table the new model must not be made to resemble**, and the fence in
`SMALLEST_SCHEMA.md` §6 exists for exactly this comparison: `Evidence` rows are relationship +
proposition + source collapsed, and calling the new relationship table "the evidence" would
have invited a one-to-one mapping onto it.

### `Determination(axis, state, evidence, rule_version, determined_at)` and `Classification`

| target object | held as |
|---|---|
| **derived, not stored (target)** | `state` is `strength_of`'s input — a stored summary of the evidence chain, recomputed only by appending a new determination. The target derives it on read. |
| **provenance of derivation** | `rule_version` + `determined_at` — *which rule, when* — a legitimate **about**-provenance the target keeps (a reading by a process carries `reader_process`) |
| **subject** | the `Classification` (a transaction with merchant, MCC, category, date) — a **subject type** the target's proposition points at; `category_set_by` is the one place the shipped code records *who asserted* (user vs importer) — an origin, on the subject instead of on the claim |

**Fuses:** a proposition's subject with the evidence about it (the transaction carries its own
determinations). **Cannot say:** anything H3/H4 listed — and `category_set_by` is the shipped
system's only origin field, in the wrong place.

### `PdfExtractCache(source_hash PK, issuer, extracted_json, created_at)` — 1.x, running

| target object | held as |
|---|---|
| **artefact** | `source_hash` — identity **by bytes** (A1, rejected as identity; strong correspondence evidence) |
| **reading** | `extracted_json` — **one reading per artefact, by construction**; a re-parse cannot coexist (D3's limitation, exactly) |
| **origin, as a description** | `issuer` — a string the document says about itself: correspondence evidence, held as if it were the party (the encounter ruling's *second fact wearing the third's clothes*) |
| **encounter provenance** | `created_at` |

**Fuses:** artefact and reading (1:1 by key); description and origin. **Cannot say:** a second
reading; an asserted artefact; who the issuer *is*; that two hashes are one statement (scan vs
download). **The nearest shipped thing to an artefact store, and the clearest demonstration of
the ontology's three-way split.**

### `HistorianEntry` — the event substrate, running

| target object | held as |
|---|---|
| **utterance / reading, partially** | `event_category` values like `payment_confirmed`, `categorization_suggestion_confirm`, `recurring_pattern_confirm` are **household assertions** — utterances — recorded as typed events with no proposition object and no origin party (the household is implicit) |
| **provenance of encounter** | `created_at`; FKs to `debt_account`, `category`, `healthcare_expense` — subjects, on the substrate rule (*every structural relationship in a foreign key*) |
| **content** | `context_json` — the opaque content the substrate question fenced from carrying structure |

**Fuses:** the *act* (utterance) with the *thing it was about* (subject FKs) with *what was
said* (JSON) in one row, without a proposition to separate them. **Cannot say:** what
proposition was asserted, at what strength; whether two events are one act. **But it is the
shipped system's only utterance-shaped store**, and its FK convention is the target's.

### `payment_plan.Entry(kind, amount, on, reason, reverses, recorded_at)` — pure

| target object | held as |
|---|---|
| **utterance** | every entry is a household assertion — *I paid $175 on Aug 3* — with `on` = **evidence time** and `recorded_at` = encounter: **the one shipped structure that already keeps the two apart** (H2 audit) |
| **proposition** | kind = payment / reversal / adjustment; content = amount; `reverses` = a **second participant** naming another entry — an *utterance-about-an-utterance* (the identity ruling's Case B shape), shipped |
| **subject** | the plan — implicit |
| **origin** | absent (the household, implicit) |
| **what it cannot hold** | P-ack — the entitled party's acknowledgment (H2): no utterance whose origin is E can enter |

**Fuses:** utterance and proposition in one entry, with the right times. **Closest to the
target's utterance of anything shipped**, missing only an origin and a separable proposition.

### `plan_year` — `Plan`, `TermVersion`, `Operation(kind, seq)` — pure; and the 2.0 tables `HealthPlan`, `HealthPlanTermVersion`, `HealthPlanOperation`

| target object | held as |
|---|---|
| **subject** | the plan — a subject type |
| **utterance + proposition** | a `TermVersion` is a household assertion of terms; an `Operation(kind = change \| correction)` is the **provenance kind** the period-close ruling said needs a third value (*ended*, *resolved*) |
| **evidence time vs encounter** | `effective_from/to` vs `seq` — the two axes, present; but *ended earlier than recorded* has no operation (T8) |

**Fuses:** assertion, proposition and provenance kind into versioned rows — a reasonable
projection, missing origin and the third kind. **Cannot say:** who asserted a term; that two
plans' periods overlap as a *represented* state (H1 refuses now; the target represents it as
competing propositions of one kind and subject).

### `ExpenseObligationVersion(amount, effective_seq, recorded_seq, supersedes_id)` and `ExpenseDetermination(status, amount, evidence: String(80), …)`

| target object | held as |
|---|---|
| **proposition** | *the obligation's amount is X* — a value proposition, versioned |
| **evidence time vs encounter** | `effective_seq` / `recorded_seq` — **the dual pattern, shipped** |
| **supersession** | `supersedes_id` — the *B supersedes A* relation as a column pointer (the target: a proposition of a correspondence-adjacent kind) |
| **evidentiary relationship** | `ExpenseDetermination.evidence` — **a `String(80)` label**: the relationship reduced to a name (H4's finding on the persisted side) |

**Fuses:** proposition with its provenance times (fine) and with its supersession (a pointer
where the target has a claim). **Cannot say:** what evidence, from which artefact, by which
reading, established the amount.

### `ExpenseFundingAllocation(funder, amount, mode, source, cleared, attached, user_confirmed, duplicate_of, occurred_on, effective_seq)`

| target object | held as |
|---|---|
| **utterance + proposition** | an allocation is a household assertion of *who funded what*; `mode` and `source` are provenance kinds |
| **the acknowledgment states, partly** | `attached`, `cleared`, `user_confirmed` — three booleans that are **the ruled sequence's stations** (attached → acknowledged) *minus the entitled party*: `user_confirmed` is household confirmation, which the acknowledgment ruling separated from E's acknowledgment (K6: a cleared payment is not acknowledgment) |
| **correspondence** | `duplicate_of` — a *this is the same as that* claim held as a column, not a proposition |
| **evidence time** | `occurred_on` vs `effective_seq` |

**Fuses:** the most target-shaped shipped row outside `Entry`, and the one that shows how the
ruled acknowledgment sequence was *almost* reached with booleans and then stopped one party
short.

### `parties` — built to the rulings

The only shipped structure that decomposes into exactly one target object.

### Strings that are descriptions held as parties

`Account.institution`, `DebtAccount.name`, `PdfExtractCache.issuer`, `HealthPlan.name` — each
is **correspondence evidence for a party** held as though it were the party's identity. The
target's institution branch has none of these on the party; they are utterance content.

---

## 2. The answer, in the three parts Rob asked for

### Which of the six already exist under other names

| target | shipped, under another name | fidelity |
|---|---|---|
| **party** | `parties` (household); institution — **nowhere**, strings only | exact for household; absent for institutions |
| **artefact** | `PdfExtractCache.source_hash` (bytes as identity); `IMPORTED_EOB` (a kind as an instance) | identity by the wrong basis; asserted artefacts absent |
| **reading** | `PdfExtractCache.extracted_json` (one per artefact); every `Evidence` row with a process source | present, capped at one per artefact; no reader |
| **utterance** | `payment_plan.Entry` (with both times — the best); `HistorianEntry` confirm-events; `TermVersion`; `ExpenseFundingAllocation`; `Evidence(USER_STATED)` | present in five places, never with an origin party, never separable from its proposition |
| **proposition** | `Evidence.axis + supports` (two kinds, one bit); `ExpenseObligationVersion.amount`; `Entry.kind + amount` | present as fields on the evidence or the subject; never as its own object; **no value proposition in the health model** |
| **evidentiary relationship** | each `Evidence` row; `ExpenseDetermination.evidence` as a `String(80)` | present as the row itself or as a label |
| **correspondence** | `duplicate_of`; `supersedes_id`; `PersonAlias` (the one shipped correspondence-as-assertion, for persons) | present as pointer columns and one proper relation |

### Which are conflated

Four fusions, each named already by a ruling and now located in a table:

```text
proposition + relationship + source        Evidence               (H3, H4)
artefact + reading                          PdfExtractCache        (D3)
description + origin                        issuer / institution / name strings   (K5, encounter ruling)
utterance + proposition + subject           HistorianEntry, Entry, TermVersion, ExpenseFundingAllocation
```

And one **beneficial** conflation the target keeps: `Entry` and `ExpenseFundingAllocation` fuse
evidence time with the assertion — which is right, because for an utterance they are the
same event (the primitive ruling).

### Which required distinctions are currently impossible to represent

Not "hard" — **impossible**, because no shipped field can hold them:

1. **Two readings of one artefact** (D3) — `PdfExtractCache` is keyed by hash; `Evidence` has no
   artefact.
2. **An asserted (never-held) artefact** (R-ASSERT) — nothing can be an artefact without bytes.
3. **Origin as a party, distinct from channel** (K5) — origin is an enum everywhere except
   `category_set_by`, which is on the subject.
4. **A document's own date as evidence time** (H3) — `Evidence.recorded_at` is the import
   clock; only `Entry.on` and the `*_seq` pairs keep the axis, and not for documents.
5. **A value proposition on a health record** (V4) — `amount` is scope.
6. **The entitled party's acknowledgment** (P-ack) — no utterance can have E as origin.
7. **An institution as a party** — no identity exists; strings only.
8. **Subject *not established, with candidates*** — every FK is populated or NULL, and NULL
   means nothing in particular (the `PARTY_ID = NULL` collapse, everywhere).
9. **A claim about an utterance** (Case B) — `Entry.reverses` is the sole instance, and it is a
   pointer, not a proposition.
10. **Independence by lineage** (T-B) — `distinct = {e.source}` is the only independence the
    shipped code computes, and it is by type.

Ten, and none is a bug in a function — each is a field that does not exist because the object
it belongs to does not exist.

---

## 3. What the comparison establishes for the build — findings, not decisions

- **The shipped system is not wrong about *what*; it is wrong about *where*.** Nearly every
  target object is present somewhere, usually fused with its neighbour. The build is a
  *separation*, not an invention — which is why the target could be derived from cases the
  shipped code already passes.
- **`payment_plan.Entry` and the `*_seq` pairs are the shipped precedents for the utterance's
  two times.** The target does not introduce a new idea there; it generalises one the code
  already has in two places.
- **`PersonAlias` is the shipped precedent for correspondence-as-assertion.** The target's
  correspondence kind is that relation, generalised beyond persons.
- **`HistorianEntry`'s FK convention is the target's subject convention** (shape (i) in
  `SMALLEST_SCHEMA.md` §5), and its `context_json` is exactly the opaque `content` the target
  gives an utterance — the substrate question already ruled what may and may not live there.
- **The four fusions are the four places a migration would have to *split* a row into two
  objects**, and splitting is where information is manufactured if done by inference (a
  `PdfExtractCache` row does not say whether it was read once or twice). That is a build-
  sequencing fact: **new objects are populated from new encounters; old rows are decomposed
  only where the decomposition is a fact, not a guess** — the same rule the hazard audit
  applied to `accumulators`.

---

## 4. What this record does not decide

Any migration; which shipped structure, if any, is extended rather than superseded; whether
`PdfExtractCache` becomes the artefact store or is read as one; whether `HistorianEntry`
carries utterances or a new table does; the order in which the ten impossibilities are made
possible; anything about 1.x debt scope (still its own question). It also does not resolve the
two open representation choices in `SMALLEST_SCHEMA.md`, though it adds one piece of evidence
to each: the shipped FK convention favours subject shape (i), and `Entry.reverses` is a shipped
second participant held as a plain reference — evidence that an explicit slot has precedent,
not a decision that it is right.

---

## 5. Decision remaining — Rob's

Whether the comparison is accepted as the map of shipped-to-target, with the ten
impossibilities as the build's definition of done and the four fusions as its decomposition
points. If so, the next question is the first that orders work: **which of the ten is made
possible first** — and the forced dependency already recorded (utterance before institution)
is the first constraint on that order.

---

## 6. Ruling — Rob, 2026-09-13. Accepted as the shipped-to-target map; the first build slice named.

*The decomposition shows the target is not inventing a parallel financial ontology; it is
separating concepts the shipped system has historically fused.*

**One distinction before ordering:**

> **The ten impossibilities are the acceptance targets; they are not necessarily ten
> independent build slices.** Some are consequences of the same primitive becoming available.

### The dependency graph the comparison yields

| target capability | requires first |
|---|---|
| utterance-shaped evidence | utterance primitive |
| value proposition on a health record | proposition + reading / evidence |
| document's own date | artefact + its date |
| two readings of one artefact | artefact + reading |
| asserted artefact | artefact + utterance |
| origin as a party | utterance + party |
| institution as a party | utterance + minting assertion |
| claim about an utterance | utterance + proposition |
| E's acknowledgment | proposition + appropriate parties / subject |
| subject not established with candidates | proposition + correspondence machinery |
| independence by lineage | the identity / provenance graph |

### First: make the evidence primitives possible

Not `Institution`, not `PdfExtractCache`, not even `Artefact`. The first slice is the smallest
operational substrate producing

```text
Party → Utterance → Proposition ← evidentiary relationship
```

with the ruled semantics intact — because an institution cannot be minted without an
utterance; an asserted artefact cannot exist without one; a claim about an utterance cannot
exist without one; the proposition is the utterance's target; proposition kinds determine
derived strength; and the evidentiary relationship connects propositions to utterances and
readings without making either cease to be evidence. **The first build is not one of the ten;
it is the primitive that makes several of them possible.**

### The sequence the ten then fall into

```text
1  evidence substrate        proposition · utterance · evidentiary relationship
2  artefact + reading         two readings of one artefact · document date · then asserted artefacts
                              (the first cannot be reconstructed from PdfExtractCache where history is absent)
3  institution anchor         minted through an existing utterance — the forced dependency honoured
4  correspondence             ambiguous subjects with candidates · artefact↔artefact · party↔party · lineage
5  higher-order propositions  claims whose subjects are utterances — ordinary propositions, not mechanisms
6  domain propositions        health value claims · E's acknowledgment · roles · obligations — instances
```

**The later ten are mostly tests of generality, not reasons to expand the ontology.**

### The build gate before moving from slice 1 to artefacts / readings

End to end:

```text
Person → makes utterance → has proposition (kind · subject · content)
                         → has evidence time
                         → has derived strength
```

and separately:

```text
same act            → one utterance
same proposition    → may be asserted by multiple utterances
false proposition   → remains representable
unresolved subject  → remains representable
```

No institution, no migration, no correspondence beyond what is strictly required to make the
primitive operational.

> **Ruled: the first build slice is the evidence substrate — proposition, utterance, and the
> evidentiary relationship that connects propositions to utterances / readings. It precedes
> artefact / readings and therefore institution. The ten impossibilities are acceptance tests
> over that substrate and its subsequent slices, not ten mandatory tables or ten sequential
> migrations.**

A build order without the order becoming a second ontology.
