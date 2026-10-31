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
          and 'Report a problem' in privacy and 'Nothing is sent unless' in privacy
          and re.search(r'Last updated: [A-Z][a-z]+ \d{1,2}, 2026', privacy))
    check('s206 W6 the site\'s AI wording agrees with the app and the EULA: local only, no cloud option',
          'There is no cloud AI option.' in privacy and 'No cloud AI' in src
          and not re.search(r'cloud AI (mode|option is)|optional cloud', src, re.I))

    coming = src.split("@app.route('/coming')", 1)[1].split('@app.route', 1)[0]
    home = src.split('HOME_CONTENT = _icons(', 1)[1].split('""") + SIGNUP_BAND', 1)[0]
    pages = {k: src.split(f"@app.route('{k}')", 1)[1].split('@app.route', 1)[0]
             for k in ('/features', '/about', '/download', '/knowledge-base', '/privacy', '/terms')}
    # W3, superseded 2026-10-31 (Rob: "remake the website to show this ... highlight all these features ... make that
    # the central focus"): 2.0 may be shown on every page - but never as available before it is the download. Every
    # page is rendered both ways; until SITE_VERSION is 2.x each says "coming soon" / names it as 2.0's.
    import importlib, os as _os, sys as _sys, tempfile as _tf
    _os.environ.setdefault('GW_SITE_DATA', _tf.mkdtemp(prefix='gw_site_'))
    _sys.path.insert(0, str(BASE / 'Website'))
    site = importlib.import_module('website')
    sc = site.app.test_client()
    pre = {k: sc.get(k).get_data(as_text=True) for k in ('/', '/coming', '/privacy', '/download', '/llms.txt')}
    check('s206 W3 (2026-10-31) before 2.0 is the download, everything new says so: "coming soon", the 2.0 page "isn\'t in '
          'the download yet", the Privacy page names its 2.0 parts, and llms.txt says 2.0 is being built',
          not site.RELEASED_20 and pre['/'].count('New in 2.0 · coming soon') >= 2 and 'Coming in Groundwork 2.0' in pre['/']
          and "isn't in the download yet" in pre['/coming'] and 'The assistant (Groundwork 2.0)' in pre['/privacy']
          and 'The microphone (Groundwork 2.0)' in pre['/privacy'] and 'being built and tested now' in pre['/llms.txt']
          and 'Groundwork 1.1 gets no more updates' not in pre['/download'])
    check('s206 W3/W8 the Health page is described as built (no longer "in design"), and the health promise stays',
          'In design' not in coming and 'not built yet' not in coming and 'A Health page' in coming
          and 'nothing about your health leaves' in ' '.join(coming.split()))
    # The site is truthful whenever it is published: no invented proof, no pressure (TM6), no checksum made up
    bad = [w for w in ('trusted by', 'join thousands', 'join millions', 'limited time', 'only today', 'act now', '5 stars',
                       'rated #1', '#1 app', 'testimonial', 'award-winning') if w in flat.lower()]
    check(f's206 the site invents no proof and no urgency ({bad})', not bad)
    check('s206 R7 the last 1.1 is offered by name only with its real SHA-256 - none is made up',
          site.V11_SHA256 == '' or re.fullmatch(r'[0-9a-f]{64}', site.V11_SHA256))
    shots = re.findall(r'src="/static/shots/([^"]+)"', pre['/'])
    alts = re.findall(r'<img src="/static/shots/[^"]+"[^>]*alt="([^"]+)"', pre['/'])
    check(f's206 the screenshots exist, each with words for a screen reader that say its figures are made up ({len(shots)})',
          shots and all((BASE / 'Website' / 'static' / 'shots' / f).exists() for f in shots)
          and len(alts) == len(shots) and all('made-up' in a.lower() or 'made up' in a.lower() for a in alts))
    import json as _j
    lds = [_j.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', pre['/'], re.S)]
    faq = next((d for d in lds if d.get('@type') == 'FAQPage'), {})
    check('s206 SEO: the home page gives search engines the app, its features and its FAQ - the same answers the page shows',
          {d.get('@type') for d in lds} >= {'SoftwareApplication', 'FAQPage', 'WebSite'}
          and all(q['name'] in pre['/'] for q in faq.get('mainEntity', [])) and len(faq.get('mainEntity', [])) >= 5)
    robots = sc.get('/robots.txt').get_data(as_text=True)
    check('s206 SEO: robots.txt welcomes search engines and AI assistants by name, and keeps the admin and token pages out; '
          'llms.txt describes Groundwork for AI assistants',
          all(f'User-agent: {a}' in robots for a in ('GPTBot', 'ClaudeBot', 'PerplexityBot', 'Googlebot'))
          and robots.count('Disallow: /admin') >= 5 and 'Sitemap:' in robots
          and '# Groundwork' in pre['/llms.txt'] and 'never' in pre['/llms.txt'].lower())
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
          'Financial independence for everyone,</span><br><span class="nobr">one understood decision at a time.' in home
          and line2 in re.sub(r'<[^>]+>', '', about) and line2 in re.sub(r'<[^>]+>', '', coming))
    # Rob 2026-10-12: "everyone should never be wrapped into the next line" - every occurrence is one unbreakable unit
    bare = [m.start() for m in re.finditer(r'(?i)financial independence,? for everyone', src)
            if not src[max(0, m.start() - 40):m.start()].rstrip().endswith(('class="fi">', 'class="nobr">'))]
    check(f's206 "Financial independence, for everyone" never breaks across lines: every occurrence is held together ({len(bare)} loose)',
          not bare and '.fi { white-space: nowrap; }' in src and '.statement-line .nobr { white-space: nowrap; }' in src)
    check('s206 the 2.0 page is in both sitemaps', "('/coming'," in src
          and '/coming</loc>' in (BASE / 'Website' / 'sitemap.xml').read_text(encoding='utf-8'))
