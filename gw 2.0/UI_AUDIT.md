# Item 79 — A UI audit: pages that are too busy

Opened 2026-10-11. Rob: *"I think many of the pages are looking too busy. Lets take an audit after the work is
completed and resolve any UI looks that could be changed."*

**Opened to run after item 78 is built. No code. The audit's findings come back as points for ruling before
anything changes.**

## 1. Why now

Recent items each added a card to a page:
- the income card and *Your pay* on Budget;
- *From your records*, *Trials and return windows* and *The full cost, and financing* on Before You Buy;
- the *Paid back by work* card on the Ledger;
- Needs attention's fourth kind on the dashboard;
- the evidence cards on goals and the debt plan.

Each was right on its own. Together, some pages are long stacks of cards. Item 77 fixed whether the text can be read;
this item is about how much is on each page at once.

## 2. How the audit is done (measured, on a copy of Rob's data)

For every page:

- **Count:** cards, sections, buttons and words on first view and in total, and the scroll length in screen heights.
- **First view:** what is visible without scrolling, and whether that is what the page is for.
- **Repetition:** the same figure or message shown in two places on one page, or on two pages.
- **Empty or rare cards:** cards that are usually empty, or only matter once in a while, and take space every day.
- **Order:** whether the most-used or time-sensitive part comes first.
- **Consistency:** tabs on one page and stacks on another, button styles, headings, spacing.
- **Screenshots** of each page, before.

Pages: Dashboard, Budget, Ledger, Before You Buy, Debt Payoff, Trip Planner, Gift Budget, Investments, Net Worth,
Assistant, Working picture (after item 78), Settings, Reports.

## 3. What comes back

A page-by-page list of findings, each with a proposed change and a reason, as points to rule on. Typical changes:
- tabs where a page has distinct jobs;
- folding rare cards behind one line;
- merging repeated figures;
- moving the time-sensitive part to the top.

Nothing is removed without Rob's ruling. The transparency standard holds throughout: every figure keeps its working
and its source; only the layout changes.


## 4. Measured, 2026-10-12 (Rob: *"ok to build all"*; the audit, no code)

**Setup:**
- a copy of Rob's real database, AI off (`scratchpad/audit_server.py`);
- the browser at 1280 x 800, a common laptop screen;
- every page opened in turn;
- only cards that are shown and not nested were counted;
- a page's length is in screens of 800px.

| Page | Screens long | Cards | Buttons | Words | What fills the first screen |
|---|---|---|---|---|---|
| Debt Payoff | **11.1** | 4 | **143** | 1,725 | path to zero, payment budget, strategy, the start of *Your cards & loans* |
| Calendar | **11.4** | **24** | 0 | 2,147 | the next three weeks |
| Budget | **10.7** | 12 | 35 | 1,780 | **Possible futures only** |
| Ledger | 4.9 | 1 | 13 | 1,013 | *What that one cost*, then the table |
| Trophies | 2.5 | 1 | 0 | 750 | |
| Settings | 2.2 | 6 | 10 | 907 | Speaking up, Household, AI features, **AI narrative gate health** |
| Net Worth | 2.1 | 5 | 5 | 256 | current net worth, assets, liabilities, update balances |
| Dashboard | 2.0 | 6 | 14 | 478 | Needs attention |
| Reports | 1.8 | - | - | 223 | the catalogue |
| Assistant | 1.7 | 2 | 40 | 854 | Get my accounts |
| Trip Planner, Investments, Before You Buy | 1.4-1.5 | 2-3 | 4-7 | 181-231 | |
| Gift Budget, Working picture | under 1 | | | | (the picture opens on *Needs you*) |

**Three pages are far longer than the rest:** Debt Payoff, Budget and Calendar, at 11 screens each. Everything else
fits in two or three.

## 5. Findings, as points for ruling (nothing changes until ruled)

Each point says what was measured, the proposed change, and why. **The transparency standard holds:** every figure keeps
its working and its source; only where things sit changes. Nothing is removed.

**U1. Budget opens on the futures, not the budget.**
- The first screen is all *Possible futures*: two charts and four scenario cards, 957px.
- *Income* and *Expenses* begin below it. *Expenses* alone is 3,305px.
- The page's 12 cards do three different jobs:
  - the plan: Income, Expenses, Debt Payments, Saving toward, What's Left, What these amounts cost;
  - the futures: Possible futures, A starting budget from your record;
  - the bills and charges: Bills read from their own website, Price changes, Recurring charges detected, Sinking
    funds.
- **Proposed:** three tabs, using the tab bar the Assistant and Working picture already use: *Your budget* (opens
  first) / *Possible futures* / *Bills and charges*. Anything waiting on the person, such as a price change to apply,
  puts a plain count on its tab, as *Needs you* does.
- *Why:* the page people open most should open on what they came for.

**U2. Debt Payoff shows every debt fully open.**
- *Your cards & loans* is 8,280px with 143 buttons. Each of the 11 debts shows its whole editing form at once: type,
  balance, APR, minimum, due day, account link, balance check, *Estimate APR*, notes, balance history and the manual
  ledger.
- A debt already paid in full (TJ Max) sits first, fully open.
- **Proposed:**
  - each debt is one line (name, balance, APR, minimum, payoff month) that opens on a tap, as the Assistant page's
    accounts do (item 69);
  - debts paid in full move to the end, under *Paid off (n)*.
- *Why:* about a screen of summary instead of nine screens of forms. The forms are one tap away.

**U3. The Calendar is 24 cards, 11 screens.**
- Every week for 90 days is its own card, then each month to a year out.
- **Proposed:**
  - the next four weeks open;
  - the rest folded by month (*November: 14 dates, $3,210*), each opening on a tap.
- *Why:* the near weeks are what the page is for. The rest is there when looked for (W3-c: looked at, never pushed).

**U4. Settings puts the AI gate's statistics on the first screen.**
- *AI narrative gate health* (788px, a table of rule names like `R8_number_provenance`) sits beside *AI features*.
- It is a developer's measurement, not a setting.
- **Proposed:** fold it into one line under AI features (*"55 answers held back in 30 days. Details"*).
- *Why:* Settings is for settings. The numbers stay one tap away.

**U5. The dashboard's *Needs attention* repeats itself.**
- On Rob's data:
  - four separate rows say an account was *"last imported ... days ago"* (Apple Card, Cashback 6862, Superior
    Savings and one more), each with *Import* and *Dismiss*;
  - two more rows (*Net worth can't be assessed*, *Debt progress can't be assessed*) have the same cause: balances
    not verified.
- **Proposed:**
  - one row for stale imports (*"4 accounts haven't been imported for 90+ days"*) that opens the list;
  - one row for the unverified balances, naming both things it blocks.
- *Why:* the same message six times makes the one different item (the Harbor Amazon payment due today) easy to miss.

**U6. Repetition across pages:**
- **Recurring charges** appear in three places:
  - *Recurring charges detected* (Budget);
  - *Price changes* (Budget);
  - the Calendar's *Expected* charges.

  Each uses a different rule: the old detector checks 3 charges within 5%; W2 and W3 use their own.
- **Upcoming dates** show on the dashboard's card and on the Calendar, from one source (W3-b). Not a duplicate of
  logic, only of place: fine.
- **Proposed:**
  - *Recurring charges detected* uses the Calendar's monthly rule (3+ months, about a month apart), so the Budget and
    the Calendar never disagree about what recurs;
  - the card links to the Calendar.
- *Why:* two lists of "your recurring charges" that disagree teach the wrong lesson.

**U7. Consistency.**
- The Assistant, Working picture and Debt Payoff use tabs; Budget and Calendar are stacks.
- Section headings mix CAPS labels (*POSSIBLE FUTURES*) with sentence-case card titles.
- **Proposed:**
  - tabs wherever a page has distinct jobs (U1), with the same tab bar;
  - one heading style (the existing small-caps card label) for every card.
- *Why:* one way of finding things.

**U8. Left as they are:**
- Dashboard, Net Worth, Investments, Trip Planner, Before You Buy, Gift Budget, Reports and Trophies are each two and a
  half screens or less, and open on what they are for.
- The Ledger is long because it is a table of transactions. That is its job, not clutter.

## 6. Status

- **Measured 2026-10-12. U1-U8 for Rob's ruling.** No code changes until each is ruled.
- Before screenshots were taken in the audit. They are retaken after each change, so before and after can be compared.

## 7. Ruled and built

- **U1 RULED 2026-10-12** (Rob: *"I accept u1"*) and **BUILT 2026-10-12** (s219), **ACCEPTED 2026-10-13** (Rob: *"I accept both"*).
  - The Budget page now has three tabs, using the Assistant's tab bar: *Your budget* (opens first: income-change
    scenarios, trips this month, the budget), *Possible futures* (the futures card and the what-if), and *Bills and
    charges* (bills read, price changes, recurring charges, savings funds).
  - Every card is kept.
  - The guide's *Open it for me* and the what-if shortcuts open the right tab first.
  - A price change waiting for a tap is a plain count on its tab.
  - Measured on a copy of Rob's data: the first screen is now the budget itself (income, out, left; the income
    lines), not the futures charts.
- **U2-U8 RULED 2026-10-13** (Rob: *"I agree with the UI proposals u2-u8"*). Each is built, gated and shown before the next.
- **U2-U7 BUILT 2026-10-13** (s222), awaiting acceptance.
  - **U2:** each debt starts as its one-line summary: name, balance, APR and minimum, payoff month, ▾ Show. A debt just
    added opens; paid-off debts sit at the end under *Paid off (n)*.
  - **U3:** the Calendar's next four weeks are open. Every month after is one line (*"November 2026: 10 dates,
    $609.03"*, the first one *"Rest of …"*), opening on a tap.
  - **U4:** the AI gate's statistics are one line under AI features (*"No AI answers held back in the last 30 days.
    Details"*), with the table on a tap.
  - **U5:** Needs attention puts stale imports in one row (*"3 accounts haven't been imported for 93+ days"*, with
    the list on a tap and each item keeping its own Dismiss). Conclusions answered by the one Verify step are one row,
    naming each one's own missing input.
  - **U6:** one rule for a recurring charge (`core/upcoming.recurring_charges`: 3+ months of the last 6, about a month
    apart, within 5%). The Budget card (`/api/calendar/recurring`) and the Calendar both read it.
    - Debt payments, interest, fees, transfers and savings are not recurring charges: a debt is on the calendar by
      its own due day.
    - On Rob's data: Auto Finance A, Heidt Veterinary and Netflix. The old card's own detector listed loan payments and
      interest charges.
  - **U7:** the cards with their own heading style now use the card label: Investments' three, Debt Payoff's *Your
    path to zero*, Net Worth's *Current net worth*, and Trophies' money story.
  - **U8:** no change, as ruled.
- **Measured after, on a copy of Rob's data at 1280 x 800:**

  | Page | Before (screens / buttons) | After |
  |---|---|---|
  | Debt Payoff | 11.1 / 143 | **1.9 / 32** |
  | Calendar | 11.4 / 24 cards | **2.4** |
  | Budget | 10.7, opening on futures | 7.6, opening on the budget (U1) |
  | Dashboard | 2.0 / 14 | 1.6 / 9 |
  | Settings | 2.2 | 2.2, the gate statistics one line |

  There were no errors on any page.
