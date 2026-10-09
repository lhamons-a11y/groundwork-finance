# Item 57 — Groundwork fetches your bank downloads, when you ask

Opened 2026-10-09. Rob: *"What can't we automate the agent to go to the bank using the build in web browser … and
load bank transactions and credit card transactions for Groundwork. The user can state that they want Groundwork to
do that for them. The passwords would have to live somewhere in groundwork which would need to be secured."*

Focus-group testers asked the same question. The rest of the brief, in Rob's words:
- *"we can't scheduled it we will have to make the user click a button to start the automation … or if we add
  voice controls they could ask assistant to do that and then we still have a no 3rd party is ever seeing your data
  rule enforced."*
- *"lets make the user aware this is due to 2fa rules and guidelines that many banks enforce. I agree with keeping
  the passwords in the security vaults in the operating system."*

**Already decided by Rob (2026-10-09):**
- Started by the user only: a button, and later Assistant by voice. No schedule.
- The user is told why: two-step login rules that many banks enforce.
- Passwords live in the operating system's vault.
- No third party ever sees the data: bank → the user's computer → Groundwork.

**A1 RULED 2026-10-09 (Rob: "change the viewers rule, It would be a mistake to not do this"), option (b). A2–A11 RULED 2026-10-09 (Rob: "approve A2–A11 as recommended")**: A7 (a), a remembered device opt-in per account; master only (A10). **No code yet:** the build needs its own go-ahead.

## 1. What is true today (measured 2026-10-09 on master 0e6335f)

- **The bank window (item 19, `BANK_BROWSER.md`) is ruled as a viewer, not an agent.** Its §0 invariant:
  *"Groundwork supplies only the user-entered HTTPS URL, receives no page state, performs no interaction, retains no
  session, and receives financial data only when the user independently downloads a file into the existing review
  path."*
  - F1 made the process shape an invariant: *URL in → bank WebView → user interaction → user-selected download →
    filesystem.*
  - `bank_window.py` never calls `evaluate_js`, `run_js`, `get_elements`, `get_cookies`, `load_html` or `load_url`,
    and s126 fails if it ever does.
  - The window runs in `private_mode`, so nothing (no remembered device, no cookie) survives closing it.
  - **Fetching downloads automatically breaks every clause of that sentence.** The ruling has to say so, not slip it
    in (A1).
- **The import review is the one way bank data enters.** A file in the Downloads folder (F6, one resolved folder) is
  offered by name and read only after a yes, then staged for review before anything is saved.
- **No secret is stored anywhere today.** Groundwork has no password, token or key for any outside service. The
  `keyring` library (Windows Credential Manager, macOS Keychain, Linux Secret Service) isn't installed. It would be a
  new dependency in all three builds.
- **The pattern exists at a smaller scale:** item 44 reads one button's price in the Google Flights window, after
  the user's click, named as Google's, and confirmed before use.

## 2. What it would do

1. **Show me once.** The user opens their bank in Groundwork and does their usual download. Groundwork records only
   the steps: which link or button, which date range, which format. It records **no typed values**. The password
   goes into the vault through Groundwork's own form, never captured from the page.
2. **Get my latest transactions.** One button per account, or later *"Assistant, get my bank transactions"*.
   Groundwork opens the bank, fills the login from the vault, replays the steps, and saves the file to Downloads.
3. **You stay at the computer.** When the bank asks for a code, or the page doesn't look as recorded, Groundwork
   stops and says what it's waiting for. It never reads codes from a phone or email, and never works around a check.
4. **Review as always.** The file goes through the existing import review. Nothing is saved without the user's yes.

## 3. Points for ruling

**A1. The bank window's invariant, and where the agent lives.**
- (a) **A separate agent process.** The viewer (item 19) stays exactly as ruled, and s126 keeps holding it. The agent
  is a new, separately ruled process with the same isolation: no Groundwork server, database, session token or API
  bridge. It is the only code that may fill a login, click recorded steps, and read the few page anchors those steps
  name. Its only output is a file in Downloads.
- (b) Amend item 19's invariant to allow scripted interaction in the one window.

*Recommended: (a).* The viewer's guarantee stays true for everyone who doesn't turn the agent on, and the new power
gets its own boundary and its own crossing test.

**RULED (b) (Rob, 2026-10-09):** *"change the viewers rule, It would be a mistake to not do this. with this we will be
able to actually capture when exactly all of the transactions were downloaded and imported because we still allow
imports to happen away from groundworks. This will also fill in blanks in the historian. We would have a clearer
learning model for the agent to be able to help teach the user."*

What the amendment changes, to be written into `BANK_BROWSER.md` §0 and §7 at build time:
- **The new invariant** (proposed wording): *"The bank window shows the user's bank. It acts on the bank page only
  when the user starts a fetch, and then only to fill that account's login from the operating system's vault and
  replay the steps the user recorded. It reads no page content beyond the anchors those steps name, and its only
  output is the downloaded file, which enters the existing review path."*
- **s126's crossing test** moves with it. The calls it forbids today (`evaluate_js` and the rest) become allowed in
  the fetch path only, and the new mutations are A10's: a typed value recorded, a page's content read, a password
  reaching the database or a log, a run starting without a click.
- **F1's process shape stays.** There is still no Groundwork server, database, session token or API bridge in the
  bank process. Only the interaction clause changes.
- **The learning model stays under its rules.** What the fetch records is provenance: the user's own action and its
  times (A11). Anything the agent teaches from it is surfaced, never inferred silently (*no silent learning*).

**A2. Started by the user, every time (ruled in brief).** A *Get my latest transactions* button per account, and an
Assistant voice action later that calls the same start. No schedule, no background run, and no automatic retry.
*Recommended, as Rob ruled.*

**A3. What the user is told, before turning it on.** Proposed wording:
> *Groundwork can fetch your downloads for you, but only when you ask, and only while you're here. Many banks
> require two-step verification (a code by text or app) and have rules against unattended automated access, so
> Groundwork can't run this on a schedule. You'll type any code yourself; Groundwork never reads your texts or email.*
>
> *Your password is kept in your computer's own password vault (Windows Credential Manager, macOS Keychain, or your
> Linux keyring), not in Groundwork's files. Anyone who can sign in to your computer as you could use it. Your bank's
> terms may not allow automated access, and how a bank treats fraud on an account whose password was used by
> software varies. Check with your bank if you're unsure.*

*Recommended.*

**A4. The vault (ruled in brief).**
- One entry per account, named *Groundwork – <account name>*, added with `keyring`.
- Read only by the agent process, at login, and never written to Groundwork's database, logs, exports or the
  narrator.
- Settings lists which accounts have a saved login (never the password) with *Forget*, which deletes the vault entry.
- On Linux without a secret service, the feature says it's unavailable rather than falling back to a file.

*Recommended.*

**A5. Show me once: what is recorded.**
- **Recorded:** each click's target, identified the way the page names it (its label, its role, or its link text),
  the date-range choice and the file format.
- **Never recorded:** typed values, page content, balances or account numbers.
- The recipe is stored per account and shown to the user in words, for example: *"Accounts → Checking → Download →
  Last 30 days → CSV"*. It can be re-recorded or deleted.

*Recommended.*

**A6. When it stops.** It stops and hands the window to the user, saying why, when:
- the bank asks for a code;
- the page doesn't match the next recorded step;
- a CAPTCHA or "unusual activity" page appears;
- the download doesn't arrive in 2 minutes.

Nothing is guessed, and nothing is retried on its own.
*Recommended.*

**A7. Remembered device.** Banks ask for a code less often on a device they remember, but the viewer's
`private_mode` forgets everything. The agent process could keep its own bank cookies in a per-account profile on
disk, with *Forget this device* beside *Forget* in Settings.
- (a) Keep a profile. Fewer codes, but a stored bank session on disk.
- (b) Private every time. A code nearly every run.

*Recommended: (a), opt-in per account, stated in A3's wording.*

**A8. Into the review, never past it.** The downloaded file lands in Downloads and is offered by name through the
existing review (item 19 F6). Nothing in the agent writes a transaction.
*Recommended.*

**A9. Which banks.** It works with any bank whose download the user can record. The ones it can't do are named, not
hidden:
- banks without a download option;
- banks that block automated browsers.

OFX Direct Connect, where a bank offers it, is a later item.
*Recommended.*

**A10. Lines and tests.**
- Master only.
- A crossing test for the agent process like s126, with mutations: a typed value recorded, a password reaching the
  database or a log, the agent importing the server, a run starting without a click.
- The vault tested through `keyring`'s in-memory backend.
- One real run on Rob's bank before acceptance, the way item 19 was measured.

*Recommended.*

**A11. When each file was fetched, in the Historian.** Rob's reason for (b). Today the Historian records an import
(`import_committed`, item 20 H1: file name, content hash, origin, account, counts, date range), but not when or how
the file was fetched. That's why a file downloaded outside Groundwork leaves a gap. Each fetch would record one
`statement_fetched` event:
- the account and the bank's host;
- the recipe used (its words, as in A5);
- started, the time a code was asked for and how long the user took, and finished;
- the outcome: fetched, stopped (and why, as in A6), or cancelled;
- the file's name and content hash.

The later import's `import_committed` event carries the same hash, so the two are joined by the file, not by a
guess. A file the user downloads themselves still gets `import_committed` alone, and the gap stays visible, never
filled in. Nothing of the file's content is recorded (H1's C3).
*Recommended.*

## 4. Not decided here

- **The Assistant voice action:** that's Assistant's own build. A2 makes it call the same start.
- **OFX Direct Connect:** its own item.
- **Learning from what the user downloads:** ruled out by *no silent learning*.
