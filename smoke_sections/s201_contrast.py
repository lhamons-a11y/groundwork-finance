"""Item 77 (gw 2.0/CONTRAST.md K1-K8, RULED 2026-10-11; Rob: "build item 77").

K6: the test that keeps text readable. It computes, by the WCAG formula, every text colour Groundwork defines against
every background it defines, and scans the page code for text set in a colour that can't pass.

    K1  4.5:1 for normal text (the threshold everywhere here)
    K2  the tokens: slate, slate-2 and the text shades pass on all eight light backgrounds
    K3  green, gold and red as text use their text shades; the bright colours stay for fills and borders
    K4  hard-coded text colours: only those whose background is known and passes
    K5  white text on a fill: the fill is dark enough; faint white on the dark pages is at least 50%
"""
import re
from pathlib import Path


def _lum(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    x, y = sorted([_lum(a), _lum(b)])
    return (y + 0.05) / (x + 0.05)


TEXT = ('ink', 'ink-2', 'slate', 'slate-2', 'pine-text', 'gold-text', 'ember-text', 'sky')
BACKGROUNDS = ('paper', 'mist', 'mist-2', 'pine-bg', 'ember-bg', 'gold-bg', 'sky-bg', 'steel')
WHITE_ON = ('sky', 'pine-text', 'ember', 'ink', 'ink-2')
# K4: hard-coded text colours still allowed, each with the background it sits on (checked below)
ALLOWED_LITERALS = {
    '#fff': None,            # white: on the fills in WHITE_ON (checked separately) and on the dark pages
    '#000': '#ffffff',       # print styles
    '#1e40af': '#eff6ff',    # the blue badge
    '#4ade80': '#0d1117', '#f87171': '#0d1117', '#fca5a5': '#0d1117', '#86efac': '#052e16',   # on the dark report and bars
}


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    html = ctx.html_src
    root = re.search(r':root\s*\{(.*?)\}', html, re.S).group(1)
    tok = dict(re.findall(r'--([a-z0-9-]+):(#[0-9a-fA-F]{3,6})', root))

    missing = [t for t in TEXT + WHITE_ON if t not in tok]
    fails = [(t, b, round(ratio(tok[t], tok[b]), 2)) for t in TEXT for b in BACKGROUNDS
             if t in tok and not (t == 'sky' and b == 'steel') and ratio(tok[t], tok[b]) < 4.5] + [(t, 'missing') for t in missing]
    check(f'K2 every text colour is at least 4.5:1 on every light background ({fails or "all pass"})', not fails)
    check('K2 the light grey that started this (#94a3b8, 2.45:1 on green) is gone from the tokens',
          tok['slate-2'].lower() != '#94a3b8' and ratio(tok['slate-2'], tok['pine-bg']) >= 4.5)
    weak = [(b, round(ratio('#ffffff', tok[b]), 2)) for b in WHITE_ON if b in tok and ratio('#ffffff', tok[b]) < 4.5]
    check(f'K5 white text on each fill it sits on is at least 4.5:1 ({weak or "all pass"})', not weak)
    check('K6 mutation caught: the old light grey would fail the table above', ratio('#94a3b8', tok['pine-bg']) < 4.5)
    dark = {t: round(ratio(tok[t], tok['ink']), 2) for t in ('pine-on-dark', 'sky-on-dark') if t in tok}
    check(f'K5 the shades for the dark sidebar and pages pass on ink ({dark})',
          len(dark) == 2 and all(v >= 4.5 for v in dark.values()))

    files = [BASE / 'static/js/app.js', BASE / 'static/index.html'] + sorted((BASE / 'static/js/teaching').glob('*.js'))
    src = {f.name: f.read_text(encoding='utf-8') for f in files}
    src['index.html'] = src['index.html'].replace(re.search(r':root\s*\{.*?\}', src['index.html'], re.S).group(0), '')

    bright_text = []
    for name, t in src.items():
        for m in re.finditer(r'(?<![-\w])color\s*:\s*[\'"]?var\(--(pine|gold|ember)\)', t):
            bright_text.append(f'{name}:{t.count(chr(10), 0, m.start()) + 1} {m.group(1)}')
        for m in re.finditer(r'\.style\.color\s*=\s*[\'"]var\(--(pine|gold|ember)\)', t):
            bright_text.append(f'{name}:{t.count(chr(10), 0, m.start()) + 1} {m.group(1)}')
    check(f'K3 green, gold and red text uses the text shades - the bright colours are for fills and borders ({bright_text[:5]})',
          not bright_text)

    white_green = []
    for name, t in src.items():
        for m in re.finditer(r'background\s*:\s*var\(--pine\)', t):
            seg = t[m.end():m.end() + 240]
            stop = min([i for i in (seg.find('"'), seg.find('`'), seg.find('}'), seg.find('>')) if i != -1] or [len(seg)])
            back = t[max(0, m.start() - 240):m.start()]
            cut = max(back.rfind('"'), back.rfind('`'), back.rfind('}'), back.rfind('>'))
            if re.search(r'color\s*:\s*#fff\b', seg[:stop]) or re.search(r'color\s*:\s*#fff\b', back[cut + 1:]):
                white_green.append(f'{name}:{t.count(chr(10), 0, m.start()) + 1}')
    check(f'K5 white text never sits on the bright green fill (3.3:1) ({white_green[:5]})', not white_green)

    literals = {}
    for name, t in src.items():
        for m in re.finditer(r'(?<![-\w])color\s*:\s*(#[0-9a-fA-F]{3,6})\b', t):
            literals.setdefault(m.group(1).lower(), []).append(f'{name}:{t.count(chr(10), 0, m.start()) + 1}')
    stray = {k: v[:3] for k, v in literals.items() if k not in ALLOWED_LITERALS}
    check(f'K4 no hard-coded text colour outside the tokens, except the few with a known background ({stray})', not stray)
    weak_lit = {k: round(ratio(k, bg), 2) for k, bg in ALLOWED_LITERALS.items() if bg and ratio(k, bg) < 4.5}
    check(f'K4 each allowed hard-coded colour passes on its background ({weak_lit or "all pass"})', not weak_lit)

    faint = []
    for name, t in src.items():
        for m in re.finditer(r'(?<![-\w])color\s*:\s*rgba\(255,\s*255,\s*255,\s*(\.\d+|0\.\d+)\)', t):
            if float(m.group(1)) < 0.5:
                faint.append(f'{name}:{t.count(chr(10), 0, m.start()) + 1} {m.group(1)}')
    check(f'K5 white text on the dark pages is at least 50% white (5.3:1 on ink) ({faint[:5]})', not faint)
