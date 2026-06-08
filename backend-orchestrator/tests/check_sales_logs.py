import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.crm.models import PipelineLog

shop_id = "xLK0QPj"

# Get the very latest log
log = PipelineLog.objects.filter(shop_id=shop_id).order_by("-created_at").first()
if log:
    print(f"=== LATEST LOG [{log.created_at}] ===")
    print(f"user_text: {log.user_text}")
    print(f"bot_text : {log.bot_text[:100]}")
    print()
    print("--- FULL LOG TRACE ---")
    for line in log.log_messages.splitlines():
        if "DEBUG" in line or "carousel" in line.lower() or "last_viewed" in line.lower() or "PIPELINE" in line:
            print(line)
