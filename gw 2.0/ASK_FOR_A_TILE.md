# Ask for a tile (queue item 28)

> Status: **RULED 2026-10-01 (Rob, §5: all five; §6: the seven build requirements); first slice AUTHORISED
> (Rob: "Build it") and BUILT (§7), 2.0 only; gate 2039 / 0; first slice ACCEPTED (Rob, 2026-10-01). The remaining slices (the five
> entries and the model matcher) AUTHORISED ("Build Item 28") and BUILT (§9), gate 2065 / 0; awaiting Rob's acceptance.** Opened the same day. Rob, 2026-10-01: *"open item 28"*.
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

---

## 5. Ruling: Rob, 2026-10-01

*"Accept all .. each one fits."* K1–K7 as proposed:
- a closed, evidence-gated catalogue;
- matching only, by search or by the local model picking an id, with the user confirming;
- an honest no that names what is needed;
- kept requests that are visible, deletable, never mined and never sent;
- added tiles to item 27's standard, settings only, 2.0 only;
- the first build is the mechanism, the search matcher and *Net worth over time*.

**Not authorised yet:** the build itself.

---

## 6. Build requirements: ruled by Rob, 2026-10-01

Rob asked whether accepting all five would create a bug in the code. The answer was that the rulings do not
contradict each other, but seven places would break if built naively. Rob, 2026-10-01: *"I accept your input as
written. I too felt that it would cause issue but also parts of each has its importance. I rule we accept your
recommendations."*

Each is a requirement of the build, and **R1–R4 each get their own test**.

| # | requirement | why |
|---|---|---|
| **R1** | **One source for the tile list.** The server's allowed ids are the seven tiles plus the catalogue. The page reads that list, so no second copy is kept in the JS | the layout endpoint accepts only known ids, and s131 pins that. An added tile would otherwise fail to save, and two copies drift |
| **R2** | **Parameterised entries are validated against the record.** *One category over time* carries its category in the id (`cat:Dining`), and the server accepts it only for a category the record backs (seen in at least 3 recorded months) | otherwise any string becomes a tile, and the catalogue stops being closed in practice |
| **R3** | **A chosen tile that loses its evidence stays and says what it needs** (K3's honest no). It is never hidden silently and never drawn broken | item 29's *hidden when absent* governs **defaults**, not tiles the user chose |
| **R4** | **The BANNED lexicon covers Groundwork's words, not the user's.** Kept requests are marked as the user's text and excluded from the scan | a user who asks *"am I on track?"* must not trip the test |
| **R5** | **Kept requests are escaped, and capped in length and count.** The docs say plainly that the user's own backup file includes their settings, and so their requests. That is the user's file and action, not Groundwork sending anything | free text on the page; honesty about *"never sent"* |
| **R6** | **Additions are saved one at a time from the latest layout** | two quick additions must not overwrite each other |
| **R7** | **The model matcher never blocks the page.** It runs in the background with a timeout, and any answer that is not exactly one catalogue id counts as *"none"* | K2, plus a timeout |

Expected changes, not bugs: s131's pinned route list gains the new endpoints, as items 22 and 29 did. The
mechanism lives in its own module, inside s30's borrowing cap.

---

## 7. The first slice (2026-10-01)

Rob: *"Build it."* K7's first slice:
- the mechanism;
- the search matcher with confirmation;
- kept requests;
- **Net worth over time**.

The other five catalogue entries and the model matcher (R7) come later, each by ruled addition.

| piece | where | what it does |
|---|---|---|
| **the catalogue (K1, R1)** | `server.TILE_CATALOGUE` | The seven defaults plus `gwNetWorthTrendCard`, each with a title and plain words. **The one source**: an `assert` ties its defaults to `DASHBOARD_TILES`, and `/prefs` gives the page the user's tiles (defaults plus added) and every title. `dashboard.js` keeps no list or titles of its own |
| **matching (K2)** | `match_tile_request`, `POST /api/dashboard/ask` | A phrase from an entry found in the request scores 3, and a shared content word scores 1; the best entry wins at 2 or more. The words decide, nothing else. Returns the match with `backed` / `needs`, or none |
| **confirming (K2, R2, R6)** | `POST /api/dashboard/add` | **Only a catalogue id**: a parameterised or unknown id gets 400. Asking for a hidden default shows it. A catalogue entry is added only if the record backs it (409 with its needs otherwise). **The server merges into the latest stored layout**, and `PUT /layout` cannot drop what was added |
| **evidence (K3, R3)** | `_tile_evidence`, `GET /api/dashboard/tile/net-worth` | Net worth over time needs at least 2 snapshots. A chosen tile that loses its evidence **stays the user's** and returns `{backed: false, needs}`, so the tile says what it needs in place |
| **kept requests (K4, R5)** | `dashboard_tile_requests`; `POST /api/dashboard/requests/delete` | No match keeps the words with their date. Capped at **200 characters and 50 requests**. Deletable by the user. **Read only by the three routes that keep, show and delete them**, pinned by an AST test. Never sent: the page calls only the dashboard's own endpoints. *Footnote, R5:* the user's own backup file contains their settings, so it contains these requests. That is their file and their action |
| **the page (R4)** | `static/js/teaching/asktile.js` (dashboard.js calls it after layout) | An *Ask for a tile* box in Your summary. *"Add 'X' to your summary?"* with Add / No. *"'X' is already on your dashboard"*. The needs sentence. *"Groundwork can't show that yet. Your request is kept below, in your words."* The kept list is **escaped and marked `data-gw-user-words`**, so the BANNED lexicon checks Groundwork's words only |
| **the tile** | `tiletext.netWorth` (Node-tested), `asktile._netWorthTile` | *"Net worth: $X on <latest>. First saved: $Y on <first> - a change of ±$Z across N snapshots."* The source line says Groundwork does not fill the gaps between snapshots |

**Found in the page run, fixed and pinned:**
- **Snapshot dates come in two shapes.** The user saves a day (`2026-08-31`); the app's own monthly snapshot saves a month (`2026-10`). The tile showed *"Invalid Date"* for the month.
- It now shows a month as a month, never invented into a day.
- s134 runs the page's own formatter on both shapes.

**Found, named, not changed (out of scope, shared with 1.x):**
- **The app's monthly net worth snapshot counts missing account balances as $0.** On the test database (accounts with no balance entered) it recorded *-$2,800* (the Visa balance, against $0 of assets).
- The tile reports the record faithfully, but the snapshot writer has the absence-as-zero shape.

**Tests: `smoke_sections/s134_ask_for_a_tile.py`, 28 checks.**
- **K1 and R1:** the catalogue; /prefs as the one source; no copy in dashboard.js.
- **K2:** Ak1, Ak7, Ak4, and one everyday word is not a match.
- **K3 / R3:** evidence through a session with a known count; /add 409 when not backed; the tile computed from snapshots; a tile that loses its evidence stays and says what it needs.
- **R2:** parameterised and unknown ids refused by /add and the layout.
- **Ak7 / R6:** a hidden default shown, and two additions both survive.
- **K5:** the layout cannot drop an addition.
- **K4 / R5:** the honest no, the 200-character and 50-request caps, Ak8 delete, the readers pin, the page calling only its own endpoints.
- **R4:** the user's words escaped and marked.
- **R7:** no model call in this slice.
- **In Node:** the tile's words, including the needs line, and the month-date formatter.

s131's pinned layout and route list are updated as expected (the layout now carries `added`; four new routes).

**Seen in the page** (throwaway database, built-in browser):
- *"show my net worth over time"* went to *Add 'Net worth over time'?*, then Add, and the tile appeared in Your summary and stayed after a reload.
- *"am I on track with my credit score?"* got the honest no, with the words kept, dated and deletable.
- The BANNED scan of Groundwork's text was clean, while the full page text, including the user's own words, contained *"on track"*. R4 is working as ruled.
- No errors.

---

## 8. Acceptance: Rob, 2026-10-01

*"I accept."* The first slice is accepted at master `4181006`, gate 2039 / 0. Item 28 stays open for its remaining
slices, each a small ruled addition under K1:
- savings funds pace;
- recurring charges;
- one category over time (the first parameterised entry, under R2);
- EIA energy prices;
- the working picture;
- then the local-model matcher (R7).

Named, not part of this item: the app's monthly net worth snapshot counts missing balances as $0.

---

## 9. The remaining slices (2026-10-01)

Rob: *"Build Item 28."* The five entries named in §1 and the model matcher (K7's last step).

| entry / piece | record test (K3) | what the tile says |
|---|---|---|
| **Savings funds** (`gwFundsCard`) | an active savings fund | each fund: what is still to go, the pace (put in or planned), the finish in months, and the months to its deadline. It uses the same answer as `/api/sinking-funds/pace`, so a break in contributions (item 25) says the date is the plan's |
| **Recurring charges** (`gwRecurringCard`) | a charge repeating at least three months (`trim_candidates`) | the count, the monthly total, and each charge at its monthly cost with its category |
| **One category over time** (`cat:<category>`) | **R2's one parameterised shape:** a category in the ledger, seen in at least three recorded months | *"Dining, by month: June 2026 $310.00; July 2026 none recorded; ..."* plus the average over the months it appears. **A gap stays a gap** |
| **Energy prices** (`gwEnergyCard`) | an EIA price **already on record**; the dashboard fetches nothing | electricity and gasoline with area and period. Natural gas with none on record says so, until item 26's Ohio fix |
| **What Groundwork has concluded** (`gwPictureCard`) | a concluding reading or a statement | up to four readings said as the record's, the user's statements as theirs, and a button to open the working picture |

- **Matching with the ledger's categories:** a category named in the request competes on the **same scale** as the catalogue. With a category called *Gas*, *"gas prices"* is still the energy tile, while *"gas over time"* is the category.
- **R1:** `/prefs` gives added category tiles their titles.
- **R2:** `_catalogue_entry` admits only a catalogue id or `cat:<1–80 chars>`, and `/add` then requires the category to be in the ledger and backed.

**The model matcher (K2, R7)**, `model_match_tile`:
- **When it runs:** only when the search finds nothing. Only when AI is on **and** a local model is actually answering (`_model_ready`: one 1-second look, remembered for a minute).
- **What it is asked:** the ids, the titles and the request, in a background thread with a **12-second** cap.
- **What counts as a match:** only an answer that is exactly one catalogue id. A sentence, a parameterised id, an unknown id, an error, a timeout or no model is *none*.
- **What the page does:** shows *"Looking..."* while it waits, and makes no model call of its own.

**Found while building, fixed and pinned:**
- **With AI switched on but no model running,** every unmatched request waited out the full timeout. `_model_ready` makes that cost nothing, and s135 pins it at under half a second with no model call.
- **A real local model during the gate.** s134 sends 55 unmatched requests; on a machine with a model running that took over eight minutes of live, nondeterministic calls. s134 now holds the model matcher off; it tests the search. s135 tests the matcher with controlled answers.

**Found in the page run, for Rob:**
- **The installed local model is a "thinking" model.** Asked the K2 question about *"how are my rainy day pots doing"*, it took about **32 seconds**. It ignored the 12-token limit, and its answer was paragraphs of reasoning that **did reach `gwFundsCard`**.
- As ruled, that is *none*: the cap cut it off, and the words never reached the page. **R7 worked exactly as designed.**
- **But on this machine the matcher will rarely match.** Making it useful needs Ollama's constrained output (a JSON schema limiting the answer to the catalogue ids) and thinking switched off. That is a change to the shared AI call, so it is **named, not made here**.

**Tests:**
- **`smoke_sections/s135_tile_catalogue.py`, 26 checks:**
  - each entry's record test, both ways;
  - the category entry end to end (2 months not backed, 3 added, the tile with its gap, its title from /prefs);
  - R2 refusals;
  - the category-versus-catalogue scoring;
  - each entry found by its words;
  - the model matcher: exact id, a sentence, a parameterised id, an unknown id and an error, the 0.3-second cut-off, no model, AI on with no model running costing nothing, and asked only when the search finds nothing;
  - all five tiles' words in Node, with the BANNED lexicon.
- **s134** (28 checks) is updated for the larger catalogue and holds the model off.
- **s131's** route list gains the five tile endpoints.

**Seen in the page** (throwaway database with a fund, a recurring charge and groceries):
- *"show my savings goals"*, *"my subscriptions"* and *"groceries by month"* each became a tile with real figures.
- *"energy prices"* said what it needs, because a fresh database has no EIA price.
- *"how are my rainy day pots doing"* went to the model and came back *none* at the 12-second cap, as above.

