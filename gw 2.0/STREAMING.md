# Streaming narration — item 10, measured before anything is built

**Prompt size and wait time per AI surface, captured from the running app and replayed against the shipped local model**

> Status: **Measured 2026-09-19/20 against `master` at `076056c`. Nothing is built or proposed here.**
>
> Item 10 opened on a decided-not-built finding: `MODEL_PLACEMENT.md` / Appendix H settled *narration
> is streamed* (perceived wait 6.92 s → 0.80 s), and no line streams — `server.py:6734` sends
> `'stream': False`, `app.js` has no reader. Rob's first step for the pass: *measure prompt size per
> surface*, because streaming fixes only the generation half of a wait and prompt evaluation is the
> other half. This document is that measurement. It answers which half dominates, on what hardware,
> and records what else the measurement turned up.

---

## 1. Method — captured, not reconstructed

- **The app, not a model of it.** `dev_server.py` (the real `server.py` on a throwaway DB), seeded
  with a representative household: 692 transactions over 12 months across 12 categories and two
  accounts, 12 budget lines, two debts, a past trip window. EULA accepted; onboarding **skipped**
  (this matters — §4 T5).
- **Every `/api/ai/chat` payload the page built was captured** at `API.post` in the browser, with
  the local provider selected. Nine surfaces, 21 captures, 14 unique prompts (the report card's two
  retry variants and the auto-fired duplicates are distinct captures).
- Three surfaces needed help to fire: `sunday_checkin` (shows only on Sundays — one render with
  `getDay()` returning 0), `projection` (hidden while balances are unverified — invoked directly
  with a representative `projData`), and the legacy `monthly_report` (§4 T8 — its target element no
  longer exists; supplied one to capture the prompt).
- **Timing from Ollama itself, not a stopwatch.** Each unique prompt replayed to
  `localhost:11434/api/chat` with the server's exact options (`temperature 0.3`, `num_predict` = the
  surface's `max_tokens` or the server's 1000 default, `keep_alive 30m`, no stream) and Ollama's
  `prompt_eval_count` / `prompt_eval_duration` / `eval_count` / `eval_duration` read back. One
  five-token warm-up call first so model load is measured once, separately.
- **One live run left as the app ran it** — the first report card, end to end, no short-circuit —
  because the replay cannot show what the gate's retry loop does to a user (§4 T3).

**Hardware, because every number below depends on it:** i7-12800H (14 cores), 32 GB, **NVIDIA RTX
A1000 4 GB**. `ollama ps` reported the model split **33 % CPU / 67 % GPU**. This is *not* the 8 GB
CPU-only tier the narrator evidence left unmeasured; §5 says what that changes.

---

## 2. The surfaces — what each prompt is made of

All sizes in characters as captured. *Voice* is `_GW_VOICE` from `static/voice_rules.json`, appended
by `callAI` to every gated surface — a fixed **1,846 chars (~460 tokens)**. *Own* is the surface's
own system text. *User* is the findings / data message.

| Surface | Reached from | Voice | Own | User | Total | `max_tokens` | Gate |
|---|---|---|---|---|---|---|---|
| `distance_traveled` (report card) | Reports → card; local auto-fires | 1,846 | 336 | 2,469 | 4,651 | 350 | gated |
| `income_savings` (report card) | same | 1,846 | 336 | 2,182 | 4,364 | 350 | gated |
| `category_*` (report card) | same | 1,846 | 336 | 1,901 | 4,083 | 350 | gated |
| `annual_*` (report card) | same | 1,846 | 336 | 2,588 | 4,770 | 350 | gated |
| `*_followup` | question box under a card | 1,846 | 128 | 191 | 2,165 | 200 | gated |
| `monthly_report_v2` | Reports → Monthly; **local auto-fires on open and on every month change** | 1,846 | 127 | 617 | 2,590 | **none → 1000** | gated |
| `projection` | dashboard card | 1,846 | 62 | 612 | 2,520 | 140 | gated |
| `sunday_checkin` | dashboard, Sundays | 1,846 | 115 | 878 | 2,839 | 100 | gated |
| `monthly_report` (legacy) | **unreachable** (§4 T8) | 1,846 | 195 | 2,774 | 4,815 | 250 | gated |
| `trip_learn_classify` | Trip Planner → Analyze that trip | 0 | 150 | 1,750 (15 txns) | 1,900 | 200 + 40/txn | skip |
| `trip_quote_extract` | Trip Planner → Read it | 0 | 159 | 1,248 | 1,407 | 400 | skip |
| `generateTripBudget` | Trip Planner → Generate | 0 | 97 | 1,713 | 1,810 | 800 | skip |

Two facts about composition before any timing:

- **The voice block is 40–70 % of every gated prompt that is not a report card.** On `projection`
  (62 chars of its own) the surface is 2 % of what the model reads; the rules are 73 %.
- **A retry does not shorten the prompt; it lengthens it.** The gate's corrective retry appends
  508 chars (a second retry 596) listing the flagged phrases, and re-sends the whole prompt.

---

## 3. The timing — `phi3.5` (the ruled default), warm, this hardware

| Surface | Prompt tok | Prompt eval s | Output tok | Generation s | Total s | Hit cap? |
|---|---|---|---|---|---|---|
| `distance_traveled` — **first call of the session** | 1,244 | **11.01** | 313 | 12.37 | **23.4** | |
| `distance_traveled` retry 1 | 1,392 | 0.95 | 283 | 11.61 | 12.8 | |
| `distance_traveled` retry 2 | 1,426 | 0.86 | 232 | 10.52 | 11.7 | |
| `income_savings` | 1,296 | 0.98 | 249 | 13.49 | 15.1 | |
| `monthly_report_v2` | 697 | 0.77 | 346 | 16.57 | 17.6 | (no cap) |
| `category_*` | 1,137 | 0.41 | **350** | 18.17 | 18.9 | **yes, mid-sentence** |
| `annual_*` | 1,468 | 0.84 | 254 | 14.70 | 15.6 | |
| `projection` | 654 | 0.83 | 54 | 1.74 | **2.8** | |
| `sunday_checkin` | 746 | 0.75 | 79 | 2.71 | 3.6 | |
| `*_followup` | 583 | 0.72 | 80 | 2.53 | 3.4 | |
| `monthly_report` (legacy) | 1,266 | 1.25 | 250 | 13.81 | 15.3 | yes |
| `trip_learn_classify` (15 txns) | 994 | 0.97 | **507** | **27.11** | **28.3** | |
| `trip_quote_extract` | 507 | 0.59 | 120 | 5.19 | 6.0 | |
| `generateTripBudget` | 583 | 0.73 | 429 | 21.46 | 22.4 | |
| *`distance_traveled` on `qwen3:4b`* | 1,079 | 0.91 | 350 | 15.00 | 16.0 | yes — all of it thinking (T5) |

**Cold costs, measured once each:** model load 13.2 s (`phi3.5`), 9.1 s (`qwen3:4b`). The first
real prompt of the session then paid 11.0 s of prompt evaluation that no later prompt paid
(§4 T4). So **the first narration after launch, or after 30 idle minutes (`keep_alive`), is ~35 s
before the first token exists** — and nothing is on screen for any of it.

**Generation rate:** 20–27 tokens/s on every surface. **Warm prompt evaluation:** 0.4–1.3 s for
500–1,500 tokens.

---

## 4. Findings

Numbered T so they do not collide with the S-series in `SAFETY_PROVISIONS_INVENTORY.md`.

### T1 — on this hardware, generation is 75–95 % of every wait; streaming is the lever

Warm, the prompt half is ~1 s on every surface and the generation half is 2–27 s. Streaming would
bring the *felt* wait down to roughly the prompt-eval column: a report card from ~15 s to ~1 s, the
trip classifier from 28 s to 1 s. Prompt *size* barely moves the warm numbers here — `annual_*` at
1,468 tokens evaluated in 0.84 s. **The half the ruling picked is the half that matters, on a GPU.**

### T2 — the first call is different, and it is the one a user judges

The 11.0 s first-call evaluation plus 13 s model load is the session's opening experience. Streaming
does not touch either. What does: keeping the model resident (`keep_alive` is already 30 m), and a
warm-up on launch — not measured, not proposed, named because T1's "~1 s" is not what a user sees
first.

### T3 — the gate's retry loop multiplies the wait, and the app's live run ended in nothing

Left to run as shipped, the first report card took **71 s + 49 s + 45 s = 165 s** — three full
generations in series, every one rejected by the voice gate, then the honest fallback ("Written
analysis unavailable"). The user waits two and three-quarter minutes to be told there is no
analysis. `callAI`'s loop is two corrective retries — three attempts — before the fallback; the
third generation is that loop, not the report-card path.

On `phi3.5` in replay the same three prompts cost 23 + 13 + 12 = 48 s; the live run was slower
because it ran on `qwen3:4b` (T5) — but the shape is the model-independent finding: **the wait is
not one generation, it is N generations, N decided by the gate after each one completes.** Streaming
makes each attempt visible; it does nothing about N. This is where item 10's stated constraint
(the gate reads the complete response) becomes a cost, not just a design tension.

### T4 — prefix caching is real, large, and accidental

Retry 1 was *longer* than the first call (1,392 vs 1,244 tokens) and evaluated in 0.95 s instead of
11.0 s: Ollama reused the KV cache for the identical prefix and evaluated only the ~250 new tokens.
`income_savings` — a different card — got the same benefit (0.98 s) because two report cards share
their first 2,183 characters (card system + voice block).

But `callAI` assembles the system as `payload.system + _GW_VOICE`: **the one block every gated
surface shares is placed after the part that differs.** The cache therefore helps within a family
(report cards) and not across surfaces. Voice-first ordering would make the 460-token block a
universal prefix, paid once per session. Recorded as a measured fact; not changed.

### T5 — the model behind the voice was not the ruled one, and it burned every budget thinking

With onboarding skipped, `_resolve_local_model` (`server.py:6654`) chose **`qwen3:4b`** — its
auto-detect order is `qwen → llama → phi → mistral → gemma`; the ruled default (*phi3.5 stays*,
2026-08-30) is third. Onboarding *pins* `local_model` (mid tier → `phi3.5`), so a normal install
avoids this — but the **high tier pins `qwen2.5:7b`**, the size class the narrator evidence measured
at 70 % inference-smuggling. Both are decided-not-built in exactly the way streaming is.

And `qwen3:4b` failed every attempt the same way: the `think: False` + `/no_think` belt-and-braces
at `server.py:6725` did not take. All 350 tokens were reasoning ("Okay, the user wants me to act as
Groundwork's financial analysis engine…"), the `<think>` block never closed, the strip regex found
nothing, and the gate — correctly — rejected prose about writing a report. Replay reproduced it
exactly. **This is `SAFETY_PROVISIONS_INVENTORY.md` S12 observed live:** the attribution line said
"Analyzed on your machine · qwen3:4b" and the voice contract was open.

### T6 — `monthly_report_v2` has no output cap and auto-fires on every month switch

It sends no `max_tokens`, so the server's default of 1,000 applies (it generated 346 here, 16.6 s,
and stopped on its own — it could run three times longer). For local users it fires on view and on
each month change with no click; opening the report modal and changing the month once produced
**three** captures. Each is a full generation the user did not ask for.

### T7 — three surfaces are output-bound by their own shape

- `category_*` hit its 350-token cap **mid-sentence** (18 s to produce a truncated answer).
- `trip_learn_classify` spent 507 tokens (27 s) on `{"id": "689", "bucket": "Other"}` boilerplate —
  its budget grows 40 tokens per transaction, so a 40-transaction trip is a ~60 s call.
- `generateTripBudget` spent 429 tokens (22 s), and its output opens `"cost": 120, "note":
  "Estimated fuel cost … assuming an average"` — S2 (the search that never ran) and S10 (the
  assumption persisted as the plan) observed together in one line.

### T8 — the legacy `monthly_report` surface is unreachable, and wrong if reached

`generateReport()` writes to `#reportAiNarrative`, which is not in `static/index.html`; the
`Report` button now runs `monthly_report_v2`. Supplied the element, it read an empty month selector
and spent 15 s narrating *"income remained consistent at $0.00, and your spending was also $0.00"*.
Dead code that would fabricate a report if resurrected. Nine surfaces declared; eight live.

### T9 — incidental, outside item 10, recorded so it is not lost

The follow-up surface sends only the prior assistant bubble and the question — no findings — and
its answer read `$1,078.32` (the amount *paid down* on the Harbor Visa) as the *remaining balance*,
then advised focusing on it. R5 catches the advice; **nothing catches a figure that is in the
findings but attached to the wrong noun.** R8 checks presence, not meaning. Not a streaming finding;
a gate-coverage one. Belongs with item 8's inventory when that record is next opened, not here.

---

## 5. What this says about the two halves — and what it cannot say

Rob's framing: streaming fixes generation, only a smaller prompt fixes prompt evaluation. Measured on
this machine: **generation dominates by an order of magnitude once warm**, so streaming is the lever
and prompt size is not — *with a 4 GB GPU taking two-thirds of the model.*

What this measurement cannot say: the CPU-only number. The narrator evidence left the 8 GB tier
unmeasured (`llm_runtime_spike.py` prints a banner on a low-RAM box; paging, not tok/s, is the
cliff there). On CPU alone, prompt evaluation slows far more than generation does, the 11 s
first-call figure becomes the every-call figure, and the prompt-size lever returns. The 460-token
voice block and the voice-after-surface ordering (T4) are the things that would then matter most,
and both are measured here already. **Measure the CPU-only tier before deciding the order of work;
do not extrapolate from a GPU box.**

---

## 6. The constraint, restated with a number on it

*A fabricating model never reaches the screen* is true today because nothing is shown until the gate
has read the whole response. Streaming shows tokens before the gate can. T3 puts the cost on both
sides: without streaming, the user waits N × (full generation) in silence; with naive streaming,
the user reads an answer the gate is about to reject. The three shapes named in the queue row —
gate-then-reveal (keeps the silence), sentence-level gating, a change to the gate's contract — are
still the three, and choosing is Rob's ruling. One measured input for that ruling: on this hardware
a full report-card generation is 11–18 s and the retry rate on the shipped model was 3 of 3.

---

## 7. What has not been done

- Nothing built. No `stream: True`, no reader, no reordering of the system prompt, no cap on
  `monthly_report_v2`, no change to the resolver's preference order, no removal of the legacy
  surface, no warm-up on launch.
- The CPU-only tier is unmeasured (§5). The cloud path is unmeasured (its latency is Anthropic's,
  its per-call preview is S3's).
- T5, T8 and T9 are findings for other records (item 8 / a 1.x correctness pass), placed here
  because this measurement produced them.
- The captured prompts and replay results are in the session scratchpad, not the repo; the method
  above reproduces them from a fresh `dev_server.py` seed in under an hour.
