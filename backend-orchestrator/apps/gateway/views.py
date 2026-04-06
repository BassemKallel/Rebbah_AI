"""
views.py — Layer 4: HTTP Entry Point (thin orchestrator)

This file only:
1. Parses the incoming HTTP request
2. Delegates to MessagePipeline for all processing
3. Returns the HTTP response

All business logic lives in pipeline.py, disambiguation.py, and dialog_manager.py.
"""
import hmac
import hashlib
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


def _verify_meta_signature(request) -> bool:
    """
    Vérifie la signature HMAC-SHA256 envoyée par Meta dans X-Hub-Signature-256.
    Retourne True si valide, ou si META_APP_SECRET n'est pas configuré (dégradé gracieux).
    """
    app_secret = getattr(settings, 'META_APP_SECRET', '')
    if not app_secret:
        logger.warning("[META WEBHOOK] META_APP_SECRET not set — skipping signature verification")
        return True

    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        logger.warning("[META WEBHOOK] Missing or malformed X-Hub-Signature-256")
        return False

    expected = "sha256=" + hmac.new(
        app_secret.encode("utf-8"),
        request.body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature_header, expected)


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
        if not _verify_meta_signature(request):
            return Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

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

                # ── Ignorer les messages envoyés par la page elle-même (admin) ──
                if sender_psid == page_id:
                    logger.info(f"[META WEBHOOK] Ignoring message from page itself (admin): {sender_psid}")
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
    POC endpoint for testing and internal integrations.
    Accepts a simplified JSON payload.

    Authentication: X-Shop-Token header (dashboard_token from Company model).
    The company is resolved from the token — shop_id in the body is optional.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # ── 0. Authenticate via X-Shop-Token ─────────────────────────────
        token = request.headers.get("X-Shop-Token")
        if not token:
            return Response(
                {"error": "Missing X-Shop-Token header."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        company = Company.objects.filter(dashboard_token=token, is_active=True).first()
        if not company:
            return Response(
                {"error": "Invalid or inactive shop token."},
                status=status.HTTP_403_FORBIDDEN
            )

        shop_id = company.shop_id

        # ── 1. Parse Input ────────────────────────────────────────────────
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"error": "user_id is required."},
                status=status.HTTP_400_BAD_REQUEST
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

        # Mode override optionnel : "nlu" ou "llm" (écrase company.response_mode pour cette requête)
        mode_override = request.data.get("mode")
        if mode_override not in ("nlu", "llm"):
            mode_override = None

        # ── 2. Delegate to pipeline ───────────────────────────────────────
        result = pipeline.run(
            user_id, shop_id, text,
            image_url=image_url,
            image_file=image_file,
            mode_override=mode_override,
        )


        # ── 3. Build HTTP Response ────────────────────────────────────────
        payload = {
            "status": "success",
            "shop_id": shop_id,
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


class MetaWebhookSilentView(APIView):
    """
    Webhook Meta en mode silence.

    Identique à MetaWebhookView SAUF qu'il ne rappelle jamais
    messenger_service.send_message(). Toutes les données sont stockées en DB.

    Cas d'usage :
      - Environnement staging branché sur une page Meta de test
      - Monitoring passif / audit sans déranger les clients
      - Tests end-to-end avec vrai format Meta

    Sécurité : vérification X-Hub-Signature-256 (partagée avec MetaWebhookView).
    """
    permission_classes = [AllowAny]

    # ── GET: Vérification webhook ─────────────────────────────────────────
    def get(self, request):
        mode      = request.query_params.get("hub.mode")
        token     = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode == "subscribe" and token == META_VERIFY_TOKEN:
            logger.info("[SILENT WEBHOOK] Verification successful")
            return HttpResponse(challenge, content_type="text/plain")

        logger.warning("[SILENT WEBHOOK] Verification failed — bad token")
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    # ── POST: Réception messages (SANS send_message) ──────────────────────
    def post(self, request):
        # 0. Vérifier signature Meta
        if not _verify_meta_signature(request):
            return Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        object_type = data.get("object")
        if object_type not in ("page", "instagram"):
            return Response({"error": "Unsupported object type"}, status=status.HTTP_400_BAD_REQUEST)

        platform  = "messenger" if object_type == "page" else "instagram"
        responses = []

        for entry in data.get("entry", []):
            page_id = entry.get("id", "")
            company = resolve_page_to_company(page_id)
            if not company:
                logger.warning(f"[SILENT WEBHOOK] No company for page_id={page_id}, skipping")
                continue

            shop_id   = company.shop_id

            for messaging_event in entry.get("messaging", []):
                sender_psid = messaging_event.get("sender", {}).get("id", "")
                message_obj = messaging_event.get("message", {})

                if not sender_psid or not message_obj:
                    continue

                # ── Ignorer les messages envoyés par la page elle-même (admin) ──
                if sender_psid == page_id:
                    logger.info(f"[SILENT WEBHOOK] Ignoring message from page itself (admin): {sender_psid}")
                    continue

                user_id   = sender_psid
                text      = message_obj.get("text", "")
                image_url = None
                for attach in message_obj.get("attachments", []):
                    if attach.get("type") == "image":
                        image_url = attach.get("payload", {}).get("url")
                        break

                # ── Pipeline complet (NLU ou LLM selon company.response_mode) ──
                result = pipeline.run(user_id, shop_id, text, image_url=image_url)
                result["platform"]    = platform
                result["sender_psid"] = sender_psid

                # ── Récupérer nom client (lecture seule, pas d'envoi) ──────────
                token = company.meta_page_access_token
                if token and sender_psid:
                    sender_name = messenger_service.get_sender_name(sender_psid, token)
                    if sender_name:
                        from apps.crm.models import Lead
                        Lead.objects.filter(platform_id=user_id).update(name=sender_name)
                        logger.info(f"[SILENT WEBHOOK] Lead name: '{sender_name}' for {user_id}")

                # ❌ send_message() volontairement absent — mode silence total
                bot_preview = result.get("text", "")[:60]
                logger.info(f"[SILENT WEBHOOK] Response stored (not sent): '{bot_preview}...'")

                responses.append(result)

        return Response({"status": "ok", "mode": "silent", "responses": responses})

