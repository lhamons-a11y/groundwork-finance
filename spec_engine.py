"""The local AI engine and its pinned model, for the macOS and Linux builds (gw 2.0/ENGINE_OTHER_PLATFORMS.md, item 33).

Rob, 2026-10-03: "a pinned engine version + a pinned model artifact + a verified fingerprint -> a reproducible platform
package", never "whatever happens to be in vendor/ on the developer's machine". So:

  engine_parts()   the llama_cpp runtime, collected for PyInstaller (it is imported lazily, after the CPU check, so
                   PyInstaller cannot find it alone). A build without it FAILS - except on an Intel Mac, where no
                   tested runtime exists (Q2): that build runs Groundwork with local AI unavailable, and says so.
  model_data()     the exact tested model, packaged as models/<MODEL_FILE>. The build FAILS if the file is missing, if
                   its SHA-256 does not match core/engine.py's pin, or if it cannot be staged - a release must never
                   build with the wrong model, or none.

The pin lives in one place, core/engine.py (MODEL_FILE, MODEL_SHA256); this reads it rather than repeating it.
Where the model comes from: GW_MODEL_PATH (CI downloads the pinned release asset there), else the dev copy in vendor/.
"""
import hashlib
import os
import platform
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_SRC = (ROOT / 'core' / 'engine.py').read_text(encoding='utf-8')
MODEL_FILE = re.search(r"^MODEL_FILE = '([^']+)'", _SRC, re.M).group(1)
MODEL_SHA256 = re.search(r"^MODEL_SHA256 = '([0-9a-f]{64})'", _SRC, re.M).group(1)


class BuildRefused(SystemExit):
    pass


def intel_mac():
    return sys.platform == 'darwin' and platform.machine() == 'x86_64'


def engine_parts():
    """(binaries, datas, hiddenimports) for the runtime; empty on an Intel Mac (Q2). Refuses a build without it."""
    if intel_mac():
        print('[spec] Intel Mac: no tested local AI runtime exists (ENGINE_OTHER_PLATFORMS.md Q2) - building '
              'Groundwork with local AI unavailable. The application runs; the engine reports why.')
        return [], [], []
    try:
        import llama_cpp  # noqa: F401
    except Exception as e:
        raise BuildRefused('spec_engine: llama-cpp-python is not installed in the build environment (%s). Install the '
                           'pinned version from requirements.txt.' % e)
    from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules
    return collect_dynamic_libs('llama_cpp'), collect_data_files('llama_cpp'), collect_submodules('llama_cpp')


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def model_source():
    env = os.environ.get('GW_MODEL_PATH')
    return Path(env) if env else ROOT / 'vendor' / 'phi3.5_model' / 'blobs' / f'sha256-{MODEL_SHA256}'


def model_data(stage_dir=None):
    """[(staged_file, 'models')] for PyInstaller datas - the verified model under its shipped name. Empty on an Intel
    Mac (no engine to read it). Refuses the build if the file is missing or is not the tested file."""
    if intel_mac():
        return []
    src = model_source()
    if not src.is_file():
        raise BuildRefused(f'spec_engine: the model file is missing ({src}). Set GW_MODEL_PATH to the pinned model '
                           f'(CI downloads the release asset there). A release never builds without its model.')
    got = _sha256(src)
    if got != MODEL_SHA256:
        raise BuildRefused(f'spec_engine: {src} is not the tested model (SHA-256 {got}, pinned {MODEL_SHA256}). '
                           f'A release never builds with the wrong model.')
    stage = Path(stage_dir or ROOT / 'build' / 'engine_model')
    stage.mkdir(parents=True, exist_ok=True)
    dest = stage / MODEL_FILE
    try:
        if dest.exists() and dest.stat().st_size == src.stat().st_size:
            pass
        else:
            if dest.exists():
                dest.unlink()
            try:
                os.link(src, dest)                      # no 2 GB copy when the filesystem allows it
            except OSError:
                shutil.copyfile(src, dest)
    except OSError as e:
        raise BuildRefused(f'spec_engine: the model could not be staged for packaging ({e}).')
    return [(str(dest), 'models')]


# ── Item 113: voice commands (core/voice.py) ─────────────────────────────────────────────────────────────────────────
# Optional, unlike the AI engine: voice is off by default and Groundwork says when it is unavailable. A build without
# the runtime or the model says so loudly and carries on; a model that is not the measured file is still refused.
_VOICE_SRC = (ROOT / 'core' / 'voice.py').read_text(encoding='utf-8')
VOICE_FILE = re.search(r"^MODEL_FILE = '([^']+)'", _VOICE_SRC, re.M).group(1)
_vpin = re.search(r"^MODEL_SHA256 = '([0-9a-f]{64})'", _VOICE_SRC, re.M)
VOICE_SHA256 = _vpin.group(1) if _vpin else ''


def voice_parts():
    """(binaries, datas, hiddenimports) for pywhispercpp, or empty with a warning when it is not installed."""
    try:
        import pywhispercpp  # noqa: F401
    except Exception as e:
        print('[spec] WARNING: pywhispercpp is not installed (%s) - this build has no voice commands.' % e)
        return [], [], []
    from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules
    return (collect_dynamic_libs('pywhispercpp') + collect_dynamic_libs('_pywhispercpp'),
            collect_data_files('pywhispercpp'), collect_submodules('pywhispercpp') + ['_pywhispercpp'])


def voice_model_data():
    """[(file, 'models')] - the measured whisper model, from GW_WHISPER_PATH or vendor/whisper/. Missing: a warning and
    no voice. Present but not the measured file: the build is refused."""
    env = os.environ.get('GW_WHISPER_PATH')
    src = Path(env) if env else ROOT / 'vendor' / 'whisper' / VOICE_FILE
    if not src.is_file():
        print('[spec] WARNING: the voice model is missing (%s) - this build has no voice commands. '
              'scripts/fetch_whisper_model.py fetches it.' % src)
        return []
    got = _sha256(src)
    if not VOICE_SHA256 or got != VOICE_SHA256:
        raise BuildRefused(f'spec_engine: {src} is not the measured voice model (SHA-256 {got}, pinned '
                           f'{VOICE_SHA256 or "none"} in core/voice.py).')
    return [(str(src), 'models')]
