# Item 45 stage 1: the health privacy enforcement point (H6)

Opened 2026-10-12. Rob authorised stage 1 on 2026-10-11 (*"Stage 1 only"*) and again on 2026-10-12 (*"I accept rule 45
stage 1"*). **By the 2026-10-09 decision in `HEALTH_REVIEW.md` §7, H6 is complete only when:**
1. its **design is approved** (this document);
2. its implementation is authorised (done);
3. its acceptance tests pass.

**P1–P9 RULED 2026-10-12 (Rob: "I approve P1 - P9. These features were evaluated looked through and worked through.").** The design is approved and the build is authorised (stage 1). Nothing here names a person, a
medication or a diagnosis, and H6 is the gate that must stand before anything does.

## 1. What counts as health-sensitive (measured 2026-10-12, master)

| Class | Where it lives today |
|---|---|
| **A. Health records** | `healthcare_expenses`, `expense_obligation_versions`, `person_assignments`, `person_enrolments`, `health_plans`, `health_plan_term_versions`, `health_plan_operations`; `historian_entries.healthcare_expense_id`. Built as record layer only, with no screen (HEALTH_REVIEW §1d). |
| **B. Health spending in the ledger** | Transactions in the protected health categories (Pharmacy, Doctor, Dental, Medical, Medications, Prescriptions, Therapy, Healthcare...: `core/solution.py` `is_protected`, list v3 from item 47). The **merchant and description** say who and where (*"CVS PHARMACY #1234"*, *"MERCY HOSPITAL"*). |
| **C. Derived** | Anything computed from A or B: a category total, a month's pharmacy spend, a protected-category note in a report, a Historian context that names the category. A record with no name can still disclose, through its merchant or by inference (§7's requirement 1). |
| **D. Person** | `persons` and `person_aliases`, the household's own people. Not health on their own; health once joined to A (H6 fences that join). |

## 2. The inventory of flows and sinks (measured)

Counted across the app's Python (`server.py`, the window modules, the importers, `core/`), plus the page.

| # | Sink | Count | What can reach it today | Rule (P-point) |
|---|---|---|---|---|
| S1 | **Logs:** `groundwork.log`, `startup.log`, prints | 62 logging calls + 10 prints | Error messages; some format request bodies or rows. No check stops a merchant or category from being logged. | P2 |
| S2 | **Exports:** `/api/settings/export-to-file` (JSON / CSV), and report printing | 1 route, 3 downloads | Every transaction, health ones included; the AI log only when ticked (item 62 G5) | P3 |
| S3 | **Backups:** `/api/backup` create / restore / upload, and the recycle bin | 4 routes | The whole database, A–D included. They stay on the person's computer, at the place they choose. | P4 |
| S4 | **Model context:** the prompts the local model is given | 9 server-side builders, plus page-side `callAI` data lines | Category totals by name; merchant names on some surfaces | P5 |
| S5 | **The AI log (item 62)** | 1 writer, `_ai_log_write` | Every prompt as sent, so whatever S4 carried | P6 |
| S6 | **Diagnostics:** the ⚑ Report button | 1 (page) | The error log text, which is whatever S1 carried | P2 + P6 |
| S7 | **Outbound network** | 20 | Ticker symbols, a state, place names, update check; bank and Google windows opened on a click. **No health class reaches any of them today.** | P7 |
| S8 | **The Historian** | `log_historian_event` callers | Category ids and amounts in context JSON. Persisted, local. | P8 |

## 3. Points for ruling

**P1. One enforcement point.** A single module, `core/health_boundary.py`, owns:
- **the classifier:** is this row or text health-sensitive (classes A–C)? It reuses the one protected list, never a
  second one.
- **the scrubber:** it replaces health-identifying text (a health transaction's merchant and description, a health
  record's fields) with its class: *"[health: Pharmacy]"*, *"[health record]"*.

Every sink in §2 calls it. Nothing else decides.

*Recommended.* It is design F1 in `HEALTH_TRUST_BOUNDARY.md`: one place.

**P2. Logs carry no health content.**
- A logging filter on every Groundwork handler, at startup, passes each record through the scrubber.
- A rule test fails the gate if any logging or print call formats a transaction's description or merchant, or a
  health record's fields.
- Since the Report button sends the error log text, S6 is covered by the same filter.

*Recommended.*

**P3. Exports leave health rows out unless included** (design rule 4).
- Export-to-file gets an *"Include health spending and records"* tick, off by default, like item 62's AI-log tick.
- **Unticked:** health-category transactions are left out, and class A tables are never exported.
- The file states what it leaves out, and how many rows.

*Recommended.*

**P4. Backups say what they hold** (design rule 6). A backup copies everything, because it exists to restore
everything; a backup without health records would lose data.
- The backup screen and the restore screen state plainly: *"A backup contains everything, including health spending
  and records. Keep it somewhere private."*
- Backups never leave the computer unless the person moves them. Groundwork uploads nothing.

*Recommended.*

**P5. The model sees health spending only as a total.**
- Every prompt passes the scrubber before the model gets it.
- A health category may appear by its category name and amount (*"Pharmacy: $84"*): it is the person's own budget,
  and the reports already show it.
- Merchants, descriptions and class A fields never appear.

*Recommended.* The model runs on the computer, but its context is what reaches S5, and S5 is persisted and
exportable.

**P6. The AI log stores only what passed P5, and is the named regression case.**
- `_ai_log_write` scrubs again before writing (defence in depth).
- The test feeds a prompt containing a pharmacy merchant and a class A field, and asserts the stored row holds
  neither. This is the §7 requirement that item 62's log be an explicit test case.

*Recommended.*

**P7. Outbound requests are fenced.**
- Each outbound call in S7 is listed with what it may send.
- A test asserts that no outbound builder accepts a transaction or health record as input.

Today none does, so this freezes a property that already holds.

*Recommended.*

**P8. The Historian keeps health as it keeps everything else, on the computer.**
- It is a local record, the person's own, like the ledger.
- Its context never carries a merchant or description for a health-category event; it carries the category id and
  amount, as it already does.
- It is included in P3's export rule.

*Recommended.*

**P9. Completeness you can check: the reconciliation test.**
- A registry, `HEALTH_SINKS` in `core/health_boundary.py`, lists every sink in §2 by file, function and kind.
- The gate test scans the code for sink patterns (the same ones §2 counted: logging and print calls, file writes,
  `send_file`, outbound URL calls, AI-log writes, export builders).
- It **fails if any sink is not in the registry, or a registered one has gone**. A new logging, export or network
  path cannot slip past: it fails the gate until someone registers it and says how it is enforced.

This is §7's *"verifiable, not a statement in a document"*.

*Recommended.*

## 4. Not in stage 1

- **Named people, medications, diagnoses, the visit report, plan-year tracking:** H7's later stages, each its own item
  and ruling. **H6 being done authorises none of them.**
- **Encrypting the database or backups at rest.** That is a larger question (keys, recovery). Recorded, not proposed.
- **1.x:** master only (L1; nothing here is a data-loss or wrong-figure fix).

## 5. Acceptance tests (the gate H6 needs)

The tests, as §7 lists them:
- the inventory and the reconciliation (P9);
- each sink's enforcement: logs (P2), exports in and out of the tick (P3), backup statements (P4), model context
  (P5), the AI log regression (P6), outbound fences (P7), Historian context (P8);
- a **derived-disclosure** case: a pharmacy transaction's merchant must not reach any sink, even though the
  transaction names no person.
