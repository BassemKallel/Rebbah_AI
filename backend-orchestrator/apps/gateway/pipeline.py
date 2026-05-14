"""
pipeline.py — Core Message Processing Pipeline

Single entry point for all message processing, eliminating duplication
between MetaWebhookView and MessengerWebhookPOC.

Steps:
  1. Resolve Company + Billing Quota
  2. Cold Memory: Lead + Conversation
  3. Hot Memory: Redis conversation history
  4. Visual RAG: Image-to-Image search (if image attached)
  5. LLM Response (Gemini) with RAG catalog injected in system prompt
  6. Context Accumulation + Entity Extraction
  7. Order State Machine (COLLECTING → CONFIRMING → COMPLETED)
  8. Persist State + Save Messages to DB
"""
import logging
import random
import re
import time
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.crm.models import Lead, Conversation, Message, BotConfiguration, Company, PipelineLog, PendingMessage
from .context_manager import ContextManager
from .services import ai_service
from .services.azure_storage import azure_storage_service
from .services.llm_response_service import generate_llm_response

logger = logging.getLogger(__name__)

context_manager = ContextManager()

# Grace period: how long a completed conversation stays open for corrections
GRACE_PERIOD_MINUTES = 2

# ── LLM Mode constants ──────────────────────────────────────────────────

# Words that count as order confirmation in any supported language/dialect
_LLM_CONFIRM_WORDS: frozenset = frozenset({
    "oui", "yes", "ey", "behi", "ayh", "ok", "okay", "confirme", "confirmé", "confirmée",
    "confirmer", "confirm", "valide", "valider", "d'accord", "mrigl", "rigel", "mrigla",
    "c bon", "c'est bon", "cest bon", "sava", "sa va", "na3am", "yezzi", "go", "parfait",
})


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
        # ── Upload image to Azure if file provided ─────────────────────────
        uploaded_url = None
        if image_file:
            uploaded_url = azure_storage_service.upload_image(image_file, prefix=shop_id)
            if uploaded_url:
                image_url = uploaded_url

        # ── 1. Resolve Company ─────────────────────────────────────────────
        company = Company.objects.filter(shop_id=shop_id, is_active=True).first()
        if not company:
            logger.error(f"[PIPELINE] No active company found for shop={shop_id}")
            return {"text": "Désolé, cette boutique n'est pas active.", "intent": "NOISE", "state": "COMPLETED", "entities": {}, "context": {}, "missing_entities": []}

        # ── 0. Vérification du quota financier (BillingWallet) ─────────────
        if hasattr(company, 'wallet') and company.wallet:
            if company.wallet.is_limit_exceeded():
                logger.warning(f"[BILLING] Quota épuisé pour {shop_id}. Passage en manuel.")
                if company.bot_config and company.bot_config.bot_enabled:
                    company.bot_config.bot_enabled = False
                    company.bot_config.bot_disabled_at = timezone.now()
                    company.bot_config.save()
                return {"text": "Notre assistant virtuel est temporairement désactivé pour cette boutique. Un agent humain vous répondra bientôt.", "intent": "OTHER", "state": "NEW_CONVERSATION", "entities": {}, "context": {}, "missing_entities": []}

        # ── Log collector: captures every logger call during this run ─────
        _log_buffer = []

        class _ListHandler(logging.Handler):
            def emit(self, record):
                _log_buffer.append(f"[{record.levelname}] {self.format(record)}")

        _handler = _ListHandler()
        _handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
        _handler.setLevel(logging.DEBUG)
        _root_logger = logging.getLogger()  # Root logger captures ALL modules
        _root_logger.addHandler(_handler)
        # ── 1. Cold Memory: Lead + Conversation ────────────────────────────────
        # Filter by (sender_id, shop_id) for strict multi-tenant isolation.
        # Two different shops cannot share the same conversation even if the
        # sender_id were identical (edge case in tests; impossible with Meta IDs).
        conversation = Conversation.objects.filter(
            sender_id=user_id,
            shop_id=shop_id,
            state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY", "LLM_ACTIVE", "LLM_CONFIRMING"]
        ).first()

        if not conversation:
            # Toujours créer un nouveau Lead pour chaque nouvelle conversation
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

        # ── 2. Hot Memory: conversation history from Redis ───────────────────
        # shop_id passed for tenant-scoped Redis key: chat_context:{shop_id}:{user_id}
        conversation_history = context_manager.get_recent_context(user_id, n=10, shop_id=shop_id)

        # ── 2b. Vision: identify product from image (Visual RAG) ───────
        matched_image_url = None
        carousel_elements_to_send = None
        
        if image_url:
            try:
                vision_results = ai_service.call_vision(shop_id, image_url=image_url, limit=3)
                if vision_results:
                    matched_item = vision_results[0]
                    is_exact_match = matched_item.get("is_exact_match", False)

                    if is_exact_match:
                        # ── Exact Match ──
                        matched_image_url = matched_item.get("image_url")
                        meta = matched_item.get("metadata", {})
                        if matched_image_url:
                            product_name = str(meta.get("name", "Produit sélectionné"))
                            carousel_elements_to_send = [{
                                "title": product_name[:80],
                                "subtitle": f"{meta.get('price', '')} TND".strip()[:80],
                                "image_url": matched_image_url,
                                "buttons": [
                                    {
                                        "type": "postback",
                                        "title": "Commander 🛒",
                                        "payload": f"Je veux commander le produit : {product_name}"
                                    }
                                ]
                            }]
                            
                        desc = str(meta.get("name", "cet article"))
                        if meta.get("price"):
                            desc += f" à {meta['price']} TND"
                            
                        text = f"[INFO SYSTÈME : Le client a envoyé une photo. Le système visuel a trouvé une correspondance exacte en stock : {desc}. Une carte visuelle du produit vient d'être affichée au client. Continue la discussion en l'aidant à l'acheter !] {text}".strip()
                        logger.info(f"[LLM PIPELINE] Vision RAG exact match: {desc}")
                    
                    else:
                        # ── Soft Fallback ──
                        carousel_elements_to_send = []
                        names = []
                        for item in vision_results:
                            img_url = item.get("image_url")
                            meta = item.get("metadata", {})
                            if img_url:
                                product_name = str(meta.get("name", "Produit similaire"))
                                names.append(product_name)
                                carousel_elements_to_send.append({
                                    "title": product_name[:80],
                                    "subtitle": f"{meta.get('price', '')} TND".strip()[:80],
                                    "image_url": img_url,
                                    "buttons": [
                                        {
                                            "type": "postback",
                                            "title": "Commander 🛒",
                                            "payload": f"Je veux commander le produit : {product_name}"
                                        }
                                    ]
                                })
                                
                        text = f"[INFO SYSTÈME : Le client a envoyé une photo. Le système n'a pas trouvé le produit exact, mais a affiché un carrousel avec ces articles similaires : {', '.join(names)}. Informe le client que tu n'as pas le modèle exact mais propose-lui ces alternatives !] {text}".strip()
                        logger.info(f"[LLM PIPELINE] Vision RAG soft fallback with {len(carousel_elements_to_send)} items.")
                else:
                    text = f"[Image reçue — aucun produit similaire trouvé dans la base de données] {text}".strip()
            except Exception as e:
                logger.warning(f"[LLM PIPELINE] Vision RAG lookup failed (non-blocking): {e}")
                text = f"[Image reçue] {text}".strip()


        # ── 3. Call LLM with company context ─────────────────────────────
        llm_result = generate_llm_response(
            text=text,
            company=company,
            shop_id=shop_id,
            conversation_history=conversation_history,
            current_context=current_context,
            state_before=state_before,
        )

        bot_text = llm_result["response_text"]
        detected_intent = llm_result.get("detected_intent", "LLM_DIRECT")
        extracted_entities = llm_result.get("extracted_entities", {})
        
        # ── Handle Text-Based Carousel ─────────────────────────────────────
        llm_carousel_items = llm_result.get("carousel_items", [])
        if llm_carousel_items and not carousel_elements_to_send:
            try:
                from apps.crm.models.analytics import ItemVector
                rag_items = ItemVector.objects.filter(shop_id=shop_id, item_id__in=llm_carousel_items)
                if rag_items:
                    carousel_elements_to_send = []
                    for item in rag_items:
                        if item.image_url:
                            meta = item.metadata or {}
                            product_name = str(meta.get("name", "Produit"))
                            carousel_elements_to_send.append({
                                "title": product_name[:80],
                                "subtitle": f"{meta.get('price', '')} TND".strip()[:80],
                                "image_url": item.image_url,
                                "buttons": [
                                    {
                                        "type": "postback",
                                        "title": "Commander 🛒",
                                        "payload": f"Je veux commander le produit : {product_name}"
                                    }
                                ]
                            })
                    logger.info(f"[LLM PIPELINE] Appending text-based carousel with {len(carousel_elements_to_send)} items")
            except Exception as e:
                logger.warning(f"[LLM PIPELINE] Failed to build text-based carousel: {e}")

        # ── Circuit Breaker: handle Gemini API errors gracefully ──────────
        if llm_result.get("error"):

            _FALLBACK_PHRASES = [
                "Laissez-moi juste vérifier ça avec notre équipe, je reviens vers vous dans quelques instants 😊",
                "Notre système est un peu lent en ce moment, un petit instant s'il vous plaît...",
                "Je vérifie les informations disponibles, je vous réponds très rapidement !",
            ]
            _HANDOFF_PHRASE = (
                "Notre système rencontre des difficultés techniques. "
                "Je vous mets en relation avec un conseiller humain qui prendra le relais immédiatement. "
                "Merci pour votre patience ! 🙏"
            )

            error_count = context_manager.increment_error_count(user_id, shop_id)
            logger.warning(
                f"[CIRCUIT BREAKER] Gemini error #{error_count} for sender={user_id} "
                f"shop={shop_id} error_type={llm_result.get('error_type')}"
            )

            # ── Regex Fallback: Essayer d'extraire le numéro même si le LLM a planté ──
            phone_match = re.search(r'\b[24579]\d{7}\b', text)
            if phone_match:
                current_context["phone_number"] = phone_match.group(0)
                conversation.context_data = current_context
                conversation.save(update_fields=['context_data'])
                logger.info(f"[CIRCUIT BREAKER] Fallback Regex extracted phone: {phone_match.group(0)}")


            if error_count >= 3:
                # ── Handoff: escalade vers agent humain ───────────────────
                conversation.is_human_controlled = True
                conversation.save(update_fields=['is_human_controlled'])
                context_manager.reset_error_count(user_id, shop_id)
                bot_text = _HANDOFF_PHRASE
                logger.warning(
                    f"[CIRCUIT BREAKER] Human handoff triggered for sender={user_id} "
                    f"shop={shop_id} after {error_count} consecutive errors."
                )
            else:
                # ── Graceful Fallback: message naturel + mise en queue ─────
                bot_text = random.choice(_FALLBACK_PHRASES)
                try:
                    PendingMessage.objects.create(
                        shop_id=shop_id,
                        sender_id=user_id,
                        conversation=conversation,
                        user_text=text,
                        image_url=image_url or '',
                    )
                    logger.info(
                        f"[CIRCUIT BREAKER] Message queued for retry — "
                        f"sender={user_id} shop={shop_id}"
                    )
                except Exception as q_err:
                    logger.error(f"[CIRCUIT BREAKER] Failed to queue message: {q_err}")

            # Save and return the graceful response immediately
            Message.objects.create(
                conversation=conversation, sender="USER", text=text,
                extracted_intent="LLM_ERROR", conversation_state_before=state_before,
            )
            Message.objects.create(
                conversation=conversation, sender="BOT", text=bot_text
            )
            context_manager.add_message(user_id, role="user", text=text, shop_id=shop_id)
            context_manager.add_message(user_id, role="bot", text=bot_text, shop_id=shop_id)

            # Write PipelineLog for error monitoring
            _root_logger.removeHandler(_handler)
            _duration = int((time.time() - _start_time) * 1000)
            try:
                PipelineLog.objects.create(
                    shop_id=shop_id, sender_id=user_id, mode='llm',
                    user_text=text, bot_text=bot_text,
                    detected_intent='LLM_ERROR', state_before=state_before,
                    state_after=conversation.state,
                    has_error=True,
                    error_type=llm_result.get('error_type', 'api_error'),
                    error_detail=str(llm_result.get('error_detail', '')),
                    duration_ms=_duration,
                    log_messages='\n'.join(_log_buffer),
                )
            except Exception:
                pass
            return {
                "text": bot_text, "intent": "LLM_ERROR",
                "state": conversation.state, "entities": {},
                "context": current_context, "missing_entities": [],
                "matched_image_url": None,
            }

        # ── Gemini succeeded: reset error counter ─────────────────────────
        context_manager.reset_error_count(user_id, shop_id)

        # ── 4. Accumulate entities into context ──────────────────────────
        # variation_id is an internal key — never trust from LLM output.
        _LLM_BLOCKED_FIELDS = {"variation_id"}
        for key, value in extracted_entities.items():
            if value and key not in _LLM_BLOCKED_FIELDS:
                current_context[key] = value

        # ── 4.5 Update or Create Lead Dynamically ───────────────────────
        if not lead:
            lead = Lead.objects.create(platform_id=user_id, name=current_context.get("name", ""), shop_id=shop_id)
            conversation.lead = lead
            conversation.save(update_fields=['lead'])
        
        # Always update lead data in real-time
        lead.extracted_data = current_context.copy()
        if current_context.get("name") and not lead.name:
            lead.name = current_context.get("name")
        lead.save(update_fields=['name', 'extracted_data'])

        # ── 5. Save User Message (traceability) ─────────────────────────
        user_message = Message.objects.create(
            conversation=conversation,
            sender="USER",
            text=text,
            extracted_intent=detected_intent,
            extracted_entities=extracted_entities,
            conversation_state_before=state_before,
        )

        # ── 6. Confirmation gate + Order creation ────────────────────────
        # Phase A — All entities collected → show recap, enter LLM_CONFIRMING
        # Phase B — Client confirms       → RAG stock check → create order → COMPLETED
        # Phase C — Client corrects       → update context, stay LLM_CONFIRMING
        new_state = "LLM_ACTIVE"

        user_text_normalized = text.lower().strip().rstrip("!.,؟?")
        words = user_text_normalized.split()

        # Mots de confirmation explicites (client doit VRAIMENT confirmer)
        has_confirm_word = (
            user_text_normalized in _LLM_CONFIRM_WORDS or
            any(w in _LLM_CONFIRM_WORDS for w in words)
        )

        # Mots de correction/refus: "pas", "non", "la", "ghalta", "mش", "faux"
        _DENY_WORDS = {"non", "no", "la", "le", "pas", "ghalta", "faux", "false", "mش", "mech"}
        has_deny_word = any(w in _DENY_WORDS for w in words)

        # La confirmation nécessite un mot positif OU l'accord de Gemini (order_ready=true), ET l'absence de négation
        is_confirmation = (has_confirm_word or llm_result.get("order_ready")) and not has_deny_word

        # On rentre dans le bloc de finalisation si on était déjà en CONFIRMING,
        # OU BIEN si c'est une confirmation claire.
        if state_before == "LLM_CONFIRMING" or (is_confirmation and llm_result.get("order_ready")):

            if is_confirmation:
                # ── Phase B: RAG Stock check → then create order ──────────────
                try:
                    from apps.crm.models.analytics import ItemVector

                    # Check in_stock flag from the RAG catalog (set by the merchant)
                    product_name = current_context.get("product", "").lower().strip()
                    stock_ok = True  # Default: accept order if product not found in RAG
                    out_of_stock_product = None

                    if product_name:
                        rag_items = ItemVector.objects.filter(shop_id=shop_id)
                        for rag_item in rag_items:
                            meta = rag_item.metadata or {}
                            rag_name = meta.get("name", "").lower().strip()
                            if rag_name and rag_name in product_name or product_name in rag_name:
                                if meta.get("in_stock") is False:
                                    stock_ok = False
                                    out_of_stock_product = meta.get("name", product_name)
                                break

                    if not stock_ok:
                        # RAG catalog says product is out of stock
                        _order_lang = "ar" if re.search(r'[\u0600-\u06FF]', text) else "fr"
                        if _order_lang == "ar":
                            bot_text = f"عذراً، منتج '{out_of_stock_product}' غير متوفر حالياً. اختار منتج آخر من كتالوجنا!"
                        else:
                            bot_text = f"Désolé, le produit '{out_of_stock_product}' est actuellement en rupture de stock. Souhaitez-vous choisir un autre produit ?"
                        new_state = "LLM_ACTIVE"
                        current_context.pop("product", None)
                        logger.info(f"[LLM PIPELINE] RAG Stock check: '{out_of_stock_product}' is out of stock")

                    else:
                        # Build extracted_data: dumping all entities from the LLM
                        extracted_data = current_context.copy()
                        
                        # RÉSILIENCE : On garde le produit en clair au cas où
                        if current_context.get("product"):
                            extracted_data["unmatched_product"] = current_context["product"]
                        


                        from apps.crm.services.order_service import create_pending_order
                        
                        # ── Fallback Panier ──
                        # Si le LLM utilise l'ancien format (clé 'product' au lieu du tableau 'items')
                        items = current_context.get("items", [])
                        if not items and current_context.get("product"):
                            items = [{
                                "product_name": current_context.get("product"),
                                "quantity": int(current_context.get("quantity", 1))
                            }]
                            
                        create_pending_order(
                            lead=lead,
                            shop_id=shop_id,
                            extracted_data=extracted_data,
                            items=items
                        )
                        new_state = "COMPLETED"
                        conversation.completed_at = timezone.now()
                        logger.info(f"[LLM PIPELINE] Order confirmed and created — lead={lead.id}")

                        # ── Override bot_text avec message de confirmation final ──
                        # Gemini tend à régénérer un récap en réponse au "ok" au lieu
                        # d'envoyer un vrai message de confirmation — on corrige ici.
                        import re
                        _order_lang = "ar" if re.search(r'[\u0600-\u06FF]', text) else "fr"
                        _product_name = current_context.get("product", "")
                        _address = current_context.get("address", "")
                        if _order_lang == "ar":
                            bot_text = (
                                f"يعيشك! طلبيتك تأكدت بنجاح 🎉\n"
                                f"{'جو: ' + _product_name + chr(10) if _product_name else ''}"
                                f"{'عنوان: ' + _address + chr(10) if _address else ''}"
                                f"التوصيل في 2-3 أيام عمل، والدفع عند الاستلام. شكراً على ثقتك! 🙏"
                            )
                        else:
                            bot_text = (
                                f"Parfait, votre commande est confirmée ! 🎉\n"
                                f"{'Produit : ' + _product_name + chr(10) if _product_name else ''}"
                                f"{'Adresse : ' + _address + chr(10) if _address else ''}"
                                f"Livraison sous 2-3 jours ouvrables, paiement à la livraison. Merci ! 🙏"
                            )

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
        bot_msg = Message.objects.create(
            conversation=conversation, sender="BOT", text=bot_text
        )
        context_manager.add_message(user_id, role="user", text=text, intent=detected_intent, shop_id=shop_id)
        context_manager.add_message(user_id, role="bot", text=bot_text, shop_id=shop_id)

        # ── 8b. Facturation (BillingLog & Wallet) ────────────────────────
        prompt_tokens = llm_result.get('prompt_tokens', 0)
        completion_tokens = llm_result.get('completion_tokens', 0)
        model_name = llm_result.get('model_name', 'gemini-2.5-flash')
        
        # Prix par défaut: Gemini Flash $0.075 / 1M input, $0.30 / 1M output
        import os
        from decimal import Decimal
        price_input = Decimal(os.getenv("GEMINI_INPUT_PRICE_PER_1M", "0.075"))
        price_output = Decimal(os.getenv("GEMINI_OUTPUT_PRICE_PER_1M", "0.300"))
        
        cost_input = (Decimal(prompt_tokens) / Decimal(1_000_000)) * price_input
        cost_output = (Decimal(completion_tokens) / Decimal(1_000_000)) * price_output
        total_cost = cost_input + cost_output
        
        from apps.crm.models.billing import BillingWallet, LLMUsageLog
        LLMUsageLog.objects.create(
            company=company,
            message=bot_msg,
            model_name=model_name,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            cost_input=cost_input,
            cost_output=cost_output,
            total_cost=total_cost
        )
        
        wallet, _ = BillingWallet.objects.get_or_create(company=company)
        wallet.current_month_usage += total_cost
        wallet.save(update_fields=['current_month_usage', 'last_updated'])

        user_message.conversation_state_after = new_state
        user_message.save(update_fields=["conversation_state_after"])

        # ── 9. PipelineLog ────────────────────────────────────────────────
        _duration = int((time.time() - _start_time) * 1000)
        # Detach the per-request log collector before writing to DB
        _root_logger.removeHandler(_handler)
        _collected_logs = '\n'.join(_log_buffer)
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
                log_messages  = _collected_logs,
                prompt_tokens = llm_result.get('prompt_tokens', 0),
                completion_tokens = llm_result.get('completion_tokens', 0),
            )
        except Exception as log_err:
            logger.warning(f"[PIPELINE] Failed to write PipelineLog: {log_err}")

        result_dict = {
            "text": bot_text,
            "intent": detected_intent,
            "state": new_state,
            "entities": extracted_entities,
            "context": current_context,
            "missing_entities": [],
            "matched_image_url": matched_image_url,
        }
        
        if carousel_elements_to_send:
            result_dict["carousel_elements"] = carousel_elements_to_send
            
        return result_dict
