# What may be concluded from a transaction? — the classification question

**The open decision the classifier is waiting on**

> Status: **Answered and built 2026-09-07.** Three positions and four resolutions; what remains
> is a measurement and a line of product copy, neither of which blocked the classifier.
> `core/classification.py` now exists and satisfies the fixture — 56 assertions, and 12 of 12
> mutations detected. Raised by `ARCHITECTURE_REVIEW_P0.md` §2b and
> `ARCHITECTURE_REVIEW_LIFECYCLE.md` §C2, which the P0 review itself flags as the largest
> unresolved item.
>
> **Upstream of both the classifier and the privacy gate**, and that is the review's own reason
> for settling it first: each one changes what the other must do, so building either first fixes
> the other's shape by accident.
>
> `OBLIGATION_SEMANTICS_QUESTION.md` and `EVENT_SUBSTRATE_QUESTION.md` are the two closed
> questions this one sits beside. It follows their method — settle the semantics, pre-register
> what would falsify the answer, and let a fixture written first decide it.
>
> `tests/test_classification_fixture.py` is that fixture. It fails on purpose.

---

## How it surfaced — two vocabularies, six minutes apart

The lifecycle review, at 14:31 on 2026-09-06, sets the rule:

> states must be named in **evidence terms, not policy terms** — a state called
> `SUPPORTED_HEALTH_CLASSIFICATION` has already smuggled in a policy judgement (supported enough
> for *what?*)

The P0 addendum, at 14:37, proposes:

```text
SUPPORTED_SIGNAL · POSSIBLE_SIGNAL · NOT_SUPPORTED · UNKNOWN
```

`SUPPORTED_SIGNAL` and `POSSIBLE_SIGNAL` invite exactly the banned question. Supported enough
for a lever? For a tax line? For a sentence the narrator may say? Three different answers, one
state name.

**This is worth recording rather than quietly fixing.** Both passages were written by the same
reviewer in one sitting, with the rule fresh, and the drift still happened inside six minutes.
It is the fourth appearance of principle 1's fusion, and the thing it demonstrates is that
naming a state by what you intend to do with it is the *default*, not a lapse. A vocabulary that
resists it has to be chosen deliberately and then defended in review.

---

## Position 1 — the vocabulary is evidence-shaped, and it has two fields, not one

C2 proposes two things that have been read as one. They are separate and both are needed.

**Source** is a property of each piece of evidence — where this particular signal came from:

```text
user_stated · imported_eob · merchant_match · mcc · inferred
```

**Evidence state** is the summary across all the evidence held about one claim:

| State | What is known |
|---|---|
| `user_asserted` | the user said so |
| `imported_attested` | a party with knowledge recorded it — EOB, pharmacy record, custodian statement |
| `corroborated` | two or more independent signals agree |
| `single_weak_signal` | exactly one signal, and it is not from a knowing party |
| `contradicted` | evidence exists and points away |
| `not_evaluated` | never examined |

C2's list is `user_asserted`, `corroborated`, `single_weak_signal`. **The last two states are
added here, and the gap they close is principle 2.**

> `not_evaluated` and `contradicted` are not the same state. *We never looked* and *we looked and
> found against it* produce the same result for every consumer that exists today, which is
> precisely the condition under which they get collapsed and a later consumer arrives that must
> tell them apart.

The one that will be asked for first is a reclassification audit: *what did Groundwork examine
and rule out?* is a different and more useful question than *what has Groundwork not looked at?*,
and a merged state answers neither.

`not_evaluated` also does structural work further down: it is the overwhelming majority of the
transaction universe, and it is what makes the fail-closed boundary tractable rather than global.

`imported_attested` generalises C2's `imported_eob`. An EOB is one instance of *a party with
knowledge of the transaction recorded what it was*; a pharmacy history and an HSA custodian
statement are the same kind of evidence and must not each earn their own state.

**And no confidence number, per C2.** `if confidence > 0.8` is an invented threshold over an
invented quantity driving a protection decision invisibly — the null-model failure this project
has already paid for twice. *Never protect on `single_weak_signal` alone* is testable in a way
that a float never is.

---

## Position 2 — protection and tax do not need two thresholds. They need two axes

C2's reason that one classification cannot serve both is the error asymmetry: protection
over-includes because a false positive costs one unavailable lever, tax under-includes because a
false positive costs a wrong return. That is right, and it still frames the problem as one axis
with two cut points.

The CVS transaction shows it is not one axis. A merchant match is **certain about the
counterparty and silent about the content.** Prescription, birthday card or crisps — the bank
record cannot distinguish them, and it never will, at any evidence strength.

```text
axis 1   counterparty    what kind of party received this money
axis 2   content         what this money bought
```

Each axis carries its own evidence state. A CVS charge is `corroborated` on axis 1 — merchant
name and MCC agree — and `not_evaluated` on axis 2, because nothing in a bank record speaks to
it.

**The wall between the axes is the finding.** No accumulation of counterparty evidence
establishes content. Ten CVS transactions are ten pieces of axis-1 evidence and zero pieces of
axis-2 evidence. This is what makes one-classification-two-thresholds impossible rather than
merely awkward: the thresholds would be reading a claim that the evidence never made.

Which lets each policy read the axis it is entitled to:

| Consumer | Reads | Because |
|---|---|---|
| Necessity floor / lever eligibility | **axis 1** | over-inclusion costs one lever, a trade `is_protected`'s docstring already accepts |
| Tax qualifying total | **axis 2 only** | a false positive is a wrong return — the one place being wrong has a legal consequence for the user |
| Narrator, export, backup | **either, and the sensitivity that came with it** | see position 3 |

And the invariant, which is mechanical and mutation-provable in a way a threshold is not:

> **No tax line may cite an axis-1-only classification.**

### What follows, and it is not comfortable

Axis 2 is established in practice by `user_asserted` or `imported_attested` and by nothing else.
That is not a limitation to engineer around — **only the user, or a party present at the
transaction, knows what was bought.** Any mechanism that manufactures axis 2 from axis 1 is
guessing about a person's medical care to put a number on a tax return.

So Groundwork cannot build a Schedule A total from a bank feed. It can build one from what the
user has designated plus what has been imported, and it must show the axis-1-only set beside it
as **unevaluated** rather than absent.

That is the same shape as the qualifying figure in `OBLIGATION_SEMANTICS_QUESTION.md` — confirmed,
unresolved, and no definitive total — and the same rule as the dashboard's $7,053 phantom
shortfall. **Absence is not zero**, third appearance, this time in a classification rather than
an amount.

### The category name is not one signal, and its axis depends on provenance

This is where the two axes reach shipped code.

`is_protected('Prescriptions')` reads a category name. But a category is not evidence — it is an
interpretation already applied, and *whose* interpretation decides which axis it lands on:

```text
user set the category to Prescriptions      →  axis 2, user_asserted
importer assigned it from the merchant      →  axis 1, at best merchant_match
```

**Two transactions with identical category names, different tax treatment.** The
user-confirmed one may reach the qualifying total; the auto-assigned one may not, and no
inspection of the string can tell them apart.

`Transaction` has no provenance column, so the row cannot answer this. The historian partly can —
`categorization_suggestion_confirm` and `_reject` are logged — which is `ASSISTANT_SCOPE.md`'s
*"set" is derived, not stored* arriving in a second subsystem. It is also
`ARCHITECTURE_REVIEW_LIFECYCLE.md` §A2 with a concrete consequence attached: the healthcare side
can be built perfectly and the chain still stops at a provenance-free ledger row.

---

## Position 3 — sensitivity attaches to the question, not to the verdict

§2b defines the sensitivity layer over the classifier's output. Read literally, `NOT_SUPPORTED`
creates nothing sensitive, because nothing was found.

That is wrong wherever the evaluation is **targeted at an identified person's record**. A stored
row saying *evaluated for health relevance, not supported* still discloses that this transaction
was health-suspicious enough to evaluate. The sensitive act was asking the question about a named
person, and the answer does not undo it.

So the sensitivity layer's input is the pair **(subject, claim domain)** — determined when the
question is asked — not the verdict.

| Evidence state, health domain | What is actually stored | Sensitivity |
|---|---|---|
| `user_asserted` | what the user chose to tell us | health-domain, user-originated |
| `imported_attested` | what a knowing party recorded | health-domain, externally originated |
| `corroborated` | a conclusion Groundwork reached | health-domain, **manufactured** |
| `single_weak_signal` | a suspicion Groundwork holds | health-domain, **manufactured** |
| `contradicted` | that we looked, and found against | health-domain, low harm, not zero |
| `not_evaluated` | nothing | none |

### The inversion

**The unresolved states are the most sensitive, not the least.** A verdict-keyed sensitivity
model ranks them lowest — nothing was established, so nothing was created — and gets it exactly
backwards.

A `user_asserted` classification is information the user chose to give and can see and correct. A
`single_weak_signal` classification is information Groundwork **manufactured about them**, which
they cannot correct because they do not know it exists, and which steers what the app will and
will not offer. That is §2b's own "derived fact more sensitive than any source fact had," and it
is the state the intuition protects least.

### The collision with the no-silent-learning boundary

This is the part that stops the classifier being built, and it is not a privacy detail.

> **Settled rule: an unsurfaced observation may never persist.**

A stored `single_weak_signal` health suspicion the user has never seen is exactly an unsurfaced
observation that persists. Three ways out, and only one survives:

- **(a) Persist it silently.** Forbidden by the rule, and by E.2b's reasoning about hidden
  beliefs that steer — worse than ones merely stored, because the harm is invisible at the point
  it occurs.
- **(b) Do not persist; recompute per use.** The boundary holds and the memory does not, so the
  same question gets asked repeatedly. *Repetition is nagging when the software chose it* —
  `ASSISTANT_SCOPE.md`'s standing-conditions principle, and this is the software choosing it.
- **(c) Persist only once surfaced.** A suspicion becomes durable when the user has had the
  chance to see it. **This is the answer**, and resolution 1 below is what makes it cheap.

(c) is not a new mechanism. Establishing axis 2 requires `user_asserted`, and the design already
has the instrument: the **direct question for a missing fact, never for a commitment** — *"was
this a prescription?"*, never *"would you cut this."* The classifier's only honest escalation
path is the one the assistant scope already defined.

The cost looked prohibitive until the gauntlet was actually run against it. It is not — see
**resolution 1**, which is also where "surfaced" gets its definition.

---

## The fail-closed boundary, made mechanical

§2b says the burden changes once the system recognises a derived value *could cross into a
protected domain*. That needs a trigger a test can evaluate:

```text
no signal on either axis
    → outside the boundary
    → ordinary finance data, ordinary lever eligibility

any health-domain signal on either axis
    → inside the boundary
    → not offered as a lever; not propagated to narrator, export or backup
      without an explicit policy decision

inside the boundary, axis 2 established
    → the tax consumer may read it, and only it
```

Which is P0-1's table with a mechanical entry condition: **the boundary is entered by the
existence of a signal, not by the strength of one.** Strength decides what may be concluded
inside it; existence decides whether you are inside.

This is what keeps fail-closed from being global. A user with no healthcare data has no
health-domain signals, is never inside the boundary, and §6.1 behaves exactly as it does today —
which was P0-1's stated requirement and the reason *unknown → protected* cannot be the rule.

**The prevalence still has to be measured before release.** P0-1 already requires this; the two
axes make it a specific count rather than a survey: *transactions with an axis-1 signal and
axis-2 `not_evaluated`.* That population is the one that becomes unavailable as a lever and the
one that generates classification prompts, so it sets both how often §6.4's honest-no fires and
how loud the third prompt-kind is. Simulate it against real data before the threshold ships;
this project has twice found the obvious rule to be a coin flip.

---

## What this does to `is_protected` — nothing yet, deliberately

`is_protected` is the axis-1 policy read, with a single weak signal as its evidence and no
classification named in between. It stays.

The floor fix is *necessary, not sufficient*, and it is already versioned at
`NECESSITY_FLOOR_VERSION = '2'`. When the classifier exists it supplies a richer axis-1 evidence
state and `is_protected` becomes one consumer of it rather than the whole path. Restructuring six
working lines ahead of that recreates the fusion somewhere else, which is the mistake the
mitigation was deliberately kept small to avoid.

**The trigger for changing it is the same as the historian's dangling `entry_id`:** the first
consumer that needs the middle layer named. Tax is that consumer.

---

## The pre-registered falsification criterion

Declared before the fixture is satisfied, because a model that half-works exerts a strong pull to
be kept and the argument then runs on attachment rather than evidence.

> **The two-axis model fails if a legitimate consumer needs a claim that is neither about the
> counterparty nor about the content** — or **if any axis-1-only classification can establish a
> tax-qualifying amount** that a reasonable person would accept.

The first would mean the decomposition is incomplete; the second would mean the wall between the
axes is not real, and the whole separation collapses back to one classification with two
thresholds.

---

## The four items, resolved 2026-09-07

Three of them turned out to be **Gated rather than Open** — the standard already existed and
needed pinning to this case. That is the same shape the clarification-budget question took on
2026-09-03, and it is worth noticing that the pattern repeats: what looks like new governance is
usually Appendix A applied to a case it was never written against.

### Resolution 1 — it is Passive, and per transaction it never promotes

**The earlier claim that this is a third unbudgeted prompt-kind was wrong.** It was made without
running A.2's gauntlet against it, and the gauntlet rejects it at the first gate:

- **A.2.1 Materiality.** A $41 pharmacy charge is not two weeks of debt-free date, not 5% of a
  monthly budget, and crosses no goal boundary. A classification question about one transaction
  fails materiality outright and will essentially always fail it.
- **A.2.2 Actionability.** The gate exists so bad news never arrives without a path. This is not
  bad news; there is nothing wrong and no §6 solution to offer, because the app is asking for
  information rather than reporting a problem.

And A.1's consequence applies unchanged: **strictness is free.** A sub-threshold insight is not
lost, it stays Passive. So the classification question lives **on the transaction row, where the
user meets it** — an unresolved marker inviting designation — and never interrupts. There is no
stream of prompts, because there is no promotion.

**One proactive form can clear the gauntlet honestly, and only one.** Aggregated and seasonal:
*there are 43 transactions I could not evaluate for your medical total.* Material, because it
moves a deduction. Actionable, because reviewing them is the path. Perishable in A.3's strict
sense — a filing deadline is a window closing by a known amount, not a predicted trajectory. It
**draws the brake budget** under the existing standing rule (*a new prompt-kind joins the budget
its attention cost resembles; it does not mint its own*) and competes on the ordinary ruler.

The starvation worry goes with it. Per-transaction candidates never reach contention, so they
cannot crowd out a real brake.

### Resolution 1b — Passive is what satisfies the no-silent-learning boundary

A.1's Passive tier is *visible where the user meets it, no prompt, no budget draw.* The
self-changing-settings decision of 2026-09-03 broke the identical false binary with the identical
move: a change can be made without asking and still not be silent. **Third use.**

> A suspicion rendered on the transaction row is surfaced, and may persist from that moment —
> not from the answer.

Recorded honestly, because it will be discovered otherwise: the standard is **availability, not
confirmation of attention.** A user who never scrolls to that row never sees the marker. That is
the same standard already accepted for passively-surfaced settings changes, and accepting it here
is consistent rather than new.

### Resolution 2 — the marker asks about the transaction, never about a person

§1.7 already states the position plainly: **names are labels, not access control**, anyone who
opens Groundwork sees every person's data, this design does not solve that, and the interface
should say so. Per-account visibility (settled 2026-08-13) governs which *account's* data is in
view; it says nothing about which household member's health is.

What the classifier changes is real and worth naming: for the first time the app would
**originate** health-adjacent content on a shared screen, rather than display what a household
member chose to enter. The containment is structural — a bank transaction has no person. Person
attachment belongs to medications, bills, devices and plan-year state, and it only ever comes
from the user.

> **The classification marker is about the transaction. It must not name, suggest, or default a
> person — even where history would support a guess.**

Guessing the person compounds the manufactured-fact failure at its worst point: inferring *which
household member is ill* is the most disclosive thing this module could do, and it would be
inferred rather than told. Checkable, and in the fixture.

### Resolution 3 — different policy, and the difference is directional

Boundary transitions are asymmetric, for the reason `is_protected`'s docstring already accepts —
applied to the transition instead of the match:

```text
enter the boundary   on any supporting signal
leave the boundary   only on knowing-party evidence (user_asserted / imported_attested)
```

| State | Boundary | Re-entry |
|---|---|---|
| `not_evaluated` | outside | on any signal |
| `contradicted` | outside | **only on knowing-party evidence** |

**`contradicted` is sticky.** If a merchant rule could drag it back in, the user answers *no, it
was a birthday card* and is asked again next month — nagging, and A.2.3 and A.4 both forbid
re-running what the user has already resolved.

And the tax report distinguishes them **in the user's view**. Both qualify $0.00; only one was
looked at. *43 unevaluated* and *43 reviewed, none qualifying* are different claims about
completeness, and a total that cannot tell them apart is overstating what it checked. That is the
second consumer, and it arrives immediately rather than hypothetically — which is what turns
position 1 from a precaution into a requirement.

### Resolution 4 — no sub-kinds, and the reason is not "no consumer yet"

The only candidate consumer is the sensitivity layer: a therapist's office is more disclosive
than a pharmacy, so it might warrant tighter handling on a shared screen or in an export.

Serving that would require Groundwork to hold **a ranking of how disclosive a kind of care is** —
the application asserting whose condition is more embarrassing. It must not. It is also the
confidence float in different clothes: a graded judgement, invented rather than measured, that
something will inevitably threshold.

**So the health domain is handled uniformly, at its most protective level.** The necessity floor
already works this way — it names mental health explicitly to guarantee it is *included*, not to
rank it above dental.

The escape hatch, if a real need appears: the distinction comes from **the user setting it**,
never from Groundwork's ranking. That is consistent with declarations being sovereign, and with
nothing being editable that is not first a claim with a receipt.

## Still open

Two, and neither blocks the classifier:

- **The prevalence measurement**, already required by P0-1 and now a specific count: transactions
  with an axis-1 signal and axis-2 `not_evaluated`. It sets how often §6.4's honest-no fires and
  how large the seasonal review offer gets.
- **The interface statement §1.7 already owes** — that anyone who opens Groundwork sees every
  person's data. Not created by this work, but the classifier is what makes it urgent, because it
  is the first thing that puts app-originated health content on a shared screen. Product copy,
  not architecture.

## The fixture that decides it

`tests/test_classification_fixture.py`, written before any classifier and currently failing.
One CVS transaction, one that the user designates, one auto-categorised with the same name, one
split charge where protection and tax must reach different answers on the same row, and the
derived-fact escape where a sentence with no medical word in it is still health information.

The four resolutions are asserted there too, so they cannot quietly decay into preferences: the
marker is Passive and draws no budget, persistence follows the render, no person is named,
`contradicted` survives a weak re-entry attempt and counts as evaluated, and neither the axis nor
the sensitivity carries a gradient.

If a classifier can carry evidence → axis → sensitivity → policy without a stored boolean, a
confidence float, or a suspicion the user has never seen, it gets built. If it cannot, that is
demonstrated in code rather than argued here.

### It got built — `core/classification.py`, 2026-09-07

56 assertions pass, and **12 of 12 mutations are detected**: breaking the wall between the axes,
entering the boundary by strength instead of existence, letting a merchant rule overturn a
`contradicted` state, ignoring category provenance, keying sensitivity on the verdict,
persisting before surfacing, promoting the per-transaction ask, overwriting a determination,
counting `contradicted` as unevaluated, manufacturing a definitive total, guessing a person, and
handing the narrator the underlying records. Each is caught by the check that names it, so the
invariants are enforced rather than merely asserted.

**Two things the implementation changed, and both were fixture defects rather than model
concessions.** The `UNAVAILABLE` sentinel was local to the test, where a bare `object()` can
never compare identical to anything a model returns — an assertion that could only ever *fail*,
which is the mirror image of the failure mode this project keeps finding. It moved into the
module. And `category_delta` took no records, so a module that does not read the ledger could
not have computed it; the caller now supplies them, which is the division of labour
`core/solution.py` already uses. Neither weakened an assertion, and both are named here rather
than quietly fixed, because a specification edited during implementation is exactly the pull the
write-the-fixture-first discipline exists to resist.

> `tests/test_lifecycle_fixture.py` has the identical sentinel defect in its `UNRESOLVED`, and
> it is left alone — it is a committed specification for a different model, and changing it is
> a decision about that model, not this one.

One thing the module tightened that the document did not anticipate. **Axis-1 over-inclusion is
no longer free.** The necessity floor can afford a loose match because a near-miss costs one
lever; this classifier cannot, because a near-miss also *manufactures a health suspicion about
an ordinary transaction*, and by position 3 that is the most sensitive thing the system holds.
So the merchant vocabulary is deliberately narrower than the floor's — `healthcare`, never bare
`health`, which would take OhioHealth and a health club with the same shrug.
