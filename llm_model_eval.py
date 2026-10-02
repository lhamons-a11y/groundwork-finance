#!/usr/bin/env python3
"""
GROUNDWORK MODEL EVALUATION
===========================
Which local model should narrate? Decided on repeated measurement, not one run.

Why this exists: a single pass (n=6, one run per model) suggested smaller models
hold Groundwork's voice BETTER than the locked default phi3.5 — qwen2.5:3b at
4/6 against phi3.5's 2/6, while being smaller and ~2x faster. That is a strong
claim against a locked decision, and single-run evidence is exactly what
produced three wrong conclusions during the runtime spike. So: repeat it.

WHAT IT MEASURES, per model
  * gate pass rate across REPEATED runs, with the spread shown
  * R8 violations — the cardinal metric. A model that fabricates a figure is
    disqualified regardless of how well it scores on tone.
  * per-rule failure rates — WHERE a model fails, not just how often
  * throughput (completion tokens over the call's wall time, so prefill is INCLUDED - unlike the Ollama-era
    eval counters this file once read; compare like with like)
  * output length — because of the hypothesis below

THE HYPOTHESIS UNDER TEST
  Smaller models scored better because they are TERSER, and the voice rules
  reward terseness: rambling is what trips R3 (smuggled inference), R4
  (commands/cheer) and R5 (jargon/drama). If true, output length should predict
  gate failure ACROSS models, not just between them. That is testable here and
  is reported as "terseness hypothesis".

READ THE SPREAD, NOT THE MEAN. If a model's per-run pass rate swings widely,
its mean is not a ranking — it is a distribution, and the runs are the evidence.

USAGE
    python llm_model_eval.py                 # default models, 5 runs
    python llm_model_eval.py --runs 3
    python llm_model_eval.py --models phi3.5 qwen2.5:3b
Runs on Groundwork's own in-app engine (core/engine.py, ENGINE_REPLACEMENT.md): the shipped model file, the
shipped load settings. Ollama is gone from both lines, so the multi-model comparison this file was built for is
historical; it now measures the one model Groundwork ships, a different seed per call so repeated runs are
independent samples. Needs llama-cpp-python (the CPU wheel) and the model file.
"""
import argparse
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import voice_discipline_test as H  # real GW_VOICE, real CASES, real check()

ENGINE_MODEL = "phi3.5 (in-app engine)"
DEFAULT_MODELS = [ENGINE_MODEL]
_SEED = [0]

# Minimum sample per group before the terseness verdict means anything. The
# recorded finding pooled 143 calls; a 6-call run once printed "SUPPORTED,
# 1.46x" off three data points, which is the same failure as scoring silence
# as a pass - a number presented as a finding when the sample cannot carry it.
MIN_TERSENESS_N = 30


def model_sizes():
    from core import engine
    p = engine.model_path()
    return {ENGINE_MODEL: p.stat().st_size / 1e9} if p.exists() else {}


def size_of(name, sizes):
    return sizes.get(name) or sizes.get(f"{name}:latest") or 0.0


def unload(model):
    """The engine owns its lifecycle; it is released when this process ends."""


def chat(model, system, user):
    """One call on the in-app engine, returned in the shape eval_model() reads."""
    from core import engine
    engine.allow_load()
    engine.start()
    engine._ready.wait(120)
    if engine._model is None:
        raise RuntimeError(engine.status().get("message") or "engine unavailable")
    _SEED[0] += 1
    t = time.time()
    with engine._lock:
        out = engine._model.create_chat_completion(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=300, temperature=0.3, seed=_SEED[0])
    return {"message": {"content": out["choices"][0]["message"]["content"]},
            "eval_count": (out.get("usage") or {}).get("completion_tokens") or 0,
            "eval_duration": int((time.time() - t) * 1e9)}


def score(text, case):
    """check(), excluding rules the rubric leaves unscored (R6 returns None)."""
    v = H.check(text, case)
    scored = {r: x for r, x in v.items() if x[0] is not None}
    failed = [r for r, (p, _n) in scored.items() if not p]
    r8 = v.get("R8_number_provenance")
    return failed, (not failed), (r8[0] if r8 else None), (r8[1] if r8 else "")


def eval_model(model, runs, sizes):
    gb = size_of(model, sizes)
    print(f"\n── {model}  ({gb:.2f} GB) · {runs} runs x {len(H.CASES)} cases")
    per_run_pass, rule_fails = [], Counter()
    empty_calls = 0
    r8_violations, samples = [], []
    tps_all, tok_all = [], []

    for run in range(runs):
        passed_this_run = 0
        for case in H.CASES:
            try:
                res = chat(model, H.SYSTEM_PROMPT, case.findings)
            except Exception as e:
                print(f"    call failed ({type(e).__name__}) — skipping")
                continue
            text = (res.get("message") or {}).get("content", "").strip()
            n_tok = res.get("eval_count") or 0
            dur = res.get("eval_duration") or 0
            # An empty response violates no rule, so check() returns clean and
            # the call would score as a PASS. That is how q2_K once came back
            # 97% pass / 0% failure on every rule with 27 of 30 calls returning
            # nothing at all - a silent model looked like the best model in the
            # set. Silence is not voice discipline. Record it, never score it.
            if not text:
                empty_calls += 1
                samples.append({"run": run, "case": case.name, "tokens": n_tok,
                                "pass": False, "empty": True, "failed": []})
                continue

            if dur:
                tps_all.append(n_tok / (dur / 1e9))
            tok_all.append(n_tok)

            failed, ok, r8, r8note = score(text, case)
            passed_this_run += bool(ok)
            for f in failed:
                rule_fails[f] += 1
            if r8 is False:
                r8_violations.append({"run": run, "case": case.name,
                                      "note": r8note, "text": text})
            samples.append({"run": run, "case": case.name, "tokens": n_tok,
                            "pass": ok, "empty": False, "failed": failed})
        per_run_pass.append(passed_this_run)
        print(f"    run {run + 1}: {passed_this_run}/{len(H.CASES)}")

    total = len(samples)
    scored = total - empty_calls
    unload(model)
    return {
        "model": model, "gb": round(gb, 2), "runs": runs, "n": total,
        "per_run_pass": per_run_pass,
        "empty_calls": empty_calls,
        "scored": scored,
        "pass_rate": round(sum(per_run_pass) / scored, 3) if scored else 0,
        "pass_spread": f"{min(per_run_pass)}-{max(per_run_pass)}/{len(H.CASES)}" if per_run_pass else "-",
        "r8_violations": len(r8_violations),
        "r8_examples": r8_violations[:3],
        "median_tok_per_s": round(statistics.median(tps_all), 1) if tps_all else 0,
        "median_output_tokens": round(statistics.median(tok_all)) if tok_all else 0,
        "rule_fail_rate": {r: round(c / scored, 3) for r, c in rule_fails.most_common()} if scored else {},
        "samples": samples,
    }


def terseness_test(all_results):
    """Does output LENGTH predict gate failure, pooled across every model?"""
    pas, fail = [], []
    for r in all_results:
        for s in r["samples"]:
            if s.get("empty"):
                continue      # unscoreable; pooling these flipped this verdict once
            (pas if s["pass"] else fail).append(s["tokens"])
    if not pas or not fail:
        return None
    mp, mf = statistics.median(pas), statistics.median(fail)
    return {"n_pass": len(pas), "n_fail": len(fail),
            "median_tokens_when_passing": mp,
            "median_tokens_when_failing": mf,
            "ratio": round(mf / mp, 2) if mp else None,
            "underpowered": len(pas) < MIN_TERSENESS_N or len(fail) < MIN_TERSENESS_N,
            "min_n": MIN_TERSENESS_N,
            "supported": None if (len(pas) < MIN_TERSENESS_N or len(fail) < MIN_TERSENESS_N)
                         else mf > mp * 1.2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    args = ap.parse_args()

    sizes = model_sizes()
    if not sizes:
        print("the in-app engine's model file was not found (models/ or vendor/phi3.5_model, or GROUNDWORK_MODEL_PATH)")
        return 1
    models = [m for m in args.models if size_of(m, sizes)]
    missing = [m for m in args.models if not size_of(m, sizes)]
    if missing:
        print(f"not pulled, skipping: {', '.join(missing)}")

    t0 = time.time()
    results = [eval_model(m, args.runs, sizes) for m in models]

    print("\n" + "=" * 78)
    print(f"{'model':<34}{'GB':>6}{'tok/s':>8}{'out tok':>9}{'empty':>7}"
          f"{'pass':>8}{'spread':>9}{'R8 viol':>9}")
    for r in sorted(results, key=lambda x: (-x['pass_rate'], x['gb'])):
        flags = []
        if r['r8_violations']:
            flags.append('R8')
        if r.get('empty_calls'):
            flags.append('EMPTY')
        flag = ('  <-- ' + '+'.join(flags)) if flags else ''
        # pass% is over SCORED calls, so a mostly-silent model can read 100%.
        # The empty column is what stops that being taken at face value.
        print(f"{r['model']:<34}{r['gb']:>6.2f}{r['median_tok_per_s']:>8.1f}"
              f"{r['median_output_tokens']:>9}{r.get('empty_calls', 0):>7}"
              f"{r['pass_rate']:>8.0%}{r['pass_spread']:>9}"
              f"{r['r8_violations']:>9}{flag}")

    print("\nPER-RULE FAILURE RATE (share of calls failing that rule)")
    rules = sorted({k for r in results for k in r["rule_fail_rate"]})
    print(f"{'model':<16}" + "".join(f"{r.split('_')[0]:>7}" for r in rules))
    for r in results:
        print(f"{r['model']:<16}" +
              "".join(f"{r['rule_fail_rate'].get(x, 0):>7.0%}" for x in rules))

    th = terseness_test(results)
    if th:
        print(f"\nTERSENESS HYPOTHESIS (pooled, n={th['n_pass'] + th['n_fail']})")
        print(f"  median output when PASSING: {th['median_tokens_when_passing']} tokens")
        print(f"  median output when FAILING: {th['median_tokens_when_failing']} tokens "
              f"({th['ratio']}x)")
        if th["supported"] is None:
            print("  => NOT JUDGED - need >= %d per group, have %d passing / %d failing"
                  % (th["min_n"], th["n_pass"], th["n_fail"]))
        elif th["supported"]:
            print("  => SUPPORTED — longer output fails more")
        else:
            print("  => NOT SUPPORTED — length does not predict failure")

    # R8 is disqualifying; among the clean, rank by pass rate then size.
    clean = [r for r in results
             if not r["r8_violations"] and not r.get("empty_calls")]
    dirty = [r for r in results if r["r8_violations"]]
    print("\nRECOMMENDATION")
    for r in results:
        if r.get("empty_calls"):
            print("  returned NOTHING on %d/%d calls: %s - scored on %d only"                  % (r["empty_calls"], r["n"], r["model"], r["scored"]))
    if dirty:
        print("  disqualified on R8 (fabricated a figure): " +
              ", ".join(f"{r['model']} x{r['r8_violations']}" for r in dirty))
    if clean:
        best = sorted(clean, key=lambda x: (-x["pass_rate"], x["gb"]))[0]
        print(f"  best R8-clean: {best['model']} — {best['pass_rate']:.0%} gate pass "
              f"(spread {best['pass_spread']}), {best['gb']}GB, "
              f"{best['median_tok_per_s']} tok/s")
        print("  NOTE: read the spread. A wide spread means the mean is not a ranking.")
    else:
        print('  no candidate: every model either fabricated a figure '
              'or returned nothing. The gate is doing the work.')

    out = {"generated": time.strftime("%Y-%m-%d %H:%M"), "runs": args.runs,
           "engine": ENGINE_MODEL, "terseness": th,
           "results": [{k: v for k, v in r.items() if k != "samples"} for r in results],
           "samples": {r["model"]: r["samples"] for r in results}}
    p = HERE / "llm_model_eval_results.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nelapsed {time.time() - t0:.0f}s   ->  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
