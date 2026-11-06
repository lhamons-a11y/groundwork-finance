"""What may leave the Groundwork window for the outside world (security audit 2026-11-05, gap 3).

The page's Content-Security-Policy stops script sending data with fetch, images or forms. It cannot stop script handing
an address to the system browser or walking the window to another site, and an address can carry data. So both go
through here, in Python, where a script in the page cannot reach:

    decide()       an address on its way to the system browser
    stays_home()   an address the main window is about to go to

The sites below are the only ones the page itself links to; s286 fails if app.js links to one that is not listed.
Anything else still opens, on the person's own Yes, in a dialog the page cannot press.
"""
import re
from urllib.parse import urlsplit

KNOWN_HOSTS = (
    'groundworkfinance.app',
    '988lifeline.org',
    'consumerfinance.gov',
    'veteranscrisisline.net',
    'thetrevorproject.org',
    'nfcc.org',
    'lawhelp.org',
    'crisistextline.org',
    '211.org',
    'findahelpline.com',
    'openstreetmap.org',      # the licence credit the road map carries (ROAD_MAP.md)
)
MAX_ADDRESS = 2000
_PHONE = re.compile(r'(?:tel|sms):\d{3,11}')
_LOCAL_HOSTS = ('127.0.0.1', 'localhost')

OPEN, ASK, REFUSE = 'open', 'ask', 'refuse'


def _parts(url):
    """The split address, or None for one that could be read two ways: a trick has no honest use here."""
    if not isinstance(url, str) or not url or len(url) > MAX_ADDRESS:
        return None
    if any(ch.isspace() or ord(ch) < 32 for ch in url) or '\\' in url:
        return None
    try:
        parts = urlsplit(url)
        parts.port                                  # raises on a bad port
    except ValueError:
        return None
    return parts


def decide(url):
    """OPEN, ASK or REFUSE for an address on its way to the system browser."""
    if isinstance(url, str) and _PHONE.fullmatch(url):
        return OPEN                                 # a help line's Call / Text: digits only, so it can carry nothing
    parts = _parts(url)
    if parts is None or parts.scheme.lower() not in ('http', 'https') or not parts.hostname:
        return REFUSE
    if parts.username is not None or parts.password is not None or '@' in parts.netloc:
        return REFUSE
    host = parts.hostname.rstrip('.').lower()
    known = host in KNOWN_HOSTS or (host.startswith('www.') and host[4:] in KNOWN_HOSTS)
    if parts.scheme.lower() == 'https' and known and parts.port in (None, 443):
        return OPEN
    return ASK


def ask_words(url):
    """(title, message) for the person's Yes. The whole address is shown: what it carries is theirs to see."""
    return ('Open this in your web browser?',
            'Groundwork was asked to open this address in your web browser:\n\n' + url +
            '\n\nOpen it only if you just asked for this and you recognise the address.')


def stays_home(url, port):
    """True when the main window may go to this address: Groundwork's own server on its own port, or a blank page."""
    if url == 'about:blank':
        return True
    if isinstance(url, str) and url.startswith('blob:'):        # a file the page made and is saving; same origin only
        url = url[5:]
    parts = _parts(url)
    if parts is None or parts.scheme.lower() != 'http' or parts.username is not None or parts.password is not None:
        return False
    return parts.hostname in _LOCAL_HOSTS and parts.port == port


def window_may_go(url, port, new_window):
    """WebKit's question, on a Mac and on Linux, before it sends anything. A new window (target=_blank) is let through
    because it loads nothing here: pywebview hands that address to webbrowser.open, which is open_external."""
    return bool(new_window) or stays_home(url, port)
