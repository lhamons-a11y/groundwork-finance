# Item 96 — The AI engine on Apple Silicon's graphics (Metal)

Opened 2026-10-17 (Rob: *"can we add apple metal support ?"*). **No code.** Item 33 Q1 shipped the Mac on the
processor first and said Metal would be *"a later, separate test, on the same terms as Vulkan: it falls back, and it
is measurably better."* Item 95 left it out on purpose (`GPU_ENGINE.md` §5). This pass says what Metal needs and puts
it to Rob.

---

## 1. What is there today (gpu-engine `6425a23`)

- **The Mac engine is built in CI from source, with Metal turned off.** `macos-build.yml` builds
  `llama-cpp-python 0.3.35` with `CMAKE_ARGS=-DGGML_METAL=OFF`. Every published macOS arm64 wheel, Metal included,
  failed its zip CRC (measured 2026-10-08), so building from source is the only way either kind ships.
- **Fitting knows only Vulkan.** In `core/engine_fit.py`:
  - `has_graphics_backend()` looks for `ggml-vulkan` in the engine's libraries;
  - `load_backends()` loads only `ggml-vulkan`;
  - one chip is chosen with `GGML_VK_VISIBLE_DEVICES`;
  - a device counts as graphics when its name starts with `Vulkan`.
  On a Metal build none of these would match. So fitting wouldn't run, and the engine would load on the processor
  as it does now (`n_gpu_layers` is only set on the fitted path).
- **Item 33 Q6 is still open.** No Apple Silicon Mac has run the engine at all, on the processor or otherwise.

## 2. What is different about Metal

- **One graphics chip, sharing the memory.** An Apple Silicon Mac has one GPU, and it uses the same memory as the
  processor. So there is no chip to pick and no card that "can't hold the model". Like the Iris Xe (Vulkan
  `uma: 1`), it saves **no memory**. The gain, if any, is speed only. That matters on the 8 GB base M1/M2/M3 Airs,
  which are also the macOS 8 GB test (item 33 Q6).
- **It is another backend, so it writes different words.** Item 95 measured that the processor, Intel and NVIDIA
  each wrote a different answer at the same seed (`GPU_ENGINE.md` §2 B4). Metal will be no different.
- **One seed during fitting is not enough to clear a backend.** The pre-release A/B run today (`GPU_ENGINE.md`, the
  A/B section) found invented figures in 2 of 120 NVIDIA answers, 4 of 120 Intel and 4 of 120 on the processor. Almost
  all of them come from the same fault on every device: an answer that doesn't end. NVIDIA's one-seed fitting check
  had come back clean, and Intel's had flagged it. A six-answer check can't tell those apart. So the 20-seed A/B,
  measured beside the processor on the same harness, is the gate that counts, and it has to run on Metal itself (how
  it is judged is G4″ there, for ruling).

## 3. Points for ruling

**M1. Metal is offered the way Vulkan is: fitted, never forced.** The fitting step times the processor and Metal in
child processes and takes the faster one whose answers pass R8, with no user setting (G0 applies unchanged). A Metal
load that fails falls back to the processor at once (G6). *Recommended.*

**M2. The build.** The Mac CI build turns Metal on (`-DGGML_METAL=on`, with its shader library embedded in the
engine, so nothing is looked up at run time). It keeps the same pinned 0.3.35 source and checks the version as now.
If the Metal build can't run on a Mac without a usable GPU, it is the CPU build that ships, as Vulkan's hard
dependency was handled in G1. *Recommended.*
- Not yet known: whether the Metal backend is a separate library that can be loaded at run time (as Vulkan is on
  Windows) or linked in. That decides how `has_graphics_backend()` and `load_backends()` recognise it, and is
  measured on the first CI build, before any engine code.

**M3. Fitting learns Metal by name, not by a second code path.** The Vulkan-only checks in §1 become "a graphics
backend": Vulkan on Windows, Metal on the Mac. Choosing one chip only applies where there are several. The stored
fingerprint carries the Mac's chip name and macOS version in place of the Windows driver list. *Recommended.*

**M4. Metal ships only after its own pre-release voice A/B.** 20 seeds × 6 cases through `CASES` and `check()`,
shipped settings, beside the processor on the same Mac and harness. It passes on whatever bar G4″ sets for Vulkan
(recommended there: R8 no worse than the processor's, gate pass within noise). Otherwise Metal is named as excluded
and the Mac stays on the processor. *Recommended.*

**M5. It needs a real Apple Silicon Mac, ideally the 8 GB one.** The same machine closes item 33 Q6. CI can prove the
build and packaging. Whether GitHub's macOS runners expose the GPU to Metal at all is unverified and is checked
first, but CI can't replace the speed or usability measurement either way (R-d). *Recommended.*

**M6. Order.** After item 33 Q6 has proved the processor engine on a real Mac, because the processor is the fallback
Metal is measured against. Master only (item 32 L1: 1.x gets data-loss, wrong-figure and security fixes only).
*Recommended.*

## Closing

Metal is a fair candidate. Apple's graphics are well supported by llama.cpp, and the fitting step item 95 built is
most of what's needed. Two things have stopped it being started: no Mac to measure on, and the lesson from today's
A/B that a backend has to be cleared on 120 answers, not 6.
- **The Mac:** Rob has a Mac mini he can install and test on (2026-10-17). Its chip and memory are not yet
  confirmed, and it must be Apple Silicon. A measurement kit for it would touch no app code.
- **Nothing here is authorised to build.**

## M1-M6 ruled — Rob, 2026-10-18

*"i accept item 96"*: M1-M6 are ruled as recommended. That is a ruling, not authorisation to build. Code still
needs Rob's go-ahead, and M6 puts it after item 33 Q6.
- **M4 now has its bar.** G4″ (a) was ruled the same day: a backend passes when its R8 count is no worse than the
  processor's on the same harness in the same run, and its gate pass is within noise. Item 97's stops
  (`engine.STOP` and the role tokens) apply to every model call, Metal included, so the Mac A/B runs on the stopped
  engine.
- **What comes next is measurement, not code.** A kit for Rob's Mac mini, once its chip and memory are confirmed:
  - the pinned 0.3.35 engine built twice, CPU and Metal;
  - the 20-seed × 6-case A/B at 512 tokens on each;
  - fitting's timing test on each.

  That gives item 33 Q6 its processor run and M4 its evidence. It touches no app code.
