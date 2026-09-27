# Cloud AI removal — all local, or no AI at all

> Status: **RULED, BUILT and ACCEPTED 2026-09-27 (Rob, §7 / §8), with EULA 1.1. CLOSED. The build goes `lts/1.x` first. The EULA wording and
> version are a separate legal-text decision.** Opened 2026-09-26. The decision is Rob's, already made (2026-09-25):
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

---

## 7. Ruling — Rob, 2026-09-27

| # | ruling |
|---|---|
| **1** | **R: remove cloud AI outright on both lines, with both crossing tests.** The invariant is stronger than *"the option is unavailable"*: Groundwork has **no path** that sends user data to an off-device AI model |
| **2** | **Keep the internal message format.** It is an application-internal contract and implies no network transport |
| **3** | **Delete the stored key automatically on upgrade, with a one-time notice.** No remaining feature can use it, so keeping it is obsolete sensitive configuration. **Only `ANTHROPIC_API_KEY`**; the rest of `config.json` is preserved. A key in the environment simply becomes unused and is never mutated |
| **4** | **An honest PDF message now; PDF import without a model is a separate pass.** Import semantics do not change silently, and nothing pretends local AI can handle a PDF when it can't. CSV / QFX / OFX / QIF are unaffected |
| **5** | **EULA:** when §7 is rewritten, the version number changes, and **acceptance is required again if the revised clause materially changes the user's agreement about data handling.** The exact wording and version are **a separate legal-text decision**, not inferred from this engineering pass |
| **6** | **`lts/1.x` first, then merge to `master`**, the same controlled progression as the schema work |

**Measured for ruling 5, so the legal decision knows what it controls:** re-acceptance already
exists. `app.js` holds `GW_TERMS_VERSION = '1.0'`, and the gate shows the terms to **any user
whose stored `terms_accepted` differs from it**. So *"acceptance required again"* is one version
bump, no new code. The terms text lives in **three places that must match**: `EULA.txt`,
`_TERMS_HTML` in `app.js`, and the website's /terms page (`app.js`'s own comment says to keep all
three in sync).

**What this means for the build, and what it doesn't:**

- the engineering build removes the code, crosses users over (ruling 3), adds the honest PDF
  message (ruling 4) and both crossing tests (ruling 1), on `lts/1.x` first;
- it does **not** write the new EULA §7, nor choose its version or whether users re-accept.
  Those come from the legal-text decision;
- **but** once the code is gone, today's §7 describes a cloud mode that no longer exists. So **the
  EULA text is a release dependency**: no release ships the removal with the old §7 still in the
  three places. The build note will record that dependency, not settle it;
- the unconditional privacy line (C7) goes live in copy only when the code is gone **and** the terms
  match.

---

## 8. Built — both lines (2026-09-27) — ACCEPTED (Rob, 2026-09-27)

**`lts/1.x` first (`765ec58`), then merged to `master`**, as ruling 6 set.

**Removed:** `_ai_chat_cloud` (the only request to `api.anthropic.com`); the provider switch in
`ai_chat` and in `_ai_complete_text` (PDF extraction's caller); `POST /api/settings/api-key`;
`_get_api_key` and `api_key_configured`. `ai/status` names local as the only provider, and the
settings PATCH ignores `ai_provider` and `api_key`. **In the page:** the Local / Cloud (Anthropic)
switch, the `sk-ant` field, the one cloud preview-before-send, *"Powered by Claude"*, the
cloud-only *Generate* button, every `aiProvider` branch, and onboarding's offer of a cloud key.
**Kept:** the internal Anthropic-shaped response format (ruling 2). On master, item 12's comments
now describe it as that internal format, and s26's *"the cloud path proxies stop_reason"* check is
retired: its replacement asserts no cloud path remains.

**Beyond the pass's inventory, flagged for Rob:** *"local" is now a boundary.* `local_endpoint`
must be a loopback address. It is refused on save, and a planted non-loopback value is ignored at
the moment of use. This closes S6, because ruling 1's *"no path"* could not hold while "local"
could point anywhere. **Its cost:** Ollama run on a second machine is no longer reachable.

**The crossover (ruling 3):** a flagged one-time `_remove_cloud_ai` step in `migrate.py`. It
removes `ai_provider`. It deletes **only** `ANTHROPIC_API_KEY` from Groundwork's own
`config.json`, by atomic replace; the EIA and SerpApi keys stay, an unreadable file is left
alone, and an environment key is simply unused. It records a one-time notice **only for a user it
affected**. `SCHEMA_VERSION` is `20260927-lts-cloud-ai-removed` on 1.x and
`20260927-cloud-ai-removed` on master (distinct, so each line's databases migrate), each with its
own s51 pin. **The notice is recorded as shown the moment it is displayed.** The first version
recorded it only on OK, so Cancel or × would have brought it back on every start; that was found
in the browser. Local AI if this machine runs it; otherwise AI turned off and the user told so.
**PDF without a model:** an honest message pointing to CSV / QFX (ruling 4).

**Measured:**
- a **v1.1.0** cloud user with a saved key and an EIA key, opened by 1.x and by master:
  bootstrap 200, `ai_provider` gone, the Anthropic key gone, the EIA key kept, the notice
  recorded. The same for a **pre-merge master** cloud user;
- in the real page (1.x): the notice with local AI ready; the notice with local AI unreachable,
  where AI was turned off and the topbar said *AI off*; the notice never returning after
  dismissal; the Settings AI panel local-only, the override labelled *(this computer only)*;
- **s52**: 22 / 0. The source scan found no hosted-model endpoint in any shipped file. The runtime
  crossing test refused every connection with 'cloud', an env key and a remote endpoint planted:
  every AI route answered and none reached beyond this computer. Plus the crossover, and five
  mutations each caught.

**Gates:** 1.x **794 / 0**, then over V10 **807 / 0**; master merge **1852 / 0**.

**Not done here, by ruling 5: the EULA.** §7 in `EULA.txt`, `_TERMS_HTML` in `app.js` and the
website's /terms page still describe cloud mode. The wording, the version, and whether users
re-accept are Rob's separate legal-text decision. **This is a release dependency:** no release
ships this removal while those three still say cloud mode exists. Re-acceptance is one bump of
`GW_TERMS_VERSION`.

**Not covered:** macOS / Linux; a frozen build. s52's source scan lists the shipped modules by
name, so a new top-level module must be added to it.

**Rob, 2026-09-27, on the two open points:**

1. ***"Local" as a boundary* — ACCEPTED.** `local_endpoint` stays loopback-only; S6 is closed, and
   Ollama on a second machine is knowingly given up.
2. ***"Fix EULA"* — DONE, and the release dependency is CLEARED.** §7 now reads: *AI features are
   optional and run only on your own computer, using a local model; the Software does not send
   your data to any AI service and has no option to; without a local model they are unavailable
   and the rest works as described; outputs subject to §§3–4.* It is changed identically in
   `EULA.txt` (**Version 1.1**, effective September 27, 2026, which the three installers also
   show), `_TERMS_HTML`'s AI sentence, and the website /terms page. §7 was the only clause
   describing cloud AI. **Re-acceptance** (ruling 5, since the clause materially changes the data
   handling agreed to): `GW_TERMS_VERSION` is `'1.1'`, so every 1.0 user sees the terms again.
   Measured in the real page: a 1.0 user got the gate with Version 1.1 and the new §7, and
   *cloud mode* appeared nowhere. s52 gains two pins so the three texts cannot drift: one version
   everywhere, and no terms text describing a cloud mode or a third-party AI provider.
   `lts/1.x` `a465a70`, gate **809 / 0**; merged to master below.

**ACCEPTED AS A WHOLE — Rob, 2026-09-27.** The removal on both lines (`lts/1.x` `765ec58`, master
`6756e52`), the crossover and its notice, the honest PDF message, *"local" as a boundary*, the
s52 crossing tests, and EULA 1.1 with re-acceptance (`a465a70` / `b6a353e`). Item 21 is closed.
**Still open, by name, and not part of the acceptance:** macOS / Linux and a frozen build are not
measured, and s52's source scan must be told about any new top-level module.

