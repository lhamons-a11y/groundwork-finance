# The smallest schema for the six semantic objects

> Status: **Build mode, first question, 2026-09-12 — PARTIAL, two fences applied on Rob's review
> (§11). A schema proposal is not permission to migrate, alter existing tables, or add
> compatibility machinery.** Rob's question:
>
> > **What is the smallest relational schema that can represent the six semantic objects and
> > their mandatory relationships, while preserving every distinction already ruled?**
>
> Not *how should the existing tables change*, not *what is convenient*, not implementation.
> Inventory only, per object: **identity · mandatory data · mandatory edges · cardinality
> (only where forced) · evidence vs structure · unknown / unestablished states · derived
> values excluded from storage.**
>
> **The gate, applied before normalisation or elegance:**
>
> > **Every semantic distinction that required a separate ontology object must remain
> > separately representable in the smallest schema.** If the smallest candidate puts
> > proposition content on an utterance, strength on a party, or minting evidence on an
> > institution row, it has failed — however simple.
>
> **Started from the six objects and their edges. Not from the shipped tables.** The one shipped
> piece already built to the rulings — `parties` — is used as given.

---

## 0. The six, and the one that turns out to be a kind

```text
Artefact · Reading · Utterance · Proposition · Party · Correspondence
```

Working through the inventory, **correspondence is a proposition** — the proposition ruling's
own inventory lists *arrival R corresponds to artefact X* as one, and the identity rulings
describe correspondence throughout as *a claim with strength*, i.e. something an utterance or
reading asserts. It needs no table of its own; it needs the proposition to be able to name **a second
referential participant**, which several other ruled propositions also need (*S serves P*,
*P is E of X at d*, *B supersedes A*). **How** that participant is represented — an explicit
slot, or kind-determined structure inside `content` — is left open (§5, §11). So the schema
has **five tables for six objects plus the evidentiary relationship**, and the gate is checked
in §8 to confirm correspondence remains *separately representable* — its semantics (strength,
never merges rows, never crosses foundations) are all statements about propositions of that
kind, and none is lost.

The shape, before the detail:

```text
parties        (built)                   artefacts ──owns──► readings
   ▲                                          ▲                 │
   │ origin                                   │ subject (+ any  │ asserts
   │                                          │  2nd participant)│
utterances ──evidences──► propositions ◄──────┘                 │
   │                         ▲                                  │
   └── minted_by (institution party) ◄── ... ◄── evidentiary relationship ◄──┘
                                          (proposition × {utterance | reading})
```

---

## 1. Party — built; restated so the inventory is complete

| | |
|---|---|
| **identity** | minted (`id`); household party anchored 1:1 to `people` (declaration); institution party is the minted identity itself |
| **mandatory data** | `id`; **household:** `person_id` (UNIQUE, → `people`); **institution:** `minted_by` (→ `utterances`) — the one evidentiary *pointer* an anchor carries, ruled |
| **mandatory edges** | exactly one anchor: `person_id` xor `minted_by` |
| **cardinality** | one `Person` ↔ one party (built, guarded); one minting utterance → one party (the utterance's cardinality question, next); a party ← many propositions, artefact origins, roles |
| **evidence vs structure** | the row is **structure**. `minted_by` is a reference *to* evidence, not evidence. **No name, no descriptors, no strength, no state** — descriptors are the minting utterance's content (ruled); display is derived |
| **states** | none on the party. The four states are states of *references to* parties (proposition subject; artefact origin) — relocated by the proposition ruling |
| **derived, not stored** | display name (from the minting utterance / later correspondence); anything about *what the party is* |

Change from the built slice: **one additive nullable column, `minted_by`**, for the
institution branch — the additive column the built docstring said would arrive. Exactly-one-
anchor stays a guard (SQLite cannot add a CHECK after creation).

---

## 2. Artefact

| | |
|---|---|
| **identity** | minted on encounter (`id`); held vs asserted is a *property* |
| **mandatory data** | `id` · `held` (bool) · `content_hash` (nullable — held only; **correspondence evidence, never identity**) · `as_of` (nullable — the artefact's own date, the temporal axis H3/the tie ruling said has no field today; absent for captures without a stated date) · `encountered_at` (when Groundwork first held or was told of it — the artefact's minting event, which for artefacts *is* the encounter, ruled) |
| **mandatory edges** | **asserted artefacts:** `asserted_by` (→ `utterances`) — an artefact Groundwork never held exists because the household asserted it (R-ASSERT), the same *under-a-claim* shape as an institution. **Held artefacts:** none — the encounter is the provenance |
| **cardinality** | one artefact → 0..n readings; asserted artefact → exactly one asserting utterance (guard) |
| **evidence vs structure** | `id · held · content_hash · as_of · encountered_at` are structure and encounter provenance. **Origin is not a column** — see states |
| **states — origin** | **derived, not stored.** The artefact's origin party is established by a *proposition* (kind: *origin-of-artefact*, subject: the artefact, second participant: a party) asserted by an utterance or a reading — contract C3: origin is asserted, with a chain, at a strength. Storing it as a column would be a stored summary of evidence that can drift from the claims that determine it — the tie fixture's lesson, and the same reason `resolution()` and `strength_of` are computed on read. The four origin states — established · not established (with candidates) · no party — are therefore **read off the origin propositions**, exactly as *governing plan* is read off plan claims (the concurrent-coverage ruling) |
| **derived, not stored** | origin and its state; supersession (a proposition: *B supersedes A*); "which readings agree"; independence |

**A consequence worth stating:** Rob's primitive-layer diagram says an artefact *carries* an
origin party when established. In this schema it carries it **by derivation**, not by column.
That is the smallest representation consistent with *origin is asserted* — and it is the one
place where a reviewer might expect a column and should find a proposition instead.

---

## 3. Reading

| | |
|---|---|
| **identity** | an observation event of one artefact (`id`) |
| **mandatory data** | `id` · `artefact_id` (NOT NULL) · `read_at` · **reader:** `reader_party` (nullable → `parties`; a household member transcribing) *or* `reader_process` (nullable text: parser name/version) — a reading by a process has **no party**, the positive fourth state, and it must be representable, not null-ambiguous: exactly one of the two is set (guard) |
| **mandatory edges** | → `artefacts` (owned by it, ruled) |
| **cardinality** | belongs to exactly one artefact; yields 0..n propositions through `evidence` — **zero is legitimate** (V6: the reading happened and the field was unreadable) |
| **evidence vs structure** | the row is an **event** — structure. What it *claims* is in `evidence` edges to propositions. **No content column:** a reading's content is the propositions it yields; raw extracted text, if kept, is an artefact of the reading (a held thing) and not the reading's identity |
| **states** | none on the reading |
| **derived, not stored** | "read twice, agreed" (two readings of one artefact with matching propositions); parse-dispute status (same kind + subject, differing content across readings of one artefact) |

---

## 4. Utterance

| | |
|---|---|
| **identity** | an assertion event (`id`) — the act |
| **mandatory data** | `id` · `origin_party` (NOT NULL → `parties`; a `Person`'s party today) · `asserted_at` (**evidence time** — when the party made it; nullable because *"sometime in March"* is an intrinsic coordinate that can be uncertain — noted in the identity ruling, not designed here) · `recorded_at` (NOT NULL — Groundwork's encounter; **about**, kept as a separate column so the two can never be conflated) · `content` (opaque text — **what was asserted**, intrinsic by the identity ruling) |
| **mandatory edges** | → `parties` (origin) |
| **cardinality** | asserts 0..n propositions through `evidence` — **zero is legitimate**: an uninterpreted utterance (P3) has content and no proposition yet; propositions are its *interpretation* (about) |
| **evidence vs structure** | the row is the **event plus its intrinsic content** — structure. Its links to propositions are the evidence. **No strength column** (derived, ruled); **no truth/resolution/retraction state** (about — later claims with the utterance as subject) |
| **states** | none on the utterance |
| **derived, not stored** | strength (origin × proposition kind); whether it is reaffirmed, contradicted, retracted (propositions about it); whether two rows are one act (a correspondence proposition) |

---

## 5. Proposition

| | |
|---|---|
| **identity** | minted when first asserted or read (`id`). **Not** unique on (kind, subject, content) — ruled; sameness beyond that is a correspondence claim |
| **mandatory data** | `id` · `kind` (NOT NULL — primary; the knowing relation is defined over it) · `subject_state` (NOT NULL: `established` · `not_established` · `no_subject`) · **subject** (populated iff established — see the open choices below) · `content` (opaque — what is claimed) · `as_of` (nullable — for dated kinds: a stance *as of d*, an entitlement *at d*; individuates the proposition, so it is a column and not buried in content). **A second referential participant** is required by several ruled kinds (*S serves P*, *P is E of X*, *B supersedes A*, *R corresponds to X*) — **whether it is an explicit `object` slot with its own state, or operand structure inside `content` whose semantics `kind` determines, is NOT decided** (Rob's fence, §11) |
| **mandatory edges** | the subject reference, **carrying its own explicit state**; any further referential participant carries the same explicit-state discipline *however* it is represented |
| **cardinality** | evidenced by 0..n `evidence` rows (a proposition with none is a *candidate* — e.g. offered by the surface, C9 — and may exist unasserted) |
| **evidence vs structure** | the row is the **claim-shape** — structure. Nothing on it is evidence; what supports it is in `evidence` |
| **states** | `subject_state` is **explicit; NULL follows from it, never the reverse** (the party-shape ruling, relocated), and the same holds for any second participant however represented. `not_established` may carry candidates — a *candidate* relation (proposition → party/artefact, several rows) rather than a placeholder subject |
| **derived, not stored** | truth · resolution · established-ness · strength · which utterances/readings support or contradict it · resolution kind (source-history vs reading-level, now computable because readings and utterances are distinct rows) |

**Two representational choices this record leaves open, deliberately.**

**(A) Referential-participant representation.** The semantic ruling gave a proposition *kind ·
subject · content* and left content opaque. Several ruled kinds name a second participant.
That establishes that propositions can express more than one referential participant; it does
**not** establish that the representation is specifically *subject + object* rather than
structured content whose operands `kind` determines. Making `object` a field would be the
same premature concretisation the proposition ruling avoided. **Open: an explicit second
participant slot, or kind-determined operands in `content`** — with the constraint that
either must preserve referential integrity and an explicit established/not-established state
for every participant that points into the record.

**(B) Subject shape.** A subject can be a transaction, an artefact, a party, an utterance, a
classification, an obligation, a plan — or the world / nothing. Two shapes preserve integrity
and the explicit state:

- **(i) one nullable FK per subject type** — the project's standing convention (*sprawl is the
  price of enforceability*), with the CHECK that at most one is set and `subject_state` saying
  whether any is;
- **(ii) a `subjects` anchor table** on the `parties` pattern — one `subject_id`, anchored to
  exactly one referable table, propositions FK to it.

Both keep *not established* a state and not a null. **(i) is what the schema convention says;
(ii) is what the party ruling did for the same problem.** Rob's caution — *subject must not
become a polymorphic FK on reflex* — is satisfied by either and violated by a `(type, id)`
pair, which is rejected on the `HistorianEntry` reasoning already recorded. Not chosen here.

---

## 6. The evidentiary relationship — *this proposition is evidenced by this utterance / reading*

Not one of the six as named; the **evidentiary relationship** the ontology set beside the
chain. **Utterances and readings are the evidence** — the settled semantics — and this table
records which of them evidences which proposition:

```text
utterance ─┐
           ├─ evidences → proposition
reading ───┘
```

The smallest schema needs it as a table because it is many-to-many and it carries the one
thing neither end owns. `evidence` may remain its eventual table name; its semantic role is
the relationship, and it must not be read as *the only thing that is evidence* — that reading
would set `utterance ≠ evidence, reading ≠ evidence, evidence = evidence`, and would poison
the comparison against the shipped `Evidence` dataclass before it begins.

| | |
|---|---|
| **identity** | one row per (source, proposition) assertion |
| **mandatory data** | `proposition_id` (NOT NULL) · `utterance_id` xor `reading_id` (exactly one — a CHECK at creation) |
| **evidence vs structure** | the row is the **evidentiary relationship** — referential in form (two foreign keys), evidentiary in meaning: it is the statement *X evidences P*. The evidence itself is the utterance or reading it names |
| **states** | none — a negative claim is a proposition with negative content evidenced here, not a `supports` flag (V3's *agreement on a negative* is then two evidence rows on one negative proposition) |
| **derived, not stored** | **strength** — `strength(edge) = knowing(origin(source), kind(proposition))`, weakest-link over the source's chain; recomputed on read, as `strength_of` is today |

---

## 7. Correspondence — a proposition kind, with its rules intact

`kind ∈ {artefact_corresponds, party_corresponds, utterance_corresponds, proposition_corresponds}`,
subject = term A, the second term represented per the open choice (A) in §5, content = the
basis (hash match · issuer id · description · *"yes, that's the one"*), evidenced by the
utterance or reading that asserted it. The ruled rules become checks on this kind:

- **never merges rows** — a correspondence is a proposition; `parties`/`artefacts` are untouched;
- **never crosses foundations** — `party_corresponds` between a person-anchored and an
  institution-anchored party is refused (guard);
- **strength** — derived like any edge; a hash match asserted by a process reading is strong
  by kind, a description match weak.

Separately representable: yes — a dedicated kind with its own guards, on the general
proposition structure. **Not a table; not collapsed.**

---

## 8. The gate — every ruled distinction, separately representable

| distinction | representable by |
|---|---|
| held vs asserted artefact | `artefacts.held`; `asserted_by` |
| artefact ≠ file | identity minted; `content_hash` is evidence |
| reading ≠ source; one artefact read twice ≠ two artefacts | `readings.artefact_id`; two rows under one artefact |
| parse dispute vs source conflict | two readings of one artefact vs readings of two artefacts, on propositions of one kind+subject — computable on read |
| asserted-at ≠ recorded-at | two columns on `utterances` |
| utterance ≠ its interpretation; uninterpreted utterance exists | `utterances.content`; zero `evidence` rows |
| one act recorded twice ≠ two acts | one `utterances` row; a second encounter is `utterance_corresponds` |
| proposition ≠ text; same text, two propositions; two contents, one proposition | `propositions` rows independent of `content` text; V4 = two propositions? — **no**: V4 is one kind+subject with two readings asserting *different propositions of the same kind and subject* — the dispute is computable and nothing is chosen |
| the four subject states, `NO PARTY` positive | `subject_state`; `reader_process` |
| Person ≠ institution; two epistemic foundations | `parties.person_id` vs `parties.minted_by` — two anchors, a join, never a kind |
| institution under its minting claim; anchor points to evidence, is not evidence | `parties.minted_by` → an utterance |
| strength never stored | no column anywhere; §6 |
| origin never from channel/enum | no `source` enum anywhere; origin is a proposition with a party object |
| correspondence never merges, never crosses foundations | §7 |
| roles are dated relations, never parties | propositions of a relational kind with `as_of` and a second participant (however represented) |
| P-world exists as a claim nobody is knowing for | a proposition with `subject_state = no_subject`, kind P-world, evidenced by readings; strength derives to the floor |

**Passes.** No distinction required a column on the wrong object; three things the shipped
code stores are here **derived** (origin, strength, resolution), which is the ruling's
direction, not a loss.

---

## 9. Guards — what SQLite cannot express and the creation path must own

exactly one anchor per party · exactly one reader per reading (party xor process) · asserted
artefact ⇒ asserting utterance · subject populated iff `subject_state = established` (and the
same for any second participant, however represented) · `party_corresponds` never crosses foundations · `evidence` names exactly one
source (this one *can* be a CHECK). Each is the built slice's pattern: a query that must be
empty, a fixture that asserts it, a mutation that breaks it and is caught.

---

## 10. What this record does not do

It does not compare any of this to `Evidence`, `Classification`, `PdfExtractCache`,
`HealthPlan`, `DebtAccount` or `HistorianEntry`; does not propose a migration; does not choose
the second-participant representation (A) or between subject shapes (i) and (ii); does not enumerate the kind catalogue beyond what the
rulings named; does not decide the uncertain-`asserted_at` representation, the candidate
relation's shape, or where raw extracted text lives. **Next, if ruled:** the comparison against
the shipped system — which of these objects the code already holds under other names, and
where the two disagree.

---

## 11. Review — Rob, 2026-09-12. PARTIAL: two fences applied before the comparison.

**1. `object` had appeared without being earned.** The semantic ruling gave *kind · subject ·
content* with content opaque; the schema had introduced `object + object_state` as a settled
field. That some ruled propositions are binary establishes that propositions can express more
than one referential participant — not that the representation is specifically *subject +
object* rather than structured content whose semantics `kind` determines. The same premature
concretisation the proposition ruling avoided. **Applied:** the referential-participant
representation is now an open choice (§5 A), the `object` columns are withdrawn from the
mandatory data, and correspondence, guards and the gate are restated in terms of *a second
participant, however represented.*

**2. "The only rows that ARE evidence" was too strong and conflicted with the rulings.** An
utterance is evidence; a reading is evidence; the table records *this proposition is evidenced
by this utterance / reading.* **Applied:** §6 is now the *evidentiary relationship*; `evidence`
may remain the eventual table name, and the ontology reads *utterance / reading ─ evidences →
proposition*, not *evidence = evidence*. This matters directly for the comparison against the
shipped `Evidence` dataclass.

**Everything else survives review:** origin derived not stored · strength derived · zero
evidentiary rows legitimate for an uninterpreted utterance or unreadable reading ·
`recorded_at` distinct from evidence time · subject state explicit, never NULL-encoded · party
foundation structural, not a proposition kind · `minted_by` a reference to evidence, not
evidence on the party · correspondence a proposition kind, provided every required
correspondence case is representable without a special object · no uniqueness on
kind + subject + content. **The gate is the right gate.**

**Postponing the shipped-system comparison was correct:** the target representation now exists
without legacy vocabulary dictating it. The comparison must be able to find that **one old
table represents parts of several new objects**, rather than forcing the ontology into old
boundaries.

**Next question, ready:**

> **Against the shipped system, which of these six semantic objects already exist under other
> names, which are conflated, and which required distinctions are currently impossible to
> represent?**

The first comparison where the existing tables are allowed into the room.
