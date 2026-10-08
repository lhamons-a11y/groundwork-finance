"""
The Google Flights window's one page read (gw 2.0/FLIGHT_FARE_READ.md, item 44; Rob 2026-10-08, R0 (a) and R1-R8).

The flights window runs in the bank window's separate, private process (bank_window.py), which reads nothing from a
page. Item 44 makes one exception, for this window only, and it all lives in this module so that bank_window.py keeps
no page read at all (s126 checks that file):

  R1  one figure: the price in the label of the "Continue to book with ..." button, on Google's booking page
  R2  read when the user clicks that button - nothing is watched, nothing else is kept
  R3  one line back to Groundwork, "fare <amount>", a number only, over $0 and at most $100,000, checked again there
  R5  a label that does not read exactly as expected gives no figure

The child side (create_window, the page script, the api) runs in the window process. The parent side (watch, latest,
clear) runs in Groundwork and reads the child's lines. This module imports nothing of Groundwork's.
"""
import re
import sys
import threading
from datetime import datetime
from urllib.parse import urlsplit

MAX_FARE = 100000
BOOKING_HOST = 'www.google.com'
BOOKING_PATH = '/travel/flights/booking'

# "Continue to book with United, Basic Economy for 690 US dollars" (measured 2026-10-08). Anything else: no figure.
_LABEL = re.compile(r'^Continue to book with .{1,120} for (\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d{1,2}))? US dollars$')
_LINE = re.compile(r'^fare (\d{1,6})\.(\d{2})$')


def fare_from_label(label):
    """The price in a Continue button's label, or None."""
    m = _LABEL.match(label if isinstance(label, str) else '')
    if not m:
        return None
    amount = float(m.group(1).replace(',', '') + '.' + (m.group(2) or '0'))
    return amount if 0 < amount <= MAX_FARE else None


def fare_line(amount):
    return f'fare {amount:.2f}'


def parse_fare_line(line):
    """Groundwork's side of R3: the amount in a 'fare <amount>' line, or None."""
    m = _LINE.match((line or '').strip())
    if not m:
        return None
    amount = float(m.group(1) + '.' + m.group(2))
    return amount if 0 < amount <= MAX_FARE else None


def on_booking_page(url):
    parts = urlsplit(url or '')
    return parts.scheme == 'https' and (parts.hostname or '').lower() == BOOKING_HOST and parts.path.startswith(BOOKING_PATH)


# ── The window process ─────────────────────────────────────────────────────────

# Installed on each page load. It acts only on a real click (isTrusted) on a Continue button while the page is Google's
# booking page, and hands over that button's label - nothing else of the page.
PAGE_SCRIPT = r'''(function () {
  if (window.__gwFareReader) return;
  window.__gwFareReader = true;
  document.addEventListener('click', function (e) {
    if (!e.isTrusted) return;
    if (location.hostname !== 'www.google.com' || location.pathname.indexOf('/travel/flights/booking') !== 0) return;
    var b = e.target && e.target.closest ? e.target.closest('button[aria-label^="Continue to book with "]') : null;
    if (b && window.pywebview && window.pywebview.api && window.pywebview.api.fare_label) {
      window.pywebview.api.fare_label(b.getAttribute('aria-label'));
    }
  }, true);
})();'''


class FareApi:
    """The one function the page may call. It checks the page is Google's booking page before reading the label."""

    def __init__(self, out=None):
        self._window = None
        self._out = out or sys.stdout

    def fare_label(self, label):
        try:
            url = self._window.get_current_url() if self._window else None
        except Exception:
            url = None
        amount = fare_from_label(label) if on_booking_page(url) else None
        if amount is not None:
            self._out.write(fare_line(amount) + '\n')
            self._out.flush()
        return None


def create_window(webview, url, title):
    """The Google Flights window: the bank window's shape, plus the fare reader."""
    api = FareApi()
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
_latest = {'fare': None, 'at': None}


def watch(proc):
    """Read the window process's lines after it is ready; keep the last valid fare. Anything else is ignored."""
    def run():
        try:
            for line in proc.stdout:
                amount = parse_fare_line(line)
                if amount is not None:
                    with _lock:
                        _latest.update(fare=amount, at=datetime.now().isoformat(timespec='seconds'))
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def latest():
    with _lock:
        return dict(_latest)


def clear():
    with _lock:
        _latest.update(fare=None, at=None)
