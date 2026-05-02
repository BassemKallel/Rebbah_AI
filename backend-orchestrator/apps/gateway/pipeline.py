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
from django.db import transaction
from django.utils import timezone

import time
from apps.crm.models import Lead, Conversation, Message, BotConfiguration, NLUFallbackLog, Company, PipelineLog
from .context_manager import ContextManager
from .response_templates import FALLBACK_PRODUCTS
from .services import ai_service, tiktak_service, dialog_manager
from .services.dialog_manager import detect_language
from .services.azure_storage import azure_storage_service
from .services.template_service import prewarm_order_templates
from .services.llm_response_service import generate_llm_response
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
            image_url=None, image_file=None, platform="messenger",
            mode_override=None) -> dict:
        """
        Process one incoming message through the full pipeline.

        Args:
            user_id:       Unique user identifier (e.g. "messenger:123456")
            shop_id:       Shop identifier for product/config lookup
            text:          Message text (may be empty if image-only)
            image_url:     URL of an image attachment (optional)
            image_file:    Uploaded image file object (optional, POC only)
            platform:      Channel — "messenger" | "instagram" | "poc"
            mode_override: "nlu" or "llm" — overrides company.response_mode for this request only (POC/testing)

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

        # ── 1. Resolve Company (for LLM mode + auth) ──────────────────────
        company = Company.objects.filter(shop_id=shop_id, is_active=True).first()

        # ── LLM Direct Mode — bypass NLU pipeline ─────────────────────────
        effective_mode = mode_override or (getattr(company, 'response_mode', 'nlu') if company else 'nlu')
        if effective_mode == 'llm' and company:
            logger.info(f"[PIPELINE] LLM mode activated for shop={shop_id} (override={bool(mode_override)})")
            return self._run_llm_mode(user_id, shop_id, text, company, image_url=image_url)

        # ── 2. Cold Memory: Lead + Conversation ───────────────────────────
        # Atomic block prevents race conditions when two messages arrive simultaneously
        # for the same user (e.g. Meta retransmission or rapid double-tap).
        # select_for_update() acquires a PostgreSQL FOR UPDATE lock so concurrent
        # threads wait instead of each creating a duplicate Lead + Conversation.
        with transaction.atomic():
            conversation = (
                Conversation.objects
                .select_for_update()
                .filter(
                    sender_id=user_id,
                    state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY", "WAITING_DISAMBIGUATION", "AWAITING_CORRECTION"]
                )
                .select_related('lead')
                .first()
            )
            if not conversation:
                # No active conversation → start fresh; lead will be created lazily on ORDER_PRODUCT
                conversation = Conversation.objects.create(
                    sender_id=user_id,
                    shop_id=shop_id,
                    platform=platform,
                    state="NEW_CONVERSATION"
                )
                lead = None
                is_new_conversation = True
            else:
                # Always derive lead from the conversation to stay consistent
                lead = conversation.lead
                is_new_conversation = False

        # Pre-warm ORDER_PRODUCT / INFORM_INFO templates for new conversations.
        # Runs outside the transaction to avoid coupling Redis I/O to the DB lock.
        # A failure here is non-blocking — get_template() will fall back normally.
        if is_new_conversation:
            try:
                prewarm_order_templates(shop_id)
            except Exception as exc:
                logger.warning(f"[PIPELINE] Template pre-warm failed (non-blocking): {exc}")

        # ── HANDOFF GUARD 1 : Bot désactivé globalement pour la boutique ──────────
        bot_config, _ = BotConfiguration.objects.get_or_create(
            shop_id=shop_id,
            defaults={'bot_enabled': True}
        )
        if not bot_config.bot_enabled:
            logger.info(f"[PIPELINE] Bot DISABLED for shop={shop_id} — saving message, skipping AI")
            Message.objects.create(
                conversation=conversation,
                sender='USER',
                text=text or '[image]',
                conversation_state_before=conversation.state,
                conversation_state_after=conversation.state,
            )
            return {"text": None, "handoff": True, "reason": "bot_disabled", "intent": "HANDOFF"}

        # ── HANDOFF GUARD 2 : Conversation sous contrôle humain ───────────────────
        if conversation.is_human_controlled:
            logger.info(f"[PIPELINE] Conv {conversation.id} is HUMAN-CONTROLLED — saving message, skipping AI")
            Message.objects.create(
                conversation=conversation,
                sender='USER',
                text=text or '[image]',
                conversation_state_before=conversation.state,
                conversation_state_after=conversation.state,
            )
            return {"text": None, "handoff": True, "reason": "human_controlled", "intent": "HANDOFF"}

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
                    lead = None
                    conversation = Conversation.objects.create(
                        sender_id=user_id,
                        shop_id=shop_id, platform=platform, state="NEW_CONVERSATION"
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
                lead = None
                conversation = Conversation.objects.create(
                    sender_id=user_id,
                    shop_id=shop_id, platform=platform, state="NEW_CONVERSATION"
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

        # Default intent when only an image was provided.
        # If a non-order intent was pending (e.g. ASK_PRICE waiting for product),
        # restore it instead of blindly forcing ORDER_PRODUCT.
        if (image_url or image_file) and (extracted_intent == "NOISE" or not text):
            _pending = conversation.context_data.get("_pending_intent")
            if (_pending
                    and conversation.state == "WAITING_USER_REPLY"
                    and _pending in ("ASK_PRICE", "ASK_AVAILABILITY", "ASK_DETAILS", "ASK_DISCOUNT")):
                extracted_intent = _pending
                logger.info(f"[PIPELINE] Image received — restoring pending intent: {_pending}")
            else:
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

        # ── 10c. Progressive Lead Update ──────────────────────────────────
        # Lead is created lazily on first ORDER_PRODUCT intent (purchase intent detected).
        # For non-purchase intents, lead stays None and this block is skipped.
        if extracted_intent in ("ORDER_PRODUCT", "INFORM_INFO") and lead is None:
            lead = Lead.objects.create(platform_id=user_id)
            conversation.lead = lead
            conversation.lead_uuid = lead.uuid
            conversation.save(update_fields=['lead', 'lead_uuid'])
            logger.info(f"[PIPELINE] Lead created lazily on ORDER_PRODUCT — lead.id={lead.id}")

        if lead is not None:
            _lead_dirty = []

            if matched_product:
                _pid = str(matched_product.get("id", ""))
                if _pid and lead.product_id != _pid:
                    lead.product_id = _pid
                    _lead_dirty.append("product_id")

            if vision_variation_id and lead.variation_id != str(vision_variation_id):
                lead.variation_id = str(vision_variation_id)
                _lead_dirty.append("variation_id")

            if not lead.shop_id and shop_id:
                lead.shop_id = shop_id
                _lead_dirty.append("shop_id")

            _ctx_to_lead = {
                "color":        "color",
                "size":         "size",
                "address":      "address",
                "phone_number": "phone_number",
                "quantity":     "quantity",
            }
            for ctx_key, lead_field in _ctx_to_lead.items():
                ctx_val = current_context.get(ctx_key)
                if ctx_val is not None and getattr(lead, lead_field) != ctx_val:
                    setattr(lead, lead_field, ctx_val)
                    _lead_dirty.append(lead_field)

            if _lead_dirty:
                _lead_dirty.append("updated_at")
                lead.save(update_fields=_lead_dirty)
                logger.info(f"[PIPELINE] Lead progressive update: {_lead_dirty}")

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
        # Clean up _pending_intent once it has been fulfilled (product now in context)
        if current_context.get("_pending_intent") and not missing_list:
            current_context.pop("_pending_intent", None)
            logger.info("[PIPELINE] _pending_intent cleared — intent fulfilled")
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

    def _run_llm_mode(self, user_id, shop_id, text, company, image_url=None):
        """
        Simplified pipeline for LLM Direct mode.
        Gemini generates the response using the company's context.
        Supports image input via the vision service (CLIP embeddings).
        Can also create orders when all entities are collected.
        """
        # ── 1. Cold Memory: Lead + Conversation ──────────────────────────
        conversation = Conversation.objects.filter(
            sender_id=user_id,
            state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY", "LLM_ACTIVE", "LLM_CONFIRMING"]
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
        _start_time = time.time()

        # ── 2. Hot Memory: conversation history from Redis ───────────────
        conversation_history = context_manager.get_recent_context(user_id, n=8)

        # ── 2b. Vision: identify product from image ──────────────────────
        matched_image_url = None
        if image_url:
            try:
                vision_result = ai_service.call_vision(shop_id, image_url=image_url)
                if vision_result:
                    variation_id = vision_result.get("variation_id")
                    matched_image_url = vision_result.get("image_url")
                    products = tiktak_service.get_products(shop_id)

                    # Resolve product from variation_id
                    vision_product, color_from_vision, _ = tiktak_service.find_product(
                        products, f"Article_From_Image_{variation_id}"
                    )

                    if vision_product:
                        current_context["product"] = vision_product["name"]
                        if color_from_vision:
                            current_context["color"] = color_from_vision
                        # Inject product info into user message so LLM understands context
                        product_info = f"{vision_product['name']}"
                        if color_from_vision:
                            product_info += f" ({color_from_vision})"
                        if vision_product.get("base_price"):
                            product_info += f" — {vision_product['base_price']} TND"
                        text = f"[Image reçue — produit identifié : {product_info}] {text}".strip()
                        logger.info(f"[LLM PIPELINE] Vision matched: {product_info} (variation_id={variation_id})")
                    else:
                        text = f"[Image reçue — produit non identifié dans le catalogue] {text}".strip()
                        logger.warning(f"[LLM PIPELINE] Vision returned variation_id={variation_id} but no product matched")
                else:
                    text = f"[Image reçue — vision service indisponible] {text}".strip()
            except Exception as e:
                logger.warning(f"[LLM PIPELINE] Vision lookup failed (non-blocking): {e}")
                text = f"[Image reçue] {text}".strip()

        # ── 3. Call LLM with company context ─────────────────────────────
        llm_result = generate_llm_response(
            text=text,
            company=company,
            shop_id=shop_id,
            conversation_history=conversation_history,
            current_context=current_context,
        )

        bot_text = llm_result["response_text"]
        detected_intent = llm_result.get("detected_intent", "LLM_DIRECT")
        extracted_entities = llm_result.get("extracted_entities", {})

        # ── 4. Accumulate entities into context ──────────────────────────
        # Blocked fields: product_id and variation_id must ONLY be resolved
        # via tiktak_service.find_product(), never trusted from the LLM output.
        _LLM_BLOCKED_FIELDS = {"product_id", "variation_id"}
        for key, value in extracted_entities.items():
            if value and key not in _LLM_BLOCKED_FIELDS:
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

        # ── 6. Confirmation gate + Order creation ────────────────────────
        # Phase A — All entities collected → show recap, enter LLM_CONFIRMING
        # Phase B — Client confirms       → create order → COMPLETED
        # Phase C — Client corrects       → update context, stay LLM_CONFIRMING
        new_state = "LLM_ACTIVE"

        _CONFIRM_WORDS = {
            "oui", "yes", "ey", "behi", "ayh", "ok", "okay", "confirme",
            "confirmer", "confirm", "valide", "valider", "d'accord",
            "na3am", "yezzi", "go", "c'est bon", "cest bon", "parfait",
        }

        def _check_stock(products, product_name, color, size):
            """
            Resolve product + variation from catalog AND verify stock.

            Returns:
                (product_dict, variation_dict, error_code)
                error_code: None | 'rupture_de_stock' | 'variation_introuvable' | 'produit_introuvable'
            """
            import unicodedata
            def _norm(s):
                if not s:
                    return ''
                return ''.join(
                    c for c in unicodedata.normalize('NFD', s.lower().strip())
                    if unicodedata.category(c) != 'Mn'
                )

            product_norm = _norm(product_name)
            for p in products:
                if _norm(p['name']) != product_norm:
                    continue

                # Product matched — find best variation
                color_norm = _norm(color)
                size_norm  = _norm(size)
                best_variation = None

                # Exact color + size match
                for v in p.get('variations', []):
                    c_match = not color_norm or _norm(v.get('color', '')) == color_norm
                    s_match = not size_norm  or _norm(v.get('size',  '')) == size_norm
                    if c_match and s_match:
                        best_variation = v
                        break

                # Fallback: color match only (size may not have been specified)
                if best_variation is None:
                    for v in p.get('variations', []):
                        c_match = not color_norm or _norm(v.get('color', '')) == color_norm
                        if c_match:
                            best_variation = v
                            break

                if best_variation is None:
                    return p, None, 'variation_introuvable'

                if best_variation.get('stock_quantity', 0) <= 0:
                    return p, best_variation, 'rupture_de_stock'

                return p, best_variation, None  # OK

            # Product not found by exact name — try fuzzy match
            try:
                matched, _, _ = tiktak_service.find_product(products, product_name)
                if matched:
                    return matched, None, 'variation_introuvable'
            except Exception:
                pass
            return None, None, 'produit_introuvable'


        if state_before == "LLM_CONFIRMING":
            user_text_normalized = text.lower().strip().rstrip("!.,؟?")
            is_confirmation = user_text_normalized in _CONFIRM_WORDS

            if is_confirmation:
                # ── Phase B: Stock check → then create order ──────────────
                try:
                    products_for_check = tiktak_service.get_products(shop_id)  # from Redis cache
                    matched_product, matched_variation, stock_error = _check_stock(
                        products_for_check,
                        current_context.get("product", ""),
                        current_context.get("color", ""),
                        current_context.get("size", ""),
                    )

                    if stock_error == "rupture_de_stock":
                        # Stock = 0 → refuse order, prompt client to pick another option
                        v_info = ""
                        if matched_variation:
                            c = matched_variation.get("color", "")
                            s = matched_variation.get("size", "")
                            v_info = f" ({c} {s})".strip()
                        user_lang = detect_language(text)
                        if user_lang == "ar":
                            bot_text = f"عذراً، هذا المنتج{v_info} غير متوفر حالياً. هل تريد اختيار لون أو مقاس آخر؟"
                        else:
                            bot_text = f"Désolé, ce produit{v_info} est en rupture de stock. Souhaitez-vous choisir une autre couleur ou taille disponible ?"
                        new_state = "LLM_ACTIVE"
                        current_context.pop("size", None)
                        current_context.pop("color", None)
                        logger.info(
                            f"[LLM PIPELINE] Stock check failed (rupture) "
                            f"product='{current_context.get('product')}' variation={matched_variation}"
                        )

                    else:
                        # Stock OK (or variation not found — agent will verify)
                        if stock_error:
                            logger.warning(
                                f"[LLM PIPELINE] Stock check warning: {stock_error} "
                                f"product='{current_context.get('product')}'"
                            )
                        if matched_product:
                            logger.info(
                                f"[LLM PIPELINE] Product resolved: '{matched_product['name']}' "
                                f"id={matched_product['id']} variation={matched_variation}"
                            )
                        lead.create_pending_order(
                            shop_id=shop_id,
                            product_id=matched_product["id"] if matched_product else None,
                            variation_id=matched_variation["id"] if matched_variation else None,
                            color=current_context.get("color", ""),
                            size=current_context.get("size", ""),
                            address=current_context.get("address", ""),
                            phone_number=current_context.get("phone_number", ""),
                            quantity=int(current_context.get("quantity", 1)),
                        )
                        new_state = "COMPLETED"
                        logger.info(f"[LLM PIPELINE] Order confirmed and created — lead={lead.id}")

                except Exception as e:
                    logger.error(f"[LLM PIPELINE] Order creation error: {e}")
                    new_state = "LLM_CONFIRMING"  # Retry on next message
            else:
                # ── Phase C: Client corrected something ───────────────────
                new_state = "LLM_CONFIRMING"
                logger.info(f"[LLM PIPELINE] Correction received in confirming phase: {extracted_entities}")

        elif llm_result.get("order_ready"):
            # ── Phase A: All entities collected → enter confirmation ──────
            new_state = "LLM_CONFIRMING"
            logger.info("[LLM PIPELINE] All entities collected — entering LLM_CONFIRMING phase")

        # ── 7. Persist conversation state ────────────────────────────────
        conversation.state = new_state
        conversation.context_data = current_context
        conversation.save()

        # ── 8. Save Bot Message + Redis ──────────────────────────────────
        Message.objects.create(
            conversation=conversation, sender="BOT", text=bot_text
        )
        context_manager.add_message(user_id, role="user", text=text, intent=detected_intent)
        context_manager.add_message(user_id, role="bot", text=bot_text)

        user_message.conversation_state_after = new_state
        user_message.save(update_fields=["conversation_state_after"])

        # ── 9. PipelineLog ────────────────────────────────────────────────
        _duration = int((time.time() - _start_time) * 1000)
        try:
            PipelineLog.objects.create(
                shop_id       = shop_id,
                sender_id     = user_id,
                mode          = 'llm',
                user_text     = text,
                bot_text      = bot_text,
                detected_intent = detected_intent,
                has_image     = bool(image_url),
                state_before  = state_before,
                state_after   = new_state,
                order_created = (new_state == 'COMPLETED'),
                has_error     = llm_result.get('error', False),
                error_type    = llm_result.get('error_type', 'none') if llm_result.get('error') else 'none',
                error_detail  = str(llm_result.get('error_detail', '')),
                duration_ms   = _duration,
            )
        except Exception as log_err:
            logger.warning(f"[PIPELINE] Failed to write PipelineLog: {log_err}")

        return {
            "text": bot_text,
            "intent": detected_intent,
            "state": new_state,
            "entities": extracted_entities,
            "context": current_context,
            "missing_entities": [],
            "matched_image_url": matched_image_url,
        }
