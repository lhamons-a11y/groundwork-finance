# The in-app engine on macOS and Linux (item 33)

Opened 2026-10-03 (Rob: *"open it"*). **No code.** This gap was named under item 31 on 2026-10-02: only the Windows
build (`groundwork.spec`) ships the engine. This pass measures what the other two platforms need and puts it to Rob.

---

## 1. What was measured (master `2d2c155`, lts `9c52cc9`)

**The specs** (`groundwork_macos.spec`, `groundwork_linux.spec`):
- They do not collect `llama_cpp`, and they still **exclude numpy**, which `llama_cpp` imports.
- They package no model.
- So on both platforms the engine imports nothing, and AI reports *unavailable (runtime)* - honestly, by item 31's
  ruling 7, never a crash. But it never runs.

**The published runtime wheels** for the shipped version, `llama-cpp-python 0.3.35` (PyPI has only the source):

| platform | wheel | consequence |
|---|---|---|
| Windows x64 | yes (cpu index) | ships today |
| Linux x86_64 | yes (`manylinux2014`, cpu index); also aarch64 | CI's Ubuntu smoke test installs it, green on every push |
| macOS Apple Silicon | yes (cpu index **and** metal index) | buildable |
| **macOS Intel** | **none** | `requirements.txt`'s `--only-binary` install **fails** on an Intel Mac |

**The model is git-ignored** (`vendor/`). **No CI build can package it today, on any platform.** The Windows kit works
only because it is built on this machine, which has `vendor/phi3.5_model`. The macOS build is CI-only
(`macos-build.yml`, run on tags or by hand) and has not run since item 31 changed the requirements.

**Where an app finds the model.** `core/engine.py` looks beside the executable, one folder up, and in PyInstaller's
`_MEIPASS`. In a macOS `.app` those are `Contents/MacOS`, `Contents` and `Contents/Frameworks`. Apple's place for
bundled data is **`Contents/Resources`**, which is not searched. The Linux tree works like Windows (`models/` beside
the binary).

**The processor check** already covers both: Linux reads `/proc/cpuinfo` for AVX2; an Intel Mac uses `sysctl`; Apple
Silicon (arm64) needs no AVX2.

**The website** says *"Apple Silicon and Intel Macs"* and gives macOS and Linux the same RAM line as Windows (*"8GB+
for the optional local AI"*). Today neither platform can run the AI at all.

---

## 2. Points for ruling

**Q1. Apple Silicon ships the engine, CPU build first.** This is R-c's order applied to the Mac.
- On Apple Silicon the GPU shares the same memory, so Metal is not the separate-VRAM question Vulkan is on Windows.
- But it is still a different build, with its own way to fail.
- So the cpu-index wheel ships first. Metal is a later, separate test, on the same terms as Vulkan: it falls back,
  and it is measurably better.

*Recommended.*

**Q2. Intel Macs: AI unavailable, honestly.** No wheel is published. Building one from source in CI would ship an
artifact nobody tested, which breaks ruling 4 (*the exact tested artifact*).
- `requirements.txt` gets a platform marker, so the install does not fail there.
- On an Intel Mac the engine reports AI unavailable, and everything else works.
- The website says local AI needs an Apple Silicon Mac.

*Recommended.*

**Q3. Linux x86_64 ships the engine** from the `manylinux` CPU wheel, with the same AVX2 check. aarch64 Linux is out
of scope until someone asks. *Recommended.*

**Q4. Packaging, the same as Windows** (item 31 E6):
- both specs collect `llama_cpp`, and stop excluding numpy;
- a build fails without the runtime, rather than shipping an AI that can never start;
- the OpenBLAS cap already applies (`launch.py`, all platforms);
- the model goes to **`Contents/Resources/models`** on macOS (the engine adds that path to its search) and to
  **`models/`** beside the binary on Linux;
- the SHA-256 check applies on every platform.

*Recommended.*

**Q5. The model for builds that are not on this machine.** Because it is git-ignored, CI cannot see it.

*Recommended:* the exact tested file is published once as a **pinned release asset** (a GitHub Release of the GGUF).
CI downloads it, checks its SHA-256 against `core/engine.py`'s pin, refuses to build on a mismatch, and packages it.
Redistribution is the licence gate's question (ruling 8), already a release gate.

*Alternative:* keep the macOS and Linux builds local, which needs those machines here.

**Q6. What has to be tested on real hardware.**
- An **Apple Silicon Mac**, ideally an **8 GB** one. The base M1, M2 and M3 MacBook Airs ship with 8 GB, so the same
  machine is the macOS 8 GB test.
- A **Linux x86_64** box.
- CI runners can prove the packaging and an engine smoke run (GitHub's arm64 macOS runner has about 7 GB of memory,
  its Ubuntu runner 16 GB). They cannot replace R-d's usability ruling.
- The 8 GB kit (`engine_8gb_test.py`) is Windows-only today. A macOS/Linux version is part of this item.

*Recommended.*

**Q7. Until it is done, the website says what is true:** *local AI is available on Windows; on macOS (Apple Silicon)
and Linux it is coming*, and Intel Macs run Groundwork without local AI. Not deployed until Rob says so, like the
other site changes. *Recommended.*

**Q8. Both lines, 1.x first.** 1.x ships macOS and Linux downloads too. *Recommended.*

## 3. Ruling and authorisation (Rob, 2026-10-03)

**Q1–Q8 approved as recommended.** Q2 stands as written: *"Do not compile the engine from source for Intel just to
claim support. Graceful unavailability is preferable to shipping an untested artifact."* An Intel Mac is described
accurately: **the application runs; the local AI engine is unavailable there.**

**Clarification 1, an acceptance criterion: five separate states, never collapsed.**

```text
platform supported → the app packages → the AI engine is available → the model loads → inference works (on real hardware)
```

CI can prove the first four. **It does not prove the fifth.** A green build is never read as *"Mac/Linux AI is
validated"*, and Apple Silicon and Linux AI are not called available until Q6's hardware validation passes.

**Clarification 2: the model's fingerprint check is mandatory.** The build fails if the download fails, if the file
is missing, if its SHA-256 does not match, or if the model cannot be packaged. That replaces *"whatever happens to be
in `vendor/` on the developer's machine"* with a pinned engine, a pinned model and a verified fingerprint, so the
package is reproducible.

**Authorised:** Q1–Q5 first (packaging, the model path, the reproducible model), and **Q7 now**: the website is
corrected immediately. Then Q6's real Apple Silicon and Linux hardware gives the final inference and usability proof.
Both lines, 1.x first (Q8).

## 4. The build: Q1–Q5 and Q7 (2026-10-03)

- **`spec_engine.py`** (shared by the macOS and Linux specs).
  - It reads the model's name and SHA-256 from `core/engine.py`, so there is still one pin.
  - `engine_parts()` collects the runtime and **refuses the build without it**. On an **Intel Mac** it builds without
    the engine and says so (Q2).
  - `model_data()` stages the model as `models/<MODEL_FILE>` and **refuses the build** if the file is missing or is not
    the tested file. Rob's clarification 2: the check is mandatory.
- **Both specs** collect the runtime and the verified model, no longer exclude numpy, and keep the native libraries out
  of UPX. The model lands in `Contents/Resources/models` on macOS and `_internal/models` on Linux.
- **`core/engine.py`** also searches a macOS app's `Contents/Resources` (Q4).
- **`requirements.txt`:** the runtime is skipped on an Intel Mac (`sys_platform != "darwin" or platform_machine ==
  "arm64"`), so the install never fails there. Checked: Windows, Linux and Apple Silicon true; Intel Mac false.
- **`fetch_model.py`** (Q5) downloads the pinned **release asset** (tag `model-phi3.5-mini-q4`) with `gh`, verifies
  the SHA-256, and exits 1 on a failed download, a missing file or a mismatch. In CI it sets `GW_MODEL_PATH`.
  - `macos-build.yml` runs it before PyInstaller.
  - **`linux-build.yml` is new**, the first Linux CI build. Its last step checks that the model and the runtime are in
    the package, and says in its own text that a green run proves packaging, not inference.
- **The website (Q7):**
  - macOS: *"Local AI: coming to Apple Silicon Macs. Intel Macs run Groundwork fully, without local AI."*
  - Linux: *"Local AI: coming to Linux. Groundwork runs fully without it."*
  - The Windows line is unchanged. **Not deployed.**
- **Tests (s61, 12 new checks):** one pin; the build refusing a wrong and a missing model; the tested file staged
  under its name; the Intel Mac building with neither engine nor model; both specs; the requirements marker; the
  Resources path; both workflows verifying before packaging; the website lines.

**Found by building, not by the gate:** the Linux spec never imported `sys`, so the new block failed at its first
line. The gate's text checks could not see it. Building it for real did. Both specs' blocks now import what they use.

**Proven on real Linux (WSL Ubuntu, x86_64, this machine).** These are states 2–4 of Rob's five, never state 5:
- **The engine:** the `manylinux` wheel installed; `core/engine.py` passed the CPU check, verified the SHA-256, loaded
  the model and answered *"Understood."* (the same text as on Windows); `stop()` released it. The load took about
  28 s only because WSL reads `/mnt/c` slowly.
- **The package:** `groundwork_linux.spec` built (exit 0) with `GW_MODEL_PATH` exactly as CI sets it. It contains the
  model under its shipped name (2,176,177,152 bytes), `libllama.so` and the `libggml` set, and numpy; 2.2 GB in all.
- Running the packaged app needs a Linux desktop with GTK, so it is **not shown here**.

**Gates:** lts/1.x **927 / 0** (`138d3e4`), master **2257 / 0** (`7eed5e0`).

**Not done, by the ruling's own order:**
- **The release asset does not exist yet**, so both build workflows will fail at *Fetch and verify* until it is
  published. That is the intended behaviour: no model, no build. Publishing it uploads the 2.2 GB model to this
  **private** repository's Releases, and **waits for Rob's go-ahead** (the licence gate, ruling 8, covers
  redistribution).
- **No macOS build was run.** There is no Mac here.
- **Q6 is the real hardware:**
  - an Apple Silicon Mac (ideally 8 GB) and a Linux desktop;
  - the five states proven there;
  - a macOS/Linux version of the 8 GB kit.
- Apple Silicon and Linux AI are **not called available** until Q6 passes.

## 5. Acceptance (Rob, 2026-10-03)

*"Yes"*. Q1–Q5 and Q7 are ACCEPTED as built: lts `138d3e4`, master `7eed5e0`.

## 6. Status

Q1–Q5 and Q7 ACCEPTED. **Item 33 stays open** for two things:
- **the model release asset** (tag `model-phi3.5-mini-q4`): not created. Publishing it is Rob's decision, alongside
  the licence gate (ruling 8). Until then both build workflows stop at *Fetch and verify*, by design;
- **Q6, real hardware:** an Apple Silicon Mac (ideally 8 GB) and a Linux desktop, to prove state 5. Apple Silicon and
  Linux AI are not called available before then.
