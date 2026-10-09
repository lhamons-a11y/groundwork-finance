# Item 58 — The evidence library: what research says, offered where it applies

Opened 2026-10-09. Rob:
- *"can we add that type of information into groundwork to help it learn how to teach? Like a research of all
  financial behaviors that add up and allow the llm to narrate with better financial and logical verbiage that we
  won't ever fail the guardrails that we setup."*
- *"lets not worry about never break the rules as much as giving the guardrails a foundation now instead of hoping
  they holdup."*

It grew from item 39's point 2 and Rob's question about how often people check their finances. **E1–E10 RULED 2026-10-09 (Rob: "approve E1–E10 as recommended")**: ruling 6 stands (E2); every entry verified against its paper and accepted by Rob before it ships (E6); master only (E10). **No code yet:** the build needs its own go-ahead.

## 1. What is true today (measured 2026-10-09 on master a729e15)

- **Groundwork teaches from the user's own record and their own statements**, through the engines (the solution
  engine, the Willingness Layer, the estimates and the reports). It holds **no research findings**. Nothing in it
  says what is known about how people manage money.
- **The narrator** (phi3.5, local) explains what the engines found. The voice check (`_voiceGateCheck`) blocks
  verdict words, advice words and numbers not in the findings. **There is no rule about research claims:** a
  sentence like *"studies show people who budget save more"* passes if its words are allowed, whether or not any
  study says it.
- **The rules this must keep:**
  - *Report statements must be proven*: no judgement wording, and the math shows it true.
  - *Teach the question*: mechanisms are conditional, never verdicts.
  - *Transparency*: every figure shows its working.
  - *No silent learning.*
  - **Willingness ruling 6**: the layer never reads usage.
  - **The dashboard rule**: usage never creates, ranks or implies anything.
  - **A10**: everything works with AI off.
  - **Local only**: no network.
- **The research that started this** (to be verified against the papers before any entry is written):
  - Monitoring progress toward a goal makes reaching it more likely, more so when the progress is recorded (Harkin
    et al., 2016, *Psychological Bulletin*, a meta-analysis).
  - People look at their accounts less when the news is bad: the "ostrich effect" (Karlsson, Loewenstein & Seppi,
    2009; Sicherman, Loewenstein, Seppi & Utkus, 2016). That is why **how often someone checks can't be read as how
    willing they are**: it moves with how things are going.

## 2. What it would do

A file shipped with Groundwork holds checked findings. When the user's record or their own statements show a
situation an entry applies to, the engine offers that entry where it fits, in its own words and with its source.
It's offered as an option or a question, never as a verdict about the user. The narrator may introduce an entry but
never invent one, and a new voice-check rule makes that hold.

## 3. Points for ruling

**E1. The entry.** One record per finding:
- **id**;
- **finding**: one or two plain sentences, no verdict words;
- **limits**: who was studied, and what it does *not* show;
- **source**: authors, year, journal, and a link where public;
- **strength**: meta-analysis, randomized trial, field study or survey;
- **applies when**: the situations, each a fact the engines already compute or a statement the user made;
- **offer**: the question or option shown, such as *"Want a weekly check-in reminder?"*.

Stored as `core/data/evidence.json`, versioned like the fare table, and changed only with a release.
*Recommended.*

**E2. Selection is the engine's, and never reads usage.** An entry is chosen by a plain rule matching its
*applies when* to the user's own financial facts or statements. **Ruling 6 and the dashboard rule stand:** how often
someone opens Groundwork never selects, ranks or implies an entry. The narrator never chooses entries.
*Recommended.*

**E3. Shown as written, with its source.** The entry's finding, limits line and source appear as written, with no
paraphrase by the model. The narrator may add one introducing sentence, which passes the voice check like any
other. With AI off, entries show without the sentence (A10).
*Recommended.*

**E4. The foundation: a voice-check rule for research claims (fail closed).** A sentence that makes a research-style
claim is blocked unless it carries an entry id from the library. That means words like *study / studies, research,
researchers, evidence shows, people who…, on average people, most people, experts*. The check runs on every AI
surface, through item 10's sentence-level check once that's built.
*Recommended.* It makes *"the narrator never invents research"* an enforced structure, not a hope.

**E5. Teach the question.** Every entry's *offer* is a question or an option the user can take or leave. The user's
answer is a **statement**, and the Willingness Layer already reads statements. No entry concludes anything about
the user.
*Recommended.*

**E6. Verified, and accepted one by one.** Each entry is drafted against the actual paper, with its limits, and Rob
accepts each before it ships. No entry is written from memory. A finding that later changes is corrected in the
next release, and the old wording is kept in the file's history.
*Recommended.*

**E7. The first set, about 20–30 entries.** Proposed topics, each to be verified:
- watching goal progress (Harkin et al. 2016);
- the ostrich effect (Karlsson et al. 2009; Sicherman et al. 2016);
- automatic savings increases (Thaler & Benartzi 2004, *Save More Tomorrow*);
- defaults in retirement saving (Madrian & Shea 2001);
- small early wins in paying off debt (Gal & McShane 2012);
- the minimum-payment anchor on card statements (Stewart 2009);
- savings reminders (Karlan et al. 2016);
- mental accounting (Thaler 1999);
- emergency savings and financial strain;
- present bias and commitment devices.

*Recommended, with each entry's source confirmed before it's written.*

**E8. The user's own rhythm, shown, never read** (from Rob's question). A fact view: *"You opened Groundwork 9 times
in the last 30 days, mostly Sunday evenings."* Shown to the user, read by no engine (ruling 6), with the goal-progress
entry's offer of a weekly reminder beside it.
*Recommended.*

**E9. Where entries appear.** Where the situation is already shown: the goal card, the debt plan, the card payoff
rows (item 49), the Willingness home. An entry never appears as an unprompted interruption of its own; the
proactive card's rules still govern that.
*Recommended.*

**E10. Lines and tests.** Master only. Tests:
- every entry has all its fields and a source;
- selection never reads a usage event (a mutation that adds one fails);
- E4 blocks an unsourced research claim and passes a sourced one;
- entries show with AI off;
- no entry text carries verdict words.

*Recommended.*

## 4. Not decided here

- **Reversing ruling 6** (usage as a willingness signal). Not proposed. The ostrich effect is the reason it would
  misread people under the most strain. If Rob wants it, it's its own point with that risk beside it.
- **Research run on Groundwork's own users.** Not possible under local only, since no data leaves the computer. One
  person's history is far too small to show such a pattern.
