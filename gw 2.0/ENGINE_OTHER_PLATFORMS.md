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

## 3. Status

OPEN: eight points for ruling (Q1–Q8). No code until ruled. The real-hardware tests (Q6) need machines Rob supplies.
