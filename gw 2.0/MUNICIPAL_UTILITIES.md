# Item 56 — Municipal utilities, and what the bill covers

Opened 2026-10-09. Rob:
- *"City of Millbrook would be water, sewer, garbage charge that is billed as one services as the city of millbrook
  utilities."*
- *"Many cities will bundle all of their utilities charges as one bill that covers multiple services."*
- *"we can call the municipalities utilities and add what does that cover? Allow the user to enter those and if
  their municipalities utility bill doesn't cover it then they would have a company that covers that cost."*

**RULED 2026-10-09 (Rob: "approve U1–U8 as recommended")**: master only (U8). **BUILT 2026-10-09 (Rob: "build item 56")**: the leaf and the bump (`20261009-municipal-utilities`, fixture saved; an upgraded database gains the leaf, and without the bump it would not - both in `s168`), the `municipal_covers` set fact (`canonical_set`), the checklist and per-service lines in Settings → Your home, the inline question in the gas and electricity estimate cards, U5 in `utility_applies`, the rule on both sides, the review from Other / Utilities / Water / Sewer. U3 shows where each uncovered service's charge is filed; linking a specific charge to it is not built. **ACCEPTED and CLOSED (Rob, 2026-10-09: "I accept item 56"), gate 2659 / 0.**

## 1. What is true today (measured 2026-10-09; items 54 and 55 on their branch, gating)

- **The tree has no place for a bundled bill.** Utilities has seven leaves: Electric, Gas, Water / Sewer, Internet,
  Phone / Cell, Trash and Cable / TV. One charge from the city for water, sewer and trash belongs to two of them at
  once.
- **Under items 54 and 55, a city bill gets no guess.** Code 4900 (every kind of utility) names Other. The words
  "city of millbrook" match no rule, and "utility bill" names Other. So the bill waits in Other for the user every month.
  Before item 54 it was saved as **Utilities**, a parent.
- **The estimates read only their own leaf.** The gas and electricity estimates (item 26) count the bills in Gas and
  Electric. A city that also sells electricity puts it on the bundled bill, where no estimate sees it.
- **Asked facts exist** (item 30, `core/household.py` `FACTS`, the `household_facts` history). Each fact is one
  answer from a fixed list, such as `heating_fuel` or `housing_status`, recorded with when and where it was said.
  No fact yet holds a set of answers.
- **New categories reach an existing database** through `migrate._seed_child_categories`, which runs only when
  `SCHEMA_VERSION` changes.

## 2. What it would do

- A new leaf, **Municipal Utilities**, under Utilities, for the one bill a city, village or town sends.
- One asked question: **"What does your municipal utility bill cover?"** It's a checklist: water, sewer, trash,
  electricity, natural gas, or "I don't get a municipal bill".
- Each service the city doesn't cover is shown as coming from its own company, in its own category: Water / Sewer,
  Trash, Electric or Gas, as today.

## 3. Points for ruling

**U1. The leaf.** *Municipal Utilities*, under Utilities, added to `CATEGORY_TREE`. It reaches existing databases
through the migration, with a `SCHEMA_VERSION` bump. No table changes.
*Recommended.*

**U2. The question, and where it's asked.** A new asked fact, `municipal_covers`. The answer is the set of services,
or "none", kept with its history like every other fact (stored as a sorted list; changing it adds a row). It's asked
in two places:
- in Settings → Household, beside the heating questions;
- once, inline, when the first Municipal Utilities charge appears ("This looks like your city's utility bill. What
  does it cover?"), with source `inline_prompt`.

It's never inferred from the amount or from which other bills exist. *No silent learning.*
*Recommended.*

**U3. What the city doesn't cover.** Once the answer is in, Settings shows each service either as *on your municipal
bill* or as *its own company*, the latter with the category it's filed under. Groundwork doesn't conclude anything
from a missing bill (*absence is not zero*). It may ask, never state: *"Trash isn't on your city bill. If you pay
for it, which charge is it?"* Answering is optional.
*Recommended.*

**U4. The matcher.** Words that name a municipal utility go to Municipal Utilities, the same on the server and the
page (item 54 M1):
- *city of … utilities*, *village of … utilities*, *town of … utilities*, *township … utilities* or *borough …
  utilities*;
- *municipal utilities* and *public utilities*.

The word "utilities" is required, so a city parking ticket or a court fee isn't filed here. Code 4900 still names
Other and lets these words decide (item 55 C4). A bare "CITY OF MILLBROOK" charge with no "utilities" stays in Other.
*Recommended.*

**U5. The estimates.** When `municipal_covers` includes electricity or natural gas, the electricity or gas estimate
says so instead of fitting part of the bills: *"Your electricity is on your municipal utility bill with other
services, so Groundwork can't separate it from the total."* When it doesn't include them, nothing changes. The
municipal bill is never split by guessing.
*Recommended.*

**U6. What's already saved: item 54's review.** Rows in Other, Utilities or Water / Sewer whose words now name
Municipal Utilities are offered in the review card with their amounts, and moved only on a yes. The *regroup* block
does this once Other is added to its list of old answers for this one target.
*Recommended.*

**U7. Tests.** One section covering:
- the leaf in the tree and seeded on an upgraded database (through `run_migration_if_needed`, per *SCHEMA_VERSION
  gates migrations*);
- the fact's history, including a changed answer;
- the matcher on both sides, with the parking-ticket and court-fee lines kept out;
- the estimate's words when electricity is covered;
- the review.

*Recommended.*

**U8. Which line.** Master only. It's a new category and a new question, not a fix to a saved figure.
*Recommended.*

## 4. Not decided here

- **Splitting one charge across categories** ($40 water, $25 sewer, $18 trash). It would be exact, but Groundwork has
  no split transactions, so it would be its own, larger item. U5's wording names the gap meanwhile.
- **Other bundles** (internet plus TV plus phone from one company): the same shape, its own item if wanted.
