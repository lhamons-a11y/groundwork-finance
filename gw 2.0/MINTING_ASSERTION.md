# The minting assertion — where it lives, and its relationship to the minted institution

> Status: **Design mode, 2026-09-12. No table, no code.** Rob's question, narrowed:
>
> > **Once the household assertion mints an institution, where does that assertion live, and
> > what exactly is the relationship between the assertion and the minted institution?**
>
> **Not decided here, by fence:** whether the assertion is mutable · whether it can be
> superseded · whether the institution can be unminted · whether correspondence can
> independently strengthen it · the eventual database shape.
>
> **Ruled upstream and used:** an institution exists as a party by one event only — the
> household's individuating assertion, a claim with strength, origin `Person`
> (`INSTITUTION_ENCOUNTER.md` §7). A party reference is a referential mechanism, not evidence
> (`PARTY_REFERENCE_SHAPE.md`). The `parties` row is structural and carries nothing
> evidentiary — asserted as an absence by the built fixture. The ontology's evidence unit is
> *a reading's claim on a proposition; or an utterance* (`REPRESENTATION_CANDIDATE_MATRIX.md`
> §0).

---

## 1. Where the assertion lives — the ontology already answers

The household's assertion *"my insurer is Lakeview Health, at this address, plan number …"* is, in the
ruled ontology, exactly one thing: **an utterance** — evidence with no artefact behind it
(D8: utterances need no referent), origin `Person`, a strength, and a proposition it supports.
It is not a new kind of thing. It is the evidence family's own unit, made by the fixed point.

So the assertion lives **in the evidence family**, as an utterance, beside every other claim
the household makes — *"it was health"*, *"S serves P"*, *"that's the same statement"*. Three
candidate homes were considered and two fail:

| candidate home | verdict |
|---|---|
| **columns on the `parties` row** (`asserted_by`, `asserted_at`, strength) | **rejected** — the party row is structural, not evidence; the built fixture asserts it carries no evidentiary column, and that was the right assertion. A reference-layer identity must not carry the claim that made it, or every FK to it silently transports evidence. |
| **columns on the institution anchor** (`institutions(party_id, asserted_by, …, name, address)`) | **rejected as the *home*** — it would make the anchor a second place where claims are stored, outside the family that owns claims, with its own strength and no resolver: two sources of truth for what the household asserted. The anchor may *reference* the assertion; it must not *be* it. |
| **an utterance in the evidence family**, referenced by the anchor | **the only home consistent with the rulings** — one family owns every claim; the assertion has origin, strength and supersession semantics *because it is evidence*, not because the institution table grew them. |

**And the descriptors go with the assertion, not the identity.** *Lakeview Health* · the address · the
plan number are the *content of the utterance* — what the household said about the party — and
they are correspondence evidence for later arrivals (a letterhead matching the asserted name
is a candidate; an issuer id matching the asserted plan number is strong). They are not
columns of identity on the party. The party is the minted identity; what it is *called* is
what someone asserted about it.

---

## 2. The relationship — the assertion is the institution's provenance, and it is asymmetric

```text
utterance U            origin: Person p · strength · content: "an institution, described as …"
   │ supports
   ▼
proposition            "a party exists, which p deals with as [role], described as …"
   │ whose subject is
   ▼
party X (minted)       the referent U's act created; X's anchor records: minted-by U
```

Three statements, each traceable, and together they are the relationship:

1. **U is X's provenance.** X exists because U was made. The institution anchor records *which
   utterance minted it* — a reference to evidence, in the anchor, pointing *outward* to the
   family. That reference is the one place an anchor carries anything evidentiary, and it
   carries a *pointer to* evidence, not evidence.
2. **X is U's subject.** U's proposition is about X — the party U brought into existence. This
   is the one case in the ontology where a claim's subject is created by the claim; it is not
   circular, because the *identity* (X, minted) and the *claim* (U, that a party with these
   descriptors exists and is dealt with) are different things, and X can outlive U's content
   being wrong (S3: the party is real; the descriptors and the relation were false).
3. **References to X are not evidence; X's existence is.** An FK to X says *points to X* — the
   shape ruling. But *why X exists* is U, a claim with strength. So the institution branch has a
   property the `Person` branch lacks by construction: **its anchor has provenance.** A
   `Person`'s anchor has none because the declaration *is* the identity; an institution's anchor
   has one because an assertion is not a declaration.

That third statement is the structural difference the encounter ruling predicted, made
precise: `Person` → anchor is structure; institution → anchor is structure **plus a pointer to
the claim that minted it.**

---

## 3. What this forces about build order — a finding, not a decision

The Party slice is built. The evidence family — artefact · reading · evidence/utterance — is
ruled and **not built.** §1 says the minting assertion *is* an utterance in that family, and
§2 says the institution anchor *references* it.

So **the institution slice cannot be built before the evidence family's utterance primitive
exists** — not without inlining an utterance into the anchor, which §1 rejected as a second
home for claims. The alternative ("build the institution table now with `asserted_by` columns
and migrate to the family later") is exactly the two-sources-of-truth shape the architecture
principles were written against, and it would ship the household's most consequential
assertions in a table with no resolver, no strength semantics and no supersession, to be
reconciled later against a family that would then already disagree with it.

**Build order, forced by the ontology:**

```text
1  evidence family: artefact · reading · utterance   (ruled; not built)
2  the institution anchor, referencing its minting utterance
3  correspondence — between artefacts, and between parties — as claims in the family
```

Not a plan; a dependency. The party branch's next slice is not the institution; it is the
utterance.

---

## 4. What this record does not decide

Everything fenced: mutability, supersession, unminting, correspondence strengthening, the
database shape. Also: the utterance primitive's own shape (it is the evidence family's first
build question, not this one); whether the anchor's minted-by reference is a column or a
relation; whether one utterance can mint one party only (it should — one individuating
assertion, one identity — but that is the utterance's cardinality question, next).

---

## 5. Ruling candidate — for Rob

> **The minting assertion lives in the evidence family as an utterance — origin `Person`,
> with strength — beside every other claim the household makes; its descriptors are its
> content and become correspondence evidence, never identity columns. The minted institution
> is the utterance's subject and the utterance is the institution's provenance: the
> institution anchor references the utterance that minted it, and that pointer is the one
> evidentiary thing an anchor carries — a reference to a claim, not a claim. References to the
> institution remain non-evidentiary; its existence is not. Consequently the institution
> slice depends on the evidence family's utterance primitive and is built after it, never
> with an inlined assertion.**

If ruled, the next question is the evidence family's first: **the utterance primitive** — the
smallest representation of *a claim made by a party, with strength, about a proposition* —
which the minting assertion, the servicer-of-record relation, and every correspondence claim
all turn out to be.

---

## 6. Ruling — Rob, 2026-09-12. §5 ruled. The point where the ontology stops describing the architecture and starts constraining its implementation order.

**The strongest sentence:** *the anchor references the utterance that minted it, and that
pointer is the one evidentiary thing an anchor carries — a reference to a claim, not a claim.*
The anchor does not become a second evidence store because the thing it identifies was
created by evidence.

**Locked in:**

1. **The utterance is the primitive, not an institution-specific mechanism.** *"My insurer is
   Lakeview Health"* creates no special `InstitutionAssertion` object; it is an ordinary utterance whose
   proposition happens to participate in identity creation. One evidence family expresses
   *"my insurer is Lakeview Health"* · *"this is my servicer"* · *"these two artefacts came from the same
   institution"* — the semantics differ, the primitive does not.
2. **"Subject created by the claim" is not circular.** It looks circular only if identity and
   proposition are treated as one object. The utterance existed as evidence before the
   institution existed as a party; after minting, the institution becomes the subject of that
   already-existing claim. This matters enormously for bad assertions: **a false
   correspondence does not retroactively mean the utterance never existed** (S3).
3. **The build dependency is genuinely forced** — *dependency, not a plan.* An institution
   anchor built first has only two implementations, inline assertion data or a provisional
   assertion representation, both competing with the family for the same claim, both to be
   reconciled later. The ordering is a consequence of the semantic dependency:

   ```text
   utterance → minting provenance → institution identity → correspondence / relations
   ```

**To watch in the next question.** *"The smallest representation of a claim made by a party,
with strength, about a proposition"* is the right boundary — and it must not silently answer
**what propositions are.** The next ruling establishes the primitive's minimum semantics —
**origin · strength · proposition**, plus whatever provenance the evidence doctrine already
forces — and does **not** decide whether propositions are normalised objects, strings,
structured predicates, or typed relations. That would be designing the table while settling
the ontology.

**A question hiding inside it, to be demonstrated from the corpus rather than assumed:**

> **Does an utterance exist independently of whether its proposition is true, resolvable, or
> even currently understood?**

The prior rulings point strongly to *yes* — otherwise S3-type false assertions cannot be
represented cleanly — but it is shown, not assumed, the way this record showed its answer.

**Accepted as the next fence:** don't build the institution · don't design its table · don't
decide unminting · **establish the evidence primitive first.**
