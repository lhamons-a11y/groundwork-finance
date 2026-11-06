# Security audit, 2026-11-05

Rob: "The goal is to make this software as secure as possible." A read-only review of the code and of this PC's data
folder. No attack was run. Mac and Linux behaviour, the website and the voice features in depth were not reviewed, and
no dependency scan was run (the last one recorded is 2026-10-31, `MAC_BUILD_CHECK_2026-10-31.md`).

## Fixed (Rob: "Yes let's fix 1 and 3 first"; s287)

### Gap 1: a saved bank password had no site check

The fetch filled the saved login into any page with a password box and pressed submit, and followed a sign-in frame to
any https address to do it. A bad redirect or a compromised page would have received the password.

Now a login is sent only when the window's own address (`get_current_url`, read from the window, because anything the
page says about itself passes through the page's own JavaScript) is https on the site of the account's link or of a
sign-in the person recorded. The script that carries it also checks `location.hostname` with `===`, in case the page
moved after that check. A login box anywhere else stops the run as `other_site`, with nothing sent and the window left
to the person. The username step is no longer given the password. `same_site` no longer treats two names under a shared
ending (`bank.co.uk`, `evil.co.uk`; two `github.io` sites) as one site.

**What could change for a real bank:** a bank whose sign-in sits on another company's site, in a frame, with no sign-in
recorded there, now stops at that page instead of filling it. Recording a sign-in there allows it. **Needs a real bank
run; none has been done with this guard.**

### Gap 3: injected script could still send data out

The page's policy stops fetch, images and forms. It cannot stop script handing an address to the system browser or
walking the window to another site, and an address can carry data. A comment in `server.py` said script had "nowhere to
send data". That was wrong, and it has been corrected. Reaching this needed script injected into the page first; no way
to do that has been found (2026-10-31 sweep).

`link_guard.py` now decides, in Python:

| Way out | Now |
|---|---|
| `open_external` to a site the page itself links to, or a help line's digits | opens |
| `open_external` to anything else | waits for the person's Yes, in a window dialog showing the whole address |
| anything that could be read two ways, or is not a web address | refused |
| `window.open`, `target=_blank` | the same road: pywebview's `webbrowser.open` now goes through `open_external` |
| the main window going elsewhere (`location=`, a plain link) | **Windows, Mac:** cancelled before anything is sent. **Linux:** brought back after the page loads, which is after the request has gone |

Measured on a real WebView2 window with a throwaway local page: `location=` and a plain link stayed home, `window.open`
and an unknown address reached the question and did not open, a known address opened, a `file:` address did not, and the
window's own pages still worked.

Mac, 2026-11-06 (Rob: "Yes, build it"; `launch._hold_window_mac`, s287): measured on a real WKWebView window with a
throwaway page with no policy of its own, so only the guard stood in the way, and a listener recording every request
that reached it.

| Step | Without the guard | With it |
|---|---|---|
| `location=`, plain link, form post, iframe, download link | all 5 reached the listener | none did, window stayed home |
| `file:`, `data:` | nothing reached it | nothing reached it |
| `target=_blank` | handed to `open_external` | handed to `open_external`, nothing sent |
| `window.open` | nothing | nothing |
| the window's own page, its own `blob:` page | worked | worked |

On a Mac this also holds frames and downloads, which WebKit asks about through the same question. Not yet run in the
built app: the next Mac rebuild should confirm the app opens and works as usual.

## Open

**From gap 3:**
- **Linux navigation.** It needs the same cancel as Windows and the Mac, built and tested on a Linux machine.
- **A bank window as a way out.** Script holding the token can save a bank link and open a bank window at it. The window
  is visible to the person, but the address carries data. Not closed here.
- **WebRTC.** `connect-src` does not cover it in every browser engine. Not tested.
- **1.x.** `open_external` on `lts/1.x` is unguarded. Item 32 L1 admits security fixes to 1.x, built there first; this was
  built on master first. Rob to rule on the port.

**Not started:**
- **Installers are unsigned.** No signing step in `build.bat`, `deploy.bat` or the specs, and no Developer ID (2026-10-31).
  Users cannot verify a download, and a hacked website could offer a fake one. A cost decision for Rob.
- **Deleted data is not gone.** Safety copies are plain until backup protection is set up, including the full copy made
  before "Delete all". This PC holds 18 plain `.db` copies back to June, 12 of them pre-delete.
- **The live database is plain.** Recorded and deferred (`PERFECT_BACKUP.md`, `HEALTH_PRIVACY_H6.md`). It would help with
  a stolen disk or copied files, not with a program running as the same account. Checking for disk encryption and
  suggesting it follows the supported-OS rule: warn, never block.
- **What Groundwork keeps that identifies someone.** Medical bill and collection account numbers as typed, card last four,
  employers, health provider names, and a remembered-device browser folder per bank account where ticked. So the website
  should not claim Groundwork keeps no identifying material. `groundwork.log` holds statement-style file names, which can
  contain account digits. `voice_miss_log.jsonl` (rejected AI text) has no size limit in the code read.
- **Smaller.** No request size limit (the token is needed anyway). `flask-cors` is listed and unused. Most dependencies
  have loose ranges and no hash pinning. Vulnerability scanning is not in the gate.
