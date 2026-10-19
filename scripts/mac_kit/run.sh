#!/bin/bash
# Item 96 / item 33 Q6 Mac kit, step 2: measure the processor, then Metal, and write REPORT.txt.
#   bash scripts/mac_kit/run.sh /path/to/phi3.5-mini-instruct-q4.gguf
# One Metal build, measured twice: on the processor (n_gpu_layers 0) and on Metal (every layer). Each runs in its own
# process (one model in memory at a time - this is an 8 GB Mac). About 30-60 minutes in
# all. Close other apps first: free memory is part of what's measured. Keep the Mac awake (plugged in).
set -e
KIT="$(cd "$(dirname "$0")" && pwd)"
MODEL="${1:?give the model file: bash scripts/mac_kit/run.sh /path/to/phi3.5-mini-instruct-q4.gguf}"
[ -f "$MODEL" ] || { echo "No file at $MODEL"; exit 1; }
[ -x "$KIT/venv-metal/bin/python" ] || { echo "Run setup.sh first (venv-metal missing)."; exit 1; }

WANT=b5374915da534cb93df39f03bd4f2cd5a0c533df0d5e21957dc9556c260be9eb
echo "Checking the model's fingerprint (about 10 s)..."
GOT="$(shasum -a 256 "$MODEL" | cut -d' ' -f1)"
[ "$GOT" = "$WANT" ] || { echo "Wrong model file: SHA-256 $GOT, expected $WANT"; exit 1; }

export GROUNDWORK_MODEL_PATH="$MODEL"
OUT="$KIT/results-$(date +%Y%m%d-%H%M)"
mkdir -p "$OUT"
caffeinate -i -w $$ &          # keep the Mac awake while this script runs
for mode in cpu metal; do
  echo; echo "=== $mode  $(date)"
  "$KIT/venv-metal/bin/python" -I "$KIT/mac_measure.py" "$mode" "$OUT/$mode.jsonl" 2>&1 | tee "$OUT/$mode.log" \
      | grep -v '^ggml_metal\|^llama_\|^load\|^print_info' || true
  tail -1 "$OUT/$mode.jsonl" 2>/dev/null | grep -q '"summary": true' \
      || { echo "The $mode run did not finish - see $OUT/$mode.log"; exit 1; }
done

{
  echo "Groundwork Mac engine measurement (item 96 / item 33 Q6) - $(date)"
  echo "Mac: $(sysctl -n machdep.cpu.brand_string), $(( $(sysctl -n hw.memsize) / 1073741824 )) GB, macOS $(sw_vers -productVersion)"
  echo "This report holds no financial data: the voice cases are made-up test figures."
  for mode in cpu metal; do
    echo; echo "[$mode]"
    head -1 "$OUT/$mode.jsonl" | "$KIT/venv-metal/bin/python" -c "import json,sys; h=json.load(sys.stdin); print('engine', h['llama_cpp'], '| gpu offload', h['gpu_offload'], '| libs', ' '.join(h['libs']))"
    tail -1 "$OUT/$mode.jsonl"
    "$KIT/venv-metal/bin/python" - "$OUT/$mode.jsonl" <<'PY'
import json, sys
for r in map(json.loads, open(sys.argv[1], encoding='utf-8')):
    if r.get('invented'):
        print(f"R8 seed {r['seed']} {r['case']}: {r['invented']}")
PY
  done
} > "$OUT/REPORT.txt"
echo; cat "$OUT/REPORT.txt"
echo; echo "Done. Send Claude the text above (it is also in $OUT/REPORT.txt); keep the folder - it has every answer."
