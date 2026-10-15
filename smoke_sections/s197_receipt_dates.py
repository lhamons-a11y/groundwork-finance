"""Item 73 stage 2 (gw 2.0/BYB_AGENT.md Y2, RULED 2026-10-10; Rob 2026-10-11: "Please proceed item 71- 73").

    Y2  trial, return and cancel-by dates read from a receipt on this computer: only dates written with a year,
        only a price the receipt states; kept on the person's pick; on the dashboard from a week before; Groundwork
        never cancels or returns anything; the receipt is not kept
"""
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app = ctx.app_src
    from core.receipt_dates import read
    from core.database import AppSetting, DATA_DIR, db_session

    r = read('Peacock\nWelcome!\nYour 7-day free trial ends on November 14, 2026. After that you will be charged $7.99/month.\n'
             'Order number: A1B2C3D4E5\nCancel anytime before Nov 14 to avoid charges.')
    t = r['dates'][0] if r['dates'] else {}
    check(f'Y2 a free trial\'s end and the price after it, with the receipt\'s own words ({r})',
          r['merchant'] == 'Peacock' and len(r['dates']) == 1 and t['kind'] == 'trial_ends' and t['date'] == '2026-11-14'
          and t['price_after'] == 7.99 and t['every'] == 'month' and 'free trial ends' in t['phrase'] and r['warnings'] == [])
    check('Y2 a confirmation number is taken out of the text before anything else reads it',
          'A1B2C3D4E5' not in json.dumps(r))
    b = read('Best Buy\nReceipt\nSony headphones $248.00\nReturn by: December 1, 2026\nCancel by Dec 3 for a refund.')
    check(f'Y2 a return date is read; a date without its year is left out and said, never assumed ({b})',
          [(x['kind'], x['date']) for x in b['dates']] == [('return_by', '2026-12-01')]
          and len(b['warnings']) == 1 and 'without a year' in b['warnings'][0])
    lbl = read('Streamco\nTrial ends\n01/09/2027\nthen $12.50 per month')
    check('Y2 a label with its date on the next line is read', lbl['dates'] and lbl['dates'][0]['date'] == '2027-01-09'
          and lbl['dates'][0]['price_after'] == 12.5)
    bad = read('Gym\nYour free trial ends on March 3, 2027.')
    planted = [x['price_after'] for x in bad['dates']]
    check('Y2 a price the receipt does not state is never filled in', planted == [None])
    check('Y2 a receipt with no such date finds nothing', read('Walmart\nMilk $3.49\nThank you')['dates'] == [])

    # the routes: read saves nothing; the pick is kept; handled leaves the list
    before = sorted(os.listdir(DATA_DIR))
    with db_session() as s:
        n0 = s.query(AppSetting).filter_by(key='receipt_dates').count()
    eml = ('From: Peacock <hello@peacock.example>\r\nSubject: Welcome\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n'
           'Peacock\r\nYour free trial ends on November 14, 2026, then $7.99/month.\r\n').encode()
    rf = c.post('/api/byb/receipt/read', headers=H, data={'file': (io.BytesIO(eml), 'welcome.eml')}, content_type='multipart/form-data')
    rt = c.post('/api/byb/receipt/read', headers=HJ, data=json.dumps({'text': 'Best Buy\nReturn by: December 1, 2026'}))
    with db_session() as s:
        n1 = s.query(AppSetting).filter_by(key='receipt_dates').count()
    check('Y2 a saved email and pasted text are read on this computer, and reading keeps nothing - no setting, no file',
          rf.status_code == 200 and rf.get_json()['data']['dates'][0]['date'] == '2026-11-14' and rt.status_code == 200
          and n0 == n1 and sorted(os.listdir(DATA_DIR)) == before)
    soon = (date.today() + timedelta(days=3)).isoformat()
    far = (date.today() + timedelta(days=40)).isoformat()
    sv = c.post('/api/byb/receipt-dates', headers=HJ, data=json.dumps({'merchant': 's193 Peacock', 'dates': [
        {'kind': 'trial_ends', 'date': soon, 'price_after': 7.99, 'every': 'month', 'phrase': 'trial ends'},
        {'kind': 'return_by', 'date': far, 'phrase': 'return by'},
        {'kind': 'pay_now', 'date': soon}, {'kind': 'cancel_by', 'date': 'next Tuesday'}]}))
    added = sv.get_json()['data']['added']
    lst = c.get('/api/byb/receipt-dates', headers=H).get_json()['data']['dates']
    none = c.post('/api/byb/receipt-dates', headers=HJ, data=json.dumps({'merchant': 'x', 'dates': [{'kind': 'nope', 'date': soon}]}))
    check('Y2 only the picked dates are kept, each checked again: an unknown kind or an unreadable date is not',
          sv.status_code == 200 and [a['kind'] for a in added] == ['trial_ends', 'return_by'] and none.status_code == 400
          and [x['date'] for x in lst if x['merchant'] == 's193 Peacock'] == [soon, far])
    done = c.post(f"/api/byb/receipt-dates/{added[0]['id']}/done", headers=HJ, data='{}')
    missing = c.post('/api/byb/receipt-dates/1/done', headers=HJ, data='{}')
    lst2 = c.get('/api/byb/receipt-dates', headers=H).get_json()['data']['dates']
    check('Y2 "Handled" marks it done and it stays in the person\'s record', done.status_code == 200 and missing.status_code == 404
          and next(x for x in lst2 if x['id'] == added[0]['id'])['done'])

    # the dashboard: a ruled fourth kind, from seven days before, run in Node
    node = shutil.which('node')
    out = None
    if node:
        src = (ctx.BASE / 'static' / 'js' / 'teaching' / 'attention.js').read_text(encoding='utf-8')
        today = date.today()
        rows = [{'id': 1, 'merchant': 'A', 'kind': 'trial_ends', 'date': (today + timedelta(days=7)).isoformat()},
                {'id': 2, 'merchant': 'B', 'kind': 'return_by', 'date': (today + timedelta(days=8)).isoformat()},
                {'id': 3, 'merchant': 'C', 'kind': 'cancel_by', 'date': (today - timedelta(days=1)).isoformat()},
                {'id': 4, 'merchant': 'D', 'kind': 'trial_ends', 'date': today.isoformat(), 'done': '2026-10-11'},
                {'id': 5, 'merchant': 'E', 'kind': 'return_by', 'date': today.isoformat()}]
        js = src + '\nconst A = module.exports; const items = A.build({dates: A.datesEnding(' + json.dumps(rows) + ', new Date())}, []);\n' \
             'console.log(JSON.stringify({kinds: A.KINDS, items: items.map(i => [i.title, i.days])}));'
        fd, p = tempfile.mkstemp(suffix='.js')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(js)
        try:
            out = json.loads(subprocess.run([node, p], capture_output=True, text=True, encoding='utf-8', timeout=60).stdout or 'null')
        except Exception:                      # noqa: BLE001
            out = None
        finally:
            os.remove(p)
    check(f'Y2 on the dashboard from seven days before, soonest first; past or handled dates are not ({out})',
          out and 'date_ends' in out['kinds'] and out['items'] == [['E', 0], ['A', 7]])

    dash = (ctx.BASE / 'static' / 'js' / 'teaching' / 'dashboard.js').read_text(encoding='utf-8')
    js = app.split('async function renderBybReceipts(')[1].split('\nasync function bybReceiptDone(')[0]
    check('Y2 Groundwork never cancels or returns anything, says so, and uses no model',
          "doesn\\'t cancel or return anything; you do" in dash and 'callAI(' not in js and 'not kept' in js
          and not re.search(r'cancel(Subscription|Order)|/cancel\b|/refund', js))

    with db_session() as s:
        s.query(AppSetting).filter_by(key='receipt_dates').delete(); s.commit()
