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
            req = urllib.request.Request(UPDATE_MANIFEST_URL,
                                         headers={'User-Agent': 'Groundwork'})
            with urllib.request.urlopen(req, timeout=4) as r:
                info = json.loads(r.read(65536).decode('utf-8'))
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
    run_migration_if_needed()

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
    app.register_blueprint(backup_bp,        url_prefix='/api/backup')
    app.register_blueprint(import_bp,        url_prefix='/api/import')
    app.register_blueprint(bank_import_bp,   url_prefix='/api/import')
    app.register_blueprint(auto_import_bp,   url_prefix='/api/auto-import')
    app.register_blueprint(sinking_funds_bp,  url_prefix='/api/sinking-funds')
    app.register_blueprint(proactive_bp,     url_prefix='/api/proactive')
    app.register_blueprint(trophies_bp,      url_prefix='/api/trophies')
    app.register_blueprint(college_funds_bp,  url_prefix='/api/college-funds')
    app.register_blueprint(gift_bp,           url_prefix='/api/gift')
    app.register_blueprint(historian_bp,      url_prefix='/api/historian')
    app.register_blueprint(willingness_bp,    url_prefix='/api/willingness')
    app.register_blueprint(income_bp,         url_prefix='/api/income-change')
    app.register_blueprint(evidence_bp,       url_prefix='/api/evidence')
    app.register_blueprint(why_bp,            url_prefix='/api/why')
    app.register_blueprint(help_bp,           url_prefix='/api/help')
    app.register_blueprint(review_bp,         url_prefix='/api/reports/review')
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
                        'timestamp': datetime.utcnow().isoformat()})

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
                    setting.updated_at = datetime.utcnow()
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

        return ok([serialize_transaction(t, linked_map.get(t.id)) for t in txns],
                  total=total, page=page, per_page=per_page)


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
        backup_name = f'groundwork_backup_pre-delete-all_{ts}.db'
        backup_path = _backups_dir() / backup_name
        shutil.copy2(DB_PATH, backup_path)
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
        _unlink_debt_for_deleted_transaction(session, txn_id)
        session.delete(txn)
        session.commit()
        return ok({'deleted': txn_id})


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


def detect_recurring_patterns(session, months: int = 6, min_occurrences: int = 3, tolerance_pct: float = 5.0) -> list:
    """
    Phase H2 Feature 4 (adaptive learning — recurring transaction
    auto-detection). Merchants with 3+ transactions of consistent amount
    (within tolerance_pct of their own average) over the trailing window —
    the "Netflix $15.99 every month" pattern. Skips merchants that already
    have an active budget item, since flagging something the user already
    budgets for isn't a suggestion, it's noise.
    """
    cutoff = date.today() - timedelta(days=30 * months)
    rows = session.query(Transaction.merchant, Transaction.amount).filter(
        Transaction.type == 'debit', Transaction.date >= cutoff, Transaction.merchant != ''
    ).all()

    by_merchant = {}
    for merchant, amount in rows:
        by_merchant.setdefault(merchant, []).append(amount)

    existing_budgeted = {
        b[0] for b in session.query(BudgetItem.name).filter_by(is_active=True).all()
    }

    patterns = []
    for merchant, amounts in by_merchant.items():
        if len(amounts) < min_occurrences or merchant in existing_budgeted:
            continue
        avg = sum(amounts) / len(amounts)
        if avg <= 0:
            continue
        max_deviation_pct = max(abs(a - avg) / avg * 100 for a in amounts)
        if max_deviation_pct <= tolerance_pct:
            patterns.append({
                'merchant': merchant, 'avg_amount': round(avg, 2), 'frequency': len(amounts),
                'max_deviation_pct': round(max_deviation_pct, 1),
            })
    patterns.sort(key=lambda p: -p['frequency'])
    return patterns


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
    cutoff = today - timedelta(days=30 * months)
    out = []
    for pattern in detect_recurring_patterns(session, months=months)[:limit]:
        merchant = pattern['merchant']
        rows = session.query(
            Transaction.date, Transaction.amount, Category.name
        ).outerjoin(Category, Transaction.category_id == Category.id).filter(
            Transaction.merchant == merchant, Transaction.type == 'debit',
            Transaction.date >= cutoff
        ).all()
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
            'name': merchant,
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
    for e in session.query(HistorianEntry).filter(
            HistorianEntry.event_category == 'budget_adjusted').order_by(HistorianEntry.created_at, HistorianEntry.id):
        c = json.loads(e.context_json or '{}')
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


evidence_bp = Blueprint('evidence', __name__)
usage_bp = Blueprint('usage', __name__)


# ── Item 58 - the evidence library (EVIDENCE_LIBRARY.md E1-E10) ───────────────────────────────────────────────
@evidence_bp.route('', methods=['GET'])
def evidence_for_surface():
    """E2/E3/E9: the accepted entries that apply on one surface, chosen from the person's goals and debts only,
    each with the person's own answer to its offer, if they gave one."""
    from core import evidence as ev
    surface = (request.args.get('surface') or '').strip()
    with db_session() as session:
        answers = _setting_json(session, 'evidence_answers', []) or []
        out = []
        for e in ev.select(session, surface):
            last = next((a for a in reversed(answers) if a.get('id') == e['id']), None)
            out.append({**e, 'answer': last})
        return ok({'surface': surface, 'entries': out})


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


# E8: the person's own rhythm. Recorded and shown to them; no engine, selection, ranking or tile reads it (ruling 6).
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


@usage_bp.route('/rhythm', methods=['GET'])
def usage_rhythm():
    """E8: "You opened Groundwork 9 times in the last 30 days, mostly Sunday evenings." The 'mostly' is named only
    when one day-and-time holds at least 40% of at least 4 opens."""
    with db_session() as session:
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
    return ok({'opens_30d': len(recent), 'mostly': mostly})


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
        for ch in plan['changes']:
            item = session.get(BudgetItem, ch['id'])
            if not item or abs((item.amount or 0) - ch['old']) > 0.005:
                continue                      # the line changed since the plan was shown: left as it is
            item.amount = ch['new']
            log_historian_event(session, 'budget_adjusted', expected_value=ch['old'], actual_value=ch['new'],
                                context={'budget_item_id': item.id, 'name': item.name, 'item_type': item.type})
            done.append({'id': item.id, 'name': item.name, 'old': ch['old'], 'new': ch['new']})
        _set_setting(session, 'income_change_applied', json.dumps({'at': datetime.now().isoformat(timespec='seconds'),
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
        for ch in applied.get('changes', []):
            item = session.get(BudgetItem, ch['id'])
            if not item or abs((item.amount or 0) - ch['new']) > 0.005:
                continue                      # changed again since: the person's later edit stands
            item.amount = ch['old']
            log_historian_event(session, 'budget_adjusted', expected_value=ch['new'], actual_value=ch['old'],
                                context={'budget_item_id': item.id, 'name': item.name, 'item_type': item.type})
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
    now = today or datetime.utcnow()
    rows = session.query(
        Transaction.account_id, func.max(Transaction.created_at)
    ).filter(
        Transaction.account_id.isnot(None),
        Transaction.source.isnot(None), Transaction.source != '', Transaction.source != 'manual',
    ).group_by(Transaction.account_id).all()
    out = []
    for account_id, last in rows:
        if last is None:
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
    now = today or datetime.utcnow()
    start = datetime(now.year, now.month, 1)
    rows = session.query(Transaction.account_id, func.max(Transaction.created_at)).filter(
        Transaction.account_id.isnot(None),
        Transaction.source.isnot(None), Transaction.source != '', Transaction.source != 'manual',
    ).group_by(Transaction.account_id).all()
    out = []
    for account_id, last in rows:
        if last is None or last >= start:
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
            'payment_due', 'import_stale', 'blocked_conclusion'):
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
        reqs.append({'text': text, 'at': datetime.utcnow().isoformat(timespec='seconds')})
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
        _dashboard_store(session, key, {'fetched_at': datetime.utcnow().isoformat(), 'rows': rows})
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
            age = datetime.utcnow() - datetime.fromisoformat(cached['fetched_at'])
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
        url = STEO_URL.format(key=urllib.parse.quote(api_key), series=urllib.parse.quote(series), start=start)
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
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
    item = session.query(BudgetItem).filter(func.lower(BudgetItem.category) == 'gas', BudgetItem.is_active == True).first()  # noqa: E712
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
            age = datetime.utcnow() - datetime.fromisoformat(cached['fetched_at'])
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
        url = EIA_WEEKLY_GAS_URL.format(key=urllib.parse.quote(api_key), area=urllib.parse.quote(area), product=product)
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
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
        func.lower(Category.name) == 'gas / fuel', Transaction.type == 'debit').order_by(Transaction.date).all() if d and a]
    months = ue.fuel_months(fills, weekly, today.strftime('%Y-%m')) if weekly else {}
    item = session.query(BudgetItem).filter(func.lower(BudgetItem.category) == 'gas / fuel', BudgetItem.is_active == True).first()  # noqa: E712
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
            age = datetime.utcnow() - datetime.fromisoformat(cached['fetched_at'])
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
        url = EIA_WEEKLY_RES_URL.format(key=urllib.parse.quote(api_key), area=urllib.parse.quote(area), product=product)
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
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
                    'assumes': 'Reading your Gas / Fuel fill-ups as regular gasoline. Tell us what your vehicle uses to be sure.'}
        return {'applies': True, 'ask': ask}
    return {'applies': True, 'ask': ask}


_UTILITY_CATEGORY = {'gas': 'gas', 'electric': 'electric', 'gasoline': 'gas / fuel', 'propane': 'propane',
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
    from core.solution import past_charge_lesson, is_protected

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
        if (cat and is_protected(cat.name)) or (not cat and (is_protected(t.merchant) or is_protected(t.description))):
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
    now = datetime.utcnow()
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
    window_start = datetime.utcnow() - timedelta(days=365)
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
                        'months_ago': ((datetime.utcnow().year - acct.paid_off_at.year) * 12
                                       + (datetime.utcnow().month - acct.paid_off_at.month))})
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

    window_start = datetime.utcnow() - timedelta(days=365)
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
            months_ago = ((datetime.utcnow().year - acct.paid_off_at.year) * 12
                          + (datetime.utcnow().month - acct.paid_off_at.month))
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
        backup_name = f'groundwork_backup_pre-delete-debt-{debt_id}_{ts}.db'
        shutil.copy2(DB_PATH, _backups_dir() / backup_name)
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
    Call the active AI provider directly — no HTTP round-trip through
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
            session.add(CheckingTransactionLink(
                checking_transaction_id=linked_txn_id,
                debt_ledger_entry_id=entry.id,
                link_indicator='payment_to_card' if entry_type == 'payment' else 'charge_from_card',
                user_confirmed_at=datetime.utcnow(),
            ))

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
                rp.last_confirmed_at = datetime.utcnow()
                rp.last_executed_at = datetime.utcnow()

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
        session.add(CheckingTransactionLink(
            checking_transaction_id=txn_id,
            debt_ledger_entry_id=entry.id,
            link_indicator='payment_to_card',
            user_confirmed_at=datetime.utcnow(),
        ))
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
        context_json=json.dumps(context) if context else None,
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
    count once), plus this month's budget_reviewed count. UTC day boundaries,
    matching how created_at is stored. Honest zero shape when there's no
    history yet — the UI self-gates on streak_days the same way the confidence
    cards gate on a null score."""
    starts = session.query(HistorianEntry.created_at).filter(
        HistorianEntry.event_category == 'session_start').all()
    days = sorted({c.date() for (c,) in starts if c is not None}, reverse=True)
    today = datetime.utcnow().date()
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
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
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
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
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
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
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
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
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


def _log_gift_season_contribution_variance(session, season_id, target: float, saved_before: float,
                                            deadline: str, actual_amount: float):
    """
    Gift seasons' Historian write-hook, called from POST
    .../gift/seasons/<id>/contribute. Unlike sinking/college funds, a gift
    season has no monthly_contribution/monthlyContrib field at all — only
    target + deadline — so "expected" is computed the same way the
    client's own _giftSeasonCard already displays it ("$X/mo for N
    months"): (target - saved) / months_left, using the balance BEFORE
    this deposit is applied. Skipped when there's no deadline, no target,
    no months remaining, or the season is already funded — nothing
    meaningful to compare against in any of those cases.
    """
    if not deadline or not target:
        return
    try:
        d = datetime.strptime(deadline, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return
    today = datetime.utcnow().date()
    months_left = max(0, (d.year - today.year) * 12 + (d.month - today.month))
    remaining = target - saved_before
    if months_left <= 0 or remaining <= 0:
        return
    expected = remaining / months_left
    log_historian_event(
        session, 'gift_season_contribution_variance',
        expected_value=round(expected, 2), actual_value=round(actual_amount, 2),
        context={'gift_season_id': season_id},
    )


def get_gift_season_confidence(session, season_id, months: int = 12) -> dict:
    """0-100 pace confidence for a gift season — identical shape and
    scoring to get_sinking_fund_confidence/get_college_fund_confidence."""
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
    entries = session.query(HistorianEntry).filter(
        HistorianEntry.event_category == 'gift_season_contribution_variance',
        HistorianEntry.created_at >= cutoff,
    ).all()
    matched = []
    for e in entries:
        try:
            ctx = json.loads(e.context_json or '{}')
        except (json.JSONDecodeError, TypeError):
            continue
        if str(ctx.get('gift_season_id')) == str(season_id):
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


def _log_gift_occasion_variance(session, person_id, occasion_id, budget: float, actual_spent: float):
    """Occasions' Historian write-hook — logged once an occasion's actual
    spend is recorded (see log_gift_occasion_spend below). expected=budget,
    actual=actual_spent; skipped when no budget was ever set (nothing to
    compare an unplanned gift against)."""
    if not budget or budget <= 0:
        return
    log_historian_event(
        session, 'gift_occasion_variance',
        expected_value=round(budget, 2), actual_value=round(actual_spent, 2),
        context={'gift_person_id': person_id, 'occasion_id': occasion_id},
    )


def get_payment_variance_for_account(session, debt_account_id: int, months: int = 12) -> dict:
    """Payment compliance metrics for a debt account from real historian
    events (payment_confirmed / payment_amount_variance), over a trailing
    window. Distinct from server.py :: get_payment_compliance (Phase E),
    which reads current ledger state per recurring pattern — this reads the
    historian's point-in-time record of what happened at confirm time,
    which survives even if the underlying ledger entry is later edited."""
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
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
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
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
    cutoff = datetime.utcnow() - timedelta(days=time_range_days)
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
        _set_setting(session, f'bank_recipe:{key}', json.dumps({'steps': clean, 'saved': datetime.utcnow().isoformat()}))
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
    return ok({'id': b.id, 'account_id': acct})


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
    now = datetime.utcnow()            # the Historian's times are UTC (HistorianEntry.created_at)
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
                row['last_download'] = last.isoformat(timespec='minutes') + 'Z' if last else None   # UTC, said so
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
        chk = bill_check.pay_check(balance, as_of, last, buf, r.amount if r else None, [], datetime.utcnow())
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
    gas = next((c for c in cats if c.name == 'Gas' and parent.get(c.parent_id) == 'Utilities'), None)
    fuel, gym = by.get('Gas / Fuel'), by.get('Gym / Fitness')
    rows, groc_rows = [], []
    if gas and fuel:
        for t in session.query(Transaction).filter(Transaction.category_id == gas.id, Transaction.type == 'debit').all():
            if bi.auto_category(t.description or '', t.mcc or '') == 'Gas / Fuel':
                rows.append(t)
    # Item 53 G7 (FUEL_NAMES.md): warehouse-club and grocery fuel (Costco Gas, Meijer Express) that older imports
    # saved under Groceries, offered the same way.
    groc = by.get('Groceries')
    if groc and fuel:
        for t in session.query(Transaction).filter(Transaction.category_id == groc.id, Transaction.type == 'debit').all():
            if bi.auto_category(t.description or '', t.mcc or '') == 'Gas / Fuel':
                groc_rows.append(t)
    stray = next((c for c in cats if c.name.lower() == 'fitness' and not c.is_system), None)
    return gas, fuel, gym, rows, stray, groc_rows


# Item 54 M6 (MATCHER_ONE_ANSWER.md): the categories the two old matchers saved that today's rules no longer give -
# the server's parents, and the page's wrong leaves. A row in one of them whose words now name a different real
# leaf is offered, grouped by from -> to. Gas and Groceries rows that are fuel are item 52/53's own blocks.
_OLD_MATCHER_ANSWERS = ('Utilities', 'Insurance', 'Transportation', 'Food', 'Healthcare', 'Entertainment', 'Education',
                        'Personal', 'Subscriptions', 'Income', 'Property Taxes',
                        'Gas / Fuel', 'Groceries', 'Health Insurance', 'Electric', 'Doctor / Co-pays',
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
        if to == 'Gas / Fuel' and src in ('Gas', 'Groceries'):
            continue                  # item 52/53's blocks
        if src in _MUNICIPAL_FROM and src not in _OLD_MATCHER_ANSWERS and to != 'Municipal Utilities':
            continue                  # item 56 U6: from Other or Water / Sewer, only to Municipal Utilities
        groups.setdefault((src, to), []).append(t)
    return groups


@categories_bp.route('/label-review', methods=['GET'])
def category_label_review():
    with db_session() as session:
        gas, fuel, gym, rows, stray, groc_rows = _label_review(session)

        def block(src, rs):
            rs.sort(key=lambda t: t.date, reverse=True)
            return {'from': src, 'to': 'Gas / Fuel', 'count': len(rs), 'total': round(sum(float(t.amount) for t in rs), 2),
                    'rows': [{'id': t.id, 'date': t.date.isoformat(), 'description': t.description or '',
                              'amount': float(t.amount)} for t in rs]}
        out = {'fuel': block('Gas', rows) if rows else None,
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
            row.last_updated = datetime.utcnow()
        else:
            session.add(PriceCache(
                ticker       = ticker,
                price        = price,
                is_manual    = True,
                last_updated = datetime.utcnow(),
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
            existing.updated_at = datetime.utcnow()
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
                row.updated_at = datetime.utcnow()
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
        rows = session.query(Transaction.id, Transaction.date, Transaction.amount, Transaction.merchant).filter(
            Transaction.type == 'debit', Transaction.date >= window).all()
        budgeted = [b.name for b in session.query(BudgetItem).filter_by(is_active=True).all()]
        cards, budget, strategy, _undated = _consequence_inputs(session)
        offers = []
        for o in byb_offer.new_recurring(rows, budgeted, today, window):
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
            decided_at       = datetime.utcnow() if decision in ('commit', 'walkaway') else None,
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
        item.decided_at  = datetime.utcnow()
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
    key = ('hotels', 0)
    bank_window.close_bank_window(key)        # a new search replaces the one on screen
    return ok({'result': bank_window.open_bank_window(key, url)})


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
        b.updated_at = datetime.utcnow()
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
        b.updated_at = datetime.utcnow()
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
            if session.query(InvestmentLot.id).first():
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
                dest.write_text(output.getvalue(), encoding='utf-8')
            else:
                payload = {
                    'exported_at':   datetime.utcnow().isoformat(),
                    'transactions':  txn_rows,
                    'budget':        budget_rows,
                    'debt_accounts': debt_rows,
                    'net_worth':     nw_rows,
                    'settings':      all_settings,
                }
                if body.get('include_ai_log'):    # item 62 G5: only when the person ticks it
                    payload['ai_log'] = [_ai_log_json(r, full=True) for r in session.query(AiLog).order_by(AiLog.id).all()]
                dest.write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')

            resp = {'saved': True, 'path': str(dest), 'filename': filename}
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
    # Respect the user's AI toggle — return a friendly message, not an error code
    if not _ai_is_enabled():
        return ok({
            'ai_available': False,
            'reason':       'disabled',
            'message':      'AI features are turned off. You can enable them in Settings.',
        })

    body = request.json or {}
    if body.get('stream'):
        return _ai_chat_stream(body)
    return _ai_chat_local(body)


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
                yield 'data: ' + json.dumps({'done': True, 'stop_reason': stop_reason, 'provider': 'local', 'log_id': log_id}) + '\n\n'
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
            session.query(AiLog).filter(AiLog.created_at < datetime.utcnow() - timedelta(days=AI_LOG_DAYS)) \
                .delete(synchronize_session=False)
            row = AiLog(call_id=str(body.get('log_call') or '')[:64], attempt=int(body.get('log_attempt') or 1),
                        surface=str(body.get('surface') or '')[:80], system=str(body.get('system') or '')[:40000],
                        messages=json.dumps(body.get('messages') or [])[:80000], response=str(response or '')[:40000],
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
                    'provider': 'local', 'finish': finish, 'stop_reason': stop_reason, 'log_id': log_id})


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
    return ok({'enabled': _ai_is_enabled(), 'provider': 'local', 'engine': st['state'], 'reason': st['reason'],
               'message': st['message'], 'model_file': st['model_file'],
               'ready': st['state'] == 'ready', 'available': st['state'] in ('loading', 'ready'),
               'load_seconds': st['load_seconds']})


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
    out = {'id': r.id, 'at': r.created_at.isoformat(timespec='seconds') + 'Z' if r.created_at else None,
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
        session.query(AiLog).filter(AiLog.created_at < datetime.utcnow() - timedelta(days=AI_LOG_DAYS)) \
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
        'ts':      datetime.utcnow().isoformat() + 'Z',
        'surface': str(body.get('surface', 'unknown'))[:80],
        'model':   str(body.get('model', ''))[:80],
        'rules':   body.get('rules') if isinstance(body.get('rules'), list) else [],
        'text':    str(body.get('text', ''))[:2000],
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


@backup_bp.route('', methods=['POST'])
@backup_bp.route('/create', methods=['POST'])
def create_backup():
    """Create a timestamped backup of the database."""
    import shutil
    from core.database import DB_PATH

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'groundwork_backup_{ts}.db'
    backup_path = _backups_dir() / backup_name

    try:
        shutil.copy2(DB_PATH, backup_path)
        if not (request.get_json(silent=True) or {}).get('include_ai_log'):
            _scrub_ai_log(backup_path)        # item 62 G5: left out unless the person includes it
        return ok({'filename': backup_name, 'size': backup_path.stat().st_size})
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

    # Validate it's a real SQLite file (not something malicious)
    try:
        with open(backup_path, 'rb') as f:
            magic = f.read(16)
        if not magic.startswith(b'SQLite format 3'):
            return err('File does not appear to be a valid Groundwork backup', 400)
    except OSError as e:
        return err(f'Could not read backup file: {e}', 500)

    try:
        # Close all active sessions and release file locks
        db_session.remove()
        engine.dispose()

        # Copy backup over the live database
        shutil.copy2(str(backup_path), str(DB_PATH))

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

    if not header.startswith(b'SQLite format 3'):
        return err('That file does not look like a Groundwork backup', 400)

    ts          = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name   = f'restored_{ts}.db'
    backup_path = _backups_dir() / safe_name

    try:
        upload.save(str(backup_path))

        # Close all active sessions and release file locks
        db_session.remove()
        engine.dispose()

        # Copy uploaded backup over the live database
        shutil.copy2(str(backup_path), str(DB_PATH))

        # Reinitialize — reconnects SQLAlchemy to the restored database, and
        # runs migrations in case the restored backup predates a schema
        # change (e.g. an older backup missing the CP3 Transaction columns).
        run_migration_if_needed()

        return ok({'restored': True, 'filename': safe_name})
    except Exception as e:
        return err(f'Restore failed: {e}', 500)


@backup_bp.route('', methods=['GET'])
@backup_bp.route('/list', methods=['GET'])
def list_backups():
    backup_dir = _backups_dir()
    files = []
    for f in sorted(backup_dir.glob('*.db'), reverse=True):
        files.append({
            'filename': f.name,
            'size':     f.stat().st_size,
            'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return ok(files)


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
        'pct_funded':           round((saved / target * 100) if target > 0 else 0, 1),
        # Legacy aliases for old JS code paths
        'balance':              saved,
        'target':               target,
        'monthlyContrib':       monthly_needed,
    }


def _fund_contributions(session, fund_id: int, months: int = 12):
    """The Historian's contribution events for one fund, inside the window."""
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
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
    now = datetime.utcnow()
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
    now = datetime.utcnow()
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


# ── Gift seasons + occasions (Historian logging — same pattern as
# college_funds_bp: gift_seasons_json/gift_people_json stay client-managed
# blobs, these routes exist so "expected" always comes from that
# server-held blob, never a client-passed number) ──────────────────────────
gift_bp = Blueprint('gift', __name__)


@gift_bp.route('/seasons/<season_id>/contribute', methods=['POST'])
@require_json
def log_gift_season_contribution(season_id):
    """Body: { amount: float }. expected is computed from the season's own
    target/deadline/saved in gift_seasons_json — gift seasons have no
    monthly_contribution field, so this reproduces the same deadline-pace
    math the client already displays, using the balance as of THIS
    request (before the client applies the deposit)."""
    amount = float(request.json.get('amount', 0) or 0)
    if amount <= 0:
        return err('Amount must be positive')
    with db_session() as session:
        row = session.query(AppSetting).filter_by(key='gift_seasons_json').first()
        try:
            seasons = json.loads(row.value) if row and row.value else []
        except (json.JSONDecodeError, TypeError):
            seasons = []
        season = next((s for s in seasons if str(s.get('id')) == str(season_id)), None)
        if not season:
            return err('Season not found', 404)
        target = float(season.get('target', 0) or 0)
        saved_before = float(season.get('saved', 0) or 0)
        deadline = season.get('deadline', '')
        _log_gift_season_contribution_variance(session, season_id, target, saved_before, deadline, amount)
        session.commit()
        return ok({'logged': True})


@gift_bp.route('/seasons/<season_id>/confidence', methods=['GET'])
def gift_season_confidence(season_id):
    """Gift seasons' mirror of the sinking/college-fund confidence
    routes — thin read of get_gift_season_confidence."""
    with db_session() as session:
        return ok(get_gift_season_confidence(session, season_id))


@gift_bp.route('/occasions/<person_id>/<occasion_id>/spend', methods=['POST'])
@require_json
def log_gift_occasion_spend(person_id, occasion_id):
    """
    Body: { actual_spent: float }. Records what was actually spent on an
    occasion (gift_people_json has no such field today — only the
    budgeted amount) and logs the variance against that budget. Updates
    the occasion in place in the settings blob, same as it always
    persisted budget/note, rather than only living in the historian log.
    """
    actual_spent = request.json.get('actual_spent')
    if actual_spent is None:
        return err('actual_spent is required')
    actual_spent = float(actual_spent)
    with db_session() as session:
        row = session.query(AppSetting).filter_by(key='gift_people_json').first()
        try:
            people = json.loads(row.value) if row and row.value else []
        except (json.JSONDecodeError, TypeError):
            people = []
        person = next((p for p in people if str(p.get('id')) == str(person_id)), None)
        occasion = next((o for o in (person.get('occasions') or [])
                          if str(o.get('id')) == str(occasion_id)), None) if person else None
        if not occasion:
            return err('Occasion not found', 404)
        budget = float(occasion.get('budget', 0) or 0)
        occasion['actual_spent'] = actual_spent
        occasion['spent_at'] = datetime.utcnow().date().isoformat()
        row.value = json.dumps(people)
        _log_gift_occasion_variance(session, person_id, occasion_id, budget, actual_spent)
        session.commit()
        return ok({'logged': True, 'actual_spent': actual_spent})


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
                          created, duplicates, errors):
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
        'errors':         errors,
        'first_date':     dates[0] if dates else None,
        'last_date':      dates[-1] if dates else None,
    })


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
                existing = None
                if fitid:
                    existing = session.query(Transaction).filter(
                        Transaction.account_id == account_id,
                        Transaction.import_id  == fitid,
                    ).first()
                if not existing:
                    candidates = session.query(Transaction).filter(
                        Transaction.account_id == account_id,
                        Transaction.date       == txn_date,
                        Transaction.type       == txn_type,
                        Transaction.amount.between(amount - 0.005, amount + 0.005),
                    ).all()
                    existing = next(
                        (c for c in candidates if _descriptions_match_fuzzy(c.description, description)),
                        None,
                    )

                if existing:
                    duplicates += 1
                    continue

                # Category — resolve against the existing taxonomy, NEVER
                # create. The DB carries the tuned hierarchy (parents, colors,
                # icons); a row created here is a parentless ghost the budget
                # doesn't track. Unknown names land in Other instead.
                cat = session.query(Category).filter(
                    func.lower(Category.name) == cat_name.lower()
                ).first()
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

                session.add(Transaction(
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
                ))
                new_txn_deltas.append((amount, txn_type))
                created += 1

            except Exception as e:
                errors += 1
                logging.warning('Row error: %s', e)

        # H1 (SOURCE_DOCUMENT_CUSTODY.md s4, s8): the import itself is a
        # historical event, recorded whether or not its source is ever kept.
        # Inside this transaction, so it exists exactly when the import does.
        # A fact ABOUT the file - never its bytes, never an Artefact (C3).
        _log_import_committed(session, source, account_id, acct_name, records,
                              created, duplicates, errors)
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
    }
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
