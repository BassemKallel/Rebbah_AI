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
from django.conf import settings
from django.utils import timezone


from apps.crm.models import Lead, Conversation, Message, BotConfiguration, NLUFallbackLog, Company
from .context_manager import ContextManager
from .response_templates import FALLBACK_PRODUCTS
from .services import ai_service, tiktak_service, dialog_manager
from .services.llm_response_service import generate_llm_response
from .services.dialog_manager import detect_language
from .services.azure_storage import azure_storage_service
from . import disambiguation

logger = logging.getLogger(__name__)

context_manager = ContextManager()

# Grace period: how long a completed conversation stays open for corrections
GRACE_PERIOD_MINUTES = 2


class MessagePipeline:
    """
    Unified message processing pipeline.
    Called by both MetaWebhookView and MessengerWebhookPOC.
    """

    def run(self, user_id, shop_id, text,
            image_url=None, image_file=None,
            mode_override=None) -> dict:
        """
        Process one incoming message through the full pipeline.

        Args:
            user_id:       Unique user identifier (e.g. "messenger:123456")
            shop_id:       Shop identifier for product/config lookup
            text:          Message text (may be empty if image-only)
            image_url:     URL of an image attachment (optional)
            image_file:    Uploaded image file object (optional, POC only)
            api_token:     (supprimé) — l'API TikTak est publique, aucun token requis.
            mode_override: Force 'nlu' or 'llm' for this request only (optional)
                           If None, uses Company.response_mode from DB.

        Returns:
            dict with keys: text, intent, state, entities, context,
                            matched_image_url?, uploaded_url?
        """
        result = {}

        # ── LLM Mode Branch ───────────────────────────────────────────────
        # If the company uses LLM Direct mode, bypass the entire NLU pipeline
        company = Company.objects.filter(shop_id=shop_id, is_active=True).first()

        # Determine effective mode: override > company setting > default 'nlu'
        effective_mode = (
            mode_override if mode_override in ('nlu', 'llm')
            else (company.response_mode if company else 'nlu')
        )

        if company and effective_mode == 'llm' and text:
            return self._run_llm_mode(user_id, shop_id, text, company)


        # ── Upload image to Azure if file provided ─────────────────────────
        uploaded_url = None
        if image_file:
            uploaded_url = azure_storage_service.upload_image(image_file, prefix=shop_id)
            if uploaded_url:
                image_url = uploaded_url
                result["uploaded_url"] = uploaded_url

        # ── 2. Cold Memory: Lead + Conversation ───────────────────────────
        # Find an active conversation for this user (in-progress order)
        conversation = Conversation.objects.filter(
            sender_id=user_id,
            state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY", "WAITING_DISAMBIGUATION", "AWAITING_CORRECTION"]
        ).first()

        if conversation:
            # Reuse the Lead tied to the active conversation
            lead = conversation.lead
        else:
            # No active conversation → new order → create a fresh Lead
            lead = Lead.objects.create(platform_id=user_id)
            conversation = Conversation.objects.create(
                lead=lead,
                lead_uuid=lead.uuid,
                sender_id=user_id,
                shop_id=shop_id,
                state="NEW_CONVERSATION"
            )

        # Handle grace period expiration
        correction_mode = False
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
                    lead = Lead.objects.create(platform_id=user_id)
                    conversation = Conversation.objects.create(
                        lead=lead, lead_uuid=lead.uuid, sender_id=user_id,
                        shop_id=shop_id, state="NEW_CONVERSATION"
                    )
                else:
                    # Still in grace period — correction mode
                    correction_mode = True
                    conversation.state = "WAITING_USER_REPLY"
                    conversation.save()
                    logger.info("[PIPELINE] Correction mode: will force ORDER_PRODUCT after NLU")
            else:
                # completed_at not set — treat as expired, start fresh
                logger.warning("[PIPELINE] AWAITING_CORRECTION but completed_at is None — starting new conversation")
                conversation.state = "COMPLETED"
                conversation.save()
                context_manager.clear_context(user_id)
                lead = Lead.objects.create(platform_id=user_id)
                conversation = Conversation.objects.create(
                    lead=lead, lead_uuid=lead.uuid, sender_id=user_id,
                    shop_id=shop_id, state="NEW_CONVERSATION"
                )


        # ── 3. (Hot Memory moved to step 5b — after NLU) ─────────────────

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

                # Pre-fill color from variation (size is left for the user to provide)
                if vision_variation_id:
                    products = tiktak_service.get_products(shop_id)
                    detected_color = tiktak_service.get_color_from_variation(vision_variation_id, products)
                    if detected_color:
                        extracted_entities["color"] = detected_color
                        logger.info(f"[PIPELINE] Vision pre-filled color='{detected_color}'")
            else:
                is_error = True

        # ── 5. NLU API ────────────────────────────────────────────────────
        nlu_raw_entities = []
        extracted_intent  = "NOISE"
        intent_confidence = None
        is_fallback = False
        nlu_result = {}

        if text:
            nlu_result = ai_service.call_nlu(text, user_id=user_id)
            extracted_intent    = nlu_result["intent"]
            nlu_raw_entities    = nlu_result["raw_entities"]
            intent_confidence   = nlu_result.get("confidence_score")
            is_error = is_error or nlu_result["error"]
            is_fallback = nlu_result.get("fallback_used", False)

            if is_fallback:
                logger.warning(f"[PIPELINE] Gemini fallback used (reason={nlu_result.get('_trigger_reason')})")

            # ── 5b. Hot Memory (enriched — after NLU) ─────────────────────
            context_manager.add_message(
                user_id, role="user", text=text,
                intent=extracted_intent,
                confidence=intent_confidence,
                entities=extracted_entities,
            )
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
        if (image_url or image_file) and (extracted_intent == "NOISE" or not text):
            extracted_intent = "ORDER_PRODUCT"

        # Detect language for disambiguation messages
        lang = detect_language(text)

        state_before = conversation.state

        # ── 6. Save User Message ──────────────────────────────────────────
        is_fallback = is_fallback if text else False
        user_message = Message.objects.create(
            conversation=conversation,
            sender="USER",
            text=text if text else f"[Image: {image_url}]",
            extracted_intent=extracted_intent,
            intent_confidence_score=intent_confidence if text else None,
            extracted_entities=extracted_entities,
            is_error=is_error,
            is_fallback=is_fallback,
            conversation_state_before=state_before,
        )

        # ── 6b. Save NLU Fallback Log (active learning) ───────────────────
        if text and is_fallback:
            tunbert_orig = nlu_result.get("_tunbert_original", {})
            trigger = nlu_result.get("_trigger_reason", "LOW_CONFIDENCE")
            try:
                NLUFallbackLog.objects.create(
                    message=user_message,
                    original_text=text,
                    tunbert_intent=tunbert_orig.get("intent"),
                    tunbert_confidence=tunbert_orig.get("confidence_score"),
                    tunbert_entities=tunbert_orig.get("raw_entities", []),
                    gemini_intent=nlu_result["intent"],
                    gemini_confidence=nlu_result.get("confidence_score"),
                    gemini_entities=nlu_result.get("raw_entities", []),
                    trigger_reason=trigger,
                    intent_changed=(tunbert_orig.get("intent") != nlu_result["intent"]),
                )
            except Exception as e:
                logger.error(f"[PIPELINE] Failed to save NLUFallbackLog: {e}")

        # ── 7. Context Accumulation ───────────────────────────────────────
        current_context = conversation.context_data
        current_context = dialog_manager.accumulate_context(current_context, extracted_entities)
        conversation.context_data = current_context

        # Persist/restore vision_variation_id across messages
        if vision_variation_id:
            current_context["_vision_variation_id"] = vision_variation_id
        else:
            vision_variation_id = current_context.get("_vision_variation_id")

        # ── 8. Contextual Mapping ─────────────────────────────────────────
        previous_state = conversation.state
        _contextual_intents = {"INFORM_INFO", "NOISE", "ORDER_PRODUCT", "CONFIRM_DENY", "UNKNOWN"}

        # Redirect CONFIRM_DENY / UNKNOWN → INFORM_INFO during active flow
        if (extracted_intent in ("CONFIRM_DENY", "UNKNOWN")
                and previous_state == "WAITING_USER_REPLY"
                and conversation.missing_entities):
            logger.info(f"[PIPELINE] {extracted_intent} during active flow → INFORM_INFO")
            extracted_intent = "INFORM_INFO"

        if extracted_intent in _contextual_intents:
            extracted_entities, contextual_match = dialog_manager.run_contextual_mapping(
                conversation, text, extracted_entities, nlu_raw_entities, current_context
            )
            if contextual_match and extracted_intent in ("NOISE", "CONFIRM_DENY", "UNKNOWN"):
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

        # ── 10b. Correction Mode Override ─────────────────────────────────
        if correction_mode and extracted_intent in ("INFORM_INFO", "NOISE", "UNKNOWN"):
            extracted_intent = "ORDER_PRODUCT"
            logger.info("[PIPELINE] Correction mode → forcing ORDER_PRODUCT intent")

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
            shop_id=shop_id,  # ← required for shop-specific template overrides
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

    # ── LLM Direct Mode Pipeline ─────────────────────────────────────────

    def _run_llm_mode(self, user_id, shop_id, text, company):
        """
        Simplified pipeline for LLM Direct mode.
        Gemini generates the response using the company's context.
        Can also create orders when all entities are collected.
        """
        # ── 1. Cold Memory: Lead + Conversation ──────────────────────────
        conversation = Conversation.objects.filter(
            sender_id=user_id,
            state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY", "LLM_ACTIVE"]
        ).first()

        if not conversation:
            lead = Lead.objects.create(platform_id=user_id)
            conversation = Conversation.objects.create(
                lead=lead, lead_uuid=lead.uuid, sender_id=user_id,
                shop_id=shop_id, state="LLM_ACTIVE"
            )
        else:
            lead = conversation.lead

        state_before = conversation.state
        current_context = conversation.context_data or {}

        # ── 2. Hot Memory: conversation history from Redis ───────────────
        conversation_history = context_manager.get_messages(user_id)

        # ── 3. Call LLM with company context ─────────────────────────────
        llm_result = generate_llm_response(
            text=text,
            company=company,
            conversation_history=conversation_history,
            current_context=current_context,
        )

        bot_text = llm_result["response_text"]
        detected_intent = llm_result.get("detected_intent", "LLM_DIRECT")
        extracted_entities = llm_result.get("extracted_entities", {})

        # ── 4. Accumulate entities into context ──────────────────────────
        for key, value in extracted_entities.items():
            if value:
                current_context[key] = value

        # ── 5. Save User Message (traceability) ─────────────────────────
        user_message = Message.objects.create(
            conversation=conversation,
            sender="USER",
            text=text,
            extracted_intent=detected_intent,
            extracted_entities=extracted_entities,
            is_fallback=False,
            conversation_state_before=state_before,
        )

        # ── 6. Order creation if ready ───────────────────────────────────
        new_state = "LLM_ACTIVE"
        if llm_result.get("order_ready"):
            matched_product = None
            prod_name = current_context.get("product")
            if prod_name:
                try:
                    token = None
                    products = tiktak_service.get_products(shop_id)
                    matched_product, _, _ = tiktak_service.find_product(
                        products, prod_name
                    )
                except Exception as e:
                    logger.error(f"[LLM PIPELINE] Product lookup error: {e}")

            try:
                lead.create_pending_order(
                    shop_id=shop_id,
                    product_id=matched_product["id"] if matched_product else None,
                    variation_id=None,
                    color=current_context.get("color", ""),
                    size=current_context.get("size", ""),
                    address=current_context.get("address", ""),
                    phone_number=current_context.get("phone_number", ""),
                    quantity=int(current_context.get("quantity", 1)),
                )
                new_state = "COMPLETED"
                logger.info(f"[LLM PIPELINE] Order created for lead={lead.id} shop={shop_id}")
            except Exception as e:
                logger.error(f"[LLM PIPELINE] Order creation error: {e}")

        # ── 7. Persist conversation state ────────────────────────────────
        conversation.state = new_state
        conversation.context_data = current_context
        conversation.save()

        # ── 8. Save Bot Message (traceability) ──────────────────────────
        Message.objects.create(
            conversation=conversation, sender="BOT", text=bot_text
        )
        context_manager.add_message(user_id, role="user", text=text, intent=detected_intent)
        context_manager.add_message(user_id, role="bot", text=bot_text)

        user_message.conversation_state_after = new_state
        user_message.save(update_fields=["conversation_state_after"])

        return {
            "text": bot_text,
            "intent": detected_intent,
            "state": new_state,
            "entities": extracted_entities,
            "context": current_context,
            "missing_entities": [],
        }
