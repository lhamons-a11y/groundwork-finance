"""Build core/data/grocery_chains.json from Wikipedia's "List of supermarket chains in the United States"
(Rob 2026-11-01: "here is a website to grab all of the major national Grocery Stores that is in the United States").

    python scripts/build_grocery_chains.py [raw_wikitext_file]

Run on the build machine, by hand; Groundwork itself never fetches the list. Without a file argument it downloads the
page's raw wikitext once. Each chain is kept with the section it was listed under and one of three kinds:

    grocery   a supermarket - its spending is groceries
    mixed     sells much more than food (Walmart, Target, Costco, Amazon, the dollar stores) - its spending is not
              assumed to be groceries
    company   a parent company or buying cooperative, not a store name on a receipt - kept out

The wholesalers and the defunct chains are left out. The page is CC BY-SA 4.0; the names are facts, credited in
THIRD_PARTY_NOTICES.md.
"""
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TITLE = 'List_of_supermarket_chains_in_the_United_States'
RAW_URL = f'https://en.wikipedia.org/w/index.php?title={TITLE}&action=raw'
REV_URL = (f'https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles={TITLE}'
           '&rvprop=ids|timestamp&format=json')

SKIP_SECTIONS = {'Wholesalers', 'Defunct chains', 'See also', 'References', 'External links'}
# sells much more than food: its spending is not assumed to be groceries
MIXED = {'amazon', 'costco', "bj's wholesale club", 'target', 'walmart', "sam's club", 'big lots', 'dollar general',
         'family dollar', 'five below'}
# a parent company or buying cooperative, not a name on a receipt
COMPANY = re.compile(r'\b(?:inc\.?|llc|corporation|associates|delhaize|wholesale grocers|associated grocers|'
                     r'associated food stores|affiliated foods|wakefern|topco|spartannash)\b', re.I)


_LINK = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')


def _head(text):
    """The name at the start of a line - cut at its first note: a bracket, a dash, a comma or a reference, none of them
    inside a link ("[[99 Ranch Market]] – the largest [[Asian Americans|Asian-American]] chain ... [[Nevada]]")."""
    text = re.sub(r'\[https?://\S+ ([^\]]+)\]', r'\1', text)            # [https://... Food Bazaar]
    depth, i = 0, 0
    while i < len(text):
        if text.startswith('[[', i):
            depth += 1; i += 2; continue
        if text.startswith(']]', i):
            depth -= 1; i += 2; continue
        if depth == 0 and (text.startswith(' (', i) or text.startswith(' –', i) or text.startswith(' - ', i)
                           or text.startswith(', ', i) or text.startswith('<ref', i) or text.startswith('{{', i)):
            return text[:i]
        i += 1
    return text


# How Groundwork's voice is to say a chain it says wrong (Rob 2026-11-01, after Meijer came out "major"). Each was read
# off the voice's own phonemes for the name (kokoro_onnx's Tokenizer, en-us), and each respelling checked the same way.
SAY = {
    'Fred Meyer': 'Fred Myer', 'IGA': 'I G A', 'Ingles Markets': 'Ingulls Markets', 'Erewhon': 'Air-wahn',
    'Gristedes': 'Griss-tee-dees', 'Remke Markets': 'Rem-kee Markets', "Trucchi's": 'Troo-keys',
    "Kowalski's Markets": 'Ko-wall-skis Markets', "Buehler's": 'Beulers', "Magruder's": 'Muh-grooders',
    "Uncle Giuseppe's": 'Uncle Joo-seppies', 'Vallarta Supermarkets': 'Vy-yarta Supermarkets',
    'Tresierras Supermarkets': 'Tress-see-air-ahs Supermarkets',
    'La Perla Tapatía Supermarkets': 'La Perla Tapa-tee-ah Supermarkets', 'Número Uno Market': 'Noo-meh-ro Oono Market',
    'Tenochtitlán Market': 'Teh-noch-teet-lahn Market', 'Mi Pueblo Food Center': 'Mee Pueblo Food Center',
    'Mi Tienda': 'Mee Tee-enda', 'Presidente': 'Preh-see-den-teh', 'El Ahorro Supermarket': 'El Ah-orro Supermarket',
    'Publix Sabor': 'Publix Sah-bor', 'Sieu Thi ABC': 'Syoo Tee A-B-C', 'Ai Hoa Supermarket': 'Eye Wah Supermarket',
    'Hoa Binh Supermarket': 'Wah Bin Supermarket', 'Nam Dae Mun Farmers Market': 'Nam Deh Moon Farmers Market',
    'Lotte Plaza': 'Lot-teh Plaza', 'Arirang Market': 'Ah-ree-rahng Market', 'Nijiya Market': 'Nee-jee-yah Market',
    'Uwajimaya': 'Oo-wah-jee-mah-yah', 'Mitsuwa': 'Meet-soo-wah', "Gleiberman's Gourmet": "Glyberman's Gourmet",
    'Stater Bros.': 'Stater Brothers', "Seller's Bros.": "Seller's Brothers", 'Roche Bros': 'Roach Brothers',
    'Mr. Special': 'Mister Special', 'Super A Foods': 'Super Ay Foods', "Gelson's Markets": "Ghelson's Markets",
    "Gerrity's Supermarkets": "Gair-itty's Supermarkets", 'Gerbes': 'Gurbees', 'Lidl': 'Leedle',
    'Indopak Supermarket and Cafe': 'Indo-pak Supermarket and Cafe', 'Great Valu': 'Great Value',
    'Rosauers Supermarkets': 'Rose-hours Supermarkets', "Reasor's": 'Reezers',
    'La Michoacana Meat Market': 'Lah Mee-cho-ah-kah-nah Meat Market',
}


# Grocery chains named by an everyday word or phrase: said and heard, never a category's evidence ("LUCKY DRAGON" is not
# a supermarket; "123 MARKET STREET" is an address)
GENERIC = {
    'Giant', 'Lucky', 'Tops', 'Homeland', 'Pueblo', 'Bravo', 'Presidente', 'Evergreen', 'Seasons', "Baker's", "Fry's",
    "Terry's", "Hugo's", "Marc's", "Harding's", "Motty's", 'Pavilions', 'New Day', 'Market Street', 'City Market',
    'The Markets', 'Market District', 'Spring Market', 'Central Market', 'Warehouse Market', 'Grand Mart', 'Ideal Market',
    'Viva Markets', 'Galleria Market', 'Metro Supermarket', 'Country Mart', 'Price Mart', 'Apple Market', 'Key Food',
    'Food City', 'Food Town', 'Food King', 'Food Rite', 'Crest Foods', 'The Market Place', 'Market 32', 'El Super',
    'El Rey', 'El Rancho', 'La Bonita', 'La Placita', 'Ocean Mart', 'Lion Food', 'Zion Market', 'Greenland Market',
    'Times Supermarkets', 'Western Beef', 'Fresh Encounters', 'The Fresh Market', 'Bingo Wholesale', 'Cash Saver',
    'Cash Wise', 'Great Valu', 'Twin City Supermarket', 'Super A Foods', 'Associated Supermarkets', 'Lucky California',
}


def _names(text):
    """The chain names in a piece of wikitext: each link's shown text, else the plain name."""
    out = [shown or target for target, shown in _LINK.findall(text)]
    if not out:
        plain = re.sub(r'\[https?://\S+ ([^\]]+)\]', r'\1', text).strip(" *!|–-")
        if plain:
            out.append(plain)
    return out


def _clean(name):
    n = re.sub(r'%27', "'", name).replace('_', ' ').replace('’', "'")
    n = re.sub(r'\s+in\s+[A-Z].*$', '', re.sub(r'\s+', ' ', n))           # "88 Ranch Marketplace in Southern California"
    n = re.sub(r'\s*\((?:supermarket|grocery store|company|US grocery store chain|Texas|Landover|United States|New England)\)$',
               '', n).strip()
    return n


def parse(raw):
    chains, seen, section, sub = [], set(), '', ''
    in_table, brands_col, col = False, False, 0
    for line in raw.splitlines():
        h = re.match(r'^(==+)\s*(.+?)\s*\1\s*$', line)
        if h:
            if len(h.group(1)) == 2:
                section, sub = h.group(2), ''
            else:
                sub = h.group(2)
            continue
        if section in SKIP_SECTIONS or not section:
            continue
        if line.startswith('{|'):
            in_table, col = True, 0
            continue
        if line.startswith('|}'):
            in_table = False
            continue
        names = []
        if in_table:
            if line.startswith('|-'):
                col = 0
                continue
            if line.startswith('! scope="row"'):
                col = 1
                names = _names(line.split('|', 1)[1])
            elif line.startswith('|') and col:
                col += 1
                if col == 5:                       # "Associated supermarket brands": a comma-separated list
                    cell = re.sub(r"\s*\([^)]*\)|''", '', line.lstrip('|'))      # "(Illinois, Indiana, ...)" is not a name
                    names = [n for part in re.split(r',(?![^\[]*\]\])', cell) for n in _names(part)]
            else:
                continue
        elif line.startswith('*'):
            # "**[[Randalls]] and [[Tom Thumb ...|Tom Thumb]] (Texas)": every link in the name at the start of the line
            names = _names(_head(line.lstrip('* ')))
        # "Price Chopper / Price Mart", "India Bazaar/IndiaCo": two names
        names = [part for n in names for part in re.split(r'\s*/\s*', n)]
        for n in names:
            n = _clean(n)
            key = n.lower()
            if not n or key in seen or len(n) > 60:
                continue
            seen.add(key)
            kind = 'company' if COMPANY.search(n) else 'mixed' if key in MIXED else 'grocery'
            entry = {'name': n, 'section': section + (' / ' + sub if sub else ''), 'kind': kind}
            if n in SAY:
                entry['say'] = SAY[n]
            if n in GENERIC and kind == 'grocery':
                entry['generic'] = True
            chains.append(entry)
    return chains


def main():
    if len(sys.argv) > 1:
        raw = Path(sys.argv[1]).read_text(encoding='utf-8')
        rev = {}
    else:
        req = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Groundwork-build/1.0'}))
        raw = req(RAW_URL).read().decode('utf-8')
        page = next(iter(json.loads(req(REV_URL).read())['query']['pages'].values()))
        rev = page['revisions'][0]
    chains = parse(raw)
    missing = sorted((set(SAY) | GENERIC) - {c['name'] for c in chains})
    if missing:
        sys.exit('SAY or GENERIC names no chain on the page any more: %s' % missing)
    out = {
        'source': 'https://en.wikipedia.org/wiki/' + TITLE,
        'revision': rev.get('revid'), 'revision_time': rev.get('timestamp'),
        'retrieved': date.today().isoformat(),
        'licence': 'CC BY-SA 4.0 (Wikipedia); the names are facts, credited in THIRD_PARTY_NOTICES.md',
        'chains': chains,
    }
    dest = ROOT / 'core' / 'data' / 'grocery_chains.json'
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    kinds = {}
    for c in chains:
        kinds[c['kind']] = kinds.get(c['kind'], 0) + 1
    print(f'{dest}: {len(chains)} chains {kinds}')


if __name__ == '__main__':
    main()
