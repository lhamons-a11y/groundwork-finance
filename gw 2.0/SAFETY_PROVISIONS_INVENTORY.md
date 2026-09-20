# Safety provisions — measured inventory, per release line

**What actually stops Groundwork from acting, sending, or reaching beyond the machine — on 1.0, LTS, and 2.0, as the code stands**

> Status: **Measured 2026-09-17. Nothing is proposed here.** S9 folded and S10–S12 appended
> 2026-09-19 on Rob's ruling (§8); the second axis — where the model's words become a record,
> and whose text reaches the model — measured then.
>
> Rob's framing, 2026-09-17: *"we are doing web searching with Travel and we never programmed
> the agent to go to the bank."* This document tests both halves of that sentence against each
> line and records what it finds. It distinguishes, for every provision, whether it holds **by
> design** (there is code whose job is to stop the thing) or **by absence** (nothing stops it;
> nothing happens to do it). The distinction matters because a provision by absence survives
> only until the next feature, and 2.0 is a next feature.
>
> `HEALTH_TRUST_BOUNDARY.md` §3 measured the same code for one invariant (health data). This
> document measures it for the general question and does not repeat what §3 already lists;
> it points there.

---

## 1. The three lines, and what "per line" turns out to mean

| Line | Ref | Commit | Date |
|---|---|---|---|
| 1.0 (shipped) | tag `v1.1.0` | `7494e20` | 2026-08-28 |
| LTS | branch `lts/1.x` | `a80b2ee` | 2026-09-06 |
| 2.0 | branch `master` | `04c0447` | 2026-09-17 |

*(No `v1.0` tag exists; `v1.1.0` is the shipped 1.x release and is what "1.0" means here.)*

**Measured first, because it collapses the work:** `server.py`, `launch.py`, `bank_importer.py`,
`gas_price.py`, `flight_price.py`, `trip_distance.py`, `utility_price.py` and `price_engine.py`
are **byte-identical between `lts/1.x` and `master`**. The whole diff between those two lines is
`core/*` additions (the 2.0 substrate — `classification.py`, `database.py`, `plan_year.py`,
`payment_plan.py`, `person.py`, `allocation.py`, `reserve.py`) and 210 lines of
`static/js/app.js`. None of the `core/` additions open a connection.

So there are **two** distinct egress surfaces to inventory, not three: `v1.1.0`, and
`lts/1.x`≡`master`. Where the LTS and 2.0 lines differ at all, it is in `app.js`, and §5 records
the one difference that is a provision.

**What ships.** `groundwork.spec` bundles `launch.py`, `static/`, `core/`, `bank_importer.py`
and the five lookup modules. `llm_model_eval.py`, `llm_runtime_spike.py` and
`voice_discipline_test.py` are developer tools and are not in the bundle; `Website/website.py`
is the marketing site, a separate deployable (its one outbound call is SendGrid, for the
mailing list). All four are excluded below.

---

## 2. What is being inventoried

Four things, because those are the four ways software can act beyond the record the user
handed it:

- **A. Outbound network** — every call site, what triggers it, what leaves.
- **B. The model's reach** — whether the model can take an action (tools), what gates a send,
  what the user is shown, where the credential lives.
- **C. Replication outside the database** — where data sits that is not the ledger.
- **D. The local HTTP surface** — who can talk to the server on the machine.

---

## 3. Inventory — `v1.1.0` (shipped 1.x, `7494e20`)

### A. Outbound network — 16 `urlopen` sites in bundled code

**Off-machine by default (9 sites, 7 hosts):**

| Site | Host | Trigger | What leaves |
|---|---|---|---|
| `server.py:127` `update_check` | `groundworkfinance.app/version.json` | app start / periodic (6 h cache) | `User-Agent: Groundwork`. No version, no id. |
| `server.py:5370` `_ai_chat_cloud` | `api.anthropic.com/v1/messages` | any AI surface, **only when `ai_provider == 'cloud'`** | the `system` + `messages` the surface built — see B |
| `server.py:5623` `_download_with_progress` | `ollama.com/download/…` | explicit "Install Ollama" click | nothing; downloads an installer |
| `gas_price.py:63` | `api.eia.gov` | Travel: trip gas price | EIA key, fixed facets (`EPMR`, `NUS`) |
| `utility_price.py:61,82` | `api.eia.gov` | Utilities benchmark | EIA key, two-letter state code |
| `trip_distance.py:72` | `nominatim.openstreetmap.org` | Travel: distance | the city name typed, once per place (cached forever after) |
| `flight_price.py:163` | `serpapi.com` | Travel: flight lookup | SerpApi key, airport codes, dates, traveller count |
| `price_engine.py:70` | `query1.finance.yahoo.com` | Investments | ticker symbol |

**Loopback by default (7 sites):** `server.py:5239,5317,5473,5534` (Ollama tags / chat /
status / pull — all against `_local_endpoint()`), `server.py:5696` (fixed
`DEFAULT_OLLAMA_ENDPOINT`), `launch.py:60,162` (waits for and posts to the app's own port).

**Every site opens its own `urllib.request`.** No shared egress function (F1 of
`HEALTH_TRUST_BOUNDARY.md`, restated here because it is the general finding, not a health one).

### B. The model's reach

| Question | Measured answer | By design / by absence |
|---|---|---|
| Can the model call a tool? | **No.** `_ai_chat_cloud` builds the provider payload from exactly four keys — `model`, `max_tokens`, `messages`, `system`. `_ai_chat_local` likewise. No `tool_use` handling exists anywhere in `server.py`, `app.js` or `core/`. | **Absence.** Nothing strips or refuses a tool; the payload builder simply never copies one. |
| Is a tool ever *requested*? | **Yes, once.** `app.js:11046` `generateTripBudget` sends `tools: [{type:'web_search_20250305'}]` and a prompt that opens *"Use web search to find current prices."* The server drops the key. The model receives an instruction it cannot follow. | — (see S2) |
| Which provider by default? | `local`. `cloud` only if the `ai_provider` setting is literally `'cloud'`. `ai_enabled` defaults **on**. | Design |
| Whose credential? | The user's own, via `_get_config_value`: env var → `config.json` in DATA_DIR → beside `server.py` → home. **Never the database, never echoed back** (`save_api_key` returns only a flag). Same convention for EIA and SerpApi keys. No bundled key exists. | Design |
| Preview before a cloud send? | **On one surface of nine.** `_rcSendAI` (report cards) renders *"Here's what Groundwork will send to Anthropic's API…"* and waits for a click. The other eight — `monthly_report`, `sunday_checkin`, `monthly_report_v2`, `_rcFollowUp`, `projection`, `trip_learn_classify`, `trip_quote_extract`, `generateTripBudget` — send on their own trigger. Four of them render a **post-hoc** "View what was sent to AI" disclosure. | Design, on one surface. Absence on eight. |
| Server-side sends with no UI at all? | **One.** `server.py:1740` PDF statement import → `_ai_complete_text` → the condensed statement text, whichever provider is active. | Absence |
| Does transaction text ever leave? | **Yes, on two surfaces, when cloud is selected.** `trip_learn_classify` sends `id\|date\|description[:60]\|category` for every transaction in the trip's range. PDF import sends statement text. | Absence |
| Fail-closed declaration of what a surface passes? | **Does not exist on this line.** `callAI` has the voice gate (fabrication check on the *response*); nothing checks the *request*. | Absence |
| "Loopback-only" local AI? | **A default, not a structure.** `local_endpoint` is an ordinary `AppSetting`, writable via `PATCH /api/settings`. Pointed elsewhere, the path still returns `provider: 'local'` and the footer still reads *"Analyzed on your machine"*. | Absence |

### C. Replication outside the database

Identical to `HEALTH_TRUST_BOUNDARY.md` §3 "Persistence and replication" — `groundwork.log`
(rotating, INFO, tracebacks with `request.path`), `/api/debug/log-tail` (last 60 lines over
HTTP), `voice_miss_log.jsonl` (the narrator's generated sentences, verbatim, up to 2000 chars),
file export, backup create/restore/upload/list, and the beta bug-report builder whose
`mailto:` body is not the panel labelled "Report preview" (F2 there). All present on this line.

### D. The local HTTP surface

| Fact | Measured |
|---|---|
| Bind | `127.0.0.1:8765` (`server.serve`, `launch.py`). Never `0.0.0.0`. |
| Auth | `@app.before_request _check_session_token` rejects any `/api/*` request without the session token. Exempt: `/api/health`, `/api/ping`. **Design.** |
| What the token guards | Everything below it — including `PATCH /api/settings` (any key, including `ai_provider` and `local_endpoint`), `POST /api/settings/api-key`, backup restore/upload, and `/api/debug/log-tail`. |
| Executes downloaded code? | `_run_install_ollama` downloads `OllamaSetup.exe` over HTTPS from `ollama.com` and runs it `/VERYSILENT`. **No hash, no signature check.** Explicit click only. |
| Update download | Manifest's `url` is discarded unless it starts with `https://groundworkfinance.app/` (`server.py:133`). **Design.** |

---

## 4. Inventory — `lts/1.x` (`a80b2ee`)

`server.py`, `launch.py` and every lookup module are byte-identical to `master`; the line
numbers below are shared with §5. Against `v1.1.0` this line carries +1579 lines of `server.py`
(the Solution Engine, cycles, proactive, trophies) and +797 of `app.js`. **None of it adds an
outbound site or a tool.**

### A. Outbound network — 16 sites, same 7 hosts

Off-machine by default: `server.py:129` update-check, `:6809` `_ai_chat_cloud`, `:7062`
Ollama download; `gas_price.py:63`; `utility_price.py:61,82`; `trip_distance.py:72`;
`flight_price.py:163`; `price_engine.py:70`. Same triggers and payloads as §3.A.

Loopback by default: `server.py:6678,6756,6912,6973` (against `_local_endpoint()`),
`server.py:7135` (fixed), `launch.py:123,231`.

### B. The model's reach — as §3.B, every row

Tool request still made and still dropped (`app.js` `generateTripBudget`, server payload keys
unchanged at `server.py:6790–6797`). Preview on one surface of nine. PDF path at
`server.py:3098`. No request-side declaration gate. `local_endpoint` still a setting.

### C, D — as §3.C and §3.D, every row

Token guard present. Installer executed unverified. Update URL prefix-checked.

---

## 5. Inventory — `master` (2.0 line, `04c0447`)

### A. Outbound network — identical to §4.A

`core/classification.py`, `core/database.py`, `core/plan_year.py`, `core/payment_plan.py`,
`core/person.py`, `core/allocation.py`, `core/reserve.py` — the whole 2.0 substrate — contain
**no network code**. Verified by grep for `urlopen`, `requests.`, `http.client`, `socket`.
The Assistant's aboutness / independence / level-consistency functions are pure reads on a
session.

### B. The model's reach — §4.B plus one provision that exists only here

**The request-side declaration gate** (`app.js:22419` `_findingsKindsRefusal`, called from
`callAI`): a call that does not declare `findings_kinds`, or declares any of `description`,
`memo`, `transaction_text`, `free_text`, `notes`, `merchant_text`, **does not run** and the
caller falls to its honest fallback. **Design.** This is the only line where the request is
checked before the model sees it.

**Its reach, measured:** 6 of 9 surfaces pass through it (`monthly_report`, `sunday_checkin`,
`monthly_report_v2`, `projection`, and the two report-card paths via `_reportFindingsKinds`).
**3 opt out with `skipGate: true`** — `trip_learn_classify`, `trip_quote_extract`,
`generateTripBudget` — and one of those (`trip_learn_classify`) sends exactly the prohibited
class. The server-side PDF path never reaches `callAI` at all.

Everything else in §3.B holds unchanged on this line.

### C, D — as §3

---

## 6. Findings

Numbered S so they do not collide with `HEALTH_TRUST_BOUNDARY.md`'s F-series.

**Three failure classes, kept apart (Rob, 2026-09-19).** *Capability by absence* — S1: the model cannot act because there is no tool or action path. *Crossing into durable state* — S10: model output can become application state without provenance or review. *Untrusted text entering the model* — S11: third-party text already crosses into the model, its blast radius bounded today by S1. S9 says what currently contains the system; S1–S8 and S10–S12 say where it crosses, or where containment is weaker than its representation suggests. S10 is not evidence that the Assistant architecture is unsafe; it is evidence that one existing surface already crosses without the controls the 2.0 doctrine would require. Do not collapse these into one notion of "safety".

### S1 — "we never programmed the agent to go to the bank" is true, and it is true by absence

On every line the provider payload is built from four keys and no `tool_use` block is ever
parsed. The model cannot act because nothing gives it a way to — not because anything would
stop it. There is no allowlist of zero, no assertion, no test that would fail if a fifth key
were copied. `bank_importer.py` has no network code at all; it reads files the user hands it.

This is a sound provision for `v1.1.0` and `lts/1.x`, where nothing is being added. It is not a
provision for `master`, where `ASSISTANT_SCOPE.md` §"Changing things on the user's behalf" is
already settled doctrine about the software acting. The moment the Assistant gains any tool,
S1 stops being true and nothing records that it was ever relied upon.

### S2 — Travel does not web-search; it asks a model to pretend it did

`generateTripBudget` (every line) sends a `web_search_20250305` tool declaration, a system
prompt *"Always search for real current prices"*, and a user prompt opening *"Use web search to
find current prices."* The server never forwards `tools`. The disclosure panel then tells the
user *"This request could search the web for current prices."*

So the sentence "we are doing web searching with Travel" is false in the direction that matters:
the **deterministic** lookups (EIA gas, Nominatim distance, SerpApi flights) are real, keyed,
and carry only reference parameters — and they are not the model. The **model** call in Travel
performs no search, receives an instruction it cannot honour, and its prices are generated. The
one Travel surface that says it searches is the one that cannot; the three that can are not
searches by the model. This is `EXTERNAL_ACTION_CASES.md` E11 in code form — *told where to
look ≠ resolved* — turned on the software itself.

Separately: the same prompt carries `Total trip budget available` and `Monthly surplus after
debt` as dollar figures, with no preview, under `skipGate`.

### S3 — the preview-before-send gate covers one surface; the copy claims all of them

Settings copy, cloud provider selected: *"You'll see exactly what's being shared before it's
sent."* Measured: one of nine surfaces shows anything before sending (`_rcSendAI`); four show it
afterwards; four show nothing; the PDF path has no UI. Same shape as F2 — a claim about
behaviour that one code path honours, made on behalf of all of them.

### S4 — "your raw transactions stay on your computer" has two exceptions, on every line

With `ai_provider == 'cloud'`:

- `trip_learn_classify` sends `id|date|description[:60]|category` for every transaction in the
  trip's date range. On `master` this bypasses the declaration gate via `skipGate`; on the other
  two lines there is no gate to bypass.
- PDF statement import sends `condense_for_prompt(statement_text)` — page-filtered, not
  redacted. `pdf_statement.py` contains no account-number masking; the condense step drops
  pages with few figures, which is the opposite of dropping the sensitive ones.

Both are honest features doing what they say on the tin. What is wrong is only the sentence
beside them.

### S5 — the one request-side provision is `master`-only and opt-out

`_findingsKindsRefusal` exists on `master` and nowhere else. `v1.1.0` and `lts/1.x` check the
model's *answer* (voice gate) and never its *question*. On `master`, three of nine surfaces opt
out — and all three are the Travel surfaces. A provision that a caller can switch off with one Boolean, and that the shipped lines lack
entirely, is a provision on the line where it is least needed.

### S6 — "local" is a setting, not a boundary

`local_endpoint` is an `AppSetting`. `PATCH /api/settings` writes any key. With the session
token, the "Analyzed on your machine" path can be pointed at any host and every surface — the
attribution line included — keeps reporting local. The loopback claim is true of the default
and of nothing else. The one fixed call is `server.py:7135`'s launch-time probe.

### S7 — there is no chokepoint, restated as the general case

Sixteen bundled `urlopen` sites, each its own authority. The three keys share one lookup
convention (`_get_config_value`) — that is the only place where egress-related code is shared,
and it governs where a credential is *read from*, not where it is *sent to*. F1 of the health
document is not a health finding.

### S8 — the software executes an unverified download on one click

`_run_install_ollama`: HTTPS fetch from `ollama.com`, then `subprocess.run([exe, '/VERYSILENT',
'/SUPPRESSMSGBOXES', '/NORESTART'])`. TLS is the whole provenance chain. Present on all three
lines. Contrast the update path, which refuses any manifest URL off the official prefix — the
two downloads in the product are held to different standards and nothing says why.

### S9 — the current containment boundary: what holds by design, on every line

Recorded so the inventory is not only a list of gaps — and, after 2026-09-19, so that it says
what the model-facing surfaces *are* today rather than merely that certain files make no model
call. **S9 is a statement about current containment. S10–S12 are separate crossings the
inventory had not measured; they are not folded here (Rob, 2026-09-19).**

**Egress and credential provisions**

- the session-token guard on `/api/*` (`_check_session_token`);
- provider defaults to `local`; cloud requires the literal setting;
- credentials: filesystem only, never DB, never echoed, never bundled, one convention;
- the update manifest's download URL is prefix-checked against the official site;
- the reference lookups (EIA, Nominatim, SerpApi, Yahoo) carry no personal figure — codes,
  names, dates, tickers — and Nominatim results are cached per place so a city is sent once;
- the update check sends nothing but a user-agent string;
- bind is loopback and never configurable to a public interface.

**The model-facing surfaces — measured 2026-09-19**

- **System-initiated surfaces are deterministic today.** `core/proactive.py`, `core/solution.py`,
  `core/consequence.py` — every surface that speaks without being asked — contain no model
  call. The alarm side of `ASSISTANT_SCOPE.md` has no model in it.
- **PDF extraction has a validation-and-review boundary.** `pdf_statement.py:168`
  `validate_and_clean` nulls any summary figure, and drops any transaction, whose number is not
  literally in the source text — the safe direction is always null/drop; then
  `app.js:5844` `_renderPdfSummaryPanel` puts the figures in front of the user to correct before
  `pdf-reconcile` overwrites anything. Two gates, both by design, on every line.
- **Downloads auto-import only queues and offers.** `launch.py` `_queue_import_file` posts to
  the app's own queue; `app.js:1122` `_offerAutoImport` waits for the user. Nothing is parsed —
  and so nothing reaches a model — until the user accepts.
- **The classification and extraction surfaces render rather than persist.**
  `trip_learn_classify` (`app.js:10370`) and `trip_quote_extract` (`app.js:10559`) hand their
  parsed JSON to a renderer and nowhere else. No write.
- **Voice rules constrain the output surface.** `static/voice_rules.json`, loaded verbatim by
  both the harness and `callAI`'s gate so the two cannot drift: never fabricate a reading, never
  assign motive, never coach or judge, never present an inference as a finding — "state what
  happened, why it matters in their numbers, and what options exist." An anti-advice provision
  as much as an anti-fabrication one.

### S10 — a model's number is persisted as the user's plan, unmarked: **no silent writing**

`generateTripBudget` → `app.js:11115` `POST /api/trip/budget` with `{...d, aiResult: data,
generatedAt}` → `server.py` `save_trip_budget` → `AppSetting('trip_budget')` holding the whole
body. Those are S2's prices — produced by a "search" that never ran — written as *the trip
budget*: no provenance marker, no R8-style check against any source, no review panel between the
model and the row. On every line.

This is qualitatively different from S1–S8. The violation is not that a model produced bad
numbers; it is that **model output crosses from transient model output into durable application
state while being represented as though it were an application-owned fact or plan.** It is the
only place in the product where a model output becomes a record with neither validation nor a
human in between. In the 2.0 substrate's terms it is a claim with no recording party — the exact
thing the substrate refuses to mint — and it is the cousin of the no-silent-learning boundary:
**no silent writing** is the boundary language and is to be preserved (Rob, 2026-09-19).

Not fixed here. It remains a finding until the relevant 1.x / 2.0 scope decision says what
happens to the feature.

### S11 — the untrusted-text → model boundary is real, named, and currently contained by S1 alone

Third-party text reaches the model on three concrete surfaces:

- **bank descriptions** — `trip_learn_classify` sends `description[:60]` per transaction;
- **issuer PDFs** — `pdf-extract` sends the condensed statement text;
- **pasted quotes** — `trip_quote_extract` sends whatever the user pasted from a third party.

**Current containment, exactly:** today the blast radius is bounded because the model has no
hands (S1). An injected memo can at worst put words on a screen — and those words pass R8 (PDF),
a review panel (PDF), or the voice gate (narrative) on the way. The problem is not that prompt
injection can make the model take an action today. The problem is that the system has an
identifiable untrusted-text → model boundary whose consequences change the moment tools arrive,
and that boundary is held by a provision that exists by absence.

**The transition, recorded now so it is not discovered later:** when an Assistant tool is
introduced, every existing third-party-text → model path becomes an action-adjacent boundary and
requires its own crossing test. This list is what that pass inherits. No generic "prompt-injection
defence" is specified here; the three paths are.

Locality is not a defence. The local model (phi3.5) is more injectable than the cloud one, not
less. **Locality protects data and control boundaries; it does not make untrusted instructions
trustworthy.**

### S12 — `pull-model` accepts any registry name, so the voice contract is not closed

`server.py:7004` `ai_pull_model` takes `model` from the request body with no allowlist; any
Ollama registry name can be pulled and will then speak behind the "Analyzed on your machine ·
*model*" attribution and through a voice gate tuned against phi3.5. Severity small, and kept
small. The invariant it fails is: **the model behind the Groundwork Assistant's voice is an
identified, controlled model, not arbitrary registry content.** Same family as S6 — the
attribution line reports a setting, not a boundary. Inventoried, not solved.

**Observed live, 2026-09-20 (`STREAMING.md` T5):** with onboarding skipped, `_resolve_local_model`'s
auto-detect order (`qwen → llama → phi → mistral → gemma`) chose `qwen3:4b` over the installed, ruled
`phi3.5`; the attribution line read "Analyzed on your machine · qwen3:4b"; `think: False` did not take and
every budget was spent on reasoning, 3 of 3 rejected by the gate. The high onboarding tier pins
`qwen2.5:7b`, the size class measured at 70 % inference-smuggling. Both are decided-not-built.

### S13 — the gate checks that a figure is present, not what it is attached to

`STREAMING.md` T9, folded here on Rob's instruction 2026-09-20. The report-card follow-up surface
sends only the prior assistant bubble and the user's question — no findings — and its answer read
`$1,078.32` (the amount *paid down* on the Harbor Visa) as the *remaining balance*, then advised
focusing on that debt. R5 catches the advice. **Nothing catches a figure that is in the findings
but attached to the wrong noun**: R8's provenance check is presence in the findings text, not the
relation the sentence asserts. On every line; on every gated surface, not only the follow-up.

Class: a gap in the output-surface containment S9 records (voice rules constrain the output surface)
— the containment is real for tone, motive and invented numbers, and does not reach *misattributed*
numbers. A crossing the same size as a wrong balance on screen. Inventoried, not solved; not a
streaming finding and not to be solved inside item 10.

---

## 7. What this inventory does not do

- It does not propose an egress chokepoint, a tool allowlist, a preview gate on the other eight
  surfaces, redaction in the PDF path, or hash-checking the installer. `HEALTHCARE_FAILURE_SEMANTICS.md`
  §5's rule applies: the inventory exists so that a provision, when one is opened, is designed
  against what is there rather than what was assumed.
- It does not rank S1–S13. S1–S8 are listed in the order Rob's sentence raised them; S10–S12
  in the order the second axis surfaced them; S13 arrived from item 10's measurement.
- It does not fix S10 or S12. Both stay findings until a scope decision names what happens to
  the feature; S11 stays a list until the pass that introduces a tool inherits it.
- It does not decide which of them, if any, belong to 1.x. S2, S3, S4 and S8 are shipped
  behaviour on `v1.1.0`; whether the LTS line takes a fix is a release question, not a
  measurement one.
- It is a point-in-time measurement against three named commits. `app.js` line numbers on
  `v1.1.0` differ from the shared `lts/1.x`/`master` numbers and are given where they were
  measured.

---

## 8. The discipline going forward — Rob's ruling, 2026-09-19

Everything settled for the Assistant in `ASSISTANT_SCOPE.md` — no silent learning, no motive, no
ambient capture, per-account visibility, alarm governance, the standing-grant rule — *is* the
2.0 AI-safety doctrine, and today it is all doctrine and no measurement, because there is no
Assistant code yet. That is correct for now. The provision to carry is procedural, and it is the
analogue of the PARTIAL exit criterion:

> **Every settled Assistant safety rule receives a concrete crossing inventory and an executable
> violation test when its implementation first exists.**

It avoids two opposite mistakes. **Too early:** inventing elaborate safety machinery for
hypothetical code that does not exist. **Too late:** a beautiful safety doctrine that nobody has
ever demonstrated against the actual crossing where it matters — F1 again, an invariant whose
machinery has no contact with any crossing.

**Item 9A does not inherit any of this.** `UNDER_PLAN`, `_BEGAN`, `_ENDED` are ontology work.
S9–S12 are the Assistant safety inventory. The concerns may sit adjacent in the record; S10, S11
and S12 do not enter the 9A build.

Then stop. The safety work stays measured and does not become speculative architecture.
