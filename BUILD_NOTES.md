# Groundwork — Build Folder

Complete source tree for building Groundwork v1.0.0.0. The frontend
(`static/index.html` + `static/js/app.js`) is the checkpoint-9 onboarding
build; the backend and packaging files are unchanged.

## Layout
```
groundwork_v2/
├── launch.py, server.py, migrate.py, auto_update.py   app entry + backend
├── bank_importer.py, quicken_import.py                 import engines
├── version.py, version_info.txt                        version metadata
├── requirements.txt                                    Python deps
├── groundwork.spec, build.bat                          PyInstaller build
├── install_linux.sh                                    Linux installer
├── README.md, SETUP_GUIDE.md                           docs
├── static/
│   ├── index.html
│   └── js/app.js
├── core/
│   ├── __init__.py
│   └── database.py
├── assets/
│   ├── groundwork.ico   (Windows / PyInstaller icon)
│   └── groundwork.png   (Linux desktop icon)
├── installer/
│   └── groundwork_setup.iss                            Inno Setup script
└── tests/                                              regression suite
```

## Build (Windows)
```
build.bat
```
Installs deps + PyInstaller, builds `dist\Groundwork\Groundwork.exe`, and (if
Inno Setup 6 is installed) produces `installer\Output\GroundworkSetup.exe`.

## Run from source (any OS)
```
pip install -r requirements.txt
python launch.py
```

## Tests (onboarding regression — checkpoints 0–9)
```
cd tests
npm install jsdom          # one-time, for the DOM suites
./run_tests.sh
```
Runs all 5 JS suites + the Flask backend integration test (153 checks).

## Before a public release (not blocking a local build)
- `version.py`: set `GITHUB_OWNER` / `GITHUB_REPO` (still placeholders).
  `auto_update.py` builds its GitHub API URL from these.
- `LICENSE`: `README.md` says "See LICENSE file" but none is present —
  add the license you intend (the README describes it as free/open source).
