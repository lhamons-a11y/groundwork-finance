"""
Groundwork — Flask API Server
==============================
Clean REST API. All data access through the database layer.
No business logic in routes — just request/response handling.
"""

import os
import re
import secrets
import uuid as _uuid
import sys
import json
import logging
import threading
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from functools import wraps
from typing import Any

from flask import copy_current_request_context, Flask, jsonify, request, send_from_directory, send_file, Response, stream_with_context

# Session ID — changes on every server start so client can detect restarts
_GW_SESSION_ID = str(_uuid.uuid4())[:8]
GW_VERSION     = '20261008-d25'  # must match app.js GW_VERSION constant

# ── Security: session token ────────────────────────────────────────────────────
# Generated fresh on every startup. Lives in RAM only — never written to disk.
# Injected into index.html at serve time so the JS client can include it in
# every API request header. Any request missing the token is rejected with 403.
# This means even if another process on the same machine finds port 8765, it
# cannot read or write Groundwork data without the token.
_GW_TOKEN = secrets.token_hex(32)

# The only names a request may address this server by. It binds 127.0.0.1 and
# nothing else, so any other Host means a name that was made to resolve here -
# a DNS-rebinding page. Enforced by _check_request_host in create_app.
_LOCAL_HOSTNAMES = ('127.0.0.1', 'localhost')


def _request_host_refusal(environ, path):
    """Why this request must be refused, or None if it may proceed.

    Module-level, and looked up by the before_request at call time, so the
    smoke section (s125) can break it and prove the break is caught.
    """
    port = str(environ.get('SERVER_PORT', ''))
    host = environ.get('HTTP_HOST', '')
    name, sep, host_port = host.rpartition(':')
    if not sep:
        name, host_port = host, '80'
    if name not in _LOCAL_HOSTNAMES or host_port != port:
        return 'Unauthorized host'

    origin = environ.get('HTTP_ORIGIN')
    if origin is not None and path.startswith('/api/'):
        allowed = {f'http://{n}:{port}' for n in _LOCAL_HOSTNAMES}
        if port == '80':
            allowed |= {f'http://{n}' for n in _LOCAL_HOSTNAMES}
        if origin not in allowed:
            return 'Unauthorized origin'
    return None

from sqlalchemy import func, desc, text

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import ( db_session, DATA_DIR, TripBooking,
    Account, Category, Transaction, BudgetItem,
    DebtAccount, BudgetPlan, BudgetMonth, Achievement, BillReading, AiLog,
    AppSetting, BYBItem, NetWorthSnapshot,
    InvestmentTransaction, InvestmentLot, PriceCache,
    DebtBalanceHistory, PdfExtractCache,
    DebtLedgerEntry, RecurringDebtPayment, CheckingTransactionLink,
    HistorianEntry, TripHistory, WillingnessDeclaration,
)
from core.consequence import simulate_payoff
from core.solution import MIN_MONTHS_OBSERVED
from migrate import run_migration_if_needed


# ── App setup ─────────────────────────────────────────────────────────────────

def create_app(static_folder: str = None) -> Flask:
    """
    Application factory. Separates app creation from startup
    so tests can create isolated instances.
    """
    if static_folder is None:
        static_folder = str(Path(__file__).parent / 'static')

    # static_folder=None: disable Flask's built-in static route. It was
    # registered before serve_frontend and intercepted /index.html, serving
    # it raw WITHOUT token injection → every API call 403'd. All static
    # files are served manually by serve_frontend below.
    app = Flask(__name__, static_folder=None)

    # ── File logging (Phase 1) ────────────────────────────────────────────────
    # Errors used to vanish: pywebview has no visible console, so anything
    # printed to stderr was lost. Everything now also lands in a rotating log
    # in the data dir, and /api/debug/log-tail feeds it into beta bug reports.
    from logging.handlers import RotatingFileHandler
    from core.database import DATA_DIR
    log_path = DATA_DIR / 'groundwork.log'
    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        fh = RotatingFileHandler(log_path, maxBytes=512_000, backupCount=2,
                                 encoding='utf-8')
        fh.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s: %(message)s'))
        fh.setLevel(logging.INFO)
        root.addHandler(fh)
        if root.level > logging.INFO:
            root.setLevel(logging.INFO)
    # Item 45 H6 P2: every log record passes the health scrubber, on every handler (HEALTH_PRIVACY_H6.md)
    from core import health_boundary
    health_boundary.install_log_filter()
    try:
        with db_session() as _hs:
            health_boundary.refresh(_hs)
    except Exception:
        pass               # a database not migrated yet: refreshed on the first import or AI call
    logging.getLogger('groundwork').info('Groundwork %s starting', GW_VERSION)

    @app.errorhandler(Exception)
    def _log_unhandled(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e  # 404s etc. keep their normal handling
        logging.getLogger('groundwork').exception(
            'Unhandled error on %s %s', request.method, request.path)
        return err('Internal error (logged)', 500)

    @app.route('/api/debug/log-tail')
    def debug_log_tail():
        """Last 60 log lines — appended to ⚑ beta bug reports."""
        try:
            lines = log_path.read_text(encoding='utf-8',
                                       errors='replace').splitlines()[-60:]
        except OSError:
            lines = []
        return ok({'log': lines, 'path': str(log_path)})

    # ── Update channel (Phase 2) ──────────────────────────────────────────────
    # Fetches a static version.json from the website, server-side (the webview
    # never makes external requests — no CORS, no IP exposure beyond one GET
    # of a static file, no telemetry sent). Successes cache 6h; failures 30min
    # so recovery after an outage is quick. Version strings YYYYMMDD-dNN
    # compare correctly as plain strings (day number is zero-padded).
    _update_cache = {'ts': 0.0, 'data': None}
    UPDATE_MANIFEST_URL = 'https://groundworkfinance.app/version.json'
    OFFICIAL_DOWNLOAD_PREFIX = 'https://groundworkfinance.app/'

    @app.route('/api/update-check')
    def update_check():
        import time as _t
        import urllib.request
        now = _t.time()
        ttl = 6 * 3600 if (_update_cache['data'] or {}).get('latest') else 1800
        if _update_cache['data'] is not None and now - _update_cache['ts'] < ttl:
            return ok(_update_cache['data'])
        try:
            from core import egress                # item 8: the one door out
            info = json.loads(egress.get(UPDATE_MANIFEST_URL, headers={'User-Agent': 'Groundwork'}, timeout=4,
                                         limit=65536).decode('utf-8'))
            latest = str(info.get('latest', '')).strip()
            url    = str(info.get('url', '')).strip()
            # Never hand the client a download link pointing anywhere but the
            # official site, no matter what the manifest says.
            if not url.startswith(OFFICIAL_DOWNLOAD_PREFIX):
                url = ''
            data = {
                'update_available': bool(latest) and latest > GW_VERSION and bool(url),
                'current': GW_VERSION,
                'latest':  latest or None,
                'url':     url,
                'notes':   str(info.get('notes', ''))[:300],
            }
        except Exception as e:
            logging.getLogger('groundwork').info('update check unavailable: %s', e)
            data = {'update_available': False, 'current': GW_VERSION,
                    'latest': None, 'url': '', 'notes': '', 'offline': True}
        _update_cache['ts']   = now
        _update_cache['data'] = data
        return ok(data)


    # Initialize database — runs schema migrations (new columns on an
    # existing DB) in addition to creating any missing tables. Previously
    # this called bare init_db(), which only creates tables that don't
    # exist yet and silently never alters a table that's already on disk.
    # Item 82 R3 (L3b): a dated copy first, whenever the database is about to be migrated.
    _pre = _backup_before_migration()
    run_migration_if_needed()
    # ... and the migrated database backed up as well (Rob 2026-10-22): the person has a backup of what they now have,
    # and it counts as their latest for the backup reminder
    if _pre and not _pre.get('error'):
        _backup_after_migration(_pre)

    # Register all blueprints
    app.register_blueprint(transactions_bp,  url_prefix='/api/transactions')
    app.register_blueprint(accounts_bp,      url_prefix='/api/accounts')
    app.register_blueprint(categories_bp,    url_prefix='/api/categories')
    app.register_blueprint(investments_bp,   url_prefix='/api/investments')
    app.register_blueprint(networth_bp,      url_prefix='/api/net-worth')
    app.register_blueprint(byb_bp,           url_prefix='/api/byb')
    app.register_blueprint(trip_bp,          url_prefix='/api/trip')
    app.register_blueprint(utility_bp,       url_prefix='/api/utility')
    app.register_blueprint(budget_bp,        url_prefix='/api/budget')
    app.register_blueprint(debt_bp,          url_prefix='/api/debt')
    app.register_blueprint(achievements_bp,  url_prefix='/api/achievements')
    app.register_blueprint(settings_bp,      url_prefix='/api/settings')
    app.register_blueprint(ai_bp,            url_prefix='/api/ai')
    app.register_blueprint(sample_bp,        url_prefix='/api/sample')
    app.register_blueprint(backup_bp,        url_prefix='/api/backup')
    app.register_blueprint(import_bp,        url_prefix='/api/import')
    app.register_blueprint(bank_import_bp,   url_prefix='/api/import')
    app.register_blueprint(auto_import_bp,   url_prefix='/api/auto-import')
    app.register_blueprint(sinking_funds_bp,  url_prefix='/api/sinking-funds')
    app.register_blueprint(proactive_bp,     url_prefix='/api/proactive')
    app.register_blueprint(trophies_bp,      url_prefix='/api/trophies')
    app.register_blueprint(college_funds_bp,  url_prefix='/api/college-funds')
    app.register_blueprint(gifts_bp,          url_prefix='/api/gifts')
    app.register_blueprint(futures_bp,        url_prefix='/api/futures')
    app.register_blueprint(trips_bp,          url_prefix='/api/trips')
    app.register_blueprint(calendar_bp,       url_prefix='/api/calendar')
    app.register_blueprint(tidy_bp,           url_prefix='/api/tidy')
    app.register_blueprint(price_changes_bp,  url_prefix='/api/price-changes')
    app.register_blueprint(yearly_steps_bp,   url_prefix='/api/yearly-steps')
    app.register_blueprint(two_accounts_bp,   url_prefix='/api/two-accounts')   # item 107
    app.register_blueprint(first_import_bp,   url_prefix='/api/first-import')
    app.register_blueprint(year_end_bp,       url_prefix='/api/year-end')
    app.register_blueprint(historian_bp,      url_prefix='/api/historian')
    app.register_blueprint(willingness_bp,    url_prefix='/api/willingness')
    app.register_blueprint(income_bp,         url_prefix='/api/income-change')
    app.register_blueprint(evidence_bp,       url_prefix='/api/evidence')
    app.register_blueprint(why_bp,            url_prefix='/api/why')
    app.register_blueprint(reimburse_bp,      url_prefix='/api/reimburse')
    app.register_blueprint(medical_bp,        url_prefix='/api/medical-bills')   # item 94
    app.register_blueprint(help_bp,           url_prefix='/api/help')
    app.register_blueprint(review_bp,         url_prefix='/api/reports/review')
    app.register_blueprint(checkin_bp,        url_prefix='/api/checkin')
    app.register_blueprint(usage_bp,          url_prefix='/api/usage')
    app.register_blueprint(dashboard_bp,      url_prefix='/api/dashboard')

    # System routes
    @app.route('/api/ping')
    def ping():
        try:
            from version import VERSION
        except ImportError:
            VERSION = '1.0.0.0'
        return jsonify({'status': 'ok', 'version': VERSION,
                        'timestamp': datetime.now().isoformat()})

    @app.route('/api/save', methods=['GET', 'POST'])
    def save_snapshot():
        """
        v1 compatibility shim — persists the full app state snapshot from app.js.
        POST: accepts JSON body (buildSnapshot output), stores in app_settings.
        GET:  returns the stored snapshot.
        """
        if request.method == 'POST':
            snapshot = request.get_json(silent=True) or {}
            with db_session() as session:
                setting = _get_setting(session, 'app_snapshot')
                payload = json.dumps(snapshot)
                if setting:
                    setting.value      = payload
                    setting.updated_at = datetime.now()
                else:
                    session.add(AppSetting(key='app_snapshot', value=payload))
                session.commit()
            return jsonify({'ok': True, 'saved': True})
        else:
            with db_session() as session:
                setting = _get_setting(session, 'app_snapshot')
                if setting:
                    try:
                        return jsonify(json.loads(setting.value))
                    except (ValueError, TypeError):
                        pass
            return jsonify(None)

    @app.route('/api/load', methods=['GET'])
    def load_snapshot():
        """v1 compatibility shim — returns the stored app snapshot."""
        with db_session() as session:
            setting = _get_setting(session, 'app_snapshot')
            if setting:
                try:
                    return jsonify(json.loads(setting.value))
                except (ValueError, TypeError):
                    pass
        return jsonify(None)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Serve the frontend SPA and static assets.

        For index.html we inject the session token as a JS constant so the
        client can authenticate every API request. The token is generated fresh
        on each server start and never written to disk.
        """
        # index.html must NEVER be served raw — it needs the session token
        # injected. Route it (and '') to the injection branch below.
        if path in ('index.html', 'index'):
            path = ''
        # Check static folder first
        static_path = Path(static_folder) / path
        if path and static_path.exists():
            response = send_from_directory(static_folder, path)
        # Check assets folder (images, icons)
        elif path and (Path(static_folder).parent / path).exists():
            response = send_from_directory(str(Path(static_folder).parent), path)
        else:
            # Serve index.html with the token injected
            index_path = Path(static_folder) / 'index.html'
            html = index_path.read_text(encoding='utf-8')
            # Inject token as the very first script so it's available before
            # any other JS runs. Replace a known placeholder or prepend to <head>.
            token_script = f'<script>window.GW_SESSION_TOKEN="{_GW_TOKEN}";</script>'
            if '<head>' in html:
                html = html.replace('<head>', f'<head>\n    {token_script}', 1)
            # The teaching-layer seam (GW 2.0). The loader tag is emitted only
            # when the file is actually in the build: groundwork*.spec strips
            # static/js/teaching/ for GW_PRODUCT=lts, so an LTS build has
            # nothing here to find and index.html needs no product-specific
            # markup - which is what keeps the two lines' index.html identical
            # and their forward-merges clean. Loaded after app.js on purpose:
            # the dependency runs one way, teaching -> app, never back.
            teaching_dir = Path(static_folder) / 'js' / 'teaching'
            teaching_entry = teaching_dir / 'index.js'
            if teaching_entry.exists() and '</body>' in html:
                # Every module in the directory, entry point first. The seam
                # says adding a module is adding a file rather than editing the
                # entry point — and that was true of the registry inside
                # index.js while being false of the page, which only ever loaded
                # index.js. A module dropped in this directory was never
                # fetched, so the only way to ship teaching front-end code was
                # to write it into app.js. Which is what happened.
                modules = sorted(f.name for f in teaching_dir.glob('*.js')
                                 if f.name != 'index.js')
                tags = ''.join(
                    '    <script src="/js/teaching/%s?v=%s"></script>\n' % (name, GW_VERSION)
                    for name in ['index.js'] + modules)
                html = html.replace('</body>', tags + '</body>', 1)
            from flask import Response
            response = Response(html, mimetype='text/html')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma']        = 'no-cache'
        return response

    @app.before_request
    def _check_request_host():
        """Refuse any request not addressed to this server by its loopback name.

        The token check below stops a process that does not have the token. It
        cannot stop a web page that gets it, and `/` hands the token to any
        request that asks. A DNS-rebinding page does ask: its hostname is made
        to resolve to 127.0.0.1, so it is same-origin with this server, reads
        the token out of index.html, and has every /api/* route. What gives it
        away is the Host header - the browser always sends the page's own
        hostname, and ours is never anyone else's. (BANK_BROWSER.md F12.)

        So: the Host must name 127.0.0.1 or localhost, on the port this request
        actually arrived on - 8765 in the app, 8766 under dev_server.py, the
        implicit 80 of Flask's test client. And an /api/* request that carries
        an Origin must come from that same server.

        Registered before _check_session_token on purpose: it has to run for
        `/` and /api/health, which the token check exempts.
        """
        refusal = _request_host_refusal(request.environ, request.path)
        if refusal:
            return jsonify({'error': refusal, 'code': 403}), 403
        return None  # allow through

    @app.before_request
    def _check_session_token():
        """Reject any /api/* request that lacks our session token.

        Exemptions:
          - /api/health  — used by the heartbeat before token may be loaded
          - Static assets — JS, CSS, images, index.html itself
          - /api/ping    — legacy liveness check

        This is our primary defence against other processes on the same machine
        reading or modifying Groundwork data by hitting localhost:8765 directly.
        """
        path = request.path

        # Only protect API endpoints
        if not path.startswith('/api/'):
            return None

        # Exempt lightweight system endpoints that run before or outside auth
        exempt = {'/api/health', '/api/ping'}
        if path in exempt:
            return None

        token = request.headers.get('X-GW-Token', '')
        if not secrets.compare_digest(token, _GW_TOKEN):
            return jsonify({'error': 'Unauthorized', 'code': 403}), 403

        return None  # allow through

    # Item 90 (RESERVE_AWARE_DATES.md D1-D3): the household's health reserve plan, for every payoff date this request
    # computes. Lazy - read the first time the engine asks, once per request - so a request that dates nothing pays
    # nothing; reset when the request ends.
    @app.before_request
    def _reserve_plan_for_request():
        if not request.path.startswith('/api/'):
            return None
        from flask import g as _flask_g
        from core.consequence import RESERVE_PLAN
        from core import health_reserve
        memo = {}

        def plan():
            if 'p' not in memo:
                try:
                    with db_session() as _s:
                        memo['p'] = health_reserve.request_plan(_s, _resolve_bank_anchor)
                except Exception:
                    memo['p'] = None          # a database without the tables: the plan as today
            return memo['p']
        _flask_g._reserve_tok = RESERVE_PLAN.set(plan)
        return None

    @app.teardown_request
    def _reserve_plan_done(_exc):
        from flask import g as _flask_g
        from core.consequence import RESERVE_PLAN
        tok = _flask_g.pop('_reserve_tok', None)     # once: a streamed response can tear down twice (s170)
        if tok is not None:
            try:
                RESERVE_PLAN.reset(tok)
            except (ValueError, RuntimeError):         # a different context, or the token already used
                RESERVE_PLAN.set(None)

    @app.route('/api/health')
    def health_check():
        """Lightweight health check — used by client heartbeat to detect
        server restarts and version mismatches."""
        import platform as _platform
        try:
            with db_session() as session:
                result = session.execute(text('PRAGMA integrity_check')).fetchone()
                db_ok  = result and result[0] == 'ok'
        except Exception:
            db_ok = False
        return jsonify({
            'ok':         True,
            'version':    GW_VERSION,
            'session_id': _GW_SESSION_ID,
            'db_ok':      db_ok,
            'platform':   _platform.system(),   # Windows / Darwin / Linux
            'py_version': _platform.python_version(),
        })

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def server_error(e):
        import traceback
        tb = traceback.format_exc()
        logging.exception('Internal error')
        return jsonify({'error': 'Internal server error', 'detail': str(e), 'trace': tb}), 500

    @app.route('/api/debug/bootstrap')
    def debug_bootstrap():
        """Diagnostic — shows exact bootstrap error with full traceback."""
        import traceback
        try:
            from core.database import db_session, DebtAccount
            with db_session() as session:
                debts = session.query(DebtAccount).filter_by(is_active=True).all()
                results = []
                for d in debts:
                    try:
                        results.append(serialize_debt_account(d, session))
                    except Exception as e:
                        results.append({
                            'id': d.id,
                            'name': d.name,
                            'ERROR': str(e),
                            'traceback': traceback.format_exc()
                        })
                return {'status': 'ok', 'debt_count': len(debts), 'results': results}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500
        import traceback
        try:
            from core.database import BudgetItem, DebtAccount, Category, Transaction, AppSetting, Account, DB_PATH
            with db_session() as session:
                step = 'settings'
                settings = {s.key: s.value for s in session.query(AppSetting).all()}
                step = 'budget_items'
                items = session.query(BudgetItem).filter_by(is_active=True)\
                               .order_by(BudgetItem.type, BudgetItem.sort_order).all()
                step = 'debts'
                debts = session.query(DebtAccount).filter_by(is_active=True).all()
                step = 'categories'
                cats = session.query(Category).all()
                step = 'transactions_count'
                count = session.query(Transaction).count()
                step = 'accounts'
                accts = session.query(Account).all()
                return jsonify({'ok': True, 'steps_completed': step,
                                'budget_items': len(items), 'debts': len(debts),
                                'categories': len(cats), 'transactions': count,
                                'accounts': len(accts),
                                'db_path': str(DB_PATH),
                                'account_names': [a.name for a in accts]})
        except Exception as e:
            return jsonify({'ok': False, 'failed_at': step,
                            'error': str(e), 'trace': traceback.format_exc()}), 200

    return app


# ── Helpers ───────────────────────────────────────────────────────────────────

from flask import Blueprint

def ok(data: Any = None, status: int = 200, **kwargs) -> tuple:
    resp = {'ok': True}
    if data is not None:
        resp['data'] = data
    resp.update(kwargs)
    return jsonify(resp), status


def err(msg: str, status: int = 400) -> tuple:
    return jsonify({'ok': False, 'error': msg}), status


def _get_setting(session, key: str):
    """
    Look up an AppSetting by its `key` column.

    AppSetting's primary key is `id` (auto-increment integer), not `key`,
    so _get_setting(session, key_string) ALWAYS returns None — it does
    a primary-key lookup, not a key-column lookup. Use this everywhere
    instead.
    """
    return session.query(AppSetting).filter_by(key=key).first()


def require_json(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.is_json:
            return err('Content-Type must be application/json')
        return f(*args, **kwargs)
    return decorated


def serialize_transaction(t: Transaction, linked_debt_entry_id=None) -> dict:
    # BUG FIX (July 6): `date` was calling .isoformat() with no null guard,
    # unlike posted_date right below it which correctly handles None. A
    # single transaction with a null date would throw and crash the entire
    # export for every transaction, not just the bad one. Confirmed
    # plausible in the field: export was failing with a generic "Internal
    # error (logged)" on an account with 959 transactions — one bad row is
    # enough. Fixed to match the same safe pattern already used elsewhere
    # in this same function.
    return {
        'id':          t.id,
        'account_id':  t.account_id,
        'account':     t.account.name if t.account else '',
        'category_id': t.category_id,
        'category':    t.category.name if t.category else 'Other',
        'date':        t.date.isoformat() if t.date else None,
        'description': t.description,
        'amount':      round(t.amount, 2),
        'type':        t.type,
        'cleared':     t.cleared,
        'memo':        t.memo,
        'merchant':        t.merchant or '',
        'posted_date':     t.posted_date.isoformat() if t.posted_date else None,
        'running_balance': t.running_balance,
        'mcc':             t.mcc or '',
        'card_last4':      t.card_last4 or '',
        'source':          t.source or 'manual',
        'check_number':    t.check_number or '',
        'pending':         bool(getattr(t, 'pending', False)),   # item 93 B9: the bank's file said still pending
        # Debt Reconciliation Phase D — which debt_ledger_entries row this
        # checking transaction is linked to (payment/charge), if any. None
        # here means "not linked", not "unknown" — every call site that
        # matters for the 💳 indicator (list_transactions) passes it.
        'linked_debt_entry_id': linked_debt_entry_id,
    }


def serialize_debt_account(d: DebtAccount, session=None) -> dict:
    # If this debt card is linked to an imported account, calculate the
    # real balance from transaction data.
    #
    # Priority:
    # 1. running_balance on the most recent transaction — the bank's own
    #    running total, accurate regardless of how far back the import goes.
    # 2. Net debits - credits — only correct when full history is imported.
    #
    # When a running_balance is found, we also update current_balance on the
    # debt card itself so the debt page always reflects the most recent import.
    #
    # ALL new column accesses use getattr(..., None) so this function never
    # crashes when the migration hasn't run yet (e.g. on first boot after
    # upgrading). The migration adds the columns; until it runs, we return
    # safe nulls.
    calculated_balance  = None
    balance_basis       = None
    linked_account_name = None
    linked_txn_count    = 0
    linked_account_id   = getattr(d, 'linked_account_id', None)

    if linked_account_id and session:
        try:
            from core.database import Transaction as Txn, Account
            acct = session.get(Account, linked_account_id)
            if acct:
                linked_account_name = acct.name
                txns = session.query(Txn).filter_by(
                    account_id=linked_account_id
                ).order_by(Txn.date.desc(), Txn.id.desc()).all()
                linked_txn_count = len(txns)
                if txns:
                    # d21: same-day rows from newest-first exports made
                    # "latest by (date, id)" pick a stale intraday balance —
                    # use the chain-resolved anchor (see _resolve_bank_anchor).
                    latest_with_bal, _chain_ok = _resolve_bank_anchor(txns)
                    if latest_with_bal:
                        # Bank-reported balance. OFX convention for credit
                        # cards is negative-when-owed; debt cards store owed
                        # as positive. Normalize so the cross-check compares
                        # like with like.
                        calculated_balance = round(abs(latest_with_bal.running_balance), 2)
                        balance_basis = 'bank'
                    else:
                        calc = sum(
                            t.amount if t.type == 'debit' else -t.amount
                            for t in txns
                        )
                        # Activity sum can't see the balance that existed
                        # before imported history begins. If payments exceed
                        # imported charges it goes negative — a number we
                        # can't stand behind, so report nothing rather than
                        # mislead the cross-check.
                        if calc > 0:
                            calculated_balance = round(calc, 2)
                            balance_basis = 'activity'
                    # NOTE: no write to d.current_balance here. This is a
                    # serializer — viewing data must never change it. The
                    # client owns applying the bank number, either silently
                    # (diff under $1) or via the cross-check buttons.
        except Exception as _e:
            import logging
            logging.warning('serialize_debt_account linked_account query failed: %s', _e)

    # Safe accessors for columns added in migrations — return None if the
    # column doesn't exist yet rather than crashing the bootstrap endpoint.
    debt_type   = getattr(d, 'debt_type',   None) or 'credit'
    end_date    = getattr(d, 'end_date',    None)
    credit_limit= getattr(d, 'credit_limit',None)
    paid_off_at = getattr(d, 'paid_off_at', None)

    return {
        'id':                   d.id,
        'name':                 d.name,
        'begin_balance':        d.begin_balance,
        'current_balance':      d.current_balance,
        'calculated_balance':   calculated_balance,
        'balance_basis':        balance_basis,
        'linked_txn_count':     linked_txn_count,
        'linked_account_id':    linked_account_id,
        'linked_account_name':  linked_account_name,
        'debt_type':            debt_type,
        'start_date':           d.start_date.isoformat() if d.start_date else None,
        'end_date':             end_date.isoformat() if end_date else None,
        'interest_rate':        d.interest_rate,
        'minimum_payment':      d.minimum_payment,
        'due_day':              d.due_day,
        'credit_limit':         credit_limit,
        'is_active':            d.is_active,
        'paid_off_at':          paid_off_at.isoformat() if paid_off_at else None,
        # A boolean only; the address stays behind the /portal routes (F5).
        'has_portal':           _debt_portal_url(session, d) is not None,
        # V2
        'interest_rate_source':   getattr(d, 'interest_rate_source', None),
        'minimum_payment_source': getattr(d, 'minimum_payment_source', None),
        'statement_as_of':        _latest_statement_date(session, d.id),
    }


def _debt_portal_url(session, d):
    """The link a card opens: its Account's when linked, its own when not (F3)."""
    linked = getattr(d, 'linked_account_id', None)
    if linked:
        acct = session.get(Account, linked) if session is not None else None
        return (getattr(acct, 'portal_url', None) or None) if acct else None
    return getattr(d, 'portal_url', None) or None


def _latest_statement_date(session, debt_id):
    """The latest reconciled statement's closing date for a debt, or None (V2)."""
    if session is None:
        return None
    row = (session.query(DebtBalanceHistory.statement_period_end)
           .filter(DebtBalanceHistory.debt_id == debt_id,
                   DebtBalanceHistory.statement_period_end != None)   # noqa: E711
           .order_by(DebtBalanceHistory.statement_period_end.desc()).first())
    return row[0] if row else None


# ── Transactions ──────────────────────────────────────────────────────────────

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('', methods=['GET'])
def list_transactions():
    """
    List transactions with filtering.
    Query params: account_id, category, type, from_date, to_date,
                  cleared, search, page, per_page
    """
    with db_session() as session:
        q = session.query(Transaction)

        if request.args.get('account_id'):
            q = q.filter(Transaction.account_id == int(request.args['account_id']))
        if request.args.get('category'):
            # Join and filter by category name
            q = q.join(Category).filter(Category.name == request.args['category'])
        if request.args.get('type'):
            q = q.filter(Transaction.type == request.args['type'])
        if request.args.get('from_date'):
            q = q.filter(Transaction.date >= date.fromisoformat(request.args['from_date']))
        if request.args.get('to_date'):
            q = q.filter(Transaction.date <= date.fromisoformat(request.args['to_date']))
        if request.args.get('cleared') is not None:
            q = q.filter(Transaction.cleared == (request.args['cleared'] == 'true'))
        if request.args.get('search'):
            term = f"%{request.args['search']}%"
            q = q.filter(Transaction.description.ilike(term))

        total = q.count()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
        txns = q.order_by(desc(Transaction.date), desc(Transaction.id)) \
                .offset((page - 1) * per_page).limit(per_page).all()

        # Bulk-fetch link status for this page — one indexed query, not N+1.
        # (Debt Reconciliation Phase D: feeds the checking-ledger's 💳 indicator.)
        txn_ids = [t.id for t in txns]
        linked_map = {}
        if txn_ids:
            for row in session.query(
                CheckingTransactionLink.checking_transaction_id,
                CheckingTransactionLink.debt_ledger_entry_id
            ).filter(CheckingTransactionLink.checking_transaction_id.in_(txn_ids)).all():
                linked_map[row[0]] = row[1]

        # Item 93 stage 2: which lines carry corrections (B6), and which posted lines followed a pending one (B9).
        from core import bank_versions as _bv
        corrected = _bv.corrected_ids(session, txn_ids)
        was_pending = _bv.paired_ids(session, txn_ids)
        out = []
        for t in txns:
            d = serialize_transaction(t, linked_map.get(t.id))
            d['corrected'] = t.id in corrected
            d['was_pending'] = was_pending.get(t.id)
            out.append(d)
        return ok(out, total=total, page=page, per_page=per_page)


@transactions_bp.route('', methods=['DELETE'])
def delete_all_transactions():
    """
    Delete EVERY transaction. Irreversible through the app's own undo
    mechanism, so this always makes a full database backup first — done
    server-side (not left to the client to remember) so there's no way to
    skip the safety net. If the backup fails, nothing is deleted.
    """
    import shutil
    from core.database import DB_PATH

    try:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = _write_backup(f'groundwork_backup_pre-delete-all_{ts}')   # item 81: sealed when protection is on
    except Exception as e:
        return err(f'Could not create a safety backup, aborting (nothing was deleted): {e}', 500)

    with db_session() as session:
        count = session.query(Transaction).count()
        # Same dangling-FK edge case as the single-transaction delete, at
        # bulk scale: every checking_transaction_links row and every debt
        # entry's linked_checking_transaction_id would otherwise point at
        # a transaction that's about to stop existing.
        session.query(DebtLedgerEntry).filter(
            DebtLedgerEntry.linked_checking_transaction_id.isnot(None)
        ).update({DebtLedgerEntry.linked_checking_transaction_id: None})
        session.query(CheckingTransactionLink).delete()
        session.query(Transaction).delete()
        session.commit()

    return ok({'deleted': count, 'backup_filename': backup_name})


@transactions_bp.route('', methods=['POST'])
@require_json
def create_transaction():
    body = request.json
    for field in ('date', 'account_id', 'description', 'amount'):
        if body.get(field) in (None, ''):
            return err(f'{field} is required')
    try:
        txn_date = date.fromisoformat(body['date'])
        account_id = int(body['account_id'])
        amount = abs(float(body['amount']))
    except (ValueError, TypeError):
        return err('date, account_id, and amount must be valid')
    with db_session() as session:

        # Resolve or create category
        cat_name = body.get('category', 'Other')
        cat = session.query(Category).filter(
            func.lower(Category.name) == cat_name.lower()
        ).first()
        if not cat:
            # Resolve-never-create — unknown names go to Other (ghost
            # categories broke the budget hierarchy; see import commit).
            cat = session.query(Category).filter(
                func.lower(Category.name) == 'other'
            ).first()

        txn = Transaction(
            account_id=account_id,
            category_id=cat.id,
            date=txn_date,
            description=body['description'],
            amount=amount,
            type=body.get('type', 'debit'),
            cleared=bool(body.get('cleared', False)),
            memo=body.get('memo'),
            merchant=body.get('merchant', ''),
            posted_date=date.fromisoformat(body['posted_date']) if body.get('posted_date') else None,
            running_balance=body.get('running_balance'),
            mcc=body.get('mcc', ''),
            card_last4=body.get('card_last4', ''),
            source=body.get('source', 'manual'),
        )
        session.add(txn)
        session.flush()
        session.commit()
        return ok(serialize_transaction(txn), status=201)


@transactions_bp.route('/<int:txn_id>', methods=['PATCH'])
@require_json
def update_transaction(txn_id):
    body = request.json
    with db_session() as session:
        txn = session.get(Transaction, txn_id)
        if not txn:
            return err('Transaction not found', 404)

        if 'cleared' in body:
            txn.cleared = bool(body['cleared'])
        if 'category' in body:
            cat = session.query(Category).filter(
                func.lower(Category.name) == body['category'].lower()
            ).first()
            if not cat:
                cat = Category(name=body['category'])
                session.add(cat)
                session.flush()
            txn.category_id = cat.id
        if 'description' in body:
            txn.description = body['description']
        if 'amount' in body:
            txn.amount = abs(float(body['amount']))
        if 'memo' in body:
            txn.memo = body['memo']
        if 'check_number' in body:
            txn.check_number = body.get('check_number', '')
        if 'date' in body:
            txn.date = date.fromisoformat(body['date'])
        if 'type' in body and body['type'] in ('debit', 'credit'):
            txn.type = body['type']
        if 'account_id' in body:
            txn.account_id = int(body['account_id'])
        if 'merchant' in body:
            txn.merchant = body['merchant']

        session.commit()
        return ok(serialize_transaction(txn))


@transactions_bp.route('/<int:txn_id>/versions', methods=['GET'])
def transaction_versions(txn_id):
    """Item 93 B6/B9: the line now, the earliest version kept, every correction between, and the pending line it
    followed. Every total uses the line as it is now."""
    from core import bank_versions
    with db_session() as session:
        txn = session.get(Transaction, txn_id)
        if not txn:
            return err('Transaction not found', 404)
        return ok(bank_versions.versions(session, txn))


def _unlink_debt_for_deleted_transaction(session, txn_id: int):
    """
    Debt Reconciliation Phase G edge case: deleting a checking transaction
    that's linked to a debt ledger entry must not leave a dangling FK.
    Same "unlink, don't delete" rule as the explicit unlink endpoint — the
    debt entry (someone's real charge or payment record) survives, it just
    stops pointing at a transaction that no longer exists.
    """
    link = session.query(CheckingTransactionLink).filter_by(checking_transaction_id=txn_id).first()
    if not link:
        return
    entry = session.get(DebtLedgerEntry, link.debt_ledger_entry_id)
    if entry:
        entry.linked_checking_transaction_id = None
    session.delete(link)


@transactions_bp.route('/<int:txn_id>', methods=['DELETE'])
def delete_transaction(txn_id):
    with db_session() as session:
        txn = session.get(Transaction, txn_id)
        if not txn:
            return err('Transaction not found', 404)
        # Item 93 B7: deleting hides; it never destroys. Set aside whole, debt link remembered, restorable.
        from core import import_custody as ic
        sa = ic.set_aside(session, txn, reason=str((request.get_json(silent=True) or {}).get('reason') or ''))
        session.commit()
        return ok({'deleted': txn_id, 'set_aside': sa.id})


@transactions_bp.route('/set-aside', methods=['GET'])
def set_aside_get():
    from core import import_custody as ic
    with db_session() as session:
        return ok({'set_aside': ic.set_aside_list(session), 'batches': ic.batches(session)})


@transactions_bp.route('/set-aside/<int:sa_id>/restore', methods=['POST'])
def set_aside_restore(sa_id):
    from core import import_custody as ic
    with db_session() as session:
        txn, problem = ic.restore(session, sa_id)
        if problem:
            return err(problem)
        session.commit()
        return ok({'restored': txn.id})


@transactions_bp.route('/import-batches/<batch>/set-aside', methods=['POST'])
def import_batch_set_aside(batch):
    """Item 93 B7: a mistaken import, set aside as a batch - every line restorable."""
    from core import import_custody as ic
    with db_session() as session:
        n = ic.set_aside_batch(session, batch)
        session.commit()
        return ok({'set_aside': n})


@transactions_bp.route('/bulk-clear', methods=['POST'])
@require_json
def bulk_clear():
    """Mark multiple transactions as cleared."""
    body = request.json
    ids = body.get('ids', [])
    cleared = bool(body.get('cleared', True))
    with db_session() as session:
        updated = session.query(Transaction) \
            .filter(Transaction.id.in_(ids)) \
            .all()
        for t in updated:
            t.cleared = cleared
        session.commit()
        return ok({'updated': len(updated)})


# ── Accounts ──────────────────────────────────────────────────────────────────

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('', methods=['GET'])
def list_accounts():
    with db_session() as session:
        accounts = session.query(Account).filter_by(is_active=True) \
                          .order_by(Account.sort_order, Account.name).all()
        return ok([{
            'id': a.id, 'name': a.name, 'type': a.type,
            'institution': a.institution, 'currency': a.currency,
            'has_portal': bool(getattr(a, 'portal_url', None)),
        } for a in accounts])


@accounts_bp.route('', methods=['POST'])
@require_json
def create_account():
    body = request.json
    name = (body.get('name') or '').strip()
    if not name:
        return err('name is required')
    with db_session() as session:
        existing = session.query(Account).filter(
            func.lower(Account.name) == name.lower()
        ).first()
        if existing:
            # Re-activate if archived
            if not existing.is_active:
                existing.is_active  = True
                existing.type       = body.get('type', existing.type)
                existing.institution= body.get('institution', existing.institution)
                session.commit()
                return ok(_serialize_account(existing, session))
            return err(f'Account "{name}" already exists')
        account = Account(
            name=name,
            type=body.get('type', 'checking'),
            institution=body.get('institution', ''),
            sort_order=body.get('sort_order', 0),
            is_active=True,
        )
        session.add(account)
        session.flush()
        session.commit()
        return ok(_serialize_account(account, session), status=201)


@accounts_bp.route('/<int:account_id>', methods=['PATCH'])
@require_json
def update_account(account_id):
    body = request.json
    with db_session() as session:
        acct = session.get(Account, account_id)
        if not acct:
            return err('Account not found', 404)
        if 'name'            in body and body['name'].strip():
            acct.name            = body['name'].strip()
        if 'type'            in body: acct.type            = body['type']
        if 'institution'     in body: acct.institution     = body['institution']
        if 'currency'        in body: acct.currency        = body['currency']
        if 'sort_order'      in body: acct.sort_order      = int(body['sort_order'])
        if 'minimum_balance' in body: acct.minimum_balance = float(body['minimum_balance'] or 0)
        session.commit()
        return ok(_serialize_account(acct, session))


@accounts_bp.route('/<int:account_id>', methods=['DELETE'])
def archive_account(account_id):
    """
    Archive (soft-delete) an account. Transactions are preserved.
    Archived accounts are hidden from import dropdowns and summaries
    but can be re-activated by POSTing with the same name.
    """
    with db_session() as session:
        acct = session.get(Account, account_id)
        if not acct:
            return err('Account not found', 404)
        txn_count = session.query(Transaction).filter_by(account_id=account_id).count()
        acct.is_active = False
        session.commit()
    # An archived account's bank window closes (F2).
    import bank_window
    bank_window.close_bank_window(('account', account_id))
    return ok({'archived': account_id, 'transactions_preserved': txn_count})


# ── HSA and FSA (gw 2.0/HSA_FSA.md, item 86 = item 45 H5; ruled 2026-10-14) ──────────────────────────────────────
# Money only. The figures and sentences come from core/hsa_fsa.py with their working; every term the person did not
# enter stays unknown. No advice (F7).

# ── Item 89 U4 (CARE_NEVER_A_LEVER.md): "Is this health care?" - only the person's answer is stored ─────────────

# ── Item 91 (VISIT_REPORT_YEAR_REVIEW.md V1-V4): the visit report - per provider, templated, nothing stored ───────

# ── Item 92 (NAMED_PEOPLE.md N1-N8): named people, and whom a health payment was for ────────────────────────────
# Names are labels, not locks (N3). Whom care was for is said, never inferred (N2); an answer is kept (N4). The tag is
# a 1.x record of the household's answer (N8 decided 2026-10-17). Names never reach the model or an untickable export.

@accounts_bp.route('/people', methods=['GET'])
def people_list():
    from core import people
    with db_session() as session:
        return ok(people.listing(session))


@accounts_bp.route('/people', methods=['POST'])
@require_json
def people_add():
    from core import people
    with db_session() as session:
        p, problem = people.add(session, (request.json or {}).get('name'))
        if problem:
            return err(problem)
        session.commit()
        return ok(people.listing(session))


@accounts_bp.route('/people/<int:person_id>/rename', methods=['POST'])
@require_json
def people_rename(person_id):
    from core import people
    with db_session() as session:
        _p, problem = people.rename(session, person_id, (request.json or {}).get('name'))
        if problem:
            return err(problem)
        session.commit()
        return ok(people.listing(session))


@accounts_bp.route('/people/<int:person_id>/remove', methods=['POST'])
def people_remove(person_id):
    from core import people
    with db_session() as session:
        what, problem = people.remove(session, person_id)
        if problem:
            return err(problem, 404)
        session.commit()
        return ok(dict(people.listing(session), done=what))


@accounts_bp.route('/care-for/<int:transaction_id>', methods=['GET'])
def care_for_get(transaction_id):
    """The Ledger's slot: whether this payment is health, whom it was for now, and the earlier answers."""
    from core import health_boundary, people
    with db_session() as session:
        t = session.get(Transaction, transaction_id)
        health = bool(t) and t.type == 'debit' and health_boundary.health_rows(session)(t)
        return ok({'health': health, 'person_id': people.current(session, transaction_id) if health else None,
                   'answered': bool(health and people.history(session, transaction_id)),
                   'history': people.history(session, transaction_id) if health else [],
                   'people': [x for x in people.listing(session)['people'] if x['active']] if health else []})


# ── Item 93 stages 3-4 (BANK_SIDE_RECORDS.md B2-B4, B8, B11): the household's statements in the 2.0 records ──────
# Every route that mints answers `need_speaker` (409) when no one has said who is answering; the page asks once and
# tries again (Rob 2026-10-18). Nothing here changes a total.

def _statement(fn):
    """Run a statement. NeedSpeaker and NeedBank become 409s the page answers by asking (who is answering; which bank
    holds the line's account) and trying again. Nothing is kept from the attempt: its session is never committed."""
    from core import household_statements as hs
    try:
        return fn()
    except hs.NeedSpeaker:
        return err(hs.NEED_SPEAKER_TEXT, 409)
    except hs.NeedBank as e:
        return jsonify({'ok': False, 'error': str(e), 'need_bank': {'account_id': e.account_id, 'account': e.account,
                                                                    'candidate': e.candidate}}), 409


@accounts_bp.route('/speaker', methods=['GET'])
def speaker_get():
    from core import household_statements as hs, people
    with db_session() as session:
        return ok({**hs.speaker_view(session), 'people': [x for x in people.listing(session)['people'] if x['active']],
                   'offer': people.listing(session)['offer']})


@accounts_bp.route('/speaker', methods=['POST'])
@require_json
def speaker_set():
    """{person_id} or {name}: who is answering on this computer, remembered until changed."""
    from core import household_statements as hs, people
    body = request.json or {}
    with db_session() as session:
        pid = body.get('person_id')
        if not pid and (body.get('name') or '').strip():
            p, problem = people.add(session, body.get('name'))
            if problem:
                return err(problem)
            pid = p.id
        p, problem = hs.set_speaker(session, pid)
        if problem:
            return err(problem)
        session.commit()
        return ok(hs.speaker_view(session))


@accounts_bp.route('/banks', methods=['GET'])
def banks_get():
    from core import household_statements as hs
    with db_session() as session:
        return ok(hs.bank_questions(session))


@accounts_bp.route('/banks/<int:account_id>', methods=['POST'])
@require_json
def banks_say(account_id):
    """B2: {name} - "this account is at NAME" - or {not_a_bank: true}."""
    from core import household_statements as hs
    body = request.json or {}

    def go():
        with db_session() as session:
            row, problem = hs.say_bank(session, account_id, body.get('name'), bool(body.get('not_a_bank')))
            if problem:
                return err(problem)
            session.commit()
            return ok(hs.bank_questions(session))
    return _statement(go)


@accounts_bp.route('/line-statement/<int:txn_id>', methods=['GET'])
def line_statement_get(txn_id):
    from core import household_statements as hs
    with db_session() as session:
        return ok(hs.line_view(session, txn_id))


@accounts_bp.route('/line-statement/<int:txn_id>', methods=['POST'])
@require_json
def line_statement_say(txn_id):
    """B3, one line at a time: {payee} - "that was my payment to PAYEE"."""
    from core import household_statements as hs
    body = request.json or {}

    def go():
        with db_session() as session:
            rec, problem = hs.say_payment(session, txn_id, body.get('payee'))
            if problem:
                return err(problem)
            session.commit()
            return ok(hs.line_view(session, txn_id))
    return _statement(go)


@accounts_bp.route('/standing', methods=['GET'])
def standing_get():
    from core import household_statements as hs
    with db_session() as session:
        args = request.args
        preview = None
        if args.get('account_id') and args.get('payee'):
            preview = len(hs.covered_lines(session, int(args['account_id']), args['payee']))
        return ok({'standing': hs.standing_list(session), 'covers': preview})


@accounts_bp.route('/standing', methods=['POST'])
@require_json
def standing_say():
    """B3, the importer contract: {account_id, payee} - "treat every debit from this account to PAYEE as my payment"."""
    from core import household_statements as hs
    body = request.json or {}

    def go():
        with db_session() as session:
            st, n, problem = hs.say_standing(session, body.get('account_id'), body.get('payee'))
            if problem:
                return err(problem)
            session.commit()
            return ok({'id': st.id, 'payments': n, 'standing': hs.standing_list(session)})
    return _statement(go)


@accounts_bp.route('/standing/<int:sid>/withdraw', methods=['POST'])
def standing_withdraw(sid):
    from core import household_statements as hs

    def go():
        with db_session() as session:
            st, problem = hs.withdraw_standing(session, sid)
            if problem:
                return err(problem)
            session.commit()
            return ok({'standing': hs.standing_list(session)})
    return _statement(go)


@accounts_bp.route('/reversals', methods=['GET'])
def reversals_get():
    from core import household_statements as hs
    with db_session() as session:
        return ok({'candidates': hs.reversal_candidates(session)})


@accounts_bp.route('/reversals', methods=['POST'])
@require_json
def reversals_answer():
    """B8: {credit_id, debit_id, answer: yes | no}. A yes is the household's claim that the money-in line undoes the
    charge; nothing is netted off. A no is kept so the pair isn't asked again."""
    from core import household_statements as hs
    body = request.json or {}
    if body.get('answer') not in ('yes', 'no'):
        return err('answer yes or no')

    def go():
        with db_session() as session:
            row, problem = hs.answer_reversal(session, body.get('credit_id'), body.get('debit_id'), body['answer'] == 'yes')
            if problem:
                return err(problem)
            session.commit()
            return ok({'candidates': hs.reversal_candidates(session)})
    return _statement(go)


@accounts_bp.route('/earlier-answers', methods=['GET'])
def earlier_answers_get():
    from core import household_statements as hs
    with db_session() as session:
        return ok({'answers': hs.earlier(session), **hs.speaker_view(session)})


@accounts_bp.route('/earlier-answers', methods=['POST'])
@require_json
def earlier_answers_confirm():
    """B11 (Rob 2026-10-18: confirm them once): {items: [{source, source_id}]} - "these were mine"."""
    from core import household_statements as hs
    body = request.json or {}

    def go():
        with db_session() as session:
            n, problem = hs.confirm_earlier(session, body.get('items') or [])
            if problem:
                return err(problem)
            session.commit()
            return ok({'confirmed': n, 'answers': hs.earlier(session)})
    return _statement(go)


@accounts_bp.route('/care-for', methods=['POST'])
@require_json
def care_for_set():
    """N4: {transaction_id, person_id | 'household'} - or {ids: [...], person_id} for the payee offer, on a yes."""
    from core import people
    body = request.json or {}
    with db_session() as session:
        if body.get('ids') is not None:
            n, problem = people.assign_many(session, body.get('ids'), body.get('person_id'))
            if problem:
                return err(problem)
            _carry_care(session, body.get('ids') or [])
            session.commit()
            return ok({'assigned': n})
        row, problem = people.assign(session, body.get('transaction_id'), body.get('person_id'))
        if problem:
            return err(problem)
        _carry_care(session, [body.get('transaction_id')])
        session.commit()
        tid = int(body.get('transaction_id'))
        return ok({'person_id': people.current(session, tid), 'history': people.history(session, tid),
                   'offer': people.same_payee_offer(session, tid) if body.get('person_id') not in (None, '', 'household') else None})


def _carry_care(session, ids):
    """Item 93 B11: a care-for answer given while someone is answering is their statement at once; otherwise it waits
    among the earlier answers to confirm."""
    from core import household_statements as hs
    from core.database import CareFor
    for tid in ids:
        row = session.query(CareFor).filter_by(transaction_id=int(tid or 0)).order_by(CareFor.id.desc()).first()
        if row is not None and row.person_id is not None:
            hs.carry_new(session, 'care', row.id)


@accounts_bp.route('/health-providers', methods=['GET'])
def health_providers():
    from core import health_documents as hd
    with db_session() as session:
        return ok({'providers': hd.providers(session)})


@accounts_bp.route('/visit-report', methods=['POST'])
@require_json
def visit_report():
    """V1: {names: [exact payee names]} -> the report. Q3: it leaves only by the person's own print or save."""
    from core import health_documents as hd
    with db_session() as session:
        body = request.json or {}
        rep, problem = hd.visit_report(session, body.get('names') or [], _resolve_bank_anchor, _reserve_balance,
                                       person_id=body.get('person_id'))     # item 92 N5a
        if problem:
            return err(problem)
        return ok(rep)


@accounts_bp.route('/care-questions', methods=['GET'])
def care_questions():
    from core import care_status
    with db_session() as session:
        return ok({'questions': care_status.questions(session), 'answered': care_status.answered(session)})


@accounts_bp.route('/care-questions', methods=['POST'])
@require_json
def care_answer():
    from core import care_status
    body = request.json or {}
    with db_session() as session:
        row, problem = care_status.answer(session, body.get('category_id'), str(body.get('answer') or '').lower())
        if problem:
            return err(problem)
        session.commit()
        return ok({'saved': row.id, 'questions': care_status.questions(session), 'answered': care_status.answered(session)})


@accounts_bp.route('/hsa-fsa', methods=['GET'])
def hsa_fsa_list():
    from core import hsa_fsa
    with db_session() as session:
        rows = hsa_fsa.states(session, _resolve_bank_anchor)
        return ok({'accounts': rows, 'attention': hsa_fsa.attention(rows), 'warn_days': hsa_fsa.FSA_WARN_DAYS,
                   'limit_years': sorted(hsa_fsa.LIMITS)})


# ── The health plan (gw 2.0/PLAN_YEAR_TRACKING.md, item 87 = item 45 H7 stage 2; ruled 2026-10-15) ──────────────
# Progress is what the insurer reports, typed with its date - never summed from spending (P1). Every write refreshes
# the H6 scrubber, so a plan's name is health text from the moment it is saved (P8).

def _health_plan_done(session, out):
    from core import health_boundary
    session.commit()
    health_boundary.refresh(session)
    from core import health_plan
    return ok(health_plan.states(session) | ({'saved': out} if out is not None else {}))


# ── The health reserve (gw 2.0/HEALTH_RESERVE.md, item 88 = item 45 H7 stage 3; ruled 2026-10-16) ───────────────
# A level of a named account's balance, never a movement (R3). The before / alongside / after choice is the
# person's, each shown through the same engine with no option labelled best (R1).

def _reserve_balance(session, account_id):
    """The bank's own reported balance and its date, or unknown - never the sum of imported activity (d21)."""
    bal, as_of, _last, _txns = _account_balance_facts(session, account_id)
    return (bal, as_of.strftime('%b %d, %Y')) if as_of is not None else (None, None)


def _reserve_payload(session):
    from core import health_reserve as hr
    st = hr.state(session, _resolve_bank_anchor, _reserve_balance)
    cards, budget, strategy, _undated = _consequence_inputs(session)
    ch = st.get('choice') or {}
    st['options'] = hr.options(cards, budget, strategy, st['gap'], monthly=ch.get('monthly'))
    st['applied'] = hr.applied(hr.request_plan(session, _resolve_bank_anchor), cards, budget)   # item 90 D4
    return st


# ── Item 94 (BILL_THAT_LANDS.md, L1-L10 ruled 2026-10-19): the bill that lands ────────────────────────────────────────
# The provider's statements as the household typed them, the amount owed now with its working, and every fact the record
# supports - templated in core/medical_bills.py, no model, nothing contacting anyone. Statements go through _statement:
# each is the answering person's utterance (item 93).
medical_bp = Blueprint('medical', __name__)


def _bills_ctx(session):
    """What the alarm (L6) and the capacity (L8) are measured against: savings on record, the reserve as allocated,
    the stability floor (one month of recorded expenses, C.5), and the leanest complete month on record."""
    from core import medical_bills as mb
    from core.database import ReserveAllocation
    from core.income_def import income_category_ids

    def setting(key):
        row = session.query(AppSetting).filter_by(key=key).first()
        try:
            return (float(row.value), True) if row and row.value not in (None, '') else (0.0, False)
        except (TypeError, ValueError):
            return 0.0, False
    (sav, k1), (cash, k2) = setting('savings_balance'), setting('cash_balance')
    alloc = session.query(ReserveAllocation).order_by(ReserveAllocation.seq.desc()).first()
    reserve = float(alloc.amount) if alloc else 0.0
    floor = sum(v['month_amount'] for v in budget_month_amounts(session).values())
    # L8: the leanest of the last twelve complete months - money in by the one income definition, money out less transfers
    month_start = date.today().replace(day=1)
    since = (month_start - timedelta(days=366)).replace(day=1)
    inc_ids, tr_ids = income_category_ids(session), _transfer_category_ids(session)
    months = {}
    for t in session.query(Transaction).filter(Transaction.date >= since, Transaction.date < month_start).all():
        m = months.setdefault(t.date.strftime('%Y-%m'), [0.0, 0.0])
        if t.type == 'credit' and t.category_id in inc_ids:
            m[0] += float(t.amount or 0)
        elif t.type == 'debit' and t.category_id not in tr_ids:
            m[1] += float(t.amount or 0)
    from core.health_reserve import _setting as _hr_setting
    choice = (_hr_setting(session, 'reserve_order_json', []) or [None])[-1] or {}
    fill = float(choice.get('monthly') or 0) if choice.get('choice') in ('before', 'alongside') else 0.0
    if len(months) < MIN_MONTHS_OBSERVED:
        cap = {'thin': True, 'months': len(months)}
    else:
        key = min(months, key=lambda k: months[k][0] - months[k][1])
        left = round(months[key][0] - months[key][1], 2)
        cap = {'thin': False, 'months': len(months), 'leanest': date.fromisoformat(key + '-01').strftime('%B %Y'),
               'left': left, 'reserve_monthly': fill, 'monthly': round(left - fill, 2)}
    return {'liquid': sav + cash, 'liquid_known': k1 or k2, 'reserve': reserve, 'floor': round(floor, 2), 'capacity': cap}


@medical_bp.route('', methods=['GET'])
def medical_bills_get():
    """Every bill account, the dates (L9) and the attention items (L6)."""
    from core import medical_bills as mb
    from core.database import MedicalBillAccount
    with db_session() as session:
        ctx = _bills_ctx(session)
        views = [mb.view(session, a, ctx) for a in session.query(MedicalBillAccount).order_by(MedicalBillAccount.id).all()]
        cards, budget, strategy, _undated = _consequence_inputs(session)
        today = date.today().strftime('%Y-%m')
        sim = simulate_payoff(cards, budget, strategy, today_key=today, start_month=today) if cards else {'months': 0}
        card_free = None if sim is None or sim.get('capped') else int(sim.get('months') or 0)   # None: not reached at this budget
        return ok({'bills': views, 'dates': mb.obligations_date(views, card_free),
                   'attention': [v['attention'] for v in views if v.get('attention')], 'never_directs': mb.NEVER_DIRECTS})


@medical_bp.route('/statement', methods=['POST'])
@require_json
def medical_bill_statement():
    """L1: a provider's bill or an insurer's explanation of benefits, as the household typed it."""
    from core import medical_bills as mb

    def go():
        with db_session() as session:
            a, problem = mb.add_statement(session, request.json or {})
            if problem:
                return err(problem)
            session.commit()
            return ok({'id': a.id})
    return _statement(go)


@medical_bp.route('/<int:account_id>/<what>', methods=['POST'])
@medical_bp.route('/<int:account_id>/collections', methods=['POST'], defaults={'what': 'collections'})   # item 101
@require_json
def medical_bill_say(account_id, what):
    """mine | claim {pending} | arrangement {monthly, first_date, payments} or {none} | payment {transaction_id} |
    collections {collector, account_number, sent_on, amount, statement_date} (item 101)"""
    from core import medical_bills as mb
    body = request.json or {}
    fns = {'mine': lambda s: mb.say_mine(s, account_id),
           'claim': lambda s: mb.say_claim(s, account_id, bool(body.get('pending'))),
           'arrangement': lambda s: mb.say_arrangement(s, account_id, body),
           'payment': lambda s: mb.link_payment(s, account_id, body.get('transaction_id')),
           'collections': lambda s: mb.send_to_collections(s, account_id, body)}       # item 101 C2
    if what not in fns:
        return err('Not a statement about a bill.', 404)

    def go():
        with db_session() as session:
            _x, problem = fns[what](session)
            if problem:
                return err(problem)
            session.commit()
            return ok({'id': account_id})
    return _statement(go)


@medical_bp.route('/providers/<int:provider_id>/kind', methods=['POST'])
@require_json
def medical_provider_nonprofit(provider_id):
    """L7: {value: true | false | null} - the household's word on whether the provider is a non-profit hospital."""
    from core import medical_bills as mb
    v = (request.json or {}).get('value')

    def go():
        with db_session() as session:
            _p, problem = mb.say_nonprofit(session, provider_id, v if v in (True, False) else None)
            if problem:
                return err(problem)
            session.commit()
            return ok({'id': provider_id})
    return _statement(go)


@medical_bp.route('/<int:account_id>/lines', methods=['GET'])
def medical_bill_lines(account_id):
    """L2/L5: recent money-out lines the household may say were toward this bill (the last 120 days)."""
    from core.database import Account
    with db_session() as session:
        since = date.today() - timedelta(days=120)
        rows = session.query(Transaction).filter(Transaction.type == 'debit', Transaction.date >= since) \
            .order_by(Transaction.date.desc()).limit(60).all()
        accts = {a.id: a.name for a in session.query(Account).all()}
        return ok({'lines': [{'id': t.id, 'date': t.date.isoformat() if t.date else '', 'amount': round(float(t.amount or 0), 2),
                              'what': (t.merchant or t.description or '')[:60], 'account': accts.get(t.account_id, '')}
                             for t in rows]})


@medical_bp.route('/<int:account_id>/budget', methods=['POST'])
def medical_bill_budget(account_id):
    """L4, on the household's tap: the agreed arrangement as a budget line (a bill on the Budget page, item 68)."""
    import json as _j
    from core.database import MedicalBillAccount, MedicalProvider
    from core.health_boundary import is_health_category
    with db_session() as session:
        a = session.get(MedicalBillAccount, account_id)
        arr = ((_j.loads(a.arrangement_json or '[]') or [{}])[-1]) if a else {}
        if not a or not arr.get('monthly'):
            return err('Record the arrangement the provider agreed first.')
        prov = session.get(MedicalProvider, a.provider_id)
        cat = next((c for c in session.query(Category).order_by(Category.id).all()
                    if c.parent_id is None and is_health_category(c.name)), None)
        item = BudgetItem(name=f'{prov.name if prov else "Medical bill"} - payment arrangement', amount=arr['monthly'],
                          type='expense', category=cat.name if cat else 'Other', is_active=True)
        session.add(item)
        session.commit()
        return ok({'budget_item_id': item.id, 'category': item.category, 'name': item.name, 'amount': item.amount})


@accounts_bp.route('/health-summary', methods=['GET'])
def health_summary_get():
    """Item 100 HP5: health money out by month and by person, as recorded (core/health_page.py). Never a lever."""
    from core import health_page
    with db_session() as session:
        return ok(health_page.summary(session))


@accounts_bp.route('/health-reserve', methods=['GET'])
def health_reserve_get():
    with db_session() as session:
        return ok(_reserve_payload(session))


@accounts_bp.route('/health-reserve/target', methods=['POST'], defaults={'what': 'target'})
@accounts_bp.route('/health-reserve/reserved', methods=['POST'], defaults={'what': 'reserved'})
@accounts_bp.route('/health-reserve/choice', methods=['POST'], defaults={'what': 'choice'})
@require_json
def health_reserve_set(what):
    """target {basis, amount} | reserved {amount, account_id, reason} | choice {choice, monthly}"""
    from core import health_reserve as hr
    fn = {'target': hr.set_target, 'reserved': hr.set_reserved, 'choice': hr.set_choice}.get(what)
    if not fn:
        return err('Unknown setting.', 404)
    with db_session() as session:
        _row, problem = fn(session, request.json or {})
        if problem:
            return err(problem)
        session.commit()
        return ok(_reserve_payload(session))


@accounts_bp.route('/health-plans', methods=['GET'])
def health_plans_list():
    from core import health_plan
    with db_session() as session:
        return ok(health_plan.states(session))


@accounts_bp.route('/health-plans', methods=['POST'])
@require_json
def health_plans_add():
    from core import health_plan
    with db_session() as session:
        plan, problem = health_plan.add_plan(session, request.json or {})
        if problem:
            return err(problem)
        return _health_plan_done(session, plan.id)


@accounts_bp.route('/health-plans/<int:plan_id>/terms', methods=['POST'])
@require_json
def health_plans_terms(plan_id):
    """P2: {mode: 'correction' | 'change', deductible, oop_max, tier, from (a change), reason}."""
    from core import health_plan
    from core.database import HealthPlan
    body = request.json or {}
    with db_session() as session:
        plan = session.get(HealthPlan, plan_id)
        if not plan:
            return err('That plan was not found.', 404)
        mode = body.get('mode')
        if mode == 'correction':
            row, problem = health_plan.correct_terms(session, plan, body)
        elif mode == 'change':
            row, problem = health_plan.change_terms(session, plan, body)
        else:
            return err('Say whether the figure changed from a date, or was always this (mode: change or correction).')
        if problem:
            return err(problem)
        return _health_plan_done(session, row.id)


@accounts_bp.route('/health-plans/<int:plan_id>/readings', methods=['POST'])
@require_json
def health_plans_reading(plan_id):
    """P1/P3: {deductible_met, oop_met, as_of} - what the insurer reports, as typed."""
    from core import health_plan
    from core.database import HealthPlan
    with db_session() as session:
        plan = session.get(HealthPlan, plan_id)
        if not plan:
            return err('That plan was not found.', 404)
        row, problem = health_plan.add_reading(session, plan, request.json or {})
        if problem:
            return err(problem)
        return _health_plan_done(session, row.id)


@accounts_bp.route('/<int:account_id>/terms', methods=['GET'])
def hsa_fsa_terms_history(account_id):
    from core import hsa_fsa
    with db_session() as session:
        acct = session.get(Account, account_id)
        if not acct or acct.type not in hsa_fsa.TYPES:
            return err('That HSA or FSA account was not found.', 404)
        return ok({'account_id': acct.id, 'kind': acct.type, 'history': hsa_fsa.history(session, acct.id)})


@accounts_bp.route('/<int:account_id>/terms', methods=['POST'])
@require_json
def hsa_fsa_terms_save(account_id):
    """F2: {plan_year, coverage, catch_up, year_end, rule, grace_until, carryover_max, claims_by, election,
    typed_contributions, typed_balance, typed_balance_on}. Adds a row; the old terms stay as history."""
    from core import hsa_fsa
    body = request.json or {}
    try:
        year = int(body.get('plan_year') or date.today().year)
    except (TypeError, ValueError):
        return err('plan_year must be a year')
    if not 2000 <= year <= 2100:
        return err('plan_year must be a year')
    with db_session() as session:
        acct = session.get(Account, account_id)
        if not acct or acct.type not in hsa_fsa.TYPES:
            return err('That HSA or FSA account was not found.', 404)
        row, problem = hsa_fsa.save_terms(session, acct, year, body)
        if problem:
            return err(problem)
        session.commit()
        txns = session.query(Transaction).filter_by(account_id=acct.id).all()
        state = (hsa_fsa.hsa_state if acct.type == 'hsa' else hsa_fsa.fsa_state)(session, acct, txns, _resolve_bank_anchor)
        return ok({'saved': row.id, 'state': state})


# ── The bank window's link (gw 2.0/BANK_BROWSER.md) ───────────────────────────
# These routes are the ONLY readers and writers of portal_url. The link is
# launch configuration for a webpage, not financial evidence or model context:
# the serializers carry has_portal (a boolean) and nothing else, so the address
# cannot reach the snapshot, a prompt, a finding or an export (F5; s126 pins it).
# Groundwork does not verify that the address belongs to the institution (F4).

def _portal_body_url(body):
    """(url or None, problem or None) from a PUT body. Empty clears the link."""
    import bank_window
    raw = (body.get('url') or '').strip() if isinstance(body, dict) else ''
    if not raw:
        return None, None
    problem = bank_window.portal_url_problem(raw)
    if problem:
        return None, problem
    return bank_window.normalise_portal_url(raw), None


def _portal_open(key, url, mode):
    import bank_window
    if not url:
        return err('No bank website is set for this account.', 404)
    if mode == 'browser':
        result = bank_window.open_in_browser(url)
    else:
        result = bank_window.open_bank_window(key, url)
    if result == 'refused_url':
        return err('This address can no longer be opened. Check it in the account settings.', 400)
    return ok({'result': result})


@accounts_bp.route('/<int:account_id>/portal', methods=['GET'])
def get_account_portal(account_id):
    with db_session() as session:
        acct = session.get(Account, account_id)
        if not acct:
            return err('Account not found', 404)
        return ok({'url': acct.portal_url or ''})


@accounts_bp.route('/<int:account_id>/portal', methods=['PUT'])
@require_json
def put_account_portal(account_id):
    url, problem = _portal_body_url(request.json)
    if problem:
        return err(problem, 400)
    with db_session() as session:
        acct = session.get(Account, account_id)
        if not acct:
            return err('Account not found', 404)
        acct.portal_url = url
        session.commit()
        return ok({'url': url or ''})


@accounts_bp.route('/<int:account_id>/portal/open', methods=['POST'])
def open_account_portal(account_id):
    mode = (request.get_json(silent=True) or {}).get('mode', 'window')
    with db_session() as session:
        acct = session.get(Account, account_id)
        if not acct:
            return err('Account not found', 404)
        url = acct.portal_url
    return _portal_open(('account', account_id), url, mode)


@accounts_bp.route('/<int:account_id>/summary', methods=['GET'])
def account_summary(account_id):
    """
    Per-account balance and transaction summary.
    Returns running balance (credits − debits), transaction count,
    date of first and last transaction.
    """
    with db_session() as session:
        acct = session.get(Account, account_id)
        if not acct:
            return err('Account not found', 404)

        txns = session.query(Transaction).filter_by(account_id=account_id).all()
        if not txns:
            return ok({
                'id': account_id, 'name': acct.name,
                'balance': 0.0, 'transaction_count': 0,
                'first_date': None, 'last_date': None,
                'total_credits': 0.0, 'total_debits': 0.0,
            })

        credits = sum(t.amount for t in txns if t.type == 'credit')
        debits  = sum(t.amount for t in txns if t.type == 'debit')
        dates   = sorted(t.date for t in txns)

        return ok({
            'id':                account_id,
            'name':              acct.name,
            'type':              acct.type,
            'institution':       acct.institution or '',
            'balance':           round(credits - debits, 2),
            'transaction_count': len(txns),
            'first_date':        dates[0].isoformat()  if dates else None,
            'last_date':         dates[-1].isoformat() if dates else None,
            'total_credits':     round(credits, 2),
            'total_debits':      round(debits, 2),
        })


def _resolve_bank_anchor(txns):
    """
    Pick the transaction whose running_balance is the account's CURRENT bank-
    reported balance. (d21, field-caught: Superior CU CSVs are newest-first
    and post several rows per day, so 'latest by (date, id)' selects the
    physically-last-inserted row — a stale intraday balance.)

    Same-day rows are ordered by the bank's own arithmetic: undoing a row
    (running_balance + amount for a debit, − amount for a credit) yields the
    balance BEFORE it. The latest row of the day is the one whose
    running_balance is not any other row's balance-before. This both orders
    the day and verifies the chain links — a broken chain means the rows
    don't reconcile, and we fall back to insertion order.

    Returns (anchor_txn, chain_ok) or (None, True) when no row carries a
    bank-reported balance.
    """
    with_rb = [t for t in txns
               if getattr(t, 'running_balance', None) not in (None, 0)]
    if not with_rb:
        return None, True
    last_date = max(t.date for t in with_rb)
    day_rows  = [t for t in with_rb if t.date == last_date]
    if len(day_rows) == 1:
        return day_rows[0], True
    EPS = 0.005
    priors = []
    for t in day_rows:
        prior = t.running_balance + t.amount if t.type == 'debit' \
                else t.running_balance - t.amount
        priors.append(round(prior, 2))
    candidates = [t for i, t in enumerate(day_rows)
                  if not any(abs(t.running_balance - p) <= EPS
                             for j, p in enumerate(priors) if j != i)]
    if len(candidates) == 1:
        return candidates[0], True
    # Chain didn't resolve cleanly (missing rows, duplicate balances) —
    # best-effort by insertion id, flagged so the caller can label it.
    return max(day_rows, key=lambda t: t.id), False


@accounts_bp.route('/with-balances', methods=['GET'])
def accounts_with_balances():
    """
    List all active accounts with pre-computed balances and transaction counts.

    d21 (field-caught): 'balance' was the raw activity sum (credits − debits)
    over imported rows — the net of imported ACTIVITY, not the account's
    balance. Any partial import made it wrong (three imported rows produced
    −$3,918.88 for an account the bank showed at $4,989.14), and that number
    cascaded into net worth, the profile, and every report. The debt
    serializer already refused to report unanchored sums; this endpoint now
    follows the same honesty rules:
      balance_basis 'bank'     — anchored on the bank's own running balance
      balance_basis 'activity' — credits − debits, only when no bank balance
                                 exists; correct only for full-history imports
    """
    import traceback
    try:
        with db_session() as session:
            # Auto-heal accounts that were broken during data recovery —
            # accounts with is_active=False that HAVE transactions are
            # clearly real accounts that got their flag corrupted, not
            # intentionally archived accounts. Fix only those.
            broken = session.query(Account).filter(
                Account.is_active == False
            ).all()
            for a in broken:
                txn_count = session.query(Transaction).filter_by(account_id=a.id).count()
                if txn_count > 0:
                    a.is_active = True
            if any(a.is_active for a in broken):
                session.commit()

            accounts = session.query(Account).filter_by(is_active=True) \
                              .order_by(Account.sort_order, Account.name).all()
            result = []
            for a in accounts:
                try:
                    txns    = session.query(Transaction).filter_by(account_id=a.id).all()
                    credits = sum(t.amount for t in txns if t.type == 'credit')
                    debits  = sum(t.amount for t in txns if t.type == 'debit')
                    dates   = sorted(t.date for t in txns if t.date)

                    anchor, chain_ok = _resolve_bank_anchor(txns)
                    if anchor is not None:
                        balance       = round(anchor.running_balance, 2)
                        balance_basis = 'bank' if chain_ok else 'bank_unordered'
                        balance_as_of = anchor.date.isoformat() if anchor.date else None
                    else:
                        balance       = round(credits - debits, 2)
                        balance_basis = 'activity'
                        balance_as_of = None

                    result.append({
                        **_serialize_account(a, session),
                        'balance':           balance,
                        'balance_basis':     balance_basis,
                        'balance_as_of':     balance_as_of,
                        'activity_net':      round(credits - debits, 2),
                        'transaction_count': len(txns),
                        'last_date':         dates[-1].isoformat() if dates else None,
                        'total_credits':     round(credits, 2),
                        'total_debits':      round(debits, 2),
                    })
                except Exception as e:
                    # Surface per-account errors instead of silently dropping
                    result.append({
                        'id': a.id, 'name': a.name, 'error': str(e),
                        'balance': 0, 'transaction_count': 0,
                    })
            return ok(result)
    except Exception as e:
        return ok([], error=str(e), trace=traceback.format_exc()[:500])


@accounts_bp.route('/<int:account_id>/recalculate-balances', methods=['POST'])
def recalculate_running_balances(account_id):
    """
    Reconcile running balances from an anchor point.

    The anchor is a known balance at a known date — either:
      - "backward": the user enters today's balance and we work backward
      - "forward":  the user enters what the balance was on a historical date

    Body:
      {
        "anchor_balance": 4231.00,   -- known balance at the anchor date
        "anchor_date":    "2026-06-22",  -- date the anchor balance is valid
        "direction":      "backward" | "forward"
      }

    Algorithm:
      1. Sort all transactions by (date, id)
      2. Find the anchor row — the last transaction on or before anchor_date
      3. Walk FORWARD from anchor: balance_after = balance_before +/- amount
      4. Walk BACKWARD from anchor: balance_before = balance_after -/+ amount
      5. Store the anchor row's import_id so the Ledger can mark it

    Returns:
      { "updated": N, "anchor_txn_id": X, "final_balance": Y }
    """
    body           = request.get_json(silent=True) or {}
    anchor_balance = float(body.get('anchor_balance', 0.0))
    anchor_date_s  = body.get('anchor_date') or date.today().isoformat()
    direction      = body.get('direction', 'backward')  # 'backward' or 'forward'

    try:
        anchor_date = date.fromisoformat(anchor_date_s)
    except ValueError:
        return err('Invalid anchor_date — use YYYY-MM-DD format')

    with db_session() as session:
        txns = session.query(Transaction).filter_by(
            account_id=account_id
        ).order_by(Transaction.date, Transaction.id).all()

        if not txns:
            return ok({'updated': 0, 'anchor_txn_id': None, 'final_balance': anchor_balance})

        # ── Find the anchor index ───────────────────────────────────────
        # For backward mode: anchor is the last txn on or before today's
        # date — the most recent transaction whose balance we know.
        # For forward mode: anchor is the last txn on or before the
        # historical date the user supplies.
        anchor_idx = None
        for i, t in enumerate(txns):
            if t.date <= anchor_date:
                anchor_idx = i
            else:
                break
        if anchor_idx is None:
            anchor_idx = 0  # all txns are after anchor date; start from beginning

        # ── Walk forward from anchor ─────────────────────────────────────
        # The anchor row gets the anchor_balance as its balance AFTER the
        # transaction. Rows after it are calculated from that running total.
        running = anchor_balance
        for i in range(anchor_idx, len(txns)):
            txns[i].running_balance = round(running, 2)
            if i + 1 < len(txns):
                t = txns[i + 1]
                running = running + t.amount if t.type == 'credit' else running - t.amount

        # ── Walk backward from anchor ────────────────────────────────────
        # To find what the balance was BEFORE each prior transaction, we
        # invert the operation: if a debit reduced the balance by X, the
        # prior balance was current + X; if a credit added X, prior was
        # current − X.
        running = anchor_balance
        for i in range(anchor_idx - 1, -1, -1):
            t = txns[i]
            # running is the balance AFTER txns[i+1], i.e. AFTER this txn.
            # Invert to get balance AFTER this txn (which is before the next).
            next_t = txns[i + 1]
            running = running - next_t.amount if next_t.type == 'credit' else running + next_t.amount
            txns[i].running_balance = round(running, 2)

        # Mark the anchor transaction so the Ledger can show the reconciliation marker
        anchor_txn = txns[anchor_idx]
        anchor_txn_id = anchor_txn.id

        session.commit()

        # Direction-aware: forward ends at the newest row, backward at the
        # oldest — previously always reported txns[-1], wrong for backward.
        final = txns[-1].running_balance if direction == 'forward' else txns[0].running_balance
        return ok({
            'updated':       len(txns),
            'anchor_txn_id': anchor_txn_id,
            'final_balance': round(final or 0, 2),
        })


def _serialize_account(a: Account, session=None) -> dict:
    return {
        'id':              a.id,
        'name':            a.name,
        'type':            a.type,
        'institution':     a.institution or '',
        'currency':        a.currency or 'USD',
        'is_active':       a.is_active,
        'sort_order':      a.sort_order,
        # minimum_balance was added in d94 — use getattr with default 0.0
        # so existing DBs that haven't migrated yet don't crash here.
        'minimum_balance': getattr(a, 'minimum_balance', None) or 0.0,
        # Whether a bank website is set - never the address itself. The link
        # is launch configuration, read only by the /portal routes, so it can
        # never reach the snapshot, a model prompt or an export (F5).
        'has_portal':      bool(getattr(a, 'portal_url', None)),
    }


# ── Budget ────────────────────────────────────────────────────────────────────

budget_bp = Blueprint('budget', __name__)


def get_budget_variance_for_category(session, category_name: str, months: int = 6) -> dict:
    """
    Phase H2 Feature 2 (adaptive learning — budget variance). Real spending
    volatility for a budgeted category, from actual transactions over a
    trailing window — not the historian scaffold (nothing writes
    budget_variance_observed yet), a direct computation against real data,
    matching how Feature 1's category suggestion also reads real history
    directly rather than waiting on a historian writer that doesn't exist.
    """
    empty = {'category': category_name, 'budgeted': None, 'avg_actual': None,
              'volatility': None, 'classification': None, 'months_sampled': 0}
    item = session.query(BudgetItem).filter_by(category=category_name, is_active=True).first()
    if not item or not item.amount:
        return empty

    cutoff = date.today() - timedelta(days=30 * months)
    rows = session.query(
        func.strftime('%Y-%m', Transaction.date).label('month'),
        func.sum(Transaction.amount).label('total')
    ).join(Category, Transaction.category_id == Category.id).filter(
        Category.name == category_name, Transaction.type == 'debit', Transaction.date >= cutoff
    ).group_by('month').all()
    if not rows:
        return {**empty, 'budgeted': item.amount}

    actuals = [r[1] for r in rows]
    avg_actual = sum(actuals) / len(actuals)
    per_month_variance_pct = [abs(a - item.amount) / item.amount * 100 for a in actuals]
    volatility = sum(per_month_variance_pct) / len(per_month_variance_pct)
    classification = 'stable' if volatility < 10 else 'volatile' if volatility > 30 else 'moderate'

    return {
        'category': category_name, 'budgeted': item.amount, 'avg_actual': round(avg_actual, 2),
        'volatility': round(volatility, 1), 'classification': classification, 'months_sampled': len(actuals),
    }


def suggest_budget_adjustment(proposed_budget: float, volatility_pct) -> float:
    """Add a buffer to volatile categories, tighten stable ones. A no-op
    (returns proposed_budget unchanged) when volatility isn't known —
    never adjust based on a guess."""
    if volatility_pct is None:
        return proposed_budget
    if volatility_pct > 30:
        return round(proposed_budget * 1.15, 2)
    if volatility_pct < 10:
        return round(proposed_budget * 0.95, 2)
    return proposed_budget


@budget_bp.route('/variance', methods=['GET'])
def budget_variance():
    category = request.args.get('category', '')
    months = int(request.args.get('months', 6))
    with db_session() as session:
        variance = get_budget_variance_for_category(session, category, months)
        result = dict(variance)
        if variance['budgeted'] is not None:
            result['suggested_budget'] = suggest_budget_adjustment(variance['budgeted'], variance['volatility'])
        else:
            result['suggested_budget'] = None
        return ok(result)


@budget_bp.route('/pressure', methods=['GET'])
def budget_pressure_route():
    """What each overspent category costs, and where the money could come from.

    §8's teaching form for this surface. The cost is in months on the payoff
    date, which is the same currency the trip planner has priced a purchase in
    since Pillar 1 — the alternative is the same dollar meaning two different
    things on two screens.

    An empty list is an answer: nothing in the record runs over its own budget
    in every month it can speak about. So is `reason`, when there is no debt to
    price the time against.
    """
    from core.solution import budget_pressure

    with db_session() as session:
        cards, budget, strategy, undated = _consequence_inputs(session)
        if not cards:
            return ok({'pressure': [], 'base': None, 'undated_forgiveness': [],
                       'reason': 'no active debt to price the time against'})
        today = date.today().strftime('%Y-%m')
        result = {
            'base': simulate_payoff(cards, budget, strategy,
                                    today_key=today, start_month=today),
            'pressure': budget_pressure(
                cards, budget, categories=reallocation_candidates(session),
                strategy=strategy, today_key=today, start_month=today),
            'undated_forgiveness': undated,
        }
    return ok(result)


def _recurring_pattern_groups(session, months: int = 6, min_occurrences: int = 3, tolerance_pct: float = 5.0):
    """The patterns and the rows behind each: [(pattern, [(date, amount, category)])]. Item 108 R1: one payee from
    one account (core/recurring_groups.py), a card switch read as one charge (R4)."""
    from core import recurring_groups as rg
    cutoff = date.today() - timedelta(days=30 * months)
    rows = session.query(Transaction.merchant, Transaction.account_id, Transaction.date, Transaction.amount,
                         Category.name).outerjoin(Category, Transaction.category_id == Category.id).filter(
        Transaction.type == 'debit', Transaction.date >= cutoff, Transaction.merchant != ''
    ).order_by(Transaction.id).all()
    names = {a.id: a.name for a in session.query(Account).all()}

    existing_budgeted = {
        b[0] for b in session.query(BudgetItem.name).filter_by(is_active=True).all()
    }

    patterns = []
    for grp in rg.groups(rows, names):
        amounts = [a for _, a, _ in grp['rows']]
        if len(amounts) < min_occurrences or grp['payee'] in existing_budgeted:
            continue
        avg = sum(amounts) / len(amounts)
        if avg <= 0:
            continue
        max_deviation_pct = max(abs(a - avg) / avg * 100 for a in amounts)
        if max_deviation_pct <= tolerance_pct:
            patterns.append(({
                'merchant': grp['payee'], 'label': grp['label'], 'account': grp['account'],
                'avg_amount': round(avg, 2), 'frequency': len(amounts),
                'max_deviation_pct': round(max_deviation_pct, 1),
            }, grp['rows']))
    patterns.sort(key=lambda p: -p[0]['frequency'])
    return patterns


def detect_recurring_patterns(session, months: int = 6, min_occurrences: int = 3, tolerance_pct: float = 5.0) -> list:
    """
    Phase H2 Feature 4 (adaptive learning — recurring transaction
    auto-detection). Merchants with 3+ transactions of consistent amount
    (within tolerance_pct of their own average) over the trailing window —
    the "Netflix $15.99 every month" pattern. Skips merchants that already
    have an active budget item, since flagging something the user already
    budgets for isn't a suggestion, it's noise.

    Item 108: read per account. `merchant` is the payee (what a budget line and an answer match, R5); `label` names
    the account when the payee recurs from more than one (R3).
    """
    return [p for p, _ in _recurring_pattern_groups(session, months, min_occurrences, tolerance_pct)]


def reallocation_candidates(session, months: int = 6) -> list:
    """Lever 1's raw material (§6.1): what each budgeted category actually spent,
    month by month, and how many months the ledger can speak about.

    Two rules keep this honest, and the solution engine cannot enforce either of
    them because neither is visible from a single category.

    A month with no spending in a category is a real zero only if the ledger
    holds transactions from that month at all; otherwise it is a month with no
    data, and reading it as zero spend invents headroom out of a hole in the
    record — the same mistake that once read blank income months as a $7,053
    shortfall that was really a surplus.

    And a category the ledger has never seen is not a category spending nothing.
    An envelope paid in cash, or on a card nobody imports, looks identical to
    perfect thrift from in here, and the difference matters: one has headroom
    and the other has a recording gap. So a category earns its months from the
    months it actually appears in, and a category that appears in too few is not
    a candidate at all — the zero months only ever refine a maximum it already
    has.

    The current month is excluded outright: it is half-recorded by definition,
    and half a month of spending looks exactly like an underspend.
    """
    today = date.today()
    month_start = today.replace(day=1)
    cutoff = month_start - timedelta(days=30 * months)

    ledger_months = {
        r[0] for r in session.query(func.strftime('%Y-%m', Transaction.date)).filter(
            Transaction.type == 'debit',
            Transaction.date >= cutoff, Transaction.date < month_start
        ).distinct().all() if r[0]
    }
    if len(ledger_months) < MIN_MONTHS_OBSERVED:
        return []

    rows = session.query(
        Category.name,
        func.strftime('%Y-%m', Transaction.date).label('m'),
        func.sum(Transaction.amount)
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.type == 'debit',
        Transaction.date >= cutoff, Transaction.date < month_start
    ).group_by(Category.name, 'm').all()
    spend = {(r[0], r[1]): float(r[2] or 0) for r in rows}

    out = []
    for item in session.query(BudgetItem).filter_by(is_active=True, type='expense').all():
        if not item.category or not item.amount:
            continue
        seen = [m for m in ledger_months if (item.category, m) in spend]
        if len(seen) < MIN_MONTHS_OBSERVED:
            continue
        # The maximum runs over every month the ledger can speak about, the
        # quiet ones included: a month this category really did spend nothing
        # in is part of its record. The COUNT runs only over the months it was
        # actually seen, because that is what says the ledger can speak about
        # this category at all.
        monthly = [spend.get((item.category, m), 0.0) for m in ledger_months]
        out.append({
            'name': item.category,
            'budgeted': float(item.amount),
            'max_observed': max(monthly),
            # The floor of the same window, for the opposite question. Headroom
            # asks what the envelope never needed; overspend asks what it never
            # came in under. Both are the part of the record that held in EVERY
            # month the ledger can speak about, which is the only claim either
            # can make without extrapolating from a spike.
            'min_observed': min(monthly),
            'months_observed': len(seen),
        })
    # W-C: the user's word and their record's readings travel with each candidate, and a category the
    # user protected is not a candidate at all (WILLINGNESS_LAYER.md).
    from core.willingness import annotate
    return annotate(out, willingness_state(session)['effective'])


def trim_candidates(session, months: int = 6, limit: int = 12) -> list:
    """Lever 4's raw material (§6.1): recurring merchants, what each one costs
    per MONTH, and the category it sits in.

    Three rules keep this honest. The figure is the monthly cost, not the
    charge: `detect_recurring_patterns` calls a merchant recurring at three
    consistent charges inside the window, which a weekly $16 coffee satisfies
    too, and naming $16 for what is really a $69/mo line understates it
    fourfold. The span it divides by runs from the first charge to the last
    rather than across the whole window, so something that only started three
    months ago is not averaged down to look small. And an item nobody has paid
    in 45 days is not a saving — it is already gone, and offering it would be
    offering the user money they do not have.

    A merchant whose transactions carry no category comes back with `None`, and
    the solution engine treats an unknown category as protected.
    """
    today = date.today()
    out = []
    # Item 108 R6: each account's charge is its own candidate, at its own monthly cost
    for pattern, rows in _recurring_pattern_groups(session, months=months)[:limit]:
        if not rows:
            continue
        dates = [r[0] for r in rows if r[0]]
        if not dates:
            continue
        first, last = min(dates), max(dates)
        if (today - last).days > 45:
            continue
        span = (last.year - first.year) * 12 + (last.month - first.month) + 1
        if span < MIN_MONTHS_OBSERVED:
            continue
        names = [r[2] for r in rows if r[2]]
        out.append({
            'name': pattern['label'],
            'payee': pattern['merchant'],
            'monthly': round(sum(float(r[1] or 0) for r in rows) / span, 2),
            'category': max(set(names), key=names.count) if names else None,
        })
    # W-C: a recurring item in a category the user protected is not a candidate (WILLINGNESS_LAYER.md).
    from core.willingness import annotate
    return annotate(out, willingness_state(session)['effective'], field='category')

# ── The Willingness Layer (blueprint Appendix F; gw 2.0/WILLINGNESS_LAYER.md, ruled 2026-09-27) ─────────────
#
# THE READ BOUNDARY (W6). What the layer may read is the user's financial record and their own statements:
# budget items, the 'budget_adjusted' edits, transactions, categories, and willingness_declarations. It never
# reads usage - app opens and closes, page visits ('budget_reviewed'), or whether a suggestion was shown or
# dismissed ('proactive_shown' / 'proactive_dismissed'): a dismissal says "I dismissed this", not "I am
# unwilling to do this" (Rob, 2026-09-27). s129 pins this function's reads structurally.

def _willingness_inputs(session, months: int = 12) -> dict:
    """Gather what core.willingness reads - the record and the user's word, nothing else."""
    today = date.today()
    month_start = today.replace(day=1)
    cutoff = month_start - timedelta(days=30 * months)

    items = session.query(BudgetItem).all()
    by_id = {i.id: i for i in items}
    categories = sorted({i.category for i in items if i.is_active and i.type == 'expense' and i.category})

    # The user's own budget edits. The category is the item's category as it stands now: budget items key
    # category by name, and an edit made to "Dining" is about whatever that item is today.
    edits = []
    from core import plan_edits                         # item 80: a plan's Undo is not the person's decisions
    adj = session.query(HistorianEntry).filter(
        HistorianEntry.event_category == 'budget_adjusted').order_by(HistorianEntry.created_at, HistorianEntry.id).all()
    ctxs = {e.id: json.loads(e.context_json or '{}') for e in adj}
    undone = plan_edits.leave_out([(e.id, ctxs[e.id]) for e in adj])
    for e in adj:
        if e.id in undone:
            continue
        c = ctxs[e.id]
        item = by_id.get(c.get('budget_item_id'))
        if (not item or not item.category or c.get('item_type', 'expense') != 'expense'
                or e.expected_value is None or e.actual_value is None or e.created_at is None):
            continue
        edits.append({'id': e.id, 'date': e.created_at.strftime('%Y-%m-%d'), 'category': item.category,
                      'old': float(e.expected_value), 'new': float(e.actual_value)})

    # Spending by category and month, over complete months only - the current month is half-recorded by
    # definition. Transfers are money moving between the user's own accounts, not spending.
    rows = session.query(
        Category.name, Category.type, func.strftime('%Y-%m', Transaction.date), func.sum(Transaction.amount)
    ).outerjoin(Category, Transaction.category_id == Category.id).filter(
        Transaction.type == 'debit', Transaction.date >= cutoff, Transaction.date < month_start
    ).group_by(Category.name, Category.type, func.strftime('%Y-%m', Transaction.date)).all()
    spend, debits, ledger_months = {}, {}, set()
    for name, ctype, m, total in rows:
        if not m:
            continue
        ledger_months.add(m)
        if (ctype or '').lower() == 'transfer':
            continue
        debits[m] = debits.get(m, 0.0) + float(total or 0)
        if name:
            spend[(name, m)] = spend.get((name, m), 0.0) + float(total or 0)

    # Income by month - only months with income on record appear, so a month with none is unknown rather
    # than zero (absence is not zero).
    income = {}
    from core.income_def import income_category_ids    # item 71 amendment D1: one definition of income
    for m, total in session.query(
            func.strftime('%Y-%m', Transaction.date), func.sum(Transaction.amount)
    ).filter(
        Transaction.type == 'credit', Transaction.category_id.in_(income_category_ids(session)),
        Transaction.date >= cutoff, Transaction.date < month_start
    ).group_by(func.strftime('%Y-%m', Transaction.date)).all():
        if m and total and float(total) > 0:
            income[m] = float(total)

    declarations = [{'id': d.id, 'category': d.category, 'stance': d.stance, 'answer_kind': d.answer_kind,
                     'answer_text': d.answer_text or '', 'said_at': d.said_at.isoformat()}
                    for d in session.query(WillingnessDeclaration).order_by(
                        WillingnessDeclaration.said_at, WillingnessDeclaration.id)]
    return {'categories': categories, 'edits': edits, 'spend': spend, 'ledger_months': ledger_months,
            'income': income, 'debits': debits, 'declarations': declarations}


def willingness_state(session) -> dict:
    """The working picture's content, recomputed on every call - nothing derived is stored (ruling 2)."""
    from core.willingness import (observed_readings, current_declarations, effective, contradictions,
                                  shortfall_responses, strategy)
    from core.solution import is_protected
    i = _willingness_inputs(session)
    readings = observed_readings(i['categories'], i['edits'], i['spend'], i['ledger_months'],
                                 i['income'], i['debits'])
    current = current_declarations(i['declarations'])
    st = strategy(shortfall_responses(i['edits'], i['income'], i['debits']))
    aside = _strategy_set_aside(session)
    return {
        'readings': readings,
        'declarations': i['declarations'],
        'current': [{**d, 'on_floor': is_protected(d['category'])} for d in current.values()],
        'effective': effective(readings, i['declarations']),
        # W-D: asked, never applied
        'contradictions': contradictions(i['declarations'], i['edits'], i['spend'], i['ledger_months'], i['income']),
        # W-E: earned or unclassified; the user may set an earned label aside (their word, kept with when)
        'strategy': {**st, 'set_aside': aside},
    }


def _strategy_set_aside(session):
    """The user's word on the strategy label: {'said': iso} when they set it aside, else None."""
    row = _get_setting(session, 'willingness_strategy_aside')
    try:
        return json.loads(row.value) if row and row.value else None
    except (TypeError, ValueError):
        return None


def _demonstrated_lever(session):
    """E.3 rule 4's input: the earned W-E label, unless the user set it aside. None for most people."""
    try:
        st = willingness_state(session)['strategy']
    except Exception:
        return None
    return st['label'] if st['label'] != 'unclassified' and not st.get('set_aside') else None


willingness_bp = Blueprint('willingness', __name__)


@willingness_bp.route('', methods=['GET'])
def willingness_picture():
    """The working picture: what Groundwork has concluded, with receipts, and what the user has said."""
    with db_session() as session:
        s = willingness_state(session)
        s.pop('effective')
        return ok(s)


@willingness_bp.route('/declarations', methods=['POST'])
@require_json
def willingness_declare():
    """Record what the user said. Append-only: there is no route that edits or deletes a statement.

    F.3: a statement answers something Groundwork showed - a claim in the working picture (a reading, or
    the user's own earlier statement) or a path on a decision screen that names the category. There is no
    preference to set about something Groundwork has never claimed or offered.
    """
    from core.willingness import STANCES, claim_for
    body = request.json or {}
    category = (body.get('category') or '').strip()
    stance = (body.get('stance') or '').strip()
    answer = body.get('answer') if isinstance(body.get('answer'), dict) else {}
    kind = (answer.get('kind') or '').strip()
    said_to = (answer.get('text') or '').strip()[:500]
    if stance not in STANCES:
        return err('stance must be protect, flexible or release')
    if not category or len(category) > 80:
        return err('a category is required')
    with db_session() as session:
        state = willingness_state(session)
        current = {d['category'].strip().lower() for d in state['current']}
        if kind == 'claim':
            if not claim_for(category, state['readings'], state['declarations']):
                return err('Groundwork has not claimed anything about this category to answer', 409)
        elif kind == 'proposal':
            if stance == 'release':
                return err('a release answers an earlier statement, not a proposal')
            if category.lower() not in said_to.lower():
                return err('the proposal answered must name the category')
        else:
            return err('a statement answers a claim or a proposal')
        if stance == 'release' and category.lower() not in current:
            return err('there is no statement about this category to release', 409)
        session.add(WillingnessDeclaration(category=category, stance=stance, answer_kind=kind,
                                           answer_text=said_to))
        session.commit()
        s = willingness_state(session)
        s.pop('effective')
        return ok(s)


# ── Item 71 - when income drops (INCOME_CHANGE_SCENARIOS.md), on item 66's frame ─────────────────────────────
# Computed on every read (SC5): nothing derived is stored. What is kept is the person's own: their answer to "do you
# expect this to last?" (append-only, with when), their "not now" for the month, and what they applied (for Undo).
def _pay_kinds(session):
    """D10: the person's answer per payer - {payer: 'hourly'|'salary'} - from their own statements (latest wins)."""
    out = {}
    for s in _setting_json(session, 'pay_kinds', []) or []:
        if isinstance(s, dict) and s.get('payer') and s.get('kind') in ('hourly', 'salary'):
            out[s['payer']] = s['kind']
    return out


def _pay_state(session, today=None):
    """Item 71 amendment D1/D3-D10: every income deposit of the last ten months, judged per payer on its own
    checks. Calendar months stay only for the scenarios' monthly figures."""
    from core import income_change as ic
    from core.ask_why import payer_key
    from core.income_def import income_category_ids
    today = today or date.today()
    rows = session.query(Transaction).filter(
        Transaction.type == 'credit', Transaction.category_id.in_(income_category_ids(session)),
        Transaction.date >= today - timedelta(days=300)).all()
    ends = dict(session.query(Transaction.account_id, func.max(Transaction.date)).group_by(Transaction.account_id).all())
    deposits = [{'date': t.date, 'amount': t.amount or 0, 'payer': payer_key(t), 'account_id': t.account_id}
                for t in rows if (t.amount or 0) > 0 and payer_key(t)]
    return ic.detect_pay(deposits, _pay_kinds(session), ends, today)


def _income_change_state(session):
    from core import income_change as ic
    pay = _pay_state(session)
    change = pay['change']
    answers = _setting_json(session, 'income_change_answers', []) or []
    applied = _setting_json(session, 'income_change_applied')
    if not change:
        return {'change': None, 'applied': applied, 'payers': pay['payers']}
    answer = next((a['answer'] for a in reversed(answers) if a.get('since') == change['month']), None)
    month_amts = budget_month_amounts(session)
    items = session.query(BudgetItem).filter_by(is_active=True, type='expense').all()
    outflow = round(sum((month_amts.get(i.id) or {}).get('month_amount', i.amount or 0) or 0 for i in items), 2)
    lines = [{'id': i.id, 'name': i.name, 'category': i.category or i.name, 'amount': float(i.amount or 0)} for i in items]
    effective = willingness_state(session)['effective']
    cards, debt_budget, strategy, _undated = _consequence_inputs(session)
    cushion = _cash_above_floors(session)
    known = cushion is not None
    cushion = cushion or 0.0
    today = date.today().strftime('%Y-%m')
    # D11: payments set by a contract are never cut; one that may be waits for the person's answer
    from core.contracts import classify
    said = {}
    for x in _setting_json(session, 'contract_lines', []) or []:
        if isinstance(x, dict) and x.get('answer') in ('yes', 'no'):
            said[x.get('line_id')] = x['answer']
    debt_names = [d.name for d in session.query(DebtAccount).filter_by(is_active=True).all()]
    kinds = classify(lines, debt_names, said)
    sc = ic.scenarios(change, outflow, lines, effective, cards, debt_budget, round(cushion, 2) if known else None,
                      answer=answer, kw=dict(strategy=strategy, today_key=today, start_month=today), fixed=set(kinds))
    by_id = {ln['id']: ln for ln in lines}
    sc['contracts'] = [{'id': i, 'name': by_id[i]['name'], 'amount': by_id[i]['amount'], 'why': k['why']}
                       for i, k in kinds.items() if k['kind'] == 'contract']
    sc['contract_questions'] = [{'id': i, 'name': by_id[i]['name'], 'amount': by_id[i]['amount'], 'why': k['why']}
                                for i, k in kinds.items() if k['kind'] == 'ask']
    from core import household
    return {'change': change, 'answer': answer, 'outflow': outflow, 'goal': household.current(session, 'surplus_goal'),
            'snoozed': (_get_setting(session, 'income_change_snooze') or AppSetting(value='')).value == today,
            'applied': applied, 'payers': pay['payers'],
            # D9: the money first - what is left after the budgeted spending, before and now
            'left_before': round(change['from'] - outflow, 2), 'left_now': round(change['to'] - outflow, 2), **sc}


# ── Item 66 - possible futures (SCENARIOS.md SC1-SC7) ──────────────────────────────────────────────────────────
# Computed on every read (SC5). Kept: the person's possibilities (SC3, append-only, each with when), their answers to
# "Does this reflect your situation?" (SC4), and a path they chose (SC6). Nothing derived is stored.
futures_bp = Blueprint('futures', __name__)


def _cash_above_floors(session):
    """Cash in checking and savings above the person's own floors, or None when no balance is known."""
    cushion, known = 0.0, False
    for a in session.query(Account).filter_by(is_active=True).all():
        if (a.type or '').lower() not in ('checking', 'savings'):
            continue
        bal, _asof, _last, _tx = _account_balance_facts(session, a.id)
        if bal is None:
            continue
        floor = (_setting_json(session, f'bank_buffer:account:{a.id}') or {}).get('amount') or 0
        cushion += max(0.0, bal - floor)
        known = True
    return round(cushion, 2) if known else None


def _complete_months(today, n):
    first = today.replace(day=1)
    out, y, m = [], first.year, first.month
    for _ in range(n):
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
        out.append(f'{y}-{m:02d}')
    return list(reversed(out))


def _futures_inputs(session, today=None):
    from core import futures as fu
    from core.income_def import income_category_ids
    from core import household
    from core import gifts as gf
    from statistics import median
    today = today or date.today()
    months12 = _complete_months(today, 12)
    start = date(int(months12[0][:4]), int(months12[0][5:7]), 1)
    end = today.replace(day=1)
    # months with anything on record; a month with nothing is unknown, never zero (absence is not zero)
    ledger = {m for (m,) in session.query(func.strftime('%Y-%m', Transaction.date)).filter(
        Transaction.date >= start, Transaction.date < end).distinct().all()}
    inc_ids = income_category_ids(session)
    inc = dict(session.query(func.strftime('%Y-%m', Transaction.date), func.sum(Transaction.amount)).filter(
        Transaction.type == 'credit', Transaction.category_id.in_(inc_ids),
        Transaction.date >= start, Transaction.date < end).group_by(func.strftime('%Y-%m', Transaction.date)).all())
    inc_months = [m for m in months12[-6:] if m in ledger and (inc.get(m) or 0) > 0][-3:]
    income = round(median(float(inc[m]) for m in inc_months), 2) if len(inc_months) >= fu.MIN_INCOME_MONTHS else None
    spend_rows = session.query(Category.type, func.strftime('%Y-%m', Transaction.date), func.sum(Transaction.amount)) \
        .outerjoin(Category, Transaction.category_id == Category.id).filter(
        Transaction.type == 'debit', Transaction.date >= start, Transaction.date < end) \
        .group_by(Category.type, func.strftime('%Y-%m', Transaction.date)).all()
    spent = {}
    for ctype, m, total in spend_rows:
        if (ctype or '').lower() == 'transfer' or not m:
            continue
        spent[m] = spent.get(m, 0.0) + abs(float(total or 0))
    spend_record = [(m, round(spent.get(m, 0.0), 2)) for m in months12 if m in ledger]

    month_amts = budget_month_amounts(session)
    debt_names = {(d.name or '').strip().lower() for d in session.query(DebtAccount).filter_by(is_active=True).all()}
    spend, debt_lines = 0.0, 0.0
    for i in session.query(BudgetItem).filter_by(is_active=True, type='expense').all():
        amt = float((month_amts.get(i.id) or {}).get('month_amount', i.amount or 0) or 0)
        if (i.category or '').strip().lower() == 'debt' or (i.name or '').strip().lower() in debt_names \
                or (i.category or '').strip().lower() in debt_names:
            debt_lines += amt
        else:
            spend += amt
    cards, debt_budget, strategy, _undated = _consequence_inputs(session)
    known = []
    for o in gf.upcoming(session, today, days=fu.KNOWN_COST_DAYS):
        known.append({'label': o['label'], 'month': o['date'][:7], 'amount': o['budget'], 'source': 'gift'})
    return {
        'income': income, 'income_months': len(inc_months), 'spend': round(spend, 2),
        'debt_lines': round(debt_lines, 2), 'debt_pay': round(float(debt_budget or 0), 2) if cards else 0.0,
        'minimums': round(sum(c.minimum for c in cards), 2), 'owed': round(sum(c.balance for c in cards), 2),
        'cards': cards, 'strategy': strategy, 'cash': _cash_above_floors(session),
        'goal': household.current(session, 'surplus_goal') or 'unsure', 'start_month': today.strftime('%Y-%m'),
        'spend_record': spend_record, 'known_costs': known,
    }


def _pre_budget(session, inputs):
    """SC7: committed money, recurring charges and what is set aside, from the record - a starting point."""
    from core import futures as fu
    from core.contracts import classify
    rows = []
    if inputs['minimums']:
        rows.append({'label': 'Minimum debt payments', 'amount': inputs['minimums'], 'kind': 'observed',
                     'source': 'your debt accounts', 'group': 'committed'})
    said = {x.get('line_id'): x['answer'] for x in (_setting_json(session, 'contract_lines', []) or [])
            if isinstance(x, dict) and x.get('answer') in ('yes', 'no')}
    items = session.query(BudgetItem).filter_by(is_active=True, type='expense').all()
    lines = [{'id': i.id, 'name': i.name, 'category': i.category or i.name, 'amount': float(i.amount or 0)} for i in items]
    debt_names = [d.name for d in session.query(DebtAccount).filter_by(is_active=True).all()]
    by_id = {ln['id']: ln for ln in lines}
    for lid, k in classify(lines, debt_names, said).items():
        if k['kind'] == 'contract' and (by_id[lid]['category'] or '').strip().lower() != 'debt' \
                and by_id[lid]['name'] not in debt_names:
            rows.append({'label': by_id[lid]['name'], 'amount': round(by_id[lid]['amount'], 2), 'kind': 'observed',
                         'source': 'a payment set by a contract, in your budget', 'group': 'committed'})
    seen = {r['label'].strip().lower() for r in rows}
    for r in trim_candidates(session):
        if r['name'].strip().lower() in seen:
            continue
        rows.append({'label': r['name'], 'amount': r['monthly'], 'kind': 'observed',
                     'source': 'a recurring charge in your ledger' + (f" ({r['category']})" if r.get('category') else ''),
                     'group': 'recurring'})
    from core.database import SinkingFund
    for f in session.query(SinkingFund).filter_by(is_active=True).all():
        need = _serialize_sinking_fund(f)['monthly_needed']
        if need > 0:
            rows.append({'label': f.name, 'amount': round(need, 2), 'kind': 'projected',
                         'source': 'what this fund takes a month to reach its target by its date', 'group': 'set_aside'})
    return fu.pre_budget(inputs['income'], rows)


def _going_trip_possibilities(session):
    """Item 61 T8: each going trip, as a known cost in its departure month - the part paid from cash (checking,
    savings, funds), or the whole trip when no split is entered. Tagged as the person's own statement (SC3)."""
    from core import trips as tr
    from core.database import Trip
    out = []
    for t in session.query(Trip).filter_by(status='going').all():
        if not t.depart:
            continue
        parts = tr.cash_parts(t)
        amount = round(sum(parts.values()), 2) if tr.sources(t) else round(float(t.total or 0), 2)
        if amount > 0:
            out.append({'id': f'trip{t.id}', 'kind': 'cost', 'amount': amount, 'month': t.depart[:7],
                        'label': f'Trip to {t.label}', 'from_trip': t.id,
                        'said_at': (t.going_at or t.created_at).isoformat(timespec='seconds')})
    return out


def _futures_state(session):
    from core import futures as fu
    inputs = _futures_inputs(session)
    poss = ((_setting_json(session, 'future_possibilities', []) or []) + _going_trip_possibilities(session)
            + _first_import_possibilities(session))
    answers = _setting_json(session, 'future_answers', []) or []
    out = fu.build(inputs, poss, answers)
    out['fingerprint'] = fu.fingerprint(inputs, poss, answers)
    out['computed_at'] = datetime.now().isoformat(timespec='seconds')
    out['pre_budget'] = _pre_budget(session, inputs)
    out['choice'] = _setting_json(session, 'future_choice')
    out['debt_lines'] = inputs['debt_lines']
    # charts and figures only: the engine's Card objects stay server-side
    for s in out.get('scenarios', []):
        s.pop('cards', None)
    return out, inputs


@futures_bp.route('', methods=['GET'])
def futures_get():
    with db_session() as session:
        out, _ = _futures_state(session)
        return ok(out)


@futures_bp.route('/fingerprint', methods=['GET'])
def futures_fingerprint():
    """SC5: what the figures on screen were computed from; a different answer means they are stale."""
    from core import futures as fu
    with db_session() as session:
        inputs = _futures_inputs(session)
        poss = ((_setting_json(session, 'future_possibilities', []) or []) + _going_trip_possibilities(session)
                + _first_import_possibilities(session))
        return ok({'fingerprint': fu.fingerprint(inputs, poss, _setting_json(session, 'future_answers', []) or [])})


@futures_bp.route('/answer', methods=['POST'])
@require_json
def futures_answer():
    """SC4: the person's word on a scenario - yes / partly / unlikely (hides it) / explore / show (undoes unlikely)."""
    from core import futures as fu
    b = request.json or {}
    key, answer = str(b.get('key') or ''), b.get('answer')
    if not key or answer not in fu.ANSWERS:
        return err('A scenario and one of the answers are needed.')
    with db_session() as session:
        said = _setting_json(session, 'future_answers', []) or []
        said.append({'key': key, 'answer': answer, 'at': datetime.now().isoformat(timespec='seconds')})
        _set_setting(session, 'future_answers', json.dumps(said[-500:]))
        session.commit()
        return ok({'saved': True})


@futures_bp.route('/possibility', methods=['POST'])
@require_json
def futures_possibility():
    """SC3/SC4 "Partly": a possibility the person states. Kept as theirs - never a transaction, line or balance."""
    from core import futures as fu
    b = request.json or {}
    kind = b.get('kind')
    try:
        amount = round(float(b.get('amount')), 2)
    except (TypeError, ValueError):
        return err('Enter an amount.')
    month = (b.get('month') or '').strip()[:7]
    if kind not in fu.POSSIBILITY_KINDS or amount <= 0:
        return err('Enter what it is and an amount.')
    if month and not re.fullmatch(r'\d{4}-\d{2}', month):
        return err('Use a month like 2027-03.')
    if kind == 'cost' and not month:
        return err('A known cost needs its month.')
    with db_session() as session:
        said = _setting_json(session, 'future_possibilities', []) or []
        pid = f'p{len(said) + 1}-{int(datetime.now().timestamp())}'
        said.append({'id': pid, 'kind': kind, 'amount': amount, 'month': month or None,
                     'label': str(b.get('label') or '').strip()[:80], 'said_at': datetime.now().isoformat(timespec='seconds')})
        _set_setting(session, 'future_possibilities', json.dumps(said))
        session.commit()
        return ok({'id': pid})


@futures_bp.route('/possibility/<pid>/withdraw', methods=['POST'])
def futures_withdraw(pid):
    """The person takes a possibility back. Its history stays; the latest statement is the withdrawal."""
    from core import futures as fu
    with db_session() as session:
        said = _setting_json(session, 'future_possibilities', []) or []
        cur = next((p for p in fu.possibilities_in_force(said) if p['id'] == pid), None)
        if not cur:
            return err('Not found.', 404)
        said.append({**cur, 'withdrawn': True, 'said_at': datetime.now().isoformat(timespec='seconds')})
        _set_setting(session, 'future_possibilities', json.dumps(said))
        session.commit()
        return ok({'withdrawn': pid})


@futures_bp.route('/choose', methods=['POST'])
@require_json
def futures_choose():
    """SC6: a path is chosen only on the person's word. "What is left goes to the debt" can also set the monthly debt
    payment - on its own tap, with the old figure kept for Undo. Nothing else changes the plan."""
    b = request.json or {}
    key = str(b.get('key') or '')
    with db_session() as session:
        out, inputs = _futures_state(session)
        s = next((x for x in out.get('scenarios', []) if x['key'] == key), None)
        if not s:
            return err('That future is not shown now.', 404)
        choice = {'key': key, 'title': s['title'], 'at': datetime.now().isoformat(timespec='seconds')}
        if b.get('apply'):
            if key != 'surplus_to_goal' or not s.get('new_debt_pay'):
                return err('Only "What is left goes to the debt" changes a figure.')
            row = _get_setting(session, 'monthly_budget')
            choice['applied'] = {'setting': 'monthly_budget', 'before': row.value if row else None,
                                 'after': str(s['new_debt_pay'])}
            _set_setting(session, 'monthly_budget', str(s['new_debt_pay']))
        _set_setting(session, 'future_choice', json.dumps(choice))
        session.commit()
        return ok(choice)


# ── Item 65 W5 (AGENT_W_ITEMS.md): cause and effect you can move - several figures, one engine, nothing saved ────
@futures_bp.route('/what-if', methods=['POST'])
@require_json
def futures_what_if():
    """W5-a: the person's figures moved together, through the futures' own run() and the one payoff engine."""
    from core import futures as fu
    changes = (request.get_json() or {}).get('changes') or {}
    with db_session() as session:
        inputs = _futures_inputs(session)
        if inputs['income'] is None:
            return err(f'Groundwork needs at least {fu.MIN_INCOME_MONTHS} complete months of income on record for a what-if.', 409)
        poss = ((_setting_json(session, 'future_possibilities', []) or []) + _going_trip_possibilities(session)
                + _first_import_possibilities(session))
        return ok(fu.what_if(inputs, poss, changes))


def _savings_line(session):
    for b in session.query(BudgetItem).filter_by(is_active=True, type='expense').all():
        if (b.category or '').strip().lower() == 'savings' or (b.name or '').strip().lower() == 'savings':
            return b
    return None


def _what_if_plan(session, changes):
    """W5-b: exactly what "Make this my plan" would change, each with its before and after - and what it would not."""
    from core import futures as fu
    inputs = _futures_inputs(session)
    poss = ((_setting_json(session, 'future_possibilities', []) or []) + _going_trip_possibilities(session)
            + _first_import_possibilities(session))
    w = fu.what_if(inputs, poss, changes)
    items, notes = [], []
    for c in w['changed']:
        if c['key'] == 'debt_pay':
            row = _get_setting(session, 'monthly_budget')
            items.append({'key': 'debt_pay', 'what': 'Your monthly debt payment', 'before': row.value if row else None,
                          'after': c['to']})
        elif c['key'] == 'save':
            line = _savings_line(session)
            items.append({'key': 'save', 'what': f'Your budget line {line.name}' if line else 'A new budget line, Savings',
                          'line_id': line.id if line else None, 'before': round(line.amount or 0, 2) if line else None,
                          'after': round((line.amount or 0) + c['to'], 2) if line else c['to']})
        elif c['key'] == 'one_time':
            items.append({'key': 'one_time', 'what': f"A known cost in {c['month']}, kept as something you said",
                          'before': None, 'after': c['to'], 'month': c['month']})
        elif c['key'] == 'income':
            notes.append("Income isn't changed: Groundwork reads it from your deposits.")
        elif c['key'] == 'spend':
            notes.append(f"Spending isn't changed here: this what-if moved it to {c['to']:,.2f} a month in total, "
                         f"and your budget changes line by line on the Budget page.")
    return w, items, notes


@futures_bp.route('/what-if/plan', methods=['POST'])
@require_json
def futures_what_if_plan():
    """W5-b: "Make this my plan". Without apply it only says what would change; with apply it changes exactly that,
    keeps the before for Undo, and nothing else."""
    b = request.get_json() or {}
    with db_session() as session:
        if _futures_inputs(session)['income'] is None:
            return err('There is no what-if without income on record.', 409)
        w, items, notes = _what_if_plan(session, b.get('changes') or {})
        if not b.get('apply'):
            return ok({'changes': items, 'not_changed': notes})
        if not items:
            return err('Nothing here changes your plan.')
        now = datetime.now().isoformat(timespec='seconds')
        done = []
        for it in items:
            if it['key'] == 'debt_pay':
                _set_setting(session, 'monthly_budget', str(it['after']))
                done.append(it)
            elif it['key'] == 'save':
                if it['line_id']:
                    session.get(BudgetItem, it['line_id']).amount = it['after']
                    done.append(it)
                else:
                    line = BudgetItem(name='Savings', category='Savings', amount=it['after'], type='expense', is_active=True)
                    session.add(line); session.flush()
                    done.append({**it, 'line_id': line.id, 'created': True})
            elif it['key'] == 'one_time':
                said = _setting_json(session, 'future_possibilities', []) or []
                pid = f'p{len(said) + 1}-{int(datetime.now().timestamp())}'
                said.append({'id': pid, 'kind': 'cost', 'amount': it['after'], 'month': it['month'],
                             'label': 'A one-time cost (from a what-if)', 'said_at': now})
                _set_setting(session, 'future_possibilities', json.dumps(said))
                done.append({**it, 'possibility': pid})
        _set_setting(session, 'what_if_applied', json.dumps({'at': now, 'items': done}))
        session.commit()
        return ok({'applied': done, 'not_changed': notes})


@futures_bp.route('/what-if/undo', methods=['POST'])
def futures_what_if_undo():
    """W5-b: Undo puts back exactly what "Make this my plan" changed."""
    with db_session() as session:
        rec = _setting_json(session, 'what_if_applied')
        if not rec:
            return err('Nothing to undo.', 404)
        for it in rec.get('items', []):
            if it['key'] == 'debt_pay':
                if it.get('before') is None:
                    row = _get_setting(session, 'monthly_budget')
                    if row:
                        session.delete(row)
                else:
                    _set_setting(session, 'monthly_budget', it['before'])
            elif it['key'] == 'save' and it.get('line_id'):
                line = session.get(BudgetItem, it['line_id'])
                if line and it.get('created'):
                    session.delete(line)
                elif line:
                    line.amount = it['before']
            elif it['key'] == 'one_time' and it.get('possibility'):
                said = _setting_json(session, 'future_possibilities', []) or []
                cur = next((p for p in said if p.get('id') == it['possibility'] and not p.get('withdrawn')), None)
                if cur:
                    said.append({**cur, 'withdrawn': True, 'said_at': datetime.now().isoformat(timespec='seconds')})
                    _set_setting(session, 'future_possibilities', json.dumps(said))
        session.delete(_get_setting(session, 'what_if_applied'))
        session.commit()
        return ok({'undone': True})


@futures_bp.route('/choose/undo', methods=['POST'])
def futures_choose_undo():
    with db_session() as session:
        choice = _setting_json(session, 'future_choice')
        if not choice:
            return err('Nothing to undo.', 404)
        ap = choice.get('applied')
        if ap:
            if ap.get('before') is None:
                row = _get_setting(session, 'monthly_budget')
                if row:
                    session.delete(row)
            else:
                _set_setting(session, 'monthly_budget', ap['before'])
        row = _get_setting(session, 'future_choice')
        if row:
            session.delete(row)
        session.commit()
        return ok({'undone': True})


# ── Item 61 (TRIP_FUNDING_COACH.md T1-T9): a trip you commit to becomes part of the plan ──────────────────────
# Groundwork never moves or pays money (TM1) and never decides a trip is happening (TM5). The split and the payback
# choices are the person's statements; every figure is the record and the one payoff engine, computed on read.
trips_bp = Blueprint('trips', __name__)


def _trip_json(session, t, plan=False):
    from core import trips as tr
    tot, left = tr.assigned(t)
    d = {'id': t.id, 'label': t.label, 'depart': t.depart, 'ret': t.ret, 'total': round(float(t.total or 0), 2),
         'lines': tr.lines(t), 'status': t.status, 'sources': tr.sources(t), 'assigned': tot, 'left_to_assign': left,
         'rebuild_months': t.rebuild_months or 6, 'pay_order': t.pay_order or '', 'split_pct': t.split_pct,
         'fund_id': t.fund_id, 'actual_spent': t.actual_spent}
    if plan and t.status == 'going':
        d['plan'] = _trip_plan(session, t)
    return d


def _trip_plan(session, t):
    """T3-T6, computed on read: what each source leaves, the way back, the two orders, the coach line."""
    from core import trips as tr
    from core.database import SinkingFund
    from core.trip_card import plan as card_plan
    from core import household
    today = date.today()
    start = today.strftime('%Y-%m')
    cards, budget, strategy, _undated = _consequence_inputs(session)
    credit = {c['id']: c for c in _trip_credit_cards(session)}
    ids_by_name = {c['name']: c['id'] for c in credit.values()}
    matched = {}
    for b in session.query(TripBooking).filter(TripBooking.trip_label == t.label,
                                               TripBooking.paid_with_kind == 'card').all():
        if b.debt_account_id and (b.matched_debt_entry_id or b.matched_transaction_id):
            matched[b.debt_account_id] = matched.get(b.debt_account_id, 0.0) + float(b.charged_amount or b.amount or 0)
    shares = tr.card_shares(t, matched)
    cash = tr.cash_parts(t)
    cash_total = round(sum(cash.values()), 2)
    card_total = round(sum(s['projected'] for s in shares.values()), 2)
    # what each source leaves (T3)
    left = []
    for s in tr.sources(t):
        amt = float(s['amount'])
        row = {'kind': s['kind'], 'ref_id': s.get('ref_id'), 'amount': round(amt, 2)}
        if s['kind'] == 'card':
            c = credit.get(int(s.get('ref_id') or 0))
            row['name'] = c['name'] if c else 'A card no longer on record'
            row['available_after'] = None if not c or c.get('available') is None else round(c['available'] - amt, 2)
            if c:
                row['payoff'] = card_plan(amt, c, cards, budget, strategy, c['index'])['rows']
        elif s['kind'] in ('checking', 'savings'):
            a = session.get(Account, int(s.get('ref_id') or 0))
            row['name'] = a.name if a else 'An account no longer on record'
            bal = _account_balance_facts(session, a.id)[0] if a else None
            floor = ((_setting_json(session, f'bank_buffer:account:{a.id}') or {}).get('amount') if a else None)
            row['balance_after'] = None if bal is None else round(bal - amt, 2)
            row['floor'] = floor
            row['above_floor_after'] = None if bal is None or floor is None else round(bal - amt - float(floor), 2)
        elif s['kind'] in ('fund', 'save_ahead'):
            f = session.get(SinkingFund, int(s.get('ref_id') or 0)) if s.get('ref_id') else None
            row['name'] = f.name if f else ('A trip fund' if s['kind'] == 'save_ahead' else 'A fund no longer on record')
            if f:
                row['fund_after'] = round(float(f.current_amount or 0) - amt, 2) if s['kind'] == 'fund' else None
                row['target'] = round(float(f.target_amount or 0), 2)
        left.append(row)
    # the way back (T4)
    m = t.rebuild_months or 6
    rebuild = {k: {'amount': v, 'months': m, 'monthly': round(v / m, 2)} for k, v in cash.items() if v > 0}
    # one plan, two orders (T5)
    fi = _futures_inputs(session)
    surplus = round((fi['income'] or 0) - fi['spend'] - fi['debt_pay'], 2) if fi['income'] is not None else None
    cards_plus = tr._with_shares(cards, ids_by_name, shares)
    base_months = tr._months(cards, budget, strategy, start) if cards else None
    with_months = tr._months(cards_plus, budget, strategy, start) if cards else None
    ords = tr.orders(cards_plus, budget, strategy, start, surplus or 0, card_total, cash_total, t.split_pct) if surplus else {}
    for k, v in ords.items():
        v['debt_label'] = tr.month_label(start, v['debt_months'])
        v['rebuild_label'] = tr.month_label(start, v['rebuild_months']) if v['rebuild_months'] else None
    chosen = ords.get(t.pay_order) if t.pay_order else None
    goal = household.current(session, 'surplus_goal') or 'unsure'
    assumptions = [
        'Each card\'s share is added to that card in your one debt plan, as a projected charge, until the real charge is '
        'imported and linked to the booking; then the record carries it and the projection drops.',
        'The payback orders use what is left each month after your budget and debt payments'
        + (f' ({fmt_money(surplus)} a month).' if surplus is not None else '. Your record does not show enough income to know it.'),
        'Debt first: that money goes toward the debt until the trip\'s card amount has been paid in extra, then to '
        'rebuilding. Rebuild first: the other way round.',
    ]
    return {'left': left, 'card_total': card_total, 'cash_total': cash_total, 'shares': shares,
            'rebuild': rebuild, 'surplus': surplus, 'base_debt_months': base_months,
            'base_debt_label': tr.month_label(start, base_months), 'with_trip_debt_months': with_months,
            'with_trip_debt_label': tr.month_label(start, with_months), 'orders': ords,
            'coach': tr.coach_line(goal, base_months, chosen, start, cash_total) if chosen else None,
            'coach_both': None if chosen else [tr.coach_line(goal, base_months, ords[k], start, cash_total)
                                               for k in ('debt_first', 'rebuild_first') if k in ords],
            'goal': goal, 'assumptions': assumptions}


def fmt_money(x):
    return f'${x:,.0f}' if x >= 0 else f'-${-x:,.0f}'


@trips_bp.route('', methods=['GET'])
def trips_list():
    from core import trips as tr
    from core.database import Trip
    with db_session() as session:
        tr.carry_setting(session)
        session.commit()
        rows = session.query(Trip).filter(Trip.status != 'cancelled').order_by(Trip.depart, Trip.id).all()
        return ok({'trips': [_trip_json(session, t, plan=True) for t in rows]})


@trips_bp.route('', methods=['POST'])
@require_json
def trips_commit():
    """T1: "I'm going on this trip" - the planner's current trip, saved as going. Only this tap does it."""
    from core import trips as tr
    from core.database import Trip
    b = request.json or {}
    label = str(b.get('dest') or b.get('label') or '').strip()[:160]
    try:
        total = round(float(b.get('total')), 2)
    except (TypeError, ValueError):
        return err('The trip needs its total.')
    if not label or total <= 0:
        return err('The trip needs a destination and a total.')
    with db_session() as session:
        tr.carry_setting(session)
        t = Trip(label=label, depart=(b.get('depart') or '')[:10] or None, ret=(b.get('ret') or '')[:10] or None,
                 total=total, lines_json=json.dumps(tr.lines_from_budget(b)), status='going', going_at=datetime.now())
        session.add(t)
        session.commit()
        return ok(_trip_json(session, t, plan=True))


@trips_bp.route('/<int:tid>', methods=['PATCH'])
@require_json
def trips_edit(tid):
    """T3-T5: the person's split, rebuild months and payback order. Sources must name a source of theirs."""
    from core import trips as tr
    from core.database import SinkingFund, Trip
    b = request.json or {}
    with db_session() as session:
        t = session.get(Trip, tid)
        if not t:
            return err('Trip not found', 404)
        if 'status' in b:
            if b['status'] not in ('going', 'cancelled', 'planning'):
                return err('A trip can be going, planning or cancelled here; "done" comes after it, on a yes.')
            t.status = b['status']
            if b['status'] == 'going' and not t.going_at:
                t.going_at = datetime.now()
        if 'sources' in b:
            clean = []
            for s in b.get('sources') or []:
                kind = (s or {}).get('kind')
                try:
                    amt = round(float(s.get('amount')), 2)
                except (TypeError, ValueError):
                    return err('Each source needs an amount.')
                if kind not in tr.SOURCE_KINDS or amt <= 0:
                    return err('Each source needs what it is and an amount.')
                ref = s.get('ref_id')
                if kind == 'card' and not any(c['id'] == int(ref or 0) for c in _trip_credit_cards(session)):
                    return err('That card is not one of your credit cards.')
                if kind in ('checking', 'savings') and not session.get(Account, int(ref or 0)):
                    return err('That account was not found.')
                if kind == 'fund' and not session.get(SinkingFund, int(ref or 0)):
                    return err('That fund was not found.')
                clean.append({'kind': kind, 'ref_id': int(ref) if ref not in (None, '') else None, 'amount': amt})
            if round(sum(x['amount'] for x in clean), 2) > round(float(t.total or 0), 2) + 0.005:
                return err('The sources add up to more than the trip.')
            t.sources_json = json.dumps(clean)
            # T2: saving ahead makes (or resizes) the trip's own fund, which fills itself monthly until the trip
            ahead = round(sum(x['amount'] for x in clean if x['kind'] == 'save_ahead'), 2)
            if ahead > 0:
                f = session.get(SinkingFund, t.fund_id) if t.fund_id else None
                if f is None:
                    f = SinkingFund(name=f'Trip: {t.label}'[:120], target_amount=ahead, current_amount=0.0,
                                    deadline=t.depart, monthly_contribution=0.0, purpose=tr.TRIP_PURPOSE,
                                    note='Set aside ahead for this trip (item 61)')
                    session.add(f)
                    session.flush()
                    t.fund_id = f.id
                else:
                    f.target_amount = ahead
                    f.deadline = t.depart
                for x in clean:
                    if x['kind'] == 'save_ahead':
                        x['ref_id'] = t.fund_id
                t.sources_json = json.dumps(clean)
        if 'rebuild_months' in b:
            if int(b['rebuild_months']) not in tr.REBUILD_MONTHS:
                return err('Rebuild over 3, 6 or 12 months.')
            t.rebuild_months = int(b['rebuild_months'])
        if 'pay_order' in b:
            if b['pay_order'] not in ('', *tr.ORDERS):
                return err('Pick debt first, rebuild first, or a split.')
            t.pay_order = b['pay_order']
            if b['pay_order'] == 'split':
                try:
                    pct = float(b.get('split_pct'))
                except (TypeError, ValueError):
                    return err('A split needs the share that goes to debt.')
                if not 0 < pct < 100:
                    return err('A split needs the share that goes to debt.')
                t.split_pct = pct
        session.commit()
        return ok(_trip_json(session, t, plan=True))


@trips_bp.route('/sources-available', methods=['GET'])
def trips_sources_available():
    """T3: what a trip can be paid from - checking and savings accounts, savings funds, credit cards."""
    from core.database import SinkingFund
    with db_session() as session:
        accts = [{'id': a.id, 'name': a.name, 'type': (a.type or '').lower()} for a in
                 session.query(Account).filter_by(is_active=True).all() if (a.type or '').lower() in ('checking', 'savings')]
        funds = [{'id': f.id, 'name': f.name, 'current': round(float(f.current_amount or 0), 2)} for f in
                 session.query(SinkingFund).filter_by(is_active=True).all() if (f.purpose or '') != 'trip']
        return ok({'accounts': accts, 'funds': funds, 'cards': _trip_credit_cards(session)})


@trips_bp.route('/<int:tid>/charges', methods=['GET'])
def trips_after_charges(tid):
    """T7: after the trip, its bookings and the Travel charges in its dates - listed, not used."""
    from core import trips as tr
    from core.database import Trip
    with db_session() as session:
        t = session.get(Trip, tid)
        if not t:
            return err('Trip not found', 404)
        return ok(tr.after_charges(session, t, date.today()))


@trips_bp.route('/<int:tid>/charges', methods=['POST'])
@require_json
def trips_use_charges(tid):
    """T7, on the person's yes: the charges they picked are what the trip cost, and the trip is done."""
    from core import trips as tr
    from core.database import Trip
    with db_session() as session:
        t = session.get(Trip, tid)
        if not t:
            return err('Trip not found', 404)
        offered = {c['id']: c for c in tr.after_charges(session, t, date.today())['charges']}
        picked = [str(x) for x in (request.json.get('ids') or [])]
        if not picked or any(p not in offered for p in picked):
            return err('Pick charges from the list.')
        t.actual_spent = round(sum(offered[p]['amount'] for p in picked), 2)
        t.actual_txn_ids = ','.join(picked)
        t.status = 'done'
        t.done_at = datetime.now()
        log_historian_event(session, 'trip_actual', expected_value=round(float(t.total or 0), 2),
                            actual_value=t.actual_spent, context={'trip_id': t.id})
        session.commit()
        return ok(_trip_json(session, t))


@trips_bp.route('/in-month', methods=['GET'])
def trips_in_month():
    """T2: going trips that touch a month, for the Budget page - derived, never a budget line."""
    from core import trips as tr
    from core.database import Trip
    month = (request.args.get('month') or date.today().strftime('%Y-%m'))[:7]
    with db_session() as session:
        rows = [t for t in session.query(Trip).filter_by(status='going').all() if tr.in_month(t, month)]
        return ok({'month': month, 'trips': [_trip_json(session, t) for t in rows]})


# ── Item 65 W3 (AGENT_W_ITEMS.md): the one calendar of what's coming ──────────────────────────────────────────
# ── Item 65 W2 (AGENT_W_ITEMS.md): price changes on recurring charges ──────────────────────────────────────────
price_changes_bp = Blueprint('price_changes', __name__)


def _norm_payee(s):
    return ''.join(ch for ch in (s or '').lower() if ch.isalnum())


def _price_line(session, payee):
    """The budget line this payee's price lives on, by name: a budget item first, then a recurring bill. None when no
    line names it - then the change is shown as a fact only, with nothing to update."""
    n = _norm_payee(payee)
    if len(n) < 4:
        return None
    hit = lambda name: (lambda m: len(m) >= 4 and (m in n or n in m))(_norm_payee(name))
    for b in session.query(BudgetItem).filter_by(is_active=True, type='expense').all():
        if hit(b.name):
            return {'kind': 'budget', 'id': b.id, 'name': b.name, 'amount': round(b.amount or 0, 2)}
    for r in _setting_json(session, 'recurring_items_json', []) or []:
        if isinstance(r, dict) and hit(r.get('name')):
            return {'kind': 'recurring', 'id': r.get('id'), 'name': r.get('name'), 'amount': round(float(r.get('amount') or 0), 2)}
    return None


def _price_changes(session, today=None):
    """W2: every recurring charge whose price stepped in the last 13 months, from the ledger (core/price_change.py).
    Derived on every read - nothing about a finding is stored (no silent learning)."""
    from core import price_change as pc
    from core import recurring_groups as rg
    today = today or date.today()
    rows = session.query(Transaction.merchant, Transaction.account_id, Transaction.date, Transaction.amount,
                         Category.name).outerjoin(Category, Category.id == Transaction.category_id).filter(
        Transaction.type == 'debit', Transaction.merchant != '', Transaction.date >= today - timedelta(days=396),
        Transaction.date <= today).all()
    names = {a.id: a.name for a in session.query(Account).all()}
    out = []
    # item 108: a price steps on one account's charges; `payee` matches the budget line and the tap (R5), `label`
    # names the account when the payee recurs from more than one (R3)
    for grp in rg.groups(rows, names):
        m, xs = grp['payee'], [(d, a) for d, a, _ in grp['rows']]
        cat = {m: grp['rows'][-1][2] or ''}
        s = pc.step(xs, cat[m])
        if not s:
            continue
        after = sorted(d for d, _ in xs if d >= s['first_after'])
        line = _price_line(session, m)
        out.append({'payee': m, 'label': grp['label'], 'account': grp['account'], 'category': cat[m],
                    'before': s['before'], 'after': s['after'],
                    'last_before': s['last_before'].isoformat(), 'first_after': s['first_after'].isoformat(),
                    'seen_on': after[pc.MIN_AFTER - 1].isoformat(),   # the charge that made it a step (W2-a)
                    'after_count': s['after_count'], 'kind': s['kind'], 'sentence': pc.sentence(grp['label'], s),
                    'records': s['records'], 'line': line,
                    'line_matches': bool(line and abs(line['amount'] - s['after']) < 0.01)})
    out.sort(key=lambda x: x['seen_on'], reverse=True)
    return out


@price_changes_bp.route('', methods=['GET'])
def price_changes_get():
    with db_session() as session:
        return ok({'changes': _price_changes(session)})


def _set_line_amount(session, kind, line_id, amount):
    if kind == 'budget':
        b = session.get(BudgetItem, int(line_id))
        if not b:
            return None
        old, b.amount = round(b.amount or 0, 2), amount
        return old
    items = _setting_json(session, 'recurring_items_json', []) or []
    for r in items:
        if isinstance(r, dict) and str(r.get('id')) == str(line_id):
            old, r['amount'] = round(float(r.get('amount') or 0), 2), amount
            _set_setting(session, 'recurring_items_json', json.dumps(items))
            return old
    return None


@price_changes_bp.route('/apply', methods=['POST'])
@require_json
def price_changes_apply():
    """W2: the person's one tap - the budget line takes the new price. The amount is the record's, worked out again
    here, never the page's; the reply carries the old amount for Undo."""
    payee = (request.get_json() or {}).get('payee')
    label = (request.get_json() or {}).get('label') or payee          # item 108: which account's change, by its label
    with db_session() as session:
        f = next((x for x in _price_changes(session) if x['payee'] == payee and x['label'] == label), None)
        if not f or not f['line']:
            return err('No price change with a budget line was found for that payee.', 404)
        old = _set_line_amount(session, f['line']['kind'], f['line']['id'], f['after'])
        if old is None:
            return err('That budget line is gone.', 404)
        session.commit()
        return ok({'line': f['line']['name'], 'kind': f['line']['kind'], 'id': f['line']['id'], 'from': old, 'to': f['after']})


@price_changes_bp.route('/undo', methods=['POST'])
@require_json
def price_changes_undo():
    b = request.get_json() or {}
    try:
        amount = round(float(b.get('amount')), 2)
    except (TypeError, ValueError):
        return err('An amount is needed.', 400)
    if amount < 0 or b.get('kind') not in ('budget', 'recurring'):
        return err('That is not a line Groundwork changed.', 400)
    with db_session() as session:
        if _set_line_amount(session, b['kind'], b.get('id'), amount) is None:
            return err('That budget line is gone.', 404)
        session.commit()
        return ok({'restored': amount})


# ── Item 107 (SAME_CHARGE_TWO_ACCOUNTS.md): the same charge paid from two accounts in the same month ─────────────
two_accounts_bp = Blueprint('two_accounts', __name__)


def _two_accounts(session, today=None):
    """D1-D5 on the record, and what each pair shows now under D8. Derived on every read."""
    from core import two_accounts as ta
    today = today or date.today()
    cats = {c.id: c for c in session.query(Category).all()}
    accounts = {a.id: a.name for a in session.query(Account).all()}
    since = date(today.year, today.month, 1) - timedelta(days=31 * (ta.WINDOW - 1) + 1)
    rows = session.query(Transaction).filter(Transaction.type == 'debit', Transaction.date >= since,
                                             Transaction.date <= today).all()
    said = _setting_json(session, ta.SETTING, []) or []
    found = ta.pairs(rows, accounts, ta.payment_category_ids(cats), today)
    return found, said, accounts


@two_accounts_bp.route('', methods=['GET'])
def two_accounts_get():
    """D6 (a): Needs attention's items; D6 (b)'s single months stay in Ask why. D8: what the person said, for Settings."""
    from core import two_accounts as ta
    with db_session() as session:
        found, said, accounts = _two_accounts(session)
        today = date.today()
        out = [ta.item(p, st, said, accounts) for p in found for st in [ta.state(p, said, today)] if st]
        return ok({'attention': out, 'said': ta.listed(said)})


@two_accounts_bp.route('/answer', methods=['POST'])
@require_json
def two_accounts_answer():
    """D8: the person's answer, appended as their statement. It changes nothing else (D9)."""
    from core import two_accounts as ta
    b = request.get_json() or {}
    answer = b.get('answer')
    if answer not in ta.ANSWERS:
        return err('That is not one of the answers.', 400)
    with db_session() as session:
        found, said, _ = _two_accounts(session)
        p = next((x for x in found if x['key'] == b.get('pair')), None)
        st = p and ta.state(p, said, date.today())
        if not st:
            return err('Groundwork is not asking about that pair now.', 404)
        said = ta.append(said, p, answer, again=(st == 'again'))
        _set_setting(session, ta.SETTING, json.dumps(said))
        log_historian_event(session, 'two_accounts_answered',
                            context={'payee_key': p['canon'], 'accounts': p['accounts'], 'answer': answer,
                                     'again': st == 'again'})
        session.commit()
        return ok({'said': said[-1]})


@two_accounts_bp.route('/undo', methods=['POST'])
@require_json
def two_accounts_undo():
    """D8: Undo adds a withdrawal of one statement; it removes nothing."""
    from core import two_accounts as ta
    n = (request.get_json() or {}).get('n')
    with db_session() as session:
        said = _setting_json(session, ta.SETTING, []) or []
        out = ta.withdraw(said, n) if isinstance(n, int) else None
        if out is None:
            return err('There is no such answer to undo.', 404)
        gone = next(s for s in said if s.get('n') == n)
        _set_setting(session, ta.SETTING, json.dumps(out))
        log_historian_event(session, 'two_accounts_answered',
                            context={'payee_key': gone['key'].split('|')[0], 'accounts': gone.get('accounts'),
                                     'answer': 'withdrawn', 'withdraws': gone.get('answer')})
        session.commit()
        return ok({'withdrawn': n})


# ── Item 106 (YEARLY_PRICE_STEPS.md): a bill that steps at the same time each year - said, projected, asked ───────
yearly_steps_bp = Blueprint('yearly_steps', __name__)
# Y5: usage bills item 26 already estimates from EIA's regional price - a yearly rate step is in that figure already,
# so a household step on top would count it twice (section 7). The rest are asked about (Y5(c)).
_ITEM26_USAGE = {'electric', 'electricity', 'natural gas', 'propane', 'heating oil'}


def _yearly_answers(session):
    return _setting_json(session, 'yearly_step_answers', {}) or {}


def _yearly_steps(session, today=None):
    """Item 106: every payee's yearly price steps, from the whole ledger and the household's answers (Y1-Y8).
    Derived on every read; only the answers and the person's taps are stored."""
    from core import yearly_steps as ys
    from core import recurring_groups as rg
    from core.price_change import USAGE_CATEGORIES
    today = today or date.today()
    rows = session.query(Transaction.merchant, Transaction.account_id, Transaction.date, Transaction.amount,
                         Category.name).outerjoin(Category, Category.id == Transaction.category_id).filter(
        Transaction.type == 'debit', Transaction.merchant != '', Transaction.date <= today).all()
    names = {a.id: a.name for a in session.query(Account).all()}
    answers = _yearly_answers(session)
    follow = set(_setting_json(session, 'yearly_step_follow', []) or [])
    out = []
    # item 108: one payee from one account; the household's answers and the budget line are the payee's (R5), the
    # words name the account when the payee recurs from more than one (R3)
    for grp in rg.groups(rows, names):
        m, label, xs = grp['payee'], grp['label'], [(d, a) for d, a, _ in grp['rows']]
        cat = {m: grp['rows'][-1][2] or ''}
        c = cat[m].strip().lower()
        mine = answers.get(m, [])
        answered = [a['month'] for a in mine]
        line = None
        if c in USAGE_CATEGORIES:
            if c in _ITEM26_USAGE:
                continue
            steps = ys.apply_answers([], mine)                           # Y5(c): only the household's word
            pat = ys.pattern(steps)
            sm = ys.same_month(xs, today)
            q = None
            if sm and (today.year * 12 + today.month) - (int(sm['month'][:4]) * 12 + int(sm['month'][5:7])) <= 1 \
                    and abs(sm['pct']) >= ys.FLOOR and not any(
                    abs((int(sm['month'][:4]) * 12 + int(sm['month'][5:7])) - (int(a[:4]) * 12 + int(a[5:7]))) <= 11
                    for a in answered):
                way = 'higher' if sm['pct'] > 0 else 'lower'
                mon = date(int(sm['month'][:4]), int(sm['month'][5:7]), 1).strftime('%B')
                q = {'kind': 'rate', 'month': sm['month'],
                     'text': f"Your {mon} bill from {label} was {abs(sm['pct']) * 100:.1f}% {way} than last {mon}'s "
                             f"(${sm['this']:,.2f} against ${sm['last_year']:,.2f}). A usage bill follows what is used "
                             f"as well as the rate. Did your rate change?"}
            if not pat and not q:
                continue
            line = _price_line(session, m)
            level = line['amount'] if line else None
            proj = ys.projection(pat, level, today) if pat else None
            out.append({'payee': m, 'label': label, 'account': grp['account'], 'category': cat[m], 'kind': 'usage',
                        'sentence': ys.sentence(label, pat),
                        'steps': (pat or {}).get('steps', []), 'pattern': bool(pat and pat['pattern']),
                        'projection': proj, 'question': q, 'line': line,
                        'followed': bool(line and line['kind'] == 'budget' and line['id'] in follow and proj)})
            continue
        info = ys.read(xs, cat[m])
        if not info:
            continue
        steps = ys.apply_answers(info['steps'], mine)
        pat = ys.pattern(steps)
        if not pat:
            continue
        q = ys.question(info, pat, today, answered)
        if q:
            q = {'kind': 'price', **q, 'text': f"Is your {label} bill now ${q['amount']:,.2f}?"}
        line = _price_line(session, m)
        proj = ys.projection(pat, info['level'], today)
        out.append({'payee': m, 'label': label, 'account': grp['account'], 'category': cat[m], 'kind': info['kind'],
                    'sentence': ys.sentence(label, pat),
                    'steps': pat['steps'], 'pattern': pat['pattern'], 'level': info['level'],
                    'projection': proj, 'question': q, 'line': line,
                    'followed': bool(line and line['kind'] == 'budget' and line['id'] in follow and proj)})
    out.sort(key=lambda x: (not x['question'], not x['projection'], x['label'].lower()))
    return out


def _yearly_follow_amounts(session, today=None):
    """Y6: {budget item id: projection} for rows the household follows, from the expected month on. A row not
    followed keeps its saved amount (M1); nothing is read when nothing is followed."""
    if not (_setting_json(session, 'yearly_step_follow', []) or []):
        return {}
    this_month = (today or date.today()).strftime('%Y-%m')
    return {x['line']['id']: {**x['projection'], 'payee': x['payee']} for x in _yearly_steps(session, today)
            if x['followed'] and x['projection']['month'] <= this_month}


@yearly_steps_bp.route('', methods=['GET'])
def yearly_steps_get():
    with db_session() as session:
        return ok({'items': _yearly_steps(session)})


@yearly_steps_bp.route('/answer', methods=['POST'])
@require_json
def yearly_steps_answer():
    """Y7: the household's answer - the only write, besides the line it changes (shown first, with Undo). Every
    figure but the person's own is worked out again here, never taken from the page."""
    b = request.get_json() or {}
    payee, answer = b.get('payee'), b.get('answer')
    if answer not in ('yes', 'amount', 'rate', 'no_change', 'not_sure'):
        return err('That is not an answer Groundwork asks for.', 400)
    with db_session() as session:
        label = b.get('label') or payee                              # item 108: which account's question
        x = next((i for i in _yearly_steps(session) if i['payee'] == payee and i['label'] == label and i['question']), None)
        if not x:
            return err('There is no question open for that payee.', 404)
        q = x['question']
        rec = {'month': q['month'], 'answer': answer, 'at': datetime.now().isoformat(timespec='seconds')}
        new_amount = None
        if q['kind'] == 'price':
            if answer not in ('yes', 'amount', 'not_sure'):
                return err('That answer is for a usage bill.', 400)
            rec['before'] = q['before']
            if answer == 'yes':
                rec['amount'] = new_amount = q['amount']
            elif answer == 'amount':
                try:
                    rec['amount'] = new_amount = round(float(b.get('amount')), 2)
                except (TypeError, ValueError):
                    return err('An amount is needed.', 400)
                if new_amount <= 0:
                    return err('An amount is needed.', 400)
        else:
            if answer not in ('rate', 'no_change', 'not_sure'):
                return err('That answer is for a fixed price.', 400)
            if answer == 'rate':
                try:
                    pct = float(b.get('pct')) / 100.0
                except (TypeError, ValueError):
                    return err('The change, as a percent, is needed.', 400)
                if not -0.5 < pct < 1.0 or pct == 0:
                    return err('That percent is outside what a rate change would be.', 400)
                rec['pct'] = pct
                if x['line']:
                    new_amount = round(x['line']['amount'] * (1 + pct), 2)
        answers = _yearly_answers(session)
        answers.setdefault(payee, []).append(rec)
        _set_setting(session, 'yearly_step_answers', json.dumps(answers))
        change = None
        if new_amount is not None and x['line'] and abs(new_amount - x['line']['amount']) >= 0.01:
            old = _set_line_amount(session, x['line']['kind'], x['line']['id'], new_amount)
            if old is not None:
                change = {'line': x['line']['name'], 'kind': x['line']['kind'], 'id': x['line']['id'],
                          'from': old, 'to': new_amount}
        session.commit()
        return ok({'recorded': rec, 'change': change})


@yearly_steps_bp.route('/undo', methods=['POST'])
@require_json
def yearly_steps_undo():
    """Undo an answer: the answer is removed and the line, if it changed, goes back."""
    b = request.get_json() or {}
    payee, month = b.get('payee'), b.get('month')
    with db_session() as session:
        answers = _yearly_answers(session)
        mine = answers.get(payee, [])
        keep = [a for a in mine if a.get('month') != month]
        if len(keep) == len(mine):
            return err('There is no answer for that month to undo.', 404)
        answers[payee] = keep
        _set_setting(session, 'yearly_step_answers', json.dumps(answers))
        ch = b.get('change')
        if isinstance(ch, dict) and ch.get('kind') in ('budget', 'recurring'):
            try:
                amount = round(float(ch.get('from')), 2)
            except (TypeError, ValueError):
                amount = None
            if amount is not None and amount >= 0:
                _set_line_amount(session, ch['kind'], ch.get('id'), amount)
        session.commit()
        return ok({'undone': month})


@yearly_steps_bp.route('/follow', methods=['POST'])
@require_json
def yearly_steps_follow():
    """Y6: the household chooses whether a budget row's totals follow its yearly projection (M1); the saved amount
    is never changed by following."""
    b = request.get_json() or {}
    try:
        item_id = int(b.get('item_id'))
    except (TypeError, ValueError):
        return err('A budget row is needed.', 400)
    with db_session() as session:
        if not session.get(BudgetItem, item_id):
            return err('That budget row is gone.', 404)
        follow = [i for i in (_setting_json(session, 'yearly_step_follow', []) or []) if i != item_id]
        if b.get('on'):
            follow.append(item_id)
        _set_setting(session, 'yearly_step_follow', json.dumps(follow))
        session.commit()
        return ok({'following': follow})


# ── Item 65 W1 (AGENT_W_ITEMS.md): patterns a long history shows - asked about, never assumed ────────────────────
first_import_bp = Blueprint('first_import', __name__)
_MONTH_NAMES = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
                'November', 'December')


def _first_import_findings(session):
    """W1: yearly / twice-yearly bills and months that run heavy every year, from the whole ledger
    (core/first_import.py). Derived on every read; the person's answers are the only thing kept (W1-b), and an
    answered finding is not asked about again."""
    from core import checkin as ck
    from statistics import median
    from core import first_import as fi
    from core import recurring_groups as rg
    rows = session.query(Transaction.merchant, Transaction.date, Transaction.amount, Transaction.category_id,
                         Category.name, Transaction.account_id).outerjoin(
        Category, Category.id == Transaction.category_id).filter(Transaction.type == 'debit').all()
    dates = [r[1] for r in rows if r[1]]
    months = fi.complete_months(dates)
    if len(months) < fi.MIN_MONTHS:
        return {'enough': False, 'months': len(months),
                'message': f'Groundwork needs about a year of history to see yearly bills. Your record covers '
                           f'{len(months)} full month{"s" if len(months) != 1 else ""} so far.'}
    said_b = [e for e in _setting_json(session, 'yearly_bills_json', []) or [] if isinstance(e, dict)]
    said_h = [e for e in _setting_json(session, 'heavy_months_json', []) or [] if isinstance(e, dict)]
    # item 108: a renewal is one payee from one account, named by its label; the answer is the payee's (R5)
    names = {a.id: a.name for a in session.query(Account).all()}
    by, cat, of = {}, {}, {}
    for grp in rg.groups([(m, acct, d, a, c) for m, d, a, _, c, acct in rows], names):
        by[grp['label']] = [(d, a) for d, a, _ in grp['rows']]
        cat[grp['label']] = grp['rows'][-1][2] or ''
        of[grp['label']] = grp
    answered = {_norm_payee(e.get('payee')): e.get('answer') for e in said_b}
    ren = []
    for f in fi.renewals(by, cat, (min(dates), max(dates))):
        f['sentence'] = fi.sentence(f)
        grp = of[f['payee']]
        f['label'], f['payee'], f['account'] = f['payee'], grp['payee'], grp['account']
        f['answer'] = answered.get(_norm_payee(f['payee']))
        ren.append(f)
    # heavy months: spending by complete month (transfers are not spending), and each category's usual month
    tr = ck._transfer_ids(session)
    keep = set(months)
    totals, cats = {k: 0.0 for k in months}, {}
    for _, d, a, cid, c, _acct in rows:
        k = d.strftime('%Y-%m') if d else None
        if k in keep and cid not in tr:
            totals[k] += abs(float(a or 0))
            cats.setdefault(k, {}).setdefault(c or 'Uncategorized', 0.0)
            cats[k][c or 'Uncategorized'] += abs(float(a or 0))
    names = {c for v in cats.values() for c in v}
    usual = {c: median([cats.get(k, {}).get(c, 0.0) for k in months]) for c in names}
    h_answered = {int(e.get('month') or 0): e.get('answer') for e in said_h}
    heavy = []
    for h in fi.heavy_months(totals):
        latest = h['years'][-1]['month']
        mo = lambda k: f"{_MONTH_NAMES[int(k[5:7]) - 1][:3]} {k[:4]}"
        h['name'] = _MONTH_NAMES[h['month'] - 1]
        h['sentence'] = (f"{h['name']} ran above your usual month in each of the last {len(h['years'])} years: "
                         + '; '.join(f"${y['total']:,.0f} in {mo(y['month'])}, against a middle month of ${y['median']:,.0f}"
                                     for y in h['years']) + '.')
        h['categories'] = [{'category': c, 'amount': v, 'usual': u}
                           for c, v, u in fi.biggest_categories(cats.get(latest, {}), usual)]
        h['answer'] = h_answered.get(h['month'])
        heavy.append(h)
    return {'enough': True, 'months': len(months), 'renewals': ren, 'heavy': heavy,
            'heavy_note': None if len(months) >= 24 else
            'Seeing a month that runs high every year takes two full years of history.'}


@first_import_bp.route('', methods=['GET'])
def first_import_get():
    with db_session() as session:
        return ok(_first_import_findings(session))


@first_import_bp.route('/offer', methods=['GET'])
def first_import_offer():
    """W1: after an import, offer the look-through once for this length of history - when there is something unasked."""
    with db_session() as session:
        f = _first_import_findings(session)
        fresh = f['enough'] and any(x['answer'] is None for x in f['renewals'] + f['heavy'])
        offered = _setting_json(session, 'first_import_offered', 0) or 0
        return ok({'offer': bool(fresh and f['months'] != offered), 'months': f['months']})


@first_import_bp.route('/offered', methods=['POST'])
def first_import_offered():
    with db_session() as session:
        _set_setting(session, 'first_import_offered', json.dumps(_first_import_findings(session)['months']))
        session.commit()
        return ok({'saved': True})


@first_import_bp.route('/answer', methods=['POST'])
@require_json
def first_import_answer():
    """W1-b: the person's answer - yes / no / not sure - kept so the same finding isn't asked again. Only a yes changes
    anything: a yearly bill reaches the calendar (possible) and the futures (a known cost); a heavy month the futures.
    The finding is worked out again here, never taken from the page."""
    b = request.get_json() or {}
    answer = b.get('answer')
    if answer not in ('yes', 'no', 'not_sure'):
        return err('Answer yes, no or not sure.')
    now = datetime.now().isoformat(timespec='seconds')
    with db_session() as session:
        f = _first_import_findings(session)
        if not f['enough']:
            return err('There is not enough history yet.', 409)
        if b.get('kind') == 'renewal':
            hit = next((x for x in f['renewals'] if x['payee'] == b.get('payee')), None)
            if not hit:
                return err('That finding is not in the record.', 404)
            said = [e for e in _setting_json(session, 'yearly_bills_json', []) or []
                    if isinstance(e, dict) and _norm_payee(e.get('payee')) != _norm_payee(hit['payee'])]
            # item 108 R5 (a): the answer is the payee's - kept for each account's renewal of it, so a yes puts every
            # one in its own months on the calendar; the stored shape is unchanged
            for x in f['renewals']:
                if _norm_payee(x['payee']) == _norm_payee(hit['payee']):
                    said.append({'payee': x['payee'], 'amount': x['amount'], 'months': x['months'], 'day': x['day'],
                                 'rhythm': x['rhythm'], 'answer': answer, 'at': now})
            _set_setting(session, 'yearly_bills_json', json.dumps(said))
        elif b.get('kind') == 'heavy':
            hit = next((x for x in f['heavy'] if x['month'] == b.get('month')), None)
            if not hit:
                return err('That finding is not in the record.', 404)
            said = [e for e in _setting_json(session, 'heavy_months_json', []) or []
                    if isinstance(e, dict) and int(e.get('month') or 0) != hit['month']]
            said.append({'month': hit['month'], 'over': hit['over'], 'answer': answer, 'at': now})
            _set_setting(session, 'heavy_months_json', json.dumps(said))
        else:
            return err('A finding is needed.')
        session.commit()
        return ok({'saved': answer})


def _first_import_possibilities(session):
    """W1: a yes, as a known cost in the futures (SCENARIOS.md SC3, the person's own word) - each yearly bill in its
    next date(s) - the calendar's own dates, so a bill already charged this month is next year's - and each heavy
    month at its usual excess, the next time that month starts. The futures count what falls in their horizon."""
    from core import upcoming
    today = date.today()
    ahead = [(today.year + (today.month + i) // 12, (today.month + i) % 12 + 1) for i in range(12)]   # from next month
    out = []
    for e in _setting_json(session, 'yearly_bills_json', []) or []:
        if isinstance(e, dict) and e.get('answer') == 'yes' and (e.get('amount') or 0) > 0:
            for d in upcoming._yearly_dates(e, today + timedelta(days=1), today + timedelta(days=365)):
                y, m = d.year, d.month
                out.append({'id': f"yb-{_norm_payee(e.get('payee'))}-{y}{m:02d}", 'kind': 'cost',
                            'amount': round(float(e['amount']), 2), 'month': f'{y}-{m:02d}',
                            'label': f"{e.get('payee')} (a yearly bill you confirmed)", 'said_at': e.get('at')})
    for e in _setting_json(session, 'heavy_months_json', []) or []:
        if isinstance(e, dict) and e.get('answer') == 'yes' and (e.get('over') or 0) > 0:
            y, m = next(((y, m) for y, m in ahead if m == int(e.get('month') or 0)), (None, None))
            if y:
                out.append({'id': f'hm-{y}{m:02d}', 'kind': 'cost', 'amount': round(float(e['over']), 2),
                            'month': f'{y}-{m:02d}', 'label': f'{_MONTH_NAMES[m - 1]} usually runs this much above your usual month',
                            'said_at': e.get('at')})
    return out


# ── Item 65 W9 (AGENT_W_ITEMS.md): the year-end packet - the year's figures in one place, never tax advice ──────
year_end_bp = Blueprint('year_end', __name__)
YEAR_END_STATEMENT = "These are the year's figures from your records. Your tax preparer decides how they are treated."
YEAR_END_NOT_INCLUDED = (
    'Anything not in your records: cash paid by hand and never entered, accounts never imported, and paper receipts.',
    'Tax forms. Groundwork does not have your W-2s, 1099s, 1098s or brokerage statements unless you gave them to it, '
    'and these figures are not a substitute for them.',
    'Whether anything is deductible, taxable or reportable. Groundwork does not decide how any figure is treated.',
    'Investment gains on lots Groundwork has no cost basis for, and anything sold in an account it does not track.',
    'Interest that was never charged as its own line (for example, mortgage interest inside a payment).',
)


def _year_end(session, year, include_health=False):
    """W9: one year from the record. W9-a facts only; W9-b health only on its tick (H6 P3); W9-c a month or an
    account with nothing imported is listed as missing, never counted as zero."""
    from core import checkin as ck
    from core import health_boundary
    from core.database import Account, Artefact, InvestmentLot
    from core.income_def import income_category_ids
    y0, y1 = date(year, 1, 1), date(year, 12, 31)
    today = date.today()
    last_month = 12 if year < today.year else (today.month - 1 if year == today.year else 0)
    txns = session.query(Transaction).filter(Transaction.date >= y0, Transaction.date <= y1).all()
    cats = {c.id: c for c in session.query(Category).all()}
    cname = lambda t: (cats[t.category_id].name if t.category_id in cats else 'Uncategorized')
    tr, inc_ids = ck._transfer_ids(session), set(income_category_ids(session))
    is_health = health_boundary.health_rows(session)       # by category, or an HSA / FSA account's row (item 86 F6)
    health_left_out = 0 if include_health else sum(1 for t in txns if is_health(t))
    if not include_health:
        txns = [t for t in txns if not is_health(t)]
    income, spend, interest, donations = {}, {}, {}, {}
    for t in txns:
        amt = abs(float(t.amount or 0))
        if t.category_id in tr:
            continue
        if t.type == 'credit' and t.category_id in inc_ids:
            k = (t.merchant or t.description or 'Unnamed').strip()
            income.setdefault(k, [0.0, 0])
            income[k][0] += amt; income[k][1] += 1
        elif t.type == 'debit':
            n = cname(t)
            spend[n] = spend.get(n, 0.0) + amt
            low = n.strip().lower()
            if 'interest' in low or low in ('fees', 'interest / fees'):    # the person's own categories for them
                k = (t.merchant or t.description or n).strip()
                interest[k] = interest.get(k, 0.0) + amt
            if 'charit' in low or low in ('donations', 'gifts & donations'):
                k = (t.merchant or t.description or n).strip()
                donations[k] = donations.get(k, 0.0) + amt
    rows = lambda d: [{'name': k, 'total': round(v, 2)} for k, v in sorted(d.items(), key=lambda x: -x[1])]
    lots = [l for l in session.query(InvestmentLot).filter_by(is_closed=True).all() if l.closed_date and l.closed_date.year == year]
    st = round(sum(l.realized_gain or 0 for l in lots if (l.holding_period_days or 0) < 366), 2)
    lt = round(sum(l.realized_gain or 0 for l in lots if (l.holding_period_days or 0) >= 366), 2)
    docs = [{'id': a.id, 'as_of': a.as_of} for a in session.query(Artefact).filter(Artefact.held.is_(True)).all()
            if (a.as_of or '').startswith(str(year))]
    # W9-c: every month and every account the record should speak for
    months = [f'{year}-{m:02d}' for m in range(1, last_month + 1)]
    all_rows = session.query(Transaction.account_id, Transaction.date).filter(Transaction.date >= y0, Transaction.date <= y1).all()
    seen_any = {d.strftime('%Y-%m') for _, d in all_rows if d}
    by_acct = {}
    for a, d in all_rows:
        if d:
            by_acct.setdefault(a, set()).add(d.strftime('%Y-%m'))
    accts = {a.id: a for a in session.query(Account).all()}
    missing_months = [m for m in months if m not in seen_any]
    gaps = []
    for aid, a in accts.items():
        had = by_acct.get(aid, set())
        if not had:
            if a.is_active:
                gaps.append({'account': a.name, 'months': months, 'note': f'nothing imported for {year}'})
            continue
        first = min(had)
        miss = [m for m in months if m >= first and m not in had]
        if miss:
            gaps.append({'account': a.name, 'months': miss, 'note': f"{len(miss)} month{'s' if len(miss) != 1 else ''} with nothing imported"})
    return {'year': year, 'statement': YEAR_END_STATEMENT, 'months_covered': months,
            'income': [{'payer': k, 'total': round(v[0], 2), 'deposits': v[1]} for k, v in sorted(income.items(), key=lambda x: -x[1][0])],
            'income_total': round(sum(v[0] for v in income.values()), 2),
            'categories': rows(spend), 'spending_total': round(sum(spend.values()), 2),
            'interest': rows(interest), 'interest_total': round(sum(interest.values()), 2),
            'donations': rows(donations), 'donations_total': round(sum(donations.values()), 2),
            'gains': {'short_term': st, 'long_term': lt, 'total': round(st + lt, 2), 'lots': len(lots)},
            'documents': docs, 'include_health': bool(include_health), 'health_left_out': health_left_out,
            'missing_months': missing_months, 'account_gaps': gaps, 'not_included': list(YEAR_END_NOT_INCLUDED),
            'complete': not missing_months and not gaps,
            # Item 91 Y1: the Schedule A section, on the health tick only (H6 P3)
            'health_schedule_a': (__import__('core.health_documents', fromlist=['schedule_a'])
                                  .schedule_a(session, year, complete=not missing_months and not gaps)
                                  if include_health else None)}


def _year_end_args():
    b = request.get_json(silent=True) or {}
    src = {**request.args.to_dict(), **b}
    try:
        year = int(src.get('year') or date.today().year - 1)
    except (TypeError, ValueError):
        year = date.today().year - 1
    return year, str(src.get('include_health', '')).lower() in ('1', 'true', 'yes')


@year_end_bp.route('', methods=['GET'])
def year_end_get():
    year, inc = _year_end_args()
    with db_session() as session:
        years = sorted({d.year for (d,) in session.query(Transaction.date).distinct().all() if d}, reverse=True)
        return ok({**_year_end(session, year, inc), 'years': years})


@year_end_bp.route('/agi', methods=['POST'])
@require_json
def year_end_agi():
    """Item 91 Y4: {year, value} - the person's own AGI for a year, kept with its date; blank withdraws it."""
    from core import health_documents as hd
    body = request.json or {}
    with db_session() as session:
        problem = hd.set_agi(session, body.get('year'), body.get('value'))
        if problem:
            return err(problem)
        session.commit()
        return ok({'year': int(body.get('year')), 'agi': hd.agi(session, int(body.get('year')))})


@year_end_bp.route('/export', methods=['POST'])
def year_end_export():
    """W9: the packet as a CSV in the exports folder - on this computer, health only on its tick (H6 P3)."""
    import csv
    import io
    year, inc = _year_end_args()
    with db_session() as session:
        p = _year_end(session, year, inc)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([f'Groundwork year-end packet, {year}'])
    w.writerow([p['statement']])
    if p['health_left_out']:
        w.writerow([f"{p['health_left_out']} health spending transaction(s) left out; tick \"Include health spending\" to include them"])
    for title, key, cols in (('INCOME BY PAYER', 'income', ('payer', 'total', 'deposits')),
                             ('SPENDING BY CATEGORY', 'categories', ('name', 'total')),
                             ('INTEREST AND FEES (your categories for them)', 'interest', ('name', 'total')),
                             ('CHARITABLE DONATIONS', 'donations', ('name', 'total'))):
        w.writerow([]); w.writerow([f'--- {title} ---']); w.writerow(cols)
        for r in p[key]:
            w.writerow([r[c] for c in cols])
    g = p['gains']
    w.writerow([]); w.writerow(['--- REALIZED INVESTMENT GAINS AND LOSSES ---'])
    w.writerow(['short_term', 'long_term', 'total', 'lots']); w.writerow([g['short_term'], g['long_term'], g['total'], g['lots']])
    w.writerow([]); w.writerow(['--- DOCUMENTS GROUNDWORK HOLDS FOR THE YEAR ---'])
    for d in p['documents']:
        w.writerow([d['id'], d['as_of']])
    if not p['documents']:
        w.writerow(['none'])
    w.writerow([]); w.writerow(['--- MISSING FROM THE RECORD (not counted as zero) ---'])
    for m in p['missing_months']:
        w.writerow(['no records at all', m])
    for gp in p['account_gaps']:
        w.writerow([gp['account'], gp['note'], ' '.join(gp['months'])])
    sa = p.get('health_schedule_a')
    if sa:                                  # item 91 Y1: on the health tick only
        w.writerow([]); w.writerow(['--- HEALTH CARE, FOR SCHEDULE A ---'])
        for ln in sa['lines'] + [sa['statement']]:
            w.writerow([ln])
        w.writerow(['date', 'payee', 'category', 'account', 'amount'])
        for r in sa['counted']:
            w.writerow([r['date'], r['name'], r['category'], r['account'], r['amount']])
        for r in sa['refunds']:
            w.writerow([r['date'], r['name'], r['category'], r['account'], -r['amount']])
        for grp in sa['set_aside']:
            w.writerow([]); w.writerow(['SET ASIDE: ' + grp['reason']])
            for r in grp['rows']:
                w.writerow([r['date'], r['name'], r['category'], r['account'], r['amount']])
        if sa['hsa_8889']:
            w.writerow([]); w.writerow(['HSA (Form 8889 detail): ' + sa['hsa_8889']['note']])
            for ln in sa['hsa_8889']['contributions']:
                w.writerow([ln])
            w.writerow(['payments out of the HSA', sa['hsa_8889']['distributions'] if sa['hsa_8889']['distributions'] is not None
                        else f'not known - nothing imported into it for {year}'])
    w.writerow([]); w.writerow(['--- WHAT THIS DOES NOT INCLUDE ---'])
    for n in p['not_included']:
        w.writerow([n])
    dest = _exports_dir() / f"groundwork_year_end_{year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    dest.write_text(out.getvalue(), encoding='utf-8')
    return ok({'path': str(dest), 'health_left_out': p['health_left_out']})


# ── The dashboard projection's levers (found in the AI-off audit, 2026-10-12; fixed 2026-10-13) ────────────────
NOT_SPENDING_WORDS = ('transfer', 'savings', 'interest', 'fees', 'refund', 'atm', 'income', 'paycheck', 'salary')


def not_levers(names, income_names=()):
    """The categories never offered as spending to cut: the necessity floor (`is_protected`, the one list), payments
    set by a contract (a loan, lease, debt or insurance payment - `contracts.CONTRACT_WORDS`), and money that is not
    spending at all (transfers, savings, interest and fees, refunds, cash withdrawals, income)."""
    from core.contracts import CONTRACT_WORDS
    from core.care_status import never_lever
    out = set()
    for n in names:
        low = (n or '').strip().lower()
        if not low:
            continue
        words = set(low.replace('/', ' ').replace('&', ' ').split())
        if (never_lever(n) or CONTRACT_WORDS.search(n) or words & set(NOT_SPENDING_WORDS)     # item 89: + uncertain
                or low in {x.strip().lower() for x in income_names}):
            out.add(n)
    return sorted(out)


@budget_bp.route('/not-levers', methods=['GET'])
def budget_not_levers():
    """For the dashboard projection: which of the person's categories may never be proposed as the one to cut."""
    from core.income_def import income_category_ids
    with db_session() as session:
        cats = session.query(Category).all()
        inc = income_category_ids(session)
        names = {c.name for c in cats} | {b.category for b in session.query(BudgetItem).all() if b.category} | \
                {b.name for b in session.query(BudgetItem).filter_by(type='expense').all() if b.name}
        income_names = [c.name for c in cats if c.id in inc or (c.type or '') in ('income', 'transfer')]
        return ok({'not_levers': not_levers(names, income_names)})


# ── Item 83 (RECORD_TIDY.md): the agent keeps the record tidy - it proposes, the person decides, Undo for each ─────
tidy_bp = Blueprint('tidy', __name__)


def _tidy_inputs(session):
    cats = session.query(Category).all()
    used = dict(session.query(Transaction.category_id, func.count(Transaction.id)).group_by(Transaction.category_id).all())
    lines = [{'id': b.id, 'name': b.name, 'amount': round(b.amount or 0, 2), 'category': b.category}
             for b in session.query(BudgetItem).filter_by(is_active=True).all()]
    rules = _setting_json(session, 'import_rules_json', []) or []
    ruled = {(r.get('category') or '').strip().lower() for r in rules if isinstance(r, dict)}
    budgeted = {(b['category'] or '').strip().lower() for b in lines} | {(b['name'] or '').strip().lower() for b in lines}
    plain = [{'id': c.id, 'name': c.name, 'parent_id': c.parent_id, 'is_system': bool(c.is_system),
              'is_enabled': c.is_enabled is not False, 'type': c.type or 'expense'} for c in cats]
    return plain, used, lines, budgeted, ruled


def _tidy_state(session):
    """T1-T4: what the agent proposes now, less what the person already answered. Derived on every read."""
    from core import record_tidy as rt
    cats, used, lines, budgeted, ruled = _tidy_inputs(session)
    said = _setting_json(session, 'tidy_answers_json', {}) or {}
    tw = [t for t in rt.twins(cats, used, lines) if f"twin:{t['source']['name']}" not in said]
    twin_ids = {t['source']['id'] for t in tw}
    hide = [h for h in rt.hideable(cats, used, budgeted, ruled) if h['id'] not in twin_ids and f"hide:{h['name']}" not in said]
    tr = _transfer_category_ids(session)
    rows = session.query(Transaction.merchant, Category.name, Transaction.amount, Transaction.date).join(
        Category, Category.id == Transaction.category_id).filter(Transaction.type == 'debit', Transaction.merchant != '').all()
    sp = [s for s in rt.splits([(m, c, a, d.isoformat() if d else '') for m, c, a, d in rows]) if f"split:{s['merchant']}" not in said]
    unmatched = [u for u in (_setting_json(session, 'import_unmatched_json', []) or []) if not u.get('answer')]
    # a hidden category that now holds transactions (the importer files into it by name) is offered back
    back = [{'id': c['id'], 'name': c['name'], 'transactions': used[c['id']]} for c in cats
            if not c['is_enabled'] and used.get(c['id'], 0)]
    return {'hide': hide, 'twins': tw, 'splits': sp[:25], 'unmatched': unmatched, 'show_again': back,
            'counts': {'hide': len(hide), 'twins': len(tw), 'splits': len(sp), 'unmatched': len(unmatched), 'show_again': len(back)},
            'undo': bool(_setting_json(session, 'tidy_last')), 'transfer_ids': sorted(tr)}


def _transfer_category_ids(session):
    from core import checkin as ck
    return ck._transfer_ids(session)


def _tidy_said(session, key, answer):
    said = _setting_json(session, 'tidy_answers_json', {}) or {}
    said[key] = {'answer': answer, 'at': datetime.now().isoformat(timespec='seconds')}
    _set_setting(session, 'tidy_answers_json', json.dumps(said))


@tidy_bp.route('', methods=['GET'])
def tidy_get():
    with db_session() as session:
        return ok(_tidy_state(session))


@tidy_bp.route('/hide', methods=['POST'])
@require_json
def tidy_hide():
    """T1, on the tap: the listed empty categories leave every picker. Hidden, never deleted; Undo shows them again."""
    ids = [int(i) for i in (request.get_json() or {}).get('ids') or []]
    with db_session() as session:
        ok_ids = {h['id'] for h in _tidy_state(session)['hide']}
        done = []
        for cid in ids:
            c = session.get(Category, cid)
            if c and cid in ok_ids:                     # re-checked here: still empty, still unused
                c.is_enabled = False
                done.append({'id': c.id, 'name': c.name})
        _set_setting(session, 'tidy_last', json.dumps({'kind': 'hide', 'ids': [d['id'] for d in done]}))
        session.commit()
        return ok({'hidden': done})


@tidy_bp.route('/show', methods=['POST'])
@require_json
def tidy_show():
    """A hidden category that holds transactions again, shown in the pickers again on the tap."""
    cid = int((request.get_json() or {}).get('id') or 0)
    with db_session() as session:
        if cid not in {b['id'] for b in _tidy_state(session)['show_again']}:
            return err('That category is not hidden with transactions.', 404)
        session.get(Category, cid).is_enabled = True
        session.commit()
        return ok({'shown': cid})


@tidy_bp.route('/twin', methods=['POST'])
@require_json
def tidy_twin():
    """T2, on the tap: the empty twin merges into the used one. A budget line it held is added into the target's line
    (Rob 2026-10-13), so the total budget never changes. Everything needed to undo it is kept."""
    b = request.get_json() or {}
    with db_session() as session:
        t = next((x for x in _tidy_state(session)['twins'] if x['source']['id'] == int(b.get('source_id') or 0)), None)
        if not t:
            return err('That pair is not proposed now.', 404)
        if b.get('answer') == 'no':
            _tidy_said(session, f"twin:{t['source']['name']}", 'no')
            session.commit()
            return ok({'kept': t['source']['name']})
        src = session.get(Category, t['source']['id'])
        undo = {'kind': 'twin', 'category': {'name': src.name, 'type': src.type, 'color': src.color, 'icon': src.icon,
                                             'parent_id': src.parent_id, 'sort_order': src.sort_order}}
        if t['line']:
            line = session.get(BudgetItem, t['line']['id'])
            undo['line'] = {'name': line.name, 'amount': line.amount, 'type': line.type, 'category': line.category}
            if t['target_line']:
                tl = session.get(BudgetItem, t['target_line']['id'])
                undo['target_line'] = {'id': tl.id, 'amount': tl.amount}
                # folding a duplicate line into its twin is not a decision about the category, so it writes no
                # budget_adjusted entry for the Willingness Layer to read (as W2's and W5's taps write none)
                tl.amount = round((tl.amount or 0) + (line.amount or 0), 2)
                session.delete(line)
            else:
                line.category = t['target']['name']
                undo['line_moved'] = line.id
        session.delete(src)
        _set_setting(session, 'tidy_last', json.dumps(undo))
        session.commit()
        return ok({'merged': t['source']['name'], 'into': t['target']['name']})


@tidy_bp.route('/split', methods=['POST'])
@require_json
def tidy_split():
    """T3, the person's answer about a merchant in several categories: keep them as they are (not asked again), or
    all of them belong in one - moved, and an import rule so new ones land there too. Undo puts each back."""
    b = request.get_json() or {}
    merchant, answer = b.get('merchant'), b.get('answer')
    with db_session() as session:
        s = next((x for x in _tidy_state(session)['splits'] if x['merchant'] == merchant), None)
        if not s:
            return err('That merchant is not asked about now.', 404)
        if answer == 'keep':
            _tidy_said(session, f'split:{merchant}', 'keep')
            session.commit()
            return ok({'kept': merchant})
        target = session.query(Category).filter(func.lower(Category.name) == str(b.get('category') or '').lower()).first()
        if answer != 'move' or not target or target.name not in [c['name'] for c in s['categories']]:
            return err('Choose one of the categories it is already in.')
        moved = []
        for t in session.query(Transaction).filter(Transaction.merchant == merchant, Transaction.type == 'debit',
                                                   Transaction.category_id != target.id).all():
            moved.append([t.id, t.category_id])
            t.category_id = target.id
        rules = _setting_json(session, 'import_rules_json', []) or []
        rule = {'id': int(datetime.now().timestamp() * 1000), 'type': 'contains', 'value': merchant,
                'category': target.name, 'direction': 'debit', 'source': 'record_tidy'}
        rules.append(rule)
        _set_setting(session, 'import_rules_json', json.dumps(rules))
        _tidy_said(session, f'split:{merchant}', f'move:{target.name}')
        _set_setting(session, 'tidy_last', json.dumps({'kind': 'split', 'merchant': merchant, 'moved': moved, 'rule_id': rule['id']}))
        session.commit()
        return ok({'moved': len(moved), 'into': target.name, 'rule': rule})


@tidy_bp.route('/unmatched', methods=['POST'])
@require_json
def tidy_unmatched():
    """T4, the person's answer for an imported category name that matched none of theirs: its transactions move from
    Other to the category they choose, and the name is remembered for the next import. Or it is left as it is."""
    b = request.get_json() or {}
    with db_session() as session:
        items = _setting_json(session, 'import_unmatched_json', []) or []
        u = next((x for x in items if x.get('name') == b.get('name') and not x.get('answer')), None)
        if not u:
            return err('That imported name is not asked about now.', 404)
        if b.get('answer') == 'leave':
            u['answer'] = 'leave'
            _set_setting(session, 'import_unmatched_json', json.dumps(items))
            session.commit()
            return ok({'left': u['name']})
        target = session.query(Category).filter(func.lower(Category.name) == str(b.get('category') or '').lower()).first()
        if not target:
            return err('Choose one of your categories.')
        other = session.query(Category).filter(func.lower(Category.name) == 'other').first()
        moved = []
        for t in session.query(Transaction).filter(Transaction.id.in_(u.get('ids') or [])).all():
            if other is None or t.category_id == other.id:          # only rows still where the import left them
                moved.append([t.id, t.category_id])
                t.category_id = target.id
        aliases = _setting_json(session, 'category_aliases_json', {}) or {}
        aliases[u['name'].strip().lower()] = target.name
        _set_setting(session, 'category_aliases_json', json.dumps(aliases))
        u['answer'] = target.name
        _set_setting(session, 'import_unmatched_json', json.dumps(items))
        _set_setting(session, 'tidy_last', json.dumps({'kind': 'unmatched', 'name': u['name'], 'moved': moved}))
        session.commit()
        return ok({'moved': len(moved), 'into': target.name})


@tidy_bp.route('/new-vendors', methods=['GET'])
def new_vendors_get():
    """Item 98: the new vendors the bank's own label filed, waiting to be asked about (the Ledger shows the first)."""
    from core import new_vendor as nv
    with db_session() as session:
        return ok({'waiting': nv.waiting(session, nv.load(session))})


@tidy_bp.route('/new-vendors/answer', methods=['POST'])
@require_json
def new_vendors_answer():
    """Item 98 N5: {key, answer: 'yes' | 'no'}. Recorded, so the vendor is never asked about again. Nothing about the
    transaction changes here: Yes opens it for the person to change; No leaves it."""
    from core import new_vendor as nv
    b = request.get_json() or {}
    if b.get('answer') not in ('yes', 'no'):
        return err("Answer 'yes' or 'no'.")
    with db_session() as session:
        items = nv.load(session)
        e = next((x for x in items if x.get('key') == b.get('key') and not x.get('answer')), None)
        if not e:
            return err('That vendor is not asked about now.', 404)
        e['answer'] = b['answer']
        e['answered_at'] = datetime.now().isoformat(timespec='seconds')
        _set_setting(session, nv.SETTING, json.dumps(items))
        session.commit()
        return ok({'key': e['key'], 'answer': e['answer']})


@tidy_bp.route('/undo', methods=['POST'])
def tidy_undo():
    """Undo puts back exactly what the last tidy tap changed."""
    with db_session() as session:
        last = _setting_json(session, 'tidy_last')
        if not last:
            return err('Nothing to undo.', 404)
        k = last.get('kind')
        if k == 'hide':
            for cid in last.get('ids', []):
                c = session.get(Category, cid)
                if c:
                    c.is_enabled = True
        elif k == 'twin':
            meta = last['category']
            c = Category(name=meta['name'], type=meta.get('type'), color=meta.get('color'), icon=meta.get('icon'),
                         parent_id=meta.get('parent_id'), sort_order=meta.get('sort_order') or 0)
            session.add(c)
            if last.get('target_line'):
                tl = session.get(BudgetItem, last['target_line']['id'])
                if tl:
                    tl.amount = last['target_line']['amount']
            if last.get('line') and not last.get('line_moved'):
                ln = last['line']
                session.add(BudgetItem(name=ln['name'], amount=ln['amount'], type=ln['type'], category=ln['category'], is_active=True))
            if last.get('line_moved'):
                lm = session.get(BudgetItem, last['line_moved'])
                if lm:
                    lm.category = meta['name']
        elif k in ('split', 'unmatched'):
            for tid, cid in last.get('moved', []):
                t = session.get(Transaction, tid)
                if t:
                    t.category_id = cid
            if k == 'split':
                rules = [r for r in (_setting_json(session, 'import_rules_json', []) or []) if r.get('id') != last.get('rule_id')]
                _set_setting(session, 'import_rules_json', json.dumps(rules))
                said = _setting_json(session, 'tidy_answers_json', {}) or {}
                said.pop(f"split:{last['merchant']}", None)
                _set_setting(session, 'tidy_answers_json', json.dumps(said))
            else:
                items = _setting_json(session, 'import_unmatched_json', []) or []
                for x in items:
                    if x.get('name') == last['name']:
                        x.pop('answer', None)
                _set_setting(session, 'import_unmatched_json', json.dumps(items))
                aliases = _setting_json(session, 'category_aliases_json', {}) or {}
                aliases.pop(last['name'].strip().lower(), None)
                _set_setting(session, 'category_aliases_json', json.dumps(aliases))
        session.delete(_get_setting(session, 'tidy_last'))
        session.commit()
        return ok({'undone': k})


calendar_bp = Blueprint('calendar', __name__)


def _calendar_entries(session, start, end, include_detected=True):
    from core import upcoming
    from core import yearly_steps as ys
    recurring = _setting_json(session, 'recurring_items_json', []) or []
    out = upcoming.entries(session, start, end, pay=_pay_state(session, start)['payers'],
                           recurring=recurring if isinstance(recurring, list) else [],
                           people=_setting_json(session, 'payer_people', {}) or {}, include_detected=include_detected)
    # item 106 Y10: the month a yearly price step would fall in - expected from three steps, possible from two
    for x in _yearly_steps(session, start):
        nxt = x['pattern'] and ys.next_expected({'pattern': True, 'steps': x['steps']})
        if not nxt:
            continue
        when = date(int(nxt[:4]), int(nxt[5:7]), 1)
        if not start <= when <= end:
            continue
        three = len(x['steps']) >= ys.MIN_PROJECT
        out.append({'date': when.isoformat(), 'kind': 'step', 'title': f"{x['payee']}: its yearly price step month",
                    'amount': x['projection']['amount'] if x['projection'] else None,
                    'certainty': upcoming.EXPECTED if three else upcoming.POSSIBLE,
                    'source': 'its price steps a year apart' + ('' if three else ' (two so far)'), 'view': 'budget'})
    return sorted(out, key=lambda e: (e['date'], e['kind'], e['title']))       # upcoming's dates are ISO strings


@calendar_bp.route('/recurring', methods=['GET'])
def calendar_recurring():
    """Item 79 U6: the recurring charges, by the Calendar's own rule, for the Budget page's card - budgeted or not."""
    from core import upcoming
    with db_session() as session:
        return ok({'charges': upcoming.recurring_charges(session, date.today(), include_budgeted=True)})


@calendar_bp.route('', methods=['GET'])
def calendar_get():
    """W3: every upcoming date, from today, each confirmed / expected / possible. `days` defaults to the rest of a year."""
    try:
        days = max(1, min(int(request.args.get('days', 365)), 400))
    except ValueError:
        days = 365
    today = date.today()
    with db_session() as session:
        return ok({'from': today.isoformat(), 'to': (today + timedelta(days=days)).isoformat(),
                   'entries': _calendar_entries(session, today, today + timedelta(days=days))})


evidence_bp = Blueprint('evidence', __name__)
usage_bp = Blueprint('usage', __name__)


# ── Item 58 - the evidence library (EVIDENCE_LIBRARY.md E1-E10) ───────────────────────────────────────────────
@evidence_bp.route('', methods=['GET'])
def evidence_for_surface():
    """E2/E3/E9: the accepted entries that apply on one surface, chosen from the person's goals and debts only,
    each with the person's own answer to its offer, if they gave one.
    Rob 2026-10-21: one card per question - entries that ask the same thing are one card, the first leading and the
    rest in 'also', and one answer covers the card; and each card carries the person's own record ('yours')."""
    from core import evidence as ev
    surface = (request.args.get('surface') or '').strip()
    with db_session() as session:
        answers = _setting_json(session, 'evidence_answers', []) or []
        chosen = ev.select(session, surface)
        cushion = _cash_above_floors(session) if any('no_savings_goal' in e['applies_when'] for e in chosen) else None
        out, by_offer = [], {}
        for e in chosen:
            lead = by_offer.get(e['offer'])
            if lead is not None:
                lead['also'].append({k: e[k] for k in ('id', 'finding', 'limits', 'source', 'strength')})
                lead['ids'].append(e['id'])
                continue
            intro = _setting_json(session, f"evidence_intro_{e['id']}_{surface}")
            card = {**e, 'also': [], 'ids': [e['id']], 'yours': ev.yours(session, e, cushion),
                    'intro': intro.get('text') if isinstance(intro, dict) else None}
            by_offer[e['offer']] = card
            out.append(card)
        for card in out:
            card['answer'] = next((a for a in reversed(answers) if a.get('id') in card['ids']), None)
        return ok({'surface': surface, 'surface_words': ev.SURFACE_WORDS.get(surface), 'entries': out})


@evidence_bp.route('/intro', methods=['POST'])
@require_json
def evidence_intro():
    """E3: the narrator's one introducing sentence for an entry on a surface, kept once it passed the voice check
    (R11 included). Only for an accepted entry and a known surface."""
    from core import evidence as ev
    body = request.json or {}
    eid, surface, text = str(body.get('id') or ''), str(body.get('surface') or ''), str(body.get('text') or '').strip()
    if eid not in ev.accepted_ids() or surface not in ev.SURFACES or not text:
        return err('Not an accepted entry on a known surface.', 400)
    with db_session() as session:
        _set_setting(session, f'evidence_intro_{eid}_{surface}', json.dumps({'text': text[:400], 'at': datetime.now().isoformat(timespec='seconds')}))
        session.commit()
        return ok({'saved': True})


@evidence_bp.route('/ids', methods=['GET'])
def evidence_ids():
    """E4: the accepted ids - the only ones the voice check's R11 lets a research claim cite."""
    from core import evidence as ev
    return ok({'ids': ev.accepted_ids()})


@evidence_bp.route('/answer', methods=['POST'])
@require_json
def evidence_answer():
    """E5: the person's answer to an entry's offer - their statement, kept append-only, changed by a new answer."""
    from core import evidence as ev
    body = request.json or {}
    eid, answer = str(body.get('id') or ''), body.get('answer')
    if answer not in ('yes', 'no'):
        return err("answer must be 'yes' or 'no'")
    if eid not in ev.accepted_ids():
        return err('Not an entry in the evidence library.', 404)
    with db_session() as session:
        answers = _setting_json(session, 'evidence_answers', []) or []
        answers.append({'id': eid, 'answer': answer, 'said_at': datetime.now().isoformat(timespec='seconds')})
        _set_setting(session, 'evidence_answers', json.dumps(answers[-500:]))
        session.commit()
        return ok({'answers': [a for a in answers if a['id'] == eid]})


# E8: the person's own rhythm. Recorded; no engine, selection, ranking or tile reads it (ruling 6). Not shown on the
# working picture since Rob 2026-10-21 ("let's bail" on the count there), and kept: "we will need it in other areas".
# usage_open and usage_rhythm are the only code that touches the list of opens (s188).
@usage_bp.route('/open', methods=['POST'])
def usage_open():
    with db_session() as session:
        opens = _setting_json(session, 'app_opens', []) or []
        now = datetime.now()
        cutoff = (now - timedelta(days=60)).isoformat(timespec='seconds')
        opens = [o for o in opens if isinstance(o, str) and o >= cutoff] + [now.isoformat(timespec='seconds')]
        _set_setting(session, 'app_opens', json.dumps(opens[-500:]))
        session.commit()
        return ok({'recorded': True})


def usage_rhythm(session):
    """E8: the opens of the last 30 days, and the 'mostly' (a day-and-time named only when it holds at least 40% of at
    least 4 opens) - {'opens_30d', 'mostly'}. Kept for other areas to use (Rob 2026-10-21); no route serves it now."""
    opens = _setting_json(session, 'app_opens', []) or []
    cutoff = (datetime.now() - timedelta(days=30)).isoformat(timespec='seconds')
    recent = []
    for o in opens:
        try:
            if isinstance(o, str) and o >= cutoff:
                recent.append(datetime.fromisoformat(o))
        except ValueError:
            continue
    mostly = None
    if len(recent) >= 4:
        def part(h):
            return 'mornings' if 5 <= h < 12 else 'afternoons' if 12 <= h < 17 else 'evenings' if 17 <= h < 22 else 'nights'
        tally = {}
        for d in recent:
            k = f"{d.strftime('%A')} {part(d.hour)}"
            tally[k] = tally.get(k, 0) + 1
        top, n = max(tally.items(), key=lambda kv: kv[1])
        if n / len(recent) >= 0.4:
            mostly = top
    return {'opens_30d': len(recent), 'mostly': mostly}


checkin_bp = Blueprint('checkin', __name__)


# ── Item 76 - the Sunday check-in (SUNDAY_CHECKIN.md S1-S12) and the overnight narration rule (S1/S2) ───────────
def _newest_import(session):
    """When the newest imported records arrived (local time, item 109) - hand-kept and Groundwork-written records never count."""
    return session.query(func.max(Transaction.created_at)).filter(
        Transaction.source.isnot(None), Transaction.source != '', Transaction.source != 'manual').scalar()


@checkin_bp.route('', methods=['GET'])
def checkin_get():
    """S3-S8: the week behind, the month so far, the week ahead - every figure from the record - and this Sunday's
    written part if one was written, and whether the person is done with it."""
    from core import checkin as ck
    with db_session() as session:
        today = date.today()
        amts = budget_month_amounts(session)
        items = session.query(BudgetItem).filter_by(is_active=True, type='expense').all()
        budget = sum((amts.get(i.id) or {}).get('month_amount', i.amount or 0) or 0 for i in items)
        recurring = _setting_json(session, 'recurring_items_json', []) or []
        f = ck.facts(session, today, budget_month=budget, pay=_pay_state(session, today)['payers'],
                     payer_people=_setting_json(session, 'payer_people', {}) or {},
                     recurring=recurring if isinstance(recurring, list) else [])
        # item 58 E5: a yes to a goal-progress entry makes the check-in name the goals and where they stand
        from core import evidence as ev
        acts = {e['id']: (e.get('act') or {}).get('kind') for e in ev.accepted()}
        said = {}
        for a in _setting_json(session, 'evidence_answers', []) or []:
            if isinstance(a, dict):
                said[a.get('id')] = a.get('answer')
        f['goals'] = []
        if any(acts.get(i) == 'checkin_goals' and v == 'yes' for i, v in said.items()):
            from core.database import SinkingFund
            for sf in session.query(SinkingFund).filter_by(is_active=True).all():
                left = max(0.0, (sf.target_amount or 0) - (sf.current_amount or 0))
                months = None
                try:
                    dl = date.fromisoformat(sf.deadline) if sf.deadline else None
                    months = max(1, (dl.year - today.year) * 12 + dl.month - today.month) if dl and dl > today else None
                except ValueError:
                    dl = None
                f['goals'].append({'name': sf.name, 'saved': round(sf.current_amount or 0, 2), 'target': round(sf.target_amount or 0, 2),
                                   'deadline': sf.deadline, 'monthly': round(left / months, 2) if months and left > 0 else None})
        w0, w1 = ck.week_bounds(today)
        f['price_changes'] = [{'sentence': x['sentence'], 'payee': x['payee']} for x in _price_changes(session, today)
                              if w0.isoformat() <= x['seen_on'] <= w1.isoformat()]
        # item 106 Y10: a yearly projection the week its month begins; a question the week its new price landed
        f['yearly_steps'] = []
        for x in _yearly_steps(session, today):
            q, p = x['question'], x['projection']
            begins = lambda m: w0.isoformat() <= m + '-01' <= w1.isoformat()
            if q and w0.isoformat() <= (q.get('charge_date') or q['month'] + '-01') <= w1.isoformat():
                f['yearly_steps'].append({'payee': x['payee'], 'sentence': x['sentence'], 'question': q['text']})
            elif p and begins(p['month']):
                f['yearly_steps'].append({'payee': x['payee'], 'sentence': x['sentence'],
                                          'projection': {'month': p['month'], 'amount': p['amount']}})
        key = today.isoformat()
        return ok({**f, 'date': key, 'is_sunday': today.weekday() == 6,
                   'written': _setting_json(session, f'checkin_text_{key}'),
                   'closed': bool(_setting_json(session, f'checkin_closed_{key}')),
                   'people': [r.value for r in (_get_setting(session, 'household_user1'), _get_setting(session, 'household_user2'))
                              if r is not None and (r.value or '').strip()]})


@checkin_bp.route('/written', methods=['POST'])
@require_json
def checkin_written():
    """S1/S9: this Sunday's written part, kept once it passed the checks."""
    body = request.json or {}
    key, text = str(body.get('date') or '')[:10], str(body.get('text') or '').strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', key) or not text:
        return err('date and text are required')
    with db_session() as session:
        _set_setting(session, f'checkin_text_{key}', json.dumps({'text': text[:4000], 'written_at': datetime.now().isoformat(timespec='seconds')}))
        session.commit()
        return ok({'saved': key})


@checkin_bp.route('/close', methods=['POST'])
@require_json
def checkin_close():
    """S12: the person is done with this Sunday's check-in; it stays closed for that day."""
    key = str((request.json or {}).get('date') or date.today().isoformat())[:10]
    with db_session() as session:
        _set_setting(session, f'checkin_closed_{key}', 'true')
        session.commit()
        return ok({'closed': key})


@checkin_bp.route('/whose', methods=['POST'])
@require_json
def checkin_whose():
    """S7: whose pay an employer's deposits are - asked once, kept as the person's word, changeable."""
    body = request.json or {}
    payer = str(body.get('payer') or '').strip().lower()[:60]
    person = str(body.get('person') or '').strip()[:40]
    if not payer or not person:
        return err('payer and person are required')
    with db_session() as session:
        people = _setting_json(session, 'payer_people', {}) or {}
        people[payer] = person
        _set_setting(session, 'payer_people', json.dumps(people))
        session.commit()
        return ok({'payer_people': people})


def _narration_rule(newest, last, now):
    """S1 (Rob's rule), as a pure function: (fresh, unwritten). Fresh: the newest import is under 48 hours old.
    Unwritten: nothing has been written since it."""
    fresh = bool(newest and now - newest < timedelta(hours=48))
    unwritten = bool(newest and (last is None or newest > last))
    return fresh, unwritten


@checkin_bp.route('/narration-due', methods=['GET'])
def narration_due():
    """S1/S2 (Rob's rule): background narration runs only when the newest import is under 48 hours old and nothing
    has been written since it. Then: this Sunday's check-in (if today is Sunday and none is written) and the one
    monthly review that is due (item 75)."""
    from core import monthly_review as mr
    with db_session() as session:
        newest = _newest_import(session)
        last = _setting_json(session, 'narration_last_at')
        try:
            last_dt = datetime.fromisoformat(last) if last else None
        except (TypeError, ValueError):
            last_dt = None
        fresh, unwritten = _narration_rule(newest, last_dt, datetime.now())
        ok_to_run = fresh and unwritten
        today = date.today()
        return ok({'run': ok_to_run, 'fresh': fresh, 'unwritten': unwritten,
                   'checkin': ok_to_run and today.weekday() == 6 and not _setting_json(session, f'checkin_text_{today.isoformat()}'),
                   'review': mr.due(session) if ok_to_run else None})


@checkin_bp.route('/narration-done', methods=['POST'])
def narration_done():
    """S1: the night's narration is written - nothing more runs until a newer import arrives."""
    with db_session() as session:
        # full precision: an import in the same second as this must not read as newer than it
        _set_setting(session, 'narration_last_at', json.dumps(datetime.now().isoformat()))
        session.commit()
        return ok({'done': True})


review_bp = Blueprint('review', __name__)


# ── Item 75 - the month's review, written when the month is complete (MONTHLY_REVIEW.md M1-M10) ─────────────────
@review_bp.route('/status', methods=['GET'])
def review_status():
    """M2/M4: a month's state (complete, in progress, waiting - and for which accounts) and its saved review."""
    from core import monthly_review as mr
    month = (request.args.get('month') or '').strip()
    if not re.fullmatch(r'\d{4}-\d{2}', month):
        return err('month (YYYY-MM) is required')
    with db_session() as session:
        return ok({**mr.status(session, month), 'saved': mr.saved(session, month)})


@review_bp.route('/due', methods=['GET'])
def review_due():
    """M1/M6: the one month whose review should be written now, if any."""
    from core import monthly_review as mr
    with db_session() as session:
        return ok({'month': mr.due(session)})


@review_bp.route('', methods=['POST'])
@require_json
def review_save():
    """M4: save a review as the month's; the earlier one is kept in its history. Never a month in progress."""
    from core import monthly_review as mr
    body = request.json or {}
    month, text, kind = str(body.get('month') or ''), str(body.get('text') or '').strip(), body.get('kind')
    if not re.fullmatch(r'\d{4}-\d{2}', month) or not text:
        return err('month and text are required')
    with db_session() as session:
        try:
            out = mr.save(session, month, text[:20000], kind)
        except ValueError as e:
            return err('A month in progress is never saved as its review.' if str(e) == 'in_progress' else 'kind is not one Groundwork keeps', 400)
        session.commit()
        return ok(out)


@review_bp.route('/ready', methods=['GET'])
def review_ready():
    """M5: the newest review written but not yet opened - for one quiet line on the dashboard."""
    with db_session() as session:
        rows = session.query(AppSetting).filter(AppSetting.key.like('review_meta_%')).all()
        best = None
        for r in rows:
            try:
                meta = json.loads(r.value or '{}')
            except ValueError:
                continue
            if not meta.get('seen'):
                m = r.key.replace('review_meta_', '')
                if not best or m > best:
                    best = m
        return ok({'month': best})


@review_bp.route('/seen', methods=['POST'])
@require_json
def review_seen():
    with db_session() as session:
        key = f"review_meta_{str((request.json or {}).get('month') or '')[:7]}"
        meta = _setting_json(session, key)
        if meta:
            meta['seen'] = True
            _set_setting(session, key, json.dumps(meta))
            session.commit()
        return ok({'seen': bool(meta)})


@review_bp.route('/skip-account', methods=['POST'])
@require_json
def review_skip_account():
    """M2: the person says an account is not needed for reviews (closed, or never imported); a month stops waiting."""
    try:
        aid = int((request.json or {}).get('account_id'))
    except (TypeError, ValueError):
        return err('account_id is required')
    with db_session() as session:
        skip = _setting_json(session, 'review_skip_accounts', []) or []
        if aid not in skip:
            skip.append(aid)
        _set_setting(session, 'review_skip_accounts', json.dumps(skip))
        session.commit()
        return ok({'skipped': skip})


help_bp = Blueprint('help', __name__)


# ── Item 72 stage 2 C7/C11: the questions the Ask box could not answer - the person's own words, kept only to be shown
# back to them and cleared. The three routes below are the only code that touches them (s193).
@help_bp.route('/unanswered', methods=['GET'])
def help_unanswered_list():
    with db_session() as session:
        return ok({'questions': _setting_json(session, 'help_unanswered', []) or []})


@help_bp.route('/unanswered', methods=['POST'])
@require_json
def help_unanswered_add():
    text = str((request.json or {}).get('text') or '').strip()[:300]
    if not text:
        return err('text is required')
    with db_session() as session:
        qs = _setting_json(session, 'help_unanswered', []) or []
        qs.append({'text': text, 'at': datetime.now().isoformat(timespec='seconds')})
        _set_setting(session, 'help_unanswered', json.dumps(qs[-100:]))
        session.commit()
        return ok({'count': len(qs[-100:])})


@help_bp.route('/unanswered/clear', methods=['POST'])
@require_json
def help_unanswered_clear():
    """One question (by its place in the list) or all of them."""
    idx = (request.json or {}).get('index')
    with db_session() as session:
        qs = _setting_json(session, 'help_unanswered', []) or []
        if idx is None:
            qs = []
        elif isinstance(idx, int) and 0 <= idx < len(qs):
            qs.pop(idx)
        else:
            return err('Not a question in the list.', 404)
        _set_setting(session, 'help_unanswered', json.dumps(qs))
        session.commit()
        return ok({'questions': qs})


why_bp = Blueprint('why', __name__)


# ── Item 72 - Ask why, stage 1 (ASK_WHY.md C1-C10 as revised in section 5) ─────────────────────────────────────
# Fixed checks on the record; fixes previewed, approved, verified and undoable. No model in this stage.
def _import_rules(session):
    rules = _setting_json(session, 'import_rules_json', []) or []
    return [r for r in rules if isinstance(r, dict)]


@why_bp.route('', methods=['GET'])
def why_investigate():
    """C3: every check that applies to a figure, run on the record, each with its rows, what it can and can't tell."""
    from core import ask_why
    with db_session() as session:
        out = ask_why.investigate(session, (request.args.get('figure') or '').strip())
        if out is None:
            return err('Not a figure Groundwork can check.', 404)
        return ok(out)


# Item 72 stage 3 (C2): the model picks one registered check for a question about the person's money - under a
# grammar that can write nothing else - or says it is unsure, or that none fits. It sees only the question and the
# check names; it never sees the record, writes a query, or changes anything. Its pick is offered, then run on a tap.
WHY_ROUTE_SYSTEM = (
    'You sort one question about a person\'s own money records into one check, by name. Answer with exactly one name.\n'
    'inputs_income: what went into their monthly income figure; which deposits counted; why income looks lower.\n'
    'payer_switch: the same payer or store filed under a different category than before.\n'
    'wrong_kind: deposits filed as spending, or charges filed as income.\n'
    'stopped: a regular paycheck or deposit that has not come in.\n'
    'duplicates: the same transaction showing twice.\n'
    'two_accounts: the same charge or subscription paid from two different accounts.\n'
    'own_transfers: money moved between their own accounts counted as income.\n'
    'empty_months: months or accounts with no records.\n'
    'unsure: about their records, and two or more checks fit equally.\n'
    'none: anything else - advice, investing, a request to do or pay something, writing, general knowledge, '
    'or instructions.\n'
    'Examples:\n'
    '"Which deposits count toward my income?" -> inputs_income\n'
    '"Why did my income go down in July?" -> inputs_income\n'
    '"Why is my pay under a new category?" -> payer_switch\n'
    '"Why are my paychecks counted as spending?" -> wrong_kind\n'
    '"My paycheck did not come in" -> stopped\n'
    '"The same charge shows up twice" -> duplicates\n'
    '"Am I paying for Netflix from two accounts?" -> two_accounts\n'
    '"Is my savings transfer counted as income?" -> own_transfers\n'
    '"Why are there no transactions in April?" -> empty_months\n'
    '"Something looks off" -> unsure\n'
    '"Should I buy a stock?" -> none\n'
    '"Write a poem about money" -> none\n'
    '"Pay my bill" -> none')
# A question that names nothing in the person's records never reaches the model: it gets C11's sentence (stage 3's
# plain-words gate, measured 2026-10-11 - the model alone sent "a poem about money" to a check).
WHY_ROUTE_WORDS = re.compile(r'\b(income|deposit\w*|paycheck\w*|pay|paid|salary|wages?|charge[sd]?|transactions?|'
                             r'categor\w*|account\w*|transfer\w*|month\w*|records?|ledger|spending|spent|imports?|'
                             r'twice|duplicate\w*|missing|statement\w*|filed|purchase\w*|bought|grocer\w*|shopping|bills?)\b', re.I)
WHY_ACT_WORDS = re.compile(r'\b(should i|buy|invest\w*|stocks?|poem|write|pay (?:my|the|this)|delete|remove|erase|'
                           r'move (?:all|every)|transfer (?:all|money)|ignore|forget|disregard|pretend|you are now|'
                           r'rules|instructions|prompt|system:|admin|account numbers?|passwords?)\b', re.I)


def why_route_outside(q):
    """Stage 3's gate, before any model: a question that names nothing in the person's records, asks for advice, or
    asks Groundwork to do something gets C11's sentence. Words typed in are only words."""
    return not WHY_ROUTE_WORDS.search(q) or bool(WHY_ACT_WORDS.search(q))


WHY_ROUTE_OPTIONS = ('inputs_income', 'payer_switch', 'wrong_kind', 'stopped', 'duplicates', 'two_accounts',
                     'own_transfers', 'empty_months', 'unsure', 'none')


@why_bp.route('/route', methods=['POST'])
@require_json
def why_route():
    """-> {'state': 'picked', 'check', 'title'} | {'state': 'unsure', 'checks': [...]} | {'state': 'none'} |
    {'state': 'off'}. The question is data: it goes to the model as the user's words and nowhere else."""
    from core import ask_why, engine
    q = str((request.json or {}).get('question') or '').strip()[:300]
    if not q:
        return err('A question is needed.')
    every = [{'check': k, 'title': v['title']} for k, v in ask_why.CHECKS.items()]
    if why_route_outside(q):
        return ok({'state': 'none'})            # advice, a request to act, or nothing about the records: never the model
    # AI-off audit F6 (item 32 L4): with AI off or unable to run, a question about the records still reaches the
    # checks - the person chooses one from the fixed list, exactly as when the model is unsure. Never the model.
    with db_session() as session:
        if _get_setting(session, 'ai_enabled') and (_get_setting(session, 'ai_enabled').value or '').lower() in ('false', '0', 'off'):
            return ok({'state': 'off', 'checks': every})
    try:
        r = engine.choose(WHY_ROUTE_SYSTEM, q, WHY_ROUTE_OPTIONS)
    except Exception:                                   # noqa: BLE001 - routing failing is the same as no route
        logging.getLogger('groundwork').info('why route: the model could not be asked')
        return ok({'state': 'off', 'checks': every})
    _ai_log_write({'surface': 'ask_why_route', 'system': WHY_ROUTE_SYSTEM, 'messages': [{'role': 'user', 'content': q}]},
                  r.get('raw') or r.get('reason') or '', 'grammar' if r.get('ok') else (r.get('reason') or ''),
                  getattr(engine, 'MODEL_FILE', ''))
    if not r.get('ok'):
        # the model did not answer (off, loading, or unable to run here - a processor, a missing or mismatched file, a
        # failed load: the engine names which); only a refused answer means the question fits no check
        if r.get('reason') not in ('refused', 'too_long'):
            return ok({'state': 'off', 'checks': every})
        return ok({'state': 'none'})
    if r['choice'] == 'none':
        return ok({'state': 'none'})
    if r['choice'] == 'unsure':
        return ok({'state': 'unsure', 'checks': every})
    return ok({'state': 'picked', 'check': r['choice'], 'title': ask_why.CHECKS[r['choice']]['title'], 'checks': every})


@why_bp.route('/check', methods=['GET'])
def why_check():
    """Stage 3: one registered check, run on the record, as the person picked it (or tapped the model's pick)."""
    from core import ask_why
    with db_session() as session:
        out = ask_why.run_one(session, (request.args.get('id') or '').strip())
        if out is None:
            return err('Not a check Groundwork has.', 404)
        return ok(out)


@why_bp.route('/preview', methods=['POST'])
@require_json
def why_preview():
    """C4: the exact change - each row, current and proposed category, the total, the figure before and after."""
    from core import ask_why
    with db_session() as session:
        p = ask_why.preview(session, (request.json or {}).get('fix'), _import_rules(session))
        if not p:
            return err('That change does not match the records.', 400)
        return ok(p)


@why_bp.route('/apply', methods=['POST'])
@require_json
def why_apply():
    """C4: applies exactly the previewed change, only if the records are as previewed; confirms the write and records
    it in the Historian. A changed record returns a fresh preview instead (409)."""
    from core import ask_why
    body = request.json or {}
    with db_session() as session:
        state, res = ask_why.apply(session, body.get('fix'), str(body.get('fingerprint') or ''), _import_rules(session),
                                   use_rule=bool(body.get('use_rule')))
        if state == 'invalid':
            return err('That change does not match the records.', 400)
        if state == 'stale':
            return jsonify({'ok': False, 'error': 'These records changed since the preview. Here is the change as it '
                                                  'stands now.', 'data': res}), 409
        if state == 'failed':
            return err('The change did not take. Nothing was changed.', 500)
        if res['rule_added']:
            _set_setting(session, 'import_rules_json', json.dumps(res['rules']))
        session.commit()
        return ok({'historian_id': res['historian_id'], 'changed': res['changed'], 'rule_added': res['rule_added']})


@why_bp.route('/undo', methods=['POST'])
@require_json
def why_undo():
    """C4: reverts a fix - only rows still as it left them; rows edited since are listed and left as they are."""
    from core import ask_why
    with db_session() as session:
        res = ask_why.undo(session, int((request.json or {}).get('historian_id') or 0), _import_rules(session))
        if res is None:
            return err('Not a fix Groundwork made.', 404)
        if res.get('already'):
            return err('That fix was already undone.', 409)
        _set_setting(session, 'import_rules_json', json.dumps(res['rules']))
        session.commit()
        return ok({'reverted': res['reverted'], 'left_as_edited': res['left_as_edited']})


@why_bp.route('/fixes', methods=['GET'])
def why_fixes():
    """The fixes made through Ask why, newest first, each with whether it was undone."""
    with db_session() as session:
        rows = (session.query(HistorianEntry).filter_by(event_category='record_fix')
                .order_by(HistorianEntry.id.desc()).limit(20).all())
        out = []
        for e in rows:
            c = json.loads(e.context_json or '{}')
            out.append({'historian_id': e.id, 'at': e.created_at.isoformat() if e.created_at else None,
                        'label': c.get('label'), 'to': c.get('to'), 'count': len(c.get('changes') or []),
                        'total': c.get('total'), 'undone': c.get('undone')})
        return ok({'fixes': out})


reimburse_bp = Blueprint('reimburse', __name__)


# ── Item 72 stage 4 (ASK_WHY.md C5): purchases an employer pays back - told, never guessed ─────────────────────
@reimburse_bp.route('', methods=['GET'])
def reimburse_state():
    from core import reimburse
    with db_session() as session:
        said = _setting_json(session, 'work_reimbursements_said')
        return ok({'said': said, 'items': reimburse.state(session) if (said or {}).get('answer') == 'yes' else []})


@reimburse_bp.route('/said', methods=['POST'])
@require_json
def reimburse_said():
    """C5: the person's own word that they buy things for work and get paid back (or not). Changeable."""
    answer = (request.json or {}).get('answer')
    if answer not in ('yes', 'no'):
        return err("answer must be 'yes' or 'no'")
    with db_session() as session:
        _set_setting(session, 'work_reimbursements_said',
                     json.dumps({'answer': answer, 'at': datetime.now().isoformat(timespec='seconds')}))
        session.commit()
        return ok({'answer': answer})


def _reimburse_do(fn, *args):
    from core import reimburse
    with db_session() as session:
        if ((_setting_json(session, 'work_reimbursements_said') or {}).get('answer')) != 'yes':
            return err('Say first that you buy things for work and get paid back.', 409)
        res, problem = getattr(reimburse, fn)(session, *args)
        if problem:
            session.rollback()
            return err(problem, 400)
        if fn == 'match' and isinstance(res, dict) and res.get('match'):
            from core import household_statements as _hs
            _hs.carry_new(session, 'reimburse', res['match'])     # item 93 B11, when someone is answering
        session.commit()
        return ok({'result': res if isinstance(res, dict) else {'id': getattr(res, 'id', None)},
                   'items': reimburse.state(session)})


@reimburse_bp.route('/mark', methods=['POST'])
@require_json
def reimburse_mark():
    b = request.json or {}
    return _reimburse_do('mark', int(b.get('transaction_id') or 0), str(b.get('employer') or ''))


@reimburse_bp.route('/match', methods=['POST'])
@require_json
def reimburse_match():
    b = request.json or {}
    return _reimburse_do('match', int(b.get('item_id') or 0), int(b.get('credit_id') or 0))


@reimburse_bp.route('/unmatch', methods=['POST'])
@require_json
def reimburse_unmatch():
    return _reimburse_do('unmatch', int((request.json or {}).get('match_id') or 0))


@reimburse_bp.route('/write-off', methods=['POST'])
@require_json
def reimburse_write_off():
    return _reimburse_do('write_off', int((request.json or {}).get('item_id') or 0))


@reimburse_bp.route('/unmark', methods=['POST'])
@require_json
def reimburse_unmark():
    return _reimburse_do('unmark', int((request.json or {}).get('item_id') or 0))


income_bp = Blueprint('income_change', __name__)


@income_bp.route('', methods=['GET'])
def income_change_get():
    with db_session() as session:
        return ok(_income_change_state(session))


@income_bp.route('/answer', methods=['POST'])
@require_json
def income_change_answer():
    """I2: the person's word - 'lasting' | 'temporary' | 'unsure'. Append-only, with when and which change it answers."""
    ans = (request.json or {}).get('answer')
    if ans not in ('lasting', 'temporary', 'unsure'):
        return err('answer must be lasting, temporary or unsure')
    with db_session() as session:
        st = _income_change_state(session)
        if not st.get('change'):
            return err('There is no income change on record to answer.', 409)
        hist = _setting_json(session, 'income_change_answers', []) or []
        hist.append({'answer': ans, 'said': datetime.now().isoformat(timespec='seconds'), 'since': st['change']['month'],
                     'level': st['change']['to']})
        _set_setting(session, 'income_change_answers', json.dumps(hist))
        session.commit()
        return ok(_income_change_state(session))


@income_bp.route('/apply', methods=['POST'])
@require_json
def income_change_apply():
    """I6 (a), ruled: the person's one tap - "Make this my budget". The plan is recomputed here (never taken from the
    page), each line's change is a budget_adjusted event exactly as a manual edit is, and the old amounts are kept for
    Undo. Nothing else ever changes a saved amount."""
    with db_session() as session:
        st = _income_change_state(session)
        plan = next((s.get('plan') for s in st.get('scenarios', []) if s['key'] == 'budget_follows'), None)
        if not st.get('change') or not plan or not plan['changes']:
            return err('There is nothing to apply.', 409)
        done = []
        from core import plan_edits
        plan_at = datetime.now().isoformat(timespec='seconds')   # item 80 E1: one time for the plan
        for ch in plan['changes']:
            item = session.get(BudgetItem, ch['id'])
            if not item or abs((item.amount or 0) - ch['old']) > 0.005:
                continue                      # the line changed since the plan was shown: left as it is
            item.amount = ch['new']
            log_historian_event(session, 'budget_adjusted', expected_value=ch['old'], actual_value=ch['new'],
                                context=plan_edits.plan_context(item, 'income_change_apply', plan_at))
            done.append({'id': item.id, 'name': item.name, 'old': ch['old'], 'new': ch['new']})
        _set_setting(session, 'income_change_applied', json.dumps({'at': plan_at,
                                                                   'month': st['change']['month'], 'changes': done}))
        session.commit()
        return ok(_income_change_state(session))


@income_bp.route('/undo', methods=['POST'])
@require_json
def income_change_undo():
    """I6 (a): Undo restores the amounts the tap changed - each a budget_adjusted event back, so the record shows
    both (AP10: undoing never falsifies the history)."""
    with db_session() as session:
        applied = _setting_json(session, 'income_change_applied')
        if not applied:
            return err('There is nothing to undo.', 409)
        from core import plan_edits
        for ch in applied.get('changes', []):
            item = session.get(BudgetItem, ch['id'])
            if not item or abs((item.amount or 0) - ch['new']) > 0.005:
                continue                      # changed again since: the person's later edit stands
            item.amount = ch['old']
            log_historian_event(session, 'budget_adjusted', expected_value=ch['new'], actual_value=ch['old'],
                                context=plan_edits.plan_context(item, 'income_change_undo', applied.get('at')))
        row = _get_setting(session, 'income_change_applied')
        if row:
            session.delete(row)
        session.commit()
        return ok(_income_change_state(session))


@income_bp.route('/pay-kind', methods=['POST'])
@require_json
def income_pay_kind():
    """D10: the person says what kind of pay a payer's is - hourly with overtime, or salary / steady. Kept as their
    statement (append-only, latest wins), changeable; it picks the rule for that payer."""
    body = request.json or {}
    payer = str(body.get('payer') or '').strip().lower()[:60]
    kind = body.get('kind')
    if not payer or kind not in ('hourly', 'salary'):
        return err("a payer and kind 'hourly' or 'salary' are needed")
    with db_session() as session:
        said = _setting_json(session, 'pay_kinds', []) or []
        said.append({'payer': payer, 'kind': kind, 'said_at': datetime.now().isoformat(timespec='seconds')})
        _set_setting(session, 'pay_kinds', json.dumps(said[-200:]))
        session.commit()
        return ok(_income_change_state(session))


@income_bp.route('/contract', methods=['POST'])
@require_json
def income_contract_line():
    """D11: the person says whether a budget line is set by a contract. Kept as their statement (append-only, the
    latest wins); a yes keeps the line out of every plan that moves budget money, a no lets it be offered."""
    body = request.json or {}
    answer = body.get('answer')
    try:
        line_id = int(body.get('line_id'))
    except (TypeError, ValueError):
        return err('line_id is required')
    if answer not in ('yes', 'no'):
        return err("answer must be 'yes' or 'no'")
    with db_session() as session:
        if not session.get(BudgetItem, line_id):
            return err('Not one of your budget lines.', 404)
        said = _setting_json(session, 'contract_lines', []) or []
        said.append({'line_id': line_id, 'answer': answer, 'said_at': datetime.now().isoformat(timespec='seconds')})
        _set_setting(session, 'contract_lines', json.dumps(said[-500:]))
        session.commit()
        return ok(_income_change_state(session))


def _plan_repair_rows(session):
    rows = session.query(HistorianEntry).filter(HistorianEntry.event_category == 'budget_adjusted') \
        .order_by(HistorianEntry.created_at, HistorianEntry.id).all()
    return [(e.id, e.created_at, json.loads(e.context_json or '{}'), e.expected_value, e.actual_value) for e in rows]


@willingness_bp.route('/plan-repair', methods=['GET'])
def willingness_plan_repair():
    """Item 80 E4: budget changes written by "Make this my budget" and its Undo before they were marked - found by
    their shape, shown to the person line by line before anything is changed."""
    from core import plan_edits
    with db_session() as session:
        return ok({'pairs': plan_edits.unmarked_pairs(_plan_repair_rows(session))})


@willingness_bp.route('/plan-repair/mark', methods=['POST'])
@require_json
def willingness_plan_repair_mark():
    """Item 80 E4: mark exactly one shown pair as the plan's and its Undo's. Nothing is deleted; the record keeps
    every change as it happened, and the working picture stops reading them as the person's own decisions."""
    from core import plan_edits
    apply_at = str((request.json or {}).get('apply_at') or '')
    with db_session() as session:
        pair = next((x for x in plan_edits.unmarked_pairs(_plan_repair_rows(session)) if x['apply_at'] == apply_at), None)
        if not pair:
            return err('Nothing to mark for that time.', 404)
        n = plan_edits.mark(session, pair)
        log_historian_event(session, 'plan_edits_marked', context={'apply_at': pair['apply_at'], 'undo_at': pair['undo_at'],
                                                                    'entries': n})
        session.commit()
        return ok({'marked': n})


@income_bp.route('/snooze', methods=['POST'])
@require_json
def income_change_snooze():
    """I6 (a)'s monthly check-in: "Not now" hides the card for the rest of this month - the person's choice."""
    with db_session() as session:
        _set_setting(session, 'income_change_snooze', date.today().strftime('%Y-%m'))
        session.commit()
        return ok(_income_change_state(session))


@willingness_bp.route('/strategy', methods=['POST'])
@require_json
def willingness_strategy():
    """F.6a: the inferred channel is adjustable, always. {use: false} sets an earned strategy label aside (it is
    then shown, not used); {use: true} lets it be used again. The label itself is never stored."""
    use = (request.json or {}).get('use')
    if not isinstance(use, bool):
        return err('use must be true or false')
    with db_session() as session:
        row = _get_setting(session, 'willingness_strategy_aside')
        if use:
            if row:
                session.delete(row)
        else:
            _set_setting(session, 'willingness_strategy_aside', json.dumps({'said': datetime.now().isoformat(timespec='seconds')}))
        session.commit()
        s = willingness_state(session)
        s.pop('effective')
        return ok(s)


# ── The dashboard: your summary, and what needs attention (gw 2.0/DASHBOARD_SUMMARY_ATTENTION.md, ruled
# 2026-09-27, authorised 2026-09-30) ──────────────────────────────────────────────────────────────────────
#
# Rob's rule, exactly: usage never creates, ranks, or implies an attention item; an attention item requires
# evidence about the user's finances. Nothing here reads, counts or stores what the user opens. What IS
# stored is the user's own choices: how they arranged the summary tiles, and which facts they dismissed.

DASHBOARD_TILES = ('dashWhatChanged', 'dashHealthCard', 'dashHeroCard', 'dashFreedMinimumsCard',
                   'dashDonutCard', 'dashUpcomingCard', 'dashInvestmentsCard')   # the seventh: item 29
IMPORT_STALE_DAYS = 21          # ruling 4: an account not imported for three weeks
_MAX_DISMISSED = 300

dashboard_bp = Blueprint('dashboard', __name__)


def _dashboard_json(session, key, default):
    row = _get_setting(session, key)
    try:
        return json.loads(row.value) if row and row.value else default
    except (json.JSONDecodeError, TypeError):
        return default


def _dashboard_store(session, key, value):
    row = _get_setting(session, key)
    if row:
        row.value = json.dumps(value)
    else:
        session.add(AppSetting(key=key, value=json.dumps(value)))


def stale_imports(session, today=None):
    """Ruling 4's second kind: an account whose last IMPORT is three weeks old or more.

    The completeness test comes first (absence is not zero). Only an account that has been imported
    into at all - any transaction whose source is not 'manual' - can be stale. An account kept by hand
    has no import to be late, and saying it is late would invent an obligation the user never took on.
    The fact is the date the last import landed (its transactions' created_at), not the latest
    transaction date: a quiet account imported yesterday is up to date.
    """
    now = today or datetime.now()
    rows = session.query(
        Transaction.account_id, func.max(Transaction.created_at)
    ).filter(
        Transaction.account_id.isnot(None),
        Transaction.source.isnot(None), Transaction.source != '', Transaction.source != 'manual',
    ).group_by(Transaction.account_id).all()
    out = []
    skip = set(_setting_json(session, 'review_skip_accounts', []) or [])     # item 75/76: "not needed" counts here too
    for account_id, last in rows:
        if last is None or account_id in skip:
            continue
        days = (now - last).days
        if days < IMPORT_STALE_DAYS:
            continue
        acct = session.get(Account, account_id)
        if not acct or (hasattr(acct, 'is_active') and acct.is_active is False):
            continue
        out.append({'account_id': account_id, 'account': acct.name, 'last_import': last.date().isoformat(),
                    'days': days})
    out.sort(key=lambda r: -r['days'])
    return out


def imports_behind_this_month(session, today=None):
    """Item 27 T1: the completeness test for any pace statement about this month.

    The imported accounts (hand-kept ones never count) with nothing imported since the month began. While
    any is listed, the month's spending is not known, and a tile says so instead of stating a pace.
    """
    now = today or datetime.now()
    start = datetime(now.year, now.month, 1)
    rows = session.query(Transaction.account_id, func.max(Transaction.created_at)).filter(
        Transaction.account_id.isnot(None),
        Transaction.source.isnot(None), Transaction.source != '', Transaction.source != 'manual',
    ).group_by(Transaction.account_id).all()
    out = []
    skip = set(_setting_json(session, 'review_skip_accounts', []) or [])     # item 75/76: "not needed" counts here too
    for account_id, last in rows:
        if last is None or last >= start or account_id in skip:
            continue
        acct = session.get(Account, account_id)
        if not acct or acct.is_active is False:
            continue
        out.append({'account_id': account_id, 'account': acct.name, 'last_import': last.date().isoformat()})
    out.sort(key=lambda r: r['account'])
    return out


@dashboard_bp.route('/attention/imports', methods=['GET'])
def dashboard_stale_imports():
    with db_session() as session:
        return ok({'stale': stale_imports(session), 'threshold_days': IMPORT_STALE_DAYS,
                   'behind_this_month': imports_behind_this_month(session)})


@dashboard_bp.route('/prefs', methods=['GET'])
def dashboard_prefs():
    """The user's own arrangement and dismissals - their choices, nothing observed."""
    with db_session() as session:
        lay = _layout(session)
        return ok({'tiles': _user_tiles(lay),
                   'titles': {**{e['id']: e['title'] for e in TILE_CATALOGUE if not e.get('param')},
                              **{a: _catalogue_entry(a)['title'] for a in lay['added']}},
                   'layout': lay,
                   'dismissed': _dashboard_json(session, 'dashboard_dismissed', []),
                   'requests': _dashboard_json(session, 'dashboard_tile_requests', [])})


@dashboard_bp.route('/layout', methods=['PUT'])
@require_json
def dashboard_set_layout():
    """Ruling 1: pin / hide / reorder, by the user. Only the known tiles; nothing else is accepted."""
    body = request.json or {}
    with db_session() as session:
        stored = _layout(session)
        allowed = set(_user_tiles(stored))
        layout = {}
        for field in ('order', 'pinned', 'hidden'):
            v = body.get(field, [])
            if not isinstance(v, list) or any(t not in allowed for t in v) or len(set(v)) != len(v):
                return err(f'{field} must list known dashboard tiles, each once')
            layout[field] = v
        layout['added'] = stored['added']       # only /add changes what the user has added (R6)
        _dashboard_store(session, 'dashboard_layout', layout)
        session.commit()
    return ok(layout)


@dashboard_bp.route('/dismiss', methods=['POST'])
@require_json
def dashboard_dismiss():
    """Ruling 3: a dismissal is the user's act and persists until the fact it names changes.

    The client sends the item's fingerprint - its kind, its subject and the fact itself (a due date and
    amount, a last-import date, a gated conclusion's missing input). When the fact changes, so does the
    fingerprint, and the item returns on its own evidence: no timeout, and nothing about use resurfaces it.
    """
    fp = (request.json or {}).get('fingerprint')
    if not isinstance(fp, str) or not fp or len(fp) > 300 or fp.split('|', 1)[0] not in (
            'payment_due', 'import_stale', 'blocked_conclusion', 'date_ends', 'fsa_deadline', 'bill_due'):   # item 86 F5, item 94 L6
        return err('a fingerprint of a ruled attention kind is required')
    with db_session() as session:
        dismissed = [d for d in _dashboard_json(session, 'dashboard_dismissed', []) if d != fp]
        dismissed.append(fp)
        _dashboard_store(session, 'dashboard_dismissed', dismissed[-_MAX_DISMISSED:])
        session.commit()
        return ok({'dismissed': dismissed[-_MAX_DISMISSED:]})


def investments_tile(session, today=None):
    """Item 29: the dashboard's Investments tile, from what is on record (INVESTMENTS_TILE.md I1-I5).

    I1  cached prices only - `skip_refresh=True`, so opening the dashboard fetches nothing - each with its date
    I2  a position with no price is named and left out of value and gain; never valued at cost
    I3  a lot with no cost basis counts in value (its value is known) and is named and left out of the gain
    I4  realized gains this calendar year from closed lots; allocation against the user's target only if set
    I5  investment accounts with a balance but no holdings are listed as a fact

    Item 35 V1 (INVESTMENT_VALUATION.md): the two exclusions now live in _compute_portfolio_positions itself - the
    one valuation the Investments page, Net Worth, the snapshots, the drift log and the advisor prompt share - so
    the tile reads its summary rather than re-deriving them, and no two screens can disagree.
    """
    today = today or date.today()
    positions, summary = _compute_portfolio_positions(session, skip_refresh=True)
    value = summary['total_market_value']
    unpriced = [{'ticker': u['ticker'], 'shares': round(u['shares'], 6)} for u in summary['unpriced']]
    no_basis = [{'ticker': u['ticker'], 'shares': round(u['shares'], 6)} for u in summary['no_basis']]
    by_class, unclassified = {}, {}
    for p in positions:
        if p['market_value'] is None:
            continue                                   # no price on record: named in `unpriced`, never valued
        pos_value = float(p['market_value'])
        cls = p.get('asset_class')
        if cls:
            by_class[cls] = by_class.get(cls, 0.0) + pos_value
        else:
            # No class assigned: its value is real, so it is named with its share rather than silently
            # dropped - dropping it would read as "0% US equity" when VOO is most of the portfolio.
            unclassified[p['ticker']] = unclassified.get(p['ticker'], 0.0) + pos_value

    realized = {'total': 0.0, 'short': 0.0, 'long': 0.0, 'unstated': 0, 'lots': 0}
    for lot in session.query(InvestmentLot).filter_by(is_closed=True).all():
        if not lot.closed_date or lot.closed_date.year != today.year:
            continue
        realized['lots'] += 1
        if lot.realized_gain is None:
            realized['unstated'] += 1
            continue
        realized['total'] += lot.realized_gain
        days = getattr(lot, 'holding_period_days', None)
        if days is not None:
            realized['long' if days >= 365 else 'short'] += lot.realized_gain
    realized = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in realized.items()}

    allocation = None
    try:
        t_row = _get_setting(session, 'inv_target_alloc')
        targets = json.loads(t_row.value) if t_row and t_row.value else {}
    except (json.JSONDecodeError, TypeError):
        targets = {}
    targets = {k: v for k, v in (targets or {}).items() if v}
    if targets and value > 0:
        allocation = [{'asset_class': k, 'target_pct': float(v),
                       'actual_pct': round(by_class.get(k, 0.0) / value * 100, 1)} for k, v in sorted(targets.items())]
    allocation_unclassified = ([{'ticker': t, 'pct': round(v / value * 100, 1)} for t, v in sorted(unclassified.items())]
                               if allocation is not None else [])

    held_accounts = {p.get('account_id') for p in positions}
    balance_only = [{'account': a.name, 'balance': round(float(a.balance or 0), 2)}
                    for a in session.query(Account).filter_by(type='investment').all()
                    if a.is_active is not False and a.id not in held_accounts and (a.balance or 0) > 0]

    present = bool(positions) or bool(balance_only) or realized['lots'] > 0
    return {
        'present': present,
        'value': round(value, 2),
        'unrealized': ({'gain': summary['total_gain'], 'pct': summary['total_gain_pct']}
                       if summary['total_gain'] is not None else None),
        'prices_from': summary['prices_from'], 'prices_to': summary['prices_to'],
        'manual_prices': summary['manual_prices'],
        'unpriced': unpriced, 'no_basis': no_basis,
        'realized_this_year': realized, 'year': today.year,
        'allocation': allocation, 'allocation_unclassified': allocation_unclassified, 'balance_only': balance_only,
    }


@dashboard_bp.route('/investments', methods=['GET'])
def dashboard_investments():
    with db_session() as session:
        return ok(investments_tile(session))


# ── Item 28: ask for a tile (ASK_FOR_A_TILE.md, ruled 2026-10-01 with build requirements R1-R7) ─────────────
#
# K1: a CLOSED catalogue. Every tile a user can have is an entry here - the seven defaults and the entries the
# engines can back - and adding one is a ruled code change, never generated. R1: this is the one source of the
# tile list; the page reads it from /prefs and keeps no copy of its own.
TILE_CATALOGUE = [
    {'id': 'dashWhatChanged', 'title': 'What changed since last month', 'default': True,
     'words': ['what changed', 'changes', 'since last month', 'month over month', 'movement']},
    {'id': 'dashHealthCard', 'title': 'This month', 'default': True,
     'words': ['this month', 'month so far', 'spending this month', 'budget', 'pace']},
    {'id': 'dashHeroCard', 'title': 'Your plan', 'default': True,
     'words': ['debt free', 'debt-free', 'payoff', 'pay off', 'debt plan', 'your plan']},
    {'id': 'dashFreedMinimumsCard', 'title': 'Freed minimums', 'default': True,
     'words': ['freed minimums', 'paid off cards', 'freed up', 'minimums freed']},
    {'id': 'dashDonutCard', 'title': 'Spending by category', 'default': True,
     'words': ['spending by category', 'categories', 'where my money goes', 'breakdown', 'category breakdown']},
    {'id': 'dashUpcomingCard', 'title': 'Coming up', 'default': True,
     'words': ['upcoming bills', 'coming up', 'due dates', 'bills due', 'upcoming payments']},
    {'id': 'dashInvestmentsCard', 'title': 'Investments', 'default': True,
     'words': ['investments', 'investment', 'stocks', 'portfolio', 'gains', 'losses', 'holdings']},
    {'id': 'gwNetWorthTrendCard', 'title': 'Net worth over time', 'default': False,
     'words': ['net worth', 'networth', 'worth over time', 'wealth', 'assets minus debts', 'how much am i worth']},
    # The remaining slices (Rob, 2026-10-01: "Build Item 28"), each a ruled addition under K1.
    {'id': 'gwFundsCard', 'title': 'Savings funds', 'default': False,
     'words': ['savings funds', 'sinking funds', 'savings goals', 'saving for', 'funds pace', 'savings']},
    {'id': 'gwRecurringCard', 'title': 'Recurring charges', 'default': False,
     'words': ['recurring charges', 'subscriptions', 'recurring', 'monthly charges', 'repeating charges']},
    {'id': 'cat:', 'title': 'One category over time', 'default': False, 'param': 'category',
     'words': ['over time', 'by month', 'monthly', 'trend', 'history']},
    {'id': 'gwEnergyCard', 'title': 'Energy prices', 'default': False,
     'words': ['energy prices', 'gas prices', 'electricity price', 'natural gas', 'utility prices', 'eia', 'fuel prices']},
    {'id': 'gwPictureCard', 'title': 'What Groundwork has concluded', 'default': False,
     'words': ['working picture', 'what groundwork has concluded', 'conclusions', 'what you know about me',
               'flexible', 'protected']},
]
_CATALOGUE_BY_ID = {e['id']: e for e in TILE_CATALOGUE if not e.get('param')}


def _catalogue_entry(tile_id):
    """R2: a tile id is a catalogue id, or the one parameterised shape 'cat:<category>' - nothing else."""
    if tile_id in _CATALOGUE_BY_ID:
        return _CATALOGUE_BY_ID[tile_id]
    if isinstance(tile_id, str) and tile_id.startswith('cat:') and 0 < len(tile_id) - 4 <= 80:
        return {'id': tile_id, 'title': tile_id[4:] + ' over time', 'default': False, 'param': 'category'}
    return None


def _category_months(session, name, months=12):
    """Complete ledger months, and this category's spending in each month it appears (gaps stay gaps)."""
    today = date.today()
    start = today.replace(day=1)
    cutoff = start - timedelta(days=30 * months)
    held = sorted({r[0] for r in session.query(func.strftime('%Y-%m', Transaction.date)).filter(
        Transaction.type == 'debit', Transaction.date >= cutoff, Transaction.date < start).distinct().all() if r[0]})
    rows = session.query(func.strftime('%Y-%m', Transaction.date), func.sum(Transaction.amount)).join(
        Category, Transaction.category_id == Category.id).filter(
        func.lower(Category.name) == name.lower(), Transaction.type == 'debit',
        Transaction.date >= cutoff, Transaction.date < start).group_by(func.strftime('%Y-%m', Transaction.date)).all()
    seen = {m: round(float(v or 0), 2) for m, v in rows if m}
    return held, seen
assert tuple(e['id'] for e in TILE_CATALOGUE if e['default']) == DASHBOARD_TILES   # one list, not two (R1)
_REQUEST_MAX_CHARS = 200        # R5
_REQUEST_MAX_COUNT = 50         # R5
_ASK_STOP = {'show', 'me', 'my', 'the', 'a', 'an', 'of', 'in', 'on', 'to', 'for', 'see', 'view', 'tile', 'dashboard',
             'please', 'i', 'want', 'would', 'like', 'what', 'how', 'is', 'are', 'and', 'with', 'can', 'you', 'add',
             'do', 'have', 'it', 'be', 'all'}


def _tile_evidence(session, tile_id):
    """K3 / R3: whether the record backs a catalogue tile now, and if not, what it needs - in the user's terms."""
    if tile_id == 'gwNetWorthTrendCard':
        n = len(_snapshots_by_month(session)[0])      # item 38: months with figures, never an all-zero record
        return (n >= 2, None if n >= 2 else
                f'Net worth over time needs at least two net worth snapshots; you have {n}.')
    if tile_id == 'gwFundsCard':
        from core.database import SinkingFund
        n = session.query(SinkingFund).filter_by(is_active=True).count()
        return (n >= 1, None if n else 'Savings funds needs at least one savings fund; you have none yet.')
    if tile_id == 'gwRecurringCard':
        n = len(trim_candidates(session))
        return (n >= 1, None if n else
                'Recurring charges needs a charge that repeats for at least three months in your ledger; none found yet.')
    if isinstance(tile_id, str) and tile_id.startswith('cat:'):
        name = tile_id[4:]
        cat = session.query(Category).filter(func.lower(Category.name) == name.lower()).first()
        if not cat:
            return False, f'There is no category called {name} in your ledger.'
        held, seen = _category_months(session, cat.name)
        n = len(seen)
        return (n >= 3, None if n >= 3 else
                f'{cat.name} over time needs {cat.name} in at least three recorded months; it appears in {n}.')
    if tile_id == 'gwEnergyCard':
        e = _energy_on_record(session)
        return (bool(e), None if e else 'Energy prices needs an EIA price on record; the Budget page fetches them.')
    if tile_id == 'gwPictureCard':
        st = willingness_state(session)
        n = sum(1 for r in st['readings'] if r['stance'] in ('flexible', 'sacred') or r['reason'] in ('probation', 'break'))
        n += len(st['current'])
        return (n >= 1, None if n else 'What Groundwork has concluded needs at least one conclusion or statement; there are none yet.')
    return True, None            # the default tiles hide themselves when the record has nothing for them


def _energy_on_record(session):
    """The EIA prices already in the cache - read only; the dashboard fetches nothing (as item 29's I1)."""
    out = {}
    state = ''
    row = _get_setting(session, 'home_state')
    if row and row.value:
        state = row.value.strip().upper()[:2]
    for kind, area, label, unit in (('elec', state or 'US', 'Electricity', 'c/kWh'),
                                    ('ng', ('S' + state) if state else 'NUS', 'Natural gas', '$/MCF')):
        c = _dashboard_json(session, f'utility_price_{kind}_{area}', None)
        if c and c.get('price') is not None:
            out[kind] = {'label': label, 'price': c['price'], 'period': c.get('period') or '',
                         'area': c.get('area_name') or ('U.S.' if area in ('US', 'NUS') else state), 'unit': unit}
    g_ = _dashboard_json(session, 'gas_price_cache', None)
    if g_ and g_.get('price') is not None:
        out['gasoline'] = {'label': 'Gasoline', 'price': g_['price'], 'period': g_.get('period') or '',
                           'area': 'U.S.', 'unit': '$/gal'}
    return out


def match_tile_request(text, categories=()):
    """K2: the request only MATCHES - by its words against each entry's title and plain words, and nothing else.

    A phrase from the entry found in the request scores 3; a shared content word scores 1. The best entry wins if it
    scores at least 2. Nothing about the user's history ranks anything (item 22's rule).
    """
    t = ' '.join(re.findall(r"[a-z0-9-]+", (text or '').lower()))
    words = {w for w in t.split() if w not in _ASK_STOP}
    best, best_score = None, 0
    # A category the user's own ledger names, said in the request, is the parameterised entry (R2's one shape).
    # It competes on the same scale rather than winning outright: with a category called "Gas", the request
    # "gas prices" still means the energy prices tile (its own phrase plus two shared words outscore one name).
    for name in sorted(categories or (), key=lambda n: -len(n)):
        n_ = ' '.join(re.findall(r"[a-z0-9-]+", name.lower()))
        if n_ and ' ' + n_ + ' ' in ' ' + t + ' ':
            score = 3 + len(n_.split())
            if score > best_score:
                best = {'id': 'cat:' + name, 'title': name + ' over time', 'default': False, 'param': 'category'}
                best_score = score
            break
    for e in TILE_CATALOGUE:
        if e.get('param'):
            continue
        phrases = [e['title'].lower()] + e['words']
        score = sum(3 for ph in phrases if ' ' + ph + ' ' in ' ' + t + ' ')
        vocab = {w for ph in phrases for w in ph.split() if w not in _ASK_STOP}
        score += len(words & vocab)
        if score >= best_score and (score > best_score or (best or {}).get('param')):   # a tie goes to the entry
            best, best_score = e, score
    return best if best_score >= 2 else None


def _layout(session):
    lay = _dashboard_json(session, 'dashboard_layout', {})
    return {'order': lay.get('order', []), 'pinned': lay.get('pinned', []), 'hidden': lay.get('hidden', []),
            'added': [a for a in lay.get('added', []) if _catalogue_entry(a)]}


def _user_tiles(layout):
    """The tiles this user has: the defaults plus the catalogue entries they added (R1)."""
    return list(DASHBOARD_TILES) + [a for a in layout['added'] if a not in DASHBOARD_TILES]


MODEL_MATCH_TIMEOUT_S = 12      # R7: the model never holds the request longer than this
def _model_ready():
    """Is the in-app model loaded and answering? (ENGINE_REPLACEMENT.md) Asked of the engine itself - no probe, no wait.

    Found building item 28: with AI on but no model running, every unmatched request waited out the full timeout. A
    request costs nothing extra when there is no model: the engine's state says so at once.
    """
    from core import engine
    return engine.status()['state'] == 'ready'


def model_match_tile(text):
    """K2 / R7: when the search finds nothing, the local model may pick ONE catalogue id - and nothing else.

    It is shown the ids and titles and the request, and must answer with exactly one id or 'none'. Anything else -
    a sentence, two ids, a parameterised id, a timeout, no model - is 'none'. It never writes a figure, a title or a
    sentence the user sees: the entry's own title and engine do that.
    """
    if not _ai_is_enabled() or not _model_ready():
        return None
    ids = [e for e in TILE_CATALOGUE if not e.get('param')]
    system = ('You match a request to one dashboard tile. Reply with exactly one id from the list, or the single '
              'word none. No other words.')
    user = 'Tiles:\n' + '\n'.join(f"{e['id']}: {e['title']}" for e in ids) + f'\n\nRequest: {text}'
    import threading
    box = {}

    @copy_current_request_context
    def _call():
        try:
            box['out'] = _ai_complete_text(system, user, max_tokens=12)
        except Exception as ex:          # a failing model is 'none', never an error the user sees
            box['err'] = ex

    th = threading.Thread(target=_call, daemon=True)
    th.start()
    th.join(MODEL_MATCH_TIMEOUT_S)
    answer = (box.get('out') or '').strip()
    return _CATALOGUE_BY_ID.get(answer) if not th.is_alive() and answer in _CATALOGUE_BY_ID else None


@dashboard_bp.route('/ask', methods=['POST'])
@require_json
def dashboard_ask():
    """K2-K4: match a typed request to the catalogue; the user confirms with /add. No match is kept as their words."""
    text = str((request.json or {}).get('text') or '').strip()[:_REQUEST_MAX_CHARS]
    if not text:
        return err('type what you would like to see')
    with db_session() as session:
        cats = [c for (c,) in session.query(Category.name).join(Transaction, Transaction.category_id == Category.id)
                .filter(Transaction.type == 'debit').distinct().all() if c]
    e = match_tile_request(text, cats) or model_match_tile(text)
    with db_session() as session:
        if e:
            ok_, needs = _tile_evidence(session, e['id'])
            shown = e['id'] in _user_tiles(_layout(session)) and e['id'] not in _layout(session)['hidden']
            return ok({'match': {'id': e['id'], 'title': e['title'], 'shown': shown}, 'backed': ok_, 'needs': needs})
        reqs = _dashboard_json(session, 'dashboard_tile_requests', [])
        reqs.append({'text': text, 'at': datetime.now().isoformat(timespec='seconds')})
        reqs = reqs[-_REQUEST_MAX_COUNT:]
        _dashboard_store(session, 'dashboard_tile_requests', reqs)
        session.commit()
        return ok({'match': None, 'kept': True, 'requests': reqs})


@dashboard_bp.route('/add', methods=['POST'])
@require_json
def dashboard_add_tile():
    """The user's confirmation. R2: only a catalogue id - nothing else, parameterised or not, becomes a tile.
    R6: the server appends to the LATEST stored layout, so two quick additions cannot overwrite each other."""
    tile_id = (request.json or {}).get('id')
    if not _catalogue_entry(tile_id):
        return err('not a tile Groundwork can show')
    with db_session() as session:
        lay = _layout(session)
        if tile_id in DASHBOARD_TILES:
            lay['hidden'] = [h for h in lay['hidden'] if h != tile_id]      # asking for a hidden default shows it
        else:
            backed, needs = _tile_evidence(session, tile_id)
            if not backed:
                return err(needs, 409)
            if tile_id not in lay['added']:
                lay['added'].append(tile_id)
        _dashboard_store(session, 'dashboard_layout', lay)
        session.commit()
        return ok(lay)


@dashboard_bp.route('/requests/delete', methods=['POST'])
@require_json
def dashboard_delete_request():
    """K4: the user may delete their own kept request. Nothing else ever reads these but /prefs, to show them."""
    body = request.json or {}
    with db_session() as session:
        reqs = [r for r in _dashboard_json(session, 'dashboard_tile_requests', [])
                if not (r.get('at') == body.get('at') and r.get('text') == body.get('text'))]
        _dashboard_store(session, 'dashboard_tile_requests', reqs)
        session.commit()
        return ok({'requests': reqs})


@dashboard_bp.route('/tile/funds', methods=['GET'])
def dashboard_tile_funds():
    """Savings funds and their pace - the same answer as /api/sinking-funds/pace (post-break only, item 25)."""
    with db_session() as session:
        backed, needs = _tile_evidence(session, 'gwFundsCard')
    if not backed:
        return ok({'backed': False, 'needs': needs})
    r = sinking_funds_pace()
    resp = r[0] if isinstance(r, tuple) else r
    return ok({'backed': True, 'funds': ((resp.get_json() or {}).get('data') or {}).get('funds', [])})


@dashboard_bp.route('/tile/recurring', methods=['GET'])
def dashboard_tile_recurring():
    """Recurring charges, at what each costs per MONTH (trim_candidates' own rules)."""
    with db_session() as session:
        backed, needs = _tile_evidence(session, 'gwRecurringCard')
        if not backed:
            return ok({'backed': False, 'needs': needs})
        items = [{'name': c['name'], 'monthly': c['monthly'], 'category': c.get('category')}
                 for c in trim_candidates(session)]
        return ok({'backed': True, 'items': items})


@dashboard_bp.route('/tile/category', methods=['GET'])
def dashboard_tile_category():
    """One category over time: the months the ledger holds, and this category's spending where it appears."""
    name = (request.args.get('name') or '').strip()
    with db_session() as session:
        backed, needs = _tile_evidence(session, 'cat:' + name)
        if not backed:
            return ok({'backed': False, 'needs': needs})
        cat = session.query(Category).filter(func.lower(Category.name) == name.lower()).first()
        held, seen = _category_months(session, cat.name)
        return ok({'backed': True, 'category': cat.name,
                   'months': [{'month': m, 'amount': seen.get(m)} for m in held]})


@dashboard_bp.route('/tile/energy', methods=['GET'])
def dashboard_tile_energy():
    with db_session() as session:
        backed, needs = _tile_evidence(session, 'gwEnergyCard')
        return ok({'backed': backed, 'needs': needs, 'prices': _energy_on_record(session) if backed else {}})


@dashboard_bp.route('/tile/picture', methods=['GET'])
def dashboard_tile_picture():
    """What Groundwork has concluded - the working picture's own readings and the user's statements, summarised."""
    with db_session() as session:
        backed, needs = _tile_evidence(session, 'gwPictureCard')
        if not backed:
            return ok({'backed': False, 'needs': needs})
        st = willingness_state(session)
        claims = [{'category': r['category'], 'stance': r['stance'], 'reason': r['reason']} for r in st['readings']
                  if r['stance'] in ('flexible', 'sacred') or r['reason'] in ('probation', 'break')]
        said = [{'category': d['category'], 'stance': d['stance'], 'said_at': d['said_at']} for d in st['current']]
        return ok({'backed': True, 'claims': claims, 'said': said})


@dashboard_bp.route('/tile/net-worth', methods=['GET'])
def dashboard_tile_net_worth():
    """The first catalogue entry beyond the seven: net worth over time, from the user's own snapshots.
    R3: when the record stops backing it, the tile says what it needs instead of vanishing or drawing broken."""
    with db_session() as session:
        backed, needs = _tile_evidence(session, 'gwNetWorthTrendCard')
        if not backed:
            return ok({'backed': False, 'needs': needs})
        snaps = _snapshots_by_month(session)[0]       # item 38 P4: one per month, with figures
        return ok({'backed': True, 'points': [{'date': s.snapshot_date, 'net_worth': round(s.net_worth or 0, 2)}
                                              for s in snaps]})


# ── Item 26: utility bill estimates (gw 2.0/UTILITY_ESTIMATES.md, ruled 2026-10-01) - the natural gas slice ──────
#
# EIA's Short-Term Energy Outlook (STEO) gives each census division's residential natural gas price and heating
# degree days, history and forecast. Calls take ~10 s and STEO publishes monthly, so each series is cached for a
# week and fetched only from these routes, which the Budget page and the monthly report call - never the dashboard
# (item 29's I1). The estimate is DERIVED: recomputed on every read and never written to BudgetItem.amount, so the
# Willingness Layer never reads an estimate as the user's own budget edit (U3(a); Rob, 2026-10-01: totals keep the
# saved amount until a follow-up pass).

STEO_URL = ('https://api.eia.gov/v2/steo/data/?api_key={key}&frequency=monthly&data[0]=value'
            '&facets[seriesId][]={series}&start={start}&sort[0][column]=period&sort[0][direction]=asc&length=120')
STEO_FRESH_DAYS = 7
UTILITY_KINDS = ('gas', 'electric', 'gasoline', 'propane', 'heating_oil')


def _cache_rows(session, key, rows):
    """Cache freshly fetched EIA rows. The Budget page loads its estimate cards at once, and two of them can fetch the
    same series (degree days) on a cold cache: the second insert of the key fails. The rows are still good - this
    request returns them - and its session is rolled back, never left failed for the next query."""
    try:
        _dashboard_store(session, key, {'fetched_at': datetime.now().isoformat(), 'rows': rows})
        session.commit()
    except Exception as e:                       # noqa: BLE001 - another request cached the same rows first
        session.rollback()
        logging.info('eia cache write skipped (%s): %s', key, e)


def _steo(session, series, fetch=True):
    """One STEO series as {period: value}, from a week-fresh cache or, when `fetch`, from EIA. {} when unavailable."""
    key = f'steo_{series}'
    cached = _dashboard_json(session, key, None)
    if cached and cached.get('rows'):
        try:
            age = datetime.now() - datetime.fromisoformat(cached['fetched_at'])
        except (KeyError, ValueError, TypeError):
            age = timedelta(days=999)
        if age < timedelta(days=STEO_FRESH_DAYS) or not fetch:
            return cached['rows']
    if not fetch:
        return {}
    api_key = _get_eia_api_key()
    if not api_key:
        return (cached or {}).get('rows', {})
    try:
        import urllib.request
        import urllib.parse
        start = f'{date.today().year - 3}-01'
        from core import egress                    # item 8: the one door out
        url = STEO_URL.format(key=urllib.parse.quote(api_key), series=urllib.parse.quote(series), start=start)
        data = egress.get_json(url, timeout=30)
        rows = {x['period']: float(x['value']) for x in ((data.get('response') or {}).get('data') or [])
                if x.get('period') and x.get('value') not in (None, '')}
        if rows:
            _cache_rows(session, key, rows)
            return rows
    except Exception as e:
        logging.info('steo fetch failed (%s): %s', series, e)
    return (cached or {}).get('rows', {})


def _gas_bills(session, lag):
    """The user's natural gas bills: debits in the Gas category, summed by the month PAID, each moved to its service
    month (`lag` months earlier; Rob: gas is billed a month behind). Months with no bill are absent, never zero."""
    return _utility_bills(session, 'gas', lag)


def _utility_bills(session, category, lag):
    """A utility's bills by service month, from debits in its own category (Gas, Electric)."""
    from core.utility_estimate import service_month
    rows = session.query(func.strftime('%Y-%m', Transaction.date), func.sum(Transaction.amount)).join(
        Category, Transaction.category_id == Category.id).filter(
        func.lower(Category.name) == category, Transaction.type == 'debit').group_by(
        func.strftime('%Y-%m', Transaction.date)).order_by(func.strftime('%Y-%m', Transaction.date)).all()
    return [{'month': service_month(m, lag), 'paid_month': m, 'amount': round(float(v or 0), 2)} for m, v in rows if m and v]


def _month_add(m, k):
    y, mo = int(m[:4]), int(m[5:7]) + k
    while mo > 12:
        y, mo = y + 1, mo - 12
    while mo <= 0:
        y, mo = y - 1, mo + 12
    return f'{y}-{mo:02d}'


def gas_estimate(session, fetch=True, today=None):
    """Item 26's natural gas estimate for the bill paid next month, with every figure it rests on."""
    from core import utility_estimate as ue
    today = today or date.today()
    prefs = _dashboard_json(session, 'utility_estimates', {})
    lag = int((prefs.get('gas') or {}).get('lag', 1))
    optin = bool((prefs.get('gas') or {}).get('on'))
    row = _get_setting(session, 'home_state')
    reg = ue.region(row.value if row and row.value else '')
    prices = _steo(session, ue.steo_series('ng_price', reg), fetch)
    hdds = _steo(session, ue.steo_series('hdd', reg), fetch)
    bills = _gas_bills(session, lag)
    this_month = today.strftime('%Y-%m')
    next_service = this_month                       # the bill paid next month pays for this month
    prev_service = _month_add(this_month, -1)
    item = session.query(BudgetItem).filter(func.lower(BudgetItem.category) == 'natural gas', BudgetItem.is_active == True).first()  # noqa: E712  (item 84: was 'gas')
    out = {'kind': 'gas', 'region': reg, 'optin': optin, 'lag': lag,
           'saved_amount': round(float(item.amount), 2) if item and item.amount is not None else None,
           'bills': len(bills), 'has_eia': bool(prices and hdds)}
    if not prices or not hdds:
        return {**out, 'estimate': None,
                'needs': 'EIA\'s outlook for your region could not be loaded; it is fetched from this page when online.'}
    choice = ue.choose(bills, prices, hdds)
    nxt = ue.estimate(choice, bills, next_service, prices.get(next_service), hdds.get(next_service), prices)
    prv = ue.estimate(choice, bills, prev_service, prices.get(prev_service), hdds.get(prev_service), prices)
    out.update({
        'choice': {k: v for k, v in choice.items() if k != 'model'},
        'estimate': nxt, 'previous': prv, 'split': ue.split_vs_last_year(choice, nxt, bills, prices, hdds),
        'forecast': {'month': next_service, 'price': prices.get(next_service), 'prev_month': prev_service,
                     'prev_price': prices.get(prev_service), 'hdd': hdds.get(next_service)},
        'last_bill': bills[-1] if bills else None,
    })
    return out


def electric_estimate(session, fetch=True, today=None):
    """Item 26's electricity estimate (U8's second slice): the same shape as gas, with cooling degree days."""
    from core import utility_estimate as ue
    today = today or date.today()
    prefs = _dashboard_json(session, 'utility_estimates', {})
    lag = int((prefs.get('electric') or {}).get('lag', 1))
    optin = bool((prefs.get('electric') or {}).get('on'))
    row = _get_setting(session, 'home_state')
    reg = ue.region(row.value if row and row.value else '')
    cents = _steo(session, ue.steo_series('elec_price', reg), fetch)
    prices = {m: v / 100.0 for m, v in cents.items()}          # cents/kWh -> $/kWh, the unit on the arithmetic
    hdds = _steo(session, ue.steo_series('hdd', reg), fetch)
    cdds = _steo(session, ue.steo_series('cdd', reg), fetch)
    bills = _utility_bills(session, 'electric', lag)
    this_month = today.strftime('%Y-%m')
    prev_service = _month_add(this_month, -1)
    item = session.query(BudgetItem).filter(func.lower(BudgetItem.category) == 'electric', BudgetItem.is_active == True).first()  # noqa: E712
    out = {'kind': 'electric', 'region': reg, 'optin': optin, 'lag': lag,
           'saved_amount': round(float(item.amount), 2) if item and item.amount is not None else None,
           'bills': len(bills), 'has_eia': bool(prices and hdds and cdds)}
    if not prices or not hdds or not cdds:
        return {**out, 'estimate': None,
                'needs': 'EIA\'s outlook for your region could not be loaded; it is fetched from this page when online.'}
    choice = ue.choose_electric(bills, prices, hdds, cdds)
    nxt = ue.estimate_electric(choice, bills, this_month, prices.get(this_month), hdds.get(this_month), cdds.get(this_month), prices)
    prv = ue.estimate_electric(choice, bills, prev_service, prices.get(prev_service), hdds.get(prev_service),
                               cdds.get(prev_service), prices)
    out.update({
        'choice': {k: v for k, v in choice.items() if k != 'model'},
        'estimate': nxt, 'previous': prv, 'split': ue.split_electric(choice, nxt, bills, prices, hdds, cdds),
        'forecast': {'month': this_month, 'price': cents.get(this_month), 'prev_month': prev_service,
                     'prev_price': cents.get(prev_service), 'hdd': hdds.get(this_month), 'cdd': cdds.get(this_month)},
        'last_bill': bills[-1] if bills else None,
    })
    return out


EIA_WEEKLY_GAS_URL = ('https://api.eia.gov/v2/petroleum/pri/gnd/data/?api_key={key}&frequency=weekly&data[0]=value'
                      '&facets[product][]={product}&facets[duoarea][]={area}&sort[0][column]=period'
                      '&sort[0][direction]=desc&length=130')
WEEKLY_FRESH_DAYS = 3


def _eia_weekly_gas(session, area, fetch=True, product='EPMR'):
    """EIA's weekly retail price for an area, {week 'YYYY-MM-DD': $/gal}, cached three days. product: EPMR regular
    gasoline (item 26), EPD2D No. 2 diesel (item 34 F1)."""
    key = f'eia_weekly_gas_{area}' if product == 'EPMR' else f'eia_weekly_{product}_{area}'
    cached = _dashboard_json(session, key, None)
    if cached and cached.get('rows'):
        try:
            age = datetime.now() - datetime.fromisoformat(cached['fetched_at'])
        except (KeyError, ValueError, TypeError):
            age = timedelta(days=999)
        if age < timedelta(days=WEEKLY_FRESH_DAYS) or not fetch:
            return cached['rows']
    if not fetch:
        return {}
    api_key = _get_eia_api_key()
    if not api_key:
        return (cached or {}).get('rows', {})
    try:
        import urllib.request
        import urllib.parse
        from core import egress                    # item 8: the one door out
        url = EIA_WEEKLY_GAS_URL.format(key=urllib.parse.quote(api_key), area=urllib.parse.quote(area), product=product)
        data = egress.get_json(url, timeout=30)
        rows = {x['period']: float(x['value']) for x in ((data.get('response') or {}).get('data') or [])
                if x.get('period') and x.get('value') not in (None, '')}
        if rows:
            _cache_rows(session, key, rows)
            return rows
    except Exception as e:
        logging.info('eia weekly gasoline fetch failed (%s): %s', area, e)
    return (cached or {}).get('rows', {})


def gasoline_estimate(session, fetch=True, today=None):
    """The vehicle-fuel estimate: typical monthly gallons from the user's fill-ups x EIA's latest weekly price.

    Item 26 U2 priced regular gasoline; item 34 F1 prices diesel by the same method when the household said its vehicle
    uses diesel (EIA's weekly diesel series: California's own, else the PADD region). The estimate keeps its id
    ('gasoline'), so the opt-in and the budget totals carry over; 'fuel' says which fuel it priced.
    """
    from core import utility_estimate as ue
    from core import household
    today = today or date.today()
    prefs = _dashboard_json(session, 'utility_estimates', {})
    optin = bool((prefs.get('gasoline') or {}).get('on'))
    row = _get_setting(session, 'home_state')
    reg = ue.region(row.value if row and row.value else '')
    fuel = 'diesel' if household.current(session, 'vehicle_fuel') == 'diesel' else 'gasoline'
    area = ue.diesel_area(reg) if fuel == 'diesel' else ue.gasoline_area(reg)
    weekly = _eia_weekly_gas(session, area['duoarea'], fetch, product=ue.EIA_PRODUCT[fuel])
    fills = [{'date': d.isoformat(), 'amount': float(a)} for d, a in session.query(Transaction.date, Transaction.amount).join(
        Category, Transaction.category_id == Category.id).filter(
        func.lower(Category.name) == 'gasoline / diesel', Transaction.type == 'debit').order_by(Transaction.date).all() if d and a]
    months = ue.fuel_months(fills, weekly, today.strftime('%Y-%m')) if weekly else {}
    item = session.query(BudgetItem).filter(func.lower(BudgetItem.category) == 'gasoline / diesel', BudgetItem.is_active == True).first()  # noqa: E712  (item 84)
    est = ue.estimate_gasoline(months, weekly)
    return {'kind': 'gasoline', 'fuel': fuel, 'region': reg, 'area': area, 'optin': optin, 'lag': 0,
            'saved_amount': round(float(item.amount), 2) if item and item.amount is not None else None,
            'bills': len(fills), 'has_eia': bool(weekly), 'months': months, 'estimate': est,
            'needs': est.get('needs') if est.get('method') == 'none' else None}


EIA_WEEKLY_RES_URL = ('https://api.eia.gov/v2/petroleum/pri/wfr/data/?api_key={key}&frequency=weekly&data[0]=value'
                      '&facets[product][]={product}&facets[duoarea][]={area}&facets[process][]=PRS'
                      '&sort[0][column]=period&sort[0][direction]=desc&length=130')


def _eia_weekly_heating(session, area, product, fetch=True):
    """EIA's weekly RESIDENTIAL heating-fuel price for an area, {week: $/gal}, cached three days (item 34 F2-F4).

    product: EPLLPA propane, EPD2F heating oil. Only process PRS (residential): the same EIA series also carries
    wholesale (PWR) prices, which are not what a household pays. EIA collects these October to March only."""
    key = f'eia_weekly_res_{product}_{area}'
    cached = _dashboard_json(session, key, None)
    if cached and cached.get('rows'):
        try:
            age = datetime.now() - datetime.fromisoformat(cached['fetched_at'])
        except (KeyError, ValueError, TypeError):
            age = timedelta(days=999)
        if age < timedelta(days=WEEKLY_FRESH_DAYS) or not fetch:
            return cached['rows']
    if not fetch:
        return {}
    api_key = _get_eia_api_key()
    if not api_key:
        return (cached or {}).get('rows', {})
    try:
        import urllib.request
        import urllib.parse
        from core import egress                    # item 8: the one door out
        url = EIA_WEEKLY_RES_URL.format(key=urllib.parse.quote(api_key), area=urllib.parse.quote(area), product=product)
        data = egress.get_json(url, timeout=30)
        rows = {x['period']: float(x['value']) for x in ((data.get('response') or {}).get('data') or [])
                if x.get('period') and x.get('value') not in (None, '') and x.get('process') in (None, 'PRS')}
        if rows:
            _cache_rows(session, key, rows)
            return rows
    except Exception as e:
        logging.info('eia weekly heating fetch failed (%s %s): %s', product, area, e)
    return (cached or {}).get('rows', {})


_DELIVERED_CATEGORY = {'propane': 'propane', 'heating_oil': 'heating oil'}
_DELIVERED_NEEDS = {
    'too_few': 'three deliveries priced in EIA\'s heating season (October to March), each after another delivery',
    'no_fit': 'deliveries spread across different weather',
    'no_heating_slope': 'deliveries that rise with the cold',
    'no_better_than_average': 'deliveries that follow the weather more closely than one steady daily rate',
    'weather_share_too_small': 'deliveries in which the weather explains at least 30% of a year\'s use',
    'out_of_season': 'a current EIA price (under two weeks old); EIA publishes them weekly in the heating season, '
                     'October to March',
    'no_degree_days': 'EIA\'s degree days for your region',
}


def delivered_estimate(session, fuel, fetch=True, today=None):
    """Item 34 F2-F4: a propane or heating oil estimate from the user's own deliveries (FUEL_PRICING.md s7).

    Each delivery's dollars become gallons at EIA's weekly residential price for that week; the gallons delivered at
    one fill are what was used since the fill before. The weather fit is used only if it passes the F2 guard (three
    priced intervals, beats one daily rate by 25% held out, rises with the cold, weather >= 30% of a year's use);
    otherwise there is no estimate, and the card says which test it did not pass. Out of season (F3) there is no
    current figure: last season's price is shown as last season's, never as this month's, and never a zero.
    """
    from core import utility_estimate as ue
    today = today or date.today()
    prefs = _dashboard_json(session, 'utility_estimates', {})
    optin = bool((prefs.get(fuel) or {}).get('on'))
    row = _get_setting(session, 'home_state')
    reg = ue.region(row.value if row and row.value else '')
    area = ue.delivered_area(reg, fuel)
    cat = _DELIVERED_CATEGORY[fuel]
    weekly = _eia_weekly_heating(session, area['duoarea'], ue.DELIVERED_PRODUCT[fuel], fetch)
    hdds = _steo(session, ue.steo_series('hdd', reg), fetch)
    deliveries = [{'date': d.isoformat(), 'amount': float(a)} for d, a in session.query(Transaction.date, Transaction.amount).join(
        Category, Transaction.category_id == Category.id).filter(
        func.lower(Category.name) == cat, Transaction.type == 'debit').order_by(Transaction.date).all() if d and a]
    item = session.query(BudgetItem).filter(func.lower(BudgetItem.category) == cat, BudgetItem.is_active == True).first()  # noqa: E712
    this_month = today.strftime('%Y-%m')
    out = {'kind': fuel, 'fuel': fuel, 'region': reg, 'area': area, 'optin': optin, 'lag': 0,
           'saved_amount': round(float(item.amount), 2) if item and item.amount is not None else None,
           'bills': len(deliveries), 'has_eia': bool(weekly and hdds)}
    if not weekly or not hdds:
        return {**out, 'estimate': None,
                'needs': 'EIA\'s residential prices and degree days for your region could not be loaded; they are '
                         'fetched from this page when online.'}
    year = [_month_add(this_month, -i) for i in range(1, 13)]
    year_hdd = sum(hdds[m] for m in year) if all(hdds.get(m) is not None for m in year) else None
    intervals, unpriced = ue.delivered_intervals(deliveries, weekly, hdds)
    choice = (ue.choose_delivered(intervals, year_hdd) if year_hdd is not None
              else {'method': 'none', 'reason': 'no_degree_days', 'n': len(intervals)})
    est = ue.estimate_delivered(choice, this_month, hdds.get(this_month), weekly, today)
    if est.get('method') == 'none':
        est['needs'] = _DELIVERED_NEEDS.get(est.get('reason'), 'more deliveries')
    return {**out, 'choice': choice, 'estimate': est, 'intervals': len(intervals), 'unpriced': unpriced,
            'year_hdd': year_hdd, 'needs': est.get('needs')}


_HEAT_WORDS = {'propane': 'propane', 'heating_oil': 'heating oil', 'wood_pellets': 'wood or pellets', 'other': 'another fuel'}


def _municipal_ask(session, f):
    """Item 56 U2: ask what the municipal bill covers - once, where it matters - only when a Municipal Utilities
    charge exists and the question is unanswered. Never inferred from the amount or from other bills."""
    if f.get('municipal_covers'):
        return []
    cat = session.query(Category).filter(Category.name == 'Municipal Utilities').first()
    if not cat or not session.query(Transaction.id).filter(Transaction.category_id == cat.id).first():
        return []
    return ['municipal_covers']


def utility_applies(session, kind):
    """Whether an item 26 estimate applies to this household, from what it told Groundwork (ONBOARDING_REVISIT.md).

    The consumer of housing_status, electricity_included, heating_fuel, heating_payment and vehicle_fuel. Returns
    {'applies', 'why' (when it does not), 'ask' (unanswered facts that would settle it), 'assumes' (what is taken
    from the record while they are unanswered - said, never silent)}. An answer is never replaced by a default: an
    unanswered fuel is not natural gas - the estimate says it is reading the Gas category's bills as natural gas, and
    asks.
    """
    from core import household
    f = {k: household.current(session, k) for k in household.FACTS}
    ask = [] if f['home_state'] else ['home_state']
    if kind == 'gas':
        fuel, pay = f['heating_fuel'], f['heating_payment']
        if fuel in ('propane', 'heating_oil'):          # item 34: priced on its own card, from its own deliveries
            w = _HEAT_WORDS[fuel]
            return {'applies': False, 'why': f'You told us {w} heats your home, so there is no natural gas estimate; '
                                             f'{w} has its own estimate, from your deliveries.'}
        if fuel in _HEAT_WORDS:
            w = _HEAT_WORDS[fuel]
            return {'applies': False, 'why': f'You told us {w} heats your home. Groundwork does not price {w} yet, '
                                             f'so there is no natural gas estimate.'}
        if fuel == 'electric':
            return {'applies': False, 'why': 'You told us electricity heats your home, so heating is part of your '
                                             'electricity estimate, not a natural gas one.'}
        if fuel == 'included':
            return {'applies': False, 'why': 'You told us your rent includes heat, so there is no gas bill to estimate.'}
        if fuel == 'not_sure':
            return {'applies': False, 'why': 'You told us you are not sure what heats your home, so there is no '
                                             'natural gas estimate until you know.', 'ask': []}
        if pay in ('even_monthly', 'prepaid'):
            how = 'the same amount every month' if pay == 'even_monthly' else 'a prepaid contract'
            return {'applies': False, 'why': f'You told us you pay for heating with {how}. Those payments do not follow '
                                             f'the weather, so they cannot show how much gas you use - there is no estimate.'}
        if 'natural_gas' in (f['municipal_covers'] or '').split(','):     # item 56 U5
            return {'applies': False, 'why': 'Your natural gas is on your municipal utility bill with other services, so '
                                             'Groundwork can\'t separate it from the total - there is no natural gas estimate.'}
        ask += _municipal_ask(session, f)
        if fuel is None:
            return {'applies': True, 'ask': ask + ['heating_fuel'],
                    'assumes': 'Reading the bills in your Gas category as natural gas. Tell us what heats your home to be sure.'}
        return {'applies': True, 'ask': ask + ([] if pay else ['heating_payment'])}
    if kind in ('propane', 'heating_oil'):           # item 34 F2-F4: delivered heating fuel
        fuel, pay, w = f['heating_fuel'], f['heating_payment'], _HEAT_WORDS[kind]
        if fuel is not None and fuel != kind:
            other = _HEAT_WORDS.get(fuel) or {'natural_gas': 'natural gas', 'electric': 'electricity',
                                              'included': 'heat included in your rent', 'not_sure': None}.get(fuel)
            told = f'You told us {other} heats your home' if other else 'You told us you are not sure what heats your home'
            return {'applies': False, 'why': f'{told}. Groundwork estimates {w} only as the fuel that heats your home, '
                                             f'so there is no {w} estimate.', 'ask': []}
        if pay in ('even_monthly', 'prepaid'):
            how = 'the same amount every month' if pay == 'even_monthly' else 'a prepaid contract'
            return {'applies': False, 'why': f'You told us you pay for heating with {how}. Those payments do not follow '
                                             f'the weather, so they cannot show how much {w} you use - there is no estimate.'}
        if fuel is None:
            return {'applies': True, 'ask': ask + ['heating_fuel'],
                    'assumes': f'Reading your {w.capitalize()} deliveries as the fuel that heats your home. Tell us what '
                               f'heats your home to be sure.'}
        return {'applies': True, 'ask': ask + ([] if pay else ['heating_payment'])}
    if kind == 'electric':
        if f['housing_status'] == 'rent' and f['electricity_included'] == 'yes':
            return {'applies': False, 'why': 'You told us your rent includes electricity, so there is no electricity '
                                             'bill to estimate.'}
        if 'electricity' in (f['municipal_covers'] or '').split(','):     # item 56 U5
            return {'applies': False, 'why': 'Your electricity is on your municipal utility bill with other services, so '
                                             'Groundwork can\'t separate it from the total - there is no electricity estimate.'}
        return {'applies': True, 'ask': ask + _municipal_ask(session, f)}
    if kind == 'gasoline':
        v = f['vehicle_fuel']
        if v == 'electric':
            return {'applies': False, 'why': 'You told us your vehicle is electric, so there is no gasoline estimate; '
                                             'charging at home is part of your electricity bill.'}
        if v == 'none':
            return {'applies': False, 'why': 'You told us you have no vehicle fuel expense, so there is no gasoline estimate.'}
        if v == 'diesel':                      # item 34 F1: priced from EIA's weekly diesel series
            return {'applies': True, 'ask': ask}
        if v == 'other':
            return {'applies': False, 'why': 'You told us your vehicle uses another fuel. Groundwork prices regular '
                                             'gasoline only, so there is no estimate for it.'}
        if v is None:
            return {'applies': True, 'ask': ask + ['vehicle_fuel'],
                    'assumes': 'Reading your Gasoline / Diesel fill-ups as regular gasoline. Tell us what your vehicle uses to be sure.'}
        return {'applies': True, 'ask': ask}
    return {'applies': True, 'ask': ask}


_UTILITY_CATEGORY = {'gas': 'natural gas', 'electric': 'electric', 'gasoline': 'gasoline / diesel', 'propane': 'propane',   # item 84
                     'heating_oil': 'heating oil'}
_KIND_WORDS = {'gas': 'the natural gas estimate', 'electric': 'the electricity estimate', 'gasoline': 'the gasoline estimate',
               'propane': 'the propane estimate', 'heating_oil': 'the heating oil estimate'}


def _estimate_for(session, kind, fetch):
    """An item 26 estimate as its route answers it (the household's answers first, then the estimate)."""
    app = utility_applies(session, kind)
    if not app['applies']:
        return {'kind': kind, 'not_applicable': app['why'], 'estimate': None}
    if kind == 'gas':
        return gas_estimate(session, fetch=fetch)
    if kind == 'electric':
        return electric_estimate(session, fetch=fetch)
    if kind in _DELIVERED_CATEGORY:
        return delivered_estimate(session, kind, fetch=fetch)
    return gasoline_estimate(session, fetch=fetch)


def budget_month_amounts(session, fetch=False, today=None):
    """Every expense row's amount for this month (BUDGET_MONTH_AMOUNT.md, M1-M3, M5), keyed by budget item id.

    {'month_amount', 'month_source' ('estimate' | 'saved'), 'month_why', 'kind'}. The saved amount is never changed:
    this is derived on every read, and no write path sends it. Only a row whose kind the user FOLLOWS can differ; a
    followed estimate with no figure for the bill paid this month uses the saved amount and says why. fetch=False:
    the totals never wait on EIA - they use what the Budget page's estimate cards last fetched.
    """
    from core import budget_month as bm, household
    this_month = (today or date.today()).strftime('%Y-%m')
    prefs = _dashboard_json(session, 'utility_estimates', {})
    picked = {}
    for kind in UTILITY_KINDS:
        if (prefs.get(kind) or {}).get('on'):
            picked[kind] = bm.pick_estimate(_estimate_for(session, kind, fetch), kind, this_month)
    yearly = _yearly_follow_amounts(session, today)                # item 106 Y6: followed yearly projections
    out = {}
    for item in session.query(BudgetItem).filter_by(is_active=True, type='expense').all():
        kind = next((k for k, c in _UTILITY_CATEGORY.items() if (item.category or '').lower() == c), None)
        followed = kind in picked
        est, why = picked.get(kind, (None, None))
        amt, src = bm.month_amount(item.amount, followed, est)
        words = _KIND_WORDS.get(kind)
        if kind == 'gasoline' and household.current(session, 'vehicle_fuel') == 'diesel':
            words = 'the diesel estimate'
        bill = session.query(BillReading).filter(BillReading.budget_item_id == item.id, BillReading.use_for_month == True,   # noqa: E712
                                                 BillReading.amount.isnot(None), BillReading.due_date.isnot(None)) \
            .order_by(BillReading.id.desc()).first()
        if bill and bill.due_date.strftime('%Y-%m') == this_month:
            out[item.id] = {'month_amount': round(bill.amount, 2), 'month_source': 'bill', 'kind': None, 'month_why': None,
                            'month_from': f"the bill read from {bill.source_host or 'its website'} on {bill.read_at:%b} {bill.read_at.day}",
                            'month_for': None}
            continue
        if not followed and item.id in yearly:
            y = yearly[item.id]
            out[item.id] = {'month_amount': y['amount'], 'month_source': 'yearly', 'kind': None, 'month_why': None,
                            'month_from': f"{y['payee']}'s yearly step, about {y['pct'] * 100:.1f}% from "
                                          f"{date(int(y['month'][:4]), int(y['month'][5:7]), 1):%B %Y}",
                            'month_for': None}
            continue
        out[item.id] = {'month_amount': amt, 'month_source': src, 'kind': kind if followed else None,
                        'month_why': (f'{words} is followed, but {why}' if followed and src == 'saved' and why
                                      else None),
                        'month_from': words if followed and src == 'estimate' else None,
                        # the service month of the bill paid this month (gas/electric); none for fill-ups
                        'month_for': ((est or {}).get('month') if followed and src == 'estimate'
                                      and kind in ('gas', 'electric') else None)}
    return out


@budget_bp.route('/month-amounts', methods=['GET'])
def budget_month_amounts_route():
    """This month's figure for every expense row - read by the Budget page after a change; never written."""
    with db_session() as session:
        return ok({str(k): v for k, v in budget_month_amounts(session).items()})


def _estimate_pref(prefs, kind):
    """The user's own choices for one estimate card: {'follow': 'follow' | 'not_follow' | None, 'hidden': bool}.
    ('follow', not 'choice': each estimate's 'choice' is already its weather-fit decision.)

    None means they have not chosen - never read as 'do not follow' (an unanswered question is not a default), though
    until they choose, the saved amount sets the totals. Hidden is a VIEW choice only: it says nothing about whether
    they follow or track it (Rob: maybe in the off season they see no need to view it), so a followed estimate stays
    followed while its card is hidden."""
    p = prefs.get(kind) or {}
    choice = p.get('choice') or ('follow' if p.get('on') else None)
    return {'follow': choice, 'hidden': bool(p.get('hidden'))}


@budget_bp.route('/utility-estimate/<kind>', methods=['GET'])
def budget_utility_estimate(kind):
    if kind not in UTILITY_KINDS:
        return err('not a utility Groundwork estimates yet', 404)
    with db_session() as session:
        app = utility_applies(session, kind)
        if not app['applies']:
            # What the household told Groundwork settles it: no EIA fetch, no estimate - and the reason, said plainly.
            cat = _UTILITY_CATEGORY[kind]
            n = session.query(func.count(Transaction.id)).join(Category, Transaction.category_id == Category.id).filter(
                func.lower(Category.name) == cat, Transaction.type == 'debit').scalar() or 0
            item = session.query(BudgetItem).filter(func.lower(BudgetItem.category) == cat,
                                                    BudgetItem.is_active == True).first()  # noqa: E712
            return ok({'kind': kind, 'optin': False, 'estimate': None, 'not_applicable': app['why'],
                       'bills': n, 'saved_amount': round(float(item.amount), 2) if item and item.amount is not None else None,
                       'ask': app.get('ask', []),
                       # still the user's choices: a follow made before they moved stays theirs to change (Rob)
                       'lag': int(((_dashboard_json(session, 'utility_estimates', {}) or {}).get(kind) or {}).get('lag', 1)),
                       **_estimate_pref(_dashboard_json(session, 'utility_estimates', {}), kind)})
        out = _estimate_for(session, kind, True)
        out.update(ask=app.get('ask', []), assumes=app.get('assumes'),
                   **_estimate_pref(_dashboard_json(session, 'utility_estimates', {}), kind))
        rows = [v for v in budget_month_amounts(session).values() if v['kind'] == kind]
        out['budget_uses'] = {'in_totals': bool(rows) and all(v['month_source'] == 'estimate' for v in rows),
                              'month_amount': rows[0]['month_amount'] if rows else None,
                              'month_for': rows[0]['month_for'] if rows else None,
                              'why': rows[0]['month_why'] if rows else None}
        return ok(out)


@budget_bp.route('/utility-estimate/optin', methods=['POST'])
@require_json
def budget_utility_estimate_optin():
    """U3: the user's choices for an estimate card. Their saved amount is never touched.

    Each field is changed only when sent, so hiding a card keeps its follow choice and lag: 'choice' ('follow' |
    'not_follow'; 'on' true/false is the same choice, as earlier pages send it), 'lag' (0-2), 'hidden' (true/false)."""
    body = request.json or {}
    kind = body.get('kind')
    if kind not in UTILITY_KINDS:
        return err('not a utility Groundwork estimates yet')
    lag = body.get('lag')
    if lag is not None and (not isinstance(lag, int) or isinstance(lag, bool) or not 0 <= lag <= 2):
        return err('the billing lag is 0, 1 or 2 months')
    choice = body.get('choice')
    if choice is None and 'on' in body:
        choice = 'follow' if body.get('on') else 'not_follow'
    if choice not in (None, 'follow', 'not_follow'):
        return err('the choice is follow or not_follow')
    hidden = body.get('hidden')
    if hidden is not None and not isinstance(hidden, bool):
        return err('hidden is true or false')
    with db_session() as session:
        prefs = _dashboard_json(session, 'utility_estimates', {})
        cur = dict(prefs.get(kind) or {})
        cur.setdefault('lag', 1)
        if lag is not None:
            cur['lag'] = lag
        if choice is not None:
            cur['choice'], cur['on'] = choice, choice == 'follow'
        if hidden is not None:
            cur['hidden'] = hidden
        prefs[kind] = cur
        _dashboard_store(session, 'utility_estimates', prefs)
        session.commit()
        return ok(prefs)


@budget_bp.route('/detect-recurring', methods=['GET'])
def budget_detect_recurring():
    months = int(request.args.get('months', 6))
    with db_session() as session:
        return ok(detect_recurring_patterns(session, months=months))


@budget_bp.route('/detect-recurring/feedback', methods=['POST'])
@require_json
def budget_detect_recurring_feedback():
    """
    Phase H2 Feature 4's missing other half — dismissal was already real
    (session-only, see app.js's _recurringDismissed), but neither accepting
    nor dismissing a detected pattern was ever logged anywhere durable.
    Body: { merchant: str, avg_amount: float, confirmed: bool }.
    """
    body     = request.json
    merchant = (body.get('merchant') or '').strip()
    amount   = body.get('avg_amount')
    confirmed = bool(body.get('confirmed'))
    if not merchant:
        return err('merchant is required')
    with db_session() as session:
        log_historian_event(
            session, 'recurring_pattern_confirm' if confirmed else 'recurring_pattern_reject',
            actual_value=float(amount) if amount is not None else None,
            context={'merchant': merchant},
        )
        session.commit()
    return ok({'logged': True})


@budget_bp.route('/items', methods=['GET'])
def get_budget_items():
    with db_session() as session:
        items = session.query(BudgetItem).filter_by(is_active=True) \
                       .order_by(BudgetItem.type, BudgetItem.sort_order).all()
        return ok([{
            'id': i.id, 'type': i.type, 'name': i.name,
            'amount': i.amount, 'category': i.category,
        } for i in items])


@budget_bp.route('/items', methods=['POST'])
@require_json
def create_budget_item():
    body = request.json
    # Named before use. body['type'] on a request missing it is a KeyError, and
    # a KeyError here is a 500 - the app telling a caller it broke when what
    # happened is that the caller left a field out.
    for field in ('type', 'name', 'amount'):
        if body.get(field) in (None, ''):
            return err(f'{field} is required')
    try:
        amount = float(body['amount'])
    except (TypeError, ValueError):
        return err('amount must be a number')
    with db_session() as session:
        cat_name = (body.get('category') or '').strip()
        if cat_name:
            # Resolve or create the category, same pattern as transactions —
            # a Budget category is the same category, not a separate concept.
            cat = session.query(Category).filter(
                func.lower(Category.name) == cat_name.lower()
            ).first()
            if not cat:
                cat = Category(name=cat_name)
                if body.get('type') == 'income':
                    # item 71 amendment D2: an income line's new category is an income category under Income -
                    # created as a spending one, it hid the pay filed under it from every income figure
                    cat.type = 'income'
                    cat.parent_id = getattr(session.query(Category).filter(func.lower(Category.name) == 'income').first(), 'id', None)
                session.add(cat)
                session.flush()
            cat_name = cat.name  # normalize to existing casing if it matched

        item = BudgetItem(
            type=body['type'],
            name=body['name'],
            amount=amount,
            category=cat_name,
        )
        session.add(item)
        session.flush()
        session.commit()
        return ok({'id': item.id}, status=201)


@budget_bp.route('/items/<int:item_id>', methods=['PATCH'])
@require_json
def update_budget_item(item_id):
    body = request.json
    with db_session() as session:
        item = session.get(BudgetItem, item_id)
        if not item:
            return err('Not found', 404)
        if 'name'   in body: item.name   = body['name']
        if 'amount' in body:
            _old_amount = item.amount
            _new_amount = float(body['amount'])
            item.amount = _new_amount
            # Historian: an intentional budget-amount change by the user —
            # distinct from budget_variance_observed (automatic actual-vs-plan
            # drift). Only a real change against a known prior amount counts;
            # no category_id FK because budget items key category by name, not
            # a categories.id row (see create/update above).
            if _old_amount is not None and _new_amount != _old_amount:
                log_historian_event(
                    session, 'budget_adjusted',
                    expected_value=_old_amount, actual_value=_new_amount,
                    context={'budget_item_id': item.id, 'name': item.name,
                             'item_type': item.type},
                )
        if 'category' in body:
            cat_name = (body['category'] or '').strip()
            if cat_name:
                cat = session.query(Category).filter(
                    func.lower(Category.name) == cat_name.lower()
                ).first()
                if not cat:
                    cat = Category(name=cat_name)
                    if item.type == 'income':        # item 71 amendment D2, as on create
                        cat.type = 'income'
                        cat.parent_id = getattr(session.query(Category).filter(func.lower(Category.name) == 'income').first(), 'id', None)
                    session.add(cat)
                    session.flush()
                cat_name = cat.name
            item.category = cat_name
        session.commit()
        return ok({'id': item.id, 'type': item.type, 'name': item.name,
                    'amount': item.amount, 'category': item.category})


@budget_bp.route('/items/<int:item_id>', methods=['DELETE'])
def delete_budget_item(item_id):
    with db_session() as session:
        item = session.get(BudgetItem, item_id)
        if not item:
            return err('Not found', 404)
        session.delete(item)
        session.commit()
        return ok({'deleted': item_id})


@budget_bp.route('/plan', methods=['GET'])
def get_active_plan():
    with db_session() as session:
        plan = session.query(BudgetPlan).filter_by(is_active=True) \
                      .order_by(desc(BudgetPlan.created_at)).first()
        if not plan:
            return ok(None)

        months = [{
            'month_key':    m.month_key,
            'targets':      json.loads(m.targets or '{}'),
            'actuals':      json.loads(m.actuals or '{}'),
            'is_complete':  m.is_complete,
            'is_over':      m.is_over,
            'saved_amount': m.saved_amount,
            'coach_note':   m.coach_note,
        } for m in plan.months]

        return ok({
            'id':           plan.id,
            'goal_amount':  plan.goal_amount,
            'goal_months':  plan.goal_months,
            'start_month':  plan.start_month,
            'total_saved':  plan.total_saved,
            'streak_count': plan.streak_count,
            'months':       months,
        })


@budget_bp.route('/plan', methods=['POST'])
@require_json
def create_plan():
    body = request.json
    # Before the deactivation below, not after. This route retires the current
    # plan first and builds the new one second, so a missing field raised after
    # the retirement - and the only reason it did not cost anyone their active
    # plan is that the session is closed without a commit on the way out.
    # Validating first means not relying on that.
    for field in ('goal_amount', 'goal_months', 'start_month'):
        if body.get(field) in (None, ''):
            return err(f'{field} is required')
    try:
        goal_amount = float(body['goal_amount'])
        goal_months = int(body['goal_months'])
    except (TypeError, ValueError):
        return err('goal_amount and goal_months must be numbers')
    with db_session() as session:
        # Deactivate any existing plan
        for old in session.query(BudgetPlan).filter_by(is_active=True).all():
            old.is_active = False

        plan = BudgetPlan(
            goal_amount=goal_amount,
            goal_months=goal_months,
            start_month=body['start_month'],
        )
        session.add(plan)
        session.flush()

        for month_data in body.get('months', []):
            session.add(BudgetMonth(
                plan_id=plan.id,
                month_key=month_data['month_key'],
                targets=json.dumps(month_data.get('targets', {})),
            ))

        session.commit()
        return ok({'id': plan.id}, status=201)


@budget_bp.route('/plan/<int:plan_id>/checkin', methods=['POST'])
@require_json
def monthly_checkin(plan_id):
    """Record a monthly check-in with actuals and coach note."""
    body = request.json
    with db_session() as session:
        plan = session.get(BudgetPlan, plan_id)
        if not plan:
            return err('Plan not found', 404)

        month = session.query(BudgetMonth).filter_by(
            plan_id=plan_id, month_key=body['month_key']
        ).first()
        if not month:
            return err('Month not found in plan', 404)

        month.actuals     = json.dumps(body.get('actuals', {}))
        month.is_complete = True
        month.is_over     = bool(body.get('is_over', False))
        month.saved_amount= float(body.get('saved_amount', 0))
        month.coach_note  = body.get('coach_note', '')

        plan.total_saved  += month.saved_amount

        # Grace logic: one hard month costs 1 off the streak, not everything.
        # The grace_period flag (true when user marks a life event — deployment,
        # illness, emergency) holds the streak completely intact.
        grace = bool(body.get('grace_period', False))
        if grace:
            pass  # streak unchanged — life happened
        elif not month.is_over:
            plan.streak_count += 1
        else:
            plan.streak_count = max(0, plan.streak_count - 1)

        session.commit()
        return ok({'streak': plan.streak_count, 'total_saved': plan.total_saved})


# ── Debt ──────────────────────────────────────────────────────────────────────

debt_bp = Blueprint('debt', __name__)


def _pslf_terms(raw, today=None):
    """One reading of a PSLF record, for every caller that needs one.

    Factored out because the debt page's own simulator has never modelled
    forgiveness by payment count — it only excludes flagged loans from extra
    payments — while `_consequence_inputs` does. That is two answers to the same
    question for anyone on an income-driven plan: the payoff date on the debt
    page and the one behind every consequence sentence could disagree, and
    nothing reconciled them. One rule, one place.

    Returns (is_pslf, forgive_after_months, datable). `datable` is False when
    the loan is flagged but nothing on record says how far along it is — the
    honest-null that stopped someone ten months from forgiveness being told
    eighteen years.
    """
    today = today or date.today()
    program_totals = {'pslf': 120, 'ibr': 240, 'paye': 240, 'save': 240, 'other': 120}
    if not raw:
        return False, None, True
    if raw is True:
        return True, None, False              # legacy shape: flagged, undatable
    if not (isinstance(raw, dict) and raw.get('enabled')):
        return False, None, True

    total = program_totals.get(raw.get('program') or 'pslf', 120)
    made = raw.get('paymentsMade')
    if made is None and raw.get('startDate'):
        try:
            st = date.fromisoformat(str(raw['startDate'])[:10])
            made = max(0, (today.year - st.year) * 12 + (today.month - st.month)
                       - (1 if today.day < st.day else 0))
        except (ValueError, TypeError):
            made = None
    if made is None:
        return True, None, False
    return True, max(0, int(total) - int(made)), True


def _mortgage_split(d, today=None):
    """How much of a mortgage payment is principal & interest (V3).

    None for anything that is not a mortgage. For a mortgage with a balance, an
    APR and a maturity date, principal & interest is calculated the way the
    extra-payment tool already does it - exact for a fixed-rate, fully
    amortizing loan - and the rest of the payment (escrow, PMI, fees) is
    'other': it leaves the account but never reduces what is owed. Without
    those figures the split is unknown and callers use the whole payment, as
    before, and the page says so.
    """
    if (getattr(d, 'debt_type', None) or 'credit') != 'mortgage':
        return None
    pay = d.minimum_payment
    bal = d.current_balance if d.current_balance is not None else d.begin_balance
    apr = d.interest_rate
    if pay is None:
        return {'known': False}
    if not bal or bal <= 0 or apr is None or not d.end_date:
        return {'known': False, 'payment': float(pay)}
    today = today or date.today()
    months = (d.end_date.year - today.year) * 12 + (d.end_date.month - today.month)
    if months < 1:
        return {'known': False, 'payment': float(pay)}
    r = float(apr) / 1200
    pi = float(bal) / months if r == 0 else float(bal) * r / (1 - (1 + r) ** -months)
    if pi <= 0 or pi >= float(pay):
        # The payment is at or below what amortizes by the maturity date: all of it is P&I.
        return {'known': True, 'payment': float(pay), 'pi': float(pay), 'other': 0.0}
    return {'known': True, 'payment': float(pay), 'pi': round(pi, 2),
            'other': round(float(pay) - pi, 2)}


def _payoff_minimum(d):
    """The part of a debt's payment that goes to principal & interest (V3)."""
    split = _mortgage_split(d)
    if split and split.get('known'):
        return split['pi']
    return float(d.minimum_payment or 0)


def _consequence_inputs(session):
    """Build consequence-engine inputs from persisted state, matching app.js.

    Every rule here mirrors a rule in the client so the two cannot drift into
    different answers, which is the defect Pillar 1 exists to retire:
      * balance    — current_balance is authoritative; 0 is a real balance and
                     only a genuinely absent value falls back to begin_balance
                     (_cardBal, app.js)
      * strategy   — the user's own debt_method, not a hardcoded avalanche
      * budget     — the persisted monthly_budget, same 1500 default as boot
      * PSLF       — flagged loans take minimums only, and are dated by their
                     remaining qualifying payments
    """
    from core.consequence import Card

    def setting(key, default=None):
        row = session.query(AppSetting).filter_by(key=key).first()
        return row.value if row and row.value is not None else default

    try:
        pslf_all = json.loads(setting('pslf_accounts_json', '{}') or '{}')
    except (ValueError, TypeError):
        pslf_all = {}

    today = date.today()
    cards, undated = [], []

    for d in session.query(DebtAccount).filter_by(is_active=True).all():
        bal = d.current_balance if d.current_balance is not None else (d.begin_balance or 0)

        # One reading of the PSLF record, shared with /simulate. A loan flagged
        # but undated stays undated: pretending otherwise is what told someone
        # ten months from forgiveness that they had eighteen years.
        is_pslf, forgive_after, datable = _pslf_terms(pslf_all.get(str(d.id)), today)
        if is_pslf and not datable:
            undated.append(d.name)

        cards.append(Card(
            balance=float(bal or 0),
            rate=float(d.interest_rate or 0),
            minimum=_payoff_minimum(d),   # V3: a mortgage's escrow never reduces the balance
            name=d.name or 'Card',
            is_lease=(d.debt_type or 'credit') == 'lease',
            end_month=d.end_date.strftime('%Y-%m') if d.end_date else None,
            is_pslf=is_pslf,
            forgive_after_months=forgive_after,
        ))

    budget = float(setting('monthly_budget', 1500) or 1500)
    # V3: the payoff budget includes each mortgage's whole payment, but its
    # escrow share goes to taxes and insurance, not to debt - left in, the
    # engine would hand it to other debts as "extra".
    budget -= sum((_mortgage_split(d) or {}).get('other', 0.0)
                  for d in session.query(DebtAccount).filter_by(is_active=True).all())
    strategy = setting('debt_method', 'avalanche') or 'avalanche'
    return cards, budget, strategy, undated


@debt_bp.route('/decision-impact', methods=['POST'])
def debt_decision_impact():
    """What a decision does to the payoff date — Pillar 1's one deterministic core.

    Body: { monthly_delta, one_time_cost }. A trip is a one-time cost; a new
    recurring payment is a monthly delta; both together are allowed.

    Returns base and after side by side, never a bare delta, so the caller can
    always show its work. A figure that cannot be simulated comes back null
    rather than as a number — the heuristic this replaces returned a confident
    (total/income)*30 that understated the truth by up to 17x.
    """
    from core.consequence import decision_impact, offsetting_monthly_delta
    from core.solution import (do_nothing_note, save_first_plan,
                               solve_monthly_cost, solve_one_time_cost)

    body = request.get_json(silent=True) or {}
    try:
        monthly_delta = float(body.get('monthly_delta', 0) or 0)
        one_time_cost = float(body.get('one_time_cost', 0) or 0)
        # A commitment, priced the way the decision is actually made: what the
        # thing costs, and what it displaces. The caller sends both because
        # which of someone's commitments a new one replaces is theirs to name
        # (BYB's `replacing_id`), not something the ledger can infer.
        monthly_cost = float(body.get('monthly_cost', 0) or 0)
        replaces_monthly = float(body.get('replaces_monthly', 0) or 0)
    except (TypeError, ValueError):
        return err('monthly_delta and one_time_cost must be numbers')
    if monthly_cost < 0 or replaces_monthly < 0:
        return err('monthly_cost and replaces_monthly cannot be negative')
    if monthly_cost and not monthly_delta:
        # Only the difference is felt. Derived here rather than asked for, so
        # the base/after pair below describes the same decision the paths do.
        monthly_delta = -(monthly_cost - replaces_monthly)
    if one_time_cost < 0:
        return err('one_time_cost cannot be negative')

    with db_session() as session:
        cards, budget, strategy, undated = _consequence_inputs(session)
        if not cards:
            return ok({'base': None, 'after': None, 'months_delta': None,
                       'interest_delta': None, 'undated_forgiveness': [],
                       'reason': 'no active debt'})
        result = decision_impact(cards, budget,
                                 monthly_delta=monthly_delta,
                                 one_time_cost=one_time_cost,
                                 strategy=strategy,
                                 today_key=date.today().strftime('%Y-%m'),
                                 start_month=date.today().strftime('%Y-%m'))

        # Pillar 2's lever: the smallest sustained monthly increase that cancels
        # this decision's effect on the date. A number, not a suggestion — which
        # category it comes from is the Solution Engine's job, and inventing one
        # here would be the fabrication R8 exists to stop.
        # Pillar 3: the paths that close the gap, with their costs, so the user
        # chooses (E.4) — or the honest no with the nearest true path (§6.4).
        if one_time_cost:
            # Levers 1 and 4 name things — a category, a merchant — so they need
            # spend history the engine has no way to read for itself. Measuring
            # it is this layer's job precisely because the honesty rules live in
            # the whole ledger: which months are recorded at all, and what a
            # recurring item costs per month rather than per charge.
            sol = solve_one_time_cost(cards, budget, one_time_cost, strategy=strategy,
                                      today_key=date.today().strftime('%Y-%m'),
                                      start_month=date.today().strftime('%Y-%m'),
                                      categories=reallocation_candidates(session),
                                      recurring=trim_candidates(session),
                                      demonstrated=_demonstrated_lever(session))
            result['paths'] = sol['paths']
            result['honest_no'] = sol['honest_no']

            # Lever 6, for the funding panel — minus its financing comparison.
            # §6.2 requires a solution to need no new debt, so "your lowest-rate
            # card would cost less than paying cash" is not something this page
            # may say, however true the arithmetic is (and it often is: see the
            # finding in save_first_plan). That block is for a surface where the
            # purchase is already financed and the user has raised it. Stripped
            # here rather than left for the view to ignore, because a field that
            # reaches the client is a field something will eventually render.
            plan = save_first_plan(cards, budget, one_time_cost, strategy=strategy,
                                   today_key=date.today().strftime('%Y-%m'),
                                   start_month=date.today().strftime('%Y-%m'))
            if plan:
                plan.pop('financed', None)
            result['save_first'] = plan
        else:
            result['paths'], result['honest_no'] = [], None
            result['save_first'] = None

        # Substitution's recurring half: the paths for a commitment, and the
        # price at which one holds the date (§6.1's "$220/mo instead of $350").
        if monthly_cost:
            result['monthly'] = solve_monthly_cost(
                cards, budget, monthly_cost, replaces_monthly=replaces_monthly,
                strategy=strategy,
                today_key=date.today().strftime('%Y-%m'),
                start_month=date.today().strftime('%Y-%m'),
                categories=reallocation_candidates(session),
                recurring=trim_candidates(session),
                demonstrated=_demonstrated_lever(session))
        else:
            result['monthly'] = None

        # Lever 7: what is true if nothing changes. Computed whether or not
        # there is a gap — "this needs no lever" is an answer, and so is the
        # proof that the payoff order they already use is the faster one.
        result['do_nothing'] = do_nothing_note(
            cards, budget, one_time_cost, strategy=strategy,
            monthly_delta=monthly_delta,
            today_key=date.today().strftime('%Y-%m'),
            start_month=date.today().strftime('%Y-%m'))

        result['offsetting_monthly'] = (
            offsetting_monthly_delta(cards, budget, one_time_cost,
                                     strategy=strategy,
                                     today_key=date.today().strftime('%Y-%m'),
                                     start_month=date.today().strftime('%Y-%m'))
            if one_time_cost else 0.0)

    # A loan on a forgiveness plan with no recorded payment count cannot be
    # dated, and pretending otherwise is what told a user ten months from PSLF
    # forgiveness that they had eighteen years left. Say so instead.
    result['undated_forgiveness'] = undated
    result['covers_all_debt'] = not undated
    return ok(result)


# Money that moved between the user's own pockets is not spending, and
# pricing it as spending would tell someone their credit-card payment cost
# them three months. Matched on category name because that is what the ledger
# records; payments linked to a debt ledger entry are excluded outright, which
# is the precise version of the same rule.
_LESSON_EXCLUDED_CATEGORIES = {'transfer', 'transfers', 'income', 'debt',
                               'debt payment', 'savings', 'investment',
                               'investments'}


def large_charge_lesson(session, cards, budget, strategy, days: int = 60,
                        consider: int = 8):
    """The recent charge that cost the most, priced by what it would have done.

    §8's line for the Ledger. "Large" is not a dollar threshold here: the
    biggest recent charges are priced, and one earns a sentence by having moved
    the payoff date a month or more. That is a fact about this portfolio rather
    than a number chosen for every portfolio — $900 is large against one plan
    and rounding against another.

    Returns None when nothing qualifies, which is the common case and is not a
    failure. A ledger with no month-moving charge in it has nothing to teach,
    and manufacturing a lesson from the largest available row would be teaching
    for its own sake.
    """
    from core.solution import past_charge_lesson
    from core.care_status import never_lever, row_never_lever      # item 89

    cutoff = date.today() - timedelta(days=days)
    linked = {r[0] for r in session.query(
        CheckingTransactionLink.checking_transaction_id).all()}

    # The biggest first, so the scan can stop early: a smaller charge cannot
    # cost more months than a larger one against the same portfolio.
    rows = session.query(Transaction).filter(
        Transaction.type == 'debit', Transaction.date >= cutoff
    ).order_by(Transaction.amount.desc()).limit(consider * 4).all()

    today = date.today().strftime('%Y-%m')
    priced = 0
    for t in rows:
        if priced >= consider:
            break
        if t.id in linked:
            continue
        cat = session.query(Category).filter_by(id=t.category_id).first() if t.category_id else None
        if cat and (cat.name or '').strip().lower() in _LESSON_EXCLUDED_CATEGORIES:
            continue
        # Item 46 (CARE_NOT_PRICED.md C1): necessary care is never the lesson. A
        # charge in a protected category is skipped, and so is an uncategorised
        # one whose merchant or description reads like the necessity floor
        # ("CVS Pharmacy", "St. Mary's Hospital") - over-protecting loses one
        # lesson, under-protecting prices someone's surgery in months.
        # Item 89 (CARE_NEVER_A_LEVER.md U3): uncertain too - a category with a health signal, or an uncategorised
        # row the classification reads as possibly care.
        if (cat and never_lever(cat.name)) or (not cat and row_never_lever(t.merchant, t.description, t.mcc)):
            continue
        priced += 1
        lesson = past_charge_lesson(cards, budget, t.amount, strategy=strategy,
                                    today_key=today, start_month=today)
        if not lesson or lesson['months_cost'] < 1:
            continue
        # The first eligible one is the answer. Money toward the debt never
        # delays the payoff, so months saved rises with the amount, and these
        # are in descending order — no smaller charge below can beat it.
        return {
            'lesson': lesson,
            'charge': {
                'amount': round(float(t.amount or 0), 2),
                'date': t.date.isoformat() if t.date else None,
                'name': (t.merchant or t.description or 'that charge'),
                'category': cat.name if cat else None,
            },
        }
    return None


@transactions_bp.route('/lesson', methods=['GET'])
def ledger_lesson():
    """What the biggest month-moving charge in the recent ledger cost (§8).

    Past tense, and passive: it renders where the user is already looking at
    their own transactions. A.1's passive tier is the whole permission for it —
    nothing is prompted, nothing is pushed, and no speech budget is drawn.
    """
    with db_session() as session:
        cards, budget, strategy, undated = _consequence_inputs(session)
        if not cards:
            return ok({'lesson': None, 'reason': 'no active debt to price it against'})
        found = large_charge_lesson(session, cards, budget, strategy)
        if not found:
            return ok({'lesson': None, 'reason': 'no recent charge moved the date'})

        from core.solution import solve_one_time_cost
        today = date.today().strftime('%Y-%m')
        sol = solve_one_time_cost(
            cards, budget, found['lesson']['amount'], strategy=strategy,
            today_key=today, start_month=today,
            categories=reallocation_candidates(session),
            recurring=trim_candidates(session), demonstrated=_demonstrated_lever(session))
        # §6's levers, in the past tense. Substitution is dropped: a cheaper
        # version of a purchase already made is not an option anyone has.
        paths = [p for p in sol['paths'] if p['kind'] != 'substitution']

        # And what each one PUTS BACK, simulated rather than assumed. These
        # paths were solved to cancel a cost arriving in the future; the
        # sentence they feed claims they recover months already lost. The two
        # agree often enough to be mistaken for the same number and are not the
        # same computation, so the recovery is measured here and the copy says
        # what was measured.
        base = simulate_payoff(cards, budget, strategy,
                               today_key=today, start_month=today)
        for p in paths:
            freed = p.get('frees_monthly')
            # Only money available now. A timing path's capacity arrives when a
            # balance clears, and it is already in the base simulation — running
            # it from month one would credit the user with months they get
            # anyway, which is the flattering direction and the wrong number.
            if not freed or base is None or p.get('available_in_months'):
                p['months_recovered'] = None
                continue
            after = simulate_payoff(cards, budget + freed, strategy,
                                    today_key=today, start_month=today)
            p['months_recovered'] = (base['months'] - after['months']
                                     if after is not None else None)

        return ok({
            'lesson': found['lesson'],
            'charge': found['charge'],
            'paths': paths,
            'undated_forgiveness': undated,
        })


# Appendix A's routes live beside the engines they govern rather than with the
# other blueprints at the bottom of this file, because a decorator cannot run
# before the blueprint it names exists.
proactive_bp = Blueprint('proactive', __name__)
trophies_bp = Blueprint('trophies', __name__)


@trophies_bp.route('', methods=['GET'])
def list_trophies():
    """Every trophy, with the receipt behind it or the reason there is none.

    B.3: the trophy IS the proof. So this does not report what was awarded —
    the achievements table already does that — it reports what the ledger can
    still show. A trophy earned in 1.x before any of this existed comes back
    unproven rather than false: it was not fraudulently awarded, it simply has
    no receipt on file, and saying so is more honest than either dropping it or
    dressing it up.

    The per-case standard is pinned in `core/trophies.py`, which §12 gated until
    it was. Nothing here decides a class; it only gathers the evidence each
    class asks for.
    """
    from core.consequence import Card, simulate_payoff as _sim
    from core.trophies import (DURABILITY_MONTHS, TROPHY_SPEC, attributable,
                               held, verdict)

    with db_session() as session:
        earned_rows = {a.achievement_id: a for a in session.query(Achievement).all()}
        cards, budget, strategy, undated = _consequence_inputs(session)

        # ── the evidence, gathered once ─────────────────────────────────────
        cleared = session.query(DebtAccount).filter(
            DebtAccount.paid_off_at.isnot(None)).order_by(DebtAccount.paid_off_at).all()
        actives = session.query(DebtAccount).filter_by(is_active=True).all()

        history = session.query(DebtBalanceHistory).order_by(
            DebtBalanceHistory.month).all()
        by_month = {}
        for h in history:
            by_month.setdefault(h.month, 0.0)
            by_month[h.month] += float(h.balance or 0)
        months_sorted = sorted(by_month)
        paid_share = None
        if len(months_sorted) >= 2:
            first_total = by_month[months_sorted[0]]
            last_total = by_month[months_sorted[-1]]
            if first_total > 0:
                paid_share = max(0.0, (first_total - last_total) / first_total)

        snaps = [{'date': s.snapshot_date, 'net_worth': float(s.net_worth or 0),
                  'liabilities': float(s.liabilities or 0)}
                 for s in _snapshots_by_month(session)[0]]          # item 38: one per month, with figures

        # Payments landing above the minimums, by month — the receipt
        # `above_minimum` needs and the setting it currently fires on does not
        # have. A number someone typed is not money that moved.
        minimum_total = sum(_payoff_minimum(d) for d in actives)   # V3: matches the cards
        paid_by_month = {}
        for e in session.query(DebtLedgerEntry).filter_by(entry_type='payment').all():
            if not e.entry_date:
                continue
            key = e.entry_date.strftime('%Y-%m')
            paid_by_month[key] = paid_by_month.get(key, 0.0) + float(e.amount or 0)
        above_series = [paid_by_month[m] for m in sorted(paid_by_month)]

        # V11: "minimums only" means one thing everywhere - core.consequence.
        # minimums_only, the twin of the pages' _minimumsOnly. It was the engine at
        # today's minimum total, rolled over: a plan, not minimums. A run cut off
        # at 30 years proves no saving, so the trophy stays unproven then.
        from core.consequence import minimums_only
        interest_saved = None
        if cards:
            plan = _sim(cards, budget, strategy)
            floor = minimums_only([
                {'balance': (d.current_balance if d.current_balance is not None
                             else (d.begin_balance or 0)),
                 'rate': d.interest_rate or 0,
                 'minimum': _payoff_minimum(d),
                 'debt_type': d.debt_type or 'credit'} for d in actives])
            if plan and floor and not floor['capped']:
                interest_saved = floor['total_interest'] - plan['total_interest']

        # What each trophy actually claims, not merely what kind of proof it
        # uses. Two trophies read the same record and mean different things:
        # `first_card_down` needs one balance gone, `zero` needs all of them.
        # Keyed on the proof kind alone, a single cleared card proved "you are
        # debt free" while two balances were still open — a false trophy, which
        # is the one failure this module exists to prevent.
        open_balances = [d for d in actives
                         if float(d.current_balance or d.begin_balance or 0) > 0]

        def evidence_for(spec, trophy_id=None):
            proof_kind = spec.get('proof')
            if proof_kind == 'debt_cleared':
                if trophy_id == 'zero':
                    return ({'proven': bool(cleared) and not open_balances},
                            [{'label': 'balances still open',
                              'value': len(open_balances), 'unit': 'count'},
                             {'label': 'cleared', 'value': len(cleared), 'unit': 'count'}])
                return ({'proven': bool(cleared)},
                        [{'label': 'cleared', 'value': c.name, 'unit': 'text'}
                         for c in cleared[:3]]
                        + [{'label': 'first cleared', 'unit': 'text',
                            'value': cleared[0].paid_off_at.date().isoformat()}]
                        if cleared else [])
            if proof_kind == 'balance_history':
                if paid_share is None:
                    return {'proven': None}, []
                return ({'proven': paid_share > 0},
                        [{'label': 'paid down', 'value': round(paid_share * 100, 1),
                          'unit': 'percent'},
                         {'label': 'months of history', 'value': len(months_sorted),
                          'unit': 'count'}])
            if proof_kind == 'engine_interest':
                if interest_saved is None:
                    return {'proven': None}, []
                # The trophy names a thousand dollars. A receipt that proves
                # "some interest was saved" does not prove that trophy, and
                # counting it would be the declared-backed failure in miniature.
                return ({'proven': interest_saved >= 1000},
                        [{'label': 'interest saved vs minimums only',
                          'value': round(interest_saved), 'unit': 'money'}])
            if proof_kind == 'net_worth_series':
                return ({'held': held(snaps, lambda s: s['net_worth'] > 0),
                         'attributable': attributable(snaps)},
                        [{'label': 'snapshots on record', 'value': len(snaps),
                          'unit': 'count'}]
                        + ([{'label': 'liabilities then', 'value': snaps[0]['liabilities'],
                             'unit': 'money'},
                            {'label': 'liabilities now', 'value': snaps[-1]['liabilities'],
                             'unit': 'money'}] if len(snaps) >= 2 else []))
            if proof_kind == 'payments_above_minimum':
                if minimum_total <= 0:
                    return {'held': None}, []
                return ({'held': held(above_series, lambda p: p > minimum_total)},
                        [{'label': 'months of payments', 'value': len(above_series),
                          'unit': 'count'},
                         {'label': 'minimums total', 'value': round(minimum_total, 2),
                          'unit': 'money'}])
            if proof_kind == 'composite':
                return ({'held': held(snaps, lambda s: s['net_worth'] > 0),
                         'attributable': attributable(snaps)}, [])
            # Everything else: the record does not carry it yet, and the honest
            # answer is to say which record is missing rather than to guess.
            return {'proven': None, 'held': None}, []

        out = []
        for tid, spec in TROPHY_SPEC.items():
            ev, proof = evidence_for(spec, tid)
            v = verdict(tid, ev)
            row = session.query(Achievement).filter_by(achievement_id=tid).first()
            out.append({
                'id': tid, 'class': v['class'], 'earned': v['earned'],
                'rule': v['rule'], 'reason': v['reason'], 'proof': proof,
                'awarded_at': (earned_rows[tid].earned_at.isoformat()
                               if tid in earned_rows and earned_rows[tid].earned_at else None),
            })
        return ok({'trophies': out, 'durability_months': DURABILITY_MONTHS})


def _proactive_state(session):
    """The frequency budget, read from the historian rather than kept in memory.

    A.3's caps are counts over real windows, so the ledger that answers them has
    to survive a restart. `proactive_shown` and `proactive_dismissed` are that
    ledger; nothing else here is state.
    """
    now = datetime.now()
    week = now - timedelta(days=7)
    last_session = session.query(HistorianEntry).filter(
        HistorianEntry.event_category == 'session_start'
    ).order_by(HistorianEntry.created_at.desc()).first()
    session_since = last_session.created_at if last_session else now - timedelta(hours=12)

    shown, dismissed = {}, {}
    session_prompts = brake_7d = green_7d = 0
    rows = session.query(HistorianEntry).filter(
        HistorianEntry.event_category.in_(('proactive_shown', 'proactive_dismissed'))
    ).all()
    category_dismissals = {}
    for e in rows:
        try:
            cxt = json.loads(e.context_json or '{}')
        except (json.JSONDecodeError, TypeError):
            cxt = {}
        key = cxt.get('key')
        age_days = max(0, (now - e.created_at).days)
        if e.event_category == 'proactive_shown':
            if key:
                shown[key] = age_days
            if e.created_at >= session_since:
                session_prompts += 1
            if e.created_at >= week:
                if cxt.get('budget') == 'green':
                    green_7d += 1
                else:
                    brake_7d += 1
        else:
            if key and (key not in dismissed or age_days < dismissed[key]['days_ago']):
                dismissed[key] = {'days_ago': age_days}
            cat = cxt.get('category')
            if cat:
                category_dismissals[cat] = category_dismissals.get(cat, 0) + 1

    # §12's dial: explicit control, stored as a setting like every other
    # preference. Read here so the gauntlet sees it as state rather than as a
    # special case somewhere upstream.
    dial_row = session.query(AppSetting).filter_by(key='proactive_dial').first()
    dial = (dial_row.value if dial_row and dial_row.value else 'normal')

    return {
        'dial': dial if dial in ('normal', 'fewer', 'off') else 'normal',
        'session_prompts': session_prompts,
        'brake_last_7d': brake_7d,
        'green_last_7d': green_7d,
        'shown': shown,
        'dismissed': dismissed,
        # Counted only to know when to ASK (item 39 U2 (b)); never a gate on its own.
        'category_dismissals': category_dismissals,
        # Item 39: the categories the user said to stop bringing up - their setting, nothing inferred.
        'silenced_categories': _proactive_silenced(session),
    }


def _set_setting(session, key, value):
    row = session.query(AppSetting).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        session.add(AppSetting(key=key, value=value))
    session.flush()


def _proactive_silenced(session):
    row = session.query(AppSetting).filter_by(key='proactive_silenced').first()
    try:
        val = json.loads(row.value) if row and row.value else []
    except (json.JSONDecodeError, TypeError):
        val = []
    return sorted({str(c) for c in val if c})


def _proactive_declined(session):
    """Categories where the user answered No to "stop bringing this up?" - asked again never, since they said."""
    out = set()
    for e in session.query(HistorianEntry).filter(HistorianEntry.event_category == 'proactive_silence_declined').all():
        try:
            cat = json.loads(e.context_json or '{}').get('category')
        except (json.JSONDecodeError, TypeError):
            cat = None
        if cat:
            out.add(cat)
    return out


def _proactive_candidates(session, cards, budget, strategy):
    """The insights eligible to interrupt, drawn from §7's named events.

    Each one already exists as a passive surface. That is the point of A.1: this
    does not compute anything new, it only asks whether something already true
    is worth saying unprompted.
    """
    from core.solution import (accelerations, budget_pressure, green_light,
                               solve_one_time_cost)

    today = date.today().strftime('%Y-%m')
    kw = dict(strategy=strategy, today_key=today, start_month=today)
    cats = reallocation_candidates(session)
    out = []

    charge = large_charge_lesson(session, cards, budget, strategy)
    if charge:
        sol = solve_one_time_cost(cards, budget, charge['lesson']['amount'],
                                  categories=cats, recurring=trim_candidates(session), **kw)
        out.append({
            'key': f"charge:{charge['charge']['name']}:{charge['charge']['date']}",
            'kind': 'brake', 'category': charge['charge'].get('category'),
            'months': charge['lesson']['months_cost'],
            'dollars': charge['charge']['amount'],
            'has_path': any(p['closes'] for p in sol['paths']),
            'goal_impact': charge['lesson']['months_cost'],
            'subject': charge['charge']['name'],
            'detail_kind': 'charge',
        })

    # Item 46 C2: a brake is a cost by definition, and necessary care is not one.
    for over in [o for o in budget_pressure(cards, budget, categories=cats, **kw) if o['priced']][:1]:
        out.append({
            'key': f"overspend:{over['name']}",
            'kind': 'brake', 'category': over['name'],
            'months': over['months_cost'], 'dollars': over['monthly'],
            'has_path': over['fix'] is not None,
            'goal_impact': over['months_cost'],
            'subject': over['name'], 'detail_kind': 'overspend',
        })

    drivers = []
    window_start = datetime.now() - timedelta(days=365)
    for acct in session.query(DebtAccount).filter(
            DebtAccount.paid_off_at.isnot(None),
            DebtAccount.paid_off_at >= window_start).all():
        minimum = float(acct.minimum_payment or 0)
        if minimum <= 0:
            continue
        deliberate = session.query(DebtLedgerEntry).filter(
            DebtLedgerEntry.debt_account_id == acct.id,
            DebtLedgerEntry.entry_type == 'payment',
            DebtLedgerEntry.amount > minimum + 1.0).first() is not None
        drivers.append({'name': acct.name, 'monthly': round(minimum, 2),
                        'deliberate': deliberate,
                        'months_ago': ((datetime.now().year - acct.paid_off_at.year) * 12
                                       + (datetime.now().month - acct.paid_off_at.month))})
    # Appendix G's checkpoints. G.3b is emphatic that these are not a
    # separate alert channel: same voice, same gate, same budget as every
    # other brake. Materiality is instantiated at G's own timescale rather
    # than exempted — reaching a checkpoint IS the materiality event, which
    # A.2.1 already admits as "crosses a goal/milestone boundary", so it
    # clears the gate on its own ruler and never on a lower bar.
    from core.cycles import recurrence as _recurrence
    cyc = _recurrence(revolving_series(session))
    if cyc['state'] in ('approaching', 'past') and cyc.get('prior'):
        levers = accelerations(cards, budget, categories=cats,
                               recurring=trim_candidates(session), **kw)
        out.append({
            # The key differs by checkpoint on purpose: crossing from
            # approaching to past is a new and materially different fact,
            # and clears novelty on its own merits rather than as a repeat
            # (G.3b.3).
            'key': f"cycle:{cyc['state']}:{cyc['prior']['closed_month']}",
            'kind': 'brake', 'category': None,
            'months': None, 'dollars': cyc['prior']['peak'],
            'crosses_boundary': True,
            # G.3b.2: bad news needs an honest lever or it stays passive.
            # G never pushes a fact with nothing to do about it.
            'has_path': bool(levers),
            # A position fact, not a date-impact. Scoring it with the best
            # lever's months would answer a different question — what could be
            # done about it, rather than what it threatens — so it enters as
            # None and competes on perishability (A.3).
            'goal_impact': None,
            # Approaching is perishable by G.3a's own reasoning: waiting until
            # it is past is the most honest option and the least useful one,
            # because by then the worse outcome is already true. Past is not
            # perishable — it is true now and stays true.
            'perishable': cyc['state'] == 'approaching',
            'subject': cyc['prior']['peak'], 'detail_kind': 'cycle',
            'cycle': cyc,
        })

    # Item 71 I5: a drop in recorded income, unless the person said "not now" this month or already applied a plan
    # for it. A brake (A.3), material by nature (it moves the whole month), its path the scenarios.
    try:
        ics = _income_change_state(session)
        chg = ics.get('change')
        if chg and not ics.get('snoozed') and not ((ics.get('applied') or {}).get('month') == chg['month']) and ics.get('gap'):
            out.append({'key': f"income:{chg['kind']}:{chg['month']}", 'kind': 'brake', 'category': None,
                        'months': None, 'dollars': ics['gap'], 'crosses_boundary': True, 'has_path': True,
                        'goal_impact': None, 'perishable': False, 'detail_kind': 'income_change',
                        'subject': 'income', 'from': chg['from'], 'to': chg['to'], 'month': chg['month']})
    except Exception:
        logging.getLogger('groundwork').warning('the income check could not be read')

    # W-D (E.2b): a statement the user's own later edits contradict. A clarification costs what a brake costs
    # (A.3: it asks the user to resolve something), its path is the answer itself, and it disputes the category
    # - so contend() fires it before anything ranked on that category. It passes the gauntlet or stays passive
    # in the working picture, where it always shows.
    try:
        for cx in willingness_state(session)['contradictions']:
            r = cx['reading']['receipt']
            out.append({
                'key': cx['key'], 'kind': 'clarification', 'category': cx['category'],
                'months': None, 'dollars': cx['dollars'], 'has_path': True, 'goal_impact': None,
                'disputes': cx['category'], 'subject': cx['category'], 'detail_kind': 'clarification',
                'stance': cx['declaration']['stance'], 'said_at': cx['declaration']['said_at'][:10],
                'cut_old': r['cut']['old'], 'cut_new': r['cut']['new'],
            })
    except Exception:
        logging.getLogger('groundwork').warning('the contradiction-check could not be read')

    lit = green_light(cards, budget, drivers, **kw)
    if lit:
        out.append({
            'key': f"green:{lit['freed_monthly']}:{lit['driver_count']}",
            'kind': 'green', 'category': None,
            'months': lit['months_sooner'], 'dollars': lit['freed_monthly'],
            'has_path': True, 'goal_impact': lit['months_sooner'],
            'subject': (lit['drivers'][0]['name'] if lit['drivers'] else 'what you changed'),
            'detail_kind': 'green', 'freed_monthly': lit['freed_monthly'],
        })
    return out


@proactive_bp.route('/next', methods=['GET'])
def proactive_next():
    """The one insight, if any, that has earned the right to interrupt (App. A).

    **The caller owns the timing gate.** A.2 #5 forbids mid-task and blocking,
    and no server can see what the user is doing — so this route is called on a
    dashboard load and nowhere else, and the verdict says the gate was
    delegated rather than pretending to have checked it.

    Nothing promoted is not an error and not an empty state: A.3 says a week
    with no material event is a silent week. The gate that stopped each
    candidate comes back too, because "why didn't it say anything" deserves an
    answer that is not a shrug.
    """
    from core.proactive import contend, verdict

    with db_session() as session:
        cards, budget, strategy, undated = _consequence_inputs(session)
        if not cards:
            return ok({'prompt': None, 'considered': [], 'reason': 'no active debt'})

        state = _proactive_state(session)
        state['monthly_budget'] = budget

        promoted, considered = [], []
        for cand in _proactive_candidates(session, cards, budget, strategy):
            v = verdict(cand, state)
            considered.append({'key': cand['key'], 'promote': v['promote'],
                               'gate': v['gate'], 'budget': v['budget']})
            if v['promote']:
                promoted.append({**cand, 'budget': v['budget']})

        # Read-only, deliberately. Selecting is not showing, and this route does
        # both only if you let it: called on every dashboard render, a GET that
        # logs would spend the session budget on a card nobody has seen yet and
        # then hide that card on the next render, because the budget it just
        # spent now blocks it. Worse, the frequency ledger would be a record of
        # what was COMPUTED rather than what was shown. The client reports the
        # showing, which is the only place that knows it happened.
        return ok({'prompt': contend(promoted), 'considered': considered,
                   'dial': state['dial']})


@proactive_bp.route('/shown', methods=['POST'])
@require_json
def proactive_shown():
    """Record that a prompt actually reached the user (A.3's ledger).

    Posted by the surface that rendered it, because only the surface knows. A
    prompt selected and never displayed has cost the user no attention and must
    not cost the budget any either.
    """
    body = request.json or {}
    key = (body.get('key') or '').strip()
    if not key:
        return err('key is required')
    with db_session() as session:
        log_historian_event(
            session, 'proactive_shown',
            context={'key': key, 'budget': body.get('budget') or 'brake',
                     'category': body.get('category')})
        session.commit()
    return ok({'shown': key})


@proactive_bp.route('/dismiss', methods=['POST'])
@require_json
def proactive_dismiss():
    """The user closed one. That is an instruction, and it is logged as one.

    A.4: a dismissal buys a 60-day cooldown on that insight, and the card says
    so (item 39 U1). From the second in a category the card asks whether to stop
    bringing the category up (U2 (b)); nothing is concluded from the clicks, and
    the cadence does not change (U3).
    """
    body = request.json or {}
    key = (body.get('key') or '').strip()
    if not key:
        return err('key is required')
    from core.proactive import DISMISS_COOLDOWN_DAYS, DISMISSALS_TO_ASK
    category = body.get('category') or None
    with db_session() as session:
        log_historian_event(session, 'proactive_dismissed',
                            context={'key': key, 'category': category})
        session.commit()
        # Item 39 U2 (b): from the second dismissal in a category, ASK - never conclude. Not asked when the
        # category is already silenced, or when the user already answered No.
        ask = None
        if category:
            n = _proactive_state(session)['category_dismissals'].get(category, 0)
            if (n >= DISMISSALS_TO_ASK and category not in _proactive_silenced(session)
                    and category not in _proactive_declined(session)):
                ask = category
    return ok({'dismissed': key, 'cooldown_days': DISMISS_COOLDOWN_DAYS, 'ask_silence': ask})


@proactive_bp.route('/silence', methods=['POST'])
@require_json
def proactive_silence():
    """Item 39 U2 (b): the user's answer to "Stop bringing up <category> on its own?". {category, silence: true|false}.
    Yes adds it to the user's setting (listed in Settings with Undo); No is recorded so it is not asked again."""
    body = request.json or {}
    category = (body.get('category') or '').strip()
    if not category:
        return err('category is required')
    with db_session() as session:
        if body.get('silence'):
            cats = sorted(set(_proactive_silenced(session)) | {category})
            _set_setting(session, 'proactive_silenced', json.dumps(cats))
            log_historian_event(session, 'proactive_category_silenced', context={'category': category})
        else:
            log_historian_event(session, 'proactive_silence_declined', context={'category': category})
        session.commit()
        return ok({'silenced': _proactive_silenced(session)})


@proactive_bp.route('/silenced', methods=['GET'])
def proactive_silenced_list():
    with db_session() as session:
        return ok({'silenced': _proactive_silenced(session)})


@proactive_bp.route('/unsilence', methods=['POST'])
@require_json
def proactive_unsilence():
    """Undo, from Settings: the category may come up on its own again."""
    category = ((request.json or {}).get('category') or '').strip()
    if not category:
        return err('category is required')
    with db_session() as session:
        cats = [c for c in _proactive_silenced(session) if c != category]
        _set_setting(session, 'proactive_silenced', json.dumps(cats))
        log_historian_event(session, 'proactive_category_unsilenced', context={'category': category})
        session.commit()
        return ok({'silenced': cats})


def revolving_series(session):
    """Overall revolving debt, month by month, from recorded history.

    G.3 pins the unit: the whole revolving position, not one balance and not one
    debt type. Installment loans and leases are excluded because they amortise
    to zero by design — a car loan ending is not a cycle closing, and counting
    it as one would manufacture the very shape this is meant to detect.

    Read from `debt_balance_history` rather than from current balances, because
    a cycle is a claim about the past and only the recorded past can support it.
    """
    revolving = {d.id for d in session.query(DebtAccount).all()
                 if (d.debt_type or 'credit') == 'credit'}
    if not revolving:
        return []

    by_month = {}
    for h in session.query(DebtBalanceHistory).order_by(DebtBalanceHistory.month).all():
        if h.debt_id not in revolving:
            continue
        slot = by_month.setdefault(h.month, {'month': h.month, 'balance': 0.0,
                                             'interest': 0.0, 'interest_known': True})
        slot['balance'] += float(h.balance or 0)
        if h.interest_charged is None:
            slot['interest_known'] = False
        else:
            slot['interest'] += float(h.interest_charged)

    out = []
    for month in sorted(by_month):
        row = by_month[month]
        out.append({'month': month, 'balance': round(row['balance'], 2),
                    'interest': (round(row['interest'], 2)
                                 if row['interest_known'] else None)})
    return out


@debt_bp.route('/simulate', methods=['POST'])
@require_json
def debt_simulate():
    """Run the one engine against a portfolio the caller holds (Pillar 1, §7).

    Every other consequence route reads persisted state, and deliberately: a
    route that takes numbers on trust is a route that can be told anything. This
    one takes the portfolio because it has to. The debt page recalculates while
    someone types a balance — `setCardField` mutates client state and re-renders
    before the 600ms save lands — so a payoff figure computed only from saved
    state would be a figure for a portfolio the user is no longer looking at.

    Pillar 1's claim is one implementation of the MATH, not one copy of the
    data: "the defect is two answers to the same question". Handing the working
    portfolio to the same engine keeps one answer. What it must never do is
    persist any of this — nothing here is written, and the caller's numbers
    leave no trace beyond the response.
    """
    from core.consequence import Card, simulate_payoff

    body = request.json or {}
    try:
        budget = float(body.get('budget', 0) or 0)
        extra = float(body.get('extra', 0) or 0)
    except (TypeError, ValueError):
        return err('budget and extra must be numbers')
    strategy = 'snowball' if body.get('strategy') == 'snowball' else 'avalanche'

    # The caller sends what it is holding; forgiveness terms come from the
    # server's own PSLF record, by card id. The client has never modelled
    # forgiveness by payment count, so taking its word for it would import the
    # very divergence this route exists to end.
    with db_session() as session:
        row = session.query(AppSetting).filter_by(key='pslf_accounts_json').first()
    try:
        pslf_all = json.loads(row.value) if row and row.value else {}
    except (ValueError, TypeError):
        pslf_all = {}

    cards, undated = [], []
    for raw in (body.get('cards') or []):
        try:
            is_pslf, forgive_after, datable = _pslf_terms(
                pslf_all.get(str(raw.get('id'))))
            if is_pslf and not datable:
                undated.append(str(raw.get('name') or 'Card'))
            cards.append(Card(
                balance=float(raw.get('balance', 0) or 0),
                rate=float(raw.get('rate', 0) or 0),
                minimum=float(raw.get('minimum', 0) or 0),
                name=str(raw.get('name') or 'Card'),
                is_lease=bool(raw.get('is_lease')),
                end_month=raw.get('end_month') or None,
                is_pslf=is_pslf,
                forgive_after_months=forgive_after,
            ))
        except (TypeError, ValueError):
            return err('every card needs numeric balance, rate and minimum')

    today = date.today().strftime('%Y-%m')
    result = simulate_payoff(cards, budget + extra, strategy,
                             today_key=today, start_month=today)
    if result is None:
        # The honest null the JS has always returned here, and it means one
        # specific thing: the budget cannot cover the minimums. It is not
        # "unknown" and it is not zero.
        return ok({'result': None, 'reason': 'the budget does not cover the minimums'})
    return ok({'result': {
        'months': result['months'],
        'totalInterest': result['total_interest'],
        'clearedAt': result['cleared_at'],
        'undatedForgiveness': (result['undated_forgiveness'] or undated),
        'conditionalOnCertification': result['conditional_on_certification'],
    }})


@debt_bp.route('/cycle', methods=['GET'])
def debt_cycle():
    """Whether this shape has happened before, and how far along it is (App. G).

    Silence is the common answer and the correct one: most ledgers have no
    completed cycle in them, and C.7 routes that through the honest-no rather
    than through a fabricated peak. `state: none` carries the reason.
    """
    from core.cycles import recurrence

    with db_session() as session:
        series = revolving_series(session)
        return ok({'cycle': recurrence(series), 'months_recorded': len(series)})


@debt_bp.route('/green-light', methods=['GET'])
def debt_green_light():
    """What deliberate action freed, and what it now covers (Pillar 4, App. D).

    The drivers are obligations that ENDED. An extra payment is deliberate and
    it moves the date, but it frees no monthly money — putting it in a figure
    called "freed per month" would be false in the one sentence most likely to
    be read as praise. What extra payments do here is decide whether a clearing
    was deliberate at all (D.4): a balance that ran out on its minimums is the
    expected floor, and praising a floor erodes trust.

    Nothing about income or investments reaches this route (D.3, D.6). Not by
    filtering — by never being read.
    """
    from core.solution import green_light

    window_start = datetime.now() - timedelta(days=365)
    today = date.today().strftime('%Y-%m')
    with db_session() as session:
        cards, budget, strategy, undated = _consequence_inputs(session)
        if not cards:
            return ok({'green_light': None, 'reason': 'no active debt'})

        drivers = []
        cleared = session.query(DebtAccount).filter(
            DebtAccount.paid_off_at.isnot(None),
            DebtAccount.paid_off_at >= window_start).all()
        for acct in cleared:
            minimum = float(acct.minimum_payment or 0)
            if minimum <= 0:
                continue
            # Above the baseline, by more than a rounding cent. A payment equal
            # to the minimum is the floor; anything above it is a choice.
            deliberate = session.query(DebtLedgerEntry).filter(
                DebtLedgerEntry.debt_account_id == acct.id,
                DebtLedgerEntry.entry_type == 'payment',
                DebtLedgerEntry.amount > minimum + 1.0).first() is not None
            months_ago = ((datetime.now().year - acct.paid_off_at.year) * 12
                          + (datetime.now().month - acct.paid_off_at.month))
            drivers.append({'name': acct.name, 'monthly': round(minimum, 2),
                            'deliberate': deliberate, 'months_ago': months_ago})

        return ok({'green_light': green_light(cards, budget, drivers,
                                              strategy=strategy, today_key=today,
                                              start_month=today)})


@debt_bp.route('/teaching', methods=['GET'])
def report_teaching():
    """The month's causal findings, each with the proof behind it (§8, App. B).

    §8's line for Reports is "the causal teaching layer, made explicit,
    lever-oriented, and proof-cited". Explicit is the operative word: this
    composes what the other surfaces already compute rather than growing a
    sixth engine, so the report cannot drift from the pages it summarises.
    Every finding is a number this app renders somewhere else.

    **No prose here.** Each finding is structured — what moved, by how much,
    what would change it, and the figures behind it — and the sentence is the
    view's to write, as it is on every other surface (B.2a keeps register in
    one place). It also means the narrator can be handed facts rather than
    sentences: B.2's whole posture is that the model interprets truth and never
    originates it, and the measured reason is sharper than the principle —
    inference-smuggling ran 37-70% on every model tested and ROSE with size, so
    a causal claim composed by the model is the one thing the evidence says not
    to build (MODEL_PLACEMENT.md).

    `proof` is the drill-down: the figures a claim rests on, so "show your work"
    is a field rather than a promise (B.1).
    """
    from core.solution import (accelerations, budget_pressure, capacity_unlocked,
                               fund_pace)
    from core.database import SinkingFund

    with db_session() as session:
        cards, budget, strategy, undated = _consequence_inputs(session)
        if not cards:
            return ok({'findings': [], 'reason': 'no active debt to price against'})

        today = date.today().strftime('%Y-%m')
        kw = dict(strategy=strategy, today_key=today, start_month=today)
        base = simulate_payoff(cards, budget, strategy,
                               today_key=today, start_month=today)
        cats = reallocation_candidates(session)
        rec = trim_candidates(session)
        findings = []

        # What the month's biggest charge cost — the retrospective one, first
        # because it is the only finding about something that already happened.
        charge = large_charge_lesson(session, cards, budget, strategy)
        if charge:
            findings.append({
                'kind': 'charge',
                'subject': charge['charge']['name'],
                'months': charge['lesson']['months_cost'],
                # What the months MEAN. A renderer that assumes every month
                # count is a payoff-date month told the narrator that a fund
                # running late was ten months on the debt-free date — a false
                # fact, handed over by the one block built to prevent them.
                'months_label': 'on the debt-free date',
                'interest': charge['lesson']['interest_cost'],
                'monthly': None,
                # Each figure says what it IS. The view formatted by sniffing
                # the label for the word "month", which read a month count as
                # dollars ("payoff without it: $13.00") and dollars-per-month
                # as a bare number. A unit is a fact; guessing it from prose is
                # the same mistake as guessing anything else from prose.
                'proof': [
                    {'label': 'charge', 'value': charge['charge']['amount'], 'unit': 'money'},
                    {'label': 'dated', 'value': charge['charge']['date'], 'unit': 'text'},
                    {'label': 'payoff without it', 'unit': 'months',
                     'value': base['months'] - charge['lesson']['months_cost']},
                    {'label': 'payoff as recorded', 'value': base['months'], 'unit': 'months'},
                ],
            })

        # What runs over its own budget, and what that costs.
        for over in budget_pressure(cards, budget, categories=cats, **kw)[:1]:
            findings.append({
                'kind': 'overspend',
                'subject': over['name'],
                'months': over['months_cost'],
                'months_label': 'on the debt-free date',
                'interest': over['interest_cost'],
                'monthly': over['monthly'],
                'protected': over['protected'],
                'proof': [
                    {'label': 'budgeted', 'value': over['budgeted'], 'unit': 'money'},
                    {'label': 'lowest month on record', 'value': over['floor'], 'unit': 'money'},
                    {'label': 'months on record', 'value': over['months_observed'], 'unit': 'count'},
                ],
            })

        # And what would move the date most from here.
        for lever in accelerations(cards, budget, categories=cats, recurring=rec, **kw)[:1]:
            findings.append({
                'kind': 'lever',
                'subject': lever['label'],
                'months': lever['months_saved'],
                'months_label': 'sooner on the debt-free date',
                'interest': lever['interest_saved'],
                'monthly': lever['monthly'],
                'requires_cut': lever['requires_cut'],
                'proof': [
                    {'label': 'from', 'value': lever['detail'], 'unit': 'text'},
                    {'label': 'payoff now', 'value': base['months'], 'unit': 'months'},
                    {'label': 'payoff with it', 'unit': 'months',
                     'value': base['months'] - lever['months_saved']}],
            })

        # A fund that will not make its own deadline at the pace being kept.
        for f in session.query(SinkingFund).filter_by(is_active=True).all():
            deadline_months = None
            if f.deadline:
                try:
                    d = date.fromisoformat(f.deadline)
                    deadline_months = ((d.year - date.today().year) * 12
                                       + (d.month - date.today().month))
                except ValueError:
                    deadline_months = None
            planned = float(f.monthly_contribution or 0)
            # F.8: a break in what the fund has been fed is a boundary - only the months since it may
            # set the pace (BREAK_DETECTOR.md ruling 6).
            brk = fund_contribution_break(session, f.id)
            observed, samples = fund_observed_monthly(session, f.id, since=brk['month'] if brk else None)
            pace = fund_pace(f.target_amount, f.current_amount, planned,
                             deadline_months=deadline_months,
                             observed_monthly=observed, samples=samples,
                             categories=cats, recurring=rec, since_break=brk)
            if pace and not pace.get('funded') and pace.get('on_track') is False:
                findings.append({
                    'kind': 'fund',
                    'subject': f.name,
                    'months_label': 'past its own deadline',
                    'months': (pace['finish_months'] - pace['deadline_months']
                               if pace.get('finish_months') else None),
                    'interest': None,
                    'monthly': pace.get('short_monthly'),
                    'pace_source': pace['pace_source'],
                    'proof': [
                        {'label': 'still needed', 'value': pace['remaining'], 'unit': 'money'},
                        {'label': 'going in per month', 'value': pace['pace_monthly'],
                         'unit': 'money'},
                        {'label': 'months until the deadline', 'unit': 'count',
                         'value': pace['deadline_months']},
                    ],
                })
                break

        return ok({'findings': findings, 'base_months': base['months'],
                   'undated_forgiveness': undated})


@debt_bp.route('/capacity', methods=['GET'])
def debt_capacity():
    """What a balance the user could now cover outright would enable (§8).

    Rendered on Net Worth, computed here because the arithmetic is the payoff
    engine's. Liquid means savings and cash — not investments, whose sale has
    consequences this engine does not model and would not advise on, and not
    home equity, which is not spendable without a transaction nobody here is
    going to propose.

    The buffer is one month of the user's own recorded expenses. With none
    recorded there is no way to express a buffer, and the answer is nothing.
    """
    from core.solution import capacity_unlocked

    with db_session() as session:
        cards, budget, strategy, undated = _consequence_inputs(session)
        if not cards:
            return ok({'capacity': [], 'reason': 'no active debt'})

        def setting(key):
            row = session.query(AppSetting).filter_by(key=key).first()
            try:
                return float(row.value) if row and row.value else 0.0
            except (TypeError, ValueError):
                return 0.0

        liquid = setting('savings_balance') + setting('cash_balance')
        # This month's figures (BUDGET_MONTH_AMOUNT.md M3): a followed estimate counts; the saved amounts are untouched.
        monthly_expenses = sum(v['month_amount'] for v in budget_month_amounts(session).values())

        today = date.today().strftime('%Y-%m')
        return ok({
            'liquid': round(liquid, 2),
            'monthly_expenses': round(monthly_expenses, 2),
            'base': simulate_payoff(cards, budget, strategy,
                                    today_key=today, start_month=today),
            'capacity': capacity_unlocked(cards, budget, liquid, monthly_expenses,
                                          strategy=strategy, today_key=today,
                                          start_month=today),
            'undated_forgiveness': undated,
        })


@debt_bp.route('/accelerations', methods=['GET'])
def debt_accelerations():
    """What moves the payoff date most, on the plan already in place (§8).

    Every other consequence route answers a question about a decision. This one
    answers a question about the plan, which is what the Debt Payoff surface is
    for, and it takes no body because there is nothing to decide — the levers
    are read from what the ledger already records.

    An empty list is an answer, not a failure: it means nothing in the record
    moves the date further, and `do_nothing` carries the proof that goes with
    it (lever 7).
    """
    from core.solution import accelerations, do_nothing_note

    with db_session() as session:
        cards, budget, strategy, undated = _consequence_inputs(session)
        if not cards:
            return ok({'base': None, 'accelerations': [], 'do_nothing': None,
                       'undated_forgiveness': [], 'reason': 'no active debt'})
        today = date.today().strftime('%Y-%m')
        result = {
            'base': simulate_payoff(cards, budget, strategy,
                                    today_key=today, start_month=today),
            'accelerations': accelerations(
                cards, budget,
                categories=reallocation_candidates(session),
                recurring=trim_candidates(session),
                strategy=strategy, today_key=today, start_month=today),
            'do_nothing': do_nothing_note(cards, budget, strategy=strategy,
                                          today_key=today, start_month=today),
            'undated_forgiveness': undated,
        }
    return ok(result)


@debt_bp.route('', methods=['GET'])
def list_debt():
    with db_session() as session:
        debts = session.query(DebtAccount).filter_by(is_active=True).all()
        return ok([serialize_debt_account(d, session) for d in debts])


# V2: the sources a client may claim. 'statement' is only ever set by the
# statement reconcile, never taken from a request body.
_CLIENT_FIGURE_SOURCES = ('user', 'calculated')


def _figure_changed(old, new):
    if old is None or new is None:
        return (old is None) != (new is None)
    return abs(float(old) - float(new)) > 1e-9


def _debt_figure(body, key):
    """A debt's balance / rate / minimum from a request body (V6).

    An explicit blank - None or '' - is unknown and stored as NULL, because 0 is
    a real APR (promotional) and a real balance (paid off), and a zero written
    for "not entered" can never be told apart from one afterwards. A key that
    is absent keeps the old default of 0, so callers that never send it (Before
    You Buy's lease, older clients) behave as before.
    """
    if key not in body:
        return 0.0
    raw = body[key]
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


@debt_bp.route('', methods=['POST'])
@require_json
def create_debt():
    body = request.json
    if not (body.get('name') or '').strip():
        return err('name is required')
    with db_session() as session:
        start_date = None
        if body.get('start_date'):
            try:
                start_date = date.fromisoformat(body['start_date'])
            except ValueError:
                pass

        end_date = None
        if body.get('end_date'):
            try:
                end_date = date.fromisoformat(body['end_date'])
            except ValueError:
                pass

        debt = DebtAccount(
            name=body['name'],
            begin_balance=_debt_figure(body, 'begin_balance'),
            current_balance=_debt_figure(body, 'current_balance'),
            interest_rate=_debt_figure(body, 'interest_rate'),
            minimum_payment=_debt_figure(body, 'minimum_payment'),
            due_day=body.get('due_day'),
            start_date=start_date,
            end_date=end_date,
            debt_type=body.get('debt_type', 'credit'),
        )
        session.add(debt)
        session.flush()  # get debt.id
        # The columns default to 0.0, and SQLAlchemy applies a column default
        # even when None is passed at insert - so a blank has to be set back to
        # unknown after the insert, where an explicit None does persist (V6).
        for _f in ('begin_balance', 'current_balance', 'interest_rate', 'minimum_payment'):
            if _debt_figure(body, _f) is None:
                setattr(debt, _f, None)
        # V2: a figure the caller gave is the user's; an absent or blank one has no source.
        for _f in ('interest_rate', 'minimum_payment'):
            given = _f in body and _debt_figure(body, _f) is not None
            src = body.get(f'{_f}_source')
            setattr(debt, f'{_f}_source',
                    (src if src in _CLIENT_FIGURE_SOURCES else 'user') if given else None)

        # Auto-create a companion Account so the user can import transactions
        # against this debt card immediately. The account uses the same name
        # as the card. If an account with this name already exists, link to
        # it instead of creating a duplicate.
        if body.get('name', '').strip():
            existing_acct = session.query(Account).filter_by(name=body['name'].strip()).first()
            if existing_acct:
                debt.linked_account_id = existing_acct.id
            else:
                acct = Account(
                    name=body['name'].strip(),
                    type='credit',
                    institution='',
                    is_active=True,
                )
                session.add(acct)
                session.flush()
                debt.linked_account_id = acct.id

        session.commit()
        return ok(serialize_debt_account(debt, session), status=201)


@debt_bp.route('/<int:debt_id>', methods=['PATCH'])
@require_json
def update_debt(debt_id):
    body = request.json
    with db_session() as session:
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('Not found', 404)
        if 'portal_url' in body:
            # Written only through PUT /api/debt/<id>/portal, which enforces F3.
            return err('Set the bank website through the portal route.', 400)
        if 'linked_account_id' in body and body['linked_account_id'] != debt.linked_account_id:
            conflict = _relink_card_portal(session, debt, body['linked_account_id'],
                                           body.get('portal_keep'))
            if conflict:
                return jsonify({'ok': False,
                                'error': 'The card and the account have different bank websites.',
                                'portal_conflict': conflict}), 409
        for field in ['name', 'current_balance', 'interest_rate',
                      'minimum_payment', 'due_day', 'linked_account_id',
                      'credit_limit', 'debt_type']:
            if field in body:
                if field in ('current_balance', 'interest_rate', 'minimum_payment'):
                    old = getattr(debt, field)
                    new = _debt_figure(body, field)   # blank = unknown (V6)
                    setattr(debt, field, new)
                    # V2: the Debt page resends every field on every edit, so the
                    # source moves only when the value actually changes - editing
                    # the due day must not relabel a statement APR as typed.
                    if field != 'current_balance' and _figure_changed(old, new):
                        src = body.get(f'{field}_source')
                        setattr(debt, f'{field}_source',
                                None if new is None
                                else (src if src in _CLIENT_FIGURE_SOURCES else 'user'))
                else:
                    setattr(debt, field, body[field])
        # Date fields need explicit parsing. paid_off_at (d21): the serializer
        # already emitted it defensively via getattr, but nothing ever accepted
        # or stored it — the paid flag lived only in client memory and died on
        # every restart. Requires the DebtAccount model line in core/database.py
        # (paid_off_at = Column(Date, nullable=True)); until that line exists,
        # setattr writes an inert instance attribute and persistence stays off.
        for date_field in ['start_date', 'end_date', 'paid_off_at']:
            if date_field in body:
                raw = body[date_field]
                if raw:
                    try:
                        setattr(debt, date_field, date.fromisoformat(raw))
                    except (ValueError, TypeError):
                        logging.getLogger('groundwork').warning(
                            'debt PATCH: invalid %s %r ignored', date_field, raw)
                else:
                    setattr(debt, date_field, None)
        session.commit()
        return ok(serialize_debt_account(debt, session))


@debt_bp.route('/<int:debt_id>', methods=['DELETE'])
def delete_debt(debt_id):
    with db_session() as session:
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('Not found', 404)
        debt.is_active = False
        session.commit()
    import bank_window
    bank_window.close_bank_window(('card', debt_id))
    return ok({'deleted': debt_id})


def _relink_card_portal(session, debt, new_account_id, keep=None):
    """Keep one source of truth for a card's bank website across a link change (F3, s7).

    Unlinking empties the card's link - nothing is copied from the Account, so
    the old relationship leaves no destination behind. Linking stores NULL on
    the card and the Account's link governs. If the card had its own link and
    the Account has none, the card's is carried to the Account (there is only
    one link, so nothing is chosen). If both have links and they differ, the
    user is asked: returns the conflict until `keep` says 'card' or 'account'.
    """
    if not new_account_id:
        debt.portal_url = None
        return None
    acct = session.get(Account, new_account_id)
    card_url = getattr(debt, 'portal_url', None) or None
    acct_url = (getattr(acct, 'portal_url', None) or None) if acct else None
    if acct is not None and card_url and acct_url and card_url != acct_url:
        if keep == 'card':
            acct.portal_url = card_url
        elif keep != 'account':
            import bank_window
            # The full addresses, not just hosts: two links on one bank's site
            # often share a host and differ only in path. Shown once, in the
            # prompt that asks the user; never kept in app state.
            return {'card_host': bank_window.portal_host(card_url),
                    'account_host': bank_window.portal_host(acct_url),
                    'card_url': card_url, 'account_url': acct_url,
                    'account_name': acct.name}
    elif acct is not None and card_url and not acct_url:
        acct.portal_url = card_url
    debt.portal_url = None
    return None


@debt_bp.route('/<int:debt_id>/portal', methods=['GET'])
def get_debt_portal(debt_id):
    with db_session() as session:
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('Not found', 404)
        linked = debt.linked_account_id
        acct = session.get(Account, linked) if linked else None
        return ok({
            'url':          _debt_portal_url(session, debt) or '',
            'owner':        'account' if linked else 'card',
            'account_id':   linked,
            'account_name': acct.name if acct else None,
        })


@debt_bp.route('/<int:debt_id>/portal', methods=['PUT'])
@require_json
def put_debt_portal(debt_id):
    url, problem = _portal_body_url(request.json)
    if problem:
        return err(problem, 400)
    with db_session() as session:
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('Not found', 404)
        if debt.linked_account_id:
            # A linked card has no link of its own (F3): the Account's governs.
            return err("This card uses its account's bank website. Change it in the account settings.", 409)
        debt.portal_url = url
        session.commit()
        return ok({'url': url or ''})


@debt_bp.route('/<int:debt_id>/portal/open', methods=['POST'])
def open_debt_portal(debt_id):
    mode = (request.get_json(silent=True) or {}).get('mode', 'window')
    with db_session() as session:
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('Not found', 404)
        url = _debt_portal_url(session, debt)
        key = ('account', debt.linked_account_id) if debt.linked_account_id else ('card', debt_id)
    return _portal_open(key, url, mode)


@debt_bp.route('/<int:debt_id>/permanent', methods=['DELETE'])
def delete_debt_added_by_mistake(debt_id):
    """Delete a debt that was added by mistake, and its history with it.

    DELETE /api/debt/<id> only hides a debt, and a hidden debt's balance
    history still counts wherever past debt is summed (revolving_series, the
    trophies) - right for a card that really existed and closed, wrong for a
    duplicate or a typo, which kept adding to those sums after removal (V8).

    Real deletion, so it takes a full database backup first, server-side as
    DELETE /api/transactions does; if the backup fails nothing is deleted. The
    existence check comes before the backup, so an id nothing owns is a 404
    with no backup written.

    Deleted: the debt, its balance history, its ledger entries and their
    checking-transaction links, and its recurring payments. Kept: historian
    entries, unlinked (SQLite reuses the highest id, so a dangling id could
    attach them to the next debt created), and the companion account and its
    imported transactions, which are bank data, not debt data.
    """
    import shutil
    from core.database import DB_PATH

    with db_session() as session:
        if not session.get(DebtAccount, debt_id):
            return err('Not found', 404)

    try:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = _write_backup(f'groundwork_backup_pre-delete-debt-{debt_id}_{ts}')   # item 81
    except Exception as e:
        return err(f'Could not create a safety backup, aborting (nothing was deleted): {e}', 500)

    with db_session() as session:
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('Not found', 404)
        entry_ids = [eid for (eid,) in session.query(DebtLedgerEntry.id)
                     .filter_by(debt_account_id=debt_id).all()]
        links = 0
        if entry_ids:
            links = session.query(CheckingTransactionLink).filter(
                CheckingTransactionLink.debt_ledger_entry_id.in_(entry_ids)
            ).delete(synchronize_session=False)
        entries = session.query(DebtLedgerEntry).filter_by(
            debt_account_id=debt_id).delete(synchronize_session=False)
        history = session.query(DebtBalanceHistory).filter_by(
            debt_id=debt_id).delete(synchronize_session=False)
        recurring = session.query(RecurringDebtPayment).filter_by(
            debt_account_id=debt_id).delete(synchronize_session=False)
        unlinked = session.query(HistorianEntry).filter_by(
            debt_account_id=debt_id).update({'debt_account_id': None},
                                            synchronize_session=False)
        session.delete(debt)
        session.commit()
        return ok({'deleted': debt_id, 'backup': backup_name,
                   'balance_history': history, 'ledger_entries': entries,
                   'checking_links': links, 'recurring_payments': recurring,
                   'historian_unlinked': unlinked})


@debt_bp.route('/history', methods=['POST'])
def save_debt_history():
    """
    Blueprint §11 — write a monthly snapshot for each active debt.
    Called when the user saves the budget for a given month.
    POST body: { month: 'YYYY-MM', snapshots: [{ debt_id, balance, payment, min_payment, apr }] }
    UNIQUE(debt_id, month) — re-saving the same month just updates.
    """
    from core.database import DebtBalanceHistory
    body      = request.get_json(force=True) or {}
    month     = body.get('month', '')
    snapshots = body.get('snapshots', [])
    if not month or not snapshots:
        return err('month and snapshots required', 400)

    with db_session() as session:
        for snap in snapshots:
            debt_id = int(snap.get('debt_id', 0))
            if not debt_id:
                continue
            existing = session.query(DebtBalanceHistory).filter_by(
                debt_id=debt_id, month=month
            ).first()
            if existing:
                existing.balance              = float(snap.get('balance', 0))
                existing.payment              = float(snap.get('payment', 0))
                existing.min_payment          = float(snap.get('min_payment', 0))
                existing.apr                  = snap.get('apr')
                if 'interest_charged' in snap:
                    existing.interest_charged     = snap.get('interest_charged')
                if 'statement_period_end' in snap:
                    existing.statement_period_end = snap.get('statement_period_end')
            else:
                session.add(DebtBalanceHistory(
                    debt_id              = debt_id,
                    month                = month,
                    balance              = float(snap.get('balance', 0)),
                    payment              = float(snap.get('payment', 0)),
                    min_payment          = float(snap.get('min_payment', 0)),
                    apr                  = snap.get('apr'),
                    interest_charged     = snap.get('interest_charged'),
                    statement_period_end = snap.get('statement_period_end'),
                ))
        session.commit()
    return ok({'saved': len(snapshots)})


@debt_bp.route('/history/all', methods=['GET'])
def get_all_debt_history():
    """
    Return recent history for ALL active debts in one call.
    Used by Budget-CP4 to compute minimum decay and freed-minimums.
    Returns: { debt_id: [{ month, balance, payment, min_payment, apr }, ...] }
    """
    from core.database import DebtBalanceHistory
    with db_session() as session:
        rows = session.query(DebtBalanceHistory)\
                      .order_by(DebtBalanceHistory.debt_id,
                                DebtBalanceHistory.month.desc())\
                      .all()
        result = {}
        for r in rows:
            key = str(r.debt_id)
            if key not in result:
                result[key] = []
            result[key].append({
                'month':                r.month,
                'balance':              r.balance,
                'payment':              r.payment,
                'min_payment':          r.min_payment,
                'apr':                  r.apr,
                'interest_charged':     r.interest_charged,
                'statement_period_end': r.statement_period_end,
            })
        return ok(result)


@debt_bp.route('/history/<int:debt_id>', methods=['GET'])
def get_debt_history(debt_id):
    """Return all monthly snapshots for one debt, newest first."""
    from core.database import DebtBalanceHistory
    with db_session() as session:
        rows = session.query(DebtBalanceHistory)\
                      .filter_by(debt_id=debt_id)\
                      .order_by(DebtBalanceHistory.month.desc())\
                      .all()
        return ok([{
            'month':                r.month,
            'balance':              r.balance,
            'payment':              r.payment,
            'min_payment':          r.min_payment,
            'apr':                  r.apr,
            'interest_charged':     r.interest_charged,
            'statement_period_end': r.statement_period_end,
        } for r in rows])


# ── Phase 4: PDF statement extraction (issuer-agnostic) ───────────────────────
# Two-destination routing: transactions flow through the SAME
# /api/import/commit path every other import source uses (dedup,
# categorization, the existing B3.5/B6b auto-writes); the statement's own
# authoritative summary figures land here via pdf-reconcile, overwriting
# whatever B3.5/B6b derived from transaction arithmetic. The statement's
# printed balance is trusted over our own sum — it catches a miscategorized
# fee or a transaction extraction miss that would otherwise drift silently.

def _ai_complete_text(system: str, user: str, max_tokens: int = 4000):
    """
    Call the in-app AI engine directly — no HTTP round-trip through
    /api/ai/chat — for server-side pipelines (like PDF extraction) that need
    a model call but aren't themselves handling a chat request. Returns the
    response text, or None if AI is disabled/unreachable/unavailable.
    """
    if not _ai_is_enabled():
        return None
    body = {'system': system, 'messages': [{'role': 'user', 'content': user}],
            'max_tokens': max_tokens}
    resp = _ai_chat_local(body)
    resp_obj = resp[0] if isinstance(resp, tuple) else resp
    try:
        data = resp_obj.get_json()
    except Exception:
        return None
    if not data or data.get('ai_available') is False:
        return None
    content = data.get('content') or []
    text = '\n'.join(b.get('text', '') for b in content if b.get('text'))
    return text or None


@debt_bp.route('/pdf-extract', methods=['POST'])
def debt_pdf_extract():
    """
    4A/4B/4E — accept a PDF statement, extract its text (layout only, never
    interprets meaning), have the model return strict JSON, then validate
    every figure against the source text (R8-style number provenance) before
    it's trusted. Returns transactions in bank_importer's exact record shape
    so they flow through the existing /api/import/preview+commit path.
    """
    if 'file' not in request.files:
        return err('No file uploaded')
    f = request.files['file']
    pdf_bytes = f.read()
    if not pdf_bytes:
        return err('Empty file')

    import pdf_statement as ps

    source_hash = ps.sha256_bytes(pdf_bytes)

    # SHA-256 cache — a re-upload of the identical statement returns the
    # already-validated numbers instead of re-running the model.
    with db_session() as session:
        cached = session.query(PdfExtractCache).filter_by(source_hash=source_hash).first()
        if cached:
            try:
                payload = json.loads(cached.extracted_json)
                return ok({**payload, 'source_hash': source_hash, 'cached': True})
            except (ValueError, TypeError):
                pass  # corrupt cache row — fall through and re-extract

    try:
        statement_text = ps.extract_text(pdf_bytes)
    except ValueError as e:
        return err(str(e), 422)
    except Exception as e:
        logging.exception('PDF text extraction failed')
        return err(f'Could not read PDF: {e}', 500)

    # A real multi-page statement is mostly legal boilerplate — send the
    # model a condensed version so it stays focused on account data instead
    # of drifting into summarizing disclosure text. Validation below still
    # runs against the FULL untrimmed text, never the condensed prompt.
    prompt_text = ps.condense_for_prompt(statement_text)

    ai_text = _ai_complete_text(ps.PDF_STATEMENT_SYSTEM_PROMPT, ps.build_user_prompt(prompt_text))
    if not ai_text:
        return ok({'ai_available': False, 'reason': 'no_model',
                    'message': ("Reading a PDF statement needs a local AI model, and this computer isn't "
                                "running one. Download your transactions from your bank as a CSV or QFX "
                                "file instead - those import without AI.")})

    try:
        raw = ps.parse_json_response(ai_text)
    except (ValueError, json.JSONDecodeError):
        return err('The model did not return valid JSON for this statement. '
                    'Try again, or enter this statement manually.', 502)

    cleaned, warnings = ps.validate_and_clean(raw, statement_text)

    # Normalize into bank_importer's exact record shape — the SAME shape
    # /api/import/commit already expects from CSV/OFX/QIF, so PDF-sourced
    # transactions get identical dedup, categorization, and B3.5/B6b handling.
    from bank_importer import auto_category
    records = []
    for t in cleaned['transactions']:
        txn_type = t.get('type') if t.get('type') in ('debit', 'credit') else 'debit'
        records.append({
            'date':         t.get('date'),
            'description':  (t.get('description') or '').strip(),
            'amount':       abs(float(t.get('amount', 0))),
            'type':         txn_type,
            'category':     auto_category(t.get('description') or ''),
            'raw_category': '',
            'cleared':      True,
            'source':       'pdf',
        })

    from bank_importer import get_category_summary
    result = {
        'bank':             'Credit Card',
        'records':          records,        # full list — client stores for commit step
        'records_count':    len(records),
        'category_summary': get_category_summary(records),
        'sample_records':   records[:5],    # matches /api/import/preview's contract —
                                             # renderImportPreview() reuses that renderer
        'summary':          cleaned['summary'],
        'warnings':         warnings,
        'cached':           False,
    }

    try:
        with db_session() as session:
            session.add(PdfExtractCache(
                source_hash=source_hash, issuer=ps.ISSUER_GENERIC,
                extracted_json=json.dumps(result),
            ))
            session.commit()
    except Exception as e:
        logging.warning('PDF extract cache write failed: %s', e)

    return ok({**result, 'source_hash': source_hash})


@debt_bp.route('/pdf-reconcile', methods=['POST'])
@require_json
def debt_pdf_reconcile():
    """
    4D — the point of the whole feature. Writes the PDF statement's own
    authoritative figures (not transaction-derived sums) into
    debt_balance_history and the debt card itself. Call AFTER
    /api/import/commit has already landed the statement's transactions —
    this reads the debt's current_balance (by then already updated by B3.5
    from the newly-committed transactions) as the "implied" balance and
    cross-checks it against the statement's own stated balance before the
    stated figure overwrites it.
    Body: { debt_id, summary: {newBalance, apr, minimumPayment,
            interestCharged, paymentReceived, statementPeriod} }
    """
    body    = request.json or {}
    debt_id = body.get('debt_id')
    summary = body.get('summary') or {}
    if not debt_id:
        return err('debt_id required')

    period = summary.get('statementPeriod')
    if not period or len(str(period)) < 7:
        return err('summary.statementPeriod is required — this statement has no readable closing date')
    month = str(period)[:7]

    new_balance = summary.get('newBalance')
    if new_balance is None:
        return err('summary.newBalance is required — a statement without a readable balance cannot be reconciled')
    new_balance = round(float(new_balance), 2)

    apr               = summary.get('apr')
    min_payment       = summary.get('minimumPayment')
    interest_charged  = summary.get('interestCharged')
    payment_received  = summary.get('paymentReceived')

    with db_session() as session:
        debt = session.query(DebtAccount).filter_by(id=int(debt_id)).first()
        if not debt:
            return err('Debt account not found', 404)

        implied_balance = debt.current_balance

        existing = session.query(DebtBalanceHistory).filter_by(debt_id=debt.id, month=month).first()
        if existing:
            existing.balance              = new_balance
            existing.payment              = round(float(payment_received), 2) if payment_received is not None else existing.payment
            existing.min_payment          = round(float(min_payment), 2) if min_payment is not None else existing.min_payment
            existing.apr                  = float(apr) if apr is not None else existing.apr
            existing.interest_charged     = round(float(interest_charged), 2) if interest_charged is not None else existing.interest_charged
            existing.statement_period_end = str(period)
        else:
            session.add(DebtBalanceHistory(
                debt_id=debt.id, month=month,
                balance=new_balance,
                payment=round(float(payment_received), 2) if payment_received is not None else 0.0,
                min_payment=round(float(min_payment), 2) if min_payment is not None else round(float(debt.minimum_payment or 0), 2),
                apr=float(apr) if apr is not None else debt.interest_rate,
                interest_charged=round(float(interest_charged), 2) if interest_charged is not None else None,
                statement_period_end=str(period),
            ))

        # The statement's own printed balance wins over anything derived from
        # our own transaction arithmetic — that's the entire point of this
        # feature (Blueprint §6): a verified figure, not an inference.
        debt.current_balance = new_balance
        previous_apr, previous_min = debt.interest_rate, debt.minimum_payment
        previous_apr_source, previous_min_source = debt.interest_rate_source, debt.minimum_payment_source
        if apr is not None:
            debt.interest_rate = float(apr)
            debt.interest_rate_source = 'statement'   # V2
        if min_payment is not None:
            debt.minimum_payment = round(float(min_payment), 2)
            debt.minimum_payment_source = 'statement'

        session.commit()

        balance_check = {
            'implied':  implied_balance,
            'stated':   new_balance,
            'diff':     round(new_balance - implied_balance, 2) if implied_balance is not None else None,
            'matches':  implied_balance is not None and abs(new_balance - implied_balance) < 0.01,
        }
        result = {
            'debt_id': debt.id, 'debt_name': debt.name,
            'new_balance': debt.current_balance, 'month': month,
            'balance_check': balance_check,
            # V2: the figures the page must take up (so a later save cannot
            # send the old ones back), and what they replaced, for the toast.
            'interest_rate': debt.interest_rate, 'minimum_payment': debt.minimum_payment,
            'previous_interest_rate': previous_apr, 'previous_minimum_payment': previous_min,
            'previous_interest_rate_source': previous_apr_source,
            'previous_minimum_payment_source': previous_min_source,
            'statement_period_end': str(period),
        }

    return ok(result)


# CFPB guidance URL — stored as a constant so it can be updated if the URL changes.
CFPB_CANT_PAY_URL = (
    'https://www.consumerfinance.gov/ask-cfpb/'
    'what-should-i-do-if-i-cant-pay-my-credit-card-bills-en-1697/'
)


# ── Debt Reconciliation (Phase A: data layer) ──────────────────────────────────
# Debt Reconciliation Blueprint, Phase A. Query helpers + serializers only —
# no routes yet (those land with the UI in Phases B-D). Two helpers from the
# blueprint's original Phase A list are deliberately not implemented here:
#   - logHistorianEvent(): there is no historian_entries table in this
#     codebase yet (see GROUNDWORK_1_0_ROADMAP.md Phase H1) — writing to a
#     table that doesn't exist isn't an option, and a stub that discards the
#     event would just be dead code. Lands in Phase H1.
#   - getPayoffPlanSuggestedAmount(): there is no persisted payoff-plan
#     entity in this codebase — payoff projections are computed client-side
#     on demand (_calcDebtIntelligence in app.js), not stored. Phase E has
#     to decide how a suggested amount gets computed server-side; faking one
#     now would be a half-finished implementation.

def serialize_debt_ledger_entry(e: DebtLedgerEntry) -> dict:
    return {
        'id':                              e.id,
        'debt_account_id':                 e.debt_account_id,
        'entry_type':                      e.entry_type,
        'amount':                          e.amount,
        'entry_date':                      e.entry_date.isoformat() if e.entry_date else None,
        'description':                     e.description or '',
        'category':                        e.category or '',
        'merchant':                        e.merchant or '',
        'linked_checking_transaction_id':  e.linked_checking_transaction_id,
        'source_type':                     e.source_type,
        'created_at':                      e.created_at.isoformat() if e.created_at else None,
        'updated_at':                      e.updated_at.isoformat() if e.updated_at else None,
    }


def serialize_recurring_debt_payment(r: RecurringDebtPayment) -> dict:
    return {
        'id':                          r.id,
        'debt_account_id':             r.debt_account_id,
        'scheduled_date_of_month':     r.scheduled_date_of_month,
        'amount':                      r.amount,
        'frequency':                   r.frequency,
        'is_active':                   r.is_active,
        'is_auto_confirm':             r.is_auto_confirm,
        'created_at':                  r.created_at.isoformat() if r.created_at else None,
        'last_confirmed_at':           r.last_confirmed_at.isoformat() if r.last_confirmed_at else None,
        'last_executed_at':            r.last_executed_at.isoformat() if r.last_executed_at else None,
        'created_from_transaction_id': r.created_from_transaction_id,
    }


def serialize_checking_transaction_link(link: CheckingTransactionLink) -> dict:
    return {
        'id':                        link.id,
        'checking_transaction_id':   link.checking_transaction_id,
        'debt_ledger_entry_id':      link.debt_ledger_entry_id,
        'link_indicator':            link.link_indicator,
        'created_at':                link.created_at.isoformat() if link.created_at else None,
        'user_confirmed_at':         link.user_confirmed_at.isoformat() if link.user_confirmed_at else None,
    }


def get_debt_ledger_for_account(session, account_id: int, start_date=None, end_date=None) -> list:
    """All debt ledger entries for an account, newest first. Caller supplies
    an open session (matches this file's convention — see list_transactions)."""
    q = session.query(DebtLedgerEntry).filter_by(debt_account_id=account_id)
    if start_date:
        q = q.filter(DebtLedgerEntry.entry_date >= start_date)
    if end_date:
        q = q.filter(DebtLedgerEntry.entry_date <= end_date)
    return q.order_by(DebtLedgerEntry.entry_date.desc(), DebtLedgerEntry.id.desc()).all()


def get_recurring_payments_due(session, range_start, range_end) -> list:
    """Active recurring payments whose scheduled_date_of_month falls within
    [range_start, range_end] for the months that range spans. Phase C's
    scheduler calls this with a 3-5 day lookahead window; this function only
    resolves *which* recurring patterns are due, not draft generation itself
    (that's Phase C)."""
    from calendar import monthrange

    recurring = session.query(RecurringDebtPayment).filter_by(is_active=True).all()
    due = []
    # Walk each calendar month the range touches (almost always 1, occasionally
    # 2 near a month boundary) so "last day of month" (None) resolves correctly
    # per month rather than assuming range_start's month throughout.
    months_seen = set()
    cursor = date(range_start.year, range_start.month, 1)
    while cursor <= range_end:
        months_seen.add((cursor.year, cursor.month))
        cursor = date(cursor.year + (cursor.month == 12), (cursor.month % 12) + 1, 1)

    for r in recurring:
        if r.frequency != 'monthly':
            # weekly/biweekly due-date math isn't defined by a day-of-month
            # field — out of scope until a phase actually needs it.
            continue
        for (yr, mo) in months_seen:
            last_day = monthrange(yr, mo)[1]
            day = r.scheduled_date_of_month or last_day
            day = min(day, last_day)   # e.g. "31st" in a 30-day month
            due_date = date(yr, mo, day)
            if range_start <= due_date <= range_end:
                due.append({'recurring': r, 'due_date': due_date})
    return due


def get_checking_transaction_link(session, checking_transaction_id: int) -> 'CheckingTransactionLink | None':
    """The link row for a checking transaction, if it's been linked to a debt
    payment. Returns None (not an empty list) — a checking transaction can be
    linked to at most one debt entry, enforced by the unique constraint."""
    return session.query(CheckingTransactionLink).filter_by(
        checking_transaction_id=checking_transaction_id
    ).first()


_LEDGER_ENTRY_TYPES = {'charge', 'payment', 'interest', 'fee'}


def _apply_ledger_balance_effect(debt: DebtAccount, entry: DebtLedgerEntry, sign: int = 1):
    """
    Debt Reconciliation Phase E. Adjust a debt account's current_balance by
    a ledger entry's real-money effect: sign=+1 when the entry newly takes
    effect (created as manual, or a draft just confirmed), sign=-1 to
    reverse it (the entry is being deleted).

    Only call this for an entry that actually represents money having
    moved — never for 'draft' or 'skipped' source_type. Without this, the
    ledger is cosmetic: a user could log $500 of charges and $300 of
    payments and never see the card balance (or the avalanche/snowball
    payoff projection, which reads current_balance) reflect any of it —
    the entire point of "reconciliation" is that this number is real.
    """
    delta = entry.amount if entry.entry_type in ('charge', 'interest', 'fee') else -entry.amount
    # An unknown balance plus a charge is still unknown (V6): no figure is
    # invented by adding a change to a number nobody entered.
    if debt.current_balance is None:
        return
    debt.current_balance = round(debt.current_balance + sign * delta, 2)


@debt_bp.route('/<int:debt_id>/ledger', methods=['GET'])
def list_debt_ledger(debt_id):
    with db_session() as session:
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('Not found', 404)
        entries = get_debt_ledger_for_account(session, debt_id)
        return ok([serialize_debt_ledger_entry(e) for e in entries])


@debt_bp.route('/<int:debt_id>/ledger', methods=['POST'])
@require_json
def create_debt_ledger_entry(debt_id):
    body = request.json
    entry_type = body.get('entry_type')
    if entry_type not in _LEDGER_ENTRY_TYPES:
        return err(f"entry_type must be one of {sorted(_LEDGER_ENTRY_TYPES)}")
    try:
        amount = float(body.get('amount'))
    except (TypeError, ValueError):
        return err('amount must be a number')
    if amount <= 0:
        return err('amount must be greater than 0')

    entry_date = date.today()
    if body.get('entry_date'):
        try:
            entry_date = date.fromisoformat(body['entry_date'])
        except ValueError:
            return err('entry_date must be YYYY-MM-DD')

    with db_session() as session:
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('Not found', 404)

        entry = DebtLedgerEntry(
            debt_account_id=debt_id,
            entry_type=entry_type,
            amount=amount,
            entry_date=entry_date,
            description=(body.get('description') or '').strip(),
            category=(body.get('category') or '').strip(),
            merchant=(body.get('merchant') or '').strip(),
            source_type='manual',
        )
        session.add(entry)
        session.flush()   # get entry.id before optionally linking

        linked_txn_id = body.get('linked_checking_transaction_id')
        if linked_txn_id:
            txn = session.get(Transaction, linked_txn_id)
            if not txn:
                session.rollback()
                return err('linked_checking_transaction_id not found', 404)
            if get_checking_transaction_link(session, linked_txn_id):
                session.rollback()
                return err('That checking transaction is already linked to a debt entry')
            entry.linked_checking_transaction_id = linked_txn_id
            _new_link = CheckingTransactionLink(
                checking_transaction_id=linked_txn_id,
                debt_ledger_entry_id=entry.id,
                link_indicator='payment_to_card' if entry_type == 'payment' else 'charge_from_card',
                user_confirmed_at=datetime.now(),
            )
            session.add(_new_link)
            if entry_type == 'payment':                  # item 93 B11: the household's statement, when someone is answering
                session.flush()
                from core import household_statements as _hs
                _hs.carry_new(session, 'debt', _new_link.id)

        _apply_ledger_balance_effect(debt, entry, sign=1)
        if entry_type == 'charge':
            log_historian_event(
                session, 'charge_observation', debt_account_id=debt_id,
                actual_value=amount, context={'merchant': entry.merchant, 'entry_id': entry.id},
            )
        session.commit()
        return ok(serialize_debt_ledger_entry(entry), status=201)


@debt_bp.route('/ledger/<int:entry_id>', methods=['DELETE'])
def delete_debt_ledger_entry(entry_id):
    with db_session() as session:
        entry = session.get(DebtLedgerEntry, entry_id)
        if not entry:
            return err('Not found', 404)
        # A link row FKs to this entry with no ON DELETE CASCADE (SQLite
        # default) — remove it first or it dangles.
        session.query(CheckingTransactionLink).filter_by(
            debt_ledger_entry_id=entry_id
        ).delete()
        # Reverse the balance effect — but only if this entry ever applied
        # one. 'draft'/'skipped' entries never touched current_balance, so
        # reversing them here would incorrectly move the balance.
        if entry.source_type not in ('draft', 'skipped'):
            debt = session.get(DebtAccount, entry.debt_account_id)
            if debt:
                _apply_ledger_balance_effect(debt, entry, sign=-1)
        session.delete(entry)
        session.commit()
        return ok({'deleted': entry_id})


@debt_bp.route('/<int:debt_id>/linkable-transactions', methods=['GET'])
def list_linkable_transactions(debt_id):
    """Recent transactions on this debt card's linked checking/credit account
    that aren't already linked to a debt ledger entry — candidates for the
    "+ Payment → link to checking" dropdown (Phase B)."""
    with db_session() as session:
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('Not found', 404)
        if not debt.linked_account_id:
            return ok([])

        linked_entry_txn_ids = {
            row[0] for row in session.query(CheckingTransactionLink.checking_transaction_id).all()
        }
        txns = session.query(Transaction).filter_by(
            account_id=debt.linked_account_id
        ).order_by(Transaction.date.desc(), Transaction.id.desc()).limit(50).all()

        candidates = [t for t in txns if t.id not in linked_entry_txn_ids]
        return ok([{
            'id': t.id, 'date': t.date.isoformat(), 'amount': t.amount,
            'type': t.type, 'description': t.description or '', 'merchant': t.merchant or '',
        } for t in candidates])


# ── Debt Reconciliation Phase C: recurring payment drafts ──────────────────────
_FREQUENCIES = {'monthly', 'biweekly', 'weekly'}


def generate_recurring_payment_drafts(session, lookahead_days: int = 5) -> list:
    """Materialize draft ledger entries for recurring payments due within the
    lookahead window. Idempotent: a (recurring pattern, due date) pair that
    already has an entry — draft or already-confirmed — is never duplicated,
    so this is safe to call on every debt-page load rather than needing a
    real background scheduler (this is a desktop app with no daemon)."""
    today_ = date.today()
    due = get_recurring_payments_due(session, today_, today_ + timedelta(days=lookahead_days))
    created = []
    for item in due:
        r, due_date = item['recurring'], item['due_date']
        exists = session.query(DebtLedgerEntry).filter_by(
            linked_recurring_payment_id=r.id, entry_date=due_date
        ).first()
        if exists:
            continue
        draft = DebtLedgerEntry(
            debt_account_id=r.debt_account_id,
            entry_type='payment',
            amount=r.amount,
            entry_date=due_date,
            description='Recurring payment (draft)',
            source_type='draft',
            linked_recurring_payment_id=r.id,
        )
        session.add(draft)
        created.append(draft)
    if created:
        session.commit()
    return created


def _validate_recurring_payload(body: dict):
    """Shared validation for create/update. Returns (cleaned_fields, error_or_None)."""
    fields = {}
    if 'amount' in body:
        try:
            amt = float(body['amount'])
        except (TypeError, ValueError):
            return None, 'amount must be a number'
        if amt <= 0:
            return None, 'amount must be greater than 0'
        fields['amount'] = amt
    if 'frequency' in body:
        if body['frequency'] not in _FREQUENCIES:
            return None, f'frequency must be one of {sorted(_FREQUENCIES)}'
        fields['frequency'] = body['frequency']
    if 'scheduled_date_of_month' in body:
        sched = body['scheduled_date_of_month']
        if sched is not None:
            try:
                sched = int(sched)
                if not (1 <= sched <= 31):
                    raise ValueError
            except (TypeError, ValueError):
                return None, 'scheduled_date_of_month must be an integer 1-31'
        fields['scheduled_date_of_month'] = sched
    if 'is_active' in body:
        fields['is_active'] = bool(body['is_active'])
    return fields, None


def get_payment_compliance(session, recurring_id: int) -> dict:
    """
    Debt Reconciliation Phase E. On-time/under-plan/over-plan counts and
    average variance % for a recurring pattern's confirmed payments, compared
    against the pattern's own saved amount — the closest thing to "the plan"
    this codebase has. No persisted payoff-plan table exists here (payoff
    projections are computed client-side on demand, not stored — see Phase
    A/E notes), so this reads "the plan" as what the user told the recurring
    pattern to expect, not a payoff-plan entity's suggestion.
    """
    rp = session.get(RecurringDebtPayment, recurring_id)
    empty = {'total': 0, 'on_time': 0, 'under_plan': 0, 'over_plan': 0, 'avg_variance_pct': None}
    if not rp or not rp.amount:
        return empty
    entries = session.query(DebtLedgerEntry).filter_by(
        linked_recurring_payment_id=recurring_id, source_type='manual'
    ).all()
    if not entries:
        return empty
    variances = [((e.amount - rp.amount) / rp.amount) * 100 for e in entries]
    return {
        'total':            len(entries),
        'on_time':          sum(1 for v in variances if abs(v) <= 5),
        'under_plan':       sum(1 for v in variances if v < -5),
        'over_plan':        sum(1 for v in variances if v > 5),
        'avg_variance_pct': round(sum(variances) / len(variances), 1),
    }


@debt_bp.route('/<int:debt_id>/confidence', methods=['GET'])
def debt_payoff_confidence(debt_id):
    """Phase H2 Feature 5 (adaptive learning — payoff confidence scoring).
    Thin wrapper around Phase H1's get_payment_compliance_confidence —
    that function already IS this feature; H1 built it in anticipation of
    this exact use, per its own docstring."""
    with db_session() as session:
        if not session.get(DebtAccount, debt_id):
            return err('Not found', 404)
        return ok(get_payment_compliance_confidence(session, debt_id))


@debt_bp.route('/<int:debt_id>/recurring', methods=['GET'])
def list_recurring_payments(debt_id):
    with db_session() as session:
        if not session.get(DebtAccount, debt_id):
            return err('Not found', 404)
        rows = session.query(RecurringDebtPayment).filter_by(
            debt_account_id=debt_id
        ).order_by(RecurringDebtPayment.created_at.desc()).all()
        result = []
        for r in rows:
            row = serialize_recurring_debt_payment(r)
            row['compliance'] = get_payment_compliance(session, r.id)
            result.append(row)
        return ok(result)


@debt_bp.route('/<int:debt_id>/recurring', methods=['POST'])
@require_json
def create_recurring_payment(debt_id):
    fields, error = _validate_recurring_payload(request.json)
    if error:
        return err(error)
    if 'amount' not in fields:
        return err('amount is required')

    with db_session() as session:
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('Not found', 404)
        r = RecurringDebtPayment(
            debt_account_id=debt_id,
            amount=fields['amount'],
            frequency=fields.get('frequency', 'monthly'),
            scheduled_date_of_month=fields.get('scheduled_date_of_month'),
            is_active=True,
        )
        session.add(r)
        session.commit()
        return ok(serialize_recurring_debt_payment(r), status=201)


@debt_bp.route('/recurring/<int:rid>', methods=['PATCH'])
@require_json
def update_recurring_payment(rid):
    fields, error = _validate_recurring_payload(request.json)
    if error:
        return err(error)
    with db_session() as session:
        r = session.get(RecurringDebtPayment, rid)
        if not r:
            return err('Not found', 404)
        for k, v in fields.items():
            setattr(r, k, v)
        session.commit()
        return ok(serialize_recurring_debt_payment(r))


@debt_bp.route('/recurring/<int:rid>', methods=['DELETE'])
def delete_recurring_payment(rid):
    """Soft-delete: mark inactive rather than removing the row — preserves
    the audit trail for any drafts/confirmed entries this pattern already
    generated, and matches the blueprint's stated behavior."""
    with db_session() as session:
        r = session.get(RecurringDebtPayment, rid)
        if not r:
            return err('Not found', 404)
        r.is_active = False
        session.commit()
        return ok(serialize_recurring_debt_payment(r))


@debt_bp.route('/drafts/pending', methods=['GET'])
def list_pending_drafts():
    with db_session() as session:
        generate_recurring_payment_drafts(session)
        drafts = session.query(DebtLedgerEntry).filter_by(
            source_type='draft'
        ).order_by(DebtLedgerEntry.entry_date.asc()).all()
        result = []
        for d in drafts:
            debt = session.get(DebtAccount, d.debt_account_id)
            row = serialize_debt_ledger_entry(d)
            row['debt_account_name'] = debt.name if debt else ''
            result.append(row)
        return ok(result)


@debt_bp.route('/drafts/<int:entry_id>/confirm', methods=['POST'])
@require_json
def confirm_debt_draft(entry_id):
    body = request.json
    with db_session() as session:
        entry = session.get(DebtLedgerEntry, entry_id)
        if not entry or entry.source_type != 'draft':
            return err('Not found', 404)

        if body.get('amount') is not None:
            try:
                amt = float(body['amount'])
            except (TypeError, ValueError):
                return err('amount must be a number')
            if amt <= 0:
                return err('amount must be greater than 0')
            entry.amount = amt
        if body.get('entry_date'):
            try:
                entry.entry_date = date.fromisoformat(body['entry_date'])
            except ValueError:
                return err('entry_date must be YYYY-MM-DD')

        entry.source_type = 'manual'
        if entry.description == 'Recurring payment (draft)':
            entry.description = 'Recurring payment'

        rp = None
        if entry.linked_recurring_payment_id:
            rp = session.get(RecurringDebtPayment, entry.linked_recurring_payment_id)
            if rp:
                rp.last_confirmed_at = datetime.now()
                rp.last_executed_at = datetime.now()

        debt = session.get(DebtAccount, entry.debt_account_id)
        if debt:
            _apply_ledger_balance_effect(debt, entry, sign=1)   # draft → manual: takes effect now

        # Historian (Phase H1): log against the pattern's saved amount — "the
        # plan" — the same reference point Phase E's compliance math uses.
        if rp and rp.amount:
            variance_pct = round((entry.amount - rp.amount) / rp.amount * 100, 1)
            category = 'payment_confirmed' if abs(variance_pct) <= 5 else 'payment_amount_variance'
            log_historian_event(
                session, category, debt_account_id=entry.debt_account_id,
                expected_value=rp.amount, actual_value=entry.amount,
                context={'recurring_payment_id': rp.id, 'entry_id': entry.id},
            )

        session.commit()
        return ok(serialize_debt_ledger_entry(entry))


@debt_bp.route('/drafts/<int:entry_id>/skip', methods=['POST'])
def skip_debt_draft(entry_id):
    """Mark a single due-date occurrence as skipped — NOT a delete. Deleting
    would let generate_recurring_payment_drafts() see no entry for that
    (recurring, due_date) pair and silently regenerate the exact draft it
    was just told to skip on the next page load. The recurring pattern
    itself stays active; only this occurrence is dismissed."""
    with db_session() as session:
        entry = session.get(DebtLedgerEntry, entry_id)
        if not entry or entry.source_type != 'draft':
            return err('Not found', 404)
        entry.source_type = 'skipped'
        log_historian_event(
            session, 'payment_skipped', debt_account_id=entry.debt_account_id,
            expected_value=entry.amount,
            context={'recurring_payment_id': entry.linked_recurring_payment_id, 'entry_id': entry.id},
        )
        session.commit()
        return ok(serialize_debt_ledger_entry(entry))


# ── Debt Reconciliation Phase D: checking transaction linking ──────────────────

@debt_bp.route('/ledger/<int:entry_id>', methods=['GET'])
def get_debt_ledger_entry(entry_id):
    """Single-entry lookup — used by the checking ledger's 💳 jump-to-entry
    navigation to find which debt account (and therefore which card to
    expand) a linked entry belongs to."""
    with db_session() as session:
        entry = session.get(DebtLedgerEntry, entry_id)
        if not entry:
            return err('Not found', 404)
        return ok(serialize_debt_ledger_entry(entry))


@debt_bp.route('/ledger/<int:entry_id>/unlink', methods=['POST'])
def unlink_debt_ledger_entry(entry_id):
    """Remove the association between a debt entry and a checking
    transaction WITHOUT deleting either side — distinct from Phase B's
    DELETE /ledger/<id>, which removes the debt entry entirely. Unlink is
    for "these were never actually the same payment"; delete is for
    "this entry shouldn't exist." Callable from either the debt ledger or
    the checking ledger, since both know the debt entry id (the checking
    ledger gets it from GET /transactions' linked_debt_entry_id field)."""
    with db_session() as session:
        entry = session.get(DebtLedgerEntry, entry_id)
        if not entry:
            return err('Not found', 404)
        session.query(CheckingTransactionLink).filter_by(debt_ledger_entry_id=entry_id).delete()
        entry.linked_checking_transaction_id = None
        session.commit()
        return ok(serialize_debt_ledger_entry(entry))


@transactions_bp.route('/<int:txn_id>/link-debt', methods=['POST'])
@require_json
def link_checking_txn_to_debt(txn_id):
    """Link an EXISTING checking transaction to a debt account, initiated
    from the checking ledger side (mirror of Phase B's create_debt_ledger_entry,
    which links from the debt-card side by creating the debt entry first).
    Creates a new debt_ledger_entries row + the link in one call; amount/date
    default from the checking transaction itself."""
    body = request.json
    debt_id = body.get('debt_account_id')
    if not debt_id:
        return err('debt_account_id is required')

    with db_session() as session:
        txn = session.get(Transaction, txn_id)
        if not txn:
            return err('Not found', 404)
        debt = session.get(DebtAccount, debt_id)
        if not debt:
            return err('debt_account_id not found', 404)
        if get_checking_transaction_link(session, txn_id):
            return err('That checking transaction is already linked to a debt entry')

        # Linking from the checking side is specifically "this movement of
        # money WAS a payment toward this debt" (the blueprint's own example:
        # "Transfer to Capital One $500" tagged as a payment) — always
        # 'payment', regardless of the checking transaction's debit/credit
        # type, rather than guessing at 'charge' for the rare credit case.
        entry = DebtLedgerEntry(
            debt_account_id=debt_id,
            entry_type='payment',
            amount=abs(txn.amount),
            entry_date=txn.date,
            description=(body.get('description') or '').strip(),
            source_type='manual',
            linked_checking_transaction_id=txn_id,
        )
        session.add(entry)
        session.flush()
        _new_link = CheckingTransactionLink(
            checking_transaction_id=txn_id,
            debt_ledger_entry_id=entry.id,
            link_indicator='payment_to_card',
            user_confirmed_at=datetime.now(),
        )
        session.add(_new_link)
        session.flush()
        from core import household_statements as _hs
        _hs.carry_new(session, 'debt', _new_link.id)     # item 93 B11: the household's statement, when someone is answering
        _apply_ledger_balance_effect(debt, entry, sign=1)
        session.commit()
        return ok(serialize_debt_ledger_entry(entry), status=201)


# ── Historian Infrastructure (Phase H1) ─────────────────────────────────────────
# GROUNDWORK_1_0_ROADMAP.md Phase H1. Genuinely new construction — see
# HistorianEntry's docstring in core/database.py for why. Query helpers here
# split into two groups: three read from event types Phase H1 itself starts
# writing (wired into the debt-reconciliation routes below); four are
# 1.1-scaffold reads for event types nothing writes yet (Phase H2 wires the
# writers when it builds each adaptive feature) — each returns an honest
# empty/neutral result rather than fabricating one in the meantime.

def log_historian_event(session, event_category: str, debt_account_id=None, category_id=None,
                         expected_value=None, actual_value=None, context=None):
    """Atomic historian insert. Computes variance_pct/variance_amount when
    both expected_value and actual_value are given; leaves them null
    otherwise rather than guessing. context is a plain dict, stored as JSON."""
    variance_amount = None
    variance_pct = None
    if expected_value is not None and actual_value is not None:
        variance_amount = round(actual_value - expected_value, 2)
        if expected_value:
            variance_pct = round((variance_amount / expected_value) * 100, 1)
    entry = HistorianEntry(
        event_category=event_category,
        debt_account_id=debt_account_id,
        category_id=category_id,
        expected_value=expected_value,
        actual_value=actual_value,
        variance_pct=variance_pct,
        variance_amount=variance_amount,
        context_json=json.dumps(__import__('core.health_boundary', fromlist=['scrub_obj']).scrub_obj(context)) if context else None,   # H6 P8
    )
    session.add(entry)
    return entry


historian_bp = Blueprint('historian', __name__)

# Engagement / session events the client signals directly — page navigations
# and app close — as opposed to the domain events logged inline by the route
# where the thing actually happens (a confirm, a ledger write, a budget edit).
# Whitelisted so a compromised or buggy client can't inject arbitrary event
# categories into the historian. session_start is NOT here: it's logged
# server-side in bootstrap(), the one request guaranteed to fire on app open.
_CLIENT_ENGAGEMENT_EVENTS = {'session_end', 'budget_reviewed'}


@historian_bp.route('/engagement', methods=['POST'])
@require_json
def log_engagement_event():
    """Client-signaled engagement event. Body: { event: str, context?: dict }.
    Only whitelisted, purely-categorical events are accepted — these are
    "it happened" markers, so they carry no expected/actual values and never
    fabricate a variance. session_end arrives via a keepalive fetch on page
    hide, so this stays cheap and the client never reads the response."""
    body  = request.json
    event = (body.get('event') or '').strip()
    if event not in _CLIENT_ENGAGEMENT_EVENTS:
        return err('unknown engagement event')
    ctx = body.get('context')
    if not isinstance(ctx, dict):
        ctx = None
    with db_session() as session:
        log_historian_event(session, event, context=ctx)
        session.commit()
    return ok({'logged': True})


def get_engagement_streak(session) -> dict:
    """The historian's first *engagement* reader — a habit signal, not a pace
    score like the confidence readers. Consecutive-day check-in streak from
    session_start events (distinct days, so many launches/refreshes in one day
    count once), plus this month's budget_reviewed count. Local day boundaries,
    matching how created_at is stored (item 109). Honest zero shape when there's no
    history yet — the UI self-gates on streak_days the same way the confidence
    cards gate on a null score."""
    starts = session.query(HistorianEntry.created_at).filter(
        HistorianEntry.event_category == 'session_start').all()
    days = sorted({c.date() for (c,) in starts if c is not None}, reverse=True)
    today = datetime.now().date()
    streak = 0
    # A streak stays alive if the most recent check-in was today or yesterday;
    # not opening the app *yet today* shouldn't read as broken until a full day
    # has lapsed.
    if days and days[0] >= today - timedelta(days=1):
        streak = 1
        for newer, older in zip(days, days[1:]):
            if (newer - older).days == 1:
                streak += 1
            else:
                break
    month_start = datetime(today.year, today.month, 1)
    reviews = session.query(HistorianEntry).filter(
        HistorianEntry.event_category == 'budget_reviewed',
        HistorianEntry.created_at >= month_start).count()
    return {
        'streak_days':               streak,
        'active_today':              bool(days) and days[0] == today,
        'budget_reviews_this_month': reviews,
    }


@historian_bp.route('/streak', methods=['GET'])
def engagement_streak():
    """Thin read of get_engagement_streak — the dashboard check-in streak.
    Mirrors the confidence routes: a plain ok(...) the client self-gates on."""
    with db_session() as session:
        return ok(get_engagement_streak(session))


def _months_between(start_str: str, end_str: str) -> int:
    """Whole calendar months between two 'YYYY-MM' or 'YYYY-MM-DD' strings."""
    sy, sm = int(start_str[:4]), int(start_str[5:7])
    ey, em = int(end_str[:4]), int(end_str[5:7])
    return (ey - sy) * 12 + (em - sm)


def _log_net_worth_milestone_variance(session, month_key: str, net_worth: float):
    """
    Net worth's Historian write-hook — this module's mirror of the debt
    reconciliation write-hooks above, called from create_snapshot() below.

    Milestones aren't a DB table (see HistorianEntry docstring) — they live
    in AppSetting.nw_goals_json, a JSON array app.js manages. A milestone is
    only eligible once it carries id/startAmount/startDate, which app.js
    stamps on new milestones going forward; milestones saved before this
    existed lack those fields and are silently skipped here rather than
    backfilling a guessed start point for them.
    """
    try:
        goals_row = session.query(AppSetting).filter_by(key='nw_goals_json').first()
        goals = json.loads(goals_row.value) if goals_row and goals_row.value else []
    except (json.JSONDecodeError, TypeError):
        return
    for goal in goals:
        gid        = goal.get('id')
        start_amt  = goal.get('startAmount')
        start_date = goal.get('startDate')
        target_amt = goal.get('amount')
        target_date = goal.get('date')
        if gid is None or start_amt is None or not start_date or not target_date or target_amt is None:
            continue
        try:
            total_months   = _months_between(start_date, target_date)
            elapsed_months = _months_between(start_date, month_key)
        except (ValueError, IndexError):
            continue
        if total_months <= 0:
            continue  # target at/before start — no valid pace to compare against
        expected = start_amt + (target_amt - start_amt) * (elapsed_months / total_months)
        log_historian_event(
            session, 'net_worth_milestone_variance',
            expected_value=round(expected, 2), actual_value=round(net_worth, 2),
            context={'milestone_id': gid, 'milestone_name': goal.get('name', '')},
        )


def get_net_worth_milestone_confidence(session, milestone_id, months: int = 12) -> dict:
    """0-100 pace confidence for a net worth milestone, from real snapshot
    variance history logged by _log_net_worth_milestone_variance. Mirrors
    get_payment_compliance_confidence's shape and honesty rule: returns
    confidence=None (not a fabricated number) when there's no snapshot
    history yet for this milestone, rather than guessing from the static
    linear projection the UI already shows without any history at all."""
    cutoff = datetime.now() - timedelta(days=30 * months)
    entries = session.query(HistorianEntry).filter(
        HistorianEntry.event_category == 'net_worth_milestone_variance',
        HistorianEntry.created_at >= cutoff,
    ).all()
    matched = []
    for e in entries:
        try:
            ctx = json.loads(e.context_json or '{}')
        except (json.JSONDecodeError, TypeError):
            continue
        if str(ctx.get('milestone_id')) == str(milestone_id):
            matched.append(e)
    # Item 38 P5: a $0 actual logged on a day an all-zero snapshot was written is the paid-off marker's, not a net
    # worth. Such events carry no month or snapshot link, so the same day and the same $0 are the evidence; they are
    # left out, and the result says how many.
    zero_days = {r.created_at.date() for r in session.query(NetWorthSnapshot).all()
                 if _snapshot_without_figures(r) and r.created_at}
    left_out = [e for e in matched if (e.actual_value or 0) == 0 and e.created_at and e.created_at.date() in zero_days]
    matched = [e for e in matched if e not in left_out]
    note = (f' {len(left_out)} reading(s) of $0 left out: logged the day a snapshot was recorded without figures.'
            if left_out else '')
    if not matched:
        return {'confidence_pct': None, 'trend': None, 'avg_variance_pct': None,
                'samples': 0, 'left_out': len(left_out),
                'reasoning': 'No snapshot history yet for this milestone.' + note}
    variances = [e.variance_pct for e in matched if e.variance_pct is not None]
    if not variances:
        return {'confidence_pct': None, 'trend': None, 'avg_variance_pct': None,
                'samples': len(matched), 'left_out': len(left_out), 'reasoning': 'No variance data yet.' + note}
    avg_variance = sum(variances) / len(variances)
    # variance_pct = (actual-expected)/expected*100 — positive means AHEAD of
    # pace, which never lowers confidence; only running behind pace does.
    confidence = max(0, min(100, round(100 + min(0, avg_variance) * 2)))
    trend = 'ahead' if avg_variance > 5 else 'behind' if avg_variance < -5 else 'on_pace'
    return {
        'confidence_pct': confidence, 'trend': trend,
        'avg_variance_pct': round(avg_variance, 1), 'samples': len(matched), 'left_out': len(left_out),
        'reasoning': f'{len(matched)} snapshot(s) tracked, {trend.replace("_", " ")}' + note,
    }


def _log_investment_allocation_drift(session):
    """
    Investments' Historian write-hook — this module's mirror of
    _log_net_worth_milestone_variance, called from POST
    /api/investments/prices/refresh (the natural "checkpoint" action, same
    idea as debt's payment-confirm and net worth's snapshot-save).

    Target allocation isn't a DB table either (AppSetting's inv_target_alloc,
    a {asset_class: pct} dict app.js manages) — reuses
    _compute_portfolio_positions so the dollar figures logged here always
    match what the Investments page itself shows, never a second
    independent calculation quietly drifting out of sync with it.
    """
    try:
        targets_row = session.query(AppSetting).filter_by(key='inv_target_alloc').first()
        targets = json.loads(targets_row.value) if targets_row and targets_row.value else {}
    except (json.JSONDecodeError, TypeError):
        return
    if not targets:
        return  # no targets set — nothing to compare against

    positions, summary = _compute_portfolio_positions(session, skip_refresh=True)
    total = summary['total_market_value']
    if not total:
        return  # nothing priced yet — nothing meaningful to log
    if summary.get('unpriced'):
        # Item 35 V6: a holding with no price makes the total incomplete; a drift computed without it would be a
        # partial allocation recorded as if whole, and later read as evidence. Nothing is logged.
        return

    by_class = {}
    for p in positions:
        cls = p.get('asset_class')
        if cls and p['market_value'] is not None:
            by_class[cls] = by_class.get(cls, 0) + p['market_value']

    for cls, target_pct in targets.items():
        if not target_pct:
            continue
        expected = total * (target_pct / 100)
        actual = by_class.get(cls, 0)
        log_historian_event(
            session, 'investment_allocation_drift',
            expected_value=round(expected, 2), actual_value=round(actual, 2),
            context={'asset_class': cls},
        )


def get_investment_allocation_confidence(session, asset_class: str, months: int = 12) -> dict:
    """0-100 on-target confidence for one asset class, from real allocation
    drift history logged by _log_investment_allocation_drift. Mirrors
    get_net_worth_milestone_confidence's shape and honesty rule: returns
    confidence=None (not fabricated) when there's no refresh history yet."""
    cutoff = datetime.now() - timedelta(days=30 * months)
    entries = session.query(HistorianEntry).filter(
        HistorianEntry.event_category == 'investment_allocation_drift',
        HistorianEntry.created_at >= cutoff,
    ).all()
    matched = []
    for e in entries:
        try:
            ctx = json.loads(e.context_json or '{}')
        except (json.JSONDecodeError, TypeError):
            continue
        if ctx.get('asset_class') == asset_class:
            matched.append(e)
    if not matched:
        return {'confidence_pct': None, 'trend': None, 'avg_variance_pct': None,
                'samples': 0, 'reasoning': 'No price-refresh history yet for this asset class.'}
    variances = [e.variance_pct for e in matched if e.variance_pct is not None]
    if not variances:
        return {'confidence_pct': None, 'trend': None, 'avg_variance_pct': None,
                'samples': len(matched), 'reasoning': 'No variance data yet.'}
    avg_variance = sum(variances) / len(variances)
    # variance_pct = (actual-expected)/expected*100. Unlike net worth (where
    # running ahead of a savings goal is never bad), running either over OR
    # under an allocation target is equally off-target, so this scores on
    # |variance| rather than only penalizing the negative side.
    confidence = max(0, min(100, round(100 - abs(avg_variance) * 2)))
    trend = 'overweight' if avg_variance > 5 else 'underweight' if avg_variance < -5 else 'on_target'
    return {
        'confidence_pct': confidence, 'trend': trend,
        'avg_variance_pct': round(avg_variance, 1), 'samples': len(matched),
        'reasoning': f'{len(matched)} refresh(es) tracked, {trend.replace("_", " ")}',
    }


def _log_sinking_fund_contribution_variance(session, fund, actual_amount: float):
    """
    Sinking funds' Historian write-hook, called from POST
    .../deposit and POST .../auto-credit below. Unlike net worth/
    investments (which had to derive an "expected" figure from a linear
    projection or a % target), SinkingFund already has monthly_contribution
    — a real, user-set expectation — so this is closer to debt's
    payment_amount_variance: actual contribution vs. the fund's own stated
    pace. Skipped when monthly_contribution isn't set (auto-credit's
    deadline-derived fallback isn't a real expectation the user set, so
    comparing against it would trivially always read "on pace").
    """
    expected = float(fund.monthly_contribution or 0)
    if expected <= 0:
        return
    log_historian_event(
        session, 'sinking_fund_contribution_variance',
        expected_value=expected, actual_value=round(actual_amount, 2),
        context={'sinking_fund_id': fund.id},
    )


def get_sinking_fund_confidence(session, fund_id: int, months: int = 12) -> dict:
    """0-100 pace confidence for a sinking fund, from real contribution
    variance history. Mirrors get_net_worth_milestone_confidence's scoring
    (running ahead of a savings pace is never bad, only behind is)."""
    cutoff = datetime.now() - timedelta(days=30 * months)
    entries = session.query(HistorianEntry).filter(
        HistorianEntry.event_category == 'sinking_fund_contribution_variance',
        HistorianEntry.created_at >= cutoff,
    ).all()
    matched = []
    for e in entries:
        try:
            ctx = json.loads(e.context_json or '{}')
        except (json.JSONDecodeError, TypeError):
            continue
        if str(ctx.get('sinking_fund_id')) == str(fund_id):
            matched.append(e)
    if not matched:
        return {'confidence_pct': None, 'trend': None, 'avg_variance_pct': None,
                'samples': 0, 'reasoning': 'No contribution history yet for this fund.'}
    variances = [e.variance_pct for e in matched if e.variance_pct is not None]
    if not variances:
        return {'confidence_pct': None, 'trend': None, 'avg_variance_pct': None,
                'samples': len(matched), 'reasoning': 'No variance data yet.'}
    avg_variance = sum(variances) / len(variances)
    confidence = max(0, min(100, round(100 + min(0, avg_variance) * 2)))
    trend = 'ahead' if avg_variance > 5 else 'behind' if avg_variance < -5 else 'on_pace'
    return {
        'confidence_pct': confidence, 'trend': trend,
        'avg_variance_pct': round(avg_variance, 1), 'samples': len(matched),
        'reasoning': f'{len(matched)} contribution(s) tracked, {trend.replace("_", " ")}',
    }


def _log_college_fund_contribution_variance(session, fund_id, expected: float, actual_amount: float):
    """
    College funds' Historian write-hook, called from
    addCollegeContribution's server round-trip (settings PATCH) — see
    server.py's add_college_contribution route below. Same shape as
    sinking funds: expected is the fund's own monthlyContrib, only logged
    when the caller (app.js) actually has a positive one to compare against.
    """
    if expected <= 0:
        return
    log_historian_event(
        session, 'college_fund_contribution_variance',
        expected_value=round(expected, 2), actual_value=round(actual_amount, 2),
        context={'college_fund_id': fund_id},
    )


def get_college_fund_confidence(session, fund_id, months: int = 12) -> dict:
    """0-100 pace confidence for a college fund — identical shape and
    scoring to get_sinking_fund_confidence."""
    cutoff = datetime.now() - timedelta(days=30 * months)
    entries = session.query(HistorianEntry).filter(
        HistorianEntry.event_category == 'college_fund_contribution_variance',
        HistorianEntry.created_at >= cutoff,
    ).all()
    matched = []
    for e in entries:
        try:
            ctx = json.loads(e.context_json or '{}')
        except (json.JSONDecodeError, TypeError):
            continue
        if str(ctx.get('college_fund_id')) == str(fund_id):
            matched.append(e)
    if not matched:
        return {'confidence_pct': None, 'trend': None, 'avg_variance_pct': None,
                'samples': 0, 'reasoning': 'No contribution history yet for this fund.'}
    variances = [e.variance_pct for e in matched if e.variance_pct is not None]
    if not variances:
        return {'confidence_pct': None, 'trend': None, 'avg_variance_pct': None,
                'samples': len(matched), 'reasoning': 'No variance data yet.'}
    avg_variance = sum(variances) / len(variances)
    confidence = max(0, min(100, round(100 + min(0, avg_variance) * 2)))
    trend = 'ahead' if avg_variance > 5 else 'behind' if avg_variance < -5 else 'on_pace'
    return {
        'confidence_pct': confidence, 'trend': trend,
        'avg_variance_pct': round(avg_variance, 1), 'samples': len(matched),
        'reasoning': f'{len(matched)} contribution(s) tracked, {trend.replace("_", " ")}',
    }


def get_payment_variance_for_account(session, debt_account_id: int, months: int = 12) -> dict:
    """Payment compliance metrics for a debt account from real historian
    events (payment_confirmed / payment_amount_variance), over a trailing
    window. Distinct from server.py :: get_payment_compliance (Phase E),
    which reads current ledger state per recurring pattern — this reads the
    historian's point-in-time record of what happened at confirm time,
    which survives even if the underlying ledger entry is later edited."""
    cutoff = datetime.now() - timedelta(days=30 * months)
    entries = session.query(HistorianEntry).filter(
        HistorianEntry.debt_account_id == debt_account_id,
        HistorianEntry.event_category.in_(['payment_confirmed', 'payment_amount_variance']),
        HistorianEntry.created_at >= cutoff,
    ).all()
    if not entries:
        return {'on_time': 0, 'under_plan': 0, 'over_plan': 0, 'avg_variance_pct': None, 'total_payments': 0}
    on_time = sum(1 for e in entries if e.variance_pct is not None and abs(e.variance_pct) <= 5)
    under   = sum(1 for e in entries if e.variance_pct is not None and e.variance_pct < -5)
    over    = sum(1 for e in entries if e.variance_pct is not None and e.variance_pct > 5)
    variances = [e.variance_pct for e in entries if e.variance_pct is not None]
    return {
        'on_time': on_time, 'under_plan': under, 'over_plan': over,
        'avg_variance_pct': round(sum(variances) / len(variances), 1) if variances else None,
        'total_payments': len(entries),
    }


def get_payment_compliance_confidence(session, debt_account_id: int) -> dict:
    """0-100 confidence score for a debt account's payoff timeline, from
    payment reliability — on-time rate, penalized for late fees. Returns
    confidence=None (not a fabricated number) when there's no history yet."""
    variance = get_payment_variance_for_account(session, debt_account_id)
    if variance['total_payments'] == 0:
        return {'confidence_pct': None, 'reasoning': 'No confirmed payments yet.'}
    late_fee_count = session.query(HistorianEntry).filter_by(
        debt_account_id=debt_account_id, event_category='late_fee_trigger'
    ).count()
    on_time_pct = (variance['on_time'] / variance['total_payments']) * 100
    confidence = max(0, min(100, round(on_time_pct - (late_fee_count * 5))))
    reasoning = f"{variance['on_time']}/{variance['total_payments']} payments on-time (±5%)"
    if late_fee_count:
        reasoning += f"; {late_fee_count} late fee event(s)"
    return {'confidence_pct': confidence, 'reasoning': reasoning}


def get_late_payment_pattern(session, debt_account_id: int) -> dict:
    """Late-payment frequency from payment_timing_slippage events. This
    event type isn't written anywhere yet (nothing in this codebase computes
    a due-date-vs-confirmed-date offset) — this returns an honest empty
    result until that write path exists, rather than a fake zero."""
    entries = session.query(HistorianEntry).filter_by(
        debt_account_id=debt_account_id, event_category='payment_timing_slippage'
    ).all()
    if not entries:
        return {'late_fee_count': 0, 'avg_days_late': None, 'months_affected': 0}
    days_late = [e.actual_value for e in entries if e.actual_value is not None]
    return {
        'late_fee_count': len(entries),
        'avg_days_late': round(sum(days_late) / len(days_late), 1) if days_late else None,
        'months_affected': len(entries),
    }


# ── 1.1-scaffold reads — see module docstring above ─────────────────────────

def get_category_patterns(session, merchant_name: str) -> dict:
    """How the user has categorized this merchant historically. The
    categorization_suggestion_confirm/reject events now exist (see the
    confirm route), but this deliberately reads the ledger/transaction
    history instead: the ledger holds the full categorization record,
    where the confirm/reject log only captures the sparse cases where a
    suggestion was shown. Phase H2 Feature 1 can blend the two; today the
    ledger is the richer, real answer."""
    rows = session.query(DebtLedgerEntry.category, func.count(DebtLedgerEntry.id)).filter(
        DebtLedgerEntry.merchant.ilike(f'%{merchant_name}%'), DebtLedgerEntry.category != ''
    ).group_by(DebtLedgerEntry.category).order_by(desc(func.count(DebtLedgerEntry.id))).all()
    if not rows:
        return {'most_common_category': None, 'frequency': 0, 'edge_cases': []}
    total = sum(r[1] for r in rows)
    return {
        'most_common_category': rows[0][0],
        'frequency': round(rows[0][1] / total * 100, 1),
        'edge_cases': [r[0] for r in rows[1:]],
    }


def get_budget_variance_by_category(session, category_id: int, months: int = 12) -> dict:
    """Budget vs. actual variance for a category. Scaffold for Phase H2
    Feature 2 — budget_variance_observed isn't written anywhere yet."""
    cutoff = datetime.now() - timedelta(days=30 * months)
    entries = session.query(HistorianEntry).filter(
        HistorianEntry.category_id == category_id,
        HistorianEntry.event_category == 'budget_variance_observed',
        HistorianEntry.created_at >= cutoff,
    ).all()
    if not entries:
        return {'avg_variance': None, 'variance_pct': None, 'months_over': 0, 'months_under': 0}
    over  = sum(1 for e in entries if e.variance_pct is not None and e.variance_pct > 0)
    under = sum(1 for e in entries if e.variance_pct is not None and e.variance_pct < 0)
    pcts  = [e.variance_pct for e in entries if e.variance_pct is not None]
    return {
        'avg_variance': round(sum(e.variance_amount for e in entries if e.variance_amount is not None) / len(entries), 2),
        'variance_pct': round(sum(pcts) / len(pcts), 1) if pcts else None,
        'months_over': over, 'months_under': under,
    }


def get_trip_variance_by_region(session, region: str) -> dict:
    """
    Regional trip spending variance from trip_history (Phase H1 addition,
    not historian_entries — trips are per-trip rows, not point events).

    save_trip_budget's estimate rows and save_trip_learned_actual's actual
    rows are deliberately not the same row (see save_trip_learned_actual's
    docstring — a "learned actual" is applied to inform a NEW trip being
    planned, not closing the loop on one specific past estimate), so a
    region's actual-only rows never carry an estimated_total. Averaging
    across "all rows with an actual" while treating a missing estimate as
    0 (the original bug here) drags avg_estimated toward zero as more
    actual-only rows accumulate, until variance_pct silently locks at
    None forever regardless of how much real data exists. Averaging
    estimates and actuals over their own independent row sets — which is
    what the field names already imply — fixes that without losing either
    side's signal.
    """
    est_rows = session.query(TripHistory.estimated_total).filter(
        TripHistory.region == region, TripHistory.estimated_total.isnot(None)
    ).all()
    act_rows = session.query(TripHistory.actual_total).filter(
        TripHistory.region == region, TripHistory.actual_total.isnot(None)
    ).all()
    if not est_rows or not act_rows:
        return {'avg_estimated': None, 'avg_actual': None, 'variance_pct': None, 'trip_count': len(act_rows)}
    avg_est = sum(r[0] for r in est_rows) / len(est_rows)
    avg_act = sum(r[0] for r in act_rows) / len(act_rows)
    return {
        'avg_estimated': round(avg_est, 2),
        'avg_actual': round(avg_act, 2),
        'variance_pct': round((avg_act - avg_est) / avg_est * 100, 1) if avg_est else None,
        'trip_count': len(act_rows),
    }


def get_llm_miss_log(time_range_days: int = 30) -> dict:
    """Gate-flag counts and recent misses, read from the existing
    voice_miss_log.jsonl (ai_voice_miss route) — not historian_entries.
    That file is already the real miss-log (Phase 1E); no separate
    'llm_gate_flag' event type is written in parallel."""
    log_path = DATA_DIR / 'voice_miss_log.jsonl'
    if not log_path.exists():
        return {'gate_flag_count_by_type': {}, 'most_recent_flags': []}
    cutoff = datetime.now() - timedelta(days=time_range_days)
    counts, recent = {}, []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                try:
                    ts = datetime.fromisoformat(entry.get('ts', '').rstrip('Z'))
                except ValueError:
                    continue
                if ts < cutoff:
                    continue
                for rule in entry.get('rules', []):
                    counts[rule] = counts.get(rule, 0) + 1
                recent.append(entry)
    except Exception:
        pass
    recent.sort(key=lambda e: e.get('ts', ''), reverse=True)
    return {'gate_flag_count_by_type': counts, 'most_recent_flags': recent[:20]}


# ── Achievements ──────────────────────────────────────────────────────────────

achievements_bp = Blueprint('achievements', __name__)


@achievements_bp.route('', methods=['GET'])
def list_achievements():
    """Return all earned achievements, optionally filtered by section."""
    with db_session() as session:
        q = session.query(Achievement)
        if request.args.get('section'):
            q = q.filter(Achievement.section == request.args['section'])
        achs = q.order_by(Achievement.earned_at).all()
        return ok([{
            'id':             a.id,
            'achievement_id': a.achievement_id,
            'section':        a.section,
            'earned_at':      a.earned_at.isoformat(),
            'notified':       a.notified,
        } for a in achs])


@achievements_bp.route('', methods=['POST'])
@require_json
def award_achievement():
    """Award an achievement. Idempotent — safe to call multiple times."""
    body = request.json
    ach_id = body.get('achievement_id')
    if not ach_id:
        return err('achievement_id required')

    with db_session() as session:
        existing = session.query(Achievement).filter_by(
            achievement_id=ach_id
        ).first()
        if existing:
            return ok({'already_earned': True, 'earned_at': existing.earned_at.isoformat()})

        ach = Achievement(
            achievement_id=ach_id,
            section=body.get('section', 'general'),
            extra_data=json.dumps(body.get('metadata', {})),
            notified=False,
        )
        session.add(ach)
        session.flush()
        session.commit()
        return ok({
            'earned': True,
            'earned_at': ach.earned_at.isoformat(),
        }, 201)


# ── Settings ──────────────────────────────────────────────────────────────────

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('', methods=['GET'])
def get_settings():
    """
    Return all app settings as a flat key-value dict.
    """
    with db_session() as session:
        settings = {s.key: s.value for s in session.query(AppSetting).all()}

    # Default ai_enabled to 'true' if not yet set
    if 'ai_enabled' not in settings:
        settings['ai_enabled'] = 'true'

    return ok(settings)


@settings_bp.route('', methods=['PATCH'])
@require_json
def update_settings():
    """Update one or more app settings."""
    body = request.json
    # Item 105: only the sample household's own load marks the records as the sample (which lets them be cleared)
    body.pop('sample_household', None)
    # Item 107 D8: what the person said about a pair of accounts is appended by its own route, never written over
    body.pop('two_accounts_said_json', None)
    # Cloud AI is gone (CLOUD_AI_REMOVAL.md): there is no provider to choose and
    # no key to store, so neither setting is ever written.
    body.pop('api_key', None)
    body.pop('ai_provider', None)
    # There is no AI address or model to choose: the engine is in this process and ships one tested model
    # (ENGINE_REPLACEMENT.md). Neither setting is ever written.
    body.pop('local_endpoint', None)
    body.pop('local_model', None)
    # Household facts (home_state, pay_frequency, ...) are never written here directly: they go through the one write
    # path, which keeps their history and their current value together (ONBOARDING_REVISIT.md s4). An empty value
    # withdraws the answer; an unknown value is refused, and then nothing in this request is saved.
    from core import household
    facts = {k: body.pop(k) for k in list(body) if k in household.FACTS}

    with db_session() as session:
        try:
            for key, value in facts.items():
                household.set_household_fact(session, key, value, 'settings')
        except household.FactError as e:
            session.rollback()
            return err(str(e), 400)
        for key, value in body.items():
            setting = _get_setting(session, key)
            if setting:
                setting.value = str(value)
            else:
                session.add(AppSetting(key=key, value=str(value)))
        session.commit()
    # Switching AI off releases the model; switching it on loads it (R-a). Only the launcher allows a real load.
    if 'ai_enabled' in body:
        from core import engine
        if str(body['ai_enabled']).lower() == 'false':
            engine.stop()
        else:
            engine.start()
    return ok({'updated': list(body.keys()) + list(facts)})


# ── Household facts (ONBOARDING_REVISIT.md, item 30) ─────────────────────────────────────────────────────────────
# Onboarding, Settings' "Your home" card and the inline prompts all set the SAME canonical facts, through
# core.household.set_household_fact(). These routes are how the page reads and sets them.

@settings_bp.route('/household', methods=['GET'])
def household_facts():
    """Every household fact this line asks: the question, the answers that exist, the current value (null =
    unanswered), and - with ?history=1 - each fact's dated history."""
    from core import household
    with db_session() as session:
        facts = household.snapshot(session)
        if request.args.get('history'):
            for k in facts:
                facts[k]['history'] = household.history(session, k)
        return ok(facts)


@settings_bp.route('/household', methods=['POST'])
@require_json
def household_set_fact():
    """Set one fact: {key, value, source}. value null or '' withdraws it. source: onboarding | settings |
    inline_prompt (carried_over is the migration's alone)."""
    from core import household
    body = request.json or {}
    source = body.get('source') or 'settings'
    if source not in ('onboarding', 'settings', 'inline_prompt'):
        return err('not a source the page can use', 400)
    with db_session() as session:
        try:
            changed = household.set_household_fact(session, body.get('key'), body.get('value'), source)
        except household.FactError as e:
            session.rollback()
            return err(str(e), 400)
        session.commit()
        return ok({'key': body.get('key'), 'value': household.current(session, body.get('key')), 'changed': changed})


# ── Item 57 stage 1 (BANK_AGENT.md A3/A4, Rob 2026-10-09): saved bank logins, in the operating system's vault ──
# Nothing here returns, logs or stores a password: the vault holds it (core/bank_vault.py), and only the fetch reads
# it. Saving needs the user's acknowledgement of A3's wording, sent with the save.

def _bank_agent_accounts(session):
    """The accounts and standalone cards with a bank link (BANK_BROWSER.md F3): the ones a fetch could open."""
    from core import bank_vault
    rows = []
    for a in session.query(Account).filter(Account.is_active == True).all():   # noqa: E712
        if a.portal_url:
            rows.append({'key': f'account:{a.id}', 'name': a.name})
    for d in session.query(DebtAccount).filter(DebtAccount.is_active == True).all():   # noqa: E712
        if d.portal_url and not d.linked_account_id:
            rows.append({'key': f'card:{d.id}', 'name': d.name})
    for r in rows:
        r['kind'] = 'bank'
    # item 68 B1/B4: bills with their own website, after the banks (Get my accounts visits them last)
    for b in session.query(BudgetItem).filter(BudgetItem.is_active == True, BudgetItem.type == 'expense') \
            .order_by(BudgetItem.sort_order, BudgetItem.id).all():   # noqa: E712
        if _bank_agent_url(session, f'bill:{b.id}'):
            rows.append({'key': f'bill:{b.id}', 'name': b.name, 'kind': 'bill'})
    for r in rows:
        r['has_login'] = bank_vault.has_login(r['key'])
        r['has_steps'] = bool(((_bank_recipe(session, r['key']) or {}).get('steps')))
        r['remembered'] = (_get_setting(session, f"bank_device:{r['key']}") or AppSetting(value='')).value == 'yes'
    return rows


@settings_bp.route('/bank-logins', methods=['GET'])
def bank_logins():
    from core import bank_vault
    with db_session() as session:
        rows = _automation_accounts(session) if request.args.get('all') else _bank_agent_accounts(session)
        return ok({'available': bank_vault.available(), 'vault': bank_vault.vault_name(),
                   'accounts': rows, 'remind_days': _fetch_remind_days(session)})


def _automation_accounts(session):
    """Item 69 P3: every active account and standalone card, by name - with or without a link - and where each
    stands. No balance, no amount: the Automation page is about getting the data in. The link itself never leaves
    the server (s126); only whether there is one."""
    from core import bank_vault
    rows = [{'key': f'account:{a.id}', 'id': a.id, 'kind': 'account', 'name': a.name}
            for a in session.query(Account).filter(Account.is_active == True).order_by(Account.sort_order, Account.name).all()]   # noqa: E712
    rows += [{'key': f'card:{d.id}', 'id': d.id, 'kind': 'card', 'name': d.name}
             for d in session.query(DebtAccount).filter(DebtAccount.is_active == True).order_by(DebtAccount.sort_order, DebtAccount.name).all()   # noqa: E712
             if not d.linked_account_id]
    for r in rows:
        r['has_site'] = bool(_bank_agent_url(session, r['key']))
        r['has_login'] = r['has_site'] and bank_vault.has_login(r['key'])
        r['has_steps'] = bool(((_bank_recipe(session, r['key']) or {}).get('steps')))
        r['remembered'] = (_get_setting(session, f"bank_device:{r['key']}") or AppSetting(value='')).value == 'yes'
    return rows


@settings_bp.route('/bank-logins', methods=['POST'])
@require_json
def bank_login_save():
    """{key, username, password, acknowledged: true}. The login goes to the vault and nowhere else."""
    from core import bank_vault
    body = request.json or {}
    key = str(body.get('key') or '')
    if body.get('acknowledged') is not True:
        return err('Read and accept how fetching works before saving a login.', 400)
    if not (body.get('username') and body.get('password')):
        return err('A username and a password are both needed.', 400)
    with db_session() as session:
        if key not in {r['key'] for r in _bank_agent_accounts(session)}:
            return err('Not an account with a bank link.', 400)
    if not bank_vault.available():
        return err('This computer has no password vault Groundwork can use, so it cannot keep a bank login.', 400)
    bank_vault.save_login(key, body['username'], body['password'])
    return ok({'key': key, 'has_login': True})


@settings_bp.route('/bank-logins/forget', methods=['POST'])
@require_json
def bank_login_forget():
    from core import bank_vault
    key = str((request.json or {}).get('key') or '')
    try:
        removed = bank_vault.forget(key)
    except ValueError:
        return err('Not a saved login.', 400)
    return ok({'key': key, 'forgotten': removed})


# ── Item 57 stage 2 (BANK_AGENT.md A5): "show me once" ──
# The user does their usual download once in the agent's window; it records the steps - which control, which choice -
# never a typed value. The steps come back in words; saved per account only when the user says so.

def _bank_agent_url(session, key):
    """The link the agent's window opens for an account or standalone card (BANK_BROWSER.md F3), or None."""
    kind, _, ident = str(key).partition(':')
    if not ident.isdigit():
        return None
    if kind == 'account':
        a = session.get(Account, int(ident))
        return a.portal_url if a else None
    if kind == 'card':
        d = session.get(DebtAccount, int(ident))
        return d.portal_url if d and not d.linked_account_id else None
    if kind == 'pay':                          # item 68 B8 (b): the bank of the account the bill is paid from
        acct = _pay_account(session, ident)
        return _bank_agent_url(session, f'account:{acct.id}') if acct else None
    if kind == 'bill':                         # item 68 B1: a bill's own website, on its budget line
        b = session.get(BudgetItem, int(ident))
        row = _get_setting(session, f'bill_site:{ident}') if b and b.is_active else None
        return (row.value or None) if row else None
    return None


def _pay_account(session, bill_id):
    """Item 68 B8 (b): the account the person said pays this bill (bill_from:<id>), or None."""
    row = _get_setting(session, f'bill_from:{bill_id}')
    if not row or not (row.value or '').isdigit():
        return None
    a = session.get(Account, int(row.value))
    return a if a and a.is_active else None


def _device_key(session, key):
    """The key whose remembered device (A7) a window uses: a pay route uses its bank account's."""
    if str(key).startswith('pay:'):
        acct = _pay_account(session, str(key).split(':', 1)[1])
        return f'account:{acct.id}' if acct else key
    return key


def _bank_recipe(session, key):
    row = _get_setting(session, f'bank_recipe:{key}')
    try:
        r = json.loads(row.value) if row and row.value else None
    except (TypeError, ValueError):
        return None
    if r and r.get('steps'):            # cleaned again on every read: an older recipe's numbers are masked here too
        import bank_agent_window
        r['steps'] = [s for s in (bank_agent_window.clean_step(x) for x in r['steps']) if s]
    return r


@settings_bp.route('/bank-agent/record', methods=['POST'])
@require_json
def bank_agent_record():
    import bank_agent_window
    key = str((request.json or {}).get('key') or '')
    # item 70 R3: re-record from step N (1-based): the steps before it are kept
    try:
        from_step = int((request.json or {}).get('from_step')) - 1 if (request.json or {}).get('from_step') else None
    except (TypeError, ValueError):
        from_step = None
    with db_session() as session:
        url = _bank_agent_url(session, key)
        dkey = _device_key(session, key)
        device_on = (_get_setting(session, f'bank_device:{dkey}') or AppSetting(value='')).value == 'yes'
    if not url:
        return err('That account has no bank link.', 400)
    key_for_device = dkey
    # A7: with "Remember this computer" ticked, the recording window keeps the bank's cookies in the same folder the
    # fetch uses, so trusting this device while recording carries into the fetch
    device = str(_bank_device_dir(key_for_device, create=True)) if device_on else ''
    return ok({'key': key, 'result': bank_agent_window.start_recording(key, url, device_dir=device,
                                                                      from_step=from_step if from_step and from_step > 0 else None)})


@settings_bp.route('/bank-agent/record', methods=['GET'])
def bank_agent_record_steps():
    import bank_agent_window
    key = request.args.get('key', '')
    s = bank_agent_window.steps(key)
    return ok({'key': key, 'steps': s, 'words': [bank_agent_window.step_words(x) for x in s]})


@settings_bp.route('/bank-agent/record/finish', methods=['POST'])
@require_json
def bank_agent_record_finish():
    import bank_agent_window
    key = str((request.json or {}).get('key') or '')
    s, frm = bank_agent_window.finish_recording(key, with_from=True)
    kept = []
    if frm:
        with db_session() as session:
            kept = (((_bank_recipe(session, key) or {}).get('steps')) or [])[:frm]
    # item 70 R3: the whole list, kept and new, goes to the review before anything is saved (A5)
    whole = kept + s if s else []
    return ok({'key': key, 'steps': whole, 'kept': len(kept) if s else 0,
               'words': [bank_agent_window.step_words(x) for x in whole]})


@settings_bp.route('/bank-agent/recipe', methods=['POST'])
@require_json
def bank_agent_recipe_save():
    """Save the steps the user confirmed. Each is cleaned again: only named fields, no typed values, digits masked."""
    import bank_agent_window
    body = request.json or {}
    key = str(body.get('key') or '')
    clean = [s for s in (bank_agent_window.clean_step(x) for x in (body.get('steps') or [])) if s]
    if not clean:
        return err('No steps to save.', 400)
    with db_session() as session:
        if not _bank_agent_url(session, key):
            return err('That account has no bank link.', 400)
        _set_setting(session, f'bank_recipe:{key}', json.dumps({'steps': clean, 'saved': datetime.now().isoformat()}))
        session.commit()
    return ok({'key': key, 'steps': clean, 'words': [bank_agent_window.step_words(x) for x in clean]})


@settings_bp.route('/bank-agent/recipe', methods=['GET'])
def bank_agent_recipe_get():
    import bank_agent_window
    key = request.args.get('key', '')
    with db_session() as session:
        r = _bank_recipe(session, key)
    steps_ = (r or {}).get('steps') or []
    return ok({'key': key, 'steps': steps_, 'words': [bank_agent_window.step_words(x) for x in steps_]})


@settings_bp.route('/bank-agent/recipe/delete', methods=['POST'])
@require_json
def bank_agent_recipe_delete():
    key = str((request.json or {}).get('key') or '')
    with db_session() as session:
        row = _get_setting(session, f'bank_recipe:{key}')
        if row:
            session.delete(row)
            session.commit()
    return ok({'key': key, 'deleted': True})


# ── Item 57 stage 3 (BANK_AGENT.md A2/A6/A7): the fetch - started by the user's click, never on a schedule ──

def _bank_device_dir(key, create=False):
    """A7: the per-account folder where the bank's own cookies are kept, only when the user opted in."""
    safe = str(key).replace(':', '_')
    d = DATA_DIR / 'bank_devices' / safe
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


@settings_bp.route('/bank-agent/fetch', methods=['POST'])
@require_json
def bank_agent_fetch():
    key = str((request.json or {}).get('key') or '')
    result, problem = _start_bank_fetch(key)
    if problem:
        return err(problem, 400)
    return ok({'key': key, 'result': result})


def _start_bank_fetch(key, batch=None, on_end=None):
    """Start one account's fetch: (result, None), or (None, a reason in words) when it can't start. The single
    button and item 67's batch both come here; each run records its own statement_fetched (A11), with the batch id
    when it was one of a batch (G8)."""
    import bank_agent_window
    from core import bank_vault
    with db_session() as session:
        url = _bank_agent_url(session, key)
        recipe = _bank_recipe(session, key)
        device_on = (_get_setting(session, f'bank_device:{key}') or AppSetting(value='')).value == 'yes'
    if not url:
        return None, 'That account has no bank link.'
    if not bank_vault.has_login(key):
        return None, 'Save a login for this account first.'
    steps_ = (recipe or {}).get('steps') or []
    if not steps_:
        return None, 'Show Groundwork the steps once first.'
    device = str(_bank_device_dir(key, create=True)) if device_on else ''
    started = datetime.now().isoformat(timespec='seconds')
    words = [bank_agent_window.step_words(s) for s in steps_]

    def _finished(k, events):
        _record_fetch(k, url, words, started, events, batch=batch)
        if str(k).startswith('bill:'):
            try:
                _bill_pending(k, url, events)
            except Exception:
                logging.getLogger('groundwork').warning('a bill reading could not be kept to be checked')
        if on_end:
            on_end(k, events)
    return bank_agent_window.start_fetch(key, url, steps_, device, on_finish=_finished), None


def _bill_pending(key, url, events):
    """Item 68 B3: what a bill's run read, waiting for the person's yes - nothing is used before it."""
    import bank_agent_window
    from urllib.parse import urlsplit
    got = {e.get('what'): e.get('val') for e in events if e.get('s') == 'read'}
    if not got:
        return
    due = bank_agent_window.parse_due(got.get('due'))
    pending = {'amount': bank_agent_window.parse_amount(got.get('amount')), 'amount_text': got.get('amount'),
               'due': due.isoformat() if due else None, 'due_text': got.get('due'),
               'read_at': datetime.now().isoformat(timespec='seconds'), 'host': (urlsplit(url).hostname or '').lower()}
    with db_session() as session:
        _set_setting(session, f"bill_pending:{key.split(':', 1)[1]}", json.dumps(pending))
        session.commit()


def _record_fetch(key, url, words, started, events, folder=None, batch=None):
    """Item 57 A11: one 'statement_fetched' Historian event per fetch - provenance, the user's own action and its
    times. A fixed set of keys; the file's name and SHA-256 (correspondence with the later import's own record),
    never its content. Read by the Settings history route alone - no prompt, no engine."""
    import hashlib
    from urllib.parse import urlsplit
    first = lambda s: next((e for e in events if e.get('s') == s), None)          # noqa: E731
    end = next((e for e in reversed(events) if e.get('s') in ('stopped', 'downloaded', 'no_download', 'done')), {}) or {}
    code = first('waiting_code')
    after_code = next((e for e in events if code and e.get('s') == 'step' and e.get('i') == code.get('i')), None)
    file_name, sha = None, None
    if end.get('s') == 'downloaded' and end.get('file'):
        import bank_window
        p = Path(folder or bank_window.downloads_dir()) / Path(end['file']).name
        file_name = p.name
        try:
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            sha = None              # the file has gone - recorded as unknown, never guessed
    try:
        with db_session() as session:
            log_historian_event(session, 'statement_fetched', context={
                'account_key':    key,
                'host':           (urlsplit(url).hostname or '').lower(),
                'steps':          list(words),
                'started':        started,
                'code_asked':     code.get('at') if code else None,
                'code_entered':   after_code.get('at') if after_code else None,
                'finished':       end.get('at'),
                'outcome':        end.get('s'),
                'why':            end.get('why'),
                'stopped_at':     end.get('i'),
                'file_name':      file_name,
                'content_sha256': sha,
                'batch':          batch,           # item 67 G8: the runs from one "Get my accounts" press share it
            })
            session.commit()
    except Exception:
        logging.getLogger('groundwork').warning('statement_fetched could not be recorded')


@settings_bp.route('/bank-agent/history', methods=['GET'])
def bank_agent_history():
    """A11: an account's last fetches, each joined to its import by the file's hash (or 'not imported yet')."""
    key = request.args.get('key', '')
    out = []
    with db_session() as session:
        rows = session.query(HistorianEntry).filter(HistorianEntry.event_category == 'statement_fetched') \
            .order_by(HistorianEntry.id.desc()).limit(200).all()
        for e in rows:
            ctx = json.loads(e.context_json or '{}')
            if ctx.get('account_key') != key:
                continue
            imp = None
            if ctx.get('content_sha256'):
                hit = session.query(HistorianEntry).filter(
                    HistorianEntry.event_category == 'import_committed',
                    HistorianEntry.context_json.contains(f'"content_sha256": "{ctx["content_sha256"]}"')).first()
                if hit:
                    ic = json.loads(hit.context_json or '{}')
                    imp = {'at': hit.created_at.isoformat(timespec='seconds'), 'records': ic.get('created')}
            out.append({**{k: ctx.get(k) for k in ('started', 'finished', 'outcome', 'why', 'file_name', 'code_asked', 'code_entered')},
                        'imported': imp})
            if len(out) >= 10:
                break
    return ok({'key': key, 'fetches': out})


@settings_bp.route('/bank-agent/fetch', methods=['GET'])
def bank_agent_fetch_status():
    import bank_agent_window
    key = request.args.get('key', '')
    with db_session() as session:
        steps_ = ((_bank_recipe(session, key) or {}).get('steps')) or []
    evs = bank_agent_window.fetch_events(key)
    return ok({'key': key, 'events': evs, 'words': [w for w in (bank_agent_window.fetch_words(e, steps_) for e in evs) if w]})


# ── Item 67 - Get all my accounts (GET_ALL_ACCOUNTS.md G1-G8) ────────────────
@settings_bp.route('/bank-agent/fetch-all', methods=['POST'])
@require_json
def bank_agent_fetch_all():
    """G1: the user's press. Every account with saved steps, one at a time, in the order they are listed - or, from
    an account's own Bank button on the Ledger, just that one ({keys: [key]})."""
    import bank_agent_window
    only = (request.json or {}).get('keys')
    with db_session() as session:
        items = [{'key': a['key'], 'name': a['name']} for a in _bank_agent_accounts(session) if a['has_steps']
                 and (not only or a['key'] in only)]
    if not items:
        return err('No account has saved steps yet.', 400)

    def _launch(key, batch_id, on_end):
        result, problem = _start_bank_fetch(key, batch=batch_id, on_end=on_end)
        if problem:
            return 'no_login' if 'login' in problem else 'no_steps' if 'steps' in problem else 'refused_url'
        return result
    return ok({'result': bank_agent_window.start_batch(items, _launch)})


@settings_bp.route('/bank-agent/fetch-all', methods=['GET'])
def bank_agent_fetch_all_status():
    import bank_agent_window
    return ok(bank_agent_window.batch_state())


@settings_bp.route('/bank-agent/fetch-all/stop', methods=['POST'])
@require_json
def bank_agent_fetch_all_stop():
    import bank_agent_window
    return ok({'stopped': bank_agent_window.stop_batch()})


def _fetch_remind_days(session):
    """G3: days after which the dashboard's "Last fetched" line appears; 0 turns it off. 7 unless the user set it."""
    row = _get_setting(session, 'bank_fetch_remind_days')
    try:
        return max(0, min(365, int(row.value))) if row and row.value not in (None, '') else 7
    except (TypeError, ValueError):
        return 7


def _last_fetches(session):
    """account key -> when its last fetch DOWNLOADED a file (statement_fetched; the record only, G3)."""
    out = {}
    for e in session.query(HistorianEntry).filter(HistorianEntry.event_category == 'statement_fetched') \
            .order_by(HistorianEntry.id.desc()).limit(2000).all():
        ctx = json.loads(e.context_json or '{}')
        k = ctx.get('account_key')
        if k and k not in out and ctx.get('outcome') == 'downloaded':
            out[k] = ctx.get('finished') or e.created_at.isoformat(timespec='seconds')
    return out


@settings_bp.route('/bank-agent/last-fetched', methods=['GET'])
def bank_agent_last_fetched():
    """G2/G3: the accounts a press would visit, each with its last download from the record. Read when a page asks;
    nothing here starts anything or runs on a timer."""
    with db_session() as session:
        accts = [a for a in _bank_agent_accounts(session) if a['has_steps']]
        last = _last_fetches(session)
        days_setting = _fetch_remind_days(session)
    today = datetime.now().date()
    rows = []
    for a in accts:
        when = last.get(a['key'])
        try:
            days = (today - datetime.fromisoformat(when).date()).days if when else None
        except ValueError:
            days = None
        rows.append({'key': a['key'], 'name': a['name'], 'last': when, 'days': days})
    show = bool(rows) and days_setting > 0 and any(r['days'] is None or r['days'] >= days_setting for r in rows)
    return ok({'accounts': rows, 'remind_days': days_setting, 'show': show})


@settings_bp.route('/bank-agent/remind-days', methods=['POST'])
@require_json
def bank_agent_remind_days():
    """G3: the user's number of days (0 = off)."""
    try:
        days = max(0, min(365, int((request.json or {}).get('days'))))
    except (TypeError, ValueError):
        return err('A number of days, please.', 400)
    with db_session() as session:
        _set_setting(session, 'bank_fetch_remind_days', str(days))
        session.commit()
    return ok({'remind_days': days})


def _fetched_for(session, sha):
    """G6 (a): a queued file's own fetch, matched by its content hash - the account it was fetched for, and its place
    among the files one press brought in. None when no fetch brought it (a file the user downloaded themselves)."""
    if not sha:
        return None
    hit = session.query(HistorianEntry).filter(
        HistorianEntry.event_category == 'statement_fetched',
        HistorianEntry.context_json.contains(f'"content_sha256": "{sha}"')).order_by(HistorianEntry.id.desc()).first()
    if not hit:
        return None
    ctx = json.loads(hit.context_json or '{}')
    key = ctx.get('account_key') or ''
    kind, _, ident = key.partition(':')
    row = None
    if ident.isdigit():
        row = session.get(Account if kind == 'account' else DebtAccount, int(ident)) if kind in ('account', 'card') else None
    out = {'key': key, 'name': row.name if row else None, 'batch': ctx.get('batch'), 'pos': None, 'of': None}
    if ctx.get('batch'):
        ids = [e.id for e in session.query(HistorianEntry).filter(
            HistorianEntry.event_category == 'statement_fetched',
            HistorianEntry.context_json.contains(f'"batch": "{ctx["batch"]}"')).order_by(HistorianEntry.id).all()
            if json.loads(e.context_json or '{}').get('outcome') == 'downloaded']
        if hit.id in ids:
            out['pos'], out['of'] = ids.index(hit.id) + 1, len(ids)
    return out


# ── Item 68 - bills read from their own website (BILLS_AND_PAYING.md B1-B5) ───
def _bill_reading_json(r):
    return {'id': r.id, 'amount': r.amount, 'due': r.due_date.isoformat() if r.due_date else None,
            'read_at': r.read_at.isoformat(timespec='seconds') if r.read_at else None, 'host': r.source_host,
            'use_for_month': bool(r.use_for_month)}


@settings_bp.route('/bank-agent/bills', methods=['GET'])
def bank_agent_bills():
    """B1/B3: every expense line, its website if set, whether its login is saved, what was last read (waiting for a
    yes) and last confirmed."""
    from core import bank_vault
    out = []
    with db_session() as session:
        for b in session.query(BudgetItem).filter(BudgetItem.is_active == True, BudgetItem.type == 'expense') \
                .order_by(BudgetItem.sort_order, BudgetItem.id).all():   # noqa: E712
            site = _get_setting(session, f'bill_site:{b.id}')
            pend = _get_setting(session, f'bill_pending:{b.id}')
            last = session.query(BillReading).filter_by(budget_item_id=b.id).order_by(BillReading.id.desc()).first()
            try:
                pending = json.loads(pend.value) if pend and pend.value else None
            except (TypeError, ValueError):
                pending = None
            out.append({'id': b.id, 'key': f'bill:{b.id}', 'name': b.name, 'category': b.category, 'planned': b.amount,
                        'site': (site.value if site else '') or '', 'pending': pending,
                        'has_login': bool(site and site.value) and bank_vault.has_login(f'bill:{b.id}'),
                        # item 69 P5: the rest of a bill's setup, for its row on the Automation page
                        'has_steps': bool(((_bank_recipe(session, f'bill:{b.id}') or {}).get('steps'))),
                        'pay_steps': bool(((_bank_recipe(session, f'pay:{b.id}') or {}).get('steps'))),
                        'paid_from': (lambda a: a.id if a else None)(_pay_account(session, b.id)),
                        'remembered': (_get_setting(session, f'bank_device:bill:{b.id}') or AppSetting(value='')).value == 'yes',
                        'confirmed': _bill_reading_json(last) if last else None})
    return ok({'bills': out})


@settings_bp.route('/bank-agent/bill-site', methods=['POST'])
@require_json
def bank_agent_bill_site():
    """B1: {id, url}. The same https check as a bank's link; '' removes it (and the saved steps with it)."""
    import bank_window
    body = request.json or {}
    try:
        bid = int(body.get('id'))
    except (TypeError, ValueError):
        return err('Which bill?', 400)
    url = str(body.get('url') or '').strip()
    if url and bank_window.portal_url_problem(url):
        return err(bank_window.portal_url_problem(url), 400)
    with db_session() as session:
        b = session.get(BudgetItem, bid)
        if not b or not b.is_active or b.type != 'expense':
            return err('That budget line was not found.', 404)
        if url:
            _set_setting(session, f'bill_site:{bid}', url)
        else:
            for k in (f'bill_site:{bid}', f'bank_recipe:bill:{bid}', f'bill_pending:{bid}'):
                row = _get_setting(session, k)
                if row:
                    session.delete(row)
        session.commit()
    return ok({'id': bid, 'site': url})


@settings_bp.route('/bank-agent/bill-read/confirm', methods=['POST'])
@require_json
def bank_agent_bill_confirm():
    """B3: {id, yes}. Yes keeps what was read as a BillReading; no discards it. Either way the waiting reading goes."""
    body = request.json or {}
    try:
        bid = int(body.get('id'))
    except (TypeError, ValueError):
        return err('Which bill?', 400)
    with db_session() as session:
        row = _get_setting(session, f'bill_pending:{bid}')
        if not row or not row.value:
            return err('Nothing is waiting for that bill.', 404)
        pending = json.loads(row.value)
        session.delete(row)
        saved = None
        if body.get('yes') is True:
            r = BillReading(budget_item_id=bid, amount=pending.get('amount'),
                            due_date=date.fromisoformat(pending['due']) if pending.get('due') else None,
                            read_at=datetime.fromisoformat(pending['read_at']), source_host=pending.get('host') or '')
            session.add(r)
            session.flush()
            log_historian_event(session, 'bill_confirmed', context={
                'budget_item_id': bid, 'amount': r.amount, 'due_date': pending.get('due'), 'host': r.source_host,
                'read_at': pending.get('read_at')})
            saved = _bill_reading_json(r)
        session.commit()
    return ok({'id': bid, 'confirmed': saved})


@settings_bp.route('/bank-agent/bill-read/use', methods=['POST'])
@require_json
def bank_agent_bill_use():
    """B3 (a): {reading_id, use}. Use the confirmed bill's amount as this month's figure for its line - derived when
    the month is read, the saved amount untouched."""
    body = request.json or {}
    with db_session() as session:
        r = session.get(BillReading, int(body.get('reading_id') or 0))
        if not r:
            return err('That reading was not found.', 404)
        r.use_for_month = bool(body.get('use'))
        session.commit()
        return ok(_bill_reading_json(r))


# ── Item 68 B6/B7 - "can I pay this?" and "paid?" (core/bill_check.py computes; nothing here pays) ──
def _setting_json(session, key, default=None):
    row = _get_setting(session, key)
    try:
        return json.loads(row.value) if row and row.value else default
    except (TypeError, ValueError):
        return default


def _account_balance_facts(session, account_id):
    """The account's balance as the Accounts list shows it (the bank's own running balance where the download
    carried one, else the activity's net), its date, and when its transactions last came in (import_committed)."""
    txns = session.query(Transaction).filter_by(account_id=account_id).all()
    anchor, _ok = _resolve_bank_anchor(txns)
    if anchor is not None:
        balance, as_of = round(anchor.running_balance, 2), anchor.date
    elif txns:
        balance = round(sum(t.amount for t in txns if t.type == 'credit') - sum(t.amount for t in txns if t.type == 'debit'), 2)
        as_of = None
    else:
        balance, as_of = None, None
    last = None
    for e in session.query(HistorianEntry).filter(HistorianEntry.event_category == 'import_committed') \
            .order_by(HistorianEntry.id.desc()).limit(500).all():
        if json.loads(e.context_json or '{}').get('account_id') == account_id:
            last = e.created_at
            break
    return balance, as_of, last, txns


@settings_bp.route('/bank-agent/buffer', methods=['POST'])
@require_json
def bank_agent_buffer():
    """B6: {account_id, amount}. The person's own floor for an account - kept as they said it, changed only by them.
    amount null removes it."""
    body = request.json or {}
    with db_session() as session:
        a = session.get(Account, int(body.get('account_id') or 0))
        if not a:
            return err('That account was not found.', 404)
        if body.get('amount') in (None, ''):
            row = _get_setting(session, f'bank_buffer:account:{a.id}')
            if row:
                session.delete(row)
            amt = None
        else:
            try:
                amt = round(float(body.get('amount')), 2)
            except (TypeError, ValueError):
                return err('An amount, please.', 400)
            if amt < 0:
                return err('An amount of zero or more, please.', 400)
            _set_setting(session, f'bank_buffer:account:{a.id}',
                         json.dumps({'amount': amt, 'said': datetime.now().isoformat(timespec='seconds')}))
        session.commit()
    return ok({'account_id': a.id, 'amount': amt})


@settings_bp.route('/bank-agent/bill-from', methods=['POST'])
@require_json
def bank_agent_bill_from():
    """B6: {id, account_id}. Which account the person pays this bill from (their statement; null removes it)."""
    body = request.json or {}
    with db_session() as session:
        b = session.get(BudgetItem, int(body.get('id') or 0))
        if not b:
            return err('That bill was not found.', 404)
        bid = b.id      # read before the commit: the reply is built after the session closes
        acct = body.get('account_id')
        if acct in (None, ''):
            row = _get_setting(session, f'bill_from:{b.id}')
            if row:
                session.delete(row)
        else:
            if not session.get(Account, int(acct)):
                return err('That account was not found.', 404)
            _set_setting(session, f'bill_from:{b.id}', str(int(acct)))
        session.commit()
    return ok({'id': bid, 'account_id': acct})


@settings_bp.route('/bank-agent/bill-paid', methods=['POST'])
@require_json
def bank_agent_bill_paid():
    """B7: {reading_id, txn_id, yes}. The person's answer to "is this the payment?" - a near-match is never assumed."""
    body = request.json or {}
    rid, tid = int(body.get('reading_id') or 0), int(body.get('txn_id') or 0)
    with db_session() as session:
        if not session.get(BillReading, rid) or not session.get(Transaction, tid):
            return err('Not found.', 404)
        ans = _setting_json(session, f'bill_paid:{rid}', {'yes': None, 'no': []})
        if body.get('yes') is True:
            ans['yes'] = tid
        else:
            ans['no'] = sorted(set(ans.get('no') or []) | {tid})
            if ans.get('yes') == tid:
                ans['yes'] = None
        _set_setting(session, f'bill_paid:{rid}', json.dumps(ans))
        session.commit()
    return ok(ans)


@settings_bp.route('/bank-agent/bill-checks', methods=['GET'])
def bank_agent_bill_checks():
    """B6/B7 for every bill with a confirmed reading: the paying account, the check against the floor (with the
    24-hour notice), and whether its payment has been seen. Computed on every read; nothing is written."""
    from core import bill_check
    now = datetime.now()            # the Historian's times are local, as every time is (item 109)
    out, accounts = [], []
    with db_session() as session:
        for a in session.query(Account).filter_by(is_active=True).order_by(Account.sort_order, Account.name).all():
            buf = _setting_json(session, f'bank_buffer:account:{a.id}')
            accounts.append({'id': a.id, 'name': a.name, 'buffer': (buf or {}).get('amount'),
                             'has_portal': bool(_bank_agent_url(session, f'account:{a.id}'))})
        latest = {}
        for r in session.query(BillReading).order_by(BillReading.id.desc()).all():
            latest.setdefault(r.budget_item_id, r)
        facts, items = {}, {}
        for bid, r in latest.items():
            b = session.get(BudgetItem, bid)
            if not b or not b.is_active:
                continue
            items[bid] = (b, r)
        for bid, (b, r) in items.items():
            frm = _get_setting(session, f'bill_from:{bid}')
            acct_id = int(frm.value) if frm and (frm.value or '').isdigit() else None
            row = {'id': bid, 'name': b.name, 'reading_id': r.id, 'amount': r.amount,
                   'pay_steps': bool(((_bank_recipe(session, f'pay:{bid}') or {}).get('steps'))),
                   'due': r.due_date.isoformat() if r.due_date else None, 'account_id': acct_id,
                   'check': None, 'paid': None, 'last_download': None}
            if acct_id is not None:
                if acct_id not in facts:
                    facts[acct_id] = _account_balance_facts(session, acct_id)
                balance, as_of, last, txns = facts[acct_id]
                tx = [{'id': t.id, 'date': t.date, 'amount': t.amount, 'type': t.type, 'description': t.description,
                       'running_balance': t.running_balance} for t in txns if t.date]
                paid = bill_check.paid_match(r.amount, r.due_date, b.name, tx, _setting_json(session, f'bill_paid:{r.id}'))
                earlier = []
                for obid, (ob, orr) in items.items():
                    if obid == bid or orr.amount is None or orr.due_date is None or r.due_date is None:
                        continue
                    ofrm = _get_setting(session, f'bill_from:{obid}')
                    if not (ofrm and ofrm.value == str(acct_id)) or not (date.today() <= orr.due_date < r.due_date):
                        continue
                    if bill_check.paid_match(orr.amount, orr.due_date, ob.name, tx,
                                             _setting_json(session, f'bill_paid:{orr.id}'))['state'] != 'paid':
                        earlier.append((ob.name, orr.amount))
                buf = next((x['buffer'] for x in accounts if x['id'] == acct_id), None)
                chk = bill_check.pay_check(balance, as_of, last, buf, r.amount, earlier, now)
                row['check'] = chk
                row['last_download'] = last.isoformat(timespec='minutes') if last else None   # local time (item 109)
                t = paid['txn']
                row['paid'] = {'state': paid['state'],
                               'txn': ({'id': t['id'], 'date': t['date'].isoformat(), 'amount': t['amount'],
                                        'description': t['description']} if t else None),
                               'lowest': ({'amount': paid['lowest'][0], 'date': paid['lowest'][1].isoformat()}
                                          if paid['lowest'] else None)}
            out.append(row)
    return ok({'bills': out, 'accounts': accounts})


@settings_bp.route('/bank-agent/pay-open', methods=['POST'])
@require_json
def bank_agent_pay_open():
    """Item 68 B8 (b), ruled: {id}. Take the person to their bank's bill pay for this bill - by the way they recorded
    once - signed in with the bank account's login, and STOP. The window stays with the bill's facts on its bar; the
    person enters the amount and presses Pay. Groundwork never pays (TM1), and no step can press a payment's button."""
    import bank_agent_window
    from core import bank_vault, bill_check
    body = request.json or {}
    try:
        bid = int(body.get('id'))
    except (TypeError, ValueError):
        return err('Which bill?', 400)
    key = f'pay:{bid}'
    with db_session() as session:
        b = session.get(BudgetItem, bid)
        acct = _pay_account(session, bid)
        if not b or not acct:
            return err('Choose the account this bill is paid from first.', 400)
        url = _bank_agent_url(session, key)          # the bank's link, through the one function that hands it on
        if not url:
            return err("That account has no bank link.", 400)
        steps_ = ((_bank_recipe(session, key) or {}).get('steps')) or []
        if not steps_:
            return err("Show Groundwork the way to your bank's payment screen for this bill once first.", 400)
        login_key = f'account:{acct.id}'
        device_on = (_get_setting(session, f'bank_device:{login_key}') or AppSetting(value='')).value == 'yes'
        r = session.query(BillReading).filter_by(budget_item_id=bid).order_by(BillReading.id.desc()).first()
        balance, as_of, last, _tx = _account_balance_facts(session, acct.id)
        buf = (_setting_json(session, f'bank_buffer:account:{acct.id}') or {}).get('amount')
        chk = bill_check.pay_check(balance, as_of, last, buf, r.amount if r else None, [], datetime.now())
        name, acct_name = b.name, acct.name
    if not bank_vault.has_login(login_key):
        return err(f'Save a login for {acct_name} first.', 400)
    facts = f'{name}: ' + (f'${r.amount:,.2f}' if r and r.amount is not None else 'amount not read')
    facts += f' due {r.due_date:%b} {r.due_date.day}. ' if r and r.due_date else '. '
    if chk['state'] == 'fits':
        facts += f'{acct_name} would be ${chk["after"]:,.2f}, ${chk["margin"]:,.2f} above your ${buf:,.2f}'
    elif chk['state'] == 'below':
        facts += f'{acct_name} would be ${chk["after"]:,.2f}, ${-chk["margin"]:,.2f} below your ${buf:,.2f}'
    else:
        facts += 'Groundwork could not check your balance'
    if chk.get('stale'):
        facts += ' (last downloaded over 24 hours ago - newer transactions are not counted)'
    hold = facts + '. Enter the amount and press Pay yourself. Groundwork never pays.'
    device = str(_bank_device_dir(login_key, create=True)) if device_on else ''

    def _finished(k, events):
        end = next((e for e in reversed(events) if e.get('s') in bank_agent_window.TERMINAL), {}) or {}
        try:
            with db_session() as session:
                log_historian_event(session, 'bill_pay_opened', context={
                    'budget_item_id': bid, 'account_id': int(login_key.split(':')[1]), 'outcome': end.get('s'),
                    'why': end.get('why')})
                session.commit()
        except Exception:
            logging.getLogger('groundwork').warning('bill_pay_opened could not be recorded')
    result = bank_agent_window.start_fetch(key, url, steps_, device, on_finish=_finished,
                                           extra={'login_key': login_key, 'hold': hold})
    return ok({'id': bid, 'result': result})


@settings_bp.route('/bank-agent/fetch/stop', methods=['POST'])
@require_json
def bank_agent_fetch_stop():
    import bank_agent_window
    key = str((request.json or {}).get('key') or '')
    return ok({'key': key, 'stopped': bank_agent_window.stop_fetch(key)})


@settings_bp.route('/bank-agent/device', methods=['POST'])
@require_json
def bank_agent_device():
    """A7: {key, on}. On keeps the bank's cookies for this account in its own folder; off forgets them."""
    import shutil
    body = request.json or {}
    key = str(body.get('key') or '')
    with db_session() as session:
        if not _bank_agent_url(session, key):
            return err('That account has no bank link.', 400)
        if body.get('on'):
            _set_setting(session, f'bank_device:{key}', 'yes')
        else:
            row = _get_setting(session, f'bank_device:{key}')
            if row:
                session.delete(row)
            shutil.rmtree(_bank_device_dir(key), ignore_errors=True)
        session.commit()
    return ok({'key': key, 'remembered': bool(body.get('on'))})


@settings_bp.route('/bootstrap', methods=['GET'])
def bootstrap():
    """
    Single endpoint that returns everything needed to boot the app from the DB.
    Replaces the old /api/load snapshot pattern.
    Returns all core state in one round trip.
    """
    import sys, traceback
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    try:
        with db_session() as session:
            # ── Settings & preferences ─────────────────────────────────────────
            settings = {s.key: s.value for s in session.query(AppSetting).all()}
            if 'ai_enabled' not in settings:
                settings['ai_enabled'] = 'true'

            # ── Budget items ───────────────────────────────────────────────────
            from core.database import BudgetItem
            budget_items = session.query(BudgetItem).filter_by(is_active=True) \
                                  .order_by(BudgetItem.type, BudgetItem.sort_order).all()
            incomes  = [{'id':i.id,'name':i.name,'amount':i.amount}
                        for i in budget_items if i.type == 'income']
            _month = budget_month_amounts(session)
            expenses = [{'id':i.id,'name':i.name,'amount':i.amount,
                         'cat': i.category or 'Other', **_month.get(i.id, {})}
                        for i in budget_items if i.type == 'expense']

            # ── Debt accounts ──────────────────────────────────────────────────
            debt_accounts = session.query(DebtAccount).filter_by(is_active=True).all()
            try:
                debts = [serialize_debt_account(d, session) for d in debt_accounts]
            except Exception as _debt_err:
                logging.error('bootstrap: serialize_debt_account failed: %s\n%s',
                              _debt_err, traceback.format_exc())
                debts = [{
                    'id':               d.id,
                    'name':             d.name,
                    'begin_balance':    d.begin_balance,
                    'current_balance':  d.current_balance,
                    'interest_rate':    d.interest_rate,
                    'minimum_payment':  d.minimum_payment,
                    'due_day':          d.due_day,
                    'is_active':        d.is_active,
                    'debt_type':        'credit',
                    'calculated_balance': None,
                    'linked_account_id':  None,
                    'linked_account_name':None,
                    'linked_txn_count':   0,
                    'start_date':       None,
                    'end_date':         None,
                    'credit_limit':     None,
                    'interest_rate_source':   getattr(d, 'interest_rate_source', None),
                    'minimum_payment_source': getattr(d, 'minimum_payment_source', None),
                    'statement_as_of':        None,
                    'paid_off_at':      None,
                } for d in debt_accounts]

            # ── Achievements ───────────────────────────────────────────────────
            achievements = session.query(Achievement).all()
            earned_ids   = [a.achievement_id for a in achievements]

            # ── BYB items ──────────────────────────────────────────────────────
            byb_items = session.query(BYBItem).order_by(BYBItem.created_at).all()
            byb = [{
                'id':       b.id,
                'type':     b.item_type,
                'name':     b.name,
                'category': b.category,
                'monthly':  b.monthly_cost,
                'replacing': {'name': b.replacing_name, 'amount': b.replacing_amount}
                              if b.replacing_name else None,
            } for b in byb_items]

            # ── Net worth settings ─────────────────────────────────────────────
            # BUG FIX (July 6): retirement401k/retirementIRA were missing from
            # this dict entirely. app.js reads S.netWorth.retirement401k from
            # here (with a fallback to `prefs`, which never had it either —
            # see below), so both paths were always undefined and always
            # defaulted to 0 regardless of what was actually saved via
            # PATCH /api/settings. Confirmed in the field: these values never
            # survived a reboot. Added here, reading the same settings keys
            # updateNetWorth() in app.js already correctly saves to.
            net_worth = {
                'savings':        float(settings.get('savings_balance',    0) or 0),
                'investments':    float(settings.get('investments_balance',0) or 0),
                'cash':           float(settings.get('cash_balance',       0) or 0),
                'homeValue':      float(settings.get('home_value',        0) or 0),
                'mortgage':       float(settings.get('mortgage_balance',  0) or 0),
                'retirement401k': float(settings.get('retirement_401k',   0) or 0),
                'retirementIRA':  float(settings.get('retirement_ira',    0) or 0),
            }

            # ── App preferences (previously in snapshot) ───────────────────────
            prefs = {
                'monthlyBudget':  float(settings.get('monthly_budget',  1500) or 1500),
                'savingsPct':     float(settings.get('savings_pct',      10)  or 10),
                'debtMethod':     settings.get('debt_method',     'avalanche'),
                'proactiveDial':  settings.get('proactive_dial',  'normal'),
                'dfmActive':      settings.get('dfm_active',      'false') == 'true',
                'dfmSavingsCut':  float(settings.get('dfm_savings_cut', 5) or 5),
                'strategyStreak': int(settings.get('strategy_streak',   0) or 0),
                'paymentStreak':  int(settings.get('payment_streak',    0) or 0),
            }

            # Historian: app open. bootstrap is the one request guaranteed to
            # fire on every launch, so session_start is logged here rather than
            # trusting a client signal. Engagement telemetry must never break
            # the boot path, so a logging failure is swallowed — the return
            # below is what actually matters.
            try:
                log_historian_event(session, 'session_start')
                session.commit()
            except Exception as _hist_err:
                logging.warning('bootstrap: session_start log failed: %s', _hist_err)
                session.rollback()

            return ok({
                'incomes':           incomes,
                'expenses':          expenses,
                'debts':             debts,
                'earnedAchievements':earned_ids,
                'bybItems':          byb,
                'netWorth':          net_worth,
                'prefs':             prefs,
                'settings':          settings,
            })

    except Exception as _boot_err:
        tb = traceback.format_exc()
        logging.error('bootstrap CRASHED: %s\n%s', _boot_err, tb)
        # Return the actual error in the response so it shows in browser dev tools
        return jsonify({
            'error':     'Bootstrap failed',
            'detail':    str(_boot_err),
            'traceback': tb,
        }), 500


categories_bp = Blueprint('categories', __name__)


def serialize_category(c: Category) -> dict:
    return {
        'id':          c.id,
        'name':        c.name,
        'icon':        c.icon or '',
        'color':       c.color or '#8a9bac',
        'parent_id':   c.parent_id,
        'is_system':   c.is_system,
        'is_optional': getattr(c, 'is_optional', False) or False,
        'is_enabled':  getattr(c, 'is_enabled', True) if getattr(c, 'is_enabled', None) is not None else True,
        'sort_order':  c.sort_order,
        'type':        c.type or 'expense',
    }


def suggest_category_for_merchant(session, merchant_name: str) -> dict:
    """
    Phase H2 Feature 1 (adaptive learning — category suggestions). Most
    common category this user has actually picked for a merchant, from real
    transaction history — not a guess, a frequency count over what already
    happened. Reads the main Transaction table (checking/credit ledger),
    where merchant categorization history actually lives.
    """
    if not merchant_name or not merchant_name.strip():
        return {'category': None, 'confidence_pct': None, 'sample_size': 0}
    term = merchant_name.strip()
    rows = session.query(Category.name, func.count(Transaction.id).label('freq')).join(
        Transaction, Transaction.category_id == Category.id
    ).filter(Transaction.merchant.ilike(f'%{term}%')).group_by(Category.name).order_by(desc('freq')).all()
    if not rows:
        return {'category': None, 'confidence_pct': None, 'sample_size': 0}
    total = sum(r[1] for r in rows)
    return {
        'category': rows[0][0],
        'confidence_pct': round(rows[0][1] / total * 100, 1),
        'sample_size': total,
    }


@categories_bp.route('/suggest', methods=['GET'])
def suggest_category():
    merchant = request.args.get('merchant', '')
    with db_session() as session:
        return ok(suggest_category_for_merchant(session, merchant))


@categories_bp.route('/suggest-feedback', methods=['POST'])
@require_json
def suggest_category_feedback():
    """
    Phase H2 Feature 1's missing other half — the docstring on
    HistorianEntry always described categorization_suggestion_confirm/
    reject as scaffold-only because nothing called this. Body:
    { merchant: str, suggested_category: str, kept: bool } — kept is
    whether the suggestion shown was still the category at save time
    (app.js compares the two; this route just logs the outcome, no
    category_id FK since suggestions are keyed by merchant name, not a
    saved transaction's category row).
    """
    body      = request.json
    merchant  = (body.get('merchant') or '').strip()
    suggested = (body.get('suggested_category') or '').strip()
    kept      = bool(body.get('kept'))
    if not merchant or not suggested:
        return err('merchant and suggested_category are required')
    with db_session() as session:
        log_historian_event(
            session, 'categorization_suggestion_confirm' if kept else 'categorization_suggestion_reject',
            context={'merchant': merchant, 'suggested_category': suggested},
        )
        session.commit()
    return ok({'logged': True})


@categories_bp.route('', methods=['GET'])
def list_categories():
    with_counts = request.args.get('counts', 'false').lower() == 'true'
    with db_session() as session:
        cats = session.query(Category).order_by(
            Category.is_system.desc(), Category.sort_order, Category.name
        ).all()
        result = []
        for c in cats:
            d = serialize_category(c)
            if with_counts:
                d['transaction_count'] = session.query(Transaction)\
                    .filter_by(category_id=c.id).count()
            result.append(d)
        return ok(result)


@categories_bp.route('', methods=['POST'])
@require_json
def create_category():
    body = request.json
    name = (body.get('name') or '').strip()
    if not name:
        return err('name is required')
    with db_session() as session:
        existing = session.query(Category).filter(
            func.lower(Category.name) == name.lower()
        ).first()
        if existing:
            return err(f'Category "{name}" already exists')
        cat = Category(
            name=name,
            icon=body.get('icon', ''),
            color=body.get('color', '#8a9bac'),
            type=body.get('type', 'expense'),
            parent_id=body.get('parent_id'),
            is_system=False,
            sort_order=999,
        )
        session.add(cat)
        session.flush()
        session.commit()
        return ok(serialize_category(cat), status=201)


@categories_bp.route('/<int:cat_id>', methods=['PATCH'])
@require_json
def update_category(cat_id):
    body = request.json
    with db_session() as session:
        cat = session.get(Category, cat_id)
        if not cat:
            return err('Category not found', 404)
        if 'name' in body and body['name'].strip():
            if cat.is_system:
                return err('System category names cannot be changed')
            cat.name = body['name'].strip()
        if 'icon'  in body: cat.icon       = body['icon']
        if 'is_enabled' in body:  cat.is_enabled  = bool(body['is_enabled'])
        if 'parent_id'  in body:  cat.parent_id   = body.get('parent_id')
        if 'color' in body: cat.color      = body['color']
        if 'sort_order' in body: cat.sort_order = int(body['sort_order'])
        session.commit()
        return ok(serialize_category(cat))


@categories_bp.route('/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    with db_session() as session:
        cat = session.get(Category, cat_id)
        if not cat:
            return err('Category not found', 404)
        if cat.is_system:
            return err('System categories cannot be deleted')
        other     = session.query(Category).filter_by(name='Other').first()
        other_id  = other.id if other else None
        moved     = session.query(Transaction).filter_by(category_id=cat_id).all()
        for t in moved:
            t.category_id = other_id
        session.delete(cat)
        session.commit()
        return ok({'deleted': cat_id, 'transactions_moved': len(moved)})


@categories_bp.route('/<int:cat_id>/merge', methods=['POST'])
@require_json
def merge_category(cat_id):
    body      = request.json
    target_id = body.get('target_id')
    if not target_id:
        return err('target_id required')
    with db_session() as session:
        source = session.get(Category, cat_id)
        target = session.get(Category, int(target_id))
        if not source: return err('Source category not found', 404)
        if not target: return err('Target category not found', 404)
        if source.id == target.id: return err('Source and target cannot be the same')
        moved = session.query(Transaction).filter_by(category_id=source.id).all()
        for t in moved: t.category_id = target.id
        # Budget lines carry the category's NAME, not an id (item 52: the
        # id lookup here raised on every merge since 1.0, so no merge ever saved).
        bmoved = session.query(BudgetItem).filter(func.lower(BudgetItem.category) == source.name.lower()).all()
        for b in bmoved: b.category = target.name
        if not source.is_system: session.delete(source)
        session.commit()
        return ok({'transactions_moved': len(moved), 'budget_items_moved': len(bmoved),
                   'target': serialize_category(target)})


# ── Item 52 L5 (CATEGORY_LABELS.md, Rob 2026-10-09): what is already saved ──
# Before item 52 the importer filed fill-ups under Gas, the natural-gas utility,
# and gyms under a "Fitness" that is not in the tree. Fixing the names fixed new
# imports only. This offers the rows already saved - each with its amount - and
# moves nothing without the user's yes (no silent writing).

def _label_review(session):
    import bank_importer as bi
    cats = session.query(Category).all()
    by = {c.name: c for c in cats}
    parent = {c.id: c.name for c in cats}
    gas = next((c for c in cats if c.name in ('Natural Gas', 'Gas') and parent.get(c.parent_id) == 'Utilities'), None)   # item 84
    fuel, gym = by.get('Gasoline / Diesel'), by.get('Gym / Fitness')
    rows, groc_rows = [], []
    if gas and fuel:
        for t in session.query(Transaction).filter(Transaction.category_id == gas.id, Transaction.type == 'debit').all():
            if bi.auto_category(t.description or '', t.mcc or '') == 'Gasoline / Diesel':
                rows.append(t)
    # Item 53 G7 (FUEL_NAMES.md): warehouse-club and grocery fuel (Costco Gas, Meijer Express) that older imports
    # saved under Groceries, offered the same way.
    groc = by.get('Groceries')
    if groc and fuel:
        for t in session.query(Transaction).filter(Transaction.category_id == groc.id, Transaction.type == 'debit').all():
            if bi.auto_category(t.description or '', t.mcc or '') == 'Gasoline / Diesel':
                groc_rows.append(t)
    stray = next((c for c in cats if c.name.lower() == 'fitness' and not c.is_system), None)
    return gas, fuel, gym, rows, stray, groc_rows


# Item 54 M6 (MATCHER_ONE_ANSWER.md): the categories the two old matchers saved that today's rules no longer give -
# the server's parents, and the page's wrong leaves. A row in one of them whose words now name a different real
# leaf is offered, grouped by from -> to. Gas and Groceries rows that are fuel are item 52/53's own blocks.
_OLD_MATCHER_ANSWERS = ('Utilities', 'Insurance', 'Transportation', 'Food', 'Healthcare', 'Entertainment', 'Education',
                        'Personal', 'Subscriptions', 'Income', 'Property Taxes',
                        'Gasoline / Diesel', 'Groceries', 'Health Insurance', 'Electric', 'Doctor / Co-pays',
                        'Interest / Fees', 'Other Subscriptions',
                        # Item 55 C5: the page's card-code leaves that are now wrong for some codes
                        'Personal Care', 'Tuition / Courses')


_MUNICIPAL_FROM = ('Other', 'Water / Sewer', 'Utilities')


def _regroup_review(session):
    import bank_importer as bi
    cats = session.query(Category).all()
    by_id = {c.id: c for c in cats}
    by_name = {c.name: c for c in cats}
    # Item 56 U6: Other and Water / Sewer are old answers only for a municipal utility bill
    from_ids = [c.id for c in cats if c.name in _OLD_MATCHER_ANSWERS or c.name in _MUNICIPAL_FROM]
    groups = {}
    if not from_ids:
        return groups
    for t in session.query(Transaction).filter(Transaction.category_id.in_(from_ids)).all():
        src = by_id[t.category_id].name
        to = bi.auto_category(t.description or '', t.mcc or '')
        if to in ('Other', src) or to not in by_name:
            continue
        if to == 'Gasoline / Diesel' and src in ('Natural Gas', 'Gas', 'Groceries'):
            continue                  # item 52/53's blocks
        if src in _MUNICIPAL_FROM and src not in _OLD_MATCHER_ANSWERS and to != 'Municipal Utilities':
            continue                  # item 56 U6: from Other or Water / Sewer, only to Municipal Utilities
        groups.setdefault((src, to), []).append(t)
    # Item 85: a row whose card code item 85 corrected (home stores were Rent / Mortgage) is offered to its new leaf,
    # when the code now names one - never to Other: those rows stay where they are, as before
    fixed = ['5200', '5211', '5251', '5310', '5311', '5331', '5399', '5712', '5713', '5722', '5732', '5932', '5942', '5947', '5969', '5999']
    seen = {t.id for rs in groups.values() for t in rs}
    for t in session.query(Transaction).filter(Transaction.type == 'debit', (Transaction.mcc.in_(list(fixed))) |
                                               (Transaction.category_id.in_([c.id for c in cats if c.name in ('Clothing', 'Rent / Mortgage')]))).all():
        if t.id in seen or t.category_id not in by_id:
            continue
        src, to = by_id[t.category_id].name, bi.auto_category(t.description or '', t.mcc or '')
        if to not in ('Other', src) and to in by_name:
            groups.setdefault((src, to), []).append(t)
    # Item 84: a charging row is offered from wherever older rules left it (Rob's sat in Car Maintenance and Car Lease
    # Payment, card code 5552) - shown first, moved only on the person's yes, like every row here
    ev = by_name.get('EV Charging')
    if ev:
        seen = {t.id for rs in groups.values() for t in rs}
        for t in session.query(Transaction).filter(Transaction.type == 'debit', Transaction.category_id != ev.id).all():
            if t.id in seen or t.category_id not in by_id:
                continue
            if bi.auto_category(t.description or '', t.mcc or '') == 'EV Charging':
                groups.setdefault((by_id[t.category_id].name, 'EV Charging'), []).append(t)
    return groups


@categories_bp.route('/label-review', methods=['GET'])
def category_label_review():
    with db_session() as session:
        gas, fuel, gym, rows, stray, groc_rows = _label_review(session)

        def block(src, rs):
            rs.sort(key=lambda t: t.date, reverse=True)
            return {'from': src, 'to': 'Gasoline / Diesel', 'count': len(rs), 'total': round(sum(float(t.amount) for t in rs), 2),
                    'rows': [{'id': t.id, 'date': t.date.isoformat(), 'description': t.description or '',
                              'amount': float(t.amount)} for t in rs]}
        out = {'fuel': block(gas.name if gas else 'Natural Gas', rows) if rows else None,
               'fuel_groceries': block('Groceries', groc_rows) if groc_rows else None, 'fitness': None}
        out['regroup'] = [{**block(src, rs), 'to': to} for (src, to), rs in sorted(_regroup_review(session).items())]
        if stray and gym:
            n = session.query(Transaction).filter_by(category_id=stray.id).count()
            out['fitness'] = {'id': stray.id, 'name': stray.name, 'count': n, 'to_id': gym.id, 'to': gym.name}
        return ok(out)


@categories_bp.route('/label-review/move', methods=['POST'])
@require_json
def category_label_review_move():
    """Move the fill-ups the user said yes to. Only rows the review itself offers can move."""
    ids = {int(i) for i in (request.json.get('ids') or []) if str(i).isdigit()}
    with db_session() as session:
        gas, fuel, gym, rows, stray, groc_rows = _label_review(session)
        moved = 0
        for t in rows + groc_rows:
            if t.id in ids:
                t.category_id = fuel.id
                moved += 1
        # Item 54 M6: each regrouped row goes to the leaf the review offered it for
        to_cat = {c.name: c for c in session.query(Category).all()}
        for (src, to), rs in _regroup_review(session).items():
            for t in rs:
                if t.id in ids:
                    t.category_id = to_cat[to].id
                    moved += 1
        session.commit()
        return ok({'moved': moved})


@categories_bp.route('/bulk-categorize', methods=['POST'])
@require_json
def bulk_categorize():
    """Recategorize a specific list of transaction IDs to a new category."""
    body     = request.json
    ids      = body.get('ids', [])
    category = (body.get('category') or '').strip()
    if not ids or not category:
        return err('ids and category required')
    with db_session() as session:
        cat = session.query(Category).filter(
            func.lower(Category.name) == category.lower()
        ).first()
        if not cat:
            return err(f'Category "{category}" not found')
        txns = session.query(Transaction).filter(Transaction.id.in_(ids)).all()
        for t in txns:
            t.category_id = cat.id
        session.commit()
        return ok({'updated': len(txns), 'category': category})


@categories_bp.route('/smart-backfill', methods=['POST'])
@require_json
def smart_backfill():
    """
    Re-categorize transactions that are still in 'Other' or 'Personal'
    (the two catch-all buckets) using the current bank_importer categorization
    engine. Leaves any other category alone — this is explicitly a cleanup
    pass, not a wholesale recategorization.

    Body: { "dry_run": false }
    Returns: { "updated": N, "skipped": M, "sample": [...] }
    """
    import importlib, sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        bi = importlib.import_module('bank_importer')
        importlib.reload(bi)
    except Exception as e:
        return err(f'Could not load bank_importer: {e}')

    dry_run    = bool((request.json or {}).get('dry_run', False))

    with db_session() as session:
        cat_map = {c.name.lower(): c for c in session.query(Category).all()}

        # Only target rows currently in Other or Personal
        target_ids = {c.id for name, c in cat_map.items()
                      if name in ('other', 'personal')}
        if not target_ids:
            return ok({'updated': 0, 'skipped': 0, 'message': 'No Other/Personal categories found'})

        txns    = session.query(Transaction).filter(
            Transaction.category_id.in_(target_ids)
        ).all()

        updated  = 0
        skipped  = 0
        sample   = []

        for t in txns:
            desc = t.description or ''
            mcc  = t.mcc or ''
            new_cat_name = bi.auto_category(desc, mcc)

            # Only update if we found something better than Other/Personal
            if new_cat_name.lower() in ('other', 'personal'):
                skipped += 1
                continue

            new_cat = cat_map.get(new_cat_name.lower())
            if not new_cat:
                # Item 52 L4 (CATEGORY_LABELS.md): never mint a category from a
                # matcher's name - a parentless ghost the budget doesn't track.
                # A name the user's categories don't hold leaves the row as it is.
                skipped += 1
                continue

            if len(sample) < 10:
                sample.append({
                    'description': desc[:60],
                    'from': t.category.name if t.category else 'Other',
                    'to':   new_cat_name,
                })

            if not dry_run:
                t.category_id = new_cat.id
            updated += 1

        if not dry_run:
            session.commit()

        return ok({
            'updated':   updated,
            'skipped':   skipped,
            'dry_run':   dry_run,
            'sample':    sample,
            'message':   f"{'Would update' if dry_run else 'Updated'} {updated} transactions. {skipped} remain in Other/Personal (no better match found).",
        })


@categories_bp.route('/reclassify-income', methods=['POST'])
@require_json
def reclassify_income():
    """
    One-time backfill for a categorization bug (fixed same day as this route
    was added): Transfer's generic \\bdeposit\\b pattern used to be checked
    BEFORE Income's payroll/direct-deposit patterns in bank_importer.py's
    first-match-wins list, so every real paycheck deposit landed in Transfer
    instead of Income. That ordering is now fixed for new imports — this
    route re-runs the corrected categorizer against existing credit
    transactions still sitting in Transfer, and moves any that now resolve
    to Income. Scoped tightly (credits only, Transfer only) so it can't
    reclassify anything else.

    Body: { "dry_run": false }
    Returns: { "updated": N, "sample": [...] }
    """
    import importlib, sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        bi = importlib.import_module('bank_importer')
        importlib.reload(bi)
    except Exception as e:
        return err(f'Could not load bank_importer: {e}')

    dry_run = bool((request.json or {}).get('dry_run', False))

    with db_session() as session:
        transfer_cat = session.query(Category).filter(
            func.lower(Category.name) == 'transfer'
        ).first()
        income_cat = session.query(Category).filter(
            func.lower(Category.name) == 'income'
        ).first()
        if not transfer_cat or not income_cat:
            return ok({'updated': 0, 'sample': [], 'message': 'No Transfer/Income category found'})

        txns = session.query(Transaction).filter(
            Transaction.category_id == transfer_cat.id,
            Transaction.type == 'credit',
        ).all()

        updated = 0
        sample  = []
        for t in txns:
            new_cat_name = bi.auto_category(t.description or '', t.mcc or '')
            if new_cat_name.lower() != 'income':
                continue
            if len(sample) < 10:
                sample.append({'description': (t.description or '')[:60], 'amount': t.amount})
            if not dry_run:
                t.category_id = income_cat.id
            updated += 1

        if not dry_run:
            session.commit()

        return ok({
            'updated': updated,
            'dry_run': dry_run,
            'sample':  sample,
            'message': f"{'Would move' if dry_run else 'Moved'} {updated} transaction(s) from Transfer to Income.",
        })


# ── Investments (Phase 4B) ────────────────────────────────────────────────────

investments_bp = Blueprint('investments', __name__)


def _serialize_inv_txn(t) -> dict:
    return {
        'id':              t.id,
        'account_id':      t.account_id,
        'type':            t.type,
        'ticker':          t.ticker.upper(),
        'security_type':   t.security_type,
        'shares':          t.shares,
        'price_per_share': t.price_per_share,
        'total_amount':    t.total_amount,
        'fees':            t.fees or 0.0,
        'date':            t.date.isoformat(),
        'note':            t.note or '',
    }


def _apply_splits(ticker: str, purchase_date, cost_basis: float,
                  shares: float, session) -> tuple[float, float]:
    """
    Adjust cost_basis_per_share and shares for any splits that occurred
    after the purchase_date for this ticker.
    Returns (adjusted_cost_basis, adjusted_shares).
    """
    import json

    splits = session.query(InvestmentTransaction).filter(
        InvestmentTransaction.ticker == ticker.upper(),
        InvestmentTransaction.type == 'split',
        InvestmentTransaction.date > purchase_date,
    ).order_by(InvestmentTransaction.date).all()

    for split in splits:
        try:
            meta  = json.loads(split.meta or '{}')
            ratio = float(meta.get('ratio', 1.0))
            if ratio > 0:
                shares    *= ratio
                cost_basis /= ratio
        except (ValueError, TypeError, json.JSONDecodeError):
            logging.getLogger('groundwork').warning(
                'corrupt split meta on txn — ratio ignored', exc_info=True)

    return cost_basis, shares


@investments_bp.route('/transactions', methods=['GET'])
def list_inv_transactions():
    """List investment transactions, optionally filtered by account or ticker."""
    account_id = request.args.get('account_id')
    ticker     = request.args.get('ticker', '').upper()
    with db_session() as session:
        q = session.query(InvestmentTransaction)
        if account_id: q = q.filter_by(account_id=int(account_id))
        if ticker:     q = q.filter_by(ticker=ticker)
        txns = q.order_by(desc(InvestmentTransaction.date)).all()
        return ok([_serialize_inv_txn(t) for t in txns])


@investments_bp.route('/transactions', methods=['POST'])
@require_json
def create_inv_transaction():
    """
    Record a buy, sell, dividend, split, or other investment transaction.
    For buys: automatically creates a new lot.
    For sells: reduces existing lots using FIFO (default) and records realized gain.
    For splits: stores the split ratio in meta JSON.
    """
    body       = request.json
    txn_type   = body.get('type', 'buy').lower()
    ticker     = (body.get('ticker') or '').strip().upper()
    account_id = int(body.get('account_id', 1))

    if not ticker:
        return err('ticker is required')

    try:
        txn_date = date.fromisoformat(body['date'])
    except (KeyError, ValueError):
        return err('valid date required (YYYY-MM-DD)')

    shares    = abs(float(body.get('shares', 0)))
    price     = abs(float(body.get('price_per_share', 0)))
    total     = abs(float(body.get('total_amount', 0) or shares * price))
    fees      = abs(float(body.get('fees', 0)))
    note      = body.get('note', '')
    security_type = body.get('security_type', 'stock')
    meta_raw  = body.get('meta', {})

    with db_session() as session:
        # ── Oversell guard (July 8, audit week) ──────────────────────────────
        # Previously a sell exceeding open lots consumed everything available,
        # logged a server-side warning, and still returned 201 — the client
        # showed a normal success toast while the transaction row permanently
        # recorded the phantom quantity (a typo'd extra zero committed
        # silently). The client has no shares-held validation of its own, so
        # this check is the only line of defense. It runs BEFORE the txn row
        # is created or anything is added to the session, so an early return
        # cannot leave a half-applied transaction behind regardless of
        # db_session's commit-on-exit semantics.
        if txn_type == 'sell':
            if shares <= 0:
                return err('share quantity is required for a sell')
            available = session.query(
                func.sum(InvestmentLot.shares_remaining)
            ).filter_by(
                account_id=account_id, ticker=ticker, is_closed=False
            ).scalar() or 0.0
            if shares > available + 0.00001:
                return err(
                    f'Sell of {shares:g} exceeds shares held — this account '
                    f'has {available:g} open share(s) of {ticker}. '
                    f'Adjust the quantity or record the missing purchase first.',
                    400
                )

        # Record the transaction
        txn = InvestmentTransaction(
            account_id      = account_id,
            type            = txn_type,
            ticker          = ticker,
            security_type   = security_type,
            shares          = shares if txn_type in ('buy','transfer_in','reinvested_dividend') else -shares,
            price_per_share = price,
            total_amount    = total,
            fees            = fees,
            date            = txn_date,
            note            = note,
            meta            = json.dumps(meta_raw) if meta_raw else None,
            import_source   = 'manual',
        )
        session.add(txn)
        session.flush()

        # ── Buy / transfer in / reinvested dividend → create a lot ──────────
        if txn_type in ('buy', 'transfer_in', 'reinvested_dividend'):
            cost_per_share = price if price > 0 else (total / shares if shares else 0)
            lot = InvestmentLot(
                account_id           = account_id,
                source_transaction_id= txn.id,
                ticker               = ticker,
                security_type        = security_type,
                shares_original      = shares,
                shares_remaining     = shares,
                cost_basis_per_share = cost_per_share,
                purchase_date        = txn_date,
            )
            session.add(lot)

        # ── Sell → reduce lots per cost-basis method ──────────────────────────
        elif txn_type == 'sell':
            remaining_to_sell = shares
            sell_price        = price if price > 0 else (total / shares if shares else 0)

            # Determine cost basis method for this account
            method_key = f'cost_basis_method_{account_id}'
            method_row = _get_setting(session, method_key)
            method     = (method_row.value if method_row else None) or 'fifo'

            # Specific-lot IDs supplied in meta?
            specific_lot_ids = []
            if meta_raw and isinstance(meta_raw, dict):
                specific_lot_ids = [int(x) for x in meta_raw.get('lot_ids', [])]

            # Query open lots for this position
            q = session.query(InvestmentLot).filter_by(
                account_id=account_id, ticker=ticker, is_closed=False
            )

            if specific_lot_ids:
                # User chose specific lots — apply in the order supplied
                lots = [session.get(InvestmentLot, lid) for lid in specific_lot_ids
                        if session.get(InvestmentLot, lid) and
                           not session.get(InvestmentLot, lid).is_closed]
            elif method == 'lifo':
                lots = q.order_by(InvestmentLot.purchase_date.desc()).all()
            elif method == 'hifo':
                lots = q.order_by(InvestmentLot.cost_basis_per_share.desc()).all()
            else:  # fifo (default)
                lots = q.order_by(InvestmentLot.purchase_date).all()

            for lot in lots:
                if remaining_to_sell <= 0.00001:
                    break
                if lot is None:
                    continue

                shares_from_lot   = min(lot.shares_remaining, remaining_to_sell)
                lot.shares_remaining -= shares_from_lot
                remaining_to_sell    -= shares_from_lot

                # Record realized gain for the shares sold from this lot
                holding_days = (txn_date - lot.purchase_date).days if txn_date > lot.purchase_date else 0
                cost         = lot.cost_basis_per_share * shares_from_lot
                proceeds     = sell_price * shares_from_lot
                gain         = proceeds - cost
                gain_pct     = (gain / cost * 100) if cost else 0

                if lot.shares_remaining <= 0.00001:
                    # Lot fully exhausted — close it
                    lot.is_closed              = True
                    lot.closed_date            = txn_date
                    lot.sell_price_per_share   = sell_price
                    lot.realized_gain          = round(gain, 4)
                    lot.realized_gain_pct      = round(gain_pct, 4)
                    lot.holding_period_days    = holding_days
                    lot.shares_remaining       = 0.0
                else:
                    # Partial fill — accumulate realized gain on the lot
                    # (additional sells from this lot will add to it)
                    current_gain = lot.realized_gain or 0.0
                    lot.realized_gain = round(current_gain + gain, 4)

            if remaining_to_sell > 0.001:
                # Should be unreachable — the oversell guard above rejects
                # before mutation. If this ever fires, the guard and the lot
                # consumption disagree (e.g. a lot closed mid-request).
                logging.error('OVERSELL PAST GUARD: %s (acct %s) exceeds open lots by %.4f shares',
                              ticker, account_id, remaining_to_sell)

        session.flush()
        session.commit()
        return ok(_serialize_inv_txn(txn), status=201)


@investments_bp.route('/transactions/<int:txn_id>', methods=['DELETE'])
def delete_inv_transaction(txn_id):
    """
    Delete an investment transaction.
    For buys: also closes/removes the associated lot.
    For sells: re-opens reduced lots (best-effort).
    """
    with db_session() as session:
        txn = session.get(InvestmentTransaction, txn_id)
        if not txn:
            return err('Transaction not found', 404)

        if txn.type in ('buy', 'transfer_in', 'reinvested_dividend'):
            lot = session.query(InvestmentLot).filter_by(
                source_transaction_id=txn_id
            ).first()
            if lot:
                session.delete(lot)

        session.delete(txn)
        session.commit()
        return ok({'deleted': txn_id})


def _expense_ratio_for(ticker, pct_map, legacy_map, defaults_pct):
    """(fraction, source, unconfirmed): a holding's annual expense ratio as a FRACTION of its value (0.0003 = 0.03%).

    source 'yours' (entered in percent), 'default' (the published figure), or None. A value saved before the unit was
    stated came from a prompt that asked for a percent but stored an entry <= 1 as typed and divided a larger one by
    100. So a saved v <= 0.01 or v > 0.03 can only have been typed as a percent; a v in (0.01, 0.03] could be either
    (0.02% typed, or 2% divided). That one is not guessed: no figure, and `unconfirmed` carries it so the page asks.
    """
    if ticker in pct_map:
        return float(pct_map[ticker]) / 100, 'yours', None
    if ticker in legacy_map:
        v = float(legacy_map[ticker])
        if v <= 0.01 or v > 0.03:
            return v / 100, 'yours', None
        return None, None, v
    d = defaults_pct.get(ticker)
    return (d / 100, 'default', None) if d is not None else (None, None, None)


def _compute_portfolio_positions(session, account_id=None, skip_refresh=False):
    """
    Shared by GET /api/investments/positions and
    _log_investment_allocation_drift (net worth's Historian drift-tracking
    hook, further below) — extracted so both read the exact same market
    values instead of two independent computations quietly drifting apart.
    Returns (positions: list[dict], summary: dict) — same shape the route
    used to build inline.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    # Auto-refresh stale prices (silent — never blocks the caller)
    if not skip_refresh:
        try:
            from price_engine import refresh_stale_prices
            refresh_stale_prices(session)
        except ImportError:
            # price_engine isn't part of this build (investments price
            # feed is dormant). Log once, not on every request.
            global _PRICE_ENGINE_WARNED
            if not globals().get('_PRICE_ENGINE_WARNED'):
                _PRICE_ENGINE_WARNED = True
                logging.info('price_engine not present — price auto-refresh disabled')
        except Exception as e:
            logging.warning('Price refresh skipped: %s', e)

    q = session.query(InvestmentLot).filter_by(is_closed=False)
    if account_id:
        q = q.filter_by(account_id=int(account_id))
    lots = q.order_by(InvestmentLot.ticker, InvestmentLot.purchase_date).all()

    # Group lots by (account_id, ticker)
    positions = {}
    for lot in lots:
        key = (lot.account_id, lot.ticker)
        if key not in positions:
            positions[key] = {
                'ticker':        lot.ticker,
                'account_id':    lot.account_id,
                'security_type': lot.security_type,
                'lots':          [],
                'total_shares':  0.0,
                'total_cost':    0.0,
            }
        p = positions[key]

        # Apply splits to this lot's cost basis and shares
        adj_cost, adj_shares = _apply_splits(
            lot.ticker, lot.purchase_date,
            lot.cost_basis_per_share, lot.shares_remaining, session
        )
        p['lots'].append({
            'lot_id':        lot.id,
            'shares':        adj_shares,
            'cost_basis':    adj_cost,
            'purchase_date': lot.purchase_date.isoformat(),
        })
        p['total_shares'] += adj_shares
        p['total_cost']   += adj_shares * adj_cost
        # Item 35 V3: a lot with no cost basis has a known value but no known gain.
        if adj_cost is not None and adj_cost > 0:
            p['basis_shares'] = p.get('basis_shares', 0.0) + adj_shares
            p['basis_cost']   = p.get('basis_cost', 0.0) + adj_shares * adj_cost

    # Attach prices from cache
    result = []
    for pos in positions.values():
        if pos['total_shares'] < 0.00001:
            continue

        avg_cost = pos['total_cost'] / pos['total_shares'] if pos['total_shares'] else 0

        price_row = session.get(PriceCache, pos['ticker'])
        priced = bool(price_row and price_row.price is not None and price_row.price > 0)
        if priced:
            current_price    = price_row.price
            company_name     = price_row.company_name or pos['ticker']
            day_change       = price_row.day_change or 0
            day_change_pct   = price_row.day_change_pct or 0
        else:
            # Item 35 V1 (Rob 2026-10-03): no price on record means no value and no gain - never the cost, which is
            # what was paid, not what it is worth, and never zero. The holding is named in the summary instead.
            current_price    = None
            company_name     = (price_row.company_name if price_row else None) or pos['ticker']
            day_change       = 0
            day_change_pct   = 0

        basis_shares = pos.get('basis_shares', 0.0)
        basis_cost   = pos.get('basis_cost', 0.0)
        market_value = pos['total_shares'] * current_price if priced else None
        if priced and basis_shares > 0 and basis_cost > 0:
            unrealized_gain = basis_shares * current_price - basis_cost
            unrealized_pct  = unrealized_gain / basis_cost * 100
        else:
            unrealized_gain = unrealized_pct = None
        no_basis_shares = pos['total_shares'] - basis_shares

        result.append({
            'ticker':          pos['ticker'],
            'account_id':      pos['account_id'],
            'security_type':   pos['security_type'],
            'company_name':    company_name,
            'total_shares':    round(pos['total_shares'], 6),
            'avg_cost_basis':  round(avg_cost, 4),
            'total_cost':      round(pos['total_cost'], 2),
            'current_price':   round(current_price, 4) if priced else None,
            'market_value':    round(market_value, 2) if priced else None,
            'unrealized_gain': round(unrealized_gain, 2) if unrealized_gain is not None else None,
            'unrealized_pct':  round(unrealized_pct, 2) if unrealized_pct is not None else None,
            'day_change':      round(day_change, 4),
            'day_change_pct':  round(day_change_pct, 2),
            'price_stale':     not priced,          # (kept for older readers) true = no price on record
            'priced':          priced,
            # V4: every price carries its date; a manual price says so. No threshold, no verdict.
            'price_date':      (price_row.last_updated.date().isoformat()
                                if priced and price_row.last_updated else None),
            'price_manual':    bool(priced and price_row.is_manual),
            # V3: shares with no cost basis on record - in the value, left out of the gain
            'no_basis_shares': round(no_basis_shares, 6) if no_basis_shares > 0.00001 else 0,
            'gain_basis':      round(basis_cost, 2) if unrealized_gain is not None else None,
            'lots':            pos['lots'],
        })

    # Sort by market_value descending; holdings with no price on record last
    result.sort(key=lambda x: (x['market_value'] is not None, x['market_value'] or 0), reverse=True)

    # Inject user-defined asset_class and expense_ratio from app_settings
    ac_setting = _get_setting(session, 'inv_asset_classes_json')
    er_setting = _get_setting(session, 'inv_expense_ratios_json')        # saved before the unit was stated
    pct_setting = _get_setting(session, 'inv_expense_ratios_pct_json')   # the user's entries, in percent
    asset_classes   = json.loads(ac_setting.value)  if ac_setting  else {}
    expense_ratios  = json.loads(er_setting.value)  if er_setting  else {}
    expense_pct     = json.loads(pct_setting.value) if pct_setting else {}

    # Smart defaults for common tickers
    _ASSET_CLASS_DEFAULTS = {
        'BND':'fixed_income','BNDX':'fixed_income','AGG':'fixed_income',
        'TLT':'fixed_income','IEF':'fixed_income','SHY':'fixed_income',
        'VTIP':'fixed_income','VGLT':'fixed_income','VCIT':'fixed_income',
        'VXUS':'international_equity','VEU':'international_equity',
        'EFA':'international_equity','EEM':'international_equity',
        'SCHE':'international_equity','VWO':'international_equity',
        'VYMI':'international_equity','IEFA':'international_equity',
        'VNQ':'real_estate','VNQI':'real_estate','REZ':'real_estate',
        'SCHH':'real_estate','IYR':'real_estate',
    }
    # Published expense ratios in PERCENT (VOO 0.03 = 0.03% a year); handed to the page as a fraction (/ 100).
    _EXPENSE_RATIO_PCT_DEFAULTS = {
        'VOO':0.03,'VTI':0.03,'VUG':0.04,'VTV':0.04,'VXUS':0.07,
        'BND':0.03,'VNQ':0.13,'VWO':0.08,'EFA':0.07,'EEM':0.68,
        'SCHB':0.03,'SCHA':0.04,'SCHG':0.04,'SCHD':0.06,
        'IVV':0.03,'SPY':0.0945,'QQQ':0.2,'GLD':0.4,'SLV':0.5,
    }

    for p in result:
        t = p['ticker']
        p['asset_class']    = asset_classes.get(t) or _ASSET_CLASS_DEFAULTS.get(t) or None
        p['expense_ratio'], p['expense_ratio_source'], p['expense_ratio_unconfirmed'] = _expense_ratio_for(
            t, expense_pct, expense_ratios, _EXPENSE_RATIO_PCT_DEFAULTS)

    # Portfolio totals (item 35 V1): the value of what is priced, the gain on lots with a cost basis, and - named -
    # what each leaves out. One summary for the Investments page, Net Worth, the snapshots, the drift log and the
    # advisor prompt, so no two screens can disagree about the same holdings.
    total_cost         = sum(p['total_cost']    for p in result)
    total_market_value = sum(p['market_value'] for p in result if p['market_value'] is not None)
    gained             = [p for p in result if p['unrealized_gain'] is not None]
    gain_basis         = sum(p['gain_basis'] for p in gained)
    total_gain         = sum(p['unrealized_gain'] for p in gained) if gained else None
    total_gain_pct     = (total_gain / gain_basis * 100) if gained and gain_basis else None
    dates              = sorted(p['price_date'] for p in result if p['price_date'])

    summary = {
        'total_cost':         round(total_cost, 2),
        'total_market_value': round(total_market_value, 2),
        'total_gain':         round(total_gain, 2) if total_gain is not None else None,
        'total_gain_pct':     round(total_gain_pct, 2) if total_gain_pct is not None else None,
        'gain_basis':         round(gain_basis, 2),
        'position_count':     len(result),
        'unpriced':           [{'ticker': p['ticker'], 'shares': p['total_shares'], 'account_id': p['account_id']}
                               for p in result if not p['priced']],
        'no_basis':           [{'ticker': p['ticker'], 'shares': p['no_basis_shares']}
                               for p in result if p['priced'] and p['no_basis_shares']],
        'prices_from':        dates[0] if dates else None,
        'prices_to':          dates[-1] if dates else None,
        'manual_prices':      sorted({p['ticker'] for p in result if p['price_manual']}),
    }
    return result, summary


@investments_bp.route('/positions', methods=['GET'])
def get_positions():
    """
    Return current portfolio positions aggregated from open lots.
    Each position: ticker, total_shares, avg_cost_basis,
                   total_cost, current_price (from cache),
                   market_value, unrealized_gain, unrealized_pct,
                   day_change, day_change_pct.

    Optional ?account_id= filter.
    Automatically refreshes stale prices before computing positions.
    """
    account_id   = request.args.get('account_id')
    skip_refresh = request.args.get('skip_refresh', 'false').lower() == 'true'

    with db_session() as session:
        result, summary = _compute_portfolio_positions(session, account_id, skip_refresh)
        return ok({'positions': result, 'summary': summary})


@investments_bp.route('/price', methods=['PATCH'])
@require_json
def set_manual_price():
    """
    Set a manual price for a ticker. Marks it as manual so auto-refresh skips it.
    Body: { ticker: str, price: float }
    """
    body   = request.json
    ticker = (body.get('ticker') or '').strip().upper()
    price  = float(body.get('price', 0))
    if not ticker or price <= 0:
        return err('ticker and price > 0 required')

    with db_session() as session:
        row = session.get(PriceCache, ticker)
        if row:
            row.price        = price
            row.day_change   = price - (row.previous_close or price)
            row.day_change_pct = ((price - (row.previous_close or price)) / (row.previous_close or price) * 100) if row.previous_close else 0
            row.is_manual    = True
            row.last_updated = datetime.now()
        else:
            session.add(PriceCache(
                ticker       = ticker,
                price        = price,
                is_manual    = True,
                last_updated = datetime.now(),
                source       = 'manual',
            ))
        session.commit()
        return ok({'ticker': ticker, 'price': price, 'manual': True})


@investments_bp.route('/allocation/<asset_class>/confidence', methods=['GET'])
def investment_allocation_confidence(asset_class):
    """Investments' mirror of GET /api/debt/<id>/confidence and GET
    /api/net-worth/milestone/<id>/confidence — thin read of
    get_investment_allocation_confidence."""
    with db_session() as session:
        return ok(get_investment_allocation_confidence(session, asset_class))


@investments_bp.route('/accounts', methods=['GET'])
def list_investment_accounts():
    """List accounts of type 'investment' with their total market value."""
    with db_session() as session:
        accts = session.query(Account).filter_by(
            type='investment', is_active=True
        ).order_by(Account.sort_order, Account.name).all()
        return ok([_serialize_account(a, session) for a in accts])


@investments_bp.route('/prices/refresh', methods=['POST'])
def refresh_prices():
    """
    Trigger a price refresh for all stale positions.
    Body (optional): { force: bool, tickers: [str] }

    Returns: { refreshed: [tickers], skipped: [tickers], errors: int, prices: {...} }
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    body    = request.json or {}
    force   = bool(body.get('force', False))
    tickers = body.get('tickers', [])  # optional: refresh only specific tickers

    try:
        try:
            from price_engine import refresh_stale_prices, fetch_prices
        except ImportError:
            # The price-feed module isn't part of this build. Tell the truth —
            # the client was showing "check your connection" for this.
            return err('Price lookups aren\'t included in this beta build yet. '
                       'Your holdings and cost basis still track normally.', 501)
        with db_session() as session:
            if tickers:
                results = fetch_prices([t.upper() for t in tickers], session)
                _log_investment_allocation_drift(session)
                session.commit()
                return ok({
                    'refreshed': list(results.keys()),
                    'skipped':   [],
                    'errors':    len(tickers) - len(results),
                    'prices':    results,
                })
            else:
                result = refresh_stale_prices(session, force=force)
                _log_investment_allocation_drift(session)
                session.commit()
                return ok(result)
    except Exception as e:
        logging.exception('Price refresh failed')
        return err(f'Price refresh failed: {e}', 500)


@investments_bp.route('/prices/validate', methods=['GET'])
def validate_ticker():
    """
    Validate a ticker symbol and return basic info.
    Query param: ?ticker=VOO
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    symbol = request.args.get('ticker', '').strip().upper()
    if not symbol:
        return err('ticker parameter required')

    try:
        from price_engine import validate_ticker as _validate
        result = _validate(symbol)
        return ok(result)
    except Exception as e:
        return ok({'valid': False, 'symbol': symbol, 'error': str(e)})


@investments_bp.route('/prices', methods=['GET'])
def get_cached_prices():
    """
    Return all cached prices.
    Used by the frontend to check freshness without triggering a refresh.
    """
    with db_session() as session:
        rows = session.query(PriceCache).order_by(PriceCache.ticker).all()
        return ok([{
            'ticker':          r.ticker,
            'price':           r.price,
            'previous_close':  r.previous_close,
            'day_change':      r.day_change,
            'day_change_pct':  r.day_change_pct,
            'company_name':    r.company_name,
            'currency':        r.currency,
            'market_state':    r.market_state,
            'last_updated':    r.last_updated.isoformat() if r.last_updated else None,
            'is_manual':       r.is_manual,
            'source':          r.source,
        } for r in rows])


# ── Cost basis & lot accounting endpoints (Phase 4D) ─────────────────────────


@investments_bp.route('/realized-gains', methods=['GET'])
def get_realized_gains():
    """
    List all closed lots (realized gains/losses).
    Query params: ?account_id=  ?ticker=  ?year=2025  ?term=short|long
    """
    account_id = request.args.get('account_id')
    ticker     = request.args.get('ticker', '').upper()
    year       = request.args.get('year')
    term       = request.args.get('term', '').lower()  # 'short' | 'long'

    with db_session() as session:
        q = session.query(InvestmentLot).filter_by(is_closed=True)
        if account_id: q = q.filter_by(account_id=int(account_id))
        if ticker:     q = q.filter_by(ticker=ticker)
        if year:
            from sqlalchemy import extract
            q = q.filter(extract('year', InvestmentLot.closed_date) == int(year))
        lots = q.order_by(InvestmentLot.closed_date.desc()).all()

        result = []
        for lot in lots:
            holding_days = lot.holding_period_days or 0
            is_long_term = holding_days >= 366

            if term == 'short' and is_long_term:  continue
            if term == 'long'  and not is_long_term: continue

            result.append({
                'id':                   lot.id,
                'ticker':               lot.ticker,
                'account_id':           lot.account_id,
                'shares_sold':          lot.shares_original - (lot.shares_remaining or 0),
                'cost_basis_per_share': lot.cost_basis_per_share,
                'sell_price_per_share': lot.sell_price_per_share,
                'realized_gain':        lot.realized_gain,
                'realized_gain_pct':    lot.realized_gain_pct,
                'purchase_date':        lot.purchase_date.isoformat(),
                'sell_date':            lot.closed_date.isoformat() if lot.closed_date else None,
                'holding_period_days':  holding_days,
                'is_long_term':         is_long_term,
                'term_label':           'Long-term' if is_long_term else 'Short-term',
            })

        total_gain  = sum(r['realized_gain'] or 0 for r in result)
        short_gain  = sum(r['realized_gain'] or 0 for r in result if not r['is_long_term'])
        long_gain   = sum(r['realized_gain'] or 0 for r in result if r['is_long_term'])

        return ok({
            'lots':        result,
            'summary': {
                'total_gain':    round(total_gain,  2),
                'short_term':    round(short_gain,  2),
                'long_term':     round(long_gain,   2),
                'count':         len(result),
            }
        })


@investments_bp.route('/tax-summary', methods=['GET'])
def get_tax_summary():
    """
    Realized gains grouped by tax year and short/long-term.
    Useful for tax planning and Schedule D prep.
    Query param: ?account_id=
    """
    account_id = request.args.get('account_id')

    with db_session() as session:
        q = session.query(InvestmentLot).filter_by(is_closed=True)
        if account_id: q = q.filter_by(account_id=int(account_id))
        lots = q.order_by(InvestmentLot.closed_date).all()

        years = {}
        for lot in lots:
            if not lot.closed_date: continue
            year          = lot.closed_date.year
            holding_days  = lot.holding_period_days or 0
            is_long       = holding_days >= 366
            gain          = lot.realized_gain or 0

            if year not in years:
                years[year] = {'year': year, 'short_term': 0.0, 'long_term': 0.0,
                               'total': 0.0, 'lots': 0}
            key = 'long_term' if is_long else 'short_term'
            years[year][key]  += gain
            years[year]['total'] += gain
            years[year]['lots']  += 1

        result = sorted(years.values(), key=lambda x: x['year'], reverse=True)
        for r in result:
            r['short_term'] = round(r['short_term'], 2)
            r['long_term']  = round(r['long_term'],  2)
            r['total']      = round(r['total'],       2)

        return ok(result)


@investments_bp.route('/asset-classes', methods=['GET', 'PATCH'])
def manage_asset_classes():
    """Get or update the ticker → asset_class mapping stored in app_settings."""
    with db_session() as session:
        if request.method == 'GET':
            s = _get_setting(session, 'inv_asset_classes_json')
            return ok(json.loads(s.value) if s else {})

        body = request.get_json(silent=True) or {}
        existing = _get_setting(session, 'inv_asset_classes_json')
        current  = json.loads(existing.value) if existing else {}
        current.update({k.upper(): v for k, v in body.items() if v is not None})
        # Remove entries explicitly set to null
        current = {k: v for k, v in current.items() if v}
        payload = json.dumps(current)
        if existing:
            existing.value      = payload
            existing.updated_at = datetime.now()
        else:
            session.add(AppSetting(key='inv_asset_classes_json', value=payload))
        session.commit()
        return ok(current)


@investments_bp.route('/expense-ratios', methods=['GET', 'PATCH'])
def manage_expense_ratios():
    """Get or update the user's expense ratios, in PERCENT ({'unit': 'percent', 'ratios': {ticker: 0.03}}).

    A body without `unit: percent` is refused: the old shape could not say which unit it meant, which is how a 0.03%
    fund came to be stored as 3%. Saving a ticker in percent retires its old, unit-less entry.
    """
    with db_session() as session:
        pct_row = _get_setting(session, 'inv_expense_ratios_pct_json')
        legacy_row = _get_setting(session, 'inv_expense_ratios_json')
        pct = json.loads(pct_row.value) if pct_row else {}
        legacy = json.loads(legacy_row.value) if legacy_row else {}
        if request.method == 'GET':
            return ok({'unit': 'percent', 'ratios': pct,
                       'unconfirmed': {t: v for t, v in legacy.items() if t not in pct and 0.01 < float(v) <= 0.03}})

        body = request.get_json(silent=True) or {}
        if body.get('unit') != 'percent' or not isinstance(body.get('ratios'), dict):
            return err('send {"unit": "percent", "ratios": {ticker: percent}} - e.g. 0.03 for a 0.03% fund')
        try:
            update = {str(k).upper(): float(v) for k, v in body['ratios'].items() if v is not None}
        except (TypeError, ValueError):
            return err('each expense ratio is a number, in percent')
        if any(v < 0 or v > 100 for v in update.values()):
            return err('an expense ratio is a percent between 0 and 100')
        pct.update(update)
        for t in update:
            legacy.pop(t, None)
        for key, value in (('inv_expense_ratios_pct_json', pct), ('inv_expense_ratios_json', legacy)):
            row = _get_setting(session, key)
            if row:
                row.value      = json.dumps(value)
                row.updated_at = datetime.now()
            elif value or key == 'inv_expense_ratios_pct_json':
                session.add(AppSetting(key=key, value=json.dumps(value)))
        session.commit()
        return ok({'unit': 'percent', 'ratios': pct})


# ── Analytics ─────────────────────────────────────────────────────────────────


# ── Before You Buy (Phase 0B) ─────────────────────────────────────────────────

byb_bp = Blueprint('byb', __name__)


def _serialize_byb(item) -> dict:
    return {
        'id':                item.id,
        'type':              item.item_type,
        'name':              item.name,
        'category':          item.category,
        'monthly':           item.monthly_cost,
        'replacing': {
            'name':   item.replacing_name,
            'amount': item.replacing_amount,
        } if item.replacing_name else None,
        'decision':          item.decision,
        'dti_before':        item.dti_before,
        'dti_after':         item.dti_after,
        'payoff_impact':     item.payoff_impact,
        'whats_left_before': item.whats_left_before,
        'whats_left_after':  item.whats_left_after,
        'actual_cost':       item.actual_cost,
        'decided_at':        item.decided_at.isoformat() if item.decided_at else None,
        'created_at':        item.created_at.isoformat() if item.created_at else None,
    }


def _log_byb_decision(session, item):
    """
    Historian write-hook for Before You Buy, called from create_byb_item()
    (an immediate wizard-time commit/walkaway) and resolve_byb_item() (a
    'track' item decided later). Only a 'commit' with a real actual_cost —
    i.e. a resolved 'track' item — has anything to compare against the
    original estimate; an immediate decision hasn't produced an "actual"
    yet, so it's logged as a pure categorical event (context only) rather
    than a fabricated 0%-variance data point. 'track' itself is never
    logged here — it isn't a decision yet.
    """
    if item.decision not in ('commit', 'walkaway'):
        return
    expected = actual = None
    if item.decision == 'commit' and item.actual_cost is not None:
        expected = item.monthly_cost
        actual   = item.actual_cost
    log_historian_event(
        session, 'byb_purchase_decision',
        expected_value=expected, actual_value=actual,
        context={'byb_item_id': item.id, 'name': item.name, 'decision': item.decision,
                  'dti_after': item.dti_after, 'payoff_impact': item.payoff_impact},
    )


@byb_bp.route('/memory', methods=['GET'])
def byb_memory():
    """What this user's own decision history says (Pillar 5, §7).

    Read from the historian rather than from `byb_items`, because the historian
    is the proof ledger (B.1) and because it already carries the one figure the
    table does not: the variance between what a purchase was estimated to cost
    and what it actually cost, computed at the moment the comparison existed.

    A reader, and only a reader. These events have been written since Phase H1
    and nothing has ever read them back — the collect-and-ignore loop §7 names.
    """
    from core.solution import decision_memory

    with db_session() as session:
        rows = session.query(HistorianEntry).filter(
            HistorianEntry.event_category == 'byb_purchase_decision'
        ).order_by(HistorianEntry.created_at).all()

        records = []
        for e in rows:
            try:
                cxt = json.loads(e.context_json or '{}')
            except (json.JSONDecodeError, TypeError):
                cxt = {}
            records.append({'decision': cxt.get('decision'),
                            'variance_pct': e.variance_pct})
        return ok(decision_memory(records))


def _byb_offers_said(session):
    """Y1: the person's answers to offers made from the record - {key: {'said', 'at'}}, the latest wins."""
    out = {}
    for x in _setting_json(session, 'byb_offers_said', []) or []:
        if isinstance(x, dict) and x.get('key') and x.get('said') in ('meant', 'cancel', 'dismiss'):
            out[x['key']] = {'said': x['said'], 'at': x.get('at')}
    return out


def _byb_impact(session, monthly=0.0, one_time=0.0, cards=None, budget=None, strategy=None, months_cost=None):
    """Y1/Y6: what a purchase does, as if Before You Buy had been asked first - what is left each month, the
    payoff date, and each savings goal's date - with the assumption in words."""
    from core import byb_offer
    from core.consequence import simulate_payoff
    from core.database import SinkingFund
    today = date.today()
    month_amts = budget_month_amounts(session)
    items = session.query(BudgetItem).filter_by(is_active=True).all()
    income = sum(float(i.amount or 0) for i in items if i.type == 'income')
    outflow = sum((month_amts.get(i.id) or {}).get('month_amount', i.amount or 0) or 0 for i in items if i.type == 'expense')
    left_now = round(income - outflow, 2)
    kw = dict(strategy=strategy, today_key=today.strftime('%Y-%m'), start_month=today.strftime('%Y-%m'))
    payoff_now = payoff_with = None
    if cards:
        try:
            r0 = simulate_payoff(cards, budget, **kw)
            payoff_now = r0['months'] if r0 else None
            if monthly:
                r1 = simulate_payoff(cards, max(0.0, budget - monthly), **kw)
                payoff_with = r1['months'] if r1 else None
            elif months_cost is not None and payoff_now is not None:
                payoff_with = payoff_now + months_cost
        except Exception:                               # noqa: BLE001 - a payoff the engine can't price is left out
            payoff_now = payoff_with = None
    goals = [{'id': f['id'], 'name': f['name'], 'target': f['target_amount'], 'saved': f['current_amount'],
              'contribution': f.get('monthly_needed') or f.get('monthly_contribution') or 0}
             for f in (_serialize_sinking_fund(x) for x in session.query(SinkingFund).filter_by(is_active=True).all())]
    return {'left_now': left_now, 'left_with': round(left_now - monthly, 2) if monthly else None,
            'payoff_months_now': payoff_now, 'payoff_months_with': payoff_with,
            'goals': byb_offer.goal_dates(goals, today, monthly=monthly, one_time=one_time),
            'assumption': byb_offer.assumption(monthly, one_time)}


@byb_bp.route('/offers', methods=['GET'])
def byb_offers():
    """Item 73 Y1 + Y6: purchases that never came through Before You Buy, brought to it from the record - a new
    repeating charge, or a charge that moved the payoff date a month or more - each with what it does. An offer the
    person answered or dismissed is not offered again."""
    from core import byb_offer
    today = date.today()
    window = today - timedelta(days=365)
    with db_session() as session:
        said = _byb_offers_said(session)
        from core import recurring_groups as rg
        rows = session.query(Transaction.merchant, Transaction.account_id, Transaction.date, Transaction.amount,
                             Transaction.id).filter(Transaction.type == 'debit', Transaction.date >= window).all()
        budgeted = [b.name for b in session.query(BudgetItem).filter_by(is_active=True).all()]
        cards, budget, strategy, _undated = _consequence_inputs(session)
        # item 108: a new repeating charge is one payee from one account, offered under its label; it is matched to
        # budget lines and answered by payee (R5), so its key stays the payee's
        names = {a.id: a.name for a in session.query(Account).all()}
        payee_of, per_account = {}, []
        for grp in rg.groups([r for r in rows if r[0]], names):
            payee_of[grp['label']] = grp['payee']
            if grp['payee'] in budgeted:
                budgeted.append(grp['label'])
            per_account += [(tid, d, a, grp['label']) for d, a, tid in grp['rows']]
        offers = []
        for o in byb_offer.new_recurring(per_account, budgeted, today, window):
            o['key'] = f"recurring:{byb_offer._norm(payee_of[o['name']])}"
            if o['key'] in said:
                continue
            offers.append({**o, 'impact': _byb_impact(session, monthly=o['monthly'], cards=cards, budget=budget,
                                                       strategy=strategy)})
        charge = large_charge_lesson(session, cards, budget, strategy) if cards else None
        if charge:
            ch = charge['charge']
            key = f"charge:{ch['date']}:{ch['amount']:.2f}:{(ch['name'] or '').strip().lower()[:40]}"
            if key not in said:
                offers.append({'key': key, 'kind': 'large_charge', 'name': ch['name'], 'amount': ch['amount'],
                               'monthly': 0, 'since': ch['date'], 'months_cost': charge['lesson']['months_cost'],
                               'impact': _byb_impact(session, one_time=ch['amount'], cards=cards, budget=budget,
                                                     strategy=strategy, months_cost=charge['lesson']['months_cost'])})
        answered = [{'key': k, **v} for k, v in said.items() if v['said'] != 'dismiss']
        return ok({'offers': offers, 'answered': answered[-20:]})


@byb_bp.route('/offers/answer', methods=['POST'])
@require_json
def byb_offer_answer():
    """Y1: the person's word on a purchase brought from the record - 'meant' (I meant to), 'cancel' (I'll cancel it)
    or 'dismiss'. Kept as their statement; the offer is not made again. Nothing else changes: it is not a budget
    edit, and it is not read as anything about the person."""
    body = request.json or {}
    key, said = str(body.get('key') or '')[:120], body.get('said')
    if not key or said not in ('meant', 'cancel', 'dismiss'):
        return err("a key and said = 'meant', 'cancel' or 'dismiss' are needed")
    with db_session() as session:
        rows = _setting_json(session, 'byb_offers_said', []) or []
        rows.append({'key': key, 'said': said, 'at': datetime.now().isoformat(timespec='seconds')})
        _set_setting(session, 'byb_offers_said', json.dumps(rows[-500:]))
        session.commit()
        return ok({'key': key, 'said': said})


# ── Item 73 stage 2 (BYB_AGENT.md Y2): trial and return dates, read from a receipt ───────────────────────────
def _receipt_dates(session):
    return [x for x in (_setting_json(session, 'receipt_dates', []) or []) if isinstance(x, dict)]


@byb_bp.route('/receipt/read', methods=['POST'])
def byb_receipt_read():
    """Y2: a pasted or dropped confirmation (PDF, saved email, text), read on this computer for the dates it
    states. Nothing is saved and the file is not kept; the person picks what to keep."""
    from core import itinerary, receipt_dates
    try:
        if 'file' in request.files:
            up = request.files['file']
            text = itinerary.text_from_upload(up.filename, up.read())
        else:
            text = str((request.get_json(silent=True) or {}).get('text') or '')
            if not text.strip():
                return err('Paste the receipt, or choose its PDF or saved email.')
            if len(text) > itinerary.MAX_BYTES:
                return err('That is far longer than a receipt.')
    except ValueError as e:
        return err(str(e))
    except Exception:                                  # noqa: BLE001 - never the document's text in a log
        logging.getLogger('groundwork').info('receipt file could not be read')
        return err('Could not read that file.')
    return ok(receipt_dates.read(text))


@byb_bp.route('/receipt-dates', methods=['GET'])
def byb_receipt_dates_list():
    """Y2: the dates the person kept, soonest first, with whether they marked each handled."""
    with db_session() as session:
        rows = sorted(_receipt_dates(session), key=lambda x: x.get('date') or '')
        return ok({'dates': rows})


@byb_bp.route('/receipt-dates', methods=['POST'])
@require_json
def byb_receipt_dates_save():
    """Y2: keep the dates the person ticked. Each is checked again - a kind Groundwork knows, a full date - before it
    is kept; the receipt itself never is."""
    from core.receipt_dates import KINDS
    body = request.json or {}
    merchant = str(body.get('merchant') or '').strip()[:80]
    picked = body.get('dates') or []
    with db_session() as session:
        rows = _receipt_dates(session)
        added = []
        for d in picked[:20]:
            if not isinstance(d, dict) or d.get('kind') not in KINDS:
                continue
            try:
                when = date.fromisoformat(str(d.get('date'))[:10]).isoformat()
            except ValueError:
                continue
            price = d.get('price_after')
            row = {'id': int(datetime.now().timestamp() * 1000) + len(added), 'merchant': merchant or 'A purchase',
                   'kind': d['kind'], 'date': when,
                   'price_after': round(float(price), 2) if isinstance(price, (int, float)) else None,
                   'every': d.get('every') if d.get('every') in ('month', 'year', 'week') else None,
                   'phrase': str(d.get('phrase') or '')[:160], 'added_at': datetime.now().isoformat(timespec='seconds'),
                   'done': None}
            rows.append(row)
            added.append(row)
        if not added:
            return err('Nothing to keep - pick at least one date.')
        _set_setting(session, 'receipt_dates', json.dumps(rows[-200:]))
        session.commit()
        return ok({'added': added})


@byb_bp.route('/receipt-dates/<int:row_id>/done', methods=['POST'])
def byb_receipt_date_done(row_id):
    """Y2: the person says they have handled it (cancelled, returned, or kept it). It leaves the dashboard."""
    with db_session() as session:
        rows = _receipt_dates(session)
        hit = next((r for r in rows if r.get('id') == row_id), None)
        if not hit:
            return err('Not one of your saved dates.', 404)
        hit['done'] = datetime.now().isoformat(timespec='seconds')
        _set_setting(session, 'receipt_dates', json.dumps(rows))
        session.commit()
        return ok(hit)


# ── Item 73 stage 3 (BYB_AGENT.md Y3 + Y4): the full cost, and a financing offer read ──────────────────────
def _insurance_reading(session):
    """Y3: the latest bill reading the person confirmed for an insurance bill - {name, amount, date} or None."""
    rows = (session.query(BillReading, BudgetItem).join(BudgetItem, BillReading.budget_item_id == BudgetItem.id)
            .filter(BillReading.amount.isnot(None)).order_by(BillReading.read_at.desc()).all())
    for r, b in rows:
        if re.search(r'insur|geico|state farm|progressive|allstate|liberty mutual|nationwide|usaa',
                     f'{b.name} {b.category or ""}', re.I):
            return {'name': b.name, 'amount': float(r.amount), 'date': r.read_at.date().isoformat()}
    return None


@byb_bp.route('/full-cost', methods=['POST'])
@require_json
def byb_full_cost():
    """Y3: a car's, phone's or yearly charge's monthly cost from the person's figures, their confirmed insurance bill
    reading and EIA's national gas price (a fixed public query - nothing about the person is sent). A part with no
    source is left out and named."""
    from core import purchase_cost
    body = request.json or {}
    gas = None
    if (body.get('kind') == 'car'):
        try:
            import gas_price
            gas = gas_price.get_national_gas_price(_get_eia_api_key())
        except Exception:                               # noqa: BLE001 - no published price: fuel is left out, said
            gas = None
    with db_session() as session:
        res = purchase_cost.full_cost(body.get('kind'), body.get('inputs') or {}, _insurance_reading(session), gas)
    if res is None:
        return err("kind must be 'car', 'phone' or 'annual'")
    return ok(res)


@byb_bp.route('/financing', methods=['POST'])
@require_json
def byb_financing():
    """Y4: a pasted financing offer read for its figures (each must be in the text) and laid beside paying cash and
    the person's own highest-rate debt. Nothing is saved."""
    from core import purchase_cost
    text = str((request.json or {}).get('text') or '')[:20000]
    if not text.strip():
        return err('Paste the financing offer.')
    offer = purchase_cost.read_offer(text)
    with db_session() as session:
        debts = [{'name': d.name, 'balance': float(d.current_balance or 0), 'rate': float(d.interest_rate or 0)}
                 for d in session.query(DebtAccount).filter_by(is_active=True).all()]
    return ok({'offer': offer, 'compare': purchase_cost.compare(offer, debts)})


@byb_bp.route('', methods=['GET'])
def list_byb_items():
    """Return all active BYB sandbox items."""
    with db_session() as session:
        items = session.query(BYBItem).order_by(BYBItem.created_at).all()
        return ok([_serialize_byb(i) for i in items])


@byb_bp.route('', methods=['POST'])
@require_json
def create_byb_item():
    """
    Add an item to the BYB sandbox. The wizard always evaluates a decision
    (commit/track/walkaway) before saving — see _bybCommit in app.js — so
    this accepts and stores that plus the simulation output (dti_before/
    after, payoff_impact, whats_left_before/after) rather than dropping it,
    which is what made every saved item render as "walked away" regardless
    of the real choice (see BYBItem's docstring).
    """
    body = request.json
    with db_session() as session:
        # The wizard (_bybCommit) sends replacing_name as a flat string, not
        # the nested {name, amount} shape this route originally expected —
        # support both rather than silently losing it either way.
        replacing = body.get('replacing') or {}
        decision  = body.get('decision')
        if decision not in (None, 'commit', 'track', 'walkaway'):
            return err("decision must be 'commit', 'track', or 'walkaway'")
        if not (body.get('name') or '').strip():
            return err('name is required')
        item = BYBItem(
            item_type        = body.get('type', 'other'),
            name             = body['name'],
            category         = body.get('category', 'Other'),
            monthly_cost     = float(body.get('monthly', 0)),
            replacing_name   = body.get('replacing_name') or replacing.get('name'),
            replacing_amount = float(replacing['amount']) if replacing.get('amount') else None,
            replacing_id     = body.get('replacing_id'),
            decision         = decision,
            dti_before       = body.get('dti_before'),
            dti_after        = body.get('dti_after'),
            payoff_impact    = body.get('payoff_impact'),
            whats_left_before = body.get('whats_left_before'),
            whats_left_after  = body.get('whats_left_after'),
            decided_at       = datetime.now() if decision in ('commit', 'walkaway') else None,
        )
        session.add(item)
        session.flush()
        _log_byb_decision(session, item)
        session.commit()
        return ok(_serialize_byb(item))


@byb_bp.route('/<int:item_id>/resolve', methods=['PATCH'])
@require_json
def resolve_byb_item(item_id):
    """
    Resolve a 'track' item once the user actually decides — the second
    half of the Historian-facing purpose of this table (see BYBItem's
    docstring): a real actual_cost captured here, compared against the
    original monthly_cost estimate, is genuine estimate-vs-actual signal
    that an immediate wizard-time decision never produces.
    Body: { decision: 'commit'|'walkaway', actual_cost: float (optional) }
    """
    body     = request.json
    decision = body.get('decision')
    if decision not in ('commit', 'walkaway'):
        return err("decision must be 'commit' or 'walkaway'")
    with db_session() as session:
        item = session.get(BYBItem, item_id)
        if not item:
            return err('Item not found', 404)
        item.decision    = decision
        item.actual_cost = float(body['actual_cost']) if body.get('actual_cost') is not None else None
        item.decided_at  = datetime.now()
        _log_byb_decision(session, item)
        session.commit()
        return ok(_serialize_byb(item))


@byb_bp.route('/<int:item_id>', methods=['DELETE'])
def delete_byb_item(item_id):
    """Remove an item from the BYB sandbox."""
    with db_session() as session:
        item = session.get(BYBItem, item_id)
        if not item:
            return err('Item not found', 404)
        session.delete(item)
        session.commit()
        return ok({'deleted': item_id})


@byb_bp.route('', methods=['DELETE'])
def clear_byb_items():
    """Clear all BYB sandbox items (user clicks Not Buying It)."""
    with db_session() as session:
        session.query(BYBItem).delete()
        session.commit()
        return ok({'cleared': True})


# ── Trip Planner (Phase 10) ───────────────────────────────────────────────────

trip_bp = Blueprint('trip', __name__)


def _extract_trip_region(dest: str):
    """'Denver, CO' -> 'CO'. Best-effort region tag for trip_history —
    returns the raw string when there's no comma-separated state code
    (e.g. a destination typed without one), never raises."""
    if not dest or not dest.strip():
        return None
    parts = dest.rsplit(',', 1)
    return parts[-1].strip() if len(parts) == 2 else dest.strip()


def get_improved_trip_estimate(session, region: str, base_estimate: float) -> dict:
    """
    Phase H2 Feature 3 (adaptive learning — trip spending forecast). Adjusts
    a base trip estimate using real regional variance from trip_history
    (Phase H1). Returns the base estimate unchanged, with confidence='none',
    when there's no real data for the region yet — an unadjusted estimate is
    correct output here, not a fallback to hide.
    """
    variance = get_trip_variance_by_region(session, region)
    if variance['trip_count'] == 0 or variance['variance_pct'] is None:
        return {'estimate': base_estimate, 'adjustment_pct': 0, 'confidence': 'none', 'trip_count': 0}
    adjusted = round(base_estimate * (1 + variance['variance_pct'] / 100), 2)
    confidence = 'low' if variance['trip_count'] < 2 else 'medium' if variance['trip_count'] < 4 else 'high'
    return {
        'estimate': adjusted, 'adjustment_pct': variance['variance_pct'],
        'confidence': confidence, 'trip_count': variance['trip_count'],
    }


@trip_bp.route('/forecast', methods=['GET'])
def trip_forecast():
    # Normalize the same way the two write hooks do (save_trip_budget,
    # save_trip_learned_actual) — callers may pass a raw "City, ST" destination
    # string (the trip planner UI does) or an already-extracted region code;
    # trip_history always stores the extracted form, so the lookup must match it.
    region = _extract_trip_region(request.args.get('region', ''))
    try:
        base_estimate = float(request.args.get('base_estimate', 0))
    except (TypeError, ValueError):
        return err('base_estimate must be a number')
    with db_session() as session:
        return ok(get_improved_trip_estimate(session, region, base_estimate))


@trip_bp.route('/learned-actual', methods=['POST'])
@require_json
def save_trip_learned_actual():
    """
    Write hook 2/2 for trip_history (deferred from Phase H1 to here, per
    HISTORIAN_GUIDE.md — this is the code that actually knows what "actual"
    means). Fires when the user applies a past trip's real spending
    (_applyTripLearnedBasis in app.js) to the trip they're currently
    planning. Region is approximated from the CURRENT trip's destination
    field, since learning happens in service of planning that trip — the
    common case (the blueprint's own example: learning from past Colorado
    trips while planning a new one) is learning from a trip to the same
    region, but this is a best-effort tag, not a verified fact.
    """
    body = request.json
    region = _extract_trip_region(body.get('region_hint', ''))
    hotel_per_night = body.get('hotel_per_night')
    dining_per_person_day = body.get('dining_per_person_day')
    activities_per_person_day = body.get('activities_per_person_day')
    actual_total = body.get('actual_total')

    with db_session() as session:
        row = TripHistory(
            trip_label=(body.get('label') or '')[:120],
            region=region,
            actual_total=actual_total,
            actual_by_category=json.dumps({
                'hotel_per_night': hotel_per_night,
                'dining_per_person_day': dining_per_person_day,
                'activities_per_person_day': activities_per_person_day,
            }),
        )
        session.add(row)
        session.commit()
        return ok({'saved': True, 'id': row.id})


@trip_bp.route('/oil-check', methods=['GET'])
def check_oil_change():
    """
    Check the ledger for the last oil change transaction.
    Looks for known oil change merchants in transaction descriptions.
    Returns last date, description, and miles_ago estimate if mileage tracked.
    """
    OIL_PATTERNS = [
        'jiffy lube', 'valvoline', 'firestone', 'goodyear', 'midas',
        'pep boys', 'oil change', 'quick lube', 'take 5', 'express oil',
        "jiffy", 'meineke', 'monro', 'ntb ', 'sears auto',
    ]
    with db_session() as session:
        txns = session.query(Transaction)\
            .order_by(Transaction.date.desc())\
            .limit(500).all()

        for t in txns:
            desc = (t.description or '').lower()
            if any(p in desc for p in OIL_PATTERNS):
                from datetime import date as date_cls
                days_ago = (date_cls.today() - t.date).days if t.date else None
                return ok({
                    'found':       True,
                    'date':        t.date.isoformat() if t.date else None,
                    'description': t.description,
                    'amount':      t.amount,
                    'days_ago':    days_ago,
                    'overdue':     days_ago > 90 if days_ago else False,
                })

        return ok({'found': False})


@trip_bp.route('/gas-price', methods=['GET'])
def trip_gas_price():
    """
    Phase 5A — the real national-average gas price for trip fuel estimates,
    replacing the hardcoded $3.40 placeholder. Zero user-data egress: this
    is a fixed query for the national average, nothing about the user's
    trip or finances is ever sent. Degrades honestly (live:false) rather
    than breaking when no EIA key is configured yet.
    """
    import gas_price
    result = gas_price.get_national_gas_price(_get_eia_api_key())
    return ok(result)


@trip_bp.route('/airfare-markets', methods=['GET'])
def trip_airfare_markets():
    """
    The city markets DOT lists, for the trip planner's From / To pickers
    (core/airfare.py, gw 2.0/DOT_AIRFARE.md). Read from the table on disk;
    nothing is fetched here.
    """
    from core import airfare
    return ok(airfare.markets())


@trip_bp.route('/airfare', methods=['GET'])
def trip_airfare():
    """
    The average one-way fare DOT reports for a route, narrowed to the airport
    pair when both airports are given and DOT lists it. A lookup in the table
    on disk: the user's route never leaves the computer.
    """
    from core import airfare
    return ok(airfare.lookup(request.args.get('from', ''), request.args.get('to', ''),
                             request.args.get('from_airport', ''), request.args.get('to_airport', '')))


@trip_bp.route('/flights-window', methods=['POST'])
@require_json
def trip_flights_window():
    """
    Open the Google Flights search for the trip's airports, dates and
    travelers in Groundwork's own window (item 42, gw 2.0/FLIGHTS_WINDOW.md):
    the bank window's separate, private process (bank_window.py), given only
    the address. The address is built here from the form's fields, so the
    page can never ask for any other site to be opened. mode 'browser' is the
    escape hatch: the same search in the user's own browser.
    """
    import bank_window
    from core import airfare
    body = request.json
    url = airfare.google_flights_url(body.get('origin'), body.get('dest'), body.get('depart'),
                                     body.get('return') or None, body.get('travelers', 1))
    if not url:
        return err('Enter both 3-letter airport codes and your departure date first.', 400)
    if body.get('mode') == 'browser':
        return ok({'result': bank_window.open_in_browser(url)})
    import flights_window
    key = ('flights', 0)
    bank_window.close_bank_window(key)        # a new search replaces the one on screen
    flights_window.clear()                    # and its fare with it
    result = bank_window.open_bank_window(key, url)
    if result == 'opened' and bank_window.process(key):
        flights_window.watch(bank_window.process(key))     # item 44: the fare the user picks, if they pick one
    return ok({'result': result})


@trip_bp.route('/flights-window/fare', methods=['GET'])
def trip_flights_window_fare():
    """
    Item 44 (FLIGHT_FARE_READ.md R3/R4): the price on the Google Flights
    Continue button the user last clicked, or none. Shown to the user to
    confirm; nothing is written here.
    """
    import flights_window
    return ok(flights_window.latest())


@trip_bp.route('/flights-window/fare/clear', methods=['POST'])
def trip_flights_window_fare_clear():
    """The user used the fare or turned it down: forget it."""
    import flights_window
    flights_window.clear()
    return ok({'cleared': True})


# ── Item 59 (TRIP_REAL_PRICES.md): GSA's per-diem rates, and Google Hotels in Groundwork's window ──────────────
def _label_old_ai_prices(saved):
    """Item 59 P1: a budget saved by an earlier version with the model's figures keeps them, said for what they are."""
    if isinstance(saved, dict) and saved.get('aiResult') is not None:
        saved = {**saved, 'aiResult_label': 'estimated by the AI model in an earlier version, not a price'}
    return saved


@trip_bp.route('/itinerary/read', methods=['POST'])
def trip_itinerary_read():
    """Item 60 (TRIP_ITINERARY_IMPORT.md) I1/I5/I6: a pasted itinerary, a PDF or a saved email (.eml), read on this
    computer. Confirmation numbers come out of the text first. A known sender's document is broken into its parts
    here, without a model; anything else comes back for the local model to transcribe (then /itinerary/check).
    Nothing is written and the file is not kept."""
    from core import itinerary as it
    try:
        if 'file' in request.files:
            up = request.files['file']
            text = it.text_from_upload(up.filename, up.read())
        else:
            text = str((request.get_json(silent=True) or {}).get('text') or '')
            if not text.strip():
                return err('Paste the itinerary, or choose its PDF or saved email.')
            if len(text) > it.MAX_BYTES:
                return err('That is far longer than an itinerary.')
    except ValueError as e:
        return err(str(e))
    except Exception:                                  # noqa: BLE001 - never the document's text in a log
        logging.getLogger('groundwork').info('itinerary file could not be read')
        return err('Could not read that file.')
    text, codes = it.take_confirmations(text)
    known = it.read_known(text)
    if known:
        return ok({**it.finish(known, text, codes), 'needs_model': False})
    return ok({'needs_model': True, 'text': text, 'model_text': it.text_for_model(text), 'confirmations': codes,
               'parts': [], 'warnings': []})


@trip_bp.route('/itinerary/check', methods=['POST'])
@require_json
def trip_itinerary_check():
    """Item 60 I2/I3: the local model's transcription of an itinerary, every figure checked against the document.
    A figure the document doesn't contain is dropped and said; an answer that isn't the asked shape is refused whole
    (fail closed). Nothing is written."""
    from core import itinerary as it
    body = request.json or {}
    text = str(body.get('text') or '')
    if not text.strip():
        return err('The itinerary text is needed to check the figures against.')
    text, codes = it.take_confirmations(text)
    codes += [{'kind': c.get('kind') if c.get('kind') in it.KINDS else None, 'code': str(c.get('code') or '')[:25]}
              for c in (body.get('confirmations') or [])[:10] if isinstance(c, dict) and c.get('code')]
    out = it.from_model(body.get('raw'), text, codes)
    if out is None:
        return err("The reader's answer wasn't usable - nothing was taken from it.")
    return ok({**out, 'needs_model': False})


@trip_bp.route('/per-diem', methods=['GET'])
def trip_per_diem():
    """P2: GSA's lodging and meals rate for a destination on a date - the federal travel rate, never a quote. Looked
    up in the shipped table on this computer; nothing about the trip leaves it."""
    from core import per_diem
    return ok(per_diem.lookup(request.args.get('dest', ''), request.args.get('date', '')))


@trip_bp.route('/per-diem-refresh', methods=['POST'])
def trip_per_diem_refresh():
    """P2: GSA's file for the current fiscal year, when the app's table is older - at most one look a month. The
    request is GSA's whole public file, carrying nothing about any trip. Any failure keeps the current table."""
    from core import per_diem
    return ok(per_diem.refresh())


@trip_bp.route('/hotels-window', methods=['POST'])
@require_json
def trip_hotels_window():
    """P3: Google Hotels for the trip's destination, dates and guests, in Groundwork's own window (the bank window's
    separate, private process, given only the address, as Google Flights is - item 42). The address is built here,
    so the page can never ask for another site. mode 'browser': the same search in the person's own browser."""
    import bank_window
    from core import per_diem
    body = request.json or {}
    url = per_diem.google_hotels_url(body.get('dest'), body.get('checkin'), body.get('checkout'), body.get('guests', 1))
    if not url:
        return err('Enter the destination first.', 400)
    if body.get('mode') == 'browser':
        return ok({'result': bank_window.open_in_browser(url)})
    import hotels_window
    key = ('hotels', 0)
    bank_window.close_bank_window(key)        # a new search replaces the one on screen
    hotels_window.clear()                     # and its price with it
    result = bank_window.open_bank_window(key, url)
    if result == 'opened' and bank_window.process(key):
        hotels_window.watch(bank_window.process(key))     # the stay total the person clicks, if they click one
    return ok({'result': result})


@trip_bp.route('/hotels-window/price', methods=['GET'])
def trip_hotels_window_price():
    """P3's optional half: the stay's total with taxes and fees from the Google Hotels row the person last clicked,
    and its nights - or none. Shown to the person to confirm; nothing is written here."""
    import hotels_window
    return ok(hotels_window.latest())


@trip_bp.route('/hotels-window/price/clear', methods=['POST'])
def trip_hotels_window_price_clear():
    """The person used the price or turned it down: forget it."""
    import hotels_window
    hotels_window.clear()
    return ok({'cleared': True})


@trip_bp.route('/airfare-refresh', methods=['POST'])
def trip_airfare_refresh():
    """
    Download DOT's newest quarter when it is newer than the table the app has,
    at most one look a week. The request is the whole quarter's table, so it
    carries nothing about the user's trip. Any failure keeps the current table.
    """
    from core import airfare
    return ok(airfare.refresh())


@trip_bp.route('/distance', methods=['GET'])
def trip_distance_estimate():
    """
    Phase 5E — real driving-distance estimate for trip fuel-cost math,
    replacing the hardcoded 400-miles-each-way placeholder. Geocodes via
    OpenStreetMap Nominatim (free, keyless) then great-circle x road-factor.
    Only the origin/destination place names are sent — no other trip or
    financial data.
    """
    import trip_distance
    origin      = (request.args.get('origin') or '').strip()
    destination = (request.args.get('destination') or '').strip()
    if not destination:
        return err('destination required')
    return ok(trip_distance.get_drive_distance(origin, destination))


def _trip_credit_cards(session):
    """Item 49 R1: the active debts a trip can be put on - type credit - with what the record holds about each, in the
    same order the payoff engine sees them (`_consequence_inputs`)."""
    from core.trip_card import available_credit
    out = []
    for i, d in enumerate(session.query(DebtAccount).filter_by(is_active=True).all()):
        if (d.debt_type or 'credit') != 'credit':
            continue
        bal = d.current_balance if d.current_balance is not None else (d.begin_balance or 0)
        out.append({'id': d.id, 'index': i, 'name': d.name or 'Card', 'balance': round(float(bal or 0), 2),
                    'apr': float(d.interest_rate or 0), 'minimum': float(d.minimum_payment or 0),
                    'limit': float(d.credit_limit) if d.credit_limit is not None else None,
                    'available': available_credit(bal, d.credit_limit)})
    return out


@trip_bp.route('/cards', methods=['GET'])
def trip_cards():
    """Item 49 (TRIP_ON_CREDIT.md R1): the credit cards a trip could go on. Available credit only where a limit is
    entered; otherwise None, and the page says the limit isn't entered."""
    with db_session() as session:
        return ok({'cards': _trip_credit_cards(session)})


@trip_bp.route('/card-plan', methods=['GET'])
def trip_card_plan():
    """Item 49 R2-R4: what putting the trip on one card would take and cost - whether it fits, 3/6/12-month payoffs at
    the card's APR, the in-full-this-statement row, and the whole plan at current payments - each with its assumption.
    Computed here, in core/trip_card.py; nothing is saved."""
    from core.trip_card import plan
    try:
        amount = float(request.args.get('amount', ''))
        card_id = int(request.args.get('card_id', ''))
    except (TypeError, ValueError):
        return err('amount and card_id required')
    if not (0 < amount <= 1_000_000):
        return err('amount out of range')
    with db_session() as session:
        card = next((c for c in _trip_credit_cards(session) if c['id'] == card_id), None)
        if not card:
            return err('Not one of your credit cards', 404)
        cards, budget, strategy, _undated = _consequence_inputs(session)
        return ok(plan(amount, card, cards, budget, strategy, card['index']))


# ── Item 50 (TRIP_BOOKED.md, Rob 2026-10-08, B1-B8): "I booked it" ─────────────
# A booking is a planned record (B2): nothing here writes a transaction, a debt
# ledger entry, a budget total or a balance. The real charge is counted once, when
# it is imported; these routes only propose it (B3) and link it on the user's yes.
# The confirmation number is the user's own typing (B1), served only to its own
# record and never logged.

def _booking_json(b):
    from core.trip_booking import trip_cost
    d = {'id': b.id, 'trip_label': b.trip_label, 'airline': b.airline, 'amount': b.amount,
         'booked_on': b.booked_on.isoformat(), 'paid_with_kind': b.paid_with_kind,
         'debt_account_id': b.debt_account_id, 'account_id': b.account_id, 'confirmation': b.confirmation or '',
         'status': b.status, 'refund_expected': bool(b.refund_expected), 'charged_amount': b.charged_amount,
         'matched': bool(b.matched_transaction_id or b.matched_debt_entry_id),
         'refunded': bool(b.refund_transaction_id or b.refund_debt_entry_id)}
    d['trip_cost'] = trip_cost({**d, 'booked_on': b.booked_on})
    return d


def _booking_rows(session, b, refund=False):
    """Every row on the card or account the booking was paid with, inside the date window, as {kind, id, amount,
    date, text} - charges for a booking, money back for a refund. Already-matched rows come back flagged."""
    from core.trip_booking import window
    lo, hi = window(b.booked_on)
    rows = []
    account_ids = []
    if b.paid_with_kind == 'account' and b.account_id:
        account_ids.append(b.account_id)
    if b.paid_with_kind == 'card' and b.debt_account_id:
        debt = session.get(DebtAccount, b.debt_account_id)
        if debt and debt.linked_account_id:
            account_ids.append(debt.linked_account_id)
        etype = 'payment' if refund else 'charge'
        for e in session.query(DebtLedgerEntry).filter(
                DebtLedgerEntry.debt_account_id == b.debt_account_id, DebtLedgerEntry.entry_type == etype,
                DebtLedgerEntry.entry_date >= lo, DebtLedgerEntry.entry_date <= hi).all():
            rows.append({'kind': 'ledger', 'id': e.id, 'amount': float(e.amount), 'date': e.entry_date,
                         'text': f'{e.merchant or ""} {e.description or ""}'})
    if account_ids:
        ttype = 'credit' if refund else 'debit'
        for x in session.query(Transaction).filter(
                Transaction.account_id.in_(account_ids), Transaction.type == ttype,
                Transaction.date >= lo, Transaction.date <= hi).all():
            rows.append({'kind': 'transaction', 'id': x.id, 'amount': float(x.amount), 'date': x.date,
                         'text': f'{x.merchant or ""} {x.description or ""}'})
    taken_t, taken_l = set(), set()
    for o in session.query(TripBooking).filter(TripBooking.id != b.id).all():
        taken_t.update(i for i in (o.matched_transaction_id, o.refund_transaction_id) if i)
        taken_l.update(i for i in (o.matched_debt_entry_id, o.refund_debt_entry_id) if i)
    for r in rows:
        r['taken'] = (r['id'] in taken_t) if r['kind'] == 'transaction' else (r['id'] in taken_l)
    return rows


@trip_bp.route('/booking-accounts', methods=['GET'])
def trip_booking_accounts():
    """B4: what a booking can be paid with - the user's credit cards and checking accounts (airlines take debit cards).
    'Other' is always offered by the page."""
    with db_session() as session:
        cards = [{'id': c['id'], 'name': c['name']} for c in _trip_credit_cards(session)]
        accounts = [{'id': a.id, 'name': a.name} for a in session.query(Account).filter_by(is_active=True).all()
                    if (a.type or 'checking').lower() == 'checking']
        return ok({'cards': cards, 'accounts': accounts})


@trip_bp.route('/bookings', methods=['GET'])
def trip_bookings_list():
    """The bookings for one trip (or all), each with what the trip's flight line shows for it (B7)."""
    trip = (request.args.get('trip') or '').strip()
    with db_session() as session:
        q = session.query(TripBooking)
        if trip:
            q = q.filter(TripBooking.trip_label == trip)
        return ok({'bookings': [_booking_json(b) for b in q.order_by(TripBooking.id).all()]})


@trip_bp.route('/bookings', methods=['POST'])
@require_json
def trip_bookings_create():
    """B2: record a booking the user says they made. A planned record - no transaction, no balance."""
    body = request.json
    airline = (body.get('airline') or '').strip()[:80]
    try:
        amount = round(float(body.get('amount')), 2)
        booked_on = date.fromisoformat(body.get('booked_on') or date.today().isoformat())
    except (TypeError, ValueError):
        return err('amount and booked_on (YYYY-MM-DD) required')
    if not airline or not (0 < amount <= 1_000_000):
        return err('An airline and an amount over $0 are needed.')
    kind = body.get('paid_with_kind') or 'other'
    if kind not in ('card', 'account', 'other'):
        return err("paid_with_kind must be 'card', 'account' or 'other'")
    conf = (body.get('confirmation') or '').strip()[:40] or None
    with db_session() as session:
        b = TripBooking(trip_label=(body.get('trip_label') or '').strip()[:160], airline=airline, amount=amount,
                        booked_on=booked_on, paid_with_kind=kind, confirmation=conf, status='booked')
        if kind == 'card':
            ids = {c['id'] for c in _trip_credit_cards(session)}
            if body.get('debt_account_id') not in ids:
                return err('Not one of your credit cards.', 400)
            b.debt_account_id = body['debt_account_id']
        elif kind == 'account':
            acct = session.get(Account, body.get('account_id') or 0)
            if not acct:
                return err('Not one of your accounts.', 400)
            b.account_id = acct.id
        session.add(b)
        session.commit()
        return ok(_booking_json(b))


@trip_bp.route('/bookings/<int:booking_id>', methods=['PUT'])
@require_json
def trip_bookings_update(booking_id):
    """B6: correct a booking, or mark it cancelled (kept, never deleted), with or without a refund expected."""
    body = request.json
    with db_session() as session:
        b = session.get(TripBooking, booking_id)
        if not b:
            return err('Not found', 404)
        if 'airline' in body and (body['airline'] or '').strip():
            b.airline = body['airline'].strip()[:80]
        if 'amount' in body:
            try:
                b.amount = round(float(body['amount']), 2)
            except (TypeError, ValueError):
                return err('amount must be a number')
        if 'confirmation' in body:
            b.confirmation = (body['confirmation'] or '').strip()[:40] or None
        if body.get('status') == 'cancelled' and b.status in ('booked', 'charged'):
            b.status = 'cancelled'
            b.refund_expected = bool(body.get('refund_expected'))
        b.updated_at = datetime.now()
        session.commit()
        return ok(_booking_json(b))


@trip_bp.route('/bookings/<int:booking_id>/candidates', methods=['GET'])
def trip_bookings_candidates(booking_id):
    """B3: the imported charges that may be this booking (or, B6, the refund of a cancelled one). Nothing is linked."""
    from core.trip_booking import candidates
    with db_session() as session:
        b = session.get(TripBooking, booking_id)
        if not b:
            return err('Not found', 404)
        refund = b.status == 'cancelled' and b.refund_expected
        if b.status not in ('booked',) and not refund:
            return ok({'candidates': [], 'for': b.status})
        rows = _booking_rows(session, b, refund=refund)
        bk = {'amount': b.amount, 'booked_on': b.booked_on, 'airline': b.airline}
        found = candidates(bk, [r for r in rows if not r['taken']])
        return ok({'for': 'refund' if refund else 'charge',
                   'candidates': [{**r, 'date': r['date'].isoformat()} for r in found]})


@trip_bp.route('/bookings/<int:booking_id>/match', methods=['POST'])
@require_json
def trip_bookings_match(booking_id):
    """B3: the user said yes. Link the booking to the row - one the rule proposed, or (by hand) any unmatched row on the
    same card or account in the window. The charge stays counted where it was imported; the booking just points at it."""
    from core.trip_booking import candidates
    body = request.json
    kind, row_id, by_hand = body.get('kind'), body.get('id'), bool(body.get('by_hand'))
    with db_session() as session:
        b = session.get(TripBooking, booking_id)
        if not b:
            return err('Not found', 404)
        refund = b.status == 'cancelled' and b.refund_expected
        if b.status != 'booked' and not refund:
            return err('This booking is not waiting for a charge.', 400)
        rows = [r for r in _booking_rows(session, b, refund=refund) if not r['taken']]
        pool = rows if by_hand else candidates({'amount': b.amount, 'booked_on': b.booked_on, 'airline': b.airline}, rows)
        row = next((r for r in pool if r['kind'] == kind and r['id'] == row_id), None)
        if not row:
            return err('That row is not one this booking can be matched to.', 400)
        if refund:
            if kind == 'transaction':
                b.refund_transaction_id = row_id
            else:
                b.refund_debt_entry_id = row_id
            b.status = 'refunded'
        else:
            if kind == 'transaction':
                b.matched_transaction_id = row_id
            else:
                b.matched_debt_entry_id = row_id
            b.charged_amount = row['amount']
            b.status = 'charged'
        b.updated_at = datetime.now()
        session.commit()
        return ok(_booking_json(b))


@trip_bp.route('/budget', methods=['GET'])
def get_trip_budget():
    """Return any saved trip budget from app_settings."""
    with db_session() as session:
        row = _get_setting(session, 'trip_budget')
        if row and row.value:
            try:
                return ok(_label_old_ai_prices(json.loads(row.value)))
            except Exception:
                logging.getLogger('groundwork').warning(
                    'trip_budget setting is corrupt JSON — returning None',
                    exc_info=True)
        return ok(None)


@trip_bp.route('/budget', methods=['POST'])
@require_json
def save_trip_budget():
    """Save a trip budget to app_settings for tracking."""
    body = request.json
    with db_session() as session:
        row = _get_setting(session, 'trip_budget')
        body = {k: v for k, v in (body or {}).items() if k != 'aiResult'}   # item 59 P1: never the model's prices
        val = json.dumps(body)
        if row:
            row.value = val
        else:
            session.add(AppSetting(key='trip_budget', value=val))

        # Write hook 1/2 for trip_history (Phase H2 Feature 3, deferred from
        # Phase H1). Matched on (region, start_date, end_date) so re-saves
        # during the same planning session (e.g. the AI-refine step re-POSTs)
        # update the estimate rather than accumulating duplicate rows.
        try:
            region = _extract_trip_region(body.get('dest', ''))
            start_date = date.fromisoformat(body['depart']) if body.get('depart') else None
            end_date = date.fromisoformat(body['ret']) if body.get('ret') else None
            if region and start_date and end_date and body.get('total') is not None:
                trip_row = session.query(TripHistory).filter_by(
                    region=region, start_date=start_date, end_date=end_date
                ).first()
                if not trip_row:
                    trip_row = TripHistory(region=region, start_date=start_date, end_date=end_date)
                    session.add(trip_row)
                trip_row.trip_label = (body.get('dest') or '')[:120]
                trip_row.estimated_total = float(body['total'])
                trip_row.estimated_by_category = json.dumps({
                    'transport': body.get('transport'), 'hotel': body.get('hotel'),
                    'dining': body.get('dining'), 'activities': body.get('activities'),
                })
        except (ValueError, TypeError, KeyError) as e:
            logging.getLogger('groundwork').warning('trip_history estimate write skipped: %s', e)

        session.commit()
        return ok({'saved': True})


# ── Utility price benchmarks ───────────────────────────────────────────────────
# Real residential natural-gas/electricity prices for the user's own state
# (or national, if no home state is set) — a budget benchmark, not a
# billing figure. See utility_price.py.

utility_bp = Blueprint('utility', __name__)


def _home_state() -> str:
    """The user's configured home state (2-letter USPS code), '' if unset."""
    try:
        with db_session() as session:
            row = _get_setting(session, 'home_state')
            return (row.value if row else '').strip().upper()[:2]
    except Exception:
        return ''


@utility_bp.route('/natural-gas-price', methods=['GET'])
def utility_natural_gas_price():
    import utility_price
    return ok(utility_price.get_natural_gas_price(_get_eia_api_key(), _home_state()))


@utility_bp.route('/electricity-price', methods=['GET'])
def utility_electricity_price():
    import utility_price
    return ok(utility_price.get_electricity_price(_get_eia_api_key(), _home_state()))


# ── Net Worth snapshots ────────────────────────────────────────────────────────

networth_bp = Blueprint('networth', __name__)


def _serialize_snapshot(s) -> dict:
    """Serialize a NetWorthSnapshot row. Handles string snapshot_date."""
    from datetime import datetime as _dt
    date_str = s.snapshot_date or ''
    try:
        # snapshot_date stored as YYYY-MM or YYYY-MM-DD
        if len(date_str) == 7:
            label = _dt.strptime(date_str, '%Y-%m').strftime('%b %Y')
        elif len(date_str) >= 10:
            label = _dt.strptime(date_str[:7], '%Y-%m').strftime('%b %Y')
        else:
            label = date_str
    except ValueError:
        label = date_str
    return {
        'id':               s.id,
        'date':             date_str,
        'month_label':      label,
        'total_assets':     round(s.assets      or 0, 2),
        'total_liabilities':round(s.liabilities or 0, 2),
        'net_worth':        round(s.net_worth   or 0, 2),
        'notes':            s.notes or '',
        'breakdown':        {},
    }


def _snapshot_without_figures(s) -> bool:
    """Item 38 P4: a snapshot whose assets, liabilities and net worth are all 0 records no figures - the paid-off
    marker wrote such rows from the first commit until 2026-10-04 (a missing figure read as 0). It is not a net worth
    of $0. A row with a net worth but no breakdown has a figure, and is never set aside."""
    return not (s.assets or 0) and not (s.liabilities or 0) and not (s.net_worth or 0)


def _snapshots_by_month(session):
    """(month rows oldest first, all-zero rows that stand alone in their month). Nothing is deleted or rewritten:
    for each month the readers use its latest snapshot with figures; an all-zero row beside one is skipped; an all-zero
    row alone in its month is returned separately, to be shown as recorded without figures, never as a value."""
    by_month = {}
    for r in session.query(NetWorthSnapshot).order_by(NetWorthSnapshot.snapshot_date, NetWorthSnapshot.id).all():
        by_month.setdefault(r.snapshot_date, []).append(r)
    real, alone = [], []
    for month in sorted(by_month):
        with_figures = [r for r in by_month[month] if not _snapshot_without_figures(r)]
        if with_figures:
            real.append(with_figures[-1])
        else:
            alone.append(by_month[month][-1])
    return real, alone


@networth_bp.route('/snapshots', methods=['GET'])
def list_snapshots():
    """Return snapshot history for the trending chart: one row per month with figures (item 38 P4), plus - marked
    `without_figures` - any month whose only record has none, so the page can say so instead of drawing $0."""
    months = int(request.args.get('months', 24))
    with db_session() as session:
        real, alone = _snapshots_by_month(session)
        rows = sorted([(r, False) for r in real] + [(r, True) for r in alone], key=lambda x: x[0].snapshot_date)[-months:]
        return ok([{**_serialize_snapshot(r), 'without_figures': w} for r, w in rows])


_SNAPSHOT_LOCK = threading.Lock()


def _merge_note(old, new):
    """A note is added to a snapshot's notes once; nothing already recorded is removed."""
    old, new = (old or '').strip(), (new or '').strip()
    if not new or new in old:
        return old
    return (old + ' ' + new).strip()[:2000]


@networth_bp.route('/snapshot', methods=['POST'])
def create_snapshot():
    """Take this month's net worth snapshot (item 38, PAID_OFF_SNAPSHOT.md).

    P2  `assets` and `liabilities` are required numbers - a missing figure is refused, never read as 0
    P3  one snapshot per month: the check and the insert happen under one lock
    P1  a `note` on a month already taken is added to that month's snapshot; its figures are left alone unless `force`
    """
    body  = request.get_json(silent=True) or {}
    force = bool(body.get('force', False))
    month_key = date.today().strftime('%Y-%m')

    if body.get('note_only'):
        # P1: a payoff noted on this month's snapshot, when there is one with figures. Never a snapshot of its own.
        note = str(body.get('note') or '').strip()[:500]
        with _SNAPSHOT_LOCK, db_session() as session:
            snap = next((r for r in session.query(NetWorthSnapshot).filter_by(snapshot_date=month_key)
                         .order_by(NetWorthSnapshot.id.desc()).all() if not _snapshot_without_figures(r)), None)
            if not snap or not note:
                return ok({'taken': False, 'noted': False,
                           'message': 'No snapshot with figures this month to add the note to.' if note else 'No note.'})
            snap.notes = _merge_note(snap.notes, note)
            session.commit()
            return ok({'taken': False, 'noted': True, 'snapshot': _serialize_snapshot(snap)})

    def _figure(k):
        v = body.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float('inf'), float('-inf')):
            return None
        return float(v)
    assets, liabilities = _figure('assets'), _figure('liabilities')
    if assets is None or liabilities is None:
        return err('a snapshot needs assets and liabilities as numbers - a missing figure is not zero')

    with _SNAPSHOT_LOCK, db_session() as session:
        existing = (session.query(NetWorthSnapshot).filter_by(snapshot_date=month_key)
                    .order_by(NetWorthSnapshot.id.desc()).all())
        existing = next((r for r in existing if not _snapshot_without_figures(r)), existing[0] if existing else None)
        if existing and not force and not _snapshot_without_figures(existing):
            note = str(body.get('note') or '').strip()[:500]
            if note:
                existing.notes = _merge_note(existing.notes, note)
                session.commit()
            return ok({'taken': False, 'noted': bool(note), 'snapshot': _serialize_snapshot(existing),
                       'message': 'Snapshot already exists. Pass force=true to overwrite.'})
        # An all-zero record for this month (the old marker's) is never overwritten; a real snapshot is added beside
        # it, and the readers use the one with figures (P4).
        if existing and _snapshot_without_figures(existing):
            existing = None
        net_worth   = assets - liabilities
        notes = [str(body.get('note') or '').strip()[:500]]        # what the page says the figure leaves out (V6)
        # Item 35 V7: history is never rewritten; the first snapshot after valuation changed says so, so a step in the
        # line is explained rather than read as a loss. Once, and only for a household that has held investments.
        if not _get_setting(session, 'inv_valuation_v35_noted'):
            # ... and only where there is an earlier snapshot whose line the change would step (a new household has none)
            earlier = session.query(NetWorthSnapshot.id).filter(NetWorthSnapshot.snapshot_date < month_key).first()
            if earlier and session.query(InvestmentLot.id).first():
                notes.append('Investment valuation changed on ' + date.today().isoformat() + ': holdings with no '
                             'price on record are no longer counted at cost, and lots with no cost basis are left '
                             'out of the gain.')
            session.add(AppSetting(key='inv_valuation_v35_noted', value=date.today().isoformat()))
        note = ' '.join(n for n in notes if n)
        if existing:
            existing.assets      = assets
            existing.liabilities = liabilities
            existing.net_worth   = net_worth
            if note:
                existing.notes = _merge_note(existing.notes, note)
            snap = existing
        else:
            snap = NetWorthSnapshot(
                snapshot_date=month_key,
                assets=assets,
                liabilities=liabilities,
                net_worth=net_worth,
                notes=note,
            )
            session.add(snap)
        _log_net_worth_milestone_variance(session, month_key, net_worth)
        session.commit()
        return ok({'taken': True, 'snapshot': _serialize_snapshot(snap)})


@networth_bp.route('/milestone/<milestone_id>/confidence', methods=['GET'])
def net_worth_milestone_confidence(milestone_id):
    """Net worth's mirror of GET /api/debt/<id>/confidence — thin read of
    get_net_worth_milestone_confidence, this feature's version of Phase H2
    Feature 5 (payoff confidence scoring), for milestone pace instead of
    debt payoff."""
    with db_session() as session:
        return ok(get_net_worth_milestone_confidence(session, milestone_id))


@networth_bp.route('/snapshots/<int:snapshot_id>', methods=['DELETE'])
def delete_snapshot(snapshot_id):
    """Delete a specific snapshot (e.g. to correct bad data)."""
    with db_session() as session:
        s = session.get(NetWorthSnapshot, snapshot_id)
        if not s:
            return err('Snapshot not found', 404)
        session.delete(s)
        session.commit()
        return ok({'deleted': snapshot_id})


@networth_bp.route('/goal', methods=['GET'])
def get_goal():
    """Return the saved net worth goal (amount + date)."""
    with db_session() as session:
        amount_row = _get_setting(session, 'nw_goal_amount')
        date_row   = _get_setting(session, 'nw_goal_date')
        return ok({
            'amount': float(amount_row.value) if amount_row else None,
            'date':   date_row.value          if date_row   else None,
        })


@networth_bp.route('/goal', methods=['PUT'])
@require_json
def save_goal():
    """
    Save or update the net worth goal.
    Body: { amount: float, date: 'YYYY-MM' }
    """
    body   = request.json
    amount = body.get('amount')
    target = (body.get('date') or '').strip()

    if amount is None or not target:
        return err('amount and date required')
    try:
        float(amount)
        # Validate YYYY-MM format
        from datetime import datetime
        datetime.strptime(target + '-01', '%Y-%m-%d')
    except (ValueError, TypeError):
        return err('amount must be a number and date must be YYYY-MM')

    with db_session() as session:
        for key, val in [('nw_goal_amount', str(amount)),
                         ('nw_goal_date',   target)]:
            row = _get_setting(session, key)
            if row:
                row.value = val
            else:
                session.add(AppSetting(key=key, value=val))
        session.commit()
    return ok({'amount': float(amount), 'date': target})


@networth_bp.route('/goal', methods=['DELETE'])
def delete_goal():
    """Clear the saved goal."""
    with db_session() as session:
        for key in ('nw_goal_amount', 'nw_goal_date'):
            row = _get_setting(session, key)
            if row:
                session.delete(row)
        session.commit()
    return ok({'cleared': True})


def _exports_dir() -> Path:
    """
    Where exports are written. Downloads by default, because that is where a
    file someone asked for should turn up, and settable for the same reasons
    the backup folder is - external storage, a redirected profile, a machine
    where Downloads is not where Python thinks it is.

    Two things this fixes over the hardcoded path it replaces. A home folder
    with no Downloads directory - renamed, redirected to OneDrive, or a
    service account - made the write raise, and the user was shown "Export
    failed: [Errno 2] No such file or directory" for a folder they never chose.
    It is created now. And the destination was untestable: the only way to
    exercise the write was to drop a file in the real Downloads folder of
    whoever ran the suite, so nothing ever did.

    Same fallback discipline as _backups_dir: a configured folder that has
    gone away falls back to the default rather than failing the export.
    """
    default = Path.home() / 'Downloads'
    try:
        with db_session() as session:
            setting = session.query(AppSetting).filter_by(key='export_dir').first()
            custom = (setting.value or '').strip() if setting else ''
    except Exception:
        custom = ''

    if custom:
        p = Path(custom)
        try:
            p.mkdir(parents=True, exist_ok=True)
            if os.access(p, os.W_OK):
                return p
        except OSError:
            logging.getLogger('groundwork').warning(
                'custom export dir %s not writable - falling back to Downloads', p)

    try:
        default.mkdir(parents=True, exist_ok=True)
        return default
    except OSError:
        # No home, no Downloads, nowhere to put it. The data directory always
        # exists - the database is in it - so the export lands somewhere the
        # app can name rather than failing.
        fallback = DATA_DIR / 'exports'
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


@settings_bp.route('/export-to-file', methods=['POST'])
def export_to_file():
    """
    Save export directly to the user's Downloads folder, or wherever
    _exports_dir() resolves to if that has been pointed elsewhere.
    Returns the full path so the app can tell the user exactly where it is.
    """
    import io

    body       = request.get_json(silent=True) or {}
    fmt_param  = body.get('format', 'json').lower()
    if fmt_param not in ('json', 'csv'):
        return err('format must be "json" or "csv"')

    # Build the export content (reuse the same logic)
    with db_session() as session:
        # BUG FIX (July 6): these were bare list comprehensions — one bad
        # record anywhere (a null date, a malformed debt account, whatever)
        # threw an unhandled exception that killed the ENTIRE export for
        # every other record too, surfacing to the user as a generic
        # "Internal error (logged)" with no indication what actually broke
        # or how many records were affected. Confirmed as a real risk: the
        # 'date' field crash below was found on inspection, not from a live
        # traceback — this per-item guard means whatever the next such gap
        # turns out to be, it degrades to "one row skipped" instead of
        # "nobody's export works."
        txns        = session.query(Transaction).order_by(desc(Transaction.date)).all()
        # Item 45 H6 P3: health spending stays out of an export unless the person ticks it in
        from core import health_boundary
        health_left_out = 0
        if not body.get('include_health'):
            _is_health = health_boundary.health_rows(session)   # item 86 F6: an HSA / FSA account's rows too
            health_left_out = sum(1 for t in txns if _is_health(t))
            txns = [t for t in txns if not _is_health(t)]
        txn_rows, txn_skipped = [], 0
        for t in txns:
            try:
                txn_rows.append(serialize_transaction(t))
            except Exception as _e:
                txn_skipped += 1
                logging.warning('export: skipped transaction id=%s (%s)', getattr(t,'id',None), _e)

        from core.database import BudgetItem
        budget_rows = [{'type':i.type,'name':i.name,'amount':i.amount}
                       for i in session.query(BudgetItem).filter_by(is_active=True).all()]

        debt_rows, debt_skipped = [], 0
        for d in session.query(DebtAccount).filter_by(is_active=True).all():
            try:
                debt_rows.append(serialize_debt_account(d, session))
            except Exception as _e:
                debt_skipped += 1
                logging.warning('export: skipped debt account id=%s (%s)', getattr(d,'id',None), _e)

        nw_rows, nw_skipped = [], 0
        for s in session.query(NetWorthSnapshot).order_by(NetWorthSnapshot.snapshot_date).all():
            try:
                nw_rows.append({'date': str(s.snapshot_date), 'assets': s.total_assets,
                                 'liabilities': s.total_liabilities, 'net_worth': s.net_worth})
            except Exception as _e:
                nw_skipped += 1
                logging.warning('export: skipped net worth snapshot id=%s (%s)', getattr(s,'id',None), _e)

        if txn_skipped or debt_skipped or nw_skipped:
            logging.warning('export: completed with skipped records — transactions=%d debts=%d net_worth=%d',
                             txn_skipped, debt_skipped, nw_skipped)

        all_settings = {r.key: r.value for r in session.query(AppSetting).all()
                        if r.key not in ('api_key', 'app_snapshot')}

        ts       = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'groundwork_export_{ts}.{fmt_param}'
        dest     = _exports_dir() / filename

        try:
            if fmt_param == 'csv':
                import csv
                output = io.StringIO()
                w = csv.writer(output)
                if health_left_out:
                    w.writerow([f'{health_left_out} health spending transaction(s) left out; tick "Include health spending" to include them'])
                w.writerow(['--- TRANSACTIONS ---'])
                if txn_rows:
                    w.writerow(txn_rows[0].keys())
                    for r in txn_rows: w.writerow(r.values())
                w.writerow([]); w.writerow(['--- DEBT ACCOUNTS ---'])
                if debt_rows:
                    w.writerow(debt_rows[0].keys())
                    for r in debt_rows: w.writerow(r.values())
                w.writerow([]); w.writerow(['--- NET WORTH HISTORY ---'])
                if nw_rows:
                    w.writerow(nw_rows[0].keys())
                    for r in nw_rows: w.writerow(r.values())
                if body.get('include_health'):    # item 87 P8: the health plans only on the health tick
                    from core import health_plan as _hp
                    w.writerow([]); w.writerow(['--- HEALTH PLANS ---'])
                    w.writerow(['name', 'from', 'to', 'tier', 'deductible', 'oop_max', 'deductible_met', 'oop_met'])
                    for r in _hp.export_rows(session):
                        w.writerow([r[k] for k in ('name', 'from', 'to', 'tier', 'deductible', 'oop_max', 'deductible_met', 'oop_met')])
                dest.write_text(output.getvalue(), encoding='utf-8')
            else:
                payload = {
                    'exported_at':   datetime.now().isoformat(),
                    'health_left_out': (f'{health_left_out} health spending transaction(s) left out; tick "Include '
                                        'health spending" to include them') if health_left_out else None,
                    'transactions':  txn_rows,
                    'budget':        budget_rows,
                    'debt_accounts': debt_rows,
                    'net_worth':     nw_rows,
                    'settings':      all_settings,
                }
                if body.get('include_health'):    # item 87 P8: the health plans only on the health tick
                    from core import health_plan as _hp
                    payload['health_plans'] = _hp.export_rows(session)
                if body.get('include_ai_log'):    # item 62 G5: only when the person ticks it
                    payload['ai_log'] = [_ai_log_json(r, full=True) for r in session.query(AiLog).order_by(AiLog.id).all()]
                dest.write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')

            resp = {'saved': True, 'path': str(dest), 'filename': filename, 'health_left_out': health_left_out}
            total_skipped = txn_skipped + debt_skipped + nw_skipped
            if total_skipped:
                resp['skipped'] = total_skipped
                resp['warning'] = (f'{total_skipped} record(s) could not be exported and were skipped — '
                                    f'check the app log for details.')
            return ok(resp)
        except Exception as e:
            return err(f'Export failed: {e}', 500)


# ── AI proxy ──────────────────────────────────────────────────────────────────

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/chat', methods=['POST'])
@require_json
def ai_chat():
    """
    AI proxy to the LOCAL model (the in-app engine, in this process) - the only AI
    Groundwork has. Cloud AI was removed on purpose (CLOUD_AI_REMOVAL.md): no
    path sends a user's data to an off-device model, and s52 fails if one
    returns. The response keeps its internal shape
    ({content:[{type:'text', text:...}]}), an application-internal contract
    with callAI(), not a network format (ruling 2).
    """
    # Item 8 provision 2: the model has no hands - it writes text and nothing else. A request that offers it tools or
    # functions is refused, and no call into the engine passes any (s240).
    if any(k in (request.json or {}) for k in ('tools', 'tool_choice', 'functions', 'function_call')):
        return err('The AI writes text only; it is given no tools.', 400)
    # Respect the user's AI toggle — return a friendly message, not an error code
    if not _ai_is_enabled():
        return ok({
            'ai_available': False,
            'reason':       'disabled',
            'message':      'AI features are turned off. You can enable them in Settings.',
        })

    body = _health_scrub_prompt(request.json or {})
    if body.get('stream'):
        return _ai_chat_stream(body)
    return _ai_chat_local(body)


def _health_scrub_prompt(body):
    """Item 45 H6 P5: what the model is given passes the health scrubber - a category and an amount stay; a merchant,
    a description or a health record's text does not. Learned fresh, so a just-imported pharmacy is caught."""
    from core import health_boundary
    try:
        with db_session() as _hs:
            health_boundary.refresh(_hs)
    except Exception:
        pass
    out = dict(body)
    if 'system' in out:
        out['system'] = health_boundary.scrub(out.get('system'))
    if 'messages' in out:
        out['messages'] = health_boundary.scrub_obj(out.get('messages') or [])
    return out


@ai_bp.route('/stop', methods=['POST'])
def ai_stop():
    """Item 10 S6: the user pressed Stop - end the generation in progress."""
    from core import engine
    engine.cancel()
    return ok({'stopping': True})


def _ai_chat_stream(body: dict):
    """Item 10 S4 (NARRATION_STREAMING.md): the same local chat, answered as server-sent events on this computer's own
    server - {"t": piece} as the model writes, then {"done": true, "stop_reason": ...} ('end_turn', 'max_tokens' or
    'unknown', exactly as _ai_chat_local maps it), or {"stopped": true}, or {"error": reason, "message": ...}.
    Nothing leaves the machine (s52). The page shows nothing until the voice check has passed a whole sentence (S1)."""
    from core import engine

    def events():
        said = []                          # item 62: the whole answer, for the log, written when the stream ends
        for kind, val in engine.chat_stream(body.get('system'), body.get('messages', []),
                                            max_tokens=int(body.get('max_tokens', 1000)),
                                            temperature=float(body.get('temperature', 0.3))):
            if kind == 'text':
                said.append(val)
                yield 'data: ' + json.dumps({'t': val}) + '\n\n'
            elif kind == 'done':
                stop_reason = 'max_tokens' if val == 'length' else 'end_turn' if val == 'stop' else 'unknown'
                log_id = _ai_log_write(body, ''.join(said), stop_reason, engine.MODEL_FILE)
                yield 'data: ' + json.dumps({'done': True, 'stop_reason': stop_reason, 'log_id': log_id}) + '\n\n'
            elif kind == 'stopped':
                _ai_log_write(body, ''.join(said), 'stopped', engine.MODEL_FILE, stopped=True)
                yield 'data: ' + json.dumps({'stopped': True}) + '\n\n'
            else:
                _ai_log_write(body, ''.join(said), 'unavailable', engine.MODEL_FILE)
                yield 'data: ' + json.dumps({'error': 'engine_' + val['reason'], 'message': val['message']}) + '\n\n'
    return Response(stream_with_context(events()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ── Local AI: the in-app engine (core/engine.py; ENGINE_REPLACEMENT.md, item 31) ────────────────────────────────
# Ollama is gone from both lines (Rob, 2026-09-27 and 2026-10-02). The model runs inside this process: no port, no
# second program, no endpoint or model to configure. So the old rule that a "local" address must be this computer
# (SAFETY_PROVISIONS_INVENTORY S6) now holds by construction - there is no address at all.

# ── Item 62 - the AI log (AI_LOG.md) ───────────────────────────────────────────────────────────────────────────
AI_LOG_DAYS = 90


def _ai_log_write(body, response='', stop_reason='', model='', stopped=False):
    """G1/G7: one row per attempt, written here only. Off when the person turned the log off (G4); entries older
    than 90 days go each time one is written. Never read by anything but the log's own routes (G3)."""
    try:
        with db_session() as session:
            if (_get_setting(session, 'ai_log_keep') or AppSetting(value='')).value == 'off':
                return None
            session.query(AiLog).filter(AiLog.created_at < datetime.now() - timedelta(days=AI_LOG_DAYS)) \
                .delete(synchronize_session=False)
            from core import health_boundary as _hb      # item 45 H6 P6: scrubbed again, whoever called
            row = AiLog(call_id=str(body.get('log_call') or '')[:64], attempt=int(body.get('log_attempt') or 1),
                        surface=str(body.get('surface') or '')[:80], system=_hb.scrub(str(body.get('system') or ''))[:40000],
                        messages=json.dumps(_hb.scrub_obj(body.get('messages') or []))[:80000],
                        response=_hb.scrub(str(response or ''))[:40000],
                        stop_reason=str(stop_reason or '')[:20], stopped=bool(stopped), model=str(model or '')[:120])
            session.add(row)
            session.commit()
            return row.id
    except Exception:
        logging.getLogger('groundwork').warning('the AI log could not be written')
        return None


def _ai_chat_local(body: dict):
    """Run one chat on the in-app engine; return the internal shape callAI() reads ({content:[{type,text}]})."""
    from core import engine
    r = engine.chat(body.get('system'), body.get('messages', []),
                    max_tokens=int(body.get('max_tokens', 1000)),
                    temperature=float(body.get('temperature', 0.3)))
    if not r['ok']:
        _ai_log_write(body, stop_reason='unavailable')
        return ok({'ai_available': False, 'reason': f"engine_{r['reason']}", 'message': r['message']})
    # Whether the answer finished or hit its token cap, from the engine itself: 'length' is the cap, 'stop' is a
    # finished answer, and anything else is unknown - never read as finished (item 12 reads this as stop_reason).
    finish = r['finish']
    stop_reason = 'max_tokens' if finish == 'length' else 'end_turn' if finish == 'stop' else 'unknown'
    log_id = _ai_log_write(body, r['text'], stop_reason, engine.MODEL_FILE)
    return jsonify({'content': [{'type': 'text', 'text': r['text']}], 'model': engine.MODEL_FILE,
                    'finish': finish, 'stop_reason': stop_reason, 'log_id': log_id})


def engine_launch():
    """Called once by the launcher when the server is up. Loads the model only if AI is on (R-a); never blocks."""
    from core import engine
    engine.allow_load()
    if _ai_is_enabled():
        engine.start()


def _get_config_value(name: str) -> str:
    """
    Locate a secret/config value by name. Checks in order:
      1. <name> environment variable
      2. config.json in the app data directory (DATA_DIR)
      3. config.json next to server.py
      4. config.json in the user's home directory
    Never reads from the database — keys stay on the filesystem only.
    Shared by every external API key this app uses (EIA) —
    one lookup convention, not a copy per key.
    """
    val = os.environ.get(name, '').strip()
    if val and val != 'your-api-key-here':
        return val

    for search_dir in [DATA_DIR, Path(__file__).parent, Path.home()]:
        cfg = search_dir / 'config.json'
        if cfg.exists():
            try:
                with open(cfg, 'r', encoding='utf-8') as f:
                    v = json.load(f).get(name, '').strip()
                if v and v != 'your-api-key-here':
                    return v
            except Exception:
                pass
    return ''


def _get_eia_api_key() -> str:
    """
    The EIA (U.S. Energy Information Administration) open-data API key, for
    Phase 5A's real national-average gas price. Free, self-service key at
    https://www.eia.gov/opendata/register.php — same config.json/env lookup
    convention as the other keys. Trip planning degrades to an honest
    estimate (gas_price.FALLBACK_PRICE) when this isn't configured, never
    a crash or a silently wrong "live" number.
    """
    return _get_config_value('EIA_API_KEY')


def _ai_is_enabled() -> bool:
    """Check if AI features are enabled in app_settings."""
    try:
        with db_session() as session:
            row = _get_setting(session, 'ai_enabled')
            # Default to enabled if key not yet set
            return row is None or row.value != 'false'
    except Exception:
        return True  # default on if DB not available


@ai_bp.route('/status', methods=['GET'])
def ai_status():
    """The engine's state for Settings -> AI: off / loading / ready / unavailable, with an honest message."""
    from core import engine
    st = engine.status()
    dev = st.get('device') or {}
    # Item 95 G7: where the AI runs and how that was measured - shown, never a control (G0: the software chooses).
    return ok({'enabled': _ai_is_enabled(), 'engine': st['state'], 'reason': st['reason'],
               'message': st['message'], 'model_file': st['model_file'],
               'ready': st['state'] == 'ready', 'available': st['state'] in ('loading', 'fitting', 'ready'),
               'load_seconds': st['load_seconds'],
               'device_line': dev.get('line', '') if st['state'] == 'ready' else '',
               'device_tried': dev.get('tried', []) if st['state'] == 'ready' else []})


# 8 GB is the minimum for Groundwork AI, not for Groundwork (R-d). An "8 GB" machine reports a little under 8 to
# Windows (firmware and integrated graphics reserve some), so the line sits at 7.5.
AI_MIN_TOTAL_GB = 7.5


@ai_bp.route('/system-ram', methods=['GET'])
def ai_system_ram():
    """
    The first-run trust surface: what THIS machine can run, before anything else happens. One model, one engine:
    a machine meets the AI minimum or it doesn't, and either way the choice to turn AI on is the user's. Every core
    feature works with AI off.
    """
    from core import engine
    cpu_ok, cpu_detail = engine.cpu_supported()
    try:
        import psutil
        vm = psutil.virtual_memory()
        total_gb = round(vm.total / (1024 ** 3), 1)
        free_gb  = round(vm.available / (1024 ** 3), 1)
    except Exception as e:
        return ok({'available': False, 'error': str(e), 'cpu_ok': cpu_ok})
    return ok({'available': True, 'total_gb': total_gb, 'free_gb': free_gb, 'ai_min_gb': 8,
               'cpu_ok': cpu_ok, 'cpu_detail': cpu_detail,
               'meets_ai_minimum': cpu_ok and total_gb >= AI_MIN_TOTAL_GB})


# ── An Ollama left from before: the one-time notice (R-b) ───────────────────────────────────────────────────────
# Earlier installers ran Ollama's own installer into its standard per-user location and wrote no marker, so
# Groundwork cannot tell a copy it installed from one the user installed and uses elsewhere. It removes nothing: it
# says once what is there and offers Windows' own uninstall. The user decides.

def _dir_bytes(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _ollama_footprint():
    """What an existing Ollama is: where, how big, whether it starts at login. Read-only. None when there is none."""
    if sys.platform != 'win32':
        return None
    program = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Ollama'
    if not (program / 'ollama.exe').exists():
        return None
    models = Path.home() / '.ollama' / 'models'
    startup = (Path(os.environ.get('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
               / 'Startup' / 'Ollama.lnk')
    return {'program_dir': str(program), 'program_bytes': _dir_bytes(program),
            'models_dir': str(models) if models.exists() else '',
            'models_bytes': _dir_bytes(models) if models.exists() else 0,
            'starts_at_login': startup.exists()}


@ai_bp.route('/ollama-notice', methods=['GET'])
def ai_ollama_notice():
    with db_session() as session:
        row = _get_setting(session, 'ollama_notice')
        if row and row.value == 'shown':
            return ok({'show': False})
    fp = _ollama_footprint()
    return ok({'show': bool(fp), **(fp or {})})


@ai_bp.route('/ollama-notice', methods=['POST'])
def ai_ollama_notice_shown():
    with db_session() as session:
        row = _get_setting(session, 'ollama_notice')
        if row:
            row.value = 'shown'
        else:
            session.add(AppSetting(key='ollama_notice', value='shown'))
        session.commit()
    return ok({'shown': True})


@ai_bp.route('/ollama-notice/uninstall', methods=['POST'])
def ai_ollama_open_uninstall():
    """Open Windows' own Installed apps page. Groundwork uninstalls nothing itself."""
    if sys.platform != 'win32':
        return err('Only on Windows', 400)
    try:
        os.startfile('ms-settings:appsfeatures')
    except OSError as e:
        return err(f'Could not open Windows Settings: {e}', 500)
    return ok({'opened': True})


def _ai_log_json(r, full=False):
    v = None
    try:
        v = json.loads(r.voice) if r.voice else None
    except (TypeError, ValueError):
        v = None
    out = {'id': r.id, 'at': r.created_at.isoformat(timespec='seconds') if r.created_at else None,
           'call_id': r.call_id, 'attempt': r.attempt, 'surface': r.surface, 'stop_reason': r.stop_reason,
           'stopped': bool(r.stopped), 'voice': v, 'model': r.model}
    if full:
        try:
            msgs = json.loads(r.messages or '[]')
        except (TypeError, ValueError):
            msgs = []
        out.update(system=r.system, messages=msgs, response=r.response)
    return out


@ai_bp.route('/log', methods=['GET'])
def ai_log_list():
    """G1: the log, newest first - one line per attempt (the page groups a request's attempts). G3: this route and
    the four below are the only readers of the table."""
    with db_session() as session:
        session.query(AiLog).filter(AiLog.created_at < datetime.now() - timedelta(days=AI_LOG_DAYS)) \
            .delete(synchronize_session=False)
        session.commit()
        rows = session.query(AiLog).order_by(AiLog.id.desc()).limit(300).all()
        keep = (_get_setting(session, 'ai_log_keep') or AppSetting(value='')).value != 'off'
        return ok({'entries': [_ai_log_json(r) for r in rows], 'keep': keep, 'days': AI_LOG_DAYS})


@ai_bp.route('/log/<int:log_id>', methods=['GET'])
def ai_log_entry(log_id):
    with db_session() as session:
        r = session.get(AiLog, log_id)
        return ok(_ai_log_json(r, full=True)) if r else err('That entry is not in the log.', 404)


@ai_bp.route('/log/call/<call_id>', methods=['GET'])
def ai_log_call(call_id):
    """G2: a panel's link - every attempt of that request, in order."""
    with db_session() as session:
        rows = session.query(AiLog).filter(AiLog.call_id == call_id[:64]).order_by(AiLog.attempt, AiLog.id).all()
        return ok({'entries': [_ai_log_json(r, full=True) for r in rows]})


@ai_bp.route('/log/<int:log_id>/voice', methods=['POST'])
def ai_log_voice(log_id):
    """G1/G6: the page's voice check on that attempt - passed, or which rules it broke - so a rewrite shows."""
    body = request.get_json(silent=True) or {}
    rules = [str(x)[:60] for x in (body.get('rules') or [])][:20] if isinstance(body.get('rules'), list) else []
    with db_session() as session:
        r = session.get(AiLog, log_id)
        if r:
            r.voice = json.dumps({'pass': bool(body.get('pass')), 'rules': rules, 'shortened': bool(body.get('shortened'))})
            session.commit()
    return ok({'logged': bool(r)})


@ai_bp.route('/log/clear', methods=['POST'])
def ai_log_clear():
    """G4: Clear the log - every entry deleted."""
    with db_session() as session:
        n = session.query(AiLog).delete(synchronize_session=False)
        session.commit()
    return ok({'cleared': n})


@ai_bp.route('/log/keep', methods=['POST'])
def ai_log_keep():
    """G4: Keep the log - on or off. Off writes nothing; the panels still show their numbers."""
    keep = (request.get_json(silent=True) or {}).get('keep')
    if not isinstance(keep, bool):
        return err('keep must be true or false')
    with db_session() as session:
        _set_setting(session, 'ai_log_keep', 'on' if keep else 'off')
        session.commit()
    return ok({'keep': keep})


def _scrub_ai_log(db_file):
    """G5: a backup copy without the AI log - its rows deleted and the file compacted, so the text is gone from it."""
    import sqlite3
    con = sqlite3.connect(str(db_file))
    try:
        con.execute('DELETE FROM ai_log')
        con.commit()
        con.execute('VACUUM')
    except sqlite3.OperationalError:
        pass                                  # an older copy with no table has nothing to remove
    finally:
        con.close()


@ai_bp.route('/voice-miss', methods=['POST'])
def ai_voice_miss():
    """
    Phase 1E miss-log: the frontend's _voiceGateCheck() posts here every time
    a model's narration is rejected (fabricated number, assigned intent,
    self-narration, etc.), whether or not the retry-once recovers it. This is
    what makes residual R3 leakage visible in production instead of silently
    vanishing into the fallback — the record hardening depends on.

    Best-effort only: logging must never be able to break narration, so any
    failure here is swallowed and still returns ok().
    """
    body = request.get_json(silent=True) or {}
    entry = {
        'ts':      datetime.now().isoformat(),
        'surface': str(body.get('surface', 'unknown'))[:80],
        'model':   str(body.get('model', ''))[:80],
        'rules':   body.get('rules') if isinstance(body.get('rules'), list) else [],
        'text':    __import__('core.health_boundary', fromlist=['scrub']).scrub(str(body.get('text', '')))[:2000],   # H6
    }
    try:
        log_path = DATA_DIR / 'voice_miss_log.jsonl'
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        pass
    return ok({'logged': True})


@ai_bp.route('/miss-log', methods=['GET'])
def ai_miss_log_summary():
    """
    Phase H2 Feature 6 (adaptive learning — LLM gate improvement). Exposes
    Phase H1's get_llm_miss_log() so gate flags can actually be reviewed:
    which rules are failing most, on which surfaces, and the raw rejected
    text to read. "Improvement" itself (tightening a wordlist, rewording a
    prompt rule) is a human-in-the-loop step informed by this data, not
    something this route does automatically — there's no real observed
    failure pattern to react to until an actual gate miss happens in the
    field, and fabricating a "fix" without one would be exactly the kind
    of invented confidence this whole gate exists to prevent.
    """
    days = int(request.args.get('days', 30))
    return ok(get_llm_miss_log(time_range_days=days))


# ── Auto-import queue (Downloads folder watcher bridge) ───────────────────────
# launch.py POSTs detected files here; the frontend polls /pending to retrieve them.

_auto_import_queue = []   # list of {filename, content} dicts — cleared on read

# Statements (PDFs) are queued by NAME only - the watcher never reads their
# bytes, and nothing here does until the user says yes to the offer (F7). The
# bytes route below serves only a path that was actually offered this session,
# inside the Downloads folder, ending .pdf: it is not a general file reader.
_offered_statements = set()


def _in_downloads(file_path):
    """The resolved path if it lies inside the Downloads folder, else None (F6)."""
    from bank_window import downloads_dir
    try:
        target = Path(file_path).resolve()
        target.relative_to(downloads_dir().resolve())
        return target
    except (ValueError, OSError):
        return None

auto_import_bp = Blueprint('auto_import', __name__)


@auto_import_bp.route('/queue', methods=['POST'])
def auto_import_queue():
    """Receive a detected file from the Downloads watcher in launch.py."""
    body     = request.get_json(silent=True) or {}
    filename = (body.get('filename') or '').strip()
    content  = body.get('content', '')
    path     = (body.get('path') or '').strip()
    if body.get('kind') == 'statement':
        target = _in_downloads(path) if path else None
        if not filename or target is None or target.suffix.lower() != '.pdf':
            return ok({'queued': False})
        _offered_statements.add(str(target))
        _auto_import_queue.append({'filename': filename, 'path': str(target), 'kind': 'statement'})
        while len(_auto_import_queue) > 5:
            _auto_import_queue.pop(0)
        return ok({'queued': True, 'filename': filename})
    if not filename or not content:
        return ok({'queued': False})
    sha = (body.get('sha256') or '').strip().lower()
    _auto_import_queue.append({'filename': filename, 'content': content, 'path': path,
                               'sha256': sha if _SHA256_HEX.match(sha) else None})
    while len(_auto_import_queue) > 5:
        _auto_import_queue.pop(0)
    return ok({'queued': True, 'filename': filename})


@auto_import_bp.route('/delete-file', methods=['POST'])
def auto_import_delete_file():
    """
    Delete a file that failed validation.
    Security: only deletes files inside the user's Downloads folder.
    """
    body      = request.get_json(silent=True) or {}
    file_path = (body.get('path') or '').strip()
    if not file_path:
        return err('No path provided', 400)

    target = _in_downloads(file_path)
    if target is None:
        return err('File path is not within the Downloads folder', 403)

    if not target.exists():
        return ok({'deleted': False, 'reason': 'File no longer exists'})

    try:
        target.unlink()
        print(f'[Security] Deleted invalid import file: {target.name}')
        return ok({'deleted': True, 'filename': target.name})
    except OSError as e:
        return err(f'Could not delete file: {e}', 500)


# H2 (SOURCE_DOCUMENT_CUSTODY.md s4, s8): the user's Downloads copy, removed at
# the user's word after a successful import - to the Recycle Bin, never deleted.
# A Downloads-tidiness act on the USER's file; it retains nothing and ends no
# Groundwork custody (Groundwork never had the file). Each guard is a case in s128.
_REMOVABLE_KINDS = {'.qfx': 'transactions', '.ofx': 'transactions', '.qbo': 'transactions',
                    '.qif': 'transactions', '.csv': 'transactions', '.pdf': 'statements'}


@auto_import_bp.route('/remove-download', methods=['POST'])
def auto_import_remove_download():
    body     = request.get_json(silent=True) or {}
    target   = _in_downloads((body.get('path') or '').strip())
    sha      = (body.get('sha256') or '').strip().lower()
    standing = body.get('standing') is True
    if target is None:
        return err('That file is not in your Downloads folder', 403)
    if target.suffix.lower() not in _REMOVABLE_KINDS:
        return err('Only bank files and statements can be removed this way', 400)
    if not _SHA256_HEX.match(sha):
        return err('The file could not be identified', 400)
    import hashlib
    import recycle_bin
    with db_session() as session:
        # Only a file that was actually imported: an import_committed event
        # (H1) from the watcher, for exactly these bytes.
        imported = session.query(HistorianEntry).filter(
            HistorianEntry.event_category == 'import_committed',
            HistorianEntry.context_json.contains(f'"content_sha256": "{sha}"'),
        ).all()
        if not any(json.loads(e.context_json or '{}').get('origin') == 'watcher' for e in imported):
            return err('That file has not been imported', 409)
        if not target.is_file():
            return ok({'removed': False, 'reason': 'gone'})
        # Exactly the file imported: a newer download under the same name is
        # a different file, and is left alone.
        if hashlib.sha256(target.read_bytes()).hexdigest() != sha:
            return ok({'removed': False, 'reason': 'changed'})
        removed, reason = recycle_bin.send_to_recycle_bin(target)
        if not removed:
            return ok({'removed': False, 'reason': reason})
        _log_download_removed(session, target.name, sha, standing)
        session.commit()
    return ok({'removed': True})


def _log_download_removed(session, file_name, sha, standing):
    """H2's Historian record: the user's Downloads copy went to the Recycle Bin, one-off or by
    the user's standing choice. Touched by this writer alone - it reaches no prompt (s128)."""
    log_historian_event(session, 'download_removed', context={
        'file_name': file_name, 'content_sha256': sha, 'standing': standing,
    })


@auto_import_bp.route('/pending', methods=['GET'])
def auto_import_pending():
    """Return and clear the next queued file for the frontend to process."""
    if not _auto_import_queue:
        return ok(None)
    item = _auto_import_queue.pop(0)
    if item.get('sha256'):
        try:
            with db_session() as session:
                ff = _fetched_for(session, item['sha256'])
            if ff:
                item = {**item, 'fetched_for': ff}   # G6: the review starts on this account; the user can change it
        except Exception:
            pass
    return ok(item)


@auto_import_bp.route('/statement', methods=['POST'])
def auto_import_statement_bytes():
    """The bytes of an offered statement - called only after the user says yes (F7).

    Returns the file and nothing else: no extraction, no model call. The page
    hands it to the same import flow a manual upload takes.
    """
    body   = request.get_json(silent=True) or {}
    target = _in_downloads((body.get('path') or '').strip())
    if target is None or str(target) not in _offered_statements or target.suffix.lower() != '.pdf':
        return err('That statement was not offered', 403)
    if not target.is_file():
        return err('The statement is no longer in Downloads', 404)
    return send_file(str(target), mimetype='application/pdf', as_attachment=False,
                     download_name=target.name)


# ── Backup ────────────────────────────────────────────────────────────────────

# ── Item 105: a sample household to look around in (gw 2.0/SAMPLE_HOUSEHOLD.md, Rob 2026-10-20) ─────────────────────
# Offered on the welcome screen. It goes only into an empty Groundwork, and only the sample can be cleared this way.
sample_bp = Blueprint('sample', __name__)


@sample_bp.route('', methods=['GET'])
def sample_status():
    from core import sample_household as sh
    with db_session() as session:
        flag = _get_setting(session, sh.SAMPLE_FLAG)
        reason = sh.empty_reason(session)
        return ok({'sample': bool(flag and flag.value == 'true'), 'can_load': reason is None, 'why_not': reason})


@sample_bp.route('/load', methods=['POST'])
def sample_load():
    from flask import current_app
    from core import sample_household as sh
    with db_session() as session:
        reason = sh.empty_reason(session)
    if reason:
        return err(f'The sample household goes only into an empty Groundwork - {reason}.', 409)
    db_session.remove()
    try:
        made = sh.build(current_app.test_client(), {'X-GW-Token': _GW_TOKEN})
    except Exception as e:
        logging.exception('sample household')
        return err(f'The sample household could not be built: {e}', 500)
    return ok({'loaded': True, **made})


@sample_bp.route('/clear', methods=['POST'])
def sample_clear():
    """Back to a first launch: the sample's records go, the terms accepted and the AI and backup choices stay."""
    from core import sample_household as sh
    from core.database import DB_PATH, AppSetting, engine
    with db_session() as session:
        flag = _get_setting(session, sh.SAMPLE_FLAG)
        if not (flag and flag.value == 'true'):
            return err('Only the sample household can be cleared this way. Your own records are never cleared here.', 403)
        kept = {r.key: r.value for r in session.query(AppSetting).all() if r.key.startswith(sh.KEEP_PREFIXES)}
    try:
        db_session.remove()
        engine.dispose()
        for suffix in ('', '-wal', '-shm', '-journal'):
            f = DB_PATH.with_name(DB_PATH.name + suffix)
            if f.exists():
                f.unlink()
        run_migration_if_needed()
        with db_session() as session:
            for k, v in kept.items():
                setting = _get_setting(session, k)
                if setting:
                    setting.value = v
                else:
                    session.add(AppSetting(key=k, value=v))
            session.commit()
    except Exception as e:
        logging.exception('sample clear')
        return err(f'Clearing the sample failed: {e}', 500)
    return ok({'cleared': True})


backup_bp = Blueprint('backup', __name__)


def _backups_dir() -> Path:
    """
    Where backups are written. Defaults to the app's data directory, but
    the user can point this at external storage (e.g. a USB drive) via
    Settings -> Data & Backup -> Choose folder.

    If the configured folder is missing or unwritable (e.g. a USB drive
    that's been unplugged), silently fall back to the default rather than
    failing a backup/restore outright.
    """
    default = DATA_DIR / 'backups'
    try:
        with db_session() as session:
            setting = session.query(AppSetting).filter_by(key='backup_dir').first()
            custom = (setting.value or '').strip() if setting else ''
    except Exception:
        custom = ''

    if custom:
        p = Path(custom)
        try:
            p.mkdir(parents=True, exist_ok=True)
            if os.access(p, os.W_OK):
                return p
        except OSError:
            logging.getLogger('groundwork').warning(
                'custom backup dir %s not writable — falling back to default', p)

    default.mkdir(parents=True, exist_ok=True)
    return default


# ── Item 81 (PERFECT_BACKUP.md B1-B9): encrypted backups, three keys to one lock ──────────────────────────────
# The backup key lives in this computer's vault; each backup's header carries it wrapped by the backup password and by
# the 24-word recovery key. Groundwork sends no key anywhere and logs none (H6). core/backup_crypto.py does the sealing.

def _protection(session):
    return _setting_json(session, 'backup_protection')


def _vault_backup_key(prot):
    """This computer's copy of the backup key, if it is the one the protection was set up with."""
    from core import backup_crypto as bc
    if not prot:
        return None
    k = bc.VAULT.get()
    return k if k is not None and bc.key_id(k) == prot.get('key_id') else None


def _backup_before_migration():
    """Item 82 R3 (item 32 L3b, ruled 2026-10-04): before a database whose recorded schema differs from this build's
    is migrated - 1.1 opened by 2.0, or any later upgrade - a dated copy is written through the backup function: sealed
    when backup protection is set up (item 81 B1), plain only when it is not, exactly as every safety copy is (a copy
    is never blocked for want of a key). It is never deleted. A database holding no records has nothing to lose and
    gets no copy. The copy's name, folder and versions are kept so the app can say once where it is. Returns the
    record, or None when no copy was needed."""
    import sqlite3
    import migrate
    from core.database import DB_PATH
    stored = migrate._stored_schema_version()
    if stored == migrate.SCHEMA_VERSION:
        return None
    try:
        if not Path(DB_PATH).exists() or Path(DB_PATH).stat().st_size == 0:
            return None
        con = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
        try:
            present = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN "
                                                 "('transactions', 'debt_accounts', 'budget_items', 'accounts')")]
            held = sum(con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in present)
        finally:
            con.close()
        if not held:
            return None
    except Exception:                                     # noqa: BLE001 - unreadable here: copy it anyway, the safe way
        logging.getLogger('groundwork').warning('pre-upgrade backup: could not read the database first; copying anyway')
    rec = {'at': datetime.now().isoformat(timespec='seconds'), 'from': stored, 'to': migrate.SCHEMA_VERSION, 'shown': False}
    try:
        name = _write_backup(f"groundwork_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_before_upgrade")
        rec.update(name=name, folder=str(_backups_dir()), sealed=name.endswith('.gwbk'))
    except Exception as e:                                # noqa: BLE001 - said, never silent; the upgrade still runs
        logging.getLogger('groundwork').exception('pre-upgrade backup failed')
        rec.update(error=str(e)[:200])
    try:
        with db_session() as session:
            _set_setting(session, 'pre_upgrade_backup', json.dumps(rec))
            session.commit()
    except Exception:                                     # noqa: BLE001
        logging.getLogger('groundwork').warning('pre-upgrade backup: the note of it could not be saved')
    return rec


def _backup_after_migration(rec):
    """After a migration that had a before-upgrade copy (so there were records to keep), the migrated database is
    backed up too, sealed or plain on the same terms, and recorded as the person's latest backup (Rob 2026-10-22: "after
    the migration it does a backup of the new database so we have a backup"). A failure is logged and noted on the
    upgrade's record; it never stops the app opening."""
    try:
        name = _write_backup(f"groundwork_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_after_upgrade")
        rec.update(after_name=name)
        with db_session() as session:
            _set_setting(session, 'pre_upgrade_backup', json.dumps(rec))
            _set_setting(session, 'backup_last', json.dumps({**_backup_stamp(name), 'after_upgrade': True}))
            session.commit()
    except Exception:                                     # noqa: BLE001 - said, never silent; the app still opens
        logging.getLogger('groundwork').exception('after-upgrade backup failed')


def _write_backup(stem, include_ai_log=True, key=None):
    """Copy the live database to the backups folder - sealed when protection is set up and a key is at hand (B1),
    plain only when it is not (a safety copy before a delete is never blocked for want of a key). Returns the name."""
    import shutil
    from core import backup_crypto as bc
    from core.database import DB_PATH
    folder = _backups_dir()
    tmp = folder / f'.{stem}.tmp'
    shutil.copy2(DB_PATH, tmp)
    try:
        if not include_ai_log:
            _scrub_ai_log(tmp)
        with db_session() as session:
            prot = _protection(session)
        key = key or _vault_backup_key(prot)
        if prot and prot.get('confirmed') and key is not None:
            name = f'{stem}.gwbk'
            (folder / name).write_bytes(bc.encrypt_db(tmp.read_bytes(), key, prot))
            return name
        name = f'{stem}.db'
        shutil.copy2(tmp, folder / name)
        return name
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


@backup_bp.route('/pre-upgrade', methods=['GET', 'POST'])
def backup_pre_upgrade():
    """Item 82 R3: the copy written before the last upgrade, so the app says once where it is (GET), and that it was
    shown (POST). The copy itself is never touched here."""
    with db_session() as session:
        rec = _setting_json(session, 'pre_upgrade_backup')
        if request.method == 'POST' and rec:
            rec['shown'] = True
            _set_setting(session, 'pre_upgrade_backup', json.dumps(rec))
            session.commit()
        return ok(rec or {})


@backup_bp.route('/location', methods=['GET'])
def get_backup_location():
    """Return the effective backup directory and whether it's custom."""
    with db_session() as session:
        setting = session.query(AppSetting).filter_by(key='backup_dir').first()
        custom = (setting.value or '').strip() if setting else ''
    effective = _backups_dir()
    return ok({
        'path':       str(effective),
        'is_custom':  bool(custom),
        'is_default': str(effective) == str(DATA_DIR / 'backups'),
    })


@backup_bp.route('/location', methods=['POST'])
@require_json
def set_backup_location():
    """
    Set (or clear) a custom backup folder.
    Body: { path: str }  — empty string reverts to the default location.
    """
    path = (request.json.get('path') or '').strip()

    with db_session() as session:
        setting = _get_setting(session, 'backup_dir')

        if not path:
            if setting:
                session.delete(setting)
                session.commit()
            return ok({'path': str(DATA_DIR / 'backups'), 'is_custom': False, 'is_default': True})

        p = Path(path)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return err(f'Could not use that folder: {e}', 400)
        if not os.access(p, os.W_OK):
            return err('That folder is not writable', 400)

        if setting:
            setting.value = str(p)
        else:
            session.add(AppSetting(key='backup_dir', value=str(p)))
        session.commit()
        return ok({'path': str(p), 'is_custom': True, 'is_default': False})


# Item 45 H6 P4: a backup copies everything, because it exists to restore everything - so it says so.
BACKUP_STATEMENT = ('A backup contains everything, including health spending and records. '
                    'Keep it somewhere private.')


@backup_bp.route('', methods=['POST'])
@backup_bp.route('/create', methods=['POST'])
def create_backup():
    """Create a timestamped backup of the database."""
    import shutil
    from core.database import DB_PATH

    from core import backup_crypto as bc
    body = request.get_json(silent=True) or {}
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Item 81 B1: a backup is sealed, always - so protection is set up first, and the key must be at hand
    with db_session() as session:
        prot = _protection(session)
    if not (prot and prot.get('confirmed')):
        return err('Set up backup protection first: a password and a recovery key.', 409)
    key = _vault_backup_key(prot)
    if key is None:
        try:
            key = bc.unwrap(prot, password=body.get('password'))[0]
        except bc.BackupLocked:
            return err('This computer does not hold the backup key: enter the backup password.', 403)

    try:
        backup_name = _write_backup(f'groundwork_backup_{ts}', include_ai_log=bool(body.get('include_ai_log')), key=key)
        backup_path = _backups_dir() / backup_name
        with db_session() as session:                       # the backup reminder reads this, not the folder (Rob 2026-10-22)
            _set_setting(session, 'backup_last', json.dumps(_backup_stamp(backup_name)))
            session.commit()
        return ok({'filename': backup_name, 'size': backup_path.stat().st_size, 'statement': BACKUP_STATEMENT,
                   'encrypted': backup_name.endswith('.gwbk')})
    except Exception as e:
        return err(f'Backup failed: {e}', 500)


@backup_bp.route('/restore', methods=['POST'])
def restore_backup():
    """
    Restore the database from a named backup file.
    Safety checks:
      - File must exist in the backups directory (no path traversal)
      - File must be a valid SQLite database (magic bytes check)
    Process:
      - Close all active SQLAlchemy sessions and dispose engine connections
      - Copy backup file over the live database
      - Reinitialize the database layer
    """
    import shutil
    from core.database import DB_PATH, db_session, engine, init_db

    body     = request.get_json(silent=True) or {}
    filename = (body.get('filename') or '').strip()

    if not filename:
        return err('No filename provided', 400)

    # Security — must be inside backups directory, no traversal
    backup_path = (_backups_dir() / filename).resolve()
    allowed_dir = _backups_dir().resolve()
    if not str(backup_path).startswith(str(allowed_dir)):
        return err('Invalid backup path', 403)

    if not backup_path.exists():
        return err('Backup file not found', 404)

    # Item 81: a sealed backup opens by this computer's key, the password or the recovery words; a plain one is
    # checked as before. Either way, nothing touches the live database until the backup has opened in full.
    from core import backup_crypto as bc
    try:
        data, _how = _open_backup_bytes(backup_path.read_bytes(), body)
    except bc.BackupLocked as e:
        return err(str(e), 403)
    except bc.BackupDamaged as e:
        return err(str(e) if 'valid Groundwork backup' in str(e) else str(e), 400)
    except OSError as e:
        return err(f'Could not read backup file: {e}', 500)

    try:
        # Close all active sessions and release file locks
        db_session.remove()
        engine.dispose()

        # Write the opened backup over the live database
        DB_PATH.write_bytes(data)

        # Reinitialize — reconnects SQLAlchemy to the restored database, and
        # runs migrations in case the restored backup predates a schema
        # change (e.g. an older backup missing the CP3 Transaction columns).
        run_migration_if_needed()

        return ok({'restored': True, 'filename': filename})
    except Exception as e:
        return err(f'Restore failed: {e}', 500)


@backup_bp.route('/restore-upload', methods=['POST'])
def restore_backup_upload():
    """
    Restore the database from an uploaded backup file.

    Unlike /restore (which only accepts a filename already in this
    machine's backups folder), this accepts a file the user picked from
    anywhere on disk — the common case being a backup copied over from a
    previous computer. Same SQLite validation and restore process as
    /restore; the uploaded file is also saved into the backups directory
    so it shows up in future "Manage backups" lists.
    """
    import shutil
    from core.database import DB_PATH, db_session, engine, init_db

    if 'file' not in request.files:
        return err('No file uploaded', 400)

    upload = request.files['file']
    if not upload.filename:
        return err('No file selected', 400)

    # Validate SQLite magic bytes before touching anything
    try:
        header = upload.stream.read(16)
        upload.stream.seek(0)
    except OSError as e:
        return err(f'Could not read uploaded file: {e}', 500)

    from core import backup_crypto as bc
    if not (header.startswith(b'SQLite format 3') or bc.is_encrypted(header)):
        return err('That file does not look like a Groundwork backup', 400)
    blob = upload.stream.read()
    try:
        data, _how = _open_backup_bytes(blob, {'password': request.form.get('password'),
                                               'words': request.form.get('words')})
    except bc.BackupLocked as e:
        return err(str(e), 403)
    except bc.BackupDamaged as e:
        return err(str(e), 400)

    ts          = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name   = f'restored_{ts}' + ('.gwbk' if bc.is_encrypted(blob) else '.db')
    backup_path = _backups_dir() / safe_name

    try:
        backup_path.write_bytes(blob)          # kept as it came: sealed stays sealed

        # Close all active sessions and release file locks
        db_session.remove()
        engine.dispose()

        # Write the opened backup over the live database
        DB_PATH.write_bytes(data)

        # Reinitialize — reconnects SQLAlchemy to the restored database, and
        # runs migrations in case the restored backup predates a schema
        # change (e.g. an older backup missing the CP3 Transaction columns).
        run_migration_if_needed()

        return ok({'restored': True, 'filename': safe_name})
    except Exception as e:
        return err(f'Restore failed: {e}', 500)


# ── The backup reminder (Rob 2026-10-22, after Quicken's): "you have not backed up since <date>" ─────────────────────
# Every backup the person makes records its date ('backup_last'), so a backup on a drive that is unplugged still counts.
# A reminder is due when the last one is BACKUP_REMIND_DAYS old (the person's choice of 3, 7, 14 or 30) AND records were
# added since - with nothing new there is nothing more to lose, and a reminder would only be noise. Never backed up:
# due once the record holds transactions. The copy of a database just upgraded counts (it is all of it, as it now
# is); the safety copies of what was there before a migration or a delete don't. "Remind me later" hides it for BACKUP_SNOOZE_DAYS. Not for the sample.
BACKUP_REMIND_DAYS = 7
BACKUP_REMIND_CHOICES = (3, 7, 14, 30)
BACKUP_SNOOZE_DAYS = 3
_OWN_BACKUP = re.compile(r'^groundwork_backup_\d{8}_\d{6}(_after_upgrade)?\.(gwbk|db)$')   # the person's, and the
                                                                                         # copy of an upgraded database


def _backup_stamp(name, when=None):
    """The record of a backup: `at`, local time to the microsecond - for saying when, and for comparing with
    created_at, which is local time too (item 109); a record saved earlier in the same second is before it. A record
    from before item 109 also carries `utc`, which nothing reads now."""
    ts = when if when is not None else time.time()
    return {'at': datetime.fromtimestamp(ts).isoformat(), 'file': name, 'folder': str(_backups_dir())}


def _backup_last(session):
    """When the person last backed up: the recorded date, or - the first time, for backups made before it was recorded
    - the newest of their own backup files Groundwork can see, recorded then. None when there is neither."""
    rec = _setting_json(session, 'backup_last', None)
    if rec and rec.get('at'):
        return rec
    try:
        own = [f for f in _backups_dir().iterdir() if _OWN_BACKUP.match(f.name)]
    except OSError:
        own = []
    if not own:
        return None
    f = max(own, key=lambda x: x.stat().st_mtime)
    rec = {**_backup_stamp(f.name, f.stat().st_mtime), 'folder': str(f.parent), 'from_file': True}
    _set_setting(session, 'backup_last', json.dumps(rec))
    session.commit()
    return rec


def _backup_reminder(session, now=None):
    from core import sample_household as sh
    now = now or datetime.now()
    try:
        days = int(_setting_json(session, 'backup_remind_days', BACKUP_REMIND_DAYS))
    except (TypeError, ValueError):
        days = BACKUP_REMIND_DAYS
    days = days if days in BACKUP_REMIND_CHOICES else BACKUP_REMIND_DAYS
    snooze = _setting_json(session, 'backup_remind_snooze', None)
    last = _backup_last(session)
    since = datetime.fromisoformat(last['at']) if last else None
    added = {'transactions': 0, 'other': 0}
    q = lambda model: session.query(func.count(model.id)).filter(model.created_at > since).scalar() or 0
    if since:
        added['transactions'] = q(Transaction)
        added['other'] = q(Account) + q(DebtAccount) + q(BudgetItem)
    else:
        added['transactions'] = session.query(func.count(Transaction.id)).scalar() or 0
    age = (now - since).days if since else None
    flag = _get_setting(session, sh.SAMPLE_FLAG)
    sample = bool(flag and flag.value == 'true')
    snoozed = bool(snooze and now.date().isoformat() < snooze)
    changed = added['transactions'] + added['other'] > 0
    due = not sample and not snoozed and changed and (since is None or age >= days)
    out = {'every': days, 'choices': list(BACKUP_REMIND_CHOICES), 'last': last, 'days_since': age, 'added': added,
           'snoozed_until': snooze if snoozed else None, 'due': due, 'attention': []}
    if due:
        out['attention'] = [{'subject': 'backup', 'last': last['at'][:10] if last else None, 'days': age,
                             'transactions': added['transactions'], 'other': added['other'],
                             'fact': (last['at'][:10] if last else 'never')}]
    return out


@backup_bp.route('/reminder', methods=['GET'])
def backup_reminder_get():
    with db_session() as session:
        return ok(_backup_reminder(session))


@backup_bp.route('/reminder/snooze', methods=['POST'])
def backup_reminder_snooze():
    """"Remind me later": the reminder rests for BACKUP_SNOOZE_DAYS, then comes back if a backup is still due."""
    until = (date.today() + timedelta(days=BACKUP_SNOOZE_DAYS)).isoformat()
    with db_session() as session:
        _set_setting(session, 'backup_remind_snooze', json.dumps(until))
        session.commit()
        return ok({'snoozed_until': until})


@backup_bp.route('/reminder/every', methods=['POST'])
@require_json
def backup_reminder_every():
    try:
        days = int((request.get_json() or {}).get('days'))
    except (TypeError, ValueError):
        days = None
    if days not in BACKUP_REMIND_CHOICES:
        return err('Choose 3, 7, 14 or 30 days.', 400)
    with db_session() as session:
        _set_setting(session, 'backup_remind_days', json.dumps(days))
        session.commit()
        return ok({'every': days})


@backup_bp.route('', methods=['GET'])
@backup_bp.route('/list', methods=['GET'])
def list_backups():
    backup_dir = _backups_dir()
    files = []
    for f in sorted(list(backup_dir.glob('*.db')) + list(backup_dir.glob('*.gwbk')),
                    key=lambda x: x.stat().st_mtime, reverse=True):
        files.append({
            'filename': f.name,
            'size':     f.stat().st_size,
            'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            'encrypted': f.suffix == '.gwbk',
        })
    return ok(files)


@backup_bp.route('/protect', methods=['GET'])
def backup_protect_state():
    """B2-B4: whether backups are protected, whether this computer holds the key, and the vault's name."""
    from core import backup_crypto as bc, bank_vault
    with db_session() as session:
        prot = _protection(session)
        return ok({'set_up': bool(prot), 'confirmed': bool(prot and prot.get('confirmed')),
                   'key_on_this_computer': _vault_backup_key(prot) is not None,
                   'vault_available': bc.VAULT.available(), 'vault_name': bank_vault.vault_name() if bc.VAULT.available() else None,
                   'set_at': (prot or {}).get('set_at'), 'recovery_set_at': (prot or {}).get('recovery_set_at'),
                   'min_password': bc.MIN_PASSWORD})


def _check_password(p):
    from core import backup_crypto as bc
    if not isinstance(p, str) or len(p) < bc.MIN_PASSWORD:
        return f'The backup password needs at least {bc.MIN_PASSWORD} characters.'
    return None


@backup_bp.route('/protect/setup', methods=['POST'])
@require_json
def backup_protect_setup():
    """B3: a backup key made once, kept in this computer's vault, wrapped by the password and the recovery words. The
    words are returned this once and never stored by Groundwork."""
    import os as _os
    from core import backup_crypto as bc
    pw = (request.json or {}).get('password')
    why = _check_password(pw)
    if why:
        return err(why)
    with db_session() as session:
        if (_protection(session) or {}).get('confirmed'):
            return err('Backups are already protected. Change the password or make a new recovery key instead.')
        key = _os.urandom(32)
        words = bc.new_recovery_words()
        prot = bc.wrap(key, pw, words)
        stored = bc.VAULT.put(key)
        prot.update(confirmed=False, set_at=datetime.now().isoformat(timespec='seconds'),
                    recovery_set_at=datetime.now().isoformat(timespec='seconds'), in_vault=bool(stored))
        _set_setting(session, 'backup_protection', json.dumps(prot))
        session.commit()
        return ok({'words': words, 'key_on_this_computer': bool(stored)})


@backup_bp.route('/protect/confirm', methods=['POST'])
def backup_protect_confirm():
    """B3: the person showed they saved the words (the page checks three of them); backups are protected from here."""
    with db_session() as session:
        prot = _protection(session)
        if not prot:
            return err('Set up backup protection first.', 404)
        prot['confirmed'] = True
        _set_setting(session, 'backup_protection', json.dumps(prot))
        session.commit()
        return ok({'confirmed': True})


def _key_for_change(prot, body):
    """The backup key, from this computer's vault or the current password - never from anywhere else."""
    from core import backup_crypto as bc
    k = _vault_backup_key(prot)
    if k is not None:
        return k
    try:
        return bc.unwrap(prot, password=body.get('password'))[0]
    except bc.BackupLocked:
        return None


@backup_bp.route('/protect/password', methods=['POST'])
@require_json
def backup_protect_password():
    """B6: a new password for new backups. Older backups still open with the old one, or the recovery key."""
    from core import backup_crypto as bc
    body = request.json or {}
    why = _check_password(body.get('new_password'))
    if why:
        return err(why)
    with db_session() as session:
        prot = _protection(session)
        if not prot:
            return err('Set up backup protection first.', 404)
        key = _key_for_change(prot, body)
        if key is None:
            return err('Enter the current backup password.', 403)
        prot = bc.rewrap_password(prot, key, body['new_password'])
        prot['password_set_at'] = datetime.now().isoformat(timespec='seconds')
        _set_setting(session, 'backup_protection', json.dumps(prot))
        session.commit()
        return ok({'changed': True, 'note': 'New backups use the new password. Older backups still open with the old '
                                            'password, or with your recovery key.'})


@backup_bp.route('/protect/recovery', methods=['POST'])
def backup_protect_recovery():
    """B6: a new recovery key (the paper was lost). Shown once; older backups still need the old one or the password."""
    from core import backup_crypto as bc
    body = request.get_json(silent=True) or {}
    with db_session() as session:
        prot = _protection(session)
        if not prot:
            return err('Set up backup protection first.', 404)
        key = _key_for_change(prot, body)
        if key is None:
            return err('Enter the backup password.', 403)
        words = bc.new_recovery_words()
        prot = bc.rewrap_recovery(prot, key, words)
        prot.update(confirmed=False, recovery_set_at=datetime.now().isoformat(timespec='seconds'))
        _set_setting(session, 'backup_protection', json.dumps(prot))
        session.commit()
        return ok({'words': words, 'note': 'Older backups still need your old recovery key, or the backup password.'})


@backup_bp.route('/protect/reset', methods=['POST'])
@require_json
def backup_protect_reset():
    """B8: password forgotten and paper lost, but this is the computer: its vault opens the key, so a new password
    and new words are set. Nowhere else can do this."""
    from core import backup_crypto as bc
    body = request.json or {}
    why = _check_password(body.get('new_password'))
    if why:
        return err(why)
    with db_session() as session:
        prot = _protection(session)
        key = _vault_backup_key(prot)
        if key is None:
            return err('Only the computer that holds the backup key can reset its password.', 403)
        words = bc.new_recovery_words()
        prot = bc.rewrap_recovery(bc.rewrap_password(prot, key, body['new_password']), key, words)
        prot.update(confirmed=False, password_set_at=datetime.now().isoformat(timespec='seconds'),
                    recovery_set_at=datetime.now().isoformat(timespec='seconds'))
        _set_setting(session, 'backup_protection', json.dumps(prot))
        session.commit()
        return ok({'words': words})


def _backup_file(filename):
    """A file inside the backups folder, or None (no path climbs out)."""
    p = (_backups_dir() / (filename or '')).resolve()
    if not filename or not str(p).startswith(str(_backups_dir().resolve())) or not p.exists():
        return None
    return p


def _open_backup_bytes(blob, body):
    """The database bytes in a backup: plain (an old one) or sealed (by the vault, the password or the words)."""
    from core import backup_crypto as bc
    if not bc.is_encrypted(blob):
        if not blob.startswith(b'SQLite format 3'):
            raise bc.BackupDamaged('File does not appear to be a valid Groundwork backup')
        return blob, 'not encrypted'
    with db_session() as session:
        vk = _vault_backup_key(_protection(session))
    words = body.get('words')
    return bc.decrypt(blob, password=body.get('password') or None, words=words or None, vault_key=vk)


@backup_bp.route('/check', methods=['POST'])
@require_json
def backup_check():
    """B5: proves a backup opens and is undamaged, without restoring it."""
    from core import backup_crypto as bc
    body = request.json or {}
    p = _backup_file(body.get('filename'))
    if p is None:
        return err('Backup file not found', 404)
    try:
        data, how = _open_backup_bytes(p.read_bytes(), body)
    except bc.BackupLocked as e:
        return err(str(e), 403)
    except bc.BackupDamaged as e:
        return err(str(e), 422)
    return ok({'opens': True, 'opened_with': how, 'size': len(data)})


@backup_bp.route('/encrypt-old', methods=['POST'])
@require_json
def backup_encrypt_old():
    """B7: an old plain backup re-saved sealed, next to it. The plain one stays until the person deletes it."""
    from core import backup_crypto as bc
    p = _backup_file((request.json or {}).get('filename'))
    if p is None or p.suffix != '.db':
        return err('Backup file not found', 404)
    blob = p.read_bytes()
    if not blob.startswith(b'SQLite format 3'):
        return err('File does not appear to be a valid Groundwork backup', 400)
    with db_session() as session:
        prot = _protection(session)
        key = _vault_backup_key(prot)
    if not (prot and prot.get('confirmed')) or key is None:
        return err('Set up backup protection on this computer first.', 409)
    out = p.with_suffix('.gwbk')
    out.write_bytes(bc.encrypt_db(blob, key, prot))
    return ok({'filename': out.name, 'plain_kept': p.name})


@backup_bp.route('/delete', methods=['POST'])
@require_json
def backup_delete():
    """B7: deleting a backup is the person's tap, one file at a time; Groundwork never does it on its own."""
    p = _backup_file((request.json or {}).get('filename'))
    if p is None or p.suffix not in ('.db', '.gwbk'):
        return err('Backup file not found', 404)
    p.unlink()
    return ok({'deleted': p.name})



# ── Entry point ───────────────────────────────────────────────────────────────


# ── Sinking Funds ─────────────────────────────────────────────────────────────
sinking_funds_bp = Blueprint('sinking_funds', __name__)

def _serialize_sinking_fund(f) -> dict:
    from datetime import date
    today  = date.today()
    target = float(f.target_amount or 0)
    saved  = float(f.current_amount or 0)
    contrib = float(f.monthly_contribution or 0)

    # Auto-calculate monthly needed from deadline if no override
    monthly_needed = contrib
    if not contrib and f.deadline:
        try:
            d = date.fromisoformat(f.deadline)
            months = max(1, (d.year - today.year) * 12 + (d.month - today.month))
            monthly_needed = max(0, round((target - saved) / months, 2))
        except Exception:
            pass

    return {
        'id':                   f.id,
        'name':                 f.name,
        'target_amount':        target,
        'current_amount':       saved,
        'deadline':             f.deadline or '',
        'monthly_contribution': contrib,
        'monthly_needed':       monthly_needed,
        'note':                 f.note or '',
        'is_active':            f.is_active,
        'last_contributed_month': f.last_contributed_month or '',
        'purpose':              f.purpose or '',
        'pct_funded':           round((saved / target * 100) if target > 0 else 0, 1),
        # Legacy aliases for old JS code paths
        'balance':              saved,
        'target':               target,
        'monthlyContrib':       monthly_needed,
    }


def _fund_contributions(session, fund_id: int, months: int = 12):
    """The Historian's contribution events for one fund, inside the window."""
    cutoff = datetime.now() - timedelta(days=30 * months)
    matched = []
    for e in session.query(HistorianEntry).filter(
            HistorianEntry.event_category == 'sinking_fund_contribution_variance',
            HistorianEntry.created_at >= cutoff).all():
        try:
            ctx = json.loads(e.context_json or '{}')
        except (json.JSONDecodeError, TypeError):
            continue
        if str(ctx.get('sinking_fund_id')) == str(fund_id) and e.actual_value is not None:
            matched.append(e)
    return matched


def fund_contribution_break(session, fund_id: int, months: int = 12):
    """F.8 on what a fund has actually been fed: the latest break in its monthly contributions, or None.

    The series runs over COMPLETE months from the first contribution on record. A month with no contribution
    is a real zero here, unlike a month missing from a bank import: contributions are recorded in the app
    itself, so the record of them is complete, and a fund that stopped being fed is exactly the change F.8
    exists to see. The current month is left out because it is half over by definition.
    """
    from core.breaks import detect_break
    matched = _fund_contributions(session, fund_id, months)
    if not matched:
        return None
    first = min(e.created_at for e in matched)
    now = datetime.now()
    by_month = {}
    for e in matched:
        k = e.created_at.strftime('%Y-%m')
        by_month[k] = by_month.get(k, 0.0) + float(e.actual_value or 0)
    series, y, m = [], first.year, first.month
    while (y, m) < (now.year, now.month):
        k = f'{y}-{m:02d}'
        series.append((k, by_month.get(k, 0.0)))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return detect_break(series)


def fund_observed_monthly(session, fund_id: int, months: int = 12, since: str = None):
    """What a fund has actually been fed, per MONTH — not per contribution.

    The distinction is the same one that bit the recurring-cost lever: months
    with no contribution are not logged at all, so averaging the logged ones
    describes a saver who contributes every month regardless of whether they
    do. Three deposits across a year is $X/3 per contribution and $X/12 per
    month, and only the second answers "when does this finish".

    The span runs from the first contribution on record to now, so a fund
    started three months ago is not averaged across a year it has not lived.

    `since` ('YYYY-MM'), when a break in the contributions was found, starts
    the span there instead: only the months since the change may set the pace
    (F.8, BREAK_DETECTOR.md ruling 6). The earlier contributions stay in the
    record; they are simply not evidence of the pace being kept now.
    """
    matched = _fund_contributions(session, fund_id, months)
    if since:
        start = datetime(int(since[:4]), int(since[5:7]), 1)
        matched = [e for e in matched if e.created_at >= start]
    if not matched:
        return None, 0

    first = min(e.created_at for e in matched)
    if since:
        first = datetime(int(since[:4]), int(since[5:7]), 1)
    now = datetime.now()
    span = max(1, (now.year - first.year) * 12 + (now.month - first.month) + 1)
    total = sum(float(e.actual_value or 0) for e in matched)
    return round(total / span, 2), len(matched)


@sinking_funds_bp.route('/pace', methods=['GET'])
def sinking_funds_pace():
    """Where each fund lands at the pace it is actually being fed (§8).

    The pace badge these rows already carry says how reliably the plan is met.
    This says when the thing arrives, whether that clears the deadline, and
    what would move it — the causal half, which no reader here had.
    """
    from core.database import SinkingFund
    from core.solution import fund_pace

    today = date.today()
    with db_session() as session:
        cats = reallocation_candidates(session)
        rec = trim_candidates(session)
        out = []
        for f in session.query(SinkingFund).filter_by(is_active=True).order_by(SinkingFund.id).all():
            deadline_months = None
            if f.deadline:
                try:
                    d = date.fromisoformat(f.deadline)
                    deadline_months = ((d.year - today.year) * 12 + (d.month - today.month))
                except ValueError:
                    deadline_months = None

            planned = float(f.monthly_contribution or 0)
            if not planned and deadline_months and deadline_months > 0:
                planned = max(0.0, (float(f.target_amount or 0)
                                    - float(f.current_amount or 0)) / deadline_months)

            # F.8: a break in what the fund has been fed is a boundary - only the months since it may
            # set the pace (BREAK_DETECTOR.md ruling 6).
            brk = fund_contribution_break(session, f.id)
            observed, samples = fund_observed_monthly(session, f.id, since=brk['month'] if brk else None)
            pace = fund_pace(f.target_amount, f.current_amount, planned,
                             deadline_months=deadline_months,
                             observed_monthly=observed, samples=samples,
                             categories=cats, recurring=rec, since_break=brk)
            if pace:
                out.append({'id': f.id, 'name': f.name, 'pace': pace})
        return ok({'funds': out})


@sinking_funds_bp.route('', methods=['GET'])
def list_sinking_funds():
    with db_session() as session:
        from core.database import SinkingFund
        funds = session.query(SinkingFund).filter_by(is_active=True).order_by(SinkingFund.id).all()
        return ok([_serialize_sinking_fund(f) for f in funds])


@sinking_funds_bp.route('', methods=['POST'])
@require_json
def create_sinking_fund():
    body = request.json
    with db_session() as session:
        from core.database import SinkingFund
        f = SinkingFund(
            name=body.get('name','').strip(),
            target_amount=float(body.get('target_amount',0) or 0),
            current_amount=float(body.get('current_amount',0) or 0),
            deadline=body.get('deadline','') or None,
            monthly_contribution=float(body.get('monthly_contribution',0) or 0),
            note=body.get('note',''),
        )
        if not f.name:
            return err('Name is required')
        session.add(f)
        session.flush()
        session.commit()
        return ok(_serialize_sinking_fund(f))


@sinking_funds_bp.route('/<int:fund_id>', methods=['PATCH'])
@require_json
def update_sinking_fund(fund_id):
    body = request.json
    with db_session() as session:
        from core.database import SinkingFund
        f = session.get(SinkingFund, fund_id)
        if not f:
            return err('Fund not found', 404)
        if 'name' in body:               f.name = body['name'].strip()
        if 'target_amount' in body:      f.target_amount = float(body['target_amount'] or 0)
        if 'current_amount' in body:     f.current_amount = float(body['current_amount'] or 0)
        if 'deadline' in body:           f.deadline = body['deadline'] or None
        if 'monthly_contribution' in body: f.monthly_contribution = float(body['monthly_contribution'] or 0)
        if 'note' in body:               f.note = body['note']
        if 'is_active' in body:          f.is_active = bool(body['is_active'])
        if 'last_contributed_month' in body: f.last_contributed_month = body['last_contributed_month']
        session.commit()
        return ok(_serialize_sinking_fund(f))


@sinking_funds_bp.route('/<int:fund_id>', methods=['DELETE'])
def delete_sinking_fund(fund_id):
    with db_session() as session:
        from core.database import SinkingFund
        f = session.get(SinkingFund, fund_id)
        if not f:
            return err('Fund not found', 404)
        session.delete(f)
        session.commit()
        return ok({'deleted': fund_id})


@sinking_funds_bp.route('/<int:fund_id>/deposit', methods=['POST'])
@require_json
def deposit_sinking_fund(fund_id):
    """Add an amount to a sinking fund's current balance."""
    body = request.json
    amount = float(body.get('amount', 0) or 0)
    if amount <= 0:
        return err('Amount must be positive')
    with db_session() as session:
        from core.database import SinkingFund
        f = session.get(SinkingFund, fund_id)
        if not f:
            return err('Fund not found', 404)
        target = float(f.target_amount or 0)
        f.current_amount = min(target, float(f.current_amount or 0) + amount) if target > 0                            else float(f.current_amount or 0) + amount
        _log_sinking_fund_contribution_variance(session, f, amount)
        session.commit()
        return ok(_serialize_sinking_fund(f))


@sinking_funds_bp.route('/<int:fund_id>/confidence', methods=['GET'])
def sinking_fund_confidence(fund_id):
    """Sinking funds' mirror of the debt/net-worth/investments confidence
    routes — thin read of get_sinking_fund_confidence."""
    with db_session() as session:
        return ok(get_sinking_fund_confidence(session, fund_id))


@sinking_funds_bp.route('/<int:fund_id>/spend', methods=['POST'])
def spend_sinking_fund(fund_id):
    """Mark a fund as spent — reset balance to 0 for next cycle."""
    with db_session() as session:
        from core.database import SinkingFund
        f = session.get(SinkingFund, fund_id)
        if not f:
            return err('Fund not found', 404)
        f.current_amount       = 0
        f.last_contributed_month = ''
        session.commit()
        return ok(_serialize_sinking_fund(f))


@sinking_funds_bp.route('/auto-credit', methods=['POST'])
def auto_credit_sinking_funds():
    """
    Auto-credit monthly contributions for the current month.
    Called on app boot or from the budget page.
    Idempotent — only credits once per month per fund.
    """
    from datetime import date
    this_month = date.today().strftime('%Y-%m')
    credited   = 0
    with db_session() as session:
        from core.database import SinkingFund
        funds = session.query(SinkingFund).filter_by(is_active=True).all()
        for f in funds:
            if f.last_contributed_month == this_month:
                continue  # already credited this month
            contrib = float(f.monthly_contribution or 0)
            if contrib <= 0:
                # Auto-calculate from deadline
                if f.deadline:
                    try:
                        d    = date.fromisoformat(f.deadline)
                        today = date.today()
                        months = max(1, (d.year-today.year)*12+(d.month-today.month))
                        contrib = max(0, (float(f.target_amount or 0) - float(f.current_amount or 0)) / months)
                    except Exception:
                        pass
            if contrib > 0:
                target = float(f.target_amount or 0)
                f.current_amount = min(target, float(f.current_amount or 0) + contrib) if target > 0                                    else float(f.current_amount or 0) + contrib
                f.last_contributed_month = this_month
                # Only a real logged variance when monthly_contribution was
                # actually set — _log_sinking_fund_contribution_variance
                # itself no-ops otherwise, but the deadline-derived fallback
                # contrib computed above would make expected==actual here by
                # construction, which isn't a real signal either way.
                _log_sinking_fund_contribution_variance(session, f, contrib)
                credited += 1
        session.commit()
    return ok({'credited': credited, 'month': this_month})


# ── College funds (Historian logging only — balance itself is managed
# client-side via the generic /api/settings college_funds_json blob, same
# as it always was; this route exists purely so a contribution's "expected"
# figure comes from that same server-held blob rather than a client-passed
# number, matching how every other confidence feature in this file sources
# its expected value) ────────────────────────────────────────────────────
college_funds_bp = Blueprint('college_funds', __name__)


@college_funds_bp.route('/<fund_id>/contribute', methods=['POST'])
@require_json
def log_college_fund_contribution(fund_id):
    """Body: { amount: float }. Looks up the fund's own monthlyContrib from
    college_funds_json for 'expected' — never trusts a client-passed
    expectation for the number that gets logged as fact."""
    amount = float(request.json.get('amount', 0) or 0)
    if amount <= 0:
        return err('Amount must be positive')
    with db_session() as session:
        row = session.query(AppSetting).filter_by(key='college_funds_json').first()
        try:
            funds = json.loads(row.value) if row and row.value else []
        except (json.JSONDecodeError, TypeError):
            funds = []
        fund = next((f for f in funds if str(f.get('id')) == str(fund_id)), None)
        if not fund:
            return err('Fund not found', 404)
        expected = float(fund.get('monthlyContrib', 0) or 0)
        _log_college_fund_contribution_variance(session, fund_id, expected, amount)
        session.commit()
        return ok({'logged': True})


@college_funds_bp.route('/<fund_id>/confidence', methods=['GET'])
def college_fund_confidence(fund_id):
    """College funds' mirror of the debt/net-worth/investments/sinking-fund
    confidence routes — thin read of get_college_fund_confidence."""
    with db_session() as session:
        return ok(get_college_fund_confidence(session, fund_id))


# ── Gift Budget in tables (GIFT_BUDGET.md, item 74) ──────────────────────────
# The page reads and writes here. The old /api/gift routes, which read the settings, were removed once nothing called
# them; the settings themselves are kept as the record of what was carried over (G8).
gifts_bp = Blueprint('gifts', __name__)


def _gift_today():
    return date.today()


def _gift_occasion_dict(session, o, people, today):
    from core import gifts as gf
    from core.database import GiftShare
    nxt = gf.next_occurrence(o.type, o.date, today)
    d = {'id': o.id, 'person_id': o.person_id, 'type': o.type, 'name': o.name or '', 'date': o.date or '',
         'budget': round(float(o.budget or 0), 2), 'note': o.note or '', 'shared': bool(o.shared),
         'actual_spent': o.actual_spent, 'spent_at': o.spent_at,
         'label': gf.occasion_label(o, people.get(o.person_id)),
         'next': nxt.isoformat() if nxt else None, 'days': (nxt - today).days if nxt else None,
         'offer_date': (lambda w: w.isoformat() if w else None)(gf.offer_date(o, today))}
    if o.shared:
        shares = session.query(GiftShare).filter_by(occasion_id=o.id).order_by(GiftShare.id).all()
        split = gf.split_shared(o.budget, [(s.person_id, s.fixed_amount) for s in shares])
        d['shares'] = [{'id': s.id, 'person_id': s.person_id,
                        'name': people[s.person_id].name if s.person_id in people else '',
                        'fixed_amount': s.fixed_amount, 'amount': split['per_person'].get(s.person_id, 0.0)}
                       for s in shares]
        d['split'] = {k: v for k, v in split.items() if k != 'per_person'}
    return d


def _gift_fund_dict(session, f):
    from core import gifts as gf
    d = _serialize_sinking_fund(f)
    d['last_spend'] = gf.last_spend(session, f.id)
    return d


@gifts_bp.route('', methods=['GET'])
def gifts_state():
    """Everything the Gift page shows: people with their occasions, shared occasions, gift funds, the seasonal
    funds still to move, and the year's plan with its working."""
    from core import gifts as gf
    from core.database import GiftPerson, GiftOccasion
    today = _gift_today()
    with db_session() as session:
        gf.ensure_imported(session)
        session.commit()
        people = {p.id: p for p in session.query(GiftPerson).order_by(GiftPerson.id).all()}
        occs = session.query(GiftOccasion).order_by(GiftOccasion.id).all()
        out_people = []
        for p in people.values():
            out_people.append({'id': p.id, 'name': p.name, 'relationship': p.relationship or 'other',
                               'occasions': [_gift_occasion_dict(session, o, people, today)
                                             for o in occs if o.person_id == p.id and not o.shared]})
        return ok({
            'people': out_people,
            'shared': [_gift_occasion_dict(session, o, people, today) for o in occs if o.shared],
            'funds': [_gift_fund_dict(session, f) for f in gf.gift_funds(session)],
            'seasons_to_move': [{'id': s.get('id'), 'name': s.get('name'), 'target': s.get('target'),
                                 'saved': s.get('saved'), 'deadline': s.get('deadline')}
                                for s in gf.seasons_to_move(session)],
            'plan': gf.year_plan(session, today),
        })


@gifts_bp.route('/people', methods=['POST'])
@require_json
def gifts_add_person():
    from core import gifts as gf
    from core.database import GiftPerson
    name = (request.json.get('name') or '').strip()
    if not name:
        return err('Enter a name')
    rel = request.json.get('relationship')
    with db_session() as session:
        gf.ensure_imported(session)
        p = GiftPerson(name=name[:120], relationship=rel if rel in gf.RELATIONSHIPS else 'other')
        session.add(p)
        session.commit()
        return ok({'id': p.id})


@gifts_bp.route('/people/<int:pid>', methods=['PATCH'])
@require_json
def gifts_edit_person(pid):
    from core import gifts as gf
    from core.database import GiftPerson
    with db_session() as session:
        p = session.get(GiftPerson, pid)
        if not p:
            return err('Person not found', 404)
        if 'name' in request.json and (request.json['name'] or '').strip():
            p.name = request.json['name'].strip()[:120]
        if 'relationship' in request.json:
            rel = request.json['relationship']
            p.relationship = rel if rel in gf.RELATIONSHIPS else 'other'
        session.commit()
        return ok({'id': p.id})


@gifts_bp.route('/people/<int:pid>', methods=['DELETE'])
def gifts_delete_person(pid):
    from core.database import GiftPerson, GiftOccasion, GiftShare
    with db_session() as session:
        p = session.get(GiftPerson, pid)
        if not p:
            return err('Person not found', 404)
        own = [o.id for o in session.query(GiftOccasion).filter_by(person_id=pid).all()]
        if own:
            session.query(GiftShare).filter(GiftShare.occasion_id.in_(own)).delete(synchronize_session=False)
            session.query(GiftOccasion).filter(GiftOccasion.id.in_(own)).delete(synchronize_session=False)
        session.query(GiftShare).filter_by(person_id=pid).delete(synchronize_session=False)
        session.delete(p)
        session.commit()
        return ok({'deleted': pid})


@gifts_bp.route('/occasions', methods=['POST'])
@require_json
def gifts_add_occasion():
    """A person's occasion ({person_id, type, date}) or a shared one ({shared: true, name, type, date})."""
    from core import gifts as gf
    from core.database import GiftPerson, GiftOccasion
    b = request.json
    typ = b.get('type') if b.get('type') in gf.TYPE_LABELS else 'other'
    date_s = (b.get('date') or '').strip()[:10]
    if date_s and gf._parse(date_s) is None:
        return err('Use a date like 2026-12-25')
    with db_session() as session:
        gf.ensure_imported(session)
        if b.get('shared'):
            name = (b.get('name') or '').strip() or gf.TYPE_LABELS[typ].capitalize()
            o = GiftOccasion(person_id=None, shared=True, type=typ, name=name[:120], date=date_s,
                             budget=max(0.0, float(b.get('budget') or 0)))
        else:
            p = session.get(GiftPerson, int(b.get('person_id') or 0))
            if not p:
                return err('Person not found', 404)
            if typ != 'other' and session.query(GiftOccasion).filter_by(person_id=p.id, type=typ).first():
                return err(f'{gf.TYPE_LABELS[typ].capitalize()} is already added')
            o = GiftOccasion(person_id=p.id, type=typ, name=(b.get('name') or '').strip()[:120], date=date_s)
        session.add(o)
        session.commit()
        return ok({'id': o.id})


@gifts_bp.route('/occasions/<int:oid>', methods=['PATCH'])
@require_json
def gifts_edit_occasion(oid):
    from core import gifts as gf
    from core.database import GiftOccasion
    b = request.json
    with db_session() as session:
        o = session.get(GiftOccasion, oid)
        if not o:
            return err('Occasion not found', 404)
        if 'budget' in b:
            o.budget = max(0.0, float(b.get('budget') or 0))
        if 'date' in b:
            ds = (b.get('date') or '').strip()[:10]
            if ds and gf._parse(ds) is None:
                return err('Use a date like 2026-12-25')
            o.date = ds
        if 'name' in b:
            o.name = (b.get('name') or '').strip()[:120]
        if 'note' in b:
            o.note = b.get('note') or ''
        session.commit()
        return ok({'id': o.id})


@gifts_bp.route('/occasions/<int:oid>', methods=['DELETE'])
def gifts_delete_occasion(oid):
    from core.database import GiftOccasion, GiftShare
    with db_session() as session:
        o = session.get(GiftOccasion, oid)
        if not o:
            return err('Occasion not found', 404)
        session.query(GiftShare).filter_by(occasion_id=oid).delete(synchronize_session=False)
        session.delete(o)
        session.commit()
        return ok({'deleted': oid})


def _log_gift_spend(session, o, actual, from_ledger=False, charges=0):
    if not o.budget or o.budget <= 0:
        return
    log_historian_event(session, 'gift_occasion_variance', expected_value=round(float(o.budget), 2),
                        actual_value=round(float(actual), 2),
                        context={'gift_occasion_id': o.id, 'gift_person_id': o.person_id,
                                 'occasion_id': o.legacy_id or o.id, 'from_ledger': from_ledger,
                                 'charges': charges})


@gifts_bp.route('/occasions/<int:oid>/spend', methods=['POST'])
@require_json
def gifts_occasion_spend(oid):
    """The "$" button: what the occasion cost, typed by the person."""
    from core.database import GiftOccasion
    actual = request.json.get('actual_spent')
    try:
        actual = round(float(actual), 2)
    except (TypeError, ValueError):
        return err('actual_spent is required')
    if actual < 0:
        return err('actual_spent is required')
    with db_session() as session:
        o = session.get(GiftOccasion, oid)
        if not o:
            return err('Occasion not found', 404)
        o.actual_spent = actual
        o.spent_at = _gift_today().isoformat()
        o.spent_txn_ids = ''
        _log_gift_spend(session, o, actual)
        session.commit()
        return ok({'actual_spent': actual})


@gifts_bp.route('/occasions/<int:oid>/charges', methods=['GET'])
def gifts_occasion_charges(oid):
    """G4: the gift charges in the weeks before the occasion, listed for the person to pick from."""
    from core import gifts as gf
    from core.database import GiftOccasion, GiftPerson
    today = _gift_today()
    with db_session() as session:
        o = session.get(GiftOccasion, oid)
        if not o:
            return err('Occasion not found', 404)
        out = gf.charges_for(session, o, today)
        out['label'] = gf.occasion_label(o, session.get(GiftPerson, o.person_id) if o.person_id else None)
        return ok(out)


@gifts_bp.route('/occasions/<int:oid>/charges', methods=['POST'])
@require_json
def gifts_occasion_use_charges(oid):
    """G4, on the person's yes: the charges they picked become what the occasion cost."""
    from core import gifts as gf
    from core.database import GiftOccasion
    with db_session() as session:
        o = session.get(GiftOccasion, oid)
        if not o:
            return err('Occasion not found', 404)
        ids = request.json.get('txn_ids') or []
        spent, why = gf.use_charges(session, o, ids, _gift_today())
        if why:
            return err(why)
        _log_gift_spend(session, o, spent, from_ledger=True, charges=len(ids))
        session.commit()
        return ok({'actual_spent': spent})


@gifts_bp.route('/occasions/<int:oid>/shares', methods=['POST'])
@require_json
def gifts_add_share(oid):
    """G6: a person under a shared occasion, with a fixed amount or none (an even part of the rest)."""
    from core.database import GiftOccasion, GiftPerson, GiftShare
    b = request.json
    with db_session() as session:
        o = session.get(GiftOccasion, oid)
        if not o or not o.shared:
            return err('Shared occasion not found', 404)
        p = session.get(GiftPerson, int(b.get('person_id') or 0))
        if not p:
            return err('Person not found', 404)
        if session.query(GiftShare).filter_by(occasion_id=oid, person_id=p.id).first():
            return err(f'{p.name} is already in it')
        fixed = b.get('fixed_amount')
        s = GiftShare(occasion_id=oid, person_id=p.id,
                      fixed_amount=None if fixed in (None, '') else max(0.0, float(fixed)))
        session.add(s)
        session.commit()
        return ok({'id': s.id})


@gifts_bp.route('/shares/<int:sid>', methods=['PATCH'])
@require_json
def gifts_edit_share(sid):
    from core.database import GiftShare
    with db_session() as session:
        s = session.get(GiftShare, sid)
        if not s:
            return err('Not found', 404)
        fixed = request.json.get('fixed_amount')
        s.fixed_amount = None if fixed in (None, '') else max(0.0, float(fixed))
        session.commit()
        return ok({'id': s.id})


@gifts_bp.route('/shares/<int:sid>', methods=['DELETE'])
def gifts_delete_share(sid):
    from core.database import GiftShare
    with db_session() as session:
        s = session.get(GiftShare, sid)
        if not s:
            return err('Not found', 404)
        session.delete(s)
        session.commit()
        return ok({'deleted': sid})


@gifts_bp.route('/set-aside', methods=['POST'])
@require_json
def gifts_set_aside():
    """G1, on a tap: one "Gifts (set aside)" budget line at one of the plan's amounts."""
    from core import gifts as gf
    with db_session() as session:
        line, why = gf.apply_set_aside(session, request.json.get('monthly'), _gift_today())
        if why:
            return err(why)
        session.commit()
        return ok({'id': line.id, 'name': line.name, 'amount': round(float(line.amount), 2)})


@gifts_bp.route('/funds', methods=['POST'])
@require_json
def gifts_add_fund():
    """G2: a gift fund is a sinking fund marked 'gift'; its monthly amount adds itself like every fund's."""
    from core import gifts as gf
    from core.database import SinkingFund
    b = request.json
    name = (b.get('name') or '').strip()
    target = float(b.get('target_amount') or 0)
    if not name:
        return err('Enter a fund name')
    if target <= 0:
        return err('Enter a target amount')
    with db_session() as session:
        f = SinkingFund(name=name[:120], target_amount=target, current_amount=0.0,
                        deadline=(b.get('deadline') or None), monthly_contribution=float(b.get('monthly_contribution') or 0),
                        purpose=gf.GIFT_PURPOSE)
        session.add(f)
        session.commit()
        return ok(_gift_fund_dict(session, f))


@gifts_bp.route('/funds/<int:fid>/spent', methods=['POST'])
@require_json
def gifts_fund_spent(fid):
    """G3: "Mark spent" records the target and what was spent, then sets the fund back to $0 for next time."""
    from core import gifts as gf
    from core.database import SinkingFund
    try:
        spent = round(float(request.json.get('spent')), 2)
    except (TypeError, ValueError):
        return err('Enter what was spent')
    if spent < 0:
        return err('Enter what was spent')
    with db_session() as session:
        f = session.get(SinkingFund, fid)
        if not f:
            return err('Fund not found', 404)
        target = float(f.target_amount or 0)
        gf.mark_fund_spent(session, f, spent, _gift_today())
        log_historian_event(session, 'gift_fund_spent', expected_value=round(target, 2), actual_value=spent,
                            context={'sinking_fund_id': f.id})
        session.commit()
        return ok(_gift_fund_dict(session, f))


@gifts_bp.route('/seasons/move', methods=['POST'])
def gifts_move_seasons():
    """G2, on a tap: the old seasonal funds become gift funds, keeping what each held."""
    from core import gifts as gf
    with db_session() as session:
        moved = gf.move_seasons(session)
        session.commit()
        return ok({'moved': moved})


@gifts_bp.route('/upcoming', methods=['GET'])
def gifts_upcoming():
    """G5: budgeted occasions in the next 30 days, for the dashboard's coming-up list."""
    from core import gifts as gf
    with db_session() as session:
        gf.ensure_imported(session)
        session.commit()
        return ok({'occasions': gf.upcoming(session, _gift_today())})


# ── Quicken import endpoint ───────────────────────────────────────────────────
from flask import Blueprint
import_bp = Blueprint('import', __name__)

@import_bp.route('/quicken', methods=['POST'])
def import_quicken_file():
    """
    Deprecated. The legacy /api/import/quicken endpoint depended on the
    no-longer-shipped quicken_import.py module. The modern flow uses
    /api/import/preview followed by /api/import/commit, which routes
    every file type (CSV / QFX / OFX / QIF / TXT) through
    bank_importer.detect_and_parse(). Returning a clear 410 so any old
    callers know to migrate rather than silently breaking.
    """
    return err(
        'This endpoint is deprecated. Use /api/import/preview followed '
        'by /api/import/commit instead.',
        410
    )


# ── Bank CSV import endpoint  (Phase 3B) ─────────────────────────────────────
bank_import_bp = Blueprint('bank_import', __name__)

@bank_import_bp.route('/preview', methods=['POST'])
def bank_import_preview():
    """
    Accept a CSV/OFX/QIF file, detect the bank, and return a preview
    without writing anything to the database.

    Returns: { bank, records_count, category_summary, sample_records, warnings }
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    if 'file' not in request.files:
        return err('No file uploaded')

    f        = request.files['file']
    text     = f.read().decode('utf-8', errors='replace')
    filename = f.filename or 'import.csv'

    try:
        # bank_importer.detect_and_parse now handles CSV/QFX/OFX/QIF/TXT
        # internally — dispatch by content shape, not extension, so a .txt
        # holding CSV or a .csv that's actually OFX still parses correctly.
        from bank_importer import detect_and_parse, get_category_summary
        records, bank, warnings = detect_and_parse(text, filename)

        return ok({
            'bank':             bank,
            'records_count':    len(records),
            'category_summary': get_category_summary(records),
            'records':          records,        # full list — client stores for commit step
            'sample_records':   records[:5],    # first 5 for preview table display only
            'warnings':         warnings[:10],
        })

    except Exception as e:
        logging.exception('Bank import preview failed')
        return err(f'Preview failed: {e}', 500)


def _record_rb(r):
    """Parse a preview record's running_balance; None when absent/zero/garbage."""
    v = r.get('running_balance')
    try:
        f = float(v)
        return f if f != 0 else None
    except (TypeError, ValueError):
        return None


def _normalize_record_order(records):
    """
    Insert imported rows in true chronological order regardless of how the
    bank orders its file. (d21 field-caught: Superior CU exports newest-first;
    same-day rows carry no intraday timestamp, so the Ledger's same-day order
    is insertion order — file order — which reversed each day's chronology:
    the deposit displayed where the day's newest transaction belonged.)

    Stage 1 — file direction: if the date sequence runs newest→oldest,
    reverse the whole file.
    Stage 2 — within each same-date group, order by the bank's own
    running-balance arithmetic when every row in the group carries one:
    undoing a row (running_balance + amount for a debit, − amount for a
    credit) yields its balance-before; the oldest remaining row is the one
    whose balance-before is not any remaining row's running balance. A break
    in the chain keeps stage-1 order for the rest of that group — best
    effort, never worse than the old behavior.
    """
    if len(records) < 2:
        return records
    dated = [r for r in records if r.get('date')]
    if len(dated) >= 2 and dated[0]['date'] > dated[-1]['date']:
        records = list(reversed(records))

    out, i = [], 0
    while i < len(records):
        j = i
        while j < len(records) and records[j].get('date') == records[i].get('date'):
            j += 1
        group = records[i:j]
        if len(group) > 1 and all(_record_rb(r) is not None for r in group):
            def prior(r):
                amt = abs(float(r.get('amount', 0) or 0))
                rb  = _record_rb(r)
                return round(rb + amt, 2) if (r.get('type', 'debit') == 'debit') else round(rb - amt, 2)
            ordered, remaining = [], list(group)
            while remaining:
                rbs = [round(_record_rb(r), 2) for r in remaining]
                oldest = [r for k, r in enumerate(remaining)
                          if not any(abs(prior(r) - b) <= 0.005
                                     for m, b in enumerate(rbs) if m != k)]
                if len(oldest) != 1:
                    ordered.extend(remaining)   # chain broken — keep stage-1 order
                    break
                ordered.append(oldest[0])
                remaining.remove(oldest[0])
            group = ordered
        out.extend(group)
        i = j
    return out


_DESC_NOISE_PREFIX = re.compile(r'^\s*(withdrawal|deposit|purchase|payment)\s+', re.IGNORECASE)


def _normalize_desc(s: str) -> str:
    s = _DESC_NOISE_PREFIX.sub('', (s or '').lower())
    return re.sub(r'\s+', ' ', s).strip()


def _descriptions_match_fuzzy(a: str, b: str) -> bool:
    """True if two transaction descriptions likely describe the same real
    transaction. Confirmed in the field (2026-07-25): CSV and QFX/OFX
    exports of the SAME transaction from the SAME bank differ in two ways
    that broke the old exact-match dedup — CSV prepends a generic
    'Withdrawal '/'Deposit ' word that QFX omits, and QFX truncates long
    ACH memo/name fields to a fixed max length while CSV does not (a real
    Capital One ACH payment's trace number came through as
    '...45780' from QFX vs the untruncated '...457802' from CSV). An
    entire QFX re-import went through as ~880 new "duplicate" rows because
    of this — every one was an exact-match miss.
    Exact match after stripping the noise prefix covers the common case;
    prefix-containment (one is a truncated copy of the other) covers the
    truncation case. The 20-char floor keeps two short, genuinely
    different transactions that happen to share a common prefix (e.g.
    "Interest Charge" vs "Interest Charge Fee") from being merged — only
    long, specific ACH/wire-style descriptions get the fuzzy match."""
    na, nb = _normalize_desc(a), _normalize_desc(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    return len(shorter) >= 20 and longer.startswith(shorter)


_SHA256_HEX = re.compile(r'^[0-9a-f]{64}$')


def _import_source_file(raw):
    """The file an import came from, as the page reports it: name, content hash, origin.

    The hash is CORRESPONDENCE evidence (the artefact ruling), never identity, and is kept only
    when it is a well-formed SHA-256; anything else is recorded as unknown rather than guessed.
    """
    raw = raw if isinstance(raw, dict) else {}
    name = raw.get('name') if isinstance(raw.get('name'), str) else ''
    sha = raw.get('sha256') if isinstance(raw.get('sha256'), str) else ''
    origin = raw.get('origin') if raw.get('origin') in ('watcher', 'manual') else None
    return {
        'file_name': name.strip()[:255] or None,
        'content_sha256': sha.lower() if _SHA256_HEX.match(sha.lower()) else None,
        'origin': origin,
    }


def _log_import_committed(session, source, account_id, account_name, records,
                          created, duplicates, errors, held=0):
    """H1: one 'import_committed' Historian event per commit. The context is a fixed set of
    keys - what was imported, from which file, into which account - and never the file's
    content. Read by nothing that builds a model prompt (s127 pins it)."""
    dates = sorted(r['date'] for r in records
                   if isinstance(r, dict) and isinstance(r.get('date'), str) and len(r['date']) == 10)
    log_historian_event(session, 'import_committed', context={
        'file_name':      source['file_name'],
        'content_sha256': source['content_sha256'],
        'origin':         source['origin'],
        'account_id':     account_id,
        'account_name':   account_name,
        'records':        len(records),
        'created':        created,
        'duplicates':     duplicates,
        'held':           held,          # item 93 B5: look-alikes held for the person, never dropped
        'errors':         errors,
        'first_date':     dates[0] if dates else None,
        'last_date':      dates[-1] if dates else None,
    })


def _import_insert(session, account_id, rec, batch):
    """One line, inserted exactly as the import commit does - used for a held line brought in on a yes (item 93 B5)."""
    try:
        txn_date = date.fromisoformat(rec['date'])
        amount = abs(float(rec.get('amount', 0)))
        description = (rec.get('description') or '').strip()
        cat_name = rec.get('category', 'Other')
        cat = session.query(Category).filter(func.lower(Category.name) == cat_name.lower()).first() \
            or session.query(Category).filter(func.lower(Category.name) == 'other').first()
        posted_raw = rec.get('posted_date')
        t = Transaction(account_id=account_id, category_id=cat.id if cat else None, date=txn_date,
                        description=description, amount=amount, type=rec.get('type', 'debit'),
                        cleared=bool(rec.get('cleared', True)), memo=rec.get('memo', ''),
                        merchant=rec.get('merchant', '') or description,
                        posted_date=date.fromisoformat(posted_raw) if posted_raw else txn_date,
                        running_balance=rec.get('running_balance'), mcc=rec.get('mcc', ''),
                        card_last4=rec.get('card_last4', ''), import_id=(rec.get('fitid') or '').strip(),
                        source=rec.get('source', 'csv'), check_number=rec.get('check_number', ''), import_batch=batch,
                        pending=bool(rec.get('pending')))
        if t.pending:
            t.cleared = False
        session.add(t)
        session.flush()
        return t
    except Exception:
        return None


@bank_import_bp.route('/pending-pairs', methods=['GET'])
def import_pending_pairs():
    """Item 93 B9: posted lines that may be a pending line already here - each waits for the person's answer."""
    from core import bank_versions
    with db_session() as session:
        return ok({'pairs': bank_versions.suggestions(session)})


@bank_import_bp.route('/pending-pairs/<int:pair_id>', methods=['POST'])
@require_json
def import_pending_pair_answer(pair_id):
    """{answer: 'yes' | 'no'}. Yes: both kept, the pending line set aside with its own date and amount, the posted one
    current for totals. No: both stay in the ledger, and this pair is not asked again."""
    from core import bank_versions
    ans = (request.json or {}).get('answer')
    if ans not in ('yes', 'no'):
        return err('answer yes or no')
    with db_session() as session:
        p, problem = bank_versions.answer(session, pair_id, ans == 'yes')
        if problem:
            return err(problem)
        session.commit()
        return ok({'state': p.state, 'pairs': bank_versions.suggestions(session)})


@bank_import_bp.route('/held', methods=['GET'])
def import_held_list():
    """Item 93 B5: lines imports held back because they only looked like ones already here."""
    from core import import_custody as ic
    with db_session() as session:
        return ok({'held': ic.held_list(session)})


@bank_import_bp.route('/held/batch', methods=['POST'])
@require_json
def import_held_resolve_batch():
    """{batch, answer} - one decision for every line one import held back (the listed set, on the person's yes)."""
    from core import import_custody as ic
    body = request.json or {}
    with db_session() as session:
        n, problem = ic.resolve_batch(session, str(body.get('batch') or ''), body.get('answer'), _import_insert)
        if problem:
            return err(problem)
        session.commit()
        return ok({'resolved': n, 'held': ic.held_list(session)})


@bank_import_bp.route('/held/<int:held_id>', methods=['POST'])
@require_json
def import_held_resolve(held_id):
    """{answer: 'bring_in' | 'same'} - only the person decides; the held line stays on record with the decision."""
    from core import import_custody as ic
    with db_session() as session:
        h, problem = ic.resolve(session, held_id, (request.json or {}).get('answer'), _import_insert)
        if problem:
            return err(problem)
        session.commit()
        return ok({'resolved': h.resolved, 'brought_in_id': h.brought_in_id, 'held': ic.held_list(session)})


@bank_import_bp.route('/commit', methods=['POST'])
@require_json
def bank_import_commit():
    """
    Commit a previously-previewed import.
    Body: { records: [...], account_id: int, account_name: str }
    Each record may have user-overridden category from the preview UI.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    body       = request.json
    records    = body.get('records', [])
    account_id = body.get('account_id')
    acct_name  = body.get('account_name', 'Imported').strip()
    source     = _import_source_file(body.get('source_file'))

    # Nothing to import is not an import. Without this, a commit carrying no
    # records still falls through to the account resolution below, finds no
    # account_id and no account_name, and creates one called "Imported" - so a
    # failed or empty import leaves a stray empty account behind on the
    # accounts page, with nothing in it to explain where it came from.
    if not records:
        return err('no records to import')

    # d21: insert in true chronological order so same-day Ledger order and
    # id-based tiebreaks reflect what actually happened at the bank.
    records = _normalize_record_order(records)

    created = duplicates = errors = 0
    import uuid as _uuid
    from core import import_custody as _ic
    batch = _uuid.uuid4().hex          # item 93 B7: this import's lines, together
    held_rows = []                     # item 93 B5: look-alikes held back, never dropped
    from core import bank_versions as _bv
    pairs_asked = []                   # item 93 B9: posted lines that may be a pending one - asked, never decided
    pairs_made = 0                     # item 93 B9: posted lines the bank's own id paired with their pending line
    # BUG FIX (July 6): tracks (amount, type) for every transaction actually
    # created in THIS import batch — needed below because the debt-balance
    # auto-update only ever trusted the bank's own reported running_balance
    # column, which many real exports (confirmed: Capital One) simply don't
    # include. When that's the case, the update silently did nothing at
    # all — not a wrong direction, a complete no-op. Confirmed in the
    # field: a real Capital One charge posted correctly to the Ledger, but
    # the linked debt card's balance never moved either way.
    new_txn_deltas = []

    with db_session() as session:
        # Resolve account
        if account_id:
            account_id = int(account_id)
        else:
            from core.database import Account
            acct = session.query(Account).filter_by(name=acct_name).first()
            if not acct:
                acct = Account(name=acct_name, type='checking')
                session.add(acct)
                session.flush()
            account_id = acct.id

        # Item 83 T4: the person's own category names, their remembered answers for imported names, and the names
        # that matched nothing (kept, with their rows, to ask about - never left silently in Other)
        _tidy_names = [c.name for c in session.query(Category).all()]
        _tidy_aliases = _setting_json(session, 'category_aliases_json', {}) or {}
        _tidy_unmatched = {}
        # Item 98 (core/new_vendor.py): a vendor never seen before, filed by the bank's own label, is asked about once.
        # Never on an account's first import (N3): its whole history is new.
        from core import new_vendor as _nv
        _nv_on = _nv.account_had_rows(session, account_id)
        _nv_rules = _setting_json(session, 'import_rules_json', []) or []
        _nv_found, _nv_new = {}, {}

        for rec in records:
            try:
                txn_date    = date.fromisoformat(rec['date'])
                amount      = abs(float(rec.get('amount', 0)))
                description = (rec.get('description') or '').strip()
                txn_type    = rec.get('type', 'debit')
                cat_name    = rec.get('category', 'Other')
                fitid       = (rec.get('fitid') or '').strip()

                if not description or amount <= 0:
                    continue

                # ── Dedup ──────────────────────────────────────────────────
                # QFX/OFX files contain a FITID (Financial Institution
                # Transaction ID) — a globally unique ID the bank assigns to
                # each transaction. Check it first when available: it's exact
                # and survives date/description changes, so it's the cheapest
                # and most precise signal. But it is NOT sufficient on its
                # own — a row's FITID can only ever match another row that
                # also has a FITID, so a QFX row reimporting a transaction
                # that was originally imported via CSV (which has no FITID)
                # would never find its existing match here and always fell
                # through to being created as a duplicate. So: always fall
                # back to the date+type+amount+fuzzy-description match below
                # when the FITID check doesn't find anything, regardless of
                # whether this row has a FITID or not.
                #
                # The fuzzy description match (see _descriptions_match_fuzzy)
                # tolerates CSV/QFX formatting differences confirmed in the
                # field (2026-07-25): CSV prepends a generic "Withdrawal "/
                # "Deposit " word that QFX omits, and QFX truncates long ACH
                # memo/trace-number text to a fixed max length while CSV does
                # not — an exact string match silently missed these every
                # time. Same-day same-amount transactions with a genuinely
                # different (and not merely truncated) description — e.g. two
                # Clark Gas fill-ups — still both import; see the 20-char
                # shared-prefix floor in _descriptions_match_fuzzy.
                is_pending  = bool(rec.get('pending'))
                existing = None
                if fitid:
                    existing = session.query(Transaction).filter(
                        Transaction.account_id == account_id,
                        Transaction.import_id  == fitid,
                    ).first()
                posts_pending = None
                if existing and existing.pending and not is_pending:
                    # Item 93 B9: the bank's own id, once pending and now posted - the bank's statement changed.
                    # Both are kept: this posted line comes in, and the pending one is set aside with its own date
                    # and amount once the posted line has an id (below).
                    posts_pending, existing = existing, None
                if existing:
                    # The bank's own id: the bank says this is the same line, imported again.
                    duplicates += 1
                    continue
                candidates = session.query(Transaction).filter(
                    Transaction.account_id == account_id,
                    Transaction.date       == txn_date,
                    Transaction.type       == txn_type,
                    Transaction.amount.between(amount - 0.005, amount + 0.005),
                ).all()
                look_alike = next(
                    (c for c in candidates if _descriptions_match_fuzzy(c.description, description)
                     and not _ic.bank_says_different(c, fitid)),
                    None,
                )
                pending_alike = None
                if look_alike is not None and look_alike.pending and not is_pending:
                    # Item 93 B9: it looks like a pending line here - the posted version, probably. It comes in, and
                    # whether it is that pending line is asked, never decided.
                    pending_alike, look_alike = look_alike, None
                if posts_pending is not None:
                    look_alike = None
                if look_alike:
                    # Item 93 B5: similarity proposes, it never decides - held back and shown, never dropped.
                    held_rows.append(_ic.hold(session, account_id, rec, look_alike, batch).id)
                    continue

                # Category — resolve against the existing taxonomy, NEVER
                # create. The DB carries the tuned hierarchy (parents, colors,
                # icons); a row created here is a parentless ghost the budget
                # doesn't track. Unknown names land in Other instead.
                cat = session.query(Category).filter(
                    func.lower(Category.name) == cat_name.lower()
                ).first()
                if not cat and cat_name and cat_name.strip().lower() not in ('other', ''):
                    # item 83 T4: the person's remembered answer for this imported name, then a near-twin of their own
                    from core import record_tidy as _rt
                    _alias = (_tidy_aliases.get(cat_name.strip().lower()) if _tidy_aliases is not None else None)
                    _hit = _alias or _rt.near_twin(cat_name, _tidy_names)
                    if _hit:
                        cat = session.query(Category).filter(func.lower(Category.name) == _hit.lower()).first()
                    if not cat:
                        _tidy_unmatched.setdefault(cat_name.strip(), [])
                if not cat:
                    cat = session.query(Category).filter(
                        func.lower(Category.name) == 'other'
                    ).first()

                # CP3 fields — parsed upstream in bank_importer.py, simply
                # weren't being persisted here before. posted_date defaults
                # to the transaction date when the parser didn't find a
                # separate true date (decision #2 — always store both).
                posted_date_raw = rec.get('posted_date')
                posted_date = date.fromisoformat(posted_date_raw) if posted_date_raw else txn_date

                _new_txn = Transaction(
                    account_id=account_id,
                    category_id=cat.id,
                    date=txn_date,
                    description=description,
                    amount=amount,
                    type=txn_type,
                    cleared=bool(rec.get('cleared', True)),
                    memo=rec.get('memo', ''),
                    merchant=rec.get('merchant', '') or description,
                    posted_date=posted_date,
                    running_balance=rec.get('running_balance'),
                    mcc=rec.get('mcc', ''),
                    card_last4=rec.get('card_last4', ''),
                    import_id=fitid,   # FITID from QFX — enables exact dedup on reimport
                    source=rec.get('source', 'csv'),
                    check_number=rec.get('check_number', ''),
                    import_batch=batch,          # item 93 B7
                    pending=is_pending,          # item 93 B9
                )
                if is_pending:
                    _new_txn.cleared = False
                session.add(_new_txn)
                if posts_pending is not None:
                    session.flush()
                    _bv.pair_by_bank_id(session, posts_pending, _new_txn)
                    pairs_made += 1
                elif not is_pending and (pending_alike is not None or session.query(Transaction.id).filter(
                        Transaction.account_id == account_id, Transaction.pending.is_(True)).first()):
                    session.flush()
                    _pp = _bv.suggest(session, _new_txn, prefer=pending_alike)
                    if _pp is not None:
                        pairs_asked.append(_pp.id)
                if cat_name and cat_name.strip() in _tidy_unmatched:
                    session.flush()
                    _tidy_unmatched[cat_name.strip()].append(_new_txn.id)
                _nv_label = (rec.get('bank_category') or '').strip()
                if _nv_on and _nv_label:
                    _nv_k = _nv.key(_new_txn.merchant, description)
                    if _nv_k and _nv_k not in _nv_new:
                        _nv_new[_nv_k] = not _nv.ruled(_nv_rules, _nv_k) and not _nv.seen_before(session, _nv_k, batch)
                    if _nv_k and _nv_new[_nv_k]:
                        session.flush()
                        _nv_found.setdefault(_nv_k, {'merchant': _new_txn.merchant or description, 'label': _nv_label,
                                                     'category': cat.name, 'ids': []})['ids'].append(_new_txn.id)
                # B9: a posted line paired by the bank's id moves a linked card by what changed, not twice
                new_txn_deltas.append((amount - (posts_pending.amount if posts_pending is not None else 0), txn_type))
                created += 1

            except Exception as e:
                errors += 1
                logging.warning('Row error: %s', e)

        # H1 (SOURCE_DOCUMENT_CUSTODY.md s4, s8): the import itself is a
        # historical event, recorded whether or not its source is ever kept.
        # Inside this transaction, so it exists exactly when the import does.
        # A fact ABOUT the file - never its bytes, never an Artefact (C3).
        # Item 93 B3: each new debit a standing statement covers becomes a payment by that statement.
        from core import household_statements as _hs
        session.flush()
        standing_paid = _hs.apply_standing(session, session.query(Transaction).filter(
            Transaction.import_batch == batch, Transaction.type == 'debit').all())
        _log_import_committed(session, source, account_id, acct_name, records,
                              created, duplicates, errors, held=len(held_rows))
        if _tidy_unmatched:                              # item 83 T4: asked about on the tidy card, never silent
            _kept = _setting_json(session, 'import_unmatched_json', []) or []
            for _n, _ids in _tidy_unmatched.items():
                _e = next((x for x in _kept if x.get('name') == _n and not x.get('answer')), None)
                if _e:
                    _e['ids'] = sorted(set((_e.get('ids') or []) + _ids))
                elif _ids:
                    _kept.append({'name': _n, 'ids': _ids, 'at': datetime.now().isoformat(timespec='seconds')})
            _set_setting(session, 'import_unmatched_json', json.dumps(_kept))
        if _nv_found:                                    # item 98 N4: waits on the Ledger, one vendor at a time
            _set_setting(session, _nv.SETTING, json.dumps(_nv.queue(_nv.load(session), _nv_found)))
        session.commit()

    # B3.5: Auto-update linked debt card current_balance from the most recent
    # imported transaction's running_balance. This keeps the debt page current
    # after every import without the user having to manually type the new balance.
    #
    # BUG FIX (July 6): this only ever worked when the bank's own export
    # included a running_balance column — Superior Credit Union's checking
    # export has one, but plenty of real, common exports don't (confirmed:
    # Capital One's CSV has only Debit/Credit columns, no balance). For
    # those, `latest` below was always None, so the whole block quietly did
    # nothing — a real charge would post correctly to the Ledger while the
    # linked debt card's balance never moved at all. Fixed with a fallback:
    # when no bank-reported balance is available, compute the delta
    # ourselves from the transactions actually created in this import batch
    # — a debit (charge) increases what's owed, a credit (payment) decreases
    # it — and apply that delta to the debt's existing balance instead of
    # leaving it frozen.
    balance_updates = []
    try:
        from core.database import DebtAccount, Transaction as TxnQ
        with db_session() as session:
            linked_debts = session.query(DebtAccount).filter_by(
                linked_account_id=account_id, is_active=True
            ).all()
            for debt in linked_debts:
                latest = session.query(TxnQ).filter(
                    TxnQ.account_id == account_id,
                    TxnQ.running_balance != None,
                    TxnQ.running_balance != 0,
                ).order_by(TxnQ.date.desc(), TxnQ.id.desc()).first()

                old_bal = debt.current_balance
                new_bal = None

                if latest and latest.running_balance:
                    # Bank reports its own running balance — trust it directly,
                    # same as before.
                    new_bal = round(latest.running_balance, 2)
                elif new_txn_deltas:
                    # No bank-reported balance available at all — compute the
                    # change ourselves from what actually got imported this
                    # batch. Debit (charge) increases the balance owed;
                    # credit (payment) decreases it.
                    delta = 0.0
                    for amt, typ in new_txn_deltas:
                        delta += amt if typ == 'debit' else -amt
                    if abs(delta) > 0.01:
                        new_bal = round((old_bal or 0) + delta, 2)

                # A balance the bank reports fills an unknown one (V6).
                if new_bal is not None and (old_bal is None or abs(old_bal - new_bal) > 0.01):
                    debt.current_balance = new_bal
                    balance_updates.append({
                        'debt_id':   debt.id,
                        'debt_name': debt.name,
                        'old_bal':   old_bal,
                        'new_bal':   new_bal,
                    })
            if balance_updates:
                session.commit()
    except Exception as e:
        logging.warning('Balance auto-update failed: %s', e)

    # B6b: Auto-write debt_balance_history on every import.
    # When an imported account is linked to a debt card, write (or update) a
    # monthly historian snapshot using real transaction data from this import.
    # This fires automatically — no user action required. It replaces the
    # manual-only path that only wrote when the user opened the Budget page.
    #
    # Fields derived from imported transactions:
    #   balance              = running_balance on the latest transaction
    #   payment              = sum of credit transactions (payments TO the card)
    #   interest_charged     = sum of Interest-category debit transactions
    #   statement_period_end = date of the last transaction in the import
    #   month                = YYYY-MM from statement_period_end
    #   min_payment          = stored minimum_payment on the debt card
    #   apr                  = stored interest_rate on the debt card
    #
    # UNIQUE(debt_id, month) → re-importing the same statement just updates.
    history_written = []
    try:
        from core.database import DebtAccount, Transaction as TxnQ, DebtBalanceHistory
        with db_session() as session:
            linked_debts = session.query(DebtAccount).filter_by(
                linked_account_id=account_id, is_active=True
            ).all()

            for debt in linked_debts:
                # Get all transactions for this account, newest first
                all_txns = session.query(TxnQ).filter_by(
                    account_id=account_id
                ).order_by(TxnQ.date.desc(), TxnQ.id.desc()).all()

                if not all_txns:
                    continue

                # statement_period_end = date of the latest transaction
                latest_txn = all_txns[0]
                period_end = latest_txn.date.isoformat() if hasattr(latest_txn.date, 'isoformat') else str(latest_txn.date)
                month      = period_end[:7]   # YYYY-MM

                # balance = running_balance from latest txn, or net-change fallback
                if latest_txn.running_balance and latest_txn.running_balance != 0:
                    balance = round(latest_txn.running_balance, 2)
                else:
                    balance = round(sum(
                        t.amount if t.type == 'debit' else -t.amount
                        for t in all_txns
                    ), 2)

                # Scope to this month's transactions for payment and interest
                month_txns = [
                    t for t in all_txns
                    if str(t.date)[:7] == month
                ]

                # payment = sum of credit transactions (payments received by the card)
                payment = round(sum(
                    t.amount for t in month_txns if t.type == 'credit'
                ), 2)

                # interest_charged = sum of Interest-category debits this month
                # Join via category to check name (category_id FK)
                from core.database import Category as CatModel
                interest_cat = session.query(CatModel).filter(
                    CatModel.name.ilike('interest')
                ).first()
                if interest_cat:
                    interest_charged = round(sum(
                        t.amount for t in month_txns
                        if t.type == 'debit' and t.category_id == interest_cat.id
                    ), 2)
                else:
                    # Fallback: match by description pattern
                    INTEREST_KEYWORDS = ['interest charge', 'finance charge', 'interest charged']
                    interest_charged = round(sum(
                        t.amount for t in month_txns
                        if t.type == 'debit' and
                        any(kw in (t.description or '').lower() for kw in INTEREST_KEYWORDS)
                    ), 2)

                min_payment = round(float(debt.minimum_payment or 0), 2)
                apr         = float(debt.interest_rate or 0)

                # Upsert: update existing row for this month or insert new
                existing = session.query(DebtBalanceHistory).filter_by(
                    debt_id=debt.id, month=month
                ).first()

                if existing:
                    existing.balance              = balance
                    existing.payment              = payment
                    existing.min_payment          = min_payment
                    existing.apr                  = apr
                    existing.interest_charged     = interest_charged if interest_charged > 0 else existing.interest_charged
                    existing.statement_period_end = period_end
                else:
                    session.add(DebtBalanceHistory(
                        debt_id              = debt.id,
                        month                = month,
                        balance              = balance,
                        payment              = payment,
                        min_payment          = min_payment,
                        apr                  = apr,
                        interest_charged     = interest_charged if interest_charged > 0 else None,
                        statement_period_end = period_end,
                    ))

                history_written.append({
                    'debt_id':   debt.id,
                    'debt_name': debt.name,
                    'month':     month,
                    'balance':   balance,
                    'interest':  interest_charged,
                })

            if history_written:
                session.commit()

    except Exception as e:
        logging.warning('B6b historian auto-write failed: %s', e)

    # B4: APR change detection — scan newly imported transactions for interest
    # charges on linked debt card accounts. If implied APR differs from stored
    # rate by > 1 percentage point, flag it for user confirmation.
    # Never auto-updates APR. Always surfaces and requires user confirmation.
    apr_alerts = []
    try:
        from core.database import DebtAccount
        with db_session() as session:
            # Find debt cards linked to this account
            linked_debts = session.query(DebtAccount).filter_by(
                linked_account_id=account_id, is_active=True
            ).all()

            INTEREST_PATTERNS = [
                'interest charge', 'interest charged', 'finance charge',
                'periodic rate', 'purchase interest', 'cash advance interest',
                'balance transfer interest', 'int chg', 'finance chg',
            ]

            for debt in linked_debts:
                # Find interest charge transactions in the just-imported records
                interest_txns = [
                    r for r in records
                    if any(p in (r.get('description','') or '').lower()
                           for p in INTEREST_PATTERNS)
                    and r.get('type','debit') == 'debit'
                ]
                if not interest_txns:
                    continue

                # Use the largest interest charge (most recent full month)
                interest_charge = max(float(r.get('amount', 0)) for r in interest_txns)
                if interest_charge <= 0:
                    continue

                # Find prev_balance: use running_balance from the transaction
                # before the interest charge when available, else current_balance
                prev_balance = None
                for r in interest_txns:
                    if r.get('running_balance'):
                        prev_balance = float(r['running_balance']) + interest_charge
                        break
                if not prev_balance:
                    prev_balance = float(debt.current_balance) if debt.current_balance else None
                if not prev_balance or prev_balance <= 0:
                    continue

                implied_apr = round((interest_charge / prev_balance) * 12 * 100, 2)
                stored_apr  = float(debt.interest_rate or 0)

                if abs(implied_apr - stored_apr) > 1.0:
                    # Determine statement month from the interest charge date
                    charge_month = interest_txns[0].get('date', '')[:7]
                    apr_alerts.append({
                        'debt_id':        debt.id,
                        'debt_name':      debt.name,
                        'stored_apr':     stored_apr,
                        'implied_apr':    implied_apr,
                        'interest_charge': interest_charge,
                        'basis_balance':  round(prev_balance, 2),
                        'month':          charge_month,
                    })
    except Exception as e:
        logging.warning('APR detection failed: %s', e)

    result = {
        'created':    created,
        'duplicates': duplicates,
        'errors':     errors,
        'batch':      batch,
        'pending_paired': pairs_made,    # item 93 B9
        'standing_payments': standing_paid,   # item 93 B3
        'new_vendors': len(_nv_found),        # item 98: asked about on the Ledger
    }
    if pairs_asked:                      # item 93 B9
        with db_session() as session:
            result['pending_pairs'] = [x for x in _bv.suggestions(session) if x['id'] in pairs_asked]
    if held_rows:                      # item 93 B5
        with db_session() as session:
            from core.database import ImportHeldLine
            result['held'] = _ic.held_views(session, [session.get(ImportHeldLine, i) for i in held_rows])
    if apr_alerts:
        result['apr_alerts'] = apr_alerts
    if balance_updates:
        result['balance_updates'] = balance_updates
    if history_written:
        result['history_written'] = history_written

    return ok(result)


def serve(app, host='127.0.0.1', port=8765):
    """Serve the app, on a server meant for it.

    Flask's built-in server is a development convenience and says so in its own
    startup banner. Groundwork shipped on it anyway — every launch path called
    `app.run()` — and the cost is measurable rather than theoretical: request
    latency alternated between roughly 45ms and 250ms on loopback, `/api/health`
    and a real route alike, which is the signature of connection handling rather
    than of anything the routes do. That was invisible while the client answered
    payoff questions itself. Once it started asking the server, it became a
    visible flash on every keystroke in the debt page.

    Waitress is the choice for a desktop app: pure Python, so it freezes into a
    PyInstaller bundle without a compiler; cross-platform, unlike gunicorn;
    threaded, which is what a local single-user server wants.

    **The fallback is deliberate and loud.** If waitress is missing — a source
    checkout that skipped requirements.txt — the app still runs, on the old
    server, with a warning in the log. Refusing to start would trade a slow app
    for no app, and this is a personal finance tool someone may be opening to
    check whether a payment cleared.
    """
    try:
        from waitress import serve as _waitress_serve
    except ImportError:
        # getLogger inline: this module has no module-level `logger`, and a
        # NameError here would break the one path that exists to keep the app
        # running when something is missing.
        logging.getLogger('groundwork').warning(
            'waitress is not installed - falling back to the Flask development '
            'server. The app works; requests are slower and less consistent. '
            'Install it with: pip install -r requirements.txt')
        app.run(host=host, port=port, debug=False, threaded=True,
                use_reloader=False)
        return

    # Threads: a desktop app has one user, and the ceiling exists to stop a
    # runaway from spawning without limit rather than to serve a crowd.
    # channel_timeout keeps a dropped webview connection from holding a thread.
    _waitress_serve(app, host=host, port=port, threads=8,
                    channel_timeout=120, ident='Groundwork')


if __name__ == '__main__':
    app = create_app()
    logging.basicConfig(level=logging.INFO)
    serve(app, host='127.0.0.1', port=8765)
