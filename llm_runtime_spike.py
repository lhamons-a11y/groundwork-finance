#!/usr/bin/env python3
"""
GROUNDWORK LLM RUNTIME SPIKE
============================
Purpose: measure whether an IN-PROCESS inference runtime (llama.cpp) can replace
the Ollama dependency, without changing what reaches the user.

Why this file exists: `gw 2.0/MODEL_PLACEMENT.md` decides to embed the runtime —
no separate Ollama install, no second process — because store distribution
(Microsoft, Apple) cannot depend on separately-installed software. That decision
rests on measurements, and one of them is still missing: **the low-RAM tier.**
Everything measured so far was taken on 14 cores / 34GB, which is not the target
machine. Run this on an 8GB box before Phase 2B's RAM tiering is finalised.

WHAT IT MEASURES
----------------
  1. cold load          — startup cost we own instead of a resident daemon
  2. COLD vs WARM call  — first narration of a session vs every one after
  3. gate pass + R8     — does in-process behave like Ollama did?
  4. GBNF grammar       — can the sampler emit a figure that isn't in findings?

The A/B against Ollama is the point. Latency alone proves nothing; what matters
is whether swapping the runtime changes the OUTPUT. Run both engines.

THREE MEASUREMENT TRAPS — all three produced wrong numbers before being caught.
Do not re-introduce them:

  * R6 IS UNSCORED. `check()` returns passed=None for R6 — an explicit
    "HEURISTIC: human check" placeholder (voice_discipline_test.py:192).
    Counting `not None` as a failure reports 0/6 when the real rate is 2/6.
  * RECORD THE TOKEN COUNT. A call that takes longer may simply have generated
    more. A "warm call slower than cold" turned out to be 273 tokens vs 113.
  * CONTROL THE PROMPT-PREFIX CACHE. GW_VOICE is identical on every call, so the
    first call pays full prefill and the rest reuse it — worth ~1.7x here. A
    sweep that loaded 8 models in one process, and a warmup that used a trivial
    8-token prompt, both measured cache state instead of the variable.

  And the general lesson, learned the expensive way: when two measurements of the
  same thing disagree, the disagreement is the finding. Do not average them.

USAGE
-----
    # Ollama side only (no extra deps):
    python llm_runtime_spike.py --engine ollama

    # in-process side (needs the runtime):
    pip install llama-cpp-python --extra-index-url \
        https://abetlen.github.io/llama-cpp-python/whl/cpu
    python llm_runtime_spike.py --engine both --grammar

Model weights: reuses the GGUF the store installer already stages at
vendor/phi3.5_model/blobs/ — an Ollama model layer IS a GGUF, so llama.cpp
opens it directly and nothing needs downloading.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import voice_discipline_test as H  # real GW_VOICE, real CASES, real check()

BLOB_DIR = HERE / "vendor" / "phi3.5_model" / "blobs"
OLLAMA_MODEL = "phi3.5"


def find_model():
    """The Ollama model layer is the largest blob, and it is a GGUF."""
    if not BLOB_DIR.is_dir():
        return None
    blobs = sorted(BLOB_DIR.glob("sha256-*"), key=lambda p: p.stat().st_size, reverse=True)
    return blobs[0] if blobs else None


def score(text, case):
    """Score with check(), EXCLUDING rules the rubric leaves unscored (passed=None)."""
    v = H.check(text, case)
    scored = {r: x for r, x in v.items() if x[0] is not None}
    failed = [r for r, (p, _n) in scored.items() if not p]
    r8 = v.get("R8_number_provenance")
    return {"failed": failed, "pass": not failed,
            "r8_pass": (r8[0] if r8 else None), "r8_note": (r8[1] if r8 else "")}


def unload_ollama():
    """Drop Ollama's resident model so its first call is genuinely cold."""
    import urllib.request
    try:
        body = json.dumps({"model": OLLAMA_MODEL, "keep_alive": 0}).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate",
                                     data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req, timeout=20).read()
        time.sleep(3)
        return True
    except Exception:
        return False


def machine():
    import platform
    info = {"python": sys.version.split()[0], "platform": platform.platform()}
    try:
        import psutil
        info["ram_total_gb"] = round(psutil.virtual_memory().total / 1e9, 1)
        info["ram_avail_gb"] = round(psutil.virtual_memory().available / 1e9, 1)
        info["cores_physical"] = psutil.cpu_count(logical=False)
        info["cores_logical"] = psutil.cpu_count(logical=True)
    except Exception:
        pass
    return info


def run_llamacpp(model_path, n_threads=None):
    from llama_cpp import Llama
    kw = {"model_path": str(model_path), "n_ctx": 2048, "verbose": False}
    if n_threads:
        kw["n_threads"] = n_threads
    t0 = time.perf_counter()
    llm = Llama(**kw)
    load_s = time.perf_counter() - t0

    rows = []
    for i, case in enumerate(H.CASES):
        t0 = time.perf_counter()
        out = llm.create_chat_completion(
            messages=[{"role": "system", "content": H.SYSTEM_PROMPT},
                      {"role": "user", "content": case.findings}],
            temperature=0.3, max_tokens=300)
        dt = time.perf_counter() - t0
        text = (out["choices"][0]["message"]["content"] or "").strip()
        tok = (out.get("usage") or {}).get("completion_tokens") or 0
        rows.append({"case": case.name, "i": i, "s": round(dt, 2), "tok": tok,
                     "tps": round(tok / dt, 2) if dt else 0,
                     "text": text, **score(text, case)})
    return {"engine": "llama.cpp", "cold_load_s": round(load_s, 2), "rows": rows,
            "_llm": llm}


def run_ollama():
    rows = []
    for i, case in enumerate(H.CASES):
        t0 = time.perf_counter()
        text = H.run_model(OLLAMA_MODEL, H.SYSTEM_PROMPT, case.findings)
        dt = time.perf_counter() - t0
        if text is None:
            rows.append({"case": case.name, "i": i, "unreachable": True})
            continue
        text = text.strip()
        rows.append({"case": case.name, "i": i, "s": round(dt, 2),
                     "tok": None, "tps": None, "text": text, **score(text, case)})
    return {"engine": "ollama", "rows": rows}


def grammar_test(llm):
    """Can the sampler emit a dollar figure that is NOT in the findings?

    NOTE what this does and does not prove. A grammar guarantees PROVENANCE, not
    CORRECTNESS: it cannot stop a true number being placed in a false relation
    (observed: '$17 daily ... is approximately $2,400', arithmetic nonsense from
    two real figures). It narrows the voice gate's job; it never replaces it.
    """
    from llama_cpp import LlamaGrammar
    case = H.CASES[0]
    allowed = sorted(H._financial_numbers(case.findings))
    if not allowed:
        return {"supported": False, "error": "no figures in findings"}
    # Render each allowed figure both bare and thousands-grouped.
    lits = set()
    for a in allowed:
        lits.add(a)
        if a.isdigit() and len(a) > 3:
            lits.add(f"{int(a):,}")
    alts = " | ".join(f'"{x}"' for x in sorted(lits))
    gbnf = ('root ::= chunk+\n'
            'chunk ::= money | prose\n'
            f'money ::= "$" ({alts})\n'
            'prose ::= [^$]+\n')
    try:
        grammar = LlamaGrammar.from_string(gbnf, verbose=False)
        adversarial = case.findings + "\n\nState the total projected interest cost in dollars."
        t0 = time.perf_counter()
        out = llm.create_chat_completion(
            messages=[{"role": "system", "content": H.SYSTEM_PROMPT},
                      {"role": "user", "content": adversarial}],
            temperature=0.3, max_tokens=200, grammar=grammar)
        dt = time.perf_counter() - t0
        text = (out["choices"][0]["message"]["content"] or "").strip()
        emitted = H._financial_numbers(text)
        fabricated = sorted(n for n in emitted if n not in set(allowed))
        return {"supported": True, "latency_s": round(dt, 2), "allowed": allowed,
                "emitted": sorted(emitted), "fabricated": fabricated,
                "held": not fabricated, "text": text}
    except Exception as e:
        return {"supported": False, "error": f"{type(e).__name__}: {e}"}


def summarise(res):
    rows = [r for r in res["rows"] if not r.get("unreachable")]
    if not rows:
        return {"engine": res["engine"], "reachable": False}
    cold, warm = rows[0], rows[1:]
    lat = [r["s"] for r in warm]
    out = {"engine": res["engine"], "reachable": True,
           "cold_call_s": cold["s"],
           "warm_median_s": round(statistics.median(lat), 2) if lat else None,
           "warm_max_s": round(max(lat), 2) if lat else None,
           "gate_pass": f"{sum(1 for r in rows if r['pass'])}/{len(rows)}",
           "r8_pass": f"{sum(1 for r in rows if r['r8_pass'])}/{len(rows)}",
           "failed_rule_counts": {
               rule: sum(1 for r in rows if rule in r["failed"])
               for rule in sorted({x for r in rows for x in r["failed"]})}}
    tps = [r["tps"] for r in warm if r.get("tps")]
    if tps:
        out["warm_median_tok_per_s"] = round(statistics.median(tps), 1)
        out["cold_tok_per_s"] = cold.get("tps")
    if res.get("cold_load_s") is not None:
        out["cold_load_s"] = res["cold_load_s"]
    return out


def report(res):
    print(f"\n── {res['engine']} ──────────────────────────────")
    if res.get("cold_load_s") is not None:
        print(f"cold load {res['cold_load_s']}s")
    for r in res["rows"]:
        if r.get("unreachable"):
            print(f"  [SKIP] {r['case']:<28} unreachable / model not pulled")
            continue
        tag = "COLD" if r["i"] == 0 else "warm"
        tokpart = f"{r['tok']:>4} tok {r['tps']:6.2f} tok/s " if r.get("tok") else " " * 21
        rules = ",".join(x.split("_")[0] for x in r["failed"]) or "-"
        print(f"  [{tag}] {r['case']:<28} {r['s']:6.2f}s {tokpart}"
              f"{'PASS' if r['pass'] else 'FAIL'} R8={'ok' if r['r8_pass'] else 'VIOLATED'} {rules}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=["llamacpp", "ollama", "both"], default="both")
    ap.add_argument("--grammar", action="store_true", help="run the GBNF constraint test")
    ap.add_argument("--threads", type=int, default=None,
                    help="llama.cpp n_threads (default: library default; a sweep on "
                         "14 cores found NO signal above run-to-run noise)")
    args = ap.parse_args()

    info = machine()
    print("MACHINE:", json.dumps(info, indent=2))
    if info.get("ram_total_gb", 99) <= 9:
        print("\n>>> LOW-RAM TIER — this is the measurement MODEL_PLACEMENT.md is "
              "missing. Record these numbers in that note's Measured section. <<<")

    out = {"machine": info}
    want_lc = args.engine in ("llamacpp", "both")
    want_ol = args.engine in ("ollama", "both")

    if want_ol:
        print(f"\nOllama unload: {'ok' if unload_ollama() else 'skipped (not running?)'}")

    if want_lc:
        model = find_model()
        if not model:
            print(f"\nFATAL: no GGUF blob under {BLOB_DIR}")
            return 1
        print(f"\nMODEL: {model.name[:24]}... ({model.stat().st_size / 1e9:.2f} GB)")
        try:
            lc = run_llamacpp(model, args.threads)
        except ImportError:
            print("\nllama-cpp-python not installed — skipping in-process engine.\n"
                  "  pip install llama-cpp-python --extra-index-url "
                  "https://abetlen.github.io/llama-cpp-python/whl/cpu")
            lc = None
        if lc:
            report(lc)
            if args.grammar:
                g = grammar_test(lc["_llm"])
                out["grammar"] = g
                print("\nGRAMMAR TEST — figure fabrication at the sampler:")
                if g.get("supported"):
                    print(f"  emitted    {g['emitted']}")
                    print(f"  fabricated {g['fabricated'] or 'NONE — constraint held'}")
                    print("  NOTE: provenance only. A grammar cannot stop a true number "
                          "being put in a false relation.")
                else:
                    print(f"  unsupported: {g.get('error')}")
            lc.pop("_llm", None)
            out["llama_cpp"] = lc

    if want_ol:
        ol = run_ollama()
        report(ol)
        out["ollama"] = ol

    summary = {k: summarise(out[k]) for k in ("llama_cpp", "ollama") if k in out}
    out["summary"] = summary
    print("\n" + "=" * 62)
    print(json.dumps(summary, indent=2))

    a, b = summary.get("llama_cpp"), summary.get("ollama")
    if a and b and a.get("reachable") and b.get("reachable"):
        print(f"\nCOLD  llama.cpp {a['cold_call_s']}s   vs  ollama {b['cold_call_s']}s")
        print(f"WARM  llama.cpp {a['warm_median_s']}s   vs  ollama {b['warm_median_s']}s")
        print(f"GATE  llama.cpp {a['gate_pass']}      vs  ollama {b['gate_pass']}")
        print(f"R8    llama.cpp {a['r8_pass']}      vs  ollama {b['r8_pass']}")
        print("\nThe R8 row is the one that licenses the swap: equal R8 means the "
              "runtime change does not alter what reaches the user.")

    p = HERE / "llm_runtime_spike_results.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nfull results -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
