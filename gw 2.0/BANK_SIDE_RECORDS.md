# Item 93 — Bank-side record creation: what an import is, and what may come of it

**OPENED 2026-10-17 (Rob: "Open item 93 — Bank-side record creation"; ahead of stage 6). A design and ruling item for
the general import model, not only for health. RULED 2026-10-17 (Rob: "I approve item 93 b1 - b12"). B5 and B7 count as data-loss fixes for
1.x under L1 (Rob: "they may count as data loss in 1.x"). No build authorised: each stage is authorised separately.**

## Summary

Every imported bank line is the bank saying that money moved. Groundwork already has careful rules about what that
does and doesn't make true:
- a bank line is the bank's statement, not a payment (T2, 2026-09-14);
- a payment exists only when the household says it does (Pm2);
- similarity suggests a match and never proves one;
- only the household's say-so creates an expense (September 2026);
- a reversal is a claim about a payment, not a new kind of thing (item 3).

The import code was written before those rules and doesn't follow them yet:
- **Duplicates:** it decides that two lines are one by similarity and silently drops the second.
- **Edits:** a person's edit overwrites what the bank said.
- **Deletions:** deleting a line destroys it.
- **Pending charges:** a pending charge is overwritten when it posts.

Nothing in the import creates payments or expenses, because the 2.0 records aren't used yet. That's why item 92's
"who was this for" answers had to be tags.

This item sets the boundaries the import has to keep:
- between the bank's statement and a payment;
- between imported evidence and an expense you establish;
- between a possible match and a confirmed one;
- between keeping a source file and the records drawn from it;
- between existing records and corrections, reversals and duplicate imports.

It also rules the one thing every earlier pass left fenced: the **importer contract**, meaning what a household may
authorise an import to do on its behalf, so twelve autopay lines a year don't need twelve separate answers. Item 20
(source-document custody) is unchanged. This is design only. The build, if ruled, would be staged and each stage
authorised separately.

## 1. What the import does today (measured on master `e447509`)

| Step | Today | The rule it meets or misses |
|---|---|---|
| Duplicate check | The bank's own id (QFX FITID) matching an existing row: skipped. Otherwise the same account, date, type and amount (±$0.005) with a "fuzzy" description match (`_descriptions_match_fuzzy`, a 20-character shared prefix): **skipped and only counted** (`server.py` ~15108) | The bank id is the bank's own correspondence evidence (T2/T3). The fuzzy match is **similarity deciding identity**, and a real second charge that looks like the first is lost without being shown |
| The row | One `transactions` row per line, holding what the bank said | The bank's statement (T2), kept as a 1.x row |
| A person's edit | `PATCH /api/transactions/<id>` **overwrites** date, description, amount and category in place | Overwrites the bank's statement with the household's correction; the bank's version is gone |
| Deleting | `session.delete(txn)`: **gone**, with no history | History is destroyed |
| Pending then posted (Tx4) | The posted line replaces the pending one in place | T2 keeps both, each with its date |
| Category | Set by rules at import; changed by the person | A source's category is a candidate, never a claim (decision 9); the review moves rows only on a yes (items 54, 85) |
| Reversal / chargeback | A new line, with nothing linking it | Item 3: a reversal is a claim about a payment, never its own identity |
| Payments and expenses | None created: the 2.0 `payments` and `expenses` tables are empty in production | Pm2 and the September rule hold, but only because nothing is built |
| Linked records | "Attach as debt payment" (the person links a row to a debt), work reimbursements (item 72) and `care_for` tags (item 92) are each the household's statement, stored on 1.x rows | Each is a household assertion with no 2.0 home yet |
| Source file | Item 20: kept only on the person's word; H1 logs the import, and H2 moves a file from Downloads to the Recycle Bin, never deleting it | Unchanged here |

## 2. Points for ruling

### The bank and its statement

**B1. A bank line is the bank's statement, and Groundwork keeps it as the bank said it.** The imported row records
what the statement said, which file and import it came from, and when. Nothing the household later says rewrites
it (B6). *Recommended.*

**B2. The bank is a party once, per account, by the household's word.** An account's institution becomes a party
when you confirm it once:
- *"Is this account at Superior Credit Union?"*, with the existing institution text offered as the candidate.

Its established roles are holding the account and being the source of the statement. A bank's identity never
establishes a provider, a creditor, a patient or an obligation, and it never settles an uncertain relationship.
*Recommended.*

### Payments, and the importer contract

**B3. A bank line becomes a payment only by the household's statement, given one of two ways:**
- **One line at a time.** Your answer, for example "that was my payment to AEP", or "for Sam" (item 92), is the
  statement.
- **A standing statement, the importer contract.** You say once, explicitly: *"Treat every debit from Joint Checking
  to AEP OHIO as my payment."* Each standing statement:
  - is scoped to an account, a payee as you name it, and debits;
  - is dated, listed on the Accounts tab, and can be withdrawn;
  - turns each line it covers into a payment by your statement, recorded as such;
  - is never invented: Groundwork may *suggest* one after you've answered three lines from the same payee, and
    creates it only on your yes.

The importer never creates a payment from its own guess. Withdrawing a standing statement stops new lines; it
doesn't undo payments already recorded under it, which stay recorded with the statement they came from.
*Recommended.*

### Expenses

**B4. Only your say-so creates an expense, and a payment is never assumed to be one.** An expense (a visit, a
purchase) exists when the household names it:
- "that was Sam's visit";
- a bill you bring in and confirm (item 94);
- a receipt you keep.

A payment can be *toward* an expense (`payment_in_respect_of`, ruled), and several payments can be toward one, or
none. A purchase with no separate payment record, such as a card swipe, is still one expense plus one payment, each
from your statement. *Recommended.*

### Possible matches and confirmed ones

**B5. Similarity proposes; it never decides.**
- **The bank's own id** (FITID) matching an existing line establishes that it's the same statement imported again.
  This is the bank's correspondence evidence, under the importer contract (T2/T3).
- **A fuzzy match** (same date, amount and similar text) **no longer drops a line silently.** The line is held back
  and listed in the import summary: *"2 lines looked like ones already here — Clark Gas, $42.10 on Mar 3. Bring
  them in?"* It is brought in only on a yes, and never lost.
- **Matching a line to a payment, an expense, a bill or a debt** is always a suggestion until you confirm it.

*Recommended.*

### Corrections, reversals, pending lines and deletions

**B6. The household's correction sits beside the bank's statement, never over it.** When you edit a date,
description, amount or category, the edit is kept as your correction, dated, with the bank's version underneath.
Every total uses your correction, and the earlier versions stay visible. *Recommended.*

**B7. Deleting hides; it never destroys.** A deleted line is set aside, with when and (optionally) why. It drops
out of every total and can be restored. Lines brought in by a mistaken import can be removed as a batch, set aside
the same way. *Recommended.*

**B8. A reversal is linked only on your word.** A reversal or chargeback line is a new statement. Groundwork may
suggest *"This looks like the reversal of the $48.20 on Mar 12"*. Linking the two is your claim (item 3). Nothing
is netted off on its own. *Recommended.*

**B9. A pending line and its posted line are both kept (Tx4).** The posted line becomes current for totals, the
pending one stays with its date, and a changed amount (pending $48.20, posted $51.90) is shown, not overwritten.
*Recommended.*

### Custody and derived records

**B10. Item 20 is unchanged.** A source file is kept only on your word. Ending custody ends current custody: it
never deletes or rewrites the records drawn from the file, and their provenance then says *"source no longer
held"*. How an artefact records past versus current custody (`Artefact.held`) stays the open representation
question item 20 left, and it is not decided here. *Recommended.*

### What becomes of the records already kept as household statements

**B11. They are absorbed later, unchanged in meaning.** Item 92's `care_for` tags, "Attach as debt payment" links
and item 72's reimbursement matches are each a household statement on a 1.x row. When B1 to B9 are built, each
becomes the same statement in the 2.0 records:
- a `care_for` tag becomes a payment, an expense minted by that answer, `incurred_by` the person, and the bank line
  concerning the payment;
- each keeps its original date, and nothing new is inferred along the way.

*Recommended.*

**B12. The scope is every import, not health.** Bank files (QFX, CSV, OFX), the in-app bank window, Quicken files and
the agent's fetches all follow these rules. Health uses them like everything else. *Recommended.*

## 3. Left out, on purpose

- **The matcher's own design:** how candidates are scored and ranked. B5 says only what a candidate may and may
  not do.
- **Statement lines inside a held PDF:** that is the document line, item 18, stage 3.
- **The bill that lands:** item 94 builds on this.
- **Per-account visibility:** its own item (2026-08-13).
- **The 1.x line**, except where a B-point fixes a data-loss risk under L1 (B5's silent drop and B7's destroying
  delete may qualify, which is for Rob to say).

## 4. If ruled, how it could be built, each stage separately authorised

1. **B5 and B7.** No line silently dropped, nothing destroyed. These two lose data today, so they are the obvious
   first stage.
2. **B6 and B9.** Corrections and pending lines kept beside the bank's statement.
3. **B2 and B3.** Banks as parties, and standing statements.
4. **B4, B8 and B11.** Payments and expenses in the 2.0 records, reversals linked on a yes, and the absorption of
   the 1.x statements.

Each stage would have its own smoke section, with mutation checks for:
- a fuzzy duplicate lost;
- an edit overwriting the bank's version;
- a delete destroying a row;
- a payment minted with no household statement.

## Closing

The rules were settled in September. What was left fenced was the importer contract, the one place a household lends
its word to a pipeline. B3 rules it narrowly: explicit, scoped, listed, withdrawable and never invented. The rest of
the item makes the import keep those rules, starting with the two places it loses data today.

## Ruling — Rob, 2026-10-17

- **B1–B12 approved as written.**
- **B5** (a fuzzy duplicate held and shown, never dropped) and **B7** (deleting hides, never destroys) **count as
  data-loss fixes**. Under item 32 L1 they go to 1.x as well as master, shipping as a 1.1.x release.
- **Stage 1 (B5 + B7) is the first build, once authorised.** Stages 2–4 follow, each with its own go-ahead.
- Item 94 stays dependent on stages 3 and 4 (payments and expenses).

## Stage 1 built — 2026-10-17 (B5 + B7; s233; 1.x first, under L2) — ACCEPTED 2026-10-17 (Rob: "I accept item 93 stage 1. Push 1.x and master.")

- **1.x:** branch `lts-b5b7` `4f2492e`, SCHEMA `20261017-lts-import-custody`, gate 1031 / 0.
- **Master:** merged in (`aa52fe4`, `a6e646b`), SCHEMA `20261017-import-custody`, gate 3579 / 0. Master's own
  `server.py` and `migrate.py` were re-applied with the same changes, because its import insert differs from 1.x.
- **B5:**
  - A look-alike line (same account, date, type, amount, similar text) is held in `import_held_lines`, shown after
    the import, and listed in Settings → Data. "Bring it in" uses the importer's own insert; "It's the same" adds
    nothing. Either way the decision stays on record.
  - One decision can cover everything one import held: a file imported twice once meant about 880 look-alikes.
  - The bank's own id (FITID) still says "same line". Two different bank ids now import as two lines.
  - The page's duplicate bot only reports after an import; its toolbar button asks once and sets aside.
  - On master, the `import_committed` event also records how many lines were held.
- **B7:**
  - The Ledger's delete moves the row whole to `set_aside_transactions`, with its full debt-link rows. It is
    restorable with the same id, and a `before_insert` guard keeps any new row (one or a whole batch) from taking a
    set-aside id.
  - Every import line carries `import_batch`, and a mistaken import is set aside together from Settings → Data.
  - Not covered: "Delete all transactions", which takes a full database backup first, and investment transactions,
    which are holdings records, not bank lines.
- **Fixed during the build:**
  - The id guard first gave a whole batch one id.
  - The import summary read held rows after their session closed (a 500 on any held line).
  - A smoke check picked up orphan rows under a reused account id; s233 now selects its own rows by name.
- **Verified in the running app (master):** look-alike held; original deleted and set aside; restored with the same
  id; "It's the same" left one line.

Note 2026-10-17: on master the section is **s234** (`s234_import_custody.py`), because item 95 (the GPU engine,
pushed by another session the same day) took s233. On 1.x it stays s233. Same checks.

## Stage 2 built — 2026-10-18 (B6 + B9; s235; master only) — ACCEPTED 2026-10-18 (Rob: "push")

Rob: "go ahead on stage 2". Master only: under item 32 L1 only B5 and B7 were ruled data-loss fixes for 1.x.
SCHEMA `20261018-bank-versions` (tables `transaction_corrections`, `pending_posted`; column `transactions.pending`).

- **B6, corrections beside the bank's version:**
  - A change to a line's date, description, amount, category or kind (money in / money out) is kept, dated, with
    the value it replaced. The line holds the corrected value, so every total uses your correction.
  - It's kept by a listener under every database write, not by the Ledger's edit route, so a category move on a
    yes, a split or any other path that changes a line can't skip it. Kind (debit/credit) is kept too, because
    flipping it changes every total the same way an amount does.
  - The edit panel shows **Earlier versions**: the earliest version kept, then each change. The earliest version is
    called *"What the bank's file said"* only for lines imported after this build. For older lines it says
    *"The earliest version kept (changes made before Oct 18, 2026 were not kept)"*, because an edit made before
    today left no trace and Groundwork can't claim to know the bank's original.
  - A line set aside and restored keeps its history.
- **B9, pending and posted both kept:**
  - Measured before building: no import read a pending marker at all. Every line came in as cleared. So a Citi
    file's pending charge counted, and when it posted at a new amount the posted line either came in as a second
    charge (counted twice) or, with the same bank id, was **skipped as a duplicate**, leaving the pending amount
    standing for good. The doc's "the posted line replaces the pending one in place" was not what the code did.
  - A bank file's Status column saying *Pending* (Citi's export, or any CSV with a plain Status column) now
    marks the line pending and uncleared. Nothing else is read as pending.
  - **The bank's own id** on a pending line and a posted line says they are the same charge: the posted line
    comes in and counts, and the pending one is set aside whole with its own date and amount. A linked card's
    balance moves by the difference, not twice.
  - **Similarity only asks.** A posted line that looks like a pending one (same account and kind, within 10 days,
    a shared merchant word) comes in, and Settings → Data asks *Same charge / Different charges*. Both count
    until you answer. A yes sets the pending one aside; a no leaves both and isn't asked again.
  - The edit panel of a paired posted line says: *"Pending $48.20 on Mar 12; posted $51.90 on Mar 14. The
    amount changed when it posted."*, and whether the bank's id or you paired them.
  - Restoring a paired pending line undoes the pair (it counts again).
- **Tests:** s235 (20 checks); full gate 3632 / 0. Mutation-checked: with the listener's write removed, five B6 checks fail; with the
  bank-id pairing removed, the posted line is skipped and the B9 checks fail.
- **Named limits:**
  - A pair confirmed by your yes doesn't adjust a linked card's balance figure. The next statement balance sets it.
  - The pairing window (10 days) and the merchant-word match are only what triggers the question, never a decision.
  - Bulk SQL in `migrate.py` that merges duplicate category names moves rows without a correction. It's a
    migration, not a household change.
  - The Ledger's *Delete all transactions* still destroys, behind its full backup. It's untouched by item 93 so
    far.

## Two rulings for stages 3–4 — Rob, 2026-10-18

Building stage 3 surfaced a question no ruling had answered. A payment, an expense, an obligation and an institution are
minted only by an utterance from a **Person**. Groundwork had no way to know which person was answering, and the
existing rulings forbid inventing one ("the implementation may not invent historical facts", OBLIGATION_IDENTITY §9).

- **B13. Who is answering: asked once, remembered, with a switch.** The first time a statement needs a person,
  Groundwork asks *"Who's answering?"* and lists the household's People, or lets you add yourself. It remembers the
  answer on this computer. Settings → Accounts shows who is answering and has a **Change** button. Each statement is
  recorded as that person's.
- **B14. Earlier answers: confirmed once.** Answers given before Groundwork recorded who gave them (care-for tags,
  "attach as debt payment" links, work reimbursement matches) are listed in Settings → Data. A person says *"These
  were mine"*, which becomes their statement today, and each answer keeps the date it was first given. Nothing is
  credited to anyone without that yes.

## Stages 3 and 4 built — 2026-10-18 (B2, B3, B4, B8, B11; s236; master only) — ACCEPTED 2026-10-18 (Rob: "Permission granted")

Rob: "go ahead stage 3 and 4". SCHEMA `20261018-household-statements` (new tables `account_banks`,
`standing_statements`, `ledger_line_records`, `earlier_answers`, `reversal_answers`). These are the first production
writes to the 2.0 records (`utterances`, `parties`, `payments`, `expenses`, `obligations`, `propositions`,
`evidence`). **No total changes**, because nothing reads these records for a figure yet.

- **How a line is recorded.** The ledger line never becomes an identity (Pm2, Tx12). When you say something about a
  line, Groundwork records:
  - a `movement` proposition: the line as the bank stated it, with the bank's party as its subject;
  - the payment your statement minted;
  - a `proposition_concerns` claim tying the two, plus `amount`, `occurred_on` and `paid_to` claims.

  All of these are evidenced by your utterance. 1.x rows are only indexed (`LedgerLineRecord`, `AccountBank`) and
  are never presumed to be the 2.0 thing.
- **B2, banks:**
  - Settings → Accounts asks *"Is it at SUPERIOR CU?"* for each account. The account's institution text is offered as
    the candidate, never taken as the answer.
  - A yes mints the bank as an institution party by the answering person's statement. Naming the same bank for a
    second account points to the same party. *"Not a bank account"* mints nothing, and that account's lines are the
    household's own record.
  - Found while building: the ruled `movement` kind requires an established subject. So a line can't be said to be
    anything until its account's bank is named. Groundwork asks *"Which bank holds Superior Checking?"* first, then
    carries on.
- **B3, payments:**
  - **One line at a time:** the Ledger's edit panel asks *"Was this your payment? To [payee]"* for money out. Money
    in is never "my payment", and a line has one payment at most.
  - **Standing statements:** after three answers for one payee on one account, the panel offers *"Say it once for
    every debit to AEP OHIO from this account?"*. It's only made on a yes. Settings → Accounts lists each standing
    statement (account, payee, how many payments, said when and by whom) with a **Withdraw** button, and has a form
    to make one.
  - The yes is informed: it says how many lines already here it covers. New imports are covered as they arrive. A
    statement matches when the payee text appears in the line's text.
  - Withdrawing stops new lines and leaves every payment already recorded under the statement.
- **B4, expenses:** a care-for answer ("for Sam") now mints an expense from that answer: `incurred_by` Sam, with the
  payment toward it (`payment_in_respect_of`). Changing the person adds a new `incurred_by` claim on the same
  expense, and the earlier one stays. No other payment is ever assumed to be an expense.
- **B8, reversals:**
  - Settings → Data lists money-in lines that may undo a charge, each with the charge. The rule: same account, within
    90 days after the charge, no more than it, at least half of the money-in line's merchant words (4+ letters) in
    the charge, and income lines excluded.
  - *"It undoes that charge"* records the money back as another payment, plus your `payment_counteracts` claim.
    Nothing is netted off.
  - *"No"* is kept, and that pair isn't asked about again.
  - The first rule offered a paycheck as a "refund" on one shared three-letter word. It was tightened before the
    gate.
- **B11, the 1.x answers:**
  - With someone answering, a new care-for answer, debt-payment link or reimbursement match becomes their statement
    at once:
    - care-for → payment + expense + `incurred_by`;
    - debt link → payment + `payment_in_respect_of_obligation`, with the debt's obligation minted once by the
      statement that first names it;
    - reimbursement → both payments + `paid_by` the employer + `payment_counteracts`.
  - With no one answering, or no bank named for the account, the answer is kept exactly as before and waits among
    the earlier answers. It's all or nothing (a savepoint), so nothing is ever half-written.
- **Tests:** s236 (25 checks); full gate 3658 / 0. Every audit of the minting rule stays empty: payments, expenses, obligations, and
  parties with one anchor. Every new claim passes the participant guard, and totals are unchanged. Mutation check:
  with a standing statement's payee scope removed, the "others do not" check fails.
- **Named limits:**
  - Unlinking a debt payment or unmatching a reimbursement later leaves the 2.0 statement in place. A retraction
    (`utterance_retraction`) isn't offered yet.
  - The reversal rule was measured on dev data only. Measuring it on a copy of the live database was blocked by this
    session's permissions, so the first look at real candidates will be yours.
  - The payee box is prefilled with the line's merchant text as a candidate. You edit it before saying yes.
  - Naming a different bank later doesn't rewrite lines already relayed under the earlier answer. Both answers stay
    on record, and the newest is current.
  - Nothing reads the 2.0 records for any figure yet. Item 94 (the bill that lands) can now build on them, once its
    L1–L10 are ruled.
