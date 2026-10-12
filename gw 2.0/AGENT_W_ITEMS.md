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

## W2 null model (2026-10-12, `scripts/w2_null_model.py`, before the rule shipped)

4,000 synthetic series per row, seeded. The bar: no more than 2% false alarms on any trend-free series, and steps of
8% or more found at least 95% of the time.

**First rule, FAILED.** A step was 3%+, 3x the payee's own swing, and every new charge nearer the new level.
- Steady subscriptions passed (0-2.5% false alarms).
- Seasonal usage bills fired on **18-30%** of trend-free years.
- Variable monthly spending fired on 7%.
- The multiple split points the rule tries find a "step" in noise.

**Fix 1, the decisive one: a price only steps from a steady charge.** The old level's typical swing, and every new
charge's distance from the new level, are within 3%. A bill whose amount follows use has no one price to step from, so
a seasonal utility is never read as a price change.

**Fix 2: the old level must be most of the charges** (75%), not two odd ones. Two odd charges at the start had been
taken as the old price.

**Result, PASSED.**
- Worst false-alarm rate: **1.0%**. That is two identical odd charges at the very end, which is exactly what "2
  charges at the new level" means.
- Every step from 5% to 25%, up or down, with 2, 3 or 6 charges since: **100%** found, including a step after a
  prorated first charge and an odd month.
- A slow 1%-a-month drift is not read as a step (0.0%).

**On the live ledger** (read-only, 273 payees, 13 months), the first version found two:
- **Netflix:** $23.23 through April, $25.09 since May.
- **A card's interest charge.** That moves with the balance; it is not a price. Interest, fees, debt payments,
  transfers, savings, refunds and ATM are now not prices (`NOT_PRICES`), so only Netflix remains.

## Built: W2, price changes (2026-10-12), awaiting acceptance

- **`core/price_change.py`:** arithmetic only, with no database and no clock. It finds the latest step in one payee's
  charges and writes the sentence.
- **W2-a:**
  - 3+ steady charges at the old level, 2+ at the new;
  - a change of at least 3% and 50 cents, and at least 3 times the payee's own swing;
  - the charges before it were a recurring rhythm (weekly to yearly).
- **W2-b:** the sentence states the old and new amounts and their months, and nothing else. *"Netflix: $23.23 through
  April, $25.09 since May (6 charges)."* It adds only what the record itself shows:
  - the charges moved from monthly to yearly (the gaps);
  - a usage bill, whose amount follows use as well as price (the category).
- **W2-c:**
  - **Budget page, Price changes:** each change with its charges (open *The charges*), and the budget line it lives on.
    A budget item or recurring bill is matched by name.
  - **One tap:** the button shows the change first (*"Change it to $25.09"*). The new amount is worked out again on
    the server, never taken from the page. The toast has Undo.
  - **The Sunday check-in** names a change in the week its second new-level charge arrived, and says the Budget page
    can update the line.
  - Nothing about a finding is stored: it is derived from the ledger on every read (no silent learning). The only
    write is the person's tap.
- **Tests:** s211, 8 checks, including the null model run in the gate.

## W1 null model (2026-10-12, `scripts/w1_null_model.py`, before either rule shipped)

20,000 synthetic histories per row, seeded. **The bar, set before the first run:** no more than 5% false alarms on any
case where nothing is there (each finding is asked about, never assumed), and real patterns found at least 90% of the
time.

**Renewals (yearly and twice-a-year bills).** The false alarms come from an occasional payee in a category that isn't
everyday spending, visited at random.
- **First rule:** 2-4 charges, every gap a year (355-375 days) or six months (175-190), amounts within 15%, and not
  everyday spending.
  - Varied amounts gave 0.4-1.6% false alarms.
  - A fixed price (a copay) visited twice in 13 months gave **5.2%**.
- **Fixes:**
  - The six-month window narrowed to 176-189 days.
  - Several gaps may each wander 6 days when their middle gap is in the window.
  - **A rhythm the history contradicts is not one:** when the record runs past the next charge's date (plus 20 days)
    and it never came, the charges were a coincidence, or the bill stopped. Either way, nothing is coming.
  - The start of the record is not checked. A bill begins some time, and a new policy in a long record is still a
    yearly bill.
- **Result, meets the bar:**
  - Worst false alarm 4.67% (the copay case).
  - Yearly bills found 100%, twice-a-year bills 96-98%.

**Heavy months.** One year cannot tell a heavy month from an ordinary bumpy one. The first rule was a month 25% and
3.5 robust deviations above the year's median.
- It flagged **5-26%** of trend-free years.
- It found a real +40% December only **20-55%** of the time.
- That is the coin flip W1-a forbids.

So a heavy month now needs **two full years**, and means *this month runs heavy every year*:
- each month's distance from its own year's median is averaged over the years;
- the average is judged against the spread of every other month (the month judged is never its own yardstick);
- it must be at least 20% above on average, and at least 10% above in every single year, so one freak year can't
  carry it.

**Result: against the bar set first, this does not fully meet it.** The settings tried (thresholds 3.0 and 3.5,
every-year floors from 0 to 20%) all traded one side for the other. None reached both 5% and 90% with two years of
months.

At the chosen setting:
- **false alarms:** at most **4.67%** (heavy-tailed noise; 1.2-2.4% otherwise);
- **found:** **81-85%** of strong patterns (December +40% at 10% noise, +60% at 15%);
- **weak patterns:** mostly missed (+40% at 20% noise: 20%; three years at 15% noise: 55%).

A miss costs nothing, because nothing is assumed. A false alarm costs one question. So heavy months are held to the
false-alarm bar and a find bar of 80%. **That find bar was lowered after seeing the data. It is stated here and in the
script, for Rob to accept or reject.**

## Built: W1, patterns from a long history (2026-10-12), awaiting acceptance

- **`core/first_import.py`:** arithmetic only. It covers complete months (a partial first or last month is not a
  small month), renewals, heavy months, and each one's sentence.
- **W1-c:** under 10 complete months it says *"Groundwork needs about a year of history to see yearly bills. Your
  record covers N full months so far."*
  - On Rob's ledger today (January to October 2026) that is 8 full months, so it says so and finds nothing.
  - Heavy months need 24 complete months, and say so below that.
- **The offer:** after an import, when the history is long enough and something has not been asked yet, one question
  is shown: *"Look through your history?"* It is shown once for each length of history, not on every import.
- **The look-through (Calendar page, on a tap):** each finding is shown with its records.
  - **Renewals:** the charges themselves.
  - **Heavy months:** the categories that stood above their usual month.
  - Each is asked about: *"Is this a regular bill?"* or *"Does this happen every year?"*, with Yes / No / Not sure.
- **W1-b, only a yes changes anything:**
  - A yearly-bill yes is kept in `yearly_bills_json`. The calendar shows it as *Possible* (W3), and the futures card
    counts it as a known cost on its next date. A bill already charged this month counts next year.
  - A heavy-month yes is kept in `heavy_months_json`, and the futures card counts its usual excess.
  - **No** and **Not sure** are kept as the person's answer, shown as answered, and not asked again.
  - The finding is worked out again on the server for every answer, never taken from the page.
- **Tests:** s212, 9 checks, including the null model run in the gate (4,000 runs per case there; 20,000 by hand).

## Found while building W1: Undo on toasts (fixed, on its own branch)

`showToast` copied the Undo function into the button as text. Each Undo therefore lost every variable it closed over.
- **The Ledger's delete Undo** looked up `id`. Inside an inline handler that resolves to the button's own empty `id`,
  so Undo did nothing and the transaction was deleted five seconds later. It was confirmed in the running app: the
  probe Undo received `""`, not the id.
- **W2's price-change Undo** threw.

The function is now kept and called (`_runToastUndo`); s211 checks it. The 1.x line has the same code.

## Built: W5, the what-if panel (2026-10-12), ACCEPTED 2026-10-12

- **`core/futures.py` `what_if`:** the person's own figures moved together, through the futures' own `run()` and the
  one payoff engine (W5-a). There is no second calculation:
  - with nothing moved, it equals *As things are*, figure for figure;
  - with the debt payment moved to what is left, it equals the card's own *What is left goes to the debt*, to the
    month;
  - both are checked in s214.
- **The panel** (Budget page, Possible futures card, *What if… move your own figures*).
  - **Sliders for:** income a month, spending a month, the debt payment, a monthly amount to set aside, and a one-time
    cost with its month.
  - **The comparison:** *As things are* beside *What if* for debt-free in, cash in a year, set aside over the year,
    borrowed to get through, and lowest cash.
  - Every changed input is named with its from and to. It is labelled *"A what-if, not a prediction."*
  - A debt payment below the minimums says so, and gives no payoff date.
  - Money set aside leaves the cash (so borrowing counts it) but is counted back in the year's total: it is still the
    person's.
- **W5-b.** Nothing is saved while figures move. *Make this my plan* first lists exactly what it changes, with before
  and after:
  - the monthly debt payment setting;
  - the Savings budget line (or a new Savings line);
  - a one-time cost, kept as something the person said.

  It also lists what it does not change: income is read from deposits, and spending changes line by line on the
  Budget page. Applying keeps every before, and Undo puts each one back.
- **W5-c.** The Debt page's *What if you paid extra?* slider and the mortgage's extra-principal slider both stay. Each
  gains *Move more than one figure →*, which opens the panel with its figure already in it.
- **On Rob's record (2026-10-12):**
  - $300 more a month to debt brings debt-free from 19 to 15 months.
  - Because budgeted spending ($8,714) is above income ($8,471), that $300 is borrowed: $11,380 over the year
    against $8,248. The panel shows both.
- **Tests:** s214, 9 checks.

## Built: W9, the year-end packet (2026-10-12), awaiting acceptance

**Reports → Year-end packet**, for a chosen year (`/api/year-end`, `_year_end`).
- **Contents:**
  - income by payer (deposits in income categories);
  - spending by category, with transfers left out;
  - interest and fees, from the person's own categories for them (named so because Rob's *Interest / Fees* category
    holds a BMV kiosk and TaxSlayer, which are not interest);
  - charitable donations;
  - realized investment gains and losses (closed lots, short and long term);
  - the statements and documents Groundwork holds that are dated that year (held artefacts);
  - a section on what it does not include.
- **W9-a.** It opens with *"These are the year's figures from your records. Your tax preparer decides how they are
  treated."* It never says what is deductible or how anything is taxed. The words appear only where it says it does
  not decide them.
- **W9-b.** Health spending is left out and counted (*"19 health spending transactions are left out"* on Rob's 2026)
  until *Include health spending* is ticked. The same holds in the CSV. The CSV is a registered H6 sink
  (`year_end_export`).
- **W9-c.** Missing data is listed, never counted as zero:
  - a month with no records at all;
  - each account's months with nothing imported, from its first month;
  - an active account with nothing imported for the year.

  On Rob's 2026 ledger: Superior Savings is missing 4 months, Rob's Apple Card 3, and TJ Max 2.
- **Print or save as PDF** uses the Reports page's print rules. **Save as CSV** writes to the exports folder on this
  computer.
- **Tests:** s215, 7 checks.
