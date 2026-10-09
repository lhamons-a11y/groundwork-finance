# Item 12, step 2 — Room to finish: each AI surface's length cap

Opened 2026-10-09 (Rob: *"open item 12 step 2"*, *"ok measure them after the gate"*). Step 1 (R10: a cut answer is not
an answer) is on both lines and ACCEPTED (2026-10-03). Step 2, the caps themselves, was never ruled. **K1–K8 RULED 2026-10-09 (Rob: "I accept these rules as written")**: K3 (a), keep the finished sentences and mark them shortened; master only (K8). **BUILT 2026-10-09 (Rob: "build item 12 step 2")**: the caps and word lengths in `app.js` (K1, K2), `_gwKeepFinished` and the shortened mark in `callAI` and the stream (K3), the classifier in batches of 10 (K4), `generateReport` removed and its buttons pointed at the live report (K5), `s171` (K6 included). K7 measured, then a length limit added (§3). **ACCEPTED and CLOSED (Rob, 2026-10-09: "I accept items 10 and 12 step 2"), gate 2699 / 0.**

## 1. What is true today (measured 2026-10-09 on master 65048b4)

**The caps** (from the code):

| Surface | Cap (tokens) | What the prompt asks for |
|---|---|---|
| Monthly report (`monthly_report_v2`) | none set, so the server default **1000** | "3-4 paragraphs" |
| Report narratives (`_rcSendAI`: debt, savings, category, annual …) | 350 | "3 short paragraphs max" |
| Follow-up answers | 200 | "1-2 short paragraphs max" |
| Sunday check-in | 100 | "Two sentences" |
| Dashboard projection | 140 | "Two sentences max" |
| Old monthly report (`monthly_report`, `STREAMING.md` T8: unreachable) | 250 | |
| Trip transaction classifier (JSON, ungated) | 200 + 40 a transaction, up to 4,000 | |
| Trip quote reader (JSON) | 400 | |
| Trip budget (JSON) | 800 | **removed by item 59 P1** |

**What they actually use.** Measured on the real model, the shipped CPU engine on an i7-12800H laptop. Two runs each
with the surface's own system prompt (gated ones with `GW_VOICE` appended, as `callAI` does), and representative
figures in the user prompt (stand-ins, not a household's data):

| Surface | Cap | Run 1 | Run 2 |
|---|---|---|---|
| Monthly report | 1000 | 540 tokens, finished (44.5 s) | 383, finished (22.8 s) |
| Report narrative (debt) | 350 | **350, cut** (34.7 s) | **350, cut** (20.7 s) |
| Follow-up | 200 | 114, finished | **200, cut** |
| Sunday check-in | 100 | **100, cut** (52 words for "two sentences") | **100, cut** (46 words) |
| Projection | 140 | 77, finished | **140, cut** |
| Trip classifier, 20 transactions | 1000 | **1000, cut** (67 s) | 339, finished |

**7 of 12 runs hit the cap.** Each would be rejected by R10 and reworded, which is up to two more full generations,
and often ends in the fallback. **The model doesn't keep to "two sentences"** with the voice rules appended: it
wrote 46–52 words where two sentences is about 30.

**Item 10 makes this visible.** A streamed report that hits its cap shows its checked sentences one by one. Then the
end-of-answer check sees the cut (R10), withdraws everything the person has just read, and shows *"Rewording…"*.

## 2. Points for ruling

**K1. Caps sized from what finished answers use.** Each gated surface's cap is at least twice the longest finished
answer measured. For the ones that never finished, it's twice the cap they kept hitting, re-measured after:

| Surface | Cap now | Cap proposed |
|---|---|---|
| Monthly report | 1000 (default) | 1000, set explicitly |
| Report narratives | 350 | 700 |
| Follow-up | 200 | 400 |
| Sunday check-in | 100 | 200 |
| Projection | 140 | 280 |

*Recommended.*

**K2. The prompt names the length in words.** For example *"in about 40 words"* instead of *"Two sentences"*, so the
cap is a backstop rather than the thing that ends the answer. It's measured again under K7. If the model still
overruns, the cap catches it (K3).
*Recommended.*

**K3. At the cap: keep the finished sentences and say so.** This changes how R10 is handled, not what it protects.
Today a cut answer is rejected and rewritten.

Proposed: when the stop reason is the cap, the unfinished last sentence is dropped. The finished sentences, each
already through the voice check, are kept and marked *"Shortened at the length limit."* R10's purpose holds: a cut
answer is never presented as finished. And with item 10, nothing the person has read is withdrawn.
- (a) Keep and mark, as above.
- (b) Today's reject-and-reword.

*Recommended: (a).* If fewer than two sentences survive, it falls back to (b).

**K4. The trip classifier in batches.** It classifies 10 transactions a call (cap 600), not all at once (up to
4,000), so one long trip isn't one minute-long call that the cap cuts. A batch whose JSON doesn't read is retried
once, and then those transactions are left unclassified and said.
*Recommended.*

**K5. The unreachable old monthly report goes** (`STREAMING.md` T8: unreachable, and it would narrate $0.00 if it
were reached).
*Recommended.*

**K6. Every gated AI call declares its cap.** A gate check fails if a gated `callAI` passes no `max_tokens`, so the
server's 1000 default is never a narrative surface's cap by accident.
*Recommended.*

**K7. Measured again, for acceptance.** Every surface, two runs, on the CPU engine: none of the narrative surfaces
hits its cap. The same table as §1, after.
*Recommended.*

**K8. Lines.** Master only. 1.x has R10 (step 1) but not item 10. A cut answer there falls back honestly, and that
isn't a wrong saved figure.
*Recommended, and this is your call under the 1.x rule.*

## 3. K7 measured after the build (2026-10-09, the CPU engine, three runs each)

| Surface | Cap | Tokens per run | |
|---|---|---|---|
| Monthly report | 1000 | 520, 442, 416 | all finished |
| Report narrative | 700 | 426, 327, 312 | all finished (all were cut before) |
| Follow-up | 400 | 162, 126, **400 cut** | 217 words for "about 100" |
| Sunday check-in | 200 | **200 cut**, **200 cut**, 153 | 82–97 words for "two sentences, about 40 words" |
| Projection | 280 | 84, 171, 85 | all finished |
| Trip classifier, 10 per batch | 600 | 227, 454, 176 | all finished |

So 15 of 18 runs finished, against 5 of 12 before. The model doesn't keep to a short length.

- **Rob chose (b) first, raising the caps.** At 600 and 300, each surface still ran over in one run of three (326 and
  139 words), and a runaway just filled the bigger cap (40 s).
- **Rob then ruled (a)** (*"a and agree the cap can go to 200 and 400"*): **a surface that promises a length gets
  it, enforced in code.** `payload.max_sentences` makes `callAI` show at most that many finished sentences, each
  already through the voice check, marked *"Shortened at the length limit."* when it trims:
  - the Sunday check-in: 2;
  - the projection: 2;
  - follow-ups: 5.

  The caps are back at 200 and 400, so a runaway is stopped sooner. `s171` holds it.
