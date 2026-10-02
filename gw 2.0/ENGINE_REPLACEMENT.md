# Replacing Ollama with the in-app engine (item 31)

Opened 2026-10-02 (Rob: *"queue it as item 31 and open the pass, and place ahead before the onboarding"*). **No code.**
The decision was made on 2026-09-27 (`MODEL_PLACEMENT.md`, rulings 1–6: *"Ollama is gone it should not be in either
one"*) and recorded as *"not built, not queued"*. This pass measures what the replacement touches and puts the open
questions to Rob. It goes ahead of the onboarding revisit (item 30, A6), because A8 and A9 depend on it.

---

## 1. What was measured (master `a8cface`, lts/1.x `d9ce860`)

**The server already funnels every AI call through one function.** Nine functions in `server.py` speak Ollama's
protocol. Every model call passes through **`_ai_chat_local`** (~8089), which has two callers:
- `_ai_complete_text`, the server's own AI uses (via `_call`, and `debt_pdf_extract`);
- the `/api/ai/chat` route, the client's one entry point.

| function (server.py) | what it does | after the replacement |
|---|---|---|
| `_ai_chat_local` | sends the chat to Ollama over HTTP | **the swap**: calls the in-app engine instead |
| `_local_endpoint`, `_resolve_local_model` | find Ollama's address and model | gone |
| `_model_ready` (item 28's 1 s probe) | asks Ollama whether a model is up | asks the engine whether it's loaded |
| `ai_status` | reports Ollama reachable, model resolved | reports the engine: off / loading / ready |
| `_run_model_pull`, `/pull-model`, `/pull-status` | downloads a model through Ollama | gone (the model ships inside) |
| `_run_install_ollama`, `/install-ollama`, `/install-status` | installs Ollama | gone |
| `ai_chat` | the client route | kept, unchanged in shape |

Reference counts: `server.py` 51 (lts 45), `launch.py` 15 (lts 13), `app.js` 28 (lts 26), plus `index.html`'s Ollama
setup panel (`aiOllamaSetup`, the *"Needs ollama.com"* line).

**The model file is already the right format.** `vendor/phi3.5_model/blobs/sha256-b537…` (2.18 GB) is a GGUF:
Ollama's model layer *is* the file llama.cpp opens. The spike ran on exactly this file.

**The behaviour evidence already exists** (`MODEL_PLACEMENT.md`, three runs each, the real voice cases):
- R8 number provenance held 6/6 on both engines, every run.
- Gate pass rate was within noise (2/6 against 1–2/6).
- Warm calls took 6.6–9.3 s in-process (CPU only) against 5.4–6.3 s for Ollama on a 4 GB GPU.
- Cold load took 1.5–3.3 s.
- The runtime (`llama-cpp-python` 0.3.35, CPU wheel) is 7.1 MB.

So swapping the runtime does not change what reaches the user.

**The installers carry Ollama three ways:**
- `groundwork.iss` runs the 1.4 GB `OllamaSetup.exe`.
- `groundwork_offline.iss` runs it and writes the model into `~\.ollama`.
- `groundwork_store.iss` copies a portable Ollama plus the model, never verified on a clean machine.

All three put files **outside** Groundwork's install folder: `%LOCALAPPDATA%\Programs\Ollama` and `~\.ollama`.

**Tests that assume Ollama:**
- `s60` stands up a fake Ollama server.
- `s26`, `s50`, `s52`, `s55` name its routes or protocol.
- The dev tools `llm_model_eval.py`, `voice_discipline_test.py` and `jev_category_screen.py` call it.

**Not yet available here:** `llama_cpp` is not installed in this environment. The spike installed it separately.

---

## 2. Points for ruling

**E1. One seam.** A new `core/engine.py` owns the model: load, generate (whole or streamed), free, state.
`_ai_chat_local`'s body becomes a call to it, keeping its request and response shape, so neither caller changes.
The Ollama-only functions and routes in §1 are removed, and the client's setup panel is replaced by a plain state line
(off / loading / ready). *Recommended.*

**E2. Runtime: `llama-cpp-python`, CPU build, first.** It is measured as runtime-neutral, 7.1 MB, and opens the file
already shipped. ONNX is not pursued unless packaging fails (E6). A GPU build is not part of this build: it is an
optimisation to measure later (ruling 2: hardware acceleration where available, never required). *Recommended.*

**E3. Load policy (ruling 4, and item 30's A9):**
- Load at launch **only if AI is on**, on a background thread, so the window opens at once.
- Free the model on exit.
- Switching AI off frees it, and switching AI on loads it.
- While it loads, AI surfaces show *loading* with the plain figures (A10).
- **One model and one call at a time, behind a lock.** Ollama used to queue calls for us, and now we must.

*Recommended.*

**E4. Where the model lives.** It ships inside Groundwork's own install folder as a named file
(`models/phi3.5-mini-instruct-q4.gguf`), with its SHA-256 checked at load. A file that fails the check is not loaded,
and AI says so. It is never placed in `~\.ollama`. The licence check stays a release gate (ruling 5): pin the artifact,
keep LICENSE/NOTICE, verify the quantized file actually shipped. *Recommended.*

**E5. Machines that already have our Ollama.** Earlier installers put Ollama and a 2.2 GB model outside our folder.
Groundwork can't reliably tell *our* Ollama from one the user installed and uses for other things. Deleting it would
be silent writing, and it would cross the custody ruling.

*Recommended:*
- Groundwork simply stops starting it.
- After the update, it says once, plainly: Ollama is no longer needed by Groundwork; this is where it is and how much
  space it uses; removing it is the user's choice, and other programs may use it.
- Nothing is removed by Groundwork.

**E6. Installers.**
- All three drop `OllamaSetup.exe` and the `~\.ollama` copy, and place the GGUF in `{app}\models`.
- The store variant becomes plain files with no nested runtime. That is what the stores require.
- Packaging `llama_cpp`'s native library with PyInstaller is the one unmeasured risk. The build's first step is a
  packaged-build test on a clean machine, before anything else is changed.

*Recommended.*

**E7. Both lines, 1.x first** (shared code, as with every shared fix: lts first, then merged to master, a gate on
each). The question ruling 6 left open: a 1.x machine that can't run the model has no Ollama to fall back to.

*Recommended:* 1.x uses the same choice as 2.0.
- The machine check, then the user's AI on/off decision.
- A machine that can't run the model runs with AI off and the plain-figures floor.
- That needs A10 (every surface complete with AI off) to hold on 1.x too, so A10's gate pass runs on both lines.

**E8. Tests.**

Updated:
- `s60` drives a stand-in engine, not a fake Ollama server.
- `s26`, `s50`, `s52` and `s55` follow the routes that remain.

New:
- **AI off never loads the model** (A9).
- **The engine opens no network port.** The test asserts that no listening socket is created. The point of
  in-process is that no other program on the machine can reach the model.
- **Ollama is absent** from the shipped code: a crossing test in the style of `s52` (cloud AI absent).
- The model's memory is released on exit and on switching AI off.
- **The voice A/B is rerun on the packaged build**, through the real `CASES` and `check()`: R8 6/6, gate pass within
  noise of the measured 2/6.

*Recommended.*

**E9. Dev tools.**
- `llm_model_eval.py`, `voice_discipline_test.py` and `jev_category_screen.py` move to the engine, so what we evaluate
  is what we ship.
- `llm_runtime_spike.py` keeps its Ollama A/B as a historical control only, marked so.

*Recommended.*

**E10. What this unlocks, and does not include.** Each of these needs its own go-ahead after this build:
- GBNF grammars (MODEL_PLACEMENT rule 2), which fix figures by construction;
- constrained output for item 28's model matcher, which is the *capable is not admissible* fix: enforce the shape,
  don't salvage the reply;
- item 30's A8 facts block, warm from launch;
- item 10's streaming, rewritten against the engine;
- item 12's truncation check, from the engine's own finish reason.

*Recommended: the build stops at the replacement.*

---

## 3. Order

1. The packaged-build test on a clean machine (E6). If it fails, stop and come back.
2. lts/1.x: engine, seam, load policy, installer, tests; gate.
3. Merge to master; master's own removals (2.0 surfaces); gate.
4. The voice A/B on the packaged build of each line.

## 4. Rob's ruling, 2026-10-02, and what was raised back

Rob ruled in ten points and closed the architecture (*"the next pass should therefore be implementation of the
replacement, not another round of deciding what the replacement is"*):

1. **Runtime:** `llama-cpp-python`; no ONNX in this pass.
2. **8 GB:** a hard shipping requirement, tested on a real 8 GB Windows machine. The test: usable with the model
   resident; loads reliably; database and UI stay responsive; AI completes its work; memory pressure does not make the
   app unusable; closing releases the model.
3. **GPU:** opportunistic acceleration, never a prerequisite. Vulkan is the first Windows backend, not CUDA. *One
   engine. CPU always available. No GPU-only edition.* The 8 GB test decides how far layers are offloaded.
4. **Model:** ship the exact tested quantized artifact, pinned by file, revision and checksum. No download.
5. **Packaging:** the installer holds Groundwork, the runtime and the model. No first-run download, model server,
   account, Ollama install or network dependency.
6. **Lifecycle:** load at launch, keep available, release at close. No lazy loading.
7. **A 1.x machine that cannot run the model:** AI unavailable, said honestly, and the app otherwise fully usable.
   There is no Ollama fallback, no cloud fallback, no API key request, no forced upgrade and no invented AI result.
8. **Licence:** a release gate on the exact artifact, recording the upstream model and revision, the quantized file,
   its hash, the quantization's provenance, the licence, and the included notice files.
9. **Existing installs:**
   - stop launching and contacting Ollama;
   - remove Groundwork's Ollama configuration, routes and UI;
   - use the bundled engine;
   - leave the financial data untouched;
   - never silently uninstall a separately installed Ollama.

   *"If Groundwork itself installed a private/bundled Ollama component ... that component can be removed."*
10. **A8, A9, item 10, item 12:** these wait on the replacement and talk to Groundwork's local inference interface, never
    Ollama's HTTP: *Groundwork → local engine → model.*

**Raised back, 2026-10-02 (awaiting Rob):**

- **R-a. Point 6 and A9.** *Load at launch* must stay *load at launch when AI is on*. That is ruling 4's own wording,
  and item 30's A9, which Rob agreed.
- **R-b. Point 9: there is no "private" Ollama to tell apart.** All three installers ran Ollama's **own** installer, or
  copied it, into Ollama's standard per-user location (`%LOCALAPPDATA%\Programs\Ollama`). They skipped that step when it
  was already there, and they wrote no marker. So Groundwork cannot prove which copy it installed, and a copy it did
  install may since have been used for other things. That copy also starts at Windows login, which costs memory even
  when Groundwork is closed.

  Proposed:
  - Groundwork removes nothing by itself.
  - It shows a one-time notice: *Groundwork no longer uses Ollama; it is here, it uses this much space and starts at
    login; other programs may use it.*
  - The notice offers to open Windows' own uninstall for Ollama. The user chooses.
- **R-c. Point 3: CPU first, then Vulkan behind its own packaged test.** A Vulkan build of `llama-cpp-python` is a
  different build of the library. If it fails to load on a machine with no Vulkan driver (older integrated graphics,
  some VMs), the whole engine fails, which would break *CPU always available*. Proposed order:
  - ship the CPU build first;
  - add Vulkan only once a packaged test shows it loads, **and falls back to CPU**, on a machine with no Vulkan
    driver, and is measurably faster on integrated graphics at 8 GB.
- **R-d. Point 2: wording.** *8 GB minimum* is the minimum for **AI**, not for running Groundwork. With AI off,
  Groundwork runs on less (Rob, 2026-10-02: *"freeware that doesn't suck"*), and point 7 already says so. The 8 GB test
  also needs a real 8 GB Windows machine. This one has 34 GB, and Windows 11 Home has no Hyper-V to make a VM, so
  Rob supplies the machine.
- **Kept from the pass, not contradicted by the ruling:** E3's one-call-at-a-time lock, E4's checksum check at load,
  E6's packaged-build test on a clean machine as step one, E8's tests (no listening port, Ollama absent, AI off never
  loads, memory released, the voice A/B on the packaged build), and E9's dev tools moving to the engine.

## 5. R-a to R-d agreed, and the build authorised (Rob, 2026-10-02)

*"Agreed to R-a through R-d, and I authorize the build."*

- **R-a, lifecycle:** the model loads at launch **only when AI is enabled**. With AI off it is not loaded at all. It
  is released when Groundwork closes.
- **R-b, Ollama migration:** Groundwork never uninstalls Ollama. Every existing Ollama is treated as potentially
  user-owned. The migration is a one-time notice: Groundwork no longer uses it; where it is, the space it uses, and that
  it starts at login. The notice offers Windows' own uninstall path, and the user decides.
- **R-c, acceleration:** the CPU engine ships first. Vulkan is a separate later implementation and test. It becomes
  supported only after proving that machines without Vulkan still have a working CPU path, and that Vulkan gives a real
  benefit on an 8 GB shared-memory machine.
- **R-d, 8 GB:** 8 GB is the minimum for Groundwork **AI**, not for Groundwork itself. AI off stays usable on less. A
  real 8 GB machine is a completion criterion. The 34 GB development machine cannot substitute for it.

**Retained controls, agreed:**
- one AI call at a time;
- SHA-256 verified before the model loads;
- the clean-machine packaged-build test first;
- no listening port;
- Ollama absent from the architecture;
- AI off means no model load;
- memory released on exit;
- the voice check rerun;
- the developer evaluation tools on the new engine.

**Authorisation:**
- *"Build the replacement now. Start with the packaged 1.x build test."*
- Both lines converge on the built-in engine, with no Ollama fallback and no cloud fallback.
- **The real 8 GB machine test is the one remaining hard completion gate.** Until it is passed, the engine can be
  built and otherwise validated, but the replacement stays **explicitly not complete for release**.

## 6. The build (2026-10-02)

**Step 1, the packaged build test.** This ran on the development machine. No clean machine is available here: Windows
11 Home has no Windows Sandbox or Hyper-V. Results:
- A frozen probe and then the real 1.x app, built with the new `groundwork.spec`, loaded the runtime from inside the
  bundle with PATH stripped to `System32`.
- PyInstaller bundles the Visual C++ runtime the native libraries import (`msvcp140`, `vcomp140`,
  `vcruntime140(_1)`). The rest is the Universal CRT that ships with Windows 10 and 11.
- The packaged app loaded the model at launch with AI on, settling at **3.7 GB private about 12 s after launch**. The
  window did not wait for it.
- **The only listening port was 8765**, Groundwork's own existing UI server, so the engine adds none.
- Closing the window released the model: **3,697 MB to 726 MB within a second**. The process then exited cleanly.
- Found on the same machine: the user's own Ollama, listening on 11434 since login on 25 September. Groundwork did not
  start it. That is exactly R-b's case.

**Found building, and handled:**
- **The CPU build requires AVX2, FMA and F16C.** On a processor without AVX2 (Celeron or Pentium chips from before
  about 2021, common in 8 GB laptops) the runtime would fault **the whole app**, because it runs in-process. So
  `core/engine.py` asks Windows (`IsProcessorFeaturePresent`) **before** importing the runtime. Without AVX2, AI is
  unavailable and said so (ruling 7). s61 checks the order.
- **numpy was excluded** from the spec, but `llama_cpp` imports it. It is now included.
- **The runtime is imported lazily,** so the spec collects it explicitly, and the build **fails** if it is missing,
  rather than quietly shipping a Groundwork whose AI can never start.

**The cache, chosen by measurement.**

Memory (process private, model loaded):

| setting | memory | speed |
|---|---|---|
| 4096 context, f16 cache | 4.53 GB | 18.3 tok/s |
| 2048 context, f16 cache | 3.63 GB | 18.7 tok/s |
| 4096 context, q8_0 cache + flash attention | 3.61 GB | 19.7 tok/s |

The voice A/B ran on the real `CASES` and `check()`, 20 seeds × 6 cases per setting:

| setting | gate pass | R8 violations |
|---|---|---|
| q8_0 + flash | 30/120 | **2** |
| f16 | 38/120 | **0** |

R8 is cardinal, so **the 8-bit cache is disqualified** despite saving about 0.9 GB. The engine ships **f16 at 4096,
flash attention off**: the configuration the voice was validated on, R8 0/120, gate pass within the measured range.
- The largest measured prompt plus answer is about 1,720 tokens (STREAMING.md §3), so 4096 keeps headroom.
- **2048 is the measured fallback** (3.63 GB, identical output for anything that fits). The real 8 GB test chooses
  between them (R-d).
- The runtime library itself is about 0.64 GB once imported. With AI off it is never imported, and the process stays
  around 11 MB plus the app.

**What changed, on both lines:**
- **`core/engine.py` (new):**
  - loads only when the launcher allows it and AI is on;
  - checks the CPU, then that the file exists, then its SHA-256 (2.3 s), then imports the runtime and loads;
  - runs one call at a time behind a lock;
  - is released by `stop()`;
  - opens no network: no socket or HTTP import.
- **`server.py`:**
  - `_ai_chat_local` calls the engine and carries its finish reason as `stop_reason` (item 12);
  - `/api/ai/status` reports off, loading, ready or unavailable, with the engine's own message;
  - `/system-ram` reports the 8 GB AI minimum and the CPU check;
  - the AI toggle starts or stops the engine;
  - the endpoint and model settings are never written;
  - the Ollama install, pull and tags code is gone;
  - the R-b notice (`/api/ai/ollama-notice`) reads what is there and opens `ms-settings:appsfeatures`. It removes
    nothing.
- **`launch.py`:** no Ollama starter. `_start_engine()` runs after the server is up, and `_stop_engine()` runs after
  the window closes.
- **The client:**
  - onboarding offers *Turn on local AI* / *Continue with AI off* against the machine check, with no download;
  - Settings → AI shows the engine's state;
  - the one-time Ollama notice;
  - the model picker, endpoint override and Ollama setup are gone.
- **Installers:** all three ship `{app}\models\phi3.5-mini-instruct-q4.gguf`, stored uncompressed, with no Ollama.
- **`requirements.txt`:** `llama-cpp-python==0.3.35`, from the project's CPU wheel index.
- **Dev tools:**
  - `voice_discipline_test.py` and `llm_model_eval.py` run on the engine, with a seed per call in the eval;
  - `llm_runtime_spike.py` is marked as the historical control.
- **2.0 only:** item 28's `_model_ready` asks the engine's state, and s26 drives the engine's finish reason.

**Tests:**
- `s60` was rewritten on a stand-in model (12 checks).
- `s61` is new (29 checks): AI off loads nothing; the CPU check comes first; checksum refusal; missing file; runtime
  failure leaves the app answering; no network imports; Ollama absent from shipped code, with a mutation check; the
  notice removes nothing and shows once; the installers ship the model.
- **`s52` now proves an AI call opens no connection at all, not even to this computer.** A mutation that puts a call
  behind a local port is caught.
- `s50`, `s55`, `smoke_test` and (2.0) `s26` follow the changes.

**Gates:**
- lts/1.x **850 / 0** (`a594f73`, pushed).
- master **2151 / 0**.

The first 1.x run caught one ordering fault in s61: s50's sweep had already marked the notice shown. It was fixed to
start from never-shown.

**Still open, by the ruling:**
- **The real 8 GB machine test** (R-d, the hard completion gate). It also decides 4096 against 2048.
- **The clean-machine run** of the packaged build: no prior Python, no Visual C++ redistributable, no Ollama. That
  can be the same machine.
- **Building the installer itself** with the 2.2 GB model inside (Inno Setup is installed here; not yet built).
- **Vulkan** (R-c), a separate later implementation.
- **The licence release gate** on the exact artifact (ruling 8).

## 7. Acceptance (Rob, 2026-10-02)

*"i accept"*. The build is ACCEPTED as built, with the 8 GB test still outstanding.

## 8. The 8 GB test: the kit, and a dry run (2026-10-02)

Rob: *"Run the test."* It cannot run here: this machine has 34 GB, and R-d rules that it cannot substitute. So the
test was built, packaged and dry-run, ready for the real machine.

**`engine_8gb_test.py`**, also packaged as `engine_8gb_test.exe`, so the test machine needs no Python. That makes the
same run the clean-machine test too.
- It launches the packaged Groundwork twice, with a throwaway data folder, and measures R-d's six points:
  - the load, and the engine's state;
  - ordinary requests timed **while the model loads** and **while it generates**;
  - a real narration-sized request;
  - free memory, swap and **hard page faults per second** (the paging cliff);
  - the model released and the process exiting on a normal close;
  - a second launch.
- It writes `engine_8gb_report.json`. It passes or fails nothing; Rob rules on the figures.
- **The kit:** `installer_output/gw_8gb_test_kit/` (git-ignored): the packaged 2.0 Groundwork with the model in
  `models\`, the test exe, and a README with how to run it. About 2.2 GB.

**The dry run, on this machine (34 GB) - not the 8 GB result:**

| | run 1 | run 2 |
|---|---|---|
| window up | 3.1 s | 1.2 s |
| engine ready after launch | 8.2 s (load 1.6 s) | 8.1 s |
| requests while loading | 90, 0 errors, median 0.018 s, worst 0.084 s | 90, 0 errors, worst 0.080 s |
| requests while generating | 66, 0 errors, worst 0.34 s | 69, 0 errors, worst 0.046 s |
| AI request | completed, 11.6 s, 109 words, `end_turn` | completed, 11.7 s |
| Groundwork + window, model loaded | 4.79 GB private | 4.79 GB |
| free memory used up | 5.8 GB (18.74 to 12.97 GB) | 5.8 GB |
| hard page faults | 0 / s | 0 / s |
| on close | model released in 1.0 s, exited in 3.0 s | 1.0 s, 3.5 s |

**What it predicts:** an 8 GB machine typically has 3–4 GB free once Windows and background programs are running.
Groundwork with AI on takes about 5–6 GB, so the 8 GB run is likely to page. The 2048 context saves about 0.9 GB,
which may still not be enough. The real run's page-fault figure is the deciding number, and R-d's choice between
4096 and 2048, or a finding that 8 GB cannot hold the narrator, follows from it. **Not decided here:** a prediction
is not the test.

## 9. Tuned for the 8 GB floor (Rob, 2026-10-02: "make the 8 GB configuration work")

Memory only, never the model's arithmetic. Each step was checked **word for word** against the validated 4096
configuration: the six voice cases on two seeds, **12 of 12 identical**. So the voice A/B (R8 0/120) carries over
unchanged.

| step | process memory, model loaded |
|---|---|
| the first build: 4096 context, f16 cache | 4.53 GB |
| 2048 context | 3.63 GB |
| OpenBLAS capped at one thread (numpy reserved 620 MB on 20 threads; Groundwork does no numpy maths) | 3.02 GB |
| prompt batch 256 | 2.90 GB |
| model file **read in, not memory-mapped** (the mapped file stayed resident beside the CPU build's own copy, ~1.8 GB) | **2.83 GB resident** (was 4.60 GB resident) |

- **The 8-bit KV cache stays out.** Rob proposed it; it was raised back because the 20-seed A/B gave it **2 R8
  violations in 120**, and at 2048 it would save only ~0.4 GB. The kit measures it on the real machine, labelled
  *R8-disqualified unless re-validated*.
- Phi-3.5, the CPU-only baseline and the launch/close lifecycle are unchanged.
- **Guards in s61:** the shipped values; OpenBLAS set before anything can import numpy (in `launch.py` and
  `core/engine.py`); the file not mapped; the test-only switches (`GROUNDWORK_TEST_ENGINE_*`) set by nothing in
  Groundwork.
- **Gates:**
  - lts `102a208` 884 / 0, then `a0d971e` 885 / 0;
  - master `e834a75` 2204 / 0, then `21281db` 2205 / 0.

**The kit is now a configuration-selection test**: shipping twice (the second run is R-d's point 6), then the 8-bit
cache for comparison. The target, in Rob's words: *Groundwork remains responsive, the AI request completes, and
sustained memory pressure does not turn ordinary use into disk-bound behavior* - not zero paging.

**Dry run of the tuned kit, on this machine (not the 8 GB result):**

| | shipping, run 1 | shipping, run 2 | 8-bit cache (R8-disqualified) |
|---|---|---|---|
| free memory taken, model loaded | **3.26 GB** (was 5.8) | 3.29 GB | 2.93 GB |
| Groundwork + window | 3.35 GB (was 4.79) | 3.34 GB | 2.96 GB |
| requests while loading / generating | 0 errors, worst 0.27 / 0.05 s | 0 errors, worst 0.27 / 0.06 s | 0 errors |
| AI request | completed, 12.2 s | completed, 12.3 s | completed, 10.6 s |
| hard page faults | 0 / s | 1 / s (once) | 0 / s |
| on close | released 1.0 s, exited 4.0 s | 1.0 s, 4.0 s | 1.0 s, 4.0 s |

**State (Rob, 2026-10-02):** the architecture decision is settled; the runtime tuning looks promising; the code is
green on both lines; **8 GB usability is still unproven; the engine replacement is not closed.** The cold-start load on
the 8 GB machine must read 2.2 GB from disk either way, so expect it to be slower there than the 1.44 s measured here.

## 8. Status

BUILT and ACCEPTED on both lines (lts `a594f73`, master `84469f5`).

**NOT COMPLETE FOR RELEASE.** These remain open:
- The real 8 GB machine test. It is the hard gate, and it also chooses between 4096 and 2048.
- The clean-machine run of the packaged build.
- Building the installer with the model inside.
- The licence release gate.
- Vulkan, later (R-c).

The onboarding revisit (item 30, A6) is next.
