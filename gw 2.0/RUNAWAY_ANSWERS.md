# Item 97 — Answers that don't end

Opened 2026-10-18 (Rob, ruling G4″ (c): *"fix the runaway answer as its own item"*). **No code.** Measured on
gpu-engine after `2a853c1`. Nothing in the engine was changed. Every measurement below sets its stops in the test
harness only.

## Summary

The narrator sometimes finishes a good answer and then keeps writing: a made-up new instruction ("You write a
comprehensive…"), a second copy of its answer, new "Computed facts:". Nearly every invented figure in the item 95 A/B
was in that tail, on the processor and both graphics chips alike (`GPU_ENGINE.md`, the A/B section). It happens in
about 5–7 answers in 120 on every device.

**The cause is in the text, not the end token.** The model's end of turn, `<|end|>`, already stops the engine
(`llama_vocab_is_eog` is true for it). In a runaway the model never writes it. It writes three or four newlines and
carries straight on in plain text. Once (NVIDIA, seed 3) it wrote `<|user|>` instead, starting a new user turn, and
that token renders as nothing.

**A stop at a run of three newlines removes every runaway, on every device, and changes nothing else.** Measured on
the same 20 seeds × 6 cases at 512 tokens, the shipped settings, with `stop=["\n\n\n"]` and the role tokens added as
stop tokens:

| device | before: gate pass | before: R8 | with the stop: gate pass | with the stop: R8 |
|---|---:|---:|---:|---:|
| processor | 39/120 | 4/120 | 40/120 | **1/120** |
| NVIDIA RTX A1000 | 37/120 | 2/120 | 38/120 | **0/120** |
| Intel Iris Xe | 33/120 | 4/120 | 34/120 | **0/120** |

- **Only tails were cut.** 5 answers changed on NVIDIA, 6 on Intel and 7 on the processor. Each one is an exact
  prefix of its old answer, and the other 102–115 are word for word the same.
- **Every answer now ends on its own:** all 360 finish with `stop`. Before, 3–7 per device ran to the cap.
- **No answer that passes the gate contains a run of three newlines,** on any device or either harness (0 of 217).
  Paragraphs use one blank line (two newlines), so the stop doesn't cut a real answer short.
- **The one R8 left is a different fault.** On the processor's seed 4 the model works out a "~$3,000" total interest
  inside the narration itself. The stop can't touch that, and it shouldn't. The per-sentence voice gate in `app.js`
  is what catches it, as now.
- **Most cut answers still fail the gate, on the usual rules** (R3 smuggled inference, R4 command or cheer) in the
  narration before the tail. Each device gained one pass. The gate rate is unchanged within noise (|z| ≤ 0.6 against
  38/120).

## 1. What was measured

- **The token check.** Every token sampled for NVIDIA's two runaways was logged.
  - Seed 14, `verified_debt_progress`: "…reduce interest payments." then four `\n` tokens (id 13), then "You write a
    comprehensive…". No special token at all.
  - Seed 3, `mixed_movement`: after the answer, `<|user|>` (id 32010) at token 136, then the "Atlas Investments"
    prompt.
- **The role-token stop alone** (`<|user|>`, `<|system|>`, `<|assistant|>` as stop tokens) changed 1 answer in 360:
  seed 3 above. So the newline stop does the work, and the role tokens are a second guard.
- **The app's path is the harness's path.** `core/engine.py`'s `chat()` and `chat_stream()` call
  `create_chat_completion` with the model file's own chat template and no stop strings. `server.py` adds none, and
  callers send caps from 80 to 1000 tokens.
- **Raw answers:** `side-session-notes/local_d42ec9c4-…/gpu_ab_2026-10-17/` (`se_*` role tokens only, `nl_*` both).

## 2. What a user sees today

The narration path's per-sentence gate (`_voiceGateCheck`, item 10) withdraws the answer at the first sentence that
fails. So an invented figure in a tail is caught. But the sentences before it are already on screen: the made-up
instruction is one of them, since it fails no rule until a figure appears. Then the answer is rewritten. The user
saw a strange paragraph appear and vanish, and the narration took twice as long.

## 3. Points for ruling

**U1. Stop every narrator call at a run of three newlines and at a role token.** One constant in `core/engine.py`,
passed on every call (`chat`, `chat_stream`, the grammar-constrained route), plus the model's role tokens as stop
tokens. A cut answer reports `stop`, not `length`, so item 12's R10 and the gate's K3 shortening are unaffected.
*Recommended.*

**U2. Every place that calls the model uses the same stops.** That covers fitting's probe (`engine_fit.py`), the voice
A/B (`voice_discipline_test.py`) and `llm_model_eval.py`, so what is measured is what ships. A smoke section scans
for every `create_chat_completion` call and fails on one that doesn't pass them, as item 89's `LEVER_SURFACES` scan
does. *Recommended.*

**U3. Check the callers that might want three newlines before the stop goes in.** A structured answer (the Ask box, a
list, a report paragraph) could legitimately use a wider gap. None of the six voice cases does. The build inventories
every caller first, with one probe per kind. *Recommended.*

**U4. Fitting compares a chip with the processor, as G4″ (a) ruled.** Fitting reads the six cases on the processor too,
and excludes a chip only when its R8 count is higher than the processor's on the same six. With U1 the runaway is
gone, so what's left is in-answer arithmetic at about 1 in 120. A single six-case read would still exclude an
innocent chip about 5% of the time, and comparing with the processor stops that. *Recommended.*

**U5. Correct the baseline where it's quoted.** `core/engine.py`'s comment says *"gate pass 38/120, R8 violations 0"*.
Measured now on the same harness, the processor gives 39/120 with R8 4/120, and with U1 40/120 with R8 1/120. The
comment should give the harness and the date, and say that the reference is the processor measured beside each A/B.
*Recommended.*

**U6. Acceptance: the A/B on the built engine.** The same 20 seeds × 6 cases at 512 tokens, on the processor, NVIDIA
and Intel. It passes when every answer ends on its own (no `length`), no runaway tail is left, and each graphics family
is no worse than the processor on R8 with gate pass within noise. Plus the full smoke gate. *Recommended.*

**U7. Master only.** This is narration quality, caught by the gate before a figure is shown. It isn't a saved figure,
data loss or security, so item 32 L1 keeps it off 1.x. *Recommended.*

## Closing

This one is small and well measured. The runaway is one behaviour on every device, it starts at a visible marker,
and stopping at that marker removed all 9 runaway-caused R8 violations across the three devices (10 became 1)
without changing any answer that didn't run away. It also settles the oddity behind item 95's Intel exclusion: that was a runaway, not
something about the chip. Nothing here is authorised to build.

## U1-U7 ruled — Rob, 2026-10-18

*"I approve"* (U1-U7 as recommended). The build is not yet authorised.

## Built 2026-10-18 (Rob: "Build now"; s237; no schema change)

**What changed:**
- **U1:** `core/engine.py` adds `STOP = ['\n\n\n']`, passed on every call (`chat`, `chat_stream`, the grammar route
  `choose`). It also adds `install_stops(model)`, which gives the model's role tokens (`<|end|>`, `<|user|>`,
  `<|system|>`, `<|assistant|>`, looked up by their text, not hard-coded ids) to the chat handler as stop tokens,
  alongside its own end of turn. Both engine loads call it.
- **U2:** fitting's probe calls `install_stops` and passes `STOP` on its warm-up, timed and voice answers, and
  `llm_model_eval.py` passes `STOP`. s237 scans every `create_chat_completion` in the repo for `stop=STOP` (7 found)
  and every function that builds a model for `install_stops` (3 found). The one exemption is
  `llm_runtime_spike.py`, the frozen record of how the runtime was chosen.
- **U4:** the processor's probe reads the same six voice answers. `choose()` excludes a chip only when it has more
  answers with an invented figure than the processor had. With no processor reading, the bar is none. Settings says
  "more … than this computer's processor did". Fitting takes about a minute longer for the processor's six.
- **U5:** the comment in `core/engine.py` keeps the old line, marks the 0/120 as not reproducing, gives the
  re-measured figures and harness, and names the reference: the processor measured beside each A/B.

**U3, measured before the stop went in:** one probe per kind of caller, 5 seeds each, no stops, on NVIDIA, with the
app's own system prompts and prompt shapes. The kinds were the trip quote and itinerary JSON extractors, the trip
classifier JSON, the category report (700 tokens), the monthly report (1000), a report follow-up and the Sunday
check-in. Across 35 answers a run of three newlines appeared **4 times, each right after a complete answer and each
the start of a runaway that ran to the cap:**
- after the itinerary JSON: "Your response was incorrect… Here is the corrected JSON object";
- after the classifier JSON: a "Note:" ramble;
- after the category report, and after the follow-up: an **invented new "Category report, September 2026"** with
  made-up figures.

No caller used three newlines inside a real answer. So the stop applies to every caller unchanged.

**U6, the A/B on the built engine:** `engine.chat()` on a model loaded by `engine._load` (the shipped path:
`install_stops`, `STOP`), with each device pinned by a fit record. The device actually running was checked at load.
20 seeds × 6 cases, 512 tokens, temperature 0.3:

| device | gate pass | z vs the processor beside it | R8 | ran to the cap | runaway markers left |
|---|---:|---:|---:|---:|---:|
| processor | 39/120 | (reference) | **0/120** | 0 | 0 |
| NVIDIA RTX A1000 | 38/120 | −0.1 | **0/120** | 0 | 0 |
| Intel Iris Xe | 30/120 | −1.3 | **0/120** | 0 | 0 |

**Verdict against U6:** passed. Every answer ended on its own, no runaway is left, R8 is no worse than the processor
on both families (0 against 0), and gate pass is within noise. Intel is the lowest of the three, as it was before
(33/120), and still inside noise.

**One thing learned while checking:** these answers are not the same answers as the harness runs above, from the
first word. The cause is seeding, not the stops. The harness passed `seed=` on every call. The app calls
`set_seed()` only (here) or not at all (in use). Measured on NVIDIA, the default chat handler and `install_stops`
write identical text under the same seeding. So `install_stops` doesn't change the prompt, and this A/B is a fresh
sample of the app's own path.

**Gate:** 3645 / 0 at 743ce64, and 3671 / 0 on the merge with master (a1cb515). PUSHED 2026-10-18. ACCEPTED + CLOSED 2026-10-18 (Rob: "Accept item 97 and rebuild the installers from master.").

**Not done:**
- **The installers** built yesterday (from 2597220) don't have this change. They need rebuilding when you ask for a
  build.
- **AMD and Metal** are still owed (items 95 and 96).
