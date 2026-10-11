"""
The Google Hotels window's one page read (gw 2.0/TRIP_REAL_PRICES.md, item 59 P3's optional half; built 2026-10-11,
Rob: "build 58 and 59"). The same shape as item 44's Google Flights read (flights_window.py):

  - one figure: the stay's total with taxes and fees, from the row of the "Visit site for ..." button the person clicks
    on a hotel's price list - read on that click, nothing watched, nothing else kept
  - measured on Google Hotels 2026-10-11: each booking row holds three prices under the page's headings "Nightly base
    price", "Nightly price with taxes + fees" and "Stay total with taxes + fees", and the page says "N nights with
    taxes + fees". The figure counts only when all of that reads exactly so, and the total equals the nightly price
    with taxes times the nights (to within a dollar a night, for Google's rounding)
  - one line back to Groundwork, "hotel <total> <nights>", numbers only, checked again there
  - anything that doesn't read exactly as expected gives no figure

The child side runs in the window process; the parent side (watch, latest, clear) in Groundwork. bank_window.py keeps
no page read at all (s126); it hands Google Hotels windows to this module, as it hands Google Flights to flights_window.
"""
import re
import sys
import threading
from datetime import datetime
from urllib.parse import urlsplit

MAX_TOTAL = 100000
HOST = 'www.google.com'
PATH = '/travel/'
HEADER = 'Stay total with taxes + fees'
_LABEL = re.compile(r'^Visit site for .{1,80}$')
_PRICE = re.compile(r'^\$(\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d{2}))?$')
_NIGHTS = re.compile(r'^(\d{1,2}) nights? with taxes \+ fees$')
_LINE = re.compile(r'^hotel (\d{1,6})\.(\d{2}) (\d{1,2})$')


def _amount(text):
    m = _PRICE.match((text or '').strip())
    if not m:
        return None
    return float(m.group(1).replace(',', '') + '.' + (m.group(2) or '0'))


def total_from_row(label, prices, header_shown, nights_text):
    """(total, nights) from what the click hands over, or None. Exactly three prices, the page's own headings, and a
    total that agrees with the nightly price with taxes."""
    if not (isinstance(label, str) and _LABEL.match(label)) or header_shown is not True:
        return None
    if not isinstance(prices, list) or len(prices) != 3:
        return None
    vals = [_amount(p) for p in prices]
    if any(v is None for v in vals):
        return None
    m = _NIGHTS.match((nights_text or '').strip()) if isinstance(nights_text, str) else None
    if not m:
        return None
    nights = int(m.group(1))
    base, with_fees, total = vals
    if not (0 < base <= with_fees and 0 < total <= MAX_TOTAL and nights >= 1):
        return None
    if abs(with_fees * nights - total) > nights * 1.0:
        return None
    return total, nights


def hotel_line(total, nights):
    return f'hotel {total:.2f} {nights}'


def parse_hotel_line(line):
    m = _LINE.match((line or '').strip())
    if not m:
        return None
    total = float(m.group(1) + '.' + m.group(2))
    nights = int(m.group(3))
    return (total, nights) if 0 < total <= MAX_TOTAL and nights >= 1 else None


def on_hotels_page(url):
    parts = urlsplit(url or '')
    return parts.scheme == 'https' and (parts.hostname or '').lower() == HOST and parts.path.startswith(PATH)


# ── The window process ─────────────────────────────────────────────────────────
# Installed on each page load. It acts only on a real click (isTrusted) on a "Visit site for ..." button on Google's
# travel pages, and hands over that row's three price texts, whether the page shows the stay-total heading, and the
# page's "N nights with taxes + fees" text - nothing else of the page.
PAGE_SCRIPT = r'''(function () {
  if (window.__gwHotelReader) return;
  window.__gwHotelReader = true;
  document.addEventListener('click', function (e) {
    if (!e.isTrusted) return;
    if (location.hostname !== 'www.google.com' || location.pathname.indexOf('/travel/') !== 0) return;
    var b = e.target && e.target.closest ? e.target.closest('[aria-label^="Visit site for "]') : null;
    var row = b ? b.closest('a') : (e.target && e.target.closest ? e.target.closest('a[href^="/aclk"]') : null);
    if (!b && row) b = row.querySelector('[aria-label^="Visit site for "]');
    if (!b || !row || !window.pywebview || !window.pywebview.api || !window.pywebview.api.hotel_row) return;
    var prices = [];
    row.querySelectorAll('span').forEach(function (s) {
      if (s.childElementCount === 0 && /^\$[\d,]+(\.\d\d)?$/.test(s.textContent.trim())) prices.push(s.textContent.trim());
    });
    var leaves = Array.prototype.filter.call(document.querySelectorAll('span, div'), function (x) { return x.childElementCount === 0; });
    var header = leaves.some(function (x) { return x.textContent.trim() === 'Stay total with taxes + fees'; });
    var nights = (leaves.filter(function (x) { return /^\d{1,2} nights? with taxes \+ fees$/.test(x.textContent.trim()); })[0] || {}).textContent || '';
    window.pywebview.api.hotel_row(b.getAttribute('aria-label'), prices, header, nights.trim());
  }, true);
})();'''


class HotelApi:
    """The one function the page may call. It checks the page is Google's travel pages before reading anything."""

    def __init__(self, out=None):
        self._window = None
        self._out = out or sys.stdout

    def hotel_row(self, label, prices, header_shown, nights_text):
        try:
            url = self._window.get_current_url() if self._window else None
        except Exception:
            url = None
        got = total_from_row(label, prices, header_shown, nights_text) if on_hotels_page(url) else None
        if got is not None:
            self._out.write(hotel_line(*got) + '\n')
            self._out.flush()
        return None


def create_window(webview, url, title):
    api = HotelApi()
    window = webview.create_window(title=title, url=url, width=1100, height=800, js_api=api)
    api._window = window

    def on_loaded(*_):
        try:
            window.evaluate_js(PAGE_SCRIPT)
        except Exception:
            pass

    window.events.loaded += on_loaded
    return window


# ── Groundwork's side ──────────────────────────────────────────────────────────
_lock = threading.Lock()
_latest = {'total': None, 'nights': None, 'at': None}


def watch(proc):
    def run():
        try:
            for line in proc.stdout:
                got = parse_hotel_line(line)
                if got is not None:
                    with _lock:
                        _latest.update(total=got[0], nights=got[1], at=datetime.now().isoformat(timespec='seconds'))
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def latest():
    with _lock:
        return dict(_latest)


def clear():
    with _lock:
        _latest.update(total=None, nights=None, at=None)
