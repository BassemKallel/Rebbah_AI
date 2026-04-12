"""
apps/crm/services/handoff_service.py

Business logic for human handoff operations.
Views should call these functions instead of containing logic directly.
"""
import logging
from django.utils import timezone
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def takeover(conversation, agent: User) -> dict:
    """
    Agent takes control of the conversation.
    Returns updated conversation data.
    """
    conversation.is_human_controlled = True
    conversation.human_takeover_at = timezone.now()
    conversation.human_agent = agent
    conversation.save(update_fields=['is_human_controlled', 'human_takeover_at', 'human_agent'])

    logger.info(f"[HANDOFF] Takeover — conv={conversation.id} agent={agent.username}")

    return {
        "conversation_id": conversation.id,
        "is_human_controlled": conversation.is_human_controlled,
        "human_takeover_at": conversation.human_takeover_at,
        "human_agent": agent.username,
    }


def release(conversation) -> dict:
    """
    Release conversation back to the bot.
    """
    conversation.is_human_controlled = False
    conversation.human_takeover_at = None
    conversation.human_agent = None
    conversation.save(update_fields=['is_human_controlled', 'human_takeover_at', 'human_agent'])

    logger.info(f"[HANDOFF] Release — conv={conversation.id}")

    return {
        "conversation_id": conversation.id,
        "is_human_controlled": False,
    }


def toggle_bot_global(shop_id: str, enable: bool) -> dict:
    """
    Enable or disable the bot for an entire shop.

    - enable=False : All conversations → is_human_controlled=True
    - enable=True  : All conversations → is_human_controlled=False (bot resumes)

    Returns a summary dict.
    """
    from apps.crm.models import BotConfiguration, Conversation

    bot_config, _ = BotConfiguration.objects.get_or_create(
        shop_id=shop_id,
        defaults={'bot_enabled': True}
    )

    bot_config.bot_enabled = enable
    bot_config.bot_disabled_at = None if enable else timezone.now()
    bot_config.save(update_fields=['bot_enabled', 'bot_disabled_at'])

    if enable:
        affected = Conversation.objects.filter(
            shop_id=shop_id, is_human_controlled=True
        ).update(
            is_human_controlled=False,
            human_takeover_at=None,
            human_agent=None,
        )
        logger.info(f"[HANDOFF] Bot RE-ENABLED shop={shop_id} — released {affected} conversations")
    else:
        affected = Conversation.objects.filter(
            shop_id=shop_id, is_human_controlled=False
        ).update(
            is_human_controlled=True,
            human_takeover_at=timezone.now(),
        )
        logger.info(f"[HANDOFF] Bot DISABLED shop={shop_id} — {affected} conversations set to human-controlled")

    return {
        "shop_id": shop_id,
        "bot_enabled": bot_config.bot_enabled,
        "bot_disabled_at": bot_config.bot_disabled_at,
        "conversations_affected": affected,
    }
