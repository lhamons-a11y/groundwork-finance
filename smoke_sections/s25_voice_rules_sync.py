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

    # ── Every gated callAI declares its findings kinds (HAZARD_AUDIT H5) ────
    # The runtime refuses an undeclared gated call; this check makes the same invariant
    # visible at commit time, so a new surface cannot reach the gate undeclared and be
    # discovered only when it fails closed in someone's browser. A call skips the gate
    # (`skipGate: true`) or declares - nothing else is a valid shape.
    calls = [m.start() for m in re.finditer(r'callAI\(\{', src)]
    undeclared, declared_kinds = [], set()
    allowed = set(re.findall(r"^\s*'([a-z_]+)',\s*//", src[src.find('const GW_FINDINGS_KINDS'):
                                                        src.find('const GW_FINDINGS_KINDS_PROHIBITED')],
                             re.M))
    prohibited = set(re.findall(r"'([a-z_]+)'", src[src.find('const GW_FINDINGS_KINDS_PROHIBITED'):
                                                    src.find('const GW_REPORT_FINDINGS_KINDS')]))
    for start in calls:
        end = src.find('});', start)
        block = src[start:end if end != -1 else start + 4000]
        if 'skipGate: true' in block or 'skipGate:true' in block:
            continue
        m = re.search(r"findings_kinds\s*:\s*\[([^\]]*)\]", block)
        via_registry = 'findings_kinds: _reportFindingsKinds(' in block or \
                       'findings_kinds: (_reportFindingsKinds(' in block
        surface = re.search(r"surface\s*:\s*[`']([^`']+)[`']", block)
        name = surface.group(1) if surface else f'@{start}'
        if not m and not via_registry:
            undeclared.append(name)
            continue
        if m:
            declared_kinds.update(re.findall(r"'([a-z_]+)'", m.group(1)))
    # The generic report path declares through a registry; its rows are declarations too.
    reg = src[src.find('const GW_REPORT_FINDINGS_KINDS'):src.find('function _reportFindingsKinds')]
    registry = {}
    for row in re.finditer(r"^\s*'?([A-Za-z_*]+)'?\s*:\s*\[([^\]]*)\]", reg, re.M):
        registry[row.group(1)] = re.findall(r"'([a-z_]+)'", row.group(2))
        declared_kinds.update(registry[row.group(1)])
    check('the generic report path has a declaration registry', bool(registry))
    check('the declaration vocabulary is present in app.js', bool(allowed) and bool(prohibited))
    check('every gated callAI declares its findings kinds', not undeclared)
    if undeclared:
        print('        undeclared gated surfaces: %s' % undeclared)
    bad = sorted(k for k in declared_kinds if k not in allowed and k not in prohibited)
    check('every declared kind is a known kind', not bad)
    if bad:
        print('        unknown kinds declared: %s' % bad)
    refusing = sorted(k for k, v in registry.items() if set(v) & prohibited)
    check('no gated surface declares free transaction text (a declaring one refuses at runtime)',
          not (declared_kinds & prohibited))
    if refusing:
        print('        surfaces declaring prohibited kinds, and therefore refusing: %s' % refusing)
    if orphan:
        print(f'        referenced but absent: {orphan}')
