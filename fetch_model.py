#!/usr/bin/env python3
"""Fetch the pinned model for a build, and refuse anything but the tested file (ENGINE_OTHER_PLATFORMS.md, item 33 Q5).

    python fetch_model.py            downloads the release asset into model_dl/, verifies it, prints its path; in CI
                                     it also sets GW_MODEL_PATH for the following steps (spec_engine.py reads it)

The model is git-ignored, so a build that is not on the developer's machine cannot see it. It is published once, as a
release asset of this repository (tag MODEL_RELEASE_TAG), and every build fetches that exact file. The pin lives in
core/engine.py (MODEL_FILE, MODEL_SHA256); this reads it. The build fails - exit status 1 - if the download fails, if
the file is missing, or if its SHA-256 is not the pinned one (Rob, 2026-10-03: the fingerprint check is mandatory).
Uses the GitHub CLI (`gh`), authenticated by GH_TOKEN in CI.

The model (2.03 GiB) is over GitHub's 2 GiB limit for one release file, so the release holds it in halves -
MODEL_FILE.part1, .part2 - which are joined here in order before the same fingerprint check (2026-10-08). A release
that holds the whole file still works.
"""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_RELEASE_TAG = 'model-phi3.5-mini-q4'
_SRC = (ROOT / 'core' / 'engine.py').read_text(encoding='utf-8')
MODEL_FILE = re.search(r"^MODEL_FILE = '([^']+)'", _SRC, re.M).group(1)
MODEL_SHA256 = re.search(r"^MODEL_SHA256 = '([0-9a-f]{64})'", _SRC, re.M).group(1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def join_parts(out, name):
    """Join name.part1, name.part2, ... in out into out/name, in number order, and remove the parts.
    Returns the number of parts joined (0 when there are none)."""
    parts = sorted(out.glob(f'{name}.part*'), key=lambda p: int(re.sub(r'\D', '', p.suffix) or 0))
    if not parts:
        return 0
    numbers = [int(re.sub(r'\D', '', p.suffix) or 0) for p in parts]
    if numbers != list(range(1, len(parts) + 1)):
        raise ValueError(f'the model halves are not a complete run 1..{len(parts)}: {numbers}')
    tmp = out / (name + '.joining')
    with open(tmp, 'wb') as joined:
        for p in parts:
            with open(p, 'rb') as fh:
                for block in iter(lambda: fh.read(8 << 20), b''):
                    joined.write(block)
    os.replace(tmp, out / name)
    for p in parts:
        p.unlink()
    return len(parts)


def main():
    out = ROOT / 'model_dl'
    out.mkdir(exist_ok=True)
    dest = out / MODEL_FILE
    if not dest.is_file():
        r = subprocess.run(['gh', 'release', 'download', MODEL_RELEASE_TAG, '--pattern', f'{MODEL_FILE}*',
                            '--dir', str(out), '--clobber'], capture_output=True, text=True)
        if r.returncode != 0:
            print(f'fetch_model: the download failed (release {MODEL_RELEASE_TAG}, asset {MODEL_FILE}): '
                  f'{(r.stderr or r.stdout).strip()[:400]}', file=sys.stderr)
            return 1
        try:
            join_parts(out, MODEL_FILE)
        except ValueError as e:
            print(f'fetch_model: {e}', file=sys.stderr)
            return 1
    if not dest.is_file():
        print(f'fetch_model: {dest} is missing after the download.', file=sys.stderr)
        return 1
    got = sha256(dest)
    if got != MODEL_SHA256:
        print(f'fetch_model: {dest} is not the tested model (SHA-256 {got}, pinned {MODEL_SHA256}). Refusing.',
              file=sys.stderr)
        dest.unlink()
        return 1
    env_file = os.environ.get('GITHUB_ENV')
    if env_file:
        with open(env_file, 'a', encoding='utf-8') as fh:
            fh.write(f'GW_MODEL_PATH={dest}\n')
    print(f'fetch_model: {dest} verified (SHA-256 {got})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
