# Item 52 — Imported purchases land in the right category

Opened 2026-10-09 (Rob: *"open the label fix as an item"*), from an unmerged fix found while cleaning up worktrees.
That fix is `bef7d01`, on worktree `jolly-wu` and branch `claude/frosty-margulis-3b686a`, dated 2026-09-20. It was
never merged to master or 1.x. **RULED 2026-10-09 (Rob: "approve L1–L7 as recommended")**, including L2's Shopping → Personal and L7's split: L1, L3 and L4 on 1.x as a wrong saved figure, all of L1–L6 on master. **BUILT 2026-10-09 (Rob: "build item 52")**: on 1.x (`labels-lts`, gate 1009 / 0) L1 in `bank_importer.py`, L4 in the smart backfill, and `s164` (L3); on master, merged from 1.x, L2 in `_mapAppleCardCategory` and L5 as *Imported categories to check* in Settings → Categories (`GET /api/categories/label-review`, `POST …/label-review/move`, which moves only the rows the review offers). Found while building L5: the category **Merge** route looked up budget lines by a `category_id` they don't have, so it raised on every merge since 1.0 and no merge ever saved. Fixed on master (budget lines move by name). It is a broken button on 1.x, not a wrong saved figure, so 1.x is left as it is unless you rule otherwise. Not covered: Willingness declarations, also keyed by category name, don't follow a merge. Awaiting acceptance.

## 1. What is true today (measured 2026-10-09 on master e625483 and lts/1.x)

When a bank file is imported, `bank_importer.auto_category()` picks a category by name, from its 34 name patterns and
its 29 card-code (MCC) targets. Each name is matched to the category tree (`CATEGORY_TREE`, 88 names). Two of them
point at the wrong place:

| Purchase | Today it lands in | It belongs in |
|---|---|---|
| `SHELL OIL 57444`, `CLARK GAS 12`, `MEIJER FUEL`, card codes 5541, 5542 and 5172 | **Gas**, the natural-gas *utility* under Utilities | **Gas / Fuel**, under Transportation |
| `PLANET FITNESS 33`, card code 7997 | **Fitness**, which is not in the tree | **Gym / Fitness**, under Healthcare |

The page's own matcher (`clientAutoCategory` in `app.js`) already uses the right names, so only the Python import
path is wrong. Both lines are affected: lts/1.x has the same two names.

### What it breaks

- **The natural-gas estimate (item 26)** reads the bills in **Gas** (`_UTILITY_CATEGORY['gas']`). Imported fill-ups
  are mixed in with gas bills, so the bill months it fits on are wrong.
- **The gasoline estimate (item 34)** reads **Gas / Fuel**. Imported fill-ups never reach it, so it can say there
  aren't enough fill-ups when the ledger is full of them.
- **Spending by category:** Utilities reads too high and Transportation too low, by every fill-up.
- **Fitness:** saving an import drops it to Other. The *Re-categorise* route (`server.py` ~6768) creates a stray,
  parentless category named "Fitness" beside the real Gym / Fitness.

### A second path with the same defect

`_mapAppleCardCategory()` in `app.js`, used for the Apple Card import, returns six names that aren't in the tree:
**Health, Travel, Shopping, Restaurant, Interest and Fees**. It also returns **Gas**, the utility leaf, for Apple's own
"Gas" category.

### Why nothing caught it

No gate check pins these tables to the tree. Section 32 already checks `_QIF_CATEGORY_MAP` this way ("every target is
a real current category name"), but no such check exists for the importer's patterns, its card codes or the Apple
Card map.

## 2. Points for ruling

**L1. The two importer names.** `Gas` becomes `Gas / Fuel` and `Fitness` becomes `Gym / Fitness`, in the patterns and
in the card-code map. The matching regexes don't change, and natural-gas bills (Dominion, "gas company", MCC 4900 →
Utilities) are untouched. This is what `bef7d01` did, rebuilt on today's code rather than merged from a branch three
weeks old.
*Recommended.*

**L2. The Apple Card map.** Each name maps to the tree:

| Returned today | Becomes |
|---|---|
| Gas | Gas / Fuel |
| Health | Healthcare |
| Travel | Vacation / Travel |
| Restaurant | Restaurants |
| Shopping | Personal (the tree has no Shopping) |
| Interest | Interest / Fees |
| Fees | Interest / Fees |

`clientAutoCategory` still gets the first try wherever it does today.
*Recommended, with the Shopping row named as the one judgement call.*

**L3. A guard so it can't drift again.** One gate check: every name the importer patterns, the card-code map, the
Apple Card map and `clientAutoCategory` can return is a real tree name. It is the same check section 32 applies to the
QIF map.
*Recommended.*

**L4. Never mint a category from an import.** *Re-categorise* (and import-commit) leaves a row unchanged when the name
isn't in the tree, instead of creating a new category. A category the user makes themselves is unaffected.
*Recommended.*

**L5. What's already saved: a review, not a rewrite.** Changing the names fixes new imports only. Rows already saved
stay where they are until the user says otherwise:
- A one-time list shows the rows in **Gas** (utility) whose description or card code matches the fuel patterns,
  as "These look like fill-ups, not gas bills — move them to Gas / Fuel?", with each row and its amount, and
  "Move all", "Choose" or "Leave them".
- A stray **Fitness** category, if one exists, is offered as "Merge into Gym / Fitness?".
- Nothing moves without a yes. *No silent writing.*

*Recommended.*

**L6. The estimates after a move.** Moving rows changes what the gas and gasoline estimates read. They recompute from
the record the next time they're shown, as they already do. Nothing is cached, so nothing else changes.
*Recommended, no new code.*

**L7. Which line.** On master: L1–L6. On 1.x: L1, L3 and L4, as a wrong saved figure under the 1.x rule (L1 in
`LTS_SUNSET`), because every imported fill-up saves the wrong category and the spending totals by category are wrong.
L2 and L5 would be master only, unless you rule otherwise. 1.x doesn't carry the utility estimates, so its harm is the
totals alone.
*Recommended, and this is your call under the 1.x rule.*

## 3. Not decided here

- **Two regex gaps** the audit noted: `\bbp\s` misses `BP#8823`, and `\bexxon\b` misses `EXXONMOBIL`. These are
  matching, not labels, so they would be their own small item.
- **The worktree** `jolly-wu` (`bef7d01`) is kept until this item is built, then removed.
