# Item 82 - The 2.0 release: the checklist that says when 2.0 ships

Opened 2026-10-12 as the release item item 32 L7 calls for (Rob: *"agree let's complete everything in the order you
suggest ... ok to build all"*).

**The checklist is L7's, ruled 2026-10-04.** This item adds nothing to it: adding a line is a ruling (L7). It records
where each line stands today, measured, and what is left for each. Section 3 lists lines **proposed** for Rob to add or
leave out.

## 1. The checklist, measured 2026-10-12 (master after the AI-off audit)

| # | Condition (L7, ruled) | Where it stands | What is left |
|---|---|---|---|
| R1 | The AI-off audit passes on master, with every surface listed, and Rob has ruled each surface's AI-off answer (L4a, L4b, L4d, L4e) | **Built** (`AI_OFF_AUDIT.md`): 14 surfaces listed from the code, both conditions measured, six findings, four fixed, s217 in the gate. | Rob's acceptance and push; Rob's ruling on each surface (the table's *Ruling* column); the browser sweep repeated just before release. |
| R2 | Item 31's 8 GB result is recorded, and the AI minimum is set from it (item 31, L4c) | Item 31 was closed by Rob on 2026-10-11. The minimum in the code is 7.5 GB reported (an 8 GB machine reports a little under 8), with AVX2. **No run on a real 8 GB machine is recorded.** | Rob rules whether the closure satisfies this line, or the 8 GB kit (`installer_output/gw_8gb_test_kit`) is run first. |
| R3 | A dated backup is written before a 1.x database is migrated, and the one-way test is recorded (L3b, L3c) | **L3b BUILT 2026-10-12, ACCEPTED 2026-10-13** (Rob: "yes", "I accept both"; `_backup_before_migration`, s218): before any migration, a dated copy `groundwork_backup_<date>_before_upgrade` through the backup function, sealed when protection is set up and plain otherwise (as every safety copy), never deleted, and said once on the page. | L3c: open a 2.0-migrated database in 1.1 and record the result. |
| R4 | `GW_VERSION` is in the date form and sorts after every released version (L3f) | The form is pinned by s149. **Master's `GW_VERSION` is still `20261008-d25`**, the same as 1.1.1. | At release, a new date-form version later than every 1.1.x, in `server.py` and `app.js` (s149 checks both). |
| R5 | The installer upgrades a 1.1 install in place, checked on a clean machine with a real 1.1 database (L3a) | Not done. The migration itself is proven in the gate (s67, from v1.1.0's schema). | Build the 2.0 installer (with the model) and run it over 1.1.1 on a clean machine. |
| R6 | The Store channel is submitted, or said not to be offered (L3d) | `groundwork_store.iss` exists. Nothing is decided. | Rob's call. |
| R7 | The last 1.1.x is tagged, and stays downloadable under a versioned name (L5b, L5d) | `v1.1.1` is tagged. **The site does not yet offer `Groundwork_Setup_1.1.x.exe`**: no versioned 1.1 download was found in `Website/`. | Add the versioned 1.1.1 download with its SHA-256, labelled unsupported. Publishing is Rob's. |
| R8 | The website says what 2.0 is and what happens to 1.1 (item 37, L6c) | The site was redesigned and accepted (item 37, with the 2.0 overview page). No line about 1.1 support ending was found. | Add the 1.1 line. Rob publishes. |

## 2. What this means today

**2.0 does not ship yet.** Of the eight lines:
- R1 is built and waiting on acceptance;
- R2, R6 and part of R1 are Rob's rulings;
- R3 is a build: data safety, and the only one that touches users' records;
- R4, R5, R7 and R8 belong to release day: a version string, an installer run, and two website lines.

**Suggested order:**
1. R1's acceptance.
2. R3 (build it now: it is ruled, and nothing should migrate a user's whole record without a copy).
3. Rob's rulings on R2 and R6.
4. R7 and R8 with the next site change.
5. R4 and R5 on release day.

## 3. Proposed additions, for Rob to rule (L7: adding a line is a ruling)

Found while measuring. Not on the checklist unless Rob adds them.
- **P1. The two wrong figures found in the audit** (the dashboard projection's leverage category, and transfers
  counted as spending in the Monthly Report) are fixed. A release should not ship a known wrong figure (L1's own
  standard for 1.x).
- **P2. Item 81 B10 (the security key)** is built, or said to follow 2.0.
- **P3. Item 33 Q6 (the AI engine on Apple Silicon and Linux)** and **item 19's open measurements (the bank window on
  macOS and Linux, the installer path)**: either measured, or 2.0 is said to ship for Windows first.
- **P4. The model download** (`model-phi3.5-mini-q4`, a GitHub release asset, sha256 `34b830f4…`) is confirmed as what
  the 2.0 installer and `fetch_model.py` fetch.

## 4. Status

Opened 2026-10-12. R1 built (awaiting acceptance). R3 is the next build, if Rob agrees.

**Rulings 2026-10-19 (Rob):**
- **P1 ADDED and DONE:** both wrong figures were fixed and accepted 2026-10-13 (`a2f290c`, s221).
- **P2 ADDED:** the security key (item 81 B10) is tested last, before release.
- **P3:** the Mac is measured (Rob's M2, 8 GB: engine on Metal, macOS 12 floor, CI build `19135a3` passed). Linux:
  Rob asks whether Linux running on Windows (WSL) can be the Linux test - answered in the session, not yet ruled.
- **P4 ADDED:** the model download is checked before release, when the installers are built.
- Item 98 is tried during the beta; nothing needed now.
- The open-source release (the cleaned public copy, `scripts/export_public.py`) waits for the 2.0 release.
- Order: s174 A8 fixed (2026-10-19), then the release-day lines.

