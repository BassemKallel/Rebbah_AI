"""
views.py — Layer 4: HTTP Entry Point (thin orchestrator)

This file only:
1. Parses the incoming HTTP request
2. Delegates to MessagePipeline for all processing
3. Returns the HTTP response

All business logic lives in pipeline.py, disambiguation.py, and dialog_manager.py.
"""
import logging
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from apps.crm.models import Company
from .pipeline import MessagePipeline
from .services import messenger_service

logger = logging.getLogger(__name__)

pipeline = MessagePipeline()

# Webhook verify token (set META_VERIFY_TOKEN in settings.py or .env)
META_VERIFY_TOKEN = getattr(settings, "META_VERIFY_TOKEN", "tiktak_verify_token")


def resolve_page_to_company(page_id):
    """
    Dynamically resolves a Meta page_id to a Company object.
    Configured via Django Admin → Companies.
    Returns the Company instance, or None if not found.
    """
    try:
        return Company.objects.get(meta_page_id=page_id, is_active=True)
    except Company.DoesNotExist:
        return None


class MetaWebhookView(APIView):
    """
    Real Meta Webhook for Messenger and Instagram.

    GET  → Webhook verification (hub.mode, hub.verify_token, hub.challenge)
    POST → Receives messages in the official Meta format
    """
    permission_classes = [AllowAny]

    # ── GET: Webhook Verification ─────────────────────────────────────────
    def get(self, request):
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode == "subscribe" and token == META_VERIFY_TOKEN:
            logger.info("[META WEBHOOK] Verification successful")
            return HttpResponse(challenge, content_type="text/plain")

        logger.warning("[META WEBHOOK] Verification failed — bad token")
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    # ── POST: Receive Messages ────────────────────────────────────────────
    def post(self, request):
        data = request.data
        object_type = data.get("object")  # "page" (Messenger) or "instagram"

        if object_type not in ("page", "instagram"):
            return Response({"error": "Unsupported object type"}, status=status.HTTP_400_BAD_REQUEST)

        platform = "messenger" if object_type == "page" else "instagram"
        responses = []

        for entry in data.get("entry", []):
            page_id = entry.get("id", "")

            # Resolve Company dynamically from DB
            company = resolve_page_to_company(page_id)
            if not company:
                logger.warning(f"[META WEBHOOK] No company mapped for page_id={page_id}, skipping")
                continue

            shop_id = company.shop_id

            for messaging_event in entry.get("messaging", []):
                sender_psid = messaging_event.get("sender", {}).get("id", "")
                message_obj = messaging_event.get("message", {})

                if not sender_psid or not message_obj:
                    continue

                user_id = sender_psid   # PSID brut — ex: "7341829462837401"
                text = message_obj.get("text", "")

                # Extract image URL from attachments
                image_url = None
                for attach in message_obj.get("attachments", []):
                    if attach.get("type") == "image":
                        image_url = attach.get("payload", {}).get("url")
                        break

                # ── Delegate to pipeline ───────────────────────────────
                result = pipeline.run(user_id, shop_id, text, image_url=image_url)
                result["platform"] = platform
                result["sender_psid"] = sender_psid

                # ── Retrieve & persist sender name ─────────────────────
                token = company.meta_page_access_token
                if token and sender_psid:
                    sender_name = messenger_service.get_sender_name(sender_psid, token)
                    if sender_name:
                        from apps.crm.models import Lead
                        Lead.objects.filter(platform_id=user_id).update(name=sender_name)
                        logger.info(f"[META WEBHOOK] Lead name updated: '{sender_name}' for {user_id}")

                # ── Send bot reply back to Messenger ───────────────────
                bot_text = result.get("text", "")
                if bot_text and token:
                    messenger_service.send_message(sender_psid, bot_text, token)

                # Image produit désactivée — l'utilisateur a déjà envoyé l'image
                # matched_image = result.get("matched_image_url")
                # if matched_image and token:
                #     messenger_service.send_image(sender_psid, matched_image, token)

                responses.append(result)

        return Response({"status": "ok", "responses": responses})


class MessengerWebhookPOC(APIView):
    """
    POC endpoint for testing via Postman / curl.
    Accepts a simplified JSON payload.
    """

    def post(self, request):
        # ── 1. Parse Input ────────────────────────────────────────────────
        user_id = request.data.get("user_id")
        shop_id = request.data.get("shop_id")

        if not user_id or not shop_id:
            return Response(
                {"error": "user_id and shop_id are strictly required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate that the shop_id exists in the Company table
        if not Company.objects.filter(shop_id=shop_id, is_active=True).exists():
            return Response(
                {"error": f"shop_id '{shop_id}' does not exist or is inactive."},
                status=status.HTTP_404_NOT_FOUND
            )

        message_data = request.data.get("message", {})
        if isinstance(message_data, str):
            import json as _json
            try:
                message_data = _json.loads(message_data)
            except Exception:
                message_data = {}

        text = message_data.get("text", "") or request.data.get("text", "")
        image_url = message_data.get("image_url") or request.data.get("image_url")
        image_file = request.FILES.get("image")

        # ── 2. Delegate to pipeline ───────────────────────────────────────
        result = pipeline.run(
            user_id, shop_id, text,
            image_url=image_url,
            image_file=image_file,
        )

        # ── 3. Build HTTP Response ────────────────────────────────────────
        payload = {
            "status": "success",
            "bot_response": {
                "text": result["text"],
                "internal_debug": {
                    "intent_detected":    result.get("intent"),
                    "entities_extracted":  result.get("entities", {}),
                    "accumulated_context": result.get("context", {}),
                    "new_state":          result.get("state"),
                    "missing_entities":   result.get("missing_entities", []),
                },
            },
        }
        if result.get("matched_image_url"):
            payload["bot_response"]["identified_image_url"] = result["matched_image_url"]
        if result.get("uploaded_url"):
            payload["bot_response"]["uploaded_image_url"] = result["uploaded_url"]

        return Response(payload)
