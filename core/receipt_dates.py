"""
Groundwork - trial and return dates, read from a receipt (gw 2.0/BYB_AGENT.md, item 73 stage 2: Y2)
===================================================================================================
A confirmation the person drops or pastes is read on this computer (item 60's reader) for the dates it states:

  - trial_ends   a free trial's end, and the price after it when the receipt states one
  - return_by    the last day to return or exchange
  - cancel_by    the last day to cancel before a charge

Every date must be written with its year - a date without one is dropped and said, never assumed. A price after a
trial must appear in the receipt (the statement reader's number check). The receipt's own line is kept as the
phrase, so the person sees what it said. Nothing is fetched, the file is not kept, and Groundwork never cancels or
returns anything - the person does.
"""
import re

from core.itinerary import parse_date, take_confirmations
from pdf_statement import _financial_numbers, _number_candidates

KINDS = ('trial_ends', 'return_by', 'cancel_by')
_PATTERNS = (
    ('cancel_by', re.compile(r'\b(cancel (?:by|before|on or before|anytime before)|to avoid (?:being )?charged?,? cancel)\b', re.I)),
    ('trial_ends', re.compile(r'\b(free trial|trial (?:period )?ends?|your trial|trial will end|free until|'
                              r'first (?:charge|payment|billing) (?:on|date)|will be (?:charged|billed) on|renews on)\b', re.I)),
    ('return_by', re.compile(r'\b(return (?:by|before|window|or exchange by)|returnable (?:until|through|by)|'
                             r'eligible for (?:a )?return (?:until|through)|returns? accepted (?:until|through)|'
                             r'refund (?:by|until))\b', re.I)),
)
_PRICE = re.compile(r'\$\s?(\d[\d,]*(?:\.\d{1,2})?)\s*(?:/|per|a|each)?\s*(month|mo|year|yr|week|wk)?', re.I)
_MONTHWORD = re.compile(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b', re.I)


def _merchant(text):
    """The sender: the first short line that is not a greeting or a date."""
    for line in text.splitlines():
        s = line.strip()
        if 2 <= len(s) <= 60 and not re.search(r'\b(dear|hi|hello|thank|order|receipt|confirmation)\b', s, re.I) \
                and not parse_date(s) and not _PRICE.search(s):
            return s
    return ''


def read(text):
    """-> {'merchant', 'dates': [{kind, date, price_after, every, phrase}], 'warnings': [...]}. Nothing is saved."""
    text, _codes = take_confirmations(text or '')
    nums = _financial_numbers(text)
    dates, warnings, seen = [], [], set()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        kind = next((k for k, pat in _PATTERNS if pat.search(line)), None)
        if not kind:
            continue
        # the date sits on the line, or (a label on its own) on the next line
        d = parse_date(line) or (parse_date(lines[i + 1]) if i + 1 < len(lines) and len(line) < 40 else None)
        if not d:
            mw = _MONTHWORD.search(line)
            if mw:
                warnings.append((mw.group(0), f'"{line[:80]}" gives a date without a year - left out rather than guessed'))
            continue
        price, every = None, None
        # the price after: on the line, or on the next one or two (a label, its date, then its terms)
        m = next((x for x in (_PRICE.search(l) for l in lines[i:i + 3]) if x), None)
        if m and kind == 'trial_ends':
            v = float(m.group(1).replace(',', ''))
            if _number_candidates(v) & nums:
                price = round(v, 2)
                every = {'mo': 'month', 'month': 'month', 'yr': 'year', 'year': 'year', 'wk': 'week',
                         'week': 'week'}.get((m.group(2) or '').lower())
        key = (kind, d)
        if key in seen:
            continue
        seen.add(key)
        dates.append({'kind': kind, 'date': d, 'price_after': price, 'every': every, 'phrase': line[:160]})
    # a date already read with its year needs no warning when it is mentioned again without one
    have = {(int(x['date'][5:7]), int(x['date'][8:10])) for x in dates}
    months = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')

    def month_day(md):
        word, day = md.lower().replace('.', '').split()[0][:3], int(md.split()[-1])
        return (months.index(word) + 1, day) if word in months else None
    kept = [w for md, w in warnings if month_day(md) not in have]
    return {'merchant': _merchant(text), 'dates': dates, 'warnings': kept}
