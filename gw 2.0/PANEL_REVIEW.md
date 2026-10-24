# The simulated user panel: what it found, what is fixed, what needs a ruling (item 112)

Opened 2026-10-24 (Rob: *"here are the results from the simulated review and issues that was detected"*, then *"start
on the High ones then move through the rest of the list"*). The review: ten made-up households run through 24 months
of the real server (`groundwork-panel-sim-files.zip`: harness, personas, 90 journal entries, 25 issues).

**What the panel liked:** no one was ever shamed (all ten); interest as dollars a month; honest fund pace and "did not
hold" readings; the Health module (bills owed only when you say so); every figure saying where it came from;
privacy that can be checked.

---

## 1. Fixed (2026-10-24), held by s260

| # | What | Commit |
|---|---|---|
| I-01, I-04 | Debt payments are budgeted wherever they are spent: one rule (`_debt_month_plan` / `_debtMonthPlan`: the payoff plan, never below the minimums; the minimums with no plan) in the check-in, Before You Buy, the income futures, the Budget page; a debt payment is never offered as a purchase or priced as the month's biggest charge | 347cc79 |
| I-03, I-06 | A payoff that can't be dated is said, never a 500: below the minimums by $X (with "Use my minimums"), or never clearing (including the 30-year cap). Found on the way: the budget typed on Debt Payoff never reached the server's `monthly_budget`; it is saved as it is typed | 83b1f1b |
| I-05 | A debt the record brings to $0 is asked about ("Is it paid off?"), dated when it reached $0; $0 counts as a real balance in the Trophy Room | fd421a6 |
| I-02 | Each trophy held to its own description (10%, half, a real crossing, three rises in a row, all three of Groundwork laid) | 523a296 |
| I-07 | AI on only when chosen; an install that had it on by the old default keeps it, written once | 523a296 |
| I-08 | The schema pin reads the same on Python 3.12, 3.13 and 3.15; re-pinned without a version bump | 523a296 |
| I-16 | One "freed minimums" figure, against the minimums on record | 523a296 |
| I-17 | Payments on record short of the plan for three full months: Debt Payoff says so, with the date at that pace | 523a296 |
| I-22 | "Whose pay" asked only of a household of two | 523a296 |
| I-18 | Facts, not advice: the Budget's grades and to-do lines, the 15-20% savings target and its colour grade, "Consider checking" | f3865b3 |
| I-19, I-20, I-21 | The said-history count; no price dated after today; trophies earned together in one toast, at most three toasts | f3865b3 |

**Already fixed before the review reached us:** I-09 (parity, passing), I-10 (item 109), I-15 (item 110 V1), I-24
(`unique_path`), I-25 (3608760).

---

## 2. For ruling (no code)

**P1 (I-11). Pay with no rhythm is asked about, and read by the week.** Ray's Uber pay was "unknown" for 24 months, so
every income feature skipped him. Proposed: a payer with deposits several times a week and no schedule goes to the
same "ask" path weekly contractors get; and variable pay is read as a weekly-earnings view - a typical week, a low
week and a high week, from the last 13 weeks - never as a monthly figure it doesn't have. *Recommended.*

**P2 (I-12). No brake on spending a fund was saving for, and "I had to" describes rather than prices.** The brake
priced a $2,900 hotel as "8 months on your debt-free date" while a fund the app tracked had saved for that trip, and a
$900 brake repair at "2 months". Proposed:
- (a) a charge that matches an active fund (its name, or within 10% of its balance) is shown as "paid from your
  Honeymoon fund", never priced;
- (b) the person can mark a charge "had to" (car, home, health): described ("a $900 repair"), not priced.

*Recommended, both. (b) is the person's statement, kept like every other.*

**P3 (I-13). A fund notices what it paid for.** After the roof and the house closing were paid, the funds still said
"18 months to go". Proposed:
- When a large charge is within 10% of a fund's balance or target, Groundwork asks "Is this what you were saving
  for?". A yes spends it from the fund and closes or reduces the fund.
- A deposit over the target is shown as over, never quietly capped: today `min(target, current + amount)` drops the
  extra from the record.

*Recommended.*

**P4 (I-14). In Household mode, who changed what.** Darnell cut Restaurants and Keisha put it back; the working
picture read "restored: something you keep". Proposed:
- Each budget edit records which partner made it, when Household mode is on.
- When one partner reverses the other's edit, Groundwork asks "Is this a shared decision?" instead of concluding.
- Until it is answered, the reading is "undecided", never "sacred".

*Recommended (it fits item 92's named people).*

**P5 (I-23). Accessibility, then a real audit.** Proposed now:
- Words on every colour state ("$13.67 over", not only a red bar).
- Caption text raised to WCAG AA contrast.
- A one-line text summary under each chart.

Then a session with screen-reader users (NVDA, JAWS, VoiceOver), which Rob would need to arrange. The panel was
clear that screenshots are not a test. *Recommended.*

**P6. A simple mode and larger text.** Harold: *"A simple mode with only the pages I use."* Proposed:
- A Settings choice that shows only Dashboard, Ledger, Budget, Debt Payoff and Settings. Every page stays one click
  away under "More".
- A text-size setting (100 / 115 / 130%).

*Recommended as its own item; the page list is Rob's call.*

**P7. Outside help, and a printable summary.** Proposed:
- (a) A plain "Outside help" page: NFCC, 211, the CFPB, and legal aid by state, reached from the ? help. Item 104 has
  these numbers for the crisis words already; this makes them findable without a crisis.
- (b) "Print this session": the check-in's facts and the month's figures on one page, for a counsellor or a partner.

*Recommended, both.*

---

## 3. Ruling sought: Rob

1. **P1-P4:** build as proposed, in the order P2 (smallest), P3, P1, P4?
2. **P5:** the three page changes now, and will you arrange a screen-reader session?
3. **P6:** its own item - which pages make the simple list?
4. **P7:** (a) and (b), or one of them?
