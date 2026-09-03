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

---

## Standing conditions — SETTLED 2026-09-02

A condition that stays true and unresolved for months is the hardest case in alarm design.
Re-telling is nagging; going silent is dishonest. Industrial practice resolves it by
treating a standing alarm as evidence the alarm was designed wrong, and removing it — which
is right for a control room, where the operator cannot opt in or out.

Here the problem is different, and so is the answer. The alarm is not wrong. **The wrong
party owns it.**

> Repetition is nagging when the software chose it, and service when the user chose it.

So when the Historian shows a pattern that keeps recurring, Groundwork neither escalates nor
goes quiet. It **offers to hand the condition over**:

> "I've noticed you get near or past your budget most months. Would you like me to tell you
> when you're getting close?"

That is not a nag and not a scold. It is the software naming something already in the user's
own record, and offering the one capability it has that fits.

### What each branch resolves to

| the condition | what happens |
|---|---|
| **offer accepted** | it becomes **their** watch. It fires as configured and bypasses the frequency budget, because they asked for it. That is the instrument working, not a nag. |
| **offer declined** | that is an answer, and a first-class one (F.2). It is a declaration, so it persists under §10, and it is never re-run (A.2 gate 3). |
| **no watch form fits it** | it **stays passive, indefinitely**. A.1 already settles this: strictness is free — a sub-threshold insight is never lost, it just stays passive instead of interrupting. |

### Four rules, decided

1. **The offer is a proactive prompt and draws from the brake budget.** It is triggered by an
   adverse pattern and costs the same attention as a brake, so it competes for the same
   scarce slots under A.3 and clears the same gauntlet — materiality, novelty, timing.
   Without this, one nag is simply replaced by a stream of "would you like me to watch this?"
2. **A declined offer returns only on a material change in magnitude × breadth.** Never on a
   clock, and never on repetition of the same condition at the same size. This is F.8's
   existing measure applied to the offer rather than to the projection — no new machinery,
   no new threshold to invent.
3. **The offer is templated, never free-generated.** "I've noticed you get near or past your
   budget" is a statement about the user's behaviour, and a few degrees of drift turns it
   into a scold. This is exactly B.2a's tone-sensitive case: the architecture owns the
   register here, not the model.
4. **It is a third kind of ask, and inherits neither of the other two rules.** The answer
   surface asks for **facts**; F.4 forbids asking for **willingness**. This asks for neither
   — it asks whether the user wants a **capability**. Naming it prevents it being filed under
   either and picking up the wrong constraint: it is not budget-exempt the way a factual
   clarification is, and it is not forbidden the way a willingness interrogation is.

### What this does to the catalogue

It makes it active. Provability already decides what may be offered at all — no retirement
watches for someone holding no retirement. This decides *when* a particular watch is put in
front of someone: when their own record shows the pattern it addresses. Feature discovery
driven by the user's data rather than by a feature list, and honest because the evidence for
the offer is the same evidence the watch would use. The software is not promoting a feature;
it is saying *here is a pattern in your record, and here is the one thing I can do about it.*

---

## Changing things on the user's behalf — SETTLED 2026-09-03

**"Settings" is the wrong noun** and the section is named accordingly. `app_settings` is mostly
the user's own data; the domain this governs is broader and more ordinary — ledger annotations
like transaction categories, budget amounts, detected recurring patterns, debt terms. Anything
the software might change on someone's behalf.

The instinct this starts from is sound: **offers are expensive.** They draw from the brake
budget, so if many things could use adjusting, most offers never fire and most adjustments never
happen. Silent change scales; asking does not.

Right about the cost, wrong about the remedy — and the reason is already in the blueprint. E.2b:
a durable contradicting behaviour *doesn't silently flip the word*, it surfaces a
contradiction-check. A silent settings change is exactly **behaviour contradicts the setting, so
overwrite the setting**, which is that move under another name.

Two harms, and the second is the one that scales:

- **A hidden belief that steers.** To silently raise a grocery budget, the software must first
  conclude *this person's real grocery spend is $452*. That is a derived observation, and acting
  on it unsurfaced is worse than storing it unsurfaced (§10): it is invisible *and* it moves
  things.
- **Broken trust is uncontainable.** A user who discovers the software has been changing things
  without saying so does not conclude *helpful*. They conclude **what else has it changed?** —
  and that question retroactively taints every number in the product, including all the honest
  ones. A convenience-level feature buying an existential-level failure is a bad trade at any
  frequency.

### Silent versus interrupting is a false binary

A.1 already provides the third tier. **Passive** — the insight lives on the relevant screen,
available if the user looks. So a change the software makes on its own can be **made without
asking and still not be silent**: it happens, it is visible where the user will meet it —
*"raised your grocery budget to $452 on Sept 3; here's why"* — and it is revertible. No prompt,
no interruption, **no draw on the brake budget**. The frictionlessness survives and so does the
integrity.

### The rule

> **Unsolicited, the software may adjust only what the user has not set. With a standing
> per-item grant, it may adjust that item. Where provenance is unknown, treat it as set.**

- **The user set it** → never adjusted unsolicited. A durable contradicting behaviour surfaces a
  contradiction-check (E.2b). It is their declaration, and the Declared channel is sovereign
  (F.6a). This routes into the contradiction-check budget, already an open item below rather than
  a new one.
- **A standing per-item grant exists** → adjustable, because the grant is *itself* a Declaration.
  Acting within it honours their word rather than overriding it — the same logic that lets a
  user-set watch bypass the frequency budget. Still passive-surfaced like any other change, and
  revocable. `RecurringDebtPayment.is_auto_confirm` (1.x, reserved, `default=False`) is the
  existing shape and the right granularity: **per item, opt-in** — never a blanket "the assistant
  may manage things."
- **Provenance is unknown** → treat it as set. Absence is not evidence of absence, and the costs
  are asymmetric: wrongly changing something the user chose costs trust; wrongly leaving an
  auto-filled value alone costs almost nothing.

**"Set" is derived, not stored.** No provenance column exists — `Transaction` carries
`category_id` and nothing about who chose it. But the Historian already logs
`categorization_suggestion_confirm` / `_reject`, so the answer lives in **events rather than in a
flag**, which is what §10 requires anyway: derive it, do not remember it. The unknown class is
real — rows predating the Historian, paths that never logged — and is exactly what the third
branch is for.

**The grant is the main path, not a footnote.** `app_settings` holds gift lists, goals, target
allocations, a backup folder: the user's own data, not preferences with defaults. **Genuine
untouched defaults are rare here**, so the friction this rule was meant to relieve is relieved
almost entirely by the grant branch. Which lands back where the instinct began — the assistant
*can* make adjustments, per item, once asked to, and the ask is offerable through the mechanism
already settled: *"want me to keep this one current?"* The gradient still runs the right way:
**the more a user engages, the less the software touches unbidden.**

---

## Open

- **Alarm governance is partly undesigned.** Appendix A covers promotion at runtime, per
  instance. Industrial practice adds two things it still lacks: **rationalization** (each
  alarm *type* justifies its existence at design time — cause, consequence, response,
  priority basis — which is this document's own "Gated" discipline applied to a bucket that
  does not have it), and **measured delivered rate** treated as a design defect when it
  drifts, the way the voice gate's miss-log is used. *(Stale conditions, the third gap, is
  settled above.)*
- **Alarms proper are still an unbudgeted prompt-kind.** A.3 budgets brakes and green-lights.
  The offer-to-watch above is now settled into the brake budget, and the factual clarification
  is exempt because it is solicited — but the contradiction-check remains unpinned (§12) and a
  bare alarm has no budget at all. Two kinds outstanding, not three. The offer-to-watch is the
  precedent for how to resolve them: decide which existing budget the kind's *attention cost*
  most resembles, rather than minting a new cap per kind.
- **Gate 2 versus genuinely path-less news.** A.2 requires an honest §6 solution before a
  brake may interrupt. Some alarming facts have no lever — income stopping. The honest-no
  always carries a nearest lever and nearest reachable goal, so this may resolve itself, but
  "we never deliver bad news with no path" and "the user needs to know this" can collide and
  it should be checked deliberately rather than assumed.
- **Layer 5's stakes gate.** `LEARNING.md` makes stakes decide whether the system may
  recommend at all. Groundwork's honest-no (Appendix C) governs what it may *claim*, not
  whether the stakes permit a recommendation. Whether these are the same rule seen twice
  or two rules that need reconciling is unchecked.
- *(Resolved 2026-09-03 — F.3 is settled and Layer 4's output surfaces in the working picture,
  which lives with the assistant. This document's own placement question is answered by it.)*
