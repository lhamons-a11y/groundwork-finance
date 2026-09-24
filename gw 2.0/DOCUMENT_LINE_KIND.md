# A stance before its subject is tied — the document line's own kind

> Status: **Queue item 18, opened by Rob 2026-09-21 from the bank line's F1; no code.** The sibling
> question item 14 named and did not rule: **what kind does a reading of a creditor's, insurer's or
> provider's document line mint, when the line states that party's position about an identity
> (an obligation, an expense, a plan) that nobody has yet tied it to?** The bank line's answer does
> not transfer: its referent — a movement — *is never an identity* (T2), so `movement` could have no
> object at all. These lines are positions about identities that exist or will. Cases → findings →
> candidate → ruling → a separate build authorisation.
>
> **One correction on the way in.** The running boundary list has called this *the 7J-F4-F1 sibling
> question*. It is not: 7J-F4-F1's siblings were the per-relationship holder gates, built and closed
> at `f215c30`. This question was named in `BANK_LINE_KIND.md` §4 F1 and accepted in its §7. The
> subject matter Rob named — *a stance before its subject is tied* — is unchanged; only the label was
> wrong.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **The bank line's own kind (item 14, closed)** | a line is *the party's statement that …*, subject the party whose statement it is, content the line as read, `as_of` the date the line states, `KNOWING_SUBJECT_PARTY`, **no object** — *the line mints evidence about an occurrence, not a stance about an identified domain object*; what it concerns is Ab7's claim; **the later tie cannot be manufactured by the line-kind rule**; the matcher stays fenced. **And: the corpus is the SHAPE, not the names.** |
| **Ab7 / K1p (ruled, built)** | the line → identity tie is `proposition_concerns(P, X)`, **a party's assertion**; a matcher's pairing is a **reading-sourced candidate** concerns claim (Pa3); `PARTICIPANT_CANDIDATES` names nothing and holds no reference — *the candidates are the reading-sourced concerns claims*. A proposition-level crossing is **not** a property of the artefact (Ab10: the wrong artefact can still concern the right obligation). |
| **9D-i / 9D-ii / 9D-iii (ruled, built)** | the ruled stances take **the identity as subject**: `balance(O)`, `billed(X)` / `patient_responsibility(X)` / `plan_paid(X)`, `deductible(P)` / `plan_year(P)` / `deductible_applied(P)`; each with a role-at-date knowing relation on the asserter. **The line shape — the party as subject, the thing a candidate — was REFUSED under every one of those names** (Ob-pin for `statement_figure`, Xs13 for `eob_amount`, 9D-iii F6(i) for `sbc_line_figure`, Va11 for the bank line) and kept under stand-ins. |
| **7G-F3 / 7J-F4 / 7J-F4-F1 (ruled, built)** | the **document path**: a reading evidences the ruled stance claim itself — `balance(O)` from Harbor's statement line (Dc3, Sb3), `deductible(P)` from the SBC (Te5), `patient_responsibility(X)` from the EOB (Sh3) — a candidate whose strength is the artefact's origin's, established when a party accepts it, and then governing. **These claims name the identity at reading time.** |
| **Slice 6 / the registry** | a ruled kind's participants are **established** in the kind's slots, or a required absence; `PARTICIPANT_CANDIDATES` is available only to **unruled** kinds (the state discipline alone). So *no ruled kind can carry a candidates participant.* |
| **9D-i's strength mechanism** | every stand-in's strength still comes from the caller's **foundation map** (`{'institution'} ⇒ knowing`) — the mechanism 9D retired for every ruled kind. After item 14 retired the bank line's, **these stand-ins are the last users of it.** |
| **Candidate generation — fenced** | the matcher, the importer contract, standing authorisation. This pass may rule what a line **is**; it may not rule when a matcher may name the identity. |

---

## 2. The surface — and the inventory, by shape

**Two representations of the same fact live in the record, side by side.** Harbor's March statement
says the balance is $2,588:

| | the claim | its subject | how it is tied to O | who reads it |
|---|---|---|---|---|
| **(i) the line** | `statement_figure` (unruled) | **the party**, Harbor | `proposition_concerns(P, O)` — Ab7, a party's assertion or a reading-sourced candidate | 7A (parse disputes), 7C (correspondence), 7D (level consistency), 7E (chain strength), Ab7, the identity fixtures |
| **(ii) the stance** | `balance` (ruled) | **the obligation**, O | **presupposed** — the claim is minted with `subject_obligation_id=O` | 7G, 7I, 7H, 9D-i |

Neither is wrong on its own terms. But **(ii) is minted at reading time with the identity already
named, and nothing in the record says who named it.** In the built document-path cases (Dc3, Sb3,
Te5, Sh3) the reading evidences a claim about O / X / P directly — the tie Ab7 ruled must be asserted
is, in those corpora, *assumed by the fixture*. That is the question this pass exists to settle, and
it is the same class of finding as item 14's: **a shape in the corpus that the ruling, applied
strictly, would not permit a reader to produce.**

**The inventory, by shape rather than by name (item 14's lesson).** Counting *subject the party,
object `PARTICIPANT_CANDIDATES`, evidenced by a reading* — and its slice-3 variant *subject the
artefact* — the line shape is **not three stand-ins and ~60 sites**. It is at least:

| stand-in | sites | documents |
|---|---|---|
| `statement_figure` | **77** | the creditor's statement (balance, escrow, last payment) |
| `eob_amount` | **37** | the insurer's EOB |
| `terms` · `payment_due` · `minimum` · `rate` · `escrow` | **34 / 15 / 14 / 9 / 2** | the same statements, other lines |
| `services` · `applied` · `disbursement` · `sbc_line_figure` | **11 / 16 / 1 / 4** | the servicer's letter, the payoff letter, the SBC |
| the artefact-subject variant | **21** | slice-3 era: the reading, relational-knowing and retraction fixtures |

across **24 files**, with **87 helper-driven call sites** (`line(…)` / `read_value(…)`) whose default
shape is this one. **Any build that changes the shape touches the substrate's oldest and widest
corpus** — and three of those names (`terms`, `services`, `applied`) are not in the record's
"three stand-ins" description at all.

---

## 3. The question, and the readings

> **Is a document line its own kind — the party's statement of a figure, subject the party, no
> established identity — with the tie to O / X / P always Ab7's separate claim? Or is it the ruled
> stance itself, minted only when a party has named the identity — in which case the line, before
> that, is not a claim of any ruled kind at all?**

**Reading L1 — the line is its own kind (the bank line's answer, extended).** One ruled kind (or a
small family) for *the party's statement of a figure on a document*: subject the party, **no
object**, content the line, `as_of` the line's date, `KNOWING_SUBJECT_PARTY`. The ruled stances stay
exactly as they are, and a stance is created **only when someone ties the line** — by an utterance
(*that line is my mortgage balance*) or by accepting a matcher's candidate. **Consequence:** the
document-path corpora (Dc3, Sb3, Te5, Sh3) are *shortcuts* — the reading would yield a line, and the
`balance(O)` claim would need the tie in the record. Either those corpora gain the tie, or the
shortcut is ruled legitimate (F3).

**Reading L2 — the stance is the claim; the line is the same stance before its subject is known.**
The ruled kinds gain nothing; what the reading mints *is* `balance` / `billed` / `deductible`, with
the identity participant simply **not yet established** — which the registry forbids for ruled kinds
(slice 6). To take L2 the registry would have to admit a candidates participant on a ruled kind: **a
substrate change to the participant discipline**, and the one 9D refused four times by name.

**Reading L3 — both, with a rule about which.** The line kind for a reading that names no identity;
the ruled stance for a reading whose identity the record already ties (via `artefact_concerns(A, O)`
plus the line's position, or an existing `proposition_concerns`). **Two shapes for one fact, with a
derivation choosing between them** — the *drift* the one-source rule forbids, and it makes the
reader's output depend on what else happens to be in the record at read time.

**Reading L0 — rule nothing; leave the stand-ins.** The stand-ins have carried these consumers since
slice 2 and no consumer reads their *kind* semantically (7A groups whatever the readings yield). The
cost is that the substrate's widest corpus stays unruled, its strength still comes from the retired
foundation map, and item 9's inventory is not actually complete.

*Reading, for Rob to reject:* **L1**, with **F3** ruled explicitly — because L1 is the answer item 14
already gave for the same shape, and the only question it leaves is whether a reader may name the
identity. **But L1's corpus is the largest in the record, and its ruling has a consequence for four
built passes.** That is what makes this pass big, and why F1 asks whether it should be ruled at all
before the matcher is.

---

## 4. Findings

**F1 — order: this question, or the matcher first.** L1's whole content is *the line is not the
stance; the tie is a separate claim* — and **who may make that tie is candidate generation**, fenced
since item 9. Ruling L1 without the matcher leaves the household holding lines that nothing may tie
except an explicit utterance per line (Pm10's twelve autopay lines, one a year, is the same problem).
*Reading:* rule what the line **is** here (it is answerable from T2 / Ab7 / item 14 alone) and state
plainly that **the tie's authorisation remains fenced** — or defer the whole question until the
matcher is opened. **Rob's, and it decides whether this pass proceeds.**

**F2 — one kind or a family.** The bank line got one kind because one predicate covered it (*a
movement occurred*). Here the lines are a creditor's balance, an amount due, a rate, an escrow
figure, an insurer's adjudicated amount, a plan's deductible, a servicer's *we service your
mortgage*. *Reading:* **one kind** — *the party's statement of a figure on its document*, the line's
own words the content and the kind of figure **not** interpreted (which is 7A's `payment_due` vs
`balance` kind-dispute case: the parse disagrees about what kind of line it is, and that dispute must
survive the ruling). **Rob's.**

**F3 — the document path in four built passes.** Dc3 / Sb3 (7G), Te5 (7J), Sh3 (7H) mint the ruled
stance from a reading with the identity already named. Under L1 that is either (a) legitimate — a
reader may name the identity when the household's acceptance does, and the claim is the stance, not
the line; or (b) a corpus shortcut to be corrected, with the tie made explicit. **(b) would mean
re-opening four accepted passes' corpora.** *Reading:* **(a)** — *the acceptance that establishes the
stance is also what names its subject*; the line kind is for a reading that names nobody. **This is
the finding that decides the size of the build. Rob's.**

**F4 — the foundation map's last users.** These stand-ins are the last kinds whose strength comes
from the caller's `{'institution'}` map. Under L1 they get `KNOWING_SUBJECT_PARTY` and the map
entries retire — completing what 9D began. *Reading:* as stated. **Rob's.**

**F5 — what the consumers see.** 7A / 7C / 7D / 7E read whatever kinds the readings yield and would
be unaffected in substance — but 7A's **kind dispute** (Pd4: one reading says `balance`, the other
`payment_due`) is a dispute between two *stand-in* kinds. Under one ruled line kind, the disagreement
moves from the kind to the **content**. *Reading:* the kind dispute must survive as a dispute about
*what the line says*, or Pd4 is silently lost. **Rob's.**

**F6 — the corpus, measured by shape (§2).** ~200 sites, 24 files, 87 helper call sites, at least ten
names, three of which the record's own description omits. *Reading:* if L1 is ruled, the build is
**staged** — one document family at a time, each stage its own gate — and the first stage names which.
**Rob's.**

**F7 — what must not change.** Ab7's tie, `PARTICIPANT_CANDIDATES`' meaning (*the carrier is the
concerns claims*), the ruled stances' subjects, the matcher's fence, 7E's chain semantics, and the
refusals that keep the line out of the ruled stance names (Xs13, Va11, 9D-iii F6(i)). *Reading:* as
stated. **Rob's.**

---

## 5. Cases

The credit-union statement A (origin the CU), read; it lists the mortgage O1 and the HELOC O2; line 3
reads *balance $44,000*. The EOB (origin Lakeview Health) lists PR $412 and plan paid $900 for a visit X.

| # | Case | today | under L1 |
|---|---|---|---|
| **Ln1** | line 3, read, nobody has said what it is about | `statement_figure`, subject the CU, object candidates; strength by the map | the ruled line kind, subject the CU, **no object**, knowing through the origin; identical in every consumer |
| **Ln2 (Ab7 / Pa1)** | Rob: *that line is the HELOC* | `proposition_concerns(P3, O2)`, established | unchanged — the tie is Ab7's, always |
| **Ln3 (Pa3)** | the parser pairs line 3 with O2 by heading | a reading-sourced concerns **candidate** | unchanged — and **the matcher stays fenced** |
| **Ln4 — the crux (F3)** | the same line, and Rob says *the mortgage balance is $44,000* | today: a `balance(O1)` claim, the identity named at mint | under L1(a): the same — the acceptance names the subject; under L1(b): the line plus a tie, and `balance(O1)` only on a second act |
| **Ln5 (Pd4)** | two readings kind line 3 `balance` and `payment_due` | a **kind** dispute (7A) | the dispute is about the line's **content**; 7A must still report a disagreement (F5) |
| **Ln6 (Ab10)** | the line is about O2 but the artefact was mis-tied to O1 | the proposition-level tie is independent | unchanged |
| **Ln7 (K5 / O5)** | Rob types the EOB's figure from memory; Rob's spreadsheet is read | not_knowing by the map | not_knowing by the relation (the origin is not the subject party) |
| **Ln8 (the SBC)** | *$3,000 individual / $6,000 family* on one line | `sbc_line_figure`, one claim, two figures in the content | unchanged — the content is not interpreted (F2) |
| **Ln9 (7E)** | the chain: the line's strength through `artefact_origin` | the map | the relation; the chain's shape unchanged |
| **Ln10 (the null model)** | every consumer's existing outcome | — | identical, by construction: no consumer reads the kind semantically |

---

## 6. Candidate — pending the ruling

**Under L1:** one ruled kind — *the party's statement of a figure on its document*: subject
(`subject_party_id`), **object `()`**, content the line as read, `as_of` the line's date,
`reading_establishes True`, `KNOWING_SUBJECT_PARTY`; the foundation-map entries retire; the tie stays
Ab7's; the matcher stays fenced; the ruled stances unchanged; F3(a) keeps the four document-path
corpora as they are. **The build is staged by document family (F6)**, each stage its own gate, with
the first stage named in the ruling. Mutations, per stage: the line admitted as the ruled stance ·
the tie manufactured from the artefact's concerns · the kind dispute collapsed (F5) · the map
restored.

**Under L0:** nothing; the record states that the line shape stays a stand-in until the matcher is
ruled, and item 9's inventory is explicitly *not* complete.

---

## 7. Ruling sought

> **(1) F1:** proceed now, or defer until the matcher is opened. **(2)** L0, L1, L2 or L3. **(3) F3:**
> (a) the acceptance names the subject — the four built passes' corpora stand; or (b) they are
> shortcuts to correct. **(4) F2:** one kind, the figure's sort uninterpreted. **(5) F5:** the kind
> dispute survives as a content dispute. **(6) F6:** staged by document family, the first stage named.
> **(7) F4, F7** as read. Nothing here authorises code.

---

## 8. Ruling — Rob, 2026-09-21: **L1 with F3(a)**; F1 answered first — proceed now; no build

**L1: the line is its own kind.** *It is not the `balance(O)` stance merely because both
representations can carry the same underlying figure.* That means:

- **The line has its own identity and semantics.**
- **The stance remains the separate `balance(O)` representation.**
- **The tie between them remains a separate claim; this ruling does not mint, infer, or repair that
  tie.**
- **Candidate generation remains fenced. L1 does not authorise the matcher or any
  candidate-generation machinery.**
- **The four document-path corpora stand as already accepted** (F3(a)): *their fixtures are evidence
  that the relevant subject / tie is present in those cases, not permission to reinterpret the
  acceptance as a shortcut.*
- **L2 is rejected** — it would require the substrate change 9D already refused.
- **L3 is rejected** — a chooser would violate the one-source boundary.
- **L0 is rejected** — it would leave the semantic question unresolved despite the shape inventory
  establishing that these are occurrences of the same structural question.

**F1 — answered first, and answered *proceed now*.** *The important ordering is: first rule what the
line is; separately, and later, determine how a line gets tied to a stance / subject. That preserves
the matcher boundary rather than smuggling matcher semantics into the line kind.*

**No code is authorised by this ruling.** The next step is the usual separate decision about whether
this ruling actually warrants a build.

**Still unruled, and needed before any build can be scoped** (named here so the build decision is
made with them in view, not around them): **F2** — one kind, with the figure's sort uninterpreted ·
**F4** — the foundation map's last users retire to `KNOWING_SUBJECT_PARTY` · **F5** — 7A's kind
dispute (Pd4) must survive as a dispute about the line's content · **F6** — the ~200-site corpus
staged by document family, the first stage named · **F7** — what must not change.

**One boundary note.** The ruling was recorded as *"D′.11 / document-line kind"*; **D′.11 is a
different question** — composition across relation kinds — and remains named and unopened. This
ruling touches the document line only.

---

## 9. Ruling — Rob, 2026-09-21: F2, F5, F6; the artefact-subject class named; F4 and F7 still open; no build

*Surfacing the second shape first is the right move. The new corpus shape changes the build scope,
but it does not change the §8 ruling about what a document line is.*

### F2 — one kind

**Rule one document-line kind.** *The figure's sort remains uninterpreted by the ontology. I would
not introduce a family keyed by figure sort, and I would not add a sort slot merely to preserve the
distinction that the reader would then have to interpret.* That means the existing distinction is
**deliberately lost at the kind level**:

- same document-line kind → same kind;
- differing descriptions of what the line means → **`content` disagreement**;
- the figure itself remains uninterpreted.

***That is a real semantic reduction, and it is acceptable only because F5 explicitly handles the
consequence. It does not become an accidental loss hidden inside the migration.***

### F5 — (b)

**Rule (b).** Pd4 remains a **kind-dispute** classification, but after the one-kind ruling it can
only occur when the comparison is between **a document line and a non-line kind**. **Two document
lines cannot produce a kind disagreement merely because their opaque `content` differs.** (c) is
refused — *reopening the parse-dispute consumer would be using the migration to manufacture a new
semantic question*; (a) is refused — it would accept the degradation without specifying how 7A's
existing classification changes. **So F5 records the exact consequence of F2 rather than reopening
interpretation.**

### F6 — staged migration, the 21 artefact-subject sites a named correction class

**The stages, each with its own gate:**

1. **SBC** — 4 sites / 2 files.
2. **EOB** — 37 ordinary sites **plus the 21 artefact-subject sites, explicitly tracked as the EOB
   artefact-subject correction class**.
3. **The statement family** — ~117 sites: `statement_figure` · `payment_due` · `minimum` · `rate` ·
   `escrow` — and their named consumers.
4. **`services` / `applied` / `disbursement`** — a separate fourth stage **only if ruled to be figure
   lines**; otherwise **explicitly excluded** from the figure-line migration.

**The 21 artefact-subject sites — not a second kind.** *§8 already says the line is its own kind; it
does not say that every existing representation currently calling itself an `eob_amount` is correctly
shaped for that kind.* They are a **corpus correction class**: *the artefact-subject shape is not the
ruled document-line shape, because it lacks the subject party the ruled line representation
requires.* They **cannot remain silently as-is if F4 moves consumers to `KNOWING_SUBJECT_PARTY`** —
and they **must not be bulk-rewritten before the cases are preserved.** Kn8 is valuable precisely
because it establishes *Rob's sheet establishes that the thing was health, but does not establish
that Rob knows the insurer's figure*. So the corrected representation makes the party subject
explicit **while preserving the provenance distinction**:

> **subject = Lakeview Health; origin = Rob's sheet → `not_knowing`** — rather than letting the migration turn
> the old `not_knowing` into an accidental `undetermined`.

**A representation correction within F6, not a new ontology kind.**

### Scope consequence

F2 one kind · F5 Pd4's surviving (b) behaviour · F6 staged migration with the 21 EOB
artefact-subject sites explicitly corrected rather than ignored. **F4 is still independently
unruled:** these rulings do not silently settle `KNOWING_SUBJECT_PARTY`; they establish **what F4's
migration will have to account for**. **F4 and F7 must be ruled before the build scope is closed.
No build is authorised.**

---

## 10. Ruling — Rob, 2026-09-21: F4 and F7; the 21 → 15 correction; no build

*I agree with the shape of both. There are two places where I would make the ruling especially
explicit so the migration cannot silently erase behaviour.*

### F4 — retire the foundation map for the migrated kind; `KNOWING_SUBJECT_PARTY` replaces it

**(1) The migrated kind no longer consults the foundation map.** Derived strength uses
**`KNOWING_SUBJECT_PARTY` + the origin claim's own strength**. The map is retired for that migrated
kind **stage by stage**, and **remains operative for genuinely unruled kinds**. The registry entry
**must carry `reading_establishes: True`** — *otherwise the new subject-party rule would be correct
but 9D-i would still make reading-sourced lines undetermined: an accidental interaction between two
independent rulings.*

**(2) The 15 artefact-subject sites are a required correction, not an acceptable `undetermined`.**
They must be **restated so the ruled line has its required party subject**, and Kn8 must continue to
produce **subject = Lakeview Health; origin = Rob's sheet → `not_knowing`**. ***The migration may not use the
absence of a party subject as the new semantic answer.*** **F4's gate must demonstrate both:**

- the corrected artefact-subject cases **preserve their evidence-based `not_knowing`**; and
- a genuinely missing party subject elsewhere **still means `undetermined`**, rather than being
  papered over.

**(3) The three mechanism probes move to a neutral unruled kind.** *They aren't line fixtures; their
purpose is to test the map mechanism itself. Once the kind is ruled, leaving those probes attached to
it would falsely make the migration look like it preserved coverage while actually making the tested
branch unreachable.* They move, **assertions unchanged** — *preserving the test's semantic purpose
rather than its old spelling.*

### F7 — the seven fences, and `PARTICIPANT_CANDIDATES` retained

**Ruled as proposed.** The migration must not alter: **(1)** Ab7's tie semantics or
`PARTICIPANT_CANDIDATES`; **(2)** ruled stance subjects and dated role relations; **(3)** the matcher /
importer boundary; **(4)** 7E's reading → origin → weakest-link chain; **(5)** Kn8's
evidence-supported `not_knowing`; **(6)** F5(b) — Pd4 remains line-vs-non-line only; **(7)**
`movement` remains its own kind and is never absorbed by the line kind.

**The candidate-state question, ruled explicitly.** The ruled line kind has **`object: ()`**, so the
**94 party-subject line constructions that currently populate `CANDIDATES` move to `NONE`**, exactly
as the bank-line migration demonstrated. **But that does not retire `PARTICIPANT_CANDIDATES`:** its
ruled meaning remains intact; the migration merely removes the document-line construction sites that
no longer have permission to use it. **Each F6 stage must report the remaining legitimate
`PARTICIPANT_CANDIDATES` users.** If the count approaches zero, *that fact is recorded as a
consequence of the migration rather than quietly converted into a retirement.* ***An empty or nearly
empty current user set is not evidence that the state itself is obsolete. Retirement would require
its own semantic question.***

### The count, corrected in the record rather than carried forward

The **21** artefact-subject figure in §9 was a **shape overcount**. The document-line correction class
is **15 = 14 `eob_amount` + 1 `statement_figure`**; the other six `subject_artefact_id` sites are
**non-line constructions and must not be counted as F6 line migrations.** §9's stage 2 reads with
this correction.

### Result

**F2** one line kind · **F4** subject-party strength replaces the foundation map for that kind ·
**F5** Pd4 survives only line-vs-non-line · **F6** staged migration with **15** artefact-subject line
corrections · **F7** seven semantic fences, `PARTICIPANT_CANDIDATES` retained and not silently
retired. **No build authorisation.** The next step is a **build-scope decision, not an automatic
build authorisation.**

---

## 11. Stage 1 (SBC) — scope ruled and build authorised — Rob, 2026-09-21

**The four-site boundary is correct.** The build may touch exactly `core/database.py`,
`tests/test_plan_identity_fixture.py`, `tests/test_plan_stances_fixture.py`,
`smoke_sections/s99_plan_identity.py` — **and nothing else.** *In particular `plan_identity:206`
remains untouched despite sharing the helper; the defaulted helper parameter is permitted precisely
because it leaves that sibling call unchanged.*

**The name: `document_line`**, not `line_figure`. *That follows F2: the kind names the
representation, not the sort of figure carried by its content; `line_figure` invites the exact
interpretation F2 rejected.* The ruled entry: `subject_party_id` · `object: ()` ·
`reading_establishes: True` · `relational_knowing: True` · `knowing_relation:
KNOWING_SUBJECT_PARTY` · non-symmetric · not a role · **semantically distinct from `MOVEMENT`**, and
that distinction is added as a **permanent semantic guard** — *structural identity is not semantic
identity under F7.7.*

**The F4 precision — accepted.** *For a ruled kind, absence of the required subject is not an
`undetermined` knowledge result; it is rejected at the representation boundary.* So Stage 1 must
prove **missing party subject → refusal**, not *→ `undetermined`*. **The second half of F4's
two-sided proof moves to the genuinely unruled mechanism-probe path in Stage 2, where `undetermined`
is actually reachable.** *That does not weaken F4; it prevents the test from asserting an impossible
state.*

**The six cases accepted** — particularly Sb-3 (an empty foundation map still yields `knowing`),
Sb-4 (Rob-originating evidence yields `not_knowing`), Sb-6 (a missing subject is refused) and Sb-5
(`movement`, the deductible semantics and the candidate-object refusal stay fenced). Sb-1's explicit
distinction from `MOVEMENT` is **retained as a permanent semantic guard**.

**`PARTICIPANT_CANDIDATES`: report, do not pin.** Record **55 mentions before → 53 after**, the two
removed identified as the SBC construction and its assertion. ***Do not turn that inventory number
into a semantic invariant.***

**The four `s99` mutations** are the right crossing points: the ruled line used as a different kind ·
the tie manufactured from `artefact_concerns` · the foundation map restored for the ruled kind · a
candidate object permitted despite `object: ()`. **`s122` remains untouched** except for the
explicitly authorised Ps14 restatement.

**The gate sequence approved exactly as proposed:** registry null → four-site swap → Stage-1 cases →
standalone mutations → full gate → build note. *The registry-only null model should demonstrate that
merely introducing `document_line` has no collateral semantic effect before the corpus starts using
it.*

**Stages 2–4.** The inheritance split is accepted. **Stage 2:** mechanical inheritance allowed, but
the 15 EOB corrections remain **case-by-case semantic restatements**, and the three mechanism probes
move there — **not part of Stage 1**; `unruled_probe_kind` is **not authorised in Stage 1**, and when
Stage 2 opens the name is to be evaluated against the existing ontology and the requirement that it
remain permanently unruled. **Stage 3:** inherits the mechanics, but Pd4's F5(b) consumer restatement
and the one `statement_figure` artefact-subject correction happen **there**, not silently in Stage 1.
**Stage 4: not authorised or semantically ruled.** The corpus reading is useful but is not a ruling —
`services` **excluded** from the figure-line migration, its relationship-statement semantics needing
their own question; `applied` and `disbursement` **candidate** figure lines, whose entry into Stage 4
remains for that stage's semantic opening.

**Stage 1 is authorised to build exactly the four SBC sites and their necessary registry / fixture /
mutation changes.** It is **not** authorised to touch: `eob_amount` · the 15 EOB artefact-subject
sites · `statement_figure` / the statement family · the mechanism probes · consumers · `MOVEMENT` ·
the ruled stances · `PARTICIPANT_CANDIDATES` semantics · `services` / `applied` / `disbursement` ·
any matcher or tie behaviour. **The authorisation is conditional on the gate sequence and build-note
evidence specified. Nothing beyond Stage 1 is authorised.**

---

## 12. Stage 1 (SBC) — built — 2026-09-23

`core/database.py`: **`DOCUMENT_LINE = 'document_line'`** and one registry entry — `subject
('subject_party_id',)`, `object ()`, `reading_establishes True`, `relational_knowing True`,
`knowing_relation KNOWING_SUBJECT_PARTY`, not a role — plus a comment block carrying L1 / F2 / F4 /
F7 and the permanent `MOVEMENT` distinction. **Three non-comment lines of substrate.** The four
authorised sites and nothing else: the map entry retired, the `line()` helper's defaulted
`object_state` (so `plan_identity:206`'s EOB call is untouched), the SBC construction, Pl2's
assertion, and Ps14's two clauses.

**The gate sequence, as ruled.** **(1) Registry-only null model** — the kind introduced, corpus
untouched: plan identity 35/35, plan stances 20/20, 9D-iv 26/26, payment identity 38/38, 9B 26/26,
under_plan 27/27, plan relations 33/33, artefact origin 43/43, artefact reading 43/43, relational
knowing 23/23, 9D-ii 18/18, 9D-i 22/22 — **zero collateral effect**. **(2) The four-site swap** —
both fixtures green, no `sbc_line_figure` anywhere, `eob_amount` at `:206` untouched. **(3) The six
cases** — plan identity 35 → **41**. **(4) Mutations** — `s99` 9 → **13**, all four caught first run;
`s122` 23/23. **(5) The full gate, in a clean scratch worktree at `021b161`** (a second session held
uncommitted `server.py`, `BANK_BROWSER.md` and an untracked `s125_request_host.py` in the shared
tree; the shared-tree run was stopped and is not evidence): **1596 → 1600, 0 failed**, no foreign
section present.

**The oracle.** **Sb-1** the registry as ruled — *and the permanent guard:* the entry is **identical
to `MOVEMENT`'s and a different kind** (an occurrence that is never an identity vs a position about
an identity that exists or will); never merged. **Sb-2** the insurer's own SBC line, read → subject
Lakeview Health, **no object**, a candidate in state, **knowing** because the artefact's established origin *is*
the subject party — **and, F7.3 made executable, the reading yields the line and nothing else: no
`proposition_concerns` claim is manufactured for it, and the artefact's own concerns claim about P
does not become the line's.** **Sb-4** the same figure read from Rob's sheet, still Lakeview Health's line →
**not_knowing**: the laundering guard arrives through the relation, with no foundation type
consulted. **Sb-5** the ruled term keeps the plan as its subject; the line still refused under
`deductible`; a candidates object refused under `document_line`; `movement` untouched. **Sb-6** a
line with **no party subject is refused at the representation boundary** — the F4 precision.

**Sb-3, and a correction found by building it.** The case as first written asserted that an **empty**
foundation map leaves the line knowing. It does not: with the map empty the line reads
**undetermined** — not because the kind consults it, but because **C3's second link** (how well the
artefact's origin is established) reads **`ARTEFACT_ORIGIN`'s own map entry**, which is separately
ruled (`ARTEFACT_ORIGIN.md` s4) and untouched by F4. So the case now states F4 exactly: a **hostile**
entry for `document_line` changes nothing (the relation answers), dropping `ARTEFACT_ORIGIN`'s entry
makes it undetermined **by the origin link, never by the kind**, and `ARTEFACT_ORIGIN`'s entry alone
suffices. *F4 retires the migrated kind's own map membership — not the chain's second link.*

**`PARTICIPANT_CANDIDATES`, reported and not pinned, in the two measures the ruling distinguishes:**
**raw textual mentions 55 → 56** (stage 1's own refusal probes — Sb-5, Sb-6, Ps14 — each name the
state in order to prove it is refused); **legitimate construction sites: one removed**, the SBC line,
which no longer has permission to use it. *The raw count rising while the construction count falls is
why the ruling said report both and pin neither.* The state's ruled meaning is untouched.

**Untouched, by name:** `eob_amount` — including `plan_identity:206` in the same file — the 15
artefact-subject sites, `statement_figure` and the statement family, the mechanism probes,
`unruled_probe_kind`, every consumer, `MOVEMENT`, the ruled stances, `services` / `applied` /
`disbursement`, and any matcher or tie behaviour. **Stages 2–4 remain unauthorised.**

---

## 13. Stage 1 (SBC) — accepted — Rob, 2026-09-24

**Accepted as built and ruled: `83c5577`, clean-worktree gate 1600 / 0.**

**Sb-6 stands; refusal is correct.** *The committed Stage 1 ruling at `021b161` is the controlling
scope:* a ruled `document_line` with a missing required subject is a **representation refusal**; *it
does not become `undetermined`*; the genuinely-missing-subject → `undetermined` proof **belongs to
the unruled mechanism-probe path in Stage 2**; **Stage 1 therefore has six cases, with Sb-6
asserting refusal.** A parallel session's copy of the scope review, which read *"five cases /
absent subject → undetermined"*, **is stale — it is to be corrected before that session's acceptance
record is finalised, and never used to alter this implementation.**

**The gate numbers, as treated.** **1600 / 0 is the verified Stage 1-only gate and remains the
authoritative Stage 1 evidence** (a scratch worktree at `021b161` carrying only the four authorised
files). **1622 / 0 is a reported combined gate** — this session has not independently verified it,
and it is not Stage 1 evidence. **Nothing about the F12 / bank-window acceptance changes the Stage 1
semantic ruling.**

**Stage 1 (SBC): OPENED → RULED → BUILT → ACCEPTED.** **Stage 2 remains unopened and
unauthorised**, and with it the 15 EOB artefact-subject corrections, the three mechanism probes and
their neutral kind, Stage 3's statement family with Pd4's F5(b) restatement, and Stage 4's
undecided `services` / `applied` / `disbursement` question.

---

## 14. Stage 2 (the EOB) — opened 2026-09-24; no code

*Opened by Rob. Stage 1 is accepted and closed (§13). Stage 2 is F6's second stage: `eob_amount`'s
ordinary sites, **the artefact-subject correction class**, and **the three map-mechanism probes'
neutral kind**. The inventory comes first, as item 14's lesson and F6 require — and it does not
match the description Stage 1 carried forward.*

### 14.1 What is fixed

**§11 / §13 (ruled, built, accepted):** `document_line` — subject the party, `object ()`,
`reading_establishes True`, `KNOWING_SUBJECT_PARTY`, distinct from `MOVEMENT`; **a ruled kind's
missing required subject is a representation refusal, never `undetermined`** (Sb-6). **F4:** the map
retires **for the migrated kind only** and stays operative for genuinely unruled kinds;
**F4's gate is two-sided** — the corrected cases keep their evidence-based `not_knowing` (Kn8), *and*
a genuinely missing party subject still means `undetermined`. **F6:** stage 2 is the EOB's ordinary
sites **plus the artefact-subject class**, each stage its own gate; **the artefact-subject sites are a
corpus correction, not a second kind**, and *must not be bulk-rewritten before the cases are
preserved*. **The probes:** they move to a neutral unruled kind, **the name not invented but
evaluated against the existing ontology**, and it must remain permanently unruled. **F7:** the seven
fences; `PARTICIPANT_CANDIDATES` reported per stage, never pinned. **Sb-3's finding:** F4 retires the
kind's own map membership — **not C3's second link through `ARTEFACT_ORIGIN`**.

### 14.2 The inventory, by shape — and what it shows

All 37 `eob_amount` sites, classified by what they construct:

| population | sites | files |
|---|---|---|
| **A — ordinary party-subject lines** (mechanical) | **7** | chain strength ×2, expense stances (a refusal probe), obligation-in-respect-of, plan identity, relational knowing ×2 |
| **B — provenance cases, artefact-subject** (Rob's Kn8 class: correct to party-subject) | **3** | relational knowing Kn5 / Kn8, correspondence's *said* |
| **C — slice-3 mechanism cases, artefact-subject** | **12** | artefact reading ×7, artefact origin ×5 |
| **D — the map probes** | **3** | artefact origin ×2, artefact reading ×1 (two of these are inside C's files) |
| **E — map entries** | **7** | seven fixtures' `KNOWING` dicts |
| **F — the absence pin** | **1** | expense stances: *`eob_amount` not in `RULED_KINDS`* |
| **G — the retraction pair** | **2** | utterance retraction |

**The finding that matters: the "15 artefact-subject sites" are not one class.** Stage 1 carried them
forward as a single corpus correction. By shape they are **three** populations with three different
right answers:

- **B (3 sites) — Rob's ruled class.** Kn5 (*Rob says the EOB says $412*), Kn8 (*one sheet, two kinds*),
  correspondence's *said*. Here the artefact-subject shape is **incidental**; the case is about **who
  knows what**, and the ruled correction — *subject Lakeview Health, origin Rob's sheet → `not_knowing`* —
  preserves it exactly.
- **C (12 sites) — where the artefact-subject shape IS the case.** `artefact_reading` asserts *a
  reading evidences a proposition **whose subject is the artefact***, and *the parse dispute is
  computable by structure: **same kind + subject**, two contents*; `artefact_origin` walks the
  origin → strength chain on artefact-subject claims. **Correcting these to a party subject deletes
  their subject matter** — the same failure mode as leaving the probes attached to a ruled kind, in
  the other direction. *Reading: they belong with the probes in the neutral unruled kind, not in the
  correction class.*
- **G (2 sites) — the retraction pair.** *"That is false" is a domain proposition with negative
  content, not a `contradiction` kind*, plus *a reading whose origin is multiple → undetermined*. The
  first is a borderline B; the second is **the only live demonstration in the corpus of the
  `undetermined` branch on a reading path**, and F4's second half depends on something of its shape.

**So the neutral-kind population is not 3 but ~14–17**, and the correction class is not 15 but **3
(+2 borderline)**. The name question becomes correspondingly more load-bearing.

### 14.3 The neutral kind — surfaced, not invented

**A neutral unruled kind already exists in the record's practice, in two conventions:**

- **`'x'`** — `evidence_substrate`'s kind for *a proposition with no semantics*, used to exercise the
  participant-state discipline (≈8 sites). Obviously never a domain kind; nobody would rule it.
- **`'some_future_kind'`** — `correspondence`'s kind for *a kind the record has not ruled yet* (1
  site), used to show the substrate does not require a ruling to represent something.

*Reading: adopt `'x'`* — it already means *unruled, on purpose*, it is the older convention, and the
probes are substrate tests exactly as `evidence_substrate`'s are. `'some_future_kind'` reads as *a
kind that will be ruled*, which is the opposite of the requirement. **Either way the name is not
invented, and `unruled_probe_kind` is withdrawn.** A **permanent** absence pin (*this kind is never
in `RULED_KINDS`*) should accompany it — the one absence pin the record means to keep. **Rob's.**

### 14.4 Findings

**S2-F1 — the class splits three ways (14.2).** *Reading:* **B (3) corrected** as Rob ruled; **C (12)
and D (3) moved to the neutral unruled kind**, assertions unchanged; **G (2) ruled individually**.
**This is the finding that decides Stage 2's size and must be ruled before any code. Rob's.**

**S2-F2 — the neutral kind's name (14.3).** *Reading:* `'x'`, with a permanent absence pin. **Rob's.**

**S2-F3 — F4's second demonstration may be unreachable as stated.** Stage 1 established that for a
**ruled** kind a missing subject is **refused**, so *a genuinely missing party subject → `undetermined`*
cannot be shown on `document_line` at all. On the **unruled** path the `undetermined` branch is
reachable and already demonstrated twice — `artefact_origin:160` (the kind has no map rule) and
`utterance_retraction:216` (the artefact's origin is multiple). *Reading:* F4's second half is
**satisfied by the unruled path's existing demonstrations, carried into the neutral kind**, and the
record should say so rather than leave an untestable clause standing. **Rob's.**

**S2-F4 — populations A, E, F are mechanical** — 7 constructions (`CANDIDATES` → `NONE`), 7 map
entries retired, 1 absence pin retired — *provided* the strength is unchanged, which the null model
must show before any case is added. Two of A's sites are **7E's chain cases** (`L3`, the capture `V`),
where the strength is the whole point. *Reading:* as stated. **Rob's.**

**S2-F5 — what Stage 2 must not touch.** `statement_figure` and the statement family (stage 3),
Pd4 / 7A (stage 3), `services` / `applied` / `disbursement` (stage 4, unruled), `MOVEMENT`, the ruled
stances, the matcher, `PARTICIPANT_CANDIDATES`' meaning, and every file the bank-window session owns
(`server.py`, `launch.py`, `migrate.py`, `static/js/app.js`, `bank_window.py`, `s125`, `s126`,
`BANK_BROWSER.md`). *Reading:* as stated; the build runs in this session's own worktree and commits
by explicit path. **Rob's.**

### 14.5 Cases

| # | Case | today | under the reading |
|---|---|---|---|
| **Eo1 (A)** | the EOB line on the insurer's own EOB, read | `eob_amount`, party subject, candidates object, knowing by map | `document_line`, no object, knowing by the relation — unchanged in substance |
| **Eo2 (B / Kn8)** | the insurer's figure on **Rob's sheet**, read | not_knowing by map (person ∉ institution) | **subject Lakeview Health, origin Rob → not_knowing by the relation** — the ruled correction, evidence-based |
| **Eo3 (B / Kn5)** | Rob's utterance *the EOB says $412* | not_knowing | subject Lakeview Health, origin Rob → not_knowing |
| **Eo4 (C)** | *a reading evidences a proposition whose subject is the artefact* | the case | **unchanged, under the neutral kind** — migrating it would delete it |
| **Eo5 (C)** | the parse dispute by structure: same kind + subject, two contents | the case | unchanged, under the neutral kind |
| **Eo6 (D)** | the map's own branches: no rule → undetermined; a hostile entry → not_knowing | the case | unchanged, under the neutral kind — **and this is F4's second half** (S2-F3) |
| **Eo7 (G)** | a reading whose artefact origin is **multiple** → undetermined | the case | unchanged; the `undetermined` branch stays live |
| **Eo8 (G)** | *"that is false"* is a domain proposition, not `contradiction` | the case | ruled individually (B or C) |
| **Eo9 (7E)** | the chain cases `L3` and the capture `V` | strength through origin, weakest link | **identical** — the null model's requirement |
| **Eo10 (the null model)** | every existing outcome | — | identical before any case is added |

### 14.6 Candidate — pending the ruling

No registry change (`document_line` exists). Population **A** migrated (7 constructions, `CANDIDATES`
→ `NONE`), **E**'s 7 map entries and **F**'s absence pin retired, **B**'s 3 corrected to party-subject
with their assertions unchanged, **C**'s 12 and **D**'s 3 renamed to the neutral kind with their
assertions unchanged, **G**'s 2 per ruling. Fixture cases: Eo1–Eo3 and Eo9 in the migrated files; the
neutral kind's permanent absence pin. Mutations (`s97` / the relevant sections): the neutral kind
ruled into the registry · a corrected B site reading `undetermined` instead of `not_knowing` (the
Kn8 guard made executable) · the migrated line admitted as a ruled stance · the map restored for
`document_line`. `PARTICIPANT_CANDIDATES` reported before / after in both measures.

### 14.7 Ruling sought

> **(1) S2-F1:** the three-way split, or the single correction class as first described. **(2) S2-F2:**
> `'x'`, `'some_future_kind'`, or another name — with the permanent absence pin. **(3) S2-F3:** F4's
> second half satisfied by the unruled path's existing demonstrations. **(4) S2-F4, S2-F5** as read.
> **(5)** whether **G**'s two sites are B or C. Nothing here authorises code.

---
