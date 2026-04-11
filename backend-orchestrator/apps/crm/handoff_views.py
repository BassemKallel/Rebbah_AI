"""
handoff_views.py — Human Handoff API Endpoints

Routes:
  POST   /api/v1/crm/conversations/{id}/takeover/     → Agent prend le relais
  POST   /api/v1/crm/conversations/{id}/release/      → Remettre au bot
  POST   /api/v1/crm/conversations/{id}/agent-reply/  → Agent envoie un message
  GET    /api/v1/crm/conversations/{id}/handoff-status/ → Statut handoff
  PATCH  /api/v1/crm/bot-configurations/toggle-bot/  → Toggle bot on/off (global)
"""
import logging
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.crm.models import Conversation, Message, BotConfiguration, Company
from apps.gateway.services.messenger_service import send_message

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def takeover_conversation(request, conversation_id):
    """
    Agent takes over a specific conversation.
    The bot stops responding to this conversation.
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if conversation.is_human_controlled:
        return Response(
            {"detail": "Cette conversation est déjà sous contrôle humain."},
            status=status.HTTP_200_OK
        )

    conversation.is_human_controlled = True
    conversation.human_takeover_at = timezone.now()
    conversation.human_agent = request.user
    conversation.save(update_fields=['is_human_controlled', 'human_takeover_at', 'human_agent'])

    logger.info(
        f"[HANDOFF] Takeover — conv={conversation_id} by user={request.user.username}"
    )
    return Response({
        "status": "takeover",
        "conversation_id": conversation_id,
        "human_agent": request.user.username,
        "taken_at": conversation.human_takeover_at,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def release_conversation(request, conversation_id):
    """
    Release a conversation back to the bot.
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)

    conversation.is_human_controlled = False
    conversation.human_takeover_at = None
    conversation.human_agent = None
    conversation.save(update_fields=['is_human_controlled', 'human_takeover_at', 'human_agent'])

    logger.info(
        f"[HANDOFF] Released — conv={conversation_id} by user={request.user.username}"
    )
    return Response({
        "status": "released",
        "conversation_id": conversation_id,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agent_reply(request, conversation_id):
    """
    Agent sends a message to the user (via Meta Messenger API).
    Saves the message in DB and sends it via Meta Send API.
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    text = request.data.get("text", "").strip()

    if not text:
        return Response(
            {"detail": "Le message ne peut pas être vide."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not conversation.is_human_controlled:
        return Response(
            {"detail": "La conversation n'est pas en mode handoff humain."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 1. Save message in DB (sender=BOT, but flagged as human agent)
    Message.objects.create(
        conversation=conversation,
        sender='BOT',
        text=text,
        is_human_agent=True,
        conversation_state_before=conversation.state,
        conversation_state_after=conversation.state,
    )

    # 2. Send via Meta Messenger API
    sent = False
    try:
        company = Company.objects.filter(shop_id=conversation.shop_id).first()
        if company and company.meta_page_access_token:
            psid = conversation.sender_id
            # Extract raw PSID if prefixed (e.g. "messenger:123456" → "123456")
            if psid and ':' in psid:
                psid = psid.split(':', 1)[1]
            sent = send_message(
                recipient_psid=psid,
                text=text,
                page_access_token=company.meta_page_access_token,
            )
        else:
            logger.warning(
                f"[HANDOFF] No Meta token for shop={conversation.shop_id} — message saved but not sent via Meta"
            )
    except Exception as exc:
        logger.error(f"[HANDOFF] agent_reply Meta send failed: {exc}")

    logger.info(
        f"[HANDOFF] Agent reply — conv={conversation_id} "
        f"by={request.user.username} sent_via_meta={sent}"
    )
    return Response({
        "status": "sent",
        "conversation_id": conversation_id,
        "sent_via_meta": sent,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def handoff_status(request, conversation_id):
    """
    Returns current handoff status of a conversation.
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    return Response({
        "conversation_id": conversation_id,
        "is_human_controlled": conversation.is_human_controlled,
        "human_agent": conversation.human_agent.username if conversation.human_agent else None,
        "human_takeover_at": conversation.human_takeover_at,
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def toggle_bot(request, shop_id):
    """
    Toggle the bot on/off globally for a shop.
    Body: { "bot_enabled": true|false }

    When bot is re-enabled (True):
      - All conversations with is_human_controlled=True are released back to the bot.
    """
    # get_or_create: in case BotConfiguration does not exist yet
    bot_config, _ = BotConfiguration.objects.get_or_create(
        shop_id=shop_id,
        defaults={'bot_enabled': True}
    )
    enabled = request.data.get("bot_enabled")

    if enabled is None:
        return Response(
            {"detail": "Champ 'bot_enabled' requis (true ou false)."},
            status=status.HTTP_400_BAD_REQUEST
        )

    enabled = bool(enabled)
    bot_config.bot_enabled = enabled
    bot_config.bot_disabled_at = None if enabled else timezone.now()
    bot_config.save(update_fields=['bot_enabled', 'bot_disabled_at'])

    released_count = 0
    if enabled:
        # Re-enabling bot — release ALL human-controlled conversations for this shop
        released_count = Conversation.objects.filter(
            shop_id=shop_id,
            is_human_controlled=True
        ).update(
            is_human_controlled=False,
            human_takeover_at=None,
            human_agent=None,
        )
        logger.info(
            f"[HANDOFF] Bot re-enabled for shop={shop_id} — released {released_count} conversations"
        )

    logger.info(
        f"[HANDOFF] Bot toggle — shop={shop_id} bot_enabled={enabled} "
        f"by user={request.user.username}"
    )
    return Response({
        "shop_id": shop_id,
        "bot_enabled": bot_config.bot_enabled,
        "bot_disabled_at": bot_config.bot_disabled_at,
        "conversations_released": released_count,
    })
