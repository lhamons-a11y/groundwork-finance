// Runs the REAL payoff simulators from app.js against stdin scenarios, so the
// Python port is compared to the shipped code rather than to a description of
// it. Functions are extracted verbatim at runtime by brace-balancing; if app.js
// changes, this picks the change up and parity fails loudly.
//
// Two targets, because app.js has two LIVE simulators:
//   _simulatePayoffStrategy(cards, budget, strategy) — parameterised, no PSLF
//   _simulatePayoff(extraPerMonth)                   — app state, PSLF-aware
// (A third, _simulatePayoffFromRows, was dead code and was removed.)
//
// UPDATE: app.js no longer computes payoffs — it asks the engine. The simulators
// it used to carry are frozen in tests/js_reference_payoff.js, and this reads
// them from there. The differential now proves the port still reproduces the
// implementation it was ported from, rather than that two live implementations
// agree; there is only one live implementation now, which was the point.
const fs = require('fs');
const src = fs.readFileSync('tests/js_reference_payoff.js', 'utf8');

function extract(name) {
  const s = src.indexOf('function ' + name + '(');
  if (s === -1) { console.error('EXTRACT_FAIL: ' + name + ' not found'); process.exit(2); }
  let i = src.indexOf('{', s), d = 0, e = -1;
  for (let p = i; p < src.length; p++) {
    if (src[p] === '{') d++;
    else if (src[p] === '}') { d--; if (d === 0) { e = p + 1; break; } }
  }
  if (e === -1) { console.error('EXTRACT_FAIL: unbalanced braces in ' + name); process.exit(2); }
  return src.slice(s, e);
}

const scenarios = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = scenarios.map(s => {
  const S = { debtCards: s.cards, debtMethod: s.strategy };
  const flagged = new Set((s.cards || []).filter(c => c.pslf).map(c => c.id));
  const build = (name) => new Function(
    '_cardBal', '_pslfIsFlagged', '_getMonthlyBudget', 'S', 'MAX_MONTHS',
    extract(name) + '; return ' + name + ';'
  )(c => c.balance, k => flagged.has(k), () => s.budget, S, 360);

  const r = (s.target === 'stateful')
    ? build('_simulatePayoff')(0)
    : build('_simulatePayoffStrategy')(s.cards, s.budget, s.strategy);
  return r === null ? null : { months: r.months, totalInterest: r.totalInterest };
});
process.stdout.write(JSON.stringify(out));
