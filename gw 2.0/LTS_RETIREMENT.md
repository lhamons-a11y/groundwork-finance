# Item 32 — LTS is no longer needed

Opened 2026-10-04. No code. **The question is ruled.** Rob, 2026-10-04: *"Item 32 .. LTS is no longer needed."*

The item was queued to open after item 31's 8 GB report. Rob decided it without that report, so its two conditions
(who cannot run the narrator; 2.0 complete with AI off) are no longer what decides whether LTS exists. This pass sets
out what retiring it changes. It asks for rulings and authorises nothing.

## 1. Where LTS stands today (measured 2026-10-04)

- **The line.** `lts/1.x` is the shipped 1.x line: `v1.1.0` (August 2026), now at `9a1f20e`. People run 1.1 today, and
  2.0 is due in 2027.
- **How shared code is built.** Every shared change since 2026-08 has been built on `lts/1.x` first, gated, then merged
  to master and gated again. In this session alone that was items 35, 36, 38 and the fee-drag fix. That is the cost
  item 32 was asked about: each shared change built, gated and merged twice.
- **What 1.x users get now.** Recent correctness fixes went to 1.x:
  - investment valuation (item 35);
  - fee drag;
  - the help icon (item 36);
  - the $0 net worth snapshots (item 38).

  Item 38's bug writes wrong figures into saved history, and 1.1 users have it until they get the fix.
- **How a 1.x user would hear of a release.** `/api/update-check` reads the website's `version.json` manifest and
  offers a download only from the official site.
- **The upgrade path.** s67 already upgrades real old-schema databases in the gate, including 1.x to 2.0 (item 24).
- **The reason LTS existed.** Machines that cannot run the narrator (under 8 GB, no AVX2, Intel Mac). 2.0 already
  answers it:
  - A9: AI off loads nothing.
  - A10: every surface works with AI off. Agreed 2026-10-02, but the full surface audit is not recorded as done.

## 2. Points for ruling

**L1. What happens on `lts/1.x` until 2.0 ships.**
- (a) Frozen: no more commits. 1.1 users wait for 2.0.
- (b) Fixes only: data loss, wrong saved figures, and security fixes go to 1.x. Everything else is master only.
- (c) As now: every shared change on both lines.

*Recommended: (b).* It ends the double build for everything except the fixes 1.1 users would otherwise live with,
like item 38's, until 2027. (a) leaves known history-corrupting bugs in shipped software for a year. (c) keeps the cost
Rob asked about.

**L2. How a fix that qualifies under L1 reaches both lines** (opened 2026-10-04, Rob: *"Open L2"*).

L1 settles *which* changes go to 1.x. L2 settles *how* such a fix is built, and who says it qualifies.

**What today showed.** Four fixes went to both lines this session (items 35, 36, 38, and the fee drag). Each was built
on `lts/1.x`, gated, then merged into master and gated again.
- **The merges.** All four merged without a conflict. Each still needed master-only follow-up the 1.x code does not
  have: item 35's tile, item 38's 2.0 net worth tile and the s134 stub. Each was found on master's gate or sections.
- **One fix changed during the merge.** Item 38's *"without figures"* definition was found too broad on master's s134.
  It was corrected on 1.x first (`9a1f20e`) and merged again, so both lines kept one definition.

**L2a. The order.**
- (a) **On `lts/1.x` first, then merged forward into master** (as today). The fix is written against the older code
  it must run on. Master always contains everything 1.x has, by merge, so nothing can be on 1.x and missing from master.
- (b) **On master first, then backported to `lts/1.x`** (cherry-pick, adapted). The fix is written where development
  happens. But the two lines carry two versions of the same fix, and nothing guarantees they agree. A later merge of 1.x
  into master would meet the fix twice.
- (c) **Written separately on each line.** Two implementations, each gated.

*Recommended: (a).* It keeps one implementation of each fix, keeps "master contains 1.x" true by construction, and
writes the fix for the line where it is hardest to get right. Master-only follow-up stays master-only, found by
master's gate, as today.

**L2b. Who decides that a change qualifies.**
- Each pass that could touch 1.x says, in its points, whether the change is a data-loss, wrong-saved-figure or security
  fix and why. Rob rules it with the pass's other points.
- Without that ruling, the change is master only. Nothing goes to 1.x by default.

*Recommended.* (The alternative, Claude deciding at build time, would make the line a side effect of an implementation
choice.)

**L2c. The gate.** A fix on 1.x passes the 1.x gate before it is pushed, and master's gate after the merge, before
master is pushed. This is unchanged from today.

*Recommended.*

**L2 tested (2026-10-04, Rob: *"Test L2"*).**
- **Method.** A throwaway clone of the current GitHub branches, with pushing disabled (`scratchpad/l2_test.py`). Each
  simulated fix is a one-line change to a line both lines share. If a fix cannot be applied, the test says it is
  broken rather than reporting.
- **The first run found a real defect.**
  - `lts/1.x` had two commits master did not contain. They were item 38's `7031844` and `9a1f20e`.
  - **Cause:** while recording item 38's build, the master branch was rebased before pushing. A rebase flattens merge
    commits, so master carried *copies* of the two commits (`fcfe5b8`, `85220b9`), with the same code and different
    identities.
  - **Effect:** every later merge from 1.x conflicted. That is the failure (b) produces, arrived at by accident under (a).
  - **Repaired** by a real merge of `lts/1.x` into master (`c213510`). It changes no file: the tree is identical,
    verified with `git diff`. It restores *master contains every 1.x commit*. The code on master was always the gated
    code (`a09bfea` and `27c596f` differ only in `gw 2.0/`).
- **The second run, after the repair:**

| | First merge or pick | A later 1.x fix merged into master | Master contains every 1.x commit |
|---|---|---|---|
| (a) on 1.x, merged forward | clean | clean | yes |
| (a), with master-only follow-up in between (as items 35 and 38 had) | clean | clean | yes |
| (b) on master, cherry-picked back (same text) | clean | **conflict** (`server.py`) | **no** |
| (b), with the backport adapted to the older code | — | **conflict** (`server.py`) | **no** |

**What the test adds to L2:**
- **L2d. Never rebase a branch that holds merges from `lts/1.x`.** Update it with `git merge`, or not at all.
- **Before pushing master,** check `git merge-base --is-ancestor origin/lts/1.x HEAD`. If it fails, master has lost the
  link and the push waits.

*Recommended*, as a working rule, with the check run at every master push that follows a 1.x merge.

**Gaps in L2, found on review (2026-10-04, Rob: *"Is there any gaps that you see in L2?"* / *"Let's add these"*).**
L2a–L2d say how a fix reaches the branches. They do not say how it reaches people, and they leave five other cases
unwritten. Measured 2026-10-04:
- Only `v1.1.0` is tagged (`3935484`, 2026-08-28), and `lts/1.x` has **183 commits** since.
- `GW_VERSION` is still `20260826-d24` on both lines.
- `Website/version.json`, which the in-app update check reads, still says Groundwork *"installs Ollama for you"*.
- The lines carry different `SCHEMA_VERSION` strings: `20261002-lts-household-facts` on 1.x,
  `20261002-household-facts` on master.

**L2e. A 1.x fix reaches users only in a release. The release is part of the fix.**
- No 1.x release has shipped since August. Item 38's fix (wrong figures written into saved history), item 35's and
  item 36's are on `lts/1.x` and have reached no 1.1 user.
- When a qualifying fix is accepted, it is released as **1.1.x**, which means:
  - the version bumped on 1.x (`GW_VERSION`, matched in `app.js`);
  - the Windows installer built from `lts/1.x` and checked on a clean machine;
  - the changelog written, listing everything since the last release (see L2j);
  - `version.json` updated so 1.1 installs are offered it.
- Rob decides each release and deploys the website (the deploy stays his, as now). Claude prepares everything else and
  says what is ready.
- **The first such release** carries everything on `lts/1.x` since `v1.1.0`. It is laid out for Rob's go-ahead as its
  own step, not bundled into a ruling.

*Recommended.* Without this, L1's *"1.x gets data-loss fixes"* is true of a branch and of nobody's computer.

**L2f. The bug is shown on 1.x before it is fixed there.**
- Development is now master-only, so most bugs will be found on master.
- A pass proposing a 1.x fix measures the bug on `lts/1.x` (as items 35 and 38 did, on both lines) and records it.
- A bug that does not reproduce on 1.x is master only, whatever its kind.

*Recommended.*

**L2g. Merges go one way: `lts/1.x` into master, never master into `lts/1.x`.** A merge the other way would carry
2.0's code into the 1.x line. The rule is implied by L2a and written here so it is not only implied.

*Recommended.*

**L2h. A 1.x fix that changes the database.**
- The lines already keep separate schema versions. A 1.x fix with a migration therefore:
  - bumps 1.x's own version and pin (s51) on 1.x;
  - is resolved at the version line in the merge into master, where master takes its own next version and pin;
  - adds an s67 fixture for the new 1.x schema, so the 1.x → 2.0 upgrade still proves itself from that version.
- Each such fix says so in its pass, because this is the one kind of fix where the merge forward is never automatic.

*Recommended.*

**L2i. When the code around a fix has diverged, master's resolution is recorded as a change.**
- If the merge forward conflicts, the resolution is master's version of the fix. Only master's gate checks it.
- The build record names the conflict, the resolution, and the master check that covers it, as items 35 and 38 named
  their master-only follow-ups.
- It is never left as merge mechanics.

*Recommended.*

**L2j. The ancestry check runs itself.**
- L2d's *"master contains every 1.x commit"* becomes a gate check on master.
- When git and `origin/lts/1.x` are present, it fails if `lts/1.x` is not an ancestor of `HEAD`.
- When they are not present, it says it was skipped rather than passing silently.
- Today's slip happened because nothing checked.

*Recommended.*

**Note (not a point).** Some changes already on `lts/1.x` would not qualify under L1, such as item 36's help icon and
the Ollama removal (item 31). Nothing is undone. The first 1.1.x release notes list them with the rest (L2e).

**L2, for ruling as a whole:** L2a (a); L2b; L2c; L2d; L2e–L2j.

**L3. 1.1 users move to 2.0 by upgrading in place** (opened 2026-10-04, Rob: *"Open L3 - L6"*).

**Measured:**
- **Both lines keep their data in the same place.** `core/database.py` uses `%LOCALAPPDATA%\Groundwork`, unless
  `GROUNDWORK_DATA_DIR` is set. So 2.0, installed over 1.1, opens the 1.1 database.
- **The upgrade is already proven in the gate.** `tests/schema/` holds `20260725-byb` (v1.1.0's released schema),
  `20261002-lts-household-facts` (1.x today) and `20261002-household-facts` (master). On master, s67 upgrades each one
  through `run_migration_if_needed` and checks every table and column.
- **Nothing is backed up before a migration.** `run_migration_if_needed` changes the database in place. Once 2.0 has
  migrated a 1.1 database, nothing measured shows that 1.1 can still open it, and the user has no copy from before.
- **One manifest serves both lines.** Both read `https://groundworkfinance.app/version.json`, and both offer an update
  when its `latest` is newer than their own `GW_VERSION` (a date string).
  - So the day `version.json` names 2.0, every 1.1 install is offered 2.0.
  - Until then, 1.1.x releases (L2e) and 2.0 cannot both be "latest".

**Points:**
- **L3a. In place, as recommended:** the 2.0 installer goes over 1.1, and the first launch migrates the database. No
  export or import is asked of the user.
- **L3b. A copy before the move.** Before migrating a database whose stored schema version differs, the app writes a
  dated copy beside it (*"Groundwork backup before 2.0, <date>"*), using the existing backup function. It says where the
  copy is, and never deletes it.

  *Recommended.* It is the user's whole financial record, and the move is one-way.
- **L3c. One way, said plainly.** Once migrated, the database is a 2.0 database. 1.1 is not made to open it. A user who
  wants 1.1 back restores the L3b copy.
  - Before release, a test opens a 2.0-migrated database in 1.1. The result is recorded either way, so the statement
    is measured, not assumed.

  *Recommended.*
- **L3d. The manifest when 2.0 ships.** `version.json` names 2.0, and every 1.1 install is offered it. A 1.1 user who
  does not upgrade keeps the last 1.1.x, with no further fixes (L5).

  *Recommended.* (A separate 1.x manifest would only matter if 1.x outlived 2.0's release, which L1 rules out.)
  - **The Store channel is separate** (found on review). `groundwork_store.iss` builds a Store package. Store installs
    update through the Store, not `version.json`, so *"every 1.1 install is offered 2.0"* is not true of them. The 2.0
    release (L7) includes the Store submission, or says the Store channel is not offered 2.0.
- **L3e. The machine 1.1 ran on runs 2.0.** 2.0 with AI off has no AI requirement (A9). The AI needs AVX2 and the 8 GB
  minimum (item 31). The upgrade is never refused for lack of them: the AI is simply off, and the app says why.

  *Recommended.*
- **L3f. 2.0's version string stays in the date form for as long as 1.1 is in use** (found on review, measured).
  - The installed 1.1.0 compares versions as text (`latest > GW_VERSION`), and `GW_VERSION` is a date string
    (`20260826-d24`).
  - Measured: `"2.0.0" > "20260826-d24"` is **False**, and `"20270101-2.0" > "20260826-d24"` is True.
  - So a 2.0 that called itself `2.0.0` would never be offered to a single 1.1.0 install. That code is on users'
    machines and cannot be changed.
  - **The rule:** `GW_VERSION` and the manifest's `latest` keep the date form (`YYYYMMDD-…`), and *"2.0"* is the name
    shown to people. Any change to the comparison is made only in 2.0, for 2.0's own future updates.
  - A gate check pins that `GW_VERSION` sorts after every released version.

  *Recommended.* Without it, L3d's *"every 1.1 install is offered 2.0"* fails silently.

**L4. Machines that cannot run the local AI use 2.0 with AI off. The A10 audit is the exit criterion.**

**Measured:**
- `callAI` (the single path for every narrative AI answer) is called from **at least** nine places in `app.js`:
  - `generateReport`;
  - the trip planner: `_learnFromPastTrip`, `_readTripQuote` and `generateTripBudget`;
  - `renderSundayCard`;
  - `_renderProjectionAI`;
  - the report chat: `_rcSendAI`, `_rcFollowUp` and `_rcMonthlyGenerate`.
- The Investments advisor and other model uses go through their own paths. The audit lists them as it finds them.
- **Correction (found on review):** nine is the count in `app.js` only. The teaching modules and the server have other
  model uses, such as item 28's tile matcher. L4a's list is built from the code, so the audit's coverage is not limited
  by this count, but the count is not the total.
- A10 (item 30, 2026-10-02) says each must give *"the plain-figures fallback, never an empty box or an error"* with AI
  off, and that this has *"not been checked"*.
- **AI defaults to on.** The settings route sets `ai_enabled = 'true'` when unset. A machine that cannot run it relies
  on the engine guard (AVX2, the 8 GB check) to switch it off.

**Points:**
- **L4a. The audit is a gate check, as A10 already specifies.** One pass with `ai_enabled=false` visits every AI
  surface. Each must give a useful answer without AI, or say plainly what needs the AI and that it is off. It must
  never show an empty box, an error or a spinner that never ends. The list of surfaces is built from the code (every
  `callAI` caller and every AI route), not from memory, so a new surface cannot be missed.

  *Recommended.*
- **L4b. The audit happens before 2.0 ships, as its own pass.** It is opened, ruled and built like any item, and each
  surface it finds wanting is fixed in it.
  - **Exit criterion:** the L4a check passes on master with every surface listed.
  - Until it passes, the retirement of LTS stands, but its reason (machines without AI are served by 2.0) is unproven,
    and the record says so.

  *Recommended.*
- **L4c. A machine that cannot run the AI gets AI off automatically, and is told why.** This is measured on the
  engine guard (no AVX2 or under 8 GB means off, with the reason), so the user is not left with an AI that fails.

  *Recommended.* Item 31's 8 GB test measures the RAM half on real hardware.
- **L4d. "AI on but not working" gets the same fallback** (found on review).
  - L4a checks the switch set to off. A machine where the AI is on but the engine does not load, the model file is
    missing, or an answer fails part-way must give the same plain-figures answer, with the reason.
  - These are item 31's five states, never collapsed. So the audit runs twice: once with `ai_enabled=false`, and once
    with AI on and the engine made to fail at each state it can fail at.

  *Recommended.*
- **L4e. "Useful" is ruled, not tested** (found on review). The gate proves what it can: no empty box, no error, no
  endless spinner, a stated reason. Whether each surface's AI-off answer is good enough is Rob's ruling, surface by
  surface, in the L4b pass, with each surface's AI-off output shown to him.

  *Recommended.* (*Capable is not admissible:* a passing check is not the same as a good answer.)
- **L4f. The count in the record is corrected** to *"at least nine in app.js; the full list is the L4a audit's"*, so
  the record does not understate the audit.

  *Recommended.*

**L5. Nothing is deleted.**

**Measured:**
- `lts/1.x` is not a protected branch on GitHub (`protected: false`). "Frozen" is a working rule today, not something
  GitHub enforces.
- `v1.1.0` is the only tag.

**Points:**
- **L5a.** `lts/1.x`, `v1.1.0` and every 1.1.x tag (L2e) stay as they are. Nothing on the line is deleted or rewritten.
- **L5b. When 2.0 ships:** the last 1.1.x is tagged, and `lts/1.x` takes no further commits. Rob may also protect the
  branch on GitHub. That is his account setting, and Claude does not change it.
- **L5c. After 2.0 ships, a 1.1 user who does not upgrade** keeps the last 1.1.x, unsupported. The website says so
  (item 37).
- **L5d. The last 1.1.x stays downloadable** (found on review).
  - The site serves one file, `Groundwork_Setup.exe`, which becomes 2.0. A 1.1 user moving to a new computer could
    not get 1.1 again.
  - The last 1.1.x installer stays on the site under a versioned name (`Groundwork_Setup_1.1.x.exe`), with its SHA-256
    published beside it, and is labelled unsupported. The site's side of this is item 37's.

*Recommended* (all four).

**L6. Other items.**

**Measured:** wording that assumes every shared change goes to 1.x first still stands in:
- `ENGINE_REPLACEMENT.md` E7 (*"as with every shared fix: lts first"*);
- `ENGINE_OTHER_PLATFORMS.md` Q8 (*"Both lines, 1.x first"*; item 33 is open);
- several closed items' records.

**Points:**
- **L6a.** Item 31 (the 8 GB test) still stands. It sets 2.0's AI minimum (L4c), not whether LTS exists.
- **L6b.** Item 33's remaining work (the release asset, Q6 on real hardware) is master only under L1, unless a part of
  it is a data-loss or security fix (L2b). Q8's *"1.x first"* is superseded for what remains.
- **L6c.** Item 37 (the website) carries what the site says about versions, LTS, the 1.1.x releases and the end of 1.1
  support (L3d, L5c).
- **L6d.** Closed items' records stay as written: they were true when built. Open items and new passes follow L1/L2,
  and a note in BUILD_QUEUE says the *"1.x first"* order is retired except for L1's fixes.
- **L6e.** Item 12 step 2 (the caps) is master only unless ruled otherwise.

*Recommended* (all five).

**L7. "When 2.0 ships" is defined by a release checklist** (found on review).

L3, L4 and L5 each turn on 2.0 shipping, and nothing yet defines that moment. The 2.0 release is its own item, opened
when 2.0 is near. It ships only when every line below holds:

| Condition | From |
|---|---|
| The AI-off audit passes on master, with every surface listed, and Rob has ruled each surface's AI-off answer | L4a, L4b, L4d, L4e |
| Item 31's 8 GB result is recorded, and the AI minimum is set from it | item 31, L4c |
| A dated backup is written before a 1.x database is migrated, and the one-way test is recorded | L3b, L3c |
| `GW_VERSION` is in the date form and sorts after every released version | L3f |
| The installer upgrades a 1.1 install in place, checked on a clean machine with a real 1.1 database | L3a |
| The Store channel is submitted, or said not to be offered | L3d |
| The last 1.1.x is tagged, and stays downloadable under a versioned name | L5b, L5d |
| The website says what 2.0 is and what happens to 1.1 | item 37, L6c |

*Recommended.* The checklist is the definition. Adding a line to it later is a ruling, not a build detail.

## 3. Ruling

**L1 RULED (Rob, 2026-10-04: *"I agree with L1"*), as recommended: (b).** Until 2.0 ships:
- `lts/1.x` gets only fixes for data loss, wrong saved figures and security.
- Everything else is built on master alone.

From this ruling on, a shared change is not built on 1.x unless it is one of those fixes.

**L2 RULED AS A WHOLE (Rob, 2026-10-04: *"Yes i accept L2 as a whole"*), as recommended:**
- **L2a (a):** a qualifying fix is built on `lts/1.x` first, gated, then merged forward into master.
- **L2b:** each pass says whether a change qualifies under L1 and why; Rob rules it. Without that ruling it is master
  only.
- **L2c:** the 1.x gate before pushing 1.x, then master's gate before pushing master.
- **L2d:** never rebase a branch that holds 1.x merges; check ancestry before pushing master.
- **L2e:** a 1.x fix reaches users in a 1.1.x release. Rob decides each release and deploys the site; Claude prepares
  the rest. The first release, carrying everything since `v1.1.0`, is laid out for Rob's go-ahead as its own step.
- **L2f:** the bug is shown on 1.x before it is fixed there.
- **L2g:** merges go `lts/1.x` → master only.
- **L2h:** a schema-changing 1.x fix keeps 1.x's own version and pin, is resolved at the merge, and adds an s67 fixture.
- **L2i:** a diverged-code resolution is recorded as master's change.
- **L2j:** the ancestry check becomes a gate check on master.

**What L2 needs built:**
- L2j's gate check: a small change, master only.
- L2e's first 1.1.x release: a release, laid out for Rob before anything is built or published.

Neither is authorised by this ruling.

L3–L6 have not been ruled. They stay open, and are not assumed. L3–L6 were opened and measured 2026-10-04 (above). On review they gained L3f, the Store channel in L3d,
L4d–L4f, L5d and L7.

## 4. Status

QUESTION RULED 2026-10-04 (LTS no longer needed). L1 RULED (b). L2 RULED as a whole. L3–L6 open. No build
authorised: L2j's gate check and L2e's first 1.1.x release each await their own go-ahead.
