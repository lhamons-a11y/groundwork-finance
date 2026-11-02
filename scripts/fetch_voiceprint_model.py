"""Fetch the voiceprint model for packaging (core/voiceprint.py, item 116 V19): WeSpeaker's ResNet34-LM trained on
VoxCeleb (CC BY 4.0), into vendor/voiceprint/.

    python scripts/fetch_voiceprint_model.py

The file is checked against the SHA-256 pinned in core/voiceprint.py; a file that does not match is deleted, never
packaged. This runs on the build machine only - Groundwork itself never downloads it, and never sends a voice anywhere.
"""
import hashlib
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    src = (ROOT / 'core' / 'voiceprint.py').read_text(encoding='utf-8')
    name = re.search(r"^MODEL_FILE = '([^']+)'", src, re.M).group(1)
    pin = re.search(r"^MODEL_SHA256 = '([0-9a-f]{64})'", src, re.M).group(1)
    url = re.search(r"^MODEL_URL = '([^']+)' \+ MODEL_FILE", src, re.M).group(1) + name
    dest = ROOT / 'vendor' / 'voiceprint' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        print('Fetching', url)
        try:
            urllib.request.urlretrieve(url, dest)
        except Exception as e:                      # e.g. a python.org Python with no certificate store
            if not shutil.which('curl'):
                raise
            print('urllib could not fetch it (%s); using curl' % e)
            subprocess.run(['curl', '-sL', '--fail', '-o', str(dest), url], check=True)
    h = hashlib.sha256(dest.read_bytes()).hexdigest()
    if h != pin:
        dest.unlink()
        print(f'{name}: SHA-256 {h} is not the pinned {pin}; deleted.')
        sys.exit(1)
    print(f'{dest} ({dest.stat().st_size:,} bytes) SHA-256 {h}')


if __name__ == '__main__':
    main()
