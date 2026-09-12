# Utterance identity — what makes two utterances two distinct events

> Status: **Design mode, 2026-09-12. No table, no code. Proposition still opaque.** Rob's
> question, opened after the primitive was ruled:
>
> > **Is an utterance fundamentally an assertion event, with its identity supplied by the
> > occurrence of that act, rather than by its content, resolution, or storage encounter?**
>
> **Four readings, tested against the rulings, with the expected answer not carried in:**
>
> ```text
> E1  same origin + same proposition  ⇒  same utterance
> E2  same content                    ⇒  same utterance
> E3  different recording times       ⇒  different utterances
> E4  each act of assertion           ⇒  a distinct utterance, whether or not its content repeats
> ```
>
> **The two cases every reading must survive** (Rob's):
>
> ```text
> A   Monday:  Person → "My insurer is Lakeview Health."
>     Friday:  Person → "My insurer is Lakeview Health."                           identical content
>
> B   Monday:  Person → "My insurer is Lakeview Health."
>     Friday:  Person → "My insurer is Lakeview Health, but I was wrong Monday."   related, not identical
> ```
>
> **Then, and only then:** which provenance is *intrinsic* to the utterance versus *about* it.
> Fenced: what a proposition is; retraction semantics; deduplication mechanics; any table.

---

## 1. Case A — identical content, two days apart

**What the rulings already say about a repeated identical assertion.** Q2 named it:
*reaffirmation* — a kind of resolution, defined as *the resolver last stood for the current
conclusion*. The tie ruling then fixed its weight: *among equals a party can always regain
currency by restating; the count of contradictions is history, never confidence — a user who
restates five times is not five times more right.* And `resolution()`'s docstring: *appending
an agreeing event changes neither kind nor resolver.*

So the record **already treats Friday's statement as a second event** — one that can make a
stance current again (T2), that is counted as history, and that adds no strength. That is
only expressible if Friday is a distinct utterance from Monday.

- **E1 (same origin + same proposition ⇒ same)** collapses Friday into Monday. Then
  *reaffirmation* has no event to be, T2 is unrepresentable, and the tie ruling's *regain
  currency by restating* has nothing that was restated. **Rejected by a ruled kind.**
- **E2 (same content ⇒ same)** collapses more: it also merges **RA5** — two household members
  independently saying *"the Sept 1 statement says $1,925"* — into one utterance, erasing the
  second *origin*. RA5's ruling was *same subject, corroboration fenced*; E2 would make the
  corroboration question unaskable by deleting one of the parties. **Rejected.**
- **E4** holds A cleanly: two events, one origin, one proposition; the second is a
  reaffirmation, counted as history, adding no strength. **Rob's stated case — *the second does
  not strengthen the first merely because the proposition is identical* — is exactly what Q2
  and the tie ruling already enforce, and only E4 lets them.**

---

## 2. Case B — related content, a self-correction

Friday's *"…but I was wrong Monday"* is **RA4's shape**: the same source revising its report.
The R-ASSERT ruling classified it — *a testimony conflict, for which `resolution()`'s
source-history kinds are already correct* — and Q2 names the kind: *self_reversal* (the
resolver's last prior stance was the opposite). Both require Monday and Friday to be two
events with a *relationship* between them: the second is *about* the first.

- **E1 / E2** — the propositions differ, so neither merges the two; but neither can say that
  Friday is *about* Monday. Under content-identity, Friday is merely another utterance whose
  content happens to mention a prior one; the relation *this corrects that* would have to be
  inferred from text. **They survive B only by being unable to express it.**
- **E4** — two events; the second's proposition has the first as (part of) its subject —
  *Monday's assertion was wrong* — which is a proposition about an utterance, and utterances
  are things the record holds and can be the subject of. The retraction/correction relation is
  then a claim like any other, with origin and strength, pointing at an event that still
  exists. **This is the minting ruling's lock-in — *a false correspondence does not
  retroactively mean the utterance never existed* — applied to the party's own correction.**

---

## 3. E3 — recording time as identity — the tempting one, tested separately

E3 says two rows with different `recorded_at` are two utterances. It gets A and B right by
accident and fails where the utterance ruling just drew its line: **asserted-at is not
recorded-at.**

- **The household reports one act twice.** *"I told the servicer in March"*, entered in
  September; the same March conversation entered again in November. Two recordings. Are they
  two utterances? The March act is one event *in the world* that the household is *reporting*
  — but the report itself is an in-app assertion, and September's and November's are **two
  acts of assertion about one reported act.** E3 and E4 agree here (two), for different
  reasons — E3 by clock, E4 by act.
- **One act, recorded twice by the system.** A note file re-imported; a sync replayed. One act
  of assertion, two rows, two `recorded_at`. E3 says two utterances — **it has minted an
  assertion the party never made.** E4 says one utterance, encountered twice — and the second
  row is a *correspondence question at the utterance level* (are these two recordings of one
  act?), exactly the artefact ruling's shape: identity is the act; a duplicate recording is a
  claim about correspondence, never a second act.
- **The rejected-bases list** already contains *import event* and *timestamp alone* as
  identity bases. E3 is both.

**E3 rejected**, and the rejection sharpens E4: **the storage encounter is provenance *about*
the utterance, never its identity.**

---

## 4. The ruling the cases give

> **An utterance is an assertion event. Its identity is the occurrence of that act — a party
> asserting something at a time — and not its content, its proposition's resolution, or the
> system's encounter with it. Two acts are two utterances even when their content is
> identical; one act is one utterance even when it is recorded twice. Relationships between
> utterances — reaffirmation, self-reversal, correction, retraction — are relations between
> distinct events, expressed as claims that can take an utterance as their subject.**

Run against the record: T2's reaffirmation is a second event that adds no strength ✓; RA4 /
Case B's correction is a second event *about* the first ✓; RA5's two members are two events
with two origins ✓; D8's *two utterances, one source, `recorded_at` separates them* is the
in-app special case where act time and recording time coincide ✓; a replayed sync is one act,
twice encountered ✓. No ruled case is rewritten; E1, E2 and E3 each rewrite at least one.

**And the symmetry with readings is exact.** The identity primitive ruled *reading identity
is the observation event, owned by its artefact — a re-parse yielding identical values is
still a second reading; the record can say "read twice, agreed."* An utterance is the
assertion event with no artefact; a restatement yielding identical content is still a second
utterance; the record can say *"said twice, agreed."* One rule, both evidence kinds.

---

## 5. Provenance — intrinsic versus about the utterance

With identity fixed as the act, the split Rob proposed falls out, and each side is checked
against what the rulings force:

```text
INTRINSIC to the utterance (constitutes the act; changing it is a different act)
    who asserted        the origin party — the contract's C1; the fixed point
    what was asserted   the proposition (opaque)
    when asserted       the evidence time — the utterance ruling; NOT recorded_at

ABOUT the utterance (evidence and findings concerning an act that already exists)
    when / where / how Groundwork learned it     recorded_at · the surface · the import — provenance of encounter (C2)
    later interpretations                        readings of the utterance's content; understanding is not existence (P3)
    later correspondence                         this recording is that act; this referent is that party (RA1–RA3)
    later contradiction / retraction             a further claim taking the utterance as subject (RA4, Case B)
    strength                                     derived from origin × proposition kind, never carried (the primitive ruling)
```

Two things the split settles that were open:

- **Retraction is *about*, not intrinsic.** A retracted utterance is an utterance with a
  later claim against it, not an utterance that ceased to be — gap 1's *a retraction is a
  state, not a removal*, arriving at the utterance level, and the only reading under which
  S3's minted party keeps its provenance after the household withdraws the assertion.
- **The surface is *about*.** Which screen the household typed on is encounter provenance; no
  ruling makes an utterance a different utterance for having been made on a different surface.
  (H5's findings-kinds declaration classifies what a *surface passes to the model*, which is a
  property of the crossing, not of the utterance.)

---

## 6. What this record does not decide

What a proposition is (the subject of Case B's Friday utterance is *an utterance* — which says
propositions must be able to take utterances as subjects, a constraint on the fenced question,
not an answer to it) · how duplicate recordings of one act are detected or merged
(correspondence mechanics) · what retraction does to a party the utterance minted (fenced
upstream) · whether *when asserted* may be approximate or unknown (*"sometime in March"* — an
intrinsic coordinate that is itself uncertain; noted, not opened) · any table.

---

## 7. Decision remaining — Rob's

Whether §4 is the identity ruling and §5 the provenance split. If so, the evidence family's
utterance is fully specified at the semantic level — *an assertion event; origin, proposition,
evidence time intrinsic; strength derived; everything else about it* — and the remaining
question before the family can be built is the one every record has fenced: **what a
proposition is** — now with two constraints on it from this record (it can take an utterance
as subject; it can take a party the utterance created as subject) and one from the primitive
(it has a *kind* the knowing relation is defined over).

---

## 8. Ruling — Rob, 2026-09-12. §4 and §5 ruled as written, including the evidence-time correction.

**The correction is more than editorial:** *evidence time is when the party made the
assertion; `recorded_at` is when Groundwork encountered it.* That keeps the ontology
independent of the ingestion path — an in-app assertion may have identical timestamps, but
that is an implementation circumstance, not a semantic identity rule.

**The identity ruling:** *an utterance is an assertion event; its identity is the occurrence
of the act.* The exact analogue of readings:

```text
read twice   =  two readings           one act encountered twice   =  one utterance
said twice   =  two utterances         two acts, identical content =  two utterances
```

E3's failure is decisive: it shows why **recording is provenance about evidence, not the
evidence event itself.**

**Both deductions agreed:** retraction is *about* the utterance, not removal of it — preserving
the assertion that explains S3's provenance; surface is *about* the encounter — the same
assertion does not become a different one for crossing through another surface.

**The evidence family's boundary:**

```text
UTTERANCE
    assertion event
    ├── origin
    ├── proposition
    └── evidence time
         ├── strength         → derived, never stored
         └── everything else  → about the utterance
```

Duplicate encounter is no longer an ontology problem; it is correspondence / deduplication
machinery downstream.

### The remaining question — what is a proposition?

Opened **without designing a representation**, under seven accumulated constraints:

1. a proposition has a **kind** — the origin's knowing relation is evaluated against it;
2. it can take a **party** as subject;
3. it can take an **utterance** as subject;
4. the subject can therefore be something **created by another assertion**;
5. truth, resolution and comprehension are **not prerequisites** for its existence;
6. it cannot collapse into the utterance — the **same proposition can be asserted by multiple
   utterances**;
7. **identical textual content does not necessarily mean identical proposition semantics.**

**The danger test:**

> **Can the proposition be reduced to either text/content or a relation between already-
> existing parties?**

If either reduction fails in the corpus, Groundwork needs a genuine proposition concept rather
than an `utterance.text` field or a collection of typed foreign keys. The two cases to test:

```text
Person ─ asserts → [proposition A] ─ subject: Institution S3
Person ─ asserts → [proposition B] ─ subject: an earlier utterance
```

The second means the proposition system must express claims about **evidence events**, not
merely about worldly entities.
