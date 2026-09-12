# What a proposition is — the last semantic question before the evidence family can be built

> Status: **Design mode, 2026-09-12. No representation designed. No table, no code.** The
> question every record since Cluster B has fenced, opened by Rob under seven accumulated
> constraints and one danger test.
>
> **The constraints, from the rulings:**
>
> ```text
> 1  a proposition has a KIND — the origin's knowing relation is evaluated against it
> 2  it can take a PARTY as subject
> 3  it can take an UTTERANCE as subject
> 4  the subject can therefore be something CREATED BY ANOTHER ASSERTION
> 5  truth, resolution and comprehension are NOT prerequisites for its existence
> 6  it cannot collapse into the utterance — the SAME proposition can be asserted by multiple utterances
> 7  identical TEXTUAL CONTENT does not necessarily mean identical proposition semantics
> ```
>
> **The danger test:**
>
> > **Can the proposition be reduced to either (a) text/content, or (b) a relation between
> > already-existing parties?**
>
> If either reduction fails in the corpus, Groundwork needs a genuine proposition concept
> rather than an `utterance.text` field or a set of typed foreign keys. The two cases to test
> are the ones the record already produced:
>
> ```text
> Person ─ asserts → [proposition A] ─ subject: Institution S3
> Person ─ asserts → [proposition B] ─ subject: an earlier utterance
> ```
>
> **Fenced:** the representation (string · predicate · graph edge · typed object · normalised
> row); how propositions are compared for sameness (beyond what the corpus forces); the
> full catalogue of kinds; any table.

---

## 0. What the corpus already holds as propositions — the inventory

Before testing reductions, the propositions the rulings have actually named, each with its
subject and the party that is knowing for it:

| proposition, as ruled | subject | knowing party | where |
|---|---|---|---|
| *this transaction is health on axis X* | a transaction | user · insurer | `core/classification.py`, the two-axis space |
| **P-subject** — *artefact A states patient-responsibility = $412* | an **artefact** | whoever read A | Cluster B ruling |
| **P-world** — *patient-responsibility for this claim = $412* | the world (the claim) | nobody — §8.2a's premise | Cluster B ruling |
| **P-ack** — *E's stated position on payment p / balance b, as of d* | a **party's stance** | E only | acknowledgment ruling |
| *S serves P* (servicer of record) | two **parties** | the household (asserted) | S1–S3, contract C3 |
| *P is E of obligation X at d* | a party and an **obligation** | the household; E's own documents | disposition doctrine |
| *B supersedes A* | two **artefacts** | the issuer of B | tie ruling T4 |
| *arrival R corresponds to artefact X* | an **artefact** and an arrival | hash · issuer id · the household | identity primitive |
| *this institution exists, described as …* (the minting assertion) | a **party the assertion creates** | the household | minting ruling |
| *Monday's assertion was wrong* | an **utterance** | the household | identity ruling, Case B |
| *the classification of row r is manufactured* | a **classification** | no party — a process | sensitivity ruling |

Seven different subject types across eleven ruled propositions: a transaction, an artefact,
the world, a party's stance, two parties, a party and an obligation, an utterance, a
classification. That inventory is the evidence for §1 and §2.

---

## 1. Reduction (a) — the proposition is its text

Under (a), the proposition *is* what the party wrote or the parser extracted: `utterance.text`.
Sameness is string equality; kind is inferred from the string; subject is whatever the string
mentions.

**Constraint 7 already rejects it, and the corpus supplies the cases:**

- **The category-name ruling** (`CLASSIFICATION_QUESTION.md`): *a category name's axis depends
  on who set it* — `Prescriptions` set by the user is content evidence (*it was health*);
  `Prescriptions` set by the importer is counterparty evidence at best. **Identical text, two
  propositions**, and the difference is not in the string.
- **D5**: *"the EOB says it was health"* and *"it was health"* — two propositions (one about an
  artefact, one about the world) that a text reduction would have to distinguish by parsing
  *"the EOB says"*, and that the ruling distinguished by **subject type**, not wording.
- **RA6 versus RA1**: *"a letter from the hospital said $1,925"* and *"the Sept 1 statement
  from P says $1,925"* differ in whether the proposition *has a subject at all* — below
  individuation there is no referent. A text reduction has a string in both cases and no way to
  say one of them is not about anything.
- **Case A of the identity ruling**: two utterances with identical text are, by constraint 6,
  two assertions of **one** proposition — which is right, and which (a) gets by accident;
  but **the category-name case shows identical text can also be two propositions**, so text
  equality is neither sufficient nor necessary for proposition sameness. It is correlated with
  it, the way a description is correlated with an artefact's identity — and the identity
  ruling already placed descriptions as *correspondence evidence, never identity*.

**And the reverse failure:** V4's `$412` and `$4.12` are two claims about **one** proposition
(P-subject for artefact A) with different values. Under (a) they are two propositions with
nothing in common, and the parse dispute — the thing Cluster B exists to represent — is
unrepresentable: there is no *one thing* the two readings disagree about.

**(a) fails.** Text is the *content* of an utterance or a reading — intrinsic to the act, per
the identity ruling — and it is **evidence for which proposition was asserted**, not the
proposition. Exactly the shape of every prior reduction the record has rejected: description
for artefact identity, enum for origin, `[-1]` for resolution.

---

## 2. Reduction (b) — the proposition is a relation between already-existing parties

Under (b), a proposition is a typed edge — `(kind, subject_fk, object_fk, value)` — between
things that exist as rows: parties, obligations, artefacts. No proposition concept; a set of
relation tables.

**Rob's two cases test it directly, and it fails on both:**

- **Case A — subject: Institution S3.** At the moment the household asserts *"my servicer is
  S3"*, S3 **does not yet exist as a party** — the assertion is what mints it (the encounter
  ruling: *the assertion establishes/mints the identity; then the institution becomes the
  referent*). A typed foreign key to `parties` cannot be written before the row it points to
  exists, and the row exists *because* the proposition was asserted. Under (b) the minting
  assertion cannot be represented: the relation needs its object first, and the object needs
  the relation first. **(b) makes the one identity-creating event of the institution branch
  unrepresentable** — constraint 4 in its sharpest form.
- **Case B — subject: an earlier utterance.** *"Monday's assertion was wrong"* is a proposition
  whose subject is **an evidence event**, not a party or a thing in the world. Under (b), the
  relation tables would need an edge type *utterance → utterance*, which is representable —
  but then "already-existing parties" was never the right description of what propositions
  relate; they relate **anything the record holds**, including its own evidence. That is not a
  relation *between parties*; it is a claim *about the record*.

**And the inventory in §0 finishes it.** P-world's subject is *the world* — nothing the record
holds a row for; P-subject's is an artefact; P-ack's is *a party's stance as of a date* — not
the party, a position the party took. Seven subject types, one of which is nothing at all and
one of which is evidence. A typed-FK model would need a relation table per (kind × subject
type × object type), and would still have nowhere to put *"the world."*

**(b) fails.** Propositions are not relations between existing rows. Some of their subjects
are rows; some are created by the assertion; some are evidence; one is the world.

---

## 3. What survives — the proposition as its own concept, and what it minimally is

Both reductions fail, so the record needs **a genuine proposition concept**. The corpus fixes
what it minimally must be, without fixing how it is represented:

> **A proposition is a claim-shape: a *kind* (which determines who can be knowing for it), a
> *subject* (which may be a transaction, an artefact, a party, a party's stance, an
> obligation, an utterance, a classification, or the world — and which may be brought into
> existence by the assertion that first asserts the proposition), and a *content* (what is
> claimed about the subject — a value, a relation, an existence). It exists independently of
> its truth, its resolution, and any party's ability to interpret it. One proposition may be
> asserted by many utterances and read from many artefacts; two propositions may share every
> word. Sameness of propositions is not sameness of text and not sameness of rows.**

Three things that follow, each already forced somewhere in the record:

1. **Kind is primary.** Constraint 1: the knowing relation is defined over kinds (health: user,
   insurer; P-ack: E; P-world: nobody). A proposition without a kind has no strength function,
   no independence semantics, and no fail-closed terminal. Kind is the one thing that must be
   known about a proposition before anything else can be computed about it.
2. **Subject is a reference into the record *or* an absence, and it may be created by the
   assertion.** Cases A and B: the subject of the minting assertion is a party the assertion
   mints; the subject of a correction is an utterance. And RA6: a proposition may have **no
   subject** — below individuation — and still exist as *what was asserted* (constraint 5),
   which the record holds as an utterance whose proposition's subject is *not established*.
   The four party states arrive at the proposition's subject: established · not established
   (with candidates) · no subject (the world; a process).
3. **Content is what disagreement is *about*.** V4's two readings share kind and subject and
   differ in content; that is what makes them a parse dispute rather than two propositions.
   T3's two statements share kind, subject, as-of and differ in content; that is a tie.
   RA5's two members share everything; that is two utterances of one proposition.
   **Disagreement is representable only because propositions have parts** — a text
   reduction has no parts, and a relation reduction has no content for *the world.*

---

## 4. The one thing this record adds that the constraints did not have

**The subject may be *not established* without the proposition being absent.** The party
ruling's four states were about a *reference to a party*; §3.2 shows they are really states of
a *proposition's subject*, of which a party reference is one case. *"My servicer is Acme"* with
two Acmes on file: kind established (a servicing relation), content established (*serves me*),
**subject not established, with candidates**. The utterance exists (P4), the proposition exists
(constraint 5), and its subject is what correspondence work will settle. This is the same
sentence as RA2's *asserted referent, currently ambiguous* — now located: it is the subject
slot of a proposition, not a property of the utterance.

---

## 5. What this record does not decide

The representation — whether kind is an enum or a table, whether subject is a polymorphic
reference (the party-shape ruling's anchored pattern is the obvious candidate and is *not*
chosen here), whether content is a value column, a JSON blob, or a set of typed columns per
kind; the catalogue of kinds (the record has at least eleven; whether they are eleven kinds or
five kinds with sub-shapes is design); how two propositions are compared for sameness beyond
*same kind, same subject, same content*; whether P-world propositions are ever stored as
propositions or only ever as premises (§8.2a); any table.

---

## 6. Decision remaining — Rob's

Whether §3 is the proposition concept: kind · subject · content, subject possibly created by
the assertion and possibly not established, content the locus of disagreement, existence
independent of truth and interpretation, sameness neither textual nor relational. If ruled,
**the evidence family is semantically complete** — artefact, reading, utterance, proposition,
party, correspondence — and the next question is the first that designs a representation for
any of it, which is a build-mode question: *what is the smallest schema that carries these six
without collapsing any of the distinctions the rulings drew.*
