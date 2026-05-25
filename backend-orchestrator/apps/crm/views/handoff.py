"""
apps/crm/views/handoff.py

Human Handoff API views.
Thin view layer — all business logic lives in services/handoff_service.py.

Routes:
  POST  conversations/<id>/takeover/       → Agent prend le relais
  POST  conversations/<id>/release/        → Remettre au bot
  POST  conversations/<id>/agent-reply/    → Agent envoie un message
  GET   conversations/<id>/handoff-status/ → Statut handoff
  PATCH bot-configurations/<shop_id>/toggle-bot/ → Toggle bot global
"""
import logging
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.crm.models import Conversation, Message, Company
from apps.crm.services.handoff_service import takeover, release, toggle_bot_global
from apps.gateway.services.messenger_service import send_message

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def takeover_conversation(request, conversation_id):
    """Agent takes over a specific conversation — bot stops responding."""
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if conversation.is_human_controlled:
        return Response({"detail": "Cette conversation est déjà sous contrôle humain."}, status=200)

    result = takeover(conversation, request.user)
    return Response({"status": "takeover", **result})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def release_conversation(request, conversation_id):
    """Release conversation back to the bot."""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    result = release(conversation)
    return Response({"status": "released", **result})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agent_reply(request, conversation_id):
    """
    Agent sends a message to the user.
    Saves to DB and delivers via Meta Messenger API.
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    text = request.data.get("text", "").strip()

    if not text:
        return Response({"detail": "Le message ne peut pas être vide."}, status=status.HTTP_400_BAD_REQUEST)

    if not conversation.is_human_controlled:
        return Response({"detail": "La conversation n'est pas en mode handoff humain."}, status=status.HTTP_400_BAD_REQUEST)

    # Save message in DB
    Message.objects.create(
        conversation=conversation,
        sender='BOT',
        text=text,
        is_human_agent=True,
        agent='HUMAN',
        conversation_state_before=conversation.state,
        conversation_state_after=conversation.state,
    )

    # Deliver via Meta Messenger API
    sent = False
    try:
        company = Company.objects.filter(shop_id=conversation.shop_id).first()
        if company and company.meta_page_access_token:
            psid = conversation.sender_id
            if psid and ':' in psid:
                psid = psid.split(':', 1)[1]
            sent = send_message(
                recipient_psid=psid,
                text=text,
                page_access_token=company.meta_page_access_token,
            )
        else:
            logger.warning(f"[HANDOFF] No Meta token for shop={conversation.shop_id} — message NOT sent via Meta")
    except Exception as exc:
        logger.error(f"[HANDOFF] agent_reply Meta send failed: {exc}")

    logger.info(f"[HANDOFF] Agent reply — conv={conversation_id} by={request.user.username} sent_via_meta={sent}")
    return Response({"status": "sent", "conversation_id": conversation_id, "sent_via_meta": sent})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def handoff_status(request, conversation_id):
    """Returns current handoff status of a conversation."""
    conv = get_object_or_404(Conversation, id=conversation_id)
    return Response({
        "conversation_id": conversation_id,
        "is_human_controlled": conv.is_human_controlled,
        "human_agent": conv.human_agent.username if conv.human_agent else None,
        "human_takeover_at": conv.human_takeover_at,
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def toggle_bot(request, shop_id):
    """
    Toggle the bot on/off globally for a shop.
    Body: { "bot_enabled": true|false }
    """
    enabled = request.data.get("bot_enabled")
    if enabled is None:
        return Response({"detail": "Champ 'bot_enabled' requis (true ou false)."}, status=status.HTTP_400_BAD_REQUEST)

    result = toggle_bot_global(shop_id, bool(enabled))
    logger.info(f"[HANDOFF] Bot toggle — shop={shop_id} bot_enabled={enabled} by user={request.user.username}")
    return Response(result)
