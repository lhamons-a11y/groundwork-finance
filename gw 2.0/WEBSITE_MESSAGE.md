# Item 37 — The website says what Groundwork is

Opened 2026-10-04 (Rob: *"I would like the process of what it should look like to be laid out just like what we've
done with the application"*). No code, and no change to the website. This pass asks for rulings; it authorises nothing.

Rob's description, the same day: *"We are building a full feature financial application that actually tracks the
user finances and also learns and teaches users how to understand finances. Without selling you a loan, credit card,
and subscription. This is an application that is made for everyone no matter their financial situation."* Then: *"Also
health care cost."*

The site says something narrower: a debt-payoff app for people who are broke. This pass measures what it says today,
asks for the rulings that decide what it should say, and lays out the stages from here to a published site. It uses
the same stages as an app feature: opened, ruled, built against a gate, accepted, then published.

## 1. What the site says today (measured 2026-10-04 at `c2094fc`)

- The whole site is one file, `Website/website.py`. It is identical on `lts/1.x` and master.
- Public pages: `/` (home), `/download`, `/knowledge-base` (help), `/about`, `/privacy`, `/terms`, `/features`,
  `/signup`, `/changelog`.
- It also serves `/version.json`, which the app's update check reads. That is one GET of a static file: the request
  sends no version and no data (`server.py` `update_check`), and the website does not count it as a page view.
- The site advertises **version 1.1**.

### 1a. The site describes a debt app

| Where | What it says |
|---|---|
| Home headline, `website.py:460` | *"Stop living paycheck to paycheck. Groundwork gives you a real plan."* |
| Home subhead | *"…builds a step-by-step path out of debt"* |
| Home search and preview text, `:453` | *"…stop living paycheck to paycheck and build a real plan to get out of debt."* |
| Home features title, `:496` | *"Everything you need to get out of debt"* |
| Home closing section, `:636` | *"Built for people who are tired of being broke"* |
| About, `:1084` onward | *"…built from scratch for that situation"* (paycheck to paycheck, credit card debt) |
| About search text, `:1114` | *"…built to help you get out of debt and stop living paycheck to paycheck."* |
| Features opening, `:1288` | *"Every tool you need to get out of debt and start building wealth."* |

Ledger, net worth, investments, reconciliation, imports, the trip planner, Before You Buy and the reports all appear,
but as tools for getting out of debt. A reader with savings and no debt has no reason to stay. A reader in debt is
described as *"broke"*.

### 1b. Claims that are not true today

These are wrong now, whatever the site's message becomes.

1. **Learning.** Home, `:475`–`:483`: *"it watches what you actually do (when you pay, how you adjust budgets, how
   quickly you recover from mistakes), learns the patterns, and adapts."* This is the silent learning Rob ruled out on
   2026-08-17: nothing Groundwork notices may become persistent memory unless it is shown to the person.
2. **"By default."** Home, `:522`: *"runs privately on your own machine by default."* "By default" implies another
   option. There is none: cloud AI was removed on both lines (item 21, 2026-09-27). The Help and Privacy pages already
   say *"There is no cloud AI option,"* so the home page contradicts them.
3. **"AI reports send aggregated numbers only."** Help, `:1051`: *"AI reports send aggregated numbers only — no names,
   no account details."* This was written for the cloud path. Nothing is sent now.
4. **The Report button.** About, `:1105`: *"the ⚑ Report button in the app sends us the error log directly."*
   Groundwork has never sent it.
   - In 1.1 (`lts/1.x`, `v1.1.0`) the button opens the user's own mail app with the report filled in. The user sends
     it.
   - In 2.0 the button only prints the report (`app.js`, *"Print-only by design"*).
   - Help, `:1059`–`:1061` (*"Open in mail app"*) is right for 1.1 and wrong for 2.0.
5. **"One concrete thing to do differently"** (home, `:522`) and **"one concrete suggestion per month"** (features,
   `:1313`). Both promise a verdict, which the teaching goal (2026-09-24 and 09-26) and the report-statement rule
   (2026-09-27) rule out.
6. **"78% of Americans live paycheck to paycheck."** Home, `:644`. No source anywhere on the site.
7. **"No manual entry."** Home, `:502`. An import starts with a file the user downloads from their bank. "No
   retyping" would be true.
8. **The Privacy page's "This website" section** (`:1131`):
   - It leaves out the counters the website keeps: one count per page per day, and one count per download platform per
     day. It stores no IP address, cookie or user agent (`website.py:58`–`:113`).
   - It says to unsubscribe *"by emailing"*. Every update email also carries a one-click unsubscribe link
     (`/unsubscribe/<token>`).
   - It says *"Last updated: July 2026"*, but its AI section was rewritten in September.
9. **The Privacy page leaves out what the app does send.** The app makes these outbound calls, and none of them
   carries a balance or figure (the July audit; re-verify before citing):
   - the update check;
   - ticker symbols to Yahoo for prices;
   - state or ZIP codes to EIA for utility and fuel prices;
   - city names and dates to SerpApi for the trip planner.

   *"It never leaves your machine"* is true of the financial data. The page should say what does leave.
10. **The download page will change with other items.**
    - *"offline installer… includes Ollama"* (`:761`) changes when item 31 replaces Ollama with the in-app engine.
    - *"Apple Silicon and Intel Macs"* depends on item 33, which found no Intel Mac build of the in-app engine.

Not checked in this pass: the Features page's *"Ten built-in reports"* (`:1309`) and every other count or capability
the site states. Stage 3 checks them all.

### 1c. What the site does not say at all

- **That Groundwork teaches.** Rob's goal (2026-09-24) is that users stop needing Groundwork to make good decisions:
  explain the term, show the mechanism, teach the question to ask. The site never mentions it.
- **Health care.** It appears only as *"medical bill"* in a placeholder inside the app.
- **That it has nothing to sell.** The site says *"no subscription"* and *"no ads"*. It never says the point: no loan,
  no card and no product is behind the advice, and the user isn't the product, the software is (Rob, 2026-07-25).
- **That it is for everyone.** Every page addresses one situation.

### 1d. Health care, as it stands

- **1.1:** Health care is a spending category, and imports categorize pharmacy, doctor, dental and similar
  transactions automatically.
- **The protected list holds on both lines.** Run against both branch tips on 2026-10-04, `is_protected()` returns
  True for Medications, Prescriptions, Pharmacy, Doctor, Therapy, Dental, Healthcare and Medical. So these categories
  are never offered as cuts.
  - That closes the defect `HEALTHCARE_MODULE_DESIGN.md` §0 found.
  - Only `is_protected()` was checked. §0 also requires health spending to stay out of headroom, reallocation and the
    named best option. Those were not checked.
- **2.0:** The health care module (bills against insurance statements, deductible and out-of-pocket progress,
  medication prices, the year that follows) is `HEALTHCARE_MODULE_DESIGN.md`. It is marked *"Draft for decision.
  Nothing built."*
  - Parts of the record layer exist: plan identity and the accumulator and reconciliation derivations.
  - No screen for them was found.
- **The health-data privacy rule** (`HEALTH_TRUST_BOUNDARY.md`) is doctrine, and its own status line says enforcement
  does not exist.

## 2. Points for ruling

**W1. What Groundwork is, in one sentence.** Search results, link previews and the headline all carry this sentence.

- (a) A full personal finance app that tracks your whole financial picture, teaches you to understand it, and has
  nothing to sell you, for everyone whatever their situation. Debt payoff is one tool in it: first on screen for
  someone in debt, never the definition of the app.
- (b) Keep the debt-first message and add the other features below it.
- (c) Lead with teaching, and put tracking second.

*Recommended: (a).* It is Rob's own description. (b) keeps losing every reader who is not in debt. (c) promises the
part that is mostly 2.0. Exact wording is stage 4. Example lines, not proposed copy: *"Your whole financial picture,
explained, and nothing to sell you."* · *"Understand your money. Nobody's selling you anything."*

**W2. The pillars.** The structure the home, About and Features pages are built on.

1. **It tracks everything:** budget, ledger, net worth, investments, debt and health care spending, from your own
   bank files.
2. **It teaches:** what a term means, how the number was made, and the question to ask next time.
3. **Health care is a cost, not a failure:** tracked, explained, and never something Groundwork suggests cutting.
4. **It has nothing to sell you:** no loan, no card, no subscription, no ads. Your data stays on your machine.

*Recommended.* Health care gets its own pillar because it is the clearest proof of pillar 4: an app that sells loans
has no reason to refuse to price your prescriptions against your debt.

**W3. Today versus where it's going.** The site offers 1.1 for download, and much of the teaching and the health care
module is 2.0.

- (a) The site describes only what the downloadable version does. A clearly labelled *"Where Groundwork is going"*
  section names the 2.0 direction, with no dates.
- (b) The same, with the 2027 release year.
- (c) Nothing about 2.0 until it ships.

*Recommended: (a).* A public date becomes a promise. (c) hides the direction Rob just described. This is Rob's call.

**W4. Who it is for.** Drop *"tired of being broke"* and *"built for that situation"*. Keep the warmth for people in
hard spots, in wording that holds at both ends (for example *"whether you're paying down $12,000 or deciding where
your first $10,000 goes"*).

*Recommended.*

**W5. The proof rule, applied to the site.**
- Every factual claim on the site traces to the measured behaviour of the version offered for download, or it comes
  off.
- A statistic carries its source, or it comes off.
- The site states no verdicts about the reader's finances.
- 2.0 behaviour appears only under W3's labelled section.

This is the rule the app already follows for report statements (2026-09-27) and teaching prose (G6).

*Recommended.*

**W6. A gate for the website.** Today nothing tests the site's text. s52 already pins the no-cloud wording across the
three EULA texts.

- (a) A claims inventory (stage 3) plus a smoke section that fails the gate on known-false wording ("by default" AI,
  "watches… learns", "sends us the error log", "medical debt", an unsourced statistic). It also checks that the
  site's privacy and AI wording agrees with the app and EULA texts, and that the advertised version matches
  `version.json`.
- (b) The inventory as a document only, checked by hand at each release.
- (c) Nothing.

*Recommended: (a).* It is code, so it needs its own authorisation at stage 5. Without it, §1b is what the site drifts
back to: every item there was true once.

**W7. Correct the false claims before the rewrite?** §1b items 1–8 are false on a live public page, and items 2 and 4
contradict the site's own privacy wording.

- (a) A small correction pass first: change only the false sentences, no repositioning. Stage 2 below.
- (b) Fold the corrections into the full rewrite.

*Recommended: (a).* Rob said the website need not be built now, so this is his call on timing. (a) is a few
sentences, and it stops the site promising silent learning in the meantime.

**W8. Health care on the site.**
- The words are *"health care cost"*, never *"medical debt"* (`HEALTHCARE_MODULE_DESIGN.md` §0.2).
- Care is never measured in months of debt-free date (§0.1).
- For 1.1, the site says only what is true today: health care is tracked as its own spending category, and Groundwork
  does not suggest cutting it.
  - Before the site says *"never"*, verify the other places §0 names: headroom, reallocation, the named best option,
    the do-nothing option and the honest no.
- The 2.0 module appears only under W3's section.
- No health-specific privacy promise until `HEALTH_TRUST_BOUNDARY.md` is enforced. The general promise (your data
  stays on your machine, no cloud AI) already covers health spending.

*Recommended.*

**W9. What the Privacy page covers.**
- The website's own aggregate counters (§1b.8).
- Every outbound call the app makes and what each one sends (§1b.9). The claim becomes *"no call Groundwork makes can
  carry your financial data off your device"* instead of a blanket *"never leaves"*.
- The Report button, as each line actually behaves.
- The one-click unsubscribe.
- A true *"last updated"* date.

*Recommended.* *"No telemetry"* stays: it is true of the app.

## 3. The process from here

Each stage starts only when the one before it is ruled or accepted, as with the app. Nothing reaches the public site
without Rob doing it.

| Stage | What happens | Output | Who decides |
|---|---|---|---|
| **0. Opened** | This document: measured state, W1–W9 | this file, queue row 37 | — |
| **1. Ruled** | Rob rules W1–W9 | rulings recorded in §4 | Rob |
| **2. Correction pass** *(if W7 (a))* | Only §1b's false sentences change, to what is true for the version on the page. No repositioning | a `Website/website.py` diff; full gate green; local preview screenshots | Rob authorises, then accepts |
| **3. Claims inventory** | Every factual claim the site makes, each with the code path or measurement behind it and the line it applies to (1.1 or 2.0), in the style of the July call-home audit. Anything unproven is marked for removal | §5 of this file | Rob rules what stays |
| **4. Copy draft** | Full wording for home, About, Features, the Help intro, Privacy, and every page's search and preview text and structured data, built on W1–W4, checked against stage 3 and the W5 rule. Written here, not on the site, one page per section, so it can be ruled page by page | §6 of this file | Rob rules wording |
| **5. Build** | The site change, plus the W6 gate section if authorised. Run `website.py` locally, check every page, take screenshots, run the full gate | commits on a branch; gate green; screenshots | Rob authorises, then accepts |
| **6. Publish** | Deploying the site | the live site | Rob does it; Claude does not publish |
| **7. Keeping it true** | Any release that changes a behaviour the inventory cites updates the inventory and the page in the same pass. The W6 section catches wording that drifts back | inventory rows move with the code | each item's own ruling |

Not yet known, and to be named at stage 2: which branch the live site deploys from. Today the two lines' copies are
identical, so it has not mattered.

## 4. Rulings

*(none yet)*

## 5. Claims inventory

*(stage 3)*

## 6. Copy draft

*(stage 4)*

## 7. Not in this pass

- Visual redesign, new pages, imagery, and the mock screens on the home page (beyond W4's wording).
- Newsletter content and cadence. Search-engine strategy beyond the descriptions in stage 4.
- The EULA and terms text. Those follow their own rule: GW_TERMS_VERSION, three texts kept in step.
- Any 2.0 feature itself. This pass only describes features; it never builds them.

OPENED 2026-10-04. No code. Awaiting Rob's rulings on W1–W9.
