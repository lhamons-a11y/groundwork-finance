# Item 63 — The last cloud-AI leftovers

Opened 2026-10-09. Rob: *"lets clear all former cloud ai referenced."* Cloud AI was removed from both lines in item
21 (`CLOUD_AI_REMOVAL.md`, 2026-09-25) and Ollama in item 31. Measured 2026-10-09 on master, these remain. **L1–L6 RULED 2026-10-11 as recommended (L3: (a), keep the notices; L6: master), BUILT 2026-10-11 (master 15c8f40, gate 3115/0); ACCEPTED + CLOSED 2026-10-11 (Rob: "I accept"); see §3.**

## 1. What remains

**Untrue text a user can see:**
1. `app.js` (the AI-off message): *"Add an API key in Settings to enable Groundwork's analysis, or switch to local AI
   (free, no key needed)."* There's no key and no switch.
2. `_renderAIDisclosure`: *"This request could search the web for current prices."* It's shown when a call carries a
   `web_search_20250305` tool. Nothing can search.
3. `generateTripBudget`: *"Always search for real current prices"*, the `web_search` tool and the *"✦ AI · live
   prices"* label (two places). That is item 59 P1, on both lines.

**Internal leftovers, invisible to users:**
- the `provider` field, always `'local'`, carried through `callAI`, the panels and the report cache;
- the "Settings → AI provider pane" comment;
- `_server_ai_call`'s *"Call the active AI provider"* docstring;
- a "cloud-key case" comment.

**Kept on purpose, because they're correct or protective:**
- *"No cloud AI. Nothing is sent to an AI service, ever"* (website, FAQ);
- the settings guards that drop `api_key` and `ai_provider`;
- **s52** (fails if cloud AI returns);
- the EIA key (government energy data, not AI);
- the merchant words "anthropic", "openai" and "claude.ai" in the category rules (they recognise subscriptions).

**The two one-time upgrade notices** (`_cloudAiRemovedNotice`: *"Groundwork no longer uses cloud AI… Your Anthropic
API key has been deleted"*; `_ollamaNotice`). They're shown once, only to someone upgrading from 1.1.0 or earlier.

## 2. Points for ruling

**L1. The untrue user-facing text goes.**
- (1) becomes *"AI is off. Turn it on in Settings to get Groundwork's analysis; everything else works without it."*
- (2) is removed with its tool check.
- (3) is built with item 59 P1.

*Recommended.*

**L2. The internal leftovers are tidied.**
- The `provider` field is removed. The attribution line says *"on this computer"* without it.
- The comments and docstring say what is true.

*Recommended.*

**L3. The upgrade notices.**
- (a) Keep them: they're how an upgrader learns their key was deleted and Ollama is no longer needed.
- (b) Remove them.

*Recommended: (a), until the release after 2.0, when no one can still be upgrading from a cloud version.*

**L4. Kept as listed above:** the "no cloud AI" statements, the guards, s52, the EIA key and the merchant words.
*Recommended.*

**L5. s52 learns these.** It fails on *"API key"* in AI text, *"search the web"*, `web_search`, *"live prices"* and a
`provider` other than local, so they can't return.
*Recommended.*

**L6. Lines.**
- L1's (3) on both lines (item 59).
- The rest master only: a misleading line isn't a wrong saved figure.

*Recommended: master; your call under the 1.x rule.*


## 3. Built (2026-10-11)

- **L1:**
  - The AI-off line in Reports is now *"AI is off. Turn it on in Settings to get Groundwork's analysis; everything
    else works without it."*
  - The web-search disclosure and the trip budget's AI prices were already gone (item 59).
- **L2:**
  - The `provider` field is gone from `/api/ai/chat`, the stream's end event and `/api/ai/status`, and from every
    place the page carried it: `callAI` results, report panels and the report cache. The attribution line reads
    the model only.
  - The "AI provider pane", "active AI provider" and "cloud-key case" comments now say what is true.
- **L3 (a):** the two one-time upgrade notices stay.
- **L4:** the "no cloud AI" statements, the settings guards, s52, the EIA key and the merchant words all stay.
- **L5:** s52 fails if *"Add an API key"*, *"search the web"*, `web_search`, *"live prices"* or *"switch to local
  AI"* returns to the page, or a provider returns to an AI reply. s26, s60 and s170 now check that no provider is
  named.
- **L6:** master only.
