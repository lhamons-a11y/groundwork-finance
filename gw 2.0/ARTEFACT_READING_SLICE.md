# Slice 2 — artefact and reading: the thing encountered vs the act of observing it

> Status: **Build mode, slice 2 opened by Rob 2026-09-13; candidate RULED as written and the
> build AUTHORISED under Rob's gate (§8).** Slice 1 is accepted at `6700b69` (`SMALLEST_SCHEMA.md`
> §13). §1–§7 test the ruled artefact/reading shape against Rob's carried-in warning.

**Rob's question, verbatim:** *can an artefact and its reading be represented independently,
while preserving the distinction between the thing encountered and the act of observing it?*

**Rob's warning, verbatim:** *don't let the implementation convenience of `reading_id` turn
Reading into an alternate kind of Utterance.*

The shape was already ruled in `SMALLEST_SCHEMA.md` §2–§3 (artefacts · readings) and §6 (the
relationship takes `utterance_id` xor `reading_id`). So the question for this record is not
*what are the tables* — it is *where, in implementing those tables beside slice 1, would the
convenience of symmetry collapse the distinction?* Each place is found by asking what the code
would do if a reading were an utterance, and checking that against a case already ruled.

---

## 1. Where a reading and an utterance genuinely coincide — and where they do not

At the **relationship** the two are symmetric, by ruling: each is *evidence*; the row says *this
proposition is evidenced by this utterance / reading* (§6, Rob's fence). Exactly-one-source is
the only thing the relationship knows about the difference. That symmetry is real and should be
implemented as such — `reading_id` is an additive nullable column beside `utterance_id`, and
`SOURCE_SLOTS` grows by one.

Everything **upstream** of the relationship is asymmetric:

| | Utterance | Reading |
|---|---|---|
| **what it is** | an assertion event by a party | an observation event of an artefact |
| **identity** | the act (`UTTERANCE_IDENTITY.md`) | the act of observation, one per read (`IDENTITY_MECHANISM_COMPARISON.md`: the artefact owns its reading identities, one per act of observation) |
| **who** | `origin_party_id` NOT NULL — the party whose assertion it is | a **reader**: `reader_party` (a member transcribing) xor `reader_process` (a parser) — and the reader is **not** an origin |
| **of what** | nothing — an utterance is not *of* an artefact; it may be *about* one (subject) | `artefact_id` NOT NULL — owned |
| **its own time** | `asserted_at` (evidence time) ≠ `recorded_at` (encounter) | `read_at` — the reading's own time, which is neither the artefact's `as_of` nor its `encountered_at` |
| **content** | opaque `content` — what was said | **no content column** — its propositions are its content (§3) |
| **zero propositions** | legitimate (P3: held, not yet interpreted) | legitimate (V6: the field was unreadable) |
| **strength of what it evidences** | origin foundation × kind, on read | **not the reader's foundation** — see §2 |

The two coincide at exactly one column: `id`. Everything else differs in kind, and the table
above is the list of places the implementation must not share code.

---

## 2. The five places convenience would collapse the distinction

Each is stated as the tempting move, the ruled case it breaks, and what the slice does instead.

### 2.1 `reader_party` read as an origin

**Tempting:** extend `derived_strength` so a reading-sourced relation takes `reader_party` where
an utterance-sourced one takes `origin_party_id`. One function, one join, symmetric.

**Breaks:** contract C1/C2 (`PROVENANCE_IDENTITY_CONTRACT.md`): *origin = the party whose
knowledge the reading conveys; the capture channel never determines origin.* A household member
transcribing Lakeview Health's EOB is a channel; the EOB's claims convey Lakeview Health's knowledge, not the
member's. Reading `reader_party` as origin would make the member *knowing* for a health value
(C4's inflation) — and would make a process reading's origin *no party*, when in fact the
process is merely the channel and the origin is whatever the artefact's origin is.

**Instead:** a reading's origin is **the artefact's origin**, which is *derived from origin
propositions* (§2: not a column) — and those propositions, the origin-of-artefact kind, are
**not in this slice**. So in slice 2, `derived_strength` on a reading-sourced relation returns
**`undetermined`**, honestly: the origin is not yet derivable, and *the absence of a rule is not
a rule* (slice 1's own principle). The reader is recorded, never consulted for strength.

### 2.2 `reader_process` promoted to a party

**Tempting:** mint a party for "Groundwork's PDF parser" so every reading has a `reader_party`
and the xor guard disappears.

**Breaks:** the party ruling's fourth state (`PARTY_REFERENCE_QUESTION.md`): **NO PARTY** is
positive — *a process originated it; contributes nothing to independence; must not masquerade
as unidentified evidence.* A process-as-party would be an origin-shaped thing that could be
counted as a knowing source by any consumer that joins parties.

**Instead:** `reader_process` is text (name/version), `reader_party` is a nullable FK, and
exactly one is set — a guard, as ruled in §9. The fixture asserts that a process reading has no
party and that a reading with both, or neither, is refused.

### 2.3 A reading of an artefact Groundwork does not hold

**Tempting:** let the user's "the EOB says $412" be recorded as a reading of the asserted
artefact — the value came *from* the document, after all.

**Breaks:** R-ASSERT (`ASSERTED_REFERENT_CASES.md`): an asserted referent gives POSE + FIND,
**never RE-READ**; held = custody + re-readable (C4 of the capture ruling). A reading is an
observation of an artefact by Groundwork's reader; an artefact Groundwork never held cannot have
been observed by it. Recording testimony as a reading would manufacture a held-artefact
provenance for an unheld document — the exact promotion S3 forbids in the party domain.

**Instead:** the user's report is an **utterance** whose proposition has **`subject_artefact_id`
= the asserted artefact** (the slot arrives in this slice, additively). *A reading exists only
of a held artefact* — a guard (`readings_of_unheld_artefacts()` must be empty; the creation
path refuses). This is the single most direct test of Rob's warning: the same sentence, "the
EOB says $412", is a reading when the parser produced it from held bytes and an utterance when
the household said it — and the record can tell them apart without consulting the text.

### 2.4 `content_hash` as identity

**Tempting:** `UNIQUE(content_hash)` — or worse, look up the artefact by hash on encounter and
reuse the row. `PdfExtractCache` does exactly this and it is running.

**Breaks:** the frozen primitive (`IDENTITY_MECHANISM_COMPARISON.md`): *every "this arrival is
that artefact" is an asserted correspondence with a strength, never computed as identity from
bytes; `hash==X → artefact_id=X` is forbidden by construction.* Also D3 (`DOCUMENT_IDENTITY_
CASES.md`): one EOB uploaded twice and two EOBs must be distinguishable — under a hash key they
are the same row.

**Instead:** `content_hash` nullable, **not unique**, indexed only for finding *candidates*. Two
encounters with identical bytes are **two artefacts** until a correspondence claim (slice 4)
says otherwise. The fixture inserts two artefacts with one hash and asserts two rows.

### 2.5 The artefact's date and the reading's date and the encounter date, conflated

**Tempting:** one timestamp on the artefact (`created_at`) and one on the reading, and let
`as_of` be "whatever the parser found".

**Breaks:** the tie ruling (`SOURCE_TIE_CASES.md`): *recency is on the evidence's own time axis
— dated document → as-of; import order → never evidence*; H3's finding that a document's own
as-of **has no field today**. And the capture ruling: render-time vs source-stated as-of are
different (fenced, but the fence is preserved only if the columns are distinct).

**Instead:** three columns, three events — `artefacts.as_of` (the artefact's own date, nullable:
may be absent or unknown), `artefacts.encountered_at` (Groundwork first held or was told of
it; the minting event), `readings.read_at` (this observation). Mirrors slice 1's
`asserted_at` ≠ `recorded_at` exactly, and for the same reason: two columns so nothing can
ever read one as the other. Whether `as_of` was *stated by the source* or *read off a render*
is not represented in this slice — it is a proposition about the artefact, later.

---

## 3. The cases the slice makes representable — and what each proves

These are the acceptance tests, taken from the ten impossibilities (`SHIPPED_VS_TARGET.md`
§5) where they land in this slice, and from Rob's warning.

| Case | Ruled in | Representable after slice 2 | Proves |
|---|---|---|---|
| **One EOB read twice, readings disagree** ($412 / $4.12) | D3, V-cases | two `readings` rows under one `artefacts` row; each evidences a proposition of the same kind + `subject_artefact_id`; contents differ | parse dispute is *computable and nothing is chosen* — no `[-1]`, no `[0]` |
| **Two EOBs, same insurer, disagree** | D3, T-B | two `artefacts` rows, one reading each | source conflict ≠ parse dispute, by structure not by timestamp or text |
| **One EOB uploaded twice** | D3 | two artefacts, one hash — until correspondence | identity is minted, bytes are evidence |
| **Unreadable field** | V6 | a reading with zero evidentiary rows | *absence acquires no meaning* — the reading happened, the value did not |
| **Asserted artefact** ("my March statement, which I don't have") | R-ASSERT | `held = false`, `asserted_by → utterances`, **no readings** | POSE + FIND, never RE-READ |
| **Testimony about a held or unheld document** | R-ASSERT, the warning | an utterance whose proposition has `subject_artefact_id` | the same words are a reading or an utterance by *who observed what*, never by text |
| **Document date ≠ import date** | H3, tie | `as_of` vs `encountered_at` vs `read_at` | the missing field exists; recency is on the evidence's own axis |
| **Process reading** | party state 4 | `reader_process` set, `reader_party` NULL | *no party* is positive, not an unidentified party |
| **A member transcribes a statement** | C2 | `reader_party` set; strength still not from the reader | channel ≠ origin |
| **Strength of a reading-sourced claim** | C1, slice 1 | `undetermined` | origin is derived from propositions that do not yet exist; nothing guessed |

**Not made representable, deliberately:** the artefact's *origin* (slice 3: it needs the
origin-of-artefact proposition kind and, for institutions, the minted party); *which readings
agree* as a derived status (a consumer, not the substrate); *independence*; *supersession*;
the asserted → held upgrade (fenced: never auto-match a later artefact to a description);
raw extracted text (if kept, an artefact of the reading — a held thing — not built here).

---

## 4. Shipped vs target for this slice — one row, untouched

`PdfExtractCache(source_hash PK, issuer, extracted_json, created_at)` is the shipped artefact +
reading, 1:1 by hash, with `issuer` as description-as-origin (`SHIPPED_VS_TARGET.md` §1). It is
**not mapped, migrated, read as, or repaired** by this slice — Rob's list of things not
reopened includes it by name. The two structures coexist; the 1.x pipeline keeps writing the
cache; nothing in 2.0 reads it as an artefact store. Decomposing its rows into artefacts and
readings would be a *guess* about whether any hash was read once or twice — exactly the
decomposition the map says must not be done where it is not a fact.

---

## 5. What the slice would contain, if authorised

Additive throughout; no existing column changes; no data step.

```text
artefacts     id · held (bool NOT NULL) · content_hash (nullable, NOT unique, indexed)
              · as_of (String(10), nullable) · encountered_at (DateTime NOT NULL)
              · asserted_by (nullable → utterances)
readings      id · artefact_id (NOT NULL → artefacts) · read_at (DateTime NOT NULL)
              · reader_party_id (nullable → parties) · reader_process (String, nullable)
evidence      + reading_id (nullable → readings)          SOURCE_SLOTS = (utterance_id, reading_id)
propositions  + subject_artefact_id · object_artefact_id  (nullable → artefacts)
              SUBJECT_SLOTS / OBJECT_SLOTS grow by one; the state discipline is unchanged
```

Guards (each: a query that must be empty · a fixture assertion · a mutation that is caught):

- **exactly one source** on `evidence` — now real (`evidence_without_one_source` already exists
  and enumerates `SOURCE_SLOTS`); a listener refuses the row, as `_validate_participants` does
- **exactly one reader** on `readings` — party xor process
- **asserted ⇒ asserting utterance**: `held = false` ⇒ `asserted_by` NOT NULL; `held = true` ⇒
  `asserted_by` NULL (a held artefact's provenance is the encounter, §2)
- **readings only of held artefacts** (§2.3)
- **no origin column, no strength column, no content column on readings** — absence assertions,
  the slice 1 pattern

`derived_strength`: a reading-sourced relation → `undetermined`; the docstring says why and
names slice 3 as where the origin becomes derivable. `migrate.py`: `SCHEMA_VERSION` bump;
`create_all` creates two tables; the three additive columns go through the existing
`_add_missing_columns(table, [(name, ddl)])` helper (`migrate.py:146`, idempotent via
`PRAGMA table_info`) — additive by construction, which is why slice 1 left `utterance_id`
nullable. Fixture `tests/test_artefact_reading_fixture.py` = §3's
table; `smoke_sections/s88_artefact_reading.py` with at least: reader-xor guard removed;
unheld-reading guard removed; `derived_strength` reading the reader as origin.

**Not in the slice:** origin-of-artefact kind · institution · correspondence · `PdfExtractCache`
· held upgrade · raw text · independence · supersession · any consumer.

---

## 6. Build gate — candidate, for Rob to state in his own words

Mirroring slice 1's gate:

```text
encounter        -> one artefact, minted, held, with its own as_of distinct from encountered_at
read             -> one reading under that artefact, with its own read_at, its reader recorded
read again       -> a second reading under the SAME artefact (one artefact, two observations)
readings disagree-> two propositions of one kind + subject; nothing chosen; both remain
same bytes twice -> two artefacts
unreadable       -> a reading with no propositions
asserted artefact-> held = false, under an utterance, and it cannot be read
testimony        -> an utterance about an artefact is not a reading of it
process reader   -> no party, and no party is manufactured
strength         -> undetermined for every reading-sourced relation in this slice
```

---

## 7. Ruling candidate — for Rob

1. **Readings only of held artefacts** is a guard, not a convention — the direct mechanical
   form of *never RE-READ* and of the warning (§2.3). Candidate: **yes, in the slice.**
2. **A reading's strength is `undetermined` in this slice** — the reader is never consulted;
   the artefact's origin waits for the origin-of-artefact proposition (slice 3). Candidate:
   **yes; the alternative is inventing an origin from the channel, which C2 forbids.**
3. **`reader_process` is text, not a party.** Candidate: **yes** (party state 4).
4. **The artefact slots on `propositions` are in this slice** — without them the asserted-
   artefact testimony case (§2.3) and the parse-dispute case (§3 row 1) cannot be represented,
   and both are this slice's acceptance tests. Candidate: **yes.**
5. **`content_hash` is nullable, not unique** — two artefacts with one hash are two rows.
   Candidate: **yes** (frozen primitive).
6. **The origin-of-artefact proposition kind is NOT in this slice.** It is the first entry in a
   catalogue Rob has not ruled, and it is the thing whose absence makes 2 honest rather than
   lazy. Candidate: **out; it opens slice 3.**

*The distinction the slice must preserve, in one line: an utterance is what a party said; a
reading is what Groundwork saw — and the record must tell them apart without reading the text.*

---

## 8. Ruling — Rob, 2026-09-13. Candidate ruled as written; slice 2 ready to build under this gate.

*The important thing is that this is not merely adding `artefacts` and `readings`; it proves
the new evidence source cannot accidentally inherit the semantics of the assertion side.*

1. **A reading is not an utterance.** `reader_party` establishes who *performed the reading*,
   not who asserted the proposition. A member reading an EOB remains an observer of that
   artefact; they do not become the origin of its contents. A reading-sourced relationship
   cannot acquire knowing strength from `reader_party`; absent the artefact-origin proposition,
   **`undetermined` is the honest result.**
2. **`reader_process` really does mean no party.** NO PARTY is a positive semantic state, not a
   missing-value accident. Promoting the process into a party would manufacture epistemic
   ownership the evidence does not contain.
3. **Held-only is the right guard** — the cleanest expression of the distinction:

   ```text
   held artefact → reading → observation of that artefact
   Person → utterance → proposition about an artefact
   ```

   Similar English sentences; fundamentally different evidence events. *"The EOB says $412"*:
   a parser reading the held EOB produces a reading; a member saying it produces an utterance
   whose proposition has the artefact as subject. Same words, different event — and the
   substrate now has somewhere to preserve that.
4. **Hash remains description/correlation material, not identity.** `A1 ─ H`, `A2 ─ H` are two
   artefacts until correspondence establishes otherwise; a unique hash would turn an
   implementation convenience into an ontological assertion.
5. **The three times remain three times** — `as_of · encountered_at · read_at`, as
   `asserted_at · recorded_at`. `encountered_at` never becomes evidence of when the document
   existed; `read_at` never becomes the document's date.

**Especially endorsed — origin-of-artefact kind is OUT.** Tempting because the reading's
strength is otherwise `undetermined`, but that is backwards: *the need for a value downstream is
not evidence that the proposition kind is already ruled.* Slice 2 correctly leaves `reading →
proposition → strength → undetermined`; **slice 3 answers the actual question: what
proposition establishes an artefact's origin, and what evidence is sufficient to establish it?**

**The gate, in Rob's words:**

> An artefact and a reading must be independently representable, and neither may acquire the
> semantics of the other through convenience. A reading identifies an observation of a held
> artefact; it does not establish the artefact's origin, create a party, or become an
> assertion. An artefact's hash, dates, and reader information remain distinct coordinates, and
> every source-dependent conclusion remains derived rather than stored.

**One practical acceptance requirement:** the fixture must deliberately construct the two
identical-looking statements and prove they remain different evidence paths — not merely
*reading exists, utterance exists*, but `reading("EOB says $412") ≠ utterance("EOB says $412")`,
because **the event that produced the proposition is what is being protected.**

If that passes, slice 2 is ready to build. After it, slice 3 is the artefact-origin question —
not another schema question disguised as implementation.
