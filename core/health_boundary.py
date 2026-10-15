"""The health privacy enforcement point (gw 2.0/HEALTH_PRIVACY_H6.md, item 45 stage 1, P1-P9 ruled 2026-10-12).

One place decides what is health-sensitive and scrubs it before any sink: logs, exports, the model's context, the AI
log, the Historian. The health terms are the one protected list's health block (core/solution.py NECESSITY_FLOOR),
never a second list. What it removes is text that says who or where: a health transaction's merchant and description,
a health record's names and reasons. A category and an amount stay, because they are the person's own budget.

HEALTH_SINKS is the registry P9 reconciles against the code: a new sink fails the gate until it is listed here with
how it is enforced.
"""
import logging
import re
import threading

from core import solution as _sol

# ── P1: the classifier, from the one list ───────────────────────────────────
_FLOOR = _sol.NECESSITY_FLOOR
HEALTH_TERMS = _FLOOR[_FLOOR.index('health care'):_FLOOR.index('emergency room') + 1]
_HEALTH_RUNS = tuple(_sol._floor_words(t) for t in HEALTH_TERMS)
_HEALTH_WHOLE = frozenset(_sol._floor_words(t) for t in ('health', 'health insurance'))


def is_health_category(name):
    """True for a category the protected list names as health (whole words, as is_protected matches)."""
    words = _sol._floor_words(name or '')
    if not words:
        return False
    if words in _HEALTH_WHOLE:
        return True
    return any(_sol._has_run(words, run) for run in _HEALTH_RUNS)


def health_category_ids(session):
    """Every category that is health, and every child of one."""
    from core.database import Category
    cats = session.query(Category).all()
    ids = {c.id for c in cats if is_health_category(c.name)}
    changed = True
    while changed:
        changed = False
        for c in cats:
            if c.parent_id in ids and c.id not in ids:
                ids.add(c.id)
                changed = True
    return ids


# Item 86 F6 (HSA_FSA.md, ruled 2026-10-14): every row of an HSA or FSA account is health, whatever its category -
# its statement names the pharmacy, the doctor, the lab. The balance and the limit stay ordinary money.
HEALTH_ACCOUNT_TYPES = ('hsa', 'fsa')
_MONEY_WORDS = frozenset(('fee', 'fees', 'monthly', 'maintenance', 'service', 'charge', 'distribution', 'withdrawal',
                          'transfer', 'payment', 'interest', 'contribution', 'deposit', 'dividend', 'account', 'hsa',
                          'fsa', 'card', 'debit', 'adjustment', 'reversal', 'to', 'from', 'the', 'of', 'a'))


def health_account_ids(session):
    from core.database import Account
    return {a.id for a in session.query(Account.id).filter(Account.type.in_(HEALTH_ACCOUNT_TYPES)).all()}


def health_rows(session):
    """A test for one transaction: health by its category (P1) or by its account (item 86 F6)."""
    cids, aids = health_category_ids(session), health_account_ids(session)
    return lambda t: t.category_id in cids or t.account_id in aids


# ── P1: the scrubber ────────────────────────────────────────────────────────
MIN_MARKER = 4                 # shorter text is too common to stand for a place ("CVS" is 3 - kept by its whole word)
_lock = threading.Lock()
_markers = {}                  # lowercased marker -> replacement
_pattern = None


def _key(text):
    return ' '.join(str(text or '').split()).strip().lower()


def refresh(session):
    """Learn the text to remove: health transactions' merchants and descriptions (by their category), and the health
    record tables' names and reasons. Called at startup and after an import; the scrubber never queries the database
    itself, so a log line can never recurse into it."""
    global _pattern
    from core.database import Category, Transaction
    found = {}
    ids = health_category_ids(session)
    names = {c.id: c.name for c in session.query(Category).filter(Category.id.in_(ids)).all()} if ids else {}
    if ids:
        for merchant, desc, cid in session.query(Transaction.merchant, Transaction.description, Transaction.category_id) \
                .filter(Transaction.category_id.in_(ids)).all():
            label = f'[health: {names.get(cid, "health")}]'
            for t in (merchant, desc):
                k = _key(t)
                if len(k) >= MIN_MARKER or (k and k.isalpha() and len(k) >= 3):
                    found[k] = label
    # Item 86 F6: an HSA's or FSA's spending names where the care was. Its deposits, interest and fees do not, and a
    # generic word learned as a marker ("Interest") would be scrubbed from every log and prompt - so only the debits,
    # and never a description made only of money words.
    aids = health_account_ids(session)
    if aids:
        for merchant, desc in session.query(Transaction.merchant, Transaction.description) \
                .filter(Transaction.account_id.in_(aids), Transaction.type == 'debit').all():
            for t in (merchant, desc):
                k = _key(t)
                if set(re.findall(r'[a-z]+', k)) <= _MONEY_WORDS:
                    continue
                if len(k) >= MIN_MARKER or (k and k.isalpha() and len(k) >= 3):
                    found.setdefault(k, '[health: HSA/FSA]')
    for table, cols in (('health_plans', ('name',)), ('person_assignments', ('reason', 'source')),
                        ('health_plan_term_versions', ('reason', 'source'))):
        try:
            from sqlalchemy import text as _t
            for row in session.execute(_t(f'SELECT {", ".join(cols)} FROM {table}')).fetchall():
                for v in row:
                    k = _key(v)
                    if len(k) >= MIN_MARKER:
                        found[k] = '[health record]'
        except Exception:      # a database from before the table existed
            continue
    with _lock:
        _markers.clear()
        _markers.update(found)
        keys = sorted(_markers, key=len, reverse=True)
        _pattern = re.compile('|'.join(re.escape(k) for k in keys), re.I) if keys else None
    return len(found)


def scrub(text):
    """The text with every known health marker replaced by its class. Pure: no database, no logging."""
    if not text or _pattern is None:
        return text
    s = str(text)
    return _pattern.sub(lambda m: _markers.get(m.group(0).lower(), '[health]'), s)


def scrub_obj(obj):
    """scrub() through a JSON-like value: strings in dicts and lists."""
    if isinstance(obj, str):
        return scrub(obj)
    if isinstance(obj, list):
        return [scrub_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: scrub_obj(v) for k, v in obj.items()}
    return obj


# ── P2: every log record passes the scrubber ────────────────────────────────
class HealthLogFilter(logging.Filter):
    def filter(self, record):
        try:
            msg = record.getMessage()
            clean = scrub(msg)
            if clean != msg:
                record.msg, record.args = clean, ()
        except Exception:
            pass
        return True


_FILTER = HealthLogFilter()


def install_log_filter():
    """On the root logger and every handler it has now. Idempotent."""
    root = logging.getLogger()
    if _FILTER not in root.filters:
        root.addFilter(_FILTER)
    for h in root.handlers:
        if _FILTER not in h.filters:
            h.addFilter(_FILTER)
    return _FILTER


# ── P9: the sink registry ───────────────────────────────────────────────────
# (file, function or '*', kind) -> how it is enforced. Logs and prints are registered per file: the log filter covers
# every record, so a file is what has to be known. Everything else is registered per function.
LOG = 'scrubbed by HealthLogFilter on every handler (P2)'
HEALTH_SINKS = {
    ('server.py', '*', 'log'): LOG, ('launch.py', '*', 'log'): LOG, ('migrate.py', '*', 'log'): LOG,
    ('core/engine.py', '*', 'log'): LOG, ('utility_price.py', '*', 'log'): LOG, ('price_engine.py', '*', 'log'): LOG,
    ('gas_price.py', '*', 'log'): LOG, ('core/airfare.py', '*', 'log'): LOG, ('core/per_diem.py', '*', 'log'): LOG,
    ('trip_distance.py', '*', 'log'): LOG,
}


# Every other sink, per function (P9). Each line says how H6 holds there.
_NO_HEALTH_INPUT = 'outbound: builds its request from no transaction or health record (P7, s208 checks the imports)'
for _f, _fn in (('bank_agent_window.py', 'child_main'), ('bank_agent_window.py', 'fetch_child_main'),
                ('bank_window.py', 'child_main'), ('core/airfare.py', '_fetch_airports'), ('core/airfare.py', '_get'),
                ('core/per_diem.py', '_get'), ('flights_window.py', 'create_window'), ('gas_price.py', '_fetch_from_eia'),
                ('hotels_window.py', 'create_window'), ('launch.py', '_post_queue_item'), ('launch.py', '_wait_for_flask'),
                ('launch.py', 'main'), ('price_engine.py', '_http_get_json'), ('server.py', '_eia_weekly_gas'),
                ('server.py', '_eia_weekly_heating'), ('server.py', '_steo'), ('server.py', 'create_app'),
                ('trip_distance.py', '_geocode'), ('utility_price.py', '_fetch_electricity'),
                ('utility_price.py', '_fetch_natural_gas')):
    HEALTH_SINKS[(_f, _fn, 'network')] = _NO_HEALTH_INPUT
HEALTH_SINKS.update({
    ('core/airfare.py', '_write', 'file'): 'public fare tables only (DOT), no personal data',
    ('core/airfare.py', 'refresh', 'file'): 'public fare tables only (DOT), no personal data',
    ('core/per_diem.py', 'refresh', 'file'): 'public per-diem tables only (GSA), no personal data',
    ('launch.py', '_start_server', 'file'): 'the startup log; the log filter scrubs it (P2)',
    ('migrate.py', '_remove_cloud_ai', 'file'): 'config.json without the old API key; no personal data',
    ('server.py', 'ai_voice_miss', 'file'): 'model text that failed the voice check, scrubbed before writing (P5)',
    ('server.py', '_write_backup', 'file'): 'every backup and safety copy: sealed with the backup key once protection is on (item 81 B1), with BACKUP_STATEMENT (P4)',
    ('server.py', 'backup_encrypt_old', 'file'): 'an old plain backup re-saved sealed (item 81 B7)',
    ('server.py', 'export_to_file', 'file'): 'health spending left out unless include_health (P3)',
    ('server.py', 'year_end_export', 'file'): 'item 65 W9: health spending left out unless include_health (P3)',
    ('server.py', 'restore_backup', 'file'): 'restores the person\'s own backup, after a safety copy (P4)',
    ('server.py', 'restore_backup_upload', 'file'): 'restores the person\'s own backup file, after a safety copy (P4)',
    ('server.py', 'auto_import_statement_bytes', 'download'): 'serves the person\'s own downloaded statement back to the page, on the computer',
    ('server.py', 'create_app', 'download'): 'serves the app\'s own files (static), no data',
    ('server.py', '_ai_chat_local', 'ai_log'): 'the AI log: scrubbed in _ai_log_write (P6), prompt scrubbed first (P5)',
    ('server.py', '_ai_chat_stream', 'ai_log'): 'the AI log: scrubbed in _ai_log_write (P6), prompt scrubbed first (P5)',
    ('server.py', 'why_route', 'ai_log'): 'the AI log: scrubbed in _ai_log_write (P6)',
})


def register(file, function, kind, how):
    HEALTH_SINKS[(file, function, kind)] = how
