import os
import sys
import django
import time

# Set up Django environment — remonte d'un niveau pour trouver core.settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.crm.models import Company, Conversation, Lead, Message
from rest_framework.test import APIRequestFactory
from apps.gateway.views import DirectMessageProcessView

def run_test():
    user_id = "test_direct_async_user_888"
    
    # 1. Resolve active company and dashboard token
    company = Company.objects.filter(is_active=True).first()
    if not company:
        print("ERROR: No active company found in the database. Please create one.")
        sys.exit(1)
        
    shop_id = company.shop_id
    token = company.dashboard_token
    print(f"Using Company: {company.name} | Shop ID: {shop_id} | Token: {token}")

    # 2. Clean up previous test data
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    Lead.objects.filter(platform_id=user_id).delete()
    
    # Clear hot memory from Redis for deterministic test results
    from apps.gateway.services.pipeline import context_manager
    context_manager.clear_context(user_id, shop_id)

    # 3. Simulate calling DirectMessageProcessView
    factory = APIRequestFactory()
    request = factory.post(
        '/api/v1/gateway/message/process/',
        {
            "user_id": user_id,
            "text": "Bonjour, je veux tester l'API direct"
        },
        format='json',
        HTTP_X_SHOP_TOKEN=token
    )
    
    view = DirectMessageProcessView.as_view()
    response = view(request)
    
    print(f"Received response status={response.status_code} | data={response.data}")
    assert response.status_code == 200, "Direct API did not return HTTP 200!"
    assert response.data.get("status") == "queued_for_processing", "Direct API did not queue the request!"
    
    # 4. Wait for Celery worker to finish processing using a polling loop (up to 20 seconds)
    print("\nWaiting for Celery worker to process the message in background...")
    conv = None
    user_msgs = []
    for attempt in range(20):
        time.sleep(1.0)
        conv = Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).first()
        if conv:
            user_msgs = list(Message.objects.filter(conversation=conv, sender="USER"))
            if len(user_msgs) > 0:
                print(f"Success! Found message in DB after {attempt + 1} seconds.")
                break
                
    assert conv is not None, "Conversation was not created by the pipeline!"
    print(f"User messages in DB: {[m.text for m in user_msgs]}")
    assert len(user_msgs) == 1, "Expected 1 USER message to be saved in DB"
    assert "tester l'API direct" in user_msgs[0].text, "Message text was not matching!"
    
    print("\n✅ DIRECT ASYNC API TEST SUCCESSFUL!")

if __name__ == "__main__":
    run_test()
