"""The release line holds (gw 2.0/LTS_RETIREMENT.md, item 32 L2j and L3f; Rob 2026-10-04: "Run the gates").

    L2j  master contains every lts/1.x commit. Fixes go lts/1.x -> master by merge (L2a), and a rebase once copied two
         1.x commits into master instead (item 38, relinked at c213510). When git or the 1.x ref is not available,
         the check says it was skipped - it never passes silently.
    L3f  GW_VERSION stays in the date form and sorts after every released version. The installed 1.1.0 compares
         versions as text (`latest > GW_VERSION`): "2.0.0" sorts below "20260826-d24", so a 2.0 named that way
         would never be offered to a 1.1.0 install.
"""
import json
import os
import re
import shutil
import subprocess

DATE_FORM = re.compile(r'^\d{8}-[0-9A-Za-z.]+$')


def offered_to(installed, latest):
    """What the shipped 1.x update check does (server.py update_check): text comparison."""
    return bool(latest) and latest > installed


def version_ok(version, released):
    """L3f: date form, and not below any released version (equal is the release itself)."""
    return bool(DATE_FORM.match(version)) and all(version >= r for r in released)


def lts_contained(base, head='HEAD', ref='origin/lts/1.x'):
    """L2j: True / False, or None when it cannot be measured here (no git, no ref) - never a silent pass."""
    git = shutil.which('git')
    if not git:
        return None
    if subprocess.run([git, 'rev-parse', '--verify', '--quiet', ref], cwd=base, capture_output=True).returncode:
        return None
    r = subprocess.run([git, 'merge-base', '--is-ancestor', ref, head], cwd=base, capture_output=True)
    return r.returncode == 0


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    import server

    # ── L3f ────────────────────────────────────────────────────────────────────────────────────────────────────
    changelog = json.loads(BASE.joinpath('Website/changelog.json').read_text(encoding='utf-8'))
    released = [e['version'] for e in changelog if e.get('version')]
    manifest = json.loads(BASE.joinpath('Website/version.json').read_text(encoding='utf-8'))
    app_v = re.search(r"const GW_VERSION = '([^']+)'", ctx.app_src)
    check('s149 L3f every released version is in the date form (YYYYMMDD-...)',
          bool(released) and all(DATE_FORM.match(v) for v in released) and DATE_FORM.match(manifest['latest']))
    check('s149 L3f GW_VERSION is in the date form and sorts at or after every released version and the manifest',
          version_ok(server.GW_VERSION, released + [manifest['latest']]))
    check('s149 L3f server.py and app.js carry the same GW_VERSION', bool(app_v) and app_v.group(1) == server.GW_VERSION)
    check('s149 L3f the reason, measured: a 1.1.0 install would never be offered "2.0.0", and would be offered a '
          'date-form 2.0', not offered_to('20260826-d24', '2.0.0') and offered_to('20260826-d24', '20270115-2.0'))
    check('s149 L3f the check can fail: "2.0.0" and a version below a release are refused',
          not version_ok('2.0.0', released) and not version_ok('20200101-old', released))

    # ── L2j ────────────────────────────────────────────────────────────────────────────────────────────────────
    contained = lts_contained(BASE)
    if contained is None:
        print('  SKIP  s149 L2j master contains every lts/1.x commit - not measurable here (no git, or no '
              'origin/lts/1.x ref); not counted as a pass')
    else:
        check('s149 L2j master contains every lts/1.x commit (fixes reach master by merge, never as copies)', contained)
        git = shutil.which('git')
        # The probe commit carries its own name: a CI runner has no git identity, and without one commit-tree
        # fails, the probe is empty and this check failed on GitHub while passing locally (2026-10-08).
        probe_env = dict(os.environ, GIT_AUTHOR_NAME='s149 probe', GIT_AUTHOR_EMAIL='s149@probe.invalid',
                         GIT_COMMITTER_NAME='s149 probe', GIT_COMMITTER_EMAIL='s149@probe.invalid')
        orphan = subprocess.run([git, 'commit-tree', 'HEAD^{tree}', '-m', 's149 probe: a commit not in master'],
                                cwd=BASE, capture_output=True, text=True, env=probe_env).stdout.strip()
        check('s149 L2j the check can fail: a commit that is not in master is reported as not contained',
              bool(orphan) and lts_contained(BASE, ref=orphan) is False)
