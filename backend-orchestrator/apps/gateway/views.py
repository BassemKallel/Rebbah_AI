import json
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.crm.models import Lead, Conversation, Message
from .context_manager import ContextManager
from .response_templates import (
    TEMPLATES, MISSING_ENTITY_TEMPLATES, REQUIRED_ORDER_ENTITIES,
    DISAMBIGUATION_TEMPLATE, OUT_OF_STOCK_TEMPLATE,
    ORDER_CONFIRMED_TEMPLATE, ORDER_CONFIRMED_NO_REF_TEMPLATE
)

# Internal service URLs
NLU_URL = "http://nlu-service:8001/predict"
VISION_URL = "http://vision-service:8002/search-similar"

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

        # 3. Vision API (if image provided)
        matched_image_url = None
        vision_variation_id = None   # Variable locale, jamais persistée en DB
        if image_url:
            try:
                vision_res = requests.post(
                    VISION_URL,
                    json={"image_url": image_url, "limit": 1, "shop_id": shop_id}
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
                nlu_res = requests.post(NLU_URL, json={"message": text})
                if nlu_res.status_code == 200:
                    nlu_data = nlu_res.json()
                    intent_obj = nlu_data.get("intent", {})
                    extracted_intent = intent_obj.get("intent", "UNKNOWN")
                    
                    # Merge NLU entities with Vision entities
                    for ent in nlu_data.get("entities", []):
                        extracted_entities[ent["label"]] = ent["text"]
                        
            except requests.RequestException as e:
                is_error = True
                print(f"NLU API Error: {e}")
                
            # Fallback for POC: if NLU missed the product but recognized intent
            if "product" not in extracted_entities and not image_url:
                text_lower = text.lower()
                common_products = ["pull", "t-shirt", "veste", "pantalon", "robe"]
                for cp in common_products:
                    if cp in text_lower:
                        extracted_entities["product"] = cp
                        break
                        
        # If user sent an image but NLU failed to get the intent, default to ORDER
        if image_url and (extracted_intent == "UNKNOWN" or not text):
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
        current_context.update(extracted_entities)
        # Toujours nettoyer les clés internes — jamais persistées en DB
        current_context.pop("_vision_variation_id", None)
        conversation.context_data = current_context

        # 7. State Machine & Response Generation
        previous_state = conversation.state
        bot_response_text = TEMPLATES.get("UNKNOWN")
        missing_list = []
        new_state = previous_state
        
        prod_name = current_context.get("product")
        matched_product = None
        
        # We fetch Mock API first if we have a product, because we might need its real name instead of the UUID
        if prod_name:
            try:
                mock_api_url = "http://192.168.100.10:8003/api/v1/products/"
                headers = {"X-Store-ID": shop_id}
                resp = requests.get(mock_api_url, headers=headers, timeout=5)
                
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
                    new_state = "COMPLETED"
                    display_name = matched_product["name"] if matched_product else current_context.get("product", "votre article")
                    bot_response_text = ORDER_CONFIRMED_NO_REF_TEMPLATE.replace("{product}", display_name)
            else:
                bot_response_text = TEMPLATES.get("INFORM_INFO")

        elif extracted_intent in ["ASK_PRICE", "ASK_AVAILABILITY"]:
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
