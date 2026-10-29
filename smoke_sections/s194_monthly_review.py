"""Item 75: the month's review, written when the month is complete (gw 2.0/MONTHLY_REVIEW.md M1-M10, RULED 2026-10-10;
Rob 2026-10-11: "build item 75"). A fixed past month (March 2019) keeps the rule clear of other sections' records.

    M1  after an import, the one due review is written - once
    M2  complete = every account with records in the month has a later one (or is inactive, or "not needed")
    M3  a month in progress is never saved as its review; opening Reports writes nothing
    M4  a saved review keeps what it was written from; later records are counted, and writing again keeps the old
    M5  one quiet dashboard line until it is opened
    M6/M7/M9  one at a time; a failed written part keeps the summary; AI off saves the summary
    M8  said in Settings, with a switch
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app, html = ctx.app_src, ctx.html_src
    from core import monthly_review as mr
    from core.database import Account, AppSetting, Transaction, db_session

    M, today = '2019-03', date(2019, 4, 15)
    with db_session() as s:
        a, b, gone = Account(name='s194 Checking'), Account(name='s194 Savings'), Account(name='s194 Old card', is_active=False)
        auto = Account(name='s194 Recurring')
        s.add_all([a, b, gone, auto]); s.flush()
        ids = {'a': a.id, 'b': b.id}
        s.add_all([Transaction(date=date(2019, 3, 5), amount=40.0, type='debit', account_id=a.id, description='s194 store'),
                   Transaction(date=date(2019, 3, 9), amount=2000.0, type='credit', account_id=a.id, description='s194 pay'),
                   Transaction(date=date(2019, 4, 2), amount=12.0, type='debit', account_id=a.id, description='s194 april'),
                   Transaction(date=date(2019, 3, 12), amount=300.0, type='credit', account_id=b.id, description='s194 savings'),
                   Transaction(date=date(2019, 3, 20), amount=9.0, type='debit', account_id=gone.id, description='s194 old'),
                   Transaction(date=date(2019, 3, 20), amount=260.21, type='debit', account_id=auto.id, description='s194 bill auto-log',
                               source='manual')])
        s.commit()
        st1 = mr.status(s, M, today)
        due_wait = mr.due(s, today)
    check(f's194 M2 a month waits for an account whose imported records end inside it, and says which; an inactive account, or one holding only records Groundwork or the person wrote, never holds it ({st1["waiting"]})',
          st1['state'] == 'waiting' and [w['account'] for w in st1['waiting']] == ['s194 Savings']
          and st1['waiting'][0]['records_end'] == '2019-03-12' and due_wait is None)
    sk = c.post('/api/reports/review/skip-account', headers=HJ, data=json.dumps({'account_id': ids['b']}))
    with db_session() as s:
        st2 = mr.status(s, M, today)
        due1 = mr.due(s, today)
        inprog = mr.status(s, '2019-04', today)
    check('s194 M2 "not needed for reviews" lets the month complete; then it is the one review due',
          sk.status_code == 200 and st2['state'] == 'complete' and due1 == M)
    check('s194 M3 the month in progress is never complete', inprog['state'] == 'in_progress')

    # legacy review (saved before this item) does not count; the switch turns it off
    with db_session() as s:
        s.add(AppSetting(key=f'report_text_{M}', value='An old review, written mid-month.')); s.commit()
        legacy_due = mr.due(s, today)
        s.add(AppSetting(key='auto_monthly_review', value='false')); s.commit()
        off_due = mr.due(s, today)
        s.query(AppSetting).filter_by(key='auto_monthly_review').delete(); s.commit()
    check('s194 M1/M8 a review saved before this item (maybe mid-month) does not count; the switch turns the review off',
          legacy_due == M and off_due is None)

    # save: once, history kept, changes counted
    with db_session() as s:
        first = mr.save(s, M, 'The March review.', 'written', today); s.commit()
        after = mr.due(s, today)
        sv = mr.saved(s, M)
        hist = json.loads(s.query(AppSetting).filter_by(key=f'review_history_{M}').first().value)
    check('s194 M1/M4 saved as the month\'s review with what it was written from; the earlier one is kept; nothing more is due',
          after is None and sv['text'] == 'The March review.' and sv['meta']['kind'] == 'written'
          and sv['meta']['fingerprint']['records'] == 5 and sv['changed_since'] is None
          and hist[0]['text'] == 'An old review, written mid-month.')
    with db_session() as s:
        s.add(Transaction(date=date(2019, 3, 28), amount=5.0, type='debit', account_id=ids['a'], description='s194 late'))
        s.commit()
        late = mr.saved(s, M)
    check('s194 M4 a record that arrives later is counted and said, never written over',
          late['changed_since'] == {'records_then': 5, 'records_now': 6} and late['text'] == 'The March review.')

    cur = date.today().strftime('%Y-%m')
    bad = c.post('/api/reports/review', headers=HJ, data=json.dumps({'month': cur, 'text': 'x', 'kind': 'written'}))
    badk = c.post('/api/reports/review', headers=HJ, data=json.dumps({'month': M, 'text': 'x', 'kind': 'verdict'}))
    check('s194 M3 a month in progress is refused as a review; so is a kind Groundwork does not keep',
          bad.status_code == 400 and badk.status_code == 400)

    rdy = c.get('/api/reports/review/ready', headers=H).get_json()['data']['month']
    c.post('/api/reports/review/seen', headers=HJ, data=json.dumps({'month': M}))
    rdy2 = c.get('/api/reports/review/ready', headers=H).get_json()['data']['month']
    st = c.get(f'/api/reports/review/status?month={M}', headers=H).get_json()['data']
    check('s194 M5 one quiet line until the review is opened', rdy == M and rdy2 != M and st['saved']['meta']['seen'] is True)

    # the page
    refresh = app.split('function _rcMonthlyRefreshPreview() {')[1].split('\n}\n')[0]
    check('s194 M3 opening Reports writes nothing by itself', '_rcMonthlyGenerate()' not in refresh and '_rcMonthlyShowSaved(month)' in refresh)
    ci = app.split('async function confirmImport() {')[1].split('\nasync function ')[0]
    check('s194 M1 as amended by item 76 S2: the due review is written by the night run, not by the import itself',
          'monthlyReviewAfterImport()' not in ci and 'monthlyReviewAfterImport()' in app.split('async function _nightNarration() {')[1])
    check('s194 M5/M8 the dashboard line and the Settings words and switch are there',
          'id="dashReviewReady"' in html and 'Nothing is sent anywhere. Every request is in the AI log.' in html
          and 'id="settingsAutoReview"' in html and "s.auto_monthly_review !== 'false'" in app)

    # the writer, run in Node: AI off, AI ok, AI failing, nothing due, one at a time
    node = shutil.which('node')
    out = None
    if node:
        # item 109: _localISODate and _localStamp, the page's local clock, come in with the functions that use them
        fn = lambda name, pre='function ': re.search(r'\n(?:async )?' + pre + name + r'\(.*?\n\}\n', app, re.S).group(0)
        js = ('const posts = []; let due = "2019-03", ai = false, aiResult = null, calls = 0;\n'
              'const S = {transactions: [{date: "2019-03-05", amount: 40, type: "debit", category: "Food", kind: "spending"}], incomes: [{amount: 2000}]};\n'
              'const _catParentName = c => c; const fmt = n => "$" + Number(n).toFixed(2);\n'
              + fn('_kind') + fn('_isSpend') + fn('_spendAmt') + fn('_spendCat') +      # item 111: the kind is the server's
              '\n'
              'const esc = s => String(s); const _gwErr = () => () => {}; const renderReviewReady = () => {};\n'
              'const aiEnabled = () => ai; const callAI = async () => { calls++; return aiResult; };\n'
              'const API = { get: async () => ({ month: due }), post: async (u, b) => { posts.push(b); return {}; } };\n'
              'let _monthlyReviewBusy = false;\n'
              + fn('_localISODate') + fn('_localStamp') + fn('_rcMonthlyFallbackText') + fn('_rcMonthFacts') + re.search(r'\nasync function monthlyReviewAfterImport\(.*?\n\}\n', app, re.S).group(0) +
              '(async () => {\n'
              ' await monthlyReviewAfterImport();\n'
              ' ai = true; aiResult = {ok: true, text: "Written."}; await monthlyReviewAfterImport();\n'
              ' aiResult = {ok: false}; await monthlyReviewAfterImport();\n'
              ' due = null; const before = posts.length; await monthlyReviewAfterImport();\n'
              ' due = "2019-03"; aiResult = {ok: true, text: "Again."}; const p1 = monthlyReviewAfterImport(), p2 = monthlyReviewAfterImport(); await p1; await p2;\n'
              ' console.log(JSON.stringify({kinds: posts.map(p => p.kind), texts: posts.map(p => p.text.slice(0, 40)), nothingDue: posts.length - before, calls}));\n'
              '})();')
        fd, p = tempfile.mkstemp(suffix='.js')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(js)
        try:
            out = json.loads(subprocess.run([node, p], capture_output=True, text=True, encoding='utf-8', timeout=60).stdout or 'null')
        except Exception:                      # noqa: BLE001
            out = None
        finally:
            os.remove(p)
    check(f's194 M9/M7/M6 run in Node: AI off saves the summary, AI on saves the written review, a failed one keeps the summary, nothing due writes nothing, two at once write one ({out})',
          out is not None and out['kinds'] == ['summary', 'written', 'summary_failed', 'written']
          and out['texts'][0].startswith('In March 2019 you kept') and "didn't pass Groundwork's checks" not in out['texts'][0]
          and out['texts'][1] == 'Written.' and out['calls'] == 3)

    with db_session() as s:
        s.query(Transaction).filter(Transaction.description.like('s194%')).delete(synchronize_session=False)
        s.query(Account).filter(Account.name.like('s194%')).delete(synchronize_session=False)
        for k in (f'report_text_{M}', f'review_meta_{M}', f'review_history_{M}', 'review_skip_accounts'):
            s.query(AppSetting).filter_by(key=k).delete()
        s.commit()
