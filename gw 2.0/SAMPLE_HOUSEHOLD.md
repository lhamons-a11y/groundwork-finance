# Item 105 — A sample household to look around in

**RULED 2026-10-20 by Rob:** *"we need test data can you add that please. Also that way if I want to send this for
people to review I think sending them test data would assist them to get an understanding of the software."* And:
*"well remember they will get the welcome screen on first launch."*

## What it does (S1-S5)

**S1. On the welcome screen.** "Let's begin." offers *Look around with a sample household first* above importing,
setting up by hand and restoring. It goes only into an empty Groundwork - no budget, accounts, debts or transactions -
so a household's own records and the sample never mix. A reviewer needs no file and no setup.

**S2. The Morgans, whole.** Sam and Jordan Morgan - made up, as is every business named - renting, two paychecks every
other Friday, fourteen budget lines, a credit card, a car loan and a student loan (each with six months of balance
history in the Historian's `debt_balance_history`), six months of everyday spending up to today (about 235
transactions on a checking account, a savings account and the card), three funds priced by hand (no lookup leaves the
computer), two savings goals, three gift occasions, a medical bill they said is theirs, and net worth history. Built
through Groundwork's own routes (`core/sample_household.py`), so every record is shaped as the app shapes it; the
same seed every time, dated from today.

**S3. Something to explain.** This month's Restaurants is five visits making exactly $500.00 against a $300 line - the
figure that opens its transactions in a grid (item 103), and that "why is restaurants so high" answers.

**S4. Only the sample can be cleared.** The sample's own load is the only thing that marks records as the sample (the
settings route refuses the mark), so "Start with my own" can never clear a household's real records. It clears the
sample - and anything added while looking around - keeps the accepted terms and the AI and backup choices, and the
welcome screen comes back.

**S5. Always said.** While the sample is here, a small notice at the foot of every page says "Sample household (made
up)", with *Start with my own*.

## Found on the way (fixed)

- The Dashboard read the debts' balance history only once the Budget page had been opened, so until then it said
  "balances unverified" whatever the history held. It is read at boot now.
- The item 35 note ("Investment valuation changed ...") was written on a brand-new household's first snapshot, where
  there is no earlier line for it to explain. It now needs an earlier snapshot.

## Status

Ruled and built 2026-10-20 (s249). Checked in the browser from a fresh install: terms, the AI choice, "Let's begin.",
the sample, every page without an error, Health showing the bill as owed, the notice.
