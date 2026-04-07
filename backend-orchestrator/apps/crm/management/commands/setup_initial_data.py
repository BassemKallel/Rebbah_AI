"""
setup_initial_data.py

Management command to auto-create:
  1. Django superuser (from env vars)
  2. Initial Company / Shop (from env vars)

Run automatically at startup via docker-compose, or manually:
    python manage.py setup_initial_data

Required env vars:
    DJANGO_SUPERUSER_USERNAME  (default: admin)
    DJANGO_SUPERUSER_EMAIL     (default: admin@tiktakpro.com)
    DJANGO_SUPERUSER_PASSWORD  (required for creation)
    SHOP_ID                    (required for Company creation)
    SHOP_NAME                  (default: TikTak Shop)
"""
import os
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create superuser and initial Company from environment variables"

    def handle(self, *args, **options):
        self._create_superuser()
        self._create_company()

    # ── Superuser ──────────────────────────────────────────────────────────────

    def _create_superuser(self):
        User = get_user_model()
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
        email    = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@tiktakpro.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "")

        if not password:
            self.stdout.write(self.style.WARNING(
                "[setup] DJANGO_SUPERUSER_PASSWORD not set — skipping superuser creation."
            ))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f"[setup] Superuser '{username}' already exists — skipped.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"[setup] Superuser '{username}' created."))

    # ── Company ────────────────────────────────────────────────────────────────

    def _create_company(self):
        from apps.crm.models import Company

        shop_id   = os.getenv("SHOP_ID", "")
        shop_name = os.getenv("SHOP_NAME", "TikTak Shop")

        if not shop_id:
            self.stdout.write(self.style.WARNING(
                "[setup] SHOP_ID not set — skipping Company creation."
            ))
            return

        company, created = Company.objects.get_or_create(
            shop_id=shop_id,
            defaults={
                "name":      shop_name,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                f"[setup] Company '{shop_name}' (shop_id={shop_id}) created."
            ))
        else:
            self.stdout.write(f"[setup] Company '{shop_id}' already exists — skipped.")
