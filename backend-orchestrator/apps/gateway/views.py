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
from .services.azure_storage import azure_storage_service

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
                postback_obj = messaging_event.get("postback", {})

                if not sender_psid or (not message_obj and not postback_obj):
                    continue

                # ── Ignorer les messages envoyés par la page elle-même (admin) ──
                if sender_psid == page_id:
                    logger.info(f"[META WEBHOOK] Ignoring message from page itself (admin): {sender_psid}")
                    continue

                user_id = sender_psid   # PSID brut — ex: "7341829462837401"
                
                if postback_obj:
                    text = postback_obj.get("payload", "")
                else:
                    text = message_obj.get("text", "")

                # Extract image URL from attachments
                image_url = None
                for attach in message_obj.get("attachments", []):
                    if attach.get("type") == "image":
                        image_url = attach.get("payload", {}).get("url")
                        break

                # ── Delegate to pipeline ───────────────────────────────
                result = pipeline.run(user_id, shop_id, text, image_url=image_url, platform=platform)
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
                carousel_elements = result.get("carousel_elements")
                if carousel_elements and token:
                    messenger_service.send_carousel(sender_psid, carousel_elements, token)
                    
                bot_text = result.get("text", "")
                if bot_text and token:
                    messenger_service.send_message(sender_psid, bot_text, token)

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
            platform="poc",
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


class CatalogUploadView(APIView):
    """
    Endpoint pour le Dashboard Frontend.
    Reçoit une image locale, l'upload sur Azure, puis l'envoie au Vision Service pour vectorisation.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        shop_id = request.data.get("shop_id")
        item_id = request.data.get("item_id")
        metadata_str = request.data.get("metadata", "{}")
        image_file = request.FILES.get("image")

        if not all([shop_id, item_id, image_file]):
            return Response({"error": "shop_id, item_id, et image sont requis."}, status=status.HTTP_400_BAD_REQUEST)

        import json
        import requests
        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            metadata = {}

        custom_attributes_raw = request.data.get('custom_attributes')
        if custom_attributes_raw:
            try:
                custom_dict = json.loads(custom_attributes_raw)
                metadata.update(custom_dict)
            except json.JSONDecodeError:
                pass

        # 1. Upload l'image sur Azure (Le fichier physique devient une URL publique)
        image_url = azure_storage_service.upload_image(image_file, prefix=shop_id)
        if not image_url:
            return Response({"error": "Echec de l'upload sur Azure Storage."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. Construction du texte à embedder (Nom + Description)
        text_to_embed = None
        if metadata:
            name = metadata.get("name", "")
            desc = metadata.get("description", "")
            if name or desc:
                text_to_embed = f"{name} - {desc}".strip()

        # 3. Envoie l'URL publique, le texte et les infos au service Vision pour l'IA (Fusion Multimodale)
        try:
            vision_url = settings.VISION_SERVICE_URL.rstrip('/') + '/vectorize'
            res = requests.post(
                vision_url,
                json={
                    "image_url": image_url,
                    "text_to_embed": text_to_embed,
                    "item_id": item_id,
                    "shop_id": shop_id,
                    "metadata": metadata
                },
                timeout=15
            )
            if res.status_code == 200:
                return Response({
                    "status": "success",
                    "message": "Produit uploadé sur Azure et vectorisé avec succès !",
                    "azure_url": image_url,
                    "vision_response": res.json()
                })
            else:
                return Response({"error": f"Erreur Vision Service: {res.text}"}, status=res.status_code)
        except Exception as e:
            return Response({"error": f"Erreur de communication avec Vision Service: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CatalogUpdateMetadataView(APIView):
    """
    Met à jour uniquement les métadonnées d'un produit existant
    (nom, prix, description, in_stock) sans re-vectoriser l'image.

    PATCH /api/v1/gateway/catalog/update-metadata
    Body (JSON): { item_id, shop_id, metadata: { name, price, description, in_stock } }
    """
    permission_classes = [AllowAny]

    def patch(self, request):
        import json
        from apps.crm.models.analytics import ItemVector

        shop_id     = request.data.get("shop_id")
        item_id     = request.data.get("item_id")
        metadata_in = request.data.get("metadata", {})

        if not all([shop_id, item_id]):
            return Response({"error": "shop_id et item_id sont requis."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse metadata if it came as a JSON string
        if isinstance(metadata_in, str):
            try:
                metadata_in = json.loads(metadata_in)
            except json.JSONDecodeError:
                metadata_in = {}

        try:
            item = ItemVector.objects.get(item_id=item_id, shop_id=shop_id)
        except ItemVector.DoesNotExist:
            return Response({"error": "Produit introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # Merge incoming metadata into existing (keeps image_url and embedding intact)
        existing_meta = item.metadata or {}
        new_meta = {}
        # We start with the new keys
        for k, v in metadata_in.items():
            new_meta[k] = v
            
        # Ensure standard keys are not lost if omitted (fallback to existing)
        new_meta["name"] = metadata_in.get("name", existing_meta.get("name", ""))
        new_meta["price"] = metadata_in.get("price", existing_meta.get("price", ""))
        new_meta["description"] = metadata_in.get("description", existing_meta.get("description", ""))
        new_meta["in_stock"] = metadata_in.get("in_stock", existing_meta.get("in_stock", True))

        item.metadata = new_meta
        item.save(update_fields=["metadata"])

        logger.info(f"[CATALOG] Metadata updated for item_id={item_id} shop_id={shop_id}")
        return Response({"status": "success", "message": "Métadonnées mises à jour.", "metadata": new_meta})


class CatalogImportCsvView(APIView):
    """
    Importe un catalogue via un fichier CSV.
    Les produits sont créés sans image ni vecteur (Vector RAG). 
    Le marchand devra ajouter les images manuellement plus tard.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        import csv
        import uuid
        import io
        from apps.crm.models.analytics import ItemVector

        shop_id = request.data.get("shop_id")
        csv_file = request.FILES.get("file")

        if not shop_id or not csv_file:
            return Response({"error": "shop_id et file (CSV) sont requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string, delimiter=',')
            
            if reader.fieldnames and ';' in reader.fieldnames[0]:
                io_string.seek(0)
                reader = csv.DictReader(io_string, delimiter=';')

            items_created = 0
            for row in reader:
                row_lower = {k.lower().strip() if k else '': v for k, v in row.items()}
                
                name = row_lower.get("name", "").strip()
                if not name:
                    name = row_lower.get("nom", "").strip()
                if not name:
                    continue
                
                price = row_lower.get("price", "").strip()
                if not price:
                    price = row_lower.get("prix", "").strip()
                    
                description = row_lower.get("description", "").strip()
                
                in_stock_str = str(row_lower.get("in_stock", "true")).strip().lower()
                in_stock = in_stock_str in ["true", "1", "yes", "oui", "vrai", "v"]

                metadata = {
                    "name": name,
                    "price": price,
                    "description": description,
                    "in_stock": in_stock
                }
                
                # Ajout dynamique des colonnes supplémentaires du CSV
                standard_keys = ['name', 'nom', 'price', 'prix', 'description', 'in_stock', 'stock']
                for k, v in row.items():
                    if k and k.lower().strip() not in standard_keys:
                        val = v.strip() if isinstance(v, str) else v
                        if val:  # Ne pas ajouter de champs vides
                            metadata[k.strip()] = val
                
                
                item_id = f"prod_{uuid.uuid4().hex[:8]}"

                ItemVector.objects.create(
                    item_id=item_id,
                    shop_id=shop_id,
                    metadata=metadata,
                    image_url="",
                    embedding=None
                )
                items_created += 1

            return Response({
                "status": "success", 
                "message": f"{items_created} produits importés avec succès !",
                "count": items_created
            })
            
        except Exception as e:
            logger.error(f"[CSV IMPORT] Error: {e}")
            return Response({"error": f"Erreur lors de l'import CSV : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
