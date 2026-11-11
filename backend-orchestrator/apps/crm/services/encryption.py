"""
encryption.py — Fernet AES-128-CBC Field Encryption

EncryptedTextField transparently encrypts values before saving to DB
and decrypts them on read. Uses the FIELD_ENCRYPTION_KEY env variable.

If the key is missing, falls back to plain text (with a warning) to
avoid breaking the system during initial setup.
"""
import logging
from django.db import models
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_fernet():
    """Returns a Fernet instance or None if key is not configured."""
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
    if not key:
        logger.warning(
            "[ENCRYPTION] FIELD_ENCRYPTION_KEY not set — storing sensitive fields in plain text!"
        )
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        logger.error(f"[ENCRYPTION] Invalid FIELD_ENCRYPTION_KEY: {e}")
        return None


def encrypt_value(value: str) -> str:
    """Encrypt a string. Returns the value unchanged if key is missing."""
    if not value:
        return value
    fernet = _get_fernet()
    if fernet is None:
        return value
    try:
        return fernet.encrypt(value.encode()).decode()
    except Exception as e:
        logger.error(f"[ENCRYPTION] Encrypt error: {e}")
        return value


def decrypt_value(value: str) -> str:
    """Decrypt a string. Returns the value unchanged if not encrypted or key is missing."""
    if not value:
        return value
    fernet = _get_fernet()
    if fernet is None:
        logger.warning(f"[ENCRYPTION] No Fernet key - returning value as-is (length={len(value)})")
        return value
    try:
        decrypted = fernet.decrypt(value.encode()).decode()
        logger.debug(f"[ENCRYPTION] Successfully decrypted value (length={len(value)} -> {len(decrypted)})")
        return decrypted
    except Exception as e:
        # Value is not encrypted (plain text) — return as-is (migration safety)
        logger.warning(f"[ENCRYPTION] Decrypt failed: {e} — returning value as-is (starts with: {value[:20]}...)")
        return value


class EncryptedTextField(models.TextField):
    """
    A TextField that automatically encrypts before saving and decrypts on read.
    Transparent to the rest of the application code.
    """

    def from_db_value(self, value, expression, connection):
        return decrypt_value(value)

    def to_python(self, value):
        return decrypt_value(value) if value else value

    def get_prep_value(self, value):
        """Called before saving to DB — encrypts the value."""
        raw = super().get_prep_value(value)
        return encrypt_value(raw) if raw else raw
