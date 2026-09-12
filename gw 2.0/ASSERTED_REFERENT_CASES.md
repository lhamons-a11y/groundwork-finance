# R-ASSERT — can an asserted, never-held document be P-subject's referent?

> Status: **Case set, 2026-09-12. Evidence mode. No decision, no representation, no rank.**
> Fourth fence opened in evidence mode. Rob's narrow question:
>
> > **Can testimony about a document that Groundwork never held establish a sufficient document
> > referent for P-subject?** Does an assertion that identifies a particular external
> > document/view give P-subject a referent even though Groundwork possesses no bytes of it?
>
> **Not whether testimony is true. Not its strength. Not whether the portal should be trusted.**
> The hard stopping boundary, his: do not decide whether testimony establishes the proposition;
> do not decide its evidentiary strength; do not decide whether two testimonies corroborate; do
> not design representation. **Referent sufficiency, nothing beyond it.**
>
> **What a referent does, from the Cluster B ruling** — the four things each case checks:
>
> ```text
> POSE      P-subject can be stated:  "<referent> states X"
> FIND      later readings/testimonies can be recognised as being about the same referent
> RE-READ   a dispute about its contents can be resolved against it
> RETRACT   retraction reaches everything derived from it
> ```
>
> A held artefact supplies all four. The cases ask which an asserted identity supplies.
>
> **The isolating instance, from the captured-portal ruling (C5):** *"the portal showed $1,925"*
> — the utterance is held, the portal is not. No new doctrine is needed to pose the question.

---

## Case RA1 — "The statement dated Sept 1 says $1,925."

Issuer P, date Sept 1, kind *statement*. Not imported.

- **POSE:** yes. *Statement(P, Sept 1) states balance $1,925.* The subject is a **described
  document** — a description that would pick out a document if one exists. P-subject has a
  subject.
- **FIND:** yes, **by description-matching.** If a second household member later says *"the
  Sept 1 statement says $1,925"*, or a PDF from P dated Sept 1 is later imported, the record
  can recognise these as being about the same described document — because the descriptions
  match. Unlike a held referent, where identity is bytes, **this identity is an inference** (same
  issuer + date → same document), and an inference can be wrong (RA2).
- **RE-READ:** **never.** Nothing to read.
- **RETRACT:** the utterance, and what was derived from the utterance. Nothing was ever derived
  from the document.

**Forces finding 1.** An asserted referent that **individuates** — names one particular
document by issuer, date and kind — is sufficient to **pose** P-subject and to make later
readings **findable** as readings of the same subject. It supplies two of the four; the two it
supplies are the ones that concern *which document*, and the two it cannot are the ones that
concern *what the document contains*.

## Case RA2 — two statements, same issuer, same date; one ambiguously described

P issued two statements dated Sept 1 — a regular one and a corrected one, or one per account.
The household says *"the Sept 1 statement says $1,925."*

- **POSE:** only as *one of {A, B} states $1,925* — a proposition about a document matching a
  description, not about a document. **Underdetermined.**
- **FIND:** description matches two candidates; the link is ambiguous. D7's default applies:
  the relationship is *unresolved*, not guessed.
- And the sharper point: **the ambiguity can arrive later.** On Sept 2 the description was
  unique; when the corrected statement is imported in October, RA1's referent becomes RA2's.
  **An asserted referent's sufficiency can degrade as the record grows.** A held referent's
  cannot — bytes are bytes.

**Forces finding 2.** Sufficiency is a property of the description **relative to the record's
candidates**, not of assertion as such — and it is **not monotonic.** A description that
individuated yesterday may not tomorrow. The record has to be able to hold *asserted referent,
currently ambiguous* without collapsing it to either candidate by position.

## Case RA3 — "The portal showed $1,925." No retained view.

C5, exactly.

- **POSE:** yes. *View(S's portal, ~Sept 1) displayed $1,925.* The subject is a **rendering at
  a moment** — an event, not a document.
- **FIND:** **never, in the forward direction.** There is exactly one rendering the household
  saw and no later import can *be* it; a capture made later is a different rendering. The
  referent is a **singleton**: it individuates perfectly and can never be re-identified.
- **RE-READ / RETRACT:** as RA1.

**Forces finding 3.** Asserted referents come in **two kinds**: **re-identifiable** (RA1 — a
document that exists somewhere; a later held import may turn out to be it) and **singular**
(RA3 — a view that existed once; nothing can ever be brought into correspondence with it). Both
pose P-subject. Only the first has a path from asserted to held.

## Case RA4 — the household later says the portal showed $1,295

Same household member, a week later: *"actually it showed $1,295."*

- Is this a **re-reading dispute** (two readings of one referent, resolvable by re-reading) or a
  **testimony conflict** (one source, two utterances, a self-reversal)?
- The referent is RA3's singleton. Nothing can be re-read. The second utterance is not a
  reading of the view; it is the same source revising its report. D8: two utterances, one
  source, `recorded_at` separates them.
- **A testimony conflict.** And note what that means for Q2's projection: `resolution()` would
  report `self_reversal, resolver = user_stated` — and here that is **correct.** The projection's
  source-history kinds were *wrong* for the re-parse (D3b — two readings of a held artefact
  reported as a source reversing) and are *right* here, because with an asserted referent there
  are no readings, only reports.

**Forces finding 4.** **The kind of disagreement is fixed by the referent's kind, not by the
values.** Held referent → a disagreement about contents is a *parse dispute*, resolvable against
the artefact, and source-history kinds misdescribe it. Asserted referent → a disagreement about
contents is *always* a testimony conflict, and source-history kinds describe it correctly. The
reading-level resolution kind that the re-parse ruling left as a wiring hazard is needed **only
for held referents**.

## Case RA5 — two household members independently describe the same never-held statement

Both say *"the Sept 1 statement says $1,925."* Neither imports it.

- **FIND:** yes — the descriptions match, so the record can say *two reports of one described
  document.* That is the FIND property working for an asserted referent: **shared subject by
  description.**
- Whether the two reports **corroborate** is fenced, and this case is placed so the fence is
  visible: findability says *they are about one thing*; it says nothing about whether two
  people saying it makes it stronger. (For P-ack it could not — one knowing party; but that is
  the acknowledgment ruling's, not this case's.)

**Forces finding 5.** An asserted referent can be **shared** across testimonies. Findability by
description is real and is what makes "about the same document" sayable. It is an inference at
each link, unlike held identity, and it stops exactly at *same subject* — it does not reach
*corroboration*.

## Case RA6 — "A letter from the hospital said I owe $1,925."

No date. No kind. "The hospital" — P has sent several letters.

- **POSE:** **no.** *Some document from P states $1,925* is an existential, not a proposition
  about a referent. There is no subject to be P-subject's.
- **FIND:** nothing to match against.
- What the testimony *is*: closer to D5's *"it was health"* than to *"the EOB says it was
  health"* — a report about the world **routed through** an unidentified document. The
  document adds nothing the record can hold; what is left is *the user reports having been told
  X* — a world-flavoured testimony with a vanished intermediary.

**Forces finding 6.** There is a **threshold of individuation** below which an asserted
referent does not exist. Above it (RA1, RA3), P-subject is posable and findable; below it
(RA6), the testimony is not about a document at all in any sense the record can use, and
must not be recorded as if it were.

---

## What the cases force

1. **An individuating assertion is a sufficient referent to pose P-subject and to make
   readings findable** (RA1). It supplies POSE and FIND; it never supplies RE-READ; RETRACT
   reaches only the utterance.
2. **Sufficiency is relative to the record's candidates and is not monotonic** (RA2). An
   asserted referent can become ambiguous when a second candidate is imported later, and the
   record must be able to hold *currently ambiguous* without choosing by position.
3. **Two kinds of asserted referent**: re-identifiable (a document somewhere) and singular (a
   view once) (RA3). Both pose; only the first can ever become held.
4. **The kind of disagreement follows the referent's kind** (RA4). Asserted → always a
   testimony conflict, and `resolution()`'s source-history kinds are correct for it. Held →
   a parse dispute, for which they are wrong. The reading-level kind is a held-referent need
   only.
5. **Asserted referents can be shared by description** (RA5) — *same subject* is sayable;
   corroboration is not reached.
6. **Below individuation there is no referent** (RA6); the testimony is about the world through
   a vanished document and must not be recorded as being about a document.

---

## The fence's question, answered by the cases — not ruled

> *Can an assertion identifying a particular document/view give P-subject a referent with no
> bytes held?*

**Yes — for exactly what a referent's identity does, and for nothing a referent's contents do.**

```text
                        POSE    FIND                   RE-READ   RETRACT
held artefact           yes     yes (bytes)            yes       reaches derived facts
asserted, individuating yes     yes (by description;   never     the utterance only
                                an inference; can
                                degrade)
asserted, singular      yes     never re-identified    never     the utterance only
below individuation     no      —                      —         —
```

The Cluster B ruling said *an open proposition without a held referent cannot establish what
source instance is being disputed.* The cases refine it without contradicting it: an asserted
referent **can establish which source instance is meant** — that is FIND — and **cannot
establish what it contains** beyond testimony, which is why every disagreement about it is a
testimony conflict and never a parse dispute. Held and asserted differ on RE-READ, and
RE-READ is the only property the re-parse needed.

---

## What the cases do not establish

1. **Whether testimony about a described document establishes P-subject's truth, or at what
   strength.** Rob's boundary. RA1 poses; nothing here says it is established.
2. **Whether two matching testimonies corroborate** (RA5). *Same subject* only.
3. **How the asserted → held upgrade happens** (RA1, RA3). When the Sept 1 statement is later
   imported, does the held artefact *become* the earlier testimony's referent? By
   description-match that is an inference; C9's *ask, don't manufacture* suggests the link be
   confirmed rather than inferred. Named, not decided.
4. **The individuation threshold's exact content** (RA6). Issuer + date + kind suffices in RA1;
   what the minimum is, and whether it differs by document kind, is not set here.
5. **Representation** of described referents, of *currently ambiguous*, or of singularity.

---

## Decision remaining — Rob's

Whether to lift the fence on these terms: an individuating assertion is a sufficient referent
for P-subject's *identity* (pose, find) and never for its *contents* (re-read); two kinds of
asserted referent; sufficiency non-monotonic and relative to the record; and — the result
with a consequence for shipped code — disagreements about an asserted referent are testimony
conflicts, for which `resolution()`'s existing kinds are already right.
