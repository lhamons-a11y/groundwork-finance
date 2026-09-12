# Where health sensitivity actually goes — one fact, traced through every layer that exists

**Gap 11, kept empirical: a health-sensitive fact followed from source to the last layer built,
with its state named at each.**

> Status: **Case set, 2026-09-11. No health-aware renderer, no new field, no abstraction. The
> decision is Rob's.**
>
> `HEALTHCARE_GAP_TRIAGE.md` gap 11: *the mechanism exists — sensitivity propagates through
> narrator, export and backup, and derived facts inherit it. What is untested is reconstruction.*
>
> Rob's discipline for it: don't assume the marking exists only at ingestion. Trace the fact —
> `source → stored fact → derived fact → generic representation → surface → consumer` — because
> the interesting loss may be in the middle. And name each layer's state as one of four:
> **explicitly preserved · explicitly absent · accidentally inferable · genuinely
> unrecoverable.** Only then decide whether there is a gap.
>
> **The fact followed:** a CVS pharmacy transaction the importer filed under *Other*. No user
> statement, no EOB — the classifier marks it health from the merchant and MCC, and marks that
> marking `manufactured`, which its own docstring calls *the most sensitive thing the system
> holds*: a suspicion about a person that nobody asserted.

---

## The trace

| Layer | Object | domain | manufactured | State |
|---|---|---|---|---|
| **1** source → stored fact | `Classification` | `health` | `True` | **explicitly preserved** |
| **2** stored → derived | `DerivedFact` (`category_delta:Other`) | `health` | `True` | **explicitly preserved** — and the docstring says why: *"spending increased 20%" contains no medical word and is still health information* |
| **3a** derived → narrator | `NarratorFacts` | **no field** | **no field** | **explicitly absent** |
| **3b** derived → export | `export_row` | `'health'` | **no field** | **preserved, partially** — the domain travels; the fact that nobody asserted it does not |
| **3c** derived → backup | `backup_row` | same as export | same | same |
| **4** surface | — | | | **not built** (gap 9) |
| **5** consumer | — | | | **not built** |

**The trace ends at layer 3, and so does the sensitivity.** `NarratorFacts` is:

```python
metric: str · value: object · includes_records: bool · resolution: object
```

Its contract — *what the narrator is allowed to see, never the underlying records* — is about
not leaking rows. It was never about carrying what kind of information the figure is, and it
does not. **The generic representation is lossy by contract**, which is the finding Rob said to
look for rather than *the renderer lost it*. There is no renderer.

---

## The four states, each with its case

### Explicitly preserved — layers 1 and 2

`sensitivity(c)` attaches the domain on any evidence bearing on a health claim, including
evidence against; `DerivedFact` carries `Sensitivity(domain, manufactured)` forward and
`category_delta` folds `manufactured` as *any source manufactured*. Asserted in
`test_classification_fixture.py`. Working.

### Genuinely unrecoverable — the adversarial case, at the narrator

Two CVS transactions under *Other*, both `manufactured` health. The delta is `corroborated`, so
the narrator is **permitted** to receive it:

```text
DerivedFact     strength=corroborated   domain=health   manufactured=True
NarratorFacts   metric='category_delta:Other'   value=180.0
```

**The number is exactly right. Nothing the narrator holds can determine that a health-suspicious
transaction is inside it.** *Other* is not a health word; there is no field; the value is a
float. A surface built on `NarratorFacts` alone would be **completely accurate and unable to
know it was handling the most sensitive thing the system holds** — which is the case Rob named
as the one he most wanted, and it exists at the first representation the narrator sees.

### Accidentally inferable — the metric name

A user-categorised *Prescriptions* transaction. The narrator receives:

```text
metric='category_delta:Prescriptions'
```

A human reads *Prescriptions* and infers health. The representation carries no sensitivity
field; the inference rides on a category string that happens to be embedded in the metric name.
**It is not marking. It is a coincidence of naming**, and the reverse case shows why that
matters.

### The reverse — wording invites inference, the record has none

A hardware-store purchase with a memo *wheelchair ramp lumber*. The classifier reads merchant,
MCC and category; it does not read memos. Both axes `not_evaluated`. The narrator receives
`category_delta:Home` and nothing else. **The record has no health relationship, and that is
correct** — the purchase may be for a neighbour, a job, a stage set.

The temptation this case exists to name: a narrator that *does* read memos — and the client
narrator is a language model handed whatever facts the surface gives it — would infer health
from *wheelchair* and could **say** it. That would be manufacturing sensitivity from language:
principle 1's inference-without-evidence, and the value-disagreement finding's *evidence carries
one boolean about one fixed proposition* turned into a fourth path in. **Absence here is the
truthful state, and it must stay absent.** The record is right; only a consumer could get it
wrong.

### Explicitly absent — and the fixture describes the property it does not assert

`test_classification_fixture.py`, in the section headed *derived facts: health context survives
transformation*, asserts:

```text
sensitivity(delta).domain == 'health'              ✓ asserted
export_row(delta)['sensitivity'] == 'health'       ✓ asserted
backup_row(delta)['sensitivity'] == 'health'       ✓ asserted
narrator_facts(delta).includes_records is False    ✓ asserted — a DIFFERENT property
```

There is **no assertion** that the narrator's representation carries sensitivity. And the
fixture's own `describe()` prints, as part of its specification:

> *derived figures inherit sensitivity through narrator, export, backup*

**The spec printout claims the property; the assertions cover two of the three consumers; the
code satisfies exactly those two.** Gap 4's shape a fourth time — a fixture that describes more
than it checks — and the triage's *the mechanism exists and propagates through narrator* was
written from the printout. It should have been written from the assertions.

---

## Where the loss is, and what kind

**Layer 3a. Before any surface. A projection gap** — Q2's class exactly: the information exists
one layer up, correctly, and the representation handed to the consumer drops it. Not a
representation gap (the record holds it), not upstream absence (it is there), not an operation
gap. **The same class Q2 was, and Q2's fix shape — carry it beside the value, never inside the
strength — is the shape this would take.** Not built here.

And a second, quieter loss at 3b: **export carries the domain and drops `manufactured`.** An
export file can say a figure is health-related and cannot say whether a person asserted that or
the system suspected it from a merchant name. The classifier ranks those as the least and most
sensitive things it holds, respectively, and the export makes them one.

---

## For the register, below the line

**A narrator built on `NarratorFacts` as it stands would narrate manufactured health suspicion
with no way to know it was doing so.** Plausible, coherent, accurate to the dollar. Unreachable:
`core.classification` has no consumer, and no surface exists. So it sits with the
trigger-dependent entries, with the wiring condition: **the first narrator consumer must not be
able to receive a health-domain derived fact without the domain and `manufactured` beside it.**

---

## Is there a gap?

**Yes, and it is narrower than gap 11 suspected.** The question was whether a health situation
could be *reconstructed* from unmarked surfaces. The trace shows the unmarked surface does not
have to be reconstructed from — it is **handed** to the narrator unmarked, at the module's own
boundary, by a representation whose contract never included the marking. The concern about
reconstruction is downstream of a loss that happens first.

**No gap in the reverse direction.** The record correctly refuses to manufacture sensitivity from
wording, and the only way to break that is a consumer that reads text the record does not.

**The finding, in one sentence (Rob's):**

> **Sensitivity is preserved through classification and derivation but projected away at the
> narrator boundary.**

**Nothing to decide about renderers.** The two losses are both in `core/classification.py`'s
consumer helpers, and both are the projection class. **What is Rob's, and they are three
different kinds of question:**

1. whether `NarratorFacts` carries `Sensitivity` beside its value, as `resolution` now does —
   a **representation** decision;
2. whether export carries `manufactured` — another representation decision, *if export actually
   needs that distinction*;
3. whether a manufactured suspicion may ever be **voiced** by the narrator — the policy boundary,
   and the genuinely interesting one.

**#3 does not follow from #1.** Carrying the distinction does not mean the narrator is permitted
to say it. The two questions stay apart because the architecture keeps them apart:

```text
representation   what do we know?
permission       what may this layer say?
```

**And a note on what `includes_records = False` is doing.** It is the reason the narrator
*cannot* reconstruct what its contract excludes: it does not secretly hold the underlying
evidence. That assertion is doing real work — it is the reason the loss at layer 3 is a clean
loss rather than a leak by another route.

**The symmetry with the reconstruction experiment**, worth noticing and not building on: the
economic model was found unable to preserve two independent historical dimensions at once; the
teaching pipeline was found able to preserve a sensitive distinction perfectly and then
discarding it at a contract boundary. **Neither result says what the architecture should be.**
