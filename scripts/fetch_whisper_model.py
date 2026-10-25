"""Fetch the voice model for packaging (item 113): whisper.cpp's base.en, into vendor/whisper/.

    python scripts/fetch_whisper_model.py

The file is checked against the SHA-256 pinned in core/voice.py; a file that does not match is deleted, never
packaged. This runs on the build machine only - Groundwork itself never downloads it, and never sends audio anywhere.
"""
import hashlib
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin'


def main():
    src = (ROOT / 'core' / 'voice.py').read_text(encoding='utf-8')
    name = re.search(r"^MODEL_FILE = '([^']+)'", src, re.M).group(1)
    pin = (re.search(r"^MODEL_SHA256 = '([0-9a-f]*)'", src, re.M) or [None, ''])[1]
    dest = ROOT / 'vendor' / 'whisper' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        print('Fetching', URL)
        try:
            urllib.request.urlretrieve(URL, dest)
        except Exception as e:                      # e.g. a python.org Python with no certificate store
            if not shutil.which('curl'):
                raise
            print('urllib could not fetch it (%s); using curl' % e)
            subprocess.run(['curl', '-sL', '--fail', '-o', str(dest), URL], check=True)
    h = hashlib.sha256(dest.read_bytes()).hexdigest()
    if pin and h != pin:
        dest.unlink()
        sys.exit(f'{name}: SHA-256 {h} is not the pinned {pin}; deleted.')
    print(f'{dest} ({dest.stat().st_size:,} bytes) SHA-256 {h}' + ('' if pin else ' - not pinned yet: set MODEL_SHA256 in core/voice.py'))


if __name__ == '__main__':
    main()
