# What survives a resolved conflict — six histories against the shipped module

**Q2 of `EVIDENCE_MATRIX.md`, attacked with concrete histories before any storage question.**

> Status: **Case set, 2026-09-11. No mechanism, no schema. Direction decided the same day
> (Rob's) — see *The Q2 decision* — and the resolution-kind vocabulary probed, not specified.**
> The question, as he posed it:
>
> > **When conflicting evidence is later resolved, what must remain reconstructable about the
> > conflict, and what may subsequently be treated as the current fact?**
>
> Six histories were run against `core/classification.py` as it is, and for each the five
> questions below were answered by looking at where the answer actually lives:
>
> 1. What is the current conclusion?
> 2. What evidence supports it?
> 3. Was there a contradiction?
> 4. What resolved it?
> 5. Can narration or export distinguish this from a fact that was never contradicted?
>
> **The result changes the question.** The two contracts Q2 offered — *history of the conflict
> event* versus *provenance of the present conclusion only* — turn out to **both already exist**,
> at different layers, and the defect is that nothing carries the first into the second.

---

## The histories

All on the content axis of one neutral transaction, `U` = `USER_STATED`, `E` = `IMPORTED_EOB`.

| | History | Current state | Strength | Determination chain | Narrator gets |
|---|---|---|---|---|---|
| **H1** | U:health | `user_asserted` | 3 | `[not_evaluated, user_asserted]` | `1250.00` |
| **H2** | E:not → U:health | `user_asserted` | 3 | `[not_evaluated, contradicted, user_asserted]` | `1250.00` |
| **H3** | U:health → E:not | `contradicted` | 0 | `[not_evaluated, user_asserted, contradicted]` | refusal |
| **H4** | U:health → E:not → U:health | `user_asserted` | 3 | `[…, user_asserted, contradicted, user_asserted]` | `1250.00` |
| **H5** | E:not → U:health → E:health | `imported_attested` | 3 | `[…, contradicted, user_asserted, imported_attested]` | `1250.00` |
| **H6** | U:health → U:not | `contradicted` | 0 | `[not_evaluated, user_asserted, contradicted]` | refusal |

And in every case the current determination's `evidence` tuple holds **every** piece of knowing
evidence ever recorded, disagreements included.

---

## The five questions, answered by layer

| Question | Where the answer lives | H2 |
|---|---|---|
| 1. current conclusion | `axis(c, CONTENT).state` | `user_asserted` |
| 2. supporting evidence | `evidence(c, CONTENT)` — the full tuple | `[(eob, no), (user, yes)]` |
| 3. was there a contradiction | the tuple, or `determinations(c, CONTENT)` | **yes — visible in both** |
| 4. what resolved it | the chain: which determination followed `contradicted` | the user's statement, by recency |
| 5. can a consumer tell H2 from H1 | `strength_of` → the boundary | **no** |

**Questions 1–4 are answerable today, from the record, without any new concept.**
`record_evidence` returns a new classification with the prior determination surviving in place —
*superseded, never overwritten* — and each determination carries the whole evidence tuple up to
that point. So the conflict event is preserved, its sequence is preserved, and what resolved it is
preserved.

**Question 5 is the defect, and it is now precisely located.** `strength_of` reads the current
state and nothing else. The current state is `user_asserted`. Rank 3. The number goes out. The
chain that says *this overrode a contradicting EOB* is two attribute accesses away and nothing at
the boundary reads it.

---

## What this corrects in the earlier framing

`EVIDENCE_MATRIX.md` classified conflict disappearance as **provenance / history loss**. The
histories show that is the wrong label. **Nothing is lost.** The record layer is already contract
A — the event survives — and the consumer layer is contract B — present provenance only — and
**the failure is that the summary is lossy and the consumer sees only the summary.**

```text
evidence tuple          preserves the conflict          ✓
determination chain     preserves the sequence          ✓
current state           collapses it                    ✗   user_asserted
strength_of             collapses it                    ✗   rank 3
consumer                never sees it                   ✗
```

Which is the same shape as the two findings before it. Sensitivity survives the typed lattice and
dies at rendering. The refusal existed and never reached the consumer until Q1. And here: the
conflict is recorded and never reaches the boundary. **This codebase's recurring defect is not
losing information — it is holding information that does not travel.**

---

## Three findings the histories forced

### 1. Rank 3 is a ceiling that absorbs every history

H1, H2, H4 and H5 are all rank 3 and all deliver `1250.00`. Their evidentiary histories are:

```text
H1   one knowing source, never opposed
H2   one knowing source, overriding another by recency alone
H4   one knowing source, reaffirming after seeing the opposition
H5   the EOB source disagreeing, then agreeing   ← first read as "independent"; see below
```

**Every one of these yields exactly the same rank as a bare unopposed statement.** Recency among
equals, reaffirmation, and a source reversing itself are one number to a consumer. *(The first
draft called H5 "an independent second source confirming". The probe in the later section shows
it is not — with two knowing identities there is no such thing — and the point of this finding
survives the correction: the lattice cannot distinguish any of them.)*
The lattice has no headroom above 3 and no second axis, so every history that ends in a knowing
`yes` is one number to a consumer.

This is not a defect in the lattice as a *strength* lattice. It is the finding that **resolution
kind is not a strength**, and trying to encode it as one would need headroom the lattice was never
designed to have.

### 2. ~~Reaffirmation is invisible, and that is probably correct~~ — superseded

**Wrong at the layer that matters, and Rob challenged it before it was blessed.** H4 and H2 are
identical to *strength* — correctly, by gap 4's dedup — and **fully distinguishable from the
record**, as the probe in *The reaffirmation challenge, tested* shows. What the first draft said
"nothing else can express" is derivable from the chain in a dozen lines. The finding that survives
is narrower: reaffirmation is invisible to strength and visible to the record, and **whether it
travels** is the decision — now answered: it does, beside the value.

### 3. An external contradiction and a self-correction are one state

H3 (an EOB disagrees with the user) and H6 (the user changed their own mind) are both
`contradicted`, rank 0, refused. They are different situations — one is an unresolved conflict
between parties, the other is a correction with no opposing party — and the lattice reports both
as *we have evidence against it*.

**Noticed, not pursued.** Whether it matters depends on whether `contradicted` is a strength or a
verdict, which is the evidence/classification/verdict fusion the module's own docstring warns
about in `is_protected`. It is adjacent to Q2, not inside it, and it is recorded here so it is not
rediscovered.

---

## The question, narrowed

Not *do we need a new persistent concept*. Persistence exists. The question is:

> **Should a resolved conflict affect what a consumer receives, and if so, through what — the
> strength, or something carried beside it?**

Four answers the histories make concrete, each with its cost:

| | Answer | H2 relative to H1 | Cost |
|---|---|---|---|
| **i** | no — recency among equals is authoritative | equal | consumers cannot tell a contested fact from an uncontested one. **Current behaviour.** |
| **ii** | demote — overriding an equal-rank source is weaker than never being opposed | H2 < H1 | **penalises evidence.** A user who imported an EOB that was wrong and corrected it ends up weaker than one who never imported it. More evidence, less permission — but here the extra evidence was refuted, and the refutation counts against the person who refuted it |
| **iii** | rank the resolution — an independent confirmation outranks recency | H5 > H1 > H2 | needs headroom above rank 3 or a second axis. **A lattice change**, and finding 1 says resolution kind is not a strength |
| **iv** | leave strength alone; carry the conflict beside the value | equal rank, **distinguishable** | the consumer receives a second thing and must decide what to do with it — which is Q1's downstream presentation question, again |

**Option iv is the one consistent with how this codebase has fixed the last three instances of
the same shape.** The refusal existed and was made to reach the consumer with its reason. The
sensitivity existed and must survive to rendering. The conflict exists in the chain and would
travel beside the value — reconstructable from `determinations()` today, and delivered rather than
merely available. It does not reinterpret the lattice, does not penalise a person for correcting a
wrong document, and does not invent a rank the lattice cannot hold.

**What it does not settle**, and what makes the decision Rob's: what exactly travels. The
histories suggest at least three distinguishable facts a consumer might be handed —

```text
a knowing source was overridden          H2, H4, H5
by recency alone, or by reaffirmation    H2 vs H4
or by an independent confirmation        H5
```

— and how many of those the narrator or the export may show is presentation, downstream, and
deliberately not decided here.

---

---

## The Q2 decision — direction established, mechanism not specified

*(Rob, 2026-09-11.)*

> **A resolved conflict travels beside the value. It does not alter the value's strength.**

The evidence history already answers *what happened*. What is missing is **a summary of the
resolution event that a consumer can actually receive.** So the current determination may carry a
separate descriptor — vocabulary still to be scrutinised, and the shape below is a candidate, not
a commitment:

```text
current value        = health
current strength     = rank 3
resolution           = conflict_resolved
resolution_basis     = user_assertion
resolution_relation  = superseded_prior_evidence
```

**The invariant that makes it safe:**

> **Resolution metadata describes the history of how the current determination was reached. It
> does not constitute evidence for the current determination.**

That is what stops the lattice acquiring a second meaning in which *was previously contradicted*
becomes a strength. Two axes, kept apart:

```text
                    current determination
                           │
              ┌────────────┴────────────┐
              ↓                         ↓
        evidence strength         resolution history
        "how strong now?"         "how did we get here?"
```

All four histories in the table below may retain the **same** strength if their present evidence
warrants it; only the descriptor differs. Whether a consumer *sees* all four distinctions is a
surface decision, downstream, exactly as Q1 separated refusal contents from presentation.

---

## The reaffirmation challenge, tested

The earlier finding said *reaffirmation is invisible, and that is probably correct*. Rob's
challenge: *probably correct* is not a contract, and the case that decides it is

```text
EOB: no  →  user: yes  →  EOB: no again  →  user: yes again
```

— because if dedup-by-source-identity makes the second assertion vanish, Groundwork cannot tell
*asserted once after a contradiction* from *explicitly reaffirmed after being shown one*.

**Tested with a probe over the chain, not a claim.** The probe reads only what the module already
keeps — the knowing evidence in the current determination's tuple — and names how the current
conclusion was reached. Nine histories:

| | History | State | Derived resolution |
|---|---|---|---|
| H1 | U:y | `user_asserted` | **none** |
| H2 | E:n U:y | `user_asserted` | **superseded** — user corrected the EOB |
| H4 | U:y E:n U:y | `user_asserted` | **reaffirmation** |
| R1 | E:n U:y E:n U:y | `user_asserted` | **reaffirmation**, contradictions = 2 |
| X3 | E:n U:y U:y | `user_asserted` | **superseded** — repeated, but nothing new was answered |
| H5' | E:y U:y | `user_asserted` | **none** — agreement, no conflict |
| H5 | E:n U:y E:y | `imported_attested` | **self_reversal** — the EOB source flipped |
| X1 | U:y E:n E:y | `imported_attested` | **self_reversal** — same |
| X2 | U:y E:n U:n | `contradicted` | **self_reversal** — the user conceded |

**The earlier finding was wrong at the layer that matters.** Reaffirmation is invisible to
*strength* — correctly, by gap 4's dedup — and **fully derivable from the record.** H4 and H2 are
distinguishable. R1 and H4 are distinguishable, by contradiction count. X3 is distinguishable from
H4: saying it twice is not the same as saying it again *after being contradicted*, and the chain
knows which. So the answer to the challenge is: **yes, Groundwork can distinguish them, today,
from data it already holds.**

### The finding the probe forced: independent confirmation is unreachable

`independent_confirmation` — a source that never disagreed adding its agreement after a conflict
— **fired for no history**, and cannot:

> With exactly two knowing source identities, `USER_STATED` and `IMPORTED_EOB`, a second agreement
> after a conflict is **always a reversal by one of the two.** For two asserters to exist and one
> contradictor to exist, one identity must have said both *yes* and *no*.

So H5 — the case the earlier document called *an independent EOB confirms* — is not that. It is
the EOB **source** contradicting and then agreeing. And the record cannot say whether that was
**one document re-read**, or **a genuinely different document** — because `IMPORTED_EOB` is the
identity of every EOB ever imported. Source identity is a *type*, not a document.

**That is `EVIDENCE_MATRIX.md` finding 3 arriving from a new direction**: there is no state for
*this document said this*, so there can be no state for *a different document said this*. The
fourth resolution kind is **not a Q2 mechanism.** It is blocked on evidence carrying document
identity, which is an upstream change to what `Evidence` records, and a separate decision.

### What self-reversal does and does not separate

It collapses three situations with different teaching value — an EOB re-imported with a different
reading, a second EOB that disagrees with the first, and a user conceding to a document. **The
third is separable now** by `resolver`: X2's resolver is the user, H5's and X1's is the EOB. *The
user changed their mind after seeing the document* is derivable. The first two are the irreducible
ambiguity, and it is the document-identity gap again.

---

## What travels — the shape the probe supports

**Derived on read from the chain, never stored** — gap 4's rule for strength, applied for the same
reason: a stored summary can drift from the record it summarises; a derived one cannot.

```text
kind             none · superseded · reaffirmation · self_reversal
resolver         which knowing source made the current conclusion current
contradictions   how many times a knowing source disagreed with it
```

`independent_confirmation` is **reserved and unreachable** until evidence carries document identity.
The probe that produces the table above is roughly fifteen lines over data the module already
keeps; **it is not in the module, on purpose.** Whether these three fields are the vocabulary, and
which of them a narrator or an export may show, is Rob's — and the invariant above holds
whichever way that lands.

---

## Adjacent, and now a third sighting

X2 ends with the user and the EOB **agreeing** that the transaction is not health — two knowing
sources, no remaining dissent — and lands at `contradicted`, rank 0, refused. **Agreement on a
negative is the floor of the lattice.** This is H3/H6 from the first pass and `is_protected`'s
fusion warning: `contradicted` is a verdict about the health claim wearing a strength's name.
Three sightings in two days. It is still outside Q2, and it should stop being *noticed* and get an
entry of its own.

## What has not been done

No mechanism. No change to `strength_of`, `_state_from`, the lattice, `refusal()`, or the
consumer helpers. The probe lives in a scratch directory, not the module. The tie fixture stays
red. The three doctrine questions stay where they are — nothing here touches carrier, disposition
scope, or F3.
