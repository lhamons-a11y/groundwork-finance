"""The dashboard: your summary, and what needs attention (`gw 2.0/DASHBOARD_SUMMARY_ATTENTION.md`, ruled
2026-09-27, authorised 2026-09-30). Cases Da1-Da10 where this build reaches them.

    the rule     usage never creates, ranks, or implies an attention item - nothing on the dashboard's path
                 reads, counts or stores a view, a click or a visit (structural, with mutations)
    attention    exactly three kinds (a fourth is refused by construction, Da10), each a dated fact with its
                 source: an unpaid payment due within 7 days, an account not imported for 3 weeks (hand-kept
                 accounts never listed - completeness first), a conclusion blocked by missing data
    speaking up  attention reads nothing of the Speaking up dial or Appendix A's caps (ruling 2)
    dismissal    stored as the user's act, keyed by the fact itself: a changed fact returns the item (ruling 3)
    tiles        arranged by the user only - pin / hide / reorder, only known tiles, stored as their setting
    retired      Current priority hidden in 2.0 (ruling 5); 1.x untouched - app.js and index.html unchanged
                 (ruling 6)
"""
import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta

_RUN = [0]


def _node_cases(base):
    node = shutil.which('node')
    if not node:
        return None
    path = str(base.joinpath('static/js/teaching/attention.js')).replace('\\', '/')
    prog = f"""
const A = require({json.dumps(path)});
const out = {{}};
const today = new Date(2026, 8, 28);           // 28 Sep 2026
const cards = [{{id: 1, name: 'Visa', dueDay: 2, minimum: 45}},     // next due 2 Oct: in 4 days
               {{id: 2, name: 'Store', dueDay: 30, minimum: 25}},   // 30 Sep: in 2 days
               {{id: 3, name: 'Loan', dueDay: 20, minimum: 300}},   // 20 Oct: 22 days away
               {{id: 4, name: 'Paid', dueDay: 29, minimum: 60}},    // 29 Sep, but paid
               {{id: 5, name: 'NoDay', dueDay: null, minimum: 10}}];
const paid = (c, m) => c.id === 4 && m === '2026-09';
const p = A.paymentsDue(cards, today, paid);
out.due = p.map(i => [i.subject, i.due, i.days]);
out.kinds = A.KINDS;
const imp = A.importsStale([{{account_id: 7, account: 'Checking', last_import: '2026-09-01', days: 27}}]);
const conf = {{claims: {{networth: {{claim: 'networth', label: 'Net worth', status: 'insufficient',
  checks: [{{key: 'balances', label: 'Account balances', state: 'fail', detail: 'not verified'}}]}},
  spending: {{claim: 'spending', label: 'Spending patterns', status: 'ready', checks: []}}}}}};
const bl = A.blockedConclusions(conf, true);
out.blocked = bl.map(i => [i.subject, i.missing]);
out.blocked_no_record = A.blockedConclusions(conf, false).length;
const all = A.build({{payments: p, imports: imp, blocked: bl}}, []);
out.order = all.map(i => i.kind + ':' + i.subject);
const fpStore = A.fingerprint(p.find(i => i.subject === '2'));
out.dismissed = A.build({{payments: p, imports: imp, blocked: bl}}, [fpStore]).map(i => i.subject);
const moved = A.paymentsDue([{{id: 2, name: 'Store', dueDay: 30, minimum: 35}}], today, paid);
out.changed_fact_returns = A.build({{payments: moved}}, [fpStore]).length;
try {{ A.build({{payments: [{{kind: 'engagement_nudge', subject: 'x', fact: 'y'}}]}}, []); out.fourth = 'accepted'; }}
catch (e) {{ out.fourth = 'refused'; }}
console.log(JSON.stringify(out));
"""
    r = subprocess.run([node, '-e', prog], capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', r.stderr[:400])
        return {}


def _server_cases(c, HJ, dbs):
    from core.database import Account, Transaction
    import server
    _RUN[0] += 1
    n = _RUN[0]
    out = {}
    now = datetime.utcnow()
    with dbs() as s:
        stale = Account(name=f'S131 Stale {n}')
        fresh = Account(name=f'S131 Fresh {n}')
        hand = Account(name=f'S131 Hand {n}')
        s.add_all([stale, fresh, hand])
        s.flush()
        s.add(Transaction(date=(now - timedelta(days=30)).date(), description='S131', amount=5, type='debit',
                          account_id=stale.id, source='csv', created_at=now - timedelta(days=25)))
        s.add(Transaction(date=(now - timedelta(days=40)).date(), description='S131', amount=5, type='debit',
                          account_id=fresh.id, source='qfx', created_at=now - timedelta(days=3)))
        s.add(Transaction(date=(now - timedelta(days=90)).date(), description='S131', amount=5, type='debit',
                          account_id=hand.id, source='manual', created_at=now - timedelta(days=90)))
        s.commit()
        ids = (stale.id, fresh.id, hand.id)
    r = c.get('/api/dashboard/attention/imports', headers=HJ)
    got = {x['account_id']: x for x in ((r.get_json() or {}).get('data') or {}).get('stale', [])}
    out['Da5 an account last imported 25 days ago is listed, with its date and days'] = (
        ids[0] in got and got[ids[0]]['days'] == 25 and got[ids[0]]['account'] == f'S131 Stale {n}')
    out['an account imported 3 days ago is not listed - a quiet account is not a late one'] = ids[1] not in got
    out['completeness first: an account kept by hand has no import to be late, and is never listed'] = ids[2] not in got

    r = c.put('/api/dashboard/layout', headers=HJ, data=json.dumps(
        {'order': ['dashDonutCard', 'dashHealthCard'], 'pinned': ['dashDonutCard'], 'hidden': ['dashHeroCard']}))
    p = (c.get('/api/dashboard/prefs', headers=HJ).get_json() or {}).get('data') or {}
    out['Da2 the user\'s arrangement is stored as their setting and read back exactly'] = (
        r.status_code == 200 and {k: v for k, v in (p.get('layout') or {}).items() if k != 'added'}
        == {'order': ['dashDonutCard', 'dashHealthCard'], 'pinned': ['dashDonutCard'], 'hidden': ['dashHeroCard']})
    r = c.put('/api/dashboard/layout', headers=HJ, data=json.dumps({'order': ['dashCurrentPriority']}))
    out['only known tiles can be arranged - Current priority is not one (retired)'] = r.status_code == 400
    r = c.post('/api/dashboard/dismiss', headers=HJ, data=json.dumps({'fingerprint': 'payment_due|2|2026-09-30|25.00'}))
    r2 = c.post('/api/dashboard/dismiss', headers=HJ, data=json.dumps({'fingerprint': 'most_opened|x|y'}))
    p = (c.get('/api/dashboard/prefs', headers=HJ).get_json() or {}).get('data') or {}
    out['Da9 a dismissal is stored as the user\'s act, keyed by the fact; only ruled kinds can be dismissed'] = (
        r.status_code == 200 and 'payment_due|2|2026-09-30|25.00' in p.get('dismissed', []) and r2.status_code == 400)
    rules = [str(r) for r in c.application.url_map.iter_rules() if '/api/dashboard' in str(r)]
    out['the dashboard\'s routes are its prefs, layout, dismissals and import facts - nothing that records use'] = (
        sorted(rules) == ['/api/dashboard/add', '/api/dashboard/ask', '/api/dashboard/attention/imports',
                          '/api/dashboard/dismiss', '/api/dashboard/investments', '/api/dashboard/layout',
                          '/api/dashboard/prefs', '/api/dashboard/requests/delete', '/api/dashboard/tile/category',
                          '/api/dashboard/tile/energy', '/api/dashboard/tile/funds', '/api/dashboard/tile/net-worth',
                          '/api/dashboard/tile/picture', '/api/dashboard/tile/recurring'])
    return out


_USAGE = r"engagement|budget_reviewed|session_start|session_end|proactive_(shown|dismissed)|localStorage|sessionStorage|" \
         r"setInterval|visibilitychange|mouseover|mouseenter|scroll|IntersectionObserver|performance\.now|Date\.now|dwell|count\+\+|views?Count"


def run(ctx):
    check = ctx.check
    base = ctx.BASE
    res = _node_cases(base)
    check('s131 node is available to run the attention rules (skip the next if not)', res is not None)
    if res is not None:
        check('s131 Da4 unpaid payments due within 7 days - next due date, days to it; paid, far and undated excluded',
              res.get('due') == [['1', '2026-10-02', 4], ['2', '2026-09-30', 2]])
        check('s131 exactly the ruled kinds - the three of 2026-09-27, item 73 Y2\'s date_ends (ruled 2026-10-10), item 86 F5\'s fsa_deadline (ruled 2026-10-14) and item 94 L6\'s bill_due (ruled 2026-10-19)',
              res.get('kinds') == ['payment_due', 'import_stale', 'blocked_conclusion', 'date_ends', 'fsa_deadline', 'bill_due'])
        check('s131 Da6 a blocked conclusion names what is missing, in the record\'s own words',
              res.get('blocked') == [['networth', ['Account balances: not verified']]])
        check('s131 completeness first: with no record at all, nothing is called blocked', res.get('blocked_no_record') == 0)
        check('s131 ordered by kind, then by the fact\'s own urgency - never by use',
              res.get('order') == ['payment_due:2', 'payment_due:1', 'import_stale:7', 'blocked_conclusion:networth'])
        check('s131 Da9 a dismissed fact stays dismissed while it stands', res.get('dismissed') == ['1', '7', 'networth'])
        check('s131 ruling 3 a changed fact (a new amount) returns the item - no timeout, no use-based resurfacing',
              res.get('changed_fact_returns') == 1)
        check('s131 Da10 a fourth kind of attention item is refused by construction', res.get('fourth') == 'refused')

    for name, ok in _server_cases(ctx.c, ctx.HJ, ctx.dbs).items():
        check(f's131 {name}', ok)

    js = base.joinpath('static/js/teaching/dashboard.js').read_text(encoding='utf-8') \
        + base.joinpath('static/js/teaching/attention.js').read_text(encoding='utf-8')
    code = re.sub(r'/\*.*?\*/', '', js, flags=re.S)
    code = '\n'.join(l for l in code.splitlines() if not l.strip().startswith('//'))
    hits = re.findall(_USAGE, code)
    check('s131 Da3 nothing on the dashboard\'s path reads, counts or stores use (no timers, dwell, storage or '
          'engagement events)', not hits)
    if hits:
        print(f'        found: {hits}')
    check('s131 mutation caught: a view counter added to the dashboard',
          bool(re.search(_USAGE, code + '\nlocalStorage.setItem("views", n); viewCount++')))
    apis = set(re.findall(r"API\.(?:get|put|post)\('([^']+)'", code))
    check("s131 the dashboard calls only its own prefs, layout, dismissal and import-fact endpoints, the person's kept receipt dates (item 73 Y2), their FSA terms (item 86 F5) the bills they typed in (item 94 L6) and a payee paid from two accounts with the person's answer (item 107 D6/D8)",
          apis == {'/api/dashboard/prefs', '/api/dashboard/layout', '/api/dashboard/dismiss',
                   '/api/dashboard/attention/imports', '/api/byb/receipt-dates', '/api/byb/receipt-dates/',
                   '/api/accounts/hsa-fsa', '/api/medical-bills', '/api/two-accounts', '/api/two-accounts/answer'})
    check('s131 Da8 ruling 2: attention reads nothing of Speaking up (no dial, no Appendix A caps)',
          not re.search(r'proactive|speaking|dial', code, re.I))
    check('s131 ruling 5: Current priority is retired in 2.0 (hidden by the teaching layer, not deleted from 1.x)',
          '#dashCurrentPriority{display:none!important}' in js)
    srv = ctx.server_src.split("dashboard_bp = Blueprint('dashboard', __name__)", 1)[1].split("@budget_bp.route('/detect-recurring'", 1)[0]
    check('s131 the server side reads the record and the user\'s settings only - no historian events at all',
          'HistorianEntry' not in srv and not re.search(_USAGE, srv))
    check('s131 ruling 6: 1.x untouched - app.js and index.html know nothing of the 2.0 dashboard',
          not re.search(r'gwAttention|gwSummary|/api/dashboard|attention\.js', ctx.app_src)
          and 'gwAttention' not in base.joinpath('static/index.html').read_text(encoding='utf-8'))
