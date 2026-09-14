# Slice 4 — what is a correspondence claim?

> Status: **Build mode, slice 4 opened by Rob 2026-09-13; candidate RULED (§8); build AUTHORISED
> and BUILT — see the commit for the build boundary.** Slice 3 is
> accepted and closed at `d626218` (`ARTEFACT_ORIGIN.md` §9). This record tests three readings
> of the question against the cases already ruled, finds one conflict between two earlier
> records and resolves it by the cases, finds two things the substrate must add, and ends
> with a ruling candidate, ruled in §8.

**Rob's question, verbatim:** *what is a correspondence claim?*

**Rob's carry-in, verbatim:** *origin and correspondence must never become interchangeable.
The fact that Riverbend Hospital appears in an Lakeview Health document is not a weak version of `origin(EOB) =
Riverbend Hospital`. It is a different proposition about a different relationship.*

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Frozen primitive** (`IDENTITY_MECHANISM_COMPARISON.md`) | *every "this arrival is that artefact" is an ASSERTED CORRESPONDENCE with a strength, never computed as identity from bytes/description/file*; hash · issuer id · description · *"yes, that's it"* are **correspondence evidence at graded strength, never identity**; separately-minted identities can later be established as corresponding |
| **Party reference** (`PARTY_REFERENCE_QUESTION.md`, `_SHAPE.md`) | an institution is minted, with correspondence as asserted claims with strength (name / external id / "same company" = evidence, never identity); **correspondence never crosses foundations** — Person and institution may *relate*, never be collapsed; *a party reference is a referential mechanism, not evidence of party identity* |
| **Institution encounter** | the household's assertion *either asserts correspondence to an existing party or mints a new one*; other parties' statements, identifiers and descriptions are **correspondence evidence and candidate sources**; **description never mints or matches**; import pipelines produce candidates and ASK |
| **Utterance identity** | one act recorded twice = one utterance — a replayed sync must not mint; *a duplicate encounter is a correspondence question, never a second row minted by the importer* |
| **Proposition** | "same kind + subject + content" is **not** a uniqueness constraint: sameness beyond that minimum is a correspondence claim; semantic sameness ≠ event identity |
| **R-ASSERT** | an asserted referent is found by description — an inference that can DEGRADE as candidates arrive (non-monotonic); **asserted → held upgrade fenced: never auto-match a later artefact to a description** |
| **Ontology** (`REPRESENTATION_CANDIDATE_MATRIX.md` ruling) | *correspondence operates ACROSS the four layers, never becoming one of them*; a user's report of the EOB and the EOB = *possibly one referent, to be DISCOVERED, never assumed* |
| **`SMALLEST_SCHEMA.md` §7** (PARTIAL) | a proposition kind per referent type; *never merges rows*; *never crosses foundations*; strength derived — **and one line this record must test: *"a hash match asserted by a process reading is strong by kind"*** |
| **Slice 3, O9** | a process cannot utter; the substrate cannot represent a process as an origin |

The last two rows conflict, and §3 resolves it.

---

## 2. Three readings of "a correspondence claim"

**Reading A — a proposition: *X and Y are one referent*.** Per referent type, a kind whose
subject and second participant are two separately minted identities of that type. A claim
like any other: evidenced, with strength, derived state, never a column. The rows stay; the
referent is *read* as what the established claims connect.

**Reading B — an operation: alias or merge.** `PersonAlias`'s shape generalised — a canonical
id, a `duplicate_of` pointer, a re-pointed foreign key. Correspondence *does* something to the
rows.

**Reading C — an entity: the logical referent.** A `referents` (or *logical document*) table
that minted identities are members of; correspondence = membership.

B is rejected by the rulings directly: *never merges rows*; a pointer column is a stored
summary of a claim that can drift from the claims (the `resolution()` lesson), and a merge
destroys the history Rob just endorsed keeping (*Rob said Lakeview Health; later somebody said Riverbend Hospital;
both remain*). `PersonAlias` is the shipped precedent for correspondence-as-*assertion*, not
for correspondence-as-merge — its `source` column is the part to inherit, its `person_id`
pointer the part not to.

C is the `subjects`-table decision again (`SMALLEST_SCHEMA.md` §12 B): an identity-bearing
object between a thing and its referent that the ontology did not rule. For parties it is
worse than redundant — the minted party *is* the anchor correspondence points at; a
`referents` row would be a second identity for every institution. And it would make "are 17
and 42 the same?" answerable by a row lookup rather than by claims — identity computed, not
asserted. Rejected without a case.

A is tested below.

---

## 3. The conflict, resolved by the cases: who can establish a correspondence?

`SMALLEST_SCHEMA.md` §7 (PARTIAL, pre-slice-3) said a hash match *asserted by a process
reading* is **strong**. Slice 3 then ruled and built: a reading of the artefact itself yields a
**candidate**, never establishes; and O9 found a process cannot utter. The two cannot both
stand. The cases decide:

- **Frozen primitive:** identity is *never computed from bytes*. A hash match that establishes
  is identity computed from bytes with one step of indirection.
- **R-ASSERT:** *never auto-match a later artefact to a description*. A hash is the strongest
  description there is; the rule does not carve it out.
- **Institution encounter:** *import pipelines may not create institutions from issuer strings;
  they produce candidates and ask* (C9). The same pipeline, the same rule, for artefacts.
- **Slice 3's derivation, mechanically:** a reading-sourced claim's strength derives through
  the *artefact's origin* (C1). The knowledge "these bytes equal those bytes" is not Lakeview Health's;
  routing it through Lakeview Health would score it *not knowing* by accident. The honest reading is
  that the observation has **no party** — state 4 — and *contributes nothing to independence*.

So: **a correspondence is established only by a party's utterance; every observed match —
hash, import id, issuer string, description, date + origin — is a candidate with no party
behind it.** The PARTIAL line is withdrawn. What the hash *does* buy is being the strongest
candidate: the pipeline can ask with confidence, and a consumer that shows candidates can rank
them by basis — but ranking candidates is a consumer's presentation, not the substrate's
strength.

**The replayed-sync objection, answered by a distinction already ruled.** *One act recorded
twice = one utterance* was ruled as **identity** (E3), not correspondence: the importer
recognising *its own* prior encounter of *the same arrival* is Groundwork knowing what
Groundwork did — not a claim about the world. That stays where it is (the 1.x `import_id`
mechanism is that recognition). Two *arrivals* that may be one artefact — a re-upload, a
re-download, a second sync of a changed file — are correspondence, and are candidates until a
party says so. **Where the line between "same arrival" and "two arrivals" falls is the
importer's contract and is not decided here.** How a *standing* household authorisation might
let a pipeline act on its own candidates is a policy question outside the substrate (§6).

---

## 4. The cases

| # | Case | Ruled in | Under A |
|---|---|---|---|
| **X1** | One EOB uploaded twice: artefacts 17 and 42, one hash. | D3, frozen primitive | two artefacts (slice 2). The importer's hash match → `artefact_corresponds(42, 17)` **candidate** (reading-sourced, no party). Rob: "yes, I uploaded it twice" → **established**. Rows untouched; readings of 42 stay under 42; the *referent* {17, 42} is derived on read |
| **X2** | Two identical Lakeview Health letterheads (O7): two letters, both from Lakeview Health. | O-encounter | **not a correspondence.** Their *origins* correspond (both Lakeview Health — origin, slice 3); the artefacts are two statements. *Same origin ≠ same artefact.* A description match here is a candidate for **origin**, not for artefact correspondence — the first place the two must not be confused |
| **X3** | Rob minted "Lakeview Health" in March; in June, not remembering, mints "Lakeview Health Health Inc." Later: "those are the same company." | party reference, encounter | `party_corresponds(B, A)` **established** by Rob's utterance. Neither party row is merged, re-pointed or deleted; the June EOB's origin still names B; a consumer asking "who is the origin of these two EOBs" reads the referent {A, B} and finds one insurer |
| **X4** | Rob and "Rob's sole proprietorship" (an institution). | never crosses foundations | `party_corresponds(Rob, Rob LLC)` **refused** (guard) — the two foundations never collapse; *related* is a relation of another kind, not this one |
| **X5** | "My March Harbor statement — I don't have it" (asserted artefact 9). In May a PDF is uploaded (held artefact 30). | R-ASSERT, asserted→held fence | a candidate may be *found* (origin Harbor + `as_of` March match); **established only when Rob says "that's it."** 9 stays asserted, 30 stays held — nothing is upgraded; the correspondence lets consumers read propositions whose subject is 9 as about the referent 30 is in. *POSE + FIND, then a claim — never RE-READ of 9* |
| **X6** | "The EOB says $412" (Rob, about an asserted artefact) and the parser's reading of the uploaded EOB. | captured-portal, ontology | *possibly one referent, to be discovered, never assumed* — the same shape as X5; discovery = a candidate; the claim = Rob's |
| **X7** | A bank sync replays: the same transaction arrives twice. | E3 | **identity, not correspondence** — the importer recognising its own encounter (§3). If two rows were nonetheless minted, that is a defect repaired by a correspondence claim, not a merge |
| **X8** | Rob says "$412"; the parser reads "412.00" — same kind, same subject. | PROPOSITION, V4 | two propositions; whether they are *one claim* is `proposition_corresponds` — **not forced by any ruled case**: "those two pieces of evidence agree" is a *comparison* consumers derive over content under one kind + subject, not a correspondence. Deferred until a case needs it (§6) |
| **X9** | Lakeview Health's EOB names Riverbend Hospital Hospital (Rob's carry-in). | O6, §9 | **not a correspondence and not origin.** A mention is *content*; it becomes a candidate only where there is a second referent of the right type — the origin of a *Riverbend Hospital bill* (slice 3, candidates). Nothing in this slice consumes mentions |
| **X10** | `corresponds(17, 42)` and `corresponds(42, 55)`. | tie ruling, C3 | the referent {17, 42, 55} is the **connected component under established claims**, derived on read; its strength is weakest-link along the path. Nothing stores the component |
| **X11** | Rob: "17 and 42 are the same." Later: "no, 42 was the corrected one." | Case B, slice 3 `multiple` | both claims remain; a Case-B claim about the first utterance may exist; the derivation reports the component as **contested** and chooses nothing — the resolver over corrections is the same fenced question as origin's `multiple` |
| **X12** | `corresponds(17, 17)`; `corresponds(artefact 17, party Lakeview Health)`. | — | **refused**: a thing corresponds to itself trivially and to a thing of another type never. The second is the first *per-kind slot constraint* the substrate has needed (§5) |

**What the cases fix about A's meaning:**

- A correspondence claim is *X and Y are one referent*, for two **separately minted identities
  of one type**, both established. Its content is the **basis** (hash · id · description ·
  "yes, that's it") — evidence for a consumer to show, never consulted by the derivation.
- **Established only by a party's utterance** (§3). Observed matches are candidates, no party.
- **Symmetric in meaning**: `corresponds(42, 17)` and `corresponds(17, 42)` are one claim said
  two ways; stored as asserted, read both ways. Not transitive by storage — the component is
  derived (X10).
- **Never merges rows; never rewrites a reference** (X1, X3, X5): the derivation is the only
  thing that ever "unifies", and it does so on read.
- **Never crosses foundations** (X4); **never crosses types** (X12); **never reflexive** (X12).
- **Not origin, not mention, not role** (X2, X9, X4): same origin is not same artefact; a name
  in a document is content; relatedness is another kind.
- **Referent state, read off the claims:** *separate* (no established claim) · *candidates* ·
  *corresponding* (one component) · *contested* (established claims plus a Case-B claim
  against one, or claims that would put a thing in two components — reported, not resolved).

---

## 5. Two things the substrate must add — found, not designed

**5.1 Per-kind slot constraints.** Slice 3 fixed `artefact_origin`'s shape by convention only:
the derivation *filters* for `subject_artefact_id` + `object_party_id`, so a malformed origin
claim (subject a party) is silently ignored rather than refused. X12 makes the gap visible for
the first kind whose two participants must be the *same* type. The proposition ruling already
said it: *no universal subject/object requirement — kind determines which slots are
meaningful.* What is needed is small: a registry `kind → (permitted subject slots, permitted
object slots)` for the **ruled kinds only** (`artefact_origin`, `artefact_corresponds`,
`party_corresponds`), enforced by `_validate_participants` when the kind is in the registry
and *not enforced* for kinds that are not — the catalogue stays open; ruled kinds stop being
convention. Retroactively tightening `artefact_origin` is a slice-4 change to a slice-3 kind
and is stated as such.

**5.2 The `same-foundation` guard for `party_corresponds`.** Already ruled; needs the anchor
built in slice 3 to be checkable — the listener joins both parties' anchors.

---

## 6. Not decided here — fences

- **`utterance_corresponds`, `proposition_corresponds`** — in the PARTIAL schema's kind list;
  **no ruled case forces either** (X7 is identity; X8 is a comparison). Not built until a case
  does. The shape is the same; adding a kind later is a registry entry.
- **The importer's contract** — where *same arrival* (identity, E3) ends and *two arrivals*
  (correspondence) begins; and whether a standing household authorisation can let a pipeline
  act on its own candidates. Policy, outside the substrate; the O9 sibling (*a process is
  knowing for facts about its own operations*) lives here.
- **Consequences of an established correspondence for other derivations** — readings of
  corresponding artefacts are readings of one referent (4 → 6: never independent); propositions
  about 9 read as about 30's referent; origin of a party's component. Each is a *consumer* of
  correspondence and is not derived in this slice.
- **Resolution over contested components** (X11) — the same fenced resolver as origin's
  `multiple`.
- **Person ↔ Person correspondence** — `PersonAlias` is the shipped precedent, but a duplicate
  `Person` is a registry (`core/person.py`) question about the household's declaration, not a
  minted identity; not exercised.
- **Candidate ranking by basis** (hash > id > description) — a consumer's presentation.

---

## 7. Ruling candidate — for Rob

> **A correspondence claim is a proposition asserting that two separately minted identities
> of one type are one referent — *artefact_corresponds* and *party_corresponds* in this slice
> — with both participants established, distinct, of that type, and, for parties, of one
> foundation. It is established only by a party's utterance; every observed match — hash,
> import id, issuer string, description, date and origin — is a candidate with no party
> behind it, however strong its basis, and the basis is the claim's content, shown to a
> person and never consulted by a derivation. A correspondence never merges rows, never
> rewrites a reference, never crosses foundations or types, and is never reflexive. Sameness
> is read, never stored: the referent is the connected component under established claims,
> weakest-link along the path, reported as contested when the claims conflict and never
> resolved by position. Origin, mention and role are not correspondence: same origin is not
> same artefact; a name in a document is content; relatedness is another kind. Ruled kinds
> acquire per-kind participant-slot constraints, enforced; unruled kinds remain unconstrained.**

If ruled, slice 4's build contents are: the two kinds · the kind → permitted-slots registry
for the three ruled kinds, enforced in `_validate_participants` (tightening `artefact_origin`
retroactively, stated) · the same-foundation guard · `referent(session, thing)` deriving
component + state · fixture over X1–X12 (X7 asserted as identity, X8/X9 asserted as *not
correspondence*) · mutations (a hash match establishes; a merge/re-point; cross-foundation
accepted; cross-type accepted; position resolves a contested component) · migration: none
(no new column or table — the first slice that adds only claims) · gate. **Not in it:** the
importer's contract · any consumer of the component · `utterance_`/`proposition_corresponds`
· Person ↔ Person · the resolver.

*The line the slice must hold: a match is a reason to ask; only an answer is a claim.*

---

## 8. Ruling — Rob, 2026-09-13. §7 ruled as stated; no fenced question reopened.

*Slice 4 did not merely add "correspondence." It made a much more precise separation, and
none of the four can silently substitute for another:*

```text
Origin          answers   whose statement is this?
Correspondence  answers   are these two established identities one referent?
Content         answers   what does this artefact say?
Identity        answers   is this the same event / row / arrival?
```

**The strongest part is the conflict resolution around the process/hash match.** The tempting
architecture — *identical bytes → strong correspondence → same referent* — is refused. The
hash tells Groundwork something it observed; it does not constitute a party asserting that two
artefacts are one referent. The evidence direction stays intact:

```text
observation → candidate → party assertion → correspondence claim → derived referent
```

never `observation → identity`. Consistent with the origin ruling just closed.

**Carried forward — referent vs identity stays extremely sharp.** *The referent is the
connected component under established claims* is right because it is derived; but the
sentence *"artefacts 17 and 42 are the same"* is easy for a consumer or UI to read as row
identity. **The safer vocabulary: *17 and 42 correspond; their derived referent contains
both.*** Two artefact identities, two histories, potentially two arrival events remain.

**X2 becomes a permanent regression case:** `A ≠ B`, `origin(A) = origin(B)` — one case that
prevents an enormous class of future mistakes. **Likewise X9:** the Lakeview Health EOB's content
"Riverbend Hospital Hospital" becomes neither `origin(EOB) = Riverbend Hospital` nor `EOB ↔ Riverbend Hospital artefact` unless a
separate ruled mechanism establishes it. *The conceptual firewall to preserve.*

**The slot registry is a real substrate correction, not overengineering.** Slice 3 had a
convention; convention is not enforcement. If the proposition system is deliberately
open-ended, known kinds need their known participant contracts enforced without pretending
all future kinds are known — *a correction discovered by implementation, not a new design
agenda.*

**Where the architecture is left:**

```text
                 ASSERTED CLAIMS
                       │
          ┌────────────┴────────────┐
   artefact_origin          artefact_corresponds
          ▼                         ▼
      origin state             referent state
          └────────────┬────────────┘
                 CONSUMERS LATER

   candidate ≠ claim · claim ≠ identity · claim ≠ truth · derived state ≠ stored identity
```

Correspondence does not need to know *why* the party asserted it: hash, identifier,
description, "yes, that's it" remain the basis — content of the assertion. The substrate
establishes that a party made the claim; consumers decide how to present or act on its basis.

**Not to be opened until an actual case forces one:** `utterance_corresponds` ·
`proposition_corresponds` · candidate ranking · resolver behaviour · correspondence consumers.
The next slice starts from the next actual question the architecture needs, not from the
interesting things correspondence has made possible.

The two lines, paired:
> *A match is a reason to ask; only an answer is a claim.*
> *A document can say where it is from; only a party can say where a document is from.*
