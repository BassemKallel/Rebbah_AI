import os
import sys
import django

# Set up Django environment — remonte d'un niveau pour trouver core.settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.gateway.services.pipeline import MessagePipeline
from apps.crm.models import Conversation, Lead
from apps.gateway.services.entity_normalizer import normalize_entities, normalize_order_items, _parse_item_string

def run_normalizer_unit_tests():
    print("=== STARTING ENTITY NORMALIZER UNIT TESTS ===")
    
    # Test 1: Version numbers in game titles (FIFA 24, GTA 5)
    res_fifa = _parse_item_string("FIFA 24")
    print(f"FIFA 24 -> {res_fifa}")
    assert res_fifa["product_name"] == "FIFA 24" and res_fifa["quantity"] == 1, "Failed FIFA 24 version check"
    
    res_gta = _parse_item_string("GTA 5")
    print(f"GTA 5 -> {res_gta}")
    assert res_gta["product_name"] == "GTA 5" and res_gta["quantity"] == 1, "Failed GTA 5 version check"

    # Test 2: Leading quantity (2 FIFA 24)
    res_leading = _parse_item_string("2 FIFA 24")
    print(f"2 FIFA 24 -> {res_leading}")
    assert res_leading["product_name"] == "FIFA 24" and res_leading["quantity"] == 2, "Failed leading quantity check"

    # Test 3: Trailing quantity with explicit symbol (T-shirt x3)
    res_explicit = _parse_item_string("T-shirt x3")
    print(f"T-shirt x3 -> {res_explicit}")
    assert res_explicit["product_name"] == "T-shirt" and res_explicit["quantity"] == 3, "Failed explicit multiplier check"

    # Test 4: Trailing quantity with space only (T-shirt rouge 2)
    res_space = _parse_item_string("T-shirt rouge 2")
    print(f"T-shirt rouge 2 -> {res_space}")
    assert res_space["product_name"] == "T-shirt rouge" and res_space["quantity"] == 2, "Failed space trailing quantity check"

    # Test 5: Key translation aliases
    entities = {
        "num_tel": "98765432",
        "adresse_livraison": "Tunis",
        "panier": "FIFA 24"
    }
    normalized = normalize_entities(entities)
    print(f"Normalized Entities -> {normalized}")
    assert normalized.get("phone_number") == "98765432", "Failed key alias phone_number"
    assert normalized.get("address") == "Tunis", "Failed key alias address"
    assert len(normalized.get("items", [])) == 1 and normalized["items"][0]["product_name"] == "FIFA 24", "Failed key alias items"

    # Test 6: Cart items merging and quantity safeguard
    pipeline = MessagePipeline()
    existing = [{"product_name": "Jeu Mallette By Lama", "quantity": 2, "attributes": {}}]
    
    # Merging incoming quantity 1 (fallback) on existing quantity 2 should preserve quantity 2
    incoming_fallback = [{"product_name": "Jeu Mallette By Lama", "quantity": 1, "attributes": {}}]
    res_fallback = pipeline._merge_order_items(existing, incoming_fallback)
    print(f"Merge with fallback qty 1 -> {res_fallback}")
    assert len(res_fallback) == 1 and res_fallback[0]["quantity"] == 2, "Failed to preserve quantity 2 on default fallback"
    
    # Merging incoming quantity 3 (explicit update) on existing quantity 2 should update to quantity 3
    incoming_update = [{"product_name": "Jeu Mallette By Lama", "quantity": 3, "attributes": {}}]
    res_update = pipeline._merge_order_items(existing, incoming_update)
    print(f"Merge with update qty 3 -> {res_update}")
    assert len(res_update) == 1 and res_update[0]["quantity"] == 3, "Failed to update quantity to 3 on explicit quantity"

    print("=== ENTITY NORMALIZER UNIT TESTS PASSED ===\n")


def run_anaphora_resolution_test():
    print("=== STARTING ANAPHORA RESOLUTION UNIT TEST ===")
    user_id = "test_user_anaphora_999"
    shop_id = "xLK0QPj" # Active shop (Lama)
    
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    Lead.objects.filter(platform_id=user_id).delete()
    
    # Clear Redis hot context memory
    from apps.gateway.services.pipeline import context_manager
    context_manager.clear_context(user_id, shop_id)
    
    pipeline = MessagePipeline()
    
    # 1. User clicks "Plus d'infos" or asks for info on Ken T7ebni
    print("\nUser: 'Donne-moi plus d'informations sur le produit : Jeu Ken T7ebni'")
    res1 = pipeline.run(user_id=user_id, shop_id=shop_id, text="Donne-moi plus d'informations sur le produit : Jeu Ken T7ebni")
    print(f"Bot: '{res1['text']}'")
    conv = Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).first()
    print(f"Stored last viewed product: {conv.context_data.get('_last_viewed_product')}")
    assert conv.context_data.get("_last_viewed_product") == "Jeu Ken T7ebni", "Failed to track _last_viewed_product"
    
    # 2. User commands implicitly: "ok c'est bon, commande cet article"
    print("\nUser: 'ok c'est bon, commande cet article'")
    res2 = pipeline.run(user_id=user_id, shop_id=shop_id, text="ok c'est bon, commande cet article")
    print(f"Bot: '{res2['text']}'")
    print(f"Extracted Entities: {res2['entities']}")
    print(f"Conversation State: {res2['state']}")
    
    # Check that items contains the active product
    items = res2['entities'].get("items", [])
    print(f"Items in basket: {items}")
    assert len(items) == 1 and "ken t7ebni" in items[0]["product_name"].lower(), "Failed anaphora resolution for cart product"
    print("=== ANAPHORA RESOLUTION UNIT TEST PASSED ===\n")


def run_change_mind_test():
    print("=== STARTING CHANGE MIND (CAROUSEL -> TEXT) UNIT TEST ===")
    user_id = "test_user_changemind_888"
    shop_id = "xLK0QPj" # Active shop (Lama)
    
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    Lead.objects.filter(platform_id=user_id).delete()
    
    # Clear Redis hot context memory
    from apps.gateway.services.pipeline import context_manager
    context_manager.clear_context(user_id, shop_id)
    
    pipeline = MessagePipeline()
    
    # 1. Initialize DB Conversation with _last_viewed_product as "Jeu Mallette By Lama"
    lead = Lead.objects.create(
        platform_id=user_id,
        shop_id=shop_id
    )
    conv = Conversation.objects.create(
        lead=lead,
        lead_uuid=lead.uuid,
        sender_id=user_id,
        shop_id=shop_id,
        platform="poc",
        state="LLM_ACTIVE",
        context_data={"_last_viewed_product": "Jeu Mallette By Lama"}
    )
    
    # Verify it is set
    assert conv.context_data.get("_last_viewed_product") == "Jeu Mallette By Lama", "Failed to mock initial product"
    
    # 2. User changes mind via a normal message asking details about Ken T7ebni
    print("\nUser: 'tnajem ta3tini akther details aala jeu ken t7ebni stp'")
    res1 = pipeline.run(user_id=user_id, shop_id=shop_id, text="tnajem ta3tini akther details aala jeu ken t7ebni stp")
    print(f"Bot: '{res1['text']}'")
    
    conv = Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).first()
    stored_prod = conv.context_data.get("_last_viewed_product")
    print(f"Stored last viewed product: {stored_prod}")
    assert stored_prod == "Jeu Ken T7ebni", f"Expected _last_viewed_product to update to 'Jeu Ken T7ebni', but got '{stored_prod}'"
    
    # 3. User says "commande cet article"
    print("\nUser: 'commande cet article'")
    res2 = pipeline.run(user_id=user_id, shop_id=shop_id, text="commande cet article")
    print(f"Bot: '{res2['text']}'")
    
    # Check that items in cart now contains "Jeu Ken T7ebni" (resolved from _last_viewed_product)
    items = res2['entities'].get("items", [])
    print(f"Items in basket: {items}")
    assert len(items) == 1 and "ken t7ebni" in items[0]["product_name"].lower(), "Failed to resolve correct product from updated _last_viewed_product"
    
    print("=== CHANGE MIND (CAROUSEL -> TEXT) UNIT TEST PASSED ===\n")


def run_locked_carousel_test():
    print("=== STARTING LOCKED CAROUSEL UNIT TEST ===")
    user_id = "test_user_locked_carousel_777"
    shop_id = "xLK0QPj" # Active shop (Lama)
    
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    Lead.objects.filter(platform_id=user_id).delete()
    
    # Clear Redis hot context memory
    from apps.gateway.services.pipeline import context_manager
    context_manager.clear_context(user_id, shop_id)
    
    pipeline = MessagePipeline()
    
    # 1. Simuler une commande en cours de confirmation (state="LLM_CONFIRMING")
    # et panier avec "Jeu Ken T7ebni"
    lead = Lead.objects.create(
        platform_id=user_id,
        shop_id=shop_id
    )
    conv = Conversation.objects.create(
        lead=lead,
        lead_uuid=lead.uuid,
        sender_id=user_id,
        shop_id=shop_id,
        platform="poc",
        state="LLM_CONFIRMING",
        context_data={
            "_last_viewed_product": "Jeu Ken T7ebni",
            "_active_agent": "CHECKOUT",
            "items": [{"product_name": "Jeu Ken T7ebni", "quantity": 1, "attributes": {}}]
        }
    )
    
    # 2. L'utilisateur clique rétroactivement sur un bouton carrousel d'un autre produit
    print("\nUser (clic carrousel) : 'Commander le produit : Jeu Daggez'")
    res = pipeline.run(user_id=user_id, shop_id=shop_id, text="Commander le produit : Jeu Daggez")
    print(f"Bot: '{res['text']}'")
    
    # 3. Vérifications :
    # - Le message du bot doit être l'avertissement de blocage
    assert "3andek talbiya" in res['text'] or "Vous avez déjà" in res['text'], "Failed to trigger warning message"
    
    # - L'état de la conversation doit être préservé en LLM_CONFIRMING
    conv.refresh_from_db()
    assert conv.state == "LLM_CONFIRMING", f"Expected state to remain LLM_CONFIRMING, but got {conv.state}"
    
    # - Le produit en cours d'affichage/panier ne doit PAS avoir été modifié
    assert conv.context_data.get("_last_viewed_product") == "Jeu Ken T7ebni", f"Expected product to remain Jeu Ken T7ebni, but got {conv.context_data.get('_last_viewed_product')}"
    
    # - Un carrousel de confirmation doit être ré-attaché pour guider le client
    carousel_elements = res.get("carousel_elements", [])
    print(f"Carousel elements sent: {carousel_elements}")
    assert len(carousel_elements) == 1 and carousel_elements[0].get("title") == "Confirmer la commande ? 🛒", "Failed to re-attach confirmation carousel"
    
    print("=== LOCKED CAROUSEL UNIT TEST PASSED ===\n")


def run_checkout_question_test():
    print("=== STARTING CHECKOUT QUESTION UNIT TEST ===")
    user_id = "test_user_question_checkout_666"
    shop_id = "xLK0QPj" # Active shop (Lama)
    
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    Lead.objects.filter(platform_id=user_id).delete()
    
    # Clear Redis hot context memory
    from apps.gateway.services.pipeline import context_manager
    context_manager.clear_context(user_id, shop_id)
    
    pipeline = MessagePipeline()
    
    # 1. Simuler un checkout actif (panier avec "Jeu Ken T7ebni" et active_agent="CHECKOUT", state="LLM_ACTIVE")
    lead = Lead.objects.create(
        platform_id=user_id,
        shop_id=shop_id
    )
    conv = Conversation.objects.create(
        lead=lead,
        lead_uuid=lead.uuid,
        sender_id=user_id,
        shop_id=shop_id,
        platform="poc",
        state="LLM_ACTIVE",
        context_data={
            "_last_viewed_product": "Jeu Ken T7ebni",
            "_active_agent": "CHECKOUT",
            "items": [{"product_name": "Jeu Ken T7ebni", "quantity": 2, "attributes": {}}]
        }
    )
    
    # 2. L'utilisateur pose une question sur le prix du produit
    print("\nUser : 'kadesh yetlaa3 l soum ?'")
    res = pipeline.run(user_id=user_id, shop_id=shop_id, text="kadesh yetlaa3 l soum ?")
    print(f"Bot: '{res['text']}'")
    
    # 3. Vérifications :
    # - La réponse du bot doit parler du prix (ex: "59")
    assert "59" in res['text'] or "118" in res['text'], f"Expected price '59' or '118' in bot response, but got: '{res['text']}'"
    
    # - L'état de la conversation doit être préservé à LLM_ACTIVE (il ne doit PAS passer à COMPLETED !)
    conv.refresh_from_db()
    print(f"Conversation state in DB: {conv.state}")
    assert conv.state == "LLM_ACTIVE", f"Expected state to remain LLM_ACTIVE, but got {conv.state}"
    
    # - Le panier d'achat ne doit PAS avoir été vidé (il doit toujours contenir les 2 Jeu Ken T7ebni)
    items = conv.context_data.get("items", [])
    print(f"Items in basket: {items}")
    assert len(items) == 1 and items[0].get("quantity") == 2, f"Expected 2 items in basket, but got: {items}"
    
    print("=== CHECKOUT QUESTION UNIT TEST PASSED ===\n")


def run_routing_and_id_safety_tests():
    print("=== STARTING ROUTING AND ID SAFETY UNIT TEST ===")
    user_id = "test_user_routing_safety_777"
    shop_id = "xLK0QPj" # Active shop (Lama)
    
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    Lead.objects.filter(platform_id=user_id).delete()
    
    # Clear Redis hot context memory
    from apps.gateway.services.pipeline import context_manager
    context_manager.clear_context(user_id, shop_id)
    
    pipeline = MessagePipeline()
    
    # 1. Test ID safety: User asks for available games. The response must NOT print product IDs.
    print("\nUser : 'chfama al3ab ?'")
    res1 = pipeline.run(user_id=user_id, shop_id=shop_id, text="chfama al3ab ?")
    print(f"Bot: '{res1['text']}'")
    
    # Check that common product IDs like prod_... or ID: ... are not in the response text
    import re
    assert not re.search(r'prod_\d+|prod_[a-zA-Z0-9]+', res1['text']), f"Found product ID in response: '{res1['text']}'"
    
    # 2. Test Routing: User says "atini lo3bet ken thebni" (Purchase intent, no quantity).
    # Since they want to order, they should be routed to CHECKOUT agent.
    print("\nUser : 'atini lo3bet ken thebni'")
    res2 = pipeline.run(user_id=user_id, shop_id=shop_id, text="atini lo3bet ken thebni")
    print(f"Bot: '{res2['text']}'")
    
    conv = Conversation.objects.get(sender_id=user_id, shop_id=shop_id)
    active_agent = conv.context_data.get("_active_agent")
    print(f"Active agent in DB: {active_agent}")
    assert active_agent == "CHECKOUT", f"Expected active agent to transition to CHECKOUT, but got {active_agent}"
    
    # Also verify that this second response does not contain any product IDs either
    assert not re.search(r'prod_\d+|prod_[a-zA-Z0-9]+', res2['text']), f"Found product ID in response: '{res2['text']}'"
    
    print("=== ROUTING AND ID SAFETY UNIT TEST PASSED ===\n")


def run_checkout_correction_and_confirm_test():
    print("=== STARTING CHECKOUT CORRECTION AND CONFIRM UNIT TEST ===")
    user_id = "test_user_correction_confirm_888"
    shop_id = "xLK0QPj" # Active shop (Lama)
    
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    Lead.objects.filter(platform_id=user_id).delete()
    
    # Clear Redis hot context memory
    from apps.gateway.services.pipeline import context_manager
    context_manager.clear_context(user_id, shop_id)
    
    pipeline = MessagePipeline()
    
    # 1. Simuler un état de confirmation initial avec un numéro de téléphone erroné (state="LLM_CONFIRMING")
    lead = Lead.objects.create(
        platform_id=user_id,
        shop_id=shop_id
    )
    conv = Conversation.objects.create(
        lead=lead,
        lead_uuid=lead.uuid,
        sender_id=user_id,
        shop_id=shop_id,
        platform="poc",
        state="LLM_CONFIRMING",
        context_data={
            "product": "Jeu Ken T7ebni",
            "_last_viewed_product": "Jeu Ken T7ebni",
            "_active_agent": "CHECKOUT",
            "items": [{"product_name": "Jeu Ken T7ebni", "quantity": 1, "attributes": {}}],
            "address": "Tunis",
            "phone_number": "50152516" # Erroné
        }
    )
    
    # 2. L'utilisateur envoie sa correction
    print("\nUser : 'numero ghalet c'est 50152515'")
    res1 = pipeline.run(user_id=user_id, shop_id=shop_id, text="numero ghalet c'est 50152515")
    print(f"Bot: '{res1['text']}'")
    
    # Vérification:
    # - Le téléphone doit être corrigé en DB
    conv.refresh_from_db()
    phone = conv.context_data.get("phone_number")
    print(f"Phone in DB: {phone}")
    assert phone == "50152515", f"Expected phone to be corrected to 50152515, but got {phone}"
    
    # - L'état de la conversation doit RESTER LLM_CONFIRMING puisque toutes les infos sont complètes et prêtes
    print(f"Conversation state in DB after correction: {conv.state}")
    assert conv.state == "LLM_CONFIRMING", f"Expected state to remain LLM_CONFIRMING, but got {conv.state}"
    
    # 3. L'utilisateur envoie son message de confirmation
    print("\nUser : 'oui confirme'")
    res2 = pipeline.run(user_id=user_id, shop_id=shop_id, text="oui confirme")
    print(f"Bot: '{res2['text']}'")
    
    # Vérification:
    # - L'état de la conversation doit être COMPLETED (commande validée directement !)
    conv.refresh_from_db()
    print(f"Conversation state in DB after confirmation: {conv.state}")
    assert conv.state == "COMPLETED", f"Expected state to transition to COMPLETED, but got {conv.state}"
    
    # - Une commande doit être présente en DB (champs du lead complétés et OrderItems associés)
    lead.refresh_from_db()
    assert lead.has_pending_order is True, "Lead has_pending_order is False!"
    from apps.crm.models.lead import OrderItem
    order_items = OrderItem.objects.filter(lead=lead)
    print(f"Created order items count: {order_items.count()}")
    assert order_items.exists(), "No OrderItems were created in the database!"
    
    print("=== CHECKOUT CORRECTION AND CONFIRM UNIT TEST PASSED ===\n")


def run_checkout_cancellation_test():
    print("=== STARTING CHECKOUT CANCELLATION UNIT TEST ===")
    user_id = "test_user_cancellation_999"
    shop_id = "xLK0QPj" # Active shop (Lama)
    
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    Lead.objects.filter(platform_id=user_id).delete()
    
    # Clear Redis hot context memory
    from apps.gateway.services.pipeline import context_manager
    context_manager.clear_context(user_id, shop_id)
    
    pipeline = MessagePipeline()
    
    # 1. Simuler un état de checkout actif (state="LLM_ACTIVE", agent="CHECKOUT", items présents)
    lead = Lead.objects.create(
        platform_id=user_id,
        shop_id=shop_id
    )
    conv = Conversation.objects.create(
        lead=lead,
        lead_uuid=lead.uuid,
        sender_id=user_id,
        shop_id=shop_id,
        platform="poc",
        state="LLM_ACTIVE",
        context_data={
            "product": "Jeu Ken T7ebni",
            "_last_viewed_product": "Jeu Ken T7ebni",
            "_active_agent": "CHECKOUT",
            "items": [{"product_name": "Jeu Ken T7ebni", "quantity": 1, "attributes": {}}],
            "address": "Tunis",
            "phone_number": "50152515"
        }
    )
    
    # 2. L'utilisateur envoie le message d'annulation
    print("\nUser : 'annuler la commande stp'")
    res = pipeline.run(user_id=user_id, shop_id=shop_id, text="annuler la commande stp")
    print(f"Bot: '{res['text']}'")
    
    # Vérifications :
    # - La réponse du bot doit être un message d'annulation
    assert "إلغاء" in res['text'] or "annulée" in res['text'], f"Expected cancellation message, but got: '{res['text']}'"

    # - L'état de la conversation doit être LLM_CANCELED (et non plus COMPLETED)
    conv.refresh_from_db()
    print(f"Conversation state in DB after cancel: {conv.state}")
    assert conv.state == "LLM_CANCELED", f"Expected state to transition to LLM_CANCELED, but got {conv.state}"
    
    # - Le panier d'achat doit avoir été entièrement vidé
    items = conv.context_data.get("items", [])
    print(f"Items in basket after cancel: {items}")
    assert len(items) == 0, f"Expected basket to be cleared, but got: {items}"
    
    # 3. Test de l'annulation via le bouton du carrousel ("non annule samhni")
    print("\nSimuler le clic sur le bouton carrousel d'annulation...")
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    context_manager.clear_context(user_id, shop_id)
    
    lead2 = Lead.objects.create(platform_id=user_id, shop_id=shop_id)
    conv2 = Conversation.objects.create(
        lead=lead2, lead_uuid=lead2.uuid, sender_id=user_id, shop_id=shop_id,
        platform="poc", state="LLM_CONFIRMING",
        context_data={
            "product": "Jeu Ken T7ebni",
            "_last_viewed_product": "Jeu Ken T7ebni",
            "_active_agent": "CHECKOUT",
            "items": [{"product_name": "Jeu Ken T7ebni", "quantity": 1, "attributes": {}}],
            "address": "Tunis",
            "phone_number": "50152515"
        }
    )
    res_btn = pipeline.run(user_id=user_id, shop_id=shop_id, text="non annule samhni")
    print(f"Bot (clic bouton): '{res_btn['text']}'")
    
    conv2.refresh_from_db()
    assert conv2.state == "LLM_CANCELED", f"Expected state to transition to LLM_CANCELED after carousel cancel click, but got {conv2.state}"
    assert len(conv2.context_data.get("items", [])) == 0, "Basket items were not cleared after cancel button click!"
    assert "إلغاء" in res_btn['text'] or "annulée" in res_btn['text'], f"Expected cancellation text, but got: '{res_btn['text']}'"

    print("=== CHECKOUT CANCELLATION UNIT TEST PASSED ===\n")


def run_test():
    run_normalizer_unit_tests()
    run_anaphora_resolution_test()
    run_change_mind_test()
    run_locked_carousel_test()
    run_checkout_question_test()
    run_routing_and_id_safety_tests()
    run_checkout_correction_and_confirm_test()
    run_checkout_cancellation_test()
    user_id = "test_user_unique_12345"
    shop_id = "abcd"
    
    # 1. Clean up previous test data
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    Lead.objects.filter(platform_id=user_id).delete()
    
    # Clear Redis hot context memory
    from apps.gateway.services.pipeline import context_manager
    context_manager.clear_context(user_id, shop_id)
    
    pipeline = MessagePipeline()
    
    # Sequence of user messages to test the checkout flow
    messages = [
        "Bonjour, j'aimerais tester votre solution Tiktak Pro s'il vous plaît",
        "Je m'appelle Mohamed Kallel",
        "Mon numéro est le 98123456",
        "Ma boutique s'appelle Kallel Shop et je fais environ 20 commandes par jour",
        "Oui, c'est parfait !"
    ]
    
    print("=== STARTING PIPELINE FLOW TEST ===")
    for msg in messages:
        print(f"\nUser: '{msg}'")
        res = pipeline.run(user_id=user_id, shop_id=shop_id, text=msg)
        print(f"Bot: '{res['text']}'")
        print(f"Intent: {res['intent']} | State: {res['state']}")
        print(f"Entities: {res['entities']}")
        
        # Reload conversation to check state and context
        conv = Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).first()
        if conv:
            print(f"Conversation State in DB: {conv.state}")
            print(f"Conversation Context Data: {conv.context_data}")

if __name__ == "__main__":
    run_test()
