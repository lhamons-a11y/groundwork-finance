# GROUNDWORK_LLM_BUILD_PLAN.md
**Purpose:** the executable, sequenced build plan for the local-LLM era — derived from GROUNDWORK_LLM_BLUEPRINT.md. The blueprint is the spec and rationale; this is the order of operations, the per-task "definition of done," and the deploy discipline. Build top to bottom: each phase gates the next.
**Decisions it assumes (all LOCKED this session):** provider = local Ollama (cloud opt-in) · default model **phi3.5** (4B tier), **qwen2.5:7b** auto-upgrade (16GB+), **qwen2.5:3b** backup · voice = **data-historian sense** · first PDF issuer = **Capital One** · gas price = **EIA** · beta = **gate-first, then canary**.
> ⚠️ **PARTLY SUPERSEDED (2026-08-30) — read `gw 2.0/MODEL_PLACEMENT.md` before building Phase 2 or Phase 6.**
> The "provider = local Ollama" decision above is superseded by *local inference, provider **in-process***
> (embedded llama.cpp, no separate Ollama install, no second process) — driven by Microsoft/Apple store
> distribution, and it unlocks grammar-constrained decoding. Ollama remains the **development** runtime
> until the latency spike lands. **Phases 1, 3, 4, 5 are unaffected.** Phases 2A/2B and 6A/6B need rewriting.
> That note also records the decision *against* training a custom finance-specific LLM, and why.
>
> **`default model phi3.5` — CONFIRMED, keep it.** A repeated evaluation (5 runs × 6 cases ×
> 5 models, 143 calls, `llm_model_eval.py`) found phi3.5 is the **only sub-2.5GB model that never
> fabricated a figure** (R8 0/30, vs 8/30 for llama3.2:1b, 12/30 for llama3.2:3b, 3/30 for
> qwen2.5:3b). An earlier single-run signal suggesting smaller models were better was noise.
>
> **Two additions to Phase 1, both evidence-backed:**
> - **Streaming** (`stream=True`) cuts perceived latency **8.7x** (6.92s → 0.80s to first token) on
>   any model, because generation outruns reading 2.5x. Cheapest large win available; do it early.
> - **The gate is permanent, not scaffolding.** Every model tested smuggles inference (R3) 37–70%
>   of the time, and it got *worse* with size (qwen2.5:7b: 70%). No model upgrade removes the need
>   for retry-then-fallback; the fix is templating (blueprint B.2a), not a bigger model.

**Reference code already written:** `voice_discipline_test.py` holds the working rubric — R8 number-provenance, the hardened inference/causal wordlists, and the data-historian `GW_VOICE`. Phase 1 is largely *porting* this into `app.js`, not inventing it.

**Deploy discipline (applies to EVERY phase — non-negotiable):** three-place version bump (app.js / server.py / index.html cache-buster) · `smoke_test.py` green before ship · `SCHEMA_VERSION` gate on any DB change · `core/database.py` deploys to `C:\Groundwork\core\` (never root) · `deploy.bat` with rollback ready · Pamphlet Standard for any UI.

---

## Phase 0 — Baseline (DONE, this session)
Not work — the floor you're building from, so the plan starts from reality.
- ✅ `ai_chat()` is a provider router (local Ollama default / cloud opt-in); `_ai_chat_local`, `_resolve_local_model`, `_local_endpoint`, `GET /api/ai/status` shipped in `server.py`.
- ✅ Frontend contract unchanged — `callAI()` parses the same Anthropic shape from both providers.
- ✅ `voice_discipline_test.py` is a live, trustworthy harness (R8 + wordlists + data-historian prompt; empty-sentinel and qwen3 bugs fixed).
- ✅ Model chosen on evidence: phi3.5.

---

## Phase 1 — The Voice Gate  ⟵ THE FLOOR; blocks Phases 3+
**Why first:** raw phi3.5 still smuggles inference (R3) and would, unchecked, occasionally let a bad line through. Nothing goes to a tester on local until a fabricated number *cannot* reach the screen. This is build-seq steps 1–2, and it's mostly porting `voice_discipline_test.py` into the app.

| # | Task | Where | Done when |
|---|------|-------|-----------|
| 1A | Port the hardened voice prompt: data-historian framing + anti-self-narration line, **and add the omit-not-hedge instruction for R3** ("do not speculate about causes even hedged; omit what wasn't computed") | `app.js :: _GW_VOICE` | `_GW_VOICE` matches the harness `GW_VOICE`; a manual local run shows no "Groundwork…" self-narration |
| 1B | Port the rubric as a runtime check `_voiceGateCheck(text, findings)` — R1–R8 from `check()`. Share a **single canonical rule table** between harness and app so they never drift | `app.js` (new fn) | gate returns the same verdicts the harness does on the six trap-cases |
| 1C | Structural backstop = the guarantee: **R8 number-provenance** (reject any financial figure not in findings) + **causal-structure** check. Lean here, not on tone wordlists | inside `_voiceGateCheck` | fabricated `$1,500`/`$4,500` style lines are rejected deterministically |
| 1D | Retry-once-then-fallback at the single choke point: on gate fail, regenerate once (terser prompt); second fail → existing `_render*Fallback` (the honest floor) | `callAI()` / `_rcRenderAIPanel` | a forced-fabrication prompt never renders prose; it renders the evidence table instead |
| 1E | Miss-log: append every rejection (surface, model, rule, text) to a local file | `app.js` / small server route | rejections accumulate; readable for hardening |

**Phase gate (must all hold):** every narrative surface routes through `_voiceGateCheck`; a deliberately fabricating prompt renders the fallback, never the lie; harness and app share the rule table; runs green on `smoke_test.py`.

---

## Phase 2 — Provider UI + first-run trust surface
> ⚠️ **2A needs rewriting** — see `gw 2.0/MODEL_PLACEMENT.md`. With an in-process runtime there is no
> endpoint to probe and no installed-model list: `_local_endpoint`, `_resolve_local_model`,
> `/api/ai/status` and the `install-ollama` route collapse or disappear. **2B (RAM tiering) survives
> unchanged and matters more.** 2C's copy audit stands.

**Why here:** makes local mode coherent and installable before any tester touches it. Blueprint §4 + §11.1.

| # | Task | Where | Done when |
|---|------|-------|-----------|
| 2A | Settings → AI provider pane (Local / Cloud), fed by `/api/ai/status`: reachability, resolved model, installed list, **Test Connection** button, model picker (writes `local_model`), collapsed endpoint override | `index.html` + `app.js` Settings render | a tester can see "local reachable · phi3.5" and switch providers without editing settings by hand |
| 2B | **First-run RAM detection = the trust surface** (§11.1): read free RAM (psutil / Ollama's fit report), route 16GB+→offer qwen2.5:7b, 8–16GB→phi3.5 (~2.2GB), <8GB→cloud/structured. Plain-language, every tier a legitimate path, no spec-shaming | first-run flow | on each machine the setup honestly states what it can run, before anything else happens |
| 2C | Copy audit — provider-aware everywhere: `index.html:2371`, `app.js:19069/19075/19104/21666/22347`; privacy Q&A `app.js:10553` (advertise "nothing leaves the machine"); attribution "Analyzed on your machine · phi3.5" | those line refs | no "add your Anthropic key" text appears in local mode |

**Phase gate:** a tester with **no API key** enables local AI and gets gated narration; setup screen reports the machine's real capability; Pamphlet Standard met.

---

## Phase 3 — Beta cutover (canary → rollout)
Blueprint decision #4. Requires Phases 1–2.

| # | Task | Done when |
|---|------|-----------|
| 3A | Beta packaging = one-page setup (install Ollama, `ollama pull phi3.5`, app auto-detects) — Lane C. Not the open installer yet | 1–2 canary testers running local narration |
| 3B | Canary: cut **1–2 most-engaged testers** to local; watch the **miss-log** ~1 week; harden wordlists from real misses | a week of local narration with zero fabrication reaching a user (miss-log shows the gate catching, not the user seeing) |
| 3C | Roll to the remaining testers; **cloud key stays as per-tester escape hatch**; sub-8GB testers stay on cloud/structured | all willing testers on local; escape hatch intact |

**Phase gate:** miss-log demonstrates the gate is catching residual R3 in production; no fabricated figure observed in any tester's rendered output.

---

## Phase 4 — Capital One PDF extraction  ⟵ THE DEBT-GAP UNLOCK
Blueprint §6. Highest-leverage feature. Can begin in parallel with Phase 2 once Phase 1's R8 exists (it reuses R8 for extraction validation). Build **one issuer end-to-end**, then widen.

| # | Task | Where | Done when |
|---|------|-------|-----------|
| 4A | `pdfplumber` text extraction (layout→text only; never guesses meaning) | `server.py` new import path | Capital One statement → clean text |
| 4B | Strict-JSON extraction prompt + schema: `transactions[]` + `summary{newBalance, apr, minimumPayment, interestCharged, paymentReceived, statementPeriod}`; **null for any field not on the page, never guessed** | extraction fn | model returns valid JSON, nulls where absent |
| 4C | Confirm-before-commit UI (verdict confirmation, not chat): show extracted summary + txn count; user approves the **balance** especially | `app.js` | nothing commits without user confirmation |
| 4D | **Two-destination routing:** transactions → `bank_import_commit`; **summary → reconciliation** (`_calcDebtIntelligence` + `debt_balance_history` upsert on `UNIQUE(debt_id,month)`). *This is the point of the whole feature.* | `server.py` | verified balance/APR/min/interest land in the debt tables |
| 4E | Validation: R8-style number-provenance on every extracted figure (must appear in source text); **CSV × PDF cross-check** (PDF txns vs CSV txns; implied running balance vs extracted statement balance vs the account's known balance); SHA-256 cache to skip re-extraction | `server.py` | extracted balance matches the real balance to the cent |

**Phase gate (the money shot):** import a real Capital One PDF → the debt claim flips **insufficient → confirmed** in `_computeClaimConfidence`, the hero payoff projection **un-suppresses**, and the reconciliation gap closes. Then repeat for **Apple Card**. `SCHEMA_VERSION` bumped if `debt_balance_history` schema changes.

---

## Phase 5 — Trip planning + exogenous facts
Blueprint §7 + §8. After the gate (narration) and ideally after Phase 4 (document intake reuses the PDF pipeline).

| # | Task | Where | Done when |
|---|------|-------|-----------|
| 5A | EIA gas-price fetch (`api.eia.gov`, free key), server-side into the trip gas rate; **zero user-data egress** | `server.py` → `tripUpdateBudget` | trip fuel uses a real current national avg, not `3.40` |
| 5B | **Exogenous fuel-cost-into-budget (§8.5):** EIA price as a computed finding placed beside the user's fuel spend; monthly fuel budget becomes condition-aware. Ship the **side-by-side "good" version** (dollars only); decomposition is a later stretch (needs gallons) | engine + narration | "your fuel spend rose $X" appears beside "national avg rose Y%" — never a claim about the user's exact pump price |
| 5C | Learn-from-last-trip: cluster a past vacation's transactions (LLM labels, engine sums, user confirms) — reuses the travel-merchant classifier | `app.js` + `server.py` | a past trip pre-fills a new trip's per-category basis from real history |
| 5D | Document intake (paste a quote → extract via Phase 4 pipeline) + natural-language trip intake | reuse Phase 4 | a pasted VRBO/flight quote fills real numbers |
| 5E | Distance table (bundled) + remaining placeholder fixes | `server.py` | drive distance from a real lookup, not `400×2` |

**Deferred (decision #7, still open):** flights live-pricing API — needs the current-terms comparison (Amadeus/Duffel/Kiwi/SerpApi) before committing to the route/date egress. Not on the critical path.

**Phase gate:** a trip estimate reads its real inputs and honestly labels its confidence (Grounded / Partial / Rough shape).

---

## Phase 6 — Open-user packaging
> ⚠️ **6A/6B need rewriting** — see `gw 2.0/MODEL_PLACEMENT.md`. Both lanes were shaped around
> installing or bundling *Ollama*; the target is now an embedded runtime shipped inside the app, with
> the GGUF pulled on first run (weights are data, not executable code — permitted by Apple). This is
> also where the Microsoft/Apple store lanes actually become possible. 6C (signing) and 6D (smoke) stand.

Blueprint §5.2–5.4. Last, because it's the most work for the least *integrity* gain and iterates independently once the free path works.

| # | Task | Done when |
|---|------|-----------|
| 6A | Lane A (default): small installer; first-run downloads the RAM-appropriate model (phi3.5 ~2.2GB) with a progress bar | fresh machine installs, detects RAM, pulls phi3.5, works offline after |
| 6B | Lane B (alt): offline bundle (app + Ollama + model) — **only after phi3.5's license is cleared for redistribution** | offline installer verified on a no-internet machine |
| 6C | Per-platform (Win11 / macOS / Ubuntu 24.04) + **installer code-signing** (bundled binary + multi-GB model trips SmartScreen/AV) | signed installers per platform |
| 6D | New `smoke_test.py` checks: provider valid; `/api/ai/status` 200; local mode resolves a model or the no-model UX is reachable (never a silent dead AI feature) | smoke_test covers the AI path |

---

## Critical path (the spine)
**Phase 1 (gate) → Phase 2 (UI) → Phase 3 (canary)** is the trunk — everything user-facing waits on the gate. **Phase 4 (Capital One PDF)** is the highest-value branch and can start once Phase 1's R8 exists; it's the feature that closes the debt gap, so prioritize it right behind the gate. **Phases 5–6** follow. The one truly-deferred item is the flights API (decision #7).

Suggested order if building solo: **1 → 4 → 2 → 3 → 5 → 6** (gate first for safety, then the debt-gap unlock while it's fresh, then the UI/cutover that ships both, then trips, then open packaging). Or **1 → 2 → 3** first if getting testers onto free local narration matters more to you than PDF.

## First move
Phase 1, task **1A/1B**: open `app.js`, and port `_GW_VOICE` + `_voiceGateCheck` from `voice_discipline_test.py`. You have a locked model to build against and working reference code for the hard part (R8 + wordlists). Everything else stands on that.
