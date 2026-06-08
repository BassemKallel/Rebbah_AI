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
from apps.gateway.services.pipeline import context_manager
from apps.gateway.services.azure_storage import azure_storage_service
from apps.gateway.tasks import process_webhook_message_async

logger = logging.getLogger(__name__)

META_VERIFY_TOKEN = getattr(settings, "META_VERIFY_TOKEN", "tiktak_verify_token")


def _verify_meta_signature(request) -> bool:
    """
    Vérifie la signature HMAC-SHA256 envoyée par Meta dans X-Hub-Signature-256.
    Retourne True si valide, ou si META_APP_SECRET n'est pas configuré.
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
    """
    try:
        return Company.objects.get(meta_page_id=page_id, is_active=True)
    except Company.DoesNotExist:
        return None


class MetaWebhookView(APIView):
    """
    Real Meta Webhook for Messenger and Instagram.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode == "subscribe" and token == META_VERIFY_TOKEN:
            logger.info("[META WEBHOOK] Verification successful")
            return HttpResponse(challenge, content_type="text/plain")

        logger.warning("[META WEBHOOK] Verification failed — bad token")
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        if not _verify_meta_signature(request):
            return Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        object_type = data.get("object")

        if object_type not in ("page", "instagram"):
            return Response({"error": "Unsupported object type"}, status=status.HTTP_400_BAD_REQUEST)

        platform = "messenger" if object_type == "page" else "instagram"
        responses = []

        for entry in data.get("entry", []):
            page_id = entry.get("id", "")
            company = resolve_page_to_company(page_id)
            if not company:
                logger.warning(f"[META WEBHOOK] No company mapped for page_id={page_id}, skipping")
                continue

            shop_id = company.shop_id

            for messaging_event in entry.get("messaging", []):
                sender_psid = messaging_event.get("sender", {}).get("id", "")
                message_obj = messaging_event.get("message", {})
                postback_obj = messaging_event.get("postback", {})

                if not sender_psid or (not message_obj and not postback_obj):
                    continue

                if sender_psid == page_id:
                    logger.info(f"[META WEBHOOK] Ignoring message from page itself (admin): {sender_psid}")
                    continue

                user_id = sender_psid
                
                if postback_obj:
                    text = postback_obj.get("payload", "")
                else:
                    text = message_obj.get("text", "")

                image_url = None
                for attach in message_obj.get("attachments", []):
                    if attach.get("type") == "image":
                        image_url = attach.get("payload", {}).get("url")
                        break

                current_timestamp = context_manager.add_to_debounce_buffer(
                    user_id, shop_id, text, image_url
                )

                token = company.meta_page_access_token
                process_webhook_message_async.delay(
                    user_id=user_id,
                    shop_id=shop_id,
                    text=text,
                    image_url=image_url,
                    current_timestamp=current_timestamp,
                    platform=platform,
                    page_token=token,
                    sender_psid=sender_psid,
                )
                logger.info(
                    f"[META WEBHOOK] Message queued for Celery: user_id={user_id} "
                    f"shop_id={shop_id} platform={platform}"
                )
                responses.append({"status": "queued_for_processing"})

        return Response({"status": "ok", "responses": responses})


class MessengerWebhookPOC(APIView):
    """
    POC endpoint for testing and internal integrations.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        import traceback
        try:
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

            mode_override = request.data.get("mode")
            if mode_override not in ("nlu", "llm"):
                mode_override = None

            if image_file:
                uploaded_url = azure_storage_service.upload_image(image_file, prefix=shop_id)
                if uploaded_url:
                    image_url = uploaded_url

            current_timestamp = context_manager.add_to_debounce_buffer(user_id, shop_id, text, image_url)

            process_webhook_message_async.delay(
                user_id=user_id,
                shop_id=shop_id,
                text=text,
                image_url=image_url,
                current_timestamp=current_timestamp,
                platform="poc",
                page_token=None,
                sender_psid=user_id,
            )
            logger.info(
                f"[POC WEBHOOK] Message queued for Celery: user_id={user_id} shop_id={shop_id}"
            )

            return Response({
                "status": "queued_for_processing",
                "shop_id": shop_id,
                "note": "Message is being processed asynchronously by the Celery worker.",
            })
        except Exception as e:
            logger.error(f"[POC WEBHOOK ERROR] 500 Exception: {e}", exc_info=True)
            return Response({
                "status": "error",
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MetaWebhookSilentView(APIView):
    """
    Webhook Meta en mode silence.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode == "subscribe" and token == META_VERIFY_TOKEN:
            logger.info("[SILENT WEBHOOK] Verification successful")
            return HttpResponse(challenge, content_type="text/plain")

        logger.warning("[SILENT WEBHOOK] Verification failed — bad token")
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        if not _verify_meta_signature(request):
            return Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        object_type = data.get("object")
        if object_type not in ("page", "instagram"):
            return Response({"error": "Unsupported object type"}, status=status.HTTP_400_BAD_REQUEST)

        platform = "messenger" if object_type == "page" else "instagram"
        responses = []

        for entry in data.get("entry", []):
            page_id = entry.get("id", "")
            company = resolve_page_to_company(page_id)
            if not company:
                logger.warning(f"[SILENT WEBHOOK] No company for page_id={page_id}, skipping")
                continue

            shop_id = company.shop_id

            for messaging_event in entry.get("messaging", []):
                sender_psid = messaging_event.get("sender", {}).get("id", "")
                message_obj = messaging_event.get("message", {})

                if not sender_psid or not message_obj:
                    continue

                if sender_psid == page_id:
                    logger.info(f"[SILENT WEBHOOK] Ignoring message from page itself (admin): {sender_psid}")
                    continue

                user_id = sender_psid
                text = message_obj.get("text", "")
                image_url = None
                for attach in message_obj.get("attachments", []):
                    if attach.get("type") == "image":
                        image_url = attach.get("payload", {}).get("url")
                        break

                current_timestamp = context_manager.add_to_debounce_buffer(
                    user_id, shop_id, text, image_url
                )

                process_webhook_message_async.delay(
                    user_id=user_id,
                    shop_id=shop_id,
                    text=text,
                    image_url=image_url,
                    current_timestamp=current_timestamp,
                    platform=platform,
                    page_token=None,
                    sender_psid=sender_psid,
                )
                logger.info(
                    f"[SILENT WEBHOOK] Message queued for Celery (silent): "
                    f"user_id={user_id} shop_id={shop_id}"
                )
                responses.append({"status": "queued_for_processing"})

        return Response({"status": "ok", "mode": "silent", "responses": responses})


class DirectMessageProcessView(APIView):
    """
    Direct asynchronous message processing view.
    Receives message payload from client servers, validates via X-Shop-Token,
    and queues processing in Celery which replies directly to the client via Meta API.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        import traceback
        try:
            # 1. Authenticate using static shop token
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

            # 2. Extract inputs
            user_id = request.data.get("user_id")
            if not user_id:
                return Response(
                    {"error": "user_id is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            text = request.data.get("text", "")
            image_url = request.data.get("image_url")

            # 3. Register message to Redis debounce buffer
            current_timestamp = context_manager.add_to_debounce_buffer(user_id, shop_id, text, image_url)

            # 4. Fire Celery async task (replies directly to Meta)
            process_webhook_message_async.delay(
                user_id=user_id,
                shop_id=shop_id,
                text=text,
                image_url=image_url,
                current_timestamp=current_timestamp,
                platform="messenger",
                page_token=company.meta_page_access_token,
                sender_psid=user_id,
            )
            logger.info(
                f"[DIRECT API] Message queued for Celery: user_id={user_id} shop_id={shop_id}"
            )

            # 5. Return immediate acknowledgment to the calling server
            return Response({
                "status": "queued_for_processing",
                "shop_id": shop_id,
                "note": "Message is being processed asynchronously and reply will be sent directly to Meta.",
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[DIRECT API ERROR] Failed to queue message: {e}", exc_info=True)
            return Response({
                "status": "error",
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

