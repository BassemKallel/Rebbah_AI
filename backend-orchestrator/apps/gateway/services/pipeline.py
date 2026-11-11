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
import os
import random
import re
import time
import unicodedata
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from apps.crm.models import Lead, Conversation, Message, BotConfiguration, Company, PipelineLog, PendingMessage
from apps.crm.models.analytics import ItemVector
from apps.crm.models.billing import BillingWallet, LLMUsageLog
from apps.crm.services.order_service import create_pending_order
from .context_manager import ContextManager
from . import ai_service
from .azure_storage import azure_storage_service
from .agents import run_orchestrator
from .entity_normalizer import normalize_context_data, normalize_entities, normalize_order_items

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
            mode_override=None, sender_name: Optional[str] = None) -> dict:
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
        _start_time = time.time()

        # ── Setup Log Collector ───────────────────────────────────────────
        _log_buffer, _handler, _root_logger = self._setup_log_collector()

        try:
            # ── Upload image to Azure if file provided ─────────────────────
            image_url = self._handle_image_upload(shop_id, image_file, image_url)

            # ── 1. Resolve Company ─────────────────────────────────────────
            company = self._resolve_company(shop_id)
            if not company:
                return self._inactive_company_response(shop_id)

            # ── 0. Vérification du quota financier (BillingWallet) ─────────
            quota_error_response = self._check_billing_quota(company, shop_id)
            if quota_error_response:
                return quota_error_response

            # ── 1. Cold Memory: Lead + Conversation ────────────────────────
            conversation, lead = self._resolve_conversation_and_lead(
                user_id, shop_id, sender_name
            )
            state_before = conversation.state
            current_context = normalize_context_data(conversation.context_data or {})

            # ── Bypasse de l'IA (Sécurité & Handoff Humain) ─────────────────
            # 1. Si la conversation est sous contrôle humain (Takeover)
            # 2. Si aucune configuration de bot n'est liée à la boutique
            # 3. Si le bot est explicitement désactivé globalement
            if conversation.is_human_controlled:
                logger.info(f"[PIPELINE] Conversation {conversation.id} is under human control. Skipping AI response.")
                return {
                    "text": "",
                    "intent": "HUMAN_TAKEOVER",
                    "state": state_before,
                    "entities": {},
                    "context": current_context,
                    "missing_entities": []
                }
            
            if not company.bot_config or not company.bot_config.bot_enabled:
                logger.info(f"[PIPELINE] Bot is disabled or not configured for shop={shop_id}. Skipping AI agents.")
                return {
                    "text": "",
                    "intent": "HUMAN_TAKEOVER",
                    "state": state_before,
                    "entities": {},
                    "context": current_context,
                    "missing_entities": []
                }

            # ── 1.5 Guardrail: Bloquer les clics carrousel obsolètes si une commande est active ──
            if text and "le produit :" in text:
                is_checkout_active = (current_context.get("_active_agent") == "CHECKOUT" and bool(current_context.get("items")))
                is_confirming = (state_before == "LLM_CONFIRMING")
                
                if is_confirming or is_checkout_active:
                    logger.info(f"[PIPELINE] Carousel click ignored because checkout/confirming is active for conversation={conversation.id}")
                    warning_text = (
                        "3andek talbiya 9a3ed t7ader fiha tawa. Kmelha walla ab3ath 'annuler' bech t3awed men jdid stp. 🙏\n\n"
                        "(Vous avez déjà une commande en cours de finalisation. Veuillez la terminer ou taper 'annuler' pour recommencer.)"
                    )
                    
                    # 1. Enregistrer le message de l'utilisateur (sans appeler l'IA)
                    user_message = Message.objects.create(
                        conversation=conversation,
                        sender="USER",
                        text=text,
                        conversation_state_before=state_before,
                    )
                    
                    # 2. Persister l'état inchangé
                    conversation.state = state_before
                    conversation.context_data = current_context
                    conversation.save()
                    
                    # 3. Enregistrer le message du bot et mettre à jour Redis
                    bot_msg = self._save_bot_message_and_redis(
                        user_id=user_id,
                        shop_id=shop_id,
                        conversation=conversation,
                        bot_text=warning_text,
                        text=text,
                        detected_intent="ORDER_PRODUCT",
                        active_agent="CHECKOUT"
                    )
                    
                    # 4. Finaliser les logs de l'utilisateur
                    user_message.conversation_state_after = state_before
                    user_message.save(update_fields=["conversation_state_after"])
                    
                    # 5. Enregistrer le PipelineLog
                    _duration = int((time.time() - _start_time) * 1000)
                    _root_logger.removeHandler(_handler)
                    _collected_logs = '\n'.join(_log_buffer)
                    
                    mock_llm_result = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "error": False,
                    }
                    self._write_pipeline_log(
                        shop_id=shop_id,
                        sender_id=user_id,
                        text=text,
                        bot_text=warning_text,
                        detected_intent="ORDER_PRODUCT",
                        image_url=image_url,
                        state_before=state_before,
                        new_state=state_before,
                        llm_result=mock_llm_result,
                        duration_ms=_duration,
                        collected_logs=_collected_logs
                    )
                    
                    # 6. Si on est en phase de confirmation, on ré-attache le carrousel Oui/Non
                    carousel_elements_to_send = None
                    if state_before == "LLM_CONFIRMING":
                        confirm_card = {
                            "title": "Confirmer la commande ? 🛒",
                            "subtitle": "Cliquez ci-dessous pour confirmer ou annuler",
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "Oui, je confirme ! ✅",
                                    "payload": "Oui, c'est parfait !"
                                },
                                {
                                    "type": "postback",
                                    "title": "Non, j'annule ❌",
                                    "payload": "non annule samhni"
                                }
                            ]
                        }
                        carousel_elements_to_send = [confirm_card]
                    
                    return self._build_result_dict(
                        bot_text=warning_text,
                        detected_intent="ORDER_PRODUCT",
                        new_state=state_before,
                        extracted_entities={},
                        current_context=current_context,
                        matched_image_url=None,
                        carousel_elements_to_send=carousel_elements_to_send
                    )

            # Détection du produit depuis les clics carrousel ("Commander" ou "Plus d'infos")
            if text and "le produit :" in text:
                parts = text.split("le produit :")
                if len(parts) > 1:
                    product_name = parts[1].strip()
                    current_context["_last_viewed_product"] = product_name
                    logger.info(f"[PIPELINE] Extracted _last_viewed_product='{product_name}' from carousel button click.")

            # Détection automatique : si le client mentionne un produit du catalogue dans son texte brut
            if text:
                try:
                    catalog_items = list(ItemVector.objects.filter(shop_id=shop_id))
                    for item in catalog_items:
                        meta = item.metadata or {}
                        prod_name = meta.get("name")
                        if prod_name:
                            # Comparaison normalisée insensible aux accents et caractères spéciaux
                            norm_prod = self._normalize_match_text(prod_name)
                            norm_text = self._normalize_match_text(text)
                            if len(norm_prod) > 3 and len(norm_text) > 3 and (norm_prod in norm_text or norm_text in norm_prod):
                                current_context["_last_viewed_product"] = prod_name
                                logger.info(f"[PIPELINE] Détection automatique du produit '{prod_name}' dans le texte utilisateur.")
                                break
                except Exception as e:
                    logger.warning(f"[PIPELINE] Échec de l'auto-détection du produit depuis le texte : {e}")

            # ── 2. Hot Memory: conversation history from Redis ───────────────
            conversation_history = context_manager.get_recent_context(user_id, n=10, shop_id=shop_id)

            # ── 2b. Vision: identify product from image (Visual RAG) ───────
            text, matched_image_url, carousel_elements_to_send = self._handle_visual_rag(
                shop_id, image_url, text
            )

            # ── 3. Call Orchestrator ────────────────────────────────────────
            llm_result = run_orchestrator(
                user_message=text,
                image_url=image_url,
                conversation=conversation,
                company=company,
                history=conversation_history,
            )

            # ── Circuit Breaker: handle Gemini API errors gracefully ──────
            if llm_result.get("error"):
                return self._handle_circuit_breaker(
                    user_id=user_id,
                    shop_id=shop_id,
                    conversation=conversation,
                    current_context=current_context,
                    text=text,
                    image_url=image_url,
                    state_before=state_before,
                    llm_result=llm_result,
                    _start_time=_start_time,
                    _log_buffer=_log_buffer,
                    _handler=_handler,
                    _root_logger=_root_logger
                )

            # ── Gemini succeeded: reset error counter ─────────────────────
            context_manager.reset_error_count(user_id, shop_id)

            # ── 4. Accumulate entities into context ──────────────────────
            active_agent = llm_result.get("active_agent")
            if active_agent:
                current_context["_active_agent"] = active_agent

            if llm_result.get("checkout_abandoned"):
                logger.info("[PIPELINE] Checkout abandonment detected. Clearing local context of non-system entities.")
                keys_to_clear = [k for k in current_context.keys() if not k.startswith('_')]
                for k in keys_to_clear:
                    current_context.pop(k, None)
                conversation.state = "LLM_CANCELED"
                conversation.completed_at = timezone.now()
            else:
                self._accumulate_entities(current_context, llm_result.get("extracted_entities", {}))

            # ── 4.5 Update or Create Lead Dynamically ───────────────────
            lead = self._update_lead(lead, conversation, current_context, shop_id)

            # ── 5. Save User Message (traceability) ─────────────────────
            user_message = self._save_user_message(conversation, text, state_before, llm_result)

            bot_text = llm_result["response_text"]

            # ── Handle Text-Based Carousel ─────────────────────────────────
            carousel_elements_to_send = self._handle_text_carousel(
                shop_id, llm_result.get("carousel_items", []), carousel_elements_to_send
            )

            # Extraction automatique du produit depuis les recommandations retournées par l'IA (carousel_items)
            logger.debug(f"[PIPELINE DEBUG] carousel_items={llm_result.get('carousel_items')} | _last_viewed_product={current_context.get('_last_viewed_product')}")
            if llm_result.get("carousel_items") and not current_context.get("_last_viewed_product"):
                try:
                    first_item_id = llm_result["carousel_items"][0]
                    matched_item = ItemVector.objects.filter(shop_id=shop_id, item_id=first_item_id).first()
                    logger.debug(f"[PIPELINE DEBUG] first_item_id={first_item_id!r} | matched={matched_item}")
                    if matched_item:
                        meta = matched_item.metadata or {}
                        prod_name = meta.get("name")
                        if prod_name:
                            current_context["_last_viewed_product"] = prod_name
                            logger.info(f"[PIPELINE] Extracted _last_viewed_product='{prod_name}' from carousel_items.")
                except Exception as e:
                    logger.warning(f"[PIPELINE] Failed to extract product from carousel: {e}")

            # ── 6. Confirmation gate + Order creation ────────────────────
            is_confirmed_by_llm = bool(llm_result.get("order_confirmed", False))
            
            # Regex ultra-robuste des mots de validation bilingues (Derja, Arabizi, Français, Anglais)
            confirm_regex = re.compile(
                r'^(?:ey|ay|oui|yes|yep|ok|okay|mrig[el]{1,2}|d\'?accord|c\'?est\s+bon|na[ck]ed|نعم|اي|أكيد|اكيد|موافق|صحيح|عديها)\b', 
                re.IGNORECASE
            )
            # Validation déterministe serveur uniquement pour les messages de confirmation très courts (max 3 mots)
            is_short_msg = len(text.strip().split()) <= 3
            is_confirmed_by_server = bool(
                state_before == "LLM_CONFIRMING" and 
                is_short_msg and 
                confirm_regex.match(text.strip().lower())
            )
            
            # Une confirmation n'est valide que si la conversation était déjà en cours de confirmation ou prête
            is_confirmation = False
            if state_before == "LLM_CONFIRMING":
                is_confirmation = is_confirmed_by_llm or is_confirmed_by_server
            elif state_before == "LLM_ACTIVE" and llm_result.get("order_ready"):
                is_confirmation = is_confirmed_by_llm

            new_state, bot_text = self._process_order_confirmation(
                lead=lead,
                conversation=conversation,
                current_context=current_context,
                text=text,
                shop_id=shop_id,
                is_confirmation=is_confirmation,
                bot_text=bot_text,
                llm_result=llm_result,
                state_before=state_before,
                extracted_entities=llm_result.get("extracted_entities", {}),
                company=company
            )
            
            # ── Add Yes/No Carousel for Order Confirmation ─────────────────
            if new_state == "LLM_CONFIRMING":
                confirm_instruction = "\n\n👉 *Veuillez cliquer sur Oui pour confirmer ou Non pour annuler la commande.*"
                if confirm_instruction not in bot_text:
                    bot_text += confirm_instruction
                
                confirm_card = {
                    "title": "Confirmer la commande ? 🛒",
                    "subtitle": "Cliquez ci-dessous pour confirmer ou annuler",
                    "buttons": [
                        {
                            "type": "postback",
                            "title": "Oui, je confirme ! ✅",
                            "payload": "Oui, c'est parfait !"
                        },
                        {
                            "type": "postback",
                            "title": "Non, j'annule ❌",
                            "payload": "non annule samhni"
                        }
                    ]
                }
                if carousel_elements_to_send is None:
                    carousel_elements_to_send = []
                if not any(el.get("title") == "Confirmer la commande ? 🛒" for el in carousel_elements_to_send):
                    carousel_elements_to_send.append(confirm_card)


            # ── 7. Persist conversation state ────────────────────────────
            conversation.state = new_state
            conversation.context_data = current_context
            conversation.save()

            # ── 8. Save Bot Message + Redis ──────────────────────────────
            bot_msg = self._save_bot_message_and_redis(
                user_id=user_id,
                shop_id=shop_id,
                conversation=conversation,
                bot_text=bot_text,
                text=text,
                detected_intent=llm_result.get("detected_intent", "LLM_DIRECT"),
                active_agent=llm_result.get("active_agent")
            )

            # ── 8b. Facturation (BillingLog & Wallet) ────────────────────
            self._process_billing_usage(company, bot_msg, llm_result)

            user_message.conversation_state_after = new_state
            user_message.save(update_fields=["conversation_state_after"])

            # ── 9. PipelineLog ────────────────────────────────────────────
            _duration = int((time.time() - _start_time) * 1000)
            _root_logger.removeHandler(_handler)
            _collected_logs = '\n'.join(_log_buffer)
            self._write_pipeline_log(
                shop_id=shop_id,
                sender_id=user_id,
                text=text,
                bot_text=bot_text,
                detected_intent=llm_result.get("detected_intent", "LLM_DIRECT"),
                image_url=image_url,
                state_before=state_before,
                new_state=new_state,
                llm_result=llm_result,
                duration_ms=_duration,
                collected_logs=_collected_logs
            )

            return self._build_result_dict(
                bot_text=bot_text,
                detected_intent=llm_result.get("detected_intent", "LLM_DIRECT"),
                new_state=new_state,
                extracted_entities=llm_result.get("extracted_entities", {}),
                current_context=current_context,
                matched_image_url=matched_image_url,
                carousel_elements_to_send=carousel_elements_to_send
            )

        finally:
            # Always ensure the root logger handler is detached
            try:
                _root_logger.removeHandler(_handler)
            except Exception:
                pass

    # ── Private Helper Methods ────────────────────────────────────────────

    def _setup_log_collector(self):
        _log_buffer = []

        class _ListHandler(logging.Handler):
            def emit(self, record):
                _log_buffer.append(f"[{record.levelname}] {self.format(record)}")

        _handler = _ListHandler()
        _handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
        _handler.setLevel(logging.DEBUG)
        _root_logger = logging.getLogger()
        _root_logger.addHandler(_handler)
        return _log_buffer, _handler, _root_logger

    def _handle_image_upload(self, shop_id, image_file, image_url):
        if image_file:
            uploaded_url = azure_storage_service.upload_image(image_file, prefix=shop_id)
            if uploaded_url:
                return uploaded_url
        return image_url

    def _resolve_company(self, shop_id):
        return Company.objects.filter(shop_id=shop_id, is_active=True).first()

    def _inactive_company_response(self, shop_id):
        logger.error(f"[PIPELINE] No active company found for shop={shop_id}")
        return {
            "text": "Désolé, cette boutique n'est pas active.",
            "intent": "NOISE",
            "state": "COMPLETED",
            "entities": {},
            "context": {},
            "missing_entities": []
        }

    def _check_billing_quota(self, company, shop_id):
        if hasattr(company, 'wallet') and company.wallet:
            if company.wallet.is_limit_exceeded():
                logger.warning(f"[BILLING] Quota épuisé pour {shop_id}. Passage en manuel.")
                if company.bot_config and company.bot_config.bot_enabled:
                    company.bot_config.bot_enabled = False
                    company.bot_config.bot_disabled_at = timezone.now()
                    company.bot_config.save()
                return {
                    "text": "Notre assistant virtuel est temporairement désactivé pour cette boutique. Un agent humain vous répondra bientôt.",
                    "intent": "OTHER",
                    "state": "NEW_CONVERSATION",
                    "entities": {},
                    "context": {},
                    "missing_entities": []
                }
        return None

    def _resolve_conversation_and_lead(self, user_id, shop_id, sender_name: Optional[str] = None):
        conversation = Conversation.objects.filter(
            sender_id=user_id,
            shop_id=shop_id,
            state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY", "LLM_ACTIVE", "LLM_CONFIRMING"]
        ).first()

        if not conversation:
            lead = Lead.objects.create(
                platform_id=user_id,
                name=sender_name or None,
                shop_id=shop_id,
            )
            conversation = Conversation.objects.create(
                lead=lead, lead_uuid=lead.uuid, sender_id=user_id,
                shop_id=shop_id, state="LLM_ACTIVE"
            )
        else:
            lead = conversation.lead
            if sender_name and lead and not lead.name:
                lead.name = sender_name
                lead.save(update_fields=["name"])
        return conversation, lead

    def _handle_visual_rag(self, shop_id, image_url, text):
        matched_image_url = None
        carousel_elements_to_send = None

        if image_url:
            try:
                vision_results = ai_service.call_vision(shop_id, image_url=image_url, limit=3)
                if vision_results:
                    matched_item = vision_results[0]
                    is_exact_match = matched_item.get("is_exact_match", False)

                    if is_exact_match:
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
                                    },
                                    {
                                        "type": "postback",
                                        "title": "Plus d'infos ℹ️",
                                        "payload": f"Donne-moi plus d'informations sur le produit : {product_name}"
                                    }
                                ]
                            }]
                            
                        desc = str(meta.get("name", "cet article"))
                        if meta.get("price"):
                            desc += f" à {meta['price']} TND"
                            
                        text = f"[INFO SYSTÈME : Le client a envoyé une photo. Le système visuel a trouvé une correspondance exacte en stock : {desc}. Une carte visuelle du produit vient d'être affichée au client. Continue la discussion en l'aidant à l'acheter !] {text}".strip()
                        logger.info(f"[LLM PIPELINE] Vision RAG exact match: {desc}")
                    
                    else:
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
                                        },
                                        {
                                            "type": "postback",
                                            "title": "Plus d'infos ℹ️",
                                            "payload": f"Donne-moi plus d'informations sur le produit : {product_name}"
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

        return text, matched_image_url, carousel_elements_to_send

    def _accumulate_entities(self, current_context: Dict[str, Any], extracted_entities: Dict[str, Any]) -> None:
        _LLM_BLOCKED_FIELDS = {"variation_id"}
        normalized_entities = normalize_entities(extracted_entities)
        for key, value in normalized_entities.items():
            if value and key not in _LLM_BLOCKED_FIELDS:
                if key == "items":
                    current_context[key] = self._merge_order_items(current_context.get(key), value)
                    # Sauvegarder automatiquement le nom du produit comme dernier produit actif discuté
                    if value and isinstance(value, list) and len(value) > 0:
                        current_context["_last_viewed_product"] = value[0].get("product_name")
                else:
                    current_context[key] = value

        # Auto-population of basket from _last_viewed_product in checkout phase
        if current_context.get("_active_agent") == "CHECKOUT":
            has_basket_items = bool(current_context.get("items"))
            has_product = bool(current_context.get("product"))
            last_viewed = current_context.get("_last_viewed_product")
            
            if not has_basket_items and not has_product and last_viewed:
                # Resolve quantity from context/extracted_entities or default to 1
                qty = self._safe_int(current_context.get("quantity") or normalized_entities.get("quantity") or 1)
                current_context["items"] = [{
                    "product_name": last_viewed,
                    "quantity": qty,
                    "attributes": self._extract_item_attributes(current_context)
                }]
                logger.info(f"[PIPELINE] Automatically pre-populated basket with active product '{last_viewed}' (qty={qty}) for checkout.")

    def _merge_order_items(self, existing: Any, incoming: Any) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        index_by_key: Dict[str, int] = {}

        for item in normalize_order_items(existing) + normalize_order_items(incoming):
            item_key = self._order_item_identity(item)
            if item_key in index_by_key:
                existing_item = merged[index_by_key[item_key]]
                new_qty = item.get("quantity", 1)
                existing_qty = existing_item.get("quantity", 1)
                
                # Garde-fou : Si la nouvelle quantité est 1 (valeur de repli par défaut)
                # et que le panier contient déjà une quantité supérieure, on conserve la quantité existante.
                if new_qty == 1 and existing_qty > 1:
                    item["quantity"] = existing_qty
                
                merged[index_by_key[item_key]] = item
            else:
                index_by_key[item_key] = len(merged)
                merged.append(item)
        return merged

    def _order_item_identity(self, item: Dict[str, Any]) -> str:
        product_id = str(item.get("product_id") or "").strip().lower()
        if product_id:
            return f"id:{product_id}"
        product_name = self._normalize_match_text(str(item.get("product_name") or ""))
        attributes = item.get("attributes") or {}
        attributes_key = "|".join(f"{key}:{attributes[key]}" for key in sorted(attributes))
        return f"name:{product_name}|attrs:{attributes_key}"

    def _update_lead(self, lead, conversation, current_context, shop_id):
        if not lead:
            lead = Lead.objects.create(
                platform_id=conversation.sender_id,
                name=current_context.get("name", ""),
                shop_id=shop_id
            )
            conversation.lead = lead
            conversation.save(update_fields=['lead'])
        
        lead.extracted_data = self._build_lead_extracted_data(current_context)
        if current_context.get("name") and not lead.name:
            lead.name = current_context.get("name")
        lead.save(update_fields=['name', 'extracted_data'])
        return lead

    def _save_user_message(self, conversation, text, state_before, llm_result):
        return Message.objects.create(
            conversation=conversation,
            sender="USER",
            text=text,
            extracted_intent=llm_result.get("detected_intent", "LLM_DIRECT"),
            extracted_entities=llm_result.get("extracted_entities", {}),
            conversation_state_before=state_before,
            agent=llm_result.get("active_agent"),
        )

    def _handle_text_carousel(self, shop_id, llm_carousel_items, carousel_elements_to_send):
        if llm_carousel_items and not carousel_elements_to_send:
            try:
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
                                    },
                                    {
                                        "type": "postback",
                                        "title": "Plus d'infos ℹ️",
                                        "payload": f"Donne-moi plus d'informations sur le produit : {product_name}"
                                    }
                                ]
                            })
                    logger.info(f"[LLM PIPELINE] Appending text-based carousel with {len(carousel_elements_to_send)} items")
            except Exception as e:
                logger.warning(f"[LLM PIPELINE] Failed to build text-based carousel: {e}")
        return carousel_elements_to_send

    def _handle_circuit_breaker(self, user_id, shop_id, conversation, current_context, text, image_url, state_before, llm_result, _start_time, _log_buffer, _handler, _root_logger):
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

        phone_match = re.search(r'\b[24579]\d{7}\b', text)
        if phone_match:
            current_context["phone_number"] = phone_match.group(0)
            conversation.context_data = current_context
            conversation.save(update_fields=['context_data'])
            logger.info(f"[CIRCUIT BREAKER] Fallback Regex extracted phone: {phone_match.group(0)}")

        if error_count >= 3:
            conversation.is_human_controlled = True
            conversation.save(update_fields=['is_human_controlled'])
            context_manager.reset_error_count(user_id, shop_id)
            bot_text = _HANDOFF_PHRASE
            logger.warning(
                f"[CIRCUIT BREAKER] Human handoff triggered for sender={user_id} "
                f"shop={shop_id} after {error_count} consecutive errors."
            )
        else:
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
                    f"[CIRCUIT BREAKER] Message queued for retry — sender={user_id} shop={shop_id}"
                )
            except Exception as q_err:
                logger.error(f"[CIRCUIT BREAKER] Failed to queue message: {q_err}")

        Message.objects.create(
            conversation=conversation, sender="USER", text=text,
            extracted_intent="LLM_ERROR", conversation_state_before=state_before,
            agent="ERROR",
        )
        Message.objects.create(
            conversation=conversation, sender="BOT", text=bot_text,
            agent="ERROR",
        )
        context_manager.add_message(user_id, role="user", text=text, shop_id=shop_id)
        context_manager.add_message(user_id, role="bot", text=bot_text, shop_id=shop_id)

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

    def _build_lead_extracted_data(
        self,
        current_context: Dict[str, Any],
        items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        normalized_context = normalize_context_data(current_context)
        excluded_keys = {"product", "quantity"} if items is not None else set()
        extracted_data = {
            key: value
            for key, value in normalized_context.items()
            if not str(key).startswith("_") and key not in excluded_keys
        }
        if items is not None:
            extracted_data["items"] = items
        elif "items" in extracted_data:
            extracted_data["items"] = normalize_order_items(extracted_data["items"])
        return extracted_data

    def _extract_items_from_context(self, current_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        normalized_context = normalize_context_data(current_context)
        items = normalize_order_items(normalized_context.get("items"))
        if items:
            return items

        product = normalized_context.get("product")
        if product:
            return [{
                "product_name": str(product),
                "quantity": self._safe_int(normalized_context.get("quantity", 1)),
                "attributes": self._extract_item_attributes(normalized_context),
            }]
        return []

    def _extract_item_attributes(self, current_context: Dict[str, Any]) -> Dict[str, Any]:
        attributes: Dict[str, Any] = {}
        for key in ("color", "size", "variant"):
            if current_context.get(key):
                attributes[key] = current_context[key]
        return attributes

    def _prepare_order_items(
        self,
        current_context: Dict[str, Any],
        shop_id: str
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        requested_items = self._extract_items_from_context(current_context)
        if not requested_items:
            return [], []

        catalog_items = list(ItemVector.objects.filter(shop_id=shop_id))
        prepared_items: List[Dict[str, Any]] = []
        item_errors: List[str] = []

        for requested_item in requested_items:
            matched_item = self._match_catalog_item(requested_item, catalog_items)
            requested_name = requested_item.get("product_name", "Produit demandé")
            if not matched_item:
                item_errors.append(str(requested_name))
                continue

            meta = matched_item.metadata or {}
            if meta.get("in_stock") is False:
                item_errors.append(str(meta.get("name") or requested_name))
                continue

            prepared_items.append({
                "product_id": str(matched_item.item_id),
                "product_name": str(meta.get("name") or requested_name),
                "quantity": self._safe_int(requested_item.get("quantity", 1)),
                "price": self._parse_catalog_price(meta.get("price") or meta.get("base_price")),
                "attributes": requested_item.get("attributes") or {},
            })

        return prepared_items, item_errors

    def _match_catalog_item(self, requested_item: Dict[str, Any], catalog_items: List[ItemVector]) -> Optional[ItemVector]:
        requested_product_id = str(requested_item.get("product_id") or "").strip()
        requested_name = self._normalize_match_text(str(requested_item.get("product_name") or ""))

        for catalog_item in catalog_items:
            if requested_product_id and requested_product_id == str(catalog_item.item_id):
                return catalog_item

        if not requested_name:
            return None

        requested_words = set(requested_name.split())
        best_match: Optional[ItemVector] = None
        best_score = 0
        for catalog_item in catalog_items:
            meta = catalog_item.metadata or {}
            catalog_name = self._normalize_match_text(str(meta.get("name") or ""))
            catalog_desc = self._normalize_match_text(str(meta.get("description") or ""))
            if not catalog_name:
                continue
            if len(requested_name) > 3 and (requested_name in catalog_name or catalog_name in requested_name):
                return catalog_item

            catalog_words = set((catalog_name + " " + catalog_desc).split())
            score = len(requested_words.intersection(catalog_words))
            if score > best_score:
                best_score = score
                best_match = catalog_item

        return best_match if best_score > 0 else None

    def _normalize_match_text(self, value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
        normalized = re.sub(r"[^a-zA-Z0-9\s]+", " ", ascii_value)
        return re.sub(r"\s+", " ", normalized.lower()).strip()

    def _parse_catalog_price(self, value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        if isinstance(value, (int, float, Decimal)):
            return float(value)
        match = re.search(r"\d+(?:[.,]\d+)?", str(value))
        if not match:
            return None
        return float(match.group(0).replace(",", "."))

    def _safe_int(self, value: Any, default: int = 1) -> int:
        try:
            parsed = int(str(value).strip())
            return parsed if parsed > 0 else default
        except (TypeError, ValueError):
            return default

    def _build_unavailable_items_message(self, item_errors: List[str], text: str, company=None) -> str:
        items_text = ", ".join(item_errors)
        is_arabic = bool(re.search(r'[\u0600-\u06FF]', text))
        
        is_standard_arabic = False
        if company and getattr(company, "bot_config", None):
            lang_rules = getattr(company.bot_config, "language_rules", "").lower()
            is_standard_arabic = any(keyword in lang_rules for keyword in [
                "arabe pur", "arabe standard", "fusha", "classique", "littéraire", 
                "pas de tunisien", "sans tunisien", "pas de dialecte", "sans dialecte"
            ])

        if is_arabic:
            if is_standard_arabic:
                return f"عذراً، هذا المنتج غير واضح أو غير متوفر في الكتالوج: {items_text}. هل يمكنك اختيار منتج آخر من الكتالوج المتوفر؟"
            return f"سامحني، المنتج هذا موش واضح أو موش متوفر في الكاتالوغ: {items_text}. تنجم تختار منتج آخر من المتوفر؟"
        return (
            f"Désolé, je n'ai pas pu confirmer ce produit dans le catalogue: {items_text}. "
            "Pouvez-vous choisir un produit disponible ?"
        )

    def _process_order_confirmation(self, lead, conversation, current_context, text, shop_id, is_confirmation, bot_text, llm_result, state_before, extracted_entities, company=None):
        if llm_result.get("checkout_abandoned"):
            logger.info("[LLM PIPELINE] Checkout cancellation/abandonment detected. Forcing state to LLM_CANCELED.")
            conversation.completed_at = timezone.now()
            return "LLM_CANCELED", bot_text

        new_state = "LLM_ACTIVE"

        if is_confirmation:
            try:
                product_name = current_context.get("product", "").lower().strip()
                stock_ok = True
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
                    _order_lang = "ar" if re.search(r'[\u0600-\u06FF]', text) else "fr"
                    if _order_lang == "ar":
                        bot_text = f"عذراً، منتج '{out_of_stock_product}' غير متوفر حالياً. اختار منتج آخر من كتالوجنا!"
                    else:
                        bot_text = f"Désolé, le produit '{out_of_stock_product}' est actuellement en rupture de stock. Souhaitez-vous choisir un autre produit ?"
                    new_state = "LLM_ACTIVE"
                    current_context.pop("product", None)
                    logger.info(f"[LLM PIPELINE] RAG Stock check: '{out_of_stock_product}' is out of stock")

                else:
                    items, item_errors = self._prepare_order_items(current_context, shop_id)
                    if item_errors:
                        bot_text = self._build_unavailable_items_message(item_errors, text, company=company)
                        new_state = "LLM_ACTIVE"
                        logger.info(f"[LLM PIPELINE] Blocking order confirmation, item errors={item_errors}")
                        return new_state, bot_text

                    extracted_data = self._build_lead_extracted_data(current_context, items)
                        
                    create_pending_order(
                        lead=lead,
                        shop_id=shop_id,
                        extracted_data=extracted_data,
                        items=items or None
                    )
                    new_state = "COMPLETED"
                    conversation.completed_at = timezone.now()
                    logger.info(f"[LLM PIPELINE] Order confirmed and created — lead={lead.id}")
                    logger.info(f"[LLM PIPELINE] Final confirmation generated by LLM: '{bot_text}'")

            except Exception as e:
                logger.error(f"[LLM PIPELINE] Order creation error: {e}")
                new_state = "LLM_CONFIRMING"
        else:
            if llm_result.get("order_ready"):
                new_state = "LLM_CONFIRMING"
                logger.info("[LLM PIPELINE] All entities collected or updated — entering/remaining in LLM_CONFIRMING phase")
            else:
                new_state = "LLM_ACTIVE"

        return new_state, bot_text

    def _save_bot_message_and_redis(self, user_id, shop_id, conversation, bot_text, text, detected_intent, active_agent):
        bot_msg = Message.objects.create(
            conversation=conversation, sender="BOT", text=bot_text,
            agent=active_agent,
        )
        context_manager.add_message(user_id, role="user", text=text, intent=detected_intent, shop_id=shop_id)
        context_manager.add_message(user_id, role="bot", text=bot_text, shop_id=shop_id)
        return bot_msg

    def _process_billing_usage(self, company, bot_msg, llm_result):
        prompt_tokens = llm_result.get('prompt_tokens', 0)
        completion_tokens = llm_result.get('completion_tokens', 0)
        model_name = llm_result.get('model_name', 'gemini-2.5-flash')
        
        price_input = Decimal(os.getenv("GEMINI_INPUT_PRICE_PER_1M", "0.075"))
        price_output = Decimal(os.getenv("GEMINI_OUTPUT_PRICE_PER_1M", "0.300"))
        
        cost_input = (Decimal(prompt_tokens) / Decimal(1_000_000)) * price_input
        cost_output = (Decimal(completion_tokens) / Decimal(1_000_000)) * price_output
        total_cost = cost_input + cost_output
        
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
        
        wallet.total_messages_count += 1
        old_count = wallet.total_messages_count - 1
        if old_count == 0:
            wallet.average_cost_per_message = total_cost
        else:
            wallet.average_cost_per_message = (
                (wallet.average_cost_per_message * old_count) + total_cost
            ) / wallet.total_messages_count

        wallet.save(update_fields=['current_month_usage', 'total_messages_count', 'average_cost_per_message', 'last_updated'])

    def _write_pipeline_log(self, shop_id, sender_id, text, bot_text, detected_intent, image_url, state_before, new_state, llm_result, duration_ms, collected_logs):
        try:
            PipelineLog.objects.create(
                shop_id=shop_id,
                sender_id=sender_id,
                mode='llm',
                user_text=text,
                bot_text=bot_text,
                detected_intent=detected_intent,
                has_image=bool(image_url),
                state_before=state_before,
                state_after=new_state,
                order_created=(new_state == 'COMPLETED'),
                has_error=llm_result.get('error', False),
                error_type=llm_result.get('error_type', 'none') if llm_result.get('error') else 'none',
                error_detail=str(llm_result.get('error_detail', '')),
                duration_ms=duration_ms,
                log_messages=collected_logs,
                prompt_tokens=llm_result.get('prompt_tokens', 0),
                completion_tokens=llm_result.get('completion_tokens', 0),
            )
        except Exception as log_err:
            logger.warning(f"[PIPELINE] Failed to write PipelineLog: {log_err}")

    def _build_result_dict(self, bot_text, detected_intent, new_state, extracted_entities, current_context, matched_image_url, carousel_elements_to_send):
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
