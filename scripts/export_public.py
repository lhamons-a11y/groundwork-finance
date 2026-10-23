#!/usr/bin/env python3
"""Build Groundwork's public copy: this repository's last commit, less what stays private, as a NEW repository with
one commit and no history (Rob 2026-10-19, the open-source cleanup report: "publish a new public repo from a cleaned
snapshot"). Nothing is pushed or published - that is a separate step, Rob's.

    python3 scripts/export_public.py ~/Documents/Groundwork-public

What stays private, and why:
  gw 2.0/ and the GROUNDWORK_*.md plans   the decision trail: results measured on the household's real ledger
  .claude/, deploy.bat                      one developer's machine setup
  scripts/export_public.py                  this script: its list below names what must never be public
The full history stays here; the public copy starts fresh, so nothing ever removed from history can leak.

Before committing, every exported text file is scanned for what must never be public (family names, personal
addresses, a real bank trace number). One hit and the export stops, leaving nothing committed.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PRIVATE_DIRS = ('gw 2.0/', '.claude/', 'scripts/mac_kit/results')
PRIVATE_FILES = re.compile(r'^(GROUNDWORK_[A-Z0-9_]+\.md|deploy\.bat|scripts/export_public\.py)$')
NEVER = re.compile(r'Partner|Sample|lhamons@|Family|000000000000001|/Users/rob', re.I)
AUTHOR = 'Groundwork <hello@groundworkfinance.app>'


def private(rel):
    return rel.startswith(PRIVATE_DIRS) or bool(PRIVATE_FILES.match(rel))


def run(*args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout


def main(dest):
    dest = Path(dest).expanduser().resolve()
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f'{dest} is not empty; give a new or empty folder.')
    if run('git', 'status', '--porcelain', '--untracked-files=no', cwd=REPO).strip():
        sys.exit('This repository has uncommitted changes; the export takes the last commit, so commit first.')
    head = run('git', 'rev-parse', '--short', 'HEAD', cwd=REPO).strip()
    files = [f for f in run('git', 'ls-files', '-z', cwd=REPO).split('\0') if f]
    keep = [f for f in files if not private(f)]

    hits = []
    for rel in keep:
        try:
            text = (REPO / rel).read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue                                        # images and other binaries
        for n, line in enumerate(text.splitlines(), 1):
            if NEVER.search(line):
                hits.append(f'{rel}:{n}: {line.strip()[:100]}')
    if hits:
        print('Stopped: these lines must not be public. Fix them here, commit, and run again.')
        print('\n'.join(hits))
        sys.exit(1)

    dest.mkdir(parents=True, exist_ok=True)
    for rel in keep:
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dest / rel)
    name, email = AUTHOR[:-1].split(' <')
    env = {'GIT_AUTHOR_NAME': name, 'GIT_AUTHOR_EMAIL': email, 'GIT_COMMITTER_NAME': name,
           'GIT_COMMITTER_EMAIL': email, 'PATH': '/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin'}
    run('git', 'init', '-q', '-b', 'master', cwd=dest)
    run('git', 'add', '-A', cwd=dest)
    run('git', 'commit', '-q', '-m', f'Groundwork, released under the GNU GPL v3\n\nFrom the private repository at {head}.',
        cwd=dest, env=env)
    print(f'{len(keep)} files exported to {dest} as one commit ({len(files) - len(keep)} kept private). Not pushed.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
