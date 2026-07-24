"""
Groundwork — Transaction Restore Script
Run this ONCE from C:\Groundwork\ to restore your 976 transactions.

Usage:
  1. Copy this file to C:\Groundwork\
  2. Copy groundwork_backup_pre-delete-all_20260622_212104.db to C:\Groundwork\
  3. Open a command prompt in C:\Groundwork\
  4. Run: python restore_groundwork.py
  5. Start Groundwork normally

This script:
  - Reads transactions from the backup
  - Inserts them into the live database
  - Maps account/category IDs correctly between backup and live DB
  - Does NOT touch any other data (categories, debts, budget items stay as-is)
"""

import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
BACKUP_FILE = Path(__file__).parent / 'groundwork_backup_pre-delete-all_20260622_212104.db'
LIVE_DB     = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'Groundwork' / 'groundwork.db'

print(f"Backup: {BACKUP_FILE}")
print(f"Live DB: {LIVE_DB}")
print()

if not BACKUP_FILE.exists():
    print(f"ERROR: Backup file not found at {BACKUP_FILE}")
    print("Copy groundwork_backup_pre-delete-all_20260622_212104.db to C:\\Groundwork\\ first.")
    sys.exit(1)

if not LIVE_DB.exists():
    print(f"ERROR: Live database not found at {LIVE_DB}")
    sys.exit(1)

# ── Read backup ─────────────────────────────────────────────────────────────
print("Reading backup...")
src = sqlite3.connect(str(BACKUP_FILE))
src.row_factory = sqlite3.Row

backup_txns   = src.execute('SELECT * FROM transactions').fetchall()
backup_accts  = {r['id']: r['name'] for r in src.execute('SELECT id, name FROM accounts').fetchall()}
backup_cats   = {r['id']: r['name'] for r in src.execute('SELECT id, name FROM categories').fetchall()}
src.close()

print(f"  {len(backup_txns)} transactions found in backup")
print(f"  Accounts in backup: {dict(list(backup_accts.items())[:5])}")

# ── Read live DB ─────────────────────────────────────────────────────────────
print("\nReading live database...")
dst = sqlite3.connect(str(LIVE_DB))
dst.row_factory = sqlite3.Row

live_accts  = {r['name']: r['id'] for r in dst.execute('SELECT id, name FROM accounts').fetchall()}
live_cats   = {r['name']: r['id'] for r in dst.execute('SELECT id, name FROM categories').fetchall()}
live_txn_count = dst.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]

print(f"  Current transactions in live DB: {live_txn_count}")
print(f"  Accounts in live DB: {dict(list(live_accts.items())[:5])}")

# ── Build ID maps ─────────────────────────────────────────────────────────────
# Map backup account IDs → live account IDs by name
acct_map = {}
for backup_id, name in backup_accts.items():
    if name in live_accts:
        acct_map[backup_id] = live_accts[name]
    else:
        # Account doesn't exist in live DB — create it
        dst.execute("INSERT INTO accounts (name, type, institution, currency) VALUES (?, 'checking', '', 'USD')", (name,))
        dst.commit()
        new_id = dst.execute("SELECT id FROM accounts WHERE name=?", (name,)).fetchone()['id']
        acct_map[backup_id] = new_id
        live_accts[name] = new_id
        print(f"  Created missing account: '{name}' → id {new_id}")

# Map backup category IDs → live category IDs by name
cat_map = {}
other_id = live_cats.get('Other', 1)
for backup_id, name in backup_cats.items():
    if name in live_cats:
        cat_map[backup_id] = live_cats[name]
    else:
        cat_map[backup_id] = other_id  # fallback to Other

print(f"\n  Account ID map: {acct_map}")

# ── Check live DB schema has all needed columns ───────────────────────────────
live_cols = {r[1] for r in dst.execute('PRAGMA table_info(transactions)').fetchall()}
needed = {'merchant', 'posted_date', 'running_balance', 'mcc', 'card_last4',
          'source', 'import_id', 'check_number'}
missing = needed - live_cols
if missing:
    print(f"\nAdding missing columns to live DB: {missing}")
    for col in missing:
        if col in ('posted_date',):
            dst.execute(f"ALTER TABLE transactions ADD COLUMN {col} DATE")
        elif col == 'running_balance':
            dst.execute(f"ALTER TABLE transactions ADD COLUMN {col} FLOAT")
        else:
            dst.execute(f"ALTER TABLE transactions ADD COLUMN {col} VARCHAR(120) DEFAULT ''")
    dst.commit()

# ── Insert transactions ───────────────────────────────────────────────────────
print(f"\nInserting {len(backup_txns)} transactions...")

inserted = 0
skipped  = 0
errors   = 0

for row in backup_txns:
    try:
        live_acct_id = acct_map.get(row['account_id'], 1)
        live_cat_id  = cat_map.get(row['category_id'], other_id)

        dst.execute('''
            INSERT OR IGNORE INTO transactions
            (id, account_id, category_id, date, description, amount, type,
             cleared, memo, merchant, posted_date, running_balance,
             mcc, card_last4, source, import_id, check_number, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            row['id'],
            live_acct_id,
            live_cat_id,
            row['date'],
            row['description'],
            row['amount'],
            row['type'],
            row['cleared'] if row['cleared'] is not None else 1,
            row['memo'] or '',
            row['merchant'] or '',
            row['posted_date'],
            row['running_balance'],
            row['mcc'] or '',
            row['card_last4'] or '',
            row['source'] or 'csv',
            row['import_id'] or '',
            row['check_number'] or '',
            row['created_at'],
        ))
        inserted += 1
    except Exception as e:
        errors += 1
        print(f"  Error on row {row['id']}: {e}")

dst.commit()

# ── Verify ───────────────────────────────────────────────────────────────────
final_count = dst.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
dst.close()

print(f"\nDone.")
print(f"  Inserted: {inserted}")
print(f"  Skipped (already existed): {skipped}")
print(f"  Errors: {errors}")
print(f"  Live DB transaction count: {final_count}")

if final_count > 0:
    print(f"\n✓ SUCCESS — {final_count} transactions restored.")
    print("  Start Groundwork normally and your data should be back.")
else:
    print(f"\n✗ Something went wrong — transaction count is still 0.")
    print("  Contact support with the error messages above.")
