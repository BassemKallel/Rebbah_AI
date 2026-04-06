from django.urls import path
from .views import MessengerWebhookPOC, MetaWebhookView, MetaWebhookSilentView
from .health import ServicesHealthView
from .sync_views import SyncTriggerView, SyncTriggerShopView, SyncStatusView

urlpatterns = [
    path('messenger/poc',       MessengerWebhookPOC.as_view(),   name='messenger_poc'),
    path('meta/webhook',        MetaWebhookView.as_view(),        name='meta_webhook'),
    path('meta/webhook/silent', MetaWebhookSilentView.as_view(),  name='meta_webhook_silent'),
    path('health/',             ServicesHealthView.as_view(),      name='services_health'),
    
    # Sync endpoints
    path('sync/trigger',             SyncTriggerView.as_view(),     name='sync_trigger'),
    path('sync/trigger/<str:shop_id>', SyncTriggerShopView.as_view(), name='sync_trigger_shop'),
    path('sync/status',              SyncStatusView.as_view(),       name='sync_status'),
]

