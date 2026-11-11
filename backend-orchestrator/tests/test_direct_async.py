import os
import sys
import django
import time
import threading

# Set up Django environment — remonte d'un niveau pour trouver core.settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.crm.models import Company, Conversation, Lead, Message
from rest_framework.test import APIRequestFactory
from apps.gateway.views import DirectMessageProcessView

def run_test():
    user_id = "test_direct_sync_user_888"
    
    # 1. Resolve active company and dashboard token
    company = Company.objects.filter(is_active=True).first()
    if not company:
        print("ERROR: No active company found in the database. Please create one.")
        sys.exit(1)
        
    shop_id = company.shop_id
    token = company.dashboard_token
    print(f"Using Company: {company.name} | Shop ID: {shop_id} | Token: {token}")

    # Helper function to clear previous test data
    def cleanup():
        Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
        Lead.objects.filter(platform_id=user_id).delete()
        from apps.gateway.services.pipeline import context_manager
        context_manager.clear_context(user_id, shop_id)

    # ==========================================
    # TEST 1: Single Synchronous Message
    # ==========================================
    print("\n=== STARTING SYNCHRONOUS SINGLE MESSAGE TEST ===")
    cleanup()

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
    
    start_time = time.time()
    response = view(request)
    duration = time.time() - start_time
    
    print(f"Received response status={response.status_code} in {duration:.2f} seconds.")
    print(f"Response data: {response.data}")
    
    assert response.status_code == 200, "Direct API did not return HTTP 200!"
    assert response.data.get("status") == "success", f"Direct API did not return success! Got: {response.data.get('status')}"
    
    bot_response = response.data.get("bot_response", {})
    assert "text" in bot_response, "bot_response does not contain text!"
    print(f"Bot response text: {bot_response.get('text')}")
    assert len(bot_response.get("text", "")) > 0, "Bot response text is empty!"

    # ==========================================
    # TEST 2: Concurrent Messages (Debouncing)
    # ==========================================
    print("\n=== STARTING SYNCHRONOUS DEBOUNCING / COALESCING TEST ===")
    cleanup()

    # Clear main thread's event loop to prevent async_to_sync from deadlocking in worker threads
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop and not loop.is_running():
            loop.close()
    except Exception:
        pass
    asyncio.set_event_loop(None)

    results = {}

    def send_msg(thread_name, text, delay):
        from django.db import connections
        connections.close_all()
        if delay > 0:
            time.sleep(delay)
        print(f"[{thread_name}] Sending message: '{text}' at time {time.time():.2f}")
        
        req = factory.post(
            '/api/v1/gateway/message/process/',
            {
                "user_id": user_id,
                "text": text
            },
            format='json',
            HTTP_X_SHOP_TOKEN=token
        )
        
        thread_view = DirectMessageProcessView.as_view()
        thread_start = time.time()
        res = thread_view(req)
        thread_duration = time.time() - thread_start
        
        print(f"[{thread_name}] Received response status={res.status_code} in {thread_duration:.2f} seconds | data={res.data}")
        results[thread_name] = res.data

    thread_a = threading.Thread(target=send_msg, args=("Thread_A", "nheb t-shirt", 0.0))
    thread_b = threading.Thread(target=send_msg, args=("Thread_B", "bleu", 1.0))
    
    start_time_debounce = time.time()
    thread_a.start()
    thread_b.start()
    
    # Wait for both threads to finish
    while thread_a.is_alive() or thread_b.is_alive():
        time.sleep(0.1)

    print(f"\nDebounce test finished in {time.time() - start_time_debounce:.2f} seconds.")

    assert "Thread_A" in results, "Thread A did not complete."
    assert "Thread_B" in results, "Thread B did not complete."
    
    response_a = results["Thread_A"]
    response_b = results["Thread_B"]

    # Thread A must be skipped since Thread B sent a newer message at T=1.0s
    print(f"Thread A Status: {response_a.get('status')} | Reason: {response_a.get('reason')}")
    assert response_a.get("status") == "skipped", "Thread A was not skipped!"
    assert response_a.get("reason") == "newer_message_received", "Thread A skip reason is incorrect!"

    # Thread B must succeed and contain the coalesced text and generated AI response
    print(f"Thread B Status: {response_b.get('status')}")
    assert response_b.get("status") == "success", "Thread B did not succeed!"
    
    bot_response_b = response_b.get("bot_response", {})
    print(f"Thread B Bot response: {bot_response_b.get('text')}")
    assert len(bot_response_b.get("text", "")) > 0, "Thread B Bot response text is empty!"

    # Check the database for the coalesced message
    conv = Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).first()
    assert conv is not None, "Conversation was not created!"
    user_msgs = list(Message.objects.filter(conversation=conv, sender="USER"))
    print(f"User messages in DB: {[m.text for m in user_msgs]}")
    
    assert len(user_msgs) == 1, f"Expected exactly 1 coalesced USER message, got {len(user_msgs)}"
    assert user_msgs[0].text == "nheb t-shirt bleu", f"Expected coalesced text 'nheb t-shirt bleu', got '{user_msgs[0].text}'"

    print("\n✅ DIRECT SYNCHRONOUS DEBOUNCING API TEST SUCCESSFUL!")

if __name__ == "__main__":
    run_test()
