# What survives a resolved conflict — six histories against the shipped module

**Q2 of `EVIDENCE_MATRIX.md`, attacked with concrete histories before any storage question.**

> Status: **Case set, 2026-09-11. No mechanism, no schema, and the decision is Rob's.** The
> question, as he posed it:
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
H5   two independent knowing sources agreeing, after one of them disagreed
```

**The strongest resolution possible — an independent second source confirming — yields exactly
the same rank as a bare unopposed statement.** And the weakest — recency among equals — also does.
The lattice has no headroom above 3 and no second axis, so every history that ends in a knowing
`yes` is one number to a consumer.

This is not a defect in the lattice as a *strength* lattice. It is the finding that **resolution
kind is not a strength**, and trying to encode it as one would need headroom the lattice was never
designed to have.

### 2. Reaffirmation is invisible, and that is probably correct

H4 and H2 are identical to every layer above the chain. A user who reaffirms after seeing the EOB
is treated exactly as a user who spoke once after it. Gap 4 deduplicates corroboration by **source
identity**, so the same source twice is one source — and that rule is right. What follows is that
*the user looked at the contradiction and stood by their answer* is a fact the chain records and
nothing else can express. Whether it **should** be expressible is part of the decision.

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

## What has not been done

No mechanism. No change to `strength_of`, `_state_from`, the lattice, `refusal()`, or the
consumer helpers. The tie fixture stays red. The three doctrine questions stay where they are —
nothing here touches carrier, disposition scope, or F3.
