# Ask for a tile (queue item 28)

> Status: **OPENED 2026-10-01. No code.** Rob, 2026-10-01: *"open item 28"*.
>
> Rob's request (2026-09-30): let the user type what they would like to see. His example: *"a comparison to their
> gains and losses in their investments in the dashboard"*. That example is now answered by item 29's tile; this
> pass is the general mechanism.
>
> **What governs it:**
> - item 22: tiles are arranged by the user only, and usage never creates, ranks or implies anything;
> - item 27: completeness first, a source line, the BANNED lexicon;
> - proof, not persuasion, and report statements proven in the same run: **a number on the dashboard always comes
>   from an engine, never from a model**;
> - F.3's rule: only what the record can back may be offered;
> - local-only AI;
> - the 17 August no-silent-learning rule.
>
> **Out of scope:** item 24, item 26, W-D, W-E, the Investments page's own gaps, the gate stall, and anything in 1.x.

---

## 1. Measured (master `44d95ed`)

- **Tiles today:** seven, all user-arranged (`DASHBOARD_TILES`). A hidden one can already be shown again from
  Arrange.
- **Engines that already compute something a user might ask for, with no tile:**

| candidate | engine / data already there | the record backs it when |
|---|---|---|
| Net worth over time | `NetWorthSnapshot`, Net Worth page | at least 2 snapshots |
| Savings funds and their pace | `solution.fund_pace`, `/api/sinking-funds/pace` (post-break-only since item 25) | an active fund |
| Recurring charges | `detect_recurring_patterns`, `trim_candidates` | at least one recurring pattern |
| One category over time | the ledger by category and month (the reallocation reader's completeness rules) | the category seen in at least 3 recorded months |
| Energy prices (EIA) | `utility_price.py`, `gas_price.py` | a live EIA price (the Ohio natural-gas lag fix is item 26's prerequisite) |
| What Groundwork has concluded | the working picture (`/api/willingness`) | at least one reading or statement |

- **The local model:** `/api/ai/status` says whether a model is available. With none, the app works without AI
  (local-only ruling).

---

## 2. Findings and proposals

**K1: A closed catalogue, each entry evidence-gated.**
- Each entry has: an id, a title, plain words people might use for it (synonyms), the engine that computes it, and
  the record test that must pass before it can be offered.
- The seven existing tiles are in it, so asking for a hidden one shows it. So are the six candidates above.
- **Adding an entry is a ruled code change, never something generated.** The same rule closes Needs attention's
  three kinds.

**K2: The request only matches.**
- **Without a model:** a plain search over the catalogue's titles and synonyms, ranked by how well the words match
  and nothing else.
- **With the local model:** it is given the request and the list of entry ids, and may answer only with one id
  from the list or "none". Anything else is treated as "none". It never writes a figure, a title or a sentence the
  user sees.
- **Either way the user confirms:** *"Add 'Net worth over time'?"*. Nothing is added silently.

**K3: Offered only when the record can back it.**
- A matched entry whose record test fails is not added. The user is told what it needs: *"Net worth over time needs
  at least two net worth snapshots; you have one."*
- That is an honest no carrying the nearest way forward (C.4 / C.7).

**K4: No match is an honest no, and the words are kept as the user's own.**
- *"Groundwork can't show that yet."* The request is kept, with its date, in a visible list in Arrange, as the
  user's words.
- The user can delete their own request.
- It is **mined for nothing:** no ranking, no suggestion, no inference.
- It **never leaves the machine,** so there is no feedback channel. A pinned test shows its only reader is that
  list.

**K5: An added tile is a tile.**
- It is pinned, hidden and reordered like the seven, by the user only.
- It meets item 27's standard: completeness first, a source line, no banned words.
- Its numbers come from the engine named in K1.

**K6: Storage and scope.**
- The user's added tiles join the layout setting (`dashboard_layout`), and their requests go in
  `dashboard_tile_requests`. No schema.
- 2.0 only, through the teaching seam. app.js and index.html are untouched.

**K7: Build order.**
- K1 to K4 with the **search matcher** and **one** new entry first. Recommend *Net worth over time*: the most-asked
  kind of thing, with a simple record test.
- Then the other five entries, each its own small addition under K1's rule.
- The model matcher last, behind `/api/ai/status`.

---

## 3. Cases

| # | situation | expected |
|---|---|---|
| Ak1 | "show my net worth over time", 3 snapshots | matched; *Add 'Net worth over time'?*; on yes, a tile with its source line |
| Ak2 | the same with 1 snapshot | not added; *"needs at least two snapshots; you have one"* |
| Ak3 | "my spending on dining by month" | matched to *one category over time*, Dining; offered only if Dining is seen in at least 3 recorded months |
| Ak4 | "which stocks will go up" | no match; *"Groundwork can't show that yet"*; the words kept in Arrange |
| Ak5 | the model answers with text, not an id | treated as "none"; the search matcher's answer is used |
| Ak6 | no local model | the search matcher alone; nothing breaks |
| Ak7 | asking for a hidden tile ("show my upcoming bills") | the hidden tile is shown again |
| Ak8 | the user deletes a kept request | gone; nothing else changed |
| Ak9 | any added tile's text | passes the BANNED lexicon; has its source line |
| Ak10 | structural | kept requests have one reader (the list); no network call carries them; nothing is ranked by use |

---

## 4. Ruling sought: Rob

1. **K1:** a closed catalogue, evidence-gated, with new entries only by ruled code change?
2. **K2:** matching only, by search, with the local model allowed to pick an id from the list; the user confirms
   every addition?
3. **K3 / K4:** an entry the record can't back says what it needs; no match is an honest no, with the request kept
   visibly as the user's words, deletable, never mined or sent?
4. **K5 / K6:** added tiles behave like the seven, to item 27's standard; settings only, no schema, 2.0 only?
5. **K7:** first build is the mechanism, the search matcher and *Net worth over time*; then the other entries; the
   model matcher last?
