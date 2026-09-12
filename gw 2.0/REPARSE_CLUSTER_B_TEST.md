# Cluster B on the re-parse — referent, proposition, verdict strength, one case

> Status: **Doctrine test, 2026-09-12. No decision. No field on `Evidence`, no proposition
> type, no lattice change, no change to `qualifying_amount`, `_state_from` or `resolution()`.**
> Cluster B is the one cluster the map left without a joint pass. Rob opened it on **one case
> only — the re-parse** (`DOCUMENT_IDENTITY_CASES.md` D3/D3b, `VALUE_DISAGREEMENT_CASES.md`
> V4) — and on the arrows it actually exercises:
>
> ```text
> document referent (4)  ↔  proposition space (5)  →  verdict strength (6)
> ```
>
> **The opening questions — Rob's, from the case pass, never answered by a test:**
>
> > *Can we identify what proposition is being disagreed about without making the document
> > itself the proposition?*
> > *Does verdict strength have an independent dimension, or does it inherit whatever evidence
> > representation happens to exist?*
>
> **Discipline, his:** case evidence first; one ruling in his words; anything the case does
> not establish stays fenced. And the specific hazard for this cluster: **do not let referent,
> proposition space and verdict strength become a generalised ontology.** The test is built to
> exercise arrows, not to define objects.
>
> **Fence.** Testimony *about* a document (D5, D7 — the asserted-identity referent), four
> balance figures (U6), multi-source resolution (the pending fixture), the rank-3 tie
> (`knowing[-1]`), and the temporal latent are all adjacent and none is admitted. Where a cell
> would need one, it says so.

---

## 0. The case, as recorded, and what the module does with it

**One EOB, imported twice.** The first import parses the patient-responsibility line as
**$412**; the second parses the same line as **$4.12**. Both readings mark the transaction
*health* on the content axis. The transaction itself is $950.

```python
record_evidence(c, CONTENT, source=IMPORTED_EOB, supports=True, amount=412)
record_evidence(c, CONTENT, source=IMPORTED_EOB, supports=True, amount=4.12)
```

What the module holds (`core/classification.py`):

| | as built | the consequence |
|---|---|---|
| `Evidence` | `(axis, source, supports, amount, recorded_at)` — `source` is a **type** (`IMPORTED_EOB`), `amount` is **scope** by docstring, `supports` is one bit about *health* | two readings of one artefact are byte-identical to two artefacts; two values are two scopes, not two claims |
| `_state_from` | `knowing[-1]` → `IMPORTED_ATTESTED`, rank 3 | no disagreement registers — both say *yes* |
| `resolution()` | no dissent on the bit → `none` | the projection is faithful to a record that cannot say the readings disagree |
| `qualifying_amount` | `attested[-1]` → **$4.12** (or **$412.00** in the other order) | the tax figure is decided by recording order, with no trace that another reading existed |

**D3b, the variant:** the two readings disagree on the *bit* — *not-health* then *health*.
Now `resolution()` reports `self_reversal, resolver = imported_eob` — *the EOB source reversed
itself*. In D3b no source reversed anything; one document was read two ways. The projection is
correct and the record it projects assigns a **wrong causal story**.

**What the case presupposes, and it matters for 4:** *two parses of one thing* requires the
thing. Groundwork parsed bytes, twice. The re-parse is therefore a case about an artefact
**Groundwork holds** — it cannot exercise the asserted-identity referent (*"the March EOB"*,
described by the user, never held), because nothing can be re-parsed that was never parsed.

---

## 1. The candidates the case can exercise — and the one it cannot

```text
4   R-HELD      the referent is an artefact Groundwork holds bytes of; readings are of it
    R-ASSERT    the referent is an identity the user asserts; nothing is held    ← NOT EXERCISED
                                                                                   by this case
5   P-CLOSED    the space stays two boolean axes; amounts are scope
    P-OPEN      propositions can carry a value; a reading is a claim about a proposition

6   evaluated only where 5 = P-OPEN, because under P-CLOSED there is no value verdict to
    have a strength (the gate the map recorded)
```

Two cells for 4 × 5, then 6 inside the surviving one. Each cell: what a later observer must
hold to understand the disagreement · what is context · the sentence · does it hold.

---

## 2. The cells

### R-HELD · P-CLOSED

- *Observer holds:* the artefact's identity; that it was read twice; two `(yes, amount)`
  entries. With a referent, the two readings are **findable** as readings of one thing —
  corroboration no longer counts them as two sources (D1/D2 repaired).
- *What it cannot hold:* that the readings **disagree**. `amount` is scope; there is no
  proposition *the document says X* for $412 and $4.12 to be competing answers to. The
  disagreement exists in the world and not in the record.
- *Sentence:* *"Your EOB was imported twice."* True, and it is all that can be said.
- *Tax:* still `attested[-1]`. The referent changed nothing about the figure.
- **Fails the case.** Referent without proposition makes readings findable and leaves the
  disagreement unsayable — the case doc's own line, now measured.

### R-HELD · P-OPEN

- *Observer holds:* the artefact A; two readings **as claims about a proposition whose subject
  is A** — *A's stated patient-responsibility is $412* / *… is $4.12*; and that they compete.
- *Resolvable, and by whom:* Groundwork holds A. A third reading — a re-parse, or the user
  looking at the rendered document — settles *what A says*. This is a **parse dispute**,
  resolvable inside Groundwork, with no adjudication between sources because there is one
  source.
- *Sentence during:* *"Two readings of your EOB disagree about the amount — $412 or $4.12."*
  *After:* *"Re-reading it: $412."* Both true.
- *Tax:* from the **resolved** reading; **`UNKNOWN` while unresolved** — never `[-1]`.
  Honest-null at the evidence layer, where today the fallback is position.
- **Holds.** And it holds with **two propositions per value, not one** — see §3.

### R-ASSERT · (either) — not exercised

The user says *"the March EOB shows $412"*, later *"…$4.12"*. That is one person's testimony
twice, about a document Groundwork never read — D5's referent, D8's utterance — and its
disagreement is a **user self-reversal**, not a parse dispute. The re-parse case cannot reach
it. **Fenced, and stated so R-HELD's survival is not read as R-ASSERT's failure.**

---

## 3. Rob's first question, answered from the case

> *Can we identify what proposition is being disagreed about without making the document
> itself the proposition?*

**Yes — and the case forces something sharper: there are two propositions, and the readings
disagree about only one of them.**

```text
P-subject   "artefact A states patient-responsibility = X"     subject: the document
P-world     "patient-responsibility for this claim   = X"     subject: the world
```

The $412/$4.12 dispute is about **P-subject**. Resolving it — re-reading A — establishes *what
the document says*. It does **not** establish P-world: the document may be for a different
patient, withdrawn, or wrong (D6). P-world is *supported by* the resolved P-subject at one
source's rank; it is not identical to it.

The document is never the proposition. It is the **subject** of P-subject and a **source** for
P-world — the two roles the case pass named, now doing different work in one case. And the
module's current shape collapses them: *"successful parsing establishes the fact outright, with
no state for 'the document contained this value'"* (`EVIDENCE_MATRIX.md` finding 3). The
re-parse is where that collapse costs a tax figure.

**Arrow 4 ↔ 5, on this case: confirmed mutual constraint, no gate.**
- 5 constrains 4: P-subject cannot be *posed* unless the record can name its subject — a
  referent (R-HELD·P-CLOSED shows the referent alone does nothing; P-OPEN gives it a job).
- 4 constrains 5: P-subject cannot be *resolved* unless the subject can be re-read — R-HELD.
  Under R-ASSERT the same proposition is posable and unresolvable by Groundwork.
- Neither gates: R-HELD·P-CLOSED is a coherent record (findable, unsayable); P-OPEN over
  utterances (D8) is coherent with no referent at all.

---

## 4. Rob's second question, answered from the case

> *Does verdict strength have an independent dimension, or does it inherit whatever evidence
> representation happens to exist?*

Take R-HELD·P-OPEN and ask what the strength of the verdict *"A says $412"* is, after the
readings $412 · $4.12 · (re-read) $412.

- **What the lattice would say if asked:** it ranks support for a boolean. Two readings *for*
  $412 and one *against*? That is not what happened — $4.12 is not evidence against $412 on an
  axis; it is a competing value. The lattice has no operation for this. Under P-OPEN, 6 is not
  merely *posable* (V3 already made it that); it is **forced open** — a value verdict exists
  and the built notion of strength cannot be applied to it at all.
- **What counting would say:** two readings agree on $412, one on $4.12 → "$412, 2:1". **Wrong,
  and the case says why:** all three are readings of one artefact. `DOCUMENT_IDENTITY_CASES.md`'s
  boundary — *source instance ≠ source independence* — means **re-reading does not corroborate.**
  Three readings of A are one source. The strength of *"A says $412"* is not a count; it is a
  state — *disputed* or *resolved* — and resolution is by a reading that settles the parse,
  not by a majority.
- **And P-world's strength is untouched by any of it.** One EOB, rank 3, before the re-parse
  and after. The re-parse changed *which value* the source attests; it changed nothing about
  how many sources attest it.

So the answer to Rob's question is **independent — and the case shows two strengths where the
map had one**:

```text
strength of P-subject    a resolution state: disputed | resolved     (not a rank; not a count)
strength of P-world      the lattice's rank over sources             (unchanged by re-reading)
```

Neither is inherited from the representation. The representation — three `Evidence` rows —
would suggest *corroborated* to a naive fold and *contradicted* to the built one; the correct
answer is *one source, parse resolved*, and that is a **function chosen over the graph**, not
read off it. `EVIDENCE_MATRIX.md` already said strength is *a function over the graph,
recomputed on read*; the case says **which functions**, and that there are two.

**Arrow 5 → 6, on this case: gate confirmed, and stronger than "consequence".** Under P-OPEN the
value verdict exists and has *no* strength under the built lattice — 6 is not a refinement
once 5 opens, it is a hole. And **6 ──X──► 5 held**: nothing about resolution states says
whether the space should open.

**An arrow the case exercises that the map does not draw: 4 → 6.** *Source instance ≠ source
independence* is a referent boundary (4), and it directly constrains what any strength function
(6) may count: readings of one referent are never corroboration. The map routed everything from
4 through 5. The case shows 4 reaches 6 on its own — as a **constraint on 6's admissible
answers**, not a gate. Recorded for the map; the map is not edited (Rob's rule).

---

## 5. What the case does to Q2's projection — a wiring condition, not a decision

D3b: `resolution()` reports `self_reversal by imported_eob` for two readings of one artefact.
Under R-HELD·P-OPEN the two readings are a parse dispute, and its resolution kind is *neither*
`superseded`, `reaffirmation` nor `self_reversal` — those are the shapes of **source** history,
and here no source changed its stance. `resolution()`'s docstring says it *reads the knowing
evidence in order and reports the shape of the history*; with readings distinguishable from
sources, the history has a shape the projection has no name for. **Document identity is
upstream of Q2's fidelity** — confirmed on the code, and the consequence is that `resolution()`
needs a reading-level kind before it can be trusted on a re-parsed record. Not designed here.

---

## 6. What the test does not prove

1. **Anything about R-ASSERT.** The case presupposes held bytes. Whether an asserted identity
   is a sufficient referent for testimony about a document is D5/D7's question and stays there.
2. **Whether P-subject and P-world are two proposition *kinds* or one proposition with a
   subject field.** The case forces the *distinction*; representation is design.
3. **What "resolved" requires for a parse dispute.** A re-read, a user inspection (C9: *ask
   them to inspect*), or a rendered-document confirmation — the case shows resolution is
   inside Groundwork's reach under R-HELD and does not choose the mechanism.
4. **U6.** Four balance figures with no referent and no shared proposition are a different
   case — possibly four propositions — and the two-strength result above should not be assumed
   to cover them.
5. **The tie.** `knowing[-1]` between `USER_STATED` and `IMPORTED_EOB` is a *source* conflict;
   the re-parse is a *reading* conflict. The case says they are different in kind (D3b/D4's
   own finding); it does not touch the tie.

---

## 7. Decision remaining — Rob's

4 and 5 jointly, on this case: whether the space opens with a subject proposition and a held
referent — the only combination the re-parse survives under — and 6, now shown to be two
functions rather than one rank, with one hard constraint from 4 (re-reading never corroborates)
and one from the case (the built lattice cannot express a value verdict's strength at all). No
object is defined here; three arrows are, and one the map did not have.

---

## 8. Ruling — Rob, 2026-09-12. A genuine Cluster B doctrine result, not an implementation observation.

**4 and 5 are jointly necessary, and neither is sufficient alone.** For a value proposition to
be open to disagreement, Groundwork needs (1) a **held document referent** identifying the
source instance, and (2) a **proposition space capable of distinguishing what the document says
from what the world is claimed to be.** The document is therefore the *subject* of one
proposition, not the proposition itself:

```text
P-subject   "Document A states patient-responsibility = $412."
P-world     "Patient-responsibility for this claim   = $412."
```

The `$412 → $4.12 → $412` sequence is a disagreement about P-subject. Re-reading resolves what
A says. It does not establish that A's statement is true of the world.

> **Frozen: 4 ↔ 5 is a joint opening condition, not a hierarchy.** A held referent without an
> open proposition cannot express the disagreement; an open proposition without a held referent
> cannot establish what source instance is being disputed.

**Not generalised to R-ASSERT.** That remains D5/D7.

**6 is independent — and the map's "one strength" was wrong.** Two different functions are
currently being called strength, and they are not two values on one ladder:

```text
P-subject strength   =  resolution state of the source's reading      disputed | resolved
P-world strength     =  evidentiary rank over independent sources
```

Three `Evidence` rows are not three independent attestations; they are three readings of one
document. The second `$412` cannot corroborate the first. The world-level evidence is exactly
as strong after the re-parse as before — one independent source; the parse changed *which
value* that source attests, not the number or independence of sources.

> **Frozen: 6 does not inherit strength from evidence representation.** Strength is a function
> evaluated over the evidence graph, and **the function depends on which proposition is being
> evaluated.** This makes *recomputed on read* more precise without replacing it.

**4 → 6 is real — recorded as a constraint, not promoted to a gate:**

> Document referent constrains admissible verdict strength because multiple readings of one
> referent cannot constitute independent corroboration.

The map was incomplete. **The map is not edited during a case pass**; the arrow is recorded
here and the map is revised only as a later, explicit map-maintenance step.

**Q2 consequence — real, kept out of today's doctrine.** `self_reversal` and its siblings
describe *source* history; this case exposes *reading* history.

> `resolution()` is not trustworthy on a re-parsed record until reading-level resolution is
> represented distinctly from source-level resolution.

An implementation/design consequence, not a decision about what the new kind should be.

**Frozen from this case:**

```text
Cluster B — re-parse

4 ↔ 5     joint opening condition: held document referent + open proposition space;
          neither alone sufficient; document ≠ proposition
5 → 6     confirmed as a gate; proposition space must identify what is being evaluated;
          6 is not merely a refinement of 5
6         two independent functions: P-subject → resolution state; P-world → evidentiary rank
4 → 6     newly discovered constraint; one referent ≠ multiple independent sources; not a gate
repr.     does not determine verdict strength

fenced    R-ASSERT · proposition representation (two kinds vs a subject field) · resolution
          mechanism · U6 · the USER_STATED ↔ IMPORTED_EOB tie · the reading-level resolution kind
```

**Not authorised by this case:** defining the proposition object; inventing a strength type
hierarchy; resolving U6; settling the tie.

**The strongest result is the negative one:** the three concepts cannot be collapsed into a
single evidence-row interpretation without producing exactly the false `$412`/`$4.12` story that
prompted this pass.
