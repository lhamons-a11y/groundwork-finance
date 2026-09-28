# Model Placement — where the language model lives, and what it is allowed to be

**A design note for the 1.x → 2.0 transition**

> Status: **Decided; latency question closed by measurement, thread-tuning and the low-RAM tier
> still open.** See "Measured" below — the runtime swap is behaviour-neutral against an Ollama
> control, so the packaging win is free. Written 2026-08-30 against the real 1.1
> codebase, after a session that asked whether Groundwork should train its own finance-specific
> LLM. Companion to `GW_2.0_TEACHING_PLATFORM_BLUEPRINT.md` (Appendix B.2) and
> `CALCULATION_PLACEMENT.md` — that note says where the money math lives; this one says where the
> *model* lives. **Supersedes part of `GROUNDWORK_LLM_BUILD_PLAN.md`** — see "What this changes"
> at the bottom. **The 2.0 consequences are folded into the blueprint as Appendix H** (§5, §11,
> §12 and B.2a were amended); this note holds the evidence, that appendix holds what it binds.
>
> **Rulings of 2026-09-27 (Rob) — see "Rulings — 2026-09-27" below: Ollama leaves BOTH lines; the
> tested quantized model ships inside Groundwork; loaded at launch, freed on exit; the 8 GB line is
> the original design (Q4 floor, no small-model tier, LTS for machines that cannot run it).**

---

## The question

Two questions arrived as one:

1. Should Groundwork train its own LLM — finance-only vocabulary, the voice rules and gates baked
   into the weights — so it cannot use bad verbiage or invent numbers, because it never learned to
   think any other way?
2. Store distribution (Microsoft, Apple) is blocked by depending on a separate Ollama install, and
   a second background process is a startup cost on the user's machine. Should everything live in
   one wrapper?

## The decision

**No custom-trained model as a source of truth. Yes to embedding the inference runtime in-process.
Yes to constrained decoding. A voice fine-tune is deferred, and only ever for tone.**

Four rules:

1. **The model is the interpreter, never the source.** Unchanged from blueprint B.2. Nothing below
   reopens it.
2. **Rules bake into the decoder and the architecture, not the weights.** Weights are irreducibly
   probabilistic. Decoders and gates are deterministic. Durable rules go where determinism is.
3. **The runtime ships inside Groundwork.** No separately-installed software, no second process.
4. **Any fine-tune targets tone, is measured by first-pass gate acceptance, and trains on
   synthetic findings only.**

---

## Why not a custom model — the argument that nearly went the other way

The premise is intuitive: a model that only ever learned finance, with the gates and the voice in
its training, cannot wander outside them. Checking it is what reversed the conclusion.

**Narrowing does not reduce fabrication; it usually increases it.** Hallucination is not a
knowledge gap that a smaller domain closes — it is a property of sampling the next token from a
probability distribution. A finance-only model still emits plausible-looking dollar figures,
because emitting plausible-looking text is the whole operation. Worse, the capability Groundwork
actually leans on — *following the instruction "do not add numbers you were not given"* — comes
from broad general instruction-tuning, not from domain knowledge. Narrow the training and the
constraint-following degrades first. The result would know more about amortization and obey less.

**And the fabrication problem is already solved structurally.** R8 number-provenance in
`_voiceGateCheck` rejects any financial figure absent from `findings`. That is a guarantee by
construction, not a tendency. A fine-tune moves compliance from roughly 95% to roughly 99% — and
the gate is still required afterward, so the training buys nothing on the safety axis.
**Trading a proof for a probability is a downgrade even when the probability is high.**

**Cost closes it.** Pretraining even a 1B model is a curated corpus and five-to-six figures of GPU
time, and the result follows instructions worse than stock phi3.5 does today.

**What a custom model would not buy: integration.** `ai_chat()` (`server.py:5166`) is already a
provider router; a custom model drops in as a different model behind the same call. The
integration boundary is identical either way. A custom model changes behavior *at* the boundary,
not the boundary itself.

---

## The decoupling that matters

The two questions above look like one idea. They are orthogonal, and conflating them is the
mistake this note exists to prevent:

- Training a custom model **does not** solve the store problem. A custom GGUF still needs a
  runtime; if that runtime is Ollama, the dependency is unchanged.
- Embedding an in-process runtime **does** solve it completely — and works with stock phi3.5, with
  no training at all.

The packaging problem is real and load-bearing. The training answer to it is a non-sequitur.

---

## Why the runtime moves in-process

**We are already halfway there, the hard way.** `groundwork_store.iss` bundles a portable Ollama
runtime and the phi3.5 model as plain file copies — written specifically to dodge MS Store
certification 10.2.9.2, because the normal lane runs a 1.4GB nested installer that risks a cert
timeout. `launch.py:199 :: _ensure_ollama_running` then starts `ollama serve` itself. Its own
header says: *not yet verified on a clean machine*. Model staging is solved
(`vendor/phi3.5_model/`); the **runtime** is the unsolved piece.

Four reasons it moves:

1. **Apple forces it.** Mac App Store sandboxing is mandatory; a bundled `ollama serve` needs
   re-signing under our team ID, inherits the sandbox, and wants `~/.ollama`. Review also rejects
   apps requiring separately-installed software. Bundling a *library* is routine; bundling a
   *server daemon* is the fight. In-process is what makes a Mac App Store lane viable at all.
2. **Windows gets simpler.** The portable-Ollama gamble retires. (Note: the MS Store has accepted
   Win32 `.exe` installers since 2021, so the Inno lane can list either way — Windows is the
   forgiving case, not the blocking one.)
3. **One process, one support surface.** No tray app, no port 11434, no login autostart, no version
   skew against an Ollama the user already had.
4. **It unlocks the sampler.** In-process llama.cpp exposes GBNF grammars. Ollama's HTTP API does
   not expose arbitrary grammars. This is what makes rule 2 above *buildable* — see below.

### Be precise about the resource claim

| Claim | Verdict |
|---|---|
| Removes a second install | **True** — the store-lane blocker |
| Removes a second process / tray / autostart | **True** — roughly 100–300MB and the startup cost |
| Reduces model RAM | **False** — ~2.2GB for phi3.5 Q4 either way; this dominates |
| Automatically lighter at runtime | **False** — Ollama unloads after ~5 min idle by default |

In-process gives us *control* over the load/unload tradeoff (lazy-load = slower first narration;
resident = holds 2.2GB), not an automatic saving. State it that way; do not oversell it.

---

## Constrained decoding — the original instinct, at the right layer

The intuition behind "bake the gates into the model" is correct. The layer is the **decoder**.

Constrain the sampler with a grammar so numeric tokens can only be drawn from the supplied
`findings` set. Fabrication becomes **impossible at generation time**, not merely rejected after.
This is the same conclusion blueprint B.2a reaches for tone ("the architecture owns the register,
not the model's discretion"), extended to figures — and it is only reachable once the runtime is
in-process.

Sequence matters: **runtime first, grammars second, fine-tune last (if ever).**

**Measured caveat — a grammar constrains figures, not relationships.** In the spike the
grammar held: asked adversarially for a figure that did not exist, the model emitted only
`$17` and `$2,400`, both from findings. But it composed them into arithmetic nonsense — *"a
daily interest rate of $17 … is approximately $2,400"*. **R8-by-construction guarantees
provenance, not correctness.** A grammar cannot stop a true number being put in a false
relation, so it *narrows* the voice gate's job and never replaces it — the causal-structure
check matters more after grammars, not less. This is the same lesson as B.2a's tone channel:
close one channel and persuasion moves to the next one over.

---

## The fine-tune, if it happens

A LoRA on a small open model (Qwen2.5-7B / phi tier) that internalises `GW_VOICE`, so the historian
register is native rather than re-litigated in a long prompt on every call. Legitimate, but a
*quality* improvement, not a safety one.

- **Metric:** first-pass gate acceptance rate. Not "accuracy." The harness
  (`voice_discipline_test.py`) and the ground truth (`voice_miss_log.jsonl`,
  `server.py:3105 :: get_llm_miss_log`) already exist.
- **Payoff:** fewer R3 inference smuggles → fewer retries → fewer fallbacks → more real prose
  reaching the user, on weaker hardware.
- **Cost:** a few hundred examples, hours of rented GPU, roughly $50–200.
- **Timing:** *after* the canary. The miss-log is the negative examples and gate-passing output is
  the positive ones — the training set is the harvest of the existing plan, and does not exist yet.
- **Hard constraint: synthetic findings only, never real user narration.** A shipped adapter
  trained on real transcripts carries one user's financial data in its weights to every other user.
  That breaks "nothing leaves the machine" and "the user isn't the product" in a way no disclosure
  repairs.

**Scope limit.** "Advisor, accountant, friend" is three things and they do not all belong in the
model. *Friend* is a tone property — the fine-tune's legitimate target. *Accountant* is
deterministic (Consequence Engine; see `CALCULATION_PLACEMENT.md`). *Advisor* originates judgments,
which is the source→interpreter demotion running backwards — that is the Solution Engine's output,
ranked by the Willingness Layer and bounded by the honest-no. The model may make advice *sound*
like a friend said it. It may never be the thing that decided it.

---

## Explicitly not doing

- **No pretraining a model from scratch.** Cost, and it would obey worse than phi3.5.
- **No domain-narrowed model as a fabrication defence.** It degrades the constraint-following the
  gate depends on.
- **No removing the voice gate**, whatever the model. Grammars and fine-tunes reduce how often it
  fires; they never replace it.
- **No quantization below Q4_0.** Measured 2026-09-02: q3_K_M, q3_K_S and q2_K each violated R8
  where the q4_0 control did not, and q2_K returns no output at all. Storage is the wrong reason
  to trade the one axis that disqualifies.
- **No custom tokenizer/vocabulary work.** Marginal gains, real complexity.
- **No CUDA in the shipped package.** It balloons size; CPU baseline, Metal on Mac, Vulkan only if
  Windows GPU proves necessary.
- **No fine-tuning on user data.** Ever. See above.

## The stopping rule

If a constraint can be enforced deterministically — by the gate, by the grammar, by a template — it
is enforced there and the model is not trusted with it. Only what cannot be checked is left to the
model's discretion, and the less checkable it is, the more it gets templated. We never hand a small
model a degree of freedom we cannot verify.

---

## Measured — the spike, 2026-08-30

Run against the **same weights the store installer already stages**
(`vendor/phi3.5_model/blobs/sha256-b537…`, 2.18 GB — the Ollama model layer *is* a GGUF, so
llama.cpp opens it directly and no separate download was needed). `llama-cpp-python` 0.3.35,
prebuilt CPU wheel, **7.1 MB** — the runtime is negligible; the 2.2 GB is all model. Scored with
`voice_discipline_test.py`'s real `CASES` and `check()`, imported, not copied.

**The control is the point.** Latency alone proves nothing without knowing whether in-process
*behaves* like Ollama did, so the same six cases ran through both engines. Cold (first narration
of a session) is reported separately from warm, because `GW_VOICE` is an identical prefix on
every call and the KV cache makes that difference large:

Three independent runs (ranges, not single shots — see the variance note below):

| | llama.cpp (in-process) | Ollama (control) |
|---|---|---|
| **R8 number provenance** | **6/6, 6/6, 6/6** | **6/6, 6/6, 6/6** |
| Gate pass (first-pass) | 2/6, 2/6, 2/6 | 2/6, 1/6, 1/6 |
| Cold call | 15.8–16.2s (7.0–7.1 tok/s) | 11.7–15.4s |
| Warm median | **6.6–9.3s** (11.6–14.4 tok/s) | **5.4–6.3s** |
| Cold load | 1.5–3.3s (mmap) | n/a (resident daemon) |
| Dominant failure | R3 inference-smuggling | R3 inference-smuggling |

**Verdict: runtime-neutral on behaviour.** R8 held 6/6 in all six engine-runs, and the gate pass
rate differs by less than its own noise. **Swapping the runtime does not change what reaches the
user** — which is what licenses the packaging win. Speed is *not* settled; see Open.

What this settles:

- **Latency passes.** Warm median 9.3s for a real narration, cold load 1.5–3.3s. That load is
  the startup cost we would *own* instead of an always-on daemon.
- **2/6 is not news and not a regression.** Ollama scores the same. This is raw phi3.5 smuggling
  R3, exactly as `GROUNDWORK_LLM_BUILD_PLAN.md` Phase 1 documents — and why retry-then-fallback
  exists. **Neither engine ever violated R8**, before any grammar.
- **Cold vs warm is a real production effect.** First narration after load is ~1.7x slower
  (16.2s / 7.0 tok/s) than every one after (9.3s / 11.6 tok/s), because the shared `GW_VOICE`
  prefix is already in cache. A session's first report is the slow one; this bears on the
  load/unload policy we inherit from Ollama.

### Streaming — the largest win found, and it is free

Generation is not the user's wait; *waiting for the last token* is. Measured on phi3.5 in-process,
warm, across the six cases:

| | blocking | streaming |
|---|---|---|
| Median wait before text appears | **6.92s** | **0.80s** |

Generation runs at 10.5 words/s against a 250-wpm reader's 4.2 words/s — **text arrives 2.5x
faster than it can be read**, so the reader never catches the generator. The perceived wait is
therefore time-to-first-token alone: **0.80s, not 6.92s — an 8.7x perceived improvement with zero
change in throughput.** Cost: `stream=True` plus a frontend that appends tokens.

This reframes every latency number in this note. Throughput sets whether the text *keeps up with
reading* (it does, 2.5x over); TTFT sets what the user experiences. **Optimise TTFT, not tok/s.**
It also matters most exactly where the machine is weakest — on the low-RAM tier, streaming is what
stands between "slow" and "unusable."

### Model choice — phi3.5 CONFIRMED, and the preliminary signal was noise

A single run had suggested smaller models beat phi3.5 and that the locked default should be
revisited. **Repeated, it reversed.** 5 runs × 6 cases × 5 models, 143 completed calls
(`llm_model_eval.py`):

| model | GB | tok/s | pass rate | spread | **R8 violations** |
|---|---|---|---|---|---|
| llama3.2:1b | 1.32 | 82.4 | 47% | 2–3/6 | **8 / 30** |
| qwen2.5:3b | 1.93 | 56.9 | 33% | 0–4/6 | **3 / 30** |
| **phi3.5** (locked default) | 2.18 | 26.8 | 30% | 1–3/6 | **0** |
| llama3.2:3b | 2.02 | 47.3 | 27% | 1–3/6 | **12 / 30** |
| qwen2.5:7b | 4.68 | 14.2 | 27% | 1–2/6 | **0** |

**Keep phi3.5.** It is the only model under 2.5 GB that never fabricated a figure in 30 calls.
qwen2.5:3b's apparent 6/6 R8 in the single run was luck — at 30 calls it violates 13% of the time.
And the gate pass rates are *not* separable: every spread overlaps every other (0–4/6 against
1–3/6), so the "twice as good as phi3.5" reading was noise, exactly as the small sample warned.

Three findings that outrank the ranking:

- **R8 is the axis that decides, and it is bimodal.** Models either never fabricate (phi3.5,
  qwen2.5:7b) or do so often (13–40%). There is no middle. That makes model choice a
  *disqualification* test, not a score: fail R8 and nothing else matters.
- **R3 is universal and gets WORSE with size.** Smuggled inference is the dominant failure for
  every model — phi3.5 57%, and **qwen2.5:7b 70%**, the largest model tested. **Scaling the model
  up will not fix the voice.** More capable models are more inclined to explain, and explaining is
  what R3 forbids. This closes off "use a bigger model later" as a strategy.
- **The terseness hypothesis is dead.** Pooled across all 143 calls, output length barely differs
  between passing (48 tokens) and failing (55.5) — 1.16x, **not supported**. The mechanism
  proposed for the preliminary result was wrong, and the result it explained was not real either.

### Quantization — Q4_0 is the floor, measured 2026-09-02

The size axis the model-choice experiment never touched. That one varied **parameter count** across
five different models; this varies **numeric precision** within one. Both read as "make it
smaller." They are not the same lever and the first result does not transfer to the second.

**Why it was asked.** Storage, not RAM. Apple M-series has the compute to run the narrator, but
small non-upgradeable SSDs are a real constraint for Mac users (Rob, 2026-09-02), and the ~2.2GB is
the *weights* — the teaching-layer code is kilobytes and the runtime tens of MB, so no code split
addresses it. Quantization was the only size lever the evidence had not already ruled out.

**Method.** 5 runs x 6 cases per arm (30 calls, the same pass/fail screen R8 requires), with q4_0
re-run **in the same session as a control** rather than compared against the table above. This
document's history is a list of conclusions that reversed when a control was not held.

| quant | on disk | resident @4096 ctx | usable calls | **R8 violations** |
|---|---|---|---|---|
| **q4_0** (current default) | 2.18 GB | 3.9 GB | 30/30 | **0** |
| q3_K_M | 1.96 GB | 3.7 GB | 30/30 | **2** |
| q3_K_S | 1.68 GB | 3.4 GB | 30/30 | **1** |
| q2_K | 1.42 GB | — | **3/30** | 1 of 3 |

**Keep Q4_0.** The control replicated — 0/30 on R8, matching the recorded figure, with a 1-2/6 pass
spread inside the recorded 1-3/6 — and all three lower quants violated R8 where it did not.

**Read the effect size honestly.** One or two violations in 30 is 3-7%, *below* the 13-40% band
that defines the fabricating mode above. Three-for-three in the same direction against a clean
control is a consistent signal, but the licensed claim is **degradation begins below Q4_0**, not
*these quants are in the fabricating mode*. Under a pass/fail screen the distinction does not
change the answer.

**q2_K does not produce output at all.** 27 of 30 calls returned zero tokens; the three that spoke
each ran to the 300-token cap and one fabricated. It is disqualified for being mute. Its R8 rate is
unmeasured, not low.

**The storage relief is smaller than the file sizes suggest.** Resident footprint sits ~1.7GB above
file size (weights plus KV cache at 4096 ctx), so quantization saves roughly the same *absolute* GB
in RAM as on disk but a much smaller *share* of the footprint: q4_0 -> q3_K_S is -0.50GB on disk
and -0.5GB resident. Real for a small SSD; nowhere near enough to move a RAM tier. **Disk size and
resident size are different axes and the tables in this document only record the first.**

**This screen also found a bug in the harness that produced it.** An empty response violates no
voice rule, so `check()` returned clean and the call scored as a gate PASS — q2_K's 27 silences
reported as *97% pass, 0% failure on every rule, ranked first in the table*, and they poisoned the
pooled terseness test badly enough to flip its recorded verdict. Fixed the same session (empties
are now unscoreable and disqualifying). **Any quantization or model number produced before that fix
is suspect on the same axis.** That is the third scorer bug in this record, after the R6 placeholder
counted as failed and the warm-call timing taken without a token count; the shape is identical each
time — the measurement sat downstream of something absorbing the evidence.


### What the measuring got wrong first (kept, because the traps recur)

Four numbers were wrong before they were right, and every one was a control not held:

- **"0/6 gate pass"** — the scorer counted R6 as failed. `check()` returns `passed=None` for R6,
  an explicit human-eye placeholder (`voice_discipline_test.py:192`). Real rate: 2/6.
- **"Warm call slower than cold" (22s vs 16s)** — no token count recorded. It had generated 273
  tokens against 113: re-measured, 13.0 tok/s, the *fastest* run in the set.
- **"Best n_threads = 12"** — eight models built in one process, competing for RAM. Re-run with a
  fresh process per setting, the answer changed to 14 and the honest verdict was **INCONCLUSIVE**:
  the between-setting spread (1.83x) sat inside the run-to-run spread of a *single* setting
  (up to 13 tok/s). **Thread count is not the explanation. Do not ship a tuned `n_threads`.**
- **"Generation is memory-bandwidth-bound, and we are at the DDR5 wall."** Stated confidently
  from wall-clock tok/s; the data does not support it. Wall clock includes prefill, so it
  understated generation throughput ~2x (phi3.5 is 27.4 tok/s generating, not 11–14). Worse, the
  implied constant fails: derived bandwidth ran 59.6 / 112.5 / 104.4 GB/s across the three
  models, when a purely bandwidth-bound workload would hold it roughly constant — and 112 GB/s
  exceeds plausible dual-channel DDR5 anyway. And the prediction failed cleanly: 1.65x fewer
  bytes produced **2.88x** more speed, not 1.65x. Quantisation format (Q8_0 / Q4_K_M / Q4_0) and
  architecture clearly matter as much as size. Bandwidth is *a* factor, not *the* factor —
  which also means the thread-sweep null result still lacks an explanation.
- **"llama.cpp is ~50% slower, replicated"** — retracted by the next run. Two runs agreed
  (57%, 52% slower) and looked like replication; the third came back at **5%** — parity
  (6.58s vs 6.25s, 14.4 tok/s). Nothing was tuned between them. **Across-run variance exceeds
  the effect being measured**, so two agreeing runs were not replication, they were two samples
  from a wide distribution. The speed comparison is unresolved, not decided-and-bad.

The general lesson, learned five times in one session: **when two measurements of the same thing
disagree, the disagreement is the finding.** Do not average them, do not report the one that
suits the argument — and two agreeing runs are not replication until you know the spread.

---

## How to proceed — what the measurements actually license

### Settled; build in this order

1. **Stream the narration** (`stream=True` + a frontend that appends). 8.7x perceived-latency
   improvement, works on every model and every tier, and costs almost nothing. **Do this first** —
   it is the cheapest large win available and it makes the weakest machine feel viable.
2. **Keep phi3.5 as the default.** Confirmed on 30 calls: the only sub-2.5 GB model that never
   fabricated a figure. The Phase 0 decision stands, now on stronger evidence than it had.
3. **Embed the runtime in-process.** Behaviour-neutral against an Ollama control (equal R8, gate
   rate inside noise), so the store-distribution win costs nothing in output quality.
4. **Treat the voice gate as permanent architecture, not scaffolding.** Every model tested fails
   R3 between 37% and 70% of the time. There is no model, at any size, that makes the gate
   unnecessary. Retry-then-fallback is the product's integrity, not a stopgap until models improve.

### Changed by the evidence

- **Stop treating "a better model" as the path to voice discipline.** R3 got *worse* with scale
  (7B: 70%). The lever is architectural — grammar-constrained figures, and **templating the
  tone-sensitive surfaces** as Appendix B.2a already argued. This evidence promotes that from a
  preference to the only demonstrated path. The more of the narration that is templated, the less
  of it depends on a behaviour no model exhibits reliably.
- **The low-RAM tier cannot be solved with a smaller model.** That was the intuitive fix and R8
  disqualifies it: at ≤2 GB the models fabricate figures 13–40% of the time. So the sub-8 GB path
  is **not** a 1B local model.

  **The answer is a product split, not a degraded build: 1.x becomes GW LTS** (decided
  2026-08-30). Machines that cannot honestly run the narrator get the 1.x line — complete, and
  promising exactly what it delivers — rather than a 2.0 with its teaching layer quietly hollowed
  out. A 2.0 that cannot teach is 1.x carrying extra weight and a broken promise. This is the
  honest-no (blueprint C.5, *a no beats an inhumane yes*) applied one level up: to **which product
  a machine gets**.

  Two consequences, both load-bearing:
  - **Tiering moves from runtime to install time.** Phase 2B was designed to route users *within*
    one app by free RAM. Under the split it decides which product to install — an easier thing to
    get right and a far easier thing to explain honestly.
  - **LTS is a support commitment, not a freeze.** The split is *teaching-layer vs
    no-teaching-layer*, not *old vs new*. Correctness fixes flow to both lines; only the teaching
    layer is 2.0-exclusive. If LTS hardens into "frozen at today's state," the low-spec segment
    gets a product that rots — and the four calculation bugs of 2026-08-26 are exactly the class
    that would go unfixed there.

  **This raises the stakes on the `app.js` test gap.** `CALCULATION_PLACEMENT.md` records that all
  four of those bugs lived in code the suite "covered" by grepping source text, and every one
  survived a green run. That is tolerable for a product heading toward replacement. It is a
  liability for one committed to years of support, so the 43 source-text checks matter **more**
  under this strategy, not less.
- **Fabrication is a cliff, not a slope.** Models either never fabricate or fabricate often.
  Model qualification is therefore a pass/fail R8 screen run over ~30 calls — which is what
  `llm_model_eval.py` now does — and any future model swap must clear it before anything else
  about it is discussed.

### Still to measure, in priority order

1. **The 8 GB tier**, with `llm_runtime_spike.py`. Record whether the model stays *resident*, not
   just its tok/s — paging, not throughput, is the cliff there. **Demoted from blocker to
   line-placement** by the GW LTS split: it no longer decides *whether* low-spec users get
   something honest (they get LTS), only *where* the install-time line falls. Worth measuring, no
   longer worth waiting on.
2. **Grammar + streaming together**, since both touch the same generation path and the grammar's
   effect on TTFT is unmeasured.
3. **Interleaved A/B/A/B** on an idle machine, to settle the llama.cpp-vs-Ollama speed question
   that three runs left unresolved.

---

## Open

- **Relative speed vs Ollama is UNRESOLVED — the variance swamps the effect.** Three runs put
  llama.cpp at 57%, 52%, and 5% slower on identical weights with nothing changed between them.
  **Ruled out as the cause:** thread count (sweep inconclusive) and prompt-cache state
  (controlled; the gap persisted in one run and vanished in the next). The remaining suspect is
  ambient system load, which nothing here controlled for. **Do not record a regression, and do
  not record parity.** Settle it with interleaved A/B/A/B repetitions on an otherwise-idle
  machine before the cutover. Absolute numbers are usable either way — 6.6–9.3s warm for 2–4
  sentences — so this gates *understanding*, not the decision.
- **The measurements are an upper bound.** Taken on 14 physical cores / 34 GB RAM — not the target
  machine. **The 8 GB tier is unmeasured**, and it is exactly where latency decides whether local
  narration is honest to offer at all. Phase 2B's RAM tiering depends on a number we do not have.
  `llm_runtime_spike.py` (repo root) is the harness for it and prints a banner when it detects a
  low-RAM box; run it there and paste the numbers into the table above.
- **Which runtime.** `llama-cpp-python` is now the working assumption on evidence (one code path,
  GGUF, Metal on Mac, tiny wheel). ONNX Runtime GenAI remains a real alternative on Windows —
  first-class phi support, DirectML and NPU paths — at the cost of two runtimes to maintain.
  Not decided.
- **Where the model file comes from.** Leaning: ship the runtime in the package (~10–50MB), pull the
  GGUF on first run. Weights are *data*, not executable code, so Apple's no-executable-download rule
  permits it; it keeps the store package small and stops the sub-8GB tier from downloading 2.2GB it
  will never run. The structured fallback already makes the app usable before the download finishes.
  Not verified against current review guidelines.
- **What replaces Ollama's auto-unload.** A policy we now own. Undecided.
- **Whether Phase 6B's license clearance is moot.** It gated redistributing phi3.5 inside an offline
  bundle. In-process bundling raises the same question, possibly unchanged. Re-check, do not assume.

---

## Rulings — 2026-09-27

> Status: **RULED by Rob, 2026-09-27. Recorded, not built, not queued** — a ruling is not a build
> authorisation. Reached after the launch warm-up for Ollama (`STREAMING.md` T2 / T4) raised the
> question *"so could we actually get away from ollama completely?"*

Rob's reasons, in his words: memory that holds *"items that pertain to Groundwork and groundwork
only"*, no Ollama extras taking RAM, and the Microsoft Store and Mac App Store. And the premise that
makes an in-process engine enough: *"We are not asking the llm to go research or get any
information we are simply reading what the data shows for the user and their finances."* The model
never needs the network; in-process it has none — not even the loopback port (11434) that any
program on the machine can reach today.

1. **Ollama is gone — from both lines.** *"Ollama is gone it should not be in either one."* The
   built-in engine replaces it on **lts/1.x and 2.0**. Supersedes "Ollama remains the development
   runtime until the spike lands" (below) and the assumption that LTS keeps Ollama. The install,
   pull, tags and auto-detect paths (`/api/ai/install-ollama`, `/api/ai/pull-model`,
   `_resolve_local_model`, `_local_endpoint`) go with it.
2. **One engine; hardware acceleration where available, never required.** The measured gap (warm
   6.6–9.3 s CPU-only in-process against 5.4–6.3 s for Ollama on a 4 GB GPU) does not justify a
   second engine. A GPU build is an optimisation to measure, not a prerequisite for running.
3. **The tested model ships inside Groundwork.** No first-run download — supersedes the "pull the
   GGUF on first run" lean under Open. The file is the quantized one the evidence ran against
   (`vendor/phi3.5_model/`, 2.18 GB Q4), not Microsoft's full-precision release. Works offline,
   present immediately, no model host, and the user receives exactly the model that was tested.
4. **Loaded at launch, kept warm, freed on exit.** Lazy loading was considered and dropped (*"forget
   lazy load then"*): the model loads when Groundwork opens with AI on, stays resident while it is
   open, and is released when it closes — no 30-minute residency after exit, which is what Ollama's
   `keep_alive` does today. Whether to wait for the model or turn AI off stays the user's call.
5. **Licence: not a blocker; a release gate.** phi3.5-mini-instruct is MIT, as are llama.cpp and
   `llama-cpp-python`. Before release: pin the exact artifact, keep its LICENSE / NOTICE, verify the
   licence against the **quantized file actually shipped** (ours came from Ollama's registry), and
   record the check in the release documentation.
6. **8 GB: the original design stands.** *"I agree with this lets keep it to the original design."*
   Q4 is the floor (measured 2026-09-02) and there is no small-model tier (≤2 GB models fabricated
   figures in 13–40 % of calls). A machine that cannot run the narrator honestly gets **LTS**, not a
   weaker model — the 2026-08-30 product split. The 8 GB tier is still unmeasured; the test that
   decides it must show more than "the model loads":
   - Groundwork launches normally, and the model loads;
   - Groundwork stays responsive, and ledger / database work stays usable while the model is loaded;
   - AI produces the required response;
   - no pathological swapping or thrashing, and the machine stays usable;
   - closing Groundwork releases the model's memory, and a second launch works normally.

### What these rulings leave open

- **LTS on a machine that cannot run the model.** With Ollama gone from LTS too, LTS's narration
  runs on the same built-in engine. A machine that fails the 8 GB test on LTS has no other engine to
  fall back to — whether LTS then ships with AI off and the structured fallback (Phase 1D's floor)
  is not ruled.
- **Which runtime** — `llama-cpp-python` is the working assumption (one code path, GGUF, Metal on
  Mac, 7.1 MB CPU wheel); ONNX Runtime GenAI remains the alternative on Windows.
- **Which GPU build**, if any (CUDA is large; Vulkan is vendor-neutral), and what it adds to the
  installer.
- **The Ollama launch warm-up** (`2c26404` on a local lts branch, never pushed) was built for the
  engine these rulings remove. Its prompt order (the voice block first, so the prefix cache serves
  every surface) carries to any engine; its Ollama call does not — under ruling 4 the in-process
  engine simply loads at launch.
- **The existing users' crossover** — an installed Ollama and its downloaded models are the user's
  software; what Groundwork says or does about them on upgrade is unruled.

## What this changes in `GROUNDWORK_LLM_BUILD_PLAN.md`

The build plan is otherwise intact — Phases 1, 3, 4, 5 are unaffected. Three items are superseded:

- **The locked decision line** ("provider = local Ollama") is now *local inference, provider
  in-process*. Ollama remains the development runtime until the spike lands.
- **Phase 2A/2B** — the provider pane's "is Ollama reachable / installed models" framing collapses.
  `_local_endpoint`, `_resolve_local_model`, `GET /api/ai/status` and the `install-ollama` route
  (`server.py:5713`) simplify or disappear. RAM tiering (2B) survives unchanged and matters more.
- **Phase 6A/6B** — Lane A/Lane B were both shaped around installing or bundling *Ollama*. Rewrite
  against an embedded runtime. 6C (code-signing) and 6D (smoke checks) stand.

Blast radius is contained: `ai_chat()` is already a provider router, so the change lands in
`_ai_chat_local` (`server.py:5253`) and both paths can coexist while they are compared.

---

## Provenance

Written after the 2026-08-30 session, which asked whether Groundwork should train its own LLM and
then — more usefully — why store distribution requires a separate Ollama install. The first
question resolved against the premise (narrowing does not reduce fabrication; the gate already
guarantees what training would only make likely). The second resolved *for* the instinct behind it,
one layer down: the dependency is real, the fix is an embedded runtime, and it happens to unlock
the constrained decoding that makes the first question moot. The conclusions are drawn from the
1.1 codebase as it stands — `groundwork_store.iss`'s unverified portable-Ollama workaround, the
live `_voiceGateCheck`, and `voice_miss_log.jsonl` already collecting — not from general
architecture principle.

**Amended 2026-09-02** with the quantization screen, which the 2026-08-30 session never ran: it had
varied parameter count across models and treated that as the whole size question. Quantization is a
second, independent size axis, and it was asked for a reason the original session did not have —
Apple M-series has the compute but not always the disk. The answer closed it (Q4_0 is the floor),
and the run turned up a third scorer bug in `llm_model_eval.py` on the way.
