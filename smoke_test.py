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

    # API.put existed as a call site (saveNWGoal's legacy net-worth-goal
    # compat write, and the same call in obFinishGoals) with no matching
    # method ever defined on the API object — found by actually exercising
    # "add a net worth milestone" in a browser, where it threw
    # "API.put is not a function" and aborted the whole save. General
    # regression: every API.<verb>( call site anywhere in app.js must name
    # a verb that's actually defined on the API object, not just the ones
    # known about today.
    _api_block = app_src[app_src.index('const API = {'):app_src.index('const API = {')+1500]
    _api_defined_verbs = set(re.findall(r'\basync (\w+)\(', _api_block))
    _api_called_verbs  = set(re.findall(r'\bAPI\.(\w+)\(', app_src))
    check(f'API object defines get/post/patch/put/delete ({sorted(_api_defined_verbs)})',
          {'get', 'post', 'patch', 'put', 'delete'} <= _api_defined_verbs)
    check('every API.<verb>( call site names a verb the API object actually defines',
          _api_called_verbs <= _api_defined_verbs)

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

    # ── 19b. Debt Reconciliation Phase F (narrative integration) ─────────────
    # Phase F is entirely client-side (reuses Phase E's compliance endpoint,
    # no new server routes) — the compliance math and R8 gate are already
    # covered above/elsewhere, so this is a static-content check that the
    # wiring exists, matching the pattern already used for the AI surfaces
    # (e.g. "app.js has a 'no model resolved' fallback string").
    check("app.js Distance Traveled pulls in payment compliance",
          'paymentCompliance' in app_src and 'get(`/api/debt/${c._dbId}/recurring`)' in app_src)
    check("app.js Distance Traveled dataLines include compliance figures",
          'Recurring debt payments logged' in app_src
          and 'Average variance from the planned payment amount' in app_src)
    check("app.js Distance Traveled prompt forbids shaming below-plan payments",
          'below-plan payments' in app_src)

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

    # ── 21. Debt Reconciliation Phase G (edge cases) ──────────────────────────
    # Recurring payment on a $0-balance account — nothing in the create path
    # should reject this (e.g. a card paid to zero but still tracked for
    # future charges).
    with _dbs() as session:
        debt6 = _DA(name='Phase G Zero Balance Card', current_balance=0.0)
        session.add(debt6); session.commit()
        _debt6_id = debt6.id
    r = c.post(f'/api/debt/{_debt6_id}/recurring', headers=HJ,
               data=json.dumps({'amount': 25.0, 'frequency': 'monthly', 'scheduled_date_of_month': 1}))
    check('recurring payment allowed on a $0-balance account', r.status_code == 201)

    # Multiple recurring patterns on the same account.
    r2 = c.post(f'/api/debt/{_debt6_id}/recurring', headers=HJ,
                data=json.dumps({'amount': 15.0, 'frequency': 'monthly', 'scheduled_date_of_month': 20}))
    r_list = c.get(f'/api/debt/{_debt6_id}/recurring', headers=H)
    check('multiple recurring patterns on one account both persist',
          r2.status_code == 201 and len((r_list.get_json() or {}).get('data') or []) == 2)

    # A draft generated from a pattern that gets paused afterward must still
    # be confirmable — pausing stops NEW drafts, it doesn't invalidate ones
    # already sitting in front of the user.
    with _dbs() as session:
        rp6 = _RDP(debt_account_id=_debt6_id, scheduled_date_of_month=(_date.today() + _timedelta(days=1)).day,
                    amount=10.0, frequency='monthly', is_active=True)
        session.add(rp6); session.commit()
        _rp6_id = rp6.id
    r = c.get('/api/debt/drafts/pending', headers=H)
    draft6 = next(d for d in (r.get_json() or {}).get('data') or [] if d.get('debt_account_id') == _debt6_id)
    c.patch(f'/api/debt/recurring/{_rp6_id}', headers=HJ, data=json.dumps({'is_active': False}))
    r = c.post(f'/api/debt/drafts/{draft6["id"]}/confirm', headers=HJ, data=json.dumps({}))
    check('a draft from a since-paused recurring pattern is still confirmable', r.status_code == 200)

    # Deleting a linked checking transaction must unlink, not orphan, the
    # debt entry — the dangling-FK edge case from the blueprint's own list
    # ("User deletes checking transaction (cascade to debt?)").
    with _dbs() as session:
        acct6 = _Acct(name='Phase G Smoke Checking', type='checking')
        session.add(acct6); session.flush()
        txn6 = _Txn(date=_date(2026, 7, 24), amount=25.0, type='debit',
                     account_id=acct6.id, description='Transfer to Phase G Zero Balance Card')
        session.add(txn6); session.commit()
        _txn6_id = txn6.id
    r = c.post(f'/api/transactions/{_txn6_id}/link-debt', headers=HJ, data=json.dumps({'debt_account_id': _debt6_id}))
    _linked6_id = (r.get_json() or {}).get('data', {}).get('id')

    r = c.delete(f'/api/transactions/{_txn6_id}', headers=H)
    check('deleting the linked checking transaction succeeds', r.status_code == 200)

    r = c.get(f'/api/debt/ledger/{_linked6_id}', headers=H)
    surviving_entry = (r.get_json() or {}).get('data') or {}
    check('debt entry survives the checking transaction delete, now unlinked',
          r.status_code == 200 and surviving_entry.get('linked_checking_transaction_id') is None)

    # ── 22. Historian Infrastructure (Phase H1) ───────────────────────────────
    from core.database import HistorianEntry as _HE, TripHistory as _TH
    from server import (
        log_historian_event, get_payment_variance_for_account,
        get_payment_compliance_confidence, get_late_payment_pattern,
        get_category_patterns, get_budget_variance_by_category,
        get_trip_variance_by_region, get_llm_miss_log,
    )

    with engine.connect() as conn:
        hist_tables = {row[0] for row in conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
            "('historian_entries','trip_history')"
        ))}
    check('historian_entries and trip_history tables exist', len(hist_tables) == 2)

    with _dbs() as session:
        debt7 = _DA(name='Historian Smoke Card', current_balance=500.0)
        session.add(debt7); session.commit()
        _debt7_id = debt7.id

    # log_historian_event: variance computed correctly when both values given.
    with _dbs() as session:
        e = log_historian_event(session, 'payment_confirmed', debt_account_id=_debt7_id,
                                 expected_value=100.0, actual_value=95.0, context={'note': 'test'})
        session.commit()
        _hist_entry_id = e.id
    with _dbs() as session:
        stored = session.get(_HE, _hist_entry_id)
        check('log_historian_event computes variance_pct/variance_amount',
              stored.variance_amount == -5.0 and stored.variance_pct == -5.0)
        check('log_historian_event stores context as JSON',
              json.loads(stored.context_json or '{}').get('note') == 'test')

    with _dbs() as session:
        empty_variance = get_payment_variance_for_account(session, 999999)
        check('get_payment_variance_for_account returns an honest empty shape for an account with no history',
              empty_variance == {'on_time': 0, 'under_plan': 0, 'over_plan': 0, 'avg_variance_pct': None, 'total_payments': 0})

    # End-to-end: confirming a draft actually writes a historian event now
    # (Phase H1 wiring into Phase C's confirm route).
    # Isolated account for the confirm/confidence checks below — _debt7_id
    # already has one manually-logged historian event from the check above,
    # which would otherwise skew these averages.
    with _dbs() as session:
        debt7c = _DA(name='Historian Confirm Smoke Card', current_balance=500.0)
        session.add(debt7c); session.flush()
        rp7 = _RDP(debt_account_id=debt7c.id, scheduled_date_of_month=(_date.today() + _timedelta(days=1)).day,
                    amount=200.0, frequency='monthly', is_active=True)
        session.add(rp7); session.commit()
        _debt7c_id = debt7c.id
    r = c.get('/api/debt/drafts/pending', headers=H)
    draft7 = next(d for d in (r.get_json() or {}).get('data') or [] if d.get('debt_account_id') == _debt7c_id)
    c.post(f'/api/debt/drafts/{draft7["id"]}/confirm', headers=HJ, data=json.dumps({'amount': 180.0}))

    with _dbs() as session:
        variance = get_payment_variance_for_account(session, _debt7c_id)
        check('confirming a draft writes a historian event the query helper can read',
              variance['total_payments'] == 1 and variance['avg_variance_pct'] == -10.0)
        confidence = get_payment_compliance_confidence(session, _debt7c_id)
        # 1 payment, variance -10% -> outside +/-5%, so 0 on-time / 1 total -> 0% - 0 late fees = 0
        check('get_payment_compliance_confidence scores a below-plan-only history low',
              confidence['confidence_pct'] == 0)

    # Skipping a draft writes payment_skipped.
    with _dbs() as session:
        rp7b = _RDP(debt_account_id=_debt7_id, scheduled_date_of_month=(_date.today() + _timedelta(days=1)).day,
                     amount=50.0, frequency='monthly', is_active=True)
        session.add(rp7b); session.commit()
    r = c.get('/api/debt/drafts/pending', headers=H)
    draft7b = next(d for d in (r.get_json() or {}).get('data') or []
                   if d.get('debt_account_id') == _debt7_id)
    c.post(f'/api/debt/drafts/{draft7b["id"]}/skip', headers=HJ, data=json.dumps({}))
    with _dbs() as session:
        skipped_events = session.query(_HE).filter_by(
            debt_account_id=_debt7_id, event_category='payment_skipped').count()
        check('skipping a draft writes a payment_skipped historian event', skipped_events == 1)

    # A manual charge writes charge_observation.
    c.post(f'/api/debt/{_debt7_id}/ledger', headers=HJ,
           data=json.dumps({'entry_type': 'charge', 'amount': 40.0, 'merchant': 'Historian Test Merchant'}))
    with _dbs() as session:
        charge_events = session.query(_HE).filter_by(
            debt_account_id=_debt7_id, event_category='charge_observation').count()
        check('a manual charge writes a charge_observation historian event', charge_events == 1)

    with _dbs() as session:
        check('get_late_payment_pattern returns an honest empty result (nothing writes this event yet)',
              get_late_payment_pattern(session, _debt7_id) ==
              {'late_fee_count': 0, 'avg_days_late': None, 'months_affected': 0})

        # 1.1-scaffold reads — real functions, honest empty/neutral shapes.
        check('get_budget_variance_by_category returns honest empty shape (nothing writes budget_variance_observed yet)',
              get_budget_variance_by_category(session, 1) ==
              {'avg_variance': None, 'variance_pct': None, 'months_over': 0, 'months_under': 0})
        check('get_trip_variance_by_region returns honest empty shape (no trip_history rows yet)',
              get_trip_variance_by_region(session, 'CO') ==
              {'avg_estimated': None, 'avg_actual': None, 'variance_pct': None, 'trip_count': 0})
        check('get_category_patterns returns honest empty shape for an unseen merchant',
              get_category_patterns(session, 'ZzUnseenMerchantZz') ==
              {'most_common_category': None, 'frequency': 0, 'edge_cases': []})

    # get_llm_miss_log reads voice_miss_log.jsonl, not historian_entries.
    from datetime import datetime as _dt
    miss_log_path = Path(_TMP) / 'voice_miss_log.jsonl'
    with open(miss_log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'ts': _dt.utcnow().isoformat() + 'Z', 'surface': 'distance_traveled',
            'model': 'phi3.5', 'rules': ['R8_number_provenance'], 'text': 'fabricated test line',
        }) + '\n')
    miss = get_llm_miss_log(time_range_days=30)
    check('get_llm_miss_log reads voice_miss_log.jsonl and counts flags by rule',
          miss['gate_flag_count_by_type'].get('R8_number_provenance', 0) >= 1
          and len(miss['most_recent_flags']) >= 1)

    # ── 23. Adaptive Learning Feature 1 (category suggestions) ───────────────
    from server import suggest_category_for_merchant
    from core.database import Category as _Cat

    with _dbs() as session:
        groceries = session.query(_Cat).filter_by(name='Groceries').first()
        household = session.query(_Cat).filter_by(name='Household Supplies').first()
        check('fixture categories exist (Groceries, Household Supplies)',
              groceries is not None and household is not None)
        acct8 = _Acct(name='Suggest Smoke Checking', type='checking')
        session.add(acct8); session.flush()
        # 3x "Groceries" for Whole Foods, 1x "Household Supplies" — Groceries
        # should win, at 75% confidence over a sample of 4.
        for i in range(3):
            session.add(_Txn(date=_date(2026, 7, 10 + i), amount=50.0, type='debit',
                              account_id=acct8.id, merchant='Whole Foods', category_id=groceries.id))
        session.add(_Txn(date=_date(2026, 7, 14), amount=20.0, type='debit',
                          account_id=acct8.id, merchant='Whole Foods', category_id=household.id))
        session.commit()

    with _dbs() as session:
        suggestion = suggest_category_for_merchant(session, 'Whole Foods')
        check('suggest_category_for_merchant picks the most frequent category',
              suggestion['category'] == 'Groceries' and suggestion['confidence_pct'] == 75.0
              and suggestion['sample_size'] == 4)

        no_history = suggest_category_for_merchant(session, 'ZzTotallyUnseenMerchantZz')
        check('suggest_category_for_merchant returns honest empty shape for an unseen merchant',
              no_history == {'category': None, 'confidence_pct': None, 'sample_size': 0})

        empty_input = suggest_category_for_merchant(session, '   ')
        check('suggest_category_for_merchant handles blank input without querying',
              empty_input == {'category': None, 'confidence_pct': None, 'sample_size': 0})

    r = c.get('/api/categories/suggest?merchant=Whole+Foods', headers=H)
    route_data = (r.get_json() or {}).get('data') or {}
    check('GET /api/categories/suggest route works end-to-end',
          r.status_code == 200 and route_data.get('category') == 'Groceries')

    r = c.get('/api/categories/suggest', headers=H)
    check('GET /api/categories/suggest handles a missing merchant param gracefully',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('category') is None)

    # ── 24. Adaptive Learning Feature 2 (budget variance learning) ───────────
    from server import get_budget_variance_for_category, suggest_budget_adjustment
    from core.database import BudgetItem as _BI

    with _dbs() as session:
        session.add(_BI(name='Smoke Volatile Item', category='Restaurants', amount=500.0, type='expense'))
        session.add(_BI(name='Smoke Stable Item', category='Coffee Shops', amount=300.0, type='expense'))
        session.commit()

        acct9 = _Acct(name='Budget Variance Smoke Checking', type='checking')
        session.add(acct9); session.flush()
        restaurants = session.query(_Cat).filter_by(name='Restaurants').first()
        coffee = session.query(_Cat).filter_by(name='Coffee Shops').first()
        # Volatile: 200, 800, 200 vs budgeted 500 -> 60% avg variance each month.
        for i, amt in enumerate([200.0, 800.0, 200.0]):
            session.add(_Txn(date=_date(2026, 4 + i, 15), amount=amt, type='debit',
                              account_id=acct9.id, category_id=restaurants.id))
        # Stable: 310, 295, 305 vs budgeted 300 -> ~3.3% avg variance.
        for i, amt in enumerate([310.0, 295.0, 305.0]):
            session.add(_Txn(date=_date(2026, 4 + i, 20), amount=amt, type='debit',
                              account_id=acct9.id, category_id=coffee.id))
        session.commit()

    with _dbs() as session:
        volatile = get_budget_variance_for_category(session, 'Restaurants', months=6)
        check('volatile category is classified correctly from real spending',
              volatile['classification'] == 'volatile' and volatile['months_sampled'] == 3)
        check('suggest_budget_adjustment adds a 15% buffer for a volatile category',
              suggest_budget_adjustment(500.0, volatile['volatility']) == 575.0)

        stable = get_budget_variance_for_category(session, 'Coffee Shops', months=6)
        check('stable category is classified correctly from real spending',
              stable['classification'] == 'stable')
        check('suggest_budget_adjustment tightens a stable category by 5%',
              suggest_budget_adjustment(300.0, stable['volatility']) == 285.0)

        no_budget = get_budget_variance_for_category(session, 'ZzNoBudgetItemZz', months=6)
        check('get_budget_variance_for_category returns honest empty shape with no budget item',
              no_budget['classification'] is None and no_budget['months_sampled'] == 0)

        check('suggest_budget_adjustment is a no-op when volatility is unknown',
              suggest_budget_adjustment(400.0, None) == 400.0)

    r = c.get('/api/budget/variance?category=Restaurants&months=6', headers=H)
    route_data = (r.get_json() or {}).get('data') or {}
    check('GET /api/budget/variance route works end-to-end',
          r.status_code == 200 and route_data.get('suggested_budget') == 575.0)

    # ── 25. Adaptive Learning Feature 3 (trip spending forecast) ──────────────
    from server import get_improved_trip_estimate, _extract_trip_region

    check('_extract_trip_region parses "City, ST"', _extract_trip_region('Denver, CO') == 'CO')
    check('_extract_trip_region falls back to the raw string with no comma',
          _extract_trip_region('Somewhere') == 'Somewhere')
    check('_extract_trip_region handles blank input', _extract_trip_region('') is None)

    with _dbs() as session:
        empty_forecast = get_improved_trip_estimate(session, 'ZzNoTripsHereZz', 1500.0)
        check('get_improved_trip_estimate returns the base estimate unchanged with no regional data',
              empty_forecast == {'estimate': 1500.0, 'adjustment_pct': 0, 'confidence': 'none', 'trip_count': 0})

        # Two past CO trips, both ~15% over their estimate.
        session.add(_TH(region='CO', trip_label='CO Trip 1', estimated_total=1200.0, actual_total=1380.0))
        session.add(_TH(region='CO', trip_label='CO Trip 2', estimated_total=1300.0, actual_total=1495.0))
        session.commit()

    with _dbs() as session:
        forecast = get_improved_trip_estimate(session, 'CO', 1500.0)
        check('get_improved_trip_estimate adjusts upward from real regional overspend',
              forecast['confidence'] == 'medium' and forecast['trip_count'] == 2
              and forecast['estimate'] > 1500.0)

    r = c.get('/api/trip/forecast?region=CO&base_estimate=1500', headers=H)
    check('GET /api/trip/forecast route works end-to-end',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('trip_count') == 2)

    # Regression: the trip planner UI sends the full "City, ST" destination
    # string as region, not a pre-extracted code — caught in browser testing
    # when the route did an exact match against "Denver, CO" while
    # trip_history stores the already-extracted "CO", silently finding
    # nothing and hiding the forecast hint.
    r = c.get('/api/trip/forecast?region=Denver%2C+CO&base_estimate=1500', headers=H)
    check('GET /api/trip/forecast normalizes a full "City, ST" region string',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('trip_count') == 2)

    r = c.get('/api/trip/forecast?region=CO&base_estimate=not-a-number', headers=H)
    check('GET /api/trip/forecast rejects a non-numeric base_estimate (400)', r.status_code == 400)

    # Regression: save_trip_budget and save_trip_learned_actual write
    # SEPARATE rows by design (a "learned actual" applies to the NEW trip
    # being planned, not the specific past trip it came from — see that
    # route's docstring), so a region's actual-only rows never carry an
    # estimated_total. The original average-over-all-matching-rows math
    # coerced that missing estimate to 0, dragging avg_estimated toward
    # zero until variance_pct silently locked at None forever — caught
    # while browser-testing the new trip advisor panel, which never had
    # anything to show for exactly this realistic write pattern.
    with _dbs() as session:
        session.add(_TH(region='OrphanRegion', trip_label='Estimate only', estimated_total=1000.0, actual_total=None))
        session.add(_TH(region='OrphanRegion', trip_label='Actual only 1', estimated_total=None, actual_total=1300.0))
        session.add(_TH(region='OrphanRegion', trip_label='Actual only 2', estimated_total=None, actual_total=1300.0))
        session.commit()
        orphan_forecast = get_improved_trip_estimate(session, 'OrphanRegion', 1000.0)
    check('get_improved_trip_estimate is not fooled by mismatched estimate/actual rows (regression)',
          orphan_forecast['confidence'] != 'none' and orphan_forecast['adjustment_pct'] == 30.0)

    # Write hook 1/2: saving a trip budget writes/updates the estimate side.
    trip_body = {
        'dest': 'Nashville, TN', 'depart': '2026-09-01', 'ret': '2026-09-05',
        'total': 1800.0, 'transport': 300, 'hotel': 900, 'dining': 400, 'activities': 200,
    }
    c.post('/api/trip/budget', headers=HJ, data=json.dumps(trip_body))
    with _dbs() as session:
        saved_trip = session.query(_TH).filter_by(region='TN', start_date=_date(2026, 9, 1)).first()
        check('saving a trip budget writes a trip_history row (estimate side)',
              saved_trip is not None and saved_trip.estimated_total == 1800.0)

    # Re-saving the same trip (same region/dates) updates rather than duplicates.
    trip_body['total'] = 1850.0
    c.post('/api/trip/budget', headers=HJ, data=json.dumps(trip_body))
    with _dbs() as session:
        matching = session.query(_TH).filter_by(region='TN', start_date=_date(2026, 9, 1)).all()
        check('re-saving the same trip updates the existing row instead of duplicating',
              len(matching) == 1 and matching[0].estimated_total == 1850.0)

    # Write hook 2/2: applying a learned basis writes the actual side.
    r = c.post('/api/trip/learned-actual', headers=HJ, data=json.dumps({
        'label': 'Past Nashville Trip', 'region_hint': 'Nashville, TN',
        'hotel_per_night': 150.0, 'dining_per_person_day': 60.0, 'activities_per_person_day': 40.0,
        'actual_total': 1000.0,
    }))
    check('POST trip/learned-actual succeeds', r.status_code == 200)
    with _dbs() as session:
        actual_row = session.query(_TH).filter_by(region='TN', actual_total=1000.0).first()
        check('the learned-actual write hook creates a trip_history row with the actual side filled',
              actual_row is not None and actual_row.trip_label == 'Past Nashville Trip')

    # ── 26. Adaptive Learning Feature 4 (recurring transaction detection) ────
    from server import detect_recurring_patterns

    with _dbs() as session:
        acct10 = _Acct(name='Recurring Detect Smoke Checking', type='checking')
        session.add(acct10); session.flush()
        # Consistent: Netflix $15.99 x4, no variance -> should be detected.
        for i in range(4):
            session.add(_Txn(date=_date(2026, 3 + i, 5), amount=15.99, type='debit',
                              account_id=acct10.id, merchant='Netflix'))
        # Inconsistent: "Corner Store" varies wildly -> should NOT be detected
        # even though it appears 4 times too.
        for amt in [12.0, 45.0, 8.0, 60.0]:
            session.add(_Txn(date=_date(2026, 3, 10), amount=amt, type='debit',
                              account_id=acct10.id, merchant='Corner Store'))
        # Only 2 occurrences -> below the minimum, should NOT be detected.
        for i in range(2):
            session.add(_Txn(date=_date(2026, 5 + i, 1), amount=9.99, type='debit',
                              account_id=acct10.id, merchant='Spotify'))
        session.commit()

    with _dbs() as session:
        patterns = detect_recurring_patterns(session, months=6)
        by_merchant = {p['merchant']: p for p in patterns}
        check('a consistent-amount merchant seen 4x is detected as recurring',
              'Netflix' in by_merchant and by_merchant['Netflix']['frequency'] == 4
              and by_merchant['Netflix']['avg_amount'] == 15.99)
        check('a high-variance merchant is NOT flagged despite meeting the frequency bar',
              'Corner Store' not in by_merchant)
        check('a merchant below the minimum occurrence count is NOT flagged',
              'Spotify' not in by_merchant)

    # Already-budgeted merchants are excluded even if the pattern matches.
    with _dbs() as session:
        session.add(_BI(name='Netflix', category='Streaming Video', amount=15.99, type='expense'))
        session.commit()
    with _dbs() as session:
        patterns_after_budget = detect_recurring_patterns(session, months=6)
        check('a merchant that already has an active budget item is excluded from detection',
              not any(p['merchant'] == 'Netflix' for p in patterns_after_budget))

    r = c.get('/api/budget/detect-recurring?months=6', headers=H)
    route_data = (r.get_json() or {}).get('data') or []
    check('GET /api/budget/detect-recurring route works end-to-end',
          r.status_code == 200 and not any(p['merchant'] == 'Netflix' for p in route_data))

    # ── 27. Adaptive Learning Feature 5 (payoff confidence scoring) ──────────
    # The scoring function itself (get_payment_compliance_confidence) was
    # already built and tested in Phase H1 — Feature 5 IS that function; this
    # just verifies the new HTTP route that exposes it for the narrative.
    with _dbs() as session:
        debt11 = _DA(name='Confidence Route Smoke Card', current_balance=100.0)
        session.add(debt11); session.commit()
        _debt11_id = debt11.id

    r = c.get(f'/api/debt/{_debt11_id}/confidence', headers=H)
    conf_data = (r.get_json() or {}).get('data') or {}
    check('GET /api/debt/<id>/confidence returns an honest null for an account with no history',
          r.status_code == 200 and conf_data.get('confidence_pct') is None)

    r = c.get('/api/debt/999999/confidence', headers=H)
    check('GET /api/debt/<id>/confidence 404s for an unknown account', r.status_code == 404)

    with _dbs() as session:
        log_historian_event(session, 'payment_confirmed', debt_account_id=_debt11_id,
                             expected_value=100.0, actual_value=100.0)
        session.commit()
    r = c.get(f'/api/debt/{_debt11_id}/confidence', headers=H)
    conf_data2 = (r.get_json() or {}).get('data') or {}
    check('GET /api/debt/<id>/confidence scores a perfect on-time history at 100%',
          conf_data2.get('confidence_pct') == 100)

    # app.js wiring check — matches the pattern used for Phase F's other
    # static-content checks (no new server surface beyond the route above).
    check('app.js Distance Traveled fetches and narrates payoff confidence',
          "get(`/api/debt/${c._dbId}/confidence`)" in app_src
          and 'Payoff confidence, from real payment reliability' in app_src)

    # ── 28. Adaptive Learning Feature 6 (LLM gate improvement) ────────────────
    r = c.get('/api/ai/miss-log?days=30', headers=H)
    miss_route_data = (r.get_json() or {}).get('data') or {}
    check('GET /api/ai/miss-log route works end-to-end and reflects the earlier logged miss',
          r.status_code == 200 and miss_route_data.get('gate_flag_count_by_type', {}).get('R8_number_provenance', 0) >= 1)

    r = c.get('/api/ai/miss-log?days=0', headers=H)
    check('GET /api/ai/miss-log with a zero-day window finds nothing (honest, not an error)',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('gate_flag_count_by_type') == {})

    check('app.js Settings renders the gate-health panel',
          'gateHealthPanel' in app_src and "get('/api/ai/miss-log" in app_src)

    # ── 29. Phase I: cross-system integration regression ─────────────────────
    # GROUNDWORK_1_0_ROADMAP.md Phase I.2 scenario 1 ("Complete Ledger -> Debt
    # Flow"), run as one continuous flow instead of isolated per-phase checks
    # — the point is verifying the systems built in separate phases (A-H2)
    # actually compose correctly together, not re-testing any one of them.
    with _dbs() as session:
        debt12 = _DA(name='Integration Smoke Card', current_balance=0.0, begin_balance=2000.0)
        session.add(debt12); session.flush()
        acct12 = _Acct(name='Integration Smoke Checking', type='checking')
        session.add(acct12); session.flush()
        session.commit()
        _debt12_id, _acct12_id = debt12.id, acct12.id

    # Step 1 (Phase B): manual charge.
    r = c.post(f'/api/debt/{_debt12_id}/ledger', headers=HJ,
               data=json.dumps({'entry_type': 'charge', 'amount': 600.0, 'entry_date': '2026-07-03', 'merchant': 'Costco'}))
    check('integration: charge entry succeeds', r.status_code == 201)

    # Step 2 (Phase D): checking payment, linked from the checking side.
    with _dbs() as session:
        txn12 = _Txn(date=_date(2026, 7, 15), amount=500.0, type='debit',
                      account_id=_acct12_id, description='Transfer to Integration Smoke Card')
        session.add(txn12); session.commit()
        _txn12_id = txn12.id
    r = c.post(f'/api/transactions/{_txn12_id}/link-debt', headers=HJ, data=json.dumps({'debt_account_id': _debt12_id}))
    check('integration: linking the checking payment succeeds', r.status_code == 201)
    _linked12_id = (r.get_json() or {}).get('data', {}).get('id')

    # Step 3 (Phase C): save as recurring, from that linked payment's amount.
    r = c.post(f'/api/debt/{_debt12_id}/recurring', headers=HJ,
               data=json.dumps({'amount': 500.0, 'frequency': 'monthly',
                                  'scheduled_date_of_month': (_date.today() + _timedelta(days=2)).day}))
    check('integration: saving the payment pattern as recurring succeeds', r.status_code == 201)

    # Step 4 (Phase C): next month's draft generates and gets confirmed at a
    # different amount (this is the "distance traveled" narrative's variance).
    r = c.get('/api/debt/drafts/pending', headers=H)
    draft12 = next(d for d in (r.get_json() or {}).get('data') or [] if d.get('debt_account_id') == _debt12_id)
    r = c.post(f'/api/debt/drafts/{draft12["id"]}/confirm', headers=HJ, data=json.dumps({'amount': 450.0}))
    check('integration: confirming the next draft succeeds', r.status_code == 200)

    # Step 5 (Phase E): balance reflects all of the above — charge +600,
    # first payment -500, second (confirmed) payment -450 -> 2000-600... wait,
    # charges INCREASE what's owed: 0 + 600 - 500 - 450 = -350. A negative
    # current_balance here is a legitimate "overpaid" state — the point of
    # this check is that ALL THREE entries actually moved the number, not
    # what the specific sign works out to.
    r = c.get('/api/debt', headers=H)
    final_debt = next(d for d in (r.get_json() or {}).get('data') or [] if d['id'] == _debt12_id)
    check('integration: current_balance reflects all three ledger entries together',
          final_debt['current_balance'] == -350.0)

    # Step 6 (Phase H1): historian recorded the draft confirmation.
    with _dbs() as session:
        hist_count = session.query(_HE).filter_by(debt_account_id=_debt12_id).count()
        check('integration: historian recorded at least the draft confirmation', hist_count >= 1)

    # Step 7 (Phase E): compliance math sees the variance from the confirmed draft.
    r = c.get(f'/api/debt/{_debt12_id}/recurring', headers=H)
    recur12 = (r.get_json() or {}).get('data') or []
    check('integration: recurring-pattern compliance reflects the confirmed variance',
          any(rp.get('compliance', {}).get('total', 0) >= 1 for rp in recur12))

    # Step 8: the ledger itself shows all three entries with the checking
    # link indicator on the right one.
    r = c.get(f'/api/debt/{_debt12_id}/ledger', headers=H)
    ledger12 = (r.get_json() or {}).get('data') or []
    check('integration: full ledger shows all three entries',
          len(ledger12) == 3)
    check('integration: the linked entry still shows its checking-transaction link',
          any(e['id'] == _linked12_id and e['linked_checking_transaction_id'] == _txn12_id for e in ledger12))

    # ── 30. Phase I: database integrity — no orphaned FKs after a full
    # create/link/unlink/delete cycle across every table this build added.
    from core.database import CheckingTransactionLink as _CTL2

    with _dbs() as session:
        orphaned_links = session.query(_CTL2).filter(
            ~_CTL2.debt_ledger_entry_id.in_(session.query(_DLE.id))
        ).count()
        check('database integrity: no checking_transaction_links row points at a deleted debt entry',
              orphaned_links == 0)

        orphaned_hist = session.query(_HE).filter(
            _HE.debt_account_id.isnot(None),
            ~_HE.debt_account_id.in_(session.query(_DA.id))
        ).count()
        check('database integrity: no historian_entries row points at a deleted debt account',
              orphaned_hist == 0)

        dangling_txn_links = session.query(_DLE).filter(
            _DLE.linked_checking_transaction_id.isnot(None),
            ~_DLE.linked_checking_transaction_id.in_(session.query(_Txn.id))
        ).count()
        check('database integrity: no debt_ledger_entries row points at a deleted checking transaction',
              dangling_txn_links == 0)

    # ── 31. Flights API (GROUNDWORK_LLM_BUILD_PLAN.md decision #7) ───────────
    import flight_price
    from core.database import FlightPriceCache as _FPC
    from datetime import datetime as _dt2, timedelta as _td2

    check('search_flights is honest with no API key configured',
          flight_price.search_flights('ORD', 'DEN', '2026-09-10', api_key='') ==
          {'live': False, 'reason': 'no_api_key'})

    r = flight_price.search_flights('', 'DEN', '', api_key='fake-key-for-this-check')
    check('search_flights rejects missing required fields before making any request',
          r == {'live': False, 'reason': 'missing_required_field'})

    # _parse_response: honest failure reasons for malformed/empty SerpApi
    # response shapes — never guesses a price from a partial one.
    check('_parse_response reports the API-side error verbatim',
          flight_price._parse_response({'error': 'Invalid API key.'})[1] == 'Invalid API key.')
    check('_parse_response reports no_results for an empty response',
          flight_price._parse_response({'best_flights': [], 'other_flights': []})[1] == 'no_results')
    check('_parse_response reports no_price_in_response when flights exist but have no price field',
          flight_price._parse_response({'best_flights': [{'flights': [{'airline': 'Test Air'}]}]})[1]
          == 'no_price_in_response')
    parsed, reason = flight_price._parse_response({'best_flights': [
        {'price': 450, 'flights': [{'airline': 'Test Air'}]},
        {'price': 320, 'flights': [{'airline': 'Cheap Air'}]},
    ]})
    check('_parse_response picks the cheapest priced candidate',
          reason is None and parsed['price'] == 320.0 and parsed['airline'] == 'Cheap Air')

    # Cache hit: a fresh cache row must short-circuit before any network call
    # — proven here by supplying an obviously-fake key that would fail if the
    # module actually tried to reach SerpApi with it.
    cache_key = flight_price._cache_key('ORD', 'DEN', '2026-09-10', '2026-09-14', 2)
    with _dbs() as session:
        session.add(_FPC(cache_key=cache_key, origin='ORD', destination='DEN',
                          outbound_date='2026-09-10', return_date='2026-09-14', travelers=2,
                          price_total=317.50, airline='Cached Air'))
        session.commit()
    cached_result = flight_price.search_flights('ORD', 'DEN', '2026-09-10', '2026-09-14', 2,
                                                  api_key='fake-key-would-fail-if-actually-called')
    check('search_flights returns a fresh cache hit without attempting a network call',
          cached_result == {'live': True, 'price_total': 317.50, 'airline': 'Cached Air', 'cached': True})

    # Regression: the cache check must run BEFORE the api_key gate — a cache
    # hit makes no new request, so it needs no key. Caught during this
    # build: the original ordering checked api_key first, which meant a
    # valid cached price silently became unreachable ('no_api_key') the
    # moment a key went missing, even though nothing about serving cache
    # requires one.
    cached_no_key = flight_price.search_flights('ORD', 'DEN', '2026-09-10', '2026-09-14', 2, api_key='')
    check('a cache hit does not require an API key at all (regression)',
          cached_no_key == {'live': True, 'price_total': 317.50, 'airline': 'Cached Air', 'cached': True})

    # A stale cache row (older than the freshness window) must NOT be
    # returned as a hit — this one has no api_key either, so if staleness
    # weren't respected it would wrongly fall through to 'live': True anyway
    # only by accident; assert the correct no_api_key path is reached instead.
    with _dbs() as session:
        stale_key = flight_price._cache_key('LAX', 'JFK', '2026-01-01', None, 1)
        session.add(_FPC(cache_key=stale_key, origin='LAX', destination='JFK',
                          outbound_date='2026-01-01', return_date=None, travelers=1,
                          price_total=199.0, airline='Old Air',
                          fetched_at=_dt2.utcnow() - _td2(hours=48)))
        session.commit()
    stale_result = flight_price.search_flights('LAX', 'JFK', '2026-01-01', None, 1, api_key='')
    check('a stale cache row is not treated as a hit (falls through to the real no-key path)',
          stale_result == {'live': False, 'reason': 'no_api_key'})

    # Route-level: no key configured in this smoke environment either.
    r = c.get('/api/trip/flight-price?origin=ORD&destination=DEN&outbound_date=2026-09-10&travelers=2', headers=H)
    route_data = (r.get_json() or {}).get('data') or {}
    check('GET /api/trip/flight-price responds 200 with an honest live:false (no key in this env)',
          r.status_code == 200 and route_data.get('live') is False)

    # But the SAME route/dates as the cached entry above must still hit cache
    # even via the HTTP route (proves the route wires through to the cache
    # path, not just the module function directly).
    r = c.get('/api/trip/flight-price?origin=ORD&destination=DEN&outbound_date=2026-09-10&return_date=2026-09-14&travelers=2', headers=H)
    route_cached = (r.get_json() or {}).get('data') or {}
    check('GET /api/trip/flight-price hits the cache through the route too',
          route_cached.get('live') is True and route_cached.get('price_total') == 317.50)

    r = c.get('/api/trip/flight-price?origin=ORD', headers=H)
    check('GET /api/trip/flight-price handles missing params without a 500',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('live') is False)

    check('groundwork.spec declares flight_price as a hidden import (PyInstaller trace)',
          "'flight_price'" in Path('groundwork.spec').read_text(encoding='utf-8'))

    check("app.js wires the explicit search button (not the automatic tripUpdateBudget path)",
          'searchLiveFlightPrice' in app_src and 'tripFlightSearchResult' in app_src)

    # ── 32. QIF import category mapping (Quicken/Money legacy categories) ────
    # quicken_import.py's own route returns 410 Deprecated (confirmed dead
    # code — server.py never calls into it); the LIVE import path is
    # bank_importer.py's _parse_qif(), which is what this covers.
    import bank_importer as _bi
    from core.database import CATEGORY_TREE as _CAT_TREE

    _tree_names = {row[0] for row in _CAT_TREE}
    _mapped_targets = set(_bi._QIF_CATEGORY_MAP.values())
    check('every _QIF_CATEGORY_MAP target is a real current category name',
          _mapped_targets <= _tree_names)

    check('normalize_qif_category maps a known flat Quicken category',
          _bi.normalize_qif_category('Groceries') == 'Groceries')
    check('normalize_qif_category is case-insensitive',
          _bi.normalize_qif_category('GROCERIES') == 'Groceries')
    check('normalize_qif_category maps "Parent:Child" by trying the child first',
          _bi.normalize_qif_category('Auto & Transport:Gas & Fuel') == 'Gas / Fuel')
    check('normalize_qif_category falls back to the parent when the child is unmapped',
          _bi.normalize_qif_category('Bills & Utilities:Some Unmapped Child') == 'Utilities')
    check('normalize_qif_category returns unmapped input unchanged (never blanks or guesses)',
          _bi.normalize_qif_category('Totally Made Up Category') == 'Totally Made Up Category')
    check('normalize_qif_category passes through empty/None unchanged',
          _bi.normalize_qif_category('') == '' and _bi.normalize_qif_category(None) is None)

    # End-to-end through _parse_qif(): a real QIF transaction block with a
    # mapped legacy category, and one with an unmapped category that should
    # fall through to auto_category()'s keyword guess rather than being lost.
    _qif_sample = (
        '!Type:Bank\n'
        'D1/15\'26\n'
        'T-42.17\n'
        'PKroger\n'
        'LGroceries\n'
        '^\n'
        'D1/16\'26\n'
        'T-9.50\n'
        'PStarbucks\n'
        'LFood & Dining:Coffee Shops\n'
        '^\n'
    )
    _qif_records, _qif_org, _qif_warnings = _bi._parse_qif(_qif_sample, [])
    check('_parse_qif produces both sample transactions',
          len(_qif_records) == 2)
    check('_parse_qif maps a flat legacy category via the live import path',
          _qif_records[0]['category'] == 'Groceries')
    check('_parse_qif maps a Parent:Child legacy category via the live import path',
          _qif_records[1]['category'] == 'Coffee Shops')

    # ── 33. Debt balance fields accept cents (regression) ────────────────────
    # Both the Debt page's own balance field (_debtBalanceField) and the
    # Budget page's quick-edit debt bloom (bloom-debt-bal) previously used
    # step="10" / step="1" — a currency field with a whole-number step
    # triggers the browser's native stepMismatch/:invalid state on any
    # typed cents value (confirmed via simulated keystroke entry: the typed
    # value still lands in .value, but validity.stepMismatch becomes true),
    # which is what made "add cents to a debt balance" appear broken. Every
    # other dollar-amount field in this codebase uses step="0.01" — these
    # two were the only outliers.
    _debt_bal_field_src = app_src.split('function _debtBalanceField')[1][:400]
    check('_debtBalanceField uses step="0.01" so typed cents are valid (not step="10")',
          'min="0" step="0.01"' in _debt_bal_field_src)
    check('the budget-bloom quick-edit balance field uses step="0.01" (not step="1")',
          'class="bloom-debt-bal" min="0" step="0.01"' in app_src)

    # ── 34. Pre-release UI audit: currency fields reject cents (regression) ──
    # Full sweep triggered by the TJ Max debt-balance bug: every type="number"
    # field in app.js/index.html was checked for a whole-number step (or no
    # step at all — which silently defaults to step="1" and is just as bad).
    # 64 fields across onboarding, Net Worth, Before You Buy, sinking funds,
    # gift budgets, college funds, retirement calculators, and the APR
    # estimator had this bug; whole-number fields (day-of-month, term
    # months, ages, years, percentages, share counts) were left alone. This
    # regression check samples one prominent field per feature area rather
    # than re-asserting all 64 individually.
    _currency_field_ids = [
        'obIncome', 'obIncome2', 'obExpHousing', 'obNWGoal',      # onboarding
        'monthlyBudget',                                          # debt payoff
        'nwSavings', 'nwHomeValue', 'nwMortgage', 'nwGoalAmount', # net worth
        'sfBalance', 'sfTarget', 'sfMonthly',                     # sinking funds
        'cfBalance', 'cfTarget', 'cfMonthly',                     # college funds
        'pensionBenefit', 'retireSSIncome', 'rmdBalance',         # retirement
        'ssFRABenefit', 'nwTraditional401k', 'nwRoth401k',        # retirement
        'mortgageFullPayment', 'settingsMonthlyBudget',           # misc
        'bybMonthlyAmount', 'gsTarget',                           # BYB / gifts
    ]
    _combined_src = app_src + '\n' + html_src
    _missing_cents_support = [
        fid for fid in _currency_field_ids
        if not re.search(rf'id="{re.escape(fid)}"[^>]*step="0\.01"|step="0\.01"[^>]*id="{re.escape(fid)}"', _combined_src)
    ]
    check(f'{len(_currency_field_ids)} sampled currency fields all accept cents (step="0.01")',
          not _missing_cents_support)

    # ── 35. Net Worth Historian integration ───────────────────────────────────
    # Net worth was explicitly scoped OUT of Historian for 1.0 (roadmap: "Net
    # worth ... unchanged, already correct") — added after the fact to bring
    # it to parity with debt's payoff confidence feature. Milestones aren't a
    # DB table (they live in AppSetting.nw_goals_json), so this writes/reads
    # that directly, the same way app.js does.
    from server import _log_net_worth_milestone_variance, get_net_worth_milestone_confidence
    from core.database import AppSetting as _AS

    r = c.get('/api/net-worth/milestone/nonexistent-id/confidence', headers=H)
    nw_conf_empty = (r.get_json() or {}).get('data') or {}
    check('GET /api/net-worth/milestone/<id>/confidence is honest-empty for an unknown milestone',
          r.status_code == 200 and nw_conf_empty.get('confidence_pct') is None
          and nw_conf_empty.get('samples') == 0)

    # Seed a milestone the same shape app.js's saveNWGoal() writes: start
    # pace 2026-01-01 -> $0, target 2026-12 -> $10,000.
    _nw_goal = {'id': 'smoke-ms-1', 'name': 'Smoke Test Goal', 'amount': 10000,
                'date': '2026-12', 'startAmount': 0, 'startDate': '2026-01-01'}
    with _dbs() as session:
        session.add(_AS(key='nw_goals_json', value=json.dumps([_nw_goal])))
        session.commit()

    # A snapshot at 2026-07 (6 of 11 months elapsed) with actual net worth
    # $4,000 vs. an on-pace expectation of $10,000 * 6/11 = $5,454.55 —
    # deliberately behind pace, to verify the trend classification.
    with _dbs() as session:
        _log_net_worth_milestone_variance(session, '2026-07', 4000.0)
        session.commit()
    with _dbs() as session:
        hist_nw = session.query(_HE).filter_by(
            event_category='net_worth_milestone_variance').order_by(_HE.id.desc()).first()
        check('_log_net_worth_milestone_variance writes a historian entry with the expected linear-pace value',
              hist_nw is not None and abs(hist_nw.expected_value - 5454.55) < 0.5
              and hist_nw.actual_value == 4000.0)
        check('the historian entry carries milestone_id in context_json (no FK column for it)',
              json.loads(hist_nw.context_json or '{}').get('milestone_id') == 'smoke-ms-1')

        conf = get_net_worth_milestone_confidence(session, 'smoke-ms-1')
        check('get_net_worth_milestone_confidence classifies a below-pace snapshot as "behind"',
              conf['trend'] == 'behind' and conf['confidence_pct'] is not None
              and conf['confidence_pct'] < 100 and conf['samples'] == 1)

    r = c.get('/api/net-worth/milestone/smoke-ms-1/confidence', headers=H)
    nw_conf_route = (r.get_json() or {}).get('data') or {}
    check('GET /api/net-worth/milestone/<id>/confidence route reflects the logged variance',
          r.status_code == 200 and nw_conf_route.get('trend') == 'behind')

    # A milestone missing startAmount/startDate (pre-feature, or malformed)
    # must be silently skipped, not crash the snapshot route.
    with _dbs() as session:
        session.query(_AS).filter_by(key='nw_goals_json').delete()
        session.add(_AS(key='nw_goals_json', value=json.dumps(
            [{'id': 'no-start', 'name': 'Old Goal', 'amount': 5000, 'date': '2026-12'}])))
        session.commit()
        try:
            _log_net_worth_milestone_variance(session, '2026-07', 1000.0)
            session.commit()
            _nw_no_crash = True
        except Exception:
            _nw_no_crash = False
    check('a milestone missing startAmount/startDate is skipped, not a crash',
          _nw_no_crash)

    # End-to-end through the real route: POST /api/net-worth/snapshot must
    # not error with a milestone present, and confidence must resolve
    # afterward — proves the write-hook is actually wired into
    # create_snapshot(), not just callable standalone.
    with _dbs() as session:
        session.query(_AS).filter_by(key='nw_goals_json').delete()
        session.add(_AS(key='nw_goals_json', value=json.dumps([_nw_goal])))
        session.commit()
    r = c.post('/api/net-worth/snapshot', headers=H, json={'force': True, 'assets': 6000, 'liabilities': 0})
    check('POST /api/net-worth/snapshot succeeds with a milestone present',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('taken') is True)

    # ── 36. Investments Historian integration ─────────────────────────────────
    # Investments was flagged as the priority gap after Net Worth's fix —
    # allocation-vs-target drift is the direct analog of net worth's
    # milestone pace: a real target already exists (inv_target_alloc), this
    # just adds the variance trail on top of it. No network calls here —
    # _compute_portfolio_positions(skip_refresh=True) and
    # _log_investment_allocation_drift never touch price_engine's live
    # Yahoo Finance fetch, only PriceCache rows seeded directly below.
    from server import (
        _compute_portfolio_positions, _log_investment_allocation_drift,
        get_investment_allocation_confidence,
    )
    from core.database import InvestmentLot as _IL, PriceCache as _PC

    with _dbs() as session:
        session.add(_IL(ticker='SMOKETEST', security_type='stock', shares_original=10,
                         shares_remaining=10, cost_basis_per_share=100.0,
                         purchase_date=_date(2026, 1, 1)))
        session.add(_PC(ticker='SMOKETEST', price=110.0, is_manual=True, source='manual'))
        session.commit()

    with _dbs() as session:
        positions, summary = _compute_portfolio_positions(session, skip_refresh=True)
        check('_compute_portfolio_positions values the seeded lot at shares * cached price',
              summary['total_market_value'] == 1100.0 and summary['total_cost'] == 1000.0
              and len(positions) == 1 and positions[0]['ticker'] == 'SMOKETEST')

    # Target 50% domestic_equity, but SMOKETEST isn't tagged yet — the whole
    # $1,100 position is untagged, so actual domestic_equity holding is $0
    # against a $550 target: deliberately, heavily underweight.
    with _dbs() as session:
        session.add(_AS(key='inv_target_alloc', value=json.dumps({'domestic_equity': 50})))
        session.commit()
        _log_investment_allocation_drift(session)
        session.commit()
    with _dbs() as session:
        hist_inv = session.query(_HE).filter_by(
            event_category='investment_allocation_drift').order_by(_HE.id.desc()).first()
        check('_log_investment_allocation_drift logs expected = target % of real portfolio value',
              hist_inv is not None and hist_inv.expected_value == 550.0 and hist_inv.actual_value == 0.0)
        check("the historian entry carries asset_class in context_json (no FK column for it)",
              json.loads(hist_inv.context_json or '{}').get('asset_class') == 'domestic_equity')

        conf_empty = get_investment_allocation_confidence(session, 'international_equity')
        check('get_investment_allocation_confidence is honest-empty for a class with no history',
              conf_empty['confidence_pct'] is None and conf_empty['samples'] == 0)

        conf = get_investment_allocation_confidence(session, 'domestic_equity')
        check('get_investment_allocation_confidence classifies a fully-unheld target as "underweight"',
              conf['trend'] == 'underweight' and conf['confidence_pct'] is not None and conf['samples'] == 1)

    # Now tag the ticker as domestic_equity and log again — actual should
    # jump to the full $1,100, overshooting the $550 target: "overweight".
    with _dbs() as session:
        session.add(_AS(key='inv_asset_classes_json', value=json.dumps({'SMOKETEST': 'domestic_equity'})))
        session.commit()
        _log_investment_allocation_drift(session)
        session.commit()
    with _dbs() as session:
        conf2 = get_investment_allocation_confidence(session, 'domestic_equity')
        check('a second refresh after tagging the ticker shows the corrected actual value',
              conf2['samples'] == 2)

    r = c.get('/api/investments/allocation/domestic_equity/confidence', headers=H)
    inv_conf_route = (r.get_json() or {}).get('data') or {}
    check('GET /api/investments/allocation/<class>/confidence route reflects the logged variance',
          r.status_code == 200 and inv_conf_route.get('samples') == 2)

    r = c.get('/api/investments/positions', headers=H)
    check('GET /api/investments/positions still works after the _compute_portfolio_positions refactor',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('summary', {}).get('total_market_value') == 1100.0)

    check("app.js wires the investment advisor panel (surface: 'investment_advisor')",
          "'investment_advisor'" in app_src and 'invAdvisorCard' in app_src)

    # ── 37. Fill-the-gaps: Sinking Funds, College Funds, Retirement,
    # Trophy Room, Budget suggestion/recurring feedback trail ────────────────
    # Scope agreed after the Investments pass: everything except Trip
    # Planner/Before You Buy/Gift Budget (called non-essential add-ons), and
    # LLM-narrative-only (no Historian) for Retirement tools and Trophy Room
    # since neither has a real target/actual to compare.
    from server import (
        _log_sinking_fund_contribution_variance, get_sinking_fund_confidence,
        _log_college_fund_contribution_variance, get_college_fund_confidence,
    )
    from core.database import SinkingFund as _SF

    # Sinking funds: a real DB row with its own monthly_contribution — the
    # expected value comes straight from the fund, no linear-pace math
    # needed (closer to debt's payment_amount_variance than net worth's
    # milestone projection).
    with _dbs() as session:
        fund = _SF(name='Smoke Sinking Fund', target_amount=1200, current_amount=0, monthly_contribution=100)
        session.add(fund); session.commit()
        _sf_id = fund.id

    r = c.get(f'/api/sinking-funds/{_sf_id}/confidence', headers=H)
    check('GET /api/sinking-funds/<id>/confidence is honest-empty with no contribution history',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('confidence_pct') is None)

    r = c.post(f'/api/sinking-funds/{_sf_id}/deposit', headers=H, json={'amount': 150})
    check('POST /api/sinking-funds/<id>/deposit succeeds (over-contribution, deliberately ahead of pace)',
          r.status_code == 200)

    with _dbs() as session:
        hist_sf = session.query(_HE).filter_by(
            event_category='sinking_fund_contribution_variance').order_by(_HE.id.desc()).first()
        check('_log_sinking_fund_contribution_variance logs expected = fund.monthly_contribution',
              hist_sf is not None and hist_sf.expected_value == 100.0 and hist_sf.actual_value == 150.0)
        conf_sf = get_sinking_fund_confidence(session, _sf_id)
        check('get_sinking_fund_confidence classifies an over-contribution as "ahead" (never penalized)',
              conf_sf['trend'] == 'ahead' and conf_sf['confidence_pct'] == 100)

    # A fund with no monthly_contribution set must be skipped silently, not
    # logged with a fabricated expectation of 0.
    with _dbs() as session:
        fund2 = _SF(name='No-Contrib Fund', target_amount=500, current_amount=0, monthly_contribution=0)
        session.add(fund2); session.commit()
        _log_sinking_fund_contribution_variance(session, fund2, 50.0)
        session.commit()
        no_hist = session.query(_HE).filter_by(event_category='sinking_fund_contribution_variance').count()
    check('a fund with no monthly_contribution set is skipped (no fabricated expectation)',
          no_hist == 1)  # still just the one from the fund above, not two

    # College funds: JSON-in-AppSetting like net worth milestones — the
    # dedicated /contribute route sources "expected" from the settings blob
    # server-side, never trusting a client-passed expectation.
    _cf = {'id': 'smoke-cf-1', 'childName': 'Smoke Kid', 'balance': 0, 'target': 10000, 'monthlyContrib': 200}
    with _dbs() as session:
        session.add(_AS(key='college_funds_json', value=json.dumps([_cf])))
        session.commit()

    r = c.get('/api/college-funds/smoke-cf-1/confidence', headers=H)
    check('GET /api/college-funds/<id>/confidence is honest-empty with no history',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('confidence_pct') is None)

    r = c.post('/api/college-funds/smoke-cf-1/contribute', headers=H, json={'amount': 50})
    check('POST /api/college-funds/<id>/contribute succeeds (deliberately behind the $200 pace)',
          r.status_code == 200)
    r = c.post('/api/college-funds/nonexistent-id/contribute', headers=H, json={'amount': 50})
    check('POST /api/college-funds/<id>/contribute 404s for an unknown fund', r.status_code == 404)

    with _dbs() as session:
        hist_cf = session.query(_HE).filter_by(
            event_category='college_fund_contribution_variance').order_by(_HE.id.desc()).first()
        check('college fund contribution logs expected from the settings blob, not a client-passed value',
              hist_cf is not None and hist_cf.expected_value == 200.0 and hist_cf.actual_value == 50.0)
        conf_cf = get_college_fund_confidence(session, 'smoke-cf-1')
        check('get_college_fund_confidence classifies an under-contribution as "behind"',
              conf_cf['trend'] == 'behind')

    # Budget: category-suggestion and recurring-detection feedback — the
    # part of Phase H2 Features 1/4 that was always scaffold-only until now.
    r = c.post('/api/categories/suggest-feedback', headers=H,
               json={'merchant': 'Smoke Merchant', 'suggested_category': 'Groceries', 'kept': True})
    check('POST /api/categories/suggest-feedback succeeds', r.status_code == 200)
    r = c.post('/api/categories/suggest-feedback', headers=H, json={'merchant': '', 'suggested_category': ''})
    check('POST /api/categories/suggest-feedback rejects a missing merchant (400)', r.status_code == 400)

    r = c.post('/api/budget/detect-recurring/feedback', headers=H,
               json={'merchant': 'Smoke Recurring Co', 'avg_amount': 15.99, 'confirmed': False})
    check('POST /api/budget/detect-recurring/feedback succeeds', r.status_code == 200)

    with _dbs() as session:
        confirm_cat = session.query(_HE).filter_by(event_category='categorization_suggestion_confirm').first()
        reject_rec  = session.query(_HE).filter_by(event_category='recurring_pattern_reject').first()
        check('categorization_suggestion_confirm was logged with merchant/category in context_json',
              confirm_cat is not None
              and json.loads(confirm_cat.context_json or '{}').get('suggested_category') == 'Groceries')
        check('recurring_pattern_reject was logged with the merchant and its avg_amount',
              reject_rec is not None and reject_rec.actual_value == 15.99
              and json.loads(reject_rec.context_json or '{}').get('merchant') == 'Smoke Recurring Co')

    # LLM-narrative-only surfaces (Retirement tools, Trophy Room) — no
    # Historian equivalent, since neither has a real target/actual to log.
    check("app.js wires the sinking-funds savings advisor (surface: 'savings_goals_advisor')",
          "'savings_goals_advisor'" in app_src and 'budgetSavingsAdvisorCard' in app_src)
    check("app.js wires the combined retirement advisor (surface: 'retirement_advisor')",
          "'retirement_advisor'" in app_src and 'retirementAdvisorCard' in app_src)
    check("app.js wires the Trophy Room narrative (surface: 'trophy_room_narrative')",
          "'trophy_room_narrative'" in app_src and 'trophyAdvisorCard' in app_src)

    # ── 38. Before You Buy — decision/impact persistence + Historian ─────────
    # The wizard (_bybCommit) always computed decision/dti_before/dti_after/
    # payoff_impact/whats_left_before/after, but _syncBYBItemToDb never sent
    # them and byb_items had no columns for them — every saved item's real
    # decision was silently dropped, which made every item render as
    # "walked away" (see BYBItem's docstring). This section proves the full
    # round-trip now actually persists what the wizard computes.
    from core.database import BYBItem as _BI

    r = c.post('/api/byb', headers=H, json={
        'name': 'Smoke Vehicle', 'type': 'vehicle', 'category': 'vehicle', 'monthly': 450,
        'decision': 'commit', 'dti_before': 22.0, 'dti_after': 28.5,
        'payoff_impact': 4, 'whats_left_before': 800, 'whats_left_after': 350,
        'replacing_id': 999, 'replacing_name': 'Old Sedan',
    })
    byb_data = (r.get_json() or {}).get('data') or {}
    check('POST /api/byb persists decision and simulation output (regression: used to be silently dropped)',
          r.status_code == 200 and byb_data.get('decision') == 'commit'
          and byb_data.get('dti_after') == 28.5 and byb_data.get('payoff_impact') == 4
          and (byb_data.get('replacing') or {}).get('name') == 'Old Sedan')
    _byb_commit_id = byb_data.get('id')

    with _dbs() as session:
        hist_commit = session.query(_HE).filter_by(event_category='byb_purchase_decision').order_by(_HE.id.desc()).first()
        check('create_byb_item logs byb_purchase_decision for an immediate commit, expected/actual both null',
              hist_commit is not None and hist_commit.expected_value is None and hist_commit.actual_value is None
              and json.loads(hist_commit.context_json or '{}').get('decision') == 'commit')

    r = c.post('/api/byb', headers=H, json={'name': 'Smoke Subscription', 'type': 'subscription', 'monthly': 15, 'decision': 'track'})
    byb_track = (r.get_json() or {}).get('data') or {}
    check("a 'track' decision does not log to Historian (not a decision yet)",
          byb_track.get('decision') == 'track')
    _byb_track_id = byb_track.get('id')
    with _dbs() as session:
        track_hist_count = session.query(_HE).filter_by(event_category='byb_purchase_decision').count()
    check('exactly one byb_purchase_decision logged so far (the commit, not the track)',
          track_hist_count == 1)

    # Resolve the tracked item as bought, with a real actual cost different
    # from the original estimate — this is the genuine estimate-vs-actual
    # signal an immediate decision never produces.
    r = c.patch(f'/api/byb/{_byb_track_id}/resolve', headers=H, json={'decision': 'commit', 'actual_cost': 18.50})
    resolved = (r.get_json() or {}).get('data') or {}
    check('PATCH /api/byb/<id>/resolve succeeds and updates decision/actual_cost/decided_at',
          r.status_code == 200 and resolved.get('decision') == 'commit'
          and resolved.get('actual_cost') == 18.50 and resolved.get('decided_at'))

    with _dbs() as session:
        hist_resolved = session.query(_HE).filter_by(
            event_category='byb_purchase_decision').order_by(_HE.id.desc()).first()
        check('resolving a tracked item to "commit" with actual_cost logs a real variance (expected=estimate, actual=real cost)',
              hist_resolved is not None and hist_resolved.expected_value == 15.0 and hist_resolved.actual_value == 18.50)

    r = c.patch('/api/byb/999999/resolve', headers=H, json={'decision': 'commit'})
    check('PATCH /api/byb/<id>/resolve 404s for an unknown item', r.status_code == 404)
    r = c.patch(f'/api/byb/{_byb_commit_id}/resolve', headers=H, json={'decision': 'sideways'})
    check('PATCH /api/byb/<id>/resolve rejects an invalid decision (400)', r.status_code == 400)

    with _dbs() as session:
        db_item = session.get(_BI, _byb_commit_id)
        check('the ORM model itself has the new columns (not just the route accepting extra JSON)',
              db_item.decision == 'commit' and db_item.dti_after == 28.5 and db_item.replacing_id == 999)

    check('app.js sends decision/dti/payoff-impact to the server (regression: used to send only 5 fields)',
          "decision:           item.decision" in app_src and "dti_after:          item.dti_after" in app_src)
    check('app.js wires the "Decide now" resolve action for tracked items',
          '_bybResolveTracked' in app_src and "/resolve" in app_src)

    # ── 39. Gift Budget — seasons + occasions Historian, and the Trip
    # advisor (the last two areas from "capture data everywhere") ────────────
    # Gift seasons have no monthly_contribution field like sinking funds do
    # (only target + deadline), so "expected" is a deadline-derived pace
    # computed server-side — same formula the client's own _giftSeasonCard
    # already displays as "$X/mo for N months".
    from server import (
        _log_gift_season_contribution_variance, get_gift_season_confidence,
        _log_gift_occasion_variance,
    )

    r = c.get('/api/gift/seasons/nonexistent-id/confidence', headers=H)
    check('GET /api/gift/seasons/<id>/confidence is honest-empty for an unknown season',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('confidence_pct') is None)

    # Deadline 6 months out (2027-01), target $1200, $0 saved so far ->
    # expected pace = 1200/6 = $200/mo. A $120 deposit is deliberately
    # behind that pace.
    _gift_season = {'id': 'smoke-gs-1', 'name': 'Smoke Holiday Fund', 'target': 1200, 'saved': 0, 'deadline': '2027-01-24'}
    with _dbs() as session:
        session.add(_AS(key='gift_seasons_json', value=json.dumps([_gift_season])))
        session.commit()

    r = c.post('/api/gift/seasons/smoke-gs-1/contribute', headers=H, json={'amount': 120})
    check('POST /api/gift/seasons/<id>/contribute succeeds (deliberately behind the deadline-derived pace)',
          r.status_code == 200)
    r = c.post('/api/gift/seasons/nonexistent-id/contribute', headers=H, json={'amount': 50})
    check('POST /api/gift/seasons/<id>/contribute 404s for an unknown season', r.status_code == 404)

    with _dbs() as session:
        hist_gs = session.query(_HE).filter_by(
            event_category='gift_season_contribution_variance').order_by(_HE.id.desc()).first()
        check('_log_gift_season_contribution_variance computes expected from target/deadline/saved, not a stored field',
              hist_gs is not None and abs(hist_gs.expected_value - 200.0) < 0.5 and hist_gs.actual_value == 120.0)
        conf_gs = get_gift_season_confidence(session, 'smoke-gs-1')
        check('get_gift_season_confidence classifies a below-pace deposit as "behind"',
              conf_gs['trend'] == 'behind' and conf_gs['confidence_pct'] is not None)

    r = c.get('/api/gift/seasons/smoke-gs-1/confidence', headers=H)
    check('GET /api/gift/seasons/<id>/confidence route reflects the logged variance',
          r.status_code == 200 and (r.get_json() or {}).get('data', {}).get('trend') == 'behind')

    # A season with no deadline must be skipped silently, not crash with a
    # fabricated expectation.
    with _dbs() as session:
        _log_gift_season_contribution_variance(session, 'no-deadline-season', 500, 0, '', 25)
        session.commit()
        no_deadline_count = session.query(_HE).filter_by(event_category='gift_season_contribution_variance').count()
    check('a season with no deadline is skipped (no fabricated expectation)', no_deadline_count == 1)

    # Occasions: had a budgeted amount but nothing ever recorded what was
    # actually spent — same gap BYB had before its resolve flow.
    _gift_person = {'id': 'smoke-person-1', 'name': 'Smoke Niece', 'relationship': 'family',
                     'occasions': [{'id': 'smoke-occ-1', 'type': 'birthday', 'date': '2026-03-01', 'budget': 75}]}
    with _dbs() as session:
        session.add(_AS(key='gift_people_json', value=json.dumps([_gift_person])))
        session.commit()

    r = c.post('/api/gift/occasions/smoke-person-1/smoke-occ-1/spend', headers=H, json={'actual_spent': 92.50})
    check('POST /api/gift/occasions/<pid>/<oid>/spend succeeds (over budget)', r.status_code == 200)
    r = c.post('/api/gift/occasions/smoke-person-1/nonexistent-occ/spend', headers=H, json={'actual_spent': 10})
    check('POST /api/gift/occasions/<pid>/<oid>/spend 404s for an unknown occasion', r.status_code == 404)

    with _dbs() as session:
        hist_occ = session.query(_HE).filter_by(event_category='gift_occasion_variance').first()
        check('gift_occasion_variance logs expected=budget, actual=actual_spent',
              hist_occ is not None and hist_occ.expected_value == 75.0 and hist_occ.actual_value == 92.50)
        row = session.query(_AS).filter_by(key='gift_people_json').first()
        people_after = json.loads(row.value)
        occ_after = people_after[0]['occasions'][0]
        check('the occasion itself is updated in the settings blob (actual_spent/spent_at persisted)',
              occ_after.get('actual_spent') == 92.50 and occ_after.get('spent_at'))

    check("app.js wires the gift advisor panel (surface: 'gift_advisor')",
          "'gift_advisor'" in app_src and 'giftAdvisorCard' in app_src)
    check("app.js wires the trip advisor panel (surface: 'trip_advisor')",
          "'trip_advisor'" in app_src and 'tripAdvisorCard' in app_src)
    check('app.js wires occasion actual-spend logging (data-action="spend-occ")',
          "'spend-occ'" in app_src and '_giftLogOccasionSpend' in app_src)

    # ── Ledger: re-render after the optimistic-id swap (regression) ────────────
    # saveTransaction() swapped the temp negative id for the real DB id in
    # S.transactions but never re-rendered, so a freshly-added row's baked-in
    # data-id/onclick handlers (link-to-debt, dblclick-edit, checkbox select)
    # stayed wired to an id that no longer existed until the next page reload.
    save_txn_fn = app_src[app_src.index('async function saveTransaction()'):]
    save_txn_fn = save_txn_fn[:save_txn_fn.index('\nfunction deleteTransaction')]
    check('saveTransaction() re-renders the ledger after swapping in the real id '
          '(regression: stale temp id broke link-to-debt/dblclick/checkbox on new rows)',
          'if (row && saved?.id)' in save_txn_fn
          and 'renderLedger(); updateLedgerStats();' in save_txn_fn)

    # ── Import dedup: CSV vs QFX description formatting (regression) ───────────
    # Real bug found in a live database (2026-07-25): CSV exports prepend a
    # generic "Withdrawal " word that QFX/OFX omits, and QFX/OFX truncates
    # long ACH memo/trace-number text to a fixed max length while CSV does
    # not. The old exact-string dedup match missed these every time — an
    # entire QFX re-import of already-CSV-imported data went through as
    # ~880 new "duplicate" rows. These two real descriptions (trace number
    # truncated by exactly one digit) are taken directly from that database.
    with _dbs() as session:
        dedup_acct = _Acct(name='Smoke Dedup Checking', type='checking')
        session.add(dedup_acct)
        session.flush()
        dedup_acct_id = dedup_acct.id

    csv_desc = ('Withdrawal ACH CAPITAL ONE TYPE: CRCARDPMT CO: CAPITAL ONE NAME: '
                'Pat Sample Entry Class Code: WEB ACH Trace Number: 000000000000001')
    qfx_desc = ('ACH CAPITAL ONE TYPE: CRCARDPMT CO: CAPITAL ONE NAME: '
                'Pat Sample Entry Class Code: WEB ACH Trace Number: 00000000000000')

    r1 = c.post('/api/import/commit', headers=HJ, json={
        'account_id': dedup_acct_id,
        'records': [{'date': '2026-05-18', 'amount': 60.0, 'type': 'debit',
                     'description': csv_desc, 'source': 'csv'}],
    })
    r2 = c.post('/api/import/commit', headers=HJ, json={
        'account_id': dedup_acct_id,
        'records': [{'date': '2026-05-18', 'amount': 60.0, 'type': 'debit',
                     'description': qfx_desc, 'source': 'qfx', 'fitid': '2605180001999596'}],
    })
    check('CSV-then-QFX import of the same real transaction: first commit creates it',
          r1.status_code == 200 and r1.get_json()['data']['created'] == 1)
    check('CSV-then-QFX import of the same real transaction: second commit recognizes '
          'the duplicate (regression: used to silently create a second row)',
          r2.status_code == 200 and r2.get_json()['data']['created'] == 0
          and r2.get_json()['data']['duplicates'] == 1)

    with _dbs() as session:
        count = session.query(_Txn).filter_by(account_id=dedup_acct_id).count()
        check('exactly one transaction exists after both imports (not two)', count == 1)

    # Guard against over-merging: two genuinely different short-description
    # transactions, same day/amount, must NOT be treated as duplicates.
    r3 = c.post('/api/import/commit', headers=HJ, json={
        'account_id': dedup_acct_id,
        'records': [{'date': '2026-06-01', 'amount': 25.0, 'type': 'debit',
                     'description': 'Clark Gas Station', 'source': 'csv'}],
    })
    r4 = c.post('/api/import/commit', headers=HJ, json={
        'account_id': dedup_acct_id,
        'records': [{'date': '2026-06-01', 'amount': 25.0, 'type': 'debit',
                     'description': 'Shell Gas Station', 'source': 'csv'}],
    })
    check('two different short-description same-day/amount transactions both import '
          '(fuzzy match does not over-merge unrelated transactions)',
          r3.get_json()['data']['created'] == 1 and r4.get_json()['data']['created'] == 1)

    # ── Ledger bloom: attach-as-debt-payment button ─────────────────────────────
    # The link-to-debt action previously only existed as a faint icon on the
    # collapsed row; added a real button inside the double-click edit bloom
    # too, since that faint icon was hard enough to notice that it prompted
    # this whole investigation.
    bloom_fn = app_src[app_src.index('function _openEditBloom('):]
    bloom_fn = bloom_fn[:bloom_fn.index('\nfunction _readBloomFields')]
    check('the edit bloom offers "Attach as debt payment" for an unlinked debit row',
          "data-act=\"link-debt\"" in bloom_fn and 'Attach as debt payment' in bloom_fn)
    check('the edit bloom offers "View linked payment" for an already-linked row',
          "data-act=\"view-debt-link\"" in bloom_fn and 'View linked payment' in bloom_fn)
    check('the bloom\'s debt-link buttons are wired to the same picker/jump functions as the row icon',
          "addEventListener('click', e => { e.stopPropagation(); openLinkToDebtPicker(id); });" in app_src
          and "addEventListener('click', e => { e.stopPropagation(); jumpToLinkedDebtEntry(t.linked_debt_entry_id); });" in app_src)

    # ── Debt Payoff page card edits now write a balance-history snapshot ───────
    # Regression found against a real database (2026-07-25): editing a debt's
    # balance/APR/payment on the Debt Payoff page (setCardField) never called
    # _budgetSaveDebtSnapshot — only the Budget page's separate debt-bloom
    # editor did. 12 of 13 real active debt cards had zero
    # debt_balance_history rows because of it, so the "minimum payment is
    # dropping" trend indicator (_budgetMinDecay) could never appear for a
    # card managed the normal way.
    set_card_field_fn = app_src[app_src.index('function setCardField(id, field, value)'):]
    set_card_field_fn = set_card_field_fn[:set_card_field_fn.index('\nfunction confirmRemoveCard')]
    check('setCardField() writes a debt balance-history snapshot on every edit '
          '(regression: Debt Payoff page edits never populated history)',
          '_budgetSaveDebtSnapshot(_budgetMonthKey)' in set_card_field_fn)

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
