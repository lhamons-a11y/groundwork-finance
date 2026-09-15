# The transaction referent — what does a transaction refer to, and is that referent an identity at all?

> Status: **Queue item 2, opened by Rob 2026-09-14; one correspondence-wording correction on his
> review; T2 RULED (§7). No build.** Relational
> knowing is closed at `79b817f`. The question was framed at `BUILD_QUEUE.md` §2: *transaction row
> ≠ payment event* and *a transaction can exist without a payment* are ruled; what remains is
> **what exactly a transaction refers to, and whether that referent is an identity at all or a
> relationship to some institution-side record**. This record derives the readings from the
> rulings and the shipped `Transaction` row, tests them, decomposes the 1.x row afterwards, finds
> what the answer defers to later queue items, and ends with a ruling candidate, ruled in §7.

**Rob's caution, carried in:** do it before reversal, because reversal will touch the
transaction/payment boundary — and do not let bank terminology decide the ontology.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Slice 6 §4** | *a `transactions` row is the bank's statement that a transaction occurred* — a value read from a feed or statement: a **P-subject** whose artefact and reading are unrepresented; the purchase is the referent of that statement, not the row; `subject_transaction_id` would put the bank's statement where the world event belongs |
| **Payment slice** | **payment ≠ transaction**: a payment may have no transaction (cash, Pm11); a transaction may be no payment (own-account transfer, Pm12); the bank knows *movement*; a bank line is a **candidate** for a payment, never its minter; a bank line's read claim carries the payment as *not established with candidates* |
| **Slices 2 / 3** | an artefact is a thing encountered — held or asserted — with an origin; a reading is what Groundwork saw of a held artefact; a value read from A has A's origin's authority |
| **Captured-portal ruling** | a live system is *observed, dated, not held*; a capture makes a held artefact **of an observation** and changes reproducibility by custody; **`captured value ≠ captured source`** — retaining a value derived from an artefact does not make the artefact held: *reading retained, referent not* is a third state |
| **Ab7 / `proposition_concerns`** | a statement line is a proposition; which identity it concerns is a claim about the proposition — a payment via `proposition_concerns(line, p)`, asserted, candidates from matches |
| **`proposition_corresponds`** | two propositions from two readings can be two recordings of one claim; contents may differ; institution-side identifiers are correspondence *evidence* |
| **E3 / utterance identity** | one act recorded twice = one recording — the importer recognising *its own prior arrival*; where "same arrival" ends and "two arrivals" begins is the **importer's contract**, fenced |
| **O9** | a process cannot utter; encounter mints nothing; a process's output is not a world object |
| **Slice 6, D1** | *transaction t is health on axis X* has subject **a transaction** — the world event the household was at — not the row; its referent has no identity |
| **Party / identity pattern** | identities are minted by a Person's individuating assertion; institution-side identifiers (account numbers, external ids) are content and correspondence evidence, never identity |

Two consequences before the readings. First, **nobody in the household individuates
transactions**: bank lines arrive by the thousand; the household individuates *payments* (I paid
this toward that), *expenses* (that was the ER copay) and *obligations* — never "the debit of
$4.37 on the 12th" as such. Under the identity pattern, an identity nobody asserts is an identity
the record does not have. Second, **the bank does individuate them** — every line carries the
bank's own transaction id — and the bank is an institution, whose identifiers are correspondence
evidence, not Groundwork identity.

---

## 2. Four readings of "what a transaction refers to"

**T1 — a world event, a Groundwork-minted identity.** Each movement of money is minted like a
payment, by the household's assertion. Fails on the first consequence: the household never makes
that assertion per line, and a process may not make it for them (O9). It would also duplicate
the payment identity for every line that *is* a payment.

**T2 — a proposition: the bank's statement that a movement occurred.** A bank line is what a
*reading* of a bank artefact (a statement, a feed capture) yields: a domain proposition with the
bank's authority, whose content is the amount, date, description, merchant, posted date, running
balance, card, check number — and whose **world referent, the movement itself, is not minted**.
What the line *concerns* in Groundwork — a payment, an obligation, later an expense — is a
`proposition_concerns` claim. Institution-side identifiers are content and correspondence
evidence. "Transaction" names **no identity**.

**T3 — an institution-side record, referenced.** The referent is the bank's ledger entry, and
Groundwork holds a *reference* to it (the bank's id). Close to T2, but it makes the bank's id an
identity Groundwork points at — the account-number error of the institution ruling (*description
never mints or matches*), and it has no answer for a manual entry or a cash movement the bank
never recorded.

**T4 — a transaction is a payment.** Dead by Pm11 / Pm12.

T2 is tested. T3 survives as the description of what a bank id *is* — correspondence evidence
between propositions — inside T2.

---

## 3. The cases

| # | Case | Ruled in | Under T2 |
|---|---|---|---|
| **Tx1** | Feed line `HARBOR MTG 3/3 −1,412.00`; Rob: "that's my March payment." | Pm2, Pa2 | a proposition read from the feed capture (origin the bank; content the line); its payment participant *not established with candidates*; `proposition_concerns(line, p)` asserted by Rob. **Already representable — the payment slice built exactly this** |
| **Tx2** | `TRANSFER TO SAVINGS −2,000.00`. | Pm12 | a proposition read from the capture, concerning nothing minted — legitimately, forever. A movement the household never individuates. **No identity is missing here** |
| **Tx3** | The same bank record arrives in Monday's pull and Tuesday's pull. | E3, captured-portal, `proposition_corresponds` | each pull is a **capture** — a held artefact of an observation of a live system, `as_of` the pull time. The line in each is a proposition read from *that* capture. The bank's transaction id is **correspondence evidence** between them (`proposition_corresponds`, candidate from the id, established… by whom? — the importer's contract, §5). 1.x collapses this at ingest by `import_id`: identity by process — E3's *same arrival* rule stretched over two arrivals |
| **Tx4** | Pending on Monday ($48.20, date 3/12); posted on Thursday ($51.90, posted 3/14). | tie ruling, as_of | two propositions from two captures that **may correspond — candidate from the bank id, established under the importer's contract — with different content** — the bank's statement changed over time. 1.x updates the row in place and loses the pending state; T2 keeps both with their `as_of`. **The parse-dispute shape carrying a real state change** |
| **Tx5** | Rob enters "$40 cash, farmers' market" by hand. | K5 / C1 | **not a bank line at all**: an utterance of Rob's evidencing a proposition of Rob's (his stance about a movement he made), with Rob's authority. 1.x stores it in the same table with `source = 'manual'` — **two provenances under a source enum**, the exact K5 collapse `Evidence.source` shipped |
| **Tx6** | A check: `CHECK #1042 −300.00`. | payment slice | a bank line whose content includes the check number; the payee is *Rob's* claim (`paid_to`) about the payment the line concerns; the number is correspondence evidence tying line to payment (and to the check image, an artefact) |
| **Tx7** | The card statement shows the purchase; the bank statement shows the card payment. | payment slice | two lines from two artefacts about **two different movements** — never one referent; the card payment is a payment toward the card obligation; the purchase is a movement the household may or may not individuate as an expense |
| **Tx8** | The classifier says "this transaction was health" (D1). | slice 6 D1 | D1's subject is the **world event** — the purchase the household was at — which T2 leaves unminted. So the health claim cannot attach to "the transaction": it attaches to an **expense identity** the household mints when it individuates the purchase ("that was my ER copay") — queue item 4 — and the bank line then *concerns* that expense. **The classifier's subject moves from the row to the expense identity; not decided here, deferred to item 4 with the reason** |
| **Tx9** | "Which account is this line from?" | — | the account is the artefact's context — the capture is *of* an account's feed — and the bank account is **not a ruled identity** (`Account` is a 1.x row). Whether accounts need identity is not forced by any transaction case; **fenced** |
| **Tx10** | `running_balance`, `cleared`, `posted_date`. | bank knows movement | bank claims about the bank's own record — content of the line proposition, dated by the capture's `as_of`; `cleared` is the bank's claim, never acknowledgment (K6) |
| **Tx11** | Reversal / chargeback appears as a new line `REVERSAL −(−48.20)`. | queue item 3 | a **new bank line** — a new proposition from a later capture — whose relation to the earlier line and to any payment is exactly queue item 3's question. **Not decided here; T2 does not pre-empt it** — a reversal line is a proposition like any other until item 3 says what it is about |
| **Tx12** | The legacy `transactions` table: 1.x rows whose feed captures were never retained. | captured-portal C3 | *reading retained, referent not*: the rows are **readings without artefacts** — and the substrate's guard says readings exist only of held artefacts, and a process cannot utter. **Legacy rows cannot be decomposed into 2.0 evidence** without either the source captures (gone) or a household assertion (absent — and no Person rows). The same blocker as `DebtAccount`, one layer down |

**T2 survives every case.** What the cases fix:

- **"Transaction" names no 2.0 identity.** A bank line is a **proposition read from a captured
  artefact whose origin is the bank**: the bank's statement that a movement occurred. Its world
  referent — the movement — is not minted (Tx2: legitimately never; Tx8: individuated, when it
  is, as an *expense*, item 4). What it *concerns* in Groundwork is a `proposition_concerns`
  claim (Tx1).
- **Institution-side identifiers are content and correspondence evidence** (Tx3, Tx6) — never
  identity (T3 rejected as identity, kept as evidence).
- **Each feed pull is a capture; propositions read from successive captures *may* correspond.**
  The bank's transaction identifier is **evidence for a correspondence candidate, not
  correspondence itself**; establishment of `proposition_corresponds` belongs to the importer's
  contract. A changed record may therefore be two corresponding propositions with differing
  content and two `as_of`s (Tx4) — but the change does not itself establish the correspondence.
  1.x's in-place update is history loss.

  ```text
  bank transaction id → correspondence evidence → candidate → [importer's authorised assertion] → proposition_corresponds
  ```
- **A manual entry is the household's utterance**, not a bank line (Tx5) — two provenances 1.x
  fused under a source enum.
- **Reversal is a later line whose meaning is item 3's** (Tx11); **the account is fenced** (Tx9);
  **the classifier's subject moves to the expense identity** (Tx8, item 4).

---

## 4. What T2 does not decide — and hands to the queue in order

| Deferred to | What | Why not here |
|---|---|---|
| **Item 3 — reversal** | what a reversal line is about; whether reversal is an event or a claim | T2 supplies only that a reversal line is a proposition from a later capture; the boundary Rob warned about |
| **Item 4 — claim / plan / expense identities** | D1's subject: the purchase the household individuates as an expense; the line concerns it | T2 leaves the movement unminted on purpose; individuation is the household's, when it happens |
| **The importer's contract** (fenced since slice 4) | who establishes `proposition_corresponds` between pulls; whether the bank id is enough for the importer to *assert* on a standing authorisation | policy over candidates; not identity |
| **Accounts** | whether a bank account is an identity | not forced by any transaction case |
| **Legacy decomposition** (Tx12) | none possible | readings without artefacts; no Person rows |

---

## 5. The 1.x row, decomposed afterwards

| `Transaction` column | Under T2 |
|---|---|
| `date`, `amount`, `type`, `description`, `merchant`, `posted_date`, `running_balance`, `mcc`, `card_last4`, `check_number` | **content** of the bank-line proposition; `posted_date` vs `date` = two claims across captures (Tx4) |
| `cleared` | the bank's claim about its own record (Tx10); never acknowledgment |
| `import_id` | the bank's id — correspondence evidence between captures (Tx3); 1.x's identity-by-process |
| `source` (`manual` / `import`) | the K5 collapse: a manual row is a household utterance, an imported row a reading of a capture — two provenances, one enum (Tx5) |
| `account_id` | the capture's context (Tx9) — fenced |
| `category_id` | a **classification claim about the movement** — D1's shape, whose subject becomes the expense identity (Tx8, item 4) |
| `memo` | household content — an utterance's content about the line |
| `created_at` | when 1.x wrote the row: neither the movement's time nor the capture's `as_of` (the payment slice's `created_at` lesson, one layer down) |
| the row's `id` | **the identity of a recording** — 1.x's arrival — not of a movement |

Nothing here is a migration plan (Tx12 forbids one); it is the answer to *what is this row*, in
the only terms the ontology has.

---

## 6. Ruling candidate — for Rob

> **"Transaction" names no 2.0 identity. A bank line is a proposition read from a captured
> artefact whose origin is the bank — the bank's statement that a movement occurred — with the
> line's amount, dates, description, merchant, balance, card and check number as its content and
> the capture's `as_of` as its time. The movement it refers to in the world is not minted:
> nobody in the household individuates movements as such, and a process may not do it for them;
> where the household does individuate one, it does so as a payment, an obligation or — when
> that identity is ruled — an expense, and the line then concerns that identity by a
> `proposition_concerns` claim, candidate from a match, asserted by a party. Institution-side
> identifiers are content and evidence for a correspondence candidate between propositions read
> from successive captures — never identity and never correspondence itself; each feed pull is
> a capture, propositions read from successive captures may correspond, establishment of that
> correspondence belongs to the importer's contract, and a changed record may be two
> corresponding propositions with differing content and two dates without the change
> establishing anything. A movement the household enters by hand is the household's utterance
> evidencing the household's proposition, not a bank line: two provenances, never one enum. A
> reversal line is a proposition from a later capture whose meaning is the reversal question's,
> not this one's. Legacy `transactions` rows are readings whose artefacts were never retained and
> cannot be decomposed into evidence.**

**Build, if ruled: none.** The answer adds no identity, no slot, no kind — a bank line is already
a domain proposition the substrate represents, and its ties are already `proposition_concerns`
and `proposition_corresponds`. The ruling stands as the definition items 3 and 4 are checked
against; the only executable trace worth having is an absence — no `subject_transaction_id`, no
transaction anchor — which the existing fixtures can assert when a later slice touches the
registry. **Outside it under any authorisation:** reversal · the expense identity · accounts · the
importer's contract · any legacy decomposition.

*The line: the bank tells us money moved; the household tells us what moved it. A line in a
statement is the first; "transaction" was never the second.*

---

## 7. Ruling — Rob, 2026-09-14. T2 accepted and ruled, with one correction applied.

**The correction (applied above in §3 summary, Tx4 and §6):** *the same record across pulls is a
`proposition_corresponds`* was too strong and contradicted the closed correspondence doctrine.
A matching bank identifier is **evidence for a correspondence candidate**; it does not establish
correspondence; establishment belongs to the importer's contract. Tx3 had it right; the summary
now says the same. This also keeps T2 from becoming an importer doctrine by accident.

*Otherwise exceptionally clean.* The crucial distinction:

```text
BANK  ── asserts a movement occurred ──► proposition
                                          ├── content: amount · date · merchant · …
                                          ├── evidence: captured artefact + reading
                                          └── concerns → a household-minted identity, if one exists
WORLD ── the movement ──► no Groundwork identity merely because the bank gave it an identifier
```

T1 would manufacture world identities from ingestion; T3 would mistake an institution's
identifier for a Groundwork identity; T4 would collapse transaction and payment. T2 needs none
of those inventions. **Tx2 is not a missing-identity bug** — the ontology may represent a
statement without forcing a household object into existence. **Tx8 correctly fenced** — the
bank-line proposition cannot be the subject of the world-event classification merely because 1.x
called the row a transaction; item 4 decides what the household individuates there. **Tx12 is an
important negative result, preserved almost exactly:** *the available 1.x row does not contain
enough provenance to reconstruct the 2.0 evidence structure* — an ontological boundary, not an
engineering inconvenience; inventing a Person assertion to make the row decomposable would
manufacture provenance after the fact.

**The boundary, as Rob states it:** transaction — no 2.0 identity · bank line — proposition · bank
transaction id — content / evidence for correspondence, never identity · movement — no identity
merely by appearing in a feed · payment / expense / obligation — household identities when
separately individuated · line → household identity — `proposition_concerns`, not identity
substitution · repeated captures — candidate correspondence; establishment remains the importer's
contract · reversal — untouched · legacy rows — insufficient provenance for decomposition ·
**build — none.**

This ruling reopens neither payment, nor proposition correspondence, nor relational knowing, nor
the closed identity doctrine: *the next layer down, not a backdoor redefinition.* The final line
is kept as the memorable explanation.
