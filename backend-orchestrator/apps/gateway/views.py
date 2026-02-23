import json
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.crm.models import Lead, Conversation, Message
from .context_manager import ContextManager
from .response_templates import TEMPLATES, MISSING_ENTITY_TEMPLATES, REQUIRED_ORDER_ENTITIES

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
        message_data = request.data.get("message", {})
        text = message_data.get("text", "")
        image_url = message_data.get("image_url")

        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Cold Memory: Get or Create Lead and active Conversation
        lead, _ = Lead.objects.get_or_create(platform_id=user_id)
        
        # Assuming one active conversation for simplicity (can be enhanced based on state OR timeframe)
        conversation = Conversation.objects.filter(lead=lead, state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY"]).first()
        if not conversation:
            conversation = Conversation.objects.create(lead=lead, shop_id=shop_id, state="NEW_CONVERSATION")

        # 2. Add User Message to Hot Memory (Redis)
        context_manager.add_message(user_id, role="user", text=text)

        extracted_intent = "UNKNOWN"
        extracted_entities = {}
        is_error = False

        # 3. Vision API (if image provided)
        if image_url:
            try:
                vision_res = requests.post(VISION_URL, json={"image_url": image_url, "limit": 1})
                if vision_res.status_code == 200:
                    vision_data = vision_res.json()
                    if vision_data.get("results"):
                        top_match = vision_data["results"][0]
                        # Simulate adding the detected product from Vision
                        extracted_entities["product"] = f"Article_From_Image_{top_match['product_id']}"
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
            if "product" not in extracted_entities:
                text_lower = text.lower()
                common_products = ["pull", "t-shirt", "veste", "pantalon", "robe"]
                for cp in common_products:
                    if cp in text_lower:
                        extracted_entities["product"] = cp
                        break

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
        conversation.context_data = current_context

        # 7. State Machine & Response Generation
        previous_state = conversation.state
        bot_response_text = TEMPLATES.get("UNKNOWN")
        missing_list = []
        new_state = previous_state

        # Simple logic based on Intent
        if extracted_intent == "ORDER_PRODUCT":
            # Check what's missing
            for req in REQUIRED_ORDER_ENTITIES:
                if req not in current_context:
                    missing_list.append(req)
            
            if missing_list:
                new_state = "WAITING_USER_REPLY"
                first_missing = missing_list[0]
                # Format template with existing product if known
                prod_name = current_context.get("product", "cet article")
                bot_response_text = MISSING_ENTITY_TEMPLATES.get(first_missing, f"Pouvez-vous me donner votre {first_missing} ?").replace("{product}", prod_name)
            else:
                new_state = "COMPLETED"
                bot_response_text = f"Parfait ! Votre commande pour le {current_context.get('product')} est confirmée."
        
        elif extracted_intent == "INFORM_INFO":
            # This intent means the user is answering a question
            if previous_state == "WAITING_USER_REPLY" and conversation.missing_entities:
                # We assume the new entities fill the gap. Let's re-check ORDER_PRODUCT requirements
                for req in REQUIRED_ORDER_ENTITIES:
                    if req not in current_context:
                        missing_list.append(req)
                
                if missing_list:
                    new_state = "WAITING_USER_REPLY"
                    first_missing = missing_list[0]
                    # Safe replacement
                    bot_response_text = MISSING_ENTITY_TEMPLATES.get(first_missing, f"Pouvez-vous me donner votre {first_missing} ?")
                    for k, v in current_context.items():
                        bot_response_text = bot_response_text.replace(f"{{{k}}}", str(v))
                else:
                    new_state = "COMPLETED"
                    bot_response_text = "Toutes les informations sont complètes. Votre commande est validée ! 🎉"
            else:
                bot_response_text = TEMPLATES.get("INFORM_INFO")
                
        else:
            # Check price/stock using the Mock API if we have a product target
            bot_response_text = TEMPLATES.get(extracted_intent, TEMPLATES["UNKNOWN"])
            
            # Extract product context (from NLU text or Vision image match)
            prod_name = current_context.get("product")
            if prod_name and extracted_intent in ["ASK_PRICE", "ASK_AVAILABILITY"]:
                try:
                    # Search the mock API
                    # Using host.docker.internal to bridge outside to the host running django
                    mock_api_url = "http://host.docker.internal:8003/api/v1/products/"
                    headers = {"X-Store-ID": shop_id}
                    resp = requests.get(mock_api_url, headers=headers, timeout=5)
                    
                    if resp.status_code == 200:
                        products = resp.json()
                        matched_product = None
                        
                        # Very simple name matching for POC
                        for p in products:
                            if p["name"].lower() in prod_name.lower() or prod_name.lower() in p["name"].lower():
                                matched_product = p
                                break
                                
                        if matched_product:
                            price = matched_product.get("base_price", "0")
                            bot_response_text = bot_response_text.replace("{product}", matched_product["name"]).replace("{price}", str(price))
                            
                            # Check variations stock
                            variations = matched_product.get("variations", [])
                            sizes = ", ".join(list(set([v["size"] for v in variations if v.get("stock_quantity", 0) > 0])))
                            bot_response_text = bot_response_text.replace("{sizes}", sizes or "rupture de stock")
                            
                            colors = ", ".join(list(set([v["color"] for v in variations if v.get("stock_quantity", 0) > 0])))
                            bot_response_text = bot_response_text.replace("{colors}", colors or "rupture de couleur")
                            
                        else:
                            bot_response_text = f"Désolé, je ne trouve pas le produit {prod_name} dans notre catalogue."
                except Exception as e:
                    print(f"Mock API Error: {e}")
                    bot_response_text = bot_response_text.replace("{product}", prod_name).replace("{price}", "Indisponible")
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
        return Response({
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
        })
