"""
The bank logins Groundwork may use to fetch a user's downloads (gw 2.0/BANK_AGENT.md, item 57 A4; Rob 2026-10-09:
"I agree with keeping the passwords in the security vaults in the operating system").

A login lives ONLY in the operating system's own vault - Windows Credential Manager, the macOS Keychain, or a Linux
Secret Service - through `keyring`, one entry per account, named "Groundwork - <key>" (key 'account:<id>' or
'card:<id>'). Never in Groundwork's database, settings, logs, exports or the narrator. On a system with no vault
(a Linux without a Secret Service), the feature is unavailable; there is no file fallback.

Only the fetch (the bank process, a later stage) reads a password, through read_login(). Nothing here returns a
password to a route, and s172 fails if a route does.
"""
import json
import os

# The vault is the computer's, shared by every Groundwork on it. dev_server.py (and so the bank window it starts, and
# the video maker) sets GROUNDWORK_VAULT_SERVICE, so a throwaway database's 'account:1' can never overwrite or read the
# installed app's 'account:1' - found 2026-11-08, when a dev run was one click from replacing a real saved login.
# Installed, it is unset: 'Groundwork', as always. bank_agent_window.VAULT_SERVICE reads the same (s174).
SERVICE = os.environ.get('GROUNDWORK_VAULT_SERVICE') or 'Groundwork'


def _keyring():
    try:
        import keyring
        return keyring
    except Exception:                                  # noqa: BLE001 - not installed: unavailable, never a fallback
        return None


def available():
    """True when a real operating-system vault is reachable (not keyring's fail or null backend)."""
    kr = _keyring()
    if kr is None:
        return False
    try:
        backend = kr.get_keyring()
    except Exception:                                  # noqa: BLE001
        return False
    name = type(backend).__module__ + '.' + type(backend).__name__
    return not any(bad in name for bad in ('keyring.backends.fail', 'keyring.backends.null', 'chainer.ChainerBackend')) \
        or _chainer_has_real(backend)


def _chainer_has_real(backend):
    for b in getattr(backend, 'backends', []) or []:
        n = type(b).__module__
        if 'fail' not in n and 'null' not in n:
            return True
    return False


def vault_name():
    """The vault's everyday name, for the page."""
    kr = _keyring()
    if kr is None:
        return None
    n = type(kr.get_keyring()).__name__.lower()
    if 'win' in n:
        return 'Windows Credential Manager'
    if 'mac' in n or 'keychain' in n:
        return 'macOS Keychain'
    if 'secret' in n or 'kwallet' in n or 'libsecret' in n:
        return 'your Linux keyring'
    return 'your system\'s password vault'


def _entry(key):
    if not key.startswith(('account:', 'card:', 'bill:')) or not key.split(':', 1)[1].isdigit():
        raise ValueError(f'not a vault key: {key!r}')
    return SERVICE, f'{SERVICE} - {key}'


def save_login(key, username, password):
    """Store one account's login in the vault. Raises RuntimeError when no vault is available."""
    if not available():
        raise RuntimeError('no operating-system vault on this computer')
    service, name = _entry(key)
    _keyring().set_password(service, name, json.dumps({'u': str(username), 'p': str(password)}))


def has_login(key):
    if not available():
        return False
    service, name = _entry(key)
    try:
        return _keyring().get_password(service, name) is not None
    except Exception:                                  # noqa: BLE001
        return False


def forget(key):
    """Delete the vault entry. True when one was there."""
    if not available():
        return False
    service, name = _entry(key)
    try:
        _keyring().delete_password(service, name)
        return True
    except Exception:                                  # noqa: BLE001 - nothing stored
        return False


def read_login(key):
    """(username, password) for the fetch only, or None. Never returned to a route."""
    if not available():
        return None
    service, name = _entry(key)
    raw = _keyring().get_password(service, name)
    if raw is None:
        return None
    d = json.loads(raw)
    return d.get('u', ''), d.get('p', '')
