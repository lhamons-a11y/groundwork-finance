# The summary tiles meet the attention standard (queue item 27)

> Status: **OPENED 2026-09-30. No code.** Rob, 2026-09-30: *"I accept the dashboard build, open item 27."*
>
> **The standard** is the one Needs attention already meets (`DASHBOARD_SUMMARY_ATTENTION.md` §6–7):
> - every statement is a fact from the record, with its source;
> - completeness is tested first;
> - the question is taught, and no verdict or advice is given.
>
> Item 22 applied that standard to the attention list. This pass applies it to the six summary tiles and
> the greeting line, which were written before it.
>
> **Rob's aim, recorded with the queue** (2026-09-30): the dashboard should show people what they need
> *"before they know they want to see it"*. That comes from the record's upcoming facts, never from
> watching the user. It does not reopen the 17 August rule.
>
> **Out of scope:**
> - item 28 (ask for a tile), item 24, item 26, W-D, W-E;
> - the tile set and the arrangement rules (item 22 ruling 1, unchanged);
> - anything in 1.x.

---

## 1. Measured (master `dfde36e`)

| where | today | against the standard |
|---|---|---|
| **This month** (`_renderHealthCard`) | a verdict, **On track / Watch it / Over budget**, from `projected = spent ÷ days gone × days in month` against budgeted income; the border turns ember or gold | **verdict**, and **no completeness test**. In item 22's page run it said *"On track, Spent $0.00, $4,000 under budget"* for a September with nothing imported, directly under *"Checking: last imported Sep 4, 26 days ago"*. That is the $7,053 shape again |
| its meta row | *"DTI 41% ↑ above 36%"*, *"↓ lender-ready"*, *"⚠ No emergency buffer yet"* | a label about the person (*lender-ready*) and a warning, where the fact is the ratio and the question is what 36% means |
| **greeting line** (`renderDashboard`) | *"4 months on track. Keep going."*, *"This month needs attention."*, *"Getting close — stay sharp."*, *"Tip: build a $500 buffer before accelerating debt payoff."* | verdict and advice, before any fact |
| **Your plan** (`_renderDashHeroCard`) | *"Debt-free by March 2028"*, *"↓ 3 mo behind schedule"*, *"N months tracked"*; already gated on the debt confidence verdict (`_debtTrusted`) | mostly facts, and gated. *"behind schedule"* is judged against a schedule the user may never have set; the fact is the two dates |
| **What changed** (`_computeWhatChanged`) | confidence-gated, with a *Still being evaluated* column; ✓ / ↑ marks with *good* colouring | **closest to the standard already.** The *good / not good* colouring is the one judgement left |
| **Spending by category** (donut) | this period's debits by parent category; hides itself with no debits | facts, but **no completeness test.** A month half imported draws a whole-looking donut |
| **Freed minimums** | minimums freed by paid-off cards | facts, from the record |
| **Coming up** (`_renderDashUpcoming`) | due within 7 days, **this month's due day only** | misses next month's due dates (found building item 22); unpaid ones are already in Needs attention |

---

## 2. Findings and proposals

**T1: Completeness before any pace statement.**
- A month can be judged only when every imported account is current, meaning it has had an import since the month began (item 22's own fact, `stale_imports`).
- Otherwise the tile states the gap, not a pace: *"September so far: nothing imported for Checking since Sep 4, so this month's spending isn't known yet."*
- Accounts kept by hand are never counted as missing, the same rule as item 22.

**T2: This month says the arithmetic, not a verdict.**
- Keep: spent, days gone, the projection and budgeted income.
- Say it as the sum: *"Spent $1,240 in 12 of 30 days; at that rate the month ends near $3,100 against $4,000 budgeted."*
- Drop *On track / Watch it / Over budget* and the coloured border.
- The pace bar stays as the picture of the same numbers.
- The projection is labelled as a straight-line projection, because it is one.

**T3: The greeting keeps the greeting and loses the judgement.**
- *"Good morning, Rob."* followed by the one fact that matters most today, chosen from the record's upcoming facts (item 22's attention kinds first). This is where the *"before they know they want it"* aim lives.
- With nothing upcoming, the greeting alone. Never *"Keep going"*, never *"Tip:"*.

**T4: The meta row states ratios and teaches the question.**
- *"Debt payments are 41% of income (the DTI lenders look at; 36% is a common cut-off)."* No *lender-ready*, no ⚠.
- The buffer fact: *"No savings fund marked as an emergency buffer."* Only when the record can tell; otherwise nothing.

**T5: Your plan states dates, not a schedule verdict.**
- *"At the current payments, debt-free around March 2028; your plan date was December 2027."* This only when a plan date exists.
- *"behind schedule"* goes, because the two dates say it.

**T6: Every tile names its source and its window**, in one small line, as the attention items do. For example: *"From your ledger, Sep 1–12, all accounts current."*

**T7: The donut, and What changed.**
- The donut takes T1's completeness test and says which accounts it covers.
- What changed keeps its gating and loses the *good / not good* colouring. A movement is a movement.

**T8: Coming up shows the next occurrence** (item 22's `paymentsDue` logic): 2.0 corrects it through the teaching layer. The 1.x card stays as it is (1.x untouched).

**T9: Mechanism.** 2.0 only, through the teaching seam, the way item 22 did it:
- `dashboard.js` re-renders the tiles' text after `renderDashboard`, from the same numbers app.js computed;
- no app.js or index.html change;
- no schema, and no usage read (item 22's pins extend).

---

## 3. Cases

| # | situation | expected |
|---|---|---|
| St1 | nothing imported this month for an imported account | This month states the gap and names the account; no pace, no verdict |
| St2 | all accounts current, spending below the straight-line budget | the arithmetic sentence; no *On track* |
| St3 | above it | the same sentence; no *Over budget*, no ember border |
| St4 | an account kept by hand only | never counted as missing (T1) |
| St5 | the greeting with an unpaid payment due Thursday | *"Good morning."* + that fact, with its source |
| St6 | the greeting with nothing upcoming | the greeting alone |
| St7 | DTI 41% | the ratio and what 36% means; no *lender-ready*, no ⚠ |
| St8 | a plan date exists and the projection is later | both dates stated; no *behind schedule* |
| St9 | a half-imported month | the donut says which accounts and dates it covers |
| St10 | any tile text | a lexicon test: none of *on track, watch it, over budget, keep going, stay sharp, tip:, lender-ready, behind schedule* |
| St11 | 1.x | unchanged (app.js and index.html untouched) |

---

## 4. Ruling sought: Rob

1. **T1:** is *every imported account current since the month began* the completeness test for a pace statement?
2. **T2:** retire *On track / Watch it / Over budget* and the coloured border for the arithmetic sentence?
3. **T3:** does the greeting carry one upcoming fact from the record, or the greeting alone?
4. **T4–T5:** ratios with the question they answer; plan date against projected date, instead of *behind schedule*?
5. **T6–T8:** a source line on every tile; completeness on the donut; next-occurrence Coming up in 2.0?
6. **T9:** 2.0 only through the teaching seam; 1.x untouched?
