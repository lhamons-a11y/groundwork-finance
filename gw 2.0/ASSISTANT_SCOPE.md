# ASSISTANT SCOPE — the learning layer Groundwork builds for itself

**Status:** scope, not design. Decided 2026-09-02. Nothing here is built.
**Relationship to `C:/Assistant`:** none in code. That product continues on its own.

---

## What this is

Groundwork 2.0 needs to know a person well enough to teach them — that is the
Willingness Layer (blueprint Appendix F). The Assistant already solved most of that
problem generally, in `LEARNING.md`. This document says which parts Groundwork rebuilds
for itself, which it already has, and which it will not have at all.

**The premise is `LEARNING.md`'s, and it is the reason any of this exists:**

> generic advice mostly is not wrong, it is unfollowed

So the value of knowing a person is not better answers. It is answers they act on.

## What "scaled down" means

Not a smaller version of the Assistant. A **narrower** one — finance only, Groundwork
only — and narrowness is what buys depth. A general assistant has to be shallow about
money because it is also about calendars and health and research. This one is only ever
about money, so it can go further into it than the original design could.

---

## Why a second implementation, honestly

The case against is real and should be stated first: **two implementations of the same
ideas is two places to get them wrong**, and one of those ideas is the persistence
boundary, where a bug is a privacy incident rather than a wrong number.

Three things outweigh it.

1. **Different clocks.** GW 2.0 targets 2027. The Assistant's horizon is ~2029-30.
   Sharing code would drag the earlier product onto the later one's schedule and freeze
   both designs before either had evidence.
2. **Groundwork becomes the proving ground.** Shipping two to three years earlier
   against real ledgers means the lessons flow *Assistant-ward from something that
   actually ran* — the reverse of the usual duplication argument.
3. **The domains genuinely differ.** The Assistant's taxonomy example was debt payoff
   method. Groundwork's is which of its own seven levers a person reaches for. Same
   discipline, different objects.

**The one thing that must not diverge:** the persistence boundary. Same rule, same
deletion test, asserted independently on each side (blueprint §9/§10). Everything else
may differ.

---

## The five layers, mapped

`LEARNING.md` has five layers, each checked differently. Groundwork does not need five
new ones — it already has three of them under other names.

| layer | Groundwork's version | status |
|---|---|---|
| **1. Observation** — cited facts | the ledger + Historian + proof-not-persuasion (Appendix B) | **exists in 1.x.** Reuse; do not rebuild. |
| **2. Strategy** — the only inference, made falsifiable | willingness strategy over the §6.1 levers | **written** (Appendix F.6a/F.6b, 2026-09-02). Not built. |
| **3. Anticipation** — what comes next | F.8 projection: deterministic consequence conditioned on demonstrated willingness | **written.** F.8 *is* this layer. Do not build a second one. |
| **4. Approach** — how to tell *this* person | Appendix A governs *when* to speak; B.2a governs *register* | **the gap.** Nothing governs how to frame for a particular person. |
| **5. The offer** — stakes decide whether it may recommend at all | §6 levers, C's honest-no, E's ranking | **mostly exists.** The stakes gate needs checking against C. |

### Layer 4 is the actual work

This is where "better financial conversation and understanding" lives, and it is the one
layer Groundwork has no equivalent for. Appendix A answers *may we speak*. B.2a answers
*in what register*. Neither answers *how should this be framed for someone who has shown
us they run snowball and will not touch timing*.

`LEARNING.md`'s discipline applies unchanged: **approach is derived, never asserted.** It
is a consequence of the strategy label, carries no independent claim about the person,
and disappears when the label drops to `unclassified` — which, per F.6b, is most of the
time for most people.

---

## What Groundwork has that the Assistant did not

These are the structural advantages that make this version better rather than smaller.

- **The raw material is the product.** The Assistant discards conversations, so anything
  it wants to remember it must derive — and derivation is what the persistence boundary
  forbids. Groundwork keeps the ledger and the user sees all of it, so every derivation
  can be redone. The boundary costs compute, not capability (§10).
- **The taxonomy already exists.** §6.1's seven levers are the strategy vocabulary. No
  behavioural categories get invented, which is the failure mode that turns a taxonomy
  into a horoscope.
- **Every claim already has to cite.** Proof-not-persuasion (Appendix B) and the R8
  number-provenance gate were built for the narrator; the learning layer inherits both
  rather than negotiating them.
- **A joint account has no author.** Settled 2026-08-13: visibility belongs per-account,
  in Groundwork, because Groundwork owns accounts. That replaces the Assistant's
  per-person historian split wholesale — the hardest part of its multi-user model simply
  does not arise here.

---

## Out of scope, permanently

Not "later." These are the narrowing that makes the depth affordable.

- **No ambient capture.** No microphone, no passive observation of anything the user did
  not hand over as a transaction or type as a declaration.
- **No non-financial domains.** No calendar, health, research, correspondence.
- **No per-person historian.** Per-account visibility instead (2026-08-13).
- **No cross-product transfer.** A strategy earned here is a claim about finance
  behaviour in Groundwork. It does not travel to the Assistant, and nothing travels back.
- **No motive.** Refused at the blueprint level (F.6b), and it is the line that keeps the
  whole layer falsifiable.

---

---

## What "conversation" means — SETTLED 2026-09-02

Two directions, and they are not the same mechanism. Conflating them is how a product
that answers questions turns into a product that interrupts.

### User-initiated — the answer surface

The user asks. The assistant answers from their data, the math, and the facts. Where the
evidence is insufficient to answer honestly, it asks a **direct question for a missing
fact** — never for a commitment.

> "I don't see income for March — is that missing, or was there none?"
> and never
> "would you consider cutting dining?"

That distinction is the whole design. Normal finance software asks questions to extract
commitment. This asks questions to **earn the right to compute**. Answering *"that $2,400
was a medical bill, not a vacation"* commits the user to nothing; it makes the next number
true. No shaming, no willingness interrogation, no pressure to cut anything.

Three properties fall out, and each removes work rather than adding it:

- **No frequency cap needed.** A.3's budget governs *unsolicited* speech. A clarifying
  question inside an answer the user asked for is part of the answer, not an interruption.
  F.4's "don't over-ask" governs *willingness* asking specifically, and does not reach here.
- **Answers persist legally, with no new machinery.** A reply to a factual question is a
  declaration made in context — surfaced by definition, therefore eligible under §10's
  persistence boundary. It is the Declared channel of F.6a, arriving through a new door.
- **It is the structural cure for treating absence as zero.** An engine that cannot
  distinguish "no data" from "zero" answers confidently and wrongly. Asking is how that gap
  closes, and it is the honest alternative to guessing.

**Question selection — a candidate, not a decision.** F.8's swing asks where one small
change most moves the outcome. Choosing *which* question to ask is plausibly the same
computation run on the unknown side: **which missing fact, if known, would most change the
answer.** That would give Layer 4 its selection rule from machinery already specified. It
should be tested before it is assumed.

### System-initiated — alarms and watches

Groundwork may also speak first. Appendix A already governs promotion to proactive, and
A.2's Actionability gate — *never proactively deliver bad news with no path* — is
independently the same rule industrial alarm practice arrived at: if there is no response
to make, it is information, not an alarm.

Two constraints are settled here even though the governance is not:

- **Alarm candidates come from what Groundwork can prove**, not from generic
  financial-wellness categories — the same reason the strategy taxonomy came from §6.1
  rather than being invented. Two detectors already exist and are the obvious first
  sources: F.8's break-detector and Appendix G's cycle recurrence.
- **The watch catalogue is gated by provability for *this* user.** Groundwork does not
  offer retirement watches to someone holding no retirement, or a spread of debt-free
  watches to someone carrying no debt who is using it as a ledger. Not as noise reduction —
  because there is nothing to prove, and offering a watch it cannot service is a promise it
  cannot keep (honest-null, §10; C.7). A user-set watch is sovereign and bypasses the
  frequency budget entirely, since the user asked for it; what is *offered* is still bound
  by what can be evidenced.

That makes the catalogue itself a teaching surface. Showing someone what can be watched,
what it would tell them, and where it would say nothing useful, is one of the more honest
things this product can do — and it is the same lesson as the honest-no, delivered before
the fact instead of after.

## Open

- **Alarm and watch governance is not designed.** Appendix A covers promotion at runtime,
  per instance. Industrial practice adds three things it lacks: **rationalization** (each
  alarm *type* justifies its existence at design time — cause, consequence, response,
  priority basis — which is this document's own "Gated" discipline applied to a bucket that
  does not have it); **measured delivered rate** treated as a design defect when it drifts,
  the way the voice gate's miss-log is used; and **stale conditions** — something true and
  unresolved for months, where re-telling is nagging but dropping it silently is dishonest.
  The blueprint has no answer to the third.
- **Alarms are a fourth prompt-kind, and the budget does not fit them.** A.3 budgets brakes
  and green-lights. The contradiction-check is already flagged unpinned (§12). Alarms make
  three unbudgeted kinds against two budgeted ones, so §12's open item is larger than it
  currently reads.
- **Gate 2 versus genuinely path-less news.** A.2 requires an honest §6 solution before a
  brake may interrupt. Some alarming facts have no lever — income stopping. The honest-no
  always carries a nearest lever and nearest reachable goal, so this may resolve itself, but
  "we never deliver bad news with no path" and "the user needs to know this" can collide and
  it should be checked deliberately rather than assumed.
- **Layer 5's stakes gate.** `LEARNING.md` makes stakes decide whether the system may
  recommend at all. Groundwork's honest-no (Appendix C) governs what it may *claim*, not
  whether the stakes permit a recommendation. Whether these are the same rule seen twice
  or two rules that need reconciling is unchecked.
- **Where Layer 4's output is surfaced** is entangled with F.3, which is still the open
  frontier. This document does not resolve F.3 and should not be read as narrowing it.
