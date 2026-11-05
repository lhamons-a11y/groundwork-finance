"""The United States' supermarket chains, as a bank line names them (Rob 2026-11-01: "Know they are grocery stores").

core/data/grocery_chains.json is built by scripts/build_grocery_chains.py from Wikipedia's list of supermarket chains in
the United States; it ships with the app and is never fetched by it. Each chain is one of:

    grocery   a supermarket: a bank line naming it is Groceries
    mixed     sells much more than food (Walmart, Target, Costco, Amazon, the dollar stores): left to the other rules
    company   a parent company or buying cooperative: not a name on a receipt

A grocery chain marked `generic` - an everyday word or phrase ("Giant", "Lucky", "Seasons", "Market Street", "City
Market") - is said and heard (core/speak.py, the Ask box), but never decides a category: "LUCKY DRAGON" is not a
supermarket, and "123 MARKET STREET" is an address.

bank_importer.auto_category asks this right after its own Groceries rule, and the page's clientAutoCategory does the
same with the same list (s284 holds them together).
"""
import json
import re
from pathlib import Path

DATA = Path(__file__).parent / 'data' / 'grocery_chains.json'
STORES = Path(__file__).parent / 'data' / 'us_stores.json'
# a bank line that says what kind of store it is
GROCERY_WORDS = re.compile(r'\b(?:supermarkets?|supermercados?)\b')

_compiled = None


def norm(text):
    """Lower case, & as "and", no apostrophes, words only, a plural s dropped - so "STOP & SHOP" is "stop and shop",
    "HARPS FOOD STORE #12" meets "Harps Food Stores", and "WOODMANS" meets "Woodman's"."""
    t = re.sub(r"['’]", '', str(text or '').lower().replace('&', ' and '))
    t = re.sub(r'[^a-z0-9]+', ' ', t).strip()
    return ' '.join(w[:-1] if len(w) > 3 and w.endswith('s') else w for w in t.split())


def load():
    try:
        return json.loads(DATA.read_text(encoding='utf-8')).get('chains', [])
    except Exception:
        return []


def load_stores():
    """The other major stores and payees, {group: [[name, phonetic, heard], ...]} (core/data/us_stores.json) - for the
    voice to hear them. Nothing here decides a category."""
    try:
        return json.loads(STORES.read_text(encoding='utf-8')).get('groups', {})
    except Exception:
        return {}


def _patterns():
    global _compiled
    if _compiled is None:
        _compiled = [(c['name'], re.compile(r'(?:^| )' + re.escape(norm(c['name'])) + r'(?: |$)'))
                     for c in load() if c.get('kind') == 'grocery' and not c.get('generic') and norm(c['name'])]
    return _compiled


def grocery_chain(description):
    """The supermarket a bank line names, or None. The line's own words "supermarket" / "supermercado" count too, for
    a local store the list does not carry ("CHIEF SUPERMARKET 2 MILLBROOK")."""
    d = norm(description)
    if not d:
        return None
    for name, rx in _patterns():
        if rx.search(d):
            return name
    m = GROCERY_WORDS.search(str(description or '').lower())
    return m.group(0) if m else None
