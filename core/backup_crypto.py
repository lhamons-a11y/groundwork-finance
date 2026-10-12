"""The perfect backup (gw 2.0/PERFECT_BACKUP.md, item 81, B1-B9 ruled 2026-10-12).

One random backup key seals every backup (AES-256-GCM). It is never stored in the clear: it sits in this computer's
own vault, and each backup's header carries it twice more, wrapped - once by the backup password (scrypt), once by
the 24-word recovery key (HKDF). Any of the three opens a backup; a thief with the file has none of them. Nothing here
sends a key anywhere, and no key is ever logged or exported (H6's sink registry).

File format, read by every later Groundwork (B5):
    b'GWBK1\\n' | 4-byte header length | header JSON | 12-byte nonce | ciphertext (AES-GCM, header bound as AAD)
"""
import base64
import hashlib
import json
import os
import secrets
import struct
from datetime import datetime

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.exceptions import InvalidTag

MAGIC = b'GWBK1\n'
SETTING = 'backup_protection'
MIN_PASSWORD = 10
SCRYPT = {'n': 2 ** 15, 'r': 8, 'p': 1}
VAULT_USER = 'backup-key'
WORDS = 24

# 256 plain words, one byte each: 24 words carry 192 bits. Short, distinct, easy to write by hand. FIXED FOREVER:
# every recovery key ever written down is read against this exact order, so it may never change (s209 pins it).
WORDLIST = tuple((
    'able acid aged also area army away baby back ball band bank base bath bear beat bell belt best bird blue boat '
    'body bone book born both bowl brave bread brick bring brown build burn busy cake calm camp card care cart case '
    'cash cast cell chair chalk chart chef chin city clay clean clock cloud coal coat code coin cold cook cool copy '
    'corn cost crew crop crow cube cup dance dark dawn deal deep deer desk dial dish dock door dove draw dream '
    'dress drum duck dust each early east echo edge egg eight else empty end even exit face fair fall farm fast '
    'fern field film fire fish five flag flat fly foam fog food foot fork form fox free frog fruit fuel game gate '
    'gift girl glad glass goat gold good grain grass gray green grid grow gulf hair half hall hand harp hat hawk '
    'heat herb hill hint home hook hope horn horse host hour house idea inch iron item jade jar jazz joke jump kept '
    'kettle key kind king kite knee knot lake lamp land lane last leaf left lemon lens life lift lime line lion '
    'list loaf lock long loop lucky lunch mango map maple march mask meal milk mint mist moon moss mouse music nail '
    'name nest net nine noon north note oak ocean olive open orange oven owl page paint palm paper park path peach '
    'pearl pen pine pink plum pond pool port quiet rain ranch reed rice ridge ring river road robin rock roof rope '
    'rose '
).split())
assert len(WORDLIST) == 256 and len(set(WORDLIST)) == 256, len(WORDLIST)


class BackupLocked(Exception):
    """None of the keys offered opens this backup."""


class BackupDamaged(Exception):
    """The backup was altered or is damaged: its seal does not check out (B1)."""


# ── the computer's vault (B2's first key). Tests swap VAULT for a stand-in; nothing reaches the real vault then ──
class KeyringVault:
    def get(self):
        from core import bank_vault
        if not bank_vault.available():
            return None
        try:
            import keyring
            v = keyring.get_password(bank_vault.SERVICE, VAULT_USER)
            return base64.b64decode(v) if v else None
        except Exception:
            return None

    def put(self, key):
        from core import bank_vault
        if not bank_vault.available():
            return False
        import keyring
        keyring.set_password(bank_vault.SERVICE, VAULT_USER, base64.b64encode(key).decode())
        return True

    def available(self):
        from core import bank_vault
        return bank_vault.available()


VAULT = KeyringVault()


class MemoryVault:
    """A stand-in vault for tests, so nothing they do reaches the real operating-system vault."""
    def __init__(self, key=None):
        self.key = key

    def get(self):
        return self.key

    def put(self, key):
        self.key = key
        return True

    def available(self):
        return True


def test_protect(client, headers, password='s-test password 1'):
    """For a test that makes backups: a stand-in vault, and protection set up and confirmed on it. Returns the vault
    it replaced, for the test to put back with test_unprotect()."""
    import json as _j
    from core.database import AppSetting, db_session
    old = globals()['VAULT']
    globals()['VAULT'] = MemoryVault()
    with db_session() as s:
        s.query(AppSetting).filter_by(key=SETTING).delete()
        s.commit()
    client.post('/api/backup/protect/setup', headers=headers, data=_j.dumps({'password': password}))
    client.post('/api/backup/protect/confirm', headers=headers, data='{}')
    return old


def test_unprotect(old):
    from core.database import AppSetting, db_session
    globals()['VAULT'] = old
    with db_session() as s:
        s.query(AppSetting).filter_by(key=SETTING).delete()
        s.commit()


def _b64(b):
    return base64.b64encode(b).decode()


def _unb64(s):
    return base64.b64decode(s.encode())


def key_id(key):
    return hashlib.sha256(b'gw-backup-key-id' + key).hexdigest()[:16]


def _seal(key, data, aad=b''):
    n = os.urandom(12)
    return n + AESGCM(key).encrypt(n, data, aad)


def _open(key, blob, aad=b''):
    return AESGCM(key).decrypt(blob[:12], blob[12:], aad)


def _pw_kek(password, salt, params=SCRYPT):
    return Scrypt(salt=salt, length=32, n=params['n'], r=params['r'], p=params['p']).derive(password.encode('utf-8'))


def _rec_kek(words, salt):
    raw = words_to_bytes(words)
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=b'gw-backup-recovery').derive(raw)


def new_recovery_words():
    return [WORDLIST[b] for b in secrets.token_bytes(WORDS)]


def words_to_bytes(words):
    ws = [w.strip().lower() for w in (words if isinstance(words, (list, tuple)) else str(words).split())]
    ws = [w for w in ws if w]
    if len(ws) != WORDS or any(w not in WORDLIST for w in ws):
        raise BackupLocked('The recovery key is 24 words from Groundwork\'s list.')
    return bytes(WORDLIST.index(w) for w in ws)


def wrap(key, password, words):
    """The two wrapped copies of the backup key that every backup header carries, plus what opens them."""
    salt, rsalt = os.urandom(16), os.urandom(16)
    return {'key_id': key_id(key), 'kdf': dict(SCRYPT, salt=_b64(salt)), 'pw': _b64(_seal(_pw_kek(password, salt), key)),
            'rec_salt': _b64(rsalt), 'rec': _b64(_seal(_rec_kek(words, rsalt), key))}


def rewrap_password(prot, key, password):
    salt = os.urandom(16)
    return dict(prot, kdf=dict(SCRYPT, salt=_b64(salt)), pw=_b64(_seal(_pw_kek(password, salt), key)))


def rewrap_recovery(prot, key, words):
    rsalt = os.urandom(16)
    return dict(prot, rec_salt=_b64(rsalt), rec=_b64(_seal(_rec_kek(words, rsalt), key)))


def unwrap(header, password=None, words=None, vault_key=None):
    """The backup key, by the first of the three that opens it: this computer's vault, the password, the words."""
    if vault_key is not None and key_id(vault_key) == header.get('key_id'):
        return vault_key, 'this computer'
    if password:
        k = header['kdf']
        try:
            return _open(_pw_kek(password, _unb64(k['salt']), k), _unb64(header['pw'])), 'password'
        except InvalidTag:
            pass
    if words:
        try:
            return _open(_rec_kek(words, _unb64(header['rec_salt'])), _unb64(header['rec'])), 'recovery key'
        except InvalidTag:
            pass
    raise BackupLocked('That password or recovery key does not open this backup.' if (password or words)
                       else 'This backup was made on another computer: enter its backup password or recovery key.')


def encrypt_db(db_bytes, key, prot):
    header = json.dumps({'v': 1, 'made': datetime.now().isoformat(timespec='seconds'), 'key_id': prot['key_id'],
                         'kdf': prot['kdf'], 'pw': prot['pw'], 'rec_salt': prot['rec_salt'], 'rec': prot['rec']},
                        separators=(',', ':')).encode()
    return MAGIC + struct.pack('>I', len(header)) + header + _seal(key, db_bytes, MAGIC + header)


def is_encrypted(blob_or_head):
    return bytes(blob_or_head[:len(MAGIC)]) == MAGIC


def read_header(blob):
    if not is_encrypted(blob):
        raise BackupDamaged('Not a Groundwork encrypted backup.')
    (n,) = struct.unpack('>I', blob[len(MAGIC):len(MAGIC) + 4])
    raw = blob[len(MAGIC) + 4:len(MAGIC) + 4 + n]
    return json.loads(raw), raw, len(MAGIC) + 4 + n


def decrypt(blob, password=None, words=None, vault_key=None):
    """(the database bytes, which key opened it). BackupLocked when no key fits; BackupDamaged when the seal fails."""
    header, raw, at = read_header(blob)
    key, how = unwrap(header, password, words, vault_key)
    try:
        data = _open(key, blob[at:], MAGIC + raw)
    except InvalidTag:
        raise BackupDamaged('This backup has been changed or damaged since it was made, so it will not be restored.')
    if not data.startswith(b'SQLite format 3'):
        raise BackupDamaged('This backup opens, but what is inside is not a Groundwork database.')
    return data, how
