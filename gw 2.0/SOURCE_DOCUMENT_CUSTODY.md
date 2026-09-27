# Source-document custody — what Groundwork keeps, and what it promises about it

> Status: **RULED 2026-09-25 (Rob, §8). No code. The source store's build is NOT authorised; H1 and
> H2 are authorised as SEPARATE builds.** Opened and revised the same day. Rob's question:
>
> > **Should Groundwork have a managed document store for financial source files, and if so,
> > what does Groundwork promise about those files?**
>
> In the order he set: *what does Groundwork retain? why? who controls removal? what happens to
> provenance when it is removed? what does backup mean for retained source documents?* The folder
> architecture comes after, and **where the store lives is not decided here.**
>
> Queue item 20. Arose from the bank window (item 19), whose F9 fenced statement custody as
> unopened. The review's corrections are tagged **[Rv1]–[Rv17]**. §4 holds two items from the
> same day's discussion that **do not depend on how custody is ruled**.

---

## The invariant

> **Source custody can end. Source-derived history does not thereby end.**
>
> Groundwork may remember what it learned from a source without pretending it still possesses
> that source.

---

## 0. The three states — Rob's, and not to be conflated

```text
DOWNLOADS              the institution gave the file to the user. The OS's download location.
                       Groundwork does not have it, and never has.
        │   user imports, and explicitly lets Groundwork keep it
        ▼
RETAINED               Groundwork has CUSTODY of a financial artefact
        │   custody ends (the user's act, §3 D5)
        ▼
CUSTODY ENDED          the records derived from it DO NOT disappear. Groundwork stops implying it
                       can produce the original if asked "where did these numbers come from?"
```

**Custody means possession and availability, never ownership [Rv1].** Retaining a copy promises
that Groundwork can produce those bytes again. It makes no claim to legal ownership of the
document, which stays the institution's issue and the user's record.

**Move and retention are two decisions** (Rob). Retention is a custody decision. Removing the
Downloads copy is a tidiness decision about the user's own file. The bank window must never turn
*"Groundwork offered to keep this"* into *"Groundwork manages everything in Downloads."*

**Age is not usefulness** (Rob). An old statement may be exactly what explains a historical
balance two years later. No rule may treat *old* as *safe to remove*.

---

## 1. What is fixed

1. **The captured-portal ruling** (`CAPTURED_PORTAL_CASES.md`). *An artefact is held when
   Groundwork retains the artefact itself such that its contents can later be re-read.*
   Retaining a value derived from an artefact does not make it held. Held is not strength,
   verification, faithfulness or recency.
2. **The artefact substrate** (`ARTEFACT_READING_SLICE.md`, accepted `9cdb4e6`). `Artefact` is
   minted on encounter; a reading is only ever of a held artefact; `content_hash` is correspondence
   evidence, **never identity**; `as_of`, `encountered_at` and `read_at` are three times.
3. **No silent writing, no silent learning.** Nothing is kept, moved or removed unseen, and no
   standing choice is ever inferred from repeated behaviour.
4. **Absence is not zero.**
5. **The bank window's F6** (`BANK_BROWSER.md` §7). Downloads is where the Save dialog lands and
   what the watcher reads. This pass does not move that.
6. **Local-only AI** (Rob, 2026-09-25). The cloud AI path is being removed from LTS and 2.0: all
   local, or no AI. Decided, not yet built.

---

## 2. The surface today — measured 2026-09-25

| where | what it does | which state |
|---|---|---|
| every import path | parses the file and commits transactions. **No import mints an `Artefact`**; no bytes are kept | DOWNLOADS only |
| the Historian (`log_historian_event`, 18 call sites) | logs payments, suggestions, insights, decisions. **No call site logs an import** | nothing records that an import happened, or from what |
| `PdfExtractCache` | a PDF's **extracted values** keyed by SHA-256 | C3's middle state: value retained, source not. Not held |
| `Artefact` | ruled and accepted; **no production code creates one** | — |
| `Artefact.held` | a boolean **stated at mint** | cannot distinguish *was held* from *is held*. See D3 |
| `/api/auto-import/delete-file` | **permanently** deletes a Downloads file (the invalid-file path) | the only file deletion today, and not to the Recycle Bin |
| backups | `shutil.copy2` of the single `.db` file | a store outside the database would silently fall out of every backup |

Today Groundwork **holds nothing**, and does not even record which file an import came from.

---

## 3. Findings

### Ready to accept, as the review found them

**D1 — Retention is the user's act, at the moment they can judge it.** After a successful import,
*"Keep a copy of this file in Groundwork?"* No default-yes, no quiet retention, no bulk retention
after the fact. **The decision attaches to that encounter / import, never to the hash [Rv4]:**
*"I kept this statement last time"* never becomes *"keep this new encounter too"* (D9 protects the
same line from the other side).

**D2 — Retention and Downloads removal are two independent decisions [Rv5].** A combined prompt
is acceptable UX (*Keep in Groundwork and remove from Downloads* / *Keep, leave Downloads alone* /
*Don't keep*), but semantically there are two answers, and *retained + still in Downloads* is a
legitimate state: two physical copies, one retained artefact. Any removal of the Downloads copy
that Groundwork performs goes to the **Recycle Bin**, never straight to permanent deletion.
**Atomicity, as an invariant, not a design:** *a successful move into custody means the retained
source exists before the original is removed from Downloads.* Groundwork may never claim a
retained source whose copy failed, nor remove the original before the retained copy is
established.

**D4 — Custody ending is not retraction.** Retraction withdraws what was **derived**. Custody
ending withdraws **possession** and nothing else. Transactions, readings and every claim stand;
what changes is what Groundwork can **produce**. **Two provenance states, never conflated
[Rv3]:**

| state | produced by | effect |
|---|---|---|
| **source unavailable** | custody ended (D3) | the reading and everything derived stand; provenance says the source is no longer retained |
| **source evidence invalidated** | a bad reading, a demonstrated parser error, later contradicting evidence | the existing retraction / correction machinery, never triggered by custody ending |

The crossing test: custody ending treated as invalidation is caught, and no derived claim or
record may change.

**D6 — What retention promises, and what it does not [Rv8] [Rv9].** Claim A: *the retained bytes
are the byte sequence Groundwork encountered.* The recorded hash can establish that. Claim B:
*the document is genuine, correct, faithful or authoritative.* Retention never establishes that
(fixed 1). **Whenever Groundwork relies on the retained file as the retained artefact**, it
verifies the bytes still correspond to the recorded artefact, and a mismatch is reported, never
silently accepted. Which operations count as "relying on" is not fixed here: parsing and
producing it as a source do; incidental OS reads are not artefact readings.

**D9 — Duplicates are correspondence, not identity.** Two encounters with identical bytes are
two artefacts until a correspondence says otherwise. The UI may say *"you already kept this
statement"*. It may not merge them silently.

**D10 — The retained source never leaves the device and never enters model context [Rv13].** The
retained artefact itself is never placed in a model's context or transmitted anywhere. What a
model may see is Groundwork's **readings** of it (extracted, source-tied lines), because
statement text is third-party-authored (S11, untrusted text into a model) and too large for a
local model's context. Local-only AI does not change either reason. The existing PDF
extraction's cloud preview sent **derived text**, never the retained file, and is scheduled for
removal with the rest of the cloud path. It was never a custody transfer. **Encryption at rest is
its own question [Rv7-gate].**

**D11 — Not decided here:** where the store lives, its layout, naming, and any *Statements*
browser.

### Principle accepted, wording tightened

**D3 — Custody ending ends current custody; the custody history remains [Rv2].** Two facts, never
one:

```text
"Did Groundwork ever retain this source?"     the custody history   - yes, from encounter to T
"Can Groundwork produce this source now?"     current custody       - no, custody ended at T
```

The first draft said `held` stays true after removal. The review showed that uses `held` for both
facts. `held` as ruled (fixed 1) means *Groundwork retains the artefact*, a current-state
predicate, and after custody ends that is no longer true. But flipping it to false would rewrite
history into *"never held"*, which is also false.

**The ruling sought is the semantics, not the representation:** *custody ending does not erase
the fact that the artefact was held; it ends current custody; the custody history remains.*
Whether `held` stays the mint-time fact beside a custody-ended event, or is split into
*custody established* and *currently held*, is a representation choice for a later build. It is
named as an **ontology question** (`Artefact.held` was minted before custody could end), not
answered here. D8's restore problem turns on the same distinction.

**D5 — Removal authority, as three questions [Rv6] [Rv7]:**

1. **Who may end custody?** The user. Either directly, or through a policy **the user
   established**, which may then perform removals the user authorised in advance. That is the
   intended model, stated so that "the user, and nothing else" and "a policy may remove" do not
   contradict. No age, size or *"imported long ago"* rule acts on its own authority.
2. **May a user-authored retention policy exist at all?** Rob's call.
3. **The sole-provenance condition.** *Principle, as a candidate:* an automatic policy must not
   end custody of a retained source when doing so would destroy the user's only retained
   provenance for a currently visible record. **Mechanism: open.** Proving *"the only source for a
   visible record"* needs record-level provenance, and this pass rules only the import-level link
   (D7). One import can consume several artefacts and produce hundreds of records, so batch-level
   provenance cannot decide it. Ruling the mechanism here would smuggle transaction-level
   provenance into this pass.

**D7 — The minimal link, phrased so it manufactures nothing [Rv10].** This pass may rule: *an
import operation has a relationship to the artefact it consumed.* It does **not** rule that the
import batch is the semantic source of any transaction. How readings and derived records inherit
that relationship, and a display like *"Source: March 2026 statement"*, belong to the later
provenance work, named, not opened.

**D8 — Honest restore is mandatory; (a) or (b) is Rob's [Rv11].** The invariant, whichever
option: **a backup / restore may never produce a database that claims current possession of
source bytes the installation does not have.**

- **(a)** the retained store is part of backup and restore, so a backup is a complete Groundwork
  state. Keeping retained bytes **in the database** would give this for free, since backups copy
  the database file.
- **(b)** the store is excluded. A restore then must distinguish *never retained* from
  *retained historically, not present in this restore*: D3's two facts again.

---

## 4. Independent of the custody ruling — two items from the same day

Both hold under **N** or **M**, touch no custody semantics, and need no `held` decision.

**H1 — Log each import in the Historian.** Today nothing records that an import happened. One
event, *import committed*, carrying the file name, its content hash (correspondence evidence,
never identity), the account, the record count and the date range. It gives batch-level *"where
did this come from"* even when the file is never retained. Recording a fact about an import is
not retaining its source (C3).

**H2 — Offer to remove the downloaded file after import, with a standing choice.** After a
**successful** import of a file the watcher offered:

> *Remove chase_sept.qfx from your Downloads? Your transactions stay in Groundwork.*
> **Remove** / **Keep** / **Always remove**

- It names **the file**, never the transactions.
- ***Always*** is the user's standing decision, made once and knowingly. It shows as a Settings
  toggle (*"After importing, remove the downloaded file"*) that can be turned off. It is set only
  by that button or that toggle, **never inferred** from repeated *Remove* clicks (no silent
  learning). Each later removal still shows a notice, so it never happens unseen.
- It acts only after a successful commit; never on cancel, failure or a closed review. It acts
  only on the exact file imported, with its hash re-checked immediately before removal, so a newer
  download with the same name is never touched. It goes only to the **Recycle Bin**, and only
  inside the Downloads folder.
- **Statements get their own choice**: *Always* applies per kind, so removing CSVs never implies
  removing PDF statements.
- It naturally covers watcher-offered files only. A file chosen by hand arrives with no path, and
  is where the user put it.
- The Historian records each removal (H1's companion event).
- **Build note, not a design:** today's delete route unlinks permanently. H2 needs a Recycle-Bin
  path on all three OSes (likely `send2trash`, a new dependency).

H2 is exactly the Downloads-tidiness half of D2 **without** retention, and Rob's own practice
(deleting downloads by hand) is the use it serves.

---

## 5. Cases

| # | situation | expected |
|---|---|---|
| Dc1 | import, *keep and remove from Downloads* | one held artefact, hash recorded; the Downloads copy to the Recycle Bin **only after** the retained copy is established; the import linked to it |
| Dc2 | import, *don't keep* | nothing minted; transactions exactly as today; H1's event recorded |
| Dc3 | custody of a retained statement ends | transactions, readings, claims unchanged; a dated custody-ending event; the artefact **remains known as having been held**; current custody absent; provenance reads *no longer retained* [Rv15] |
| Dc4 | **the crossing test**: custody ending treated as invalidation / retraction | caught: no derived claim or record changes |
| Dc5 | the retained file altered on disk | reported when Groundwork next relies on it; never silently accepted as the same artefact |
| Dc6 | *candidate future invariant, not a gate* [Rv16]: an automatic policy would end the sole retained provenance of a visible record | refused. **Depends on record-level provenance, not ruled here** |
| Dc7 | backup / restore under D8 (a) / (b) | (a) restored custody is real; (b) *retained historically, not present in this restore*, never *held now* and never *never held* |
| Dc8 | the same statement kept twice | two artefacts, one hash, the UI says so, no silent merge |
| Dc9 | no statement kept for April | *not retained*, never *no April statement* |
| Dc10 | a PDF, kept | the extract cache's values and the retained file both present, never read as one another (C3) |
| Dc11 | a *move into custody* whose copy fails | no retained artefact is claimed; the Downloads original untouched |
| Dc12 | H2: *Always remove* on, the file replaced by a newer download of the same name before removal | the hash check fails; the file is left alone |
| Dc13 | H2: the import is cancelled after the offer | nothing removed, whatever the standing choice |

---

## 6. Readings

- **N**: no managed custody. Groundwork keeps values, never sources. H1 and H2 still apply.
- **M**: explicit, user-governed custody: D1–D10 as revised.
- **A**: automatic retention with age cleanup. **Refused:** age does not establish uselessness,
  and automatic cleanup cannot establish what is safe to remove. So A is not a real third
  option. **The real question is M versus N [Rv17].**

---

## 7. Ruling sought — Rob

1. **Custody model:** M or N? If M: *Groundwork may retain a source artefact only following an
   explicit user choice at import.*
2. **Downloads:** retention and Downloads removal as separate decisions, the combined prompt
   acceptable, any Groundwork removal of the Downloads copy to the Recycle Bin, and the atomicity
   invariant?
3. **Custody ending:** *removing a retained source ends current custody, does not erase the fact
   that it was held, and retracts nothing derived from it.* The representation left open, and
   `Artefact.held` named as an ontology question.
4. **Retention policy:** may a user-authored policy exist? If yes, is the user's prior
   authorisation enough for later automatic custody-ending, subject to the sole-provenance
   principle, with its mechanism left open until provenance is ruled?
5. **Backup:** (a) the store is part of backup and restore, or (b) it isn't and a restore records
   the sources as unavailable? Either way, no restored state claims bytes it does not have.
6. **Provenance scope:** only *import ↔ the artefact it consumed* in this pass; transaction ↔
   reading ↔ artefact provenance and its display deferred by name.
7. **Encryption at rest:** its own question.
8. **H1 and H2 (§4):** buildable now under either custody answer?

---

## 8. Ruling — Rob, 2026-09-25

| item | ruling |
|---|---|
| **1. Managed source custody** | **Yes: M.** Explicit retention only. No default, no silent retention, no inference that an imported file must be kept |
| **2. Keep vs. remove from Downloads** | **Separate decisions.** Groundwork's removals go to the Recycle Bin, and the retained copy must exist before the Downloads original is removed |
| **3. Custody ending** | **Ends current custody, preserves the custody history, and is never retraction** |
| **4. User retention policy** | **Permitted, and user-authorised only.** *User-authorised policy: yes. Groundwork-invented cleanup policy: no.* The sole-provenance principle stays a **future provenance constraint**, not a requirement of this pass |
| **5. Backup** | **(a): retained source documents are part of the backup / restore state.** A size warning before backup is appropriate; the backup-store architecture belongs to the storage pass |
| **6. Provenance** | **Import → artefact only:** *this import consumed this source artefact.* `transaction → reading → artefact` is deferred |
| **7. Encryption** | **A separate future question** (storage, backup format, keys, restore, portability) |
| **8. H1 / H2** | **Build now, as SEPARATE authorisations** |

**The combinations under ruling 2.** Once a store exists: *keep in Groundwork + remove from
Downloads*, *keep in Groundwork + leave Downloads alone*, *don't keep + leave Downloads alone*.
The fourth, *don't keep + remove from Downloads*, is **H2**, authorised on its own terms under
ruling 8. Until the store is built, H2's prompt is the only one a user sees.

**Preserved, as Rob asked: the semantics are ruled; the field representation isn't.** D3's two
facts (the custody history and current custody) are ruled. Whether `Artefact.held` stays a
mint-time fact beside a custody-ended event, or is split, is **unresolved**, and no build may
settle it by default by making the old boolean carry both meanings.

**H1 and H2 are separate build authorisations, not the custody implementation.** Building them
is no evidence that the source store is authorised. **H2's *Always* is a Downloads-cleanup
policy, never a retention policy:** *"always remove from Downloads" does not mean "always retain
in Groundwork"*, and no build may let it become that.

**Not authorised:** the source store, its location and layout (D11), the `held` representation,
encryption, record-level provenance and its display.

**Next:** build H1, then H2, each gated on its own. The source store waits for its own storage
pass.

---

## 9. H1 built — every import recorded in the Historian (2026-09-25) — ACCEPTED (Rob, 2026-09-26)

A separate build under ruling 8, **not** the custody implementation: nothing here retains a source.

- **`server.py`:** the import commit writes one `import_committed` Historian event **inside the
  commit's own transaction**, so the record exists exactly when the import does. The context is a
  fixed set of keys: file name, `content_sha256` (correspondence evidence, never identity; kept
  only when well-formed, otherwise recorded as unknown), origin (`watcher` / `manual`), account,
  records, created, duplicates, errors, first and last date. **Never the file's content, and never
  an `Artefact`.** An empty commit is not an import and records nothing. A commit of all
  duplicates is an import, and is recorded.
- **`launch.py`:** the watcher hashes the **raw bytes on disk**, which it already reads. The page
  cannot, because it rebuilds a `File` from decoded text, which hashes differently. A statement's
  bytes stay unread by the watcher, as the bank window's F7 ruled; the page hashes a statement
  only after the user says yes.
- **`app.js`:** the commit carries `source_file` (name, hash, origin). A watcher-offered file brings
  the watcher's raw-bytes hash; a hand-picked file is hashed from its own bytes.
- **`core/database.py`:** `import_committed` added to the Historian's category registry.

**The privacy pin.** Filenames can carry account digits. `import_committed` is touched in
`server.py` by its writer alone, so the event reaches no prompt-building function. s127 fails if
any other function reads it.

**Measured in the real page** (the worktree's dev server): a hand-picked CSV recorded origin
*manual* with the browser's SHA-256, which matched Python's over the same bytes. A watcher-offered
file recorded origin *watcher* with the watcher's hash carried through, not re-derived from the
decoded text.

**Gate:** s127 17 / 0 standalone, three mutations each caught (the file's content put into the
event; an Artefact minted by the commit; the event read by a prompt-building function). Full gate
**1729 / 0** (1712 + 17).

**H1 ACCEPTED — Rob, 2026-09-26**, as built at `ca14f82` (gate 1729 / 0), with the privacy pin as later
widened by H2 to name its import check (§10). It authorises nothing of the source store.

**The sequence this leaves:** *import → Historian record → the user's Downloads decision (H2) →
optional, separate source retention (not built)*. H1 is not a back door to custody.

---

## 10. H2 built — the user's Downloads copy, removed at the user's word (2026-09-26) — ACCEPTED (Rob, 2026-09-26)

A separate build under ruling 8, **not** the custody implementation: nothing is retained, and no
Groundwork custody exists to end (Groundwork never had the file). *"Always remove from Downloads"*
is a Downloads-tidiness policy, never a retention policy.

- **`recycle_bin.py` (new):** sends one file to the OS Recycle Bin / Trash through a library each
  build already ships: `SHFileOperationW` with `FOF_ALLOWUNDO` (Windows, `ctypes`),
  `NSFileManager.trashItemAtURL` (macOS, PyObjC), `Gio.File.trash` (Linux, PyGObject). **No new
  dependency, and no permanent-delete call anywhere in the module.** If the bin is unavailable,
  the file is left exactly where it was.
- **`POST /api/auto-import/remove-download`:** refuses anything outside Downloads, anything but a
  bank file or statement, and a malformed hash. It accepts **only a file that was imported**: an H1
  `import_committed` event from the watcher for exactly these bytes. A hand-picked import does not
  authorise it. **A file changed since import** (a newer download under the same name) is left
  alone; *gone* is reported, not an error. Each removal writes a `download_removed` Historian event
  (file, hash, whether it was the standing choice), touched by its writer alone.
- **The page:** after a **successful** commit of a watcher-offered file only: *"Remove X from your
  Downloads? Your transactions stay in Groundwork."* **Remove / Keep / Always remove bank files**
  (or *statements*). *Always* is **per kind** (bank files and statements separately), shows as two
  checkboxes in Settings → Automation (*After importing from Downloads*), and is written **only**
  by that button and those checkboxes, never inferred from repeated removals.

**Measured, on Windows:**
- `recycle_bin` put a probe file in the real Recycle Bin.
- In the real page, three test files of this session's own went through end to end: *Remove*
  (the file left Downloads and appeared in the Recycle Bin, with the notice); *Always remove bank
  files* (the setting became bank files only, statements untouched, and the file was removed); the
  next import removed **without asking**, with the notice; the Settings checkboxes showed the
  choice, and unticking it cleared it (*"Groundwork will ask each time"*).
- **Found while testing:** the dev database crashed on start because V2 had added two columns
  without a `SCHEMA_VERSION` bump, the same crash any upgraded 1.1 user would have hit. Fixed on both
  branches before H2 continued (`125b020`, `e60e726`, with the new s51 pin). The dev database's
  later upgrade was one more real proof.

**Gate:** s128 21 / 0 standalone, five mutations each caught (the import check skipped; the hash
check skipped; a permanent-delete fallback; the event read by a prompt builder; *Always* inferred
from repeated removals). **The first full gate came back 1790 / 6, all in these sections, none a
behaviour fault:** H1's privacy pin surfaced H2's route as a new reader of `import_committed` (it
reads it only to confirm an import; now named in the pin with its reason, so any other reader still
fails); an H1 check matched code text H2 reworded; and an H2 check assumed zero Artefacts in the
whole database, true standalone but not after other sections mint theirs (now a before / after
count). Rerun: **1796 / 0**. Then rebased over V4 (`app.js`) and gated again: **1806 / 0**, the tree pushed.

**Not covered:** macOS and Linux trash, which are written against their platform APIs but not run
here, and statements through H2 end to end in the page (the route and the per-kind choice are
covered by s128).

**H2 ACCEPTED — Rob, 2026-09-26**, as built and gated (1806 / 0 on the tree pushed). The
acceptance covers H2 only. It authorises nothing of the source store, and *"Always remove"*
remains a Downloads policy, never retention. Still open, by name: macOS and Linux trash on real
machines, and a statement through H2 end to end in the page.

