"""
cron_jobs.py — Background job functions for Rebbah AI

These are plain Python functions/classes called by Django management commands.
No external scheduler dependency needed.

Usage (called by management commands):
  python manage.py expire_conversations
  python manage.py retry_pending_messages
"""
import logging
from django.utils import timezone
from apps.crm.models import Conversation, PendingMessage

logger = logging.getLogger(__name__)

GRACE_PERIOD_MINUTES = 10


def expire_conversations():
    """
    Transitions AWAITING_CORRECTION conversations to COMPLETED
    when the grace period (10 min) has elapsed.
    """
    now = timezone.now()
    expired = Conversation.objects.filter(
        state="AWAITING_CORRECTION",
        completed_at__isnull=False,
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
                    f"[CRON] Conversation {conv.id} (lead={conv.sender_id}) "
                    f"expired after {elapsed:.1f}min → COMPLETED"
                )
        except Exception as e:
            logger.error(f"[CRON] Error processing conversation {conv.id}: {e}")

    logger.info(f"[CRON] ExpireConversations: {count} conversation(s) expired.")
    return count


def retry_pending_messages():
    """
    Retry queue consumer.

    For each PendingMessage whose next_retry_at has passed:
      - Re-calls the LLM with the original user message.
      - On success: sends the response to the client via Messenger API
        and deletes the PendingMessage from the queue.
      - On failure: reschedules (retry_count += 1, next_retry_at += 60s).
      - After MAX_RETRIES failures: escalates to human handoff.
    """
    from apps.crm.models import Company
    from apps.gateway.services.agents import run_orchestrator
    from apps.gateway.services.context_manager import ContextManager

    now = timezone.now()
    pending = PendingMessage.objects.filter(next_retry_at__lte=now).select_related('conversation')
    context_manager = ContextManager()
    processed = 0

    logger.info(f"[RETRY CRON] Processing {pending.count()} pending message(s).")

    for msg in pending:
        try:
            company = Company.objects.get(shop_id=msg.shop_id)
        except Company.DoesNotExist:
            logger.error(f"[RETRY CRON] Company not found for shop_id={msg.shop_id}. Deleting orphan.")
            msg.delete()
            continue

        try:
            history = context_manager.get_recent_context(
                msg.sender_id, n=8, shop_id=msg.shop_id
            )
            if not msg.conversation:
                logger.error(f"[RETRY CRON] PendingMessage {msg.id} has no associated conversation. Deleting.")
                msg.delete()
                continue

            llm_result = run_orchestrator(
                user_message=msg.user_text,
                image_url=msg.image_url or None,
                conversation=msg.conversation,
                company=company,
                history=history,
            )

            if llm_result.get('error'):
                raise RuntimeError(f"LLM error: {llm_result.get('error_type')}")

            # ── Success: send response to client ──────────────────────────
            bot_text = llm_result['response_text']
            _send_to_messenger(msg.shop_id, msg.sender_id, bot_text)
            context_manager.add_message(
                msg.sender_id, role='bot', text=bot_text, shop_id=msg.shop_id
            )
            logger.info(
                f"[RETRY CRON] ✅ Message retried successfully — "
                f"sender={msg.sender_id} shop={msg.shop_id}"
            )
            msg.delete()
            processed += 1

        except Exception as e:
            logger.warning(
                f"[RETRY CRON] ❌ Retry failed for sender={msg.sender_id} "
                f"shop={msg.shop_id} attempt={msg.retry_count + 1}: {e}"
            )

            if msg.is_expired:
                # ── Max retries reached: human handoff ────────────────────
                if msg.conversation:
                    msg.conversation.is_human_controlled = True
                    msg.conversation.save(update_fields=['is_human_controlled'])
                logger.warning(
                    f"[RETRY CRON] Human handoff triggered after max retries — "
                    f"sender={msg.sender_id} shop={msg.shop_id}"
                )
                try:
                    _send_to_messenger(
                        msg.shop_id, msg.sender_id,
                        "Notre système rencontre des difficultés techniques. "
                        "Je vous mets en relation avec un conseiller humain. "
                        "Merci pour votre patience ! 🙏"
                    )
                except Exception:
                    pass
                msg.delete()
            else:
                msg.schedule_next_retry(delay_seconds=60)

    return processed


def _send_to_messenger(shop_id: str, sender_id: str, text: str):
    """
    Send a message to the client via the Facebook Messenger Send API.
    Uses the page_access_token stored on the Company object.
    """
    import requests
    from apps.crm.models import Company

    company = Company.objects.get(shop_id=shop_id)
    token = (
        getattr(company, 'page_access_token', None)
        or getattr(company, 'facebook_token', None)
        or getattr(company, 'meta_page_access_token', None)
    )
    if not token:
        logger.warning(f"[RETRY CRON] No Messenger token for shop={shop_id}. Cannot send.")
        return

    resp = requests.post(
        "https://graph.facebook.com/v19.0/me/messages",
        params={"access_token": token},
        json={
            "recipient": {"id": sender_id},
            "message": {"text": text},
        },
        timeout=10,
    )
    resp.raise_for_status()
    logger.info(f"[RETRY CRON] Message sent to {sender_id} via Messenger.")
