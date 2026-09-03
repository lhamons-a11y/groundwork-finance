# Groundwork 2.0 — Build Blueprint

**The Teaching Platform**

> Status: **Information-gathering / vision capture.** Nothing here is scheduled or being built.
> This document is the north star for 2.0, written against the real 1.0 codebase so the ideas
> stay honest about what exists and what's new.
> Created 2026-08-03.

---

## Executive Summary

**What this is.** Groundwork 2.0 turns the app from an honest *recorder* of a person's money into an
honest *teacher* — not a finance tool with a teaching feature, but a teacher that happens to work in
the domain of money. It teaches by showing people their own facts, never by lecturing.

**The one idea everything rests on.** *The app earns the right to teach by showing receipts.* Every
claim is a fact from the user's own logged history — proof, not persuasion. That single principle is
what makes it un-preachy: it never asserts an opinion, it reflects back what's already true.

**What it does (the mechanics).**
- **Consequence engine** — one deterministic core: "if you do X, here's what happens to your whole
  picture" (unifying math that already exists in BYB, the trip planner, and debt projection).
- **Teaching layer** — causal sentences ending in a lever the user controls, not bare stats.
- **Solution engine** — offers only honest levers (reallocation, timing, trimming, substitution,
  save-first, patience). **Never** "make more money," **never** a new loan/credit card, and an
  **honest "no"** is a first-class answer — bounded to current numbers, never "never," always with the
  nearest lever and a reachable smaller goal.
- **Green-light** — the mirror of the brake: "because you did X, you can now afford Z," credited only
  to real, deliberate, user-driven action (never the market, never an unspent raise).
- **Memory / Trophy Room** — verified, evidence-backed recognition; the trophy *is* the receipt.

**How it relates to the user (the Willingness Layer — the spine).** The software teaches strictly
within what the user is willing to change — and *"nothing at all" is a valid answer.* It reads
willingness from **actions, not words** (a stated intention that behavior doesn't follow is simply an
answer), and it shifts as the user shifts. It's a teacher–student covenant: keep teaching for whoever's
willing to learn, never chase the disengaged, and measure success as *having taught truthfully* — not
retention.

**Why it holds (the structural guarantee).** Every virtue is guaranteed by a constraint, not by good
intentions: **freeware** makes honesty structural (nothing to sell but the truth); **demonstrated
willingness** makes projection honest (we don't guess intent); **not knowing "why" a behavior shifted**
makes non-judgment structural (we can't moralize a cause we can't see); **proof** makes non-fabrication
structural (we can't invent a number). We don't ask to be trusted — we remove our ability to be
otherwise.

**On "prediction."** No behavioral/intention prediction, no surveillance. The only predictability is
honest *projection*: deterministic outcomes conditioned on demonstrated behavior, showing the *swing*
(where a small willing change matters most), bounded by an honest horizon, re-derived as behavior
shifts.

**Status.** A vision artifact, not a spec — nothing is built. It is deliberately a philosophy scaffold,
not a full scope. Most design questions are worked through (Appendices A–G); the open surface is sorted
into two kinds (§12): **Open** (no answer exists yet) — free-generated drama-safety (B.2a) —
and **Gated** (standard exists, pin per case before build) — Trophy Room's proof-source and
Appendix G's cycle thresholds. Alarm governance is open too, in `ASSISTANT_SCOPE.md`.

---

## 0. One-sentence thesis

Groundwork 1.0 is an honest **recorder** of a person's financial life. Groundwork 2.0 turns that
record into an honest **teacher** — one that shows you, in your own numbers, *why* your actions
open or close a door, and then offers only the solutions the math actually supports — never
"make more money," never "get another loan," and never a comforting lie.

---

## 1. North Star

A financial program that teaches by consequence, not by lecture:

- **Cause → effect, in the user's own money.** "Because you did X, Z is now possible / no longer
  possible." Not generic advice — *their* numbers.
- **Real solutions the math proves true.** Every suggestion is computed from the user's own budget,
  debt, and history, and can be verified in a sandbox before they act.
- **Honest even when the answer is no.** If the math says a goal isn't reachable, the platform
  says so plainly — and shows the nearest true path, or an honest horizon. A truthful "not yet"
  is more valuable than a motivational fiction.
- **Never preachy, never predatory.** It shows what's true and offers options. It does not scold,
  does not block, and never routes the user into new debt to paper over a shortfall.

---

## 2. The core reframe: recorder → teacher

| | 1.0 (recorder) | 2.0 (teacher) |
|---|---|---|
| What it does with data | describes ("72% on pace", "3-day streak") | explains ("your dining overspend pushed your date out 6 weeks") |
| When it speaks | when the user opens a screen | at the real moment a decision happens (a charge, a budget edit, a detected subscription) |
| Direction | mostly the brake (debt grind, "this costs you") | brake **and** green light ("what your progress just unlocked") |
| Memory | events logged, ~half never read | every logged decision feeds reflection and the next lesson |
| Advice | little; a monthly AI narrative | a solution engine constrained to honest, math-true levers |

The substrate for all of this — the Historian — **already exists.** 2.0 is overwhelmingly a
*consumption* build (turn collected data into teaching), not a *collection* build. See §4.

And "teacher" implies a *relationship*, not a broadcast. The interaction model that relationship runs
on — the user declaring what they're willing to change (or nothing at all), and the software deriving
honest guidance strictly within that — is **the Willingness Layer**, the spine that ties Pillars and
Appendices A–E into one relationship. See **Appendix F** (named, not yet solved).

---

## 3. Non-negotiable principles (guardrails)

These are the rules every 2.0 feature must obey. They are the product's moat.

1. **Math-true or silent.** Inherit 1.0's existing discipline: never fabricate a number; return
   nothing (not a guess) when there isn't real data. A lesson that isn't provable from the user's
   data doesn't ship.
2. **No fictional-income "solutions."** "Just earn more" is banned. It is not a plan; it's a way
   of avoiding one. Every solution must work within the money the user actually has.
3. **No new-debt "solutions."** Never suggest a credit card, personal loan, balance-transfer
   product, BNPL, or any new borrowing to close a gap. The platform optimizes *within existing
   obligations*; it never adds one. (This is the line most finance apps cross to make money — we
   don't monetize the user, so we don't have to.)
4. **The honest no is a first-class answer.** "On today's numbers this isn't possible" is a valid,
   complete output — always paired with the nearest true path or an honest horizon (see §6.4).
5. **Show, don't scold.** Present the causal math and the options; the user decides. Never block a
   purchase, never moralize, never use guilt. "Here's what happened / here's what would change it,"
   never "you shouldn't have."
6. **Meet the moment from real signals, not surveillance.** Trigger teaching from actions the user
   *takes* (a charge, an edit, a confirmed pattern) — never from hesitation-timing, dwell-time
   profiling, or "predict what they'll do before they do it." Deterministic consequence > statistical
   prediction, always. (See §9.)
7. **Local and private.** Everything runs on-device. No teaching feature introduces an outbound
   call. "Your data stays on your machine" stays literally true.
8. **Proof, not persuasion.** The teaching's authority comes from the user's own history, not our
   opinion. Every claim is a fact drawn from their logged data, shown as evidence they can inspect —
   we don't tell them what to think, we show them what's true. This is *the* anti-preachy mechanism:
   receipts, not sermons. It cuts both ways — the same evidence base proves earned progress (the
   Trophy Room, the green-lights), not only costs. See Appendix B.
9. **Freeware is structural, not a price.** Because we sell nothing — no product, subscription, ad, or
   upsell — the only thing we ever have to "sell" is the truth, and no incentive can bend the teaching.
   Freeware is not a marketing choice; it is the structural guarantee that makes the covenant (Appendix
   F.7) honest and every anti-goal (§9) affordable. A user may take the ledger and ignore every lesson
   forever, and we lose nothing — because we never monetized their attention or their compliance. The
   business model *is* the ethics.
10. **The model is the voice; the architecture is the intelligence.** Groundwork targets the
    *smallest* viable local model and makes it feel like the best AI available — not by growing the
    model, but by the information architecture around it. The deterministic engines do the reasoning,
    the Historian supplies verified personal facts, and proof-grounding (Appendix B.2) forbids
    invention — so the model is only ever asked to do the one thing small models do *well*: phrase a
    pre-computed truth clearly. It is structurally prevented from doing what small models do *badly*
    (facts, math, multi-step reasoning). It seems great because it is never allowed to visibly fail.
    Perceived intelligence here comes from being **never wrong** (proof-grounding), **knowing you**
    (the Historian), delivering **pre-computed non-obvious insight** (the "swing", Appendix F.8), and
    being **honest about limits** — none of which needs scale. And this is the *only* AI design that
    stays private, free, and genuinely smart at once: a cloud model breaks privacy, a huge local model
    breaks "runs on a normal machine / free." The small model isn't a compromise — it's the only kind
    that keeps the whole promise. The intelligence lives in the architecture; the model just speaks.

*The pattern across these principles: **every virtue is guaranteed by a structural constraint, not by
good intentions.** Honesty is guaranteed by freeware (#9 — nothing to sell but the truth). Honest
projection is guaranteed by demonstrated willingness (Appendix F.6/F.8 — we don't guess intent).
Non-judgment is guaranteed by not knowing "why" a behavior shifted (Appendix F.8 — we can't moralize a
cause we can't see). Non-fabrication is guaranteed by proof (#8, Appendix B — we can't invent a number).
We do not ask users to trust that we will be good; we remove our ability to be otherwise. That is why
the vision holds under implementation pressure — the guarantees are architectural, not aspirational.*

*Extension guardrail (stated in the calm, on purpose): **coherence with the spine is the bar for a new
capability — not whether it sharpens an existing part.** Improving something that already exists is a
frequent bonus, never the entry fee. The risk grows with success: a clean result — like the
break-detector → E.2a chain, where every addition happened to sharpen something older — is the one most
likely to be mistaken for the **rule** rather than an **instance** of it, after which a genuinely good
idea gets rejected for failing to produce a side effect instead of for breaking a principle. Friction is
information; a clean win removes the signal that it was a choice, and so looks like a law. This is
written before there is any case to apply it to, deliberately — a guardrail authored while a specific
idea is on trial is contaminated by that idea, and can only be used, never neutrally set, thereafter.
The only honest test for admitting a new capability: does it obey the same handful of principles as
everything else? — not, does it make the others more correct?*

---

## 4. Where 1.0 stands (grounded gap analysis)

The Historian writes ~19 event categories. The gap is **not** collection — it's teaching:

- **Consumed today (turned into something the user sees):** payment compliance + payoff confidence;
  the pace/variance "% on pace" badges (net worth, investments, sinking/college/gift funds); the
  check-in streak. All of it only **describes** (a score or a count).
- **Collected and read by nothing:** `budget_adjusted`, `charge_observation`,
  `recurring_pattern_confirm/reject`, `categorization_suggestion_*`, `gift_occasion_variance`,
  `session_end`, and — most tellingly — **`byb_purchase_decision`**, which already logs each
  purchase decision *with its computed payoff impact* and is never read back.
- **No teaching layer anywhere.** No causal explanation, no solution engine, no "capacity unlocked."

**Assets already in the code that 2.0 builds on:**
- A real consequence engine, currently triplicated: `_bybSandboxCalc` (BYB), the trip-impact calc
  (`app.js` ~10751), and `_calcDebtIntelligence` (`app.js:654`). All compute "impact on the
  debt-free date" separately.
- The teaching *sentence* pattern already exists in the trip planner (`app.js` ~10822):
  *"This trip moves your debt-free date from March to Sept — 6 days later. A worthy trade."*
- Honest-null discipline already enforced (e.g. BYB stores `payoff_impact = null` for "not
  affordable" rather than a fabricated negative).

---

## 5. Architecture — the five pillars

**Pillar 1 — Consequence Engine (unify what exists).**
Extract one function, `decisionImpact({ monthlyDelta, oneTimeCost, ... })` →
`{ payoffDaysDelta, dtiBefore/After, whatsLeft, freeDateBefore/After }`. BYB, the trip planner,
and every future trigger call it. This is the deterministic core everything else stands on.

**Pillar 2 — Teaching Layer (causal sentences, not stats).**
A generator that turns a `decisionImpact` result into a plain-English cause→effect line, always
ending in *a lever the user controls*: "…pushes your date from March → Sept; **trim dining $40/mo
and it's only 2 months.**" Reuses the trip planner's proven pattern app-wide.

**Pillar 3 — Solution Engine (the heart — see §6).**
Given a gap ("you want Z, the math currently says no"), search only the honest lever-set for the
combinations that close it, ranked by least disruption — or return the honest no with the nearest
true path.

**Pillar 4 — Capacity / Green-Light.**
The mirror of the brake. Detect positive state changes (a card hit $0 → freed $/mo; a budget cut;
a milestone crossed) from the Historian and translate them into what's *newly reachable*, with
attribution: "You cleared the Visa in April — that freed $180/mo; that now covers Z without moving
your date." This is the "because you changed X, you can now afford Z" the user asked for. Attribution
rules — window, what counts as credit, and the honesty guards — are in **Appendix D**.

**Pillar 5 — Memory & Reflection.**
Finally read the decision log. `get_byb_decision_history` (and siblings) over the Historian →
walkaway rate, cumulative committed $/mo and its payoff cost, estimate-vs-actual bias. Surfaced as
reward for good behavior: "You walked away from 4 of 6 things this quarter — that pulled your date
in ~5 weeks."

### Data flow — how the pieces connect (and why it dissolves nagging)

The pillars aren't parallel features; they're a **pipeline**, flowing one direction — from fact to
voice:

```
HISTORIAN  (facts / receipts)
   │  everything reads from here
   ├──────────────►  CONSEQUENCE ENGINE   (pure math: "if X then Y" — willingness-independent)
   │
   ▼
WILLINGNESS LAYER   (derives "what will this user change," from actions — Appendix F)
   │  a background, always-updating lens
   ▼
SOLUTION ENGINE · GREEN-LIGHT · HONEST-NO   (constrained & ranked by willingness)
   │
   ▼
TEACHING LAYER   (composes the lesson: causal sentence + the lever)
   │
   ▼
LLM   (voices it in natural language — grounded strictly in the proof above)
   │
   ▼
USER
```

Three things this picture makes precise:
1. **Willingness is derived, not a source.** It reads the Historian (primarily actions, F.6) and
   continuously derives a state; it sits *between* the facts and the decision engines — a lens, not a
   well of data.
2. **It feeds the engines as a constraint, not a data feed.** Truth is willingness-independent (the
   consequence math holds regardless of what the user will do); willingness shapes which *solutions*
   are offered and how they're ranked, bounds the *honest-no*, and gates the *proactive* prompts.
3. **The LLM is the voice, not the brain.** The deterministic engines decide; the LLM only narrates
   what's already computed and proven (Appendix B.2). Deterministic brain, proof-grounded voice — a
   deliberate inversion of LLM-first apps, and the reason the teaching cannot novelize.

**Why this dissolves the nagging problem.** The Willingness Layer was meant to answer two hard
questions: *how do we avoid nagging?* and *what do we suggest?* The answer isn't a clever heuristic —
it's **stop asking, watch, learn, respect:**
- The user who always protects groceries but cuts dining never has to *tell* us. After a few budget
  edits the engine knows it (Appendix E), and every suggestion respects it.
- The user who walked away from four impulse buys but couldn't resist subscriptions — same thing,
  learned from the Historian's `byb_purchase_decision` and `recurring_pattern` events.

So the LLM never guesses "should I suggest cutting this category?" It reads the Willingness Layer's
output — *sacred = [groceries, kids], flexible = [dining, subs]* — and narrates within it. That is the
bridge: **Historian → Willingness Layer → every other engine → LLM → the user sees teaching that feels
like it knows them, because it does** — not from profiling them, but from watching what they did and
respecting it.

---

## 6. The Solution Engine, in depth

This is the piece that makes 2.0 different, and the piece with the strictest rules. When the user
faces a gap — a purchase they can't fit, a goal that's out of reach — the engine may only offer
solutions drawn from this honest lever-set, each **computed from the user's own numbers** and
**verifiable in the sandbox**:

### 6.1 The legitimate levers

1. **Reallocation** — move money between existing categories. "Shift $60/mo from dining to the car
   fund and Z is reachable in 4 months." (No new income, no new debt.)
2. **Timing / sequencing** — the delayed green light. "Not now. But the Visa clears in April, which
   frees $180/mo — then Z fits without moving your date." Waiting is a real, math-true solution.
3. **Payoff-order optimization** — targeting the highest-APR balance (avalanche) frees capacity
   faster than the user's current order; quantify the difference. Optimizes *existing* debt only.
4. **Specific-cost trimming** — name the actual recurring items whose removal changes the verdict,
   with dollar amounts. "Cutting these two subscriptions ($43/mo) makes Z reachable in 3 months
   instead of never." (Uses `recurring_pattern` + ledger data already present.)
5. **Substitution** — a cheaper alternative that nets out. BYB's existing "replacing" mechanic,
   generalized. "A $220/mo car instead of $350/mo keeps your date where it is."
6. **Save-first (the anti-loan)** — instead of financing, a sinking-fund plan. "Save $X/mo for 4
   months and buy it in cash — $0 interest, vs. ~$Y in interest if financed." This is the direct,
   principled alternative to the "get a loan" advice we refuse to give. (Surfaces on the existing
   sinking/college/gift-fund infrastructure.)
7. **Do-nothing, quantified** — sometimes the honest lesson is that the current path is already
   optimal and patience is the plan: "You're on track; Z arrives on its own in 6 months if nothing
   changes."

### 6.2 What a solution must satisfy

- Computed from the user's real data (never a template).
- Requires **no** new income and **no** new debt.
- Reversible/inspectable in the sandbox before commit.
- Ranked by *least disruption to the user's life*, not by what's mathematically tidiest — where
  "least disruption" is defined by the user's own values, not ours (**Appendix E**).
- May **incorporate free, government-backed consumer/credit protection** (e.g. the U.S. Consumer
  Financial Protection Bureau, CFPB) as a **sanctioned referral** — never a paid product. This is the
  honest alternative to a loan in genuinely dire cases: when the math says "not reachable *sustainably*"
  (Appendix C.5), the right move is a free protective resource, **never** new debt. Conditions: (1) it
  must be genuinely free and government-backed — never a gateway to a paid service; (2) we *refer* the
  user to the authoritative source — never impersonating, overstating its endorsement, or fabricating
  its guidance; (3) it is a pointer, not data exfiltration — consistent with the local/private posture
  (§10).

### 6.3 What is banned as a "solution"

- "Earn/make more money," "get a side hustle," "ask for a raise" (fictional-income non-advice).
- Any new credit product, loan, balance transfer, or BNPL.
- Motivational filler with no math behind it.

**Clarification — trajectory ≠ "make more money."** The income ban applies to *present, solvable
gaps*, where pointing at income dodges a problem the levers can actually fix. It does **not** mean we
pretend income doesn't exist. For a genuine *beyond-horizon aspiration* (Appendix C.6), the honest
math genuinely tracks with income over years — and we may **show** that relationship as proof ("at
~$X/yr this becomes a 6-year goal, not 12"), never **prescribe** it as advice ("go get a raise").
Proof of the relationship is empowering and allowed; "just earn more" as a directive is a dodge and
banned. The user sees the math and draws their own conclusion.

### 6.4 The honest no (first-class output)

When no combination of honest levers closes the gap, the engine does **not** say a bare "you can't."
It returns the truth plus the nearest real path:

- **Nearest true path:** "The smallest change that makes Z possible is trimming $95/mo somewhere —
  here's where that could come from — and Z would then be reachable in 5 months."
- **Honest horizon:** "On today's numbers, Z isn't reachable within 24 months without going
  backward. That's real information — here's what would have to change for that to move."
- **Never:** an invented number, a loan, or "just make more."

A truthful no, with a map, is the single most trust-building thing this platform can do. Full horizon
rules — degrading precision, the credibility ceiling, the "never say never" stance, the nearest
reachable adjacent goal, and the stability floor — are specified in **Appendix C**.

---

## 7. First proving ground — BYB, perfected

BYB is the natural first surface: it already has the consequence math, the honest-null discipline,
and the decision log. Perfected BYB = a two-sided decision coach:

- **Unify** its calc into Pillar 1.
- **Teach a sentence** (Pillar 2) instead of stat chips.
- **Add the green light** (Pillar 4): "you freed $180/mo, this fits."
- **Add memory** (Pillar 5): read `byb_purchase_decision`, show walkaway discipline + estimate bias.
- **Add honest solutions** (Pillar 3): when a purchase doesn't fit, offer the §6 levers — including
  save-first — and the honest no.
- **Meet the moment** (later): trigger from `recurring_pattern_confirm`, `budget_adjusted`, and
  large `charge_observation` events — **gentle-proactive** (speaks up on its own, per §12),
  dismissable, frequency-capped, never blocking.

Suggested tracer-bullet order (when building eventually): Pillar 5 reader first (cheap, closes the
collect-and-ignore loop), then Pillar 4 green light (the emotional differentiator), then Pillar 3.

---

## 8. Whole-program expansion (every surface becomes teaching)

| Surface | Today | Teaching form (2.0) |
|---|---|---|
| Budget | edit amounts | "this category's overspend costs ~6 weeks; here's the reallocation that fixes it" |
| Debt Payoff | payoff date + confidence | name the single lever that moves the date most; payoff-order optimization |
| Ledger | records charges | a large charge → retrospective, past-tense lesson + §6 options |
| BYB | manual downside calc | the two-sided coach (Pillar surface, §7) |
| Sinking / College / Gift funds | savings target + a pace-confidence % (readers exist) | causal pace narration — on-track/behind + the lever that changes the finish date (same logic as Budget/Debt/Net Worth). A chosen *save-first* plan (§6.1) lands here — that's where the money sits, not where the teaching is |
| Net Worth | number goes up | capacity-unlocked: "you crossed $X — here's what that enables" |
| Reports / AI monthly | retrospective narrative | the causal teaching layer, made explicit, lever-oriented, and **proof-cited** (Appendix B) |
| Trophy Room | achievements | **evidence-backed**: verified proof the user did it ("paid off $4,200 across 3 cards — here's the timeline"). The trophy *is* the receipt (Appendix B.3). *Proof-source per trophy type is gated — §12; must meet D.4/E.2a durability before build.* |
| Trip Planner | already teaches ("worthy trade") | the template every other surface adopts |

---

## 9. What we will explicitly NOT do (anti-goals)

- **No behavioral-prediction / intention-modeling** ("know what the user will do before they do").
  Single-user data can't support it honestly, and its natural use is manipulation. We do
  deterministic consequence, triggered by real actions. (The legitimate, bounded form — deterministic
  *projection* from *demonstrated* willingness, and its "swing"/leverage — is Appendix F.8. It is not
  behavioral prediction and does not reopen this door.)
- **No hesitation/dwell-time surveillance.** (This was considered and rejected — it collects the
  user's psychology, conflicts with "user isn't the product," and buys nothing the honest approach
  doesn't.)
- **No engagement optimization.** We are not trying to maximize time-in-app. A user who checks in
  briefly and leaves confident is a success, not a churn risk. And we **never chase the disengaged** —
  investment tracks the student's willingness (effort-matched teaching), the exact inverse of retention
  mechanics (Appendix F.7).
- **No monetizing the user** — which is exactly why we can afford principles #2 and #3 above.
- **No silent data-collection expansions** framed as "no user-facing changes." New data, if any,
  ships with disclosure and a control.
- **No derived observations kept out of sight.** Detection is allowed; silent accumulation is not. A
  strategy label or confidence score the user cannot see may be computed and used inside the pass that
  computed it, never stored (§10). This is the retention counterpart to the two bans above: they
  forbid inferring the user's psychology, this forbids quietly keeping what was inferred.

---

## 10. Data & privacy posture

- 2.0 is a **consumption** build. Preference: build the teacher against data already collected; let
  the teacher reveal what (if any) new data it genuinely needs, then add that deliberately and
  disclosed.
- Everything on-device. No teaching feature adds an outbound call.
- The Historian's honest-null discipline is the model for the whole platform: no history → no
  claim.
- **Derived state may be cached, never remembered.** The Assistant's persistence boundary
  (`RETENTION.md`, decided 2026-08-17) governs here too: *if an observation is not surfaced to the
  person, it cannot become persistent memory* — detection is allowed, silent accumulation is not. A
  willingness strategy, its score, a break's magnitude, a confidence level: each is a claim about the
  user that the user cannot see, and none may be kept as one. **Groundwork can hold this more strictly
  than the Assistant can.** The Assistant discards its raw material, so what it wants to remember it
  must derive — and derivation is the forbidden thing. Our raw material *is the product*: the ledger
  persists, the user sees all of it, and every derivation can be redone. The boundary costs us
  compute, not capability.
  - **The test is deletion.** Wipe every derived table and re-run. Identical output means the rule
    holds; any difference names exactly what was being remembered.
  - **What persists:** the ledger (they handed it over and can see it) and their declarations (they
    made them, and they are surfaced by definition, F.3). Nothing else — not the strategy label, not
    its held-out score, not a break's magnitude or breadth, not a confidence level.

---

## 11. Phasing (rough, non-committal — for shape, not schedule)

1. **Foundation:** unify the consequence engine (Pillar 1); build the Pillar 5 reader for BYB
   (closes the biggest collect-and-ignore gap).
2. **The differentiator:** capacity / green-light (Pillar 4) on BYB + net worth.
3. **The heart:** solution engine (Pillar 3) — levers first, honest-no second — on BYB and budget.
4. **The teaching voice:** causal-sentence layer (Pillar 2) rolled across surfaces per §8. **Nothing in
   §12's Gated bucket (Trophy Room, debt-cycle recurrence, …) enters this rollout until its per-case
   standard is pinned** — otherwise "evidence-backed" / "resolved" degrades to "declared-backed" under
   deadline pressure (the D.4 failure).
5. **Meet the moment:** gentle-proactive (per §12), dismissable, frequency-capped triggers from
   existing server-side events, plus the user control to dial them down.
6. Documentation + honest-solution copy review at each step.

---

## 12. Decisions & open questions

### Decided

- **Default posture of triggered teaching: GENTLE PROACTIVE.** (Decided 2026-08-03.) The platform
  speaks up on its own — it doesn't wait to be asked. Rationale: proactive guidance is what proves
  Groundwork is a *teacher*, not a dumb ledger or a marketing ploy; users who feel genuinely guided
  come to trust the software. Not everyone will want it ("some, not all, will appreciate it") — so
  gentle-proactive is paired with a **user control to dial it down or off** and every prompt is
  **dismissable**. This decision *raises* the stakes on the nagging-threshold question below: proactive
  only works if the frequency cap and tone are right, or it becomes the exact failure mode we fear.

- **Nagging threshold / "meet the moment" governance: DECIDED — see Appendix A.** (Decided
  2026-08-03.) Modeled as a two-tier system (passive vs. proactive) where a candidate insight must
  pass a five-gate gauntlet to be *promoted* to proactive, under frequency caps with decay and
  adaptive backoff. Specific thresholds are tunable starting defaults.
- **Honest-no horizon: DECIDED — see Appendix C.** (Decided 2026-08-03.) The horizon is a
  *projection-credibility ceiling* (~24 months stated, ~36 coarse, no date beyond), precision degrades
  with distance, we **never** say a bare "never" (always bounded to current numbers), and every
  honest-no carries the nearest lever + nearest reachable adjacent goal, subject to a stability floor
  (no inhumane paths). Thresholds tunable.
- **Green-light attribution window: DECIDED — see Appendix D.** (Decided 2026-08-03.) Not a calendar
  window — a delta anchored to the state transition (the span between the last "no" and this "yes").
  Credit only proven, user-driven, deliberate-above-baseline action; never the market or a windfall;
  decompose multi-cause honestly; recency governs framing, not truth. Fresh-credit recency ~12 months,
  tunable.

- **Solution-engine "least disruption" ranking: DECIDED — see Appendix E.** (Decided 2026-08-03.)
  "Least disruption" is the user's to define, not ours. One universal layer only — a necessity floor
  (stability, not virtue). Above it, sacred-vs-flexible is learned from the user's proven behavior
  (`budget_adjusted` + category ledger) and always overridden by their explicit word. The engine
  ranks and shows the tradeoff; the user chooses (and the choice is how it learns). When a category's
  status is unknown, ask — never assume disposable.

- **Sibling detectors' shared propagation (F.8 × G): DECIDED.** A confirmed G cycle-recurrence feeds
  F.8's existing propagation on F.8's own terms — no exception, nothing G-specific. Widens
  willingness-model confidence proportional to magnitude × breadth (breadth high because debt is
  load-bearing; magnitude scales with recurrence depth) and decays via subsequent proof like any break
  — **no permanent floor, no standing penalty** (C.3, non-judgment). The propagation was never
  break-coupled; it keys on magnitude × breadth, which is detector-agnostic, so G is simply an input
  (see F.8's propagation bullet). Earlier "factor out a shared mechanism" was an over-correction —
  G.2 already separates the *detectors* (a cycle is a boundary-crossing, not a shape *discontinuity*,
  so it needs its own detector), but a cycle is still a *break* that feeds the same propagation; it
  needed only the one-clause generalization, not new machinery.

### Open

Two kinds — and the *kind* is the routing instruction. **Open** = no answer exists yet → *design one;
don't build until it does*. **Gated** = the standard already exists; it needs pinning per case → *apply
it, then ship*. Nothing in the **Gated** bucket enters the build queue (§11) until its per-case standard
is pinned; until then, any "evidence-backed" / "resolved" language it carries is aspirational.
- **Where the Willingness Layer lives (Appendix F.3): DECIDED 2026-09-03.** The **working picture**
  — renamed from "current agreement", which oversold what the evidence supports — **lives with the
  assistant**, as the assistant's record of its own conduct: what it concluded, what it did, why,
  and what the user may dispute. Same home as the answer surface but a *distinct view*, since a Q&A
  transcript is no place for durable state. **Settings gets a pointer, never residence** — location
  teaches interpretation. Nothing is editable that isn't first a claim with a receipt; the empty
  state is a cold-start property and is designed first; and the placement carries a stated
  dependency — it assumes the assistant is a first-class destination, so demoting it later is a
  decision about the Willingness Layer, not just navigation.
- **Clarification prompt-kind's budget (A.3, E.2b): DECIDED 2026-09-03.** A promoted
  contradiction-check **draws from the brake budget** — no cap of its own — because its attention
  cost is a brake's: an unsolicited interruption asking the user to resolve something is mild
  pressure, and the green-light budget exists precisely because good news isn't. Generalized as a
  standing rule: *a new prompt-kind joins the budget its attention cost resembles; it does not mint
  its own.* Ranking against other candidates was already covered — A.3's perishability tie-break
  explicitly handles "a position fact that doesn't reduce to a date-impact," which is exactly a
  contradiction-check's weight-of-contradiction unit, so most of this item turned out to be Gated
  rather than Open. **One new clause was needed:** *dependency before impact* — a contradiction-check
  outranks candidates whose ranking depends on the contradicted declaration, because the
  contradiction is upstream and firing them first spends a slot on possibly-wrong advice. Not a
  hierarchy by kind (A.3 forbids those); an ordering by dependency, and checkable.


**Open — no answer exists yet:**
- **Free-generated drama-safety (B.2a, §3 #10).** Confidence and urgency inflation are gate-checkable
  (against computed confidence / a real closing window); drama isn't a factual check. B.2a enforces it
  by *templating* tone-sensitive output — the architecture owns the register. The residual: if a surface
  genuinely needs *free-generated* narrative and still must be drama-safe, the detector is unsolved (a
  banned-pattern list is too crude; a judge model is another small model with the same reliability
  problem). The architecture leans toward *avoiding* free-generated tone where it matters (template
  instead); whether that's fully sufficient is the open question. No existing standard settles it.

**Gated — the standard exists; pin it per case before build:**
- **Trophy Room proof-source / timing (B.3, §8).** For each trophy type, define the proof event and
  whether it fires on the triggering action (only when instantly provable, e.g. a card hitting $0) or
  only after the change proves durable (e.g. a budget cut that sticks), per **D.4/E.2a**.
- **Debt-cycle recurrence thresholds (Appendix G).** Pin the strict cycle boundary (G.3, biased to
  false-negatives — what unarguably counts as a completed cycle), the **approaching-checkpoint
  proximity** (G.3a — how near the prior peak makes the static-distance statement available), and the
  insufficient-history handling (C.7): how "no prior cycle visible" routes through the honest-no rather
  than a fabricated peak.

---

## Appendix A — Proactive Teaching Governance (the nagging threshold)

Gentle-proactive only earns trust if it never becomes nagging. For a debt app serving financially
stressed people, over-prompting is fatal. This is the governance model.

### A.1 Two tiers — the threshold is a promotion bar, not a filter

- **Passive:** the insight always lives on the relevant screen (the budget card shows the overspend
  cost; BYB shows the impact). Available if the user looks.
- **Proactive:** the insight comes to the user unprompted.

The nagging threshold governs **promotion from passive → proactive.** Key consequence: **strictness
is free** — a sub-threshold insight is never lost, it just stays passive instead of interrupting. So
we can set a high bar for interrupting without hiding value.

### A.2 The gauntlet — a candidate must pass ALL five to go proactive

1. **Materiality** — impact ≥ ~2 weeks on the debt-free date, OR ≥ ~5% of monthly budget, OR it
   crosses a goal/milestone boundary. Relative to the user's scale, not absolute. (Kills most
   nagging on its own.)
2. **Actionability** — for a *brake*, an honest §6 solution must exist; we never proactively deliver
   bad news with no path. (Green-light/positive always passes this gate.)
3. **Novelty** — not already shown for this lesson/category within its cooldown; never a re-run of
   something the user dismissed.
4. **Budget** — under the frequency cap (A.3).
5. **Timing** — fires at a natural boundary (after a charge saves, next dashboard load); never
   mid-task, never a blocking modal.

### A.3 Frequency caps (starting defaults — tunable)

- ≤ **1 proactive prompt per session**.
- **Brake/warning: ≤ 2 per rolling 7 days.**
- **Green-light/positive: separate looser budget, ~1–2/week.** Deliberate asymmetry — nagging is
  *unwanted pressure*; good news isn't pressure. Capped so it doesn't become empty cheerleading.
- **Clarifications (contradiction-checks, E.2b) draw from the brake budget — no separate cap.** A
  promoted contradiction-check is an unsolicited interruption asking the user to resolve something.
  That is mild pressure, so it costs what a brake costs; the green-light budget exists precisely
  because good news *isn't* pressure. A cap of its own would also sit idle most weeks, since E.2b
  makes these Passive by default and promotion needs an explicit declaration, durable contradicting
  behaviour, *and* enough weight to clear the gauntlet. The rule generalizes: **a new prompt-kind
  joins the budget its attention cost resembles; it does not mint its own.**
- **Quiet days → silence.** Saying nothing is correct behavior, not a gap to fill. Proactive is
  event-driven; a week with no material events is a silent week.
- **Contention (which candidate takes a scarce slot).** When more candidates clear the gauntlet than
  the budget allows, resolve by **impact on the user's own active goal** — the debt-free date, or
  whatever goal they're currently working toward — in dollars/time relative to their scale. The
  candidate that most moves or threatens *the user's objective* takes the slot.
  - **Never by insight source or appendix.** A fixed "this kind outranks that kind" hierarchy is the
    system imposing a universal importance ranking — the E.1/E.2 error (what most needs saying to
    *this* user isn't ours to pre-decide). The ruler is the user's goal, not our ordering of appendices.
  - **Dependency before impact.** A promoted contradiction-check outranks any candidate whose
    ranking **depends on the contradicted declaration**; against candidates that do not depend on
    it, it competes normally. This is not the hierarchy-by-kind forbidden above — it is an ordering
    by dependency, and it is checkable: *does this candidate's ranking use the category under
    dispute?* The justification is that the contradiction sits **upstream**. If dining is marked
    protected and the user has been trimming it, every solution ranked on that protection may be
    ranked wrongly, so firing one first spends a scarce slot on possibly-wrong advice. Resolving
    the contradiction is what makes the other candidates *correct*. **New clause (2026-09-03) —
    the only part of the clarification-budget question not settled by an existing standard.**
  - **Tie-break 1 — perishability.** When goal-impact is comparable, or a candidate is a position fact
    that doesn't reduce to a date-impact (e.g. G's "approaching your prior peak", or a
    contradiction-check, which carries weight-of-contradiction rather than dollars), surface the one that
    *loses the most by waiting*: a decision the user is about to make outranks a fact that's equally
    true next week. Perishability is judged from what is *already true* — a decision in progress, a
    window closing by a known amount — never from a predicted trajectory (distance-not-direction, F.8).
  - **Tie-break 2 — defer, don't double-spend.** If still even, hold the extra rather than fire two.
    The silence-over-noise bias governs contention too: one clear thing now, the other next cycle.

### A.4 Decay & adaptive backoff (the honest use of engagement data)

- Dismiss a lesson → **60-day cooldown** (or until the underlying number materially changes).
- Same category dismissed **twice** → auto-drop to passive-only. The user told us; we listen.
- Track dismiss-vs-engage globally; **sustained dismissals auto-lower the whole cadence a tier.**
  This is the *only* sanctioned use of engagement data — to respect a demonstrated preference, never
  to predict or manipulate (see §9). Pairs with the manual user dial (§12): dial = explicit control,
  backoff = implicit learning.

### A.5 Guardrail cross-check

This model must remain consistent with §3: show-don't-scold (#5), real-signal not surveillance (#6),
and local-only (#7). The engagement-data use in A.4 is bounded strictly to preference-respect.

---

## Appendix B — Proof, Not Persuasion (the evidence engine)

The mechanism that makes teaching land without preaching: we never assert an opinion, we show the
user a fact from their own history. "You spend $X/mo on dining on average" isn't advice — it's a
receipt, computed over as far back as they've used Groundwork. The facts do the teaching.

### B.1 The Historian is a proof ledger
Reframe: the Historian isn't only a feature substrate — it's the **evidence base**. Every number the
app shows can be traced to the logged events behind it and drilled into. "Show your work" for every
claim. This is 1.0's "never fabricate a number" discipline taken one step further: we don't invent
numbers, *and* we can prove every one.

### B.2 Proof-grounded LLM narrative

> **The LLM is not the source of truth. It is the interpreter of truth.**

That one line is the whole AI posture. Three things fall straight out of it: (1) **swap the interpreter,
the truth doesn't change** — upgrade the model and not one fact moves, only the phrasing; the source of
truth outlives every model. (2) **The interpreter never gets the last word** — any "is this right?"
resolves to the source (the ledger + engines), never the model. (3) **Its only possible failure is
cosmetic** — an interpreter can mis-*phrase*, never mis-*fact*, because facts aren't its to originate.
This is also the quiet answer to "should AI be near my money?": demoted from source to interpreter, the
model gives you AI's clarity with none of its danger.

The AI narrative expands from a summary into **cited teaching** — each sentence backed by, and
drill-downable to, the historian facts behind it. This also hardens an existing weakness: the code
already guards against the LLM "novelizing" unreconciled facts (see the reconciliation logic in
`_calcDebtIntelligence` and the voice gate / `voice_miss_log`). Proof-grounding is the structural
fix — if every claim must cite real logged history, the model can only narrate what's provable; it
cannot invent. Expanding the LLM's sentences and grounding them in proof are the same move.

### B.2a Proof-grounds the *tone*, not just the content
B.2 stops the LLM from inventing facts. But **tone is the unguarded back door for persuasion**, and §3
#8 ("proof, not persuasion") has to hold on the tone channel too or it doesn't hold at all — a sentence
can be fully proof-grounded in *content* and still persuade through word choice alone. This adds no new
principle; it applies three disciplines the doc already has to a channel they hadn't reached:
- **Confidence inflation** — a base-rate voiced as a certainty ("you'll *definitely* exceed this"). The
  sentence carries no more confidence than the proof supports (F.8's distance-not-direction; C.2's
  degrading precision, applied to language). An uncertain projection is voiced as uncertain.
- **Drama / affect inflation** — loaded words around a true number ("*bleeding* money," "*crisis*").
  The register matches the fact's actual weight; the fact carries its own weight and needs no
  amplification (G.4's "visibility, not volume"; B.4's "clean facts" widened from the shame axis to
  *all* affect).
- **Urgency inflation** — time-pressure the data doesn't contain ("act *now*, before it's too late").
  Urgency must be a real present fact — a window closing by a known amount (A.3 perishability) — never
  an invented push.

One line: **the interpreter inherits the proof's confidence, weight, and urgency, and adds none.**
Proof-grounding that stops at content and leaves tone free isn't proof-grounding — it's a true fact
delivered *as persuasion*. The B.2 epigraph is the test: an interpreter renders faithfully, tone
included; the moment it editorializes through affect, it has quietly become a *source* again.

**Enforcement — a rule isn't enforcement.** The three axes split by how enforceable they are, and each
is handled the way the rest of the architecture handles the small model (§3 #10): verify what's
verifiable, constrain by design what isn't, and never invent a checker for the unverifiable case just to
feel covered. *Confidence* and *urgency* are **gate-checkable** — confidence against the proof's
*computed* confidence (a base-rate voiced as "definitely" is flaggable), urgency against whether a real
window is actually closing (perishability) — so both extend the existing voice gate (`voice_miss_log`,
B.2): same machinery, new checks. *Drama* is **not** a factual check ("bleeding money" is inflated
register, not a wrong fact), and there is no clean verifier — a banned-word list is crude and gamed, a
judge model is another small model with the same reliability problem (the turtles-all-the-way-down
trap). So drama is enforced by **templating** the tone-sensitive surfaces: the model fills facts into a
register-controlled template (the trip-planner "worthy trade" pattern), so the *architecture* owns the
register, not the model's discretion. The less verifiable the tone, the more you template — you never
trust a small model with a degree of freedom you can't check. *(Open residual — §12: drama-safety for
genuinely free-generated narrative, which the architecture leans toward *avoiding* — template it —
rather than solving.)*

### B.3 Evidence-backed Trophy Room
Because we hold valid proof the user actually did these things, the Trophy Room stops being generic
gamification and becomes **earned recognition**: "You paid off $4,200 across three cards — here's the
verified timeline." The trophy *is* the proof. Impossible to fake; built from logged history;
on-brand with progress-not-perfection and honesty.

### B.4 The stance on risk (and the one refinement)
**Conviction: we will not soften the truth to retain a user.** If seeing their real history drives
someone away, that is their sovereign choice and an acceptable cost — the reward for those who stay
(real change, real trust) is worth it.

Refinement, so the risk is taken cleanly: separate the **truth** from the **tone**. Accept fully the
risk that the truth is too hard for some — but present proof as neutral, empowering evidence ("here's
what's true, here's what you can do"), never as an indictment that shames ("look what you wasted").
Shame makes people leave *and* fail; clean facts make some leave and the rest change. And remember:
proof mostly **validates** — most of the evidence base is earned progress (B.3, the green-lights),
not a hard mirror. So this is less "scary honesty" than "mostly earned pride, honestly kept."

### B.5 Consistency
This is the concrete engine behind §3 principle #8 and guardrail #5 (show-don't-scold). It's the same
evidence base the Solution Engine (§6), the green-light (Pillar 4), and Memory/Reflection (Pillar 5)
already draw on — unified under one idea: **the app earns the right to teach by showing receipts.**

---

## Appendix C — The Honest-No Horizon

When the Solution Engine (§6) can't close a gap with honest levers, how far ahead do we search before
saying "not reachable," and do we ever say a flat "never"?

### C.1 The horizon is honesty, not search cost
The real question isn't "how long until we give up searching" — it's **"how far can we see before a
stated date becomes a lie."** A single household's finances aren't honestly projectable years out;
too many unknowns. So the horizon is a **projection-credibility ceiling** — "proof, not persuasion"
(Appendix B) applied to time. We only state what we can stand behind.

### C.2 Degrading precision & the ceiling (defaults — tunable)
We search forward to the ceiling; precision degrades with distance, because faking precision we don't
have is itself fabrication:

| Distance | Answer granularity |
|---|---|
| 0–3 months | specific ("by October") |
| 3–12 months | season ("around next spring") |
| 12–24 months | coarse ("roughly 18 months out") |
| 24–~36 months | band only ("a 2–3 year goal at this pace") |
| beyond ceiling | no date ("further out than we can honestly project") |

Stated-date ceiling ≈ **24 months**; coarse band ≈ **36 months**; no specific date beyond.

### C.3 We never say a bare "never"
"You'll never afford this" is dishonest (we can't see the future) and harmful. The strongest honest
statement is **bounded to current numbers and the horizon**: "On today's numbers, this isn't reachable
within [horizon]." A fact about the present trajectory, not a prophecy about the person's life — it
leaves the door the truth actually leaves open, without inventing a path.

### C.4 Every honest-no carries a way forward (no dead ends, no false hope)
Never just "no." When true, it includes:
1. **Nearest lever** — "the smallest change that makes it possible is [X]; then it's reachable in [Y]."
2. **Nearest reachable adjacent goal** — "the full $30k car isn't reachable in 24 months, but a $12k
   used one is, by [date]." Not "no" — "not *that*, but here's what IS true and reachable."

Neither is fabricated: if there's no honest lever and no adjacent goal, we say exactly that.

### C.5 The stability floor (a no beats an inhumane yes)
A path that *technically* closes the gap by breaking the user's stability — draining the emergency
fund, cutting essentials/groceries/kids below a livable floor — is **not** offered as a solution. If
the only math-path is destructive, the honest answer is "not reachable *sustainably*," never a yes
that sets them up to fail. (Ties to the still-open "least disruption" ranking question and guardrail
#5.)

### C.6 Beyond the ceiling: aspirational goals
Some goals genuinely sit past the credibility ceiling — a 22-year-old making $18/hr who wants an
$80k sports car. "Further out than we can project" (C.2) is honest but, alone, cold, and it risks
reading as the "never" C.3 forbids. Here the honest-no switches from **"when"** (which we can't answer
truthfully) to **"what would have to be true"**:

- We do **not** invent a date, and we do **not** say "never." At $18/hr, an $80k car is not reachable
  on the current trajectory within any horizon we can honestly see — a fact about the *trajectory*,
  not the person's future.
- We pivot to **trajectory as proof** (Appendix B; and §6.3 clarification): show the relationship
  without prescribing it. "A goal this size tracks with income over years, not this month's budget.
  Honest math: at ~$X/yr it's roughly an [N]-year goal; at ~$Y/yr, [M] years." Proof, not "go earn
  more" advice.
- We keep the dream alive **and** give something real now via the nearest reachable adjacent goal
  (C.4): "the new $80k car is a long-term life goal; a $12–15k fun used car is reachable in ~3 years."

Net: the young person hears *"a long-term goal with a visible path and a real stepping-stone,"* never
*"you can't have this."* Reframing an impossible fantasy into a trajectory goal is the teaching.

### C.7 Insufficient evidence triggers the honest-no too — it is *not* a special "no data" state
Two conditions produce a "we can't give you a confident yes," and they share one path: **the math
doesn't reach** (we have the data; the honest computation says not within the horizon), and
**insufficient evidence** (not enough history to compute a confident answer at all). The second is
**not a new category and not a separate "No data yet" UI state** — route it through the same honest-no.
The *only* thing that differs is the nearest way forward (C.4): instead of a financial lever, it's the
thing that would let the answer exist — a bit more history, or "verify your balances." Everything else
is identical: a bounded, honest statement ("I don't have enough history yet to answer that
confidently"), never a fabricated placeholder (no fake `$0`, no invented projection — this is the
honest-null discipline of Appendix B), and never a dead-end blank. **Warning to a future builder:** if
you treat "no data" as its own empty/error screen, you will re-invent a path that quietly breaks
proof-not-persuasion or the never-a-dead-end rule. The honest-no is the single funnel for *every* "not
a confident yes," whatever its cause.

---

## Appendix D — Green-Light Attribution

When Groundwork says "because you did X, you can now afford Z" (Pillar 4), how far back does "X" reach,
and what counts as X?

### D.1 It's a delta anchored to a transition, not a calendar window
The open question framed this as "this month / this quarter / since baseline." All three are the wrong
model. Capacity is a **state**; a green-light fires when that state crosses from "Z not reachable" to
"Z reachable." So the attribution window is **the span between the last "no" and this "yes"** — we
credit what actually changed since the goal was last out of reach, whenever that was.
- **Primary window:** since the last honest-no for this specific goal (event-anchored; Appendix C).
- **Fallback (no prior no logged):** since the goal/baseline was set, with a ~12-month recency bound
  for *fresh-credit* framing (D.5).

### D.2 The green-light is the honest-no's receipt
This closes the loop: the honest-no (Appendix C) said "not yet — here's the lever." The green-light is
the moment the lever got pulled and the no became a yes. Same proof, opposite sign; the window is
literally the distance between them. It's the same evidence that powers the Trophy Room (B.3) — the
green-light is the live moment, the trophy is that moment made permanent.

### D.3 Proven and user-driven only — never credit the market
Attribute only to specific logged events (a `payment_confirmed` that zeroed a card, a `budget_adjusted`
cut). **Exogenous factors are acknowledged separately, never credited to the user:** a market gain, a
one-time windfall, or an inheritance is not "because you did X." "You freed $180/mo by clearing the
Visa" is credit; "your investments rose $2k" (the market) is not. Crediting a windfall as discipline is
a lie (Appendix B).

### D.4 Credit deliberate action above baseline, not the baseline itself
Paying the minimum is not a green-light — it's the expected floor. Credit **deliberate action above
baseline**: an extra payment, a real cut, a walkaway. Praising someone for merely not defaulting is
hollow and erodes trust (the empty-cheerleading failure mode, Appendix A.3). Real credit only, or none.

### D.5 Decomposition & recency
- **Multi-cause:** name the top 1–2 drivers by magnitude ("$180 from the Visa, $40 from dining"), or
  honestly say "a lot of small good choices" if it's genuinely diffuse. Never cherry-pick one cause and
  imply it was the whole story.
- **Recency governs framing, not truth:** a recent action → "because you just did X." An older action
  that's still the real cause → *state* framing ("your position now supports Z"), optionally "since you
  cleared X last year." Never dress an old cause as fresh. Default fresh-credit recency ≈ 12 months
  (tunable).

### D.6 Income and investments: potential is not achievement
Two capacity sources that look positive but must **not** be credited as user achievement or treated as
a green-light on their own:

**A raise is potential, not virtue.** A pay bump the user simply spends is not progress. The green-light
never fires on the raise itself — only on the *behavior that converts it* (debt paid down, purchases
slowed), and attribution credits that conversion, not the paycheck. Crediting a raise as success is the
**attribution-side of the banned "make more money" fallacy** (§6.3): we won't accept "earn more" as a
*solution*, and we won't celebrate "earned more" as an *achievement*. Same principle, both sides — a
raise is a bigger opportunity to do the real thing, not the real thing.

**Investments are a living thing — never spendable capacity.** Portfolio value moves, weakens,
strengthens, and can be cashed out. So unrealized (paper) gains are **never** the basis of a green-light
("your stocks are up, buy Z") and are **never** credited to the user as discipline — a market gain is
not an action (D.3). Market-driven net-worth growth is shown as *fact* (net worth is net worth) but is
neither achievement nor spendable capacity. A cash-out is itself a **decision to teach about**,
BYB-style ("cashing out $5k for Z costs you your buffer and its future growth") — not an unlock to
celebrate; it is often the opposite of the lesson.

**Net:** the green-light's input is filtered to **behavior-driven, realized, deliberate** changes only.
Raises and paper gains are context, not credit.

---

## Appendix E — "Least Disruption": Ranking Solutions Without Judging

When the Solution Engine (§6) offers levers to close a gap, it ranks them by "least disruption to the
user's life" (§6.2). The trap: the instant we rank spending by *our* idea of what's disposable, we
become the latte-shaming app we refuse to be. What's disruptive is the user's call, not ours.

### E.1 The only universal ranking is a necessity floor (stability, not virtue)
Protected by necessity, never proposed for cuts: housing, utilities, food (groceries), insurance,
transport-to-work, minimum debt payments, kids' basic needs. Protected because cutting them breaks
stability (Appendix C.5), **not** because they're morally superior. This is the one objective layer —
and the one place the platform asserts a default the human should sanity-check (e.g. "transport to
work" isn't universal).

### E.2 Above the floor, sacred-vs-flexible is the user's — learned from proof, never assumed
We don't guess which spending is disposable; we read the user's own history (proof, not persuasion —
data already in `budget_adjusted` + the category ledger):
- **cut before and it stuck** → demonstrably flexible *for this user*;
- **cut, then restored** → demonstrably sacred (they tried; it hurt);
- **never touched, held through tight months** → treat as sacred until shown otherwise.
The user's **explicit word always beats inference.** The inference is visible and correctable — never
a hidden model that quietly deprioritizes something they love (Appendix B: show your work).

### E.2a Correlated causes get a probation window before classification (the "raise → dining" case)
A category's spending can shift for a reason that has nothing to do with discretion — a wage or hours
increase that shows up in the ledger, a one-time event, a change elsewhere in the budget that explains
the new number. Classifying a shift as flexible-or-sacred (E.2) before checking for a correlated cause
risks the exact fabrication §3 #1 forbids: not inventing a number, but inventing a *meaning* for one
that isn't ours to assign.

The lag is real and must be respected. A correlated cause doesn't always land in the ledger on the same
cycle as the effect — a raise may post immediately while the spending pattern it explains takes two or
three weeks to become a stable pattern rather than noise (the same evidence-threshold problem as cold
start, Appendix C.7, applied to a shifted category instead of a new one). During that window the system
holds *less* proof than E.2 needs to classify, not *different* proof — so it is governed by C.7, not by
a new rule: insufficient evidence is an honest-no on the classification itself. The category is not yet
flexible, not yet sacred — it is **unclassified**, and stays out of the Solution Engine's eligible-lever
set (§6.1) until the probation window closes.

- **What ends probation:** either the pattern holds long enough on its own to satisfy E.2's normal
  threshold with no correlated cause found (classify normally), or a correlated cause is confirmed in
  the ledger (below).
- **What a confirmed correlation does:** it can still change the classification — but the change is the
  user's to make, not the system's. A dining rise that moves with a concurrent hours/wage rise is the
  *strongest* trigger to surface the fact and ask, at the earliest moment, "is this something to
  protect?" If the user confirms, the category becomes **user-protected** (sacred by their explicit
  word, E.2) and the Solution Engine treats it as off-limits. What the system must **not** do is promote
  the category to E.1's necessity floor on its own: E.1 is an objective *stability* floor, extra dining
  isn't stability even when income-correlated, and "this correlation means it's now a necessity" is
  exactly the inferred causal meaning F.8 and this subsection's opening forbid. **The confirmed
  correlation earns the user a prompt, not a system verdict.**
- **Correlation is shown, never narrated as cause.** The system may surface "this category rose in the
  same window your income did" as a drillable fact (Appendix B — proof, not persuasion). It may not say
  "you're working more and don't have time to cook" or any other story about *why* — that is F.8's line
  ("shows the shift, not the story"), and it applies here with the same force: a correlation is not a
  confirmed cause, only a fact worth showing the user so they can confirm or correct it (E.2's "explicit
  word beats inference," at the earliest possible moment rather than after a bad proposal already
  shipped).
- **This is a precondition, not a new appendix.** It adds no rule outside what C.7 and F.8 already
  established — it is their existing discipline (no claim without proof; shift ≠ story) applied one step
  earlier, at classification, instead of at output.

### E.2b The general correction channel — override any inference (not only the E.2a case)
E.2's "explicit word beats inference" is a *principle*; this is its *mechanism* for the general case
E.2a doesn't cover — the user just disagrees with a classification, no correlated cause. Pinnable now:
- **An override is a persistent user-set classification.** "Protect dining" / "dining's flexible after
  all" holds as the user's explicit word, not a one-time nudge. The user can release or change it
  anytime — their word, not a cage.
- **It does not decay — a deliberate contrast.** F.8's propagation and E.2's inferences decay or re-earn
  confidence over time, because they are *inferences* (guesses that age). An override is a *declaration*
  (ground truth); a declaration doesn't get less true with time, so it persists at full strength until
  the user changes it. **Builder note:** do not apply F.8's decay to overrides — the decay mechanic is
  for inferred confidence, not declared preference.
- **It narrows uncertainty and does not propagate — and this is *earned*, not assumed** (the "no
  fan-out" outcome is exactly the convenient-clean result §3's extension guardrail says to distrust).
  F.8 propagates because a break is an *unexplained* discontinuity: the model sees behavior move,
  doesn't know the cause, and hedges its ignorance by widening confidence broadly. An override has *no
  unexplained cause — it is the explanation*, so there's no ignorance to hedge, nothing to propagate.
  Second reason reinforces the first: reading "protected dining" as "feels broadly tighter" would infer
  a *story* from a *declaration* — the move E.2a and F.8's "shows the shift, not the story" forbid. If
  the user *is* broadly tighter, that shows in **behavior** (F.8/G/E.2's channel), never mined from a
  declaration. Declarations are received locally; broad state is read from behavior — two channels, two
  jobs. So an override is the **inverse of a break**: a break widens confidence and decays back; an
  override collapses it and doesn't decay. Same axis, opposite sign — same inference-vs-declaration line
  as the bullet above.
- **Word vs. action, reconciled.** The one place E.2's "explicit word beats inference" and F.6's
  "actions are the answer" look like they collide. They don't: F.6 governs the *no-explicit-word* case
  (willingness inferred from behavior); once there's an explicit word, it's the higher-confidence signal
  and beats inference. A *durable* contradicting behavior doesn't silently flip the word — it surfaces a
  **contradiction-check**: "you set dining protected, but you've been trimming it — which do you mean?"
- **The contradiction-check is not "just another prompt."** It's a reconciliation between the user's own
  word and their own action, not a teaching insight, so it doesn't map onto A's gates cleanly — there's
  no §6 *lever* for a contradiction; the actionable thing is the *answer* itself. So it is **Passive by
  default** — surfaced in F.3's working picture, where the user already sees overrides against
  behavior — and promotes to **Proactive** only through the Gauntlet as a *scale-appropriate instance*
  (like G.3b did for G): materiality ruled by the *weight of the contradiction* (category significance ×
  how durable the drift is), Actionability satisfied by the resolution being available, not a §6 lever.
  *(Open sub-question — see §12: a contradiction-check is a third prompt-kind, a clarification, neither
  brake nor green-light, so whether it draws its own A.3 budget or competes by materiality in contention
  is unpinned.)*
- **Overrides take effect prospectively.** An override set *after* a proposal or trophy already fired
  does not retroactively invalidate it: a proposal shown while dining was flexible was honest at the
  time (point-in-time honesty, like the historian's), and an earned trophy is a receipt of a real past
  action (B.3) — receipts aren't un-issued. The override changes classification *going forward*. The one
  exception: a *live, not-yet-acted* proposal now inconsistent with a fresh override updates to respect
  it, rather than standing against the user's just-stated word.

**Deferred to F.3 (the interaction):** *how* the user issues an override, and *where* the standing set
of overrides — and the Passive contradiction-checks — are seen and adjusted. F.3's one living working
picture is exactly that surface. This closes the correction channel's *discipline*; its
*interaction* rides with F.3.

### E.3 Ranking order (among honest levers, §6.1)
Hard constraint: the necessity floor (E.1) is off the table. Then prefer:
1. **Waiting/timing over cutting** — delaying a not-yet purchase disrupts nothing current; often the
   least-disruptive path, and the honest-no already speaks it.
2. **Flexible-by-proof over sacred-by-proof** categories.
3. **Smaller, reversible over large, permanent** (pause a subscription > restructure housing).
4. **Changes the user has demonstrated tolerance for** over untested ones.
5. **Spread vs. concentrate** (many small trims vs. one clean cut) is itself a per-user preference —
   learn it, or offer both.

### E.4 Rank, don't decide — show the tradeoff, let the user choose
The engine never imposes one answer. It shows the top paths *with their costs*: "trimming subscriptions
gets there in 5 months; protect subs and cut dining, 4; protect both, 7." The math is visible; the
choice is the user's — **and which path they pick is how the engine learns their priorities.** This is
the anti-preachy mechanism applied to solutions.

### E.5 When in doubt, ask — never assume disposable
A $50 cut is trivial to one person and a child's only activity to another; the math can't see that.
Where a category's status is unknown and a proposal would touch it, **ask rather than assume**, or
offer options and let the user reveal priority by choosing. Kids especially: basic needs are floor
(E.1); enrichment is default-protected and never proposed for cuts without asking. Humility is a
feature, not a gap.

---

## Appendix F — The Willingness Layer (the interaction model)

*Status: the interaction model is **named and now placed** (F.3, settled 2026-09-03). What it is, how each
source proves itself, what may persist and where it lives are decided; **none of it is built**.*

The deepest expression of "recorder → teacher": a teacher implies a **relationship**, not a broadcast.
This is not a feature — it's the **interaction model** the rest of the blueprint serves.

### F.1 The three planes normal software collapses
Most software (and every finance app) collapses three things that must stay separate:
1. **What's true** — the proof/math (ledger, consequences). Immutable, honest.
2. **What would help** — the full solution space the engine can see (all levers, §6). Complete, offered.
3. **What the user is willing to do** — their declared willingness. Sovereign, theirs alone.

Normal software assumes *true + helpful ⇒ you should ⇒ nag.* Groundwork keeps the planes separate:
**always show plane 1, always offer plane 2, only ever act/teach within plane 3** — never pretending
the gap between 2 and 3 doesn't exist, never shaming it. The user draws and redraws the boundary of
their own commitment; the software continuously re-derives honest guidance inside it. That is "real
change, not do-you-like-X-or-Y."

### F.2 "Nothing at all" is a first-class answer
The user can set willingness to zero — "I'm not changing anything right now" — and the software accepts
it without guilt, still shows the truth, and stays quietly useful ("here's where that leaves you; I'm
here when you're ready"). Respecting "no" is what earns the eventual "yes." This is the trust engine.

### F.3 Where it lives — SETTLED 2026-09-03
**Not a settings screen** — willingness-as-static-config is the exact preferences-toggle trap this is
meant to escape. Candidate direction:
- **Declared in context** — willingness is expressed at real decision moments ("I'll cut dining, never
  the kids' stuff" said in response to a specific proposal), where it's concrete; accumulated into one
  living model.
- **Summarized in one living place — the working picture.** A single view holding what Groundwork
  actually has to go on: the observed, the inferred and the declared (F.6a), each with its
  provenance; the gap to the user's goals; and what is reachable within their current willingness.
  It doesn't live in a screen; it lives in the **relationship state** — expressed everywhere,
  summarized in one place.
  - **Not "the current agreement."** That was the name used here first, and it oversells. An
    agreement implies both parties committed, while F.1 makes willingness *theirs alone* and F.6b
    makes `unclassified` the common case. For most users most of the time there is no agreement —
    there is a ledger, perhaps a declaration, and no strategy. The name has to be honest about that
    or the screen gets built to justify the name.
  - **The empty state is the design centre, not an edge case.** Because `unclassified` must stay
    common (F.6b), this view is nearly empty for most users most of the time. A view that is empty
    by design gets filled with noise to look useful — unless the emptiness *is* the point. It is
    the point: an empty working picture is the software saying *I have not earned any conclusions
    about you yet*, which is the one thing no other finance product will say on day one. Design
    this state first. The populated one is both the easier problem and the rarer one.
- **Proof-backed and correctable** — "you said X in March; your behavior since suggests Y — update?"
  A living, honest contract (Appendix E), never a frozen declaration.
- **Nothing is editable that isn't first a claim with a receipt.** This is what keeps the view out
  of the settings trap it opens by declaring. E.2b defers the override *interaction* to here, so
  the user must be able to mark dining protected somewhere — and a place where you set things is a
  settings screen unless something prevents it. The preventer: every editable item is attached to a
  claim the software has already made, shown with the evidence it rests on. Editing is **disputing
  a claim**, not configuring a system. There is no preference to set about something Groundwork has
  never observed, because there is nothing there to dispute. This governs what the *view* offers
  to edit, not what the user may volunteer: in-context declaration is the other channel and is
  untouched — "never the kids' stuff," said in response to a proposal, stands whether or not that
  category has any history behind it.
  - The editable surface is therefore **generated from evidence, not from a feature list** — the
    same rule as the watch catalogue, where only what can be proven for *this* user may be offered,
    applied a third time. The consistency is not tidiness: a feature list is a fixed set somebody
    maintains, and maintaining one is exactly how "not a settings screen" degrades into one.
  - It also bounds the empty state honestly: a working picture with nothing in it has nothing to
    edit. **A settings screen has all of its controls on day one; this one starts with none and
    grows them as evidence arrives.** That is the difference stated as behaviour rather than as
    intent — and behaviour is the half that can be checked.
- **Where it lives: with the assistant.** The working picture is not a summary of beliefs — it is
  **the assistant's record of its own conduct**: what it concluded, what it did, why, and what the
  user may dispute. The assistant draws the conclusions, makes the adjustments
  (`ASSISTANT_SCOPE.md`) and issues the offers, so the record belongs where the work happened.
  - **Same home, distinct view.** A Q&A transcript is a poor place for durable state; the record
    would scroll away. The assistant has a conversation *and* a record, and they are not the same
    pane.
  - **Settings gets a pointer, never the thing.** One line — *"what Groundwork has concluded about
    how you handle money →"*. Discoverable from where people look, without the room full of
    toggles redefining what it is. Residence there would undo the rule above: a screen where
    everything else is configuration teaches the user to read this as configuration too.
  - **The emptiness is a cold-start property, not a steady state.** `unclassified` staying common
    (F.6b) keeps the *inferred* channel thin, but observed items, overrides and actions-taken
    accumulate. It starts empty and fills — the footprint-grows-with-evidence rule working as
    intended, not an argument against a permanent home.
  - **It is the Historian's first user-visible face.** The Historian is an event log with no
    surface (`historian/HISTORIAN_GUIDE.md` calls it infrastructure — the substrate H2's features
    read from). The working picture is how it becomes visible: as conclusions, each expanding to
    the events supporting them, rather than as a raw log, which is a debugging tool and not a user
    surface.
  - **The dependency, stated so a later demotion is visible.** This placement assumes the
    assistant is a **first-class destination**. If it becomes a secondary pane, the correction
    channel goes with it and E.2b quietly stops working. Demoting the assistant is therefore a
    decision about the Willingness Layer too, and should be taken as one.

### F.4 The hazards (and why existing guardrails defuse them)
- **Willingness must never become a stick.** "You said you'd cut dining and didn't" violates
  show-don't-scold (§3 #5) and the whole mission. A missed intention is renegotiated neutrally —
  "dining's harder to cut than expected; protect it and find another path?" — never a failure notice.
- **Don't over-ask.** Constant "what are you willing to change?" is its own nagging. Willingness is
  evidenced three ways with three different standards (F.6a), and only one of them is asking — all
  under the same gentle-proactive caps (Appendix A). Ask only when genuinely needed (E.5).
- **`unclassified` is not a prompt to ask.** It is the honest resting state, and asking would not
  resolve it anyway, since a stated answer is an opening bid rather than a verdict (F.6). The cost of
  not knowing is humility in ranking, not a gap to interrogate the user about.

### F.5 Why this is the spine
Appendices A–E are the mechanics; the Willingness Layer is the relationship they serve. The gauntlet
(A) paces it; the honest-no (C) is honest *within the current willingness*; the green-light (D) rewards
*chosen* change; least-disruption (E) ranks *within what the user will consider*. This layer is where
five systems become one relationship — and it's the piece that, if built well, makes Groundwork
function differently from other software.

### F.6 Actions are the answer (willingness is demonstrated, not declared)
The user's real answer to a suggestion is what they **do**, not what they say. "I'll cut dining" is a
hypothesis; the behavior that follows confirms or revises it. So the Willingness Layer is read
primarily from **action** (Appendices D.4, E.2), with stated willingness as an opening bid, not a
verdict. A stated intention that behavior doesn't follow is not a broken promise to scold — it is an
*answer* ("not this, not now"), and the software believes the behavior over the words and shifts to
match. **The software shifts as the user shifts.** This is proof, not persuasion (Appendix B), applied
to willingness itself: we don't take the word, we read the receipts. Even willingness is proven.

### F.6a How willingness is evidenced
Willingness reaches the software three ways, and they are not interchangeable — each carries a
different burden of proof. Collapsing them is how a system ends up asserting it knows someone on
evidence that could never support the claim.

| source | what it is | what it must prove |
|---|---|---|
| **Observed** | which categories the user has actually moved — `budget_adjusted` plus the category ledger (E.2) | a **citation**. It is a receipt, not an inference: it names the edits and transactions it rests on. |
| **Inferred** | the strategy label — which of §6.1's levers they reach for when capacity is needed (F.6b) | a **prediction** on behaviour it was not fitted to. Below threshold, it is not held. |
| **Declared** | their explicit word, given in context (F.3) | **nothing.** It is sovereign. It beats inference (E.2b), is received locally, and is never mined for broader state. |

Three properties follow, each load-bearing:
- **The standards do not substitute for one another.** An observation is not promoted to a strategy by
  repetition, and a declaration is not demoted by contradicting behaviour — that surfaces a
  contradiction-check (E.2b); it never silently overwrites the word.
- **All three are adjustable, always.** None is a verdict. The user moves any of them at any time and
  the software re-derives rather than argues.
- **`unclassified` is the resting state of the inferred channel** and must stay common (F.6b). The
  observed and declared channels keep working while it is empty — which is why not knowing someone's
  strategy costs *humility in ranking*, not the ability to help.

### F.6b Willingness is a strategy, not a motive
F.6 establishes that willingness is read from action. This establishes *what kind of thing* is being
read, and how we know we read it right. Both come from `LEARNING.md` (the Assistant's Layer 2),
narrowed to finance.

Two claims answer *why did they do that*, and only one leaves evidence:

| | |
|---|---|
| **motive** — *they protect dining because cooking feels like failure* | refused |
| **strategy** — *when capacity is needed they trim recurring items and never touch timing* | **this is the layer** |

A motive explains everything and can never be wrong. A strategy commits to a forecast and can
therefore be **graded**, which is the only honest test of whether the software knows this person at
all. It is Appendix B applied to willingness itself: we don't take the word, we read the receipts —
and then we check whether reading them worked.

- **The taxonomy is the engine's own lever set (§6.1).** We invent no behavioural categories. A
  willingness strategy is *which honest lever this person actually reaches for*: reallocation, timing,
  payoff-order, trimming, substitution, save-first, do-nothing — plus `unclassified`. Each carries the
  discriminating prediction that makes it falsifiable: **given a shortfall next month, which lever
  shows up in the ledger.** E ranks within what the user will consider; this is what "will consider"
  means, in the vocabulary the engine already speaks.
- **The prediction test.** A strategy may be attributed only when it predicts behaviour it was **not
  fitted to** — better than the alternatives and better than a naive baseline. Fit on events up to a
  point, score on what came after; never fit and score on the same events. The label and its score are
  **cached** together and recomputed as behaviour arrives — cached, never remembered (§10).
  Below threshold the label drops to `unclassified`. Nobody decides this; the arithmetic does.
- **`unclassified` is the resting state and must stay common.** A taxonomy that always finds a
  category is a horoscope. **If in practice nearly everyone gets a label, this layer is decoration and
  should be deleted** — an acceptance test, not a caution. It is also the honest home for F.2's
  "nothing at all": a user who changes nothing has no strategy to attribute, and that is a fact about
  our evidence, not a verdict about them.
- **Scoped to where it was earned.** A strategy earned in debt payoff is a claim about debt payoff.
  Carrying it to how someone meets a grocery shortfall is a leap the ledger cannot back. A
  cross-context transfer enters as a labelled hypothesis at a weaker class, is tested where it landed,
  and promoted only if it predicts there too.

### F.7 The teacher–student covenant (effort-matched teaching)
The relationship is reciprocal and non-coercive: *the software keeps teaching as long as the student is
willing to attend and study.*
- **We own our half, not theirs.** Our job is to teach truthfully and keep the door open. The student's
  willingness is theirs — we don't manufacture it, and we haven't failed when they don't have it.
  Success is *having taught honestly to whoever was willing to learn* — **not** retention. That is why
  "if the truth makes them leave, fine" (Appendix B.4) is respect, not resignation: we control our
  integrity, never their readiness, and a teacher who tried to control the latter would have to lie or
  coerce.
- **Effort-matched, not attention-maximizing.** Investment tracks engagement: lean in and go deeper for
  the student who studies; for the one who stops attending, **don't chase** — keep the classroom lit and
  teach when they return. This is the exact *inverse* of engagement-optimization, which pushes hardest
  on the disengaged to re-hook them (§9). A business built on attention cannot afford to stop chasing;
  we can, because we don't sell the student's time. The moat, stated as a relationship. This is only
  affordable because the software is freeware (§3 #9): with nothing to sell, there is no incentive to
  chase.

### F.8 From prediction to projection (predictability, honestly)
Earlier this project rejected *prediction* — forecasting a user's choices, especially from hesitation
surveillance, for engagement (§9). The covenant changes what becomes possible without reopening that
door. Prediction was dishonest because we were **guessing a willingness we didn't have.** Once
willingness is *demonstrated* (F.6), the missing honest input arrives, and the future becomes
**projectable deterministically** — not because we predict the person, but because they have shown us
the input. The Willingness Layer is precisely what converts illegitimate *prediction of behavior* into
legitimate *projection of outcomes*.
- **The swing.** The value isn't a fixed forecast — it's *sensitivity*: given the user's demonstrated
  trajectory, where does one small willing change swing the outcome most? Teaching at its sharpest is
  showing the leverage point, not the destiny.
- **Live, not fixed.** The projection is conditioned on demonstrated behavior and re-derived as
  behavior shifts (F.6). If the user changes, it changes; it never claims to know their choices.
- **The trigger for "live" is a break-detector, not a clock.** "Live" (above) means the system
  re-derives *when the signal actually breaks* — a discontinuity in demonstrated behavior, detected by
  its **shape** — not on a nightly clock or a fixed decay window (which just averages and hopes to
  catch up eventually). This is the "swing" applied to the willingness model instead of the payoff
  model: it watches *where and how hard* the signal moved. Two disciplines keep it honest and correctly
  scoped:
  - **It fans out — not just to the projection.** A detected break re-derives the **willingness model
    (E.2)** *and* the projection, and drives F.6's "software shifts as the user shifts." Scope it to
    every willingness-dependent layer; a break-detector wired only to the forecast would leave the
    willingness model coasting on a dumb clock — the exact under-scoping C.7 warns against.
  - **Propagation is proportional to the break, not binary.** Whether a break resets confidence in the
    touched category only or system-wide is a false fork — the real variable is continuous: the break's
    **magnitude × breadth**. A small local wobble stays local; a hard, broad break widens uncertainty
    everywhere, because the user's whole context likely just moved. There is **no separate
    "is-this-load-bearing?" rule to design** — a break in a load-bearing category (income, rent) is wide
    and deep *by definition*, since so much of the model is downstream of it, so measuring the break's
    spread captures it automatically. It's the same measurement as the swing ("where does one small
    change matter most"), run on the *disruption* side instead of the opportunity side.
  - **Not just F.8's own inputs — the propagation is general.** It operates on any confirmed **break**
    in demonstrated behavior, regardless of which appendix first detects it. A confirmed debt-cycle
    recurrence (Appendix G) is such a break: G's strict, boundary-based detector and F.8's shape-based
    detector answer different questions (did a discrete threshold get crossed vs. does an ongoing
    pattern's shape show a discontinuity) and stay separate for that reason (G.2) — but once G confirms
    a break, it is simply an input to the propagation math already described above, on the same terms as
    any other break: it widens confidence in proportion to its own magnitude and breadth, and decays
    back down exactly as any other break does, governed entirely by subsequent proof. No separate rule,
    no standing floor, nothing G-specific. Detection method and propagation are two different questions
    — the appendices differ on the first, and were never meant to differ on the second.
  - **It never tips into prediction.** The detector acts on the *fact* that a break happened — its
    shape — never on *why* or *how long* ("Shows the shift, not the story", below). Noticing a
    discontinuity is the opposite of forecasting a choice; it stays on the honest side of the F.8 line.
- **Shows the shift, not the story.** The ledger surfaces a change — a rise in spending, a missed
  payment — as a visible, auditable *fact*, and the projection updates from it, so the user can always
  trace *why the number moved* to specific transactions (proof reaching into the projection's inputs).
  But the software shows only the **fact** of the shift. It does **not** diagnose the **why** (a bad
  month, a job loss, a medical bill, a real change of habit — it cannot see it) and does **not** predict
  the **duration** (two hard months are not a trend). A shift is an *incomplete answer*: it reopens the
  conversation (re-check the plan/willingness, F.4; ask, don't assume, E.5), never a verdict. And not
  knowing the why is what makes non-judgment **structural** — the software cannot moralize a cause it
  cannot see.
- **Bounded by honesty.** Same credibility ceiling as the honest-no (Appendix C): precision degrades
  with distance; we project only as far as we can stand behind.
- **Still barred.** This does *not* reopen intention-modeling, hesitation-timing, or surveillance-based
  behavioral prediction (§9). Predictability lives entirely inside deterministic consequence
  conditioned on *demonstrated* willingness — the honest completion of the earlier "no prediction"
  stance, not a reversal of it.

---

## Appendix G — Debt-Cycle Recurrence (The Long Arc)

**Status:** named here, **gated** — not yet in the build. The *narrative and guardrails* are resolved
(G.1, G.4, G.5). The *mechanism* is not: the cycle-detection threshold (G.3) and the insufficient-history
handling (C.7) are the open piece — the same gate as Trophy Room (§11/§12): concept settled,
proof-standard to be pinned down before build, so it can't ship loose under deadline pressure. Two
things are genuinely left, not one — pin the threshold, then decide where the fact gets shown.

### G.1 The gap this closes
Pillar 4 (green-light) and Pillar 5 (memory) both operate on a single arc: debt accrues, the user acts,
debt clears, it's celebrated. Nothing in the current design asks whether this is the second time through
that arc — and if the user is now deeper in debt than before the first payoff, the platform has no
mechanism to say so. The gap isn't that the user might fail again — that's unknowable, and this appendix
doesn't claim to know it. The gap is narrower and fully knowable: the user may not realize they've
already been through this shape once. They lived the two cycles as separate moments in time; the
Historian can show they're the same story, told twice. That is a visibility gap, not a willpower gap —
and visibility gaps are exactly what proof-not-persuasion (Appendix B) exists to close.

### G.2 This is a different timescale than anything else in the doc
Everything built so far — the Gauntlet (A), the honest-no (C), the break-detector (F.8) — operates on
weeks-to-months, single-category, single-decision patterns. A debt cycle is months-to-years and
structural: payoff → relief → gradual re-accumulation → a second crisis, possibly worse than the first.
It needs its own read of the Historian, not an extension of F.8's break-detector, which is tuned for a
much shorter discontinuity.

### G.3 What would have to be tracked
Not a new data collection (§10 — consumption, not collection): the same debt/payment events already
logged, read across a longer window and explicitly linked across cycles.
- **Cycle close (strict):** a genuine payoff — *overall revolving debt* cleared to ~$0 — closes
  "cycle N." Not "a major balance cleared," and not one debt type in isolation: the unit is overall
  revolving debt, because that's the shape that actually recurs, and a loose boundary is precisely what
  would fabricate a cycle that isn't one.
- **Cycle open:** re-accumulation of overall revolving debt after a close opens "cycle N+1."
- **Bias to false-negatives, never false-positives.** Where the boundary is ambiguous, the system stays
  *silent*, not speculative. Missing a real cycle is the acceptable cost; claiming one that isn't real
  is a fabricated story about the user's life — the exact proof-not-persuasion violation this appendix
  exists to prevent. Every recurrence shown must be unarguably real; the price is that some borderline
  cycles go unremarked (the honest-null bias — "return None rather than guess").
- The comparison that matters: cycle N+1's peak, compared honestly to cycle N's peak — not to zero, not
  to the moment of the trophy, but to the worst point of the prior cycle. "You are now higher than you
  were before you cleared this last time" is the fact that has no home anywhere else in this document.
- The cost of the first cycle (interest paid, time spent getting out) travels with the comparison —
  "$XXXX.XX in interest to get out last time" is a receipt (B.3) about the cost of the shape repeating,
  not a prediction that it will.

### G.3a When G is allowed to speak (the trigger, not just the comparison)
G.3's comparison (cycle N+1's peak vs. cycle N's peak) is a fact only once cycle N+1 has actually passed
the prior peak. Waiting for that moment to speak is the most honest option — and the least useful one,
since by then the worse outcome is already true. The resolution isn't a predicted threshold; it's a
second, earlier fact that's also fully true today, not guessed at:
- **No pattern yet** — silence (C.7's insufficient-evidence discipline applies here exactly as it does
  everywhere else in the doc).
- **Re-accumulating, but well below the prior peak** — no G-level statement. This is already visible in
  the ordinary debt/budget surfaces; G doesn't need to repeat it.
- **Approaching the prior peak, not yet past it** — a proactive, honest statement becomes available:
  "You are within $X of where you were before you cleared this last time; that cost $Y in interest to
  get out of." This is not a prediction that they'll exceed it — it's a true statement about present
  distance from a known point, exactly as honest as C's "you're 2 weeks from your debt-free date."
  Distance is a fact; direction of travel is not claimed.
- **Past the prior peak** — the full G.3 comparison, at maximum honest weight.

In A.1's vocabulary: the "below peak" state is **Passive** at most — the fact lives on the ordinary debt
surfaces if the user looks, never promoted; only the "approaching" and "past" checkpoints are candidates
for promotion to **Proactive**, and even then only through the Gauntlet (G.3b).

The "approaching" checkpoint is what makes G useful before the fact it's warning about is already locked
in — without predicting anything, because proximity is measurable today, the same way a debt-free date's
proximity is measurable before the date arrives.

### G.3b G's checkpoints route through the Gauntlet (Appendix A) — they do not bypass it
G.3a defines *when a fact becomes true* (proximity to, or passing, the prior peak). It does not, on its
own, define *when the software is allowed to interrupt the user with it*. That decision belongs to
Appendix A, the same as every other proactive insight in this document — G is not a separate alert
channel; per §3 #10 and the single pipeline (§5), it shares one voice and one gate with everything else.
A builder must not read G.3a as self-sufficient. Mapping G's checkpoints onto A's five gates (A.2):
1. **Materiality (A.2.1) — satisfied with a scale-appropriate ruler, not exempted.** G still passes
   A.2.1's gate; it does not get a bypass. It instantiates the gate at its own timescale: reaching the
   "approaching" checkpoint (G.3a) *is* G's materiality event, the proximity threshold serving as the
   significance test. A's default units (≥2 weeks on the debt-free date, ≥5% of budget) are tuned for
   short-horizon, single-decision insights and are the wrong *ruler* for a whole-cycle comparison — the
   same way A.2.1's materiality is already "relative to the user's scale, not absolute." So G uses the
   *correct* threshold for a cycle-scale fact, never a *lower* bar and never an exemption; it does not
   additionally need to clear ≥2 weeks / ≥5%.
2. **Actionability (A.2.2).** G's fact is bad news (approaching or past a prior peak), so per A.2.2 it
   needs an honest §6 lever attached, exactly like any other brake. The nearest-lever logic already
   required by C.4 supplies this — G cannot fire as a bare fact with nothing to do about it. In the dire
   case where no lever closes the gap sustainably (C.5's stability-floor situation), A.2.2's own "no
   lever → stays passive" rule applies — G never *pushes* bad-news-with-no-path — and the honest path
   there is the free CFPB referral (§6.2), never a loan (§6.3). This stops a builder from either
   inventing a bad lever just to satisfy Gate 2 or reaching for a banned one under pressure to have
   something to offer.
3. **Novelty (A.2.3).** Once shown at the "approaching" checkpoint, the same comparison is not re-shown
   on cooldown per A.4's normal dismiss rules — including the 60-day cooldown and the
   two-dismissals-drops-to-passive rule. Crossing from "approaching" to "exceeded" (G.3a) is a new,
   materially different fact and clears novelty on its own merits, not as a repeat.
4. **Budget (A.2.4 / A.3).** G's checkpoints draw from the same frequency cap as every other brake — no
   separate, uncapped budget; a cycle-recurrence warning competes for the same ≤2-per-7-days brake
   budget. Safe because A.3 resolves contention by **impact on the user's goal** — the user's importance
   wins the slot, never a special budget and never our ranking of insight kinds.
5. **Timing (A.2.5).** Fires at a natural boundary (dashboard load, after a relevant charge/payment
   saves) — never mid-task, same as everything else in A.

Below the "approaching" checkpoint, G has nothing to promote — there is no proactive candidate to
evaluate, so the Gauntlet is moot until G.3a's own proximity fact becomes true. The Gauntlet doesn't
make G fire sooner; it constrains whether an already-true G fact is allowed to interrupt, exactly as it
constrains every other insight in this document.

### G.4 The force is in visibility, not volume
The instinct to "push harder" here is right, but the push isn't frequency, insistence, or an exemption
from the Gauntlet (A) — every other insight in the doc stays capped and dismissable, and this one
doesn't need to be different. The force is in being the first time the two cycles are shown side by side
at all — whether at the approaching-checkpoint (G.3a) or the exceeded-checkpoint (G.3). A user who has
never seen "cycle 1 peaked at $X, cost $Y in interest; cycle 2 is now approaching or has passed that
peak" has never had the shape of their own history made visible — that fact, stated once and plainly,
carries its own weight without needing louder delivery. Making the connection visible is the harder
push; it doesn't require anything else on top of it.

### G.5 What this must not become
A diagnosis of why the cycle repeated (F.8 — still cannot see the cause), a prediction that the user
will fail again (this states a fact about position and history, never about what happens next),
shame-framed language (B.4 — clean facts, not indictment), or **a cycle inferred from history the
Historian cannot actually see (C.7)**. That last one is the common case, not a corner case: this needs
*two* genuine cycles on record, and for most users — for a long time — there won't be two, or the
history won't reach the prior peak. "I can't see a prior cycle to compare against" is an honest-no on
the comparison (C.7) — never a fabricated boundary, never an invented prior peak, and never a special
"no prior cycle" screen; it routes through the same path as every other insufficient-evidence case. It
is a statement about the trajectory, not a verdict on the person — the same distinction the honest-no
already draws (C.3): a fact about where things stand, not a prophecy about who someone is.
