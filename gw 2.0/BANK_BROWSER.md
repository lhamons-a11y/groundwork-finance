# The bank window — downloading from the institution inside Groundwork

> Status: **RULED 2026-09-23 (Rob), §7. No code. Sequenced: F12 first, as its own change; W's build follows F12's accepted gate.** Opened and revised the same day. Rob's question:
>
> > **May Groundwork open the user's bank or card site in a window of its own, so the user
> > downloads transactions and statements there and the file lands in the existing review —
> > and what may that window never do?**
>
> Queue item 18. Rob's review (2026-09-23) accepted W in principle and asked for twelve
> tightenings before build; each is answered below and tagged **[R1]–[R12]**. His follow-up the
> same day added runtime currency, **[R13]**, answered as **F13**. Three findings
> are new from reading pywebview 6.2.1's source during the revision: **F1** (per-window
> downloads are impossible, so the window is its own process), **F6** (a relocated Downloads
> folder defeats the watcher), and **F12** (the local server hands its token to any page that
> reaches it).

---

## 0. The invariant

> **The bank window is an untrusted webpage viewer, not a Groundwork integration surface.
> Groundwork supplies only the user-entered HTTPS URL, receives no page state, performs no
> interaction, retains no session, and receives financial data only when the user
> independently downloads a file into the existing review path.**

Every finding below either implements a clause of that sentence or says what enforces it.
The crossing test (§5, Bw10) is that sentence made executable.

---

## 1. What is fixed

1. **pywebview, not Tauri** (Rob, 2026-09-23).
2. **Manual login and manual download.** Groundwork never logs in, fetches, schedules or retries.
3. **The link lives on the account** (Rob, 2026-09-23), with no global "bank URL" setting.
4. **SimpleFIN remains unruled and is not part of this implementation.** The manual bank-window
   path is the current authorized path. **[R12]** This pass makes no ruling that SimpleFIN is
   undesirable or prohibited.
5. **No silent writing.** Nothing reaches the ledger except through the existing staged review.
6. **The captured-portal ruling** (`CAPTURED_PORTAL_CASES.md`). A downloaded statement is an
   artefact the institution issued. A screenshot would be an artefact of a rendering. *Held
   is not verified.*
7. **S1 holds by absence** (`SAFETY_PROVISIONS_INVENTORY.md`). The model has no hands.
8. **The privacy claim.** No call this app makes carries financial data off the device without
   the user choosing it.

**Left alone by Rob's review, and not reopened here:** pywebview · manual login and download ·
no credentials · no page inspection · `js_api=None` · no persistent sessions · no captures · no
automatic PDF extraction · staged import · the browser escape hatch · no URL registry · no
Assistant capability · no *up to date* inference · no SimpleFIN in this build.

---

## 2. The surface today — measured 2026-09-23

| where | what it does now |
|---|---|
| `launch.py:416` | one window, `js_api=GroundworkAPI()`; `webview.start()` with `private_mode` defaulting to **True** |
| `webview.settings` | `ALLOW_DOWNLOADS: False` · `OPEN_EXTERNAL_LINKS_IN_BROWSER: True` — a **module-level dict** |
| pywebview 6.2.1 source | **WebView2** (`edgechromium.py:316`) reads `ALLOW_DOWNLOADS` *at each download* and opens a WinForms **Save dialog** whose start folder is the **registry Downloads folder** (known-folder `{374DE290…}`). **WKWebView** (`cocoa.py:339`) reads it at each response and opens an **NSSavePanel** at `NSDownloadsDirectory`. **WebKitGTK** (`gtk.py:214`) reads it at window creation, connects `download-started` on the web context, and opens a **Save dialog** at the **XDG download dir**. *All three prompt, and in all three the user may save elsewhere.* Read from source, **not measured.** |
| `launch.py:238` watcher | watches **`Path.home()/'Downloads'`**, **`on_moved` only**, extensions `.qfx .ofx .qbo .qif .csv`, ≤ 5 MB, no `.pdf` |
| `server.py:7235` queue | in-memory, capped at 5, **popped** by `/pending` |
| `app.js:1113` poller | every 45 s, only while the import modal is closed; **offers** the file (*"Import now"* / *"Not this file"*); the offer **disappears after 60 s** |
| `server.py:3053` | a PDF statement is extracted by the **model** |
| `server.py:256` / `293` | `/` serves `index.html` **with the session token written into it**, to any request. `/api/*` checks `X-GW-Token` and nothing else: **no Host or Origin check** |
| pywebview 6.2.1 `winforms.py:131–155` | picks **WebView2** only if the Evergreen runtime (≥ 86.0.622.0, 2020) is in the registry. Otherwise it **silently falls back to MSHTML, the IE11 engine**, logging only a deprecation warning. `groundwork.spec:135` **bundles `webview.platforms.mshtml`**. `WEBVIEW2_RUNTIME_PATH` is `None`, so the runtime is Evergreen (not pinned) |
| pywebview `guilib.py` | honours a **`PYWEBVIEW_GUI` environment variable** that can force any backend, and on Linux **`KDE_FULL_SESSION` puts Qt first**. The three specs exclude PyQt5/6, so a frozen bundle cannot pick Qt; a source run can |
| the three installers | check the WebView2 registry key and, on *Yes*, **open Microsoft's download page in the user's browser** (`ShellExec`). Groundwork downloads no engine itself |
| `core/database.py` | `Account` has no URL. Cards live in `DebtAccount` (`debt_type='credit'`), optionally `linked_account_id` → `Account` |

---

## 3. Findings

### The window

**F1 — Downloads cannot be per-window, so the bank window is its own process. [R1] [R8] [R10]**
`ALLOW_DOWNLOADS` is one process-wide dict, read at event time on two backends and at window
creation on the third, possibly on a shared web context. There is no clean per-window switch.
Setting it globally would give the main window download capability for no reason. The
answer is structural, not a test of a global flag:

- The bank window runs in a **separate process**: the same executable started as
  `Groundwork --bank-window`, with **the URL on stdin and nothing else**. There, and only there,
  `ALLOW_DOWNLOADS=True`, `private_mode=True`, `js_api=None`.
- The main process **keeps `ALLOW_DOWNLOADS=False`**. Its download surface is unchanged.
- The bank process imports `webview` and the standard library **only**. No `server`, no
  `core`, no database, no session token, no `GroundworkAPI`. It cannot hand Groundwork
  anything, because it holds no way to reach Groundwork.
- Dispatch happens in `launch.py` **before** Flask, the watcher or Ollama start, so a bank
  process never becomes a second Groundwork.

This is the strongest form of *URL in → webpage out*: the boundary is a process boundary, and
the only financial-data crossing left is the filesystem. **Cost:** a second engine start
(about a second), and on macOS a second Dock icon while a bank window is open.

**F2 — The window's lifecycle. [R8]** The window is a controlled UI resource, not an
intelligent one.

| event | behaviour |
|---|---|
| open the same account's bank while its window is open | no second window; the button reads *already open* (the main process tracks one child per account) |
| open a different account's bank | its own window, its own process |
| the account's URL changes while its window is open | the open window is unaffected (it received a URL once); the next open uses the new one |
| the account is deleted | its bank window is closed (the child is terminated) |
| the main window closes / Groundwork exits | every bank window is closed |
| the bank window closes | nothing happens in Groundwork |
| the window's title | the URL's host, derived from the URL. **Never the account's name**: no account data reaches the bank process |

### The link

**F3 — Which row owns the link: one source of truth. [R7]** A nullable `portal_url` on both
`Account` and `DebtAccount`, with the invariant **enforced at write, not only in the UI**:

- an **unlinked** `DebtAccount` owns its own link;
- a **linked** `DebtAccount` (`linked_account_id` set) **stores NULL** and is not
  independently editable. It displays and opens its Account's link. The server rejects a
  write of `portal_url` to a linked `DebtAccount`, so the database cannot hold
  `DebtAccount.portal_url = A` beside `Account.portal_url = B`;
- **linking** two rows that both hold a link, where the links differ, asks the user which
  one to keep. Groundwork does not pick silently;
- **unlinking** copies nothing. The `DebtAccount` starts with no link, and the user enters one
  if they want it. (Candidate; a ruling point, §6.)

An empty link means no button, never a URL guessed from `institution`.

**F4 — What a link may be, and what Groundwork guarantees about it. [R5] [R6]** Checked on
save **and again at launch**, because the stored value is not trusted just because it passed
once:

- scheme `https` only;
- **no userinfo**: `https://user:pass@…` is refused, never normalised, never stored;
- **no explicit port** (`:443` accepted and dropped): a non-default port has no documented
  reason and blurs the local-network line;
- the host is a DNS name. **IP literals are refused**, as are `localhost`, `*.localhost`,
  `*.local`, `*.internal`, `*.lan`, and single-label names;
- stored as typed after trimming; nothing else is rewritten.

**What Groundwork does *not* guarantee, said plainly:** it does **not resolve DNS** and makes no
claim about where the name resolves, at save or at launch. Resolve-then-check is exactly the
TOCTOU Rob named, and a bank page can navigate anywhere once loaded, so a check on the
first URL could never bound where the window goes. The window is an untrusted web viewer,
like any browser. What protects Groundwork itself from a hostile page is **F12**, on the
server, not this check.

**Groundwork does not verify that the URL belongs to the institution.** The UI must never
imply it did. The field's copy:

> **Bank website**
> This is the address Groundwork will open. Groundwork doesn't check that it belongs to your
> bank. Make sure it does.

No curated list.

**F5 — The link is launch configuration, not evidence or context. [R9]** It is read in exactly
one place, the code that starts the bank process. It appears in **no** model prompt, provider
request body, snapshot (`app_snapshot`), narrator or report input, generated finding, financial
export (CSV / report / share), log line, or the update-check ping. **Backups carry it**, because
a backup is the user's own copy and a restore must restore it; that is the one sanctioned
place it leaves the table. Test: plant a sentinel URL, run every builder that feeds a model or
export, and assert that the sentinel is absent.

### The file

**F6 — Importable means "appeared in the folder the watcher owns", and the two folders must
be the same folder. [R2]** The contract:

> **Groundwork considers a download an import candidate only when it appears in the watched
> download folder. A file saved anywhere else is not seen, and Groundwork says so rather than
> implying the download reached it.**

What each backend does, from source: all three **prompt**, starting in the platform's Downloads
folder, and the user may choose elsewhere. That is acceptable. The bank window's footer says
it once: *"Save to Downloads and Groundwork will offer to import it. Saved somewhere else? Use
Import file."*

**The defect the source exposed:** the watcher watches `Path.home()/'Downloads'`, but WebView2
starts its dialog at the **registry** Downloads folder and WebKitGTK at the **XDG** one. A user
who moved Downloads (`D:\Downloads`), or runs a localised Linux (`~/Téléchargements`), saves to
the dialog's default and **the watcher never sees it**. *Download succeeded ≠ Groundwork can
see the file*, on the default path. The fix is one resolver used by **both** the watcher and
the footer copy: the Windows known folder, `NSDownloadsDirectory`, `XDG_DOWNLOAD_DIR`. This is
pre-existing for the user's normal browser too, but the bank window makes it the default path.

**The event gap:** `on_moved` only. WebView2 writes `.crdownload` then renames it. WKWebView
moves an `NSURLSession` temp file in from outside the folder, which FSEvents may report as
*created* rather than *moved*. WebKitGTK's write pattern is unknown. Add `on_created` /
`on_closed` with a size-settle check **only where Bw9 shows the gap**.

**Bw9 is a build acceptance requirement, not a test.** A real download from a real bank page on
each real backend reaches an offer. A fixture that renames a file does not count.

**F7 — The state machine, for every file. [R3] [R4]**

```text
appears in the watched folder
   → NOTICED      (watcher)                     — reads bytes, interprets nothing
   → OFFERED      (a prompt naming the file)    — interprets nothing
   → CHOSEN       (the user says yes)           — the only door
   → STAGED       (existing preview / review)
   → COMMITTED    (the user commits)
```

| kind | noticed → | on *yes* |
|---|---|---|
| `.qfx .ofx .qbo .qif .csv` | offered | existing transaction import preview |
| `.pdf` | offered (*"Statement downloaded: X.pdf. Open it in Debt statements?"*) | existing debt-statement flow, the cloud path behind its per-call preview |
| anything else | **ignored** | — |
| any kind | **nothing is ever committed, previewed, parsed, extracted or sent to a model before *yes*** | |

**A correction to the review's premise, from `app.js:1127`:** structured files are **not**
auto-previewed today. They are already *offered* (*"Import now"* / *"Not this file"*), and
preview starts only on *Import now*. So the invariant **no downloaded file is interpreted
merely because it appeared** already holds for structured files. PDFs join the same machine
rather than getting a special path.

**The offer can be lost.** `/pending` pops the item and the prompt removes itself after 60 s.
An unanswered offer is gone from the queue but **not from disk**, and *Import file* still
works. This is recorded, not changed here. **Absence is not zero:** an expired offer is not
*nothing to import*.

**F8 — Sessions are not kept.** `private_mode=True` in the bank process. The cost: two-factor
on every visit. A persistent profile would hold a live bank session on disk, and is refused
here as its own custody question.

**F9 — No captures, and statement custody is not opened.** No screenshot, no print-to-PDF, no
"save this page". Whether a downloaded statement becomes a **held** `Artefact` is not opened.

**F10 — The escape hatch is required.** *Open in my browser* sits beside every *Open bank*
button: the same link, `webbrowser.open`, the same F4 check. Its downloads reach the same F6
watcher.

**F11 — The Assistant gains nothing, and absence is not zero.** No tool, no action. S1 gains a
line saying it is now relied upon. The window records no coverage, and the button implies
nothing about *up to date*.

**F13 — Runtime currency, provenance and a safe failure. [R13]** Groundwork does not ship a
browser. It embeds the platform engine, and the platform keeps that engine current:

| OS | engine | who updates it |
|---|---|---|
| Windows | WebView2 **Evergreen** | Microsoft's Edge updater |
| macOS | WKWebView (system WebKit) | macOS / Safari updates |
| Linux | WebKitGTK (`webkit2gtk-4.0` / `4.1`) | the distribution's packages |

The contract:

1. **Groundwork never ships, pins, bundles, updates or fetches a browser engine.** No
   fixed-version WebView2 (`WEBVIEW2_RUNTIME_PATH` stays `None`), no CEF, no Qt WebEngine, and
   no *"check for browser updates"* feature. That would be a second outbound update path inside
   the privacy boundary, and the wrong abstraction. What Groundwork says instead is: *I use your
   operating system's supported web runtime. If it can't give you a usable bank window, use your
   normal browser.*
2. **The bank process pins its backend and refuses every other.** It passes `gui=` explicitly
   (`edgechromium` / `cocoa` / `gtk`), **ignores `PYWEBVIEW_GUI`** and `KDE_FULL_SESSION`, and
   after initialising **checks the renderer it actually got**. On Windows,
   `renderer == 'edgechromium'`, never `mshtml`. Anything else exits before loading the URL.
   **The measured defect this closes:** without WebView2, pywebview today would open the
   user's bank in **IE11's engine** with only a log line. A bank page must never meet that
   fallback. (The main window has the same fallback; that is recorded, not changed here.)
3. **Unavailable means say so and offer the browser.** When the engine is missing, refused or
   fails to start, the main window says *"Groundwork can't open your bank here on this
   computer"* and shows **Open in my browser**. There is no silent switch, no retry on another
   engine, and no download. F10's escape hatch is therefore the **compatibility guarantee**,
   not a convenience.
4. **What Groundwork does not certify:** that the runtime is *current enough for a particular
   bank*. Banks change their requirements on their own schedule. The guarantee is **runtime
   provenance and a safe fallback**, not *this will always work with every bank*. Groundwork
   sets no version floor of its own beyond refusing the MSHTML path; a floor would be a claim
   it cannot keep.
5. **A runtime update must not need a Groundwork update.** Because nothing is pinned, an
   Evergreen, macOS or distro engine update reaches the bank window with no action from
   Groundwork. Bw18 measures that rather than assuming it.

### What the window forces onto the server

**F12 — The local server hands its session token to any page that reaches it. Pre-existing;
a precondition for this build.** `/` serves `index.html` with `window.GW_SESSION_TOKEN` written
into it, and nothing checks the request's `Host`. A normal cross-origin page cannot read that
response. A **DNS-rebinding** page can: a name that resolves to a public address, then to
`127.0.0.1`, on port 8765, makes the page same-origin with Groundwork. It reads the token,
and every `/api/*` route is open to it.

That is true **today** of every page the user visits in their own browser; whether current
browsers' private-network protections block it on every OS is **not measured**. The bank
window does not create the gap. It does make Groundwork itself the thing that opens arbitrary
web pages, which is why F4 cannot be the defence. The origin F4 permits (`https`, port 443)
can never be same-origin with `http://127.0.0.1:8765`. But the page can navigate anywhere
after loading, and the user's normal browser was never bound by F4 at all.

**The fix belongs on the server:** `before_request` rejects any request whose `Host` is not
`127.0.0.1:8765` or `localhost:8765`, the token-bearing `/` included, and `/api/*` rejects a
present `Origin` that is not the same. It is small, but it is its own change with its own test,
and it should land **before** the bank window ships. It is recorded here and flagged separately.

---

## 4. Readings

- **N**: build nothing; the watcher already serves the user's own browser.
- **W**: as §3: a separate bank process, per-account links with one source of truth, the F4
  syntax contract with no DNS claim, F5 exclusion, the F6 folder resolver and Bw9 as
  acceptance, the F7 machine, private sessions, no captures, the escape hatch as the compatibility guarantee, F13's pinned
  runtime, **F12 first**.
- **W+**: persistent sessions or captures. **Refused** (F8, F9).

---

## 5. Cases

| # | situation | expected |
|---|---|---|
| Bw1 | checking account with a link; QFX downloaded to Downloads | offered; preview only on *yes*; nothing committed until the user commits |
| Bw2 | card linked to an Account | one link, stored on the Account; a write to the card's `portal_url` is refused by the server |
| Bw3 | card unlinked | its own link and button |
| Bw4 | linking two rows whose links differ | the user chooses; nothing picked silently |
| Bw5 | no link | no button; nothing guessed from `institution` |
| Bw6 | `http://…` · `https://u:p@bank.com` · `https://bank.com:8443` · `https://127.0.0.1` · `https://localhost` · `https://nas.local` · `https://intranet` · `javascript:` · `file:` | refused on save **and** at launch (a value planted directly in the database is refused too) |
| Bw7 | statement PDF downloaded | offered; **no extraction and no model call** until *yes* (asserted: the offer path reaches neither `pdf-extract` nor a provider) |
| Bw8 | a `.zip` or `.exe` downloaded | ignored; never offered |
| Bw9 | **acceptance**: a real download on WebView2, WKWebView and WebKitGTK, default dialog folder, including a relocated / localised Downloads | offered. Saved elsewhere: not offered, and the footer said so |
| Bw10 | **the crossing test**, §5.1 | every mutation fails the section |
| Bw11 | same bank opened twice · URL edited while open · account deleted · Groundwork quit | F2's table |
| Bw12 | sentinel URL planted | absent from every prompt, provider body, snapshot, narrator input, finding, export, log line and the update ping; present in a backup |
| Bw13 | the bank refuses embedded engines | *Open in my browser* works; its download is offered |
| Bw14 | same file downloaded twice | the existing `seen` dedup; one offer |
| Bw15 | restart, reopen the bank | signed out; two-factor again (F8, by design) |
| Bw17 | WebView2 absent (Windows), or a backend forced by `PYWEBVIEW_GUI=mshtml` / `qt` | the bank process refuses to load the URL; the main window says so and offers *Open in my browser*; **no network request** is made by Groundwork for an engine |
| Bw18 | **acceptance**: on each OS, record the engine and version the bank process actually used; update the runtime by the platform's own mechanism (Edge updater / macOS update / distro package) and reopen | the bank window works on the new runtime with **no Groundwork rebuild**, and the recorded version changed |
| Bw16 | F12: a request with `Host: evil.example:8765` to `/` and to `/api/…` | refused; no token in the body |

### 5.1 The crossing test's mutations [R10] [R11]

A smoke section inspects the bank entrypoint and its launcher. Each mutation below, applied
alone, must fail it:

1. `js_api` set on the bank window
2. any `evaluate_js`, `run_js`, `get_elements`, `get_cookies`, `load_html` or `load_url` call reaching the bank window (credential fill, DOM read, cookie read)
3. an automation action: any timer, event handler or loop in the bank process that acts on the page
4. the bank process importing `server`, `core`, the token, the database or `GroundworkAPI`
5. anything besides the URL passed to the bank process (account name, id, balance)
6. **downloaded file content made available to the bank process or page**
7. a download handler that delivers a file to Groundwork **other than** by the filesystem into the watched folder (e.g. POSTing to the queue directly)
8. `ALLOW_DOWNLOADS=True` in the main process
9. `private_mode=False` or a `storage_path` in the bank process
10. the link added to a provider payload, snapshot or export (the Bw12 builders)
11. the bank process accepting a renderer other than its pinned one (`mshtml`, `cef`, `qt`), or reading `PYWEBVIEW_GUI`
12. **an alternate engine made reachable**: a fixed-version WebView2 path set, a CEF / Qt WebEngine import, or any code path in Groundwork that fetches or installs a browser engine or checks for engine updates

---

## 6. Candidate, recommendation, ruling sought

**W**, with **F12 landing first** as its own change. The build, once authorised:

1. **F12**: Host / Origin check on the server; Bw16
2. `portal_url` on `Account` and `DebtAccount` (`migrate.py` `_add_missing_columns`); the F3
   write invariant; the F4 check on save and at launch
3. the link field with F4's copy in each account's settings; a linked card displays its Account's
4. `--bank-window` dispatch in `launch.py` before anything else starts; URL on stdin; one child
   per account, tracked and terminated per F2
5. *Open bank* + *Open in my browser* on each account with a link
6. the F6 download-folder resolver shared by the watcher and the copy; event handlers only where
   Bw9 shows the gap; `.pdf` offered per F7
7. the crossing section (§5.1) and Bw12's exclusion test
8. F13: `gui=` pinned in the bank process, the renderer check, the *can't open here* message
   with *Open in my browser*
9. Bw9 and Bw18 on all three OSes, **as acceptance**
10. privacy copy: *the bank's page loads straight from your bank; Groundwork sees only the file
   you choose to download.*

**Not in the build:** SimpleFIN · persistent sessions · captures · statement custody · a bank
list · any Assistant action · changing the offer's 60 s expiry.

**Ruling sought:**

1. **W with F12 first**, or F12 alongside?
2. **F1**: the separate bank process (and the second Dock icon on macOS)?
3. **F3**: the write-enforced single source; ask on a conflicting link; **unlinking copies nothing**?
4. **F4**: no explicit ports, no IP literals, no DNS claim, and the stated non-guarantee?
5. **F6**: the shared folder resolver, and Bw9 as acceptance?
6. **F13**: the pinned backend with MSHTML refused, no version floor beyond that, and Bw18 as
   acceptance?

---

## 7. Ruling — Rob, 2026-09-23

**W stands, and is not reopened.** The code findings sharpen its implementation boundary. Only
F12 is **sequenced before** W; everything else is part of W's build and acceptance evidence.

| finding | ruling |
|---|---|
| **F12** server Host / token | **first.** F12 fix → its gate verified → then build W. It stays a separate task: a prerequisite, not an expansion of W |
| **F1** separate bank process | **accepted**, and made an **invariant**, not an implementation detail |
| **F3** unlinking a card | **the card's `portal_url` becomes empty** |
| **F4** URL limits | **adopted**: `https` only, no custom ports, no raw IP addresses, no claim about destination identity |
| **F6** downloads folder | **one OS-resolved folder for both the dialog and the watcher, plus a real test on all three OSes** |
| **F13** runtime | **one supported engine per OS; known legacy fallbacks refused; no Groundwork engine or update system** |

**F1: the bank process's shape, as an invariant.**

```text
URL in → bank WebView → user interaction → user-selected download → filesystem
```

and never *URL + server + database + Groundwork session + API bridge*. The bank process has:
no Groundwork server · no database · no session token · no `js_api` · no Groundwork API
endpoint · no financial-data payload. The second engine start and the macOS Dock icon are
accepted costs of the boundary.

**F3: the link's owner.**

- a linked card shares the Account's one URL;
- a standalone card owns its own URL;
- **unlinking empties the card's URL.** Nothing is copied, so the old relationship leaves no
  plausible-looking destination without a semantic owner;
- relinking does not resurrect an old URL;
- two existing links that disagree when linked: the user is asked; Groundwork never picks.

> **A portal URL belongs to the currently represented account relationship, not to historical
> linkage.**

**F4: validation is syntactic.** Groundwork says, in effect: *I will open the HTTPS address you
supplied. I do not verify that it belongs to your financial institution.* It **does not resolve
the host** to make a security determination about where it points. Groundwork is not an
institution-identity verifier.

**F6: acceptance.** The dialog's start folder and the watched folder derive from the **same
OS-level source**, never two independently computed concepts. *On Windows, macOS and Linux, a
bank download saved to the system's default Downloads location is observed by the existing
review pipeline*, **including a moved / non-default Downloads location where the platform
permits one.** **Until that real-backend test passes, W is not complete.**

**F13: "no minimum version" does not mean "any version is acceptable."** The requirement is to use
the supported platform runtime and never silently fall back to a legacy engine Groundwork has
determined is unacceptable. On Windows, **WebView2 is accepted and IE11 / `mshtml` refused**.
On macOS and Linux, the platform's native WebKit. No Groundwork-specific minimum browser
version: that would make Groundwork a browser-compatibility authority it cannot maintain.
Runtime unavailable → **refuse embedded mode → offer Open in my browser.** The runtime test
must exercise the **actual installer behaviour**, especially on Windows:

- WebView2 present → the bank window uses WebView2;
- WebView2 absent → **no IE11 fallback**;
- no browser-engine download by Groundwork;
- no alternate engine silently substituted;
- the browser escape hatch still available.

**Preserved in the record, verbatim:**

> **Groundwork does not promise that a bank will work with the embedded engine; it promises only
> that it will not silently substitute an unsupported/legacy engine, and it always provides the
> user's normal browser as the escape path.**

**Next:** the F12 server fix, as its own task, to its own accepted gate. **W's build is not started
until then.**
