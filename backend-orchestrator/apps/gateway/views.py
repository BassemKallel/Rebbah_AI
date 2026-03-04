"""
views.py — Layer 4: HTTP Entry Point (thin orchestrator)

This file should only:
1. Parse the incoming HTTP request
2. Retrieve or create the DB records (Lead, Conversation)
3. Delegate to service layers in order
4. Persist results and return the HTTP response
"""
import logging
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.crm.models import Lead, Conversation, Message
from .context_manager import ContextManager
from .response_templates import DISAMBIGUATION_TEMPLATE, REQUIRED_ORDER_ENTITIES, FALLBACK_PRODUCTS
from .services import ai_service, tiktak_service, dialog_manager

logger = logging.getLogger(__name__)

context_manager = ContextManager()


class MessengerWebhookPOC(APIView):
    """
    Simulates the webhook receiving messages from WhatsApp or Messenger.
    """

    def post(self, request):
        # ── 1. Parse Input ────────────────────────────────────────────────
        user_id  = request.data.get("user_id")
        shop_id  = request.data.get("shop_id", "default_shop")

        message_data = request.data.get("message", {})
        if isinstance(message_data, str):
            import json as _json
            try:
                message_data = _json.loads(message_data)
            except Exception:
                message_data = {}

        text      = message_data.get("text", "") or request.data.get("text", "")
        image_url = message_data.get("image_url") or request.data.get("image_url")
        image_file = request.FILES.get("image")

        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # ── 2. Cold Memory: Lead + Conversation ───────────────────────────
        lead, _ = Lead.objects.get_or_create(platform_id=user_id)
        conversation = Conversation.objects.filter(
            lead=lead,
            state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY", "WAITING_DISAMBIGUATION"]
        ).first()
        if not conversation:
            conversation = Conversation.objects.create(lead=lead, shop_id=shop_id, state="NEW_CONVERSATION")

        # ── 3. Hot Memory: log user message in Redis ──────────────────────
        context_manager.add_message(user_id, role="user", text=text)

        # ── 4. Vision API ─────────────────────────────────────────────────
        is_error           = False
        extracted_entities = {}
        matched_image_url  = None
        vision_variation_id = None

        if image_file or image_url:
            vision_result = ai_service.call_vision(shop_id, image_url=image_url, image_file=image_file)
            if vision_result:
                extracted_entities["product"] = f"Article_From_Image_{vision_result['product_id']}"
                matched_image_url             = vision_result.get("image_url")
                vision_variation_id           = vision_result.get("variation_id")
            else:
                is_error = True

        # ── 5. NLU API ────────────────────────────────────────────────────
        nlu_raw_entities = []
        extracted_intent = "UNKNOWN"

        if text:
            nlu_result = ai_service.call_nlu(text)
            extracted_intent  = nlu_result["intent"]
            nlu_raw_entities  = nlu_result["raw_entities"]
            is_error          = is_error or nlu_result["error"]

            # Entity filtering & guards
            filtered = dialog_manager.apply_entity_guards(nlu_raw_entities, extracted_intent, conversation)
            extracted_entities.update(filtered)

            # Simple product keyword fallback
            if ("product" not in extracted_entities
                    and not image_url
                    and "product" not in conversation.context_data):
                for cp in FALLBACK_PRODUCTS:
                    if cp in text.lower():
                        extracted_entities["product"] = cp
                        break

        # Default intent when only an image was provided
        if (image_url or image_file) and (extracted_intent == "UNKNOWN" or not text):
            extracted_intent = "ORDER_PRODUCT"

        # ── 6. Save User Message ──────────────────────────────────────────
        user_message = Message.objects.create(
            conversation=conversation,
            sender="USER",
            text=text if text else f"[Image: {image_url}]",
            extracted_intent=extracted_intent,
            extracted_entities=extracted_entities,
            is_error=is_error,
        )

        # ── 7. Context Accumulation ───────────────────────────────────────
        current_context = conversation.context_data
        current_context = dialog_manager.accumulate_context(current_context, extracted_entities)
        conversation.context_data = current_context

        # ── 8. Contextual Mapping ─────────────────────────────────────────
        previous_state = conversation.state
        _contextual_intents = {"INFORM_INFO", "NOISE", "ORDER_PRODUCT", "UNKNOWN"}

        if extracted_intent in _contextual_intents:
            extracted_entities, contextual_match = dialog_manager.run_contextual_mapping(
                conversation, text, extracted_entities, nlu_raw_entities, current_context
            )
            if contextual_match and extracted_intent == "NOISE":
                extracted_intent = "INFORM_INFO"

        # ── 9. Product Lookup ─────────────────────────────────────────────
        matched_product = None
        prod_name = current_context.get("product")

        if prod_name:
            try:
                products = tiktak_service.get_products(shop_id)
                matched_product, color_from_vision, candidates = tiktak_service.find_product(
                    products, prod_name, vision_variation_id
                )

                # Pre-fill color from vision if not yet in context
                if color_from_vision and "color" not in current_context:
                    current_context["color"]     = color_from_vision
                    extracted_entities["color"]  = color_from_vision

                # Handle ambiguous keyword match
                if candidates:
                    current_context["candidates"]    = candidates
                    current_context["pending_intent"] = extracted_intent
            except Exception as e:
                logger.error(f"[TIKTAK] product lookup failed: {e}")

        # Update message with any enriched entities
        user_message.extracted_entities = extracted_entities
        user_message.extracted_intent   = extracted_intent
        user_message.save(update_fields=["extracted_entities", "extracted_intent"])

        # ── 10. Disambiguation Resolution ─────────────────────────────────
        if previous_state == "WAITING_DISAMBIGUATION":
            candidates = current_context.get("candidates", [])
            resolved   = None
            if text and candidates:
                text_lower = text.lower()
                for i, c in enumerate(candidates):
                    if str(i + 1) in text:
                        resolved = c
                        break
                if not resolved:
                    for c in candidates:
                        if c["name"].lower() in text_lower or text_lower in c["name"].lower():
                            resolved = c
                            break
                if not resolved:
                    for c in candidates:
                        for v in c.get("variations", []):
                            if v.get("color", "").lower() in text_lower:
                                resolved = c
                                break
                        if resolved:
                            break

            if resolved:
                matched_product = resolved
                current_context["product"] = resolved["name"]
                extracted_intent = current_context.pop("pending_intent", extracted_intent)
                current_context.pop("candidates", None)
            else:
                new_state  = "WAITING_DISAMBIGUATION"
                items_list = "\n".join(f"{i+1}. {c['name']} ({c['base_price']} TND)" for i, c in enumerate(candidates))
                bot_text   = DISAMBIGUATION_TEMPLATE.replace("{count}", str(len(candidates))).replace("{list}", items_list)
                conversation.state         = new_state
                conversation.context_data  = current_context
                conversation.missing_entities = []
                conversation.save()
                Message.objects.create(conversation=conversation, sender="BOT", text=bot_text)
                context_manager.add_message(user_id, role="bot", text=bot_text)
                return Response({"status": "success", "bot_response": {"text": bot_text, "internal_debug": {"intent_detected": extracted_intent, "new_state": new_state}}})

        # New ambiguity detected this turn
        if current_context.get("candidates") and not matched_product:
            new_state  = "WAITING_DISAMBIGUATION"
            candidates = current_context["candidates"]
            items_list = "\n".join(f"{i+1}. {c['name']} ({c['base_price']} TND)" for i, c in enumerate(candidates))
            bot_text   = DISAMBIGUATION_TEMPLATE.replace("{count}", str(len(candidates))).replace("{list}", items_list)
            conversation.state         = new_state
            conversation.context_data  = current_context
            conversation.missing_entities = []
            conversation.save()
            Message.objects.create(conversation=conversation, sender="BOT", text=bot_text)
            context_manager.add_message(user_id, role="bot", text=bot_text)
            return Response({"status": "success", "bot_response": {"text": bot_text, "internal_debug": {"intent_detected": extracted_intent, "new_state": new_state}}})

        # ── 11. State Machine ─────────────────────────────────────────────
        # Inject shop_id into context for create_pending_order helper
        current_context["shop_id"] = shop_id
        sm_result = dialog_manager.run_state_machine(
            intent=extracted_intent,
            previous_state=previous_state,
            current_context=current_context,
            matched_product=matched_product,
            lead=lead,
            conversation=conversation,
            vision_variation_id=vision_variation_id,
        )
        current_context.pop("shop_id", None)

        bot_response_text = sm_result["bot_response"]
        new_state         = sm_result["new_state"]
        missing_list      = sm_result["missing_list"]

        # ── 12. Persist State ─────────────────────────────────────────────
        conversation.state           = new_state
        conversation.missing_entities = missing_list
        conversation.context_data    = current_context
        conversation.save()

        # ── 13. Save Bot Message ──────────────────────────────────────────
        Message.objects.create(conversation=conversation, sender="BOT", text=bot_response_text, is_error=False)
        context_manager.add_message(user_id, role="bot", text=bot_response_text)

        if new_state == "COMPLETED":
            context_manager.clear_context(user_id)

        # ── 14. HTTP Response ─────────────────────────────────────────────
        payload = {
            "status": "success",
            "bot_response": {
                "text": bot_response_text,
                "internal_debug": {
                    "intent_detected":    extracted_intent,
                    "entities_extracted": extracted_entities,
                    "accumulated_context": current_context,
                    "previous_state":     previous_state,
                    "new_state":          new_state,
                    "missing_entities":   missing_list,
                },
            },
        }
        if matched_image_url:
            payload["bot_response"]["identified_image_url"] = matched_image_url

        return Response(payload)
