"""
Groundwork — Account Restore Script
Restores accounts from the backup file.
Run from C:\Groundwork\ after copying this file there.

Usage:
  1. Copy this file to C:\Groundwork\
  2. Copy groundwork_backup_pre-delete-all_20260622_212104.db to C:\Groundwork\
  3. Close Groundwork
  4. Open command prompt in C:\Groundwork\
  5. Run: python restore_accounts.py
  6. Start Groundwork
"""

import sqlite3, os, sys
from pathlib import Path

BACKUP = Path(__file__).parent / 'groundwork_backup_pre-delete-all_20260622_212104.db'
LIVE   = Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData'/'Local')) / 'Groundwork' / 'groundwork.db'

print(f"Backup: {BACKUP}")
print(f"Live DB: {LIVE}")

if not BACKUP.exists():
    print("ERROR: Backup file not found. Copy it to C:\\Groundwork\\ first.")
    sys.exit(1)
if not LIVE.exists():
    print(f"ERROR: Live database not found at {LIVE}")
    sys.exit(1)

# Read accounts from backup
src = sqlite3.connect(str(BACKUP))
src.row_factory = sqlite3.Row
backup_accounts = src.execute('SELECT * FROM accounts').fetchall()
src.close()
print(f"\nAccounts in backup: {len(backup_accounts)}")
for a in backup_accounts:
    print(f"  id={a['id']} | {a['name']} | {a['type']}")

# Write to live DB
dst = sqlite3.connect(str(LIVE))

# Check if minimum_balance column exists, add if not
cols = {r[1] for r in dst.execute('PRAGMA table_info(accounts)').fetchall()}
if 'minimum_balance' not in cols:
    print("\nAdding minimum_balance column...")
    dst.execute("ALTER TABLE accounts ADD COLUMN minimum_balance FLOAT DEFAULT 0")
    dst.commit()

inserted = 0
for a in backup_accounts:
    try:
        dst.execute('''
            INSERT OR IGNORE INTO accounts
            (id, name, type, institution, currency, balance, sort_order, is_active, created_at, minimum_balance)
            VALUES (?,?,?,?,?,?,?,?,?,0)
        ''', (
            a['id'], a['name'], a['type'],
            a['institution'] or '',
            a['currency'] or 'USD',
            a['balance'] or 0,
            a['sort_order'] or 0,
            a['is_active'] if a['is_active'] is not None else 1,
            a['created_at'],
        ))
        inserted += 1
    except Exception as e:
        print(f"  Error on {a['name']}: {e}")

dst.commit()

# Verify
final = dst.execute('SELECT id, name FROM accounts').fetchall()
dst.close()

print(f"\nInserted: {inserted}")
print(f"Accounts now in live DB:")
for r in final:
    print(f"  id={r[0]} | {r[1]}")

if final:
    print("\n✓ SUCCESS — start Groundwork and check Settings → Accounts")
else:
    print("\n✗ Something went wrong — accounts still empty")
