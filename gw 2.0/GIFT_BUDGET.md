# Item 74 — Gift Budget: a gift is a yearly cost paid in a few months

Opened 2026-10-10. Rob: *"lets look at gift budget and see how can that get improved?"*

**G1–G9 RULED 2026-10-11 (Rob: "I accept on all items that need ruled on"), G1–G5 and G7–G9 as recommended; G6, offered without a recommendation, accepted under that "all". No code yet: the build needs its own go-ahead.**

## 1. What is true today (measured 2026-10-10, master 7479f50, and Rob's data read without changes)

**What the page does:**
- **People and their occasions.** People (with a relationship), each with occasions (birthday, anniversary,
  Christmas and others). Each occasion has a date and a budget.
- **Coming up.** The next 90 days are listed.
- **Logging and budgeting.** "$" logs what an occasion actually cost (a Historian entry). "Budget it" adds the
  occasion to the budget.
- **Seasonal funds.** Each has a name, a target and a funded-by date. "+ Add" records money put in; "Mark spent"
  sets the fund back to $0.
- **Advisor.** An AI write-up of what is coming up and how the funds are pacing.
- **Storage.** Everything is kept as two JSON settings (`gift_people_json`, `gift_seasons_json`), not in tables.

**What is wrong, measured:**
1. **"Budget it" makes a yearly gift a monthly cost.** It adds a budget line, such as "Mom's Birthday $100", and
   budget lines repeat every month: there is no one-time line. A $100 birthday then reads as $1,200 a year in every
   budget total, plan and scenario until someone deletes the line.
2. **A seasonal fund never fills itself.** The card says "$X/mo for N months", and `_applySeasonalContributions`
   would add a monthly amount, but nothing anywhere sets that amount (`_monthlyContrib`). The suggestion can't be
   turned on.
3. **Two kinds of savings fund.** Seasonal funds (Gift page, a JSON setting) and sinking funds (Budget page, a
   database table) are the same idea in two places, not linked. Everything built since (goals, the evidence
   library's goal entries, Ask why) sees only sinking funds.
4. **"Mark spent" forgets.** It sets the fund to $0, with no record of what was spent or when. Next year's target
   can't be compared with this year's.
5. **Gift spending never meets the ledger.** What an occasion cost is typed by hand. Gift purchases imported from
   the bank are never offered as that occasion's spend.
6. **Occasions carried over from the old gift list can't be changed.** Their ids are fractional (Rob's birthday
   occasion is `1782615276010.1562`), and the delete, budget and "$" buttons compare whole numbers. Those buttons
   silently do nothing for them.
7. **The help answer was wrong.** "How does Gift Budget work?" described occasion "pools", fixed per-person amounts
   and drawing from sinking funds. None of that exists. *(Corrected with item 72 stage 2's guide, which was shipping
   it.)*

**Rob's data:** one person, two occasions, no budgets set, no seasonal funds, no gift spending in the ledger. Little
use so far, so this is a design pass, not a data repair (except point 6).

## 2. Points for ruling

**G1. The year's gift plan, as one monthly set-aside, with its working.**
- The page totals every occasion's budget for the next 12 months.
- It shows that figure, the monthly amount it takes (the total ÷ 12, or what's left to save ÷ the months left), and
  each occasion behind it. Shown as a fact and an option, never a verdict.
- **"Budget it" is replaced by "Set aside for gifts"**: on the tap, one budget line, *Gifts (set aside)*, at that
  monthly amount. It is shown with its working and updated (again on a tap) when occasions change.

*Recommended.* It fixes point 1 at its cause: a gift is a yearly cost, paid in a few months.

**G2. One kind of fund.**
- Seasonal funds become sinking funds, which have a target, a date and a monthly contribution that actually adds
  itself.
- The Gift page shows the gift funds. The Budget page, goals and Ask why see them as they do every sinking fund.
- Existing seasonal funds are moved over on a tap, listed first, with nothing lost.

*Recommended.* It fixes points 2 and 3.

**G3. "Mark spent" keeps the record.**
- It records what was spent and when, in the Historian and on the fund's history.
- Next year the fund shows *"Last time: target $800, spent $1,140 (Dec 2026)"* beside this year's target, as a
  fact. The target stays the person's choice.

*Recommended.* It fixes point 4.

**G4. Gift purchases from the ledger, offered, never assumed.**
- In the weeks before an occasion, charges filed under Gifts (or a category the person names) are listed under it:
  *"These 3 charges before Mom's birthday came to $75.17. Use them as what it cost?"*
- Only on a yes do they become the occasion's actual spend.
- Groundwork never decides who a purchase was for (TM5: never infer life events or people from purchases). The
  person picks.

*Recommended.* It fixes point 5.

**G5. Gifts in what Groundwork already shows ahead.**
- Thirty days out, an occasion with a budget appears where upcoming facts appear: the dashboard's coming-up list,
  next to bills.
- *"Mom's birthday, Nov 12: $60 budgeted; the gift fund holds $140."* From the record's own dates, never from
  watching the person.

*Recommended.*

**G6. Occasions shared by many people (Christmas, a family exchange).**
- One occasion with one total and the people under it. Each person can have a fixed amount, and the rest is split
  among the others, with what's left to assign shown.
- This is what the old help answer described, and it doesn't exist today.

*Offered, not recommended either way.* It is the most work, and Rob's call whether it is wanted.

**G7. Fix the occasions that can't be changed.**
- Ids are compared as stored, and the carried-over fractional ids are made whole once, on load, keeping every
  occasion.

*Recommended.* It is a fix, so it builds with the first stage. Master only: gift data isn't a saved figure under 1.x
rule L1.

**G8. Gift data into tables.**
- People, occasions and funds move from JSON settings into database tables, with a SCHEMA_VERSION bump.
- Then the Historian, the ledger matching (G4), exports and Ask why can join them.

*Recommended.* It builds with G2/G4.

**G9. Lines and tests.** Master only. Tests:
- the set-aside equals the occasions' total and stays monthly-correct (a $100 birthday is $100 a year, not $1,200);
- a gift fund adds its monthly contribution once a month;
- "Mark spent" keeps its record;
- ledger charges become an occasion's spend only on a yes;
- the carried-over occasions can be deleted, budgeted and logged;
- AI off works throughout.

*Recommended.*

## 3. Not decided here

- **Gift ideas, wish lists, or prices of things.** Not proposed. Groundwork prices from the person's record, not
  from shopping.
- **Reminders by notification.** Upcoming occasions show where upcoming facts already show (G5). Nothing pushes or
  counts down (TM6).

## 4. Built 2026-10-11 (Rob: "build 74") - ACCEPTED + CLOSED 2026-10-11 (Rob: "i accept item 74")

- **G8, G7.** People, occasions, shared occasions' people, and each "Mark spent" now live in tables (`gift_people`,
  `gift_occasions`, `gift_shares`, `fund_spends`), plus `sinking_funds.purpose`, at SCHEMA `20261011-gift-tables`.
  The old `gift_people_json` is carried in once, on first read, with new whole-number ids; each old id is kept as
  `legacy_id`, and the setting itself is left as it was. Rob's birthday occasion can be changed again.
- **G1.** "The year's gifts" totals the next 12 months' budgeted occasions and shows its working. It offers
  *Set aside for gifts* at the total ÷ 12, and, when a date comes before 12 months of setting aside (always so in a
  first year), a second amount that covers each occasion by its own date, counting what the gift funds hold. The
  person picks. Either way it is one line, *Gifts (set aside)*; any other amount is refused. "Budget it" is gone.
- **G2.** A gift fund is a sinking fund marked `gift`. It adds its monthly amount itself through the existing
  monthly auto-credit, and shows on the Budget page with every fund. The old seasonal funds are listed first, with
  a *Move them to gift funds* button. Each keeps its target, date and what it held, and the setting records which
  fund each became.
- **G3.** *Mark spent* asks what was spent and keeps it with the target (`fund_spends`, and the Historian's
  `gift_fund_spent`). The fund shows *"Last time: target $800.00, spent $1,140.00 (Dec 2026)"*.
- **G4.** For an occasion up to 45 days past, or up to 30 days ahead, the receipt button lists the charges filed
  under Gifts (or its subcategories, or a category named in `gift_charge_category_ids`) from the six weeks before
  it to three days after. The page says Groundwork can't tell who a purchase was for, and the person unticks any
  that weren't for this occasion. Only charges that were offered are accepted, only on the yes. A charge given to
  one occasion isn't offered for another.
- **G5.** Budgeted occasions within 30 days join the dashboard's Upcoming card, next to bills, as one sentence:
  *"Mom's birthday, Nov 12: $60.00 budgeted; the gift fund holds $140.00."*
- **G6.** *+ Shared occasion* gives one total for many people. Fixed amounts are taken first, and the rest is split
  evenly to the cent. The page shows what's left to assign, or that the fixed amounts are over the total.
- **G9.** s202, 23 checks. The old `/api/gift` routes stay, for the settings kept as backup.
- **Not changed:** the occasion "$" still takes a typed amount. The AI advisor reads the same figures the page
  shows.
