# Item 62 — The AI log: what was sent, kept in one place

**ACCEPTED + CLOSED 2026-10-10** (Rob 2026-10-10: "i accept all").

Opened 2026-10-09. Rob: *"should we have a page maybe in settings we have a page that shows the what was sent to ai
log that they could select and view, That way we can clean up the look of the ui and still show the users what
data was used."*, then *"yes"*. **G1–G8 RULED as recommended (Rob 2026-10-09: "I accept item 59, 60, 62"). BUILT 2026-10-10** (Rob: "build all items that have been ruled on"): the `ai_log` table (SCHEMA_VERSION 20261010-ai-log, pins, fixture), written by the chat route only - every attempt, streamed or not, finished, shortened, stopped or unanswered; each attempt's voice verdict reported back from the page; Settings -> AI features -> AI log (grouped by request, Keep the log, Clear); the panels' one line "Sent to AI on this computer · see it in the log"; backups scrub it (rows deleted, file compacted) and JSON exports leave it out unless ticked; 90 days; s184. The old "could search the web" line went with the fold-out. Two older Node tests (s170, s171) now pass their page code through a file: it had grown past Windows' command-line limit. Awaiting the gate and acceptance.

## 1. What is true today (measured 2026-10-09, master)

- **Every report AI panel (`_rcRenderAIPanel`) carries:**
  - the answer;
  - Copy;
  - **"The numbers behind this analysis"**, a fold-out with the figures;
  - the follow-up box;
  - **"View what was sent to AI"** (`_renderAIDisclosure`), a fold-out with the full instructions and the financial
    summary as sent;
  - an attribution line;
  - Regenerate.
- **Calls with no panel show nothing:** the trip classifier, the quote reader and the other JSON calls.
- **Rejected answers are stored and never shown.** `/api/ai/voice-miss` keeps the voice check's rejected text for
  hardening, out of the user's sight.
- **The disclosure still says** *"This request could search the web for current prices"* when a web-search tool is
  attached. That is untrue since cloud AI was removed (item 63).

## 2. Points for ruling

**G1. The log.** Settings → *AI log* lists every AI call, newest first. Each entry has:
- the surface ("Monthly report", "Trip classifier" …) and when;
- what was sent: the instructions and the data, exactly;
- what came back;
- whether the voice check passed it, and if it rewrote it, which rules and how many attempts;
- whether it was shortened (item 12) or stopped (item 10);
- *"run on this computer"*.

*Recommended.*

**G2. The panel, cleaned up.** "View what was sent to AI" leaves the panel, replaced by one small line: *"Sent to AI on
this computer · see it in the log"*, which opens that exact entry. **"The numbers behind this analysis" stays** on the
panel: it's the figures' working, and the transparency standard (item 39 U7) keeps working beside the figure.
*Recommended.*

**G3. A record, never an input.** No engine, prompt or narrator reads the log. It's what Groundwork sent, shown to the
user, and nothing learns from it (*no silent learning*). A gate check fails if anything but the log page and its
routes reads it.
*Recommended.*

**G4. Kept for 90 days, cleared on request.** Entries older than 90 days are deleted. *Clear the log* deletes all of
them. A *Keep the log* setting turns logging off (the panels still show their numbers).
*Recommended.*

**G5. Out of exports, unless chosen.** The log holds financial summaries, so it's left out of exports and backups
unless the user ticks *include the AI log*.
*Recommended.*

**G6. The voice-miss record becomes part of it.** The rejected attempts already stored are shown in the entry they
belong to, so a rewrite is visible, not hidden. Nothing new is collected.
*Recommended.*

**G7. Storage.** One table, `ai_log`, with a SCHEMA_VERSION bump, the s51 pin and an upgrade fixture. Written by
`callAI`'s server route only.
*Recommended.*

**G8. Lines and tests.** Master only. Tests:
- every call lands one entry, its rewrites included;
- the panel's link opens its entry;
- nothing but the log page reads the table (the G3 mutation);
- 90-day pruning and Clear;
- export excludes it by default;
- AI off logs nothing.

*Recommended.*
