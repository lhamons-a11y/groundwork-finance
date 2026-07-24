"""
Groundwork — pre-deploy smoke test.

Run from C:\\Groundwork (or let deploy.bat run it). Boots the server against
a THROWAWAY temp database — it can never touch real data — and verifies the
critical paths end-to-end. Exit code 0 = safe to deploy, 1 = DO NOT DEPLOY.

Usage:  python smoke_test.py
"""

import os
import re
import sys
import json
import tempfile
from pathlib import Path

# ── Test isolation: MUST happen before any core.database import ──────────────
_TMP = tempfile.mkdtemp(prefix='gw_smoke_')
os.environ['GROUNDWORK_DATA_DIR'] = _TMP

BASE = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / 'core'))

PASS, FAIL = [], []


def check(name, condition):
    (PASS if condition else FAIL).append(name)
    print(f'  {"OK  " if condition else "FAIL"}  {name}')


def main():
    print(f'Groundwork smoke test — temp DB at {_TMP}\n')

    # ── 1. Version consistency across all three files ────────────────────────
    # (server GW_VERSION, app.js GW_VERSION, index.html cache-buster)
    server_src = (BASE / 'server.py').read_text(encoding='utf-8', errors='replace')
    app_src    = (BASE / 'static' / 'js' / 'app.js').read_text(encoding='utf-8', errors='replace')
    html_src   = (BASE / 'static' / 'index.html').read_text(encoding='utf-8', errors='replace')

    v_server = (re.search(r"GW_VERSION\s*=\s*'([^']+)'", server_src) or [None, ''])[1]
    v_app    = (re.search(r"const GW_VERSION = '([^']+)'", app_src) or [None, ''])[1]
    v_cache  = (re.search(r"app\.js\?v=([\w-]+)", html_src) or [None, ''])[1]

    print(f'  versions: server={v_server}  app.js={v_app}  cache-buster={v_cache}')
    check('version strings match (server == app.js == cache-buster)',
          v_server and v_server == v_app == v_cache)

    # ── 2. Boot the server on the temp DB ─────────────────────────────────────
    try:
        from server import create_app, _GW_TOKEN
        app = create_app(static_folder=str(BASE / 'static'))
        c = app.test_client()
        check('server boots (create_app + migrations)', True)
    except Exception as e:
        check(f'server boots — {e}', False)
        return finish()

    H  = {'X-GW-Token': _GW_TOKEN}
    HJ = {**H, 'Content-Type': 'application/json'}

    # ── 3. Health + database integrity ────────────────────────────────────────
    h = c.get('/api/health').get_json()
    check('health endpoint responds', h.get('ok') is True)
    check('database integrity check passes (db_ok)', h.get('db_ok') is True)
    check('health reports matching version', h.get('version') == v_server)

    # ── 4. Token injection + auth enforcement ─────────────────────────────────
    check('token injected on /',            b'GW_SESSION_TOKEN' in c.get('/').data)
    check('token injected on /index.html',  b'GW_SESSION_TOKEN' in c.get('/index.html').data)
    check('API rejects missing token (403)', c.get('/api/settings/bootstrap').status_code == 403)
    check('API accepts valid token (200)',   c.get('/api/settings/bootstrap', headers=H).status_code == 200)

    # ── 5. Performance indexes present ────────────────────────────────────────
    from core.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        idx = {r[0] for r in conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'ix_txn%'"))}
    check('performance indexes exist (3)', len(idx) == 3)

    # ── 6. Core write paths (the gift-budget class of bug) ────────────────────
    r = c.post('/api/budget/items', headers=HJ,
               data=json.dumps({'type': 'expense', 'name': 'SmokeTest', 'amount': 1.0}))
    check('budget item POST persists', r.status_code in (200, 201))
    items = c.get('/api/budget/items', headers=H).get_json().get('data') or []
    check('budget item readback', any(i.get('name') == 'SmokeTest' for i in items))

    r = c.post('/api/trip/budget', headers=HJ, data=json.dumps({'total': 123}))
    rb = (c.get('/api/trip/budget', headers=H).get_json().get('data') or {})
    check('trip budget round-trip', r.status_code == 200 and rb.get('total') == 123)

    # ── 7. Auto-import queue pipeline ─────────────────────────────────────────
    r = c.post('/api/auto-import/queue', headers=HJ,
               data=json.dumps({'filename': 't.qfx', 'content': 'x', 'path': '/t'}))
    p = (c.get('/api/auto-import/pending', headers=H).get_json().get('data') or {})
    check('auto-import queue -> pending -> pop',
          r.status_code == 200 and p.get('filename') == 't.qfx'
          and c.get('/api/auto-import/pending', headers=H).get_json().get('data') is None)

    # ── 8. Error visibility (Phase 1) ─────────────────────────────────────────
    lt = c.get('/api/debug/log-tail', headers=H)
    lt_data = (lt.get_json() or {}).get('data') or {}
    check('log-tail endpoint responds', lt.status_code == 200 and 'log' in lt_data)
    check('server log file created', Path(lt_data.get('path', '/nonexistent')).exists())
    check('app.js has no silent .catch(() => {})',
          '.catch(() => {})' not in app_src.replace("silent `.catch(() => {})`", ''))

    # ── 9. Ghost-ID tripwire (dead-button class) ──────────────────────────────
    # A handler targeting an element that doesn't exist fails in silence —
    # this is how the Net Worth chart went invisible. Known guarded remnants
    # are allowlisted; anything NEW fails the deploy.
    _ALLOWED_GHOSTS = {
        'ledgerSum', 'dashProjectionBadge', 'obBufferStatus', 'obExpUtilities',
        'obNWGoalFields', 'obNWToggle', 'obNoDebtState', 'obScenarioCards',
        'obScenarioWrap', 'obStage1', 'obStage2', 'obStrategyCards',
    }
    refd = set(re.findall(r"\bg\('([^']+)'\)", app_src))
    refd |= set(re.findall(r"getElementById\('([^']+)'\)", app_src))
    have = set(re.findall(r'id="([^"]+)"', html_src))
    have |= set(re.findall(r'id="([^"]+)"', app_src))
    have |= set(re.findall(r"\.id\s*=\s*'([^']+)'", app_src))
    ghosts = {r for r in refd if r not in have and '${' not in r} - _ALLOWED_GHOSTS
    check(f'no new ghost element IDs ({len(ghosts)} found)', not ghosts)
    if ghosts:
        print('      new ghosts:', ', '.join(sorted(ghosts)))
    check('no native prompt() calls (dead in pywebview)',
          not re.search(r'[^.\w]prompt\(', app_src))

    # ── 10. Update channel (Phase 2) ──────────────────────────────────────────
    u = c.get('/api/update-check', headers=H)
    ud = (u.get_json() or {}).get('data') or {}
    check('update-check responds and never crashes offline',
          u.status_code == 200 and 'update_available' in ud)

    # ── 11. price_engine.py contract ──────────────────────────────────────────
    # server.py imports refresh_stale_prices/fetch_prices/validate_ticker/
    # get_portfolio_value from this module inside try/except ImportError, so
    # a missing or broken price_engine.py never crashes the app — it just
    # silently degrades to manual-price-only. That's exactly the failure
    # mode we don't want to ship blind: this check makes it loud instead.
    # Offline only — no network call, just import + signature shape.
    import inspect
    try:
        import price_engine as _pe
        check('price_engine.py imports cleanly', True)

        _PE_CONTRACT = {
            'fetch_prices':         2,  # (tickers, session)
            'refresh_stale_prices': 1,  # (session, force=False)
            'validate_ticker':      1,  # (symbol)
            # get_portfolio_value removed July 8 — its only caller was the
            # dead /api/analytics/net-worth route (removed same sweep). Net
            # Worth pulls live portfolio client-side via /investments/positions.
        }
        for fn_name, min_args in _PE_CONTRACT.items():
            fn = getattr(_pe, fn_name, None)
            check(f'price_engine.{fn_name} exists and is callable',
                  callable(fn))
            if callable(fn):
                params = list(inspect.signature(fn).parameters)
                check(f'price_engine.{fn_name} accepts {min_args} arg(s)',
                      len(params) >= min_args)
    except Exception as e:
        check(f'price_engine.py imports cleanly — {e}', False)

    # ── 12. Frontend sanity (no Node dependency) ──────────────────────────────
    check('app.js is substantial (>500KB)', len(app_src) > 500_000)
    check('app.js has no merge-conflict markers', '<<<<<<<' not in app_src)
    check('index.html has closing </html>', '</html>' in html_src)

    # ── 13. API contract: every client path has a server route ───────────────
    # After the July 8 dead-route sweep, this is the moment a typo'd client
    # path or a deleted-but-still-called route becomes a silent 404 in the
    # field. Template-literal segments (${...}) normalize to a wildcard that
    # matches Flask <converter> segments.
    bp_prefix = dict(re.findall(
        r"(\w+)\s*=\s*Blueprint\([^)]*?url_prefix\s*=\s*['\"]([^'\"]+)['\"]",
        server_src, re.S))
    bp_prefix.update(re.findall(
        r"register_blueprint\(\s*(\w+)\s*,\s*url_prefix\s*=\s*['\"]([^'\"]+)['\"]",
        server_src))
    server_paths = set()
    for bp, path in re.findall(r"@(\w+)\.route\(\s*['\"]([^'\"]*)['\"]", server_src):
        full = bp_prefix.get(bp, '') + path
        server_paths.add(re.sub(r'<[^>]+>', '@', full).rstrip('/'))
    client_paths = set()
    for p in re.findall(r"['\"`](/api/[^'\"`\s]+)", app_src):
        q = re.sub(r'\$\{[^}]*\}', '@', p.split('?')[0]).rstrip('/')
        q = re.sub(r'@+', '@', q)
        # A template var glued to a segment (no slash before it, e.g.
        # `realized-gains${yearQS}`) is a query string or suffix, not a path
        # param — path params are always written `/${id}`. Resolve the glued
        # form against its base path.
        q = re.sub(r'(?<=[^/])@$', '', q)
        client_paths.add(q)
    unmatched = {c for c in client_paths
                 if c not in server_paths
                 and c + '/@' not in server_paths
                 and c + '/@/@' not in server_paths}
    check(f'every client API path has a server route ({len(unmatched)} unmatched)',
          not unmatched)
    if unmatched:
        print('      unmatched:', ', '.join(sorted(unmatched)))

    # ── 14. Null-payoff regression tripwire (bug class #12) ──────────────────
    # `?.months || 0` outside an explicit insufficient/null guard is the exact
    # pattern that rendered "not affordable" as "20 months sooner" (fixed in
    # four BYB locations July 6, two Dashboard locations July 8). Comment
    # lines are skipped (the fix comments quote the pattern verbatim), and
    # the guard window is 8 lines to reach past template-literal blocks.
    _app_lines = app_src.split('\n')
    bad_coerce = []
    for i, line in enumerate(_app_lines, 1):
        if line.strip().startswith('//'):
            continue
        if re.search(r'\?\.months\s*\|\|\s*0', line):
            ctx = _app_lines[max(0, i - 8):i + 1]
            if not any('Insufficient' in l or 'null' in l
                       or 'payoffImpossible' in l for l in ctx):
                bad_coerce.append(i)
    check(f'no unguarded ?.months||0 coercions ({len(bad_coerce)} found)',
          not bad_coerce)
    if bad_coerce:
        print('      lines:', bad_coerce)

    # ── 15. AI provider path (Phase 6D) ───────────────────────────────────────
    # /api/ai/status must always answer 200 — it's what the Settings "Test
    # connection" button and first-run onboarding poll to tell the user
    # whether local AI is reachable. A provider misconfiguration or an
    # unreachable Ollama must show up as an honest status, never a 500 or a
    # silently-dead feature. Offline-safe: this box likely has no Ollama
    # running, so 'reachable' is expected to be False here — the checks are
    # about the shape/honesty of the response, not that a model is present.
    a = c.get('/api/ai/status', headers=H)
    ad = (a.get_json() or {}).get('data') or {}
    check('/api/ai/status responds 200', a.status_code == 200)
    check('ai/status reports a valid provider', ad.get('provider') in ('local', 'cloud'))
    check('ai/status reachability is a real boolean', isinstance(ad.get('reachable'), bool))
    check('ai/status never claims a model when unreachable',
          ad.get('reachable') or not ad.get('active_model'))

    # The client must surface "no model" honestly rather than hide it —
    # tripwire on the literal fallback string so this can't regress silently.
    check("app.js has a 'no model resolved' fallback string",
          'no model resolved' in app_src)
    check("app.js has a 'not reachable' fallback for local AI",
          'Not reachable' in app_src)

    # ── 16. Debt Reconciliation Phase A (data layer) ──────────────────────────
    # No routes exist yet (Phase A is schema + query helpers only — UI lands
    # in Phase B), so this exercises the models and helpers directly against
    # the same temp DB the server booted against.
    from datetime import date as _date, timedelta as _timedelta
    from core.database import (
        DebtAccount as _DA, DebtLedgerEntry as _DLE,
        RecurringDebtPayment as _RDP, CheckingTransactionLink as _CTL,
        Account as _Acct, Transaction as _Txn, db_session as _dbs,
    )
    from server import (
        get_debt_ledger_for_account, get_recurring_payments_due,
        get_checking_transaction_link, serialize_debt_ledger_entry,
    )

    with engine.connect() as conn:
        _new_tables = {row[0] for row in conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
            "('debt_ledger_entries','recurring_debt_payments','checking_transaction_links')"
        ))}
    check('debt reconciliation tables exist (3)', len(_new_tables) == 3)

    with engine.connect() as conn:
        _new_idx = {row[0] for row in conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name IN "
            "('debt_ledger_entries','recurring_debt_payments','checking_transaction_links')"
        ))}
    check('debt reconciliation indexes exist (>=7)', len(_new_idx) >= 7)

    with _dbs() as session:
        debt = _DA(name='Smoke Test Card', current_balance=1000.0)
        session.add(debt)
        session.flush()

        charge  = _DLE(debt_account_id=debt.id, entry_type='charge',  amount=60.0,
                        entry_date=_date(2026, 7, 3), merchant='Costco', source_type='manual')
        payment = _DLE(debt_account_id=debt.id, entry_type='payment', amount=50.0,
                        entry_date=_date(2026, 7, 15), source_type='manual')
        session.add_all([charge, payment])
        session.flush()

        entries = get_debt_ledger_for_account(session, debt.id)
        check('get_debt_ledger_for_account returns both entries', len(entries) == 2)
        check('get_debt_ledger_for_account orders newest-first',
              entries and entries[0].entry_date == _date(2026, 7, 15))

        ser = serialize_debt_ledger_entry(charge)
        check('serialize_debt_ledger_entry shape',
              ser.get('entry_type') == 'charge' and ser.get('amount') == 60.0
              and ser.get('entry_date') == '2026-07-03')

        acct = _Acct(name='Smoke Checking', type='checking')
        session.add(acct)
        session.flush()
        txn = _Txn(date=_date(2026, 7, 15), amount=50.0, type='debit',
                    account_id=acct.id, description='Transfer to Smoke Test Card')
        session.add(txn)
        session.flush()

        link = _CTL(checking_transaction_id=txn.id, debt_ledger_entry_id=payment.id,
                     link_indicator='payment_to_card')
        session.add(link)
        session.flush()

        found = get_checking_transaction_link(session, txn.id)
        check('get_checking_transaction_link finds the link',
              found is not None and found.debt_ledger_entry_id == payment.id)
        check('get_checking_transaction_link returns None for unlinked txn',
              get_checking_transaction_link(session, 999999) is None)

        # Edge case: same checking txn linked to the same debt entry twice must
        # be rejected (UniqueConstraint), not silently duplicated.
        dup_rejected = False
        try:
            session.add(_CTL(checking_transaction_id=txn.id, debt_ledger_entry_id=payment.id,
                              link_indicator='payment_to_card'))
            session.flush()
        except Exception:
            dup_rejected = True
            session.rollback()
        check('duplicate checking-debt link is rejected', dup_rejected)

        recurring = _RDP(debt_account_id=debt.id, scheduled_date_of_month=15,
                          amount=735.0, frequency='monthly', is_active=True)
        session.add(recurring)
        session.flush()

        due_in_window     = get_recurring_payments_due(session, _date(2026, 8, 10), _date(2026, 8, 20))
        due_outside_window= get_recurring_payments_due(session, _date(2026, 8, 1),  _date(2026, 8, 9))
        check('get_recurring_payments_due finds a payment due on the 15th',
              len(due_in_window) == 1 and due_in_window[0]['due_date'] == _date(2026, 8, 15))
        check('get_recurring_payments_due excludes payments outside the window',
              len(due_outside_window) == 0)

        # "Last day of month" (scheduled_date_of_month=None) must clamp to the
        # real last day, not overflow into the next month.
        recurring_eom = _RDP(debt_account_id=debt.id, scheduled_date_of_month=None,
                              amount=100.0, frequency='monthly', is_active=True)
        session.add(recurring_eom)
        session.flush()
        due_eom = get_recurring_payments_due(session, _date(2026, 2, 25), _date(2026, 2, 28))
        check('get_recurring_payments_due clamps "last day" for a 28-day month',
              any(d['due_date'] == _date(2026, 2, 28) for d in due_eom))

        session.rollback()   # smoke fixtures never persist past this check

    # ── 17. Debt Reconciliation Phase B (ledger routes) ───────────────────────
    # Exercises the actual HTTP routes (list_debt_ledger, create_debt_ledger_entry,
    # delete_debt_ledger_entry, list_linkable_transactions) through the Flask
    # test client, not the helpers directly — those were covered in section 16.
    with _dbs() as session:
        debt2 = _DA(name='Phase B Smoke Card', current_balance=500.0)
        session.add(debt2)
        session.flush()
        acct2 = _Acct(name='Phase B Smoke Checking', type='checking')
        session.add(acct2)
        session.flush()
        debt2.linked_account_id = acct2.id
        txn2 = _Txn(date=_date(2026, 7, 20), amount=75.0, type='debit',
                     account_id=acct2.id, description='Transfer to Phase B Smoke Card')
        session.add(txn2)
        session.commit()
        _debt2_id, _acct2_id, _txn2_id = debt2.id, acct2.id, txn2.id

    r = c.post(f'/api/debt/{_debt2_id}/ledger', headers=HJ, data=json.dumps({
        'entry_type': 'charge', 'amount': 40.0, 'entry_date': '2026-07-15', 'merchant': 'Target'}))
    check('POST ledger charge succeeds (201)', r.status_code == 201)
    _charge_id = (r.get_json() or {}).get('data', {}).get('id')

    r = c.get(f'/api/debt/{_debt2_id}/ledger', headers=H)
    ledger_data = (r.get_json() or {}).get('data') or []
    check('GET ledger returns the created charge', any(e['id'] == _charge_id for e in ledger_data))

    r = c.post(f'/api/debt/{_debt2_id}/ledger', headers=HJ, data=json.dumps({
        'entry_type': 'nonsense', 'amount': 10.0}))
    check('POST ledger rejects invalid entry_type (400)', r.status_code == 400)

    r = c.post(f'/api/debt/{_debt2_id}/ledger', headers=HJ, data=json.dumps({
        'entry_type': 'charge', 'amount': -5.0}))
    check('POST ledger rejects non-positive amount (400)', r.status_code == 400)

    r = c.post('/api/debt/999999/ledger', headers=HJ, data=json.dumps({
        'entry_type': 'charge', 'amount': 10.0}))
    check('POST ledger 404s for unknown debt account', r.status_code == 404)

    r = c.get(f'/api/debt/{_debt2_id}/linkable-transactions', headers=H)
    linkable = (r.get_json() or {}).get('data') or []
    check('linkable-transactions lists the unlinked checking txn',
          any(t['id'] == _txn2_id for t in linkable))

    r = c.post(f'/api/debt/{_debt2_id}/ledger', headers=HJ, data=json.dumps({
        'entry_type': 'payment', 'amount': 75.0, 'entry_date': '2026-07-20',
        'linked_checking_transaction_id': _txn2_id}))
    check('POST ledger payment with link succeeds (201)', r.status_code == 201)
    _payment_id = (r.get_json() or {}).get('data', {}).get('id')

    r = c.post(f'/api/debt/{_debt2_id}/ledger', headers=HJ, data=json.dumps({
        'entry_type': 'payment', 'amount': 1.0, 'linked_checking_transaction_id': _txn2_id}))
    check('POST ledger rejects re-linking an already-linked txn (400)', r.status_code == 400)

    r = c.get(f'/api/debt/{_debt2_id}/linkable-transactions', headers=H)
    linkable_after = (r.get_json() or {}).get('data') or []
    check('linkable-transactions excludes the now-linked txn',
          not any(t['id'] == _txn2_id for t in linkable_after))

    r = c.delete(f'/api/debt/ledger/{_payment_id}', headers=H)
    check('DELETE ledger entry succeeds', r.status_code == 200)

    r = c.get(f'/api/debt/{_debt2_id}/linkable-transactions', headers=H)
    linkable_restored = (r.get_json() or {}).get('data') or []
    check('deleting the entry frees the checking txn to link again',
          any(t['id'] == _txn2_id for t in linkable_restored))

    r = c.delete('/api/debt/ledger/999999', headers=H)
    check('DELETE unknown ledger entry 404s', r.status_code == 404)

    # ── 18. Debt Reconciliation Phase C (recurring drafts) ────────────────────
    with _dbs() as session:
        debt3 = _DA(name='Phase C Smoke Card', current_balance=200.0)
        session.add(debt3)
        session.commit()
        _debt3_id = debt3.id

    r = c.post(f'/api/debt/{_debt3_id}/recurring', headers=HJ, data=json.dumps({
        'amount': 60.0, 'frequency': 'monthly', 'scheduled_date_of_month': 15}))
    check('POST recurring succeeds (201)', r.status_code == 201)
    _recurring_id = (r.get_json() or {}).get('data', {}).get('id')

    r = c.post(f'/api/debt/{_debt3_id}/recurring', headers=HJ, data=json.dumps({
        'amount': 10.0, 'frequency': 'yearly'}))
    check('POST recurring rejects invalid frequency (400)', r.status_code == 400)

    r = c.post(f'/api/debt/{_debt3_id}/recurring', headers=HJ, data=json.dumps({
        'amount': 10.0, 'scheduled_date_of_month': 45}))
    check('POST recurring rejects out-of-range day (400)', r.status_code == 400)

    r = c.get(f'/api/debt/{_debt3_id}/recurring', headers=H)
    recurring_list = (r.get_json() or {}).get('data') or []
    check('GET recurring lists the created pattern',
          any(rp['id'] == _recurring_id for rp in recurring_list))

    # Force this pattern's due date into the generator's lookahead window
    # regardless of what day "today" is in this run, so draft generation is
    # actually exercised rather than skipped by chance.
    with _dbs() as session:
        rp = session.query(_RDP).get(_recurring_id)
        rp.scheduled_date_of_month = (_date.today() + _timedelta(days=2)).day
        session.commit()

    r = c.get('/api/debt/drafts/pending', headers=H)
    pending = (r.get_json() or {}).get('data') or []
    _draft = next((d for d in pending if d.get('debt_account_id') == _debt3_id), None)
    check('GET drafts/pending materializes a draft for the due pattern', _draft is not None)

    # Idempotency: fetching again must not create a second draft for the same
    # (recurring, due_date) pair.
    r = c.get('/api/debt/drafts/pending', headers=H)
    pending_again = (r.get_json() or {}).get('data') or []
    check('GET drafts/pending is idempotent (no duplicate draft)',
          len([d for d in pending_again if d.get('debt_account_id') == _debt3_id]) == 1)

    if _draft:
        r = c.post(f'/api/debt/drafts/{_draft["id"]}/confirm', headers=HJ, data=json.dumps({'amount': 65.0}))
        check('POST draft confirm with edited amount succeeds', r.status_code == 200)
        confirmed = (r.get_json() or {}).get('data') or {}
        check('confirmed draft has edited amount and source_type manual',
              confirmed.get('amount') == 65.0 and confirmed.get('source_type') == 'manual')
        check('confirmed draft description no longer says "(draft)"',
              confirmed.get('description') == 'Recurring payment')

    r = c.post(f'/api/debt/drafts/999999/confirm', headers=HJ, data=json.dumps({}))
    check('POST draft confirm 404s for unknown draft', r.status_code == 404)

    # Regression test for the skip-then-regenerate bug caught during Phase C
    # browser testing: skipping must be a durable marker, not a delete —
    # otherwise generate_recurring_payment_drafts sees no entry for that due
    # date and silently recreates the exact draft the user just dismissed.
    with _dbs() as session:
        rp2 = _RDP(debt_account_id=_debt3_id, scheduled_date_of_month=(_date.today() + _timedelta(days=1)).day,
                    amount=30.0, frequency='monthly', is_active=True)
        session.add(rp2)
        session.commit()
        _rp2_id = rp2.id

    r = c.get('/api/debt/drafts/pending', headers=H)
    pending2 = (r.get_json() or {}).get('data') or []
    _draft2 = next((d for d in pending2 if d.get('debt_account_id') == _debt3_id and d['id'] != (_draft or {}).get('id')), None)
    check('a second due pattern produces a second draft', _draft2 is not None)

    if _draft2:
        r = c.post(f'/api/debt/drafts/{_draft2["id"]}/skip', headers=HJ, data=json.dumps({}))
        check('POST draft skip succeeds', r.status_code == 200)
        skipped_entry = (r.get_json() or {}).get('data') or {}
        check('skipped entry has source_type skipped (not deleted)',
              skipped_entry.get('source_type') == 'skipped')

        r = c.get('/api/debt/drafts/pending', headers=H)
        pending3 = (r.get_json() or {}).get('data') or []
        check('skipped draft does not reappear in pending list',
              not any(d['id'] == _draft2['id'] for d in pending3))

        r = c.get('/api/debt/drafts/pending', headers=H)   # call again — the actual regression scenario
        pending4 = (r.get_json() or {}).get('data') or []
        check('skipped draft does not regenerate on a second fetch (regression)',
              not any(d.get('debt_account_id') == _debt3_id and d['entry_date'] == skipped_entry['entry_date']
                      for d in pending4))

    r = c.patch(f'/api/debt/recurring/{_recurring_id}', headers=HJ, data=json.dumps({'is_active': False}))
    check('PATCH recurring pauses the pattern', r.status_code == 200
          and (r.get_json() or {}).get('data', {}).get('is_active') is False)

    r = c.delete(f'/api/debt/recurring/{_recurring_id}', headers=H)
    soft_deleted = (r.get_json() or {}).get('data') or {}
    check('DELETE recurring soft-deletes (is_active False, row still exists)',
          r.status_code == 200 and soft_deleted.get('is_active') is False)

    r = c.get(f'/api/debt/{_debt3_id}/recurring', headers=H)
    still_listed = (r.get_json() or {}).get('data') or []
    check('soft-deleted recurring pattern still appears in list (audit trail)',
          any(rp['id'] == _recurring_id for rp in still_listed))

    # ── 19. Debt Reconciliation Phase D (checking transaction linking) ───────
    with _dbs() as session:
        debt4 = _DA(name='Phase D Smoke Card', current_balance=150.0)
        session.add(debt4); session.flush()
        acct4 = _Acct(name='Phase D Smoke Checking', type='checking')
        session.add(acct4); session.flush()
        txn4 = _Txn(date=_date(2026, 7, 22), amount=80.0, type='debit',
                     account_id=acct4.id, description='Transfer to Phase D Smoke Card')
        session.add(txn4)
        session.commit()
        _debt4_id, _txn4_id = debt4.id, txn4.id

    r = c.get('/api/transactions', headers=H)
    txn_list = (r.get_json() or {}).get('data') or []
    check('GET transactions includes linked_debt_entry_id (null pre-link)',
          any(t['id'] == _txn4_id and t.get('linked_debt_entry_id') is None for t in txn_list))

    r = c.post(f'/api/transactions/{_txn4_id}/link-debt', headers=HJ,
               data=json.dumps({'debt_account_id': _debt4_id}))
    check('POST link-debt succeeds (201)', r.status_code == 201)
    linked_entry = (r.get_json() or {}).get('data') or {}
    _linked_entry_id = linked_entry.get('id')
    check('link-debt-created entry is a payment for the txn amount',
          linked_entry.get('entry_type') == 'payment' and linked_entry.get('amount') == 80.0)

    r = c.get('/api/transactions', headers=H)
    txn_list2 = (r.get_json() or {}).get('data') or []
    check('GET transactions now reports linked_debt_entry_id',
          any(t['id'] == _txn4_id and t.get('linked_debt_entry_id') == _linked_entry_id for t in txn_list2))

    r = c.post(f'/api/transactions/{_txn4_id}/link-debt', headers=HJ,
               data=json.dumps({'debt_account_id': _debt4_id}))
    check('POST link-debt rejects an already-linked txn (400)', r.status_code == 400)

    r = c.post('/api/transactions/999999/link-debt', headers=HJ,
               data=json.dumps({'debt_account_id': _debt4_id}))
    check('POST link-debt 404s for unknown transaction', r.status_code == 404)

    r = c.get(f'/api/debt/ledger/{_linked_entry_id}', headers=H)
    check('GET single ledger entry succeeds', r.status_code == 200)

    r = c.get('/api/debt/ledger/999999', headers=H)
    check('GET single ledger entry 404s for unknown id', r.status_code == 404)

    r = c.post(f'/api/debt/ledger/{_linked_entry_id}/unlink', headers=HJ, data=json.dumps({}))
    check('POST unlink succeeds', r.status_code == 200)
    unlinked_entry = (r.get_json() or {}).get('data') or {}
    check('unlinked debt entry still exists with no checking link',
          unlinked_entry.get('linked_checking_transaction_id') is None)

    r = c.get('/api/transactions', headers=H)
    txn_list3 = (r.get_json() or {}).get('data') or []
    check('unlink clears linked_debt_entry_id on the checking side too',
          any(t['id'] == _txn4_id and t.get('linked_debt_entry_id') is None for t in txn_list3))

    r = c.get(f'/api/debt/{_debt4_id}/ledger', headers=H)
    ledger_after_unlink = (r.get_json() or {}).get('data') or []
    check('debt entry was NOT deleted by unlink (distinct from Phase B delete)',
          any(e['id'] == _linked_entry_id for e in ledger_after_unlink))

    r = c.post('/api/debt/ledger/999999/unlink', headers=HJ, data=json.dumps({}))
    check('POST unlink 404s for unknown entry', r.status_code == 404)

    # ── 20. Debt Reconciliation Phase E (balance sync + compliance) ──────────
    with _dbs() as session:
        debt5 = _DA(name='Phase E Smoke Card', current_balance=1000.0)
        session.add(debt5)
        session.commit()
        _debt5_id = debt5.id

    def _bal():
        r = c.get('/api/debt', headers=H)
        rows = (r.get_json() or {}).get('data') or []
        return next(d['current_balance'] for d in rows if d['id'] == _debt5_id)

    check('starting balance is 1000', _bal() == 1000.0)

    r = c.post(f'/api/debt/{_debt5_id}/ledger', headers=HJ,
               data=json.dumps({'entry_type': 'charge', 'amount': 150.0, 'entry_date': '2026-07-20'}))
    check('charge entry increases balance (1000 -> 1150)', r.status_code == 201 and _bal() == 1150.0)
    _charge5_id = (r.get_json() or {}).get('data', {}).get('id')

    r = c.post(f'/api/debt/{_debt5_id}/ledger', headers=HJ,
               data=json.dumps({'entry_type': 'payment', 'amount': 200.0, 'entry_date': '2026-07-22'}))
    check('payment entry decreases balance (1150 -> 950)', r.status_code == 201 and _bal() == 950.0)
    _payment5_id = (r.get_json() or {}).get('data', {}).get('id')

    r = c.delete(f'/api/debt/ledger/{_payment5_id}', headers=H)
    check('deleting a manual entry reverses its balance effect (950 -> 1150)',
          r.status_code == 200 and _bal() == 1150.0)

    # A draft must NOT move the balance until it's actually confirmed.
    with _dbs() as session:
        rp5 = _RDP(debt_account_id=_debt5_id, scheduled_date_of_month=(_date.today() + _timedelta(days=1)).day,
                    amount=80.0, frequency='monthly', is_active=True)
        session.add(rp5)
        session.commit()
        _rp5_id = rp5.id

    r = c.get('/api/debt/drafts/pending', headers=H)
    pending5 = [d for d in ((r.get_json() or {}).get('data') or []) if d.get('debt_account_id') == _debt5_id]
    check('a pending draft does not move the balance', len(pending5) == 1 and _bal() == 1150.0)

    _draft5 = pending5[0]
    r = c.post(f'/api/debt/drafts/{_draft5["id"]}/confirm', headers=HJ, data=json.dumps({'amount': 70.0}))
    check('confirming a draft applies its (possibly edited) balance effect (1150 -> 1080)',
          r.status_code == 200 and _bal() == 1080.0)

    r = c.get(f'/api/debt/{_debt5_id}/recurring', headers=H)
    recur5 = next(rp for rp in (r.get_json() or {}).get('data') or [] if rp['id'] == _rp5_id)
    comp = recur5.get('compliance') or {}
    # (70 - 80) / 80 * 100 = -12.5% — outside the ±5% on-time band, so under_plan.
    check('compliance reflects the confirmed variance vs. the pattern amount',
          comp.get('total') == 1 and comp.get('under_plan') == 1 and comp.get('avg_variance_pct') == -12.5)

    # Skipping a draft must never move the balance — it never represented
    # money moving in the first place.
    with _dbs() as session:
        rp5b = _RDP(debt_account_id=_debt5_id, scheduled_date_of_month=(_date.today() + _timedelta(days=1)).day,
                     amount=40.0, frequency='monthly', is_active=True)
        session.add(rp5b)
        session.commit()

    r = c.get('/api/debt/drafts/pending', headers=H)
    pending5b = [d for d in ((r.get_json() or {}).get('data') or []) if d.get('debt_account_id') == _debt5_id]
    _draft5b = next(d for d in pending5b if d['id'] != _draft5['id'])
    r = c.post(f'/api/debt/drafts/{_draft5b["id"]}/skip', headers=HJ, data=json.dumps({}))
    check('skipping a draft does not move the balance', r.status_code == 200 and _bal() == 1080.0)

    # Linking from the checking side also applies the balance effect.
    with _dbs() as session:
        acct5 = _Acct(name='Phase E Smoke Checking', type='checking')
        session.add(acct5); session.flush()
        txn5 = _Txn(date=_date(2026, 7, 23), amount=30.0, type='debit',
                     account_id=acct5.id, description='Transfer to Phase E Smoke Card')
        session.add(txn5)
        session.commit()
        _txn5_id = txn5.id

    r = c.post(f'/api/transactions/{_txn5_id}/link-debt', headers=HJ, data=json.dumps({'debt_account_id': _debt5_id}))
    check('linking from the checking side applies the balance effect (1080 -> 1050)',
          r.status_code == 201 and _bal() == 1050.0)
    _linked5_id = (r.get_json() or {}).get('data', {}).get('id')

    r = c.post(f'/api/debt/ledger/{_linked5_id}/unlink', headers=HJ, data=json.dumps({}))
    check('unlinking does NOT reverse the balance (the payment still happened, only the link is gone)',
          r.status_code == 200 and _bal() == 1050.0)

    return finish()


def finish():
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed')
    if FAIL:
        print('\nDO NOT DEPLOY — failures:')
        for f in FAIL:
            print(f'  - {f}')
        return 1
    print('ALL CLEAR — safe to deploy.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
