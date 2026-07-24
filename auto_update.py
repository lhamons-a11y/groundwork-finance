"""
Groundwork — Auto-Update Check
Silently checks for a newer release on boot.
Never auto-installs. User decides when to update.
"""

import json
import threading
import urllib.request
import urllib.error
from version import VERSION_TUPLE, RELEASES_API, RELEASES_PAGE, APP_NAME


def _parse_version(version_str: str):
    """Parse a version string like '1.2.3.0' into a tuple of ints."""
    try:
        clean = version_str.lstrip('v').strip()
        parts = clean.split('.')
        # Pad to 4 parts
        while len(parts) < 4:
            parts.append('0')
        return tuple(int(p) for p in parts[:4])
    except Exception:
        return (0, 0, 0, 0)


def _check_for_update(callback):
    """
    Runs in a background thread. Calls callback(latest_version, release_url)
    if a newer version is available, or callback(None, None) if up to date
    or if the check fails.
    """
    try:
        req = urllib.request.Request(
            RELEASES_API,
            headers={'User-Agent': f'{APP_NAME}/{".".join(str(v) for v in VERSION_TUPLE)}'}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data     = json.loads(resp.read().decode('utf-8'))
            tag      = data.get('tag_name', '')
            html_url = data.get('html_url', RELEASES_PAGE)
            remote   = _parse_version(tag)
            if remote > VERSION_TUPLE:
                callback(tag.lstrip('v'), html_url)
            else:
                callback(None, None)
    except Exception:
        # Network unavailable, API rate-limited, or any other error — silent
        callback(None, None)


def check_for_update_async(on_update_available):
    """
    Non-blocking update check. Fires on_update_available(version, url)
    if a newer release exists. Safe to call on boot — never blocks startup.

    Usage:
        def on_update(version, url):
            # show notification to user
            window.evaluate_js(f'notifyUpdate("{version}", "{url}")')

        check_for_update_async(on_update)
    """
    t = threading.Thread(
        target=_check_for_update,
        args=(on_update_available,),
        daemon=True
    )
    t.start()
