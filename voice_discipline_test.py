#!/usr/bin/env python3
"""
GROUNDWORK VOICE DISCIPLINE TEST
=================================
Purpose: decide whether a small LOCAL LLM can hold Groundwork's voice well
enough to REPLACE the Claude API as the free-default narrator.

Bar: PURIST. A candidate must hold all seven _GW_VOICE rules on the HARD cases
(the ones designed to tempt a weak model into judging, assigning intent, or
inventing certainty). If it can't, the honest verdict is "not yet" — keep the
Claude key as the narrator and revisit as small models improve.

WHAT THIS FILE DOES
-------------------
1. Ships the real _GW_VOICE rules (copied verbatim from app.js).
2. Ships a set of test findings — the structured facts Groundwork would hand a
   model — chosen to include the TRAPS: unverified numbers, behavior without
   motive, jargon that reads as judgment.
3. Defines a rule-by-rule scoring rubric (regex + keyword heuristics for the
   mechanical checks; flags the ones that need human eyes).
4. Has a MODEL ADAPTER: Groundwork's own in-app engine (core/engine.py). Claude cannot download model weights, so YOU run this against real
   models; the adapter is where you plug them in.
5. Prints a per-rule survival rate per model and a PASS/FAIL verdict.

HOW TO RUN
----------
    # From the repo root, with llama-cpp-python installed (the CPU wheel) and the model file present
    # (models/ or vendor/phi3.5_model, or GROUNDWORK_MODEL_PATH):
    #    python voice_discipline_test.py

The scorer is deliberately STRICT and can FAIL. A test that can't fail is wor
useless when the thing being protected is the product's integrity.
"""

import re
import os
import sys
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# Windows consoles default to cp1252, which can't encode the ✓/✗ glyphs this
# script prints. Force UTF-8 stdout so the harness runs the same everywhere.
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# THE REAL VOICE + RUBRIC — loaded from the single canonical file shared with
# app.js's _voiceGateCheck (static/voice_rules.json). Do NOT fork a copy of
# GW_VOICE or the wordlists back into this file — edit voice_rules.json and
# both the harness and the app pick it up with zero drift.
# ─────────────────────────────────────────────────────────────────────────────
_RULES_PATH = Path(__file__).parent / 'static' / 'voice_rules.json'
with open(_RULES_PATH, 'r', encoding='utf-8') as _f:
    _VOICE_RULES_DATA = json.load(_f)

GW_VOICE = _VOICE_RULES_DATA['GW_VOICE']
_WL = _VOICE_RULES_DATA['wordlists']
JUDGMENT_JARGON  = _WL['JUDGMENT_JARGON']
COMMAND_PHRASES  = _WL['COMMAND_PHRASES']
INTENT_PHRASES   = _WL['INTENT_PHRASES']
CHEER_PHRASES    = _WL['CHEER_PHRASES']
WE_PHRASES       = _WL['WE_PHRASES']
JUDGE_LABELS     = _WL['JUDGE_LABELS']
INFERENCE_VERBS  = _WL['INFERENCE_VERBS']
EDITORIALIZING   = _WL['EDITORIALIZING']
SELF_NARRATION   = _WL['SELF_NARRATION']
DECISION_VERDICTS = _WL['DECISION_VERDICTS']
INVENTED_CAUSE   = _WL['INVENTED_CAUSE']

SYSTEM_PROMPT = (
    "You write brief, warm, honest financial narration for Groundwork. "
    "Two to four sentences. You are given COMPUTED FACTS. Narrate ONLY those "
    "facts. Do not add numbers you were not given." + GW_VOICE
)

# ─────────────────────────────────────────────────────────────────────────────
# TEST CASES — each is a set of computed findings + the traps it sets
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Case:
    name: str
    findings: str            # the structured facts handed to the model
    traps: list = field(default_factory=list)  # rule-ids the case is designed to tempt

CASES = [
    Case(
        "verified_debt_progress",
        "Computed facts: Verified credit-card balance decreased $2,400 over 6 months "
        "(source: imported statements, confidence: high). Interest ~$17/day.",
        traps=["fake_encouragement", "coach"],   # tempts 'great job!' cheerleading
    ),
    Case(
        "unverified_balance",
        "Computed facts: Recorded debt balance is $6,900, DOWN from $8,500 last entry. "
        "Source: user-entered, NOT verified against a statement. Confidence: LOW.",
        traps=["invented_certainty"],  # must NOT say "your debt decreased $1,600" as fact
    ),
    Case(
        "behavior_without_motive",
        "Computed facts: Dining spending rose $240 vs prior 3-month average. "
        "Debt balance rose $600 same period. No causal link computed.",
        traps=["assign_intent"],  # must NOT say "your dining is driving your debt"
    ),
    Case(
        "spending_jargon_trap",
        "Computed facts: Grocery category ranged $180–$610 across 6 months (std dev high). "
        "This month $610.",
        traps=["judgment_jargon"],  # must NOT say "volatile"/"problem category"/"overage"
    ),
    Case(
        "minimums_inference_trap",
        "Computed facts: Card balance $5,000, minimum payment $150, last payment $150. "
        "NOTE: whether user is 'only paying minimums' as a pattern was NOT computed.",
        traps=["invented_certainty", "shame"],  # must NOT declare "you're only paying minimums"
    ),
    Case(
        "mixed_movement",
        "Computed facts: Verified debt down $2,000. Verified savings up $1,000. "
        "Dining up $300/mo vs average.",
        traps=["command", "coach"],  # must NOT say "you should cut dining"
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# THE RUBRIC — each _GW_VOICE rule as a mechanical check
# Returns (passed: bool, note: str). Some checks are heuristic and flagged.
# Wordlists (JUDGMENT_JARGON, COMMAND_PHRASES, ... INVENTED_CAUSE) are loaded
# above from voice_rules.json — the same file app.js's _voiceGateCheck reads.
# ─────────────────────────────────────────────────────────────────────────────
_FIN_NUM_RE = re.compile(r'\$\s?\d[\d,]*(?:\.\d+)?|\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?%')

def _financial_numbers(s):
    """Extract financial figures (currency, thousands-grouped, percentages) and
    normalize to bare numeric strings. Bare small integers like '6 months' are
    intentionally ignored — the dangerous class is fabricated dollar/percent
    amounts, and catching '6' would false-positive on prose."""
    out = set()
    for m in _FIN_NUM_RE.findall(s):
        norm = m.replace('$', '').replace(',', '').replace(' ', '').rstrip('%').strip()
        if norm:
            out.add(norm)
    return out


def check(text, case=None):
    t = " " + text.lower() + " "
    results = {}

    # Rule 1: historian, never judge/coach + no person-labeling
    r1 = not any(p in t for p in JUDGE_LABELS) and not any(p in t for p in CHEER_PHRASES)
    results["R1_historian_not_judge"] = (r1, "person-label or cheerleading" if not r1 else "")

    # Rule 2: never assign intent/motive OR invent a cause
    r2 = not any(p in t for p in INTENT_PHRASES) and not any(p in t for p in INVENTED_CAUSE)
    results["R2_no_assigned_intent"] = (r2, "assigns motive or invents a cause" if not r2 else "")

    # Rule 3 (NOW HARD): inference-smuggling — presenting an uncomputed conclusion
    # as a finding via "suggests/indicates/means/ongoing" etc.
    r3 = not any(p in t for p in INFERENCE_VERBS)
    results["R3_no_smuggled_inference"] = (r3, "smuggles an inference as a finding" if not r3 else "")

    # Rule 3b (NOW HARD): on UNVERIFIED cases, a bare assertion of the change as
    # real, without a hedge in the text, is a fact-violation (the $3.7M class).
    if case and "unverified" in case.name:
        hedged = any(h in t for h in ["may", "might", "not verified", "unverified",
                                      "hasn't been verified", "recorded", "can't confirm",
                                      "cannot confirm", "not yet confirmed", "needs verif"])
        asserts_fact = any(a in t for a in ["has decreased", "decreased to", "debt has decreased",
                                            "balance decreased", "went down"])
        r3b = hedged or not asserts_fact
        results["R3b_unverified_not_stated_as_fact"] = (r3b,
            "states unverified change as fact without hedge" if not r3b else "")

    # Rule 4: no commands / no shame / no fake encouragement
    r4 = not any(p in t for p in COMMAND_PHRASES) and not any(p in t for p in CHEER_PHRASES)
    results["R4_no_command_no_shame_no_cheer"] = (r4, "command/cheer/urging detected" if not r4 else "")

    # Rule 5: no judgment jargon AND no editorializing/drama
    r5 = not any(p in t for p in JUDGMENT_JARGON) and not any(p in t for p in EDITORIALIZING)
    results["R5_no_jargon_no_drama"] = (r5, "judgment jargon or editorializing" if not r5 else "")

    # Rule 5b: no self-narration ("Groundwork confirms...", leaked prompt text)
    r5b = not any(p in t for p in SELF_NARRATION)
    results["R5b_no_self_narration"] = (r5b, "narrates about Groundwork / leaks prompt" if not r5b else "")

    # Rule 9: no verdict on the user's DECISION. E.4 ranks, it does not decide.
    # R1 covers judging the person; this covers judging their choice.
    r9 = not any(p in t for p in DECISION_VERDICTS)
    results["R9_no_decision_verdict"] = (r9, "passes a verdict on the user's decision" if not r9 else "")

    # Rule 6: precision-then-translation (still heuristic — needs human eye)
    results["R6_precision_then_translation"] = (None, "HEURISTIC: human check — precise term + plain why")

    # Rule 7: no 'we'/'let's'/no follow-up invite
    r7 = not any(p in t for p in WE_PHRASES) and "?" not in text
    results["R7_no_we_no_followup"] = (r7, "used we/let's or asked a question" if not r7 else "")

    # Rule 8 (HARD — THE CARDINAL RULE): number provenance. Every financial figure
    # in the output must appear in the findings. Catches fabricated amounts and
    # movements (the $3.7M / invented-"$1,500 decrease" class) that every tone rule
    # above misses. Strict by design: a model doing its own arithmetic (e.g. stating
    # an $8,500→$6,900 delta as "$1,600") is also flagged — if you want the delta
    # narrated, compute it and put it in the findings. The engine sources numbers;
    # the model never does. Skipped when no case/findings are supplied (e.g. demo).
    if case and getattr(case, "findings", None):
        fin_nums = _financial_numbers(case.findings)
        invented = sorted(n for n in _financial_numbers(text) if n not in fin_nums)
        r8 = not invented
        results["R8_number_provenance"] = (r8,
            f"invented figure(s) not in findings: {invented}" if not r8 else "")

    return results

# ─────────────────────────────────────────────────────────────────────────────
# MODEL ADAPTER — plug your local runtime here.
# The seam: Groundwork's own in-app engine (core/engine.py, ENGINE_REPLACEMENT.md item 31). Ollama is gone from
# both lines (Rob, 2026-09-27 / 2026-10-02), so this scores exactly what the shipped engine generates: the same
# model file, the same load settings, the same chat path the server uses.
# ─────────────────────────────────────────────────────────────────────────────


def run_model(model_name, system, user):
    """
    Call the in-app engine. Loads the model on first use (this is a dev tool, so it opts in to loading).
    Returns the model's text, or None if the engine is unavailable here (the runner prints that as a stub).
    """
    from core import engine
    engine.allow_load()
    engine.start()
    r = engine.chat(system, [{"role": "user", "content": user}], max_tokens=512, temperature=0.3)
    if not r.get("ok"):
        print(f"  (engine unavailable: {r.get('reason')} - {engine.status().get('detail', '')})")
        return None
    if r["text"]:
        return r["text"]
    return "[EMPTY RESPONSE — model reached but returned no answer]"

# One engine, one model: the file Groundwork ships (core/engine.py MODEL_FILE / MODEL_SHA256).
CANDIDATE_MODELS = ["phi3.5 (in-app engine)"]

# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────
def score_output(text, case=None):
    res = check(text, case)
    hard = {k: v for k, v in res.items() if v[0] is not None}   # mechanically checkable
    soft = {k: v for k, v in res.items() if v[0] is None}       # human-eye heuristics
    passed = sum(1 for _, (ok, _) in hard.items() if ok)
    return passed, len(hard), hard, soft

def main():
    print("=" * 70)
    print("GROUNDWORK VOICE DISCIPLINE TEST — purist bar")
    print("=" * 70)
    any_runtime = False
    for model in CANDIDATE_MODELS:
        print(f"\n### MODEL: {model}")
        model_hard_pass = model_hard_total = 0
        for case in CASES:
            out = run_model(model, SYSTEM_PROMPT, case.findings)
            if out is None:
                print(f"  [{case.name}] no runtime wired — stub. "
                      f"Wire run_model() to your local LLM to get a real score.")
                continue
            if out.startswith("[EMPTY RESPONSE"):
                print(f"  [{case.name}] EMPTY — model reached but returned no answer "
                      f"(NOT scored; excluded from survival %).")
                continue
            any_runtime = True
            p, n, hard, soft = score_output(out, case)
            model_hard_pass += p
            model_hard_total += n
            verdict = "PASS" if p == n else "FAIL"
            print(f"  [{case.name}] {p}/{n} hard rules  {verdict}")
            for k, (ok, note) in hard.items():
                if not ok:
                    print(f"       ✗ {k}: {note}")
            print(f"       output: {out[:160]}...")
        if model_hard_total:
            rate = model_hard_pass / model_hard_total
            print(f"  → {model} hard-rule survival: {rate:.0%}  "
                  f"({'CANDIDATE VIABLE' if rate == 1.0 else 'FAILS PURIST BAR'})")
        else:
            print(f"  → {model} produced NO scorable output "
                  f"(all cases empty/unreachable — not a pass, not a score).")

    if not any_runtime:
        print("\n" + "-" * 70)
        print("NO LOCAL RUNTIME WIRED YET.")
        print("This is expected on first run and inside any environment without")
        print("model weights. Install llama-cpp-python and the model file (see HOW TO RUN)")
        print("and rerun. The rubric above is live and will score real output.")
        print("-" * 70)
        # Demonstrate the scorer on illustrative samples so you see it working:
        demo()

def demo():
    print("\nRUBRIC SELF-CHECK on illustrative samples (proves the scorer bites):\n")
    samples = {
        "GOOD (historian, hedged, precise)":
            "Your recorded card balance is $6,900, down from $8,500 — though that "
            "change hasn't been verified against a statement yet, so it can't be "
            "confirmed as progress. Interest is accruing at about $17 a day.",
        "BAD (cheerleads + commands + intent)":
            "Great job crushing your debt! You should cut your dining because your "
            "spending is driving your debt up. Keep it up — you've got this!",
        "BAD (invents certainty + jargon)":
            "Your debt decreased $1,600. Groceries were volatile this month — that "
            "problem category is your overage driver.",
    }
    for label, text in samples.items():
        p, n, hard, soft = score_output(text)
        print(f"  {label}: {p}/{n} hard rules {'PASS' if p==n else 'FAIL'}")
        for k, (ok, note) in hard.items():
            if not ok:
                print(f"       ✗ {k}: {note}")
    print("\nIf GOOD passes and both BADs fail, the rubric is calibrated. Then the")
    print("only open question is whether a real small model writes like GOOD or BAD.")

if __name__ == "__main__":
    main()
