"""
cron_jobs.py — django-cron tasks for TikTak AI

Registered in settings.CRON_CLASSES.
Run via: python manage.py runcrons
"""
import logging
from django_cron import CronJobBase, Schedule
from django.utils import timezone
from apps.crm.models import Conversation

logger = logging.getLogger(__name__)

GRACE_PERIOD_MINUTES = 10


class ExpireConversationsCronJob(CronJobBase):
    """
    Transitions AWAITING_CORRECTION conversations to COMPLETED
    when the grace period (10 min) has elapsed.
    Runs every minute.
    """
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = "apps.crm.cron_jobs.ExpireConversationsCronJob"

    def do(self):
        now = timezone.now()
        expired = Conversation.objects.filter(
            state="AWAITING_CORRECTION",
            completed_at__isnull=False,
        )
        count = 0
        for conv in expired:
            try:
                if conv.completed_at is None:
                    continue
                elapsed = (now - conv.completed_at).total_seconds() / 60
                if elapsed > GRACE_PERIOD_MINUTES:
                    conv.state = "COMPLETED"
                    conv.save(update_fields=["state"])
                    count += 1
                    logger.info(
                        f"[CRON] Conversation {conv.id} (lead={conv.sender_id}) "
                        f"expired after {elapsed:.1f}min → COMPLETED"
                    )
            except Exception as e:
                logger.error(f"[CRON] Error processing conversation {conv.id}: {e}")

        logger.info(f"[CRON] ExpireConversations: {count} conversation(s) expired.")
