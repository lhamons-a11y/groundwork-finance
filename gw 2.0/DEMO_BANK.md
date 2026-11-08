# Item 117 — A demo bank, so the public can see "Get my accounts" work

Opened 2026-11-07. Rob, after the website gap review: *"One is having the AI get your accounts, now we would have to
simulate a website to make this happen but things like that we need to highlight and show the public how to do it."*
Then: *"Write it up."*

**D1-D10 RULED 2026-11-07 (Rob: "Accept all as recommended"), each as recommended.** Not built: the build waits on
Rob's word.

## 1. What is true today (master `c12a376`, 2.0.0)

**What the app does** (items 57, 67, 68, 69, 70, all built):
- **Show me once.** The person opens their bank inside Groundwork and does their usual download. Groundwork records the
  steps (each control's name and role, digits masked, no typed values) and where the sign-in page was (item 70 R1).
- **Get my accounts.** The header button, the dashboard's "last fetched" line, or the voice ("go get my accounts")
  visits each account with saved steps, one window at a time. It fills the login from the operating system's vault,
  replays the steps and saves the file to Downloads.
- **Codes are typed by the person.** When the bank asks for one, that window comes to the front with its bar, and the
  batch waits up to 5 minutes (`CODE_WAIT`). A code is never asked for or typed through Groundwork (item 67 G5).
- **A bot check stops everything** (`botCheck()`, stop reason `bot_check`). A click on anything that pays stops the run
  (`would_pay`).
- **Each file goes through the import review**, with its account already chosen by content hash (item 67 G6).
- **Bills read from the biller** (item 68): the same recording, on a bill's own site, reads the amount due and the due
  date from the places the person marked. It never presses Pay.
- All of it lives on **Coach → Assistant** (item 69), with Accounts and Bills tabs.

**What the website says about it:** one sentence on the home page and one paragraph on What's new
(*"Your statements, with one press"*), plus the Privacy page's description of the window. **There is no help
article, no screenshot and no video.** A reader can't see what "Show me once" means, what the window looks like, or what
happens when a code is asked for. The four tours (Ask, Health, Reports, Privacy) don't touch it.

**Why it can't be shown today:**
1. **Nobody can film a real bank.** A real sign-in, real account numbers and a real bank's look can't appear on a
   public site, and a recording against a real bank shows a real bank's pages.
2. **The window refuses anything local.** `bank_window.py:61-78` opens only `https://` addresses, with no port and no
   `localhost`, `.local`, `.internal`, `.lan` or `.home.arpa` host. So a demo bank served from the video machine
   (as `scripts/site_video/` serves everything else) can't be opened in the real window without weakening that check.
3. **The sample household has no bank link.** `core/sample_household.py` makes Everyday Checking and High-Yield
   Savings at *"Lakeside Credit Union"* with no bank website, so "Get my accounts" isn't shown in the sample (the
   header button appears only when an account has saved steps).

## 2. What it would be

A made-up bank on Groundwork's own website. Anyone with Groundwork can point the sample household at it, record
"Show me once", press **Get my accounts**, type the code the demo page shows them, and watch a statement come back into
the import review. The same site gives the video its scenes and the help article its screenshots. A made-up biller page
does the same for **Bills read from the biller**.

## 3. Points for ruling

**D1. Where the demo bank lives.**
- (a) **A path on the existing site:** `https://groundworkfinance.app/demo-bank/`, served by `Website/website.py`. It
  passes the window's https check as it stands. Nothing in the app changes.
- (b) A subdomain, `https://demo-bank.groundworkfinance.app`. Same effect, plus a DNS record and a certificate.
- (c) A local demo bank, with a dev-only exception in `bank_window.py` for `localhost`.

*Recommended: (a).* (c) puts a hole in the one check that keeps the window on real https sites, and an exception that
exists "only for the video" is the kind that ships. (a) is one more set of routes in the file Rob already publishes.

**D2. What it's called, and how it looks.**
- A name that can't be anyone's bank: **"Demo Credit Union"**, with *"Not a real bank. Made by Groundwork so you can
  try Get my accounts."* on every page. Its own plain look, nothing borrowed from any real bank.
- **The sample household's institution changes to match.** "Lakeside Credit Union" is a name real credit unions use.
  Inside the app nobody minded; on a public demo it would read as that bank.

*Recommended.*

**D3. Signing in.**
- Any username and any password work, and the page says so. A filled-in suggestion (`morgan` / `demo`) saves the
  reader thinking.
- The password still goes into the vault through Groundwork's own form, exactly as for a real bank. That's the point
  of the demo: it shows where the password lives.
- **Nothing typed is stored by the website.** The demo routes write nothing to the server: no log of usernames, no
  counter beyond the existing one-count-per-page-per-day.

*Recommended.*

**D4. The code step.** After the sign-in, the demo asks for a 6-digit code, and **shows the code on the same page**
(*"A real bank would text this to you. Here it is: 482 913"*). The window comes to the front with Groundwork's bar
(*"Your bank is asking you something"*), and the person types it. This shows the one thing people most need to see:
Groundwork waits for them and never reads the code.
- A **"Remember this computer"** box on the demo, so the second run skips the code, as a real bank's does (item 57 A7).

*Recommended.*

**D5. The pages and the download.** A sign-in page, the code page, an accounts list (Everyday Checking, High-Yield
Savings, the card), an account's activity, and a **Download** page with a date range and a format (CSV, OFX, QFX).
- **The files hold the Morgans' sample transactions**, made by the same seed as `core/sample_household.py`, dated
  from the day they're downloaded. Imported into the sample household, they meet the import review's duplicate check:
  most lines are already there, a few new ones are not. That's what a real second import looks like.
- Made by the website, never stored: each download is built on request from the seed.

*Recommended.*

**D6. The bot check, on purpose.** A link on the demo, *"See what happens when a bank asks 'Are you a robot?'"*,
opens a page carrying a check the agent recognises. The run stops and says why, and the batch doesn't carry on. It
shows a safety rule working, not just the happy path.

*Recommended.* It costs one page.

**D7. A demo biller.** `https://groundworkfinance.app/demo-bill/`: **"Demo Power & Light"**, signed in the same way,
with an amount due, a due date and a **Pay now** button that does nothing. The recording marks the amount and the date;
a run reads them into the Budget page's bills card; the agent stops at Pay now (`would_pay`). This shows *"Groundwork
never presses Pay"* happening.

*Recommended.*

**D8. Into the sample household.** When the sample is loaded, Everyday Checking and the card carry the demo bank's
address as their bank website, and the electric bill line carries the demo biller's. **No steps are pre-recorded**:
the person does "Show me once" themselves, because that's the part to learn.
- It's only in the sample. A household's own accounts never get a demo address.
- With no internet, the demo simply doesn't load, and the window says so as it would for any bank.

*Recommended.*

**D9. What the public sees.**
- **A fifth tour video, "Get my accounts"**, made by `scripts/site_video/make.mjs` from a new `fetch.json`: Show me
  once, the vault, Get my accounts, the code, the import review. About a minute, narrated and captioned like the
  others. Card on the home page and What's new.
- **A help article**, *"Get my accounts: fetch your statements with one press"*, step by step, with screenshots from
  the demo: set the bank website on the account; Show me once; save the login; Get my accounts or "go get my
  accounts"; when a code is asked; what stops a run and why; Remember this computer; Forget a login.
- **A second article for bills**, the same shape.
- **"Try it yourself"**, at the end of both: load the sample household, open Coach → Assistant, and the demo bank is
  already linked.

*Recommended.*

**D10. Lines and tests.** Master and the website only.
- A smoke section for the demo routes: every page says it isn't a real bank; the download's lines come from the seed;
  no route writes what was typed; the code page shows its code; the bot-check page carries a check `botCheck()`
  recognises.
- One real run in the app against the published demo, recorded before the video is made.
- The video and the help article go up together, after that run.

*Recommended.*

## 4. Not decided here

- **The rest of the website gaps** found on 2026-11-07 (the help pages describing 1.x onboarding and reports, the voice,
  Possible futures, protected backups, the sample household, open source, the empty changelog in preview). Each is
  small and separate; this item is only the demo.
- **Videos for voice setup and Possible futures.** They need no demo site; they're ordinary tours.
- **Showing the demo bank to people without Groundwork** (a web-only walkthrough). The video covers it.

## 5. Status

Opened 2026-11-07. **D1-D10 RULED the same day, all as recommended** (Rob: *"Accept all as recommended"*).

**BUILT 2026-11-07 (Rob: "Build it"):**
- **The lines, one source:** `core/sample_lines.py` holds the Morgans' everyday transactions; `core/sample_household.py`
  posts them as before (the same 223 transactions, checked by fingerprint before and after), and the website carries a
  byte-for-byte copy, `Website/sample_lines.py`. **Deploying the site now means uploading that file beside
  `website.py`.**
- **The demo bank** (`website.py`, `/demo-bank/`): sign-in (any login), the code page (today's code shown on it, a
  one-time-code box, "Remember this computer"), Accounts, each account's last 30 days, Download activity (range and
  CSV / OFX / QFX), and a security-check page the agent stops at. A download needs a sign-in. No route writes anything.
  Cookies: `democu_in` while signed in and `democu_device` only when remembered, each holding "1", on `/demo-bank` only.
- **The demo biller** (`/demo-bill/`): sign-in, the bill (amount due and due date beside their labels, due the 21st),
  and a Pay now that pays nothing.
- **Never indexed:** a noindex meta and `X-Robots-Tag` on every page, and robots.txt disallows both paths.
- **Privacy page:** a line on the two demo sites and their two cookies.
- **The sample household (D2, D8):** its bank is Demo Credit Union; Everyday Checking and the Cashback Visa are linked
  to the demo bank, the Electric line to the demo biller; nothing is recorded.
- **Found on the way, and fixed:** "Start with my own" deleted the database, but a login saved for the demo would have
  stayed in the computer's vault under the sample's ids, so a household's own account made later would show a saved
  login. A login saved while the sample is here is noted (`sample_vault_keys`, its own route only: the settings route
  drops it), and the clear forgets exactly those, and the sample's remembered-device folders. Nothing else in the vault
  is touched, so the gate's own sample runs can't remove a real saved login.
- **Checked:** s293 (14 checks). Every download reads back through Groundwork's own importer as the sample's own lines
  in all three formats, and imported into the sample household each line is held as "looks like one you have" (223 of
  223); clicked through in a browser at desktop and phone width.

**Found, not fixed (for Rob):** Groundwork's OFX reader keeps `&amp;` as written, so a bank that escapes "AT&T" as the
OFX standard says puts "AT&amp;T" in the ledger. The demo writes `&` plainly, as many banks do. Fixing the reader
changes how an existing ledger's escaped descriptions match the next import, so it's a ruling, not a quiet fix.

**Left:**
- Publish the site with `Website/sample_lines.py` (Rob's).
- One real run in the app against the published demo (D10): Show me once, Get my accounts, the code, the import review,
  the bill read, and the security check stopping a run.
- Then the video (`scripts/site_video/fetch.json`) and the two help articles (D9), with screenshots from that run.
