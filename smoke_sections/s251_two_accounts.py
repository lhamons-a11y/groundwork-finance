"""Item 107 (gw 2.0/SAME_CHARGE_TWO_ACCOUNTS.md; Rob 2026-10-21: "D1-D12 as recommended, build it"): the same charge
paid from two accounts in the same month.

    D1  the same payee by the Ledger key, letters and digits, equal or one inside the other (4+)
    D2  within 5%          D3  two accounts; never a transfer, card or loan payment, refund or pending line
    D4  said from the second month within three          D5  per pair of accounts
    D6  Needs attention (a seventh kind) and an Ask why check      D7  fixed words, no verdict, no why
    D8  the answer appended, never written over; "should stop" said once more two months on; Dismiss 60 days
    D9  an answer feeds nothing else      D10 AI off changes nothing      D11 the Morgans show StreamBox
    Section 7: the null model, and the one-charge-a-month rule it forced.
"""
import json
import random
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta
from types import SimpleNamespace as N

BARRED = ('duplicate', 'double', 'twice by mistake', 'wasted', 'should', 'forgot', 'mistake')


def _row(i, d, amount, acct, merchant='', description='', category_id=5, kind='debit', pending=False, card=''):
    return N(id=i, date=d, amount=amount, account_id=acct, type=kind, category_id=category_id, merchant=merchant,
             description=description or merchant.upper(), pending=pending, card_last4=card)


def _monthly(rows, months, acct, merchant, amount, day, **kw):
    for (y, m) in months:
        rows.append(_row(len(rows) + 1, date(y, m, day), amount, acct, merchant, **kw))


def _back(today, k):
    y, m = today.year, today.month - k
    while m < 1:
        y, m = y - 1, m + 12
    return y, m


_SAMPLE = r'''
import json, os, sys
sys.path.insert(0, os.getcwd())
from server import create_app, _GW_TOKEN
app = create_app(); c = app.test_client(); H = {'X-GW-Token': _GW_TOKEN, 'Content-Type': 'application/json'}
c.patch('/api/settings', headers=H, data=json.dumps({'terms_accepted': 'v-test', 'ai_enabled': 'false'}))
c.post('/api/sample/load', headers=H)
out = {'two': c.get('/api/two-accounts', headers=H).get_json()['data'],
       'why': c.get('/api/why/check?id=two_accounts', headers=H).get_json()['data']}
print('@@' + json.dumps(out))
'''


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import two_accounts as ta
    T = date(2026, 10, 21)
    three = [(2026, 8), (2026, 9), (2026, 10)]
    names = {1: 'Checking Account', 2: 'Chase Visa', 3: 'Savings'}

    # ── D1-D5: what pairs ───────────────────────────────────────────────────────────────────────────────────────
    rows = []
    _monthly(rows, three, 1, '', 17.99, 3, description='NETFLIX.COM 866-579-7172')
    _monthly(rows, three, 2, 'Netflix', 17.99, 20)
    ps = ta.pairs(rows, names, set(), T)
    st = ps and ta.state(ps[0], [], T)
    check(f"s251 D1/D4 Rob's example: two spellings, two accounts, three months - said ({ps and ps[0]['payee']}, {st})",
          len(ps) == 1 and ps[0]['payee'] == 'Netflix' and st == 'said' and ps[0]['accounts'] == [1, 2])
    words = ps and ta.sentence(ps[0])
    check(f's251 D7 the fixed words: what was seen, the months, no verdict ("{words}")',
          words == '$17.99 from Checking Account on Oct 3 and $17.99 from Chase Visa on Oct 20. Both accounts paid it in '
                   'August and September too.')

    one = []
    _monthly(one, three[-1:], 1, 'Netflix', 17.99, 3)
    _monthly(one, three[-1:], 2, 'Netflix', 17.99, 9)
    p1 = ta.pairs(one, names, set(), T)
    check('s251 D4 one month only is not said on the Dashboard; Ask why lists it as one month',
          len(p1) == 1 and ta.state(p1[0], [], T) is None and ta.sentence(p1[0]).endswith('One month only.'))

    switch = []
    _monthly(switch, three[:2], 1, 'Netflix', 17.99, 3)              # the old account through September ...
    _monthly(switch, three[1:], 2, 'Netflix', 17.99, 28)             # ... the new one from September
    ps = ta.pairs(switch, names, set(), T)
    check('s251 D4 a card switch (the last old charge and the first new one in one month) is not said',
          len(ps) == 1 and ta.state(ps[0], [], T) is None)

    pay = []
    _monthly(pay, three, 2, 'Target', 17.99, 5)                      # a purchase on the store card ...
    _monthly(pay, three, 1, '', 17.99, 25, description='TARGET CARD PMT')   # ... and checking paying that card
    _monthly(pay, three, 2, 'Cashback', 50.0, 8)
    _monthly(pay, three, 1, 'Cashback', 50.0, 22, category_id=9)    # a card payment filed under a payment category
    check('s251 D3 checking paying the card never pairs, even when the store card shares the store\'s name',
          ta.pairs(pay, names, {9}, T) == [])
    tr = []
    _monthly(tr, three, 1, 'Netflix', 17.99, 3, category_id=9)
    _monthly(tr, three, 2, 'Netflix', 17.99, 9)
    pend = []
    _monthly(pend, three, 1, 'Netflix', 17.99, 3, pending=True)
    _monthly(pend, three, 2, 'Netflix', 17.99, 9)
    ref = []
    _monthly(ref, three, 1, 'Netflix', 17.99, 3, kind='credit')
    _monthly(ref, three, 2, 'Netflix', 17.99, 9)
    check('s251 D3 a Transfer-category, pending or refund row never pairs',
          ta.pairs(tr, names, {9}, T) == [] and ta.pairs(pend, names, set(), T) == [] and ta.pairs(ref, names, set(), T) == [])
    off = []
    _monthly(off, three, 1, 'Netflix', 17.99, 3)
    _monthly(off, three, 2, 'Netflix', 19.07, 9)                     # 6% apart
    check('s251 D2 amounts 6% apart are not paired', ta.pairs(off, names, set(), T) == [])
    cards = []
    _monthly(cards, three, 1, 'Netflix', 17.99, 3, card='1111')
    _monthly(cards, three, 1, 'Netflix', 17.99, 9, card='2222')
    check('s251 D3 two cards on one account are not paired (section 4: held)', ta.pairs(cards, names, set(), T) == [])
    shop = []
    for (y, m) in three:
        for acct in (1, 2):
            for d in (4, 18):
                shop.append(_row(len(shop) + 1, date(y, m, d), 42.10 + d * 0.01, acct, 'Kroger'))
    check('s251 section 7 a payee charged more than once on an account that month is shopping, not a subscription',
          ta.pairs(shop, names, set(), T) == [])

    # ── section 7: the null model ────────────────────────────────────────────────────────────────────────────────
    fired = 0
    for k in range(200):
        rnd, hh = random.Random(k), []
        for j, (name, price) in enumerate([('Netflix', 17.99), ('Spotify', 11.99), ('Gym', 45.0), ('Phone', 94.0),
                                           ('Internet', 69.99), ('Cloud', 2.99), ('News', 12.0), ('Xbox', 16.99)]):
            _monthly(hh, three, (j + k) % 3 + 1, name, price, j * 3 + 1)
        for store in ('Kroger', 'Walmart', 'Target', 'Shell', 'Starbucks', 'Amazon'):
            for (y, m) in three:
                for acct in (1, 2):
                    for _ in range(rnd.randint(0, 3)):
                        d = date(y, m, rnd.randint(1, 28))
                        if d <= T:
                            hh.append(_row(len(hh) + 1, d, round(rnd.uniform(5, 160), 2), acct, store))
        fired += any(ta.state(p, [], T) for p in ta.pairs(hh, names, set(), T))
    check(f's251 section 7 the null model: each payee paid from one account, shopping from two - said in {fired} of 200 households',
          fired == 0)

    # ── D8: the answers ──────────────────────────────────────────────────────────────────────────────────────────
    rows = []
    _monthly(rows, three, 1, 'Netflix', 17.99, 3)
    _monthly(rows, three, 2, 'Netflix', 17.99, 9)
    p = ta.pairs(rows, names, set(), T)[0]
    s1 = ta.append([], p, 'both_meant', at='2026-10-21T10:00:00')
    s2 = ta.append(s1, p, 'not_same', at='2026-10-21T10:05:00')
    check('s251 D8 each answer is appended, never written over; the newest counts',
          len(s2) == 2 and s2[0] == s1[0] and ta.effective(s2, p['key'])['answer'] == 'not_same')
    check('s251 D8 "Both are meant" and "These aren\'t the same" end the pair',
          ta.state(p, s1, T) is None and ta.state(p, ta.append([], p, 'not_same', at='2026-10-21T10:00:00'), T) is None
          and ta.state(p, s1, date(2027, 6, 1)) is None)
    nn = ta.append([], p, 'not_now', at='2026-10-21T10:00:00')
    check('s251 D8 Dismiss is "not now" for 60 days, not a statement Settings lists',
          ta.state(p, nn, T + timedelta(days=59)) is None and ta.state(p, nn, T + timedelta(days=60)) == 'said'
          and ta.listed(nn) == [])
    stop = ta.append([], p, 'should_stop', at='2026-10-21T10:00:00')
    later = list(rows)
    _monthly(later, [(2026, 11), (2026, 12)], 1, 'Netflix', 17.99, 3)
    _monthly(later, [(2026, 11), (2026, 12)], 2, 'Netflix', 17.99, 9)
    nov = ta.pairs(later, names, set(), date(2026, 11, 30))[0]
    dec = ta.pairs(later, names, set(), date(2026, 12, 20))[0]
    again = ta.state(dec, stop, date(2026, 12, 20))
    check(f's251 D8 (a) "One of these should stop": quiet, then said once more when both still pay it two months on ({again})',
          ta.state(p, stop, T) is None and ta.state(nov, stop, date(2026, 11, 30)) is None and again == 'again'
          and ta.sentence(dec, 'again', '2026-12').startswith('You said one of these should stop. Both paid it in December ('))
    after = ta.append(stop, dec, 'not_now', at='2026-12-20T10:00:00', again=True)
    check('s251 D8 (a) once more, then never: whatever the answer to it',
          ta.state(dec, after, date(2027, 3, 1)) is None
          and ta.state(dec, ta.append(stop, dec, 'both_meant', at='2026-12-20T10:00:00', again=True), date(2027, 3, 1)) is None)
    w = ta.withdraw(s1, 0, at='2026-10-21T10:00:00')
    check('s251 D8 Undo adds a withdrawal, removes nothing, and the pair is asked again',
          len(w) == 2 and w[0] == s1[0] and w[1]['answer'] == 'withdrawn' and ta.state(p, w, T) == 'said'
          and ta.listed(w) == [] and ta.withdraw(s1, 7) is None
          and ta.state(p, ta.append(w, p, 'not_now', at='2026-10-21T10:00:00'), T) is None)

    # ── D7: the words ────────────────────────────────────────────────────────────────────────────────────────────
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    js = (root / 'static/js/teaching/twoaccounts.js').read_text(encoding='utf-8')
    dash = (root / 'static/js/teaching/dashboard.js').read_text(encoding='utf-8')
    branch = dash[dash.index("i.kind === 'two_accounts'"):dash.index("i.kind === 'import_stale'")]
    said_words = ' '.join([ta.sentence(ps[0]) if ps else '', ta.SOURCE, ta.LABEL, ta.ESTABLISHES, ta.CANNOT,
                           ta.sentence(p), ta.sentence(p, 'again', '2026-10')]).lower()
    bad = [b for b in BARRED if b in said_words.replace('you said one of these should stop', '')]
    check(f's251 D7 none of the barred words in the fixed words ({bad})', not bad)
    check('s251 D6 (a) Needs attention takes the seventh kind, with its answers, Show the charges and a 60-day Dismiss',
          "'two_accounts'," in (root / 'static/js/teaching/attention.js').read_text(encoding='utf-8')   # (the backup
          and 'twoAccounts: A.twoAccounts(two),' in dash                                                     # reminder's kind follows) and 'data-gw-two-show' in branch
          and all(f'data-gw-two-answer="{a}"' in branch for a in ('both_meant', 'should_stop', 'not_same', 'not_now'))
          and 'e.g. one is for someone else' in branch and 'data-gw-dismiss=' not in branch)
    if shutil.which('node'):
        src = str(root / 'static/js/teaching/attention.js').replace('\\', '/')
        r = subprocess.run(['node', '-e', f"const A=require('{src}');const i=A.twoAccounts([{{pair:'netflix|1|2',title:'Netflix',"
                            f"state:'said',sentence:'x',source:'y',label:'z',search:'Netflix',fact:'netflix|1|2|said'}}]);"
                            f"let bad=false;try{{A.build({{payments:[{{kind:'nope'}}]}},[])}}catch(e){{bad=true}};"
                            f"console.log(JSON.stringify([A.build({{twoAccounts:i}},[]).length,bad]))"],
                           capture_output=True, text=True)
        check(f's251 D6 (a) in Node: build() takes the new kind and still refuses an unknown one ({r.stdout.strip()})',
              r.stdout.strip() == '[1,true]')

    # ── the routes, on this database ─────────────────────────────────────────────────────────────────────────────
    from core.database import Account, AppSetting, HistorianEntry, Transaction, db_session
    today = date.today()
    m1, m2 = _back(today, 2), _back(today, 1)
    with db_session() as s:
        a1 = Account(name='s251 Checking', type='checking'); a2 = Account(name='s251 Visa', type='credit')
        s.add_all([a1, a2]); s.flush()
        ids = []
        for (y, m) in (m1, m2):
            for acct, d, desc, merch in ((a1.id, 3, 'STREAMQ.COM 1234', ''), (a2.id, 9, 'STREAMQ', 'StreamQ')):
                t = Transaction(date=date(y, m, d), description=desc, merchant=merch, amount=13.37, type='debit',
                                account_id=acct)
                s.add(t); s.flush(); ids.append(t.id)
        s.commit()
        acct_ids = [a1.id, a2.id]
    def items():
        return [x for x in (c.get('/api/two-accounts', headers=H).get_json()['data']['attention'])
                if x['accounts'] == acct_ids]
    def figures():
        tx = c.get('/api/transactions?per_page=5000', headers=H).get_json()['data']
        with db_session() as s:
            rec = s.query(AppSetting).filter_by(key='recurring_items_json').first()
            rec = rec.value if rec else None
        return (round(sum(t['amount'] for t in tx if t['type'] == 'debit'), 2), len(tx),
                json.dumps(c.get('/api/budget/items', headers=H).get_json()['data'], sort_keys=True), rec,
                json.dumps(c.get('/api/budget/detect-recurring', headers=H).get_json()['data'], sort_keys=True))
    try:
        it = items()
        check(f"s251 D6 (a) the route says it, with the fixed words and the rows behind it ({it and it[0]['sentence']})",
              len(it) == 1 and it[0]['state'] == 'said' and it[0]['title'] == 'StreamQ' and it[0]['source'] == ta.SOURCE
              and len(it[0]['rows']) == 4 and 'Both accounts paid it in' in it[0]['sentence'])
        why = c.get('/api/why/check?id=two_accounts', headers=H).get_json()['data']
        check('s251 D6 (b) the Ask why check finds it, with what it can and can\'t tell, and is in "Your records"',
              any(r['text'].startswith('StreamQ: ') and r['cannot'] == ta.CANNOT and r['establishes'] == ta.ESTABLISHES
                  for r in why['results']))
        from core import ask_why
        check('s251 D6 (b) / D10 the check is on the "Your records" list and the routing list',
              'two_accounts' in ask_why.FIGURES['records']['checks'] and "'two_accounts'" in ctx.server_src
              and 'two_accounts: the same charge or subscription paid from two different accounts.' in ctx.server_src)
        pair = it[0]['pair'] if it else ''
        before = figures()
        bad = c.post('/api/two-accounts/answer', headers=HJ, data=json.dumps({'pair': pair, 'answer': 'cancel it'}))
        nope = c.post('/api/two-accounts/answer', headers=HJ, data=json.dumps({'pair': 'nothing|1|2', 'answer': 'both_meant'}))
        c.patch('/api/settings', headers=HJ, data=json.dumps({'two_accounts_said_json': '[]'}))
        r = c.post('/api/two-accounts/answer', headers=HJ, data=json.dumps({'pair': pair, 'answer': 'both_meant'})).get_json()
        c.patch('/api/settings', headers=HJ, data=json.dumps({'two_accounts_said_json': '[]'}))
        after = figures()
        got = c.get('/api/two-accounts', headers=H).get_json()['data']
        check(f's251 D8 the answer is kept as the person\'s statement, the pair is not said again, and the settings route '
              f'can\'t write over it ({bad.status_code}, {nope.status_code})',
              bad.status_code == 400 and nope.status_code == 404 and r.get('ok') and items() == []
              and any(x['key'] == pair and x['answer'] == 'both_meant' for x in got['said']))
        check('s251 D9 nothing else moves: spending, the budget, recurring items and the recurring detection are the same',
              before == after)
        with db_session() as s:
            h = s.query(HistorianEntry).filter_by(event_category='two_accounts_answered').order_by(HistorianEntry.id.desc()).first()
            ctxj = h.context_json if h else ''
        check(f's251 D8 the Historian has the answer, the payee key and the two accounts, and no bank text ({ctxj})',
              h is not None and json.loads(ctxj)['answer'] == 'both_meant' and json.loads(ctxj)['accounts'] == acct_ids
              and 'STREAMQ.COM' not in ctxj and '1234' not in ctxj)
        n = next(x['n'] for x in got['said'] if x['key'] == pair)
        u = c.post('/api/two-accounts/undo', headers=HJ, data=json.dumps({'n': n})).get_json()
        check('s251 D8 Undo from Settings adds a withdrawal, and the pair is said again',
              u.get('ok') and len(items()) == 1
              and not any(x['key'] == pair for x in c.get('/api/two-accounts', headers=H).get_json()['data']['said']))
        c.post('/api/two-accounts/answer', headers=HJ, data=json.dumps({'pair': pair, 'answer': 'not_now'}))
        check('s251 D8 Dismiss on the Dashboard is "not now": gone, and not listed as something said',
              items() == [] and not any(x['key'] == pair for x in c.get('/api/two-accounts', headers=H).get_json()['data']['said']))
        check('s251 D8 Settings lists what was said, each with Undo (twoaccounts.js under the Speaking up card)',
              'data-gw-two-undo' in js and "'/api/two-accounts/undo'" in js and "getElementById('proactiveSilenced')" in js)
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.id.in_(ids)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(acct_ids)).delete(synchronize_session=False)
            row = s.query(AppSetting).filter_by(key=ta.SETTING).first()
            if row:
                s.delete(row)
            s.commit()

    # ── D10, D11: the Morgans, with AI off, in their own process and folder ──────────────────────────────────────
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, GROUNDWORK_DATA_DIR=d)
        r = subprocess.run([sys.executable, '-c', _SAMPLE], cwd=str(root), env=env, capture_output=True, text=True, timeout=300)
    line = next((x for x in r.stdout.splitlines() if x.startswith('@@')), None)
    if not line:
        check(f's251 the Morgans ran ({(r.stderr or "")[-600:]})', False)
        return
    o = json.loads(line[2:])
    att = (o.get('two') or {}).get('attention') or []
    check(f"s251 D11 / D10 the Morgans show exactly one, StreamBox, with AI off ({[a['title'] + ': ' + a['sentence'] for a in att]})",
          len(att) == 1 and att[0]['title'] == 'StreamBox' and att[0]['account_names'] == ['Everyday Checking', 'Cashback Visa']
          and att[0]['sentence'].startswith('$15.49 from Everyday Checking on ')
          and 'Both accounts paid it in' in att[0]['sentence'])
    check('s251 D11 the Ask why check finds the same StreamBox for the Morgans',
          any(x['text'].startswith('StreamBox: ') for x in ((o.get('why') or {}).get('results') or [])))
