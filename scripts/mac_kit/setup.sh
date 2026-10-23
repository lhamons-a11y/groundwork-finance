#!/bin/bash
# Item 96 / item 33 Q6 Mac kit, step 1: build the pinned engine once, with Metal (the only Mac build there is:
# llama-cpp-python's CMakeLists.txt forces GGML_METAL ON on Apple, so -DGGML_METAL=OFF is ignored).
# Run from anywhere:  bash scripts/mac_kit/setup.sh
# Needs: an Apple Silicon Mac, Apple's command-line tools (xcode-select --install) and Python 3.12 from python.org.
# Builds llama-cpp-python 0.3.35 from its official source, the way macos-build.yml does (published Mac wheels fail
# their CRC). Takes about 10-20 minutes. Nothing outside scripts/mac_kit/ is changed.
set -e
KIT="$(cd "$(dirname "$0")" && pwd)"
cd "$KIT"

[ "$(uname -m)" = "arm64" ] || { echo "This Mac is not Apple Silicon ($(uname -m)); Metal can't be tested here."; exit 1; }
xcode-select -p >/dev/null 2>&1 || { echo "Apple's command-line tools are missing: run  xcode-select --install  then rerun."; exit 1; }
PY="$(command -v python3.12 || true)"
[ -n "$PY" ] || { echo "Python 3.12 is missing: install it from python.org (macOS 64-bit universal2 installer), then rerun."; exit 1; }
echo "macOS $(sw_vers -productVersion), $(sysctl -n machdep.cpu.brand_string), $(( $(sysctl -n hw.memsize) / 1073741824 )) GB, $($PY --version)"

build() {   # build <venv>
  echo; echo "=== Building $1 (Metal)"
  rm -rf "$KIT/$1"
  "$PY" -m venv "$KIT/$1"
  "$KIT/$1/bin/python" -m pip install --quiet --upgrade pip
  "$KIT/$1/bin/python" -m pip install --no-cache-dir --no-binary llama-cpp-python \
      --index-url https://pypi.org/simple "llama-cpp-python==0.3.35"
  "$KIT/$1/bin/python" -c "import llama_cpp as l, sys; print('built', l.__version__, 'gpu offload:', l.llama_supports_gpu_offload()); sys.exit(l.__version__ != '0.3.35')"
}
build venv-metal
echo; echo "Setup done. Next:  bash scripts/mac_kit/run.sh /path/to/phi3.5-mini-instruct-q4.gguf"
