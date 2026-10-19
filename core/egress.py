"""Item 8 provision 1 (SAFETY_PROVISIONS_INVENTORY.md section 9; Rob 2026-10-19: "approve"): one door out.

Every request Groundwork makes to the internet goes through `get()` here, and `get()` goes only to the hosts below -
each one a service the website's Privacy page names, with what it is sent. Anything else is refused before a byte
leaves: another host, plain http, a port, credentials in the URL, or a redirect that would end somewhere else.
s240 fails if code anywhere else in the app opens an internet connection, or if a host here is not on the Privacy page.

Requests to this computer's own server (127.0.0.1) are not internet requests and do not come through here.
"""
import json
import urllib.parse
import urllib.request

# host -> the Privacy page's name for what it is used for (s240 checks each name is on the page)
ALLOWED = {
    'groundworkfinance.app': 'The update check',
    'query1.finance.yahoo.com': 'Investment prices',
    'api.eia.gov': 'Utility and fuel prices',
    'nominatim.openstreetmap.org': 'Trip distances',
    'data.transportation.gov': 'Flight and travel-cost tables',
    'data.bts.gov': 'Flight and travel-cost tables',
    'www.transtats.bts.gov': 'Flight and travel-cost tables',
    'www.gsa.gov': 'Flight and travel-cost tables',
}


class Refused(Exception):
    """A request the one door does not open."""


def check(url):
    """The URL if it may go out, else Refused. Exact host match: no subdomain or look-alike rides on a listed one."""
    u = urllib.parse.urlsplit(str(url or ''))
    host = (u.hostname or '').lower()
    if u.scheme != 'https':
        raise Refused(f'not https: {u.scheme or "no scheme"}')
    if host not in ALLOWED:
        raise Refused(f'not a service the Privacy page names: {host or "no host"}')
    if u.username or u.password or u.port not in (None, 443):
        raise Refused(f'credentials or a port in the URL: {host}')
    return url


class _StayInside(urllib.request.HTTPRedirectHandler):
    """A redirect is followed only to another allowed https URL."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


urllib.request.install_opener(urllib.request.build_opener(_StayInside))


def get(url, headers=None, timeout=10, limit=None):
    """The response body (bytes) of one GET through the door. Raises Refused, or the network's own error."""
    req = urllib.request.Request(check(url), headers=dict(headers or {}))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        final = getattr(r, 'geturl', lambda: url)()
        check(final)                                    # where it actually ended, not only where it started
        return r.read() if limit is None else r.read(limit)


def get_json(url, headers=None, timeout=10, limit=None):
    return json.loads(get(url, headers=headers, timeout=timeout, limit=limit).decode('utf-8'))
