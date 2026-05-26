import os
import sys
import django
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Set up Django environment — remonte d'un niveau pour trouver core.settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.crm.models import Company, Conversation, Lead, Message
from rest_framework.test import APIRequestFactory
from apps.gateway.views import MessengerWebhookPOC

def run_test():
    user_id = "test_debounce_user_999"
    
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
    from apps.gateway.pipeline import context_manager
    context_manager.clear_context(user_id, shop_id)

    factory = APIRequestFactory()
    results = {}

    def send_msg(thread_name, text, delay):
        from django.db import connections
        connections.close_all()
        if delay > 0:
            time.sleep(delay)
        print(f"[{thread_name}] Sending message: '{text}' at time {time.time():.2f}")
        
        request = factory.post(
            '/api/v1/gateway/messenger/poc/',
            {
                "user_id": user_id,
                "message": {
                    "text": text
                }
            },
            format='json',
            HTTP_X_SHOP_TOKEN=token
        )
        
        view = MessengerWebhookPOC.as_view()
        response = view(request)
        
        print(f"[{thread_name}] Received response status={response.status_code} | data={response.data} at time {time.time():.2f}")
        results[thread_name] = response.data

    print("\n=== STARTING DEBOUNCE COALESCING TEST ===")
    start_time = time.time()
    
    # We will spawn two threads:
    # - Thread A sends "nheb t-shirt" immediately (T = 0)
    # - Thread B sends "bleu" 1.0s later (T = 1.0s)
    # With a 3.0s debounce sleep:
    # - Thread A will sleep from T=0 to T=3.0s. At T=3.0s, latest_timestamp (T=1.0s) > thread_timestamp (T=0). A skips!
    # - Thread B will sleep from T=1.0 to T=4.0s. At T=4.0s, latest_timestamp (T=1.0s) == thread_timestamp (T=1.0s). B processes!
    # B should concatenate the buffer into "nheb t-shirt bleu" and return success.
    
    # Start watchdog thread to print stack traces if execution hangs for more than 300 seconds
    def watchdog():
        time.sleep(300.0)
        import sys
        import traceback
        print("\n=== WATCHDOG TIMEOUT: PRINTING ALL THREAD STACK TRACES ===")
        for thread_id, frame in sys._current_frames().items():
            print(f"\n--- Thread {thread_id} ---")
            traceback.print_stack(frame)
        sys.exit(1)
        
    watchdog_thread = threading.Thread(target=watchdog, daemon=True)
    watchdog_thread.start()

    # Clear main thread's event loop to prevent async_to_sync from deadlocking in worker threads
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop and not loop.is_running():
            loop.close()
    except Exception:
        pass
    asyncio.set_event_loop(None)

    thread_a = threading.Thread(target=send_msg, args=("Thread_A", "nheb t-shirt", 0.0))
    thread_b = threading.Thread(target=send_msg, args=("Thread_B", "bleu", 1.0))
    
    thread_a.start()
    thread_b.start()
    
    # Wait for both threads to finish while keeping the main thread responsive (prevents deadlock)
    while thread_a.is_alive() or thread_b.is_alive():
        time.sleep(0.1)

    print(f"\nTest finished in {time.time() - start_time:.2f} seconds.")

    # 3. Assertions
    print("\n=== VERIFYING RESULTS ===")
    
    assert "Thread_A" in results, "Thread A did not complete."
    assert "Thread_B" in results, "Thread B did not complete."
    
    response_a = results["Thread_A"]
    response_b = results["Thread_B"]
    
    # Both HTTP requests should be queued successfully in <20ms
    print(f"Thread A HTTP Status: {response_a.get('status')}")
    assert response_a.get("status") == "queued_for_processing", "Thread A HTTP call was not queued!"
    
    print(f"Thread B HTTP Status: {response_b.get('status')}")
    assert response_b.get("status") == "queued_for_processing", "Thread B HTTP call was not queued!"

    # Wait for Celery worker to finish processing using a robust polling loop (up to 20 seconds)
    print("\nWaiting for Celery worker to process the messages (polling DB up to 20 seconds)...")
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
    
    # Check database messages
    assert conv is not None, "Conversation was not created!"
    print(f"User messages in DB: {[m.text for m in user_msgs]}")
    
    # There should be exactly one USER message containing the coalesced text
    assert len(user_msgs) == 1, f"Expected 1 coalesced USER message, got {len(user_msgs)}"
    assert user_msgs[0].text == "nheb t-shirt bleu", f"Expected 'nheb t-shirt bleu', got '{user_msgs[0].text}'"
    
    print("\n✅ DEBOUNCE TEST SUCCESSFUL! Coalescing and sliding window work perfectly.")

if __name__ == "__main__":
    run_test()
