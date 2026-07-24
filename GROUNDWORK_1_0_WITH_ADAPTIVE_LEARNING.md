# Groundwork 1.0 With Adaptive Learning

**Status:** Production Build With Real Data  
**Version:** 1.0 (FINAL, not beta)  
**Date:** July 24, 2026  
**Critical Shift:** Adaptive learning ships WITH 1.0, tested against real live database  
**Versioning:** 1.0.0 → 1.0.1 (bugfixes only) → 1.0.2, etc. No new features in 1.x line.

---

## Executive Summary

**This is NOT a beta release.** This is a production release with adaptive learning already built and tested on real data.

**What ships:**
- Debt reconciliation feature (Phases A–G)
- Historian infrastructure (Phase H)
- **Six adaptive learning features, all production-grade (NEW Phase H2)**
- Subsystem verification (Phase I)
- Release readiness (Phase J)

**Key difference from previous plan:**
- Adaptive features are NOT post-1.0; they ship WITH 1.0
- Code has direct access to your real database for testing/verification
- Every adaptive feature is validated against real financial data before shipping
- 1.0 is feature-complete; versions 1.0.1+ are bugfixes only

---

## What Changes

### Testing Strategy: From Hypothetical to Real

**Old approach:**
- Build feature
- Test on synthetic data
- Ship to beta
- Hope users find edge cases
- Iterate in 1.1

**New approach:**
- Build feature
- Query your real database to understand patterns
- Build adaptive feature that learns from those patterns
- Validate against real data BEFORE shipping
- Ship 1.0 with confidence
- Version 1.0.1+ = bugfixes only

### Example: Category Suggestions

**Old:** "Category suggestion is a good idea for 1.1"

**New:** "Let me look at your real categories and merchant patterns, build the suggestion engine, test it against your actual ledger, ship it in 1.0"

---

## Build Phases (Integrated)

### Phase A–G: Debt Reconciliation (14–18 days)
**Same as before.** Build the feature, test it works.

### Phase H1: Historian Infrastructure (2–3 days)
**Same as before.** Production-grade schema and queries.

### Phase H2: Adaptive Learning Features (NEW — 8–12 days)
**This is the critical new phase.** Six features, all production-grade, all tested on real data.

#### Feature 1: Category Suggestions (3 days)
**What it does:** Next time user enters a transaction, app suggests category based on merchant patterns from historian.

**Build sequence:**
1. Query your real ledger: For each merchant, what categories has the user picked?
   ```sql
   SELECT merchant, category, COUNT(*) as freq 
   FROM transactions 
   GROUP BY merchant, category 
   ORDER BY freq DESC
   ```

2. Write suggestion function:
   ```python
   def suggestCategoryForMerchant(merchant_name):
       """Return most common category for this merchant."""
       # Uses historian data
       # Returns (category, confidence %)
   ```

3. Integrate into ledger: When user types a new merchant, fetch suggestion via API
4. Test against your data: Does it suggest correctly for your most-used merchants?
5. Validate: Add to smoke tests; verify suggestion accuracy on known merchants

**Verification:**
- [ ] Query your real merchants (how many unique?)
- [ ] Check suggestion accuracy on 10 most-used merchants
- [ ] Verify suggestions don't break existing categorization

#### Feature 2: Budget Variance Learning (2–3 days)
**What it does:** App learns which budget categories are volatile vs. stable, adjusts buffers automatically.

**Build sequence:**
1. Query your real budget data: For each category, what's the variance?
   ```sql
   SELECT category, AVG(variance_amount) as avg_var, 
          STDDEV(variance_pct) as volatility
   FROM monthly_budget_tracking
   GROUP BY category
   ```

2. Categorize spending patterns:
   - Stable (variance < 10%): "Food" for you = predictable
   - Volatile (variance > 30%): "Entertainment" for you = unpredictable
   - Moderate (10-30%): "Utilities" for you = seasonal

3. Write adapter: Suggest budget adjustments
   ```python
   def adjustBudgetBasedOnVariance(category, proposed_budget):
       """Add buffer to volatile categories, tighten stable ones."""
       variance = getHistoricalVariance(category)
       if variance > 30:
           return proposed_budget * 1.15  # Add 15% buffer
       elif variance < 10:
           return proposed_budget * 0.95  # Tighten by 5%
       return proposed_budget
   ```

4. Integrate: When user edits budget, show suggestion
5. Test: Analyze your categories. Which ones actually need buffers?

**Verification:**
- [ ] Run variance query on your real categories
- [ ] Identify 3–5 volatile categories where buffer helps
- [ ] Verify suggested budgets feel right (not too aggressive)

#### Feature 3: Trip Spending Forecast (2–3 days)
**What it does:** App learns regional trip spending patterns and improves forecasts.

**Build sequence:**
1. Query your real trip data: How much did you spend per region?
   ```sql
   SELECT trip_region, AVG(estimated), AVG(actual), 
          AVG((actual - estimated) / estimated * 100) as variance_pct
   FROM trips
   GROUP BY trip_region
   ```

2. Write forecast adapter:
   ```python
   def getImprovedTripEstimate(region, base_estimate):
       """Adjust estimate based on regional variance."""
       historical_var = getRegionalVariance(region)  # e.g., +12%
       return base_estimate * (1 + historical_var)
   ```

3. Integrate: When user plans a trip, show adjusted estimate
4. Test: Does the adjustment match your actual patterns?

**Verification:**
- [ ] Query trips by region (how many for each?)
- [ ] Check if adjustment improves accuracy
- [ ] Verify confidence level (if only 1 trip to Colorado, low confidence)

#### Feature 4: Recurring Transaction Auto-Detection (1–2 days)
**What it does:** App watches historian and suggests "make this recurring?" when it spots patterns.

**Build sequence:**
1. Query: Find patterns in your manual entries
   ```sql
   SELECT merchant, category, ROUND(AVG(amount), 2) as avg_amt,
          COUNT(*) as frequency
   FROM transactions
   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
   GROUP BY merchant, category
   HAVING frequency >= 3 AND STDDEV(amount) < avg_amt * 0.05
   ```

2. Write detector:
   ```python
   def detectRecurringPatterns():
       """Find merchants with 3+ identical-amount entries."""
       # Returns list of (merchant, amount, frequency)
   ```

3. Integrate: In ledger, show "Gym $50 appears monthly. Make recurring?" prompt
4. Test: Do these patterns match your actual recurring expenses?

**Verification:**
- [ ] Run query on your database
- [ ] Identify 5–10 actual recurring expenses you have
- [ ] Verify detector finds them correctly

#### Feature 5: Payoff Confidence Scoring (2 days)
**What it does:** Distance Traveled shows honest confidence in payoff date based on payment history.

**Build sequence:**
1. Query your debt payment data:
   ```sql
   SELECT debt_account_id, 
          COUNT(*) as total_payments,
          SUM(CASE WHEN variance_pct BETWEEN -5 AND 5 THEN 1 ELSE 0 END) as on_track,
          SUM(CASE WHEN late_fee_count > 0 THEN 1 ELSE 0 END) as late_months
   FROM debt_payments
   ```

2. Calculate confidence:
   ```python
   def getPayoffConfidence(debt_account_id):
       """Score 0-100 based on payment history."""
       on_time_pct = on_track / total_payments * 100
       late_fee_impact = late_months * 5  # Deduct 5 per late month
       confidence = on_time_pct - late_fee_impact
       return max(0, min(100, confidence))
   ```

3. Narrative integration: "On track [78% confidence: your payments are 92% on-time, but 1 late month this year]"
4. Test: Does confidence score match your actual payment behavior?

**Verification:**
- [ ] Query your payment history
- [ ] Calculate confidence for each debt account
- [ ] Ask: Does the score feel honest?

#### Feature 6: LLM Gate Improvement (1–2 days)
**What it does:** Distance Traveled narratives improve as gate logs what works and what doesn't.

**Build sequence:**
1. Historian already logs gate flags (from Phase H1)
2. Query the logs: What's the gate flagging most?
   ```sql
   SELECT event_category, COUNT(*) as flag_count
   FROM historian_entries
   WHERE event_category LIKE 'llm_gate%'
   GROUP BY event_category
   ```

3. Hardening: If gate flags "inference_smuggling" 30% of narratives:
   - Tighten the causal-wordlist in prompt
   - Add explicit constraint: "Do not imply causation"
   
4. Test: Run Distance Traveled again after prompt tightening
5. Measure: Did flag rate drop?

**Verification:**
- [ ] Review gate logs from your real data
- [ ] Identify top 3 categories of flags
- [ ] Apply prompt fixes and re-test on same data

---

### Phase H2 Testing (Integrated With Build — 3–4 days)

**For each feature:**
1. **Query your real data** to understand the pattern
2. **Build the adaptive logic** that learns from that pattern
3. **Test against your actual database** to verify it works
4. **Measure:** Does the feature improve the behavior it targets?

**Each feature has a success criterion:**

| Feature | Success Criterion | Test Method |
|---------|------------------|------------|
| Category Suggestions | Accuracy > 85% on 10 most-used merchants | Manual review of suggestions |
| Budget Variance | Adjusted budgets closer to actual | Compare variance before/after |
| Trip Forecasts | Estimate variance < 8% | Historical accuracy check |
| Recurring Detection | Finds 80% of your actual recurring txns | Manual count of recurring expenses |
| Payoff Confidence | Confidence score matches actual payment reliability | Spot-check: does score feel right? |
| LLM Gate | Flag rate decreases after hardening | Pre/post gate-log analysis |

---

### Phase I: Subsystem Verification (2–3 days)
**Same as before, but now includes adaptive features in smoke tests.**

**New smoke test additions:**
```python
test_category_suggestion_accuracy()
test_budget_variance_calculation()
test_trip_forecast_adjustment()
test_recurring_detection_accuracy()
test_payoff_confidence_scoring()
test_llm_gate_improvement()
```

### Phase J: Release Readiness (1 day)
**Same as before.**
- [ ] Version bump to 1.0.0
- [ ] Changelog complete
- [ ] Deploy test on all platforms
- [ ] Go/no-go decision

---

## How Adaptive Learning Works In 1.0

### Category Suggestions
**User adds transaction "Whole Foods $136"**
- App queries: "Have I categorized Whole Foods before?"
- Historian says: "Mostly 'Groceries' (15x), sometimes 'Food' (2x)"
- UI shows: "Groceries (87% match)?" ← pre-filled
- User confirms or corrects
- If corrects: historian logs "suggested Groceries, user picked Food"

### Budget Variance
**User looks at January budget:**
- App calculated: "Dining varies ±28%, recommend budget $452"
- User sees: "$500 budgeted, but historically runs $422–$474. Suggest $550?"
- App shows why: "Last 6 months: $422, $452, $474, $445, $426, $474 (avg variance: +4%)"
- User can accept the buffer or insist on $500

### Trip Forecast
**User plans Colorado trip:**
- App says: "Your Colorado trips average $1,650. Base estimate: $1,500"
- Adjustment reason: "Last 3 trips to CO: estimated $1,200/$1,300/$1,400, actual $1,450/$1,409/$1,462 (avg +15% variance)"
- User sees realistic range, makes better decisions

### Recurring Detection
**Ledger shows:**
- Historian detects: "Netflix $15.99 on 10/5, 11/5, 12/5, 1/5"
- Prompt: "Netflix looks like a monthly subscription. Make it recurring?"
- User clicks yes, recurring is created
- No more manual entry next month

### Payoff Confidence
**Distance Traveled shows:**
> "On track [78% confidence]. You've paid 22/24 months on schedule, but had 1 late payment in Q3 that added $35. At this rate, payoff date is Jan 2027 ±3 weeks."

Not just "on track." Honest about variability.

### LLM Gate Learning
**Gate flags R3 (inference-smuggling) in 28% of narratives**
- Example: "Your food spending rose $40, which may reflect dining out more"
- Problem: "may reflect" is inference-smuggling; user didn't give us that data
- Hardening: Prompt tightened to forbid hedged causation
- Next month: R3 flags drop to 12%

---

## Database Integration For Adaptive Learning

**Key principle:** Code has direct read access to your real database.

**Set up in development:**
1. Point dev environment to your actual Groundwork database (C:\Groundwork\core\groundwork.db)
2. Write exploratory queries:
   ```python
   # In a test script or REPL
   from models import *
   
   # Find all merchants
   merchants = db.session.query(Transaction.merchant).distinct().all()
   
   # Analyze categories
   categories = db.session.query(
       Transaction.category,
       func.count().label('count'),
       func.avg(Transaction.amount).Label('avg_amount')
   ).group_by(Transaction.category).all()
   
   # Check debt payment patterns
   debt_payments = db.session.query(DebtLedgerEntry).filter(
       DebtLedgerEntry.entry_type == 'payment'
   ).all()
   ```

3. Each adaptive feature includes exploratory script:
   - `scripts/explore_categories.py` — understand your category patterns
   - `scripts/explore_budgets.py` — analyze variance per category
   - `scripts/explore_trips.py` — check regional spending
   - `scripts/explore_recurring.py` — find potential recurring txns
   - `scripts/explore_debt_patterns.py` — analyze payment reliability
   - `scripts/explore_gate_logs.py` — review LLM gate misses

4. Each script outputs:
   - Summary of patterns found in your data
   - Validation results (Does suggestion engine work? Does forecast adjust correctly?)
   - Confidence scores

---

## Verification Workflow

**For each adaptive feature:**

1. **Understand:** Run exploratory script, understand your real patterns
2. **Build:** Code the adaptive logic (suggestion, variance, forecast, etc.)
3. **Test:** Run it against your real database
4. **Measure:** Does it work the way you expect?
5. **Integrate:** Wire into UI
6. **Smoke test:** Add to test suite
7. **Ship:** In 1.0.0

**Example for Category Suggestions:**
```bash
# Step 1: Understand your categories
python scripts/explore_categories.py
# Output: "Your top merchants: Whole Foods (Groceries 87%), Target (Groceries 60%, Household 30%), ..."

# Step 2–6: Build, test, integrate (happens in development)

# Step 7: Ship
# Run smoke test: test_category_suggestion_accuracy()
# Deploy to 1.0.0
```

---

## Timeline: Build + Verify + Ship

### Week 1 (Mon–Fri)
- **Mon:** Phase A (data layer)
- **Tue–Wed:** Phase B (debt ledger UI)
- **Thu:** Phase C (recurring drafts)
- **Fri:** Phase D (checking linking)

### Week 2 (Mon–Fri)
- **Mon:** Phase E (payoff integration)
- **Tue–Wed:** Phase F (distance traveled narrative)
- **Thu:** Phase G (testing & polish)
- **Fri:** Phase H1 (historian schema)

### Week 3 (Mon–Fri)
- **Mon:** Phase H2.1 (Category Suggestions — understand + build + test)
- **Tue:** Phase H2.2 (Budget Variance — understand + build + test)
- **Wed:** Phase H2.3 (Trip Forecasts — understand + build + test)
- **Thu:** Phase H2.4 (Recurring Detection + Confidence + Gate Learning)
- **Fri:** Phase I (subsystem verification + adaptive smoke tests)

### Week 4 (Mon)
- **Mon:** Phase J (version bump, deploy, go/no-go) → Ship 1.0.0

---

## 1.0.0 Release Notes

```
Groundwork 1.0.0 is released.

WHAT'S IN THIS RELEASE:
- Complete ledger: CSV/OFX/PDF import, manual entry, reconciliation
- Debt reconciliation: manual entry, recurring payments, plan-synced drafts
- Budget tracking with category alerts
- Debt payoff planning with adaptive narratives
- Net worth tracking
- Trip planning with learning
- Flights API integration
- Auto-import watcher
- Export encryption

NEW IN 1.0: ADAPTIVE LEARNING
- Category suggestions: App learns your merchant categories, suggests them next time
- Budget variance learning: App identifies which categories need buffers based on your history
- Trip forecast improvement: App learns regional spending patterns and improves estimates
- Recurring detection: App spots patterns and suggests recurring transactions
- Payoff confidence scoring: Distance Traveled shows honest confidence based on your payment reliability
- LLM gate improvement: AI narratives improve as system learns from its mistakes

ALL FEATURES VALIDATED AGAINST REAL DATA
Every adaptive feature has been tested and verified on production financial data before shipping.
The system learns from your actual spending patterns, not hypothetical data.

TECHNICAL:
- Local LLM (phi3.5 default) with validation gate — nothing leaves your machine
- Historian system: system records what it learns, so it improves over time
- All numeric figures in Distance Traveled are sourced from your data
- Three-place version control: 1.0.0 → 1.0.1 (bugfixes) → 1.0.2, etc.

REQUIREMENTS:
- Windows 11, macOS (Apple Silicon), Ubuntu 24.04 LTS
- 8GB RAM minimum (16GB+ for local LLM)
- Ollama (auto-installs)

This is 1.0. It's complete. All features are built, tested on real data, and production-ready.
Versions 1.0.1+ will be maintenance/bugfixes only as the world finds edge cases.
```

---

## Post-1.0: How Versioning Works

**1.0.0** → Ship to public  
**1.0.1** → User finds bug in category suggestion, we fix it  
**1.0.2** → User reports trip forecast off by 5%, we investigate and refine  
**1.0.3** → LLM gate flags something weird, we harden prompt  
**...1.0.x** → Accumulate bugfixes and edge-case refinements

**No new features in 1.0.x line.** Each version is a fix to what shipped in 1.0.0.

If a user requests a feature (e.g., "category merging" or "bill reminders"), that goes to 1.1, not 1.0.x.

---

## Success Criteria For 1.0.0 Release

- [ ] Debt reconciliation feature complete and tested
- [ ] Historian infrastructure production-ready
- [ ] Six adaptive features built, each tested against real data
- [ ] Adaptive features validated: suggestion accuracy, variance learning, forecast improvement, detection, confidence, gate improvement
- [ ] Subsystems (ledger, budget, payoff, net worth, import, trips, flights) all passing smoke tests
- [ ] Smoke tests include 6 adaptive features
- [ ] No critical bugs
- [ ] App performs well on all platforms
- [ ] Version 1.0.0 tagged in git
- [ ] Release notes written
- [ ] Changelog complete
- [ ] Deploy test successful
- [ ] Go/no-go decision: GO

---

## The Shift This Represents

**Old model:** Build features, beta test, iterate in next version
**New model:** Build features, test on real data, ship production-grade

**Old model:** "Adaptive learning is a future idea"
**New model:** "Adaptive learning ships with 1.0, proven to work on your actual data"

**Old model:** 1.0 is exploratory; 1.1 is the real release
**New model:** 1.0 is production; 1.0.x is maintenance

This is not a philosophy change. It's a quality and confidence change.

You're not releasing a beta. You're releasing a product that has learned from your own financial life.

