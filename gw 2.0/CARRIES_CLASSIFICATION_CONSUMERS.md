# §7.7 *carries* as classification — the consumers, before any dimension

> Status: **Consumer inventory, 2026-09-12. No decision. No dimension proposed.**
> The question, as Rob opened it after the doctrine test (`CARRIES_DOCTRINE_TEST.md` §6):
>
> > **What property of a financial obligation is §7.7's "carries" classification actually
> > intended to describe, and what downstream behaviour is supposed to change when that
> > property changes?**
>
> **The constraint, his:** do not start from candidate dimensions. Start with the consumer. If
> nothing downstream behaves differently when the classification changes, the distinction may be
> semantically interesting and architecturally unnecessary; if something does, *that consumer
> says what the classification must preserve.*
>
> **Forbidden:** borrowing the disposition doctrine's answer. The disposition object is the
> household obligation across entitlement; nothing here may assume classification reads the
> same thing.
>
> **The rule under inventory** (`HEALTHCARE_MODULE_DESIGN.md` §7.7, never-list 17):
>
> > *An obligation is a healthcare cost when the provider carries it at no interest. It is a
> > credit card when a lender carries it, whatever the marketing calls it, and however medical
> > the purchase was.*
>
> **Method.** Every place the design makes something behave differently on *healthcare cost
> vs credit card* — or on a neighbouring distinction that a reader might take for the same one.
> For each: what behaves differently · **what property it actually reads** to do so · and
> whether it would behave differently on the recourse outbound leg (provider → vendor, same
> obligation, same amount, same 0% terms), since that is the case that made the question.
> Nothing is built; the consumers are the design's, and the design is what has to be honest.

---

## 1. The consumers

| # | Consumer | What behaves differently | What it actually reads | Changes on recourse outbound? |
|---|---|---|---|---|
| C1 | **§0.2 — the noun.** Never-14. | *Healthcare Cost* vs *debt*, everywhere, in every export | Whether §0.2's protection applies — and §7.7 says it does **not** apply to a lender's balance, so C1 is not reading *care* (the purchase is medical either way). §7.7's own gloss: *"§0.2 protects care from being called a failure, not lenders from being called lenders."* So C1 reads **whether the instrument is the adversary.** | **Only if the label flips.** The household holds the same 0% term plan for the same care. Nothing C1 protects against — a verdict on the person — has changed. |
| C2 | **Placement.** Never-14, §7.7 ¶*"its own section"*. | Its own heading in the payoff view vs a line among the cards | Same as C1 — placement *is* the noun by layout. | Same as C1. |
| C3 | **Lever protection.** §7.7 ¶*"flagged protected"*. | Never trimmed, never headroom, never a reallocation source | Whether the obligation is **necessary care** — the necessity floor's reason, not the carrier's. §0's rationale is that care is not a lever. | **No.** The care is the same care. A vendor's name on the statement does not make medication a reallocation source. |
| C4 | **Payoff engine — pricing and ranking.** §7.7 ¶*"the engine sees it"*. | Exact end date (balance ÷ payment); ranked last | **Interest rate and term.** The design says so directly: *"the engine's own ranking puts a 0% obligation last without being told to."* The engine never reads the label. | **No.** Same rate, same term, same date. |
| C5 | **The cliff.** Never-16, §7.4 urgent tier, the third obligation type. | Promotional end date + retroactive principal shown; serene payoff date forbidden; urgent-tier bypass | **Instrument mechanics**: deferred interest accruing from purchase, retroactive on the original amount, a date. The three obligation types the engine needs — *card · provider plan at 0% with a term · promotional balance with a cliff and retroactive principal* — are three **term structures**, not three parties. | **Only if the vendor's product has a cliff** — which is a fact about its terms, known or not, and not a fact about the vendor. A recourse-funded 0% plan with no promotional period has no cliff to show. |
| C6 | **Card-free date.** Open Question 7. | Healthcare cost excluded from the headline figure | Whether the obligation is part of *the fight against the cards* — C1's property again, read by a number instead of a noun. | Same as C1. |
| C7 | **Never-10.** | A credit card is never offered as a neutral way to pay for care | Whether an *instrument* is a card — this is about a **prospective** payment method, not an existing obligation's classification. | Not applicable — it governs offers, not holdings. |
| C8 | **§8 — collections.** §8.1, §8.2a, never-11, never-20. | Premise attached to every figure; no payment figure ever offered; §501(r) asserted only where the provider type carries it; FDCPA rights surfaced; original creditor and amount kept beside the agency's | **Who is entitled to collect, and what duties that party owes the household.** A hospital owes §501(r); an agency that bought the account owes only the FDCPA; and the premise exists because *ownership of the debt is what the household cannot verify.* | **Possibly, and it is a legal question.** Whether §501(r) financial-assistance duties still attach to an account a hospital has sold with recourse is not something the design answers, and never-11 says the app must not assert protections it cannot condition. The consumer that reads entitlement reads it for **duties**, and says nothing about *healthcare cost vs credit card*. |

---

## 2. What the inventory shows

**No consumer of §7.7's classification reads the party.** C1, C2 and C6 read *is this instrument
the adversary*; C3 reads *is this necessary care*; C4 and C5 read *the terms* — rate, term, and
whether there is a cliff. The provider/lender distinction in §7.7's wording is a **proxy**: where
the rule was written, provider plans were 0% term instruments and lender products were cards or
deferred-interest balances, so *who* stood in for *what terms*. That is the same finding
`OBLIGATION_LIFECYCLE_QUESTION.md` §10 reached about *carries* as one fact — *the rule was
written where they happen to coincide* — arriving now for classification rather than lifecycle.

**Run the recourse outbound leg through every consumer and nothing needs to change** except
where the label itself would flip — and the label flipping is the thing under question, not a
consumer of it. The household has the same care, the same obligation, the same amount, the
same rate, the same end date, and no cliff unless the vendor's terms have one. Under §7.7 as
worded, C1, C2 and C6 would rename it *credit card* on the outbound leg and *healthcare cost*
on the return, and **no consumer's reason for its behaviour would have changed either time.**

So Rob's test comes out on the second branch, sharply: *something* does behave differently on
the classification — five consumers — and what they need preserved is **not entitlement.** The
category error he named is real: §7.7's rule was carrying two objects, and the doctrine test
found the one disposition needs while the consumers here need the other.

**Entitlement is read downstream — by C8, not by §7.7.** §8's whole apparatus exists because
the party changed: the premise, the duties, the validation right, the original-creditor pair.
That is a genuine consumer of *who is entitled to collect*, and it is a separate rule with a
separate trigger (*in collections*), not a case of §7.7. The two objects the doctrine test
suspected are both real and both consumed, by different rules:

```text
disposition          reads   the obligation across entitlement       (doctrine test, frozen)
§8 collections       reads   entitlement — for the duties owed       (C8)
§7.7 classification  reads   instrument terms and care-necessity     (C1–C6)
```

**One thing the inventory does not settle, and it is the reason the proxy might be deliberate.**
A household usually knows *who sends the bill* long before it knows *the terms*. If §7.7's party
test is meant as a **fail-closed default where terms are not held** — a lender's balance is the
adversary until its terms prove otherwise — then the proxy is doing honest work, and the rule
should say that is what it is doing rather than say *carries*. The inventory cannot tell a proxy
kept on purpose from one kept by accident; the design text gives no sign either way.

---

## 3. What this does not prove

1. **Which property §7.7 should name.** The consumers read three things — adversary-instrument,
   necessary-care, terms — and the inventory reports that; it does not choose among them or
   propose that one subsumes the others. C3 in particular reads something none of the others do.
2. **That the party is never a legitimate input.** §2's last paragraph: as a default under
   unknown terms it may be exactly right. That is a decision about what the rule *is*, not a
   finding about what its consumers read.
3. **Anything about C8's legal question.** Whether §501(r) follows a recourse-sold account is
   for the design's *state the policy, condition it on provider type, stop* rule, not for this
   inventory.
4. **That classification and disposition never meet.** C8 shows entitlement *is* consumed, and
   a collections transfer is both an entitlement transition (disposition's object) and §8's
   trigger. They meet there; they are still two rules reading one event for two reasons.

---

## 4. Decision remaining — Rob's

Whether §7.7's classification rule is restated in terms of what C1–C6 actually read, keeping
the provider/lender test — if at all — as a stated default for unheld terms rather than as the
definition; or whether the party test is what §7.7 intends and the recourse relabelling is
accepted behaviour. The inventory's contribution is that the second option now has to be chosen
knowing that no consumer asked for it.
