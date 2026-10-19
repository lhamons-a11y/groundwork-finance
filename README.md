# Groundwork

A free personal finance app for Windows, macOS, and Linux.
Built for people who want to get out of debt and start building wealth.

**1.0** adds debt reconciliation (manual charge/payment tracking, recurring
payment drafts, checking-account linking) and adaptive learning (category
suggestions, budget variance, trip forecasting, recurring-transaction
detection, payoff confidence, AI gate health) — see `Website/changelog.json`
(the single source the site's changelog page publishes from) for the full list.

## Quick Start

**1. Install dependencies**
```
pip install -r requirements.txt
```
Linux users — read INSTALL.md first for system packages.

**2. Run**
```
python launch.py
```

That's it. Your data is stored locally on your machine — nothing goes to the cloud.

## Where your data lives

| Platform | Location |
|----------|----------|
| Windows  | `%LOCALAPPDATA%\Groundwork\groundwork.db` |
| macOS    | `~/Library/Application Support/Groundwork/groundwork.db` |
| Linux    | `~/.local/share/Groundwork/groundwork.db` |

## Project structure

```
Groundwork/
├── launch.py           ← Run this to start the app
├── server.py           ← Flask REST API (runs on localhost:8765)
├── requirements.txt    ← Python dependencies
├── INSTALL.md          ← Platform-specific setup guide
├── core/
│   ├── database.py     ← SQLAlchemy models + data directory
│   ├── migrate.py      ← Safe schema migrations (run on every boot)
│   └── bank_importer.py ← CSV/OFX/QIF parser
└── static/
    ├── index.html      ← App UI
    └── js/
        └── app.js      ← All frontend logic
```

## Reporting a problem

Open Groundwork, click **⚑ Report** in the top bar, describe what happened,
and tap **Open in mail app**. The report goes to support@groundworkfinance.app
with your error log and system info pre-filled.

## Notes

- The app runs entirely on your machine. No account needed, no subscription.
- AI reports run only on your own computer, on the engine built into the app. There is no cloud AI and no API key.
- Backups: Settings → Data & Backup → Back up now.
- The server runs on port 8765 and only accepts connections from this machine.

## Contributing and security

See `CONTRIBUTING.md` for bugs, ideas and pull requests, and `SECURITY.md` to report a security problem privately.

## License

Groundwork is free software under the GNU General Public License, version 3 (`LICENSE`). The name "Groundwork" and
its logo are not covered by the license. It is built on the open-source software listed in `THIRD_PARTY_NOTICES.md`.
