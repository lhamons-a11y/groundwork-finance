# Party reference — what a party is, for provenance

> Status: **Design mode, 2026-09-12. No table, no schema, no migration, no UUID discussion, no
> correspondence storage.** The sole job: determine what a party reference *means* and what
> must be true for two references to denote the same party. Rob's question:
>
> > **What identity primitive represents a party in provenance, such that the same party can be
> > recognised across artefacts and mediation chains, different parties can remain distinct,
> > and absence of an established party does not assert difference?**
>
> Three tests the record must answer: **(1)** what entities can be parties — against the
> parties that actually appear in the ruled cases, not against the tables; **(2)** what makes
> two references the same party — knowing that `"Lakeview Health"` ≠ identity, `"AETNA INC"` ≠ identity,
> role ≠ identity, absence ≠ difference, description ≠ identity; **(3)** what *absent* means —
> made executable as doctrine, not left as a nullable foreign key.
>
> **Carried from the artefact ruling, verbatim in spirit:** *do not confuse the evidence by
> which Groundwork establishes party correspondence with the identity of the party itself.*
> Every derived artefact identity failed; party identity gets the same treatment rather than
> being assumed obvious because `Person` exists.

---

## 0. The parties the ruled cases contain

Collected from the cases, not from `core/database.py`. Each row is a party a ruling had to
name to say a true sentence.

| party | appears in | what the record must be able to say about it |
|---|---|---|
| **a household member** — the user; two members (RA5); named people (§1.7) | health tie (knowing origin); RA5; person assignment | *is a knowing origin for "it was health"*; *is the same person across two utterances*; *is not the same as the other member* |
| **the insurer** — one; **two** under concurrent coverage (CC1); the same insurer printing twice (DI) | health tie; D1/D2; CC1/CC3 | *is a knowing origin for the health proposition*; *two EOBs from it are one origin*; *two insurers are two origins* |
| **the provider / entitled party P** | write-off; recourse; S1–S7; K1 | *is E of obligation X at date d*; *stops being E on the outbound leg and is again on return* — the **same party**, the role moving |
| **a servicer** — S, S1, S2; **S3 never authorised** | S1–S3; K2–K3 | *serves P* (asserted by the household); *stopped serving P on Sept 1*; *S3 claims to serve P and does not* — a false relation on a real party |
| **a financing vendor V** | recourse | *was E from March to the return*; *funded and serviced* |
| **a collection agency A** | S4/S5; §8 | *acts for P* (assignment) **or** *is E* (sale) — indistinguishable to the household, different duties |
| **the household's bank** | K6 | *knows the money left*; *is not knowing for what E acknowledges* |
| **Groundwork's own classifier / a parser** | the manufactured flag; `MERCHANT_MATCH`, `MCC`, `INFERRED` | *originated a suspicion nobody asserted* — an originator that is **not a knowing party** |
| **an unknown sender** | RA6 ("a letter from the hospital"); S3 before discovery; a second letter (U5/D7) | *no established party* — and the record must not manufacture one |

Two things this table settles before any candidate is scored:

- **Roles are relations over parties, not parties.** *Entitled party*, *servicer of record*,
  *primary insurer* are all *X stands in relation R to obligation/plan Y at date d*. P is E,
  stops being E, is E again — one party. So the party primitive must support **asserted,
  dated relations between parties and between a party and an obligation**, and those
  relations are exactly C3's mediation links.
- **Not every originator is a knowing party.** The classifier originates the manufactured
  flag. That origin is *established* — Groundwork knows precisely where it came from — and it
  is *no party at all*. This is a state test 3 has to hold distinct from *not established*.

---

## 1. Test 1 — what entities can be parties, without a role-specific identity mechanism

The parties above fall into **two kinds by who is knowing for their identity**, and that turns
out to be the fact that decides the candidate:

- **Household members.** The household is the *authority on its own membership* — F.6a's
  declaration is sovereign; §1.7 makes a person a label the household assigns. `Person`
  exists and is authoritative *because the household asserts it*, not because a table exists.
- **Everyone else** — insurers, providers, servicers, vendors, agencies, banks — is known to
  Groundwork **only through artefacts and assertions**: a letterhead, an `issuer` string, a
  payment coupon, the household saying *"that's my insurer."* Nobody inside Groundwork is
  knowing for Lakeview Health's identity the way the household is knowing for its own.

So test 1's answer: **yes, every party in the cases can be represented without role-specific
identity — but not with one mechanism.** Household members have a pre-existing sovereign
identity; institutions have none and must be given one on the same terms as artefacts.

---

## 2. Test 2 — what makes two references the same party; candidates against the cases

| candidate | same when | different when | cases it fails | verdict |
|---|---|---|---|---|
| **P1 — existing domain identity only** (`Person`; `DebtAccount`; `HealthPlan`) | same row | different row | `DebtAccount` is an *account*, not a creditor — two cards from one bank are two rows, one party (the T-B analogue); `HealthPlan` is a *plan*, not the insurer — CC1's two plans may be one insurer or two; institutions with no account (a servicer, an agency, a bank as K6's origin) have **no identity at all** | fails for every institutional party; right for household members |
| **P2 — role-qualified reference** (*the insurer of plan Y*, *E of obligation X at d*) | same role instance | different | roles are relational: P is *E of X*, *E of Y*, and *not E of X during the recourse leg* — one party, three role instances; two insurers under CC1 are *the insurer of A* and *the insurer of B* — two roles that may be one party. Cannot say *same party* across roles | rejected — the O3 result, again |
| **P3 — normalised external identity** (NPI for providers, payer id for insurers, EIN) | external id matches | differs | absent for agencies, servicers, most letters, all captures; an insurer has several payer ids; a provider group has many NPIs — the A2 result: strong **evidence** where present, never sufficient | rejected as identity; kept as correspondence evidence |
| **P4 — minted party identity**, correspondence asserted | linked by established correspondence | no correspondence asserted | none of the institutional cases; **but** for household members it would mint a second identity beside `Person` — two identities for the one party kind the household is sovereign over, with a correspondence claim between them that no one is knowing for except the household, who already asserted `Person` | right for institutions; **wrong for household members** — it would make the household's own declaration a correspondence claim about a minted stranger |
| **P5 — a union over existing identities** (`Person` ∣ `DebtAccount` ∣ issuer string ∣ …) | same member of the union | different | for institutions the union member is a string or an account — P1's failures inside a wrapper | rejected — a discriminated union over identities that are not identities |
| **P6 — the hybrid the knowing relation forces:** `Person` for household members (existing, sovereign, no minting); **minted identity for every other party**, with correspondence as asserted claims (name match weak · external id strong · issuer id on artefacts · the household saying *"same company"*) | household: same `Person`; institution: established correspondence | household: different `Person`; institution: no correspondence | **none of the cases in §0.** Two EOBs from one insurer: one minted party, two artefacts (DI ✓). Two insurers: two minted parties (CC1 ✓). `"Lakeview Health"` / `"AETNA INC"`: two arrivals, correspondence *asserted or not* — never equal by spelling ✓. S3: a real minted party with a **false asserted relation** to P (K3 ✓ — the relation is what is wrong, not the identity). P through recourse: one party, the E-relation dated (✓). The bank: a party, not knowing for P-ack (K6 ✓). | passes; and the split is **not** a convenience — it is where the knowing relation puts it |

**The regress, and where it stops.** Rob's worry: if party identity is minted, what
establishes correspondence between party references — the same question one level up? It is
the same *shape* and it **terminates**. A party-correspondence claim is evidence with an
origin; its origin is whoever asserted it — an external identifier on an artefact (origin: the
artefact's issuer), or the household (*"yes, same company"*). The household's assertions
ground in `Person`, which is not minted but declared. So the chain is:

```text
minted institution ──corresponds-to──► minted institution      (a claim)
                              └── origin of the claim: an artefact, or a household member (Person)
```

There is no party-of-the-party. The regress ends in the one party kind whose identity is not a
correspondence question because the household is sovereign over it. **That is why P6 is a
finding and not a compromise: the household is the fixed point.**

---

## 3. Test 3 — what *absent* means, as doctrine

The §0 table produced **four** states, not three, and they must not collapse:

```text
ESTABLISHED = A         the reference denotes party A
ESTABLISHED = B         … party B; A and B distinct
NOT ESTABLISHED         no party has been established for this provenance
                          — a letter from an unknown sender; S3 before discovery; "the hospital"
                            when two are known (RA2's shape at the party level)
NO PARTY                established: the origin is a process, not a party — the classifier's
                          manufactured flag; a merchant-match rule; a parser's inference
```

**Doctrine each state carries:**

1. **NOT ESTABLISHED does not assert difference.** Two artefacts each with no established party
   are not thereby from different parties, and neither is from a party different from A.
   Independence against them is *not established* (contract C4), never *yes*.
2. **NOT ESTABLISHED must not mint a placeholder.** No `unknown-party-X`. A placeholder is a
   minted identity with no correspondence evidence and a name that lies — it would later
   attract correspondence claims to a thing that never existed. The reference is *absent*, and
   absent is a value the record holds, not a row.
3. **NOT ESTABLISHED may carry candidates.** *"The hospital"* with two hospitals known is not
   established *and* has a candidate set — RA2's non-monotonicity at the party level. The
   record holds the candidates as candidates; position does not pick.
4. **NO PARTY is established, not absent.** The manufactured flag's origin is known exactly.
   It is not a knowing party, so it contributes nothing to independence (contract C1), and it
   is not *unknown* — treating machine origin as *not established* would let a manufactured
   suspicion masquerade as evidence whose source merely hasn't been identified yet. That is the
   voice ruling's *manufactured provenance cannot satisfy the authorisation requirement*,
   arriving as a provenance state.
5. **Absent is never resolved by the channel.** `IMPORTED_EOB` does not imply *established =
   the insurer*; the artefact's origin party is established by its own evidence (letterhead,
   payer id, the household's word) or it is not established. This is C2 restated for parties.

---

## 4. What the party primitive must support beyond identity — found, not designed

The §0 table requires two things of parties that are not identity and are not decided here:

- **Asserted, dated relations** between parties (*S serves P*; *A acts for P*) and between a
  party and an obligation or plan (*P is E of X at d*; *Lakeview Health is the insurer of plan A*).
  These are C3's mediation links and the frozen disposition doctrine's entitlement history,
  stated over parties. **A role is such a relation; it is never a party.**
- **Correspondence claims between party references**, with strength, on the artefact ruling's
  terms — and with the household's assertion as one kind of evidence among several, not the
  only one.

Both are relationships; both are outside the identity primitive; both are what the identity
primitive exists to make statable.

---

## 5. What this record does not decide

Whether `Person` is extended, wrapped, or referenced; whether minted institutions are a table,
rows in an existing one, or values; how a correspondence claim between parties is stored or
scaled; whether external identifiers are stored on the party or on the correspondence; whether
`DebtAccount.name`, `PdfExtractCache.issuer` or `HealthPlan.name` become correspondence evidence
for anything; any migration. And — flagged, not opened — whether Groundwork itself is a party
for purposes other than *NO PARTY* (it is the originator of every derived fact; the sensitivity
ruling treats that as *nobody asserted*, which is the answer this record uses).

---

## 6. Ruling candidate — for Rob

> **A party reference denotes either a household member — whose identity is the household's
> own declaration (`Person`), sovereign and not minted — or an institution, whose identity
> Groundwork mints when the party is encountered and for which every "this is the same party"
> is an asserted correspondence with a strength, never a computation from a name, an external
> identifier, an account, or a role. Roles are dated relations over parties, never parties. A
> party reference has four states — established as A, established as B, not established, and
> no party (a process originated it) — and not established asserts neither difference nor a
> placeholder, may carry candidates, and is never resolved by the capture channel.**

The household is the fixed point: the one party kind whose identity is not a correspondence
question, and the point at which the correspondence regress terminates.

If ruled, the next question is the first implementation question in the whole chain, and it
is small: **whether minted institutions live beside `Person` or as a second kind under one
reference.** That is a table question, and it is not this one.

---

## 7. Ruling — Rob, 2026-09-12. §6 ruled.

*The case work showed the hybrid is not a compromise between two mechanisms; the cases force
it because the knowing relation is different.*

**The strongest part is the fixed-point argument.** It closes a recursion that would otherwise
quietly infect the model — *who establishes that this institution is party A? → another party
→ who establishes that? → …* — because `Person` is not merely another evidence-derived
identity; it is the domain's authoritative declaration of household membership. Materially
different from an institution identified by an artefact.

**Preserved aggressively — future implementation must not collapse these:**

```text
Person identity        →  the household's declaration
Institution identity   →  Groundwork-minted identity  →  correspondence evidence
```

Not "two ways to create IDs" — **two different epistemic foundations for identity.** And:

```text
NOT ESTABLISHED   is not   UNKNOWN PARTY   and certainly not   PARTY_ID = NULL
```

The four-state distinction matters because **NO PARTY has positive semantic meaning**: the
process originated the thing and there is no party assertion behind it. It prevents the
manufactured classifier from acquiring a fake provenance merely because its output is attached
to an artefact.

**The role ruling — a rule reviewers may reject future designs against:**

> **Roles are dated relations over parties, never parties.**

```text
P ──[E, t1..t2]──► X
P ──[not E, t2..t3]──► X
P ──[E, t3..]──────► X          still P; the relation changed, the party did not
```

Exactly the distinction the capture/source machinery could not express.

### The primitive layer

```text
ARTEFACT
  minted identity
      ├── owns    → READING
      └── carries → ORIGIN PARTY (when established)

PARTY
  household member → Person / household declaration
  institution      → minted identity
  correspondence   → evidence, never identity

RELATIONS
  role             → dated relation over parties
  correspondence   → asserted relation with strength
  lineage          → derived over established relations
  independence     → derived over established provenance

PARTY STATE
  established A · established B · not established · no party
```

> **Identity is primitive; relationships explain what we know about identities.**

### The next question — implementation-shaped, and allowed to touch schema

The semantic requirement now earned:

> **There must be a single usable party reference capable of referring to either a household
> `Person` or a minted institution.**

Not decided: one polymorphic/reference table · separate tables with an abstraction above ·
a party table alongside `Person` · something else. The ontology has earned the right to ask.

**The constraint carried into that discussion:**

> **The implementation must not make the semantic distinction between household-declared and
> institution-minted identity disappear merely because they share a reference type.** "One
> reference" does not necessarily mean "one ontology."

That is the next place to look for a hidden architectural trap.
