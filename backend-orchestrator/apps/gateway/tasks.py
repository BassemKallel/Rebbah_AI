"""
apps/gateway/tasks.py — Celery Async Task Layer

This module deports all long-running, I/O-heavy work (debouncing sleep,
Gemini/ADK pipeline call, and Meta Messenger reply dispatch) from the
Django request thread into a background Celery worker.

Design principles:
  - One task per incoming Messenger/Instagram message event.
  - The HTTP webhook thread (views.py) does nothing except push to Redis
    and fire this task — it returns HTTP 200 to Meta in under 20ms.
  - The debounce sliding window (5.0s), pipeline run, and Meta send_message
    are ALL executed here, in the worker process.
"""
import logging
import time
from typing import Optional

from celery import shared_task

from apps.gateway.services.pipeline import MessagePipeline, context_manager
from apps.gateway.services import messenger_service

logger = logging.getLogger(__name__)
DEBOUNCE_WINDOW_SECONDS = 5.0

# Module-level singleton — reused across task invocations in the same worker process.
_pipeline = MessagePipeline()


def _resolve_sender_name(sender_psid: str, page_token: Optional[str]) -> Optional[str]:
    """
    Resolve the sender display name from the Messenger/Instagram PSID.
    """
    if not sender_psid or not page_token:
        return None
    return messenger_service.get_sender_name(sender_psid, page_token)


@shared_task(
    name="apps.gateway.tasks.process_webhook_message_async",
    bind=True,
    max_retries=0,
    ignore_result=False,
)
def process_webhook_message_async(
    self,
    user_id: str,
    shop_id: str,
    text: str,
    image_url: Optional[str],
    current_timestamp: float,
    platform: str,
    page_token: Optional[str],
    sender_psid: str,
) -> str:
    """
    Background Celery task that handles the full message processing lifecycle:

    1. Debounce sleep (5.0 seconds)
    2. Sliding window check — abort if a newer message arrived during the sleep
    3. Coalesce all buffered messages from Redis into one consolidated payload
    4. Run the full AI pipeline (routing → agent ADK → Gemini → entity extraction)
    5. Dispatch the bot reply back to Meta Messenger / Instagram via the Graph API

    Args:
        user_id:           Messenger / Instagram PSID of the client.
        shop_id:           Slug of the active shop (multi-tenant isolation).
        text:              Raw text of the incoming message.
        image_url:         Optional public image URL (attachments).
        current_timestamp: Unix timestamp at which this message was registered.
        platform:          "messenger" | "instagram" | "poc"
        page_token:        Meta Page Access Token for send_message calls.
        sender_psid:       Raw PSID used to address Meta API replies.
    Returns:
        Status string: "success" | "queued_and_skipped" | "error_..."
    """
    from django.db import connections
    # Ensure the worker thread gets a fresh DB connection (no leaked sockets)
    connections.close_all()

    # ── 1. Debounce sleep (5.0 s) ────────────────────────────────────────────
    time.sleep(DEBOUNCE_WINDOW_SECONDS)

    # ── 2. Sliding window check ───────────────────────────────────────────────
    latest_timestamp = context_manager.get_debounce_last_time(user_id, shop_id)
    if latest_timestamp and latest_timestamp > current_timestamp:
        logger.info(
            f"[CELERY] Newer message detected for user_id={user_id} shop_id={shop_id}. "
            f"Skipping this task (queued_and_skipped)."
        )
        return "queued_and_skipped"

    # ── 3. Retrieve & clear consolidated message buffer ───────────────────────
    consolidated_text, consolidated_image_url = context_manager.get_and_clear_debounce_buffer(
        user_id, shop_id
    )
    logger.info(
        f"[CELERY] Processing coalesced message for user_id={user_id}: '{consolidated_text}'"
    )

    # ── 4. Run the AI pipeline ────────────────────────────────────────────────
    sender_name = _resolve_sender_name(sender_psid, page_token)

    try:
        result = _pipeline.run(
            user_id=user_id,
            shop_id=shop_id,
            text=consolidated_text,
            image_url=consolidated_image_url,
            platform=platform,
            sender_name=sender_name,
        )
    except Exception as exc:
        logger.error(f"[CELERY] Pipeline error for user_id={user_id}: {exc}", exc_info=True)
        return f"pipeline_error: {str(exc)}"

    # ── 5. Dispatch bot reply to Meta Messenger / Instagram ───────────────────
    if not page_token:
        logger.warning(
            f"[CELERY] No page token available for shop_id={shop_id}. "
            "Skipping Meta send_message (reply stored in DB only)."
        )
        return "success_no_token"

    try:
        carousel_elements = result.get("carousel_elements")
        if carousel_elements:
            messenger_service.send_carousel(sender_psid, carousel_elements, page_token)

        bot_text = result.get("text", "")
        if bot_text:
            messenger_service.send_message(sender_psid, bot_text, page_token)

    except Exception as exc:
        logger.error(
            f"[CELERY] Meta send_message error for sender_psid={sender_psid}: {exc}",
            exc_info=True,
        )
        return f"send_error: {str(exc)}"

    logger.info(f"[CELERY] Task completed successfully for user_id={user_id}.")
    return "success"
