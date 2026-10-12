"""Item 37 W6 (gw 2.0/WEBSITE_MESSAGE.md; Rob 2026-10-12: "I accept W1 - W9"): the website's text is held to what is true.

    W5/W7  the sentences found untrue on 2026-10-04 never come back
    W6     the advertised version is the changelog's newest release; every outside service the app's code contacts is
           named on the Privacy page; the site's AI wording agrees with the app and EULA (no cloud option)
    W3     2.0 is described only on its labelled page and the home page's labelled section, and the one designed-only
           part says it is in design
    W1/W4  the debt-first framing is gone from every page's title and description
"""
import json
import re


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    src = (BASE / 'Website' / 'website.py').read_text(encoding='utf-8')
    flat = ' '.join(src.split())

    gone = {
        'watches what you actually do': 'the silent-learning claim (no-silent-learning rule)',
        'learns the patterns': 'the silent-learning claim',
        'by default': 'AI "by default" - there is no other option',
        'aggregated numbers': 'AI reports "send aggregated numbers" - nothing is sent',
        'sends us the error log': 'the Report button never sends anything',
        'error log attached': 'the Report button opens your own mail app; you send it',
        '78%': 'an unsourced statistic',
        'No manual entry': '"no manual entry" - an import starts with a file you download',
        'one concrete thing to do differently': 'a promised verdict',
        'one concrete suggestion': 'a promised verdict',
        'tired of being broke': 'the debt-only framing (W4)',
        'medical debt': 'health care is a cost, never "medical debt" (W8)',
        'smarter it gets': 'implied silent learning',
        'ten built-in reports': 'an unchecked count',
        'Ollama': 'Ollama left both lines (item 31)',
    }
    back = {k: v for k, v in gone.items() if k.lower() in flat.lower()}
    check(f's206 W7 none of the sentences found untrue comes back ({back})', not back)

    m = re.search(r"^SITE_VERSION = '([^']+)'", src, re.M)
    log = json.loads((BASE / 'Website' / 'changelog.json').read_text(encoding='utf-8'))
    newest = log[0].get('headline', '') if log else ''
    check(f"s206 W6 the advertised version is the changelog's newest release ({m and m.group(1)} in {newest!r})",
          m is not None and f'Groundwork {m.group(1)}' in newest
          and not re.search(r'Version 1\.1 [—-]|Groundwork 1\.1 is here', src))

    privacy = src.split("@app.route('/privacy')", 1)[1].split('@app.route', 1)[0]
    hosts = {}
    for f, label in (('price_engine.py', 'Yahoo Finance'), ('trip_distance.py', 'OpenStreetMap'),
                     ('utility_price.py', 'Energy Information Administration'), ('gas_price.py', 'Energy Information Administration')):
        p = BASE / f
        if p.exists() and re.search(r'https://[a-z0-9.]*(yahoo|openstreetmap|eia\.gov)', p.read_text(encoding='utf-8')):
            hosts[f] = label
    missing = sorted({v for v in hosts.values() if v not in privacy})
    check(f's206 W9 every outside service the app contacts is named on the Privacy page, with what it is sent ({sorted(set(hosts.values()))}, missing {missing})',
          hosts and not missing and 'The update check' in privacy and 'ticker symbols' in privacy
          and 'your state' in privacy and 'places you type' in privacy)
    check('s206 W9 the Privacy page names the site\'s own counters, the one-click unsubscribe and the Report button as it behaves',
          'one count per page per day' in ' '.join(privacy.split()) and 'one-click unsubscribe' in privacy
          and 'The Report button' in privacy and 'Nothing is sent unless' in privacy
          and re.search(r'Last updated: [A-Z][a-z]+ \d{1,2}, 2026', privacy))
    check('s206 W6 the site\'s AI wording agrees with the app and the EULA: local only, no cloud option',
          'There is no cloud AI option.' in privacy and 'No cloud AI' in src
          and not re.search(r'cloud AI (mode|option is)|optional cloud', src, re.I))

    coming = src.split("@app.route('/coming')", 1)[1].split('@app.route', 1)[0]
    home = src.split('HOME_CONTENT = _icons(', 1)[1].split('""") + SIGNUP_BAND', 1)[0]
    pages = {k: src.split(f"@app.route('{k}')", 1)[1].split('@app.route', 1)[0]
             for k in ('/features', '/about', '/download', '/knowledge-base', '/privacy', '/terms')}
    leak = [k for k, v in pages.items() if re.search(r'Groundwork 2\.0|in 2\.0 ', v)
            and k not in ('/features', '/knowledge-base')]   # those two only link to the 2.0 page
    check(f's206 W3 2.0 is described only on its own page and the home page\'s labelled section ({leak})',
          not leak and 'Coming in Groundwork 2.0' in home and "isn't in the download yet" in coming
          and all(re.search(r'href="/coming"', pages[k]) for k in ('/features',)))
    check('s206 W3/W8 the one designed-only part says so, and the health promise is the general one',
          'In design' in coming and 'not built yet' in coming and 'nothing about your health leaves your computer' in coming)
    titles = re.findall(r"title='([^']+)'", src) + re.findall(r"description='([^']+)'", src)
    debt_first = [t for t in titles if re.search(r'paycheck to paycheck|get out of debt', t, re.I)]
    check(f's206 W1/W4 no page title or description leads with debt any more ({debt_first})', not debt_first)
    check('s206 W1 the home page carries the ruled sentence: the whole picture, explained, nothing to sell',
          'Your whole financial picture' in home and 'nothing to sell you' in home.lower()
          and 'for everyone' in ' '.join(home.split()).lower())
    about = src.split("@app.route('/about')", 1)[1].split('@app.route', 1)[0]
    line2 = 'Financial independence for everyone, one understood decision at a time.'
    check('s206 the horizon (Rob 2026-10-12): "Financial independence, for everyone" on the home, About and 2.0 pages - stated as the goal, never a promise',
          'Financial independence, for everyone' in home and 'Our horizon' in about
          and "can't promise anyone gets there" in ' '.join(about.split()) and 'financial independence, for everyone' in ' '.join(coming.split())
          and 'every user' not in flat)
    check('s206 the closing statement (Rob 2026-10-12): "one understood decision at a time" closes the home, About and 2.0 pages',
          line2.replace('everyone, ', 'everyone,<br>') in home and line2 in about and line2 in coming)
    check('s206 the 2.0 page is in both sitemaps', "('/coming'," in src
          and '/coming</loc>' in (BASE / 'Website' / 'sitemap.xml').read_text(encoding='utf-8'))
