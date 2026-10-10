# Item 71 — When income drops: scenarios that keep a goal in reach, and how the budget follows

**ACCEPTED + CLOSED 2026-10-10** (Rob 2026-10-10: "i accept all").

Opened 2026-10-10. Rob:

> *"Scenario if Groundwork sees that income of one of the users appear to get less and less as their time is getting
> cut at work for whatever reason. Should groundwork start running scenarios that shows if this income stay at this
> rate what should the budget get adjusted for the user and that should also become part of the learning that income
> has become less and the budget (teaching) has to get adjusted. This will help users when this occur they never
> adjust their budget they just increase their debt. I think we can help users not do that but also the budget is
> not complete doom and gloom."*

Then: *"yes and I would like you to also offer multiple simulation that the agent should be running in the background
for the user and see what works and make settle adjustments to the budget to keep the user on track to meet their
goals."*

**Already decided (the frame, not reopened):**
- Item 65: AP2 (learn from the record, out loud: a pattern is shown with its evidence before it shapes a plan), AP4
  (life events are asked, never inferred: "your hours were cut" is never said), AP5 (a detector must beat a null
  model), AP9 (unknown said), AP11 (works with AI off), TM3 (never allocate money silently), TM6 (no urgency or
  doom), RG1–RG6 (every claim has evidence; scenarios expose their assumptions; failed validation withholds).
- Item 66: observed, projected and user-supplied are never confused; scenarios are recalculated when inputs change,
  marked stale otherwise, and never stored as conclusions; futures are chosen only on the person's word.
- Item 25: the break detector (income breaks included), null-modelled.
- Item 23: the person's flexible and protected categories (observed and declared) and the necessity floor.

**I6 RULED 2026-10-10: (a)** (Rob: *"this is where the rules to keep the ai in a box also gets gray because to do
exactly what you want it to do, it will break a rule. I agree with A."*). Rob's reason for the tap: *"its there just in case that the agent is wrong or its a temporary moment
that the AI is picking up."* The detector can mistake noise for a trend, and a real dip can be passing; the person's
tap is where either gets caught before the budget moves. I1–I5, I7, I8 RULED 2026-10-10 as recommended (Rob: "i accept rule 71"). **BUILT 2026-10-10** (Rob: "71 build on 66", "build all items that have been ruled on"): `core/income_change.py` (detect, budget_follows, scenarios, order), `/api/income-change` (read; answer; apply; undo; snooze), the Budget page card, the proactive card, the working picture's income line; s183. **The detector, null-modelled before it shipped:** a first version flagged up to 9% of plain noise, so it was tightened - the recent months must sit under every one of up to six months before them, and the drop must clear twice those months' own swing. Now: biweekly pay 0%, commission lumps 1.1%, late deposits 0%, noise 5/10/20% at 0.1/0.8/1.3%; a real slide 100%, a 15% cut found 73-100% depending on noise, a 12% cut 84%. The break detector (item 25) only names changes of 30% or more, so it is not what finds a pay cut. Awaiting the gate and acceptance.

**The one point that needed Rob's ruling against a settled rule was I6** (adjusting the budget without asking each
time). Everything else fits the rules as they stand. No code until Rob says "build item 71".

## 1. What is true today (master 4b22637)

- **A level change in income is already found:** `core/breaks.py`, through `willingness.breaks` (scope `income`),
  null-modelled at ≤5% false breaks. It is used only to limit which months count as evidence; nothing tells the
  person.
- **A slow slide is not found.** The break detector looks for a step, not a trend.
- **Budget amounts are what the person saved.** A month's figure can differ only by an estimate the person follows
  (item 26) or a bill they chose to use (item 68). Nothing changes a saved amount but the person.
- **Debt projections exist** (the payoff engine, the debt-free date) and **paths exist** (the solution engine: trim,
  reallocation, timing, payoff order …), each ranked by E.3 and by the person's willingness.
- **Goals:** the debt-free date, savings funds with target dates, and the budget plan's goal.

## 2. Points for ruling

**I1. Noticing an income change, honestly.** Two signals, both computed from the record whenever it changes
(an import, an edit), never on a clock:
- **a step** (the existing break detector, scope income): *"Your recorded income moved from about $4,002 a month to
  about $3,393, from July on."*
- **a slide** (new): income falling month over month for at least four complete months. It is null-modelled
  before it ships, against biweekly pay (a three-paycheck month), commission lumps and a late deposit, and must
  stay at or under 5% false slides on trend-free income.

Months missing income are unknown, never zero. It never says why income changed.
*Recommended.*

**I2. One question, the person's answer kept as theirs.** *"Do you expect this to last?"* Yes, for now / No, it's
temporary / Not sure. The answer is a statement (like item 23's), kept with when, changeable any time, and never
inferred. It decides which scenario leads (I3). No answer is "not sure", never "yes".
*Recommended.*

**I3. Several scenarios, computed for the person whenever the record or an answer changes.** This is "the agent
running simulations in the background": local arithmetic, recomputed when the inputs change. It is never on a
timer, never stored as a conclusion, and needs no AI. Each scenario is labelled with its assumptions (RG4):
1. **Nothing changes:** income stays at the new level, the budget as saved. *"The gap is $700 a month; at that rate
   the card balance grows about $700 a month and the debt-free date moves from March 2028 to …"*. This answers
   "people just add debt", in their own numbers.
2. **The budget follows the income:** the gap closed from the person's flexible categories first (item 23's
   order), never the necessity floor, with each line named and its new figure.
3. **A goal moves instead:** the same gap met by moving a goal's date (a savings fund's target, the debt-free date),
   shown as how far.
4. **It's temporary (a bridge):** how many months the person's buffer covers the gap, and what to trim only for
   those months.
5. **Income comes back:** for comparison, so the picture is never one-sided.

Each scenario says whether it keeps each goal on its date, in plain words, without verdict words.
*Recommended.*

**I4. "What works", side by side.** The scenarios appear together on one screen (the Budget page, and the working
picture's income line). Each shows the monthly gap, each goal's date, and the debt balance a year out.
- **The order:** the scenario that keeps the person's goals with the smallest change first. "Smallest change"
  counts budget lines touched, then dollars moved, never chosen for the person.
- **It's never doom:** the screen opens with what still holds (*"Your bills and the necessity floor are covered;
  it's $700 of the flexible spending that doesn't fit"*).

*Recommended.*

**I5. Reaching the person.** The income change is a candidate for the A.2 gauntlet as a brake. It is material by
nature, and its path is the scenarios. It can interrupt only if it passes the gates (the dial, novelty, the weekly
budget); otherwise it waits on the Budget page. Never a countdown, never an alarm (TM6).
*Recommended.*

**I6. Adjusting the budget: Rob's ruling. Rob asked for "subtle adjustments to keep the user on track"**, and that
meets TM3 head on. Three options:
- **(a) One tap, the person's tap.** A scenario carries **"Make this my budget"**. It changes the named lines, all
  at once, shown before and after, undoable, and recorded (`budget_adjusted`, the same as a manual edit, so item
  23 reads it as the person's own act). Groundwork can also offer a **monthly budget check-in**: if the record has
  moved, the leading scenario's adjustment is waiting there with one tap to take it. Nothing changes without that
  tap.
- **(b) A standing rule the person sets**, for example *"keep me on track: move up to $25 a month between my
  flexible categories without asking"*. Groundwork then adjusts within that bound on its own. Each change is listed
  where the person will see it, with Undo.
  - This rewrites TM3 for those categories and that amount.
  - Item 23 could no longer read those edits as the person's own (they wouldn't be), so they would need marking
    and leaving out of willingness.
  - It weakens the lesson: the person stops seeing the trade-off.
- **(c) Proposals only**, with no one-tap apply.

*Recommended: (a).* It keeps the person deciding and keeps the friction to one tap a month. The gap between "subtle
adjustments" and "one tap" is the rule TM3 protects. If Rob wants (b), it should come with its own bounds and tests
as a separate ruling.

**I7. The learning, out loud.** What Groundwork keeps: the income change as a recorded fact, with its months; the
person's answer to I2; and, if they take a scenario, their own budget edits (which item 23 already reads).
Groundwork shows its learning in the working picture: *"Income moved to about $3,393 from July; you said you expect
it to last; you moved $700 from Dining, Fun and Clothing on Aug 3."* It never concludes a story, such as "they lost
hours" or "they're struggling" (AP4, F.8).
*Recommended.*

**I8. Tests.**
- The slide detector's null model: biweekly pay, commission and late deposits stay at or under 5% false slides,
  and a real slide is found.
- Scenarios: each states its assumptions; "nothing changes" reaches the debt projection; the floor is never cut; a
  protected category is never cut; nothing is written without the tap; Undo restores.
- The question's answer is stored as said; no "why" is ever stated; no verdict or urgency words; it works with AI off.
- If I6 (b) is ruled, its bound is enforced and every change is listed with Undo.

Master only.
*Recommended.*

## 3. Not decided here

- **Other life changes** (a new expense, a raise): the same machinery could serve them; not proposed now.
- **Narration:** the scenarios stand without AI (AP11); the narrator may later explain them, under RG1–RG6.


## 4. Amendment: it fired too early (opened 2026-10-10)

Rob, after seeing the card on his own data: *"the loss in wages jumps the gun a little to early. It shows my income
has dipped ... it should look at the past 8 weeks income average compared to each 2 week period. or at least look
over the ledger see income salary and then look at the last 5 deposits and determine if the income dropped by more
than 8% for two pay periods in a row. why 8%"*

**Points D1–D8 for ruling. No code yet.**

### 4.1 What happened on Rob's data (measured 2026-10-10, a copy of the live database, nothing changed)

- **The pay never dropped. It moved to a category the detector can't see.**
  - Up to June 25, City of Millbrook pay (about $1,991–$2,125 every two weeks) was filed under **Income**.
  - From July 9 the same deposits are filed under **"Rob's Income"**: 7 deposits, $16,748.80.
  - "Rob's Income" and "Partner's income" were created on 2026-06-26 as **expense**-type categories, outside
    Income. They carry the same names as the budget's two income lines.
  - The detector counts only credits in the category named exactly "Income" (`_willingness_inputs`, server.py). From
    July it saw Harmon Packaging alone and read about $3,741 a month as lost.
  - "Rob's Income" also holds three debits ($317.78), one of them a City of Millbrook card charge (likely the water bill).
- **The month it compared was complete.** The current month is already left out, so a half-month was not the cause.
- **Other code that finds income by the name "Income":**
  - `_willingness_inputs` (server.py), which feeds item 71 and the Willingness readings;
  - `reclassify_income` (server.py);
  - `_buildStageContext` (app.js), which matches 'Income' exactly.

  Some page code matches any name containing "income", so different surfaces can disagree today.

### 4.2 Rob's rule, tested on his own paychecks first (the null-model rule)

Each payer is told apart by the deposit's description: City of Millbrook every 14 days, 20 checks; Harmon Packaging every
7 days, 40 checks, $788–$1,837. Each version of the rule was run on the real history. It was then run on his own
amounts shuffled 2,000 times, so that nothing changes and any alarm is false. Last, an 8–12% cut was planted in the
last checks to see whether it would be caught.

| Rule | City of Millbrook: real alarms / false alarms in the shuffles | Harmon: real / false |
|---|---|---|
| last 2 checks each 8% below the 8-week **average** | 4 / 92% | 19 / 100% |
| last 2 checks each 8% below the 8-week **typical check** (median) | **0 / 16%** (10%: 0 / 4%) | 2 / 53% |
| last 2 two-week **totals** each 8% below the typical two-week total | 0 / 14% | 4 / 98% |
| last **4** weekly checks each 8% below the typical check | — | 2 / 43% |

A real cut of 8% or more in the last checks was caught by the median versions.

- **The average fails.** Occasional big checks (overtime, City of Millbrook's $4,283 double check) lift the average, so
  ordinary pay sits below it most weeks.
- **Two-week totals fail.** Whether a payday lands just inside or just outside a window swings the totals.
- **The typical check works for a salary** (City of Millbrook).
- **Nothing tried works yet for hourly pay with overtime** (Harmon). Overtime weeks cluster and lift the typical
  check, and the ordinary weeks after them look like a cut. Harmon's checks fell in July–August against the spring
  because there was less overtime: real money, but not a pay cut.

### 4.3 Why 8%, or 10%?

Neither number comes from research; item 71 ruled 10%. As Rob's note says, a percentage alone doesn't tell you what
a drop means. What the tests show:

- **The threshold matters less than the method.** At 8% and at 10% the average-based rule fired on almost
  everything.
- **The right threshold depends on the payer.** It has to clear that payer's own normal swing. City of Millbrook's checks
  barely vary, so 8% is meaningful there. Harmon's vary by more than 100%, so no fixed percentage can separate a cut
  from a quiet overtime month.
- **What the drop does to the money matters more than its size.** The same 8% is $278 a month from $4,000. That is
  nothing with $800 left over and a $220 shortfall with $100 left over. The card should lead with that.

### 4.4 Points for ruling

**D1. Count all income.**
- A credit counts as income when its category is income-type, a child of Income, or carries the name of one of the
  budget's income lines.
- Every reader in §4.1 uses the same one definition, so no two surfaces can disagree again.

*Recommended.* This alone stops the card on Rob's data.

**D2. Repair the two categories, shown first.**
- "Rob's Income" and "Partner's income" become income-type children of Income.
- The three debits in "Rob's Income" are listed for Rob to re-file.
- Separately, find what created income lines' categories as expense-type, so it doesn't happen to anyone else.

*Recommended.* Nothing is changed until Rob sees the list.

**D3. Pay periods, not calendar months.**
- Each payer's deposits are compared with that payer's own pay, and payers are told apart by the deposit's
  description.
- Calendar months stay only for the scenarios' monthly figures.

*Recommended* (Rob's direction).

**D4. Against the typical check (median) of the 8 weeks before, never the average.** *Recommended*, on the evidence
in §4.2.

**D5. How long a drop must last.**
- A payer paid every two weeks: 2 checks in a row (Rob's "two pay periods").
- A payer paid weekly: 4 checks in a row, the same four weeks.

*Recommended.*

**D6. The threshold.**
- A drop counts when it is at least the larger of 8% and twice that payer's own normal swing.
- A rule ships only if it raises a false alarm 5% of the time or less in the shuffle test on the payer's own amounts.

*Recommended.* This keeps Rob's 8% where pay is steady and stays quiet where it isn't.

**D7. A paycheck that hasn't come in is not a drop.**
- When a payer's usual payday passes with nothing on record, the card asks: *"Your City of Millbrook pay hasn't come in
  since June 25. Is it filed somewhere else, or did it stop?"*
- It never treats the missing pay as zero.

*Recommended.* This would have caught today's problem at its real cause.

**D8. Hourly pay with overtime: a fact, not an alarm, until a rule passes D6.**
- For a payer like Harmon, the working picture shows the plain figures: *"Harmon Packaging: $3,313 over the last 4
  weeks; the 4 weeks before, $4,320"*. No scenarios card and no budget proposal.
- A rule for this kind of pay comes back for ruling once one passes the shuffle test.

*Recommended.*

**D9. Lead with the money.** When the card does show, its first line is the drop in dollars a month and what
it leaves after bills, before any percentage. *Recommended* (Rob's note).
