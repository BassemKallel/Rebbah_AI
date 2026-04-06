"""
encryption.py — Stub for migration compatibility.

EncryptedTextField was removed in favor of plain TextField storage.
This stub keeps the class definition so that existing migrations
(which reference 'apps.crm.encryption.EncryptedTextField') can still run.
"""
from django.db import models


class EncryptedTextField(models.TextField):
    """Legacy stub — behaves as a plain TextField."""
    pass
