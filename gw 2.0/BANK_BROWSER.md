# The bank window — downloading from the institution inside Groundwork

> Status: **OPENED 2026-09-23, no code.** Rob's question, and only it:
>
> > **May Groundwork open the user's bank or card site in a window of its own, so the user
> > downloads transactions and statements there and the file lands in the existing review —
> > and what may that window never do?**
>
> Queue item 18. Findings, cases, candidate, recommendation; ruling sought.

---

## 1. What is fixed

1. **pywebview, not Tauri** (Rob, 2026-09-23). pywebview 6.2.1 already runs on all three
   systems on the same OS engines Tauri would use (WebView2 · WKWebView · WebKitGTK). No
   shell rewrite, no Rust, no change to the three PyInstaller specs beyond what this pass adds.
2. **The download stays manual.** The user signs in, the user clicks download. Groundwork
   never logs in, never fetches, never schedules, never retries. This replaces SimpleFIN for
   now. It does not rule on SimpleFIN, and SimpleFIN's relay question stays unruled.
3. **The link lives on the account** (Rob, 2026-09-23). Each account the user downloads from
   carries its own URL, set in that account's settings. There is no global "bank URL" field.
4. **No silent writing.** Every file reaches the ledger only through the existing staged
   review, `/api/import/preview` → `/api/import/commit`. The window adds no second path.
5. **The captured-portal ruling** (`CAPTURED_PORTAL_CASES.md`, 2026-09-12). A statement the
   institution issues and the user downloads is an artefact the institution **issued**
   (K1-shaped). A screenshot of the portal is an artefact **of a rendering** (C2). Those are
   different evidence conditions. *Held is not verified.*
6. **S1 holds by absence** (`SAFETY_PROVISIONS_INVENTORY.md`). The model has no hands. The
   window must not become the first thing that gives it any.
7. **The privacy claim.** *No call this app makes can carry your financial data off your
   device without you choosing it.* The window must keep that sentence true, not add an
   asterisk to it.

---

## 2. The surface today — measured 2026-09-23 at `ed041da`

| where | what it does now | why it matters here |
|---|---|---|
| `launch.py:416` | one `create_window`, `js_api=GroundworkAPI()`, `webview.start(debug=False)` | `private_mode` not passed, so it defaults to **True**: no cookies or storage survive a restart, in any window |
| `webview.settings` | `ALLOW_DOWNLOADS: False` · `OPEN_EXTERNAL_LINKS_IN_BROWSER: True` | downloads are off today. The setting is **global**, so turning it on also allows downloads in the main window. New-window links on a bank page go to the system browser. |
| `launch.py:238` `_start_downloads_watcher` | watches `~/Downloads`, **`on_moved` only** (a browser's temp-name → final-name rename) | a backend that writes the final name directly fires `on_created` / `on_closed` and is **not seen** |
| `launch.py:177` `_IMPORT_EXTENSIONS` | `.qfx .ofx .qbo .qif .csv`, ≤ 5 MB | **no `.pdf`**, so statements are never picked up |
| `server.py:7235` `/api/auto-import/queue` | holds up to 5 `{filename, content, path}` in memory | this is the review path the window's files should reach |
| `server.py:3053` `/api/debt/pdf-extract` | a PDF statement is extracted by the **model**, local or cloud | a downloaded statement must never be routed here automatically |
| `core/database.py` `Account` | `institution` string, **no URL** | fact 3 needs a column |
| `core/database.py` `DebtAccount` | cards live here (`debt_type='credit'`), optional `linked_account_id` → `Account` | a card can be **two rows**: see F2 |

---

## 3. Findings

**F1 — The window is a second window with no bridge.** `create_window(url=<the account's
link>, js_api=None)`. Nothing ever calls `evaluate_js`, `get_elements`, `get_cookies`,
`load_html` or `load_url` on it after it opens. Groundwork does not read the page, fill it,
watch it, or learn which bank the user visited from it. The page runs on the OS engine and
talks to the bank directly. Groundwork makes **no outbound call of its own**. This is the
crossing surface, so per the crossing-test discipline it gets its inventory and violation
test **with the code that creates it**, not later (Fd-shaped; see §6).

**F2 — Which row carries the link.** Fact 3 settles "on the account"; the schema gives two
places a card can be:

- **(a)** a `portal_url` column on **both** `Account` and `DebtAccount`, each edited in its own
  settings. When a `DebtAccount` has `linked_account_id`, its settings **show and edit the
  linked Account's link**. One card, one link; two links on one card would disagree.
- **(b)** `Account` only. A card that exists only as a `DebtAccount` gets no button. That
  refuses the credit-card half of Rob's request.

Recommend **(a)**. The column is nullable. An empty link means *no button*, never a guessed
URL from `institution`.

**F3 — What a link may be.** `https://` only, stored exactly as the user typed it after
trimming. Refused on entry: `http:`, `file:`, `javascript:`, `data:`, and any host that
resolves to loopback or the local network (a link to `127.0.0.1:8765` would open Groundwork
itself). No shipped list of bank URLs, since a curated list is a list we must keep true. The
link is the user's statement of where their bank is, and Groundwork does not second-guess
it beyond the scheme and host rule.

**F4 — The link never enters a model payload.** Which bank a household uses is not a dollar
figure, but it is exactly what `privacy_call_home_audit` says leaves only by choice. The link
joins nothing the snapshot, the narrator, or the cloud path builds. There is one violation
test: plant a link and assert it appears in no provider request body.

**F5 — Sessions are not kept.** `private_mode=True` is today's default, and this pass does
not change it. The cost is honest: the bank will ask for two-factor on every visit, and "remember
this device" will not stick. The OS password manager and browser extensions are also absent.
**Refused here:** switching to a persistent `storage_path`. That would make Groundwork's
profile hold a live bank session on disk, which is a custody question, not a convenience
setting. It gets its own pass if users ask.

**F6 — Downloads, and where they land.** `ALLOW_DOWNLOADS=True`. Where the file then goes is
**backend-specific and unmeasured**: WebView2 may save straight to Downloads, WKWebView may
prompt, WebKitGTK may prompt or refuse. Recommendation: land in `~/Downloads`, the same place
a normal browser puts it. The user keeps a file they can see, and the existing watcher
already reads there. **The event gap in §2 must be measured on each OS before anything is
called working.** Measure where the failure can appear: at the watcher, with a real download
from the real backend, not a fixture that renames a file.

**F7 — Statements are surfaced, never extracted.** Add `.pdf` to what the watcher *notices*,
but not to what it *queues for import*. A downloaded PDF raises one line: *"Statement
downloaded: X.pdf. Open it in Debt statements?"* Nothing runs until the user says yes. The
cloud path keeps its per-call preview. Without this, the first statement download would be
the first import that spends a model call the user never asked for.

**F8 — The window takes no captures.** No screenshot, no print-to-PDF, no "save this page".
A capture of a rendering is a different evidence condition (fact 5, C2), and this pass does
not open it. Whether a downloaded statement is **held**, meaning retained in Groundwork's
custody as an `Artefact`, is also **not opened here**. The file in Downloads is the user's.

**F9 — The escape hatch is required, not optional.** Some banks refuse embedded engines or
break their MFA pop-ups (see `OPEN_EXTERNAL_LINKS_IN_BROWSER`). Passkeys are limited on
WKWebView and WebKitGTK. Beside every *Open bank* button sits **Open in my browser**
(`webbrowser.open`, same link). Files downloaded there reach the same watcher. The feature
is not allowed to fail with no way forward.

**F10 — The Assistant gains nothing.** No tool, no action, no "go get my transactions". S1
stays true by absence, and this pass adds a line to the inventory saying it was relied upon.

**F11 — Absence is not zero.** The window records no coverage. A skipped or failed download
is missing data, exactly as it is today. The button does not imply *up to date*.

---

## 4. Cases

| # | situation | expected |
|---|---|---|
| Bw1 | checking account with a link; user downloads a QFX in the window | one staged import appears; nothing committed until the user commits |
| Bw2 | card as `DebtAccount` linked to an `Account` | one link, edited from either; one button |
| Bw3 | card as `DebtAccount` only | its own link, its own button |
| Bw4 | account with no link | no button; nothing guessed from `institution` |
| Bw5 | link `http://…`, `file://…`, `javascript:…`, `https://127.0.0.1:8765` | refused on save, with the reason |
| Bw6 | user downloads a statement PDF | one surfaced line; no model call until yes |
| Bw7 | the bank refuses the embedded engine | *Open in my browser* works; its download reaches review |
| Bw8 | restart, reopen the bank | signed out; MFA asked again (F5, by design) |
| Bw9 | download on each backend (Windows · macOS · Linux) | the watcher sees it; measured on the real backend, not simulated |
| Bw10 | the crossing test | bank window `js_api is None`; no `evaluate_js` / `get_cookies` / `get_elements` call site reaches it; the link appears in no provider payload |
| Bw11 | same file downloaded twice | the existing `seen` / dedup path applies; no second import |

---

## 5. Readings

- **N**: build nothing; users keep downloading in their own browser (the watcher already works).
- **W**: the window as §3 specifies: per-account link (F2a), no bridge, private sessions,
  Downloads + watcher, statements surfaced, escape hatch, crossing test.
- **W+**: W with persistent sessions or captures. **Refused** (F5, F8): each is its own
  question.

## 6. Candidate and recommendation

**W.** The build, when authorised:

1. nullable `portal_url` on `Account` and `DebtAccount` via `migrate.py`'s `_add_missing_columns`;
   the F3 check on save
2. the link field in each account's settings, with a linked card showing its Account's link (F2a)
3. *Open bank* + *Open in my browser* on each linked account
4. a `GroundworkAPI` method that opens `create_window(url, js_api=None)` and nothing else;
   `ALLOW_DOWNLOADS=True`
5. watcher: `on_created` / `on_closed` with a size-settle check, only if Bw9 shows the gap is
   real; `.pdf` noticed and surfaced, never queued (F7)
6. the crossing test (Bw10) as a smoke section, with mutations: `js_api` set on the bank window;
   an `evaluate_js` added against it; the link added to a provider payload. Each must fail
   the section.
7. one sentence of privacy copy: *the bank's page loads straight from your bank; Groundwork
   sees only the file you choose to download.*

**Not in the build:** SimpleFIN · persistent sessions · captures · statement custody · any
shipped bank list · any Assistant action.

## 7. Ruling sought — Rob's

1. **W**, or N?
2. **F2a**: the link on both tables, a linked card sharing its Account's link?
3. **F5**: private sessions, MFA every visit, accepted as the cost?
4. **F7**: statements surfaced, never auto-extracted?
