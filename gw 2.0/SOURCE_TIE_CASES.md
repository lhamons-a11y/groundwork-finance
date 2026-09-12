# The source tie — what "tie" means, and which time breaks it

> Status: **Case set, 2026-09-12. Evidence mode. No decision, no state name, no resolver
> design, no rank change.** Sixth fence opened in evidence mode. Rob's framing: *two P-ack
> claims, the same as-of, genuinely different channels — determine what "tie" means without
> importing the health ranking.*
>
> **A framing correction first, because the rulings changed what the fence is.** Two P-ack
> claims at one as-of from *different* channels is F4 (`FOUR_FIGURES_CASES.md`), and the
> acknowledgment ruling orders it: one knowing party, channels always ranked, **no tie**. For
> P-ack a tie can arise only **within** a channel — one party against itself at one as-of. And
> the tie the board names — `USER_STATED` ↔ `IMPORTED_EOB`, gap 15's — is on the **health**
> proposition, between **two independent knowing parties** deliberately held equal. Two
> different ties. The case set asks what "tie" means of each and does not let either answer
> the other.
>
> **What is already settled, and not reopened.** Q2 (`RESOLVED_CONFLICT_CASES.md`, and the
> tie fixture's re-pointing) settled that the health tie's *current state* resolves by recency
> among equals, and that the conflict is never erased — it travels beside the value in
> `resolution()`. The fixture's order-independent-state assertions were retired for that
> reason. **Gap 15's "explicit tie state" is therefore not open as a state question.**
>
> **What the fixture still demands, and is open:** *"latest" must be by `recorded_at`, not by
> list position.* Latent — `record_evidence` appends in call order — and going live the moment
> evidence is assembled any other way.
>
> **So the fence, in today's terms:**
>
> > **Which time axis breaks a same-proposition, same-as-of disagreement between equals — and
> > what does the record hold when no axis can?**
>
> **Fence.** Representation of any unresolved state; the resolver's design; whether
> reaffirmation should ever matter (Q2 says count is history, never confidence); `remaining`;
> the health rank table.

---

## 0. The two ties, side by side

```text
HEALTH TIE (gap 15)                          P-ACK WITHIN-CHANNEL TIE (new today)
proposition   is this transaction health?    P's stated balance as of d
parties       user · EOB — two, independent, P — one party, against itself
              first-hand, equal
evidence      utterances and a document      two documents (or two captures)
time on the   recorded_at — for an           as-of — the document's own date;
evidence      utterance, the only time       recorded_at is import order
```

The right-hand column exists because of today's rulings: P-ack is dated (acknowledgment
ruling), channels are ordered (K7), and held artefacts carry their own as-of (captured-portal
ruling). None of that was available when gap 15 was written.

---

## Case T1 — the health tie, both orders, and the time that breaks it

User says *health* (Mar 3). EOB says *not* (Apr 10). Then reversed: EOB first, user second.

- **As built:** `knowing[-1]` — list position. `user→EOB` gives `contradicted`; `EOB→user`
  gives `user_asserted`. Q2 accepted that the *current state* goes to the later stance among
  equals, and made the disagreement visible in `resolution()` (contradictions = 1 either way).
- **The open part:** *later by what?* Put the EOB's evidence in the list second but with
  `recorded_at` = Apr 10 and the user's `recorded_at` = May 1 (a late-arriving re-import, or a
  merge). List order says EOB is latest; time says the user is. **Position and time diverge, and
  the state follows position.** The fixture's third section measures exactly this.
- **Which time is meaningful here?** The user's utterance has one time — when they said it.
  The EOB has two — its adjudication date (its own as-of) and when it was imported. For the
  *health* proposition, what the EOB says is not dated in the way a balance is: the claim *this
  service was medical* does not change between April and May. So for the health tie the
  meaningful recency is **when each party last stated its stance** — `recorded_at` for the
  utterance; for the EOB, its own date if held, its import if not.

**Forces finding 1.** The health tie's recency rule (Q2) is sound **only when "latest" is on
the evidence's own time**, never on list position. Today it is position. That is the temporal
latent, and this case is where it stops being latent: a late-arriving EOB that predates the
user's statement must not become "latest" by being appended last.

## Case T2 — reaffirmation: the last word

User: *health* (Mar). EOB: *not* (Apr). User: *health, I'm sure* (May).

- Under Q2: current = `user_asserted`; `resolution()` = kind *reaffirmation*, resolver = user,
  contradictions = 1. The user's restatement makes their stance current.
- **What this means, stated plainly so it is chosen and not discovered:** among equals, **a
  party can always regain currency by restating.** Q2 accepted this and ruled that the count of
  contradictions is *history, never confidence* — a user who restates five times is not five
  times more right, and the EOB's dissent is visible every time.
- What this case does **not** do: reopen Q2. It records that the health tie is resolved by
  *whose stance is most recent on its own time*, and that this is a chosen property with a
  known consequence.

**Forces finding 2.** For two independent knowing parties, *tie* means **equal rank, resolved
by most-recent stance on the evidence's own time, with the dissent carried.** It never means
*count*. Settled by Q2; the case adds only the time axis (T1).

## Case T3 — P-ack, one party, two statements, one as-of

P issues two statements both dated Sept 1: one says $1,925, one says $2,100. Both imported —
the $2,100 one second.

- **Same proposition** (P's position at Sept 1), **same as-of**, **same channel** (P, issued),
  **same party.** F4's ordering has nothing to order. F1-forced named this a self-conflict by
  P; the question is what is *current*.
- **Recency by as-of:** equal. No tie-breaker.
- **Recency by `recorded_at`:** the $2,100 one, imported second. **But `recorded_at` on an
  imported document is the household's import order, not P's issuance order** — the household
  may have scanned them in any order. Using it is `[-1]` under another name: the winner is
  whichever the household happened to import last, which is not a fact about P's position.
- **So no time axis breaks it.** The meaningful time for P-ack is as-of, and as-of is equal.

**Forces finding 3 — the result the P-ack tie adds.** For a same-party, same-as-of
disagreement between dated documents, **no recency exists**: as-of is equal and `recorded_at`
is not evidence about the proposition. The record must hold **an explicit unresolved state** —
D7's default, *unresolved, not guessed* — and it is resolved only by something that is
evidence: a later as-of (the next statement), a supersession claim (T4), or E's confirmation.
**Never by import order.** This is the one place a genuinely unbreakable tie exists on the
board, and it is not the health tie.

## Case T4 — the corrected statement

As T3, but the $2,100 statement carries *"CORRECTED — supersedes statement of Sept 1."*

- **Not a tie.** The artefact makes a P-subject claim about *another artefact*: *statement B
  states that it supersedes statement A.* That is a held-referent relationship between two
  documents (D6's shape, retraction reaching by reference), and P's current position at Sept 1
  is B's — because B says so, not because B was imported later.
- The resolution is by **the document's own claim**, which is evidence. Compare T3, where
  nothing in either document says anything about the other.

**Forces finding 4.** P-ack same-as-of conflicts resolve in the world by **supersession
claims inside the documents**, and the record must be able to hold *B supersedes A* as a
P-subject relationship. When the documents make no such claim (T3), the record holds
*unresolved* and waits.

## Case T5 — two captures, same minute, different figures

Two screenshots of S's portal, both stamped Sept 1 14:32, one showing $1,925, one $2,100.

- Same channel (live system), same as-of, both held (C2). Two artefacts of two renderings.
- Either the system's state changed between two renders seconds apart (a payment posting), or
  one capture is not faithful (the fenced trust question), or one is of a different account
  view. **Nothing in the record can say which.**
- Both are re-readable, so the disagreement is *examinable* — each side's figure is
  confirmable against its capture — and still **unresolvable between them**: the captures
  contradict each other and neither claims to supersede the other.

**Forces finding 5.** T3's result holds for held observations too: same channel, same as-of,
no supersession claim → **unresolved**, examinable but not decidable. Held-ness (captured-
portal ruling) buys examinability, not a winner — the ruling's *held is not strength* arriving
in the tie.

## Case T6 — consumers under an unresolved tie

The health tie is never unresolved after Q2 (recency decides). The P-ack tie can be (T3, T5).
What does each consumer do with *unresolved*?

| consumer | question it asks | safe terminal under unresolved |
|---|---|---|
| protection (what may leave the boundary) | is this health? | *stays health-sensitive* — gap 12: uncertainty may not resolve to safe |
| tax (`qualifying_amount`) | is content health attested? | **$0** — nothing attested; no figure manufactured |
| `remaining` (payment projection) | has P acknowledged this? | **confirmed remaining does not move** — the ruled sequence stalls at *attached, unacknowledged* |
| narrator | what may be said? | *"P's two Sept 1 statements disagree; we can't tell which is current"* — the honest report, F5's shape |

Each fails closed in its **own** direction. The §7.7 fallback ruling's rule — *where required
evidence is absent, the consumer determines the safe terminal behaviour* — is the same rule
here with *unresolved* in place of *absent*.

**Forces finding 6.** An unresolved tie needs **no rank.** It needs a state each consumer can
map to its own fail-closed terminal. A rank would have to choose one direction for all of
them, and T6 shows they differ.

---

## What the cases force

1. **The health tie's recency rule is sound only on the evidence's own time, never on list
   position** (T1). The temporal latent stops being latent at the first late-arriving import.
2. **For two independent knowing parties, tie = equal rank, most-recent stance wins, dissent
   carried, count is history** (T2). Q2's settlement, plus the time axis.
3. **For one party against itself at one as-of, no recency exists** (T3). As-of is equal;
   `recorded_at` on documents is import order and is not evidence. The record holds
   *unresolved*.
4. **Same-as-of document conflicts resolve by supersession claims inside the documents** (T4)
   — evidence, not order — and the record must be able to hold *B supersedes A*.
5. **Held observations tie the same way** (T5). Examinable, not decidable; held is not a
   winner.
6. **An unresolved tie needs a state, not a rank** (T6). Each consumer fails closed in its own
   direction.

---

## The fence's question, answered by the cases — not ruled

> *Which time axis breaks a same-proposition, same-as-of disagreement between equals — and
> what does the record hold when no axis can?*

**The axis is the evidence's own time, and which time that is depends on the evidence kind:**

```text
testimony (utterance)         recorded_at — its only time
dated document / capture      its as-of — never its import order
```

**The health tie has an axis** (each party's most recent stance) and Q2's recency rule works
on it — once *latest* means the evidence's time and not the list's. **The P-ack within-channel
tie has none** — same party, same as-of — and the record holds **unresolved**: resolved by a
later as-of, a supersession claim, or E's confirmation; never by import order, count, or
position; and consumed by each consumer at its own fail-closed terminal.

**The health ranking was not imported.** The two ties differ in *why* they are ties — two
equal parties versus one party with itself — and the difference in reason produced a
difference in answer: one has recency, the other does not.

---

## What the cases do not establish

1. **The name or shape of the unresolved state.** T3/T5 demand it; nothing here designs it.
2. **The resolver.** T1 makes *by evidence time* a requirement for `_state_from` and
   `resolution()`; it does not redesign either. And the R-ASSERT ruling stands: the existing
   source-history kinds are right for testimony conflicts; T3/T4 are document conflicts and
   may need the reading/document-level kind.
3. **Whether Q2's last-word property should ever change** (T2). Recorded as a chosen
   consequence; not reopened.
4. **What a supersession claim requires to be trusted** (T4) — the document says it supersedes;
   whether that is enough is the faithfulness fence in another form.
5. **Representation** of *B supersedes A*, of as-of on evidence, or of unresolved.

---

## Decision remaining — Rob's

Whether to lift the fence on these terms: *latest* is on the evidence's own time — `recorded_at`
for utterances, as-of for documents — never list position; the health tie keeps Q2's recency
rule on that axis; the P-ack within-channel tie has no axis and is held unresolved, resolved
only by evidence, consumed fail-closed per consumer; and no rank is created for a tie in
either case.
