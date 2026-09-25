"""V2: a debt's current APR and minimum carry their source, and a statement's stay put.

Four things set a debt's APR - what the user types, a reconciled statement, the
implied-APR alert and the APR estimator - and all four used to land in one column
with no record of which. Now each records 'user', 'statement' or 'calculated'.
Because the Debt page resends every field on every edit, the source moves only
when the value actually changes. And the page takes up the statement's figures
after a reconcile, so a later save cannot send the old ones back over them.
"""
import tempfile
from pathlib import Path


def run(ctx):
    check, c, HJ = ctx.check, ctx.c, ctx.HJ
    from core.database import DebtAccount
    from server import db_session

    def body(resp):
        j = resp.get_json() or {}
        return j.get('data') or j

    def src(debt_id):
        with db_session() as s:
            d = s.get(DebtAccount, debt_id)
            return (d.interest_rate, d.interest_rate_source, d.minimum_payment, d.minimum_payment_source)

    made = c.post('/api/debt', headers=HJ, json={
        'name': 'V2 Source Card', 'begin_balance': 3800, 'current_balance': 3800,
        'interest_rate': 22.9, 'minimum_payment': 114})
    did = body(made).get('id')
    check('V2: a figure the user types is recorded as theirs',
          src(did) == (22.9, 'user', 114.0, 'user'))

    blank = c.post('/api/debt', headers=HJ, json={'name': 'V2 Blank Card', 'interest_rate': None})
    bid = body(blank).get('id')
    check('and an unknown figure has no source rather than a guessed one',
          src(bid)[1] is None)

    rec = c.post('/api/debt/pdf-reconcile', headers=HJ, json={
        'debt_id': did, 'summary': {'statementPeriod': '2026-08-28', 'newBalance': 3800,
                                    'apr': 24.9, 'minimumPayment': 117}})
    r = body(rec)
    check('a reconciled statement sets the APR and minimum, sourced to the statement',
          rec.status_code == 200 and src(did) == (24.9, 'statement', 117.0, 'statement'))
    check('and reports what it replaced, and whose it was, for the page to say so',
          r.get('previous_interest_rate') == 22.9 and r.get('previous_interest_rate_source') == 'user'
          and r.get('interest_rate') == 24.9 and r.get('statement_period_end') == '2026-08-28')

    resend = c.patch(f'/api/debt/{did}', headers=HJ, json={
        'interest_rate': 24.9, 'minimum_payment': 117, 'due_day': 22,
        'interest_rate_source': 'user', 'minimum_payment_source': 'user'})
    check('an ordinary save that resends the same APR (editing the due day) keeps the statement as its source',
          resend.status_code == 200 and src(did)[:4] == (24.9, 'statement', 117.0, 'statement'))

    got = body(c.get('/api/debt', headers=HJ))
    row = next((x for x in (got if isinstance(got, list) else []) if x.get('id') == did), {})
    check('the API gives the page the source and the statement date to show',
          row.get('interest_rate_source') == 'statement' and row.get('statement_as_of') == '2026-08-28')

    c.patch(f'/api/debt/{did}', headers=HJ, json={'interest_rate': 23.5, 'interest_rate_source': 'user'})
    check('typing a new APR makes it the user\'s again', src(did)[:2] == (23.5, 'user'))

    c.patch(f'/api/debt/{did}', headers=HJ, json={'interest_rate': 21.0, 'interest_rate_source': 'calculated'})
    check('the implied-APR alert or the estimator records a calculation', src(did)[:2] == (21.0, 'calculated'))

    c.patch(f'/api/debt/{did}', headers=HJ, json={'interest_rate': 20.0, 'interest_rate_source': 'statement'})
    check('a client cannot claim a statement as the source - only a reconcile sets that',
          src(did)[:2] == (20.0, 'user'))

    c.patch(f'/api/debt/{did}', headers=HJ, json={'interest_rate': ''})
    check('clearing the APR clears its source with it', src(did)[:2] == (None, None))

    # The migration adds the columns to a database from before them, and existing rows get no source.
    import migrate
    import sqlalchemy as sa
    old_engine = migrate.engine
    tmp = Path(tempfile.mkdtemp(prefix='gw_v2_mig_')) / 'old.db'
    eng = sa.create_engine(f'sqlite:///{tmp}')
    with eng.connect() as conn:
        conn.execute(sa.text('CREATE TABLE debt_accounts (id INTEGER PRIMARY KEY, name VARCHAR(120), interest_rate FLOAT)'))
        conn.execute(sa.text("INSERT INTO debt_accounts (name, interest_rate) VALUES ('Old Card', 19.9)"))
        conn.commit()
    try:
        migrate.engine = eng
        migrate._add_missing_columns('debt_accounts', migrate._NEW_DEBT_COLUMNS)
    finally:
        migrate.engine = old_engine
    with eng.connect() as conn:
        cols = {r[1] for r in conn.execute(sa.text('PRAGMA table_info(debt_accounts)'))}
        old_row = conn.execute(sa.text(
            "SELECT interest_rate, interest_rate_source, minimum_payment_source FROM debt_accounts")).fetchone()
    eng.dispose()
    check('the migration adds both source columns to a database from before them',
          {'interest_rate_source', 'minimum_payment_source'} <= cols)
    check('and an existing row keeps its APR with no source, not a guessed one',
          tuple(old_row) == (19.9, None, None))

    app_js = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    check('after a reconcile the page takes up the statement\'s APR, so a later save cannot revert it',
          "linkedCard.rate    = String(rec.interest_rate)" in app_js)
    check('and the toast says what the statement replaced',
          'function _statementFigureChanges' in app_js and '_changes ? `. ${_changes}`' in app_js)

    with db_session() as s:
        from core.database import Account, DebtBalanceHistory
        for debt_id in (did, bid):
            if not debt_id:
                continue
            s.query(DebtBalanceHistory).filter_by(debt_id=debt_id).delete()
            d = s.get(DebtAccount, debt_id)
            if d is not None:
                acct_id = d.linked_account_id
                s.delete(d)
                if acct_id:
                    s.query(Account).filter_by(id=acct_id).delete()
        s.commit()
