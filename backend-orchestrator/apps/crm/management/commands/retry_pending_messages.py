"""
retry_pending_messages.py — Management command to process the retry queue.

Called by the Docker crontab every minute:
  python manage.py retry_pending_messages

This command re-processes PendingMessage entries that failed due to temporary
Gemini API errors (429 / 503), and sends the response to the client via
the Facebook Messenger Send API.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Retry pending messages that failed due to Gemini API errors.'

    def handle(self, *args, **options):
        from apps.crm.cron_jobs import retry_pending_messages
        processed = retry_pending_messages()
        self.stdout.write(
            self.style.SUCCESS(f'[retry_pending_messages] {processed} message(s) retried successfully.')
        )
