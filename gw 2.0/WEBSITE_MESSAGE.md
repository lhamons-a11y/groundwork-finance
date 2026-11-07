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

**W3, ruled by direction (Rob, 2026-10-12):** *"lets add a readable but very readable and simple overview but use more
than a sentence or two to describe many of the new features that is coming that we have in 2.0 that's being built."*
Then: *"make it appear that I have a marketing team that is pushing the new stuff."*
- The site keeps describing the downloadable version. A clearly labelled section describes 2.0.
- That section is a **simple, very readable overview**: a short paragraph for each of the main new features, not a
  line each.
- It covers what is built in 2.0 now. Anything only designed is said to be in design.
- No dates (W3 (a)'s reason stands: a public date becomes a promise).
- **The voice is a polished launch page:** a confident "we", a banner, and benefit-first headlines. That is how a
  marketed product reads. **It does not say there is a marketing team.** That would be a factual claim W5 would have
  to remove, and it would be the one untrue line on a site whose point is honesty. (Claude's reading of the
  direction.) **Rob, 2026-10-12: *"We as in me and my laptop."*** So the "we" is true as written: the site speaks
  as the people who build Groundwork, without claiming more of them than there are.

**W1–W9 RULED (Rob, 2026-10-12: "I accept W1 - W9"):**
- **W1 (a):** one sentence, the whole picture explained with nothing to sell, for everyone.
- **W2:** the four pillars.
- **W3:** as directed above.
- **W4:** the who-it's-for wording.
- **W5:** the proof rule.
- **W6 (a):** the website's own gate section.
- **W7 (a):** correct the false claims first; done in the same build, below.
- **W8:** health care on the site.
- **W9:** the Privacy page's coverage.

**With it, a widened scope (Rob: "Make the website look amazing and fresh"):** a visual redesign, which §7 had left
out of this pass.

## 4a. Built 2026-10-12: stages 2–5 in one pass - ACCEPTED 2026-10-12 (Rob: "That website looks amazing. I accept.")

Rob asked for the site itself, so the correction pass, the claims check, the copy and the build were done together on
branch `website-message`. Nothing is published; stage 6 is Rob's.

- **The design.** New typography (Fraunces for headings, Inter for text) and the app's ink, pine and gold palette,
  refreshed. The page uses:
  - a frosted sticky nav and a gradient hero;
  - a sample-figure illustration of the dashboard, labelled *"Illustration · sample figures"*;
  - inline line icons, card grids, a dark privacy band, and fade-in sections (off under *reduced motion*);
  - a four-column footer.

  It is laid out for phones: every page was measured at 375px with no sideways scroll.
- **The pages.**
  - **Home:** W1's sentence, W2's four pillars, *In Groundwork today* (1.1.1 only), the privacy band with what does
    leave the computer, W3's labelled 2.0 section, and W4's who-it's-for.
  - **New `/coming`:** §6.1 in full, in nav, footer and both sitemaps.
  - **Features:** 1.1.1's features, health care spending included.
  - **About:** rewritten, nothing to sell; the Report button as it behaves.
  - **Privacy:** W9, below.
  - **Download / Terms / Knowledge base / Changelog / Signup:** the new look. Their wording is unchanged except
    what was untrue.
- **Corrected (W7), each now pinned by s206:**
  - the "watches... learns the patterns" passage (removed);
  - AI "by default";
  - "AI reports send aggregated numbers";
  - the Report button "sends us the error log" and "error log attached";
  - the unsourced 78%;
  - "No manual entry", which is now "no retyping";
  - "one concrete thing / suggestion";
  - "tired of being broke";
  - "the smarter it gets";
  - "ten built-in reports";
  - "Version 1.1", which is now 1.1.1, the changelog's newest.
- **W9's Privacy page,** re-measured against `lts/1.x` (the download) on 2026-10-12. The app's code contacts:
  - the update check (`groundworkfinance.app`);
  - Yahoo Finance (ticker symbols);
  - the EIA (your state);
  - OpenStreetMap (the places typed into the trip planner).

  The bank and Google Flights windows open only on the person's click, and their section is unchanged (s156 pins
  it). The page also states the website's counters (one per page per day, one per download platform per day, no IP
  address, cookie or browser details), the one-click unsubscribe, and the Report button as it behaves. *"Last
  updated"* is now a true date.
- **W6:** `s206_website_claims.py`.
  - None of the untrue sentences comes back.
  - The version matches the changelog.
  - Every outside service the code contacts is named on the Privacy page.
  - The AI wording agrees with the app and EULA.
  - 2.0 appears only on its page and the home page's labelled section.
  - No title or description leads with debt.
  - W1's sentence is on the home page.
- **Untouched:**
  - the Terms text (EULA rule: s52 and s156 pin it);
  - the download page's platform and AI lines (s61 pins them);
  - the analytics, signup, admin and `version.json` code.
- **To check before publishing:**
  - the pillar *"It explains what it shows"* rests on 1.1.1's help answers and figures' working, and a full stage 3
    inventory would trace each one;
  - the three lines §6.1 flags;
  - which branch the live site deploys from (§3's open question; the build is on master's line).


## 5. Claims inventory

*(stage 3)*

## 6. Copy draft

*(The full stage 4 draft waits for W1, W2 and W4. §6.1 is drafted ahead of it because W3 is ruled.)*

### 6.1 Coming in Groundwork 2.0 (draft, 2026-10-12, for ruling)

Each paragraph traces to a built, accepted item (W5); the table after the draft gives each one. The draft uses plain
words and short sentences, with no figures that could go stale and no dates.

> ## Coming in Groundwork 2.0
>
> **The biggest update we've ever built, and it's being tested right now.**
>
> Groundwork 2.0 does more of the work for you, explains more of what it finds, and still keeps every number on your
> own computer. Here's what's on the way.
>
> ### Your statements, with one press
> No more logging in to download files. Tell Groundwork which bank you use, and when you ask, it opens your bank's
> website in a window inside Groundwork and brings your statements back for you to review. It only goes when you ask,
> never on its own or on a schedule. Your password stays in your computer's own secure vault, not in Groundwork.
>
> ### Your bills, read straight from the biller
> Groundwork can read what a bill says on the company's own website, like the amount and the due date, and put it
> right next to that line in your budget. You confirm it before it's used. And Groundwork never presses a Pay button:
> paying is always yours.
>
> ### Ask why
> A number looks wrong? Ask. Groundwork checks your own records and tells you what it found: a payment filed in the
> wrong place, a deposit that isn't counted as income, a month with nothing imported. If there's a fix, you see
> exactly what would change before anything does, and every fix can be undone.
>
> ### Your pay, employer by employer
> Groundwork reads each paycheck on its own. If one stops showing up or drops, it tells you plainly and shows a few
> ways the month could go from there. If your pay changes with overtime or holiday pay, it asks once, so a slow week
> is never mistaken for a pay cut.
>
> ### Possible futures
> See your next twelve months side by side: as things are, and what happens if your most expensive months come back,
> a month goes by without income, or you pay only the minimums. Every future says what it assumes. If one doesn't fit
> your life, tell it what's missing and they all recalculate.
>
> ### A monthly review and a Sunday check-in
> When a month's records are complete, Groundwork writes up what happened: what came in, what went out, and how it
> compares. Every Sunday, a short check-in looks back at your week and ahead to the next one: a paycheck due, a bill
> coming up.
>
> ### Before You Buy, with the whole cost
> Thinking about a big purchase? See what it really costs each month, interest included, and whether financing it
> costs more than paying down what you already owe. We're not here to talk you out of anything. We show you the
> numbers.
>
> ### Trips, priced from real fares
> The trip planner opens Google Flights and Google Hotels right inside Groundwork and uses the price you pick. Haven't
> picked one yet? It uses the government's average fare for that route instead of a guess.
>
> ### Gifts, as the yearly cost they are
> Birthdays and holidays come every year. Groundwork adds up the next twelve months of them and shows what to set
> aside each month, so December never arrives as a surprise.
>
> ### Utilities and fuel, from public prices
> Groundwork estimates your gas, electric, propane, heating oil and gasoline costs from the U.S. government's
> published prices for your state. It asks which state you're in and never looks up your location.
>
> ### Research, shown honestly
> Where a well-known study backs up an idea, like saving automatically, Groundwork shows you what the study found and
> what it doesn't show.
>
> ### An assistant that lives on your computer
> The AI ships inside Groundwork and runs on your own machine. Nothing you ask it is sent anywhere. Every page still
> works with the AI turned off, and a log shows you exactly what the assistant was given.
>
> ### Every number shows its working
> Groundwork shows where its figures come from: the inputs, the math, and any assumption behind them. If it can't
> show how it got a number, it doesn't show you the number.
>
> ### Easier on the eyes
> We checked every piece of text against every background, so nothing in Groundwork is too faint to read.
>
> ### On the drawing board: health care costs
> We're designing a health care section that tracks your bills against your insurance statements and follows your
> deductible through the year. It's in design, not built yet, and it will follow the same rule as the rest of
> Groundwork: nothing about your health leaves your computer.
>
> *Groundwork 2.0 isn't in the download yet. When it is, you'll see it here first.*

**What each paragraph rests on (W5).** Every row is ACCEPTED in `BUILD_QUEUE.md`, and each is re-verified at stage
3 before publishing:

| Paragraph | Items |
|---|---|
| Statements with one press | 57, 67, 70 (user-started, no schedule; the OS vault) |
| Bills from the biller | 68 (B1-B7; TM1: never presses Pay) |
| Ask why | 72 stages 1-4 |
| Pay, employer by employer | 71 and its amendment D1-D11 |
| Possible futures | 66 |
| Monthly review, Sunday check-in | 75, 76 |
| Before You Buy | 73 |
| Trips | 40-44, 59 (fares and hotels read on the person's click), 41 (the DOT average) |
| Gifts | 74 |
| Utilities and fuel | 26, 34, 30 (state asked, never geolocated) |
| Research | 58 |
| An assistant on your computer | 31, 21, 62, 64, 30 A10 (every surface works AI-off) |
| Every number shows its working | 39 U7 (the transparency standard) |
| Easier on the eyes | 77 |
| Health care, in design | 45 (H1-H7 ruled, design only; stage 1 is H6 enforcement, not built) |

**Three things to check before stage 5.**
- **The health care promise.** *"Nothing about your health leaves your computer"* is true of every call the app makes
  today (W9's list), and it is worded as the general rule, so it stays inside W8. Rob may prefer to hold it until
  H6 is enforced.
- **"Nothing you ask it is sent anywhere."** This is about the assistant only. The update check and the price lookups
  still go out, and W9's Privacy page says so.
- **"You'll see it here first."** This is a promise about the site itself: the 2.0 announcement goes on this page
  before anywhere else. Rob keeps it or drops it.

## 7. Not in this pass

- Visual redesign, new pages, imagery, and the mock screens on the home page (beyond W4's wording).
- Newsletter content and cadence. Search-engine strategy beyond the descriptions in stage 4.
- The EULA and terms text. Those follow their own rule: GW_TERMS_VERSION, three texts kept in step.
- Any 2.0 feature itself. This pass only describes features; it never builds them.

OPENED 2026-10-04. W1–W9 RULED 2026-10-12. Stages 2–5 BUILT 2026-10-12 (§4a): the redesigned site on branch website-message, awaiting Rob's acceptance; publishing is Rob's.

## Direction from Rob, 2026-10-05: a user forum for reporting problems

Rob, on the gap that Groundwork has no way to hear when something breaks (it sends no telemetry, by design): *"we can
fix this with a website rebuild. Have a user forum that things can be reported. This way user won't be concerned with a
outside company seeing their finances."*

Recorded for this pass, not yet a point for ruling:
- **A forum on the site** is where users report problems and ask questions. It is the user's own choice to post.
  Nothing is sent from the app.
- **A report is plain words, not data** (Rob, 2026-10-05: *"I wouldn't expect users to put copies of their program on
  the forum but a suggestion or report an issue like 'the monthly report calculator is not working' that way it's
  easier to report bugs."*).
  - A post describes what happened, or suggests something, in the user's own words.
  - No file, export or "problem report" helper is part of it.
- **A forum is public.** The site's short posting guidance asks users not to include amounts, names or account
  details, since a description is all a bug report needs.
- **Who hosts it,** and what that host can see, is part of the site's privacy statement (W-points on privacy).

## 4b. The horizon (Rob, 2026-10-12)

Rob: *"we do need to make sure for the website and groundwork the goal of our software is to help every user become
finically independent. That's our horizon."*
- **Home:** a band right after the hero, *"Our horizon: Financial independence, for every user"*.
- **About:** opens with *Our horizon*. It says plainly that Groundwork can't promise anyone gets there, and what it
  does do.
- **Coming in 2.0:** the headline paragraph ends on the horizon.
- **Footer:** the one-line description carries it.

It is the goal, stated as a goal: no claim that a user will reach it, which W5 would remove. s206 holds the three
pages to it.

**Wording settled (Rob, 2026-10-12):**
- **The headline:** *"Financial independence, for everyone"* (option 1). "Everyone" replaces "every user": it is
  warmer, and it echoes W1's *for everyone*.
- **Option 2 as the closing statement:** *"Financial independence for everyone, one understood decision at a
  time."* (Rob: *"That is perfect to be placed in the website somewhere that will hit the user like yes this software
  that I have never seen seems like the software that I want to use."*) It appears:
  - on the home page, as a full-width closing band just before the sign-up, with *"That's why Groundwork explains
    every number it shows you, and has nothing to sell you."*;
  - as the last line of About;
  - at the foot of the 2.0 page.

  s206 holds both.

## The 2.0 remake (Rob, 2026-10-31)

Rob: *"with the changes that we added we should remake the website to show this. We should highlight all these features
that Groundwork has and make that the central focus ie: lets market groundwork to make someone feel like that have to
download it. Also add as much SSO [SEO] to the backend that Google and other AI agents can't help but not look at
Groundwork."*

- **W3 superseded:** 2.0 is the site's central focus, on every page - but never shown as available before it is the
  download. `RELEASED_20` follows `SITE_VERSION`: until it is 2.x, everything new says *"New in 2.0 · coming soon"*,
  the 2.0 page says it isn't in the download yet, and the Privacy page names its 2.0 parts; on release day the same
  pages read as current with no other edit.
- **The home page** leads with the assistant, in real screenshots of the made-up sample household: asking in plain
  words (Rob's $200-on-the-Visa question), "Did you mean...?", nothing changing without your Yes, talking to it, and
  money set aside and available. Then *Built so you can trust it* (runs on your computer; can't make a number up;
  never moves money; says when it doesn't know; questions aren't kept; can't be talked into anything), the horizon,
  the four promises, today's features, privacy, what else is in 2.0, who it's for, and seven questions answered.
- **W1, the horizon and the closing statement are unchanged**; every claim is one the app holds (s206). No invented
  proof, no urgency (TM6), no made-up checksum.
- **Corrected:** the 2.0 page said Health care was "in design, not built yet" - the Health page is built; its
  assistant card described an older design.
- **Privacy:** the assistant (questions never kept; the AI log keeps what was read; no money moved) and the microphone
  (off until turned on; recognised on the computer; never sent or kept) - item 113's condition for voice.
- **SEO and AI assistants:** the home page carries the app (with its features and screenshots), its FAQ and the site as
  structured data; a real link-preview image; `/llms.txt` describes Groundwork for AI assistants; `robots.txt` welcomes
  search engines and AI crawlers by name (Google, Bing, OpenAI, Anthropic, Perplexity, Apple, DuckDuckGo) and keeps
  the admin and token pages out; every sitemap entry has a last-modified date.
- **Item 82 R7/R8:** the download page says what happens to 1.1 once 2.0 is the download; the last 1.1 is offered by
  name only when its real SHA-256 is filled in (`V11_SHA256`, release day).

## The 2.0 release site (Rob, 2026-11-07)

Rob: *"update it to show that we are releasing 2.0 with all of the features marking the major feature updates like
healthcare ... the report section also focusing on what's new ... the new AI tools and the privacy push ... add videos
so a user can look at this software and say I need to download this software. Also add the update notice."* Ruled the
same day: the site says 2.0 is out (published only once the 2.0 installers are what `/dl/` serves); the update notice's
version id waits for release day.

- **Released:** `SITE_VERSION = '2.0'`, so every page reads as current. s206 W3 now holds the released wording: nothing
  says "coming soon", the 1.1 line shows on the download page, `/coming` lands on `/whats-new` (301).
- **`/whats-new`**, the launch page: the new AI tools, Health (every feature, the same list as the Health page), Reports
  (what's new), the privacy push, everything else new, and how updating from 1.1 works. Every line traces to an accepted
  item or the app's own words on its screens.
- **Videos:** four tours on the home page, one per section of `/whats-new`, the Health tour on `/health`; each with a
  poster, captions and "made-up figures", and described to search engines (VideoObject). `ask` is the 2026-11-01 tour;
  `health`, `reports` and `privacy` are recorded from the real app on its sample household by `scripts/site_video`
  (headless Chrome, narrated by Groundwork's own Kokoro voice; no downloads). MP4 only for those three: Chrome's WebM
  recording carries no duration, so it can't be seeked.
- **The update notice:** every page's banner ("Already using Groundwork? Updating keeps your records"), the note at the
  top of `/whats-new`, its *Updating from Groundwork 1.1* section, and the changelog's 2.0 entry (no build id yet).
  `Website/version.2.0.json` is the in-app notice for release day: its `latest` is empty, so it offers nothing until the
  2.0 build's `GW_VERSION` is filled in, the changelog entry gets the same id and a date, and it is copied over
  `version.json`.

