# Document identity — what an evidence instance has to be able to say

**The gap that surfaced four times in two days, attacked with cases against the shipped module.**

> Status: **Case set, 2026-09-11. No schema, no field added to `Evidence`, and the decision is
> Rob's.** The question:
>
> > **What must an evidence instance be able to say about where it came from, and what claim
> > does each addition unlock?**
>
> Where it surfaced: `EVIDENCE_MATRIX.md` finding 2 (testimony about a document lands as
> testimony about the world), finding 3 (parsing establishes the fact — no state for *the document
> contained this value*), `RESOLVED_CONFLICT_CASES.md` (independent confirmation structurally
> unreachable), and `USER_KNOWLEDGE_CASES.md` U5 (a second letter). Rob's boundary from Q2 is the
> premise: **source type ≠ source instance.**
>
> **Fence.** This does not decide obligation identity, does not touch the three doctrine
> questions, and does not propose what `Evidence` stores. It establishes which *distinctions*
> the record must be able to make, by showing which ones it cannot make today.

---

## What the record can tell apart today, measured

Five pairs, each run through `record_evidence` on the content axis and read back through
`axis()`, `strength_of()` and `resolution()`:

| | Pair | Evidence tuple | Distinguishable? |
|---|---|---|---|
| **D1 / D2** | one EOB imported twice, parsed the same · **vs** · two different EOBs, both $412 | `[(eob, yes, 412), (eob, yes, 412)]` both | **no** |
| **D3b / D4** | one EOB re-parsed, *not-health* then *health* · **vs** · two different EOBs disagreeing | `[(eob, no), (eob, yes, 412)]` both | **no** |
| **D5a / D5b** | *"the EOB says it was health"* · **vs** · *"it was health"* | `[(user, yes)]` both | **no** |
| **D3** | one EOB imported twice, parsed **$412** then **$4.12** | `[(eob, yes, 412), (eob, yes, 4.12)]` | **no disagreement registers at all** |

**Every pair is byte-identical in the record**, so nothing downstream can separate them — not the
state, not the strength, and not `resolution()`. `IMPORTED_EOB` is the identity of every EOB ever
imported, and `USER_STATED` is the identity of everything the user ever said, about anything.

**And D3b / D4 is worse than indistinguishable.** `resolution()` reports both as
`self_reversal, resolver = imported_eob` — a faithful projection of a record that says *the EOB
source reversed itself*. In D4 that is true. In D3b **no source reversed anything**: one document
was read two ways. The projection is correct and the record it projects cannot say what happened.
**Document identity is upstream of Q2's fidelity**, not a refinement of it.

---

## The cases, and what each forces

### D1 / D2 — same document twice, or two documents

Two evidence entries of the same type. Today corroboration counts **distinct source types**
(`distinct = {e.source for e in supporting}`), so both land identically — which is *correct* for
D1 and *wrong* for D2, and the code cannot know which it is looking at.

> **Forces: an evidence instance from a re-observable artefact must be able to name which
> artefact.** Two readings of one artefact are one source. Two artefacts are two.

### D3b / D4 — a parse dispute, or a source conflict

Same tuple, two different situations with **different remedies**:

```text
D3b   one document, two readings disagree      →  a PARSE DISPUTE:   re-read the document
D4    two documents disagree                   →  a SOURCE CONFLICT: adjudicate between them
```

The first is resolvable by Groundwork on its own, if it holds the document. The second is not —
it is exactly the equal-rank tie gap 15 refused to break by invention. Collapsing them means a
re-import that parsed differently is recorded as *the insurer changed its position*.

> **Forces: multiple readings of one artefact must be recordable as readings of it, so that
> disagreement between them is a dispute about the reading and never a reversal by the source.**

### D3 — the parse error, and the finding I did not predict

`$412` read as `$4.12`, both readings marked *health*. **No disagreement registers.**
`Evidence.supports` is a boolean about the health claim, both readings say *yes*, and the amounts
differ silently. `resolution()` says `none`.

This is `EVIDENCE_MATRIX.md` finding 4's gap — value-level disagreement is unrepresentable —
arriving through document identity: **even with two readings of one artefact, the record has no
way to say the readings disagree about the number.** Document identity makes the two readings
*findable*; something else has to make their disagreement *sayable*. They are separate gaps and
this case is where they meet.

### D5 — testimony about a document

*"The EOB says it was health"* and *"it was health"* are one entry: `(user_stated, yes)`. Rob's
Q2-era rule already says what the first establishes — *the user reports that the document says X*
— and the record cannot hold that.

> **Forces: evidence must be able to say what it is *about* — the world, or an artefact — and
> whether Groundwork holds that artefact or only knows of it.**

Held and referenced are different relationships to the same document. A held EOB can be
re-read, re-parsed, shown, and later corroborated by reading it again. A referenced one — the
user described it — permits none of that, and no amount of user testimony about it can be
upgraded by Groundwork into having read it. That is principle 4's reproducibility, applied to
evidence rather than to rules.

### D6 — one document, many claims, and the document turns out to be wrong

One EOB yields evidence on the content axis, an amount, a provider, a date — several entries, all
`IMPORTED_EOB`, no link between them. If the document is later found to be for a different
patient, or withdrawn, or fraudulent, **every piece of evidence derived from it must be
retractable together.** Without a referent they cannot be found.

> **Forces: retraction of an artefact must reach everything derived from it.** Gap 1 settled that
> a retraction is a state, not a removal, for obligations. This is the same rule one layer down,
> and it is only satisfiable if the derived evidence knows what it was derived from.

### D7 — U5 revisited: two letters

Two documents from different senders, possibly about one debt. Document identity lets the
relationship between the obligations **reference** the documents. It does **not** decide whether
they are the same obligation — that is the relationship's own fact, with *unresolved* as its
default, and it stays where `USER_KNOWLEDGE_CASES.md` put it.

> **Boundary: document identity ≠ obligation identity.** Necessary for the relationship to be
> recorded; not sufficient to decide it.

### D8 — the user says it twice

*Health* in March; *health* again in September. Two utterances, one source. Does an utterance
need a referent? **No.** An utterance cannot be re-observed — there is nothing to re-read — and
`recorded_at` already separates the two. The gap is specific to **artefacts that persist and can
be read again**, and generalising it to *every evidence entry needs an instance identity* would be
adding a field to things that do not need one.

---

## Findings

1. **Same-referent disagreement is a parse dispute; different-referent disagreement is a source
   conflict.** Different in kind, different in remedy, unrepresentable today, and `resolution()`
   faithfully reports the wrong one. Document identity is upstream of Q2's fidelity.
2. **Independent confirmation needs distinct referents.** Necessary, not sufficient — which
   produces the next boundary.
3. **Held vs referenced is reproducibility.** Only a held artefact can be re-read; testimony about
   a referenced one cannot be promoted by Groundwork into an observation.
4. **Retraction must reach everything derived from an artefact**, and only a referent makes that
   possible.
5. **Two readings of one artefact can disagree about a value with nothing registering.** Document
   identity makes readings findable; value-level disagreement is a separate gap that makes them
   comparable, and D3 is where the two meet.
6. **Utterances do not need referents.** The gap is specific to re-observable artefacts.
7. **Document identity ≠ obligation identity.** Necessary to record the relationship, not
   sufficient to decide it.

### The boundary that keeps the fix honest

Rob's boundary from Q2 was **source type ≠ source instance**. The cases force the one after it:

> **Source instance ≠ source independence.** Two EOBs from one insurer, for one claim, are two
> artefacts and **not** independent evidence. Distinct referents are what make independence
> *expressible*; nothing here makes it *established*. Whether two artefacts are independent is a
> further fact about their provenance, and the record must be able to hold *unknown* there too.

Without that boundary, adding document identity would let the system claim *two documents
confirm this* for what is one insurer's statement printed twice.

---

## What each distinction unlocks

Stated as permitted claims, because that is the test the matrix asks — a distinction that unlocks
no truthful sentence does not belong in the model:

| Distinction | Sentence it permits |
|---|---|
| which artefact | *two documents say this* — as opposed to *one document, twice* |
| which reading | *this document was read two ways, and they disagree* |
| about / referenced | *you told us the letter says this; we have not seen it* |
| held | *we have the document — here is what it says* |
| retractable by referent | *that document has been withdrawn, and so has everything it told us* |

And one sentence that stays **forbidden** whatever is added: *these two documents independently
confirm it* — until independence is itself established, which is not a document-identity fact.

---

## The progression, and the boundary after this one

*(Rob, 2026-09-11.)* The case set establishes an ordering, and each step is a separate fact
rather than a refinement of the one before:

```text
source type
    ↓
source instance
    ↓
artefact / reading relationship
    ↓
value-level disagreement       ← separate gap
    ↓
source independence            ← separate fact
```

**The parse-dispute / source-conflict distinction is the strongest result here**, because it
means the system is not merely missing a prettier provenance record — it is currently capable of
**assigning the wrong causal story to an evidence history.**

### Named and not attacked: artefact identity ≠ file identity

The five distinctions above are requirements, not fields, and none of them yet says
`Evidence.instance_id = …`. Before anyone designs the referent, one more collision has to be
forced by cases rather than guessed at with a UUID:

```text
one EOB, downloaded twice
one EOB, copied to a backup
one EOB, renamed, imported from two locations
one logical document, several physical representations
```

The eventual cases must make the system answer whether a referent means **the logical document**
or **the particular bytes Groundwork observed** — and they must do it before a schema freezes
either answer. Not solved here. Not to be solved by picking.

---

## What has not been done

No field on `Evidence`. No referent type, no observation id, no held/referenced flag, no
retraction mechanism. `record_evidence` is unchanged. Value-level disagreement is named as the
adjacent gap and not opened. Obligation identity stays unresolved by default. The three doctrine
questions are untouched.

**What is Rob's:** whether an evidence instance carries all five distinctions or a subset, and —
the one that shapes everything else — **whether a referent is an artefact Groundwork holds bytes
of, or an identity the user asserts** (*"this is the EOB from March"*). The second is cheaper and
weaker, and it is the difference between held and referenced applied to the referent itself.
