"""
pipeline.py — Core Message Processing Pipeline

Single entry point for all message processing, eliminating duplication
between MetaWebhookView and MessengerWebhookPOC.

Steps:
  2. Cold Memory: Lead + Conversation + Grace Period
  3. Hot Memory: Redis
  4. Vision API
  5. NLU API + Guards + Fallback
  6. Save User Message
  7. Context Accumulation
  8. Contextual Mapping
  9. Product Lookup
  10. Disambiguation Resolution
  11. State Machine
  12-13. Persist State + Save Bot Message + AWAITING_CORRECTION
"""
import logging
from datetime import timedelta
from django.utils import timezone

from apps.crm.models import Lead, Conversation, Message, BotConfiguration
from .context_manager import ContextManager
from .response_templates import FALLBACK_PRODUCTS
from .services import ai_service, tiktak_service, dialog_manager
from .services.dialog_manager import detect_language
from .services.azure_storage import azure_storage_service
from . import disambiguation

logger = logging.getLogger(__name__)

context_manager = ContextManager()

# Grace period: how long a completed conversation stays open for corrections
GRACE_PERIOD_MINUTES = 10


class MessagePipeline:
    """
    Unified message processing pipeline.
    Called by both MetaWebhookView and MessengerWebhookPOC.
    """

    def run(self, user_id, shop_id, text,
            image_url=None, image_file=None,
            api_token=None) -> dict:
        """
        Process one incoming message through the full pipeline.

        Args:
            user_id:    Unique user identifier (e.g. "messenger:123456")
            shop_id:    Shop identifier for product/config lookup
            text:       Message text (may be empty if image-only)
            image_url:  URL of an image attachment (optional)
            image_file: Uploaded image file object (optional, POC only)
            api_token:  Per-shop API token for TikTak API (optional)

        Returns:
            dict with keys: text, intent, state, entities, context,
                            matched_image_url?, uploaded_url?
        """
        result = {}

        # ── Upload image to Azure if file provided ─────────────────────────
        uploaded_url = None
        if image_file:
            uploaded_url = azure_storage_service.upload_image(image_file, prefix=shop_id)
            if uploaded_url:
                image_url = uploaded_url
                result["uploaded_url"] = uploaded_url

        # ── 2. Cold Memory: Lead + Conversation ───────────────────────────
        lead, _ = Lead.objects.get_or_create(platform_id=user_id)
        conversation = Conversation.objects.filter(
            lead=lead,
            state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY", "WAITING_DISAMBIGUATION", "AWAITING_CORRECTION"]
        ).first()
        if not conversation:
            conversation = Conversation.objects.create(lead=lead, shop_id=shop_id, state="NEW_CONVERSATION")

        # Handle grace period expiration
        if conversation.state == "AWAITING_CORRECTION":
            if conversation.completed_at:
                try:
                    elapsed_minutes = (timezone.now() - conversation.completed_at).total_seconds() / 60
                except TypeError:
                    # Fallback: make completed_at timezone-aware if stored naive
                    from django.utils import timezone as tz
                    completed_at_aware = tz.make_aware(conversation.completed_at.replace(tzinfo=None))
                    elapsed_minutes = (tz.now() - completed_at_aware).total_seconds() / 60
                logger.info(f"[PIPELINE] Grace period: {elapsed_minutes:.1f}min elapsed / {GRACE_PERIOD_MINUTES}min limit")
                if elapsed_minutes > GRACE_PERIOD_MINUTES:
                    conversation.state = "COMPLETED"
                    conversation.save()
                    context_manager.clear_context(user_id)
                    conversation = Conversation.objects.create(lead=lead, shop_id=shop_id, state="NEW_CONVERSATION")
                else:
                    # Still in grace period — restore to WAITING_USER_REPLY
                    conversation.state = "WAITING_USER_REPLY"
                    conversation.save()
            else:
                # completed_at not set — treat as expired, start fresh
                logger.warning("[PIPELINE] AWAITING_CORRECTION but completed_at is None — starting new conversation")
                conversation.state = "COMPLETED"
                conversation.save()
                context_manager.clear_context(user_id)
                conversation = Conversation.objects.create(lead=lead, shop_id=shop_id, state="NEW_CONVERSATION")

        # ── 3. Hot Memory ─────────────────────────────────────────────────
        context_manager.add_message(user_id, role="user", text=text)

        # ── 4. Vision API ─────────────────────────────────────────────────
        is_error = False
        extracted_entities = {}
        matched_image_url = None
        vision_variation_id = None

        if image_file or image_url:
            vision_result = ai_service.call_vision(shop_id, image_url=image_url, image_file=image_file if image_file else None)
            if vision_result:
                extracted_entities["product"] = f"Article_From_Image_{vision_result['product_id']}"
                matched_image_url = vision_result.get("image_url")
                vision_variation_id = vision_result.get("variation_id")
            else:
                is_error = True

        # ── 5. NLU API ────────────────────────────────────────────────────
        nlu_raw_entities = []
        extracted_intent  = "UNKNOWN"
        intent_confidence = None

        if text:
            nlu_result = ai_service.call_nlu(text)
            extracted_intent    = nlu_result["intent"]
            nlu_raw_entities    = nlu_result["raw_entities"]
            intent_confidence   = nlu_result.get("confidence_score")
            is_error = is_error or nlu_result["error"]

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

        # Detect language for disambiguation messages
        lang = detect_language(text)

        state_before = conversation.state

        # ── 6. Save User Message ──────────────────────────────────────────
        user_message = Message.objects.create(
            conversation=conversation,
            sender="USER",
            text=text if text else f"[Image: {image_url}]",
            extracted_intent=extracted_intent,
            intent_confidence_score=intent_confidence if text else None,
            extracted_entities=extracted_entities,
            is_error=is_error,
            conversation_state_before=state_before,
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
                products = tiktak_service.get_products(shop_id, api_token=api_token)
                matched_product, color_from_vision, candidates = tiktak_service.find_product(
                    products, prod_name, vision_variation_id
                )

                # Pre-fill color from vision if not yet in context
                if color_from_vision and "color" not in current_context:
                    current_context["color"] = color_from_vision
                    extracted_entities["color"] = color_from_vision

                # Handle ambiguous keyword match
                if candidates:
                    current_context["candidates"] = candidates
                    current_context["pending_intent"] = extracted_intent
            except Exception as e:
                logger.error(f"[TIKTAK] product lookup failed: {e}")

        # Update message with any enriched entities
        user_message.extracted_entities = extracted_entities
        user_message.extracted_intent = extracted_intent
        user_message.save(update_fields=["extracted_entities", "extracted_intent"])

        # ── 10. Disambiguation Resolution ─────────────────────────────────
        disambig_result = self._handle_disambiguation(
            conversation, previous_state, current_context,
            text, extracted_intent, matched_product, user_id, lang
        )
        if disambig_result is not None:
            # Early return — disambiguation message sent
            if disambig_result.get("matched_product"):
                matched_product = disambig_result["matched_product"]
                current_context["product"] = matched_product["name"]
                extracted_intent = current_context.pop("pending_intent", extracted_intent)
                current_context.pop("candidates", None)
            else:
                # Unresolved — return disambiguation response
                result.update(disambig_result)
                return result

        # ── 11. State Machine ─────────────────────────────────────────────
        bot_config, _ = BotConfiguration.objects.get_or_create(shop_id=shop_id)
        current_context["shop_id"] = shop_id
        sm_result = dialog_manager.run_state_machine(
            intent=extracted_intent,
            previous_state=previous_state,
            current_context=current_context,
            matched_product=matched_product,
            lead=lead,
            conversation=conversation,
            vision_variation_id=vision_variation_id,
            bot_config=bot_config,
            text=text,
        )
        current_context.pop("shop_id", None)

        bot_response_text = sm_result["bot_response"]
        new_state = sm_result["new_state"]
        missing_list = sm_result["missing_list"]

        # ── 12. Persist State ─────────────────────────────────────────────
        conversation.state = new_state
        conversation.missing_entities = missing_list
        conversation.context_data = current_context
        conversation.save()

        # ── 13. Save Bot Message ──────────────────────────────────────────
        Message.objects.create(conversation=conversation, sender="BOT", text=bot_response_text, is_error=False)
        context_manager.add_message(user_id, role="bot", text=bot_response_text)

        # ── Grace Period: AWAITING_CORRECTION ─────────────────────────────
        if new_state == "COMPLETED":
            new_state = "AWAITING_CORRECTION"
            conversation.state = new_state
            conversation.completed_at = timezone.now()
            conversation.save()

        # Update user message with the FINAL state (after AWAITING_CORRECTION override)
        user_message.conversation_state_after = new_state
        user_message.save(update_fields=["conversation_state_after"])

        # ── Build result ──────────────────────────────────────────────────
        result.update({
            "text": bot_response_text,
            "intent": extracted_intent,
            "state": new_state,
            "entities": extracted_entities,
            "context": current_context,
            "missing_entities": missing_list,
        })
        if matched_image_url:
            result["matched_image_url"] = matched_image_url

        return result

    def _handle_disambiguation(self, conversation, previous_state, current_context,
                                text, extracted_intent, matched_product, user_id, lang="FR"):
        """
        Handle disambiguation: resolve existing ambiguity or detect new one.
        Returns None if no disambiguation needed,
        or a dict with either matched_product or disambiguation response.
        """
        # Resolve existing disambiguation
        if previous_state == "WAITING_DISAMBIGUATION":
            candidates = current_context.get("candidates", [])
            resolved = disambiguation.resolve(text, candidates)

            if resolved:
                return {"matched_product": resolved}
            else:
                # Still unresolved — re-send disambiguation message
                bot_text = disambiguation.build_response(candidates, lang=lang)
                conversation.state = "WAITING_DISAMBIGUATION"
                conversation.context_data = current_context
                conversation.missing_entities = []
                conversation.save()
                Message.objects.create(conversation=conversation, sender="BOT", text=bot_text)
                context_manager.add_message(user_id, role="bot", text=bot_text)
                return {
                    "text": bot_text,
                    "intent": extracted_intent,
                    "state": "WAITING_DISAMBIGUATION",
                    "entities": {},
                    "context": current_context,
                    "missing_entities": [],
                }

        # New ambiguity detected this turn
        if current_context.get("candidates") and not matched_product:
            candidates = current_context["candidates"]
            bot_text = disambiguation.build_response(candidates, lang=lang)
            conversation.state = "WAITING_DISAMBIGUATION"
            conversation.context_data = current_context
            conversation.missing_entities = []
            conversation.save()
            Message.objects.create(conversation=conversation, sender="BOT", text=bot_text)
            context_manager.add_message(user_id, role="bot", text=bot_text)
            return {
                "text": bot_text,
                "intent": extracted_intent,
                "state": "WAITING_DISAMBIGUATION",
                "entities": {},
                "context": current_context,
                "missing_entities": [],
            }

        return None
