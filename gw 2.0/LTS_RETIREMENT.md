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

**L2. The order for shared code changes.** Under (b), the rule *"lts/1.x first, then merge to master"* applies only to
a fix that goes to 1.x. Everything else is built on master alone.

*Recommended.*

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

## 3. Status

QUESTION RULED 2026-10-04 (LTS no longer needed). L1–L6 sought. No build authorised.
