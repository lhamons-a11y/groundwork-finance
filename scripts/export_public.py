#!/usr/bin/env python3
"""Build Groundwork's public copy: this repository's last commit, less what stays private, as a NEW repository with
one commit and no history (Rob 2026-10-19, the open-source cleanup report: "publish a new public repo from a cleaned
snapshot"). Nothing is pushed or published - that is a separate step, Rob's.

    python3 scripts/export_public.py ~/Documents/Groundwork-public     a new repository, one commit (the first publish)
    python3 scripts/export_public.py --sync [--push] [CLONE]          an update to the published one

--sync (Rob 2026-11-09: "set it up"): the public repository is github.com/lhamons-a11y/groundwork-finance, published
2026-11-09 from ad7e123. CLONE is a local clone of it (default ~/Groundwork-public, cloned on first use). The same
files are taken and the same check made; the clone's files are replaced by them (deleted files go too) and committed
as ONE commit "Update from the private repository at <sha>" - no private commit message ever goes public. --push
pushes it; without it, the commit waits in the clone to be looked at. The sync stops if the public repository has
commits from anyone else since the last sync (a merged pull request): bring those into this repository first, or
the sync would erase them.

What stays private, and why:
  gw 2.0/ and the GROUNDWORK_*.md plans   the decision trail: results measured on the household's real ledger
  .claude/, deploy.bat                      one developer's machine setup
  scripts/export_public.py                  this script: its list below names what must never be public
The full history stays here; the public copy starts fresh, so nothing ever removed from history can leak.

Before committing, every exported text file is scanned for what must never be public (family names, personal
addresses, a real bank trace number - the list is ~/.config/groundwork/export_never.txt, never committed). One hit and the export stops, leaving nothing committed.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PRIVATE_DIRS = ('gw 2.0/', '.claude/', 'scripts/mac_kit/results')
PRIVATE_FILES = re.compile(r'^(GROUNDWORK_[A-Z0-9_]+\.md|deploy\.bat|scripts/export_public\.py)$')
# The patterns themselves live off GitHub (they name what they look for): one regular expression per line, # for a
# comment. Without the file the export stops - the check is never skipped.
NEVER_FILE = Path.home() / '.config' / 'groundwork' / 'export_never.txt'


def never():
    if not NEVER_FILE.exists():
        sys.exit(f'Stopped: {NEVER_FILE} is missing - the list of what must never be public. Restore it first.')
    pats = [ln.strip() for ln in NEVER_FILE.read_text(encoding='utf-8').splitlines()
            if ln.strip() and not ln.lstrip().startswith('#')]
    if not pats:
        sys.exit(f'Stopped: {NEVER_FILE} names nothing to look for.')
    return re.compile('|'.join(f'(?:{p})' for p in pats), re.I)

AUTHOR = 'Groundwork <hello@groundworkfinance.app>'


def private(rel):
    return rel.startswith(PRIVATE_DIRS) or bool(PRIVATE_FILES.match(rel))


def run(*args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout


PUBLIC_URL = 'https://github.com/lhamons-a11y/groundwork-finance.git'
SYNC_SUBJECTS = ('Groundwork, released under the GNU GPL v3', 'Update from the private repository at ')


def snapshot():
    """(head, files, keep): this repository's last commit and the files that may be public. Stops on any hit."""
    if run('git', 'status', '--porcelain', '--untracked-files=no', cwd=REPO).strip():
        sys.exit('This repository has uncommitted changes; the export takes the last commit, so commit first.')
    head = run('git', 'rev-parse', '--short', 'HEAD', cwd=REPO).strip()
    files = [f for f in run('git', 'ls-files', '-z', cwd=REPO).split('\0') if f]
    keep = [f for f in files if not private(f)]

    NEVER = never()
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
    return head, files, keep


def copy_into(dest, keep):
    for rel in keep:
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dest / rel)


def author_env():
    name, email = AUTHOR[:-1].split(' <')
    return {'GIT_AUTHOR_NAME': name, 'GIT_AUTHOR_EMAIL': email, 'GIT_COMMITTER_NAME': name,
            'GIT_COMMITTER_EMAIL': email, 'PATH': '/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin'}


def main(dest):
    dest = Path(dest).expanduser().resolve()
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f'{dest} is not empty; give a new or empty folder.')
    head, files, keep = snapshot()
    dest.mkdir(parents=True, exist_ok=True)
    copy_into(dest, keep)
    env = author_env()
    run('git', 'init', '-q', '-b', 'master', cwd=dest)
    run('git', 'add', '-A', cwd=dest)
    run('git', 'commit', '-q', '-m', f'Groundwork, released under the GNU GPL v3\n\nFrom the private repository at {head}.',
        cwd=dest, env=env)
    print(f'{len(keep)} files exported to {dest} as one commit ({len(files) - len(keep)} kept private). Not pushed.')


def sync(clone, push):
    clone = Path(clone).expanduser().resolve()
    head, files, keep = snapshot()
    if not (clone / '.git').is_dir():
        if clone.exists() and any(clone.iterdir()):
            sys.exit(f'{clone} is not a clone of the public repository; give an empty folder or its clone.')
        print(f'Cloning {PUBLIC_URL} into {clone} ...')
        subprocess.run(['git', 'clone', '-q', PUBLIC_URL, str(clone)], check=True)
    if run('git', 'status', '--porcelain', cwd=clone).strip():
        sys.exit(f'{clone} has uncommitted changes; clear them first.')
    run('git', 'fetch', '-q', 'origin', cwd=clone)
    branch = run('git', 'rev-parse', '--abbrev-ref', 'HEAD', cwd=clone).strip()
    behind = run('git', 'rev-list', '--count', f'HEAD..origin/{branch}', cwd=clone).strip()
    if behind != '0':
        run('git', 'merge', '-q', '--ff-only', f'origin/{branch}', cwd=clone)

    # Anyone else's commits since the last sync would be erased by replacing the files: stop and say which.
    foreign = []
    for line in run('git', 'log', '--format=%h%x09%ae%x09%s', cwd=clone).splitlines():
        sha, email, subject = line.split('\t', 2)
        if email == AUTHOR[:-1].split(' <')[1] and subject.startswith(SYNC_SUBJECTS):
            break
        foreign.append(f'  {sha} {email} {subject}')
    if foreign:
        print('Stopped: the public repository has commits since the last sync that are not from it. Bring them into')
        print('this repository first (e.g. git fetch the public repo and cherry-pick), commit, then sync again:')
        print('\n'.join(foreign))
        sys.exit(1)

    for item in clone.iterdir():
        if item.name == '.git':
            continue
        shutil.rmtree(item) if item.is_dir() and not item.is_symlink() else item.unlink()
    copy_into(clone, keep)
    run('git', 'add', '-A', cwd=clone)
    stat = run('git', 'diff', '--cached', '--shortstat', cwd=clone).strip()
    if not stat:
        print(f'Nothing to sync: the public repository already matches {head}.')
        return
    version = re.search(r'^VERSION\s*=\s*"([^"]+)"', (REPO / 'version.py').read_text(encoding='utf-8'), re.M)
    msg = f'Update from the private repository at {head}' + (f'\n\nGroundwork {version.group(1)}.' if version else '')
    run('git', 'commit', '-q', '-m', msg, cwd=clone, env=author_env())
    print(f'Committed in {clone}: {stat}.')
    print(run('git', 'diff', '--stat', 'HEAD~1', 'HEAD', cwd=clone).strip().splitlines()[-1])
    if push:
        run('git', 'push', '-q', 'origin', branch, cwd=clone)
        print(f'Pushed to {PUBLIC_URL}.')
    else:
        print(f'Not pushed. Look it over (git -C {clone} show --stat), then: git -C {clone} push')


if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == '--sync':
        rest = [a for a in args[1:] if a != '--push']
        sync(rest[0] if rest else '~/Groundwork-public', '--push' in args[1:])
    elif len(args) == 1 and not args[0].startswith('-'):
        main(args[0])
    else:
        sys.exit(__doc__)
