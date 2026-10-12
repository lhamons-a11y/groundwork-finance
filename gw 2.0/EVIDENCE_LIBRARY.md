# Item 58 — The evidence library: what research says, offered where it applies

**ITEM 58 ACCEPTED + CLOSED 2026-10-11** (Rob: "i accept items 58 and 59 and the draft").

**ACCEPTED + CLOSED 2026-10-10** (Rob 2026-10-10: "i accept all").

Opened 2026-10-09. Rob:
- *"can we add that type of information into groundwork to help it learn how to teach? Like a research of all
  financial behaviors that add up and allow the llm to narrate with better financial and logical verbiage that we
  won't ever fail the guardrails that we setup."*
- *"lets not worry about never break the rules as much as giving the guardrails a foundation now instead of hoping
  they holdup."*

It grew from item 39's point 2 and Rob's question about how often people check their finances. **E1–E10 RULED 2026-10-09 (Rob: "approve E1–E10 as recommended")**: ruling 6 stands (E2); every entry verified against its paper and accepted by Rob before it ships (E6); master only (E10). **BUILT 2026-10-10 on master** (Rob: "build all items that have been ruled on"); see §5. **All nine entries ACCEPTED 2026-10-10 (Rob 2026-10-10: "i accept all") and now offered where they apply.**

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


## 5. Built (2026-10-10, master)

- **E1.** `core/data/evidence.json`, one record per finding, read by `core/evidence.py`. `problems()` refuses a record
  missing a field or a full source, with an unknown strength, fact or surface, or with an offer that isn't a question.
- **E2.** Facts come from the person's goals and debts only: `has_savings_goal`, `has_debt`, `multiple_debts`,
  `has_card_balance`. Selection never reads usage; s188 fails if `core/evidence.py` names the opens or any usage
  record, and a mutation proves the check bites.
- **E3.** An entry shows as written: finding, *What it doesn't show*, source line, strength. No model is involved, so
  AI off changes nothing. **Not built:** the narrator's optional introducing sentence (E3 says *may*). Nothing calls
  the narrator about an entry yet, so no `[ev:id]` tag is ever displayed.
- **E4.** Voice rule **R11_research_claims_sourced**, in both gate copies (`_voiceGateCheck` and
  `voice_discipline_test.py`), with the `RESEARCH_CLAIMS` wordlist in `voice_rules.json`. A sentence with a research
  phrase fails unless it carries `[ev:<id>]` naming an *accepted* entry. If the accepted ids can't be loaded, every
  such sentence fails (fail closed). It runs on every gated AI surface.
- **E5.** Each offer has Yes / No thanks. The answer is the person's statement, kept append-only (`evidence_answers`),
  with the latest one shown and changeable. **Not built:** acting on a yes (a reminder, a raise plan). Each offer's
  follow-through is its own piece of work.
- **E6.** Only entries with `status: accepted` and an `accepted_on` date are ever offered or citable. **All nine
  shipped entries are drafts**, so nothing shows in the app until Rob accepts them below.
- **E7.** Nine drafts, each written from its paper's abstract or publisher record (§6 says which). Not drafted yet:
  - **emergency savings and financial strain:** no specific paper was chosen;
  - **mental accounting (Thaler 1999):** the abstract couldn't be read in full.
- **E8.** Each app start records the time (`app_opens`, the last 60 days). The working picture shows *"You opened
  Groundwork N times in the last 30 days, mostly Sunday evenings"*, naming the most common time only when it
  holds at least 40% of 4 or more opens. Only `usage_open` and `usage_rhythm` touch the record (s188).
- **E9.** The goal card (Settings > sinking funds), the debt plan (beside the advisor) and the working picture.
  **Not built:** item 49's card payoff rows. The debt-plan block sits on the same page.
- **E10.** s188: 14 checks.

## 6. The entries (accepted 2026-10-10)

Each was drafted from what is named under *Checked against*. An entry checked only against its abstract or a
working paper should be read against the full paper before it is accepted. Accepting one means setting its
`status` to `accepted` with the date, in a release.

### harkin2016_monitoring - accepted 2026-10-10
- **Finding:** Across 138 experiments, helping people check their progress toward a goal more often made them more likely to reach it. The effect was larger when the progress was written down or reported.
- **What it doesn't show:** Most of the studies were about health goals such as exercise, diet and weight, not money. It is an average across studies; it does not say how often any one person should check.
- **Source:** Harkin, Webb, Chang et al. (2016). *Does monitoring goal progress promote goal attainment? A meta-analysis of the experimental evidence*. Psychological Bulletin 142(2), 198-229. https://doi.org/10.1037/bul0000025
- **Strength:** meta-analysis. **Applies when:** has_savings_goal. **Shown on:** goal, willingness.
- **Offer:** Want a weekly reminder to look at your goals?
- **Checked against:** abstract and the accepted manuscript's record (White Rose eprints 91437)

### karlsson2009_ostrich - accepted 2026-10-10
- **Finding:** Investors in Sweden and the United States looked at their accounts more often when markets were rising than when markets were flat or falling.
- **What it doesn't show:** It studied investors and their portfolios, not household budgets. It describes a pattern across many people and says nothing about why any one person looks or does not.
- **Source:** Karlsson, Loewenstein & Seppi (2009). *The ostrich effect: Selective attention to information*. Journal of Risk and Uncertainty 38, 95-115. https://doi.org/10.1007/s11166-009-9060-6
- **Strength:** field study. **Applies when:** always, on its surface. **Shown on:** willingness.
- **Offer:** Want a weekly reminder that comes whatever the week looked like?
- **Checked against:** abstract

### sicherman2016_attention - accepted 2026-10-10
- **Finding:** Logins to online retirement accounts fell by about 9.5% after the market fell, and were lower when market volatility was high.
- **What it doesn't show:** Retirement-plan investors at one provider. How much attention people paid also varied with age, gender and wealth.
- **Source:** Sicherman, Loewenstein, Seppi & Utkus (2016). *Financial attention*. Review of Financial Studies 29(4), 863-897. https://doi.org/10.1093/rfs/hhv073
- **Strength:** field study. **Applies when:** always, on its surface. **Shown on:** willingness.
- **Offer:** Want a weekly reminder that comes whatever the week looked like?
- **Checked against:** abstract

### thaler2004_smart - accepted 2026-10-10
- **Finding:** At one company, employees who agreed in advance to send part of each future raise to retirement saving went from saving 3.5% of pay to 13.6% by their fourth raise.
- **What it doesn't show:** One employer's plan, and the workers who chose to join it. A later U.S. Department of Labor review rated the causal evidence low. It is about raises and retirement plans.
- **Source:** Thaler & Benartzi (2004). *Save More Tomorrow: Using behavioral economics to increase employee saving*. Journal of Political Economy 112(S1), S164-S187. https://doi.org/10.1086/380085
- **Strength:** field study. **Applies when:** has_savings_goal. **Shown on:** goal.
- **Offer:** Want to decide now how much of your next raise goes to a goal?
- **Checked against:** working-paper abstract and the Department of Labor CLEAR summary; the published abstract was not read

### madrian2001_defaults - accepted 2026-10-10
- **Finding:** When one company began enrolling new employees in its retirement plan automatically, far more took part, and many kept the plan's default contribution rate and fund.
- **What it doesn't show:** One large U.S. company. Many people stayed at the default even where it was not the rate they would have chosen, so a default carries weight either way.
- **Source:** Madrian & Shea (2001). *The power of suggestion: Inertia in 401(k) participation and savings behavior*. Quarterly Journal of Economics 116(4), 1149-1187. https://www.nber.org/papers/w7682
- **Strength:** field study. **Applies when:** has_savings_goal. **Shown on:** goal.
- **Offer:** Want to set one monthly amount for this goal and leave it in place?
- **Checked against:** NBER working-paper abstract (w7682)

### gal2012_small_wins - accepted 2026-10-10
- **Finding:** Among about 6,000 people in a debt settlement program, closing individual debt accounts went with finishing the program, whatever the dollar size of the accounts closed.
- **What it doesn't show:** People in a debt settlement program. It shows a link, not that closing the smallest debt first causes success, and paying the highest rate first still costs less interest.
- **Source:** Gal & McShane (2012). *Can small victories help win the war? Evidence from consumer debt management*. Journal of Marketing Research 49, 487-501. https://www.kellogg.northwestern.edu/academics-research/research/detail/2012/can-fighting-small-battles-help-win-the-war-evidence
- **Strength:** field study. **Applies when:** multiple_debts. **Shown on:** debt_plan.
- **Offer:** Want to see the plan that closes a debt soonest beside the one that costs the least interest?
- **Checked against:** Kellogg School research and news pages; the abstract itself was not read

### stewart2009_anchor - accepted 2026-10-10
- **Finding:** People who meant to pay only part of a credit card bill chose to repay less when the bill showed the minimum payment.
- **What it doesn't show:** A UK survey and hypothetical bills. People who pay the whole balance each month were not affected.
- **Source:** Stewart (2009). *The cost of anchoring on credit-card minimum repayments*. Psychological Science 20(1), 39-41. https://doi.org/10.1111/j.1467-9280.2008.02255.x
- **Strength:** randomized trial. **Applies when:** has_card_balance. **Shown on:** debt_plan.
- **Offer:** Want to set your own monthly payment for each card, apart from the minimum?
- **Checked against:** abstract opening (Warwick repository) and the university's press release

### karlan2016_reminders - accepted 2026-10-10
- **Finding:** In field experiments at three banks, new savings-account holders who were sent reminders were more likely to reach their savings goal, most of all when the reminder named the goal.
- **What it doesn't show:** New account holders at banks in lower-income countries, with text reminders from the bank. Framing a reminder as a gain or a loss made no clear difference.
- **Source:** Karlan, McConnell, Mullainathan & Zinman (2016). *Getting to the top of mind: How reminders increase saving*. Management Science. https://www.nber.org/papers/w16205
- **Strength:** randomized trial. **Applies when:** has_savings_goal. **Shown on:** goal.
- **Offer:** Want a reminder that names this goal?
- **Checked against:** working-paper abstracts (NBER w16205 and the 2014 draft); the published abstract was not read

### ashraf2006_commitment - accepted 2026-10-10
- **Finding:** In a randomized trial at a bank in the Philippines, clients offered a savings account that held their money until a date or amount they chose had average balances 81 percentage points higher after a year than a comparison group.
- **What it doesn't show:** Clients of one Philippine bank; about 28% of those offered the account opened one. Money held until a date is harder to reach in an emergency.
- **Source:** Ashraf, Karlan & Yin (2006). *Tying Odysseus to the mast: Evidence from a commitment savings product in the Philippines*. Quarterly Journal of Economics 121(2), 635-672. https://doi.org/10.1162/qjec.2006.121.2.635
- **Strength:** randomized trial. **Applies when:** has_savings_goal. **Shown on:** goal.
- **Offer:** Want to give this goal a date and an amount to hold to?
- **Checked against:** abstract and the Yale ISPS record


## 7. The rest of item 58, built 2026-10-11 (Rob: "build 58 and 59")

- **E3, the narrator's introducing sentence.**
  - With AI on, each entry on each surface gets one sentence (about 25 words, no numbers, no advice) saying why it is
    shown there.
  - It goes through the voice check: R11 requires the entry's `[ev:id]` tag after any mention of research.
  - It is kept once it passes (`evidence_intro_<id>_<surface>`) and shown with the tag taken out.
  - With AI off there is no sentence; the entry stands as written.
- **E5, acting on a yes.** Each entry now has a follow-through (`act`):
  - **Open it for me** (navigation only) for the monthly amount and the date and amount of a goal (Madrian, Ashraf,
    and the emergency-savings draft), and for the debt plan and the cards (Gal, Stewart);
  - **the Sunday check-in names your goals** and where each stands, with what a month gets there (Harkin, Karlan),
    seen in s188;
  - **the Sunday check-in is that reminder**, coming every Sunday whatever the week looked like (Karlsson,
    Sicherman);
  - **Thaler & Benartzi (a share of the next raise):** Groundwork can't act on this yet, because nothing notices a
    raise. The answer is kept and it says so.

  Adding `act` and a surface changes how an accepted entry is wired, not its accepted words.
- **E9, the card payoff rows.** The debt entries (Gal, Stewart) now also show under the trip's card payoff plan (item
  49), surface `card_payoff`.
- **E7, the two topics not drafted before:**
  - **Emergency savings: drafted.** `gjertson2016_emergency`, from the paper's abstract (the full text is paywalled).
    It applies when the person has no savings goal and offers *"Want to start a small fund for emergencies?"*. **It
    is a draft and shows nowhere until Rob accepts it (E6).**
  - **Mental accounting (Thaler 1999): not drafted.** The abstract could only be read in part (its third component
    was cut off in every copy found), and it is a research review, a kind of evidence E1's strengths don't list.
    Drafting it would mean writing it partly from memory, which E6 forbids. It needs either the full paper, or a
    specific mental-accounting experiment instead.

### 6a. The new draft, for acceptance

### gjertson2016_emergency - accepted 2026-10-11 (Rob: "i accept items 58 and 59 and the draft")
- **Finding:** Among low-income households in disadvantaged neighborhoods, those that set money aside for emergencies
  reported somewhat less hardship three years later, such as going without enough food or losing phone service.
- **What it doesn't show:** Low-income households in particular neighborhoods, not a national sample. It shows a link,
  and the difference was modest; it does not show that saving caused the difference.
- **Source:** Gjertson (2016). *Emergency saving and household hardship*. Journal of Family and Economic Issues
  37(1), 1-17. https://doi.org/10.1007/s10834-014-9434-z
- **Strength:** field study. **Applies when:** no savings goal. **Shown on:** goal, willingness.
- **Offer:** Want to start a small fund for emergencies?
- **Checked against:** the abstract (IDEAS/RePEc record); the full text is paywalled and was not read.
