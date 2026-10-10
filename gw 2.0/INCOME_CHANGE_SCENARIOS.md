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
