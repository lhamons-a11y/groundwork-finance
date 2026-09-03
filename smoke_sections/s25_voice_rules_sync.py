"""The voice gate's two rule copies must not drift.

static/voice_rules.json is the source; app.js carries _VOICE_RULES_FALLBACK, a
hardcoded copy used when the JSON fails to load. Adding a term to one and not
the other means the gate silently weakens on the fallback path — which happened
on 2026-09-03, when fifteen EDITORIALIZING terms went into the JSON only.

Also checks that every rule the harness enforces has a list behind it, since a
rule referencing a missing list fails open rather than closed.
"""
import json
import re


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    rules = json.loads((BASE / 'static' / 'voice_rules.json').read_text(encoding='utf-8'))
    src = (BASE / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    wordlists = rules['wordlists']

    i = src.find('const _VOICE_RULES_FALLBACK = {')
    j = src.find('\n};', i)
    check('app.js carries a _VOICE_RULES_FALLBACK block', i != -1 and j != -1)
    if i == -1 or j == -1:
        return

    block = src[i:j]
    fallback = {}
    for m in re.finditer(r'(\w+):\s*\[(.*?)\]', block, re.S):
        fallback[m.group(1)] = [x.strip('"') for x in re.findall(r'"[^"]*"', m.group(2))]

    check('the fallback carries every wordlist the json does',
          set(fallback) == set(wordlists))
    missing = sorted(set(wordlists) - set(fallback))
    if missing:
        print(f'        missing from fallback: {missing}')

    drifted = [k for k in wordlists if k in fallback and wordlists[k] != fallback[k]]
    check('every wordlist is identical in the json and the app.js fallback',
          not drifted)
    for k in drifted:
        only_json = [x for x in wordlists[k] if x not in fallback[k]]
        only_fb = [x for x in fallback[k] if x not in wordlists[k]]
        print(f'        {k}: json-only={only_json[:5]} fallback-only={only_fb[:5]}')

    # A rule naming a list that does not exist fails open — it finds nothing and
    # reports clean, which is the worst way for a gate to break.
    referenced = set(re.findall(r'rules\.([A-Z_]+)', src))
    orphan = sorted(referenced - set(wordlists))
    check('every wordlist app.js references exists in voice_rules.json', not orphan)
    if orphan:
        print(f'        referenced but absent: {orphan}')
