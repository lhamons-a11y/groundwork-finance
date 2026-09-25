"""V6: a debt figure left blank is stored as unknown, never as 0.

0% is a real APR (promotional financing) and $0 a real balance (paid off), so a
zero written for "not entered" can never be told apart from one afterwards. The
Debt page used to send `parseFloat(x) || 0`, and the server coerced anything
missing to 0. Now an explicit blank is NULL, a typed 0 stays 0, an absent key
keeps the old default (so other callers are unchanged), and nothing downstream
invents a figure by doing arithmetic on an unknown one.
"""
from pathlib import Path


def run(ctx):
    check, c, HJ = ctx.check, ctx.c, ctx.HJ
    from core.database import DebtAccount
    from server import db_session

    def body(resp):
        j = resp.get_json() or {}
        return j.get('data') or j

    def row(debt_id):
        with db_session() as s:
            d = s.get(DebtAccount, debt_id)
            return None if d is None else (d.begin_balance, d.current_balance,
                                           d.interest_rate, d.minimum_payment)

    made = []

    blank = c.post('/api/debt', headers=HJ, json={
        'name': 'V6 Blank Card', 'begin_balance': None, 'current_balance': None,
        'interest_rate': '', 'minimum_payment': None})
    b = body(blank); made.append(b.get('id'))
    check('V6: a debt created with its figures left blank is accepted',
          blank.status_code in (200, 201) and bool(b.get('id')))
    check('and all four figures are stored as unknown, not as 0',
          row(b.get('id')) == (None, None, None, None))
    check('and the API reports them as null, so the page shows blanks, not zeros',
          b.get('interest_rate') is None and b.get('minimum_payment') is None
          and b.get('current_balance') is None)

    zero = c.post('/api/debt', headers=HJ, json={
        'name': 'V6 Promo Card', 'begin_balance': 800, 'current_balance': 800,
        'interest_rate': 0, 'minimum_payment': 25})
    z = body(zero); made.append(z.get('id'))
    check('a typed 0% stays 0% - a known zero is not turned into unknown',
          row(z.get('id')) == (800.0, 800.0, 0.0, 25.0))

    legacy = c.post('/api/debt', headers=HJ, json={'name': 'V6 Legacy Caller'})
    l = body(legacy); made.append(l.get('id'))
    check('a caller that sends no figures at all keeps the old default of 0',
          row(l.get('id')) == (0.0, 0.0, 0.0, 0.0))

    p1 = c.patch(f"/api/debt/{z.get('id')}", headers=HJ, json={'interest_rate': ''})
    check('clearing the APR on an existing debt stores unknown, not 0',
          p1.status_code == 200 and row(z.get('id'))[2] is None)
    p2 = c.patch(f"/api/debt/{z.get('id')}", headers=HJ, json={'interest_rate': '18.9'})
    check('and entering it again stores the number',
          p2.status_code == 200 and row(z.get('id'))[2] == 18.9)

    led = c.post(f"/api/debt/{b.get('id')}/ledger", headers=HJ, json={
        'entry_type': 'payment', 'amount': 50, 'entry_date': '2026-09-01'})
    check('a payment logged against a debt whose balance is unknown does not crash',
          led.status_code in (200, 201))
    check('and the balance stays unknown - no figure is invented from a missing one',
          row(b.get('id'))[1] is None)

    app_js = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    sync = app_js[app_js.index('async function _syncDebtToDb'):][:1500]
    check('the Debt page save sends a blank as null, not parseFloat(x) || 0',
          'interest_rate:      _numOrNull(card.rate)' in sync
          and 'parseFloat(card.rate)        || 0' not in sync
          and 'parseFloat(card.minimum)     || 0' not in sync)
    check('and the bootstrap load keeps a stored null blank instead of defaulting it to 0',
          "c.rate       ?? c.interest_rate   ?? ''" in app_js
          and "c.rate       ?? c.interest_rate   ?? 0," not in app_js)
    check('and a projection that used a missing figure says so',
          'function _debtAssumptionNote' in app_js and '0% APR assumed' in app_js)

    with db_session() as s:
        from core.database import Account, DebtLedgerEntry
        for debt_id in [m for m in made if m]:
            s.query(DebtLedgerEntry).filter_by(debt_account_id=debt_id).delete()
            d = s.get(DebtAccount, debt_id)
            if d is not None:
                acct_id = d.linked_account_id
                s.delete(d)
                if acct_id:
                    s.query(Account).filter_by(id=acct_id).delete()
        s.commit()
