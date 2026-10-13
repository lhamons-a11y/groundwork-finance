# Item 83 - The agent keeps the record tidy

Opened 2026-10-13. Rob: *"should the agent either look at the categories and see what can be merged and merge them to
get better data flow. So we don't have the same charges in two different categories. When a user imports new data,
an old intuit quicken data that should be resolved by the agent where it makes logic ... Users will not have a claude
to look over their data like I have."*

**RULED 2026-10-13** (Rob: *"Yes i agree and accept item 83"*): the five points below, as proposed. **ACCEPTED, with
the push, on the gate passing** (Rob: *"accept and push through if the test pass"*).

## 1. Measured first, on Rob's data (read only)

- **70 of his 111 categories held no transactions.**
- **Near-twins:** in each pair one name was used and its twin empty:
  - Restaurants (251) and Restaurant (0);
  - Fast Food / Takeout (259) and Fastfood (0);
  - Charitable Donations (10) and Charity (0);
  - Pet Food / Supplies (57) and Pet, Pets, Pet Cost (0);
  - Hobbies and Hobby;
  - Subscriptions and Subscription;
  - Interest / Fees, Interest and Fees.

  Rob had eight of them merged by hand the same day (111 -> 103). Restaurant, Hobby and Subscription carried small
  lines, which were added into their main lines; the total was unchanged at $10,019.83.
- **A merchant in several categories is often right:**
  - Sam's Club is in 5 (one store selling different things);
  - Lowe's, TJ Maxx, Petco and Walgreens each sit under both a spending category and Transfer: probably store-card
    payments beside purchases.

  Merging these would break the spending figures, so the agent asks and never decides.
- **An import never creates a category.** An unknown name lands in Other (the page's comment saying the server creates
  it was out of date). A Quicken name like *Auto:Service* therefore became Other, with nothing kept to resolve it.

## 2. The points (ruled)

- **T1. Empty categories are offered to hide.** An empty category has no transactions, no budget line, no import rule
  and no subcategory in use.
  - Hiding takes it out of every picker. It is never deleted.
  - It comes back with one tap. A hidden category that later gets transactions (the importer still files by name) is
    offered back.
- **T2. Near-twins are offered to merge.** An empty, non-built-in category whose name is another's in a different form
  merges into the one used. A budget line it held is added into the target's line, so the total never changes (Rob's
  choice, 2026-10-13).
- **T3. A merchant in several categories is asked about, never merged.**
  - *Keep as they are* is kept, and not asked again.
  - *All in X* moves them into one category they are already in, and adds an import rule so new ones land there.
- **T4. Imports match names to the person's own.**
  - First exactly, then the person's remembered answer, then a near-twin. A Quicken *Parent:Child* name is tried
    whole, then the child, then the parent.
  - A name that matches nothing still lands in Other. It is now kept, with its rows, to ask: *"'Auto:Service': 12
    transactions, now in Other. Which of yours is it?"* The answer moves them, and is remembered for the next import.
- **T5. After an import, an offer to look**, only when that import brought something to answer. Nothing runs on its own.
- **Throughout:**
  - every proposal is shown before anything changes, and every tap has Undo (no silent writing, AP10);
  - the rules do the work, with no AI, so it is the same with AI off;
  - built-in categories are never deleted (the importer and the engines file by their names).

## 3. Built (2026-10-13)

- **`core/record_tidy.py`:** arithmetic only (`twin`, `near_twin`, `hideable`, `twins`, `splits`).
- **The twin rule was measured on Rob's 103 categories before it shipped.**
  - A starts-with rule and a shared-prefix rule paired Streaming Music with Streaming Video, Health Insurance with
    Healthcare, and Personal with Personal Care, so neither is used.
  - A twin is now:
    - the same letters;
    - the same word with a plural (including *-ies*);
    - the same words in any order (*Insurance:Auto* / *Auto Insurance*);
    - or one of the other's "/" or "&" alternatives (*Fastfood* / *Fast Food / Takeout*).
  - **Gas / Gas / Fuel is a named exception** (`NOT_TWINS`). Gas is the natural-gas utility, separated from fuel by
    item 52. The alternatives rule had offered to merge them.
- **On Rob's data today:**
  - 45 categories offered to hide;
  - no twins left (he merged them himself);
  - 23 merchants to ask about;
  - nothing unmatched yet (no Quicken import since).
- **The routes** are under `/api/tidy`: GET, `/hide`, `/show`, `/twin`, `/split`, `/unmatched`, `/undo`.
  - Each proposal is re-checked on the server before it changes anything.
  - Undo reverses each kind exactly. For a merge that means the category, its line, and the target line's amount.
- **The import commit** (`/api/import/commit`):
  - category names: exact, then the remembered answer (`category_aliases_json`), then `near_twin`;
  - unmatched names are kept in `import_unmatched_json` with their row ids.
- **The card:** *Tidy your categories*, at the top of Settings -> Categories. Each section is shown with its records,
  a choice for each item, and *Undo the last change*. After an import, a notice appears when that import brought
  something to answer.
- **A merge writes no budget-edit entry for the Willingness Layer.** Folding a duplicate line into its twin is not a
  decision about the category (as W2's and W5's taps write none).
- **Measured on a copy of Rob's data:**
  - hiding the 45 took the shown categories from 92 to 47, and Undo brought back 92;
  - *All Pet Food / Supplies* for Petco moved its 4 Transfer rows and added a rule, and Undo put both back.
- **Tests:** s223, 9 checks.

## 4. Open, for Rob

- **The two gas names** (Rob 2026-10-13: *"should they be named gas/petro and gas/heating fuel"*). Proposed as its own
  small item:
  - *Gas / Fuel* becomes *Gasoline / Fuel*;
  - the utility *Gas* becomes *Natural Gas*, joining his existing empty one;
  - propane and heating oil stay separate (item 34).

  Both are built-in, and the importer and engines look them up by name, so every place is listed for ruling first.
