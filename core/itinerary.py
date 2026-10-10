"""
Groundwork - bring in a whole itinerary (gw 2.0/TRIP_ITINERARY_IMPORT.md, item 60, I1-I7)
=========================================================================================
A pasted confirmation, a PDF or a saved email (.eml) becomes a list of parts - flight, lodging, car, activity,
transfer, insurance, fees - each with its dates, its figures as printed, and paid / deposit / due later.

  - I1  read on this computer: PDF text by the existing statement reader, .eml by the standard library. Nothing is
        fetched, no account is connected, and the file is never kept (I6).
  - I5  known formats first, no model: Expedia, Booking.com, an airline's receipt, a hotel chain's folio. Each reads
        the document's own price lines. Everything else goes to the local model, which only transcribes (I2).
  - I3  every figure must be in the document (the same number check as the PDF statement reader). A figure that
        isn't is dropped and said. Groundwork's sum of the kept parts is shown beside the document's printed total;
        when they differ both are shown, never reconciled.
  - I6  confirmation numbers are taken out of the text before anything else sees it (the model, the AI log); a
        flight's number travels only with that part, for the booking the person may record (item 50).

Nothing here writes to the database: what is used is decided in the page, on the person's yes (I4).
"""
import email
import email.policy
import re
from datetime import date

from pdf_statement import _financial_numbers, _number_candidates

KINDS = ('flight', 'lodging', 'car', 'activity', 'transfer', 'insurance', 'fees')
STATUSES = ('paid', 'deposit', 'due_later', 'unknown')
MAX_BYTES = 10 * 1024 * 1024
MODEL_CHARS = 6000

_MONEY = re.compile(r'(?:US)?\$\s?(\d[\d,]*(?:\.\d{1,2})?)')
# A part's heading words, most specific first: "Airport transfer" is a transfer, not a flight.
_KIND_WORDS = (
    ('insurance', r'\b(insurance|protection plan|travel protection|trip protection)\b'),
    ('transfer', r'\b(transfers?|shuttle|airport ride)\b'),
    ('car', r'\b(car rental|rental car|car)\b'),
    ('activity', r'\b(activit(?:y|ies)|things to do|tours?|excursions?|attraction)\b'),
    ('lodging', r'\b(hotels?|lodging|property|stay|rooms?|resort|accommodations?|vacation rental|suite)\b'),
    ('flight', r'\b(flights?|airfare|air fare|fare|ticket)\b'),
)
_TAX = re.compile(r'\b(tax(?:es)?|fees?|surcharges?|charges)\b', re.I)
_OWN_FEE = re.compile(r'\b(booking|service|trip|processing|change) fee\b', re.I)
_TOTAL = re.compile(r'^\s*(?:trip\s+|grand\s+|order\s+)?total\b|\btotal\s+(?:price|charged|cost|due|paid|for (?:your )?(?:trip|stay))\b', re.I)
_SUBTOTAL = re.compile(r'\bsub-?total\b', re.I)
_SUMMARY = re.compile(r'^\s*(price summary|price details|payment summary|price breakdown|cost summary|your price|'
                      r'summary of charges|charges|payment details|fare (?:summary|breakdown|details))\b', re.I)
_STATUS = (
    ('due_later', re.compile(r"\b(due at (?:the )?(?:property|hotel|pick-?up)|pay(?:able)? at (?:the )?(?:property|hotel|pick-?up)|"
                             r"pay later|due later|balance due|you'll pay when you stay|pay when you stay)\b", re.I)),
    ('deposit', re.compile(r'\bdeposit\b', re.I)),
    ('paid', re.compile(r'\b(paid in full|amount paid|paid|charged to your card|total charged)\b', re.I)),
)
_CONF = re.compile(r'((?:\b[a-z]+\s+){0,2}(?:confirmation|itinerary|record locator|booking|reservation|ticket|reference)\s*'
                   r'(?:number|no\.?|#|code|id)?\s*[:#]?\s*)([A-Z0-9][A-Z0-9-]{4,24})\b', re.I)
_MONTHS = {m[:3]: i for i, m in enumerate(('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                            'september', 'october', 'november', 'december'), 1)}
_DATE = re.compile(r'\b(\d{4})-(\d{2})-(\d{2})\b|\b(\d{1,2})/(\d{1,2})/(\d{4})\b|'
                   r'\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b|\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b')
AIRLINES = ('Delta', 'United', 'American Airlines', 'Southwest', 'Alaska Airlines', 'JetBlue', 'Spirit', 'Frontier',
            'Allegiant', 'Hawaiian Airlines', 'Sun Country', 'Air Canada', 'British Airways', 'Lufthansa', 'Air France',
            'WestJet', 'Breeze Airways', 'Avelo')
HOTEL_CHAINS = ('Marriott', 'Hilton', 'Hyatt', 'IHG', 'Holiday Inn', 'Wyndham', 'Choice Hotels', 'Best Western',
                'Hampton Inn', 'Courtyard', 'Embassy Suites', 'Radisson', 'La Quinta')


# ── I1: the document, read on this computer ────────────────────────────────────
def text_from_upload(filename, data):
    """PDF / .eml / .txt / .html bytes -> plain text. Raises ValueError with a plain reason."""
    if not data:
        raise ValueError('The file is empty.')
    if len(data) > MAX_BYTES:
        raise ValueError('That file is over 10 MB - a confirmation is much smaller.')
    name = (filename or '').lower()
    if name.endswith('.pdf') or data[:5] == b'%PDF-':
        import pdf_statement
        return pdf_statement.extract_text(data)
    if name.endswith('.eml'):
        msg = email.message_from_bytes(data, policy=email.policy.default)
        part = msg.get_body(preferencelist=('plain', 'html'))
        if part is None:
            raise ValueError('No readable text in that email.')
        body = part.get_content()
        return _html_text(body) if part.get_content_type() == 'text/html' else body
    text = data.decode('utf-8', 'replace')
    return _html_text(text) if name.endswith(('.html', '.htm')) else text


def _html_text(html):
    html = re.sub(r'(?is)<(script|style).*?</\1>', ' ', html)
    html = re.sub(r'(?i)<br\s*/?>|</(p|div|tr|li|h\d|table)>', '\n', html)
    html = re.sub(r'(?i)</t[dh]>', '  ', html)
    text = re.sub(r'<[^>]+>', '', html)
    for a, b in (('&nbsp;', ' '), ('&amp;', '&'), ('&#36;', '$'), ('&dollar;', '$'), ('&lt;', '<'), ('&gt;', '>')):
        text = text.replace(a, b)
    return '\n'.join(re.sub(r'[ \t]+', ' ', l).strip() for l in text.splitlines() if l.strip())


# ── I6: confirmation numbers out before anything else sees the text ────────────
def take_confirmations(text):
    """-> (text with each confirmation number replaced, [{'kind', 'code'}]). A code must hold a digit, so a word
    after 'Booking' is never taken for one."""
    found = []

    def repl(m):
        code = m.group(2)
        if not re.search(r'\d', code):
            return m.group(0)
        lead = m.group(1)
        found.append({'kind': 'flight' if re.search(r'\b(airline|flight|record locator|ticket)\b', lead, re.I) else _kind_of(lead),
                      'code': code})
        return m.group(1) + '[number removed]'
    return _CONF.sub(repl, text or ''), found


# ── helpers ────────────────────────────────────────────────────────────────────
def _kind_of(label):
    for kind, pat in _KIND_WORDS:
        if re.search(pat, label or '', re.I):
            return kind
    return None


def _money(line):
    return [float(v.replace(',', '')) for v in _MONEY.findall(line)]


def _label(line):
    return re.sub(r'\s{2,}', ' ', _MONEY.sub('', line)).strip(' :-–—\t')


def _status_of(line):
    for st, pat in _STATUS:
        if pat.search(line):
            return st
    return None


def parse_date(s):
    """The first full date in s (a year is required - never assumed) -> 'YYYY-MM-DD' or None."""
    for m in _DATE.finditer(s or ''):
        try:
            if m.group(1):
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
            if m.group(4):
                return date(int(m.group(6)), int(m.group(4)), int(m.group(5))).isoformat()
            mon, day, yr = (m.group(7), m.group(8), m.group(9)) if m.group(7) else (m.group(11), m.group(10), m.group(12))
            if mon[:3].lower() in _MONTHS:
                return date(int(yr), _MONTHS[mon[:3].lower()], int(day)).isoformat()
        except ValueError:
            continue
    return None


def _dated(text, words):
    """The date on the first line that starts with one of `words` (e.g. Check-in), or None."""
    for line in text.splitlines():
        if re.match(r'\s*(?:%s)\b' % '|'.join(words), line, re.I):
            d = parse_date(line)
            if d:
                return d
    return None


def _new(kind, vendor):
    return {'kind': kind, 'vendor': vendor[:80] or kind.title(), 'lines': [], 'status': None, 'start': None, 'end': None}


# ── I5: the known formats ──────────────────────────────────────────────────────
def _price_lines(lines, default=None):
    """A document's price lines -> (parts, printed_total, paid_after_total, due_after_total). Each money line goes
    to the part above it: a heading names the part ("Hotel"), taxes and fees join it, a total closes it; a line
    that opens with 'Total' and names no part is the document's own total."""
    parts, cur, printed, after = [], None, None, []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        money, label = _money(line), _label(line)
        status = _status_of(line)
        if printed is not None:                      # below the document's total: only what was paid / is due
            if status:
                after.append((status, money[-1] if money else None))
            continue
        kind = _kind_of(label)
        if not money:
            if status:                                # "Payable at the hotel" says how a part is paid, not a new part
                if cur:
                    cur['status'] = status
            elif kind and len(label) <= 80:
                cur = _new(kind, label)
                parts.append(cur)
            continue
        amt = money[-1]
        if _TOTAL.search(label) and not kind:
            printed = amt
            continue
        if _OWN_FEE.search(label):
            fee = _new('fees', label)
            fee['lines'].append({'label': label, 'amount': amt, 'role': 'price'})
            parts.append(fee)
            continue
        if cur is None or (kind and not _TAX.search(label) and not _SUBTOTAL.search(label) and not re.search(r'\btotal\b', label, re.I)):
            if cur is None and not kind and default is None:
                continue                              # a figure with no part to belong to: left out, never guessed
            cur = _new(kind or default, label)
            parts.append(cur)
        role = 'total' if (_SUBTOTAL.search(label) or re.search(r'\btotal\b', label, re.I)) else \
               'taxes_fees' if _TAX.search(label) else 'price'
        cur['lines'].append({'label': label, 'amount': amt, 'role': role})
        if status and role != 'taxes_fees':
            cur['status'] = cur['status'] or status
    return [p for p in parts if p['lines']], printed, after


def _summary_block(text):
    lines = text.splitlines()
    i = next((n for n, l in enumerate(lines) if _SUMMARY.match(l)), None)
    return lines[i + 1:] if i is not None else None


def _sender(text):
    low = text.lower()
    if 'expedia' in low:
        return 'expedia', 'Expedia'
    if 'booking.com' in low:
        return 'booking_com', 'Booking.com'
    for name in AIRLINES:
        if re.search(r'\b%s\b' % re.escape(name), text):
            return 'airline', name
    for name in HOTEL_CHAINS:
        if re.search(r'\b%s\b' % re.escape(name), text):
            return 'hotel_chain', name
    return None, None


def read_known(text):
    """I5: the parts of a known sender's document, without a model. None when the sender or its layout isn't one
    Groundwork reads - the model then reads it (I2), or with AI off the person fills the trip in by hand."""
    fmt, sender = _sender(text)
    if not fmt:
        return None
    block = _summary_block(text)
    default = {'airline': 'flight', 'hotel_chain': 'lodging', 'booking_com': 'lodging'}.get(fmt)
    if block is None:
        if fmt == 'expedia':
            return None                               # Expedia's price summary is how its parts are told apart
        block = text.splitlines()
    parts, printed, after = _price_lines(block, default)
    if not parts:
        return None
    for p in parts:                                   # a one-vendor document names its part by the vendor
        if default and p['kind'] == default and len(parts) <= 2 and fmt != 'expedia':
            p['vendor'] = sender
        named = re.search(r'^\s*%s\s*:\s*([^\n$]{2,60})$' % re.escape(p['vendor']), text, re.I | re.M)
        if named:                                     # "Hotel: The Curtis Denver" names the Hotel part
            p['vendor'] = named.group(1).strip()
    if printed is None and len(parts) == 1:           # a one-part folio's own total is the document's total
        printed = next((l['amount'] for l in reversed(parts[0]['lines']) if l['role'] == 'total'), None)
    flights = [p for p in parts if p['kind'] == 'flight']
    airline = next((a for a in AIRLINES if re.search(r'\b%s\b' % re.escape(a), text)), None)
    for p in flights:
        if airline:
            p['vendor'] = airline
        p['start'] = _dated(text, ('depart', 'departure', 'departing', 'outbound', 'flight date'))
        p['end'] = _dated(text, ('return', 'returning', 'inbound'))
    for p in parts:
        if p['kind'] == 'lodging':
            p['start'] = _dated(text, ('check-in', 'check in', 'arrival', 'arrive'))
            p['end'] = _dated(text, ('check-out', 'check out', 'departure date'))
        elif p['kind'] == 'car':
            p['start'] = _dated(text, ('pick-up', 'pick up', 'pickup'))
            p['end'] = _dated(text, ('drop-off', 'drop off', 'dropoff', 'return'))
    for st, amt in after:                             # under the total: "Amount paid $X", "You'll pay when you stay"
        if st == 'due_later':
            for p in parts:
                if p['kind'] == 'lodging' and (amt is None or abs((_amount(p)[0] or 0) - amt) < 0.005):
                    p['status'] = 'due_later'
    for st, amt in after:
        due = sum(_amount(p)[0] or 0 for p in parts if p['status'] in ('due_later', 'deposit'))
        if st == 'paid' and printed is not None and (amt is None or abs(amt - (printed - due)) < 0.005):
            for p in parts:                           # paid = the total less what is still due: the rest is paid
                p['status'] = p['status'] or 'paid'
    return {'format': fmt, 'sender': sender, 'parts': parts, 'printed_total': printed}


# ── I3: every figure must be in the document ───────────────────────────────────
def _amount(p):
    """(the part's amount, how it was found): its printed total, else Groundwork's sum of its price and tax lines."""
    tot = [l['amount'] for l in p['lines'] if l['role'] == 'total']
    if tot:
        return tot[-1], 'printed'
    rest = [l['amount'] for l in p['lines'] if l['role'] != 'total']
    if not rest:
        return None, None
    return round(sum(rest), 2), ('printed' if len(rest) == 1 else 'sum')


def finish(found, text, confirmations=(), source='format'):
    """Check every figure against the document, then lay the parts out for the page. Drops and says what fails."""
    nums = _financial_numbers(text)
    in_doc = lambda v: v is not None and bool(_number_candidates(v) & nums)
    warnings, parts = [], []
    flight_codes = [c['code'] for c in confirmations if c['kind'] == 'flight'] or                    [c['code'] for c in confirmations if c['kind'] is None]
    for n, p in enumerate(found.get('parts') or []):
        kept = []
        for l in p['lines']:
            if in_doc(l['amount']):
                kept.append(l)
            else:
                warnings.append(f"{p['vendor']}: {l['label'] or l['role']} (${l['amount']:,.2f}) is not in the document - dropped")
        p = {**p, 'lines': kept}
        amt, basis = _amount(p)
        out = {'id': n, 'kind': p['kind'], 'vendor': p['vendor'], 'start': p.get('start'), 'end': p.get('end'),
               'status': p.get('status') or 'unknown', 'lines': kept, 'amount': amt, 'basis': basis}
        if p['kind'] == 'flight' and flight_codes:
            out['confirmation'] = flight_codes[0]
        parts.append(out)
    printed = found.get('printed_total')
    if printed is not None and not in_doc(printed):
        warnings.append(f'the total (${printed:,.2f}) is not in the document - dropped')
        printed = None
    kept_sum = round(sum(p['amount'] for p in parts if p['amount'] is not None), 2)
    return {'format': found.get('format'), 'sender': found.get('sender') or 'your', 'source': source, 'parts': parts,
            'printed_total': printed, 'sum': kept_sum,
            'agree': None if printed is None else abs(printed - kept_sum) < 0.005, 'warnings': warnings}


def from_model(raw, text, confirmations=()):
    """I2/I3: the model's transcription -> parts, each figure checked against the document. The model never adds:
    a part with a price and taxes but no printed total is summed by Groundwork and said so."""
    if not isinstance(raw, dict):
        return None
    warnings, parts = [], []
    for c in (raw.get('components') or raw.get('parts') or [])[:20]:
        if not isinstance(c, dict):
            continue
        kind = c.get('kind') if c.get('kind') in KINDS else None
        vendor = str(c.get('vendor') or '').strip()[:80]
        if not kind:
            warnings.append(f"a part the reader called {str(c.get('kind'))[:20]!r} is not one Groundwork knows - left out")
            continue
        p = _new(kind, vendor)
        for field, role in (('price', 'price'), ('taxes_fees', 'taxes_fees'), ('total', 'total')):
            v = c.get(field)
            try:
                v = None if v is None else abs(float(v))
            except (TypeError, ValueError):
                v = None
            if v:
                p['lines'].append({'label': field.replace('_', ' and '), 'amount': round(v, 2), 'role': role})
        for k in ('start', 'end'):
            v = str(c.get(k) or '')
            p[k] = v if re.fullmatch(r'\d{4}-\d{2}-\d{2}', v) else None
        p['status'] = c.get('status') if c.get('status') in STATUSES else None
        parts.append(p)
    pt = raw.get('printed_total')
    try:
        pt = None if pt is None else abs(float(pt))
    except (TypeError, ValueError):
        pt = None
    sender = str(raw.get('sender') or '').strip()[:40] or None
    out = finish({'format': None, 'sender': sender, 'parts': parts, 'printed_total': pt}, text, confirmations, source='model')
    out['warnings'] = warnings + out['warnings']
    return out


def text_for_model(text):
    """The lines that carry a part: money, a part's name, a date, a status - so a long email fits the local
    model's window. The number check still runs against the whole document."""
    keep = [l for l in text.splitlines() if l.strip() and (_MONEY.search(l) or _kind_of(l) or parse_date(l) or _status_of(l)
                                                            or _TOTAL.search(l))]
    return '\n'.join(keep)[:MODEL_CHARS]
