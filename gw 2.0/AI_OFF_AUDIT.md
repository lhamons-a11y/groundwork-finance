# The AI-off audit (item 32 L4; ASKED_FACTS A10)

Run 2026-10-12. Rob: *"agree let's complete everything in the order you suggest ... ok to build all."*

This is L4b's own pass. Item 32 makes it the exit criterion for 2.0: every surface must be complete with AI off
(L4a), and the same must hold with AI on but not working (L4d).

## 1. How it was measured

- **On a copy of Rob's real database,** made with SQLite's backup API (`scratchpad/audit_server.py`). The live
  database and Rob's settings were never touched.
- **Two conditions**, each served by the real server code:
  - **AI off:** `ai_enabled = false`.
  - **AI failing:** `ai_enabled = true`, and the model started the way the launcher starts it, but with the model file
    missing. The engine reports `unavailable / missing`, which is one of item 31's states (L4d).
- **The surface list comes from the code** (L4a), not from memory:
  - every `callAI(` caller in `app.js` (10; the teaching modules have none);
  - every server-side model use: `/api/ai/chat`, the Ask box's `engine.choose` (item 72 stage 3), and the tile
    matcher (`model_match_tile`, guarded by `_model_ready`).
- **In the browser, under each condition:**
  - every page in the sidebar opened in turn, with its text, any spinner left running, and every error recorded
    (`_gwErrorLog`);
  - every report in Reports opened;
  - each AI button pressed;
  - the Ask box asked three questions.
- **Found on the way:** the browser pane was hidden, which throttles page timers to almost nothing. The sweep waits on
  network round trips instead, so the measurements were not cut short.

**Result before the fixes:**
- No page raised an error under either condition.
- No spinner was left running.
- **Six things were wrong (F1-F6)**, listed below. Four were real gaps, one (F4) turned out not to be reachable in
  the app, and one (F6) was a silent dead end.

## 2. Findings and fixes

| | Found | Fixed |
|---|---|---|
| **F1** | Trophies, AI off. *"Groundwork's money story so far - AI-written recap"* still offered **✦ Generate**. Pressing it put the model's input on the page: a "SUMMARY" header, a literal `---`, and the raw list. | With AI off the card is the facts: *"16 of 25 achievements earned. The most recent: Chipping away, Jul 11, 2026."* No Generate button. |
| **F2** | Monthly report, AI off. The note box said *"Anything unusual? (AI reads this)"*, and the report window's toolbar said *"AI reads this"*. | It says *"(kept with this report)"* with AI off. The toolbar label hides. |
| **F3** | Trip planner, AI off. *"Analyze that trip"* (learning from a past trip) and *"Read it"* (a pasted quote) were both offered. Both need the model, so each ended in *"Couldn't … Check your AI settings"*. | The past-trip card hides without AI (it is the model's work). *Read it* says *"Reading a pasted quote needs AI, which is off. A whole itinerary (Expedia, Booking.com, airline receipts, hotel folios) is read without AI: use Read as a whole itinerary."* |
| **F4** | AI on, engine never started: *"Local AI is not running. Turn on AI features in Settings to start it."* This is circular when AI is already on. | **Not reachable in the app.** The launcher always starts the engine when AI is on, and the toggle starts it too. It appeared only on a bare server. The real failure messages (processor, missing file, mismatched file, runtime, failed load) are specific and correct. No change. |
| **F5** | AI on, model unable to run (missing file). The sidebar said *"✦ AI enabled · on your machine"*, and every AI button stayed offered, each failing on its own. | A model that can **never** run here (processor, missing or mismatched file, runtime, failed load) makes `aiEnabled()` false for every surface. Every surface then behaves exactly as with AI off, which is the complete version. The sidebar says *"AI unavailable on this computer"*, with the engine's own reason on hover. A model still **loading** is not unavailable: callers wait, as before. |
| **F6** | The Ask box with AI off. *"duplicate transactions"* got *"That question is outside what Groundwork understands"*, although finding duplicates is one of item 72's record checks. With AI off nothing could route a question to a check, and *Check my records* appeared only if the question contained a word like "why". With AI on but unable to run, the route also fell to "none": the engine's specific reasons (`missing`, `cpu` …) were not counted as off. | The route still never asks a model with AI off. It now answers `off` **with the fixed list of checks**, and the Ask box offers them: *"If this is about your records, Groundwork has these checks. Which one?"* That is the same chooser the AI shows when it is unsure. Every reason except a refused answer now counts as off. |

## 3. Every surface, and what it shows with AI off (for Rob's ruling, L4e)

L4e: *"useful"* is Rob's ruling, surface by surface. Each line is what was measured with AI off, after the fixes.
**AI failing now shows the same** (F5).

| # | Surface | With AI off | Ruling |
|---|---|---|---|
| 1 | Sunday check-in (`writeSundayCheckin`) | The week's facts in full (spending, the month so far, interest, bills and pay ahead, price changes). No written lesson, and no *Write it now*. | |
| 2 | Monthly review after an import (`monthlyReviewAfterImport`) | The plain summary is the month's review (item 75 M9). | |
| 3 | Dashboard projection (`_renderProjectionAI`) | The computed fallback (`_renderProjectionFallback`): the same figures, no prose. | |
| 4 | A report's *Groundwork's analysis* (`_rcSendAI`) | The report is complete. Where the analysis would be: *"Turn AI on in Settings to enable Groundwork's analysis."* | |
| 5 | A report's follow-up question (`_rcFollowUp`) | Not offered (it follows an analysis). | |
| 6 | Monthly report *Generate / Write it anyway* (`_rcMonthlyGenerate`) | Not offered. The report's figures and *What this month cost* lines are computed (*"not written by the AI"*). | |
| 7 | Evidence intros (`_evidenceIntro`) | The evidence entry itself, without the one-line intro. | |
| 8 | Trophies' money story (`trophy_room_narrative`) | F1: the count and the most recent achievement. | |
| 9 | Trip: learn from a past trip (`_learnFromPastTrip`) | F3: the card is hidden. | |
| 10 | Trip: a pasted quote (`_readTripQuote`) | F3: says it needs AI, and points at the itinerary reader. | |
| 11 | Trip: an itinerary from an unknown sender (`_readTripItineraryWithModel`) | Known senders are read without AI. For any other: *"…reading it takes the AI model, which is off. You can enter the trip's figures in the form below."* | |
| 12 | The Ask box (`engine.choose`, item 72) | How-to answers come from the guide, never AI. Questions about the records: F6, the fixed checks to choose from. | |
| 13 | Ask for a tile (`model_match_tile`, item 28) | Search only. The model is never asked (`_ai_is_enabled` and `_model_ready` guard it). | |
| 14 | Every page in the sidebar (15) and every report (11) | All load, complete. There are no errors and no endless spinners under either condition. | |

**Nothing AI-related loads with AI off (A9).** `engine_launch()` starts the model only when AI is on. The night run
writes no check-in and falls back to the plain review.

## 4. Found outside the audit (each its own task)

1. **The dashboard projection's "high-leverage category"** picks *Debt*, reads 2026's whole year of debt payments
   ($18,540) as this month, and offers a $16,729-a-month cut. It is hidden today only because Rob's debt balances are
   unverified.
2. **The Monthly Report counts transfers as spending.** September 2026's top category is *Transfer $5,877.29 (40%)*,
   and the transfers are inside SPENT.

Both are offered to Rob as separate tasks. Neither is AI.

## 5. The gate

**s217** holds F1-F3, F5 and F6:
- with AI off, the chat route never asks a model, and the Ask box route answers `off` with the checks;
- with the engine set to `unavailable / missing`, the status names why, and the route still offers the checks;
- the page-side rules are checked in the source.

s193 and s198 were updated. They had pinned the old page-side `if (aiEnabled())` around the router, and the same rule
(*the model is asked only with AI on*) is now pinned where it is enforced: in the route, before `engine.choose`.

**The browser sweep is not in the gate.** It needs a browser. L4a asks for *"one pass … visits every AI surface"*.
The gate's s217 covers the server and the page code; the full visual sweep is this document's measurement, to be
repeated before release (item 82).

## 6. Status

- **Built 2026-10-12. ACCEPTED 2026-10-12** (Rob: *"Yes audit ai notes"*).
- **L4b's exit criterion:** the audit passes on master with every surface listed. It will be met when this is pushed.
- **L4e:** the *Ruling* column above is Rob's.
