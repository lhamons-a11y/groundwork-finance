"""
quicken_import.py — QIF, OFX/QFX, and CSV import for Groundwork.

Two layers of functionality:

1. Parsing helpers (used by /api/import/preview for non-CSV formats):
   - QIFParser           — parses QIF text into { account: {transactions, type} }
   - parse_qfx(text)     — parses OFX/QFX <STMTTRN> blocks into records
   - parse_qif_date(s)   — QIF date string -> date
   - parse_amount(s)     — currency string -> float
   - normalize_category(s) — Quicken/Money category name -> Groundwork category

2. Direct-to-database import (used by /api/import/quicken):
   - ImportContext       — tracks created/skipped/errors/warnings, dry_run
   - import_qif/import_qfx/import_csv(path, ctx, ...) -> bool
"""

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path


GROUNDWORK_CATEGORIES = [
    'Food', 'Transportation', 'Utilities', 'Entertainment', 'Healthcare',
    'Insurance', 'Housing', 'Personal', 'Income', 'Debt', 'Savings',
    'Transfer', 'Other',
]


# ── Category normalization ───────────────────────────────────────────────────
# Quicken/Money category names (lowercase, brackets stripped) -> Groundwork

_CATEGORY_MAP = {
    'groceries': 'Food', 'food': 'Food', 'dining': 'Food', 'restaurants': 'Food',
    'fast food': 'Food', 'coffee shops': 'Food',

    'auto & transport': 'Transportation', 'gas & fuel': 'Transportation',
    'auto payment': 'Transportation', 'auto insurance': 'Insurance',
    'parking': 'Transportation', 'public transportation': 'Transportation',
    'ride share': 'Transportation',

    'utilities': 'Utilities', 'mobile phone': 'Utilities', 'cell phone': 'Utilities',
    'cable': 'Utilities', 'cable/satellite': 'Utilities', 'internet': 'Utilities',
    'electric': 'Utilities', 'electricity': 'Utilities', 'gas/electric': 'Utilities',
    'water': 'Utilities',

    'entertainment': 'Entertainment', 'movies & dvds': 'Entertainment',
    'music': 'Entertainment', 'hobbies': 'Entertainment',
    'streaming': 'Entertainment',

    'health & fitness': 'Healthcare', 'doctor': 'Healthcare', 'dentist': 'Healthcare',
    'pharmacy': 'Healthcare', 'health insurance': 'Insurance', 'gym': 'Healthcare',

    'insurance': 'Insurance', 'life insurance': 'Insurance',

    'mortgage & rent': 'Housing', 'rent': 'Housing', 'mortgage': 'Housing',
    'home improvement': 'Housing', 'home services': 'Housing',
    'home insurance': 'Insurance',

    'shopping': 'Personal', 'clothing': 'Personal', 'personal care': 'Personal',
    'gifts & donations': 'Personal', 'gift': 'Personal',

    'income': 'Income', 'paycheck': 'Income', 'salary': 'Income',
    'bonus': 'Income', 'interest income': 'Income',

    'loan payment': 'Debt', 'credit card payment': 'Debt', 'loans': 'Debt',
    'student loan': 'Debt',

    'transfer': 'Transfer', 'transfer for cash spending': 'Transfer',
    'credit card transfer': 'Transfer', 'balance adjustments': 'Transfer',

    'savings': 'Savings', 'investments': 'Savings', 'retirement': 'Savings',
}


def normalize_category(raw: str) -> str:
    """Map a Quicken/Money category label to a Groundwork category."""
    if not raw:
        return 'Other'
    key = raw.strip().strip('[]').lower()
    # QIF subcategories use "Parent:Child" — try the child, then the parent
    if ':' in key:
        parent, _, child = key.partition(':')
        if child in _CATEGORY_MAP:
            return _CATEGORY_MAP[child]
        if parent in _CATEGORY_MAP:
            return _CATEGORY_MAP[parent]
        key = child
    return _CATEGORY_MAP.get(key, 'Other')


# ── Date / amount parsing ───────────────────────────────────────────────────

def parse_qif_date(s: str):
    """
    Parse a QIF date string. QIF commonly uses M/D'YY, M/D/YY, M/D/YYYY,
    or MM/DD/YYYY. Returns a date object or None.
    """
    if not s:
        return None
    s = s.strip().replace("'", "/")
    for fmt in ('%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%m-%d-%Y', '%m-%d-%y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(s: str):
    """Parse a QIF/CSV amount string into a float, or None if invalid."""
    if s is None:
        return None
    s = str(s).strip().replace(',', '').replace('$', '')
    if not s:
        return None
    negative = s.startswith('(') and s.endswith(')')
    s = s.strip('()')
    try:
        val = float(s)
    except ValueError:
        return None
    return -val if negative else val


# ── QIF parsing ───────────────────────────────────────────────────────────────

class QIFParser:
    """
    Parses QIF file text into:
        { account_name: { 'type': 'bank'|'cash'|'ccard'|..., 'transactions': [...] } }

    Each transaction dict has raw QIF field values:
        date, amount, payee, memo, category, cleared, number
    """

    _TYPE_HEADERS = {
        '!type:bank':  'bank',
        '!type:cash':  'cash',
        '!type:ccard': 'ccard',
        '!type:invst': 'invst',
        '!type:oth a': 'asset',
        '!type:oth l': 'liability',
    }

    def parse(self, text: str) -> dict:
        accounts = {}
        current_account = 'Default'
        current_type = 'bank'
        accounts[current_account] = {'type': current_type, 'transactions': []}

        txn = {}
        for raw_line in text.splitlines():
            line = raw_line.rstrip('\r\n')
            if not line:
                continue

            lowered = line.strip().lower()

            if lowered.startswith('!account'):
                continue

            if lowered in self._TYPE_HEADERS:
                current_type = self._TYPE_HEADERS[lowered]
                if current_account not in accounts:
                    accounts[current_account] = {'type': current_type, 'transactions': []}
                else:
                    accounts[current_account]['type'] = current_type
                continue

            if line == '^':
                if txn:
                    accounts[current_account]['transactions'].append(txn)
                txn = {}
                continue

            code, value = line[0], line[1:]
            if code == 'D':
                txn['date'] = value
            elif code in ('T', 'U'):
                # T = amount, U = amount (alternate field) — last one wins
                txn['amount'] = value
            elif code == 'P':
                txn['payee'] = value
            elif code == 'M':
                txn['memo'] = value
            elif code == 'L':
                txn['category'] = value
            elif code == 'C':
                txn['cleared'] = value.upper() in ('X', 'R', 'C')
            elif code == 'N':
                txn['number'] = value
            # S/E (split category/amount), A (address) are ignored —
            # split detail isn't needed for a flat transaction import.

        if txn:
            accounts[current_account]['transactions'].append(txn)

        return accounts


# ── OFX/QFX parsing ───────────────────────────────────────────────────────────

def _ofx_field(block: str, tag: str) -> str:
    m = re.search(rf'<{tag}>([^<\r\n]*)', block, re.IGNORECASE)
    return m.group(1).strip() if m else ''


def parse_qfx(text: str) -> list:
    """
    Parse OFX/QFX <STMTTRN> blocks into normalized records:
        { date (ISO str), payee, memo, amount (signed float),
          type: 'credit'|'debit', category, cleared: bool }
    """
    records = []
    for m in re.finditer(r'<STMTTRN>(.*?)</STMTTRN>', text, re.IGNORECASE | re.DOTALL):
        block = m.group(1)

        amt_str = _ofx_field(block, 'TRNAMT')
        amount = parse_amount(amt_str)
        if amount is None or amount == 0:
            continue

        date_str = _ofx_field(block, 'DTPOSTED') or _ofx_field(block, 'DTUSER')
        if not date_str:
            continue
        try:
            d = datetime.strptime(date_str[:8], '%Y%m%d').date()
        except ValueError:
            continue

        payee = _ofx_field(block, 'NAME') or _ofx_field(block, 'PAYEE')
        memo  = _ofx_field(block, 'MEMO')

        records.append({
            'date':     d.isoformat(),
            'payee':    payee,
            'memo':     memo,
            'amount':   amount,
            'type':     'credit' if amount > 0 else 'debit',
            'category': 'Other',
            'cleared':  True,
        })

    return records


# ── Direct-to-database import ─────────────────────────────────────────────────

@dataclass
class ImportContext:
    """Tracks the outcome of a direct import run."""
    dry_run: bool = False
    created: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def _get_or_create_account(session, name):
    from core.database import Account
    name = (name or 'Imported').strip()
    acct = session.query(Account).filter_by(name=name).first()
    if not acct:
        acct = Account(name=name, type='checking')
        session.add(acct)
        session.flush()
    return acct


def _get_or_create_category(session, name):
    from core.database import Category
    from sqlalchemy import func as _func
    cat = session.query(Category).filter(
        _func.lower(Category.name) == name.lower()
    ).first()
    if not cat:
        cat = Category(name=name)
        session.add(cat)
        session.flush()
    return cat


def _transaction_exists(session, account_id, txn_date, amount, description, import_id=None):
    from core.database import Transaction
    q = session.query(Transaction).filter(
        Transaction.account_id == account_id,
        Transaction.date == txn_date,
        Transaction.amount.between(amount - 0.005, amount + 0.005),
    )
    if import_id:
        existing_by_id = q.filter(Transaction.import_id == import_id).first()
        if existing_by_id:
            return True
    return q.filter(Transaction.description == description).first() is not None


def import_qif(path, ctx: ImportContext, default_account=None) -> bool:
    """Parse a QIF file and write transactions to the database."""
    from core.database import db_session, Transaction

    text = Path(path).read_text(encoding='utf-8', errors='replace')
    accounts = QIFParser().parse(text)

    with db_session() as session:
        for acct_name, acct_data in accounts.items():
            name = default_account or acct_name or 'Imported'
            account = _get_or_create_account(session, name)

            for raw in acct_data.get('transactions', []):
                try:
                    d = parse_qif_date(raw.get('date', ''))
                    amt = parse_amount(raw.get('amount', '0'))
                    if not d or amt is None or amt == 0:
                        ctx.skipped += 1
                        continue

                    description = (raw.get('payee') or raw.get('memo') or 'Transaction').strip()
                    category_name = normalize_category(raw.get('category', ''))
                    amount = abs(amt)

                    if _transaction_exists(session, account.id, d, amount, description):
                        ctx.skipped += 1
                        continue

                    if not ctx.dry_run:
                        cat = _get_or_create_category(session, category_name)
                        session.add(Transaction(
                            account_id=account.id,
                            category_id=cat.id,
                            date=d,
                            description=description,
                            amount=amount,
                            type='credit' if amt > 0 else 'debit',
                            cleared=bool(raw.get('cleared', False)),
                            memo=raw.get('memo', ''),
                        ))
                    ctx.created += 1

                except Exception as e:
                    ctx.errors.append(str(e))

        if ctx.dry_run:
            session.rollback()
        else:
            session.commit()

    return True


def import_qfx(path, ctx: ImportContext, account_name=None) -> bool:
    """Parse an OFX/QFX file and write transactions to the database."""
    from core.database import db_session, Transaction

    text = Path(path).read_text(encoding='utf-8', errors='replace')
    records = parse_qfx(text)

    if not records:
        ctx.warnings.append('No transactions found in OFX/QFX file')
        return False

    with db_session() as session:
        account = _get_or_create_account(session, account_name)

        for r in records:
            try:
                d = date.fromisoformat(r['date'])
                amount = abs(r['amount'])
                description = (r.get('payee') or r.get('memo') or 'Transaction').strip()
                category_name = normalize_category(r.get('category', ''))

                if _transaction_exists(session, account.id, d, amount, description):
                    ctx.skipped += 1
                    continue

                if not ctx.dry_run:
                    cat = _get_or_create_category(session, category_name)
                    session.add(Transaction(
                        account_id=account.id,
                        category_id=cat.id,
                        date=d,
                        description=description,
                        amount=amount,
                        type=r['type'],
                        cleared=bool(r.get('cleared', True)),
                        memo=r.get('memo', ''),
                    ))
                ctx.created += 1

            except Exception as e:
                ctx.errors.append(str(e))

        if ctx.dry_run:
            session.rollback()
        else:
            session.commit()

    return True


def import_csv(path, ctx: ImportContext, account_name=None) -> bool:
    """Parse a generic bank CSV and write transactions to the database."""
    from core.database import db_session, Transaction
    from bank_importer import detect_and_parse

    text = Path(path).read_text(encoding='utf-8', errors='replace')
    records, bank, warnings = detect_and_parse(text, Path(path).name)
    ctx.warnings.extend(warnings)

    if not records:
        ctx.warnings.append(f'No transactions recognized (detected as: {bank})')
        return False

    with db_session() as session:
        account = _get_or_create_account(session, account_name)

        for r in records:
            try:
                d = date.fromisoformat(r['date'])
                amount = abs(r['amount'])
                description = r['description'].strip()
                category_name = r.get('category', 'Other')

                if _transaction_exists(session, account.id, d, amount, description):
                    ctx.skipped += 1
                    continue

                if not ctx.dry_run:
                    cat = _get_or_create_category(session, category_name)
                    session.add(Transaction(
                        account_id=account.id,
                        category_id=cat.id,
                        date=d,
                        description=description,
                        amount=amount,
                        type=r['type'],
                        cleared=bool(r.get('cleared', True)),
                    ))
                ctx.created += 1

            except Exception as e:
                ctx.errors.append(str(e))

        if ctx.dry_run:
            session.rollback()
        else:
            session.commit()

    return True
