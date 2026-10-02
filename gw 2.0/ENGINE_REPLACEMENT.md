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

## 5. Status

RULED by Rob 2026-10-02 (points 1–10). Four points raised back (R-a to R-d) await his answer. Implementation is next;
no code until those are settled.
