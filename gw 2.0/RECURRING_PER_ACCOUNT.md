# Item 108 — Read recurring charges per account

Opened 2026-10-22. Rob: *"read recurring charges per account"*.

This was named in item 107's §4 (`SAME_CHARGE_TWO_ACCOUNTS.md`): every engine that reads a recurring charge groups by
payee across all the person's accounts, so one payee paid from two accounts reads wrong. **BUILT 2026-10-22 (§6), awaiting acceptance. RULED 2026-10-22 (Rob: "R1-R10 as recommended, build it"):** R4 (a), R5 (a), the rest as
written. §5.

---

## 1. What is true today (measured 2026-10-22 on master `1cbfdfb`)

**Seven readings group by the payee alone, with no account in the key:**

| Reading | Where | Shown on |
|---|---|---|
| `detect_recurring_patterns` | `server.py:2176` | the Ledger's *Recurring patterns spotted* |
| `trim_candidates` | `server.py:2293` | Lever 4's trim candidates (the solution engine) |
| `recurring_charges`, *"the one rule"* (item 79 U6) | `core/upcoming.py:154` | the Budget page's recurring card and the Calendar |
| `_price_changes` → `price_change.step` | `server.py:3282`, `core/price_change.py:51` | Price changes (item 65 W2) |
| `_yearly_steps` → `yearly_steps.read` | `server.py:3453`, `core/yearly_steps.py:86` | yearly price steps (item 106) |
| `_first_import_findings` → `first_import.renewals` | `server.py:3646`, `core/first_import.py:53` | yearly and twice-yearly bills (W1) |
| `byb_offers` → `byb_offer.new_recurring` | `server.py:12319`, `core/byb_offer.py:30` | Before You Buy's new-recurring offer |

**Measured on the Morgans.** StreamBox $15.49 is paid from the Cashback Visa on the 9th for six months, and from
Everyday Checking on the 3rd for the last three (item 107 D11). The control is the same household with only the Visa
paying.

| Reading | Two accounts | One account (control) |
|---|---|---|
| Ledger: patterns spotted | *"StreamBox $15.49 — seen 9 times"* | *seen 6 times* |
| Lever 4 | **$20.21 a month**: nine charges over six months. That is neither the $15.49 charge nor the $30.98 now paid | $15.49 |
| Budget card and Calendar (`recurring_charges` as of today) | **gone**: the charges sit 6 and 25 days apart, not a month | $15.49 about the 9th |
| Calendar this month (`recurring_charges` from Oct 1) | $15.49 *"about the 9th"* only; the 3rd from checking is missing | $15.49 about the 9th |

**Measured with the functions themselves (synthetic):**
- **A yearly bill paid from two accounts disappears.** An insurance renewal from checking every March and one from the
  Visa every September, for a second car: `renewals` finds the March one alone (*yearly, $539*), and nothing at all
  for both together.
- **A price step on one account is missed.** One account goes from $15.49 to $17.99, the other stays at $15.49:
  `step` finds *$15.49 → $17.99* on the first account alone, and nothing on both together.
- **The BYB offer drops a new subscription.** Paid monthly from one account, it is offered. Add a second account on
  another day and it is not (item 107 §1).
- **`rhythm` reads two monthly accounts as weekly-ish.** Charges on the 9th and the 22nd read *"every two weeks"*;
  the 3rd and the 28th read no schedule at all (item 107 §1).

**What the person has said about recurring charges is all keyed by payee, with no account:**
- `recurring_pattern_confirm` / `_reject` in the Historian (`{'merchant'}`);
- `recurring_items_json`;
- the yearly-bill answers (`yearly_bills_json`) and the yearly-step answers (`yearly_step_answers`);
- BYB's offer key `recurring:<payee>`;
- the budget line a price lands on (`_price_line`, `server.py:3266`, by name).

**Budget lines have no account.** A line names a payee or a category, never an account.

**Not affected:** item 107's check (already per pair of accounts), the record-tidy splits (about categories, not
recurrence), and category totals.

## 2. What it would do

A recurring charge is read **one payee from one account**:
- its schedule, its amount, a price step, a yearly renewal and whether it is new are worked out from that account's
  charges;
- where a payee recurs from more than one account, each one is its own line, named with its account;
- where it recurs from one account, nothing the person sees changes.

What the person has said stays as they said it. Budget lines stay as they are. Totals don't change, because no
transaction moves.

## 3. Points for ruling

**R1. The key.** Every reading in §1 groups by **payee and account**. The payee is still the Ledger key (merchant,
else description), as each reading uses it today. *Recommended.*

**R2. Which readings.** All seven in §1, in one change, so that no two pages disagree about what recurs (item 79
U6's rule, kept). *Recommended.*

**R3. How a payee from two accounts shows.**
- Each account is its own line, with the account named only when the payee recurs from more than one:
  *"StreamBox (Everyday Checking) $15.49, about the 3rd"* and *"StreamBox (Cashback Visa) $15.49, about the 9th"*.
- A payee from one account reads exactly as today.
- Calendar entries are dated by each account's own day.

*Recommended.*

**R4. A card switch is one charge continuing.** Reading strictly per account, moving a subscription from checking to
the Visa would drop it from the Budget card and the Calendar for about two months. The old account's charges age
out, and the new account needs three months of its own.
- **(a)** When one account's charges of a payee stop and another account's start within about a month, at amounts
  within 5%, they are read as **one charge that moved**. It is named with the account it is on now, and it keeps its
  history. *Recommended.*
- **(b)** Strictly per account, with the two-month gap.

It is the same case as item 107 D4: one month with both is a switch, not two charges.

**R5. Budget lines and what the person said stay per payee.**
- A budget line naming a payee covers that payee from every account, as now.
- Every answer already kept by payee (§1) keeps applying to that payee on every account. Nothing stored changes shape,
  and nothing is migrated.
- A new answer given on one account's line is kept the same way, by payee. *"Not a recurring charge"* on StreamBox
  (Everyday Checking) answers StreamBox.
  - (a) by payee, as above. Simple, and no stored shape changes. *Recommended.*
  - (b) by payee and account. Finer, but every store in §1 needs a new key and the old answers need a rule for which
    account they meant.

**R6. Lever 4.** Each account's line is its own candidate, at its own monthly cost: StreamBox $15.49 from checking
and $15.49 from the Visa. That is what the person could stop, one at a time. Lever 4's ranking and willingness rules
are unchanged. *Recommended.*

**R7. Nothing else changes.** AI off changes nothing: these are engine readings with fixed words. The narrator gets the
same facts, now per account. No total, category or budget amount moves. *Recommended.*

**R8. Item 107 stays as it is.** The pair is still said by item 107. This item makes the other pages read the same
pair as two charges, so the two never contradict each other. *Recommended.*

**R9. The Morgans.** No change to the sample. Their StreamBox becomes two lines on the Budget card and the Calendar.
On Lever 4 it becomes two candidates at $15.49, and the Ledger's patterns list shows each with its own count.
*Recommended.*

**R10. Tests and the null models, before it ships.** A new section, s255:
- **The one-account null model:** on households where every payee is paid from one account (the Morgans without
  StreamBox on checking, and synthetic ones), every reading in §1 gives **exactly the same output** before and after.
- **The switch null model:** a payee moved from one account to another stays on the Budget card and the Calendar
  through the switch, under R4 (a).
- **The §1 cases each read right per account:**
  - Lever 4: $15.49 twice, not $20.21;
  - StreamBox stays on the Budget card and the Calendar, on the 3rd and the 9th;
  - the March and September renewals are both found;
  - the price step on one account is found;
  - the BYB offer is made;
  - `rhythm` reads *monthly* twice.
- **What was said:** an existing answer by payee still applies to both accounts' lines.
- **What doesn't move:** totals, budget amounts, categories.
- **AI off:** the same results.

*Recommended.*

## 4. Not decided here

- **Two cards on one account** (`card_last4`). Still one account, as item 107 held.
- **Asking the person which account a budget line is paid from.** Budget lines stay without an account (R5).
- **Merging spellings of a payee across banks** (*NETFLIX.COM* and *Netflix*). Item 107's D1 containment is used
  there only. Each reading here keeps its own payee key, as today. That would be its own point.

## 5. Ruling: Rob, 2026-10-22

> *"R1-R10 as recommended, build it"*

- **R4** (a): a card switch is read as one charge that moved.
- **R5** (a): answers stay by payee.
- **R1-R3 and R6-R10:** as written.

## 6. Built (2026-10-22), awaiting acceptance

**One grouping for all seven readings.** `core/recurring_groups.py` groups a payee's charges by account.
- **R4 (a), card switches:** where one account's charges start within 31 days of another's last, after it, at amounts
  within 5%, the two are one charge that moved. It is named with the account it is on now, and keeps its history.
- **R3, labels:** a payee from more than one account gets the label *payee (account)*. From one account, the label is
  the payee.
- **R5 (a):** every reading keeps the payee as its identity (`merchant` / `payee`, `name` for Lever 4), so budget lines,
  the Ledger's Add and Dismiss, the BYB offer's key and every stored answer still match by payee. Each reading adds
  `label` and `account`.

**What uses the label:**
- the Ledger's patterns list and the Budget page's recurring card show it;
- Calendar entries are titled with it;
- the price-change, yearly-step and yearly-bill sentences and questions use it;
- a price-change tap and a yearly answer send it, so the right account's line is meant;
- a Lever 4 candidate is named with it.

**One answer stored differently, for R5 (a).** A yearly-bill answer (W1) is kept once for each account's renewal of
that payee, in the same shape as before. A yes then puts each renewal on the calendar in its own months; before, only
one entry per payee was kept.

**Measured:**
- **The one-account null model:** every reading in §1 gives **byte-identical output** before and after, apart from
  the new `label` and `account` fields and Lever 4's added `payee`. That held on the Morgans without the checking
  StreamBox, and on a synthetic household with six subscriptions on three accounts, two price steps, two yearly bills
  and shopping from all three.
- **The Morgans:**
  - The Ledger's patterns list shows *StreamBox (Cashback Visa) $15.49, seen 6 times* and *StreamBox (Everyday
    Checking) $15.49, seen 3 times*.
  - Lever 4 has two candidates at $15.49 (it was one at $20.21).
  - The Budget card lists both StreamBox lines (it had dropped StreamBox).
  - The Calendar shows the checking line from November, once it has three months before the month starts, as the one
    rule requires.
  - BYB now offers *StreamBox (Everyday Checking)* as a new repeating charge, since it started in August. That follows
    from R1, and answering it answers StreamBox (R5).
- **Checked in the browser:** the Ledger's patterns list and the Budget card, with no script errors.

**Tests.** s255 covers:
- the grouping: two accounts, one account, a switch, and not-a-switch (a 6% amount difference, or both still paying);
- on the database: the Ledger's patterns, Lever 4 at $13.37 per account, the one rule and the Calendar on each
  account's day, the switch staying on the Budget card and the Calendar, a price step on one account, and a yearly
  bill from each of two accounts;
- R5: a yes kept for both renewals in the same stored shape, and a budget line covering the payee from every account;
- that the pages show the label and send it when answering.
