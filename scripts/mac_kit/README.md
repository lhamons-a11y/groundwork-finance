# Mac engine kit (item 96 Metal, item 33 Q6)

Measures Groundwork's AI engine on an Apple Silicon Mac, on the processor and on Metal. **Measurement only:** it
installs nothing outside this folder, doesn't touch the app or any household data, and sends nothing anywhere.

What it answers:
- **Item 33 Q6:** does the engine run on a real Apple Silicon Mac with 8 GB, and how much memory does it leave?
- **Item 96 M4:** is Metal faster than the processor, and are its answers no worse on invented figures (R8), with the
  gate pass within noise? That's the G4″ (a) bar.

## Once: get the pieces onto the Mac (about 15 minutes)

1. **Apple's command-line tools:** open Terminal and run `xcode-select --install`, then click Install.
2. **Python 3.12:** download the macOS installer from python.org (Downloads → macOS → Python 3.12.x, "macOS 64-bit
   universal2 installer") and run it.
3. **This repository:** on github.com, open the repository, choose the `master` branch, Code → Download ZIP, and
   unzip it. Or `git clone` it if git is signed in.
4. **The model file** (2.2 GB), one of:
   - copy `phi3.5-mini-instruct-q4.gguf` from the Windows laptop (USB stick or a shared folder). It is
     `C:\Groundwork\vendor\phi3.5_model\blobs\sha256-b5374915…`; any file name is fine.
   - or, with the GitHub CLI signed in, run `python3.12 fetch_model.py` in the repository. It downloads the
     release asset and checks it.

## Run

In Terminal, in the unzipped repository folder:

```
bash scripts/mac_kit/setup.sh
bash scripts/mac_kit/run.sh ~/Downloads/phi3.5-mini-instruct-q4.gguf
```

- **`setup.sh`** builds the pinned engine (llama-cpp-python 0.3.35) once from its official source, with Metal - the
  only Mac build there is (its CMakeLists.txt forces Metal on for Apple). It takes about 5–10 minutes, mostly compiling.
- **`run.sh`** checks the model's fingerprint, then measures that build twice: on the processor (no layers on the
  graphics) and on Metal (every layer). Close other apps and keep the Mac
  plugged in first. It takes about 30–60 minutes and keeps the Mac awake.

Each run gets:
- the load time and the free memory before and after;
- one untimed warm-up answer;
- fitting's timing answer (first word, whole answer);
- the voice A/B: 20 seeds × the 6 voice cases at 512 tokens, with the shipped stops (item 97).

## Send back

At the end it prints a short report and saves it as `scripts/mac_kit/results-<date>/REPORT.txt`. Copy that text into
an email or a message to Claude. It holds no financial data: the voice cases are made-up test figures. Keep the
results folder, because it has every answer if a figure needs looking at.
