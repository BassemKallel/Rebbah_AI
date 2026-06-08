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


def run_test():
    run_normalizer_unit_tests()
    run_anaphora_resolution_test()
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
