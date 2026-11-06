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
- **P3 RULED:** the Mac is measured (Rob's M2, 8 GB: engine on Metal, macOS 12 floor, CI build `19135a3` passed). Rob 2026-11-06 raised the floor to macOS 14, because Kokoro's onnxruntime no longer fits 12; that build has not been measured on a Mac.
  Linux is tested on Ubuntu under WSL on Windows (Rob: "Linux in WSL is a fair test its ubuntu ... we can't test every
  flavor of Linux"). The bank window on Linux is recorded as measured on WSL only. Other distributions are left to the
  open-source community after 2.0 - one of Rob's reasons for opening the code.
- **P4 ADDED:** the model download is checked before release, when the installers are built.
- Item 98 is tried during the beta; nothing needed now.
- The open-source release (the cleaned public copy, `scripts/export_public.py`) waits for the 2.0 release.
- **RULED 2026-10-31 / 2026-11-01 (Rob): Groundwork goes open source with the 2.0 release** (*"I have decided that I
  will open source this with 2.0 release. I believe that I took this project as far as I can alone."*), and the clean
  copy is published **only on release day** (*"don't publish the clean copy yet. only when 2.0 release day"*).
  - Not by making `lhamons-a11y/Groundwork` public: its history holds the real-ledger results, family names and a bank
    trace number. A new public repository is made from `scripts/export_public.py`; this one stays private.
  - A trial export (2026-10-31, from 839957a, not pushed) is at `~/Documents/Groundwork-public-2.0`: 568 files, one
    commit, GPL v3, no private names or keys found. Release day: export again from the release commit, then publish.
  - Before publishing, Rob checks the old `screenshot/01-10_*.png` set (August): `02_ledger.png` shows Harbor /
    Discover / Capital One rows without the sample-household label. The text scan can't read images.
  - The website says "open source" only once `RELEASED_20` is true.
- Order: s174 A8 fixed (2026-10-19), then the release-day lines.

**R3 / L3c, the one-way test - RUN 2026-10-31** (`scripts/l3c_one_way.py`, a worktree of `v1.1.1`; Rob: *"go ahead with
1-3"*). A 1.1.1 database (an account, three transactions, a budget line) was upgraded by 2.0, opened again in 1.1.1,
then in 2.0 again:

| Step | Starts | Records read | Stored schema version | Backups |
|---|---|---|---|---|
| Made in 1.1.1 | yes | 3 transactions, 1 account, 1 line | `20261002-lts-household-facts` | none |
| Opened in 2.0 | yes | all of them | `20261030-goal-accounts` (78 tables) | before / after upgrade |
| Opened again in 1.1.1 | **yes** | all of them; **a new transaction written** | **set back to `20261002-lts-household-facts`** | unchanged |
| Opened again in 2.0 | yes | all 4 | `20261030-goal-accounts` | a second before / after pair |

**What this measures, said plainly - L3c's statement was not true as written.** 1.1 is *not* stopped from opening a
2.0 database: it opens it, reads and writes it, ignores the tables it does not know, and writes its own schema
version back. The next 2.0 start reads that as a 1.x database and runs the whole migration again. That is safe as far
as measured: every one-time step is guarded by its own done-flag, so nothing is converted twice (item 109's UTC to
local conversion included), and nothing was lost. Two effects remain: rows written while back in 1.1 carry 1.1's UTC
times, which 2.0 does not convert afterwards (4-5 hours off in the US); and each round trip writes another pair of
backups. **For ruling (L3c):** keep the statement "restore the L3b copy to go back to 1.1" and record this as measured,
or have 2.0 notice a database a 1.x opened (a 1.x schema version beside 2.0-only tables) and say so once.

**R7 and R8 built 2026-10-31** (with the website remake, WEBSITE_MESSAGE.md): the download page's 1.1 line shows once 2.0
is the download; the versioned `Groundwork_Setup_1.1.1.exe` with its SHA-256 shows once `V11_SHA256` is filled in -
**release day: build or fetch the 1.1.1 installer, fill in its hash, upload it.** Rob publishes the site.

**L3c RULED 2026-10-31 (Rob):** *"lets not let a 2.0 database be open by a previous version. It should block it."* A
released 1.1.1 cannot be changed, so a block would have to come from 2.0 making 1.1.1 fail at startup - not pursued.
Then: *"yes build those, in windows the installer should check for previous versions and uninstall them for the user
and then install 2.0. Mac, linux the files should overwrite the previous"*. **Built the same day:**
- **2.0 notices it:** a database with 2.0's own tables carrying a 1.x version is recorded before the upgrade runs
  again (`_opened_by_1x`), and the once-only upgrade notice says *"Groundwork 1.1 opened your records"*: nothing lost,
  rows added in 1.1 keep UTC times, and the way back is the copy saved before the *first* update. Checked against a real
  1.1.1 round trip.
- **Windows:** `groundwork.iss` and `groundwork_offline.iss` find an earlier Groundwork (the same AppId, any version)
  and run its uninstaller silently before installing; an open Groundwork is closed first. The uninstaller removes only
  the program folder - the records in `%LOCALAPPDATA%\Groundwork` are never touched. (The Store package is left to the
  Store.) **Not run here: Inno Setup is Windows-only - check on the Windows laptop when the installer is built.**
- **Linux:** `install_linux.sh` replaces `/opt/groundwork` instead of copying over it; the records in
  `~/.local/share/Groundwork` are never touched.
- **macOS:** the download is a zip; dragging Groundwork into Applications asks to **Replace** - the download page says so.
- **Said plainly:** the help guide's *"Can I go back to Groundwork 1.1?"*, and the download page once 2.0 is the
  download. s267 (7 checks). Gate: 4035 passed, 0 failed.

