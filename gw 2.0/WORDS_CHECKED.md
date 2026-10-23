# Item 110 — Every sentence checked against what it claims: the Projection, and the fixed words

Opened 2026-10-22, from the review pack's screenshots (`screenshot/review-2026-10-22/BRIEF.md`, known issues 1-3).
Rob asked whether each was the model or the guardrails. On the proposals, he said *"I agree with 1-3"*: one item,
written up, then built. **No code.** V1-V8 for ruling.

---

## 1. What is true today (measured 2026-10-22 on master `809b2cc`)

**The Dashboard's AI *Projection* is mostly not the model's fault.**

- **The fact it is given is wrong in kind.** The prompt (`app.js:28635`) says *"Redirect $287 → Cashback Visa: payoff
  Aug 2030→Aug 2029, 12 months sooner, saves $1303"*. The $287 is this month's restaurant overspend. But
  `_simulatePayoff(leverage.surplus)` (`app.js:28559`, `14118`) adds it as $287 extra **every month, forever**. A
  one-time $287 would move the date far less.
- **It is asked 4-5 times per Dashboard load.** On the sample household, every load sent one call with *"0 months
  sooner, saves $0"* (the debt plan not yet loaded), then three or four more with the $1,303 figure (AI log, 88 calls
  in 10 minutes). So the card's words change as the page settles.
- **The prompt asks for advice.** The stage note reads *"Keep all advice focused on debt payoff, spending habits, and
  momentum"* (`app.js:10511`).
- **The model adds what the facts don't hold:**
  - *"delaying debt freedom by one month"* (or three);
  - *"a cashback credit card"* for the Cashback Visa, which reads as a new card. Blueprint §3 #3: no new debt;
  - *"redirecting all non-essential spending"*.
- **The voice check misses them.** R8 compares only dollar amounts, comma-grouped numbers and percentages with the
  facts (`_FIN_NUM_RE`, `app.js:26689`); month counts and dates are not checked.
  - **Measured:** of the 115 AI answers on this Mac that passed the voice check, **24 (21%)** contain a month count or
    a month and year that is not in the facts. 23 are Projections and 1 is a category report.

**Two of the issues are fixed wording from 1.0, not the AI.** Both date from the initial commit (`161f30e`, Jul 24).
- *"⚠ VTI is 67% of your portfolio — consider diversifying."* (Investments, `app.js:17754`).
- *"Suggested $2,102.79 — keeps you in a healthy 50/30/20 split."* (Debt Payoff, `app.js:16567`). The figure is the
  minimums plus up to 20% of income (`_obSuggestedBudget`, `app.js:13954`).

**The voice rules run on AI text only.** Fixed wording was never swept against them. A sweep of the shown text with
the same word lists (`static/voice_rules.json`) finds, after setting aside the AI prompts, the word lists themselves
and the crisis-care words (`CARE.md`, fixed on purpose):
- an achievement that *"Rewards intentional overage"* (`app.js:1898`);
- the Trip Planner's *"…worth it with your eyes open"* (`app.js:13169`);
- a savings goal's *"you need to"* (`app.js:14221`).

The lists have no *consider* or *healthy*, so neither of Rob's two examples is caught.

## 2. What it would do

- A projection's facts would say what one payment does, and be worked out once the data is in.
- The model would be asked once per change of facts, for facts only, with names as written.
- Every month count and date the model writes would be checked like a dollar figure.
- The app's own fixed words would meet the same rules as the model's.

## 3. Points for ruling

**V1. The redirect is one payment.** The Projection's *"Redirect"* fact is worked out as **one payment of this month's
amount**, through the one-time engine that already exists (`decisionImpact({ oneTimeCost })`, Pillar 1). It is said as
*"this month's $287"*, never as if it repeats.
- (a) one payment. *Recommended.*
- (b) every month, said so: *"if $287 went to the Visa every month"*. That is a projection of behaviour, which
  Groundwork labels as an assumption, and it is not what the overspend is.

**V2. Asked once, when the facts are in.** The Projection is asked only after the debt plan has loaded, and only when
its facts change. It is kept by a fingerprint of the facts, so the same facts give the same saved answer: one call per
change, not 4-5 per load. *Recommended.*

**V3. The prompt asks for facts.** *"Keep all advice focused on…"* becomes *"State the facts given…"*, and the prompt
says to use account names exactly as written. *Recommended.*

**V4. Months and dates are checked.** R8 also compares each month count (*"12 months"*, *"one month"*) and each month
and year (*"August 2029"*) with the facts. As now, one that isn't there fails the answer, and the honest fallback
(the facts as fixed words) shows instead. On the 115 answers measured, 24 would have fallen back. *Recommended.*

**V5. No new borrowing in any answer.** A new rule (R12) fails an answer that names a kind of borrowing the person's
record doesn't hold: *a credit card*, *a new card*, *a cashback card*, *a balance transfer*, *a personal loan*,
*a loan* (unless one of their own debts is named). This is blueprint §3 #3, checked. *Recommended.*

**V6. Fixed words meet the same rules.** A smoke section sweeps every sentence the app shows with the voice word
lists, plus *consider*, *healthy* and *unhealthy* (added to the lists, for the model too).
- **Set aside:** the AI prompts, the word lists, and the crisis-care words. Each is named in the test with its
  reason.
- **Reworded now:**
  - Investments: *"VTI is 67% of your portfolio."* The fact; the ⚠ stays to mark concentration.
  - Achievement: *"Rewards finishing over budget on purpose"*, or the line goes.
  - Trip Planner: *"…so you can decide with the cost in front of you."*
  - Savings goal: *"…it takes $X a month"* for *"you need to"*.

*Recommended.*

**V7. The 50/30/20 suggestion keeps its number and loses its verdict:**

> Suggested $2,102.79: your minimums plus 20% of your income, from the 50/30/20 split.

*Recommended*, as Rob agreed.

**V8. Line and tests.** Master only. Tests:
- the Projection's redirect fact is one payment, and its words say so;
- one call per change of facts;
- R8 fails a month count and a date not in the facts, and passes them when they are;
- R12 fails *"a cashback credit card"* and passes the person's own card by name;
- the fixed-word sweep, with its named exceptions;
- the 50/30/20 wording;
- the voice harness re-screens every surface's examples.

*Recommended.*

## 4. Not decided here

- **The other AI surfaces' prompts.** Only the Projection's stage note asks for advice today. A sweep of every
  prompt's wording is its own point.
- **What a suggestion is.** The 50/30/20 figure stays a suggestion (V7). Whether Groundwork should suggest a debt
  budget at all is not asked.
