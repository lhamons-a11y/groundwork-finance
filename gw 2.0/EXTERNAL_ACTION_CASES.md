# Naming an external action — what Groundwork may say, and what it knows when it says it

**Gap 14, attacked with cases on wording, before deciding whether "external action" needs an
abstraction at all.**

> Status: **Case set, 2026-09-11. No abstraction, no surface, no copy. The decision is Rob's.**
>
> `HEALTHCARE_GAP_TRIAGE.md` gap 14: §0.3 settles *cost, not counsel* for healthcare
> specifically, and the review's generalisation — *a user-verifiable external action may be named
> when it follows from an established fact; an outcome or negotiation position may not* — exists
> nowhere as a reusable rule. `USER_KNOWLEDGE_CASES.md` U3 leaned on it (*ask them to look, not
> to know*) and noted it was ungeneralised.
>
> Rob's framing of the question:
>
> > **What external action may Groundwork legitimately recommend, request, or defer — and what
> > does it actually know when it does so?**
>
> **Nothing to run.** No shipped narration in `core/` names an external action; the surface is
> unwritten. So the cases are held against the three doctrines that already govern them —
> §0.3, the permission ladder (`Record → Calculate → Conclude → Recommend`), and the interface
> rule (*ask for evidence, never for conclusions the user cannot know*) — and one case is run
> against the evidence model, because it is where an instruction could become evidence.

---

## What §0.3 already permits and refuses, which is most of the answer

Permitted, and it is most of the value:

- **arithmetic on the user's own money**
- **general information, not applied** — *debts have a statute of limitations* is publishable;
  attaching it to *this* debt is not
- **naming that a question exists, and who answers it** — *"a referral is the opposite of a
  conclusion"*

Refused, even where useful: computing a legal position; **suggesting what to offer a collector,
because the offer itself is a legal act whose consequences the app cannot see**; estimating the
effect of an action on rights.

The third permitted item and the second refused item are the two ends of gap 14. Everything
below is finding where the line between them runs.

---

## The cases — wording that changes the epistemic claim

Each wording is held against: what it **asserts**, what Groundwork must **know** to say it, which
**rung** it climbs, and where §0.3 puts it.

### E1 — "Your EOB will show whether this was covered."

| | |
|---|---|
| asserts | a fact about **where evidence lives** |
| must know | coverage is unresolved; an EOB is the document that carries the answer |
| must NOT know | what the EOB says |
| rung | Record — *naming that a question exists, and who answers it* |
| §0.3 | **permitted**, verbatim |

The cleanest form. It names a source, presumes nothing about the user's goal, and asserts
nothing about the world beyond *this kind of document answers this kind of question*.

### E2 — "Check your insurer."

| | |
|---|---|
| asserts | the same source — **phrased as an imperative** |
| rung | edges toward Recommend: it tells the user to act |

Same referral as E1 with the epistemic claim unchanged and the **agency** changed. The
imperative presumes the user wants the question answered. It is not counsel, but it is the
first step toward it, and the difference from E1 is grammatical, not evidential — which is
exactly why wording is the right unit of analysis here.

### E3 — "Call your insurer and ask whether the service was covered."

| | |
|---|---|
| asserts | an action, **and its content** |
| must know | the insurer is a **knowing source** for this proposition — a claim about the world |
| rung | Recommend, of an evidence-gathering action |

Still on the evidence-gathering side — the result of the call is a fact the user learns, not a
change to anything. But it carries a second claim E1 did not: that *this party can answer this*.
For coverage, true. For *is this debt enforceable*, no party the app can name is a knowing source
the app may consult, and §0.3 says so. **So E3 is permitted exactly when the proposition is one
the named source can settle, and the app has to know that before it speaks.**

### E4 — "Submit an appeal." / "Dispute the charge."

| | |
|---|---|
| asserts | an action whose **result is a change in the world**, not in the record |
| rung | Recommend — and §0.3's *the offer itself is a legal act* |
| §0.3 | **refused** |

This is the line. An appeal, a dispute, an offer: each changes the user's position with a third
party, has consequences the app cannot see, and may affect rights. *"Suggesting what to offer a
collector"* is refused by name, and these are its family. **The distinction is not
information-gathering versus action — E3 is an action. It is whether the action's result is
evidence or a changed state of the world.**

### E5 — "Contact your provider about the balance."

| | |
|---|---|
| asserts | an action with an **unstated purpose** |

Ambiguous by construction: *about the balance* could mean *find out what it is* (E3, permitted)
or *negotiate it down* (E4, refused). The wording does not say, so the sentence permits either
reading, and a user will take the one the app did not intend. **A named action must carry its
purpose, because the purpose is what §0.3 rules on.**

### E6 — "You need to call your insurer."

| | |
|---|---|
| asserts | the user's goal, **and** urgency, **and** the action |
| rung | Recommend — a decision made on the user's behalf |
| §0.3 | **refused** — this is counsel regardless of what the action is |

Versus:

### E7 — "If you want to establish whether this was covered, your insurer can tell you."

| | |
|---|---|
| asserts | a conditional: *the goal is yours; here is who answers it* |
| rung | Record — general information plus a referral |
| §0.3 | **permitted** |

**E6 and E7 name the same action and are on opposite sides of the line.** The difference is one
feature: **does the sentence presume the user's objective?** E7 leaves the goal with the user
and says where the evidence is. E6 decides the goal, adds *need*, and issues the action. That is
the boundary Rob asked to attack — *here is the next thing you can do to obtain evidence* versus
*here is the thing you should do* — and it turns on presumption of goal, not on the verb.

### E8 — no external action available

*We cannot establish whether this debt is enforceable.* — with no referral to an action, because
§0.3 refuses every action that would compute it. **Groundwork may say it cannot establish
something without inventing a workaround.** The honest-null discipline applies to actions as it
does to figures: an absent path is reported as absent, not filled with *you could ask a lawyer*
dressed as help. (*Naming who answers the question* — the CFPB, legal aid — remains permitted;
what is refused is presenting that as a path to a conclusion the app will then hold.)

---

## The other side: what comes back

### E9 — the action succeeds. What evidence does the answer acquire?

The user calls; the insurer says *covered, patient responsibility $412*. The user enters it.
**Run against the evidence model:** it arrives as

```python
record_evidence(c, CONTENT, source=USER_STATED, supports=True, amount=412.0)
```

`USER_STATED`. Rank 3. The top of the lattice. **Indistinguishable from the user asserting it
from their own knowledge.** But it is not the user's knowledge — it is the user's report of what
a third party said, orally, with no artefact Groundwork can ever hold. That is
`DOCUMENT_IDENTITY_CASES.md` D5 (*testimony about a document*) extended to a source that is not
a document: **testimony about a phone call** is *about / referenced* with nothing to reference.

So the result of a permitted external action re-enters through the same one-bit channel as
everything else, and acquires that channel's meaning — the user knows this — which V6 already
named as the failure shape. The finding is not new; it is the document-identity gap arriving
from a fourth direction, and it belongs there, not in a new abstraction.

### E10 — the action fails, or produces ambiguity

The user calls; the line is busy, or the representative says *it depends*. Nothing to enter.
**The record must remain unresolved.** The attempt is not evidence, and *the user tried* is not a
proposition on any axis.

### E11 — the adversarial case: told where to look ≠ resolved

Groundwork knows an EOB would settle the question. It says so (E1). It has **no evidence the user
looked.**

**The rule the case forces:**

> **An instruction shown is a fact about Groundwork's surface, never a fact about the world. It
> produces no evidence. Only the user's report of the action's result does, and that report is
> testimony about a third party, marked as such.**

The V6 shape, exactly: an instruction forced through the evidence channel would acquire the
channel's meaning — *we told you to check* becomes *checked* becomes `supports = True`. Nothing
in the module can do that today, because nothing in the module represents an instruction. The
danger is a future surface with a *done* control that records `USER_STATED, supports=True` when
the user dismisses the prompt. **That control would be `qualifying_amount`'s `[-1]` for
actions** — a convenient path that silently manufactures a rank-3 fact — and it is refused here
before it exists.

---

## The rule the cases earn — as distinctions, not an abstraction

Four features decide every case above, and no single one does:

```text
result       evidence (E1–E3, E7)         versus   a changed state of the world (E4)
goal         left with the user (E7)      versus   presumed by the sentence (E2 → E6)
source       a knowing source for THIS proposition (E3's precondition)
purpose      stated (E3)                  versus   unstated (E5)
```

Stated once, generalising §0.3's third permitted item and its second refusal:

> **Groundwork may name where evidence lives and who can supply it, conditionally on the user's
> goal, when the named source is a knowing source for the proposition. It may not name an action
> whose result is a change in the world rather than a change in the record, and it may not
> presume the goal. An instruction shown is a fact about the surface, never evidence; the result
> of an action re-enters only as the user's testimony about a third party.**

### Does "external action" need shared representation?

**No — and the cases say why.** The instruction half has no representation need until a surface
exists, and gap 9 records that none does. The result half reduces entirely to the
document-identity gap (*about / referenced*, extended to sources that are not artefacts) and the
proposition-space gap (a phone call's answer is a value about a proposition, not a bit). Both
already have homes. An `ExternalAction` type would be a third home for two things that have two,
and it would invite E11's *done* control by giving it somewhere to write.

---

## What each distinction permits

| Distinction | Permits |
|---|---|
| evidence path, goal left with user | *if you want to know whether this was covered, your EOB will say* |
| named source is knowing for this | *your insurer can tell you what they paid* — and **not** *your insurer can tell you if this is enforceable* |
| result vs world-change | *here is where the answer is* — and **never** *submit an appeal* |
| instruction ≠ evidence | *we suggested checking; we don't know whether you did* |
| result is testimony | *you told us the insurer said $412* — not *the insurer said $412* |
| no path available | *we cannot establish this* — without a workaround |

---

## What has not been done

No `ExternalAction`. No copy. No surface. No change to how testimony re-enters the evidence model
— E9's finding is filed under document identity, where it belongs, and not repaired here.

**What is Rob's:** whether E2 — the bare imperative referral, *check your insurer* — sits on the
permitted side with E1 or the refused side with E6. The cases put it between them, and the
sentence a narrator is allowed to produce depends on the answer.
