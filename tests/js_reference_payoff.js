// The payoff simulators as app.js shipped them, frozen.
//
// These were the app's own implementation until core/consequence.py replaced
// them (Pillar 1, §7). They are kept here for one purpose: tests/
// test_consequence_parity.py runs 300 random portfolios and 150 PSLF ones
// through both and requires agreement, and that differential is what proves the
// port reproduces the behaviour it was ported from.
//
// The harness used to extract these from static/js/app.js, which was the right
// thing while the app still computed payoffs for itself — two live
// implementations, checked against each other. Now the app asks the engine, so
// there is no second live implementation to check: this file is a fixture, not
// a participant. DO NOT "fix" it to match a change in the engine. If the engine
// intentionally diverges from what shipped, that is a decision to record in the
// parity test, not an edit to make here.

// Extracted verbatim from static/js/app.js when the shipped app stopped
// computing payoffs for itself. See the header of this file.

function _simulatePayoff(extraPerMonth = 0) {
  const today    = new Date();
  const todayKey = today.toISOString().slice(0,7);

  const data = S.debtCards
    .filter(c => !c.paidInFull)
    .map(c => ({
      id:       c.id,
      name:     c.name || 'Card',
      balance:  Math.max(0, _cardBal(c)),
      rate:     Math.max(0, parseFloat(c.rate) || 0),
      minimum:  Math.max(1, parseFloat(c.minimum) || 25),
      pslf:     _pslfIsFlagged(c._dbId || c.id),
      isLease:  (c.debtType || 'credit') === 'lease',
      // endDate as YYYY-MM — simulation stops lease payments after this month
      endMonth: c.endDate ? c.endDate.slice(0,7) : null,
    })).filter(c => {
      // Skip leases whose end date is already past — obligation is done
      if (c.isLease && c.endMonth && c.endMonth < todayKey) return false;
      return c.balance > 0;
    });

  if (!data.length) return null;
  // BUG FIX (July 6): previously read g('monthlyBudget')?.value with no
  // fallback — that field only exists in the DOM on the Debt Payoff page
  // itself, so every call to this function from anywhere else (Dashboard,
  // Before You Buy, Reports) silently used a budget of 0 instead of the
  // user's real committed amount. When the field IS mounted (actively on
  // the Debt Payoff page), sync S.monthlyBudget from it too, so an edit
  // the user just made is immediately available to every other function,
  // not just this page, without waiting for a save round-trip.
  // (July 8: DOM-vs-state logic now lives in the shared _getMonthlyBudget()
  // helper so every caller gets the same fallback, not just this function.)
  const baseBudget = _getMonthlyBudget();
  const budget     = baseBudget + extraPerMonth;
  const totalMin   = data.reduce((s,c) => s+c.minimum, 0);
  if (budget < totalMin) return null;

  // Extra payment priority excludes PSLF loans and leases.
  // Leases have a fixed end date and can't be paid early.
  const sorted = data.filter(c => !c.pslf && !c.isLease).sort((a,b) =>
    S.debtMethod === 'avalanche' ? b.rate - a.rate : a.balance - b.balance
  );

  let bals = data.map(c => c.balance);
  let month = 0, totalInterest = 0;
  // Track sim month as YYYY-MM for lease end-date comparison
  const simStart = new Date(today.getFullYear(), today.getMonth(), 1);

  while (month < MAX_MONTHS && bals.some(b => b > 0.01)) {
    month++;
    const simDate = new Date(simStart.getFullYear(), simStart.getMonth() + month - 1, 1);
    const simKey  = `${simDate.getFullYear()}-${String(simDate.getMonth()+1).padStart(2,'0')}`;
    let extra = budget;
    for (let i = 0; i < data.length; i++) {
      if (bals[i] <= 0) continue;
      // Lease past its end month: obligation ends, zero the balance
      if (data[i].isLease && data[i].endMonth && simKey > data[i].endMonth) {
        bals[i] = 0;
        continue;
      }
      const ic = bals[i] * (data[i].rate / 100 / 12);
      bals[i] += ic;
      totalInterest += ic;
      const pay = Math.min(data[i].minimum, bals[i]);
      bals[i] = Math.max(0, bals[i] - pay);
      extra  -= pay;
    }
    for (const c of sorted) {
      if (extra <= 0.01) break;
      const i = data.indexOf(c);
      if (bals[i] <= 0) continue;
      const apply = Math.min(extra, bals[i]);
      bals[i] = Math.max(0, bals[i] - apply);
      extra -= apply;
    }
  }

  const free = new Date();
  free.setMonth(free.getMonth() + month);
  return {
    months:        month,
    totalInterest: Math.round(totalInterest),
    freeDate:      free.toLocaleDateString('en-US', { month:'short', year:'numeric' }),
    freeDateFull:  free,
  };
}

function _simulatePayoffStrategy(cards, budget, strategy) {
  const todayKey = new Date().toISOString().slice(0,7);
  const simStart = new Date(); simStart.setDate(1);

  const data = cards
    .filter(c => !c.paidInFull)
    .map(c => ({
      name:     c.name || 'Card',
      balance:  Math.max(0, _cardBal(c)),
      rate:     Math.max(0, parseFloat(c.rate)||0),
      minimum:  Math.max(1, parseFloat(c.minimum)||25),
      isLease:  (c.debtType || 'credit') === 'lease',
      endMonth: c.endDate ? c.endDate.slice(0,7) : null,
    }))
    .filter(c => {
      if (c.isLease && c.endMonth && c.endMonth < todayKey) return false;
      return c.balance > 0;
    });

  if (!data.length) return null;
  const totalMin = data.reduce((s,c) => s+c.minimum, 0);
  if (budget < totalMin) return null;

  const order = [...data].filter(c => !c.isLease).sort((a,b) =>
    strategy === 'snowball' ? a.balance - b.balance : b.rate - a.rate);

  let bals = data.map(c => c.balance);
  let month = 0, totalInt = 0;
  let firstClearedMonth = null, firstClearedName = null;

  while (month < 360 && bals.some(b => b > 0.01)) {
    month++;
    const simDate = new Date(simStart.getFullYear(), simStart.getMonth() + month - 1, 1);
    const simKey  = `${simDate.getFullYear()}-${String(simDate.getMonth()+1).padStart(2,'0')}`;
    let extra = budget;
    for (let i = 0; i < data.length; i++) {
      if (bals[i] <= 0) continue;
      if (data[i].isLease && data[i].endMonth && simKey > data[i].endMonth) {
        bals[i] = 0;
        continue;
      }
      const ic = bals[i]*(data[i].rate/100/12);
      bals[i] += ic; totalInt += ic;
      const pay = Math.min(data[i].minimum, bals[i]);
      bals[i] = Math.max(0, bals[i]-pay);
      extra  -= pay;
    }
    for (const c of order) {
      if (extra <= 0.01) break;
      const i = data.indexOf(c);
      if (bals[i] <= 0) continue;
      const apply = Math.min(extra, bals[i]);
      bals[i] = Math.max(0, bals[i]-apply);
      extra  -= apply;
    }
    if (firstClearedMonth === null) {
      for (let i = 0; i < data.length; i++) {
        if (bals[i] <= 0.01) { firstClearedMonth = month; firstClearedName = data[i].name; break; }
      }
    }
  }

  const free = new Date();
  free.setMonth(free.getMonth()+month);
  return {
    months:            month,
    totalInterest:     Math.round(totalInt),
    freeDate:          free.toLocaleDateString('en-US', {month:'short', year:'numeric'}),
    firstClearedMonth,
    firstClearedName,
  };
}
