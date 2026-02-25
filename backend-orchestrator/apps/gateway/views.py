import json
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.crm.models import Lead, Conversation, Message
from .context_manager import ContextManager
from .anonymization import anonymize_message
from .response_templates import (
    TEMPLATES, MISSING_ENTITY_TEMPLATES, REQUIRED_ORDER_ENTITIES,
    DISAMBIGUATION_TEMPLATE, OUT_OF_STOCK_TEMPLATE,
    ORDER_CONFIRMED_TEMPLATE, ORDER_CONFIRMED_NO_REF_TEMPLATE
)

# Service URLs — built from settings (env vars)
NLU_URL         = settings.NLU_SERVICE_URL.rstrip('/') + settings.NLU_PREDICT_PATH
VISION_URL      = settings.VISION_SERVICE_URL.rstrip('/') + settings.VISION_SEARCH_PATH
VISION_URL_FILE = settings.VISION_SERVICE_URL.rstrip('/') + '/search-similar-upload'
MOCK_API_PRODUCTS_URL = settings.MOCK_API_BASE_URL.rstrip('/') + settings.MOCK_API_PRODUCTS_PATH
MOCK_API_SHOP_HEADER  = settings.MOCK_API_SHOP_ID_HEADER
REQUEST_TIMEOUT       = settings.EXTERNAL_REQUEST_TIMEOUT

# Map intent → relevant entity labels (filter GLiNER results)
INTENT_ENTITY_FILTER = {
    "ORDER_PRODUCT": {"product", "color", "size", "address", "phone_number", "quantity"},
    "ASK_PRICE": {"product"},
    "ASK_AVAILABILITY": {"product", "color", "size"},
    "INFORM_INFO": {"address", "phone_number", "color", "size"},
    "ASK_DELIVERY": set(),
    "GREETING": set(),
    "UNKNOWN": set(),
    "NOISE": set(),
    "ASK_DETAILS": {"product"},
    "ASK_DISCOUNT": set(),
    "ASK_LOCATION": set(),
    "CANCEL_ORDER": set(),
    "CHECK_PACKAGE": set(),
    "COMPLAINT": set(),
    "CONFIRM_DENY": set(),
    "TRACK_ORDER": {"phone_number"},
}

# Initialize Hot Memory
context_manager = ContextManager()

class MessengerWebhookPOC(APIView):
    """
    Simulates the webhook receiving messages from WhatsApp or Messenger.
    """
    def post(self, request):
        user_id = request.data.get("user_id")
        shop_id = request.data.get("shop_id", "default_shop")

        # Accepte à la fois JSON imbriqué ET form-data plat
        # JSON : {"message": {"text": "...", "image_url": "..."}}
        # form-data : text=..., image_url=...
        message_data = request.data.get("message", {})
        if isinstance(message_data, str):
            import json as _json
            try:
                message_data = _json.loads(message_data)
            except Exception:
                message_data = {}
        text      = message_data.get("text", "")      or request.data.get("text", "")
        image_url = message_data.get("image_url")      or request.data.get("image_url")

        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Cold Memory: Get or Create Lead and active Conversation
        lead, _ = Lead.objects.get_or_create(platform_id=user_id)
        
        # Assuming one active conversation for simplicity (can be enhanced based on state OR timeframe)
        conversation = Conversation.objects.filter(lead=lead, state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY", "WAITING_DISAMBIGUATION"]).first()
        if not conversation:
            conversation = Conversation.objects.create(lead=lead, shop_id=shop_id, state="NEW_CONVERSATION")

        # 2. Add User Message to Hot Memory (Redis)
        context_manager.add_message(user_id, role="user", text=text)

        extracted_intent = "UNKNOWN"
        extracted_entities = {}
        is_error = False
        nlu_raw_entities = []  # Save raw NLU entities for contextual mapping later

        # 3. Vision API (if image provided — URL ou fichier uploadé)
        matched_image_url = None
        vision_variation_id = None   # Variable locale, jamais persistée en DB
        image_file = request.FILES.get("image")
        if image_file or image_url:
            try:
                if image_file:
                    vision_res = requests.post(
                        VISION_URL_FILE,
                        files={"image": (image_file.name, image_file.read(), image_file.content_type)},
                        data={"shop_id": shop_id, "limit": 1},
                        timeout=REQUEST_TIMEOUT
                    )
                else:
                    vision_res = requests.post(
                        VISION_URL,
                        json={"image_url": image_url, "limit": 1, "shop_id": shop_id},
                        timeout=REQUEST_TIMEOUT
                    )
                if vision_res.status_code == 200:
                    vision_data = vision_res.json()
                    if vision_data.get("results"):
                        top_match = vision_data["results"][0]
                        # Identifie le produit parent
                        extracted_entities["product"] = f"Article_From_Image_{top_match['product_id']}"
                        # Variables locales uniquement — jamais dans extracted_entities
                        matched_image_url = top_match.get("image_url")
                        vision_variation_id = top_match.get("variation_id")
            except requests.RequestException as e:
                is_error = True
                print(f"Vision API Error: {e}")

        # 4. NLU API (if text provided)
        if text:
            try:
                # Send original text to NLU
                # NLU will:
                # 1. Anonymize for TunBERT (intent classification)
                # 2. Use original text for GLiNER (entity extraction)
                nlu_res = requests.post(NLU_URL, json={"message": text}, timeout=REQUEST_TIMEOUT)
                if nlu_res.status_code == 200:
                    nlu_data = nlu_res.json()
                    intent_obj = nlu_data.get("intent", {})
                    extracted_intent = intent_obj.get("intent", "UNKNOWN")
                    
                    # Save raw NLU entities for contextual mapping
                    nlu_raw_entities = nlu_data.get("entities", [])
                    
                    # Filter entities based on intent (ignore irrelevant entities from GLiNER)
                    # For INFORM_INFO during an active order flow: only accept the entities
                    # that the bot is currently waiting for — prevents premature capture of
                    # address/phone while the bot is still asking for color or size.
                    if (extracted_intent == "INFORM_INFO"
                            and conversation.missing_entities
                            and conversation.state == "WAITING_USER_REPLY"):
                        relevant_entities = set(conversation.missing_entities)
                    else:
                        relevant_entities = INTENT_ENTITY_FILTER.get(extracted_intent, set())
                    _valid_sizes = {"S", "M", "L", "XL", "2XL", "3XL", "4XL", "ONE SIZE", "XS", "XXL", "XXXL"}
                    for ent in nlu_raw_entities:
                        if ent["label"] in relevant_entities:
                            # Reject address entities that are too short or look like a size
                            if ent["label"] == "address":
                                ent_val = ent["text"].strip()
                                if len(ent_val) < 3 or ent_val.upper() in _valid_sizes:
                                    continue
                            extracted_entities[ent["label"]] = ent["text"]
                        
            except requests.RequestException as e:
                is_error = True
                print(f"NLU API Error: {e}")
                
            # Fallback for POC: if NLU missed the product but recognized intent
            # Only run if product not yet identified in accumulated context
            if "product" not in extracted_entities and not image_url and "product" not in conversation.context_data:
                text_lower = text.lower()
                common_products = ["pull", "t-shirt", "veste", "pantalon", "robe"]
                for cp in common_products:
                    if cp in text_lower:
                        extracted_entities["product"] = cp
                        break
                        
        # If user sent an image (URL or file upload) but NLU failed to get the intent, default to ORDER
        if (image_url or image_file) and (extracted_intent == "UNKNOWN" or not text):
            extracted_intent = "ORDER_PRODUCT"

        # 5. Save the User Message to PostgreSQL
        Message.objects.create(
            conversation=conversation,
            sender="USER",
            text=text if text else f"[Image: {image_url}]",
            extracted_intent=extracted_intent,
            extracted_entities=extracted_entities,
            is_error=is_error
        )

        # 6. Accumulate entities in Conversation context
        current_context = conversation.context_data
        # Protect already-identified entities: once product or color is known, don't overwrite
        # with a new GLiNER/fallback detection from a later message in the same flow
        if "product" in current_context:
            extracted_entities.pop("product", None)
        if "color" in current_context:
            extracted_entities.pop("color", None)
        current_context.update(extracted_entities)
        # Toujours nettoyer les clés internes — jamais persistées en DB
        current_context.pop("_vision_variation_id", None)
        conversation.context_data = current_context

        # 7. State Machine & Response Generation
        previous_state = conversation.state
        
        # ── CONTEXTUAL MAPPING ──────────────────────────────────────
        # If we're WAITING_USER_REPLY, try to extract the expected entity
        # Smart matching: Try to match detected entity types to missing order fields
        contextual_match = False  # Flag to track if we matched expected pattern
        
        # Only run contextual mapping for intents that represent a user answer
        # Skip for side-question intents (ASK_PRICE, ASK_AVAILABILITY, ASK_DELIVERY, etc.)
        _contextual_mapping_intents = {"INFORM_INFO", "NOISE", "ORDER_PRODUCT", "UNKNOWN"}
        
        if (previous_state == "WAITING_USER_REPLY"
                and conversation.missing_entities
                and extracted_intent in _contextual_mapping_intents):
            first_missing = conversation.missing_entities[0] if conversation.missing_entities else None
            text_clean = text.strip().upper()
            
            # Strategy 1: Look for GLiNER-detected entities matching missing fields
            for ent in nlu_raw_entities:
                ent_label = ent["label"]
                if ent_label not in extracted_entities and ent_label in conversation.missing_entities:
                    # Found a detected entity that matches a missing field!
                    extracted_entities[ent_label] = ent["text"]
                    current_context[ent_label] = ent["text"]
                    contextual_match = True
                    break
            
            # Strategy 2: Validate user input against expected patterns for missing fields
            # Try each missing field to see if input matches its pattern
            if not contextual_match:
                for missing_field in conversation.missing_entities:
                    if missing_field not in extracted_entities:
                        if missing_field == "size":
                            # Valid sizes: S, M, L, XL, 2XL, 3XL, etc.
                            valid_sizes = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "ONE SIZE"]
                            if text_clean in valid_sizes:
                                extracted_entities[missing_field] = text_clean
                                current_context[missing_field] = text_clean
                                contextual_match = True
                                break
                        
                        elif missing_field == "quantity":
                            # Valid quantity: integers 1-999
                            try:
                                qty = int(text_clean)
                                if 1 <= qty <= 999:
                                    extracted_entities[missing_field] = str(qty)
                                    current_context[missing_field] = str(qty)
                                    contextual_match = True
                                    break
                            except ValueError:
                                pass
                        
                        elif missing_field == "phone_number":
                            # Accept if it looks like a phone (digits + Tunisia prefixes)
                            import re
                            phone_pattern = r'^(\+216|00216|216)?[\s.-]?[0-9\s.-]{7,}$'
                            if re.match(phone_pattern, text_clean):
                                extracted_entities[missing_field] = text
                                current_context[missing_field] = text
                                contextual_match = True
                                break
                        
                        elif missing_field in ["address", "color"]:
                            # For address: require at least 3 chars and not a size abbreviation
                            # For color: accept any non-empty text
                            val = text.strip()
                            if missing_field == "address":
                                valid_sizes = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "ONE SIZE"]
                                if val and len(val) >= 3 and val.upper() not in valid_sizes:
                                    extracted_entities[missing_field] = val
                                    current_context[missing_field] = val
                                    contextual_match = True
                                    break
                            elif val:
                                extracted_entities[missing_field] = val
                                current_context[missing_field] = val
                                contextual_match = True
                                break
        
        # If we matched an expected value through contextual mapping, override NOISE → INFORM_INFO
        if contextual_match and extracted_intent == "NOISE":
            extracted_intent = "INFORM_INFO"
        
        bot_response_text = TEMPLATES.get("UNKNOWN")
        missing_list = []
        new_state = previous_state
        
        prod_name = current_context.get("product")
        matched_product = None
        
        # We fetch Mock API first if we have a product, because we might need its real name instead of the UUID
        if prod_name:
            try:
                mock_api_url = MOCK_API_PRODUCTS_URL
                headers = {MOCK_API_SHOP_HEADER: shop_id}
                resp = requests.get(mock_api_url, headers=headers, timeout=REQUEST_TIMEOUT)
                
                if resp.status_code == 200:
                    products = resp.json()
                    
                    if prod_name.startswith("Article_From_Image_"):
                        # Exact product_id match from Vision service
                        target_id = prod_name.split("Article_From_Image_")[1]
                        effective_variation_id = vision_variation_id
                        for p in products:
                            if p["id"] == target_id:
                                matched_product = p
                                # Pré-remplir couleur ET taille depuis la variation identifiée
                                if effective_variation_id:
                                    for v in p.get("variations", []):
                                        if v["id"] == effective_variation_id:
                                            current_context["color"] = v["color"]
                                            # La taille n'est PAS déduite : elle dépend
                                            # du client, pas de l'image envoyée
                                            break
                                break
                    else:
                        # Keyword match — collect ALL matching products
                        keyword_candidates = [
                            p for p in products
                            if p["name"].lower() in prod_name.lower()
                            or prod_name.lower() in p["name"].lower()
                        ]
                        if len(keyword_candidates) == 1:
                            matched_product = keyword_candidates[0]
                        elif len(keyword_candidates) > 1:
                            # Ambiguity: store candidates for disambiguation
                            current_context["candidates"] = keyword_candidates
                            current_context["pending_intent"] = extracted_intent
            except Exception as e:
                print(f"Mock API Error: {e}")
                print(f"[MOCK API] URL={mock_api_url} shop_id={shop_id} status={resp.status_code if 'resp' in dir() else 'N/A'}")

        # ── DISAMBIGUATION RESOLUTION (user is picking from a list) ──────────
        if previous_state == "WAITING_DISAMBIGUATION":
            candidates = current_context.get("candidates", [])
            resolved = None
            if text and candidates:
                text_lower = text.lower()
                # Try numeric selection: "1", "le 2", "numéro 3" …
                for i, c in enumerate(candidates):
                    if str(i + 1) in text:
                        resolved = c
                        break
                # Try product name match
                if not resolved:
                    for c in candidates:
                        if c["name"].lower() in text_lower or text_lower in c["name"].lower():
                            resolved = c
                            break
                # Try color match against variations
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
                # Still cannot resolve — re-ask with the same list
                new_state = "WAITING_DISAMBIGUATION"
                items_list = "\n".join([
                    f"{i+1}. {c['name']} ({c['base_price']} TND)"
                    for i, c in enumerate(candidates)
                ])
                bot_response_text = DISAMBIGUATION_TEMPLATE.replace("{count}", str(len(candidates))).replace("{list}", items_list)
                conversation.state = new_state
                conversation.context_data = current_context
                conversation.missing_entities = []
                conversation.save()
                Message.objects.create(conversation=conversation, sender="BOT", text=bot_response_text)
                context_manager.add_message(user_id, role="bot", text=bot_response_text)
                return Response({"status": "success", "bot_response": {"text": bot_response_text, "internal_debug": {"intent_detected": extracted_intent, "new_state": new_state, "candidates_count": len(candidates)}}})

        # ── NEW AMBIGUITY DETECTED THIS TURN ────────────────────────────────────
        if current_context.get("candidates") and not matched_product:
            new_state = "WAITING_DISAMBIGUATION"
            candidates = current_context["candidates"]
            items_list = "\n".join([
                f"{i+1}. {c['name']} ({c['base_price']} TND)"
                for i, c in enumerate(candidates)
            ])
            bot_response_text = DISAMBIGUATION_TEMPLATE.replace("{count}", str(len(candidates))).replace("{list}", items_list)
            conversation.state = new_state
            conversation.context_data = current_context
            conversation.missing_entities = []
            conversation.save()
            Message.objects.create(conversation=conversation, sender="BOT", text=bot_response_text)
            context_manager.add_message(user_id, role="bot", text=bot_response_text)
            return Response({"status": "success", "bot_response": {"text": bot_response_text, "internal_debug": {"intent_detected": extracted_intent, "new_state": new_state, "candidates_count": len(candidates)}}})

        # ── MAIN STATE MACHINE ───────────────────────────────────────────────────
        if extracted_intent == "ORDER_PRODUCT":
            for req in REQUIRED_ORDER_ENTITIES:
                if req not in current_context:
                    missing_list.append(req)

            if missing_list:
                new_state = "WAITING_USER_REPLY"
                first_missing = missing_list[0]
                display_name = matched_product["name"] if matched_product else "cet article"
                bot_response_text = (
                    MISSING_ENTITY_TEMPLATES
                    .get(first_missing, f"Pouvez-vous me dire {first_missing} ?")
                    .replace("{product}", display_name)
                    .replace("{color}", current_context.get("color", ""))
                )
                # Inject available sizes / colors from Mock API
                if matched_product and first_missing in ["size", "color"]:
                    variations = matched_product.get("variations", [])
                    if first_missing == "size":
                        avail = ", ".join(list(set([v["size"] for v in variations if v.get("stock_quantity", 0) > 0])))
                        bot_response_text += f"\nTailles disponibles : {avail}" if avail else ""
                    elif first_missing == "color":
                        avail = ", ".join(list(set([v["color"] for v in variations if v.get("stock_quantity", 0) > 0])))
                        bot_response_text += f"\nCouleurs disponibles : {avail}" if avail else ""
            else:
                # All entities collected ── verify stock before confirming
                chosen_color = current_context.get("color", "")
                chosen_size = current_context.get("size", "")
                display_name = matched_product["name"] if matched_product else current_context.get("product", "votre article")
                stock_ok = True

                if matched_product and chosen_color and chosen_size:
                    valid_variation = next(
                        (v for v in matched_product.get("variations", [])
                         if v.get("color", "").lower() == chosen_color.lower()
                         and v.get("size", "").lower() == chosen_size.lower()
                         and v.get("stock_quantity", 0) > 0),
                        None
                    )
                    if not valid_variation:
                        stock_ok = False
                        avail = ", ".join(list(set([
                            f"{v['color']} / {v['size']}"
                            for v in matched_product.get("variations", [])
                            if v.get("stock_quantity", 0) > 0
                        ])))
                        bot_response_text = (
                            OUT_OF_STOCK_TEMPLATE
                            .replace("{product}", display_name)
                            .replace("{color}", chosen_color)
                            .replace("{size}", chosen_size)
                        )
                        if avail:
                            bot_response_text += f"\nDisponible en : {avail}"
                        # Reset so user re-chooses color & size
                        current_context.pop("color", None)
                        current_context.pop("size", None)
                        missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                        new_state = "WAITING_USER_REPLY"

                if stock_ok:
                    new_state = "COMPLETED"
                    pre_order_ref = None
                    try:
                        # ✅ Créer une PRÉ-COMMANDE dans Lead (en attente confirmation agent)
                        lead.create_pending_order(
                            shop_id=shop_id,
                            product_id=matched_product["id"] if matched_product else None,
                            variation_id=vision_variation_id,
                            color=chosen_color,
                            size=chosen_size,
                            address=current_context.get("address"),
                            phone_number=current_context.get("phone_number"),
                            quantity=int(current_context.get("quantity", 1))
                        )
                        pre_order_ref = lead.pending_order_reference
                    except Exception as e:
                        print(f"Pre-order creation error: {e}")

                    if pre_order_ref:
                        bot_response_text = ORDER_CONFIRMED_TEMPLATE.replace("{product}", display_name).replace("{ref}", str(pre_order_ref))
                    else:
                        bot_response_text = ORDER_CONFIRMED_NO_REF_TEMPLATE.replace("{product}", display_name)

        elif extracted_intent == "INFORM_INFO":
            # User is answering a previous question (color, size, address, etc.)
            if previous_state == "WAITING_USER_REPLY" and conversation.missing_entities:
                for req in REQUIRED_ORDER_ENTITIES:
                    if req not in current_context:
                        missing_list.append(req)

                if missing_list:
                    new_state = "WAITING_USER_REPLY"
                    first_missing = missing_list[0]
                    bot_response_text = (
                        MISSING_ENTITY_TEMPLATES
                        .get(first_missing, f"Et pour la {first_missing} ?")
                        .replace("{product}", current_context.get("product", "cet article"))
                        .replace("{color}", current_context.get("color", ""))
                    )
                else:
                    # All entities collected — same stock check as ORDER_PRODUCT flow
                    chosen_color = current_context.get("color", "")
                    chosen_size  = current_context.get("size", "")
                    display_name = matched_product["name"] if matched_product else current_context.get("product", "votre article")
                    stock_ok = True

                    # Fail-safe: if product was identified by image but matched_product is None
                    # (Mock API unreachable or shop_id invalid), block the order
                    if not matched_product and current_context.get("product", "").startswith("Article_From_Image_"):
                        stock_ok = False
                        bot_response_text = "Désolé, impossible de vérifier le stock pour le moment. Veuillez réessayer."
                        new_state = "WAITING_USER_REPLY"
                        missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]

                    elif matched_product and chosen_color and chosen_size:
                        print(f"[STOCK CHECK] color='{chosen_color}' size='{chosen_size}'")
                        print(f"[STOCK CHECK] variations={[(v.get('color'), v.get('size'), v.get('stock_quantity')) for v in matched_product.get('variations', [])]}")
                        valid_variation = next(
                            (v for v in matched_product.get("variations", [])
                             if v.get("color", "").lower() == chosen_color.lower()
                             and v.get("size", "").lower() == chosen_size.lower()
                             and v.get("stock_quantity", 0) > 0),
                            None
                        )
                        if not valid_variation:
                            stock_ok = False
                            avail = ", ".join(list(set([
                                f"{v['color']} / {v['size']}"
                                for v in matched_product.get("variations", [])
                                if v.get("stock_quantity", 0) > 0
                            ])))
                            bot_response_text = (
                                OUT_OF_STOCK_TEMPLATE
                                .replace("{product}", display_name)
                                .replace("{color}", chosen_color)
                                .replace("{size}", chosen_size)
                            )
                            if avail:
                                bot_response_text += f"\nDisponible en : {avail}"
                            # Reset color & size so user can re-choose
                            current_context.pop("color", None)
                            current_context.pop("size", None)
                            missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                            new_state = "WAITING_USER_REPLY"

                    if stock_ok:
                        new_state = "COMPLETED"
                        pre_order_ref = None
                        try:
                            lead.create_pending_order(
                                shop_id=shop_id,
                                product_id=matched_product["id"] if matched_product else None,
                                variation_id=vision_variation_id,
                                color=chosen_color,
                                size=chosen_size,
                                address=current_context.get("address"),
                                phone_number=current_context.get("phone_number"),
                                quantity=int(current_context.get("quantity", 1))
                            )
                            pre_order_ref = lead.pending_order_reference
                        except Exception as e:
                            print(f"Pre-order creation error (INFORM_INFO): {e}")

                        if pre_order_ref:
                            bot_response_text = ORDER_CONFIRMED_TEMPLATE.replace("{product}", display_name).replace("{ref}", str(pre_order_ref))
                        else:
                            bot_response_text = ORDER_CONFIRMED_NO_REF_TEMPLATE.replace("{product}", display_name)
            else:
                bot_response_text = TEMPLATES.get("INFORM_INFO")

        elif extracted_intent in ["ASK_PRICE", "ASK_AVAILABILITY", "ASK_DELIVERY"]:
            # If we're in the middle of an ORDER_PRODUCT flow, answer the question but stay WAITING_USER_REPLY
            if previous_state == "WAITING_USER_REPLY" and conversation.missing_entities:
                # Answer the secondary question but continue order flow
                if extracted_intent == "ASK_PRICE" and matched_product:
                    price = matched_product.get("base_price", "0")
                    product_name = matched_product["name"]
                    bot_response_text = f"Le {product_name} est au prix de {price} TND. "
                elif extracted_intent == "ASK_AVAILABILITY" and matched_product:
                    variations = matched_product.get("variations", [])
                    sizes = ", ".join(list(set([v["size"] for v in variations if v.get("stock_quantity", 0) > 0])))
                    colors = ", ".join(list(set([v["color"] for v in variations if v.get("stock_quantity", 0) > 0])))
                    bot_response_text = f"Oui, le {matched_product['name']} est en stock. "
                    bot_response_text += f"Tailles disponibles : {sizes or 'aucune'}. Couleurs disponibles : {colors or 'aucune'}. "
                else:
                    bot_response_text = TEMPLATES.get(extracted_intent, "Je n'ai pas compris.")
                
                # Now continue asking for missing entities
                for req in REQUIRED_ORDER_ENTITIES:
                    if req not in current_context:
                        missing_list.append(req)
                
                if missing_list:
                    new_state = "WAITING_USER_REPLY"
                    first_missing = missing_list[0]
                    bot_response_text += (
                        MISSING_ENTITY_TEMPLATES
                        .get(first_missing, f"Pouvez-vous me dire {first_missing} ?")
                        .replace("{product}", matched_product["name"] if matched_product else current_context.get("product", "cet article"))
                        .replace("{color}", current_context.get("color", ""))
                    )
            else:
                # Standalone question outside order context
                bot_response_text = TEMPLATES.get(extracted_intent, "Je n'ai pas compris.")
                if matched_product:
                    price = matched_product.get("base_price", "0")
                    bot_response_text = bot_response_text.replace("{product}", matched_product["name"]).replace("{price}", str(price))
                    variations = matched_product.get("variations", [])
                    sizes = ", ".join(list(set([v["size"] for v in variations if v.get("stock_quantity", 0) > 0])))
                    bot_response_text = bot_response_text.replace("{sizes}", sizes or "rupture de stock")
                    colors = ", ".join(list(set([v["color"] for v in variations if v.get("stock_quantity", 0) > 0])))
                    bot_response_text = bot_response_text.replace("{colors}", colors or "rupture de couleur")
                else:
                    try:
                        bot_response_text = bot_response_text.replace("{product}", prod_name or "cet article").replace("{price}", "N/A")
                    except Exception:
                        pass

        else:
            # Handle all other intents (GREETING, ASK_DELIVERY, UNKNOWN, NOISE, etc.)
            # Special case: NOISE during order flow should NOT clear missing_entities
            if extracted_intent == "NOISE" and previous_state == "WAITING_USER_REPLY" and conversation.missing_entities:
                # Don't change state, keep context, just ask for clarification
                new_state = "WAITING_USER_REPLY"
                missing_list = conversation.missing_entities  # Keep existing missing entities
                first_missing = missing_list[0] if missing_list else None
                
                # Respond asking to clarify
                bot_response_text = "Parlez plus clairement s'il vous plaît. "
                if first_missing:
                    bot_response_text += (
                        MISSING_ENTITY_TEMPLATES
                        .get(first_missing, f"Pouvez-vous me dire {first_missing} ?")
                        .replace("{product}", current_context.get("product", "cet article"))
                        .replace("{color}", current_context.get("color", ""))
                    )
            else:
                # No special handling needed
                bot_response_text = TEMPLATES.get(extracted_intent, TEMPLATES.get("UNKNOWN"))

        # Update Conversation state
        conversation.state = new_state
        conversation.missing_entities = missing_list
        conversation.save()

        # 8. Save Bot Message to PostgreSQL
        Message.objects.create(
            conversation=conversation,
            sender="BOT",
            text=bot_response_text,
            is_error=False
        )

        # 9. Add Bot Message to Hot Memory (Redis)
        context_manager.add_message(user_id, role="bot", text=bot_response_text)

        # 10. Clear context if completed
        if new_state == "COMPLETED":
            context_manager.clear_context(user_id)

        # 11. Prepare HTTP Response
        response_payload = {
            "status": "success",
            "bot_response": {
                "text": bot_response_text,
                "internal_debug": {
                    "intent_detected": extracted_intent,
                    "entities_extracted": extracted_entities,
                    "accumulated_context": current_context,
                    "previous_state": previous_state,
                    "new_state": new_state,
                    "missing_entities": missing_list
                }
            }
        }
        # Inclure l'image identifiée par CLIP si disponible
        if matched_image_url:
            response_payload["bot_response"]["identified_image_url"] = matched_image_url

        return Response(response_payload)
