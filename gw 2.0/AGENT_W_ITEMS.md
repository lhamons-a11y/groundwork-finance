# Item 65, part 2: the five capabilities still open (W1, W2, W3, W5, W9)

Opened 2026-10-12 (Rob: *"write up item 65 for ruling"*). `AGENT_PRINCIPLES.md` Part 5 lists W1–W10 as an unopened
menu. Five are already built through other items:
- **W4** (why on every figure): the transparency standard, item 39 U7, and every item since.
- **W6** (reading bills in Groundwork's window): item 68.
- **W7** (questions in the person's own words): item 72.
- **W8** (refunds followed through): items 50 and 72 stage 4.
- **W10** (a monthly reflection): item 75.

**RULED 2026-10-12 (Rob: "approve as recommended"): every point, and the order (W3, W2, W1, W5, W9).** Building is authorised by Rob's 2026-10-11 "build ... item 65": each item is built, gated and accepted before the next. Each one is held to the rules in force:
- the agent principles (AP1–AP11, TM1–TM8, RG1–RG6);
- no silent learning: an observation persists only once it has been shown;
- absence is not zero;
- null-model a heuristic before shipping it;
- the transparency standard;
- teach the question, never a verdict;
- the horizon: every one is a step toward financial independence, on the person's own goal.

## W1. Patterns from the first import

**What exists (measured 2026-10-12, master).**
- `detect_recurring_patterns`: 3+ charges in 6 months, within 5%. It feeds the recurring charges, the Before You Buy
  and solution levers, and item 61's starting budget.
- The dashboard's seasonal alert reads `S.profile.seasonal.flags` (B6d): *"X typically runs higher in December"*.
- **Nothing looks at a long first import as a whole:** annual bills, renewals, a December that always runs high,
  insurance paid twice a year. A twelve-month import is read exactly like a one-month one.

**Proposed.** When an import brings 10 or more months of history, Groundwork offers one look-through, on the
person's tap:
- **Yearly or twice-yearly charges:** the same payee, about 12 or 6 months apart, similar amount. *"Geico: $612 in
  March 2025 and $598 in September 2025. Looks like it renews every six months."*
- **Heavy months:** a month whose spending stands above the year's middle month in a way the null model says is not
  chance. Its biggest categories are named, as facts.
- **Each finding lists its records,** and is asked: *"Is this a regular bill?"* Yes / No / Not sure.
- **Only a yes keeps it:** as a bill with its next date (for W3), or as a known cost (for item 66's futures).
- **"Not sure" and "No" are kept as the person's answer,** so the same finding isn't asked about again.

**Points.**
- **W1-a. A null model first.** The rules for *yearly* and *heavy month* are simulated against trend-free and
  realistic synthetic years before they ship, to the bar the item 71 rules met. A rule that is a coin flip there is
  not shipped. *Recommended.*
- **W1-b. Asked, never assumed (no silent learning).** Nothing found changes a budget, a plan or a future until the
  person says yes. *Recommended.*
- **W1-c. Enough history, or it says so.** Under 10 months: *"Groundwork needs about a year of history to see
  yearly bills."* *Recommended.*

## W2. Price changes on recurring bills

**What exists.**
- Recurring charges are known.
- Item 68 reads a bill's amount from the biller.
- The monthly report compares a category with EIA market prices.
- **Nothing says when a recurring charge's price changed.**

**Proposed.** When a recurring charge's amount steps to a new level and stays there for 2+ charges, it is shown as a
fact: *"Netflix: $15.49 through July, $17.99 since August (2 charges)."*
- The old and new amounts and dates come from the records, and the records are listed.
- **The reason is never invented.** Where the evidence allows, it says what kind of change it was: a billing
  frequency change (monthly to yearly), or a usage bill (utilities, via the EIA price for the same months). Otherwise
  it says only that the amount changed.
- **One tap** updates the budget line to the new amount, shown first, with Undo. Nothing changes otherwise.

**Points.**
- **W2-a. A step, not noise.** A change counts after 2 charges at the new level (one odd charge isn't a new price),
  and when it is more than the payee's own normal swing. That is item 71's lesson for paychecks, and it is
  null-modelled the same way. *Recommended.*
- **W2-b. No reason invented** (RG and AP rules). *Recommended.*
- **W2-c. Where it shows:** the Sunday check-in (item 76) the week it is seen, and a *Price changes* list on the
  Budget page. Each is shown once, then kept in the list. *Recommended.*

## W3. An upcoming calendar from the record

**What exists:** dates are spread over many places.
- The dashboard's Upcoming card (bills and debts 7 days out, gifts 30 days out).
- The Sunday check-in's week ahead.
- Bill due dates (item 68), gift occasions (item 74), fund deadlines, going trips (item 61), debt due days.
- **There is no one view of the months ahead.**

**Proposed.** A **Calendar** page: the next 90 days by week, then by month for the rest of the year. Every entry
carries its kind:
- **Confirmed:** a date the person entered or a biller stated: a bill due date read and confirmed, a gift occasion,
  a trip, a fund deadline.
- **Expected:** a recurring charge's next date, worked out from its record (*"about the 14th, from the last 6
  months"*).
- **Possible:** a W1 yearly bill the person said yes to, with its usual month.
- **Never inferred:** no event is inferred from purchases (TM5). A birthday is there only if the person entered it.

Each entry links to where it lives. With AI off it works the same: it is all dates and amounts.

**Points.**
- **W3-a. The three kinds, never mixed, each labelled.** *Recommended.*
- **W3-b. A page, plus the dashboard card reading from it.** One source for upcoming dates, so the Upcoming card, the
  check-in and the calendar can't disagree. *Recommended.*
- **W3-c. No reminders or notifications** (TM6). The calendar is looked at; it doesn't nag. *Recommended.*

## W5. Cause and effect you can move

**What exists.**
- The Debt page's *What if* slider (extra a month toward debt) and the mortgage extra-payment slider, each on its own
  page.
- Item 66's possible futures (fixed scenarios plus stated possibilities).
- Before You Buy (one purchase) and item 61 (one trip).
- **Nothing lets the person move several inputs together and see the year change.**

**Proposed.** A **What if** panel on the Possible futures card. A few sliders on the person's own figures:
- monthly income;
- the monthly debt payment;
- monthly spending;
- a savings contribution;
- a one-time cost and its month.

Moving any of them recomputes the futures, the debt-free date and cash in a year through **the one engine**, shown
next to *as things are*, with each changed input named.
- Labelled *"a what-if, not a prediction"*.
- **Nothing is saved** unless the person taps *"Make this my plan"*. That shows exactly what would change (the debt
  payment setting, a budget line) and has Undo.

**Points.**
- **W5-a. One engine** (item 66's, with the month-by-month extra item 61 added). No second calculation. *Recommended.*
- **W5-b. The original plan is untouched** until a tap that says what it changes, with Undo (AP and TM rules).
  *Recommended.*
- **W5-c. The two existing sliders stay** where they are, and become shortcuts into this panel, so there aren't three
  ways of answering the same question. *Recommended.*

## W9. A year-end financial gathering

**What exists.**
- The Annual Summary report (a year of income, spending and top categories).
- The Investments page's tax summary (`/api/investments/tax-summary`: realized gains).
- Health spending in its categories, now behind item 45's H6 boundary.
- **Nothing gathers a year in one place for the person or their tax preparer.**

**Proposed.** A **Year-end packet** in Reports, for a chosen year:
- income by payer, from the record;
- totals by category;
- realized investment gains and losses;
- debt interest paid;
- charitable donations (the *Charitable Donations* category);
- health spending, included only on its own tick (H6 P3);
- the year's statements and documents Groundwork holds, listed;
- a page of *what this does not include*.

It is printable and exportable as a PDF or CSV, and stays on the computer.

**Points.**
- **W9-a. A summary, never tax advice.** It never says what is deductible or how anything is taxed. It says: *"These
  are the year's figures from your records. Your tax preparer decides how they are treated."* *Recommended.*
- **W9-b. Health only on its tick,** through the H6 boundary. *Recommended.*
- **W9-c. Complete or it says what is missing.** A month with no imports, or an account not imported, is listed as
  missing, never counted as zero (absence is not zero). *Recommended.*

## The order, if ruled

Each would be its own build, gated and accepted before the next, as items 74–81 were. **Proposed order:**
1. **W3**, the calendar. It gathers what exists, and W1 and W2 feed it.
2. **W2**, price changes.
3. **W1**, the first-import patterns, with its null model done first.
4. **W5**, the what-if panel.
5. **W9**, the year-end packet. It is most useful before tax season, in January.

## Not proposed

- No notifications or pushes of any kind (TM6).
- No inferring life events, people or reasons from purchases (TM5).
- Nothing that moves or pays money (TM1).
- No tax advice.

## Built: W3, the calendar (2026-10-12), awaiting acceptance

- **`core/upcoming.py`** is the one calendar. Each entry has a date, a kind, a title, an amount, a certainty and a
  source.
  - **Confirmed:**
    - each debt's due day, as entered;
    - the person's own recurring bills;
    - bills read from their page (item 68);
    - every gift occasion (item 74);
    - trips the person is going on (item 61);
    - savings funds' dates.
  - **Expected:**
    - pay from each employer's own schedule (never a payer that is overdue);
    - steady monthly charges the ledger shows and no budget line names: 3 or more, within 5%, about a month apart.
      These say *"about the 9th, from the last 6 months"*. A weekly purchase is not a monthly bill.
  - **Possible:** yearly bills the person said yes to (W1's answer, in `yearly_bills_json`), in their usual month.
- **The Calendar page** (Track → Calendar): the next 90 days by week, then month by month for the year. Each entry
  shows its icon, date, title, where it came from, the amount, and a *Confirmed / Expected / Possible* tag, and links
  to the page it lives on.
- **W3-b, one source.**
  - The Sunday check-in's week ahead now reads the calendar, not its own date arithmetic.
  - The dashboard's Upcoming card reads it too (`/api/calendar?days=7`). Confirmed bill readings now reach the card,
    which they never did. A debt already paid this month still stays off.
  - s210 checks that the check-in's week and the calendar's week are the same.
- **W3-c.** No notification, timer or model call on the page.
- **Tests:** s210, 9 checks. s195 (the check-in) still passes on the shared source.
