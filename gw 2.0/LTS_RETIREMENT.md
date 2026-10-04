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

**L3. 1.1 users move to 2.0 by upgrading in place.**
- When 2.0 ships, its installer opens a 1.x database and migrates it. s67's 1.x → 2.0 fixture already proves this in
  the gate.
- The update check offers 2.0 to 1.x users.
- Nothing is required of the user beyond installing.

*Recommended.*

**L4. Machines that cannot run the local AI use 2.0 with AI off. The A10 audit is the exit criterion.**
- Before 2.0 ships, each AI surface is confirmed to work, or to say plainly that it needs the AI, with the AI off. The
  older surfaces were named in item 32: trip planning, categorising, the narrator panels.
- This is what makes retiring LTS safe for those machines. Until it is done, the retirement holds but the reason is
  unproven.

*Recommended.*

**L5. Nothing is deleted.**
- `lts/1.x` and `v1.1.0` stay as they are.
- Under (b), the last 1.x fix release is tagged when 2.0 ships, and the branch is then frozen.

*Recommended.*

**L6. Other items.**
- **Item 31 (the 8 GB test)** still stands: it sets 2.0's AI minimum, not whether LTS exists.
- **Item 37 (the website)** carries anything the site says about versions or LTS.
- **Item 12's 1.x note,** and any *"LTS carries correctness fixes"* wording elsewhere, follow L1.

*Recommended.*

## 3. Ruling

**L1 RULED (Rob, 2026-10-04: *"I agree with L1"*), as recommended: (b).** Until 2.0 ships:
- `lts/1.x` gets only fixes for data loss, wrong saved figures and security.
- Everything else is built on master alone.

From this ruling on, a shared change is not built on 1.x unless it is one of those fixes.

L2–L6 have not been ruled. They stay open, and are not assumed. L2 was opened, tested and reviewed
2026-10-04 (L2a–L2j above).

## 4. Status

QUESTION RULED 2026-10-04 (LTS no longer needed). L1 RULED (b). L2–L6 open. No build authorised.
