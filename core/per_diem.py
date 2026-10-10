"""
Groundwork - the federal per-diem rates (gw 2.0/TRIP_REAL_PRICES.md, item 59 P2)
===============================================================================
Lodging and meals for a U.S. trip, from the U.S. General Services Administration's per-diem rates: the most a federal
traveller is reimbursed for a night's lodging and a day's meals and incidentals, by city (and county) and season.
Published once a year (effective October 1) as one public spreadsheet; works of the U.S. government, free to copy.

  - A table ships with the app (core/data/gsa_per_diem.json), built from GSA's file; refresh() downloads the next
    fiscal year's file from gsa.gov when it is out. The download is GSA's whole table - nothing about anyone's trip
    is sent. Looking a destination up never leaves the computer.
  - It is the federal travel rate, NOT a hotel quote: every line built from it says so.
  - A destination GSA does not list by name returns found: False - "no published rate for this destination; enter
    yours". GSA's standard rate covers unlisted COUNTIES, and a city name alone cannot say which county it is in,
    so it is never guessed from a name.
  - google_hotels_url (P3): Google Hotels for the destination, dates and guests, written as search text - the form
    Google fills from (checked 2026-10-10: the dates and guests fill in; its check-in parameters are ignored).
"""
import json
import logging
import os
import re
import threading
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

from core.database import DATA_DIR

logger = logging.getLogger('groundwork.per_diem')

SOURCE = 'U.S. GSA per-diem rates'
FILES_PAGE = 'https://www.gsa.gov/travel/plan-a-trip/per-diem-rates/per-diem-files'
SHIPPED = Path(__file__).parent / 'data' / 'gsa_per_diem.json'
DOWNLOADED = DATA_DIR / 'gsa_per_diem.json'
CHECK_EVERY = timedelta(days=30)      # GSA publishes once a year; a monthly look is plenty
REQUEST_TIMEOUT = 30
MIN_ROWS = 300                        # a real year has ~640 rows; fewer means a bad download
_MONTHS = {m: i for i, m in enumerate(('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                       'september', 'october', 'november', 'december'), 1)}
_NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
_lock = threading.Lock()


# ── GSA's spreadsheet, read with the standard library only ──────────────────────
def _xlsx_rows(data):
    z = zipfile.ZipFile(BytesIO(data))
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', _NS):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % _NS['m'])))
    sheet = sorted(n for n in z.namelist() if n.startswith('xl/worksheets/sheet'))[0]
    for r in ET.fromstring(z.read(sheet)).iter('{%s}row' % _NS['m']):
        out = {}
        for c in r.findall('m:c', _NS):
            col = re.match(r'[A-Z]+', c.get('r')).group(0)
            v = c.find('m:v', _NS)
            if c.get('t') == 's' and v is not None:
                out[col] = shared[int(v.text)]
            elif c.get('t') == 'inlineStr':
                out[col] = ''.join(x.text or '' for x in c.iter('{%s}t' % _NS['m']))
            else:
                out[col] = v.text if v is not None else ''
        yield out


def _md(text):
    """'October 1, 2026' -> '10-01' (a season's day of the year, in GSA's fiscal year)."""
    m = re.match(r'\s*([A-Za-z]+)\s+(\d{1,2})', str(text or ''))
    if not m or m.group(1).lower() not in _MONTHS:
        return None
    return f'{_MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}'


def build_from_xlsx(data, url=''):
    """GSA's per-diem spreadsheet -> the table this module reads, or None when it doesn't look like GSA's."""
    rows = list(_xlsx_rows(data))
    title = next((r.get('A', '') for r in rows[:3] if 'Per Diem' in r.get('A', '')), '')
    fy = re.search(r'FY\s?(\d{4})', title)
    eff = re.search(r'Effective\s+(.+)$', title)
    out, standard = [], None
    for r in rows:
        try:
            lodging, mie = int(float(r.get('F') or 0)), int(float(r.get('G') or 0))
        except ValueError:
            continue
        if lodging <= 0 or mie <= 0:
            continue
        if not r.get('A'):
            if 'Standard' in (r.get('B') or ''):
                standard = {'lodging': lodging, 'mie': mie}
            continue
        begin, end = _md(r.get('D')), _md(r.get('E'))
        if not begin or not end:
            continue
        out.append({'state': r['A'].strip().upper(), 'dest': (r.get('B') or '').strip(),
                    'counties': (r.get('C') or '').strip(), 'begin': begin, 'end': end, 'lodging': lodging, 'mie': mie})
    if not fy or len(out) < MIN_ROWS:
        return None
    return {'fy': int(fy.group(1)), 'effective': eff.group(1).strip() if eff else '', 'source': SOURCE, 'url': url,
            'standard': standard, 'rows': out}


# ── The table ──────────────────────────────────────────────────────────────────
def _read(path):
    try:
        with open(path, encoding='utf-8') as f:
            t = json.load(f)
        return t if isinstance(t, dict) and isinstance(t.get('fy'), int) and len(t.get('rows') or []) >= MIN_ROWS else None
    except (OSError, ValueError):
        return None


def table():
    """The newest valid table: the downloaded one when it is a later fiscal year than the shipped one."""
    best = None
    for path in (SHIPPED, DOWNLOADED):
        t = _read(path)
        if t and (best is None or t['fy'] > best['fy']):
            best = t
    return best


def _names(text):
    """'Dallas/Fort Worth, TX (Metropolitan Area)' -> ({'dallas', 'fort worth'}, 'TX')."""
    s = re.sub(r'\(.*?\)', '', str(text or '')).strip()
    state = None
    m = re.search(r',\s*([A-Za-z]{2})\s*$', s)
    if m:
        state, s = m.group(1).upper(), s[:m.start()]
    return [p.strip().lower() for p in re.split(r'/|,', s) if p.strip()], state     # in order: the first named leads


def _in_season(md, begin, end):
    return begin <= md <= end if begin <= end else (md >= begin or md <= end)


def lookup(destination, on_date):
    """GSA's rate for a destination on a date: {found, dest, state, lodging, mie, season, fy, source} or
    {found: False, reason}. `on_date` a date or 'YYYY-MM-DD'."""
    t = table()
    if not t:
        return {'found': False, 'reason': 'no_table'}
    if isinstance(on_date, str):
        try:
            on_date = date.fromisoformat(on_date[:10])
        except ValueError:
            return {'found': False, 'reason': 'no_date'}
    names, state = _names(destination)
    if not names:
        return {'found': False, 'reason': 'no_destination'}
    hits = []
    for name in names:                    # 'Dallas/Fort Worth' is the Dallas market: the first name that GSA lists leads
        hits = [r for r in t['rows'] if (not state or r['state'] == state)
                and name in {p.strip().lower() for p in r['dest'].split('/')}]
        if hits:
            break
    if not hits:
        return {'found': False, 'reason': 'not_listed'}
    if len({(r['state'], r['dest']) for r in hits}) > 1:
        return {'found': False, 'reason': 'ambiguous', 'places': sorted({f"{r['dest']}, {r['state']}" for r in hits})}
    md = on_date.strftime('%m-%d')
    r = next((r for r in hits if _in_season(md, r['begin'], r['end'])), None)
    if not r:
        return {'found': False, 'reason': 'no_season'}
    return {'found': True, 'dest': r['dest'], 'state': r['state'], 'counties': r['counties'], 'lodging': r['lodging'],
            'mie': r['mie'], 'season': [r['begin'], r['end']], 'fy': t['fy'], 'source': SOURCE}


# ── The yearly refresh ─────────────────────────────────────────────────────────
def _checked_path():
    return DATA_DIR / 'gsa_per_diem.checked'


def _get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Groundwork (personal finance app)'})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
        return r.read()


def current_fy(today=None):
    today = today or date.today()
    return today.year + 1 if today.month >= 10 else today.year


def refresh(force=False):
    """Download GSA's file for the current fiscal year when the app's table is older. At most one look a month
    unless forced. Never raises; the current table stays in use on any failure. Nothing about a trip is sent."""
    if not _lock.acquire(blocking=False):
        return {'updated': False, 'reason': 'already_running'}
    try:
        checked = _checked_path()
        if not force:
            try:
                last = datetime.fromisoformat(checked.read_text(encoding='utf-8').strip())
                if datetime.now() - last < CHECK_EVERY:
                    return {'updated': False, 'reason': 'checked_recently'}
            except (OSError, ValueError):
                pass
        cur, want = table(), current_fy()
        if cur and cur['fy'] >= want:
            result = {'updated': False, 'reason': 'already_latest'}
        else:
            try:
                page = _get(FILES_PAGE).decode('utf-8', 'replace')
                m = re.search(r'href="([^"]*FY%s[^"]*PerDiemRates[^"]*\.xlsx)"' % want, page, re.I)
                if not m:
                    result = {'updated': False, 'reason': 'not_published'}
                else:
                    url = urllib.parse.urljoin(FILES_PAGE, m.group(1))
                    t = build_from_xlsx(_get(url), url)
                    if not t or t['fy'] != want:
                        result = {'updated': False, 'reason': 'bad_download'}
                    else:
                        DOWNLOADED.write_text(json.dumps(t), encoding='utf-8')
                        result = {'updated': True, 'fy': t['fy']}
            except Exception as e:                       # noqa: BLE001 - a refresh never breaks the app
                logger.info('per-diem refresh failed: %s', e)
                result = {'updated': False, 'reason': 'unreachable'}
        try:
            checked.write_text(datetime.now().isoformat(timespec='seconds'), encoding='utf-8')
        except OSError:
            pass
        return result
    finally:
        _lock.release()


def google_hotels_url(destination, checkin, checkout, guests=1):
    """P3: Google Hotels for the trip, as search text Google fills its form from. None without a destination."""
    dest = re.sub(r'\(.*?\)', '', str(destination or '')).strip()
    if not dest:
        return None
    q = f'hotels in {dest}'
    try:
        a, b = date.fromisoformat(str(checkin)[:10]), date.fromisoformat(str(checkout)[:10])
        q += f" from {a.strftime('%B')} {a.day} {a.year} to {b.strftime('%B')} {b.day} {b.year}"
    except ValueError:
        pass
    g = max(1, int(guests or 1))
    q += f" for {g} adult{'s' if g != 1 else ''}"
    return 'https://www.google.com/travel/search?' + urllib.parse.urlencode({'q': q})
