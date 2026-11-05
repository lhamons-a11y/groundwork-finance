"""What Groundwork's whisper actually writes for each store in core/data/us_stores.json and the supermarket list.

    python scripts/store_names_measure.py VOICE OUT.json [--hint]

"Show me my <store> transactions" is said by one of Groundwork's Kokoro voices - from the row's phonetic spelling, so the
voice says the name as people do - and recognised by Groundwork's own whisper.cpp base.en. Writes [{name, group, heard}]:
`heard` is the words whisper put where the store goes. Run on the build machine, by hand; one process per voice.

--hint: adds the national names to the prompt too, to measure whether the prompt can carry them.

Synthetic voices are a first cut, not real people on real microphones.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

from core import speak, voice               # noqa: E402
from voice_measure import _wav16            # noqa: E402

BETWEEN = re.compile(r'\bshow(?:s|ing)?\s+(?:me\s+)?(?:my\s+)?(.*?)\s*(?:transactions?|trans\w*)?[.?!]*$', re.I)


def rows():
    d = json.loads((ROOT / 'core' / 'data' / 'us_stores.json').read_text(encoding='utf-8'))
    return [{'name': r[0], 'phonetic': r[1], 'group': g} for g, rs in d['groups'].items() for r in rs]


def heard_in(text):
    m = BETWEEN.search(text or '')
    return (m.group(1) if m else text or '').strip()


def main():
    who, out = sys.argv[1], Path(sys.argv[2])
    use_hint = '--hint' in sys.argv
    k = speak._load()
    words = [r['name'] for r in rows() if r['group'] in ('department', 'discount', 'supermarket')] if use_hint else None
    results = []
    for r in rows():
        a, rate = k.create(f"Show me my {r['phonetic']} transactions.", voice=who,
                           lang='en-gb' if who.startswith('b') else 'en-us')
        text = voice.transcribe(_wav16(a, rate), words=words)
        results.append({'name': r['name'], 'group': r['group'], 'said': text, 'heard': heard_in(text)})
        if len(results) % 50 == 0:
            out.write_text(json.dumps(results, indent=0, ensure_ascii=False), encoding='utf-8')
            print(who, len(results), flush=True)
    out.write_text(json.dumps(results, indent=0, ensure_ascii=False), encoding='utf-8')
    print(who, 'done', len(results), flush=True)


if __name__ == '__main__':
    main()
