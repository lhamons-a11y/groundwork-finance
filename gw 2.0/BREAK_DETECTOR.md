# The break-detector: the build pass (Appendix F.8)

> Status: **ACCEPTED and CLOSED (Rob, 2026-09-30, §8).** Ruled and authorised 2026-09-28 (§6), built (§7),
> gate 1946 / 0, master code byte-identical to the gated `23fc301`. Opened the same day. Queue item 25. Rob, 2026-09-28: *"open Break-detector next,
> but only its defined Appendix F.8 slice — not W-D, W-E, Queue 24, or dashboard work."*
>
> The design is **F.8** (*"the trigger for 'live' is a break-detector, not a clock"*), with its limits
> set by **G.2** (G keeps its own detector), **E.2b** (a declaration is the inverse of a break and never
> decays) and **C.7** (insufficient evidence is an honest no, not a blank). This pass is the *build*:
> what "a break" means in the code that now exists, what it re-derives, and what it may show. The design
> is not reopened.
>
> **Out of scope by ruling:** W-D (the contradiction-check), W-E (strategy inference), item 24 (the
> schema-pin table gap), category split / merge, and all dashboard work. None of these is touched here,
> and none is needed by F.8's semantics (§3, B9).

---

## 1. What is fixed

1. **F.8.** "Live" means re-derive when the signal breaks, detected by its **shape**, never on a clock
   or a decay window.
   - **It fans out** to every willingness-dependent layer, not only the projection.
   - **Propagation is proportional** to the break's **magnitude × breadth**. A small local wobble stays
     local; a hard, broad break widens uncertainty everywhere. There is no separate "load-bearing" rule:
     a break in income is wide by definition.
   - **Recovery is by subsequent proof**, never by a timer.
   - **It shows the shift, not the story:** the fact of the change, never *why*, never *how long*.
   - **It never tips into prediction.**
2. **G.2.** Debt-cycle recurrence has its own detector (`core/cycles.py`), which F.8 does not extend.
   A confirmed G break is an *input* to F.8's propagation on the same terms as any other.
3. **E.2b.** A declaration is not touched by a break. It does not decay, and it is never re-read as
   "broadly tighter".
4. **The Willingness Layer as accepted** (`WILLINGNESS_LAYER.md` §8):
   - readings are recomputed on every read, and nothing derived is stored;
   - the read boundary is the record and the user's word, **never usage**.
5. **No silent learning; absence is not zero; teach the question; null-model a threshold before
   shipping it.**

---

## 2. What exists today (measured 2026-09-28, master `d22c7c4`)

| piece | state |
|---|---|
| a clock or decay window on the willingness model | **none.** W-A readings are recomputed on every read (ruling 2); nothing is cached, so nothing coasts |
| what the readings look back over | **one 12-month window, read as one regime.** `cut_held` checks every recorded month since the cut; `held` counts tight months anywhere in the window. A discontinuity inside the window is averaged over, not seen |
| a discontinuity detector for monthly series | **none.** `_renderWhatChanged` (app.js) compares this month with last month on the dashboard, a one-step delta with no notion of a sustained shift; `_renderDashSeasonalAlert` is seasonal. Neither is a break-detector, and both are 1.x dashboard code |
| G's detector | `core/cycles.py` `detect_cycles` / `recurrence`, boundary-based (below / approaching / past), built |
| projections conditioned on *demonstrated* behaviour | **one:** fund pace (`solution.fund_pace` fed by `server.fund_observed_monthly`, a 12-month average of contributions). The payoff projection (`core/consequence.py`) runs on the user's **set** debt budget, not on demonstrated behaviour, so F.8 has nothing to re-derive there |
| a willingness reading downstream of debt | **none.** No W-A reading depends on a debt series, so a G break has nothing to widen yet |

The first row is the pass's central finding. **The failure F.8 was written against, a model coasting on
a nightly clock, cannot happen in the code as built.** What remains is the second row: without a break
test, a recomputed reading still averages across a change. Recomputing every read is not the same as
seeing a break.

---

## 3. Findings and proposals

**B1: In this code, a break's job is to scope evidence, not to trigger recomputation.** Recomputation
already happens on every read. What a break adds is a boundary: **evidence from before a break does not
vouch for behaviour after it.** A reading whose receipt crosses a break in its reach is **suspended**:
- it drops to `unclassified` with reason `break`;
- it carries the break as its receipt;
- it re-earns its stance from post-break evidence alone.

That is F.8's "re-derive", stated for a system that re-derives constantly and needs to know *from where*.

**B2: The shape is a sustained level shift, measured against the series' own variability.**
- A break is confirmed when **at least two consecutive complete months** sit beyond the prior level by
  more than a multiple of that series' own month-to-month spread (a robust measure, e.g. the median
  absolute deviation).
- **One month is a wobble, never a break:** F.8's "two hard months are not a trend" governs what a break
  *means*; this rule governs whether one *happened*.
- **Only months the ledger holds count.** A missing month is a gap, never a zero, and a gap never
  creates or confirms a break (absence is not zero).
- Direction is recorded (up or down), and so are the magnitude and the months it spans.

**The thresholds are not chosen here.** Per the null-model rule, they are set by simulation *before* the
build ships, against:
- **trend-free series** at realistic noise, which must yield breaks rarely (the false-positive rate is
  the acceptance number);
- **known injected shifts**, which must be found (the detection rate is the second number).

If no setting clears both, the detector does not ship, just as W-E would not.

**B3: Proportionality, honestly, in a layer with no confidence number.** F.8 speaks of *widening
confidence* continuously. The accepted layer has **discrete stances** (flexible / sacred /
unclassified) and no confidence value to widen. So in this build, magnitude × breadth sets the break's
**reach**, which readings it suspends, not a number:

| break | reach |
|---|---|
| **local**: one category, magnitude past the threshold | that category's readings only |
| **broad**: income, or co-moving breaks in the same months across categories carrying at least a set share of spending | **every** reading whose evidence predates the break |

- **Income is broad by definition:** it is what F.8 means by load-bearing, so no separate rule is
  needed.
- The broad share is null-modelled with B2's thresholds.
- A continuous form waits for a layer that carries confidence (W-E would be the first), and is **not**
  invented here.

**B4: Recovery is by proof only.**
- A suspended reading returns when post-break evidence alone satisfies its own rule. For example,
  `cut_held` needs three recorded months after the later of the cut and the break.
- There is no timer, no decay and no "after N months, forget the break".
- A break that is followed by another break is simply the newer boundary.

**B5: Declarations are immune.** A break never suspends, flags or re-reads what the user said (E.2b).
- If behaviour after a break differs from a declaration, that is W-D's contradiction-check. It is
  **not built, and not built here.**
- The break is shown as a fact beside the declaration, and nothing more.

**B6: The fan-out.** F.8 names two targets:
- **the willingness model (in).** B1–B5.
- **the projection (open, for ruling).**
  - Fund pace is the one projection conditioned on demonstrated behaviour, and its 12-month average
    averages across a break.
  - Fanned out, a confirmed break in a fund's contributions would scope `fund_observed_monthly` to
    post-break months. With too few of them, it routes through C.7's honest no: "not enough months
    since your contributions changed to project from them". There would be no blank and no stale
    average.
  - The payoff projection runs on the set budget and is untouched.
  - **Ruling sought: include fund pace in this slice, or name it for later.**

**B7: Showing the shift, not the story.** A break is shown **in the working picture**, the
relationship's record, as a fact with its receipt:

> *"Dining spending moved from about $310 a month (January–May) to about $452 (June–August). Earlier
> readings of Dining are set aside until the months since then show where it stands."*

- It never says why, never says how long, and gives no advice.
- A lexicon test extends F.4's to forbid causal and durational words ("because", "due to", "for now",
  "temporarily", "will", "trend").
- It does **not** speak first: no proactive prompt and no dashboard item. The dashboard's attention list is ruled and
  closed at three kinds, and a break is not one of them.
- Where a break touches a category, the working picture's existing controls apply (the category was
  already claimed). **No new control is added.**

**B8: The read boundary extends, unchanged in kind.**
- The detector reads what W-A reads: debits by category and month, recorded income, and complete months
  only.
- s129's structural pin extends to the detector: no usage, no dismissal, no session event.
- **Nothing is stored.** A break is derived, so it is recomputed on every read (ruling 2) and needs no
  table and no schema bump. Item 24 is not touched.

**B9: G is named, not wired.** G's confirmed recurrence is an input to F.8's propagation (F.8 / G.2),
but **no W-A reading depends on debt** (§2), so a G break would have nothing to widen. Wiring it now
would be a consumer-less pipe. It is recorded as the first thing to connect when a debt-dependent
willingness reading exists. Category split / merge is likewise untouched: B1–B5 operate per category
name exactly as W-A does.

---

## 4. Cases

| # | situation | expected |
|---|---|---|
| Bd1 | a trend-free series at realistic noise | no break, at the null-modelled false-positive rate |
| Bd2 | one month spikes, then returns | no break (a wobble) |
| Bd3 | a sustained shift for two or more recorded months | a break: its direction, magnitude and months |
| Bd4 | a month missing inside the series | the gap neither creates nor confirms a break |
| Bd5 | a local break in Dining | Dining's reading suspended with the break as receipt; every other reading untouched |
| Bd6 | a break in recorded income | every reading with pre-break evidence suspended |
| Bd7 | three months of post-break evidence satisfy `cut_held` | the reading returns, citing only post-break months |
| Bd8 | a declared *protected* category breaks | the declaration unchanged and still in force; the break shown beside it as a fact |
| Bd9 | any break text | no cause, no duration, no advice (lexicon test) |
| Bd10 | the detector's reads | record and income only; the usage pin extended, with mutations |
| Bd11 | a G recurrence is confirmed | no effect on W-A (no debt-dependent reading); named for later |
| Bd12 | a fund's contributions break (if B6 fan-out is ruled in) | fund pace from post-break months, or C.7's honest no |
| Bd13 | the empty state (no readings, no statements) | unchanged: a break with no reading to suspend adds no control and no claim |

---

## 5. Ruling sought: Rob

1. **B1:** a break scopes evidence (suspends readings whose receipt crosses it), since recomputation
   already happens on every read?
2. **B2:** a sustained level shift against the series' own spread, at least two consecutive recorded
   months, gaps never counting, with thresholds set by a null model **before** shipping (a
   false-positive rate and a detection rate as the acceptance numbers)?
3. **B3:** proportionality as *reach* (local or broad, income always broad) while the layer has no
   confidence number, with no continuous form invented here?
4. **B4 / B5:** recovery by post-break proof only, no timer; declarations never touched?
5. **B6:** include fund pace as the projection fan-out in this slice, or name it for later?
6. **B7:** shown only in the working picture, as a fact with its receipt, never speaking first and
   never on the dashboard?
7. **B8 / B9:** nothing stored and no schema change; G named but not wired; master only?

---

## 6. Ruling: Rob, 2026-09-28

**F.8 authorised on exactly this seven-point basis:**

| # | ruling |
|---|---|
| **1** | **A break is an evidence boundary.** Pre-break behaviour cannot support a post-break willingness reading |
| **2** | **Detection is evidence-based and calibrated by simulation.** Two recorded months at a new level are necessary; the change must be material relative to that category's own variation. One anomalous month and missing months do not count. **If no threshold reliably separates known shifts from ordinary variation, the detector does not ship** |
| **3** | **Scope is proportional to the evidence affected.** A category break reaches that category's reading. An income break, or a coordinated multi-category change, reaches every reading that relies on older evidence. **No invented confidence score** |
| **4** | **Recovery requires new evidence.** No timer-based resurrection |
| **5** | **Declarations are immutable to the detector.** A behavioural break cannot invalidate something the user explicitly said |
| **6** | **Fund pace uses post-break evidence only.** When there are too few post-break months for a defensible pace, it says so; it **never falls back to the pre-break average** |
| **7** | **The working picture may state the observed change** (spending moved from roughly $310 to $452 a month). It does not attribute a cause, does not infer a duration beyond what is established, and does not turn the change into advice. It **stays out of the dashboard** and is **not surfaced unprompted** |

**The architectural point, recorded exactly as Rob made it:**

> A break does not erase historical evidence. It changes which evidence is admissible for a particular
> current behavioural reading. The underlying budget edits remain intact for receipts, history, and any
> other calculation that legitimately uses them.

**Scope boundaries confirmed:**
- no W-D, no W-E, and nothing from item 24;
- no category split / merge semantics;
- no dashboard work;
- no debt-cycle connection until a debt-based willingness reading exists;
- no schema change.

---

## 7. The build (2026-09-28)

| piece | where | what it does |
|---|---|---|
| **the detector** | `core/breaks.py` `detect_break` | Finds the latest run of **at least two recorded months** past the prior level. Every month of the run must clear **2.0 robust spreads** (median absolute deviation) of the series' own variation. The run's level must be **≥ 3.5 standard errors** away, measured on both segments' lengths, and the change must be **at least 30%** of the prior level. A two-month run is judged by its *less* extreme month, so one big month cannot carry it. The prior level needs at least four months. Gaps are never zeros. It imports only `random` and `statistics` |
| **the null model** | `core/breaks.py` `null_model`, run by s130 on **every gate** | Seeded simulations of monthly spending at 10 / 20 / 35 / 50% noise, including one-off double months. **False breaks on trend-free series: 0.7% / 2.4% / 3.1% / 4.1%, all ≤ 5%.** Sustained three-month shifts, located within a month: at 10% noise, +50% 85%, −50% 87%, ×2 97%, −70% 97%; at 20% noise, ×2 79%, −70% 82%. All clear the committed floors. A loosened threshold is shown to fail it, so a weaker detector cannot ship |
| **what it cannot see** | stated in `core/breaks.py` | A moderate shift in a noisy category (35% variation or more), or a ±50% shift at 20% variation, is usually invisible. That is the safe direction: an unseen break leaves every reading exactly as it was before this build |
| **the boundary** | `core/willingness.py` `breaks`, `observed_readings` | Each reading is computed twice, on the whole window and on post-break evidence only. If the post-break reading concludes, it stands and cites only post-break months (`boundary`). If only the whole-window reading concluded, the reading is **set aside** (`reason: 'break'`), keeping the break and the whole reading as its receipt. **Nothing is erased** |
| **explained by the user's own edit** | `breaks` | A category break beginning **within a month of the user's own budget edit** to that category (the month before, the month of it, or the month after) is the behaviour the reading is about, not an unexplained discontinuity (E.2b). It is no boundary for that category. Without this, a cut that held would set aside its own reading. *Found building; see below* |
| **reach** | `breaks` | A category break reaches its own category. **Broad** breaks reach every reading: an income break (load-bearing by definition), or unexplained category breaks beginning within a month of each other whose categories carried **at least a quarter of spending** before them (`BROAD_SHARE`) |
| **declarations** | `effective` unchanged | What the user said is never touched by a break |
| **fund pace** | `server.fund_contribution_break`, `fund_observed_monthly(since=)`, `solution.fund_pace(since_break=)`, `teaching/funds.js` | Complete months of in-app contributions (a month with none is a real zero here, because the app records them itself). After a break, only the months since count. With too few, `insufficient_since_break` is set: the date is the plan's, and the sentence says *"what goes in changed in July, from about $200/mo to about $60/mo, and there are too few months since then to set a pace from"* |
| **the words** | `teaching/willingness.js` `_breakText` | *"Hobbies spending moved from about $60 a month to about $126, from June on. What Groundwork read about Hobbies from before then is set aside until the months since show where it stands."* The set-aside reading is shown under it. No new control is added. A lexicon test forbids cause, duration and advice words |

**Tests: `smoke_sections/s130_break_detector.py`, 35 checks.**
- **The null model's acceptance numbers,** plus two mutations: a loosened threshold fails the model, and a one-month run would make a wobble a break.
- **Detector cases:** Bd1–Bd4, a shift that returns, the two-month minimum, and too little history.
- **Boundary cases:**
  - Bd5, local, with nothing erased;
  - a cut explaining its own drop, in the same month and the month after, while an edit months away does not;
  - Bd6, income and coordinated breaks, with small envelopes staying local;
  - Bd7, recovery on post-break proof;
  - Bd8, declarations;
  - Bd13, no claim without a reading.
- **Bd12, fund pace:** unit cases, then end to end from the Historian.
- **Scope checks:**
  - no storage;
  - no usage read;
  - no `core.cycles` import;
  - SCHEMA_VERSION unchanged;
  - the break stated as a fact, with a mutation adding a cause;
  - nothing in the proactive voice or app.js.

Standalone: s130 35 / 0, s129 45 / 0, s45 288 / 0, s30 12 / 0.

**Seen in the page** (throwaway database, built-in browser):
- Hobbies' "kept through tight months" reading was set aside under the break fact, with the old reading visible beneath it.
- Dining's cut explained its own drop: no boundary, still flexible.
- The fund's break read as the post-break pace. With too few months since, it read as the plan's date with the change stated.
- No console errors.

**Found while building, for Rob:**
- **The edit window.** Without it, the user's own cut is detected as a break and sets aside the reading it created. I ruled nothing new here. The window applies E.2b's "a break is an unexplained discontinuity", and it is named so it can be reviewed. Its width (a month either side) follows how people act: spend less first, update the budget after.
- **The detector's blind spot** (above) is real and structural. Eleven months of a noisy category cannot show a moderate shift at a false-alarm rate that protects true readings. Longer windows would help and are not proposed here.
- **The app's own auto-contribution counts.** Fund pace includes the current month's contribution once it is made, as before this build. In the page run it moved a fund from "too few months" to a post-break pace the moment the Budget page posted September's contribution.

---

## 8. Acceptance: Rob, 2026-09-30

**Item 25 is accepted and closed.** The basis Rob gave:
- built on master, full gate 1946 / 0;
- the code is byte-identical to the gated commit `23fc301`;
- the accidental push `9f475ea` is accounted for, with no history rewrite;
- `8354aff` removes the conflict markers and restores the intended queue state;
- `fbe2e8d` records the gate result;
- master is clean;
- the implementation follows the seven F.8 rulings, including post-break-only fund pace;
- item 24, item 26, W-D, W-E, category split / merge and the dashboard stay outside this pass.

**Sequencing:** Willingness Layer → break-detector → **dashboard, now the next pass to build**. Item 24
and the other explicitly unbuilt pieces stay separate.

