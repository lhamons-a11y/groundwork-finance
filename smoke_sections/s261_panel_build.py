"""Item 112, the panel's proposals as ruled (PANEL_REVIEW.md section 4; Rob 2026-10-24: "i accept p1-p5 and p7").

    P2  no brake on spending a fund saved for; "I had to" describes a charge rather than pricing it
    P3  a fund notices what it paid for, and a deposit over the target is kept, never capped
    P5  colour states in words; charts that say what they show
    P1  gig pay read by the week   P4  who changed what, in Household mode   P7  outside help, a printed summary
"""
import json
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import server
    from core.database import AppSetting, DebtAccount, SinkingFund, Transaction, db_session

    today = date.today()
    with db_session() as s:
        debt = DebtAccount(name='S261 Card', current_balance=8000.0, begin_balance=8000.0, interest_rate=24.0,
                           minimum_payment=200.0, is_active=True)
        fund = SinkingFund(name='S261 Rome Trip', target_amount=3000.0, current_amount=2900.0, is_active=True)
        s.add_all([debt, fund])
        hotel = Transaction(date=today - timedelta(days=3), amount=2880.0, type='debit', merchant='S261 HOTELS ROMA',
                            description='S261 HOTELS ROMA')
        big = Transaction(date=today - timedelta(days=2), amount=90000.0, type='debit', merchant='S261 MIDAS AUTO',
                          description='S261 MIDAS AUTO')
        s.add_all([hotel, big])
        s.commit()
        hid, bid, fid, did = hotel.id, big.id, fund.id, debt.id
        funded = server._funded_by(s, s.get(Transaction, hid))

    def lesson_id():
        with db_session() as s:
            cards, budget, strategy, _u = server._consequence_inputs(s)
            got = server.large_charge_lesson(s, cards, budget, strategy)
            return got and got['charge'].get('id')

    first = lesson_id()
    mark = c.post(f'/api/transactions/{bid}/had-to', headers=HJ, data=json.dumps({'kind': 'car'}))
    after = lesson_id()
    unmark = c.delete(f'/api/transactions/{bid}/had-to', headers=H)
    back = lesson_id()
    check(f"s261 P2 a charge a fund saved for is not priced, and 'I had to' takes a charge out of every lesson, with "
          f"Undo (funded by {funded!r}; lesson {first} -> {after} -> {back})",
          funded == 'S261 Rome Trip' and first == bid and mark.status_code == 200 and after != bid
          and after != hid and unmark.status_code == 200 and back == bid)

    # P3: the fund notices the hotel, and a deposit over the target is kept
    qs = ((c.get('/api/sinking-funds/purchases', headers=H).get_json() or {}).get('data') or {}).get('questions', [])
    q = next((x for x in qs if x['fund_id'] == fid), None)
    yes = (c.post('/api/sinking-funds/purchases/answer', headers=HJ,
                  data=json.dumps({'fund_id': fid, 'txn_id': hid, 'answer': 'yes'})).get_json() or {}).get('data') or {}
    with db_session() as s:
        f1 = s.get(SinkingFund, fid)
        spent_state = (round(f1.current_amount, 2), f1.is_active)
    undo = c.post('/api/sinking-funds/purchases/undo', headers=HJ, data=json.dumps(yes.get('undo') or {}))
    with db_session() as s:
        f2 = s.get(SinkingFund, fid)
        undone = (round(f2.current_amount, 2), f2.is_active)
    asked_again = any(x['fund_id'] == fid for x in ((c.get('/api/sinking-funds/purchases', headers=H).get_json() or {})
                                                  .get('data') or {}).get('questions', []))
    check(f"s261 P3 the fund asks 'Is this what you were saving for?'; yes spends it and closes a fund with almost "
          f"nothing left; Undo restores it and the question ({q and q['amount']}; {spent_state}; {undone})",
          q and q['txn_id'] == hid and q['amount'] == 2880.0 and yes.get('done') is True and spent_state == (20.0, False)
          and undo.status_code == 200 and undone == (2900.0, True) and asked_again)
    c.post('/api/sinking-funds/purchases/answer', headers=HJ, data=json.dumps({'fund_id': fid, 'txn_id': hid, 'answer': 'no'}))
    asked_after_no = any(x['fund_id'] == fid for x in ((c.get('/api/sinking-funds/purchases', headers=H).get_json() or {})
                                                     .get('data') or {}).get('questions', []))
    dep = (c.post(f'/api/sinking-funds/{fid}/deposit', headers=HJ, data=json.dumps({'amount': 500})).get_json() or {}).get('data') or {}
    check(f"s261 P3 'no' is kept and not asked again; a deposit past the target is kept and shown as over, never capped "
          f"({dep.get('current_amount')} over {dep.get('over_target')})",
          not asked_after_no and dep.get('current_amount') == 3400.0 and dep.get('over_target') == 400.0)

    app = ctx.app_src
    funds = (ctx.BASE / 'static' / 'js' / 'teaching' / 'funds.js').read_text(encoding='utf-8')
    pro = (ctx.BASE / 'static' / 'js' / 'teaching' / 'proactive.js').read_text(encoding='utf-8')
    led = (ctx.BASE / 'static' / 'js' / 'teaching' / 'ledger.js').read_text(encoding='utf-8')
    check("s261 P2/P3 the page: 'I had to' on the brake and the Ledger lesson, the fund's question on the Budget page",
          'function hadToButtons(id)' in pro and "hadToButtons(p.txn_id)" in pro and 'GWTeaching.hadToButtons(c.id)' in led
          and "'/api/sinking-funds/purchases/answer'" in funds and 'Is this what you were saving for?' in funds)
    check("s261 P5 over and near the budget are said in words, not only colour; the charts say what they show",
          'function _budgetStateWords(proj, budget, spent)' in app and app.count('projLabel += _budgetStateWords(') == 2
          and 'role="img" aria-label="${esc(donutLabel)}"' in app and 'aria-label="${esc(nwSummary)}"' in app
          and "${esc(nwSummary)}</div>" in app)

    # ── P1: gig pay, read by the week ────────────────────────────────────────────────────────────────────────────
    import random
    from core import income_change as ic
    rnd = random.Random(2610)
    end = date(2026, 10, 20)
    gig = sorted({end - timedelta(days=rnd.randint(0, 120)) for _ in range(60)})
    checks = [(d, round(rnd.uniform(35, 210), 2)) for d in gig]
    j = ic.judge_payer('uber instant pay', checks, None, end, end)
    sparse = ic.judge_payer('odd jobs', [(end - timedelta(days=k), 300.0) for k in (3, 40, 95, 160, 230)], None, end, end)
    check(f"s261 P1 pay with no schedule landing several times a week is read by the week - a typical, low and high "
          f"week over 13 weeks - and counts toward monthly income; rare odd pay stays unknown ({j.get('state')} "
          f"{j.get('weekly')}; {sparse.get('state')})",
          j.get('state') == 'weekly' and j['weekly']['weeks'] == 13 and j['weekly']['low'] <= j['weekly']['typical'] <= j['weekly']['high']
          and j.get('per_month') and sparse.get('state') == 'unknown'
          and "p.state === 'weekly' && p.weekly" in ctx.app_src)

    # ── P4: one partner's cut and the other's restore is not a decision ────────────────────────────────────────────
    from core import willingness as wl
    cut = {'id': 1, 'date': '2026-03-02', 'category': 'Restaurants', 'old': 400.0, 'new': 250.0, 'by': 1, 'by_name': 'Darnell'}
    put = {'id': 2, 'date': '2026-04-05', 'category': 'Restaurants', 'old': 250.0, 'new': 400.0, 'by': 2, 'by_name': 'Keisha'}
    differ = wl._reading('Restaurants', [cut, put], {}, set(), {})
    agreed = wl._reading('Restaurants', [cut, {**put, 'shared': True}], {}, set(), {})
    alone = wl._reading('Restaurants', [cut, {**put, 'by': 1}], {}, set(), {})
    sh = c.post('/api/willingness/shared', headers=HJ, data=json.dumps({'restore_id': 999999, 'answer': 'shared'}))
    with db_session() as s:
        kept = json.loads((s.query(AppSetting).filter_by(key='shared_decisions').first() or AppSetting(value='[]')).value)
    wjs = (ctx.BASE / 'static' / 'js' / 'teaching' / 'willingness.js').read_text(encoding='utf-8')
    check(f"s261 P4 one partner's cut and the other's restore reads undecided, never 'something you keep', until they say "
          f"it was shared; one person's own restore reads as before ({differ['reason']}, {agreed['reason']}, {alone['reason']})",
          differ['stance'] == 'unclassified' and differ['reason'] == 'partners_differ'
          and agreed['stance'] == 'sacred' and alone['stance'] == 'sacred'
          and sh.status_code == 200 and any(a.get('restore_id') == 999999 and a.get('answer') == 'shared' for a in kept)
          and 'Is this a shared decision?' in wjs and "'budget_item_id': item.id, 'name': item.name," in ctx.server_src
          and "'item_type': item.type, **_edit_by(session)}" in ctx.server_src)

    # ── P7: outside help, and a printed summary ──────────────────────────────────────────────────────────────────
    check("s261 P7 an Outside help page from the ? help (NFCC, 211, the CFPB, free legal aid; links open only when "
          "clicked) and a one-page printed summary, from the help and the check-in",
          'function outsideHelpHTML()' in app and 'consumerfinance.gov' in app and 'lawhelp.org' in app
          and 'onclick="showOutsideHelp()">Outside help</button>' in app and 'async function printSession()' in app
          and 'printSession()">Print a summary</button>' in app and 'onclick="printSession()">Print this</button>' in app
          and '#bkPrintSheet h2{' in ctx.html_src)

    with db_session() as s:
        row = s.query(AppSetting).filter_by(key='shared_decisions').first()
        if row:
            s.delete(row)
        s.commit()
    with db_session() as s:
        s.query(Transaction).filter(Transaction.id.in_([hid, bid])).delete(synchronize_session=False)
        s.query(SinkingFund).filter_by(id=fid).delete()
        s.query(DebtAccount).filter_by(id=did).delete()
        for k in ('had_to_charges', 'fund_purchase_answers'):
            row = s.query(AppSetting).filter_by(key=k).first()
            if row:
                s.delete(row)
        s.commit()
