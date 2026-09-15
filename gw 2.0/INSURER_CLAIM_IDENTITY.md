# The insurer's claim — does it have a Groundwork identity, and what assertion could mint it?

> Status: **Queue item 4b, opened by Rob 2026-09-14 — a doctrine record, no code.** Expense
> identity is closed at `4051e35` with the boundary that opens this record: *an EOB claim number
> is institution content / correspondence evidence; it does not itself establish an Expense
> identity.* This record asks what, if anything, an insurer claim is as an identity — without
> deciding what the insurer owes, what the plan covers (4c), or the household's responsibility —
> and follows Rob's seven-step pass: what people individuate · who could mint · claim vs claim
> number · claim vs EOB · claim vs adjudication / responsibility · repeated, corrected and
> reprocessed records · then the smallest surviving shape. Nothing here is authorised to build.

**Rob's stopping question, verbatim:** *does an insurer claim have a Groundwork identity, and if
so, what assertion is capable of minting that identity?*

**The key adversarial question, verbatim:** *can the insurer's assertion mint the claim identity?*
— to be **derived from the ontology's identity-authority rules**, not concluded from "the insurer
owns the claim."

**The trap, verbatim:** *don't let "claim" become a universal financial object* — the insurer's
claim, the household's claim about responsibility, and the bank's transaction line are different
propositions / records unless a ruled relation says otherwise.

*A vocabulary note, because the collision is real: throughout the 2.0 records "claim" means
proposition — a claim-shape with kind, subject and content. This record writes **the insurer's
claim** for the insurance sense, and never uses the bare word for it.*

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Identity authority** (party, institution, obligation, payment, expense rulings) | identities are minted by **one of two acts**: Groundwork's encounter of an *artefact* (the thing it holds), or a **Person's individuating assertion** (institutions, obligations, payments, expenses). *Encounter mints nothing* for anything that is not an artefact; description never mints; an institution's identifiers are correspondence evidence, never identity |
| **Expense identity** | the household individuates the incurrence; **other parties assert claims about it but do not mint it**; the EOB concerns X (Ex3); **claim #A77 is content and correspondence evidence — the insurer's identifier for its record of X, never X's identity**; D3's P-world takes X as subject |
| **Transaction referent** | an institution-side record (the bank's ledger entry) is **not** a Groundwork identity: the bank line is a proposition read from a capture; the bank's id is evidence for a correspondence candidate; the movement is unminted; *the record describing the thing is not the thing* |
| **Acknowledgment / P-ack** | *the entitled party's stated position about a payment or balance, as of a stated date* — an institution's **dated stance about an identity**; one knowing party; every stance dated; K8: two positions are two propositions |
| **Cluster B** | P-subject (*the EOB states X*) and P-world (*X is true of the expense*) are two propositions per value; resolving one never establishes the other |
| **`proposition_corresponds`** | two propositions read from two artefacts may be recordings of one claim; an identifier is evidence for a candidate; establishment is a party's |
| **Slice 5** | "P is false" is a domain negative, not a kind; a dispute is derived |
| **Party ruling / roles** | roles are dated relations over parties; *insurer of this expense* is a role, relational knowing's designated relation for adjudication |
| **Reversal / transaction constraint** | source vocabulary decides nothing; *a source's category for a movement does not establish the identity of the thing categorised* |

Two consequences before the pass. First, **the only non-household minting the ontology allows is
of artefacts**, because an artefact is the one thing Groundwork itself holds; every other identity
is minted by a Person's assertion. So the adversarial question has a derivable answer: **the
insurer's assertion can mint a Groundwork identity only if the insurer's claim is an artefact —
which it is not (the EOB is)** — or if a ruled exception is made, which no case has yet earned.
Second, **the transaction ruling already decided the shape of an institution-side record**: a
proposition family with the institution's authority, an identifier that is evidence, and a world
referent the household mints (or never does). The insurer's claim is the same shape unless a case
breaks the parallel.

---

## 2. The pass, step by step

### 2.1 What do people actually individuate as "the claim"?

Listening to how the household speaks:

| Utterance | What it individuates |
|---|---|
| *"the claim for Kim's ER visit"* | **the expense**, seen through the insurer — X, already minted |
| *"Lakeview Health denied the claim"* | **the insurer's stance** on X — an adjudication, dated |
| *"the claim is still pending"* | the insurer's stance (or its absence) as of today — a consumer's reading of stances |
| *"I filed a claim for the out-of-network visit"* | **the household's own act** — an utterance to the insurer (the form is an artefact; the filing is an assertion event, already an identity) |
| *"claim #A77"* | **the insurer's identifier** for its record — content / correspondence evidence |
| *"they reprocessed the claim"* | a **later stance** by the insurer on the same X |
| *"the primary paid, the secondary is reviewing it"* | **two insurers' stances** on one X |

Nobody individuates a thing that is distinct from the expense, the household's filing, the
insurer's stances and the insurer's identifier. The household's "claim" is the expense-as-handled-
by-the-insurer; the insurer's "claim" is its record.

### 2.2 Who could mint it, if anyone?

- **The household** — could a Person's assertion mint an "insurer claim" identity? Only if there
  is a thing to individuate that is not already X, the filing utterance, or the insurer's
  stances. §2.1 finds none. Minting one would duplicate X under the insurer's vocabulary.
- **The insurer** — an institution's assertion mints nothing in this ontology (identity
  authority); its identifiers are correspondence evidence (party ruling; transaction ruling).
  Deriving an exception from "the insurer owns the claim" is exactly the smuggling the record is
  told to refuse.
- **Groundwork on encounter** — mints the EOB (an artefact), never what the EOB is about.

**So no act in the ontology mints an insurer-claim identity**, and no case in §3 needs one.

### 2.3–2.5 Claim vs claim number · vs EOB · vs adjudication and responsibility

| "The claim" as… | Is, in the ontology | Never |
|---|---|---|
| **the claim number** | content of EOB propositions; the insurer's identifier; **evidence for a correspondence candidate** between EOB propositions across documents and captures | an identity, or a slot |
| **the EOB / claim document** | an **artefact** (origin the insurer), read; its lines are P-subject propositions with X as a candidates participant; `artefact_concerns(EOB, X)` when the household ties it | the claim itself |
| **the adjudication** — allowed, plan paid, denied, patient responsibility | **the insurer's dated stances about X** — P-ack-shaped: *the insurer's stated position about X as of d*; read from the EOB as P-subject claims; asserted as P-world claims about X when a party says so | the claim identity; a status field |
| **patient responsibility** | a proposition about X (D3) — the insurer's stance, or the household's | the claim identity |
| **the household's filing** | the household's **utterance** (origin a Person) + the form as an artefact | a claim identity |

### 2.6 Repeated, corrected and reprocessed records

| Case | Under "no identity" |
|---|---|
| **Ic1** — the same claim number appears in the March EOB and in the April portal capture | two artefacts; their lines are propositions that **may correspond**; the claim number is evidence for the candidate; establishment is a party's (or the importer's contract). Nothing is one identity by matching numbers |
| **Ic2** — a corrected EOB reprocesses #A77: patient responsibility $412 → $180 | two dated stances by Lakeview Health about X (`as_of` the EOB dates); history, not overwrite; **the resolver over them is fenced**; the household's `remaining` consumer waits. The same number does not make the two stances one proposition — they may correspond if a party says so, and even then contents differ (the parse-dispute / state-change shape) |
| **Ic3** — the provider resubmits; Lakeview Health assigns a new number #B12 for the same service | two insurer records of one X; two identifiers; both EOBs concern X. Whether they are "one claim" is the insurer's bookkeeping — correspondence evidence at most; **X is the referent that holds them together, and X is already minted** |
| **Ic4** — primary Lakeview Health and secondary Cigna each adjudicate X | two insurers, two sets of dated stances about one X; coordination of benefits is *their* stances; nothing to mint |
| **Ic5** — one hospital-stay claim bundles a dozen line items | the household individuates the stay as one X (or several — Ex7's granularity ruling); the EOB's lines are propositions; per-line ties are `proposition_concerns` |
| **Ic6** — an EOB arrives for a service Kim never had | the EOB is an artefact; its propositions have **no established expense** (candidates none); the household asserts *no such service* — a domain negative about the world, not a retraction (the EOB is not the household's utterance); **the insurer's record exists as the insurer's record; Groundwork mints nothing for it** |
| **Ic7** — denial, then appeal | the insurer's stance *denied as of d*; the household's appeal is an utterance to the insurer plus the household's own value claims about X; the insurer's later stance *allowed on appeal as of d′*. A sequence of dated claims about X by two parties — the "episode" is a consumer's reading of it |
| **Ic8** — "claim status: pending" in the UI | a **consumer derivation** over the insurer's stances (present or absent) — fenced; the substrate holds stances, never a status |

No case forces an identity; every case is representable with X, artefacts, dated stances,
the household's utterances, and candidate correspondence.

---

## 3. What the parallel with the transaction ruling gives — and where it holds

```text
bank      ── records a movement  ──► transaction line   (proposition; id = evidence; movement unminted)
insurer   ── records a service   ──► EOB line           (proposition; claim # = evidence; the service = X, minted by the household)
```

One asymmetry, and it strengthens the result: for the bank the world referent (the movement) is
usually never individuated; for the insurer the world referent (the incurrence) **is** — as the
expense. So the insurer's record has a household-minted referent to concern, which the bank's
often does not. Nothing in that asymmetry calls for a second identity; it means EOB propositions
will more often have an established expense to be tied to.

---

## 4. The smallest surviving shape

Nothing new. The insurer's claim decomposes without remainder into:

| The insurer's claim, as… | Already-ruled primitive |
|---|---|
| a document | **artefact** (origin the insurer) + **readings** |
| a record identifier | **content**; evidence for `proposition_corresponds` / `artefact_corresponds` candidates |
| an adjudication | **the insurer's dated stances about X** — the P-ack shape (*stated position about an identity as of d*), read as P-subject, asserted as P-world |
| a filing | the household's **utterance** + an artefact |
| an episode (pending → paid → denied → appealed) | a **sequence of dated claims** by the insurer and the household about X; the episode is a consumer's derivation |
| "the claim for the ER visit" | **the expense** |

**A finding, not a build:** the P-ack shape (*an institution's dated stance about an identity, as
of d, one knowing party*) now has three instances in the record — E's acknowledgment of a payment,
E's balance on an obligation, and the insurer's adjudication of an expense. That is a **domain
kind family** (the catalogue), not new ontology; its knowing relation is the designated role
(*entitled party of O*, *insurer of X*) that relational knowing left `undetermined` until the
roles are ruled.

---

## 5. Not decided here — fences

- **Plan / coverage** — 4c; *which plan adjudicated X* is a role or a derivation from the date of
  service, per the 1.x row's own note.
- **The resolver over the insurer's successive stances** (Ic2, Ic7) — fenced since Q2.
- **"Claim status"** and every other consumer derivation (Ic8).
- **The importer's contract** — who establishes correspondence between EOB captures.
- **The role kinds** — *insurer of X*, *provider of X*; relational knowing waits on them.
- **The kind catalogue** for adjudication stances (allowed, plan paid, denied, patient
  responsibility, deductible applied…) — the domain's.
- **Legacy** — 1.x has no claim table; `PdfExtractCache.issuer` and the EOB import fuse artefact,
  reading and issuer-as-origin (SHIPPED_VS_TARGET §1); untouched.

---

## 6. Ruling candidate — for Rob

> **The insurer's claim has no Groundwork identity, and no act in the ontology could mint one:
> an institution's assertion mints nothing, its identifiers are correspondence evidence, and
> Groundwork's own minting reaches only the artefacts it holds — the EOB, never what the EOB is
> about. What the household individuates as "the claim" is the expense; what the insurer
> individuates is its record. The EOB and any claim document are artefacts whose readings yield
> P-subject propositions with the expense as a candidates participant, tied to the expense by
> the concerns kinds when a party says so; the claim number is content and evidence for
> correspondence candidates between such propositions, never an identity or a slot; an
> adjudication — allowed, paid, denied, patient responsibility — is the insurer's dated stance
> about the expense, P-ack-shaped, and successive, corrected or reprocessed adjudications are
> successive dated stances, never an overwrite and never made one by a shared number; a
> household's filing is the household's utterance and an artefact; primary and secondary
> insurers are two parties' stances on one expense; an EOB for a service the household denies
> is the insurer's record with no established expense and the household's negative claim; the
> claim's "status" or "episode" is a consumer's reading of stances and is not held. Nothing is
> minted, and nothing is built: the insurer's claim, the household's claim about
> responsibility, and the bank's line remain different propositions and records unless a ruled
> relation says otherwise.**

**Build: none** — no `claims` table, no claim slot, no claim-number column, no status; the
executable trace is the absences the expense fixture already asserts. **Outside it:** 4c ·
the resolver · consumers · the role kinds · the adjudication catalogue.

*The line: the insurer keeps a claim; the household had a visit. Groundwork holds the insurer's
statements about the visit — and the visit is the expense.*
