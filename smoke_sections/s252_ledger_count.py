"""The Ledger's header counts the rows it shows (Rob 2026-10-21: "fix the Ledger count ignoring the search box").

Found while building item 107: a search for StreamBox showed 9 rows under "All months · matching filters · 241
transactions", and typing a search left the header on the month's 36 while it showed 6. The header (updateLedgerStats)
applied only the account filter, and typing, the category filter and the uncleared toggle never called it at all.

    1  one function, _ledgerFilteredTxns(), picks the rows; renderLedger() lists them and updateLedgerStats() counts and
       totals the same ones
    2  renderLedger() updates the header itself, so every path that changes the rows changes the count
"""
import re
import shutil
import subprocess


def _fn(src, name):
    i = src.index(f'function {name}(')
    j = src.index('\n}\n', i)
    return src[i:j]


def run(ctx):
    check, app = ctx.check, ctx.app_src
    pick = _fn(app, '_ledgerFilteredTxns')
    render = _fn(app, 'renderLedger')
    stats = _fn(app, 'updateLedgerStats')
    check('s252 1 one function picks the Ledger\'s rows: the search, category, type, account and uncleared-only filters',
          all(x in pick for x in ("g('ledgerSearch')", "g('ledgerCatFilter')", "g('ledgerTypeFilter')",
                                  "g('ledgerAccountFilter')", '_ledgerShowUnclearedOnly', '_ledgerTermMatch(')))
    check('s252 1 the rows and the header both come from it, and neither filters on its own',
          'let txns = _ledgerFilteredTxns();' in render and 'let txns = _ledgerFilteredTxns();' in stats
          and 'normSearch' not in render and 'normSearch' not in stats
          and not re.search(r'txns = txns\.filter\(t => t\.account === acct\)', render + stats))
    check('s252 2 renderLedger() updates the header itself, before any early return',
          'updateLedgerStats();' in render
          and render.index('updateLedgerStats();') < render.index('if (!txns.length)'))
    code = re.sub(r'//[^\n]*', '', stats)
    check('s252 2 and updateLedgerStats() never calls back into renderLedger()', 'renderLedger(' not in code)
    if shutil.which('node'):
        js = ("const S={transactions:[{merchant:'StreamBox',description:'',category:'x',type:'debit',amount:1,account:'A',"
              "cleared:true,date:'2026-10-03'},{merchant:'Other',description:'',category:'y',type:'debit',amount:2,account:'B',"
              "cleared:true,date:'2026-10-04'}]};let _ledgerShowUnclearedOnly=false;const v={ledgerSearch:'streambox'};"
              "const g=id=>({value:v[id]||''});const _ledgerHasActiveFilter=()=>true;const _ledgerTxnsForSelectedMonth=()=>[];"
              "const _catChildren=()=>[];" + _fn(app, '_ledgerTermMatch') + "\n}\n" + pick + "\n}\nconsole.log(_ledgerFilteredTxns().length)")
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True)
        check(f's252 1 run in Node: a search keeps only its rows ({r.stdout.strip()})', r.stdout.strip() == '1')
