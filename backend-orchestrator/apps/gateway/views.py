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
            # For other intents, we just return the predefined template
            # For ASK_PRICE, we would ideally call mock DB to get real price.
            # We mock the price formatting here for POC
            bot_response_text = TEMPLATES.get(extracted_intent, TEMPLATES["UNKNOWN"])
            # Naive formatting fallback
            try:
                bot_response_text = bot_response_text.replace("{product}", current_context.get("product", "cet article")).replace("{price}", "45")
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
