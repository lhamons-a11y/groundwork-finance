# Item 54 — One purchase, one category, whichever way it arrives

Opened 2026-10-09 (Rob: *"open the rideshare mismatch as an item"*). It was found while building item 53
(`FUEL_NAMES.md`). **RULED 2026-10-09 (Rob: "approve M1–M7 as recommended")**: master only (M7); `ibuy` and `resource recycl` kept as they are (M3). **BUILT 2026-10-09 (Rob: "build item 54")**: `bank_importer._CATEGORY_PATTERNS` is the one table (46 rules), `clientAutoCategory` is written from it, `s166` compares them rule by rule and files 44 lines both ways; the review card's *regroup* blocks offer rows saved under an old answer (M6). Additions inside the ruling: Columbia Gas named as a gas company, payroll to Paycheck / Salary (an income-type leaf, so income is still found), a tax refund to Other with tax payments. Two app.js regexes (`clientParseDate`'s `/[!']/` and three `/"/g`) were rewritten with `'` / `"`, same meaning, because s30's scan read them as strings. Awaiting acceptance.

## 1. What is true today (measured 2026-10-09 on master 50d8701, item 53's branch)

Groundwork has two keyword matchers. They are meant to be copies; the page's own comment says *"must stay in sync,
scanned in same order"*:
- **The server's** `auto_category()` in `bank_importer.py` categorises CSV, OFX/QFX and QIF imports.
- **The page's** `clientAutoCategory()` in `app.js` categorises a manual entry with no category typed, imports the
  page reads itself (the Apple Card), and Apple Card rows whose own category is vague.

Both have 34 rules in the same order. They agree on 18 rules and disagree on 16. Item 53 pinned the fuel rule; this
covers the rest.

### Eleven rules: same words, different category

| Rule matches | Server saves | Page saves | Right leaf? |
|---|---|---|---|
| Uber, Lyft, parking, metro, bus pass, tolls, Amtrak, Greyhound | Transportation *(parent)* | **Gas / Fuel** | Rideshare / Transit; Parking / Tolls |
| food, restaurant, diner, cafe, bar, grill | Food *(parent)* | **Groceries** | Restaurants |
| AEP, Ohio Edison, Enbridge, Duke Energy, Dominion, National Grid, PG&E, SCE, water, sewer, trash, "utility bill" | **Utilities** *(parent)* | Electric (all of them, gas and water companies too) | Electric, Gas, Water / Sewer or Trash, by company |
| Car Insurer, Progressive, State Farm, Allstate, Nationwide, Liberty Mutual, USAA, Farmers, "insurance" | Insurance *(parent)* | **Health Insurance** | mostly Auto Insurance |
| Walgreens, CVS, Rite Aid, pharmacy, doctor, hospital, clinic, dental, ortho, vision center | Healthcare *(parent)* | Doctor / Co-pays (all of them) | Prescriptions, Doctor / Co-pays, Dental or Vision |
| refund, reversal, chargeback, credit memo, merchandise return | **Income** | Transfer | see M4 |
| IRS payment, state tax, federal tax, treasury | **Property Taxes** | **Interest / Fees** | neither; see M5 |
| Anthropic, OpenAI, ChatGPT, apple.com/bill | Subscriptions *(parent)* | Other Subscriptions | Software / Apps |
| cinemas | Entertainment *(parent)* | Activities / Events | Activities / Events |
| tuition, university | Education *(parent)* | Tuition / Courses | Tuition / Courses |
| dry cleaner, laundromat, tailor | Personal *(parent)* | Personal Care | Personal Care |

A rule may be split into smaller rules where one rule's words belong in more than one leaf (utilities, insurance,
healthcare, transport). Bold marks a category that is plainly wrong for what was bought.

### Five rules whose words differ

- The page has an interest-charge rule ("interest charge", "finance charge", "int chg" → Interest / Fees) that the
  server lacks.
- One Transfer rule differs in its words.
- Single words differ between the two copies: `flying fur pets` (server only, Pets), `ruler foods` (page only,
  Groceries) and `ibuy` (server only, Restaurants).

### What it breaks

- **Imported utility bills never reach the utility estimates.** The gas and electricity estimates (item 26) read the
  bills saved in **Gas** and **Electric** (`_utility_bills`). Every imported AEP, Dominion or Duke bill is saved in
  **Utilities**, so the estimates see only bills the user re-categorised by hand.
- **The server saves parent categories.** Ten of its rule targets are parents: Utilities, Insurance,
  Transportation, Food, Healthcare, Entertainment, Education, Personal, Subscriptions and Income. The
  app's own rule is *"parents are for display grouping only — transactions never get parent categories"*
  (`_categoryNames`), and a user can't pick a parent. Every import breaks it.
- **The page's wrong leaves:**
  - A manual Uber entry or an Apple Card rideshare counts as a fill-up, which raises the gasoline estimate.
  - A diner counts as Groceries.
  - A car-insurance bill counts as Health Insurance, so the record says it paid for health cover.
- **The same purchase gets a different category** depending on how it arrived.

## 2. Points for ruling

**M1. One answer, kept identical.** The page's rules become the same text, the same categories and the same order
as the server's. A gate check compares all of them, the way item 53's s165 compares the fuel rule. The page keeps
its own copy so manual entry and the page's own imports stay instant.
*Recommended.* The alternative, the page asking the server each time, removes the copy but adds a server round trip
to every keystroke-time guess.

**M2. Leaves only.** Every rule returns a leaf (`s164` already pins every name to the tree; this adds "and never a
parent"), splitting a rule by company or kind where needed:

| Words | Leaf |
|---|---|
| AEP, Ohio Edison, SCE, "electric bill / company" | Electric |
| Enbridge, Dominion gas, "gas company / utility" | Gas |
| water, sewer | Water / Sewer |
| trash pickup | Trash |
| Uber, Lyft, metro, bus pass, Amtrak, Greyhound, BART, MTA | Rideshare / Transit |
| parking, toll | Parking / Tolls |
| food, restaurant, diner, cafe, bar, grill | Restaurants |
| Car Insurer, Progressive and the other carriers | Auto Insurance |
| pharmacy, Walgreens, CVS, Rite Aid, Duane Reade | Prescriptions |
| doctor, hospital, clinic, medical | Doctor / Co-pays |
| dental, dentist, ortho | Dental |
| vision center | Vision |
| Anthropic, OpenAI, apple.com/bill | Software / Apps |
| cinemas | Activities / Events |
| tuition | Tuition / Courses |
| dry cleaner, tailor | Personal Care |

**Words that name more than one service get no guess.** Duke Energy, Dominion Energy, National Grid, PG&E, a bare
"utility bill" and a bare "insurance" sell more than one thing. They return no category, so the row stays in Other
for the user to choose, rather than a guess the estimates would then trust.
*Recommended.* The named judgement calls are: carriers → Auto Insurance, the most common recurring charge from them
(a user re-files home or life); pharmacy chains → Prescriptions, though they also sell everyday goods.

**M3. The words that differ: union.** Each side gains the other's extra words: the interest-charge rule,
`flying fur pets`, `ruler foods`, `ibuy`, and the Transfer wording. The page's comment says the rules were *"tested
against real 952-txn data"*, so words that look odd, like `ibuy` under Restaurants and `resource recycl` under
Healthcare, are kept, not second-guessed.
*Recommended. If you know what `ibuy` and `resource recycl` were, say so and they'll be re-filed or dropped.*

**M4. Refunds.** A refund is neither income nor a transfer: it gives back part of a purchase. Without knowing the
purchase, the least wrong keyword answer is **Transfer**. A refund saved as Income raises income; Transfer counts in
neither income nor spending. The limit is named: the original category's spending isn't reduced.
*Recommended.*

**M5. Tax payments.** The tree has no income-tax leaf. The server's Property Taxes and the page's Interest / Fees are
both wrong. Until a tax category is ruled, these return no category and stay in Other. Adding a tax leaf would be its
own item, a change to the category tree.
*Recommended.*

**M6. What's already saved: the review, extended.** Item 52's *Imported categories to check* card offers rows with
their amounts, moved only on a yes:
- rows saved in a **parent** category whose words now give a leaf, such as an AEP bill in Utilities → Electric;
- the page's wrong leaves (Uber in Gas / Fuel, a diner in Groceries, Car Insurer in Health Insurance), where the words
  give a different leaf now.

Groundwork doesn't record whether a category was chosen by hand or by the matcher. So nothing is ever moved without
asking, and a row the user put there on purpose stays if they say so.
*Recommended.*

**M7. Which line.** Master only. The wrong leaves are also wrong saved categories on 1.x, but the fix is a rewrite of
both matchers, and 1.x has no utility estimates to repair.
*Recommended: master only. This is your call under the 1.x rule.*

## 3. Not decided here

- **A tax category** in the tree (M5).
- **Telling "chosen by hand" from "chosen by the matcher"** on a saved row. That would be a schema change, its own
  item.
- **Dual-service utilities** (Duke, Dominion, National Grid): splitting gas from electric on one bill needs the
  amount or the account, not the name.
