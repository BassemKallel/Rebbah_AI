"""
encrypt_existing_tokens.py — Management command to encrypt plaintext sensitive fields.

Run this ONCE after setting FIELD_ENCRYPTION_KEY to encrypt existing plaintext values.
Safe to run multiple times (already-encrypted values are skipped via try/except in decrypt_value).

Usage:
    python manage.py encrypt_existing_tokens
    python manage.py encrypt_existing_tokens --dry-run   # preview only
"""
import logging
from django.core.management.base import BaseCommand
from apps.crm.models import Company
from apps.crm.encryption import encrypt_value, decrypt_value, _get_fernet

logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = ['meta_page_access_token', 'gemini_api_key']


def is_already_encrypted(value: str) -> bool:
    """
    Heuristic: Fernet tokens start with 'gAAA' (base64 encoded structure).
    """
    if not value:
        return False
    return value.startswith('gAAA')


class Command(BaseCommand):
    help = "Encrypt existing plaintext sensitive fields in Company records using Fernet."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be encrypted without making changes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        fernet = _get_fernet()
        if fernet is None:
            self.stderr.write(self.style.ERROR(
                "❌ FIELD_ENCRYPTION_KEY is not set or invalid. "
                "Add it to .env before running this command."
            ))
            return

        companies = Company.objects.all()
        total = companies.count()
        self.stdout.write(f"🔍 Found {total} company records to check.\n")

        encrypted_count = 0
        skipped_count = 0

        for company in companies:
            updated = False
            for field in SENSITIVE_FIELDS:
                raw_value = company.__dict__.get(field)  # bypass EncryptedTextField decryption
                if not raw_value:
                    continue

                if is_already_encrypted(raw_value):
                    self.stdout.write(
                        f"   ↳ [{company.shop_id}] {field}: already encrypted — skipped"
                    )
                    skipped_count += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"   [DRY RUN] [{company.shop_id}] {field}: "
                            f"would encrypt '{raw_value[:20]}...'"
                        )
                    )
                else:
                    encrypted = encrypt_value(raw_value)
                    # Write directly to DB to bypass get_prep_value double-encryption
                    Company.objects.filter(pk=company.pk).update(**{field: encrypted})
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"   ✅ [{company.shop_id}] {field}: encrypted successfully"
                        )
                    )
                    encrypted_count += 1
                    updated = True

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete — no changes made."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"✅ Done: {encrypted_count} fields encrypted, {skipped_count} already encrypted."
            ))
