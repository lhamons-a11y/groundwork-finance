"""Two wrong figures found in the AI-off audit (2026-10-12), fixed 2026-10-13 (Rob: "did the calculations in the
dashboard get fixed?").

    1  the dashboard projection's lever: this calendar month only, and never a category that is not a lever - the
       necessity floor, a contract payment, or money that is not spending (on Rob's data it offered "Debt",
       $18,540 read as this month, as a $16,729-a-month cut)
    2  the reports count transfers on neither side: September 2026's Monthly Report had Transfer $5,877.29 as its
       top "spending" and a net of -$5,012.41 where the month was +$864.88
"""
import json
import re
import shutil
import subprocess


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    app = ctx.app_src
    import server
    nl = set(server.not_levers(['Debt', 'Interest / Fees', 'Transfer', 'Savings', 'Rent / Mortgage', 'Groceries',
                                'Auto Insurance', 'Car Lease Payment', 'Restaurants', 'Shopping', 'Car Maintenance',
                                "Rob's Income", 'Entertainment'], ["Rob's Income"]))
    check(f"s221 1 never a lever: debt, interest and fees, transfers, savings, the floor, contract payments, income ({sorted(nl)})",
          {'Debt', 'Interest / Fees', 'Transfer', 'Savings', 'Rent / Mortgage', 'Groceries', 'Auto Insurance',
           'Car Lease Payment', "Rob's Income"} <= nl and not ({'Restaurants', 'Shopping', 'Car Maintenance', 'Entertainment'} & nl))
    r = (c.get('/api/budget/not-levers', headers=H).get_json() or {}).get('data') or {}
    check('s221 1 the page reads the one list from the server', isinstance(r.get('not_levers'), list))

    fn = re.search(r'^function _findHighLeverageCategory\(txns\) \{.*?^\}', app, re.M | re.S).group(0)
    check('s221 1 this calendar month from its own transactions, never the period the dashboard shows; nothing offered without the list',
          "(t.date||'').slice(0,7)===thisMonth" in fn and 'txns.filter' not in fn and 'if (!_notLevers) return null;' in fn
          and 'if(!lever(cat))continue;' in fn)
    node = shutil.which('node')
    if node:
        prog = ("const S={transactions:[" +
                "{type:'debit',date:'2026-10-03',category:'Debt',amount:18000}," +
                "{type:'debit',date:'2026-09-03',category:'Debt',amount:1800}," +
                "{type:'debit',date:'2026-10-04',category:'Restaurants',amount:400}," +
                "{type:'debit',date:'2026-09-04',category:'Restaurants',amount:150}," +
                "{type:'debit',date:'2025-10-04',category:'Restaurants',amount:9999}],expenses:[]};\n"
                "const _notLevers=new Set(['debt']);\n" + fn.replace('const now=new Date()', "const now=new Date('2026-10-13T12:00:00')") +
                "\nconsole.log(JSON.stringify(_findHighLeverageCategory([])));")
        out = subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8', timeout=30)
        got = json.loads(out.stdout.strip() or 'null') if out.returncode == 0 else out.stderr[-200:]
        check(f"s221 1 run in Node: a $18,000 debt payment is never the lever; last year's same month is not this month ({got})",
              isinstance(got, dict) and got.get('category') == 'Restaurants' and got.get('currentSpend') == 400 and got.get('over') == 250)

    mon = app.split('function _rcMonthlyRefreshPreview() {')[1].split('\n}\n')[0]
    inc = app.split('function _rcRenderIncomeSavings() {')[1].split('\n}\n')[0]
    prev = app.split('function updateReportPreview() {')[1].split('\n}\n')[0]
    check('s221 2 the Monthly Report, Income & Savings and the report preview count transfers on neither side, and the report says what moved',
          'txns.filter(_isSpend)' in mon and 'txns.filter(_isEarn)' in mon and "type==='debit').reduce" not in mon
          and 'moved between your own accounts this month' in mon
          and '_isEarn(t)&&' in inc and '_isSpend(t)&&' in inc and 'txns.filter(_isEarn)' in prev and 'txns.filter(_isSpend)' in prev)
    tc = re.search(r'^function _isTransferCat\(name\) \{.*?^\}', app, re.M | re.S)
    check("s221 2 one transfer test on the page, as the server's: named Transfer, typed transfer, or under one",
          tc is not None and "c.type === 'transfer'" in tc.group(0) and "p.type === 'transfer'" in tc.group(0)
          and 'return !_isTransferCat(t.category);' in app)
