// Runs the REAL _simulatePayoffStrategy from app.js against stdin scenarios, so
// the Python port is compared to the shipped code rather than to a description
// of it. The function is extracted verbatim at runtime; if app.js changes, this
// picks the change up and the parity test fails loudly.
const fs = require('fs');
const src = fs.readFileSync('static/js/app.js', 'utf8');

const start = src.indexOf('function _simulatePayoffStrategy(');
if (start === -1) { console.error('EXTRACT_FAIL: _simulatePayoffStrategy not found'); process.exit(2); }
// Balance braces from the function's opening brace to find its end.
let i = src.indexOf('{', start), depth = 0, end = -1;
for (let p = i; p < src.length; p++) {
  if (src[p] === '{') depth++;
  else if (src[p] === '}') { depth--; if (depth === 0) { end = p + 1; break; } }
}
if (end === -1) { console.error('EXTRACT_FAIL: unbalanced braces'); process.exit(2); }
const body = src.slice(start, end);

// _cardBal is app state plumbing; the scenarios supply balances directly.
const _cardBal = (c) => c.balance;
const fn = new Function('_cardBal', body + '; return _simulatePayoffStrategy;')(_cardBal);

const scenarios = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = scenarios.map(s => {
  const r = fn(s.cards, s.budget, s.strategy);
  return r === null ? null : { months: r.months, totalInterest: r.totalInterest };
});
process.stdout.write(JSON.stringify(out));
