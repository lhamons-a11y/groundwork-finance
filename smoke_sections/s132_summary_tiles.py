"""The summary tiles meet the attention standard (`gw 2.0/SUMMARY_TILES_STANDARD.md`, item 27, ruled 2026-09-30).

    T1  completeness before any pace: an imported account with nothing imported since the month began stops the
        pace sentence and is named; a hand-kept account never counts
    T2  This month says its arithmetic - no On track / Watch it / Over budget, no coloured border
    T3  the greeting line is one upcoming fact from the record, or nothing
    T4  the DTI ratio with the question it answers - no lender-ready, no warning glyph
    T5  two payoff dates, not "behind schedule"
    T6  a source line on the tiles
    T7  What changed loses its good / not-good marks; the donut names what it covers
    T8  Coming up shows the next occurrence, this month or next
    T9  2.0 only, through the seam
    St10 a lexicon test over every sentence the tiles produce, with a mutation
"""
import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta

_RUN = [0]


def _node(base):
    node = shutil.which('node')
    if not node:
        return None
    path = str(base.joinpath('static/js/teaching/tiletext.js')).replace('\\', '/')
    prog = f"""
const T = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), date: s => s, monthYear: d => d.toISOString().slice(0, 7)}};
const out = {{}};
out.gap = T.month({{spent: 0, daysGone: 30, daysInMonth: 30, budget: 4000, monthName: 'September',
                    behind: [{{account: 'Checking', last_import: '2026-09-04'}}]}}, F);
out.under = T.month({{spent: 1240, daysGone: 12, daysInMonth: 30, budget: 4000, monthName: 'September', behind: []}}, F);
out.over = T.month({{spent: 3000, daysGone: 12, daysInMonth: 30, budget: 4000, monthName: 'September', behind: []}}, F);
out.rent = T.month({{spent: 2890, bills: 1650, daysGone: 20, daysInMonth: 30, budget: 4000, monthName: 'September', behind: []}}, F);
out.nobudget = T.month({{spent: 300, daysGone: 12, daysInMonth: 30, budget: 0, monthName: 'September', behind: []}}, F);
out.dti = T.dti(41.4);
out.dti_none = T.dti(null);
out.plan = T.plan({{computable: true, monthsDelta: -3, dateThen: new Date(Date.UTC(2027, 11, 15)), dateNow: new Date(Date.UTC(2028, 2, 15))}}, F);
out.plan_same = T.plan({{computable: true, monthsDelta: 0, dateThen: new Date(Date.UTC(2028, 2, 15)), dateNow: new Date(Date.UTC(2028, 2, 15))}}, F);
out.plan_none = T.plan({{computable: false}}, F);
out.greet_pay = T.greetingFact({{kind: 'payment_due', title: 'Visa', amount: 85, due: '2026-10-03'}}, F);
out.greet_none = T.greetingFact(undefined, F);
const all = [out.gap.head, out.gap.body, out.under.body, out.over.body, out.nobudget.body, out.dti, out.plan, out.plan_same, out.greet_pay].join(' ');
out.banned = T.banned(all);
out.mutation = T.banned(all + ' On track - keep going!');
console.log(JSON.stringify(out));
"""
    r = subprocess.run([node, '-e', prog], capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', r.stderr[:400])
        return {}


def run(ctx):
    check = ctx.check
    base = ctx.BASE
    o = _node(base)
    check('s132 node is available to run the tiles\' words (skip the next if not)', o is not None)
    if o is not None:
        check('s132 St1 T1 an account behind this month stops the pace sentence and is named with its last import',
              'Checking (last import 2026-09-04)' in o['gap']['body'] and "isn't known yet" in o['gap']['body']
              and 'At that rate' not in o['gap']['body'])
        check('s132 St2 T2 this month as arithmetic: spent, days, a straight-line projection labelled as one, the budget',
              o['under']['body'] == 'Spent $1240.00 in 12 of 30 days. At that rate - a straight line, not a forecast - '
                                    'the month ends near $3100.00 against $4000.00 of budgeted income.')
        check('s132 St3 T2 the same sentence above budget - no verdict, just the numbers',
              'ends near $7500.00 against $4000.00 of budgeted income' in o['over']['body'])
        check('s132 once-a-month bills are counted once, not at the daily rate ($1,650 rent + $1,240 over 20 of 30 days)',
              o['rent']['body'] == 'Spent $2890.00 in 20 of 30 days, $1650.00 of it once-a-month bills. Counting those once '
                                   'and the rest at that rate - a straight line, not a forecast - the month ends near '
                                   '$3510.00 against $4000.00 of budgeted income.')
        check('s132 no budgeted income: the spending is stated, and the absence of a comparison said plainly',
              'no budgeted income yet' in o['nobudget']['body'])
        check('s132 St7 T4 the ratio and the question it answers',
              o['dti'] == 'Debt payments are 41% of income - the debt-to-income ratio lenders look at, where 36% is a common cut-off.'
              and o['dti_none'] == '')
        check('s132 St8 T5 two payoff dates, not a schedule verdict (and one date when they agree, nothing when unknown)',
              o['plan'] == "Your first recorded balances pointed to debt-free around 2027-12; today's point to 2028-03."
              and 'both point to debt-free around 2028-03' in o['plan_same'] and o['plan_none'] == '')
        check('s132 St5/St6 T3 the greeting line: one upcoming fact, or nothing',
              o['greet_pay'] == 'Visa: $85.00 due 2026-10-03, not yet recorded as paid.' and o['greet_none'] == '')
        check('s132 St10 no tile sentence carries a verdict or advice word', o['banned'] == [])
        check('s132 mutation caught: "On track - keep going!" added to a tile', set(o['mutation']) >= {'on track', 'keep going'})

    # T1 on the server: which imported accounts have nothing imported since the month began.
    from core.database import Account, Transaction
    import server
    _RUN[0] += 1
    n = _RUN[0]
    now = datetime.now()
    start = datetime(now.year, now.month, 1)
    with ctx.dbs() as s:
        old, cur, hand = Account(name=f'S132 Old {n}'), Account(name=f'S132 Current {n}'), Account(name=f'S132 Hand {n}')
        s.add_all([old, cur, hand])
        s.flush()
        s.add(Transaction(date=(start - timedelta(days=10)).date(), description='S132', amount=1, type='debit',
                          account_id=old.id, source='csv', created_at=start - timedelta(days=2)))
        s.add(Transaction(date=start.date(), description='S132', amount=1, type='debit',
                          account_id=cur.id, source='qfx', created_at=start + timedelta(hours=1)))
        s.add(Transaction(date=(start - timedelta(days=40)).date(), description='S132', amount=1, type='debit',
                          account_id=hand.id, source='manual', created_at=start - timedelta(days=40)))
        s.commit()
        ids = (old.id, cur.id, hand.id)
        behind = {b['account_id'] for b in server.imports_behind_this_month(s)}
    check('s132 St1 T1 an imported account with nothing since the month began is behind; one imported this month is not',
          ids[0] in behind and ids[1] not in behind)
    check('s132 St4 T1 an account kept by hand is never counted as missing', ids[2] not in behind)
    r = ctx.c.get('/api/dashboard/attention/imports', headers=ctx.HJ)
    d = (r.get_json() or {}).get('data') or {}
    check('s132 the dashboard\'s import facts carry the month\'s completeness list', 'behind_this_month' in d)

    dash = base.joinpath('static/js/teaching/dashboard.js').read_text(encoding='utf-8')
    js = base.joinpath('static/js/teaching/tiles.js').read_text(encoding='utf-8')
    check('s132 T2 the verdict and its coloured border are replaced in 2.0',
          "v.textContent = m.head" in js and "card.style.borderColor = ''" in js)
    check('s132 T3 the greeting line comes from the record\'s first upcoming fact',
          'T.greetingFact(items && items[0], F)' in js)
    check('s132 T5 "behind / ahead of schedule" is replaced by the two dates', 'T.plan(' in js and '(ahead of|behind) schedule' in js)
    check('s132 T6 every tile gets a source line', all(f"_source('{t}'" in js for t in (
        'dashHealthCard', 'dashHeroCard', 'dashWhatChanged', 'dashDonutCard', 'dashFreedMinimumsCard', 'dashUpcomingCard')))
    check('s132 T8 Coming up uses the next occurrence: the unpaid payments dashboard.js measured with the attention rules',
          'var payments = A.paymentsDue(' in dash and '_tiles(imports, items, payments)' in dash
          and '(payments || []).map(' in js.split('// Coming up (T8)', 1)[-1])
    # Found in the page run: modules load in file-name order, so a load-time lookup of a later module finds
    # nothing and the tiles silently keep their old verdicts. Pinned: both lookups happen at render.
    check('s132 modules are found when the tiles render, not at load (file-name load order)',
          'function _tiletext()' in js and 'if (!_tiletext())' in js and 'function _tiles(' in dash
          and "x.name === 'tiles'" in dash.split('function _tiles(', 1)[1])
    check('s132 T9 1.x untouched: app.js and index.html know nothing of the tiles\' new words',
          'tiletext' not in ctx.app_src and '_retext' not in ctx.app_src
          and 'tiletext' not in base.joinpath('static/index.html').read_text(encoding='utf-8'))
