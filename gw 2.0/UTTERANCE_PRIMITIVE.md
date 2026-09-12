# The utterance primitive — origin, strength, proposition, and nothing more

> Status: **Design mode, 2026-09-12. No table, no code. "Proposition" stays opaque.** The
> evidence family's first question, opened on Rob's boundary: *the smallest representation of
> a claim made by a party, with strength, about a proposition* — and the independence test
> first:
>
> > **Does an utterance exist as evidence independently of whether its proposition is true,
> > resolvable, or comprehensible?**
>
> **Four readings, tested against the rulings and the corpus:**
>
> ```text
> P1  proposition-first        an utterance exists only when its proposition can be represented / resolved
> P2  truth-dependent          an utterance exists only if its proposition is established as true
> P3  interpretation-dependent an utterance exists only when Groundwork can understand what was asserted
> P4  evidence-first           the utterance exists when a party made the assertion; truth, resolution
>                              and interpretation are properties of, or later findings about, it
> ```
>
> **The danger test:** does any of P1–P3 make an already-ruled case impossible to represent
> without rewriting history?
>
> **Fenced, and not answered:** what propositions *are* (string · predicate · graph edge ·
> typed object); what makes two utterances two; which provenance is intrinsic versus evidence
> about the utterance — the next boundary. Nothing institution-specific.

---

## 1. The S3 test — truth is not an existence condition

`SERVICING_ONLY_CASES.md` S3, ruled: the household attached S3 as the servicer of record. S3
never served P. The party ruling then treated S3 as **a real minted party with a false
asserted relation** — corrected by *conflict* with P's own statement, never by ranking and
never by unminting. And the minting ruling: *a false correspondence does not retroactively
mean the utterance never existed.*

Under **P2** the household's assertion, being false, did not exist. Then:

```text
household says "S3 serves P"   →   false   →   the assertion never existed
                                                    ↓
                                          why does party S3 exist?
                                          why did the household pay S3?
                                          what did P's statement contradict?
```

Every one of those is a ruled sentence the record must be able to say, and each names the
utterance. **P2 destroys the provenance the S3 ruling exists to preserve.** It also contradicts
Q2 directly — *a resolution may change the current conclusion but may not silently erase the
existence of the conflict; a conflict that reads as though it never happened is worse than an
unresolved one* — and the tie ruling's *count is history, never confidence*: a contradicted
stance persists as a stance that was taken. **P2 is rejected by cases already in the record.**

---

## 2. The resolvability test — the referent may not be established

*"My servicer is Acme"* — and Groundwork holds two Acmes, or none. Ruled cases that are
exactly this shape:

- **RA2** — *"the Sept 1 statement"* when two statements bear that date: the asserted identity
  is **non-monotonic**, and *the record has to be able to hold "asserted referent, currently
  ambiguous" without collapsing it to either candidate by position.* The utterance is held; its
  referent is not.
- **The party ruling's third state** — `NOT ESTABLISHED`, which *may carry candidates* and
  *never mints a placeholder*. A state defined for exactly the case where an assertion has been
  made and its party cannot yet be settled.
- **U5 / D7** — a second letter creates no relationship; *unresolved* is the default. The
  letter and the household's report of it are held; what they refer to is open.
- **The surface principle**, ruled: *`Unknown` must be an acceptable terminal state.*

Under **P1** the utterance *"my servicer is Acme"* cannot exist until Acme is resolved. Then
the thing that *needs* resolving is absent from the record, and the model inverts:

```text
ruled:      utterance → proposition → resolution        (correspondence works on existing evidence)
P1:         resolution → utterance                       (unresolved evidence does not exist)
```

The entire correspondence apparatus — candidates, asserted links with strength, C9's *ask,
don't manufacture* — operates on utterances whose referents are not yet established. **P1
would remove its inputs.** Rejected.

---

## 3. The comprehensibility test — the parser is not the party

Groundwork's ability to interpret a claim and the claim's existence are separated in the
record already, three ways:

- **V6** — an EOB whose amount the parser cannot read. Ruled: *an absent value must be
  representable as absent* and never fall through to the transaction figure. The artefact
  exists; the reading yielded nothing for that field; the insurer's statement was still made.
  The failure-semantics ruling generalises it: **successful processing ≠ evidence of
  correctness** — and its converse, unsuccessful processing ≠ evidence of absence.
- **H5, the annotation** — the household's typed note reaches the model *as the household's
  own words*, declared as an asserted kind whether or not any component understands it. The
  voice ruling's authorisation rests on *who asserted it*, not on whether it parsed.
- **`USER_KNOWLEDGE_CASES.md`** — *"the user reports the letter says X"* is not *"the letter
  says X."* The proposition is about an artefact the user describes; whether Groundwork can
  read that artefact is a separate fact about a separate thing. The report exists either way.

Under **P3** an assertion Groundwork cannot presently interpret — *"had the March thing
redone"* — did not occur. But the party made it, on a surface, at a time, and a later reader
(a person; a better parser; the same household asked C9's question) may understand it. **The
system's ability to understand a claim is not the condition under which the claim came into
existence.** The broader doctrine already says this in its own words: *the software records
what the evidence establishes; it does not manufacture reality by successfully parsing it.*
Rejected.

---

## 4. The reading that survives, and what it makes of the other three

**P4.** An utterance exists as evidence **by virtue of the originating party making the
assertion.** Truth (§1), resolvability (§2) and comprehensibility (§3) are not existence
conditions; they are states of *what the utterance says* and findings *later evidence
establishes about it*:

```text
utterance exists
      │
      └── its proposition may be:   understood · partially understood · unresolved ·
                                    later resolved · contradicted · established
```

None of those is a prerequisite. Each is a property the record attaches afterwards, by
further evidence — which is exactly how the record already treats a reading of an artefact.
**The utterance is the evidence unit with no artefact behind it, and it behaves like every
other evidence unit: it exists because it was made, and everything else is about it.**

---

## 5. The minimum primitive — and one refinement to "strength"

The independence result fixes the primitive's *semantics*:

| | what it is | forced by |
|---|---|---|
| **origin** | the party that made the assertion — a party reference (`Person` for now; an institution once minted), in one of the four party states | the contract's C1–C2 (origin is who knows; never the channel); the fixed point |
| **proposition** | what was asserted — **opaque here** | the ontology (*a claim on a proposition*); its shape is the next question's, not this one's |
| **strength** | how far the origin is knowing for *this* proposition kind | the knowing relation, ruled per proposition kind: the user is rank-3 knowing for *health*, **not** knowing for P-ack (K5); a servicer's statement is E's at weakest-link strength |

**The refinement.** The rulings say strength is *a function over the graph, recomputed on
read, never stored* (`EVIDENCE_MATRIX.md`; `strength_of`), and *belongs to the evidentiary
relationship, not to the proposition and not to the artefact* (the ontology ruling). For an
utterance there is no artefact or reading to separate the evidence from its relationship —
**the utterance and its evidentiary relationship coincide** — so strength is a property every
utterance *has*, and it is **derived from origin × proposition kind**, not carried as a field.
`origin, strength, proposition` is the right *semantic* minimum; the *stored* minimum is origin
and proposition, with strength guaranteed computable from them. The three-part statement
stands; one of the three is a derivation, and saying so now prevents a `strength` column that
would drift from the knowing relation it should mirror — the tie fixture's lesson about
stored summaries.

**Provenance the doctrine already forces, and no more:**

- **when** — an utterance's evidence time *is* `recorded_at` (the tie ruling: *utterance →
  recorded_at, its only time*). The one evidence kind where import time and evidence time
  coincide by nature, so no second coordinate is forced.
- **that it was surfaced** — satisfied by construction: an utterance is something the party
  said; the no-silent-learning boundary (an unsurfaced observation may never persist) is met
  because the party is the one who surfaced it.
- **Not forced:** channel (which surface it was typed on) — no ruling distinguishes an
  utterance by its surface; artefact — none, by definition (D8); a truth or resolution state —
  §4 says these are attached later, not carried.

---

## 6. The ruling, if the cases confirm it — they do

> **An utterance exists as evidence by virtue of the originating party making the assertion.
> Its existence does not depend on the truth, resolvability, or comprehensibility of its
> proposition; those are properties of what the utterance says and of what later evidence
> establishes about it. The primitive is origin, strength and proposition — origin a party
> reference, proposition opaque at this boundary, strength derived from the origin's knowing
> relation to the proposition's kind and never stored — with the one provenance the doctrine
> forces: when it was made, which for an utterance is its evidence time.**

Run against the record: S3 stands as a made, false, provenance-bearing assertion; *"my
servicer is Acme"* is held with its referent not established and candidates beside it; an
uninterpretable note is an utterance whose proposition is *not understood*, not a non-event.
No ruled case is rewritten; three would have been under P1–P3.

---

## 7. What this record does not decide

What a proposition is · what makes two utterances two (D8's *recorded_at separates them*
points at event identity, like readings — the next boundary's question, not this one's) ·
which provenance beyond *when* is intrinsic versus evidence about the utterance · whether an
utterance can be retracted, and what retraction means for a party it minted · any table.

---

## 8. Decision remaining — Rob's

Whether §6 is the primitive, with the strength refinement — semantically one of three,
mechanically derived — accepted or overruled. If ruled, the next boundary is the one he named:
**what makes two utterances two, and what provenance is intrinsic to the utterance versus
merely evidence about it** — where cardinality and provenance can be tested without designing
the representation.
