# Groundwork: a brief for reviewers (build of 2026-10-22)

This brief goes with the 15 screenshots in this folder. It is written so a reviewer who has never seen Groundwork
(a person, or an AI running user-group simulations) can judge it.

## What Groundwork is

Groundwork is a **free personal-finance app** for Windows, macOS and Linux, for people getting out of debt and
starting to build wealth.

- **Local and private.** Everything runs and is stored on the person's own computer. There are no accounts, no cloud
  and no ads, and nothing is sold. The optional AI also runs on the computer, on its graphics chip where it can (Metal
  on a Mac), and nothing is sent anywhere.
- **The horizon is the person's own financial independence, as they define it.** Groundwork never imposes a number
  or a one-size plan.
- **Three steps run through the program:** get out of debt, budget wisely, then invest and build net worth.
- **Freeware on purpose.** There is nothing to sell, so the only thing it has to offer is the truth.

## The rules it holds itself to

These are what a reviewer should test the screens against.

1. **Math-true or silent.** It never invents a number. When the data isn't there, it says so; it doesn't guess.
2. **No new debt as a solution.** It never suggests a credit card, a loan, a balance transfer or buy-now-pay-later.
3. **No "just earn more."** Every option works within the money the person actually has.
4. **Show, don't scold.** No verdicts ("good", "bad", "should", "healthy"), no guilt, no tough love, no cheerleading.
   It says what happened and what would change it, and the person decides.
5. **Proof, not persuasion.** Every claim comes from the person's own record, with the rows behind it.
6. **It speaks first rarely.** At most one unprompted item per session and two "brakes" a week, only when the impact
   is material, and every one can be dismissed. There is a *Speaking up* dial: Normal, Fewer or Off.
7. **It asks; it doesn't assume.** Facts about other people and life events are asked, never inferred. Nothing is
   learned silently from how the app is used.
8. **The AI only phrases.** The engines do the math. The model puts pre-computed facts into words, and a "voice check"
   blocks any sentence with a number that isn't in the facts. With AI off, every page still works.

## The sample household in the screenshots: the Morgans (made up)

- **Who they are:** Sam and Jordan Morgan, two paychecks (about $8,515 a month together), six months of history.
- **Accounts:** Everyday Checking, High-Yield Savings, a Brokerage account (VTI, VXUS, BND), and a Cashback Visa.
- **Debts:** the Cashback Visa ($3,840 at 24.99%), the Riverside Auto loan ($14,200), and a Student loan
  ($18,750). They are about 31% of the way through their starting debt, and debt-free in Aug 2030 on avalanche at
  $900 a month.
- **Planted on purpose, for review:**
  - **Restaurants this month:** $500 across five visits, against a $300 budget.
  - **A medical bill:** Northside Urgent Care, $285.40.
  - **Streaming, said and done differently:** they marked Streaming *flexible*, then cut it and put it back, so the
    *Working picture* asks which they mean.
  - **StreamBox from two accounts:** paid from both Checking and the Visa, so *Needs attention* says so.
- **The badge on every page:** *Sample household (made up)*, with *Start with my own*.

## The screenshots (taken 2026-10-22 at 1440 px wide, AI on, running on the Mac's graphics)

| File | Page | What it does |
|---|---|---|
| 01_dashboard | Dashboard | *Needs attention*, dated facts only (payments due, stale imports, a charge paid from two accounts...), each with its source and Dismiss. Summary tiles: what changed since last month, this month so far, debt progress, minimums dropping, spending, investments. An AI-written *Projection*. |
| 02_assistant | Assistant | Fetches downloads from each bank and bill site, but only when asked and while the person watches. Passwords stay in the computer's own vault. *Check my records* looks for mis-filed money. |
| 03_working_picture | Working picture | What Groundwork has concluded about how the person handles money, and what they have told it. Here it asks a question where what they said and what they did disagree. |
| 04_ledger | Ledger | Every transaction, by day. *Recurring patterns spotted* (now one line per account where a payee is paid from two), import, reconcile, dedup. |
| 05_budget | Budget | Income and expense lines with spent, projected and budget for each, by category. |
| 06_health | Health | Medical bills recorded as the provider's statements, the plan year, a reserve, HSA/FSA, and what each payment plan would leave. *Recorded, never judged.* |
| 07_calendar | Budget, Calendar tab | What is coming from the person's own record: due dates, paydays, recurring bills, each marked *Confirmed*, *Expected* or *Possible*. |
| 08_before_you_buy | Before You Buy | What a purchase does to the month and to the debt-free date, before deciding: vehicle, subscription, credit purchase or other. |
| 09_trip_planner | Trip Planner | A trip planned to fit the budget, learning from a past trip's real spending, or reading a pasted quote. |
| 10_debt_payoff | Debt Payoff | The path to zero (Aug 2030), avalanche or snowball, each card and loan, and what paying extra would do. |
| 11_investments | Investments | Holdings, value, gain, allocation, fee drag, realized gains. Prices are hand-entered in the sample. |
| 12_net_worth | Net Worth | Assets minus liabilities, the trend, and what the savings now cover. |
| 13_trophy_room | Trophy Room | Achievements, each with its proof from the record (*Earned Oct 22, 2026*, *paid down 7.9%*). |
| 14_reports | Reports | Progress, spending, debt, building and data reports. Some have an AI read, run on this computer. |
| 15_settings | Settings | *Speaking up* dial, AI on/off, the AI log (every request exactly as sent), budget defaults, *Your home*. |

## What changed in this build (2026-10-21/22)

- **Paid from two accounts (item 107).** When the same payee is paid from two of the person's accounts in the same
  month, more than once, *Needs attention* says what was seen. It never calls it a mistake. The person can answer
  *Both are meant*, *One of these should stop* or *These aren't the same*, and it never asks again about that pair.
- **Recurring charges read per account (item 108).** A payee paid from two accounts is two lines everywhere: the
  Ledger, the Budget card, the Calendar, price changes, yearly bills, Before You Buy and the debt plan's trims. A card
  switch is read as one charge that moved.
- **One clock (item 109).** Every date now comes from the computer's own local clock. Before, evening activity could
  be dated tomorrow, because UTC is ahead of US time.
- **The Ledger's count** now matches what a search or filter shows.
- **The top bar** keeps only the date, the Ask bar, Explain and ?.

## Known issues a reviewer should see

These are visible in the screenshots, found while preparing this pack, and confirmed in the code.

1. **The AI Projection on the Dashboard overstates, and wanders.**
   - **The fact it is given is wrong in kind.** The facts say "Redirect $287 → Cashback Visa: Aug 2030 → Aug 2029, 12
     months sooner, saves $1303". The engine treats this month's $287 restaurant overspend as $287 extra *every month,
     forever*. A one-time $287 would move the date far less.
   - **It is asked 4-5 times per page load.** The first time, the debt plan isn't ready, so the facts read "0 months
     sooner, saves $0". The answer changes as the page settles.
   - **The model adds claims the facts don't hold.** "Delaying debt freedom by one month" (or three), "a cashback
     credit card" for the Cashback Visa, and "redirecting all non-essential spending".
   - **The voice check misses them.** It only compares dollar amounts and percentages with the facts. Month counts
     and dates are not checked.
2. **Investments says "VTI is 67% of your portfolio — consider diversifying".** This is fixed wording from 1.0, not
   the AI. It is advice; the voice rules only check AI text.
3. **Debt Payoff says "Suggested $2,102.79 — keeps you in a healthy 50/30/20 split".** This is fixed wording from 1.0.
   "Healthy" is a verdict, and 50/30/20 is a one-size rule.
4. **The Ledger's *Recurring patterns spotted* lists transfers and loan payments** ("Transfer to savings", "Cashback
   Visa payment") with *Add to budget*. Transfers are known only by their category; the two sides of a move are
   never paired.

By design, not an issue: the Trip Planner's "No oil change found in your ledger" note. With no oil change in the
ledger in the last 90 days, it asks the person to check the oil before a long drive.

Fixed since these screenshots: the Calendar now shows paychecks as their deposits spell them ("Riverside Schools").
