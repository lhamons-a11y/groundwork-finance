# Cloud AI removal — all local, or no AI at all

> Status: **OPENED 2026-09-26, no code.** The decision is Rob's, already made (2026-09-25):
>
> > *"With LTS and 2.0, cloud is going away. It has to be all local or no AI at all. I think that
> > is fair to the users and would clear up any confusion."*
>
> This pass does **not** reopen whether. It inventories **what** goes, **how** existing users
> cross over, and **what proves it is gone**, on both lines. Queue item 21.

---

## The invariant

> **No call Groundwork makes can carry a user's data to an AI model off the device. That holds by
> absence: the cloud path is not in the code, not switched off in it.**

The privacy claim is only as strong as that absence. A hidden toggle with the code still
shipped keeps the asterisk.

---

## 1. What is fixed

1. **The decision** (Rob, 2026-09-25): cloud AI leaves **both** `lts/1.x` and 2.0 (`master`).
   Local AI (Ollama, loopback only) stays.
2. **Local-only removes the privacy reason and nothing else.** Untrusted document text into a
   model (S11) and the size limits of local models stand. Documents still reach a model only as
   Groundwork's source-tied readings (`SOURCE_DOCUMENT_CUSTODY.md` D10).
3. **The other outbound calls are not AI and are not in scope:** the update check, Yahoo ticker
   prices, EIA fuel and utility prices, SerpApi flights. They carry reference-data parameters,
   never a user's figures (the July audit).
4. **No silent writing.** Whatever happens to an existing user's settings and stored key is told
   to them.
5. **Schema discipline** (the s51 pin). Any change to `migrate.py` needs a `SCHEMA_VERSION` bump
   and a proof on an old database.

---

## 2. The surface — measured 2026-09-26

Nearly identical on both lines. Mentions of `anthropic`, `_ai_chat_cloud` or `Powered by Claude`
number 19 / 14 / 3 on `lts/1.x` and 20 / 15 / 3 on `master` (`server.py` / `app.js` /
`index.html`).

| where | what | note |
|---|---|---|
| `server.py` `ai_chat` / `_ai_provider()` | routes `/api/ai/chat` to `_ai_chat_cloud` when the stored `ai_provider == 'cloud'` | the switch |
| `server.py` `_ai_chat_cloud` | the **only** request to `https://api.anthropic.com/v1/messages` (`x-api-key`, `anthropic-version`, model `claude-haiku-4-5-20251001`) | the network path |
| `server.py` `_ai_complete_text` (`:3451`) | the same switch for server-side completions, used by **PDF statement extraction** | a second caller of the cloud path |
| `server.py` `POST /api/settings/api-key` | writes `ANTHROPIC_API_KEY` into `config.json` (key must start `sk-ant-`) | **`config.json` also holds the EIA and SerpApi keys** |
| `server.py` `_get_api_key` / `_get_config_value` | read `ANTHROPIC_API_KEY` from `config.json` **or the environment** | |
| `server.py` bootstrap / `ai/status` | `api_key_configured`; `active_model = claude-haiku-…` when cloud | |
| `index.html` | the **Local (free) / Cloud (Anthropic)** provider switch; the `sk-ant-` key field | |
| `app.js` | 17 `aiProvider` references; the **one** preview-before-send (`_rcSendAI`, *"Here's what Groundwork will send to Anthropic's API…"*); the **"Powered by Claude"** attribution (4) | |
| PDF extraction without any model | `/api/debt/pdf-extract` answers `ai_available: false, reason: no_model` | **measured: without AI, PDF statements cannot be imported.** CSV / QFX / OFX / QIF need no model |
| tests | `smoke_test.py` (`ai/status` provider ∈ {local, cloud}); `s26` asserts the cloud path proxies `stop_reason`; `s60` one reference | tests that pin the cloud path |
| docs and legal | `README.md:62` (the Anthropic key); `SETUP_GUIDE.md:134–150` (the AI section: *create an account at console.anthropic.com*, per-report charges); **`EULA.txt` §7** (*"If you choose to enable cloud mode, aggregated figures are sent to a third-party AI provider"*); `Website/website.py` (*Cloud AI — optional (Anthropic)* at `:1032`, privacy `:1136`, `:1236`, `:1311`) | |
| `SAFETY_PROVISIONS_INVENTORY.md` | **S3** (the preview gate covers one of nine surfaces) and **S4** (*"raw transactions stay on your computer"* has two cloud exceptions: trip classification and PDF import) | both exist only because cloud exists |
| developer scripts (`jev_category_screen.py`, `llm_model_eval.py`, `voice_discipline_test.py`, `llm_runtime_spike.py`) | not referenced by any build spec, so not shipped | outside the product |

---

## 3. Findings

**C1 — Removal is absence, and a test proves it.** Delete `_ai_chat_cloud`, the provider switch,
the key route, the key lookup, the provider UI, the attribution, and the cloud preview. Two
crossing tests:

- **source:** the shipped sources (`server.py`, `launch.py`, `static/`) contain no
  `api.anthropic.com`, no `x-api-key`, no `anthropic-version`, no key route, and no `'cloud'`
  provider value;
- **runtime:** with outbound network blocked (the s50 technique) and `ai_provider = 'cloud'`
  **planted in the database**, every AI route either uses the local model or reports AI
  unavailable. None attempts a non-loopback connection.

Mutations: the endpoint restored; the switch restored behind a setting; a second provider
added under another name.

**C2 — Keep the internal response shape.** The local path returns Anthropic-shaped JSON
(`{content: [{type: 'text', text}]}`, the `stop_reason` vocabulary, `s26`'s mapping). That's an
internal contract between `server.py` and `app.js`, not a network path. Renaming it is churn
across every AI surface, for no privacy gain. **Candidate: keep it**, documented as an internal
format. `s26`'s *cloud proxies `stop_reason`* check is retired, and its local mapping kept.

**C3 — Existing users cross over visibly, once.** On the first start after the upgrade:

- `ai_provider = 'cloud'` becomes **local** if a local model is reachable, otherwise **AI off**,
  never a silent failure on every AI surface;
- the user sees **one notice**: cloud AI has been removed, AI now runs on this computer (or is
  off, and why), and *"your Anthropic key has been removed from Groundwork"*;
- **the stored key is deleted**: `ANTHROPIC_API_KEY` only, from `config.json`. The EIA and
  SerpApi keys in the same file stay untouched. A secret nothing reads should not persist.
  `ANTHROPIC_API_KEY` in the **environment** is the user's and cannot be deleted; Groundwork
  simply stops reading it.

This is a one-time, flagged step. If it lives in `migrate.py`, it bumps `SCHEMA_VERSION`, updates
the pin, and is proved on a real v1.1.0 database with `ai_provider = 'cloud'` and a key in
`config.json`. **Ruling sought:** delete the key and tell (candidate), or tell and offer a *Remove
key* button.

**C4 — Machines that can't run local AI get no AI, said plainly.** Onboarding's low tier already
offers *"the fully-structured experience, not a slow model"*. Settings says the same thing where
the cloud switch was, and the release notes say it outright: users who relied on cloud AI on
weak hardware lose it.

**C5 — What cloud-only machinery goes with it.** The preview-before-send and *"Powered by
Claude"* existed only because data could leave. **S3 and S4 close**: nothing leaves, so no
preview is needed and no exception remains. *"Analyzed on your machine"* stays, true and
unconditional. **S5 and S11 are not cloud-specific and stay open.**

**C6 — PDF statements without a local model.** Measured: no model, no PDF import. Today a
weak-hardware user with a key could import PDFs through the cloud; after removal, they can't at
all. Candidates: **(a)** say so honestly in the import dialog and point to the bank's CSV / QFX
export; **(b)** a model-free extraction path, a real feature and its own pass. **Candidate (a)
now, (b) named.**

**C7 — Copy and legal.** README, SETUP_GUIDE's AI section, the website's cloud sections and its
privacy text are rewritten. **EULA §7 changes**, since its cloud clause describes something that
no longer exists. Whether the EULA's version number moves, and whether users re-accept, is a
legal call. **Ruling sought.** Removing a data-sharing clause favours the user, but it is still a
change to terms they accepted. **The unconditional privacy line** (*no call this app makes can
carry your financial data off your device*) goes live only when the code is gone, not before.

**C8 — Order: `lts/1.x` first, then merge to `master`,** the way the schema fix went. The two lines
differ by one cloud reference, so the merge should be mechanical, and each line gets its own
full gate plus the C3 proof on an old database.

**C9 — Out of scope, fenced:** the Assistant (`C:\Assistant`), a separate product with its own
providers; the developer scripts (not shipped); the non-AI outbound calls (fixed 3).

---

## 4. Cases

| # | situation | expected |
|---|---|---|
| Cr1 | fresh install | no cloud option anywhere; AI is local or off |
| Cr2 | a v1.1.0 database with `ai_provider='cloud'` and a key in `config.json`, local model reachable | starts; provider becomes local; one notice; `ANTHROPIC_API_KEY` removed from `config.json`; the EIA / SerpApi keys untouched |
| Cr3 | the same, no local model | starts; AI off; the notice says why; key removed |
| Cr4 | `ANTHROPIC_API_KEY` set in the environment | ignored: no route reads it |
| Cr5 | **the crossing test**: network blocked, `ai_provider='cloud'` planted | every AI route local or unavailable; no outbound attempt |
| Cr6 | the source scan | no Anthropic endpoint, headers, key route or cloud provider in shipped files |
| Cr7 | PDF statement import, no local model | an honest message pointing to CSV / QFX; nothing sent anywhere |
| Cr8 | the notice | shown once, never again after it is dismissed |
| Cr9 | the upgrade proof | on a real v1.1.0 database, both lines, bootstrap 200 (s51's discipline) |

---

## 5. Readings

- **R**: remove, as C1–C8. **Candidate.**
- **H**: hide the switch, keep the code. **Refused:** the claim is only as strong as the absence.
- **K**: keep cloud on `lts/1.x` only. **Refused** by the decision itself, which names LTS.

## 6. Ruling sought — Rob

1. **R**, with the C1 crossing tests (source scan, and runtime with the network blocked)?
2. **C2**: keep the internal Anthropic-shaped response format?
3. **C3**: on upgrade, cloud becomes local-or-off with one notice, and the stored key is deleted
   (candidate), or kept with a *Remove key* button?
4. **C6**: PDF statements without a local model get an honest message now, with model-free
   extraction named as its own pass?
5. **C7**: the EULA §7 rewrite: a version bump, and re-acceptance or not?
6. **C8**: `lts/1.x` first, then merge to `master`?
