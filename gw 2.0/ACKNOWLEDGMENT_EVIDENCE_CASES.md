# Acknowledgment evidence — what proposition, which sources know it, and where discharge stops

> Status: **Case set, 2026-09-12. Evidence mode. No decision, no source enum, no change to
> `core/classification.py` or `core/payment_plan.py`.** Rob opened the second fence in evidence
> mode, the one S3/S6 pointed at: *not who was paid, but what evidence lets Groundwork know that
> the entitled party acknowledged the payment or balance.*
>
> **The opening question, his, shaped by the Cluster B result:**
>
> > **What proposition is the acknowledgment evidence actually establishing, and how should
> > independently knowing sources be ranked for that proposition?**
>
> **Answer only these four:**
> 1. What is the proposition being acknowledged?
> 2. Which source relationships constitute knowledge of it?
> 3. Does source ranking behave independently of the health evidence ranking?
> 4. Does the result establish discharge, or only evidence relevant to discharge?
>
> **The standing rule this case must not erode:** *a payment may evidence discharge; it does not
> establish discharge merely by destination* (`SERVICING_ONLY_CASES.md`, ruled). This case must
> not quietly turn *good balance evidence* into *discharge*. It has to find the boundary.
>
> **The observation this case must not assume:** the health ranking — `USER_STATED` and
> `IMPORTED_EOB` tied at rank 3 as the two `KNOWING_SOURCES` — is a *mechanism shape*, not a
> table to reuse. Same shape, different proposition, different subject, own case.
>
> **Fence.** Representation of any of this; the `remaining` projection; U6 (four balance figures);
> servicing history; payment implementation; §8 — all adjacent, none opened. Where a case
> reaches one, it stops and says so.

---

## 0. Why the health sources rank as they do — the reason, not the table

`core/classification.py`: *"Sources that come from a party with knowledge of the transaction.
Only these may take a transaction OUT of the boundary, and only these establish content."* The
user and the EOB tie because **each has first-hand knowledge of the health proposition** — the
user was there; the insurer adjudicated the claim. Two independent knowing parties, so
corroboration between them is meaningful and a tie between them is honest (gap 15 refused to
invent a hierarchy).

That is the reason. The test for transfer is whether the same reason holds for the new
proposition — not whether the same names appear.

---

## 1. The base situation, carried from the servicing-only cases

Provider P owed $2,100 on 12 × $175. Servicer S sends the statements. The household paid S
$175 on Aug 3 and recorded it against P's obligation. Under the ruling, that payment is
*attached, unacknowledged* until the entitled party acknowledges it.

---

## Case K1 — the entitled party's own statement, held

P mails a statement dated Aug 20. Imported as a PDF. It reads: *payment received Aug 5, $175;
balance $1,925.*

- *What it is:* a held artefact (R-HELD) from the entitled party.
- *What it establishes, in Cluster B's terms:*
  - **P-subject:** *statement K1 states: payment $175 received Aug 5; balance $1,925.*
    Established by parsing, resolvable by re-reading.
  - **P-ack:** *P acknowledges the $175 payment and states a balance of $1,925.* Established,
    because the statement *is* P's stated position — it is what P says, from P.
  - **P-world** (*the household truly owes $1,925*): **not established, and never will be by
    any acknowledgment.** §8.2a's premise is the standing rule: every figure rests on *this
    debt is owed by this person in this amount*, which the app cannot check. P's statement is
    P's claim about the world, held at P's authority.
- *Sentence:* *"P's Aug 20 statement shows your Aug 3 payment received and a balance of
  $1,925."* True. *"You owe $1,925."* Not Groundwork's to say without the premise attached.

**Forces finding 1.** The proposition acknowledgment evidence establishes is **not the
balance. It is the entitled party's stated position** — call it P-ack — a proposition *about
E's stance*, with E as its subject. Discharge, as ruled, *is* E's acknowledgment; so evidence
that establishes P-ack for a payment establishes discharge of that payment **by definition, not
by inference.** The true balance stays a premise.

---

## Case K2 — the servicer's statement, held

Same content, on S's letterhead, imported. P never sends its own statements; in the servicing-
only world **every** acknowledgment arrives this way.

- *P-subject:* *statement K2 states …* — established.
- *P-ack:* established **only through the relationship** *S speaks for P.* Groundwork holds
  that relationship as the household's attachment of S as the servicer of the obligation — a
  household claim (S1). So P-ack via K2 is a **two-link chain**: *S states X* (held, strong) ×
  *S speaks for P* (household-asserted, unverifiable).
- *The alternative, and why it fails:* rank the servicer's statement as *not* E's
  acknowledgment. Then in the servicing-only world **discharge is unreachable** — the exact
  M-LED failure from the §7.7 test, arriving one layer down. A doctrine that can never be
  satisfied from where Groundwork stands will be satisfied by manufacture.

**Forces finding 2.** A statement from **the servicer of record** constitutes E's
acknowledgment — and its strength is bounded by the weakest link, which is the household's
assertion that S serves P. That is the built weakest-link rule (`strength_of`: *the weakest
material source, computed on every read*) applied to a chain the health question never had.
**The mechanism transfers; the ranking does not.**

---

## Case K3 — the never-authorised servicer's statement, held

S3 (from the servicing-only cases) sends a statement: *payment received; balance $1,925.*
Imported. The household had attached S3 as servicer when the first letter came.

- Byte-for-byte the same evidence shape as K2. Same chain. Same strength.
- *What distinguishes it:* nothing Groundwork holds. Only P can say S3 does not speak for it —
  and P's own next statement (K1) will not show the S3 payment.

**Forces finding 3.** Acknowledgment via a servicer **rests on a claim Groundwork cannot
verify**, and the record must say so rather than let the chain's *held* link lend its strength
to the *asserted* link. This is not a defect of the ranking; it is the ranking being honest.
The correction arrives as **conflict** (K7), not as a better rank for K2.

---

## Case K4 — the portal balance, observed

The household logs into S's portal on Sept 1 and sees *balance $1,925*. No artefact is held
unless a capture is taken.

- *Not held* → not re-readable; it is the household's **observation** of a live system, so
  what enters the record is *the user reports the portal showed $1,925 on Sept 1* — R-ASSERT's
  shape, D5's *testimony about an artefact*.
- *Same agency chain as K2* (the portal is S's).
- *What it has that K1/K2 lack:* **currency.** It is the figure as of today; a statement is
  as of its date.

**Forces finding 4.** Two properties of an acknowledgment source that the health question
never separated: **reproducibility** (held vs observed) and **timeliness** (as-of date). K4 is
weaker than K2 on the first and stronger on the second, and a ranking that has one axis
cannot order them. **Every acknowledgment carries an as-of date, and comparing two
acknowledgments without their dates is not a comparison.**

---

## Case K5 — the user's report of what a statement says

*"The statement says $1,925."* No import.

- *Health analogue:* `USER_STATED` — rank 3, tied with the EOB, because the user *knows* whether
  the purchase was medical.
- *Here:* the user **does not know what P acknowledges.** Only P does. The user can only
  **report an artefact** — and *the user reports the letter says X* is not *the letter says X*
  (`USER_KNOWLEDGE_CASES.md`).

**Forces finding 5 — and answers question 3 directly.** For P-ack, **the user is not a
first-hand knowing party.** The health tie exists because the user has first-hand knowledge of
*that* proposition; for *this* proposition the user has none, and `USER_STATED` collapses to
testimony-about-an-artefact. **The reason behind the health ranking does not hold here, so the
ranking does not transfer** — and not by adjustment; by the knowing set being different.

---

## Case K6 — the household's own bank shows the payment cleared

The bank statement shows *$175 to S BILLING SVC, cleared Aug 5.* Imported.

- *Held. Independent of P and S.* The strongest evidence in the set — of something else.
- *What it establishes:* the household's money **left** and S **received** it. A fact about the
  household's side of the payment.
- *What it does not establish:* that P credited it. S2 (servicer changed) and S3 (never
  authorised) are exactly the worlds where K6 is true and P-ack is false.

**Forces finding 6.** **Payment-completion evidence and acknowledgment evidence are different
propositions, and the strongest possible evidence of the first is no evidence of the second.**
This is the ruled sentence — *a payment may evidence discharge; it never establishes it by
destination* — with the bank's confirmation as the hardest case: even *cleared* is on the
wrong side of the line.

---

## Case K7 — conflicting sources

K1 (P's statement, Aug 20): *$175 received; $1,925.* K4 (S's portal, Sept 1): *$2,100.* K5
(user): *"I think it's $1,925."*

Three readings, and the first thing to do is not rank them:

- **K1 vs K4 may not be a disagreement at all.** Aug 20 vs Sept 1 — a reversal, a fee, a
  posting error, a different account view. Two figures at two as-of dates are two facts until
  something says they are about the same as-of. Finding 4 again: **date first, then rank.**
- If they *are* the same as-of, they conflict, and the knowing rank orders them: **P's own
  held statement > servicer's live portal (agency + observed) > user's report.** Not by
  count — there is **one knowing party** for P-ack, which is P, and everything else is a
  channel to P. Two channels agreeing are not corroboration (*source instance ≠ source
  independence*, the `4 → 6` constraint).
- **The tie that cannot happen here.** Health has two independent knowing parties, so a tie is
  honest. P-ack has one, so **no two sources of P-ack are ever equal**; there is always a
  channel ordering. The gap-15 tie state is health's, not this proposition's.

**Forces finding 7.** Conflict resolution for P-ack is **by channel, after date** — never by
count, and never by position. And Q2's resolver — *the first event after the last
disagreement*, ordered by position today — has no dates; `EVIDENCE_MATRIX.md`'s *supersession
is positional where the record is temporal* is **live for this proposition from its first
case**, not latent.

---

## Case K8 — the payment is acknowledged and the balance is not what Groundwork computed

P's statement: *$175 received Aug 5; balance $1,900.* Groundwork's `remaining` after the
payment: $1,925.

- **P-ack for the payment: established.** The $175 is credited. Discharge of *that payment*
  holds.
- **P-ack for the balance: established** — P says $1,900.
- **The $25:** an adjustment P applied (gap 6's `record_adjustment` — *the obligation itself
  changing, not a payment*), or P's error, or a fee. **Not an acknowledgment question.** It is
  a disagreement between P's stated balance and Groundwork's computed one — which is U6's
  shape (*stated on a date · computed from payments*) and stays there.

**Forces finding 8.** Acknowledgment is **two propositions, not one**: *E acknowledges this
payment* and *E states this balance.* **Discharge rests on the first.** The second feeds the
`remaining` projection and can disagree with it, and that disagreement is a different fact
with a different home.

---

## What the cases force

1. **The proposition is E's stated position — P-ack — not the balance and not the world.**
   Discharge of a payment is P-ack for that payment, by definition. The true balance stays
   §8.2a's premise (K1).
2. **The servicer of record's statement is E's acknowledgment, at weakest-link strength** —
   the held statement × the household's assertion that S serves E (K2). Refusing this makes
   discharge unreachable.
3. **Servicer acknowledgment rests on an unverifiable claim, and the record must say so** —
   corrected by conflict with E's own statement, never by ranking (K3).
4. **Acknowledgments carry an as-of date, and reproducibility and timeliness are separate
   axes** (K4). Comparing without dates is not comparing.
5. **The user is not a knowing party for P-ack.** `USER_STATED` here is testimony about an
   artefact. The health ranking's *reason* fails for this proposition, so its table does not
   transfer (K5).
6. **Payment-completion evidence is not acknowledgment evidence**, even when it is the
   strongest evidence in the record (K6).
7. **Conflicts resolve by date, then by channel — never by count or position.** One knowing
   party means no ties and no corroboration; two channels agreeing are one source (K7). Q2's
   positional resolver is live-wrong for this proposition.
8. **Acknowledgment of a payment and statement of a balance are two propositions; discharge
   rests on the first** (K8).

---

## The four questions, answered

| | |
|---|---|
| **1. What proposition?** | **P-ack: the entitled party's stated position** on a payment (credited or not) and on a balance (as of a date). Subject: E's stance. Not P-world. |
| **2. Which relationships constitute knowledge?** | **E itself** (held statement); **E's servicer of record** (held statement, bounded by the household's agency assertion); **E's or servicer's live system** (observed, dated, not held); **the user reporting any of these** (testimony about an artefact). One knowing party, four channels. |
| **3. Independent of the health ranking?** | **Yes, structurally.** Health has two first-hand knowing parties and an honest tie; P-ack has one knowing party and a channel ordering with no tie. The weakest-link mechanism transfers; the `KNOWING_SOURCES` set and `_RANK` do not. |
| **4. Discharge, or evidence relevant to discharge?** | **Evidence for P-ack, with a strength.** P-ack-for-a-payment *is* discharge by the ruling — so the evidence establishes discharge **at the strength of its weakest link.** Whether a given strength is enough to move a consumer — `remaining` — is that consumer's declaration, which is the `consume()` pattern and is **fenced** (payment implementation). *Good balance evidence* never becomes discharge: K6 and K8 hold the two lines. |

**The boundary Rob asked for:**

```text
payment evidence          →  the household's side; never discharge (K6)
acknowledgment evidence   →  P-ack, at weakest-link strength, dated
discharge of a payment    =  P-ack for that payment           (by the ruling; not inferred)
balance statement         →  a second proposition; feeds remaining; may disagree (K8 → U6)
remaining projection      →  a consumer declaring the P-ack strength it requires   (fenced)
```

---

## What the cases do not establish

1. **The representation** of P-ack, of channels, or of as-of dates. Findings, not fields.
2. **What strength `remaining` requires** before confirmed remaining moves — the consumer's
   declaration; payment implementation is fenced.
3. **U6.** K8 reaches it and stops.
4. **Whether a *captured* portal (screenshot) is held or observed.** K4 assumes no capture.
5. **The reading-level resolution kind.** K7 makes the dated resolver a requirement for this
   proposition; it does not design it.
6. **Servicing history** — *servicer of record* is used as the household's current attachment;
   whether it has a history is that fence's question.

---

## Decision remaining — Rob's

Whether to lift the fence on these terms: P-ack as the proposition; one knowing party, four
channels, weakest-link strength, dated; the health ranking's reason shown not to hold; and the
boundary — discharge is P-ack for the payment, at its evidence's strength, with the consumer's
required strength left to the consumer.

---

## Ruling — Rob, 2026-09-12. Fence lifted on exactly these terms.

*The case tested the reason behind the existing health ranking rather than pattern-matching its
output. That gives a principled non-transfer result.*

**1. The proposition is P-ack.**

> **The entitled party's stated position about a payment or balance, as of a stated date.**

Not the balance itself; not the truth of the household's obligation. For a payment, **P-ack for
that payment = discharge of that payment** — by the previously ruled definition of discharge,
not by inference from the evidence.

**2. One knowing party, four evidence channels.** The knowing party is E. The channels: E's held
statement; E's servicer-of-record's held statement, **bounded by the household's evidence that
the servicer actually serves E**; E/servicer live systems, which are dated observations rather
than held evidence; the user's testimony reporting one of those artefacts.

The health table's underlying reason — different first-hand parties can independently know the
proposition — does not exist for P-ack: the user does not independently know what E
acknowledges. Therefore:

> **The weakest-link mechanism transfers; the health `KNOWING_SOURCES` set, ranks, and tie
> behaviour do not.**

**3. Every acknowledgment is dated — frozen.**

> **P-ack has an as-of date; reproducibility and timeliness are separate dimensions.**

K7: what looks like a channel conflict may be two observations at different dates. The
existing positional resolver is therefore not merely theoretically questionable here — **it is
live-wrong for this proposition.** Its replacement is still not designed.

**4. Payment evidence stays separate from acknowledgment evidence.** K6 is the guardrail: **a
cleared payment does not establish acknowledgment** — the bank can know the household's money
left; it cannot thereby establish what E recorded. K8 keeps balance evidence from swallowing
discharge:

```text
payment acknowledgment   →   discharge of payment
balance statement        →   P-world / balance proposition
                             not the same proposition
```

The `$1,900` statement does not turn the `$175` acknowledgment question into a
balance-resolution question.

**The boundary around `remaining` — frozen, with the case's restraint kept:**

```text
payment attached
      ↓
acknowledgment evidence
      ↓
P-ack established at evidence strength
      ↓
discharge established at that strength
      ↓
remaining consumer decides what strength it requires        ← NOT decided; payment-implementation fence
```

> **Acknowledgment evidence establishes P-ack with a strength. P-ack for a payment is
> discharge. Whether that discharge is sufficient to change `remaining` belongs to the
> consuming projection and is not established here.**

**Explicitly not frozen:** no representation for P-ack; no automatic reuse of health source
ranks; no answer to U6; no captured-portal classification; no reading-level resolver design;
no servicing-history model; no §8 consequence. The fence lifts and **splits into new fences**
rather than opening payment implementation prematurely.

**The strongest result:** *same mechanism shape, different proposition, different subject,
different knowing relationships* — which is exactly why the health ranking could not simply be
copied.

`record_payment()` is left alone.
