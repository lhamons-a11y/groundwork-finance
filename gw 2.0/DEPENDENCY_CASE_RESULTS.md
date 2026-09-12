# Dependency case results — each cluster of the map taken to its case

> Status: **Case pass, 2026-09-12. No decision is made here; no arrow on the map is redrawn.**
> `DECISION_DEPENDENCY_MAP.md` (`08e28c0`) classified the relationships between the ten
> decisions. This pass takes each cluster to the case Rob named and asks one question per arrow:
> *does the case confirm the relationship as classified, weaken it, show the two independent, or
> leave it unresolved?* A case can prove that two decisions interact without proving what either
> should be, and every block below keeps those apart.
>
> **Format, Rob's:** result · what the case proves · what it does not prove · decision remaining.
> **Method:** the cases as written in the cited documents, against `core/` as built at
> `b2ba294`. Nothing was re-run; where a claim rests on code it is quoted.
>
> **Not another gap hunt.** Where a case turned up something beside the arrow it was testing,
> it is recorded under the arrow and not promoted to the board.

---

## Cluster A — meaning. The write-off, then the recourse case

Rob's test: *does the same interpretation of what is carried survive both cases, or does one
force a distinction the other doesn't? If the answer changes with disposition scope, that is
evidence for the mutual dependency; if one interpretation survives both, the coupling weakens.*

### 1 ↔ 2 — §7.7 *carries* ↔ disposition scope

```text
CASE RESULT
    1 ↔ 2 is:  CONFIRMED mutual constraint, no gate — and sharpened:
               each answer to 2 makes a DIFFERENT dimension of 1 mandatory.

WHAT THE CASE ACTUALLY PROVES
    The write-off (DISPOSITION_VOCABULARY_CASES 4b) separates books from obligation INSIDE ONE
    PARTY: the provider writes $50 off its own books and remains entitled to sell, pursue or
    report it. So 2 is posable, with content, before any second party exists — 1 does not gate 2.
    The recourse case (OBLIGATION_LIFECYCLE_QUESTION §9–10) splits funding/servicing from
    risk with NOTHING happening to any amount — the return leg moves who holds the obligation,
    not its treatment. So 1 is posable, with content, before any disposition exists — 2 does not
    gate 1.

    The constraint, run both ways:
      2 = books      → a disposition must name WHOSE books. Under recourse the vendor's books
                       (receivable repurchased) and the provider's (receivable re-recognised)
                       both move for one event, so 2 = books requires 1 to be multi-party and
                       makes the FUNDING dimension mandatory (the party that accounts for the
                       receivable).
      2 = obligation → the write-off has no disposition at all; the recourse return is a
                       *carries* event, not a disposition; and case 8's $3,000 destination
                       (same obligation vs successor) waits on M1/M2, which waits on 1. So
                       2 = obligation makes the ENTITLED-TO-COLLECT dimension mandatory and
                       hands 2's destination range to 1's chain.
    Rob's test answered: the interpretation of *carries* that survives both cases is not one
    dimension (recourse already showed that); which dimension 2 NEEDS changes with 2's answer.
    That is the mutual dependency, in a form the map's prose did not have.

WHAT IT DOES NOT PROVE
    Which reading of 2 is right. The write-off's user-facing sentence ("it is gone" may be
    false) argues against a naive books reading, but a deliberately defined abstraction over
    both is the third option the blocker names and neither case rules it out.
    Whether the four dimensions of 1 collapse to fewer once 2 is answered — only that at
    least one becomes mandatory either way.
    Anything about M1/M2. Case 8 still fires the fence.

DECISION REMAINING
    Both, and jointly: §7.7's *what fact is it trying to distinguish, and what downstream
    behaviour does that control* (Rob's); and disposition scope (Rob's). The pass adds one
    constraint to the joint answer: the pair must agree on which dimension is mandatory.
```

### 1 ──X──► 5 — held

The recourse case never produces a proposition. *Who bears this* is a fact about the
obligation's parties, recorded on the obligation; the proposition space in `core/classification`
is about transactions on an axis. Nothing in either case needed a proposition to hold a
*carries* value. **X stands.**

---

## Cluster B — identity. The value re-parse cases

Rob's test: *can we identify what proposition is being disagreed about without making the
document itself the proposition? And does verdict strength have an independent dimension, or
does it inherit whatever evidence representation happens to exist?*

### 4 ↔ 5 — document referent ↔ proposition space

```text
CASE RESULT
    4 ↔ 5 is:  CONFIRMED mutual constraint, no gate.

WHAT THE CASE ACTUALLY PROVES
    Rob's question has a case-driven answer, and it is yes. D3/D4 (DOCUMENT_IDENTITY_CASES)
    and D5 together give an artefact three roles, none of which is "the proposition":
        SUBJECT    the proposition is about the artefact — "this EOB says $412"       (D3, D5)
        SOURCE     the artefact is evidence for a proposition about the world          (D4)
        REFERENT   the thing held or known-of that the evidence instance points to     (D1/D2)
    D3 is a disagreement about a SUBJECT proposition (two readings of what one document says).
    D4 is a disagreement about a WORLD proposition with two SOURCES. Same tuple today; different
    propositions once 5 opens; different remedies (re-read vs adjudicate). The document is never
    the proposition — it is what the proposition is about, or what supports it.

    Neither gates:
      4 without 5 — D3 as recorded: two readings of one artefact are FINDABLE with a referent
                    and their disagreement is still not SAYABLE ("document identity makes the
                    readings findable; something else has to make their disagreement sayable").
      5 without 4 — D8 and V2: utterances need no referent, and *patient responsibility is $50*
                    vs *$75* is a proposition-with-value disagreement between two statements
                    with no artefact anywhere.
    Each constrains: the SUBJECT role is a proposition kind (5) that cannot be posed without the
    about/referenced distinction (4); and a same-referent disagreement (4) has no content until
    a proposition can carry a value (5).

WHAT IT DOES NOT PROVE
    That the three roles need one abstraction. The DI boundaries (document ≠ obligation
    identity; instance ≠ independence) still hold them apart, and the case gives no reason to
    merge subject, source and referent into a field.
    Which reading of the re-parse is right — "a parse dispute, not something position or
    recency should answer" is still the whole of what is known.

DECISION REMAINING
    4 (bytes held vs identity asserted; which of the five distinctions an instance carries) and
    5 (whether the space opens). Both Rob's. The pass adds: whichever way 5 opens, it needs the
    SUBJECT role to be expressible, and that is a requirement on 4's vocabulary, not on 4's
    answer.
```

### 5 gates 6 — proposition space gates verdict strength

```text
CASE RESULT
    5 → 6 is:  CONFIRMED as a gate on CONSEQUENCE; WEAKENED as a gate on FORM.
    6 has an independent dimension (Rob's second question): yes.

WHAT THE CASE ACTUALLY PROVES
    V3 (VALUE_DISAGREEMENT_CASES): U:yes → E:no → U:no. Two knowing sources agree on a
    negative and the lattice puts it at the floor, because rank is support-for-P and P is
    *health*. That question — should a well-supported negative rank as well-supported? — is
    posable TODAY, with the two-axis space, so 6 is not contentless without 5. Form: weakened.
    But with today's space the floor is harmless: `contradicted` → every consumer refuses →
    tax gets $0, which is the right figure for a negative. No consumer is wronged. The first
    proposition for which a negative verdict's STRENGTH reaches a consumer is a value
    proposition — "it is well established that the document says $412" — and that exists only
    if 5 opens. Consequence: gate confirmed.
    Independence: the case set records the strength question as "a second layer on the same
    root" that "survives the first being fixed." Verdict strength is not inherited from the
    evidence representation; it is a function over it that has to be chosen.

WHAT IT DOES NOT PROVE
    What strength should mean once 5 opens. The case set's own fence: "it must not be smuggled
    in with the proposition change."
    Whether the boundary question and value questions want the SAME notion of strength — V3
    raises exactly that (right for *is this inside the health zone*, wrong for *what does the
    document say*) and answers it for neither.

DECISION REMAINING
    6, Rob's, and the case sharpens its shape: it is not "how strong is a verdict" but
    "does one lattice serve both a boundary proposition and a value proposition, or does
    strength split with the space." That is still one decision; the case shows it has two
    possible answers with different consumers.
```

---

## Cluster C — time. The late-discovered mid-year change (T4/T8)

Rob's two questions, kept separate:

```text
period close:   what historical transition must be representable?
overlap:        what must the system say while competing effective periods remain?
```

And his instruction: *test whether either answer actually forces the other. Don't assume the
mutual arrow is vindicated merely because they're related.*

### 7 ↔ 8 — period-close shape ↔ overlap policy

```text
CASE RESULT
    7 ↔ 8 is:  WEAKENED. 8 constrains 7 under one of 8's answers. 7 does NOT constrain 8.
               The map's 7 → 8 argument rested on the OPERATION GAP, not on 7's decision.

WHAT THE CASE ACTUALLY PROVES
    Q1 (period close) answered by T4/T8: the transition is *was true, and stopped being true
    earlier than we recorded* — with the effective boundary (June 30), the recorded time (now),
    and the PRIOR BELIEF preserved (as_of before the close must still say the full-year plan
    covered August; T8 shows the direct mutation loses exactly that). Requirement 1 in the case
    doc, and it holds under either shape of 7.
    Q2 (overlap) answered by requirement 4: *two plans claim August; which one was it?* —
    detectable, never a silent tie broken by position.

    Does 7 force 8?  No. Take either shape of 7 — a new *close* operation, or *correction*
    extended to periods. In both, T4 arrives the same way: Jan–Dec on file, Jul–Dec entered.
    At that moment overlap exists until the user closes the first, and 7's shape says nothing
    about whether the system refuses the add ("close Jan–Dec first") or records the state and
    reports it. Both are coherent with both shapes. The map's argument for 7 → 8 — "a close
    that does not exist forces overlap to be representable" — is true of the DEFECT (no period
    operation at all) and disappears the moment either shape of 7 exists.

    Does 8 force 7?  Under one answer. 8 = represent-and-report puts the overlap in the record
    as a truthful state, so guarantee 2 (as_of reproduces the record's view, including its
    gaps) now has to reproduce a period during which two plans claimed August and neither
    governed. When the user later closes one, the operation is recording the RESOLUTION OF AN
    AMBIGUITY — which is neither *what was always true* (correction) nor *what was true and
    ended* (close). So 8 = represent enlarges the provenance vocabulary 7 must carry by one
    kind. 8 = refuse needs no such thing: overlap never enters the record, and 7 needs only
    the two kinds T4 already forced. One-way, branch-conditional constraint.

WHAT IT DOES NOT PROVE
    Which shape 7 takes. The case doc's own criterion — whether *ended earlier* has different
    provenance and history semantics from `correct_terms` — is untouched by overlap under
    either answer.
    Which answer 8 takes. C9's *ask, don't manufacture* precedent is still the only evidence,
    and it favours represent-and-report without deciding it.
    That the two are independent. They are not: 8 = represent reaches into 7. But the symmetric
    arrow on the map overstates it, and the map should stay as drawn per Rob — this document is
    where the weakening is recorded.

DECISION REMAINING
    7 and 8, both Rob's, and the pass changes the order in which they are USEFULLY asked without
    forcing it: 8 first tells you how many provenance kinds 7 must carry; 7 first tells you
    nothing about 8.
```

### Off-board rule 2 (effective-at ≠ learned-at) constrains 7 — held

T4/T8 is the rule's instance in a different module. The prior belief that has to survive
(*in March we believed the PPO ran all year*) is `recorded_at` doing exactly what
`OBLIGATION_LIFECYCLE_QUESTION.md` §10 says it must. **Constraint stands**, and it is the reason
the "resolution of an ambiguity" kind above is not free: it too must carry both dates.

---

## Cluster D — teaching boundary. Two CVS rows under *Other*, manufactured

Rob's chain, and the instruction not to collapse it:

```text
fact exists  →  fact survives representation  →  narrator receives it  →  narrator may say it
```

The cases established the first two can hold while the third fails (`DerivedFact` carries
`Sensitivity(health, manufactured=True)`; `NarratorFacts` has no field). The remaining
decisions: *whether preserving `Sensitivity` at #9 is necessary for some F3 behaviour, and
separately whether that information would ever authorize speech.*

### 3 → 9 constrains; 9 = NO forecloses 3's "carry it" branch

```text
CASE RESULT
    3 → 9 is:        CONFIRMED constraint (under 3 = keep the miss-log).
    9 = NO ⇒ 3:      CONFIRMED foreclosure — with its resting assumption named.

WHAT THE CASE ACTUALLY PROVES
    The narrator receives metric='category_delta:Other', value=180.0. The sentence it builds —
    "Other spending is up $180" — is health-sensitive by HEALTH_TRUST_BOUNDARY §8 limb 2
    (classification domain: the DerivedFact is health-domain and transformation does not
    declassify), and NOT by limb 3 (available inference: nobody can infer health from it —
    which is the whole point of the adversarial case). So a miss-log that stores the sentence
    stores health-sensitive content, and the only way it can know that is if the domain
    travelled to the point the sentence was built. That point is `NarratorFacts`. 3 = keep
    requires 9 = yes.
    Foreclosure: `includes_records=False` is asserted, so the narrator cannot reconstruct the
    domain from records it does not hold; §9 says sensitivity is attached upstream, never
    re-derived. With 9 = no there is nothing at the sentence to carry, and 3's first branch is
    not available. The F3 fork would have been answered by 9.

WHAT IT DOES NOT PROVE
    That 9 = no forecloses 3 = keep if the narrator obtains sensitivity by a path OTHER than
    `NarratorFacts` — e.g. a surface that reads `DerivedFact.sensitivity` directly and hands it
    to `callAI()` beside the facts. That is the consumer-bypass class the boundary fixture exists to catch, and
    today its AST scan (`tests/test_consumer_boundary_fixture.py`, `sub.attr == 'value'`)
    covers `.value` reads only, not `.sensitivity`. The foreclosure rests
    on the rule that the narrator's only input is its declared representation — a rule the
    repository holds by test for `.value` and by convention for everything else.
    That 9 = yes is sufficient for 3 = keep. The miss-log also stores the model name, failed
    gate rules and timestamp; whether those are sensitive is limb 3 applied to them, and the
    case does not reach it.

DECISION REMAINING
    3 (Rob's). 9 (Rob's), no longer free to be decided after 3 as if 3 could then be weighed on
    its merits. And one wiring condition the case adds to the register's existing one: when a
    narrator consumer is wired, the fixture's scan should cover `.sensitivity` as it covers `.value`,
    or the foreclosure has a route around it.
```

### 9 ↔ 11 — enforcement locus only; X on the policy in both directions

```text
CASE RESULT
    9 ──X──► 11 (policy):   CONFIRMED. Carrying grants nothing.
    11 ──X──► 9 (policy):   CONFIRMED. "Never" is enforceable with 9 = no.
    9 ↔ 11 (locus):         CONFIRMED — and the case shows 11 is LIVE under 9 = no, by a path
                            the map did not name.

WHAT THE CASE ACTUALLY PROVES
    In the two-CVS case the narrator does not voice a suspicion. It voices a figure. The
    manufactured suspicion — "these are health transactions" — is something the narrator never
    says because it does not hold it. So under 9 = no, 11 is not engaged by THIS case in the
    narrator: the danger is a health-sensitive sentence nobody knows is one (3's problem), not
    a voiced suspicion (11's).
    But 11 is not vacuous under 9 = no. The same case set has two more rows:
      accidentally inferable   metric='category_delta:Prescriptions' — the string carries what
                               the field does not, and a language-model narrator can voice
                               health from it;
      the reverse              memo *wheelchair ramp lumber*, both axes not_evaluated — the
                               record holds no suspicion, and a narrator that reads memos would
                               MANUFACTURE one from wording and could say it.
    So 11 has a subject that exists whatever 9 says: a suspicion manufactured by the NARRATOR
    from strings, not by the classifier from merchant/MCC. That is governed today by B.2a
    (templated, never free-generated) and principle 1 (no inference without evidence), not by
    any field.
    Locus: "never" for classifier-manufactured suspicions is enforceable at `_permitted_value`
    — `DerivedFact.sensitivity.manufactured` is available there, beside the strength the
    boundary already refuses on — without `NarratorFacts` carrying anything. So 9 does not
    gate 11's policy or its enforcement. What 9 = yes buys is the ability to enforce anything
    FINER than never/always inside the narrator (a register answer: "voiced as uncertain").
    Locus constraint confirmed both ways: the policy's granularity decides whether the field is
    needed; the field's presence decides where the policy can live.

WHAT IT DOES NOT PROVE
    What 11's answer is. Deliberately.
    That refusing manufactured rows at the boundary is the right locus — only that it is an
    AVAILABLE one, which is what defeats "9 gates 11".
    That 11 as written on the board is one decision. The case shows two referents for
    "manufactured": the record's flag and the narrator's own inference from language. Recorded,
    not split — splitting a decision is Rob's, and the second referent may already be settled by
    B.2a rather than open.

DECISION REMAINING
    11 (Rob's). The pass adds one thing to its statement: say which manufacturer it governs —
    the classifier's flag, the narrator's inference from strings, or both.
```

### 3 ──X──► 11 — held

The miss-log stores *rejected* narration. A sentence refused by a gate for voicing a suspicion
is exactly what the log is for. 3's answer says what the log may persist; it says nothing about
what the narrator may say. **X stands.**

### 10 — outside the cluster, and the case says where its requirement would come from

```text
CASE RESULT
    10 is:  INDEPENDENT — confirmed. Not promoted. But the case locates its consumer.

WHAT THE CASE ACTUALLY PROVES
    `export_row` carries `sensitivity.domain` and drops `manufactured`; `backup_row` delegates
    to it and is not in `CONSUMER_STRENGTH`. IF a backup is a round trip — restored rows become
    facts again — then a restored health-domain fact arrives with manufactured absent, which
    reads as *asserted*: the most sensitive thing the module holds restored as the least. That
    is declassification by transformation, forbidden by HEALTH_TRUST_BOUNDARY §8. So 10 has a
    consumer requirement conditional on ONE decision: what a backup is allowed to contain and
    whether it round-trips — which the code's own comment names as the decision Q1 was not.

WHAT IT DOES NOT PROVE
    That backup round-trips. `backup_row` has no caller; nothing restores anything today.
    That export (as distinct from backup) needs the distinction. No export consumer exists.
    Any dependency on 9. Same two helpers, same module, still two decisions.

DECISION REMAINING
    10, and it now has a named precondition: it becomes a decision with content the day backup's
    contents are decided, and not before. Until then, independent.
```

---

## What the pass changed, in one place

| Arrow | Map said | Case says |
|---|---|---|
| 1 ↔ 2 | mutual constraint | **confirmed**, sharpened: each answer to 2 makes a different dimension of 1 mandatory |
| 1 ──X──► 5 | not established | **held** |
| 4 ↔ 5 | mutual constraint | **confirmed**; artefact has three roles, none is the proposition |
| 5 gates 6 | gate, not constraint | **confirmed in consequence, weakened in form** — 6 is posable today, consequential only once 5 opens; 6 is an independent dimension |
| 7 ↔ 8 | mutual constraint | **weakened**: 8 = represent constrains 7 (one more provenance kind); 7 does not constrain 8; the 7 → 8 argument was the operation gap talking |
| rule 2 → 7 | constraint | **held** |
| 3 → 9 | constraint | **confirmed** under 3 = keep |
| 9 = no ⇒ 3 | foreclosure | **confirmed**, resting on the declared-input rule; the boundary fixture scans `.value` only |
| 9 ↔ 11 | locus only; X on policy | **confirmed**; 11 is live under 9 = no via the narrator's own inference from strings |
| 3 ──X──► 11 | not established | **held** |
| 10 | independent | **confirmed**; requirement located in backup-as-round-trip, conditional, not promoted |

**No arrow became a gate that was not one. One mutual arrow became one-way and conditional.**
The map stays as committed; this document is the record of what the cases did to it.

**Which of the ten are now mechanically constrained versus Rob's.** None became mechanical.
Three acquired a constraint on their *joint* answer that the map's prose did not have — 1/2
must agree on a mandatory dimension; 8 = represent obliges 7 to carry a third provenance kind;
9 = no must not be chosen as if 3 were still open — and two acquired a precondition — 6's shape
(one lattice or two) and 10's consumer (backup's contents). All ten remain Rob's.

**Next:** not a cluster pass over the same cases again. The three joint constraints are the
things to take to Rob, in his words, as the questions the cases have earned.
