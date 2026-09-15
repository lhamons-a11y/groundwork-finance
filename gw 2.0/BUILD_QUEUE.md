# The build queue after the substrate run — Rob's ordering, 2026-09-14

> Every slice opened in the run that began at `SMALLEST_SCHEMA.md` §12 is closed: the evidence
> substrate · artefact + reading · origin + institution anchor · correspondence ·
> `utterance_retraction` · domain proposition (ruled, no code) · obligation identity ·
> `artefact_concerns` · payment identity · `proposition_concerns` · `proposition_corresponds`.
> Each fenced what it does not establish. 941 green at `50a7d70`. *You aren't accumulating
> features; you're accumulating stable semantic primitives — and the queue is about how they
> interact, not holes in the foundations.*

**Not to be jumped into as implementation.** The queue has several items downstream of a smaller
number of semantic decisions; choosing the next slice well matters. The order:

| # | Question | Why here | Treat as |
|---|---|---|---|
| ~~**1**~~ | **Relational knowing — RULED (R2), mechanism built, closed** | nine kinds already carry `relational_knowing = True` and derive `undetermined`; the obvious architectural dependency — and unusually dangerous: a sloppy definition retroactively changes the meaning of nine closed slices | **a doctrine slice**, not "add knowing fields": *what does it mean for a party to know a proposition, and what exactly does that relation establish?* Establish the ontology first; then project it onto the waiting kinds |
| ~~**2**~~ | **Transaction referent — RULED (T2), no build, closed** | contained; *transaction row ≠ payment event* and *a transaction can exist without a payment* are ruled; what remains is what a transaction refers to, and whether that is an identity at all or a relationship to an institution-side record | before reversal, which will touch the transaction/payment boundary |
| ~~**3**~~ | **Reversal — RULED (C: a claim, never an identity), no build, closed; the payment-to-payment relation forced-but-unruled → item 6's family** | deceptively large: not "how do we model a reversed payment" but *is reversal an event identity, or is "payment X was reversed" a claim about an event?* | keep the alternatives completely separate until a ruling makes one legitimate; **do not let bank terminology decide the ontology**; the six hard constraints are recorded at `TRANSACTION_REFERENT.md` §8 |
| ~~**4**~~ | **Claim and plan identities — CLOSED**: 4a expense RULED (X3), built, accepted; 4b the insurer's claim RULED (no identity, nothing can mint one), no code; 4c the plan RULED (PL2), built, accepted (`dcac27e`) | another identity cluster | wait until relational knowing is settled if their assertions participate in it |
| ~~**5**~~ | **Role period — CLOSED**: RULED RP2, built (`1321170`: registry `began` / `ended` boundary metadata + structural guard, no schema, no role kind), accepted | important; a temporal-ontology question | its own narrow treatment — not introduced as infrastructure for something else; *do not let the existence of `Plan` pre-answer "covered under"* |
| **6** | **Relation semantics** (was "restructure relation") — OPENED as `RELATION_SEMANTICS.md`: passes A payment↔payment · B obligation↔obligation · C obligation↔expense · D payment↔expense (D′ payment↔obligation) · E plan↔… · F covered-under · G family decision; **pass A RULED and built (`payment_counteracts`, registry only); pass B OPENED 2026-09-15 — candidate `obligation_replaces` (§B.6), four of the five phenomena found to be one-participant claims, no code, awaiting Rob** | after the relevant identities are stable | one relation at a time; twelve prohibitions; no family-level resolver until the relations prove they share semantics |
| **7** | **Consumer derivations** — parse dispute · independence · about-ness via correspondence · level consistency · multi-link strength · discharge → `remaining` · disposition | **last, and protected most aggressively** | the substrate can now represent ambiguity without resolving it; consumer work becomes valuable exactly then — but only after the ontology stops moving underneath it |

```text
identity → claims / propositions → evidence → correspondence / about-ness / knowing → rules → consumer derivations
```

**Things that must not collapse into knowing** (carried into slice 1 of this queue): reading /
observation · assertion / utterance · evidence · proposition correspondence · about-ness ·
strength · truth · participant establishment.

Still fenced and not in the order above until a case forces one: `utterance_corresponds` ·
candidate generation · the importer contract / standing authorisation · unminting · Person ↔
Person correspondence · the manufactured / process-origin artefact (O9) · the kind catalogues.
