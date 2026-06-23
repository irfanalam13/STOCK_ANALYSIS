"""Field-level symmetric encryption (AES via Fernet).

For sensitive-but-recoverable data (API keys, external credentials, optional
financial fields) — *not* passwords, which are one-way hashed in
``core.security``. The key comes from ``DATA_ENCRYPTION_KEY`` if set, otherwise
it is deterministically derived from ``SECRET_KEY`` so the feature works out of
the box in dev while supporting a dedicated, rotatable key in production.
"""
import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from core.config import settings


@lru_cache
def _fernet() -> Fernet:
    if settings.DATA_ENCRYPTION_KEY:
        key = settings.DATA_ENCRYPTION_KEY.encode()
    else:
        # Derive a valid 32-byte url-safe base64 key from the app secret.
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Encrypt a string, returning a url-safe ciphertext token."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt`. Raises ``ValueError`` if
    the token is invalid or was produced with a different key."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("invalid or tampered ciphertext") from exc


def mask(value: str, visible: int = 4) -> str:
    """Mask a secret for display/logging, keeping the last ``visible`` chars."""
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * (len(value) - visible) + value[-visible:]
