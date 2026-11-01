# Mac build check, 2026-10-31

Rob: *"open groundwork on the mac .. lets test it for memory leakage and possible security issues. Make a full list
of issues."*

The build tested is `/Applications/Groundwork.app`, built today from `61541c3` (PyInstaller 6.22.3, Python 3.12.10,
ad-hoc signed) on the M2 with 8 GB. Memory was measured on a scratch copy holding the sample household. The security
probes ran against the running app over `127.0.0.1:8765`. The script-injection test ran against the dev preview's
throwaway database.

## Memory: no leak found

| Test | Start | End | Threads / open files |
|---|---|---|---|
| 12 rounds over the 124 read-only API routes, plus all 39 report sections, AI off | 120 MB | 126 MB (flat from round 1) | 17-18 / 139-143, steady |
| 50 more rounds, AI on | 3,047 MB | 3,039 MB | 20 / 152-154, steady |
| 15 assistant questions in a row (7-13 s each) | 3,002 MB | 3,036 MB (flat from question 2) | - |
| 10 questions sent at once | 3,040 MB | 3,047 MB, all done in 41 s | 30 while busy, back to 20 |
| AI off and on, three times | off: 162 / 165 / 167 MB; on: 3,017 / 3,014 / 3,013 MB | the model is released each time | 20 |

Turning AI off gives the 2.9 GB model back. What stays behind grows about 2-3 MB per off/on cycle, which is too small
to matter. The app stayed answering other requests while 10 questions were queued.

**Not measured:** the window's own WebKit process over a long session, voice (Talk needs a person at the microphone),
the bank windows and the bank agent, and Windows.

## Issues, most serious first

### High

1. **Opening Groundwork from Applications, the Dock or Finder hangs it.** No window appears, and the server stops
   answering about a second after it starts. It happens every time on this build and never on the 24 October build.
   It does not happen when Downloads is moved elsewhere, so the trigger is the Downloads watcher
   (`launch.py: _start_downloads_watcher`). macOS asks again for permission to read Downloads because each ad-hoc
   build has a new signature. While it waits, every thread in the app waits too: the sample showed all of them stalled
   on Python's global lock. The prompt may be sitting unanswered on the Mac's screen. *Fix:* start the watcher on its own thread
   after the window is open, so a permission prompt can never freeze startup. Also sign with a stable Developer ID
   (issue 5), so macOS remembers the answer between builds.
2. **Any program on the Mac can take the access key and read or change everything.** `GET http://127.0.0.1:8765/`
   needs no key and returns the page with `window.GW_SESSION_TOKEN` written into it. With that key,
   `/api/accounts` (and every other route) answered 200. A script, a browser helper or another user signed in to the
   same Mac can do this, since `127.0.0.1` is shared by all of them. The Host, Origin and DNS-rebinding guards all held:
   a web page cannot get in. The gap is only another program on the Mac. *Fix:* stop serving the key over HTTP. Hand it
   to the window directly (pywebview `evaluate_js` or the `js_api` after load), or put a one-time launch secret in the
   window's URL and trade it for an HttpOnly, SameSite=Strict cookie, refusing the page without it.
3. **Script injection through account and debt names (confirmed).** An account or debt named with HTML (for example
   `<img src=x onerror=…>`) runs as code when the Ledger opens: 4 runs in the test. The code escapes these names nearly
   everywhere, but these dropdowns skip it:
   - `static/js/app.js:3470`, the Ledger account filter, built from account names;
   - `app.js:6034` (*Select account…*);
   - `app.js:33297`, the Investments account filter.
   The other 13 main pages and the report builder did not run it. There are 25 `<option>` lists and about 46 template
   spots that print record text without `esc()`. Most hold fixed words, but each should be checked. Injected code would
   hold the access key and could send data off the Mac, because the page has no Content-Security-Policy (issue 4).
   Names can come from imported files and the bank agent, not only from typing. *Fix:* `esc()` on those three lines, a
   sweep of the rest, and the CSP.

### Medium

4. **No Content-Security-Policy and no frame protection.** The page carries no `Content-Security-Policy`,
   `X-Frame-Options` or `X-Content-Type-Options` header. Any web site open in the browser while Groundwork runs can
   load Groundwork in a hidden frame and trick a click (clickjacking). Nothing limits where injected script may send
   data. *Fix:* `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; connect-src 'self'` (inline
   scripts need a nonce or hash) and `X-Content-Type-Options: nosniff`.
5. **The build is not signed for anyone else.** It is ad-hoc signed, with no Team ID, no hardened runtime and no
   notarization. `spctl` rejects it, so on any other Mac Gatekeeper blocks it. It also loses its macOS permissions on
   every rebuild, which is the cause of issue 1. *Fix:* a Developer ID certificate, the hardened runtime with only the
   entitlements llama.cpp and WebKit need, and notarization.
6. **Every HTTPS call from the built app fails.** The update check, airfare, trip geocoding and prices all log
   `CERTIFICATE_VERIFY_FAILED`, and have since at least 20 October. The bundle carries no certificate list (certifi is
   not in it), and the frozen Python cannot find the system's. So users never hear of an update. Nothing falls back to
   an unchecked connection (no `verify=False` anywhere), which is right. *Fix:* bundle certifi and build each
   `urlopen` context from `certifi.where()`.
7. **Files beside the web folder are served without the key.** `/core/database.py`, `/bank_importer.py`,
   `/LICENSE` and the 2.3 GB `/models/phi3.5-mini-instruct-q4.gguf` all answer 200 (`server.py:323`, the
   "assets folder" branch serves the whole Resources folder). It is GPL code, so nothing secret leaks, but any web page
   can make the browser pull the 2.3 GB model over and over. Path tricks (`../`, `%2e%2e`) were refused. *Fix:* serve
   only `static/` and the named icons.

### Low

8. **`/api/health` needs no key** and tells any caller the version, the Python version, the platform and the session
   id. *Fix:* reduce it to `{ok: true}`.
9. **The build is stamped with an old version.** The log says `Groundwork 20261008-d25`, and Info.plist says 1.1.1, the
   same as the 24 October build. The update check and support logs cannot tell the two apart. *Fix:* bump
   `version.py` per build.
10. **The new build has no Groundwork icon.** It shows PyInstaller's default (`icon-windowed.icns`).
    `assets/groundwork.icns` is not in the repo; `build_icns.py` makes it. *Fix:* run it before building, or commit the
    `.icns`.
11. **An AI chat can still crash on an over-long prompt.** `core/engine.py:446-454`: with `stream=True`,
    llama.cpp raises the "exceed context window" error on the first chunk, which is outside the `try`. The log shows it
    twice on 25 October (`/api/ai/chat`, 2,787 tokens against 2,048). Today's length check caught a 15,000-character
    prompt cleanly ("That request is longer than the local AI model can read at once"), so only a prompt just under the
    check's estimate gets through. *Fix:* move the `for chunk in pieces` loop inside the `try`.
12. **The data on disk is not encrypted.** `groundwork.db` and the upgrade backups are plain SQLite, mode 644, inside
    `~/Library/Application Support` (mode 700). Other users cannot reach them, but any program running as you can. This
    is usual for desktop apps; FileVault is the protection. These backups are plain `.db` files, not sealed `.gwbk`.
13. **Each assistant question starts a thread, with no cap.** Ten at once were fine (41 s, threads returned). Only
    reachable through issue 2. *Fix:* one worker and a queue.
14. **The build needed things it could not find.**
    - PyInstaller was not installed in `gw-engine-venv`.
    - The pinned model was not in `vendor/`; `GW_MODEL_PATH` and `GW_WHISPER_PATH` were pointed at the installed app's
      copies.
    - The automatic signing step failed on extended attributes (`xattr -cr` and then `codesign -s -` by hand).
    *Fix:* a `build_macos.sh` that does all of that.

## Fixed, 2026-10-31 (Rob: *"Fix all 14"*)

The gate: 4,098 passed, 0 failed, with a new section, `smoke_sections/s270_mac_check.py`, that tests each fix. The
new build, `dist/Groundwork.app` (CFBundleVersion `20261031.2122-61541c3+`), was then opened with `open`, the same
route Finder and the Dock take, and probed from outside.

| # | Fix | Checked on the built app |
|---|---|---|
| 1 | The watcher starts on its own thread after the window shows, and reads Downloads with `os.listdir` (which releases Python's lock while it waits) before watching. Info.plist says why Downloads is asked for. | The window opened. macOS's Downloads question came up, and only the watcher thread waited on it (`sample`: `os_listdir → __opendir2`). The app answered in 1-5 ms the whole time. |
| 2 | The page needs a page key. The window opens on `/?k=<key>`, which trades the key for an HttpOnly, SameSite=Strict cookie kept in the window's private store. Without either, `/` is a 403 with no token in it. | From outside: `/`, `/index.html` and a guessed key are all 403, and no token is in any body. From the window: the page loaded and recorded its app-open with the token 4 s after start. |
| 3 | `esc()` added to the three dropdowns, the three typed-name lists (`accountList`, `categoryList`) and every pop-up message (`showToast` now escapes its title and line, which covers every caller that prints a name; none passes markup). A sweep of the other `<option>` lists and the template spots that print names found only fixed words or text already escaped. | The dev preview's injected accounts showed as text on the Ledger and Investments pages: 0 runs, 0 injected images. |
| 4 | Every response carries `Content-Security-Policy` (`connect-src 'self'`, images, fonts and media from itself only, `frame-ancestors 'none'`, `base-uri 'none'`, `form-action 'self'`), plus `X-Frame-Options: DENY`, `nosniff` and `no-referrer`. Inline script stays allowed, since the page uses about 580 inline handlers. | Present on the page, the API and static files. No CSP errors in the preview. |
| 5 | `build_macos.sh` signs with the hardened runtime and `entitlements_macos.plist` (executable memory and the microphone only) when `GW_SIGN_IDENTITY` names a Developer ID, and notarizes when `GW_NOTARY_PROFILE` is set. | **Not done.** This Mac has no Developer ID certificate (`security find-identity`: 0 valid). Until there is one, builds stay ad hoc, and macOS asks again for Downloads after each rebuild. With fix 1 that question no longer freezes anything. |
| 6 | certifi ships in the bundle, and the launcher points `SSL_CERT_FILE` at it before anything connects. Verification stays on. | The update check ran after the page loaded and nothing failed. Every start before this one had logged `CERTIFICATE_VERIFY_FAILED`. |
| 7 | Only `static/` and three named icons are served. Any other path is a 404. | `/core/database.py`, `/server.py`, `/bank_importer.py`, `/LICENSE` and the model are all 404. |
| 8 | `/api/health` without the token is `{"ok": true}`. The heartbeat sends the token and gets the version, build and session. | `{"ok":true}` from outside. |
| 9 | A build stamp (`date.time-commit`, `+` when uncommitted changes exist) goes into CFBundleVersion, `build_info.json`, the start-up log line and `/api/health`. `GW_VERSION` is unchanged: it is the release stamp `Website/version.json` advertises, so it moves only with a release. | Log: `Groundwork 20261008-d25 (build 20261031.2122-61541c3+) starting`. |
| 10 | `assets/groundwork.icns` is made from `groundwork_256.png` and committed. | Info.plist names `groundwork.icns`. |
| 11 | The stream loop in `core/engine.py` is inside the `try`. | s270 runs a fake model that refuses on its first chunk: the result is the too-long answer, not an exception. |
| 12 | The launcher sets umask 077, and existing data files, backups and logs are made 600 at start. Not encryption: FileVault is still the protection. | All of them are 600 after one start. |
| 13 | At most 4 assistant questions at once. A fifth gets a 429, "still answering earlier questions". | s270. |
| 14 | `./build_macos.sh` installs PyInstaller and certifi if they are missing, finds the models (env, `vendor/`, or the installed app's copies), makes the icon if it is absent, and signs. Signing happens in a copy under `/tmp`, because iCloud syncing of Documents puts Finder info back on the bundle as fast as `xattr -cr` removes it. That was the "detritus" refusal. | Used for this build. |

**Side effects to know.**
- `dev_server.py` turns the page gate off. It runs on a throwaway database and is opened from an ordinary browser.
- `python server.py` prints the address with the key.
- `engine_8gb_test.py` reads the token from a running app's `/`, and no longer can; that is the point of fix 2. Pointed at `dev_server.py`, it still works. The scripts that import `server` in-process are unaffected.

### Seen, no action

- `pip-audit` on the build environment flags `diskcache` 5.6.3 (PYSEC-2026-2447, pickle in its cache folder). It comes
  with llama-cpp-python and is **not** in the app bundle. Nothing else is flagged.
- No `shell=True`, `eval`, `pickle`, YAML or SQL built from strings was found in the server and core code. The one XML
  parser (`core/per_diem.py`) reads the GSA file over HTTPS. `open_external` opens only `http(s)`, and `tel:`/`sms:`
  with digits. Files appearing in Downloads are offered, never imported without a Yes.
- Old and new builds against the same database: opening the 24 October build re-stamps the schema, so the next start
  of the new build migrates and backs up again. Four backups came from today's testing.

## What I changed on the Mac

- `pyinstaller` and `pip-audit` added to `gw-engine-venv`.
- The new build in `/Applications`. The old one is on the Desktop as `Groundwork-old-2026-10-24.app`; the database
  copy before the upgrade is `backups/groundwork-before-2026-10-31-build.db`.
- The test copies have been stopped. The dev preview's throwaway database still holds the injection test records.
