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
