"""Fetch Groundwork's voice for packaging (core/speak.py): Kokoro's int8 model and its voices, into vendor/kokoro/.

    python scripts/fetch_kokoro_model.py

Each file is checked against the SHA-256 pinned in core/speak.py; a file that does not match is deleted, never
packaged. This runs on the build machine only - Groundwork itself never downloads them, and never sends words anywhere.
"""
import hashlib
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'


def main():
    src = (ROOT / 'core' / 'speak.py').read_text(encoding='utf-8')
    files = [(re.search(rf"^{k}_FILE = '([^']+)'", src, re.M).group(1),
              re.search(rf"^{p}_SHA256 = '([0-9a-f]{{64}})'", src, re.M).group(1))
             for k, p in (('MODEL', 'MODEL'), ('VOICES', 'VOICES'))]
    bad = False
    for name, pin in files:
        dest = ROOT / 'vendor' / 'kokoro' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            url = BASE + name
            print('Fetching', url)
            try:
                urllib.request.urlretrieve(url, dest)
            except Exception as e:                  # e.g. a python.org Python with no certificate store
                if not shutil.which('curl'):
                    raise
                print('urllib could not fetch it (%s); using curl' % e)
                subprocess.run(['curl', '-sL', '--fail', '-o', str(dest), url], check=True)
        h = hashlib.sha256(dest.read_bytes()).hexdigest()
        if h != pin:
            dest.unlink()
            print(f'{name}: SHA-256 {h} is not the pinned {pin}; deleted.')
            bad = True
            continue
        print(f'{dest} ({dest.stat().st_size:,} bytes) SHA-256 {h}')
    if bad:
        sys.exit(1)


if __name__ == '__main__':
    main()
