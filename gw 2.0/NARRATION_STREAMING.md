# Item 10 — Narration that appears as it is written, checked before it shows

Opened for ruling 2026-10-09 (Rob: *"Open item 10 and 58"*, after *"would this also speed up the ai voice in the
program?"*, and *"lets not worry about never break the rules as much as giving the guardrails a foundation now
instead of hoping they holdup"*).

Item 10 was DECIDED on 2026-08-30 (*narration is streamed*; `MODEL_PLACEMENT.md`, blueprint Appendix H) and measured
in `STREAMING.md` on 2026-09-20, when the model ran in Ollama. It was never built. **S1–S9 RULED 2026-10-09 (Rob: "approve S1–S9 as recommended")**: S1 (a), sentence-gated reveal; master only (S8); CPU-only before/after timing needed for acceptance (S7). **No code yet:** the build needs its own go-ahead.

## 1. What is true today (measured 2026-10-09 on master a729e15)

- **Nothing streams.**
  - `core/engine.py` `chat()` calls `create_chat_completion` and returns only the finished text.
  - `/api/ai/chat` (`_ai_chat_local`) returns it whole.
  - `callAI()` in `app.js` waits for it.
  - The engine is llama-cpp-python 0.3.35 in-process (item 31), which can stream (`stream=True` yields pieces as
    they are made). The pieces just aren't used.
- **The voice check reads the whole answer.**
  - `_voiceGateCheck(text, findings, truncated)` runs once on the complete text.
  - On a failure, `callAI()` makes up to 2 corrective retries, all hidden, before falling back to its honest
    no-AI text.
  - That is why *a fabricating model never reaches the screen*: nothing is shown until the check has read it all.
- **What the wait is made of** (`STREAMING.md`, measured on a GPU machine with Ollama):
  - Generation was 75–95% of the wait. Streaming turns that into visible progress.
  - The silence before the first word is the prompt being read. Only a shorter prompt helps that.
  - Retries multiply the wait: one live run took 71 + 49 + 45 = 165 s and ended in the fallback.
  - **No CPU-only computer has been measured** (item 11), and that is probably what testers have.

## 2. Points for ruling

**S1. The check and the screen: the foundation.** The rules split by what they need to see:
- **Sentence-local rules** can judge each sentence as it finishes: the banned words, the verdict and advice lists,
  and every number in the sentence matched against the findings.
- **Whole-answer rules** need the end: the answer finished rather than cut off (R10), and coverage of what had to be
  said.

Options:
- (a) **Sentence-gated reveal.** Each sentence appears only after it passes the sentence-local rules. If a sentence
  fails, generation stops, the shown sentences are withdrawn, and the answer is retried out of sight (S2). The
  whole-answer rules run at the end. If they fail, the shown text is withdrawn and replaced by the retry or the
  honest fallback, with a line saying it was rewritten.
- (b) **Progress, not text.** Generate out of sight and show *"Writing… 60 words"*, then reveal after the full
  check. It's honest and simple, but the wait is still the whole generation.
- (c) Stream raw text, check at the end, and retract on failure. Unchecked text reaches the screen, which breaks
  the rule above.

*Recommended: (a).* It keeps *nothing unchecked reaches the screen* true sentence by sentence, as an enforced
structure rather than a hope, and it's where nearly all the speed comes from.

**S2. Retries out of sight.** A failed sentence stops the stream, and the retry runs with the same up to 2 attempts
and the same cited fixes as today. The user sees *"Rewording…"*, not the rejected text.
*Recommended.*

**S3. The engine streams.** `engine.chat_stream()` yields pieces from `create_chat_completion(stream=True)` and
holds the engine's lock for the whole generation, one at a time as now. It reports the same finish reason (`stop` or
`length`) at the end, so R10 keeps working.
*Recommended.*

**S4. The route.** `/api/ai/chat` with `stream: true` answers as a stream of events on the same local server.
`callAI()` reads it with `fetch` and `getReader()`. Nothing leaves the computer: s52 (no off-device AI) still holds.
*Recommended.*

**S5. Which surfaces first.** The long narrative ones: the monthly report and the category narratives. Short answers
(a sentence or two) stay as they are, because streaming gains nothing there.
*Recommended.*

**S6. Stop.** A *Stop* button while it's writing ends the generation and frees the engine. What was already shown
stays, marked as stopped. A stopped answer is never treated as finished.
*Recommended.*

**S7. Measured before and after, on a CPU-only computer** (folds in item 11). For each surface: the time to the
first shown sentence and the total time, before and after, on a machine without a GPU. Acceptance needs those
numbers.
*Recommended.*

**S8. Lines.** Master only (the 1.x rule: this is not a data-loss, wrong-figure or security fix).
*Recommended.*

**S9. Tests.**
- A fabricating stream never shows its bad sentence.
- A later failure withdraws what was shown.
- A cut-off answer never reads as finished.
- Stop ends the generation.
- AI off is unchanged.
- The whole-answer path still gives the same verdicts as today on the existing voice fixtures.

*Recommended.*

## 3. Not decided here

- **Item 12 step 2:** the token caps per surface. Its own ruling.
- **Shorter prompts** for the silence before the first word. Measured per surface during S7.
