# Item 84 - Gasoline / Diesel, Natural Gas, and EV Charging

Opened, ruled and built 2026-10-13.
- Rob: *"should they be named at gas/petro and gas/heating fuel"*, *"or should it be gasoline/diesel"*, and *"also
  with automobile we do not have a Charging Station category"*.
- Then: *"open as item 84, when pass accept, build"*. **ACCEPTED with the push, on the gate passing.**

## 1. What was wrong (measured on Rob's data)

- **"Gas / Fuel" and "Gas" read alike**, but they are fill-ups and the natural-gas utility. Item 52 separated them
  because fuel had been counted as a gas bill.
- **Public EV charging had no category.** The importer filed card code 5552 (electric-vehicle charging) under Gas /
  Fuel, and Rob's vehicle is set to electric.
  - His four charging rows: three Nyx / NAYAX EV charges and one Auto Finance A Company charge.
  - They sat in Car Maintenance (3) and Car Lease Payment (1), together $57.15.
  - Charging at home was already counted as part of the electricity bill, and the app says so.

## 2. The names (ruled)

- **F1.** Fill-ups are **Gasoline / Diesel**. Diesel is already priced on its own (item 34).
- **F2.** The utility is **Natural Gas**.
  - On a new database, the tree's *Gas* under Utilities.
  - On Rob's data it was already *Natural Gas* (under Utilities). His *Gas* is an empty top-level leftover, which is
    left for item 83 to offer for hiding.
  - Propane and heating oil stay their own (item 34).
- **F3.** **EV Charging**, under Transportation, beside Gasoline / Diesel. The importer files there:
  - card code 5552;
  - the charging networks (ChargePoint, Electrify America, Tesla Supercharger, EVgo, Blink, NAYAX EV, Volta, FLO, "EV
    charging", "charging station"), matched before fuel;
  - Quicken's *EV Charging*.

## 3. Every place the names were used (the inventory, before anything changed)

- **"Gas / Fuel": 79 uses in 18 files.**
  - The importer's category list, its card codes, its station patterns and its Quicken map.
  - The page's own matcher and code table.
  - The category tree.
  - The gasoline estimate (item 26: its spending and its line).
  - The utility map.
  - Item 52/53's label review.
  - The necessity floor, and W1's everyday list.
  - Item 83's twin exception.
  - Eleven tests.
- **The utility "Gas".**
  - The tree; the importer's and the page's natural-gas pattern.
  - The natural-gas price lookup (`catName`).
  - Item 56's household answer (`natural_gas` to its category, twice).
  - Item 52's review (the Utilities *Gas* it reads fuel rows from).
  - **The natural-gas estimate's budget-line lookup** (`lower(category) == 'gas'`). An exact-name search missed it,
    and it would have silently lost Rob's gas estimate.
  - The utility map.
  - Six tests.
- **Stored copies of a category's name:**
  - budget lines (category, and the line's name when it is the category's);
  - Willingness declarations, the debt ledger, Before You Buy items;
  - import rules;
  - the category map, the saved app snapshot;
  - item 83's remembered answers and its answered list.

## 4. Built

- **Code:** every use above, renamed. The price lookup also accepts the old *Gas* name for a database not yet updated.
- **The update** (`migrate._fuel_names_v84`, SCHEMA_VERSION `20261013-fuel-names`; models unchanged, fixture written).
  - It renames *Gas / Fuel*, and the *Gas* under Utilities. Where the new name already exists, it moves what the old
    one holds into it.
  - It updates every stored copy, and creates *EV Charging* under Transportation.
  - Running it twice changes nothing more.
  - **Tried on a copy of Rob's database:**
    - 17 fill-ups, two budget lines and both import rules (*clark gas*, *rufus truck stop*) now say Gasoline /
      Diesel;
    - Natural Gas is untouched;
    - EV Charging is created once;
    - the stray top-level Gas is left alone.
- **His four charging rows** are offered in the existing review: *categories that may need a look*, which moves
  nothing without a yes. It now also offers any row today's rules file as EV Charging, from whatever category older
  rules left it in.
- **Item 83's matcher** gains a few one-meaning synonyms: *fuel / gasoline / diesel / petrol* to Gasoline / Diesel,
  and *charging* to EV Charging. Quicken's *Auto:Fuel* still finds the fuel category. *Gas* alone is not a synonym,
  because it could mean the utility or the pump.
- **The necessity floor** gains the two new names, so they are protected as the names they replaced were.
- **Tests:** s224, 6 checks. s136, s140, s141, s159, s164, s166 and s167 were updated to the new names.

## 5. Status

**Built 2026-10-13. Accepted with the push, on the gate passing** (Rob's instruction).
