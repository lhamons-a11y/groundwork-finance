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
