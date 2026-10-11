# Item 76 — The Sunday check-in: the week behind, the week ahead, and why it matters

Opened 2026-10-11. Rob, with a screenshot of today's check-in:

> *"when it comes to AI narration like sunday check-in we should have the agent run those processes at midnight or
> middle of the night if two things are true that the import is not older then 48 hours or more and that the import
> did not happen post ai narration. Also, I feel like we can make this more meaningful than what we are showing the
> user. We are not showing why this is important and why this matters. Not telling users that they should put every
> penny into paying off interest rates but have a comparison between weeks like yes this is higher than last week but
> those savings from the previous weeks have you still have $XXX.xx remaining this month. Also we can give what is
> know in the week ahead since we have the agent getting bills scheduled. Sunday check-in can become what we hoped a
> look back at the previous week and what's ahead this week and since we can look at the ledger and see a paycheck
> will happen this week that can be a notice that this week Groundwork expects 'Both Partner's and Rob's pay period
> to be deposited this week' ... if a deposit stops showing up like that Sunday check-in the following week does not
> mention it. Until Deposits start happening again."*

**Points S1–S10 for ruling. No code yet.**

## 1. What is true today (measured 2026-10-11, master d339ac1; Rob's screenshot)

Rob's check-in read: *"This week: $2,242.71 spent — $514.74 over your weekly pace. Transfer was the biggest category
at $1,329.25. The debt cost $93.69 in interest this week."*

- **Transfers count as spending.** Every debit in the last 7 days is "spent", including $1,329.25 of Transfer, which
  is money moved between Rob's own accounts. Most of the "$514.74 over" is that transfer.
- **"Weekly pace" isn't the budget.** It is the budget's monthly income ÷ 4.33, so the line compares spending with
  income, and "over" reads as a verdict with no reason.
- **It looks only backward, at one week.** It has no comparison with last week, nothing about the month so far, and
  nothing about the week ahead.
- **The written part is made on the spot.** `renderSundayCard` asks the AI when the dashboard opens on a Sunday,
  while the person waits. The screenshot is the version without AI.
- **What Groundwork already knows about the week ahead:**
  - bills and their due days: recurring bills, item 68's bill readings, and card due dates;
  - each employer's pay schedule (item 71 amendment D3: weekly, every two weeks or monthly, with the last date).

## 2. Points for ruling

**S1. Written overnight, only when there is something new (Rob's rule).**
- Groundwork writes the check-in's written part in the middle of the night (about 2 a.m.), when the app is running,
  and only if:
  - the newest import is under 48 hours old, and
  - nothing has been written since that import.
- What is written is saved and shown when the dashboard opens.
- When the app wasn't running overnight, or the rule didn't hold, the check-in shows its facts (S9), and *Write it
  now* is there.
- This is narration on this computer, not a bank visit, so TM2 is untouched.

*Recommended.*

**S2. Item 75's monthly review follows the same overnight rule.**
- Item 75 M6, as ruled, writes the review right after the import finishes.
- Moving it overnight under S1's two conditions makes one rule for all background narration.

*Recommended, but Rob's call.* It changes M6, which he ruled.

**S3. Spending means spending.**
- Transfers between the person's own accounts, and payments to their own cards, are left out of "spent" and named
  separately: *"$1,329.25 moved between your accounts (not spending)."*

*Recommended.* It fixes the screenshot's biggest number.

**S4. The week behind, against last week and against the month.**
- *Examples; only $913.47 is real ($2,242.71 less the $1,329.25 transfer). The rest are invented.*
- *"$913.47 spent this week, $210 more than last week."*
- *"This month so far: $2,471 of the $3,567 budgeted, with $1,096 left for the 20 days that remain."*
- *"The weeks before were lower, so the month still has room."* Said only when the arithmetic shows it.
- Every figure is from the record, compared like for like. No verdict words such as "over your pace", "great" or
  "bad".

*Recommended* (Rob's "this is higher than last week but … you still have $XXX remaining").

**S5. Why it matters: one line that teaches, never a command.**
- *Example figures.*
- Each check-in names one mechanism the week's figures show, conditionally. For example: *"The $93.69 of interest
  this week is about $406 a month at these balances: money the balances cost, whatever else is paid."*
- No "pay every penny" and no ranking of what to do (teach the question).

*Recommended.*

**S6. The week ahead: bills due.**
- *"Due this week: AEP Ohio (about $260, Oct 20), Harbor Amazon ($73 minimum, Oct 12)."*
- Taken from recurring bills, bill readings and card due dates, each with where its figure came from.

*Recommended.*

**S7. The week ahead: pay expected, from history.**
- *"Groundwork expects Rob's and Partner's pay this week."* This comes from each employer's own schedule (item 71
  D3); it is not a guess.
- Which person an employer's pay belongs to is **asked once** (*"Whose pay is City of Millbrook?"*, AP4), then used.
- With no answer yet, the employer's name is used.

*Recommended.*

**S8. A paycheck that stopped is not mentioned (Rob).**
- When an employer's deposit is overdue (item 71 D7's *missing*), the check-in says nothing about it: no "expected",
  no "missing". It stays quiet until deposits come in again.
- The Budget page's *Your pay* card still asks about it, once.

*Recommended* (Rob's rule). It also keeps the check-in from repeating something that may hurt to read.

**S9. AI off, and when the written part fails.**
- S3–S8 are facts written by the engine, and they are the check-in with AI off.
- With AI on, the written part sits above them, through the voice check (R1–R11). A failed written part is left out,
  and the facts stand.

*Recommended* (A10, item 64).

**S10. Lines and tests.** Master only. Tests:
- a transfer is not spending;
- week-over-week and month-to-date figures add up;
- bills and pay land in the right week;
- a missing employer is silent;
- the overnight rule runs only when both conditions hold, and only once per import;
- AI off shows the facts;
- no verdict words.

*Recommended.*

## 3. Not decided here

- **A daily or mid-week check-in.** Not proposed.
- **Notifications.** None. The check-in is on the dashboard when the person opens it (TM6).
