# Legal boundaries — what this software may do, and what it may say

**A research note for GW 2.0**

> Status: **Research, not advice.** Written 2026-09-06 while designing the healthcare module,
> because that module walks into more regulated territory than the rest of the product
> combined. Companion to `HEALTHCARE_MODULE_DESIGN.md`, whose §0.3 came out of this work.
>
> **This note is not legal advice and was not written by a lawyer.** It is a survey of what the
> published rules appear to say, done carefully enough to design against and not carefully
> enough to rely on. Every section that touches a shipping decision should be reviewed by a
> lawyer before that decision ships. Where the survey was uncertain, the design takes the
> conservative branch, which is why several sections end with a feature being dropped rather
> than qualified.

---

## The two tests

A feature has to pass both, in order, and the order matters.

1. **May we?** Is it permitted, and does doing it pull the product into a regulatory regime it
   is not built for?
2. **Can we say it honestly, without judgement?** Legality is a floor. A sentence can be
   perfectly lawful and still shame someone, and this platform has spent its whole design
   avoiding exactly that.

The second test is the one this project is already good at. The first is newer, and the
finding that runs through everything below is that **the answers are mostly architectural
rather than textual** — what the software *is* decides more than what it *says*. A disclaimer
is the weakest available form of compliance. Not holding the data is the strongest.

---

## §1 Practice of law

**The rule.** General legal information, even structured and practical, is not the practice of
law. Applying the law to the facts of a particular situation to reach a conclusion is.
*Quicken Family Lawyer* was held to be practising law because it questioned the user and then
recommended a specific outcome; the settled industry formulation, in LegalZoom's own
disclaimer, is "does not draw legal conclusions, provide legal advice, or apply the law to the
facts of a particular situation."

**May we?** Publish general information — yes. Compute whether *this* debt is enforceable — no.

**Where it bites.** The statute-of-limitations gate. Taking a first-delinquency date and a
state, applying a limitation period and concluding "your debt may be time-barred" is the
textbook wrong side of that line. The CFPB itself publishes the general rule and then tells
consumers to see a lawyer; a personal finance app has no standing the regulator lacks.

**Settled in the design** as §0.3: general fact unattached, a referral to who answers it, and
arithmetic on the user's own money. No state-law tables — they rot, and stale legal data is
worse than none.

**The honesty test, and where it argues back.** Saying nothing would also be lawful, and it
would be worse. Having built a payment calculator and knowing a payment can revive a dead
debt, silence is a failure of the second test even while passing the first. The published
general fact, unattached to their account, is the point where both tests pass — which is a
good demonstration that running them together produces a better answer than either alone.

---

## §2 Health data privacy — the largest exposure, and the one already solved

**HIPAA does not apply.** Its obligations attach to covered entities — health plans,
clearinghouses, and providers transmitting electronically — and to their business associates.
A personal finance application holding a user's own records is none of those. This is worth
stating precisely because it is so often assumed either way.

**What does apply is newer and broader.** Washington's **My Health My Data Act** (RCW 19.373,
in force since March 2024) was written specifically for the health data that falls *outside*
HIPAA. It reaches apps, platforms and websites; it applies to any regulated entity that
collects, processes, shares or sells consumer health data and either does business in
Washington **or offers products targeted at Washington residents** — which a nationally sold
desktop app does. Consumer health data is defined broadly and includes inferences.

**And it has teeth almost no other privacy statute has:** a private right of action, with
presumptions favouring plaintiffs, and violations treated as per se Consumer Protection Act
violations. Most privacy laws are enforced by an attorney general with limited appetite. This
one can be enforced by anyone.

**The finding that matters.** These obligations attach to entities that *collect or process*
consumer health data. **Groundwork's local-first architecture means it does neither.** The
medication list lives on the user's machine; the vendor never receives it, cannot produce it,
and could not sell it if it wanted to. The design decision already made for ethical reasons
turns out to be the compliance strategy, and it is far stronger than any consent flow.

**Which makes §3 of the design document a legal boundary and not only an ethical one.** Every
proposed outbound flow is the point where this changes:

| Proposed flow | Effect |
|---|---|
| Drug price lookup to a third party | Sends medication names off-device. Likely makes the vendor a processor of consumer health data. |
| Cloud LLM narrating health content | Same, and worse — free text with more inference in it. |
| Telemetry or crash logs containing health rows | Same, with none of the user benefit. |
| Blue Button 2.0 claims import | Patient-directed and OAuth-authorised, but the data still lands somewhere; local-only storage keeps it out of scope. |

**Design consequence.** The existing rule — health data never leaves the machine by default,
and the cloud provider is refused for health content even when selected — is not a
nice-to-have. It is what keeps the product outside a statute with a private right of action.
Any feature that breaches it needs a lawyer before it needs an engineer.

**Also worth noting:** California's CMIA and a growing set of state consumer health data laws
point the same way. The architectural answer covers all of them at once; a per-state consent
flow would not.

---

## §3 Debt relief services

**The rule.** The FTC's Telemarketing Sales Rule defines a *debt relief service* as a program
claiming, directly or by implication, that it can renegotiate, settle or otherwise change the
terms of someone's debt to an unsecured creditor or collector. It carries an advance-fee ban
and prohibits misrepresenting savings, timeframes, or effects on creditworthiness. It targets
for-profit operations, and the FTC and states both enforce it.

**May we?** Yes — as long as the product is not that. The definition turns on **what is
claimed**, which means the exposure lives in the marketing as much as in the code.

**The design rule** (design doc §8.5): a calculator and a record. Never an intermediary, never
a negotiator, never a claimant of outcomes. The app does not contact anyone, does not act on
the user's behalf, does not charge for a result, and does not state what a creditor will
accept.

**The sentence this product does not get to say:** *"Settle your medical debt for less."*

**State licensing is the second half.** Many states license "debt adjusters" or "debt
management services" on definitions broader than the federal one, generally reaching anyone
who, for compensation, acts as an intermediary between a debtor and creditors. Groundwork is
not an intermediary — the user makes every contact themselves — which is the distinction that
keeps it clear. **This one is worth a lawyer's read before the collections feature ships**,
because state definitions vary and some are drawn loosely.

---

## §4 Credit repair

**The rule.** The Credit Repair Organizations Act reaches anyone who, for a fee, represents
that they will improve a consumer's credit record, rating or score, or remove negative items.
It bans advance fees and imposes contract and disclosure requirements. It applies to apps and
digital platforms on the same terms as anyone else. The non-profit exemption is narrow and
does not save an entity that charges fees for credit improvement.

**May we?** Yes, trivially — **because the trigger is a claim we never make.** Groundwork
charges for software but has never represented that it improves anyone's credit.

**The design rule.** No credit-improvement claim, anywhere, in the product or its marketing.
This is easy to honour and easy to breach accidentally: "clear this and watch your score
recover" is a CROA trigger written by a copywriter in a hurry.

**Which is why the design document already refuses to state credit outcomes at all** — the
CFPB medical-debt rule was vacated in July 2025, what remains is voluntary bureau policy that
can be withdrawn, and "this will not affect your credit" was already forbidden as simply
untrue. The legal answer and the honesty answer arrive at the same place from different
directions.

---

## §5 Tax

**The rule.** Preparing and signing returns for compensation is regulated and requires a PTIN.
Software that helps a taxpayer organise their own figures is not that, and has not been since
consumer tax software existed.

**May we?** Yes. The year-in-review report totals the user's own records against a published
threshold. That is arithmetic and organisation, not preparation.

**Where the risk actually is, and it is not licensing.** It is being **wrong**. §213's 7.5%
AGI floor is easy; the exclusions are not. Anything reimbursed, or paid from an HSA, FSA or
HRA, must come out, and a report that quietly includes HSA-paid expenses hands someone a
number that is too high and contributes to a bad filing. **The legal exposure here is
ordinary: produce a wrong number, cause a wrong return.**

**The design rule.** Show the total, show every exclusion made and why, state the threshold and
whether the total clears it, and say plainly that the preparer decides. Never imply an outcome.

---

## §6 Medical and clinical advice

**The rule.** Diagnosing, recommending treatment, or advising on medication is practising
medicine or pharmacy. Software that does it is in the same position as a person who does.

**May we?** Nothing in this module goes near it, and nothing should.

**The design rules already written.** Never suggest changing, substituting or stopping a
medication — only the price of the same prescription. Never let a model generate a clinical or
causal claim about health; the visit report is templated for exactly this reason, and
`MODEL_PLACEMENT.md` measured inference-smuggling at 37–70% across every model tested, rising
with size. The visit report carries costs, never symptoms or conditions.

**The line to hold:** *"the same prescription is cheaper at another pharmacy"* is a price fact.
*"a cheaper drug would work as well"* is medicine, and is never said.

---

## §7 Drug pricing data

**Not a statute — a licence.** GoodRx's API is partnership-gated, and what may be displayed,
cached or retained is contractual rather than legal. NADAC is public but is the wholesale
acquisition cost, so presenting it as a patient price would be a misrepresentation regardless
of licensing. RxNorm is public domain and safe for naming and normalisation.

**May we?** Only on the terms agreed, and the terms are the constraint.

**Which strengthens the design's existing recommendation** to use the user's own recorded
prices first: no licence, no partner, no outbound medication names, and — per §2 — no
statutory exposure either. **The privacy answer, the legal answer and the honesty answer all
point at the same feature**, which is usually a sign it is the right one.

---

## §8 Debt collection

**The rule.** The FDCPA regulates *collectors*. Groundwork is the consumer's own tool and is
not one, so it has no obligations under it.

**What the user has, which is different.** Rights: validation, restrictions on contact, and
the protections around them. Those are the user's to exercise.

**May we tell them?** General information — yes, and it is published by the CFPB in plain
language. What is refused is the same thing §1 refuses: applying it to their account and
concluding what their position is.

---

## §9 The second test: honest, and without judgement

Everything above establishes what is permitted. The rest of the design is about what is
decent, and it is the harder standard.

Three sentences that are all perfectly lawful:

> *"You have $4,000 in collections."*
> *"You let this go to collections."*
> *"Your prescriptions cost you four months of freedom."*

The first is a fact. The second is the same fact with a verdict attached. The third is the one
the design document spent §0.1 ruling out — arithmetically true and functionally an
accusation. **No regulator would object to any of them.** The difference between them is the
whole product.

The rules that fall out of the second test are already written across the design document, and
they are stricter than the law in every case:

- Blame belongs to a decision, and needing medicine is not one (§0.1).
- A healthcare cost is never called a debt, and layout says it as loudly as words (§0.2).
- An honest null beats an invented figure, especially one a person will repeat out loud (§7.3).
- A stated preference is honoured; a preference inferred from silence is not learned (§7.7).
- Legal exposure is surfaced beside a ranking, never baked into a rate where it cannot be seen
  (§8.6).

**The relationship between the tests.** The law says what would get the product in trouble. The
voice rules say what would make it a thing not worth building. Where they disagree, the voice
rules are stricter, and in this module they have been stricter every single time — which is
the reassuring result, because it means compliance is a by-product of the standard already
being kept rather than a new constraint fighting it.

---

## §10 What still needs a lawyer

Named plainly, because a research note is not a substitute for one.

1. **State debt-adjuster and debt-management licensing** (§3), before anything in the
   collections feature ships. Definitions vary by state and some are drawn loosely enough to
   catch tools that are not intermediaries.
2. **My Health My Data and its siblings** (§2), before *any* health data leaves the machine.
   The local-first answer is strong, and the moment it is breached the analysis changes
   entirely — including the private right of action.
3. **The marketing copy**, against both the TSR (§3) and CROA (§4). Both regimes turn on what
   is claimed, and both are far more likely to be breached by a landing page than by the
   engine.
4. **The tax report's exclusion logic** (§5), reviewed by someone who prepares returns —
   less for liability than for correctness, which is where the real harm is.
5. **Whether §0.3's line is drawn in the right place.** This note concludes the app may state
   general legal information and refer onward. That conclusion is itself a legal judgement,
   made by people who are not lawyers, about the boundary of the practice of law. It is exactly
   the sort of thing to be wrong about confidently.
