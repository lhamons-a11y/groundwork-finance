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
