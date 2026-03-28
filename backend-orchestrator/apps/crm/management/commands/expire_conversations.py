"""
expire_conversations.py — Django management command

Transitions AWAITING_CORRECTION conversations to COMPLETED
when the grace period has expired.

Usage:
    python manage.py expire_conversations

Schedule via docker-compose command loop or system cron every minute.
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.crm.models import Conversation

logger = logging.getLogger(__name__)

GRACE_PERIOD_MINUTES = 10


class Command(BaseCommand):
    help = "Expire AWAITING_CORRECTION conversations older than the grace period"

    def handle(self, *args, **options):
        now = timezone.now()
        expired = Conversation.objects.filter(
            state="AWAITING_CORRECTION",
        )

        count = 0
        for conv in expired:
            try:
                # Use completed_at if set, otherwise fall back to updated_at
                # (covers old conversations created before completed_at was populated)
                reference_time = conv.completed_at or conv.updated_at
                elapsed = (now - reference_time).total_seconds() / 60
                if elapsed > GRACE_PERIOD_MINUTES:
                    conv.state = "COMPLETED"
                    conv.save(update_fields=["state"])
                    count += 1
                    logger.info(
                        f"[EXPIRE] Conversation {conv.id} (lead={conv.sender_id}) "
                        f"expired after {elapsed:.1f}min → COMPLETED"
                    )
            except Exception as e:
                logger.error(f"[EXPIRE] Error processing conversation {conv.id}: {e}")

        self.stdout.write(
            self.style.SUCCESS(f"Expired {count} conversation(s).")
        )
