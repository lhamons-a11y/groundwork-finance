"""V19 (item 116, VOICE_ASSISTANT.md): whose voice it is, measured before a threshold is chosen.

    python scripts/voiceprint_measure.py [--quick]

Every English Kokoro voice and the computer's own voices on Windows take a turn as the household's enrolled voice: five
sentences read once, as Settings will ask. Then V8's thirty commands, said by that voice and by every other voice -
clean, with noise at about 15 dB, and with a fan-like hum at about 10 dB - are scored against the enrolled voiceprint
(core/voiceprint.py). The scores of the same voice and of other voices are counted at each threshold: commands from the
enrolled voice let go (refused), commands from another voice taken (accepted). The null model is in the same table:
noise alone, and silence, scored against each enrolment.

Synthetic voices are the first cut, not the verdict: Kokoro's voices are one model's styles, and may sit closer to one
another than people do, or further apart. The exit criterion needs real people on real microphones. Nothing is kept but
the printout.
"""
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

from voice_measure import COMMANDS, _kokoro_clips, _noisy, _wav16, _windows_clips  # noqa: E402

ENROL = [
    ('Groundwork, this is my voice, and these are my accounts.', None),
    ('I would like to see what is coming up this week, and what is due this month.', None),
    ('Please open the budget, then show me my grocery transactions from last month.', None),
    ('My checking account pays the electric bill, the water bill, and the phone.', None),
    ('Read the page to me slowly, and stop when I say stop.', None),
]
# Only the desktop voices: SelectVoice of a voice that is not installed fails and the last voice keeps speaking -
# measured 2026-11-01, "Microsoft Mark" scored 0.909 against Zira because it was Zira
WINDOWS = ['Microsoft David Desktop', 'Microsoft Zira Desktop']


def _hum(samples, rate, snr_db=10, seed=2):
    """a fan or a refrigerator: a low hum with its harmonics and a little hiss"""
    import numpy as np
    a = np.asarray(samples, dtype=np.float32)
    t = np.arange(len(a)) / rate
    h = sum(np.sin(2 * np.pi * f * t + i) / (i + 1) for i, f in enumerate((60, 120, 180, 240)))
    h = h + np.random.default_rng(seed).normal(0, 0.3, len(a))
    p = float(np.mean(a ** 2)) or 1e-6
    return a + (h * (p / 10 ** (snr_db / 10) / float(np.mean(h ** 2))) ** 0.5).astype(np.float32)


def _samples(a, rate, end_pause=True):
    """what the server is sent: 16 kHz, the page's moment before, and the pause that ended it"""
    import numpy as np
    from core import voice
    s = voice.read_wav(_wav16(a, rate))
    return np.concatenate([s, np.zeros(int(0.9 * 16000), dtype=np.float32)]) if end_pause else s


def main():
    import numpy as np
    from core import speak, voiceprint
    quick = '--quick' in sys.argv
    voices = [v for v in sorted(speak.VOICES_ALL if hasattr(speak, 'VOICES_ALL') else [])] or None
    if voices is None:
        d = np.load(str(speak._model_dir() / speak.VOICES_FILE))
        voices = sorted(v for v in d.files if v[:2] in ('af', 'am', 'bf', 'bm'))
    if quick:
        voices = voices[:6]
    cmds = COMMANDS[:10] if quick else COMMANDS
    t0 = time.time()
    cache = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--cache=')), None)
    if cache and os.path.exists(cache):
        import pickle
        clips = pickle.load(open(cache, 'rb'))
    else:
        clips = _kokoro_clips(voices, ENROL + cmds)
        clips.update(_windows_clips(WINDOWS, ENROL + cmds, tempfile.mkdtemp(prefix='gw_vp_')))
        if cache:
            import pickle
            pickle.dump(clips, open(cache, 'wb'))
    clips = {k: c for k, c in clips.items() if k[0] in voices or k[0] in WINDOWS}
    speakers = voices + sorted({v for v, _ in clips if v in WINDOWS})
    print(f'{len(speakers)} voices, {len(cmds)} commands; made in {time.time() - t0:.0f} s')

    enrolled, prints, times = {}, {}, []
    for v in speakers:
        if not all((v, e) in clips for e, _ in ENROL):
            continue
        enrolled[v] = voiceprint.combine([voiceprint.embed(_samples(*clips[(v, e)])) for e, _ in ENROL])
        for text, _ in cmds:
            if (v, text) not in clips:
                continue
            a, rate = clips[(v, text)]
            for cond, s in (('clean', _samples(a, rate)), ('noise 15 dB', _samples(_noisy(a), rate)),
                            ('hum 10 dB', _samples(_hum(a, rate), rate))):
                t = time.perf_counter()
                prints[(v, text, cond)] = voiceprint.embed(s)
                times.append((time.perf_counter() - t, len(s) / 16000))
    speakers = sorted(enrolled)
    rng = np.random.default_rng(3)
    nulls = {'noise alone': voiceprint.embed(rng.normal(0, 0.05, 3 * 16000).astype(np.float32)),
             'hum alone': voiceprint.embed(_hum(np.full(3 * 16000, 0.05, dtype=np.float32), 16000, snr_db=-20)),
             'silence': voiceprint.embed(np.zeros(3 * 16000, dtype=np.float32))}

    same, other, short_same, none, pairs = [], [], [], 0, {}
    by_cond = {}
    for owner in speakers:
        for (v, text, cond), p in prints.items():
            if p is None:
                none += owner == v
                continue
            s = voiceprint.score(enrolled[owner], p)
            (same if v == owner else other).append(s)
            if v != owner:
                pairs[(owner, v)] = max(pairs.get((owner, v), -1), s)
            by_cond.setdefault(cond, ([], []))[0 if v == owner else 1].append(s)
            if v == owner and len(text.split()) <= 2:
                short_same.append(s)
    same, other = np.array(same), np.array(other)
    null_scores = [voiceprint.score(enrolled[o], p) for o in speakers for p in nulls.values() if p is not None]

    print(f'\nsame voice: {len(same)} clips, other voices: {len(other)} clips; '
          f'{none} clips of the enrolled voice held too little speech to score')
    print(f'same voice   score: min {same.min():.3f}  5th {np.percentile(same, 5):.3f}  median {np.median(same):.3f}')
    print(f'other voices score: median {np.median(other):.3f}  99th {np.percentile(other, 99):.3f}  '
          f'99.9th {np.percentile(other, 99.9):.3f}  max {other.max():.3f}')
    if short_same:
        print(f'short commands ("Stop", "Next") from the same voice: min {min(short_same):.3f}, '
              f'median {np.median(short_same):.3f}')
    print(f'null model: {sum(p is None for p in nulls.values())} of {len(nulls)} held too little speech to score; '
          f'scored ones max {max(null_scores) if null_scores else float("nan"):.3f}')
    print('\nthreshold | enrolled voice refused | other voices accepted')
    for th in np.arange(0.20, 0.71, 0.05):
        print(f'   {th:.2f}   | {np.mean(same < th) * 100:6.2f}% ({int(np.sum(same < th))})'
              f'        | {np.mean(other >= th) * 100:6.3f}% ({int(np.sum(other >= th))})')
    lo, hi = 0.0, 1.0
    for _ in range(40):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if np.mean(same < m) < np.mean(other >= m) else (lo, m)
    print(f'\nequal error rate {np.mean(same < lo) * 100:.2f}% at {lo:.3f}')
    for cond, (a, b) in sorted(by_cond.items()):
        a, b = np.array(a), np.array(b)
        print(f'  {cond:12s} same median {np.median(a):.3f} min {a.min():.3f} | other 99.9th {np.percentile(b, 99.9):.3f}')
    print('\nthe closest other voices (enrolled <- speaking: highest score)')
    for (o, v), s in sorted(pairs.items(), key=lambda x: -x[1])[:8]:
        print(f'  {o} <- {v}: {s:.3f}')
    t = np.array(times)
    print(f'\ntime to a voiceprint: median {np.median(t[:, 0]) * 1000:.0f} ms for a median {np.median(t[:, 1]):.1f} s clip, '
          f'max {t[:, 0].max() * 1000:.0f} ms')


if __name__ == '__main__':
    main()
