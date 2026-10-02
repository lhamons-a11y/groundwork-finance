"""The shared budget helper `_rowMonth` (BUDGET_MONTH_AMOUNT.md M7; Rob 2026-10-02), on every line.

1.x's server never sends a month figure, so on 1.x every row's amount for this month is its saved amount - the helper
changes nothing there. 2.0 sends month_amount for a followed estimate (s141 tests that side). And on both lines no
write path sends anything but the saved amount.
"""
import json
import re
import shutil
import subprocess


def run(ctx):
    check = ctx.check
    app = ctx.app_src
    m = re.search(r'^function _rowMonth\(e\) \{.*?^\}', app, re.M | re.S)
    check('s66 the helper exists, once', m is not None and app.count('function _rowMonth(') == 1)
    node = shutil.which('node')
    if m and node:
        prog = m.group(0) + "\nconsole.log(JSON.stringify([_rowMonth({amount: 120}), _rowMonth({amount: '95.5'}),"
        prog += " _rowMonth({amount: 120, month_amount: null}), _rowMonth({amount: 120, month_amount: 142})]));"
        r = subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8', timeout=30)
        check('s66 no month figure (always, on 1.x) means the saved amount; a month figure is used as sent',
              json.loads(r.stdout.strip() or '[]') == [120, 95.5, 120, 142])
    sync = app[app.index('async function _syncBudgetItemsToDb('):]
    sync = sync[:sync.index('\n}\n')]
    check('s66 the whole-list save sends the saved amount, never this month\'s figure',
          'amount: item.amount' in sync and '_rowMonth' not in sync
          and not any('month_amount' in p or '_rowMonth' in p for p in re.findall(r'API\.(?:patch|post|put)\([^;]*', app)))
