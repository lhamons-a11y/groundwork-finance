# Item 93 — The AI engine on the graphics card, fitted to each computer

**OPENED 2026-10-17 (Rob: "lets add the gpu support"; "Could we have groundwork run benchmarks in the background to
optimize the settings per machine"). G0 RULED 2026-10-17 (below). G1-G9 RULED 2026-10-17 as recommended (Rob: "I
approve G1-G9 as recommended."). Build not yet authorised. Documents only; no code in the repo has changed.**

## Summary

Today the AI runs on the processor only. Most computers also have a graphics chip: built into the processor (Intel
UHD / Iris, AMD Radeon) or a separate card (NVIDIA GTX / RTX, AMD). Measured on this laptop, the same model with the
same settings answers about 4× faster on its NVIDIA card than on its processor, and 1.6× faster on its built-in Intel
graphics. Your point about memory holds too: on a separate card the model lives in the card's own memory and uses
almost no system memory (0.19 GB, against 2.93 GB on the processor). That matters most on the 8 GB machines this
release targets.

The plan has two halves. First, a GPU-capable engine: one Vulkan build that covers NVIDIA, AMD and Intel graphics and
still runs on the processor when there's no graphics driver. Second, a fitting step: Groundwork times the model on
each device the computer has and uses the fastest one that also passes the correctness check. You've ruled that the
user doesn't override that choice (G0). Item 31's R-c already set Vulkan's terms: CPU always available, falls back on
a machine with no Vulkan driver, and a real gain at 8 GB. This document builds on that ruling rather than reopening it.

## 1. What is there today

- **The engine** (`core/engine.py`, item 31): llama-cpp-python 0.3.35, the CPU wheel from abetlen's CPU index
  (`groundwork.spec:46`, `requirements.txt`). Settings: 2048 context, batch 256, f16 cache, no mmap,
  `OPENBLAS_NUM_THREADS=1`. `n_threads` is not set, so llama.cpp uses its default (about one per physical core). AVX2 is
  checked before import. The model loads only when AI is on (R-a / A9).
- **R-c (item 31, 2026-10-02):** *"CPU first, then Vulkan behind its own packaged test"*. Vulkan becomes supported
  only once it is shown to load, to fall back to CPU on a machine with no Vulkan driver, and to give a real benefit on
  an 8 GB shared-memory machine.
- **No GPU code anywhere.** Nothing passes `n_gpu_layers`, and nothing reads the graphics hardware.

## 2. Measured 2026-10-17 (this laptop: i7-12800H, 14 cores / 20 threads, Intel Iris Xe, NVIDIA RTX A1000 4 GB, 34 GB RAM)

**A. llama.cpp's own benchmark** (official build b11556 Vulkan, phi3.5 q4, 1024 tokens read, 128 written, 3 runs):

| device | reading (tok/s) | writing (tok/s) |
|---|---:|---:|
| processor, default threads | 73.8 | 21.4 |
| processor, 4 threads (stand-in for an older quad-core) | 52.2 | 18.5 |
| Intel Iris Xe (built in) | 280.6 | 19.8 |
| NVIDIA RTX A1000 (separate card) | 1387.5 | 53.1 |

**B. Groundwork's own engine settings**: llama-cpp-python 0.3.35 built from source with Vulkan, in a scratch venv.
The test was about 1,000 tokens of household facts plus a question, with an answer of up to 300 tokens:

| device | first word | whole answer | system RAM used by the model |
|---|---:|---:|---:|
| processor | 18.6 s | 41.6 s | 2.93 GB |
| Intel Iris Xe | 6.5 s | 25.3 s | 2.97 GB |
| NVIDIA RTX A1000 | 1.5 s | 10.8 s | 0.19 GB |

**What this shows:**
1. **A separate card wins on both counts:** 4× faster, and it frees about 2.7 GB of system memory.
2. **Built-in graphics speeds up reading, not writing.** It reads the facts about 4× faster, so the first word comes
   about 3× sooner, but the words come out at roughly the processor's speed. It saves no memory, because built-in
   graphics shares system RAM (Vulkan reports `uma: 1`).
3. **The 2018 built-in chips are not measured.** An Intel UHD 620 (2017-2018 laptops) has about a quarter of the Iris
   Xe's graphics units. It may give a smaller gain, or none. Only a real one can say, which is why G3 measures each
   machine rather than assuming.
4. **The words differ by device.** At temperature 0 with the same seed, the processor, Intel and NVIDIA each wrote a
   different answer (different first words, same facts). That's expected, because the math is done in a different
   order, but it means a device's answers are a different engine as far as the voice checks are concerned (G4).
5. **Not yet verified:** a GTX 10-series card. Pascal cards support Vulkan. CUDA 13 has dropped them, which is one more
   reason to choose Vulkan. A GTX 1060 has about the same memory bandwidth as this A1000, so similar writing speed is
   likely but unverified.

**C. Found while building:**
- **The Vulkan library is wired in as a hard dependency.** `ggml.dll` loads `ggml-vulkan.dll`, which loads
  `vulkan-1.dll` (checked with `dumpbin /dependents`). On a computer with no Vulkan driver, the whole engine would fail
  to import, processor included. That would break *CPU always available* (R-c). See G1.
- **A from-source build is tuned to the machine it's built on** (CMake's `GGML_NATIVE`, on by default). A shipped build
  must turn that off and target the AVX2 floor the engine already checks for, or it may crash on older processors.
- **Size:** `ggml-vulkan.dll` is 54 MB. The engine's libraries grow from 8 MB to 81 MB, small next to the 2 GB model.
- **Build recipe:** VS 2022 Build Tools, CMake 4.4.4 and Vulkan SDK 1.4.363.0 (installed on this machine 2026-10-17),
  `CMAKE_ARGS=-DGGML_VULKAN=on`, and a short `TMP` path, because the source archive has paths over Windows' 260-character limit.

## 3. G0 — ruled

**G0. The software chooses. The user does not override it.** Rob, 2026-10-17: *"the user should not be able to
override the choices. I know we always default to let the user decide but in this case I think the user should allow
the software to do it thing to make the overall experience better."*

This covers the device and engine settings only. Whether AI is on at all stays the user's choice (A9, item 64).

## 4. Points for ruling

**G1. One library, with Vulkan loaded only if the driver is there.** Build the engine so the graphics backend is a
separate piece loaded at run time (llama.cpp's `GGML_BACKEND_DL`, the way the official release ships). On a computer
without a Vulkan driver it simply isn't loaded, and the processor path works as it does today. The other way would be
to ship two complete copies of the library (CPU and Vulkan) and pick at load, which is simpler but bigger and two
things to keep in step. Whether llama-cpp-python 0.3.35 loads backends this way is **not yet measured**. It's the
first thing the build would prove, and if it can't, this comes back to you with the two-copy option.
*Recommended: run-time backend, measured first.*

**G2. Vulkan only. No CUDA, no Intel-specific build.** One build covers NVIDIA (including the GTX 10-series), AMD and
Intel. CUDA builds are 150-400 MB and CUDA 13 no longer supports 10-series cards. *Recommended.*

**G3. The fitting step: what it measures, and how it chooses.** For each device the computer has (the processor and
each graphics chip Vulkan reports):
- load the model with the shipped settings and time a short fixed answer: reading time and writing speed;
- on a separate card, find the most of the model that fits in its memory (a 2 GB GTX 1050 can't hold all of it, so
  part goes on the card and the rest on the processor);
- read how much system memory the model left free;
- choose the device with the shortest **whole-answer time** among those that passed G4.

Each candidate runs in **its own short-lived process**, so a graphics driver that crashes takes down only that test,
never Groundwork, and that device is marked failed. *Recommended.*

**G4. Speed only chooses among correct answers.** Because each device writes different words (§2 B4), a device is
used only if its answers pass the same checks the processor's do. Two levels:
- **Before release, on our hardware:** the 20-seed voice A/B (`CASES` + `check()`, R8 cardinal) runs on each
  backend family we ship for (NVIDIA, Intel and AMD where we can get one). This is the run that disqualified the q8 cache.
- **On the user's computer, during fitting:** the timed answer is one fixed case run through `check()`. If R8 or any
  gate rule fails, that device is out and the processor is used.

Correctness is never traded for speed (*capable is not admissible*). *Recommended.*

**G5. When the fitting runs.** This is your open question from 2026-10-17:
- **(a) Once, as a visible step** the first time AI starts on a computer: "Fitting the AI to this computer (about a
  minute)". It takes 3-5 model loads plus short answers, about a minute on this laptop. It doesn't compete with
  anything, because nothing else has started.
- **(b) In the background while the app is idle.** The AI runs on the processor until fitting finishes. But on an 8 GB
  machine a second copy of the model in memory is what we're trying to avoid, and it would slow whatever the user is
  doing.

*Recommended: (a).*

**G6. When it runs again.** Only when something that could change the answer changes: a different graphics chip, a
new graphics driver version, a new engine version or a different model file. Never on a schedule. If the chosen
graphics device fails at a later launch, that launch uses the processor, and the next one runs fitting again.
*Recommended.*

**G7. What the user sees.** Under G0 there's no override, but the result is still shown, so nothing about the machine
is decided out of sight (*no silent learning*; transparency standard). In Settings' AI section, a line such as:
*"AI runs on: NVIDIA GeForce GTX 1060 — answers in about 11 s, 3.8× faster than this computer's processor (checked
17 Oct 2026)."* There's no button to change it. If a device failed, it says so: *"Intel UHD 620 was tried and was
slower than the processor."* *Recommended.*

**G8. AI off means no fitting.** No model and no graphics code are loaded (R-a, A9, A10). The fitting step belongs to
the AI's own start-up. *Recommended; restates existing rulings.*

**G9. Context size per machine (2048 or 4096).** Item 31 still has 4096 vs 2048 open, waiting on the 8 GB test. With a
separate card, the extra context goes in the card's memory, not the system's. So the fitting step could choose 4096
where the memory allows and 2048 otherwise. This is new behaviour on a ruling still open, so it's yours. *Recommended:
not in this item. Ship 2048 everywhere and keep the 4096 question with item 31's 8 GB test.*

## 5. Left out, on purpose

- **Battery.** On a laptop the separate card uses more power. Fitting chooses by speed, and G0 means no override.
  Windows' own graphics settings can still send the app to the power-saving GPU.
- **Apple Silicon (Metal).** That's item 33's Q1, on its own terms.
- **Threads, batch size and cache type.** These stay as measured in item 31. The q8 cache stays disqualified on every device.
- **Any change to the model.** Still phi3.5 q4, pinned by checksum.

## 6. How it would be built and proven, once authorised

1. **The engine build:** Vulkan with run-time backends (G1), `GGML_NATIVE` off and the AVX2 floor, pinned in the
   build notes. The spec's CPU-wheel check becomes a check for this build.
2. **Fitting** in `core/engine.py`: one child process per device, the timed `check()` case, the choice stored with its
   hardware fingerprint (G6), and the Settings line (G7).
3. **Tests (smoke sections):**
   - AI off loads no graphics code (G8);
   - a device whose test process crashes is marked failed and the app keeps running (G3);
   - a device that fails `check()` is never chosen (G4);
   - a changed fingerprint re-runs fitting and an unchanged one doesn't (G6);
   - the Settings line names the device and its measured gain (G7);
   - nothing in the UI changes the choice (G0).
4. **The R-c proofs, which are completion criteria:**
   - on a machine **with no Vulkan driver**, the engine loads on the processor (needs a clean machine or VM);
   - on a real **8 GB** machine with built-in graphics, fitting shows a real gain or correctly picks the processor;
   - ideally also a **GTX 10-series** machine.
   The 34 GB development laptop can't stand in for any of these (R-d).
5. **The voice A/B** on each backend family (G4), before release.

## Closing

The evidence supports doing this: a separate card is a large, measured gain in both speed and memory, and built-in
graphics is a smaller gain that the fitting step will either confirm or reject on each machine. The two risks are
known and both have recommended answers: the hard Vulkan dependency (G1) and words that differ by device (G4). The
proofs that close it need hardware this laptop isn't: no Vulkan driver, 8 GB, and an older card.

## G1-G9 ruled — Rob, 2026-10-17

*"I approve G1-G9 as recommended."*

- **G1:** one library with the graphics backend loaded at run time. Measured first; if llama-cpp-python 0.3.35 can't
  do it, the two-copy option comes back for ruling.
- **G2:** Vulkan only.
- **G3:** fitting per device, each in its own process, shortest whole-answer time wins.
- **G4:** only among devices that pass the voice A/B before release and the `check()` case during fitting.
- **G5 (a):** once, as a visible step the first time AI starts on a computer.
- **G6:** fit again only on a hardware, driver, engine or model change. If the chosen device fails, the processor is
  used and the next launch fits again.
- **G7:** the result is shown in Settings, with no control to change it.
- **G8:** AI off fits nothing.
- **G9:** 2048 everywhere. The 4096 question stays with item 31's 8 GB test.

The build is not yet authorised.

## G1 proven — 2026-10-17 (build authorised by Rob: "Build item 93. Start with G1")

**The build.** llama-cpp-python 0.3.35 from source:
`CMAKE_ARGS=-DGGML_VULKAN=ON -DGGML_BACKEND_DL=ON -DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON
-DGGML_F16C=ON -DGGML_AVX512=OFF`, built with VS 2022 Build Tools, CMake 4.4.4 and Vulkan SDK 1.4.363.0, and
`TMP=C:\gwb`. The wheel is 46 MB.
- `dumpbin /dependents`: `ggml.dll` now needs only `ggml-base.dll`.
- Only `ggml-vulkan.dll` needs `vulkan-1.dll`, and it is loaded at run time.
- The CPU backend is loaded at run time too.

**What 0.3.35 does and doesn't do.** It never loads run-time backends itself. With only the import, there are zero
devices, and `Llama()` fails ("Failed to load model"). So Groundwork loads them itself through `ggml.dll`'s
`ggml_backend_load(path)`:
- the CPU backend always;
- the Vulkan backend only if it loads.

That puts the choice in the engine's hands, which G3 needs anyway.

**The four cases** (`n_gpu_layers=-1` asked for every time, with the engine's shipped settings):

| case | Vulkan backend | devices found | model loads and answers |
|---|---|---|---|
| normal | loaded | CPU, Iris Xe, RTX A1000 | yes, `llama_supports_gpu_offload` true |
| `ggml-vulkan.dll` missing | not loaded | CPU | yes, on the processor |
| no Vulkan driver DLL (the import renamed to a `vulkan-9.dll` that doesn't exist) | not loaded | CPU | yes, on the processor |
| Vulkan loader present but no drivers (`VK_DRIVER_FILES` pointing nowhere) | not loaded | CPU | yes, on the processor |

**The processor path is unchanged.** The six voice cases × two seeds on the processor are **12 of 12 identical** to
the shipped CPU wheel (abetlen's CPU index). So item 31's voice A/B (R8 0/120) carries over to the processor path of
this build unchanged.

**Learned for G3:** with two graphics chips and `n_gpu_layers=-1`, llama.cpp splits the model across both by
default. Fitting has to test, and use, one chip at a time. The chip is chosen in the fitting process before the
Vulkan backend loads, with `GGML_VK_VISIBLE_DEVICES`.

**Still owed for R-c:** this proves the fallback on this laptop by simulation. The real proof, a machine with no
Vulkan driver at all, needs that machine (§6.4).

## G4 brought back before any code — the ruled check would reject every device

G4 as ruled says: during fitting, *"if R8 or any gate rule fails, that device is out."* The measured baseline makes
that unworkable. On the processor, the reference configuration, the full gate passes **38 of 120** (item 31 §7, 20
seeds × 6 cases). A single answer fails some non-cardinal rule (R1-R7, R9, R11) more often than not, on any device.
Requiring every rule to pass on one sample would send nearly every graphics chip back to the processor by chance.
That's the null-model trap again: the threshold would be a coin flip.

R8 is different. The processor's rate is **0 of 120**, so a single R8 violation on a candidate device is a real signal.

**G4′ (for ruling):**
- **(a) Fitting checks R8 only, on all six voice cases**, one seed, at the shipped temperature. Any R8 violation and
  that device is out. The other rules are judged where they can be judged, in the pre-release A/B: each backend
  family's gate pass rate must be within noise of the processor's 38/120, and R8 must be 0. It costs six short
  answers per graphics chip: about 30-45 s on a separate card, perhaps 2 minutes on built-in graphics. The processor
  isn't re-tested, because it is the reference.
- (b) R8 on one case only. Cheaper, but one case sees few figures.
- (c) No check on the user's machine; rely on the pre-release A/B alone. Driver versions vary by machine, so this
  trusts what wasn't measured.

*Recommended: (a).* G3, G5-G8 are unaffected. Fitting code waits on this ruling.

### G4′ ruled — Rob, 2026-10-17

*"I rule G4′ (a): fitting checks R8 only, on all six voice cases; the other rules are judged in the pre-release A/B.
Continue the build."*
