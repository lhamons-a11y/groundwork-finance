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

from flask import Flask, jsonify, request, send_from_directory

# Session ID — changes on every server start so client can detect restarts
_GW_SESSION_ID = str(_uuid.uuid4())[:8]
GW_VERSION     = '20260826-d24'  # must match app.js GW_VERSION constant

# ── Security: session token ────────────────────────────────────────────────────
# Generated fresh on every startup. Lives in RAM only — never written to disk.
# Injected into index.html at serve time so the JS client can include it in
# every API request header. Any request missing the token is rejected with 403.
# This means even if another process on the same machine finds port 8765, it
# cannot read or write Groundwork data without the token.
_GW_TOKEN = secrets.token_hex(32)

from sqlalchemy import func, desc, text

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import ( db_session, DATA_DIR,
    Account, Category, Transaction, BudgetItem,
    DebtAccount, BudgetPlan, BudgetMonth, Achievement,
    AppSetting, BYBItem, NetWorthSnapshot,
    InvestmentTransaction, InvestmentLot, PriceCache,
    DebtBalanceHistory, PdfExtractCache,
    DebtLedgerEntry, RecurringDebtPayment, CheckingTransactionLink,
    HistorianEntry, TripHistory,
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
    app.register_blueprint(college_funds_bp,  url_prefix='/api/college-funds')
    app.register_blueprint(gift_bp,           url_prefix='/api/gift')
    app.register_blueprint(historian_bp,      url_prefix='/api/historian')

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
            teaching_entry = Path(static_folder) / 'js' / 'teaching' / 'index.js'
            if teaching_entry.exists() and '</body>' in html:
                teaching_script = ('<script src="/js/teaching/index.js'
                                   f'?v={GW_VERSION}"></script>')
                html = html.replace('</body>', f'    {teaching_script}\n</body>', 1)
            from flask import Response
            response = Response(html, mimetype='text/html')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma']        = 'no-cache'
        return response

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
    }


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
        return ok({'archived': account_id, 'transactions_preserved': txn_count})


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
            'months_observed': len(seen),
        })
    return out


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
    return out


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
                session.add(cat)
                session.flush()
            cat_name = cat.name  # normalize to existing casing if it matched

        item = BudgetItem(
            type=body['type'],
            name=body['name'],
            amount=float(body['amount']),
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
    with db_session() as session:
        # Deactivate any existing plan
        for old in session.query(BudgetPlan).filter_by(is_active=True).all():
            old.is_active = False

        plan = BudgetPlan(
            goal_amount=float(body['goal_amount']),
            goal_months=int(body['goal_months']),
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

    program_totals = {'pslf': 120, 'ibr': 240, 'paye': 240, 'save': 240, 'other': 120}
    today = date.today()
    cards, undated = [], []

    for d in session.query(DebtAccount).filter_by(is_active=True).all():
        bal = d.current_balance if d.current_balance is not None else (d.begin_balance or 0)

        raw = pslf_all.get(str(d.id))
        is_pslf, forgive_after = False, None
        if raw:
            if raw is True:
                # Legacy shape: flagged, but nothing recorded about progress.
                # Enabled and undatable — the honest-null case, and the one that
                # produced the eighteen-year figure by being amortised instead.
                is_pslf = True
                undated.append(d.name)
            elif isinstance(raw, dict) and raw.get('enabled'):
                is_pslf = True
                total = program_totals.get(raw.get('program') or 'pslf', 120)
                made = raw.get('paymentsMade')
                if made is None and raw.get('startDate'):
                    # Derive from when income-driven repayment began, as the
                    # client's _monthsBetween does.
                    try:
                        st = date.fromisoformat(str(raw['startDate'])[:10])
                        made = max(0, (today.year - st.year) * 12 + (today.month - st.month)
                                   - (1 if today.day < st.day else 0))
                    except (ValueError, TypeError):
                        made = None
                if made is None:
                    undated.append(d.name)          # do not guess: see below
                else:
                    forgive_after = max(0, int(total) - int(made))

        cards.append(Card(
            balance=float(bal or 0),
            rate=float(d.interest_rate or 0),
            minimum=float(d.minimum_payment or 0),
            name=d.name or 'Card',
            is_lease=(d.debt_type or 'credit') == 'lease',
            end_month=d.end_date.strftime('%Y-%m') if d.end_date else None,
            is_pslf=is_pslf,
            forgive_after_months=forgive_after,
        ))

    budget = float(setting('monthly_budget', 1500) or 1500)
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
                                      recurring=trim_candidates(session))
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
                recurring=trim_candidates(session))
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


@debt_bp.route('', methods=['POST'])
@require_json
def create_debt():
    body = request.json
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
            begin_balance=float(body.get('begin_balance', 0)),
            current_balance=float(body.get('current_balance', 0)),
            interest_rate=float(body.get('interest_rate', 0)),
            minimum_payment=float(body.get('minimum_payment', 0)),
            due_day=body.get('due_day'),
            start_date=start_date,
            end_date=end_date,
            debt_type=body.get('debt_type', 'credit'),
        )
        session.add(debt)
        session.flush()  # get debt.id

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
        for field in ['name', 'current_balance', 'interest_rate',
                      'minimum_payment', 'due_day', 'linked_account_id',
                      'credit_limit', 'debt_type']:
            if field in body:
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
        return ok({'deleted': debt_id})


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
    resp = _ai_chat_cloud(body) if _ai_provider() == 'cloud' else _ai_chat_local(body)
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
                    'message': 'AI extraction is unavailable — check your AI settings and try again.'})

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
        if apr is not None:
            debt.interest_rate = float(apr)
        if min_payment is not None:
            debt.minimum_payment = round(float(min_payment), 2)

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
    if not matched:
        return {'confidence_pct': None, 'trend': None, 'avg_variance_pct': None,
                'samples': 0, 'reasoning': 'No snapshot history yet for this milestone.'}
    variances = [e.variance_pct for e in matched if e.variance_pct is not None]
    if not variances:
        return {'confidence_pct': None, 'trend': None, 'avg_variance_pct': None,
                'samples': len(matched), 'reasoning': 'No variance data yet.'}
    avg_variance = sum(variances) / len(variances)
    # variance_pct = (actual-expected)/expected*100 — positive means AHEAD of
    # pace, which never lowers confidence; only running behind pace does.
    confidence = max(0, min(100, round(100 + min(0, avg_variance) * 2)))
    trend = 'ahead' if avg_variance > 5 else 'behind' if avg_variance < -5 else 'on_pace'
    return {
        'confidence_pct': confidence, 'trend': trend,
        'avg_variance_pct': round(avg_variance, 1), 'samples': len(matched),
        'reasoning': f'{len(matched)} snapshot(s) tracked, {trend.replace("_", " ")}',
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

    by_class = {}
    for p in positions:
        cls = p.get('asset_class')
        if cls:
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
    Also includes derived flags: api_key_configured (bool as string).
    Never returns the actual API key value — only whether one is set.
    """
    with db_session() as session:
        settings = {s.key: s.value for s in session.query(AppSetting).all()}

    # Add derived flags (never expose the raw key)
    api_key = _get_api_key()
    settings['api_key_configured'] = 'true' if api_key else 'false'
    settings.pop('api_key', None)   # never send the key value to the frontend

    # Default ai_enabled to 'true' if not yet set
    if 'ai_enabled' not in settings:
        settings['ai_enabled'] = 'true'

    return ok(settings)


@settings_bp.route('', methods=['PATCH'])
@require_json
def update_settings():
    """Update one or more app settings. Never accepts api_key directly."""
    body = request.json
    # Security: API key must go through /api/settings/api-key, not here
    body.pop('api_key', None)

    with db_session() as session:
        for key, value in body.items():
            setting = _get_setting(session, key)
            if setting:
                setting.value = str(value)
            else:
                session.add(AppSetting(key=key, value=str(value)))
        session.commit()
        return ok({'updated': list(body.keys())})


@settings_bp.route('/api-key', methods=['POST'])
@require_json
def save_api_key():
    """
    Securely save the Anthropic API key to config.json on disk.
    Never stored in the database — stays in the filesystem config only.
    Returns only a success flag, never echoes the key back.
    """
    key = (request.json.get('key') or '').strip()
    if not key:
        return err('key is required')
    if not key.startswith('sk-ant-'):
        return err('Invalid key format — Anthropic keys start with sk-ant-')

    # Write to config.json in the app data directory
    config_path = DATA_DIR / 'config.json'
    try:
        cfg = {}
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        cfg['ANTHROPIC_API_KEY'] = key
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
        return ok({'saved': True, 'configured': True})
    except Exception as e:
        logging.error('Failed to save API key: %s', e)
        return err(f'Could not save key: {e}', 500)


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
            api_key  = _get_api_key()
            settings['api_key_configured'] = 'true' if api_key else 'false'
            settings.pop('api_key', None)
            if 'ai_enabled' not in settings:
                settings['ai_enabled'] = 'true'

            # ── Budget items ───────────────────────────────────────────────────
            from core.database import BudgetItem
            budget_items = session.query(BudgetItem).filter_by(is_active=True) \
                                  .order_by(BudgetItem.type, BudgetItem.sort_order).all()
            incomes  = [{'id':i.id,'name':i.name,'amount':i.amount}
                        for i in budget_items if i.type == 'income']
            expenses = [{'id':i.id,'name':i.name,'amount':i.amount,
                         'cat': i.category or 'Other'}
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
        bmoved = session.query(BudgetItem).filter_by(category_id=source.id).all()
        for b in bmoved: b.category_id = target.id
        if not source.is_system: session.delete(source)
        session.commit()
        return ok({'transactions_moved': len(moved), 'budget_items_moved': len(bmoved),
                   'target': serialize_category(target)})


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
                # Category doesn't exist yet — create it
                new_cat = Category(name=new_cat_name, is_system=False)
                session.add(new_cat)
                session.flush()
                cat_map[new_cat_name.lower()] = new_cat

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

    # Attach prices from cache
    result = []
    for pos in positions.values():
        if pos['total_shares'] < 0.00001:
            continue

        avg_cost = pos['total_cost'] / pos['total_shares'] if pos['total_shares'] else 0

        price_row = session.get(PriceCache, pos['ticker'])
        if price_row:
            current_price    = price_row.price
            company_name     = price_row.company_name or pos['ticker']
            day_change       = price_row.day_change or 0
            day_change_pct   = price_row.day_change_pct or 0
        else:
            # No price yet — use avg cost as placeholder
            current_price    = avg_cost
            company_name     = pos['ticker']
            day_change       = 0
            day_change_pct   = 0

        market_value    = pos['total_shares'] * current_price
        unrealized_gain = market_value - pos['total_cost']
        unrealized_pct  = (unrealized_gain / pos['total_cost'] * 100) if pos['total_cost'] else 0

        result.append({
            'ticker':          pos['ticker'],
            'account_id':      pos['account_id'],
            'security_type':   pos['security_type'],
            'company_name':    company_name,
            'total_shares':    round(pos['total_shares'], 6),
            'avg_cost_basis':  round(avg_cost, 4),
            'total_cost':      round(pos['total_cost'], 2),
            'current_price':   round(current_price, 4),
            'market_value':    round(market_value, 2),
            'unrealized_gain': round(unrealized_gain, 2),
            'unrealized_pct':  round(unrealized_pct, 2),
            'day_change':      round(day_change, 4),
            'day_change_pct':  round(day_change_pct, 2),
            'price_stale':     price_row is None,
            'lots':            pos['lots'],
        })

    # Sort by market_value descending
    result.sort(key=lambda x: x['market_value'], reverse=True)

    # Inject user-defined asset_class and expense_ratio from app_settings
    ac_setting = _get_setting(session, 'inv_asset_classes_json')
    er_setting = _get_setting(session, 'inv_expense_ratios_json')
    asset_classes   = json.loads(ac_setting.value)  if ac_setting  else {}
    expense_ratios  = json.loads(er_setting.value)  if er_setting  else {}

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
    _EXPENSE_RATIO_DEFAULTS = {
        'VOO':0.03,'VTI':0.03,'VUG':0.04,'VTV':0.04,'VXUS':0.07,
        'BND':0.03,'VNQ':0.13,'VWO':0.08,'EFA':0.07,'EEM':0.68,
        'SCHB':0.03,'SCHA':0.04,'SCHG':0.04,'SCHD':0.06,
        'IVV':0.03,'SPY':0.0945,'QQQ':0.2,'GLD':0.4,'SLV':0.5,
    }

    for p in result:
        t = p['ticker']
        p['asset_class']    = asset_classes.get(t) or _ASSET_CLASS_DEFAULTS.get(t) or None
        p['expense_ratio']  = expense_ratios.get(t) if t in expense_ratios else _EXPENSE_RATIO_DEFAULTS.get(t)

    # Portfolio totals
    total_cost         = sum(p['total_cost']    for p in result)
    total_market_value = sum(p['market_value']  for p in result)
    total_gain         = sum(p['unrealized_gain'] for p in result)
    total_gain_pct     = (total_gain / total_cost * 100) if total_cost else 0

    summary = {
        'total_cost':         round(total_cost, 2),
        'total_market_value': round(total_market_value, 2),
        'total_gain':         round(total_gain, 2),
        'total_gain_pct':     round(total_gain_pct, 2),
        'position_count':     len(result),
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
    """Get or update the ticker → expense_ratio mapping stored in app_settings."""
    with db_session() as session:
        if request.method == 'GET':
            s = _get_setting(session, 'inv_expense_ratios_json')
            return ok(json.loads(s.value) if s else {})

        body = request.get_json(silent=True) or {}
        existing = _get_setting(session, 'inv_expense_ratios_json')
        current  = json.loads(existing.value) if existing else {}
        current.update({k.upper(): float(v) for k, v in body.items() if v is not None})
        payload = json.dumps(current)
        if existing:
            existing.value      = payload
            existing.updated_at = datetime.utcnow()
        else:
            session.add(AppSetting(key='inv_expense_ratios_json', value=payload))
        session.commit()
        return ok(current)


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


@trip_bp.route('/flight-price', methods=['GET'])
def trip_flight_price():
    """
    Real live flight price search (flight_price.py, SerpApi's Google
    Flights engine — GROUNDWORK_LLM_BUILD_PLAN.md decision #7, previously
    deferred). Unlike gas-price/distance above, this DOES send the user's
    route and dates to a third party — that's inherent to flight search,
    not avoidable the way the gas-price national-average query is. Called
    only from an explicit "Search live flight prices" action in the UI,
    never automatically — SerpApi's free tier is 100 searches/month and
    the trip planner recomputes on every keystroke, so this must not be on
    that automatic path.
    """
    import flight_price
    origin        = (request.args.get('origin') or '').strip()
    destination   = (request.args.get('destination') or '').strip()
    outbound_date = (request.args.get('outbound_date') or '').strip()
    return_date   = (request.args.get('return_date') or '').strip() or None
    try:
        travelers = int(request.args.get('travelers', 1))
    except (TypeError, ValueError):
        travelers = 1

    result = flight_price.search_flights(
        origin, destination, outbound_date, return_date, travelers,
        api_key=_get_flights_api_key(),
    )
    return ok(result)


@trip_bp.route('/budget', methods=['GET'])
def get_trip_budget():
    """Return any saved trip budget from app_settings."""
    with db_session() as session:
        row = _get_setting(session, 'trip_budget')
        if row and row.value:
            try:
                return ok(json.loads(row.value))
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
        'breakdown':        {},
    }


@networth_bp.route('/snapshots', methods=['GET'])
def list_snapshots():
    """Return snapshot history for the trending chart."""
    months = int(request.args.get('months', 24))
    with db_session() as session:
        rows = (session.query(NetWorthSnapshot)
                .order_by(NetWorthSnapshot.snapshot_date.desc())
                .limit(months)
                .all())
        rows.reverse()
        return ok([_serialize_snapshot(r) for r in rows])


@networth_bp.route('/snapshot', methods=['POST'])
def create_snapshot():
    """Manually take a net worth snapshot for the current month."""
    body  = request.get_json(silent=True) or {}
    force = bool(body.get('force', False))
    month_key = date.today().strftime('%Y-%m')

    with db_session() as session:
        existing = session.query(NetWorthSnapshot).filter_by(
            snapshot_date=month_key).first()
        if existing and not force:
            return ok({'taken': False,
                       'message': 'Snapshot already exists. Pass force=true to overwrite.'})
        assets      = float(body.get('assets',      0))
        liabilities = float(body.get('liabilities', 0))
        net_worth   = assets - liabilities
        if existing:
            existing.assets      = assets
            existing.liabilities = liabilities
            existing.net_worth   = net_worth
            snap = existing
        else:
            snap = NetWorthSnapshot(
                snapshot_date=month_key,
                assets=assets,
                liabilities=liabilities,
                net_worth=net_worth,
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


@settings_bp.route('/export-to-file', methods=['POST'])
def export_to_file():
    """
    Save export directly to the user's Downloads folder.
    Returns the full path so the app can tell the user exactly where it is.
    """
    from pathlib import Path as P
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
        dest     = P.home() / 'Downloads' / filename

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
    AI proxy with a pluggable provider. Routes to a LOCAL LLM (Ollama) by
    default so Groundwork is free out of the box, and falls back to the
    Anthropic cloud API when ai_provider == 'cloud'.

    Both paths return the Anthropic response shape
    ({content:[{type:'text', text:...}]}) so the frontend callAI() contract
    is byte-identical regardless of provider — no app.js changes required.
    """
    # Respect the user's AI toggle — return a friendly message, not an error code
    if not _ai_is_enabled():
        return ok({
            'ai_available': False,
            'reason':       'disabled',
            'message':      'AI features are turned off. You can enable them in Settings.',
        })

    body = request.json or {}
    if _ai_provider() == 'cloud':
        return _ai_chat_cloud(body)
    return _ai_chat_local(body)


def _ai_provider() -> str:
    """Active AI provider: 'local' (default, free) or 'cloud' (Anthropic)."""
    try:
        with db_session() as session:
            row = _get_setting(session, 'ai_provider')
            val = (row.value if row else '').strip().lower()
            return 'cloud' if val == 'cloud' else 'local'
    except Exception:
        return 'local'


# ── Local LLM (Ollama) ────────────────────────────────────────────────────────
DEFAULT_OLLAMA_ENDPOINT = 'http://localhost:11434'


def _local_endpoint() -> str:
    """Ollama base URL. Overridable via the local_endpoint setting."""
    try:
        with db_session() as session:
            row = _get_setting(session, 'local_endpoint')
            val = (row.value if row else '').strip()
            return val or DEFAULT_OLLAMA_ENDPOINT
    except Exception:
        return DEFAULT_OLLAMA_ENDPOINT


def _resolve_local_model(endpoint: str) -> str:
    """
    Which local model to narrate with. Resolution order:
      1. local_model setting, if the user pinned one
      2. auto-detect from Ollama's installed tags, preferring Qwen → Llama
      3. '' when nothing is reachable (caller degrades gracefully)

    The auto-detect step is what makes "Qwen got pulled from the registry"
    a non-event: swap in any other installed model and it's picked up with
    no code change.
    """
    try:
        with db_session() as session:
            row = _get_setting(session, 'local_model')
            configured = (row.value if row else '').strip()
            if configured:
                return configured
    except Exception:
        pass

    try:
        import urllib.request
        req = urllib.request.Request(f'{endpoint}/api/tags', method='GET')
        with urllib.request.urlopen(req, timeout=5) as r:
            tags = json.loads(r.read().decode('utf-8')).get('models', [])
        names = [m.get('name', '') for m in tags if m.get('name')]
        if not names:
            return ''
        for pref in ('qwen', 'llama', 'phi', 'mistral', 'gemma'):
            for n in names:
                if pref in n.lower():
                    return n
        return names[0]
    except Exception:
        return ''


def _ai_chat_local(body: dict):
    """Call a local Ollama model; return the Anthropic response shape."""
    import urllib.request
    import urllib.error

    endpoint = _local_endpoint()
    model = _resolve_local_model(endpoint)
    if not model:
        return ok({
            'ai_available': False,
            'reason':       'no_local_model',
            'message':      ('No local model reachable. Start Ollama and pull a model '
                             '(e.g. `ollama pull qwen2.5:7b-instruct`), or switch to the '
                             'cloud provider in Settings.'),
        })

    # Anthropic-style payload → Ollama messages (system becomes a leading message)
    messages = []
    if body.get('system'):
        messages.append({'role': 'system', 'content': body['system']})
    messages.extend(body.get('messages', []))

    # Qwen3-generation models "think" by default in Ollama: a long hidden
    # reasoning pass that, on CPU, either exceeds the timeout or consumes the
    # whole token budget before any answer is written — the response comes
    # back with empty `content`, which looks identical to a broken model.
    # voice_discipline_test.py hit and fixed this exact issue for the test
    # harness; mirror the same fix here so production doesn't quietly ship a
    # dead AI feature to anyone whose Ollama resolves a qwen3 model. Disable
    # via Ollama's documented top-level `think: false` switch (the
    # `/no_think` prompt token alone did not suppress it in testing).
    # Belt-and-suspenders: also send /no_think, raise the token budget, and
    # strip any residual <think> block from the response.
    is_qwen3 = 'qwen3' in model.lower()
    max_tokens = int(body.get('max_tokens', 1000))
    if is_qwen3 and messages:
        messages = [*messages[:-1], {**messages[-1], 'content': messages[-1]['content'] + ' /no_think'}]
        max_tokens = max(max_tokens, 768)

    payload = {
        'model':      model,
        'messages':   messages,
        'stream':     False,
        # Ollama's default keep_alive is 5 minutes — anything slower than
        # that between two reports (very normal usage: read one, go do
        # something else, come back) pays a full model-reload-from-disk
        # penalty on top of actual generation, on every single call. Keeping
        # it loaded for the length of a realistic session avoids that.
        'keep_alive': '30m',
        'options':  {
            # Low temperature keeps a small model on the voice rails and
            # discourages the invented certainty _GW_VOICE forbids.
            'temperature': float(body.get('temperature', 0.3)),
            'num_predict': max_tokens,
        },
    }
    if is_qwen3:
        payload['think'] = False  # Ollama API switch to turn off qwen3 reasoning

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(f'{endpoint}/api/chat', data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        # First token on a cold small model can be slow — be patient.
        with urllib.request.urlopen(req, timeout=180) as r:
            result = json.loads(r.read().decode('utf-8'))
        text = (result.get('message') or {}).get('content', '')
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        return jsonify({
            'content':  [{'type': 'text', 'text': text}],
            'model':    model,
            'provider': 'local',
        })
    except urllib.error.URLError as e:
        # Ollama not running / unreachable — degrade to the frontend fallbacks
        return ok({
            'ai_available': False,
            'reason':       'local_unreachable',
            'message':      (f'Local model not reachable at {endpoint}. '
                             'Is Ollama running? (`ollama serve`)'),
        })
    except Exception as e:
        return err(f'Local AI request failed: {e}', 500)


def _ai_chat_cloud(body: dict):
    """Proxy to the Anthropic API (opt-in cloud provider)."""
    import urllib.request
    import urllib.error

    api_key = _get_api_key()
    if not api_key:
        return ok({
            'ai_available': False,
            'reason':       'no_key',
            'message':      ('Cloud AI is selected but no Anthropic key is configured. '
                             'Add one in Settings → AI features, or switch to the local provider.'),
        })

    payload = {
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': body.get('max_tokens', 1000),
        'messages': body.get('messages', []),
    }
    if body.get('system'):
        payload['system'] = body['system']

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=data, method='POST'
        )
        req.add_header('Content-Type', 'application/json')
        req.add_header('x-api-key', api_key)
        req.add_header('anthropic-version', '2023-06-01')

        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read().decode('utf-8'))
            # Explicit marker (not just the absence of one) so the frontend's
            # attribution line ("Analyzed on your machine" vs "Powered by
            # Claude") never has to infer provider from a missing field.
            result['provider'] = 'cloud'
            return jsonify(result)

    except urllib.error.HTTPError as e:
        body_txt = e.read().decode('utf-8')
        try:
            msg = json.loads(body_txt).get('error', {}).get('message', body_txt)
        except Exception:
            msg = body_txt[:200]
        return err(f'AI API error: {msg}', 502)
    except Exception as e:
        return err(f'AI request failed: {e}', 500)


def _get_config_value(name: str) -> str:
    """
    Locate a secret/config value by name. Checks in order:
      1. <name> environment variable
      2. config.json in the app data directory (DATA_DIR)
      3. config.json next to server.py
      4. config.json in the user's home directory
    Never reads from the database — keys stay on the filesystem only.
    Shared by every external API key this app uses (Anthropic, EIA, ...) —
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


def _get_api_key() -> str:
    """The Anthropic API key — see _get_config_value for the lookup order."""
    return _get_config_value('ANTHROPIC_API_KEY')


def _get_eia_api_key() -> str:
    """
    The EIA (U.S. Energy Information Administration) open-data API key, for
    Phase 5A's real national-average gas price. Free, self-service key at
    https://www.eia.gov/opendata/register.php — same config.json/env lookup
    convention as the Anthropic key. Trip planning degrades to an honest
    estimate (gas_price.FALLBACK_PRICE) when this isn't configured, never
    a crash or a silently wrong "live" number.
    """
    return _get_config_value('EIA_API_KEY')


def _get_flights_api_key() -> str:
    """
    The SerpApi key for real live flight-price search (flight_price.py).
    Free, self-service key at https://serpapi.com/users/sign_up — same
    config.json/env lookup convention as every other external key this app
    uses. Trip planning degrades to the existing AI-estimated/manual-quote
    flight cost when this isn't configured — never a crash or a silently
    wrong "live" price.
    """
    return _get_config_value('FLIGHTS_API_KEY')


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
    """
    Diagnostic: which provider is active, whether it's reachable, and which
    model resolves. Powers a 'Test connection' button and lets beta testers
    confirm the local LLM is wired without touching a terminal.
    """
    provider = _ai_provider()
    out = {'enabled': _ai_is_enabled(), 'provider': provider}

    if provider == 'local':
        endpoint = _local_endpoint()
        out['endpoint'] = endpoint
        try:
            import urllib.request
            req = urllib.request.Request(f'{endpoint}/api/tags', method='GET')
            with urllib.request.urlopen(req, timeout=5) as r:
                tags = json.loads(r.read().decode('utf-8')).get('models', [])
            out['reachable']        = True
            out['installed_models'] = [m.get('name') for m in tags if m.get('name')]
            out['active_model']     = _resolve_local_model(endpoint)
        except Exception as e:
            out['reachable']        = False
            out['installed_models'] = []
            out['active_model']     = ''
            out['error']            = str(e)
    else:
        out['reachable']    = bool(_get_api_key())
        out['active_model'] = 'claude-haiku-4-5-20251001'

    return ok(out)


@ai_bp.route('/system-ram', methods=['GET'])
def ai_system_ram():
    """
    Phase 2B — the first-run trust surface (Blueprint §11.1). Reports free
    RAM so setup can honestly state what THIS machine can run, before
    anything else happens. Every tier is a legitimate path — no tier is
    framed as a downgrade or a failure to meet a spec.
      16GB+ free -> 'high' (qwen2.5:7b, ~5GB, sharper analysis)
      8-16GB free -> 'mid'  (phi3.5, ~2.2GB, the default)
      <8GB free  -> 'low'  (cloud key or fully structured, no local model)
    Uses available (not total) memory — total installed RAM overstates what
    a machine can actually spare for a model alongside everything else
    already running.
    """
    try:
        import psutil
        vm = psutil.virtual_memory()
        free_gb  = round(vm.available / (1024 ** 3), 1)
        total_gb = round(vm.total / (1024 ** 3), 1)
    except Exception as e:
        return ok({'available': False, 'error': str(e)})

    tier = 'high' if free_gb >= 16 else 'mid' if free_gb >= 8 else 'low'
    return ok({'available': True, 'free_gb': free_gb, 'total_gb': total_gb, 'tier': tier})


# ── Phase 6A: first-run model pull ────────────────────────────────────────────
# Completes the trust surface Phase 2B started: it's not enough to detect what
# a machine CAN run and set a preference — first run should actually fetch the
# model, with a real progress bar, so local AI works offline immediately after
# setup instead of silently failing the first time a narrative surface calls
# it. One pull at a time; state is in-process (a single desktop app instance),
# polled by the client rather than streamed, to keep the transport simple.
_pull_lock  = threading.Lock()
_pull_state = {'active': False, 'model': '', 'status': '', 'percent': 0, 'done': False, 'error': ''}


def _run_model_pull(model: str):
    import urllib.request
    endpoint = _local_endpoint()
    try:
        payload = json.dumps({'name': model, 'stream': True}).encode('utf-8')
        req = urllib.request.Request(f'{endpoint}/api/pull', data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=1800) as r:
            for raw_line in r:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line.decode('utf-8'))
                except (ValueError, UnicodeDecodeError):
                    continue
                total     = evt.get('total') or 0
                completed = evt.get('completed') or 0
                with _pull_lock:
                    _pull_state['status'] = evt.get('status', _pull_state['status'])
                    if total:
                        _pull_state['percent'] = round(completed / total * 100, 1)
                    if evt.get('error'):
                        _pull_state['error'] = str(evt['error'])
        with _pull_lock:
            _pull_state['done']   = True
            _pull_state['active'] = False
            if not _pull_state['error']:
                _pull_state['percent'] = 100
    except Exception as e:
        with _pull_lock:
            _pull_state['error']  = str(e)
            _pull_state['done']   = True
            _pull_state['active'] = False


@ai_bp.route('/pull-model', methods=['POST'])
@require_json
def ai_pull_model():
    """Start pulling a model in the background; poll /pull-status for progress."""
    model = (request.json.get('model') or '').strip()
    if not model:
        return err('model required')

    with _pull_lock:
        if _pull_state['active']:
            return err('A model pull is already in progress', 409)
        _pull_state.update({'active': True, 'model': model, 'status': 'starting',
                            'percent': 0, 'done': False, 'error': ''})

    threading.Thread(target=_run_model_pull, args=(model,), daemon=True).start()
    return ok({'started': True, 'model': model})


@ai_bp.route('/pull-status', methods=['GET'])
def ai_pull_status():
    with _pull_lock:
        return ok(dict(_pull_state))


# ── Install Ollama itself ────────────────────────────────────────────────────
# The gap Phase 6A didn't cover: pull-model only works once Ollama is already
# installed and running — if it isn't, onboarding's own comment says so
# plainly ("Ollama itself isn't reachable — nothing to pull toward") and just
# gives up on local AI, on every platform, not just Mac/Linux. The Windows
# offline installer solves this at INSTALL time by silently running a bundled
# OllamaSetup.exe; this solves it at RUN time instead, from inside Settings,
# so the online (small) installer and the Mac/Linux builds — none of which
# bundle Ollama — get the same one-click path Windows' offline installer had
# exclusively.
#
# Automation level is deliberately uneven across platforms, because the risk
# profile is uneven:
#   Windows — fully automated (download + silent install). Verified for real.
#   macOS   — automated download + place in /Applications + `open -a Ollama`
#             (the OS-sanctioned launch path, same as double-clicking in
#             Finder). Best-effort: no real Mac to verify Gatekeeper behavior
#             on a freshly-downloaded, unsigned-by-us zip.
#   Linux   — NOT auto-run. Ollama's official install script invokes sudo
#             internally on most distros; a GUI app silently subprocessing
#             that from a background thread has no TTY to satisfy a password
#             prompt and would just hang forever with no way for the user to
#             know why. Show the official one-liner instead — safe, still
#             far easier than the user having to go find it themselves.
_install_lock  = threading.Lock()
_install_state = {'active': False, 'stage': '', 'percent': 0, 'done': False,
                   'error': '', 'manual_command': '', 'needs_manual': False}

OLLAMA_WIN_URL = 'https://ollama.com/download/OllamaSetup.exe'
OLLAMA_MAC_URL = 'https://ollama.com/download/Ollama-darwin.zip'
OLLAMA_LINUX_INSTALL_CMD = 'curl -fsSL https://ollama.com/install.sh | sh'


def _download_with_progress(url: str, dest_path, stage_label: str):
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'Groundwork'})
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, 'wb') as f:
        total = int(resp.headers.get('Content-Length') or 0)
        read = 0
        chunk = 1024 * 256
        while True:
            block = resp.read(chunk)
            if not block:
                break
            f.write(block)
            read += len(block)
            with _install_lock:
                _install_state['stage'] = stage_label
                if total:
                    _install_state['percent'] = round(read / total * 100, 1)


def _run_install_ollama():
    import subprocess
    import tempfile
    import platform as _platform
    system = _platform.system()
    try:
        if system == 'Windows':
            with tempfile.TemporaryDirectory() as tmp:
                exe_path = Path(tmp) / 'OllamaSetup.exe'
                _download_with_progress(OLLAMA_WIN_URL, exe_path, 'Downloading Ollama…')
                with _install_lock:
                    _install_state['stage'] = 'Installing (this runs once)…'
                    _install_state['percent'] = 100
                subprocess.run(
                    [str(exe_path), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'],
                    timeout=300, check=True,
                )
        elif system == 'Darwin':
            import zipfile
            import shutil
            with tempfile.TemporaryDirectory() as tmp:
                zip_path = Path(tmp) / 'Ollama-darwin.zip'
                _download_with_progress(OLLAMA_MAC_URL, zip_path, 'Downloading Ollama…')
                with _install_lock:
                    _install_state['stage'] = 'Installing…'
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(tmp)
                extracted = Path(tmp) / 'Ollama.app'
                if not extracted.exists():
                    raise RuntimeError('Ollama.app not found in downloaded archive')
                dest = Path('/Applications/Ollama.app')
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(extracted), str(dest))
                with _install_lock:
                    _install_state['stage'] = 'Starting Ollama…'
                subprocess.run(['open', '-a', 'Ollama'], timeout=30, check=True)
        else:
            # Linux: surfaced as needs_manual so the UI shows the copyable
            # command instead of pretending to have run it.
            with _install_lock:
                _install_state['needs_manual']   = True
                _install_state['manual_command'] = OLLAMA_LINUX_INSTALL_CMD
                _install_state['done']           = True
                _install_state['active']         = False
            return

        # Windows/macOS: give the newly-installed server a moment to come up,
        # then confirm it's actually reachable before declaring success —
        # installing the app isn't the same as it being ready to serve.
        with _install_lock:
            _install_state['stage'] = 'Waiting for Ollama to start…'
        import urllib.request as _ur
        import time as _t
        reachable = False
        for _ in range(20):
            try:
                _ur.urlopen(_ur.Request(f'{DEFAULT_OLLAMA_ENDPOINT}/api/tags'), timeout=2)
                reachable = True
                break
            except Exception:
                _t.sleep(1)
        with _install_lock:
            _install_state['done']   = True
            _install_state['active'] = False
            if not reachable:
                _install_state['error'] = 'Installed, but Ollama isn\'t responding yet — try Test connection in a moment.'
    except Exception as e:
        with _install_lock:
            _install_state['error']  = str(e)
            _install_state['done']   = True
            _install_state['active'] = False


@ai_bp.route('/install-ollama', methods=['POST'])
def ai_install_ollama():
    with _install_lock:
        if _install_state['active']:
            return err('An install is already in progress', 409)
        _install_state.update({'active': True, 'stage': 'starting', 'percent': 0,
                               'done': False, 'error': '', 'manual_command': '',
                               'needs_manual': False})
    threading.Thread(target=_run_install_ollama, daemon=True).start()
    return ok({'started': True})


@ai_bp.route('/install-status', methods=['GET'])
def ai_install_status():
    with _install_lock:
        return ok(dict(_install_state))


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

auto_import_bp = Blueprint('auto_import', __name__)


@auto_import_bp.route('/queue', methods=['POST'])
def auto_import_queue():
    """Receive a detected file from the Downloads watcher in launch.py."""
    body     = request.get_json(silent=True) or {}
    filename = (body.get('filename') or '').strip()
    content  = body.get('content', '')
    path     = (body.get('path') or '').strip()
    if not filename or not content:
        return ok({'queued': False})
    _auto_import_queue.append({'filename': filename, 'content': content, 'path': path})
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

    from pathlib import Path as P
    try:
        target    = P(file_path).resolve()
        downloads = P.home() / 'Downloads'
        target.relative_to(downloads)
    except (ValueError, OSError):
        return err('File path is not within the Downloads folder', 403)

    if not target.exists():
        return ok({'deleted': False, 'reason': 'File no longer exists'})

    try:
        target.unlink()
        print(f'[Security] Deleted invalid import file: {target.name}')
        return ok({'deleted': True, 'filename': target.name})
    except OSError as e:
        return err(f'Could not delete file: {e}', 500)


@auto_import_bp.route('/pending', methods=['GET'])
def auto_import_pending():
    """Return and clear the next queued file for the frontend to process."""
    if not _auto_import_queue:
        return ok(None)
    item = _auto_import_queue.pop(0)
    return ok(item)


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

                if new_bal is not None and abs(old_bal - new_bal) > 0.01:
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


if __name__ == '__main__':
    app = create_app()
    logging.basicConfig(level=logging.INFO)
    app.run(host='127.0.0.1', port=8765, debug=False, threaded=True)
