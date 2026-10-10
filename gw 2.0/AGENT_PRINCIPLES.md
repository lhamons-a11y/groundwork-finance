# Item 65 — Groundwork's Capabilities, Boundaries, and Reliability Standard

Opened 2026-10-09. Rob: *"what is your feeling? I am new to having software with this much capability, where is it
too much and where we are leaving too much to waste. I'll let you write those rules and then I will approve or
disapprove."*

**Ruling record (Rob, 2026-10-09):**
- **First ruling** ("I accept item 66 as a whole and item 65"): AP1–AP11 accepted as the governing standard,
  TM1–TM8 as prohibitions. W1–W10 a menu, none opened.
- **Second ruling** ("approve H1–H6 and S1–S7 as the next ruling, while leaving W1–W10 unopened"): **RG1–RG6 accepted
  as reliability guardrails and S1–S7 as their implementation expectations.** Rob supplied this document's present
  text with that ruling; it replaces the first version (in git history at 9cb29e6), keeping AP1–AP11 and TM1–TM8 as
  accepted.
- W1–W10 remain an unopened menu. Goal-directed planning and adverse-scenario analysis (Part 6) is a possible future
  item, not opened.
- **No code is authorised by this item.** Each new feature is opened and scoped under the established process.

*Naming:* the reliability guardrails are **RG1–RG6** (Rob, 2026-10-09: renamed from H1–H6 so they can't be confused
with item 45's own H1–H7; the ruling is unchanged). Where this document means one of item 45's, it says "item 45's H6".

## Purpose

Determine what Groundwork should do with its capabilities, what it must never do, where it is leaving useful
capabilities on the table, and what technical safeguards are required to ensure that its conclusions are reliable.

Groundwork is a financial coach, not merely a record keeper, calculator, or conversational assistant. It should
discover what the financial record reveals, anticipate what may happen, explain why it matters, and help the person
understand the consequences of their choices.

The person remains the authority over their own financial life.

**Governing principle:** Groundwork should do as much analytical work as the evidence permits, explain the limits of
what it knows, and leave consequential choices with the person.

## The short version

**Groundwork learns the money. The person learns the why.**

The engines calculate. Evidence establishes what is known. The model teaches and explains. Validation prevents
unsupported conclusions from becoming trusted claims. The person decides and moves money themselves.

No item in this document independently authorizes implementation. Each new feature must be opened and scoped under
the established development process.

## Part 1 — Accepted Rules: What Groundwork Does

These rules were accepted by Rob on 2026-10-09 and govern every future item.

**AP1. Chores automated; decisions taught; money moved only by the person.**
Groundwork should automate tedious, mechanical work wherever safely possible: importing transactions, matching
charges, reading bills, identifying recurring expenses, reconciling records, and gathering authorized information.

Consequential decisions remain with the person. Groundwork may explain which obligations compete for money, compare
payoff approaches, calculate savings scenarios, and show trade-offs. It does not silently decide which bill to pay,
which debt to prioritize, or how much to save.

Groundwork never pays bills, transfers funds, or otherwise moves money on the person's behalf, even with an
additional confirmation step.

The person should authorize work, not perform the computer's chores.

**AP2. Learn from the financial record, out loud.**
Groundwork may discover patterns supported by the user's financial record, including seasonal spending, recurring
bills, annual obligations, insurance renewals, price changes, and recurring gift or travel expenses.

A discovered pattern must be presented with its supporting evidence and limitations before it influences a budget,
forecast, or plan.

Example: *"Gift spending has averaged approximately $600 in November over the last three years. Would you like to
plan for this expense by setting aside money during the year?"*

The historical pattern, the interpretation of the pattern, the anticipated future event, and the person's chosen plan
are distinct things. Confirming one does not automatically confirm the others.

An unconfirmed interpretation must not become a persistent fact about the person or silently shape a plan. A
confirmed declaration must accurately reflect what the person actually confirmed.

Groundwork may calculate provisional scenarios without treating them as established facts or adopted plans.

**AP3. Never infer the person from how they use the app.**
Clicks, visits, dismissals, time spent, navigation patterns, and feature usage must never create, rank, or imply
willingness, motivation, priorities, emotional state, or personal intent.

A person repeatedly visiting a debt page has not thereby agreed to sacrifice spending. A person ignoring a savings
page has not thereby rejected saving.

Usage telemetry is not evidence of a person's willingness.

This rule governs the dashboard, Historian, Willingness Layer, recommendations, and future AI features.

**AP4. Facts about other people are asked, never inferred.**
Groundwork must not infer personal or family events from financial transactions and present those inferences as
facts.

Birthdays, relationships, a partner's income, a child's school expenses, health events, pregnancy, separation, job
loss, and similar personal circumstances must not be inferred from purchases or spending patterns.

When relevant, Groundwork may ask a neutral question without asserting an unsupported conclusion.

Example: *"Is October 14 a birthday you normally plan for?"*

The question must not imply that Groundwork has established the answer.

**AP5. A pattern must beat chance before it is offered.**
Every pattern detector must be tested against trend-free or appropriate null-model data before release.

A detector that routinely identifies patterns in noise must not ship.

Passing a null-model test is necessary but not sufficient. Detectors must also be tested for false positives, missed
events, robustness, and performance on realistic financial data. A pattern can be statistically detectable without
being practically useful.

The evidence must justify the strength of the conclusion.

**AP6. The engines compute; the model explains.**
All financial figures originate from the appropriate deterministic financial engine or verified source. Every
consequential financial figure must have traceable working under the established transparency standard.

The model may explain findings, introduce relevant concepts, translate questions into structured analyses, identify
missing information, and propose scenarios for the engines to calculate.

The model must never invent financial figures, sources, research, historical facts, or calculated results.

The model may propose an analysis. The engine must establish the result. Validation must check the result. The person
decides what to do with it.

The model's explanations must pass the applicable factuality and voice checks.

**AP7. The person starts every outside action.**
Opening a bank portal, retrieving a statement, reading a price from a website, or accessing an external source must
be initiated by the person.

The operation runs within Groundwork's authorized environment, accesses only the information it was instructed to
access, identifies its source, and presents the result for appropriate confirmation before it becomes trusted
financial information.

Nothing performs unattended or scheduled external financial access.

Once the person authorizes a defined operation, Groundwork may complete the mechanical processing covered by that
authorization without repeatedly asking permission for each internal step.

Authorization to perform a task does not grant broader or continuing permission.

**AP8. Nothing about the user's financial life leaves the computer.**
Groundwork must not transmit personal financial data to third parties. Public economic information may be retrieved
as complete public tables without sending personal financial details as query parameters.

Groundwork must not read email or text messages, bypass a bank's authentication or automation restrictions, or use an
unauthorized route to acquire financial information.

The user must be able to understand what information an operation accesses and where that information comes from.

This is a system-level privacy requirement, not merely a model instruction.

**AP9. When Groundwork cannot tell, it says so.**
Unknown is not zero. Missing is not absent. An estimate is not a verified fact. A forecast is not a promise.

When evidence is insufficient, Groundwork must identify the uncertainty and its practical significance. It must not
silently fill gaps with plausible values or descriptions.

A figure that cannot be responsibly established must be withheld, qualified, or presented as an explicitly
hypothetical scenario.

The absence of enough evidence must not be disguised as confidence.

**AP10. Everything Groundwork does is visible and traceable.**
Automated operations must leave an appropriate, understandable record, including relevant imports, external
retrievals, review decisions, AI-generated explanations, and changes to persistent information.

The person must be able to inspect the evidence behind consequential findings and understand what Groundwork did.

Automated changes must be reversible wherever technically possible. Corrections and superseding decisions must
preserve the history needed to explain consequential prior actions. Undoing a change must not require falsifying the
historical record.

A visible log does not excuse an incorrect action. Transparency and prevention are separate requirements.

**AP11. AI is optional; teaching is the point.**
Every core surface must remain fully functional with AI disabled, consistent with the existing AI-off requirement.

AI may make the same verified financial findings easier to understand by explaining what a figure means, why it
matters, which mechanism produced it, and which question it raises.

AI adds interpretation and teaching, not authority over the financial record.

Disabling AI must not disable essential calculations, evidence access, financial controls, or user decisions.

## Part 2 — Accepted Prohibitions: What Groundwork Must Never Do

These prohibitions were accepted by Rob on 2026-10-09.

**TM1. Never pay bills or move money.** No bill payment, transfer, or other movement of funds on the person's behalf,
even as a one-time convenience and even with a confirmation step.

**TM2. Never perform scheduled or unattended bank access.** No background polling, scheduled retrieval, or
unattended external financial access.

**TM3. Never allocate money silently.** A discovered pattern must not silently alter a budget, financial plan,
savings allocation, or payoff strategy.

**TM4. Never infer willingness or engagement from usage.** No willingness, motivation, priority, or emotional-state
scoring derived from app usage.

**TM5. Never infer life events from purchases.** No assertions or persistent conclusions about personal circumstances
based on indirect financial clues.

**TM6. Never use manipulative persuasion mechanics.** No streak pressure, countdowns, attention-pulling motion,
artificial urgency, coercive reminders, or celebration effects designed to influence behavior. Motion and interaction
design must respect the same non-manipulative voice standard as written language.

**TM7. No health specifics before the required privacy gate.** Health-specific functionality remains blocked until
item 45's H6 privacy gate is satisfied.

**TM8. Never make unsourced research claims.** No "studies show," research findings, statistics, or external claims
without a verifiable source and accurate representation of what that source supports.

## Part 3 — Reliability Guardrails: Preventing Hallucinations

**RG1–RG6 ACCEPTED by Rob, 2026-10-09.** They make the accepted principles technically enforceable across all current
and future AI-enabled features.

Hallucination prevention must not depend solely on the model being instructed to behave correctly. Groundwork must
constrain what the model can assert, provide traceable evidence, validate consequential claims, and fail safely when
validation cannot establish reliability.

**RG1. Every factual claim must have evidence.**
Every factual claim about the user's financial situation, financial history, household circumstances, financial
products, external sources, or calculated outcomes must be traceable to an appropriate source.

Acceptable evidence includes:
- A finding produced by an authorized financial engine.
- A specific transaction, statement, bill, or other verified financial record.
- A verified external source retrieved through an authorized operation.
- An explicit statement or confirmation from the person.
- A properly calculated result based on identified inputs and assumptions.

Evidence references must identify the relevant source or finding. Consequential claims must be traceable to the
underlying records and calculations.

A true number does not automatically validate the explanation attached to it.
- Supported: *"Your insurance premium increased from $120 to $120 per month."*
- Unsupported unless separately established: *"Your insurer raised the premium because of inflation."*

The model must not invent the reason, source, or context behind a verified number.

*Enforcement requirement:* claims without sufficient evidence must be rejected, qualified, or withheld rather than
accepted because they sound plausible.

**RG2. Validate the claim, not merely the number.**
Groundwork must validate the meaning of an AI-generated explanation against the evidence supplied to the model.

Validation must check, as applicable:
- Financial amounts and units.
- Dates, time periods, and comparison periods.
- Source identity and provenance.
- Whether a transaction or obligation is confirmed, pending, estimated, or missing.
- Whether a conclusion exceeds the completeness of the record.
- Whether a correlation has been incorrectly described as causation.
- Whether an estimate or scenario has been presented as a fact or prediction.
- Whether the explanation contradicts the engine's findings.
- Whether the model has introduced new factual claims absent from its evidence.
- Whether uncertainty and limitations have been preserved.

A second language model agreeing with the first is not sufficient validation.

Where practical, consequential claims should be represented in a structured form that permits deterministic checks
against evidence before they are rendered as natural language.

No validation process may be assumed perfect merely because it passes a test suite.

**RG3. The model cannot create financial facts or persistent memory.**
The model may propose a finding for investigation, a question to ask, a possible interpretation, or a scenario to
calculate.

It must not directly establish or modify trusted financial facts, confirmed patterns, user declarations, Willingness
Layer records, or Historian memory through generated prose.

Only the appropriate authorized process may establish the corresponding record, with required validation or explicit
user confirmation.

A model-generated assertion must not become evidence for another model-generated assertion. Derived findings must
preserve their lineage to underlying evidence rather than relying on earlier unverified AI output.

The system must distinguish at least:
1. Recorded facts.
2. Calculated findings.
3. Unconfirmed interpretations.
4. Confirmed user declarations.
5. Forecasts and estimates.
6. Hypothetical scenarios.
7. Unknown or conflicting information.

These categories must not be silently merged.

**RG4. Forecasts and scenarios must expose their assumptions.**
Every consequential forecast, projection, or scenario must distinguish actual records from assumptions and
hypothetical inputs.

The system must identify the relevant time period, important missing information, and material limitations.

Example: *"If heating costs are $500 higher than the amount assumed in this scenario, projected available cash
decreases by $500, all else equal."* Groundwork must not transform this into *"Your heating costs will increase by
$500."*

A forecast must not be described as a worst-case scenario unless the scope and assumptions genuinely support that
characterization.

Where several plausible outcomes exist, Groundwork must not present one scenario as inevitable merely because it is
convenient to explain.

The user must be able to distinguish what has happened, what is expected, what is assumed, and what could happen
under different conditions.

**RG5. Failed validation means no unsupported conclusion.**
If a required claim cannot be traced to evidence, a calculation does not reconcile, a required input is missing, or
an explanation contradicts verified findings, Groundwork must withhold the affected conclusion.

It may instead:
- Present the verified facts without the unsupported interpretation.
- Explain which information is missing.
- Ask the person a neutral clarifying question.
- Present an explicitly labeled hypothetical scenario.
- Report that it cannot establish the answer.

It must not fill the gap with a plausible answer simply to produce a complete or conversational response.

A failure affecting one claim need not suppress unrelated, independently verified findings. Validation should
isolate unsupported claims wherever technically possible.

If a core calculation or source is unreliable, the system must withhold any dependent conclusions.

The system must never claim validation succeeded when validation failed, was skipped, or could not be completed.

**RG6. Test reliability through deliberate adversarial testing.**
Every AI-enabled feature must have tests for both correct answers and appropriate refusal or qualification.

The test suite must include, as applicable:
- Fabricated transactions, amounts, sources, and financial facts.
- Missing or incomplete transaction histories.
- Conflicting account records.
- Duplicate transactions and reconciliation failures.
- Stale prices, statements, and financial data.
- Misleading premises in user questions.
- Unsupported explanations of why an event occurred.
- Correlation incorrectly presented as causation.
- Forecasts presented as guaranteed outcomes.
- Hypothetical assumptions presented as actual records.
- Model-generated facts attempting to enter persistent memory.
- Contradictions between model output and engine findings.
- Unsupported research claims.
- Prompt injection or hostile instructions embedded in imported documents or external content.
- Validation failures and unavailable dependencies.

Tests must verify that unsupported claims do not reach trusted outputs, persistent memory, or consequential decision
surfaces. Pattern detectors must additionally satisfy AP5's null-model and realistic-data requirements.

Voice checks, successful model responses, and ordinary happy-path tests do not establish factual reliability.

*Release requirement:* an AI-enabled feature must not ship solely because it performs well on ordinary examples. It
must demonstrate that the system reliably preserves evidence boundaries and fails safely when evidence is
insufficient.

## Part 4 — System-Level Safeguards

**S1–S7 ACCEPTED by Rob, 2026-10-09**, as the implementation expectations that make RG1–RG6 actionable.

**S1. Use a constrained evidence package.** The financial engine should provide the explanation layer with a
structured package containing the relevant findings, source references, values, units, dates, assumptions,
confidence or uncertainty indicators, and known limitations. The model should not need to reconstruct the financial
record from conversational context or invent missing context. The evidence package is the permitted factual basis for
the explanation.

**S2. Separate generation from authorization.** Generating a proposed explanation, scenario, pattern, or action must
not authorize that result to become a trusted record or change a financial plan. The system must maintain explicit
boundaries between proposing, calculating, validating, confirming, persisting, and executing. No model output should
bypass the appropriate gate merely because it appears reasonable.

**S3. Treat imported and external content as untrusted data.** Statements, PDFs, web pages, and other imported
content may contain inaccurate information or instructions designed to influence an AI system. Such content is
evidence to evaluate, not authority to override Groundwork's rules. The model must not follow instructions embedded in
imported content that attempt to alter its role, expose private data, bypass authorization, or change system
behavior.

**S4. Preserve provenance and uncertainty through every stage.** When a finding moves from the financial engine to the
explanation layer, validation gate, dashboard, report, or persistent record, its evidence references and uncertainty
must not disappear. A verified input combined with an unknown input does not automatically produce a verified
conclusion. Every downstream representation must preserve the distinctions needed to interpret the result correctly.

**S5. Make validation failures observable.** Validation failures must be recorded in an appropriate diagnostic or
audit mechanism without unnecessarily exposing sensitive financial information. The record should distinguish an
unsupported claim, a calculation failure, a missing source, a contradiction, and a validation service failure where
those distinctions can be established. Failure records must not be treated as proof that a financial claim is false;
they establish that the claim was not sufficiently validated.

**S6. Keep the system safe with AI disabled or unavailable.** Core financial calculations, data integrity, privacy
controls, and user authority must not depend on the language model. If the model fails, the application loses access
to a required component, or validation cannot complete, Groundwork should retain its verified non-AI functionality
and withhold affected AI conclusions.

**S7. Do not promise zero hallucinations.** The system must be designed to prevent unsupported output from becoming
trusted financial information, not to claim that hallucinations are impossible. Reliability must be established
through architectural constraints, traceable evidence, deterministic checks where possible, adversarial testing, and
continued monitoring of failure modes.

## Part 5 — The Capability Menu: Where Groundwork Should Do More

W1–W10 are an **unopened menu** (Rob, 2026-10-09, twice). None is authorized for implementation by this document. Each
requires Rob to open and scope it separately. The following order is a proposed investigation priority, not a
binding build sequence.

**W1. Patterns from the first import.** Use a substantial initial transaction history, where available, to identify
seasonal spending, annual bills, insurance renewals, and recurring gift or travel periods. Test patterns against
trend-free and realistic data. Show the supporting records, uncertainty, and relevant limitations. Ask the person to
confirm interpretations before they influence a plan. Do not assume every household has sufficient history or that a
pattern will recur.

**W2. Price changes on recurring bills.** Identify verified changes in recurring charges. Example: *"Your streaming
bill increased from $15.49 to $17.99 in August."* Show the old and new amounts, dates, and sources. Distinguish a
price change from a change caused by usage, taxes, fees, or billing frequency when the evidence allows. Do not invent
the reason for a change.

**W3. An upcoming calendar from the record.** Present known due dates, recurring obligations, renewals, annual fees,
confirmed birthdays, and identified future charges. Distinguish confirmed dates from estimated recurrence dates and
possible future events. Do not infer personal events from purchases.

**W4. Why on every figure.** Make the working behind consequential figures accessible in plain language. Explain
what the number represents, which inputs produced it, what is excluded, what remains uncertain, and why the result
matters. Apply the established transparency standard consistently across the product. W4 is a potential standalone
item as well as a cross-cutting design requirement.

**W5. Cause and effect you can move.** Let the person adjust hypothetical inputs such as a savings contribution, debt
payment, or trip cost and see the resulting changes in the relevant projections. Use the financial engine to
calculate consequences. Identify assumptions and preserve the original plan until the person explicitly chooses to
adopt a change. Do not describe a modeled scenario as a prediction or silently change the person's allocation.

**W6. Reading bills and quotes in Groundwork's window.** Support authorized reading of relevant bills, renewal
notices, and payoff quotes. Extracted figures must be tied to the document, labeled with the appropriate date and
meaning, and confirmed when required before being used as trusted financial information. Do not assume extracted
text is correct merely because it came from a document.

**W7. Questions in the person's own words.** Allow questions about the person's financial record, such as, *"How much
did we spend eating out since June?"* The model may translate the question into a constrained, authorized query. The
financial engine answers from the actual record. The explanation layer presents the result and its limitations.
Unsupported questions must trigger clarification or an explicit statement of what cannot be established. This feature
must not become an unrestricted advice chatbot.

**W8. Refunds and returns followed through.** Track a documented return or expected refund and compare it with
subsequent financial records. Distinguish a merchant's stated refund, an expected arrival, a pending transaction, and
a refund actually observed in the account. Do not mark a refund as received without supporting evidence.

**W9. A year-end financial gathering.** Gather relevant yearly categories, totals, and documents for the person or
their tax professional. Clearly distinguish a financial summary from tax advice, and do not assert tax treatment
without appropriate verified information and authority.

**W10. A monthly reflection that stands on its own.** Summarize verified changes, approaching obligations, meaningful
uncertainties, and a useful question for the person to consider. Avoid generic praise, shame, artificial urgency,
engagement tactics, and unsupported explanations. A reflection must be useful even if the person does not take
action.

## Part 6 — Additional Opportunity for a Future Item

**Goal-directed planning and adverse-scenario analysis.** A proposed future item, not an addition to the W1–W10 menu
and not authorization to build.

Groundwork should eventually be able to compare the person's current financial trajectory with goals they explicitly
state and difficult scenarios they want to prepare for: building an emergency reserve, replacing a vehicle, avoiding
a cash shortfall, or understanding the consequences of an unusually expensive winter.

The system would:
1. Record the person's stated goal without inventing priorities.
2. Calculate the current trajectory from available financial evidence.
3. Identify the gap between the trajectory and the goal.
4. Let the person specify or approve scenario assumptions.
5. Calculate the consequences of alternative choices and adverse conditions.
6. Explain trade-offs, uncertainties, and missing information.
7. Leave the person free to adopt a plan, change it, or do nothing.

Budgeting should increasingly emerge from verified financial data and the person's chosen goals, rather than
requiring the person to manually predict every expense in advance.

This item must distinguish current facts, expected events, hypothetical scenarios, user priorities, and adopted plans.
It must not silently turn a goal into an authorization or a forecast into a promise. (Item 66, SCENARIOS.md, already
rules the scenario side: observed / projected / user-supplied never confused.)

## Part 7 — Architectural Standard

The intended division of responsibility:

**Financial Engine → Calculated Findings → Evidence and Rules → Explanation Layer / optional Local LLM → Validation
Gate → User-facing output**

- The financial engine owns financial calculations.
- The evidence layer owns provenance and the distinction between established facts, assumptions, and unknowns.
- The model owns explanation, teaching, and proposing constrained questions or scenarios.
- The validation gate checks claims against the evidence and blocks unsupported conclusions.
- The person owns consequential choices, confirmations, and the movement of money.

No stage may silently grant itself authority assigned to another stage.

This architecture must remain consistent with Groundwork's local-first privacy requirements, AI-off functionality,
financial invariants, transparency requirements, and existing development authorization process.

## Part 8 — Acceptance and Release Standard

Every future item is evaluated against AP1–AP11 and TM1–TM8, and every AI-enabled item must additionally demonstrate
compliance with RG1–RG6 (accepted 2026-10-09), supported by S1–S7.

Before release, the responsible item must establish:
- The feature's intended value and boundaries.
- The financial and personal data it uses.
- The provenance of the facts it presents.
- The calculations and assumptions behind its conclusions.
- The distinction between facts, interpretations, forecasts, and choices.
- Its behavior when evidence is missing, conflicting, stale, or incorrect.
- Its behavior when the model generates unsupported claims.
- Its privacy and authorization boundaries.
- Its AI-off behavior, where applicable.
- Its adversarial and regression test coverage.
- Its auditability and correction behavior.
- Its compliance with existing project gates and explicit implementation authorization.

Passing ordinary tests is not sufficient if the feature can still convert unsupported model output into a trusted
financial conclusion. A feature that cannot establish its reliability must remain unshipped or have the unsupported
capability withheld.

## Part 9 — Ruling Record

Accepted by Rob on 2026-10-09 (first ruling):
- AP1–AP11: accepted as the governing standard.
- TM1–TM8: accepted as prohibitions.
- W1–W10: menu only; no item is opened by this ruling.
- No code authorized by item 65.

Accepted by Rob on 2026-10-09 (second ruling: "approve H1–H6 and S1–S7 as the next ruling, while leaving W1–W10
unopened"):
- RG1–RG6: AI factuality, evidence, validation, memory, scenario, failure, and testing safeguards.
- S1–S7: implementation expectations supporting those safeguards.
- W1–W10: still unopened.

Not ruled: goal-directed planning and adverse-scenario analysis, a potential future item requiring separate
authorization.

**Final governing principle:** Groundwork should exploit its full analytical capability without exceeding its
evidentiary authority. It should find what the person could not reasonably find alone, explain what the evidence
actually means, disclose what remains unknown, and help the person understand the consequences of their choices.

It must never substitute a plausible answer for a verified one, a model-generated assertion for evidence, or software
authority for the person's authority over their own financial life.
