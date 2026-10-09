# Item 53 — Fill-ups recognised by the station's name

Opened 2026-10-09 (Rob: *"open the regex gaps as an item"*). It comes from item 52 (`CATEGORY_LABELS.md` §3): the
2026-09-20 audit noted that `\bbp\s` misses `BP#8823` and `\bexxon\b` misses `EXXONMOBIL`. **RULED 2026-10-09 (Rob: "approve G1–G8 as recommended")**: master only (G8).
**BUILT 2026-10-09 (Rob: "build item 53")**: one 40-part pattern, the same text in `bank_importer.py` and `clientAutoCategory` (G6); all 48 station lines read as Gas / Fuel and none of the 19 non-fuel lines do, on both sides (`s165`); Groceries rows join the *Imported categories to check* card (G7). One addition to G2's store-number list: **Sinclair**, because Sinclair Community College is a common Ohio charge. Flying J was added beside Pilot. Awaiting acceptance.

## 1. What is true today (measured 2026-10-09 on master 90194ab)

- **Fuel is recognised in two ways:**
  - by the card code (MCC 5541, 5542 or 5172), when the import has one;
  - otherwise by one name pattern, the same in `bank_importer.py` (`_CATEGORY_PATTERNS`, Gas / Fuel) and in
    `clientAutoCategory` in `app.js`.
- **Most imports have no card code.** Only bank CSV formats whose descriptions carry one (`rich_description`
  signatures) and OFX/QFX files do. For everything else, the station's name is all there is.
- **The name pattern covers 14 names:** Clark, BP, Shell, Exxon, Mobil, Speedway, Marathon, Circle K, Sunoco,
  Chevron, 76, Buc-ee's, Sheetz and Wawa, plus "fuel" and "gas station" anywhere.
- **Measured against 47 station descriptors, 30 are missed.** These are descriptors written to look like bank lines,
  not taken from real statements (see G5):

  | Missed | Lands in |
  |---|---|
  | `BP#8823456 MILLBROOK OH`, `BP#1234` | Other |
  | `EXXONMOBIL 4521` | Other |
  | Phillips 66, Conoco, Citgo, Valero, QuikTrip / QT, RaceTrac, Casey's, Kwik Trip, Pilot, Love's, Murphy USA / Express, Holiday, Sinclair, Gulf, ARCO, Thorntons, TA, GetGo, Speedy Q, Cumberland Farms | Other |
  | `COSTCO GAS #123`, `MEIJER EXPRESS 123` | **Groceries** |

  Seventeen are matched: `BP 8823` (with a space), `EXXON MOBIL` (two words), Exxon, Mobil, Shell, Speedway,
  Marathon, Circle K, Sunoco, Chevron, Wawa, Sheetz, Buc-ee's, and the four that say "fuel".
- **One non-fuel line is caught as fuel today:** `MARATHON REGISTRATION` (a race entry) matches `\bmarathon\b`. Of
  18 non-fuel lines tried, it's the only one: T-Mobile, Shelly's Salon, Holiday Inn, Casey's pizza, Dominion
  gas bills and the rest stayed out.

### What a miss costs

A missed fill-up lands in Other, or for warehouse-club fuel in Groceries. It never reaches Gas / Fuel, so the
gasoline estimate (item 34) sees fewer fill-ups than the ledger holds, and Transportation spending reads low.

## 2. Points for ruling

**G1. The two named gaps.** `bp` matches when followed by a space, `#` or a digit (`BP#8823`, `BP 8823`), and
`exxon` matches at the start of a word (`EXXONMOBIL`).
*Recommended.*

**G2. The missing brands.** Add the 20 brands in §1, each as a whole word. A brand name that is also an ordinary word
or another business counts only with a store number (`#` or digits) or a station word after it:
- Pilot, Love's, Holiday, Gulf, ARCO, QT and Casey's;
- Marathon, which also fixes the race-entry false match.

`Holiday` alone stays out, for example, so Holiday Inn doesn't become fuel.
*Recommended.*

**G3. Warehouse-club and grocery fuel.** `COSTCO GAS`, `SAM'S FUEL` / `SAMS CLUB FUEL`, `MEIJER EXPRESS`, `KROGER
FUEL` and `GIANT EAGLE GETGO` go to Gas / Fuel. The fuel pattern is already checked before Groceries, so an ordinary
`COSTCO WHSE` or `KROGER #234` stays in Groceries.
*Recommended.*

**G4. A named limit: convenience stores.** Casey's, Wawa, Sheetz, QuikTrip and the like sell food too. A charge there
is read as fuel because, without a card code, the name can't tell a pizza from a fill-up. The card code still wins
when it is present (a food MCC goes to Food). This is named, not solved.
*Recommended, as the existing behaviour for Wawa and Sheetz.*

**G5. Tested both ways, with the source named.** One gate section checks:
- every station line in the list matches Gas / Fuel;
- every non-fuel line in a second list doesn't. That list includes T-Mobile, Shelly's Salon, Holiday Inn, Gulf
  Coast Bank, Murphy Bed, Pilot Pen, Lovesac, a race entry and the gas utilities.

Both lists are written to look like bank lines, not taken from real statements, and the section says so. If you want
to check them against your own statements, compare locally. Nothing is sent anywhere.
*Recommended.*

**G6. One pattern, kept identical.** The Python and page patterns are the same text today. A gate check fails if they
ever differ, the same way s164 pins names to the tree.
*Recommended.*

**G7. What's already saved: the item 52 review, extended.** Rows that landed in Other can already be re-sorted by
the user-run *smart backfill* (Other and Personal only). Rows that landed in **Groceries** (Costco Gas, Meijer
Express) join item 52's *Imported categories to check* card: listed with their amounts, moved only on a yes.
*Recommended.*

**G8. Which line.** Master only. A missed name mostly leaves a row in Other, uncategorised rather than saved as a
wrong figure, so it falls outside the 1.x rule. The Groceries case is the exception. Bringing it to 1.x would
take the pattern change alone, without the review card.
*Recommended: master only. This is your call under the 1.x rule.*

## 3. Not decided here

- **Other spending kinds with the same shape:** groceries, restaurants and pharmacies are also matched by name.
  Measuring them would be its own item.
- **Learning a station from the user's own re-categorisations:** ruled out by *no silent learning*. A name added here
  is added by a ruled change, in the open.
