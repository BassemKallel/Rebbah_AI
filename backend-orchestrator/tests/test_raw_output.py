import os
import sys
import django

# Set up Django environment — remonte d'un niveau pour trouver core.settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from apps.gateway.pipeline import MessagePipeline
from apps.crm.models import Conversation, Lead

def test():
    user_id = "test_user_unique_12345"
    shop_id = "abcd"
    
    Conversation.objects.filter(sender_id=user_id, shop_id=shop_id).delete()
    Lead.objects.filter(platform_id=user_id).delete()
    
    pipeline = MessagePipeline()
    res = pipeline.run(user_id=user_id, shop_id=shop_id, text="Bonjour, j'aimerais tester votre solution Tiktak Pro s'il vous plaît")
    print("Pipeline result:")
    print(res)

if __name__ == "__main__":
    test()
