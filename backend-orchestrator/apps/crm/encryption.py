"""
encryption.py — Symmetric encryption for sensitive fields (API keys, tokens).

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` library.
The encryption key is read from settings.FIELD_ENCRYPTION_KEY.

Usage in models:
    from apps.crm.encryption import EncryptedTextField
    class MyModel(models.Model):
        secret = EncryptedTextField(blank=True, null=True)

At runtime, Django transparently encrypts on write and decrypts on read.
Application code never sees ciphertext.
"""
import logging
from django.conf import settings
from django.db import models
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the project-wide encryption key."""
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', '')
    if not key:
        raise ValueError(
            "FIELD_ENCRYPTION_KEY is not set in settings. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode('utf-8')).decode('utf-8')


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt a ciphertext string. Returns plaintext.
    If the value is not valid Fernet ciphertext (e.g. legacy unencrypted data),
    returns it as-is to allow graceful migration.
    """
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except (InvalidToken, Exception) as exc:
        # Value is probably a legacy unencrypted token — return as-is
        logger.debug(f"[ENCRYPTION] Could not decrypt value (likely unencrypted legacy data): {exc}")
        return ciphertext


class EncryptedTextField(models.TextField):
    """
    A TextField that transparently encrypts data at rest.

    • get_prep_value()  → encrypts before INSERT/UPDATE
    • from_db_value()   → decrypts after SELECT
    • value_from_object() → returns decrypted value for serialization

    Application code always works with plaintext.
    """

    def get_prep_value(self, value):
        """Called before saving to DB — encrypt the plaintext."""
        value = super().get_prep_value(value)
        if value is None:
            return value
        return encrypt_value(str(value))

    def from_db_value(self, value, expression, connection):
        """Called after reading from DB — decrypt the ciphertext."""
        if value is None:
            return value
        return decrypt_value(str(value))

    def deconstruct(self):
        """Ensure Django migrations see this as a standard TextField."""
        name, path, args, kwargs = super().deconstruct()
        # Store as the custom field path so migrations reference the right class
        path = 'apps.crm.encryption.EncryptedTextField'
        return name, path, args, kwargs
