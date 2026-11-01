"""The app's fonts ship with it (Rob 2026-10-19: "Download the fonts and make them part of the package"): drawing the
page asks Google for nothing, every face the stylesheet names is in static/fonts, and each font's license text is
beside it (SIL OFL 1.1 requires it to travel with the fonts)."""
import re


def run(ctx):
    check, BASE, c = ctx.check, ctx.BASE, ctx.c
    html = (BASE / 'static' / 'index.html').read_text(encoding='utf-8')
    fonts = BASE / 'static' / 'fonts'
    css = (fonts / 'fonts.css').read_text(encoding='utf-8')
    named = re.findall(r'url\(([^)]+\.woff2)\)', css)
    check('s239 the app page loads no font from Google; it links the bundled stylesheet',
          'fonts.googleapis.com' not in html and 'fonts.gstatic.com' not in html
          and '<link rel="stylesheet" href="/fonts/fonts.css">' in html)
    check('s239 every font the stylesheet names is bundled, and the stylesheet points nowhere else',
          named and all((fonts / n).is_file() for n in named) and 'http' not in css.split('*/', 1)[1])
    check('s239 the families the page uses are all there (Inter 400/500/600, DM Mono 400/500, Playfair Display italic 700)',
          all(f"font-family: '{f}';" in css for f in ('Inter', 'DM Mono', 'Playfair Display'))
          and all(f'font-weight: {w};' in css for w in (400, 500, 600, 700)))
    check("s239 each font's license text ships beside it",
          all('SIL OPEN FONT LICENSE' in (fonts / f'OFL-{n}.txt').read_text(encoding='utf-8')
              for n in ('inter', 'dmmono', 'playfairdisplay')))
    r = c.get('/fonts/' + named[0]) if named else None
    check('s239 the server hands the page its fonts', r is not None and r.status_code == 200 and r.data[:4] == b'wOF2')
