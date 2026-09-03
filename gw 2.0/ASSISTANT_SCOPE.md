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

## Open

- **What "conversation" means here.** Rob's framing was "better financial conversation
  and understanding." Groundwork's speaking surfaces today are narration and prompts,
  both templated and gated. Whether Layer 4 improves *those*, or whether it implies a
  genuinely conversational surface, is undecided — and it changes the size of this
  substantially. Do not assume the smaller reading.
- **Layer 5's stakes gate.** `LEARNING.md` makes stakes decide whether the system may
  recommend at all. Groundwork's honest-no (Appendix C) governs what it may *claim*, not
  whether the stakes permit a recommendation. Whether these are the same rule seen twice
  or two rules that need reconciling is unchecked.
- **Where Layer 4's output is surfaced** is entangled with F.3, which is still the open
  frontier. This document does not resolve F.3 and should not be read as narrowing it.
