# Encountering an institution — when Groundwork has grounds to say one exists as a party

> Status: **Design mode, 2026-09-12. No table, no minting path, no code.** Rob's one question:
>
> > **When does Groundwork have grounds to say that an institution exists as a party at all?**
>
> **The constraint, explicit:** an institution's name, identifier, document appearance, issuer
> field, address, account number or other description **cannot itself be assumed to be
> institution identity.** Those may be evidence supporting correspondence to an institution;
> the record must first establish *what event, if any, causes Groundwork to mint the
> institution's party identity.*
>
> **The asymmetry that makes this a different question from `Person`'s:** the household branch
> had a declaration event that legitimately terminates the identity question — *household
> declares Person → Person is authoritative → anchor exists with it.* There is no equivalent
> fact for an institution. So the question does not begin with *what table?* or *when is the
> Party minted?* — those are downstream of the semantic answer.
>
> **Four competing readings**, to be decided by what the cases and rulings already permit:
>
> ```text
> R1  artefact encounter mints it       an artefact identifying an institution → the institution exists
> R2  origin assertion mints it         an asserted origin whose party is an institution → mint
> R3  explicit household assertion      the household identifies an institution as such → mint
> R4  no single encounter mints it      encounters yield evidence / candidates; identity is minted
>                                       only by a distinct identity-creating event
> ```
>
> **The stopping point:** *encounter → semantic state → whether/when identity is minted.* Not
> *encounter → create Institution row → attach Party.*

---

## 0. The danger test, run first

> *Can the same institution appear in multiple artefacts before Groundwork has any legitimate
> basis to know they are the same institution?*

**Yes, and the rulings already say what state that is.** Two EOBs arrive, each with *Lakeview Health* on
the letterhead. Under the artefact ruling each is a minted artefact. Their origin reference is
*established* only if some party has asserted it; the letterhead is the artefact's
**description of its own origin** — a string, on the rejected-bases list. So on arrival each
artefact's origin is, at most, **not established, with candidates** (the party ruling's third
state; RA2's non-monotonicity; the artefact ruling's *never silently turn "the Sept 1
statement" into a held statement because a later artefact matches the description*). Two
artefacts with the same description are two artefacts whose origins are each *not
established* and whose candidate sets happen to coincide. Nothing in the record may say *same
institution* from that.

**So encounter and minting cannot be one event.** If R1 held, the two EOBs would mint two
institutions (or one, by description — the exact error the artefact ruling rejected). Either
way the record would be asserting identity from descriptive sameness. R1 is rejected by the
danger test alone, before any other case is consulted.

---

## 1. What "encountering an institution" is — three things that are usually collapsed

An encounter delivers up to three distinct facts, and the rulings place each differently:

```text
an ARTEFACT is held or asserted          minted on encounter (artefact ruling) — the thing itself
the artefact DESCRIBES an origin         a string / id / letterhead: correspondence evidence, never identity
a PARTY ASSERTS the origin               an assertion with its own origin and strength (contract C3)
```

The first two happen on every import. The third is the one that can establish anything, and
it is the one an import does **not** automatically contain. `PdfExtractCache.issuer` — a
string extracted from the document — is the second fact wearing the third's clothes: the
shipped store records *what the document says its issuer is* as if it were *who issued it.*

**Who can assert an origin?** By the contract, an assertion has an origin, and independence
and establishment are computed over origins. The only party whose identity is not itself a
correspondence question is the household (`Person` — the fixed point, ruled). Every other
party's identity is, by construction, downstream of some assertion. So the first assertion
that establishes an institution **must** have the household as its origin, or it rests on an
institution that does not yet exist. That is not a policy preference; it is what "fixed point"
means when followed one step outward.

---

## 2. The readings, against the cases

Every institutional party in the ruled cases (`PARTY_REFERENCE_QUESTION.md` §0), and how it
came to be known to Groundwork:

| party | how Groundwork came to hold it | who asserted its existence |
|---|---|---|
| the insurer (EOBs; concurrent coverage) | EOBs imported; a plan entered | **the household** entered the plan and knows its insurer; the EOB's letterhead is a description |
| the provider P | bills; the obligation entered | **the household** entered the obligation and knows the provider |
| servicer S, S1, S2 | statements; the coupon | **the household** attached the servicer of record (S1, K2) — asserted, and it can be wrong |
| **S3, never authorised** | a letter | **the household** attached S3 (K3) — a real party, minted by the household's assertion, with a *false relation* to P |
| vendor V (recourse) | a statement arriving late | **the household** imports it and says whose it is — or says *I don't know who this is* |
| agency A | a letter (§8) | **the household** — and §8's *debt validation* is precisely the household not taking the letter's word for who A is |
| the household's bank | the account (`Account.institution`) | **the household** opened the account in Groundwork |
| an unknown sender (RA6, U5/D7) | a letter, unindividuated | **nobody** — *not established*, no placeholder |
| the classifier | — | **no party** — a process |

**Every minted institution in the cases was asserted into the record by the household.** No
case mints an institution from an artefact alone, and no case needs an institution to be
asserted into existence by another institution.

**R1 — artefact encounter mints.** Rejected in §0. Also: it would mint S3 *and* a scam letter
*and* RA6's "the hospital" as parties on arrival — identity from description, promiscuously.

**R2 — an asserted origin whose party is an institution mints.** The origin of the assertion
matters. If the asserting party is **the household**, R2 is R3. If it is **another
institution** — Lakeview Health's EOB naming *Riverbend Hospital Hospital* as the provider, with an NPI — then the
record holds *Lakeview Health states the provider was Riverbend Hospital Hospital (NPI …)*: a proposition asserted by
an established party about a third party's involvement. Strong **correspondence evidence** if
Riverbend Hospital is later asserted by the household; **not a minting event**, because whether *Riverbend Hospital
Hospital* corresponds to an existing party or is new cannot be established from the assertion
(absence of a correspondence is not evidence of distinctness), and minting on it would let
every EOB, every statement, every letter mint providers, pharmacies and labs by the hundred —
description-driven proliferation, the artefact ruling's error at scale. No case requires it;
the cases' providers were all household-entered. **R2 collapses into R3 for its valid part and
into R1's error for the rest.**

**R3 — explicit household assertion mints.** Supported by every row of the table. And it
carries RA6's threshold with it: the assertion must **individuate** — *"my insurer, Lakeview Health"*
mints; *"a letter from the hospital"* does not (R-ASSERT ruling: below individuation there is
no referent, and there is no party either). The household can be wrong (S3) — the assertion
mints a real party; what is false is a *relation*, corrected by conflict, never by unminting.

**R4 — no single encounter mints; a distinct identity-creating event does.** **True, and the
event is R3.** In the absence of a declaration, the only identity-creating act available is an
assertion by the fixed point. R4 and R3 are one reading stated from two ends.

---

## 3. The semantic states an encounter can leave — the actual answer

```text
ENCOUNTER (an artefact arrives; it describes an origin)
   │
   ├── the description individuates nothing         →  origin NOT ESTABLISHED, no candidates
   │                                                    (RA6; U5/D7's default)
   ├── the description matches existing parties      →  origin NOT ESTABLISHED, with candidates
   │                                                    (never auto-matched: description ≠ identity)
   ├── the household asserts correspondence          →  origin ESTABLISHED = an existing party
   │   "this is from Lakeview Health" (picked, not typed)         (a correspondence claim, household origin, with strength)
   └── the household asserts a new institution       →  the institution is MINTED; origin ESTABLISHED = it
       "this is from my insurer, X, not on file"        (the identity-creating event)

machine-originated content                           →  NO PARTY (positive; not an encounter)
```

> **An institution exists as a party when, and only when, the household asserts it as one —
> an individuating assertion whose origin is `Person`, the fixed point. Encountering an
> artefact that describes an institution establishes an artefact and a description; it mints
> nothing and matches nothing. Descriptions, identifiers, issuer fields and other parties'
> statements are correspondence evidence toward an assertion the household may make, and
> candidates it may be offered; they are never the assertion.**

**The danger test, answered by the states:** the same institution *can* appear in many
artefacts before any basis exists to know they are one — and the record holds each origin as
*not established, with candidates*, until the household asserts correspondence. Two arrivals
with identical letterheads and no household assertion are two artefacts with unestablished
origins, indefinitely. That is not a gap; it is the record refusing to know what it does not.

---

## 4. Consequences that follow, and are not decided here

- **The household's assertion is an assertion, with strength.** It is not a declaration. The
  household is sovereign over *its own membership* (`Person`); it is *knowing* about which
  institutions it deals with, which is a different epistemic position — it can be mistaken
  (S3), and the assertion can be contradicted by evidence with another origin (E's own
  statement). So an institution party, unlike a `Person`, sits under a claim, and its anchor is
  the minted identity *plus* the assertion that minted it. **How that assertion is recorded**
  is the next question, and it is where the institution branch differs structurally from the
  `Person` branch: `Person` needed no minting assertion; an institution needs one.
- **Minting is not creation-on-import.** No import pipeline may create an institution party
  from an `issuer` string, a merchant name, a letterhead, or an external identifier. It may
  produce **candidates** and **ask** (C9). `PdfExtractCache.issuer` and `Account.institution`
  are descriptions and remain so.
- **Institution minting has no lifecycle symmetry with `Person` and must not borrow it.**
  A `Person` and its anchor share one lifecycle boundary because the declaration is the
  identity. An institution's party identity is minted by an assertion and, once minted, is a
  referent that artefacts, roles and correspondences may point at; whether it can ever be
  *unminted* (as opposed to its relations retracted) is not answered here and should not be
  assumed from `_sync_delete_person`.
- **Other institutions' statements about institutions** are propositions with an established
  origin and are strong correspondence evidence — an NPI on an EOB is better evidence than a
  name — but they establish *involvement*, never *existence as a party*.

---

## 5. What this record does not decide

How the minting assertion is recorded (a relation? a column on the institution anchor? with
what strength scale?); the institution anchor's shape beyond *a minted identity under an
assertion*; the candidate relation for *not established*; what the household is *offered* as
candidates and how (surface, C9); whether an institution can be unminted; anything about
correspondence storage; any table.

---

## 6. Ruling candidate — for Rob

> **Encountering an institution mints nothing. An artefact that describes an institution is
> an artefact whose origin is not established — with candidates when the description matches
> parties on file, without when it does not. An institution comes to exist as a party by one
> event only: the household's individuating assertion that it is one, whose origin is
> `Person`. That assertion either establishes correspondence to an existing party or mints a
> new one. Other parties' statements, identifiers and descriptions are correspondence
> evidence and candidate sources, never minting events. The household's assertion is a claim
> with strength, not a declaration: an institution party sits under the assertion that minted
> it, which is the structural difference from the `Person` branch and the subject of the next
> question.**

If ruled, the next question is **how the minting assertion is recorded** — the institution
branch's analogue of "anchor timing", and the first place its shape diverges from `Person`'s.
