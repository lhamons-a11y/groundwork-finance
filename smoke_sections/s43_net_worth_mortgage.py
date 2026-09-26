"""V9: Net Worth counts a mortgage once.

Two double counts. Inside Net Worth, assets held home *equity* (value minus
mortgage) while liabilities added the mortgage again, so a $300,000 home with a
$187,000 mortgage came out at -$74,000 instead of +$113,000 - for anyone who
entered both. And since V3 a mortgage can also be a debt on the Debt page, which
Net Worth added to its own mortgage field. Now assets hold the full home value,
liabilities the mortgage once, and a Mortgage-type debt wins over the Net Worth
field. The helper is run for real, under node, extracted from app.js.
"""
import json
import subprocess
from pathlib import Path


def _extract(src, name):
    s = src.index('function ' + name + '(')
    i = src.index('{', s)
    d = 0
    for p in range(i, len(src)):
        if src[p] == '{':
            d += 1
        elif src[p] == '}':
            d -= 1
            if d == 0:
                return src[s:p + 1]
    raise ValueError('unbalanced ' + name)


def run(ctx):
    check = ctx.check
    app_js = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')

    harness = '\n'.join([
        _extract(app_js, '_cardBal'),
        _extract(app_js, '_nwMortgageInfo'),
        """
const cases = {
  typedOnly:      { typed: 187000, cards: [] },
  debtPage:       { typed: 187000, cards: [{ name: 'Home', debtType: 'mortgage', currentBal: '186500' }] },
  debtPageNoTyped:{ typed: 0,      cards: [{ name: 'Home', debtType: 'mortgage', currentBal: '186500' }] },
  loanOnly:       { typed: 187000, cards: [{ name: 'Home?', debtType: 'loan', currentBal: '186500' }] },
  paidMortgage:   { typed: 187000, cards: [{ name: 'Home', debtType: 'mortgage', currentBal: '186500', paidInFull: true }] },
};
const out = {};
for (const [k, c] of Object.entries(cases)) {
  global.S = { debtCards: c.cards, netWorth: {} };
  out[k] = _nwMortgageInfo(c.typed);
}
console.log(JSON.stringify(out));
"""])
    try:
        proc = subprocess.run(['node', '-e', harness], capture_output=True, text=True, timeout=60)
        res = json.loads(proc.stdout.strip() or '{}')
    except Exception as e:                      # noqa: BLE001
        res = {}
        print(f'        node harness failed: {e}')

    t, d, dn, l, pd = (res.get(k, {}) for k in ('typedOnly', 'debtPage', 'debtPageNoTyped', 'loanOnly', 'paidMortgage'))
    check('V9: with only the Net Worth field, the mortgage is counted once from it',
          t.get('amount') == 187000 and t.get('counted') == 187000 and t.get('fromDebtPage') is False)
    check('with a Mortgage-type debt, Net Worth uses its balance and does not count the field again',
          d.get('amount') == 186500 and d.get('counted') == 0 and d.get('fromDebtPage') is True)
    check('the same when the Net Worth field is empty',
          dn.get('amount') == 186500 and dn.get('counted') == 0)
    check('a plain Loan is not taken for a mortgage (it cannot be recognised)',
          l.get('fromDebtPage') is False and l.get('counted') == 187000)
    check('a paid-off Mortgage debt does not take over',
          pd.get('fromDebtPage') is False and pd.get('counted') == 187000)

    upd = _extract(app_js, 'updateNetWorth')
    check('the Net Worth page counts the full home value as the asset, not equity',
          'const totalAssets      = savings + totalInvestments + cash + homeValue + pensionTotal;' in upd
          and 'cash + homeEquity + pensionTotal' not in upd)
    check('and the mortgage once as a liability (not again when it is on the Debt page)',
          'const totalLiab        = debtBals + _m.counted;' in upd and 'debtBals + mortgage;' not in upd)
    check('and shows equity as information, not as a second asset',
          "['Home value',               homeValue]" in upd and "['Home equity',              homeEquity]" not in upd)
    snap = _extract(app_js, 'autoSnapshotNetWorthIfDue')
    check('the monthly snapshot uses the same corrected totals',
          'cash + homeValue + pensionTotal' in snap and 'debtBals + _m.counted' in snap)
    check('no Net Worth total adds the raw field on top of a Debt-page mortgage any more',
          '(nw.mortgage||0)+totalDebt' not in app_js and '-(nw.mortgage||0)-totalDebt' not in app_js
          and '(nw.mortgage||0)+_activeDebtCards()' not in app_js)
    check('while the field shows the Debt page\'s mortgage, what is kept is what the user typed',
          'mortgageEl.readOnly ? mortgageEl.dataset.typed : mortgageEl.value' in upd)
