"""Whose voice it is (item 116 V19, VOICE_ASSISTANT.md; Rob 2026-11-01: "lets have it recognize your voice.. Since we
are dealing with people finance and health information").

A clip of the person's speech is turned into a voiceprint - 256 numbers - by WeSpeaker's ResNet34 model trained on
VoxCeleb (CC BY 4.0), run here by ONNX Runtime. Two voiceprints are compared by their angle (cosine): the same voice
scores near 1, another voice well below. The person reads a few sentences once, in Settings; their voiceprint is kept in
the record, shown there, and can be deleted. It is never updated from what is heard - only by enrolling again.

What it is and is not: it keeps other voices - a television, a guest - from commanding Groundwork. It is not a lock: a
recording of the person's voice could pass it, and it does nothing about someone reading the screen.

This module imports nothing that can reach a network. Without the model file, voice recognition is unavailable and
says why; voice commands work as before.
"""
import logging
import os
import threading
from pathlib import Path

MODEL_FILE = 'voxceleb_resnet34_LM.onnx'
# The exact file measured on 2026-11-01 (scripts/fetch_voiceprint_model.py checks it before it is packaged).
MODEL_SHA256 = '7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068'
MODEL_URL = 'https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM/resolve/main/' + MODEL_FILE

RATE = 16000
DIM = 256
MIN_VOICED_S = 0.4      # less speech than this says too little about whose voice it is

# A clip is a known voice when it scores this or more against one. Measured 2026-11-01 (scripts/voiceprint_measure.py,
# 30 synthetic voices, V8's 30 commands, clean / noise 15 dB / hum 10 dB, VOICE_ASSISTANT.md 4c): at 0.45 the enrolled
# voice was refused 11.0% of the time - mostly the one-word commands - and another voice taken 0.87%.
THRESHOLD = 0.45

# What the person reads to enrol: everyday Groundwork sentences, long enough to carry the voice
SENTENCES = [
    'Groundwork, this is my voice, and these are my accounts.',
    'I would like to see what is coming up this week, and what is due this month.',
    'Please open the budget, then show me my grocery transactions from last month.',
    'My checking account pays the electric bill, the water bill, and the phone.',
    'Read the page to me slowly, and stop when I say stop.',
]
ENROL_MIN_CLIPS = 4         # of the five read; one may be lost to a cough
ENROL_MIN_VOICED_S = 1.5    # each reading carries at least this much speech
ENROL_MAX_VOICED_S = 9.0    # and no more than a sentence takes to read; more is something else talking too
ENROL_SAID = 0.6            # the share of a sentence's words heard in its reading


def said_share(sentence, heard):
    """How much of a sentence was heard in its reading (0..1): its words found in what whisper made of the clip. Rob
    2026-11-01: enrolled with the television on, the voiceprint was the television's - the television never reads
    Groundwork's sentences."""
    import re
    words = lambda t: re.sub(r"[^a-z' ]+", ' ', str(t or '').lower()).split()
    want, got = words(sentence), set(words(heard))
    return sum(w in got for w in want) / len(want) if want else 0.0
# Each reading sounds like the others: one that doesn't is another voice, or the television. Measured 2026-11-01 on the
# same 30 voices: a voice's own readings agreed at 0.794 or more; with one reading swapped for another voice's, 0.65
# caught 4,344 of 4,350 (0.75 caught all, with too little room for a real microphone).
ENROL_AGREE = 0.65

_lock = threading.Lock()
_session = None


class VoiceprintError(Exception):
    pass


def model_path():
    """GW_VOICEPRINT_PATH (tests, dev), else the install's models folder, else a source checkout's vendor/voiceprint/."""
    env = os.environ.get('GW_VOICEPRINT_PATH')
    if env:
        return Path(env)
    from core.engine import _base_dirs
    for base in _base_dirs():
        p = base / 'models' / MODEL_FILE
        if p.exists():
            return p
    for base in _base_dirs():
        p = base / 'vendor' / 'voiceprint' / MODEL_FILE
        if p.exists():
            return p
    return _base_dirs()[0] / 'models' / MODEL_FILE


def status():
    """{'available': bool, 'reason': str} - checked without loading the model."""
    try:
        import onnxruntime  # noqa: F401
    except Exception:
        return {'available': False, 'reason': 'This copy of Groundwork was built without voice recognition.'}
    if not model_path().exists():
        return {'available': False, 'reason': 'The voice recognition file is not installed with this copy.'}
    return {'available': True, 'reason': ''}


def _load():
    global _session
    if _session is None:
        import onnxruntime as rt
        opts = rt.SessionOptions()
        opts.intra_op_num_threads = max(1, min(2, (os.cpu_count() or 2) - 1))   # a short clip; the AI model has the rest
        opts.inter_op_num_threads = 1
        opts.enable_cpu_mem_arena = False
        _session = rt.InferenceSession(str(model_path()), sess_options=opts, providers=['CPUExecutionProvider'])
    return _session


def release():
    global _session
    with _lock:
        _session = None


# ── Features: Kaldi's 80-band log mel filterbank, as WeSpeaker computes it (wespeaker/bin/infer_onnx.py) ──────────
_FRAME, _SHIFT, _NFFT, _BANDS = 400, 160, 512, 80


def _mel_banks():
    import numpy as np
    mel = lambda f: 1127.0 * np.log(1.0 + f / 700.0)
    lo, hi = mel(20.0), mel(RATE / 2.0)
    delta = (hi - lo) / (_BANDS + 1)
    bins = mel(np.arange(_NFFT // 2) * RATE / _NFFT)
    banks = np.zeros((_BANDS, _NFFT // 2 + 1), dtype=np.float64)
    for b in range(_BANDS):
        left, centre, right = lo + b * delta, lo + (b + 1) * delta, lo + (b + 2) * delta
        up = (bins - left) / (centre - left)
        down = (right - bins) / (right - centre)
        banks[b, :_NFFT // 2] = np.where((bins > left) & (bins < right), np.where(bins <= centre, up, down), 0.0)
    return banks


_BANKS = None


def fbank(samples):
    """float samples in -1..1 at 16 kHz -> (frames, 80) log mel energies, Kaldi's way: DC removed, pre-emphasis 0.97,
    Hamming window, power spectrum, no dither."""
    import numpy as np
    global _BANKS
    if _BANKS is None:
        _BANKS = _mel_banks()
    x = np.asarray(samples, dtype=np.float64) * 32768.0
    n = 1 + (len(x) - _FRAME) // _SHIFT if len(x) >= _FRAME else 0
    if n <= 0:
        return np.zeros((0, _BANDS), dtype=np.float32)
    idx = np.arange(_FRAME)[None, :] + _SHIFT * np.arange(n)[:, None]
    f = x[idx]
    f = f - f.mean(axis=1, keepdims=True)
    f = np.concatenate([f[:, :1] - 0.97 * f[:, :1], f[:, 1:] - 0.97 * f[:, :-1]], axis=1)
    f = f * (0.54 - 0.46 * np.cos(2 * np.pi * np.arange(_FRAME) / (_FRAME - 1)))
    power = np.abs(np.fft.rfft(f, n=_NFFT)) ** 2
    return np.log(np.maximum(power @ _BANKS.T, np.finfo(np.float32).eps)).astype(np.float32)


def _voiced(feats):
    """Only the frames that carry the voice: within 40 dB of the clip's loudest. The pause that ends a clip, and the
    quiet before it, say nothing about whose voice it is."""
    import numpy as np
    if not len(feats):
        return feats
    e = np.log(np.exp(feats.astype(np.float64)).sum(axis=1))
    return feats[e > e.max() - 40 * np.log(10) / 10]


def embed(samples, session=None):
    """The voiceprint of a clip: a unit vector of DIM numbers, or None when it holds too little speech."""
    import numpy as np
    feats = _voiced(fbank(samples))
    if len(feats) * _SHIFT / RATE < MIN_VOICED_S:
        return None
    feats = feats - feats.mean(axis=0)                          # CMN, without CVN, as WeSpeaker does
    with _lock:
        s = session or _load()
        out = s.run(['embs'], {'feats': feats[None, :, :].astype(np.float32)})[0][0]
    norm = float(np.linalg.norm(out))
    return (out / norm).astype(np.float32) if norm > 0 else None


def combine(prints):
    """Several clips of one person, read at enrolment, as one voiceprint."""
    import numpy as np
    ok = [np.asarray(p, dtype=np.float32) for p in prints if p is not None]
    if not ok:
        return None
    m = np.mean(ok, axis=0)
    return (m / np.linalg.norm(m)).astype(np.float32)


def score(a, b):
    """How alike two voiceprints are: the cosine of their angle, -1..1."""
    import numpy as np
    return float(np.dot(np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)))


def voiced_seconds(samples):
    return len(_voiced(fbank(samples))) * _SHIFT / RATE


def enrol(clips, session=None):
    """The readings of SENTENCES (float sample arrays) -> one voiceprint. Refused, with the reason said, when too few
    readings carry enough speech, or one does not sound like the rest."""
    long_enough = [c for c in clips if ENROL_MIN_VOICED_S <= voiced_seconds(c) <= ENROL_MAX_VOICED_S]
    if len(long_enough) < ENROL_MIN_CLIPS:
        raise VoiceprintError('Too few of the sentences were heard clearly - %d of %d. Read them again, a little closer '
                              'to the microphone.' % (len(long_enough), len(clips)))
    prints = [embed(c, session) for c in long_enough]
    if any(p is None for p in prints):
        raise VoiceprintError('A sentence was too quiet to use. Read them again.')
    for i, p in enumerate(prints):
        rest = combine(prints[:i] + prints[i + 1:])
        if score(p, rest) < ENROL_AGREE:
            raise VoiceprintError('One of the sentences did not sound like the others - another voice, or the television. '
                                  'Read them again somewhere quieter.')
    return combine(prints)


def best(clip_print, known):
    """The known voice a clip is most like: (entry, score), or (None, best score) when none reaches THRESHOLD.
    `known`: [{'id', 'name', 'print': unit vector}]."""
    top, top_s = None, -1.0
    for k in known:
        s = score(k['print'], clip_print)
        if s > top_s:
            top, top_s = k, s
    return (top, top_s) if top is not None and top_s >= THRESHOLD else (None, top_s)


def to_text(p):
    import base64
    import numpy as np
    return base64.b64encode(np.asarray(p, dtype='<f4').tobytes()).decode('ascii')


def from_text(t):
    import base64
    import numpy as np
    a = np.frombuffer(base64.b64decode(t), dtype='<f4')
    if a.shape != (DIM,):
        raise VoiceprintError('A kept voiceprint could not be read.')
    return a


logging.getLogger(__name__).addHandler(logging.NullHandler())
