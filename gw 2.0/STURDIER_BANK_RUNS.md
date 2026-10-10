# Item 70 — Sturdier bank runs: record the route, and sign out before closing

Opened 2026-10-10. Rob, on what is left of the automation: *"yes write up 1 and 2"*. Those are:
1. **Record the route** (item 57's A12, proposed 2026-10-09, never ruled). Rob had asked the day before: *"should the
   agent go grab the site layout for the user. That way when we have the user instructs the agent we don't get lost
   on that issue."*
2. **Sign out before closing** (offered 2026-10-09, when the window first started closing itself).

**Already decided (not reopened):** the person starts every visit (TM2); the window always closes when a run ends,
except at a bill's payment screen (item 68 B8 (b)); nothing is read or recorded beyond what A5 allows; a bank's bot
check stops everything (A6); the agent never explores a site on its own (Rob, 2026-10-09: grab the layout from the
user's own recording, never by crawling).

**R1–R6 RULED 2026-10-10 (Rob: "approve R1–R6 as recommended"); R4 builds nothing. BUILT 2026-10-10 (Rob: "build
item 70"):** `clean_path` / `clean_signin_at` / `same_site`; the recorder notes every step's page and a sign-in's
address in `note()`; the driver opens the recorded sign-in once (`open_signin`, the window refusing anything not https,
off the link's site, or masked) and a page_changed stop carries the bank's path; "Show Groundwork again from step N"
(`from_step`, the kept steps joined in the review); `Driver.sign_out` / `window.__gwSignOut` after SIGN_OUT_AFTER, the
batch waiting for each window to close; s182. **One refinement, said here:** R1/R2 mask a path segment only when it
could be an identifier (a digit and six characters or more, or four digits running), not every number, because
masking `/v2/` would make the sign-in address unusable; an address with anything masked is shown but never opened.
Awaiting the gate and a real run on Superior CU.

## 1. What is true today (fix branch, 4b22637)

- **A recorded step is a control's name and role** (A5), with digits masked; a sign-in is "sign in", with no
  values. Nothing records where a step happened.
- **The fetch opens the account's link** and runs the steps from there. When the sign-in lives in a hidden frame
  (Superior CU's homepage), it fails until the person changes the link by hand. That is what happened on 2026-10-09,
  fixed by pointing the link at `online.superiorcu.com`.
- **A stop says which step, not where the bank was** ("Stopped: the page didn't look as recorded at step 3").
- **Re-recording replaces every step**, even when only the last one changed.
- **How the agent presses a control is already decided per element** (`press()`: a native button gets a click, a
  styled one gets the full mouse press), so the control's kind needs no recording.
- **When a run ends, the window closes 8 s later** with the bank session still signed in. With "Remember this
  computer" on, the bank's own cookies stay in the device folder until the bank expires the session.

## 2. Points for ruling

**R1. Where the sign-in really is.** While recording, when the person signs in, Groundwork notes the **address of the
page where the password box was**: the site and path only. No query, no fragment, and every number masked
(`https://online.superiorcu.com/auth/login`). On a run, if the account's link doesn't lead to a sign-in or to the
first step, the agent opens that recorded sign-in address once and carries on. It only does this when the address is
**https and on the same site as the link** (`superiorcu.com` for `www.superiorcu.com`), so a recording can never send
the agent somewhere else. The steps list shows it: *"Sign in (at online.superiorcu.com/auth/login)"*.
*Recommended.*

**R2. Where each step happened, for clearer stops.** Each recorded step keeps the path of the page it was taken on,
masked the same way. It is used only to say where a run stopped: *"Stopped at step 3 (Download): the bank was on
/auth/login, not /accounts/history - it may have signed you out."* The agent never jumps to a recorded address
except R1's sign-in. Deep-linking past the bank's own pages is what bot checks watch for.
*Recommended.*

**R3. Show me again from here.** When a run stops at step N because the page didn't look as recorded, the stop offers
**"Show Groundwork again from step N"**. The recording window opens (signed in by the person, as when recording);
they do the rest of the download. Steps 1 to N−1 are kept, and the new steps replace N onward. The review shows the
whole list, old and new, before anything is saved (A5, unchanged).
*Recommended.*

**R4. The control's kind: not recorded.** `press()` already reads each element at run time and presses it the way it
needs. Recording the kind would add a field that could only go stale.
*Recommended: nothing to build.*

**R5. Sign out before closing.** When a run ends with a download, a bill read, nothing downloaded, or a stop the
person can fix (the page changed, no code entered), the agent looks on the page for a control named **Sign out /
Log out / Log off** and presses it, waits up to 5 s for the bank to finish, then closes the window. The panel says
which: *"Signed out of Superior CU"*, or *"Groundwork couldn't find Sign out; your bank will end the session on its
own."*
- **Not after a bot check:** a stop there means touching nothing more (A6).
- **Not at a bill's payment screen:** the window stays with the person (item 68 B8 (b)).
- **"Remember this computer" is unaffected:** signing out ends the session, and the bank's trust in the device stays.
- **A sign-out hidden behind a menu.** If the person clicks the menu and then Sign out while recording, those clicks
  are kept as the run's last steps ("only at the end") and used the same way.

*Recommended.*

**R6. Tests.**
- R1: the sign-in address is masked; one taken from a different site is refused; it is opened at most once per run.
- R2: the stop names the expected and the actual path; no step navigates by address.
- R3: steps before N are kept; the review shows both parts.
- R5: Sign out is pressed after each allowed ending and never after a bot check or at a payment screen; the panel
  says which.
- A crossing check: the recorded address is never a query string or a number.

Master only. One real run on Superior CU before acceptance.
*Recommended.*

## 3. Not decided here

- **Groundwork paying a bill** (item 68 B8 (c)): revisited after "can I pay this?" and "paid?" have run on real
  accounts.
- **Exploring a site on its own:** ruled out (item 65 AP7; Rob 2026-10-09).
